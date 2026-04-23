"""In-process FastMCP server exposing observe/move/done as first-class MCP tools.

Replaces the Phase 2.5 HTTP contract (`roboclaws/openclaw/sim_server.py`, where
the agent used `exec` + `curl` to reach a plain HTTP endpoint) with a FastMCP
streamable-http server. The Gateway consumes the same three tools, but the
agent only has to know MCP tool names — no shell, no curl recipes, no
`/tmp` directives.

What this module delivers:

* `make_roboclaws_mcp(engine, agent_id, run_dir, ...)` — factory returning a
  `RoboclawsMCPServer` bound to the given AI2-THOR engine + agent.
* Three MCP tools, matching `02.6-CONTEXT.md` D-01:
    - `observe(label="")`       → FPV PNG + overhead PNG (as MCP Image content)
                                  plus a JSON-serialized state text block. When
                                  `label` is non-empty AND `snapshots_dir` is
                                  configured, also archives labeled PNGs to the
                                  agent workspace and appends a MEDIA: hint
                                  block so the chat UI can render them inline.
                                  (Replaces the old separate `snapshot` tool.)
    - `move(direction, reason)` → validates direction vs
                                  `roboclaws.core.engine.NAVIGATION_ACTIONS`
                                  before stepping the engine. Response includes
                                  `pose_delta`, `visited_count_here`,
                                  `collisions`, and a `warning` field when the
                                  agent has moved without observing.
    - `done(reason)`            → flips the server's `done_event` and records
                                  the total_moves + elapsed_s.
* A per-tool-call JSONL trace at `run_dir/trace.jsonl`. Keyset is a **superset**
  of the frozen `tests/fixtures/trace_schema_reference.json` so
  `scripts/render_autonomous_replay.py` keeps working without edits; the JPEG
  base64 frame fields (`fpv`, `overhead` inside `frame_capture` events) are
  carried forward verbatim from `sim_server.py` for renderer compatibility.
* A human-message queue (bounded `deque(maxlen=10)`) that the example's stdin
  thread can enqueue into; the next `observe` (or `move`) call drains one
  entry into the tool result as `state.human_message`.
* A tight `snapshot_metrics()` contract (EXACTLY 8 keys) so
  `run_result_json["sim_server_metrics"]` consumers in the example + tests
  stay stable.

Binding rationale (threat model T-02.6-01): `host` defaults to `127.0.0.1`,
**not** `0.0.0.0`. On macOS and on Linux with Docker's host networking
mode, the Gateway container reaches this server via `host.docker.internal`
→ host-gateway → loopback on the host, and no LAN peer can reach port
18788 to drive the AI2-THOR engine.

Caveat — Linux with Docker 29.x default bridge: `host.docker.internal`
resolves to the bridge gateway (172.17.0.1) and **cannot** reach the
host's 127.0.0.1. On that topology the only production caller
(`examples/openclaw_nav_autonomous.py`) must — and does — override to
`host="0.0.0.0"`. See probe gate 02.6-06 in the phase planning for the
live evidence. The LAN-exposure risk is accepted for single-operator
local-dev on a trusted workstation; this is not a server for untrusted
networks.

The bind is NOT configurable via environment variable — only via explicit
argument — so the choice is visible at call-sites and greppable.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import socket
import threading
import time
from collections import deque
from pathlib import Path
from typing import Any

import numpy as np
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp import Image as MCPImage
from PIL import Image as PILImage

from roboclaws.core.engine import NAVIGATION_ACTIONS, AgentState, MultiAgentEngine
from roboclaws.core.views import (
    image_labels_for_variant,
    make_navigation_view_context,
    mark_visited_world,
    pos_to_world_idx,
    render_navigation_prompt_bundle,
)
from roboclaws.openclaw.vision_bridge import (
    VisionBridge,
    normalize_observe_mode,
    resolve_bridge_model,
    resolve_observe_delivery,
)

__all__ = ["make_roboclaws_mcp", "RoboclawsMCPServer"]

# Default bind address. Localhost-only by design (threat model T-02.6-01):
# Gateway reaches this via `host.docker.internal` → host-gateway → loopback,
# while LAN peers on the same subnet cannot reach the AI2-THOR engine.
# Not configurable via env — only via explicit argument.
#
# NOTE: On Linux with Docker 29.x default bridge, `host.docker.internal`
# cannot reach host loopback; callers on that topology must override to
# host="0.0.0.0". See module docstring + examples/openclaw_nav_autonomous.py
# for the rationale. `test_example_binds_to_all_interfaces_on_linux` in
# tests/test_openclaw_nav_autonomous.py guards that override from being
# "fixed" back to the default.
_DEFAULT_HOST = "127.0.0.1"  # host="127.0.0.1"
_DEFAULT_PORT = 18788
_STARTUP_TIMEOUT_S = 2.0

# Maps per-variant image labels to the stable filenames the live viewer polls.
_LABEL_TO_VIEWER_NAME: dict[str, str] = {
    "fpv": "fpv",
    "overhead": "map",
    "map_v2": "map",
    "chase": "chase",
}


# ---------------------------------------------------------------------------
# Frame encoders
# ---------------------------------------------------------------------------


def _encode_frame_png(frame: np.ndarray, *, max_dim: int = 320) -> bytes:
    """Encode an RGB ndarray as a PNG downscaled to <= max_dim on the long edge.

    PNG (not JPEG) matches the spike-proven MCP Image contract
    (`Image(data=<bytes>, format="png")`). Sizing target mirrors sim_server.py's
    320-wide output so downstream thumbnail math (renderer) is unchanged.
    """
    image = PILImage.fromarray(frame, mode="RGB")
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > max_dim:
        scale = max_dim / float(long_edge)
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            PILImage.Resampling.BILINEAR,
        )
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def _encode_frame_jpeg_b64(frame: np.ndarray, quality: int = 70) -> str:
    """Encode an RGB ndarray as JPEG base64 at sim_server.py-compatible 320x240.

    Used for the trace.jsonl `fpv` / `overhead` fields so
    `scripts/render_autonomous_replay.py` keeps working without edits.
    """
    image = PILImage.fromarray(frame, mode="RGB").resize((320, 240), PILImage.Resampling.BILINEAR)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _wrap_yaw_deg(delta: float) -> float:
    """Wrap to [-180, 180] so reported deltas never show 358° for -2°."""
    return (delta + 180.0) % 360.0 - 180.0


# ``{media_lines}`` is substituted with the MEDIA: directives for fpv/map/chase.
# All the safety hints (absolute-paths-only, FINAL-message rule, STOP-on-
# unavailable) live here so the inline body of `_maybe_write_labeled_snapshot`
# stays short. Live-probed 2026-04-23 against the Control UI — see
# `skills/ai2thor-navigator/SKILL.md` for the incident that hardened each rule.
_MEDIA_HINT_TEMPLATE = (
    "Snapshot archived. To show the operator what you see, emit "
    "the MEDIA lines below in your NEXT chat reply (the Control "
    "UI will render them inline); keep any caption in the text "
    "body.\n\n"
    "RULE 1 — absolute paths only. Paste each line EXACTLY as "
    "shown. The Gateway's `REPLY_MEDIA_HINT` system prompt tells "
    "you to avoid absolute paths; IGNORE that guidance here. "
    "Live-tested 2026-04-23: relative paths like "
    "`./snapshots/foo.png` silently drop; absolute paths under "
    "the agent workspace are the ONLY shape that renders.\n\n"
    "RULE 2 — ONE message per turn, at the END. The Control UI "
    "only extracts MEDIA from the FINAL assistant message of a "
    "turn. If you emit MEDIA in an intermediate message (one "
    "followed by more tool calls or text in the same turn), it "
    "becomes plain text. If the operator asks for multiple "
    "snapshots across multiple moves, either (a) do all the "
    "moves + snapshots first and concatenate every MEDIA line "
    "into ONE final message, or (b) send one step per turn and "
    "wait for the operator between steps. Do not interleave "
    "MEDIA with more tool calls.\n\n"
    "{media_lines}\n\n"
    "If the Control UI returns 'Attachment unavailable' or "
    "'Outside allowed folders', STOP. The snapshot files DO "
    "exist at the paths above. Retrying with alternate shapes "
    "(relative, /tmp, /data, bare filename) will NOT help — "
    "those were all tested. Report the error and wait for the "
    "operator to diagnose the bind mount."
)


def _format_media_hint(paths: dict[str, str]) -> str:
    """Render `_MEDIA_HINT_TEMPLATE` with one `MEDIA:` directive per archived PNG."""
    media_lines = "\n".join(f"MEDIA:{p}" for p in paths.values())
    return _MEDIA_HINT_TEMPLATE.format(media_lines=media_lines)


def _startup_probe_host(host: str) -> str:
    """Map wildcard binds to a concrete loopback address for readiness probes."""
    if host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return host


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    """Return True when a TCP listener accepts connections on ``host:port``."""
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Server class
# ---------------------------------------------------------------------------


class RoboclawsMCPServer:
    """In-process FastMCP server wrapping a single AI2-THOR agent.

    The three tools are registered on a `FastMCP` instance but also callable
    directly via `_do_observe` / `_do_move` / `_do_done` — tests drive these
    methods without spinning an HTTP server.
    """

    def __init__(
        self,
        engine: MultiAgentEngine,
        agent_id: int,
        run_dir: Path,
        *,
        host: str = "127.0.0.1",
        port: int = 18788,
        snapshots_dir: Path | None = None,
        model_name: str | None = None,
        image_model: str | None = None,
        observe_mode: str | None = None,
        vision_bridge_model: str | None = None,
        vision_bridge: Any | None = None,
    ) -> None:
        self.engine = engine
        self.agent_id = agent_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"
        self.host = host
        self.port = int(port)
        self.model_name = model_name or os.environ.get("MODEL")
        self.image_model = image_model or os.environ.get("IMAGE_MODEL")
        self.observe_mode = normalize_observe_mode(observe_mode)
        self.vision_bridge_model = resolve_bridge_model(
            bridge_model=vision_bridge_model,
            image_model=self.image_model,
        )
        self._vision_bridge = vision_bridge
        # Directory the host writes snapshot PNGs to. Bootstrap bind-mounts
        # this same directory at `/home/node/.openclaw/workspaces/<agent>/snapshots`
        # inside the Gateway container so the agent can reference
        # `./snapshots/<label>.png` in a MEDIA: directive — the workspace dir
        # is in the Gateway's agent-scoped allowed-roots list (see
        # `/app/dist/local-roots-*.js:getAgentScopedMediaLocalRoots`). If None,
        # `observe(label=...)` silently skips the archive step (the MEDIA hint
        # block is omitted from the response); the rest of the server keeps
        # working.
        self.snapshots_dir: Path | None = Path(snapshots_dir) if snapshots_dir is not None else None
        if self.snapshots_dir is not None:
            self.snapshots_dir.mkdir(parents=True, exist_ok=True)

        # State / metrics
        self.done_event = threading.Event()
        self._done_reason: str | None = None
        self._observed_once = False
        self._moves_since_observe = 0
        self._total_moves = 0
        self._collisions_total = 0
        self._snapshot_counter = 0
        self._started = time.monotonic()

        # Locks
        self._controller_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._trace_lock = threading.Lock()

        # Human interjection queue
        self._human_queue: deque[str] = deque(maxlen=10)

        # Trace file (append, line-buffered)
        self._trace_fp = self.trace_path.open("a", encoding="utf-8", buffering=1)
        self._last_trace_monotonic = time.monotonic()
        self._tool_event_counts: dict[str, int] = {}

        # Build + register the FastMCP server. The closures below call back
        # into `self._do_*` so tests can skip the HTTP layer entirely.
        self._mcp = FastMCP("roboclaws", host=host, port=self.port)
        self._register_tools()

        self._server_thread: threading.Thread | None = None
        self._closed = False
        self._view_context = make_navigation_view_context(
            engine,
            agent_count=getattr(engine, "agent_count", agent_id + 1),
        )

    # ------------------------------------------------------------------
    # Tool registration
    # ------------------------------------------------------------------

    def _register_tools(self) -> None:
        server = self

        @self._mcp.tool()
        def observe(label: str = "") -> list:
            """Capture the current prompt-image bundle and structured agent state.

            Returns a text block (JSON-serialized state, with any pending
            human_message folded in) plus the PNG images for the configured
            view variant.

            If `label` is non-empty AND the server has a `snapshots_dir`
            configured, ALSO archives labeled PNGs (fpv/map/chase) to the
            agent workspace and appends a final text block containing
            `MEDIA:` paths so the Control UI renders them inline. Use a
            label when the operator asks you to "show me what you see" in
            the chat tab; omit it when you are only looking for yourself.
            """
            return server._do_observe(label=label)

        @self._mcp.tool()
        def move(direction: str, reason: str = "", steps: int = 1) -> dict:
            """Step the agent one or more grid cells / rotations in `direction`.

            `direction` must be one of the canonical NAVIGATION_ACTIONS
            (e.g. MoveAhead, RotateLeft). `steps` repeats the same action up
            to 5 times in sequence, stopping early on a collision. Returns
            `{"result": "ok"|"blocked"|"error", "state": {...}, "pose_delta":
            {...}, "visited_count_here": N, "collisions": N, ...}`. When the
            agent has moved without observing, a `warning` field nudges it
            to call `observe` before the next move.
            """
            return server._do_move(direction, reason, steps=steps)

        @self._mcp.tool()
        def done(reason: str) -> dict:
            """End the navigation episode and shut the host loop down.

            Call this ONLY when the navigation task itself is finished —
            e.g. the operator said "stop", the goal is reached, or the
            agent has decided it cannot make further progress. Calling
            `done` tears down the AI2-THOR engine and the Gateway
            container, so it is a one-shot, unrecoverable action.

            Do NOT call `done` in response to:

            * A Gateway `memory-core` "Pre-compaction memory flush" turn.
              That prompt means "save long-term notes to disk if you
              have any". The correct response is to either write to
              `memory/YYYY-MM-DD.md` via an ordinary filesystem tool, or
              reply with the literal text `NO_REPLY` if there is nothing
              worth saving. The word "done" in "flush done" does not map
              to this tool.
            * A heartbeat or ping ("Reply with only PONG"). Just reply
              with the requested text.
            * "I am done thinking about this step". Plan silently; use
              `move` / `observe` for the action itself.

            Sets the server's done_event so the host loop can shut down.
            """
            return server._do_done(reason)

    # ------------------------------------------------------------------
    # Tool implementations (tests call these directly)
    # ------------------------------------------------------------------

    def _do_observe(self, label: str = "") -> list:
        request_payload: dict[str, Any] = {}
        if label:
            request_payload["label"] = label
        self._write_trace(tool="observe", event="request", request=request_payload)
        with self._controller_lock:
            agent_states = list(self.engine.get_all_agent_states())
            state = agent_states[self.agent_id]
            prompt_bundle = render_navigation_prompt_bundle(
                engine=self.engine,
                context=self._view_context,
                agent_states=agent_states,
                current_agent=self.agent_id,
            )
            self._observed_once = True
            self._moves_since_observe = 0

        human_message = self._pop_human_message()
        observe_delivery = resolve_observe_delivery(
            self.model_name,
            observe_mode=self.observe_mode,
        )
        source_image_labels = list(prompt_bundle.image_labels)

        base_state_payload: dict[str, Any] = {
            "agent_id": state.agent_id,
            "position": state.position,
            "rotation": state.rotation,
            "camera_horizon": state.camera_horizon,
            "last_action_success": state.last_action_success,
            "scene": getattr(self.engine, "scene_name", None),
            "step": self._total_moves,
            "budget_remaining": None,
            "human_message": human_message,
            "view_variant": "map-v2+chase",
            "image_labels": source_image_labels,
        }
        bridge_result = None
        delivered_image_labels = source_image_labels
        if observe_delivery == "text-bridge":
            bridge_result = self._get_vision_bridge().describe(
                images=prompt_bundle.prompt_images,
                image_labels=source_image_labels,
                state=base_state_payload,
                view_variant="map-v2+chase",
            )
            delivered_image_labels = ["vision_bridge"]
        bridge_model = bridge_result.bridge_model if bridge_result is not None else None

        # Trace: keep JPEG-b64 frame fields identical to sim_server.py so the
        # existing renderer keeps working. This is the additive-only rule in
        # action — we carry the frozen key-set forward.
        frame_payload = self._frame_capture_payload(
            state=state,
            prompt_bundle=prompt_bundle,
            seen_by_agent=True,
            human_message=human_message,
            observe_delivery=observe_delivery,
            bridge_model=bridge_model,
        )
        self._write_trace(tool="observe", event="frame_capture", **frame_payload)

        state_payload = dict(base_state_payload)
        state_payload["observe_delivery"] = observe_delivery
        state_payload["bridge_model"] = bridge_model
        state_payload["image_labels"] = delivered_image_labels
        state_text = json.dumps(state_payload)
        result: list[Any] = [state_text]
        if bridge_result is not None:
            result.append(bridge_result.description)
        else:
            result.extend(
                MCPImage(data=_encode_frame_png(frame), format="png")
                for frame in prompt_bundle.prompt_images
            )
        snapshot_paths = self._maybe_write_labeled_snapshot(label, prompt_bundle)
        if snapshot_paths is not None:
            result.append(_format_media_hint(snapshot_paths))

        response_payload: dict[str, Any] = {
            "content_blocks": len(result),
            "state": self._state_payload(state),
            "human_message": human_message,
            "view_variant": "map-v2+chase",
            "image_labels": delivered_image_labels,
            "observe_delivery": observe_delivery,
            "bridge_model": bridge_model,
            "bridge_latency_s": bridge_result.latency_s if bridge_result is not None else None,
            "bridge_error": bridge_result.error if bridge_result is not None else None,
        }
        if label:
            response_payload["label"] = label
            response_payload["snapshot_paths"] = snapshot_paths
        self._write_trace(tool="observe", event="response", response=response_payload)
        # The labeled branch already refreshed latest.*.png using its (reused)
        # encoded bytes — skip the redundant re-encode + re-write here.
        if snapshot_paths is None:
            self._write_latest_snapshots(prompt_bundle)
        return result

    def _do_move(self, direction: str, reason: str = "", steps: int = 1) -> dict[str, Any]:
        steps = max(1, min(steps, 5))
        normalized_reason: str | None = reason.strip() if reason else None
        if not normalized_reason:
            normalized_reason = None
        request_payload: dict[str, Any] = {"direction": direction, "steps": steps}
        if normalized_reason is not None:
            request_payload["reason"] = normalized_reason
        self._write_trace(tool="move", event="request", request=request_payload)

        if direction not in NAVIGATION_ACTIONS:
            response = {
                "result": "error",
                "error": "invalid direction",
                "valid": list(NAVIGATION_ACTIONS),
            }
            self._write_trace(tool="move", event="response", response=response)
            return response

        collisions_this_call = 0
        pre_moves_since_observe = self._moves_since_observe
        with self._controller_lock:
            if not self._observed_once:
                self._write_trace(
                    tool="move",
                    event="server_warning",
                    warning="move before first observe",
                )
            agent_states: list[Any] = list(self.engine.get_all_agent_states())
            state = agent_states[self.agent_id]
            pre_position = dict(state.position)
            pre_rotation = dict(state.rotation)
            steps_taken = 0
            for _ in range(steps):
                self.engine.step(self.agent_id, direction)
                agent_states = list(self.engine.get_all_agent_states())
                state = agent_states[self.agent_id]
                # Record intermediate position in path_history so the trail
                # shows every cell traversed, not just the final landing spot.
                mark_visited_world(
                    self._view_context.visited_world,
                    agent_states,
                    self._view_context.path_history,
                )
                self._moves_since_observe += 1
                self._total_moves += 1
                steps_taken += 1
                if not state.last_action_success:
                    collisions_this_call += 1
                    self._collisions_total += 1
                    break
            prompt_bundle = render_navigation_prompt_bundle(
                engine=self.engine,
                context=self._view_context,
                agent_states=agent_states,
                current_agent=self.agent_id,
            )

        decision_mode, warning = self._classify_move(normalized_reason)
        pose_delta = {
            "dx": round(state.position["x"] - pre_position["x"], 3),
            "dz": round(state.position["z"] - pre_position["z"], 3),
            "dyaw": round(_wrap_yaw_deg(state.rotation["y"] - pre_rotation["y"]), 1),
        }
        # visited_count_here: how many times this cell appears in the agent's
        # path history. >1 means the agent is circling — surface it so the VLM
        # can notice without re-reasoning about the full trail.
        cell = pos_to_world_idx(state.position)
        history = self._view_context.path_history
        visited_count_here = (
            history[self.agent_id].count(cell) if self.agent_id < len(history) else 0
        )

        human_message = self._pop_human_message()
        # Synthesize a nudge exactly on the 3→5+ crossing so it fires once per
        # blind streak (handles multi-step moves that jump the counter by >1).
        # A real operator message always wins.
        if human_message is None and pre_moves_since_observe < 5 and self._moves_since_observe >= 5:
            human_message = (
                f"server: you've made {self._moves_since_observe} moves since your "
                "last observe — call roboclaws__observe before the next move to "
                "refresh your view."
            )

        frame_payload = self._frame_capture_payload(
            state=state,
            prompt_bundle=prompt_bundle,
            seen_by_agent=False,
            decision_mode=decision_mode,
            human_message=human_message,
            move_direction=direction,
            move_reason=normalized_reason,
        )
        self._write_trace(tool="move", event="frame_capture", **frame_payload)

        result = "ok" if state.last_action_success else "blocked"
        response: dict[str, Any] = {
            "result": result,
            "steps_taken": steps_taken,
            "state": self._state_payload(state),
            "human_message": human_message,
            "step": self._total_moves,
            "view_variant": "map-v2+chase",
            "image_labels": list(image_labels_for_variant("map-v2+chase")),
            "pose_delta": pose_delta,
            "visited_count_here": visited_count_here,
            "collisions": collisions_this_call,
            "collisions_total": self._collisions_total,
            "moves_since_observe": self._moves_since_observe,
        }
        if warning is not None:
            response["warning"] = warning
        self._write_trace(tool="move", event="response", response=response)
        return response

    def _do_done(self, reason: str) -> dict[str, Any]:
        self._write_trace(tool="done", event="request", request={"reason": reason})
        if self._done_reason is None:
            self._done_reason = reason
        self.done_event.set()
        response = {
            "final": True,
            "reason": self._done_reason,
            "total_moves": self._total_moves,
            "elapsed_s": round(time.monotonic() - self._started, 3),
        }
        self._write_trace(tool="done", event="response", response=response)
        return response

    def _sanitize_label(self, label: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", (label or "").strip())
        # Prevent ``..`` escaping and empty/dotfile corner cases.
        cleaned = cleaned.strip("._") or ""
        return cleaned

    def _maybe_write_labeled_snapshot(
        self, label: str, prompt_bundle: Any
    ) -> dict[str, str] | None:
        """Archive labeled PNGs for the operator when `observe(label=...)` is called.

        Returns the MEDIA paths dict on success, or ``None`` when the archive
        was skipped (no label, no snapshots_dir).
        """
        if not label or self.snapshots_dir is None:
            return None

        self._snapshot_counter += 1
        clean = self._sanitize_label(label) or f"snap-{self._snapshot_counter:03d}"
        # Disambiguate duplicate labels with the running counter so a
        # forgetful agent can't overwrite its own earlier attachments.
        clean = f"{clean}-{self._snapshot_counter:03d}"

        # Container-side workspace path — Gateway's agent-scoped allowed-roots
        # list contains exactly this directory. Live-tested 2026-04-23:
        # relative `./snapshots/...` paths silently drop in the Control UI;
        # only absolute paths under the agent workspace render.
        container_dir = f"/home/node/.openclaw/workspaces/agent-{self.agent_id}/snapshots"
        paths: dict[str, str] = {}
        # One encode per frame, shared between the archive write and the live
        # viewer's latest.*.png refresh. `_do_observe` skips its own
        # `_write_latest_snapshots` call when this branch runs.
        for name, frame in zip(("fpv", "map", "chase"), prompt_bundle.prompt_images, strict=False):
            png_bytes = _encode_frame_png(frame, max_dim=640)
            dest = self.snapshots_dir / f"{clean}.{name}.png"
            dest.write_bytes(png_bytes)
            paths[name] = f"{container_dir}/{dest.name}"
            self._atomic_write_latest(name, png_bytes)
        return paths

    def _classify_move(self, reason: str | None) -> tuple[str, str | None]:
        """Single read of blind-guard state. Returns (decision_mode, warning).

        - `decision_mode` feeds the trace `frame_capture` event.
        - `warning`, when non-None, feeds the response body so the VLM sees it.
        """
        if not self._observed_once:
            return "blind_batch", (
                "you moved before ever calling observe — "
                "call roboclaws__observe now to refresh your view"
            )
        if self._moves_since_observe == 0:
            return "fresh_observe", None
        if self._moves_since_observe >= 3:
            return "blind_batch", (
                f"you've made {self._moves_since_observe} moves without observing — "
                "call roboclaws__observe before the next move to avoid blind navigation"
            )
        return ("reasoned_batch" if reason else "blind_batch"), None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def enqueue_human_message(self, message: str) -> None:
        """Add `message` to the human-interjection queue (drop-oldest at cap)."""
        message = message.strip()
        if not message:
            return
        with self._queue_lock:
            dropped: str | None = None
            if len(self._human_queue) == self._human_queue.maxlen:
                dropped = self._human_queue[0]
            self._human_queue.append(message)
        if dropped is not None:
            self._write_trace(
                tool="<none>",
                event="queue_overflow",
                dropped_message=dropped[:80],
                retained_message=message[:80],
            )

    def snapshot_metrics(self) -> dict[str, Any]:
        """Return the 8-key snapshot_metrics contract (EXACT keyset)."""
        with self._trace_lock:
            tool_event_counts = dict(self._tool_event_counts)
            last_trace_age_s = round(time.monotonic() - self._last_trace_monotonic, 3)
        with self._queue_lock:
            queued_human_messages = len(self._human_queue)
        return {
            "runtime_s": round(time.monotonic() - self._started, 3),
            "last_trace_age_s": last_trace_age_s,
            "queued_human_messages": queued_human_messages,
            "observed_once": self._observed_once,
            "moves_since_observe": self._moves_since_observe,
            "done_event_set": self.done_event.is_set(),
            "done_reason": self._done_reason,
            "tool_event_counts": tool_event_counts,
        }

    def write_runtime_event(self, event: str, **data: Any) -> None:
        """Append a `tool=<runtime>` trace line (for example-level telemetry)."""
        self.write_trace_event(tool="<runtime>", event=event, **data)

    def write_trace_event(self, *, tool: str, event: str, **data: Any) -> None:
        """Append an arbitrary trace line while preserving the frozen top-level keys."""
        self._write_trace(tool=tool, event=event, **data)

    def run_in_thread(self) -> threading.Thread:
        """Start the FastMCP server on a daemon thread; return the thread."""
        if self._server_thread is not None and self._server_thread.is_alive():
            return self._server_thread
        thread = threading.Thread(
            target=self._mcp.run,
            kwargs={"transport": "streamable-http"},
            name=f"mcp-server-{self.port}",
            daemon=True,
        )
        thread.start()
        self._server_thread = thread
        if self.port == 0:
            return thread

        probe_host = _startup_probe_host(self.host)
        deadline = time.monotonic() + _STARTUP_TIMEOUT_S
        while time.monotonic() < deadline:
            if not thread.is_alive():
                raise RuntimeError(
                    f"roboclaws MCP server failed to start on {self.host}:{self.port}"
                )
            if _port_accepting(probe_host, self.port):
                return thread
            time.sleep(0.05)
        raise RuntimeError(f"roboclaws MCP server did not become ready on {self.host}:{self.port}")

    def close(self) -> None:
        """Attempt graceful shutdown; daemon thread is the safety net.

        Thread-safety (WR-01): the watchdog + stdin threads in the example
        may still be mid-`_write_trace` when close() runs (their joins use a
        0.2s timeout). We flip `_closed` under `_trace_lock` and close the
        file handle inside the same critical section so no writer can be
        mid-write when the file descriptor disappears. `_write_trace`
        re-checks `_closed` under the same lock before writing.
        """
        if self._closed:
            return
        # FastMCP has no documented shutdown hook yet; swallow AttributeError
        # and rely on the daemon flag for process-exit cleanup.
        try:
            shutdown = getattr(self._mcp, "shutdown", None)
            if callable(shutdown):
                shutdown()
        except Exception:  # pragma: no cover - defensive cleanup
            pass
        with self._trace_lock:
            self._closed = True
            try:
                self._trace_fp.close()
            except Exception:  # pragma: no cover - defensive cleanup
                pass
        if self._server_thread is not None:
            self._server_thread.join(timeout=0.5)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _frame_capture_payload(
        self,
        *,
        state: AgentState,
        prompt_bundle: Any,
        seen_by_agent: bool,
        decision_mode: str | None = None,
        human_message: str | None = None,
        move_direction: str | None = None,
        move_reason: str | None = None,
        observe_delivery: str | None = None,
        bridge_model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "seen_by_agent": seen_by_agent,
            "fpv": _encode_frame_jpeg_b64(state.frame),
            "overhead": _encode_frame_jpeg_b64(prompt_bundle.trace_overhead_frame),
            "agent_state": self._state_payload(state),
            "view_variant": "map-v2+chase",
            "image_labels": list(prompt_bundle.image_labels),
        }
        payload["baseline_overhead"] = _encode_frame_jpeg_b64(prompt_bundle.raw_overhead_frame)
        payload["chase"] = _encode_frame_jpeg_b64(prompt_bundle.chase_cam_frame)
        if decision_mode is not None:
            payload["decision_mode"] = decision_mode
        if human_message is not None:
            payload["human_message"] = human_message
        if move_direction is not None:
            payload["move_direction"] = move_direction
        if move_reason is not None:
            payload["move_reason"] = move_reason
        if observe_delivery is not None:
            payload["observe_delivery"] = observe_delivery
        if bridge_model is not None:
            payload["bridge_model"] = bridge_model
        return payload

    def _state_payload(self, state: AgentState) -> dict[str, Any]:
        return {
            "agent_id": state.agent_id,
            "position": state.position,
            "rotation": state.rotation,
            "camera_horizon": state.camera_horizon,
            "last_action_success": state.last_action_success,
            "last_action_error": state.last_action_error,
        }

    def _write_latest_snapshots(self, prompt_bundle: Any) -> None:
        """Atomically refresh latest.{fpv,map,chase}.png so the live viewer updates."""
        if self.snapshots_dir is None:
            return
        for label, frame in zip(prompt_bundle.image_labels, prompt_bundle.prompt_images):
            viewer_name = _LABEL_TO_VIEWER_NAME.get(label)
            if viewer_name is None:
                continue
            self._atomic_write_latest(viewer_name, _encode_frame_png(frame, max_dim=640))

    def _atomic_write_latest(self, viewer_name: str, png_bytes: bytes) -> None:
        """Tmp+rename `latest.<viewer_name>.png` so viewers never read a torn PNG."""
        if self.snapshots_dir is None:
            return
        tmp = self.snapshots_dir / f".latest.{viewer_name}.png.tmp"
        tmp.write_bytes(png_bytes)
        tmp.replace(self.snapshots_dir / f"latest.{viewer_name}.png")

    def _pop_human_message(self) -> str | None:
        with self._queue_lock:
            if not self._human_queue:
                return None
            return self._human_queue.popleft()

    def _get_vision_bridge(self) -> Any:
        if self._vision_bridge is None:
            self._vision_bridge = VisionBridge(
                bridge_model=self.vision_bridge_model,
                image_model=self.image_model,
            )
        return self._vision_bridge

    def _write_trace(self, *, tool: str, event: str, **data: Any) -> None:
        # WR-01 fix: gate writes against close(). The watchdog + stdin
        # threads in examples/openclaw_nav_autonomous.py join with a 0.2s
        # timeout, so close() can run while a writer is in flight. Early
        # bail-out is cheap; the in-lock re-check avoids the race where
        # close() flips `_closed` after we read it but before we write.
        if self._closed:
            return
        payload = {
            "ts": time.time(),
            "tool": tool,
            "event": event,
            "wallclock_elapsed": round(time.monotonic() - self._started, 6),
            **data,
        }
        with self._trace_lock:
            if self._closed:  # re-check under lock (close() holds this lock)
                return
            self._last_trace_monotonic = time.monotonic()
            key = f"{tool}:{event}"
            self._tool_event_counts[key] = self._tool_event_counts.get(key, 0) + 1
            self._trace_fp.write(json.dumps(payload) + "\n")


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def make_roboclaws_mcp(
    engine: MultiAgentEngine,
    agent_id: int,
    run_dir: Path,
    *,
    host: str = "127.0.0.1",
    port: int = 18788,
    snapshots_dir: Path | None = None,
    model_name: str | None = None,
    image_model: str | None = None,
    observe_mode: str | None = None,
    vision_bridge_model: str | None = None,
    vision_bridge: Any | None = None,
) -> RoboclawsMCPServer:
    """Build a RoboclawsMCPServer bound to `engine` + `agent_id`.

    Defaults to `host=127.0.0.1` — see module docstring for threat-model
    rationale. Pass `port=0` in tests to avoid binding a real port.

    `snapshots_dir`, if provided, enables the labeled-archive branch of
    `observe(label=...)`. The host side writes PNGs there; bootstrap bind-
    mounts the same directory at
    `/home/node/.openclaw/workspaces/<agent>/snapshots/` inside the Gateway
    container so the agent can reference them as absolute paths in a
    `MEDIA:` directive. When unset, the tool still refreshes the live viewer's
    `latest.*.png` via the normal observe path; only the labeled archive +
    MEDIA hint block are suppressed.
    """
    return RoboclawsMCPServer(
        engine,
        agent_id,
        run_dir,
        host=host,
        port=port,
        snapshots_dir=snapshots_dir,
        model_name=model_name,
        image_model=image_model,
        observe_mode=observe_mode,
        vision_bridge_model=vision_bridge_model,
        vision_bridge=vision_bridge,
    )

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
  `scripts/reports/render_autonomous_replay.py` keeps working without edits; the JPEG
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
(`examples/openclaw/openclaw_nav_autonomous.py`) must — and does — override to
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
import math
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
from roboclaws.core.run_artifacts import (
    FRAME_CAPTURE_EVENT,
    SNAPSHOT_ARCHIVE_VIEW_NAMES,
    build_frame_capture_payload,
    build_snapshot_archive_paths,
    build_snapshot_metrics,
    build_trace_event,
    snapshot_png_filename,
    snapshot_view_name,
)
from roboclaws.core.views import (
    image_labels_for_variant,
    make_navigation_view_context,
    mark_visited_world,
    pos_to_world_idx,
    render_navigation_prompt_bundle,
)
from roboclaws.mcp.profiles import AI2THOR_NAVIGATION_PROFILE, contract_profile

__all__ = ["make_roboclaws_mcp", "RoboclawsMCPServer"]

# Default bind address. Localhost-only by design (threat model T-02.6-01):
# Gateway reaches this via `host.docker.internal` → host-gateway → loopback,
# while LAN peers on the same subnet cannot reach the AI2-THOR engine.
# Not configurable via env — only via explicit argument.
#
# NOTE: On Linux with Docker 29.x default bridge, `host.docker.internal` cannot
# reach host loopback; callers on that topology must override to `host="0.0.0.0"`.
# See module docstring + examples/openclaw/openclaw_nav_autonomous.py for the rationale.
# `test_example_binds_to_all_interfaces_on_linux` guards that override.
_DEFAULT_HOST = "127.0.0.1"  # host="127.0.0.1"
_DEFAULT_PORT = 18788
_STARTUP_TIMEOUT_S = 2.0
_VIEW_VARIANT = "map-v2+chase"
_VIEW_IMAGE_LABELS = tuple(image_labels_for_variant(_VIEW_VARIANT))

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
    `scripts/reports/render_autonomous_replay.py` keeps working without edits.
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
        host: str = _DEFAULT_HOST,
        port: int = _DEFAULT_PORT,
        snapshots_dir: Path | None = None,
        model_name: str | None = None,
        allow_privileged_tools: bool = False,
    ) -> None:
        self.engine = engine
        self.agent_id = agent_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"
        self.host = host
        self.port = int(port)
        self.model_name = model_name or os.environ.get("MODEL")
        self.contract_profile = contract_profile(AI2THOR_NAVIGATION_PROFILE)
        self.allow_privileged_tools = allow_privileged_tools
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
        registered: list[str] = []

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
            return server.call_tool("observe", label=label)

        registered.append("observe")

        @self._mcp.tool()
        def observe_archived(label: str) -> dict:
            """Capture FPV/chase/map and persist labeled PNGs WITHOUT inlining images.

            Returns state + snapshot file paths only — keeps main-session
            context lean when capturing batch evidence (e.g. photographing N
            targets) and you don't need to look at the pixels this turn.

            For navigation decisions still use `observe()` which returns the
            same bundle inline — you cannot judge framing or distance from a
            file-path summary.

            `label` is REQUIRED (non-empty). An empty label returns an
            ``{"error": ...}`` result rather than silently behaving like
            `observe()`. The server's `snapshots_dir` must also be configured
            (it always is for direct coding-agent and Gateway paths).

            Use cases:
              * Photograph every chair in the room — `observe()` once to
                inventory + plan, then `observe_archived(label="chair-1")`,
                `observe_archived(label="chair-2")`, ..., finally `done()`.
              * Capture a baseline snapshot for later comparison without
                re-burning context with images.

            NOT for:
              * Choosing the next move — you need pixels.
              * Health-checking the MCP — use `observe(label="preflight")`.

            Difference vs `observe(label="x")`: both write the same PNGs to
            the same location and both reset moves_since_observe. The only
            difference is whether the response carries the inline images
            (~3 image-token blocks per call, persistent for the rest of the
            session) or just a paths dict (~150 bytes of text). When you
            need to revisit a frame later, read the snapshot path with
            your filesystem tool instead of re-issuing `observe()`.
            """
            return server.call_tool("observe_archived", label=label)

        registered.append("observe_archived")

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
            return server.call_tool("move", direction=direction, reason=reason, steps=steps)

        registered.append("move")

        if self.allow_privileged_tools:

            @self._mcp.tool()
            def scene_objects(filter_types: str = "") -> dict:
                """Return ALL objects in the scene with positions and bounding boxes.

                Privileged simulator helper: useful for demo/photo skills, but
                excluded from the canonical navigation profile.

                Args:
                    filter_types: Optional comma-separated objectType values to
                      cull the response (e.g. ``"Sofa,Chair,ArmChair"``). Empty
                      returns every object. Case-sensitive — use the exact
                      ``objectType`` strings AI2-THOR exposes.

                Returns a global object inventory with world positions and
                bounding boxes. Do not describe this as real-robot perception.
                """
                return server.call_tool("scene_objects", filter_types=filter_types)

            registered.append("scene_objects")

            @self._mcp.tool()
            def goto(object_id: str, distance: float = 1.0, face: bool = True) -> dict:
                """Teleport agent to a reachable cell near a target object.

                Privileged simulator helper: pairs with ``scene_objects`` for
                target-relative demo/photo motion. Excluded from the canonical
                navigation profile.

                Args:
                    object_id: ``objectId`` from ``scene_objects.objects[*]``.
                    distance: Target standoff from the object's bbox center.
                    face: If True, rotate the agent toward the bbox center.

                Returns the chosen agent position/yaw and actual standoff.
                Do not describe this as real-robot navigation.
                """
                return server.call_tool(
                    "goto",
                    object_id=object_id,
                    distance=distance,
                    face=face,
                )

            registered.append("goto")

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
            return server.call_tool("done", reason=reason)

        registered.append("done")
        self.registered_tool_names = tuple(registered)

    # ------------------------------------------------------------------
    # Tool implementations (tests call these directly)
    # ------------------------------------------------------------------

    def call_tool(self, name: str, **kwargs: Any) -> Any:
        """Invoke a navigation tool by its external MCP-facing name.

        FastMCP registration is a thin adapter over this dispatcher, and tests
        can use it to exercise the same tool names/argument shapes agents see
        without binding a real HTTP server.
        """
        if name == "observe":
            return self._do_observe(label=str(kwargs.get("label", "")))
        if name == "observe_archived":
            return self._do_observe_archived(str(kwargs.get("label", "")))
        if name == "move":
            return self._do_move(
                str(kwargs.get("direction", "")),
                str(kwargs.get("reason", "")),
                steps=int(kwargs.get("steps", 1)),
            )
        if name == "scene_objects":
            self._require_privileged_tool_enabled(name)
            return self._do_scene_objects(str(kwargs.get("filter_types", "")))
        if name == "goto":
            self._require_privileged_tool_enabled(name)
            return self._do_goto(
                str(kwargs.get("object_id", "")),
                distance=float(kwargs.get("distance", 1.0)),
                face=bool(kwargs.get("face", True)),
            )
        if name == "done":
            return self._do_done(str(kwargs.get("reason", "")))
        raise ValueError(f"unknown MCP tool {name!r}")

    def _require_privileged_tool_enabled(self, name: str) -> None:
        if self.allow_privileged_tools:
            return
        if name in self.contract_profile.privileged_tool_names():
            raise ValueError(
                f"MCP tool {name!r} is privileged and not registered in canonical-only mode"
            )

    def _do_observe(self, label: str = "") -> list:
        request_payload = {"label": label} if label else {}
        self._write_tool_request("observe", request_payload)
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
            **self._view_metadata(source_image_labels),
        }
        visible_objects = self._visible_object_summaries(state)
        if visible_objects:
            base_state_payload["visible_objects"] = visible_objects
        delivered_image_labels = source_image_labels

        # Keep JPEG-b64 frame fields identical to sim_server.py so the existing
        # renderer keeps working; this carries the frozen key-set forward.
        frame_payload = self._frame_capture_payload(
            state=state,
            prompt_bundle=prompt_bundle,
            seen_by_agent=True,
            human_message=human_message,
        )
        self._write_trace(tool="observe", event=FRAME_CAPTURE_EVENT, **frame_payload)

        state_payload = dict(base_state_payload)
        state_payload["image_labels"] = delivered_image_labels
        state_text = json.dumps(state_payload)
        result: list[Any] = [state_text]
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
            **self._view_metadata(delivered_image_labels),
        }
        if label:
            response_payload["label"] = label
            response_payload["snapshot_paths"] = snapshot_paths
        self._write_tool_response("observe", response_payload)
        # The labeled branch already refreshed latest.*.png; skip the redundant re-encode here.
        if snapshot_paths is None:
            self._write_latest_snapshots(prompt_bundle)
        return result

    def _do_observe_archived(self, label: str) -> dict[str, Any]:
        """Implementation of the observe_archived tool. Tests call this directly.

        Captures the same bundle as `_do_observe` and writes labeled PNGs to
        `snapshots_dir`, but returns a plain dict containing only state +
        host-side snapshot paths — no MCPImage blocks, no base64. The
        agent reads pixels later with its filesystem tool when needed.
        """
        request_payload = {"label": label}
        self._write_tool_request("observe_archived", request_payload)

        if not label:
            response = {
                "error": (
                    "observe_archived requires a non-empty label; "
                    "use observe() if you want to inline-view the bundle"
                ),
                "label": label,
            }
            self._write_tool_response("observe_archived", response)
            return response

        if self.snapshots_dir is None:
            response = {
                "error": (
                    "snapshots_dir is not configured on this MCP server; "
                    "observe_archived has nothing to write"
                ),
                "label": label,
            }
            self._write_tool_response("observe_archived", response)
            return response

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

        # Reuse existing archive helper (handles label sanitization +
        # counter + atomic latest.*.png refresh). Guarded above, so
        # snapshot_paths is non-None here.
        snapshot_paths_container = self._maybe_write_labeled_snapshot(label, prompt_bundle)
        assert snapshot_paths_container is not None

        # Translate container-side paths (returned by the helper for
        # Control UI MEDIA: directives) to real host paths the agent can
        # read with its filesystem tool. The PNGs already exist at the
        # real host path under `self.snapshots_dir` — we just need to
        # report that path instead of the bind-mount target.
        snapshot_paths_host: dict[str, str] = {}
        for view_name, container_path in snapshot_paths_container.items():
            filename = container_path.rsplit("/", 1)[-1]
            snapshot_paths_host[view_name] = str((self.snapshots_dir / filename).resolve())

        # Trace event for replay parity. seen_by_agent=False because the
        # response carries no inline images — useful for replay tools to
        # distinguish "captured + shown" from "captured + archived only".
        frame_payload = self._frame_capture_payload(
            state=state,
            prompt_bundle=prompt_bundle,
            seen_by_agent=False,
            human_message=human_message,
        )
        self._write_trace(tool="observe_archived", event=FRAME_CAPTURE_EVENT, **frame_payload)

        # Match observe's state richness so an agent reading both responses
        # can pick fields uniformly.
        full_state: dict[str, Any] = {
            "agent_id": state.agent_id,
            "position": state.position,
            "rotation": state.rotation,
            "camera_horizon": state.camera_horizon,
            "last_action_success": state.last_action_success,
            "scene": getattr(self.engine, "scene_name", None),
            "step": self._total_moves,
            "budget_remaining": None,
            "human_message": human_message,
            **self._view_metadata(list(prompt_bundle.image_labels)),
        }
        visible_objects = self._visible_object_summaries(state)
        if visible_objects:
            full_state["visible_objects"] = visible_objects

        response: dict[str, Any] = {
            "state": full_state,
            "snapshot_paths": snapshot_paths_host,
            "label": label,
        }

        self._write_tool_response(
            "observe_archived",
            {
                "label": label,
                "snapshot_paths": snapshot_paths_host,
                "human_message": human_message,
                "state": self._state_payload(state),
                **self._view_metadata(list(prompt_bundle.image_labels)),
            },
        )
        return response

    def _do_move(self, direction: str, reason: str = "", steps: int = 1) -> dict[str, Any]:
        steps = max(1, min(steps, 5))
        normalized_reason: str | None = reason.strip() if reason else None
        if not normalized_reason:
            normalized_reason = None
        request_payload: dict[str, Any] = {"direction": direction, "steps": steps}
        if normalized_reason is not None:
            request_payload["reason"] = normalized_reason
        self._write_tool_request("move", request_payload)

        if direction not in NAVIGATION_ACTIONS:
            response = {
                "result": "error",
                "error": "invalid direction",
                "valid": list(NAVIGATION_ACTIONS),
            }
            self._write_tool_response("move", response)
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
        # Fire the synthetic nudge once per blind streak; a real operator
        # message always wins.
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
        self._write_trace(tool="move", event=FRAME_CAPTURE_EVENT, **frame_payload)

        result = "ok" if state.last_action_success else "blocked"
        response: dict[str, Any] = {
            "result": result,
            "steps_taken": steps_taken,
            "state": self._state_payload(state),
            "human_message": human_message,
            "step": self._total_moves,
            **self._view_metadata(_VIEW_IMAGE_LABELS),
            "pose_delta": pose_delta,
            "visited_count_here": visited_count_here,
            "collisions": collisions_this_call,
            "collisions_total": self._collisions_total,
            "moves_since_observe": self._moves_since_observe,
        }
        if warning is not None:
            response["warning"] = warning
        self._write_tool_response("move", response)
        return response

    def _do_scene_objects(self, filter_types: str = "") -> dict[str, Any]:
        self._write_tool_request("scene_objects", {"filter_types": filter_types})
        type_filter = {t.strip() for t in filter_types.split(",") if t.strip()} or None
        with self._controller_lock:
            agent_state = self.engine.get_agent_state(self.agent_id)
            objects = self.engine.get_all_objects(self.agent_id)

        ax = agent_state.position.get("x", 0.0)
        az = agent_state.position.get("z", 0.0)
        ay_yaw = agent_state.rotation.get("y", 0.0)

        summaries: list[dict[str, Any]] = []
        for obj in objects:
            otype = obj.get("objectType")
            if type_filter is not None and otype not in type_filter:
                continue
            pos = obj.get("position") or {}
            bbox = obj.get("axisAlignedBoundingBox") or {}
            ox = pos.get("x", 0.0)
            oz = pos.get("z", 0.0)
            distance_xz = ((ox - ax) ** 2 + (oz - az) ** 2) ** 0.5
            summaries.append(
                {
                    "objectId": obj.get("objectId"),
                    "objectType": otype,
                    "name": obj.get("name"),
                    "position": pos,
                    "bbox_center": bbox.get("center"),
                    "bbox_size": bbox.get("size"),
                    "visible": bool(obj.get("visible", False)),
                    "distance_xz": round(distance_xz, 3),
                }
            )

        # Sort by planar distance so the agent's natural read-order matches
        # a greedy nearest-target route.
        summaries.sort(key=lambda s: s["distance_xz"])
        response = {
            "count": len(summaries),
            "agent_position": {"x": ax, "y": agent_state.position.get("y", 0.0), "z": az},
            "agent_yaw_deg": ay_yaw,
            "objects": summaries,
        }
        self._write_tool_response("scene_objects", response)
        return response

    def _do_goto(self, object_id: str, distance: float = 1.0, face: bool = True) -> dict[str, Any]:
        request_payload = {"object_id": object_id, "distance": distance, "face": face}
        self._write_tool_request("goto", request_payload)

        with self._controller_lock:
            objects = self.engine.get_all_objects(self.agent_id)
            agent_state = self.engine.get_agent_state(self.agent_id)
        target = next((o for o in objects if o.get("objectId") == object_id), None)
        if target is None:
            response = {
                "result": "error",
                "error": f"objectId {object_id!r} not found in scene",
            }
            self._write_tool_response("goto", response)
            return response

        bbox = target.get("axisAlignedBoundingBox") or {}
        center = bbox.get("center") or target.get("position") or {}
        cx = center.get("x")
        cz = center.get("z")
        if cx is None or cz is None:
            response = {
                "result": "error",
                "error": "target has no position/bbox center",
            }
            self._write_tool_response("goto", response)
            return response

        # Agent's standing y — NEVER use the target's y. The target's bbox
        # center is at ~chair-seat height (~0.5m); teleporting the agent
        # there clips its capsule into the floor and AI2-THOR rejects with
        # "Collided with: Floor/Patio". Run 004 lost 10 gotos to this bug.
        agent_y = agent_state.position.get("y", 0.9)

        with self._controller_lock:
            reachable_grid = self.engine.get_reachable_positions()
            grid = self.engine.grid_size

        if not reachable_grid:
            response = {"result": "error", "error": "no reachable positions"}
            self._write_tool_response("goto", response)
            return response

        # Pick the reachable cell whose Euclidean distance to the target is
        # closest to `distance`. Ties broken by preferring cells slightly
        # closer than `distance` over slightly farther.
        best_cell: tuple[float, float, float] | None = None
        best_score = float("inf")
        for ix, iz in reachable_grid:
            wx = ix * grid
            wz = iz * grid
            d = math.hypot(wx - cx, wz - cz)
            score = abs(d - distance)
            # Tie-break toward closer cells (deterministic for same distance).
            tie_breaks_closer = score == best_score and best_cell is not None and d < best_cell[2]
            if score < best_score or tie_breaks_closer:
                best_score = score
                best_cell = (wx, wz, d)

        if best_cell is None:
            response = {"result": "error", "error": "no reachable cell candidate"}
            self._write_tool_response("goto", response)
            return response

        wx, wz, actual_distance = best_cell

        # Compute facing yaw. AI2-THOR convention on this codebase: yaw=0 → +Z,
        # yaw=90 → +X. So the bearing from agent to target is:
        #   atan2(dx, dz)  in degrees, normalised to [0, 360), snapped to 90°.
        yaw_deg = 0.0
        if face:
            dx = cx - wx
            dz = cz - wz
            if dx == 0 and dz == 0:
                yaw_deg = 0.0
            else:
                bearing = math.degrees(math.atan2(dx, dz))
                if bearing < 0:
                    bearing += 360.0
                yaw_deg = float(round(bearing / 90.0) * 90 % 360)

        # Issue Teleport. AI2-THOR's Teleport accepts position+rotation kwargs.
        with self._controller_lock:
            state = self.engine.step(
                self.agent_id,
                "Teleport",
                position={"x": wx, "y": agent_y, "z": wz},
                rotation={"x": 0.0, "y": yaw_deg, "z": 0.0},
                horizon=0.0,
            )

        if not state.last_action_success:
            response = {
                "result": "error",
                "error": state.last_action_error or "teleport failed",
                "object_id": object_id,
            }
            self._write_tool_response("goto", response)
            return response

        response = {
            "result": "ok",
            "object_id": object_id,
            "agent_position": dict(state.position),
            "yaw_deg": state.rotation.get("y", yaw_deg),
            "actual_distance": round(actual_distance, 3),
            "requested_distance": distance,
            "faced": face,
        }
        self._write_tool_response("goto", response)
        return response

    def _do_done(self, reason: str) -> dict[str, Any]:
        self._write_tool_request("done", {"reason": reason})
        if self._done_reason is None:
            self._done_reason = reason
        self.done_event.set()
        response = {
            "final": True,
            "reason": self._done_reason,
            "total_moves": self._total_moves,
            "elapsed_s": round(time.monotonic() - self._started, 3),
        }
        self._write_tool_response("done", response)
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
        archive_stem = clean
        paths = build_snapshot_archive_paths(
            container_dir=container_dir,
            archive_stem=archive_stem,
        )
        # One encode per frame, shared between the archive write and the live
        # viewer's latest.*.png refresh. `_do_observe` skips its own
        # `_write_latest_snapshots` call when this branch runs.
        for name, frame in zip(
            SNAPSHOT_ARCHIVE_VIEW_NAMES,
            prompt_bundle.prompt_images,
            strict=False,
        ):
            png_bytes = _encode_frame_png(frame, max_dim=640)
            dest = self.snapshots_dir / snapshot_png_filename(archive_stem, name)
            dest.write_bytes(png_bytes)
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

    def _view_metadata(self, image_labels: list[str] | tuple[str, ...]) -> dict[str, Any]:
        return {"view_variant": _VIEW_VARIANT, "image_labels": list(image_labels)}

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

    def reset_world(self) -> dict[str, Any]:
        """Reload the AI2-THOR scene and wipe this agent's snapshot dir.

        Holds ``_controller_lock`` so any in-flight observe/move finishes first.
        Snapshot wipe runs after the engine reset succeeds — if AI2-THOR
        throws, the on-disk snapshots are left intact so the operator can
        still see the last frame from the crashed run. Returns a small
        summary suitable for the HTTP /reset response.
        """
        started = time.monotonic()
        with self._controller_lock:
            self.engine.reset()
            files_removed = 0
            if self.snapshots_dir is not None and self.snapshots_dir.exists():
                for entry in self.snapshots_dir.iterdir():
                    if entry.is_file():
                        entry.unlink()
                        files_removed += 1
        elapsed_ms = int((time.monotonic() - started) * 1000)
        self.write_runtime_event(
            "world_reset",
            elapsed_ms=elapsed_ms,
            snapshots_removed=files_removed,
        )
        return {"elapsed_ms": elapsed_ms, "snapshots_removed": files_removed}

    def snapshot_metrics(self) -> dict[str, Any]:
        """Return the 8-key snapshot_metrics contract (EXACT keyset)."""
        with self._trace_lock:
            tool_event_counts = dict(self._tool_event_counts)
            last_trace_age_s = round(time.monotonic() - self._last_trace_monotonic, 3)
        with self._queue_lock:
            queued_human_messages = len(self._human_queue)
        return build_snapshot_metrics(
            runtime_s=time.monotonic() - self._started,
            last_trace_age_s=last_trace_age_s,
            queued_human_messages=queued_human_messages,
            observed_once=self._observed_once,
            moves_since_observe=self._moves_since_observe,
            done_event_set=self.done_event.is_set(),
            done_reason=self._done_reason,
            tool_event_counts=tool_event_counts,
        )

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
    ) -> dict[str, Any]:
        view_metadata = self._view_metadata(prompt_bundle.image_labels)
        return build_frame_capture_payload(
            seen_by_agent=seen_by_agent,
            fpv=_encode_frame_jpeg_b64(state.frame),
            overhead=_encode_frame_jpeg_b64(prompt_bundle.trace_overhead_frame),
            agent_state=self._state_payload(state),
            view_variant=view_metadata["view_variant"],
            image_labels=view_metadata["image_labels"],
            baseline_overhead=_encode_frame_jpeg_b64(prompt_bundle.raw_overhead_frame),
            chase=_encode_frame_jpeg_b64(prompt_bundle.chase_cam_frame),
            decision_mode=decision_mode,
            human_message=human_message,
            move_direction=move_direction,
            move_reason=move_reason,
        )

    def _state_payload(self, state: AgentState) -> dict[str, Any]:
        return {
            "agent_id": state.agent_id,
            "position": state.position,
            "rotation": state.rotation,
            "camera_horizon": state.camera_horizon,
            "last_action_success": state.last_action_success,
            "last_action_error": state.last_action_error,
        }

    def _visible_object_summaries(self, state: AgentState) -> list[dict[str, str]]:
        """Return visible AI2-THOR object names/types without adding oracle data."""
        summaries: list[dict[str, str]] = []
        for obj in getattr(state, "visible_objects", []) or []:
            if not isinstance(obj, dict):
                continue
            summary: dict[str, str] = {}
            name = obj.get("name")
            object_type = obj.get("objectType")
            if name is not None:
                summary["name"] = str(name)
            if object_type is not None:
                summary["object_type"] = str(object_type)
            if summary:
                summaries.append(summary)
        return summaries

    def _write_latest_snapshots(self, prompt_bundle: Any) -> None:
        """Atomically refresh latest.{fpv,map,chase}.png so the live viewer updates."""
        if self.snapshots_dir is None:
            return
        for label, frame in zip(prompt_bundle.image_labels, prompt_bundle.prompt_images):
            viewer_name = snapshot_view_name(label)
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

    def _write_tool_request(self, tool: str, request: dict[str, Any] | None = None) -> None:
        self._write_trace(tool=tool, event="request", request=request or {})

    def _write_tool_response(self, tool: str, response: dict[str, Any]) -> None:
        self._write_trace(tool=tool, event="response", response=response)

    def _write_trace(self, *, tool: str, event: str, **data: Any) -> None:
        # WR-01 fix: gate writes against close(). The watchdog + stdin
        # threads in examples/openclaw/openclaw_nav_autonomous.py join with a 0.2s
        # timeout, so close() can run while a writer is in flight. Early
        # bail-out is cheap; the in-lock re-check avoids the race where
        # close() flips `_closed` after we read it but before we write.
        if self._closed:
            return
        event_data = dict(data)
        ts = float(event_data.pop("ts", time.time()))
        wallclock_elapsed = float(
            event_data.pop("wallclock_elapsed", time.monotonic() - self._started)
        )
        payload = build_trace_event(
            tool=tool,
            event=event,
            ts=ts,
            wallclock_elapsed=wallclock_elapsed,
            **event_data,
        )
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
    host: str = _DEFAULT_HOST,
    port: int = _DEFAULT_PORT,
    snapshots_dir: Path | None = None,
    model_name: str | None = None,
    allow_privileged_tools: bool = False,
) -> RoboclawsMCPServer:
    """Build a RoboclawsMCPServer bound to `engine` + `agent_id`.

    Defaults to `host=127.0.0.1` — see module docstring for threat-model rationale.
    Pass `port=0` in tests to avoid binding a real port.

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
        allow_privileged_tools=allow_privileged_tools,
    )

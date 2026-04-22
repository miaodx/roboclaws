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
    - `observe()`              → FPV PNG + overhead PNG (as MCP Image content)
                                 plus a JSON-serialized state text block.
    - `move(direction, reason)`→ validates direction vs
                                 `roboclaws.core.engine.NAVIGATION_ACTIONS`
                                 before stepping the engine.
    - `done(reason)`           → flips the server's `done_event` and records
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
    render_navigation_prompt_bundle,
    validate_view_variant,
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
        view_variant: str = "baseline",
    ) -> None:
        self.engine = engine
        self.agent_id = agent_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"
        self.host = host
        self.port = int(port)
        self.view_variant = validate_view_variant(view_variant)

        # State / metrics
        self.done_event = threading.Event()
        self._done_reason: str | None = None
        self._observed_once = False
        self._moves_since_observe = 0
        self._total_moves = 0
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
        def observe() -> list:
            """Capture the current prompt-image bundle and structured agent state.

            Returns a text block (JSON-serialized state, with any pending
            human_message folded in) plus the PNG images for the configured
            view variant.
            """
            return server._do_observe()

        @self._mcp.tool()
        def move(direction: str, reason: str = "") -> dict:
            """Step the agent one grid cell / rotation in `direction`.

            `direction` must be one of the canonical NAVIGATION_ACTIONS
            (e.g. MoveAhead, RotateLeft). Returns `{"result": "ok"|"blocked"|
            "error", "state": {...}, ...}`.
            """
            return server._do_move(direction, reason)

        @self._mcp.tool()
        def done(reason: str) -> dict:
            """Declare the episode complete and stop the loop.

            Sets the server's done_event so the host loop can shut down.
            """
            return server._do_done(reason)

    # ------------------------------------------------------------------
    # Tool implementations (tests call these directly)
    # ------------------------------------------------------------------

    def _do_observe(self) -> list:
        self._write_trace(tool="observe", event="request", request={})
        with self._controller_lock:
            agent_states = list(self.engine.get_all_agent_states())
            state = agent_states[self.agent_id]
            prompt_bundle = render_navigation_prompt_bundle(
                engine=self.engine,
                context=self._view_context,
                agent_states=agent_states,
                current_agent=self.agent_id,
                variant=self.view_variant,
            )
            self._observed_once = True
            self._moves_since_observe = 0

        human_message = self._pop_human_message()

        # Trace: keep JPEG-b64 frame fields identical to sim_server.py so the
        # existing renderer keeps working. This is the additive-only rule in
        # action — we carry the frozen key-set forward.
        frame_payload = self._frame_capture_payload(
            state=state,
            prompt_bundle=prompt_bundle,
            seen_by_agent=True,
            human_message=human_message,
        )
        self._write_trace(tool="observe", event="frame_capture", **frame_payload)

        # MCP result: state-as-text + N images matching the chosen variant.
        state_text = json.dumps(
            {
                "agent_id": state.agent_id,
                "position": state.position,
                "rotation": state.rotation,
                "camera_horizon": state.camera_horizon,
                "last_action_success": state.last_action_success,
                "scene": getattr(self.engine, "scene_name", None),
                "step": self._total_moves,
                "budget_remaining": None,
                "human_message": human_message,
                "view_variant": self.view_variant,
                "image_labels": list(prompt_bundle.image_labels),
            }
        )
        result: list[Any] = [state_text]
        result.extend(
            MCPImage(data=_encode_frame_png(frame), format="png")
            for frame in prompt_bundle.prompt_images
        )
        self._write_trace(
            tool="observe",
            event="response",
            response={
                "content_blocks": len(result),
                "state": self._state_payload(state),
                "human_message": human_message,
                "view_variant": self.view_variant,
                "image_labels": list(prompt_bundle.image_labels),
            },
        )
        return result

    def _do_move(self, direction: str, reason: str = "") -> dict[str, Any]:
        normalized_reason: str | None = reason.strip() if reason else None
        if not normalized_reason:
            normalized_reason = None
        request_payload: dict[str, Any] = {"direction": direction}
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

        with self._controller_lock:
            if not self._observed_once:
                self._write_trace(
                    tool="move",
                    event="server_warning",
                    warning="move before first observe",
                )
            self.engine.step(self.agent_id, direction)
            agent_states = list(self.engine.get_all_agent_states())
            state = agent_states[self.agent_id]
            prompt_bundle = render_navigation_prompt_bundle(
                engine=self.engine,
                context=self._view_context,
                agent_states=agent_states,
                current_agent=self.agent_id,
                variant=self.view_variant,
            )
            decision_mode = self._classify_move_decision(normalized_reason)
            self._moves_since_observe += 1
            self._total_moves += 1

        human_message = self._pop_human_message()

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
            "state": self._state_payload(state),
            "human_message": human_message,
            "step": self._total_moves,
            "view_variant": self.view_variant,
            "image_labels": list(image_labels_for_variant(self.view_variant)),
        }
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
        self._write_trace(tool="<runtime>", event=event, **data)

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
        payload: dict[str, Any] = {
            "seen_by_agent": seen_by_agent,
            "fpv": _encode_frame_jpeg_b64(state.frame),
            "overhead": _encode_frame_jpeg_b64(prompt_bundle.trace_overhead_frame),
            "agent_state": self._state_payload(state),
            "view_variant": self.view_variant,
            "image_labels": list(prompt_bundle.image_labels),
        }
        if prompt_bundle.structured_overhead_frame is not None:
            payload["baseline_overhead"] = _encode_frame_jpeg_b64(
                prompt_bundle.baseline_overhead_frame
            )
        if prompt_bundle.chase_cam_frame is not None:
            payload["chase"] = _encode_frame_jpeg_b64(prompt_bundle.chase_cam_frame)
        if decision_mode is not None:
            payload["decision_mode"] = decision_mode
        if human_message is not None:
            payload["human_message"] = human_message
        if move_direction is not None:
            payload["move_direction"] = move_direction
        if move_reason is not None:
            payload["move_reason"] = move_reason
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

    def _pop_human_message(self) -> str | None:
        with self._queue_lock:
            if not self._human_queue:
                return None
            return self._human_queue.popleft()

    def _classify_move_decision(self, reason: str | None) -> str:
        if not self._observed_once:
            return "blind_batch"
        if self._moves_since_observe == 0:
            return "fresh_observe"
        if reason:
            return "reasoned_batch"
        return "blind_batch"

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
    view_variant: str = "baseline",
) -> RoboclawsMCPServer:
    """Build a RoboclawsMCPServer bound to `engine` + `agent_id`.

    Defaults to `host=127.0.0.1` — see module docstring for threat-model
    rationale. Pass `port=0` in tests to avoid binding a real port.
    """
    return RoboclawsMCPServer(
        engine,
        agent_id,
        run_dir,
        host=host,
        port=port,
        view_variant=view_variant,
    )

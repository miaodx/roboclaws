from __future__ import annotations

import base64
import io
import json
import threading
import time
from collections import deque
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import numpy as np
from PIL import Image

from roboclaws.core.engine import NAVIGATION_ACTIONS, AgentState, MultiAgentEngine


class _DaemonThreadingHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


class SimHTTPServer:
    """Expose observe/move/done HTTP tools for a single AI2-THOR agent."""

    def __init__(
        self,
        engine: MultiAgentEngine,
        agent_id: int,
        run_dir: Path,
        host: str = "0.0.0.0",
        port: int = 18788,
    ) -> None:
        self.engine = engine
        self.agent_id = agent_id
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        self.trace_path = self.run_dir / "trace.jsonl"
        self.done_event = threading.Event()
        self._done_reason: str | None = None
        self._observed_once = False
        self._moves_since_observe = 0
        self._started = time.monotonic()
        self._controller_lock = threading.Lock()
        self._queue_lock = threading.Lock()
        self._trace_lock = threading.Lock()
        self._human_queue: deque[str] = deque(maxlen=10)
        self._trace_fp = self.trace_path.open("a", encoding="utf-8", buffering=1)

        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - stdlib hook
                server._handle_get(self)

            def do_POST(self) -> None:  # noqa: N802 - stdlib hook
                server._handle_post(self)

            def log_message(self, format: str, *args: object) -> None:  # noqa: A003
                return

        self._httpd = _DaemonThreadingHTTPServer((host, port), Handler)
        self.host = host
        self.port = int(self._httpd.server_address[1])
        self._server_thread = threading.Thread(
            target=self._httpd.serve_forever,
            name=f"sim-http-server-{self.port}",
            daemon=True,
        )
        self._server_thread.start()

    def __enter__(self) -> SimHTTPServer:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        self._server_thread.join(timeout=2.0)
        if self._server_thread.is_alive():
            print("[sim-server] warning: server thread still alive after close() join timeout")
        self._trace_fp.close()

    def enqueue_human_message(self, message: str) -> None:
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

    def _handle_get(self, handler: BaseHTTPRequestHandler) -> None:
        path = urlparse(handler.path).path
        if path != "/observe":
            self._send_json(
                handler,
                HTTPStatus.NOT_FOUND,
                {"error": f"unknown path: {path}"},
            )
            return

        self._write_trace(tool="observe", event="request", request={"method": "GET", "path": path})
        payload = self._observe_payload()
        self._send_json(handler, HTTPStatus.OK, payload)
        self._write_trace(tool="observe", event="response", response=payload)

    def _handle_post(self, handler: BaseHTTPRequestHandler) -> None:
        path = urlparse(handler.path).path
        request = self._read_json_body(handler)
        if request is None:
            self._send_json(
                handler,
                HTTPStatus.BAD_REQUEST,
                {"error": "invalid json body"},
            )
            return

        if path == "/move":
            self._write_trace(
                tool="move",
                event="request",
                request={"method": "POST", "path": path, **request},
            )
            self._handle_move(handler, request)
            return

        if path == "/done":
            self._write_trace(
                tool="done",
                event="request",
                request={"method": "POST", "path": path, **request},
            )
            self._handle_done(handler, request)
            return

        self._send_json(
            handler,
            HTTPStatus.NOT_FOUND,
            {"error": f"unknown path: {path}"},
        )

    def _handle_move(self, handler: BaseHTTPRequestHandler, request: dict[str, Any]) -> None:
        direction = str(request.get("direction", ""))
        reason = str(request.get("reason", "")).strip() or None
        if direction not in NAVIGATION_ACTIONS:
            body = {"error": "invalid direction", "valid": NAVIGATION_ACTIONS}
            self._send_json(handler, HTTPStatus.BAD_REQUEST, body)
            self._write_trace(tool="move", event="response", response=body)
            return

        with self._controller_lock:
            server_warning: str | None = None
            if not self._observed_once:
                server_warning = "move before first observe"
                self._write_trace(
                    tool="move",
                    event="server_warning",
                    warning=server_warning,
                )
            state = self.engine.step(self.agent_id, direction)
            overhead = self.engine.get_overhead_frame()
            decision_mode = self._classify_move_decision(reason)
            self._moves_since_observe += 1

        human_message = self._pop_human_message()

        frame_payload = self._frame_capture_payload(
            state=state,
            overhead=overhead,
            seen_by_agent=False,
            decision_mode=decision_mode,
            human_message=human_message,
            move_direction=direction,
            move_reason=reason,
        )
        self._write_trace(tool="move", event="frame_capture", **frame_payload)

        response = {
            "state": self._state_payload(state),
            "human_message": human_message,
        }
        if server_warning is not None:
            response["server_warning"] = server_warning
        self._send_json(handler, HTTPStatus.OK, response)
        self._write_trace(tool="move", event="response", response=response)

    def _handle_done(self, handler: BaseHTTPRequestHandler, request: dict[str, Any]) -> None:
        reason = str(request.get("reason", ""))
        if self._done_reason is None:
            self._done_reason = reason
        self.done_event.set()
        response = {"status": "ok", "reason": self._done_reason}
        self._send_json(handler, HTTPStatus.OK, response)
        self._write_trace(tool="done", event="response", response=response)

    def _observe_payload(self) -> dict[str, Any]:
        with self._controller_lock:
            state = self.engine.get_agent_state(self.agent_id)
            overhead = self.engine.get_overhead_frame()
            self._observed_once = True
            self._moves_since_observe = 0
        human_message = self._pop_human_message()
        frame_payload = self._frame_capture_payload(
            state=state,
            overhead=overhead,
            seen_by_agent=True,
            human_message=human_message,
        )
        self._write_trace(tool="observe", event="frame_capture", **frame_payload)
        return {
            "fpv": frame_payload["fpv"],
            "overhead": frame_payload["overhead"],
            "state": self._state_payload(state),
            "human_message": human_message,
        }

    def _frame_capture_payload(
        self,
        *,
        state: AgentState,
        overhead: np.ndarray,
        seen_by_agent: bool,
        decision_mode: str | None = None,
        human_message: str | None = None,
        move_direction: str | None = None,
        move_reason: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "seen_by_agent": seen_by_agent,
            "fpv": _encode_frame_b64(state.frame),
            "overhead": _encode_frame_b64(overhead),
            "agent_state": self._state_payload(state),
        }
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

    def _read_json_body(self, handler: BaseHTTPRequestHandler) -> dict[str, Any] | None:
        try:
            length = int(handler.headers.get("Content-Length", "0"))
        except ValueError:
            return None
        raw = handler.rfile.read(length) if length > 0 else b"{}"
        try:
            decoded = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return decoded if isinstance(decoded, dict) else None

    def _send_json(
        self,
        handler: BaseHTTPRequestHandler,
        status: HTTPStatus,
        body: dict[str, Any],
    ) -> None:
        encoded = json.dumps(body).encode("utf-8")
        handler.send_response(int(status))
        handler.send_header("Content-Type", "application/json")
        handler.send_header("Content-Length", str(len(encoded)))
        handler.end_headers()
        handler.wfile.write(encoded)

    def _write_trace(self, *, tool: str, event: str, **data: Any) -> None:
        payload = {
            "ts": time.time(),
            "tool": tool,
            "event": event,
            "wallclock_elapsed": round(time.monotonic() - self._started, 6),
            **data,
        }
        with self._trace_lock:
            self._trace_fp.write(json.dumps(payload) + "\n")


def _encode_frame_b64(frame: np.ndarray, quality: int = 70) -> str:
    image = Image.fromarray(frame, mode="RGB").resize((320, 240), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("ascii")

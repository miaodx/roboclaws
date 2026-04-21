from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock
from urllib import error, request

import numpy as np

from roboclaws.core.engine import AgentState
from roboclaws.openclaw.sim_server import SimHTTPServer


def _frame(color: int = 0) -> np.ndarray:
    return np.full((12, 12, 3), color, dtype=np.uint8)


def _state(*, agent_id: int = 0, color: int = 0) -> AgentState:
    return AgentState(
        agent_id=agent_id,
        frame=_frame(color),
        position={"x": 1.0, "y": 0.0, "z": -2.0},
        rotation={"x": 0.0, "y": 90.0, "z": 0.0},
        camera_horizon=30.0,
        visible_objects=[],
        last_action_success=True,
        last_action_error="",
    )


def _engine() -> MagicMock:
    engine = MagicMock()
    engine.get_agent_state.return_value = _state()
    engine.get_overhead_frame.return_value = _frame(64)
    engine.step.return_value = _state(color=128)
    return engine


def _request_json(
    method: str,
    url: str,
    body: dict | None = None,
) -> tuple[int, dict]:
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = request.Request(url, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _trace(run_dir: Path) -> list[dict]:
    path = run_dir / "trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def test_observe_happy_path(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        status, body = _request_json("GET", f"http://127.0.0.1:{server.port}/observe")

    assert status == 200
    assert set(body) == {"fpv", "overhead", "state", "human_message"}
    assert body["fpv"]
    assert body["overhead"]
    assert body["human_message"] is None
    assert body["state"]["agent_id"] == 0

    frame_events = [event for event in _trace(tmp_path) if event["event"] == "frame_capture"]
    assert len(frame_events) == 1
    assert frame_events[0]["seen_by_agent"] is True


def test_move_valid_direction_dispatches_to_engine(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        _request_json("GET", f"http://127.0.0.1:{server.port}/observe")
        status, body = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead"},
        )

    assert status == 200
    assert set(body) == {"state", "human_message"}
    engine.step.assert_called_once_with(0, "MoveAhead")

    frame_events = [event for event in _trace(tmp_path) if event["event"] == "frame_capture"]
    assert frame_events[-1]["seen_by_agent"] is False
    assert frame_events[-1]["decision_mode"] == "fresh_observe"
    assert frame_events[-1]["move_direction"] == "MoveAhead"
    assert frame_events[-1].get("move_reason") is None


def test_move_rejects_invalid_direction(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        status, body = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "Moonwalk"},
        )

    assert status == 400
    assert body["error"] == "invalid direction"
    assert "MoveAhead" in body["valid"]
    engine.step.assert_not_called()


def test_move_before_observe_returns_warning(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        status, body = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "RotateLeft"},
        )

    assert status == 200
    assert body["server_warning"] == "move before first observe"
    warning_events = [event for event in _trace(tmp_path) if event["event"] == "server_warning"]
    assert len(warning_events) == 1
    frame_events = [event for event in _trace(tmp_path) if event["event"] == "frame_capture"]
    assert frame_events[-1]["decision_mode"] == "blind_batch"


def test_move_reasoned_batch_after_first_unseen_move(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        _request_json("GET", f"http://127.0.0.1:{server.port}/observe")
        _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead"},
        )
        status, _ = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead", "reason": "clear hallway continues"},
        )

    assert status == 200
    frame_events = [event for event in _trace(tmp_path) if event["event"] == "frame_capture"]
    assert frame_events[-1]["decision_mode"] == "reasoned_batch"
    assert frame_events[-1]["move_reason"] == "clear hallway continues"


def test_move_without_reason_after_unseen_move_is_blind_batch(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        _request_json("GET", f"http://127.0.0.1:{server.port}/observe")
        _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead"},
        )
        status, _ = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "RotateLeft"},
        )

    assert status == 200
    frame_events = [event for event in _trace(tmp_path) if event["event"] == "frame_capture"]
    assert frame_events[-1]["decision_mode"] == "blind_batch"


def test_human_message_queue_drains_one_per_tool_call(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        server.enqueue_human_message("first")
        server.enqueue_human_message("second")
        _, observe_body = _request_json("GET", f"http://127.0.0.1:{server.port}/observe")
        _, move_body = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead"},
        )
        _, observe_again = _request_json("GET", f"http://127.0.0.1:{server.port}/observe")

    assert observe_body["human_message"] == "first"
    assert move_body["human_message"] == "second"
    assert observe_again["human_message"] is None


def test_human_message_queue_cap_drops_oldest(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        for idx in range(12):
            server.enqueue_human_message(f"msg-{idx}")
        _, body = _request_json("GET", f"http://127.0.0.1:{server.port}/observe")

    assert body["human_message"] == "msg-2"
    overflow_events = [event for event in _trace(tmp_path) if event["event"] == "queue_overflow"]
    assert len(overflow_events) == 2
    assert overflow_events[0]["dropped_message"] == "msg-0"
    assert overflow_events[1]["dropped_message"] == "msg-1"


def test_controller_mutex_serializes_requests(tmp_path: Path) -> None:
    engine = _engine()
    in_flight = 0
    max_in_flight = 0
    guard = threading.Lock()

    def slow_state(agent_id: int) -> AgentState:
        nonlocal in_flight, max_in_flight
        with guard:
            in_flight += 1
            max_in_flight = max(max_in_flight, in_flight)
        time.sleep(0.05)
        with guard:
            in_flight -= 1
        return _state(agent_id=agent_id)

    engine.get_agent_state.side_effect = slow_state

    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        url = f"http://127.0.0.1:{server.port}/observe"
        threads = [threading.Thread(target=_request_json, args=("GET", url)) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    assert max_in_flight == 1


def test_done_sets_event_and_is_idempotent(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        status_one, body_one = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/done",
            {"reason": "finished"},
        )
        status_two, body_two = _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/done",
            {"reason": "ignored"},
        )
        done_set = server.done_event.is_set()

    assert status_one == 200
    assert status_two == 200
    assert body_one == {"status": "ok", "reason": "finished"}
    assert body_two == {"status": "ok", "reason": "finished"}
    assert done_set is True


def test_close_joins_server_thread(tmp_path: Path) -> None:
    engine = _engine()
    server = SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0)
    server.close()
    assert server._server_thread.is_alive() is False
    assert server._trace_fp.closed is True


def test_snapshot_metrics_and_runtime_events(tmp_path: Path) -> None:
    engine = _engine()
    with SimHTTPServer(engine, agent_id=0, run_dir=tmp_path, port=0) as server:
        server.write_runtime_event("watchdog", note="boot")
        _request_json("GET", f"http://127.0.0.1:{server.port}/observe")
        _request_json(
            "POST",
            f"http://127.0.0.1:{server.port}/move",
            {"direction": "MoveAhead", "reason": "clear hallway continues"},
        )
        metrics = server.snapshot_metrics()

    assert metrics["observed_once"] is True
    assert metrics["moves_since_observe"] == 1
    assert metrics["tool_event_counts"]["<runtime>:watchdog"] == 1
    assert metrics["tool_event_counts"]["observe:request"] == 1
    assert metrics["tool_event_counts"]["move:request"] == 1
    assert metrics["last_trace_age_s"] >= 0.0

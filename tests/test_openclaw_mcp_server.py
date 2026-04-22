from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from unittest.mock import patch

import numpy as np
import pytest

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.openclaw.mcp_server import RoboclawsMCPServer, make_roboclaws_mcp

REFERENCE = json.loads(
    (Path(__file__).parent / "fixtures" / "trace_schema_reference.json").read_text(encoding="utf-8")
)


def _frame(color: int = 0) -> np.ndarray:
    return np.full((240, 320, 3), color, dtype=np.uint8)


@dataclass
class FakeAgentState:
    agent_id: int
    frame: np.ndarray
    position: dict[str, float]
    rotation: dict[str, float]
    camera_horizon: float
    last_action_success: bool
    last_action_error: str = ""
    visible_objects: list[dict[str, Any]] = field(default_factory=list)


class FakeEngine:
    """Minimal stand-in for MultiAgentEngine used by the MCP server tests."""

    def __init__(self) -> None:
        self.agent_count = 1
        self._fpv = _frame(10)
        self._overhead = _frame(200)
        self._chase = _frame(90)
        self.calls_step: list[tuple[int, str]] = []
        self.chase_updates = 0
        self._position = {"x": 1.0, "y": 0.0, "z": -2.0}
        self._rotation = {"x": 0.0, "y": 90.0, "z": 0.0}
        self._last_action_success = True
        self._last_action_error = ""

    def _state(self, agent_id: int) -> FakeAgentState:
        return FakeAgentState(
            agent_id=agent_id,
            frame=self._fpv,
            position=dict(self._position),
            rotation=dict(self._rotation),
            camera_horizon=30.0,
            last_action_success=self._last_action_success,
            last_action_error=self._last_action_error,
        )

    def get_agent_state(self, agent_id: int) -> FakeAgentState:
        return self._state(agent_id)

    def get_all_agent_states(self) -> list[FakeAgentState]:
        return [self._state(0)]

    def get_reachable_positions(self) -> set[tuple[int, int]]:
        return {(4, -8), (5, -8), (6, -8), (6, -7)}

    def get_overhead_frame(self) -> np.ndarray:
        return self._overhead

    def add_chase_cam(self, agent_id: int) -> int:
        return agent_id + 1

    def update_chase_cam(self, agent_id: int) -> None:
        self.chase_updates += 1

    def get_chase_cam_frame(self, agent_id: int) -> np.ndarray:
        return self._chase

    def step(self, agent_id: int, direction: str) -> FakeAgentState:
        self.calls_step.append((agent_id, direction))
        # MoveBack is used in the suite to exercise the "blocked" branch.
        success = direction != "MoveBack"
        self._last_action_success = success
        self._last_action_error = "" if success else "blocked"
        if success and direction == "MoveAhead":
            self._position["x"] = 1.25
        return self._state(agent_id)


@pytest.fixture
def engine() -> FakeEngine:
    return FakeEngine()


@pytest.fixture
def server(engine: FakeEngine, tmp_path: Path) -> RoboclawsMCPServer:
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    try:
        yield srv
    finally:
        srv.close()


@pytest.fixture
def server_map_v2_chase(engine: FakeEngine, tmp_path: Path) -> RoboclawsMCPServer:
    srv = make_roboclaws_mcp(
        engine,
        agent_id=0,
        run_dir=tmp_path,
        port=0,
        view_variant="map-v2+chase",
    )
    try:
        yield srv
    finally:
        srv.close()


def _read_trace(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / "trace.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


# ---------------------------------------------------------------------------
# Tool behavior
# ---------------------------------------------------------------------------


def test_observe_returns_state_text_plus_two_images(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    result = server._do_observe()
    assert isinstance(result, list)
    assert len(result) == 3

    # Text block first — JSON-serialized state
    state_text = result[0]
    assert isinstance(state_text, str)
    state = json.loads(state_text)
    for key in ("agent_id", "position", "rotation", "camera_horizon", "last_action_success"):
        assert key in state
    assert "human_message" in state
    assert state["view_variant"] == "baseline"
    assert state["image_labels"] == ["fpv", "overhead"]
    assert state["agent_id"] == 0

    # Two image blocks — SDK Image objects expose `.data` as bytes
    fpv, overhead = result[1], result[2]
    assert hasattr(fpv, "data") and isinstance(fpv.data, bytes) and len(fpv.data) > 0
    assert hasattr(overhead, "data") and isinstance(overhead.data, bytes) and len(overhead.data) > 0

    # Ledger marks the observe as seen
    assert server.snapshot_metrics()["observed_once"] is True


def test_observe_map_v2_chase_returns_three_images(
    server_map_v2_chase: RoboclawsMCPServer,
    engine: FakeEngine,
) -> None:
    result = server_map_v2_chase._do_observe()
    assert len(result) == 4
    state = json.loads(result[0])
    assert state["view_variant"] == "map-v2+chase"
    assert state["image_labels"] == ["fpv", "map_v2", "chase"]
    for block in result[1:]:
        assert hasattr(block, "data") and isinstance(block.data, bytes) and len(block.data) > 0
    assert engine.chase_updates == 1

    frame_capture = [
        line
        for line in _read_trace(server_map_v2_chase.run_dir)
        if line.get("event") == "frame_capture"
    ][0]
    assert frame_capture["view_variant"] == "map-v2+chase"
    assert frame_capture["image_labels"] == ["fpv", "map_v2", "chase"]
    assert "baseline_overhead" in frame_capture
    assert "chase" in frame_capture


def test_move_valid_direction_steps_engine(server: RoboclawsMCPServer, engine: FakeEngine) -> None:
    response = server._do_move("MoveAhead", "clear hallway")
    assert engine.calls_step == [(0, "MoveAhead")]
    assert response["result"] == "ok"
    assert response["state"]["last_action_success"] is True
    assert isinstance(response["step"], int)
    assert response["view_variant"] == "baseline"
    assert response["image_labels"] == ["fpv", "overhead"]


def test_move_invalid_direction_does_not_step_engine(
    server: RoboclawsMCPServer, engine: FakeEngine
) -> None:
    response = server._do_move("Jump", "why not")
    assert engine.calls_step == []
    assert response["result"] == "error"
    assert response["error"] == "invalid direction"
    assert "MoveAhead" in response["valid"]


def test_move_blocked_returns_blocked(server: RoboclawsMCPServer, engine: FakeEngine) -> None:
    response = server._do_move("MoveBack", "reverse")
    assert engine.calls_step == [(0, "MoveBack")]
    assert response["result"] == "blocked"
    assert response["state"]["last_action_success"] is False


def test_done_sets_event_and_records_reason(server: RoboclawsMCPServer) -> None:
    response = server._do_done("goal reached")
    assert server.done_event.is_set()
    assert server._done_reason == "goal reached"
    assert response["final"] is True
    assert response["reason"] == "goal reached"
    assert isinstance(response["total_moves"], int) and response["total_moves"] >= 0
    assert isinstance(response["elapsed_s"], float) and response["elapsed_s"] >= 0.0


def test_done_is_idempotent_on_reason(server: RoboclawsMCPServer) -> None:
    server._do_done("first-reason")
    response = server._do_done("second-reason-ignored")
    assert response["reason"] == "first-reason"


def test_enqueue_human_message_drains_on_observe(server: RoboclawsMCPServer) -> None:
    server.enqueue_human_message("turn left")
    result = server._do_observe()
    state = json.loads(result[0])
    assert state["human_message"] == "turn left"

    result_again = server._do_observe()
    state_again = json.loads(result_again[0])
    assert state_again["human_message"] is None


def test_human_message_queue_drains_on_move(server: RoboclawsMCPServer) -> None:
    server.enqueue_human_message("rotate please")
    response = server._do_move("RotateLeft")
    assert response["human_message"] == "rotate please"


# ---------------------------------------------------------------------------
# Reference-fixture contract
# ---------------------------------------------------------------------------


def test_snapshot_metrics_keys_equal_reference(server: RoboclawsMCPServer) -> None:
    metrics = server.snapshot_metrics()
    # EQUALITY, not superset. snapshot_metrics is frozen tight because
    # run_result_json["sim_server_metrics"] consumers depend on the exact keyset.
    assert set(metrics.keys()) == set(REFERENCE["snapshot_metrics"]["required_keys"])


def test_trace_payload_is_superset_of_reference_required(server: RoboclawsMCPServer) -> None:
    server._do_observe()
    server._do_move("MoveAhead", "clear hallway")
    server._do_done("goal")
    lines = _read_trace(server.run_dir)
    assert lines, "expected at least one trace line after observe+move+done"
    required = set(REFERENCE["trace_payload"]["required_keys"])
    for line in lines:
        assert required.issubset(set(line.keys())), (
            f"trace line missing required keys: {required - set(line.keys())}"
        )


def test_frame_capture_payload_is_superset_of_reference_required(
    server: RoboclawsMCPServer,
) -> None:
    server._do_observe()
    server._do_move("MoveAhead", "clear hallway")
    frame_lines = [
        line for line in _read_trace(server.run_dir) if line.get("event") == "frame_capture"
    ]
    assert len(frame_lines) >= 2
    required = set(REFERENCE["frame_capture_payload"]["required_keys"])
    for line in frame_lines:
        assert required.issubset(set(line.keys())), (
            f"frame_capture missing required keys: {required - set(line.keys())}"
        )


def test_trace_jsonl_contains_tool_events(server: RoboclawsMCPServer) -> None:
    server._do_observe()
    server._do_move("MoveAhead")
    server._do_done("done-reason")
    events = {(line["tool"], line["event"]) for line in _read_trace(server.run_dir)}
    assert {
        ("observe", "request"),
        ("observe", "response"),
        ("move", "request"),
        ("move", "response"),
        ("done", "request"),
        ("done", "response"),
    }.issubset(events)


# ---------------------------------------------------------------------------
# Factory / binding defaults
# ---------------------------------------------------------------------------


def test_factory_defaults_to_localhost_binding(tmp_path: Path) -> None:
    """Threat model T-02.6-01: host defaults to 127.0.0.1, not 0.0.0.0."""
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    try:
        assert srv.host == "127.0.0.1"
    finally:
        srv.close()


def test_navigation_actions_includes_expected(server: RoboclawsMCPServer) -> None:
    # Sanity check on the constant the move tool validates against.
    assert "MoveAhead" in NAVIGATION_ACTIONS
    assert "RotateLeft" in NAVIGATION_ACTIONS


# ---------------------------------------------------------------------------
# Thread-safety: close() vs concurrent trace writers (WR-01 regression guard)
# ---------------------------------------------------------------------------


def test_write_trace_after_close_is_safe(tmp_path: Path) -> None:
    """WR-01: write_runtime_event after close() must not raise.

    In production the watchdog + stdin threads in
    examples/openclaw_nav_autonomous.py join with a 0.2s timeout, so
    close() can race with a writer that's already called `snapshot_metrics`
    and is about to call `write_runtime_event`. Pre-fix this raised
    `ValueError: I/O operation on closed file.` Post-fix it's a silent
    no-op.
    """
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=0)
    srv._do_observe()
    srv.close()
    # Must not raise; must not re-open the file.
    srv.write_runtime_event("watchdog", metrics={"x": 1})
    srv.enqueue_human_message("post-close message")
    # Calling close() again is idempotent.
    srv.close()


def test_run_in_thread_raises_when_server_dies_before_listening(tmp_path: Path) -> None:
    engine = FakeEngine()
    srv = make_roboclaws_mcp(engine, agent_id=0, run_dir=tmp_path, port=18788)
    try:
        with patch.object(srv._mcp, "run", return_value=None), patch(
            "roboclaws.openclaw.mcp_server._port_accepting",
            return_value=False,
        ):
            with pytest.raises(RuntimeError, match="failed to start"):
                srv.run_in_thread()
    finally:
        srv.close()

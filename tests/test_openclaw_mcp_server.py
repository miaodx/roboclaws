from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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
        self._fpv = _frame(10)
        self._overhead = _frame(200)
        self.calls_step: list[tuple[int, str]] = []

    def get_agent_state(self, agent_id: int) -> FakeAgentState:
        return FakeAgentState(
            agent_id=agent_id,
            frame=self._fpv,
            position={"x": 1.0, "y": 0.0, "z": -2.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            camera_horizon=30.0,
            last_action_success=True,
            last_action_error="",
        )

    def get_overhead_frame(self) -> np.ndarray:
        return self._overhead

    def step(self, agent_id: int, direction: str) -> FakeAgentState:
        self.calls_step.append((agent_id, direction))
        # MoveBack is used in the suite to exercise the "blocked" branch.
        success = direction != "MoveBack"
        return FakeAgentState(
            agent_id=agent_id,
            frame=self._fpv,
            position={"x": 1.25, "y": 0.0, "z": -2.0},
            rotation={"x": 0.0, "y": 90.0, "z": 0.0},
            camera_horizon=30.0,
            last_action_success=success,
            last_action_error="" if success else "blocked",
        )


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
    assert state["agent_id"] == 0

    # Two image blocks — SDK Image objects expose `.data` as bytes
    fpv, overhead = result[1], result[2]
    assert hasattr(fpv, "data") and isinstance(fpv.data, bytes) and len(fpv.data) > 0
    assert hasattr(overhead, "data") and isinstance(overhead.data, bytes) and len(overhead.data) > 0

    # Ledger marks the observe as seen
    assert server.snapshot_metrics()["observed_once"] is True


def test_move_valid_direction_steps_engine(server: RoboclawsMCPServer, engine: FakeEngine) -> None:
    response = server._do_move("MoveAhead", "clear hallway")
    assert engine.calls_step == [(0, "MoveAhead")]
    assert response["result"] == "ok"
    assert response["state"]["last_action_success"] is True
    assert isinstance(response["step"], int)


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
    tools = {line["tool"] for line in _read_trace(server.run_dir)}
    assert {"observe", "move", "done"}.issubset(tools)


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

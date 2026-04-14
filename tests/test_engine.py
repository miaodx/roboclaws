from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from roboclaws.core.engine import NAVIGATION_ACTIONS, AgentState, MultiAgentEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FRAME_SHAPE = (480, 640, 3)


def _make_agent_event(agent_id: int) -> MagicMock:
    """Build a mock AI2-THOR per-agent event."""
    evt = MagicMock()
    evt.frame = np.zeros(FRAME_SHAPE, dtype=np.uint8)
    evt.third_party_camera_frames = [np.ones(FRAME_SHAPE, dtype=np.uint8) * 128]
    evt.metadata = {
        "agent": {
            "position": {"x": float(agent_id), "y": 0.0, "z": 0.0},
            "rotation": {"x": 0.0, "y": 0.0, "z": 0.0},
            "cameraHorizon": 0.0,
        },
        "objects": [
            {"visible": True, "name": f"Chair_{agent_id}"},
            {"visible": False, "name": f"Table_{agent_id}"},
        ],
        "lastActionSuccess": True,
        "errorMessage": "",
    }
    return evt


def _make_event(agent_count: int = 2) -> MagicMock:
    """Build a mock AI2-THOR multi-agent event."""
    evt = MagicMock()
    evt.events = [_make_agent_event(i) for i in range(agent_count)]
    evt.metadata = {
        "actionReturn": {
            "position": {"x": 0.0, "y": 3.0, "z": 0.0},
            "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
        },
        "lastActionSuccess": True,
    }
    return evt


@pytest.fixture()
def mock_ctrl(agent_count: int = 2):
    """Patch ai2thor.Controller; yield the mock instance."""
    with patch("roboclaws.core.engine.Controller") as MockCls:
        inst = MockCls.return_value
        evt = _make_event(agent_count=agent_count)
        inst.last_event = evt
        inst.step.return_value = evt
        yield inst


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def test_controller_created_with_correct_kwargs(mock_ctrl):
    with patch("roboclaws.core.engine.Controller") as MockCls:
        MockCls.return_value = mock_ctrl
        MultiAgentEngine(scene="FloorPlan205", agent_count=3, grid_size=0.5)
    MockCls.assert_called_once_with(
        scene="FloorPlan205",
        agentCount=3,
        gridSize=0.5,
        snapToGrid=True,
        rotateStepDegrees=90,
        fieldOfView=90,
        width=640,
        height=480,
    )


def test_overhead_camera_setup_on_init(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    calls = [str(c) for c in mock_ctrl.step.call_args_list]
    assert any("GetMapViewCameraProperties" in c for c in calls)
    assert any("AddThirdPartyCamera" in c for c in calls)
    assert engine.agent_count == 2


# ---------------------------------------------------------------------------
# get_agent_state
# ---------------------------------------------------------------------------


def test_get_agent_state_returns_dataclass(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    state = engine.get_agent_state(0)
    assert isinstance(state, AgentState)


def test_get_agent_state_frame_shape(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    for agent_id in range(2):
        state = engine.get_agent_state(agent_id)
        assert isinstance(state.frame, np.ndarray)
        assert state.frame.shape == FRAME_SHAPE
        assert state.frame.dtype == np.uint8


def test_get_agent_state_metadata(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    state = engine.get_agent_state(1)
    assert state.agent_id == 1
    assert state.position == {"x": 1.0, "y": 0.0, "z": 0.0}
    assert state.rotation == {"x": 0.0, "y": 0.0, "z": 0.0}
    assert state.camera_horizon == 0.0
    assert state.last_action_success is True
    assert state.last_action_error == ""


def test_get_agent_state_filters_visible_objects(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    state = engine.get_agent_state(0)
    # Only 1 visible object in the mock (Chair_0); Table_0 is not visible
    assert len(state.visible_objects) == 1
    assert state.visible_objects[0]["name"] == "Chair_0"


# ---------------------------------------------------------------------------
# get_all_agent_states
# ---------------------------------------------------------------------------


def test_get_all_agent_states_length(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    states = engine.get_all_agent_states()
    assert len(states) == 2
    for i, s in enumerate(states):
        assert s.agent_id == i


# ---------------------------------------------------------------------------
# step
# ---------------------------------------------------------------------------


def test_step_calls_controller_with_agent_id(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    mock_ctrl.step.reset_mock()  # clear setup calls
    engine.step(agent_id=1, action="MoveAhead")
    mock_ctrl.step.assert_called_once_with(action="MoveAhead", agentId=1)


def test_step_returns_agent_state(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    state = engine.step(agent_id=0, action="RotateLeft")
    assert isinstance(state, AgentState)
    assert state.last_action_success is True


def test_step_forwards_extra_kwargs(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    mock_ctrl.step.reset_mock()
    engine.step(agent_id=0, action="Teleport", position={"x": 1.0, "y": 0.0, "z": 1.0})
    mock_ctrl.step.assert_called_once_with(
        action="Teleport", agentId=0, position={"x": 1.0, "y": 0.0, "z": 1.0}
    )


def test_step_handles_action_failure(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    fail_evt = _make_event(agent_count=2)
    fail_evt.events[0].metadata["lastActionSuccess"] = False
    fail_evt.events[0].metadata["errorMessage"] = "Object blocking agent's path"
    mock_ctrl.step.return_value = fail_evt
    state = engine.step(agent_id=0, action="MoveAhead")
    assert state.last_action_success is False
    assert "blocking" in state.last_action_error


# ---------------------------------------------------------------------------
# get_overhead_frame
# ---------------------------------------------------------------------------


def test_get_overhead_frame_returns_array(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    frame = engine.get_overhead_frame()
    assert isinstance(frame, np.ndarray)
    assert frame.shape == FRAME_SHAPE


def test_get_overhead_frame_is_nonzero(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    frame = engine.get_overhead_frame()
    # Mock overhead frame is all-128; ensure it is not empty
    assert frame.max() > 0


# ---------------------------------------------------------------------------
# get_reachable_positions
# ---------------------------------------------------------------------------


def test_get_reachable_positions_returns_set(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    reachable_evt = _make_event(agent_count=2)
    reachable_evt.metadata["actionReturn"] = [
        {"x": 0.0, "y": 0.0, "z": 0.0},
        {"x": 0.25, "y": 0.0, "z": 0.0},
        {"x": 0.0, "y": 0.0, "z": 0.25},
    ]
    mock_ctrl.step.return_value = reachable_evt
    result = engine.get_reachable_positions()
    assert isinstance(result, set)
    assert (0, 0) in result
    assert (1, 0) in result
    assert (0, 1) in result
    assert len(result) == 3


def test_get_reachable_positions_cached(mock_ctrl):
    """Second call returns cached set without re-calling the controller."""
    engine = MultiAgentEngine(agent_count=2)
    reachable_evt = _make_event(agent_count=2)
    reachable_evt.metadata["actionReturn"] = [{"x": 0.0, "y": 0.0, "z": 0.0}]
    mock_ctrl.step.return_value = reachable_evt
    mock_ctrl.step.reset_mock()

    result1 = engine.get_reachable_positions()
    result2 = engine.get_reachable_positions()

    assert result1 is result2  # same object (cached)
    # GetReachablePositions should have been called only once
    calls = [str(c) for c in mock_ctrl.step.call_args_list]
    assert sum(1 for c in calls if "GetReachablePositions" in c) == 1


def test_get_reachable_positions_grid_projection(mock_ctrl):
    """Positions are projected to grid indices using round(x / grid_size)."""
    engine = MultiAgentEngine(agent_count=2, grid_size=0.25)
    reachable_evt = _make_event(agent_count=2)
    reachable_evt.metadata["actionReturn"] = [
        {"x": 0.50, "y": 0.0, "z": 0.75},  # → (2, 3)
        {"x": -0.25, "y": 0.0, "z": 0.0},  # → (-1, 0)
    ]
    mock_ctrl.step.return_value = reachable_evt
    result = engine.get_reachable_positions()
    assert (2, 3) in result
    assert (-1, 0) in result


def test_get_reachable_positions_empty_scene(mock_ctrl):
    """When actionReturn is empty or None, result is an empty set."""
    engine = MultiAgentEngine(agent_count=2)
    reachable_evt = _make_event(agent_count=2)
    reachable_evt.metadata["actionReturn"] = []
    mock_ctrl.step.return_value = reachable_evt
    result = engine.get_reachable_positions()
    assert result == set()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


def test_close_stops_controller(mock_ctrl):
    engine = MultiAgentEngine(agent_count=2)
    engine.close()
    mock_ctrl.stop.assert_called_once()


# ---------------------------------------------------------------------------
# NAVIGATION_ACTIONS constant
# ---------------------------------------------------------------------------


def test_navigation_actions_content():
    required = {"MoveAhead", "MoveBack", "RotateLeft", "RotateRight", "Done"}
    assert required.issubset(set(NAVIGATION_ACTIONS))


def test_navigation_actions_all_strings():
    assert all(isinstance(a, str) for a in NAVIGATION_ACTIONS)

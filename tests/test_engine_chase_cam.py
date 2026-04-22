from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from roboclaws.core.engine import MultiAgentEngine

FRAME_SHAPE = (48, 64, 3)


def _make_agent_event(agent_id: int, *, yaw: float = 0.0) -> MagicMock:
    evt = MagicMock()
    evt.frame = np.zeros(FRAME_SHAPE, dtype=np.uint8)
    evt.third_party_camera_frames = []
    evt.metadata = {
        "agent": {
            "position": {"x": float(agent_id), "y": 0.9, "z": 2.0},
            "rotation": {"x": 0.0, "y": yaw, "z": 0.0},
            "cameraHorizon": 0.0,
        },
        "objects": [],
        "lastActionSuccess": True,
        "errorMessage": "",
    }
    return evt


def _make_event(*, yaw: float = 0.0, agent_count: int = 2) -> MagicMock:
    evt = MagicMock()
    evt.events = [_make_agent_event(i, yaw=yaw) for i in range(agent_count)]
    evt.metadata = {
        "actionReturn": {
            "position": {"x": 0.0, "y": 3.0, "z": 0.0},
            "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
        },
        "lastActionSuccess": True,
    }
    return evt


@pytest.fixture()
def mock_ctrl():
    with patch("roboclaws.core.engine.Controller") as MockCls:
        inst = MockCls.return_value
        state = {"evt": _make_event()}
        inst.last_event = state["evt"]

        def step_side_effect(*, action: str, **kwargs):
            if action == "AddThirdPartyCamera":
                for agent_evt in state["evt"].events:
                    value = 64 if len(agent_evt.third_party_camera_frames) == 0 else 128
                    agent_evt.third_party_camera_frames.append(
                        np.full(FRAME_SHAPE, value, dtype=np.uint8)
                    )
            inst.last_event = state["evt"]
            return state["evt"]

        inst.step.side_effect = step_side_effect
        inst._test_state = state
        yield inst


def test_add_chase_cam_returns_stable_index(mock_ctrl) -> None:
    engine = MultiAgentEngine(agent_count=2)
    camera_id = engine.add_chase_cam(agent_id=1)
    assert camera_id == 1
    assert engine.add_chase_cam(agent_id=1) == 1


@pytest.mark.parametrize(
    ("yaw", "expected_x", "expected_z"),
    [
        (0.0, 0.0, 1.0),
        (90.0, -1.0, 2.0),
        (180.0, 0.0, 3.0),
        (270.0, 1.0, 2.0),
    ],
)
def test_update_chase_cam_uses_heading_rotated_offset(
    mock_ctrl, yaw: float, expected_x: float, expected_z: float
) -> None:
    mock_ctrl._test_state["evt"] = _make_event(yaw=yaw)
    mock_ctrl.last_event = mock_ctrl._test_state["evt"]
    engine = MultiAgentEngine(agent_count=2)
    engine._last_event = mock_ctrl.last_event
    engine.add_chase_cam(agent_id=0)
    mock_ctrl.step.reset_mock()

    engine.update_chase_cam(agent_id=0)

    mock_ctrl.step.assert_called_once()
    kwargs = mock_ctrl.step.call_args.kwargs
    assert kwargs["action"] == "UpdateThirdPartyCamera"
    assert kwargs["thirdPartyCameraId"] == 1
    assert kwargs["rotation"] == {"x": 20.0, "y": yaw, "z": 0.0}
    assert kwargs["position"]["x"] == pytest.approx(expected_x)
    assert kwargs["position"]["y"] == pytest.approx(2.4)
    assert kwargs["position"]["z"] == pytest.approx(expected_z)


def test_get_chase_cam_frame_returns_registered_camera_frame(mock_ctrl) -> None:
    engine = MultiAgentEngine(agent_count=2)
    engine.add_chase_cam(agent_id=0)
    frame = engine.get_chase_cam_frame(agent_id=0)
    assert isinstance(frame, np.ndarray)
    assert frame.shape == FRAME_SHAPE
    assert int(frame[0, 0, 0]) == 128

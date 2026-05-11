from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np

from roboclaws.core.engine import AgentState

GRID_SIZE = 0.25
FRAME_SHAPE = (480, 640, 3)
EXAMPLE_FRAME_SHAPE = (48, 64, 3)


def make_frame(
    value: int = 0,
    *,
    shape: tuple[int, int, int] = FRAME_SHAPE,
) -> np.ndarray:
    return np.full(shape, value, dtype=np.uint8)


def make_example_frame(value: int = 128) -> np.ndarray:
    return make_frame(value, shape=EXAMPLE_FRAME_SHAPE)


def make_agent_state(
    agent_id: int,
    *,
    x: float = 0.0,
    y: float = 0.0,
    z: float = 0.0,
    success: bool = True,
    rotation_y: float = 0.0,
    frame_shape: tuple[int, int, int] = FRAME_SHAPE,
    frame_value: int = 0,
    visible_objects: list[dict[str, object]] | None = None,
) -> AgentState:
    return AgentState(
        agent_id=agent_id,
        frame=make_frame(frame_value, shape=frame_shape),
        position={"x": x, "y": y, "z": z},
        rotation={"x": 0.0, "y": rotation_y, "z": 0.0},
        camera_horizon=0.0,
        visible_objects=list(visible_objects or []),
        last_action_success=success,
        last_action_error="" if success else "Object blocking agent path",
    )


def make_example_agent_state(
    agent_id: int,
    *,
    x: float = 0.0,
    z: float = 0.0,
) -> AgentState:
    return make_agent_state(
        agent_id,
        x=x,
        y=0.9,
        z=z,
        frame_shape=EXAMPLE_FRAME_SHAPE,
        frame_value=128,
    )


def make_mock_engine(
    *,
    agent_count: int = 2,
    grid_size: float = GRID_SIZE,
    field_of_view: int = 90,
) -> MagicMock:
    engine = MagicMock()
    engine.agent_count = agent_count
    engine.field_of_view = field_of_view
    engine.get_all_agent_states.return_value = [
        make_agent_state(i, x=i * grid_size) for i in range(agent_count)
    ]
    engine.step.side_effect = lambda agent_id, action, **kw: make_agent_state(
        agent_id,
        x=agent_id * grid_size,
    )
    engine.get_agent_state.side_effect = lambda agent_id: make_agent_state(
        agent_id,
        x=agent_id * grid_size,
    )
    return engine


def configure_example_engine_instance(
    engine: MagicMock,
    *,
    agent_count: int = 2,
    grid_size: float = GRID_SIZE,
    reachable_size: int = 20,
) -> list[AgentState]:
    engine.agent_count = agent_count
    states = [make_example_agent_state(i, x=i * grid_size) for i in range(agent_count)]
    engine.get_all_agent_states.return_value = states
    engine.get_overhead_frame.return_value = make_example_frame(80)
    engine.get_agent_state.side_effect = lambda aid: states[aid]
    engine.step.side_effect = lambda agent_id, action, **kw: states[agent_id]
    engine.add_chase_cam.return_value = 0
    engine.update_chase_cam.return_value = None
    engine.get_chase_cam_frame.return_value = make_example_frame(60)
    engine.get_reachable_positions.return_value = {
        (i, j) for i in range(reachable_size) for j in range(reachable_size)
    }
    return states

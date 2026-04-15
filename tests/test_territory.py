from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from roboclaws.core.engine import AgentState
from roboclaws.core.vlm import MockProvider
from roboclaws.games.territory import (
    TerritoryGame,
    TerritoryResult,
    _largest_connected_component,
    _pos_to_cell,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

GRID_SIZE = 0.25
FRAME_SHAPE = (480, 640, 3)


def _state(agent_id: int, x: float = 0.0, z: float = 0.0, success: bool = True) -> AgentState:
    return AgentState(
        agent_id=agent_id,
        frame=np.zeros(FRAME_SHAPE, dtype=np.uint8),
        position={"x": x, "y": 0.0, "z": z},
        rotation={"x": 0.0, "y": 0.0, "z": 0.0},
        camera_horizon=0.0,
        last_action_success=success,
        last_action_error="" if success else "Object blocking agent path",
    )


def _make_engine(agent_count: int = 2) -> MagicMock:
    """Return a mock MultiAgentEngine with two agents at distinct starting cells."""
    engine = MagicMock()
    engine.agent_count = agent_count
    # Agent i starts at x = i * GRID_SIZE
    engine.get_all_agent_states.return_value = [
        _state(i, x=i * GRID_SIZE) for i in range(agent_count)
    ]
    # step() returns the agent back at its original position by default
    engine.step.side_effect = lambda agent_id, action, **kw: _state(
        agent_id, x=agent_id * GRID_SIZE
    )
    engine.get_agent_state.side_effect = lambda agent_id: _state(agent_id, x=agent_id * GRID_SIZE)
    return engine


# ---------------------------------------------------------------------------
# _pos_to_cell
# ---------------------------------------------------------------------------


def test_pos_to_cell_origin():
    assert _pos_to_cell({"x": 0.0, "y": 0.0, "z": 0.0}, GRID_SIZE) == (0, 0)


def test_pos_to_cell_positive():
    assert _pos_to_cell({"x": 0.25, "y": 0.0, "z": 0.50}, GRID_SIZE) == (1, 2)


def test_pos_to_cell_negative():
    assert _pos_to_cell({"x": -0.25, "y": 0.0, "z": 0.0}, GRID_SIZE) == (-1, 0)


def test_pos_to_cell_rounds_to_nearest():
    # 0.13 / 0.25 = 0.52 → rounds to 1
    assert _pos_to_cell({"x": 0.13, "y": 0.0, "z": 0.0}, GRID_SIZE) == (1, 0)


# ---------------------------------------------------------------------------
# _largest_connected_component
# ---------------------------------------------------------------------------


def test_lcc_empty():
    assert _largest_connected_component(set()) == 0


def test_lcc_single_cell():
    assert _largest_connected_component({(0, 0)}) == 1


def test_lcc_line():
    cells = {(0, 0), (1, 0), (2, 0)}
    assert _largest_connected_component(cells) == 3


def test_lcc_disconnected():
    # Two isolated cells — largest component is 1
    assert _largest_connected_component({(0, 0), (5, 5)}) == 1


def test_lcc_two_equal_components():
    # Two separated pairs
    cells = {(0, 0), (1, 0), (10, 0), (11, 0)}
    assert _largest_connected_component(cells) == 2


def test_lcc_l_shape():
    cells = {(0, 0), (1, 0), (2, 0), (2, 1)}
    assert _largest_connected_component(cells) == 4


# ---------------------------------------------------------------------------
# TerritoryGame initialisation
# ---------------------------------------------------------------------------


def test_initial_positions_claimed():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    scores = game.get_scores()
    assert scores[0] >= 1
    assert scores[1] >= 1


def test_initial_total_claimed_equals_agents_when_distinct():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert len(game._claimed) == 2  # two distinct starting cells


def test_no_double_claiming_same_start():
    """When two agents share a starting position, only the first claimer wins."""
    engine = _make_engine(agent_count=2)
    engine.get_all_agent_states.return_value = [
        _state(0, x=0.0),
        _state(1, x=0.0),  # same cell as agent 0
    ]
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    # Cell (0, 0) must belong to agent 0
    assert game._claimed[(0, 0)] == 0
    assert (0, 0) not in game._agent_cells[1]
    # Only one unique cell has been claimed
    assert len(game._claimed) == 1


def test_three_agents_distinct_start():
    engine = _make_engine(agent_count=3)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert len(game._claimed) == 3
    for i in range(3):
        assert game._agent_cells[i]


# ---------------------------------------------------------------------------
# Round-robin stepping
# ---------------------------------------------------------------------------


def test_round_robin_two_agents():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    assert game._current_agent == 0
    game.step()
    assert game._current_agent == 1
    game.step()
    assert game._current_agent == 0


def test_round_robin_three_agents():
    engine = _make_engine(agent_count=3)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    # Check one full round (0 → 1 → 2 → wraps to 0)
    for expected in [0, 1, 2]:
        assert game._current_agent == expected
        game.step()
    assert game._current_agent == 0


# ---------------------------------------------------------------------------
# Blocking event detection
# ---------------------------------------------------------------------------


def test_blocking_event_counted_on_failed_move():
    engine = _make_engine(agent_count=2)
    # side_effect takes precedence over return_value, so set it directly
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, success=False)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    # Force a MoveAhead
    with patch.object(game.provider, "get_action", return_value={"action": "MoveAhead"}):
        game.step()
    assert game._blocking_events == 1


def test_failed_rotation_not_counted_as_blocking():
    engine = _make_engine(agent_count=2)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, success=False)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    # RotateLeft is not a movement action
    with patch.object(game.provider, "get_action", return_value={"action": "RotateLeft"}):
        game.step()
    assert game._blocking_events == 0


def test_blocking_event_increments_each_failed_move():
    engine = _make_engine(agent_count=2)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, success=False)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    with patch.object(game.provider, "get_action", return_value={"action": "MoveAhead"}):
        game.step()
        game.step()
    assert game._blocking_events == 2


def test_invalid_action_falls_back_to_rotate_right():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    with patch.object(game.provider, "get_action", return_value={"action": "Teleport"}):
        game.step()
    engine.step.assert_called_once()
    assert engine.step.call_args.kwargs["action"] == "RotateRight"


def test_failed_move_allows_different_escape_move():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    game._last_action_by_agent[0] = "MoveAhead"
    engine.get_agent_state.side_effect = lambda agent_id: _state(agent_id, success=False)
    with patch.object(game.provider, "get_action", return_value={"action": "MoveLeft"}):
        game.step()
    engine.step.assert_called_once()
    assert engine.step.call_args.kwargs["action"] == "MoveLeft"


# ---------------------------------------------------------------------------
# State consistency
# ---------------------------------------------------------------------------


def test_no_cell_double_claimed():
    """A cell must never appear in two agents' cell sets."""
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE, z=0.0)

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    game.run()

    all_cells = []
    for cells in game._agent_cells.values():
        all_cells.extend(cells)
    assert len(all_cells) == len(set(all_cells)), "A cell is owned by more than one agent"


def test_claimed_dict_consistent_with_agent_cells():
    """_claimed and _agent_cells must agree on ownership for every cell."""
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    game.run()

    for cell, owner in game._claimed.items():
        assert cell in game._agent_cells[owner]


# ---------------------------------------------------------------------------
# Termination
# ---------------------------------------------------------------------------


def test_terminates_at_max_steps():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        # Return unique z so new cells keep being discovered (stale_steps stays 0)
        return _state(agent_id, x=0.0, z=float(counter[0]))

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    result = game.run()
    assert result.total_steps == 4
    assert result.termination_reason == "max_steps"


def test_terminates_when_all_cells_claimed():
    """With a fixed mock (agents always revisit same cells), game ends early."""
    engine = _make_engine(agent_count=2)
    # step() always returns the agent's own starting cell → no new claims ever
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=100)
    result = game.run()
    assert result.termination_reason == "all_cells_claimed"
    assert result.total_steps < 100


def test_is_over_false_initially():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=50)
    assert not game.is_over()


def test_step_returns_false_when_over():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=1)
    game.step()  # consumes the only step
    assert game.is_over()
    assert game.step() is False


# ---------------------------------------------------------------------------
# get_state
# ---------------------------------------------------------------------------


def test_get_state_structure():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    state = game.get_state()
    assert state["game"] == "territory"
    assert "step" in state
    assert "remaining_steps" in state
    assert "agents" in state
    assert 0 in state["agents"]
    assert 1 in state["agents"]
    assert "cells_claimed" in state["agents"][0]


def test_get_state_remaining_steps_decrements():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    remaining_before = game.get_state()["remaining_steps"]
    game.step()
    remaining_after = game.get_state()["remaining_steps"]
    assert remaining_after == remaining_before - 1


def test_get_prompt_state_includes_available_actions():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    prompt_state = game.get_prompt_state()
    assert prompt_state["my_agent_id"] == 0
    assert prompt_state["available_actions"]
    assert "stale_steps" in prompt_state


# ---------------------------------------------------------------------------
# get_result / TerritoryResult
# ---------------------------------------------------------------------------


def test_get_result_returns_dataclass():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    game.run()
    result = game.get_result()
    assert isinstance(result, TerritoryResult)


def test_get_result_has_all_agents():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    game.run()
    result = game.get_result()
    assert 0 in result.cells_claimed
    assert 1 in result.cells_claimed
    assert 0 in result.connectivity_ratio
    assert 1 in result.connectivity_ratio


def test_connectivity_ratio_bounds():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    result = game.run()
    for ratio in result.connectivity_ratio.values():
        assert 0.0 <= ratio <= 1.0


def test_connectivity_ratio_fully_connected():
    """When all an agent's cells form one connected chain, ratio == 1.0."""
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]

    step_counter = [0]

    def step_fn(agent_id, action, **kw):
        step_counter[0] += 1
        # Cells (0,0) (1,0) (2,0) (3,0) — a single row, fully connected
        return _state(0, x=step_counter[0] * GRID_SIZE, z=0.0)

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    game.run()
    result = game.get_result()
    assert result.connectivity_ratio[0] == pytest.approx(1.0)


def test_get_scores_sums_match_total_claimed():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    game.run()
    assert sum(game.get_scores().values()) == len(game._claimed)


# ---------------------------------------------------------------------------
# run() end-to-end with MockProvider
# ---------------------------------------------------------------------------


def test_run_completes_without_error():
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=42), grid_size=GRID_SIZE, max_steps=10)
    result = game.run()
    assert result.termination_reason in ("max_steps", "all_cells_claimed")


def test_run_three_agents():
    engine = _make_engine(agent_count=3)
    game = TerritoryGame(engine, MockProvider(seed=7), grid_size=GRID_SIZE, max_steps=15)
    result = game.run()
    assert len(result.cells_claimed) == 3
    assert result.total_steps <= 15


def test_run_blocking_events_in_result():
    engine = _make_engine(agent_count=2)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, success=False)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=6)
    with patch.object(game.provider, "get_action", return_value={"action": "MoveAhead"}):
        result = game.run()
    assert result.blocking_events > 0


# ---------------------------------------------------------------------------
# reachable_cells ground truth
# ---------------------------------------------------------------------------


def test_reachable_cells_terminates_all_claimed():
    """Game ends with 'all_cells_claimed' when every reachable cell is taken."""
    engine = _make_engine(agent_count=2)
    # Only two reachable cells — already claimed at init (agents start there)
    reachable = {(0, 0), (1, 0)}
    game = TerritoryGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=100,
        reachable_cells=reachable,
    )
    result = game.run()
    assert result.termination_reason == "all_cells_claimed"
    assert result.total_steps < 100


def test_reachable_cells_terminates_stale():
    """Game ends with 'stale' when agents cannot reach new reachable cells."""
    engine = _make_engine(agent_count=2)
    # Large reachable set; agents stay put → stale for 2 * agent_count steps
    reachable = {(i, j) for i in range(10) for j in range(10)}
    game = TerritoryGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=100,
        reachable_cells=reachable,
    )
    result = game.run()
    assert result.termination_reason == "stale"
    assert result.total_steps == 2 * engine.agent_count  # stale threshold


def test_reachable_cells_state_includes_total_reachable():
    """get_state() exposes total_reachable when reachable_cells is provided."""
    engine = _make_engine(agent_count=2)
    reachable = {(0, 0), (1, 0), (2, 0)}
    game = TerritoryGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells=reachable,
    )
    state = game.get_state()
    assert "total_reachable" in state
    assert state["total_reachable"] == 3


def test_no_reachable_cells_state_excludes_total_reachable():
    """get_state() omits total_reachable when reachable_cells is None."""
    engine = _make_engine(agent_count=2)
    game = TerritoryGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    state = game.get_state()
    assert "total_reachable" not in state


def test_reachable_cells_result_reason_max_steps_takes_priority():
    """'max_steps' is reported when step limit is hit even with reachable_cells set."""
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    # Large reachable set; agents keep moving to new cells → no stale
    reachable = {(i, 0) for i in range(1000)}
    game = TerritoryGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=4,
        reachable_cells=reachable,
    )
    result = game.run()
    assert result.termination_reason == "max_steps"
    assert result.total_steps == 4

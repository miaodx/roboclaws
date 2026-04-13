from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from roboclaws.core.engine import AgentState
from roboclaws.core.vlm import MockProvider

from roboclaws.games.coverage import CoverageGame, CoverageResult, _pos_to_cell

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
    """Return a mock MultiAgentEngine with agents at distinct starting cells."""
    engine = MagicMock()
    engine.agent_count = agent_count
    # Agent i starts at x = i * GRID_SIZE
    engine.get_all_agent_states.return_value = [
        _state(i, x=i * GRID_SIZE) for i in range(agent_count)
    ]
    # step() returns the agent at its starting position by default
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


# ---------------------------------------------------------------------------
# CoverageGame initialisation
# ---------------------------------------------------------------------------


def test_initial_positions_covered():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert game.cells_covered() >= 1


def test_initial_two_distinct_agents_covered():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert game.cells_covered() == 2


def test_initial_same_start_single_cell():
    """When two agents start on the same cell, only one cell is covered."""
    engine = _make_engine(agent_count=2)
    engine.get_all_agent_states.return_value = [
        _state(0, x=0.0),
        _state(1, x=0.0),
    ]
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert game.cells_covered() == 1
    # Only agent 0 gets credit (first visitor)
    assert game._contribution[0] == 1
    assert game._contribution[1] == 0


def test_three_agents_distinct_start():
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert game.cells_covered() == 3
    for i in range(3):
        assert game._contribution[i] == 1


# ---------------------------------------------------------------------------
# Coverage monotonicity
# ---------------------------------------------------------------------------


def test_coverage_increases_monotonically():
    """Covered cell count must never decrease over time."""
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    prev = game.cells_covered()
    while not game.is_over():
        game.step()
        assert game.cells_covered() >= prev
        prev = game.cells_covered()


# ---------------------------------------------------------------------------
# Round-robin stepping
# ---------------------------------------------------------------------------


def test_round_robin_two_agents():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    assert game._current_agent == 0
    game.step()
    assert game._current_agent == 1
    game.step()
    assert game._current_agent == 0


def test_round_robin_three_agents():
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    for expected in [0, 1, 2]:
        assert game._current_agent == expected
        game.step()
    assert game._current_agent == 0


# ---------------------------------------------------------------------------
# Termination
# ---------------------------------------------------------------------------


def test_terminates_at_max_steps():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    result = game.run()
    assert result.total_steps == 4
    assert result.termination_reason == "max_steps"


def test_terminates_at_coverage_target():
    """When total_cells is small, game should terminate once coverage_fraction >= 0.95."""
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    step_counter = [0]

    def step_fn(agent_id, action, **kw):
        step_counter[0] += 1
        # Each step visits a new unique cell
        return _state(0, x=step_counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    # total_cells=10; we start with 1 covered, need ≥9.5 → ≥10 to hit 95%
    game = CoverageGame(
        engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=200, total_cells=10
    )
    result = game.run()
    assert result.termination_reason == "coverage_reached"
    assert result.total_steps < 200


def test_is_over_false_initially():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=50)
    assert not game.is_over()


def test_step_returns_false_when_over():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=1)
    game.step()
    assert game.is_over()
    assert game.step() is False


def test_no_coverage_termination_without_total_cells():
    """Without total_cells, the game never terminates due to coverage threshold."""
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(0, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    result = game.run()
    assert result.termination_reason == "max_steps"


# ---------------------------------------------------------------------------
# Failed actions do not extend coverage
# ---------------------------------------------------------------------------


def test_failed_action_does_not_cover_new_cell():
    engine = _make_engine(agent_count=2)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, x=99.0, success=False)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    covered_before = game.cells_covered()
    with patch.object(game.provider, "get_action", return_value={"action": "MoveAhead"}):
        game.step()
    # failed step should not add coverage
    assert game.cells_covered() == covered_before


# ---------------------------------------------------------------------------
# get_state
# ---------------------------------------------------------------------------


def test_get_state_structure():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    state = game.get_state()
    assert state["game"] == "coverage"
    assert "step" in state
    assert "remaining_steps" in state
    assert "current_agent" in state
    assert "agents" in state
    assert 0 in state["agents"]
    assert 1 in state["agents"]
    assert "cells_covered" in state["agents"][0]
    assert "total_covered" in state
    assert "coverage_pct" in state


def test_get_state_includes_total_cells_when_set():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(
        engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10, total_cells=50
    )
    state = game.get_state()
    assert "total_cells" in state
    assert state["total_cells"] == 50
    assert "target_pct" in state


def test_get_state_excludes_total_cells_when_not_set():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    state = game.get_state()
    assert "total_cells" not in state


def test_get_state_remaining_steps_decrements():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    before = game.get_state()["remaining_steps"]
    game.step()
    after = game.get_state()["remaining_steps"]
    assert after == before - 1


def test_get_state_includes_teammate_positions():
    """All agents' positions must appear in state['agents']."""
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    state = game.get_state()
    assert set(state["agents"].keys()) == {0, 1, 2}
    for info in state["agents"].values():
        assert "position" in info
        assert "rotation" in info


# ---------------------------------------------------------------------------
# get_coverage_pct
# ---------------------------------------------------------------------------


def test_coverage_pct_zero_without_total_cells():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    assert game.get_coverage_pct() == pytest.approx(0.0)


def test_coverage_pct_correct_with_total_cells():
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, x=0.0)  # stays in place
    game = CoverageGame(
        engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5, total_cells=20
    )
    # 1 cell covered out of 20 → 5.0%
    assert game.get_coverage_pct() == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# get_result / CoverageResult
# ---------------------------------------------------------------------------


def test_get_result_returns_dataclass():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    game.run()
    result = game.get_result()
    assert isinstance(result, CoverageResult)


def test_get_result_has_all_agents():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    game.run()
    result = game.get_result()
    assert 0 in result.contribution
    assert 1 in result.contribution
    assert 0 in result.contribution_ratio
    assert 1 in result.contribution_ratio


def test_contribution_ratios_sum_to_one():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    result = game.run()
    total = sum(result.contribution_ratio.values())
    assert total == pytest.approx(1.0)


def test_contribution_sums_to_cells_covered():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    result = game.run()
    assert sum(result.contribution.values()) == result.cells_covered


def test_work_balance_bounds():
    engine = _make_engine(agent_count=2)
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        return _state(agent_id, x=counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=20)
    result = game.run()
    assert 0.0 <= result.work_balance <= 1.0


def test_work_balance_one_for_single_agent():
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, x=0.0)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=4)
    result = game.run()
    assert result.work_balance == pytest.approx(1.0)


def test_work_balance_equal_contribution():
    """When agents contribute equally, work_balance should be 1.0."""
    engine = _make_engine(agent_count=2)
    # Alternate agents each visit their own unique cell every step
    counter = [0]

    def step_fn(agent_id, action, **kw):
        counter[0] += 1
        # Use high z to ensure unique cells per step
        return _state(agent_id, x=float(agent_id), z=float(counter[0]))

    engine.step.side_effect = step_fn
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    result = game.run()
    assert result.work_balance == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# run() end-to-end with MockProvider
# ---------------------------------------------------------------------------


def test_run_completes_without_error():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=42), grid_size=GRID_SIZE, max_steps=10)
    result = game.run()
    assert result.termination_reason in ("max_steps", "coverage_reached")


def test_run_three_agents():
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=7), grid_size=GRID_SIZE, max_steps=15)
    result = game.run()
    assert len(result.contribution) == 3
    assert result.total_steps <= 15


def test_run_cells_covered_nonnegative():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    result = game.run()
    assert result.cells_covered >= 0

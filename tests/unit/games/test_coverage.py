from __future__ import annotations

from unittest.mock import patch

import pytest

from roboclaws.core.vlm import MockProvider
from roboclaws.games.coverage import CoverageGame, CoverageResult
from tests.support import game_fakes

GRID_SIZE = game_fakes.GRID_SIZE
_state = game_fakes.make_agent_state
_make_engine = game_fakes.make_mock_engine

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
    assert game.get_result().contribution == {0: 1, 1: 0}


def test_three_agents_distinct_start():
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE)
    assert game.cells_covered() == 3
    assert game.get_result().contribution == {0: 1, 1: 1, 2: 1}


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
    assert game.current_agent_id == 0
    game.step()
    assert game.current_agent_id == 1
    game.step()
    assert game.current_agent_id == 0


def test_round_robin_three_agents():
    engine = _make_engine(agent_count=3)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    for expected in [0, 1, 2]:
        assert game.current_agent_id == expected
        game.step()
    assert game.current_agent_id == 0


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


def test_invalid_action_falls_back_to_rotate_right():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)
    with patch.object(game.provider, "get_action", return_value={"action": "Teleport"}):
        game.step()
    engine.step.assert_called_once()
    assert engine.step.call_args.kwargs["action"] == "RotateRight"


def test_failed_move_allows_different_escape_move():
    engine = _make_engine(agent_count=1)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, success=False)
    engine.get_agent_state.side_effect = lambda agent_id: _state(agent_id, success=False)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=5)

    with patch.object(game.provider, "get_action", return_value={"action": "MoveAhead"}):
        game.step()
    with patch.object(game.provider, "get_action", return_value={"action": "MoveLeft"}):
        game.step()

    assert engine.step.call_args.kwargs["action"] == "MoveLeft"


def test_fov_coverage_can_increase_without_movement():
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0, z=0.0)]
    engine.get_agent_state.side_effect = lambda agent_id: _state(agent_id, x=0.0, z=0.0)
    engine.step.side_effect = lambda agent_id, action, **kw: _state(
        agent_id=agent_id,
        x=0.0,
        z=0.0,
        rotation_y=90.0,
    )
    reachable_cells = {(0, 0), (0, 1), (1, 0)}
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=5,
        reachable_cells=reachable_cells,
    )
    covered_before = game.cells_covered()
    game.execute_action("RotateRight")
    assert game.cells_covered() > covered_before


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


def test_get_prompt_state_includes_available_actions():
    engine = _make_engine(agent_count=2)
    game = CoverageGame(engine, MockProvider(seed=0), grid_size=GRID_SIZE, max_steps=10)
    prompt_state = game.get_prompt_state()
    assert prompt_state["my_agent_id"] == 0
    assert prompt_state["available_actions"]
    assert "no_progress_steps" in prompt_state


def test_get_prompt_state_includes_action_hints():
    engine = _make_engine(agent_count=2)
    a0 = _state(0, x=0.0, z=0.0, rotation_y=0.0)
    a1 = _state(1, x=GRID_SIZE, z=0.0, rotation_y=0.0)
    engine.get_all_agent_states.return_value = [a0, a1]
    engine.get_agent_state.side_effect = lambda agent_id: [a0, a1][agent_id]
    reachable = {(0, 0), (0, 1), (1, 0), (2, 0)}
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells=reachable,
    )

    prompt_state = game.get_prompt_state(0)
    hints = prompt_state["action_hints"]

    assert hints["MoveAhead"]["target_cell"] == [0, 1]
    assert hints["MoveAhead"]["target_status"] == "covered_by_self"
    assert hints["MoveAhead"]["estimated_new_cells"] == 0
    assert hints["MoveAhead"]["nearest_uncovered_distance"] == 3
    assert hints["MoveAhead"]["improves_frontier_distance"] is False
    assert hints["MoveRight"]["target_status"] == "occupied_by_agent_1"
    assert hints["MoveRight"]["estimated_new_cells"] == 0
    assert hints["MoveRight"]["nearest_uncovered_distance"] is None
    assert hints["MoveRight"]["improves_frontier_distance"] is False
    assert hints["RotateRight"]["front_cell_after_turn"] == [1, 0]
    assert hints["RotateRight"]["front_cell_status"] == "occupied_by_agent_1"
    assert hints["RotateRight"]["estimated_new_cells"] == 1
    assert hints["RotateRight"]["nearest_uncovered_distance"] == 2
    assert hints["RotateRight"]["improves_frontier_distance"] is False


def test_nearest_uncovered_distance_tracks_frontier_progress():
    engine = _make_engine(agent_count=1)
    agent = _state(0, x=0.0, z=0.0, rotation_y=0.0)
    engine.get_all_agent_states.return_value = [agent]
    engine.get_agent_state.side_effect = lambda agent_id: agent
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells={(0, 0), (1, 0), (2, 0)},
    )
    game._covered = {(0, 0): 0, (1, 0): 0}
    game._contribution[0] = 2

    assert game._nearest_uncovered_distance((0, 0)) == 2
    assert game._nearest_uncovered_distance((1, 0)) == 1
    assert game._nearest_uncovered_distance((2, 0)) == 0


def test_get_prompt_state_includes_stall_recovery_guidance():
    engine = _make_engine(agent_count=1)
    agent = _state(0, x=0.0, z=0.0, rotation_y=0.0)
    engine.get_all_agent_states.return_value = [agent]
    engine.get_agent_state.side_effect = lambda agent_id: agent
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells={(0, 0), (1, 0), (2, 0)},
    )
    game._covered = {(0, 0): 0, (1, 0): 0}
    game._contribution[0] = 2
    game._no_progress_steps = 2

    prompt_state = game.get_prompt_state(0)
    hints = prompt_state["action_hints"]
    recovery = prompt_state["stall_recovery"]

    assert hints["MoveRight"]["estimated_new_cells"] == 0
    assert hints["MoveRight"]["nearest_uncovered_distance"] == 1
    assert hints["MoveRight"]["improves_frontier_distance"] is True
    assert recovery["active"] is True
    assert recovery["current_frontier_distance"] == 2
    assert recovery["recommended_move"] == "MoveRight"
    assert recovery["recommended_move_frontier_distance"] == 1
    assert recovery["recommended_move_estimated_new_cells"] == 0


def test_decide_overrides_rotation_loop_with_frontier_move():
    engine = _make_engine(agent_count=1)
    agent = _state(0, x=0.0, z=0.0, rotation_y=0.0)
    engine.get_all_agent_states.return_value = [agent]
    engine.get_agent_state.side_effect = lambda agent_id: agent
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells={(0, 0), (1, 0), (2, 0)},
    )
    game._covered = {(0, 0): 0, (1, 0): 0}
    game._contribution[0] = 2
    game._no_progress_steps = 2

    with patch.object(game.provider, "get_action", return_value={"action": "RotateRight"}):
        response = game.decide(prompt_state=game.get_prompt_state(0))

    assert response["raw_action"] == "RotateRight"
    assert response["action"] == "MoveRight"
    assert response["override_reason"] == "stall_recovery_frontier_move"


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
    # side_effect: agent stays in place
    engine.step.side_effect = lambda agent_id, action, **kw: _state(agent_id, x=0.0)
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


# ---------------------------------------------------------------------------
# reachable_cells ground truth
# ---------------------------------------------------------------------------


def test_reachable_cells_sets_total_cells():
    """When reachable_cells is provided and total_cells is None, total_cells = len(reachable)."""
    engine = _make_engine(agent_count=2)
    reachable = {(i, j) for i in range(5) for j in range(5)}  # 25 cells
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        reachable_cells=reachable,
    )
    assert game.get_state()["total_cells"] == 25


def test_reachable_cells_explicit_total_cells_takes_precedence():
    """An explicit total_cells value is not overridden by reachable_cells."""
    engine = _make_engine(agent_count=2)
    reachable = {(i, 0) for i in range(50)}
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=10,
        total_cells=99,
        reachable_cells=reachable,
    )
    assert game.get_state()["total_cells"] == 99


def test_reachable_cells_enables_coverage_termination():
    """With reachable_cells providing total_cells, coverage termination fires at 95%."""
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    step_counter = [0]

    def step_fn(agent_id, action, **kw):
        step_counter[0] += 1
        return _state(0, x=step_counter[0] * GRID_SIZE)

    engine.step.side_effect = step_fn
    # 10 reachable cells; starts with 1 covered → need 9.5 → 10 cells for 95%
    reachable = {(i, 0) for i in range(10)}
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=200,
        reachable_cells=reachable,
    )
    result = game.run()
    assert result.termination_reason == "coverage_reached"
    assert result.total_steps < 200


def test_reachable_cells_coverage_pct_is_real():
    """coverage_pct reflects the real fraction when reachable_cells sets total_cells."""
    engine = _make_engine(agent_count=1)
    engine.get_all_agent_states.return_value = [_state(0, x=0.0)]
    engine.step.side_effect = lambda agent_id, action, **kw: _state(0, x=0.0)
    reachable = {(i, 0) for i in range(20)}  # 20 reachable cells
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=5,
        reachable_cells=reachable,
    )
    # Agent stays at (0,0) — 1 cell covered out of 20
    assert game.get_coverage_pct() == pytest.approx(5.0)


def test_wall_clock_is_primed_by_decide_not_only_step() -> None:
    """Wall-time enforcement must kick in when the example harness drives the
    game via decide()+execute_action() (bypassing ``step()``). Before the fix,
    _wall_started_at stayed None and _wall_exceeded() was dead code — a 20-min
    budget silently did nothing and the loop ran past its limit.
    """
    import time as _t

    engine = _make_engine(agent_count=2)
    game = CoverageGame(
        engine,
        MockProvider(seed=0),
        grid_size=GRID_SIZE,
        max_steps=100,
        max_wall_seconds=0.001,  # immediate expiry on next check
    )
    game.decide()
    _t.sleep(0.01)
    assert game.is_over(), "wall clock should have fired after 0.01s"
    assert game.get_result().termination_reason == "time_limit"

"""Tests for examples/territory_game.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Make the examples directory importable without a package install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from territory_game import (  # noqa: E402
    _CENTER_COL,
    _CENTER_ROW,
    _GRID_COLS,
    _GRID_ROWS,
    _in_bounds,
    _parse_args,
    _pos_to_world_idx,
    _world_to_viz,
    run_territory_game,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

FRAME_SHAPE = (48, 64, 3)


def _make_frame(value: int = 128) -> np.ndarray:
    return np.full(FRAME_SHAPE, value, dtype=np.uint8)


def _make_agent_state(agent_id: int, x: float = 0.0, z: float = 0.0) -> MagicMock:
    s = MagicMock()
    s.agent_id = agent_id
    s.frame = _make_frame()
    s.position = {"x": x, "y": 0.9, "z": z}
    s.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
    s.last_action_success = True
    s.last_action_error = ""
    return s


# ---------------------------------------------------------------------------
# Unit: _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.agents == 2
    assert args.steps == 200
    assert args.model == "mock"
    assert args.output_dir == "output/territory"


def test_parse_args_custom() -> None:
    args = _parse_args(
        [
            "--scene",
            "FloorPlan202",
            "--agents",
            "3",
            "--steps",
            "50",
            "--model",
            "gpt-4o-mini",
            "--output-dir",
            "/tmp/territory",
        ]
    )
    assert args.scene == "FloorPlan202"
    assert args.agents == 3
    assert args.steps == 50
    assert args.model == "gpt-4o-mini"
    assert args.output_dir == "/tmp/territory"


# ---------------------------------------------------------------------------
# Unit: coordinate helpers
# ---------------------------------------------------------------------------


def test_pos_to_world_idx_origin() -> None:
    assert _pos_to_world_idx({"x": 0.0, "y": 0.9, "z": 0.0}) == (0, 0)


def test_pos_to_world_idx_positive() -> None:
    assert _pos_to_world_idx({"x": 0.50, "y": 0.9, "z": 0.75}) == (2, 3)


def test_pos_to_world_idx_negative() -> None:
    assert _pos_to_world_idx({"x": -0.25, "y": 0.9, "z": -0.50}) == (-1, -2)


def test_world_to_viz_at_origin() -> None:
    row, col = _world_to_viz(0, 0, 0, 0)
    assert row == _CENTER_ROW
    assert col == _CENTER_COL


def test_world_to_viz_offset() -> None:
    row, col = _world_to_viz(5, 3, 0, 0)
    assert col == _CENTER_COL + 5
    assert row == _CENTER_ROW + 3


def test_world_to_viz_with_origin_offset() -> None:
    row, col = _world_to_viz(10, 8, 10, 8)
    assert row == _CENTER_ROW
    assert col == _CENTER_COL


def test_in_bounds_centre() -> None:
    assert _in_bounds(_CENTER_ROW, _CENTER_COL) is True


def test_in_bounds_corners() -> None:
    assert _in_bounds(0, 0) is True
    assert _in_bounds(_GRID_ROWS - 1, _GRID_COLS - 1) is True


def test_in_bounds_out_of_range() -> None:
    assert _in_bounds(-1, 0) is False
    assert _in_bounds(0, -1) is False
    assert _in_bounds(_GRID_ROWS, 0) is False
    assert _in_bounds(0, _GRID_COLS) is False


# ---------------------------------------------------------------------------
# Integration fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_cls():
    """Patch MultiAgentEngine to avoid launching AI2-THOR."""
    with patch("territory_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 2

        a0 = _make_agent_state(0, x=0.0)
        a1 = _make_agent_state(1, x=0.25)

        inst.get_all_agent_states.return_value = [a0, a1]
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: [a0, a1][aid]
        # step() always returns the same position (agents stay put → stale quickly)
        inst.step.side_effect = lambda agent_id, action, **kw: [a0, a1][agent_id]
        # Large reachable set so short tests terminate via max_steps or stale, not all_claimed
        inst.get_reachable_positions.return_value = {(i, j) for i in range(20) for j in range(20)}

        yield MockCls


# ---------------------------------------------------------------------------
# Integration: run_territory_game with mocked engine
# ---------------------------------------------------------------------------


def test_run_returns_summary(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert isinstance(result, dict)
    assert "cells_claimed" in result
    assert "blocking_events" in result
    assert "termination_reason" in result
    assert "vlm_cost_usd" in result
    assert "output_dir" in result


def test_run_cells_claimed_has_both_agents(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert 0 in result["cells_claimed"]
    assert 1 in result["cells_claimed"]


def test_run_cost_is_zero_for_mock(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert result["vlm_cost_usd"] == 0.0


def test_run_creates_replay_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "territory"
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "replay.json").exists()


def test_run_creates_final_territory_map(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "territory"
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "territory_final.png").exists()


def test_run_engine_closed_on_completion(mock_engine_cls, tmp_path: Path) -> None:
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    mock_engine_cls.return_value.close.assert_called_once()


def test_run_engine_closed_on_keyboard_interrupt(mock_engine_cls, tmp_path: Path) -> None:
    """engine.close() is called even when the game loop is interrupted."""
    inst = mock_engine_cls.return_value
    a0 = _make_agent_state(0, x=0.0)
    a1 = _make_agent_state(1, x=0.25)
    # Call order: (1) TerritoryGame.__init__, (2) initial_states inside try → interrupt
    inst.get_all_agent_states.side_effect = [[a0, a1], [a0, a1], KeyboardInterrupt]
    run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    inst.close.assert_called_once()


def test_run_termination_reason_valid(mock_engine_cls, tmp_path: Path) -> None:
    result = run_territory_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "territory"),
    )
    assert result["termination_reason"] in ("max_steps", "all_cells_claimed", "stale")


def test_run_three_agents(tmp_path: Path) -> None:
    """Three-agent game runs to completion without error."""
    with patch("territory_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 3
        agents = [_make_agent_state(i, x=i * 0.25) for i in range(3)]
        inst.get_all_agent_states.return_value = agents
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: agents[aid]
        inst.step.side_effect = lambda agent_id, action, **kw: agents[agent_id]
        inst.get_reachable_positions.return_value = {(i, j) for i in range(20) for j in range(20)}

        result = run_territory_game(
            scene="FloorPlan201",
            agent_count=3,
            steps=10,
            model="mock",
            output_dir=str(tmp_path / "territory3"),
        )
    assert len(result["cells_claimed"]) == 3
    assert result["termination_reason"] in ("max_steps", "all_cells_claimed", "stale")

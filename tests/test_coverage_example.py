"""Tests for examples/coverage_game.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from coverage_game import (  # noqa: E402
    _CENTER_COL,
    _CENTER_ROW,
    _GRID_COLS,
    _GRID_ROWS,
    _draw_progression_chart,
    _in_bounds,
    _parse_args,
    _pos_to_world_idx,
    _world_to_viz,
    run_coverage_game,
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
    assert args.output_dir == "output/coverage"


def test_parse_args_custom() -> None:
    args = _parse_args(
        [
            "--scene",
            "FloorPlan205",
            "--agents",
            "3",
            "--steps",
            "50",
            "--model",
            "gpt-4o-mini",
            "--output-dir",
            "/tmp/coverage",
        ]
    )
    assert args.scene == "FloorPlan205"
    assert args.agents == 3
    assert args.steps == 50
    assert args.model == "gpt-4o-mini"
    assert args.output_dir == "/tmp/coverage"


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
# Unit: _draw_progression_chart
# ---------------------------------------------------------------------------


def test_draw_progression_chart_creates_file(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([0, 1, 2, 3, 4], out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_draw_progression_chart_empty_list(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([], out)
    assert out.exists()


def test_draw_progression_chart_single_value(tmp_path: Path) -> None:
    out = tmp_path / "chart.png"
    _draw_progression_chart([5], out)
    assert out.exists()


# ---------------------------------------------------------------------------
# Integration fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_cls():
    """Patch MultiAgentEngine to avoid launching AI2-THOR."""
    with patch("coverage_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 2

        a0 = _make_agent_state(0, x=0.0)
        a1 = _make_agent_state(1, x=0.25)

        inst.get_all_agent_states.return_value = [a0, a1]
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: [a0, a1][aid]
        inst.step.side_effect = lambda agent_id, action, **kw: [a0, a1][agent_id]

        yield MockCls


# ---------------------------------------------------------------------------
# Integration: run_coverage_game with mocked engine
# ---------------------------------------------------------------------------


def test_run_returns_summary(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert isinstance(result, dict)
    assert "cells_covered" in result
    assert "contribution" in result
    assert "work_balance" in result
    assert "termination_reason" in result
    assert "vlm_cost_usd" in result
    assert "output_dir" in result


def test_run_contribution_has_all_agents(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert 0 in result["contribution"]
    assert 1 in result["contribution"]


def test_run_cost_is_zero_for_mock(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert result["vlm_cost_usd"] == 0.0


def test_run_work_balance_in_range(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert 0.0 <= result["work_balance"] <= 1.0


def test_run_creates_replay_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "replay.json").exists()


def test_run_creates_coverage_final_png(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "coverage_final.png").exists()


def test_run_creates_progression_chart(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "coverage_progression.png").exists()


def test_run_creates_work_balance_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "work_balance.json").exists()


def test_run_work_balance_json_content(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "coverage"
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(out_dir),
    )
    data = json.loads((out_dir / "work_balance.json").read_text())
    assert "cells_covered" in data
    assert "work_balance" in data
    assert "contribution" in data
    assert "termination_reason" in data


def test_run_engine_closed_on_completion(mock_engine_cls, tmp_path: Path) -> None:
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=6,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    mock_engine_cls.return_value.close.assert_called_once()


def test_run_engine_closed_on_keyboard_interrupt(mock_engine_cls, tmp_path: Path) -> None:
    """engine.close() is called even when the game loop is interrupted."""
    inst = mock_engine_cls.return_value
    a0 = _make_agent_state(0, x=0.0)
    a1 = _make_agent_state(1, x=0.25)
    # Call order: (1) CoverageGame.__init__, (2) initial_states inside try, (3) loop → interrupt
    inst.get_all_agent_states.side_effect = [[a0, a1], [a0, a1], KeyboardInterrupt]
    run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    inst.close.assert_called_once()


def test_run_termination_reason_valid(mock_engine_cls, tmp_path: Path) -> None:
    result = run_coverage_game(
        scene="FloorPlan201",
        agent_count=2,
        steps=10,
        model="mock",
        output_dir=str(tmp_path / "coverage"),
    )
    assert result["termination_reason"] in ("max_steps", "coverage_reached")


def test_run_three_agents(tmp_path: Path) -> None:
    """Three-agent game runs to completion without error."""
    with patch("coverage_game.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        inst.agent_count = 3
        agents = [_make_agent_state(i, x=i * 0.25) for i in range(3)]
        inst.get_all_agent_states.return_value = agents
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.get_agent_state.side_effect = lambda aid: agents[aid]
        inst.step.side_effect = lambda agent_id, action, **kw: agents[agent_id]

        result = run_coverage_game(
            scene="FloorPlan201",
            agent_count=3,
            steps=10,
            model="mock",
            output_dir=str(tmp_path / "coverage3"),
        )
    assert len(result["contribution"]) == 3
    assert result["termination_reason"] in ("max_steps", "coverage_reached")

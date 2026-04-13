"""Tests for examples/single_agent_explore.py."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Make the examples directory importable without a package install
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "examples"))

from single_agent_explore import (  # noqa: E402
    _CENTER_COL,
    _CENTER_ROW,
    _GRID_COLS,
    _GRID_ROWS,
    _frame_to_b64,
    _in_bounds,
    _parse_args,
    _pos_to_world_idx,
    _world_to_viz,
    run_exploration,
)

# ---------------------------------------------------------------------------
# Helpers shared by multiple tests
# ---------------------------------------------------------------------------

FRAME_SHAPE = (48, 64, 3)


def _make_frame(value: int = 128) -> np.ndarray:
    return np.full(FRAME_SHAPE, value, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Unit: _parse_args
# ---------------------------------------------------------------------------


def test_parse_args_defaults() -> None:
    args = _parse_args([])
    assert args.scene == "FloorPlan201"
    assert args.steps == 50
    assert args.model == "mock"
    assert args.output_dir == "output/explore"


def test_parse_args_custom() -> None:
    args = _parse_args(
        [
            "--scene",
            "FloorPlan202",
            "--steps",
            "10",
            "--model",
            "gpt-4o-mini",
            "--output-dir",
            "/tmp/x",
        ]
    )
    assert args.scene == "FloorPlan202"
    assert args.steps == 10
    assert args.model == "gpt-4o-mini"
    assert args.output_dir == "/tmp/x"


# ---------------------------------------------------------------------------
# Unit: coordinate helpers
# ---------------------------------------------------------------------------


def test_pos_to_world_idx_origin() -> None:
    idx = _pos_to_world_idx({"x": 0.0, "y": 0.9, "z": 0.0})
    assert idx == (0, 0)


def test_pos_to_world_idx_positive() -> None:
    # x=0.50, z=0.75 → ix=2, iz=3 (rounded to nearest 0.25)
    idx = _pos_to_world_idx({"x": 0.50, "y": 0.9, "z": 0.75})
    assert idx == (2, 3)


def test_pos_to_world_idx_negative() -> None:
    idx = _pos_to_world_idx({"x": -0.25, "y": 0.9, "z": -0.50})
    assert idx == (-1, -2)


def test_world_to_viz_at_origin() -> None:
    row, col = _world_to_viz(0, 0, 0, 0)
    assert row == _CENTER_ROW
    assert col == _CENTER_COL


def test_world_to_viz_offset() -> None:
    # ix=5, iz=3 relative to origin ix=0, iz=0 → col=CENTER+5, row=CENTER+3
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
# Unit: _frame_to_b64
# ---------------------------------------------------------------------------


def test_frame_to_b64_returns_string() -> None:
    frame = _make_frame(200)
    b64 = _frame_to_b64(frame)
    assert isinstance(b64, str)
    assert len(b64) > 0


def test_frame_to_b64_is_valid_base64() -> None:
    import base64

    frame = _make_frame(100)
    b64 = _frame_to_b64(frame)
    # Must not raise
    decoded = base64.b64decode(b64)
    assert len(decoded) > 0


def test_frame_to_b64_different_frames_differ() -> None:
    b64_a = _frame_to_b64(_make_frame(0))
    b64_b = _frame_to_b64(_make_frame(255))
    assert b64_a != b64_b


# ---------------------------------------------------------------------------
# Integration: run_exploration with mocked engine
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_engine_cls():
    """Patch MultiAgentEngine to avoid launching AI2-THOR."""
    with patch("single_agent_explore.MultiAgentEngine") as MockCls:
        inst = MockCls.return_value
        # get_agent_state always returns the same mock state
        agent_state = MagicMock()
        agent_state.frame = _make_frame()
        agent_state.position = {"x": 0.0, "y": 0.9, "z": 0.0}
        agent_state.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
        agent_state.last_action_success = True
        agent_state.last_action_error = ""
        inst.get_agent_state.return_value = agent_state
        inst.get_overhead_frame.return_value = _make_frame(80)
        inst.step.return_value = agent_state
        yield MockCls


def test_run_exploration_returns_summary(mock_engine_cls, tmp_path: Path) -> None:
    result = run_exploration(
        scene="FloorPlan201",
        steps=3,
        model="mock",
        output_dir=str(tmp_path / "explore"),
    )
    assert isinstance(result, dict)
    assert "cells_visited" in result
    assert "vlm_cost_usd" in result
    assert "output_dir" in result


def test_run_exploration_cells_visited_positive(mock_engine_cls, tmp_path: Path) -> None:
    result = run_exploration(
        scene="FloorPlan201",
        steps=5,
        model="mock",
        output_dir=str(tmp_path / "explore"),
    )
    assert result["cells_visited"] >= 1


def test_run_exploration_cost_is_zero_for_mock(mock_engine_cls, tmp_path: Path) -> None:
    result = run_exploration(
        scene="FloorPlan201",
        steps=3,
        model="mock",
        output_dir=str(tmp_path / "explore"),
    )
    assert result["vlm_cost_usd"] == 0.0


def test_run_exploration_creates_replay_json(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "explore"
    run_exploration(
        scene="FloorPlan201",
        steps=4,
        model="mock",
        output_dir=str(out_dir),
    )
    assert (out_dir / "replay.json").exists()


def test_run_exploration_creates_agent_frames(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "explore"
    run_exploration(
        scene="FloorPlan201",
        steps=3,
        model="mock",
        output_dir=str(out_dir),
    )
    agent_frames = list((out_dir / "agent_frames").glob("*_agent0.png"))
    assert len(agent_frames) == 3


def test_run_exploration_engine_closed_on_completion(mock_engine_cls, tmp_path: Path) -> None:
    run_exploration(
        scene="FloorPlan201",
        steps=2,
        model="mock",
        output_dir=str(tmp_path / "explore"),
    )
    mock_engine_cls.return_value.close.assert_called_once()


def test_run_exploration_engine_closed_on_keyboard_interrupt(
    mock_engine_cls, tmp_path: Path
) -> None:
    """engine.close() is called even when the loop is interrupted."""
    inst = mock_engine_cls.return_value
    good_state = MagicMock()
    good_state.frame = _make_frame()
    good_state.position = {"x": 0.0, "y": 0.9, "z": 0.0}
    good_state.rotation = {"x": 0.0, "y": 0.0, "z": 0.0}
    # First call returns initial state; second raises KeyboardInterrupt mid-loop
    inst.get_agent_state.side_effect = [good_state, KeyboardInterrupt]
    run_exploration(
        scene="FloorPlan201",
        steps=5,
        model="mock",
        output_dir=str(tmp_path / "explore"),
    )
    inst.close.assert_called_once()

"""Tests for examples/single_agent_explore.py."""

from __future__ import annotations

import base64
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Make the examples directory importable without a package install
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "examples"))

from single_agent_explore import (  # noqa: E402
    _CENTER_COL,
    _CENTER_ROW,
    _GRID_COLS,
    _GRID_ROWS,
    _in_bounds,
    _parse_args,
    _pos_to_world_idx,
    _world_to_viz,
    run_exploration,
)

from roboclaws.core.turn_metrics import encode_frame_to_b64_jpeg  # noqa: E402


def _frame_to_b64(frame: np.ndarray) -> str:
    """Thin test-local shim: returns just the b64 string from encode_frame_to_b64_jpeg."""
    return encode_frame_to_b64_jpeg(frame)[0]


# ---------------------------------------------------------------------------
# Helpers shared by multiple tests
# ---------------------------------------------------------------------------

FRAME_SHAPE = (48, 64, 3)


def _make_frame(value: int = 128) -> np.ndarray:
    return np.full(FRAME_SHAPE, value, dtype=np.uint8)


# ---------------------------------------------------------------------------
# Unit: _parse_args
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "expected"),
    [
        (
            [],
            {
                "scene": "FloorPlan201",
                "steps": 50,
                "model": "mock",
                "output_dir": "output/explore",
            },
        ),
        (
            [
                "--scene",
                "FloorPlan202",
                "--steps",
                "10",
                "--model",
                "gpt-4o-mini",
                "--output-dir",
                "/tmp/x",
            ],
            {
                "scene": "FloorPlan202",
                "steps": 10,
                "model": "gpt-4o-mini",
                "output_dir": "/tmp/x",
            },
        ),
    ],
)
def test_parse_args(argv: list[str], expected: dict[str, object]) -> None:
    args = _parse_args(argv)
    assert {name: getattr(args, name) for name in expected} == expected


# ---------------------------------------------------------------------------
# Unit: coordinate helpers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        ({"x": 0.0, "y": 0.9, "z": 0.0}, (0, 0)),
        ({"x": 0.50, "y": 0.9, "z": 0.75}, (2, 3)),
        ({"x": -0.25, "y": 0.9, "z": -0.50}, (-1, -2)),
    ],
)
def test_pos_to_world_idx(position: dict[str, float], expected: tuple[int, int]) -> None:
    assert _pos_to_world_idx(position) == expected


@pytest.mark.parametrize(
    ("world", "origin", "expected"),
    [
        ((0, 0), (0, 0), (_CENTER_ROW, _CENTER_COL)),
        ((5, 3), (0, 0), (_CENTER_ROW + 3, _CENTER_COL + 5)),
        ((10, 8), (10, 8), (_CENTER_ROW, _CENTER_COL)),
    ],
)
def test_world_to_viz(
    world: tuple[int, int],
    origin: tuple[int, int],
    expected: tuple[int, int],
) -> None:
    assert _world_to_viz(*world, *origin) == expected


@pytest.mark.parametrize(
    ("row", "col", "expected"),
    [
        (_CENTER_ROW, _CENTER_COL, True),
        (0, 0, True),
        (_GRID_ROWS - 1, _GRID_COLS - 1, True),
        (-1, 0, False),
        (0, -1, False),
        (_GRID_ROWS, 0, False),
        (0, _GRID_COLS, False),
    ],
)
def test_in_bounds(row: int, col: int, expected: bool) -> None:
    assert _in_bounds(row, col) is expected


# ---------------------------------------------------------------------------
# Unit: _frame_to_b64
# ---------------------------------------------------------------------------


def test_frame_to_b64_returns_decodable_jpeg() -> None:
    frame = _make_frame(200)
    b64 = _frame_to_b64(frame)
    decoded = base64.b64decode(b64)

    assert isinstance(b64, str)
    assert decoded.startswith(b"\xff\xd8\xff")


def test_frame_to_b64_avoids_deprecated_pillow_mode_warning(recwarn) -> None:
    _frame_to_b64(_make_frame(200))

    mode_warnings = [
        warning
        for warning in recwarn
        if issubclass(warning.category, DeprecationWarning)
        and "'mode' parameter is deprecated" in str(warning.message)
    ]
    assert mode_warnings == []


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


def test_run_exploration_returns_summary_for_mock_provider(mock_engine_cls, tmp_path: Path) -> None:
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
    assert result["cells_visited"] >= 1
    assert result["vlm_cost_usd"] == 0.0


def test_run_exploration_persists_replay_artifacts(mock_engine_cls, tmp_path: Path) -> None:
    out_dir = tmp_path / "explore"
    run_exploration(
        scene="FloorPlan201",
        steps=4,
        model="mock",
        output_dir=str(out_dir),
    )
    agent_frames = list((out_dir / "agent_frames").glob("*_agent0.png"))

    assert (out_dir / "replay.json").exists()
    assert len(agent_frames) == 4


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

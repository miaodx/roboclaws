"""Behavior tests for SOUL-labelled visualizer output."""

from __future__ import annotations

import pytest
from PIL import Image

from roboclaws.core.visualizer import GameVisualizer
from roboclaws.core.vlm import load_agent_souls

GRID_ROWS = 10
GRID_COLS = 10
CELL_PX = 20


def _make_viz(labels: list[str] | None = None) -> GameVisualizer:
    return GameVisualizer(
        grid_rows=GRID_ROWS,
        grid_cols=GRID_COLS,
        cell_px=CELL_PX,
        agent_count=len(labels) if labels else 2,
        agent_labels=labels,
    )


def _cell_center(row: int, col: int) -> tuple[int, int]:
    return (col * CELL_PX + CELL_PX // 2, row * CELL_PX + CELL_PX // 2)


@pytest.mark.parametrize("labels", [["cooperative"], ["unknown_soul"]])
def test_soul_labels_tint_claimed_cells_differently_from_palette(labels: list[str]) -> None:
    viz_default = _make_viz()
    viz_soul = _make_viz(labels)

    positions = [(9, 9)]
    claimed_cells = {0: [(2, 2)]}

    img_default = viz_default.render_overhead_map(
        agent_positions=positions,
        claimed_cells=claimed_cells,
    )
    img_soul = viz_soul.render_overhead_map(
        agent_positions=positions,
        claimed_cells=claimed_cells,
    )

    assert img_default.getpixel(_cell_center(2, 2)) != img_soul.getpixel(_cell_center(2, 2))


@pytest.mark.parametrize("labels", [None, ["cooperative"]])
def test_visualizer_renders_valid_rgb_map_with_optional_soul_labels(
    labels: list[str] | None,
) -> None:
    viz = _make_viz(labels)
    img = viz.render_overhead_map(
        agent_positions=[(1, 1), (8, 8)],
        claimed_cells={0: [(0, 0)], 1: [(9, 9)]},
    )
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width == GRID_COLS * CELL_PX
    assert img.height == GRID_ROWS * CELL_PX


@pytest.mark.parametrize(
    ("souls_env", "agent_count", "expected_labels"),
    [
        ("", 2, []),
        ("aggressive,defensive", 2, ["aggressive", "defensive"]),
        ("aggressive", 2, ["aggressive", "default"]),
        ("agent-0:aggressive,agent-2:cooperative", 3, ["aggressive", "default", "cooperative"]),
    ],
)
def test_load_agent_souls_returns_visualizer_labels_for_supported_env_formats(
    tmp_path,
    souls_env: str,
    agent_count: int,
    expected_labels: list[str],
) -> None:
    for soul_name in {"aggressive", "defensive", "cooperative", "default"}:
        (tmp_path / f"{soul_name}.md").write_text(f"# {soul_name}\n", encoding="utf-8")

    labels, contents = load_agent_souls(souls_env, agent_count, str(tmp_path))

    assert labels == expected_labels
    assert sorted(contents) == list(range(len(expected_labels)))
    for agent_id, soul_name in enumerate(expected_labels):
        assert contents[agent_id] == f"# {soul_name}\n"

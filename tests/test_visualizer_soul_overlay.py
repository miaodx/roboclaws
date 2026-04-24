"""Tests for SOUL badge and trail-tinting in GameVisualizer (T19.8)."""

from __future__ import annotations

import numpy as np
from PIL import Image

from roboclaws.core.visualizer import _SOUL_COLOURS, GameVisualizer

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


# ---------------------------------------------------------------------------
# Smoke: agent_labels kwarg is accepted
# ---------------------------------------------------------------------------


def test_visualizer_accepts_agent_labels_kwarg() -> None:
    viz = _make_viz(["aggressive", "defensive"])
    assert viz.agent_labels == ["aggressive", "defensive"]


def test_visualizer_accepts_no_agent_labels() -> None:
    viz = _make_viz()
    assert viz.agent_labels == []


# ---------------------------------------------------------------------------
# _agent_colour returns SOUL colour when labelled, palette otherwise
# ---------------------------------------------------------------------------


def test_agent_colour_returns_soul_colour_for_known_label() -> None:
    viz = _make_viz(["aggressive", "defensive"])
    assert viz._agent_colour(0) == _SOUL_COLOURS["aggressive"]
    assert viz._agent_colour(1) == _SOUL_COLOURS["defensive"]


def test_agent_colour_falls_back_to_grey_for_unknown_label() -> None:
    viz = _make_viz(["unknown_soul"])
    assert viz._agent_colour(0) == _SOUL_COLOURS["default"]


def test_agent_colour_falls_back_to_palette_when_no_labels() -> None:
    from roboclaws.core.visualizer import _AGENT_COLOURS

    viz = _make_viz()
    assert viz._agent_colour(0) == _AGENT_COLOURS[0]
    assert viz._agent_colour(1) == _AGENT_COLOURS[1]


def test_agent_colour_palette_fallback_for_out_of_range_index() -> None:
    from roboclaws.core.visualizer import _AGENT_COLOURS

    viz = _make_viz(["aggressive"])
    # Agent 1 has no label → palette
    assert viz._agent_colour(1) == _AGENT_COLOURS[1]


# ---------------------------------------------------------------------------
# render_overhead_map — SOUL badge affects output
# ---------------------------------------------------------------------------


def test_soul_labels_change_overhead_map_output() -> None:
    """Map with SOUL labels must differ from map without labels
    (badges are drawn in SOUL colour, which differs from the default palette)."""
    viz_no_soul = _make_viz()
    viz_with_soul = _make_viz(["aggressive", "defensive"])

    positions = [(2, 2), (7, 7)]
    img_no_soul = viz_no_soul.render_overhead_map(agent_positions=positions)
    img_with_soul = viz_with_soul.render_overhead_map(agent_positions=positions)

    arr_no = np.asarray(img_no_soul)
    arr_with = np.asarray(img_with_soul)
    # SOUL colours differ from the default palette colours → pixel arrays differ
    assert not np.array_equal(arr_no, arr_with)


def test_soul_trail_tinting_differs_from_default() -> None:
    """Claimed cells with SOUL labels should use SOUL colour, not agent palette."""
    viz_default = _make_viz()
    viz_soul = _make_viz(["aggressive", "defensive"])

    positions = [(0, 0), (9, 9)]
    cells = {0: [(2, 2), (2, 3), (3, 2)], 1: [(6, 6), (6, 7), (7, 6)]}

    img_default = viz_default.render_overhead_map(agent_positions=positions, claimed_cells=cells)
    img_soul = viz_soul.render_overhead_map(agent_positions=positions, claimed_cells=cells)

    arr_default = np.asarray(img_default)
    arr_soul = np.asarray(img_soul)
    assert not np.array_equal(arr_default, arr_soul)


def test_soul_map_is_valid_pil_rgb() -> None:
    viz = _make_viz(["aggressive", "cooperative"])
    img = viz.render_overhead_map(
        agent_positions=[(1, 1), (8, 8)],
        claimed_cells={0: [(0, 0)], 1: [(9, 9)]},
    )
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"
    assert img.width == GRID_COLS * CELL_PX
    assert img.height == GRID_ROWS * CELL_PX


# ---------------------------------------------------------------------------
# AGENT_SOULS env parsing helpers (unit-tested directly)
# ---------------------------------------------------------------------------


def _parse_agent_souls_csv(souls_env: str, agent_count: int) -> list[str]:
    """Mirror the AGENT_SOULS parsing logic in territory_game / coverage_game."""
    if ":" in souls_env:
        raw_map = dict(e.split(":", 1) for e in souls_env.split(",") if ":" in e)
        return [raw_map.get(f"agent-{i}", "default") for i in range(agent_count)]
    entries = souls_env.split(",")
    return [entries[i] if i < len(entries) else "default" for i in range(agent_count)]


def test_souls_csv_positional_two_agents() -> None:
    labels = _parse_agent_souls_csv("aggressive,defensive", 2)
    assert labels == ["aggressive", "defensive"]


def test_souls_csv_positional_three_agents() -> None:
    labels = _parse_agent_souls_csv("aggressive,defensive,cooperative", 3)
    assert labels == ["aggressive", "defensive", "cooperative"]


def test_souls_csv_positional_short_pads_with_default() -> None:
    labels = _parse_agent_souls_csv("aggressive", 2)
    assert labels == ["aggressive", "default"]


def test_souls_dict_form_sparse_assignment() -> None:
    labels = _parse_agent_souls_csv("agent-0:aggressive,agent-2:cooperative", 3)
    assert labels == ["aggressive", "default", "cooperative"]


def test_souls_dict_form_two_agents() -> None:
    labels = _parse_agent_souls_csv("agent-0:defensive,agent-1:cooperative", 2)
    assert labels == ["defensive", "cooperative"]

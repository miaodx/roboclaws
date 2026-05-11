from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from roboclaws.core.visualizer import GameVisualizer, _hstack, _vstack

GRID_ROWS = 10
GRID_COLS = 10
CELL_PX = 20
LABEL_H = 20


@pytest.fixture()
def viz() -> GameVisualizer:
    return GameVisualizer(grid_rows=GRID_ROWS, grid_cols=GRID_COLS, cell_px=CELL_PX, agent_count=3)


def _make_frame(h: int = 480, w: int = 640, value: int = 128) -> np.ndarray:
    return np.full((h, w, 3), value, dtype=np.uint8)


# ---------------------------------------------------------------------------
# render_overhead_map — basic properties
# ---------------------------------------------------------------------------


def test_overhead_map_returns_pil_image(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(2, 3), (5, 7)])
    assert isinstance(img, Image.Image)


def test_overhead_map_correct_size(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(0, 0)])
    assert img.width == GRID_COLS * CELL_PX
    assert img.height == GRID_ROWS * CELL_PX


def test_overhead_map_is_rgb(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(0, 0)])
    assert img.mode == "RGB"


# ---------------------------------------------------------------------------
# render_overhead_map — claimed / covered cells
# ---------------------------------------------------------------------------


def test_overhead_map_with_claimed_cells_differs_from_blank(viz: GameVisualizer) -> None:
    blank = viz.render_overhead_map(agent_positions=[(9, 9)])
    claimed = viz.render_overhead_map(
        agent_positions=[(9, 9)],
        claimed_cells={0: [(0, 0), (0, 1), (1, 0)]},
    )
    arr_blank = np.asarray(blank)
    arr_claimed = np.asarray(claimed)
    # Claimed region introduces tinted cells — arrays must differ
    assert not np.array_equal(arr_blank, arr_claimed)


def test_overhead_map_with_covered_cells_differs_from_blank(viz: GameVisualizer) -> None:
    blank = viz.render_overhead_map(agent_positions=[(9, 9)])
    covered = viz.render_overhead_map(
        agent_positions=[(9, 9)],
        covered_cells=[(0, 0), (0, 1), (1, 0)],
    )
    assert not np.array_equal(np.asarray(blank), np.asarray(covered))


def test_overhead_map_multiple_agents_claimed(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(
        agent_positions=[(1, 1), (8, 8)],
        claimed_cells={0: [(0, 0), (0, 1)], 1: [(9, 9), (8, 9)]},
    )
    assert isinstance(img, Image.Image)
    assert img.mode == "RGB"


def test_overhead_map_with_base_frame(viz: GameVisualizer) -> None:
    base = np.ones((480, 640, 3), dtype=np.uint8) * 128
    img = viz.render_overhead_map(agent_positions=[(2, 2)], base_frame=base)
    assert isinstance(img, Image.Image)
    assert img.width == GRID_COLS * CELL_PX
    assert img.height == GRID_ROWS * CELL_PX


# ---------------------------------------------------------------------------
# render_overhead_map — agent marker distinctness
# ---------------------------------------------------------------------------


def test_two_agent_positions_differ(viz: GameVisualizer) -> None:
    img_a = viz.render_overhead_map(agent_positions=[(0, 0), (9, 9)])
    img_b = viz.render_overhead_map(agent_positions=[(0, 0), (0, 1)])
    assert not np.array_equal(np.asarray(img_a), np.asarray(img_b))


def test_single_agent_map_is_valid(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(5, 5)])
    assert isinstance(img, Image.Image)


# ---------------------------------------------------------------------------
# composite_frame
# ---------------------------------------------------------------------------


def test_composite_frame_returns_pil_image(viz: GameVisualizer) -> None:
    frames = [_make_frame() for _ in range(2)]
    overhead = viz.render_overhead_map(agent_positions=[(1, 1), (8, 8)])
    out = viz.composite_frame(frames, overhead)
    assert isinstance(out, Image.Image)


def test_composite_frame_height(viz: GameVisualizer) -> None:
    frames = [_make_frame()]
    overhead = viz.render_overhead_map(agent_positions=[(1, 1)])
    out = viz.composite_frame(frames, overhead, frame_height=120)
    assert out.height == 120 + LABEL_H


def test_composite_frame_wider_with_more_agents(viz: GameVisualizer) -> None:
    overhead = viz.render_overhead_map(agent_positions=[(1, 1), (8, 8), (5, 5)])
    out2 = viz.composite_frame([_make_frame(), _make_frame()], overhead)
    out3 = viz.composite_frame([_make_frame(), _make_frame(), _make_frame()], overhead)
    assert out3.width > out2.width


def test_composite_frame_single_agent(viz: GameVisualizer) -> None:
    overhead = viz.render_overhead_map(agent_positions=[(3, 3)])
    out = viz.composite_frame([_make_frame()], overhead, frame_height=80)
    assert out.height == 80 + LABEL_H
    assert out.width > 0


# ---------------------------------------------------------------------------
# save_png / frame_to_array
# ---------------------------------------------------------------------------


def test_save_png_creates_file(viz: GameVisualizer, tmp_path) -> None:
    img = viz.render_overhead_map(agent_positions=[(0, 0)])
    path = tmp_path / "test.png"
    viz.save_png(img, path)
    assert path.exists()
    loaded = Image.open(path)
    assert loaded.size == img.size


def test_frame_to_array_shape_and_dtype(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(0, 0)])
    arr = viz.frame_to_array(img)
    assert isinstance(arr, np.ndarray)
    assert arr.ndim == 3
    assert arr.shape[2] == 3
    assert arr.dtype == np.uint8


def test_frame_to_array_roundtrip(viz: GameVisualizer) -> None:
    img = viz.render_overhead_map(agent_positions=[(2, 3)])
    arr = viz.frame_to_array(img)
    assert arr.shape == (GRID_ROWS * CELL_PX, GRID_COLS * CELL_PX, 3)


# ---------------------------------------------------------------------------
# save_gif
# ---------------------------------------------------------------------------


def test_save_gif_from_pil_images(viz: GameVisualizer, tmp_path) -> None:
    pytest.importorskip("imageio")
    frames = [viz.render_overhead_map(agent_positions=[(i, i)]) for i in range(3)]
    path = tmp_path / "test.gif"
    viz.save_gif(frames, path, fps=2.0)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_gif_from_numpy_arrays(viz: GameVisualizer, tmp_path) -> None:
    pytest.importorskip("imageio")
    frames = [_make_frame(value=v) for v in [50, 100, 150]]
    path = tmp_path / "arrays.gif"
    viz.save_gif(frames, path, fps=2.0)
    assert path.exists()
    assert path.stat().st_size > 0


def test_save_gif_without_imageio_raises(viz: GameVisualizer, tmp_path, monkeypatch) -> None:
    import roboclaws.core.visualizer as vis_mod

    monkeypatch.setattr(vis_mod, "_HAS_IMAGEIO", False)
    frames = [viz.render_overhead_map(agent_positions=[(0, 0)])]
    with pytest.raises(ImportError, match="imageio"):
        viz.save_gif(frames, tmp_path / "x.gif")


# ---------------------------------------------------------------------------
# Private layout helpers
# ---------------------------------------------------------------------------


def test_vstack_combines_heights() -> None:
    a = Image.new("RGB", (100, 50), (255, 0, 0))
    b = Image.new("RGB", (100, 30), (0, 255, 0))
    out = _vstack([a, b])
    assert out.width == 100
    assert out.height == 80


def test_hstack_combines_widths() -> None:
    a = Image.new("RGB", (60, 100), (255, 0, 0))
    b = Image.new("RGB", (40, 100), (0, 255, 0))
    out = _hstack([a, b])
    assert out.width == 100
    assert out.height == 100


def test_vstack_preserves_pixel_values() -> None:
    red = Image.new("RGB", (10, 10), (255, 0, 0))
    blue = Image.new("RGB", (10, 10), (0, 0, 255))
    out = _vstack([red, blue])
    arr = np.asarray(out)
    # Top half should be red
    assert arr[5, 5, 0] == 255
    assert arr[5, 5, 2] == 0
    # Bottom half should be blue
    assert arr[15, 5, 0] == 0
    assert arr[15, 5, 2] == 255

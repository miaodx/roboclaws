from __future__ import annotations

import pytest

from roboclaws.core.scene_grid import (
    SceneGrid,
    compute_world_bbox,
    default_scene_grid,
    world_to_cell,
)


@pytest.mark.parametrize(
    ("position", "expected"),
    [
        ({"x": 0.0, "y": 0.0, "z": 0.0}, (0, 0)),
        ({"x": 0.25, "y": 0.0, "z": 0.50}, (1, 2)),
        ({"x": -0.25, "y": 0.0, "z": 0.0}, (-1, 0)),
        ({"x": 0.13, "y": 0.0, "z": 0.0}, (1, 0)),
    ],
)
def test_world_to_cell_uses_project_grid_rounding(
    position: dict[str, float],
    expected: tuple[int, int],
) -> None:
    assert world_to_cell(position, grid_size=0.25) == expected


def test_scene_grid_world_cell_roundtrip() -> None:
    grid = SceneGrid(grid_size=0.25)

    cell = grid.world_to_cell({"x": 0.50, "y": 0.9, "z": -0.25})

    assert cell == (2, -1)
    assert grid.cell_to_world(cell) == {"x": 0.5, "z": -0.25}


def test_scene_grid_normalizes_reachable_positions() -> None:
    grid = SceneGrid(grid_size=0.25)

    cells = grid.normalize_reachable_positions(
        [
            {"x": 0.0, "y": 0.0, "z": 0.0},
            {"x": 0.25, "y": 0.0, "z": 0.0},
            {"x": 0.26, "y": 0.0, "z": 0.01},
        ]
    )

    assert cells == {(0, 0), (1, 0)}


def test_scene_grid_projects_agent_and_object_footprints() -> None:
    grid = SceneGrid(grid_size=0.25)

    assert grid.agent_footprint({"x": 0.25, "y": 0.9, "z": 0.5}) == {(1, 2)}

    object_meta = {
        "axisAlignedBoundingBox": {
            "cornerPoints": [
                [0.0, 0.0, 0.0],
                [0.25, 0.0, 0.0],
                [0.25, 0.0, 0.25],
                [0.0, 0.0, 0.25],
            ]
        }
    }
    assert grid.object_footprint(object_meta) == {(0, 0), (1, 0), (0, 1), (1, 1)}


def test_scene_grid_object_footprint_falls_back_to_position() -> None:
    grid = SceneGrid(grid_size=0.25)

    assert grid.object_footprint({"position": {"x": -0.25, "z": 0.25}}) == {(-1, 1)}


def test_compute_world_bbox_spans_all_cells() -> None:
    assert compute_world_bbox({(0, 1), (2, -1)}, [(-3, 4)]) == (-3, -1, 2, 4)


def test_default_scene_grid_uses_project_grid_size() -> None:
    assert default_scene_grid().world_to_cell({"x": 0.25, "z": 0.5}) == (1, 2)

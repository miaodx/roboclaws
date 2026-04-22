from __future__ import annotations

import numpy as np

from roboclaws.core.visualizer import GameVisualizer


def _cell_center(
    bbox: tuple[int, int, int, int],
    *,
    ix: int,
    iz: int,
    cell_px: int,
) -> tuple[int, int]:
    min_ix, min_iz, _max_ix, _max_iz = bbox
    x = 2 + (ix - min_ix) * cell_px + cell_px // 2
    y = 2 + (iz - min_iz) * cell_px + cell_px // 2
    return x, y


def _count_marker_pixels(cell: np.ndarray) -> tuple[int, int, int, int]:
    mask = (cell[..., 0] > 150) & (cell[..., 1] < 120) & (cell[..., 2] < 120)
    ys, xs = np.where(mask)
    center_y = cell.shape[0] / 2.0
    center_x = cell.shape[1] / 2.0
    return (
        center_y - float(ys.min()),
        float(ys.max()) - center_y,
        center_x - float(xs.min()),
        float(xs.max()) - center_x,
    )


def test_unreachable_cells_render_dark() -> None:
    viz = GameVisualizer(cell_px=12)
    bbox = (0, 0, 1, 1)
    img = viz.render_structured_map(
        agent_positions=[(0, 0)],
        agent_rotations=[{"y": 90.0}],
        reachable_cells={(0, 0)},
        world_bbox=bbox,
    )
    arr = np.asarray(img)
    x, y = _cell_center(bbox, ix=1, iz=1, cell_px=12)
    assert tuple(arr[y, x]) == (60, 60, 60)


def test_agent_triangle_points_in_cardinal_directions() -> None:
    viz = GameVisualizer(cell_px=20, agent_count=1)
    bbox = (0, 0, 0, 0)
    expected = {
        0.0: "down",
        90.0: "right",
        180.0: "up",
        270.0: "left",
    }
    for yaw, direction in expected.items():
        img = viz.render_structured_map(
            agent_positions=[(0, 0)],
            agent_rotations=[{"y": yaw}],
            reachable_cells={(0, 0)},
            world_bbox=bbox,
        )
        arr = np.asarray(img)
        cell = arr[2:22, 2:22]
        up, down, left, right = _count_marker_pixels(cell)
        dominant = max(
            {"up": up, "down": down, "left": left, "right": right}.items(),
            key=lambda item: item[1],
        )[0]
        assert dominant == direction


def test_three_agents_render_distinct_colours() -> None:
    viz = GameVisualizer(cell_px=10, agent_count=3)
    bbox = (0, 0, 2, 0)
    img = viz.render_structured_map(
        agent_positions=[(0, 0), (1, 0), (2, 0)],
        agent_rotations=[{"y": 0.0}, {"y": 90.0}, {"y": 180.0}],
        reachable_cells={(0, 0), (1, 0), (2, 0)},
        claimed_cells={0: [(0, 0)], 1: [(1, 0)], 2: [(2, 0)]},
        world_bbox=bbox,
    )
    arr = np.asarray(img)
    colours = []
    for ix in range(3):
        x, y = _cell_center(bbox, ix=ix, iz=0, cell_px=10)
        colours.append(tuple(arr[y, x]))
    assert len(set(colours)) == 3


def test_empty_claimed_and_covered_render_cleanly() -> None:
    viz = GameVisualizer(cell_px=12)
    bbox = (-1, -1, 1, 1)
    img = viz.render_structured_map(
        agent_positions=[(0, 0)],
        agent_rotations=[{"y": 0.0}],
        reachable_cells={(0, 0), (1, 1)},
        claimed_cells={},
        covered_cells=[],
        world_bbox=bbox,
    )
    arr = np.asarray(img)
    x, y = _cell_center(bbox, ix=1, iz=1, cell_px=12)
    assert tuple(arr[y, x]) == (230, 230, 230)


def test_output_size_matches_bbox_plus_margin() -> None:
    viz = GameVisualizer(cell_px=15)
    bbox = (-2, -1, 1, 2)
    img = viz.render_structured_map(
        agent_positions=[(0, 0)],
        agent_rotations=[{"y": 0.0}],
        reachable_cells={(0, 0)},
        world_bbox=bbox,
    )
    cols = bbox[2] - bbox[0] + 1
    rows = bbox[3] - bbox[1] + 1
    assert img.size == (cols * 15 + 4, rows * 15 + 4)


def test_world_overhead_map_matches_bbox_plus_margin() -> None:
    viz = GameVisualizer(cell_px=15)
    bbox = (-2, -1, 1, 2)
    img = viz.render_world_overhead_map(
        agent_positions=[(0, 0)],
        covered_cells=[(0, 0)],
        world_bbox=bbox,
    )
    cols = bbox[2] - bbox[0] + 1
    rows = bbox[3] - bbox[1] + 1
    assert img.size == (cols * 15 + 4, rows * 15 + 4)


def test_world_overhead_map_draws_agent_in_expected_world_cell() -> None:
    viz = GameVisualizer(cell_px=12, agent_count=1)
    bbox = (10, 20, 11, 20)
    base = np.full((40, 40, 3), 128, dtype=np.uint8)
    img = viz.render_world_overhead_map(
        agent_positions=[(11, 20)],
        world_bbox=bbox,
        base_frame=base,
    )
    arr = np.asarray(img)
    x, y = _cell_center(bbox, ix=11, iz=20, cell_px=12)
    assert tuple(arr[y, x]) != (128, 128, 128)


def test_world_overhead_map_projects_marker_into_camera_frame() -> None:
    viz = GameVisualizer(cell_px=12, agent_count=1)
    bbox = (0, 0, 1, 1)
    base = np.full((80, 80, 3), 128, dtype=np.uint8)
    camera_pose = {
        "position": {"x": 0.125, "y": 2.0, "z": 0.125},
        "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
        "orthographicSize": 0.25,
        "orthographic": True,
    }
    img = viz.render_world_overhead_map(
        agent_positions=[(1, 1)],
        world_bbox=bbox,
        base_frame=base,
        camera_pose=camera_pose,
        grid_size=0.25,
    )
    arr = np.asarray(img)
    cx, cy = viz._project_overhead_world_point(  # noqa: SLF001 - direct geometry check
        x=0.25,
        z=0.25,
        camera_pose=camera_pose,
        image_size=img.size,
    )
    assert tuple(arr[int(round(cy)), int(round(cx))]) != (128, 128, 128)


def test_projected_structured_map_matches_requested_image_size() -> None:
    viz = GameVisualizer(cell_px=12, agent_count=1)
    camera_pose = {
        "position": {"x": 0.125, "y": 2.0, "z": 0.125},
        "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
        "orthographicSize": 0.25,
        "orthographic": True,
    }
    img = viz.render_projected_structured_map(
        agent_positions=[(1, 1)],
        agent_rotations=[{"y": 90.0}],
        reachable_cells={(1, 1)},
        world_bbox=(0, 0, 1, 1),
        camera_pose=camera_pose,
        image_size=(80, 60),
        grid_size=0.25,
    )
    assert img.size == (80, 60)


def test_projected_structured_map_yaw_zero_points_up() -> None:
    viz = GameVisualizer(cell_px=12, agent_count=1)
    camera_pose = {
        "position": {"x": 0.0, "y": 2.0, "z": 0.0},
        "rotation": {"x": 90.0, "y": 0.0, "z": 0.0},
        "orthographicSize": 0.25,
        "orthographic": True,
    }
    img = viz.render_projected_structured_map(
        agent_positions=[(0, 0)],
        agent_rotations=[{"y": 0.0}],
        reachable_cells={(0, 0)},
        world_bbox=(0, 0, 0, 0),
        camera_pose=camera_pose,
        image_size=(80, 80),
        grid_size=0.25,
    )
    arr = np.asarray(img)
    cell = arr[20:60, 20:60]
    up, down, left, right = _count_marker_pixels(cell)
    dominant = max(
        {"up": up, "down": down, "left": left, "right": right}.items(),
        key=lambda item: item[1],
    )[0]
    assert dominant == "up"

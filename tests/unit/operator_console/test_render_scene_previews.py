from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from scripts.operator_console.render_scene_previews import (
    PREVIEW_METADATA_SCHEMA,
    _first_public_waypoint,
    _preview_metadata,
    _render_semantic_map_preview,
    _scene_alignment,
    _scene_center_and_span,
    _topdown_camera_request,
)
from scripts.operator_console.semantic_map_preview import (
    semantic_map_preview_projection_summary,
)


def test_topdown_preview_request_uses_scene_camera_not_semantic_map() -> None:
    state = {
        "room_outlines": [
            {"center": [1.0, 2.0, 0.0], "half_extents": [2.0, 3.0]},
            {"center": [5.0, 4.0, 0.0], "half_extents": [1.0, 1.5]},
        ],
        "objects": {"mug_01": {"position": [6.0, 5.0, 0.8]}},
        "receptacles": {"sink_01": {"position": [-1.0, -1.0, 0.9]}},
    }

    request = _topdown_camera_request(state, width=900, height=560)

    view = request["views"][0]
    assert request["camera_model"] == "canonical_eye_target_camera_v1"
    assert request["render_resolution"] == {"width": 900, "height": 560}
    assert view["view_id"] == "topdown_scene"
    assert view["camera_basis"] == "whole_scene_true_topdown_aligned_to_semantic_map"
    assert view["eye"][2] > view["target"][2]
    assert view["eye"][:2] == pytest.approx(view["target"][:2])
    assert view["azimuth"] == pytest.approx(90.0)
    assert view["scene_alignment"]["schema"] == "operator_console_scene_alignment_v1"


def test_preview_metadata_marks_topdown_as_rendered_scene_not_map_fallback(
    tmp_path: Path,
) -> None:
    fpv_path = tmp_path / "molmospaces-val_9-fpv.png"
    map_path = tmp_path / "molmospaces-val_9-map.png"
    chase_path = tmp_path / "molmospaces-val_9-chase.png"
    topdown_path = tmp_path / "molmospaces-val_9-topdown.png"
    Image.new("RGB", (8, 8), (20, 30, 40)).save(fpv_path)
    Image.new("RGB", (8, 8), (30, 40, 50)).save(map_path)
    Image.new("RGB", (8, 8), (100, 120, 140)).save(chase_path)
    Image.new("RGB", (8, 8), (60, 90, 120)).save(topdown_path)
    scene_alignment = {
        "schema": "operator_console_scene_alignment_v1",
        "bounds": {"min_x": 0.0, "max_x": 4.0, "min_y": 0.0, "max_y": 3.0},
        "center": [2.0, 1.5, 0.4],
        "span_x_m": 4.0,
        "span_y_m": 3.0,
        "camera_span_m": 4.0,
        "screen_coordinate_convention": "screen_x_world_positive_x_screen_y_world_negative_y",
        "topdown_azimuth_deg": 90.0,
    }

    metadata = _preview_metadata(
        world_id="molmospaces/val_9",
        scene_index=9,
        seed=7,
        width=900,
        height=560,
        waypoint={"waypoint_id": "generated_exploration_001"},
        navigation={"status": "ok"},
        robot_views={
            "camera_diagnostics": {
                "views": {
                    "fpv": {"status": "ready", "camera_name": "robot_0/head_camera"},
                    "chase": {
                        "status": "ready",
                        "camera_name": "robot_0/camera_follower",
                    },
                }
            }
        },
        topdown_result={
            "views": [
                {
                    "view_id": "topdown_scene",
                    "eye": [1.0, 2.0, 10.0],
                    "target": [1.0, 2.0, 0.4],
                    "azimuth": 90.0,
                    "elevation": -90.0,
                    "distance": 9.6,
                }
            ]
        },
        topdown_request={"camera_model": "canonical_eye_target_camera_v1"},
        fpv_path=fpv_path,
        map_path=map_path,
        chase_path=chase_path,
        chase_waypoint={"waypoint_id": "generated_exploration_004"},
        chase_navigation={"status": "ok"},
        chase_robot_views={
            "camera_diagnostics": {
                "views": {
                    "chase": {
                        "status": "ready",
                        "camera_name": "robot_0/camera_follower",
                    }
                }
            }
        },
        chase_selection={
            "status": "alternate_waypoint_reviewable",
            "candidate_count_evaluated": 4,
        },
        topdown_path=topdown_path,
        scene_alignment=scene_alignment,
        semantic_projection={
            "schema": "operator_console_semantic_map_projection_v1",
            "waypoint_count": 2,
            "rendered_waypoint_count": 2,
            "room_remapped_waypoint_count": 1,
        },
    )

    assert metadata["schema"] == PREVIEW_METADATA_SCHEMA
    assert metadata["views"]["fpv"]["view"] == "raw_fpv"
    assert metadata["views"]["fpv"]["provenance"] == (
        "mujoco_robot_head_camera_first_public_waypoint"
    )
    assert metadata["views"]["chase"]["view"] == "chase_camera"
    assert metadata["views"]["chase"]["provenance"] == (
        "mujoco_robot_camera_follower_public_waypoint"
    )
    assert metadata["views"]["chase"]["waypoint_id"] == "generated_exploration_004"
    assert metadata["views"]["chase"]["selection_status"] == "alternate_waypoint_reviewable"
    assert metadata["views"]["chase"]["candidate_count_evaluated"] == 4
    assert metadata["views"]["chase"]["path"].endswith("-chase.png")
    assert metadata["views"]["chase"]["camera_diagnostics"]["camera_name"] == (
        "robot_0/camera_follower"
    )
    assert metadata["views"]["map"]["view"] == "semantic_map_aligned_preview"
    assert metadata["views"]["map"]["scene_alignment"] == scene_alignment
    assert metadata["views"]["map"]["semantic_projection"]["room_remapped_waypoint_count"] == 1
    assert metadata["views"]["topdown"]["view"] == "topdown_scene_render"
    assert metadata["views"]["topdown"]["camera_pose"]["azimuth"] == pytest.approx(90.0)
    assert metadata["views"]["topdown"]["scene_alignment"] == scene_alignment
    assert metadata["views"]["topdown"]["semantic_map_fallback"] is False
    assert metadata["views"]["topdown"]["path"].endswith("-topdown.png")
    assert metadata["views"]["topdown"]["image_diagnostics"]["visual_status"] == "low_detail"


def test_preview_helpers_use_first_public_waypoint_and_scene_bounds() -> None:
    waypoint = _first_public_waypoint(
        {"inspection_waypoints": [{"waypoint_id": "first"}, {"waypoint_id": "second"}]}
    )
    center, span = _scene_center_and_span(
        {"room_outlines": [{"center": [2.0, 3.0], "half_extents": [1.0, 2.0]}]}
    )

    assert waypoint["waypoint_id"] == "first"
    assert center == pytest.approx([2.0, 3.0, 0.4])
    assert span >= 4.0


def test_scene_alignment_expands_bounds_to_preview_aspect() -> None:
    alignment = _scene_alignment(
        {"room_outlines": [{"center": [2.0, 3.0], "half_extents": [1.0, 2.0]}]},
        width=900,
        height=560,
    )

    assert alignment["schema"] == "operator_console_scene_alignment_v1"
    assert (
        alignment["screen_coordinate_convention"]
        == "screen_x_world_positive_x_screen_y_world_negative_y"
    )
    assert alignment["topdown_azimuth_deg"] == pytest.approx(90.0)
    assert alignment["span_x_m"] / alignment["span_y_m"] == pytest.approx(900 / 560)


def test_semantic_map_preview_draws_scene_layers() -> None:
    state = {
        "room_outlines": [{"room_id": "room_1", "center": [1.0, 1.0], "half_extents": [1.0, 1.0]}],
        "receptacles": {"sink_01": {"position": [0.2, 0.4]}},
        "objects": {
            "mug_01": {"position": [1.4, 1.2]},
            "plate_01": {"position": [1.7, 0.8]},
        },
        "selected_object_ids": ["mug_01"],
        "robot_trajectory": [{"x": 0.1, "y": 0.1, "theta": 0.0}, {"x": 1.5, "y": 1.5}],
    }
    alignment = _scene_alignment(state, width=240, height=160)

    image = _render_semantic_map_preview(
        state,
        metric_map={"inspection_waypoints": [{"waypoint_id": "w1", "x": 0.5, "y": 0.5}]},
        alignment=alignment,
        world_label="molmospaces/val_0",
        width=240,
        height=160,
    )

    assert image.size == (240, 160)
    assert image.getbbox() is not None
    assert len(set(image.getdata())) > 1


def test_semantic_map_preview_draws_legend_even_without_scene_layers() -> None:
    image = _render_semantic_map_preview(
        {},
        metric_map={},
        alignment=_scene_alignment({}, width=320, height=220),
        world_label="molmospaces/val_0",
        width=320,
        height=220,
    )

    colors = set(image.getdata())
    assert (99, 102, 241) in colors  # public waypoint
    assert (86, 103, 140) in colors  # receptacle / surface
    assert (245, 158, 11) in colors  # movable object
    assert (239, 68, 68) in colors  # selected movable object
    assert (37, 99, 235) in colors  # robot path


def test_semantic_map_preview_remaps_abstract_waypoints_to_scene_room_bounds() -> None:
    state = {
        "room_outlines": [
            {
                "room_id": "room_10",
                "label": "Room 10",
                "center": [10.0, 10.0],
                "half_extents": [2.0, 4.0],
            }
        ],
    }
    metric_map = {
        "rooms": [
            {
                "room_id": "room_10",
                "polygon": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 2.0, "y": 0.0},
                    {"x": 2.0, "y": 2.0},
                    {"x": 0.0, "y": 2.0},
                ],
            }
        ],
        "inspection_waypoints": [
            {"waypoint_id": "generated_exploration_001", "room_id": "room_10", "x": 1.0, "y": 0.3}
        ],
    }
    alignment = _scene_alignment(state, width=240, height=160)

    summary = semantic_map_preview_projection_summary(
        state,
        metric_map=metric_map,
        alignment=alignment,
    )

    assert summary["waypoint_count"] == 1
    assert summary["rendered_waypoint_count"] == 1
    assert summary["room_remapped_waypoint_count"] == 1
    assert summary["raw_scene_waypoint_count"] == 0
    assert summary["skipped_waypoint_count"] == 0
    assert summary["projected_waypoint_bounds"]["min_x"] == pytest.approx(10.0)
    assert summary["projected_waypoint_bounds"]["max_y"] == pytest.approx(7.2)

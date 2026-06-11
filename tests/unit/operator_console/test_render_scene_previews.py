from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

from scripts.operator_console.render_scene_previews import (
    PREVIEW_METADATA_SCHEMA,
    _first_public_waypoint,
    _preview_metadata,
    _scene_center_and_span,
    _topdown_camera_request,
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
    assert view["camera_basis"] == "whole_scene_true_topdown"
    assert view["eye"][2] > view["target"][2]
    assert view["eye"][:2] == pytest.approx(view["target"][:2])


def test_preview_metadata_marks_topdown_as_rendered_scene_not_map_fallback(
    tmp_path: Path,
) -> None:
    fpv_path = tmp_path / "molmospaces-val_9-fpv.png"
    topdown_path = tmp_path / "molmospaces-val_9-topdown.png"
    Image.new("RGB", (8, 8), (20, 30, 40)).save(fpv_path)
    Image.new("RGB", (8, 8), (60, 90, 120)).save(topdown_path)

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
                "views": {"fpv": {"status": "ready", "camera_name": "robot_0/head_camera"}}
            }
        },
        topdown_result={
            "views": [
                {
                    "view_id": "topdown_scene",
                    "eye": [1.0, 2.0, 10.0],
                    "target": [1.0, 2.0, 0.4],
                }
            ]
        },
        topdown_request={"camera_model": "canonical_eye_target_camera_v1"},
        fpv_path=fpv_path,
        topdown_path=topdown_path,
    )

    assert metadata["schema"] == PREVIEW_METADATA_SCHEMA
    assert metadata["views"]["fpv"]["view"] == "raw_fpv"
    assert metadata["views"]["fpv"]["provenance"] == (
        "mujoco_robot_head_camera_first_public_waypoint"
    )
    assert metadata["views"]["topdown"]["view"] == "topdown_scene_render"
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
    assert span == pytest.approx(4.0)

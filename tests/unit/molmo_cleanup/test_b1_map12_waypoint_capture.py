from __future__ import annotations

import json
from pathlib import Path

from scripts.isaac_lab_cleanup.capture_b1_map12_waypoint_views import (
    DEFAULT_SCENE_XY_BOUNDS,
    build_waypoint_capture_request,
)


def test_b1_waypoint_capture_request_uses_waypoints_and_extra_points(tmp_path: Path) -> None:
    semantics = tmp_path / "semantics.json"
    semantics.write_text(
        json.dumps(
            {
                "inspection_waypoints": [
                    {
                        "waypoint_id": "meeting_room_a_center",
                        "frame_id": "map",
                        "x": -7.1,
                        "y": 2.65,
                        "yaw": 0.0,
                        "label": "Meeting room A",
                        "purpose": "reviewed_room_center",
                    },
                    {
                        "waypoint_id": "navmem_sink",
                        "frame_id": "map",
                        "x": -1.2,
                        "y": -5.0,
                        "yaw": 1.5,
                        "label": "Sink",
                        "purpose": "sink",
                    },
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    review = tmp_path / "review.json"
    review.write_text(
        json.dumps(
            {
                "labels": [
                    {
                        "label_id": "meeting_room_b",
                        "room_label": "Open kitchen",
                        "review_status": "accepted",
                        "geometry": {
                            "points": [
                                {"x": -4.0, "y": -1.0},
                                {"x": 2.0, "y": -1.0},
                                {"x": 2.0, "y": 5.0},
                                {"x": -4.0, "y": 5.0},
                            ]
                        },
                    }
                ]
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    request, manifest = build_waypoint_capture_request(
        semantics_path=semantics,
        review_manifest_path=review,
        width=320,
        height=180,
        scene_xy_bounds=DEFAULT_SCENE_XY_BOUNDS,
    )

    assert request["render_resolution"] == {"width": 320, "height": 180}
    assert manifest["waypoint_count"] == 2
    assert manifest["extra_point_count"] == 6
    assert manifest["point_count"] == 8
    assert request["point_capture"]["transform_status"] == "approx_bbox_fit_unverified"
    assert request["views"][0]["view_id"] == "wp_meeting_room_a_center"
    assert request["views"][0]["map_point"]["source"] == "inspection_waypoint"
    assert any(
        view["view_id"] == "extra_review_meeting_room_b_center" for view in request["views"]
    )
    assert any(view["view_id"] == "extra_map_center" for view in request["views"])

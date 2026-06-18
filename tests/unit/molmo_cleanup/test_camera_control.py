from __future__ import annotations

import pytest

from roboclaws.household.camera_control import (
    canonical_scene_camera_control_request,
    normalize_camera_control_request,
    scene_probe_camera_control_request,
)


def test_scene_probe_camera_control_request_rejects_bool_dimensions() -> None:
    with pytest.raises(ValueError, match="render_resolution.width must be a positive integer"):
        scene_probe_camera_control_request([{"target": [0.0, 0.0, 0.0]}], width=True, height=4)


def test_canonical_camera_control_request_rejects_non_positive_dimensions() -> None:
    with pytest.raises(ValueError, match="render_resolution.height must be a positive integer"):
        canonical_scene_camera_control_request(
            [{"eye": [0.0, 0.0, 1.0], "target": [1.0, 0.0, 1.0]}],
            width=6,
            height=0,
        )


def test_normalize_camera_control_list_requires_explicit_resolution() -> None:
    with pytest.raises(ValueError, match="render_resolution.width must be a positive integer"):
        normalize_camera_control_request([{"target": [0.0, 0.0, 0.0]}])


def test_normalize_camera_control_list_accepts_explicit_resolution() -> None:
    request = normalize_camera_control_request(
        [{"target": [0.0, 0.0, 0.0]}],
        width=6,
        height=4,
    )

    assert request["render_resolution"] == {"width": 6, "height": 4}
    assert request["views"][0]["view_id"] == "view_01"


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({"views": []}, "camera control request render_resolution must be an object"),
        (
            {"render_resolution": {"height": 4}, "views": []},
            "camera control request render_resolution.width is required",
        ),
        (
            {"render_resolution": {"width": "wide", "height": 4}, "views": []},
            "render_resolution.width must be a positive integer",
        ),
        (
            {"render_resolution": {"width": 6, "height": -1}, "views": []},
            "render_resolution.height must be a positive integer",
        ),
        (
            {"render_resolution": {"width": False, "height": 4}, "views": []},
            "render_resolution.width must be a positive integer",
        ),
    ],
)
def test_normalize_camera_control_dict_rejects_invalid_resolution(
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        normalize_camera_control_request(payload)


def test_normalize_camera_control_dict_accepts_valid_override_resolution() -> None:
    request = normalize_camera_control_request(
        {
            "render_resolution": {"width": "bad", "height": "also-bad"},
            "views": [{"target": [0.0, 0.0, 0.0]}],
        },
        width=8,
        height=5,
    )

    assert request["render_resolution"] == {"width": 8, "height": 5}
    assert request["views"][0]["view_id"] == "view_01"

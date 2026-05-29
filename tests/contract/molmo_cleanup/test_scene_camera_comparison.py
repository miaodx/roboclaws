from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.molmo_cleanup.camera_control import (
    CAMERA_CONTROL_API_NAME,
    DEFAULT_SCENE_PROBE_COLOR_PROFILE,
)
from roboclaws.molmo_cleanup.scene_camera_comparison import (
    ISAAC_LANE_ID,
    MOLMOSPACES_LANE_ID,
    SCENE_CAMERA_COMPARISON_SCHEMA,
    _camera_intrinsics_contract_from_capture,
    _camera_pose_contract_from_capture,
    _canonical_camera_control_views,
    _contact_sheet_entries,
    _image_pair_visual_delta,
    _image_visual_metrics,
    _isaac_view_specs,
    _molmospaces_view_specs,
    _projection_diagnostics,
    _room_camera_control_views,
    _room_scale_contract_from_capture,
    _scene_frame_transform_from_capture,
    render_scene_camera_comparison_report,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MOLMO_JUST = REPO_ROOT / "just" / "molmo.just"


def just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")


def _write_image(path: Path, color: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (64, 48), color=color).save(path)


def _manifest() -> dict[str, object]:
    return {
        "schema": SCENE_CAMERA_COMPARISON_SCHEMA,
        "purpose": (
            "Render-only scene identity probe. This does not execute household cleanup, "
            "pick, place, or scoring."
        ),
        "frame_mapping_note": (
            "MuJoCo and prepared Isaac USD expose different world frames for this scene. "
            "Views are matched by MolmoSpaces metadata handles and category anchors, then "
            "rendered through one Roboclaws camera-control request using the same anchor "
            "lens, lighting profile, color profile, and view ids."
        ),
        "camera_control": {
            "api_name": CAMERA_CONTROL_API_NAME,
            "camera_model": "canonical_eye_target_camera_v1",
            "coordinate_frame": "molmospaces_scene_frame_v1",
            "lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            },
            "lighting_profile": {
                "profile_id": "scene_probe_existing_usd_lights_v1",
                "isaac_dome_intensity": 0.0,
                "isaac_key_intensity": 0.0,
                "isaac_key_rotation_deg": [-55.0, 0.0, 35.0],
            },
            "color_profile": {
                "profile_id": "display_srgb_soft_highlight_v1",
                "highlight_knee": 225.0,
                "highlight_compression": 0.55,
            },
            "calibration_status": "canonical_scene_frame_similarity_fit_v1",
            "calibration_note": (
                "One Roboclaws camera-control request carries explicit eye/target/up poses."
            ),
            "request_artifact": "camera_control_request.json",
            "view_count": 2,
            "same_pose_contract": True,
        },
        "official_molmospaces_source": {
            "package": "molmo-spaces",
            "status": "installed",
            "url": "https://github.com/allenai/molmospaces.git",
            "vcs": "git",
            "commit_id": "3c50ae6093f7e4a4ef32529f8a773715da410a2f",
            "requested_revision": "3c50ae6093f7e4a4ef32529f8a773715da410a2f",
        },
        "artifacts": {
            "comparison_manifest": "comparison_manifest.json",
            "report": "report.html",
        },
        "scene_frame_transform": {
            "schema": "molmospaces_to_isaac_scene_transform_v1",
            "source_frame": "molmospaces_scene_frame_v1",
            "target_frame": "isaac_prepared_usd_world_frame",
            "diagnostic_kind": "camera_target_vs_isaac_usd_bounds",
            "status": "identity_checked_against_usd_bounds",
            "parity_status": "target_matches_usd_bounds_within_threshold",
            "target_residual_status": "target_matches_usd_bounds_within_threshold",
            "interpretation": "Target/geometry residual diagnostic, not camera pose residual.",
            "pair_count": 2,
            "xy_scale": 1.0,
            "rotation_z_deg": 0.0,
            "translation": [0.0, 0.0, 0.0],
            "residual_threshold_m": 0.08,
            "mean_residual_m": 0.03,
            "max_residual_m": 0.04,
            "mean_xy_residual_m": 0.02,
            "max_xy_residual_m": 0.022,
            "mean_z_residual_m": 0.0,
            "max_z_residual_m": 0.0,
            "pairs": [
                {
                    "anchor_id": "bed_01",
                    "category": "Bed",
                    "source": [2.8, 9.0, 0.8],
                    "target": [2.82, 9.01, 0.8],
                    "fitted": [2.8, 9.0, 0.8],
                    "residual_m": 0.022,
                    "xy_residual_m": 0.022,
                    "z_residual_m": 0.0,
                }
            ],
        },
        "camera_pose_contract": {
            "schema": "canonical_camera_pose_contract_v1",
            "camera_model": "canonical_eye_target_camera_v1",
            "coordinate_frame": "molmospaces_scene_frame_v1",
            "status": "same_backend_pose_within_threshold",
            "pair_count": 2,
            "pose_threshold_m": 0.005,
            "max_pose_delta_m": 0.0,
            "interpretation": "Backends reported the requested eye/target pose.",
            "pairs": [
                {
                    "view_id": "view_01_bed",
                    "anchor_id": "bed_01",
                    "category": "Bed",
                    "requested_eye": [0.2, 6.4, 2.6],
                    "requested_target": [2.8, 9.0, 0.8],
                    "molmospaces_backend_eye": [0.2, 6.4, 2.6],
                    "molmospaces_backend_target": [2.8, 9.0, 0.8],
                    "isaac_backend_eye": [0.2, 6.4, 2.6],
                    "isaac_backend_target": [2.8, 9.0, 0.8],
                    "backend_eye_delta_m": 0.0,
                    "backend_target_delta_m": 0.0,
                }
            ],
        },
        "camera_intrinsics_contract": {
            "schema": "canonical_camera_intrinsics_contract_v1",
            "status": "intrinsics_consistent",
            "camera_model": "canonical_eye_target_camera_v1",
            "resolution": {"width": 960, "height": 640},
            "requested_lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            },
            "molmospaces_lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            },
            "isaac_lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            },
            "isaac_derived_lens": {
                "focal_length_mm": 24.0,
                "horizontal_aperture_mm": 29.82337649086285,
            },
            "intrinsics_precedence": "vertical_fov_deg",
            "derived_from_vertical_fov": {
                "horizontal_aperture_mm": 29.82337649086285,
                "horizontal_fov_deg": 63.707,
            },
            "requested_vs_derived_horizontal_aperture_delta_mm": None,
            "interpretation": "The scene probe treats vertical_fov_deg as canonical.",
        },
        "projection_diagnostics": {
            "schema": "canonical_camera_projection_diagnostics_v1",
            "status": "same_projected_geometry_within_threshold",
            "projection_threshold_px": 0.5,
            "resolution": {"width": 960, "height": 640},
            "vertical_fov_deg": 45.0,
            "pair_count": 1,
            "max_pixel_delta": 0.0,
            "interpretation": "Projection geometry check.",
            "pairs": [
                {
                    "view_id": "view_01_bed",
                    "anchor_id": "bed_01",
                    "category": "Bed",
                    "point_count": 1,
                    "max_pixel_delta": 0.0,
                    "all_points_inside_frame": True,
                    "points": [
                        {
                            "label": "camera_target",
                            "world": [2.8, 9.0, 0.8],
                            "molmospaces_pixel": [480.0, 320.0],
                            "isaac_pixel": [480.0, 320.0],
                            "pixel_delta": 0.0,
                            "depth_m": 4.0,
                            "inside_frame": True,
                        }
                    ],
                }
            ],
        },
        "room_scale_contract": {
            "schema": "room_scale_contract_v1",
            "status": "room_outline_mesh_bounds",
            "room_count": 1,
            "room_outline_source": "molmospaces_room_outlines",
            "isaac_scene_bounds": {
                "size": [9.976, 10.097, 3.154],
                "center": [4.983, 5.043, 1.475],
            },
            "max_room_to_scene_width_ratio": 0.599,
            "max_room_to_scene_depth_ratio": 0.987,
            "interpretation": "Room-level camera poses are derived from room mesh world bounds.",
            "rooms": [
                {
                    "view_id": "room_01_room_2",
                    "room_id": "room_2",
                    "center": [2.99, 4.983],
                    "size": [5.98, 9.966],
                    "half_extents": [2.99, 4.983],
                    "provenance": "mujoco_room_mesh_world_bounds",
                }
            ],
        },
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 1,
            "seed": 7,
            "generated_mess_count": 1,
            "scene_usd_path": "/tmp/scene_semantic.usda",
            "render_width": 960,
            "render_height": 640,
        },
        "canonical_camera_views": [
            {
                "view_id": "room_01_room_2",
                "anchor_id": "room_2",
                "anchor_kind": "room",
                "category": "Room",
                "room_id": "room_2",
                "camera_basis": "room_center_inset_eye_target",
            },
            {
                "view_id": "view_01_bed",
                "anchor_id": "bed_01",
                "anchor_kind": "receptacle",
                "category": "Bed",
                "room_id": "room_2",
                "camera_basis": "near_topdown_anchor_orbit",
            },
            {
                "view_id": "view_02_sink",
                "anchor_id": "sink_01",
                "anchor_kind": "receptacle",
                "category": "Sink",
                "room_id": "room_3",
                "camera_basis": "near_topdown_anchor_orbit",
            },
        ],
        "room_camera_views": [
            {
                "view_id": "room_01_room_2",
                "anchor_id": "room_2",
                "anchor_kind": "room",
                "category": "Room",
                "room_id": "room_2",
                "camera_basis": "room_center_inset_eye_target",
                "room_outline": {
                    "center": [2.99, 4.983],
                    "half_extents": [2.99, 4.983],
                    "provenance": "mujoco_room_mesh_world_bounds",
                },
            }
        ],
        "anchors": [
            {
                "anchor_id": "bed_01",
                "anchor_kind": "receptacle",
                "category": "Bed",
                "room_id": "room_2",
                "molmospaces_position": [2.8, 9.0, 0.8],
                "room_center_xy": [2.7, 4.5],
                "isaac_support_position": [2.8, 9.0, 0.8],
                "isaac_usd_prim_path": "/val_1/Geometry/bed_01",
                "isaac_target_source": "Canonical explicit target",
            },
            {
                "anchor_id": "sink_01",
                "anchor_kind": "receptacle",
                "category": "Sink",
                "room_id": "room_3",
                "molmospaces_position": [9.6, 1.8, 0.5],
                "room_center_xy": [8.0, 3.0],
                "isaac_support_position": [9.6, 1.8, 0.5],
                "isaac_usd_prim_path": "/val_1/Geometry/sink_01",
                "isaac_target_source": "Canonical explicit target",
            },
        ],
        "lanes": {
            MOLMOSPACES_LANE_ID: {
                "status": "success",
                "python_executable": ".venv/bin/python",
                "runtime": {"python_version": "3.12.9", "mujoco_version": "3.3.0"},
                "scene_xml": "/tmp/val_1.xml",
                "visual_artifact_provenance": "mujoco_camera_control_canonical_eye_target",
                "camera_control_api": CAMERA_CONTROL_API_NAME,
                "calibration_status": "canonical_scene_frame_similarity_fit_v1",
                "lighting_profile": {"profile_id": "scene_probe_existing_usd_lights_v1"},
                "color_profile": {"profile_id": "display_srgb_soft_highlight_v1"},
                "images": {
                    "room_01_room_2": {
                        "path": "molmospaces/camera_views/room_01_room_2.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "view_01_bed": {
                        "path": "molmospaces/camera_views/view_01_bed.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "view_02_sink": {
                        "path": "molmospaces/camera_views/view_02_sink.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                },
                "views": [
                    {
                        "view_id": "room_01_room_2",
                        "eye": [1.0, 2.0, 1.45],
                        "target": [2.0, 3.0, 1.45],
                        "backend_eye": [1.0, 2.0, 1.45],
                        "backend_target": [2.0, 3.0, 1.45],
                    },
                    {
                        "view_id": "view_01_bed",
                        "eye": [0.2, 6.4, 2.6],
                        "target": [2.8, 9.0, 0.8],
                        "backend_eye": [0.2, 6.4, 2.6],
                        "backend_target": [2.8, 9.0, 0.8],
                    },
                    {
                        "view_id": "view_02_sink",
                        "eye": [7.0, -1.4, 2.6],
                        "target": [9.6, 1.8, 0.6],
                        "backend_eye": [7.0, -1.4, 2.6],
                        "backend_target": [9.6, 1.8, 0.6],
                    },
                ],
            },
            ISAAC_LANE_ID: {
                "status": "success",
                "python_executable": ".venv-isaaclab/bin/python",
                "runtime": {"python_version": "3.12.9", "isaac_lab_version": "2.2.0"},
                "scene_usd": "/tmp/scene_semantic.usda",
                "visual_artifact_provenance": (
                    "isaac_lab_camera_rgb_canonical_eye_target_scene_probe"
                ),
                "camera_control_api": CAMERA_CONTROL_API_NAME,
                "calibration_status": "canonical_scene_frame_similarity_fit_v1",
                "lighting_profile": {"profile_id": "scene_probe_existing_usd_lights_v1"},
                "color_profile": {"profile_id": "display_srgb_soft_highlight_v1"},
                "lighting_diagnostics": {
                    "status": "using_existing_stage_lights",
                    "existing_light_count": 2,
                    "added_light_count": 0,
                },
                "images": {
                    "room_01_room_2": {
                        "path": "isaaclab/camera_views/room_01_room_2.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "view_01_bed": {
                        "path": "isaaclab/camera_views/view_01_bed.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                    "view_02_sink": {
                        "path": "isaaclab/camera_views/view_02_sink.png",
                        "dimensions": {"width": 64, "height": 48, "channels": 3},
                    },
                },
                "views": [
                    {
                        "view_id": "room_01_room_2",
                        "eye": [1.0, 2.0, 1.45],
                        "target": [2.0, 3.0, 1.45],
                        "backend_eye": [1.0, 2.0, 1.45],
                        "backend_target": [2.0, 3.0, 1.45],
                    },
                    {
                        "view_id": "view_01_bed",
                        "eye": [0.2, 6.4, 2.6],
                        "target": [2.8, 9.0, 0.8],
                        "backend_eye": [0.2, 6.4, 2.6],
                        "backend_target": [2.8, 9.0, 0.8],
                    },
                    {
                        "view_id": "view_02_sink",
                        "eye": [7.0, -1.4, 2.6],
                        "target": [9.6, 1.8, 0.6],
                        "backend_eye": [7.0, -1.4, 2.6],
                        "backend_target": [9.6, 1.8, 0.6],
                    },
                ],
            },
        },
        "view_specs": {
            "room-level-canonical": [],
            MOLMOSPACES_LANE_ID: [],
            ISAAC_LANE_ID: [],
        },
    }


def test_scene_camera_comparison_report_is_render_only_and_side_by_side(tmp_path: Path) -> None:
    manifest = _manifest()
    for lane in manifest["lanes"].values():  # type: ignore[index,union-attr]
        for image in lane["images"].values():  # type: ignore[index,union-attr]
            _write_image(tmp_path / image["path"], color=(20, 80, 120))  # type: ignore[index]

    report_path = render_scene_camera_comparison_report(manifest, output_dir=tmp_path)
    html = report_path.read_text(encoding="utf-8")

    assert report_path == tmp_path / "report.html"
    assert (tmp_path / "contact_sheet.png").is_file()
    assert manifest["artifacts"]["contact_sheet"] == "contact_sheet.png"  # type: ignore[index]
    assert manifest["contact_sheet"]["view_count"] == 3  # type: ignore[index]
    assert "Render-only scene identity probe" in html
    assert "Contact Sheet" in html
    assert "contact_sheet.png" in html
    assert "does not execute household cleanup" in html
    assert "pick, place, or scoring" in html
    assert "MolmoSpaces metadata handle" in html
    assert "Camera Pose Contract" in html
    assert "Camera Intrinsics Contract" in html
    assert "Room Scale Contract" in html
    assert "Target Vs USD Bounds Diagnostics" in html
    assert "Projection Diagnostics" in html
    assert "Visual Diagnostics" in html
    assert "same_backend_pose_within_threshold" in html
    assert "same_projected_geometry_within_threshold" in html
    assert "intrinsics_consistent" in html
    assert "mujoco_room_mesh_world_bounds" in html
    assert "room_center_inset_eye_target" in html
    assert "https://github.com/allenai/molmospaces.git" in html
    assert CAMERA_CONTROL_API_NAME in html
    assert "canonical_scene_frame_similarity_fit_v1" in html
    assert "display_srgb_soft_highlight_v1" in html
    assert "canonical_eye_target_camera_v1" in html
    assert "backend eye=" in html
    assert "scene_probe_existing_usd_lights_v1" in html
    assert "using_existing_stage_lights" in html
    assert MOLMOSPACES_LANE_ID in html
    assert ISAAC_LANE_ID in html
    assert "molmospaces/camera_views/view_01_bed.png" in html
    assert "molmospaces/camera_views/room_01_room_2.png" in html
    assert "isaaclab/camera_views/view_02_sink.png" in html
    assert "Pick up" not in html


def test_scene_camera_visual_metrics_quantify_brightness_delta(tmp_path: Path) -> None:
    dark = tmp_path / "dark.png"
    bright = tmp_path / "bright.png"
    _write_image(dark, color=(10, 20, 30))
    _write_image(bright, color=(110, 120, 130))

    dark_metrics = _image_visual_metrics(dark)
    bright_metrics = _image_visual_metrics(bright)
    delta = _image_pair_visual_delta(dark, bright)

    assert dark_metrics["mean_rgb"] == pytest.approx([10.0, 20.0, 30.0])
    assert bright_metrics["mean_luminance"] > dark_metrics["mean_luminance"]
    assert dark_metrics["overexposed_fraction"] == 0.0
    assert delta["mean_absolute_pixel_delta"] == pytest.approx(100.0)


def test_scene_camera_projection_diagnostics_quantify_same_pinhole_geometry() -> None:
    manifest = _manifest()
    diagnostics = _projection_diagnostics(manifest)

    assert diagnostics["status"] == "same_projected_geometry_within_threshold"
    assert diagnostics["max_pixel_delta"] == pytest.approx(0.0)
    assert diagnostics["vertical_fov_deg"] == pytest.approx(45.0)
    assert diagnostics["resolution"] == {"width": 960, "height": 640}
    bed = next(item for item in diagnostics["pairs"] if item["view_id"] == "view_01_bed")
    target = next(point for point in bed["points"] if point["label"] == "camera_target")
    assert target["molmospaces_pixel"] == pytest.approx(target["isaac_pixel"])
    assert target["inside_frame"] is True


def test_scene_camera_contact_sheet_entries_require_existing_lane_images(tmp_path: Path) -> None:
    manifest = _manifest()
    _write_image(
        tmp_path / "molmospaces/camera_views/room_01_room_2.png",
        color=(20, 80, 120),
    )
    _write_image(
        tmp_path / "isaaclab/camera_views/room_01_room_2.png",
        color=(100, 120, 140),
    )

    entries = _contact_sheet_entries(manifest, output_dir=tmp_path)

    assert [entry["view_id"] for entry in entries] == ["room_01_room_2"]
    assert set(entries[0]["images"]) == {MOLMOSPACES_LANE_ID, ISAAC_LANE_ID}


def test_scene_camera_comparison_manifest_is_json_serializable() -> None:
    encoded = json.dumps(_manifest(), sort_keys=True)

    assert SCENE_CAMERA_COMPARISON_SCHEMA in encoded
    assert "private_manifest" not in encoded
    assert "_state" not in encoded


def test_scene_camera_comparison_default_color_profile_contract() -> None:
    assert DEFAULT_SCENE_PROBE_COLOR_PROFILE["profile_id"] == "display_srgb_soft_highlight_v1"
    assert DEFAULT_SCENE_PROBE_COLOR_PROFILE["highlight_knee"] == 225.0
    assert DEFAULT_SCENE_PROBE_COLOR_PROFILE["highlight_compression"] == 0.55


def test_isaac_view_specs_record_support_pose_for_transform_but_not_camera_target(
    tmp_path: Path,
) -> None:
    scene_dir = tmp_path / "flattened-semantic-usd" / "scene"
    scene_dir.mkdir(parents=True)
    scene_usd = scene_dir / "scene_semantic.usda"
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")
    (scene_dir / "scene_metadata.json").write_text(
        json.dumps({"objects": {"sink_01": {"category": "Sink", "is_static": True}}}),
        encoding="utf-8",
    )
    index_dir = tmp_path / "cleanup-smoke" / "latest"
    index_dir.mkdir(parents=True)
    (index_dir / "isaac_scene_index.json").write_text(
        json.dumps(
            {
                "scene_usd": str(scene_usd),
                "receptacle_index": {
                    "sink_01": {
                        "usd_prim_path": "/val_1/Geometry/sink_01",
                        "support_pose": {"x": 123.0, "y": 456.0, "z": 0.0},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    anchors = [
        {
            "anchor_id": "sink_01",
            "anchor_kind": "receptacle",
            "category": "Sink",
            "room_id": "room_3",
            "molmospaces_position": [9.5, 1.8, 0.5],
        }
    ]

    specs = _isaac_view_specs(anchors, scene_usd_path=scene_usd, scene_index=1)

    assert specs == [
        {
            "view_id": "view_01_sink",
            "label": "room_3 Sink sink_01",
            "anchor_id": "sink_01",
            "anchor_kind": "receptacle",
            "usd_prim_path": "/val_1/Geometry/sink_01",
            "target_source": "isaac_worker_usd_prim_world_bounds_diagnostic",
            "isaac_support_position": [123.0, 456.0, 0.0],
            "min_target_z": 0.6,
        }
    ]
    assert "target" not in specs[0]
    assert "eye" not in specs[0]
    assert anchors[0]["isaac_usd_prim_path"] == "/val_1/Geometry/sink_01"
    assert anchors[0]["isaac_support_position"] == [123.0, 456.0, 0.0]


def test_canonical_camera_control_views_carry_explicit_pose_not_lane_orbit() -> None:
    anchors = [
        {
            "anchor_id": "table_01",
            "anchor_kind": "receptacle",
            "category": "DiningTable",
            "room_id": "room_2",
            "molmospaces_position": [2.7, 5.9, 0.37],
            "molmospaces_support_top_z": 0.75,
            "room_center_xy": [2.7, 4.5],
        }
    ]
    molmo_specs = _molmospaces_view_specs(anchors)
    isaac_specs = [
        {
            "view_id": "view_01_diningtable",
            "label": "room_2 DiningTable table_01",
            "anchor_id": "table_01",
            "anchor_kind": "receptacle",
            "usd_prim_path": "/val_1/Geometry/table_01",
            "target_source": "isaac_worker_usd_prim_world_bounds_diagnostic",
            "isaac_support_position": [2.7, 5.9, 0.37],
            "min_target_z": 0.6,
        }
    ]

    views = _canonical_camera_control_views(
        anchors,
        molmo_specs=molmo_specs,
        isaac_specs=isaac_specs,
        scene_transform={
            "status": "identity_pending_render_diagnostics",
            "xy_scale": 1.0,
            "rotation_z_deg": 0.0,
            "translation": [0.0, 0.0, 0.0],
        },
    )

    assert views[0]["camera_model"] == "canonical_eye_target_camera_v1"
    assert views[0]["coordinate_frame"] == "molmospaces_scene_frame_v1"
    assert views[0]["target"] == pytest.approx([2.7, 5.9, 1.0])
    assert views[0]["eye"][2] > views[0]["target"][2]
    assert views[0]["camera_basis"] == "near_topdown_anchor_orbit"
    assert "lane_camera_orbits" not in views[0]


def test_room_camera_control_views_use_same_canonical_pose_contract() -> None:
    views = _room_camera_control_views(
        {
            "room_outlines": [
                {
                    "room_id": "room_2",
                    "label": "Room 2",
                    "center": [2.0, 4.0],
                    "half_extents": [3.0, 2.0],
                    "provenance": "mujoco_room_geom",
                }
            ]
        }
    )

    assert views == [
        {
            "view_id": "room_01_room_2",
            "label": "Room 2 canonical room view",
            "anchor_id": "room_2",
            "anchor_kind": "room",
            "category": "Room",
            "room_id": "room_2",
            "camera_mode": "canonical_eye_target",
            "camera_model": "canonical_eye_target_camera_v1",
            "coordinate_frame": "molmospaces_scene_frame_v1",
            "coordinate_convention": "molmospaces_scene_frame_v1",
            "calibration_status": "canonical_scene_frame_similarity_fit_v1",
            "eye": pytest.approx([0.95, 3.3, 1.45]),
            "target": pytest.approx([2.0, 4.0, 1.45]),
            "lookat": pytest.approx([2.0, 4.0, 1.45]),
            "up": [0.0, 0.0, 1.0],
            "camera_basis": "room_center_inset_eye_target",
            "target_source": {
                MOLMOSPACES_LANE_ID: "molmospaces_room_outline_center",
                ISAAC_LANE_ID: "canonical_explicit_room_target_from_molmospaces_scene_frame",
            },
            "lane_targets": {
                MOLMOSPACES_LANE_ID: {
                    "lookat": pytest.approx([2.0, 4.0, 1.45]),
                    "room_id": "room_2",
                },
                ISAAC_LANE_ID: {"room_id": "room_2"},
            },
            "room_outline": {
                "center": [2.0, 4.0],
                "half_extents": [3.0, 2.0],
                "provenance": "mujoco_room_geom",
            },
        }
    ]
    assert "lane_camera_orbits" not in views[0]


def test_scene_frame_transform_from_capture_uses_usd_bounds_distance() -> None:
    transform = _scene_frame_transform_from_capture(
        canonical_views=[
            {
                "view_id": "view_01_table",
                "anchor_id": "table_01",
                "category": "DiningTable",
                "target": [2.7, 5.9, 1.0],
            }
        ],
        isaac_lane={
            "views": [
                {
                    "view_id": "view_01_table",
                    "usd_bounds_target": [2.72, 5.94, 0.6],
                    "usd_bounds": {
                        "min": [2.0, 5.0, 0.3],
                        "max": [3.0, 6.0, 1.2],
                        "center": [2.5, 5.5, 0.75],
                    },
                }
            ]
        },
    )

    assert transform["status"] == "identity_checked_against_usd_bounds"
    assert transform["diagnostic_kind"] == "camera_target_vs_isaac_usd_bounds"
    assert (
        transform["target_residual_status"]
        == "target_inside_or_near_usd_bounds_with_surface_aim_allowance"
    )
    assert transform["max_residual_m"] == pytest.approx(0.402492, rel=1e-4)
    assert transform["max_xy_residual_m"] == pytest.approx(0.044721, rel=1e-4)
    assert transform["max_z_residual_m"] == pytest.approx(0.4)
    assert transform["max_distance_to_usd_bounds_m"] == pytest.approx(0.0)
    assert transform["max_surface_aim_distance_to_usd_bounds_m"] == pytest.approx(0.0)
    assert transform["target_inside_usd_xy_bounds_count"] == 1
    assert transform["target_inside_usd_xyz_bounds_count"] == 1


def test_scene_frame_transform_from_capture_flags_targets_outside_usd_bounds() -> None:
    transform = _scene_frame_transform_from_capture(
        canonical_views=[
            {
                "view_id": "view_01_table",
                "anchor_id": "table_01",
                "category": "DiningTable",
                "target": [4.0, 5.9, 1.0],
            }
        ],
        isaac_lane={
            "views": [
                {
                    "view_id": "view_01_table",
                    "usd_bounds_target": [2.72, 5.94, 0.6],
                    "usd_bounds": {
                        "min": [2.0, 5.0, 0.3],
                        "max": [3.0, 6.0, 1.2],
                        "center": [2.5, 5.5, 0.75],
                    },
                }
            ]
        },
    )

    assert transform["target_residual_status"] == "target_definition_residual_high"
    assert transform["max_distance_to_usd_bounds_m"] == pytest.approx(1.0)
    assert transform["target_inside_usd_xy_bounds_count"] == 0


def test_scene_frame_transform_from_capture_accepts_surface_aim_above_usd_bounds() -> None:
    transform = _scene_frame_transform_from_capture(
        canonical_views=[
            {
                "view_id": "view_01_table",
                "anchor_id": "table_01",
                "category": "DiningTable",
                "target": [2.7, 5.9, 1.0],
            }
        ],
        isaac_lane={
            "views": [
                {
                    "view_id": "view_01_table",
                    "usd_bounds_target": [2.72, 5.94, 0.6],
                    "usd_bounds": {
                        "min": [2.0, 5.0, 0.3],
                        "max": [3.0, 6.0, 0.75],
                        "center": [2.5, 5.5, 0.525],
                    },
                }
            ]
        },
    )

    assert (
        transform["target_residual_status"]
        == "target_inside_or_near_usd_bounds_with_surface_aim_allowance"
    )
    assert transform["max_distance_to_usd_bounds_m"] == pytest.approx(0.25)
    assert transform["max_surface_aim_distance_to_usd_bounds_m"] == pytest.approx(0.0)
    assert transform["target_inside_usd_xy_bounds_count"] == 1
    assert transform["target_inside_usd_xyz_bounds_count"] == 0


def test_camera_pose_contract_from_capture_checks_backend_pose_delta() -> None:
    contract = _camera_pose_contract_from_capture(
        canonical_views=[
            {
                "view_id": "view_01_table",
                "anchor_id": "table_01",
                "category": "DiningTable",
                "eye": [1.0, 2.0, 3.0],
                "target": [2.7, 5.9, 1.0],
            }
        ],
        molmospaces_lane={
            "views": [
                {
                    "view_id": "view_01_table",
                    "backend_eye": [1.0, 2.0, 3.0],
                    "backend_target": [2.7, 5.9, 1.0],
                }
            ]
        },
        isaac_lane={
            "views": [
                {
                    "view_id": "view_01_table",
                    "backend_eye": [1.0, 2.0, 3.0],
                    "backend_target": [2.7, 5.9, 1.0],
                    "usd_bounds_target": [2.72, 5.94, 0.6],
                }
            ]
        },
    )

    assert contract["status"] == "same_backend_pose_within_threshold"
    assert contract["max_pose_delta_m"] == pytest.approx(0.0)
    assert contract["pairs"][0]["backend_eye_delta_m"] == pytest.approx(0.0)
    assert contract["pairs"][0]["backend_target_delta_m"] == pytest.approx(0.0)


def test_camera_intrinsics_contract_declares_vertical_fov_precedence() -> None:
    contract = _camera_intrinsics_contract_from_capture(
        requested_lens={
            "vertical_fov_deg": 45.0,
            "focal_length_mm": 24.0,
        },
        requested_resolution={"width": 960, "height": 640},
        molmospaces_lane={
            "lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            }
        },
        isaac_lane={
            "lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
            },
            "derived_lens": {
                "focal_length_mm": 24.0,
                "horizontal_aperture_mm": 29.82337649086285,
            },
        },
    )

    assert contract["status"] == "intrinsics_consistent"
    assert contract["intrinsics_precedence"] == "vertical_fov_deg"
    assert contract["derived_from_vertical_fov"]["horizontal_aperture_mm"] == pytest.approx(
        29.82337649
    )
    assert contract["requested_vs_derived_horizontal_aperture_delta_mm"] is None


def test_room_scale_contract_compares_room_outline_to_isaac_scene_bounds() -> None:
    contract = _room_scale_contract_from_capture(
        room_views=[
            {
                "view_id": "room_01_room_2",
                "room_id": "room_2",
                "room_outline": {
                    "center": [2.99, 4.983],
                    "half_extents": [2.99, 4.983],
                    "provenance": "mujoco_room_mesh_world_bounds",
                },
            }
        ],
        isaac_lane={"scene_bounds": {"size": [9.976, 10.097, 3.154]}},
    )

    assert contract["status"] == "room_outline_mesh_bounds"
    assert contract["room_count"] == 1
    assert contract["rooms"][0]["size"] == pytest.approx([5.98, 9.966])
    assert contract["max_room_to_scene_width_ratio"] == pytest.approx(0.5994, rel=1e-3)
    assert contract["max_room_to_scene_depth_ratio"] == pytest.approx(0.987, rel=1e-3)


def test_molmospaces_view_specs_use_anchor_orbit_not_focus_camera_heuristic() -> None:
    anchors = [
        {
            "anchor_id": "table_01",
            "anchor_kind": "receptacle",
            "category": "DiningTable",
            "room_id": "room_2",
            "molmospaces_position": [2.7, 5.9, 0.37],
            "molmospaces_support_top_z": 0.75,
        }
    ]

    specs = _molmospaces_view_specs(anchors)

    assert specs[0] == {
        "view_id": "view_01_diningtable",
        "label": "room_2 DiningTable table_01",
        "anchor_id": "table_01",
        "anchor_kind": "receptacle",
        "camera_mode": "anchor_orbit",
        "focus_receptacle_id": "table_01",
        "lookat": [2.7, 5.9, 1.0],
        "target_source": "molmospaces_metadata_anchor_position",
        "camera_orbit": {"distance_m": 4.4, "azimuth_deg": 90.0, "elevation_deg": 28.0},
    }
    assert "robot_pose" not in specs[0]


def test_scene_camera_comparison_recipe_checks_prepared_usd_before_running(tmp_path: Path) -> None:
    molmo_python = tmp_path / "molmo-python"
    isaac_python = tmp_path / "isaac-python"
    missing_usd = tmp_path / "missing.usda"
    for runtime in (molmo_python, isaac_python):
        runtime.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
        runtime.chmod(0o755)

    env = os.environ.copy()
    env.pop("ROBOCLAWS_JUST_TRACE", None)
    env["ROBOCLAWS_MOLMOSPACES_PYTHON"] = str(molmo_python)
    env["ROBOCLAWS_ISAACLAB_PYTHON"] = str(isaac_python)
    result = subprocess.run(
        [
            just_bin(),
            "-f",
            str(MOLMO_JUST),
            "scene-camera-comparison",
            "seed=7",
            "generated_mess_count=1",
            "output_dir=output/molmo/scene-camera-comparison",
            "scene_source=procthor-10k-val",
            "scene_index=1",
            f"scene_usd_path={missing_usd}",
        ],
        cwd=tmp_path,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "missing prepared scene USD" in result.stderr
    assert str(missing_usd) in result.stderr

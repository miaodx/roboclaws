from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.molmo_cleanup.camera_control import CAMERA_CONTROL_API_NAME
from roboclaws.molmo_cleanup.scene_camera_comparison import (
    ISAAC_LANE_ID,
    MOLMOSPACES_LANE_ID,
    SCENE_CAMERA_COMPARISON_SCHEMA,
    _canonical_camera_control_views,
    _isaac_view_specs,
    _molmospaces_view_specs,
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
            "lens, lighting profile, and view ids."
        ),
        "camera_control": {
            "api_name": CAMERA_CONTROL_API_NAME,
            "camera_model": "canonical_eye_target_camera_v1",
            "coordinate_frame": "molmospaces_scene_frame_v1",
            "lens": {
                "vertical_fov_deg": 45.0,
                "focal_length_mm": 24.0,
                "horizontal_aperture_mm": 20.955,
            },
            "lighting_profile": {
                "profile_id": "scene_probe_soft_v1",
                "isaac_dome_intensity": 250.0,
                "isaac_key_intensity": 850.0,
                "isaac_key_rotation_deg": [-55.0, 0.0, 35.0],
            },
            "calibration_status": "canonical_scene_frame_similarity_fit_v1",
            "calibration_note": (
                "One Roboclaws camera-control request carries explicit eye/target/up poses."
            ),
            "request_artifact": "camera_control_request.json",
            "view_count": 2,
            "same_pose_contract": True,
        },
        "scene_frame_transform": {
            "schema": "molmospaces_to_isaac_scene_transform_v1",
            "source_frame": "molmospaces_scene_frame_v1",
            "target_frame": "isaac_prepared_usd_world_frame",
            "status": "identity_checked_against_usd_bounds",
            "parity_status": "canonical_pose_fit_within_threshold",
            "pair_count": 2,
            "xy_scale": 1.0,
            "rotation_z_deg": 0.0,
            "translation": [0.0, 0.0, 0.0],
            "residual_threshold_m": 0.08,
            "mean_residual_m": 0.03,
            "max_residual_m": 0.04,
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
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": 1,
            "seed": 7,
            "generated_mess_count": 1,
            "scene_usd_path": "/tmp/scene_semantic.usda",
            "render_width": 960,
            "render_height": 640,
        },
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
                "isaac_target_source": "Isaac scene-index support pose",
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
                "isaac_target_source": "Isaac scene-index support pose",
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
                "lighting_profile": {"profile_id": "scene_probe_soft_v1"},
                "images": {
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
                "lighting_profile": {"profile_id": "scene_probe_soft_v1"},
                "images": {
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
                    {"view_id": "view_01_bed", "eye": [0.1, -3.0, 2.6], "target": [2.7, 0.6, 0.8]},
                    {
                        "view_id": "view_02_sink",
                        "eye": [-0.4, -1.6, 2.6],
                        "target": [2.2, 1.6, 0.6],
                    },
                ],
            },
        },
        "view_specs": {
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
    assert "Render-only scene identity probe" in html
    assert "does not execute household cleanup" in html
    assert "pick, place, or scoring" in html
    assert "MolmoSpaces metadata handle" in html
    assert "Scene Frame Transform" in html
    assert CAMERA_CONTROL_API_NAME in html
    assert "canonical_scene_frame_similarity_fit_v1" in html
    assert "canonical_eye_target_camera_v1" in html
    assert "backend eye=" in html
    assert "scene_probe_soft_v1" in html
    assert MOLMOSPACES_LANE_ID in html
    assert ISAAC_LANE_ID in html
    assert "molmospaces/camera_views/view_01_bed.png" in html
    assert "isaaclab/camera_views/view_02_sink.png" in html
    assert "Pick up" not in html


def test_scene_camera_comparison_manifest_is_json_serializable() -> None:
    encoded = json.dumps(_manifest(), sort_keys=True)

    assert SCENE_CAMERA_COMPARISON_SCHEMA in encoded
    assert "private_manifest" not in encoded
    assert "_state" not in encoded


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
            "target_source": "isaac_scene_index_support_pose",
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
            "target_source": "isaac_scene_index_support_pose",
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


def test_scene_frame_transform_from_capture_uses_usd_bounds_residuals() -> None:
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
                    "usd_bounds_target": [2.72, 5.94, 1.0],
                }
            ]
        },
    )

    assert transform["status"] == "identity_checked_against_usd_bounds"
    assert transform["parity_status"] == "canonical_pose_fit_within_threshold"
    assert transform["max_residual_m"] == pytest.approx(0.044721, rel=1e-4)
    assert transform["max_xy_residual_m"] == pytest.approx(0.044721, rel=1e-4)
    assert transform["max_z_residual_m"] == pytest.approx(0.0)


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

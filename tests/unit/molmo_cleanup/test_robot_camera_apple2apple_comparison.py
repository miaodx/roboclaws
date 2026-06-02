from __future__ import annotations

import importlib.util
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_CAMERA_COMPARISON_PATH = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_robot_camera_apple2apple_comparison.py"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_robot_camera_image_diff_reports_color_residual(tmp_path: Path) -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_color_residual",
    )
    left_path = tmp_path / "mujoco.png"
    right_path = tmp_path / "isaac.png"
    Image.new("RGB", (12, 8), (120, 120, 120)).save(left_path)
    Image.new("RGB", (12, 8), (60, 60, 60)).save(right_path)

    diff = run_camera._image_diff(left_path, right_path)

    assert diff["mean_abs_rgb"] == 60.0
    assert diff["diff_gt_40_fraction"] == 1.0
    assert diff["diff_gt_80_fraction"] == 0.0
    assert diff["residual"]["schema"] == "robot_camera_render_residual_diagnostics_v1"
    assert diff["residual"]["residual_class"] == "view_dependent_color_residual"
    assert diff["residual"]["rgb_gain_oracle"]["mean_abs_rgb_after_gain"] == 0.0


def test_robot_camera_residual_triage_prioritizes_geometry_edges() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_geometry_residual",
    )
    left = Image.new("RGB", (32, 32), (0, 0, 0))
    ImageDraw.Draw(left).rectangle((0, 0, 15, 31), fill=(255, 255, 255))
    right = Image.new("RGB", (32, 32), (0, 0, 0))

    residual = run_camera._render_residual_diagnostics(left, right)

    assert residual["residual_class"] == "geometry_or_texture_edge_residual"
    assert residual["edge_abs_diff"] > 8.0
    summary = run_camera._summary(
        [
            {
                "status": "success",
                "image_diffs": {
                    "fpv": {
                        "mean_abs_rgb": 80.0,
                        "residual": residual,
                    },
                    "chase": {
                        "mean_abs_rgb": 32.0,
                        "residual": {
                            "residual_class": "low_residual",
                            "rgb_gain_oracle": {"mean_abs_rgb_after_gain": 30.0},
                            "edge_abs_diff": 1.0,
                        },
                    },
                },
            }
        ]
    )

    triage = summary["residual_triage"]
    assert triage["schema"] == "robot_camera_render_residual_triage_v1"
    assert triage["status"] == "render_domain_geometry_or_texture_residual"
    assert triage["views"]["fpv"]["residual_classes"] == {"geometry_or_texture_edge_residual": 1}
    assert "geometry/material/texture" in triage["recommended_next_action"]


def test_robot_camera_contract_diagnostics_flags_static_isaac_head_pitch_gap() -> None:
    run_camera = _load_module(
        RUN_CAMERA_COMPARISON_PATH,
        "run_robot_camera_apple2apple_comparison_contract_diagnostics",
    )
    robot_pose = {
        "x": 6.37057,
        "y": 8.8752,
        "theta": 1.57079632679,
        "yaw_deg": 90.0,
        "head_pitch": 0.653613,
        "pose_source": "apple2apple_shared_robot_pose",
    }
    location = {
        "status": "success",
        "robot_pose": robot_pose,
        "contracts": {
            "mujoco": {
                "agent_facing_fpv": {
                    "source": "robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {"source": "mujoco_focus_camera"},
                "robot_pose": dict(robot_pose),
            },
            "isaac": {
                "agent_facing_fpv": {
                    "source": "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
                    "camera_prim_path": "/World/robot_0/head_camera",
                    "robot_mounted": True,
                    "head_camera_equivalent": False,
                },
                "report_verify_view": {
                    "source": "isaac_lab_camera_rgb_semantic_pose_robot_views:verify"
                },
                "camera_prim_path": "/World/robot_0/head_camera",
                "robot_pose": dict(robot_pose),
                "robot_asset": {
                    "status": "imported",
                    "head_camera_mounted": True,
                    "head_camera_equivalent": False,
                    "head_camera_prim_path": "/World/robot_0/head_camera",
                    "head_link_name": "link_head_2",
                    "import_summary": {
                        "import_method": "urdf_visual_static_usd_fallback",
                        "static_only": True,
                        "urdf": {"required_joints": ["base_x", "base_y", "head_1"]},
                        "converter": {
                            "fallback": {
                                "status": "ready",
                                "missing_mesh_count": 0,
                                "unsupported_mesh_count": 4,
                            }
                        },
                    },
                },
            },
        },
    }

    per_location = run_camera._location_camera_contract_diagnostics(location)
    summary = run_camera._camera_contract_diagnostics([location])

    assert per_location["fpv_head_camera_contract"] is True
    assert per_location["robot_pose_match"] is True
    assert per_location["isaac_robot_import"]["static_only"] is True
    assert per_location["head_articulation"]["status"] == ("isaac_static_head_pitch_not_applied")
    assert per_location["chase_contract"]["same_camera_contract"] is False
    assert summary["status"] == "fpv_contract_shared_with_static_head_articulation_gap"
    assert summary["fpv_head_camera_contract_count"] == 1
    assert summary["robot_pose_match_count"] == 1
    assert summary["isaac_static_head_pitch_gap_count"] == 1

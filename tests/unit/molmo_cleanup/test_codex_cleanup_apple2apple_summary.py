from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_SUMMARY_PATH = (
    REPO_ROOT / "scripts" / "molmo_cleanup" / "run_codex_cleanup_apple2apple_summary.py"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_codex_cleanup_apple2apple_summary_marks_current_state_not_strict(
    tmp_path: Path,
) -> None:
    run_summary = _load_module(RUN_SUMMARY_PATH, "run_codex_cleanup_apple2apple_summary")
    mujoco_dir = tmp_path / "mujoco" / "seed-6"
    isaac_dir = tmp_path / "isaac" / "seed-6"
    _write_run(
        mujoco_dir,
        backend="molmospaces_subprocess",
        scenario_id="molmospaces-procthor-val-0-6",
        completion_status="success",
        restored_count=3,
        total_targets=3,
        generated_mess_count=3,
        robot_contract_backend="molmospaces-mujoco",
        fpv_source="robot_0/head_camera",
        fpv_camera_prim_path=None,
    )
    _write_run(
        isaac_dir,
        backend="isaaclab_subprocess",
        scenario_id="isaac-scene-index-procthor-10k-val-1-6-2",
        completion_status="failed",
        restored_count=0,
        total_targets=2,
        generated_mess_count=2,
        robot_contract_backend="isaaclab_subprocess",
        fpv_source="isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
        fpv_camera_prim_path="/World/robot_0/head_camera",
        robot_asset={
            "head_camera_mounted": True,
            "head_camera_equivalent": False,
            "head_camera_prim_path": "/World/robot_0/head_camera",
            "import_summary": {
                "status": "ready",
                "import_method": "urdf_visual_static_usd_fallback",
                "converter": {
                    "fallback": {
                        "status": "ready",
                        "mesh_reference_count": 32,
                        "missing_mesh_count": 0,
                        "unsupported_mesh_count": 4,
                    }
                },
            },
        },
    )

    status = run_summary.main(
        [
            "--output-dir",
            str(tmp_path / "summary"),
            "--mujoco-run-result",
            str(mujoco_dir / "run_result.json"),
            "--isaac-run-result",
            str(isaac_dir / "run_result.json"),
        ]
    )

    assert status == 0
    manifest = json.loads((tmp_path / "summary" / "comparison_manifest.json").read_text())
    assert manifest["schema"] == run_summary.SCHEMA
    assert manifest["comparison"]["strict_scene_identical"] is False
    assert manifest["comparison"]["non_comparable_axes"] == [
        "generated_mess_count",
        "scene_index",
    ]
    assert manifest["comparison"]["axis_checks"]["cleanup_target_signature"]["matches"] is True
    assert manifest["comparison"]["axis_checks"]["head_camera_fpv"]["matches"] is True
    assert manifest["lanes"]["molmospaces-mujoco-codex"]["score"]["restored_text"] == "3/3"
    assert (
        manifest["lanes"]["isaaclab-rby1m-usd-codex"]["robot_import"]["head_camera_prim_path"]
        == "/World/robot_0/head_camera"
    )
    report = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "current_state_not_strict" in report
    assert "robot_0/head_camera" in report
    assert "isaac/seed-6/report.html" in report


def test_codex_cleanup_apple2apple_summary_flags_different_target_set(
    tmp_path: Path,
) -> None:
    run_summary = _load_module(RUN_SUMMARY_PATH, "run_codex_cleanup_apple2apple_summary")
    mujoco_dir = tmp_path / "mujoco" / "seed-6"
    isaac_dir = tmp_path / "isaac" / "seed-6"
    _write_run(
        mujoco_dir,
        backend="molmospaces_subprocess",
        scenario_id="molmospaces-procthor-val-0-6",
        completion_status="success",
        restored_count=1,
        total_targets=1,
        generated_mess_count=1,
        robot_contract_backend="molmospaces-mujoco",
        fpv_source="robot_0/head_camera",
        fpv_camera_prim_path=None,
        object_id="apple_001",
        object_category="Apple",
    )
    _write_run(
        isaac_dir,
        backend="isaaclab_subprocess",
        scenario_id="isaac-scene-index-procthor-10k-val-0-6-1",
        completion_status="success",
        restored_count=1,
        total_targets=1,
        generated_mess_count=1,
        robot_contract_backend="isaaclab_subprocess",
        fpv_source="isaac_lab_camera_rgb_robot_mounted_head_camera:fpv",
        fpv_camera_prim_path="/World/robot_0/head_camera",
        object_id="bread_001",
        object_category="Bread",
    )

    status = run_summary.main(
        [
            "--output-dir",
            str(tmp_path / "summary"),
            "--mujoco-run-result",
            str(mujoco_dir / "run_result.json"),
            "--isaac-run-result",
            str(isaac_dir / "run_result.json"),
        ]
    )

    assert status == 0
    manifest = json.loads((tmp_path / "summary" / "comparison_manifest.json").read_text())
    assert manifest["comparison"]["strict_scene_identical"] is False
    assert manifest["comparison"]["non_comparable_axes"] == ["cleanup_target_signature"]
    assert manifest["comparison"]["axis_checks"]["cleanup_target_signature"]["matches"] is False


def _write_run(
    run_dir: Path,
    *,
    backend: str,
    scenario_id: str,
    completion_status: str,
    restored_count: int,
    total_targets: int,
    generated_mess_count: int,
    robot_contract_backend: str,
    fpv_source: str,
    fpv_camera_prim_path: str | None,
    robot_asset: dict | None = None,
    object_id: str = "plate_001",
    object_category: str = "Plate",
) -> None:
    run_dir.mkdir(parents=True)
    for filename in (
        "report.html",
        "trace.jsonl",
        "agent_view.json",
        "private_evaluation.json",
        "codex-last-message.md",
        "before.png",
        "after.png",
        "robot_views/0000_before.fpv.png",
        "robot_views/0000_before.chase.png",
    ):
        path = run_dir / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("artifact", encoding="utf-8")
    agent_view = {
        "cleanup_worklist": {
            "held_object_id": None if completion_status == "success" else "observed_001",
            "objects": [
                {
                    "object_id": "observed_001",
                    "category": "Plate",
                    "state": "placed" if completion_status == "success" else "held",
                    "cleanup_recommended": completion_status != "success",
                    "candidate_fixture_id": "anchor_fixture_001",
                    "last_waypoint_id": "generated_exploration_001",
                }
            ],
        }
    }
    (run_dir / "agent_view.json").write_text(json.dumps(agent_view), encoding="utf-8")
    score = {
        "status": completion_status,
        "completion_status": completion_status,
        "restored_count": restored_count,
        "total_targets": total_targets,
        "mess_restoration_rate": restored_count / total_targets,
        "sweep_coverage_rate": 1.0,
        "disturbance_count": 0,
        "object_results": [
            {
                "object_id": object_id,
                "object_category": object_category,
                "restored": completion_status == "success",
                "actual_location_id": "sink_001" if completion_status == "success" else "held",
                "actual_receptacle_category": "Sink"
                if completion_status == "success"
                else "unknown",
                "semantic_acceptability": "preferred"
                if completion_status == "success"
                else "wrong",
                "semantic_reason": "fixture test",
                "exact_private_match": completion_status == "success",
            }
        ],
    }
    run_result = {
        "backend": backend,
        "policy": "codex_agent",
        "completion_status": completion_status,
        "scenario_id": scenario_id,
        "seed": 6,
        "map_mode": "minimal",
        "static_fixture_projection_mode": "room_only",
        "perception_mode": "visible_object_detections",
        "visual_grounding_pipeline_id": "sim",
        "requested_generated_mess_count": 3,
        "generated_mess_count": generated_mess_count,
        "score": score,
        "private_evaluation": {
            "requested_generated_mess_count": 3,
            "generated_mess_count": generated_mess_count,
        },
        "robot_view_camera_control": {
            "head_camera_fpv": True,
            "status": "all_robot_views_use_head_camera_fpv",
        },
        "robot_view_steps": [
            {
                "label": "0000_before",
                "action": "before",
                "views": {
                    "fpv": "robot_views/0000_before.fpv.png",
                    "chase": "robot_views/0000_before.chase.png",
                },
                "camera_control_contract": {
                    "backend": robot_contract_backend,
                    "status": "robot_mounted_head_camera_robot_view",
                    "camera_model": "robot_mounted_head_camera_v1",
                    "lens_source": "mujoco_model_camera_defaults",
                    "agent_facing_fpv": {
                        "source": fpv_source,
                        "camera_prim_path": fpv_camera_prim_path,
                        "robot_mounted": True,
                        "head_camera_equivalent": False,
                    },
                    "robot_asset": robot_asset or {},
                },
            }
        ],
        "terminate_reason": f"{backend} fixture terminate reason",
        "artifacts": {
            "report": "report.html",
            "trace": "trace.jsonl",
            "agent_view": "agent_view.json",
            "private_evaluation": "private_evaluation.json",
            "before_snapshot": "before.png",
            "after_snapshot": "after.png",
            "robot_views": "robot_views",
        },
    }
    (run_dir / "run_result.json").write_text(json.dumps(run_result), encoding="utf-8")

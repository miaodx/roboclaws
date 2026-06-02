from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "summarize_robot_camera_visual_parity.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_visual_parity_summary_keeps_rgb_gain_comparison_only_until_broad_gate(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity")
    val0 = _write_robot_camera_manifest(
        tmp_path / "val0" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=0,
        fpv=38.0,
        chase=84.0,
        location_count=8,
    )
    val1 = _write_robot_camera_manifest(
        tmp_path / "val1" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=36.5,
        chase=72.0,
        location_count=6,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "val1_rgb" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=34.5,
        chase=73.0,
        location_count=6,
    )
    (probe.parent / "isaac_state.json").write_text(
        json.dumps(
            {
                "robot_view_color_profile_override": {
                    "backend_rgb_gain": {"isaaclab_subprocess": [0.94, 0.84, 0.82]},
                    "backend_rgb_gain_source": (f"{val0} global least-squares FPV RGB gain"),
                }
            }
        ),
        encoding="utf-8",
    )
    raw_fpv = _write_raw_fpv_run_result(tmp_path / "raw" / "run_result.json")

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[val0, val1],
        probe_specs=[f"val1_rgb={probe}"],
        raw_fpv_run_result_paths=[raw_fpv],
        calibration_manifest_paths=[],
        required_scene_count=3,
        required_seed_count=2,
    )

    assert manifest["status"] == "active"
    assert manifest["checks"]["head_camera_contract"]["status"] == ("head_camera_geometry_aligned")
    assert manifest["checks"]["raw_fpv_input_lane"]["status"] == (
        "raw_fpv_agent_input_uses_head_camera"
    )
    assert manifest["checks"]["corpus_coverage"]["status"] == "needs_broader_corpus"
    assert manifest["checks"]["calibration_scene"]["status"] in {
        "default_calibration_artifact_missing",
        "calibration_scene_not_provided",
    }
    tone = manifest["checks"]["rgb_tone_cross_validation"]
    assert tone["status"] == "comparison_only_rgb_tone_positive"
    assert tone["comparison_only"] is True
    assert tone["held_out_improved_probe_count"] == 1
    assert tone["probes"][0]["fpv_delta"] == -2.0
    assert tone["probes"][0]["held_out_scene"] is True
    assert tone["probes"][0]["held_out_slice"] is True
    assert "additional bound-target" in manifest["recommended_next_action"]
    assert (tmp_path / "summary" / "visual_parity_summary.json").is_file()
    assert (tmp_path / "summary" / "report.html").is_file()


def test_visual_parity_summary_flags_camera_contract_gap(tmp_path: Path) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_gap")
    bad = _write_robot_camera_manifest(
        tmp_path / "bad" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=0,
        fpv=50.0,
        chase=80.0,
        location_count=4,
        camera_status="fpv_contract_shared_with_static_head_articulation_gap",
        lens_status="fpv_lens_contract_delta",
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[bad],
        probe_specs=[],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
    )

    assert manifest["status"] == "needs_camera_work"
    camera = manifest["checks"]["head_camera_contract"]
    assert camera["status"] == "not_proven"
    assert {item["reason"] for item in camera["failures"]} >= {
        "camera_contract_status",
        "fpv_lens_status",
    }


def test_visual_parity_summary_stays_active_when_render_domain_is_unresolved(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_foundational")
    baselines = [
        _write_robot_camera_manifest(
            tmp_path / f"val{index}_seed{seed}" / "comparison_manifest.json",
            scene_index=index,
            seed=seed,
            generated_mess_count=2,
            fpv=35.0 + index,
            chase=70.0 + index,
            location_count=4,
        )
        for index, seed in [(0, 6), (1, 6), (2, 8)]
    ]
    raw_fpv = _write_raw_fpv_run_result(tmp_path / "raw" / "run_result.json")
    calibration = tmp_path / "calibration" / "comparison_manifest.json"
    calibration.parent.mkdir(parents=True)
    calibration.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "status": "success",
                "summary": {
                    "render_domain_calibration": {
                        "status": "global_luminance_gain_sufficient",
                        "global_isaac_luminance_gain": 0.7,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=baselines,
        probe_specs=[],
        raw_fpv_run_result_paths=[raw_fpv],
        calibration_manifest_paths=[calibration],
        required_scene_count=3,
        required_seed_count=2,
    )

    assert manifest["status"] == "active"
    assert manifest["checks"]["corpus_coverage"]["status"] == "broad_corpus_ready"
    assert manifest["checks"]["calibration_scene"]["status"] == (
        "calibration_scene_evidence_loaded"
    )
    assert manifest["checks"]["render_domain_probe_matrix"]["status"] == (
        "render_domain_delta_active"
    )


def test_visual_parity_summary_pass_requires_resolved_render_domain_and_default_rgb(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_pass")
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {"status": "calibration_scene_evidence_loaded"},
        "render_domain_probe_matrix": {"status": "render_domain_delta_resolved"},
        "rgb_tone_cross_validation": {
            "status": "default_rgb_tone_ready",
            "comparison_only": False,
        },
    }

    assert summary._overall_status(checks) == "passed"


def _write_robot_camera_manifest(
    path: Path,
    *,
    scene_index: int,
    seed: int,
    generated_mess_count: int,
    fpv: float,
    chase: float,
    location_count: int,
    camera_status: str = "fpv_contract_shared_with_static_head_camera_pitch_correction",
    lens_status: str = "fpv_lens_aligned",
    pose_status: str = "fpv_world_pose_aligned",
) -> Path:
    path.parent.mkdir(parents=True)
    payload = {
        "schema": "roboclaws_robot_camera_apple2apple_comparison_v1",
        "status": "success",
        "scene": {
            "scene_source": "procthor-10k-val",
            "scene_index": scene_index,
            "seed": seed,
            "generated_mess_count": generated_mess_count,
            "render_width": 540,
            "render_height": 360,
            "scene_usd_path": f"scene_{scene_index}.usda",
        },
        "summary": {
            "location_count": location_count,
            "successful_location_count": location_count,
            "fpv_mean_abs_rgb_avg": fpv,
            "chase_mean_abs_rgb_avg": chase,
            "camera_contract_diagnostics": {
                "status": camera_status,
                "fpv_head_camera_contract_count": location_count,
                "fpv_lens_delta_summary": {"status": lens_status},
                "fpv_world_pose_delta_summary": {"status": pose_status},
            },
            "render_domain_checks": {
                "status": "render_domain_delta_confirmed",
                "checks": [
                    {"check_id": "light_shadow_contract", "status": "light_shadow_contract_delta"},
                    {"check_id": "tone_color_response", "status": "tone_color_response_unverified"},
                ],
            },
            "render_contract_diagnostics": {
                "status": "target_material_texture_or_binding_gap",
            },
            "target_selection": {
                "status": "isaac_bound_targets_selected",
                "selected_count": location_count,
                "dropped_unbound_target_count": 0,
            },
        },
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _write_raw_fpv_run_result(path: Path) -> Path:
    path.parent.mkdir(parents=True)
    path.write_text(
        json.dumps(
            {
                "backend": "isaaclab_subprocess",
                "cleanup_profile": "camera-raw",
                "perception_mode": "raw_fpv_only",
                "raw_fpv_observations": [{"observation_id": "raw_fpv_001"}],
                "model_declared_observations": [{"source_observation_id": "raw_fpv_001"}],
                "robot_view_camera_control": {
                    "status": "all_robot_views_use_head_camera_fpv",
                    "head_camera_fpv": True,
                    "head_camera_contract_count": 2,
                    "step_count": 2,
                },
            }
        ),
        encoding="utf-8",
    )
    return path

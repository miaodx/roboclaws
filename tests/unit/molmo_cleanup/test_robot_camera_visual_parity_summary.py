from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "summarize_robot_camera_visual_parity.py"
TINY_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
    b"\x00\x01\x01\x01\x00\xc9\xfe\x92\xef\x00\x00\x00\x00IEND\xaeB`\x82"
)


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
    four_check = manifest["four_check_audit"]
    assert four_check["status"] == "active"
    assert four_check["root_cause_classification"] == "render_domain_not_camera"
    assert four_check["unresolved_check_ids"] == [
        "material_texture_response",
        "light_brightness_tone",
    ]
    four_check_rows = {row["check_id"]: row for row in four_check["rows"]}
    assert four_check_rows["camera_geometry"]["resolved"] is True
    assert four_check_rows["raw_fpv_input_lane"]["resolved"] is True
    assert four_check_rows["material_texture_response"]["resolved"] is False
    assert four_check_rows["light_brightness_tone"]["resolved"] is False
    assert manifest["checks"]["corpus_coverage"]["status"] == "needs_broader_corpus"
    report_side = manifest["report_side_visual_parity"]
    assert report_side["status"] == "not_ready"
    assert report_side["ready"] is False
    assert {blocker["check_id"] for blocker in report_side["blockers"]} >= {
        "corpus_coverage",
        "calibration_scene",
        "view_specific_prepared_scale_square_tone_gate",
    }
    default_rendering = manifest["default_rendering_visual_parity"]
    assert default_rendering["status"] == "not_ready"
    assert default_rendering["ready"] is False
    assert default_rendering["policy_scope"] == "default_rendering"
    assert {blocker.get("check_id") for blocker in default_rendering["blockers"]} >= {
        "corpus_coverage",
        "calibration_scene",
        "render_domain_probe_matrix",
        "prepared_scale_square_default_gate",
        "rgb_tone_cross_validation",
    }
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


def test_visual_parity_summary_classifies_material_probe_from_path_when_label_is_generic(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_material_path")
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline" / "comparison_manifest.json",
        scene_index=1,
        seed=8,
        generated_mess_count=2,
        fpv=37.2,
        chase=71.7,
        location_count=4,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "material_srgb_probe" / "comparison_manifest.json",
        scene_index=1,
        seed=8,
        generated_mess_count=2,
        fpv=37.4,
        chase=71.7,
        location_count=4,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"val1_seed8={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
    )

    rows = manifest["checks"]["render_domain_probe_matrix"]["probe_matrix"]["material_response"]
    assert rows[0]["label"] == "val1_seed8"
    assert rows[0]["fpv_delta"] == 0.2


def test_visual_parity_summary_does_not_classify_lightwood_material_as_light_shadow(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_lightwood")
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=38.0,
        chase=83.7,
        location_count=8,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "0008_lightwood_scale_square_probe" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=35.8,
        chase=83.7,
        location_count=8,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"val0_0008_lightwood_scale_square={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
    )

    matrix = manifest["checks"]["render_domain_probe_matrix"]["probe_matrix"]
    assert matrix["material_response"][0]["label"] == "val0_0008_lightwood_scale_square"
    assert matrix["material_response"][0]["fpv_improved"] is True
    assert "light_shadow" not in matrix


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


def test_visual_parity_summary_prefers_scene_level_calibration_over_candidate_profiles(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_scene_calibration")
    calibration = tmp_path / "calibration" / "comparison_manifest.json"
    calibration.parent.mkdir(parents=True)
    calibration.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "status": "success",
                "visual_diagnostics": {
                    "candidate_color_calibrations": {
                        "candidates": [
                            {
                                "render_domain_calibration": {
                                    "status": "view_dependent_render_domain_delta",
                                    "global_isaac_luminance_gain": 1.5,
                                    "mean_abs_calibrated_luminance_residual": 15.0,
                                }
                            }
                        ]
                    },
                    "render_domain_calibration": {
                        "status": "view_dependent_render_domain_delta",
                        "global_isaac_luminance_gain": 1.1,
                        "mean_abs_calibrated_luminance_residual": 12.0,
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[],
        probe_specs=[],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[calibration],
    )

    loaded = manifest["checks"]["calibration_scene"]["manifests"][0]
    assert loaded["render_domain_calibration_source"] == (
        "visual_diagnostics.render_domain_calibration"
    )
    assert loaded["global_isaac_luminance_gain"] == 1.1
    assert loaded["mean_abs_calibrated_luminance_residual"] == 12.0
    assert manifest["checks"]["calibration_scene"]["default_rendering_ready"] is False


def test_visual_parity_summary_uses_ready_calibration_candidate_despite_failed_history(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_ready_candidate")
    failed = tmp_path / "failed" / "comparison_manifest.json"
    ready = tmp_path / "ready" / "comparison_manifest.json"
    failed.parent.mkdir(parents=True)
    ready.parent.mkdir(parents=True)
    failed.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "visual_diagnostics": {
                    "render_domain_calibration": {
                        "status": "view_dependent_render_domain_delta",
                        "mean_abs_calibrated_luminance_residual": 12.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    ready.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "visual_diagnostics": {
                    "render_domain_calibration": {
                        "status": "global_luminance_gain_sufficient",
                        "mean_abs_calibrated_luminance_residual": 7.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[],
        probe_specs=[],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[failed, ready],
    )

    calibration = manifest["checks"]["calibration_scene"]
    assert calibration["default_rendering_ready"] is True
    assert calibration["default_rendering_blockers"] == []
    assert len(calibration["default_rendering_candidates"]) == 1
    assert len(calibration["non_default_rendering_candidates"]) == 1


def test_visual_parity_summary_tracks_combined_material_light_candidate(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_combined_light")
    baseline = _write_robot_camera_manifest(
        tmp_path / "val0_baseline" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=38.0,
        chase=84.0,
        location_count=8,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "val0_scale_square_rotx25" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=30.0,
        chase=82.0,
        location_count=8,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"val0_scale_square_rotx25={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=3,
        required_seed_count=2,
    )

    gate = manifest["checks"]["combined_material_light_default_gate"]
    assert gate["status"] == "needs_broader_corpus"
    assert gate["fpv_improved_count"] == 1
    assert gate["chase_regression_count"] == 0
    assert gate["probes"][0]["fpv_delta"] == -8.0
    assert gate["probes"][0]["chase_delta"] == -2.0
    assert {blocker["reason"] for blocker in gate["blockers"]} >= {
        "needs_broader_scene_corpus",
        "needs_broader_seed_corpus",
    }
    assert manifest["visual_samples"]
    assert manifest["visual_samples"][0]["images"]["fpv"]["mujoco"].endswith(
        "val0_baseline/mujoco/robot_views/0001_target.fpv.png"
    )
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "<h2>Visual Samples</h2>" in report_html
    assert "<img src='../val0_baseline/mujoco/robot_views/0001_target.fpv.png'" in report_html
    assert "<img src='../val0_scale_square_rotx25/isaac/robot_views/0001_target.fpv.png'" in (
        report_html
    )
    assert "non-comparable auxiliary" not in report_html
    assert "robot_0/camera_follower / robot_relative_camera_follower" in report_html
    assert "Object Parity" in report_html
    default_rendering = manifest["default_rendering_visual_parity"]
    assert any(
        blocker.get("reason") == "material_light_default_gate_not_ready"
        for blocker in default_rendering["blockers"]
    )


def test_visual_parity_summary_surfaces_object_parity_audit(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_object_audit")
    baseline = _write_robot_camera_manifest(
        tmp_path / "val1_baseline" / "comparison_manifest.json",
        scene_index=1,
        seed=8,
        generated_mess_count=2,
        fpv=26.5,
        chase=51.4,
        location_count=4,
        object_parity_audit={
            "status": "object_parity_gaps_detected",
            "item_count": 29,
            "high_priority_gap_count": 6,
        },
        object_render_parity_diagnostics={
            "status": "object_gate_failures_detected",
            "object_gate_status": "object_gate_failures_detected",
            "object_gate_failure_count": 6,
            "object_gate_comparable_count": 23,
            "render_gate_status": "render_domain_residual",
        },
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    baseline_summary = manifest["baselines"][0]
    assert baseline_summary["object_parity_status"] == "object_parity_gaps_detected"
    assert baseline_summary["object_parity_high_priority_gap_count"] == 6
    assert baseline_summary["object_render_gate_status"] == "object_gate_failures_detected"
    assert baseline_summary["object_gate_failure_count"] == 6
    assert baseline_summary["render_gate_status"] == "render_domain_residual"
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "object_parity_gaps_detected" in report_html
    assert "<th>Object Gaps</th>" in report_html
    assert "<th>Object/Render Gate</th>" in report_html
    assert "object_gate_failures_detected" in report_html


def test_visual_parity_summary_keeps_prepared_scale_square_comparison_only_on_chase_regression(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_prepared_gate")
    baselines = [
        _write_robot_camera_manifest(
            tmp_path / "baseline_0_seed_6" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=38.0,
            chase=83.0,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_6" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=36.0,
            chase=72.0,
            location_count=4,
            locations=[
                _image_diff_location(
                    "0001_bed",
                    target_id="bed_1",
                    fpv_mean=50.0,
                    fpv_edge=4.0,
                    fpv_mujoco_luma=90.0,
                    fpv_isaac_luma=105.0,
                    chase_mean=60.0,
                    chase_edge=8.0,
                    chase_mujoco_luma=150.0,
                    chase_isaac_luma=130.0,
                ),
                _image_diff_location(
                    "0002_pillow",
                    target_id="pillow_1",
                    fpv_mean=40.0,
                    fpv_edge=4.5,
                    fpv_mujoco_luma=110.0,
                    fpv_isaac_luma=125.0,
                    chase_mean=65.0,
                    chase_edge=8.5,
                    chase_mujoco_luma=145.0,
                    chase_isaac_luma=130.0,
                ),
            ],
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_8" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=37.0,
            chase=71.0,
            location_count=4,
        ),
    ]
    probes = [
        _write_robot_camera_manifest(
            tmp_path / "val0_prepared_scale_square_gate" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=32.0,
            chase=83.1,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_seed6_prepared_scale_square_gate" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=29.0,
            chase=75.0,
            location_count=4,
            locations=[
                _image_diff_location(
                    "0001_bed",
                    target_id="bed_1",
                    fpv_mean=45.0,
                    fpv_edge=4.0,
                    fpv_mujoco_luma=90.0,
                    fpv_isaac_luma=80.0,
                    chase_mean=70.0,
                    chase_edge=8.0,
                    chase_mujoco_luma=150.0,
                    chase_isaac_luma=90.0,
                ),
                _image_diff_location(
                    "0002_pillow",
                    target_id="pillow_1",
                    fpv_mean=35.0,
                    fpv_edge=4.5,
                    fpv_mujoco_luma=110.0,
                    fpv_isaac_luma=105.0,
                    chase_mean=80.0,
                    chase_edge=8.5,
                    chase_mujoco_luma=145.0,
                    chase_isaac_luma=90.0,
                ),
            ],
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_seed8_prepared_scale_square_gate" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=29.0,
            chase=70.8,
            location_count=4,
        ),
    ]
    calibration = tmp_path / "calibration" / "comparison_manifest.json"
    calibration.parent.mkdir(parents=True)
    calibration.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "status": "success",
                "summary": {
                    "render_domain_calibration": {
                        "status": "view_dependent_render_domain_delta",
                        "mean_abs_calibrated_luminance_residual": 14.0,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    raw_fpv = _write_raw_fpv_run_result(tmp_path / "raw" / "run_result.json")

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=baselines,
        probe_specs=[f"{path.parent.name}={path}" for path in probes],
        raw_fpv_run_result_paths=[raw_fpv],
        calibration_manifest_paths=[calibration],
        required_scene_count=3,
        required_seed_count=2,
    )

    gate = manifest["checks"]["prepared_scale_square_default_gate"]
    assert gate["status"] == "comparison_only_not_default"
    assert gate["comparison_only"] is True
    assert gate["default_candidate"] is False
    assert gate["prepared_probe_count"] == 3
    assert gate["fpv_improved_count"] == 3
    assert gate["chase_regression_count"] == 1
    assert {blocker["reason"] for blocker in gate["blockers"]} >= {
        "chase_regression",
        "render_domain_residuals_active",
    }
    chase_diagnostics = gate["chase_regression_diagnostics"]
    assert chase_diagnostics[0]["diagnostic_class"] == "tone_luminance_side_effect"
    assert chase_diagnostics[0]["chase"]["edge_regression_count"] == 0
    assert chase_diagnostics[0]["chase"]["luminance_gap_regression_count"] == 2
    assert "comparison-only" in manifest["recommended_next_action"]


def test_visual_parity_summary_marks_view_specific_tone_ready_for_review(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_view_tone")
    baselines = [
        _write_robot_camera_manifest(
            tmp_path / "baseline_0_seed_6" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=38.0,
            chase=83.0,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_6" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=36.0,
            chase=72.0,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_8" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=37.0,
            chase=71.0,
            location_count=4,
        ),
    ]
    probes = [
        _write_robot_camera_manifest(
            tmp_path / "val0_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=32.0,
            chase=83.7,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=30.0,
            chase=71.5,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_seed8_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=30.5,
            chase=71.4,
            location_count=4,
        ),
    ]
    for path in probes:
        (path.parent / "isaac_state.json").write_text(
            json.dumps(
                {
                    "robot_view_color_profile_override": {
                        "backend_rgb_gain": {"isaaclab_subprocess": [0.94, 0.84, 0.82]},
                        "backend_rgb_gain_source": (
                            "output/molmo/robot-camera-apple2apple/seed6_prepared "
                            "global least-squares FPV RGB gain"
                        ),
                        "backend_view_rgb_gain": {
                            "isaaclab_subprocess": {
                                "fpv": [0.94, 0.84, 0.82],
                                "chase": [1.5, 1.4, 1.3],
                            }
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
    calibration = tmp_path / "calibration" / "comparison_manifest.json"
    calibration.parent.mkdir(parents=True)
    calibration.write_text(
        json.dumps(
            {
                "schema": "scene_camera_comparison_v1",
                "status": "success",
                "summary": {
                    "render_domain_calibration": {
                        "status": "view_dependent_render_domain_delta",
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    raw_fpv = _write_raw_fpv_run_result(tmp_path / "raw" / "run_result.json")

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=baselines,
        probe_specs=[f"{path.parent.name}={path}" for path in probes],
        raw_fpv_run_result_paths=[raw_fpv],
        calibration_manifest_paths=[calibration],
        required_scene_count=3,
        required_seed_count=2,
    )

    gate = manifest["checks"]["view_specific_prepared_scale_square_tone_gate"]
    assert gate["status"] == "view_specific_report_comparison_gate_ready"
    assert gate["formal_comparison_gate_ready"] is True
    assert gate["ready_for_review"] is True
    assert gate["comparison_only"] is True
    assert gate["policy_scope"] == "report_side_comparison_only"
    assert gate["default_rendering_candidate"] is False
    assert gate["probe_count"] == 3
    assert gate["fpv_improved_count"] == 3
    assert gate["chase_regression_count"] == 0
    assert gate["view_rgb_gain_profile_count"] == 3
    assert gate["required_view_rgb_gain_views"] == ["fpv", "chase"]
    assert gate["blockers"] == []
    assert all(row["has_required_view_rgb_gain"] for row in gate["probes"])
    four_check_rows = {row["check_id"]: row for row in manifest["four_check_audit"]["rows"]}
    assert four_check_rows["material_texture_response"]["status"] == (
        "review_ready_comparison_only"
    )
    assert four_check_rows["light_brightness_tone"]["status"] == ("review_ready_comparison_only")
    assert four_check_rows["light_brightness_tone"]["policy_scope"] == (
        "report_side_comparison_only"
    )
    assert (
        "formal report-side comparison gate" in four_check_rows["light_brightness_tone"]["decision"]
    )
    report_side = manifest["report_side_visual_parity"]
    assert report_side["status"] == "report_side_visual_parity_ready"
    assert report_side["ready"] is True
    assert report_side["policy_scope"] == "report_side_comparison_only"
    assert report_side["default_rendering_candidate"] is False
    assert report_side["blockers"] == []
    default_rendering = manifest["default_rendering_visual_parity"]
    assert default_rendering["status"] == "not_ready"
    assert default_rendering["ready"] is False
    assert {blocker.get("check_id") for blocker in default_rendering["blockers"]} >= {
        "calibration_scene",
        "render_domain_probe_matrix",
        "prepared_scale_square_default_gate",
        "rgb_tone_cross_validation",
    }
    assert any(
        blocker.get("reason") == "render_domain_calibration_not_default_ready"
        for blocker in default_rendering["blockers"]
    )
    assert "default" in manifest["recommended_next_action"]


def test_visual_parity_summary_requires_actual_view_specific_rgb_profile(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_view_tone_missing")
    baselines = [
        _write_robot_camera_manifest(
            tmp_path / "baseline_0_seed_6" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=38.0,
            chase=83.0,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_6" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=36.0,
            chase=72.0,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "baseline_1_seed_8" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=37.0,
            chase=71.0,
            location_count=4,
        ),
    ]
    probes = [
        _write_robot_camera_manifest(
            tmp_path / "val0_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=0,
            seed=6,
            generated_mess_count=2,
            fpv=32.0,
            chase=83.7,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=1,
            seed=6,
            generated_mess_count=2,
            fpv=30.0,
            chase=71.5,
            location_count=4,
        ),
        _write_robot_camera_manifest(
            tmp_path / "val1_seed8_prepared_scale_square_view_rgb" / "comparison_manifest.json",
            scene_index=1,
            seed=8,
            generated_mess_count=2,
            fpv=30.5,
            chase=71.4,
            location_count=4,
        ),
    ]
    for path in probes:
        (path.parent / "isaac_state.json").write_text(
            json.dumps(
                {
                    "robot_view_color_profile_override": {
                        "backend_rgb_gain": {"isaaclab_subprocess": [0.94, 0.84, 0.82]},
                        "backend_rgb_gain_source": (
                            "output/molmo/robot-camera-apple2apple/seed6_prepared "
                            "global least-squares FPV RGB gain"
                        ),
                    }
                }
            ),
            encoding="utf-8",
        )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=baselines,
        probe_specs=[f"{path.parent.name}={path}" for path in probes],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=3,
        required_seed_count=2,
    )

    gate = manifest["checks"]["view_specific_prepared_scale_square_tone_gate"]
    assert gate["status"] == "comparison_only_needs_broader_gate"
    assert gate["formal_comparison_gate_ready"] is False
    assert gate["ready_for_review"] is False
    assert gate["policy_scope"] == "comparison_only_probe"
    assert gate["default_rendering_candidate"] is False
    assert gate["view_rgb_gain_profile_count"] == 0
    assert {blocker["reason"] for blocker in gate["blockers"]} == {"missing_backend_view_rgb_gain"}
    assert all(not row["has_required_view_rgb_gain"] for row in gate["probes"])
    report_side = manifest["report_side_visual_parity"]
    assert report_side["status"] == "not_ready"
    assert any(
        blocker["check_id"] == "view_specific_prepared_scale_square_tone_gate"
        for blocker in report_side["blockers"]
    )


def test_visual_parity_summary_pass_requires_resolved_render_domain_and_default_rgb(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_pass")
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {
            "status": "calibration_scene_evidence_loaded",
            "default_rendering_ready": True,
        },
        "render_domain_probe_matrix": {"status": "render_domain_delta_resolved"},
        "prepared_scale_square_default_gate": {"status": "prepared_scale_square_default_ready"},
        "view_specific_prepared_scale_square_tone_gate": {
            "status": "view_specific_report_comparison_gate_ready",
            "formal_comparison_gate_ready": True,
        },
        "rgb_tone_cross_validation": {
            "status": "default_rgb_tone_ready",
            "comparison_only": False,
        },
    }

    assert summary._overall_status(checks) == "passed"
    default_rendering = summary._default_rendering_visual_parity(checks)
    assert default_rendering["status"] == "default_rendering_visual_parity_ready"
    assert default_rendering["ready"] is True
    assert default_rendering["blockers"] == []
    audit = summary._four_check_audit(checks)
    assert audit["status"] == "passed"
    assert audit["unresolved_check_ids"] == []
    assert audit["root_cause_classification"] == (
        "render_domain_resolved_by_default_rendering_gates"
    )


def test_visual_parity_summary_marks_combined_material_light_promotion_candidate(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_combined_pass")
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {
            "status": "calibration_scene_evidence_loaded",
            "default_rendering_ready": True,
        },
        "render_domain_probe_matrix": {"status": "render_domain_delta_active"},
        "prepared_scale_square_default_gate": {"status": "comparison_only_not_default"},
        "combined_material_light_default_gate": {"status": "combined_material_light_default_ready"},
        "view_specific_prepared_scale_square_tone_gate": {
            "status": "view_specific_report_comparison_gate_ready",
            "formal_comparison_gate_ready": True,
        },
        "rgb_tone_cross_validation": {
            "status": "comparison_only_rgb_tone_positive",
            "comparison_only": True,
        },
    }

    assert summary._overall_status(checks) == "active"
    default_rendering = summary._default_rendering_visual_parity(checks)
    assert default_rendering["status"] == "default_rendering_promotion_candidate_ready"
    assert default_rendering["ready"] is False
    assert default_rendering["promotion_candidate_ready"] is True
    assert default_rendering["promotion_path"] == "combined_material_light_default_gate"
    assert default_rendering["blockers"] == [
        {
            "actual": "not_proven",
            "check_id": "default_rendering_path",
            "expected": "default_rendering_path_uses_combined_material_light",
            "reason": "default_rendering_path_not_promoted",
        }
    ]
    audit = summary._four_check_audit(checks)
    assert audit["status"] == "passed"
    assert audit["unresolved_check_ids"] == []
    assert audit["root_cause_classification"] == (
        "render_domain_ready_for_combined_material_light_default_path"
    )
    rows = {row["check_id"]: row for row in audit["rows"]}
    assert "ready for default-rendering review" in rows["material_texture_response"]["decision"]
    assert "ready for default-rendering review" in rows["light_brightness_tone"]["decision"]


def test_visual_parity_summary_passes_after_combined_material_light_path_is_promoted(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_combined_promoted")
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {
            "status": "calibration_scene_evidence_loaded",
            "default_rendering_ready": True,
        },
        "render_domain_probe_matrix": {"status": "render_domain_delta_active"},
        "prepared_scale_square_default_gate": {"status": "comparison_only_not_default"},
        "combined_material_light_default_gate": {"status": "combined_material_light_default_ready"},
        "default_rendering_path": {"status": "default_rendering_path_uses_combined_material_light"},
        "view_specific_prepared_scale_square_tone_gate": {
            "status": "view_specific_report_comparison_gate_ready",
            "formal_comparison_gate_ready": True,
        },
        "rgb_tone_cross_validation": {
            "status": "comparison_only_rgb_tone_positive",
            "comparison_only": True,
        },
    }

    assert summary._overall_status(checks) == "passed"
    default_rendering = summary._default_rendering_visual_parity(checks)
    assert default_rendering["status"] == "default_rendering_visual_parity_ready"
    assert default_rendering["ready"] is True
    assert default_rendering["promotion_candidate_ready"] is True
    assert default_rendering["blockers"] == []
    audit = summary._four_check_audit(checks)
    assert audit["status"] == "passed"
    assert audit["unresolved_check_ids"] == []
    assert audit["root_cause_classification"] == (
        "render_domain_resolved_by_combined_material_light_default_path"
    )
    rows = {row["check_id"]: row for row in audit["rows"]}
    assert "default prepared-USD path" in rows["material_texture_response"]["decision"]
    assert "default prepared-USD path" in rows["light_brightness_tone"]["decision"]


def test_visual_parity_summary_combined_gate_still_requires_default_calibration(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_combined_calib")
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {
            "status": "calibration_scene_evidence_loaded",
            "default_rendering_ready": False,
        },
        "render_domain_probe_matrix": {"status": "render_domain_delta_active"},
        "prepared_scale_square_default_gate": {"status": "comparison_only_not_default"},
        "combined_material_light_default_gate": {"status": "combined_material_light_default_ready"},
        "view_specific_prepared_scale_square_tone_gate": {
            "status": "view_specific_report_comparison_gate_ready",
            "formal_comparison_gate_ready": True,
        },
        "rgb_tone_cross_validation": {
            "status": "comparison_only_rgb_tone_positive",
            "comparison_only": True,
        },
    }

    assert summary._overall_status(checks) == "active"
    default_rendering = summary._default_rendering_visual_parity(checks)
    assert default_rendering["status"] == "not_ready"
    assert any(
        blocker.get("reason") == "calibration_not_default_rendering_ready"
        for blocker in default_rendering["blockers"]
    )


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
    locations: list[dict] | None = None,
    object_parity_audit: dict | None = None,
    object_render_parity_diagnostics: dict | None = None,
) -> Path:
    path.parent.mkdir(parents=True)
    default_locations = [_visual_location(path.parent)] if locations is None else locations
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
            "object_parity_audit": object_parity_audit or {},
            "object_render_parity_diagnostics": object_render_parity_diagnostics or {},
        },
        "locations": default_locations,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _visual_location(output_dir: Path) -> dict:
    label = "0001_target"
    views = {"mujoco": {}, "isaac": {}}
    for backend in ("mujoco", "isaac"):
        for view in ("fpv", "chase"):
            rel = Path(backend) / "robot_views" / f"{label}.{view}.png"
            image_path = output_dir / rel
            image_path.parent.mkdir(parents=True, exist_ok=True)
            image_path.write_bytes(TINY_PNG)
            views[backend][view] = rel.as_posix()
    return {
        "label": label,
        "target": {"target_id": "target"},
        "status": "success",
        "views": views,
        "image_diffs": {
            "fpv": _image_diff(42.0, 3.0, 85.0, 95.0),
            "chase": _image_diff(70.0, 7.0, 95.0, 105.0),
        },
        "camera_contract_diagnostics": {
            "chase_contract": {
                "same_camera_contract": True,
                "mujoco_source": "robot_0/camera_follower",
                "isaac_source": "robot_relative_camera_follower",
                "evidence_note": (
                    "Chase now uses a robot-relative rear/high report camera in both backends."
                ),
            }
        },
    }


def _image_diff_location(
    label: str,
    *,
    target_id: str,
    fpv_mean: float,
    fpv_edge: float,
    fpv_mujoco_luma: float,
    fpv_isaac_luma: float,
    chase_mean: float,
    chase_edge: float,
    chase_mujoco_luma: float,
    chase_isaac_luma: float,
) -> dict:
    return {
        "label": label,
        "target": {"target_id": target_id},
        "image_diffs": {
            "fpv": _image_diff(fpv_mean, fpv_edge, fpv_mujoco_luma, fpv_isaac_luma),
            "chase": _image_diff(chase_mean, chase_edge, chase_mujoco_luma, chase_isaac_luma),
        },
    }


def _image_diff(
    mean_abs_rgb: float,
    edge_abs_diff: float,
    mujoco_luminance: float,
    isaac_luminance: float,
) -> dict:
    return {
        "mean_abs_rgb": mean_abs_rgb,
        "residual": {
            "edge_abs_diff": edge_abs_diff,
            "left_metrics": {"mean_luminance": mujoco_luminance},
            "right_metrics": {"mean_luminance": isaac_luminance},
        },
    }


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

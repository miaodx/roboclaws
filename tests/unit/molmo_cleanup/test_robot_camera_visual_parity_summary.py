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
    assert 'class="lightbox"' in report_html
    assert "data-lightbox" in report_html
    assert 'aria-hidden="true"' in report_html
    assert 'document.querySelectorAll("img:not([data-lightbox-image])")' in report_html
    assert 'title", "Open image preview"' in report_html
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
        object_visual_parity_audit={
            "schema": "robot_camera_object_parity_audit_v1",
            "status": "object_parity_gaps_detected",
            "item_count": 29,
            "object_count": 20,
            "receptacle_count": 9,
            "high_priority_gap_count": 6,
            "category_status_summary": [
                {
                    "category": "box",
                    "item_count": 2,
                    "category_status_counts": {
                        "category_delta": 1,
                        "matched_category": 1,
                    },
                    "object_gate_status_counts": {
                        "object_gate_failed": 1,
                        "object_gate_passed": 1,
                    },
                    "rgb_view_evidence_status_counts": {
                        "nonblank_in_both_backends": 2,
                    },
                    "render_contract_status_counts": {
                        "material_texture_delta": 1,
                        "render_contract_aligned": 1,
                    },
                }
            ],
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
    audit = baseline_summary["object_visual_parity_audit"]
    assert audit["schema"] == "robot_camera_object_parity_audit_v1"
    assert audit["category_status_summary"][0]["category_status_counts"] == {
        "category_delta": 1,
        "matched_category": 1,
    }
    assert audit["category_status_summary"][0]["rgb_view_evidence_status_counts"] == {
        "nonblank_in_both_backends": 2,
    }
    assert baseline_summary["object_render_gate_status"] == "object_gate_failures_detected"
    assert baseline_summary["object_gate_failure_count"] == 6
    assert baseline_summary["render_gate_status"] == "render_domain_residual"
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "object_parity_gaps_detected" in report_html
    assert "<th>Object Gaps</th>" in report_html
    assert "<th>Object/Render Gate</th>" in report_html
    assert "<h2>Object Visual Parity Audit</h2>" in report_html
    assert "<th>Category Status</th>" in report_html
    assert "<th>RGB Evidence</th>" in report_html
    assert "object_gate_failures_detected" in report_html
    assert "category_delta" in report_html
    assert "nonblank_in_both_backends" in report_html


def test_visual_parity_summary_derives_category_rows_from_legacy_object_items(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_legacy_items")
    full_audit = {
        "schema": "robot_camera_object_parity_audit_v1",
        "status": "object_parity_gaps_detected",
        "item_count": 2,
        "high_priority_gap_count": 1,
        "items": [
            {
                "kind": "object",
                "binding_status": "bound",
                "category_status": "matched_category",
                "pose_status": "pose_aligned",
                "support_status": "support_aligned",
                "state_status": "visual_state_static_ref_baked",
                "mujoco": {"category": "Box"},
                "isaac": {"category": "Box"},
                "rgb_view_evidence": {"status": "selected_views_nonblank"},
                "render_contract_delta": {"status": "render_contract_aligned"},
            },
            {
                "kind": "object",
                "binding_status": "missing_isaac_binding",
                "category_status": "missing_binding",
                "pose_status": "not_comparable",
                "support_status": "not_comparable",
                "state_status": "not_applicable",
                "mujoco": {"category": "GarbageCan"},
                "isaac": {},
                "render_contract_delta": {"status": "not_comparable"},
            },
        ],
    }
    baseline = _write_robot_camera_manifest(
        tmp_path / "val1_baseline" / "comparison_manifest.json",
        scene_index=1,
        seed=8,
        generated_mess_count=2,
        fpv=26.5,
        chase=51.4,
        location_count=4,
        object_visual_parity_audit={
            "schema": "robot_camera_object_parity_audit_v1",
            "status": "object_parity_gaps_detected",
            "item_count": 2,
            "high_priority_gap_count": 1,
        },
        top_level_object_visual_parity_audit=full_audit,
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

    category_rows = {
        item["category"]: item
        for item in manifest["baselines"][0]["object_visual_parity_audit"][
            "category_status_summary"
        ]
    }
    assert category_rows["box"]["state_status_counts"] == {"visual_state_static_ref_baked": 1}
    assert category_rows["box"]["rgb_view_evidence_status_counts"] == {"selected_views_nonblank": 1}
    assert category_rows["garbagecan"]["binding_status_counts"] == {"missing_isaac_binding": 1}
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "selected_views_nonblank" in report_html
    assert "missing_isaac_binding" in report_html


def test_visual_parity_summary_carries_native_isaac_render_diagnostics(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_native_render")
    native = {
        "schema": "robot_camera_native_isaac_render_diagnostics_v1",
        "status": "native_settings_recorded",
        "renderer_mode": "isaac_lab_headless_rtx",
        "capture_method": "isaac_lab_camera_rgb_static_robot_views",
        "settings_api_available": True,
        "available_setting_count": 4,
        "missing_setting_count": 2,
        "camera_prim_paths": ["/World/robot_0/head_camera"],
        "render_product_paths": ["/Render/Product/Fpv"],
        "isaac_lab_isp_active": False,
        "default_render_settings_changed": False,
        "post_render_comparison_profile": {
            "applied": False,
            "source": "not_a_native_renderer_setting",
        },
    }
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline" / "comparison_manifest.json",
        scene_index=1,
        seed=8,
        generated_mess_count=2,
        fpv=37.2,
        chase=71.7,
        location_count=4,
        native_isaac_render_diagnostics=native,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
    )

    baseline_summary = manifest["baselines"][0]
    assert baseline_summary["native_isaac_render_status"] == "native_settings_recorded"
    assert baseline_summary["native_isaac_settings_api_available"] is True
    assert baseline_summary["native_isaac_default_render_settings_changed"] is False
    assert baseline_summary["native_isaac_render_diagnostics"]["camera_prim_paths"] == [
        "/World/robot_0/head_camera"
    ]
    assert (
        baseline_summary["native_isaac_render_diagnostics"]["post_render_comparison_profile"][
            "source"
        ]
        == "not_a_native_renderer_setting"
    )
    assert manifest["default_rendering_visual_parity"]["ready"] is False


def test_visual_parity_summary_ranks_render_difference_probe_batch(
    tmp_path: Path,
) -> None:
    summary = _load_module(SCRIPT_PATH, "summarize_robot_camera_visual_parity_render_probe_batch")
    native = {
        "schema": "robot_camera_native_isaac_render_diagnostics_v1",
        "status": "native_settings_recorded",
        "renderer_mode": "isaac_lab_headless_rtx",
        "settings_api_available": True,
        "default_render_settings_changed": True,
        "tone_mapping": {"op": {"status": "recorded", "value": 2}},
        "camera_exposure": {"filmIso": {"status": "recorded", "value": 100}},
        "renderer": {"samples_per_pixel": {"status": "recorded", "value": 64}},
        "post_render_comparison_profile": {
            "applied": False,
            "source": "not_a_native_renderer_setting",
        },
    }
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=40.0,
        chase=80.0,
        location_count=2,
        native_isaac_render_diagnostics={**native, "default_render_settings_changed": False},
        locations=[
            _residual_location(
                "0001_low",
                fpv_mean=38.0,
                chase_mean=75.0,
                fpv_class="low_residual",
                chase_class="geometry_or_texture_edge_residual",
            ),
            _residual_location(
                "0002_edge",
                fpv_mean=42.0,
                chase_mean=85.0,
                fpv_class="geometry_or_texture_edge_residual",
                chase_class="low_residual",
            ),
        ],
    )
    native_probe = _write_robot_camera_manifest(
        tmp_path / "native_tone_exposure" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=33.0,
        chase=80.5,
        location_count=2,
        native_isaac_render_diagnostics=native,
        locations=[
            _residual_location(
                "0001_low",
                fpv_mean=30.0,
                chase_mean=75.5,
                fpv_class="low_residual",
                chase_class="low_residual",
            ),
            _residual_location(
                "0002_edge",
                fpv_mean=36.0,
                chase_mean=85.5,
                fpv_class="view_dependent_color_residual",
                chase_class="low_residual",
            ),
        ],
    )
    report_side_probe = _write_robot_camera_manifest(
        tmp_path / "prepared_scale_square_view_rgb" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=32.0,
        chase=80.4,
        location_count=2,
        native_isaac_render_diagnostics={**native, "default_render_settings_changed": False},
    )
    (report_side_probe.parent / "isaac_state.json").write_text(
        json.dumps(
            {
                "robot_view_color_profile_override": {
                    "backend_view_rgb_gain": {
                        "isaaclab_subprocess": {
                            "fpv": [0.94, 0.84, 0.82],
                            "chase": [1.3, 1.2, 1.1],
                        }
                    },
                    "backend_view_rgb_gain_source": "unit report-side profile",
                }
            }
        ),
        encoding="utf-8",
    )
    applied_post_render_probe = _write_robot_camera_manifest(
        tmp_path / "applied_post_render_profile" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=31.0,
        chase=80.2,
        location_count=2,
        native_isaac_render_diagnostics={
            **native,
            "post_render_comparison_profile": {
                "applied": True,
                "source": "not_a_native_renderer_setting",
            },
        },
    )
    rejected_probe = _write_robot_camera_manifest(
        tmp_path / "distantlight_rotx25_chase_regression" / "comparison_manifest.json",
        scene_index=0,
        seed=6,
        generated_mess_count=5,
        fpv=34.0,
        chase=83.0,
        location_count=2,
        native_isaac_render_diagnostics=native,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[
            f"native_tone_exposure={native_probe}",
            f"prepared_scale_square_view_rgb={report_side_probe}",
            f"applied_post_render_profile={applied_post_render_probe}",
            f"distantlight_rotx25_chase_regression={rejected_probe}",
        ],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    batch = manifest["render_difference_probe_batch"]
    assert batch["status"] == "ranked_probe_batch_available"
    rows = {row["label"]: row for row in batch["ranked_rows"]}
    assert rows["native_tone_exposure"]["rank"] == 1
    assert rows["native_tone_exposure"]["probe_kind"] == "tone_color"
    assert rows["native_tone_exposure"]["policy_classification"] == "native_default_candidate"
    assert rows["native_tone_exposure"]["fpv_mean_abs_rgb_delta_vs_baseline"] == -7.0
    assert rows["native_tone_exposure"]["chase_mean_abs_rgb_delta_vs_baseline"] == 0.5
    assert rows["native_tone_exposure"]["native_settings_used"]["tone_mapping"] == {
        "op": {"status": "recorded", "value": 2}
    }
    assert rows["native_tone_exposure"]["residual_class_distribution"]["fpv"] == {
        "low_residual": 1,
        "view_dependent_color_residual": 1,
    }
    assert rows["prepared_scale_square_view_rgb"]["policy_classification"] == "report_side_only"
    assert rows["prepared_scale_square_view_rgb"]["report_side_comparison_profile"][
        "backend_view_rgb_gain"
    ] == {
        "isaaclab_subprocess": {
            "fpv": [0.94, 0.84, 0.82],
            "chase": [1.3, 1.2, 1.1],
        }
    }
    assert rows["applied_post_render_profile"]["policy_classification"] == "report_side_only"
    assert rows["applied_post_render_profile"]["classification_reason"] == (
        "probe uses report-side RGB/view compensation, not native renderer settings"
    )
    assert rows["distantlight_rotx25_chase_regression"]["probe_kind"] == "light_shadow"
    assert rows["distantlight_rotx25_chase_regression"]["policy_classification"] == "rejected"
    assert rows["distantlight_rotx25_chase_regression"]["chase_regression"] is True
    assert batch["policy_classification_counts"] == {
        "native_default_candidate": 1,
        "rejected": 1,
        "report_side_only": 2,
    }
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "<h2>Render Difference Probe Batch</h2>" in report_html
    assert "native_default_candidate" in report_html
    assert "report_side_only" in report_html
    assert "rejected" in report_html


def test_visual_parity_summary_ranks_capture_quality_downsample_against_metric_baseline(
    tmp_path: Path,
) -> None:
    summary = _load_module(
        SCRIPT_PATH,
        "summarize_robot_camera_visual_parity_capture_quality",
    )
    native = {
        "schema": "robot_camera_native_isaac_render_diagnostics_v1",
        "status": "native_settings_recorded",
        "settings_api_available": True,
        "default_render_settings_changed": False,
        "capture_quality_settings": {
            "render_settle_frames": 16,
            "anti_aliasing": {
                "status": "available",
                "value": 3,
                "setting_path": "/rtx/post/aa/op",
            },
            "denoise": {"status": "not_available", "value": None},
            "taa": {"status": "not_available", "value": None},
            "samples_per_pixel": {"status": "not_available", "value": None},
            "texture_filtering": {"status": "not_available", "value": None},
        },
    }
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=38.0,
        chase=60.0,
        location_count=4,
    )
    direct_baseline = _write_robot_camera_manifest(
        tmp_path / "baseline_1080" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=38.0,
        chase=55.5,
        location_count=4,
        render_width=1080,
        render_height=720,
        capture_quality_probe={
            "status": "direct_high_res_baseline",
            "render_resolution_requested": {"width": 1080, "height": 720},
            "render_resolution_saved": {"width": 1080, "height": 720},
            "metric_resolution": {"width": 1080, "height": 720},
            "saved_image_mode": "direct_capture",
            "metric_image_mode": "direct_capture",
            "render_settle_frames": 0,
        },
    )
    direct = _write_robot_camera_manifest(
        tmp_path / "hires_1080_direct" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=32.0,
        chase=55.0,
        location_count=4,
        render_width=1080,
        render_height=720,
        capture_quality_probe={
            "status": "capture_quality_probe_configured",
            "render_resolution_requested": {"width": 1080, "height": 720},
            "render_resolution_saved": {"width": 1080, "height": 720},
            "metric_resolution": {"width": 1080, "height": 720},
            "saved_image_mode": "direct_capture",
            "metric_image_mode": "direct_capture",
            "render_settle_frames": 0,
        },
        native_isaac_render_diagnostics=native,
    )
    downsample = _write_robot_camera_manifest(
        tmp_path / "hires_1080_downsample540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=34.0,
        chase=59.0,
        location_count=4,
        render_width=1080,
        render_height=720,
        saved_report_width=540,
        saved_report_height=360,
        metric_width=540,
        metric_height=360,
        capture_quality_probe={
            "status": "capture_quality_probe_configured",
            "render_resolution_requested": {"width": 1080, "height": 720},
            "render_resolution_saved": {"width": 540, "height": 360},
            "metric_resolution": {"width": 540, "height": 360},
            "saved_image_mode": "downsampled_from_render_capture",
            "metric_image_mode": "downsampled_from_render_capture",
            "downsample_filter": "lanczos",
            "render_settle_frames": 16,
        },
        native_isaac_render_diagnostics=native,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline, direct_baseline],
        probe_specs=[
            f"hires_1080_direct={direct}",
            f"hires_1080_downsample540={downsample}",
        ],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    rows = {row["label"]: row for row in manifest["render_difference_probe_batch"]["ranked_rows"]}
    assert rows["hires_1080_direct"]["policy_classification"] == "capture_quality_probe"
    assert rows["hires_1080_direct"]["baseline_path"] == str(direct_baseline)
    assert rows["hires_1080_direct"]["fpv_mean_abs_rgb_delta_vs_baseline"] == -6.0
    assert rows["hires_1080_direct"]["metric_resolution"] == {"width": 1080, "height": 720}
    assert rows["hires_1080_downsample540"]["probe_kind"] == "capture_quality"
    assert rows["hires_1080_downsample540"]["policy_classification"] == ("capture_quality_probe")
    assert rows["hires_1080_downsample540"]["baseline_path"] == str(baseline)
    assert rows["hires_1080_downsample540"]["fpv_mean_abs_rgb_delta_vs_baseline"] == -4.0
    assert rows["hires_1080_downsample540"]["chase_mean_abs_rgb_delta_vs_baseline"] == -1.0
    assert rows["hires_1080_downsample540"]["render_resolution_requested"] == {
        "width": 1080,
        "height": 720,
    }
    assert rows["hires_1080_downsample540"]["metric_resolution"] == {
        "width": 540,
        "height": 360,
    }
    assert rows["hires_1080_downsample540"]["metric_image_mode"] == (
        "downsampled_from_render_capture"
    )
    assert rows["hires_1080_downsample540"]["render_settle_frames"] == 16
    assert (
        rows["hires_1080_downsample540"]["capture_quality_settings"]["anti_aliasing"]["status"]
        == "available"
    )
    assert manifest["render_difference_probe_batch"]["policy_classification_counts"] == {
        "capture_quality_probe": 2,
    }
    report_html = (tmp_path / "summary" / "report.html").read_text(encoding="utf-8")
    assert "<h2>Capture Quality Probe Metadata</h2>" in report_html
    assert "hires_1080_downsample540" in report_html
    assert "1080x720" in report_html
    assert "540x360" in report_html
    assert "capture_quality_probe" in report_html


def test_visual_parity_summary_does_not_treat_native_quality_metadata_as_probe(
    tmp_path: Path,
) -> None:
    summary = _load_module(
        SCRIPT_PATH,
        "summarize_robot_camera_visual_parity_native_quality_metadata",
    )
    native = {
        "schema": "robot_camera_native_isaac_render_diagnostics_v1",
        "status": "native_settings_recorded",
        "settings_api_available": True,
        "default_render_settings_changed": False,
        "capture_quality_settings": {
            "anti_aliasing": {
                "status": "available",
                "value": 3,
                "setting_path": "/rtx/post/aa/op",
            },
            "denoise": {"status": "not_available", "value": None},
            "taa": {"status": "not_available", "value": None},
            "samples_per_pixel": {"status": "not_available", "value": None},
            "texture_filtering": {"status": "not_available", "value": None},
        },
    }
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=38.0,
        chase=60.0,
        location_count=4,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "aa_metadata_only" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=34.0,
        chase=59.5,
        location_count=4,
        native_isaac_render_diagnostics=native,
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"aa_metadata_only={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    rows = {row["label"]: row for row in manifest["render_difference_probe_batch"]["ranked_rows"]}
    assert rows["aa_metadata_only"]["policy_classification"] == "native_default_candidate"
    assert rows["aa_metadata_only"]["probe_kind"] != "capture_quality"
    assert rows["aa_metadata_only"]["metric_image_mode"] == "direct_capture"
    assert rows["aa_metadata_only"]["render_resolution_requested"] == {
        "width": 540,
        "height": 360,
    }
    assert manifest["render_difference_probe_batch"]["policy_classification_counts"] == {
        "native_default_candidate": 1,
    }


def test_visual_parity_summary_treats_requested_aa_as_capture_quality_probe(
    tmp_path: Path,
) -> None:
    summary = _load_module(
        SCRIPT_PATH,
        "summarize_robot_camera_visual_parity_requested_aa",
    )
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=38.0,
        chase=60.0,
        location_count=4,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "aa_op2_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=37.9,
        chase=60.1,
        location_count=4,
        capture_quality_probe={
            "status": "capture_quality_probe_configured",
            "render_resolution_requested": {"width": 540, "height": 360},
            "render_resolution_saved": {"width": 540, "height": 360},
            "metric_resolution": {"width": 540, "height": 360},
            "saved_image_mode": "direct_capture",
            "metric_image_mode": "direct_capture",
            "render_settle_frames": 0,
            "anti_aliasing": {
                "name": "anti_aliasing",
                "status": "requested",
                "value": 2,
                "requested_value": 2,
                "setting_path": "/rtx/post/aa/op",
                "default_render_settings_changed": True,
            },
        },
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"aa_op2_540={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    rows = {row["label"]: row for row in manifest["render_difference_probe_batch"]["ranked_rows"]}
    assert rows["aa_op2_540"]["probe_kind"] == "capture_quality"
    assert rows["aa_op2_540"]["policy_classification"] == "capture_quality_probe"
    assert rows["aa_op2_540"]["capture_quality_settings"]["anti_aliasing"]["status"] == (
        "requested"
    )


def test_visual_parity_summary_treats_requested_tonemap_as_capture_quality_probe(
    tmp_path: Path,
) -> None:
    summary = _load_module(
        SCRIPT_PATH,
        "summarize_robot_camera_visual_parity_requested_tonemap",
    )
    baseline = _write_robot_camera_manifest(
        tmp_path / "baseline_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=38.0,
        chase=60.0,
        location_count=4,
    )
    probe = _write_robot_camera_manifest(
        tmp_path / "tonemap_op5_540" / "comparison_manifest.json",
        scene_index=1,
        seed=6,
        generated_mess_count=2,
        fpv=34.0,
        chase=60.2,
        location_count=4,
        capture_quality_probe={
            "status": "capture_quality_probe_configured",
            "render_resolution_requested": {"width": 540, "height": 360},
            "render_resolution_saved": {"width": 540, "height": 360},
            "metric_resolution": {"width": 540, "height": 360},
            "saved_image_mode": "direct_capture",
            "metric_image_mode": "direct_capture",
            "render_settle_frames": 0,
            "tonemap_operator": {
                "name": "tonemap_operator",
                "status": "requested",
                "value": 5,
                "requested_value": 5,
                "setting_path": "/rtx/post/tonemap/op",
                "default_render_settings_changed": True,
            },
        },
    )

    manifest = summary.build_summary(
        output_dir=tmp_path / "summary",
        baseline_manifest_paths=[baseline],
        probe_specs=[f"tonemap_op5_540={probe}"],
        raw_fpv_run_result_paths=[],
        calibration_manifest_paths=[],
        required_scene_count=1,
        required_seed_count=1,
    )

    rows = {row["label"]: row for row in manifest["render_difference_probe_batch"]["ranked_rows"]}
    assert rows["tonemap_op5_540"]["probe_kind"] == "capture_quality"
    assert rows["tonemap_op5_540"]["policy_classification"] == "capture_quality_probe"
    assert rows["tonemap_op5_540"]["capture_quality_settings"]["tonemap_operator"]["status"] == (
        "requested"
    )


def test_visual_parity_summary_blocks_default_rendering_without_native_diagnostics(
    tmp_path: Path,
) -> None:
    summary = _load_module(
        SCRIPT_PATH,
        "summarize_robot_camera_visual_parity_native_render_required",
    )
    checks = {
        "head_camera_contract": {"status": "head_camera_geometry_aligned"},
        "raw_fpv_input_lane": {"status": "raw_fpv_agent_input_uses_head_camera"},
        "corpus_coverage": {"status": "broad_corpus_ready"},
        "calibration_scene": {
            "status": "calibration_scene_evidence_loaded",
            "default_rendering_ready": True,
        },
        "native_isaac_render_diagnostics": {
            "status": "native_isaac_render_diagnostics_missing",
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

    assert summary._overall_status(checks) == "active"
    default_rendering = summary._default_rendering_visual_parity(checks)
    assert default_rendering["status"] == "not_ready"
    assert any(
        blocker.get("check_id") == "native_isaac_render_diagnostics"
        for blocker in default_rendering["blockers"]
    )
    report_side = summary._report_side_visual_parity(checks)
    assert report_side["status"] == "report_side_visual_parity_ready"


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
        "native_isaac_render_diagnostics": {"status": "native_isaac_render_diagnostics_recorded"},
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
        "native_isaac_render_diagnostics": {"status": "native_isaac_render_diagnostics_recorded"},
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
        "native_isaac_render_diagnostics": {"status": "native_isaac_render_diagnostics_recorded"},
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
    object_visual_parity_audit: dict | None = None,
    top_level_object_visual_parity_audit: dict | None = None,
    object_render_parity_diagnostics: dict | None = None,
    native_isaac_render_diagnostics: dict | None = None,
    render_width: int = 540,
    render_height: int = 360,
    saved_report_width: int | None = None,
    saved_report_height: int | None = None,
    metric_width: int | None = None,
    metric_height: int | None = None,
    capture_quality_probe: dict | None = None,
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
            "render_width": render_width,
            "render_height": render_height,
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
            "object_visual_parity_audit": object_visual_parity_audit or {},
            "object_render_parity_diagnostics": object_render_parity_diagnostics or {},
            "native_isaac_render_diagnostics": native_isaac_render_diagnostics or {},
        },
        "locations": default_locations,
    }
    if saved_report_width is not None:
        payload["scene"]["saved_report_width"] = saved_report_width
    if saved_report_height is not None:
        payload["scene"]["saved_report_height"] = saved_report_height
    if metric_width is not None:
        payload["scene"]["metric_width"] = metric_width
    if metric_height is not None:
        payload["scene"]["metric_height"] = metric_height
    if capture_quality_probe is not None:
        payload["capture_quality_probe"] = {
            "schema": "robot_camera_capture_quality_probe_v1",
            "status": "unit_fixture",
            "policy_classification": "capture_quality_probe",
            "default_renderer_promotion": False,
            **capture_quality_probe,
        }
    if top_level_object_visual_parity_audit is not None:
        payload["object_visual_parity_audit"] = top_level_object_visual_parity_audit
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


def _residual_location(
    label: str,
    *,
    fpv_mean: float,
    chase_mean: float,
    fpv_class: str,
    chase_class: str,
) -> dict:
    return {
        "label": label,
        "target": {"target_id": label},
        "status": "success",
        "image_diffs": {
            "fpv": _image_diff_with_class(fpv_mean, fpv_class),
            "chase": _image_diff_with_class(chase_mean, chase_class),
        },
    }


def _image_diff_with_class(mean_abs_rgb: float, residual_class: str) -> dict:
    payload = _image_diff(mean_abs_rgb, 3.0, 85.0, 95.0)
    payload["residual"]["residual_class"] = residual_class
    return payload


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

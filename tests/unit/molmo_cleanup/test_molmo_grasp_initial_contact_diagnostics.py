from __future__ import annotations

from pathlib import Path

from roboclaws.household.grasp_initial_contact_diagnostics import (
    summarize_initial_contact_variants,
)
from roboclaws.household.report import render_grasp_initial_contact_diagnostics_report


def test_summarize_initial_contact_variants_selects_success_with_low_displacement() -> None:
    summary = summarize_initial_contact_variants(
        [
            {
                "name": "upstream_like",
                "success_count": 0,
                "avg_initial_displacement_m": 0.7,
                "initial_contact_count": 24,
            },
            {
                "name": "positive_far",
                "success_count": 8,
                "avg_initial_displacement_m": 0.0,
                "initial_contact_count": 0,
            },
            {
                "name": "positive_close",
                "success_count": 8,
                "avg_initial_displacement_m": 0.3,
                "initial_contact_count": 10,
            },
        ]
    )

    assert summary["successful_variant_count"] == 2
    assert summary["best_variant"]["name"] == "positive_far"


def test_render_grasp_initial_contact_diagnostics_report(tmp_path: Path) -> None:
    result = {
        "schema": "molmospaces_grasp_initial_contact_diagnostics_v1",
        "status": "ready",
        "object_name": "Bread_1",
        "candidate_count": 24,
        "variant_count": 2,
        "successful_variant_count": 1,
        "candidate_grasps_path": "Bread_1_grasps.json",
        "object_xml": "Bread_1_mesh.xml",
        "artifact_dir": str(tmp_path),
        "probe_script_path": str(tmp_path / "probe.py"),
        "probe_output_path": str(tmp_path / "result.json"),
        "assets_symlink": {
            "status": "ready",
            "path": "assets",
            "target": "assets",
            "created": False,
        },
        "command": ["python", "probe.py"],
        "command_result": {"status": "ready", "returncode": 0, "stdout": "", "stderr": ""},
        "best_variant": {
            "name": "sign_1_dist_0.8_settle_50",
            "approach_sign": 1,
            "approach_distance": 0.8,
            "settle_steps": 50,
            "success_count": 8,
            "sample_rows": [
                {
                    "candidate_index": 0,
                    "success": True,
                    "initial_contact_sides": [],
                    "initial_contact_pair_count": 0,
                    "initial_displacement_m": 0.0,
                    "final_contact_sides": ["left", "right"],
                    "final_contact_pair_count": 2,
                    "final_displacement_m": 0.02,
                }
            ],
        },
        "variants": [
            {
                "name": "sign_-1_dist_0.1_settle_500",
                "classification": "zero_success",
                "approach_sign": -1,
                "approach_distance": 0.1,
                "settle_steps": 500,
                "candidate_count": 24,
                "success_count": 0,
                "initial_contact_count": 0,
                "initial_displaced_count": 20,
                "avg_initial_displacement_m": 0.68,
                "max_initial_displacement_m": 2.1,
                "successful_candidate_indices": [],
            },
            {
                "name": "sign_1_dist_0.8_settle_50",
                "classification": "nonzero_success",
                "approach_sign": 1,
                "approach_distance": 0.8,
                "settle_steps": 50,
                "candidate_count": 24,
                "success_count": 8,
                "initial_contact_count": 0,
                "initial_displaced_count": 0,
                "avg_initial_displacement_m": 0.0,
                "max_initial_displacement_m": 0.0,
                "successful_candidate_indices": [1, 2],
            },
        ],
        "blockers": [],
        "blocker_count": 0,
        "evidence_note": "diagnostic",
    }

    report_path = render_grasp_initial_contact_diagnostics_report(
        output_dir=tmp_path,
        result=result,
    )

    report_text = report_path.read_text(encoding="utf-8")
    assert "MolmoSpaces Grasp Initial Contact Diagnostics" in report_text
    assert "sign_1_dist_0.8_settle_50" in report_text
    assert "Best Variant Samples" in report_text
    assert "nonzero_success" in report_text

from __future__ import annotations

import json
from pathlib import Path

from scripts.operator_console.export_scene_sampler_readiness import (
    _candidate_indices,
    export_readiness_artifacts,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_scene_sampler_readiness_export_writes_artifacts(tmp_path) -> None:
    result = export_readiness_artifacts(output_dir=tmp_path)

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    artifacts = result["artifacts"]
    assert set(artifacts) == {
        "candidate_readiness",
        "generated_eval_samples",
        "generated_eval_suite",
        "manifest",
        "eval_projection",
        "readiness_report",
        "scanner_admission",
        "scanner_execution_plan",
        "selection_gaps",
        "source_availability",
        "source_prep",
    }
    manifest = json.loads((tmp_path / "scene_sampler_manifest.json").read_text())
    projection = json.loads((tmp_path / "scene_sampler_eval_projection.json").read_text())
    readiness = json.loads((tmp_path / "scene_sampler_readiness_report.json").read_text())
    availability = json.loads(
        (tmp_path / "scene_sampler_source_availability.json").read_text()
    )
    candidates = json.loads((tmp_path / "scene_sampler_candidate_readiness.json").read_text())
    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())
    source_prep = json.loads((tmp_path / "scene_sampler_source_prep.json").read_text())
    scanner_admission = json.loads(
        (tmp_path / "scene_sampler_scanner_admission.json").read_text()
    )
    scanner_execution = json.loads(
        (tmp_path / "scene_sampler_scanner_execution_plan.json").read_text()
    )
    generated_suite = json.loads(
        (tmp_path / "generated_eval/scene_sampler_stress.json").read_text()
    )
    assert manifest["ui_target_per_scene_source"] == 3
    assert manifest["eval_target_per_scene_source"] == 10
    assert projection["scene_sources"]["procthor-10k-val"]["ready_count"] == 5
    assert projection["scene_sources"]["procthor-10k-val"]["support_status"] == "partial"
    assert projection["scene_sources"]["ithor"]["support_status"] == "blocked"
    assert projection["summary"]["ready_sample_count"] == 5
    assert projection["summary"]["remaining_sample_count"] == 35
    assert readiness["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert readiness["sources"]["ithor"]["blocked_rows"][0]["failure_class"] == (
        "environment_blocked"
    )
    assert availability["schema"] == "molmospaces_scene_source_availability_report_v1"
    assert availability["probe_mode"] == "no_download_no_vlm"
    assert availability["summary"]["source_count"] == 4
    assert "blocked_source_count" in availability["summary"]
    assert availability["sources"]["ithor"]["failure_class"] in {
        "",
        "environment_blocked",
    }
    assert candidates["schema"] == "molmospaces_scene_sampler_candidate_readiness_v1"
    assert candidates["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert candidates["sources"]["ithor"]["blocked_candidate_count"] == 10
    assert selection["schema"] == "molmospaces_scene_sampler_selection_gaps_v1"
    assert selection["sources"]["procthor-10k-val"]["eval_needed_count"] == 5
    assert selection["sources"]["ithor"]["ui_needed_count"] == 3
    assert source_prep["schema"] == "molmospaces_scene_sampler_source_prep_v1"
    assert source_prep["probe_mode"] == "no_download_no_vlm"
    assert source_prep["download_policy"] == "manual_operator_only"
    assert "missing_resource_summary" in source_prep["summary"]
    assert source_prep["sources"]["ithor"]["molmospaces_get_scenes_call"] == (
        'get_scenes("ithor", "train")'
    )
    assert source_prep["sources"]["procthor-objaverse-val"][
        "molmospaces_get_scenes_call"
    ] == 'get_scenes("procthor-objaverse", "val")'
    assert source_prep["sources"]["holodeck-objaverse-val"][
        "molmospaces_get_scenes_call"
    ] == 'get_scenes("holodeck-objaverse", "val")'
    assert source_prep["sources"]["procthor-10k-val"][
        "recommended_candidate_range"
    ] == "0:19"
    assert "molmospaces_scene_version" in source_prep["sources"]["procthor-10k-val"]
    assert source_prep["sources"]["procthor-10k-val"]["scene_index_map_status"] in {
        "available",
        "blocked",
    }
    assert "candidate_scene_refs" in source_prep["sources"]["procthor-10k-val"]
    assert any(
        command["name"] == "install_single_scene_example"
        for command in source_prep["sources"]["ithor"]["operator_commands"]
    )
    assert scanner_admission["schema"] == "molmospaces_scene_sampler_scanner_admission_v1"
    assert scanner_admission["probe_mode"] == "no_download_no_backend_no_vlm"
    assert scanner_admission["summary"]["source_count"] == 4
    assert "missing_gate_counts" in scanner_admission["summary"]
    assert scanner_admission["sources"]["procthor-10k-val"]["summary"][
        "admitted_count"
    ] == 5
    assert scanner_admission["sources"]["ithor"]["needed_ui_count"] == 3
    assert scanner_execution["schema"] == (
        "molmospaces_scene_sampler_scanner_execution_plan_v1"
    )
    assert scanner_execution["probe_mode"] == "no_download_no_backend_no_vlm"
    assert scanner_execution["summary"]["source_count"] == 4
    assert "ready_for_product_smoke_count" in scanner_execution["summary"]
    ithor_scanner = scanner_execution["sources"]["ithor"]["candidates"][0]
    assert ithor_scanner["world_id"] == "molmospaces/ithor/1"
    assert ithor_scanner["scanner_status"] in {
        "blocked_missing_resources",
        "ready_for_product_smoke",
    }
    assert "render_scene_previews.py --world molmospaces/ithor/1" in ithor_scanner[
        "preview_command"
    ]
    assert "world=molmospaces/ithor/1" in ithor_scanner["map_build_product_smoke_command"]
    assert generated_suite == json.loads(
        (
            REPO_ROOT / "evals/household_world/suites/scene_sampler_stress.json"
        ).read_text(encoding="utf-8")
    )
    assert len(artifacts["generated_eval_samples"]) == 5
    generated_sample = json.loads(
        (
            tmp_path
            / "generated_eval/samples/scene_sampler/procthor-10k-val_0_map_build.json"
        ).read_text(encoding="utf-8")
    )
    committed_sample = json.loads(
        (
            REPO_ROOT
            / "evals/household_world/samples/scene_sampler/procthor-10k-val_0_map_build.json"
        ).read_text(encoding="utf-8")
    )
    assert generated_sample == committed_sample


def test_scene_sampler_readiness_export_can_require_ui_supported_source(tmp_path) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_ui_supported_sources=("procthor-10k-val",),
    )

    assert result["status"] == "success"
    assert result["threshold_failures"] == []


def test_scene_sampler_readiness_export_fails_missing_eval_completion(tmp_path) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_eval_complete_sources=("procthor-10k-val",),
    )

    assert result["status"] == "failed"
    assert result["threshold_failures"] == [
        {
            "scene_source": "procthor-10k-val",
            "threshold": "eval_complete",
            "reason": "eval_not_complete",
            "ready_count": 5,
            "target_count": 10,
        }
    ]


def test_scene_sampler_readiness_export_fails_missing_selection_capacity(tmp_path) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_selection_capacity_sources=("procthor-10k-val",),
    )

    assert result["status"] == "failed"
    assert result["threshold_failures"] == [
        {
            "scene_source": "procthor-10k-val",
            "threshold": "selection_capacity",
            "reason": "insufficient_candidate_scan_capacity",
            "ui_needed_count": 0,
            "ui_available_count": 0,
            "eval_needed_count": 5,
            "eval_available_count": 2,
        }
    ]


def test_scene_sampler_readiness_export_selection_capacity_can_use_expanded_range(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        candidate_indices=tuple(range(20)),
        required_selection_capacity_sources=("procthor-10k-val",),
    )

    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    assert result["candidate_indices"][0] == 0
    assert result["candidate_indices"][-1] == 19
    assert selection["sources"]["procthor-10k-val"]["next_eval_scan_world_ids"][:5] == [
        "molmospaces/procthor-10k-val/6",
        "molmospaces/procthor-10k-val/8",
        "molmospaces/procthor-10k-val/10",
        "molmospaces/procthor-10k-val/11",
        "molmospaces/procthor-10k-val/12",
    ]


def test_scene_sampler_readiness_export_selection_capacity_passes_when_candidates_exist(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        candidate_indices=tuple(range(11)),
        required_selection_capacity_sources=("ithor",),
    )

    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    assert selection["sources"]["ithor"]["next_ui_scan_world_ids"] == [
        "molmospaces/ithor/1",
        "molmospaces/ithor/2",
        "molmospaces/ithor/3",
    ]
    assert selection["sources"]["ithor"]["next_eval_scan_world_ids"][0] == (
        "molmospaces/ithor/1"
    )
    assert selection["sources"]["ithor"]["next_eval_scan_world_ids"][-1] == (
        "molmospaces/ithor/10"
    )
    source_prep = json.loads((tmp_path / "scene_sampler_source_prep.json").read_text())
    install_candidates = source_prep["sources"]["ithor"]["install_candidates"]
    assert install_candidates[0]["scene_index"] == 1
    assert install_candidates[0]["world_id"] == "molmospaces/ithor/1"
    assert install_candidates[0]["primary_path"].endswith("FloorPlan1_physics.xml")
    install_command = install_candidates[0]["install_command"]
    assert "mapping[1]" in install_command
    assert "_scene_xml_path_from_ref(scene_ref, get_scenes_root())" in install_command
    assert "for role in ('base', 'physics', 'ceiling')" in install_command


def test_scene_sampler_readiness_export_candidate_index_options_are_sorted_unique() -> None:
    assert _candidate_indices(candidate_indexes=(4, 1), candidate_ranges=("2:3", "3:5")) == (
        1,
        2,
        3,
        4,
        5,
    )


def test_scene_sampler_readiness_export_cli_returns_failure_for_unmet_threshold(
    tmp_path,
    capsys,
) -> None:
    code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--require-eval-complete-source",
            "procthor-10k-val",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["threshold_failures"][0]["ready_count"] == 5

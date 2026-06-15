from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.launch import scene_sampler
from scripts.operator_console.export_scene_sampler_readiness import (
    _candidate_indices,
    export_readiness_artifacts,
    main,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture(autouse=True)
def isolate_scanner_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    scanner_root = tmp_path / "scanner-output"
    monkeypatch.setattr(scene_sampler, "_SCANNER_OUTPUT_ROOT", scanner_root)
    monkeypatch.setattr(scene_sampler, "_SCANNER_PREVIEW_ROOT", scanner_root / "previews")
    monkeypatch.setattr(
        scene_sampler,
        "_SCANNER_PRODUCT_SMOKE_ROOT",
        scanner_root / "product-smoke",
    )
    monkeypatch.setattr(
        scene_sampler,
        "_molmospaces_module_status",
        lambda: (False, "module_not_importable:molmo_spaces", ""),
    )


def test_scene_sampler_readiness_export_writes_artifacts(tmp_path) -> None:
    result = export_readiness_artifacts(output_dir=tmp_path)

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    assert result["summary"]["readiness"]["source_count"] == 4
    assert result["summary"]["candidate_readiness"]["source_count"] == 4
    assert result["summary"]["selection_gaps"]["source_count"] == 4
    assert result["summary"]["source_prep"]["source_count"] == 4
    artifacts = result["artifacts"]
    assert set(artifacts) == {
        "candidate_readiness",
        "generated_eval_samples",
        "generated_eval_suite",
        "manifest",
        "eval_projection",
        "next_flow_worklist",
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
    availability = json.loads((tmp_path / "scene_sampler_source_availability.json").read_text())
    candidates = json.loads((tmp_path / "scene_sampler_candidate_readiness.json").read_text())
    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())
    source_prep = json.loads((tmp_path / "scene_sampler_source_prep.json").read_text())
    scanner_admission = json.loads((tmp_path / "scene_sampler_scanner_admission.json").read_text())
    scanner_execution = json.loads(
        (tmp_path / "scene_sampler_scanner_execution_plan.json").read_text()
    )
    next_flow = json.loads((tmp_path / "scene_sampler_next_flow_worklist.json").read_text())
    generated_suite = json.loads(
        (tmp_path / "generated_eval/scene_sampler_stress.json").read_text()
    )
    assert manifest["ui_target_per_scene_source"] == 3
    assert manifest["eval_target_per_scene_source"] == 10
    assert projection["scene_sources"]["procthor-10k-val"]["ready_count"] == 10
    assert projection["scene_sources"]["procthor-10k-val"]["support_status"] == "complete"
    assert projection["scene_sources"]["ithor"]["support_status"] == "blocked"
    assert projection["summary"]["ready_sample_count"] == 20
    assert projection["summary"]["remaining_sample_count"] == 20
    assert readiness["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert readiness["sources"]["procthor-objaverse-val"]["ui_ready_count"] == 3
    assert readiness["sources"]["procthor-objaverse-val"]["eval_ready_count"] == 10
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
    assert candidates["summary"]["source_count"] == 4
    assert "eval_needed_count" in candidates["summary"]
    assert candidates["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert candidates["sources"]["procthor-10k-val"]["eval_ready_count"] == 10
    assert candidates["sources"]["procthor-objaverse-val"]["ui_ready_count"] == 3
    assert candidates["sources"]["procthor-objaverse-val"]["eval_ready_count"] == 10
    assert candidates["sources"]["ithor"]["eval_ready_count"] == 0
    assert selection["schema"] == "molmospaces_scene_sampler_selection_gaps_v1"
    assert selection["summary"]["source_count"] == 4
    assert "worklist" in selection["summary"]
    assert selection["sources"]["procthor-10k-val"]["eval_needed_count"] == 0
    assert selection["sources"]["procthor-10k-val"]["selection_capacity_status"] == "complete"
    assert selection["sources"]["procthor-10k-val"]["next_action"] == "none"
    assert selection["sources"]["ithor"]["ui_needed_count"] == 3
    assert selection["sources"]["ithor"]["next_action"] in {
        "expand_candidate_range",
        "run_source_prep_before_scanner",
        "run_scanner_admission",
    }
    assert source_prep["schema"] == "molmospaces_scene_sampler_source_prep_v1"
    assert source_prep["probe_mode"] == "no_download_no_vlm"
    assert source_prep["download_policy"] == "manual_operator_only"
    assert "missing_resource_summary" in source_prep["summary"]
    assert "prep_status_counts" in source_prep["summary"]
    assert "worklist" in source_prep["summary"]
    assert source_prep["worklist"] == source_prep["summary"]["worklist"]
    assert source_prep["worklist"][0]["next_action"] in {
        "install_repo_dev_runtime",
        "run_manual_source_prep",
        "run_scanner_admission",
        "expand_candidate_range",
        "inspect_source_prep",
    }
    assert source_prep["sources"]["ithor"]["molmospaces_get_scenes_call"] == (
        'get_scenes("ithor", "train")'
    )
    assert (
        source_prep["sources"]["procthor-objaverse-val"]["molmospaces_get_scenes_call"]
        == 'get_scenes("procthor-objaverse", "val")'
    )
    assert (
        source_prep["sources"]["holodeck-objaverse-val"]["molmospaces_get_scenes_call"]
        == 'get_scenes("holodeck-objaverse", "val")'
    )
    assert source_prep["sources"]["procthor-10k-val"]["recommended_candidate_range"] == "0:9"
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
    assert scanner_admission["sources"]["procthor-10k-val"]["summary"]["admitted_count"] == 10
    assert scanner_admission["sources"]["ithor"]["needed_ui_count"] == 3
    assert scanner_execution["schema"] == ("molmospaces_scene_sampler_scanner_execution_plan_v1")
    assert scanner_execution["probe_mode"] == "no_download_no_backend_no_vlm"
    assert scanner_execution["summary"]["source_count"] == 4
    assert "ready_for_product_smoke_count" in scanner_execution["summary"]
    assert next_flow["schema"] == "molmospaces_scene_sampler_next_flow_worklist_v1"
    assert next_flow["probe_mode"] == "no_download_no_backend_no_vlm"
    assert next_flow["download_policy"] == "manual_operator_only"
    assert next_flow["summary"]["source_count"] == 4
    assert next_flow["summary"]["ui_needed_count"] == 6
    assert next_flow["summary"]["eval_needed_count"] == 20
    assert "worklist" in next_flow["summary"]
    assert next_flow["worklist"] == next_flow["summary"]["worklist"]
    assert next_flow["worklist"][0]["scene_source"] in {
        "ithor",
        "procthor-objaverse-val",
        "holodeck-objaverse-val",
    }
    assert result["summary"]["next_flow_worklist"]["source_count"] == 4
    assert next_flow["artifact_paths"]["readiness_output_dir"] == str(tmp_path)
    assert next_flow["artifact_paths"]["source_prep"] == str(
        tmp_path / "scene_sampler_source_prep.json"
    )
    assert next_flow["sources"]["procthor-10k-val"]["ui_status"] == "ready"
    assert next_flow["sources"]["procthor-10k-val"]["eval_ready_count"] == 10
    assert next_flow["sources"]["procthor-10k-val"]["eval_needed_count"] == 0
    assert next_flow["sources"]["procthor-10k-val"]["next_action"] == "none"
    assert next_flow["sources"]["procthor-objaverse-val"]["ui_status"] == "ready"
    assert next_flow["sources"]["procthor-objaverse-val"]["eval_ready_count"] == 10
    assert next_flow["sources"]["procthor-objaverse-val"]["eval_needed_count"] == 0
    assert next_flow["sources"]["procthor-objaverse-val"]["next_action"] == "none"
    assert next_flow["sources"]["ithor"]["ui_needed_count"] == 3
    assert next_flow["sources"]["ithor"]["eval_needed_count"] == 10
    assert next_flow["sources"]["ithor"]["next_action"] in {
        "install_repo_dev_runtime",
        "run_manual_source_prep",
        "run_scanner_plan_for_ready_candidates",
        "expand_candidate_range",
    }
    assert next_flow["sources"]["ithor"]["recommended_candidate_range"] in {"0:9", "0:19"}
    assert "source_asset_available" in next_flow["sources"]["ithor"]["missing_gate_counts"]
    ithor_commands = next_flow["sources"]["ithor"]["recommended_commands"]
    assert "source_prep_dry_run" in [command["name"] for command in ithor_commands]
    assert "source_prep_execute" in [command["name"] for command in ithor_commands]
    assert any("--worklist" in command["command"] for command in ithor_commands)
    assert any("--execute" in command["command"] for command in ithor_commands)
    if scanner_execution["sources"]["ithor"]["candidates"]:
        ithor_scanner = scanner_execution["sources"]["ithor"]["candidates"][0]
        assert ithor_scanner["world_id"].startswith("molmospaces/ithor/")
        assert ithor_scanner["scanner_status"] in {
            "blocked_missing_resources",
            "ready_for_product_smoke",
        }
        assert ithor_scanner["scene_family"] == "ithor"
        assert ithor_scanner["failure_class"] == "environment_blocked"
        assert ithor_scanner["room_count"] == 0
        assert ithor_scanner["waypoint_count"] == 0
        assert ithor_scanner["category_provenance"] == "unavailable"
        assert "source_asset_available" in ithor_scanner["required_gates"]
        assert "source_asset_available" in ithor_scanner["missing_gates"]
        assert "render_scene_previews.py --world molmospaces/ithor/" in ithor_scanner[
            "preview_command"
        ]
        assert "world=molmospaces/ithor/" in ithor_scanner["map_build_product_smoke_command"]
    assert generated_suite == json.loads(
        (REPO_ROOT / "evals/household_world/suites/scene_sampler_stress.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(artifacts["generated_eval_samples"]) == 20
    generated_sample = json.loads(
        (
            tmp_path / "generated_eval/samples/scene_sampler/procthor-10k-val_0_map_build.json"
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


def test_scene_sampler_readiness_export_can_require_eval_complete_source(tmp_path) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_eval_complete_sources=("procthor-10k-val",),
    )

    assert result["status"] == "success"
    assert result["threshold_failures"] == []


def test_scene_sampler_readiness_export_fails_missing_eval_completion(tmp_path) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_eval_complete_sources=("ithor",),
    )

    assert result["status"] == "failed"
    assert result["threshold_failures"] == [
        {
            "scene_source": "ithor",
            "threshold": "eval_complete",
            "reason": "eval_not_complete",
            "ready_count": 0,
            "target_count": 10,
        }
    ]


def test_scene_sampler_readiness_export_can_require_complete_selection_capacity(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_selection_capacity_sources=("procthor-10k-val",),
    )

    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    assert selection["sources"]["procthor-10k-val"]["selection_capacity_status"] == "complete"
    assert selection["sources"]["procthor-10k-val"]["next_eval_scan_world_ids"] == []


def test_scene_sampler_readiness_export_selection_capacity_fails_for_sparse_ithor_range(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        candidate_indices=(),
        required_selection_capacity_sources=("ithor",),
    )

    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())

    assert result["status"] == "failed"
    assert result["threshold_failures"] == [
        {
            "scene_source": "ithor",
            "threshold": "selection_capacity",
            "reason": "insufficient_candidate_scan_capacity",
            "ui_needed_count": 3,
            "ui_available_count": 0,
            "eval_needed_count": 10,
            "eval_available_count": 0,
        }
    ]
    assert selection["sources"]["ithor"]["next_ui_scan_world_ids"] == []
    assert selection["sources"]["ithor"]["next_eval_scan_world_ids"] == []


def test_scene_sampler_readiness_export_fails_when_scanner_source_has_no_ready_candidate(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        candidate_indices=tuple(range(20)),
        required_scanner_ready_sources=("ithor",),
    )

    assert result["status"] == "failed"
    assert result["threshold_failures"] == [
        {
            "scene_source": "ithor",
            "threshold": "scanner_ready",
            "reason": "no_ready_product_smoke_candidates",
            "ready_for_product_smoke_count": 0,
            "candidate_count": 10,
            "blocked_count": 10,
            "prep_status": "blocked_molmospaces_module",
        }
    ]


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
            "ithor",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["summary"]["eval_projection"]["ready_sample_count"] == 20
    assert payload["threshold_failures"][0]["ready_count"] == 0


def test_scene_sampler_readiness_export_cli_accepts_scanner_ready_threshold(
    tmp_path,
    capsys,
) -> None:
    code = main(
        [
            "--output-dir",
            str(tmp_path),
            "--candidate-range",
            "0:19",
            "--require-scanner-ready-source",
            "ithor",
        ]
    )

    assert code == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "failed"
    assert payload["threshold_failures"][0]["threshold"] == "scanner_ready"
    assert payload["threshold_failures"][0]["blocked_count"] == 10

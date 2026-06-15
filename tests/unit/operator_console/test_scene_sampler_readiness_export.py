from __future__ import annotations

import json

from scripts.operator_console.export_scene_sampler_readiness import export_readiness_artifacts, main


def test_scene_sampler_readiness_export_writes_artifacts(tmp_path) -> None:
    result = export_readiness_artifacts(output_dir=tmp_path)

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    artifacts = result["artifacts"]
    assert set(artifacts) == {
        "candidate_readiness",
        "manifest",
        "eval_projection",
        "readiness_report",
        "selection_gaps",
        "source_availability",
    }
    manifest = json.loads((tmp_path / "scene_sampler_manifest.json").read_text())
    projection = json.loads((tmp_path / "scene_sampler_eval_projection.json").read_text())
    readiness = json.loads((tmp_path / "scene_sampler_readiness_report.json").read_text())
    availability = json.loads(
        (tmp_path / "scene_sampler_source_availability.json").read_text()
    )
    candidates = json.loads((tmp_path / "scene_sampler_candidate_readiness.json").read_text())
    selection = json.loads((tmp_path / "scene_sampler_selection_gaps.json").read_text())
    assert manifest["ui_target_per_scene_source"] == 3
    assert manifest["eval_target_per_scene_source"] == 10
    assert projection["scene_sources"]["procthor-10k-val"]["ready_count"] == 5
    assert readiness["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert readiness["sources"]["ithor"]["blocked_rows"][0]["failure_class"] == (
        "environment_blocked"
    )
    assert availability["schema"] == "molmospaces_scene_source_availability_report_v1"
    assert availability["probe_mode"] == "no_download_no_vlm"
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


def test_scene_sampler_readiness_export_selection_capacity_passes_when_candidates_exist(
    tmp_path,
) -> None:
    result = export_readiness_artifacts(
        output_dir=tmp_path,
        required_selection_capacity_sources=("ithor",),
    )

    assert result["status"] == "success"
    assert result["threshold_failures"] == []


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

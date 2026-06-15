from __future__ import annotations

import json

from scripts.operator_console.export_scene_sampler_readiness import export_readiness_artifacts, main


def test_scene_sampler_readiness_export_writes_artifacts(tmp_path) -> None:
    result = export_readiness_artifacts(output_dir=tmp_path)

    assert result["status"] == "success"
    assert result["threshold_failures"] == []
    artifacts = result["artifacts"]
    assert set(artifacts) == {"manifest", "eval_projection", "readiness_report"}
    manifest = json.loads((tmp_path / "scene_sampler_manifest.json").read_text())
    projection = json.loads((tmp_path / "scene_sampler_eval_projection.json").read_text())
    readiness = json.loads((tmp_path / "scene_sampler_readiness_report.json").read_text())
    assert manifest["ui_target_per_scene_source"] == 3
    assert manifest["eval_target_per_scene_source"] == 10
    assert projection["scene_sources"]["procthor-10k-val"]["ready_count"] == 5
    assert readiness["sources"]["procthor-10k-val"]["ui_ready_count"] == 3
    assert readiness["sources"]["ithor"]["blocked_rows"][0]["failure_class"] == (
        "environment_blocked"
    )


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

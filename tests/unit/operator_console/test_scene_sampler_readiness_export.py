from __future__ import annotations

import json

from scripts.operator_console.export_scene_sampler_readiness import export_readiness_artifacts


def test_scene_sampler_readiness_export_writes_artifacts(tmp_path) -> None:
    result = export_readiness_artifacts(output_dir=tmp_path)

    assert result["status"] == "success"
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

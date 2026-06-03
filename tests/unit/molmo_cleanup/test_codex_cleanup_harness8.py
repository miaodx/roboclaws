from __future__ import annotations

import json
from pathlib import Path

from scripts.molmo_cleanup import run_codex_cleanup_harness8 as harness8


def test_build_harness_has_expected_rows(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )

    assert harness["schema"] == "codex_cleanup_harness8_v1"
    assert [row["row_id"] for row in harness["setup_rows"]] == [
        "setup-semantic-map-prior-dino"
    ]
    assert [row["row_id"] for row in harness["rows"]] == [
        "direct-world-labels",
        "direct-world-labels-sanitized",
        "direct-camera-labels-grounding-dino",
        "direct-camera-raw",
        "dino-prior-world-labels",
        "dino-prior-world-labels-sanitized",
        "dino-prior-camera-labels-grounding-dino",
        "dino-prior-camera-raw",
    ]
    prior_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "dino-prior"]
    assert len(prior_rows) == 4
    assert all(row["requires_runtime_map_prior"] for row in prior_rows)


def test_replace_runtime_map_prior_updates_prior_rows_only(tmp_path: Path) -> None:
    harness = harness8.build_harness(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        runtime_map_prior="",
        visual_grounding_timeout_s="auto",
    )

    harness8._replace_runtime_map_prior(harness, "output/prior/runtime_metric_map.json")

    direct_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "direct"]
    prior_rows = [row for row in harness["rows"] if row["axes"]["map_mode"] == "dino-prior"]
    assert all(
        "runtime_map_prior=" not in " ".join(row["command"]) for row in direct_rows
    )
    assert all(
        "runtime_map_prior=output/prior/runtime_metric_map.json" in row["command"]
        for row in prior_rows
    )


def test_setup_row_refresh_treats_runtime_map_as_artifact_success(tmp_path: Path) -> None:
    run_dir = tmp_path / "_semantic-map-prior-dino" / "0603_2209" / "seed-7"
    run_dir.mkdir(parents=True)
    (run_dir / "runtime_metric_map.json").write_text(
        json.dumps({"public_semantic_anchors": [{"id": "anchor_fixture_001"}]}),
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html></html>", encoding="utf-8")
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "completion_status": "failed",
                "score": {"status": "failed", "restored_count": 0, "total_targets": 10},
                "runtime_metric_map": {"public_semantic_anchors": [{"id": "anchor_fixture_001"}]},
                "sweep_coverage_rate": 1.0,
                "disturbance_count": 0,
                "visual_grounding_pipeline_id": "grounding-dino",
            }
        ),
        encoding="utf-8",
    )

    row = harness8._semantic_map_prior_row(
        output_dir=tmp_path,
        seed=7,
        generated_mess_count=10,
        task="cleanup",
        map_bundle="bundle",
        visual_grounding_timeout_s="auto",
    )
    harness8._refresh_row_from_evidence(row, status=0, run_dir=run_dir)

    assert row["status"] == "artifact_success"
    assert row["behavior_status"] == "artifact_success"
    assert row["metrics"]["runtime_semantic_anchor_count"] == 1
    assert "exact_restored" not in row["metrics"]

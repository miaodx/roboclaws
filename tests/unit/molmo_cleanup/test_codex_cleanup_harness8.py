from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path

from pytest import MonkeyPatch

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


def test_rate_limit_evidence_detects_provider_429_log(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    (run_dir / "driver.log").write_text(
        '{"type":"error","message":"exceeded retry limit, last status: 429 Too Many Requests"}',
        encoding="utf-8",
    )

    evidence = harness8._rate_limit_evidence({"run_dir": str(run_dir)})

    assert evidence is not None
    assert evidence["pattern"] == "429 too many requests"
    assert evidence["source"] == "driver.log"


def test_execute_row_with_retries_marks_exhausted_rate_limit(
    tmp_path: Path, monkeypatch: MonkeyPatch
) -> None:
    row = {"row_id": "dino-prior-world-labels", "run_dir": str(tmp_path)}

    def fake_execute_row(row_arg, _args):
        row_arg["run_dir"] = str(tmp_path)
        row_arg["status"] = "failed"
        row_arg["behavior_status"] = "failed"
        row_arg["reason"] = "command exited with status 1"
        return 1

    monkeypatch.setattr(harness8, "_execute_row", fake_execute_row)
    monkeypatch.setattr(
        harness8,
        "_rate_limit_evidence",
        lambda _row: {
            "source": "driver.log",
            "pattern": "429 too many requests",
            "snippet": "429 Too Many Requests",
        },
    )

    status = harness8._execute_row_with_retries(
        row,
        Namespace(rate_limit_retries=1, rate_limit_retry_sleep_s=0),
    )

    assert status == 1
    assert row["status"] == "rate_limited"
    assert row["behavior_status"] == "infra_failure"
    assert row["retry_count"] == 1
    assert len(row["attempts"]) == 2

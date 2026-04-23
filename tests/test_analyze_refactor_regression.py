from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from analyze_refactor_regression import analyze_capture_sets, write_summary  # noqa: E402


def _row(
    *,
    suite: str,
    backend: str = "vlm",
    scene: str = "FloorPlan201",
    seed: int = 1,
    game: str = "explore",
    model: str = "mock",
    agents: int = 1,
    variant: str | None = None,
    status: str = "ok",
    artifact_dir: str = "output/run",
    **extra,
):
    row = {
        "suite": suite,
        "backend": backend,
        "scene": scene,
        "seed": seed,
        "game": game,
        "model": model,
        "agents": agents,
        "variant": variant,
        "label": "baseline-2026-04-23",
        "status": status,
        "artifact_dir": artifact_dir,
        "run_id": "run-1",
        "captured_at": "2026-04-23T00:00:00+00:00",
        "commit_sha": "abc123",
        "schema_version": 1,
    }
    row.update(extra)
    return row


def test_successful_pairing_passes_and_writes_outputs(tmp_path: Path) -> None:
    summary = analyze_capture_sets(
        baseline_rows=[
            _row(
                suite="explore-vlm",
                cells_visited=10,
                usd=1.0,
                wallclock_seconds=10.0,
            )
        ],
        candidate_rows=[
            _row(
                suite="explore-vlm",
                cells_visited=9,
                usd=1.2,
                wallclock_seconds=14.0,
                artifact_dir="output/candidate",
            )
        ],
    )

    assert summary["passed"] is True
    assert summary["comparisons"][0]["status"] == "pass"

    outputs = write_summary(summary=summary, output_dir=tmp_path / "analysis")
    assert Path(outputs["summary_md"]).exists()
    assert Path(outputs["summary_json"]).exists()


def test_explore_vlm_uses_absolute_slack_for_small_real_runs() -> None:
    summary = analyze_capture_sets(
        baseline_rows=[
            _row(
                suite="explore-vlm",
                cells_visited=3,
                usd=0.009459,
                wallclock_seconds=78.27,
            )
        ],
        candidate_rows=[
            _row(
                suite="explore-vlm",
                cells_visited=2,
                usd=0.016323,
                wallclock_seconds=197.62,
                artifact_dir="output/candidate",
            )
        ],
    )

    assert summary["passed"] is True


def test_missing_candidate_row_fails() -> None:
    summary = analyze_capture_sets(
        baseline_rows=[
            _row(
                suite="explore-vlm",
                cells_visited=10,
                usd=1.0,
                wallclock_seconds=10.0,
            )
        ],
        candidate_rows=[],
    )

    assert summary["passed"] is False
    assert summary["missing_pairs"][0]["missing"] == "candidate"


def test_threshold_breach_is_reported() -> None:
    summary = analyze_capture_sets(
        baseline_rows=[
            _row(
                suite="coverage-vlm",
                game="coverage",
                agents=2,
                variant="map-v2+chase",
                coverage_fraction=0.90,
                work_balance=0.95,
                total_steps=20,
            )
        ],
        candidate_rows=[
            _row(
                suite="coverage-vlm",
                game="coverage",
                agents=2,
                variant="map-v2+chase",
                coverage_fraction=0.80,
                work_balance=0.95,
                total_steps=20,
                artifact_dir="output/candidate",
            )
        ],
    )

    assert summary["passed"] is False
    checks = summary["comparisons"][0]["checks"]
    failing_metrics = {check["metric"] for check in checks if not check["passed"]}
    assert "coverage_fraction" in failing_metrics


def test_openclaw_autonomous_requires_exact_transcript_source() -> None:
    summary = analyze_capture_sets(
        baseline_rows=[
            _row(
                suite="openclaw-autonomous",
                backend="openclaw",
                game="autonomous-navigation",
                transcript_source="stream",
                tool_calls_by_type={"observe": 3, "move": 2, "done": 1},
                frames_unseen_by_agent=1,
            )
        ],
        candidate_rows=[
            _row(
                suite="openclaw-autonomous",
                backend="openclaw",
                game="autonomous-navigation",
                transcript_source="terminal-body",
                tool_calls_by_type={"observe": 3, "move": 3, "done": 1},
                frames_unseen_by_agent=2,
                artifact_dir="output/candidate",
            )
        ],
    )

    assert summary["passed"] is False
    checks = summary["comparisons"][0]["checks"]
    transcript_check = next(check for check in checks if check["metric"] == "transcript_source")
    assert transcript_check["passed"] is False

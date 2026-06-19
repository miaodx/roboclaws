from __future__ import annotations

from pathlib import Path

from roboclaws.evals.reports import render_eval_report


def test_eval_report_links_existing_artifacts_under_output_dir(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval"
    run_dir = output_dir / "runs" / "sample" / "trial-0000"
    run_dir.mkdir(parents=True)
    (run_dir / "run_result.json").write_text("{}\n", encoding="utf-8")
    (run_dir / "report.html").write_text("<html></html>\n", encoding="utf-8")

    html = render_eval_report(
        _bundle(
            output_dir=output_dir,
            artifacts={
                "run_result": str(run_dir / "run_result.json"),
                "report": str(run_dir / "report.html"),
            },
        )
    )

    assert 'href="runs/sample/trial-0000/run_result.json"' in html
    assert 'href="runs/sample/trial-0000/report.html"' in html
    assert "unavailable" not in html


def test_eval_report_marks_missing_or_escaping_artifacts_unavailable(tmp_path: Path) -> None:
    output_dir = tmp_path / "eval"
    output_dir.mkdir()
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    (outside_dir / "report.html").write_text("<html></html>\n", encoding="utf-8")

    html = render_eval_report(
        _bundle(
            output_dir=output_dir,
            artifacts={
                "run_result": "runs/sample/trial-0000/run_result.json",
                "report": "../outside/report.html",
            },
        )
    )

    assert 'href="runs/sample/trial-0000/run_result.json"' not in html
    assert 'href="../outside/report.html"' not in html
    assert (
        "run_result unavailable (missing artifact: runs/sample/trial-0000/run_result.json)" in html
    )
    assert "report unavailable (outside eval output: ../outside/report.html)" in html


def _bundle(*, output_dir: Path, artifacts: dict[str, str]) -> dict[str, object]:
    return {
        "suite": {"suite_id": "household_world.report_links"},
        "aggregate": {
            "pass_at_1": 1.0,
            "passed": 1,
            "total": 1,
        },
        "results": [
            {
                "identity": {
                    "sample_id": "sample",
                    "trial_id": "trial-0000",
                    "agent_engine": "direct-runner",
                    "provider_profile": "not_applicable",
                },
                "artifacts": artifacts,
                "status": "passed",
                "failure_class": "not_applicable",
                "metrics": {},
                "grader_outputs": {},
            }
        ],
        "artifacts": {"output_dir": str(output_dir)},
    }

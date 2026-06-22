from __future__ import annotations

from pathlib import Path

import pytest

from roboclaws.evals.models import EvalResult, EvalSuite
from roboclaws.evals.reports import render_eval_report, results_bundle


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


def test_results_bundle_rejects_invalid_sampler_projection_counts(tmp_path: Path) -> None:
    suite = _suite_with_sampler_projection(
        source_payload={
            "support_status": "partial",
            "status": "partial_or_blocked",
            "target_count": "10",
            "ready_count": 5,
            "needed_count": 5,
            "blocked_count": 0,
            "rejected_count": 0,
            "sample_ids": ["scene.sample_1"],
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "eval suite sampler_projection scene source 'procthor-10k-val' "
            "target_count must be a non-negative integer"
        ),
    ):
        results_bundle(
            suite=suite,
            results=[_result()],
            output_dir=tmp_path,
            budget="smoke",
        )


def test_results_bundle_rejects_invalid_sampler_projection_sample_ids(tmp_path: Path) -> None:
    suite = _suite_with_sampler_projection(
        source_payload={
            "support_status": "partial",
            "status": "partial_or_blocked",
            "target_count": 10,
            "ready_count": 5,
            "needed_count": 5,
            "blocked_count": 0,
            "rejected_count": 0,
            "sample_ids": "scene.sample_1",
        }
    )

    with pytest.raises(
        ValueError,
        match=(
            "eval suite sampler_projection scene source 'procthor-10k-val' "
            "sample_ids must be a list of strings"
        ),
    ):
        results_bundle(
            suite=suite,
            results=[_result()],
            output_dir=tmp_path,
            budget="smoke",
        )


def test_results_bundle_rejects_invalid_sampler_projection_summary(tmp_path: Path) -> None:
    suite = _suite_with_sampler_projection(
        source_payload={
            "support_status": "partial",
            "status": "partial_or_blocked",
            "target_count": 10,
            "ready_count": 5,
            "needed_count": 5,
            "blocked_count": 0,
            "rejected_count": 0,
            "sample_ids": ["scene.sample_1"],
        },
        summary_overrides={"remaining_sample_count": "5"},
    )

    with pytest.raises(
        ValueError,
        match="eval suite sampler_projection.summary remaining_sample_count "
        "must be a non-negative integer",
    ):
        results_bundle(
            suite=suite,
            results=[_result()],
            output_dir=tmp_path,
            budget="smoke",
        )


def test_eval_report_rejects_invalid_sampler_projection_summary(tmp_path: Path) -> None:
    bundle = _bundle(output_dir=tmp_path, artifacts={})
    bundle["aggregate"]["sampler_projection"] = _sampler_projection()
    bundle["aggregate"]["sampler_projection"]["summary"]["ready_sample_count"] = False

    with pytest.raises(
        ValueError,
        match="eval report sampler_projection.summary ready_sample_count "
        "must be a non-negative integer",
    ):
        render_eval_report(bundle)


def test_eval_report_rejects_invalid_sampler_projection_source_row(tmp_path: Path) -> None:
    bundle = _bundle(output_dir=tmp_path, artifacts={})
    bundle["aggregate"]["sampler_projection"] = _sampler_projection()
    bundle["aggregate"]["sampler_projection"]["scene_sources"]["procthor-10k-val"] = []

    with pytest.raises(
        ValueError,
        match="eval report sampler_projection scene source 'procthor-10k-val' must be an object",
    ):
        render_eval_report(bundle)


def test_eval_report_rejects_invalid_sampler_projection_sample_ids(tmp_path: Path) -> None:
    bundle = _bundle(output_dir=tmp_path, artifacts={})
    bundle["aggregate"]["sampler_projection"] = _sampler_projection()
    bundle["aggregate"]["sampler_projection"]["scene_sources"]["procthor-10k-val"]["sample_ids"] = (
        "scene.sample_1"
    )

    with pytest.raises(
        ValueError,
        match=(
            "eval report sampler_projection scene source 'procthor-10k-val' "
            "sample_ids must be a list of strings"
        ),
    ):
        render_eval_report(bundle)


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


def _suite_with_sampler_projection(
    *,
    source_payload: dict[str, object],
    summary_overrides: dict[str, object] | None = None,
) -> EvalSuite:
    summary = _sampler_projection_summary()
    summary.update(summary_overrides or {})
    return EvalSuite.from_mapping(
        {
            "schema": "roboclaws_eval_suite_v1",
            "suite_id": "household_world.scene_sampler_projection",
            "version": "2026-06-20",
            "capability": "household_world",
            "sample_ids": ["scene.sample_1"],
            "required_graders": ["sampler_admission"],
            "thresholds": {"pass_at_1": 1.0},
            "metadata": {
                "sampler_projection": {
                    "schema": "molmospaces_scene_sampler_projection_v1",
                    "projection": "camera-grounded-labels",
                    "generator_version": "unit",
                    "scene_sources": {"procthor-10k-val": source_payload},
                    "summary": summary,
                }
            },
        }
    )


def _sampler_projection() -> dict[str, object]:
    return {
        "schema": "molmospaces_scene_sampler_projection_v1",
        "projection": "camera-grounded-labels",
        "generator_version": "unit",
        "summary": _sampler_projection_summary(),
        "scene_sources": {
            "procthor-10k-val": {
                "support_status": "partial",
                "status": "partial_or_blocked",
                "target_count": 10,
                "ready_count": 5,
                "needed_count": 5,
                "blocked_count": 0,
                "rejected_count": 0,
                "sample_ids": ["scene.sample_1"],
            }
        },
    }


def _sampler_projection_summary() -> dict[str, object]:
    return {
        "source_count": 1,
        "target_sample_count": 10,
        "ready_sample_count": 5,
        "partial_source_count": 1,
        "rejected_source_count": 0,
        "blocked_source_count": 0,
        "complete_source_count": 0,
        "blocked_row_count": 0,
        "rejected_row_count": 0,
        "blocked_or_rejected_row_count": 0,
        "remaining_sample_count": 5,
    }


def _result() -> EvalResult:
    return EvalResult.from_mapping(
        {
            "schema": "roboclaws_eval_result_v1",
            "identity": {
                "suite_id": "household_world.scene_sampler_projection",
                "suite_version": "2026-06-20",
                "sample_id": "scene.sample_1",
                "sample_version": "2026-06-20",
                "trial_id": "trial-0000",
                "repetition_index": 0,
                "surface": "household-world",
                "intent": "map-build",
                "preset": "map-build",
                "world": "molmospaces/val_0",
                "backend": "mujoco",
                "evidence_lane": "camera-grounded-labels",
                "camera_labeler": "grounding-dino",
                "scenario_setup": "baseline",
                "seed": 7,
                "prompt": "not_applicable",
                "goal_contract_hash": "unit",
                "agent_engine": "direct-runner",
                "runner_class": "direct",
                "provider_profile": "not_applicable",
                "model": "not_applicable",
                "skill_name": "not_applicable",
                "prompt_source": "not_applicable",
                "mcp_profile": "household_world",
                "tool_surface": ["observe"],
                "budgets": {},
                "runtime": {},
            },
            "status": "passed",
            "failure_class": "not_applicable",
            "grader_outputs": {},
            "artifacts": {},
            "metrics": {},
        }
    )

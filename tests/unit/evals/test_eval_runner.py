from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.evals.runner import run_eval_suite


def test_eval_runner_writes_result_bundle_and_report(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="unit",
        product_runner=_passing_product_runner,
    )

    assert run.results_path.exists()
    assert run.report_path.exists()
    payload = json.loads(run.results_path.read_text())
    assert payload["schema"] == "roboclaws_eval_results_bundle_v1"
    assert payload["suite"]["suite_id"] == "household_world.smoke_regression"
    assert payload["aggregate"]["total"] == 1
    assert payload["aggregate"]["passed"] == 1
    assert payload["aggregate"]["pass_at_1"] == 1.0

    result = payload["results"][0]
    assert result["status"] == "passed"
    assert result["failure_class"] == "not_applicable"
    assert result["grader_outputs"]["outcome"]["completion_status"] == "success"
    assert result["identity"]["agent_engine"] == "direct-runner"
    assert result["identity"]["provider_profile"] == "not_applicable"
    assert result["artifacts"]["run_result"].endswith("run_result.json")
    assert result["artifacts"]["report"].endswith("report.html")
    report_html = run.report_path.read_text()
    assert "run_result" in report_html
    assert 'href="runs/cleanup_smoke_seed7/trial-0000/run_result.json"' in report_html


def test_eval_runner_classifies_missing_product_artifacts(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="artifact-failure",
        product_runner=_missing_artifact_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["status"] == "failed"
    assert result["failure_class"] == "artifact_missing"
    assert payload["aggregate"]["failure_classes"] == {"artifact_missing": 1}
    assert "report" in result["grader_outputs"]["artifacts"]["missing"]


def test_eval_runner_classifies_environment_blocked_exception(tmp_path: Path) -> None:
    run = run_eval_suite(
        "smoke_regression",
        output_root=tmp_path,
        stamp="blocked",
        product_runner=_blocked_product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["status"] == "blocked"
    assert result["failure_class"] == "environment_blocked"
    assert result["grader_outputs"]["runner"]["error_type"] == "ModuleNotFoundError"


def test_map_build_consumer_suite_passes_runtime_map_prior_between_samples(
    tmp_path: Path,
) -> None:
    seen_runtime_priors: list[str] = []

    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        if "runtime_map_prior_path" in kwargs:
            seen_runtime_priors.append(str(kwargs["runtime_map_prior_path"]))
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
            )
        if sample_id == "open_ended.drink_seed7":
            _write_product_artifacts(
                run_dir,
                completion_status="failed",
                include_goal_contract=True,
            )
            return _run_result(
                run_dir,
                completion_status="failed",
                task_intent="open-ended",
                final_status="success",
                include_completion_claim=True,
            )
        _write_product_artifacts(run_dir, completion_status="success")
        return _run_result(run_dir, completion_status="success")

    run = run_eval_suite(
        "map_build_consumer",
        output_root=tmp_path,
        stamp="map-consumer",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    assert payload["aggregate"]["passed"] == 3
    assert payload["aggregate"]["failed"] == 0
    assert len(seen_runtime_priors) == 1
    assert seen_runtime_priors[0].endswith(
        "runs/map_build_baseline_seed7/trial-0000/runtime_metric_map.json"
    )
    results = {result["identity"]["sample_id"]: result for result in payload["results"]}
    map_result = results["map_build.baseline_seed7"]
    assert map_result["grader_outputs"]["outcome"]["runtime_metric_map_schema"] == (
        "runtime_metric_map_v1"
    )
    assert map_result["grader_outputs"]["outcome"]["public_semantic_anchor_count"] == 1
    open_result = results["open_ended.drink_seed7"]
    assert open_result["status"] == "passed"
    assert open_result["grader_outputs"]["outcome"]["completion_claim_present"] is True
    assert open_result["grader_outputs"]["outcome"]["artifact_readiness"] == "ready"
    assert (
        open_result["grader_outputs"]["open_ended"]["semantic_satisfaction_authoritative"] is False
    )


def test_map_build_eval_catches_unusable_runtime_metric_map(tmp_path: Path) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
        (run_dir / "runtime_metric_map.json").write_text('{"schema": "wrong"}\n')
        return _run_result(run_dir, completion_status="semantic_sweep_complete")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="bad-map",
        product_runner=product_runner,
    )

    payload = json.loads(run.results_path.read_text())
    result = payload["results"][0]
    assert result["identity"]["sample_id"] == "map_build.baseline_seed7"
    assert result["status"] == "failed"
    assert result["failure_class"] == "map_actionability_failure"
    assert result["grader_outputs"]["outcome"]["schema_ok"] is False


def test_cleanup_consumer_fails_when_runtime_map_dependency_is_missing(tmp_path: Path) -> None:
    launched_samples: list[str] = []

    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        launched_samples.append(sample_id)
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            (run_dir / "runtime_metric_map.json").unlink()
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
                include_runtime_map=False,
            )
        if sample_id == "open_ended.drink_seed7":
            _write_product_artifacts(
                run_dir,
                completion_status="failed",
                include_goal_contract=True,
            )
            return _run_result(
                run_dir,
                completion_status="failed",
                task_intent="open-ended",
                final_status="success",
                include_completion_claim=True,
            )
        raise AssertionError("cleanup consumer should not launch without runtime_map_prior_path")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="missing-map-prior",
        product_runner=product_runner,
    )

    results = json.loads(run.results_path.read_text())["results"]
    cleanup_result = next(
        result
        for result in results
        if result["identity"]["sample_id"] == "cleanup.consume_map_seed7"
    )
    assert launched_samples == ["map_build.baseline_seed7", "open_ended.drink_seed7"]
    assert cleanup_result["status"] == "failed"
    assert cleanup_result["failure_class"] == "artifact_missing"
    assert cleanup_result["grader_outputs"]["runner"]["error_type"] == "EvalDependencyError"
    assert cleanup_result["grader_outputs"]["artifacts"]["missing_dependencies"] == [
        "runtime_map_prior_path"
    ]


def test_open_ended_eval_separates_claim_from_artifact_readiness(tmp_path: Path) -> None:
    def product_runner(**kwargs: Any) -> dict[str, Any]:
        run_dir = Path(kwargs["output_dir"])
        sample_id = kwargs["run_metadata_overrides"]["eval_sample_id"]
        if sample_id == "map_build.baseline_seed7":
            _write_product_artifacts(run_dir, completion_status="semantic_sweep_complete")
            return _run_result(
                run_dir,
                completion_status="semantic_sweep_complete",
                semantic_sweep=True,
            )
        if sample_id == "cleanup.consume_map_seed7":
            _write_product_artifacts(run_dir, completion_status="success")
            return _run_result(run_dir, completion_status="success")
        _write_product_artifacts(run_dir, completion_status="failed")
        return _run_result(run_dir, completion_status="failed", task_intent="open-ended")

    run = run_eval_suite(
        "evals/household_world/suites/map_build_consumer.json",
        output_root=tmp_path,
        stamp="open-ended-missing-claim",
        product_runner=product_runner,
    )

    results = json.loads(run.results_path.read_text())["results"]
    open_result = next(
        result for result in results if result["identity"]["sample_id"] == "open_ended.drink_seed7"
    )
    assert open_result["status"] == "failed"
    assert open_result["failure_class"] == "agent_no_completion_claim"
    assert open_result["grader_outputs"]["open_ended"]["completion_claim_present"] is False
    assert open_result["grader_outputs"]["open_ended"]["artifact_readiness"] == "missing"


def _passing_product_runner(**kwargs: Any) -> dict[str, Any]:
    run_dir = Path(kwargs["output_dir"])
    _write_product_artifacts(run_dir, completion_status="success")
    return _run_result(run_dir, completion_status="success")


def _missing_artifact_product_runner(**kwargs: Any) -> dict[str, Any]:
    run_dir = Path(kwargs["output_dir"])
    _write_product_artifacts(run_dir, completion_status="success")
    (run_dir / "report.html").unlink()
    return _run_result(run_dir, completion_status="success")


def _blocked_product_runner(**kwargs: Any) -> dict[str, Any]:
    raise ModuleNotFoundError("No module named 'molmospaces'")


def _write_product_artifacts(
    run_dir: Path,
    *,
    completion_status: str,
    include_goal_contract: bool = False,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_result.json").write_text("{}\n")
    (run_dir / "report.html").write_text("<html>report</html>\n")
    (run_dir / "agent_view.json").write_text("{}\n")
    (run_dir / "runtime_metric_map.json").write_text(
        json.dumps(
            {
                "schema": "runtime_metric_map_v1",
                "public_semantic_anchors": [{"anchor_id": "anchor_fridge"}],
                "generated_exploration_candidates": [{"waypoint_id": "generated_exploration_001"}],
                "private_truth_included": False,
                "source_map_mutated": False,
            }
        )
        + "\n"
    )
    (run_dir / "private_evaluation.json").write_text("{}\n")
    (run_dir / "advisory_evaluation.json").write_text('{"authoritative": false}\n')
    if include_goal_contract:
        (run_dir / "goal_contract.json").write_text('{"intent": "open-ended"}\n')
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            [
                '{"event": "response", "tool": "metric_map"}',
                '{"event": "response", "tool": "done"}',
            ]
        )
        + "\n"
    )


def _run_result(
    run_dir: Path,
    *,
    completion_status: str,
    semantic_sweep: bool = False,
    task_intent: str = "cleanup",
    final_status: str | None = None,
    include_completion_claim: bool = False,
    include_runtime_map: bool = True,
) -> dict[str, Any]:
    completion_claim = (
        {
            "schema": "roboclaws_agent_completion_claim_v1",
            "completion_summary": "direct runner declared task complete",
        }
        if include_completion_claim
        else {}
    )
    return {
        "score": {
            "completion_status": completion_status,
            "mess_restoration_rate": 1.0,
            "disturbance_count": 0,
            "failed_or_noop_tool_count": 0,
        },
        "completion_status": completion_status,
        "cleanup_status": completion_status,
        "task_intent": task_intent,
        "final_status": final_status or completion_status,
        "semantic_sweep_mode": semantic_sweep,
        "agent_completion_claim": completion_claim,
        "tool_event_counts": {"metric_map:response": 1, "done:response": 1},
        "artifacts": {
            "run_result": str(run_dir / "run_result.json"),
            "report": str(run_dir / "report.html"),
        },
        "runtime_metric_map": (
            json.loads((run_dir / "runtime_metric_map.json").read_text())
            if include_runtime_map and (run_dir / "runtime_metric_map.json").exists()
            else {}
        ),
        "advisory_evaluation": json.loads((run_dir / "advisory_evaluation.json").read_text()),
        "policy_uses_private_truth": False,
        "planner_uses_private_manifest": False,
        "agent_view": {},
    }

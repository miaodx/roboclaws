"""Repo-native deterministic eval suite runner."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from roboclaws.evals.agent_identity import (
    agent_engine_spec,
    blocked_result_from_live_agent_request,
    eval_provider_profile,
    validate_sample_agent,
)
from roboclaws.evals.dependencies import (
    dependency_failure,
    resolve_artifact_dependencies,
    sample_artifact_key,
)
from roboclaws.evals.live_runtime import (
    LiveTrialHooks,
    product_run_kwargs,
    run_live_eval_trial,
    run_live_surface_product,
)
from roboclaws.evals.models import (
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalSuite,
    EvalTrial,
    load_eval_sample,
    load_eval_suite,
)
from roboclaws.evals.reports import render_eval_report, results_bundle
from roboclaws.household.backend_contract import SYNTHETIC_BACKEND
from roboclaws.household.realworld_cleanup import run_realworld_cleanup

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "output" / "evals"

ProductRun = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class EvalSuiteRun:
    """Paths and result bundle for one eval suite execution."""

    suite: EvalSuite
    output_dir: Path
    results_path: Path
    report_path: Path
    bundle: dict[str, Any]


def run_eval_suite(
    suite_ref: str,
    *,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    budget: str = "smoke",
    stamp: str | None = None,
    agent_engine: str = "direct-runner",
    provider_profile: str | None = None,
    model: str | None = None,
    live_execution: str = "blocked",
    live_timeout_s: float | None = None,
    product_runner: ProductRun = run_realworld_cleanup,
    live_product_runner: ProductRun | None = None,
) -> EvalSuiteRun:
    """Run a repo-native deterministic eval suite."""

    if live_execution not in {"blocked", "run"}:
        raise ValueError("live_execution must be blocked or run")

    suite_path = resolve_suite_path(suite_ref)
    suite = load_eval_suite(suite_path)
    samples = _load_suite_samples(suite)
    engine = agent_engine_spec(agent_engine)
    selected_provider_profile = eval_provider_profile(
        agent_engine=engine.id,
        provider_profile=provider_profile,
    )
    run_stamp = stamp or time.strftime("%Y%m%dT%H%M%S")
    output_dir = output_root / _path_token(suite.suite_id) / run_stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[EvalResult] = []
    sample_artifacts: dict[str, dict[str, Any]] = {}
    for sample in samples:
        validate_sample_agent(sample, agent_engine=engine.id)
        for repetition_index in range(sample.trial_count):
            trial = _trial_from_sample(
                suite=suite,
                sample=sample,
                repetition_index=repetition_index,
                budget=budget,
                agent_engine=engine.id,
                runner_class=engine.internal_runner_class,
                provider_profile=selected_provider_profile,
                model=model,
            )
            sample_run_dir = output_dir / "runs" / _path_token(sample.sample_id)
            run_dir = sample_run_dir / f"trial-{repetition_index:04d}"
            result = _run_trial(
                suite=suite,
                sample=sample,
                trial=trial,
                run_dir=run_dir,
                budget=budget,
                repetition_index=repetition_index,
                sample_artifacts=sample_artifacts,
                agent_engine=engine.id,
                provider_profile=selected_provider_profile,
                model=model,
                live_execution=live_execution,
                live_timeout_s=live_timeout_s,
                product_runner=product_runner,
                live_product_runner=live_product_runner,
            )
            results.append(result)
            sample_artifacts[sample_artifact_key(sample.sample_id, repetition_index)] = (
                result.artifacts or _artifact_paths(run_dir)
            )
            if repetition_index == 0:
                sample_artifacts[sample.sample_id] = result.artifacts or _artifact_paths(run_dir)

    bundle = results_bundle(suite=suite, results=results, output_dir=output_dir, budget=budget)
    results_path = output_dir / "eval_results.json"
    report_path = output_dir / "eval_report.html"
    _write_json(results_path, bundle)
    report_path.write_text(render_eval_report(bundle), encoding="utf-8")
    bundle["artifacts"]["eval_results"] = str(results_path)
    bundle["artifacts"]["eval_report"] = str(report_path)
    _write_json(results_path, bundle)
    return EvalSuiteRun(
        suite=suite,
        output_dir=output_dir,
        results_path=results_path,
        report_path=report_path,
        bundle=bundle,
    )


def resolve_suite_path(suite_ref: str) -> Path:
    """Resolve a suite id, short name, or JSON path to a suite file."""

    raw = str(suite_ref or "").strip()
    if not raw:
        raw = "smoke_regression"
    candidate = Path(raw)
    if candidate.suffix == ".json":
        path = candidate if candidate.is_absolute() else REPO_ROOT / candidate
        if path.exists():
            return path
    short = raw.removeprefix("household_world.")
    path = REPO_ROOT / "evals" / "household_world" / "suites" / f"{short}.json"
    if path.exists():
        return path
    raise ValueError(f"unknown eval suite {suite_ref!r}")


def _load_suite_samples(suite: EvalSuite) -> list[EvalSample]:
    if not suite.sample_refs:
        raise ValueError(f"eval suite {suite.suite_id!r} has no sample_refs")
    samples = [load_eval_sample(REPO_ROOT / ref) for ref in suite.sample_refs]
    loaded_ids = tuple(sample.sample_id for sample in samples)
    if loaded_ids != suite.sample_ids:
        raise ValueError(
            f"eval suite {suite.suite_id!r} sample_refs resolve to {loaded_ids}, "
            f"expected {suite.sample_ids}"
        )
    return samples


def _trial_from_sample(
    *,
    suite: EvalSuite,
    sample: EvalSample,
    repetition_index: int,
    budget: str,
    agent_engine: str,
    runner_class: str,
    provider_profile: str,
    model: str | None,
) -> EvalTrial:
    limitations: list[str] = []
    if (
        budget == "smoke"
        and sample.backend != SYNTHETIC_BACKEND
        and agent_engine == "direct-runner"
    ):
        limitations.append("smoke_budget_uses_synthetic_backend_for_local_determinism")
    return EvalTrial.from_sample(
        sample,
        suite=suite,
        trial_id=f"{_path_token(sample.sample_id)}-{repetition_index:04d}",
        repetition_index=repetition_index,
        agent_engine=agent_engine,
        runner_class=runner_class,
        provider_profile=provider_profile,
        model=model or MISSING_NOT_APPLICABLE,
        skill_name=_skill_name(sample),
        prompt_source=MISSING_NOT_APPLICABLE
        if sample.prompt == MISSING_NOT_APPLICABLE
        else "sample",
        mcp_profile=_mcp_profile(sample),
        tool_surface=_tool_surface(sample),
        budgets={
            "steps": _budget_steps(budget),
            "time_s": MISSING_UNAVAILABLE,
            "token": MISSING_NOT_APPLICABLE,
            "cost": MISSING_NOT_APPLICABLE,
        },
        runtime={
            "host": MISSING_UNAVAILABLE,
            "hardware": "local_cpu",
            "network": MISSING_NOT_APPLICABLE,
            "local_live_limitations": [],
        },
        limitations=limitations,
    )


def _run_trial(
    *,
    suite: EvalSuite,
    sample: EvalSample,
    trial: EvalTrial,
    run_dir: Path,
    budget: str,
    repetition_index: int,
    sample_artifacts: dict[str, dict[str, Any]],
    agent_engine: str,
    provider_profile: str,
    model: str | None,
    live_execution: str,
    live_timeout_s: float | None,
    product_runner: ProductRun,
    live_product_runner: ProductRun | None,
) -> EvalResult:
    run_dir.mkdir(parents=True, exist_ok=True)
    if agent_engine != "direct-runner":
        if live_execution == "run":
            return run_live_eval_trial(
                sample=sample,
                trial=trial,
                run_dir=run_dir,
                budget=budget,
                repetition_index=repetition_index,
                sample_artifacts=sample_artifacts,
                agent_engine=agent_engine,
                provider_profile=provider_profile,
                model=model,
                live_timeout_s=live_timeout_s,
                live_product_runner=live_product_runner or run_live_surface_product,
                hooks=LiveTrialHooks(
                    failed_result_from_dependency=_failed_result_from_dependency,
                    blocked_result_from_exception=_blocked_result_from_exception,
                    grade_trial=_grade_trial,
                    status_from_graders=_status_from_graders,
                    artifact_paths=_artifact_paths,
                    metrics_from_graders=_metrics_from_graders,
                ),
            )
        return blocked_result_from_live_agent_request(
            trial,
            agent_engine=agent_engine,
            run_dir=run_dir,
        )
    dependency_artifacts = resolve_artifact_dependencies(
        sample,
        repetition_index=repetition_index,
        sample_artifacts=sample_artifacts,
    )
    failure = dependency_failure(dependency_artifacts)
    if failure is not None:
        return _failed_result_from_dependency(trial, run_dir, failure)
    try:
        run_result = product_runner(
            **product_run_kwargs(
                sample,
                run_dir=run_dir,
                budget=budget,
                dependency_artifacts=dependency_artifacts,
            )
        )
    except Exception as exc:  # noqa: BLE001 - eval packets must classify runner failures.
        return _blocked_result_from_exception(trial, exc)

    grader_outputs = _grade_trial(
        sample=sample,
        run_dir=run_dir,
        run_result=run_result,
        dependency_artifacts=dependency_artifacts,
    )
    status, failure_class = _status_from_graders(grader_outputs)
    artifacts = _artifact_paths(run_dir)
    metrics = _metrics_from_graders(grader_outputs, status=status, run_result=run_result)
    return EvalResult.from_trial(
        trial,
        status=status,
        failure_class=failure_class,
        grader_outputs=grader_outputs,
        artifacts=artifacts,
        artifact_schema_versions={key: MISSING_UNAVAILABLE for key in artifacts},
        metrics=metrics,
        limitations=trial.limitations,
    )


def _grade_trial(
    *,
    sample: EvalSample,
    run_dir: Path,
    run_result: dict[str, Any],
    dependency_artifacts: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifacts": _artifact_grader(run_dir, dependency_artifacts=dependency_artifacts),
        "privacy": _privacy_grader(run_result),
        "trajectory": _trajectory_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "outcome": _outcome_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "sampler_admission": _sampler_admission_grader(sample=sample),
        "open_ended": _open_ended_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "efficiency": _efficiency_grader(run_dir=run_dir, run_result=run_result),
    }


def _artifact_grader(
    run_dir: Path,
    *,
    dependency_artifacts: dict[str, Any] | None,
) -> dict[str, Any]:
    required = {
        "run_result": run_dir / "run_result.json",
        "report": run_dir / "report.html",
        "trace": run_dir / "trace.jsonl",
        "agent_view": run_dir / "agent_view.json",
        "runtime_metric_map": run_dir / "runtime_metric_map.json",
        "private_evaluation": run_dir / "private_evaluation.json",
    }
    missing = [name for name, path in required.items() if not path.exists()]
    return {
        "status": "failed" if missing else "passed",
        "missing": missing,
        "resolved_dependencies": dict(dependency_artifacts or {}),
        "required": {name: str(path) for name, path in required.items()},
    }


def _privacy_grader(run_result: dict[str, Any]) -> dict[str, Any]:
    leaked = []
    if run_result.get("policy_uses_private_truth") is True:
        leaked.append("policy_uses_private_truth")
    if run_result.get("planner_uses_private_manifest") is True:
        leaked.append("planner_uses_private_manifest")
    agent_view = (
        run_result.get("agent_view") if isinstance(run_result.get("agent_view"), dict) else {}
    )
    for key in ("private_manifest", "acceptable_destinations", "hidden_target_list"):
        if key in agent_view:
            leaked.append(f"agent_view.{key}")
    return {
        "status": "failed" if leaked else "passed",
        "private_truth_leak_count": len(leaked),
        "leaked_fields": leaked,
    }


def _trajectory_grader(
    *,
    sample: EvalSample,
    run_dir: Path,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    trace_events = _read_trace_events(run_dir / "trace.jsonl")
    response_tools = {
        str(event.get("tool"))
        for event in trace_events
        if event.get("event") == "response" and event.get("tool")
    }
    required_groups = (
        {"done"},
        {"metric_map", "resolve_target_query"} if sample.intent == "open-ended" else {"metric_map"},
    )
    missing_tools = sorted(
        ",".join(sorted(group))
        for group in required_groups
        if not response_tools.intersection(group)
    )
    fixture_hints_count = sum(1 for event in trace_events if event.get("tool") == "fixture_hints")
    violations = list(missing_tools)
    failed_or_noop_count = _int_value(
        run_result.get("score", {}).get("failed_or_noop_tool_count")
        if isinstance(run_result.get("score"), dict)
        else None
    )
    if failed_or_noop_count > 0:
        violations.append("failed_or_noop_tool")
    return {
        "status": "failed" if violations else "passed",
        "missing_required_tools": missing_tools,
        "violation_count": len(violations),
        "violations": violations,
        "fixture_hints_trace_count": fixture_hints_count,
        "fixture_hints_policy": (
            "direct_runner_internal_compatibility"
            if sample.allowed_agent_engines == ("direct-runner",)
            else "trajectory_violation_for_live_mcp"
        ),
    }


def _outcome_grader(
    *,
    sample: EvalSample,
    run_dir: Path,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    if sample.intent == "map-build":
        runtime_map_path = run_dir / "runtime_metric_map.json"
        runtime_map = _load_json(runtime_map_path) if runtime_map_path.exists() else {}
        config = sample.grader_config or {}
        schema_ok = runtime_map.get("schema") == str(
            config.get("require_runtime_metric_map_schema") or "runtime_metric_map_v1"
        )
        anchors = runtime_map.get("public_semantic_anchors") or []
        exploration = runtime_map.get("generated_exploration_candidates") or []
        private_truth_absent = runtime_map.get("private_truth_included") is False
        source_map_not_mutated = runtime_map.get("source_map_mutated") is False
        passed = (
            runtime_map_path.exists()
            and schema_ok
            and len(anchors) >= _int_value(config.get("min_public_semantic_anchors") or 0)
            and len(exploration)
            >= _int_value(config.get("min_generated_exploration_candidates") or 0)
            and (private_truth_absent if config.get("require_private_truth_absent", True) else True)
            and (
                source_map_not_mutated
                if config.get("require_source_map_not_mutated", True)
                else True
            )
        )
        return {
            "status": "passed" if passed else "failed",
            "failure_class": "map_actionability_failure" if not passed else MISSING_NOT_APPLICABLE,
            "runtime_metric_map_exists": runtime_map_path.exists(),
            "runtime_metric_map_schema": runtime_map.get("schema", MISSING_UNAVAILABLE),
            "schema_ok": schema_ok,
            "public_semantic_anchor_count": len(anchors),
            "generated_exploration_candidate_count": len(exploration),
            "private_truth_absent": private_truth_absent,
            "source_map_not_mutated": source_map_not_mutated,
        }
    if sample.intent == "open-ended":
        open_ended = _open_ended_grader(sample=sample, run_dir=run_dir, run_result=run_result)
        return {
            "status": open_ended["status"],
            "completion_claim_present": open_ended["completion_claim_present"],
            "artifact_readiness": open_ended["artifact_readiness"],
            "semantic_satisfaction_status": open_ended["semantic_satisfaction_status"],
            "open_ended_category": open_ended["open_ended_category"],
            "expected_goal_outcome": open_ended["expected_goal_outcome"],
            "success_predicate": open_ended["success_predicate"],
        }
    score = run_result.get("score") if isinstance(run_result.get("score"), dict) else {}
    completion_status = str(
        score.get("completion_status")
        or run_result.get("completion_status")
        or run_result.get("cleanup_status")
        or ""
    )
    passed = completion_status in {"passed", "success", "complete", "completed"}
    return {
        "status": "passed" if passed else "failed",
        "completion_status": completion_status,
        "mess_restoration_rate": score.get("mess_restoration_rate", MISSING_UNAVAILABLE),
        "disturbance_count": score.get("disturbance_count", MISSING_UNAVAILABLE),
    }


def _sampler_admission_grader(*, sample: EvalSample) -> dict[str, Any]:
    config = sample.grader_config or {}
    admission = config.get("sampler_admission")
    if not isinstance(admission, dict):
        return {"status": "not_applicable"}
    room_count = _int_value(admission.get("room_count"))
    waypoint_count = _int_value(admission.get("waypoint_count"))
    category_provenance = str(admission.get("category_provenance") or "")
    forbidden_provenance = {
        "heuristic_room_label",
        "heuristic_room_count",
        "room_area_fallback",
    }
    failures: list[str] = []
    if room_count < 3:
        failures.append("fewer_than_three_public_rooms")
    if waypoint_count < room_count:
        failures.append("missing_room_waypoints")
    if category_provenance in forbidden_provenance or category_provenance not in {
        "source_metadata",
        "prepared_visual_label_manifest",
    }:
        failures.append("untrusted_room_category_provenance")
    return {
        "status": "failed" if failures else "passed",
        "failure_class": "map_actionability_failure" if failures else MISSING_NOT_APPLICABLE,
        "failures": failures,
        "scene_family": str(admission.get("scene_family") or ""),
        "scene_split": str(admission.get("scene_split") or ""),
        "scene_source": str(admission.get("scene_source") or ""),
        "scene_index": admission.get("scene_index", MISSING_UNAVAILABLE),
        "room_count": room_count,
        "waypoint_count": waypoint_count,
        "category_provenance": category_provenance,
        "category_manifest": str(admission.get("category_manifest") or ""),
        "generator_version": str(admission.get("generator_version") or ""),
    }


def _efficiency_grader(*, run_dir: Path, run_result: dict[str, Any]) -> dict[str, Any]:
    tool_counts = (
        run_result.get("tool_event_counts")
        if isinstance(run_result.get("tool_event_counts"), dict)
        else {}
    )
    live_status = _merged_live_status(run_dir=run_dir, run_result=run_result)
    live_timing = _load_json(run_dir / "live_timing.json")
    timing_payload = dict(run_result)
    if live_timing:
        timing_payload["live_timing"] = live_timing
        timing_payload["runner_wall_time_s"] = _live_wall_time_s(live_timing)
    model_attempt_summary = _model_attempt_summary(timing_payload)
    return {
        "status": "passed",
        "tool_event_count": sum(_int_value(value) for value in tool_counts.values()),
        "tool_call_count": sum(
            _int_value(value)
            for key, value in tool_counts.items()
            if str(key).endswith(":request")
        ),
        "tool_event_counts": dict(tool_counts),
        "wall_time_s": _first_available_number(
            timing_payload,
            (
                "wall_time_s",
                "elapsed_s",
                "duration_s",
                "runner_wall_time_s",
                "total_elapsed_s",
            ),
        ),
        "live_status": {
            "phase": str(live_status.get("phase") or MISSING_UNAVAILABLE),
            "exit_status": live_status.get("exit_status", MISSING_UNAVAILABLE),
            "reason": str(live_status.get("reason") or MISSING_UNAVAILABLE),
            "provider_reason": str(live_status.get("provider_reason") or MISSING_UNAVAILABLE),
            "retryable": live_status.get("retryable", MISSING_UNAVAILABLE),
        },
        "model_attempt_summary": model_attempt_summary,
    }


def _open_ended_grader(
    *,
    sample: EvalSample,
    run_dir: Path,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    if sample.intent != "open-ended":
        return {
            "status": "not_applicable",
            "completion_claim_present": MISSING_NOT_APPLICABLE,
            "artifact_readiness": MISSING_NOT_APPLICABLE,
            "semantic_satisfaction_status": "advisory_not_applicable",
        }
    claim = run_result.get("agent_completion_claim")
    claim_present = isinstance(claim, dict) and bool(claim.get("completion_summary"))
    required = ("run_result.json", "report.html", "trace.jsonl", "goal_contract.json")
    missing = [name for name in required if not (run_dir / name).exists()]
    artifact_ready = not missing
    advisory = (
        run_result.get("advisory_evaluation")
        if isinstance(run_result.get("advisory_evaluation"), dict)
        else _load_json(run_dir / "advisory_evaluation.json")
    )
    advisory_available = bool(advisory)
    semantic_status = "advisory_available" if advisory_available else "advisory_unavailable"
    config = sample.grader_config or {}
    predicate_config = config.get("success_predicate")
    predicate = _open_ended_success_predicate(
        predicate_config if isinstance(predicate_config, dict) else {},
        run_dir=run_dir,
    )
    hard_passed = claim_present and artifact_ready
    if predicate["authoritative"]:
        hard_passed = hard_passed and predicate["passed"]
    return {
        "status": "passed" if hard_passed else "failed",
        "failure_class": (
            MISSING_NOT_APPLICABLE
            if hard_passed
            else (
                "private_goal_not_satisfied"
                if claim_present and artifact_ready and predicate["authoritative"]
                else "agent_no_completion_claim"
            )
        ),
        "open_ended_category": str(config.get("open_ended_category") or MISSING_UNAVAILABLE),
        "expected_goal_outcome": str(config.get("expected_goal_outcome") or MISSING_UNAVAILABLE),
        "completion_claim_present": claim_present,
        "artifact_readiness": "ready" if artifact_ready else "missing",
        "missing_artifacts": missing,
        "semantic_satisfaction_status": semantic_status,
        "semantic_satisfaction_authoritative": bool(
            config.get("semantic_satisfaction_authoritative") is True
        ),
        "success_predicate": predicate,
    }


def _open_ended_success_predicate(
    config: dict[str, Any],
    *,
    run_dir: Path,
) -> dict[str, Any]:
    predicate_id = str(config.get("predicate_id") or "completion_claim")
    authoritative = bool(config.get("authoritative") is True)
    runtime_map = _load_json(run_dir / "runtime_metric_map.json")
    trace_events = _read_trace_events(run_dir / "trace.jsonl")
    if predicate_id == "completion_claim":
        return {
            "predicate_id": predicate_id,
            "authoritative": authoritative,
            "passed": True,
            "evidence": {},
        }
    if predicate_id == "public_anchor_observed":
        return _public_anchor_observed_predicate(
            config,
            runtime_map=runtime_map,
            trace_events=trace_events,
            authoritative=authoritative,
        )
    if predicate_id == "waypoint_or_area_visited":
        return _waypoint_or_area_visited_predicate(
            config,
            runtime_map=runtime_map,
            trace_events=trace_events,
            authoritative=authoritative,
        )
    if predicate_id == "observed_category_present":
        return _observed_category_present_predicate(
            config,
            runtime_map=runtime_map,
            authoritative=authoritative,
        )
    return {
        "predicate_id": predicate_id,
        "authoritative": authoritative,
        "passed": False,
        "failure": "unknown_open_ended_success_predicate",
        "evidence": {},
    }


def _public_anchor_observed_predicate(
    config: dict[str, Any],
    *,
    runtime_map: dict[str, Any],
    trace_events: list[dict[str, Any]],
    authoritative: bool,
) -> dict[str, Any]:
    anchor_id = str(config.get("anchor_id") or "")
    room_id = str(config.get("room_id") or "")
    anchors = [
        anchor
        for anchor in _list_of_mappings(runtime_map.get("public_semantic_anchors"))
        if (not anchor_id or str(anchor.get("anchor_id") or "") == anchor_id)
        and (not room_id or str(anchor.get("room_id") or "") == room_id)
    ]
    observed_rooms = _observed_room_ids(runtime_map=runtime_map, trace_events=trace_events)
    passed = bool(anchors) and (not room_id or room_id in observed_rooms)
    return {
        "predicate_id": "public_anchor_observed",
        "authoritative": authoritative,
        "passed": passed,
        "failure": "" if passed else "required_public_anchor_not_observed",
        "evidence": {
            "anchor_id": anchor_id,
            "room_id": room_id,
            "matching_anchor_count": len(anchors),
            "observed_room_ids": sorted(observed_rooms),
        },
    }


def _waypoint_or_area_visited_predicate(
    config: dict[str, Any],
    *,
    runtime_map: dict[str, Any],
    trace_events: list[dict[str, Any]],
    authoritative: bool,
) -> dict[str, Any]:
    waypoint_id = str(config.get("waypoint_id") or "")
    room_id = str(config.get("room_id") or "")
    anchor_id = str(config.get("anchor_id") or "")
    visited_waypoints = _visited_waypoint_ids(runtime_map=runtime_map, trace_events=trace_events)
    observed_rooms = _observed_room_ids(runtime_map=runtime_map, trace_events=trace_events)
    anchors = _list_of_mappings(runtime_map.get("public_semantic_anchors"))
    anchor_present = any(
        (not anchor_id or str(anchor.get("anchor_id") or "") == anchor_id)
        and (not waypoint_id or str(anchor.get("waypoint_id") or "") == waypoint_id)
        and (not room_id or str(anchor.get("room_id") or "") == room_id)
        for anchor in anchors
    )
    waypoint_visited = not waypoint_id or waypoint_id in visited_waypoints
    passed = waypoint_visited and (not room_id or room_id in observed_rooms) and (
        not anchor_id or anchor_present or waypoint_visited
    )
    return {
        "predicate_id": "waypoint_or_area_visited",
        "authoritative": authoritative,
        "passed": passed,
        "failure": "" if passed else "required_waypoint_or_area_not_visited",
        "evidence": {
            "anchor_id": anchor_id,
            "waypoint_id": waypoint_id,
            "room_id": room_id,
            "anchor_present": anchor_present,
            "visited_waypoint_ids": sorted(visited_waypoints),
            "observed_room_ids": sorted(observed_rooms),
        },
    }


def _observed_category_present_predicate(
    config: dict[str, Any],
    *,
    runtime_map: dict[str, Any],
    authoritative: bool,
) -> dict[str, Any]:
    category = str(config.get("category") or "").lower()
    observed = _list_of_mappings(runtime_map.get("observed_objects"))
    matching = [
        item
        for item in observed
        if not category
        or category
        in {
            str(item.get("category") or "").lower(),
            str(item.get("label") or "").lower(),
            str(item.get("query") or "").lower(),
        }
    ]
    passed = bool(matching)
    return {
        "predicate_id": "observed_category_present",
        "authoritative": authoritative,
        "passed": passed,
        "failure": "" if passed else "required_observed_category_missing",
        "evidence": {
            "category": category,
            "matching_observed_count": len(matching),
        },
    }


def _visited_waypoint_ids(
    *,
    runtime_map: dict[str, Any],
    trace_events: list[dict[str, Any]],
) -> set[str]:
    visited: set[str] = set()
    summary = runtime_map.get("target_search_summary")
    if isinstance(summary, dict):
        viewpoint_budget = summary.get("viewpoint_budget")
        if isinstance(viewpoint_budget, dict):
            visited.update(
                str(item) for item in viewpoint_budget.get("observed_waypoint_ids") or []
            )
        for observation in _list_of_mappings(summary.get("inspection_observations")):
            waypoint_id = str(observation.get("waypoint_id") or "")
            if waypoint_id:
                visited.add(waypoint_id)
    for candidate in _list_of_mappings(runtime_map.get("generated_exploration_candidates")):
        if candidate.get("visited") is True and candidate.get("waypoint_id"):
            visited.add(str(candidate["waypoint_id"]))
    for event in trace_events:
        if event.get("tool") == "navigate_to_waypoint" and event.get("event") == "request":
            request = event.get("request") if isinstance(event.get("request"), dict) else {}
            waypoint_id = str(request.get("waypoint_id") or "")
            if waypoint_id:
                visited.add(waypoint_id)
    return visited


def _observed_room_ids(
    *,
    runtime_map: dict[str, Any],
    trace_events: list[dict[str, Any]],
) -> set[str]:
    rooms: set[str] = set()
    summary = runtime_map.get("target_search_summary")
    if isinstance(summary, dict):
        for observation in _list_of_mappings(summary.get("inspection_observations")):
            room_id = str(observation.get("room_id") or "")
            if room_id:
                rooms.add(room_id)
    waypoint_rooms = {
        str(candidate.get("waypoint_id") or ""): str(candidate.get("room_id") or "")
        for candidate in _list_of_mappings(runtime_map.get("generated_exploration_candidates"))
    }
    for waypoint_id in _visited_waypoint_ids(runtime_map=runtime_map, trace_events=trace_events):
        room_id = waypoint_rooms.get(waypoint_id, "")
        if room_id:
            rooms.add(room_id)
    return rooms


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _model_attempt_summary(run_result: dict[str, Any]) -> dict[str, Any]:
    for key in ("model_attempt_summary", "model_service_summary", "live_timing"):
        value = run_result.get(key)
        if isinstance(value, dict):
            return _compact_model_attempt_summary(value)
    return {
        "attempt_count": MISSING_UNAVAILABLE,
        "success_count": MISSING_UNAVAILABLE,
        "failure_count": MISSING_UNAVAILABLE,
        "provider_reasons": {},
    }


def _compact_model_attempt_summary(value: dict[str, Any]) -> dict[str, Any]:
    live_summary = _model_attempt_summary_from_live_timing(value)
    if live_summary:
        return live_summary
    attempts = _int_or_missing(
        value.get("attempt_count")
        or value.get("model_service_attempt_count")
        or value.get("total_attempts")
    )
    successes = _int_or_missing(
        value.get("success_count")
        or value.get("model_service_success_count")
        or value.get("successful_attempts")
    )
    failures = _int_or_missing(
        value.get("failure_count")
        or value.get("model_service_failure_count")
        or value.get("failed_attempts")
    )
    provider_reasons = value.get("provider_reasons")
    if not isinstance(provider_reasons, dict):
        provider_reasons = {}
    return {
        "attempt_count": attempts,
        "success_count": successes,
        "failure_count": failures,
        "provider_reasons": dict(provider_reasons),
    }


def _model_attempt_summary_from_live_timing(value: dict[str, Any]) -> dict[str, Any]:
    fallback = _nested_mapping(
        value,
        "timeline",
        "latency_attribution",
        "model_service_fallback_metrics",
    )
    attempts_list = value.get("openai_agents_attempts")
    if not isinstance(attempts_list, list):
        attempts_list = []
    if fallback:
        attempt_count = _int_or_missing(
            fallback.get("attempt_event_count")
            or fallback.get("attempt_count")
            or len(attempts_list)
        )
        success_count = _int_or_missing(
            fallback.get("success_event_count")
            or fallback.get("success_count")
            or _live_attempt_status_count(attempts_list, "finished")
        )
        failure_count = _int_or_missing(
            fallback.get("failure_event_count")
            or fallback.get("failure_count")
            or _live_attempt_failure_count(attempts_list)
        )
        provider_reasons = fallback.get("provider_reasons")
        if not isinstance(provider_reasons, dict):
            provider_reasons = {}
        return {
            "attempt_count": attempt_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "provider_reasons": dict(provider_reasons),
        }
    if attempts_list:
        return {
            "attempt_count": len(attempts_list),
            "success_count": _live_attempt_status_count(attempts_list, "finished"),
            "failure_count": _live_attempt_failure_count(attempts_list),
            "provider_reasons": _live_provider_reasons(attempts_list),
        }
    return {}


def _merged_live_status(*, run_dir: Path, run_result: dict[str, Any]) -> dict[str, Any]:
    live_status = (
        run_result.get("live_status") if isinstance(run_result.get("live_status"), dict) else {}
    )
    sidecar = _load_json(run_dir / "live_status.json")
    return {**sidecar, **live_status}


def _live_wall_time_s(live_timing: dict[str, Any]) -> Any:
    runner_timing = _nested_mapping(live_timing, "runner_timing")
    for payload in (
        runner_timing,
        _nested_mapping(live_timing, "timeline"),
        live_timing,
    ):
        value = _first_available_number(
            payload,
            ("total_elapsed_s", "accounted_elapsed_s", "runner_wall_time_s"),
        )
        if value != MISSING_UNAVAILABLE:
            return value
    return MISSING_UNAVAILABLE


def _nested_mapping(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    current: Any = payload
    for key in keys:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return current if isinstance(current, dict) else {}


def _live_attempt_status_count(attempts: list[Any], phase: str) -> int:
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, dict)
        and (
            str(attempt.get("phase") or "") == phase
            or (phase == "finished" and attempt.get("exit_status") == 0)
        )
    )


def _live_attempt_failure_count(attempts: list[Any]) -> int:
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, dict)
        and (
            attempt.get("exit_status") not in {None, 0}
            or str(attempt.get("phase") or "") == "failed"
        )
    )


def _live_provider_reasons(attempts: list[Any]) -> dict[str, int]:
    reasons: dict[str, int] = {}
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        reason = str(attempt.get("provider_reason") or attempt.get("reason") or "").strip()
        if reason:
            reasons[reason] = reasons.get(reason, 0) + 1
    return reasons


def _first_available_number(payload: dict[str, Any], keys: tuple[str, ...]) -> float | str:
    for key in keys:
        value = payload.get(key)
        try:
            return round(float(value), 3)
        except (TypeError, ValueError):
            continue
    return MISSING_UNAVAILABLE


def _int_or_missing(value: Any) -> int | str:
    if value is None:
        return MISSING_UNAVAILABLE
    try:
        return int(value)
    except (TypeError, ValueError):
        return MISSING_UNAVAILABLE


def _status_from_graders(grader_outputs: dict[str, Any]) -> tuple[str, str]:
    ordered_failures = (
        ("artifacts", "artifact_missing"),
        ("privacy", "private_truth_leak"),
        ("trajectory", "trajectory_policy_violation"),
        ("sampler_admission", "map_actionability_failure"),
        ("open_ended", "agent_no_completion_claim"),
        ("outcome", "private_goal_not_satisfied"),
    )
    for grader_name, failure_class in ordered_failures:
        grader = grader_outputs.get(grader_name, {})
        if grader.get("status") == "failed":
            return "failed", str(grader.get("failure_class") or failure_class)
    return "passed", MISSING_NOT_APPLICABLE


def _metrics_from_graders(
    grader_outputs: dict[str, Any],
    *,
    status: str,
    run_result: dict[str, Any],
) -> dict[str, Any]:
    score = run_result.get("score") if isinstance(run_result.get("score"), dict) else {}
    return {
        "pass": 1.0 if status == "passed" else 0.0,
        "private_truth_leak_count": grader_outputs["privacy"]["private_truth_leak_count"],
        "trajectory_policy_violation_count": grader_outputs["trajectory"]["violation_count"],
        "mess_restoration_rate": score.get("mess_restoration_rate", MISSING_UNAVAILABLE),
        "open_ended_artifact_readiness": grader_outputs["open_ended"].get(
            "artifact_readiness",
            MISSING_NOT_APPLICABLE,
        ),
        "tool_event_count": grader_outputs["efficiency"]["tool_event_count"],
        "tool_call_count": grader_outputs["efficiency"].get("tool_call_count", 0),
        "tool_event_counts": grader_outputs["efficiency"].get("tool_event_counts", {}),
        "wall_time_s": grader_outputs["efficiency"].get("wall_time_s", MISSING_UNAVAILABLE),
        "model_attempt_summary": grader_outputs["efficiency"].get(
            "model_attempt_summary",
            {},
        ),
    }


def _blocked_result_from_exception(trial: EvalTrial, exc: Exception) -> EvalResult:
    failure_class = _failure_class_from_exception(exc)
    blocked = failure_class in {"environment_blocked", "model_or_provider_unavailable"}
    return EvalResult.from_trial(
        trial,
        status="blocked" if blocked else "failed",
        failure_class=failure_class,
        grader_outputs={
            "runner": {
                "status": "blocked" if blocked else "failed",
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        },
        artifacts={},
        metrics={"pass": 0.0},
        limitations=(*trial.limitations, "product_run_failed_before_grading"),
    )


def _failure_class_from_exception(exc: Exception) -> str:
    if isinstance(exc, (ImportError, ModuleNotFoundError, TimeoutError)):
        return "environment_blocked"
    message = str(exc).lower()
    environment_tokens = ("no module named", "not installed", "unavailable", "timed out")
    if "another interactive codex molmo cleanup session appears to be active" in message:
        return "environment_blocked"
    if any(token in message for token in environment_tokens):
        return "environment_blocked"
    provider_tokens = (
        "provider_transient_failure",
        "provider_config_failure",
        "provider_context_failure",
        "model_service",
        "error code: 5",
        "error code: 429",
        "bad_response_status_code",
        "openai_error",
        "rate_limit",
    )
    if any(token in message for token in provider_tokens):
        return "model_or_provider_unavailable"
    return "harness_bug_unclassified"


def _failed_result_from_dependency(
    trial: EvalTrial,
    run_dir: Path,
    dependency_failure: dict[str, Any],
) -> EvalResult:
    failure_class = str(dependency_failure.get("failure_class") or "artifact_missing")
    artifacts = _artifact_paths(run_dir)
    return EvalResult.from_trial(
        trial,
        status="failed",
        failure_class=failure_class,
        grader_outputs={
            "artifacts": {
                "status": "failed",
                "missing": [],
                "missing_dependencies": dependency_failure.get("missing_dependencies", []),
                "resolved_dependencies": dependency_failure.get("resolved_dependencies", {}),
                "required": {},
            },
            "runner": {
                "status": "failed",
                "error_type": "EvalDependencyError",
                "message": str(dependency_failure.get("message") or ""),
            },
        },
        artifacts=artifacts,
        artifact_schema_versions={key: MISSING_UNAVAILABLE for key in artifacts},
        metrics={"pass": 0.0},
        limitations=(*trial.limitations, "eval_dependency_missing_before_product_run"),
    )


def _artifact_paths(run_dir: Path) -> dict[str, Any]:
    paths = {
        "run_dir": run_dir,
        "run_result": run_dir / "run_result.json",
        "report": run_dir / "report.html",
        "trace": run_dir / "trace.jsonl",
        "agent_view": run_dir / "agent_view.json",
        "runtime_metric_map": run_dir / "runtime_metric_map.json",
        "private_evaluation": run_dir / "private_evaluation.json",
    }
    return {key: str(path) for key, path in paths.items()}


def _read_trace_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            events.append(payload)
    return events


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _skill_name(sample: EvalSample) -> str:
    if sample.intent == "cleanup":
        return "molmo-realworld-cleanup"
    return "household-open-task"


def _mcp_profile(sample: EvalSample) -> str:
    if sample.intent == "cleanup":
        return "household_world+household_manipulation"
    return "household_world+household_episode"


def _tool_surface(sample: EvalSample) -> tuple[str, ...]:
    if sample.intent == "cleanup":
        return ("metric_map", "observe", "navigate", "pick", "place", "done")
    return ("metric_map", "observe", "done")


def _budget_steps(budget: str) -> int | str:
    if budget == "smoke":
        return 50
    if budget == "focused":
        return 100
    return MISSING_UNAVAILABLE


def _path_token(value: str) -> str:
    return str(value).replace("/", "_").replace(".", "_")


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    from roboclaws.evals.cli import main as cli_main

    return cli_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())

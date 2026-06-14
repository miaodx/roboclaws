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
from roboclaws.evals.models import (
    MISSING_NOT_APPLICABLE,
    MISSING_SENTINELS,
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
from roboclaws.launch.backends import BACKEND_SPECS
from roboclaws.launch.catalog import SURFACE_SPECS
from roboclaws.launch.goals import normalize_goal_contract
from roboclaws.launch.intents import TASK_INTENT_SPECS

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
    product_runner: ProductRun = run_realworld_cleanup,
) -> EvalSuiteRun:
    """Run a repo-native deterministic eval suite."""

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
                product_runner=product_runner,
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
    product_runner: ProductRun,
) -> EvalResult:
    run_dir.mkdir(parents=True, exist_ok=True)
    if agent_engine != "direct-runner":
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
            **_product_run_kwargs(
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


def _product_run_kwargs(
    sample: EvalSample,
    *,
    run_dir: Path,
    budget: str,
    dependency_artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    launch_overrides = sample.launch_overrides or {}
    semantic_sweep = sample.intent == "map-build" or sample.preset == "map-build"
    kwargs: dict[str, Any] = {
        "output_dir": run_dir,
        "seed": sample.seed,
        "task_prompt": _task_prompt(sample),
        "backend": _implementation_backend(sample, budget=budget),
        "cleanup_profile": _cleanup_profile(sample, budget=budget),
        "semantic_sweep": semantic_sweep,
        "generated_mess_count": _generated_mess_count(sample),
        "scene_source": str(launch_overrides.get("scene_source") or "procthor-10k-val"),
        "scene_index": int(launch_overrides.get("scene_index") or 0),
        "run_metadata_overrides": {
            "eval_sample_id": sample.sample_id,
            "eval_sample_version": sample.version,
            "eval_suite_runner": "roboclaws.evals.runner",
        },
    }
    goal_contract = _goal_contract_json(sample)
    if goal_contract:
        kwargs["goal_contract_json"] = goal_contract
    runtime_map_prior = str((dependency_artifacts or {}).get("runtime_map_prior_path") or "")
    if runtime_map_prior:
        kwargs["runtime_map_prior_path"] = runtime_map_prior
    return kwargs


def _implementation_backend(sample: EvalSample, *, budget: str) -> str:
    if budget == "smoke":
        return SYNTHETIC_BACKEND
    backend = BACKEND_SPECS.get(sample.backend)
    if backend is None:
        return sample.backend
    return backend.implementation_backend


def _cleanup_profile(sample: EvalSample, *, budget: str) -> str:
    if budget == "smoke":
        return "smoke"
    return sample.evidence_lane


def _task_prompt(sample: EvalSample) -> str:
    if sample.prompt not in {"", MISSING_NOT_APPLICABLE, MISSING_UNAVAILABLE}:
        return sample.prompt
    if sample.intent == "map-build":
        return "帮我建立这个房间的语义地图"
    return "帮我收拾这个房间"


def _generated_mess_count(sample: EvalSample) -> int:
    reference = sample.private_goal_reference
    if isinstance(reference.get("generated_mess_count"), int):
        return int(reference["generated_mess_count"])
    launch_overrides = sample.launch_overrides or {}
    for key in ("generated_mess_count", "relocation_count"):
        value = launch_overrides.get(key)
        if value is not None:
            return int(value)
    if sample.intent == "map-build":
        return 0
    return 10


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
        "open_ended": _open_ended_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "efficiency": _efficiency_grader(run_result),
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
    required_tools = {"metric_map", "done"}
    missing_tools = sorted(required_tools - response_tools)
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
            "status": "passed",
            "completion_claim_present": open_ended["completion_claim_present"],
            "artifact_readiness": open_ended["artifact_readiness"],
            "semantic_satisfaction_status": open_ended["semantic_satisfaction_status"],
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


def _efficiency_grader(run_result: dict[str, Any]) -> dict[str, Any]:
    tool_counts = (
        run_result.get("tool_event_counts")
        if isinstance(run_result.get("tool_event_counts"), dict)
        else {}
    )
    return {
        "status": "passed",
        "tool_event_count": sum(_int_value(value) for value in tool_counts.values()),
        "tool_event_counts": dict(tool_counts),
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
    return {
        "status": "passed" if claim_present and artifact_ready else "failed",
        "completion_claim_present": claim_present,
        "artifact_readiness": "ready" if artifact_ready else "missing",
        "missing_artifacts": missing,
        "semantic_satisfaction_status": semantic_status,
        "semantic_satisfaction_authoritative": False,
    }


def _status_from_graders(grader_outputs: dict[str, Any]) -> tuple[str, str]:
    ordered_failures = (
        ("artifacts", "artifact_missing"),
        ("privacy", "private_truth_leak"),
        ("trajectory", "trajectory_policy_violation"),
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
    }


def _blocked_result_from_exception(trial: EvalTrial, exc: Exception) -> EvalResult:
    failure_class = _failure_class_from_exception(exc)
    return EvalResult.from_trial(
        trial,
        status="blocked" if failure_class == "environment_blocked" else "failed",
        failure_class=failure_class,
        grader_outputs={
            "runner": {
                "status": "blocked" if failure_class == "environment_blocked" else "failed",
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
    if any(token in message for token in environment_tokens):
        return "environment_blocked"
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
        return "household_world_v1+household_manipulation_v1"
    return "household_world_v1+household_episode_v1"


def _goal_contract_json(sample: EvalSample) -> str:
    if sample.intent not in TASK_INTENT_SPECS:
        return ""
    surface = SURFACE_SPECS.get(sample.surface)
    if surface is None:
        return ""
    return normalize_goal_contract(
        surface=surface,
        intent=TASK_INTENT_SPECS[sample.intent],
        raw_prompt="" if sample.prompt in MISSING_SENTINELS else sample.prompt,
    ).to_json()


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

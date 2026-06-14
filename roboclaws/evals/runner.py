"""Repo-native deterministic eval suite runner."""

from __future__ import annotations

import argparse
import html
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from roboclaws.evals.models import (
    EVAL_RESULT_SCHEMA,
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalSuite,
    EvalTrial,
    load_eval_sample,
    load_eval_suite,
)
from roboclaws.household.backend_contract import SYNTHETIC_BACKEND
from roboclaws.household.realworld_cleanup import run_realworld_cleanup
from roboclaws.launch.backends import BACKEND_SPECS

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "output" / "evals"
RESULTS_BUNDLE_SCHEMA = "roboclaws_eval_results_bundle_v1"

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
    product_runner: ProductRun = run_realworld_cleanup,
) -> EvalSuiteRun:
    """Run a repo-native deterministic eval suite."""

    suite_path = resolve_suite_path(suite_ref)
    suite = load_eval_suite(suite_path)
    samples = _load_suite_samples(suite)
    run_stamp = stamp or time.strftime("%Y%m%dT%H%M%S")
    output_dir = output_root / _path_token(suite.suite_id) / run_stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[EvalResult] = []
    for sample in samples:
        if "direct-runner" not in sample.allowed_agent_engines:
            raise ValueError(
                f"sample {sample.sample_id!r} does not allow the deterministic direct-runner"
            )
        for repetition_index in range(sample.trial_count):
            trial = _trial_from_sample(
                suite=suite,
                sample=sample,
                repetition_index=repetition_index,
                budget=budget,
            )
            sample_run_dir = output_dir / "runs" / _path_token(sample.sample_id)
            run_dir = sample_run_dir / f"trial-{repetition_index:04d}"
            results.append(
                _run_trial(
                    suite=suite,
                    sample=sample,
                    trial=trial,
                    run_dir=run_dir,
                    budget=budget,
                    product_runner=product_runner,
                )
            )

    bundle = _results_bundle(suite=suite, results=results, output_dir=output_dir, budget=budget)
    results_path = output_dir / "eval_results.json"
    report_path = output_dir / "eval_report.html"
    _write_json(results_path, bundle)
    report_path.write_text(_render_eval_report(bundle), encoding="utf-8")
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
) -> EvalTrial:
    limitations: list[str] = []
    if budget == "smoke" and sample.backend != SYNTHETIC_BACKEND:
        limitations.append("smoke_budget_uses_synthetic_backend_for_local_determinism")
    return EvalTrial.from_sample(
        sample,
        suite=suite,
        trial_id=f"{_path_token(sample.sample_id)}-{repetition_index:04d}",
        repetition_index=repetition_index,
        agent_engine="direct-runner",
        runner_class="direct_runner",
        provider_profile=MISSING_NOT_APPLICABLE,
        model=MISSING_NOT_APPLICABLE,
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
    product_runner: ProductRun,
) -> EvalResult:
    run_dir.mkdir(parents=True, exist_ok=True)
    try:
        run_result = product_runner(**_product_run_kwargs(sample, run_dir=run_dir, budget=budget))
    except Exception as exc:  # noqa: BLE001 - eval packets must classify runner failures.
        return _blocked_result_from_exception(trial, exc)

    grader_outputs = _grade_trial(sample=sample, run_dir=run_dir, run_result=run_result)
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


def _product_run_kwargs(sample: EvalSample, *, run_dir: Path, budget: str) -> dict[str, Any]:
    launch_overrides = sample.launch_overrides or {}
    semantic_sweep = sample.intent == "map-build" or sample.preset == "map-build"
    return {
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
) -> dict[str, Any]:
    return {
        "artifacts": _artifact_grader(run_dir),
        "privacy": _privacy_grader(run_result),
        "trajectory": _trajectory_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "outcome": _outcome_grader(sample=sample, run_dir=run_dir, run_result=run_result),
        "efficiency": _efficiency_grader(run_result),
    }


def _artifact_grader(run_dir: Path) -> dict[str, Any]:
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
        passed = runtime_map_path.exists() and bool(runtime_map)
        return {
            "status": "passed" if passed else "failed",
            "runtime_metric_map_exists": runtime_map_path.exists(),
            "public_anchor_count": len(runtime_map.get("public_anchors") or []),
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


def _status_from_graders(grader_outputs: dict[str, Any]) -> tuple[str, str]:
    ordered_failures = (
        ("artifacts", "artifact_missing"),
        ("privacy", "private_truth_leak"),
        ("trajectory", "trajectory_policy_violation"),
        ("outcome", "private_goal_not_satisfied"),
    )
    for grader_name, failure_class in ordered_failures:
        if grader_outputs.get(grader_name, {}).get("status") == "failed":
            return "failed", failure_class
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


def _results_bundle(
    *,
    suite: EvalSuite,
    results: list[EvalResult],
    output_dir: Path,
    budget: str,
) -> dict[str, Any]:
    result_payloads = [result.to_dict() for result in results]
    aggregate = _aggregate_results(result_payloads)
    return {
        "schema": RESULTS_BUNDLE_SCHEMA,
        "suite": suite.to_dict(),
        "budget": budget,
        "result_schema": EVAL_RESULT_SCHEMA,
        "aggregate": aggregate,
        "results": result_payloads,
        "artifacts": {
            "output_dir": str(output_dir),
        },
    }


def _aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    passed = sum(1 for result in results if result.get("status") == "passed")
    failed = sum(1 for result in results if result.get("status") == "failed")
    blocked = sum(1 for result in results if result.get("status") == "blocked")
    failure_classes: dict[str, int] = {}
    for result in results:
        failure_class = str(result.get("failure_class") or MISSING_UNAVAILABLE)
        if failure_class == MISSING_NOT_APPLICABLE:
            continue
        failure_classes[failure_class] = failure_classes.get(failure_class, 0) + 1
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "pass_at_1": round(passed / total, 6) if total else 0.0,
        "failure_classes": failure_classes,
    }


def _render_eval_report(bundle: dict[str, Any]) -> str:
    suite = bundle["suite"]
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    output_dir = Path(str(artifacts.get("output_dir") or "."))
    rows = "\n".join(_report_row(result, output_dir=output_dir) for result in bundle["results"])
    aggregate = bundle["aggregate"]
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Roboclaws Eval - {html.escape(str(suite["suite_id"]))}</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 0.5rem; text-align: left; }}
    th {{ background: #f0f4f8; }}
    .passed {{ color: #176b3a; font-weight: 700; }}
    .failed, .blocked {{ color: #9f1239; font-weight: 700; }}
  </style>
</head>
<body>
  <h1>{html.escape(str(suite["suite_id"]))}</h1>
  <p>Pass@1: {aggregate["pass_at_1"]} ({aggregate["passed"]}/{aggregate["total"]})</p>
  <table>
    <thead>
      <tr><th>Sample</th><th>Trial</th><th>Status</th><th>Failure</th><th>Run</th></tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _report_row(result: dict[str, Any], *, output_dir: Path) -> str:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
    run_result = str(artifacts.get("run_result") or "")
    report = str(artifacts.get("report") or "")
    links = []
    if run_result:
        href = html.escape(_report_href(run_result, output_dir))
        links.append(f'<a href="{href}">run_result</a>')
    if report:
        href = html.escape(_report_href(report, output_dir))
        links.append(f'<a href="{href}">report</a>')
    status = str(result.get("status") or "")
    return (
        "      <tr>"
        f"<td>{html.escape(str(identity.get('sample_id') or ''))}</td>"
        f"<td>{html.escape(str(identity.get('trial_id') or ''))}</td>"
        f'<td class="{html.escape(status)}">{html.escape(status)}</td>'
        f"<td>{html.escape(str(result.get('failure_class') or ''))}</td>"
        f"<td>{' | '.join(links)}</td>"
        "</tr>"
    )


def _report_href(path: str, output_dir: Path) -> str:
    artifact_path = Path(path)
    try:
        return artifact_path.relative_to(output_dir).as_posix()
    except ValueError:
        return artifact_path.as_posix()


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


def _parse_key_value_args(argv: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    index = 0
    while index < len(argv):
        item = argv[index]
        if item.startswith("--"):
            key = item.removeprefix("--").replace("-", "_")
            if "=" in key:
                key, value = key.split("=", 1)
            else:
                index += 1
                if index >= len(argv):
                    raise ValueError(f"missing value for {item}")
                value = argv[index]
            parsed[key] = value
        elif "=" in item:
            key, value = item.split("=", 1)
            parsed[key.replace("-", "_")] = value
        else:
            raise ValueError(f"unsupported eval argument {item!r}; expected key=value")
        index += 1
    return parsed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Roboclaws eval suite.")
    parser.add_argument("overrides", nargs="*", help="key=value overrides.")
    args = parser.parse_args(argv)
    try:
        overrides = _parse_key_value_args(args.overrides)
        suite_ref = overrides.pop("suite", "smoke_regression")
        budget = overrides.pop("budget", "smoke")
        output_root = Path(overrides.pop("output_dir", str(DEFAULT_OUTPUT_ROOT)))
        stamp = overrides.pop("stamp", None)
        if overrides:
            keys = ", ".join(sorted(overrides))
            raise ValueError(f"unsupported eval override(s): {keys}")
        run = run_eval_suite(suite_ref, output_root=output_root, budget=budget, stamp=stamp)
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps({"results": str(run.results_path), "report": str(run.report_path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Eval result bundle and HTML report rendering."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from roboclaws.evals.models import (
    EVAL_RESULT_SCHEMA,
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSuite,
)

RESULTS_BUNDLE_SCHEMA = "roboclaws_eval_results_bundle_v1"


def results_bundle(
    *,
    suite: EvalSuite,
    results: list[EvalResult],
    output_dir: Path,
    budget: str,
) -> dict[str, Any]:
    result_payloads = [result.to_dict() for result in results]
    aggregate = aggregate_results(result_payloads)
    sampler_projection = _sampler_projection_aggregate(suite)
    if sampler_projection:
        aggregate["sampler_projection"] = sampler_projection
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


def aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
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
    samples = _sample_summaries(results)
    sample_count = len(samples)
    max_repetition_count = max(
        (summary["trial_count"] for summary in samples.values()),
        default=0,
    )
    pass_at_k = _pass_at_k(samples, max_repetition_count)
    pass_caret_k, pass_caret_k_eligible = _pass_caret_k(samples, max_repetition_count)
    aggregate = {
        "total": total,
        "trial_count": total,
        "sample_count": sample_count,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "pass_at_1": pass_at_k.get("1", 0.0),
        "pass_at_k": pass_at_k,
        "pass_caret_k": pass_caret_k,
        "pass_caret_k_eligible": pass_caret_k_eligible,
        "max_repetition_count": max_repetition_count,
        "failure_classes": failure_classes,
        "samples": samples,
    }
    open_ended = _open_ended_aggregate(results)
    if open_ended:
        aggregate["open_ended"] = open_ended
    return aggregate


def render_eval_report(bundle: dict[str, Any]) -> str:
    suite = bundle["suite"]
    artifacts = bundle.get("artifacts") if isinstance(bundle.get("artifacts"), dict) else {}
    output_dir = Path(str(artifacts.get("output_dir") or "."))
    rows = "\n".join(_report_row(result, output_dir=output_dir) for result in bundle["results"])
    aggregate = bundle["aggregate"]
    sampler_projection = _sampler_projection_section(aggregate)
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
  <p>Pass@1: {aggregate["pass_at_1"]} ({aggregate["passed"]}/{aggregate["total"]} trials)</p>
{sampler_projection}
  <table>
    <thead>
      <tr>
        <th>Sample</th><th>Trial</th><th>Engine</th><th>Provider</th>
        <th>Category</th><th>Outcome</th><th>Status</th><th>Failure</th>
        <th>Tool calls</th><th>Tool events</th><th>Wall time</th><th>Model attempts</th><th>Run</th>
      </tr>
    </thead>
    <tbody>
{rows}
    </tbody>
  </table>
</body>
</html>
"""


def _sampler_projection_aggregate(suite: EvalSuite) -> dict[str, Any]:
    metadata = suite.metadata if isinstance(suite.metadata, dict) else {}
    projection = metadata.get("sampler_projection")
    if not isinstance(projection, dict):
        return {}
    scene_sources = projection.get("scene_sources")
    if not isinstance(scene_sources, dict):
        scene_sources = {}
    compact_sources = {}
    for source, payload in sorted(scene_sources.items()):
        if not isinstance(payload, dict):
            continue
        compact_sources[str(source)] = {
            "support_status": payload.get("support_status", ""),
            "status": payload.get("status", ""),
            "target_count": int(payload.get("target_count") or 0),
            "ready_count": int(payload.get("ready_count") or 0),
            "needed_count": int(payload.get("needed_count") or 0),
            "blocked_count": int(payload.get("blocked_count") or 0),
            "rejected_count": int(payload.get("rejected_count") or 0),
            "sample_ids": list(payload.get("sample_ids") or []),
        }
    return {
        "schema": projection.get("schema", ""),
        "projection": projection.get("projection", ""),
        "generator_version": projection.get("generator_version", ""),
        "summary": dict(projection.get("summary") or {}),
        "scene_sources": compact_sources,
    }


def _sampler_projection_section(aggregate: dict[str, Any]) -> str:
    sampler_projection = aggregate.get("sampler_projection")
    if not isinstance(sampler_projection, dict):
        return ""
    summary = sampler_projection.get("summary")
    if not isinstance(summary, dict):
        return ""
    rows = "\n".join(
        _sampler_projection_source_row(source, payload)
        for source, payload in (sampler_projection.get("scene_sources") or {}).items()
        if isinstance(payload, dict)
    )
    return f"""  <section>
    <h2>Scene Sampler Projection</h2>
    <p>Ready samples: {html.escape(str(summary.get("ready_sample_count", 0)))} /
    {html.escape(str(summary.get("target_sample_count", 0)))}; remaining:
    {html.escape(str(summary.get("remaining_sample_count", 0)))}; partial sources:
    {html.escape(str(summary.get("partial_source_count", 0)))}; blocked sources:
    {html.escape(str(summary.get("blocked_source_count", 0)))}.</p>
    <table>
      <thead>
        <tr>
          <th>Scene source</th><th>Status</th><th>Ready</th>
          <th>Needed</th><th>Blocked</th><th>Rejected</th>
        </tr>
      </thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </section>
"""


def _sampler_projection_source_row(source: str, payload: dict[str, Any]) -> str:
    return (
        "        <tr>"
        f"<td>{html.escape(str(source))}</td>"
        f"<td>{html.escape(str(payload.get('support_status') or ''))}</td>"
        f"<td>{html.escape(str(payload.get('ready_count') or 0))}/"
        f"{html.escape(str(payload.get('target_count') or 0))}</td>"
        f"<td>{html.escape(str(payload.get('needed_count') or 0))}</td>"
        f"<td>{html.escape(str(payload.get('blocked_count') or 0))}</td>"
        f"<td>{html.escape(str(payload.get('rejected_count') or 0))}</td>"
        "</tr>"
    )


def _report_row(result: dict[str, Any], *, output_dir: Path) -> str:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    artifacts = result.get("artifacts") if isinstance(result.get("artifacts"), dict) else {}
    links = []
    for key, label in (("run_result", "run_result"), ("report", "report")):
        if key in artifacts:
            links.append(_artifact_link_or_status(label, artifacts.get(key), output_dir))
    status = str(result.get("status") or "")
    metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
    attempts = (
        metrics.get("model_attempt_summary")
        if isinstance(metrics.get("model_attempt_summary"), dict)
        else {}
    )
    open_ended = (
        result.get("grader_outputs", {}).get("open_ended")
        if isinstance(result.get("grader_outputs"), dict)
        and isinstance(result.get("grader_outputs", {}).get("open_ended"), dict)
        else {}
    )
    return (
        "      <tr>"
        f"<td>{html.escape(str(identity.get('sample_id') or ''))}</td>"
        f"<td>{html.escape(str(identity.get('trial_id') or ''))}</td>"
        f"<td>{html.escape(str(identity.get('agent_engine') or ''))}</td>"
        f"<td>{html.escape(str(identity.get('provider_profile') or ''))}</td>"
        f"<td>{html.escape(str(open_ended.get('open_ended_category') or ''))}</td>"
        f"<td>{html.escape(str(open_ended.get('expected_goal_outcome') or ''))}</td>"
        f'<td class="{html.escape(status)}">{html.escape(status)}</td>'
        f"<td>{html.escape(str(result.get('failure_class') or ''))}</td>"
        f"<td>{html.escape(str(metrics.get('tool_call_count') or ''))}</td>"
        f"<td>{html.escape(str(metrics.get('tool_event_count') or ''))}</td>"
        f"<td>{html.escape(str(metrics.get('wall_time_s') or ''))}</td>"
        f"<td>{html.escape(str(attempts.get('attempt_count') or ''))}</td>"
        f"<td>{' | '.join(links)}</td>"
        "</tr>"
    )


def _artifact_link_or_status(label: str, raw_path: Any, output_dir: Path) -> str:
    path_text = str(raw_path or "").strip()
    if not path_text:
        return _artifact_unavailable(label, "empty artifact path", "")
    artifact_path = Path(path_text)
    candidate = artifact_path if artifact_path.is_absolute() else output_dir / artifact_path
    try:
        resolved_output_dir = output_dir.resolve()
        resolved_candidate = candidate.resolve()
        relative_path = resolved_candidate.relative_to(resolved_output_dir)
    except (OSError, ValueError):
        return _artifact_unavailable(label, "outside eval output", path_text)
    if not resolved_candidate.is_file():
        return _artifact_unavailable(label, "missing artifact", relative_path.as_posix())
    href = html.escape(relative_path.as_posix())
    return f'<a href="{href}">{html.escape(label)}</a>'


def _artifact_unavailable(label: str, reason: str, path: str) -> str:
    detail = f"{reason}: {path}" if path else reason
    return (
        f'<span class="unavailable">{html.escape(label)} unavailable ({html.escape(detail)})</span>'
    )


def _sample_summaries(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
        sample_id = str(identity.get("sample_id") or "unavailable")
        grouped.setdefault(sample_id, []).append(result)

    summaries: dict[str, dict[str, Any]] = {}
    for sample_id, sample_results in sorted(grouped.items()):
        ordered = sorted(sample_results, key=_repetition_index)
        statuses = [str(result.get("status") or "") for result in ordered]
        failure_classes = [
            str(result.get("failure_class") or MISSING_UNAVAILABLE)
            for result in ordered
            if str(result.get("failure_class") or MISSING_UNAVAILABLE) != MISSING_NOT_APPLICABLE
        ]
        summaries[sample_id] = {
            "trial_count": len(ordered),
            "passed": statuses.count("passed"),
            "failed": statuses.count("failed"),
            "blocked": statuses.count("blocked"),
            "first_status": statuses[0] if statuses else MISSING_UNAVAILABLE,
            "pass_at_1": bool(statuses and statuses[0] == "passed"),
            "pass_any": any(status == "passed" for status in statuses),
            "pass_all": bool(statuses) and all(status == "passed" for status in statuses),
            "statuses": statuses,
            "failure_classes": failure_classes,
        }
    return summaries


def _open_ended_aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    open_results = [
        result
        for result in results
        if (
            isinstance(result.get("identity"), dict)
            and str(result["identity"].get("intent") or "") == "open-ended"
        )
    ]
    if not open_results:
        return {}
    by_category: dict[str, dict[str, int]] = {}
    by_outcome: dict[str, dict[str, int]] = {}
    by_engine_provider: dict[str, dict[str, int]] = {}
    by_failure_class: dict[str, int] = {}
    live_statuses: dict[str, int] = {}
    tool_event_counts: dict[str, int] = {}
    total_tool_calls = 0
    total_tool_events = 0
    wall_times: list[float] = []
    model_attempt_total = 0
    model_success_total = 0
    model_failure_total = 0
    for result in open_results:
        status = str(result.get("status") or MISSING_UNAVAILABLE)
        identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
        grader_outputs = (
            result.get("grader_outputs") if isinstance(result.get("grader_outputs"), dict) else {}
        )
        open_ended = (
            grader_outputs.get("open_ended")
            if isinstance(grader_outputs.get("open_ended"), dict)
            else {}
        )
        metrics = result.get("metrics") if isinstance(result.get("metrics"), dict) else {}
        _increment_status_bucket(
            by_category,
            str(open_ended.get("open_ended_category") or MISSING_UNAVAILABLE),
            status,
        )
        _increment_status_bucket(
            by_outcome,
            str(open_ended.get("expected_goal_outcome") or MISSING_UNAVAILABLE),
            status,
        )
        engine_provider = (
            f"{identity.get('agent_engine') or MISSING_UNAVAILABLE}/"
            f"{identity.get('provider_profile') or MISSING_UNAVAILABLE}"
        )
        _increment_status_bucket(by_engine_provider, engine_provider, status)
        failure_class = str(result.get("failure_class") or MISSING_UNAVAILABLE)
        if failure_class != MISSING_NOT_APPLICABLE:
            by_failure_class[failure_class] = by_failure_class.get(failure_class, 0) + 1
        total_tool_calls += _int_value(metrics.get("tool_call_count"))
        total_tool_events += _int_value(metrics.get("tool_event_count"))
        per_tool = metrics.get("tool_event_counts")
        if isinstance(per_tool, dict):
            for name, count in per_tool.items():
                tool_event_counts[str(name)] = tool_event_counts.get(str(name), 0) + _int_value(
                    count
                )
        wall_time = _float_or_none(metrics.get("wall_time_s"))
        if wall_time is not None:
            wall_times.append(wall_time)
        attempts = (
            metrics.get("model_attempt_summary")
            if isinstance(metrics.get("model_attempt_summary"), dict)
            else {}
        )
        model_attempt_total += _int_value(attempts.get("attempt_count"))
        model_success_total += _int_value(attempts.get("success_count"))
        model_failure_total += _int_value(attempts.get("failure_count"))
        live_status = (
            grader_outputs.get("efficiency", {}).get("live_status")
            if isinstance(grader_outputs.get("efficiency"), dict)
            and isinstance(grader_outputs.get("efficiency", {}).get("live_status"), dict)
            else {}
        )
        live_phase = str(live_status.get("phase") or MISSING_UNAVAILABLE)
        live_statuses[live_phase] = live_statuses.get(live_phase, 0) + 1
    return {
        "schema": "roboclaws_open_ended_eval_aggregate_v1",
        "by_category": by_category,
        "by_expected_goal_outcome": by_outcome,
        "by_engine_provider": by_engine_provider,
        "by_failure_class": by_failure_class,
        "live_statuses": live_statuses,
        "telemetry": {
            "tool_call_count": total_tool_calls,
            "tool_event_count": total_tool_events,
            "tool_event_counts": tool_event_counts,
            "wall_time_s": _wall_time_summary(wall_times),
            "model_attempt_count": model_attempt_total,
            "model_success_count": model_success_total,
            "model_failure_count": model_failure_total,
        },
    }


def _increment_status_bucket(buckets: dict[str, dict[str, int]], key: str, status: str) -> None:
    bucket = buckets.setdefault(key, {"passed": 0, "failed": 0, "blocked": 0, "inconclusive": 0})
    if status not in bucket:
        bucket[status] = 0
    bucket[status] += 1


def _wall_time_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0, "min": MISSING_UNAVAILABLE, "max": MISSING_UNAVAILABLE}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "sum": round(sum(values), 3),
    }


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _pass_at_k(samples: dict[str, dict[str, Any]], max_repetition_count: int) -> dict[str, float]:
    if not samples:
        return {}
    metrics: dict[str, float] = {}
    for k in range(1, max_repetition_count + 1):
        successes = 0
        for summary in samples.values():
            statuses = list(summary.get("statuses") or [])
            if any(status == "passed" for status in statuses[:k]):
                successes += 1
        metrics[str(k)] = round(successes / len(samples), 6)
    return metrics


def _pass_caret_k(
    samples: dict[str, dict[str, Any]],
    max_repetition_count: int,
) -> tuple[dict[str, float], dict[str, int]]:
    metrics: dict[str, float] = {}
    eligible_counts: dict[str, int] = {}
    for k in range(1, max_repetition_count + 1):
        eligible = [
            list(summary.get("statuses") or [])
            for summary in samples.values()
            if len(summary.get("statuses") or []) >= k
        ]
        eligible_counts[str(k)] = len(eligible)
        if not eligible:
            metrics[str(k)] = 0.0
            continue
        successes = sum(
            1 for statuses in eligible if all(status == "passed" for status in statuses[:k])
        )
        metrics[str(k)] = round(successes / len(eligible), 6)
    return metrics, eligible_counts


def _repetition_index(result: dict[str, Any]) -> int:
    identity = result.get("identity") if isinstance(result.get("identity"), dict) else {}
    try:
        return int(identity.get("repetition_index") or 0)
    except (TypeError, ValueError):
        return 0

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
    return {
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


def render_eval_report(bundle: dict[str, Any]) -> str:
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
  <p>Pass@1: {aggregate["pass_at_1"]} ({aggregate["passed"]}/{aggregate["total"]} trials)</p>
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

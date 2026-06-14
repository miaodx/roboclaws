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
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "blocked": blocked,
        "pass_at_1": round(passed / total, 6) if total else 0.0,
        "failure_classes": failure_classes,
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

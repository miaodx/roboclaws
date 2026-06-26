"""HTML rendering helpers for MapBuild eval reports."""

from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

from roboclaws.evals.models import MISSING_UNAVAILABLE


def render_map_build_matrix_report(summary: dict[str, Any], *, output_dir: Path) -> str:
    overview = summary.get("overview") if isinstance(summary.get("overview"), dict) else {}
    profile_count = html.escape(str(overview.get("profile_count", 0)))
    map_build_row_count = html.escape(str(overview.get("map_build_row_count", 0)))
    map_build_passed = html.escape(str(overview.get("map_build_passed", 0)))
    richer_than_base = html.escape(str(overview.get("richer_than_base", 0)))
    downstream_improved = html.escape(str(overview.get("downstream_improved", 0)))
    downstream_no_regression = html.escape(str(overview.get("downstream_no_regression", 0)))
    downstream_regressed = html.escape(str(overview.get("downstream_regressed", 0)))
    downstream_inconclusive = html.escape(str(overview.get("downstream_inconclusive", 0)))
    source_rows = "\n".join(
        _map_build_source_row(source, output_dir=output_dir)
        for source in _list_of_mappings(summary.get("sources"))
    )
    quality_rows = "\n".join(
        _map_build_quality_html_row(row, output_dir=output_dir)
        for row in _list_of_mappings(summary.get("map_build_rows"))
    )
    downstream_rows = "\n".join(
        _map_build_downstream_html_row(row, output_dir=output_dir)
        for row in _list_of_mappings(summary.get("downstream_rows"))
    )
    cost_rows = "\n".join(
        _map_build_cost_html_row(row, output_dir=output_dir)
        for row in _list_of_mappings(summary.get("map_build_rows"))
    )
    failure_rows = "\n".join(
        _map_build_failure_html_row(row, output_dir=output_dir)
        for row in _list_of_mappings(summary.get("failure_rows"))
    )
    failure_section = (
        _map_build_failures_section(failure_rows)
        if failure_rows
        else "  <section><h2>Failures And Inconclusive Rows</h2><p>None.</p></section>\n"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Roboclaws MapBuild Matrix Report</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1f2933; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 1.5rem; }}
    th, td {{ border: 1px solid #d9e2ec; padding: 0.5rem; text-align: left; vertical-align: top; }}
    th {{ background: #f0f4f8; }}
    code {{ white-space: pre-wrap; }}
    .passed, .improved, .no_regression {{ color: #176b3a; font-weight: 700; }}
    .failed, .regressed, .blocked {{ color: #9f1239; font-weight: 700; }}
    .inconclusive, .unavailable {{ color: #7c5e10; font-weight: 700; }}
    .metric {{ display: inline-block; margin-right: 1rem; }}
  </style>
</head>
<body>
  <h1>MapBuild Matrix Report</h1>
  <section>
    <h2>Overview</h2>
    <p>
      <span class="metric">Profiles: {profile_count}</span>
      <span class="metric">MapBuild rows: {map_build_row_count}</span>
      <span class="metric">MapBuild passed: {map_build_passed}</span>
      <span class="metric">Richer than base: {richer_than_base}</span>
      <span class="metric">Improved: {downstream_improved}</span>
      <span class="metric">No regression: {downstream_no_regression}</span>
      <span class="metric">Regressed: {downstream_regressed}</span>
      <span class="metric">Inconclusive: {downstream_inconclusive}</span>
    </p>
  </section>
  <section>
    <h2>MapBuild Quality Matrix</h2>
    <table>
      <thead>
        <tr>
          <th>Profile</th><th>Status</th><th>Anchors</th><th>Stable categories</th>
          <th>Runtime evidence</th><th>Sim truth</th><th>Quality guards</th><th>Evidence</th>
        </tr>
      </thead>
      <tbody>
{quality_rows}
      </tbody>
    </table>
  </section>
  <section>
    <h2>Downstream Impact</h2>
    <table>
      <thead>
        <tr>
          <th>Profile</th><th>Task</th><th>Label</th>
          <th>Without MapBuild prior</th><th>With MapBuild prior</th>
          <th>Tool deltas</th><th>Outcome delta</th>
          <th>Reason</th><th>Evidence</th>
        </tr>
      </thead>
      <tbody>
{downstream_rows}
      </tbody>
    </table>
  </section>
  <section>
    <h2>Tool And Time Cost</h2>
    <table>
      <thead>
        <tr>
          <th>Profile</th><th>Wall time</th><th>Model attempts</th><th>MCP/tool requests</th>
          <th>Tool events</th><th>Observe</th><th>Waypoints</th>
          <th>Relative moves</th><th>Adjust camera</th>
        </tr>
      </thead>
      <tbody>
{cost_rows}
      </tbody>
    </table>
  </section>
{failure_section}
  <section>
    <h2>Evidence Links</h2>
    <table>
      <thead><tr><th>Source</th><th>Suite</th><th>Links</th></tr></thead>
      <tbody>
{source_rows}
      </tbody>
    </table>
  </section>
</body>
</html>
"""


def render_map_build_review_section(summary: dict[str, Any], *, output_dir: Path) -> str:
    map_build_rows = _list_of_mappings(summary.get("map_build_rows"))
    downstream_rows = _list_of_mappings(summary.get("downstream_rows"))
    if not map_build_rows and not downstream_rows:
        return ""
    overview = summary.get("overview") if isinstance(summary.get("overview"), dict) else {}
    quality_rows = "\n".join(
        _map_build_quality_html_row(row, output_dir=output_dir) for row in map_build_rows
    )
    downstream_body = "\n".join(
        _map_build_downstream_html_row(row, output_dir=output_dir) for row in downstream_rows
    )
    downstream_table = ""
    if downstream_body:
        downstream_table = f"""    <table>
      <thead>
        <tr>
          <th>Profile</th><th>Task</th><th>Label</th><th>Without MapBuild prior</th>
          <th>With MapBuild prior</th><th>Tool deltas</th>
          <th>Outcome delta</th><th>Reason</th><th>Evidence</th>
        </tr>
      </thead>
      <tbody>
{downstream_body}
      </tbody>
    </table>
"""
    quality_table = ""
    if quality_rows:
        quality_table = f"""    <table>
      <thead>
        <tr>
          <th>Profile</th><th>Status</th><th>Anchors</th><th>Stable categories</th>
          <th>Runtime evidence</th><th>Sim truth</th><th>Quality guards</th><th>Evidence</th>
        </tr>
      </thead>
      <tbody>
{quality_rows}
      </tbody>
    </table>
"""
    return f"""  <section>
    <h2>MapBuild Review</h2>
    <p>Profiles: {html.escape(str(overview.get("profile_count", 0)))};
    map-build passed: {html.escape(str(overview.get("map_build_passed", 0)))} /
    {html.escape(str(overview.get("map_build_row_count", 0)))};
    richer than base: {html.escape(str(overview.get("richer_than_base", 0)))};
    downstream improved/no-regression/regressed/inconclusive:
    {html.escape(str(overview.get("downstream_improved", 0)))}/
    {html.escape(str(overview.get("downstream_no_regression", 0)))}/
    {html.escape(str(overview.get("downstream_regressed", 0)))}/
    {html.escape(str(overview.get("downstream_inconclusive", 0)))}.</p>
{quality_table}{downstream_table}  </section>
"""


def _map_build_quality_html_row(row: dict[str, Any], *, output_dir: Path) -> str:
    categories = ", ".join(_string_list(row.get("stable_semantic_anchor_categories")))
    anchors = (
        f"base {row.get('base_map_anchor_like_count', 0)} -> "
        f"semantic {row.get('public_semantic_anchor_count', 0)} "
        f"(+{row.get('runtime_enrichment_anchor_count', 0)} runtime)"
    )
    runtime = (
        f"objects {row.get('observed_object_count', 0)}; "
        f"targets {row.get('target_candidate_count', 0)}; "
        f"explore {row.get('generated_exploration_candidate_count', 0)}"
    )
    sim_truth = (
        f"recall {row.get('sim_truth_fixture_category_recall', MISSING_UNAVAILABLE)}; "
        f"precision {row.get('sim_truth_fixture_category_precision', MISSING_UNAVAILABLE)}; "
        f"best-view {row.get('sim_truth_best_view_waypoint_accuracy', MISSING_UNAVAILABLE)}"
    )
    guards = (
        f"duplicates {row.get('duplicate_fixture_viewpoint_group_count', 0)}; "
        f"RGB-only poses {row.get('rgb_only_object_pose_claim_count', 0)}; "
        f"private truth absent {row.get('private_truth_absent', MISSING_UNAVAILABLE)}; "
        f"source map unchanged {row.get('source_map_not_mutated', MISSING_UNAVAILABLE)}"
    )
    artifacts = row.get("artifacts") if isinstance(row.get("artifacts"), dict) else {}
    evidence = _matrix_artifact_links(
        artifacts,
        output_dir=output_dir,
        keys=("report", "run_result", "runtime_metric_map"),
    )
    status = str(row.get("status") or "")
    return (
        "        <tr>"
        f"<td>{html.escape(str(row.get('profile_label') or ''))}</td>"
        f'<td class="{html.escape(status)}">{html.escape(status)}</td>'
        f"<td>{html.escape(anchors)}</td>"
        f"<td>{html.escape(str(row.get('stable_semantic_anchor_category_count', 0)))}: "
        f"{html.escape(categories)}</td>"
        f"<td>{html.escape(runtime)}</td>"
        f"<td>{html.escape(sim_truth)}</td>"
        f"<td>{html.escape(guards)}</td>"
        f"<td>{evidence}</td>"
        "</tr>"
    )


def _map_build_downstream_html_row(row: dict[str, Any], *, output_dir: Path) -> str:
    no_prior = row.get("no_prior") if isinstance(row.get("no_prior"), dict) else {}
    prior = (
        row.get("fixture_focused_prior")
        if isinstance(row.get("fixture_focused_prior"), dict)
        else {}
    )
    label = str(row.get("comparison_label") or "")
    deltas = row.get("tool_deltas") if isinstance(row.get("tool_deltas"), dict) else {}
    outcome_delta = row.get("outcome_delta") if isinstance(row.get("outcome_delta"), dict) else {}
    evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
    no_links = _matrix_artifact_links(
        evidence.get("no_prior") if isinstance(evidence.get("no_prior"), dict) else {},
        output_dir=output_dir,
        keys=("report", "run_result"),
    )
    prior_links = _matrix_artifact_links(
        evidence.get("fixture_focused_prior")
        if isinstance(evidence.get("fixture_focused_prior"), dict)
        else {},
        output_dir=output_dir,
        keys=("report", "run_result"),
    )
    evidence_links = f"without MapBuild prior: {no_links}; with MapBuild prior: {prior_links}"
    return (
        "        <tr>"
        f"<td>{html.escape(str(row.get('profile_label') or ''))}</td>"
        f"<td>{html.escape(str(row.get('task_family') or ''))}</td>"
        f'<td class="{html.escape(label)}">{html.escape(label)}</td>'
        f"<td>{_downstream_variant_html(no_prior)}</td>"
        f"<td>{_downstream_variant_html(prior)}</td>"
        f"<td>{html.escape(_format_tool_deltas(deltas))}</td>"
        f"<td>{html.escape(_format_outcome_delta(outcome_delta))}</td>"
        f"<td>{html.escape(str(row.get('reason') or ''))}</td>"
        f"<td>{evidence_links}</td>"
        "</tr>"
    )


def _map_build_cost_html_row(row: dict[str, Any], *, output_dir: Path) -> str:
    request_count = row.get("request_event_count", MISSING_UNAVAILABLE)
    request_summary = f"{row.get('tool_call_count', MISSING_UNAVAILABLE)} / {request_count}"
    return (
        "        <tr>"
        f"<td>{html.escape(str(row.get('profile_label') or ''))}</td>"
        f"<td>{html.escape(str(row.get('wall_time_s', MISSING_UNAVAILABLE)))}</td>"
        f"<td>{html.escape(str(row.get('model_attempt_count', MISSING_UNAVAILABLE)))}</td>"
        f"<td>{html.escape(request_summary)}</td>"
        f"<td>{html.escape(str(row.get('tool_event_count', MISSING_UNAVAILABLE)))}</td>"
        f"<td>{html.escape(str(row.get('observe_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('navigate_to_waypoint_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('navigate_to_relative_pose_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('adjust_camera_count', 0)))}</td>"
        "</tr>"
    )


def _map_build_failure_html_row(row: dict[str, Any], *, output_dir: Path) -> str:
    label = str(row.get("label") or "")
    artifacts = row.get("artifacts") if isinstance(row.get("artifacts"), dict) else {}
    links = _matrix_artifact_links(
        artifacts,
        output_dir=output_dir,
        keys=("report", "run_result", "runtime_metric_map"),
    )
    return (
        "        <tr>"
        f"<td>{html.escape(str(row.get('profile_label') or ''))}</td>"
        f"<td>{html.escape(str(row.get('kind') or ''))}</td>"
        f'<td class="{html.escape(label)}">{html.escape(label)}</td>'
        f"<td>{html.escape(str(row.get('reason') or ''))}</td>"
        f"<td>{links}</td>"
        "</tr>"
    )


def _map_build_failures_section(rows: str) -> str:
    return f"""  <section>
    <h2>Failures And Inconclusive Rows</h2>
    <table>
      <thead><tr><th>Profile</th><th>Kind</th><th>Label</th><th>Reason</th><th>Evidence</th></tr></thead>
      <tbody>
{rows}
      </tbody>
    </table>
  </section>
"""


def _map_build_source_row(source: dict[str, Any], *, output_dir: Path) -> str:
    links = []
    source_path = str(source.get("path") or "")
    eval_report = str(source.get("eval_report") or "")
    if source_path:
        links.append(_matrix_file_link("eval_results", source_path, output_dir=output_dir))
    if eval_report:
        links.append(_matrix_file_link("eval_report", eval_report, output_dir=output_dir))
    return (
        "        <tr>"
        f"<td>{html.escape(source_path)}</td>"
        f"<td>{html.escape(str(source.get('suite_id') or ''))}</td>"
        f"<td>{' | '.join(links) if links else html.escape(MISSING_UNAVAILABLE)}</td>"
        "</tr>"
    )


def _downstream_variant_html(row: dict[str, Any]) -> str:
    tool_counts = row.get("tool_counts") if isinstance(row.get("tool_counts"), dict) else {}
    return html.escape(
        f"{row.get('status', MISSING_UNAVAILABLE)} "
        f"({row.get('failure_class', MISSING_UNAVAILABLE)}); "
        f"prior {row.get('prior_use_verdict', MISSING_UNAVAILABLE)}; "
        f"obs {tool_counts.get('observe', MISSING_UNAVAILABLE)}, "
        f"wp {tool_counts.get('navigate_to_waypoint', MISSING_UNAVAILABLE)}, "
        f"turn {tool_counts.get('navigate_to_relative_pose', MISSING_UNAVAILABLE)}, "
        f"adj {tool_counts.get('adjust_camera', MISSING_UNAVAILABLE)}; "
        f"calls {row.get('tool_call_count', MISSING_UNAVAILABLE)}; "
        f"restore {row.get('mess_restoration_rate', MISSING_UNAVAILABLE)}"
    )


def _format_tool_deltas(deltas: dict[str, Any]) -> str:
    return (
        f"obs {deltas.get('observe', MISSING_UNAVAILABLE)}, "
        f"wp {deltas.get('navigate_to_waypoint', MISSING_UNAVAILABLE)}, "
        f"turn {deltas.get('navigate_to_relative_pose', MISSING_UNAVAILABLE)}, "
        f"adj {deltas.get('adjust_camera', MISSING_UNAVAILABLE)}, "
        f"calls {deltas.get('tool_call_count', MISSING_UNAVAILABLE)}, "
        f"wall {deltas.get('wall_time_s', MISSING_UNAVAILABLE)}"
    )


def _format_outcome_delta(delta: dict[str, Any]) -> str:
    return f"restoration {delta.get('mess_restoration_rate', MISSING_UNAVAILABLE)}"


def _matrix_artifact_links(
    artifacts: dict[str, Any],
    *,
    output_dir: Path,
    keys: tuple[str, ...],
) -> str:
    links = [
        _matrix_file_link(key, str(artifacts.get(key) or ""), output_dir=output_dir)
        for key in keys
        if str(artifacts.get(key) or "").strip()
    ]
    return " | ".join(links) if links else html.escape(MISSING_UNAVAILABLE)


def _matrix_file_link(label: str, raw_path: str, *, output_dir: Path) -> str:
    path = Path(raw_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    resolved = path
    try:
        resolved = path.resolve()
        href = resolved.relative_to(output_dir.resolve()).as_posix()
    except (OSError, ValueError):
        try:
            href = Path(os.path.relpath(resolved, output_dir.resolve())).as_posix()
        except (OSError, ValueError):
            href = raw_path
    if not path.is_file():
        return _artifact_unavailable(label, "missing artifact", raw_path)
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a>'


def _list_of_mappings(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _artifact_unavailable(label: str, reason: str, path: str) -> str:
    detail = f"{reason}: {path}" if path else reason
    return (
        f'<span class="unavailable">{html.escape(label)} unavailable ({html.escape(detail)})</span>'
    )

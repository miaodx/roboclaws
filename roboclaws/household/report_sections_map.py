from __future__ import annotations

import html
from typing import Any


def map_evidence_refresh_summary_section(run_result: dict[str, Any]) -> str:
    if not _is_map_evidence_refresh_run(run_result):
        return ""

    agent_view = run_result.get("agent_view") or {}
    runtime_metric_map = (
        agent_view.get("runtime_metric_map") or run_result.get("runtime_metric_map") or {}
    )
    anchors = runtime_metric_map.get("public_semantic_anchors") or []
    observed = runtime_metric_map.get("observed_objects") or []
    generated = runtime_metric_map.get("generated_exploration_candidates") or []
    raw_observations = run_result.get("raw_fpv_observations") or (
        agent_view.get("raw_fpv_observations") or []
    )
    model_observations = run_result.get("model_declared_observations") or (
        agent_view.get("model_declared_observations") or []
    )
    trace = run_result.get("cleanup_policy_trace") or {}
    events = trace.get("events") or []
    visited_anchor_count = sum(1 for item in anchors if _anchor_was_visited(item))
    needs_review_count = sum(1 for item in anchors if _anchor_needs_review(item))
    actionable_count = sum(
        1 for item in observed if str(item.get("actionability") or "") == "actionable"
    )
    selected_targets = _map_evidence_refresh_target_rows(anchors, observed)
    driver_note = _map_evidence_refresh_driver_note(run_result)

    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Agent-driven', _yes_no(run_result.get('agent_driven')))}"
        f"{_metric('Policy', run_result.get('policy', 'unknown'))}"
        f"{_metric('Public anchors', len(anchors))}"
        f"{_metric('Visited anchors', visited_anchor_count)}"
        f"{_metric('Observed handles', len(observed))}"
        f"{_metric('Raw observations', len(raw_observations))}"
        f"{_metric('Model observations', len(model_observations))}"
        f"{_metric('Generated candidates', len(generated))}"
        "</div>"
    )
    rows = "".join(selected_targets)
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Evidence target</th>'
        "<th>Type</th><th>Category</th><th>Waypoint</th><th>Observation</th>"
        "<th>Status</th></tr></thead><tbody>"
        f"{rows}</tbody></table></div>"
        if rows
        else '<p class="note">No refreshed map-evidence targets were recorded.</p>'
    )
    task_prompt = str(run_result.get("task_prompt") or "").strip()
    prompt_html = (
        '<details class="summary-metadata"><summary>Task prompt</summary>'
        f"<p>{html.escape(task_prompt)}</p></details>"
        if task_prompt
        else ""
    )
    boundary = (
        "This section summarizes map-evidence refresh evidence. "
        f"{driver_note} "
        f"Simulated={_yes_no(run_result.get('simulated'))}; "
        f"physical robot={_yes_no(run_result.get('physical_robot'))}; "
        f"loop={trace.get('loop_style', 'unknown')}; trace events={len(events)}. "
        "Use this as a sim/readability proof unless agent-driven=true and the run "
        "used the live Codex or robot MCP route."
    )
    review_note = (
        f"{needs_review_count} anchors currently need review or carry uncertain promotion status. "
        f"{actionable_count} observed handles are actionable in the runtime map."
    )
    return (
        '<section class="panel map-evidence-refresh-summary">'
        "<h2>Map Evidence Refresh Summary</h2>"
        f'<p class="note">{html.escape(boundary)}</p>'
        f'<p class="note">{html.escape(review_note)}</p>'
        f"{metrics}{table}{prompt_html}</section>"
    )


def _is_map_evidence_refresh_run(run_result: dict[str, Any]) -> bool:
    policy = str(run_result.get("policy") or "")
    task_prompt = str(run_result.get("task_prompt") or "")
    if "map_evidence_refresh" in policy or "inspection_tour" in policy:
        return True
    prompt_markers = (
        "开放巡检",
        "语义地图",
        "public semantic anchor",
        "evidence refresh",
        "map evidence",
    )
    return run_result.get("task_name") == "semantic-map-build" and any(
        marker in task_prompt for marker in prompt_markers
    )


def _anchor_was_visited(anchor: dict[str, Any]) -> bool:
    evidence = anchor.get("evidence") if isinstance(anchor.get("evidence"), dict) else {}
    return bool(evidence.get("visited") or anchor.get("source_observation_id"))


def _anchor_needs_review(anchor: dict[str, Any]) -> bool:
    values = {
        str(anchor.get("actionability") or ""),
        str(anchor.get("promotion_status") or ""),
        str(anchor.get("grounding_status") or ""),
    }
    evidence = anchor.get("evidence") if isinstance(anchor.get("evidence"), dict) else {}
    values.add(str(evidence.get("status") or ""))
    return bool(values.intersection({"needs_review", "costmap_disagrees", "observe_only"}))


def _map_evidence_refresh_target_rows(
    anchors: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> list[str]:
    rows = []
    for item in anchors[:8]:
        rows.append(
            _map_evidence_refresh_target_row(
                identifier=item.get("anchor_id", ""),
                target_type=item.get("anchor_type", ""),
                category=item.get("category", ""),
                waypoint_id=item.get("waypoint_id", ""),
                observation_id=item.get("source_observation_id", ""),
                status=item.get("promotion_status", ""),
            )
        )
    if len(rows) < 8:
        for item in observed[: 8 - len(rows)]:
            rows.append(
                _map_evidence_refresh_target_row(
                    identifier=item.get("object_id", ""),
                    target_type="observed_object",
                    category=item.get("category", ""),
                    waypoint_id=item.get("waypoint_id", ""),
                    observation_id=item.get("source_observation_id", ""),
                    status=item.get("actionability", ""),
                )
            )
    return rows


def _map_evidence_refresh_target_row(
    *,
    identifier: Any,
    target_type: Any,
    category: Any,
    waypoint_id: Any,
    observation_id: Any,
    status: Any,
) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(identifier))}</td>"
        f"<td>{html.escape(str(target_type))}</td>"
        f"<td>{html.escape(str(category))}</td>"
        f"<td>{html.escape(str(waypoint_id))}</td>"
        f"<td>{html.escape(str(observation_id))}</td>"
        f"<td>{html.escape(str(status))}</td>"
        "</tr>"
    )


def _map_evidence_refresh_driver_note(run_result: dict[str, Any]) -> str:
    if run_result.get("agent_driven") is True:
        return "The run is marked agent-driven, so target choice should be reviewed in trace."
    return (
        "The run is not agent-driven; it validates prompt/report plumbing and "
        "direct semantic sweep evidence, not autonomous target choice."
    )


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"

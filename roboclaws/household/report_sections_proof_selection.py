from __future__ import annotations

import html
from typing import Any


def proof_request_selection_section(selection: dict[str, Any]) -> str:
    if not selection:
        return ""
    selected = selection.get("selected_requests") or []
    excluded = selection.get("excluded_requests") or []
    target_feasibility_blockers = selection.get("target_feasibility_blockers") or []
    grasp_feasibility_blockers = selection.get("grasp_feasibility_blockers") or []
    request_filter = selection.get("request_filter") or {}
    request_filter = request_filter if isinstance(request_filter, dict) else {}
    raw_fallback_generation = selection.get("fallback_generation") or {}
    fallback_generation = (
        raw_fallback_generation if isinstance(raw_fallback_generation, dict) else {}
    )
    generated = fallback_generation.get("generated_requests") or []
    filtered_aliases = fallback_generation.get("filtered_aliases") or []
    discovered_aliases = fallback_generation.get("discovered_aliases") or []
    filtered_pairs = fallback_generation.get("filtered_pairs") or []
    normalized_aliases = fallback_generation.get("normalized_aliases") or []
    exhaustion_blockers = fallback_generation.get("exhaustion_blockers") or []
    target_blocker_count = selection.get(
        "target_feasibility_blocker_count",
        len(target_feasibility_blockers),
    )
    grasp_blocker_count = selection.get(
        "grasp_feasibility_blocker_count",
        len(grasp_feasibility_blockers),
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Mode', selection.get('mode', 'unknown'))}"
        f"{_metric('Ready', selection.get('ready_request_count', 0))}"
        f"{_metric('Candidate ready', selection.get('candidate_request_count', 0))}"
        f"{_metric('Selected', selection.get('selected_count', len(selected)))}"
        f"{_metric('Excluded', selection.get('excluded_count', len(excluded)))}"
        f"{_metric('Covered', selection.get('covered_request_count', 0))}"
        f"{_metric('Coverage min steps', selection.get('prior_covered_min_proof_steps', 1))}"
        f"{_metric('Generated', selection.get('generated_fallback_request_count', len(generated)))}"
        f"{_metric('Discovered aliases', len(discovered_aliases))}"
        f"{_metric('Normalized aliases', len(normalized_aliases))}"
        f"{_metric('Filtered aliases', len(filtered_aliases))}"
        f"{_metric('Filtered pairs', len(filtered_pairs))}"
        f"{_metric('Fallback status', fallback_generation.get('status', 'unknown'))}"
        f"{_metric('Exhaustion blockers', len(exhaustion_blockers))}"
        f"{_metric('Target blockers', target_blocker_count)}"
        f"{_metric('Grasp blockers', grasp_blocker_count)}"
        f"{_metric('Fallback required', _yes_no(selection.get('fallback_required')))}"
        "</div>"
    )
    selected_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('request_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('request_type', 'source')))}</td>"
        f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('target_receptacle_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_task_feasibility_status', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_proof_quality', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_steps_executed', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_kind', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_result_match_kind', '')))}</td>"
        "</tr>"
        for item in selected
        if isinstance(item, dict)
    )
    excluded_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('request_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('target_receptacle_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('reason', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_task_feasibility_status', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_proof_quality', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_steps_executed', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_kind', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_summary', '')))}</td>"
        f"<td>{html.escape(str(item.get('prior_result_match_kind', '')))}</td>"
        f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
        "</tr>"
        for item in excluded
        if isinstance(item, dict)
    )
    if not selected_rows:
        selected_rows = '<tr><td colspan="10">No proof requests selected.</td></tr>'
    if not excluded_rows:
        excluded_rows = '<tr><td colspan="11">No proof requests excluded.</td></tr>'
    selected_table = (
        '<h3>Selected Requests</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Type</th><th>Source</th><th>Object</th><th>Target</th>"
        "<th>Prior feasibility</th><th>Prior quality</th><th>Prior steps</th>"
        "<th>Prior blocker</th><th>Prior match</th>"
        f"</tr></thead><tbody>{selected_rows}</tbody></table></div>"
    )
    excluded_table = (
        '<h3>Excluded Requests</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Object</th><th>Target</th><th>Reason</th>"
        "<th>Prior feasibility</th><th>Prior quality</th><th>Prior steps</th>"
        "<th>Prior blocker</th><th>Prior detail</th><th>Prior match</th>"
        "<th>Prior blockers</th>"
        f"</tr></thead><tbody>{excluded_rows}</tbody></table></div>"
    )
    request_filter_table = _request_filter_table(request_filter)
    generated_table = _generated_fallback_requests_table(generated)
    target_blockers_table = _target_feasibility_blockers_table(target_feasibility_blockers)
    grasp_blockers_matrix = _grasp_feasibility_blocker_matrix(grasp_feasibility_blockers)
    grasp_blockers_table = _grasp_feasibility_blockers_table(grasp_feasibility_blockers)
    discovered_table = _discovered_fallback_aliases_table(discovered_aliases)
    normalized_table = _normalized_fallback_aliases_table(normalized_aliases)
    filtered_table = _filtered_fallback_aliases_table(filtered_aliases)
    filtered_pairs_table = _filtered_fallback_pairs_table(filtered_pairs)
    exhaustion_table = _fallback_exhaustion_blockers_table(exhaustion_blockers)
    note = selection.get("evidence_note") or (
        "Private proof request selection for local proof-bundle execution."
    )
    return (
        '<section class="panel proof-request-selection">'
        "<h2>Proof Request Selection</h2>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}'
        f"{request_filter_table}{selected_table}{excluded_table}{target_blockers_table}"
        f"{grasp_blockers_matrix}{grasp_blockers_table}{generated_table}{discovered_table}"
        f"{normalized_table}{filtered_table}{filtered_pairs_table}{exhaustion_table}</section>"
    )


def _request_filter_table(request_filter: dict[str, Any]) -> str:
    if not request_filter.get("enabled"):
        return ""
    requested = [str(item) for item in request_filter.get("requested_request_ids") or []]
    matched = {str(item) for item in request_filter.get("matched_request_ids") or []}
    missing = {str(item) for item in request_filter.get("missing_request_ids") or []}
    rows = []
    for request_id in requested:
        if request_id in matched:
            status = "matched_ready"
        elif request_id in missing:
            status = "missing"
        else:
            status = "unavailable"
        rows.append(f"<tr><td>{html.escape(request_id)}</td><td>{html.escape(status)}</td></tr>")
    if not rows:
        rows.append('<tr><td colspan="2">No request ids requested.</td></tr>')
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Requested', request_filter.get('requested_count', len(requested)))}"
        f"{_metric('Matched', request_filter.get('matched_count', len(matched)))}"
        f"{_metric('Unavailable', request_filter.get('unavailable_count', 0))}"
        f"{_metric('Missing', request_filter.get('missing_count', len(missing)))}"
        "</div>"
    )
    note = request_filter.get("evidence_note") or "Explicit request-id filter."
    return (
        "<h3>Request ID Filter</h3>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}'
        '<div class="table-wrap"><table><thead><tr><th>Request</th><th>Status</th>'
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _generated_fallback_requests_table(generated: list[dict[str, Any]]) -> str:
    rows = []
    for item in generated:
        if not isinstance(item, dict):
            continue
        fallback = item.get("fallback_request") or {}
        args = item.get("planner_probe_args") or {}
        source_request_id = fallback.get(
            "source_request_id",
            item.get("source_request_id", ""),
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('request_id', '')))}</td>"
            f"<td>{html.escape(str(source_request_id))}</td>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(args.get('--cleanup-planner-object-id', '')))}</td>"
            f"<td>{html.escape(str(args.get('--cleanup-planner-target-receptacle-id', '')))}</td>"
            f"<td>{html.escape(str(fallback.get('reason', '')))}</td>"
            f"<td>{html.escape(str(fallback.get('prior_task_feasibility_blocker_kind', '')))}</td>"
            "<td>"
            f"{html.escape(str(fallback.get('prior_task_feasibility_blocker_summary', '')))}"
            "</td>"
            f"<td>{html.escape(str(fallback.get('prior_result_match_kind', '')))}</td>"
            f"<td>{html.escape(_blocker_codes(fallback.get('prior_blockers') or []))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="11">No generated fallback requests.</td></tr>')
    return (
        "<h3>Generated Fallback Requests</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Source</th><th>Object</th><th>Target</th>"
        "<th>Planner object alias</th><th>Planner target alias</th><th>Reason</th>"
        "<th>Prior blocker</th><th>Prior detail</th><th>Prior match</th><th>Prior blockers</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _target_feasibility_blockers_table(blockers: list[dict[str, Any]]) -> str:
    rows = []
    for item in blockers:
        if not isinstance(item, dict):
            continue
        object_value = item.get("object_id") or item.get("object_alias") or ""
        target_value = item.get("target_receptacle_id") or item.get("target_alias") or ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(object_value))}</td>"
            f"<td>{html.escape(str(target_value))}</td>"
            f"<td>{html.escape(str(item.get('derived_from', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_status', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_summary', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_result_match_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('last_worker_stage', '')))}</td>"
            f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
            f"<td>{html.escape(str(item.get('prior_report', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="13">No target feasibility blockers recorded.</td></tr>')
    return (
        "<h3>Target Feasibility Blockers</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Kind</th><th>Source</th><th>Object or alias</th><th>Target or alias</th>"
        "<th>Derived from</th><th>Reason</th><th>Prior feasibility</th>"
        "<th>Prior blocker</th><th>Prior detail</th><th>Prior match</th><th>Last stage</th>"
        "<th>Prior blockers</th><th>Proof report</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _grasp_feasibility_blockers_table(blockers: list[dict[str, Any]]) -> str:
    rows = []
    for item in blockers:
        if not isinstance(item, dict):
            continue
        object_value = item.get("object_id") or item.get("object_alias") or ""
        target_value = item.get("target_receptacle_id") or item.get("target_alias") or ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(object_value))}</td>"
            f"<td>{html.escape(str(target_value))}</td>"
            f"<td>{html.escape(str(item.get('derived_from', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_summary', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_result_match_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_report', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8">No grasp-feasibility blockers recorded.</td></tr>')
    return (
        "<h3>Grasp Feasibility Blockers</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Kind</th><th>Source</th><th>Object or alias</th><th>Target or alias</th>"
        "<th>Derived from</th><th>Detail</th><th>Prior match</th><th>Proof report</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _grasp_feasibility_blocker_matrix(blockers: list[dict[str, Any]]) -> str:
    cards = []
    for item in blockers:
        if not isinstance(item, dict):
            continue
        object_value = item.get("object_id") or item.get("object_alias") or "object"
        target_value = item.get("target_receptacle_id") or item.get("target_alias") or "target"
        detail = item.get("prior_task_feasibility_blocker_summary") or ""
        badges = [
            item.get("kind", "blocked"),
            item.get("source_request_id", ""),
            item.get("prior_result_match_kind", ""),
        ]
        badge_html = "".join(
            f'<span class="badge">{html.escape(str(value))}</span>' for value in badges if value
        )
        cards.append(
            '<article class="grasp-blocker-card">'
            '<div class="grasp-blocker-route">'
            f"<strong>{html.escape(str(object_value))}</strong>"
            "<span>to</span>"
            f"<strong>{html.escape(str(target_value))}</strong>"
            "</div>"
            f'<div class="evidence-badges">{badge_html}</div>'
            f"<p>{html.escape(str(detail))}</p>"
            "</article>"
        )
    if not cards:
        return ""
    return (
        "<h3>Grasp Feasibility Blocker Matrix</h3>"
        f'<div class="grasp-blocker-matrix">{"".join(cards)}</div>'
    )


def _discovered_fallback_aliases_table(discovered_aliases: list[dict[str, Any]]) -> str:
    rows = []
    for item in discovered_aliases:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('axis', '')))}</td>"
            f"<td>{html.escape(str(item.get('alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('derived_from', '')))}</td>"
            f"<td>{html.escape(str(item.get('invalid_alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="6">No runtime aliases discovered.</td></tr>')
    return (
        "<h3>Discovered Runtime Aliases</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Axis</th><th>Alias</th><th>Derived from</th>"
        "<th>Invalid alias</th><th>Reason</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _normalized_fallback_aliases_table(normalized_aliases: list[dict[str, Any]]) -> str:
    rows = []
    for item in normalized_aliases:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('axis', '')))}</td>"
            f"<td>{html.escape(str(item.get('alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('normalized_alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="5">No pickup root aliases normalized.</td></tr>')
    return (
        "<h3>Normalized Pickup Root Aliases</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Axis</th><th>Alias</th><th>Normalized alias</th><th>Reason</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _filtered_fallback_aliases_table(filtered_aliases: list[dict[str, Any]]) -> str:
    rows = []
    for item in filtered_aliases:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('axis', '')))}</td>"
            f"<td>{html.escape(str(item.get('alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="4">No fallback aliases filtered.</td></tr>')
    return (
        "<h3>Filtered Fallback Aliases</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Axis</th><th>Alias</th><th>Reason</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _filtered_fallback_pairs_table(filtered_pairs: list[dict[str, Any]]) -> str:
    rows = []
    for item in filtered_pairs:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source_request_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('object_alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_alias', '')))}</td>"
            f"<td>{html.escape(str(item.get('derived_from', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_status', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_task_feasibility_blocker_summary', '')))}</td>"
            f"<td>{html.escape(str(item.get('prior_result_match_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('last_worker_stage', '')))}</td>"
            f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
            f"<td>{html.escape(str(item.get('prior_report', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="12">No fallback alias pairs filtered.</td></tr>')
    return (
        "<h3>Filtered Fallback Pairs</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Planner object alias</th><th>Planner target alias</th>"
        "<th>Derived from</th><th>Reason</th><th>Prior feasibility</th>"
        "<th>Prior blocker</th><th>Prior detail</th><th>Prior match</th><th>Last stage</th>"
        "<th>Prior blockers</th><th>Proof report</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _fallback_exhaustion_blockers_table(blockers: list[dict[str, Any]]) -> str:
    rows = []
    for item in blockers:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('code', '')))}</td>"
            f"<td>{html.escape(str(item.get('count', '')))}</td>"
            f"<td>{html.escape(str(item.get('message', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="3">No fallback exhaustion blockers recorded.</td></tr>')
    return (
        "<h3>Fallback Exhaustion Blockers</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Blocker</th><th>Evidence count</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _blocker_codes(blockers: list[dict[str, Any]]) -> str:
    return ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in blockers
        if isinstance(item, dict)
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

from __future__ import annotations

import html
from typing import Any

from roboclaws.household.planner_proof_quality import planner_proof_quality_evidence


def planner_probe_quality_section(evidence: dict[str, Any]) -> str:
    if not evidence:
        return ""
    quality = planner_proof_quality_evidence(evidence)
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Proof Quality', quality.get('quality_tier', 'unknown'))}"
        f"{_metric('Steps', quality.get('steps_executed', 0))}"
        f"{_metric('Qpos delta', quality.get('max_abs_qpos_delta', 0.0))}"
        f"{_metric('Containment proven', 'yes' if quality.get('containment_proven') else 'no')}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("One-step motion", quality.get("one_step_motion", False)),
            _badge("Multi-step motion", quality.get("multi_step_motion", False)),
            _badge("Object state evidence", quality.get("object_state_evidence_present", False)),
        )
    )
    note = quality.get("evidence_note") or ""
    return (
        '<section class="panel planner-proof-quality">'
        "<h2>Planner Proof Quality</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div></section>'
    )


def planner_probe_views_section(evidence: dict[str, Any]) -> str:
    artifacts = evidence.get("image_artifacts") or {}
    if not artifacts:
        diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
        if diagnostics:
            return (
                '<section class="panel"><h2>Planner Probe Diagnostic Views</h2>'
                f"{planner_probe_task_sampler_diagnostic_views(diagnostics)}</section>"
            )
        return ""
    figures = "".join(
        _view_figure(path, planner_probe_image_artifact_label(label))
        for label, path in _ordered_image_artifacts(artifacts)
    )
    return (
        '<section class="panel"><h2>Planner Probe Views</h2>'
        '<div class="views">'
        f"{figures}</div></section>"
    )


def _ordered_image_artifacts(artifacts: dict[str, Any]) -> list[tuple[str, Any]]:
    preferred = ("initial", "final")
    items = []
    for key in preferred:
        if artifacts.get(key):
            items.append((key, artifacts[key]))
    items.extend(
        (str(key), value)
        for key, value in sorted(artifacts.items())
        if key not in preferred and value
    )
    return items


def planner_probe_image_artifact_label(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Planner view"
    return " ".join(part.capitalize() for part in text.split())


def planner_probe_task_sampler_diagnostic_views(diagnostics: dict[str, Any]) -> str:
    if not diagnostics:
        return ""
    return f'<div class="views">{_task_sampler_diagnostic_figure(diagnostics)}</div>'


def planner_probe_post_placement_rejection_views(diagnostics: dict[str, Any]) -> str:
    grasp_failures = [
        item for item in diagnostics.get("grasp_failures") or [] if isinstance(item, dict)
    ]
    if not grasp_failures:
        return ""
    removed = [item for item in grasp_failures if item.get("removed_candidate")]
    first = grasp_failures[0]
    object_name = str(first.get("object_name") or "sampled object")
    grasp_count = _safe_int(diagnostics.get("grasp_failure_count"), len(grasp_failures))
    removal_count = _safe_int(
        diagnostics.get("candidate_removal_count"),
        len(diagnostics.get("candidate_removals") or []),
    )
    effective_removal_count = (
        _safe_int(diagnostics.get("candidate_effective_removal_count"), 0)
        if "candidate_effective_removal_count" in diagnostics
        else len(removed)
    )
    candidate_name_miss_count = _safe_int(diagnostics.get("candidate_name_miss_count"), 0)
    threshold_exceeded_count = _safe_int(diagnostics.get("grasp_threshold_exceeded_count"), 0)
    max_value = max(grasp_count, removal_count, effective_removal_count, 1)
    grasp_width = _scaled_bar_width(grasp_count, max_value)
    removal_width = _scaled_bar_width(removal_count, max_value)
    effective_width = _scaled_bar_width(effective_removal_count, max_value)
    stats = [
        ("Grasp failures", grasp_count),
        ("Removal calls", removal_count),
        ("Effective removals", effective_removal_count),
        ("Candidate name misses", candidate_name_miss_count),
        ("Threshold exceeded", threshold_exceeded_count),
        ("Candidate rows", len(grasp_failures)),
        ("Candidates before", first.get("candidate_count_before", "")),
        ("Candidates after", first.get("candidate_count_after", "")),
    ]
    stat_html = "".join(
        '<span class="diagnostic-stat">'
        f"<small>{html.escape(str(label))}</small>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</span>"
        for label, value in stats
        if value != ""
    )
    return (
        '<div class="post-placement-rejection-views">'
        "<h3>Post-Placement Rejection Views</h3>"
        '<div class="views"><figure class="diagnostic-view rejection-view">'
        '<div class="diagnostic-visual" role="img" '
        'aria-label="Post-placement rejection flow">'
        '<svg viewBox="0 0 360 210" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="0" y="0" width="360" height="210" rx="8" fill="#fff7ed"/>'
        '<text x="24" y="34" fill="#0f172a" font-size="15" font-weight="700">'
        "Post-placement rejection flow</text>"
        '<text x="24" y="58" fill="#64748b" font-size="12">'
        f"{html.escape(object_name)}</text>"
        '<text x="24" y="91" fill="#334155" font-size="12">grasp failures</text>'
        '<rect x="150" y="79" width="170" height="14" rx="7" fill="#fed7aa"/>'
        f'<rect x="150" y="79" width="{grasp_width}" height="14" rx="7" fill="#f97316"/>'
        '<text x="326" y="91" fill="#0f172a" font-size="12" text-anchor="end">'
        f"{grasp_count}</text>"
        '<text x="24" y="128" fill="#334155" font-size="12">removal calls</text>'
        '<rect x="150" y="116" width="170" height="14" rx="7" fill="#fecaca"/>'
        f'<rect x="150" y="116" width="{removal_width}" height="14" rx="7" fill="#ef4444"/>'
        '<text x="326" y="128" fill="#0f172a" font-size="12" text-anchor="end">'
        f"{removal_count}</text>"
        '<text x="24" y="165" fill="#334155" font-size="12">effective removals</text>'
        '<rect x="150" y="153" width="170" height="14" rx="7" fill="#e2e8f0"/>'
        f'<rect x="150" y="153" width="{effective_width}" height="14" rx="7" fill="#64748b"/>'
        '<text x="326" y="165" fill="#0f172a" font-size="12" text-anchor="end">'
        f"{effective_removal_count}</text>"
        "</svg>"
        "</div>"
        f"<figcaption>Post-placement rejection flow: {html.escape(object_name)}</figcaption>"
        f'<div class="diagnostic-stats">{stat_html}</div>'
        "</figure></div></div>"
    )


def _task_sampler_diagnostic_figure(diagnostics: dict[str, Any]) -> str:
    last = diagnostics.get("last_placement_scene_diagnostic") or {}
    target = str(last.get("target_name") or "target")
    fraction = _safe_float(last.get("valid_neighborhood_fraction"))
    fraction_text = _format_fraction(last.get("valid_neighborhood_fraction", ""))
    bar_width = int(max(0.0, min(fraction, 1.0)) * 125)
    placement_attempts = int(diagnostics.get("robot_placement_attempt_count") or 0)
    placement_failures = int(diagnostics.get("robot_placement_failure_count") or 0)
    grasp_failures = int(diagnostics.get("grasp_failure_count") or 0)
    candidate_removals = int(diagnostics.get("candidate_removal_count") or 0)
    nearest = last.get("nearest_free_point_distance_m", "")
    stats = [
        ("Placement attempts", placement_attempts),
        ("Placement failures", placement_failures),
        ("Grasp failures", grasp_failures),
        ("Candidate removals", candidate_removals),
        ("Free-space fraction", fraction_text),
        ("Nearest free distance", nearest),
    ]
    stat_html = "".join(
        '<span class="diagnostic-stat">'
        f"<small>{html.escape(str(label))}</small>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</span>"
        for label, value in stats
        if value != ""
    )
    return (
        '<figure class="diagnostic-view">'
        '<div class="diagnostic-visual" role="img" aria-label="Task sampler diagnostic view">'
        '<svg viewBox="0 0 360 220" xmlns="http://www.w3.org/2000/svg">'
        '<rect x="0" y="0" width="360" height="220" rx="8" fill="#f8fafc"/>'
        '<circle cx="110" cy="104" r="70" fill="#e0f2fe" stroke="#0284c7" '
        'stroke-width="2" stroke-dasharray="7 5"/>'
        '<circle cx="110" cy="104" r="9" fill="#f97316"/>'
        '<path d="M110 104 L166 64" stroke="#475569" stroke-width="2"/>'
        '<circle cx="166" cy="64" r="6" fill="#475569"/>'
        '<text x="30" y="196" fill="#334155" font-size="13">target</text>'
        '<text x="145" y="196" fill="#334155" font-size="13">nearest free point</text>'
        '<text x="215" y="54" fill="#0f172a" font-size="16" font-weight="700">'
        f"{html.escape(str(fraction_text))}</text>"
        '<text x="215" y="75" fill="#475569" font-size="12">free-space fraction</text>'
        '<rect x="215" y="92" width="125" height="12" rx="6" fill="#e2e8f0"/>'
        f'<rect x="215" y="92" width="{bar_width}" height="12" rx="6" fill="#22c55e"/>'
        '<text x="215" y="134" fill="#0f172a" font-size="16" font-weight="700">'
        f"{grasp_failures}</text>"
        '<text x="215" y="155" fill="#475569" font-size="12">grasp failures</text>'
        '<text x="215" y="184" fill="#0f172a" font-size="16" font-weight="700">'
        f"{candidate_removals}</text>"
        '<text x="215" y="205" fill="#475569" font-size="12">candidate removals</text>'
        "</svg>"
        "</div>"
        f"<figcaption>Task sampler diagnostic: {html.escape(target)}</figcaption>"
        f'<div class="diagnostic-stats">{stat_html}</div>'
        "</figure>"
    )


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _scaled_bar_width(value: int, max_value: int, *, width: int = 170) -> int:
    if max_value <= 0:
        return 0
    return int(max(0.0, min(float(value) / float(max_value), 1.0)) * width)


def planner_probe_cleanup_binding_section(evidence: dict[str, Any]) -> str:
    sampled = evidence.get("sampled_task_binding") or {}
    requested = evidence.get("requested_cleanup_primitive_binding") or {}
    promoted = evidence.get("cleanup_primitive_binding") or {}
    blockers = evidence.get("cleanup_primitive_binding_blockers") or []
    cleanup_task_config = evidence.get("cleanup_task_config") or {}
    config_blockers = _blocker_codes(cleanup_task_config.get("blockers") or [])
    cleanup_task_sampler_adapter = evidence.get("cleanup_task_sampler_adapter") or {}
    pickup_binding = cleanup_task_sampler_adapter.get("exact_pickup_candidate_binding") or {}
    if not (
        sampled
        or requested
        or promoted
        or blockers
        or cleanup_task_config
        or cleanup_task_sampler_adapter
    ):
        return ""
    rows = [
        ("Cleanup scene XML", cleanup_task_config.get("scene_xml", "")),
        ("Exact task config applied", _yes_no(cleanup_task_config.get("applied"))),
        ("Exact task config blockers", config_blockers),
        (
            "Exact sampler adapter applied",
            _yes_no(cleanup_task_sampler_adapter.get("applied")),
        ),
        (
            "Exact sampler adapter class",
            cleanup_task_sampler_adapter.get("task_sampler_class", ""),
        ),
        (
            "Exact sampler adapter object",
            cleanup_task_sampler_adapter.get("planner_object_id", ""),
        ),
        (
            "Exact sampler adapter target",
            cleanup_task_sampler_adapter.get("planner_target_receptacle_id", ""),
        ),
        ("Exact pickup candidate action", pickup_binding.get("action", "")),
        ("Exact pickup retry budget", pickup_binding.get("retry_budget", "")),
        ("Exact pickup retry budget applied", _yes_no(pickup_binding.get("retry_budget_applied"))),
        (
            "Exact pickup requested present before",
            _yes_no(pickup_binding.get("requested_present_before")),
        ),
        (
            "Exact pickup requested present after",
            _yes_no(pickup_binding.get("requested_present_after")),
        ),
        ("Exact pickup candidates before", pickup_binding.get("candidate_count_before", "")),
        ("Exact pickup candidates after", pickup_binding.get("candidate_count_after", "")),
        ("Sampled pickup", sampled.get("pickup_obj_name", "")),
        (
            "Sampled target",
            sampled.get("place_receptacle_name") or sampled.get("place_target_name") or "",
        ),
        ("Requested object", requested.get("object_id", "")),
        ("Requested target", requested.get("target_receptacle_id", "")),
        ("Requested source", requested.get("source_receptacle_id", "")),
        ("Requested scene XML", requested.get("scene_xml", "")),
        ("Planner object alias", requested.get("planner_object_id", "")),
        ("Planner target alias", requested.get("planner_target_receptacle_id", "")),
        ("Requested tools", ", ".join(str(item) for item in requested.get("tools") or [])),
        ("Promoted object", promoted.get("object_id", "")),
        ("Promoted target", promoted.get("target_receptacle_id", "")),
        ("Promoted planner object", promoted.get("planner_object_id", "")),
        ("Promoted planner target", promoted.get("planner_target_receptacle_id", "")),
        ("Promoted tools", ", ".join(str(item) for item in promoted.get("tools") or [])),
    ]
    binding_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value
    )
    if not binding_rows:
        binding_rows = '<tr><td colspan="2">No cleanup binding values recorded.</td></tr>'
    blocker_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('code', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in blockers
    )
    if blocker_rows:
        blocker_table = (
            '<div class="table-wrap"><table><thead><tr><th>Blocker</th>'
            f"<th>Message</th></tr></thead><tbody>{blocker_rows}</tbody></table></div>"
        )
    else:
        blocker_table = '<p class="note">No cleanup binding blockers recorded.</p>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Requested', _yes_no(requested.get('requested')))}"
        f"{_metric('Promoted', _yes_no(bool(promoted)))}"
        f"{_metric('Blockers', len(blockers))}"
        "</div>"
    )
    note = (
        "Planner probe cleanup binding joins a requested cleanup primitive to the "
        "sampled upstream pickup/place task. Exact match is required before this "
        "can feed cleanup primitive executor evidence."
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th>'
        f"</tr></thead><tbody>{binding_rows}</tbody></table></div>"
    )
    return (
        '<section class="panel planner-probe-cleanup-binding">'
        "<h2>Planner Probe Cleanup Binding</h2>"
        f'<p class="note">{html.escape(note)}</p>{metrics}{table}{blocker_table}</section>'
    )


def planner_probe_task_sampler_robot_placement_profile_section(evidence: dict[str, Any]) -> str:
    profile = evidence.get("task_sampler_robot_placement_profile") or {}
    if not profile:
        return ""
    before = profile.get("before") or {}
    after = profile.get("after") or {}
    overrides = profile.get("applied_overrides") or {}
    place_overrides = profile.get("place_robot_near_overrides") or {}
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Profile', profile.get('profile', 'none'))}"
        f"{_metric('Requested', _yes_no(profile.get('requested')))}"
        f"{_metric('Applied', _yes_no(profile.get('applied')))}"
        f"{_metric('place_robot_near max tries', place_overrides.get('max_tries', ''))}"
        "</div>"
    )
    rows = [
        ("Base pose radius before", before.get("base_pose_sampling_radius_range", "")),
        ("Base pose radius after", after.get("base_pose_sampling_radius_range", "")),
        ("Robot safety radius before", before.get("robot_safety_radius", "")),
        ("Robot safety radius after", after.get("robot_safety_radius", "")),
        ("Visibility check before", _yes_no(before.get("check_robot_placement_visibility"))),
        ("Visibility check after", _yes_no(after.get("check_robot_placement_visibility"))),
        ("Max placement attempts before", before.get("max_robot_placement_attempts", "")),
        ("Max placement attempts after", after.get("max_robot_placement_attempts", "")),
        ("Applied config overrides", overrides),
        ("place_robot_near overrides", place_overrides),
    ]
    blockers = profile.get("blockers") or []
    blocker_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('code', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in blockers
        if isinstance(item, dict)
    )
    blocker_table = (
        '<div class="table-wrap"><table><thead><tr><th>Blocker</th><th>Message</th></tr>'
        f"</thead><tbody>{blocker_rows}</tbody></table></div>"
        if blocker_rows
        else ""
    )
    note = profile.get("evidence_note") or (
        "Task sampler robot-placement profiles are probe-local mitigations. They do "
        "not change the cleanup contract or count as planner-backed proof by themselves."
    )
    return (
        '<section class="panel planner-probe-task-sampler-placement-profile">'
        "<h2>Task Sampler Robot Placement Profile</h2>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}{_field_table(rows)}'
        f"{blocker_table}</section>"
    )


def planner_probe_task_sampler_failure_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
    if not diagnostics:
        return ""
    attempts = diagnostics.get("robot_placement_attempts") or []
    asset_failures = diagnostics.get("asset_failures") or []
    candidate_removals = diagnostics.get("candidate_removals") or []
    place_robot_near_calls = diagnostics.get("place_robot_near_calls") or []
    config = diagnostics.get("robot_placement_config") or {}
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Adapter applied', _yes_no(diagnostics.get('applied')))}"
        f"{_metric('Placement attempts', diagnostics.get('robot_placement_attempt_count', 0))}"
        f"{_metric('Placement failures', diagnostics.get('robot_placement_failure_count', 0))}"
        f"{_metric('Asset failures', diagnostics.get('asset_failure_count', 0))}"
        "</div>"
    )
    config_rows = [
        ("Task sampler class", diagnostics.get("task_sampler_class", "")),
        ("Hooks", ", ".join(str(item) for item in diagnostics.get("hooks") or [])),
        ("Base pose radius", config.get("base_pose_sampling_radius_range", "")),
        ("Robot safety radius", config.get("robot_safety_radius", "")),
        ("Visibility check", _yes_no(config.get("check_robot_placement_visibility"))),
        ("Max robot placement attempts", config.get("max_robot_placement_attempts", "")),
        (
            "place_robot_near overrides",
            diagnostics.get("place_robot_near_overrides") or "",
        ),
    ]
    config_table = _field_table(config_rows)
    attempt_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('attempt_index', '')))}</td>"
        f"<td>{html.escape(str(item.get('pickup_obj_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('asset_uid', '')))}</td>"
        f"<td>{html.escape(str(item.get('result', '')))}</td>"
        f"<td>{html.escape(str(item.get('exception_type', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in attempts
        if isinstance(item, dict)
    )
    if not attempt_rows:
        attempt_rows = '<tr><td colspan="6">No robot placement attempts recorded.</td></tr>'
    attempt_table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Pickup object</th>'
        "<th>Asset UID</th><th>Result</th><th>Exception</th><th>Message</th>"
        f"</tr></thead><tbody>{attempt_rows}</tbody></table></div>"
    )
    asset_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('asset_uid', '')))}</td>"
        f"<td>{html.escape(str(item.get('reason', '')))}</td>"
        "</tr>"
        for item in asset_failures
        if isinstance(item, dict)
    )
    removal_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('object_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_name_present_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('effective_removal', '')))}</td>"
        "</tr>"
        for item in candidate_removals
        if isinstance(item, dict)
    )
    call_rows = "".join(
        _place_robot_near_call_row(item)
        for item in place_robot_near_calls
        if isinstance(item, dict)
    )
    supporting_tables = ""
    if call_rows:
        supporting_tables += (
            '<div class="table-wrap"><table><thead><tr><th>#</th>'
            "<th>Requested max tries</th><th>Effective max tries</th>"
            "<th>Effective safety radius</th><th>Effective visibility</th><th>Result</th>"
            f"</tr></thead><tbody>{call_rows}</tbody></table></div>"
        )
    if asset_rows:
        supporting_tables += (
            '<div class="table-wrap"><table><thead><tr><th>Asset UID</th>'
            f"<th>Reason</th></tr></thead><tbody>{asset_rows}</tbody></table></div>"
        )
    if removal_rows:
        supporting_tables += (
            '<div class="table-wrap"><table><thead><tr><th>Removed candidate</th>'
            "<th>Candidates before</th><th>Candidates after</th>"
            "<th>Name present before</th><th>Effective removal</th>"
            f"</tr></thead><tbody>{removal_rows}</tbody></table></div>"
        )
    note = (
        "Task sampler failure diagnostics are probe-local wrappers around upstream "
        "sampler hooks. They make upstream robot-placement failures visible without "
        "changing the cleanup contract or promoting planner-backed cleanup readiness."
    )
    return (
        '<section class="panel planner-probe-task-sampler-failure">'
        "<h2>Task Sampler Failure Diagnostics</h2>"
        f'<p class="note">{html.escape(note)}</p>{metrics}{config_table}'
        f"{attempt_table}{supporting_tables}</section>"
    )


def _place_robot_near_call_row(item: dict[str, Any]) -> str:
    requested = item.get("requested") or {}
    effective = item.get("effective") or {}
    return (
        "<tr>"
        f"<td>{html.escape(str(item.get('call_index', '')))}</td>"
        f"<td>{html.escape(str(requested.get('max_tries', '')))}</td>"
        f"<td>{html.escape(str(effective.get('max_tries', '')))}</td>"
        f"<td>{html.escape(str(effective.get('robot_safety_radius', '')))}</td>"
        f"<td>{html.escape(str(effective.get('check_camera_visibility', '')))}</td>"
        f"<td>{html.escape(str(item.get('result', '')))}</td>"
        "</tr>"
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


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )


def _review_image(path: Any, alt: str, *, caption: str | None = None) -> str:
    src = html.escape(str(path), quote=True)
    alt_text = html.escape(str(alt), quote=True)
    caption_text = str(caption or alt).strip() or "report image"
    escaped_caption = html.escape(caption_text, quote=True)
    aria_label = html.escape(f"Open {caption_text} image for review", quote=True)
    return (
        f'<a class="image-link" href="{src}" data-lightbox-image '
        f'data-lightbox-caption="{escaped_caption}" aria-label="{aria_label}">'
        f'<img src="{src}" alt="{alt_text}" loading="lazy" decoding="async">'
        "</a>"
    )


def _view_figure(path: Any, label: str) -> str:
    if not path:
        return ""
    escaped_label = html.escape(label)
    return (
        "<figure>"
        f"{_review_image(path, f'{label} view')}"
        f"<figcaption>{escaped_label}</figcaption>"
        "</figure>"
    )


def _field_table(rows: list[tuple[str, Any]]) -> str:
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in (None, "")
    )
    if not table_rows:
        table_rows = '<tr><td colspan="2">No values recorded.</td></tr>'
    return (
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th>'
        f"</tr></thead><tbody>{table_rows}</tbody></table></div>"
    )


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _format_fraction(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    return value

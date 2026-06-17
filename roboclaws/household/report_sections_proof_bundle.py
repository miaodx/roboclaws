from __future__ import annotations

import html
import os
from pathlib import Path
from typing import Any

from roboclaws.household.planner_proof_quality import (
    format_quality_tier_counts,
    planner_proof_quality_summary,
)
from roboclaws.household.planner_task_feasibility import grasp_feasibility_signature_counts
from roboclaws.household.report_sections_probe import (
    planner_probe_image_artifact_label,
    planner_probe_post_placement_rejection_views,
    planner_probe_task_sampler_diagnostic_views,
)


def proof_bundle_commands_section(commands: list[dict[str, Any]]) -> str:
    if not commands:
        return (
            '<section class="panel"><h2>Proof Probe Commands</h2>'
            '<p class="note">No ready proof requests produced probe commands.</p></section>'
        )
    rows = []
    for index, item in enumerate(commands, start=1):
        command = " ".join(str(part) for part in item.get("command") or [])
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(str(item.get('request_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_receptacle_id', '')))}</td>"
            f"<td>{_command_semantic_subphases(item)}</td>"
            f"<td>{html.escape(str(item.get('run_result', '')))}</td>"
            f"<td>{html.escape(str(item.get('report', '')))}</td>"
            f"<td><code>{html.escape(command)}</code></td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Request</th>'
        "<th>Object</th><th>Target</th><th>Semantic subphases</th>"
        "<th>Proof run result</th><th>Proof report</th><th>Command</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    return (
        '<section class="panel proof-bundle-commands">'
        "<h2>Proof Probe Commands</h2>"
        '<p class="note">Command evidence only. A command row is not planner proof until '
        "the referenced proof artifact passes the strict planner probe checker.</p>"
        f"{table}</section>"
    )


def proof_execution_horizon_section(horizon: dict[str, Any]) -> str:
    if not horizon:
        return ""
    blockers = horizon.get("blockers") or []
    blocker_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('code', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in blockers
        if isinstance(item, dict)
    )
    if not blocker_rows:
        blocker_rows = '<tr><td colspan="2">No proof execution horizon blockers.</td></tr>'
    blockers_table = (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Code</th><th>Message</th>"
        f"</tr></thead><tbody>{blocker_rows}</tbody></table></div>"
    )
    return (
        '<section class="panel proof-execution-horizon">'
        "<h2>Proof Execution Horizon</h2>"
        f'<p class="note">{html.escape(str(horizon.get("evidence_note", "")))}</p>'
        f"{_proof_execution_horizon_metrics(horizon)}{blockers_table}</section>"
    )


def grasp_feasibility_mitigation_decision_section(decision: dict[str, Any]) -> str:
    if not decision:
        return ""
    missing_assets = ", ".join(
        str(value) for value in decision.get("missing_grasp_asset_uids") or []
    )
    exception_types = ", ".join(
        str(value) for value in decision.get("grasp_load_exception_types") or []
    )
    rows = []
    for item in decision.get("signature_groups") or []:
        if not isinstance(item, dict):
            continue
        row_missing_assets = ", ".join(
            str(v) for v in item.get("grasp_load_exception_asset_uids") or []
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source', '')))}</td>"
            f"<td>{html.escape(str(item.get('subkind', '')))}</td>"
            f"<td>{html.escape(str(item.get('count', '')))}</td>"
            f"<td>{html.escape(str(item.get('summary', '')))}</td>"
            f"<td>{html.escape(', '.join(str(v) for v in item.get('request_ids') or []))}</td>"
            f"<td>{html.escape(', '.join(str(v) for v in item.get('object_names') or []))}</td>"
            f"<td>{html.escape(row_missing_assets)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="7">No grasp-feasibility signature groups.</td></tr>')
    table = (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Subkind</th><th>Proofs</th><th>Summary</th>"
        "<th>Requests</th><th>Planner objects</th><th>Missing grasp assets</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )
    cards = "".join(
        [
            _decision_card(
                "Recommendation",
                decision.get("recommendation", "unknown"),
                decision.get("rationale", ""),
            ),
            _decision_card(
                "Cache path",
                missing_assets or "No missing cache assets",
                "Mitigate missing cached grasps before retrying the matching exact-scene asset.",
            ),
            _decision_card(
                "Source rotation",
                decision.get("source_rotation_state", "unknown"),
                "Run selected unproven source-rotation requests separately from "
                "known cache misses.",
            ),
        ]
    )
    return (
        '<section class="panel grasp-mitigation-decision">'
        "<h2>Grasp Feasibility Mitigation Decision</h2>"
        '<p class="note">Routes grouped grasp-feasibility evidence before another runtime run.</p>'
        f"{_grasp_mitigation_metrics(decision, missing_assets, exception_types)}"
        f'<div class="decision-cards">{cards}</div>{table}</section>'
    )


def proof_bundle_warmup_section(warmup: dict[str, Any]) -> str:
    if not warmup:
        return ""
    command = " ".join(str(part) for part in warmup.get("command") or [])
    note = warmup.get("evidence_note") or (
        "Optional local-dev warmup before proof commands. Strict per-proof "
        "checkers remain authoritative."
    )
    return (
        '<section class="panel proof-bundle-warmup">'
        "<h2>RBY1M/CuRobo Warmup</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        + _path_table(
            [
                ("Warmup output", warmup.get("output_dir", "")),
                ("Warmup run result", warmup.get("run_result", "")),
                ("Warmup report", warmup.get("report", "")),
            ]
        )
        + f"<pre><code>{html.escape(command)}</code></pre></section>"
    )


def proof_bundle_local_runtime_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight:
        return ""
    blockers = preflight.get("blockers") or []
    checks = [item for item in preflight.get("checks") or [] if isinstance(item, dict)]
    rows = [
        ("Python executable", preflight.get("python_executable", "")),
        ("Evidence note", preflight.get("evidence_note", "")),
    ]
    return (
        '<section class="panel proof-bundle-local-runtime-preflight">'
        "<h2>Local Runtime Preflight</h2>"
        f"{_local_runtime_metrics(preflight, checks, blockers)}"
        f"{_field_table(rows)}{_local_runtime_check_table(checks)}"
        f"{_local_runtime_blocker_table(blockers)}</section>"
    )


def cleanup_rerun_command_section(command: list[str]) -> str:
    if not command:
        return (
            '<section class="panel"><h2>Cleanup Rerun Command</h2>'
            '<p class="note">No cleanup rerun command recorded. Use --rerun-cleanup with '
            "--execute-probes to record one.</p></section>"
        )
    command_text = " ".join(str(part) for part in command)
    return (
        '<section class="panel"><h2>Cleanup Rerun Command</h2>'
        '<p class="note">This command consumes generated proof run results as a bundle.</p>'
        f"<pre><code>{html.escape(command_text)}</code></pre></section>"
    )


def cleanup_rerun_artifact_section(cleanup_rerun: dict[str, Any]) -> str:
    if not cleanup_rerun:
        return (
            '<section class="panel"><h2>Cleanup Rerun Artifact</h2>'
            '<p class="note">No cleanup rerun artifact recorded.</p></section>'
        )
    return (
        '<section class="panel cleanup-rerun-artifact">'
        "<h2>Cleanup Rerun Artifact</h2>"
        '<p class="note">Final cleanup rerun outputs produced after proof commands '
        "have generated strict planner proof run results.</p>"
        + _path_table(
            [
                ("Cleanup rerun output", cleanup_rerun.get("output_dir", "")),
                ("Cleanup rerun run result", cleanup_rerun.get("run_result", "")),
                ("Cleanup rerun report", cleanup_rerun.get("report", "")),
            ]
        )
        + "</section>"
    )


def proof_bundle_results_section(
    summary: dict[str, Any],
    *,
    output_dir: Path | None = None,
    title: str = "Proof Probe Results",
    section_class: str = "proof-bundle-results",
    default_note: str = (
        "Bundle-level proof result summary. Strict per-proof checkers remain authoritative."
    ),
) -> str:
    if not summary:
        return ""
    results = summary.get("results") or []
    planner_backed_count = _summary_metric(summary, results, "planner_backed_count")
    config_import_timeout_count = _summary_config_import_timeout_count(summary, results)
    binding_promoted_count = _summary_metric(summary, results, "cleanup_binding_promoted_count")
    execution_attempted_count = _summary_metric(summary, results, "execution_attempted_count")
    proof_quality_summary = summary.get("proof_quality_summary") or planner_proof_quality_summary(
        item for item in results if item.get("run_result_exists")
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Expected', summary.get('expected_count', len(results)))}"
        f"{_metric('Results', summary.get('result_count', 0))}"
        f"{_metric('Planner-backed', planner_backed_count)}"
        f"{_metric('Proof Quality', format_quality_tier_counts(proof_quality_summary))}"
        f"{_metric('Timeouts', _summary_timeout_count(summary, results))}"
        f"{_metric('Config-import timeouts', config_import_timeout_count)}"
        f"{_metric('Binding promoted', binding_promoted_count)}"
        f"{_metric('Execution attempted', execution_attempted_count)}"
        f"{_metric('Task-feasible blocked', _summary_task_blocked_count(summary, results))}"
        f"{_metric('Grasp-feasible blocked', _summary_grasp_blocked_count(summary, results))}"
        f"{_metric('Worker stage events', _summary_worker_stage_event_count(summary, results))}"
        f"{_metric('Views', _summary_view_artifact_count(summary, results))}"
        "</div>"
    )
    stage_counts = _last_worker_stage_counts_text(summary.get("last_worker_stage_counts") or {})
    stage_counts_html = (
        f'<p class="note">Last worker stages: {html.escape(stage_counts)}</p>'
        if stage_counts
        else ""
    )
    grasp_signature_html = _proof_bundle_grasp_signature_section(
        _summary_grasp_signature_counts(summary, results)
    )
    proof_quality_html = _proof_bundle_quality_summary_section(proof_quality_summary)
    body = (
        "".join(_proof_bundle_result_card(item, output_dir=output_dir) for item in results)
        if results
        else '<p class="note">No proof result rows recorded.</p>'
    )
    note = summary.get("evidence_note") or default_note
    return (
        f'<section class="panel {html.escape(section_class)}">'
        f"<h2>{html.escape(title)}</h2>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}{stage_counts_html}'
        f"{proof_quality_html}{grasp_signature_html}{body}</section>"
    )


def _command_semantic_subphases(item: dict[str, Any]) -> str:
    subphases = item.get("semantic_subphases") or []
    if not subphases:
        return ""
    rail_items = []
    for subphase in subphases:
        if not isinstance(subphase, dict):
            continue
        label = str(subphase.get("label") or "")
        detail = str(subphase.get("detail") or "")
        phase = str(subphase.get("phase") or "")
        rail_items.append(
            "<li>"
            f"<span>{html.escape(label)}</span>"
            f"<small>{html.escape(detail)} / {html.escape(phase)}</small>"
            "</li>"
        )
    if not rail_items:
        return ""
    return '<ol class="phase-rail command-phase-rail">' + "".join(rail_items) + "</ol>"


def _proof_execution_horizon_metrics(horizon: dict[str, Any]) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', horizon.get('status', 'unknown'))}"
        f"{_metric('Command steps', horizon.get('command_steps', 0))}"
        f"{_metric('Command target', horizon.get('command_quality_target', 'unknown'))}"
        f"{_metric('Coverage min steps', horizon.get('prior_covered_min_proof_steps', 1))}"
        f"{_metric('Coverage floor', horizon.get('prior_covered_quality_floor', 'unknown'))}"
        "</div>"
    )


def _grasp_mitigation_metrics(
    decision: dict[str, Any],
    missing_assets: str,
    exception_types: str,
) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', decision.get('status', 'unknown'))}"
        f"{_metric('Primary route', decision.get('primary_route', 'unknown'))}"
        f"{_metric('Source rotation', decision.get('source_rotation_state', 'unknown'))}"
        f"{_metric('Selected requests', decision.get('selected_request_count', 0))}"
        f"{_metric('Excluded requests', decision.get('excluded_request_count', 0))}"
        f"{_metric('Signature groups', decision.get('signature_group_count', 0))}"
        f"{_metric('Missing assets', missing_assets or 'none')}"
        f"{_metric('Exception types', exception_types or 'none')}"
        "</div>"
    )


def _local_runtime_metrics(
    preflight: dict[str, Any],
    checks: list[dict[str, Any]],
    blockers: list[Any],
) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Requested', _yes_no(preflight.get('requested')))}"
        f"{_metric('Checks', len(checks))}"
        f"{_metric('Blockers', len(blockers))}"
        "</div>"
    )


def _local_runtime_check_table(checks: list[dict[str, Any]]) -> str:
    check_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('name', '')))}</td>"
        f"<td>{html.escape(str(item.get('status', '')))}</td>"
        f"<td>{html.escape(' '.join(str(part) for part in item.get('command') or []))}</td>"
        f"<td>{html.escape(str(item.get('returncode', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in checks
    )
    if not check_rows:
        return ""
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Check</th><th>Status</th><th>Command</th><th>Return code</th><th>Message</th>"
        f"</tr></thead><tbody>{check_rows}</tbody></table></div>"
    )


def _local_runtime_blocker_table(blockers: list[Any]) -> str:
    blocker_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('code', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in blockers
        if isinstance(item, dict)
    )
    if not blocker_rows:
        return ""
    return (
        '<div class="table-wrap"><table><thead><tr><th>Blocker</th><th>Message</th></tr>'
        f"</thead><tbody>{blocker_rows}</tbody></table></div>"
    )


def _decision_card(title: str, value: Any, detail: Any) -> str:
    return (
        '<article class="decision-card">'
        f"<h3>{html.escape(str(title))}</h3>"
        f"<strong>{html.escape(str(value))}</strong>"
        f"<p>{html.escape(str(detail))}</p>"
        "</article>"
    )


def _proof_bundle_quality_summary_section(summary: dict[str, Any]) -> str:
    if not summary or int(summary.get("proof_count") or 0) == 0:
        return ""
    rows = [
        ("Proof quality tiers", format_quality_tier_counts(summary)),
        ("Lowest quality tier", summary.get("lowest_quality_tier", "")),
        ("Min steps", summary.get("min_steps_executed", "")),
        ("Max steps", summary.get("max_steps_executed", "")),
        ("Max qpos delta", summary.get("max_abs_qpos_delta", "")),
        ("Any containment proven", _yes_no(summary.get("any_containment_proven"))),
        ("All containment proven", _yes_no(summary.get("all_containment_proven"))),
    ]
    return "<h3>Planner Proof Quality</h3>" + _field_table(rows)


def _summary_metric(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    key: str,
) -> int:
    if key in summary:
        return int(summary.get(key) or 0)
    if key == "planner_backed_count":
        return sum(1 for item in results if item.get("planner_backed"))
    if key == "cleanup_binding_promoted_count":
        return sum(1 for item in results if item.get("cleanup_binding_promoted"))
    if key == "execution_attempted_count":
        return sum(1 for item in results if item.get("execution_attempted"))
    return 0


def _summary_timeout_count(summary: dict[str, Any], results: list[dict[str, Any]]) -> int:
    if "timeout_count" in summary:
        return int(summary.get("timeout_count") or 0)
    return sum(1 for item in results if _has_result_blocker_code(item, "timeout"))


def _summary_config_import_timeout_count(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> int:
    if "rby1m_config_import_timeout_count" in summary:
        return int(summary.get("rby1m_config_import_timeout_count") or 0)
    return sum(
        1
        for item in results
        if _has_result_blocker_code(item, "timeout")
        and str(item.get("last_worker_stage") or "") == "rby1m_config_import"
    )


def _summary_task_blocked_count(summary: dict[str, Any], results: list[dict[str, Any]]) -> int:
    if "task_feasibility_blocked_count" in summary:
        return int(summary.get("task_feasibility_blocked_count") or 0)
    return sum(1 for item in results if str(item.get("task_feasibility_status") or "") == "blocked")


def _summary_grasp_blocked_count(summary: dict[str, Any], results: list[dict[str, Any]]) -> int:
    if "grasp_feasibility_blocked_count" in summary:
        return int(summary.get("grasp_feasibility_blocked_count") or 0)
    return sum(
        1
        for item in results
        if str(item.get("task_feasibility_blocker_kind") or "") == "grasp_feasibility"
    )


def _summary_worker_stage_event_count(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> int:
    if "worker_stage_event_count" in summary:
        return int(summary.get("worker_stage_event_count") or 0)
    return sum(int(item.get("worker_stage_event_count") or 0) for item in results)


def _summary_view_artifact_count(summary: dict[str, Any], results: list[dict[str, Any]]) -> int:
    if "view_artifact_count" in summary:
        return int(summary.get("view_artifact_count") or 0)
    return sum(len(item.get("views") or []) for item in results)


def _summary_grasp_signature_counts(
    summary: dict[str, Any],
    results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    signatures = summary.get("grasp_feasibility_signature_counts") or []
    if signatures:
        return [item for item in signatures if isinstance(item, dict)]
    return grasp_feasibility_signature_counts(results)


def _proof_bundle_grasp_signature_section(signatures: list[dict[str, Any]]) -> str:
    rows = []
    for item in signatures:
        if not isinstance(item, dict):
            continue
        missing_grasp_assets = ", ".join(
            str(v) for v in item.get("grasp_load_exception_asset_uids") or []
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('count', '')))}</td>"
            f"<td>{html.escape(str(item.get('subkind', '')))}</td>"
            f"<td>{html.escape(str(item.get('summary', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate_effective_removal_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate_name_miss_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('grasp_load_failure_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('grasp_collision_check_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('zero_noncolliding_grasp_check_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('robot_placement_failure_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('place_robot_near_call_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('image_artifact_count', '')))}</td>"
            f"<td>{html.escape(', '.join(str(v) for v in item.get('request_ids') or []))}</td>"
            f"<td>{html.escape(', '.join(str(v) for v in item.get('object_names') or []))}</td>"
            f"<td>{html.escape(missing_grasp_assets)}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        "<h3>Grasp Feasibility Signature Matrix</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Proofs</th><th>Subkind</th><th>Pattern</th><th>Effective removals</th>"
        "<th>Candidate name misses</th><th>Grasp-load failures</th>"
        "<th>Collision checks</th><th>Zero non-colliding checks</th>"
        "<th>Robot placement failures</th>"
        "<th>place_robot_near calls</th><th>Diagnostic views</th>"
        "<th>Requests</th><th>Planner objects</th><th>Missing grasp assets</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _has_result_blocker_code(item: dict[str, Any], code: str) -> bool:
    blockers = [*(item.get("blockers") or []), *(item.get("cleanup_binding_blockers") or [])]
    return any(
        isinstance(blocker, dict) and str(blocker.get("code") or "") == code for blocker in blockers
    )


def _proof_bundle_result_card(item: dict[str, Any], *, output_dir: Path | None = None) -> str:
    blockers = list(item.get("blockers") or [])
    binding_blockers = list(item.get("cleanup_binding_blockers") or [])
    blocker_text = ", ".join(
        str(blocker.get("code") or blocker.get("message") or "")
        for blocker in [*blockers, *binding_blockers]
        if isinstance(blocker, dict)
    )
    requested = item.get("requested_cleanup_primitive_binding") or {}
    sampled = item.get("sampled_task_binding") or {}
    config = item.get("cleanup_task_config") or {}
    config_blockers = _blocker_codes(config.get("blockers") or [])
    robot_placement_profile = item.get("task_sampler_robot_placement_profile") or {}
    robot_placement_overrides = robot_placement_profile.get("place_robot_near_overrides") or {}
    sampler_adapter = item.get("cleanup_task_sampler_adapter") or {}
    pickup_binding = sampler_adapter.get("exact_pickup_candidate_binding") or {}
    task_sampler_failure = item.get("task_sampler_failure_diagnostics") or {}
    last_robot_failure = task_sampler_failure.get("last_robot_placement_failure") or {}
    last_scene_diagnostic = task_sampler_failure.get("last_placement_scene_diagnostic") or {}
    last_grasp_load = task_sampler_failure.get("last_grasp_load_attempt") or {}
    last_grasp_collision = task_sampler_failure.get("last_grasp_collision_check") or {}
    grasp_signature = item.get("grasp_feasibility_signature") or {}
    grasp_failures = task_sampler_failure.get("grasp_failures") or []
    candidate_effective_removals = task_sampler_failure.get(
        "candidate_effective_removal_count",
        "",
    )
    candidate_name_misses = task_sampler_failure.get("candidate_name_miss_count", "")
    missing_grasp_assets = ", ".join(
        str(value) for value in grasp_signature.get("grasp_load_exception_asset_uids") or []
    )
    grasp_load_exception_types = ", ".join(
        str(value) for value in grasp_signature.get("grasp_load_exception_types") or []
    )
    rows = [
        ("Request", item.get("request_id", "")),
        ("Object", item.get("object_id", "")),
        ("Target", item.get("target_receptacle_id", "")),
        ("Status", item.get("status", "")),
        ("Proof quality", (item.get("proof_quality") or {}).get("quality_tier", "")),
        ("Steps executed", item.get("steps_executed", "")),
        ("Qpos delta", item.get("max_abs_qpos_delta", "")),
        (
            "Containment proven",
            _yes_no((item.get("proof_quality") or {}).get("containment_proven")),
        ),
        ("Task feasibility", item.get("task_feasibility_status", "")),
        ("Task feasibility blocker", item.get("task_feasibility_blocker_kind", "")),
        ("Task feasibility detail", item.get("task_feasibility_blocker_summary", "")),
        ("Cleanup binding promoted", _yes_no(item.get("cleanup_binding_promoted"))),
        ("Execution attempted", _yes_no(item.get("execution_attempted"))),
        ("Last worker stage", item.get("last_worker_stage", "")),
        ("Worker stage events", item.get("worker_stage_event_count", "")),
        ("Worker stages", _worker_stage_summary(item.get("worker_stage_events") or [])),
        ("Probe stdout", item.get("stdout", "")),
        ("Probe stderr", item.get("stderr", "")),
        ("Proof run result", item.get("run_result", "")),
        ("Proof report", item.get("report", "")),
        ("Requested scene XML", requested.get("scene_xml", "") or config.get("scene_xml", "")),
        ("Exact task config blockers", config_blockers),
        ("Robot placement profile", robot_placement_profile.get("profile", "")),
        ("Robot placement profile applied", _yes_no(robot_placement_profile.get("applied"))),
        ("place_robot_near max tries", robot_placement_overrides.get("max_tries", "")),
        ("Exact sampler adapter applied", _yes_no(sampler_adapter.get("applied"))),
        ("Exact sampler adapter class", sampler_adapter.get("task_sampler_class", "")),
        ("Exact sampler adapter object", sampler_adapter.get("planner_object_id", "")),
        ("Exact sampler adapter target", sampler_adapter.get("planner_target_receptacle_id", "")),
        ("Exact pickup candidate action", pickup_binding.get("action", "")),
        ("Exact pickup retry budget", pickup_binding.get("retry_budget", "")),
        ("Exact pickup retry budget applied", _yes_no(pickup_binding.get("retry_budget_applied"))),
        (
            "Exact pickup requested present before",
            _yes_no(pickup_binding.get("requested_present_before")),
        ),
        ("Exact pickup candidates before", pickup_binding.get("candidate_count_before", "")),
        ("Exact pickup candidates after", pickup_binding.get("candidate_count_after", "")),
        (
            "Task sampler placement attempts",
            task_sampler_failure.get("robot_placement_attempt_count", ""),
        ),
        (
            "Task sampler placement failures",
            task_sampler_failure.get("robot_placement_failure_count", ""),
        ),
        ("Placement valid free points", last_scene_diagnostic.get("valid_free_point_count", "")),
        (
            "Placement free-space fraction",
            _format_fraction(last_scene_diagnostic.get("valid_neighborhood_fraction", "")),
        ),
        (
            "Placement nearest free distance",
            last_scene_diagnostic.get("nearest_free_point_distance_m", ""),
        ),
        ("Task sampler asset failures", task_sampler_failure.get("asset_failure_count", "")),
        ("Grasp feasibility subkind", grasp_signature.get("subkind", "")),
        ("Grasp load attempts", task_sampler_failure.get("grasp_load_attempt_count", "")),
        (
            "Grasp load failures",
            grasp_signature.get("grasp_load_failure_count")
            or task_sampler_failure.get("grasp_load_failure_count", ""),
        ),
        ("Missing grasp assets", missing_grasp_assets),
        ("Grasp load exception types", grasp_load_exception_types),
        ("Grasp load cached grasps", last_grasp_load.get("cached_grasp_count", "")),
        ("Grasp collision checks", task_sampler_failure.get("grasp_collision_check_count", "")),
        (
            "Zero non-colliding grasp checks",
            grasp_signature.get("zero_noncolliding_grasp_check_count")
            or task_sampler_failure.get("zero_noncolliding_grasp_check_count", ""),
        ),
        ("Grasp collision asset", last_grasp_collision.get("asset_uid", "")),
        (
            "Grasp collision non-colliding",
            last_grasp_collision.get("noncolliding_grasp_count", ""),
        ),
        ("Grasp collision total", last_grasp_collision.get("grasp_pose_count", "")),
        (
            "Grasp collision zero non-colliding",
            _yes_no(last_grasp_collision.get("zero_noncolliding")) if last_grasp_collision else "",
        ),
        ("Post-placement grasp failures", task_sampler_failure.get("grasp_failure_count", "")),
        ("Post-placement removal calls", task_sampler_failure.get("candidate_removal_count", "")),
        ("Post-placement effective removals", candidate_effective_removals),
        ("Post-placement candidate name misses", candidate_name_misses),
        ("Post-placement rejection rows", len(grasp_failures)),
        ("Task sampler last failure", last_robot_failure.get("message", "")),
        ("Planner object alias", requested.get("planner_object_id", "")),
        ("Planner target alias", requested.get("planner_target_receptacle_id", "")),
        ("Sampled pickup", sampled.get("pickup_obj_name", "")),
        (
            "Sampled target",
            sampled.get("place_receptacle_name") or sampled.get("place_target_name") or "",
        ),
        ("Blockers", blocker_text),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in (None, "", [], {})
    )
    views = item.get("views") or []
    if views:
        figures = "".join(
            _view_figure(
                _report_asset_src(view.get("path"), output_dir),
                f"{item.get('request_id', '')} "
                f"{planner_probe_image_artifact_label(view.get('label', ''))}",
            )
            for view in views
            if isinstance(view, dict)
        )
        view_html = (
            f'<div class="views">{figures}</div>'
            f"{planner_probe_post_placement_rejection_views(task_sampler_failure)}"
        )
    elif task_sampler_failure:
        view_html = (
            f"{planner_probe_task_sampler_diagnostic_views(task_sampler_failure)}"
            f"{planner_probe_post_placement_rejection_views(task_sampler_failure)}"
        )
    else:
        view_html = (
            '<p class="note">No planner probe views recorded'
            f" ({html.escape(str(item.get('visual_status', 'unknown')))}).</p>"
        )
    return (
        '<article class="proof-result">'
        f"<h3>{html.escape(str(item.get('request_id') or 'proof result'))}</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th>'
        f"</tr></thead><tbody>{table_rows}</tbody></table></div>{view_html}</article>"
    )


def _blocker_codes(blockers: list[dict[str, Any]]) -> str:
    return ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in blockers
        if isinstance(item, dict)
    )


def _last_worker_stage_counts_text(counts: dict[str, Any]) -> str:
    if not isinstance(counts, dict):
        return ""
    parts = []
    for stage, count in sorted(counts.items()):
        if stage:
            parts.append(f"{stage}={count}")
    return ", ".join(parts)


def _worker_stage_summary(events: list[dict[str, Any]]) -> str:
    parts = []
    for item in events:
        if not isinstance(item, dict):
            continue
        event = str(item.get("event") or "")
        stage = str(item.get("stage") or "")
        label = " -> ".join(dict.fromkeys(part for part in (event, stage) if part))
        elapsed = item.get("elapsed_s")
        if elapsed not in (None, ""):
            label = f"{label} ({elapsed}s)" if label else f"{elapsed}s"
        if label:
            parts.append(label)
    return "; ".join(parts)


def _format_fraction(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


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


def _review_image(path: Any, alt: str) -> str:
    if not path:
        return ""
    return f'<img src="{html.escape(str(path))}" alt="{html.escape(alt)}">'


def _report_asset_src(path: Any, output_dir: Path | None) -> str:
    if not path:
        return ""
    path_text = str(path)
    if output_dir is None or path_text.startswith(("http://", "https://", "data:")):
        return path_text
    candidate = Path(path_text)
    try:
        if candidate.is_absolute():
            asset_path = candidate
        elif candidate.exists():
            asset_path = candidate.resolve()
        elif (output_dir / candidate).exists():
            asset_path = (output_dir / candidate).resolve()
        else:
            return path_text
        return Path(os.path.relpath(asset_path, output_dir.resolve())).as_posix()
    except OSError:
        return path_text


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _field_table(rows: list[tuple[str, Any]]) -> str:
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    if not table_rows:
        return ""
    return (
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
    )


def _path_table(rows: list[tuple[str, Any]]) -> str:
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return (
        '<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>Path</th>'
        "</tr></thead><tbody>" + table_rows + "</tbody></table></div>"
    )


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"

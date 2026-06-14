from __future__ import annotations

import html
from typing import Any


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

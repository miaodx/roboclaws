from __future__ import annotations

import html
from typing import Any


def grasp_cache_generation_report_sections(result: dict[str, Any]) -> list[str]:
    return [
        _grasp_cache_generation_summary_section(result),
        _grasp_cache_generation_assets_section(result.get("assets") or []),
        _grasp_cache_generation_command_section(result),
        _grasp_cache_generation_blockers_section(result.get("blockers") or []),
    ]


def grasp_pose_policy_cache_report_sections(result: dict[str, Any]) -> list[str]:
    return [
        _grasp_pose_policy_cache_summary_section(result),
        _grasp_pose_policy_cache_policy_section(result.get("pose_policy") or {}),
        _grasp_pose_policy_cache_artifacts_section(result),
        _grasp_cache_generation_assets_section(result.get("assets") or []),
        _grasp_cache_generation_command_section(result),
        _grasp_cache_generation_blockers_section(result.get("blockers") or []),
    ]


def grasp_filter_diagnostics_report_sections(result: dict[str, Any]) -> list[str]:
    return [
        _grasp_filter_diagnostics_summary_section(result),
        _grasp_filter_diagnostics_artifacts_section(result),
        _grasp_filter_diagnostics_variants_section(result.get("variants") or []),
        _grasp_filter_diagnostics_blockers_section(result.get("blockers") or []),
    ]


def grasp_initial_contact_diagnostics_report_sections(result: dict[str, Any]) -> list[str]:
    return [
        _grasp_initial_contact_summary_section(result),
        _grasp_initial_contact_artifacts_section(result),
        _grasp_initial_contact_variants_section(result.get("variants") or []),
        _grasp_initial_contact_samples_section(result.get("best_variant") or {}),
        _grasp_initial_contact_blockers_section(result.get("blockers") or []),
    ]


def _grasp_cache_generation_summary_section(result: dict[str, Any]) -> str:
    return (
        '<section class="summary grasp-cache-generation-result">'
        '<div class="summary-head">'
        '<p class="eyebrow">Grasp cache generation artifact</p>'
        "<h1>MolmoSpaces Grasp Cache Generation</h1>"
        "</div>"
        '<div class="metric-grid">'
        f"{_metric('Status', result.get('status', ''))}"
        f"{_metric('Assets', result.get('asset_count', 0))}"
        f"{_metric('Blockers', result.get('blocker_count', 0))}"
        f"{_metric('Ready', _yes_no(result.get('ready')))}"
        "</div>"
        '<div class="badges">'
        f"{_badge('Schema', result.get('schema', 'unknown'))}"
        f"{_badge('Objects list', result.get('objects_list_path', ''))}"
        f"{_badge('Assets symlink', _assets_symlink_summary(result.get('assets_symlink') or {}))}"
        "</div>"
        f'<p class="note">{html.escape(str(result.get("evidence_note") or ""))}</p>'
        "</section>"
    )


def _grasp_cache_generation_assets_section(assets: list[dict[str, Any]]) -> str:
    rows = []
    for asset in assets:
        generated = asset.get("generated_validation") or {}
        installed = asset.get("installed_validation") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(asset.get('asset_uid', '')))}</td>"
            f"<td>{html.escape(str(generated.get('validation_status', '')))}</td>"
            f"<td>{html.escape(str(generated.get('transform_count', 0)))}</td>"
            f"<td>{html.escape(_yes_no(asset.get('installed')))}</td>"
            f"<td>{html.escape(str(installed.get('validation_status', '')))}</td>"
            f"<td>{html.escape(str(installed.get('transform_count', 0)))}</td>"
            f"<td>{html.escape(str(asset.get('generated_npz_path', '')))}</td>"
            f"<td>{html.escape(str(asset.get('cache_target_path', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        '<section class="panel grasp-cache-generation-assets">'
        "<h2>Generated Cache Assets</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Generated status</th><th>Generated transforms</th>"
        "<th>Installed</th><th>Installed status</th><th>Installed transforms</th>"
        "<th>Generated NPZ</th><th>Cache target</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_cache_generation_command_section(result: dict[str, Any]) -> str:
    command = " ".join(str(part) for part in result.get("command") or [])
    command_result = result.get("command_result") or {}
    if not command:
        return ""
    rows = [
        ("Command status", command_result.get("status", "")),
        ("Return code", command_result.get("returncode", "")),
        ("Stdout tail", _tail_text(command_result.get("stdout", ""), limit=1600)),
        ("Stderr tail", _tail_text(command_result.get("stderr", ""), limit=1600)),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    return (
        '<section class="panel grasp-cache-generation-command">'
        "<h2>Generation Command</h2>"
        f"<pre><code>{html.escape(command)}</code></pre>"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        "</section>"
    )


def _grasp_cache_generation_blockers_section(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return (
            '<section class="panel"><h2>Generation Blockers</h2>'
            '<p class="note">No generation blockers recorded.</p></section>'
        )
    rows = []
    for blocker in blockers:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(blocker.get('code', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('asset_uid', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
            "</tr>"
        )
    return (
        '<section class="panel grasp-cache-generation-blockers">'
        "<h2>Generation Blockers</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Code</th><th>Asset</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_filter_diagnostics_summary_section(result: dict[str, Any]) -> str:
    return (
        '<section class="summary grasp-filter-diagnostics-result">'
        '<div class="summary-head">'
        '<p class="eyebrow">Grasp filter diagnostic artifact</p>'
        "<h1>MolmoSpaces Grasp Filter Diagnostics</h1>"
        "</div>"
        '<div class="metric-grid">'
        f"{_metric('Status', result.get('status', ''))}"
        f"{_metric('Object', result.get('object_name', ''))}"
        f"{_metric('Variants', result.get('variant_count', 0))}"
        f"{_metric('Successful', result.get('successful_variant_count', 0))}"
        f"{_metric('Blockers', result.get('blocker_count', 0))}"
        "</div>"
        '<div class="badges">'
        f"{_badge('Schema', result.get('schema', 'unknown'))}"
        f"{_badge('Object XML', result.get('object_xml', ''))}"
        f"{_badge('Artifacts', result.get('artifact_dir', ''))}"
        f"{_badge('Assets symlink', _assets_symlink_summary(result.get('assets_symlink') or {}))}"
        "</div>"
        f'<p class="note">{html.escape(str(result.get("evidence_note") or ""))}</p>'
        "</section>"
    )


def _grasp_filter_diagnostics_artifacts_section(result: dict[str, Any]) -> str:
    pipeline = result.get("pipeline") or {}
    subset = result.get("candidate_subset") or {}
    rows = [
        ("Pipeline source", pipeline.get("source", "")),
        ("Candidate grasps", pipeline.get("candidate_grasps_path", "")),
        ("Candidate count", pipeline.get("candidate_count", "")),
        ("Subset grasps", subset.get("subset_path", "")),
        ("Requested subset", subset.get("requested_sample_size", "")),
        ("Subset count", subset.get("subset_count", "")),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    command_rows = []
    for command in pipeline.get("commands") or []:
        result_row = command.get("result") or {}
        command_text = " ".join(str(part) for part in command.get("command") or [])
        output_tail = _tail_text(result_row.get("stderr") or result_row.get("stdout"), limit=500)
        command_rows.append(
            "<tr>"
            f"<td>{html.escape(str(command.get('stage', '')))}</td>"
            f"<td>{html.escape(str(result_row.get('status', '')))}</td>"
            f"<td>{html.escape(str(result_row.get('returncode', '')))}</td>"
            f"<td><code>{html.escape(command_text)}</code></td>"
            f"<td>{html.escape(output_tail)}</td>"
            "</tr>"
        )
    command_table = ""
    if command_rows:
        command_table = (
            '<div class="table-wrap"><table><thead><tr>'
            "<th>Stage</th><th>Status</th><th>Return</th><th>Command</th><th>Output tail</th>"
            f"</tr></thead><tbody>{''.join(command_rows)}</tbody></table></div>"
        )
    return (
        '<section class="panel grasp-filter-diagnostics-artifacts">'
        "<h2>Diagnostic Artifacts</h2>"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        f"{command_table}"
        "</section>"
    )


def _grasp_filter_diagnostics_variants_section(variants: list[dict[str, Any]]) -> str:
    if not variants:
        return ""
    rows = []
    for variant in variants:
        validation = variant.get("validation") or {}
        command_result = variant.get("command_result") or {}
        output_tail = _tail_text(
            command_result.get("stderr") or command_result.get("stdout"), limit=500
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(variant.get('name', '')))}</td>"
            f"<td>{html.escape(str(variant.get('classification', '')))}</td>"
            f"<td>{html.escape(str(variant.get('num_shakes', '')))}</td>"
            f"<td>{html.escape(_yes_no(variant.get('rotate')))}</td>"
            f"<td>{html.escape(str(variant.get('successful_transform_count', 0)))}</td>"
            f"<td>{html.escape(str(validation.get('validation_status', '')))}</td>"
            f"<td>{html.escape(str(variant.get('output_npz_path', '')))}</td>"
            f"<td>{html.escape(output_tail)}</td>"
            "</tr>"
        )
    return (
        '<section class="panel grasp-filter-diagnostics-variants">'
        "<h2>Filter Variants</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Variant</th><th>Classification</th><th>Shakes</th><th>Rotate</th>"
        "<th>Successful transforms</th><th>NPZ status</th><th>Output NPZ</th><th>Output tail</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_filter_diagnostics_blockers_section(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return (
            '<section class="panel"><h2>Filter Diagnostic Blockers</h2>'
            '<p class="note">No filter diagnostic blockers recorded.</p></section>'
        )
    rows = []
    for blocker in blockers:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(blocker.get('code', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('variant', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
            "</tr>"
        )
    return (
        '<section class="panel grasp-filter-diagnostics-blockers">'
        "<h2>Filter Diagnostic Blockers</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Code</th><th>Variant</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_pose_policy_cache_summary_section(result: dict[str, Any]) -> str:
    policy = result.get("pose_policy") or {}
    return (
        '<section class="summary grasp-pose-policy-cache-result">'
        '<div class="summary-head">'
        '<p class="eyebrow">Pose-policy cache artifact</p>'
        "<h1>MolmoSpaces Pose Policy Grasp Cache</h1>"
        "</div>"
        '<div class="metric-grid">'
        f"{_metric('Status', result.get('status', ''))}"
        f"{_metric('Object', result.get('object_name', ''))}"
        f"{_metric('Candidates', result.get('candidate_count', 0))}"
        f"{_metric('Generated transforms', result.get('successful_transform_count', 0))}"
        f"{_metric('Installed', _yes_no((result.get('assets') or [{}])[0].get('installed')))}"
        f"{_metric('Blockers', result.get('blocker_count', 0))}"
        "</div>"
        '<div class="badges">'
        f"{_badge('Schema', result.get('schema', 'unknown'))}"
        f"{_badge('Policy', policy.get('name', ''))}"
        f"{_badge('Install requested', _yes_no(result.get('install_requested')))}"
        f"{_badge('Assets symlink', _assets_symlink_summary(result.get('assets_symlink') or {}))}"
        "</div>"
        f'<p class="note">{html.escape(str(result.get("evidence_note") or ""))}</p>'
        "</section>"
    )


def _grasp_pose_policy_cache_policy_section(policy: dict[str, Any]) -> str:
    if not policy:
        return ""
    rows = [
        ("Policy name", policy.get("name", "")),
        ("Source", policy.get("source", "")),
        ("Approach sign", policy.get("approach_sign", "")),
        ("Approach distance", policy.get("approach_distance", "")),
        ("Settle steps", policy.get("settle_steps", "")),
        ("Source success count", policy.get("source_success_count", "")),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    return (
        '<section class="panel grasp-pose-policy-cache-policy">'
        "<h2>Pose Policy</h2>"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        "</section>"
    )


def _grasp_pose_policy_cache_artifacts_section(result: dict[str, Any]) -> str:
    command_result = result.get("command_result") or {}
    rows = [
        ("Candidate grasps", result.get("candidate_grasps_path", "")),
        ("Object XML", result.get("object_xml", "")),
        ("Artifact dir", result.get("artifact_dir", "")),
        ("Probe script", result.get("probe_script_path", "")),
        ("Probe result", result.get("probe_output_path", "")),
        ("Generated NPZ", result.get("generated_npz_path", "")),
        ("Command status", command_result.get("status", "")),
        ("Command return", command_result.get("returncode", "")),
        (
            "Command output tail",
            _tail_text(command_result.get("stderr") or command_result.get("stdout"), limit=500),
        ),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    return (
        '<section class="panel grasp-pose-policy-cache-artifacts">'
        "<h2>Cache Artifacts</h2>"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        "</section>"
    )


def _grasp_initial_contact_summary_section(result: dict[str, Any]) -> str:
    best = result.get("best_variant") or {}
    return (
        '<section class="summary grasp-initial-contact-result">'
        '<div class="summary-head">'
        '<p class="eyebrow">Grasp initial-contact artifact</p>'
        "<h1>MolmoSpaces Grasp Initial Contact Diagnostics</h1>"
        "</div>"
        '<div class="metric-grid">'
        f"{_metric('Status', result.get('status', ''))}"
        f"{_metric('Object', result.get('object_name', ''))}"
        f"{_metric('Candidates', result.get('candidate_count', 0))}"
        f"{_metric('Variants', result.get('variant_count', 0))}"
        f"{_metric('Successful variants', result.get('successful_variant_count', 0))}"
        f"{_metric('Best success', best.get('success_count', 0))}"
        "</div>"
        '<div class="badges">'
        f"{_badge('Schema', result.get('schema', 'unknown'))}"
        f"{_badge('Best variant', best.get('name', ''))}"
        f"{_badge('Best sign', best.get('approach_sign', ''))}"
        f"{_badge('Best distance', best.get('approach_distance', ''))}"
        f"{_badge('Best settle', best.get('settle_steps', ''))}"
        f"{_badge('Assets symlink', _assets_symlink_summary(result.get('assets_symlink') or {}))}"
        "</div>"
        f'<p class="note">{html.escape(str(result.get("evidence_note") or ""))}</p>'
        "</section>"
    )


def _grasp_initial_contact_artifacts_section(result: dict[str, Any]) -> str:
    command_result = result.get("command_result") or {}
    rows = [
        ("Candidate grasps", result.get("candidate_grasps_path", "")),
        ("Object XML", result.get("object_xml", "")),
        ("Artifact dir", result.get("artifact_dir", "")),
        ("Probe script", result.get("probe_script_path", "")),
        ("Probe result", result.get("probe_output_path", "")),
        ("Command status", command_result.get("status", "")),
        ("Command return", command_result.get("returncode", "")),
        (
            "Command output tail",
            _tail_text(command_result.get("stderr") or command_result.get("stdout"), limit=500),
        ),
    ]
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
        if value not in ("", None)
    )
    command = " ".join(str(part) for part in result.get("command") or [])
    command_html = f'<p class="note"><code>{html.escape(command)}</code></p>' if command else ""
    return (
        '<section class="panel grasp-initial-contact-artifacts">'
        "<h2>Diagnostic Artifacts</h2>"
        f"{command_html}"
        '<div class="table-wrap"><table><thead><tr><th>Field</th><th>Value</th></tr></thead>'
        f"<tbody>{table_rows}</tbody></table></div>"
        "</section>"
    )


def _grasp_initial_contact_variants_section(variants: list[dict[str, Any]]) -> str:
    if not variants:
        return ""
    rows = []
    for variant in variants:
        successful_indices = ", ".join(
            str(i) for i in variant.get("successful_candidate_indices") or []
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(variant.get('name', '')))}</td>"
            f"<td>{html.escape(str(variant.get('classification', '')))}</td>"
            f"<td>{html.escape(str(variant.get('approach_sign', '')))}</td>"
            f"<td>{html.escape(str(variant.get('approach_distance', '')))}</td>"
            f"<td>{html.escape(str(variant.get('settle_steps', '')))}</td>"
            f"<td>{html.escape(str(variant.get('candidate_count', 0)))}</td>"
            f"<td>{html.escape(str(variant.get('success_count', 0)))}</td>"
            f"<td>{html.escape(str(variant.get('initial_contact_count', 0)))}</td>"
            f"<td>{html.escape(str(variant.get('initial_displaced_count', 0)))}</td>"
            f"<td>{html.escape(str(variant.get('avg_initial_displacement_m', 0.0)))}</td>"
            f"<td>{html.escape(str(variant.get('max_initial_displacement_m', 0.0)))}</td>"
            f"<td>{html.escape(successful_indices)}</td>"
            "</tr>"
        )
    return (
        '<section class="panel grasp-initial-contact-variants">'
        "<h2>Approach Variants</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Variant</th><th>Classification</th><th>Sign</th><th>Distance</th>"
        "<th>Settle</th><th>Candidates</th><th>Successes</th><th>Initial contacts</th>"
        "<th>Initial displaced</th><th>Avg initial move</th><th>Max initial move</th>"
        "<th>Successful candidates</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_initial_contact_samples_section(best: dict[str, Any]) -> str:
    rows = []
    for sample in best.get("sample_rows") or []:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(sample.get('candidate_index', '')))}</td>"
            f"<td>{html.escape(_yes_no(sample.get('success')))}</td>"
            f"<td>{html.escape(str(sample.get('initial_contact_sides', [])))}</td>"
            f"<td>{html.escape(str(sample.get('initial_contact_pair_count', 0)))}</td>"
            f"<td>{html.escape(str(sample.get('initial_displacement_m', 0.0)))}</td>"
            f"<td>{html.escape(str(sample.get('final_contact_sides', [])))}</td>"
            f"<td>{html.escape(str(sample.get('final_contact_pair_count', 0)))}</td>"
            f"<td>{html.escape(str(sample.get('final_displacement_m', 0.0)))}</td>"
            "</tr>"
        )
    if not rows:
        return ""
    return (
        '<section class="panel grasp-initial-contact-samples">'
        f"<h2>Best Variant Samples: {html.escape(str(best.get('name', '')))}</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Candidate</th><th>Success</th><th>Initial sides</th><th>Initial contacts</th>"
        "<th>Initial move</th><th>Final sides</th><th>Final contacts</th><th>Final move</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _grasp_initial_contact_blockers_section(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return (
            '<section class="panel"><h2>Initial Contact Blockers</h2>'
            '<p class="note">No initial-contact diagnostic blockers recorded.</p></section>'
        )
    rows = []
    for blocker in blockers:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(blocker.get('code', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
            "</tr>"
        )
    return (
        '<section class="panel grasp-initial-contact-blockers">'
        "<h2>Initial Contact Blockers</h2>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Code</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
        "</section>"
    )


def _assets_symlink_summary(symlink: dict[str, Any]) -> str:
    if not symlink:
        return ""
    return (
        f"{symlink.get('status', '')}; path={symlink.get('path', '')}; "
        f"target={symlink.get('target', '')}; created={_yes_no(symlink.get('created'))}"
    )


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _tail_text(value: Any, *, limit: int) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"

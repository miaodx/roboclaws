from __future__ import annotations

import html
from typing import Any


def grasp_cache_availability_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight:
        return ""
    asset_rows, candidate_rows, object_rows = _availability_rows(preflight)
    recommendation_html = _recommendation_note(preflight)
    note = preflight.get("evidence_note") or "Grasp cache availability preflight."
    return (
        '<section class="panel grasp-cache-preflight">'
        "<h2>Grasp Cache Availability Preflight</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f"{_availability_metrics(preflight)}{_availability_path_table(preflight)}"
        f"{recommendation_html}{_asset_status_table(asset_rows)}"
        f"{_loader_file_probe_table(candidate_rows)}{_object_asset_probe_table(object_rows)}"
        "</section>"
    )


def grasp_cache_generation_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight or preflight.get("status") == "not_applicable":
        return ""
    command = " ".join(str(part) for part in preflight.get("command") or [])
    command_html = f"<pre><code>{html.escape(command)}</code></pre>" if command else ""
    note = preflight.get("evidence_note") or "Grasp cache generation preflight."
    return (
        '<section class="panel grasp-cache-generation-preflight">'
        "<h2>Grasp Cache Generation Preflight</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f"{_generation_metrics(preflight)}{_recommendation_note(preflight)}"
        f"{_generation_path_table(preflight)}{_generation_asset_table(preflight)}"
        f"{_generation_check_table(preflight)}{_generation_blocker_table(preflight)}"
        f"<h3>Proposed Generation Command</h3>{command_html}</section>"
    )


def _availability_metrics(preflight: dict[str, Any]) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Assets', preflight.get('asset_count', 0))}"
        f"{_metric('Ready assets', preflight.get('ready_asset_count', 0))}"
        f"{_metric('Missing cache assets', preflight.get('missing_cache_asset_count', 0))}"
        f"{_metric('Assets dir source', preflight.get('assets_dir_source', 'unknown'))}"
        f"{_metric('Assets dir exists', preflight.get('assets_dir_exists', False))}"
        "</div>"
    )


def _availability_path_table(preflight: dict[str, Any]) -> str:
    return _path_table(
        [
            ("Assets dir", preflight.get("assets_dir", "")),
            ("Resolved assets dir", preflight.get("assets_dir_resolved", "")),
            ("Upstream loader", preflight.get("upstream_loader", "")),
        ]
    )


def _availability_rows(
    preflight: dict[str, Any],
) -> tuple[list[str], list[str], list[str]]:
    asset_rows: list[str] = []
    candidate_rows: list[str] = []
    object_rows: list[str] = []
    for asset in preflight.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_uid = str(asset.get("asset_uid") or "")
        asset_rows.append(_asset_status_row(asset_uid, asset))
        candidate_rows.extend(_candidate_probe_rows(asset_uid, asset))
        object_rows.extend(_object_asset_probe_rows(asset_uid, asset))
    return asset_rows, candidate_rows, object_rows


def _asset_status_row(asset_uid: str, asset: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(asset_uid)}</td>"
        f"<td>{html.escape(str(asset.get('status', '')))}</td>"
        f"<td>{html.escape(str(asset.get('loader_file_status', '')))}</td>"
        f"<td>{html.escape(str(asset.get('object_asset_status', '')))}</td>"
        "</tr>"
    )


def _candidate_probe_rows(asset_uid: str, asset: dict[str, Any]) -> list[str]:
    rows = []
    probes = [
        *(asset.get("candidate_grasp_files") or []),
        *(asset.get("folder_probe_files") or []),
    ]
    for probe in probes:
        if isinstance(probe, dict):
            rows.append(_candidate_probe_row(asset_uid, probe))
    return rows


def _candidate_probe_row(asset_uid: str, probe: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(asset_uid)}</td>"
        f"<td>{html.escape(str(probe.get('source', '')))}</td>"
        f"<td>{html.escape(str(probe.get('loader_role', '')))}</td>"
        f"<td>{html.escape(str(probe.get('exists', False)))}</td>"
        f"<td>{html.escape(str(probe.get('valid', '')))}</td>"
        f"<td>{html.escape(str(probe.get('transform_count', '')))}</td>"
        f"<td>{html.escape(str(probe.get('validation_status', '')))}</td>"
        f"<td>{html.escape(str(probe.get('size_bytes', 0)))}</td>"
        f"<td>{html.escape(str(probe.get('relative_path', '')))}</td>"
        f"<td>{html.escape(str(probe.get('resolved_path', '')))}</td>"
        "</tr>"
    )


def _object_asset_probe_rows(asset_uid: str, asset: dict[str, Any]) -> list[str]:
    rows = []
    for object_file in asset.get("object_asset_files") or []:
        if isinstance(object_file, dict):
            rows.append(_object_asset_probe_row(asset_uid, object_file))
    return rows


def _object_asset_probe_row(asset_uid: str, object_file: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(asset_uid)}</td>"
        f"<td>{html.escape(str(object_file.get('kind', '')))}</td>"
        f"<td>{html.escape(str(object_file.get('size_bytes', 0)))}</td>"
        f"<td>{html.escape(str(object_file.get('relative_path', '')))}</td>"
        f"<td>{html.escape(str(object_file.get('resolved_path', '')))}</td>"
        "</tr>"
    )


def _asset_status_table(rows: list[str]) -> str:
    if not rows:
        rows = ['<tr><td colspan="4">No missing grasp-cache assets.</td></tr>']
    return (
        '<h3>Asset Status</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Status</th><th>Rigid loader file</th><th>Object asset</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _loader_file_probe_table(rows: list[str]) -> str:
    if not rows:
        rows = ['<tr><td colspan="10">No grasp-cache file probes.</td></tr>']
    return (
        '<h3>Loader File Probes</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Source</th><th>Loader role</th><th>Exists</th>"
        "<th>Valid</th><th>Transforms</th><th>Validation</th><th>Bytes</th>"
        "<th>Relative path</th><th>Resolved path</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _object_asset_probe_table(rows: list[str]) -> str:
    if not rows:
        return ""
    return (
        '<h3>Object Asset Probes</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Kind</th><th>Bytes</th><th>Relative path</th>"
        "<th>Resolved path</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _generation_metrics(preflight: dict[str, Any]) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Assets', preflight.get('asset_count', 0))}"
        f"{_metric('Blockers', preflight.get('blocker_count', 0))}"
        f"{_metric('Ready', _yes_no(preflight.get('ready')))}"
        "</div>"
    )


def _generation_path_table(preflight: dict[str, Any]) -> str:
    return _path_table(
        [
            ("MolmoSpaces Python", preflight.get("molmospaces_python", "")),
            ("MolmoSpaces root", preflight.get("molmospaces_root", "")),
            ("Assets dir", preflight.get("assets_dir", "")),
            ("Objects list path", preflight.get("objects_list_path", "")),
            ("Working dir", preflight.get("working_dir", "")),
        ]
    )


def _generation_asset_table(preflight: dict[str, Any]) -> str:
    rows = [
        _generation_asset_row(asset)
        for asset in preflight.get("assets") or []
        if isinstance(asset, dict)
    ]
    if not rows:
        rows = ['<tr><td colspan="5">No grasp generation assets recorded.</td></tr>']
    return (
        '<h3>Generation Assets</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Object XML exists</th><th>Object XML</th>"
        "<th>Generated NPZ</th><th>Loader cache target</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _generation_asset_row(asset: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(asset.get('asset_uid', '')))}</td>"
        f"<td>{html.escape(str(asset.get('object_xml_exists', False)))}</td>"
        f"<td>{html.escape(str(asset.get('object_xml', '')))}</td>"
        f"<td>{html.escape(str(asset.get('generated_npz_path', '')))}</td>"
        f"<td>{html.escape(str(asset.get('cache_target_resolved_path', '')))}</td>"
        "</tr>"
    )


def _generation_check_table(preflight: dict[str, Any]) -> str:
    rows = [
        _generation_check_row(check)
        for check in preflight.get("checks") or []
        if isinstance(check, dict)
    ]
    if not rows:
        rows = ['<tr><td colspan="5">No generation checks recorded.</td></tr>']
    return (
        '<h3>Prerequisite Checks</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Check</th><th>Status</th><th>Code</th><th>Path</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _generation_check_row(check: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(check.get('name', '')))}</td>"
        f"<td>{html.escape(str(check.get('status', '')))}</td>"
        f"<td>{html.escape(str(check.get('code', '')))}</td>"
        f"<td>{html.escape(str(check.get('path') or check.get('resolved_path') or ''))}</td>"
        f"<td>{html.escape(str(check.get('message') or check.get('stderr') or ''))}</td>"
        "</tr>"
    )


def _generation_blocker_table(preflight: dict[str, Any]) -> str:
    rows = [
        _generation_blocker_row(blocker)
        for blocker in preflight.get("blockers") or []
        if isinstance(blocker, dict)
    ]
    if not rows:
        return '<p class="note">No generation blockers recorded.</p>'
    return (
        '<h3>Generation Blockers</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Code</th><th>Check</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def _generation_blocker_row(blocker: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(blocker.get('code', '')))}</td>"
        f"<td>{html.escape(str(blocker.get('name', '')))}</td>"
        f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
        "</tr>"
    )


def _recommendation_note(preflight: dict[str, Any]) -> str:
    recommendation = str(preflight.get("mitigation_recommendation") or "")
    if not recommendation:
        return ""
    return f'<p class="note">Recommendation: {html.escape(recommendation)}</p>'


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
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

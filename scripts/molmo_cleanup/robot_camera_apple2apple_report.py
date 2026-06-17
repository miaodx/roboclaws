from __future__ import annotations

import html
import json
from typing import Any

ROBOT_VIEW_KEYS = ("fpv", "chase")


def render_report(manifest: dict[str, Any]) -> str:
    style = "\n".join(
        [
            "body{font-family:system-ui,-apple-system,Segoe UI,sans-serif;margin:24px;"
            "background:#f7f7f4;color:#202124}",
            "header,.location{max-width:1180px;margin:0 auto 18px;background:white;"
            "border:1px solid #d9d7ce;padding:16px}",
            "h1{margin:0 0 8px;font-size:24px}",
            "h2{font-size:18px;margin:0 0 10px}",
            "h2 span{font-weight:400;color:#5f6368}",
            ".quick-summary{display:flex;flex-wrap:wrap;gap:8px;margin:10px 0 12px}",
            ".chip{font-size:12px;background:#f4f1e8;border:1px solid #d9d7ce;"
            "border-radius:4px;padding:4px 7px;color:#3c4043}",
            "a{color:#174ea6}",
            ".pairs{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}",
            ".pair{border-top:1px solid #ece8dd;padding-top:10px}",
            "figure{margin:0 0 8px}",
            "img{display:block;width:100%;height:auto;border:1px solid #ddd;background:#111}",
            "figcaption,p{font-size:13px;color:#5f6368;margin:6px 0}",
            "pre{font-size:12px;background:#f4f1e8;padding:10px;overflow:auto}",
            "details{border:1px solid #e3dfd4;background:#fbfaf6;margin:10px 0}",
            "summary{cursor:pointer;font-weight:600;padding:10px 12px;color:#3c4043}",
            "details[open] summary{border-bottom:1px solid #e3dfd4}",
            "details pre{margin:0;border:0}",
            ".details-body{padding:0 12px 12px}",
            ".location-meta{margin-top:12px}",
            "table{border-collapse:collapse;width:100%;font-size:12px;margin:10px 0;"
            "display:block;overflow:auto}",
            "th,td{border:1px solid #e0ddd4;padding:6px;text-align:left;vertical-align:top}",
            ".bad{color:#9b1c1c}",
            "@media(max-width:800px){.pairs{grid-template-columns:1fr}}",
        ]
    )
    rows = []
    for row_index, item in enumerate(manifest.get("locations") or []):
        section_id = " id='locations'" if row_index == 0 else ""
        if item.get("status") != "success":
            rows.append(
                "<section class='location'"
                + section_id
                + "><h2>"
                + html.escape(str(item.get("label")))
                + "</h2><p class='bad'>"
                + html.escape(str(item.get("blocker")))
                + "</p></section>"
            )
            continue
        pairs = []
        for view_key in ROBOT_VIEW_KEYS:
            diff = item["image_diffs"][view_key]
            residual = diff.get("residual") if isinstance(diff.get("residual"), dict) else {}
            pairs.append(
                "<div class='pair'>"
                f"<h3>{html.escape(view_key.upper())}</h3>"
                "<figure><img src='"
                + html.escape(item["views"]["mujoco"][view_key])
                + "'><figcaption>MuJoCo</figcaption></figure>"
                "<figure><img src='"
                + html.escape(item["views"]["isaac"][view_key])
                + "'><figcaption>Isaac</figcaption></figure>"
                "<p>mean abs RGB "
                + html.escape(str(diff["mean_abs_rgb"]))
                + ", nonzero "
                + html.escape(str(diff["nonzero_fraction"]))
                + ", residual "
                + html.escape(str(residual.get("residual_class") or ""))
                + "</p></div>"
            )
        rows.append(
            "<section class='location'"
            + section_id
            + "><h2>"
            + html.escape(str(item["label"]))
            + " <span>"
            + html.escape(str(item["target"]))
            + "</span></h2>"
            + "<div class='pairs'>"
            + "".join(pairs)
            + "</div><div class='location-meta'>"
            + render_json_details("Robot pose JSON", item["robot_pose"])
            + render_json_details(
                "Camera contract diagnostics JSON",
                item.get("camera_contract_diagnostics", {}),
            )
            + render_json_details(
                "Render contract diagnostics JSON",
                item.get("render_contract_diagnostics", {}),
            )
            + "</div></section>"
        )
    diagnostic_sections = (
        render_details_html(
            "Native Isaac Render Diagnostics",
            render_native_isaac_render_diagnostics(manifest),
        )
        + render_details_html(
            "Object/Render Gate",
            render_object_render_parity_diagnostics(manifest),
        )
        + render_details_html(
            "Object Parity Audit",
            render_object_parity_audit(manifest),
        )
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>RBY1M Robot Camera Apple2Apple</title>"
        "<style>" + style + "</style></head><body><header><h1>RBY1M Robot Camera Apple2Apple</h1>"
        "<p>"
        + html.escape(str(manifest.get("purpose")))
        + "</p>"
        + render_quick_summary(manifest)
        + ("<p><a href='#locations'>Jump to image comparisons</a></p>" if rows else "")
        + render_json_details("Run summary JSON", manifest.get("summary", {}))
        + render_generated_mess_manifest(manifest)
        + render_capture_quality_probe(manifest)
        + diagnostic_sections
        + "</header>"
        + "".join(rows)
        + "</body></html>"
    )


def render_quick_summary(manifest: dict[str, Any]) -> str:
    summary = _dict(manifest.get("summary"))
    mess_generation = _dict(manifest.get("mess_generation"))
    values = [
        ("status", manifest.get("status")),
        ("locations", summary.get("successful_location_count") or summary.get("location_count")),
        ("fpv mean abs RGB", summary.get("fpv_mean_abs_rgb_avg")),
        ("chase mean abs RGB", summary.get("chase_mean_abs_rgb_avg")),
        ("mess", mess_generation.get("generated_mess_count")),
        ("mess status", mess_generation.get("status")),
    ]
    chips = [
        "<span class='chip'>" + html.escape(label) + ": " + html.escape(str(value)) + "</span>"
        for label, value in values
        if value not in (None, "")
    ]
    return "<div class='quick-summary'>" + "".join(chips) + "</div>" if chips else ""


def render_details_html(title: str, body: str) -> str:
    if not body:
        return ""
    return (
        "<details class='report-details'><summary>"
        + html.escape(title)
        + "</summary><div class='details-body'>"
        + body
        + "</div></details>"
    )


def render_json_details(title: str, payload: Any) -> str:
    return (
        "<details class='json-details'><summary>"
        + html.escape(title)
        + "</summary><pre>"
        + html.escape(json.dumps(payload, indent=2, sort_keys=True))
        + "</pre></details>"
    )


def render_generated_mess_manifest(manifest: dict[str, Any]) -> str:
    mess_generation = _dict(manifest.get("mess_generation"))
    if not mess_generation:
        return ""
    return render_json_details("Canonical Generated Mess Manifest", mess_generation)


def render_capture_quality_probe(manifest: dict[str, Any]) -> str:
    capture_quality = _dict(manifest.get("capture_quality_probe")) or _dict(
        _dict(manifest.get("summary")).get("capture_quality_probe")
    )
    if not capture_quality:
        return ""
    rows = []
    for label, value in (
        ("render requested", capture_quality.get("render_resolution_requested")),
        ("saved report", capture_quality.get("render_resolution_saved")),
        ("metric", capture_quality.get("metric_resolution")),
        ("saved image mode", capture_quality.get("saved_image_mode")),
        ("metric image mode", capture_quality.get("metric_image_mode")),
        ("downsample filter", capture_quality.get("downsample_filter")),
        ("render settle frames", capture_quality.get("render_settle_frames")),
        ("samples/AA", quality_status_label(capture_quality, "anti_aliasing")),
        ("tone op", quality_status_label(capture_quality, "tonemap_operator")),
        ("denoise", quality_status_label(capture_quality, "denoise")),
        ("TAA", quality_status_label(capture_quality, "taa")),
        ("policy", capture_quality.get("policy_classification")),
    ):
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{html.escape(capture_quality_value(value))}</td>"
            "</tr>"
        )
    return render_details_html(
        "Capture Quality Probe",
        "<h2>Capture Quality Probe</h2>"
        "<p>Direct high-resolution report images and same-size metric images are "
        "tracked separately. These fields do not promote a native renderer default.</p>"
        "<table><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        + render_json_details("Capture quality JSON", capture_quality),
    )


def quality_status_label(capture_quality: dict[str, Any], key: str) -> str:
    row = _dict(capture_quality.get(key))
    status = str(row.get("status") or "")
    value = row.get("value")
    return f"{status}: {value}" if value is not None else status


def capture_quality_value(value: Any) -> str:
    if isinstance(value, dict) and {"width", "height"} <= set(value):
        return f"{value['width']}x{value['height']}"
    return str(value if value is not None else "")


def render_native_isaac_render_diagnostics(manifest: dict[str, Any]) -> str:
    diagnostics = _dict(manifest.get("native_isaac_render_diagnostics")) or _dict(
        _dict(manifest.get("summary")).get("native_isaac_render_diagnostics")
    )
    if not diagnostics:
        return ""
    rows = []
    for group_name in (
        "tone_mapping",
        "camera_exposure",
        "ocio",
        "color_correction",
        "color_grading",
        "renderer",
    ):
        group = _dict(diagnostics.get(group_name))
        for field_name, raw in group.items():
            row = _dict(raw)
            rows.append(
                "<tr>"
                f"<td>{html.escape(group_name)}</td>"
                f"<td>{html.escape(str(field_name))}</td>"
                f"<td>{html.escape(str(row.get('status') or ''))}</td>"
                f"<td>{html.escape(str(row.get('value')))}</td>"
                f"<td>{html.escape(str(row.get('setting_path') or ''))}</td>"
                "</tr>"
            )
    table = (
        "<table><thead><tr><th>Group</th><th>Setting</th><th>Status</th>"
        "<th>Value</th><th>Path</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        if rows
        else "<p>No native setting rows were recorded.</p>"
    )
    return (
        "<h2>Native Isaac Render Diagnostics</h2>"
        "<p>Status: <code>"
        + html.escape(str(diagnostics.get("status") or ""))
        + "</code>; renderer <code>"
        + html.escape(str(diagnostics.get("renderer_mode") or ""))
        + "</code>; capture <code>"
        + html.escape(str(diagnostics.get("capture_method") or ""))
        + "</code>. Settings API available: <code>"
        + html.escape(str(diagnostics.get("settings_api_available")))
        + "</code>. Default render settings changed: <code>"
        + html.escape(str(diagnostics.get("default_render_settings_changed")))
        + "</code>.</p><p>"
        + html.escape(str(diagnostics.get("interpretation") or ""))
        + "</p><p>"
        + html.escape(str(diagnostics.get("recommended_next_action") or ""))
        + "</p><pre>"
        + html.escape(
            json.dumps(
                {
                    "camera_prim_paths": diagnostics.get("camera_prim_paths") or [],
                    "render_product_paths": diagnostics.get("render_product_paths") or [],
                    "render_resolution": diagnostics.get("render_resolution") or {},
                    "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active"),
                    "post_render_comparison_profile": diagnostics.get(
                        "post_render_comparison_profile"
                    )
                    or {},
                },
                indent=2,
                sort_keys=True,
            )
        )
        + "</pre>"
        + table
    )


def render_object_render_parity_diagnostics(manifest: dict[str, Any]) -> str:
    diagnostics = _dict(manifest.get("object_render_parity_diagnostics")) or _dict(
        _dict(manifest.get("summary")).get("object_render_parity_diagnostics")
    )
    if not diagnostics:
        return ""
    object_gate = _dict(diagnostics.get("object_gate"))
    render_gate = _dict(diagnostics.get("render_gate"))
    failure_rows = []
    for item in object_gate.get("failure_records") or []:
        if not isinstance(item, dict):
            continue
        failure_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind') or ''))}</td>"
            f"<td>{html.escape(str(item.get('target_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('classification') or ''))}</td>"
            f"<td>{html.escape(str(item.get('blocking_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('binding_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('pose_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('state_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('render_contract_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('isaac_usd_prim_path') or ''))}</td>"
            "</tr>"
        )
    failure_table = (
        "<table><thead><tr><th>Kind</th><th>Target</th><th>Class</th>"
        "<th>Blocking Status</th><th>Binding</th><th>Pose</th><th>State</th>"
        "<th>Render Contract</th><th>Isaac Prim</th>"
        "</tr></thead><tbody>" + "".join(failure_rows) + "</tbody></table>"
        if failure_rows
        else "<p>No Object Gate failures were detected.</p>"
    )
    return (
        "<h2>Object/Render Gate</h2>"
        "<p>Status: <code>"
        + html.escape(str(diagnostics.get("status") or ""))
        + "</code>. Object Gate <code>"
        + html.escape(str(object_gate.get("status") or ""))
        + "</code> with "
        + html.escape(str(object_gate.get("comparable_count") or 0))
        + " comparable and "
        + html.escape(str(object_gate.get("failure_count") or 0))
        + " failing rows. Render Gate <code>"
        + html.escape(str(render_gate.get("status") or ""))
        + "</code>.</p><p>"
        + html.escape(str(diagnostics.get("recommended_next_action") or ""))
        + "</p>"
        + failure_table
    )


def render_object_parity_audit(manifest: dict[str, Any]) -> str:
    summary = _dict(manifest.get("summary"))
    audit = (
        _dict(manifest.get("object_visual_parity_audit"))
        or _dict(manifest.get("object_parity_audit"))
        or _dict(summary.get("object_visual_parity_audit"))
        or _dict(summary.get("object_parity_audit"))
    )
    if not audit:
        return ""

    def counts_cell(item: dict[str, Any], key: str) -> str:
        return "<td>" + html.escape(json.dumps(item.get(key) or {}, sort_keys=True)) + "</td>"

    category_rows = []
    for item in audit.get("category_status_summary") or []:
        if not isinstance(item, dict):
            continue
        category_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('category') or ''))}</td>"
            f"<td>{html.escape(str(item.get('item_count') or 0))}</td>"
            + counts_cell(item, "kind_counts")
            + counts_cell(item, "object_gate_status_counts")
            + counts_cell(item, "object_gate_classification_counts")
            + counts_cell(item, "binding_status_counts")
            + counts_cell(item, "state_status_counts")
            + counts_cell(item, "rgb_view_evidence_status_counts")
            + counts_cell(item, "target_coverage_status_counts")
            + counts_cell(item, "target_visual_state_status_counts")
            + counts_cell(item, "render_contract_status_counts")
            + "</tr>"
        )
    category_table = (
        "<h3>Category Status Summary</h3><table><thead><tr>"
        "<th>Category</th><th>Items</th><th>Kinds</th><th>Object Gate</th>"
        "<th>Classes</th><th>Binding</th><th>State</th><th>RGB Evidence</th>"
        "<th>Target Coverage</th><th>Target Visual State</th><th>Render</th>"
        "</tr></thead><tbody>" + "".join(category_rows) + "</tbody></table>"
        if category_rows
        else "<p>No category/status summary rows were recorded.</p>"
    )
    rows = []
    for item in audit.get("high_priority_items") or []:
        if not isinstance(item, dict):
            continue
        render_delta = _dict(item.get("render_contract_delta"))
        visual_state = _dict(item.get("visual_state_contract"))
        rgb_evidence = _dict(item.get("rgb_view_evidence"))
        mujoco = _dict(item.get("mujoco"))
        isaac = _dict(item.get("isaac"))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('kind') or ''))}</td>"
            f"<td>{html.escape(str(item.get('target_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('binding_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('category_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('pose_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('support_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('state_status') or ''))}</td>"
            f"<td>{html.escape(str(rgb_evidence.get('status') or ''))}</td>"
            f"<td>{html.escape(str(rgb_evidence.get('target_coverage_status') or ''))}</td>"
            f"<td>{html.escape(str(rgb_evidence.get('target_visual_state_status') or ''))}</td>"
            f"<td>{html.escape(str(render_delta.get('status') or ''))}</td>"
            f"<td>{html.escape(str(visual_state.get('protected_by') or ''))}</td>"
            f"<td>{html.escape(str(visual_state.get('evidence_artifact') or ''))}</td>"
            f"<td>{html.escape(str(mujoco.get('category') or ''))}</td>"
            f"<td>{html.escape(str(isaac.get('category') or isaac.get('usd_category') or ''))}</td>"
            f"<td>{html.escape(str(isaac.get('asset_id') or ''))}</td>"
            "</tr>"
        )
    table = (
        "<table><thead><tr>"
        "<th>Kind</th><th>Target</th><th>Binding</th><th>Category</th>"
        "<th>Pose</th><th>Support</th><th>State</th><th>RGB Evidence</th>"
        "<th>Target Coverage</th><th>Target Visual State</th><th>Render</th>"
        "<th>Protected By</th><th>Evidence</th>"
        "<th>MuJoCo Cat</th><th>Isaac Cat</th><th>Isaac Asset</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
        if rows
        else "<p>No high-priority object parity gaps were detected.</p>"
    )
    return (
        "<h2>Object Parity Audit</h2>"
        "<p>Status: <code>"
        + html.escape(str(audit.get("status") or ""))
        + "</code>; items "
        + html.escape(str(audit.get("item_count") or 0))
        + "; high-priority gaps "
        + html.escape(str(audit.get("high_priority_gap_count") or 0))
        + ".</p><p>"
        + html.escape(str(audit.get("recommended_next_action") or ""))
        + "</p>"
        + category_table
        + table
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

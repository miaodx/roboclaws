from __future__ import annotations

import html
import json
from typing import Any

from roboclaws.household import scene_camera_lighting_diagnostics, scene_camera_render_domain
from roboclaws.household.scene_camera_report_format import (
    ISAAC_LANE_ID,
    MOLMOSPACES_LANE_ID,
    _cell_text,
    _float_text,
    _percent_text,
    _pixels_text,
    _short_list_text,
)

_native_isaac_render_diagnostics = scene_camera_lighting_diagnostics.native_isaac_render_diagnostics
_lighting_tone_provenance = scene_camera_lighting_diagnostics.lighting_tone_provenance
_shadow_parity_probe = scene_camera_lighting_diagnostics.shadow_parity_probe
_render_domain_source_diagnostics = scene_camera_render_domain.render_domain_source_diagnostics
_render_domain_view_triage = scene_camera_render_domain.render_domain_view_triage
_render_domain_contract_probe = scene_camera_render_domain.render_domain_contract_probe


def _projection_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("projection_diagnostics")
        if isinstance(manifest.get("projection_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("pairs") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('point_count', '')))}</td>"
            f"<td>{html.escape(_pixels_text(item.get('max_pixel_delta')))}</td>"
            f"<td>{html.escape(str(item.get('all_points_inside_frame')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Handle",
            "Projected points",
            "Max pixel delta",
            "All sampled points inside frame",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; views={diagnostics.get('pair_count')}; "
        f"resolution={diagnostics.get('resolution')}; "
        f"vertical_fov={_float_text(diagnostics.get('vertical_fov_deg'))} deg; "
        f"max_pixel_delta={_pixels_text(diagnostics.get('max_pixel_delta'))}; "
        f"threshold={_pixels_text(diagnostics.get('projection_threshold_px'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Projection Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _visual_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("visual_diagnostics")
        if isinstance(manifest.get("visual_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("views") or []:
        if not isinstance(item, dict):
            continue
        lanes = item.get("lanes") if isinstance(item.get("lanes"), dict) else {}
        molmo = (
            lanes.get(MOLMOSPACES_LANE_ID)
            if isinstance(lanes.get(MOLMOSPACES_LANE_ID), dict)
            else {}
        )
        isaac = lanes.get(ISAAC_LANE_ID) if isinstance(lanes.get(ISAAC_LANE_ID), dict) else {}
        delta = item.get("delta") if isinstance(item.get("delta"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(_float_text(molmo.get('mean_luminance')))}</td>"
            f"<td>{html.escape(_float_text(isaac.get('mean_luminance')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('mean_luminance_delta')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_float_text(delta.get('rms_pixel_delta')))}</td>"
            f"<td>{html.escape(_percent_text(molmo.get('overexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(isaac.get('overexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(molmo.get('underexposed_fraction')))}</td>"
            f"<td>{html.escape(_percent_text(isaac.get('underexposed_fraction')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "MuJoCo luminance",
            "Isaac luminance",
            "Luminance delta",
            "Mean pixel delta",
            "RMS pixel delta",
            "MuJoCo overexposed",
            "Isaac overexposed",
            "MuJoCo underexposed",
            "Isaac underexposed",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"views={diagnostics.get('view_count')}; "
        f"max_luminance_delta="
        f"{_float_text(diagnostics.get('max_abs_mean_luminance_delta'))}; "
        f"mean_pixel_delta={_float_text(diagnostics.get('mean_absolute_pixel_delta'))}; "
        f"max_overexposed={_percent_text(diagnostics.get('max_overexposed_fraction'))}; "
        f"max_underexposed={_percent_text(diagnostics.get('max_underexposed_fraction'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    calibration = (
        diagnostics.get("render_domain_calibration")
        if isinstance(diagnostics.get("render_domain_calibration"), dict)
        else {}
    )
    calibration_note = ""
    if calibration:
        calibration_note = (
            f"Render-domain calibration: status={calibration.get('status')}; "
            f"global_isaac_luminance_gain="
            f"{_float_text(calibration.get('global_isaac_luminance_gain'))}; "
            f"mean_residual="
            f"{_float_text(calibration.get('mean_abs_calibrated_luminance_residual'))}; "
            f"max_residual="
            f"{_float_text(calibration.get('max_abs_calibrated_luminance_residual'))}; "
            f"{calibration.get('recommended_next_action') or ''}"
        )
    replay = (
        diagnostics.get("color_profile_replay")
        if isinstance(diagnostics.get("color_profile_replay"), dict)
        else {}
    )
    replay_note = ""
    if replay:
        replay_calibration = (
            replay.get("render_domain_calibration")
            if isinstance(replay.get("render_domain_calibration"), dict)
            else {}
        )
        replay_note = (
            f"Color-profile replay: status={replay.get('status')}; "
            f"mean_luminance_delta="
            f"{_float_text(replay.get('mean_abs_mean_luminance_delta'))}; "
            f"mean_pixel_delta={_float_text(replay.get('mean_absolute_pixel_delta'))}; "
            f"residual_status={replay_calibration.get('status') or ''}. "
            f"{replay.get('interpretation') or ''}"
        )
    candidates = (
        diagnostics.get("candidate_color_calibrations")
        if isinstance(diagnostics.get("candidate_color_calibrations"), dict)
        else {}
    )
    candidate_note = ""
    if candidates:
        candidate_rows = []
        for item in candidates.get("candidates") or []:
            if not isinstance(item, dict):
                continue
            candidate_rows.append(
                f"{item.get('candidate_id')}("
                f"lum={_float_text(item.get('mean_abs_mean_luminance_delta'))}, "
                f"px={_float_text(item.get('mean_absolute_pixel_delta'))})"
            )
        candidate_note = (
            f"Candidate color calibrations: best={candidates.get('best_candidate')}; "
            f"{'; '.join(candidate_rows)}. {candidates.get('interpretation') or ''}"
        )
    return f"""
<section class="panel">
  <h2>Visual Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(calibration_note)}</p>
  <p class="note">{html.escape(replay_note)}</p>
  <p class="note">{html.escape(candidate_note)}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _room_wall_light_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("room_wall_light_diagnostics")
        if isinstance(manifest.get("room_wall_light_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("pairs") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate', '')))}</td>"
            f"<td>{html.escape(str(item.get('region_id', '')))}</td>"
            f"<td>{html.escape(_float_text(item.get('baseline_wall_luminance')))}</td>"
            f"<td>{html.escape(_float_text(item.get('candidate_wall_luminance')))}</td>"
            f"<td>{html.escape(_float_text(item.get('wall_luminance_delta')))}</td>"
            f"<td>{html.escape(_float_text(item.get('image_luminance_delta')))}</td>"
            f"<td>{html.escape(str(item.get('classification', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Candidate",
            "Region",
            "Baseline wall luminance",
            "Candidate wall luminance",
            "Wall luminance delta",
            "Image luminance delta",
            "Classification",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"room_views={diagnostics.get('room_view_count')}; "
        f"pairs={diagnostics.get('pair_count')}; "
        f"dark_wall_pairs={diagnostics.get('dark_wall_pair_count')}; "
        f"wall_specific_pairs={diagnostics.get('wall_specific_pair_count')}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Room Wall Light Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("region_note") or ""))}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _candidate_visual_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("candidate_visual_diagnostics")
        if isinstance(manifest.get("candidate_visual_diagnostics"), dict)
        else {}
    )
    if not diagnostics:
        return ""
    rows = []
    for candidate in diagnostics.get("candidates") or []:
        if not isinstance(candidate, dict):
            continue
        status = str(candidate.get("status") or "")
        status_class = "status-degraded" if status == "degraded_visual_fidelity" else "status-ok"
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(candidate.get('candidate', '')))}</td>"
            f'<td class="{status_class}">{html.escape(status)}</td>'
            f"<td>{html.escape(str(candidate.get('view_count', '')))}</td>"
            f"<td>{html.escape(_float_text(candidate.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_float_text(candidate.get('max_mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_short_list_text(candidate.get('warning_reasons')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Candidate",
            "Visual status",
            "Views",
            "Mean pixel delta",
            "Max pixel delta",
            "Warnings",
        )
    )
    status = str(diagnostics.get("status") or "")
    warning = ""
    if status == "degraded_visual_fidelity":
        warning = (
            '<p class="warning-note">'
            + html.escape(str(diagnostics.get("recommended_next_action") or ""))
            + "</p>"
        )
    note = (
        f"status={status}; baseline={diagnostics.get('baseline')}; "
        f"candidates={diagnostics.get('candidate_count')}; "
        f"degraded={_short_list_text(diagnostics.get('degraded_candidates'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Candidate Visual Acceptance</h2>
  <p class="note">{html.escape(note)}</p>
  {warning}
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _lighting_tone_provenance_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("lighting_tone_provenance")
        if isinstance(manifest.get("lighting_tone_provenance"), dict)
        else _lighting_tone_provenance(manifest)
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("lanes") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('lane_id') or ''))}</td>"
            f"<td>{html.escape(str(item.get('environment_light_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('environment_light_summary') or ''))}</td>"
            f"<td>{html.escape(str(item.get('tone_adjustment_status') or ''))}</td>"
            f"<td>{html.escape(str(item.get('tone_adjustment_summary') or ''))}</td>"
            f"<td>{html.escape(str(item.get('native_render_summary') or ''))}</td>"
            f"<td>{html.escape(str(item.get('tone_adjustment_source') or ''))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "Lane",
            "Environment status",
            "Environment / fill evidence",
            "Tone status",
            "Tone / exposure evidence",
            "Native render",
            "Tone source",
        )
    )
    note = (
        f"status={diagnostics.get('status')}; lanes={diagnostics.get('lane_count')}; "
        f"missing_environment_light_lanes="
        f"{_cell_text(diagnostics.get('missing_environment_light_lanes'))}; "
        f"tone_adjusted_lanes={_cell_text(diagnostics.get('tone_adjusted_lanes'))}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Lighting &amp; Tone Provenance</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _shadow_parity_probe_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("shadow_parity_probe")
        if isinstance(manifest.get("shadow_parity_probe"), dict)
        else _shadow_parity_probe(manifest)
    )
    if not diagnostics:
        return ""
    rows = [
        ("Profile", diagnostics.get("profile_id")),
        ("Status", diagnostics.get("status")),
        ("Light rig schema", diagnostics.get("scene_light_rig_schema")),
        ("Isaac dome intensity", diagnostics.get("isaac_dome_intensity")),
        ("Isaac key intensity", diagnostics.get("isaac_key_intensity")),
        ("Isaac existing light scale", diagnostics.get("isaac_existing_light_intensity_scale")),
        ("Isaac added light paths", diagnostics.get("isaac_added_light_paths")),
        ("MuJoCo light count", diagnostics.get("mujoco_light_count")),
        ("Isaac light count", diagnostics.get("isaac_light_count")),
        ("Isaac shadow-off prims", diagnostics.get("isaac_shadow_disabled_prim_count")),
    ]
    rig_roles = (
        diagnostics.get("scene_light_rig_roles")
        if isinstance(diagnostics.get("scene_light_rig_roles"), dict)
        else {}
    )
    if rig_roles:
        rows.extend(
            [
                ("Rig key role", rig_roles.get("key_enabled")),
                ("Rig ambient role", rig_roles.get("ambient_enabled")),
                ("Rig fill role", rig_roles.get("fill_enabled")),
                ("Authored scene lights policy", rig_roles.get("authored_scene_lights_policy")),
                ("Rig key direction", rig_roles.get("key_direction")),
            ]
        )
    key_light = (
        diagnostics.get("key_light_direction")
        if isinstance(diagnostics.get("key_light_direction"), dict)
        else {}
    )
    if key_light:
        rows.extend(
            [
                ("Key light status", key_light.get("status")),
                ("Key light frame", key_light.get("scene_key_light_frame")),
                ("Canonical key direction", key_light.get("canonical_scene_key_light_direction")),
                ("MuJoCo key direction", key_light.get("mujoco_key_light_direction")),
                ("Isaac key direction", key_light.get("isaac_key_light_direction")),
                ("Isaac angle delta deg", _float_text(key_light.get("isaac_angle_delta_deg"))),
            ]
        )
    row_html = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(_cell_text(value))}</td></tr>"
        for label, value in rows
    )
    note = (
        f"profile={diagnostics.get('profile_id')}; status={diagnostics.get('status')}; "
        f"shadow_profile={diagnostics.get('is_shadow_parity_profile')}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Shadow Parity Probe</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr><th>Setting</th><th>Value</th></tr></thead>
    <tbody>{row_html}</tbody>
  </table></div>
</section>
"""


def _render_domain_source_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("render_domain_source_diagnostics")
        if isinstance(manifest.get("render_domain_source_diagnostics"), dict)
        else _render_domain_source_diagnostics(manifest)
    )
    if not diagnostics:
        return ""
    rows = []
    for item in diagnostics.get("source_references") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('evidence_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('lane', '')))}</td>"
            f"<td>{html.escape(str(item.get('path', '')))}:"
            f"{html.escape(str(item.get('line_start', '')))}</td>"
            f"<td>{html.escape(str(item.get('status', '')))}</td>"
            f"<td>{html.escape(str(item.get('claim', '')))}</td>"
            f"<td>{html.escape(str(item.get('snippet_summary', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in ("Evidence", "Lane", "Source", "Status", "Claim", "Snippet")
    )
    lane_summary = (
        diagnostics.get("lane_summary") if isinstance(diagnostics.get("lane_summary"), dict) else {}
    )
    lane_note = "; ".join(
        f"{lane}: {summary.get('renderer_contract')} ({summary.get('evidence_count')} refs)"
        for lane, summary in lane_summary.items()
        if isinstance(summary, dict)
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"root_cause={diagnostics.get('root_cause_status')}; "
        f"source_refs={diagnostics.get('available_source_reference_count')}/"
        f"{diagnostics.get('source_reference_count')}; {lane_note}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Render Domain Source Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _native_isaac_render_diagnostics_section(manifest: dict[str, Any]) -> str:
    diagnostics = (
        manifest.get("native_isaac_render_diagnostics")
        if isinstance(manifest.get("native_isaac_render_diagnostics"), dict)
        else _native_isaac_render_diagnostics(manifest)
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
        group = diagnostics.get(group_name) if isinstance(diagnostics.get(group_name), dict) else {}
        for field_name, raw in group.items():
            row = raw if isinstance(raw, dict) else {}
            rows.append(
                "<tr>"
                f"<td>{html.escape(group_name)}</td>"
                f"<td>{html.escape(str(field_name))}</td>"
                f"<td>{html.escape(str(row.get('status') or ''))}</td>"
                f"<td>{html.escape(str(row.get('value')))}</td>"
                f"<td>{html.escape(str(row.get('setting_path') or ''))}</td>"
                "</tr>"
            )
    setting_table = (
        '<div class="table-wrap"><table><thead><tr><th>Group</th><th>Setting</th>'
        "<th>Status</th><th>Value</th><th>Path</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
        if rows
        else '<p class="note">No native setting rows were recorded.</p>'
    )
    note = (
        f"status={diagnostics.get('status')}; "
        f"settings_api_available={diagnostics.get('settings_api_available')}; "
        f"default_render_settings_changed={diagnostics.get('default_render_settings_changed')}; "
        f"renderer={diagnostics.get('renderer_mode')}; "
        f"capture={diagnostics.get('capture_method')}. "
        f"{diagnostics.get('interpretation') or ''}"
    )
    context = {
        "camera_prim_paths": diagnostics.get("camera_prim_paths") or [],
        "render_product_paths": diagnostics.get("render_product_paths") or [],
        "render_resolution": diagnostics.get("render_resolution") or {},
        "isaac_lab_isp_active": diagnostics.get("isaac_lab_isp_active"),
        "post_render_comparison_profile": diagnostics.get("post_render_comparison_profile") or {},
    }
    return f"""
<section class="panel">
  <h2>Native Isaac Render Diagnostics</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(diagnostics.get("recommended_next_action") or ""))}</p>
  <pre>{html.escape(json.dumps(context, indent=2, sort_keys=True))}</pre>
  {setting_table}
</section>
"""


def _render_domain_view_triage_section(manifest: dict[str, Any]) -> str:
    triage = (
        manifest.get("render_domain_view_triage")
        if isinstance(manifest.get("render_domain_view_triage"), dict)
        else _render_domain_view_triage(manifest)
    )
    if not triage:
        return ""
    rows = []
    for item in triage.get("views") or []:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_kind', '')))}</td>"
            f"<td>{html.escape(str(item.get('render_residual_class', '')))}</td>"
            f"<td>{html.escape(_float_text(item.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(_float_text(item.get('abs_mean_luminance_delta')))}</td>"
            f"<td>{html.escape(_pixels_text(item.get('max_projection_delta_px')))}</td>"
            f"<td>{html.escape(str(item.get('suspected_contract', '')))}</td>"
            f"<td>{html.escape(str(item.get('usd_prim_path', '')))}</td>"
            f"<td>{html.escape(str(item.get('next_probe', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Anchor",
            "Residual",
            "Mean pixel delta",
            "Mean luminance delta",
            "Projection delta",
            "Suspected contract",
            "Isaac USD prim",
            "Next probe",
        )
    )
    note = (
        f"status={triage.get('status')}; views={triage.get('view_count')}; "
        f"high_residual_views={triage.get('high_residual_view_count')}; "
        f"top={triage.get('top_residual_view_id')}. "
        f"{triage.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Render Domain View Triage</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(triage.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""


def _render_domain_contract_probe_section(manifest: dict[str, Any]) -> str:
    probe = (
        manifest.get("render_domain_contract_probe")
        if isinstance(manifest.get("render_domain_contract_probe"), dict)
        else _render_domain_contract_probe(manifest)
    )
    if not probe:
        return ""
    rows = []
    for item in probe.get("views") or []:
        if not isinstance(item, dict):
            continue
        mujoco = item.get("mujoco") if isinstance(item.get("mujoco"), dict) else {}
        isaac = item.get("isaac") if isinstance(item.get("isaac"), dict) else {}
        delta = item.get("contract_delta") if isinstance(item.get("contract_delta"), dict) else {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('view_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('suspected_contract', '')))}</td>"
            f"<td>{html.escape(str(delta.get('status', '')))}</td>"
            f"<td>{html.escape(_float_text(item.get('mean_absolute_pixel_delta')))}</td>"
            f"<td>{html.escape(str(mujoco.get('status', '')))}</td>"
            f"<td>{html.escape(_short_list_text(mujoco.get('materials')))}</td>"
            f"<td>{html.escape(_short_list_text(mujoco.get('texture_files')))}</td>"
            f"<td>{html.escape(str(isaac.get('status', '')))}</td>"
            f"<td>{html.escape(_short_list_text(isaac.get('materials')))}</td>"
            f"<td>{html.escape(_short_list_text(isaac.get('texture_files')))}</td>"
            f"<td>{html.escape(str(isaac.get('shadow_disabled_prim_count', '')))}</td>"
            "</tr>"
        )
    headers = "".join(
        f"<th>{html.escape(label)}</th>"
        for label in (
            "View",
            "Suspected contract",
            "Contract delta",
            "Mean pixel delta",
            "MuJoCo status",
            "MuJoCo materials",
            "MuJoCo textures",
            "Isaac status",
            "Isaac materials",
            "Isaac textures",
            "Isaac shadow-off prims",
        )
    )
    note = (
        f"status={probe.get('status')}; views={probe.get('view_count')}; "
        f"high_priority_deltas={probe.get('high_priority_delta_count')}; "
        f"mujoco_parse={probe.get('mujoco_parse_status')}; "
        f"isaac_parse={probe.get('isaac_parse_status')}; "
        f"mujoco_lights={probe.get('mujoco_light_count')}; "
        f"isaac_lights={probe.get('isaac_light_count')}; "
        f"isaac_shadow_disabled_prims={probe.get('isaac_shadow_disabled_prim_count')}. "
        f"{probe.get('interpretation') or ''}"
    )
    return f"""
<section class="panel">
  <h2>Render Domain Contract Probe</h2>
  <p class="note">{html.escape(note)}</p>
  <p class="note">{html.escape(str(probe.get("recommended_next_action") or ""))}</p>
  <div class="table-wrap"><table>
    <thead><tr>{headers}</tr></thead>
    <tbody>{"".join(rows)}</tbody>
  </table></div>
</section>
"""

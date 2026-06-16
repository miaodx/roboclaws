from __future__ import annotations

import html
import json
import os
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.core.rerun import (
    render_rerun_panel,
    report_rerun_command_from_env,
    rerun_panel_css,
)
from roboclaws.household.planner_proof_quality import (
    format_quality_tier_counts,
    planner_proof_quality_evidence,
    planner_proof_quality_summary,
)
from roboclaws.household.planner_task_feasibility import grasp_feasibility_signature_counts
from roboclaws.household.report_sections_agent import (
    agent_view_section,
    cleanup_policy_trace_section,
    evidence_lane_badges,
    evidence_lane_note,
    real_robot_readiness_section,
)
from roboclaws.household.report_sections_grasp_cache import (
    grasp_cache_availability_preflight_section,
    grasp_cache_generation_preflight_section,
)
from roboclaws.household.report_sections_grasp_diagnostics import (
    grasp_cache_generation_report_sections,
    grasp_filter_diagnostics_report_sections,
    grasp_initial_contact_diagnostics_report_sections,
    grasp_pose_policy_cache_report_sections,
)
from roboclaws.household.report_sections_isaac import isaac_runtime_section
from roboclaws.household.report_sections_map import (
    map_evidence_refresh_summary_section,
)
from roboclaws.household.report_sections_nav2_map import nav2_map_bundle_section
from roboclaws.household.report_sections_proof import (
    attached_planner_proof_section,
    cleanup_primitive_gate_section,
    manipulation_provenance_section,
    planner_cleanup_bridge_section,
    planner_proof_requests_section,
)
from roboclaws.household.report_sections_proof_bundle import (
    cleanup_rerun_artifact_section,
    cleanup_rerun_command_section,
    grasp_feasibility_mitigation_decision_section,
    proof_bundle_commands_section,
    proof_bundle_local_runtime_preflight_section,
    proof_bundle_warmup_section,
    proof_execution_horizon_section,
)
from roboclaws.household.report_sections_proof_selection import proof_request_selection_section
from roboclaws.household.report_sections_robot import (
    robot_timeline_section,
    robot_view_camera_contract_summary,
    visual_core_robot_view_steps,
)
from roboclaws.household.report_sections_timing import runtime_timing_section
from roboclaws.household.report_semantic_map_artifacts import write_semantic_map_artifacts
from roboclaws.household.semantic_timeline import (
    OBJECT_DONE_PHASE,
    PLACE_CLEANUP_PHASES,
    SEMANTIC_LOOP_DISPLAY_NOTE,
    display_semantic_subphases,
)
from roboclaws.household.types import CleanupScenario

_COLORS = {
    "dish": (65, 125, 193),
    "book": (117, 86, 160),
    "linen": (78, 154, 96),
    "food": (206, 108, 65),
    "toy": (196, 154, 56),
    "electronics": (80, 80, 80),
}


def write_state_snapshot(
    scenario: CleanupScenario,
    locations: dict[str, str],
    output_path: Path,
    *,
    title: str,
) -> Path:
    """Render a compact deterministic room-state PNG."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 580), (249, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 888, 568), outline=(190, 194, 202), width=2)
    draw.text((28, 26), title, fill=(30, 34, 42))

    positions = _receptacle_positions()
    receptacles = {item.receptacle_id: item for item in scenario.receptacles}
    for receptacle_id, (x, y) in positions.items():
        receptacle = receptacles[receptacle_id]
        draw.rounded_rectangle((x - 80, y - 32, x + 80, y + 32), radius=6, fill=(232, 235, 241))
        draw.rectangle((x - 80, y - 32, x + 80, y + 32), outline=(169, 176, 190), width=1)
        draw.text((x - 70, y - 8), receptacle.name[:22], fill=(45, 51, 64))

    offsets: dict[str, int] = {}
    for obj in sorted(scenario.objects, key=lambda item: item.object_id):
        location_id = locations.get(obj.object_id, obj.location_id)
        x, y = positions.get(location_id, (450, 470))
        offset = offsets.get(location_id, 0)
        offsets[location_id] = offset + 1
        color = _COLORS.get(obj.category, (70, 90, 120))
        marker_x = x - 58 + offset * 28
        marker_y = y + 44
        draw.ellipse((marker_x, marker_y, marker_x + 20, marker_y + 20), fill=color)
        draw.text(
            (marker_x - 8, marker_y + 24),
            obj.object_id.split("_", 1)[0][:8],
            fill=(30, 34, 42),
        )

    image.save(output_path, format="PNG")
    return output_path


def render_cleanup_report(
    *,
    run_dir: Path,
    scenario: CleanupScenario,
    run_result: dict[str, Any],
    trace_events: list[dict[str, Any]],
    before_snapshot: Path,
    after_snapshot: Path,
    robot_view_steps: list[dict[str, Any]] | None = None,
) -> Path:
    """Write a self-contained cleanup `report.html`."""
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.html"
    body = "\n".join(
        _cleanup_report_sections(
            run_dir=run_dir,
            scenario=scenario,
            run_result=run_result,
            trace_events=trace_events,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            robot_view_steps=robot_view_steps or [],
        )
    )
    rerun_command = (
        str(run_result.get("rerun_command") or "").strip() or report_rerun_command_from_env()
    )
    if rerun_command:
        run_result["rerun_command"] = rerun_command
    report_title = str(run_result.get("report_title") or "MolmoSpaces Cleanup Pilot")
    report_path.write_text(
        _wrap_html(body, rerun_command=rerun_command, title=report_title),
        encoding="utf-8",
    )
    return report_path


def _cleanup_report_sections(
    *,
    run_dir: Path,
    scenario: CleanupScenario,
    run_result: dict[str, Any],
    trace_events: list[dict[str, Any]],
    before_snapshot: Path,
    after_snapshot: Path,
    robot_view_steps: list[dict[str, Any]],
) -> list[str]:
    """Return the canonical Cleanup Artifact Report section sequence."""
    moves = _extract_moves(trace_events)
    score = run_result["score"]
    write_semantic_map_artifacts(
        run_dir,
        run_result,
        robot_view_steps,
        report_asset_src=_report_asset_src,
    )
    return _present_sections(
        [
            _cleanup_report_tabs(),
            _cleanup_summary_section(scenario=scenario, run_result=run_result, score=score),
            _report_tab_panel(
                "overview",
                [
                    _confidence_layer_note(run_result),
                    _realworld_contract_note(run_result),
                    evidence_lane_note(run_result),
                    map_evidence_refresh_summary_section(run_result),
                    _before_after_section(
                        before_snapshot=before_snapshot,
                        after_snapshot=after_snapshot,
                        run_result=run_result,
                        robot_view_steps=robot_view_steps,
                    ),
                    _object_moves_section(moves),
                ],
            ),
            _report_tab_panel(
                "timeline",
                [
                    robot_timeline_section(
                        run_dir,
                        visual_core_robot_view_steps(run_result, robot_view_steps),
                        empty_state_block=_empty_state_block,
                        view_figure=_view_figure,
                        report_asset_src=_report_asset_src,
                    )
                ],
            ),
            _report_tab_panel(
                "timing",
                [runtime_timing_section(run_dir, run_result, trace_events, robot_view_steps)],
            ),
            _report_tab_panel(
                "actions",
                [_semantic_steps_table(run_result.get("semantic_substeps") or [])],
            ),
            _report_tab_panel(
                "robot",
                [
                    _molmospaces_agibot_rehearsal_section(run_dir, run_result),
                    _agibot_sdk_runner_section(run_dir, run_result),
                    isaac_runtime_section(
                        run_dir,
                        run_result,
                        metric=_metric,
                        artifact_link=_artifact_link,
                        yes_no=_yes_no,
                    ),
                    nav2_map_bundle_section(
                        run_dir,
                        run_result,
                        metric=_metric,
                        review_image=_review_image,
                        report_asset_src=_report_asset_src,
                    ),
                    real_robot_readiness_section(run_result),
                    cleanup_policy_trace_section(run_result),
                ],
            ),
            _report_tab_panel(
                "proof",
                [
                    _score_section(score),
                    manipulation_provenance_section(run_result),
                    attached_planner_proof_section(run_result, view_figure=_view_figure),
                    cleanup_primitive_gate_section(run_result),
                    planner_cleanup_bridge_section(run_result),
                    planner_proof_requests_section(run_result),
                ],
            ),
            _report_tab_panel(
                "agent",
                [
                    agent_view_section(run_result),
                    _raw_fpv_observations_section(run_result),
                    _model_declared_observations_section(run_result),
                    _camera_model_policy_section(run_result),
                    _advisory_review_section(run_result),
                    _private_evaluation_section(run_result),
                ],
            ),
        ]
    )


def render_planner_manipulation_report(
    *,
    run_dir: Path,
    run_result: dict[str, Any],
) -> Path:
    """Write a shared-underlay report for planner-backed manipulation probes."""
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "report.html"
    evidence = run_result.get("manipulation_evidence") or {}
    quality = planner_proof_quality_evidence(evidence)
    body = f"""
    <section class="summary">
      <div class="summary-head">
        <p class="eyebrow">Manipulation artifact</p>
        <h1>Planner-Backed Manipulation Probe</h1>
      </div>
      <div class="metric-grid">
        {_metric("Status", run_result.get("status", "unknown"))}
        {_metric("Embodiment", evidence.get("embodiment", "unknown"))}
        {_metric("Policy", evidence.get("upstream_policy_class", "unknown"))}
        {_metric("Proof Quality", quality.get("quality_tier", "unknown"))}
        {_metric("Steps", evidence.get("steps_executed", "n/a"))}
        {_metric("Qpos delta", evidence.get("max_abs_qpos_delta", "n/a"))}
        {_metric("Containment proven", "yes" if quality.get("containment_proven") else "no")}
      </div>
      <div class="badges">
        {_badge("Contract", run_result.get("contract", "unknown"))}
        {_badge("Backend", run_result.get("backend", "unknown"))}
        {_badge("Probe mode", evidence.get("probe_mode", "unknown"))}
        {_badge("Provenance", evidence.get("primitive_provenance", "unknown"))}
        {_badge("Planner backed", evidence.get("planner_backed", False))}
      </div>
    </section>
    {manipulation_provenance_section(run_result)}
    {_planner_probe_quality_section(evidence)}
    {_planner_probe_views_section(evidence)}
    {_planner_probe_cleanup_binding_section(evidence)}
    {_planner_probe_task_sampler_robot_placement_profile_section(evidence)}
    {_planner_probe_task_sampler_failure_section(evidence)}
    {_planner_probe_post_placement_rejection_section(evidence)}
    {_planner_probe_grasp_collision_diagnostics_section(evidence)}
    {_planner_probe_placement_scene_diagnostics_section(evidence)}
    {_planner_probe_diagnostics_section(evidence)}
    {_planner_probe_cuda_memory_section(evidence)}
    {_planner_probe_curobo_memory_profile_section(evidence)}
    {_planner_probe_policy_exception_section(evidence)}
    {_planner_probe_curobo_extension_cache_section(evidence)}
    {_planner_probe_warp_compatibility_section(evidence)}
    {_planner_probe_worker_stages_section(evidence)}
    {_rby1m_curobo_gate_section(run_result)}
    {_planner_probe_blockers_section(evidence)}
    {_planner_probe_artifacts_section(run_result)}
    """
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def _planner_probe_quality_section(evidence: dict[str, Any]) -> str:
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


def render_planner_proof_bundle_runner_report(
    *,
    output_dir: Path,
    manifest: dict[str, Any],
) -> Path:
    """Write a reviewable report for proof-bundle runner command manifests."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    commands = manifest.get("commands") or []
    cleanup_command = manifest.get("cleanup_command") or []
    cleanup_rerun = manifest.get("cleanup_rerun") or {}
    body = f"""
    <section class="summary">
      <div class="summary-head">
        <p class="eyebrow">Proof bundle runner artifact</p>
        <h1>Planner Proof Bundle Runner</h1>
      </div>
      <div class="metric-grid">
        {_metric("Status", manifest.get("status", "unknown"))}
        {_metric("Proof requests", manifest.get("proof_request_count", 0))}
        {_metric("Ready requests", manifest.get("ready_request_count", 0))}
        {_metric("Commands", manifest.get("command_count", len(commands)))}
      </div>
      <div class="badges">
        {_badge("Schema", manifest.get("schema", "unknown"))}
        {_badge("Output dir", manifest.get("output_dir", output_dir))}
      </div>
    </section>
    <section class="panel">
      <h2>Source Cleanup Artifact</h2>
      <p class="note">{html.escape(str(manifest.get("evidence_note", "")))}</p>
      {
        _path_table(
            [
                ("Cleanup run result", manifest.get("cleanup_run_result", "")),
                (
                    "Planner scene XML",
                    (manifest.get("planner_scene") or {}).get("scene_xml", ""),
                ),
            ]
        )
    }
    </section>
    {proof_execution_horizon_section(manifest.get("proof_execution_horizon") or {})}
    {proof_request_selection_section(manifest.get("proof_request_selection") or {})}
    {
        grasp_feasibility_mitigation_decision_section(
            manifest.get("grasp_feasibility_mitigation_decision") or {}
        )
    }
    {
        grasp_cache_availability_preflight_section(
            manifest.get("grasp_cache_availability_preflight") or {}
        )
    }
    {
        grasp_cache_generation_preflight_section(
            manifest.get("grasp_cache_generation_preflight") or {}
        )
    }
    {proof_bundle_local_runtime_preflight_section(manifest.get("local_runtime_preflight") or {})}
    {
        _proof_bundle_results_section(
            manifest.get("prior_proof_result_summary") or {},
            output_dir=output_dir,
            title="Prior Proof Evidence",
            section_class="prior-proof-evidence",
            default_note=(
                "Prior proof evidence consumed by selection. This keeps standalone "
                "probe and prior bundle visuals reviewable in the runner report."
            ),
        )
    }
    {proof_bundle_warmup_section(manifest.get("warmup") or {})}
    {proof_bundle_commands_section(commands)}
    {
        _proof_bundle_results_section(
            manifest.get("proof_result_summary") or {}, output_dir=output_dir
        )
    }
    {cleanup_rerun_command_section(cleanup_command)}
    {cleanup_rerun_artifact_section(cleanup_rerun)}
    """
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def render_grasp_cache_generation_report(
    *,
    output_dir: Path,
    result: dict[str, Any],
) -> Path:
    """Write a reviewable report for MolmoSpaces grasp cache generation attempts."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    body = "\n".join(_present_sections(grasp_cache_generation_report_sections(result)))
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def render_grasp_pose_policy_cache_report(
    *,
    output_dir: Path,
    result: dict[str, Any],
) -> Path:
    """Write a reviewable report for validated pose-policy cache generation."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    body = "\n".join(_present_sections(grasp_pose_policy_cache_report_sections(result)))
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def render_grasp_filter_diagnostics_report(
    *,
    output_dir: Path,
    result: dict[str, Any],
) -> Path:
    """Write a reviewable report for bounded grasp perturbation-filter diagnostics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    body = "\n".join(_present_sections(grasp_filter_diagnostics_report_sections(result)))
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def render_grasp_initial_contact_diagnostics_report(
    *,
    output_dir: Path,
    result: dict[str, Any],
) -> Path:
    """Write a reviewable report for rigid-grasp initial-contact diagnostics."""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "report.html"
    body = "\n".join(_present_sections(grasp_initial_contact_diagnostics_report_sections(result)))
    report_path.write_text(_wrap_html(body, extra_css=_planner_report_css()), encoding="utf-8")
    return report_path


def _present_sections(sections: list[str]) -> list[str]:
    return [section for section in sections if section]


def _cleanup_report_tabs() -> str:
    tabs = [
        ("overview", "Overview"),
        ("timeline", "Robot Timeline"),
        ("timing", "Timing"),
        ("actions", "Actions"),
        ("robot", "Robot & Map"),
        ("proof", "Score & Proof"),
        ("agent", "Agent & Eval"),
    ]
    buttons = "".join(
        '<button type="button" class="report-tab" '
        f'id="report-tab-button-{tab_id}" data-report-tab-button="{tab_id}" '
        f'aria-controls="report-tab-{tab_id}" aria-selected="{str(index == 0).lower()}">'
        f"{html.escape(label)}</button>"
        for index, (tab_id, label) in enumerate(tabs)
    )
    return f'<nav class="report-tabs" aria-label="Report sections">{buttons}</nav>'


def _report_tab_panel(tab_id: str, sections: list[str]) -> str:
    body = "\n".join(_present_sections(sections))
    if not body:
        body = _empty_state_block(
            "No report data recorded",
            "This run did not produce artifacts for this report section.",
        )
    escaped_id = html.escape(tab_id)
    return (
        f'<div id="report-tab-{escaped_id}" class="report-tab-panel" '
        f'data-report-tab="{escaped_id}" role="tabpanel" '
        f'aria-labelledby="report-tab-button-{escaped_id}">{body}</div>'
    )


def _empty_state_block(title: str, message: str) -> str:
    return (
        f'<div class="empty-state"><h3>{html.escape(title)}</h3><p>{html.escape(message)}</p></div>'
    )


def _cleanup_summary_section(
    *,
    scenario: CleanupScenario,
    run_result: dict[str, Any],
    score: dict[str, Any],
) -> str:
    restored_summary = f"{score['restored_count']}/{score['total_targets']}"
    eyebrow = str(run_result.get("report_eyebrow") or "Cleanup artifact")
    title = str(run_result.get("report_title") or "MolmoSpaces Cleanup Pilot")
    return f"""
    <section class="summary">
      <div class="summary-head">
        <p class="eyebrow">{html.escape(eyebrow)}</p>
        <h1>{html.escape(title)}</h1>
      </div>
      {_summary_metrics(run_result, score)}
      <details class="summary-metadata">
        <summary>Run metadata</summary>
        <div class="badges">
          {_badge("Scenario", scenario.scenario_id)}
          {_badge("Backend", run_result.get("backend", "unknown"))}
          {_badge("Contract", run_result.get("contract", "legacy"))}
          {_badge("Status", run_result["cleanup_status"])}
          {_badge("Restored", restored_summary)}
          {_badge("Generated mess", _generated_mess_summary(run_result))}
          {_badge("Policy", run_result.get("policy", run_result.get("planner", "unknown")))}
          {evidence_lane_badges(run_result, _badge)}
          {_badge("Agent driven", run_result.get("agent_driven", False))}
          {_badge("Provenance", run_result["primitive_provenance"])}
          {_badge("MCP server", run_result.get("mcp_server", "none"))}
          {_confidence_layer_badges(run_result)}
          {_robot_badge(run_result)}
          {_robot_view_camera_badges(run_result)}
        </div>
      </details>
    </section>
    """


def _before_after_section(
    *,
    before_snapshot: Path,
    after_snapshot: Path,
    run_result: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
) -> str:
    before_name = before_snapshot.name
    after_name = after_snapshot.name
    pick_place = _pick_place_comparison_grid(
        run_result.get("semantic_substeps") or [],
        robot_view_steps,
    )
    return f"""
    <section class="panel before-after-section">
      <div class="section-heading">
        <h2>Before And After</h2>
      </div>
      <div class="snapshots">
        <figure>
          {_review_image(before_name, "Before cleanup")}
          <figcaption>
            <strong>Initial room state</strong>
            <span>Object locations before the cleanup loop.</span>
          </figcaption>
        </figure>
        <figure>
          {_review_image(after_name, "After cleanup")}
          <figcaption>
            <strong>Final room state</strong>
            <span>Object locations after all reported place actions.</span>
          </figcaption>
        </figure>
      </div>
      {pick_place}
    </section>
    """


def _pick_place_comparison_grid(
    semantic_substeps: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
) -> str:
    comparisons = _pick_place_comparisons(semantic_substeps, robot_view_steps)
    if not comparisons:
        return ""
    cards = []
    for item in comparisons:
        escaped_route = html.escape(item["route"])
        escaped_route_attr = html.escape(item["route"], quote=True)
        cards.append(
            '<details class="comparison-item" open>'
            "<summary>"
            '<span class="comparison-item-head">'
            f"<strong>{html.escape(item['object_id'])}</strong>"
            f'<span title="{escaped_route_attr}">{escaped_route}</span>'
            "</span>"
            "</summary>"
            '<div class="comparison-views">'
            f"{_comparison_figure(item.get('pick_view'), 'Pick view', item.get('pick_label'))}"
            f"{_comparison_figure(item.get('place_view'), 'Place view', item.get('place_label'))}"
            "</div>"
            "</details>"
        )
    return (
        '<details class="comparison-details" open>'
        "<summary>"
        f"Pick/place visual checks <span>{len(comparisons)} completed moves</span>"
        "</summary>"
        '<div class="comparison-grid">' + "".join(cards) + "</div></details>"
    )


def _pick_place_comparisons(
    semantic_substeps: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
) -> list[dict[str, str]]:
    picks: dict[str, dict[str, Any]] = {}
    places: dict[str, dict[str, Any]] = {}
    for step in robot_view_steps:
        action = str(step.get("action") or "")
        handle = _action_object_id(action)
        if not handle:
            continue
        phase = str(step.get("semantic_phase") or "")
        if phase == "pick" and handle not in picks:
            picks[handle] = step
        elif phase in PLACE_CLEANUP_PHASES and handle not in places:
            places[handle] = step

    comparisons: list[dict[str, str]] = []
    for item in semantic_substeps:
        object_id = str(item.get("object_id") or "")
        if not object_id:
            continue
        pick = picks.get(object_id)
        place = places.get(object_id)
        if not pick and not place:
            continue
        route = (
            f"{item.get('source_receptacle_id') or 'unknown source'}"
            " -> "
            f"{item.get('target_receptacle_id') or 'unknown target'}"
        )
        comparisons.append(
            {
                "object_id": object_id,
                "route": route,
                "pick_view": _best_comparison_view(pick),
                "pick_label": str((pick or {}).get("action") or "pick"),
                "place_view": _best_comparison_view(place),
                "place_label": str((place or {}).get("action") or "place"),
            }
        )
    return comparisons


def _action_object_id(action: str) -> str:
    parts = action.split()
    if len(parts) >= 2:
        return parts[1]
    return ""


def _best_comparison_view(step: dict[str, Any] | None) -> str:
    if not step:
        return ""
    views = step.get("views") or {}
    return str(views.get("fpv") or views.get("verify") or views.get("chase") or "")


def _comparison_figure(path: Any, label: str, caption: Any) -> str:
    if not path:
        return '<figure class="comparison-missing"><figcaption>Missing view</figcaption></figure>'
    escaped_label = html.escape(label)
    escaped_caption = html.escape(str(caption or label))
    return (
        "<figure>"
        f"{_review_image(path, label)}"
        f"<figcaption><strong>{escaped_label}</strong><span>{escaped_caption}</span></figcaption>"
        "</figure>"
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


def _object_moves_section(moves: list[dict[str, Any]]) -> str:
    return f"""
    <section class="panel">
      <h2>Object Moves</h2>
      {_moves_table(moves)}
    </section>
    """


def _score_section(score: dict[str, Any]) -> str:
    return f"""
    <section class="panel">
      <h2>Score</h2>
      {_score_table(score)}
    </section>
    """


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )


def _summary_metrics(run_result: dict[str, Any], score: dict[str, Any]) -> str:
    semantic = score.get("semantic_acceptability")
    semantic_count = ""
    if isinstance(semantic, dict):
        semantic_count = f"{semantic.get('accepted_count', 0)}/{semantic.get('total_targets', 0)}"
    restored_count = f"{score.get('restored_count', 0)}/{score.get('total_targets', 0)}"
    return (
        '<div class="metric-grid">'
        f"{_metric('Status', _summary_status_label(run_result.get('cleanup_status', 'unknown')))}"
        f"{_metric('Restored', restored_count)}"
        f"{_metric('Generated', _generated_mess_summary(run_result))}"
        f"{_metric('Sweep', _rate_text(run_result.get('sweep_coverage_rate')))}"
        f"{_metric('Disturbance', run_result.get('disturbance_count', 0))}"
        f"{_metric('Semantic', semantic_count or 'n/a')}"
        "</div>"
    )


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _summary_status_label(status: Any) -> str:
    value = str(status or "unknown")
    labels = {
        "physical_agibot_navigation_pilot_rehearsal": "Rehearsal",
        "physical_agibot_navigation_pilot_complete": "Pilot complete",
        "success": "Success",
        "partial_success": "Partial success",
        "failed": "Failed",
    }
    return labels.get(value, value.replace("_", " ").title())


def _rate_text(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.0%}"
    return "n/a" if value is None else str(value)


def _robot_badge(run_result: dict[str, Any]) -> str:
    robot_name = run_result.get("robot_name")
    if not robot_name:
        return ""
    return _badge("Robot", robot_name)


def _robot_view_camera_badges(run_result: dict[str, Any]) -> str:
    summary = run_result.get("robot_view_camera_control")
    if not isinstance(summary, dict):
        return ""
    return _badge("Robot-view camera", summary.get("status", "unknown")) + _badge(
        "Head-camera FPV", summary.get("head_camera_fpv", False)
    )


def _confidence_layer_badges(run_result: dict[str, Any]) -> str:
    layer = run_result.get("confidence_layer")
    if not layer:
        return ""
    return "".join(
        (
            _badge("Confidence layer", layer),
            _badge("Next layer", run_result.get("next_confidence_layer", "unknown")),
        )
    )


def _generated_mess_summary(run_result: dict[str, Any]) -> str:
    actual = run_result.get("generated_mess_count")
    requested = run_result.get("requested_generated_mess_count")
    if actual is None:
        return "n/a"
    if requested is None or requested == actual:
        return actual
    return f"{actual} actual / {requested} requested"


def _realworld_contract_note(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    note = (
        "ADR-0003 real-world-style cleanup run. The Agent View is limited to "
        "metric map, room-level fixture hints, and robot-local observed object "
        "handles. Private Evaluation is shown only after the run."
    )
    return f'<section class="panel note-panel"><p class="note">{html.escape(note)}</p></section>'


def _confidence_layer_note(run_result: dict[str, Any]) -> str:
    layer = str(run_result.get("confidence_layer") or "")
    if not layer:
        return ""
    summary = str(run_result.get("confidence_layer_summary") or "")
    next_layer = str(run_result.get("next_confidence_layer") or "")
    note = layer
    if summary:
        note = f"{note}: {summary}"
    if next_layer:
        note = f"{note} Next confidence layer: {next_layer}."
    return f'<section class="panel note-panel"><p class="note">{html.escape(note)}</p></section>'


def _blocker_codes(blockers: list[dict[str, Any]]) -> str:
    return ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in blockers
        if isinstance(item, dict)
    )


def _proof_bundle_results_section(
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
                f"{item.get('request_id', '')} {_image_artifact_label(view.get('label', ''))}",
            )
            for view in views
            if isinstance(view, dict)
        )
        view_html = (
            f'<div class="views">{figures}</div>'
            f"{_post_placement_rejection_views(task_sampler_failure)}"
        )
    elif task_sampler_failure:
        view_html = (
            f"{_task_sampler_diagnostic_views(task_sampler_failure)}"
            f"{_post_placement_rejection_views(task_sampler_failure)}"
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


def _tail_text(value: Any, *, limit: int) -> str:
    text = str(value or "")
    return text[-limit:] if len(text) > limit else text


def _path_table(rows: list[tuple[str, Any]]) -> str:
    table_rows = "".join(
        f"<tr><td>{html.escape(str(label))}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in rows
    )
    return (
        '<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>Path</th>'
        "</tr></thead><tbody>" + table_rows + "</tbody></table></div>"
    )


def _planner_probe_views_section(evidence: dict[str, Any]) -> str:
    artifacts = evidence.get("image_artifacts") or {}
    if not artifacts:
        diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
        if diagnostics:
            return (
                '<section class="panel"><h2>Planner Probe Diagnostic Views</h2>'
                f"{_task_sampler_diagnostic_views(diagnostics)}</section>"
            )
        return ""
    figures = "".join(
        _view_figure(path, _image_artifact_label(label))
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


def _image_artifact_label(value: Any) -> str:
    text = str(value or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Planner view"
    return " ".join(part.capitalize() for part in text.split())


def _task_sampler_diagnostic_views(diagnostics: dict[str, Any]) -> str:
    if not diagnostics:
        return ""
    return f'<div class="views">{_task_sampler_diagnostic_figure(diagnostics)}</div>'


def _post_placement_rejection_views(diagnostics: dict[str, Any]) -> str:
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


def _planner_probe_cleanup_binding_section(evidence: dict[str, Any]) -> str:
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


def _planner_probe_task_sampler_robot_placement_profile_section(evidence: dict[str, Any]) -> str:
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


def _planner_probe_task_sampler_failure_section(evidence: dict[str, Any]) -> str:
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


def _planner_probe_placement_scene_diagnostics_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
    scene_diagnostics = diagnostics.get("placement_scene_diagnostics") or []
    if not scene_diagnostics:
        return ""
    last = diagnostics.get("last_placement_scene_diagnostic") or scene_diagnostics[-1]
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Scene diagnostics', _scene_diagnostic_count(diagnostics, scene_diagnostics))}"
        f"{_metric('Valid free points', last.get('valid_free_point_count', ''))}"
        f"{_metric('Free-space fraction', _scene_free_space_fraction(last))}"
        f"{_metric('Low free space', _yes_no(last.get('low_free_space')))}"
        f"{_metric('Nearest free distance', last.get('nearest_free_point_distance_m', ''))}"
        "</div>"
    )
    rows = [
        ("Target", last.get("target_name", "")),
        ("Target position", last.get("target_position", "")),
        ("Sampling radius range", last.get("sampling_radius_range", "")),
        ("Sampling area m2", last.get("sampling_area_m2", "")),
        ("Robot safety radius", last.get("robot_safety_radius", "")),
        ("px per meter", last.get("px_per_m", "")),
        ("Total free points", last.get("total_free_point_count", "")),
        ("Nearest free point", last.get("nearest_free_point", "")),
        ("Error", last.get("error", "")),
    ]
    scene_rows = "".join(
        _placement_scene_diagnostic_row(item)
        for item in scene_diagnostics
        if isinstance(item, dict)
    )
    scene_table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Target</th>'
        "<th>Valid free points</th><th>Free-space fraction</th>"
        "<th>Nearest free distance</th><th>Low free space</th></tr></thead>"
        f"<tbody>{scene_rows}</tbody></table></div>"
        if scene_rows
        else ""
    )
    band_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('radius_min_m', '')))}</td>"
        f"<td>{html.escape(str(item.get('radius_max_m', '')))}</td>"
        f"<td>{html.escape(str(item.get('free_point_count', '')))}</td>"
        "</tr>"
        for item in last.get("radius_band_counts") or []
        if isinstance(item, dict)
    )
    band_table = (
        '<div class="table-wrap"><table><thead><tr><th>Radius min m</th>'
        "<th>Radius max m</th><th>Free points</th></tr></thead>"
        f"<tbody>{band_rows}</tbody></table></div>"
        if band_rows
        else ""
    )
    note = (
        "Scene diagnostics summarize public map free-space around the actual "
        "upstream robot-placement target. They explain placement feasibility "
        "without changing cleanup semantics."
    )
    return (
        '<section class="panel planner-probe-placement-scene-diagnostics">'
        "<h2>Placement Scene Diagnostics</h2>"
        f'<p class="note">{html.escape(note)}</p>{metrics}{_field_table(rows)}'
        f"{scene_table}{band_table}</section>"
    )


def _planner_probe_grasp_collision_diagnostics_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
    load_attempts = [
        item for item in diagnostics.get("grasp_load_attempts") or [] if isinstance(item, dict)
    ]
    collision_checks = [
        item for item in diagnostics.get("grasp_collision_checks") or [] if isinstance(item, dict)
    ]
    if not load_attempts and not collision_checks:
        return ""
    last_load = diagnostics.get("last_grasp_load_attempt") or (
        load_attempts[-1] if load_attempts else {}
    )
    last_check = diagnostics.get("last_grasp_collision_check") or (
        collision_checks[-1] if collision_checks else {}
    )
    load_count = diagnostics.get("grasp_load_attempt_count", len(load_attempts))
    check_count = diagnostics.get("grasp_collision_check_count", len(collision_checks))
    zero_noncolliding = _yes_no(last_check.get("zero_noncolliding")) if last_check else ""
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Grasp load attempts', load_count)}"
        f"{_metric('Cached grasps', last_load.get('cached_grasp_count', ''))}"
        f"{_metric('Collision checks', check_count)}"
        f"{_metric('Non-colliding grasps', last_check.get('noncolliding_grasp_count', ''))}"
        f"{_metric('Zero non-colliding', zero_noncolliding)}"
        "</div>"
    )
    rows = [
        ("Asset UID", last_check.get("asset_uid", "") or last_load.get("asset_uid", "")),
        (
            "Pickup object",
            last_check.get("pickup_obj_name", "") or last_load.get("pickup_obj_name", ""),
        ),
        ("Requested grasp count", last_load.get("requested_grasp_count", "")),
        ("Gripper", last_load.get("gripper", "")),
        ("Grasp pose count", last_check.get("grasp_pose_count", "")),
        ("Batch size", last_check.get("batch_size", "")),
        ("Colliding grasps", last_check.get("colliding_grasp_count", "")),
        ("Load exception", last_load.get("exception_type", "")),
        ("Collision exception", last_check.get("exception_type", "")),
    ]
    load_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('asset_uid', '')))}</td>"
        f"<td>{html.escape(str(item.get('requested_grasp_count', '')))}</td>"
        f"<td>{html.escape(str(item.get('result', '')))}</td>"
        f"<td>{html.escape(str(item.get('gripper', '')))}</td>"
        f"<td>{html.escape(str(item.get('cached_grasp_count', '')))}</td>"
        f"<td>{html.escape(str(item.get('exception_type', '')))}</td>"
        "</tr>"
        for item in load_attempts
    )
    load_table = (
        "<h3>Grasp Load Attempts</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Asset UID</th>'
        "<th>Requested grasps</th><th>Result</th><th>Gripper</th>"
        "<th>Cached grasps</th><th>Exception</th></tr></thead>"
        f"<tbody>{load_rows}</tbody></table></div>"
        if load_rows
        else ""
    )
    check_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('asset_uid', '')))}</td>"
        f"<td>{html.escape(str(item.get('grasp_pose_count', '')))}</td>"
        f"<td>{html.escape(str(item.get('noncolliding_grasp_count', '')))}</td>"
        f"<td>{html.escape(str(item.get('colliding_grasp_count', '')))}</td>"
        f"<td>{html.escape(str(item.get('zero_noncolliding', '')))}</td>"
        f"<td>{html.escape(str(item.get('exception_type', '')))}</td>"
        "</tr>"
        for item in collision_checks
    )
    check_table = (
        "<h3>Grasp Collision Checks</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Asset UID</th>'
        "<th>Total grasps</th><th>Non-colliding</th><th>Colliding</th>"
        "<th>Zero non-colliding</th><th>Exception</th></tr></thead>"
        f"<tbody>{check_rows}</tbody></table></div>"
        if check_rows
        else ""
    )
    note = (
        "Grasp collision diagnostics wrap the upstream grasp loader and "
        "non-colliding grasp mask. They explain whether post-placement failure "
        "comes from missing cached grasps or zero feasible collision-free grasps."
    )
    return (
        '<section class="panel planner-probe-grasp-collision-diagnostics">'
        "<h2>Grasp Collision Diagnostics</h2>"
        f'<p class="note">{html.escape(note)}</p>{metrics}{_field_table(rows)}'
        f"{load_table}{check_table}</section>"
    )


def _planner_probe_post_placement_rejection_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("task_sampler_failure_diagnostics") or {}
    grasp_failures = diagnostics.get("grasp_failures") or []
    if not grasp_failures:
        return ""
    removed = [
        item for item in grasp_failures if isinstance(item, dict) and item.get("removed_candidate")
    ]
    effective_removals = (
        _safe_int(diagnostics.get("candidate_effective_removal_count"), 0)
        if "candidate_effective_removal_count" in diagnostics
        else len(removed)
    )
    candidate_name_misses = _safe_int(diagnostics.get("candidate_name_miss_count"), 0)
    threshold_exceeded = _safe_int(diagnostics.get("grasp_threshold_exceeded_count"), 0)
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Grasp failures', diagnostics.get('grasp_failure_count', len(grasp_failures)))}"
        f"{_metric('Candidate removal calls', diagnostics.get('candidate_removal_count', 0))}"
        f"{_metric('Removed by grasp threshold', len(removed))}"
        f"{_metric('Effective removals', effective_removals)}"
        f"{_metric('Candidate name misses', candidate_name_misses)}"
        f"{_metric('Threshold exceeded rows', threshold_exceeded)}"
        "</div>"
    )
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('object_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('count_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('count_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('max_failures', '')))}</td>"
        f"<td>{html.escape(str(item.get('threshold_exceeded', '')))}</td>"
        f"<td>{html.escape(str(item.get('threshold_crossed', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_name_present_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_name_present_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_removal_call_count_delta', '')))}</td>"
        f"<td>{html.escape(str(item.get('removed_candidate', '')))}</td>"
        "</tr>"
        for item in grasp_failures
        if isinstance(item, dict)
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Count before</th><th>Count after</th><th>Max failures</th>"
        "<th>Threshold exceeded</th><th>Threshold crossed</th>"
        "<th>Candidates before</th><th>Candidates after</th>"
        "<th>Name present before</th><th>Name present after</th>"
        "<th>Removal-call delta</th><th>Removed</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )
    removal_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('object_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_count_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_name_present_before', '')))}</td>"
        f"<td>{html.escape(str(item.get('candidate_name_present_after', '')))}</td>"
        f"<td>{html.escape(str(item.get('effective_removal', '')))}</td>"
        "</tr>"
        for item in diagnostics.get("candidate_removals") or []
        if isinstance(item, dict)
    )
    removal_table = (
        "<h3>Candidate Removal Effectiveness</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Candidates before</th><th>Candidates after</th>"
        "<th>Name present before</th><th>Name present after</th>"
        "<th>Effective removal</th></tr></thead>"
        f"<tbody>{removal_rows}</tbody></table></div>"
        if removal_rows
        else ""
    )
    note = (
        "Post-placement candidate rejection diagnostics explain failures after "
        "robot placement succeeds, such as grasp-feasibility thresholds removing "
        "the sampled object from the candidate pool."
    )
    return (
        '<section class="panel planner-probe-post-placement-rejections">'
        "<h2>Post-Placement Candidate Rejections</h2>"
        f'<p class="note">{html.escape(note)}</p>{metrics}'
        f"{_post_placement_rejection_views(diagnostics)}{table}{removal_table}</section>"
    )


def _placement_scene_diagnostic_row(item: dict[str, Any]) -> str:
    return (
        "<tr>"
        f"<td>{html.escape(str(item.get('call_index', '')))}</td>"
        f"<td>{html.escape(str(item.get('target_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('valid_free_point_count', '')))}</td>"
        f"<td>{html.escape(str(_scene_free_space_fraction(item)))}</td>"
        f"<td>{html.escape(str(item.get('nearest_free_point_distance_m', '')))}</td>"
        f"<td>{html.escape(str(item.get('low_free_space', '')))}</td>"
        "</tr>"
    )


def _scene_diagnostic_count(
    diagnostics: dict[str, Any],
    scene_diagnostics: list[dict[str, Any]],
) -> Any:
    return diagnostics.get("placement_scene_diagnostic_count", len(scene_diagnostics))


def _format_fraction(value: Any) -> Any:
    if isinstance(value, float):
        return f"{value:.6f}"
    return value


def _scene_free_space_fraction(item: dict[str, Any]) -> Any:
    return _format_fraction(item.get("valid_neighborhood_fraction", ""))


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


def _planner_probe_diagnostics_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    if not diagnostics:
        return ""
    modules = diagnostics.get("modules") or {}
    rows = []
    for module_name, module_info in sorted(modules.items()):
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(module_name))}</td>"
            f"<td>{html.escape(str(module_info.get('available', False)))}</td>"
            f"<td>{html.escape(str(module_info.get('version') or ''))}</td>"
            "</tr>"
        )
    module_table = (
        '<div class="table-wrap"><table><thead><tr><th>Module</th><th>Available</th>'
        "<th>Version</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    summary = (
        f"python={diagnostics.get('python_version', '')}; "
        f"executable={diagnostics.get('python_executable', '')}; "
        f"faulthandler={diagnostics.get('faulthandler_enabled', False)}; "
        f"renderer_adapter={diagnostics.get('renderer_adapter_enabled', False)}; "
        f"renderer_device={diagnostics.get('renderer_device_id', '')}; "
        f"MUJOCO_GL={diagnostics.get('mujoco_gl_env', '')}; "
        f"PYOPENGL_PLATFORM={diagnostics.get('pyopengl_platform_env', '')}; "
        f"CUDA_HOME={diagnostics.get('cuda_home_env', '')}; "
        f"TORCH_CUDA_ARCH_LIST={diagnostics.get('torch_cuda_arch_list_env', '')}"
    )
    torch_info = diagnostics.get("torch") or {}
    torch_summary = (
        f"torch={torch_info.get('version', '')}; "
        f"torch_cuda={torch_info.get('cuda_version', '')}; "
        f"torch_cuda_available={torch_info.get('cuda_available', False)}; "
        f"torch_cuda_home={torch_info.get('cpp_extension_cuda_home', '')}"
    )
    return (
        '<section class="panel"><h2>Runtime Diagnostics</h2>'
        f'<p class="note">{html.escape(summary)}</p>'
        f'<p class="note">{html.escape(torch_summary)}</p>{module_table}</section>'
    )


def _planner_probe_cuda_memory_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    cuda = diagnostics.get("cuda_memory") or {}
    snapshots = _planner_probe_cuda_memory_snapshots(evidence)
    if not cuda and not snapshots:
        return ""
    current = cuda.get("current_snapshot") or (snapshots[-1] if snapshots else {})
    free_memory = _memory_pair(current.get("free_bytes"), current.get("total_bytes"))
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('CUDA', 'available' if cuda.get('available') else 'missing')}"
        f"{_metric('Device count', cuda.get('device_count', 0))}"
        f"{_metric('Current device', _cuda_device_label(current, cuda))}"
        f"{_metric('Free memory', free_memory)}"
        f"{_metric('Torch allocated', _format_bytes(current.get('torch_allocated_bytes')))}"
        f"{_metric('Torch reserved', _format_bytes(current.get('torch_reserved_bytes')))}"
        "</div>"
    )
    env_note = (
        f"CUDA_VISIBLE_DEVICES={diagnostics.get('cuda_visible_devices_env', '')}; "
        f"PYTORCH_CUDA_ALLOC_CONF={diagnostics.get('pytorch_cuda_alloc_conf_env', '')}"
    )
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('elapsed_s', '')))}</td>"
        f"<td>{html.escape(str(item.get('stage', '')))}</td>"
        f"<td>{html.escape(_cuda_device_label(item, cuda))}</td>"
        f"<td>{html.escape(_memory_pair(item.get('free_bytes'), item.get('total_bytes')))}</td>"
        f"<td>{html.escape(_format_bytes(item.get('torch_allocated_bytes')))}</td>"
        f"<td>{html.escape(_format_bytes(item.get('torch_reserved_bytes')))}</td>"
        f"<td>{html.escape(str(item.get('error') or item.get('error_type') or ''))}</td>"
        "</tr>"
        for item in snapshots
    )
    if not rows:
        rows = '<tr><td colspan="7">No stage snapshots recorded.</td></tr>'
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Elapsed s</th><th>Stage</th>'
        "<th>Device</th><th>Free / total</th><th>Torch allocated</th>"
        "<th>Torch reserved</th><th>Error</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
    )
    note = (
        "CUDA memory headroom is runtime evidence only. OOM-blocked artifacts "
        "still do not satisfy strict planner-backed cleanup readiness."
    )
    return (
        '<section class="panel"><h2>CUDA Memory Headroom</h2>'
        f'<p class="note">{html.escape(note)}</p>'
        f'<p class="note">{html.escape(env_note)}</p>{metrics}{table}</section>'
    )


def _planner_probe_cuda_memory_snapshots(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = list(evidence.get("cuda_memory_snapshots") or [])
    if snapshots:
        return snapshots
    return [
        item["cuda_memory"]
        for item in evidence.get("worker_stage_events") or []
        if item.get("event") == "cuda_memory_snapshot" and item.get("cuda_memory")
    ]


def _cuda_device_label(snapshot: dict[str, Any], diagnostics: dict[str, Any]) -> str:
    device_name = snapshot.get("device_name")
    if not device_name:
        devices = diagnostics.get("devices") or []
        current_index = snapshot.get("device_index", diagnostics.get("current_device_index"))
        device = next((item for item in devices if item.get("index") == current_index), {})
        device_name = device.get("name")
    device_index = snapshot.get("device_index", diagnostics.get("current_device_index", ""))
    if device_name:
        return f"{device_index}: {device_name}"
    return str(device_index)


def _memory_pair(free_bytes: Any, total_bytes: Any) -> str:
    if free_bytes is None and total_bytes is None:
        return "unknown"
    return f"{_format_bytes(free_bytes)} / {_format_bytes(total_bytes)}"


def _format_bytes(value: Any) -> str:
    if value in (None, ""):
        return "unknown"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    unit = units[0]
    for unit in units:
        if abs(amount) < 1024.0 or unit == units[-1]:
            break
        amount /= 1024.0
    if unit == "B":
        return str(int(amount))
    return f"{amount:.1f} {unit}"


def _planner_probe_curobo_memory_profile_section(evidence: dict[str, Any]) -> str:
    profile = evidence.get("curobo_memory_profile") or {}
    if not profile:
        return ""
    after = profile.get("after") or {}
    policy = after.get("policy") or {}
    planners = after.get("planners") or {}
    first_planner = next(iter(planners.values()), {})
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Profile', profile.get('profile', 'unknown'))}"
        f"{_metric('Applied', _yes_no(profile.get('applied')))}"
        f"{_metric('Batch size', policy.get('batch_size', 'unknown'))}"
        f"{_metric('Max batches', policy.get('max_batch_plan_attempts', 'unknown'))}"
        f"{_metric('Collision avoidance', _yes_no(policy.get('enable_collision_avoidance')))}"
        f"{_metric('Trajopt seeds', first_planner.get('num_trajopt_seeds', 'unknown'))}"
        "</div>"
    )
    before = profile.get("before") or {}
    rows = _curobo_profile_rows(
        "policy",
        before.get("policy") or {},
        policy,
        ("batch_size", "max_batch_plan_attempts", "enable_collision_avoidance"),
    )
    before_planners = before.get("planners") or {}
    for planner_name, planner_after in sorted(planners.items()):
        rows.extend(
            _curobo_profile_rows(
                f"{planner_name}_planner",
                before_planners.get(planner_name) or {},
                planner_after,
                (
                    "num_trajopt_seeds",
                    "num_ik_seeds",
                    "max_attempts",
                    "trajopt_tsteps",
                    "enable_finetune_trajopt",
                ),
            )
        )
    table_rows = "".join(rows) or '<tr><td colspan="4">No profile values recorded.</td></tr>'
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Scope</th><th>Setting</th>'
        f"<th>Before</th><th>After</th></tr></thead><tbody>{table_rows}</tbody></table></div>"
    )
    note = (
        "CuRobo memory profile is probe-local runtime evidence. Tuning state is "
        "visible before target readiness or cleanup primitive replacement is considered."
    )
    return (
        '<section class="panel"><h2>CuRobo Memory Profile</h2>'
        f'<p class="note">{html.escape(note)}</p>{metrics}{table}</section>'
    )


def _curobo_profile_rows(
    scope: str,
    before: dict[str, Any],
    after: dict[str, Any],
    keys: tuple[str, ...],
) -> list[str]:
    rows = []
    for key in keys:
        rows.append(
            "<tr>"
            f"<td>{html.escape(scope)}</td>"
            f"<td>{html.escape(key)}</td>"
            f"<td>{html.escape(str(before.get(key, '')))}</td>"
            f"<td>{html.escape(str(after.get(key, '')))}</td>"
            "</tr>"
        )
    return rows


def _planner_probe_policy_exception_section(evidence: dict[str, Any]) -> str:
    context = evidence.get("policy_exception_context") or {}
    if not context:
        return ""
    primitives = context.get("action_primitives") or []
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Failure kind', context.get('failure_kind', 'unknown'))}"
        f"{_metric('Stage', context.get('stage', 'unknown'))}"
        f"{_metric('Exception', context.get('exception_type', 'unknown'))}"
        f"{_metric('No planned trajectory', _yes_no(context.get('no_planned_trajectory')))}"
        f"{_metric('Steps requested', context.get('steps_requested', 'unknown'))}"
        f"{_metric('Primitives', context.get('action_primitive_count', len(primitives)))}"
        "</div>"
    )
    message = str(context.get("message") or "")
    rows = []
    for primitive in primitives:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(primitive.get('index', '')))}</td>"
            f"<td>{html.escape(str(primitive.get('primitive_class', '')))}</td>"
            f"<td>{html.escape(str(primitive.get('current_phase', '')))}</td>"
            f"<td>{html.escape(_yes_no(primitive.get('planned_trajectory_present')))}</td>"
            f"<td>{html.escape(str(primitive.get('planned_trajectory_len', '')))}</td>"
            f"<td>{html.escape(str(primitive.get('trajectory_index', '')))}</td>"
            "</tr>"
        )
    table_rows = "".join(rows) or '<tr><td colspan="6">No action primitives recorded.</td></tr>'
    table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Primitive</th>'
        "<th>Current phase</th><th>Planned trajectory</th><th>Trajectory len</th>"
        f"<th>Trajectory index</th></tr></thead><tbody>{table_rows}</tbody></table></div>"
    )
    detail_rows = "".join(
        f"<tr><td>{html.escape(label)}</td><td>{html.escape(str(value))}</td></tr>"
        for label, value in (
            ("Policy class", context.get("policy_class") or ""),
            ("Policy phase", context.get("policy_current_phase") or ""),
            ("Message", message),
        )
    )
    details = (
        '<div class="table-wrap"><table><thead><tr><th>Signal</th><th>Value</th>'
        f"</tr></thead><tbody>{detail_rows}</tbody></table></div>"
    )
    note = (
        "Policy exception diagnostics preserve the planner primitive state at the "
        "target-runtime failure point, before the artifact is collapsed into a "
        "blocked-capability result."
    )
    return (
        '<section class="panel"><h2>Policy Exception Diagnostics</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{details}{table}</section>'
    )


def _planner_probe_curobo_extension_cache_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    cache = diagnostics.get("curobo_extension_cache") or {}
    extensions = cache.get("extensions") or {}
    if not extensions:
        return ""
    rows = []
    lock_count = 0
    so_count = 0
    for name, item in sorted(extensions.items()):
        if item.get("lock_exists"):
            lock_count += 1
        if item.get("so_exists"):
            so_count += 1
        files = item.get("files") or []
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(name))}</td>"
            f"<td>{html.escape(str(item.get('build_dir', '')))}</td>"
            f"<td>{html.escape(_yes_no(item.get('so_exists')))}</td>"
            f"<td>{html.escape(_yes_no(item.get('lock_exists')))}</td>"
            f"<td>{len(files)}</td>"
            f"<td>{html.escape(_curobo_cache_file_detail(files))}</td>"
            "</tr>"
        )
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Configured dir', cache.get('configured_dir') or 'default')}"
        f"{_metric('Extensions', len(extensions))}"
        f"{_metric('Compiled .so', f'{so_count}/{len(extensions)}')}"
        f"{_metric('Locks', lock_count)}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Extension</th>'
        "<th>Build dir</th><th>.so</th><th>Lock</th><th>Files</th><th>Detail</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    note = (
        "CuRobo planner imports JIT-compile several Torch CUDA extensions. "
        "This panel makes stale locks and missing binaries visible before strict readiness."
    )
    return (
        '<section class="panel"><h2>CuRobo Extension Cache</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def _curobo_cache_file_detail(files: list[dict[str, Any]]) -> str:
    if not files:
        return ""
    return "; ".join(f"{item.get('name')}:{item.get('size_bytes')}" for item in files[:6])


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"


def _planner_probe_warp_compatibility_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    warp = diagnostics.get("warp_compatibility") or {}
    if not warp:
        return ""
    adapter = warp.get("adapter") or {}
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Warp', 'available' if warp.get('available') else 'missing')}"
        f"{_metric('Version', warp.get('version') or 'unknown')}"
        f"{_metric('warp.torch', _yes_no(warp.get('has_torch_attr')))}"
        f"{_metric('Adapter applied', _yes_no(adapter.get('applied')))}"
        "</div>"
    )
    rows = [
        ("has_device_from_torch", warp.get("has_device_from_torch")),
        ("has_from_torch", warp.get("has_from_torch")),
        ("has_stream_from_torch", warp.get("has_stream_from_torch")),
        ("adapter_reason", adapter.get("reason", "")),
        ("adapter_provided", ", ".join(adapter.get("provided") or [])),
    ]
    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(name))}</td>"
        f"<td>{html.escape(_yes_no(value) if isinstance(value, bool) else str(value))}</td>"
        "</tr>"
        for name, value in rows
        if value not in (None, "", [])
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Signal</th><th>Value</th>'
        "</tr></thead><tbody>" + table_rows + "</tbody></table></div>"
    )
    note = (
        "Warp compatibility is probe-local runtime evidence. It makes any "
        "adapter visible before strict RBY1M/CuRobo readiness is considered."
    )
    return (
        '<section class="panel"><h2>Warp Compatibility</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def _planner_probe_worker_stages_section(evidence: dict[str, Any]) -> str:
    events = evidence.get("worker_stage_events") or []
    if not events:
        return ""
    rows = []
    for item in events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('elapsed_s', '')))}</td>"
            f"<td>{html.escape(str(item.get('event', '')))}</td>"
            f"<td>{html.escape(str(item.get('stage', '')))}</td>"
            f"<td>{html.escape(_worker_stage_detail(item))}</td>"
            "</tr>"
        )
    last_stage = evidence.get("last_worker_stage") or events[-1].get("stage")
    note = (
        "Worker stage events are emitted before expensive RBY1M/CuRobo warmup "
        "and execution steps, so timeout artifacts preserve the last observed stage."
    )
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Events', len(events))}"
        f"{_metric('Last stage', last_stage or 'unknown')}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Elapsed s</th>'
        "<th>Event</th><th>Stage</th><th>Detail</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    return (
        '<section class="panel"><h2>Worker Stage Timeline</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def _worker_stage_detail(item: dict[str, Any]) -> str:
    details = []
    for key in (
        "embodiment",
        "probe_mode",
        "upstream_policy_class",
        "steps",
        "steps_executed",
        "max_abs_qpos_delta",
    ):
        value = item.get(key)
        if value not in (None, ""):
            details.append(f"{key}={value}")
    cuda_memory = item.get("cuda_memory")
    if isinstance(cuda_memory, dict):
        details.append(f"cuda_free={_format_bytes(cuda_memory.get('free_bytes'))}")
        details.append(f"torch_reserved={_format_bytes(cuda_memory.get('torch_reserved_bytes'))}")
    return "; ".join(details)


def _rby1m_curobo_gate_section(run_result: dict[str, Any]) -> str:
    gate = run_result.get("rby1m_curobo_gate") or {}
    if not gate:
        return ""
    blockers = gate.get("blockers") or []
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('code', '')))}</td>"
        f"<td>{html.escape(str(item.get('message', '')))}</td>"
        "</tr>"
        for item in blockers
    )
    if not rows:
        rows = '<tr><td colspan="2">None</td></tr>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', gate.get('status', 'unknown'))}"
        f"{_metric('Embodiment', gate.get('embodiment', 'unknown'))}"
        f"{_metric('CuRobo', 'available' if gate.get('curobo_available') else 'missing')}"
        f"{_metric('Execution', _execution_gate_label(gate))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("RBY1M CuRobo ready", gate.get("rby1m_curobo_ready", False)),
            _badge("Planner backed", gate.get("planner_backed", False)),
            _badge("Strict proof", gate.get("strict_proof_eligible", False)),
        )
    )
    note = gate.get("evidence_note") or (
        "RBY1M/CuRobo readiness requires target-robot planner execution."
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Blocker</th>'
        f"<th>Message</th></tr></thead><tbody>{rows}</tbody></table></div>"
    )
    return (
        '<section class="panel rby1m-curobo-gate">'
        "<h2>RBY1M CuRobo Gate</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div>{table}</section>'
    )


def _execution_gate_label(gate: dict[str, Any]) -> str:
    return "attempted" if gate.get("execution_attempted") else "not attempted"


def _planner_probe_blockers_section(evidence: dict[str, Any]) -> str:
    blockers = evidence.get("blockers") or []
    if not blockers:
        return ""
    rows = []
    for blocker in blockers:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(blocker.get('code', 'blocked')))}</td>"
            f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
            "</tr>"
        )
    return (
        '<section class="panel"><h2>Capability Blockers</h2>'
        '<div class="table-wrap"><table><thead><tr><th>Code</th><th>Message</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></section>"
    )


def _planner_probe_artifacts_section(run_result: dict[str, Any]) -> str:
    artifacts = run_result.get("artifacts") or {}
    rows = []
    for key in ("stdout", "stderr"):
        value = artifacts.get(key)
        if value:
            rows.append(f"<tr><td>{html.escape(key)}</td><td>{html.escape(str(value))}</td></tr>")
    if not rows:
        return ""
    return (
        '<section class="panel"><h2>Probe Artifacts</h2>'
        '<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>Path</th>'
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div></section>"
    )


def _molmospaces_agibot_rehearsal_section(run_dir: Path, run_result: dict[str, Any]) -> str:
    rehearsal = run_result.get("molmospaces_agibot_contract_rehearsal") or {}
    if not rehearsal:
        return ""
    scene = run_result.get("molmospaces_scene") or {}
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    rooms = metric_map.get("rooms") or []
    waypoints = metric_map.get("inspection_waypoints") or []
    fixtures = []
    for room in fixture_hints.get("rooms") or []:
        fixtures.extend(room.get("fixtures") or [])
    runtime = str(scene.get("runtime") or rehearsal.get("runtime") or "unknown")
    if runtime == "fixture":
        note = (
            "This report used the CI-safe fixture runtime: a deterministic "
            "MolmoSpaces cleanup-contract projection with public rooms, fixtures, "
            "and inspection waypoints. It is intentionally not a live MuJoCo "
            "MolmoSpaces scene_xml run. Use --runtime molmospaces-subprocess for "
            "heavier local simulator evidence."
        )
    else:
        note = (
            "This report used the MolmoSpaces subprocess runtime and carries live "
            "simulator scene metadata when the optional MolmoSpaces/MuJoCo stack is "
            "installed."
        )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Runtime', runtime)}"
        f"{_metric('Scenario', scene.get('scenario_id', run_result.get('scenario_id', 'unknown')))}"
        f"{_metric('Scene source', scene.get('scene_source', 'unknown'))}"
        f"{_metric('Map id', metric_map.get('map_id', 'unknown'))}"
        f"{_metric('Rooms', len(rooms))}"
        f"{_metric('Fixtures', len(fixtures))}"
        f"{_metric('Waypoints', len(waypoints))}"
        f"{_metric('Simulated', rehearsal.get('simulated', 'n/a'))}"
        "</div>"
    )
    preview = str(rehearsal.get("map_preview") or "")
    figure = (
        '<figure class="map-preview-figure">'
        f"{_review_image(preview, 'MolmoSpaces metric map preview')}"
        "<figcaption>Agent-facing metric map projection: rooms, fixtures, and "
        "inspection waypoints used by the Agibot-shaped rehearsal.</figcaption>"
        "</figure>"
        if preview
        else ""
    )
    paths = _path_table(
        [
            ("Scene identity", rehearsal.get("scene_identity", "")),
            ("Agent view preflight", rehearsal.get("agent_view_preflight", "")),
            ("Waypoint sequence", rehearsal.get("waypoint_sequence", "")),
            ("Runner task input", rehearsal.get("runner_task_input", "")),
            ("Runtime export", rehearsal.get("runtime_export", "")),
        ]
    )
    return (
        '<section class="panel molmospaces-agibot-rehearsal">'
        "<h2>MolmoSpaces Scene &amp; Map <span>Agibot-shaped rehearsal</span></h2>"
        f'<p class="note">{html.escape(note)}</p>'
        f"{metrics}{figure}{paths}</section>"
    )


def _agibot_sdk_runner_section(run_dir: Path, run_result: dict[str, Any]) -> str:
    runner = run_result.get("agibot_sdk_runner") or {}
    if not runner:
        return ""
    is_molmospaces_rehearsal = (
        runner.get("rehearsal_kind") == "molmospaces_agibot_contract_rehearsal"
    )
    rows = []
    for item in runner.get("subphase_reports") or []:
        stage = str(item.get("stage", ""))
        report = str(item.get("report") or "")
        run_result_path = str(item.get("run_result") or "")
        rows.append(
            "<tr>"
            f"<td>{html.escape(stage)}</td>"
            f"<td>{html.escape(_agibot_public_tool_mapping(stage))}</td>"
            f"<td>{html.escape(_agibot_subphase_status_label(item))}</td>"
            f"<td>{_artifact_link(report, run_dir)}</td>"
            f"<td>{_artifact_link(run_result_path, run_dir)}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Backend stage</th><th>Maps to public tool</th><th>Evidence status</th>"
        "<th>Report</th><th>Run result</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    tools = ", ".join(str(item) for item in runner.get("public_tool_boundary") or [])
    gdk_imported = runner.get("gdk_imported_by_roboclaws", "unknown")
    next_layer = str(runner.get("next_confidence_layer") or "")
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Backend variant', runner.get('backend_variant', 'unknown'))}"
        f"{_metric('Runtime', runner.get('runtime', 'n/a'))}"
        f"{_metric('Simulated', runner.get('simulated', 'n/a'))}"
        f"{_metric('Physical robot', runner.get('physical_robot', 'n/a'))}"
        f"{_metric('Movement enabled', runner.get('real_movement_enabled', False))}"
        f"{_metric('GDK imported by Roboclaws', gdk_imported)}"
        f"{_metric('Sub-phase reports', len(runner.get('subphase_reports') or []))}"
        "</div>"
    )
    if is_molmospaces_rehearsal:
        heading = "AgiBot-Shaped Sim Evidence <span>MolmoSpaces contract rehearsal</span>"
        intro = (
            "One simulated Roboclaws run is written in Agibot-shaped backend stages. "
            "The rows map preflight, observe, waypoint navigation, and blocked "
            "manipulation artifacts back to the same household public "
            "tool contract. This validates contract shape and evidence plumbing; "
            "it is not Agibot Map Visual Dry Run, not Agibot SDK Dry Run, not "
            "semantic cleanup mock evidence, and not real Agibot GDK execution."
        )
        next_layer_note = (
            '<p class="note">Next confidence layer: '
            f"{html.escape(next_layer)}. Real GDK navigation, physical robot "
            "readiness, and manipulation proof remain separate validation layers.</p>"
            if next_layer
            else ""
        )
    else:
        heading = "AgiBot Backend Evidence <span>CLI boundary</span>"
        intro = (
            "One Roboclaws pilot run is replayed through three SDK-owned backend "
            "stages. The table maps each backend artifact back to the public "
            "household tool it supports, so these rows read as "
            "evidence for the same cleanup-shaped run rather than separate tasks. "
            "Dry-run rows are reviewable rehearsal evidence, not physical PNC "
            "execution proof."
        )
        next_layer_note = (
            '<p class="note">Next confidence layer: '
            f"{html.escape(next_layer)}. This report is the map/SDK dry-run layer; "
            "semantic cleanup actions, MolmoSpaces simulation, and real GDK execution "
            "remain separate layers.</p>"
            if next_layer
            else ""
        )
    return (
        '<section class="panel agibot-sdk-runner">'
        f"<h2>{heading}</h2>"
        f'<p class="note">{html.escape(intro)}</p>'
        f"{metrics}"
        f'<p class="note">Public Roboclaws tools preserved: {html.escape(tools)}</p>'
        f"{next_layer_note}"
        f"{table}</section>"
    )


def _agibot_public_tool_mapping(stage: str) -> str:
    mappings = {
        "agent_view_export": "metric_map",
        "observe": "observe",
        "navigate_waypoint": "navigate_to_waypoint",
        "blocked_manipulation": "pick, place, place_inside, open_receptacle, close_receptacle",
    }
    return mappings.get(stage, "backend evidence")


def _agibot_subphase_status_label(item: dict[str, Any]) -> str:
    status = str(item.get("status") or "")
    if status == "ok":
        return "OK"
    if status == "dry_run_blocked_capability":
        return "Dry-run blocked"
    if item.get("ok") is True:
        return "OK"
    return status.replace("_", " ").title() if status else "Unknown"


def _artifact_link(path: str, run_dir: Path) -> str:
    if not path:
        return ""
    href = html.escape(path)
    label = html.escape(path)
    if (run_dir / path).exists():
        return f'<a href="{href}">{label}</a>'
    return label


def _camera_model_policy_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("camera_model_policy_evidence") or (
        (run_result.get("agent_view") or {}).get("camera_model_policy_evidence") or {}
    )
    if not evidence or not evidence.get("enabled"):
        return ""
    rows = []
    for event in evidence.get("events") or []:
        handles = ", ".join(str(item) for item in event.get("registered_observed_handles") or [])
        pipeline = event.get("visual_grounding_pipeline") or {}
        stages = pipeline.get("stages") or []
        stage_text = ", ".join(
            str(stage.get("stage") or stage.get("producer_id") or "") for stage in stages
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('observation_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('room_id', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('camera_labeler') or run_result.get('camera_labeler') or pipeline.get('pipeline_id', '')))}</td>"  # noqa: E501
            f"<td>{html.escape(str(pipeline.get('pipeline_id', '')))}</td>"
            f"<td>{html.escape(str(pipeline.get('status', '')))}</td>"
            f"<td>{html.escape(stage_text)}</td>"
            f"<td>{html.escape(str(pipeline.get('failure_reason', '')))}</td>"
            f"<td>{html.escape(str(event.get('candidate_count', 0)))}</td>"
            f"<td>{html.escape(handles)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="9">No camera-labeler candidate events recorded.</td></tr>')
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Events', evidence.get('event_count', 0))}"
        f"{_metric('Candidates', evidence.get('candidate_count', 0))}"
        f"{_metric('Camera labeler', evidence.get('camera_labeler', run_result.get('camera_labeler', '')))}"  # noqa: E501
        f"{_metric('Service pipeline', evidence.get('visual_grounding_pipeline_id', 'sim'))}"
        f"{_metric('Failures', evidence.get('visual_grounding_failure_count', 0))}"
        f"{_metric('Duplicate rate', evidence.get('duplicate_rate', 0))}"
        f"{_metric('Model', evidence.get('model_provenance', 'unknown'))}"
        f"{_metric('Private truth', evidence.get('private_truth_included', 'unknown'))}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Observation</th>'
        "<th>Room</th><th>Camera labeler</th><th>Service pipeline</th>"
        "<th>Status</th><th>Stages</th>"
        "<th>Failure reason</th><th>Candidates</th><th>Handles</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    note = evidence.get("policy_note") or (
        "Camera labeler candidates are model-labelled public observations, "
        "not private scoring truth."
    )
    return (
        '<section class="panel camera-model-policy"><h2>Camera Labeler Evidence</h2>'
        f'<p class="note">{html.escape(str(note))}</p>{metrics}{table}</section>'
    )


def _model_declared_observations_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("model_declared_observation_evidence") or (
        (run_result.get("agent_view") or {}).get("model_declared_observation_evidence") or {}
    )
    observations = run_result.get("model_declared_observations") or evidence.get(
        "observations",
        [],
    )
    if not observations:
        return ""
    rows = []
    for item in observations:
        region = item.get("image_region") or {}
        evidence = item.get("visual_grounding_evidence") or {}
        pipeline = item.get("visual_grounding_pipeline") or {}
        overlay = str(item.get("visual_grounding_overlay") or "")
        overlay_cell = f'<a href="{html.escape(overlay)}">overlay</a>' if overlay else ""
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('source_observation_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('producer_type', '')))}</td>"
            f"<td>{html.escape(str(pipeline.get('pipeline_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_fixture_id', '')))}</td>"
            f"<td>{html.escape(str(region.get('type', '')))}: "
            f"{html.escape(str(region.get('value', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('reviewability_status', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('image_bbox', '')))}</td>"
            f"<td>{html.escape(str(item.get('grounding_status', '')))} "
            f"({html.escape(str(item.get('grounding_confidence', '')))})</td>"
            f"<td>{html.escape(str(item.get('actionability_status', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_plausibility', {}).get('status', '')))}</td>"
            f"<td>{html.escape(str(item.get('acted_on', False)))}</td>"
            f"<td>{overlay_cell}</td>"
            f"<td>{html.escape(str(item.get('evidence_note', '')))}</td>"
            f"<td>{html.escape(str(item.get('recovery_hint', '')))}</td>"
            "</tr>"
        )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Declared', evidence.get('observation_count', len(observations)))}"
        f"{_metric('Resolved', evidence.get('resolved_count', 0))}"
        f"{_metric('Acted on', evidence.get('acted_count', 0))}"
        f"{_metric('Private truth', evidence.get('private_truth_included', False))}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Source observation</th>'
        "<th>Producer</th><th>Pipeline</th><th>Handle</th><th>Category</th><th>Target fixture</th>"
        "<th>Image region</th><th>FPV reviewability</th><th>FPV bbox</th>"
        "<th>Grounding</th><th>Actionability</th><th>Target plausibility</th>"
        "<th>Acted on</th><th>Overlay</th><th>Evidence note</th><th>Recovery hint</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    return (
        '<section class="panel model-declared-observations">'
        "<h2>Model-Declared Observations</h2>"
        '<p class="note">Public camera evidence converted into observed handles. '
        "Grounding status shows whether the hidden resolver found an executable "
        "object without exposing private scoring truth.</p>"
        f"{metrics}{table}</section>"
    )


def _raw_fpv_observations_section(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    observations = run_result.get("raw_fpv_observations") or (
        (run_result.get("agent_view") or {}).get("raw_fpv_observations") or []
    )
    if not observations:
        return ""
    cards = []
    for item in observations:
        artifacts = item.get("image_artifacts") or {}
        fpv_path = artifacts.get("fpv") or item.get("fpv_image")
        offset = item.get("camera_offset") or {}
        camera_contract = robot_view_camera_contract_summary(item.get("camera_control_contract"))
        cards.append(
            '<article class="raw-fpv-card">'
            "<div>"
            f"<h3>{html.escape(str(item.get('observation_id', 'observation')))}</h3>"
            f'<p class="pose">room={html.escape(str(item.get("room_id", "")))} '
            f"waypoint={html.escape(str(item.get('waypoint_id', '')))}</p>"
            f'<p class="pose">camera yaw={html.escape(str(offset.get("yaw_delta_deg", 0)))} '
            f"pitch={html.escape(str(offset.get('pitch_delta_deg', 0)))}</p>"
            f'<p class="note">{html.escape(str(item.get("artifact_status", "")))}</p>'
            f"{camera_contract}"
            "</div>"
            f"{_view_figure(fpv_path, 'FPV')}"
            "</article>"
        )
    return (
        '<section class="panel raw-fpv-section"><h2>Raw FPV Observations</h2>'
        '<p class="note">Camera-only perception evidence: these rows provide FPV image '
        "artifacts without structured movable-object detections, categories, support "
        "estimates, target labels, or generated mess truth.</p>"
        '<div class="raw-fpv-grid">' + "".join(cards) + "</div></section>"
    )


def _private_evaluation_section(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    private = run_result.get("private_evaluation") or {}
    targets = private.get("generated_mess_set") or []
    destinations = private.get("acceptable_destination_sets") or {}
    rows = []
    for object_id in targets:
        destination_text = ", ".join(str(item) for item in destinations.get(object_id, []))
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(object_id))}</td>"
            f"<td>{html.escape(destination_text)}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Generated mess object</th>'
        "<th>Acceptable destination set</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    summary = (
        f"Generated mess count {private.get('generated_mess_count', 0)}"
        f"{_requested_generated_text(private)}; "
        f"mess restoration rate {private.get('mess_restoration_rate', 0)}; "
        f"sweep coverage rate {private.get('sweep_coverage_rate', 0)}; "
        f"disturbance count {private.get('disturbance_count', 0)}."
    )
    return (
        '<section class="panel private-evaluation"><h2>Private Evaluation</h2>'
        f'<p class="note">{html.escape(summary)}</p>{table}</section>'
    )


def _advisory_review_section(run_result: dict[str, Any]) -> str:
    advisory = run_result.get("advisory_evaluation") or {}
    if not advisory:
        return ""
    rows = []
    for item in advisory.get("object_reviews") or []:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('actual_location_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('advisory_verdict', '')))}</td>"
            f"<td>{html.escape(str(item.get('rationale', '')))}</td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Final location</th><th>Advisory verdict</th><th>Rationale</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    counts = advisory.get("counts") or {}
    summary = (
        f"{advisory.get('overall_verdict', 'unknown')} from "
        f"{advisory.get('evaluator', 'unknown')}; "
        f"authoritative={str(advisory.get('authoritative')).lower()}; "
        f"reviewed {counts.get('total_reviewed', 0)} objects."
    )
    note = advisory.get("non_authoritative_note") or advisory.get("summary") or ""
    return (
        '<section class="panel advisory-review"><h2>Advisory Review</h2>'
        f'<p class="note">{html.escape(summary)}</p>'
        f'<p class="note">{html.escape(str(note))}</p>{table}</section>'
    )


def _requested_generated_text(private: dict[str, Any]) -> str:
    requested = private.get("requested_generated_mess_count")
    if requested is None:
        return ""
    return f" (requested {requested})"


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


def _moves_table(moves: list[dict[str, Any]]) -> str:
    if not moves:
        return "<p>No place operations recorded.</p>"
    rows = []
    for index, move in enumerate(moves, start=1):
        rows.append(
            "<tr>"
            f"<td>{index}</td>"
            f"<td>{html.escape(str(move.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(move.get('receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(move.get('primitive_provenance', '')))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Object</th><th>Placed at</th>'
        "<th>Primitive provenance</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _semantic_steps_table(semantic_substeps: list[dict[str, Any]]) -> str:
    if not semantic_substeps:
        return (
            '<section class="panel semantic-section semantic-section-empty">'
            "<h2>Semantic Substeps</h2>"
            + _empty_state_block(
                "No semantic cleanup actions recorded",
                "This AgiBot rehearsal exported map context, rehearsed the policy "
                "camera boundary, and rehearsed waypoint navigation. Physical "
                "manipulation and object cleanup were intentionally not executed.",
            )
            + "</section>"
        )
    cards = []
    for item in semantic_substeps:
        steps = item.get("steps", [])
        displayed = display_semantic_subphases(steps)
        status = _semantic_substep_status(steps)
        phase_rail = "".join(
            "<li>"
            f"<span>{html.escape(step['label'])}</span>"
            f"<small>{html.escape(step['detail'])}</small>"
            "</li>"
            for step in displayed
        )
        readback = _semantic_readback(steps)
        placement = _semantic_placement_readback(steps)
        cards.append(
            '<details class="semantic-card">'
            "<summary>"
            '<span class="semantic-card-head">'
            f"<strong>{html.escape(str(item.get('object_id', '')))}</strong>"
            f"<span>{html.escape(str(item.get('source_receptacle_id', '') or 'unknown source'))}"
            " -> "
            f"{html.escape(str(item.get('target_receptacle_id', '') or 'unknown target'))}</span>"
            "</span>"
            f'<span class="semantic-card-status">{html.escape(status)}'
            f" · {len(displayed)} phases</span>"
            "</summary>"
            f'<ol class="phase-rail">{phase_rail}</ol>'
            f'<p class="readback">Readback: {html.escape(readback or "pending")}</p>'
            f"{placement}"
            "</details>"
        )
    return (
        '<section class="panel semantic-section"><h2>Semantic Substeps</h2>'
        f'<p class="note">{html.escape(SEMANTIC_LOOP_DISPLAY_NOTE)}</p>'
        '<div class="semantic-cards">' + "".join(cards) + "</div></section>"
    )


def _semantic_substep_status(steps: list[dict[str, Any]]) -> str:
    if any(step.get("phase") in {OBJECT_DONE_PHASE, *PLACE_CLEANUP_PHASES} for step in steps):
        return "placed"
    if any(step.get("ok") is False for step in steps):
        return "blocked"
    return "pending"


def _semantic_readback(steps: list[dict[str, Any]]) -> str:
    candidates = [
        step for step in steps if step.get("phase") in {OBJECT_DONE_PHASE, *PLACE_CLEANUP_PHASES}
    ]
    if not candidates:
        return "pending"
    final_step = candidates[-1]
    readback = str(final_step.get("location_id") or "")
    relation = str(final_step.get("location_relation") or "")
    contained_in = final_step.get("contained_in")
    if contained_in:
        return f"{readback} ({relation}: {contained_in})"
    return readback or "pending"


def _semantic_placement_readback(steps: list[dict[str, Any]]) -> str:
    diagnostics = [
        step.get("placement_diagnostic")
        for step in steps
        if isinstance(step.get("placement_diagnostic"), dict)
    ]
    if not diagnostics:
        return ""
    diagnostic = diagnostics[-1]
    summary = (
        f"Placement: {diagnostic.get('support_status', diagnostic.get('status', 'unknown'))}; "
        f"relation={diagnostic.get('relation', '')}; "
        f"xy={diagnostic.get('xy_distance_m', '')}m; "
        f"z={diagnostic.get('z_delta_m', '')}m; "
        f"contact={diagnostic.get('contact_proof', '')}"
    )
    return f'<p class="readback">{html.escape(summary)}</p>'


def _score_table(score: dict[str, Any]) -> str:
    rows = []
    for row in score["object_results"]:
        exact_private_match = row.get("exact_private_match", row.get("restored", False))
        semantic_level = row.get("semantic_acceptability", "unknown")
        semantic_reason = row.get("semantic_reason", "")
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['object_id']))}</td>"
            f"<td>{html.escape(str(row['actual_location_id']))}</td>"
            f"<td>{'yes' if exact_private_match else 'no'}</td>"
            f"<td>{html.escape(str(semantic_level))}</td>"
            f"<td>{html.escape(str(semantic_reason))}</td>"
            "</tr>"
        )
    semantic_summary = _semantic_acceptability_summary(score)
    return (
        semantic_summary
        + '<div class="table-wrap"><table><thead><tr><th>Object</th><th>Final location</th>'
        "<th>Exact private match</th><th>Semantic acceptability</th><th>Reason</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _semantic_acceptability_summary(score: dict[str, Any]) -> str:
    semantic = score.get("semantic_acceptability")
    if not isinstance(semantic, dict):
        return ""
    counts = semantic.get("counts") or {}
    accepted = semantic.get("accepted_count", 0)
    total = semantic.get("total_targets", score.get("total_targets", 0))
    parts = [
        f"accepted {accepted}/{total}",
        f"preferred {counts.get('preferred', 0)}",
        f"acceptable {counts.get('acceptable', 0)}",
        f"questionable {counts.get('questionable', 0)}",
        f"wrong {counts.get('wrong', 0)}",
        f"unknown {counts.get('unknown', 0)}",
    ]
    return f'<p class="note">Semantic acceptability: {html.escape(", ".join(parts))}.</p>'


def _extract_moves(trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    moves: list[dict[str, Any]] = []
    for event in trace_events:
        if event.get("tool") not in {"place", "place_inside"} or event.get("event") != "response":
            continue
        response = event.get("response")
        if isinstance(response, dict) and response.get("ok"):
            moves.append(response)
    return moves


def _image_lightbox_markup() -> str:
    return (
        '<div class="image-lightbox" data-image-lightbox hidden aria-hidden="true">'
        '<button type="button" class="lightbox-close" data-lightbox-close '
        'aria-label="Close image review">Close</button>'
        '<div class="lightbox-dialog" role="dialog" aria-modal="true" '
        'aria-label="Image review">'
        '<img alt="">'
        '<p class="lightbox-caption" data-lightbox-caption></p>'
        "</div></div>"
    )


def _wrap_html(
    body: str,
    *,
    extra_css: str = "",
    rerun_command: str | None = None,
    title: str = "MolmoSpaces Cleanup Pilot",
) -> str:
    extra_css_block = f"{extra_css.rstrip()}\n" if extra_css else ""
    rerun_panel = render_rerun_panel(rerun_command)
    image_lightbox = _image_lightbox_markup()
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      color: #20242c;
      background: #eef2f6;
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px 20px 48px; }}
    h1 {{ font-size: 30px; margin: 0; letter-spacing: 0; }}
    h2 {{ font-size: 19px; margin: 0 0 12px; letter-spacing: 0; }}
    h2 span {{ color: #647083; font-size: 13px; font-weight: 650; }}
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 22px;
      box-shadow: 0 14px 34px rgba(25, 32, 44, 0.16);
    }}
    .summary-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; }}
    .summary-metadata {{
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 8px;
      margin-top: 12px;
      background: rgba(255, 255, 255, 0.05);
    }}
    .summary-metadata > summary {{
      min-height: 42px;
      padding: 10px 12px;
      cursor: pointer;
      color: #dbe5ef;
      font-weight: 750;
    }}
    .summary-metadata .badges {{ padding: 0 12px 12px; }}
    .eyebrow {{
      margin: 0 0 6px;
      color: #a7d8cf;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
      gap: 10px;
      margin: 18px 0;
    }}
    .metric {{
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.14);
      border-radius: 8px;
      padding: 12px;
    }}
    .metric span {{ display: block; color: #b7c1ce; font-size: 12px; margin-bottom: 4px; }}
    .metric strong {{
      display: block;
      color: #ffffff;
      font-size: 19px;
      line-height: 1.15;
      overflow-wrap: anywhere;
    }}
    .panel .metric {{
      background: #f8fafc;
      border-color: #d9dde6;
    }}
    .panel .metric span {{ color: #647083; }}
    .panel .metric strong {{ color: #20242c; }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
      box-shadow: 0 5px 16px rgba(25, 32, 44, 0.06);
    }}
    .report-tabs {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      gap: 8px;
      overflow-x: auto;
      margin-top: 18px;
      padding: 10px;
      background: rgba(238, 242, 246, 0.96);
      border: 1px solid #d8dee8;
      border-radius: 8px;
      backdrop-filter: blur(8px);
    }}
    .report-tab {{
      min-height: 40px;
      border: 1px solid #cfd6e2;
      border-radius: 6px;
      padding: 0 12px;
      background: #ffffff;
      color: #334155;
      font: inherit;
      font-size: 14px;
      font-weight: 700;
      white-space: nowrap;
      cursor: pointer;
    }}
    .report-tab[aria-selected="true"] {{
      background: #20242c;
      border-color: #20242c;
      color: #ffffff;
    }}
    .report-tab:focus-visible {{
      outline: 3px solid #7cc7bb;
      outline-offset: 2px;
    }}
    .report-tab-panel {{ scroll-margin-top: 80px; }}
    .note-panel {{ background: #fbfcfd; }}
    .empty-state {{
      border: 1px dashed #cbd5e1;
      border-radius: 8px;
      background: #f8fafc;
      padding: 18px;
    }}
    .empty-state h3 {{ margin: 0 0 6px; color: #20242c; }}
    .empty-state p {{ margin: 0; color: #647083; max-width: 720px; }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 7px 10px;
    }}
    .summary .badge {{
      background: rgba(255, 255, 255, 0.09);
      border-color: rgba(255, 255, 255, 0.18);
      color: #e9edf4;
    }}
    .summary .badge strong {{ color: #ffffff; }}
    .snapshots {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    .before-after-section .snapshots figcaption,
    .comparison-item figcaption,
    .nav2-preview figcaption {{
      display: grid;
      gap: 3px;
    }}
    figcaption strong {{ color: #20242c; }}
    figcaption span {{ color: #647083; font-size: 12px; }}
    .comparison-details,
    .timing-details,
    .artifact-details,
    .robot-timeline-details {{
      margin-top: 14px;
      border: 1px solid #d9dde6;
      border-radius: 8px;
      background: #fbfcfd;
    }}
    .comparison-details > summary,
    .timing-details > summary,
    .artifact-details > summary,
    .robot-timeline-details > summary {{
      min-height: 44px;
      padding: 12px 14px;
      cursor: pointer;
      font-weight: 750;
    }}
    .comparison-details > summary span {{
      color: #647083;
      font-size: 13px;
      font-weight: 650;
      margin-left: 8px;
    }}
    .comparison-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
      gap: 12px;
      padding: 0 12px 12px;
    }}
    .comparison-item {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #ffffff;
    }}
    .comparison-item summary {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) 24px;
      gap: 10px;
      align-items: start;
      min-height: 58px;
      list-style: none;
      cursor: pointer;
    }}
    .comparison-item summary::-webkit-details-marker {{ display: none; }}
    .comparison-item summary::after {{
      content: "-";
      width: 24px;
      height: 24px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: #e6eef5;
      color: #334155;
      font-weight: 800;
    }}
    .comparison-item:not([open]) summary::after {{ content: "+"; }}
    .comparison-item[open] summary {{ margin-bottom: 10px; }}
    .comparison-item-head {{
      display: grid;
      gap: 4px;
      min-width: 0;
    }}
    .comparison-item-head strong {{ font-size: 15px; overflow-wrap: anywhere; }}
    .comparison-item-head span {{
      color: #647083;
      font-size: 12px;
      overflow-wrap: anywhere;
      display: -webkit-box;
      -webkit-box-orient: vertical;
      -webkit-line-clamp: 2;
      overflow: hidden;
    }}
    .comparison-views {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
      gap: 8px;
    }}
    .comparison-missing {{
      display: grid;
      min-height: 120px;
      place-items: center;
      background: #f1f5f9;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    .image-link {{
      position: relative;
      display: block;
      border-radius: 4px;
      overflow: hidden;
      cursor: zoom-in;
    }}
    .image-link::after {{
      content: "+";
      position: absolute;
      top: 8px;
      right: 8px;
      width: 26px;
      height: 26px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: rgba(32, 36, 44, 0.82);
      color: #ffffff;
      font-size: 18px;
      font-weight: 800;
      opacity: 0;
      transform: scale(0.94);
      transition: opacity 0.16s ease, transform 0.16s ease;
    }}
    .image-link:hover::after,
    .image-link:focus-visible::after {{
      opacity: 1;
      transform: scale(1);
    }}
    .image-link:focus-visible {{
      outline: 3px solid #7cc7bb;
      outline-offset: 3px;
    }}
    .image-lightbox[hidden] {{ display: none; }}
    .image-lightbox {{
      position: fixed;
      inset: 0;
      z-index: 1000;
      display: grid;
      place-items: center;
      padding: 24px;
      background: rgba(12, 16, 24, 0.86);
    }}
    .lightbox-dialog {{
      display: grid;
      gap: 10px;
      max-width: min(96vw, 1440px);
      max-height: 92vh;
      color: #f8fafc;
    }}
    .lightbox-dialog img {{
      max-width: min(96vw, 1440px);
      max-height: 82vh;
      width: auto;
      height: auto;
      object-fit: contain;
      border-radius: 6px;
      background: #0f172a;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.42);
    }}
    .lightbox-caption {{
      margin: 0;
      color: #e2e8f0;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    .lightbox-close {{
      position: fixed;
      top: 18px;
      right: 18px;
      min-height: 38px;
      border: 1px solid rgba(255, 255, 255, 0.22);
      border-radius: 6px;
      padding: 0 12px;
      background: rgba(15, 23, 42, 0.88);
      color: #ffffff;
      font: inherit;
      font-weight: 750;
      cursor: pointer;
    }}
    .lightbox-close:focus-visible {{
      outline: 3px solid #7cc7bb;
      outline-offset: 2px;
    }}
    figcaption {{ margin-top: 8px; color: #565f70; font-size: 14px; }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
    .timing-lane-block {{
      margin: 14px 0;
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .timing-lane-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 10px;
    }}
    .timing-lane-head h3 {{ margin: 0; font-size: 15px; }}
    .timing-lane-head span {{ color: #475569; font-weight: 750; }}
    .timing-lane {{
      display: flex;
      gap: 3px;
      overflow-x: auto;
      padding-bottom: 2px;
    }}
    .timing-segment {{
      flex: 0 0 max(var(--basis), 104px);
      min-height: 74px;
      display: grid;
      align-content: center;
      gap: 3px;
      padding: 10px;
      color: #ffffff;
      background: var(--segment-color);
      border-radius: 6px;
    }}
    .timing-segment strong,
    .timing-segment span,
    .timing-segment small {{
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }}
    .timing-segment span {{ font-size: 16px; font-weight: 800; }}
    .timing-segment small {{ color: rgba(255, 255, 255, 0.82); }}
    .timing-details .table-wrap,
    .artifact-details .table-wrap {{ margin: 0 12px 12px; }}
    .object-cycle-timing {{
      margin-top: 16px;
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .object-cycle-timing > h3 {{ margin: 0 0 8px; font-size: 16px; }}
    .object-cycle-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
    .object-cycle {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #ffffff;
    }}
    .object-cycle h3 {{ margin: 0 0 8px; font-size: 15px; overflow-wrap: anywhere; }}
    .object-cycle .timing-lane-block {{ margin: 0; padding: 10px; }}
    .object-cycle p {{ margin: 8px 0 0; color: #565f70; font-size: 12px; overflow-wrap: anywhere; }}
    .robot-timeline-details .robot-step {{
      margin: 0 12px 12px;
    }}
    .robot-step {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      margin-bottom: 14px;
    }}
    .robot-step h3 {{ font-size: 16px; margin: 0 0 4px; }}
    .pose {{ margin: 0 0 10px; color: #565f70; font-size: 13px; }}
    .semantic-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 10px; }}
    .semantic-badges .badge {{ font-size: 13px; padding: 5px 8px; background: #eef6ff; }}
    .focus-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 0 0 10px; }}
    .focus-badges .badge {{ font-size: 13px; padding: 5px 8px; }}
    .action-evidence-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: -2px 0 10px; }}
    .action-evidence-badges .badge {{
      font-size: 12px; padding: 4px 7px; background: #fff7ed; border-color: #fed7aa;
    }}
    .action-evidence-note {{ margin-top: -4px; }}
    .evidence-badges {{ display: flex; flex-wrap: wrap; gap: 6px; margin: -4px 0 10px; }}
    .evidence-badges .badge {{ font-size: 12px; padding: 4px 7px; background: #f8fafc; }}
    .views {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(230px, 1fr));
      gap: 10px;
    }}
    .robot-primary-views {{
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }}
    .sim-only-views {{
      margin-top: 10px;
      border: 1px dashed #cbd5e1;
      border-radius: 8px;
      background: #f8fafc;
    }}
    .sim-only-views > summary {{
      min-height: 40px;
      padding: 10px 12px;
      cursor: pointer;
      color: #475569;
      font-weight: 750;
    }}
    .sim-only-views .views {{ padding: 0 12px 12px; }}
    .sim-only-grid-single {{
      grid-template-columns: minmax(0, min(100%, 560px));
      justify-content: start;
    }}
{extra_css_block}    .raw-fpv-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }}
    .raw-fpv-card {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .raw-fpv-card h3 {{ margin: 0 0 4px; font-size: 15px; }}
    .raw-fpv-card figure {{ margin-top: 10px; }}
    .semantic-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 12px;
    }}
    .semantic-card {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .semantic-card summary {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto 24px;
      gap: 10px;
      align-items: center;
      list-style: none;
      cursor: pointer;
    }}
    .semantic-card summary::-webkit-details-marker {{ display: none; }}
    .semantic-card summary::after {{
      content: "+";
      width: 24px;
      height: 24px;
      display: grid;
      place-items: center;
      border-radius: 999px;
      background: #e6eef5;
      color: #334155;
      font-weight: 800;
    }}
    .semantic-card[open] summary {{ margin-bottom: 10px; }}
    .semantic-card[open] summary::after {{ content: "-"; }}
    .semantic-card-head {{
      display: grid;
      gap: 4px;
      margin: 0;
      min-width: 0;
    }}
    .semantic-card-head strong {{
      overflow-wrap: anywhere;
      font-size: 14px;
    }}
    .semantic-card-head span {{
      color: #647083;
      font-size: 12px;
      overflow-wrap: anywhere;
    }}
    .semantic-card-status {{
      color: #475569;
      font-size: 12px;
      font-weight: 750;
      white-space: nowrap;
    }}
    .phase-rail {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(58px, 1fr));
      gap: 8px;
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .phase-rail li {{
      border: 1px solid #bfdcd7;
      background: #eef8f6;
      border-radius: 7px;
      padding: 8px 6px;
      text-align: center;
    }}
    .phase-rail span {{ display: block; font-weight: 750; color: #1f5f58; }}
    .phase-rail small {{ display: block; margin-top: 2px; color: #687789; }}
    .command-phase-rail {{ min-width: 280px; }}
    .readback {{ margin: 10px 0 0; color: #565f70; font-size: 13px; overflow-wrap: anywhere; }}
    .nav2-explainer {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 10px;
      margin: 12px 0;
    }}
    .nav2-explainer div {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .nav2-explainer strong {{ display: block; margin-bottom: 4px; }}
    .nav2-explainer span {{ color: #565f70; }}
    .nav2-preview-layout {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(220px, 300px);
      gap: 12px;
      align-items: start;
    }}
    .nav2-legend {{
      border: 1px solid #d9dde6;
      border-radius: 8px;
      padding: 12px;
      background: #fbfcfd;
    }}
    .nav2-legend h3 {{ margin: 0 0 10px; font-size: 15px; }}
    .nav2-legend ul {{ display: grid; gap: 10px; list-style: none; padding: 0; margin: 0; }}
    .nav2-legend li {{
      display: grid;
      grid-template-columns: 18px minmax(0, 1fr);
      gap: 8px;
      align-items: center;
    }}
    .nav2-legend small {{
      grid-column: 2;
      color: #647083;
    }}
    .legend-swatch {{
      width: 16px;
      height: 16px;
      border-radius: 4px;
      border: 1px solid #94a3b8;
      background: #e8eef6;
    }}
    .legend-swatch.fixture {{ background: #717c8d; border-color: #475569; }}
    .legend-swatch.waypoint {{ border-radius: 999px; background: #23865a; border-color: #23865a; }}
    .legend-swatch.robot {{ border-radius: 999px; background: #2e58b2; border-color: #1e4082; }}
    .nav2-legend p {{ margin: 12px 0 0; color: #565f70; }}
    .requirements {{ color: #565f70; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
    @media (max-width: 640px) {{
      main {{ padding: 18px 12px 36px; }}
      .summary-head,
      .timing-lane-head {{
        display: grid;
        align-items: start;
      }}
      .semantic-card summary {{
        grid-template-columns: minmax(0, 1fr) 24px;
      }}
      .semantic-card-status {{
        grid-column: 1 / -1;
      }}
      .nav2-preview-layout {{
        grid-template-columns: 1fr;
      }}
    }}
{rerun_panel_css()}
  </style>
</head>
<body><main>{rerun_panel}{body}</main>{image_lightbox}<script>
(() => {{
  const buttons = Array.from(document.querySelectorAll("[data-report-tab-button]"));
  const panels = Array.from(document.querySelectorAll("[data-report-tab]"));
  if (!buttons.length || !panels.length) return;
  document.documentElement.classList.add("tabs-ready");
  const validTabs = new Set(panels.map((panel) => panel.dataset.reportTab));
  function activate(tab, options = {{}}) {{
    if (!validTabs.has(tab)) tab = panels[0].dataset.reportTab;
    for (const button of buttons) {{
      const selected = button.dataset.reportTabButton === tab;
      button.setAttribute("aria-selected", String(selected));
    }}
    let selectedPanel = panels[0];
    for (const panel of panels) {{
      const selected = panel.dataset.reportTab === tab;
      panel.hidden = !selected;
      if (selected) selectedPanel = panel;
    }}
    if (options.scroll === true && selectedPanel) {{
      requestAnimationFrame(() => {{
        selectedPanel.scrollIntoView({{ block: "start", inline: "nearest" }});
      }});
    }}
  }}
  for (const button of buttons) {{
    button.addEventListener("click", () => {{
      const tab = button.dataset.reportTabButton;
      activate(tab, {{ scroll: true }});
      history.replaceState(null, "", `#${{tab}}`);
    }});
  }}
  const hash = location.hash.replace("#", "");
  activate(validTabs.has(hash) ? hash : panels[0].dataset.reportTab);
}})();
(() => {{
  const lightbox = document.querySelector("[data-image-lightbox]");
  if (!lightbox) return;
  const lightboxImage = lightbox.querySelector("img");
  const caption = lightbox.querySelector("[data-lightbox-caption]");
  const closeButton = lightbox.querySelector("[data-lightbox-close]");
  let returnFocus = null;

  function openLightbox(link) {{
    returnFocus = link;
    lightboxImage.src = link.href;
    lightboxImage.alt = link.querySelector("img")?.alt || "";
    caption.textContent = link.dataset.lightboxCaption || lightboxImage.alt || "";
    lightbox.hidden = false;
    lightbox.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    closeButton?.focus();
  }}

  function closeLightbox() {{
    lightbox.hidden = true;
    lightbox.setAttribute("aria-hidden", "true");
    lightboxImage.removeAttribute("src");
    document.body.style.overflow = "";
    if (returnFocus && document.contains(returnFocus)) returnFocus.focus();
    returnFocus = null;
  }}

  document.addEventListener("click", (event) => {{
    const link = event.target.closest?.("[data-lightbox-image]");
    if (link) {{
      event.preventDefault();
      openLightbox(link);
      return;
    }}
    if (!lightbox.hidden && event.target === lightbox) closeLightbox();
    if (!lightbox.hidden && event.target.closest?.("[data-lightbox-close]")) closeLightbox();
  }});

  document.addEventListener("keydown", (event) => {{
    if (event.key === "Escape" && !lightbox.hidden) closeLightbox();
  }});
}})();
</script></body>
</html>
"""


def _planner_report_css() -> str:
    return """    .diagnostic-view {
      background: #ffffff;
    }
    .diagnostic-visual {
      border-radius: 8px;
      overflow: hidden;
      background: #f8fafc;
    }
    .diagnostic-visual svg {
      width: 100%;
      height: auto;
      display: block;
    }
    .diagnostic-stats {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
      gap: 8px;
      margin-top: 10px;
    }
    .diagnostic-stat {
      border: 1px solid #e2e8f0;
      border-radius: 6px;
      padding: 8px;
      background: #f8fafc;
    }
    .diagnostic-stat small {
      display: block;
      color: #64748b;
      margin-bottom: 3px;
    }
    .diagnostic-stat strong {
      color: #0f172a;
    }
    .post-placement-rejection-views h3 {
      margin: 14px 0 8px;
      font-size: 15px;
    }
    .rejection-view .diagnostic-visual {
      background: #fff7ed;
    }
    .grasp-blocker-matrix {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin-bottom: 12px;
    }
    .grasp-blocker-card {
      border: 1px solid #fecaca;
      border-radius: 8px;
      padding: 12px;
      background: #fff7f7;
    }
    .grasp-blocker-route {
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      gap: 8px;
      align-items: center;
      margin-bottom: 8px;
    }
    .grasp-blocker-route strong {
      overflow-wrap: anywhere;
    }
    .grasp-blocker-route span {
      color: #64748b;
      font-size: 12px;
    }
    .grasp-blocker-card p {
      margin: 8px 0 0;
      color: #475569;
    }
    .decision-cards {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 10px;
      margin: 0 0 12px;
    }
    .decision-card {
      border: 1px solid #bfdbfe;
      border-radius: 8px;
      padding: 12px;
      background: #eff6ff;
    }
    .decision-card h3 { margin: 0 0 6px; font-size: 14px; color: #1e3a8a; }
    .decision-card strong {
      display: block;
      color: #0f172a;
      overflow-wrap: anywhere;
      margin-bottom: 8px;
    }
    .decision-card p { margin: 0; color: #475569; }
"""


def _receptacle_positions() -> dict[str, tuple[int, int]]:
    return {
        "sofa_01": (160, 130),
        "floor_01": (450, 250),
        "armchair_01": (725, 130),
        "desk_01": (160, 350),
        "coffee_table_01": (450, 130),
        "sink_01": (725, 350),
        "bookshelf_01": (160, 465),
        "laundry_hamper_01": (450, 465),
        "fridge_01": (725, 465),
        "toy_bin_01": (450, 350),
    }


def write_trace_jsonl(trace_path: Path, events: list[dict[str, Any]]) -> None:
    trace_path.write_text(
        "".join(json.dumps(event, sort_keys=True) + "\n" for event in events),
        encoding="utf-8",
    )

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
from roboclaws.molmo_cleanup.planner_proof_quality import (
    format_quality_tier_counts,
    planner_proof_quality_evidence,
    planner_proof_quality_summary,
)
from roboclaws.molmo_cleanup.planner_task_feasibility import grasp_feasibility_signature_counts
from roboclaws.molmo_cleanup.semantic_timeline import (
    CLOSE_RECEPTACLE_PHASE,
    OBJECT_DONE_PHASE,
    PLACE_CLEANUP_PHASES,
    SEMANTIC_LOOP_DISPLAY_NOTE,
    annotate_focus_visual_grounding,
    display_semantic_subphase,
    display_semantic_subphases,
    semantic_subphase_text,
)
from roboclaws.molmo_cleanup.types import CleanupScenario

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
    return _present_sections(
        [
            _cleanup_report_tabs(),
            _cleanup_summary_section(scenario=scenario, run_result=run_result, score=score),
            _report_tab_panel(
                "overview",
                [
                    _confidence_layer_note(run_result),
                    _realworld_contract_note(run_result),
                    _cleanup_profile_note(run_result),
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
                    _robot_timeline(
                        run_dir,
                        _visual_core_robot_view_steps(run_result, robot_view_steps),
                    )
                ],
            ),
            _report_tab_panel(
                "timing",
                [_runtime_timing_section(run_dir, run_result, trace_events, robot_view_steps)],
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
                    _isaac_runtime_section(run_dir, run_result),
                    _nav2_map_bundle_section(run_dir, run_result),
                    _real_robot_readiness_section(run_result),
                    _cleanup_policy_trace_section(run_result),
                ],
            ),
            _report_tab_panel(
                "proof",
                [
                    _score_section(score),
                    _manipulation_provenance_section(run_result),
                    _attached_planner_proof_section(run_result),
                    _cleanup_primitive_gate_section(run_result),
                    _planner_cleanup_bridge_section(run_result),
                    _planner_proof_requests_section(run_result),
                ],
            ),
            _report_tab_panel(
                "agent",
                [
                    _agent_view_section(run_result),
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
    {_manipulation_provenance_section(run_result)}
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
    {_proof_execution_horizon_section(manifest.get("proof_execution_horizon") or {})}
    {_proof_request_selection_section(manifest.get("proof_request_selection") or {})}
    {
        _grasp_feasibility_mitigation_decision_section(
            manifest.get("grasp_feasibility_mitigation_decision") or {}
        )
    }
    {
        _grasp_cache_availability_preflight_section(
            manifest.get("grasp_cache_availability_preflight") or {}
        )
    }
    {
        _grasp_cache_generation_preflight_section(
            manifest.get("grasp_cache_generation_preflight") or {}
        )
    }
    {_proof_bundle_local_runtime_preflight_section(manifest.get("local_runtime_preflight") or {})}
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
    {_proof_bundle_warmup_section(manifest.get("warmup") or {})}
    {_proof_bundle_commands_section(commands)}
    {
        _proof_bundle_results_section(
            manifest.get("proof_result_summary") or {}, output_dir=output_dir
        )
    }
    {_cleanup_rerun_command_section(cleanup_command)}
    {_cleanup_rerun_artifact_section(cleanup_rerun)}
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
    body = "\n".join(
        _present_sections(
            [
                _grasp_cache_generation_summary_section(result),
                _grasp_cache_generation_assets_section(result.get("assets") or []),
                _grasp_cache_generation_command_section(result),
                _grasp_cache_generation_blockers_section(result.get("blockers") or []),
            ]
        )
    )
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
    body = "\n".join(
        _present_sections(
            [
                _grasp_pose_policy_cache_summary_section(result),
                _grasp_pose_policy_cache_policy_section(result.get("pose_policy") or {}),
                _grasp_pose_policy_cache_artifacts_section(result),
                _grasp_cache_generation_assets_section(result.get("assets") or []),
                _grasp_cache_generation_command_section(result),
                _grasp_cache_generation_blockers_section(result.get("blockers") or []),
            ]
        )
    )
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
    body = "\n".join(
        _present_sections(
            [
                _grasp_filter_diagnostics_summary_section(result),
                _grasp_filter_diagnostics_artifacts_section(result),
                _grasp_filter_diagnostics_variants_section(result.get("variants") or []),
                _grasp_filter_diagnostics_blockers_section(result.get("blockers") or []),
            ]
        )
    )
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
    body = "\n".join(
        _present_sections(
            [
                _grasp_initial_contact_summary_section(result),
                _grasp_initial_contact_artifacts_section(result),
                _grasp_initial_contact_variants_section(result.get("variants") or []),
                _grasp_initial_contact_samples_section(result.get("best_variant") or {}),
                _grasp_initial_contact_blockers_section(result.get("blockers") or []),
            ]
        )
    )
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
          {_cleanup_profile_badges(run_result)}
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


def _runtime_timing_section(
    run_dir: Path,
    run_result: dict[str, Any],
    trace_events: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
) -> str:
    timing = run_result.get("runtime_timing")
    if not isinstance(timing, dict):
        timing = runtime_timing_from_trace(trace_events, robot_view_steps)
    if not timing:
        return ""
    total_elapsed = timing.get("total_elapsed_s")
    if not isinstance(total_elapsed, (int, float)) or total_elapsed <= 0:
        return ""

    live_timing = _load_live_timing(run_dir)
    runner_timing = live_timing.get("runner_timing") if isinstance(live_timing, dict) else {}
    runner_timeline = (
        _runner_timing_timeline(runner_timing)
        if isinstance(runner_timing, dict) and runner_timing
        else ""
    )
    mcp_timeline = _mcp_timing_timeline(timing)
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('MCP elapsed', _seconds_text(total_elapsed))}"
        f"{_metric('Tool/backend handling', _seconds_text(timing.get('tool_handler_s', 0)))}"
        f"{_metric('Robot-view capture', _seconds_text(timing.get('robot_view_capture_s', 0)))}"
        f"{_metric('Between-tool gap', _seconds_text(timing.get('between_tool_gap_s', 0)))}"
        f"{_metric('Other MCP overhead', _seconds_text(timing.get('other_mcp_overhead_s', 0)))}"
        f"{_metric('Tool calls', timing.get('tool_call_count', 0))}"
        "</div>"
    )
    tool_rows = []
    for item in timing.get("tool_breakdown") or []:
        tool_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('tool', '')))}</td>"
            f"<td>{html.escape(str(item.get('calls', 0)))}</td>"
            f"<td>{html.escape(_seconds_text(item.get('handler_s', 0)))}</td>"
            f"<td>{html.escape(_seconds_text(item.get('avg_handler_s', 0)))}</td>"
            "</tr>"
        )
    gap_rows = []
    for item in timing.get("longest_between_tool_gaps") or []:
        gap_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('after_tool', '')))}</td>"
            f"<td>{html.escape(str(item.get('before_tool', '')))}</td>"
            f"<td>{html.escape(_seconds_text(item.get('gap_s', 0)))}</td>"
            "</tr>"
        )
    tool_table = (
        '<div class="table-wrap"><table><thead><tr><th>Tool</th><th>Calls</th>'
        "<th>Handler time</th><th>Avg handler</th></tr></thead><tbody>"
        + "".join(tool_rows)
        + "</tbody></table></div>"
    )
    gap_table = (
        '<div class="table-wrap"><table><thead><tr><th>After response</th>'
        "<th>Before request</th><th>Gap</th></tr></thead><tbody>"
        + "".join(gap_rows)
        + "</tbody></table></div>"
        if gap_rows
        else ""
    )
    object_cycles = _object_cycle_timing_section(timing, trace_events)
    return (
        '<section class="panel runtime-timing">'
        "<h2>Runtime Timing</h2>"
        '<p class="note">Wall-clock timing is split into scan-friendly lanes. '
        "Runner timing shows the live shell orchestration. MCP timing is the cleanup "
        "server trace inside the agent run; between-tool gaps include model reasoning, "
        "CLI orchestration, transport, and post-response overhead.</p>"
        f"{runner_timeline}{mcp_timeline}{metrics}{object_cycles}"
        '<details class="timing-details"><summary>Tool and gap tables</summary>'
        f"{tool_table}{gap_table}</details></section>"
    )


def _object_cycle_timing_section(
    timing: dict[str, Any],
    trace_events: list[dict[str, Any]],
) -> str:
    cycles = _object_timing_cycles(trace_events)
    if not cycles:
        return ""
    cycle_total = sum(float(item["total_s"]) for item in cycles)
    total_elapsed = _float_or_none(timing.get("total_elapsed_s")) or 0.0
    search_overhead = max(0.0, total_elapsed - cycle_total)
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Cleaned-object cycles', len(cycles))}"
        f"{_metric('Cycle time', _seconds_text(cycle_total))}"
        f"{_metric('Sweep/search overhead', _seconds_text(search_overhead))}"
        f"{_metric('Measured only', 'no projections')}"
        "</div>"
    )
    cards = []
    for index, cycle in enumerate(cycles, start=1):
        timing_lane = _timing_lane(
            "",
            cycle["total_s"],
            _object_cycle_segments(cycle),
            render_empty=True,
        )
        cards.append(
            '<article class="object-cycle">'
            f"<h3>{index}. {html.escape(str(cycle['object_id']))}</h3>"
            f"{timing_lane}"
            f"<p>{html.escape(_object_cycle_phase_text(cycle))}</p>"
            "</article>"
        )
    return (
        '<div class="object-cycle-timing">'
        "<h3>Per-object cleanup cycles</h3>"
        '<p class="note">Each cycle starts at the first successful object-directed '
        "action and ends at the post-place observe when present. The orange bucket "
        "is measured response-to-next-request time: agent thinking, CLI orchestration, "
        "transport, and other agent-side delay. It is not projected or estimated "
        "hardware time.</p>"
        f"{metrics}"
        '<div class="object-cycle-grid">' + "".join(cards) + "</div></div>"
    )


def _object_cycle_segments(cycle: dict[str, Any]) -> list[tuple[str, Any, str, str]]:
    return [
        (
            "Agent thinking / orchestration",
            cycle.get("agent_gap_s"),
            "response-to-next-request gap",
            "#b7683f",
        ),
        ("Robot views", cycle.get("robot_view_capture_s"), "measured report capture", "#4f6691"),
        ("Tool handlers", cycle.get("tool_handler_s"), "cleanup server work", "#2f766f"),
        ("Other measured", cycle.get("other_s"), "remaining wall time", "#7a8491"),
    ]


def _object_cycle_phase_text(cycle: dict[str, Any]) -> str:
    tools = " -> ".join(str(item) for item in cycle.get("tools") or [])
    return (
        f"{_seconds_text(cycle.get('total_s'))}; "
        f"window {_seconds_text(cycle.get('start_s'))} to {_seconds_text(cycle.get('end_s'))}; "
        f"{tools}"
    )


def _load_live_timing(run_dir: Path) -> dict[str, Any]:
    try:
        payload = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _runner_timing_timeline(runner_timing: dict[str, Any]) -> str:
    total = runner_timing.get("total_elapsed_s")
    segments = [
        ("Setup", runner_timing.get("pre_codex_setup_s"), "launcher and server prep", "#536d7a"),
        ("Codex run", runner_timing.get("codex_exec_elapsed_s"), "agent execution", "#2f766f"),
        (
            "Server wait",
            runner_timing.get("post_codex_server_wait_s"),
            "cleanup server finalization",
            "#8a6f39",
        ),
        ("Checker", runner_timing.get("checker_elapsed_s"), "artifact checker", "#4f6691"),
        ("Final", runner_timing.get("final_overhead_s"), "report wrap-up", "#6f7785"),
    ]
    return _timing_lane("Run wall clock", total, segments)


def _mcp_timing_timeline(timing: dict[str, Any]) -> str:
    segments = [
        (
            "Between tools",
            timing.get("between_tool_gap_s"),
            "agent reasoning and orchestration",
            "#b7683f",
        ),
        ("Robot views", timing.get("robot_view_capture_s"), "FPV/chase/map artifacts", "#4f6691"),
        ("Tool handlers", timing.get("tool_handler_s"), "cleanup server work", "#2f766f"),
        ("Other", timing.get("other_mcp_overhead_s"), "startup/finalization remainder", "#7a8491"),
    ]
    return _timing_lane("MCP trace attribution", timing.get("total_elapsed_s"), segments)


def _timing_lane(
    title: str,
    total: Any,
    segments: list[tuple[str, Any, str, str]],
    *,
    render_empty: bool = False,
) -> str:
    total_s = _float_or_none(total)
    if total_s is None:
        if not render_empty:
            return ""
        total_s = 0.0
    if total_s < 0:
        total_s = 0.0
    if total_s <= 0 and not render_empty:
        return ""
    segment_html = []
    visibly_zero_total = render_empty and total_s < 0.05
    if total_s > 0 and not visibly_zero_total:
        for label, value, detail, color in segments:
            seconds = _float_or_none(value)
            if seconds is None or seconds <= 0:
                continue
            pct = max(0.2, min(100.0, seconds / total_s * 100.0))
            segment_html.append(
                '<div class="timing-segment" '
                f'style="--basis: {pct:.3f}%; --segment-color: {html.escape(color)};" '
                f'title="{html.escape(label)}: {html.escape(_seconds_text(seconds))}">'
                f"<strong>{html.escape(label)}</strong>"
                f"<span>{html.escape(_seconds_text(seconds))}</span>"
                f"<small>{html.escape(detail)}</small>"
                "</div>"
            )
    if not segment_html:
        if not render_empty:
            return ""
        segment_html.append(
            '<div class="timing-segment" '
            'style="--basis: 100.000%; --segment-color: #8d96a3;" '
            'title="No measurable split: timestamps were identical">'
            "<strong>No measurable split</strong>"
            f"<span>{html.escape(_seconds_text(total_s))}</span>"
            "<small>timestamps were identical</small>"
            "</div>"
        )
    heading = f"<h3>{html.escape(title)}</h3>" if title else "<h3>Measured distribution</h3>"
    return (
        '<div class="timing-lane-block">'
        '<div class="timing-lane-head">'
        f"{heading}"
        f"<span>{html.escape(_seconds_text(total_s))}</span>"
        "</div>"
        '<div class="timing-lane">' + "".join(segment_html) + "</div></div>"
    )


def runtime_timing_from_trace(
    trace_events: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a wall-clock attribution summary from cleanup MCP trace events."""

    robot_view_steps = robot_view_steps or []
    timed_events = [
        event for event in trace_events if isinstance(event.get("wallclock_elapsed"), (int, float))
    ]
    if not timed_events:
        return {}
    timed_events.sort(key=lambda event: float(event["wallclock_elapsed"]))
    total_elapsed = max(float(event["wallclock_elapsed"]) for event in timed_events)
    tool_events = [
        event
        for event in timed_events
        if event.get("tool") != "<runtime>" and event.get("event") in {"request", "response"}
    ]
    pending_requests: dict[str, list[dict[str, Any]]] = {}
    tool_breakdown: dict[str, dict[str, float | int | str]] = {}
    handler_total = 0.0
    for event in tool_events:
        tool = str(event.get("tool", ""))
        if event.get("event") == "request":
            pending_requests.setdefault(tool, []).append(event)
            continue
        if event.get("event") != "response":
            continue
        request = None
        requests = pending_requests.get(tool) or []
        if requests:
            request = requests.pop(0)
        duration = 0.0
        if request is not None:
            duration = max(
                0.0,
                float(event["wallclock_elapsed"]) - float(request["wallclock_elapsed"]),
            )
        item = tool_breakdown.setdefault(tool, {"tool": tool, "calls": 0, "handler_s": 0.0})
        item["calls"] = int(item["calls"]) + 1
        item["handler_s"] = float(item["handler_s"]) + duration
        handler_total += duration

    raw_gap_total = 0.0
    gaps = []
    previous_response: dict[str, Any] | None = None
    for event in tool_events:
        if event.get("event") == "response":
            previous_response = event
            continue
        if event.get("event") == "request" and previous_response is not None:
            gap = max(
                0.0,
                float(event["wallclock_elapsed"]) - float(previous_response["wallclock_elapsed"]),
            )
            if gap > 0:
                raw_gap_total += gap
                gaps.append(
                    {
                        "after_tool": str(previous_response.get("tool", "")),
                        "before_tool": str(event.get("tool", "")),
                        "start_s": float(previous_response["wallclock_elapsed"]),
                        "end_s": float(event["wallclock_elapsed"]),
                        "gap_s": round(gap, 3),
                    }
                )
            previous_response = None

    robot_view_capture = _robot_view_capture_seconds(timed_events, robot_view_steps)
    robot_view_overlap = _robot_view_capture_overlap_seconds(timed_events, gaps)
    for gap in gaps:
        overlap = _robot_view_capture_overlap_seconds(timed_events, [gap])
        raw_gap = float(gap["gap_s"])
        gap["raw_gap_s"] = round(raw_gap, 3)
        gap["robot_view_capture_s"] = round(overlap, 3)
        gap["gap_s"] = round(max(0.0, raw_gap - overlap), 3)
        gap.pop("start_s", None)
        gap.pop("end_s", None)
    gap_total = max(0.0, raw_gap_total - robot_view_overlap)
    other_mcp_overhead = max(0.0, total_elapsed - handler_total - robot_view_capture - gap_total)
    breakdown = []
    for item in tool_breakdown.values():
        calls = int(item["calls"])
        handler_s = float(item["handler_s"])
        breakdown.append(
            {
                "tool": str(item["tool"]),
                "calls": calls,
                "handler_s": round(handler_s, 3),
                "avg_handler_s": round(handler_s / calls, 3) if calls else 0.0,
            }
        )
    breakdown.sort(key=lambda item: (-float(item["handler_s"]), str(item["tool"])))
    gaps.sort(key=lambda item: -float(item["gap_s"]))
    return {
        "total_elapsed_s": round(total_elapsed, 3),
        "tool_handler_s": round(handler_total, 3),
        "robot_view_capture_s": round(robot_view_capture, 3),
        "between_tool_gap_s": round(gap_total, 3),
        "raw_between_tool_gap_s": round(raw_gap_total, 3),
        "other_mcp_overhead_s": round(other_mcp_overhead, 3),
        "tool_call_count": sum(int(item["calls"]) for item in breakdown),
        "tool_breakdown": breakdown,
        "longest_between_tool_gaps": gaps[:8],
    }


def _robot_view_capture_seconds(
    trace_events: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
) -> float:
    trace_total = sum(
        float(event.get("elapsed_s") or 0.0)
        for event in trace_events
        if event.get("tool") == "<runtime>" and event.get("event") == "robot_view_capture"
    )
    if trace_total > 0:
        return trace_total
    return sum(float(step.get("capture_elapsed_s") or 0.0) for step in robot_view_steps)


def _robot_view_capture_overlap_seconds(
    trace_events: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
) -> float:
    intervals = []
    for event in trace_events:
        if event.get("tool") != "<runtime>" or event.get("event") != "robot_view_capture":
            continue
        elapsed = float(event.get("elapsed_s") or 0.0)
        end = float(event.get("wallclock_elapsed") or 0.0)
        if elapsed > 0 and end > 0:
            intervals.append((max(0.0, end - elapsed), end))
    if not intervals or not gaps:
        return 0.0
    overlap_total = 0.0
    for gap in gaps:
        gap_start = float(gap.get("start_s") or 0.0)
        gap_end = float(gap.get("end_s") or 0.0)
        if gap_end <= gap_start:
            continue
        for capture_start, capture_end in intervals:
            overlap_total += max(0.0, min(gap_end, capture_end) - max(gap_start, capture_start))
    return overlap_total


def _seconds_text(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{float(value):.1f}s"
    try:
        return f"{float(value):.1f}s"
    except (TypeError, ValueError):
        return "n/a"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _object_timing_cycles(trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = _paired_tool_calls(trace_events)
    cycles = []
    index = 0
    while index < len(calls):
        call = calls[index]
        if not _is_object_cycle_start(call):
            index += 1
            continue
        object_id = str(call.get("object_id") or "")
        end_index = None
        place_index = None
        for cursor in range(index, len(calls)):
            candidate = calls[cursor]
            candidate_object = str(candidate.get("object_id") or "")
            if (
                cursor > index
                and _is_object_cycle_start(candidate)
                and candidate_object
                and candidate_object != object_id
            ):
                break
            if (
                candidate.get("tool") in PLACE_CLEANUP_PHASES
                and candidate.get("ok") is True
                and candidate_object == object_id
            ):
                place_index = cursor
                end_index = cursor
                if cursor + 1 < len(calls) and calls[cursor + 1].get("tool") == "observe":
                    end_index = cursor + 1
                break
        if place_index is None or end_index is None:
            index += 1
            continue
        cycle_calls = calls[index : end_index + 1]
        cycles.append(_summarize_object_timing_cycle(object_id, cycle_calls, trace_events))
        index = end_index + 1
    return cycles


def _is_object_cycle_start(call: dict[str, Any]) -> bool:
    return (
        call.get("tool") in {"navigate_to_visual_candidate", "navigate_to_object"}
        and call.get("ok") is True
        and bool(call.get("object_id"))
    )


def _paired_tool_calls(trace_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    timed = [
        event
        for event in trace_events
        if isinstance(event.get("wallclock_elapsed"), (int, float))
        and event.get("event") in {"request", "response"}
        and event.get("tool") != "<runtime>"
    ]
    timed.sort(key=lambda event: float(event["wallclock_elapsed"]))
    pending: dict[str, list[dict[str, Any]]] = {}
    pairs = []
    for event in timed:
        tool = str(event.get("tool") or "")
        if event.get("event") == "request":
            pending.setdefault(tool, []).append(event)
            continue
        requests = pending.get(tool) or []
        request = requests.pop(0) if requests else None
        start_s = float((request or event)["wallclock_elapsed"])
        end_s = float(event["wallclock_elapsed"])
        request_payload = (request or {}).get("request") or {}
        response_payload = event.get("response") or {}
        pairs.append(
            {
                "tool": tool,
                "start_s": start_s,
                "end_s": end_s,
                "handler_s": max(0.0, end_s - start_s),
                "object_id": _call_object_id(tool, request_payload, response_payload),
                "ok": response_payload.get("ok"),
            }
        )
    pairs.sort(key=lambda item: float(item["start_s"]))
    return pairs


def _call_object_id(tool: str, request: dict[str, Any], response: dict[str, Any]) -> str:
    if isinstance(response.get("object_id"), str):
        return str(response["object_id"])
    if isinstance(request.get("object_id"), str):
        return str(request["object_id"])
    if tool in {"place", "place_inside"} and isinstance(response.get("placed_object_id"), str):
        return str(response["placed_object_id"])
    return ""


def _summarize_object_timing_cycle(
    object_id: str,
    calls: list[dict[str, Any]],
    trace_events: list[dict[str, Any]],
) -> dict[str, Any]:
    start_s = float(calls[0]["start_s"])
    end_s = float(calls[-1]["end_s"])
    total_s = max(0.0, end_s - start_s)
    handler_s = sum(float(call.get("handler_s") or 0.0) for call in calls)
    gap_intervals = []
    raw_gap_s = 0.0
    for previous, current in zip(calls, calls[1:]):
        gap_start = float(previous["end_s"])
        gap_end = float(current["start_s"])
        if gap_end <= gap_start:
            continue
        gap = gap_end - gap_start
        raw_gap_s += gap
        gap_intervals.append({"start_s": gap_start, "end_s": gap_end, "gap_s": gap})
    robot_gap_overlap = _robot_view_capture_overlap_seconds(trace_events, gap_intervals)
    robot_capture_s = _robot_view_capture_overlap_seconds(
        trace_events,
        [{"start_s": start_s, "end_s": end_s}],
    )
    agent_gap_s = max(0.0, raw_gap_s - robot_gap_overlap)
    other_s = max(0.0, total_s - handler_s - agent_gap_s - robot_capture_s)
    return {
        "object_id": object_id,
        "start_s": round(start_s, 3),
        "end_s": round(end_s, 3),
        "total_s": round(total_s, 3),
        "tool_handler_s": round(handler_s, 3),
        "agent_gap_s": round(agent_gap_s, 3),
        "robot_view_capture_s": round(robot_capture_s, 3),
        "other_s": round(other_s, 3),
        "tools": [str(call.get("tool") or "") for call in calls],
    }


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
        "Same-pose robot FPV", summary.get("same_pose_api", False)
    )


def _cleanup_profile_badges(run_result: dict[str, Any]) -> str:
    metadata = run_result.get("cleanup_profile_metadata") or {}
    if not metadata:
        return ""
    return "".join(
        (
            _badge("Input lane", metadata.get("profile", run_result.get("cleanup_profile", ""))),
            _badge("Agent input", metadata.get("agent_input", "")),
            _badge("Input provenance", metadata.get("input_provenance", "")),
            _badge("Report", metadata.get("report", "")),
        )
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


def _cleanup_profile_note(run_result: dict[str, Any]) -> str:
    metadata = run_result.get("cleanup_profile_metadata") or {}
    if not metadata:
        return ""
    profile = metadata.get("profile", run_result.get("cleanup_profile", "unknown"))
    verifiers = ", ".join(str(item) for item in metadata.get("verifiers") or [])
    note = (
        f"Cleanup input/evidence lane {profile}: {metadata.get('summary', '')} "
        "This lane selects what the agent receives and what evidence/report gates "
        "the run produces; map shape and map priors are controlled separately by "
        "map_mode and runtime_map_prior. "
        f"Agent input: {metadata.get('agent_input', 'unknown')}; "
        f"input provenance: {metadata.get('input_provenance', 'unknown')}; "
        f"report: {metadata.get('report', 'unknown')}; verifier gates: {verifiers}. "
        f"{metadata.get('model_input_note', '')}"
    )
    return f'<section class="panel note-panel"><p class="note">{html.escape(note)}</p></section>'


def _isaac_runtime_section(run_dir: Path, run_result: dict[str, Any]) -> str:
    isaac = run_result.get("isaac_runtime") or {}
    if not isaac:
        return ""
    runtime = isaac.get("runtime") or {}
    segmentation = isaac.get("segmentation") or {}
    rendering = runtime.get("rendering") or {}
    scene_load = isaac.get("scene_load") or {}
    scene_index = isaac.get("scene_index_diagnostics") or {}
    scene_bindings = isaac.get("scene_binding_diagnostics") or {}
    scene_index_artifact = str(
        isaac.get("scene_index_artifact")
        or (run_result.get("artifacts") or {}).get("isaac_scene_index")
        or ""
    )
    scene_index_artifact_payload = _load_isaac_scene_index_artifact(
        run_dir,
        scene_index_artifact,
    )
    mapping_gaps = isaac.get("mapping_gaps") or []
    snapshots = [item for item in isaac.get("snapshot_artifacts", []) if isinstance(item, dict)]
    real_snapshots = sum(1 for item in snapshots if item.get("placeholder_visuals") is False)
    semantic_pose_state = isaac.get("semantic_pose_state")
    if not isinstance(semantic_pose_state, dict):
        semantic_pose_state = {}
    semantic_pose_view_capture = (
        semantic_pose_state.get("semantic_pose_view_capture")
        if isinstance(semantic_pose_state.get("semantic_pose_view_capture"), dict)
        else isaac.get("semantic_pose_view_capture")
    )
    if not isinstance(semantic_pose_view_capture, dict):
        semantic_pose_view_capture = {}
    semantic_pose_events = [
        item for item in semantic_pose_state.get("transform_events", []) if isinstance(item, dict)
    ]
    selected_binding_summary = (
        f"{scene_bindings.get('selected_object_bound_count', 0)}/"
        f"{scene_bindings.get('selected_object_count', 0)} objects, "
        f"{scene_bindings.get('selected_target_receptacle_bound_count', 0)}/"
        f"{scene_bindings.get('selected_target_receptacle_count', 0)} receptacles"
    )
    pose_view_capture_method = semantic_pose_view_capture.get("capture_method") or "none"
    pose_render_steps = semantic_pose_view_capture.get("render_steps", 0)
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Runtime mode', runtime.get('runtime_mode', 'unknown'))}"
        f"{_metric('Renderer', runtime.get('renderer_mode', 'unknown'))}"
        f"{_metric('Rendering proof', rendering.get('status', 'unknown'))}"
        f"{_metric('Scene load', scene_load.get('status', 'unknown'))}"
        f"{_metric('Isaac Sim', runtime.get('isaac_sim_version') or 'unavailable')}"
        f"{_metric('Isaac Lab', runtime.get('isaac_lab_version') or 'unavailable')}"
        f"{_metric('CUDA', _yes_no(runtime.get('cuda_available')))}"
        f"{_metric('GPU', runtime.get('gpu_name') or 'n/a')}"
        f"{_metric('Objects indexed', isaac.get('object_index_count', 0))}"
        f"{_metric('Receptacles indexed', isaac.get('receptacle_index_count', 0))}"
        f"{_metric('USD index', scene_index.get('status', 'unknown'))}"
        f"{_metric('Scene index artifact', 'available' if scene_index_artifact else 'missing')}"
        f"{_metric('Selected USD bindings', selected_binding_summary)}"
        f"{_metric('Segmentation', segmentation.get('status', 'unknown'))}"
        f"{_metric('Seg bboxes', segmentation.get('candidate_bbox_count', 0))}"
        f"{_metric('Seg selected hits', segmentation.get('selected_usd_prim_match_count', 0))}"
        f"{_metric('Snapshots', f'{real_snapshots}/{len(snapshots)} real')}"
        f"{_metric('Semantic pose events', len(semantic_pose_events))}"
        f"{_metric('Pose rendered to USD', _yes_no(semantic_pose_state.get('rendered_to_usd')))}"
        f"{_metric('Pose view capture', pose_view_capture_method)}"
        f"{_metric('Pose render steps', pose_render_steps)}"
        f"{_metric('Mapping gaps', len(mapping_gaps))}"
        "</div>"
    )
    note = (
        "Isaac backend diagnostics are report evidence only. Early cleanup "
        "effects are labeled isaac_semantic_pose and are not planner-backed "
        "or physical-robot manipulation proof."
    )
    mapping_items = "".join(
        "<li>"
        f"<strong>{html.escape(str(item.get('area', 'unknown')))}:</strong> "
        f"{html.escape(str(item.get('status', 'unknown')))} - "
        f"{html.escape(str(item.get('detail', '')))}"
        "</li>"
        for item in mapping_gaps
        if isinstance(item, dict)
    )
    mapping_list = f"<ul>{mapping_items}</ul>" if mapping_items else ""
    return (
        '<section class="panel isaac-runtime">'
        "<h2>Isaac Runtime Diagnostics</h2>"
        f'<p class="note">{html.escape(note)}</p>'
        f"{metrics}"
        f"<p><strong>Scene USD:</strong> {html.escape(str(isaac.get('scene_usd', '')))}</p>"
        f"<p><strong>Scene index artifact:</strong> "
        f"{_artifact_link(scene_index_artifact, run_dir)}</p>"
        f"<p><strong>Scene load reason:</strong> "
        f"{html.escape(str(scene_load.get('reason', '')))}</p>"
        f"<p><strong>Rendering reason:</strong> "
        f"{html.escape(str(rendering.get('reason', '')))}</p>"
        f"<p><strong>Segmentation reason:</strong> "
        f"{html.escape(str(segmentation.get('reason', '')))}</p>"
        f"<p><strong>Semantic pose state:</strong> "
        f"{html.escape(str(semantic_pose_state.get('evidence_note', '')))}</p>"
        f"{mapping_list}"
        f"{_isaac_scene_index_artifact_tables(scene_index_artifact_payload, scene_bindings)}"
        f"{_isaac_semantic_pose_state_tables(semantic_pose_state, semantic_pose_events)}"
        "</section>"
    )


def _load_isaac_scene_index_artifact(run_dir: Path, path: str) -> dict[str, Any]:
    resolved = _resolve_report_asset_path(run_dir, path)
    if resolved is None:
        return {}
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _isaac_scene_index_artifact_tables(
    artifact: dict[str, Any],
    fallback_scene_bindings: dict[str, Any],
) -> str:
    if not artifact:
        return ""
    if not isinstance(fallback_scene_bindings, dict):
        fallback_scene_bindings = {}
    scene_bindings = artifact.get("scene_binding_diagnostics")
    if not isinstance(scene_bindings, dict):
        scene_bindings = fallback_scene_bindings
    object_index = artifact.get("object_index")
    if not isinstance(object_index, dict):
        object_index = {}
    receptacle_index = artifact.get("receptacle_index")
    if not isinstance(receptacle_index, dict):
        receptacle_index = {}
    private_manifest_exposed = artifact.get("private_manifest_exposed_to_agent")
    receptacle_count = artifact.get("receptacle_index_count", len(receptacle_index))
    boundary = (
        '<div class="metric-grid compact">'
        f"{_metric('Artifact schema', artifact.get('schema', 'unknown'))}"
        f"{_metric('Agent-facing', _yes_no(artifact.get('agent_facing')))}"
        f"{_metric('Private manifest exposed', _yes_no(private_manifest_exposed))}"
        f"{_metric('Artifact objects', artifact.get('object_index_count', len(object_index)))}"
        f"{_metric('Artifact receptacles', receptacle_count)}"
        "</div>"
    )
    return (
        "<h3>Scene Index Artifact Rows</h3>"
        f"{boundary}"
        "<h4>Selected USD Binding Rows</h4>"
        f"{_isaac_selected_binding_table(scene_bindings)}"
        "<h4>Selected USD Index Rows</h4>"
        f"{_isaac_selected_index_table(scene_bindings, object_index, receptacle_index)}"
    )


def _isaac_selected_binding_table(scene_bindings: dict[str, Any]) -> str:
    if not scene_bindings:
        return "<p>No selected USD binding diagnostics recorded.</p>"
    rows = []
    for kind, bindings_key in (
        ("object", "selected_object_bindings"),
        ("receptacle", "selected_target_receptacle_bindings"),
    ):
        bindings = scene_bindings.get(bindings_key)
        if not isinstance(bindings, dict):
            continue
        for public_id, binding in sorted(bindings.items(), key=lambda item: str(item[0])):
            if not isinstance(binding, dict):
                continue
            rows.append(
                "<tr>"
                f"<td>{html.escape(kind)}</td>"
                f"<td>{html.escape(str(public_id))}</td>"
                f"<td>{html.escape(str(binding.get('status', '')))}</td>"
                f"<td>{html.escape(str(binding.get('usd_handle', '')))}</td>"
                f"<td>{html.escape(str(binding.get('usd_prim_path', '')))}</td>"
                f"<td>{html.escape(str(binding.get('match_strategy', '')))}</td>"
                f"<td>{html.escape(str(binding.get('index_source', '')))}</td>"
                "</tr>"
            )
    if not rows:
        return "<p>No selected USD binding rows recorded.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Kind</th><th>Public handle</th><th>Status</th><th>USD handle</th>"
        "<th>USD prim</th><th>Match</th><th>Index source</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _isaac_selected_index_table(
    scene_bindings: dict[str, Any],
    object_index: dict[str, Any],
    receptacle_index: dict[str, Any],
) -> str:
    if not scene_bindings:
        return "<p>No selected USD index rows recorded.</p>"
    rows = []
    for kind, bindings_key, index in (
        ("object", "selected_object_bindings", object_index),
        ("receptacle", "selected_target_receptacle_bindings", receptacle_index),
    ):
        bindings = scene_bindings.get(bindings_key)
        if not isinstance(bindings, dict):
            continue
        for public_id, binding in sorted(bindings.items(), key=lambda item: str(item[0])):
            if not isinstance(binding, dict):
                continue
            usd_handle = str(binding.get("usd_handle") or "")
            row = index.get(usd_handle)
            if not isinstance(row, dict):
                row = {}
            usd_prim_path = row.get("usd_prim_path") or binding.get("usd_prim_path", "")
            rows.append(
                "<tr>"
                f"<td>{html.escape(kind)}</td>"
                f"<td>{html.escape(str(public_id))}</td>"
                f"<td>{html.escape(usd_handle)}</td>"
                f"<td>{html.escape(str(usd_prim_path))}</td>"
                f"<td>{html.escape(str(row.get('public_label', '')))}</td>"
                f"<td>{html.escape(str(row.get('category', '')))}</td>"
                f"<td>{html.escape(str(row.get('index_source', '')))}</td>"
                "</tr>"
            )
    if not rows:
        return "<p>No selected USD index rows recorded.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Kind</th><th>Public handle</th><th>USD handle</th><th>USD prim</th>"
        "<th>USD label</th><th>USD category</th><th>Index source</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _isaac_semantic_pose_state_tables(
    semantic_pose_state: dict[str, Any],
    semantic_pose_events: list[dict[str, Any]],
) -> str:
    if not semantic_pose_state:
        return ""
    object_poses = semantic_pose_state.get("object_poses")
    if not isinstance(object_poses, dict):
        object_poses = {}
    articulations = semantic_pose_state.get("articulations")
    if not isinstance(articulations, dict):
        articulations = {}
    return (
        "<h3>Semantic Pose State</h3>"
        f"{_isaac_semantic_object_pose_table(object_poses)}"
        f"{_isaac_semantic_articulation_table(articulations)}"
        "<h3>Semantic Pose Events</h3>"
        f"{_isaac_semantic_pose_event_table(semantic_pose_events)}"
    )


def _isaac_semantic_object_pose_table(object_poses: dict[str, Any]) -> str:
    if not object_poses:
        return "<p>No semantic object pose state recorded.</p>"
    rows = []
    for object_id, pose in sorted(object_poses.items(), key=lambda item: str(item[0])):
        if not isinstance(pose, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(object_id))}</td>"
            f"<td>{html.escape(str(pose.get('location_id', '')))}</td>"
            f"<td>{html.escape(str(pose.get('support_receptacle_id', '')))}</td>"
            f"<td>{_yes_no(pose.get('attached_to_robot'))}</td>"
            f"<td>{html.escape(str(pose.get('location_relation', '')))}</td>"
            f"<td>{_yes_no(pose.get('rendered_to_usd'))}</td>"
            f"<td>{html.escape(str(pose.get('usd_prim_path', '')))}</td>"
            f"<td>{html.escape(str(pose.get('support_usd_prim_path', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No semantic object pose rows recorded.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Object</th><th>Location</th><th>Support</th><th>Attached</th>"
        "<th>Relation</th><th>Rendered to USD</th><th>Object USD</th><th>Support USD</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _isaac_semantic_articulation_table(articulations: dict[str, Any]) -> str:
    if not articulations:
        return "<p>No semantic articulation state recorded.</p>"
    rows = []
    for receptacle_id, articulation in sorted(
        articulations.items(),
        key=lambda item: str(item[0]),
    ):
        if not isinstance(articulation, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(receptacle_id))}</td>"
            f"<td>{html.escape(str(articulation.get('joint_state', '')))}</td>"
            f"<td>{_yes_no(articulation.get('open'))}</td>"
            f"<td>{_yes_no(articulation.get('rendered_to_usd'))}</td>"
            f"<td>{html.escape(str(articulation.get('usd_prim_path', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No semantic articulation rows recorded.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Receptacle</th><th>Joint state</th><th>Open</th>"
        "<th>Rendered to USD</th><th>USD prim</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _isaac_semantic_pose_event_table(events: list[dict[str, Any]]) -> str:
    if not events:
        return "<p>No semantic pose mutation events recorded.</p>"
    rows = []
    for event in events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('sequence', '')))}</td>"
            f"<td>{html.escape(str(event.get('tool', '')))}</td>"
            f"<td>{html.escape(str(event.get('state_mutation', '')))}</td>"
            f"<td>{html.escape(str(event.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('location_id', '')))}</td>"
            f"<td>{_yes_no(event.get('rendered_to_usd'))}</td>"
            f"<td>{_yes_no(event.get('planner_backed'))}</td>"
            f"<td>{html.escape(str(event.get('object_usd_prim_path', '')))}</td>"
            f"<td>{html.escape(str(event.get('receptacle_usd_prim_path', '')))}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>#</th><th>Tool</th><th>Mutation</th><th>Object</th><th>Receptacle</th>"
        "<th>Location</th><th>Rendered to USD</th><th>Planner backed</th>"
        "<th>Object USD</th><th>Receptacle USD</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _manipulation_provenance_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("manipulation_evidence") or {}
    if not evidence:
        return ""
    blockers = evidence.get("blockers") or []
    summary = evidence.get("evidence_note") or ""
    badges = "".join(
        (
            _badge("Status", evidence.get("status", "unknown")),
            _badge("Primitive", evidence.get("primitive_provenance", "unknown")),
            _badge("Planner backed", evidence.get("planner_backed", False)),
            _badge("Strict proof", evidence.get("strict_proof_eligible", False)),
            _badge("API semantic edits", evidence.get("api_semantic_state_edits", "unknown")),
        )
    )
    requirements = evidence.get("strict_proof_requirements") or []
    requirements_list = "".join(f"<li>{html.escape(str(item))}</li>" for item in requirements)
    blocker_text = ""
    if blockers:
        blocker_text = f'<p class="note">Capability blocker count: {len(blockers)}.</p>'
    return (
        '<section class="panel manipulation-provenance">'
        "<h2>Manipulation Provenance</h2>"
        f'<p class="note">{html.escape(str(summary))}</p>'
        f'<div class="badges">{badges}</div>'
        f"{blocker_text}"
        f'<ul class="requirements">{requirements_list}</ul>'
        "</section>"
    )


def _attached_planner_proof_section(run_result: dict[str, Any]) -> str:
    proof = run_result.get("planner_backed_manipulation_proof") or {}
    if not proof:
        return ""
    if proof.get("schema") == "planner_backed_cleanup_proof_bundle_v1":
        return _attached_planner_proof_bundle_section(run_result, proof)
    diagnostics = proof.get("runtime_diagnostics") or {}
    images = proof.get("image_artifacts") or {}
    quality = planner_proof_quality_evidence(proof)
    note = (
        proof.get("evidence_note")
        or "Strict standalone planner-backed manipulation proof attached for review."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', proof.get('status', 'unknown'))}"
        f"{_metric('Embodiment', proof.get('embodiment', 'unknown'))}"
        f"{_metric('Proof Quality', quality.get('quality_tier', 'unknown'))}"
        f"{_metric('Steps', proof.get('steps_executed', 'n/a'))}"
        f"{_metric('Qpos delta', proof.get('max_abs_qpos_delta', 'n/a'))}"
        f"{_metric('Containment proven', 'yes' if quality.get('containment_proven') else 'no')}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Strict proof", proof.get("strict_proof_eligible", False)),
            _badge("Planner backed", proof.get("planner_backed", False)),
            _badge("Multi-step motion", quality.get("multi_step_motion", False)),
            _badge("Cleanup primitive", run_result.get("primitive_provenance", "unknown")),
            _badge("Renderer adapter", diagnostics.get("renderer_adapter_enabled", False)),
        )
    )
    views = (
        '<div class="views">'
        f"{_view_figure(images.get('initial'), 'Planner Initial')}"
        f"{_view_figure(images.get('final'), 'Planner Final')}"
        "</div>"
    )
    return (
        '<section class="panel attached-planner-proof">'
        "<h2>Attached Planner-Backed Proof</h2>"
        f'<p class="note">{html.escape(str(note))} Cleanup object moves in this '
        f"artifact remain {html.escape(str(run_result.get('primitive_provenance', 'unknown')))}."
        "</p>"
        f'<p class="note"><strong>Proof Quality:</strong> '
        f"{html.escape(str(quality.get('quality_tier', 'unknown')))}. "
        f"{html.escape(str(quality.get('evidence_note', '')))}</p>"
        f'{metrics}<div class="badges">{badges}</div>{views}</section>'
    )


def _attached_planner_proof_bundle_section(
    run_result: dict[str, Any],
    bundle: dict[str, Any],
) -> str:
    attachments = [item for item in bundle.get("attachments") or [] if isinstance(item, dict)]
    if not attachments:
        return ""
    quality_summary = (
        bundle.get("proof_quality_summary")
        if isinstance(bundle.get("proof_quality_summary"), dict)
        else planner_proof_quality_summary(attachments)
    )
    note = (
        bundle.get("evidence_note")
        or "Multiple strict standalone planner-backed manipulation proofs attached."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', bundle.get('status', 'unknown'))}"
        f"{_metric('Proofs', bundle.get('proof_count', len(attachments)))}"
        f"{_metric('Proof Quality', format_quality_tier_counts(quality_summary))}"
        f"{_metric('Min steps', quality_summary.get('min_steps_executed', 0))}"
        f"{_metric('Cleanup primitive', run_result.get('primitive_provenance', 'unknown'))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Strict proof bundle", bundle.get("strict_proof_eligible", False)),
            _badge("Planner backed", bundle.get("planner_backed", False)),
        )
    )
    rows = []
    views = []
    for attachment in attachments:
        proof_id = str(attachment.get("proof_id") or "proof")
        binding = attachment.get("cleanup_primitive_binding") or {}
        images = attachment.get("image_artifacts") or {}
        quality = planner_proof_quality_evidence(attachment)
        rows.append(
            "<tr>"
            f"<td>{html.escape(proof_id)}</td>"
            f"<td>{html.escape(str(binding.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(binding.get('target_receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(attachment.get('embodiment', 'unknown')))}</td>"
            f"<td>{html.escape(str(quality.get('quality_tier', 'unknown')))}</td>"
            f"<td>{html.escape(str(attachment.get('steps_executed', 'n/a')))}</td>"
            f"<td>{html.escape(str(quality.get('containment_proven', False)))}</td>"
            "</tr>"
        )
        views.append(
            '<div class="proof-view-pair">'
            f"{_view_figure(images.get('initial'), f'{proof_id} Planner Initial')}"
            f"{_view_figure(images.get('final'), f'{proof_id} Planner Final')}"
            "</div>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Proof</th><th>Object</th>'
        "<th>Target</th><th>Embodiment</th><th>Quality</th><th>Steps</th>"
        "<th>Containment proven</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></div>"
    )
    return (
        '<section class="panel attached-planner-proof">'
        "<h2>Attached Planner-Backed Proofs</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'<p class="note"><strong>Proof Quality:</strong> '
        f"{html.escape(format_quality_tier_counts(quality_summary))}. "
        "Attached planner proofs classify robot-motion strength separately from "
        "final cleanup containment.</p>"
        f'{metrics}<div class="badges">{badges}</div>{table}'
        f'<div class="views">{"".join(views)}</div></section>'
    )


def _cleanup_primitive_gate_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("cleanup_primitive_evidence") or {}
    if not evidence:
        return ""
    objects = evidence.get("objects") or []
    rows = []
    for item in objects:
        object_id = html.escape(str(item.get("object_id", "")))
        for step in item.get("subphases") or []:
            label = _display_subphase_from_evidence(step)
            planner_evidence = step.get("planner_primitive_evidence") or {}
            planner_evidence_summary = _planner_primitive_evidence_summary(planner_evidence)
            binding_summary = _planner_primitive_binding_summary(step)
            rows.append(
                "<tr>"
                f"<td>{object_id}</td>"
                f"<td>{html.escape(str(label))}</td>"
                f"<td>{html.escape(str(step.get('detail', '')))}</td>"
                f"<td>{html.escape(str(step.get('phase', '')))}</td>"
                f"<td>{html.escape(str(step.get('primitive_provenance', '')))}</td>"
                f"<td>{html.escape(planner_evidence_summary)}</td>"
                f"<td>{html.escape(binding_summary)}</td>"
                f"<td>{html.escape(str(step.get('state_sync_provenance') or ''))}</td>"
                f"<td>{html.escape(str(step.get('state_mutation') or ''))}</td>"
                "</tr>"
            )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Display subphase</th><th>Subphase role</th><th>Raw phase</th>"
        "<th>Primitive provenance</th>"
        "<th>Planner evidence</th><th>Binding</th><th>State sync</th>"
        "<th>State mutation</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', evidence.get('status', 'unknown'))}"
        f"{_metric('Objects', evidence.get('object_count', 0))}"
        f"{_metric('Subphases', evidence.get('subphase_count', 0))}"
        f"{_metric('Blockers', len(evidence.get('blockers') or []))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Planner-backed cleanup", evidence.get("planner_backed", False)),
            _badge("Strict proof", evidence.get("strict_proof_eligible", False)),
        )
    )
    note = evidence.get("evidence_note") or (
        "Strict cleanup primitive proof requires every displayed cleanup subphase "
        "to be planner_backed."
    )
    return (
        '<section class="panel cleanup-primitive-gate">'
        "<h2>Cleanup Primitive Gate</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div>{table}</section>'
    )


def _planner_primitive_evidence_summary(evidence: Any) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return ""
    executor = str(evidence.get("executor") or "unknown")
    status = str(evidence.get("status") or "unknown")
    payload = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else {}
    run_id = str(payload.get("planner_run_id") or payload.get("run_id") or "")
    if run_id:
        return f"{executor} {status} {run_id}"
    return f"{executor} {status}"


def _planner_primitive_binding_summary(step: dict[str, Any]) -> str:
    if not step.get("planner_primitive_evidence"):
        return ""
    object_match = step.get("object_id_matches")
    target_match = step.get("target_receptacle_id_matches")
    if object_match is True and target_match is True:
        return "object+target"
    if object_match is True:
        return "object"
    failures = []
    if object_match is False:
        failures.append("object mismatch")
    if target_match is False:
        failures.append("target mismatch")
    return ", ".join(failures)


def _planner_cleanup_bridge_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("planner_cleanup_bridge_evidence") or {}
    if not evidence:
        return ""
    target = evidence.get("target_runtime") or {}
    cleanup = evidence.get("cleanup_primitives") or {}
    blockers = evidence.get("blockers") or []
    blocker_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('code', '')))}</td>"
            f"<td>{html.escape(str(item.get('message', '')))}</td>"
            "</tr>"
        )
        for item in blockers
    )
    if blocker_rows:
        blockers_table = (
            '<div class="table-wrap"><table><thead><tr><th>Blocker</th>'
            "<th>Message</th></tr></thead><tbody>"
            f"{blocker_rows}</tbody></table></div>"
        )
    else:
        blockers_table = '<p class="note">No bridge blockers recorded.</p>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', evidence.get('status', 'unknown'))}"
        f"{_metric('Target proof', target.get('embodiment', 'missing'))}"
        f"{_metric('Cleanup gate', cleanup.get('status', 'missing'))}"
        f"{_metric('Subphases', cleanup.get('subphase_count', 0))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Target RBY1M/CuRobo ready", evidence.get("target_runtime_ready", False)),
            _badge("Cleanup primitives ready", evidence.get("cleanup_primitives_ready", False)),
            _badge("Bridge ready", evidence.get("planner_backed", False)),
        )
    )
    note = evidence.get("evidence_note") or (
        "Planner cleanup bridge readiness joins target runtime proof with cleanup subphase "
        "primitive provenance."
    )
    return (
        '<section class="panel planner-cleanup-bridge">'
        "<h2>Planner Cleanup Bridge</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div>{blockers_table}</section>'
    )


def _planner_proof_requests_section(run_result: dict[str, Any]) -> str:
    manifest = run_result.get("planner_proof_requests") or {}
    if not manifest:
        return ""
    requests = manifest.get("requests") or []
    rows = "".join(_planner_proof_request_row(request) for request in requests)
    if rows:
        table = (
            '<div class="table-wrap"><table><thead><tr>'
            "<th>Request</th><th>Status</th><th>Object</th><th>Source</th>"
            "<th>Target</th><th>Tools</th><th>Planner object</th>"
            "<th>Planner target</th><th>Blockers</th></tr></thead><tbody>"
            f"{rows}</tbody></table></div>"
        )
    else:
        table = '<p class="note">No planner proof requests recorded.</p>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Requests', manifest.get('request_count', len(requests)))}"
        f"{_metric('Ready', manifest.get('ready_count', 0))}"
        f"{_metric('Blocked', len(manifest.get('blockers') or []))}"
        "</div>"
    )
    note = manifest.get("evidence_note") or (
        "Private post-run handoff for local planner proof generation; not Agent View."
    )
    return (
        '<section class="panel planner-proof-requests">'
        "<h2>Planner Proof Requests</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f"{metrics}{table}</section>"
    )


def _planner_proof_request_row(request: dict[str, Any]) -> str:
    binding = request.get("binding") if isinstance(request.get("binding"), dict) else {}
    probe_args = request.get("planner_probe_args") or {}
    planner_object = (
        binding.get("planner_object_id") or probe_args.get("--cleanup-planner-object-id") or ""
    )
    planner_target = (
        binding.get("planner_target_receptacle_id")
        or probe_args.get("--cleanup-planner-target-receptacle-id")
        or ""
    )
    blockers = ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in request.get("blockers") or []
        if isinstance(item, dict)
    )
    tools = ", ".join(str(item) for item in request.get("tools") or [])
    status = "ready" if request.get("ready") else "blocked"
    return (
        "<tr>"
        f"<td>{html.escape(str(request.get('request_id', '')))}</td>"
        f"<td>{html.escape(status)}</td>"
        f"<td>{html.escape(str(request.get('object_id', '')))}</td>"
        f"<td>{html.escape(str(request.get('source_receptacle_id', '')))}</td>"
        f"<td>{html.escape(str(request.get('target_receptacle_id', '')))}</td>"
        f"<td>{html.escape(tools)}</td>"
        f"<td>{html.escape(str(planner_object))}</td>"
        f"<td>{html.escape(str(planner_target))}</td>"
        f"<td>{html.escape(blockers)}</td>"
        "</tr>"
    )


def _proof_bundle_commands_section(commands: list[dict[str, Any]]) -> str:
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


def _proof_request_selection_section(selection: dict[str, Any]) -> str:
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


def _proof_execution_horizon_section(horizon: dict[str, Any]) -> str:
    if not horizon:
        return ""
    blockers = horizon.get("blockers") or []
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', horizon.get('status', 'unknown'))}"
        f"{_metric('Command steps', horizon.get('command_steps', 0))}"
        f"{_metric('Command target', horizon.get('command_quality_target', 'unknown'))}"
        f"{_metric('Coverage min steps', horizon.get('prior_covered_min_proof_steps', 1))}"
        f"{_metric('Coverage floor', horizon.get('prior_covered_quality_floor', 'unknown'))}"
        "</div>"
    )
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
        f"{metrics}{blockers_table}</section>"
    )


def _grasp_feasibility_mitigation_decision_section(decision: dict[str, Any]) -> str:
    if not decision:
        return ""
    missing_assets = ", ".join(
        str(value) for value in decision.get("missing_grasp_asset_uids") or []
    )
    exception_types = ", ".join(
        str(value) for value in decision.get("grasp_load_exception_types") or []
    )
    metrics = (
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
        f'{metrics}<div class="decision-cards">{cards}</div>{table}</section>'
    )


def _decision_card(title: str, value: Any, detail: Any) -> str:
    return (
        '<article class="decision-card">'
        f"<h3>{html.escape(str(title))}</h3>"
        f"<strong>{html.escape(str(value))}</strong>"
        f"<p>{html.escape(str(detail))}</p>"
        "</article>"
    )


def _grasp_cache_availability_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight:
        return ""
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Assets', preflight.get('asset_count', 0))}"
        f"{_metric('Ready assets', preflight.get('ready_asset_count', 0))}"
        f"{_metric('Missing cache assets', preflight.get('missing_cache_asset_count', 0))}"
        f"{_metric('Assets dir source', preflight.get('assets_dir_source', 'unknown'))}"
        f"{_metric('Assets dir exists', preflight.get('assets_dir_exists', False))}"
        "</div>"
    )
    path_rows = _path_table(
        [
            ("Assets dir", preflight.get("assets_dir", "")),
            ("Resolved assets dir", preflight.get("assets_dir_resolved", "")),
            ("Upstream loader", preflight.get("upstream_loader", "")),
        ]
    )
    asset_rows = []
    candidate_rows = []
    object_rows = []
    for asset in preflight.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_uid = str(asset.get("asset_uid") or "")
        asset_rows.append(
            "<tr>"
            f"<td>{html.escape(asset_uid)}</td>"
            f"<td>{html.escape(str(asset.get('status', '')))}</td>"
            f"<td>{html.escape(str(asset.get('loader_file_status', '')))}</td>"
            f"<td>{html.escape(str(asset.get('object_asset_status', '')))}</td>"
            "</tr>"
        )
        for probe in [
            *(asset.get("candidate_grasp_files") or []),
            *(asset.get("folder_probe_files") or []),
        ]:
            if not isinstance(probe, dict):
                continue
            candidate_rows.append(
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
        for object_file in asset.get("object_asset_files") or []:
            if not isinstance(object_file, dict):
                continue
            object_rows.append(
                "<tr>"
                f"<td>{html.escape(asset_uid)}</td>"
                f"<td>{html.escape(str(object_file.get('kind', '')))}</td>"
                f"<td>{html.escape(str(object_file.get('size_bytes', 0)))}</td>"
                f"<td>{html.escape(str(object_file.get('relative_path', '')))}</td>"
                f"<td>{html.escape(str(object_file.get('resolved_path', '')))}</td>"
                "</tr>"
            )
    if not asset_rows:
        asset_rows.append('<tr><td colspan="4">No missing grasp-cache assets.</td></tr>')
    if not candidate_rows:
        candidate_rows.append('<tr><td colspan="10">No grasp-cache file probes.</td></tr>')
    asset_table = (
        '<h3>Asset Status</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Status</th><th>Rigid loader file</th><th>Object asset</th>"
        f"</tr></thead><tbody>{''.join(asset_rows)}</tbody></table></div>"
    )
    candidate_table = (
        '<h3>Loader File Probes</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Source</th><th>Loader role</th><th>Exists</th>"
        "<th>Valid</th><th>Transforms</th><th>Validation</th><th>Bytes</th>"
        "<th>Relative path</th><th>Resolved path</th>"
        f"</tr></thead><tbody>{''.join(candidate_rows)}</tbody></table></div>"
    )
    object_table = ""
    if object_rows:
        object_table = (
            '<h3>Object Asset Probes</h3><div class="table-wrap"><table><thead><tr>'
            "<th>Asset</th><th>Kind</th><th>Bytes</th><th>Relative path</th>"
            "<th>Resolved path</th>"
            f"</tr></thead><tbody>{''.join(object_rows)}</tbody></table></div>"
        )
    recommendation = str(preflight.get("mitigation_recommendation") or "")
    recommendation_html = (
        f'<p class="note">Recommendation: {html.escape(recommendation)}</p>'
        if recommendation
        else ""
    )
    note = preflight.get("evidence_note") or "Grasp cache availability preflight."
    return (
        '<section class="panel grasp-cache-preflight">'
        "<h2>Grasp Cache Availability Preflight</h2>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}{path_rows}'
        f"{recommendation_html}{asset_table}{candidate_table}{object_table}</section>"
    )


def _grasp_cache_generation_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight or preflight.get("status") == "not_applicable":
        return ""
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Assets', preflight.get('asset_count', 0))}"
        f"{_metric('Blockers', preflight.get('blocker_count', 0))}"
        f"{_metric('Ready', _yes_no(preflight.get('ready')))}"
        "</div>"
    )
    paths = _path_table(
        [
            ("MolmoSpaces Python", preflight.get("molmospaces_python", "")),
            ("MolmoSpaces root", preflight.get("molmospaces_root", "")),
            ("Assets dir", preflight.get("assets_dir", "")),
            ("Objects list path", preflight.get("objects_list_path", "")),
            ("Working dir", preflight.get("working_dir", "")),
        ]
    )
    asset_rows = []
    for asset in preflight.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        asset_rows.append(
            "<tr>"
            f"<td>{html.escape(str(asset.get('asset_uid', '')))}</td>"
            f"<td>{html.escape(str(asset.get('object_xml_exists', False)))}</td>"
            f"<td>{html.escape(str(asset.get('object_xml', '')))}</td>"
            f"<td>{html.escape(str(asset.get('generated_npz_path', '')))}</td>"
            f"<td>{html.escape(str(asset.get('cache_target_resolved_path', '')))}</td>"
            "</tr>"
        )
    if not asset_rows:
        asset_rows.append('<tr><td colspan="5">No grasp generation assets recorded.</td></tr>')
    asset_table = (
        '<h3>Generation Assets</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Asset</th><th>Object XML exists</th><th>Object XML</th>"
        "<th>Generated NPZ</th><th>Loader cache target</th>"
        f"</tr></thead><tbody>{''.join(asset_rows)}</tbody></table></div>"
    )
    check_rows = []
    for check in preflight.get("checks") or []:
        if not isinstance(check, dict):
            continue
        check_rows.append(
            "<tr>"
            f"<td>{html.escape(str(check.get('name', '')))}</td>"
            f"<td>{html.escape(str(check.get('status', '')))}</td>"
            f"<td>{html.escape(str(check.get('code', '')))}</td>"
            f"<td>{html.escape(str(check.get('path') or check.get('resolved_path') or ''))}</td>"
            f"<td>{html.escape(str(check.get('message') or check.get('stderr') or ''))}</td>"
            "</tr>"
        )
    if not check_rows:
        check_rows.append('<tr><td colspan="5">No generation checks recorded.</td></tr>')
    check_table = (
        '<h3>Prerequisite Checks</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Check</th><th>Status</th><th>Code</th><th>Path</th><th>Message</th>"
        f"</tr></thead><tbody>{''.join(check_rows)}</tbody></table></div>"
    )
    blocker_rows = []
    for blocker in preflight.get("blockers") or []:
        if not isinstance(blocker, dict):
            continue
        blocker_rows.append(
            "<tr>"
            f"<td>{html.escape(str(blocker.get('code', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('name', '')))}</td>"
            f"<td>{html.escape(str(blocker.get('message', '')))}</td>"
            "</tr>"
        )
    blocker_table = (
        '<p class="note">No generation blockers recorded.</p>'
        if not blocker_rows
        else (
            '<h3>Generation Blockers</h3><div class="table-wrap"><table><thead><tr>'
            "<th>Code</th><th>Check</th><th>Message</th>"
            f"</tr></thead><tbody>{''.join(blocker_rows)}</tbody></table></div>"
        )
    )
    command = " ".join(str(part) for part in preflight.get("command") or [])
    command_html = f"<pre><code>{html.escape(command)}</code></pre>" if command else ""
    recommendation = str(preflight.get("mitigation_recommendation") or "")
    recommendation_html = (
        f'<p class="note">Recommendation: {html.escape(recommendation)}</p>'
        if recommendation
        else ""
    )
    note = preflight.get("evidence_note") or "Grasp cache generation preflight."
    return (
        '<section class="panel grasp-cache-generation-preflight">'
        "<h2>Grasp Cache Generation Preflight</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f"{metrics}{recommendation_html}{paths}{asset_table}{check_table}"
        f"{blocker_table}<h3>Proposed Generation Command</h3>{command_html}</section>"
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


def _proof_bundle_warmup_section(warmup: dict[str, Any]) -> str:
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


def _proof_bundle_local_runtime_preflight_section(preflight: dict[str, Any]) -> str:
    if not preflight:
        return ""
    blockers = preflight.get("blockers") or []
    checks = [item for item in preflight.get("checks") or [] if isinstance(item, dict)]
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', preflight.get('status', 'unknown'))}"
        f"{_metric('Requested', _yes_no(preflight.get('requested')))}"
        f"{_metric('Checks', len(checks))}"
        f"{_metric('Blockers', len(blockers))}"
        "</div>"
    )
    rows = [
        ("Python executable", preflight.get("python_executable", "")),
        ("Evidence note", preflight.get("evidence_note", "")),
    ]
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
    check_table = (
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Check</th><th>Status</th><th>Command</th><th>Return code</th><th>Message</th>"
        f"</tr></thead><tbody>{check_rows}</tbody></table></div>"
        if check_rows
        else ""
    )
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
    return (
        '<section class="panel proof-bundle-local-runtime-preflight">'
        "<h2>Local Runtime Preflight</h2>"
        f"{metrics}{_field_table(rows)}{check_table}{blocker_table}</section>"
    )


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


def _cleanup_rerun_command_section(command: list[str]) -> str:
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


def _cleanup_rerun_artifact_section(cleanup_rerun: dict[str, Any]) -> str:
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


def _display_subphase_from_evidence(step: dict[str, Any]) -> str:
    label = step.get("label")
    if label:
        return str(label)
    return semantic_subphase_text(step.get("phase"))


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


def _agent_view_section(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    runtime_metric_map = (
        agent_view.get("runtime_metric_map") or run_result.get("runtime_metric_map") or {}
    )
    fixture_hints = agent_view.get("fixture_hints") or {}
    observed = agent_view.get("observed_objects") or []
    raw_observations = agent_view.get("raw_fpv_observations") or []
    worklist = agent_view.get("cleanup_worklist") or {}
    scratchpad = run_result.get("agent_scratchpad") or {}
    waypoints = metric_map.get("inspection_waypoints") or []
    rooms = fixture_hints.get("rooms") or []
    mode = agent_view.get("perception_mode", "visible_object_detections")
    if mode == "raw_fpv_only":
        observed_table = (
            '<p class="note">Raw FPV-only mode is active. Structured movable-object '
            "detections, categories, support estimates, target labels, and generated "
            "mess truth are not present in Agent View.</p>"
        )
    elif mode == "camera_model_policy":
        rows = []
        for item in observed:
            support = item.get("support_estimate") or {}
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
                f"<td>{html.escape(str(item.get('category', '')))}</td>"
                f"<td>{html.escape(str(support.get('fixture_id', '')))}</td>"
                f"<td>{html.escape(str(item.get('source_observation_id', '')))}</td>"
                f"<td>{html.escape(str(item.get('model_provenance', '')))}</td>"
                "</tr>"
            )
        if not rows:
            observed_table = "<p>No camera-model candidates registered.</p>"
        else:
            observed_table = (
                '<div class="table-wrap"><table><thead><tr><th>Observed handle</th>'
                "<th>Category</th><th>Support estimate</th><th>Raw observation</th>"
                "<th>Model provenance</th></tr></thead><tbody>"
                + "".join(rows)
                + "</tbody></table></div>"
            )
    else:
        rows = []
        for item in observed:
            support = item.get("support_estimate") or {}
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
                f"<td>{html.escape(str(item.get('category', '')))}</td>"
                f"<td>{html.escape(str(item.get('current_room_id', '')))}</td>"
                f"<td>{html.escape(str(support.get('fixture_id', '')))}</td>"
                "</tr>"
            )
        if not rows:
            observed_table = "<p>No objects observed.</p>"
        else:
            observed_table = (
                '<div class="table-wrap"><table><thead><tr><th>Observed handle</th>'
                "<th>Category</th><th>Room</th><th>Support estimate</th></tr></thead>"
                "<tbody>" + "".join(rows) + "</tbody></table></div>"
            )
    summary = (
        f"{len(metric_map.get('rooms') or [])} public rooms, "
        f"{len(rooms)} fixture-hint room rows, {len(waypoints)} inspection waypoints, "
        f"{len(observed)} observed object handles, "
        f"{len(raw_observations)} raw FPV observations."
    )
    sweep_note = (
        '<p class="note">Semantic Sweep Mode: cleanup actions were disabled. '
        "This report shows runtime-map evidence from public observations, not "
        "private cleanup target truth.</p>"
        if run_result.get("semantic_sweep_mode") is True
        else ""
    )
    return (
        '<section class="panel agent-view"><h2>Agent View</h2>'
        f'<p class="note">{html.escape(summary)} No Generated Mess Set, target count, '
        "acceptable destination sets, is_misplaced labels, or global movable-object "
        "inventory are present here.</p>"
        f"{sweep_note}"
        f"{_runtime_metric_map_table(runtime_metric_map)}"
        f"{_worklist_summary_table(worklist)}"
        f"{_skill_scratchpad_table(scratchpad)}{observed_table}</section>"
    )


def _runtime_metric_map_table(runtime_metric_map: dict[str, Any]) -> str:
    if not runtime_metric_map:
        return ""
    static_map = runtime_metric_map.get("static_map") or {}
    anchors = runtime_metric_map.get("public_semantic_anchors") or []
    observed = runtime_metric_map.get("observed_objects") or []
    candidates = runtime_metric_map.get("map_update_candidates") or []
    map_mode = runtime_metric_map.get("map_mode", "rich")
    generated = runtime_metric_map.get("generated_exploration_candidates") or []
    summary = (
        f"schema={runtime_metric_map.get('schema', '')}, "
        f"map mode={map_mode}, "
        f"static fixtures={len(static_map.get('fixtures') or [])}, "
        f"public semantic anchors={len(anchors)}, "
        f"observed objects={len(observed)}, update candidates={len(candidates)}, "
        f"generated exploration candidates={len(generated)}, "
        f"source map mutated={runtime_metric_map.get('source_map_mutated')}"
    )
    anchor_rows = []
    for item in anchors:
        anchor_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('waypoint_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('producer_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('promotion_status', '')))}</td>"
            "</tr>"
        )
    anchor_table = (
        "<p>No public semantic anchors yet.</p>"
        if not anchor_rows
        else (
            '<div class="table-wrap"><table><thead><tr><th>Anchor</th>'
            "<th>Type</th><th>Category</th><th>Waypoint</th>"
            "<th>Producer</th><th>Promotion</th></tr></thead><tbody>"
            + "".join(anchor_rows)
            + "</tbody></table></div>"
        )
    )
    rows = []
    for item in observed:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('state', '')))}</td>"
            f"<td>{html.escape(str(item.get('actionability', '')))}</td>"
            f"<td>{html.escape(str(item.get('producer_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_observation_id', '')))}</td>"
            "</tr>"
        )
    observed_table = (
        "<p>No runtime observed objects yet.</p>"
        if not rows
        else (
            '<div class="table-wrap"><table><thead><tr><th>Handle</th>'
            "<th>Category</th><th>State</th><th>Actionability</th>"
            "<th>Producer</th><th>Observation</th></tr></thead><tbody>"
            + "".join(rows)
            + "</tbody></table></div>"
        )
    )
    candidate_note = (
        "<p>No map update candidates proposed.</p>"
        if not candidates
        else f"<p>{len(candidates)} map update candidates proposed for review.</p>"
    )
    return (
        "<h3>Runtime Metric Map</h3>"
        f'<p class="note">{html.escape(summary)}. Static map, observed objects, '
        "public semantic anchors, and map update candidates remain separate.</p>"
        f"{anchor_table}{observed_table}{candidate_note}"
    )


def _worklist_summary_table(worklist: dict[str, Any]) -> str:
    objects = worklist.get("objects") or []
    if not objects:
        return ""
    rows = []
    for item in objects:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('state', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_fixture_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate_fixture_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('last_waypoint_id', '')))}</td>"
            "</tr>"
        )
    return (
        "<h3>Observed Handle Lifecycle</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Handle</th><th>State</th>'
        "<th>Category</th><th>Seen at fixture</th><th>Public candidate fixture</th>"
        "<th>Last waypoint</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _skill_scratchpad_table(scratchpad: dict[str, Any]) -> str:
    if not scratchpad:
        return ""
    handles = scratchpad.get("observed_handles") or {}
    notes = scratchpad.get("notes") or []
    return (
        "<h3>Skill Scratchpad</h3>"
        '<p class="note">Non-authoritative agent notes. Cleanup Worklist facts '
        "remain authoritative for done gates, reports, and checkers.</p>"
        '<div class="metric-grid">'
        f"{_metric('Schema', scratchpad.get('schema', ''))}"
        f"{_metric('Authoritative', _yes_no(bool(scratchpad.get('authoritative'))))}"
        f"{_metric('Scratch handles', len(handles))}"
        f"{_metric('Notes', len(notes))}"
        "</div>"
    )


def _cleanup_policy_trace_section(run_result: dict[str, Any]) -> str:
    trace = run_result.get("cleanup_policy_trace") or {}
    if not trace:
        return ""
    events = [item for item in trace.get("events") or [] if isinstance(item, dict)]
    has_review_fields = any(
        item.get("decision") or item.get("progress") or item.get("reason") for item in events
    )
    rows = []
    for item in events:
        review_cells = ""
        if has_review_fields:
            review_cells = (
                f"<td>{html.escape(str(item.get('decision', '')))}</td>"
                f"<td>{html.escape(str(item.get('progress', '')))}</td>"
                f"<td>{html.escape(str(item.get('reason', '')))}</td>"
            )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('index', '')))}</td>"
            f"<td>{html.escape(str(item.get('tool', '')))}</td>"
            f"<td>{html.escape(str(item.get('role', '')))}</td>"
            f"<td>{html.escape(str(item.get('waypoint_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('fixture_id', '')))}</td>"
            f"{review_cells}"
            "</tr>"
        )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Waypoint source', trace.get('waypoint_source', 'unknown'))}"
        f"{_metric('Loop style', trace.get('loop_style', 'unknown'))}"
        f"{_metric('Review kind', trace.get('agent_review_kind', 'n/a'))}"
        f"{_metric('Waypoint observes', trace.get('scan_observe_count', 0))}"
        f"{_metric('Cleanup actions', trace.get('cleanup_action_count', 0))}"
        f"{_metric('Post-place observes', trace.get('post_place_observe_count', 0))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge(
                "First cleanup before full survey",
                trace.get("first_cleanup_before_full_survey", False),
            ),
            _badge("Post-place observe complete", trace.get("post_place_observe_complete", False)),
            _badge("Agent reasoning visible", trace.get("agent_reasoning_visible", False)),
        )
    )
    review_headers = ""
    if has_review_fields:
        review_headers = "<th>Decision</th><th>Progress</th><th>Reason</th>"
    table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Tool</th>'
        "<th>Role</th><th>Waypoint</th><th>Object</th><th>Fixture</th>"
        f"{review_headers}</tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    notes = [
        "inspection_waypoints are static_map_fixture_coverage inputs. Coverage scans, "
        "cleanup actions, and post-place observes are labelled so reviewers can tell "
        "whether the run was interleaved or survey-first. The current public MCP surface "
        "models open_receptacle and close_receptacle as semantic access state around "
        "place_inside."
    ]
    operator_review_note = str(trace.get("operator_review_note") or "").strip()
    if operator_review_note:
        notes.append(operator_review_note)
    note_html = "".join(f'<p class="note">{html.escape(note)}</p>' for note in notes)
    return (
        '<section class="panel cleanup-policy-trace">'
        "<h2>Waypoint Honesty & Cleanup Loop</h2>"
        f"{note_html}"
        f'{metrics}<div class="badges">{badges}</div>{table}</section>'
    )


def _real_robot_readiness_section(run_result: dict[str, Any]) -> str:
    readiness = run_result.get("real_robot_readiness") or {}
    if not readiness:
        return ""
    blockers = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in readiness.get("blocked_capabilities") or []
    )
    nav_summary = ", ".join(
        f"{key}={value}"
        for key, value in (readiness.get("navigation_backend_summary") or {}).items()
    )
    pose_summary = ", ".join(
        f"{key}={value}" for key, value in (readiness.get("pose_source_summary") or {}).items()
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', readiness.get('status', 'unknown'))}"
        f"{_metric('Map bundle', readiness.get('map_bundle_schema', 'unknown'))}"
        f"{_metric('Navigation backends', nav_summary or 'none')}"
        f"{_metric('Pose sources', pose_summary or 'none')}"
        f"{_metric('Backend variant', readiness.get('backend_variant', 'n/a'))}"
        f"{_metric('Movement enabled', readiness.get('movement_enabled', 'n/a'))}"
        f"{_metric('Report-only sim views', readiness.get('report_only_simulation_view_count', 0))}"
        f"{_metric('physical_navigation_pilot', readiness.get('physical_navigation_pilot', False))}"
        f"{_metric('physical_cleanup_ready', readiness.get('physical_cleanup_ready', False))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Map shape", readiness.get("map_bundle_fields_present", False)),
            _badge("PoseStamped waypoints", readiness.get("pose_stamped_waypoints", False)),
            _badge("Static fixtures only", readiness.get("static_fixture_semantic_map", False)),
            _badge(
                "Chase excluded from policy",
                readiness.get("policy_view_chase_excluded", False),
            ),
            _badge("Sim/static navigation only", readiness.get("semantic_navigation_only", False)),
            _badge(
                "Static costmap routes",
                readiness.get("sim_costmap_route_validation", False),
            ),
            _badge("Physical navigation pilot", readiness.get("physical_navigation_pilot", False)),
            _badge("Manipulation blocked", readiness.get("manipulation_blocked", False)),
        )
    )
    if readiness.get("backend_variant") == "molmospaces_sim":
        note = (
            "This section is a MolmoSpaces Agibot Contract Rehearsal. It validates "
            "real_robot_cleanup_v1 contract shape, Agibot-shaped stage sequencing, "
            "and simulated observe/navigation evidence. It is not physical Agibot "
            "GDK execution, not a real movement gate, and not manipulation proof."
        )
    elif readiness.get("backend_variant") == "agibot_gdk":
        movement_flag = str(readiness.get("movement_enabled", False)).lower()
        note = (
            "This section is an AgiBot Navigation + Perception Pilot. Roboclaws keeps "
            "the real_robot_cleanup_v1 public tool boundary while the AgiBot SDK runner "
            "owns GDK execution evidence and per-stage reports. Navigation is physical "
            "only when the session-level movement gate is enabled; "
            f"movement_enabled={movement_flag}, "
            "physical_cleanup_ready=false."
        )
    elif readiness.get("physical_navigation_pilot"):
        physical_flags = (
            f"physical_navigation_pilot={str(readiness.get('physical_navigation_pilot')).lower()}, "
            f"physical_cleanup_ready={str(readiness.get('physical_cleanup_ready')).lower()}."
        )
        note = (
            "This section is a physical Navigation + Perception Pilot. Nav2 waypoint "
            "navigation may execute, reached waypoints are observed, and physical "
            f"cleanup manipulation remains blocked_capability. {physical_flags}"
        )
    else:
        note = (
            "This section checks contract shape, not live ROS/Nav2. Current simulator "
            "navigation is validated against a static Nav2-shaped costmap and still is "
            "not a physical nav2_action; chase imagery is labelled "
            "report_only_simulation_view and is not a policy input."
        )
    return (
        '<section class="panel real-robot-readiness">'
        "<h2>Real-Robot Readiness</h2>"
        f'<p class="note">{html.escape(note)}</p>'
        f'{metrics}<div class="badges">{badges}</div>'
        f'<ul class="requirements">{blockers}</ul></section>'
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
            "manipulation artifacts back to the same real_robot_cleanup_v1 public "
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
            "real_robot_cleanup_v1 tool it supports, so these rows read as "
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
        "agent_view_export": "metric_map, fixture_hints",
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


def _nav2_map_bundle_section(run_dir: Path, run_result: dict[str, Any]) -> str:
    bundle = run_result.get("nav2_map_bundle") or {}
    if not bundle:
        return ""
    artifacts = bundle.get("artifact_paths") or {}
    hashes = bundle.get("artifact_hashes") or {}
    map_contract_label = _map_contract_label(bundle)
    map_contract_note = _map_contract_note(bundle)
    preview = _write_nav2_static_navigation_preview(run_dir, run_result) or artifacts.get(
        "preview_png"
    )
    preview_figure = (
        '<figure class="nav2-preview">'
        f"{_review_image(preview, map_contract_label)}"
        f"<figcaption><strong>{html.escape(map_contract_label)}</strong>"
        "<span>Readable public map: rooms, fixtures, inspection waypoints, and robot pose.</span>"
        "</figcaption>"
        "</figure>"
        if preview
        else ""
    )
    rows = []
    labels = {
        "map_yaml": "map.yaml",
        "occupancy_image": "map.pgm",
        "semantics_json": "semantics.json",
        "robot_profile": "profiles/rby1m.yaml",
        "costmap_params": "costmaps/rby1m.costmap_params.yaml",
        "preview_png": "preview.png",
    }
    for key, label in labels.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(label)}</td>"
            f"<td>{html.escape(str(artifacts.get(key, '')))}</td>"
            f"<td><code>{html.escape(str(hashes.get(key, ''))[:16])}</code></td>"
            "</tr>"
        )
    gaps = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in bundle.get("runtime_costmap_gaps") or []
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Environment', bundle.get('environment_id', 'unknown'))}"
        f"{_metric('Map source', bundle.get('source_provenance', 'unknown'))}"
        f"{_metric('Robot profile', bundle.get('robot_profile_id', 'unknown'))}"
        f"{_metric('Costmap profile', bundle.get('costmap_profile_id', 'unknown'))}"
        f"{_metric('Parameter hash', str(bundle.get('parameter_hash', ''))[:16])}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Artifact</th><th>Path</th>'
        "<th>SHA-256</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    gap_list = (
        f'<ul class="requirements">{gaps}</ul>'
        if gaps
        else '<p class="note">No runtime costmap gaps were recorded.</p>'
    )
    return (
        '<section class="panel nav2-map-bundle">'
        f"<h2>Nav2 Map Bundle <span>{html.escape(_map_contract_subtitle(bundle))}</span></h2>"
        '<p class="note">These files are the map package a Nav2-style robot would '
        "consume: occupancy grid, semantic fixture map, robot footprint, costmap "
        "parameters, and report views. The readable view is rendered from the public "
        "semantic map contract; the raw occupancy artifact remains linked below. This "
        "is not live ROS/Nav2 execution.</p>"
        f'<p class="note">{html.escape(map_contract_note)}</p>'
        f"{metrics}"
        '<div class="nav2-explainer">'
        "<div><strong>What it proves</strong><span>Static map, fixtures, robot profile, "
        "and costmap parameters are versioned together.</span></div>"
        "<div><strong>What it does not prove</strong><span>Dynamic obstacle layers, "
        "TF timing, and rolling local costmaps remain explicit gaps.</span></div>"
        "</div>"
        '<div class="nav2-preview-layout">'
        f"{preview_figure}"
        f"{_nav2_preview_legend()}"
        "</div>"
        '<details class="artifact-details"><summary>Map files, hashes, and known gaps</summary>'
        f"{table}{gap_list}</details></section>"
    )


def _map_contract_label(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "")
    if "agibot" in source.lower():
        return "Agibot GDK map view"
    if "molmospaces" in source.lower():
        return "Agibot-shaped semantic map view"
    return "Static navigation map preview"


def _map_contract_subtitle(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "")
    if "agibot" in source.lower():
        return "Agibot GDK map artifact"
    if "molmospaces" in source.lower():
        return "Agibot-shaped static map contract"
    return "Static map contract"


def _map_contract_note(bundle: dict[str, Any]) -> str:
    source = str(bundle.get("source_provenance") or "unknown")
    source_root = str(bundle.get("source_bundle_root") or "")
    map_id = str(bundle.get("map_id") or "unknown")
    source_schema = str(bundle.get("source_schema") or "")
    if "agibot" in source.lower():
        prefix = "This map bundle came from an Agibot GDK map artifact."
    elif "molmospaces" in source.lower():
        prefix = (
            "This map bundle is not a real Agibot GDK map; it is a MolmoSpaces public "
            "semantic map rendered through the Agibot-shaped real_robot_cleanup_v1 "
            "map contract."
        )
    else:
        prefix = "This map bundle is a static public map-contract artifact."
    details = f" Source provenance: {source}; map id: {map_id}."
    if source_schema:
        details += f" Source schema: {source_schema}."
    if source_root:
        details += f" Source root: {source_root}."
    return prefix + details


def _write_nav2_static_navigation_preview(run_dir: Path, run_result: dict[str, Any]) -> str:
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    fixture_hints = agent_view.get("fixture_hints") or {}
    rooms = metric_map.get("rooms") or []
    waypoints = metric_map.get("inspection_waypoints") or []
    fixture_rooms = fixture_hints.get("rooms") or []
    if not rooms and not waypoints and not fixture_rooms:
        return ""
    output_dir = run_dir / "map_bundle"
    output_dir.mkdir(parents=True, exist_ok=True)
    bundle = run_result.get("nav2_map_bundle") or {}
    artifacts = bundle.get("artifact_paths") or {}
    map_pgm = run_dir / str(artifacts.get("occupancy_image") or "map_bundle/map.pgm")
    map_yaml = run_dir / str(artifacts.get("map_yaml") or "map_bundle/map.yaml")
    if (
        map_pgm.is_file()
        and map_yaml.is_file()
        and _nav2_occupancy_preview_has_usable_framing(
            map_pgm=map_pgm,
            map_yaml=map_yaml,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
        )
    ):
        return _write_nav2_occupancy_navigation_preview(
            run_dir,
            output_dir=output_dir,
            map_pgm=map_pgm,
            map_yaml=map_yaml,
            metric_map=metric_map,
            fixture_hints=fixture_hints,
        )
    output_path = output_dir / "report_static_navigation_map.png"
    image = Image.new("RGB", (1100, 360), (248, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.text((28, 22), _map_contract_label(bundle), fill=(30, 34, 42))
    transform = _nav2_preview_transform(rooms, waypoints, fixture_rooms)
    room_labels: list[tuple[int, int, str]] = []

    for room in rooms:
        points = room.get("polygon") or []
        if len(points) < 2:
            continue
        xs = [float(point.get("x", 0.0)) for point in points]
        ys = [float(point.get("y", 0.0)) for point in points]
        left, top = transform(min(xs), max(ys))
        right, bottom = transform(max(xs), min(ys))
        draw.rectangle(
            (left, top, right, bottom),
            fill=(232, 238, 246),
            outline=(148, 163, 184),
            width=2,
        )
        room_labels.append((left, top, str(room.get("room_label") or room.get("room_id") or "")))

    for room in fixture_rooms:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            footprint = fixture.get("footprint") or {}
            x, y = transform(float(pose.get("x", 0.0)), float(pose.get("y", 0.0)))
            half_w = max(
                14,
                int(float(footprint.get("width_m") or 0.5) * getattr(transform, "x_scale") * 0.5),
            )
            half_h = max(
                8,
                int(float(footprint.get("depth_m") or 0.35) * getattr(transform, "y_scale") * 0.5),
            )
            draw.rounded_rectangle(
                (x - half_w, y - half_h, x + half_w, y + half_h),
                radius=3,
                fill=(113, 124, 141),
                outline=(71, 85, 105),
            )

    for waypoint in waypoints:
        x, y = transform(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=(35, 134, 90))

    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        x, y = transform(float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0)))
        draw.ellipse(
            (x - 13, y - 13, x + 13, y + 13),
            fill=(46, 88, 178),
            outline=(30, 64, 130),
            width=2,
        )
        draw.text((x + 16, y - 7), "robot", fill=(30, 64, 130))

    for left, top, label in room_labels:
        label_y = max(48, top - 18)
        text_box = draw.textbbox((left, label_y), label)
        draw.rounded_rectangle(
            (text_box[0] - 4, text_box[1] - 2, text_box[2] + 4, text_box[3] + 2),
            radius=3,
            fill=(248, 250, 252),
            outline=(213, 220, 230),
        )
        draw.text((left, label_y), label, fill=(51, 65, 85))

    image.save(output_path, format="PNG")
    return _report_asset_src(output_path, run_dir)


def _nav2_occupancy_preview_has_usable_framing(
    *,
    map_pgm: Path,
    map_yaml: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> bool:
    """Return whether the occupancy map gives the semantic overlay a readable frame."""

    try:
        image = Image.open(map_pgm)
    except OSError:
        return False
    if image.width < 1 or image.height < 1:
        return False
    parsed_yaml = _simple_map_yaml(map_yaml.read_text(encoding="utf-8"))
    resolution = float(parsed_yaml.get("resolution") or metric_map.get("resolution_m") or 0.05)
    if resolution <= 0:
        return False
    origin = parsed_yaml.get("origin") if isinstance(parsed_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]
    points = _nav2_semantic_preview_points(metric_map, fixture_hints)
    if len(points) < 2:
        return False

    cols: list[int] = []
    rows: list[int] = []
    for x, y in points:
        cols.append(int(round((x - float(origin[0])) / resolution)))
        rows.append(image.height - 1 - int(round((y - float(origin[1])) / resolution)))
    min_col, max_col = max(0, min(cols)), min(image.width - 1, max(cols))
    min_row, max_row = max(0, min(rows)), min(image.height - 1, max(rows))
    if min_col >= max_col or min_row >= max_row:
        return False
    x_coverage = (max_col - min_col + 1) / image.width
    y_coverage = (max_row - min_row + 1) / image.height
    return x_coverage >= 0.35 and y_coverage >= 0.35


def _nav2_semantic_preview_points(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for room in metric_map.get("rooms") or []:
        for point in room.get("polygon") or []:
            points.append((float(point.get("x", 0.0)), float(point.get("y", 0.0))))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        points.append((float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))))
    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        points.append((float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0))))
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            points.append((float(pose.get("x", 0.0)), float(pose.get("y", 0.0))))
    return points


def _write_nav2_occupancy_navigation_preview(
    run_dir: Path,
    *,
    output_dir: Path,
    map_pgm: Path,
    map_yaml: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> str:
    output_path = output_dir / "report_static_navigation_map.png"
    image = Image.open(map_pgm).convert("L")
    image = Image.eval(image, lambda value: 255 if value >= 250 else 28 if value <= 5 else 205)
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    parsed_yaml = _simple_map_yaml(map_yaml.read_text(encoding="utf-8"))
    resolution = float(parsed_yaml.get("resolution") or metric_map.get("resolution_m") or 0.05)
    origin = parsed_yaml.get("origin") if isinstance(parsed_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]

    def transform(x: float, y: float) -> tuple[int, int]:
        col = int(round((x - float(origin[0])) / resolution))
        row = image.height - 1 - int(round((y - float(origin[1])) / resolution))
        return col, row

    for room in metric_map.get("rooms") or []:
        points = [
            transform(float(point.get("x", 0.0)), float(point.get("y", 0.0)))
            for point in room.get("polygon") or []
        ]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=(72, 121, 210, 44), outline=(31, 79, 168, 210))
        cx = sum(point[0] for point in points) / len(points)
        cy = sum(point[1] for point in points) / len(points)
        draw.text(
            (cx - 28, cy - 7),
            str(room.get("room_label") or room.get("room_id") or "")[:18],
            fill=(15, 39, 82, 255),
        )

    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            x, y = transform(float(pose.get("x", 0.0)), float(pose.get("y", 0.0)))
            draw.rectangle((x - 7, y - 5, x + 7, y + 5), fill=(130, 82, 32, 230))

    for waypoint in metric_map.get("inspection_waypoints") or []:
        x, y = transform(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(34, 158, 91, 245))
        draw.text((x + 7, y - 6), str(waypoint.get("waypoint_id") or ""), fill=(12, 74, 38, 255))

    robot_pose = metric_map.get("robot_pose") or {}
    if robot_pose:
        x, y = transform(float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0)))
        draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(46, 88, 178, 240))
        draw.text((x + 12, y - 7), "robot", fill=(22, 50, 112, 255))

    max_width = 1200
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, max(1, int(image.height * ratio))))
    image.save(output_path, format="PNG")
    return _report_asset_src(output_path, run_dir)


def _simple_map_yaml(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            payload[key.strip()] = [
                float(item.strip()) for item in value.removeprefix("[").removesuffix("]").split(",")
            ]
        elif value.replace(".", "", 1).replace("-", "", 1).isdigit():
            payload[key.strip()] = float(value) if "." in value else int(value)
        else:
            payload[key.strip()] = value.strip('"')
    return payload


def _nav2_preview_transform(
    rooms: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
    fixture_rooms: list[dict[str, Any]],
) -> Any:
    xs: list[float] = []
    ys: list[float] = []
    for room in rooms:
        for point in room.get("polygon") or []:
            xs.append(float(point.get("x", 0.0)))
            ys.append(float(point.get("y", 0.0)))
    for waypoint in waypoints:
        xs.append(float(waypoint.get("x", 0.0)))
        ys.append(float(waypoint.get("y", 0.0)))
    for room in fixture_rooms:
        for fixture in room.get("fixtures") or []:
            pose = fixture.get("pose") or {}
            xs.append(float(pose.get("x", 0.0)))
            ys.append(float(pose.get("y", 0.0)))
    min_x, max_x = (min(xs), max(xs)) if xs else (0.0, 1.0)
    min_y, max_y = (min(ys), max(ys)) if ys else (0.0, 1.0)
    x_span = max(max_x - min_x, 1.0)
    y_span = max(max_y - min_y, 1.0)
    margin_x = 58
    margin_y = 72
    x_scale = (1100 - margin_x * 2) / x_span
    y_scale = (360 - margin_y * 2) / y_span

    def transform(x: float, y: float) -> tuple[int, int]:
        return (
            int(margin_x + (x - min_x) * x_scale),
            int(360 - margin_y - (y - min_y) * y_scale),
        )

    setattr(transform, "x_scale", x_scale)
    setattr(transform, "y_scale", y_scale)
    return transform


def _nav2_preview_legend() -> str:
    items = [
        ("room", "Pale rectangles", "static room / traversable region"),
        ("fixture", "Gray blocks", "static fixture or obstacle footprint"),
        ("waypoint", "Green dots", "inspection waypoints the agent may visit"),
        ("robot", "Blue dot", "current robot pose on the public map"),
    ]
    rows = []
    for kind, label, detail in items:
        rows.append(
            f'<li><span class="legend-swatch {kind}"></span>'
            f"<strong>{html.escape(label)}</strong><small>{html.escape(detail)}</small></li>"
        )
    return (
        '<aside class="nav2-legend"><h3>Legend</h3><ul>'
        + "".join(rows)
        + "</ul><p>This is the robot's static navigation map, not a camera image and "
        "not private mess truth.</p></aside>"
    )


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
            f"<td>{html.escape(str(pipeline.get('pipeline_id', '')))}</td>"
            f"<td>{html.escape(str(pipeline.get('status', '')))}</td>"
            f"<td>{html.escape(stage_text)}</td>"
            f"<td>{html.escape(str(pipeline.get('failure_reason', '')))}</td>"
            f"<td>{html.escape(str(event.get('candidate_count', 0)))}</td>"
            f"<td>{html.escape(handles)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8">No camera-model candidate events recorded.</td></tr>')
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Events', evidence.get('event_count', 0))}"
        f"{_metric('Candidates', evidence.get('candidate_count', 0))}"
        f"{_metric('Pipeline', evidence.get('visual_grounding_pipeline_id', 'sim'))}"
        f"{_metric('Failures', evidence.get('visual_grounding_failure_count', 0))}"
        f"{_metric('Duplicate rate', evidence.get('duplicate_rate', 0))}"
        f"{_metric('Model', evidence.get('model_provenance', 'unknown'))}"
        f"{_metric('Private truth', evidence.get('private_truth_included', 'unknown'))}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Observation</th>'
        "<th>Room</th><th>Pipeline</th><th>Status</th><th>Stages</th>"
        "<th>Failure reason</th><th>Candidates</th><th>Handles</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    note = evidence.get("policy_note") or (
        "Camera-model policy candidates are model-labelled public observations, "
        "not private scoring truth."
    )
    return (
        '<section class="panel camera-model-policy"><h2>Camera Model Policy</h2>'
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
            f"<td>{html.escape(str(item.get('grounding_status', '')))} "
            f"({html.escape(str(item.get('grounding_confidence', '')))})</td>"
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
        "<th>Image region</th><th>Grounding</th><th>Target plausibility</th>"
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
        camera_contract = _robot_view_camera_contract_summary(item.get("camera_control_contract"))
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


def _robot_timeline(run_dir: Path, steps: list[dict[str, Any]]) -> str:
    if not steps:
        return (
            '<section class="panel robot-timeline robot-timeline-empty">'
            "<h2>Robot View Timeline</h2>"
            + _empty_state_block(
                "No robot-view timeline captured",
                "This run did not record FPV/map/chase timeline frames. Review the "
                "Robot & Map tab for static map artifacts, SDK subphase reports, and "
                "navigation rehearsal evidence.",
            )
            + "</section>"
        )
    static_capture = _timeline_uses_static_isaac_captures(steps)
    cards = []
    previous_action = ""
    for index, step in enumerate(steps, start=1):
        views = step.get("views", {})
        pose = step.get("robot_pose") or {}
        focus = annotate_focus_visual_grounding(step.get("focus") or {}) or {}
        semantic_phase = step.get("semantic_phase")
        fpv_bbox = _write_fpv_bbox_verification(run_dir, step, index)
        pose_text = (
            f"x={pose.get('x', '?')} y={pose.get('y', '?')} "
            f"theta={pose.get('theta', '?')} head_pitch={pose.get('head_pitch', '?')}"
        )
        fpv_bbox_figure = _view_figure(fpv_bbox, "FPV + bbox verification") if fpv_bbox else ""
        top_view_verify = (
            _view_figure(views.get("verify"), "Top-view bbox verification sim-only")
            if focus.get("has_focus")
            else ""
        )
        sim_only_figures = [
            figure
            for figure in (
                _view_figure(views.get("chase"), "Chase sim-only"),
                top_view_verify,
            )
            if figure
        ]
        sim_grid_class = "views sim-only-grid"
        if len(sim_only_figures) == 1:
            sim_grid_class += " sim-only-grid-single"
        sim_only_views = (
            '<details class="sim-only-views"><summary>Simulation/report-only views</summary>'
            f'<div class="{sim_grid_class}">'
            f"{''.join(sim_only_figures)}"
            "</div></details>"
            if sim_only_figures
            else ""
        )
        cards.append(
            '<article class="robot-step">'
            f"<h3>{index}. {html.escape(str(step.get('action', step.get('label', 'step'))))}</h3>"
            f'<p class="pose">{html.escape(pose_text)}</p>'
            f"{_semantic_phase_summary(semantic_phase)}"
            f"{_observation_role_summary(step, previous_action)}"
            f"{_focus_summary(step, focus)}"
            f"{_robot_evidence_summary(step)}"
            f"{_robot_view_provenance_summary(step)}"
            f"{_robot_view_camera_contract_summary(step.get('camera_control_contract'))}"
            '<div class="views robot-primary-views">'
            f"{_view_figure(views.get('fpv'), 'FPV')}"
            f"{_view_figure(views.get('map'), 'Map')}"
            f"{fpv_bbox_figure}"
            "</div>"
            f"{sim_only_views}"
            "</article>"
        )
        previous_action = str(step.get("action", step.get("label", "")))
    step_label = "step" if len(cards) == 1 else "steps"
    return (
        '<section class="panel robot-timeline"><h2>Robot View Timeline</h2>'
        f"{_isaac_static_robot_view_notice(static_capture)}"
        '<p class="note">FPV and map are the default review surfaces. FPV+bbox '
        "verification is generated from public visual-grounding boxes when present. "
        "Chase and top-view bbox verification are simulation/report-only evidence, "
        "not policy input and not private scoring truth. Observe role badges distinguish "
        "post-place verification from the next waypoint scan. Focus badges are "
        "public-state object/receptacle bindings; visibility badges say whether "
        "that bound object is actually visible in the current frame.</p>"
        f'<details class="robot-timeline-details" open><summary>Show {len(cards)} captured '
        f"robot-view {step_label}</summary>" + "".join(cards) + "</details></section>"
    )


def _timeline_uses_static_isaac_captures(steps: list[dict[str, Any]]) -> bool:
    return any(_step_uses_static_isaac_capture(step) for step in steps)


def _step_uses_static_isaac_capture(step: dict[str, Any]) -> bool:
    provenance = step.get("view_provenance")
    if not isinstance(provenance, dict):
        return False
    if provenance.get("semantic_pose_state_refreshed") is False:
        return True
    return "isaac_lab_camera_rgb_static_robot_views" in json.dumps(provenance, sort_keys=True)


def _isaac_static_robot_view_notice(enabled: bool) -> str:
    if not enabled:
        return ""
    return (
        '<p class="note robot-view-caveat"><strong>Isaac report-only view caveat:</strong> '
        "these FPV/map/chase/verify frames are static captures from the loaded USD "
        "scene, reused across semantic cleanup steps. The cleanup state changes are "
        "recorded in backend JSON as isaac_semantic_pose; they are not rendered back "
        "into the Isaac USD stage yet.</p>"
    )


def _robot_view_provenance_summary(step: dict[str, Any]) -> str:
    provenance = (
        step.get("view_provenance") if isinstance(step.get("view_provenance"), dict) else {}
    )
    if not provenance:
        return ""
    note = str(provenance.get("evidence_note") or "")
    if _step_uses_static_isaac_capture(step):
        badges = _badge("Isaac view", "static report-only")
        badges += _badge("Step render", "not refreshed")
    elif _step_uses_refreshed_isaac_semantic_pose_capture(step):
        badges = _badge("Isaac view", "semantic pose rerender")
        badges += _badge("Step render", "refreshed")
    else:
        return ""
    if note:
        badges += _badge("Evidence note", note)
    return '<div class="semantic-badges robot-view-provenance">' + badges + "</div>"


def _step_uses_refreshed_isaac_semantic_pose_capture(step: dict[str, Any]) -> bool:
    provenance = step.get("view_provenance")
    if not isinstance(provenance, dict):
        return False
    if provenance.get("semantic_pose_state_refreshed") is True:
        return True
    return "isaac_lab_camera_rgb_semantic_pose_robot_views" in json.dumps(
        provenance,
        sort_keys=True,
    )


def _robot_view_camera_contract_summary(contract: Any) -> str:
    if not isinstance(contract, dict):
        return ""
    badges = "".join(
        [
            _badge("Camera contract", contract.get("status", "unknown")),
            _badge("Camera model", contract.get("camera_model", "unknown")),
            _badge("Same-pose API", contract.get("same_pose_api", False)),
        ]
    )
    fpv = (
        contract.get("agent_facing_fpv")
        if isinstance(contract.get("agent_facing_fpv"), dict)
        else {}
    )
    fpv_source = fpv.get("source")
    if fpv_source:
        badges += _badge("FPV source", fpv_source)
    lighting = (
        contract.get("lighting_profile")
        if isinstance(contract.get("lighting_profile"), dict)
        else {}
    )
    if lighting:
        badges += _badge("Lighting", lighting.get("profile_id", "unknown"))
    note = str(contract.get("evidence_note") or "")
    note_html = f'<p class="note">{html.escape(note)}</p>' if note else ""
    return f'<div class="semantic-badges robot-view-camera-contract">{badges}</div>{note_html}'


def _write_fpv_bbox_verification(
    run_dir: Path,
    step: dict[str, Any],
    index: int,
) -> str:
    focus = annotate_focus_visual_grounding(step.get("focus") or {}) or {}
    visibility = focus.get("fpv_visibility") or {}
    boxes = visibility.get("boxes") or []
    if not boxes:
        return ""
    views = step.get("views") or {}
    fpv_path = _resolve_report_asset_path(run_dir, views.get("fpv"))
    if fpv_path is None:
        return ""
    label = str(step.get("label") or f"{index:04d}_fpv")
    output_path = fpv_path.with_name(f"{fpv_path.stem}.bbox.png")
    try:
        with Image.open(fpv_path) as source:
            image = source.convert("RGB")
        draw = ImageDraw.Draw(image)
        for box in boxes:
            _draw_bbox(draw, box)
        image.save(output_path, format="PNG")
    except OSError:
        return ""
    return _report_asset_src(output_path, run_dir) or f"robot_views/{html.escape(label)}.bbox.png"


def _resolve_report_asset_path(run_dir: Path, path: Any) -> Path | None:
    if not path:
        return None
    candidate = Path(str(path))
    if candidate.is_absolute():
        return candidate if candidate.exists() else None
    rooted = run_dir / candidate
    if rooted.exists():
        return rooted
    if candidate.exists():
        return candidate.resolve()
    return None


def _draw_bbox(draw: ImageDraw.ImageDraw, box: dict[str, Any]) -> None:
    bbox = box.get("bbox") or []
    if len(bbox) != 4:
        return
    try:
        x0, y0, x1, y1 = [int(value) for value in bbox]
    except (TypeError, ValueError):
        return
    try:
        color = tuple(int(value) for value in (box.get("color") or [239, 68, 68])[:3])
    except (TypeError, ValueError):
        color = (239, 68, 68)
    label = str(box.get("label") or "")
    draw.rectangle((x0, y0, x1, y1), outline=color, width=3)
    if not label:
        return
    try:
        text_box = draw.textbbox((x0, y0), label)
        text_width = text_box[2] - text_box[0]
        text_height = text_box[3] - text_box[1]
    except AttributeError:
        text_width = max(40, len(label) * 7)
        text_height = 12
    label_y = max(0, y0 - text_height - 6)
    draw.rectangle((x0, label_y, x0 + text_width + 6, label_y + text_height + 6), fill=color)
    draw.text((x0 + 3, label_y + 3), label, fill=(255, 255, 255))


def _visual_core_robot_view_steps(
    run_result: dict[str, Any],
    steps: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not _has_raw_fpv_observations(run_result):
        return steps
    return [step for step in steps if not _is_raw_fpv_observation_step(step)]


def _has_raw_fpv_observations(run_result: dict[str, Any]) -> bool:
    observations = run_result.get("raw_fpv_observations") or (
        (run_result.get("agent_view") or {}).get("raw_fpv_observations") or []
    )
    return bool(observations)


def _is_raw_fpv_observation_step(step: dict[str, Any]) -> bool:
    if step.get("semantic_phase"):
        return False
    action = str(step.get("action") or "")
    label = str(step.get("label") or "")
    return action.startswith("observe raw_fpv_") or "_raw_fpv_" in f"_{label}"


def _semantic_phase_summary(semantic_phase: Any) -> str:
    if not semantic_phase:
        return ""
    raw = str(semantic_phase)
    displayed = display_semantic_subphase(semantic_phase)
    if displayed is None:
        badges = _badge("Subphase", raw)
    else:
        badges = _badge("Subphase", displayed["label"])
        badges += _badge("Role", displayed["detail"])
        badges += _badge("Raw phase", raw)
    return '<div class="semantic-badges">' + badges + "</div>"


def _observation_role_summary(step: dict[str, Any], previous_action: str) -> str:
    if _action_tool(str(step.get("action", ""))) != "observe":
        return ""
    previous_tool = _action_tool(previous_action)
    if previous_tool in {*PLACE_CLEANUP_PHASES, CLOSE_RECEPTACLE_PHASE}:
        role = "post-place verification"
        raw_role = "post_place_observe"
    else:
        role = "waypoint scan"
        raw_role = "coverage_scan_observe"
    badges = _badge("Observe role", role)
    badges += _badge("Raw role", raw_role)
    return '<div class="semantic-badges">' + badges + "</div>"


def _focus_summary(step: dict[str, Any], focus: dict[str, Any]) -> str:
    if not focus.get("has_focus"):
        return ""
    bits = []
    handle = _observed_handle_from_action(str(step.get("action", "")))
    if handle:
        bits.append(_badge("Handle", handle))
    if focus.get("object_label"):
        bits.append(_badge("Object", focus["object_label"]))
    if focus.get("receptacle_label"):
        bits.append(_badge("Target", focus["receptacle_label"]))
    if focus.get("provenance"):
        bits.append(_badge("Focus provenance", focus["provenance"]))
    return '<div class="focus-badges">' + "".join(bits) + "</div>"


def _robot_evidence_summary(step: dict[str, Any]) -> str:
    pose = step.get("robot_pose") or {}
    focus = annotate_focus_visual_grounding(step.get("focus") or {}) or {}
    bits = []
    if pose.get("theta_source"):
        bits.append(_badge("Theta", pose["theta_source"]))
    if pose.get("head_pitch_source"):
        bits.append(_badge("Head pitch", pose["head_pitch_source"]))
    if pose.get("target_room_id"):
        relation = "same room" if pose.get("same_room_as_target") else "room mismatch"
        room_text = f"{relation} ({pose.get('robot_room_id')} -> {pose.get('target_room_id')})"
        bits.append(_badge("Room", room_text))
    if focus.get("has_focus"):
        fpv_visibility = focus.get("fpv_visibility") or {}
        if fpv_visibility.get("status") in {
            "ok",
            "weak_object_visibility",
            "contained_inside",
        }:
            bits.append(_badge("FPV visibility", _visibility_text(fpv_visibility)))
        visibility = focus.get("visibility") or {}
        if visibility.get("status") in {"ok", "weak_object_visibility", "contained_inside"}:
            bits.append(_badge("Verify visibility", _visibility_text(visibility)))
    if not bits:
        return ""
    return '<div class="evidence-badges">' + "".join(bits) + "</div>"


def _visibility_text(visibility: dict[str, Any]) -> str:
    object_pixels = _pixel_count(visibility.get("object_pixels"))
    target_pixels = _pixel_count(visibility.get("receptacle_pixels"))
    status = str(visibility.get("visual_grounding_status") or visibility.get("status") or "")
    if status == "contained_inside":
        object_text = "object contained inside"
    else:
        object_text = f"object {object_pixels} px" if object_pixels > 0 else "object not visible"
    target_text = f"target {target_pixels} px" if target_pixels > 0 else "target not visible"
    if status and status != "ok":
        return f"{status}: {object_text}, {target_text}"
    return f"{object_text}, {target_text}"


def _pixel_count(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _action_tool(action: str) -> str:
    return action.split(" ", 1)[0] if action else ""


def _observed_handle_from_action(action: str) -> str:
    parts = action.split()
    if len(parts) >= 2 and parts[1].startswith("observed_"):
        return parts[1]
    return ""


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

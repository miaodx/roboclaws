from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.semantic_timeline import (
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
    image = Image.new("RGB", (900, 520), (249, 250, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, 888, 508), outline=(190, 194, 202), width=2)
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
            scenario=scenario,
            run_result=run_result,
            trace_events=trace_events,
            before_snapshot=before_snapshot,
            after_snapshot=after_snapshot,
            robot_view_steps=robot_view_steps or [],
        )
    )
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


def _cleanup_report_sections(
    *,
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
            _cleanup_summary_section(scenario=scenario, run_result=run_result, score=score),
            _current_contract_note(run_result),
            _realworld_contract_note(run_result),
            _before_after_section(before_snapshot=before_snapshot, after_snapshot=after_snapshot),
            _object_moves_section(moves),
            _semantic_steps_table(run_result.get("semantic_substeps") or []),
            _robot_timeline(robot_view_steps),
            _score_section(score),
            _manipulation_provenance_section(run_result),
            _attached_planner_proof_section(run_result),
            _cleanup_primitive_gate_section(run_result),
            _planner_cleanup_bridge_section(run_result),
            _planner_proof_requests_section(run_result),
            _agent_view_section(run_result),
            _raw_fpv_observations_section(run_result),
            _camera_model_policy_section(run_result),
            _advisory_review_section(run_result),
            _private_evaluation_section(run_result),
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
        {_metric("Qpos delta", evidence.get("max_abs_qpos_delta", "n/a"))}
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
    {_planner_probe_views_section(evidence)}
    {_planner_probe_cleanup_binding_section(evidence)}
    {_planner_probe_diagnostics_section(evidence)}
    {_planner_probe_cuda_memory_section(evidence)}
    {_planner_probe_curobo_memory_profile_section(evidence)}
    {_planner_probe_curobo_extension_cache_section(evidence)}
    {_planner_probe_warp_compatibility_section(evidence)}
    {_planner_probe_worker_stages_section(evidence)}
    {_rby1m_curobo_gate_section(run_result)}
    {_planner_probe_blockers_section(evidence)}
    {_planner_probe_artifacts_section(run_result)}
    """
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


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
    {_proof_request_selection_section(manifest.get("proof_request_selection") or {})}
    {_proof_bundle_warmup_section(manifest.get("warmup") or {})}
    {_proof_bundle_commands_section(commands)}
    {_proof_bundle_results_section(manifest.get("proof_result_summary") or {})}
    {_cleanup_rerun_command_section(cleanup_command)}
    {_cleanup_rerun_artifact_section(cleanup_rerun)}
    """
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


def _present_sections(sections: list[str]) -> list[str]:
    return [section for section in sections if section]


def _cleanup_summary_section(
    *,
    scenario: CleanupScenario,
    run_result: dict[str, Any],
    score: dict[str, Any],
) -> str:
    restored_summary = f"{score['restored_count']}/{score['total_targets']}"
    return f"""
    <section class="summary">
      <div class="summary-head">
        <p class="eyebrow">Cleanup artifact</p>
        <h1>MolmoSpaces Cleanup Pilot</h1>
      </div>
      {_summary_metrics(run_result, score)}
      <div class="badges">
        {_badge("Scenario", scenario.scenario_id)}
        {_badge("Backend", run_result.get("backend", "unknown"))}
        {_badge("Contract", run_result.get("contract", "legacy"))}
        {_badge("Status", run_result["cleanup_status"])}
        {_badge("Restored", restored_summary)}
        {_badge("Generated mess", _generated_mess_summary(run_result))}
        {_badge("Policy", run_result.get("policy", run_result.get("planner", "unknown")))}
        {_badge("Agent driven", run_result.get("agent_driven", False))}
        {_badge("Provenance", run_result["primitive_provenance"])}
        {_badge("MCP server", run_result.get("mcp_server", "none"))}
        {_robot_badge(run_result)}
      </div>
    </section>
    """


def _before_after_section(*, before_snapshot: Path, after_snapshot: Path) -> str:
    before_name = html.escape(before_snapshot.name)
    after_name = html.escape(after_snapshot.name)
    return f"""
    <section class="panel">
      <div class="section-heading">
        <h2>Before And After</h2>
      </div>
      <div class="snapshots">
        <figure>
          <img src="{before_name}" alt="Before cleanup">
          <figcaption>Before</figcaption>
        </figure>
        <figure>
          <img src="{after_name}" alt="After cleanup">
          <figcaption>After</figcaption>
        </figure>
      </div>
    </section>
    """


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
        f"{_metric('Status', run_result.get('cleanup_status', 'unknown'))}"
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


def _rate_text(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.0%}"
    return "n/a" if value is None else str(value)


def _robot_badge(run_result: dict[str, Any]) -> str:
    robot_name = run_result.get("robot_name")
    if not robot_name:
        return ""
    return _badge("Robot", robot_name)


def _generated_mess_summary(run_result: dict[str, Any]) -> str:
    actual = run_result.get("generated_mess_count")
    requested = run_result.get("requested_generated_mess_count")
    if actual is None:
        return "n/a"
    if requested is None or requested == actual:
        return actual
    return f"{actual} actual / {requested} requested"


def _current_contract_note(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "current_contract":
        return ""
    shortcuts = ", ".join(str(item) for item in run_result.get("current_contract_shortcuts", []))
    note = (
        "Current-contract bridge run. Global scene_objects is intentionally "
        "available for agent/tool viability dogfood; this artifact does not "
        "satisfy ADR-0003 robot-local perception."
    )
    if shortcuts:
        note += f" Shortcut(s): {shortcuts}."
    return f'<section class="panel note-panel"><p class="note">{html.escape(note)}</p></section>'


def _realworld_contract_note(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    note = (
        "ADR-0003 real-world-style cleanup run. The Agent View is limited to "
        "metric map, room-level fixture hints, and robot-local observed object "
        "handles. Private Evaluation is shown only after the run."
    )
    return f'<section class="panel note-panel"><p class="note">{html.escape(note)}</p></section>'


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
    note = (
        proof.get("evidence_note")
        or "Strict standalone planner-backed manipulation proof attached for review."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', proof.get('status', 'unknown'))}"
        f"{_metric('Embodiment', proof.get('embodiment', 'unknown'))}"
        f"{_metric('Steps', proof.get('steps_executed', 'n/a'))}"
        f"{_metric('Qpos delta', proof.get('max_abs_qpos_delta', 'n/a'))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Strict proof", proof.get("strict_proof_eligible", False)),
            _badge("Planner backed", proof.get("planner_backed", False)),
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
        f'{metrics}<div class="badges">{badges}</div>{views}</section>'
    )


def _attached_planner_proof_bundle_section(
    run_result: dict[str, Any],
    bundle: dict[str, Any],
) -> str:
    attachments = [item for item in bundle.get("attachments") or [] if isinstance(item, dict)]
    if not attachments:
        return ""
    note = (
        bundle.get("evidence_note")
        or "Multiple strict standalone planner-backed manipulation proofs attached."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', bundle.get('status', 'unknown'))}"
        f"{_metric('Proofs', bundle.get('proof_count', len(attachments)))}"
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
        rows.append(
            "<tr>"
            f"<td>{html.escape(proof_id)}</td>"
            f"<td>{html.escape(str(binding.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(binding.get('target_receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(attachment.get('embodiment', 'unknown')))}</td>"
            f"<td>{html.escape(str(attachment.get('steps_executed', 'n/a')))}</td>"
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
        "<th>Target</th><th>Embodiment</th><th>Steps</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></div>"
    )
    return (
        '<section class="panel attached-planner-proof">'
        "<h2>Attached Planner-Backed Proofs</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
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
            f"<td>{html.escape(str(item.get('run_result', '')))}</td>"
            f"<td>{html.escape(str(item.get('report', '')))}</td>"
            f"<td><code>{html.escape(command)}</code></td>"
            "</tr>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>#</th><th>Request</th>'
        "<th>Object</th><th>Target</th><th>Proof run result</th><th>Proof report</th>"
        "<th>Command</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    return (
        '<section class="panel proof-bundle-commands">'
        "<h2>Proof Probe Commands</h2>"
        '<p class="note">Command evidence only. A command row is not planner proof until '
        "the referenced proof artifact passes the strict planner probe checker.</p>"
        f"{table}</section>"
    )


def _proof_request_selection_section(selection: dict[str, Any]) -> str:
    if not selection:
        return ""
    selected = selection.get("selected_requests") or []
    excluded = selection.get("excluded_requests") or []
    target_feasibility_blockers = selection.get("target_feasibility_blockers") or []
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
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Mode', selection.get('mode', 'unknown'))}"
        f"{_metric('Ready', selection.get('ready_request_count', 0))}"
        f"{_metric('Selected', selection.get('selected_count', len(selected)))}"
        f"{_metric('Excluded', selection.get('excluded_count', len(excluded)))}"
        f"{_metric('Generated', selection.get('generated_fallback_request_count', len(generated)))}"
        f"{_metric('Discovered aliases', len(discovered_aliases))}"
        f"{_metric('Normalized aliases', len(normalized_aliases))}"
        f"{_metric('Filtered aliases', len(filtered_aliases))}"
        f"{_metric('Filtered pairs', len(filtered_pairs))}"
        f"{_metric('Fallback status', fallback_generation.get('status', 'unknown'))}"
        f"{_metric('Exhaustion blockers', len(exhaustion_blockers))}"
        f"{_metric('Target blockers', target_blocker_count)}"
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
        f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
        "</tr>"
        for item in excluded
        if isinstance(item, dict)
    )
    if not selected_rows:
        selected_rows = '<tr><td colspan="6">No proof requests selected.</td></tr>'
    if not excluded_rows:
        excluded_rows = '<tr><td colspan="6">No proof requests excluded.</td></tr>'
    selected_table = (
        '<h3>Selected Requests</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Type</th><th>Source</th><th>Object</th><th>Target</th>"
        "<th>Prior feasibility</th>"
        f"</tr></thead><tbody>{selected_rows}</tbody></table></div>"
    )
    excluded_table = (
        '<h3>Excluded Requests</h3><div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Object</th><th>Target</th><th>Reason</th>"
        "<th>Prior feasibility</th><th>Prior blockers</th>"
        f"</tr></thead><tbody>{excluded_rows}</tbody></table></div>"
    )
    generated_table = _generated_fallback_requests_table(generated)
    target_blockers_table = _target_feasibility_blockers_table(target_feasibility_blockers)
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
        f"{selected_table}{excluded_table}{target_blockers_table}{generated_table}{discovered_table}"
        f"{normalized_table}{filtered_table}{filtered_pairs_table}{exhaustion_table}</section>"
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
            f"<td>{html.escape(_blocker_codes(fallback.get('prior_blockers') or []))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="8">No generated fallback requests.</td></tr>')
    return (
        "<h3>Generated Fallback Requests</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Request</th><th>Source</th><th>Object</th><th>Target</th>"
        "<th>Planner object alias</th><th>Planner target alias</th><th>Reason</th>"
        "<th>Prior blockers</th>"
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
            f"<td>{html.escape(str(item.get('last_worker_stage', '')))}</td>"
            f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
            f"<td>{html.escape(str(item.get('prior_report', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="10">No target feasibility blockers recorded.</td></tr>')
    return (
        "<h3>Target Feasibility Blockers</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Kind</th><th>Source</th><th>Object or alias</th><th>Target or alias</th>"
        "<th>Derived from</th><th>Reason</th><th>Prior feasibility</th>"
        "<th>Last stage</th><th>Prior blockers</th><th>Proof report</th>"
        f"</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"
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
            f"<td>{html.escape(str(item.get('last_worker_stage', '')))}</td>"
            f"<td>{html.escape(_blocker_codes(item.get('prior_blockers') or []))}</td>"
            f"<td>{html.escape(str(item.get('prior_report', '')))}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="9">No fallback alias pairs filtered.</td></tr>')
    return (
        "<h3>Filtered Fallback Pairs</h3>"
        '<div class="table-wrap"><table><thead><tr>'
        "<th>Source</th><th>Planner object alias</th><th>Planner target alias</th>"
        "<th>Derived from</th><th>Reason</th><th>Prior feasibility</th>"
        "<th>Last stage</th><th>Prior blockers</th><th>Proof report</th>"
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


def _blocker_codes(blockers: list[dict[str, Any]]) -> str:
    return ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in blockers
        if isinstance(item, dict)
    )


def _proof_bundle_results_section(summary: dict[str, Any]) -> str:
    if not summary:
        return ""
    results = summary.get("results") or []
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Expected', summary.get('expected_count', len(results)))}"
        f"{_metric('Results', summary.get('result_count', 0))}"
        f"{_metric('Planner-backed', summary.get('planner_backed_count', 0))}"
        f"{_metric('Timeouts', summary.get('timeout_count', 0))}"
        f"{_metric('Config-import timeouts', summary.get('rby1m_config_import_timeout_count', 0))}"
        f"{_metric('Binding promoted', summary.get('cleanup_binding_promoted_count', 0))}"
        f"{_metric('Execution attempted', summary.get('execution_attempted_count', 0))}"
        f"{_metric('Task-feasible blocked', summary.get('task_feasibility_blocked_count', 0))}"
        f"{_metric('Worker stage events', summary.get('worker_stage_event_count', 0))}"
        f"{_metric('Views', summary.get('view_artifact_count', 0))}"
        "</div>"
    )
    stage_counts = _last_worker_stage_counts_text(summary.get("last_worker_stage_counts") or {})
    stage_counts_html = (
        f'<p class="note">Last worker stages: {html.escape(stage_counts)}</p>'
        if stage_counts
        else ""
    )
    body = (
        "".join(_proof_bundle_result_card(item) for item in results)
        if results
        else '<p class="note">No proof result rows recorded.</p>'
    )
    note = summary.get("evidence_note") or (
        "Bundle-level proof result summary. Strict per-proof checkers remain authoritative."
    )
    return (
        '<section class="panel proof-bundle-results">'
        "<h2>Proof Probe Results</h2>"
        f'<p class="note">{html.escape(str(note))}</p>{metrics}{stage_counts_html}{body}</section>'
    )


def _proof_bundle_result_card(item: dict[str, Any]) -> str:
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
    sampler_adapter = item.get("cleanup_task_sampler_adapter") or {}
    rows = [
        ("Request", item.get("request_id", "")),
        ("Object", item.get("object_id", "")),
        ("Target", item.get("target_receptacle_id", "")),
        ("Status", item.get("status", "")),
        ("Task feasibility", item.get("task_feasibility_status", "")),
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
        ("Exact sampler adapter applied", _yes_no(sampler_adapter.get("applied"))),
        ("Exact sampler adapter class", sampler_adapter.get("task_sampler_class", "")),
        ("Exact sampler adapter target", sampler_adapter.get("planner_target_receptacle_id", "")),
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
        if value
    )
    views = item.get("views") or []
    if views:
        figures = "".join(
            _view_figure(
                view.get("path"),
                f"{item.get('request_id', '')} {view.get('label', '')}",
            )
            for view in views
            if isinstance(view, dict)
        )
        view_html = f'<div class="views">{figures}</div>'
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
        return ""
    return (
        '<section class="panel"><h2>Planner Probe Views</h2>'
        '<div class="views">'
        f"{_view_figure(artifacts.get('initial'), 'Initial')}"
        f"{_view_figure(artifacts.get('final'), 'Final')}"
        "</div></section>"
    )


def _planner_probe_cleanup_binding_section(evidence: dict[str, Any]) -> str:
    sampled = evidence.get("sampled_task_binding") or {}
    requested = evidence.get("requested_cleanup_primitive_binding") or {}
    promoted = evidence.get("cleanup_primitive_binding") or {}
    blockers = evidence.get("cleanup_primitive_binding_blockers") or []
    cleanup_task_config = evidence.get("cleanup_task_config") or {}
    cleanup_task_sampler_adapter = evidence.get("cleanup_task_sampler_adapter") or {}
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
        (
            "Exact sampler adapter applied",
            _yes_no(cleanup_task_sampler_adapter.get("applied")),
        ),
        (
            "Exact sampler adapter class",
            cleanup_task_sampler_adapter.get("task_sampler_class", ""),
        ),
        (
            "Exact sampler adapter target",
            cleanup_task_sampler_adapter.get("planner_target_receptacle_id", ""),
        ),
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
    fixture_hints = agent_view.get("fixture_hints") or {}
    observed = agent_view.get("observed_objects") or []
    raw_observations = agent_view.get("raw_fpv_observations") or []
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
    return (
        '<section class="panel agent-view"><h2>Agent View</h2>'
        f'<p class="note">{html.escape(summary)} No Generated Mess Set, target count, '
        "acceptable destination sets, is_misplaced labels, or global movable-object "
        "inventory are present here.</p>"
        f"{observed_table}</section>"
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
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('observation_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('room_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('model_provenance', '')))}</td>"
            f"<td>{html.escape(str(event.get('candidate_count', 0)))}</td>"
            f"<td>{html.escape(handles)}</td>"
            "</tr>"
        )
    if not rows:
        rows.append('<tr><td colspan="5">No camera-model candidate events recorded.</td></tr>')
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Events', evidence.get('event_count', 0))}"
        f"{_metric('Candidates', evidence.get('candidate_count', 0))}"
        f"{_metric('Model', evidence.get('model_provenance', 'unknown'))}"
        f"{_metric('Private truth', evidence.get('private_truth_included', 'unknown'))}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Observation</th>'
        "<th>Room</th><th>Model provenance</th><th>Candidates</th><th>Handles</th>"
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
        cards.append(
            '<article class="raw-fpv-card">'
            "<div>"
            f"<h3>{html.escape(str(item.get('observation_id', 'observation')))}</h3>"
            f'<p class="pose">room={html.escape(str(item.get("room_id", "")))} '
            f"waypoint={html.escape(str(item.get('waypoint_id', '')))}</p>"
            f'<p class="note">{html.escape(str(item.get("artifact_status", "")))}</p>'
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


def _robot_timeline(steps: list[dict[str, Any]]) -> str:
    if not steps:
        return ""
    cards = []
    for index, step in enumerate(steps, start=1):
        views = step.get("views", {})
        pose = step.get("robot_pose") or {}
        focus = step.get("focus") or {}
        semantic_phase = step.get("semantic_phase")
        pose_text = (
            f"x={pose.get('x', '?')} y={pose.get('y', '?')} "
            f"theta={pose.get('theta', '?')} head_pitch={pose.get('head_pitch', '?')}"
        )
        cards.append(
            '<article class="robot-step">'
            f"<h3>{index}. {html.escape(str(step.get('action', step.get('label', 'step'))))}</h3>"
            f'<p class="pose">{html.escape(pose_text)}</p>'
            f"{_semantic_phase_summary(semantic_phase)}"
            f"{_focus_summary(focus)}"
            f"{_robot_evidence_summary(step)}"
            '<div class="views">'
            f"{_view_figure(views.get('fpv'), 'FPV')}"
            f"{_view_figure(views.get('chase'), 'Chase')}"
            f"{_view_figure(views.get('map'), 'Map')}"
            f"{_view_figure(views.get('verify'), 'Verification') if focus.get('has_focus') else ''}"
            "</div>"
            "</article>"
        )
    return (
        '<section class="panel robot-timeline"><h2>Robot View Timeline</h2>'
        '<p class="note">FPV and chase are rendered from the RBY1M MuJoCo scene. '
        "The map and verification panels are report artifacts from public MuJoCo state, "
        "not private scoring manifest data.</p>" + "".join(cards) + "</section>"
    )


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


def _focus_summary(focus: dict[str, Any]) -> str:
    if not focus.get("has_focus"):
        return ""
    bits = []
    if focus.get("object_label"):
        bits.append(_badge("Object", focus["object_label"]))
    if focus.get("receptacle_label"):
        bits.append(_badge("Target", focus["receptacle_label"]))
    if focus.get("provenance"):
        bits.append(_badge("Focus provenance", focus["provenance"]))
    return '<div class="focus-badges">' + "".join(bits) + "</div>"


def _robot_evidence_summary(step: dict[str, Any]) -> str:
    pose = step.get("robot_pose") or {}
    focus = step.get("focus") or {}
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
        if fpv_visibility.get("status") == "ok":
            fpv_visible = (
                f"object {fpv_visibility.get('object_pixels', 0)} px, "
                f"target {fpv_visibility.get('receptacle_pixels', 0)} px"
            )
            bits.append(_badge("FPV visibility", fpv_visible))
        visibility = focus.get("visibility") or {}
        if visibility.get("status") == "ok":
            visible = (
                f"object {visibility.get('object_pixels', 0)} px, "
                f"target {visibility.get('receptacle_pixels', 0)} px"
            )
            bits.append(_badge("Verify visibility", visible))
    if not bits:
        return ""
    return '<div class="evidence-badges">' + "".join(bits) + "</div>"


def _view_figure(path: Any, label: str) -> str:
    if not path:
        return ""
    escaped_path = html.escape(str(path))
    escaped_label = html.escape(label)
    return (
        "<figure>"
        f'<img src="{escaped_path}" alt="{escaped_label} view">'
        f"<figcaption>{escaped_label}</figcaption>"
        "</figure>"
    )


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
        return ""
    cards = []
    for item in semantic_substeps:
        steps = item.get("steps", [])
        displayed = display_semantic_subphases(steps)
        phase_rail = "".join(
            "<li>"
            f"<span>{html.escape(step['label'])}</span>"
            f"<small>{html.escape(step['detail'])}</small>"
            "</li>"
            for step in displayed
        )
        readback = _semantic_readback(steps)
        cards.append(
            '<article class="semantic-card">'
            '<div class="semantic-card-head">'
            f"<strong>{html.escape(str(item.get('object_id', '')))}</strong>"
            f"<span>{html.escape(str(item.get('source_receptacle_id', '')))}"
            " -> "
            f"{html.escape(str(item.get('target_receptacle_id', '')))}</span>"
            "</div>"
            f'<ol class="phase-rail">{phase_rail}</ol>'
            f'<p class="readback">Readback: {html.escape(readback or "pending")}</p>'
            "</article>"
        )
    return (
        '<section class="panel semantic-section"><h2>Semantic Substeps</h2>'
        '<p class="note">Canonical cleanup loop: nav, pick, nav, open when needed, place.</p>'
        '<div class="semantic-cards">' + "".join(cards) + "</div></section>"
    )


def _semantic_readback(steps: list[dict[str, Any]]) -> str:
    candidates = [
        step for step in steps if step.get("phase") in {"object_done", "place", "place_inside"}
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


def _wrap_html(body: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>MolmoSpaces Cleanup Pilot</title>
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
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 22px;
      box-shadow: 0 14px 34px rgba(25, 32, 44, 0.16);
    }}
    .summary-head {{ display: flex; justify-content: space-between; gap: 16px; align-items: end; }}
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
    .metric strong {{ display: block; color: #ffffff; font-size: 19px; }}
    .panel {{
      background: #ffffff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 18px;
      margin-top: 18px;
      box-shadow: 0 5px 16px rgba(25, 32, 44, 0.06);
    }}
    .note-panel {{ background: #fbfcfd; }}
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
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    figcaption {{ margin-top: 8px; color: #565f70; font-size: 14px; }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
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
    .raw-fpv-grid {{
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
    .semantic-card-head {{
      display: grid;
      gap: 4px;
      margin-bottom: 10px;
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
    .readback {{ margin: 10px 0 0; color: #565f70; font-size: 13px; overflow-wrap: anywhere; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
  </style>
</head>
<body><main>{body}</main></body>
</html>
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

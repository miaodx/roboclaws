from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.semantic_timeline import display_semantic_subphases
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
    moves = _extract_moves(trace_events)
    score = run_result["score"]
    restored_summary = f"{score['restored_count']}/{score['total_targets']}"
    before_name = html.escape(before_snapshot.name)
    after_name = html.escape(after_snapshot.name)
    body = f"""
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
    {_current_contract_note(run_result)}
    {_realworld_contract_note(run_result)}
    {_manipulation_provenance_section(run_result)}
    {_attached_planner_proof_section(run_result)}
    {_cleanup_primitive_gate_section(run_result)}
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
    <section class="panel">
      <h2>Object Moves</h2>
      {_moves_table(moves)}
    </section>
    {_agent_view_section(run_result)}
    {_raw_fpv_observations_section(run_result)}
    {_semantic_steps_table(run_result.get("semantic_substeps") or [])}
    {_robot_timeline(robot_view_steps or [])}
    <section class="panel">
      <h2>Score</h2>
      {_score_table(score)}
    </section>
    {_advisory_review_section(run_result)}
    {_private_evaluation_section(run_result)}
    """
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


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
    {_planner_probe_diagnostics_section(evidence)}
    {_rby1m_curobo_gate_section(run_result)}
    {_planner_probe_blockers_section(evidence)}
    {_planner_probe_artifacts_section(run_result)}
    """
    report_path.write_text(_wrap_html(body), encoding="utf-8")
    return report_path


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


def _cleanup_primitive_gate_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("cleanup_primitive_evidence") or {}
    if not evidence:
        return ""
    objects = evidence.get("objects") or []
    rows = []
    for item in objects:
        object_id = html.escape(str(item.get("object_id", "")))
        for step in item.get("subphases") or []:
            label = f"{step.get('label', '')}/{step.get('detail', '')}"
            rows.append(
                "<tr>"
                f"<td>{object_id}</td>"
                f"<td>{html.escape(str(label))}</td>"
                f"<td>{html.escape(str(step.get('phase', '')))}</td>"
                f"<td>{html.escape(str(step.get('primitive_provenance', '')))}</td>"
                f"<td>{html.escape(str(step.get('state_mutation') or ''))}</td>"
                "</tr>"
            )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Display subphase</th><th>Raw phase</th><th>Primitive provenance</th>"
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
        f"PYOPENGL_PLATFORM={diagnostics.get('pyopengl_platform_env', '')}"
    )
    return (
        '<section class="panel"><h2>Runtime Diagnostics</h2>'
        f'<p class="note">{html.escape(summary)}</p>{module_table}</section>'
    )


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
    return '<div class="semantic-badges">' + _badge("Semantic phase", semantic_phase) + "</div>"


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

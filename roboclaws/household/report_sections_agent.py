from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from roboclaws.household.report_sections_robot import robot_view_camera_contract_summary

ViewFigureRenderer = Callable[[Any, str], str]


def agent_view_section(run_result: dict[str, Any]) -> str:
    if run_result.get("contract") != "realworld_cleanup_v1":
        return ""
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    runtime_metric_map = (
        agent_view.get("runtime_metric_map") or run_result.get("runtime_metric_map") or {}
    )
    static_fixture_projection = agent_view.get("static_fixture_projection") or {}
    observed = agent_view.get("observed_objects") or []
    raw_observations = agent_view.get("raw_fpv_observations") or []
    worklist = agent_view.get("cleanup_worklist") or {}
    scratchpad = run_result.get("agent_scratchpad") or {}
    waypoints = metric_map.get("inspection_waypoints") or []
    rooms = static_fixture_projection.get("rooms") or []
    summary = (
        f"{len(metric_map.get('rooms') or [])} public rooms, "
        f"{len(rooms)} static fixture projection room rows, {len(waypoints)} inspection waypoints, "
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
        f"{runtime_metric_map_table(runtime_metric_map)}"
        f"{worklist_summary_table(worklist)}"
        f"{skill_scratchpad_table(scratchpad)}"
        f"{_observed_objects_table(agent_view, observed)}</section>"
    )


def cleanup_policy_trace_section(run_result: dict[str, Any]) -> str:
    trace = run_result.get("cleanup_policy_trace") or {}
    if not trace:
        return ""
    events = [item for item in trace.get("events") or [] if isinstance(item, dict)]
    has_review_fields = any(
        item.get("decision") or item.get("progress") or item.get("reason") for item in events
    )
    rows = [_cleanup_policy_event_row(item, has_review_fields) for item in events]
    review_headers = (
        "<th>Decision</th><th>Progress</th><th>Reason</th>" if has_review_fields else ""
    )
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
        f'{_cleanup_policy_metrics(trace)}<div class="badges">{_cleanup_policy_badges(trace)}</div>'
        f"{table}</section>"
    )


def evidence_lane_badges(run_result: dict[str, Any], badge_html) -> str:  # noqa: ANN001
    metadata = _evidence_lane_metadata(run_result)
    if not metadata:
        return ""
    camera_labeler = metadata.get("camera_labeler", run_result.get("camera_labeler", ""))
    return "".join(
        (
            badge_html(
                "Evidence lane",
                metadata.get("evidence_lane", run_result.get("evidence_lane", "")),
            ),
            badge_html("Camera labeler", camera_labeler) if camera_labeler else "",
            badge_html("Agent input", metadata.get("agent_input", "")),
            badge_html("Input provenance", metadata.get("input_provenance", "")),
            badge_html("Report", metadata.get("report", "")),
        )
    )


def raw_fpv_observations_section(
    run_result: dict[str, Any],
    *,
    view_figure: ViewFigureRenderer,
) -> str:
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
            f"{view_figure(fpv_path, 'FPV')}"
            "</article>"
        )
    return (
        '<section class="panel raw-fpv-section"><h2>Raw FPV Observations</h2>'
        '<p class="note">Camera-only perception evidence: these rows provide FPV image '
        "artifacts without structured movable-object detections, categories, support "
        "estimates, target labels, or generated mess truth.</p>"
        '<div class="raw-fpv-grid">' + "".join(cards) + "</div></section>"
    )


def model_declared_observations_section(run_result: dict[str, Any]) -> str:
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


def camera_model_policy_section(run_result: dict[str, Any]) -> str:
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
        labeler = (
            evidence.get("camera_labeler")
            or run_result.get("camera_labeler")
            or pipeline.get(
                "pipeline_id",
                "",
            )
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(event.get('observation_id', '')))}</td>"
            f"<td>{html.escape(str(event.get('room_id', '')))}</td>"
            f"<td>{html.escape(str(labeler))}</td>"
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
    camera_labeler = evidence.get("camera_labeler", run_result.get("camera_labeler", ""))
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Events', evidence.get('event_count', 0))}"
        f"{_metric('Candidates', evidence.get('candidate_count', 0))}"
        f"{_metric('Camera labeler', camera_labeler)}"
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


def advisory_review_section(run_result: dict[str, Any]) -> str:
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


def private_evaluation_section(run_result: dict[str, Any]) -> str:
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


def _evidence_lane_metadata(run_result: dict[str, Any]) -> dict[str, Any]:
    metadata = run_result.get("evidence_lane_metadata")
    return metadata or run_result.get("cleanup_profile_metadata", {})


def real_robot_readiness_section(run_result: dict[str, Any]) -> str:
    readiness = run_result.get("real_robot_readiness") or {}
    if not readiness:
        return ""
    blockers = "".join(
        f"<li>{html.escape(str(item))}</li>" for item in readiness.get("blocked_capabilities") or []
    )
    return (
        '<section class="panel real-robot-readiness">'
        "<h2>Real-Robot Readiness</h2>"
        f'<p class="note">{html.escape(_real_robot_readiness_note(readiness))}</p>'
        f"{_real_robot_readiness_metrics(readiness)}"
        f'<div class="badges">{_real_robot_readiness_badges(readiness)}</div>'
        f'<ul class="requirements">{blockers}</ul></section>'
    )


def runtime_metric_map_table(runtime_metric_map: dict[str, Any]) -> str:
    if not runtime_metric_map:
        return ""
    static_map = runtime_metric_map.get("static_map") or {}
    anchors = runtime_metric_map.get("public_semantic_anchors") or []
    observed = runtime_metric_map.get("observed_objects") or []
    target_candidates = runtime_metric_map.get("target_candidates") or []
    target_search = runtime_metric_map.get("target_search_summary") or {}
    candidates = runtime_metric_map.get("map_update_candidates") or []
    map_mode = runtime_metric_map.get("map_mode", "rich")
    generated = runtime_metric_map.get("generated_exploration_candidates") or []
    summary = (
        f"schema={runtime_metric_map.get('schema', '')}, "
        f"map mode={map_mode}, "
        f"static fixtures={len(static_map.get('fixtures') or [])}, "
        f"public semantic anchors={len(anchors)}, "
        f"observed objects={len(observed)}, target candidates={len(target_candidates)}, "
        f"update candidates={len(candidates)}, "
        f"generated exploration candidates={len(generated)}, "
        f"source map mutated={runtime_metric_map.get('source_map_mutated')}"
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
        f"{_semantic_anchor_table(anchors)}{_runtime_observed_table(observed)}"
        f"{_target_candidates_section(target_candidates, target_search)}{candidate_note}"
    )


def worklist_summary_table(worklist: dict[str, Any]) -> str:
    objects = worklist.get("objects") or []
    if not objects:
        return ""
    rows = []
    for item in objects:
        evidence = item.get("visual_grounding_evidence") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('state', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_fixture_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate_fixture_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('actionability_status', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('reviewability_status', '')))}</td>"
            f"<td>{html.escape(str(item.get('last_waypoint_id', '')))}</td>"
            "</tr>"
        )
    return (
        "<h3>Observed Handle Lifecycle</h3>"
        '<div class="table-wrap"><table><thead><tr><th>Handle</th><th>State</th>'
        "<th>Category</th><th>Seen at fixture</th><th>Public candidate fixture</th>"
        "<th>Actionability</th><th>FPV reviewability</th><th>Last waypoint</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def skill_scratchpad_table(scratchpad: dict[str, Any]) -> str:
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


def _observed_objects_table(agent_view: dict[str, Any], observed: list[dict[str, Any]]) -> str:
    mode = agent_view.get("perception_mode", "visible_object_detections")
    if mode == "raw_fpv_only":
        return (
            '<p class="note">Raw FPV-only mode is active. Structured movable-object '
            "detections, categories, support estimates, target labels, and generated "
            "mess truth are not present in Agent View.</p>"
        )
    if mode == "camera_model_policy":
        return _camera_model_observed_table(observed)
    return _visible_object_observed_table(observed)


def _camera_model_observed_table(observed: list[dict[str, Any]]) -> str:
    rows = []
    for item in observed:
        support = item.get("support_estimate") or {}
        evidence = item.get("visual_grounding_evidence") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(support.get('fixture_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_observation_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('model_provenance', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('reviewability_status', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('image_bbox', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No camera-model candidates registered.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr><th>Observed handle</th>'
        "<th>Category</th><th>Support estimate</th><th>Raw observation</th>"
        "<th>Model provenance</th><th>FPV reviewability</th><th>FPV bbox</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _visible_object_observed_table(observed: list[dict[str, Any]]) -> str:
    rows = []
    for item in observed:
        support = item.get("support_estimate") or {}
        evidence = item.get("visual_grounding_evidence") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('current_room_id', '')))}</td>"
            f"<td>{html.escape(str(support.get('fixture_id', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('reviewability_status', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('image_bbox', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No objects observed.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr><th>Observed handle</th>'
        "<th>Category</th><th>Room</th><th>Support estimate</th>"
        "<th>FPV reviewability</th><th>FPV bbox</th></tr></thead>"
        "<tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _semantic_anchor_table(anchors: list[dict[str, Any]]) -> str:
    rows = []
    for item in anchors:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('anchor_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('anchor_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('waypoint_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('producer_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('promotion_status', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No public semantic anchors yet.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr><th>Anchor</th>'
        "<th>Type</th><th>Category</th><th>Waypoint</th>"
        "<th>Producer</th><th>Promotion</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )


def _runtime_observed_table(observed: list[dict[str, Any]]) -> str:
    rows = []
    for item in observed:
        evidence = item.get("visual_grounding_evidence") or {}
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('category', '')))}</td>"
            f"<td>{html.escape(str(item.get('state', '')))}</td>"
            f"<td>{html.escape(str(item.get('actionability', '')))}</td>"
            f"<td>{html.escape(str(item.get('producer_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('source_observation_id', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('reviewability_status', '')))}</td>"
            f"<td>{html.escape(str(evidence.get('image_bbox', '')))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p>No runtime observed objects yet.</p>"
    return (
        '<div class="table-wrap"><table><thead><tr><th>Handle</th>'
        "<th>Category</th><th>State</th><th>Actionability</th>"
        "<th>Producer</th><th>Observation</th><th>FPV reviewability</th>"
        "<th>FPV bbox</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def _target_candidates_section(
    target_candidates: list[dict[str, Any]],
    target_search: dict[str, Any],
) -> str:
    target_rows = []
    for item in target_candidates:
        budget = item.get("inspection_budget") or {}
        target_rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('candidate_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('candidate_type', '')))}</td>"
            f"<td>{html.escape(str(item.get('label', '')))}</td>"
            f"<td>{html.escape(str(item.get('waypoint_id', '')))}</td>"
            f"<td>{html.escape(str(item.get('target_actionability_status', '')))}</td>"
            f"<td>{html.escape(str(item.get('evidence_lane', '')))}</td>"
            f"<td>{html.escape(str(budget.get('observation_count', '')))}</td>"
            f"<td>{html.escape(str(budget.get('camera_adjustment_attempt_count', '')))}</td>"
            f"<td>{html.escape(str(item.get('rejection_reason', '')))}</td>"
            "</tr>"
        )
    target_table = (
        "<p>No target candidates yet.</p>"
        if not target_rows
        else (
            '<div class="table-wrap"><table><thead><tr><th>Candidate</th>'
            "<th>Type</th><th>Label</th><th>Waypoint</th><th>Actionability</th>"
            "<th>Lane</th><th>Observes</th><th>Camera adjusts</th><th>Reason</th>"
            "</tr></thead><tbody>" + "".join(target_rows) + "</tbody></table></div>"
        )
    )
    budget = target_search.get("viewpoint_budget") or {}
    camera_budget = target_search.get("camera_adjustment_budget") or {}
    return (
        "<h3>Target Candidates</h3>"
        f'<p class="note">Public target search budget: '
        f"{html.escape(str(budget.get('visited_waypoint_count', 0)))} visited / "
        f"{html.escape(str(budget.get('total_public_waypoints', 0)))} waypoints, "
        f"{html.escape(str(camera_budget.get('attempt_count', 0)))} camera adjustments. "
        f"{html.escape(str(target_search.get('missing_target_policy', '')))}</p>"
        f"{target_table}"
    )


def _cleanup_policy_event_row(item: dict[str, Any], has_review_fields: bool) -> str:
    review_cells = ""
    if has_review_fields:
        review_cells = (
            f"<td>{html.escape(str(item.get('decision', '')))}</td>"
            f"<td>{html.escape(str(item.get('progress', '')))}</td>"
            f"<td>{html.escape(str(item.get('reason', '')))}</td>"
        )
    return (
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


def _cleanup_policy_metrics(trace: dict[str, Any]) -> str:
    return (
        '<div class="metric-grid">'
        f"{_metric('Waypoint source', trace.get('waypoint_source', 'unknown'))}"
        f"{_metric('Loop style', trace.get('loop_style', 'unknown'))}"
        f"{_metric('Review kind', trace.get('agent_review_kind', 'n/a'))}"
        f"{_metric('Waypoint observes', trace.get('scan_observe_count', 0))}"
        f"{_metric('Cleanup actions', trace.get('cleanup_action_count', 0))}"
        f"{_metric('Post-place observes', trace.get('post_place_observe_count', 0))}"
        "</div>"
    )


def _cleanup_policy_badges(trace: dict[str, Any]) -> str:
    return "".join(
        (
            _badge(
                "First cleanup before full survey",
                trace.get("first_cleanup_before_full_survey", False),
            ),
            _badge("Post-place observe complete", trace.get("post_place_observe_complete", False)),
            _badge("Agent reasoning visible", trace.get("agent_reasoning_visible", False)),
        )
    )


def _real_robot_readiness_metrics(readiness: dict[str, Any]) -> str:
    nav_summary = ", ".join(
        f"{key}={value}"
        for key, value in (readiness.get("navigation_backend_summary") or {}).items()
    )
    pose_summary = ", ".join(
        f"{key}={value}" for key, value in (readiness.get("pose_source_summary") or {}).items()
    )
    return (
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


def _real_robot_readiness_badges(readiness: dict[str, Any]) -> str:
    return "".join(
        (
            _badge("Map shape", readiness.get("map_bundle_fields_present", False)),
            _badge("PoseStamped waypoints", readiness.get("pose_stamped_waypoints", False)),
            _badge("Static fixtures only", readiness.get("static_fixture_projection", False)),
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


def _real_robot_readiness_note(readiness: dict[str, Any]) -> str:
    if readiness.get("backend_variant") == "molmospaces_sim":
        return (
            "This section is a MolmoSpaces Agibot Contract Rehearsal. It validates "
            "household contract shape, Agibot-shaped stage sequencing, "
            "and simulated observe/navigation evidence. It is not physical Agibot "
            "GDK execution, not a real movement gate, and not manipulation proof."
        )
    if readiness.get("backend_variant") == "agibot_gdk":
        movement_flag = str(readiness.get("movement_enabled", False)).lower()
        return (
            "This section is an AgiBot Navigation + Perception Pilot. Roboclaws keeps "
            "the household public tool boundary while the AgiBot SDK runner "
            "owns GDK execution evidence and per-stage reports. Navigation is physical "
            "only when the session-level movement gate is enabled; "
            f"movement_enabled={movement_flag}, "
            "physical_cleanup_ready=false."
        )
    if readiness.get("physical_navigation_pilot"):
        physical_flags = (
            f"physical_navigation_pilot={str(readiness.get('physical_navigation_pilot')).lower()}, "
            f"physical_cleanup_ready={str(readiness.get('physical_cleanup_ready')).lower()}."
        )
        return (
            "This section is a physical Navigation + Perception Pilot. Nav2 waypoint "
            "navigation may execute, reached waypoints are observed, and physical "
            f"cleanup manipulation remains blocked_capability. {physical_flags}"
        )
    return (
        "This section checks contract shape, not live ROS/Nav2. Current simulator "
        "navigation is validated against a static Nav2-shaped costmap and still is "
        "not a physical nav2_action; chase imagery is labelled "
        "report_only_simulation_view and is not a policy input."
    )


def _requested_generated_text(private: dict[str, Any]) -> str:
    requested = private.get("requested_generated_mess_count")
    if requested is None:
        return ""
    return f" (requested {requested})"


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"

from __future__ import annotations

import html
from pathlib import Path
from typing import Any, Callable

from roboclaws.household import agent_view as agent_view_module


def molmospaces_agibot_rehearsal_section(
    run_dir: Path,
    run_result: dict[str, Any],
    *,
    metric: Callable[[str, Any], str],
    path_table: Callable[[list[tuple[str, Any]]], str],
    review_image: Callable[[Any, str], str],
) -> str:
    rehearsal = run_result.get("molmospaces_agibot_contract_rehearsal") or {}
    if not rehearsal:
        return ""
    scene = run_result.get("molmospaces_scene") or {}
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view_module.base_navigation_map(agent_view) if agent_view else {}
    static_fixtures = agent_view_module.static_map_fixtures(agent_view) if agent_view else []
    rooms = metric_map.get("rooms") or []
    waypoints = metric_map.get("inspection_waypoints") or []
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
        f"{metric('Runtime', runtime)}"
        f"{metric('Scenario', scene.get('scenario_id', run_result.get('scenario_id', 'unknown')))}"
        f"{metric('Scene source', scene.get('scene_source', 'unknown'))}"
        f"{metric('Map id', metric_map.get('map_id', 'unknown'))}"
        f"{metric('Rooms', len(rooms))}"
        f"{metric('Fixtures', len(static_fixtures))}"
        f"{metric('Waypoints', len(waypoints))}"
        f"{metric('Simulated', rehearsal.get('simulated', 'n/a'))}"
        "</div>"
    )
    preview = str(rehearsal.get("map_preview") or "")
    figure = (
        '<figure class="map-preview-figure">'
        f"{review_image(preview, 'MolmoSpaces metric map preview')}"
        "<figcaption>Agent-facing metric map projection: rooms, fixtures, and "
        "inspection waypoints used by the Agibot-shaped rehearsal.</figcaption>"
        "</figure>"
        if preview
        else ""
    )
    paths = path_table(
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


def agibot_sdk_runner_section(
    run_dir: Path,
    run_result: dict[str, Any],
    *,
    metric: Callable[[str, Any], str],
    artifact_link: Callable[[str, Path], str],
) -> str:
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
            f"<td>{artifact_link(report, run_dir)}</td>"
            f"<td>{artifact_link(run_result_path, run_dir)}</td>"
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
        f"{metric('Backend variant', runner.get('backend_variant', 'unknown'))}"
        f"{metric('Runtime', runner.get('runtime', 'n/a'))}"
        f"{metric('Simulated', runner.get('simulated', 'n/a'))}"
        f"{metric('Physical robot', runner.get('physical_robot', 'n/a'))}"
        f"{metric('Movement enabled', runner.get('real_movement_enabled', False))}"
        f"{metric('GDK imported by Roboclaws', gdk_imported)}"
        f"{metric('Sub-phase reports', len(runner.get('subphase_reports') or []))}"
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

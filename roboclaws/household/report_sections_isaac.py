from __future__ import annotations

import html
from collections.abc import Callable
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object

MetricRenderer = Callable[[str, Any], str]
ArtifactLinkRenderer = Callable[[str, Path], str]
YesNoRenderer = Callable[[Any], str]


def isaac_runtime_section(
    run_dir: Path,
    run_result: dict[str, Any],
    *,
    metric: MetricRenderer,
    artifact_link: ArtifactLinkRenderer,
    yes_no: YesNoRenderer,
) -> str:
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
        f"{metric('Runtime mode', runtime.get('runtime_mode', 'unknown'))}"
        f"{metric('Renderer', runtime.get('renderer_mode', 'unknown'))}"
        f"{metric('Rendering proof', rendering.get('status', 'unknown'))}"
        f"{metric('Scene load', scene_load.get('status', 'unknown'))}"
        f"{metric('Isaac Sim', runtime.get('isaac_sim_version') or 'unavailable')}"
        f"{metric('Isaac Lab', runtime.get('isaac_lab_version') or 'unavailable')}"
        f"{metric('CUDA', yes_no(runtime.get('cuda_available')))}"
        f"{metric('GPU', runtime.get('gpu_name') or 'n/a')}"
        f"{metric('Objects indexed', isaac.get('object_index_count', 0))}"
        f"{metric('Receptacles indexed', isaac.get('receptacle_index_count', 0))}"
        f"{metric('USD index', scene_index.get('status', 'unknown'))}"
        f"{metric('Scene index artifact', 'available' if scene_index_artifact else 'missing')}"
        f"{metric('Selected USD bindings', selected_binding_summary)}"
        f"{metric('Segmentation', segmentation.get('status', 'unknown'))}"
        f"{metric('Seg bboxes', segmentation.get('candidate_bbox_count', 0))}"
        f"{metric('Seg selected hits', segmentation.get('selected_usd_prim_match_count', 0))}"
        f"{metric('Snapshots', f'{real_snapshots}/{len(snapshots)} real')}"
        f"{metric('Semantic pose events', len(semantic_pose_events))}"
        f"{metric('Pose rendered to USD', yes_no(semantic_pose_state.get('rendered_to_usd')))}"
        f"{metric('Pose view capture', pose_view_capture_method)}"
        f"{metric('Pose render steps', pose_render_steps)}"
        f"{metric('Mapping gaps', len(mapping_gaps))}"
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
    scene_index_tables = _isaac_scene_index_artifact_tables(
        scene_index_artifact_payload,
        scene_bindings,
        metric=metric,
        yes_no=yes_no,
    )
    semantic_pose_tables = _isaac_semantic_pose_state_tables(
        semantic_pose_state,
        semantic_pose_events,
        yes_no=yes_no,
    )
    return (
        '<section class="panel isaac-runtime">'
        "<h2>Isaac Runtime Diagnostics</h2>"
        f'<p class="note">{html.escape(note)}</p>'
        f"{metrics}"
        f"<p><strong>Scene USD:</strong> {html.escape(str(isaac.get('scene_usd', '')))}</p>"
        f"<p><strong>Scene index artifact:</strong> "
        f"{artifact_link(scene_index_artifact, run_dir)}</p>"
        f"<p><strong>Scene load reason:</strong> "
        f"{html.escape(str(scene_load.get('reason', '')))}</p>"
        f"<p><strong>Rendering reason:</strong> "
        f"{html.escape(str(rendering.get('reason', '')))}</p>"
        f"<p><strong>Segmentation reason:</strong> "
        f"{html.escape(str(segmentation.get('reason', '')))}</p>"
        f"<p><strong>Semantic pose state:</strong> "
        f"{html.escape(str(semantic_pose_state.get('evidence_note', '')))}</p>"
        f"{mapping_list}"
        f"{scene_index_tables}"
        f"{semantic_pose_tables}"
        "</section>"
    )


def _load_isaac_scene_index_artifact(run_dir: Path, path: str) -> dict[str, Any]:
    resolved = _resolve_report_asset_path(run_dir, path)
    if resolved is None:
        return {}
    try:
        return read_json_object(resolved, label="Isaac scene index artifact")
    except (OSError, ValueError):
        return {}


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


def _isaac_scene_index_artifact_tables(
    artifact: dict[str, Any],
    fallback_scene_bindings: dict[str, Any],
    *,
    metric: MetricRenderer,
    yes_no: YesNoRenderer,
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
        f"{metric('Artifact schema', artifact.get('schema', 'unknown'))}"
        f"{metric('Agent-facing', yes_no(artifact.get('agent_facing')))}"
        f"{metric('Private manifest exposed', yes_no(private_manifest_exposed))}"
        f"{metric('Artifact objects', artifact.get('object_index_count', len(object_index)))}"
        f"{metric('Artifact receptacles', receptacle_count)}"
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
    *,
    yes_no: YesNoRenderer,
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
        f"{_isaac_semantic_object_pose_table(object_poses, yes_no=yes_no)}"
        f"{_isaac_semantic_articulation_table(articulations, yes_no=yes_no)}"
        "<h3>Semantic Pose Events</h3>"
        f"{_isaac_semantic_pose_event_table(semantic_pose_events, yes_no=yes_no)}"
    )


def _isaac_semantic_object_pose_table(
    object_poses: dict[str, Any],
    *,
    yes_no: YesNoRenderer,
) -> str:
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
            f"<td>{yes_no(pose.get('attached_to_robot'))}</td>"
            f"<td>{html.escape(str(pose.get('location_relation', '')))}</td>"
            f"<td>{yes_no(pose.get('rendered_to_usd'))}</td>"
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


def _isaac_semantic_articulation_table(
    articulations: dict[str, Any],
    *,
    yes_no: YesNoRenderer,
) -> str:
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
            f"<td>{yes_no(articulation.get('open'))}</td>"
            f"<td>{yes_no(articulation.get('rendered_to_usd'))}</td>"
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


def _isaac_semantic_pose_event_table(
    events: list[dict[str, Any]],
    *,
    yes_no: YesNoRenderer,
) -> str:
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
            f"<td>{yes_no(event.get('rendered_to_usd'))}</td>"
            f"<td>{yes_no(event.get('planner_backed'))}</td>"
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

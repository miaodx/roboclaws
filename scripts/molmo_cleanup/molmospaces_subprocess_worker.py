#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

import mujoco
from PIL import Image

from roboclaws.household.camera_control import (
    load_camera_control_request,
    normalize_camera_control_request,
)
from roboclaws.household.generated_mess import (
    generated_mess_success_threshold,
    select_generated_mess_targets,
    targets_from_generated_mess_manifest,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    annotate_focus_image as _annotate_focus_image_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    annotate_focus_visual_grounding as _annotate_focus_visual_grounding_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    camera_from_view_spec as _camera_from_view_spec_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    camera_vec3 as _camera_vec3_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    camera_view_spec as _camera_view_spec_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    default_average_position as _average_position_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    default_focus_camera_azimuth as _focus_camera_azimuth_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    default_focus_visibility_is_grounded as _focus_visibility_is_grounded_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    default_scene_focus_position as _scene_focus_position_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    default_visual_grounding_status as _visual_grounding_status_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    eye_from_mujoco_free_camera as _eye_from_mujoco_free_camera_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    focus_camera as _focus_camera_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    focus_payload as _focus_payload_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    focus_receptacle_can_hide_contents as _focus_receptacle_can_hide_contents_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    free_camera_from_lookat_spec as _free_camera_from_lookat_spec_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    lane_camera_orbit as _lane_camera_orbit_impl,
)
from scripts.molmo_cleanup.molmospaces_focus_camera import (
    should_use_fpv_as_verify_focus as _should_use_fpv_as_verify_focus_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    MolmoPlacementHooks,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    aabb_xy_overlaps as _aabb_xy_overlaps_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    candidate_has_direct_support as _candidate_has_direct_support_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    candidate_is_clear_of_dynamic_objects as _candidate_is_clear_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    direct_support_clearance as _direct_support_clearance_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    direct_support_placement as _direct_support_placement_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    elevated_position_over_surface as _elevated_position_over_surface_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    geom_has_upward_support_normal as _geom_has_upward_support_normal_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    geom_world_half_extents as _geom_world_half_extents_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    object_bottom_offset as _object_bottom_offset_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    object_footprint_half_extents as _object_footprint_half_extents_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    object_height as _object_height_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    object_surface_lift as _object_surface_lift_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    object_world_aabb as _object_world_aabb_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    oriented_half_extents as _oriented_half_extents_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    placement_diagnostic as _placement_diagnostic_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    placement_position as _placement_position_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    receptacle_is_open_container as _receptacle_is_open_container_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    receptacle_prefers_inside as _receptacle_prefers_inside_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    receptacle_requires_open as _receptacle_requires_open_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    receptacle_support_surfaces as _receptacle_support_surfaces_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    receptacle_text as _receptacle_text_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    resolve_placement as _resolve_placement_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    support_surface_from_geom as _support_surface_from_geom_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    support_top_z as _support_top_z_impl,
)
from scripts.molmo_cleanup.molmospaces_placement import (
    surface_candidate_positions as _surface_candidate_positions_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    angle_delta_value as _angle_delta_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    first_same_room_point as _first_same_room_point_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    outline_clearance as _outline_clearance_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    point_inside_outline as _point_inside_outline_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_head_pitch_for_target_value as _robot_head_pitch_for_target_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_pose_for_open_receptacle as _robot_pose_for_open_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_pose_for_waypoint as _robot_pose_for_waypoint_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_pose_near_object as _robot_pose_near_object_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_pose_near_position as _robot_pose_near_position_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_pose_near_receptacle as _robot_pose_near_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    robot_stand_off_for_target as _robot_stand_off_for_target_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    room_for_state_point as _room_for_point_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    room_outline_center_xy as _room_outline_center_xy_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    room_outline_for_id as _room_outline_for_id_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    room_relation_payload as _room_relation_payload_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    scene_center as _scene_center_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    target_room_id_for_receptacle as _target_room_id_impl,
)
from scripts.molmo_cleanup.molmospaces_robot_pose import (
    waypoint_target_position as _waypoint_target_position_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    collect_room_outlines as _collect_room_outlines_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    fallback_room_outlines as _fallback_room_outlines_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    geom_xy_bounds as _geom_xy_bounds_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    item_label as _item_label_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    map_bounds as _map_bounds_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    map_points as _map_points_impl,
)
from scripts.molmo_cleanup.molmospaces_room_map import (
    render_robot_map as _render_robot_map_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_cli import build_arg_parser
from scripts.molmo_cleanup.molmospaces_worker_init import (
    load_generated_mess_manifest as _load_generated_mess_manifest_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    normalize_molmospaces_scene_ref_path as _normalize_molmospaces_scene_ref_path_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    prepare_molmospaces_scene as _prepare_molmospaces_scene_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    resolve_molmospaces_scene_xml as _resolve_molmospaces_scene_xml_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    scenario_id as _scenario_id_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    scene_ref_candidate_xml_path as _scene_ref_candidate_xml_path_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_init import (
    scene_xml_path_from_ref as _scene_xml_path_from_ref_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    MolmoWorkerOutputHooks,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    camera_request_provenance as _camera_request_provenance_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    camera_request_variant as _camera_request_variant_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    render_camera_views_with_model_data as _render_camera_views_with_model_data_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    robot_view_camera_adjustment as _robot_view_camera_adjustment_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    write_camera_views as _write_camera_views_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    write_robot_views as _write_robot_views_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_outputs import (
    write_snapshot as _write_snapshot_impl,
)

BACKEND = "molmospaces_subprocess"
API_SEMANTIC_PROVENANCE = "api_semantic"
HELD_LOCATION_ID = "held_by_agent"
DEFAULT_RENDER_WIDTH = 540
DEFAULT_RENDER_HEIGHT = 360
_MODEL_DATA_CACHE: dict[tuple[str, str], tuple[mujoco.MjModel, mujoco.MjData]] = {}
_STATE_MUTATING_COMMANDS = {
    "observe",
    "navigate_to_object",
    "navigate_to_waypoint",
    "navigate_to_receptacle",
    "frame_comparison_object",
    "pick",
    "open_receptacle",
    "close_receptacle",
    "place",
    "place_inside",
}
type _WorkerCommandHandler = Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]]


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.command == "serve":
        serve(args.state_path)
        return
    if args.command == "init":
        result = _init_command(args)
    else:
        result = _run_worker_command(args.state_path, args.command, _cli_command_kwargs(args))
    print(json.dumps(result, sort_keys=True))


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    return build_arg_parser(
        default_render_width=DEFAULT_RENDER_WIDTH,
        default_render_height=DEFAULT_RENDER_HEIGHT,
    ).parse_args(argv)


def _init_command(args: argparse.Namespace) -> dict[str, Any]:
    return init_state(
        state_path=args.state_path,
        seed=args.seed,
        scene_source=args.scene_source,
        scene_index=args.scene_index,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        generated_mess_count=args.generated_mess_count,
        generated_mess_object_ids=tuple(args.generated_mess_object_id or ()),
        generated_mess_manifest_path=args.generated_mess_manifest_path,
    )


def serve(state_path: Path) -> None:
    """Serve JSON-line worker requests while keeping MuJoCo state warm."""
    print(json.dumps({"ok": True, "event": "ready", "tool": "serve"}, sort_keys=True), flush=True)
    for line in sys.stdin:
        if not line.strip():
            continue
        request: Any = {}
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            request_id = request.get("id")
            command = str(request.get("command") or "")
            kwargs = request.get("kwargs") or {}
            if not isinstance(kwargs, dict):
                raise ValueError("request kwargs must be a JSON object")
            if command == "shutdown":
                response = {
                    "id": request_id,
                    "ok": True,
                    "result": _ok("shutdown"),
                }
                print(json.dumps(response, sort_keys=True), flush=True)
                break
            result = run_state_command(state_path, command, kwargs)
            response = {"id": request_id, "ok": True, "result": result}
        except Exception as exc:
            response = {
                "id": request.get("id") if isinstance(request, dict) else None,
                "ok": False,
                "error_type": type(exc).__name__,
                "error": str(exc),
            }
        print(json.dumps(response, sort_keys=True), flush=True)


def run_state_command(
    state_path: Path,
    command: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    return _run_worker_command(state_path, command, kwargs)


def _run_worker_command(
    state_path: Path,
    command: str,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    state = _read_state(state_path)
    result, should_write = _run_loaded_state_command(state, command, kwargs)
    if should_write:
        _write_state(state_path, state)
    return result


def _run_loaded_state_command(
    state: dict[str, Any],
    command: str,
    kwargs: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    handler = _WORKER_COMMAND_HANDLERS.get(command)
    if handler is None:
        raise ValueError(f"unknown MolmoSpaces worker command: {command!r}")
    return handler(state, kwargs), command in _STATE_MUTATING_COMMANDS


def _cli_command_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    command = str(args.command)
    if command == "snapshot":
        return {
            "output_path": args.output_path,
            "title": args.title,
            "render_width": args.render_width,
            "render_height": args.render_height,
        }
    if command == "robot_views":
        return {
            "output_dir": args.output_dir,
            "label": args.label,
            "focus_object_id": args.focus_object_id,
            "focus_receptacle_id": args.focus_receptacle_id,
            "camera_yaw_offset_deg": args.camera_yaw_offset_deg,
            "camera_pitch_offset_deg": args.camera_pitch_offset_deg,
            "render_width": args.render_width,
            "render_height": args.render_height,
        }
    if command == "camera_views":
        return {
            "output_dir": args.output_dir,
            "view_specs_path": args.view_specs_path,
            "camera_request_path": args.camera_request_path,
            "render_width": args.render_width,
            "render_height": args.render_height,
        }
    if command in {"navigate_to_object", "frame_comparison_object", "pick"}:
        return {"object_id": args.object_id}
    if command == "navigate_to_waypoint":
        return {"waypoint_json": args.waypoint_json}
    if command in {
        "navigate_to_receptacle",
        "open_receptacle",
        "close_receptacle",
        "place",
        "place_inside",
    }:
        return {"receptacle_id": args.receptacle_id}
    if command == "done":
        return {"reason": args.reason}
    return {}


def _snapshot_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return write_snapshot(
        state,
        Path(str(kwargs["output_path"])),
        str(kwargs.get("title") or ""),
        width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
        height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
    )


def _robot_views_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return write_robot_views(
        state,
        Path(str(kwargs["output_dir"])),
        str(kwargs["label"]),
        focus_object_id=_optional_str(kwargs.get("focus_object_id")),
        focus_receptacle_id=_optional_str(kwargs.get("focus_receptacle_id")),
        camera_yaw_offset_deg=_float_or_zero(kwargs.get("camera_yaw_offset_deg")),
        camera_pitch_offset_deg=_float_or_zero(kwargs.get("camera_pitch_offset_deg")),
        width=_positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH),
        height=_positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT),
    )


def _camera_views_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    width = _positive_int(kwargs.get("render_width"), DEFAULT_RENDER_WIDTH)
    height = _positive_int(kwargs.get("render_height"), DEFAULT_RENDER_HEIGHT)
    camera_request = _load_camera_request_from_kwargs(kwargs, width=width, height=height)
    return write_camera_views(
        state,
        Path(str(kwargs["output_dir"])),
        camera_request,
        width=width,
        height=height,
    )


def _observe_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    del kwargs
    return observe(state)


def _locations_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    del kwargs
    return _ok("locations", final_locations=_read_locations(state))


def _navigate_to_object_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return navigate_to_object(state, str(kwargs["object_id"]))


def _navigate_to_waypoint_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return navigate_to_waypoint(state, _json_object_from_text(str(kwargs["waypoint_json"])))


def _navigate_to_receptacle_command(
    state: dict[str, Any],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    return navigate_to_receptacle(state, str(kwargs["receptacle_id"]))


def _frame_comparison_object_command(
    state: dict[str, Any],
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    return frame_comparison_object(state, str(kwargs["object_id"]))


def _pick_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return pick_object(state, str(kwargs["object_id"]))


def _open_receptacle_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return open_receptacle(state, str(kwargs["receptacle_id"]))


def _close_receptacle_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return close_receptacle(state, str(kwargs["receptacle_id"]))


def _place_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return place_object(state, str(kwargs["receptacle_id"]))


def _place_inside_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return place_inside_object(state, str(kwargs["receptacle_id"]))


def _done_command(state: dict[str, Any], kwargs: dict[str, Any]) -> dict[str, Any]:
    return done_cleanup(state, str(kwargs.get("reason") or ""))


_WORKER_COMMAND_HANDLERS: dict[str, _WorkerCommandHandler] = {
    "observe": _observe_command,
    "locations": _locations_command,
    "snapshot": _snapshot_command,
    "robot_views": _robot_views_command,
    "camera_views": _camera_views_command,
    "navigate_to_object": _navigate_to_object_command,
    "navigate_to_waypoint": _navigate_to_waypoint_command,
    "navigate_to_receptacle": _navigate_to_receptacle_command,
    "frame_comparison_object": _frame_comparison_object_command,
    "pick": _pick_command,
    "open_receptacle": _open_receptacle_command,
    "close_receptacle": _close_receptacle_command,
    "place": _place_command,
    "place_inside": _place_inside_command,
    "done": _done_command,
}


def _load_generated_mess_manifest(path: Path | None) -> dict[str, Any]:
    return _load_generated_mess_manifest_impl(path)


def init_state(
    *,
    state_path: Path,
    seed: int,
    scene_source: str,
    scene_index: int,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    generated_mess_count: int = 5,
    generated_mess_object_ids: tuple[str, ...] = (),
    generated_mess_manifest_path: Path | None = None,
) -> dict[str, Any]:
    from molmo_spaces.molmo_spaces_constants import get_robot_path, get_scenes, get_scenes_root
    from molmo_spaces.utils.lazy_loading_utils import (
        install_scene_with_objects_and_grasps_from_path,
    )
    from molmo_spaces.utils.scene_metadata_utils import get_scene_metadata

    scene_xml, scene_resolution = _prepare_molmospaces_scene(
        scene_source=scene_source,
        scene_index=scene_index,
        get_scenes=get_scenes,
        get_scenes_root=get_scenes_root,
        install_scene_with_objects_and_grasps_from_path=(
            install_scene_with_objects_and_grasps_from_path
        ),
    )
    if not scene_xml.is_file():
        raise FileNotFoundError(scene_xml)

    robot_xml: Path | None = None
    if include_robot:
        robot_xml = get_robot_path(robot_name) / _robot_xml_name(robot_name)
        if not robot_xml.is_file():
            raise FileNotFoundError(robot_xml)
        model, data = _load_robot_model_data(scene_xml, robot_xml)
    else:
        model, data = _load_model_data(scene_xml)
    metadata = get_scene_metadata(scene_xml)
    if metadata is None:
        raise RuntimeError(f"missing scene metadata for {scene_xml}")

    receptacles = _collect_receptacles(model, data, metadata)
    objects = _collect_dynamic_objects(model, data, metadata)
    if generated_mess_count < 0:
        raise ValueError("generated_mess_count must be >= 0")
    generated_mess_manifest = _load_generated_mess_manifest(generated_mess_manifest_path)
    if generated_mess_manifest:
        targets = targets_from_generated_mess_manifest(
            objects,
            receptacles,
            generated_mess_manifest,
            target_count=generated_mess_count,
        )
    elif generated_mess_count > 0:
        targets = select_generated_mess_targets(
            objects,
            receptacles,
            target_count=generated_mess_count,
            seed=seed,
            object_ids=generated_mess_object_ids or None,
        )
    else:
        targets = []
    if len(targets) < generated_mess_count:
        raise RuntimeError(
            f"expected at least {generated_mess_count} cleanup targets, found {len(targets)}"
        )

    state = {
        "backend": BACKEND,
        "seed": seed,
        "scene_source": scene_source,
        "scene_index": scene_index,
        "scene_xml": str(scene_xml),
        "scene_resolution": scene_resolution,
        "robot_included": include_robot,
        "robot_name": robot_name if include_robot else None,
        "robot_xml": str(robot_xml) if robot_xml is not None else None,
        "python_executable": sys.executable,
        "runtime": {
            "python_version": sys.version.split()[0],
            "mujoco_version": mujoco.__version__,
            "mujoco_renderer_runtime": "standard-mujoco",
        },
        "model_stats": {
            "nbody": int(model.nbody),
            "ngeom": int(model.ngeom),
            "njnt": int(model.njnt),
            "nq": int(model.nq),
        },
        "metadata_object_count": len(metadata.get("objects", {})),
        "objects": {item["object_id"]: item for item in objects},
        "receptacles": {item["receptacle_id"]: item for item in receptacles},
        "selected_object_ids": [target["object_id"] for target in targets],
        "generated_mess_manifest": generated_mess_manifest,
        "requested_generated_mess_count": generated_mess_count,
        "generated_mess_count": len(targets),
        "qpos": [float(value) for value in data.qpos],
        "held_object_id": None,
        "current_receptacle_id": None,
        "open_receptacle_ids": [],
        "mess_placement_diagnostics": [],
        "placement_diagnostics": [],
        "tool_event_counts": {},
    }
    _seed_misplaced_objects(model, data, state, targets)
    _refresh_object_positions(model, data, state)
    state["room_outlines"] = _collect_room_outlines(model, data, state)
    if include_robot and targets:
        initial_receptacle = state["receptacles"][_target_start_receptacle_id(state, targets[0])]
        robot_pose = _robot_pose_near_receptacle(state, initial_receptacle)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state["robot_trajectory"] = [robot_pose]
        state["robot_camera_names"] = _robot_camera_names(model)
        state["robot_body_name"] = "robot_0/base"
        state["robot_control_provenance"] = "semantic_robot_base_and_head_qpos"
        state["robot_view_provenance"] = {
            "fpv": "rby1m_head_camera_target_framed",
            "chase": "rby1m_follower_camera",
            "map": "public_sim_state_report",
            "verify": "public_sim_state_report_focus_camera",
        }
    state["qpos"] = [float(value) for value in data.qpos]
    state["current_receptacle_id"] = (
        _target_start_receptacle_id(state, targets[0]) if targets else _first_receptacle_id(state)
    )
    state["private_manifest"] = {
        "scenario_id": _scenario_id(scene_source=scene_source, scene_index=scene_index, seed=seed),
        "success_threshold": generated_mess_success_threshold(len(targets)),
        "targets": [
            {
                "object_id": target["object_id"],
                "valid_receptacle_ids": [target["target_receptacle_id"]],
            }
            for target in targets
        ],
    }
    state["scenario_public"] = _public_scenario(state)
    _write_state(state_path, state)
    return _ok(
        "init",
        backend=BACKEND,
        scenario=state["scenario_public"],
        private_manifest=state["private_manifest"],
        generated_mess_manifest=state.get("generated_mess_manifest") or None,
        requested_generated_mess_count=state["requested_generated_mess_count"],
        generated_mess_count=state["generated_mess_count"],
        scene_xml=state["scene_xml"],
        scene_resolution=state["scene_resolution"],
        runtime=state["runtime"],
        model_stats=state["model_stats"],
        metadata_object_count=state["metadata_object_count"],
        robot=_robot_result_payload(state, model) if include_robot else None,
    )


def observe(state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "observe")
    state["scenario_public"] = _public_scenario(state)
    return _ok(
        "observe",
        backend=BACKEND,
        scenario=state["scenario_public"],
        current_receptacle_id=state.get("current_receptacle_id"),
        held_object_id=state.get("held_object_id"),
        inventory_source="molmospaces_metadata+mujoco_state",
        metadata_object_count=state["metadata_object_count"],
    )


def _prepare_molmospaces_scene(
    *,
    scene_source: str,
    scene_index: int,
    get_scenes: Callable[..., Any],
    get_scenes_root: Callable[[], Any],
    install_scene_with_objects_and_grasps_from_path: Callable[[Path], Any],
) -> tuple[Path, dict[str, Any]]:
    return _prepare_molmospaces_scene_impl(
        scene_source=scene_source,
        scene_index=scene_index,
        get_scenes=get_scenes,
        get_scenes_root=get_scenes_root,
        install_scene_with_objects_and_grasps_from_path=(
            install_scene_with_objects_and_grasps_from_path
        ),
    )


def _resolve_molmospaces_scene_xml(
    *,
    scene_source: str,
    scene_index: int,
    get_scenes: Callable[..., Any],
    scenes_root: Path,
) -> tuple[Path, dict[str, Any]]:
    return _resolve_molmospaces_scene_xml_impl(
        scene_source=scene_source,
        scene_index=scene_index,
        get_scenes=get_scenes,
        scenes_root=scenes_root,
    )


def _scene_xml_path_from_ref(
    raw_ref: Any,
    *,
    scenes_root: Path,
) -> tuple[Path | None, str, bool]:
    return _scene_xml_path_from_ref_impl(raw_ref, scenes_root=scenes_root)


def _scene_ref_candidate_xml_path(
    raw_path: Any,
    *,
    scenes_root: Path,
) -> tuple[Path, bool] | None:
    return _scene_ref_candidate_xml_path_impl(raw_path, scenes_root=scenes_root)


def _normalize_molmospaces_scene_ref_path(
    raw_path: Any,
    *,
    scenes_root: Path,
) -> tuple[Path, bool]:
    return _normalize_molmospaces_scene_ref_path_impl(raw_path, scenes_root=scenes_root)


def _scenario_id(*, scene_source: str, scene_index: int, seed: int) -> str:
    return _scenario_id_impl(scene_source=scene_source, scene_index=scene_index, seed=seed)


def _molmo_worker_output_hooks() -> MolmoWorkerOutputHooks:
    return MolmoWorkerOutputHooks(
        apply_qpos=_apply_qpos,
        apply_robot_view_camera_offset=_apply_robot_view_camera_offset,
        annotate_focus_image=_annotate_focus_image,
        annotate_focus_visual_grounding=_annotate_focus_visual_grounding,
        camera_from_view_spec=_camera_from_view_spec,
        camera_request_provenance=_camera_request_provenance,
        camera_request_variant=_camera_request_variant,
        camera_view_spec=_camera_view_spec,
        count=_count,
        error=_error,
        fixed_camera_diagnostics=_fixed_camera_diagnostics,
        focus_camera=_focus_camera,
        focus_payload=_focus_payload,
        focus_visibility=_focus_visibility,
        free_camera_diagnostics=_free_camera_diagnostics,
        load_model_data_for_state=_load_model_data_for_state,
        ok=_ok,
        refresh_object_positions=_refresh_object_positions,
        render_camera_views_with_model_data=_render_camera_views_with_model_data,
        render_dimensions=_render_dimensions,
        render_fixed_camera=_render_fixed_camera,
        render_free_camera=_render_free_camera,
        render_robot_map=_render_robot_map,
        should_use_fpv_as_verify_focus=_should_use_fpv_as_verify_focus,
        backend=BACKEND,
    )


def write_snapshot(
    state: dict[str, Any],
    output_path: Path,
    title: str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    return _write_snapshot_impl(
        state,
        output_path,
        title,
        width=width,
        height=height,
        hooks=_molmo_worker_output_hooks(),
    )


def write_robot_views(
    state: dict[str, Any],
    output_dir: Path,
    label: str,
    *,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    return _write_robot_views_impl(
        state,
        output_dir,
        label,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
        camera_yaw_offset_deg=camera_yaw_offset_deg,
        camera_pitch_offset_deg=camera_pitch_offset_deg,
        width=width,
        height=height,
        hooks=_molmo_worker_output_hooks(),
    )


def _robot_view_camera_adjustment(
    *,
    camera_yaw_offset_deg: float = 0.0,
    camera_pitch_offset_deg: float = 0.0,
    applied_joints: list[str] | None = None,
    unavailable_reason: str | None = None,
) -> dict[str, Any]:
    return _robot_view_camera_adjustment_impl(
        camera_yaw_offset_deg=camera_yaw_offset_deg,
        camera_pitch_offset_deg=camera_pitch_offset_deg,
        applied_joints=applied_joints,
        unavailable_reason=unavailable_reason,
    )


def write_camera_views(
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> dict[str, Any]:
    return _write_camera_views_impl(
        state,
        output_dir,
        camera_request,
        width=width,
        height=height,
        hooks=_molmo_worker_output_hooks(),
    )


def _render_camera_views_with_model_data(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    state: dict[str, Any],
    output_dir: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    width: int,
    height: int,
) -> dict[str, Any]:
    return _render_camera_views_with_model_data_impl(
        model,
        data,
        state=state,
        output_dir=output_dir,
        camera_request=camera_request,
        width=width,
        height=height,
        hooks=_molmo_worker_output_hooks(),
    )


def navigate_to_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "navigate_to_receptacle")
    return _navigate_to_receptacle(state, receptacle_id, tool="navigate_to_receptacle")


def _navigate_to_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
) -> dict[str, Any]:
    if receptacle_id not in state["receptacles"]:
        return _error(tool, "stale_reference", receptacle_id=receptacle_id)
    previous = state.get("current_receptacle_id")
    state["current_receptacle_id"] = receptacle_id
    robot_pose = None
    held_object_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        robot_pose = _robot_pose_near_receptacle(state, state["receptacles"][receptacle_id])
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = _robot_pose_state_mutation(held_object_pose is not None)
    return _ok(
        tool,
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        previous_receptacle_id=previous,
        state_mutation=state_mutation,
        held_object_pose=held_object_pose,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def navigate_to_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "navigate_to_object")
    if object_id not in state["objects"]:
        return _error("navigate_to_object", "stale_reference", object_id=object_id)
    if state.get("held_object_id") == object_id:
        return _error("navigate_to_object", "object_already_held", object_id=object_id)
    locations = _read_locations(state)
    source_receptacle_id = locations.get(object_id)
    if not source_receptacle_id or source_receptacle_id == HELD_LOCATION_ID:
        return _error("navigate_to_object", "object_not_at_public_location", object_id=object_id)
    previous = state.get("current_receptacle_id")
    state["current_receptacle_id"] = source_receptacle_id
    robot_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        robot_pose = _robot_pose_near_object(
            state,
            state["objects"][object_id],
            source_receptacle_id=source_receptacle_id,
        )
        _set_robot_pose(model, data, robot_pose)
        mujoco.mj_forward(model, data)
        state["qpos"] = [float(value) for value in data.qpos]
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        qpos_changed = True
        state_mutation = "robot_base_qpos"
    return _ok(
        "navigate_to_object",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        source_receptacle_id=source_receptacle_id,
        previous_receptacle_id=previous,
        location_id=source_receptacle_id,
        state_mutation=state_mutation,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def navigate_to_waypoint(state: dict[str, Any], waypoint: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_waypoint")
    waypoint_id = str(waypoint.get("waypoint_id") or "")
    room_id = str(waypoint.get("room_id") or "")
    previous = state.get("current_waypoint_id")
    state["current_waypoint_id"] = waypoint_id
    robot_pose = None
    held_object_pose = None
    qpos_changed = False
    state_mutation = "agent_pose_semantic"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
        target = _waypoint_target_position(state, waypoint)
        robot_pose = _robot_pose_for_waypoint(state, waypoint, target)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = _robot_pose_state_mutation(held_object_pose is not None)
    return _ok(
        "navigate_to_waypoint",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        waypoint_id=waypoint_id,
        room_id=room_id,
        previous_waypoint_id=previous,
        state_mutation=state_mutation,
        held_object_pose=held_object_pose,
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def frame_comparison_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "frame_comparison_object")
    if object_id not in state["objects"]:
        return _error("frame_comparison_object", "stale_reference", object_id=object_id)
    if not state.get("robot_included"):
        return _error("frame_comparison_object", "robot_not_included")
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    robot_pose = _robot_pose_near_object(
        state,
        state["objects"][object_id],
        source_receptacle_id=None,
    )
    robot_pose["pose_source"] = "roboclaws_comparison_object_pose"
    _set_robot_pose(model, data, robot_pose)
    mujoco.mj_forward(model, data)
    state["qpos"] = [float(value) for value in data.qpos]
    state["robot_pose"] = robot_pose
    state.setdefault("robot_trajectory", []).append(robot_pose)
    return _ok(
        "frame_comparison_object",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        state_mutation="robot_base_qpos",
        robot_name=state.get("robot_name"),
        robot_pose=robot_pose,
        robot_control_provenance=state.get("robot_control_provenance"),
        qpos_changed=True,
        backend=BACKEND,
    )


def pick_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "pick")
    if object_id not in state["objects"]:
        return _error("pick", "stale_reference", object_id=object_id)
    if state.get("held_object_id") is not None:
        return _error("pick", "already_holding", held_object_id=state["held_object_id"])
    locations = _read_locations(state)
    qpos_changed = False
    state_mutation = "held_state_only"
    if state.get("robot_included"):
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        target_position = _held_object_position(state)
        _set_free_body_position(
            model, data, state["objects"][object_id]["body_name"], target_position
        )
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        state["qpos"] = [float(value) for value in data.qpos]
        qpos_changed = True
        state_mutation = "mujoco_freejoint_qpos_held_pose"
    state["held_object_id"] = object_id
    state["objects"][object_id]["contained_in"] = None
    state["objects"][object_id]["location_relation"] = "held"
    return _ok(
        "pick",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        previous_location_id=locations.get(object_id),
        location_id=HELD_LOCATION_ID,
        state_mutation=state_mutation,
        qpos_changed=qpos_changed,
        backend=BACKEND,
    )


def place_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "place")
    return _place_object_at_receptacle(state, receptacle_id, tool="place", relation="on")


def place_inside_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "place_inside")
    return _place_object_at_receptacle(
        state,
        receptacle_id,
        tool="place_inside",
        relation="inside",
    )


def _place_object_at_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
    relation: str,
) -> dict[str, Any]:
    if receptacle_id not in state["receptacles"]:
        return _error(tool, "stale_reference", receptacle_id=receptacle_id)
    object_id = state.get("held_object_id")
    if object_id is None:
        return _error(tool, "not_holding")
    receptacle = state["receptacles"][receptacle_id]
    if (
        relation == "inside"
        and _receptacle_requires_open(receptacle)
        and receptacle_id not in set(state.get("open_receptacle_ids", []))
    ):
        return _error(tool, "receptacle_closed", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    obj = state["objects"][object_id]
    placement_resolution = _resolve_placement(
        model,
        data,
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=state["selected_object_ids"].index(object_id),
        relation=relation,
    )
    target_position = placement_resolution["position"]
    _set_free_body_position(model, data, obj["body_name"], target_position)
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    diagnostic = _placement_diagnostic(
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        requested_position=target_position,
        source="cleanup_place",
        placement_resolution=placement_resolution,
    )
    state.setdefault("placement_diagnostics", []).append(diagnostic)

    state["qpos"] = [float(value) for value in data.qpos]
    state["held_object_id"] = None
    state["current_receptacle_id"] = receptacle_id
    state["objects"][object_id]["contained_in"] = receptacle_id if relation == "inside" else None
    state["objects"][object_id]["location_relation"] = relation
    final_locations = _read_locations(state)
    return _ok(
        tool,
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        receptacle_id=receptacle_id,
        location_id=final_locations.get(object_id),
        contained_in=receptacle_id if relation == "inside" else None,
        location_relation=relation,
        placement_diagnostic=diagnostic,
        placement_support_status=diagnostic["support_status"],
        mujoco_body_name=obj["body_name"],
        qpos_changed=True,
        state_mutation="mujoco_freejoint_qpos",
        backend=BACKEND,
    )


def open_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "open_receptacle")
    if receptacle_id not in state["receptacles"]:
        return _error("open_receptacle", "stale_reference", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    receptacle = state["receptacles"][receptacle_id]
    joints = _openable_receptacle_joints(model, receptacle["body_name"])
    for joint in joints:
        _set_joint_qpos(model, data, joint["joint_name"], joint["open_value"])
    robot_pose = None
    robot_pose_changed = False
    if state.get("robot_included") and joints:
        robot_pose = _robot_pose_for_open_receptacle(state, receptacle)
        _set_robot_pose(model, data, robot_pose)
        state["robot_pose"] = robot_pose
        state.setdefault("robot_trajectory", []).append(robot_pose)
        held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
        robot_pose_changed = True
    else:
        held_object_pose = None
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    state["qpos"] = [float(value) for value in data.qpos]
    open_ids = set(state.get("open_receptacle_ids", []))
    if joints:
        open_ids.add(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    return _ok(
        "open_receptacle",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        opened=bool(joints),
        open_joints=joints,
        robot_pose=robot_pose,
        held_object_pose=held_object_pose,
        qpos_changed=bool(joints) or robot_pose_changed,
        state_mutation=_open_receptacle_state_mutation(
            bool(joints),
            robot_pose_changed,
            held_object_pose is not None,
        ),
        backend=BACKEND,
    )


def close_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "close_receptacle")
    if receptacle_id not in state["receptacles"]:
        return _error("close_receptacle", "stale_reference", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    receptacle = state["receptacles"][receptacle_id]
    joints = _openable_receptacle_joints(model, receptacle["body_name"])
    closed_joints = []
    for joint in joints:
        _set_joint_qpos(model, data, joint["joint_name"], joint["close_value"])
        closed_joints.append(joint)
    held_object_pose = _sync_held_object_to_robot_pose(model, data, state)
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)
    state["qpos"] = [float(value) for value in data.qpos]
    open_ids = set(state.get("open_receptacle_ids", []))
    was_open = receptacle_id in open_ids
    open_ids.discard(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    return _ok(
        "close_receptacle",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        closed=was_open or bool(closed_joints),
        closed_joints=closed_joints,
        held_object_pose=held_object_pose,
        qpos_changed=bool(closed_joints) or held_object_pose is not None,
        state_mutation=_close_receptacle_state_mutation(
            bool(closed_joints),
            held_object_pose is not None,
        ),
        backend=BACKEND,
    )


def _robot_pose_state_mutation(held_object_changed: bool) -> str:
    parts = ["robot_base_qpos"]
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts)


def _open_receptacle_state_mutation(
    joints_changed: bool,
    robot_pose_changed: bool,
    held_object_changed: bool,
) -> str:
    parts = []
    if joints_changed:
        parts.append("mujoco_receptacle_joint_qpos")
    if robot_pose_changed:
        parts.append("robot_base_qpos")
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts) if parts else "no_openable_joint"


def _close_receptacle_state_mutation(
    joints_changed: bool,
    held_object_changed: bool,
) -> str:
    parts = []
    if joints_changed:
        parts.append("mujoco_receptacle_joint_qpos")
    if held_object_changed:
        parts.append("held_object_freejoint_qpos")
    return "+".join(parts) if parts else "no_openable_joint"


def done_cleanup(state: dict[str, Any], reason: str) -> dict[str, Any]:
    _count(state, "done")
    final_locations = _read_locations(state)
    score = _score(final_locations, state["private_manifest"])
    return _ok(
        "done",
        reason=reason,
        cleanup_status=score["status"],
        score=score,
        final_locations=final_locations,
        final_containment=_read_containment(state),
        tool_event_counts=state["tool_event_counts"],
        backend=BACKEND,
    )


def _collect_dynamic_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    items = []
    for name, info in metadata.get("objects", {}).items():
        body_name = _primary_body_name(info, fallback=name)
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0 or int(model.body_jntnum[body_id]) == 0:
            continue
        joint_id = int(model.body_jntadr[body_id])
        if int(model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_FREE):
            continue
        category = str(info.get("category", "Object"))
        items.append(
            {
                "object_id": name,
                "name": _friendly_name(category, info.get("object_id", name)),
                "category": category,
                "location_id": "",
                "pickupable": True,
                "body_name": body_name,
                "upstream_object_id": info.get("object_id", name),
                "position": _xyz(data.xpos[body_id]),
            }
        )
    return sorted(items, key=lambda item: (item["category"], item["object_id"]))


def _collect_receptacles(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    wanted = {
        "Sink",
        "ShelvingUnit",
        "Desk",
        "Fridge",
        "TVStand",
        "Bed",
        "Sofa",
        "DiningTable",
        "CounterTop",
    }
    items = []
    for name, info in metadata.get("objects", {}).items():
        category = str(info.get("category", ""))
        if category not in wanted:
            continue
        body_name = _primary_body_name(info, fallback=name)
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
        if body_id < 0:
            continue
        support_surfaces = _receptacle_support_surfaces(model, data, body_name)
        items.append(
            {
                "receptacle_id": name,
                "name": _friendly_name(category, info.get("object_id", name)),
                "category": category,
                "room_area": f"room_{info.get('room_id', 'unknown')}",
                "kind": "receptacle",
                "body_name": body_name,
                "upstream_object_id": info.get("object_id", name),
                "position": _xyz(data.xpos[body_id]),
                "support_surfaces": support_surfaces,
                "support_top_z": _support_top_z(support_surfaces),
            }
        )
    return sorted(items, key=lambda item: (item["category"], item["receptacle_id"]))


def _seed_misplaced_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    targets: list[dict[str, Any]],
) -> None:
    manifest_targets = _manifest_target_by_object_id(state)
    target_receptacle_ids = {
        _target_receptacle_id(target, manifest_targets.get(str(target["object_id"])))
        for target in targets
    }
    wrong_pool = [
        item
        for item in state["receptacles"].values()
        if item["receptacle_id"] not in target_receptacle_ids
        and not _receptacle_requires_open(item)
    ]
    if not wrong_pool:
        wrong_pool = [
            item
            for item in state["receptacles"].values()
            if item["receptacle_id"] not in target_receptacle_ids
        ]
    if not wrong_pool:
        wrong_pool = list(state["receptacles"].values())
    for index, target in enumerate(targets):
        manifest_target = manifest_targets.get(str(target["object_id"]))
        target_receptacle_id = _target_receptacle_id(target, manifest_target)
        placement_index = _target_placement_index(index, manifest_target)
        wrong = _target_start_receptacle(state, target, wrong_pool, index, manifest_target)
        state["objects"][target["object_id"]]["target_receptacle_id"] = target_receptacle_id
        state["objects"][target["object_id"]]["seeded_start_receptacle_id"] = wrong["receptacle_id"]
        relation = _target_relation(wrong, manifest_target)
        state["objects"][target["object_id"]]["contained_in"] = (
            wrong["receptacle_id"] if relation == "inside" else None
        )
        state["objects"][target["object_id"]]["location_relation"] = relation
        placement_resolution = _resolve_placement(
            model,
            data,
            state=state,
            object_id=target["object_id"],
            receptacle_id=wrong["receptacle_id"],
            index=placement_index,
            relation=relation,
        )
        placement_position = placement_resolution["position"]
        _set_free_body_position(
            model,
            data,
            target["body_name"],
            placement_position,
        )
        mujoco.mj_forward(model, data)
        _refresh_object_positions(model, data, state)
        diagnostic = _placement_diagnostic(
            state=state,
            object_id=target["object_id"],
            receptacle_id=wrong["receptacle_id"],
            relation=relation,
            requested_position=placement_position,
            source="canonical_mess_manifest" if manifest_target else "mess_seed",
            placement_index=placement_index,
            placement_resolution=placement_resolution,
        )
        state.setdefault("mess_placement_diagnostics", []).append(diagnostic)
    mujoco.mj_forward(model, data)


def _manifest_target_by_object_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = state.get("generated_mess_manifest")
    if not isinstance(manifest, dict):
        return {}
    targets: dict[str, dict[str, Any]] = {}
    for raw_target in manifest.get("targets", []):
        if not isinstance(raw_target, dict):
            continue
        object_id = str(raw_target.get("object_id") or "")
        if object_id:
            targets[object_id] = dict(raw_target)
    return targets


def _target_receptacle_id(
    target: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    if manifest_target:
        valid_ids = [
            str(item)
            for item in (
                manifest_target.get("valid_receptacle_ids")
                or [manifest_target.get("target_receptacle_id")]
            )
            if str(item)
        ]
        if valid_ids:
            return valid_ids[0]
    return str(target["target_receptacle_id"])


def _target_start_receptacle(
    state: dict[str, Any],
    target: dict[str, Any],
    wrong_pool: list[dict[str, Any]],
    index: int,
    manifest_target: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest_target:
        start_receptacle_id = str(manifest_target.get("start_receptacle_id") or "")
        if start_receptacle_id:
            receptacle = state["receptacles"].get(start_receptacle_id)
            if receptacle is None:
                raise ValueError(
                    "generated mess manifest start receptacle id is unavailable: "
                    f"{target['object_id']} -> {start_receptacle_id}"
                )
            return receptacle
    wrong = wrong_pool[index % len(wrong_pool)]
    if wrong["receptacle_id"] == target["target_receptacle_id"]:
        wrong = wrong_pool[(index + 1) % len(wrong_pool)]
    return wrong


def _target_start_receptacle_id(state: dict[str, Any], target: dict[str, Any]) -> str:
    manifest_target = _manifest_target_by_object_id(state).get(str(target["object_id"]))
    if manifest_target:
        start_receptacle_id = str(manifest_target.get("start_receptacle_id") or "")
        if start_receptacle_id:
            return start_receptacle_id
    return _first_wrong_receptacle(state, target)


def _target_relation(
    receptacle: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    if manifest_target:
        relation = str(manifest_target.get("relation") or "")
        if relation in {"on", "inside"}:
            return relation
    return "inside" if _receptacle_prefers_inside(receptacle) else "on"


def _target_placement_index(index: int, manifest_target: dict[str, Any] | None) -> int:
    if not manifest_target:
        return index
    try:
        return int(manifest_target.get("placement_index"))
    except (TypeError, ValueError):
        return index


def _public_scenario(state: dict[str, Any]) -> dict[str, Any]:
    locations = _read_locations(state)
    selected_ids = set(state["selected_object_ids"])
    selected = []
    distractors = []
    for obj in state["objects"].values():
        public = {
            "object_id": obj["object_id"],
            "name": obj["name"],
            "category": obj["category"],
            "location_id": locations.get(obj["object_id"], ""),
            "pickupable": obj.get("pickupable", True),
            "upstream_object_id": obj.get("upstream_object_id"),
            "contained_in": obj.get("contained_in"),
            "location_relation": obj.get("location_relation", "on"),
        }
        if obj["object_id"] in selected_ids:
            selected.append(public)
        elif obj["category"] not in {"Cup", "Mug", "Plate", "Bowl", "Book", "Apple"}:
            distractors.append(public)
    objects = selected + distractors[:8]
    return {
        "scenario_id": state["private_manifest"]["scenario_id"]
        if "private_manifest" in state
        else f"molmospaces-procthor-val-{state['scene_index']}-{state['seed']}",
        "task": "Clean up this real MolmoSpaces room by putting misplaced objects away.",
        "seed": state["seed"],
        "backend": BACKEND,
        "scene_source": state["scene_source"],
        "scene_index": state["scene_index"],
        "scene_xml": state["scene_xml"],
        "inventory_source": "molmospaces_metadata+mujoco_state",
        "metadata_object_count": state["metadata_object_count"],
        "objects": objects,
        "receptacles": [
            {
                "receptacle_id": item["receptacle_id"],
                "name": item["name"],
                "category": item["category"],
                "room_area": item["room_area"],
                "kind": item["kind"],
                "upstream_object_id": item["upstream_object_id"],
            }
            for item in state["receptacles"].values()
        ],
    }


def _read_locations(state: dict[str, Any]) -> dict[str, str]:
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    receptacles = list(state["receptacles"].values())
    locations = {}
    for object_id in state["selected_object_ids"]:
        if object_id == state.get("held_object_id"):
            locations[object_id] = HELD_LOCATION_ID
            continue
        obj = state["objects"][object_id]
        if obj.get("contained_in"):
            locations[object_id] = str(obj["contained_in"])
            continue
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, obj["body_name"])
        if body_id < 0:
            continue
        locations[object_id] = _nearest_receptacle(_xyz(data.xpos[body_id]), receptacles)
    return locations


def _read_containment(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    containment = {}
    for object_id in state.get("selected_object_ids", []):
        obj = state["objects"][object_id]
        if obj.get("contained_in") or obj.get("location_relation"):
            containment[object_id] = {
                "contained_in": obj.get("contained_in"),
                "location_relation": obj.get("location_relation", "on"),
            }
    return containment


def _score(final_locations: dict[str, str], manifest: dict[str, Any]) -> dict[str, Any]:
    restored = []
    missed = []
    object_results = []
    for target in manifest["targets"]:
        object_id = target["object_id"]
        actual = final_locations.get(object_id)
        is_restored = actual in set(target["valid_receptacle_ids"])
        if is_restored:
            restored.append(object_id)
        else:
            missed.append(object_id)
        object_results.append(
            {
                "object_id": object_id,
                "actual_location_id": actual,
                "restored": is_restored,
            }
        )
    status = (
        "success"
        if not manifest["targets"] or len(restored) >= manifest["success_threshold"]
        else "failed"
    )
    if status == "failed" and restored:
        status = "partial_success"
    return {
        "status": status,
        "restored_count": len(restored),
        "total_targets": len(manifest["targets"]),
        "success_threshold": manifest["success_threshold"],
        "restored_object_ids": restored,
        "missed_object_ids": missed,
        "object_results": object_results,
    }


def _nearest_receptacle(position: list[float], receptacles: list[dict[str, Any]]) -> str:
    return min(
        receptacles,
        key=lambda item: math.dist(position[:2], item["position"][:2]),
    )["receptacle_id"]


def _first_wrong_receptacle(state: dict[str, Any], target: dict[str, Any]) -> str:
    for receptacle_id in state["receptacles"]:
        if receptacle_id != target["target_receptacle_id"]:
            return receptacle_id
    return target["target_receptacle_id"]


def _first_receptacle_id(state: dict[str, Any]) -> str | None:
    first = next(iter(state["receptacles"].values()), None)
    if first is None:
        return None
    return str(first["receptacle_id"])


def _set_free_body_position(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    position: list[float],
) -> None:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        raise ValueError(f"unknown body: {body_name}")
    joint_id = int(model.body_jntadr[body_id])
    if joint_id < 0 or int(model.jnt_type[joint_id]) != int(mujoco.mjtJoint.mjJNT_FREE):
        raise ValueError(f"body does not have a free joint: {body_name}")
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr : qposadr + 3] = position


def _refresh_object_positions(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> None:
    for obj in state.get("objects", {}).values():
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, obj["body_name"])
        if body_id >= 0:
            obj["position"] = _xyz(data.xpos[body_id])


def _refresh_runtime_render_state(state: dict[str, Any]) -> None:
    try:
        model, data = _load_model_data_for_state(state)
        _apply_qpos(data, state["qpos"])
        mujoco.mj_forward(model, data)
    except Exception as exc:
        state["runtime_render_state"] = {
            "schema": "molmospaces_runtime_render_state_v1",
            "status": "unavailable",
            "unavailable_reason": f"{type(exc).__name__}: {exc}",
        }
        return
    state["runtime_render_state"] = _runtime_render_state(model, data, state)


def _runtime_render_state(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any]:
    objects = {}
    articulated_count = 0
    try:
        for object_id, obj in sorted((state.get("objects") or {}).items()):
            if not isinstance(obj, dict):
                continue
            body_name = str(obj.get("body_name") or "")
            body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
            if body_id < 0:
                continue
            joints = _runtime_subtree_joints(
                model,
                data,
                body_name,
                exclude_root_freejoint=True,
            )
            if joints:
                articulated_count += 1
            objects[str(object_id)] = {
                "object_key": str(object_id),
                "category": obj.get("category") or "",
                "body_name": body_name,
                "upstream_object_id": obj.get("upstream_object_id") or obj.get("object_id") or "",
                "position": _xyz(data.xpos[body_id]),
                "subtree_joint_count": len(joints),
                "articulation_status": "articulated" if joints else "rigid_or_free_body",
                "articulation_joints": joints,
            }
    except Exception as exc:
        return {
            "schema": "molmospaces_runtime_render_state_v1",
            "status": "unavailable",
            "unavailable_reason": f"{type(exc).__name__}: {exc}",
        }
    return {
        "schema": "molmospaces_runtime_render_state_v1",
        "status": "computed",
        "source": "mujoco_live_model_data_qpos",
        "qpos_length": len(state.get("qpos") or []),
        "object_count": len(objects),
        "articulated_object_count": articulated_count,
        "objects": objects,
    }


def _runtime_subtree_joints(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    *,
    exclude_root_freejoint: bool,
) -> list[dict[str, Any]]:
    root_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if root_body_id < 0:
        return []
    joints = []
    for body_id in _subtree_body_ids(model, body_name):
        joint_count = int(model.body_jntnum[body_id])
        if joint_count <= 0:
            continue
        body_joint_start = int(model.body_jntadr[body_id])
        for offset in range(joint_count):
            joint_id = body_joint_start + offset
            joint_type = int(model.jnt_type[joint_id])
            if (
                exclude_root_freejoint
                and body_id == root_body_id
                and offset == 0
                and joint_type == int(mujoco.mjtJoint.mjJNT_FREE)
            ):
                continue
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if not joint_name:
                continue
            qposadr = int(model.jnt_qposadr[joint_id])
            qpos_width = _joint_qpos_width(model, joint_id)
            joints.append(
                {
                    "joint_name": joint_name,
                    "body_name": mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_BODY, body_id) or "",
                    "joint_type": _joint_type_name(model, joint_id),
                    "qposadr": qposadr,
                    "qpos": [
                        round(float(value), 6)
                        for value in data.qpos[qposadr : qposadr + qpos_width]
                    ],
                    "range": [
                        round(float(model.jnt_range[joint_id][0]), 6),
                        round(float(model.jnt_range[joint_id][1]), 6),
                    ]
                    if bool(model.jnt_limited[joint_id])
                    else [],
                }
            )
    return joints


def _joint_qpos_width(model: mujoco.MjModel, joint_id: int) -> int:
    joint_type = int(model.jnt_type[joint_id])
    if joint_type == int(mujoco.mjtJoint.mjJNT_FREE):
        return 7
    if joint_type == int(mujoco.mjtJoint.mjJNT_BALL):
        return 4
    return 1


def _joint_type_name(model: mujoco.MjModel, joint_id: int) -> str:
    joint_type = int(model.jnt_type[joint_id])
    if joint_type == int(mujoco.mjtJoint.mjJNT_FREE):
        return "free"
    if joint_type == int(mujoco.mjtJoint.mjJNT_BALL):
        return "ball"
    if joint_type == int(mujoco.mjtJoint.mjJNT_SLIDE):
        return "slide"
    if joint_type == int(mujoco.mjtJoint.mjJNT_HINGE):
        return "hinge"
    return str(joint_type)


def _molmo_placement_hooks() -> MolmoPlacementHooks:
    return MolmoPlacementHooks(
        subtree_geom_ids=_subtree_geom_ids,
        xyz=_xyz,
    )


def _resolve_placement(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    state: dict[str, Any],
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
) -> dict[str, Any]:
    return _resolve_placement_impl(
        model,
        data,
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        relation=relation,
        hooks=_molmo_placement_hooks(),
    )


def _direct_support_placement(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    obj: dict[str, Any],
    receptacle: dict[str, Any],
    *,
    index: int,
) -> dict[str, Any] | None:
    return _direct_support_placement_impl(
        model,
        data,
        state,
        obj,
        receptacle,
        index=index,
        hooks=_molmo_placement_hooks(),
    )


def _surface_candidate_positions(
    surface: dict[str, Any],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
    clearance: float,
    index: int,
) -> list[list[float]]:
    return _surface_candidate_positions_impl(
        surface,
        footprint=footprint,
        bottom_offset=bottom_offset,
        clearance=clearance,
        index=index,
    )


def _candidate_has_direct_support(
    position: list[float],
    surface: dict[str, Any],
    footprint: tuple[float, float],
) -> bool:
    return _candidate_has_direct_support_impl(position, surface, footprint)


def _candidate_is_clear_of_dynamic_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    obj: dict[str, Any],
    position: list[float],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
) -> bool:
    return _candidate_is_clear_impl(
        model,
        data,
        state,
        obj,
        position,
        footprint=footprint,
        bottom_offset=bottom_offset,
        hooks=_molmo_placement_hooks(),
    )


def _elevated_position_over_surface(
    surface: dict[str, Any],
    *,
    bottom_offset: float,
) -> list[float]:
    return _elevated_position_over_surface_impl(surface, bottom_offset=bottom_offset)


def _placement_position(
    receptacle: dict[str, Any],
    *,
    index: int,
    relation: str = "on",
    object_category: str | None = None,
) -> list[float]:
    return _placement_position_impl(
        receptacle,
        index=index,
        relation=relation,
        object_category=object_category,
    )


def _object_surface_lift(object_category: str | None) -> float:
    return _object_surface_lift_impl(object_category)


def _direct_support_clearance(obj: dict[str, Any], receptacle: dict[str, Any]) -> float:
    return _direct_support_clearance_impl(obj, receptacle)


def _receptacle_support_surfaces(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
) -> list[dict[str, Any]]:
    return _receptacle_support_surfaces_impl(
        model,
        data,
        body_name,
        hooks=_molmo_placement_hooks(),
    )


def _support_surface_from_geom(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> dict[str, Any] | None:
    return _support_surface_from_geom_impl(
        model,
        data,
        geom_id,
        hooks=_molmo_placement_hooks(),
    )


def _geom_has_upward_support_normal(data: mujoco.MjData, geom_id: int) -> bool:
    return _geom_has_upward_support_normal_impl(data, geom_id)


def _geom_world_half_extents(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> tuple[float, float, float] | None:
    return _geom_world_half_extents_impl(model, data, geom_id)


def _oriented_half_extents(
    xmat: Any,
    local: tuple[float, float, float],
) -> tuple[float, float, float]:
    return _oriented_half_extents_impl(xmat, local)


def _support_top_z(surfaces: list[dict[str, Any]]) -> float | None:
    return _support_top_z_impl(surfaces)


def _object_bottom_offset(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> float:
    return _object_bottom_offset_impl(model, data, obj, hooks=_molmo_placement_hooks())


def _object_height(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> float:
    return _object_height_impl(model, data, obj, hooks=_molmo_placement_hooks())


def _object_world_aabb(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> dict[str, float] | None:
    return _object_world_aabb_impl(model, data, obj, hooks=_molmo_placement_hooks())


def _aabb_xy_overlaps(
    first: tuple[float, float, float, float],
    second: dict[str, float],
    *,
    margin: float,
) -> bool:
    return _aabb_xy_overlaps_impl(first, second, margin=margin)


def _object_footprint_half_extents(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    obj: dict[str, Any],
) -> tuple[float, float]:
    return _object_footprint_half_extents_impl(model, data, obj, hooks=_molmo_placement_hooks())


def _receptacle_requires_open(receptacle: dict[str, Any]) -> bool:
    return _receptacle_requires_open_impl(receptacle)


def _receptacle_prefers_inside(receptacle: dict[str, Any]) -> bool:
    return _receptacle_prefers_inside_impl(receptacle)


def _receptacle_is_open_container(receptacle: dict[str, Any]) -> bool:
    return _receptacle_is_open_container_impl(receptacle)


def _receptacle_text(receptacle: dict[str, Any]) -> str:
    return _receptacle_text_impl(receptacle)


def _placement_diagnostic(
    *,
    state: dict[str, Any],
    object_id: str,
    receptacle_id: str,
    relation: str,
    requested_position: list[float],
    source: str,
    placement_index: int | None = None,
    placement_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _placement_diagnostic_impl(
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        requested_position=requested_position,
        source=source,
        placement_index=placement_index,
        placement_resolution=placement_resolution,
    )


def _load_model_data(scene_xml: Path) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(scene_xml))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def _load_model_data_for_state(state: dict[str, Any]) -> tuple[mujoco.MjModel, mujoco.MjData]:
    scene_xml = str(state["scene_xml"])
    if state.get("robot_included"):
        robot_xml = state.get("robot_xml")
        if not robot_xml:
            raise ValueError("robot_included state missing robot_xml")
        cache_key = (scene_xml, str(robot_xml))
        cached = _MODEL_DATA_CACHE.get(cache_key)
        if cached is None:
            cached = _load_robot_model_data(Path(scene_xml), Path(robot_xml))
            _MODEL_DATA_CACHE[cache_key] = cached
        return cached
    cache_key = (scene_xml, "")
    cached = _MODEL_DATA_CACHE.get(cache_key)
    if cached is None:
        cached = _load_model_data(Path(scene_xml))
        _MODEL_DATA_CACHE[cache_key] = cached
    return cached


def _load_robot_model_data(
    scene_xml: Path,
    robot_xml: Path,
) -> tuple[mujoco.MjModel, mujoco.MjData]:
    xml_content = scene_xml.read_text(encoding="utf-8")
    mujoco_tag_end = xml_content.find(">") + 1
    include_line = f'\n  <include file="{robot_xml}"/>\n'
    modified_xml = xml_content[:mujoco_tag_end] + include_line + xml_content[mujoco_tag_end:]
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            suffix=".xml",
            prefix="roboclaws_robot_scene_",
            dir=str(scene_xml.parent),
            delete=False,
            encoding="utf-8",
        ) as temp:
            temp.write(modified_xml)
            temp_path = Path(temp.name)
        return _load_model_data(temp_path)
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)


def _robot_xml_name(robot_name: str) -> str:
    if robot_name == "rby1m":
        return "rby1_v1.2_site_control.xml"
    if robot_name == "rby1":
        return "rby1_site_control.xml"
    raise ValueError(f"unsupported robot for visual cleanup demo: {robot_name}")


def _robot_camera_names(model: mujoco.MjModel) -> list[str]:
    names = []
    for camera_id in range(model.ncam):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_CAMERA, camera_id)
        if name and name.startswith("robot_0/"):
            names.append(name)
    return names


def _robot_result_payload(state: dict[str, Any], model: mujoco.MjModel) -> dict[str, Any]:
    return {
        "robot_included": True,
        "robot_name": state.get("robot_name"),
        "robot_xml": state.get("robot_xml"),
        "robot_body_name": state.get("robot_body_name"),
        "robot_camera_names": state.get("robot_camera_names") or _robot_camera_names(model),
        "robot_control_provenance": state.get("robot_control_provenance"),
        "robot_view_provenance": state.get("robot_view_provenance"),
        "robot_pose": state.get("robot_pose"),
        "room_outline_count": len(state.get("room_outlines", [])),
        "robot_model_stats": {
            "nbody": int(model.nbody),
            "ngeom": int(model.ngeom),
            "njnt": int(model.njnt),
            "nq": int(model.nq),
            "nu": int(model.nu),
        },
    }


def _set_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    pose: dict[str, float],
) -> None:
    _set_joint_qpos(model, data, "robot_0/base_x", pose["x"])
    _set_joint_qpos(model, data, "robot_0/base_y", pose["y"])
    _set_joint_qpos(model, data, "robot_0/base_theta", pose["theta"])
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "robot_0/head_0") >= 0:
        _set_joint_qpos(model, data, "robot_0/head_0", float(pose.get("head_yaw", 0.0)))
    if mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, "robot_0/head_1") >= 0:
        _set_joint_qpos(model, data, "robot_0/head_1", float(pose.get("head_pitch", 0.0)))


def _apply_robot_view_camera_offset(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    yaw_offset_deg: float = 0.0,
    pitch_offset_deg: float = 0.0,
) -> dict[str, Any]:
    applied_joints: list[str] = []
    unavailable_reason = None
    if yaw_offset_deg:
        try:
            if _add_joint_qpos_if_present(
                model,
                data,
                "robot_0/head_0",
                math.radians(float(yaw_offset_deg)),
            ):
                applied_joints.append("robot_0/head_0")
        except TypeError as exc:
            unavailable_reason = f"{type(exc).__name__}: {exc}"
    if pitch_offset_deg:
        try:
            if _add_joint_qpos_if_present(
                model,
                data,
                "robot_0/head_1",
                math.radians(float(pitch_offset_deg)),
            ):
                applied_joints.append("robot_0/head_1")
        except TypeError as exc:
            unavailable_reason = f"{type(exc).__name__}: {exc}"
    return _robot_view_camera_adjustment(
        camera_yaw_offset_deg=yaw_offset_deg,
        camera_pitch_offset_deg=pitch_offset_deg,
        applied_joints=applied_joints,
        unavailable_reason=unavailable_reason,
    )


def _add_joint_qpos_if_present(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    delta: float,
) -> bool:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        return False
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr] = float(data.qpos[qposadr]) + float(delta)
    return True


def _set_joint_qpos(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    value: float,
) -> None:
    joint_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, joint_name)
    if joint_id < 0:
        raise ValueError(f"missing robot joint: {joint_name}")
    qposadr = int(model.jnt_qposadr[joint_id])
    data.qpos[qposadr] = float(value)


def _sync_held_object_to_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    object_id = state.get("held_object_id")
    if not object_id:
        return None
    obj = state["objects"].get(str(object_id))
    if obj is None:
        return None
    target_position = _held_object_position(state)
    _set_free_body_position(model, data, obj["body_name"], target_position)
    obj["position"] = target_position
    return {
        "object_id": object_id,
        "position": target_position,
        "position_source": "robot_relative_held_pose",
    }


def _held_object_position(state: dict[str, Any]) -> list[float]:
    pose = state.get("robot_pose") or {}
    if "x" not in pose or "y" not in pose or "theta" not in pose:
        return [0.0, 0.0, 1.0]
    theta = float(pose["theta"])
    distance_m = 0.8
    return [
        round(float(pose["x"]) + math.cos(theta) * distance_m, 6),
        round(float(pose["y"]) + math.sin(theta) * distance_m, 6),
        1.22,
    ]


def _openable_receptacle_joints(
    model: mujoco.MjModel,
    body_name: str,
) -> list[dict[str, Any]]:
    joints = []
    for body_id in _subtree_body_ids(model, body_name):
        joint_count = int(model.body_jntnum[body_id])
        if joint_count <= 0:
            continue
        for offset in range(joint_count):
            joint_id = int(model.body_jntadr[body_id]) + offset
            joint_type = int(model.jnt_type[joint_id])
            if joint_type not in {
                int(mujoco.mjtJoint.mjJNT_HINGE),
                int(mujoco.mjtJoint.mjJNT_SLIDE),
            }:
                continue
            joint_name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, joint_id)
            if not joint_name:
                continue
            open_value = float(model.jnt_range[joint_id][1])
            close_value = float(model.jnt_range[joint_id][0])
            joints.append(
                {
                    "joint_name": joint_name,
                    "joint_type": "hinge"
                    if joint_type == int(mujoco.mjtJoint.mjJNT_HINGE)
                    else "slide",
                    "open_value": round(open_value, 6),
                    "close_value": round(close_value, 6),
                }
            )
    return joints


def _robot_pose_near_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, Any]:
    return _robot_pose_near_receptacle_impl(state, receptacle)


def _robot_pose_for_open_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, Any]:
    return _robot_pose_for_open_receptacle_impl(state, receptacle)


def _first_same_room_point(
    state: dict[str, Any],
    candidates: list[tuple[float, float]],
    target_room_id: str | None,
) -> tuple[float, float]:
    return _first_same_room_point_impl(state, candidates, target_room_id)


def _robot_pose_near_object(
    state: dict[str, Any],
    obj: dict[str, Any],
    *,
    source_receptacle_id: str | None = None,
) -> dict[str, Any]:
    return _robot_pose_near_object_impl(
        state,
        obj,
        source_receptacle_id=source_receptacle_id,
    )


def _robot_pose_for_waypoint(
    state: dict[str, Any],
    waypoint: dict[str, Any],
    target: list[float],
) -> dict[str, Any]:
    return _robot_pose_for_waypoint_impl(state, waypoint, target)


def _waypoint_target_position(
    state: dict[str, Any],
    waypoint: dict[str, Any],
) -> list[float]:
    return _waypoint_target_position_impl(state, waypoint)


def _room_outline_center_xy(outline: dict[str, Any] | None) -> tuple[float, float] | None:
    return _room_outline_center_xy_impl(outline)


def _robot_pose_near_position(
    state: dict[str, Any],
    target: list[float],
    *,
    target_room_id: str | None,
    target_receptacle_id: str | None = None,
    target_object_id: str | None = None,
) -> dict[str, Any]:
    return _robot_pose_near_position_impl(
        state,
        target,
        target_room_id=target_room_id,
        target_receptacle_id=target_receptacle_id,
        target_object_id=target_object_id,
    )


def _robot_stand_off_for_target(state: dict[str, Any], target_object_id: str | None) -> float:
    return _robot_stand_off_for_target_impl(state, target_object_id)


def _robot_head_pitch_for_target(target: list[float], robot_xy: list[float]) -> float:
    return _robot_head_pitch_for_target_impl(target, robot_xy)


def _scene_center(items: list[dict[str, Any]]) -> tuple[float, float]:
    return _scene_center_impl(items)


def _render_fixed_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera_name)
    frame = renderer.render()
    renderer.close()
    return frame


def _fixed_camera_diagnostics(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
) -> dict[str, Any]:
    try:
        camera_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_CAMERA, camera_name)
        if camera_id < 0:
            return {
                "schema": "mujoco_fixed_camera_diagnostics_v1",
                "status": "missing_camera",
                "camera_name": camera_name,
            }
        world_position = _array_row(getattr(data, "cam_xpos"), camera_id, 3)
        world_xmat = _array_row(getattr(data, "cam_xmat"), camera_id, 9)
        return {
            "schema": "mujoco_fixed_camera_diagnostics_v1",
            "status": "ready",
            "camera_name": camera_name,
            "camera_id": int(camera_id),
            "camera_type": "fixed",
            "world_position": world_position,
            "world_xmat_rowmajor": world_xmat,
            "fovy_deg": _array_scalar(getattr(model, "cam_fovy", None), camera_id),
            "model_pos": _array_row(getattr(model, "cam_pos"), camera_id, 3),
            "model_quat_wxyz": _array_row(getattr(model, "cam_quat"), camera_id, 4),
            "znear": _optional_float(getattr(getattr(model, "vis", None), "map", None), "znear"),
            "zfar": _optional_float(getattr(getattr(model, "vis", None), "map", None), "zfar"),
        }
    except Exception as exc:
        return {
            "schema": "mujoco_fixed_camera_diagnostics_v1",
            "status": "unavailable",
            "camera_name": camera_name,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _free_camera_diagnostics(camera: mujoco.MjvCamera) -> dict[str, Any]:
    try:
        return {
            "schema": "mujoco_free_camera_diagnostics_v1",
            "status": "ready",
            "camera_type": "free",
            "lookat": [round(float(value), 6) for value in camera.lookat],
            "distance": round(float(camera.distance), 6),
            "azimuth": round(float(camera.azimuth), 6),
            "elevation": round(float(camera.elevation), 6),
        }
    except Exception as exc:
        return {
            "schema": "mujoco_free_camera_diagnostics_v1",
            "status": "unavailable",
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _array_row(array: Any, index: int, length: int) -> list[float]:
    return [round(float(value), 6) for value in array[index][:length]]


def _array_scalar(array: Any, index: int) -> float | None:
    if array is None:
        return None
    return round(float(array[index]), 6)


def _optional_float(parent: Any, attribute: str) -> float | None:
    if parent is None or not hasattr(parent, attribute):
        return None
    try:
        return round(float(getattr(parent, attribute)), 6)
    except (TypeError, ValueError):
        return None


def _focus_camera(state: dict[str, Any], focus: dict[str, Any]) -> mujoco.MjvCamera:
    return _focus_camera_impl(
        state,
        focus,
        scene_focus_position=_scene_focus_position,
        focus_camera_azimuth=_focus_camera_azimuth,
    )


def _render_free_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    return frame


def _load_rendered_robot_view_image(camera_views: dict[str, Any], *, role: str) -> Any:
    for item in camera_views.get("views") or []:
        if not isinstance(item, dict) or item.get("robot_view_role") != role:
            continue
        image_path = Path(str(item.get("image_path") or ""))
        if not image_path.is_file():
            raise RuntimeError(f"missing rendered {role} camera-control image: {image_path}")
        return _image_to_array(image_path)
    raise RuntimeError(f"missing rendered {role} camera-control view")


def _image_to_array(path: Path) -> Any:
    import numpy as np

    with Image.open(path) as image:
        return np.asarray(image.convert("RGB")).copy()


def _load_camera_view_specs(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_views = payload.get("views") if isinstance(payload, dict) else payload
    if not isinstance(raw_views, list):
        raise ValueError("camera view spec must be a list or an object with a views list")
    return [dict(item) for item in raw_views if isinstance(item, dict)]


def _load_camera_request_from_args(
    *,
    view_specs_path: Path | None,
    camera_request_path: Path | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    if camera_request_path is not None:
        return load_camera_control_request(camera_request_path, width=width, height=height)
    if view_specs_path is not None:
        return normalize_camera_control_request(
            _load_camera_view_specs(view_specs_path),
            width=width,
            height=height,
        )
    raise ValueError("camera_views requires --camera-request-path or --view-specs-path")


def _load_camera_request_from_kwargs(
    kwargs: dict[str, Any],
    *,
    width: int,
    height: int,
) -> dict[str, Any]:
    camera_request_path = kwargs.get("camera_request_path")
    if camera_request_path:
        return load_camera_control_request(
            Path(str(camera_request_path)), width=width, height=height
        )
    view_specs_path = kwargs.get("view_specs_path")
    if view_specs_path:
        return normalize_camera_control_request(
            _load_camera_view_specs(Path(str(view_specs_path))),
            width=width,
            height=height,
        )
    raise ValueError("camera_views requires camera_request_path or view_specs_path")


def _camera_view_spec(raw_spec: dict[str, Any], *, index: int) -> dict[str, Any]:
    return _camera_view_spec_impl(raw_spec, index=index)


def _lane_camera_orbit(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    return _lane_camera_orbit_impl(raw_spec, lane_id)


def _camera_request_variant(camera_request: dict[str, Any]) -> str:
    return _camera_request_variant_impl(camera_request)


def _camera_request_provenance(camera_request: dict[str, Any]) -> str:
    return _camera_request_provenance_impl(camera_request)


def _camera_vec3(value: Any, *, default: list[float]) -> list[float]:
    return _camera_vec3_impl(value, default=default)


def _eye_from_mujoco_free_camera(
    *,
    lookat: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> list[float]:
    return _eye_from_mujoco_free_camera_impl(
        lookat=lookat,
        distance=distance,
        azimuth=azimuth,
        elevation=elevation,
    )


def _free_camera_from_lookat_spec(spec: dict[str, Any]) -> mujoco.MjvCamera:
    return _free_camera_from_lookat_spec_impl(spec)


def _camera_from_view_spec(state: dict[str, Any], spec: dict[str, Any]) -> mujoco.MjvCamera:
    return _camera_from_view_spec_impl(
        state,
        spec,
        free_camera_from_lookat_spec=_free_camera_from_lookat_spec,
        focus_payload=_focus_payload,
        focus_camera=_focus_camera,
    )


def _annotate_focus_image(image: Image.Image, focus: dict[str, Any]) -> None:
    _annotate_focus_image_impl(image, focus)


def _focus_camera_azimuth(
    state: dict[str, Any],
    focus_position: list[float],
    focus: dict[str, Any] | None = None,
) -> float:
    return _focus_camera_azimuth_impl(state, focus_position, focus)


def _focus_payload(
    state: dict[str, Any],
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    return _focus_payload_impl(
        state,
        focus_object_id,
        focus_receptacle_id,
        label_item=_item_label,
        average_position=_average_position,
        scene_focus_position=_scene_focus_position,
    )


def _average_position(positions: list[list[float]]) -> list[float]:
    return _average_position_impl(positions)


def _scene_focus_position(state: dict[str, Any]) -> list[float]:
    return _scene_focus_position_impl(state)


def _item_label(item: dict[str, Any] | None, id_key: str) -> str:
    return _item_label_impl(item, id_key)


def _focus_visibility(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    focus: dict[str, Any],
    *,
    frame: Any | None = None,
) -> dict[str, Any]:
    boxes = []
    object_pixels = 0
    receptacle_pixels = 0
    try:
        render_shape = frame.shape if frame is not None and hasattr(frame, "shape") else None
        segmentation = _render_segmentation(
            model,
            data,
            camera,
            width=_shape_width(render_shape),
            height=_shape_height(render_shape),
        )
    except Exception as exc:  # pragma: no cover - depends on MuJoCo renderer internals
        return {
            "status": "segmentation_unavailable",
            "error": type(exc).__name__,
            "object_pixels": 0,
            "receptacle_pixels": 0,
            "boxes": [],
        }
    if focus.get("object_body_name"):
        box = _segmentation_box(
            model,
            segmentation,
            focus["object_body_name"],
            label=str(focus.get("object_label") or "object"),
            color=[239, 68, 68],
        )
        if focus.get("object_category") == "RemoteControl" and (
            box is None or int(box.get("pixels") or 0) < 20
        ):
            highlight_box = _highlight_diff_box(
                model,
                data,
                camera,
                focus["object_body_name"],
                label=str(focus.get("object_label") or "object"),
                color=[239, 68, 68],
                frame=frame,
            )
            if highlight_box is not None and (
                box is None or int(highlight_box.get("pixels") or 0) > int(box.get("pixels") or 0)
            ):
                box = highlight_box
        if box is not None:
            object_pixels = int(box["pixels"])
            boxes.append(box)
    if focus.get("receptacle_body_name"):
        box = _segmentation_box(
            model,
            segmentation,
            focus["receptacle_body_name"],
            label=str(focus.get("receptacle_label") or "target"),
            color=[8, 145, 178],
        )
        if box is not None:
            receptacle_pixels = int(box["pixels"])
            boxes.append(box)
    return {
        "status": "ok",
        "object_pixels": object_pixels,
        "receptacle_pixels": receptacle_pixels,
        "boxes": boxes,
    }


def _annotate_focus_visual_grounding(focus: dict[str, Any]) -> dict[str, Any]:
    return _annotate_focus_visual_grounding_impl(
        focus,
        visual_grounding_status=_visual_grounding_status,
    )


def _should_use_fpv_as_verify_focus(focus: dict[str, Any]) -> bool:
    return _should_use_fpv_as_verify_focus_impl(
        focus,
        focus_visibility_is_grounded=_focus_visibility_is_grounded,
    )


def _focus_visibility_is_grounded(
    visibility: dict[str, Any],
    focus: dict[str, Any],
) -> bool:
    return _focus_visibility_is_grounded_impl(visibility, focus)


def _visual_grounding_status(focus: dict[str, Any], visibility: dict[str, Any]) -> str:
    return _visual_grounding_status_impl(
        focus,
        visibility,
        can_hide_contents=_focus_receptacle_can_hide_contents,
    )


def _focus_receptacle_can_hide_contents(focus: dict[str, Any]) -> bool:
    return _focus_receptacle_can_hide_contents_impl(focus)


def _render_segmentation(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    renderer.render()
    renderer.enable_segmentation_rendering()
    renderer.update_scene(data, camera=camera)
    segmentation = renderer.render()
    renderer.close()
    return segmentation


def _segmentation_box(
    model: mujoco.MjModel,
    segmentation: Any,
    body_name: str,
    *,
    label: str,
    color: list[int],
) -> dict[str, Any] | None:
    geom_ids = _subtree_geom_ids(model, body_name)
    if not geom_ids:
        return None
    import numpy as np

    mask = np.isin(segmentation[:, :, 0], geom_ids) & (
        segmentation[:, :, 1] == int(mujoco.mjtObj.mjOBJ_GEOM)
    )
    pixels = int(mask.sum())
    if pixels <= 0:
        return None
    ys, xs = np.where(mask)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    left, top, right, bottom = _inflate_bbox(left, top, right, bottom, segmentation.shape)
    return {
        "label": label,
        "bbox": [left, top, right, bottom],
        "pixels": pixels,
        "color": color,
        "source": "segmentation",
    }


def _highlight_diff_box(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    body_name: str,
    *,
    label: str,
    color: list[int],
    frame: Any | None,
) -> dict[str, Any] | None:
    geom_ids = _subtree_geom_ids(model, body_name)
    if not geom_ids:
        return None
    import numpy as np

    render_shape = frame.shape if frame is not None and hasattr(frame, "shape") else None
    baseline = frame if frame is not None else _render_color_frame(model, data, camera)
    baseline = np.asarray(baseline)
    previous_rgba = model.geom_rgba[geom_ids].copy()
    previous_matid = model.geom_matid[geom_ids].copy()
    try:
        for geom_id in geom_ids:
            model.geom_rgba[geom_id] = np.array([1.0, 0.0, 1.0, 1.0])
            model.geom_matid[geom_id] = -1
        highlighted = _render_color_frame(
            model,
            data,
            camera,
            width=_shape_width(render_shape or baseline.shape),
            height=_shape_height(render_shape or baseline.shape),
        )
    finally:
        model.geom_rgba[geom_ids] = previous_rgba
        model.geom_matid[geom_ids] = previous_matid
    diff = np.abs(np.asarray(highlighted, dtype=np.int16) - baseline.astype(np.int16)).max(axis=2)
    mask = diff > 35
    pixels = int(mask.sum())
    if pixels <= 0:
        return None
    ys, xs = np.where(mask)
    left, right = int(xs.min()), int(xs.max())
    top, bottom = int(ys.min()), int(ys.max())
    left, top, right, bottom = _inflate_bbox(left, top, right, bottom, baseline.shape)
    return {
        "label": label,
        "bbox": [left, top, right, bottom],
        "pixels": pixels,
        "color": color,
        "source": "highlight_diff",
    }


def _render_color_frame(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    width, height = _render_dimensions(width, height)
    _ensure_offscreen_framebuffer(model, width=width, height=height)
    renderer = mujoco.Renderer(model, height=height, width=width, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    return frame


def _ensure_offscreen_framebuffer(
    model: mujoco.MjModel,
    *,
    width: int,
    height: int,
) -> None:
    """Grow MuJoCo's offscreen buffer so requested high-res renders are valid."""
    global_settings = getattr(getattr(model, "vis", None), "global_", None)
    if global_settings is None:
        return
    if int(getattr(global_settings, "offwidth", 0) or 0) < int(width):
        global_settings.offwidth = int(width)
    if int(getattr(global_settings, "offheight", 0) or 0) < int(height):
        global_settings.offheight = int(height)


def _subtree_geom_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    body_ids = _subtree_body_ids(model, body_name)
    return [
        geom_id
        for geom_id in range(model.ngeom)
        if int(model.geom_bodyid[geom_id]) in set(body_ids)
    ]


def _subtree_body_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, body_name)
    if body_id < 0:
        return []
    body_ids = []
    for candidate_id in range(model.nbody):
        current_id = candidate_id
        while current_id > 0:
            if current_id == body_id:
                body_ids.append(candidate_id)
                break
            current_id = int(model.body_parentid[current_id])
    return body_ids


def _inflate_bbox(
    left: int,
    top: int,
    right: int,
    bottom: int,
    shape: Any,
    *,
    min_size: int = 32,
    pad: int = 8,
) -> tuple[int, int, int, int]:
    height, width = int(shape[0]), int(shape[1])
    center_x = (left + right) // 2
    center_y = (top + bottom) // 2
    half_width = max((right - left) // 2 + pad, min_size // 2)
    half_height = max((bottom - top) // 2 + pad, min_size // 2)
    return (
        max(0, center_x - half_width),
        max(29, center_y - half_height),
        min(width - 1, center_x + half_width),
        min(height - 1, center_y + half_height),
    )


def _render_robot_map(state: dict[str, Any], *, focus: dict[str, Any] | None = None) -> Image.Image:
    return _render_robot_map_impl(state, focus=focus)


def _map_points(state: dict[str, Any], focus: dict[str, Any]) -> list[list[float]]:
    return _map_points_impl(state, focus)


def _room_relation_payload(
    state: dict[str, Any],
    receptacle: dict[str, Any],
    robot_point: list[float],
) -> dict[str, Any]:
    return _room_relation_payload_impl(state, receptacle, robot_point)


def _target_room_id(state: dict[str, Any], receptacle: dict[str, Any]) -> str:
    return _target_room_id_impl(state, receptacle)


def _room_outline_for_id(
    state: dict[str, Any],
    room_id: Any,
) -> dict[str, Any] | None:
    return _room_outline_for_id_impl(state, room_id)


def _room_for_point(state: dict[str, Any], point: list[float]) -> str | None:
    return _room_for_point_impl(state, point)


def _point_inside_outline(
    point: list[float],
    outline: dict[str, Any],
    *,
    margin: float,
) -> bool:
    return _point_inside_outline_impl(point, outline, margin=margin)


def _outline_clearance(point: list[float], outline: dict[str, Any] | None) -> float:
    return _outline_clearance_impl(point, outline)


def _angle_delta(a: float, b: float) -> float:
    return _angle_delta_impl(a, b)


def _collect_room_outlines(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    return _collect_room_outlines_impl(model, data, state, xyz=_xyz)


def _geom_xy_bounds(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    geom_id: int,
) -> tuple[list[float], list[float]] | None:
    return _geom_xy_bounds_impl(model, data, geom_id, xyz=_xyz)


def _fallback_room_outlines(state: dict[str, Any]) -> list[dict[str, Any]]:
    return _fallback_room_outlines_impl(state)


def _map_bounds(points: list[list[float]]) -> tuple[float, float, float, float]:
    return _map_bounds_impl(points)


def _apply_qpos(data: mujoco.MjData, qpos: list[float]) -> None:
    data.qpos[:] = qpos


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _json_object_from_text(text: str) -> dict[str, Any]:
    payload = json.loads(text)
    if not isinstance(payload, dict):
        raise ValueError("expected JSON object")
    return payload


def _render_dimensions(width: int, height: int) -> tuple[int, int]:
    return (
        _positive_int(width, DEFAULT_RENDER_WIDTH),
        _positive_int(height, DEFAULT_RENDER_HEIGHT),
    )


def _shape_width(shape: Any) -> int:
    if isinstance(shape, (tuple, list)) and len(shape) >= 2:
        return _positive_int(shape[1], DEFAULT_RENDER_WIDTH)
    return DEFAULT_RENDER_WIDTH


def _shape_height(shape: Any) -> int:
    if isinstance(shape, (tuple, list)) and len(shape) >= 1:
        return _positive_int(shape[0], DEFAULT_RENDER_HEIGHT)
    return DEFAULT_RENDER_HEIGHT


def _primary_body_name(info: dict[str, Any], *, fallback: str) -> str:
    bodies = info.get("name_map", {}).get("bodies", {})
    return next(iter(bodies), fallback)


def _friendly_name(category: str, upstream_id: Any) -> str:
    return f"{category} ({upstream_id})"


def _xyz(values: Any) -> list[float]:
    return [round(float(values[0]), 6), round(float(values[1]), 6), round(float(values[2]), 6)]


def _read_state(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_state(path: Path, state: dict[str, Any]) -> None:
    _refresh_runtime_render_state(state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _count(state: dict[str, Any], tool: str) -> None:
    counts = state.setdefault("tool_event_counts", {})
    key = f"{tool}:request"
    counts[key] = int(counts.get(key, 0)) + 1


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return {"ok": True, "tool": tool, "status": "ok", **payload}


def _error(tool: str, error_reason: str, **payload: Any) -> dict[str, Any]:
    return {"ok": False, "tool": tool, "status": "error", "error_reason": error_reason, **payload}


if __name__ == "__main__":
    main()

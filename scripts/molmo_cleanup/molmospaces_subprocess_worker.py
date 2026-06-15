#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
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
from scripts.molmo_cleanup.molmospaces_actions import (
    MolmoActionHooks,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    close_receptacle as _close_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    close_receptacle_state_mutation as _close_receptacle_state_mutation_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    done_cleanup as _done_cleanup_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    frame_comparison_object as _frame_comparison_object_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    navigate_to_object as _navigate_to_object_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    navigate_to_receptacle as _navigate_to_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    navigate_to_receptacle_core as _navigate_to_receptacle_core_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    navigate_to_waypoint as _navigate_to_waypoint_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    open_receptacle as _open_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    open_receptacle_state_mutation as _open_receptacle_state_mutation_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    pick_object as _pick_object_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    place_inside_object as _place_inside_object_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    place_object as _place_object_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    place_object_at_receptacle as _place_object_at_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_actions import (
    robot_pose_state_mutation as _robot_pose_state_mutation_impl,
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
from scripts.molmo_cleanup.molmospaces_rendering import (
    ensure_offscreen_framebuffer as _ensure_offscreen_framebuffer_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    fixed_camera_diagnostics as _fixed_camera_diagnostics_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    focus_visibility as _focus_visibility_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    free_camera_diagnostics as _free_camera_diagnostics_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    highlight_diff_box as _highlight_diff_box_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    image_to_array as _image_to_array_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    inflate_bbox as _inflate_bbox_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    load_rendered_robot_view_image as _load_rendered_robot_view_image_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    render_color_frame as _render_color_frame_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    render_dimensions as _render_dimensions_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    render_fixed_camera as _render_fixed_camera_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    render_free_camera as _render_free_camera_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    render_segmentation as _render_segmentation_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    segmentation_box as _segmentation_box_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    shape_height as _shape_height_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    shape_width as _shape_width_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    subtree_body_ids as _subtree_body_ids_impl,
)
from scripts.molmo_cleanup.molmospaces_rendering import (
    subtree_geom_ids as _subtree_geom_ids_impl,
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
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    add_joint_qpos_if_present as _add_joint_qpos_if_present_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    apply_robot_view_camera_offset as _apply_robot_view_camera_offset_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    held_object_position as _held_object_position_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    joint_qpos_width as _joint_qpos_width_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    joint_type_name as _joint_type_name_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    load_model_data as _load_model_data_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    load_model_data_for_state as _load_model_data_for_state_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    load_robot_model_data as _load_robot_model_data_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    openable_receptacle_joints as _openable_receptacle_joints_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    refresh_object_positions as _refresh_object_positions_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    refresh_runtime_render_state as _refresh_runtime_render_state_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    robot_camera_names as _robot_camera_names_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    robot_result_payload as _robot_result_payload_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    robot_xml_name as _robot_xml_name_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    runtime_render_state as _runtime_render_state_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    runtime_subtree_joints as _runtime_subtree_joints_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    set_free_body_position as _set_free_body_position_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    set_joint_qpos as _set_joint_qpos_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    set_robot_pose as _set_robot_pose_impl,
)
from scripts.molmo_cleanup.molmospaces_runtime_state import (
    sync_held_object_to_robot_pose as _sync_held_object_to_robot_pose_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    HELD_LOCATION_ID,
    MolmoScenarioHooks,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    collect_dynamic_objects as _collect_dynamic_objects_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    collect_receptacles as _collect_receptacles_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    first_receptacle_id as _first_receptacle_id_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    first_wrong_receptacle as _first_wrong_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    manifest_target_by_object_id as _manifest_target_by_object_id_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    nearest_receptacle as _nearest_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    public_scenario as _public_scenario_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    read_containment as _read_containment_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    read_locations as _read_locations_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    score as _score_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    seed_misplaced_objects as _seed_misplaced_objects_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    target_placement_index as _target_placement_index_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    target_receptacle_id as _target_receptacle_id_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    target_relation as _target_relation_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    target_start_receptacle as _target_start_receptacle_impl,
)
from scripts.molmo_cleanup.molmospaces_scenario_state import (
    target_start_receptacle_id as _target_start_receptacle_id_impl,
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
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    WorkerCommandHandler,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    cli_command_kwargs as _cli_command_kwargs_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    count_tool_request as _count_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    error_response as _error_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    float_or_zero as _float_or_zero_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    json_object_from_text as _json_object_from_text_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    ok_response as _ok_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    optional_str as _optional_str_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    positive_int as _positive_int_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    read_state as _read_state_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    run_loaded_state_command as _run_loaded_state_command_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    run_worker_command as _run_worker_command_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    serve_worker as _serve_worker_impl,
)
from scripts.molmo_cleanup.molmospaces_worker_protocol import (
    write_state as _write_state_impl_protocol,
)

BACKEND = "molmospaces_subprocess"
API_SEMANTIC_PROVENANCE = "api_semantic"
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
type _WorkerCommandHandler = WorkerCommandHandler


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
    _serve_worker_impl(
        state_path,
        run_state_command=run_state_command,
        ok=_ok,
    )


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
    return _run_worker_command_impl(
        state_path,
        command,
        kwargs,
        read_state=_read_state,
        write_state=_write_state,
        run_loaded_state_command=_run_loaded_state_command,
    )


def _run_loaded_state_command(
    state: dict[str, Any],
    command: str,
    kwargs: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    return _run_loaded_state_command_impl(
        state,
        command,
        kwargs,
        handlers=_WORKER_COMMAND_HANDLERS,
        mutating_commands=_STATE_MUTATING_COMMANDS,
    )


def _cli_command_kwargs(args: argparse.Namespace) -> dict[str, Any]:
    return _cli_command_kwargs_impl(args)


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


def _molmo_action_hooks() -> MolmoActionHooks:
    return MolmoActionHooks(
        api_semantic_provenance=API_SEMANTIC_PROVENANCE,
        backend=BACKEND,
        held_location_id=HELD_LOCATION_ID,
        apply_qpos=_apply_qpos,
        close_receptacle_state_mutation=_close_receptacle_state_mutation,
        count=_count,
        error=_error,
        held_object_position=_held_object_position,
        load_model_data_for_state=_load_model_data_for_state,
        ok=_ok,
        open_receptacle_state_mutation=_open_receptacle_state_mutation,
        openable_receptacle_joints=_openable_receptacle_joints,
        placement_diagnostic=_placement_diagnostic,
        read_containment=_read_containment,
        read_locations=_read_locations,
        receptacle_requires_open=_receptacle_requires_open,
        refresh_object_positions=_refresh_object_positions,
        resolve_placement=_resolve_placement,
        robot_pose_for_open_receptacle=_robot_pose_for_open_receptacle,
        robot_pose_for_waypoint=_robot_pose_for_waypoint,
        robot_pose_near_object=_robot_pose_near_object,
        robot_pose_near_receptacle=_robot_pose_near_receptacle,
        robot_pose_state_mutation=_robot_pose_state_mutation,
        score=_score,
        set_free_body_position=_set_free_body_position,
        set_joint_qpos=_set_joint_qpos,
        set_robot_pose=_set_robot_pose,
        sync_held_object_to_robot_pose=_sync_held_object_to_robot_pose,
        waypoint_target_position=_waypoint_target_position,
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
    return _navigate_to_receptacle_impl(state, receptacle_id, hooks=_molmo_action_hooks())


def _navigate_to_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
) -> dict[str, Any]:
    return _navigate_to_receptacle_core_impl(
        state,
        receptacle_id,
        tool=tool,
        hooks=_molmo_action_hooks(),
    )


def navigate_to_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return _navigate_to_object_impl(state, object_id, hooks=_molmo_action_hooks())


def navigate_to_waypoint(state: dict[str, Any], waypoint: dict[str, Any]) -> dict[str, Any]:
    return _navigate_to_waypoint_impl(state, waypoint, hooks=_molmo_action_hooks())


def frame_comparison_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return _frame_comparison_object_impl(state, object_id, hooks=_molmo_action_hooks())


def pick_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return _pick_object_impl(state, object_id, hooks=_molmo_action_hooks())


def place_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _place_object_impl(state, receptacle_id, hooks=_molmo_action_hooks())


def place_inside_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _place_inside_object_impl(state, receptacle_id, hooks=_molmo_action_hooks())


def _place_object_at_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
    *,
    tool: str,
    relation: str,
) -> dict[str, Any]:
    return _place_object_at_receptacle_impl(
        state,
        receptacle_id,
        tool=tool,
        relation=relation,
        hooks=_molmo_action_hooks(),
    )


def open_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _open_receptacle_impl(state, receptacle_id, hooks=_molmo_action_hooks())


def close_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _close_receptacle_impl(state, receptacle_id, hooks=_molmo_action_hooks())


def _robot_pose_state_mutation(held_object_changed: bool) -> str:
    return _robot_pose_state_mutation_impl(held_object_changed)


def _open_receptacle_state_mutation(
    joints_changed: bool,
    robot_pose_changed: bool,
    held_object_changed: bool,
) -> str:
    return _open_receptacle_state_mutation_impl(
        joints_changed,
        robot_pose_changed,
        held_object_changed,
    )


def _close_receptacle_state_mutation(
    joints_changed: bool,
    held_object_changed: bool,
) -> str:
    return _close_receptacle_state_mutation_impl(joints_changed, held_object_changed)


def done_cleanup(state: dict[str, Any], reason: str) -> dict[str, Any]:
    return _done_cleanup_impl(state, reason, hooks=_molmo_action_hooks())


def _collect_dynamic_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    return _collect_dynamic_objects_impl(model, data, metadata, hooks=_molmo_scenario_hooks())


def _collect_receptacles(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    return _collect_receptacles_impl(model, data, metadata, hooks=_molmo_scenario_hooks())


def _seed_misplaced_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    targets: list[dict[str, Any]],
) -> None:
    _seed_misplaced_objects_impl(model, data, state, targets, hooks=_molmo_scenario_hooks())


def _manifest_target_by_object_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _manifest_target_by_object_id_impl(state)


def _target_receptacle_id(
    target: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    return _target_receptacle_id_impl(target, manifest_target)


def _target_start_receptacle(
    state: dict[str, Any],
    target: dict[str, Any],
    wrong_pool: list[dict[str, Any]],
    index: int,
    manifest_target: dict[str, Any] | None,
) -> dict[str, Any]:
    return _target_start_receptacle_impl(state, target, wrong_pool, index, manifest_target)


def _target_start_receptacle_id(state: dict[str, Any], target: dict[str, Any]) -> str:
    return _target_start_receptacle_id_impl(state, target)


def _target_relation(
    receptacle: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    return _target_relation_impl(receptacle, manifest_target, hooks=_molmo_scenario_hooks())


def _target_placement_index(index: int, manifest_target: dict[str, Any] | None) -> int:
    return _target_placement_index_impl(index, manifest_target)


def _public_scenario(state: dict[str, Any]) -> dict[str, Any]:
    return _public_scenario_impl(state, read_locations=_read_locations, backend=BACKEND)


def _read_locations(state: dict[str, Any]) -> dict[str, str]:
    return _read_locations_impl(state, hooks=_molmo_scenario_hooks())


def _read_containment(state: dict[str, Any]) -> dict[str, dict[str, str]]:
    return _read_containment_impl(state)


def _score(final_locations: dict[str, str], manifest: dict[str, Any]) -> dict[str, Any]:
    return _score_impl(final_locations, manifest)


def _nearest_receptacle(position: list[float], receptacles: list[dict[str, Any]]) -> str:
    return _nearest_receptacle_impl(position, receptacles)


def _first_wrong_receptacle(state: dict[str, Any], target: dict[str, Any]) -> str:
    return _first_wrong_receptacle_impl(state, target)


def _first_receptacle_id(state: dict[str, Any]) -> str | None:
    return _first_receptacle_id_impl(state)


def _set_free_body_position(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    position: list[float],
) -> None:
    _set_free_body_position_impl(model, data, body_name, position)


def _refresh_object_positions(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> None:
    _refresh_object_positions_impl(model, data, state, xyz=_xyz)


def _refresh_runtime_render_state(state: dict[str, Any]) -> None:
    _refresh_runtime_render_state_impl(
        state,
        load_model_data_for_state=_load_model_data_for_state,
        apply_qpos=_apply_qpos,
        runtime_render_state=_runtime_render_state,
    )


def _runtime_render_state(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any]:
    return _runtime_render_state_impl(
        model,
        data,
        state,
        runtime_subtree_joints=_runtime_subtree_joints,
        xyz=_xyz,
    )


def _runtime_subtree_joints(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    body_name: str,
    *,
    exclude_root_freejoint: bool,
) -> list[dict[str, Any]]:
    return _runtime_subtree_joints_impl(
        model,
        data,
        body_name,
        exclude_root_freejoint=exclude_root_freejoint,
        subtree_body_ids=_subtree_body_ids,
        joint_qpos_width=_joint_qpos_width,
        joint_type_name=_joint_type_name,
    )


def _joint_qpos_width(model: mujoco.MjModel, joint_id: int) -> int:
    return _joint_qpos_width_impl(model, joint_id)


def _joint_type_name(model: mujoco.MjModel, joint_id: int) -> str:
    return _joint_type_name_impl(model, joint_id)


def _molmo_placement_hooks() -> MolmoPlacementHooks:
    return MolmoPlacementHooks(
        subtree_geom_ids=_subtree_geom_ids,
        xyz=_xyz,
    )


def _molmo_scenario_hooks() -> MolmoScenarioHooks:
    return MolmoScenarioHooks(
        primary_body_name=_primary_body_name,
        friendly_name=_friendly_name,
        xyz=_xyz,
        receptacle_support_surfaces=_receptacle_support_surfaces,
        support_top_z=_support_top_z,
        receptacle_requires_open=_receptacle_requires_open,
        receptacle_prefers_inside=_receptacle_prefers_inside,
        resolve_placement=_resolve_placement,
        set_free_body_position=_set_free_body_position,
        refresh_object_positions=_refresh_object_positions,
        placement_diagnostic=_placement_diagnostic,
        load_model_data_for_state=_load_model_data_for_state,
        apply_qpos=_apply_qpos,
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
    return _load_model_data_impl(scene_xml)


def _load_model_data_for_state(state: dict[str, Any]) -> tuple[mujoco.MjModel, mujoco.MjData]:
    return _load_model_data_for_state_impl(
        state,
        model_data_cache=_MODEL_DATA_CACHE,
        load_model_data=_load_model_data,
        load_robot_model_data=_load_robot_model_data,
    )


def _load_robot_model_data(
    scene_xml: Path,
    robot_xml: Path,
) -> tuple[mujoco.MjModel, mujoco.MjData]:
    return _load_robot_model_data_impl(scene_xml, robot_xml, load_model_data=_load_model_data)


def _robot_xml_name(robot_name: str) -> str:
    return _robot_xml_name_impl(robot_name)


def _robot_camera_names(model: mujoco.MjModel) -> list[str]:
    return _robot_camera_names_impl(model)


def _robot_result_payload(state: dict[str, Any], model: mujoco.MjModel) -> dict[str, Any]:
    return _robot_result_payload_impl(state, model, robot_camera_names=_robot_camera_names)


def _set_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    pose: dict[str, float],
) -> None:
    _set_robot_pose_impl(model, data, pose, set_joint_qpos=_set_joint_qpos)


def _apply_robot_view_camera_offset(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    *,
    yaw_offset_deg: float = 0.0,
    pitch_offset_deg: float = 0.0,
) -> dict[str, Any]:
    return _apply_robot_view_camera_offset_impl(
        model,
        data,
        yaw_offset_deg=yaw_offset_deg,
        pitch_offset_deg=pitch_offset_deg,
        add_joint_qpos_if_present=_add_joint_qpos_if_present,
        robot_view_camera_adjustment=_robot_view_camera_adjustment,
    )


def _add_joint_qpos_if_present(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    delta: float,
) -> bool:
    return _add_joint_qpos_if_present_impl(model, data, joint_name, delta)


def _set_joint_qpos(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    joint_name: str,
    value: float,
) -> None:
    _set_joint_qpos_impl(model, data, joint_name, value)


def _sync_held_object_to_robot_pose(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> dict[str, Any] | None:
    return _sync_held_object_to_robot_pose_impl(
        model,
        data,
        state,
        held_object_position=_held_object_position,
        set_free_body_position=_set_free_body_position,
    )


def _held_object_position(state: dict[str, Any]) -> list[float]:
    return _held_object_position_impl(state)


def _openable_receptacle_joints(
    model: mujoco.MjModel,
    body_name: str,
) -> list[dict[str, Any]]:
    return _openable_receptacle_joints_impl(model, body_name, subtree_body_ids=_subtree_body_ids)


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
    return _render_fixed_camera_impl(
        model,
        data,
        camera_name,
        width=width,
        height=height,
        render_dimensions=_render_dimensions,
        ensure_offscreen_framebuffer=_ensure_offscreen_framebuffer,
    )


def _fixed_camera_diagnostics(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
) -> dict[str, Any]:
    return _fixed_camera_diagnostics_impl(model, data, camera_name)


def _free_camera_diagnostics(camera: mujoco.MjvCamera) -> dict[str, Any]:
    return _free_camera_diagnostics_impl(camera)


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
    return _render_free_camera_impl(
        model,
        data,
        camera,
        width=width,
        height=height,
        render_dimensions=_render_dimensions,
        ensure_offscreen_framebuffer=_ensure_offscreen_framebuffer,
    )


def _load_rendered_robot_view_image(camera_views: dict[str, Any], *, role: str) -> Any:
    return _load_rendered_robot_view_image_impl(camera_views, role=role)


def _image_to_array(path: Path) -> Any:
    return _image_to_array_impl(path)


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
    return _focus_visibility_impl(
        model,
        data,
        camera,
        focus,
        frame=frame,
        render_segmentation=_render_segmentation,
        segmentation_box=_segmentation_box,
        highlight_diff_box=_highlight_diff_box,
        shape_width=_shape_width,
        shape_height=_shape_height,
    )


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
    return _render_segmentation_impl(
        model,
        data,
        camera,
        width=width,
        height=height,
        render_dimensions=_render_dimensions,
        ensure_offscreen_framebuffer=_ensure_offscreen_framebuffer,
    )


def _segmentation_box(
    model: mujoco.MjModel,
    segmentation: Any,
    body_name: str,
    *,
    label: str,
    color: list[int],
) -> dict[str, Any] | None:
    return _segmentation_box_impl(
        model,
        segmentation,
        body_name,
        label=label,
        color=color,
        subtree_geom_ids=_subtree_geom_ids,
        inflate_bbox=_inflate_bbox,
    )


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
    return _highlight_diff_box_impl(
        model,
        data,
        camera,
        body_name,
        label=label,
        color=color,
        frame=frame,
        subtree_geom_ids=_subtree_geom_ids,
        render_color_frame=_render_color_frame,
        shape_width=_shape_width,
        shape_height=_shape_height,
        inflate_bbox=_inflate_bbox,
    )


def _render_color_frame(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
    *,
    width: int = DEFAULT_RENDER_WIDTH,
    height: int = DEFAULT_RENDER_HEIGHT,
) -> Any:
    return _render_color_frame_impl(
        model,
        data,
        camera,
        width=width,
        height=height,
        render_dimensions=_render_dimensions,
        ensure_offscreen_framebuffer=_ensure_offscreen_framebuffer,
    )


def _ensure_offscreen_framebuffer(
    model: mujoco.MjModel,
    *,
    width: int,
    height: int,
) -> None:
    _ensure_offscreen_framebuffer_impl(model, width=width, height=height)


def _subtree_geom_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    return _subtree_geom_ids_impl(model, body_name, subtree_body_ids=_subtree_body_ids)


def _subtree_body_ids(model: mujoco.MjModel, body_name: str) -> list[int]:
    return _subtree_body_ids_impl(model, body_name)


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
    return _inflate_bbox_impl(
        left,
        top,
        right,
        bottom,
        shape,
        min_size=min_size,
        pad=pad,
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
    return _optional_str_impl(value)


def _positive_int(value: Any, default: int) -> int:
    return _positive_int_impl(value, default)


def _float_or_zero(value: Any) -> float:
    return _float_or_zero_impl(value)


def _json_object_from_text(text: str) -> dict[str, Any]:
    return _json_object_from_text_impl(text)


def _render_dimensions(width: int, height: int) -> tuple[int, int]:
    return _render_dimensions_impl(
        width,
        height,
        default_width=DEFAULT_RENDER_WIDTH,
        default_height=DEFAULT_RENDER_HEIGHT,
    )


def _shape_width(shape: Any) -> int:
    return _shape_width_impl(shape, default_width=DEFAULT_RENDER_WIDTH)


def _shape_height(shape: Any) -> int:
    return _shape_height_impl(shape, default_height=DEFAULT_RENDER_HEIGHT)


def _primary_body_name(info: dict[str, Any], *, fallback: str) -> str:
    bodies = info.get("name_map", {}).get("bodies", {})
    return next(iter(bodies), fallback)


def _friendly_name(category: str, upstream_id: Any) -> str:
    return f"{category} ({upstream_id})"


def _xyz(values: Any) -> list[float]:
    return [round(float(values[0]), 6), round(float(values[1]), 6), round(float(values[2]), 6)]


def _read_state(path: Path) -> dict[str, Any]:
    return _read_state_impl(path)


def _write_state(path: Path, state: dict[str, Any]) -> None:
    _write_state_impl_protocol(
        path, state, refresh_runtime_render_state=_refresh_runtime_render_state
    )


def _count(state: dict[str, Any], tool: str) -> None:
    _count_impl(state, tool)


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return _ok_impl(tool, **payload)


def _error(tool: str, error_reason: str, **payload: Any) -> dict[str, Any]:
    return _error_impl(tool, error_reason, **payload)


if __name__ == "__main__":
    main()

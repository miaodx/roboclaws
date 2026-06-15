#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Callable, Iterable

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image, ImageDraw

from roboclaws.household.backend import HELD_LOCATION_ID
from roboclaws.household.camera_control import (
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    MOLMOSPACES_SCENE_FRAME,
    normalize_camera_control_request,
)
from roboclaws.household.color_management import apply_camera_color_profile
from roboclaws.household.generated_mess import (
    GENERATED_MESS_MANIFEST_SCHEMA,
    generated_mess_success_threshold,
    select_generated_mess_targets,
    targets_from_generated_mess_manifest,
)
from roboclaws.household.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
)
from roboclaws.household.robot_view_camera_control import (
    backend_local_robot_view_camera_control_contract,
    robot_mounted_head_camera_control_contract,
)
from roboclaws.household.robot_view_pose import resolve_cleanup_robot_pose
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.scoring import score_cleanup
from roboclaws.household.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.household.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)
from scripts.isaac_lab_cleanup.isaac_camera_capture import (
    IsaacCameraCaptureHooks,
    IsaacCameraCaptureRequest,
    capture_isaac_lab_camera_views,
)
from scripts.isaac_lab_cleanup.isaac_camera_geometry import (
    ISAAC_RBY1M_HEAD_CAMERA_PRIM,
    RBY1M_HEAD_CAMERA_FOCAL_LENGTH_MM,
    RBY1M_HEAD_CAMERA_VERTICAL_FOV_DEG,
    RBY1M_HEAD_CAMERA_ZERO_POSITION_M,
    RBY1M_HEAD_PITCH_PIVOT_M,
    horizontal_aperture_from_lens,
    isaac_camera_view_poses,
    matrix4d_rowmajor,
    normalize_quat,
    optional_float,
    quat_from_axis_angle,
    quat_multiply,
    robot_pose_yaw_deg,
    robot_relative_chase_eye_target,
    rotate_point_y_about_pivot,
    static_head_camera_pose_for_pitch,
    tensor_first_vec3,
    usd_attr_float,
    usd_camera_fov_metadata,
    usd_vec,
)
from scripts.isaac_lab_cleanup.isaac_camera_geometry import (
    RBY1M_CHASE_CAMERA_OFFSET_M as _RBY1M_CHASE_CAMERA_OFFSET_M,
)
from scripts.isaac_lab_cleanup.isaac_camera_geometry import (
    RBY1M_CHASE_CAMERA_TARGET_OFFSET_M as _RBY1M_CHASE_CAMERA_TARGET_OFFSET_M,
)
from scripts.isaac_lab_cleanup.isaac_camera_geometry import (
    RBY1M_HEAD_CAMERA_ZERO_QUAT_WXYZ as _RBY1M_HEAD_CAMERA_ZERO_QUAT_WXYZ,
)
from scripts.isaac_lab_cleanup.isaac_camera_geometry import (
    robot_view_color_profile as isaac_robot_view_color_profile,
)
from scripts.isaac_lab_cleanup.isaac_capture_quality import (
    apply_isaac_capture_quality_overrides,
)
from scripts.isaac_lab_cleanup.isaac_capture_quality import (
    restore_isaac_capture_quality_overrides as _restore_isaac_capture_quality_overrides,
)
from scripts.isaac_lab_cleanup.isaac_mapping_diagnostics import (
    mapping_gap_diagnostics as _mapping_gap_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_mapping_diagnostics import (
    scene_load_diagnostics as _scene_load_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_mapping_diagnostics import (
    scene_usd_path as _scene_usd_path_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    ISAAC_PLACEMENT_RESOLVER_SOURCE as _ISAAC_PLACEMENT_RESOLVER_SOURCE,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    PLACEMENT_DIAGNOSTIC_SCHEMA as _PLACEMENT_DIAGNOSTIC_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    IsaacPlacementHooks,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    aabb_xy_overlaps as _aabb_xy_overlaps_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    candidate_has_direct_support as _candidate_has_direct_support_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    elevated_position_over_surface as _elevated_position_over_surface_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_candidate_is_clear_of_dynamic_objects as _candidate_clear_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_direct_support_clearance as _isaac_direct_support_clearance_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_direct_support_placement as _isaac_direct_support_placement_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_fallback_placement_position as _isaac_fallback_placement_position_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_index_entry as _isaac_index_entry_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_bottom_offset as _isaac_object_bottom_offset_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_current_aabb as _isaac_object_current_aabb_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_footprint_half_extents as _isaac_object_footprint_half_extents_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_height as _isaac_object_height_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_surface_lift as _isaac_object_surface_lift_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_object_world_bounds as _isaac_object_world_bounds_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_placement_diagnostic as _isaac_placement_diagnostic_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_receptacle_support_surface as _isaac_receptacle_support_surface_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_receptacle_support_surfaces as _isaac_receptacle_support_surfaces_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_receptacle_world_bounds as _isaac_receptacle_world_bounds_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    isaac_state_objects_for_clearance as _isaac_state_objects_for_clearance_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    normalize_support_surface as _normalize_support_surface_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    resolve_isaac_placement as _resolve_isaac_placement_impl,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    surface_candidate_positions as _surface_candidate_positions_impl,
)
from scripts.isaac_lab_cleanup.isaac_render_diagnostics import (
    ISAAC_CAPTURE_QUALITY_SETTING_FIELDS,
    ISAAC_NATIVE_RENDER_SETTING_PATHS,
    camera_render_product_paths,
    capture_quality_settings,
    capture_quality_settings_unavailable,
    isaac_setting_value,
    native_render_diagnostics,
    native_render_diagnostics_unavailable,
    native_setting_candidate_count,
    render_product_paths_from_value,
)
from scripts.isaac_lab_cleanup.isaac_render_diagnostics import (
    ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA as _ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_robot_import import (
    ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA as _ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_robot_import import (
    ISAAC_RBY1M_ROBOT_IMPORT_SUMMARY_PATH,
    ISAAC_RBY1M_ROBOT_USD_PATH,
    find_rby1m_isaac_urdf,
    load_json_if_file,
    rby1m_robot_import_plan,
    repo_path,
    robot_payload,
)
from scripts.isaac_lab_cleanup.isaac_robot_view_artifacts import (
    copy_nonblank_rgb_image,
    copy_real_robot_view_images,
    copy_real_snapshot_image,
    has_required_robot_view_images,
    pil_image_has_variance,
    real_rendering_proven,
    real_robot_view_images,
    real_smoke_robot_view_images,
    real_snapshot_source_image,
    robot_view_command_provenance,
    robot_view_provenance,
    semantic_pose_robot_view_provenance,
)
from scripts.isaac_lab_cleanup.isaac_runtime_diagnostics import (
    module_version,
)
from scripts.isaac_lab_cleanup.isaac_runtime_diagnostics import (
    rendering_diagnostics as _runtime_rendering_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_runtime_diagnostics import (
    runtime_diagnostics as _runtime_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_runtime_smoke_usd import (
    GENERATED_SCENE_KINDS,
)
from scripts.isaac_lab_cleanup.isaac_runtime_smoke_usd import (
    generated_scene_filename as _generated_scene_filename,
)
from scripts.isaac_lab_cleanup.isaac_runtime_smoke_usd import (
    write_generated_runtime_smoke_usd as _write_generated_runtime_smoke_usd,
)
from scripts.isaac_lab_cleanup.isaac_scene_bindings import (
    SCENE_BINDING_SCHEMA as _SCENE_BINDING_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_scene_bindings import (
    _scene_match_tokens,
    bind_public_scene_item,
    scene_binding_diagnostics,
    scene_index_match,
)
from scripts.isaac_lab_cleanup.isaac_scene_camera_capture import (
    IsaacSceneCameraCaptureHooks,
    IsaacSceneCameraCaptureRequest,
    capture_isaac_lab_scene_camera_views,
)
from scripts.isaac_lab_cleanup.isaac_scene_camera_geometry import (
    apply_scene_transform_to_point,
    backend_transform_for_lane,
    bounds_from_usd_prim_path,
    camera_vec3,
    eye_from_lookat_spec,
    image_has_variance,
    isaac_scene_camera_view_spec,
    lane_camera_orbit,
    load_camera_view_specs,
)
from scripts.isaac_lab_cleanup.isaac_scene_camera_geometry import (
    load_camera_request_from_args as _load_camera_request_from_args_impl,
)
from scripts.isaac_lab_cleanup.isaac_scene_index_geometry import (
    authored_reference_asset_paths,
    fallback_room_outlines_from_indices,
    is_local_reference_asset_path,
    local_reference_asset_missing,
    room_outline_from_usd_prim,
    room_outlines_from_scene_index_diagnostics,
    round_vec3,
    usd_list_op_items,
)
from scripts.isaac_lab_cleanup.isaac_scene_index_metadata import (
    MOLMOSPACES_SCENE_INDEX_RECEPTACLE_CATEGORY_NORMS,
    category_from_usd_name,
    contains_child_segment,
    is_molmospaces_object_metadata,
    is_molmospaces_receptacle_metadata,
    is_object_prim_path,
    is_receptacle_prim_path,
    load_molmospaces_scene_metadata,
    merge_molmospaces_metadata_index,
    metadata_room_id,
    molmospaces_metadata_prim_path,
    molmospaces_prim_path_rank,
    usd_handle_from_prim,
    usd_index_entry,
    usd_metadata_index_entry,
    usd_safe_name,
)
from scripts.isaac_lab_cleanup.isaac_segmentation_diagnostics import (
    ISAAC_SEGMENTATION_DATA_TYPES as _ISAAC_SEGMENTATION_DATA_TYPES,
)
from scripts.isaac_lab_cleanup.isaac_segmentation_diagnostics import (
    MAX_SEGMENTATION_CANDIDATES as _MAX_SEGMENTATION_CANDIDATES,
)
from scripts.isaac_lab_cleanup.isaac_segmentation_diagnostics import (
    SEGMENTATION_SCHEMA as _SEGMENTATION_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_segmentation_diagnostics import (
    camera_segmentation_capture_diagnostics,
    camera_segmentation_not_requested_diagnostics,
    camera_segmentation_view_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_segmentation_diagnostics import (
    segmentation_diagnostics as _segmentation_diagnostics,
)
from scripts.isaac_lab_cleanup.isaac_semantic_labels import (
    apply_scene_index_semantic_labels,
)
from scripts.isaac_lab_cleanup.isaac_semantic_labels import (
    semantic_label_application_not_requested as _semantic_label_application_not_requested,
)
from scripts.isaac_lab_cleanup.isaac_semantic_labels import (
    semantic_label_target_prims as _semantic_label_target_prims,
)
from scripts.isaac_lab_cleanup.isaac_semantic_pose_robot_view import (
    SemanticPoseRobotViewHooks,
    SemanticPoseRobotViewRequest,
    real_semantic_pose_robot_view_images,
)
from scripts.isaac_lab_cleanup.isaac_semantic_pose_state import (
    initial_semantic_pose_state,
    record_semantic_pose_event,
    record_waypoint_pose_event,
    semantic_pose_state_from_backend_state,
)
from scripts.isaac_lab_cleanup.isaac_stage_lighting import (
    current_stage_bounds,
    ensure_capture_lighting,
    isaac_distant_light_rotation_from_direction,
    normalized_vec3,
    prim_type_is_light,
    scale_stage_light_intensities,
    stage_light_paths,
)
from scripts.isaac_lab_cleanup.isaac_support_surface_geometry import (
    ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE as _ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE,
)
from scripts.isaac_lab_cleanup.isaac_support_surface_geometry import (
    ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE as _ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE,
)
from scripts.isaac_lab_cleanup.isaac_support_surface_geometry import (
    ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE as _ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE,
)
from scripts.isaac_lab_cleanup.isaac_support_surface_geometry import (
    is_usd_renderable_support_candidate,
    support_pose_from_support_surface,
    support_pose_from_usd_bounds,
    support_surface_from_usd_bounds,
    usd_receptacle_support_surfaces,
    usd_support_surface_score,
    usd_support_surface_union_entry,
)
from scripts.isaac_lab_cleanup.isaac_usd_xform import (
    set_usd_xform_translate as _set_usd_xform_translate,
)
from scripts.isaac_lab_cleanup.isaac_worker_cli import build_arg_parser

STATE_SCHEMA = "isaac_lab_backend_state_v1"
DEFAULT_WIDTH = 540
DEFAULT_HEIGHT = 360
ROBOT_VIEW_KEYS = ("fpv", "chase", "map", "verify")
SCENE_BINDING_SCHEMA = _SCENE_BINDING_SCHEMA
_bind_public_scene_item = bind_public_scene_item
_scene_binding_diagnostics = scene_binding_diagnostics
_scene_index_match = scene_index_match
_authored_reference_asset_paths = authored_reference_asset_paths
_category_from_usd_name = category_from_usd_name
_contains_child_segment = contains_child_segment
_fallback_room_outlines_from_indices = fallback_room_outlines_from_indices
_is_local_reference_asset_path = is_local_reference_asset_path
_is_molmospaces_object_metadata = is_molmospaces_object_metadata
_is_molmospaces_receptacle_metadata = is_molmospaces_receptacle_metadata
_is_object_prim_path = is_object_prim_path
_is_receptacle_prim_path = is_receptacle_prim_path
_local_reference_asset_missing = local_reference_asset_missing
_load_molmospaces_scene_metadata = load_molmospaces_scene_metadata
_merge_molmospaces_metadata_index = merge_molmospaces_metadata_index
_metadata_room_id = metadata_room_id
_molmospaces_metadata_prim_path = molmospaces_metadata_prim_path
_molmospaces_prim_path_rank = molmospaces_prim_path_rank
_room_outlines_from_scene_index_diagnostics = room_outlines_from_scene_index_diagnostics
_round_vec3 = round_vec3
_usd_list_op_items = usd_list_op_items
_MOLMOSPACES_SCENE_INDEX_RECEPTACLE_CATEGORY_NORMS = (
    MOLMOSPACES_SCENE_INDEX_RECEPTACLE_CATEGORY_NORMS
)
_usd_handle_from_prim = usd_handle_from_prim
_usd_index_entry = usd_index_entry
_usd_metadata_index_entry = usd_metadata_index_entry
_usd_safe_name = usd_safe_name
_is_usd_renderable_support_candidate = is_usd_renderable_support_candidate
_support_pose_from_support_surface = support_pose_from_support_surface
_support_pose_from_usd_bounds = support_pose_from_usd_bounds
_support_surface_from_usd_bounds = support_surface_from_usd_bounds
_usd_support_surface_score = usd_support_surface_score
_usd_support_surface_union = usd_support_surface_union_entry
SEGMENTATION_SCHEMA = _SEGMENTATION_SCHEMA
ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA = _ISAAC_NATIVE_RENDER_DIAGNOSTICS_SCHEMA
ISAAC_SEGMENTATION_DATA_TYPES = _ISAAC_SEGMENTATION_DATA_TYPES
MOLMOSPACES_CLEANUP_RECEPTACLE_CATEGORY_NORMS = {
    "sink",
    "shelvingunit",
    "desk",
    "fridge",
    "tvstand",
    "bed",
    "sofa",
    "diningtable",
    "countertop",
}
MAX_SEGMENTATION_CANDIDATES = _MAX_SEGMENTATION_CANDIDATES
RBY1M_CHASE_CAMERA_OFFSET_M = _RBY1M_CHASE_CAMERA_OFFSET_M
RBY1M_CHASE_CAMERA_TARGET_OFFSET_M = _RBY1M_CHASE_CAMERA_TARGET_OFFSET_M
RBY1M_HEAD_CAMERA_ZERO_QUAT_WXYZ = _RBY1M_HEAD_CAMERA_ZERO_QUAT_WXYZ
REAL_SMOKE_CAPTURE_METHOD = "isaac_lab_camera_rgb"
REAL_ROBOT_VIEW_CAPTURE_METHOD = "isaac_lab_camera_rgb_static_robot_views"
REAL_ROBOT_VIEW_RERENDER_METHOD = "isaac_lab_camera_rgb_semantic_pose_robot_views"
REAL_SMOKE_RENDERER_MODE = "isaac_lab_headless_rtx"
PLACEMENT_DIAGNOSTIC_SCHEMA = _PLACEMENT_DIAGNOSTIC_SCHEMA
ISAAC_PLACEMENT_RESOLVER_SOURCE = _ISAAC_PLACEMENT_RESOLVER_SOURCE
ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE = _ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE
ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE = _ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE
ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE = _ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE
ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA = _ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA
_DEFERRED_SIMULATION_APP: Any | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    return build_arg_parser(
        default_width=DEFAULT_WIDTH,
        default_height=DEFAULT_HEIGHT,
        generated_scene_kinds=GENERATED_SCENE_KINDS,
        segmentation_data_types=ISAAC_SEGMENTATION_DATA_TYPES,
    ).parse_args(argv)


type _IsaacWorkerCommand = Callable[[argparse.Namespace, dict[str, Any]], dict[str, Any]]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.command == "init":
        try:
            result = init_state(args)
        except Exception:
            traceback.print_exc()
            if _DEFERRED_SIMULATION_APP is not None:
                sys.stdout.flush()
                sys.stderr.flush()
                os._exit(1)
            raise
        return _finish_command(result)
    handler = _STATE_COMMANDS.get(args.command)
    if handler is None:  # pragma: no cover - argparse prevents this.
        raise ValueError(f"unsupported command: {args.command}")
    result = handler(args, read_state(args.state_path))
    return _finish_command(result)


def _finish_command(result: dict[str, Any]) -> int:
    print(json.dumps(result, sort_keys=True), flush=True)
    if _DEFERRED_SIMULATION_APP is not None:
        # Isaac/Omniverse shutdown can hang after the render artifacts and JSON
        # result are already written. The worker is one-shot, so prefer a hard
        # successful exit over turning completed captures into parent timeouts.
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
    return 0


def _close_deferred_simulation_app() -> None:
    global _DEFERRED_SIMULATION_APP
    if _DEFERRED_SIMULATION_APP is None:
        return
    simulation_app = _DEFERRED_SIMULATION_APP
    _DEFERRED_SIMULATION_APP = None
    simulation_app.close(wait_for_replicator=False, skip_cleanup=True)


def init_state(args: argparse.Namespace) -> dict[str, Any]:
    args.scene_index = _effective_scene_index(args)
    generated_mess_manifest = _load_generated_mess_manifest(args.generated_mess_manifest_path)
    scenario = _scenario_for_init(args, generated_mess_manifest=generated_mess_manifest)
    scenario_source = _scenario_source(args)
    real_smoke = None
    if args.runtime_mode == "real":
        try:
            real_smoke = real_runtime_smoke(args, scenario)
        except Exception as exc:
            raise RuntimeError(
                "Real Isaac runtime smoke failed before backend init could prove "
                "renderer/USD evidence. Run `just agent::harness "
                "molmo-isaac-runtime-preflight` first and keep CI-only protocol "
                "tests on ROBOCLAWS_ISAACLAB_RUNTIME_MODE=fake."
            ) from exc
    runtime = runtime_diagnostics(args.runtime_mode, real_smoke=real_smoke)
    scene_load = scene_load_diagnostics(
        args.runtime_mode,
        args.scene_source,
        args.scene_index,
        real_smoke=real_smoke,
    )
    scene_usd = str(scene_load["scene_usd"])
    object_index = _object_index(scenario)
    receptacle_index = _receptacle_index(scenario)
    scene_index_diagnostics: dict[str, Any] = {
        "status": "placeholder_mapping",
        "source": "scenario_fixture",
        "object_candidate_count": len(object_index),
        "receptacle_candidate_count": len(receptacle_index),
        "blockers": ["Object and receptacle USD prim paths are deterministic placeholders."],
    }
    if real_smoke is not None:
        scene_index_diagnostics = _dict(real_smoke.get("scene_index_diagnostics"))
        object_index = _index_or_default(real_smoke.get("object_index"), object_index)
        receptacle_index = _index_or_default(real_smoke.get("receptacle_index"), receptacle_index)
    room_outlines = _room_outlines_from_scene_index_diagnostics(scene_index_diagnostics)
    if not room_outlines:
        room_outlines = _fallback_room_outlines_from_indices(
            scenario=scenario,
            object_index=object_index,
            receptacle_index=receptacle_index,
        )
        scene_index_diagnostics["room_outline_count"] = len(room_outlines)
        scene_index_diagnostics["room_outlines"] = room_outlines
    scene_binding_diagnostics = _scene_binding_diagnostics(
        runtime_mode=args.runtime_mode,
        scenario=scenario,
        object_index=object_index,
        receptacle_index=receptacle_index,
        real_smoke=real_smoke,
    )
    scene_specific_scenario = _scene_specific_scenario_if_needed(
        args=args,
        generated_mess_manifest=generated_mess_manifest,
        scene_binding_diagnostics=scene_binding_diagnostics,
        object_index=object_index,
        receptacle_index=receptacle_index,
        real_smoke=real_smoke,
    )
    if scene_specific_scenario is not None:
        scenario = scene_specific_scenario
        scenario_source = "isaac_scene_index"
        scene_binding_diagnostics = _scene_binding_diagnostics(
            runtime_mode=args.runtime_mode,
            scenario=scenario,
            object_index=object_index,
            receptacle_index=receptacle_index,
            real_smoke=real_smoke,
        )
    segmentation = segmentation_diagnostics(
        runtime_mode=args.runtime_mode,
        real_smoke=real_smoke,
        scene_binding_diagnostics=scene_binding_diagnostics,
    )
    mapping_gaps = mapping_gap_diagnostics(
        runtime_mode=args.runtime_mode,
        map_bundle_dir=args.map_bundle_dir,
        real_smoke=real_smoke,
        scene_binding_diagnostics=scene_binding_diagnostics,
        segmentation=segmentation,
    )
    runtime["scenario_source"] = scenario_source
    initial_receptacle_id = _initial_receptacle_id(scenario)
    before_path = args.run_dir / "isaac_runtime_smoke.png"
    if real_smoke is not None:
        before_path = Path(str(real_smoke["image_path"]))
        if not before_path.is_file():
            raise RuntimeError(f"real Isaac smoke image is missing: {before_path}")
    state = {
        "schema": STATE_SCHEMA,
        "backend": ISAACLAB_SUBPROCESS_BACKEND,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "runtime": runtime,
        "scene_load": scene_load,
        "scene_source": args.scene_source,
        "scene_index": args.scene_index,
        "scene_usd": scene_usd,
        "scenario_source": scenario_source,
        "real_runtime_smoke": real_smoke,
        "requested_generated_mess_count": args.generated_mess_count,
        "scenario": scenario.public_payload(),
        "private_manifest": scenario.private_manifest.to_private_dict(),
        "generated_mess_manifest": generated_mess_manifest,
        "locations": scenario.object_locations(),
        "held_object_id": None,
        "current_receptacle_id": initial_receptacle_id,
        "open_receptacle_ids": [],
        "containment": {},
        "object_pose_overrides": {},
        "mess_placement_diagnostics": [],
        "tool_event_counts": {},
        "placement_diagnostics": [],
        "mapping_gaps": mapping_gaps,
        "object_index": object_index,
        "receptacle_index": receptacle_index,
        "room_outlines": room_outlines,
        "scene_index_diagnostics": scene_index_diagnostics,
        "scene_binding_diagnostics": scene_binding_diagnostics,
        "robot_view_images": _real_smoke_robot_view_images(real_smoke),
        "robot_view_provenance": _robot_view_provenance(args.runtime_mode, real_smoke),
        "native_render_diagnostics": _dict(
            _dict(runtime.get("rendering")).get("native_render_diagnostics")
        ),
        "segmentation": segmentation,
        "robot": _robot_payload(args.robot_name) if args.include_robot else None,
        "robot_import": _rby1m_robot_import_plan(args.robot_name) if args.include_robot else None,
    }
    _seed_generated_mess_placements(state)
    state["current_receptacle_id"] = _first_target_object_location(state) or initial_receptacle_id
    state["semantic_pose_state"] = _initial_semantic_pose_state_from_state(state)
    args.run_dir.mkdir(parents=True, exist_ok=True)
    write_state(args.state_path, state)
    if real_smoke is None:
        _write_placeholder_image(
            before_path,
            title="Isaac Lab runtime smoke",
            subtitle=runtime["renderer_mode"],
            state=state,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
        )
    return {
        "ok": True,
        "tool": "init",
        "backend": ISAACLAB_SUBPROCESS_BACKEND,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "scenario": state["scenario"],
        "private_manifest": state["private_manifest"],
        "generated_mess_manifest": state.get("generated_mess_manifest") or None,
        "runtime": runtime,
        "scene_usd": state["scene_usd"],
        "scene_load": scene_load,
        "scene_index": args.scene_index,
        "scenario_source": scenario_source,
        "scene_index_diagnostics": scene_index_diagnostics,
        "scene_binding_diagnostics": scene_binding_diagnostics,
        "object_index": state["object_index"],
        "receptacle_index": state["receptacle_index"],
        "mapping_gaps": mapping_gaps,
        "segmentation": state["segmentation"],
        "native_render_diagnostics": state["native_render_diagnostics"],
        "requested_generated_mess_count": args.generated_mess_count,
        "generated_mess_count": len(state["private_manifest"]["targets"]),
        "robot": state["robot"],
        "robot_import": state["robot_import"],
        "artifacts": {
            "runtime_smoke_image": str(before_path),
            "robot_view_images": state["robot_view_images"],
        },
    }


def _require_isaac_import() -> None:
    try:
        import isaaclab  # noqa: F401
    except Exception as exc:
        raise RuntimeError(
            "Isaac Lab runtime is unavailable. Install Isaac Sim / Isaac Lab in "
            ".venv-isaaclab/ or set ROBOCLAWS_ISAACLAB_RUNTIME_MODE=fake for "
            "CI protocol tests that do not claim renderer proof."
        ) from exc


def real_runtime_smoke(
    args: argparse.Namespace,
    scenario: CleanupScenario,
) -> dict[str, Any]:
    """Launch Isaac Lab and capture the minimal renderer/USD proof for Phase A.

    This function intentionally stays behind the worker subprocess. Normal
    Roboclaws imports must not import Isaac packages or start Omniverse.
    """

    _require_isaac_import()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    smoke_image = args.run_dir / "isaac_runtime_smoke.png"
    robot_view_paths = _runtime_smoke_robot_view_paths(args.run_dir, smoke_image=smoke_image)
    if args.scene_usd_path is not None:
        scene_usd = args.scene_usd_path
        if not scene_usd.is_file():
            raise RuntimeError(f"local Isaac scene USD is missing: {scene_usd}")
        loaded_asset_kind = "local_scene_usd"
    else:
        scene_usd = args.run_dir / _generated_scene_filename(args.generated_scene_kind)
        loaded_asset_kind = "generated_runtime_smoke_usd"
    robot_import = _rby1m_robot_import_plan(args.robot_name) if args.include_robot else {}

    simulation_app = None
    render_steps = 0
    scene_index_diagnostics: dict[str, Any] | None = None
    stage_prim_count = 0
    from isaaclab.app import AppLauncher

    launcher_args = _isaac_app_launcher_args(AppLauncher)
    app_launcher = AppLauncher(launcher_args)
    simulation_app = app_launcher.app
    global _DEFERRED_SIMULATION_APP
    _DEFERRED_SIMULATION_APP = simulation_app

    # Isaac Sim requires that Omniverse/pxr modules are not imported before
    # SimulationApp starts. Generate and inspect USD only after AppLauncher
    # owns the Kit bootstrap.
    if args.scene_usd_path is None:
        _write_generated_runtime_smoke_usd(
            scene_usd,
            scenario,
            scene_kind=args.generated_scene_kind,
        )
    scene_index_diagnostics = _inspect_usd_scene_index(scene_usd)
    stage_prim_count = int(scene_index_diagnostics["stage_prim_count"])

    capture = _capture_isaac_lab_camera_views(
        scene_usd=scene_usd,
        view_paths=robot_view_paths,
        width=DEFAULT_WIDTH,
        height=DEFAULT_HEIGHT,
        simulation_app=simulation_app,
        robot_import=robot_import,
        include_segmentation=args.enable_segmentation,
        segmentation_data_types=tuple(args.segmentation_data_type or ISAAC_SEGMENTATION_DATA_TYPES),
        semantic_filter=tuple(args.segmentation_semantic_filter or ("class",)),
        scene_index_diagnostics=scene_index_diagnostics,
    )
    render_steps = int(capture["render_steps"])
    robot_view_images = dict(capture["robot_view_images"])
    segmentation = _dict(capture.get("segmentation"))

    if not smoke_image.is_file():
        raise RuntimeError(f"Isaac Lab camera capture did not write {smoke_image}")
    if scene_index_diagnostics is None:
        raise RuntimeError("Isaac Lab runtime smoke did not inspect the USD scene index.")
    missing_views = sorted(
        key for key in ROBOT_VIEW_KEYS if not Path(str(robot_view_images.get(key, ""))).is_file()
    )
    if missing_views:
        raise RuntimeError(f"Isaac Lab robot view capture missed views: {', '.join(missing_views)}")
    return {
        "image_path": str(smoke_image),
        "scene_usd": str(scene_usd),
        "loaded_asset_kind": loaded_asset_kind,
        "generated_scene_kind": args.generated_scene_kind if args.scene_usd_path is None else "",
        "requested_scene_source": args.scene_source,
        "requested_scene_index": args.scene_index,
        "requested_molmospaces_scene_usd": _scene_usd_path(args.scene_source, args.scene_index),
        "isaac_lab_version": _module_version("isaaclab"),
        "isaac_sim_version": _module_version("isaacsim"),
        "renderer_mode": REAL_SMOKE_RENDERER_MODE,
        "capture_method": REAL_SMOKE_CAPTURE_METHOD,
        "robot_view_capture_method": REAL_ROBOT_VIEW_CAPTURE_METHOD,
        "robot_view_images": robot_view_images,
        "robot_import": robot_import,
        "robot_view_uses_mounted_head_camera": bool(
            capture.get("robot_view_uses_mounted_head_camera")
        ),
        "camera_resolution": [DEFAULT_WIDTH, DEFAULT_HEIGHT],
        "scene_bounds": capture.get("scene_bounds"),
        "stage_prim_count": stage_prim_count,
        "render_steps": render_steps,
        "scene_index_diagnostics": scene_index_diagnostics,
        "object_index": scene_index_diagnostics["object_index"],
        "receptacle_index": scene_index_diagnostics["receptacle_index"],
        "segmentation": segmentation,
        "native_render_diagnostics": _dict(capture.get("native_render_diagnostics")),
    }


def capture_semantic_pose_robot_views(
    *,
    state: dict[str, Any],
    scene_usd: Path,
    view_paths: dict[str, Path],
    width: int,
    height: int,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
    color_profile_override: dict[str, Any] | None = None,
    render_settle_frames: int = 0,
    isaac_aa_op: int | None = None,
    isaac_tonemap_op: int | None = None,
    isaac_exposure_bias: float | None = None,
    isaac_colorcorr_gain: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    _require_isaac_import()
    from isaaclab.app import AppLauncher

    launcher_args = _isaac_app_launcher_args(AppLauncher)
    app_launcher = AppLauncher(launcher_args)
    simulation_app = app_launcher.app
    global _DEFERRED_SIMULATION_APP
    _DEFERRED_SIMULATION_APP = simulation_app
    capture = _capture_isaac_lab_camera_views(
        scene_usd=scene_usd,
        view_paths=view_paths,
        width=width,
        height=height,
        simulation_app=simulation_app,
        robot_import=_dict(state.get("robot_import")),
        semantic_pose_state=_dict(state.get("semantic_pose_state")),
        color_profile_override=color_profile_override,
        render_settle_frames=render_settle_frames,
        isaac_aa_op=isaac_aa_op,
        isaac_tonemap_op=isaac_tonemap_op,
        isaac_exposure_bias=isaac_exposure_bias,
        isaac_colorcorr_gain=isaac_colorcorr_gain,
    )
    capture["simulation_app_reuse_token"] = simulation_app
    return capture


def _isaac_app_launcher_args(app_launcher_type: Any) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    app_launcher_type.add_app_launcher_args(parser)
    return parser.parse_args(
        [
            "--headless",
            "--enable_cameras",
            "--width",
            str(DEFAULT_WIDTH),
            "--height",
            str(DEFAULT_HEIGHT),
        ]
    )


def _inspect_usd_scene_index(usd_path: Path) -> dict[str, Any]:
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"Isaac USD stage could not be opened for indexing: {usd_path}")

    object_index: dict[str, dict[str, Any]] = {}
    receptacle_index: dict[str, dict[str, Any]] = {}
    room_outlines: list[dict[str, Any]] = []
    prim_paths_by_name: dict[str, list[str]] = {}
    stage_prim_count = 0
    for prim in stage.Traverse():
        stage_prim_count += 1
        prim_path = str(prim.GetPath())
        prim_paths_by_name.setdefault(prim.GetName(), []).append(prim_path)
        handle = _usd_handle_from_prim(prim_path, object_index, receptacle_index)
        room_outline = _room_outline_from_usd_prim(
            prim_path,
            prim,
            usd_geom=UsdGeom,
        )
        if room_outline is not None:
            room_outlines.append(room_outline)
        if _is_object_prim_path(prim_path):
            object_index[handle] = _usd_index_entry(prim_path, prim.GetName(), "object")
        elif _is_receptacle_prim_path(prim_path):
            receptacle_index[handle] = {
                **_usd_index_entry(prim_path, prim.GetName(), "receptacle"),
                "support_pose": _pose_near(handle),
            }
    _merge_molmospaces_metadata_index(
        usd_path=usd_path,
        prim_paths_by_name=prim_paths_by_name,
        object_index=object_index,
        receptacle_index=receptacle_index,
    )
    _annotate_usd_index_geometry(
        usd_path=usd_path,
        stage=stage,
        object_index=object_index,
        receptacle_index=receptacle_index,
        usd_geom=UsdGeom,
    )

    blockers = []
    if not object_index:
        blockers.append("No movable-object USD prim candidates matched current path heuristics.")
    if not receptacle_index:
        blockers.append(
            "No receptacle/support USD prim candidates matched current path heuristics."
        )
    return {
        "schema": "isaac_usd_scene_index_v1",
        "status": "indexed" if not blockers else "partial",
        "source": str(usd_path),
        "stage_prim_count": stage_prim_count,
        "object_candidate_count": len(object_index),
        "receptacle_candidate_count": len(receptacle_index),
        "room_outline_count": len(room_outlines),
        "room_outlines": sorted(room_outlines, key=lambda item: str(item.get("room_id") or "")),
        "object_index": object_index,
        "receptacle_index": receptacle_index,
        "blockers": blockers,
    }


def _annotate_usd_index_geometry(
    *,
    usd_path: Path,
    stage: Any,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    usd_geom: Any,
) -> None:
    for index in (object_index, receptacle_index):
        for entry in index.values():
            prim_path = str(entry.get("usd_prim_path") or "")
            if not prim_path:
                entry.update(
                    {
                        "prim_type": "",
                        "valid_stage_prim": False,
                        "has_renderable_geometry": False,
                        "renderable_descendant_count": 0,
                        "mesh_descendant_count": 0,
                        "authored_reference_count": 0,
                        "missing_referenced_asset_count": 0,
                        "missing_referenced_assets": [],
                        "geometry_status": "missing_prim_path",
                    }
                )
                continue
            prim = stage.GetPrimAtPath(prim_path)
            diagnostics = _usd_prim_geometry_diagnostics(
                usd_path=usd_path,
                prim=prim,
                usd_geom=usd_geom,
            )
            entry.update(diagnostics)
            if str(entry.get("kind") or "") == "receptacle" or isinstance(
                entry.get("support_pose"), dict
            ):
                support_surfaces = _usd_receptacle_support_surfaces(prim=prim, usd_geom=usd_geom)
                if support_surfaces:
                    entry["support_surfaces"] = support_surfaces
                support_pose = _support_pose_from_usd_bounds(
                    entry.get("usd_world_bounds"),
                    fallback=_dict(entry.get("support_pose")),
                )
                if support_surfaces:
                    support_pose = _support_pose_from_support_surface(
                        support_surfaces[0],
                        fallback=support_pose,
                    )
                if support_pose is not None:
                    entry["support_pose"] = support_pose


def _usd_prim_geometry_diagnostics(*, usd_path: Path, prim: Any, usd_geom: Any) -> dict[str, Any]:
    if not prim or not prim.IsValid():
        return {
            "prim_type": "",
            "valid_stage_prim": False,
            "has_renderable_geometry": False,
            "renderable_descendant_count": 0,
            "mesh_descendant_count": 0,
            "authored_reference_count": 0,
            "missing_referenced_asset_count": 0,
            "missing_referenced_assets": [],
            "geometry_status": "missing_stage_prim",
        }
    gprim_type = getattr(usd_geom, "Gprim", None)
    renderable_descendant_count = 0
    mesh_descendant_count = 0
    for descendant in _iter_usd_prim_range(prim):
        if gprim_type is not None and descendant.IsA(gprim_type):
            renderable_descendant_count += 1
        if str(descendant.GetTypeName() or "") == "Mesh":
            mesh_descendant_count += 1
    reference_assets = _authored_reference_asset_paths(usd_path=usd_path, prim=prim)
    missing_assets = [asset for asset in reference_assets if _local_reference_asset_missing(asset)]
    has_renderable_geometry = renderable_descendant_count > 0
    if has_renderable_geometry:
        geometry_status = "renderable"
    elif missing_assets:
        geometry_status = "missing_referenced_geometry"
    else:
        geometry_status = "no_renderable_descendants"
    world_bounds = _usd_world_bounds(prim, usd_geom=usd_geom)
    world_root_position = _usd_world_root_position(prim, usd_geom=usd_geom)
    return {
        "prim_type": str(prim.GetTypeName() or ""),
        "valid_stage_prim": True,
        "has_renderable_geometry": has_renderable_geometry,
        "renderable_descendant_count": renderable_descendant_count,
        "mesh_descendant_count": mesh_descendant_count,
        "authored_reference_count": len(reference_assets),
        "missing_referenced_asset_count": len(missing_assets),
        "missing_referenced_assets": missing_assets[:5],
        "geometry_status": geometry_status,
        "is_instanceable": bool(prim.IsInstanceable()),
        "is_instance": bool(prim.IsInstance()),
        "usd_world_bounds": world_bounds,
        "usd_world_root_position": world_root_position,
    }


def _usd_world_bounds(prim: Any, *, usd_geom: Any) -> dict[str, Any] | None:
    from pxr import Usd

    bbox_cache = usd_geom.BBoxCache(
        Usd.TimeCode.Default(),
        [usd_geom.Tokens.default_, usd_geom.Tokens.render, usd_geom.Tokens.proxy],
    )
    bbox = bbox_cache.ComputeWorldBound(prim).ComputeAlignedBox()
    min_point = [float(value) for value in bbox.GetMin()]
    max_point = [float(value) for value in bbox.GetMax()]
    size = [max_v - min_v for min_v, max_v in zip(min_point, max_point, strict=True)]
    if any(not math.isfinite(value) for value in [*min_point, *max_point, *size]):
        return None
    if max(size) <= 0:
        return None
    center = [(min_v + max_v) / 2.0 for min_v, max_v in zip(min_point, max_point, strict=True)]
    return {
        "min": _round_vec3(min_point),
        "max": _round_vec3(max_point),
        "center": _round_vec3(center),
        "size": _round_vec3(size),
    }


def _usd_world_root_position(prim: Any, *, usd_geom: Any) -> list[float] | None:
    try:
        transform = usd_geom.Xformable(prim).ComputeLocalToWorldTransform(0.0)
        position = transform.Transform((0.0, 0.0, 0.0))
    except Exception:
        return None
    values = [float(value) for value in position]
    if any(not math.isfinite(value) for value in values):
        return None
    return _round_vec3(values)


def _usd_receptacle_support_surfaces(*, prim: Any, usd_geom: Any) -> list[dict[str, Any]]:
    return usd_receptacle_support_surfaces(
        prim=prim,
        usd_geom=usd_geom,
        world_bounds=_usd_world_bounds,
        iter_prim_range=_iter_usd_prim_range,
    )


def _room_outline_from_usd_prim(
    prim_path: str,
    prim: Any,
    *,
    usd_geom: Any,
) -> dict[str, Any] | None:
    return room_outline_from_usd_prim(
        prim_path,
        prim,
        usd_geom=usd_geom,
        world_bounds=_usd_world_bounds,
    )


def _iter_usd_prim_range(prim: Any) -> Iterable[Any]:
    from pxr import Usd

    return Usd.PrimRange(prim)


def _dedupe(values: Any) -> list[str]:
    seen = set()
    result = []
    for value in values:
        item = str(value or "")
        if not item or item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def _runtime_smoke_robot_view_paths(
    run_dir: Path,
    *,
    smoke_image: Path,
) -> dict[str, Path]:
    return {
        "fpv": smoke_image,
        "chase": run_dir / "isaac_runtime_smoke.chase.png",
        "map": run_dir / "isaac_runtime_smoke.map.png",
        "verify": run_dir / "isaac_runtime_smoke.verify.png",
    }


def _capture_isaac_lab_camera_views(
    *,
    scene_usd: Path,
    view_paths: dict[str, Path],
    width: int,
    height: int,
    simulation_app: Any,
    robot_import: dict[str, Any] | None = None,
    include_segmentation: bool = False,
    segmentation_data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    semantic_filter: tuple[str, ...] = ("class",),
    scene_index_diagnostics: dict[str, Any] | None = None,
    semantic_pose_state: dict[str, Any] | None = None,
    color_profile_override: dict[str, Any] | None = None,
    render_settle_frames: int = 0,
    isaac_aa_op: int | None = None,
    isaac_tonemap_op: int | None = None,
    isaac_exposure_bias: float | None = None,
    isaac_colorcorr_gain: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    return capture_isaac_lab_camera_views(
        request=IsaacCameraCaptureRequest(
            scene_usd=scene_usd,
            view_paths=view_paths,
            width=width,
            height=height,
            simulation_app=simulation_app,
            robot_import=_dict(robot_import),
            include_segmentation=include_segmentation,
            segmentation_data_types=segmentation_data_types,
            semantic_filter=semantic_filter,
            scene_index_diagnostics=scene_index_diagnostics,
            semantic_pose_state=_dict(semantic_pose_state),
            color_profile_override=color_profile_override,
            render_settle_frames=render_settle_frames,
            isaac_aa_op=isaac_aa_op,
            isaac_tonemap_op=isaac_tonemap_op,
            isaac_exposure_bias=isaac_exposure_bias,
            isaac_colorcorr_gain=isaac_colorcorr_gain,
            robot_view_keys=ROBOT_VIEW_KEYS,
            head_camera_prim=ISAAC_RBY1M_HEAD_CAMERA_PRIM,
            head_camera_vertical_fov_deg=RBY1M_HEAD_CAMERA_VERTICAL_FOV_DEG,
            head_camera_focal_length_mm=RBY1M_HEAD_CAMERA_FOCAL_LENGTH_MM,
            renderer_mode=REAL_SMOKE_RENDERER_MODE,
            capture_method=REAL_ROBOT_VIEW_CAPTURE_METHOD,
            default_lighting_profile=DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
        ),
        hooks=IsaacCameraCaptureHooks(
            wait_for_stage_load=_wait_for_stage_load,
            load_current_stage_payloads=_load_current_stage_payloads,
            apply_semantic_pose_state_to_stage=_apply_semantic_pose_state_to_stage,
            ensure_rby1m_robot_on_stage=_ensure_rby1m_robot_on_stage,
            current_stage_bounds=_current_stage_bounds,
            ensure_capture_lighting=_ensure_capture_lighting,
            apply_scene_index_semantic_labels=_apply_scene_index_semantic_labels,
            semantic_label_application_not_requested=_semantic_label_application_not_requested,
            configure_rby1m_head_camera_lens=_configure_rby1m_head_camera_lens,
            horizontal_aperture_from_lens=_horizontal_aperture_from_lens,
            isaac_camera_view_poses=_isaac_camera_view_poses,
            isaac_settings_interface=_isaac_settings_interface,
            apply_isaac_capture_quality_overrides=_apply_isaac_capture_quality_overrides,
            isaac_native_render_diagnostics=_isaac_native_render_diagnostics,
            capture_quality_settings=_capture_quality_settings,
            camera_render_product_paths=_camera_render_product_paths,
            position_robot_for_head_camera_view=_position_robot_for_head_camera_view,
            usd_camera_diagnostics=_usd_camera_diagnostics,
            isaac_eye_target_camera_diagnostics=_isaac_eye_target_camera_diagnostics,
            robot_relative_chase_eye_target=_robot_relative_chase_eye_target,
            rgb_tensor_to_uint8=_rgb_tensor_to_uint8,
            image_has_variance=_image_has_variance,
            robot_view_color_profile=_robot_view_color_profile,
            camera_segmentation_view_diagnostics=_camera_segmentation_view_diagnostics,
            restore_isaac_capture_quality_overrides=_restore_isaac_capture_quality_overrides,
            camera_segmentation_capture_diagnostics=_camera_segmentation_capture_diagnostics,
            camera_segmentation_not_requested_diagnostics=(
                _camera_segmentation_not_requested_diagnostics
            ),
        ),
    )


def _capture_scene_camera_request_with_existing_sim(
    *,
    camera_request: dict[str, Any],
    output_dir: Path,
    width: int,
    height: int,
    sim: Any,
    sim_utils: Any,
    stage_utils: Any,
    camera_type: Any,
    camera_cfg_type: Any,
    torch: Any,
    np: Any,
    scene_bounds: dict[str, Any],
) -> dict[str, Any]:
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width = int(resolution["width"])
    height = int(resolution["height"])
    lighting_diagnostics = _ensure_capture_lighting(
        stage_utils,
        profile=camera_request.get("lighting_profile"),
    )
    lens = camera_request.get("lens") if isinstance(camera_request.get("lens"), dict) else {}
    color_profile = camera_request.get("color_profile") or {}
    focal_length = float(lens.get("focal_length_mm", 24.0))
    horizontal_aperture = _horizontal_aperture_from_lens(
        lens,
        width=width,
        height=height,
        focal_length=focal_length,
    )
    sim_utils.create_prim("/World/RoboclawsSceneRequestCameraRig", "Xform")
    camera = camera_type(
        cfg=camera_cfg_type(
            prim_path="/World/RoboclawsSceneRequestCameraRig/Camera",
            update_period=0.0,
            height=height,
            width=width,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=focal_length,
                focus_distance=4.0,
                horizontal_aperture=horizontal_aperture,
            ),
        )
    )
    sim.reset()
    native_render_diagnostics = _isaac_native_render_diagnostics(
        renderer_mode=REAL_SMOKE_RENDERER_MODE,
        capture_method="isaac_lab_camera_rgb_scene_probe",
        view_kind="scene_camera_request",
        render_resolution={"width": width, "height": height},
        camera_prim_paths=["/World/RoboclawsSceneRequestCameraRig/Camera"],
        render_product_paths=_camera_render_product_paths(camera),
        isaac_lab_isp_active=False,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    saved: dict[str, str] = {}
    shapes: dict[str, list[int]] = {}
    color_diagnostics: dict[str, dict[str, Any]] = {}
    views: list[dict[str, Any]] = []
    total_render_steps = 0
    for index, raw_spec in enumerate(camera_request.get("views") or [], start=1):
        spec = _isaac_scene_camera_view_spec(
            raw_spec,
            index=index,
            stage_utils=stage_utils,
        )
        position = torch.tensor([spec["eye"]], dtype=torch.float32, device=sim.device)
        target = torch.tensor([spec["target"]], dtype=torch.float32, device=sim.device)
        camera.set_world_poses_from_view(position, target)
        rgb_image = None
        for _ in range(24):
            sim.step()
            total_render_steps += 1
            camera.update(dt=sim.get_physics_dt())
            rgb_image = _rgb_tensor_to_uint8(camera.data.output.get("rgb"), np=np)
            if rgb_image is not None and _image_has_variance(rgb_image, np=np):
                break
        if rgb_image is None:
            raise RuntimeError(
                f"Isaac Lab camera did not produce an RGB tensor for {spec['view_id']}"
            )
        if not _image_has_variance(rgb_image, np=np):
            raise RuntimeError(f"Isaac Lab camera RGB tensor was blank for {spec['view_id']}")
        rgb_image, color_diagnostic = apply_camera_color_profile(
            rgb_image,
            np=np,
            profile=color_profile,
            backend="isaaclab-prepared-usd",
            view_id=str(spec["view_id"]),
        )
        output_path = output_dir / f"{spec['view_id']}.png"
        Image.fromarray(rgb_image, mode="RGB").save(output_path)
        saved[str(spec["view_id"])] = str(output_path)
        shapes[str(spec["view_id"])] = list(rgb_image.shape)
        color_diagnostics[str(spec["view_id"])] = color_diagnostic
        views.append(
            {
                **spec,
                "image_path": str(output_path),
                "shape": list(rgb_image.shape),
            }
        )
    return {
        "schema": "isaac_scene_camera_views_v1",
        "camera_control_api": camera_request.get("api_name") or CAMERA_CONTROL_API_NAME,
        "camera_request_schema": camera_request.get("schema"),
        "calibration_status": camera_request.get("calibration_status"),
        "lighting_profile": camera_request.get("lighting_profile") or {},
        "color_profile": color_profile,
        "color_management": color_diagnostics,
        "lighting_diagnostics": lighting_diagnostics,
        "native_render_diagnostics": native_render_diagnostics,
        "lens": camera_request.get("lens") or {},
        "derived_lens": {
            "focal_length_mm": focal_length,
            "horizontal_aperture_mm": horizontal_aperture,
        },
        "render_steps": total_render_steps,
        "scene_bounds": scene_bounds,
        "views": views,
        "images": saved,
        "shapes": shapes,
    }


def capture_scene_camera_views(
    *,
    scene_usd: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    output_dir: Path,
    width: int,
    height: int,
    semantic_pose_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from isaaclab.app import AppLauncher

    launcher_args = _isaac_app_launcher_args(AppLauncher)
    app_launcher = AppLauncher(launcher_args)
    simulation_app = app_launcher.app
    global _DEFERRED_SIMULATION_APP
    _DEFERRED_SIMULATION_APP = simulation_app
    return _capture_isaac_lab_scene_camera_views(
        scene_usd=scene_usd,
        camera_request=camera_request,
        output_dir=output_dir,
        width=width,
        height=height,
        simulation_app=simulation_app,
        semantic_pose_state=semantic_pose_state,
    )


def _capture_isaac_lab_scene_camera_views(
    *,
    scene_usd: Path,
    camera_request: dict[str, Any] | list[dict[str, Any]],
    output_dir: Path,
    width: int,
    height: int,
    simulation_app: Any,
    semantic_pose_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return capture_isaac_lab_scene_camera_views(
        request=IsaacSceneCameraCaptureRequest(
            scene_usd=scene_usd,
            camera_request=camera_request,
            output_dir=output_dir,
            width=width,
            height=height,
            simulation_app=simulation_app,
            semantic_pose_state=_dict(semantic_pose_state),
            renderer_mode=REAL_SMOKE_RENDERER_MODE,
        ),
        hooks=IsaacSceneCameraCaptureHooks(
            normalize_camera_control_request=normalize_camera_control_request,
            wait_for_stage_load=_wait_for_stage_load,
            load_current_stage_payloads=_load_current_stage_payloads,
            apply_semantic_pose_state_to_stage=_apply_semantic_pose_state_to_stage,
            current_stage_bounds=_current_stage_bounds,
            ensure_capture_lighting=_ensure_capture_lighting,
            horizontal_aperture_from_lens=_horizontal_aperture_from_lens,
            isaac_native_render_diagnostics=_isaac_native_render_diagnostics,
            camera_render_product_paths=_camera_render_product_paths,
            isaac_scene_camera_view_spec=_isaac_scene_camera_view_spec,
            rgb_tensor_to_uint8=_rgb_tensor_to_uint8,
            image_has_variance=_image_has_variance,
        ),
    )


def _apply_semantic_pose_state_to_stage(
    *,
    stage_utils: Any,
    semantic_pose_state: dict[str, Any] | None,
) -> dict[str, Any]:
    pose_state = _dict(semantic_pose_state)
    if not pose_state:
        return {
            "schema": "isaac_semantic_pose_stage_application_v1",
            "status": "not_requested",
            "applied_object_count": 0,
            "failed_object_count": 0,
            "rendered_to_usd": False,
        }
    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        raise RuntimeError("Isaac stage utils do not expose get_current_stage")
    stage = get_current_stage()
    if stage is None:
        raise RuntimeError("Isaac semantic-pose rerender has no current USD stage")
    from pxr import Gf, UsdGeom

    object_poses = _dict(pose_state.get("object_poses"))
    receptacle_index = _dict(pose_state.get("receptacle_index"))
    applied: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    for object_id, raw_pose in object_poses.items():
        pose = _dict(raw_pose)
        object_prim_path = str(pose.get("usd_prim_path") or "")
        support_id = str(pose.get("support_receptacle_id") or "")
        if not object_prim_path or pose.get("attached_to_robot") is True:
            continue
        object_prim = stage.GetPrimAtPath(object_prim_path)
        if not object_prim or not object_prim.IsValid():
            failed.append({"object_id": str(object_id), "reason": "missing_object_prim"})
            continue
        target = _semantic_pose_target_position(
            support_id=support_id,
            receptacle_index=receptacle_index,
            fallback_pose=_dict(pose),
        )
        if target is None:
            failed.append({"object_id": str(object_id), "reason": "missing_target_pose"})
            continue
        try:
            local_translate = _world_position_to_parent_local_translate(
                UsdGeom=UsdGeom,
                prim=object_prim,
                world_position=target,
            )
        except RuntimeError as exc:
            failed.append(
                {
                    "object_id": str(object_id),
                    "reason": "parent_local_transform_failed",
                    "detail": str(exc),
                }
            )
            continue
        try:
            translate_application = _set_usd_xform_translate(
                UsdGeom=UsdGeom,
                Gf=Gf,
                prim=object_prim,
                translate=local_translate,
            )
        except RuntimeError as exc:
            failed.append(
                {
                    "object_id": str(object_id),
                    "reason": "translate_authoring_failed",
                    "detail": str(exc),
                }
            )
            continue
        applied.append(
            {
                "object_id": str(object_id),
                "object_usd_prim_path": object_prim_path,
                "support_receptacle_id": support_id,
                "target_position": list(target),
                "authored_translate": list(local_translate),
                "authored_translate_frame": "parent_local",
                "translate_application_method": translate_application.get("method"),
                "authored_xform_op": translate_application.get("xform_op"),
            }
        )
    return {
        "schema": "isaac_semantic_pose_stage_application_v1",
        "status": "applied" if applied and not failed else ("partial" if applied else "blocked"),
        "applied_object_count": len(applied),
        "failed_object_count": len(failed),
        "applied_objects": applied,
        "failed_objects": failed,
        "rendered_to_usd": bool(applied) and not failed,
    }


def _world_position_to_parent_local_translate(
    *,
    UsdGeom: Any,
    prim: Any,
    world_position: tuple[float, float, float],
) -> tuple[float, float, float]:
    parent = prim.GetParent() if hasattr(prim, "GetParent") else None
    if parent is None or not parent:
        return tuple(float(value) for value in world_position)
    try:
        parent_world = UsdGeom.Xformable(parent).ComputeLocalToWorldTransform(0.0)
        world_to_parent = parent_world.GetInverse()
        local = world_to_parent.Transform(tuple(float(value) for value in world_position))
        return (float(local[0]), float(local[1]), float(local[2]))
    except Exception as exc:
        raise RuntimeError(
            "could not convert world semantic pose into parent-local USD frame"
        ) from exc


def _semantic_pose_target_position(
    *,
    support_id: str,
    receptacle_index: dict[str, Any],
    fallback_pose: dict[str, Any],
) -> tuple[float, float, float] | None:
    exact_position = _vec3(fallback_pose.get("position"))
    if exact_position is not None:
        return (exact_position[0], exact_position[1], exact_position[2])
    support = _dict(receptacle_index.get(support_id))
    pose = _dict(support.get("support_pose")) or fallback_pose
    try:
        x = float(pose.get("x"))
        y = float(pose.get("y"))
    except (TypeError, ValueError):
        return None
    try:
        z = float(pose.get("z") or 0.0)
    except (TypeError, ValueError):
        z = 0.0
    return (x, y, z + 0.18)


def _load_current_stage_payloads(stage_utils: Any) -> None:
    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return
    stage = get_current_stage()
    if stage is None:
        return
    try:
        stage.Load()
    except Exception:
        return


def _apply_scene_index_semantic_labels(
    *,
    stage_utils: Any,
    sim_utils: Any,
    scene_index_diagnostics: dict[str, Any] | None,
) -> dict[str, Any]:
    return apply_scene_index_semantic_labels(
        stage_utils=stage_utils,
        sim_utils=sim_utils,
        scene_index_diagnostics=scene_index_diagnostics,
        target_prim_resolver=_semantic_label_target_prims,
    )


def _camera_segmentation_view_diagnostics(
    camera: Any,
    *,
    data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    view_name: str,
    np: Any,
) -> dict[str, Any]:
    return camera_segmentation_view_diagnostics(
        camera,
        data_types=data_types,
        view_name=view_name,
        np=np,
        max_candidates=MAX_SEGMENTATION_CANDIDATES,
    )


def _camera_segmentation_capture_diagnostics(
    views: list[dict[str, Any]],
    *,
    requested_data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    semantic_label_application: dict[str, Any] | None = None,
    semantic_filter: str | list[str] | None = None,
) -> dict[str, Any]:
    return camera_segmentation_capture_diagnostics(
        views,
        requested_data_types=requested_data_types,
        semantic_label_application=semantic_label_application,
        semantic_filter=semantic_filter,
        max_candidates=MAX_SEGMENTATION_CANDIDATES,
    )


def _camera_segmentation_not_requested_diagnostics() -> dict[str, Any]:
    return camera_segmentation_not_requested_diagnostics(
        requested_data_types=ISAAC_SEGMENTATION_DATA_TYPES,
    )


def _current_stage_bounds(stage_utils: Any) -> dict[str, list[float]] | None:
    return current_stage_bounds(stage_utils)


def _ensure_capture_lighting(
    stage_utils: Any, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    return ensure_capture_lighting(stage_utils, profile)


def _normalized_vec3(value: Any) -> list[float] | None:
    return normalized_vec3(value)


def _isaac_distant_light_rotation_from_direction(direction: list[float]) -> list[float]:
    return isaac_distant_light_rotation_from_direction(direction)


def _scale_stage_light_intensities(
    stage: Any,
    light_paths: list[str],
    *,
    scale: float,
) -> list[dict[str, Any]]:
    return scale_stage_light_intensities(stage, light_paths, scale=scale)


def _robot_view_color_profile(override: dict[str, Any] | None = None) -> dict[str, Any]:
    return isaac_robot_view_color_profile(override)


def _stage_light_paths(
    stage: Any, *, exclude_prefix: str = "", light_api: Any | None = None
) -> list[str]:
    return stage_light_paths(stage, exclude_prefix=exclude_prefix, light_api=light_api)


def _prim_type_is_light(prim: Any) -> bool:
    return prim_type_is_light(prim)


def _isaac_camera_view_poses(
    *,
    torch: Any,
    device: Any,
    scene_bounds: dict[str, list[float]] | None = None,
    semantic_pose_state: dict[str, Any] | None = None,
) -> dict[str, tuple[Any, Any]]:
    return isaac_camera_view_poses(
        torch=torch,
        device=device,
        scene_bounds=scene_bounds,
        semantic_pose_state=semantic_pose_state,
    )


def _robot_relative_chase_eye_target(
    pose: dict[str, Any],
) -> tuple[tuple[float, float, float], tuple[float, float, float]] | None:
    return robot_relative_chase_eye_target(pose)


def _ensure_rby1m_robot_on_stage(
    *,
    stage_utils: Any,
    robot_import: dict[str, Any],
) -> dict[str, Any]:
    if robot_import.get("status") != "imported":
        return {
            "schema": "isaac_rby1m_robot_stage_reference_v1",
            "status": "not_available",
            "head_camera_prim_exists": False,
            "reason": robot_import.get("status") or "robot_not_requested",
        }
    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        raise RuntimeError("Isaac stage utils do not expose get_current_stage")
    stage = get_current_stage()
    if stage is None:
        raise RuntimeError("Isaac robot import has no current USD stage")
    from pxr import UsdGeom

    robot_prim_path = str(robot_import.get("stage_prim_path") or "/World/robot_0")
    head_camera_prim_path = str(
        robot_import.get("head_camera_prim_path") or ISAAC_RBY1M_HEAD_CAMERA_PRIM
    )
    robot_usd_path = Path(str(robot_import.get("usd_path") or ""))
    if not robot_usd_path.is_file():
        return {
            "schema": "isaac_rby1m_robot_stage_reference_v1",
            "status": "blocked",
            "head_camera_prim_exists": False,
            "robot_prim_path": robot_prim_path,
            "head_camera_prim_path": head_camera_prim_path,
            "reason": f"missing imported robot USD: {robot_usd_path}",
        }
    robot_prim = stage.GetPrimAtPath(robot_prim_path)
    if not robot_prim or not robot_prim.IsValid():
        robot_prim = UsdGeom.Xform.Define(stage, robot_prim_path).GetPrim()
        robot_prim.GetReferences().AddReference(str(robot_usd_path))
    head_camera_prim = stage.GetPrimAtPath(head_camera_prim_path)
    return {
        "schema": "isaac_rby1m_robot_stage_reference_v1",
        "status": "referenced",
        "robot_prim_path": robot_prim_path,
        "head_camera_prim_path": head_camera_prim_path,
        "robot_usd_path": str(robot_usd_path),
        "head_camera_prim_exists": bool(head_camera_prim and head_camera_prim.IsValid()),
    }


def _position_robot_for_head_camera_view(
    *,
    stage_utils: Any,
    scene_bounds: dict[str, list[float]] | None,
    semantic_pose_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return {
            "schema": "isaac_robot_head_camera_pose_application_v1",
            "status": "missing_stage_api",
        }
    stage = get_current_stage()
    if stage is None:
        return {"schema": "isaac_robot_head_camera_pose_application_v1", "status": "missing_stage"}
    robot_prim = stage.GetPrimAtPath("/World/robot_0")
    if not robot_prim or not robot_prim.IsValid():
        return {
            "schema": "isaac_robot_head_camera_pose_application_v1",
            "status": "missing_robot_prim",
            "robot_prim_path": "/World/robot_0",
        }
    from pxr import Gf, UsdGeom

    pose = _dict(_dict(semantic_pose_state).get("robot_pose"))
    pose_source = str(pose.get("pose_source") or "")
    if _has_xy(pose):
        position = (
            float(pose["x"]),
            float(pose["y"]),
            float(pose.get("z", 0.0)),
        )
        position_source = "semantic_pose_state.robot_pose"
    elif scene_bounds:
        center = scene_bounds["center"]
        size = scene_bounds["size"]
        span_x = max(float(size[0]), 1.5)
        span_y = max(float(size[1]), 1.5)
        floor_z = float(scene_bounds["min"][2])
        position = (float(center[0]) - span_x * 0.35, float(center[1]) - span_y * 0.55, floor_z)
        position_source = "scene_bounds_fallback"
    else:
        position = (1.35, -1.35, 0.0)
        position_source = "static_fallback"
    xform = UsdGeom.XformCommonAPI(robot_prim)
    xform.SetTranslate(Gf.Vec3d(*position))
    yaw_deg = _robot_pose_yaw_deg(pose)
    if yaw_deg is not None:
        xform.SetRotate(Gf.Vec3f(0.0, 0.0, yaw_deg))
    head_pitch = _optional_float(pose.get("head_pitch"))
    head_pitch_application = _apply_static_head_camera_pitch(
        stage=stage,
        head_pitch=head_pitch,
    )
    return {
        "schema": "isaac_robot_head_camera_pose_application_v1",
        "status": "applied",
        "robot_prim_path": "/World/robot_0",
        "position": [float(value) for value in position],
        "position_source": position_source,
        "pose_source": pose_source,
        "yaw_deg": yaw_deg,
        "yaw_source": "semantic_pose_state.robot_pose.theta_or_yaw_deg"
        if yaw_deg is not None
        else "not_available",
        "head_pitch": head_pitch,
        "head_pitch_source": str(pose.get("head_pitch_source") or ""),
        "head_pitch_applied": head_pitch_application.get("status") == "applied",
        "head_pitch_application": head_pitch_application,
        "head_pitch_note": _static_head_pitch_note(head_pitch_application),
    }


def _apply_static_head_camera_pitch(
    *,
    stage: Any,
    head_pitch: float | None,
) -> dict[str, Any]:
    if head_pitch is None:
        return {
            "schema": "isaac_static_head_camera_pitch_application_v1",
            "status": "not_requested",
            "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
        }
    head_camera_prim = stage.GetPrimAtPath(ISAAC_RBY1M_HEAD_CAMERA_PRIM)
    if not head_camera_prim or not head_camera_prim.IsValid():
        return {
            "schema": "isaac_static_head_camera_pitch_application_v1",
            "status": "missing_head_camera_prim",
            "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
            "head_pitch_rad": float(head_pitch),
        }
    from pxr import Gf, UsdGeom

    position, quat = _static_head_camera_pose_for_pitch(float(head_pitch))
    xform = UsdGeom.Xformable(head_camera_prim)
    xform.ClearXformOpOrder()
    xform.AddTranslateOp().Set(Gf.Vec3d(*position))
    xform.AddOrientOp().Set(Gf.Quatf(quat[0], Gf.Vec3f(*quat[1:])))
    xform.AddScaleOp().Set(Gf.Vec3f(1.0, 1.0, 1.0))
    return {
        "schema": "isaac_static_head_camera_pitch_application_v1",
        "status": "applied",
        "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
        "head_pitch_rad": round(float(head_pitch), 6),
        "head_pitch_axis": [0.0, 1.0, 0.0],
        "head_pitch_joint": "head_1",
        "head_pitch_pivot_m": [round(float(value), 6) for value in RBY1M_HEAD_PITCH_PIVOT_M],
        "zero_position_m": [round(float(value), 6) for value in RBY1M_HEAD_CAMERA_ZERO_POSITION_M],
        "applied_position_m": [round(float(value), 6) for value in position],
        "applied_quat_wxyz": [round(float(value), 6) for value in quat],
        "pose_source": "static_usd_head_camera_local_transform_with_mujoco_head_1_pitch",
    }


def _static_head_camera_pose_for_pitch(
    head_pitch: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float, float]]:
    return static_head_camera_pose_for_pitch(head_pitch)


def _rotate_point_y_about_pivot(
    point: tuple[float, float, float],
    *,
    pivot: tuple[float, float, float],
    angle_rad: float,
) -> tuple[float, float, float]:
    return rotate_point_y_about_pivot(point, pivot=pivot, angle_rad=angle_rad)


def _quat_from_axis_angle(
    axis: tuple[float, float, float],
    angle_rad: float,
) -> tuple[float, float, float, float]:
    return quat_from_axis_angle(axis, angle_rad)


def _quat_multiply(
    left: tuple[float, float, float, float],
    right: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return quat_multiply(left, right)


def _normalize_quat(
    quat: tuple[float, float, float, float],
) -> tuple[float, float, float, float]:
    return normalize_quat(quat)


def _static_head_pitch_note(head_pitch_application: dict[str, Any]) -> str:
    if head_pitch_application.get("status") == "applied":
        return (
            "Isaac currently uses a static visual robot USD, so it cannot drive the "
            "articulated head_1 joint. For robot-view parity it rewrites the mounted "
            "head_camera prim local transform with the same Y-axis head pitch used by "
            "MuJoCo before FPV capture."
        )
    return (
        "The current static Isaac robot USD has a mounted head_camera prim but could not "
        "apply a static head pitch correction for this capture; inspect "
        "head_pitch_application before treating FPV as articulated parity."
    )


def _usd_camera_diagnostics(
    *,
    stage_utils: Any,
    prim_path: str,
    view_name: str,
    width: int,
    height: int,
    robot_pose_application: dict[str, Any] | None = None,
    lens_application: dict[str, Any] | None = None,
) -> dict[str, Any]:
    try:
        stage = stage_utils.get_current_stage()
        prim = stage.GetPrimAtPath(prim_path) if stage is not None else None
        if not prim or not prim.IsValid():
            return {
                "schema": "isaac_usd_camera_diagnostics_v1",
                "status": "missing_camera_prim",
                "view_name": view_name,
                "prim_path": prim_path,
            }
        from pxr import UsdGeom

        camera = UsdGeom.Camera(prim)
        xform = UsdGeom.Xformable(prim).ComputeLocalToWorldTransform(0.0)
        focal_length = _usd_attr_float(camera.GetFocalLengthAttr())
        horizontal_aperture = _usd_attr_float(camera.GetHorizontalApertureAttr())
        fov = _usd_camera_fov_metadata(
            focal_length=focal_length,
            horizontal_aperture=horizontal_aperture,
            width=width,
            height=height,
        )
        return {
            "schema": "isaac_usd_camera_diagnostics_v1",
            "status": "ready",
            "view_name": view_name,
            "camera_type": "usd_camera_prim",
            "prim_path": prim_path,
            "world_matrix_rowmajor": _matrix4d_rowmajor(xform),
            "focal_length_mm": focal_length,
            "horizontal_aperture_mm": horizontal_aperture,
            **fov,
            "clipping_range": _usd_vec(camera.GetClippingRangeAttr()),
            "render_resolution": {"width": width, "height": height},
            "robot_pose_stage_application": _dict(robot_pose_application),
            "lens_application": _dict(lens_application),
        }
    except Exception as exc:
        return {
            "schema": "isaac_usd_camera_diagnostics_v1",
            "status": "unavailable",
            "view_name": view_name,
            "prim_path": prim_path,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _isaac_eye_target_camera_diagnostics(
    *,
    view_name: str,
    positions: Any,
    targets: Any,
    width: int,
    height: int,
    camera_basis: str = "scene_bounds_eye_target",
) -> dict[str, Any]:
    focal_length = RBY1M_HEAD_CAMERA_FOCAL_LENGTH_MM
    horizontal_aperture = _horizontal_aperture_from_lens(
        {"vertical_fov_deg": RBY1M_HEAD_CAMERA_VERTICAL_FOV_DEG},
        width=width,
        height=height,
        focal_length=focal_length,
    )
    fov = _usd_camera_fov_metadata(
        focal_length=focal_length,
        horizontal_aperture=horizontal_aperture,
        width=width,
        height=height,
    )
    return {
        "schema": "isaac_eye_target_camera_diagnostics_v1",
        "status": "ready",
        "view_name": view_name,
        "camera_type": "eye_target_scene_camera",
        "camera_basis": camera_basis,
        "eye": _tensor_first_vec3(positions),
        "target": _tensor_first_vec3(targets),
        "focal_length_mm": focal_length,
        "horizontal_aperture_mm": horizontal_aperture,
        **fov,
        "render_resolution": {"width": width, "height": height},
    }


def _configure_rby1m_head_camera_lens(
    *,
    stage_utils: Any,
    width: int,
    height: int,
) -> dict[str, Any]:
    try:
        from pxr import UsdGeom

        stage = stage_utils.get_current_stage()
        prim = stage.GetPrimAtPath(ISAAC_RBY1M_HEAD_CAMERA_PRIM) if stage is not None else None
        if not prim or not prim.IsValid():
            return {
                "schema": "isaac_rby1m_head_camera_lens_application_v1",
                "status": "missing_head_camera_prim",
                "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
            }
        focal_length = RBY1M_HEAD_CAMERA_FOCAL_LENGTH_MM
        horizontal_aperture = _horizontal_aperture_from_lens(
            {"vertical_fov_deg": RBY1M_HEAD_CAMERA_VERTICAL_FOV_DEG},
            width=width,
            height=height,
            focal_length=focal_length,
        )
        camera = UsdGeom.Camera(prim)
        camera.CreateFocalLengthAttr(focal_length).Set(focal_length)
        camera.CreateHorizontalApertureAttr(horizontal_aperture).Set(horizontal_aperture)
        return {
            "schema": "isaac_rby1m_head_camera_lens_application_v1",
            "status": "applied",
            "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
            "source_camera_name": "robot_0/head_camera",
            "source_vertical_fov_deg": RBY1M_HEAD_CAMERA_VERTICAL_FOV_DEG,
            "focal_length_mm": round(focal_length, 6),
            "horizontal_aperture_mm": round(horizontal_aperture, 6),
            "render_resolution": {"width": int(width), "height": int(height)},
        }
    except Exception as exc:
        return {
            "schema": "isaac_rby1m_head_camera_lens_application_v1",
            "status": "unavailable",
            "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
            "reason": f"{type(exc).__name__}: {exc}",
        }


def _usd_camera_fov_metadata(
    *,
    focal_length: float | None,
    horizontal_aperture: float | None,
    width: int,
    height: int,
) -> dict[str, float]:
    return usd_camera_fov_metadata(
        focal_length=focal_length,
        horizontal_aperture=horizontal_aperture,
        width=width,
        height=height,
    )


def _matrix4d_rowmajor(matrix: Any) -> list[float]:
    return matrix4d_rowmajor(matrix)


def _usd_attr_float(attr: Any) -> float | None:
    return usd_attr_float(attr)


def _usd_vec(attr: Any) -> list[float] | None:
    return usd_vec(attr)


def _tensor_first_vec3(value: Any) -> list[float]:
    return tensor_first_vec3(value)


def _robot_pose_yaw_deg(pose: dict[str, Any]) -> float | None:
    return robot_pose_yaw_deg(pose)


def _optional_float(value: Any) -> float | None:
    return optional_float(value)


def _wait_for_stage_load(stage_utils: Any, simulation_app: Any) -> None:
    is_loading = getattr(stage_utils, "is_stage_loading", None)
    if not callable(is_loading):
        return
    for _ in range(240):
        if not is_loading():
            return
        simulation_app.update()
    raise RuntimeError("Isaac Sim did not finish loading the generated USD stage")


def _rgb_tensor_to_uint8(value: Any, *, np: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach().cpu().numpy()
    array = np.asarray(value)
    if array.ndim == 4:
        array = array[0]
    if array.ndim != 3:
        raise RuntimeError(f"unexpected Isaac camera RGB tensor shape: {array.shape}")
    if array.shape[-1] > 3:
        array = array[..., :3]
    if array.shape[-1] != 3:
        raise RuntimeError(f"unexpected Isaac camera RGB channel count: {array.shape}")
    if array.dtype.kind == "f":
        scale = 255.0 if float(array.max(initial=0.0)) <= 1.0 else 1.0
        array = array * scale
    return np.clip(array, 0, 255).astype("uint8")


def _load_camera_view_specs(path: Path) -> list[dict[str, Any]]:
    return load_camera_view_specs(path)


def _load_camera_request_from_args(
    *,
    view_specs_path: Path | None,
    camera_request_path: Path | None,
    width: int,
    height: int,
) -> dict[str, Any]:
    return _load_camera_request_from_args_impl(
        view_specs_path=view_specs_path,
        camera_request_path=camera_request_path,
        width=width,
        height=height,
    )


def _isaac_scene_camera_view_spec(
    raw_spec: dict[str, Any],
    *,
    index: int,
    stage_utils: Any | None = None,
) -> dict[str, Any]:
    return isaac_scene_camera_view_spec(
        raw_spec,
        index=index,
        stage_utils=stage_utils,
    )


def _lane_camera_orbit(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    return lane_camera_orbit(raw_spec, lane_id)


def _backend_transform_for_lane(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    return backend_transform_for_lane(raw_spec, lane_id)


def _apply_scene_transform_to_point(point: list[float], transform: dict[str, Any]) -> list[float]:
    return apply_scene_transform_to_point(point, transform)


def _horizontal_aperture_from_lens(
    lens: dict[str, Any],
    *,
    width: int,
    height: int,
    focal_length: float,
) -> float:
    return horizontal_aperture_from_lens(
        lens,
        width=width,
        height=height,
        focal_length=focal_length,
    )


def _bounds_from_usd_prim_path(
    *,
    stage_utils: Any | None,
    usd_prim_path: str,
    min_target_z: float,
) -> dict[str, Any] | None:
    return bounds_from_usd_prim_path(
        stage_utils=stage_utils,
        usd_prim_path=usd_prim_path,
        min_target_z=min_target_z,
    )


def _eye_from_lookat_spec(
    *,
    target: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> list[float]:
    return eye_from_lookat_spec(
        target=target,
        distance=distance,
        azimuth=azimuth,
        elevation=elevation,
    )


def _camera_vec3(value: Any, *, default: list[float]) -> list[float]:
    return camera_vec3(value, default=default)


def _image_has_variance(array: Any, *, np: Any) -> bool:
    return image_has_variance(array, np=np)


def _module_version(module_name: str) -> str | None:
    return module_version(module_name)


def runtime_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _runtime_diagnostics(
        runtime_mode,
        real_smoke=real_smoke,
        default_width=DEFAULT_WIDTH,
        default_height=DEFAULT_HEIGHT,
        primitive_provenance=ISAAC_SEMANTIC_POSE_PROVENANCE,
        real_smoke_renderer_mode=REAL_SMOKE_RENDERER_MODE,
        real_smoke_capture_method=REAL_SMOKE_CAPTURE_METHOD,
    )


def rendering_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _runtime_rendering_diagnostics(
        runtime_mode,
        real_smoke=real_smoke,
        real_smoke_renderer_mode=REAL_SMOKE_RENDERER_MODE,
        real_smoke_capture_method=REAL_SMOKE_CAPTURE_METHOD,
    )


def _isaac_native_render_diagnostics_unavailable(
    *,
    runtime_mode: str,
    reason: str,
) -> dict[str, Any]:
    return native_render_diagnostics_unavailable(
        runtime_mode=runtime_mode,
        reason=reason,
    )


def _native_setting_candidate_count() -> int:
    return native_setting_candidate_count()


def _capture_quality_settings_unavailable(
    *,
    render_settle_frames: int,
    reason: str,
) -> dict[str, Any]:
    return capture_quality_settings_unavailable(
        render_settle_frames=render_settle_frames,
        reason=reason,
    )


def _capture_quality_settings(
    *,
    render_settle_frames: int,
    settings: Any | None,
    settings_mutation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return capture_quality_settings(
        render_settle_frames=render_settle_frames,
        settings=settings,
        settings_mutation=settings_mutation,
    )


def _isaac_native_render_diagnostics(
    *,
    renderer_mode: str,
    capture_method: str,
    view_kind: str,
    render_resolution: dict[str, Any],
    camera_prim_paths: list[str],
    render_product_paths: list[str] | None = None,
    isaac_lab_isp_active: bool = False,
    capture_quality_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return native_render_diagnostics(
        renderer_mode=renderer_mode,
        capture_method=capture_method,
        view_kind=view_kind,
        render_resolution=render_resolution,
        camera_prim_paths=camera_prim_paths,
        settings=_isaac_settings_interface(),
        render_product_paths=render_product_paths,
        isaac_lab_isp_active=isaac_lab_isp_active,
        capture_quality_settings=capture_quality_settings,
    )


def _apply_isaac_capture_quality_overrides(
    *,
    settings: Any | None,
    isaac_aa_op: int | None,
    isaac_tonemap_op: int | None = None,
    isaac_exposure_bias: float | None = None,
    isaac_colorcorr_gain: tuple[float, float, float] | None = None,
) -> dict[str, Any]:
    return apply_isaac_capture_quality_overrides(
        settings=settings,
        setting_paths=ISAAC_NATIVE_RENDER_SETTING_PATHS,
        capture_quality_fields=ISAAC_CAPTURE_QUALITY_SETTING_FIELDS,
        isaac_aa_op=isaac_aa_op,
        isaac_tonemap_op=isaac_tonemap_op,
        isaac_exposure_bias=isaac_exposure_bias,
        isaac_colorcorr_gain=isaac_colorcorr_gain,
    )


def _isaac_settings_interface() -> Any | None:
    try:
        import carb.settings  # type: ignore[import-untyped]

        return carb.settings.get_settings()
    except Exception:
        return None


def _isaac_setting_value(settings: Any | None, candidate_paths: tuple[str, ...]) -> dict[str, Any]:
    return isaac_setting_value(settings, candidate_paths)


def _camera_render_product_paths(camera: Any) -> list[str]:
    return camera_render_product_paths(camera)


def _render_product_paths_from_value(value: Any) -> list[str]:
    return render_product_paths_from_value(value)


def scene_load_diagnostics(
    runtime_mode: str,
    scene_source: str,
    scene_index: int,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _scene_load_diagnostics(
        runtime_mode,
        scene_source,
        scene_index,
        real_smoke=real_smoke,
    )


def segmentation_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
    scene_binding_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _segmentation_diagnostics(
        runtime_mode,
        real_smoke=real_smoke,
        scene_binding_diagnostics=scene_binding_diagnostics,
        requested_data_types=ISAAC_SEGMENTATION_DATA_TYPES,
        max_candidates=MAX_SEGMENTATION_CANDIDATES,
    )


def mapping_gap_diagnostics(
    *,
    runtime_mode: str,
    map_bundle_dir: Path | None,
    real_smoke: dict[str, Any] | None = None,
    scene_binding_diagnostics: dict[str, Any] | None = None,
    segmentation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return _mapping_gap_diagnostics(
        runtime_mode=runtime_mode,
        map_bundle_dir=map_bundle_dir,
        real_smoke=real_smoke,
        scene_binding_diagnostics=scene_binding_diagnostics,
        segmentation=segmentation,
        real_smoke_robot_view_images=_real_smoke_robot_view_images,
        has_required_robot_view_images=_has_required_robot_view_images,
        real_smoke_capture_method=REAL_SMOKE_CAPTURE_METHOD,
        real_robot_view_capture_method=REAL_ROBOT_VIEW_CAPTURE_METHOD,
    )


def _initial_semantic_pose_state(
    *,
    scenario: CleanupScenario,
    object_index: dict[str, Any],
    receptacle_index: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any] | None,
    initial_receptacle_id: str,
) -> dict[str, Any]:
    return initial_semantic_pose_state(
        scenario=scenario,
        object_index=object_index,
        receptacle_index=receptacle_index,
        scene_binding_diagnostics=scene_binding_diagnostics,
        initial_receptacle_id=initial_receptacle_id,
        semantic_pose_state_from_backend_state=_semantic_pose_state_from_backend_state,
    )


def _initial_semantic_pose_state_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return _semantic_pose_state_from_backend_state(state, transform_events=[])


def _semantic_pose_state_from_backend_state(
    state: dict[str, Any],
    *,
    transform_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return semantic_pose_state_from_backend_state(
        state,
        transform_events=transform_events,
        state_schema=ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
        state_source=ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        primitive_provenance=ISAAC_SEMANTIC_POSE_PROVENANCE,
        robot_pose_for_receptacle=_robot_pose_for_receptacle,
        semantic_object_poses_from_state=_semantic_object_poses_from_state,
        semantic_articulations_from_state=_semantic_articulations_from_state,
    )


def _record_semantic_pose_event(
    state: dict[str, Any],
    *,
    tool: str,
    state_mutation: str,
    object_id: str = "",
    receptacle_id: str = "",
    previous_location_id: str = "",
    location_id: str = "",
    relation: str = "",
    **extra: Any,
) -> dict[str, Any]:
    return record_semantic_pose_event(
        state,
        tool=tool,
        state_mutation=state_mutation,
        event_schema=ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
        state_schema=ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
        state_source=ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        primitive_provenance=ISAAC_SEMANTIC_POSE_PROVENANCE,
        robot_pose_for_receptacle=_robot_pose_for_receptacle,
        semantic_object_poses_from_state=_semantic_object_poses_from_state,
        semantic_articulations_from_state=_semantic_articulations_from_state,
        object_usd_prim_path=_object_usd_prim_path,
        receptacle_usd_prim_path=_receptacle_usd_prim_path,
        object_id=object_id,
        receptacle_id=receptacle_id,
        previous_location_id=previous_location_id,
        location_id=location_id,
        relation=relation,
        **extra,
    )


def _record_waypoint_pose_event(
    state: dict[str, Any],
    *,
    waypoint: dict[str, Any],
    robot_pose: dict[str, Any],
    previous_waypoint_id: str = "",
    previous_room_id: str = "",
) -> dict[str, Any]:
    return record_waypoint_pose_event(
        state,
        waypoint=waypoint,
        robot_pose=robot_pose,
        event_schema=ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
        state_schema=ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
        state_source=ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        primitive_provenance=ISAAC_SEMANTIC_POSE_PROVENANCE,
        semantic_object_poses_from_state=_semantic_object_poses_from_state,
        semantic_articulations_from_state=_semantic_articulations_from_state,
        previous_waypoint_id=previous_waypoint_id,
        previous_room_id=previous_room_id,
    )


def _seed_generated_mess_placements(state: dict[str, Any]) -> None:
    targets = [_dict(item) for item in _dict(state.get("private_manifest")).get("targets", [])]
    if not targets:
        return
    manifest_targets = _manifest_target_by_object_id(state)
    target_receptacle_ids = {
        receptacle_id
        for target in targets
        for receptacle_id in target.get("valid_receptacle_ids", [])
        if str(receptacle_id)
    }
    wrong_pool = _mess_wrong_receptacle_pool(state, target_receptacle_ids)
    if not wrong_pool:
        return
    diagnostics = [
        dict(item) for item in state.get("mess_placement_diagnostics", []) if isinstance(item, dict)
    ]
    for index, target in enumerate(targets):
        object_id = str(target.get("object_id") or "")
        if not object_id:
            continue
        target_ids = {str(item) for item in target.get("valid_receptacle_ids", []) if str(item)}
        manifest_target = manifest_targets.get(object_id)
        wrong = _target_start_receptacle(state, wrong_pool, index, target_ids, manifest_target)
        receptacle_id = str(wrong.get("receptacle_id") or "")
        if not receptacle_id:
            continue
        relation = _target_relation(wrong, manifest_target)
        placement_index = _target_placement_index(index, manifest_target)
        placement_resolution = _apply_object_location(
            state,
            object_id=object_id,
            receptacle_id=receptacle_id,
            relation=relation,
            placement_index=placement_index,
            source="canonical_mess_manifest" if manifest_target else "mess_seed",
        )
        diagnostic = _isaac_placement_diagnostic(
            state=state,
            object_id=object_id,
            receptacle_id=receptacle_id,
            relation=relation,
            source="canonical_mess_manifest" if manifest_target else "mess_seed",
            placement_index=placement_index,
            placement_resolution=placement_resolution,
        )
        diagnostics.append(diagnostic)
    state["mess_placement_diagnostics"] = diagnostics


def _manifest_target_by_object_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    manifest = _dict(state.get("generated_mess_manifest"))
    targets: dict[str, dict[str, Any]] = {}
    for raw_target in manifest.get("targets", []):
        target = _dict(raw_target)
        object_id = str(target.get("object_id") or "")
        if object_id:
            targets[object_id] = target
    return targets


def _target_start_receptacle(
    state: dict[str, Any],
    wrong_pool: list[dict[str, Any]],
    index: int,
    target_ids: set[str],
    manifest_target: dict[str, Any] | None,
) -> dict[str, Any]:
    if manifest_target:
        start_receptacle_id = str(manifest_target.get("start_receptacle_id") or "")
        if start_receptacle_id:
            receptacle = _receptacles_by_id(state).get(start_receptacle_id)
            if receptacle is None:
                raise ValueError(
                    "generated mess manifest start receptacle id is unavailable: "
                    f"{manifest_target.get('object_id')} -> {start_receptacle_id}"
                )
            return receptacle
    wrong = wrong_pool[index % len(wrong_pool)]
    if len(wrong_pool) > 1 and str(wrong.get("receptacle_id") or "") in target_ids:
        wrong = wrong_pool[(index + 1) % len(wrong_pool)]
    return wrong


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


def _mess_wrong_receptacle_pool(
    state: dict[str, Any],
    target_receptacle_ids: set[str],
) -> list[dict[str, Any]]:
    receptacles = list(_receptacles_by_id(state).values())
    wrong_pool = [
        item
        for item in receptacles
        if str(item.get("receptacle_id") or "") not in target_receptacle_ids
        and not _receptacle_requires_open(item)
    ]
    if not wrong_pool:
        wrong_pool = [
            item
            for item in receptacles
            if str(item.get("receptacle_id") or "") not in target_receptacle_ids
        ]
    return wrong_pool or receptacles


def _apply_object_location(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    relation: str,
    placement_index: int,
    source: str,
) -> dict[str, Any]:
    resolution = _resolve_isaac_placement(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=placement_index,
        relation=relation,
        source=source,
    )
    state.setdefault("locations", {})[object_id] = receptacle_id
    containment = dict(state.get("containment") or {})
    containment[object_id] = {
        "contained_in": receptacle_id if relation == "inside" else "",
        "location_relation": relation,
    }
    state["containment"] = containment
    overrides = dict(state.get("object_pose_overrides") or {})
    position = _vec3(resolution.get("position"))
    if position is not None:
        overrides[object_id] = {
            "position": _round_vec3(position),
            "position_source": ISAAC_PLACEMENT_RESOLVER_SOURCE,
            "support_receptacle_id": receptacle_id,
            "relation": relation,
            "support_status": resolution.get("support_status"),
            "contact_proof": resolution.get("contact_proof"),
            "resolution_source": resolution.get("resolution_source"),
            "source": source,
        }
    else:
        overrides.pop(object_id, None)
    state["object_pose_overrides"] = overrides
    _set_public_scenario_object_location(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
    )
    return resolution


def _set_public_scenario_object_location(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    relation: str,
) -> None:
    scenario = _dict(state.get("scenario"))
    for item in scenario.get("objects", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("object_id") or "") != object_id:
            continue
        item["location_id"] = receptacle_id
        item["contained_in"] = receptacle_id if relation == "inside" else ""
        item["location_relation"] = relation
        break


def _first_target_object_location(state: dict[str, Any]) -> str:
    for target in _dict(state.get("private_manifest")).get("targets", []):
        object_id = str(_dict(target).get("object_id") or "")
        location_id = str(_dict(state.get("locations")).get(object_id) or "")
        if location_id:
            return location_id
    return ""


def _isaac_placement_hooks() -> IsaacPlacementHooks:
    return IsaacPlacementHooks(
        aabb_xy_overlaps=_aabb_xy_overlaps,
        binding_for_handle=_binding_for_handle,
        candidate_has_direct_support=_candidate_has_direct_support,
        candidate_is_clear_of_dynamic_objects=_isaac_candidate_is_clear_of_dynamic_objects,
        dict_value=_dict,
        direct_support_clearance=_isaac_direct_support_clearance,
        direct_support_placement=_isaac_direct_support_placement,
        elevated_position_over_surface=_elevated_position_over_surface,
        fallback_placement_position=_isaac_fallback_placement_position,
        index_entry=_isaac_index_entry,
        normalize_support_surface=_normalize_support_surface,
        norm=_norm,
        object_bottom_offset=_isaac_object_bottom_offset,
        object_current_aabb=_isaac_object_current_aabb,
        object_footprint_half_extents=_isaac_object_footprint_half_extents,
        object_height=_isaac_object_height,
        object_surface_lift=_isaac_object_surface_lift,
        object_usd_prim_path=_object_usd_prim_path,
        object_world_bounds=_isaac_object_world_bounds,
        objects_by_id=_objects_by_id,
        pose_near=_pose_near,
        receptacle_support_pose=_receptacle_support_pose,
        receptacle_support_surface=_isaac_receptacle_support_surface,
        receptacle_support_surfaces=_isaac_receptacle_support_surfaces,
        receptacle_text=_receptacle_text,
        receptacle_usd_prim_path=_receptacle_usd_prim_path,
        receptacle_world_bounds=_isaac_receptacle_world_bounds,
        receptacles_by_id=_receptacles_by_id,
        round_vec3=_round_vec3,
        semantic_object_position_from_state=_semantic_object_position_from_state,
        state_objects_for_clearance=_isaac_state_objects_for_clearance,
        support_pose_position=_support_pose_position,
        support_surface_from_usd_bounds=_support_surface_from_usd_bounds,
        surface_candidate_positions=_surface_candidate_positions,
        vec3=_vec3,
    )


def _resolve_isaac_placement(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
    source: str,
) -> dict[str, Any]:
    return _resolve_isaac_placement_impl(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        relation=relation,
        source=source,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_state_objects_for_clearance(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return _isaac_state_objects_for_clearance_impl(state, hooks=_isaac_placement_hooks())


def _isaac_direct_support_placement(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
) -> dict[str, Any] | None:
    return _isaac_direct_support_placement_impl(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_receptacle_support_surface(
    state: dict[str, Any],
    receptacle_id: str,
) -> dict[str, Any] | None:
    return _isaac_receptacle_support_surface_impl(
        state,
        receptacle_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_receptacle_support_surfaces(
    state: dict[str, Any],
    receptacle_id: str,
) -> list[dict[str, Any]]:
    return _isaac_receptacle_support_surfaces_impl(
        state,
        receptacle_id,
        hooks=_isaac_placement_hooks(),
    )


def _normalize_support_surface(surface: Any) -> dict[str, Any] | None:
    return _normalize_support_surface_impl(surface)


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


def _isaac_candidate_is_clear_of_dynamic_objects(
    state: dict[str, Any],
    *,
    object_id: str,
    position: list[float],
    footprint: tuple[float, float],
    bottom_offset: float,
) -> bool:
    return _candidate_clear_impl(
        state,
        object_id=object_id,
        position=position,
        footprint=footprint,
        bottom_offset=bottom_offset,
        hooks=_isaac_placement_hooks(),
    )


def _aabb_xy_overlaps(
    first: tuple[float, float, float, float],
    second: dict[str, float],
    *,
    margin: float,
) -> bool:
    return _aabb_xy_overlaps_impl(first, second, margin=margin)


def _isaac_object_current_aabb(state: dict[str, Any], object_id: str) -> dict[str, float] | None:
    return _isaac_object_current_aabb_impl(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _elevated_position_over_surface(
    surface: dict[str, Any],
    *,
    bottom_offset: float,
) -> list[float]:
    return _elevated_position_over_surface_impl(surface, bottom_offset=bottom_offset)


def _isaac_fallback_placement_position(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
) -> list[float]:
    return _isaac_fallback_placement_position_impl(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        relation=relation,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_object_footprint_half_extents(
    state: dict[str, Any],
    object_id: str,
) -> tuple[float, float]:
    return _isaac_object_footprint_half_extents_impl(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_object_bottom_offset(state: dict[str, Any], object_id: str) -> float:
    return _isaac_object_bottom_offset_impl(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_object_height(state: dict[str, Any], object_id: str) -> float:
    return _isaac_object_height_impl(state, object_id, hooks=_isaac_placement_hooks())


def _isaac_object_surface_lift(category: Any) -> float:
    return _isaac_object_surface_lift_impl(category, norm=_norm)


def _isaac_direct_support_clearance(
    obj: dict[str, Any],
    receptacle: dict[str, Any],
) -> float:
    return _isaac_direct_support_clearance_impl(
        obj,
        receptacle,
        norm=_norm,
        receptacle_text=_receptacle_text,
    )


def _isaac_object_world_bounds(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return _isaac_object_world_bounds_impl(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_receptacle_world_bounds(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _isaac_receptacle_world_bounds_impl(
        state,
        receptacle_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_index_entry(
    state: dict[str, Any],
    public_id: str,
    *,
    index_name: str,
    binding_groups: tuple[str, ...],
) -> dict[str, Any]:
    return _isaac_index_entry_impl(
        state,
        public_id,
        index_name=index_name,
        binding_groups=binding_groups,
        hooks=_isaac_placement_hooks(),
    )


def _receptacle_requires_open(receptacle: dict[str, Any]) -> bool:
    text = _receptacle_text(receptacle)
    return "fridge" in text or "refrigerator" in text


def _receptacle_prefers_inside(receptacle: dict[str, Any]) -> bool:
    return _receptacle_requires_open(receptacle) or _receptacle_is_open_container(receptacle)


def _receptacle_is_open_container(receptacle: dict[str, Any]) -> bool:
    text = _receptacle_text(receptacle)
    return any(term in text for term in ("shelvingunit", "bookshelf", "bookcase", "shelf"))


def _receptacle_text(receptacle: dict[str, Any]) -> str:
    parts = (
        receptacle.get("receptacle_id", ""),
        receptacle.get("name", ""),
        receptacle.get("category", ""),
        receptacle.get("kind", ""),
    )
    return " ".join(str(part) for part in parts).lower()


def _isaac_placement_diagnostic(
    *,
    state: dict[str, Any],
    object_id: str,
    receptacle_id: str,
    relation: str,
    source: str,
    placement_index: int | None = None,
    placement_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _isaac_placement_diagnostic_impl(
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        source=source,
        placement_index=placement_index,
        placement_resolution=placement_resolution,
        hooks=_isaac_placement_hooks(),
    )


def _semantic_object_poses_from_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    poses: dict[str, dict[str, Any]] = {}
    locations = state.get("locations") or {}
    containment = state.get("containment") or {}
    current_receptacle_id = str(state.get("current_receptacle_id") or "")
    for item in _dict(state.get("scenario")).get("objects", []):
        if not isinstance(item, dict):
            continue
        object_id = str(item.get("object_id") or "")
        if not object_id:
            continue
        location_id = str(locations.get(object_id) or item.get("location_id") or "")
        support_receptacle_id = (
            current_receptacle_id if location_id == HELD_LOCATION_ID else location_id
        )
        relation = _dict(containment.get(object_id)).get("location_relation") or "on"
        pose_override = _dict(_dict(state.get("object_pose_overrides")).get(object_id))
        position = _semantic_object_position_from_state(
            state,
            object_id=object_id,
            location_id=location_id,
            original_location_id=str(item.get("location_id") or ""),
            support_receptacle_id=support_receptacle_id,
        )
        position_source = _semantic_object_position_source(
            position,
            location_id=location_id,
            original_location_id=str(item.get("location_id") or ""),
            pose_override=pose_override,
        )
        poses[object_id] = {
            "object_id": object_id,
            "usd_prim_path": _object_usd_prim_path(state, object_id),
            "location_id": location_id,
            "support_receptacle_id": support_receptacle_id,
            "support_usd_prim_path": _receptacle_usd_prim_path(state, support_receptacle_id),
            "attached_to_robot": location_id == HELD_LOCATION_ID,
            "location_relation": relation,
            "position": position,
            "position_source": position_source,
            "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
            "rendered_to_usd": False,
        }
        if pose_override:
            poses[object_id]["placement_support_status"] = pose_override.get("support_status")
            poses[object_id]["placement_contact_proof"] = pose_override.get("contact_proof")
            poses[object_id]["placement_resolution_source"] = pose_override.get("resolution_source")
    return poses


def _semantic_object_position_from_state(
    state: dict[str, Any],
    *,
    object_id: str,
    location_id: str,
    original_location_id: str,
    support_receptacle_id: str,
) -> list[float] | None:
    if location_id != HELD_LOCATION_ID:
        pose_override = _dict(_dict(state.get("object_pose_overrides")).get(object_id))
        override_position = _vec3(pose_override.get("position"))
        if override_position is not None:
            return _round_vec3(override_position)
    if location_id == original_location_id:
        bounds_position = _object_usd_world_bounds_center(state, object_id)
        if bounds_position is not None:
            return bounds_position
    if location_id == HELD_LOCATION_ID:
        robot_pose = _robot_pose_for_receptacle(
            state,
            str(state.get("current_receptacle_id") or support_receptacle_id),
        )
        held_target = _vec3(robot_pose.get("target_position"))
        if held_target is not None:
            return _round_vec3(held_target)
    target = _semantic_pose_target_position(
        support_id=support_receptacle_id,
        receptacle_index=_dict(state.get("receptacle_index")),
        fallback_pose={},
    )
    if target is not None:
        return _round_vec3(list(target))
    return _object_usd_world_bounds_center(state, object_id)


def _semantic_object_position_source(
    position: list[float] | None,
    *,
    location_id: str,
    original_location_id: str,
    pose_override: dict[str, Any] | None = None,
) -> str:
    if position is None:
        return ""
    if _vec3(_dict(pose_override).get("position")) is not None and location_id != HELD_LOCATION_ID:
        return str(_dict(pose_override).get("position_source") or ISAAC_PLACEMENT_RESOLVER_SOURCE)
    if location_id == HELD_LOCATION_ID:
        return "isaac_robot_target_position"
    if location_id == original_location_id:
        return "usd_world_bounds_center"
    return "isaac_support_pose_semantic_location"


def _object_usd_world_bounds_center(
    state: dict[str, Any],
    object_id: str,
) -> list[float] | None:
    binding = _binding_for_handle(
        state.get("scene_binding_diagnostics"),
        object_id,
        ("selected_object_bindings", "object_bindings"),
    )
    for handle in (binding.get("usd_handle"), object_id):
        entry = _dict(_dict(state.get("object_index")).get(str(handle)))
        center = _vec3(_dict(entry.get("usd_world_bounds")).get("center"))
        if center is not None:
            return _round_vec3(center)
    return None


def _semantic_articulations_from_state(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    open_ids = set(state.get("open_receptacle_ids") or [])
    articulations: dict[str, dict[str, Any]] = {}
    for item in _dict(state.get("scenario")).get("receptacles", []):
        if not isinstance(item, dict):
            continue
        receptacle_id = str(item.get("receptacle_id") or "")
        if not receptacle_id:
            continue
        opened = receptacle_id in open_ids
        articulations[receptacle_id] = {
            "receptacle_id": receptacle_id,
            "usd_prim_path": _receptacle_usd_prim_path(state, receptacle_id),
            "open": opened,
            "joint_state": "open" if opened else "closed",
            "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
            "rendered_to_usd": False,
        }
    return articulations


def _object_usd_prim_path(state: dict[str, Any], object_id: str) -> str:
    return _binding_usd_prim_path(
        state.get("scene_binding_diagnostics"),
        object_id,
        ("selected_object_bindings", "object_bindings"),
    ) or _index_usd_prim_path(state.get("object_index"), object_id)


def _receptacle_usd_prim_path(state: dict[str, Any], receptacle_id: str) -> str:
    return _binding_usd_prim_path(
        state.get("scene_binding_diagnostics"),
        receptacle_id,
        ("selected_target_receptacle_bindings", "receptacle_bindings"),
    ) or _index_usd_prim_path(state.get("receptacle_index"), receptacle_id)


def _binding_usd_prim_path(
    scene_binding_diagnostics: Any,
    public_id: str,
    binding_keys: tuple[str, ...],
) -> str:
    if not public_id:
        return ""
    diagnostics = _dict(scene_binding_diagnostics)
    for key in binding_keys:
        binding = _dict(_dict(diagnostics.get(key)).get(public_id))
        if binding.get("status") == "bound" and binding.get("usd_prim_path"):
            return str(binding["usd_prim_path"])
    return ""


def _index_usd_prim_path(index: Any, handle: str) -> str:
    if not handle:
        return ""
    entry = _dict(_dict(index).get(handle))
    return str(entry.get("usd_prim_path") or "")


def observe(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    del args
    _count(state, "observe")
    write_state_from_state_arg(state)
    return _ok(
        "observe",
        scenario=_public_state(state),
        current_receptacle_id=state["current_receptacle_id"],
        held_object_id=state.get("held_object_id"),
        isaac_runtime=state["runtime"],
    )


def navigate_to_object(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_object")
    object_id = args.object_id
    if object_id not in _objects_by_id(state):
        return _error("navigate_to_object", "stale_reference", object_id=object_id)
    location_id = state["locations"].get(object_id)
    if location_id in {None, HELD_LOCATION_ID}:
        return _error("navigate_to_object", "object_not_at_public_location", object_id=object_id)
    previous = state["current_receptacle_id"]
    state["current_receptacle_id"] = str(location_id)
    event = _record_semantic_pose_event(
        state,
        tool="navigate_to_object",
        state_mutation="isaac_root_pose",
        object_id=object_id,
        receptacle_id=str(location_id),
        previous_location_id=previous,
        location_id=str(location_id),
    )
    write_state_from_state_arg(state)
    return _ok(
        "navigate_to_object",
        object_id=object_id,
        source_receptacle_id=str(location_id),
        previous_receptacle_id=previous,
        location_id=str(location_id),
        robot_pose=_robot_pose_for_receptacle(state, str(location_id)),
        state_mutation="isaac_root_pose",
        semantic_pose_event=event,
    )


def navigate_to_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_receptacle")
    receptacle_id = args.receptacle_id
    if receptacle_id not in _receptacles_by_id(state):
        return _error("navigate_to_receptacle", "stale_reference", receptacle_id=receptacle_id)
    previous = state["current_receptacle_id"]
    state["current_receptacle_id"] = receptacle_id
    held_object_id = state.get("held_object_id")
    event = _record_semantic_pose_event(
        state,
        tool="navigate_to_receptacle",
        state_mutation="isaac_root_pose",
        object_id=str(held_object_id or ""),
        receptacle_id=receptacle_id,
        previous_location_id=previous,
        location_id=receptacle_id,
    )
    write_state_from_state_arg(state)
    return _ok(
        "navigate_to_receptacle",
        receptacle_id=receptacle_id,
        object_id=held_object_id,
        previous_receptacle_id=previous,
        robot_pose=_robot_pose_for_receptacle(state, receptacle_id),
        state_mutation="isaac_root_pose",
        semantic_pose_event=event,
    )


def navigate_to_waypoint(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_waypoint")
    waypoint = _dict(args.waypoint_json)
    robot_pose = _robot_pose_for_waypoint(waypoint)
    if not _has_xy(robot_pose):
        return _error(
            "navigate_to_waypoint",
            "waypoint_pose_missing",
            waypoint_id=str(waypoint.get("waypoint_id") or ""),
        )
    previous_waypoint_id = str(state.get("current_waypoint_id") or "")
    previous_room_id = str(state.get("current_room_id") or "")
    waypoint_id = str(waypoint.get("waypoint_id") or "")
    room_id = str(waypoint.get("room_id") or "")
    fixture_ids = [str(item) for item in waypoint.get("fixture_ids") or [] if str(item)]
    state["current_waypoint_id"] = waypoint_id
    state["current_room_id"] = room_id
    if fixture_ids:
        state["current_receptacle_id"] = fixture_ids[0]
    event = _record_waypoint_pose_event(
        state,
        waypoint=waypoint,
        robot_pose=robot_pose,
        previous_waypoint_id=previous_waypoint_id,
        previous_room_id=previous_room_id,
    )
    write_state_from_state_arg(state)
    return _ok(
        "navigate_to_waypoint",
        waypoint_id=waypoint_id,
        room_id=room_id,
        fixture_ids=fixture_ids,
        previous_waypoint_id=previous_waypoint_id,
        previous_room_id=previous_room_id,
        robot_pose=robot_pose,
        state_mutation="isaac_waypoint_pose",
        semantic_pose_event=event,
        backend_pose_mutation_available=True,
    )


def pick(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "pick")
    object_id = args.object_id
    objects = _objects_by_id(state)
    obj = objects.get(object_id)
    if obj is None:
        return _error("pick", "stale_reference", object_id=object_id)
    if not obj.get("pickupable", True):
        return _error("pick", "not_pickupable", object_id=object_id)
    if state.get("held_object_id") is not None:
        return _error("pick", "already_holding", held_object_id=state["held_object_id"])
    previous_location_id = state["locations"][object_id]
    state["held_object_id"] = object_id
    state["locations"][object_id] = HELD_LOCATION_ID
    event = _record_semantic_pose_event(
        state,
        tool="pick",
        state_mutation="isaac_prim_attach",
        object_id=object_id,
        receptacle_id=str(previous_location_id),
        previous_location_id=previous_location_id,
        location_id=HELD_LOCATION_ID,
    )
    write_state_from_state_arg(state)
    return _ok(
        "pick",
        object_id=object_id,
        previous_location_id=previous_location_id,
        location_id=HELD_LOCATION_ID,
        state_mutation="isaac_prim_attach",
        semantic_pose_event=event,
    )


def open_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "open_receptacle")
    receptacle_id = args.receptacle_id
    receptacle = _receptacles_by_id(state).get(receptacle_id)
    if receptacle is None:
        return _error("open_receptacle", "stale_reference", receptacle_id=receptacle_id)
    opened = "fridge" in str(receptacle.get("name", "")).lower()
    open_ids = set(state.get("open_receptacle_ids") or [])
    if opened:
        open_ids.add(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    event = _record_semantic_pose_event(
        state,
        tool="open_receptacle",
        state_mutation="isaac_articulation_joint_pose",
        object_id=str(state.get("held_object_id") or ""),
        receptacle_id=receptacle_id,
        location_id=receptacle_id,
        articulation_open=opened,
        requested_open=True,
    )
    write_state_from_state_arg(state)
    return _ok(
        "open_receptacle",
        receptacle_id=receptacle_id,
        object_id=state.get("held_object_id"),
        opened=opened,
        state_mutation="isaac_articulation_joint_pose",
        semantic_pose_event=event,
    )


def close_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "close_receptacle")
    receptacle_id = args.receptacle_id
    if receptacle_id not in _receptacles_by_id(state):
        return _error("close_receptacle", "stale_reference", receptacle_id=receptacle_id)
    open_ids = set(state.get("open_receptacle_ids") or [])
    was_open = receptacle_id in open_ids
    open_ids.discard(receptacle_id)
    state["open_receptacle_ids"] = sorted(open_ids)
    event = _record_semantic_pose_event(
        state,
        tool="close_receptacle",
        state_mutation="isaac_articulation_joint_pose",
        object_id=str(state.get("held_object_id") or ""),
        receptacle_id=receptacle_id,
        location_id=receptacle_id,
        articulation_open=False,
        was_open=was_open,
    )
    write_state_from_state_arg(state)
    return _ok(
        "close_receptacle",
        receptacle_id=receptacle_id,
        object_id=state.get("held_object_id"),
        closed=was_open,
        state_mutation="isaac_articulation_joint_pose",
        semantic_pose_event=event,
    )


def place(args: argparse.Namespace, state: dict[str, Any], *, relation: str) -> dict[str, Any]:
    tool = "place_inside" if relation == "inside" else "place"
    _count(state, tool)
    receptacle_id = args.receptacle_id
    if receptacle_id not in _receptacles_by_id(state):
        return _error(tool, "stale_reference", receptacle_id=receptacle_id)
    object_id = state.get("held_object_id")
    if object_id is None:
        return _error(tool, "not_holding")
    object_id = str(object_id)
    state["held_object_id"] = None
    state["current_receptacle_id"] = receptacle_id
    placement_resolution = _apply_object_location(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        placement_index=len(state.get("placement_diagnostics") or []),
        source="cleanup_place",
    )
    diagnostic = _isaac_placement_diagnostic(
        state=state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        source="cleanup_place",
        placement_resolution=placement_resolution,
    )
    state.setdefault("placement_diagnostics", []).append(diagnostic)
    event = _record_semantic_pose_event(
        state,
        tool=tool,
        state_mutation="isaac_prim_transform",
        object_id=object_id,
        receptacle_id=receptacle_id,
        previous_location_id=HELD_LOCATION_ID,
        location_id=receptacle_id,
        relation=relation,
        placement_support_status=diagnostic.get("placement_support_status"),
        direct_support_proven=diagnostic.get("direct_support_proven"),
        placement_contact_proof=diagnostic.get("contact_proof"),
        placement_resolution_source=diagnostic.get("resolution_source"),
    )
    write_state_from_state_arg(state)
    return _ok(
        tool,
        object_id=object_id,
        receptacle_id=receptacle_id,
        location_id=receptacle_id,
        contained_in=receptacle_id if relation == "inside" else None,
        location_relation=relation,
        placement_diagnostic=diagnostic,
        placement_support_status=diagnostic.get("placement_support_status"),
        direct_support_proven=diagnostic.get("direct_support_proven"),
        state_mutation="isaac_prim_transform",
        semantic_pose_event=event,
    )


def done(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "done")
    scenario = scenario_from_state(state)
    score = score_cleanup(state["locations"], scenario.private_manifest)
    annotated_score = annotate_score_with_semantic_acceptability(
        score.to_dict(),
        scenario,
    )
    write_state_from_state_arg(state)
    return _ok(
        "done",
        reason=args.reason,
        cleanup_status=score.status,
        score=annotated_score,
        final_locations=dict(state["locations"]),
        final_containment=dict(state.get("containment") or {}),
        tool_event_counts=dict(state.get("tool_event_counts") or {}),
    )


def write_snapshot(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "snapshot")
    if _real_rendering_proven(state):
        try:
            source_path = _real_snapshot_source_image(state)
            shape = _copy_real_snapshot_image(
                source_path,
                args.output_path,
                width=args.render_width,
                height=args.render_height,
            )
        except RuntimeError as exc:
            return _error("snapshot", "real_snapshot_image_invalid", reason=str(exc))
        write_state_from_state_arg(state)
        return _ok(
            "snapshot",
            output_path=str(args.output_path),
            visual_artifact_provenance=REAL_SMOKE_CAPTURE_METHOD,
            placeholder_visuals=False,
            native_render_diagnostics=_native_render_diagnostics_from_state(state),
            snapshot_provenance={
                "source": "isaac_runtime_rgb_capture",
                "source_path": str(source_path),
                "output_path": str(args.output_path),
                "visual_artifact_provenance": REAL_SMOKE_CAPTURE_METHOD,
                "placeholder_visuals": False,
                "static_isaac_capture": True,
                "semantic_pose_rendered": False,
                "shape": shape,
                "reason": (
                    "Snapshot reuses a real Isaac RGB capture. Semantic pose edits "
                    "are not rendered back into the USD stage yet."
                ),
            },
        )
    _write_placeholder_image(
        args.output_path,
        title=args.title,
        subtitle=state["runtime"]["renderer_mode"],
        state=state,
        width=args.render_width,
        height=args.render_height,
    )
    write_state_from_state_arg(state)
    return _ok(
        "snapshot",
        output_path=str(args.output_path),
        visual_artifact_provenance=state["runtime"]["visual_artifact_provenance"],
        placeholder_visuals=True,
        native_render_diagnostics=_native_render_diagnostics_from_state(state),
        snapshot_provenance={
            "source": "placeholder_protocol_image",
            "output_path": str(args.output_path),
            "visual_artifact_provenance": state["runtime"]["visual_artifact_provenance"],
            "placeholder_visuals": True,
            "static_isaac_capture": False,
            "semantic_pose_rendered": False,
            "reason": "Snapshot is a CI-safe placeholder because real Isaac rendering is unproven.",
        },
    )


def write_robot_views(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "robot_views")
    if state.get("robot") is None:
        return _error("robot_views", "robot_not_included")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = _safe_file_stem(args.label)
    views = {
        "fpv": args.output_dir / f"{safe_label}.fpv.png",
        "chase": args.output_dir / f"{safe_label}.chase.png",
        "map": args.output_dir / f"{safe_label}.map.png",
        "verify": args.output_dir / f"{safe_label}.verify.png",
    }
    real_views = _real_semantic_pose_robot_view_images(
        state,
        views,
        width=args.render_width,
        height=args.render_height,
        render_settle_frames=max(0, int(args.render_settle_frames or 0)),
        isaac_aa_op=args.isaac_aa_op,
        isaac_tonemap_op=args.isaac_tonemap_op,
        isaac_exposure_bias=args.isaac_exposure_bias,
        isaac_colorcorr_gain=args.isaac_colorcorr_gain,
        focus_object_id=args.focus_object_id,
        focus_receptacle_id=args.focus_receptacle_id,
    )
    semantic_pose_state_refreshed = bool(real_views)
    if not real_views:
        real_views = _real_robot_view_images(state)
    shapes: dict[str, list[int]] = {}
    if real_views:
        try:
            shapes = _copy_real_robot_view_images(
                real_views,
                views,
                width=args.render_width,
                height=args.render_height,
            )
        except RuntimeError as exc:
            return _error(
                "robot_views",
                "real_robot_view_images_invalid",
                reason=str(exc),
            )
    elif _real_rendering_proven(state):
        return _error(
            "robot_views",
            "real_robot_view_images_unavailable",
            reason=(
                "Real Isaac rendering was proven, but FPV/chase/map/verify view images "
                "were not recorded in worker state."
            ),
        )
    else:
        for view_name, path in views.items():
            _write_placeholder_image(
                path,
                title=f"{args.label} {view_name}",
                subtitle=state["runtime"]["renderer_mode"],
                state=state,
                width=args.render_width,
                height=args.render_height,
                focus_object_id=args.focus_object_id,
                focus_receptacle_id=args.focus_receptacle_id,
            )
            shapes[view_name] = [args.render_height, args.render_width, 3]
    write_state_from_state_arg(state)
    robot_pose = _robot_view_rendered_robot_pose(state)
    focus = _robot_view_focus(
        state,
        robot_pose,
        focus_object_id=args.focus_object_id,
        focus_receptacle_id=args.focus_receptacle_id,
    )
    return _ok(
        "robot_views",
        output_dir=str(args.output_dir),
        view_variant=ISAACLAB_ROBOT_VIEW_VARIANT,
        view_provenance=_robot_view_command_provenance(
            state,
            semantic_pose_state_refreshed=semantic_pose_state_refreshed,
        ),
        camera_control_contract=_robot_view_camera_control_contract(
            state,
            robot_pose=robot_pose,
            focus=focus,
        ),
        robot_pose=robot_pose,
        robot_trajectory=[robot_pose],
        room_outline_count=len(state.get("room_outlines") or []),
        color_profile=_dict(state.get("robot_view_color_profile")),
        color_management=_dict(state.get("robot_view_color_management")),
        lighting_profile=_dict(state.get("robot_view_lighting_profile")),
        lighting_diagnostics=_dict(state.get("robot_view_lighting_diagnostics")),
        camera_diagnostics=_dict(state.get("robot_view_camera_diagnostics")),
        native_render_diagnostics=_native_render_diagnostics_from_state(state),
        focus=focus,
        views={key: str(path) for key, path in views.items()},
        shapes=shapes,
        render_resolution={"width": args.render_width, "height": args.render_height},
        render_settle_frames=max(0, int(args.render_settle_frames or 0)),
    )


def _robot_view_rendered_robot_pose(state: dict[str, Any]) -> dict[str, Any]:
    semantic_robot_pose = _dict(_dict(state.get("semantic_pose_state")).get("robot_pose"))
    if _has_xy(semantic_robot_pose):
        return semantic_robot_pose
    return _robot_pose_for_receptacle(
        state,
        str(state.get("current_receptacle_id") or "floor_01"),
    )


def write_camera_views(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "camera_views")
    runtime = _dict(state.get("runtime"))
    scene_usd = str(state.get("scene_usd") or "")
    if runtime.get("runtime_mode") != "real":
        return _error("camera_views", "real_runtime_required")
    if not scene_usd or not Path(scene_usd).is_file():
        return _error("camera_views", "local_scene_usd_required", scene_usd=scene_usd)
    camera_request = _load_camera_request_from_args(
        view_specs_path=args.view_specs_path,
        camera_request_path=args.camera_request_path,
        width=args.render_width,
        height=args.render_height,
    )
    capture = capture_scene_camera_views(
        scene_usd=Path(scene_usd),
        camera_request=camera_request,
        output_dir=args.output_dir,
        width=args.render_width,
        height=args.render_height,
        semantic_pose_state=_dict(state.get("semantic_pose_state")),
    )
    semantic_pose_application = _dict(capture.get("semantic_pose_stage_application"))
    state["scene_camera_view_capture"] = {
        "schema": "isaac_scene_camera_view_capture_v1",
        "capture_method": "isaac_lab_camera_rgb_scene_probe",
        "scene_usd": scene_usd,
        "render_steps": int(capture.get("render_steps") or 0),
        "view_count": len(capture.get("views") or []),
        "semantic_pose_stage_application": semantic_pose_application,
        "semantic_pose_rendered": semantic_pose_application.get("rendered_to_usd") is True,
    }
    semantic_pose_state = _dict(state.get("semantic_pose_state"))
    if semantic_pose_application.get("rendered_to_usd") is True:
        semantic_pose_state["rendered_to_usd"] = True
        semantic_pose_state["scene_camera_view_capture"] = dict(state["scene_camera_view_capture"])
        state["semantic_pose_state"] = semantic_pose_state
    write_state_from_state_arg(state)
    view_variant = _camera_capture_variant(capture)
    provenance = _camera_capture_provenance(capture)
    return _ok(
        "camera_views",
        camera_control_api=capture.get("camera_control_api") or CAMERA_CONTROL_API_NAME,
        camera_request_schema=capture.get("camera_request_schema"),
        calibration_status=capture.get("calibration_status"),
        lighting_profile=capture.get("lighting_profile") or {},
        lighting_diagnostics=capture.get("lighting_diagnostics") or {},
        color_profile=capture.get("color_profile") or {},
        color_management=capture.get("color_management") or {},
        native_render_diagnostics=capture.get("native_render_diagnostics") or {},
        lens=capture.get("lens") or {},
        derived_lens=capture.get("derived_lens") or {},
        view_variant=view_variant,
        visual_artifact_provenance=provenance,
        scene_usd=scene_usd,
        views=capture.get("views") or [],
        images=capture.get("images") or {},
        shapes=capture.get("shapes") or {},
        scene_bounds=capture.get("scene_bounds"),
        semantic_pose_stage_application=semantic_pose_application,
        semantic_pose_rendered=semantic_pose_application.get("rendered_to_usd") is True,
        render_steps=int(capture.get("render_steps") or 0),
        render_resolution={"width": args.render_width, "height": args.render_height},
    )


def _locations_command(_: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return {"ok": True, "tool": "locations", "final_locations": state["locations"]}


_STATE_COMMANDS: dict[str, _IsaacWorkerCommand] = {
    "locations": _locations_command,
    "snapshot": write_snapshot,
    "robot_views": write_robot_views,
    "camera_views": write_camera_views,
    "observe": observe,
    "navigate_to_object": navigate_to_object,
    "navigate_to_waypoint": navigate_to_waypoint,
    "navigate_to_receptacle": navigate_to_receptacle,
    "pick": pick,
    "open_receptacle": open_receptacle,
    "place": lambda args, state: place(args, state, relation="on"),
    "place_inside": lambda args, state: place(args, state, relation="inside"),
    "close_receptacle": close_receptacle,
    "done": done,
}


def _robot_view_camera_control_contract(
    state: dict[str, Any],
    *,
    robot_pose: dict[str, Any] | None = None,
    focus: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provenance = _dict(state.get("robot_view_provenance"))
    semantic_pose_state_refreshed = provenance.get("semantic_pose_state_refreshed")
    robot_import = _dict(state.get("robot_import"))
    mounted_head_camera = bool(
        provenance.get("robot_mounted_head_camera")
        or robot_import.get("status") == "imported"
        or _dict(state.get("semantic_pose_view_capture")).get("robot_mounted_head_camera")
    )
    head_camera_equivalent = (
        bool(provenance.get("head_camera_equivalent")) and not mounted_head_camera
    )
    if mounted_head_camera or head_camera_equivalent or robot_import:
        status = (
            "robot_mounted_head_camera_robot_view"
            if mounted_head_camera
            else "robot_head_camera_equivalent_robot_view"
        )
        camera_model = (
            "robot_mounted_head_camera_v1"
            if mounted_head_camera
            else "robot_head_camera_equivalent_v1"
        )
        contract = robot_mounted_head_camera_control_contract(
            backend=ISAACLAB_SUBPROCESS_BACKEND,
            status=status,
            camera_model=camera_model,
            fpv_source=str(
                provenance.get("fpv")
                or (
                    "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv"
                    if mounted_head_camera
                    else "isaac_lab_head_camera_equivalent:fpv"
                )
            ),
            verify_source=str(provenance.get("verify") or "isaac_lab_semantic_pose_verify_camera"),
            chase_source="robot_relative_camera_follower",
            pose_source=str(
                _dict(robot_pose).get("pose_source") or "roboclaws_shared_scene_frame_support_pose"
            ),
            lens_source=(
                "rby1m_mujoco_robot_0/head_camera_extrinsics_and_fov"
                if mounted_head_camera
                else "rby1m_head_camera_contract_pending_isaac_robot_import"
            ),
            camera_prim_path=str(robot_import.get("head_camera_prim_path") or ""),
            robot_asset=robot_import,
            robot_pose=dict(robot_pose or {}),
            focus=dict(focus or {}),
            color_profile=_dict(state.get("robot_view_color_profile")),
            color_management=_dict(state.get("robot_view_color_management")),
            lighting_profile=_dict(state.get("robot_view_lighting_profile")),
        )
        contract.update(
            {
                "semantic_pose_state_refreshed": semantic_pose_state_refreshed,
                "evidence_note": (
                    "Isaac cleanup FPV uses the imported RBY1M mounted head camera "
                    "when the robot USD import artifact is present. Without that "
                    "artifact it remains explicitly marked as head-camera-equivalent. "
                    "Chase is rendered from a robot-relative rear/high report camera; "
                    "map remains auxiliary report evidence."
                ),
            }
        )
        return contract
    contract = backend_local_robot_view_camera_control_contract(
        backend=ISAACLAB_SUBPROCESS_BACKEND,
        status="backend_local_scene_bounds_camera",
        fpv_source=str(provenance.get("fpv") or "isaac_lab_scene_bounds_fpv"),
        verify_source=str(provenance.get("verify") or "isaac_lab_scene_bounds_verify"),
        pose_source="isaac_support_pose_near_current_receptacle",
        lens_source="isaac_robot_view_pinhole_defaults_24mm_20.955mm_aperture",
    )
    contract.update(
        {
            "semantic_pose_state_refreshed": semantic_pose_state_refreshed,
            "robot_pose": dict(robot_pose or {}),
            "focus": dict(focus or {}),
            "evidence_note": (
                "Isaac cleanup robot views currently use backend-local scene-bounds/support-pose "
                "camera placement, not roboclaws.camera_control.render_views. They are useful "
                "report evidence, but they are not yet proof that the agent-facing FPV is "
                "backend-swappable at identical scene-frame pose/FOV."
            ),
        }
    )
    return contract


def _target_room_id_from_pose_inputs(
    state: dict[str, Any],
    receptacle_id: str,
    support: dict[str, Any],
) -> str | None:
    scenario_receptacle = (
        _dict(_receptacles_by_id(state).get(receptacle_id))
        if isinstance(state.get("scenario"), dict)
        else {}
    )
    room_area = str(scenario_receptacle.get("room_area") or "")
    if room_area.startswith("room_"):
        return room_area
    metadata_room_id = str(support.get("metadata_room_id") or "")
    if metadata_room_id:
        return (
            metadata_room_id if metadata_room_id.startswith("room_") else f"room_{metadata_room_id}"
        )
    target = _support_pose_position(support)
    if target is None:
        return None
    for outline in state.get("room_outlines") or []:
        center = outline.get("center")
        half_extents = outline.get("half_extents")
        if not isinstance(center, list | tuple) or not isinstance(half_extents, list | tuple):
            continue
        if float(center[0]) - float(half_extents[0]) <= target[0] <= float(center[0]) + float(
            half_extents[0]
        ) and float(center[1]) - float(half_extents[1]) <= target[1] <= float(center[1]) + float(
            half_extents[1]
        ):
            return str(outline.get("room_id") or "") or None
    return None


def _robot_pose_for_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
) -> dict[str, Any]:
    support = _receptacle_support_pose(state, receptacle_id)
    if not support:
        pose = _pose_near(receptacle_id)
        pose["pose_source"] = "hash_fallback_pose_near_receptacle"
        return pose
    x = float(support["x"])
    y = float(support["y"])
    z = float(support.get("z", 0.0))
    pose = resolve_cleanup_robot_pose(
        target_position=[x, y, z],
        target_room_id=_target_room_id_from_pose_inputs(state, receptacle_id, support),
        target_receptacle_id=receptacle_id,
        room_outlines=state.get("room_outlines") or [],
        scene_center=_scene_index_center_xy(state),
        stand_off_m=1.15,
        frame=MOLMOSPACES_SCENE_FRAME,
    )
    pose["support_pose_source"] = str(support.get("source") or "")
    return pose


def _robot_pose_for_waypoint(waypoint: dict[str, Any]) -> dict[str, Any]:
    for key in ("b1_pose", "robot_pose"):
        pose = _dict(waypoint.get(key))
        if _has_xy(pose):
            result = _normalized_waypoint_robot_pose(
                pose,
                waypoint=waypoint,
                pose_source=str(pose.get("pose_source") or key),
            )
            result["waypoint_pose_key"] = key
            return result
    if not _has_xy(waypoint):
        return {}
    return _normalized_waypoint_robot_pose(
        waypoint,
        waypoint=waypoint,
        pose_source=str(waypoint.get("pose_source") or "public_waypoint_map_frame"),
    )


def _normalized_waypoint_robot_pose(
    pose: dict[str, Any],
    *,
    waypoint: dict[str, Any],
    pose_source: str,
) -> dict[str, Any]:
    x = _optional_float(pose.get("x"))
    y = _optional_float(pose.get("y"))
    if x is None or y is None:
        return {}
    yaw = _optional_float(pose.get("yaw"))
    yaw_deg = _optional_float(pose.get("yaw_deg"))
    if yaw_deg is None and yaw is not None:
        yaw_deg = math.degrees(yaw)
    result: dict[str, Any] = {
        "frame": str(
            pose.get("frame") or pose.get("frame_id") or waypoint.get("frame_id") or "map"
        ),
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "z": round(float(_optional_float(pose.get("z")) or 0.0), 6),
        "pose_source": pose_source,
        "waypoint_id": str(waypoint.get("waypoint_id") or ""),
        "room_id": str(waypoint.get("room_id") or ""),
    }
    if yaw_deg is not None:
        result["yaw_deg"] = round(float(yaw_deg), 6)
    if yaw is not None:
        result["theta"] = round(float(yaw), 6)
    target = _vec3(pose.get("target_position"))
    if target is not None:
        result["target_position"] = _round_vec3(target)
    fixture_ids = [str(item) for item in waypoint.get("fixture_ids") or [] if str(item)]
    if fixture_ids:
        result["fixture_ids"] = fixture_ids
    if pose.get("support_pose_source") is not None:
        result["support_pose_source"] = str(pose.get("support_pose_source"))
    return result


def _receptacle_support_pose(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    binding = _binding_for_handle(
        state.get("scene_binding_diagnostics"),
        receptacle_id,
        ("selected_target_receptacle_bindings", "receptacle_bindings"),
    )
    for handle in (binding.get("usd_handle"), receptacle_id):
        support = _dict(_dict(state.get("receptacle_index")).get(str(handle))).get("support_pose")
        support_pose = _dict(support)
        if _has_xy(support_pose) and support_pose.get("source") in {
            "usd_world_bounds_top_center",
            ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE,
            ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE,
            ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE,
        }:
            metadata_room_id = _dict(_dict(state.get("receptacle_index")).get(str(handle))).get(
                "metadata_room_id"
            )
            if metadata_room_id is not None:
                support_pose["metadata_room_id"] = metadata_room_id
            return support_pose
    return {}


def _binding_for_handle(
    scene_binding_diagnostics: Any,
    handle: str,
    groups: tuple[str, ...],
) -> dict[str, Any]:
    bindings = _dict(scene_binding_diagnostics)
    for group in groups:
        item = _dict(_dict(bindings.get(group)).get(handle))
        if item:
            return item
    return {}


def _scene_index_center_xy(state: dict[str, Any]) -> tuple[float, float]:
    centers: list[list[float]] = []
    for index_name in ("receptacle_index", "object_index"):
        for entry in _dict(state.get(index_name)).values():
            center = _vec3(_dict(_dict(entry).get("usd_world_bounds")).get("center"))
            if center is not None:
                centers.append(center)
    if not centers:
        return (0.0, 0.0)
    return (
        sum(center[0] for center in centers) / len(centers),
        sum(center[1] for center in centers) / len(centers),
    )


def _camera_capture_variant(capture: dict[str, Any]) -> str:
    if any(
        isinstance(item, dict) and item.get("camera_model") == CANONICAL_CAMERA_MODEL
        for item in capture.get("views") or []
    ):
        return "isaaclab-canonical-eye-target-camera-control-v1"
    return "isaaclab-anchor-orbit-camera-control-v1"


def _camera_capture_provenance(capture: dict[str, Any]) -> str:
    if any(
        isinstance(item, dict) and item.get("camera_model") == CANONICAL_CAMERA_MODEL
        for item in capture.get("views") or []
    ):
        return "isaac_lab_camera_rgb_canonical_eye_target_scene_probe"
    return "isaac_lab_camera_rgb_anchor_orbit_scene_probe"


def _real_semantic_pose_robot_view_images(
    state: dict[str, Any],
    target_images: dict[str, Path],
    *,
    width: int,
    height: int,
    render_settle_frames: int = 0,
    isaac_aa_op: int | None = None,
    isaac_tonemap_op: int | None = None,
    isaac_exposure_bias: float | None = None,
    isaac_colorcorr_gain: tuple[float, float, float] | None = None,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
) -> dict[str, str]:
    return real_semantic_pose_robot_view_images(
        SemanticPoseRobotViewRequest(
            state=state,
            target_images=target_images,
            width=width,
            height=height,
            render_settle_frames=render_settle_frames,
            isaac_aa_op=isaac_aa_op,
            isaac_tonemap_op=isaac_tonemap_op,
            isaac_exposure_bias=isaac_exposure_bias,
            isaac_colorcorr_gain=isaac_colorcorr_gain,
            focus_object_id=focus_object_id,
            focus_receptacle_id=focus_receptacle_id,
        ),
        hooks=SemanticPoseRobotViewHooks(
            capture_semantic_pose_robot_views=capture_semantic_pose_robot_views,
            has_required_robot_view_images=_has_required_robot_view_images,
            semantic_pose_robot_view_provenance=_semantic_pose_robot_view_provenance,
            write_state_from_state_arg=write_state_from_state_arg,
        ),
        real_robot_view_rerender_method=REAL_ROBOT_VIEW_RERENDER_METHOD,
        isaac_rby1m_head_camera_prim=ISAAC_RBY1M_HEAD_CAMERA_PRIM,
    )


def _robot_view_focus(
    state: dict[str, Any],
    robot_pose: dict[str, Any],
    *,
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    focus = _focus_payload(
        state=state,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
    )
    target = _vec3(focus.get("focus_position"))
    source = str(focus.get("source") or "")
    if target is None:
        target = _vec3(robot_pose.get("target_position"))
        source = "isaac_usd_world_bounds_robot_pose"
    if target is None:
        target = [0.0, 0.0, 0.0]
        source = "isaac_semantic_pose_default_origin"
    return {
        **focus,
        "has_focus": True,
        "focus_position": target,
        "object_id": focus_object_id,
        "receptacle_id": focus_receptacle_id,
        "source": source,
    }


def _focus_payload(
    *,
    state: dict[str, Any] | None = None,
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    state = state if isinstance(state, dict) else {}
    object_pose = _semantic_object_pose_entry(state, focus_object_id) if focus_object_id else {}
    receptacle_pose = (
        _receptacle_support_pose(state, focus_receptacle_id) if focus_receptacle_id else {}
    )
    object_position = _vec3(object_pose.get("position"))
    receptacle_position = _support_pose_position(receptacle_pose)
    focus_position = (
        object_position
        if object_position is not None
        else receptacle_position
        if receptacle_position is not None
        else None
    )
    has_focus = bool(focus_object_id or focus_receptacle_id)
    focus_mode = "object_closeup" if object_position is not None else "receptacle_context"
    source = (
        "isaac_semantic_pose_object_pose"
        if object_position is not None
        else "isaac_usd_world_bounds_support_pose"
        if receptacle_position is not None
        else "isaac_semantic_pose"
    )
    segmentation_unavailable = {
        "status": "segmentation_unavailable",
        "reason": "Isaac semantic-pose worker has no segmentation mask evidence.",
    }
    return {
        "has_focus": has_focus,
        "object_id": focus_object_id,
        "receptacle_id": focus_receptacle_id,
        "source": source,
        "focus_mode": focus_mode,
        "focus_position": focus_position,
        "object_position": object_position,
        "receptacle_position": receptacle_position,
        "visibility": dict(segmentation_unavailable),
        "fpv_visibility": dict(segmentation_unavailable),
    }


def _semantic_object_pose_entry(
    state: dict[str, Any],
    object_id: str | None,
) -> dict[str, Any]:
    if not object_id:
        return {}
    semantic_pose = _dict(state.get("semantic_pose_state"))
    object_poses = _dict(semantic_pose.get("object_poses"))
    return _dict(object_poses.get(object_id))


def _support_pose_position(pose: dict[str, Any]) -> list[float] | None:
    if not _has_xy(pose):
        return None
    try:
        return [
            float(pose["x"]),
            float(pose["y"]),
            float(pose.get("z", 0.0)),
        ]
    except (TypeError, ValueError):
        return None


def _real_robot_view_images(state: dict[str, Any]) -> dict[str, str]:
    return real_robot_view_images(state, robot_view_keys=ROBOT_VIEW_KEYS)


def _native_render_diagnostics_from_state(state: dict[str, Any]) -> dict[str, Any]:
    diagnostics = _dict(state.get("native_render_diagnostics"))
    if diagnostics:
        return diagnostics
    diagnostics = _dict(
        _dict(state.get("robot_view_camera_diagnostics")).get("native_render_diagnostics")
    )
    if diagnostics:
        return diagnostics
    diagnostics = _dict(
        _dict(_dict(state.get("runtime")).get("rendering")).get("native_render_diagnostics")
    )
    if diagnostics:
        return diagnostics
    return _isaac_native_render_diagnostics_unavailable(
        runtime_mode=str(_dict(state.get("runtime")).get("runtime_mode") or "fake"),
        reason="worker state did not contain native render diagnostics",
    )


def _real_smoke_robot_view_images(real_smoke: dict[str, Any] | None) -> dict[str, str]:
    return real_smoke_robot_view_images(real_smoke, robot_view_keys=ROBOT_VIEW_KEYS)


def _has_required_robot_view_images(images: dict[str, str]) -> bool:
    return has_required_robot_view_images(images, robot_view_keys=ROBOT_VIEW_KEYS)


def _copy_real_robot_view_images(
    source_images: dict[str, str],
    target_images: dict[str, Path],
    *,
    width: int,
    height: int,
) -> dict[str, list[int]]:
    return copy_real_robot_view_images(
        source_images,
        target_images,
        width=width,
        height=height,
        robot_view_keys=ROBOT_VIEW_KEYS,
    )


def _real_snapshot_source_image(state: dict[str, Any]) -> Path:
    return real_snapshot_source_image(state, robot_view_keys=ROBOT_VIEW_KEYS)


def _copy_real_snapshot_image(
    source: Path,
    target: Path,
    *,
    width: int,
    height: int,
) -> list[int]:
    return copy_real_snapshot_image(source, target, width=width, height=height)


def _copy_nonblank_rgb_image(
    source: Path,
    target: Path,
    *,
    width: int,
    height: int,
    description: str,
) -> list[int]:
    return copy_nonblank_rgb_image(
        source,
        target,
        width=width,
        height=height,
        description=description,
    )


def _pil_image_has_variance(image: Image.Image) -> bool:
    return pil_image_has_variance(image)


def _real_rendering_proven(state: dict[str, Any]) -> bool:
    return real_rendering_proven(state)


def _robot_view_provenance(
    runtime_mode: str,
    real_smoke: dict[str, Any] | None,
) -> dict[str, Any]:
    return robot_view_provenance(
        runtime_mode,
        real_smoke,
        robot_view_keys=ROBOT_VIEW_KEYS,
        real_robot_view_capture_method=REAL_ROBOT_VIEW_CAPTURE_METHOD,
    )


def _robot_view_command_provenance(
    state: dict[str, Any],
    *,
    semantic_pose_state_refreshed: bool,
) -> dict[str, Any]:
    return robot_view_command_provenance(
        state,
        semantic_pose_state_refreshed=semantic_pose_state_refreshed,
        robot_view_keys=ROBOT_VIEW_KEYS,
        real_robot_view_rerender_method=REAL_ROBOT_VIEW_RERENDER_METHOD,
    )


def _semantic_pose_robot_view_provenance(
    *,
    mounted_head_camera: bool = False,
    head_camera_equivalent: bool = False,
) -> dict[str, Any]:
    return semantic_pose_robot_view_provenance(
        mounted_head_camera=mounted_head_camera,
        head_camera_equivalent=head_camera_equivalent,
        robot_view_keys=ROBOT_VIEW_KEYS,
        real_robot_view_rerender_method=REAL_ROBOT_VIEW_RERENDER_METHOD,
    )


def _safe_file_stem(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return cleaned or "view"


def _write_placeholder_image(
    path: Path,
    *,
    title: str,
    subtitle: str,
    state: dict[str, Any],
    width: int,
    height: int,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (width, height), (28, 32, 38))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, 58), fill=(55, 68, 82))
    draw.text((16, 14), title[:80], fill=(245, 248, 250))
    draw.text((16, 36), subtitle[:80], fill=(178, 203, 219))
    receptacles = list((state.get("receptacle_index") or {}).keys())
    objects = state.get("scenario", {}).get("objects") or []
    if receptacles:
        cell_w = max(48, (width - 32) // min(len(receptacles), 5))
        for index, receptacle_id in enumerate(receptacles[:10]):
            row = index // 5
            col = index % 5
            x0 = 16 + col * cell_w
            y0 = 82 + row * 88
            fill = (78, 116, 94) if receptacle_id == focus_receptacle_id else (70, 80, 92)
            draw.rectangle((x0, y0, x0 + cell_w - 8, y0 + 68), outline=(140, 159, 176), fill=fill)
            draw.text((x0 + 6, y0 + 6), receptacle_id[:18], fill=(240, 240, 240))
    for index, obj in enumerate(objects[:12]):
        object_id = str(obj.get("object_id", ""))
        location = str(state.get("locations", {}).get(object_id, obj.get("location_id", "")))
        x = 24 + (index % 6) * max(56, (width - 48) // 6)
        y = height - 100 + (index // 6) * 34
        fill = (210, 155, 65) if object_id == focus_object_id else (169, 191, 112)
        draw.ellipse((x, y, x + 18, y + 18), fill=fill, outline=(245, 245, 245))
        draw.text((x + 24, y + 1), f"{object_id[:14]}->{location[:14]}", fill=(230, 230, 230))
    image.save(path)


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return {
        "ok": True,
        "tool": tool,
        "status": "ok",
        "backend": ISAACLAB_SUBPROCESS_BACKEND,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "physical_robot": False,
        "planner_backed": False,
        **payload,
    }


def _error(tool: str, error: str, **payload: Any) -> dict[str, Any]:
    return {
        "ok": False,
        "tool": tool,
        "status": "error",
        "error": error,
        "backend": ISAACLAB_SUBPROCESS_BACKEND,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "physical_robot": False,
        "planner_backed": False,
        **payload,
    }


def read_state(path: Path) -> dict[str, Any]:
    state = json.loads(path.read_text(encoding="utf-8"))
    state["_state_path"] = str(path)
    return state


def write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = {key: value for key, value in state.items() if not key.startswith("_")}
    path.write_text(json.dumps(clean, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_state_from_state_arg(state: dict[str, Any]) -> None:
    write_state(Path(state["_state_path"]), state)


def _count(state: dict[str, Any], tool: str) -> None:
    counts = Counter(state.get("tool_event_counts") or {})
    counts[f"{tool}:request"] += 1
    state["tool_event_counts"] = dict(counts)


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(json.dumps(state["scenario"]))
    by_id = {obj["object_id"]: obj for obj in payload["objects"]}
    for object_id, location_id in state["locations"].items():
        by_id[object_id]["location_id"] = location_id
        containment = (state.get("containment") or {}).get(object_id)
        if containment:
            by_id[object_id].update(containment)
    return payload


def scenario_from_state(state: dict[str, Any]) -> CleanupScenario:
    private = PrivateScoringManifest.from_dict(state["private_manifest"])
    public = state["scenario"]
    objects = tuple(
        CleanupObject(
            object_id=str(item["object_id"]),
            name=str(item["name"]),
            category=str(item["category"]),
            location_id=str(item["location_id"]),
            pickupable=bool(item.get("pickupable", True)),
        )
        for item in public.get("objects", [])
    )
    receptacles = tuple(
        CleanupReceptacle(
            receptacle_id=str(item["receptacle_id"]),
            name=str(item["name"]),
            room_area=str(item.get("room_area") or "unknown"),
            kind=str(item.get("kind") or "receptacle"),
            category=str(item["category"]) if item.get("category") is not None else None,
        )
        for item in public.get("receptacles", [])
    )
    return CleanupScenario(
        scenario_id=str(public["scenario_id"]),
        task=str(public["task"]),
        seed=int(public["seed"]),
        objects=objects,
        receptacles=receptacles,
        private_manifest=private,
    )


def _load_generated_mess_manifest(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError(f"generated mess manifest must be a JSON object: {path}")
    if manifest.get("schema") != GENERATED_MESS_MANIFEST_SCHEMA:
        raise ValueError(
            "generated mess manifest schema mismatch: "
            f"{manifest.get('schema')} != {GENERATED_MESS_MANIFEST_SCHEMA}"
        )
    return manifest


def _scenario_for_init(
    args: argparse.Namespace,
    *,
    generated_mess_manifest: dict[str, Any] | None = None,
) -> CleanupScenario:
    if args.scene_usd_path is not None:
        generated_mess_manifest = None
    if args.map_bundle_dir is None:
        return _scenario_from_generated_mess_manifest_or_limit(
            build_cleanup_scenario(seed=args.seed),
            generated_mess_count=args.generated_mess_count,
            generated_mess_manifest=generated_mess_manifest,
        )
    return _scenario_from_generated_mess_manifest_or_limit(
        _scenario_from_map_bundle(
            args.map_bundle_dir,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
        ),
        generated_mess_count=args.generated_mess_count,
        generated_mess_manifest=generated_mess_manifest,
    )


def _scenario_source(args: argparse.Namespace) -> str:
    return "nav2_map_bundle" if args.map_bundle_dir is not None else "default_cleanup_scenario"


def _effective_scene_index(args: argparse.Namespace) -> int:
    scene_usd_path = getattr(args, "scene_usd_path", None)
    inferred = _scene_index_from_usd_path(scene_usd_path)
    if inferred is not None:
        return inferred
    return int(getattr(args, "scene_index", 0) or 0)


def _scene_index_from_usd_path(path: Any) -> int | None:
    if path is None:
        return None
    for part in reversed(Path(path).parts):
        match = re.search(r"(?:^|_)val_?(\d+)(?:_|$)", part)
        if match:
            return int(match.group(1))
    return None


def _scene_specific_scenario_if_needed(
    *,
    args: argparse.Namespace,
    generated_mess_manifest: dict[str, Any] | None,
    scene_binding_diagnostics: dict[str, Any],
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    real_smoke: dict[str, Any] | None,
) -> CleanupScenario | None:
    if real_smoke is None or args.scene_usd_path is None:
        return None
    if not generated_mess_manifest and scene_binding_diagnostics.get("status") == "selected_bound":
        return None
    return _scenario_from_scene_index(
        scene_source=args.scene_source,
        scene_index=args.scene_index,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        generated_mess_object_ids=tuple(getattr(args, "generated_mess_object_id", None) or ()),
        generated_mess_manifest=generated_mess_manifest,
        object_index=object_index,
        receptacle_index=receptacle_index,
    )


def _scenario_from_scene_index(
    *,
    scene_source: str,
    scene_index: int,
    seed: int,
    generated_mess_count: int,
    generated_mess_object_ids: tuple[str, ...] = (),
    generated_mess_manifest: dict[str, Any] | None = None,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> CleanupScenario | None:
    cleanup_receptacle_index = _cleanup_receptacle_index_for_mess_generation(receptacle_index)
    receptacles = tuple(
        _cleanup_receptacle_from_scene_index(handle, entry)
        for handle, entry in sorted(cleanup_receptacle_index.items())
    )
    if not receptacles:
        return None

    selectable_objects: list[dict[str, Any]] = []
    for handle, entry in sorted(object_index.items()):
        target_id = _scene_target_receptacle_id(entry, cleanup_receptacle_index)
        if not target_id:
            continue
        source_id = _scene_source_receptacle_id(
            entry,
            cleanup_receptacle_index,
            target_id=target_id,
        )
        selectable_objects.append(
            {
                "object_id": handle,
                "name": _scene_object_name(handle, entry),
                "category": _scene_cleanup_object_category(entry),
                "location_id": source_id,
            }
        )

    receptacle_payloads = [receptacle.to_public_dict() for receptacle in receptacles]
    if generated_mess_count < 0:
        raise ValueError("generated_mess_count must be >= 0")
    if generated_mess_count == 0:
        selected = []
    elif generated_mess_manifest:
        selected = targets_from_generated_mess_manifest(
            selectable_objects,
            receptacle_payloads,
            generated_mess_manifest,
            target_count=int(generated_mess_count),
        )
    else:
        selected = select_generated_mess_targets(
            selectable_objects,
            receptacle_payloads,
            target_count=int(generated_mess_count),
            seed=seed,
            object_ids=generated_mess_object_ids or None,
        )

    objects = tuple(
        CleanupObject(
            object_id=str(item["object_id"]),
            name=str(item["name"]),
            category=str(item["category"]),
            location_id=str(item.get("start_receptacle_id") or item["location_id"]),
        )
        for item in selected
    )
    targets = tuple(
        TargetRule(
            object_id=str(item["object_id"]),
            valid_receptacle_ids=(str(item["target_receptacle_id"]),),
        )
        for item in selected
    )

    scenario_id = f"isaac-scene-index-{scene_source}-{scene_index}-{seed}-{len(targets)}"
    return CleanupScenario(
        scenario_id=scenario_id,
        task="Clean up this Isaac-loaded MolmoSpaces scene using scene-indexed objects.",
        seed=seed,
        objects=tuple(objects),
        receptacles=receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=targets,
            success_threshold=generated_mess_success_threshold(len(targets)),
        ),
    )


def _cleanup_receptacle_index_for_mess_generation(
    receptacle_index: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    cleanup = {
        handle: entry
        for handle, entry in receptacle_index.items()
        if _norm(_scene_object_category(entry)) in MOLMOSPACES_CLEANUP_RECEPTACLE_CATEGORY_NORMS
    }
    return cleanup or receptacle_index


def _cleanup_receptacle_from_scene_index(
    handle: str,
    entry: dict[str, Any],
) -> CleanupReceptacle:
    category = _scene_object_category(entry)
    return CleanupReceptacle(
        receptacle_id=handle,
        name=str(entry.get("public_label") or category or handle),
        room_area="isaac_scene",
        kind=str(entry.get("kind") or "receptacle"),
        category=category,
    )


def _scene_object_name(handle: str, entry: dict[str, Any]) -> str:
    category = _scene_object_category(entry)
    asset_id = str(entry.get("asset_id") or "").strip()
    if category and asset_id:
        return f"{category} ({asset_id})"
    return str(entry.get("public_label") or category or handle)


def _scene_object_category(entry: dict[str, Any]) -> str:
    return str(entry.get("category") or entry.get("asset_id") or "object")


def _scene_cleanup_object_category(entry: dict[str, Any]) -> str:
    category = _scene_object_category(entry)
    tokens = _scene_entry_tokens("", entry)
    for category_aliases, _target_aliases in _SCENE_STRICT_CLEANUP_TARGET_ALIASES:
        matched_aliases = tuple(alias for alias in category_aliases if alias in tokens)
        if matched_aliases:
            return _canonical_cleanup_category(category, matched_aliases)
    return category


def _canonical_cleanup_category(category: str, aliases: tuple[str, ...]) -> str:
    category_norm = _norm(category)
    for canonical, accepted in _CANONICAL_CLEANUP_CATEGORY_ALIASES:
        accepted_norms = {_norm(item) for item in accepted}
        alias_matches = any(_norm(alias) in accepted_norms for alias in aliases)
        if category_norm in accepted_norms or alias_matches:
            return canonical
    return category


def _scene_target_receptacle_id(
    entry: dict[str, Any],
    receptacle_index: dict[str, dict[str, Any]],
) -> str:
    entry_tokens = _scene_entry_tokens("", entry)
    for category_aliases, target_aliases in _SCENE_STRICT_CLEANUP_TARGET_ALIASES:
        if any(alias in entry_tokens for alias in category_aliases):
            target_id = _first_receptacle_matching_aliases(receptacle_index, target_aliases)
            if target_id:
                return target_id
    return ""


def _first_receptacle_matching_aliases(
    receptacle_index: dict[str, dict[str, Any]],
    aliases: tuple[str, ...],
) -> str:
    for handle, entry in sorted(receptacle_index.items()):
        tokens = _scene_entry_tokens(handle, entry)
        if any(alias in tokens for alias in aliases):
            return handle
    return ""


def _scene_source_receptacle_id(
    entry: dict[str, Any],
    receptacle_index: dict[str, dict[str, Any]],
    *,
    target_id: str,
) -> str:
    parent = str(entry.get("parent") or "")
    if parent and parent in receptacle_index and parent != target_id:
        return parent
    for handle in sorted(receptacle_index):
        if handle != target_id:
            return handle
    return target_id


def _scene_entry_tokens(handle: str, entry: dict[str, Any]) -> set[str]:
    return _scene_match_tokens(
        handle,
        entry.get("metadata_handle"),
        entry.get("public_label"),
        entry.get("category"),
        entry.get("metadata_object_id"),
        entry.get("asset_id"),
    )


_SCENE_CLEANUP_TARGET_ALIASES = (
    (
        ("dish", "cup", "mug", "plate", "bowl", "utensil", "fork", "knife", "spoon"),
        ("sink", "countertop"),
    ),
    (
        ("book", "newspaper", "notebook", "paper", "magazine"),
        ("shelvingunit", "bookshelf", "shelf", "desk"),
    ),
    (
        ("food", "apple", "bread", "egg", "potato", "lettuce", "tomato", "banana", "orange"),
        ("fridge", "refrigerator"),
    ),
    (
        ("remotecontrol", "remote", "phone", "cellphone", "laptop", "tablet", "alarmclock"),
        ("tvstand", "televisionstand"),
    ),
    (("pillow", "teddybear", "cushion"), ("bed", "sofa")),
    (("linen", "towel", "cloth", "blanket", "shirt", "clothing"), ("laundryhamper", "hamper")),
    (("toy", "toycar", "ball", "basketball", "soccer"), ("toybin",)),
)

_SCENE_STRICT_CLEANUP_TARGET_ALIASES = (
    (("cup", "mug", "plate", "bowl"), ("sink",)),
    (("book", "newspaper"), ("shelvingunit", "desk")),
    (("apple", "bread", "egg", "potato", "lettuce"), ("fridge", "refrigerator")),
    (("remotecontrol",), ("tvstand", "televisionstand")),
    (("pillow", "teddybear"), ("bed", "sofa")),
)

_CANONICAL_CLEANUP_CATEGORY_ALIASES = (
    ("Plate", ("dish", "plate", "bowl", "cup", "mug", "utensil", "fork", "knife", "spoon")),
    ("Book", ("book", "newspaper", "notebook", "paper", "magazine")),
    (
        "Potato",
        ("food", "apple", "bread", "egg", "potato", "lettuce", "tomato", "banana", "orange"),
    ),
    (
        "RemoteControl",
        ("remotecontrol", "remote", "phone", "cellphone", "laptop", "tablet", "alarmclock"),
    ),
    ("TeddyBear", ("teddybear", "teddy", "plush")),
    ("Pillow", ("pillow", "cushion")),
    ("Towel", ("linen", "towel", "cloth", "blanket", "shirt", "clothing")),
    ("ToyCar", ("toy", "toycar", "ball", "basketball", "soccer")),
)


def _scenario_from_generated_mess_manifest_or_limit(
    scenario: CleanupScenario,
    *,
    generated_mess_count: int,
    generated_mess_manifest: dict[str, Any] | None = None,
) -> CleanupScenario:
    if not generated_mess_manifest:
        return _limit_scenario_to_generated_mess_count(
            scenario,
            generated_mess_count=generated_mess_count,
        )
    if generated_mess_count < 0:
        raise ValueError("generated_mess_count must be >= 0")
    if generated_mess_count == 0:
        return _scenario_without_private_targets(
            scenario,
            scenario_id=f"{scenario.scenario_id}-canonical-mess-0",
            objects=(),
        )
    objects = [item.to_public_dict() for item in scenario.objects]
    receptacles = [item.to_public_dict() for item in scenario.receptacles]
    selected = targets_from_generated_mess_manifest(
        objects,
        receptacles,
        generated_mess_manifest,
        target_count=int(generated_mess_count),
    )
    target_ids = {str(item["object_id"]) for item in selected}
    source_objects = {item.object_id: item for item in scenario.objects}
    selected_objects = []
    for target in selected:
        object_id = str(target["object_id"])
        source = source_objects[object_id]
        selected_objects.append(
            CleanupObject(
                object_id=source.object_id,
                name=source.name,
                category=source.category,
                location_id=str(target.get("start_receptacle_id") or source.location_id),
                pickupable=source.pickupable,
            )
        )
    targets = tuple(
        TargetRule(
            object_id=str(item["object_id"]),
            valid_receptacle_ids=tuple(str(value) for value in item["valid_receptacle_ids"]),
        )
        for item in selected
    )
    scenario_id = f"{scenario.scenario_id}-canonical-mess-{len(targets)}"
    return CleanupScenario(
        scenario_id=scenario_id,
        task=scenario.task,
        seed=scenario.seed,
        objects=tuple(item for item in selected_objects if item.object_id in target_ids),
        receptacles=scenario.receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=targets,
            success_threshold=generated_mess_success_threshold(len(targets)),
        ),
    )


def _limit_scenario_to_generated_mess_count(
    scenario: CleanupScenario,
    *,
    generated_mess_count: int,
) -> CleanupScenario:
    count = int(generated_mess_count)
    if count < 0:
        raise ValueError("generated_mess_count must be >= 0")
    if count == 0:
        return _scenario_without_private_targets(
            scenario,
            scenario_id=f"{scenario.scenario_id}-isaac-0",
            objects=(),
        )
    targets = tuple(scenario.private_manifest.targets[:count])
    if not targets:
        return scenario
    target_object_ids = {target.object_id for target in targets}
    objects = tuple(item for item in scenario.objects if item.object_id in target_object_ids)
    if not objects:
        return scenario
    scenario_id = f"{scenario.scenario_id}-isaac-{len(targets)}"
    return CleanupScenario(
        scenario_id=scenario_id,
        task=scenario.task,
        seed=scenario.seed,
        objects=objects,
        receptacles=scenario.receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=targets,
            success_threshold=len(targets),
        ),
    )


def _scenario_without_private_targets(
    scenario: CleanupScenario,
    *,
    scenario_id: str,
    objects: tuple[CleanupObject, ...],
) -> CleanupScenario:
    return CleanupScenario(
        scenario_id=scenario_id,
        task=scenario.task,
        seed=scenario.seed,
        objects=objects,
        receptacles=scenario.receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=(),
            success_threshold=0,
        ),
    )


def _scenario_from_map_bundle(
    bundle_dir: Path,
    *,
    seed: int,
    generated_mess_count: int,
) -> CleanupScenario:
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    raw_fixtures = [dict(item) for item in semantics.get("fixtures") or []]
    if not raw_fixtures:
        return build_cleanup_scenario(seed=seed)

    receptacles = tuple(_cleanup_receptacle_from_fixture(item) for item in raw_fixtures)
    target_specs = _map_aligned_target_specs(raw_fixtures)
    if not target_specs:
        return build_cleanup_scenario(seed=seed)

    count = max(1, int(generated_mess_count))
    objects: list[CleanupObject] = []
    targets: list[TargetRule] = []
    for index in range(count):
        spec = target_specs[index % len(target_specs)]
        cycle = index // len(target_specs) + 1
        object_id = spec["object_id"] if cycle == 1 else f"{spec['object_id']}_{cycle}"
        source_id = str(spec["source_fixture_id"])
        target_id = str(spec["target_fixture_id"])
        objects.append(
            CleanupObject(
                object_id=object_id,
                name=str(spec["name"]),
                category=str(spec["category"]),
                location_id=source_id,
            )
        )
        targets.append(TargetRule(object_id=object_id, valid_receptacle_ids=(target_id,)))

    scenario_id = f"isaac-map-aligned-{bundle_dir.name}-{seed}"
    return CleanupScenario(
        scenario_id=scenario_id,
        task="Clean up this room by putting misplaced objects in appropriate places.",
        seed=seed,
        objects=tuple(objects),
        receptacles=receptacles,
        private_manifest=PrivateScoringManifest(
            scenario_id=scenario_id,
            targets=tuple(targets),
            success_threshold=len(targets),
        ),
    )


def _initial_receptacle_id(scenario: CleanupScenario) -> str:
    if scenario.objects:
        return scenario.objects[0].location_id
    if scenario.receptacles:
        return scenario.receptacles[0].receptacle_id
    return "floor_01"


def _cleanup_receptacle_from_fixture(fixture: dict[str, Any]) -> CleanupReceptacle:
    fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
    category = str(fixture.get("category") or fixture.get("name") or fixture_id)
    return CleanupReceptacle(
        receptacle_id=fixture_id,
        name=str(fixture.get("name") or fixture_id),
        room_area=str(fixture.get("room_id") or fixture.get("room_area") or "unknown"),
        kind="receptacle",
        category=category,
    )


def _map_aligned_target_specs(fixtures: list[dict[str, Any]]) -> list[dict[str, str]]:
    candidates = [
        {
            "object_id": "mug_01",
            "name": "ceramic mug",
            "category": "dish",
            "target_aliases": ("sink", "countertop"),
            "source_aliases": ("sofa", "diningtable", "desk", "bed"),
        },
        {
            "object_id": "plate_01",
            "name": "dinner plate",
            "category": "dish",
            "target_aliases": ("sink", "countertop"),
            "source_aliases": ("diningtable", "sofa", "desk", "bed"),
        },
        {
            "object_id": "book_01",
            "name": "paperback book",
            "category": "book",
            "target_aliases": ("shelvingunit", "bookshelf", "shelf", "desk"),
            "source_aliases": ("sofa", "diningtable", "bed"),
        },
        {
            "object_id": "apple_01",
            "name": "apple",
            "category": "food",
            "target_aliases": ("fridge", "refrigerator"),
            "source_aliases": ("desk", "diningtable", "countertop"),
        },
        {
            "object_id": "remote_01",
            "name": "TV remote",
            "category": "electronics",
            "target_aliases": ("tvstand", "tv stand", "stand"),
            "source_aliases": ("bed", "desk", "diningtable", "sofa"),
        },
    ]
    specs = []
    for candidate in candidates:
        target = _first_fixture_matching(fixtures, candidate["target_aliases"])
        source = _first_fixture_matching(
            fixtures,
            candidate["source_aliases"],
            exclude_fixture_id=str(target.get("fixture_id") or "") if target else "",
        )
        if target is None or source is None:
            continue
        specs.append(
            {
                "object_id": str(candidate["object_id"]),
                "name": str(candidate["name"]),
                "category": str(candidate["category"]),
                "source_fixture_id": str(source["fixture_id"]),
                "target_fixture_id": str(target["fixture_id"]),
            }
        )
    return specs


def _first_fixture_matching(
    fixtures: list[dict[str, Any]],
    aliases: tuple[str, ...],
    *,
    exclude_fixture_id: str = "",
) -> dict[str, Any] | None:
    for alias in aliases:
        alias_norm = _norm(alias)
        for fixture in fixtures:
            fixture_id = str(fixture.get("fixture_id") or "")
            if fixture_id == exclude_fixture_id:
                continue
            text = _norm(
                " ".join(str(fixture.get(key, "")) for key in ("fixture_id", "category", "name"))
            )
            if alias_norm and alias_norm in text:
                return fixture
    return None


def _norm(value: Any) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _json_roundtrip(value: Any) -> Any:
    return json.loads(json.dumps(value))


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _has_xy(value: dict[str, Any]) -> bool:
    if "x" not in value or "y" not in value:
        return False
    try:
        float(value["x"])
        float(value["y"])
    except (TypeError, ValueError):
        return False
    return True


def _index_or_default(
    value: Any,
    default: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict) or not value:
        return default
    return {
        str(key): dict(item) for key, item in value.items() if isinstance(item, dict)
    } or default


def _objects_by_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["object_id"]): item for item in state["scenario"]["objects"]}


def _receptacles_by_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(item["receptacle_id"]): item for item in state["scenario"]["receptacles"]}


def _object_index(scenario: CleanupScenario) -> dict[str, dict[str, Any]]:
    return {
        item.object_id: {
            "usd_prim_path": f"/World/Scene/Objects/{item.object_id}",
            "category": item.category,
            "public_label": item.name,
        }
        for item in scenario.objects
    }


def _receptacle_index(scenario: CleanupScenario) -> dict[str, dict[str, Any]]:
    return {
        item.receptacle_id: {
            "usd_prim_path": f"/World/Scene/Receptacles/{item.receptacle_id}",
            "category": item.category or item.kind,
            "public_label": item.name,
            "support_pose": _pose_near(item.receptacle_id),
        }
        for item in scenario.receptacles
    }


def _pose_near(anchor_id: str) -> dict[str, float | str]:
    value = sum(ord(char) for char in anchor_id)
    return {
        "frame": "world",
        "x": round((value % 17) * 0.17, 3),
        "y": round(((value // 17) % 17) * 0.13, 3),
        "z": 0.0,
        "yaw_deg": float((value * 13) % 360),
    }


def _robot_payload(robot_name: str) -> dict[str, Any]:
    return robot_payload(robot_name, _rby1m_robot_import_plan(robot_name))


def _rby1m_robot_import_plan(robot_name: str) -> dict[str, Any]:
    return rby1m_robot_import_plan(
        robot_name,
        robot_usd_path=ISAAC_RBY1M_ROBOT_USD_PATH,
        import_summary_path=ISAAC_RBY1M_ROBOT_IMPORT_SUMMARY_PATH,
        find_urdf=_find_rby1m_isaac_urdf,
        repo_path=_repo_path,
        load_json_if_file=_load_json_if_file,
        head_camera_prim=ISAAC_RBY1M_HEAD_CAMERA_PRIM,
    )


def _repo_path(path: Path) -> Path:
    return repo_path(path, anchor_file=__file__)


def _load_json_if_file(path: Path) -> dict[str, Any]:
    return load_json_if_file(path)


def _find_rby1m_isaac_urdf() -> Path | None:
    return find_rby1m_isaac_urdf()


def _scene_usd_path(scene_source: str, scene_index: int) -> str:
    return _scene_usd_path_impl(scene_source, scene_index)


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Callable

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image

from roboclaws.household.backend import HELD_LOCATION_ID
from roboclaws.household.camera_control import (
    DEFAULT_SCENE_PROBE_LIGHTING_PROFILE,
    normalize_camera_control_request,
)
from roboclaws.household.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_SUBPROCESS_BACKEND,
)
from roboclaws.household.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
)
from scripts.isaac_lab_cleanup import (
    isaac_mapping_diagnostics,
    isaac_placement_resolution,
    isaac_robot_camera_stage,
    isaac_robot_pose_focus,
    isaac_scenario_builders,
    isaac_scenario_state,
    isaac_scene_camera_geometry,
    isaac_scene_index_geometry,
    isaac_semantic_pose_stage,
    isaac_worker_commands,
    isaac_worker_outputs,
    isaac_worker_protocol,
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
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    ISAAC_PLACEMENT_RESOLVER_SOURCE as _ISAAC_PLACEMENT_RESOLVER_SOURCE,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    PLACEMENT_DIAGNOSTIC_SCHEMA as _PLACEMENT_DIAGNOSTIC_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_placement_resolution import (
    IsaacPlacementHooks,
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
from scripts.isaac_lab_cleanup.isaac_robot_camera_stage import (
    IsaacRobotCameraStageHooks,
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
from scripts.isaac_lab_cleanup.isaac_robot_pose_focus import (
    IsaacRobotPoseHooks,
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
from scripts.isaac_lab_cleanup.isaac_scenario_builders import (
    CANONICAL_CLEANUP_CATEGORY_ALIASES,
    SCENE_CLEANUP_TARGET_ALIASES,
    SCENE_STRICT_CLEANUP_TARGET_ALIASES,
    canonical_cleanup_category,
    cleanup_receptacle_from_fixture,
    cleanup_receptacle_from_scene_index,
    cleanup_receptacle_index_for_mess_generation,
    effective_scene_index,
    first_fixture_matching,
    first_receptacle_matching_aliases,
    initial_receptacle_id,
    limit_scenario_to_generated_mess_count,
    load_generated_mess_manifest,
    map_aligned_target_specs,
    scenario_for_init,
    scenario_from_generated_mess_manifest_or_limit,
    scenario_from_map_bundle,
    scenario_from_scene_index,
    scenario_without_private_targets,
    scene_cleanup_object_category,
    scene_entry_tokens,
    scene_index_from_usd_path,
    scene_object_category,
    scene_object_name,
    scene_source_receptacle_id,
    scene_specific_scenario_if_needed,
    scene_target_receptacle_id,
)
from scripts.isaac_lab_cleanup.isaac_scenario_state import IsaacScenarioStateHooks
from scripts.isaac_lab_cleanup.isaac_scene_bindings import (
    SCENE_BINDING_SCHEMA as _SCENE_BINDING_SCHEMA,
)
from scripts.isaac_lab_cleanup.isaac_scene_bindings import (
    bind_public_scene_item,
    scene_binding_diagnostics,
    scene_index_match,
)
from scripts.isaac_lab_cleanup.isaac_scene_camera_capture import (
    IsaacSceneCameraCaptureHooks,
    IsaacSceneCameraCaptureRequest,
    capture_isaac_lab_scene_camera_views,
    capture_scene_camera_request_with_existing_sim,
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
from scripts.isaac_lab_cleanup.isaac_scene_index_geometry import (
    IsaacUsdSceneIndexHooks,
    authored_reference_asset_paths,
    fallback_room_outlines_from_indices,
    is_local_reference_asset_path,
    local_reference_asset_missing,
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
from scripts.isaac_lab_cleanup.isaac_semantic_pose_stage import (
    IsaacSemanticPoseStageHooks,
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
    usd_support_surface_score,
    usd_support_surface_union_entry,
)
from scripts.isaac_lab_cleanup.isaac_usd_xform import (
    set_usd_xform_translate as _set_usd_xform_translate,
)
from scripts.isaac_lab_cleanup.isaac_worker_cli import build_arg_parser
from scripts.isaac_lab_cleanup.isaac_worker_commands import (
    IsaacWorkerCommandHooks,
)
from scripts.isaac_lab_cleanup.isaac_worker_outputs import (
    IsaacWorkerOutputHooks,
)

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
    return isaac_scene_index_geometry.inspect_usd_scene_index(
        usd_path,
        hooks=_isaac_usd_scene_index_hooks(),
    )


def _isaac_usd_scene_index_hooks() -> IsaacUsdSceneIndexHooks:
    return IsaacUsdSceneIndexHooks(
        annotate_usd_index_geometry=_annotate_usd_index_geometry,
        authored_reference_asset_paths=_authored_reference_asset_paths,
        dict_value=_dict,
        iter_usd_prim_range=_iter_usd_prim_range,
        is_object_prim_path=_is_object_prim_path,
        is_receptacle_prim_path=_is_receptacle_prim_path,
        local_reference_asset_missing=_local_reference_asset_missing,
        merge_molmospaces_metadata_index=_merge_molmospaces_metadata_index,
        pose_near=_pose_near,
        room_outline_from_usd_prim=_room_outline_from_usd_prim,
        round_vec3=_round_vec3,
        support_pose_from_support_surface=_support_pose_from_support_surface,
        support_pose_from_usd_bounds=_support_pose_from_usd_bounds,
        usd_handle_from_prim=_usd_handle_from_prim,
        usd_index_entry=_usd_index_entry,
        usd_receptacle_support_surfaces=_usd_receptacle_support_surfaces,
        usd_world_bounds=_usd_world_bounds,
        usd_world_root_position=_usd_world_root_position,
    )


def _annotate_usd_index_geometry(
    *,
    usd_path: Path,
    stage: Any,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    usd_geom: Any,
) -> None:
    return isaac_scene_index_geometry.annotate_usd_index_geometry(
        usd_path=usd_path,
        stage=stage,
        object_index=object_index,
        receptacle_index=receptacle_index,
        usd_geom=usd_geom,
        hooks=_isaac_usd_scene_index_hooks(),
    )


def _usd_prim_geometry_diagnostics(*, usd_path: Path, prim: Any, usd_geom: Any) -> dict[str, Any]:
    return isaac_scene_index_geometry.usd_prim_geometry_diagnostics(
        usd_path=usd_path,
        prim=prim,
        usd_geom=usd_geom,
        hooks=_isaac_usd_scene_index_hooks(),
    )


def _usd_world_bounds(prim: Any, *, usd_geom: Any) -> dict[str, Any] | None:
    return isaac_scene_index_geometry.usd_world_bounds(
        prim,
        usd_geom=usd_geom,
        round_vec3=_round_vec3,
    )


def _usd_world_root_position(prim: Any, *, usd_geom: Any) -> list[float] | None:
    return isaac_scene_index_geometry.usd_world_root_position(
        prim,
        usd_geom=usd_geom,
        round_vec3=_round_vec3,
    )


def _usd_receptacle_support_surfaces(*, prim: Any, usd_geom: Any) -> list[dict[str, Any]]:
    return isaac_scene_index_geometry.receptacle_support_surfaces(
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
    return isaac_scene_index_geometry.room_outline_from_usd_prim(
        prim_path,
        prim,
        usd_geom=usd_geom,
        world_bounds=_usd_world_bounds,
    )


def _iter_usd_prim_range(prim: Any) -> Any:
    return isaac_scene_index_geometry.iter_usd_prim_range(prim)


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
    return capture_scene_camera_request_with_existing_sim(
        camera_request=camera_request,
        output_dir=output_dir,
        width=width,
        height=height,
        sim=sim,
        sim_utils=sim_utils,
        stage_utils=stage_utils,
        camera_type=camera_type,
        camera_cfg_type=camera_cfg_type,
        torch=torch,
        np=np,
        scene_bounds=scene_bounds,
        normalize_camera_control_request=normalize_camera_control_request,
        ensure_capture_lighting=_ensure_capture_lighting,
        horizontal_aperture_from_lens=_horizontal_aperture_from_lens,
        isaac_native_render_diagnostics=_isaac_native_render_diagnostics,
        camera_render_product_paths=_camera_render_product_paths,
        isaac_scene_camera_view_spec=_isaac_scene_camera_view_spec,
        rgb_tensor_to_uint8=_rgb_tensor_to_uint8,
        image_has_variance=_image_has_variance,
        renderer_mode=REAL_SMOKE_RENDERER_MODE,
    )


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
    return isaac_semantic_pose_stage.apply_semantic_pose_state_to_stage(
        stage_utils=stage_utils,
        semantic_pose_state=semantic_pose_state,
        hooks=IsaacSemanticPoseStageHooks(
            dict_value=_dict,
            set_usd_xform_translate=_set_usd_xform_translate,
            semantic_pose_target_position=_semantic_pose_target_position,
            vec3=_vec3,
            world_position_to_parent_local_translate=_world_position_to_parent_local_translate,
        ),
    )


def _world_position_to_parent_local_translate(
    *,
    UsdGeom: Any,
    prim: Any,
    world_position: tuple[float, float, float],
) -> tuple[float, float, float]:
    return isaac_semantic_pose_stage.world_position_to_parent_local_translate(
        UsdGeom=UsdGeom,
        prim=prim,
        world_position=world_position,
    )


def _semantic_pose_target_position(
    *,
    support_id: str,
    receptacle_index: dict[str, Any],
    fallback_pose: dict[str, Any],
) -> tuple[float, float, float] | None:
    return isaac_semantic_pose_stage.semantic_pose_target_position(
        support_id=support_id,
        receptacle_index=receptacle_index,
        fallback_pose=fallback_pose,
        dict_value=_dict,
        vec3=_vec3,
    )


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
    return isaac_robot_camera_stage.ensure_rby1m_robot_on_stage(
        stage_utils=stage_utils,
        robot_import=robot_import,
    )


def _isaac_robot_camera_stage_hooks() -> IsaacRobotCameraStageHooks:
    return IsaacRobotCameraStageHooks(
        dict_value=_dict,
        has_xy=_has_xy,
        horizontal_aperture_from_lens=_horizontal_aperture_from_lens,
        matrix4d_rowmajor=_matrix4d_rowmajor,
        optional_float=_optional_float,
        robot_pose_yaw_deg=_robot_pose_yaw_deg,
        static_head_camera_pose_for_pitch=_static_head_camera_pose_for_pitch,
        tensor_first_vec3=_tensor_first_vec3,
        usd_attr_float=_usd_attr_float,
        usd_camera_fov_metadata=_usd_camera_fov_metadata,
        usd_vec=_usd_vec,
    )


def _position_robot_for_head_camera_view(
    *,
    stage_utils: Any,
    scene_bounds: dict[str, list[float]] | None,
    semantic_pose_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return isaac_robot_camera_stage.position_robot_for_head_camera_view(
        stage_utils=stage_utils,
        scene_bounds=scene_bounds,
        semantic_pose_state=semantic_pose_state,
        hooks=_isaac_robot_camera_stage_hooks(),
    )


def _apply_static_head_camera_pitch(
    *,
    stage: Any,
    head_pitch: float | None,
) -> dict[str, Any]:
    return isaac_robot_camera_stage.apply_static_head_camera_pitch(
        stage=stage,
        head_pitch=head_pitch,
        hooks=_isaac_robot_camera_stage_hooks(),
    )


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
    return isaac_robot_camera_stage.static_head_pitch_note(head_pitch_application)


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
    return isaac_robot_camera_stage.usd_camera_diagnostics(
        stage_utils=stage_utils,
        prim_path=prim_path,
        view_name=view_name,
        width=width,
        height=height,
        robot_pose_application=robot_pose_application,
        lens_application=lens_application,
        hooks=_isaac_robot_camera_stage_hooks(),
    )


def _isaac_eye_target_camera_diagnostics(
    *,
    view_name: str,
    positions: Any,
    targets: Any,
    width: int,
    height: int,
    camera_basis: str = "scene_bounds_eye_target",
) -> dict[str, Any]:
    return isaac_robot_camera_stage.isaac_eye_target_camera_diagnostics(
        view_name=view_name,
        positions=positions,
        targets=targets,
        width=width,
        height=height,
        camera_basis=camera_basis,
        hooks=_isaac_robot_camera_stage_hooks(),
    )


def _configure_rby1m_head_camera_lens(
    *,
    stage_utils: Any,
    width: int,
    height: int,
) -> dict[str, Any]:
    return isaac_robot_camera_stage.configure_rby1m_head_camera_lens(
        stage_utils=stage_utils,
        width=width,
        height=height,
        hooks=_isaac_robot_camera_stage_hooks(),
    )


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
    return isaac_scene_camera_geometry.load_camera_request_from_args(
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


def _isaac_scenario_state_hooks() -> IsaacScenarioStateHooks:
    return IsaacScenarioStateHooks(
        dict_value=_dict,
        isaac_placement_diagnostic=_isaac_placement_diagnostic,
        receptacle_prefers_inside=_receptacle_prefers_inside,
        receptacle_requires_open=_receptacle_requires_open,
        receptacles_by_id=_receptacles_by_id,
        resolve_isaac_placement=_resolve_isaac_placement,
        round_vec3=_round_vec3,
        vec3=_vec3,
    )


def _seed_generated_mess_placements(state: dict[str, Any]) -> None:
    return isaac_scenario_state.seed_generated_mess_placements(
        state,
        hooks=_isaac_scenario_state_hooks(),
    )


def _manifest_target_by_object_id(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return isaac_scenario_state.manifest_target_by_object_id(
        state,
        hooks=_isaac_scenario_state_hooks(),
    )


def _target_start_receptacle(
    state: dict[str, Any],
    wrong_pool: list[dict[str, Any]],
    index: int,
    target_ids: set[str],
    manifest_target: dict[str, Any] | None,
) -> dict[str, Any]:
    return isaac_scenario_state.target_start_receptacle(
        state,
        wrong_pool,
        index,
        target_ids,
        manifest_target,
        hooks=_isaac_scenario_state_hooks(),
    )


def _target_relation(
    receptacle: dict[str, Any],
    manifest_target: dict[str, Any] | None,
) -> str:
    return isaac_scenario_state.target_relation(
        receptacle,
        manifest_target,
        hooks=_isaac_scenario_state_hooks(),
    )


def _target_placement_index(index: int, manifest_target: dict[str, Any] | None) -> int:
    return isaac_scenario_state.target_placement_index(index, manifest_target)


def _mess_wrong_receptacle_pool(
    state: dict[str, Any],
    target_receptacle_ids: set[str],
) -> list[dict[str, Any]]:
    return isaac_scenario_state.mess_wrong_receptacle_pool(
        state,
        target_receptacle_ids,
        hooks=_isaac_scenario_state_hooks(),
    )


def _apply_object_location(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    relation: str,
    placement_index: int,
    source: str,
) -> dict[str, Any]:
    return isaac_scenario_state.apply_object_location(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        placement_index=placement_index,
        source=source,
        hooks=_isaac_scenario_state_hooks(),
    )


def _set_public_scenario_object_location(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    relation: str,
) -> None:
    return isaac_scenario_state.set_public_scenario_object_location(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        relation=relation,
        hooks=_isaac_scenario_state_hooks(),
    )


def _first_target_object_location(state: dict[str, Any]) -> str:
    return isaac_scenario_state.first_target_object_location(
        state,
        hooks=_isaac_scenario_state_hooks(),
    )


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
    return isaac_placement_resolution.resolve_isaac_placement(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        relation=relation,
        source=source,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_state_objects_for_clearance(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return isaac_placement_resolution.isaac_state_objects_for_clearance(
        state, hooks=_isaac_placement_hooks()
    )


def _isaac_direct_support_placement(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
) -> dict[str, Any] | None:
    return isaac_placement_resolution.isaac_direct_support_placement(
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
    return isaac_placement_resolution.isaac_receptacle_support_surface(
        state,
        receptacle_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_receptacle_support_surfaces(
    state: dict[str, Any],
    receptacle_id: str,
) -> list[dict[str, Any]]:
    return isaac_placement_resolution.isaac_receptacle_support_surfaces(
        state,
        receptacle_id,
        hooks=_isaac_placement_hooks(),
    )


def _normalize_support_surface(surface: Any) -> dict[str, Any] | None:
    return isaac_placement_resolution.normalize_support_surface(surface)


def _surface_candidate_positions(
    surface: dict[str, Any],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
    clearance: float,
    index: int,
) -> list[list[float]]:
    return isaac_placement_resolution.surface_candidate_positions(
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
    return isaac_placement_resolution.candidate_has_direct_support(position, surface, footprint)


def _isaac_candidate_is_clear_of_dynamic_objects(
    state: dict[str, Any],
    *,
    object_id: str,
    position: list[float],
    footprint: tuple[float, float],
    bottom_offset: float,
) -> bool:
    return isaac_placement_resolution.isaac_candidate_is_clear_of_dynamic_objects(
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
    return isaac_placement_resolution.aabb_xy_overlaps(first, second, margin=margin)


def _isaac_object_current_aabb(state: dict[str, Any], object_id: str) -> dict[str, float] | None:
    return isaac_placement_resolution.isaac_object_current_aabb(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _elevated_position_over_surface(
    surface: dict[str, Any],
    *,
    bottom_offset: float,
) -> list[float]:
    return isaac_placement_resolution.elevated_position_over_surface(
        surface, bottom_offset=bottom_offset
    )


def _isaac_fallback_placement_position(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
) -> list[float]:
    return isaac_placement_resolution.isaac_fallback_placement_position(
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
    return isaac_placement_resolution.isaac_object_footprint_half_extents(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_object_bottom_offset(state: dict[str, Any], object_id: str) -> float:
    return isaac_placement_resolution.isaac_object_bottom_offset(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_object_height(state: dict[str, Any], object_id: str) -> float:
    return isaac_placement_resolution.isaac_object_height(
        state, object_id, hooks=_isaac_placement_hooks()
    )


def _isaac_object_surface_lift(category: Any) -> float:
    return isaac_placement_resolution.isaac_object_surface_lift(category, norm=_norm)


def _isaac_direct_support_clearance(
    obj: dict[str, Any],
    receptacle: dict[str, Any],
) -> float:
    return isaac_placement_resolution.isaac_direct_support_clearance(
        obj,
        receptacle,
        norm=_norm,
        receptacle_text=_receptacle_text,
    )


def _isaac_object_world_bounds(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return isaac_placement_resolution.isaac_object_world_bounds(
        state,
        object_id,
        hooks=_isaac_placement_hooks(),
    )


def _isaac_receptacle_world_bounds(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return isaac_placement_resolution.isaac_receptacle_world_bounds(
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
    return isaac_placement_resolution.isaac_index_entry(
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
    return isaac_placement_resolution.isaac_placement_diagnostic(
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


def _isaac_worker_command_hooks() -> IsaacWorkerCommandHooks:
    return IsaacWorkerCommandHooks(
        apply_object_location=_apply_object_location,
        count=_count,
        dict_value=_dict,
        error=_error,
        has_xy=_has_xy,
        isaac_placement_diagnostic=_isaac_placement_diagnostic,
        objects_by_id=_objects_by_id,
        ok=_ok,
        public_state=_public_state,
        receptacles_by_id=_receptacles_by_id,
        record_semantic_pose_event=_record_semantic_pose_event,
        record_waypoint_pose_event=_record_waypoint_pose_event,
        robot_pose_for_receptacle=_robot_pose_for_receptacle,
        robot_pose_for_waypoint=_robot_pose_for_waypoint,
        scenario_from_state=scenario_from_state,
        write_state_from_state_arg=write_state_from_state_arg,
    )


def observe(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.observe(args, state, hooks=_isaac_worker_command_hooks())


def navigate_to_object(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.navigate_to_object(
        args, state, hooks=_isaac_worker_command_hooks()
    )


def navigate_to_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.navigate_to_receptacle(
        args, state, hooks=_isaac_worker_command_hooks()
    )


def navigate_to_waypoint(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.navigate_to_waypoint(
        args, state, hooks=_isaac_worker_command_hooks()
    )


def pick(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.pick(args, state, hooks=_isaac_worker_command_hooks())


def open_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.open_receptacle(args, state, hooks=_isaac_worker_command_hooks())


def close_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.close_receptacle(args, state, hooks=_isaac_worker_command_hooks())


def place(args: argparse.Namespace, state: dict[str, Any], *, relation: str) -> dict[str, Any]:
    return isaac_worker_commands.place(
        args, state, relation=relation, hooks=_isaac_worker_command_hooks()
    )


def done(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_commands.done(args, state, hooks=_isaac_worker_command_hooks())


def _isaac_worker_output_hooks() -> IsaacWorkerOutputHooks:
    return IsaacWorkerOutputHooks(
        camera_capture_provenance=_camera_capture_provenance,
        camera_capture_variant=_camera_capture_variant,
        capture_scene_camera_views=capture_scene_camera_views,
        copy_real_robot_view_images=_copy_real_robot_view_images,
        copy_real_snapshot_image=_copy_real_snapshot_image,
        count=_count,
        dict_value=_dict,
        error=_error,
        has_xy=_has_xy,
        load_camera_request_from_args=_load_camera_request_from_args,
        native_render_diagnostics_from_state=_native_render_diagnostics_from_state,
        ok=_ok,
        real_rendering_proven=_real_rendering_proven,
        real_robot_view_images=_real_robot_view_images,
        real_semantic_pose_robot_view_images=_real_semantic_pose_robot_view_images,
        real_snapshot_source_image=_real_snapshot_source_image,
        robot_pose_for_receptacle=_robot_pose_for_receptacle,
        robot_view_camera_control_contract=_robot_view_camera_control_contract,
        robot_view_command_provenance=_robot_view_command_provenance,
        robot_view_focus=_robot_view_focus,
        robot_view_rendered_robot_pose=_robot_view_rendered_robot_pose,
        safe_file_stem=_safe_file_stem,
        write_placeholder_image=_write_placeholder_image,
        write_state_from_state_arg=write_state_from_state_arg,
        real_smoke_capture_method=REAL_SMOKE_CAPTURE_METHOD,
    )


def write_snapshot(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_outputs.write_snapshot(args, state, hooks=_isaac_worker_output_hooks())


def write_robot_views(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_outputs.write_robot_views(args, state, hooks=_isaac_worker_output_hooks())


def _robot_view_rendered_robot_pose(state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_outputs.robot_view_rendered_robot_pose(
        state, hooks=_isaac_worker_output_hooks()
    )


def write_camera_views(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_outputs.write_camera_views(args, state, hooks=_isaac_worker_output_hooks())


def _locations_command(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_outputs.locations_command(args, state)


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
    return isaac_worker_outputs.robot_view_camera_control_contract(
        state,
        robot_pose=robot_pose,
        focus=focus,
        hooks=_isaac_worker_output_hooks(),
    )


def _isaac_robot_pose_hooks() -> IsaacRobotPoseHooks:
    return IsaacRobotPoseHooks(
        binding_for_handle=_binding_for_handle,
        dict_value=_dict,
        has_xy=_has_xy,
        optional_float=_optional_float,
        pose_near=_pose_near,
        receptacle_support_pose=_receptacle_support_pose,
        receptacles_by_id=_receptacles_by_id,
        round_vec3=_round_vec3,
        scene_index_center_xy=_scene_index_center_xy,
        semantic_object_pose_entry=_semantic_object_pose_entry,
        support_pose_position=_support_pose_position,
        vec3=_vec3,
    )


def _target_room_id_from_pose_inputs(
    state: dict[str, Any],
    receptacle_id: str,
    support: dict[str, Any],
) -> str | None:
    return isaac_robot_pose_focus.target_room_id_from_pose_inputs(
        state,
        receptacle_id,
        support,
        hooks=_isaac_robot_pose_hooks(),
    )


def _robot_pose_for_receptacle(
    state: dict[str, Any],
    receptacle_id: str,
) -> dict[str, Any]:
    return isaac_robot_pose_focus.robot_pose_for_receptacle(
        state,
        receptacle_id,
        hooks=_isaac_robot_pose_hooks(),
    )


def _robot_pose_for_waypoint(waypoint: dict[str, Any]) -> dict[str, Any]:
    return isaac_robot_pose_focus.robot_pose_for_waypoint(
        waypoint,
        hooks=_isaac_robot_pose_hooks(),
    )


def _normalized_waypoint_robot_pose(
    pose: dict[str, Any],
    *,
    waypoint: dict[str, Any],
    pose_source: str,
) -> dict[str, Any]:
    return isaac_robot_pose_focus.normalized_waypoint_robot_pose(
        pose,
        waypoint=waypoint,
        pose_source=pose_source,
        hooks=_isaac_robot_pose_hooks(),
    )


def _receptacle_support_pose(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return isaac_robot_pose_focus.receptacle_support_pose(
        state,
        receptacle_id,
        hooks=_isaac_robot_pose_hooks(),
    )


def _binding_for_handle(
    scene_binding_diagnostics: Any,
    handle: str,
    groups: tuple[str, ...],
) -> dict[str, Any]:
    return isaac_robot_pose_focus.binding_for_handle(
        scene_binding_diagnostics,
        handle,
        groups,
        dict_value=_dict,
    )


def _scene_index_center_xy(state: dict[str, Any]) -> tuple[float, float]:
    return isaac_robot_pose_focus.scene_index_center_xy(
        state,
        dict_value=_dict,
        vec3=_vec3,
    )


def _camera_capture_variant(capture: dict[str, Any]) -> str:
    return isaac_worker_outputs.camera_capture_variant(capture)


def _camera_capture_provenance(capture: dict[str, Any]) -> str:
    return isaac_worker_outputs.camera_capture_provenance(capture)


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
    return isaac_robot_pose_focus.robot_view_focus(
        state,
        robot_pose,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
        hooks=_isaac_robot_pose_hooks(),
    )


def _focus_payload(
    *,
    state: dict[str, Any] | None = None,
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    return isaac_robot_pose_focus.focus_payload(
        state=state,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
        hooks=_isaac_robot_pose_hooks(),
    )


def _semantic_object_pose_entry(
    state: dict[str, Any],
    object_id: str | None,
) -> dict[str, Any]:
    return isaac_robot_pose_focus.semantic_object_pose_entry(
        state,
        object_id,
        dict_value=_dict,
    )


def _support_pose_position(pose: dict[str, Any]) -> list[float] | None:
    return isaac_robot_pose_focus.support_pose_position(
        pose,
        has_xy=_has_xy,
    )


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
    return isaac_worker_protocol.safe_file_stem(value)


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
    isaac_worker_protocol.write_placeholder_image(
        path,
        title=title,
        subtitle=subtitle,
        state=state,
        width=width,
        height=height,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
    )


def _ok(tool: str, **payload: Any) -> dict[str, Any]:
    return isaac_worker_protocol.ok_response(tool, **payload)


def _error(tool: str, error: str, **payload: Any) -> dict[str, Any]:
    return isaac_worker_protocol.error_response(tool, error, **payload)


def read_state(path: Path) -> dict[str, Any]:
    return isaac_worker_protocol.read_state(path)


def write_state(path: Path, state: dict[str, Any]) -> None:
    isaac_worker_protocol.write_state(path, state)


def write_state_from_state_arg(state: dict[str, Any]) -> None:
    isaac_worker_protocol.write_state_from_state_arg(state)


def _count(state: dict[str, Any], tool: str) -> None:
    isaac_worker_protocol.count_tool_request(state, tool)


def _public_state(state: dict[str, Any]) -> dict[str, Any]:
    return isaac_worker_protocol.public_state(state)


def scenario_from_state(state: dict[str, Any]) -> CleanupScenario:
    return isaac_scenario_builders.scenario_from_state(state)


def _load_generated_mess_manifest(path: Path | None) -> dict[str, Any]:
    return load_generated_mess_manifest(path)


def _scenario_for_init(
    args: argparse.Namespace,
    *,
    generated_mess_manifest: dict[str, Any] | None = None,
) -> CleanupScenario:
    return scenario_for_init(args, generated_mess_manifest=generated_mess_manifest)


def _scenario_source(args: argparse.Namespace) -> str:
    return isaac_scenario_builders.scenario_source(args)


def _effective_scene_index(args: argparse.Namespace) -> int:
    return effective_scene_index(args)


def _scene_index_from_usd_path(path: Any) -> int | None:
    return scene_index_from_usd_path(path)


def _scene_specific_scenario_if_needed(
    *,
    args: argparse.Namespace,
    generated_mess_manifest: dict[str, Any] | None,
    scene_binding_diagnostics: dict[str, Any],
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    real_smoke: dict[str, Any] | None,
) -> CleanupScenario | None:
    return scene_specific_scenario_if_needed(
        args=args,
        generated_mess_manifest=generated_mess_manifest,
        scene_binding_diagnostics=scene_binding_diagnostics,
        object_index=object_index,
        receptacle_index=receptacle_index,
        real_smoke=real_smoke,
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
    return scenario_from_scene_index(
        scene_source=scene_source,
        scene_index=scene_index,
        seed=seed,
        generated_mess_count=generated_mess_count,
        generated_mess_object_ids=generated_mess_object_ids,
        generated_mess_manifest=generated_mess_manifest,
        object_index=object_index,
        receptacle_index=receptacle_index,
    )


def _cleanup_receptacle_index_for_mess_generation(
    receptacle_index: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    return cleanup_receptacle_index_for_mess_generation(receptacle_index)


def _cleanup_receptacle_from_scene_index(
    handle: str,
    entry: dict[str, Any],
) -> CleanupReceptacle:
    return cleanup_receptacle_from_scene_index(handle, entry)


def _scene_object_name(handle: str, entry: dict[str, Any]) -> str:
    return scene_object_name(handle, entry)


def _scene_object_category(entry: dict[str, Any]) -> str:
    return scene_object_category(entry)


def _scene_cleanup_object_category(entry: dict[str, Any]) -> str:
    return scene_cleanup_object_category(entry)


def _canonical_cleanup_category(category: str, aliases: tuple[str, ...]) -> str:
    return canonical_cleanup_category(category, aliases)


def _scene_target_receptacle_id(
    entry: dict[str, Any],
    receptacle_index: dict[str, dict[str, Any]],
) -> str:
    return scene_target_receptacle_id(entry, receptacle_index)


def _first_receptacle_matching_aliases(
    receptacle_index: dict[str, dict[str, Any]],
    aliases: tuple[str, ...],
) -> str:
    return first_receptacle_matching_aliases(receptacle_index, aliases)


def _scene_source_receptacle_id(
    entry: dict[str, Any],
    receptacle_index: dict[str, dict[str, Any]],
    *,
    target_id: str,
) -> str:
    return scene_source_receptacle_id(entry, receptacle_index, target_id=target_id)


def _scene_entry_tokens(handle: str, entry: dict[str, Any]) -> set[str]:
    return scene_entry_tokens(handle, entry)


_SCENE_CLEANUP_TARGET_ALIASES = SCENE_CLEANUP_TARGET_ALIASES
_SCENE_STRICT_CLEANUP_TARGET_ALIASES = SCENE_STRICT_CLEANUP_TARGET_ALIASES
_CANONICAL_CLEANUP_CATEGORY_ALIASES = CANONICAL_CLEANUP_CATEGORY_ALIASES


def _scenario_from_generated_mess_manifest_or_limit(
    scenario: CleanupScenario,
    *,
    generated_mess_count: int,
    generated_mess_manifest: dict[str, Any] | None = None,
) -> CleanupScenario:
    return scenario_from_generated_mess_manifest_or_limit(
        scenario,
        generated_mess_count=generated_mess_count,
        generated_mess_manifest=generated_mess_manifest,
    )


def _limit_scenario_to_generated_mess_count(
    scenario: CleanupScenario,
    *,
    generated_mess_count: int,
) -> CleanupScenario:
    return limit_scenario_to_generated_mess_count(
        scenario,
        generated_mess_count=generated_mess_count,
    )


def _scenario_without_private_targets(
    scenario: CleanupScenario,
    *,
    scenario_id: str,
    objects: tuple[CleanupObject, ...],
) -> CleanupScenario:
    return scenario_without_private_targets(
        scenario,
        scenario_id=scenario_id,
        objects=objects,
    )


def _scenario_from_map_bundle(
    bundle_dir: Path,
    *,
    seed: int,
    generated_mess_count: int,
) -> CleanupScenario:
    return scenario_from_map_bundle(
        bundle_dir,
        seed=seed,
        generated_mess_count=generated_mess_count,
    )


def _initial_receptacle_id(scenario: CleanupScenario) -> str:
    return initial_receptacle_id(scenario)


def _cleanup_receptacle_from_fixture(fixture: dict[str, Any]) -> CleanupReceptacle:
    return cleanup_receptacle_from_fixture(fixture)


def _map_aligned_target_specs(fixtures: list[dict[str, Any]]) -> list[dict[str, str]]:
    return map_aligned_target_specs(fixtures)


def _first_fixture_matching(
    fixtures: list[dict[str, Any]],
    aliases: tuple[str, ...],
    *,
    exclude_fixture_id: str = "",
) -> dict[str, Any] | None:
    return first_fixture_matching(fixtures, aliases, exclude_fixture_id=exclude_fixture_id)


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
    return isaac_mapping_diagnostics.scene_usd_path(scene_source, scene_index)


if __name__ == "__main__":
    raise SystemExit(main())

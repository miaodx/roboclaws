#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import platform
import re
import sys
import traceback
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.backend import HELD_LOCATION_ID
from roboclaws.molmo_cleanup.camera_control import (
    ANCHOR_ORBIT_CAMERA_MODEL,
    CAMERA_CONTROL_API_NAME,
    CANONICAL_CAMERA_MODEL,
    MOLMOSPACES_SCENE_FRAME,
    load_camera_control_request,
    normalize_camera_control_request,
)
from roboclaws.molmo_cleanup.color_management import apply_camera_color_profile
from roboclaws.molmo_cleanup.generated_mess import (
    generated_mess_success_threshold,
    select_generated_mess_targets,
)
from roboclaws.molmo_cleanup.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
)
from roboclaws.molmo_cleanup.robot_view_camera_control import (
    backend_local_robot_view_camera_control_contract,
    robot_mounted_head_camera_control_contract,
)
from roboclaws.molmo_cleanup.robot_view_pose import resolve_cleanup_robot_pose
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.scoring import score_cleanup
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)

STATE_SCHEMA = "isaac_lab_backend_state_v1"
DEFAULT_WIDTH = 540
DEFAULT_HEIGHT = 360
ROBOT_VIEW_KEYS = ("fpv", "chase", "map", "verify")
SCENE_BINDING_SCHEMA = "isaac_public_scene_bindings_v1"
SEGMENTATION_SCHEMA = "isaac_segmentation_diagnostics_v1"
ISAAC_SEGMENTATION_DATA_TYPES = (
    "semantic_segmentation",
    "instance_segmentation_fast",
    "instance_id_segmentation_fast",
)
GENERATED_SCENE_KINDS = ("roboclaws_smoke", "isaac_official_blocks")
ISAAC_OFFICIAL_ASSET_ROOT = (
    "https://omniverse-content-production.s3-us-west-2.amazonaws.com/Assets/Isaac/5.1/Isaac"
)
ISAAC_OFFICIAL_BLOCK_ASSETS = (
    "Props/Blocks/blue_block.usd",
    "Props/Blocks/red_block.usd",
    "Props/Blocks/green_block.usd",
)
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
MAX_SEGMENTATION_CANDIDATES = 24
REAL_SMOKE_CAPTURE_METHOD = "isaac_lab_camera_rgb"
REAL_ROBOT_VIEW_CAPTURE_METHOD = "isaac_lab_camera_rgb_static_robot_views"
REAL_ROBOT_VIEW_RERENDER_METHOD = "isaac_lab_camera_rgb_semantic_pose_robot_views"
REAL_SMOKE_RENDERER_MODE = "isaac_lab_headless_rtx"
PLACEMENT_DIAGNOSTIC_SCHEMA = "molmospaces_semantic_placement_diagnostic_v1"
ISAAC_PLACEMENT_RESOLVER_SOURCE = "isaac_support_placement_resolver"
ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE = "isaac_usd_descendant_support_surface"
ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE = "isaac_usd_descendant_support_surface_union"
ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE = "isaac_usd_world_bounds"
ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA = "isaac_rby1m_robot_import_plan_v1"
ISAAC_RBY1M_HEAD_CAMERA_PRIM = "/World/robot_0/head_camera"
ISAAC_RBY1M_ROBOT_USD_PATH = Path("output/isaaclab/robots/rby1m/rby1m_holobase_isaac.usda")
ISAAC_RBY1M_ROBOT_IMPORT_SUMMARY_PATH = Path(
    "output/isaaclab/robots/rby1m/rby1m_holobase_isaac.import_summary.json"
)
_DEFERRED_SIMULATION_APP: Any | None = None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Isaac Lab cleanup backend worker for Roboclaws.")
    parser.add_argument("--state-path", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--run-dir", type=Path, required=True)
    init.add_argument("--seed", type=int, default=7)
    init.add_argument("--scene-source", default="procthor-10k-val")
    init.add_argument("--scene-index", type=int, default=0)
    init.add_argument("--generated-mess-count", type=int, default=1)
    init.add_argument(
        "--generated-mess-object-id",
        action="append",
        help="Private run-control object id to include in the generated mess set. Repeatable.",
    )
    init.add_argument(
        "--generated-scene-kind",
        choices=GENERATED_SCENE_KINDS,
        default="roboclaws_smoke",
        help=(
            "Generated USD control scene to write when --scene-usd-path is omitted. "
            "Use isaac_official_blocks to probe NVIDIA Isaac sample assets."
        ),
    )
    init.add_argument("--runtime-mode", choices=("real", "fake"), default="real")
    init.add_argument("--include-robot", action="store_true")
    init.add_argument("--robot-name", default="rby1m")
    init.add_argument("--map-bundle-dir", type=Path)
    init.add_argument(
        "--enable-segmentation",
        action="store_true",
        help="Request Isaac semantic/instance segmentation tensors during real RGB capture.",
    )
    init.add_argument(
        "--segmentation-data-type",
        action="append",
        choices=ISAAC_SEGMENTATION_DATA_TYPES,
        help=(
            "Isaac segmentation data type to request. Repeat to probe individual "
            "annotators; defaults to all supported segmentation data types."
        ),
    )
    init.add_argument(
        "--segmentation-semantic-filter",
        action="append",
        help=(
            "Semantic label instance name to request from Isaac camera semantic filters. "
            "Repeat to probe class vs usd_prim_path labels; defaults to class."
        ),
    )
    init.add_argument(
        "--scene-usd-path",
        type=Path,
        help=(
            "Optional local USD/USDA scene to load in real mode. Use this for "
            "MolmoSpaces Isaac scene parity once a scene shard is available locally."
        ),
    )

    subparsers.add_parser("locations")
    subparsers.add_parser("observe")

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--output-path", type=Path, required=True)
    snapshot.add_argument("--title", required=True)
    snapshot.add_argument("--render-width", type=int, default=DEFAULT_WIDTH)
    snapshot.add_argument("--render-height", type=int, default=DEFAULT_HEIGHT)

    robot_views = subparsers.add_parser("robot_views")
    robot_views.add_argument("--output-dir", type=Path, required=True)
    robot_views.add_argument("--label", required=True)
    robot_views.add_argument("--focus-object-id")
    robot_views.add_argument("--focus-receptacle-id")
    robot_views.add_argument("--render-width", type=int, default=DEFAULT_WIDTH)
    robot_views.add_argument("--render-height", type=int, default=DEFAULT_HEIGHT)

    camera_views = subparsers.add_parser("camera_views")
    camera_views.add_argument("--output-dir", type=Path, required=True)
    camera_views.add_argument("--view-specs-path", type=Path)
    camera_views.add_argument("--camera-request-path", type=Path)
    camera_views.add_argument("--render-width", type=int, default=DEFAULT_WIDTH)
    camera_views.add_argument("--render-height", type=int, default=DEFAULT_HEIGHT)

    object_cmds = ("navigate_to_object", "pick")
    for command in object_cmds:
        item = subparsers.add_parser(command)
        item.add_argument("--object-id", required=True)

    receptacle_cmds = (
        "navigate_to_receptacle",
        "open_receptacle",
        "place",
        "place_inside",
        "close_receptacle",
    )
    for command in receptacle_cmds:
        item = subparsers.add_parser(command)
        item.add_argument("--receptacle-id", required=True)

    done = subparsers.add_parser("done")
    done.add_argument("--reason", default="")

    return parser.parse_args(argv)


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
    else:
        state = read_state(args.state_path)
        if args.command == "locations":
            result = {"ok": True, "tool": "locations", "final_locations": state["locations"]}
        elif args.command == "snapshot":
            result = write_snapshot(args, state)
        elif args.command == "robot_views":
            result = write_robot_views(args, state)
        elif args.command == "camera_views":
            result = write_camera_views(args, state)
        elif args.command == "observe":
            result = observe(args, state)
        elif args.command == "navigate_to_object":
            result = navigate_to_object(args, state)
        elif args.command == "navigate_to_receptacle":
            result = navigate_to_receptacle(args, state)
        elif args.command == "pick":
            result = pick(args, state)
        elif args.command == "open_receptacle":
            result = open_receptacle(args, state)
        elif args.command == "place":
            result = place(args, state, relation="on")
        elif args.command == "place_inside":
            result = place(args, state, relation="inside")
        elif args.command == "close_receptacle":
            result = close_receptacle(args, state)
        elif args.command == "done":
            result = done(args, state)
        else:  # pragma: no cover - argparse prevents this.
            raise ValueError(f"unsupported command: {args.command}")
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
    scenario = _scenario_for_init(args)
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


def _generated_scene_filename(scene_kind: str) -> str:
    if scene_kind == "isaac_official_blocks":
        return "roboclaws_isaac_official_blocks_scene.usda"
    return "roboclaws_phase_a_smoke_scene.usda"


def _write_generated_runtime_smoke_usd(
    usd_path: Path,
    scenario: CleanupScenario,
    *,
    scene_kind: str = "roboclaws_smoke",
) -> int:
    if scene_kind == "isaac_official_blocks":
        return _write_isaac_official_blocks_runtime_smoke_usd(usd_path, scenario)
    return _write_roboclaws_runtime_smoke_usd(usd_path, scenario)


def _write_roboclaws_runtime_smoke_usd(
    usd_path: Path,
    scenario: CleanupScenario,
) -> int:
    from pxr import Gf, Usd, UsdGeom, UsdLux

    usd_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(usd_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    floor = UsdGeom.Cube.Define(stage, "/World/Floor")
    floor.CreateSizeAttr(1.0)
    floor.CreateDisplayColorAttr([Gf.Vec3f(0.28, 0.31, 0.33)])
    UsdGeom.XformCommonAPI(floor).SetTranslate(Gf.Vec3d(0.0, 0.0, -0.025))
    UsdGeom.XformCommonAPI(floor).SetScale(Gf.Vec3f(3.0, 3.0, 0.05))

    selected_object_ids = _selected_cleanup_object_ids(scenario) or [
        scenario.objects[0].object_id if scenario.objects else "object"
    ]
    selected_object_id_set = set(selected_object_ids)
    selected_receptacle_ids = _selected_cleanup_receptacle_ids(scenario)
    source_receptacle_ids = [
        obj.location_id for obj in scenario.objects if obj.object_id in selected_object_id_set
    ]
    receptacle_ids = _dedupe(
        [
            *source_receptacle_ids,
            *selected_receptacle_ids,
            *(item.receptacle_id for item in scenario.receptacles[:1]),
        ]
    )
    if not receptacle_ids:
        receptacle_ids = ["fixture"]

    fixture_positions: dict[str, tuple[float, float, float]] = {}
    for index, receptacle_id in enumerate(receptacle_ids):
        x = (index % 3 - 1) * 0.95
        y = (index // 3) * 0.85
        z = 0.35
        fixture_positions[receptacle_id] = (x, y, z)
        fixture = UsdGeom.Cube.Define(
            stage,
            f"/World/Receptacles/{_usd_safe_name(receptacle_id)}",
        )
        fixture.CreateSizeAttr(1.0)
        fixture.CreateDisplayColorAttr([Gf.Vec3f(0.1, 0.46, 0.75)])
        UsdGeom.XformCommonAPI(fixture).SetTranslate(Gf.Vec3d(x, y, z))
        UsdGeom.XformCommonAPI(fixture).SetScale(Gf.Vec3f(0.9, 0.55, 0.25))

    objects_by_id = {item.object_id: item for item in scenario.objects}
    for index, object_id in enumerate(selected_object_ids):
        cleanup_object = UsdGeom.Sphere.Define(
            stage,
            f"/World/Objects/{_usd_safe_name(object_id)}",
        )
        cleanup_object.CreateRadiusAttr(0.16)
        cleanup_object.CreateDisplayColorAttr([Gf.Vec3f(0.95, 0.42, 0.12)])
        source_id = objects_by_id.get(object_id).location_id if object_id in objects_by_id else ""
        x, y, z = fixture_positions.get(source_id, (0.0, 0.0, 0.35))
        UsdGeom.XformCommonAPI(cleanup_object).SetTranslate(
            Gf.Vec3d(x + 0.18 + 0.08 * index, y - 0.16, z + 0.38)
        )

    key_light = UsdLux.DistantLight.Define(stage, "/World/KeyLight")
    key_light.CreateIntensityAttr(5000.0)
    UsdGeom.XformCommonAPI(key_light).SetRotate(Gf.Vec3f(-45.0, 0.0, 35.0))

    camera = UsdGeom.Camera.Define(stage, "/World/ReferenceCamera")
    camera.CreateFocalLengthAttr(24.0)
    camera.CreateHorizontalApertureAttr(20.955)
    UsdGeom.XformCommonAPI(camera).SetTranslate(Gf.Vec3d(2.4, -2.6, 1.8))

    stage.GetRootLayer().Save()
    return sum(1 for _ in stage.Traverse())


def _write_isaac_official_blocks_runtime_smoke_usd(
    usd_path: Path,
    scenario: CleanupScenario,
) -> int:
    from pxr import Gf, Usd, UsdGeom, UsdLux

    usd_path.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(usd_path))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    world = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(world.GetPrim())

    floor = UsdGeom.Cube.Define(stage, "/World/Floor")
    floor.CreateSizeAttr(1.0)
    floor.CreateDisplayColorAttr([Gf.Vec3f(0.24, 0.26, 0.28)])
    UsdGeom.XformCommonAPI(floor).SetTranslate(Gf.Vec3d(0.0, 0.0, -0.025))
    UsdGeom.XformCommonAPI(floor).SetScale(Gf.Vec3f(3.2, 3.2, 0.05))

    selected_object_ids = _selected_cleanup_object_ids(scenario) or [
        scenario.objects[0].object_id if scenario.objects else "official_block"
    ]
    selected_object_id_set = set(selected_object_ids)
    selected_receptacle_ids = _selected_cleanup_receptacle_ids(scenario)
    source_receptacle_ids = [
        obj.location_id for obj in scenario.objects if obj.object_id in selected_object_id_set
    ]
    receptacle_ids = _dedupe(
        [
            *source_receptacle_ids,
            *selected_receptacle_ids,
            *(item.receptacle_id for item in scenario.receptacles[:1]),
        ]
    )
    if not receptacle_ids:
        receptacle_ids = ["fixture"]

    fixture_positions: dict[str, tuple[float, float, float]] = {}
    for index, receptacle_id in enumerate(receptacle_ids):
        x = (index % 3 - 1) * 0.95
        y = (index // 3) * 0.85
        z = 0.28
        fixture_positions[receptacle_id] = (x, y, z)
        fixture = UsdGeom.Cube.Define(
            stage,
            f"/World/Receptacles/{_usd_safe_name(receptacle_id)}",
        )
        fixture.CreateSizeAttr(1.0)
        fixture.CreateDisplayColorAttr([Gf.Vec3f(0.1, 0.44, 0.72)])
        UsdGeom.XformCommonAPI(fixture).SetTranslate(Gf.Vec3d(x, y, z))
        UsdGeom.XformCommonAPI(fixture).SetScale(Gf.Vec3f(0.9, 0.55, 0.18))

    objects_by_id = {item.object_id: item for item in scenario.objects}
    for index, object_id in enumerate(selected_object_ids):
        object_prim_path = f"/World/Objects/{_usd_safe_name(object_id)}"
        cleanup_object = UsdGeom.Xform.Define(stage, object_prim_path)
        cleanup_asset = UsdGeom.Xform.Define(stage, f"{object_prim_path}/Asset")
        asset = ISAAC_OFFICIAL_BLOCK_ASSETS[index % len(ISAAC_OFFICIAL_BLOCK_ASSETS)]
        cleanup_asset.GetPrim().GetReferences().AddReference(f"{ISAAC_OFFICIAL_ASSET_ROOT}/{asset}")
        source_id = objects_by_id.get(object_id).location_id if object_id in objects_by_id else ""
        x, y, z = fixture_positions.get(source_id, (0.0, 0.0, 0.28))
        UsdGeom.XformCommonAPI(cleanup_object).SetTranslate(
            Gf.Vec3d(x + 0.22 + 0.12 * index, y - 0.18, z + 0.26)
        )
        UsdGeom.XformCommonAPI(cleanup_object).SetScale(Gf.Vec3f(1.6, 1.6, 1.6))

    key_light = UsdLux.DistantLight.Define(stage, "/World/KeyLight")
    key_light.CreateIntensityAttr(5000.0)
    UsdGeom.XformCommonAPI(key_light).SetRotate(Gf.Vec3f(-45.0, 0.0, 35.0))

    camera = UsdGeom.Camera.Define(stage, "/World/ReferenceCamera")
    camera.CreateFocalLengthAttr(24.0)
    camera.CreateHorizontalApertureAttr(20.955)
    UsdGeom.XformCommonAPI(camera).SetTranslate(Gf.Vec3d(2.4, -2.6, 1.8))

    stage.GetRootLayer().Save()
    return sum(1 for _ in stage.Traverse())


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


def _support_pose_from_usd_bounds(
    bounds: Any,
    *,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    raw_bounds = bounds if isinstance(bounds, dict) else {}
    center = _vec3(raw_bounds.get("center"))
    max_point = _vec3(raw_bounds.get("max"))
    if center is None:
        return dict(fallback) if fallback else None
    pose = {
        "frame": "usd_world",
        "x": center[0],
        "y": center[1],
        "z": max_point[2] if max_point is not None else center[2],
        "yaw_deg": float(_dict(fallback).get("yaw_deg") or 0.0),
        "source": "usd_world_bounds_top_center",
    }
    size = _vec3(raw_bounds.get("size"))
    if size is not None:
        pose["support_radius_m"] = round(max(size[0], size[1]) / 2.0, 6)
    return pose


def _support_pose_from_support_surface(
    surface: dict[str, Any],
    *,
    fallback: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    center = surface.get("center")
    if not isinstance(center, (list, tuple)) or len(center) < 2:
        return dict(fallback) if fallback else None
    try:
        x = float(center[0])
        y = float(center[1])
        z = float(surface["top_z"])
    except (KeyError, TypeError, ValueError):
        return dict(fallback) if fallback else None
    half_extents = surface.get("half_extents")
    pose = {
        "frame": "usd_world",
        "x": x,
        "y": y,
        "z": z,
        "yaw_deg": _float_or_default(_dict(fallback).get("yaw_deg"), 0.0),
        "source": str(surface.get("source") or ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE),
        "support_surface_id": surface.get("surface_id"),
    }
    if isinstance(half_extents, (list, tuple)) and len(half_extents) >= 2:
        try:
            pose["support_radius_m"] = round(
                max(abs(float(half_extents[0])), abs(float(half_extents[1]))),
                6,
            )
        except (TypeError, ValueError):
            pass
    return pose


def _float_or_default(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _usd_receptacle_support_surfaces(*, prim: Any, usd_geom: Any) -> list[dict[str, Any]]:
    whole_bounds = _usd_world_bounds(prim, usd_geom=usd_geom)
    whole_surface = _support_surface_from_usd_bounds(
        bounds=whole_bounds,
        surface_id=str(prim.GetPath()),
        source=ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE,
    )
    candidates = []
    for descendant in _iter_usd_prim_range(prim):
        if descendant == prim:
            continue
        if not _is_usd_renderable_support_candidate(descendant, usd_geom=usd_geom):
            continue
        bounds = _usd_world_bounds(descendant, usd_geom=usd_geom)
        surface = _support_surface_from_usd_bounds(
            bounds=bounds,
            surface_id=str(descendant.GetPath()),
            source=ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE,
        )
        if surface is None:
            continue
        score = _usd_support_surface_score(surface, whole_surface=whole_surface)
        if score is None:
            continue
        surface["selection_score"] = round(float(score), 6)
        candidates.append(surface)
    candidates.sort(
        key=lambda item: (
            float(item.get("selection_score") or 0.0),
            float(item.get("area_m2") or 0.0),
            -float(item.get("top_z") or 0.0),
            str(item.get("surface_id") or ""),
        ),
        reverse=True,
    )
    if candidates:
        union = _usd_support_surface_union(candidates, whole_surface=whole_surface)
        if union is not None:
            return [union, *candidates[:7]]
        return candidates[:8]
    return [whole_surface] if whole_surface is not None else []


def _is_usd_renderable_support_candidate(prim: Any, *, usd_geom: Any) -> bool:
    gprim_type = getattr(usd_geom, "Gprim", None)
    if gprim_type is not None and prim.IsA(gprim_type):
        return True
    return str(prim.GetTypeName() or "") in {"Mesh", "Cube", "Sphere", "Cylinder", "Capsule"}


def _support_surface_from_usd_bounds(
    *,
    bounds: Any,
    surface_id: str,
    source: str,
) -> dict[str, Any] | None:
    raw_bounds = bounds if isinstance(bounds, dict) else {}
    center = _vec3(raw_bounds.get("center"))
    size = _vec3(raw_bounds.get("size"))
    max_point = _vec3(raw_bounds.get("max"))
    if center is None or size is None or max_point is None:
        return None
    half_extents = [abs(float(size[0])) / 2.0, abs(float(size[1])) / 2.0]
    if min(half_extents) < 0.03:
        return None
    area = 4.0 * float(half_extents[0]) * float(half_extents[1])
    if area <= 0.0:
        return None
    return {
        "surface_id": surface_id,
        "center": [round(float(center[0]), 6), round(float(center[1]), 6)],
        "top_z": round(float(max_point[2]), 6),
        "half_extents": [
            round(float(half_extents[0]), 6),
            round(float(half_extents[1]), 6),
        ],
        "area_m2": round(float(area), 6),
        "source": source,
    }


def _usd_support_surface_score(
    surface: dict[str, Any],
    *,
    whole_surface: dict[str, Any] | None,
) -> float | None:
    area = float(surface.get("area_m2") or 0.0)
    if area < 0.03:
        return None
    half_extents = surface.get("half_extents")
    if not isinstance(half_extents, (list, tuple)) or len(half_extents) < 2:
        return None
    try:
        min_half_extent = min(abs(float(half_extents[0])), abs(float(half_extents[1])))
        top_z = float(surface["top_z"])
    except (KeyError, TypeError, ValueError):
        return None
    if min_half_extent < 0.06:
        return None
    whole_area = float(_dict(whole_surface).get("area_m2") or 0.0)
    whole_top_z = _dict(whole_surface).get("top_z")
    area_ratio = area / whole_area if whole_area > 0.0 else 1.0
    try:
        below_whole_top = max(float(whole_top_z) - top_z, 0.0)
    except (TypeError, ValueError):
        below_whole_top = 0.0
    # Beds and similar receptacles often include tall backboards in the parent
    # bounds. Favor broad lower descendants over the highest broad descendant.
    return area + min(area_ratio, 1.25) + min(below_whole_top * 2.0, 3.0)


def _usd_support_surface_union(
    candidates: list[dict[str, Any]],
    *,
    whole_surface: dict[str, Any] | None,
) -> dict[str, Any] | None:
    broad = []
    best_top_z = float(candidates[0].get("top_z") or 0.0) if candidates else 0.0
    for surface in candidates:
        if surface.get("source") != ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE:
            continue
        top_z = _float_or_default(surface.get("top_z"), best_top_z)
        area = _float_or_default(surface.get("area_m2"), 0.0)
        whole_area = _float_or_default(_dict(whole_surface).get("area_m2"), 0.0)
        if area < 0.03:
            continue
        if whole_area > 0.0 and area / whole_area < 0.35:
            continue
        if abs(top_z - best_top_z) > 0.08:
            continue
        center = surface.get("center")
        half_extents = surface.get("half_extents")
        if not isinstance(center, (list, tuple)) or len(center) < 2:
            continue
        if not isinstance(half_extents, (list, tuple)) or len(half_extents) < 2:
            continue
        try:
            min_x = float(center[0]) - abs(float(half_extents[0]))
            max_x = float(center[0]) + abs(float(half_extents[0]))
            min_y = float(center[1]) - abs(float(half_extents[1]))
            max_y = float(center[1]) + abs(float(half_extents[1]))
        except (TypeError, ValueError):
            continue
        broad.append((surface, min_x, max_x, min_y, max_y, top_z))
    if len(broad) < 2:
        return None
    min_x = min(item[1] for item in broad)
    max_x = max(item[2] for item in broad)
    min_y = min(item[3] for item in broad)
    max_y = max(item[4] for item in broad)
    top_z = max(item[5] for item in broad)
    area = (max_x - min_x) * (max_y - min_y)
    if area <= 0.0:
        return None
    return {
        "surface_id": "+".join(str(item[0].get("surface_id") or "") for item in broad),
        "center": [round((min_x + max_x) / 2.0, 6), round((min_y + max_y) / 2.0, 6)],
        "top_z": round(top_z, 6),
        "half_extents": [
            round((max_x - min_x) / 2.0, 6),
            round((max_y - min_y) / 2.0, 6),
        ],
        "area_m2": round(area, 6),
        "source": ISAAC_DESCENDANT_SUPPORT_SURFACE_UNION_SOURCE,
        "selection_score": round(
            max(float(item[0].get("selection_score") or 0.0) for item in broad),
            6,
        ),
        "member_count": len(broad),
    }


def _room_outline_from_usd_prim(
    prim_path: str,
    prim: Any,
    *,
    usd_geom: Any,
) -> dict[str, Any] | None:
    match = re.search(r"/(room_\d+)_visual(?:_\d+)?$", prim_path)
    if match is None:
        return None
    bounds = _usd_world_bounds(prim, usd_geom=usd_geom)
    if bounds is None:
        return None
    center = _vec3(bounds.get("center"))
    size = _vec3(bounds.get("size"))
    if center is None or size is None:
        return None
    half_extents = [abs(size[0]) / 2.0, abs(size[1]) / 2.0]
    if min(half_extents) < 0.25:
        return None
    room_id = match.group(1)
    return {
        "room_id": room_id,
        "label": room_id.replace("_", " ").title(),
        "center": [round(center[0], 6), round(center[1], 6)],
        "half_extents": [round(half_extents[0], 6), round(half_extents[1], 6)],
        "provenance": "isaac_usd_room_mesh_world_bounds",
        "usd_prim_path": prim_path,
    }


def _room_outlines_from_scene_index_diagnostics(
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    return [dict(item) for item in diagnostics.get("room_outlines") or [] if isinstance(item, dict)]


def _fallback_room_outlines_from_indices(
    *,
    scenario: CleanupScenario,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[list[float]]] = {}
    room_by_receptacle = {
        item.receptacle_id: str(item.room_area or "isaac_scene") for item in scenario.receptacles
    }
    for receptacle in scenario.receptacles:
        position = _support_pose_position(
            _dict(_dict(receptacle_index.get(receptacle.receptacle_id)).get("support_pose"))
        )
        if position is None:
            position = _vec3(
                _dict(
                    _dict(receptacle_index.get(receptacle.receptacle_id)).get("usd_world_bounds")
                ).get("center")
            )
        if position is None:
            continue
        grouped.setdefault(room_by_receptacle[receptacle.receptacle_id], []).append(position)
    for obj in scenario.objects:
        position = _vec3(
            _dict(_dict(object_index.get(obj.object_id)).get("usd_world_bounds")).get("center")
        )
        if position is None:
            continue
        grouped.setdefault(room_by_receptacle.get(obj.location_id, "isaac_scene"), []).append(
            position
        )
    outlines = []
    for room_id, points in grouped.items():
        if not points:
            continue
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        center = [round((min(xs) + max(xs)) / 2.0, 6), round((min(ys) + max(ys)) / 2.0, 6)]
        half_extents = [
            round(max((max(xs) - min(xs)) / 2.0, 0.8), 6),
            round(max((max(ys) - min(ys)) / 2.0, 0.8), 6),
        ]
        outlines.append(
            {
                "room_id": room_id,
                "label": room_id.replace("_", " ").title(),
                "center": center,
                "half_extents": half_extents,
                "provenance": "scenario_fixture_room_bounds",
            }
        )
    return sorted(outlines, key=lambda item: str(item.get("room_id") or ""))


def _round_vec3(values: list[float] | tuple[float, ...]) -> list[float]:
    return [round(float(value), 6) for value in values[:3]]


def _iter_usd_prim_range(prim: Any) -> Iterable[Any]:
    from pxr import Usd

    return Usd.PrimRange(prim)


def _authored_reference_asset_paths(*, usd_path: Path, prim: Any) -> list[str]:
    assets: list[str] = []
    for spec in prim.GetPrimStack():
        reference_list = getattr(spec, "referenceList", None)
        for reference in _usd_list_op_items(reference_list):
            asset_path = str(getattr(reference, "assetPath", "") or "")
            if not asset_path:
                continue
            layer_path = Path(str(getattr(spec.layer, "realPath", "") or usd_path))
            if not _is_local_reference_asset_path(asset_path):
                assets.append(asset_path)
            else:
                assets.append(str((layer_path.parent / asset_path).resolve()))
    return sorted(dict.fromkeys(assets))


def _usd_list_op_items(list_op: Any) -> list[Any]:
    items: list[Any] = []
    for attr in ("prependedItems", "addedItems", "appendedItems", "explicitItems"):
        values = getattr(list_op, attr, None)
        if values:
            items.extend(list(values))
    return items


def _is_local_reference_asset_path(asset_path: str) -> bool:
    return "://" not in asset_path and not asset_path.startswith("@")


def _local_reference_asset_missing(asset_path: str) -> bool:
    return _is_local_reference_asset_path(asset_path) and not Path(asset_path).exists()


def _merge_molmospaces_metadata_index(
    *,
    usd_path: Path,
    prim_paths_by_name: dict[str, list[str]],
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> None:
    metadata = _load_molmospaces_scene_metadata(usd_path)
    if not metadata:
        return

    for handle, raw_info in metadata.items():
        if not isinstance(raw_info, dict):
            continue
        prim_path = _molmospaces_metadata_prim_path(handle, prim_paths_by_name)
        if prim_path is None:
            continue
        if _is_molmospaces_receptacle_metadata(raw_info):
            receptacle_index.setdefault(
                handle,
                {
                    **_usd_metadata_index_entry(prim_path, handle, raw_info, "receptacle"),
                    "support_pose": _pose_near(handle),
                },
            )
        elif _is_molmospaces_object_metadata(raw_info):
            object_index.setdefault(
                handle,
                _usd_metadata_index_entry(prim_path, handle, raw_info, "object"),
            )


def _load_molmospaces_scene_metadata(usd_path: Path) -> dict[str, dict[str, Any]]:
    metadata_path = usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return {}
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    objects = payload.get("objects") if isinstance(payload, dict) else None
    if not isinstance(objects, dict):
        return {}
    return {
        str(handle): dict(info)
        for handle, info in objects.items()
        if isinstance(info, dict) and str(handle)
    }


def _molmospaces_metadata_prim_path(
    handle: str,
    prim_paths_by_name: dict[str, list[str]],
) -> str | None:
    candidates = list(prim_paths_by_name.get(handle) or [])
    if not candidates:
        return None
    return sorted(candidates, key=_molmospaces_prim_path_rank)[0]


def _molmospaces_prim_path_rank(prim_path: str) -> tuple[int, int, str]:
    normalized = f"/{prim_path.strip('/')}/"
    is_top_level_geometry = "/geometry/" in normalized.lower() and normalized.count("/") <= 4
    return (0 if is_top_level_geometry else 1, normalized.count("/"), prim_path)


def _usd_metadata_index_entry(
    prim_path: str,
    handle: str,
    metadata: dict[str, Any],
    kind: str,
) -> dict[str, Any]:
    category = str(metadata.get("category") or _category_from_usd_name(handle))
    metadata_object_id = str(metadata.get("object_id") or "")
    asset_id = str(metadata.get("asset_id") or "")
    label_parts = [category, metadata_object_id, asset_id]
    public_label = " ".join(part for part in label_parts if part)
    return {
        "usd_prim_path": prim_path,
        "category": category,
        "public_label": public_label or handle,
        "index_source": "usd_stage_traversal",
        "kind": kind,
        "metadata_source": "molmospaces_scene_metadata",
        "metadata_handle": handle,
        "metadata_object_id": metadata_object_id,
        "asset_id": asset_id,
        "metadata_room_id": _metadata_room_id(metadata),
        "parent": str(metadata.get("parent") or ""),
        "is_static": bool(metadata.get("is_static")),
    }


def _metadata_room_id(metadata: dict[str, Any]) -> str:
    raw_room_id = metadata.get("room_id")
    if raw_room_id in {None, ""}:
        return ""
    room_id = str(raw_room_id)
    return room_id if room_id.startswith("room_") else f"room_{room_id}"


def _is_molmospaces_object_metadata(metadata: dict[str, Any]) -> bool:
    return metadata.get("is_static") is False


def _is_molmospaces_receptacle_metadata(metadata: dict[str, Any]) -> bool:
    category = _norm(metadata.get("category"))
    if not category:
        return False
    if category in _MOLMOSPACES_SCENE_INDEX_RECEPTACLE_CATEGORY_NORMS:
        return True
    return bool(metadata.get("children")) and metadata.get("is_static") is True


_MOLMOSPACES_SCENE_INDEX_RECEPTACLE_CATEGORY_NORMS = {
    "bed",
    "bookshelf",
    "chair",
    "countertop",
    "desk",
    "diningtable",
    "dresser",
    "fridge",
    "garbagecan",
    "shelf",
    "shelvingunit",
    "sink",
    "sofa",
    "stand",
    "toilet",
    "tvstand",
}


def _usd_index_entry(prim_path: str, prim_name: str, kind: str) -> dict[str, Any]:
    return {
        "usd_prim_path": prim_path,
        "category": _category_from_usd_name(prim_name),
        "public_label": prim_name,
        "index_source": "usd_stage_traversal",
        "kind": kind,
    }


def _usd_handle_from_prim(
    prim_path: str,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> str:
    base = _usd_safe_name(Path(prim_path).name)
    if base in {"World", "Objects", "Receptacles", "Fixtures", "Scene"}:
        base = _usd_safe_name(prim_path.strip("/").replace("/", "_"))
    existing = set(object_index) | set(receptacle_index)
    if base not in existing:
        return base
    suffix = 2
    while f"{base}_{suffix}" in existing:
        suffix += 1
    return f"{base}_{suffix}"


def _is_object_prim_path(prim_path: str) -> bool:
    normalized = f"/{prim_path.strip('/').lower()}/"
    return any(
        _contains_child_segment(normalized, segment) for segment in ("objects", "movable", "props")
    )


def _is_receptacle_prim_path(prim_path: str) -> bool:
    normalized = f"/{prim_path.strip('/').lower()}/"
    return any(
        _contains_child_segment(normalized, segment)
        for segment in ("receptacles", "fixtures", "surfaces", "support_surfaces")
    )


def _contains_child_segment(normalized_path: str, segment: str) -> bool:
    token = f"/{segment}/"
    return token in normalized_path and not normalized_path.endswith(token)


def _category_from_usd_name(value: str) -> str:
    normalized = _norm(value)
    if normalized:
        return normalized
    return "unknown"


def _scene_binding_diagnostics(
    *,
    runtime_mode: str,
    scenario: CleanupScenario,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    real_smoke: dict[str, Any] | None,
) -> dict[str, Any]:
    object_bindings = {
        item.object_id: _bind_public_scene_item(
            public_id=item.object_id,
            public_label=item.name,
            category=item.category,
            index=object_index,
            kind="object",
        )
        for item in scenario.objects
    }
    receptacle_bindings = {
        item.receptacle_id: _bind_public_scene_item(
            public_id=item.receptacle_id,
            public_label=item.name,
            category=item.category or item.kind,
            index=receptacle_index,
            kind="receptacle",
        )
        for item in scenario.receptacles
    }
    selected_object_ids = _selected_cleanup_object_ids(scenario)
    selected_receptacle_ids = _selected_cleanup_receptacle_ids(scenario)
    selected_object_bindings = {
        object_id: object_bindings.get(object_id) or _unbound_scene_item(object_id, "object")
        for object_id in selected_object_ids
    }
    selected_receptacle_bindings = {
        receptacle_id: receptacle_bindings.get(receptacle_id)
        or _unbound_scene_item(receptacle_id, "receptacle")
        for receptacle_id in selected_receptacle_ids
    }
    selected_object_bound_count = _bound_count(selected_object_bindings)
    selected_receptacle_bound_count = _bound_count(selected_receptacle_bindings)
    blockers = _binding_blockers(
        selected_object_bindings,
        selected_receptacle_bindings,
    )
    if real_smoke is None:
        status = "placeholder_mapping"
        source = "scenario_fixture"
    elif blockers:
        status = "partial"
        source = "usd_stage_traversal"
    else:
        status = "selected_bound"
        source = "usd_stage_traversal"
    return {
        "schema": SCENE_BINDING_SCHEMA,
        "status": status,
        "source": source,
        "runtime_mode": runtime_mode,
        "public_object_count": len(object_bindings),
        "public_receptacle_count": len(receptacle_bindings),
        "public_object_bound_count": _bound_count(object_bindings),
        "public_receptacle_bound_count": _bound_count(receptacle_bindings),
        "selected_object_count": len(selected_object_bindings),
        "selected_target_receptacle_count": len(selected_receptacle_bindings),
        "selected_object_bound_count": selected_object_bound_count,
        "selected_target_receptacle_bound_count": selected_receptacle_bound_count,
        "object_bindings": object_bindings,
        "receptacle_bindings": receptacle_bindings,
        "selected_object_bindings": selected_object_bindings,
        "selected_target_receptacle_bindings": selected_receptacle_bindings,
        "blockers": blockers,
        "private_manifest_exposed_to_agent": False,
    }


def _bind_public_scene_item(
    *,
    public_id: str,
    public_label: str,
    category: str | None,
    index: dict[str, dict[str, Any]],
    kind: str,
) -> dict[str, Any]:
    match = _scene_index_match(
        public_id=public_id,
        public_label=public_label,
        category=category,
        index=index,
        kind=kind,
    )
    if match is None:
        return _unbound_scene_item(public_id, kind)
    handle, entry, strategy = match
    return {
        "status": "bound",
        "kind": kind,
        "public_id": public_id,
        "usd_handle": handle,
        "usd_prim_path": str(entry.get("usd_prim_path") or ""),
        "public_label": public_label,
        "category": category or "",
        "usd_public_label": str(entry.get("public_label") or ""),
        "usd_category": str(entry.get("category") or ""),
        "match_strategy": strategy,
        "index_source": str(entry.get("index_source") or ""),
        "has_renderable_geometry": entry.get("has_renderable_geometry"),
        "renderable_descendant_count": int(entry.get("renderable_descendant_count") or 0),
        "mesh_descendant_count": int(entry.get("mesh_descendant_count") or 0),
        "authored_reference_count": int(entry.get("authored_reference_count") or 0),
        "missing_referenced_asset_count": int(entry.get("missing_referenced_asset_count") or 0),
        "missing_referenced_assets": list(entry.get("missing_referenced_assets") or [])[:5],
        "geometry_status": str(entry.get("geometry_status") or ""),
    }


def _scene_index_match(
    *,
    public_id: str,
    public_label: str,
    category: str | None,
    index: dict[str, dict[str, Any]],
    kind: str,
) -> tuple[str, dict[str, Any], str] | None:
    if public_id in index:
        return public_id, index[public_id], "exact_public_id"
    public_norm = _norm(public_id)
    label_norm = _norm(public_label)
    for handle, entry in index.items():
        handle_norm = _norm(handle)
        prim_name_norm = _norm(Path(str(entry.get("usd_prim_path") or "")).name)
        entry_label_norm = _norm(entry.get("public_label"))
        if public_norm and public_norm in {handle_norm, prim_name_norm, entry_label_norm}:
            return handle, entry, "normalized_public_id"
        if label_norm and label_norm in {handle_norm, prim_name_norm, entry_label_norm}:
            return handle, entry, "normalized_public_label"

    prefix_match = _first_semantic_index_match(
        public_id=public_id,
        public_label=public_label,
        category=category,
        index=index,
        kind=kind,
    )
    if prefix_match is not None:
        return prefix_match

    category_norm = _norm(category)
    if not category_norm or not _allow_category_fallback(kind, category_norm):
        return None
    category_matches = [
        (handle, entry)
        for handle, entry in index.items()
        if _norm(entry.get("category")) == category_norm
        or category_norm in _norm(entry.get("public_label"))
    ]
    if len(category_matches) == 1:
        handle, entry = category_matches[0]
        return handle, entry, "unique_category"
    return None


def _first_semantic_index_match(
    *,
    public_id: str,
    public_label: str,
    category: str | None,
    index: dict[str, dict[str, Any]],
    kind: str,
) -> tuple[str, dict[str, Any], str] | None:
    public_prefix = _public_handle_prefix(public_id)
    if public_prefix:
        matches = _semantic_index_matches((public_prefix,), index)
        if matches:
            handle, entry = matches[0]
            return handle, entry, "public_id_prefix_first"

    label_tokens = _scene_match_tokens(public_label)
    if label_tokens:
        matches = _semantic_index_matches(tuple(sorted(label_tokens)), index)
        if matches:
            handle, entry = matches[0]
            return handle, entry, "semantic_label_token_first"

    category_norm = _norm(category)
    if category_norm and _allow_category_fallback(kind, category_norm):
        category_tokens = _scene_match_tokens(category)
        matches = _semantic_index_matches(tuple(sorted(category_tokens)), index)
        if len(matches) == 1:
            handle, entry = matches[0]
            return handle, entry, "semantic_category_token_unique"
    return None


def _semantic_index_matches(
    tokens: tuple[str, ...],
    index: dict[str, dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    matches: list[tuple[str, dict[str, Any]]] = []
    for handle, entry in sorted(index.items()):
        entry_text = _norm(
            " ".join(
                str(entry.get(key) or "")
                for key in (
                    "metadata_handle",
                    "public_label",
                    "category",
                    "metadata_object_id",
                    "asset_id",
                )
            )
        )
        handle_norm = _norm(handle)
        if any(
            token and (handle_norm.startswith(token) or token in entry_text) for token in tokens
        ):
            matches.append((handle, entry))
    return matches


def _public_handle_prefix(public_id: str) -> str:
    prefix = str(public_id or "").split("_", 1)[0]
    normalized = _norm(prefix)
    return normalized if len(normalized) >= 3 else ""


def _allow_category_fallback(kind: str, category_norm: str) -> bool:
    if not category_norm:
        return False
    if kind == "object" and category_norm in _GENERIC_CLEANUP_OBJECT_CATEGORY_NORMS:
        return False
    return True


_GENERIC_CLEANUP_OBJECT_CATEGORY_NORMS = {
    # These are public cleanup buckets, not Isaac USD object categories.
    "book",
    "dish",
    "electronics",
    "food",
    "linen",
    "toy",
}


def _scene_match_tokens(*values: Any) -> set[str]:
    tokens: set[str] = set()
    for value in values:
        text = str(value or "")
        for token in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", text):
            normalized = _norm(token)
            if len(normalized) >= 3:
                tokens.add(normalized)
        normalized = _norm(text)
        if len(normalized) >= 3:
            tokens.add(normalized)
    for token, aliases in {
        "remotecontrol": ("remote",),
        "cellphone": ("phone", "cellulartelephone"),
        "cellulartelephone": ("phone", "cellphone"),
        "tvstand": ("stand",),
    }.items():
        if token in tokens:
            tokens.update(aliases)
    return tokens


def _unbound_scene_item(public_id: str, kind: str) -> dict[str, Any]:
    return {
        "status": "unresolved",
        "kind": kind,
        "public_id": public_id,
        "usd_handle": "",
        "usd_prim_path": "",
        "match_strategy": "none",
        "blocker": "No stable USD prim candidate matched this public cleanup handle.",
    }


def _binding_blockers(
    selected_object_bindings: dict[str, dict[str, Any]],
    selected_receptacle_bindings: dict[str, dict[str, Any]],
) -> list[str]:
    blockers = []
    for object_id, binding in selected_object_bindings.items():
        if binding.get("status") != "bound":
            blockers.append(f"Selected cleanup object has no USD binding: {object_id}")
    for receptacle_id, binding in selected_receptacle_bindings.items():
        if binding.get("status") != "bound":
            blockers.append(f"Selected target receptacle has no USD binding: {receptacle_id}")
    return blockers


def _bound_count(bindings: dict[str, dict[str, Any]]) -> int:
    return sum(1 for item in bindings.values() if item.get("status") == "bound")


def _selected_cleanup_object_ids(scenario: CleanupScenario) -> list[str]:
    return _dedupe(target.object_id for target in scenario.private_manifest.targets)


def _selected_cleanup_receptacle_ids(scenario: CleanupScenario) -> list[str]:
    return _dedupe(
        receptacle_id
        for target in scenario.private_manifest.targets
        for receptacle_id in target.valid_receptacle_ids
    )


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
) -> dict[str, Any]:
    import isaaclab.sim as sim_utils
    import isaacsim.core.utils.stage as stage_utils
    import numpy as np
    import torch
    from isaaclab.sensors.camera import Camera, CameraCfg

    opened = stage_utils.open_stage(str(scene_usd))
    if opened is False:
        raise RuntimeError(f"Isaac Sim failed to open generated USD stage: {scene_usd}")
    _wait_for_stage_load(stage_utils, simulation_app)
    _load_current_stage_payloads(stage_utils)
    pose_apply = _apply_semantic_pose_state_to_stage(
        stage_utils=stage_utils,
        semantic_pose_state=semantic_pose_state,
    )
    robot_stage = _ensure_rby1m_robot_on_stage(
        stage_utils=stage_utils,
        robot_import=_dict(robot_import),
    )
    if robot_stage.get("head_camera_prim_exists") is True and hasattr(
        sim_utils, "standardize_xform_ops"
    ):
        current_stage = stage_utils.get_current_stage()
        if current_stage is not None:
            sim_utils.standardize_xform_ops(
                current_stage.GetPrimAtPath(ISAAC_RBY1M_HEAD_CAMERA_PRIM)
            )
    scene_bounds = _current_stage_bounds(stage_utils)
    _ensure_capture_lighting(stage_utils)
    semantic_label_application = (
        _apply_scene_index_semantic_labels(
            stage_utils=stage_utils,
            sim_utils=sim_utils,
            scene_index_diagnostics=scene_index_diagnostics,
        )
        if include_segmentation
        else _semantic_label_application_not_requested()
    )
    camera_semantic_filter: str | list[str]
    camera_semantic_filter = list(semantic_filter) if include_segmentation else "*:*"
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(device=device))
    mounted_head_camera = robot_stage.get("head_camera_prim_exists") is True
    data_types = [
        "rgb",
        *(segmentation_data_types if include_segmentation else ()),
    ]
    camera_spawn = sim_utils.PinholeCameraCfg(
        focal_length=24.0,
        focus_distance=4.0,
        horizontal_aperture=20.955,
    )
    head_camera = (
        Camera(
            cfg=CameraCfg(
                prim_path=ISAAC_RBY1M_HEAD_CAMERA_PRIM,
                update_period=0.0,
                height=height,
                width=width,
                data_types=data_types,
                semantic_filter=camera_semantic_filter,
                colorize_semantic_segmentation=False,
                colorize_instance_segmentation=False,
                colorize_instance_id_segmentation=False,
                spawn=None,
            )
        )
        if mounted_head_camera
        else None
    )
    sim_utils.create_prim("/World/RoboclawsSmokeCameraRig", "Xform")
    scene_camera = Camera(
        cfg=CameraCfg(
            prim_path="/World/RoboclawsSmokeCameraRig/Camera",
            update_period=0.0,
            height=height,
            width=width,
            data_types=data_types,
            semantic_filter=camera_semantic_filter,
            colorize_semantic_segmentation=False,
            colorize_instance_segmentation=False,
            colorize_instance_id_segmentation=False,
            spawn=camera_spawn,
        )
    )
    view_poses = _isaac_camera_view_poses(torch=torch, device=sim.device, scene_bounds=scene_bounds)
    sim.reset()
    saved: dict[str, str] = {}
    segmentation_views: list[dict[str, Any]] = []
    total_render_steps = 0
    robot_pose_application: dict[str, Any] = {}
    for view_name in ROBOT_VIEW_KEYS:
        if view_name == "fpv" and mounted_head_camera:
            camera = head_camera
            if camera is None:
                raise RuntimeError("mounted head camera was requested but Camera sensor is absent")
            robot_pose_application = _position_robot_for_head_camera_view(
                stage_utils=stage_utils,
                scene_bounds=scene_bounds,
                semantic_pose_state=semantic_pose_state,
            )
        else:
            camera = scene_camera
            positions, targets = view_poses[view_name]
            camera.set_world_poses_from_view(positions, targets)
        rgb_image = None
        for _ in range(24):
            sim.step()
            total_render_steps += 1
            camera.update(dt=sim.get_physics_dt())
            rgb_image = _rgb_tensor_to_uint8(camera.data.output.get("rgb"), np=np)
            if rgb_image is not None and _image_has_variance(rgb_image, np=np):
                break
        if rgb_image is None:
            raise RuntimeError(f"Isaac Lab camera did not produce an RGB tensor for {view_name}")
        if not _image_has_variance(rgb_image, np=np):
            raise RuntimeError(f"Isaac Lab camera RGB tensor was blank for {view_name}")
        output_path = view_paths[view_name]
        output_path.parent.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb_image, mode="RGB").save(output_path)
        saved[view_name] = str(output_path)
        if include_segmentation:
            segmentation_views.append(
                _camera_segmentation_view_diagnostics(
                    camera,
                    data_types=segmentation_data_types,
                    view_name=view_name,
                    np=np,
                )
            )
    return {
        "render_steps": total_render_steps,
        "robot_view_images": saved,
        "scene_bounds": scene_bounds,
        "robot_stage": robot_stage,
        "robot_view_uses_mounted_head_camera": mounted_head_camera,
        "robot_pose_stage_application": robot_pose_application,
        "semantic_pose_stage_application": pose_apply,
        "segmentation": _camera_segmentation_capture_diagnostics(
            segmentation_views,
            requested_data_types=segmentation_data_types,
            semantic_label_application=semantic_label_application,
            semantic_filter=camera_semantic_filter,
        )
        if include_segmentation
        else _camera_segmentation_not_requested_diagnostics(),
    }


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
    import isaaclab.sim as sim_utils
    import isaacsim.core.utils.stage as stage_utils
    import numpy as np
    import torch
    from isaaclab.sensors.camera import Camera, CameraCfg

    opened = stage_utils.open_stage(str(scene_usd))
    if opened is False:
        raise RuntimeError(f"Isaac Sim failed to open generated USD stage: {scene_usd}")
    _wait_for_stage_load(stage_utils, simulation_app)
    _load_current_stage_payloads(stage_utils)
    pose_apply = _apply_semantic_pose_state_to_stage(
        stage_utils=stage_utils,
        semantic_pose_state=semantic_pose_state,
    )
    scene_bounds = _current_stage_bounds(stage_utils)
    camera_request = normalize_camera_control_request(camera_request, width=width, height=height)
    resolution = camera_request["render_resolution"]
    width = int(resolution["width"])
    height = int(resolution["height"])
    lighting_diagnostics = _ensure_capture_lighting(
        stage_utils,
        profile=camera_request.get("lighting_profile"),
    )
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(device=device))
    lens = camera_request.get("lens") if isinstance(camera_request.get("lens"), dict) else {}
    color_profile = camera_request.get("color_profile") or {}
    focal_length = float(lens.get("focal_length_mm", 24.0))
    horizontal_aperture = _horizontal_aperture_from_lens(
        lens,
        width=width,
        height=height,
        focal_length=focal_length,
    )
    sim_utils.create_prim("/World/RoboclawsSceneProbeCameraRig", "Xform")
    camera = Camera(
        cfg=CameraCfg(
            prim_path="/World/RoboclawsSceneProbeCameraRig/Camera",
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
        "lens": camera_request.get("lens") or {},
        "derived_lens": {
            "focal_length_mm": focal_length,
            "horizontal_aperture_mm": horizontal_aperture,
        },
        "render_steps": total_render_steps,
        "scene_bounds": scene_bounds,
        "semantic_pose_stage_application": pose_apply,
        "views": views,
        "images": saved,
        "shapes": shapes,
    }


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
        UsdGeom.XformCommonAPI(object_prim).SetTranslate(Gf.Vec3d(*target))
        applied.append(
            {
                "object_id": str(object_id),
                "object_usd_prim_path": object_prim_path,
                "support_receptacle_id": support_id,
                "target_position": list(target),
            }
        )
    return {
        "schema": "isaac_semantic_pose_stage_application_v1",
        "status": "applied" if applied and not failed else ("partial" if applied else "blocked"),
        "applied_object_count": len(applied),
        "failed_object_count": len(failed),
        "applied_objects": applied,
        "failed_objects": failed,
        "rendered_to_usd": bool(applied),
    }


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
    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    add_labels = getattr(sim_utils, "add_labels", None)
    if not callable(get_current_stage) or not callable(add_labels):
        return {
            "status": "unavailable",
            "applied_count": 0,
            "failed_count": 0,
            "missing_prim_count": 0,
            "gprim_label_count": 0,
            "mesh_label_count": 0,
            "target_samples": [],
            "reason": "Isaac semantic label utilities were unavailable.",
        }
    stage = get_current_stage()
    if stage is None:
        return {
            "status": "unavailable",
            "applied_count": 0,
            "failed_count": 0,
            "missing_prim_count": 0,
            "gprim_label_count": 0,
            "mesh_label_count": 0,
            "target_samples": [],
            "reason": "No current Isaac stage was available for semantic labels.",
        }
    index = _dict(scene_index_diagnostics)
    entries = [
        *(_dict(index.get("object_index")).values()),
        *(_dict(index.get("receptacle_index")).values()),
    ]
    applied = 0
    labeled_prim_count = 0
    descendant_label_count = 0
    gprim_label_count = 0
    mesh_label_count = 0
    missing = 0
    failed: list[dict[str, str]] = []
    target_samples: list[dict[str, str]] = []
    for raw_entry in entries:
        entry = _dict(raw_entry)
        prim_path = str(entry.get("usd_prim_path") or "")
        if not prim_path:
            continue
        prim = stage.GetPrimAtPath(prim_path)
        if not prim or not prim.IsValid():
            missing += 1
            continue
        labels = _scene_index_semantic_labels(entry, prim_path)
        try:
            targets = _semantic_label_target_prims(prim)
            for target in targets:
                for instance_name, label in labels.items():
                    add_labels(target, labels=[label], instance_name=instance_name, overwrite=True)
                labeled_prim_count += 1
                if target != prim:
                    descendant_label_count += 1
                classification = _semantic_label_target_classification(target)
                if classification["is_gprim"]:
                    gprim_label_count += 1
                if classification["type_name"] == "Mesh":
                    mesh_label_count += 1
                if len(target_samples) < 20:
                    target_samples.append(
                        {
                            "source_prim_path": prim_path,
                            "target_prim_path": classification["path"],
                            "target_type": classification["type_name"],
                            "target_kind": classification["kind"],
                        }
                    )
            applied += 1
        except Exception as exc:  # pragma: no cover - defensive around Isaac extension APIs
            failed.append({"prim_path": prim_path, "error": str(exc)})
    status = "applied" if applied and not failed else "partial" if applied else "unavailable"
    return {
        "schema": "isaac_scene_index_semantic_label_application_v1",
        "status": status,
        "applied_count": applied,
        "labeled_prim_count": labeled_prim_count,
        "descendant_label_count": descendant_label_count,
        "gprim_label_count": gprim_label_count,
        "mesh_label_count": mesh_label_count,
        "failed_count": len(failed),
        "missing_prim_count": missing,
        "requested_prim_count": len(entries),
        "failed": failed[:10],
        "target_samples": target_samples,
        "label_instances": ["class", "kind", "usd_prim_path"],
        "reason": (
            "Scene-index USD prims were labeled for Isaac camera segmentation."
            if applied
            else "No scene-index USD prims were labeled for Isaac camera segmentation."
        ),
    }


def _semantic_label_target_classification(prim: Any) -> dict[str, Any]:
    try:
        from pxr import UsdGeom
    except Exception:
        UsdGeom = None

    try:
        path = str(prim.GetPath())
    except Exception:
        path = str(getattr(prim, "path", "") or "")
    try:
        type_name = str(prim.GetTypeName() or "")
    except Exception:
        type_name = str(getattr(prim, "type_name", "") or "")
    is_gprim = False
    if UsdGeom is not None:
        try:
            is_gprim = bool(prim.IsA(UsdGeom.Gprim))
        except Exception:
            is_gprim = False
    if not is_gprim and type_name in {"Mesh", "Cube", "Sphere", "Capsule", "Cone", "Cylinder"}:
        is_gprim = True
    kind = "gprim" if is_gprim else "prim"
    if type_name:
        kind = f"{kind}:{type_name}"
    return {
        "path": path,
        "type_name": type_name,
        "kind": kind,
        "is_gprim": is_gprim,
    }


def _semantic_label_target_prims(prim: Any) -> list[Any]:
    try:
        from pxr import Usd, UsdGeom
    except Exception:
        return [prim]

    targets = _semantic_label_target_prims_once(prim, Usd=Usd, UsdGeom=UsdGeom)
    if any(_prim_is_gprim(target, UsdGeom=UsdGeom) for target in targets):
        return targets
    try:
        prim.Load()
    except Exception:
        return targets
    return _semantic_label_target_prims_once(prim, Usd=Usd, UsdGeom=UsdGeom)


def _semantic_label_target_prims_once(prim: Any, *, Usd: Any, UsdGeom: Any) -> list[Any]:
    targets = [prim]
    for descendant in Usd.PrimRange(prim):
        if descendant == prim:
            continue
        if _prim_is_gprim(descendant, UsdGeom=UsdGeom):
            targets.append(descendant)
    return targets


def _prim_is_gprim(prim: Any, *, UsdGeom: Any) -> bool:
    try:
        return bool(prim.IsA(UsdGeom.Gprim))
    except Exception:
        return False


def _semantic_label_application_not_requested() -> dict[str, Any]:
    return {
        "schema": "isaac_scene_index_semantic_label_application_v1",
        "status": "not_requested",
        "applied_count": 0,
        "labeled_prim_count": 0,
        "descendant_label_count": 0,
        "gprim_label_count": 0,
        "mesh_label_count": 0,
        "failed_count": 0,
        "missing_prim_count": 0,
        "requested_prim_count": 0,
        "failed": [],
        "target_samples": [],
        "label_instances": [],
        "reason": "Segmentation was not requested.",
    }


def _scene_index_semantic_labels(entry: dict[str, Any], prim_path: str) -> dict[str, str]:
    category = str(entry.get("category") or entry.get("public_label") or Path(prim_path).name)
    kind = str(entry.get("kind") or "scene_prim")
    return {
        "class": category,
        "kind": kind,
        "usd_prim_path": prim_path,
    }


def _camera_segmentation_view_diagnostics(
    camera: Any,
    *,
    data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    view_name: str,
    np: Any,
) -> dict[str, Any]:
    outputs = getattr(getattr(camera, "data", None), "output", {}) or {}
    info = getattr(getattr(camera, "data", None), "info", {}) or {}
    output_rows: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    for data_type in data_types:
        if data_type not in outputs:
            continue
        array = _segmentation_array(outputs.get(data_type), np=np)
        labels = _segmentation_label_map(_segmentation_info_for_data_type(info, data_type))
        row: dict[str, Any] = {
            "present": array is not None,
            "label_count": len(labels),
            "labels_available": bool(labels),
        }
        if array is not None:
            row.update(
                {
                    "shape": [int(dim) for dim in array.shape],
                    "dtype": str(array.dtype),
                    "unique_id_count": _segmentation_unique_count(array, np=np),
                }
            )
            candidates.extend(
                _segmentation_bbox_candidates(
                    array,
                    labels,
                    data_type=data_type,
                    view_name=view_name,
                    np=np,
                )
            )
        output_rows[data_type] = row
    return {
        "view": view_name,
        "outputs": output_rows,
        "candidate_bboxes": candidates[:MAX_SEGMENTATION_CANDIDATES],
    }


def _camera_segmentation_capture_diagnostics(
    views: list[dict[str, Any]],
    *,
    requested_data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    semantic_label_application: dict[str, Any] | None = None,
    semantic_filter: str | list[str] | None = None,
) -> dict[str, Any]:
    output_data_types = sorted(
        {
            data_type
            for view in views
            for data_type, row in _dict(view.get("outputs")).items()
            if _dict(row).get("present") is True
        }
    )
    candidates = [
        candidate
        for view in views
        for candidate in view.get("candidate_bboxes", [])
        if isinstance(candidate, dict)
    ]
    return {
        "schema": SEGMENTATION_SCHEMA,
        "source": "isaac_lab_camera",
        "capture_method": "isaac_lab_camera_segmentation",
        "requested_data_types": list(requested_data_types),
        "output_data_types": output_data_types,
        "tensor_output_available": bool(output_data_types),
        "semantic_filter": semantic_filter,
        "candidate_bbox_count": len(candidates),
        "candidate_bboxes": candidates[:MAX_SEGMENTATION_CANDIDATES],
        "view_outputs": views,
        "semantic_label_application": _dict(semantic_label_application),
        "no_simulator_label_fallback": True,
    }


def _camera_segmentation_not_requested_diagnostics() -> dict[str, Any]:
    return {
        "schema": SEGMENTATION_SCHEMA,
        "source": "isaac_lab_camera",
        "capture_method": "not_requested_for_rgb_runtime_smoke",
        "requested_data_types": list(ISAAC_SEGMENTATION_DATA_TYPES),
        "output_data_types": [],
        "tensor_output_available": False,
        "candidate_bbox_count": 0,
        "candidate_bboxes": [],
        "view_outputs": [],
        "no_simulator_label_fallback": True,
    }


def _segmentation_array(value: Any, *, np: Any) -> Any | None:
    if value is None:
        return None
    if hasattr(value, "detach"):
        value = value.detach()
    if hasattr(value, "cpu"):
        value = value.cpu()
    if hasattr(value, "numpy"):
        value = value.numpy()
    array = np.asarray(value)
    if array.size == 0:
        return None
    while array.ndim > 2 and array.shape[0] == 1:
        array = array[0]
    if array.ndim == 3 and array.shape[-1] == 1:
        array = array[..., 0]
    if array.ndim != 2:
        return None
    return array


def _segmentation_info_for_data_type(info: Any, data_type: str) -> dict[str, Any]:
    if isinstance(info, dict):
        nested = info.get(data_type)
        if isinstance(nested, dict):
            return nested
        return info
    if isinstance(info, (list, tuple)):
        merged: dict[str, Any] = {}
        for item in info:
            labels = _segmentation_label_map(_segmentation_info_for_data_type(item, data_type))
            if labels:
                merged.setdefault("idToLabels", {}).update(labels)
        return merged
    return {}


def _segmentation_label_map(info: Any) -> dict[int, str]:
    if isinstance(info, (list, tuple)):
        labels: dict[int, str] = {}
        for item in info:
            labels.update(_segmentation_label_map(item))
        return labels
    if not isinstance(info, dict):
        return {}
    raw_labels = (
        info.get("idToLabels")
        or info.get("id_to_labels")
        or info.get("idToSemantics")
        or info.get("id_to_semantics")
        or {}
    )
    if not isinstance(raw_labels, dict):
        return {}
    labels: dict[int, str] = {}
    for raw_id, raw_label in raw_labels.items():
        label_id = _int_or_none(raw_id)
        if label_id is None:
            continue
        label = _segmentation_label_text(raw_label)
        if label:
            labels[label_id] = label
    return labels


def _segmentation_label_text(raw_label: Any) -> str:
    if isinstance(raw_label, str):
        return raw_label
    if isinstance(raw_label, dict):
        for key in (
            "usd_prim_path",
            "prim_path",
            "path",
            "instance",
            "class",
            "semantic",
            "label",
            "name",
        ):
            value = raw_label.get(key)
            if isinstance(value, str) and value:
                return value
        return " ".join(str(value) for value in raw_label.values() if value)
    if raw_label is None:
        return ""
    return str(raw_label)


def _segmentation_unique_count(array: Any, *, np: Any) -> int:
    try:
        return int(np.unique(array).size)
    except Exception:
        return 0


def _segmentation_bbox_candidates(
    array: Any,
    labels: dict[int, str],
    *,
    data_type: str,
    view_name: str,
    np: Any,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    height, width = array.shape
    for label_id, label in sorted(labels.items()):
        mask = array == label_id
        pixel_count = int(np.count_nonzero(mask))
        if pixel_count <= 0:
            continue
        ys, xs = np.where(mask)
        if len(xs) == 0 or len(ys) == 0:
            continue
        candidate = {
            "view": view_name,
            "data_type": data_type,
            "label_id": int(label_id),
            "label": label,
            "usd_prim_path": label if label.startswith("/") else "",
            "bbox_xyxy": [
                int(xs.min()),
                int(ys.min()),
                int(xs.max()) + 1,
                int(ys.max()) + 1,
            ],
            "pixel_count": pixel_count,
            "image_size": [int(width), int(height)],
        }
        candidates.append(candidate)
        if len(candidates) >= MAX_SEGMENTATION_CANDIDATES:
            break
    return candidates


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _current_stage_bounds(stage_utils: Any) -> dict[str, list[float]] | None:
    from pxr import Usd, UsdGeom

    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return None
    stage = get_current_stage()
    if stage is None:
        return None
    root = stage.GetDefaultPrim() or stage.GetPseudoRoot()
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    bbox = cache.ComputeWorldBound(root).ComputeAlignedBox()
    min_point = [float(value) for value in bbox.GetMin()]
    max_point = [float(value) for value in bbox.GetMax()]
    size = [max_v - min_v for min_v, max_v in zip(min_point, max_point, strict=True)]
    if any(not math.isfinite(value) for value in [*min_point, *max_point, *size]) or max(size) <= 0:
        return None
    center = [(min_v + max_v) / 2.0 for min_v, max_v in zip(min_point, max_point, strict=True)]
    return {"min": min_point, "max": max_point, "size": size, "center": center}


def _ensure_capture_lighting(
    stage_utils: Any, profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    from pxr import Gf, UsdGeom, UsdLux

    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return {"status": "missing_stage_api", "existing_light_count": 0, "added_light_count": 0}
    stage = get_current_stage()
    if stage is None:
        return {"status": "missing_stage", "existing_light_count": 0, "added_light_count": 0}
    profile = profile if isinstance(profile, dict) else {}
    dome_intensity = float(profile.get("isaac_dome_intensity", 1500.0))
    key_intensity = float(profile.get("isaac_key_intensity", 7000.0))
    key_rotation = profile.get("isaac_key_rotation_deg")
    if not isinstance(key_rotation, (list, tuple)) or len(key_rotation) < 3:
        key_rotation = [-55.0, 0.0, 35.0]
    existing_lights = _stage_light_paths(stage, exclude_prefix="/RoboclawsSmoke")
    added_lights = []
    if dome_intensity > 0.0:
        dome = UsdLux.DomeLight.Define(stage, "/RoboclawsSmokeDomeLight")
        dome.CreateIntensityAttr(dome_intensity)
        added_lights.append("/RoboclawsSmokeDomeLight")
    if key_intensity > 0.0:
        key = UsdLux.DistantLight.Define(stage, "/RoboclawsSmokeKeyLight")
        key.CreateIntensityAttr(key_intensity)
        UsdGeom.XformCommonAPI(key).SetRotate(
            Gf.Vec3f(float(key_rotation[0]), float(key_rotation[1]), float(key_rotation[2]))
        )
        added_lights.append("/RoboclawsSmokeKeyLight")
    return {
        "schema": "isaac_capture_lighting_diagnostics_v1",
        "status": "using_existing_stage_lights" if not added_lights else "added_capture_lights",
        "profile_id": str(profile.get("profile_id") or ""),
        "existing_light_count": len(existing_lights),
        "existing_light_paths": existing_lights,
        "added_light_count": len(added_lights),
        "added_light_paths": added_lights,
        "requested_dome_intensity": dome_intensity,
        "requested_key_intensity": key_intensity,
    }


def _stage_light_paths(
    stage: Any, *, exclude_prefix: str = "", light_api: Any | None = None
) -> list[str]:
    if light_api is None:
        from pxr import UsdLux

        light_api = UsdLux.LightAPI
    paths = []
    for prim in stage.Traverse():
        if not prim or not prim.IsValid():
            continue
        path = str(prim.GetPath())
        if exclude_prefix and path.startswith(exclude_prefix):
            continue
        if prim.IsA(light_api) or _prim_type_is_light(prim):
            paths.append(path)
    return paths


_USD_LIGHT_TYPE_NAMES = frozenset(
    {
        "CylinderLight",
        "DiskLight",
        "DistantLight",
        "DomeLight",
        "GeometryLight",
        "PortalLight",
        "RectLight",
        "SphereLight",
    }
)


def _prim_type_is_light(prim: Any) -> bool:
    type_name = ""
    get_type_name = getattr(prim, "GetTypeName", None)
    if callable(get_type_name):
        type_name = str(get_type_name() or "")
    if not type_name:
        get_type_info = getattr(prim, "GetPrimTypeInfo", None)
        if callable(get_type_info):
            type_info = get_type_info()
            info_type_name = getattr(type_info, "GetTypeName", None)
            if callable(info_type_name):
                type_name = str(info_type_name() or "")
    return type_name in _USD_LIGHT_TYPE_NAMES


def _isaac_camera_view_poses(
    *,
    torch: Any,
    device: Any,
    scene_bounds: dict[str, list[float]] | None = None,
) -> dict[str, tuple[Any, Any]]:
    def tensor(values: list[list[float]]) -> Any:
        return torch.tensor(values, dtype=torch.float32, device=device)

    if scene_bounds:
        center = scene_bounds["center"]
        size = scene_bounds["size"]
        span_x = max(size[0], 1.5)
        span_y = max(size[1], 1.5)
        span = max(span_x, span_y, size[2], 2.0)
        floor_z = scene_bounds["min"][2]
        target_z = max(floor_z + 0.9, center[2])
        target = [center[0], center[1], target_z]
        return {
            "fpv": (
                tensor([[center[0] - span_x * 0.35, center[1] - span_y * 0.55, floor_z + 1.25]]),
                tensor([target]),
            ),
            "chase": (
                tensor([[center[0] + span_x * 0.55, center[1] - span_y * 0.75, floor_z + 2.4]]),
                tensor([[center[0], center[1], target_z * 0.9]]),
            ),
            "map": (
                tensor([[center[0], center[1], scene_bounds["max"][2] + span * 1.25]]),
                tensor([[center[0], center[1], floor_z]]),
            ),
            "verify": (
                tensor([[center[0] - span_x * 0.18, center[1] - span_y * 0.35, floor_z + 1.6]]),
                tensor([[center[0] + span_x * 0.08, center[1] + span_y * 0.05, target_z]]),
            ),
        }

    return {
        "fpv": (tensor([[1.35, -1.35, 1.1]]), tensor([[0.05, 0.0, 0.55]])),
        "chase": (tensor([[2.4, -2.6, 1.8]]), tensor([[0.0, 0.0, 0.35]])),
        "map": (tensor([[0.05, -0.05, 4.2]]), tensor([[0.0, 0.0, 0.0]])),
        "verify": (tensor([[0.9, -1.0, 0.85]]), tensor([[0.2, -0.15, 0.55]])),
    }


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
        "head_pitch": _optional_float(pose.get("head_pitch")),
        "head_pitch_source": str(pose.get("head_pitch_source") or ""),
        "head_pitch_applied": False,
        "head_pitch_note": (
            "The current static Isaac robot USD has a mounted head_camera prim but no "
            "articulated head joint drive in this render path; base yaw is applied to "
            "the robot root, while head pitch remains recorded for parity diagnostics."
        ),
    }


def _robot_pose_yaw_deg(pose: dict[str, Any]) -> float | None:
    if not isinstance(pose, dict):
        return None
    try:
        if "theta" in pose:
            return round(math.degrees(float(pose["theta"])), 6)
        if "yaw_deg" in pose:
            return round(float(pose["yaw_deg"]), 6)
    except (TypeError, ValueError):
        return None
    return None


def _optional_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


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


def _isaac_scene_camera_view_spec(
    raw_spec: dict[str, Any],
    *,
    index: int,
    stage_utils: Any | None = None,
) -> dict[str, Any]:
    view_id = str(raw_spec.get("view_id") or raw_spec.get("id") or f"view_{index:02d}")
    safe_view_id = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in view_id)
    usd_prim_path = str(raw_spec.get("usd_prim_path") or "")
    usd_bounds = _bounds_from_usd_prim_path(
        stage_utils=stage_utils,
        usd_prim_path=usd_prim_path,
        min_target_z=float(raw_spec.get("min_target_z", 0.6)),
    )
    usd_bounds_target = usd_bounds.get("target") if isinstance(usd_bounds, dict) else None
    target_source = "usd_prim_world_bounds" if usd_bounds_target is not None else ""
    if raw_spec.get("camera_model") == CANONICAL_CAMERA_MODEL:
        target = _camera_vec3(raw_spec.get("target") or raw_spec.get("lookat"), default=[0, 0, 0])
        target_source = "canonical_explicit_target"
    elif usd_bounds_target is not None:
        target = usd_bounds_target
    else:
        target = _camera_vec3(raw_spec.get("target") or raw_spec.get("lookat"), default=[0, 0, 0])
        target_source = "explicit_target_or_default"
    backend_transform = _backend_transform_for_lane(raw_spec, "isaaclab-prepared-usd")
    if "eye" in raw_spec and raw_spec.get("eye") is not None:
        eye = _camera_vec3(
            raw_spec.get("eye"),
            default=[target[0], target[1] - 4.0, target[2] + 2.0],
        )
        if backend_transform:
            eye = _apply_scene_transform_to_point(eye, backend_transform)
            target = _apply_scene_transform_to_point(target, backend_transform)
    else:
        camera_orbit = _lane_camera_orbit(raw_spec, "isaaclab-prepared-usd")
        eye = _eye_from_lookat_spec(
            target=target,
            distance=float(camera_orbit.get("distance_m", raw_spec.get("distance", 4.0))),
            azimuth=float(camera_orbit.get("azimuth_deg", raw_spec.get("azimuth", 225.0))),
            elevation=abs(
                float(camera_orbit.get("elevation_deg", raw_spec.get("elevation", 35.0)))
            ),
        )
    return {
        "view_id": safe_view_id,
        "label": str(raw_spec.get("label") or view_id),
        "anchor_id": str(raw_spec.get("anchor_id") or ""),
        "anchor_kind": str(raw_spec.get("anchor_kind") or ""),
        "robot_view_role": str(raw_spec.get("robot_view_role") or ""),
        "camera_basis": str(raw_spec.get("camera_basis") or ""),
        "camera_mode": str(raw_spec.get("camera_mode") or "free_camera"),
        "usd_prim_path": usd_prim_path,
        "eye": eye,
        "target": target,
        "lookat": target,
        "backend_eye": eye,
        "backend_target": target,
        "usd_bounds_target": usd_bounds_target,
        "usd_bounds": usd_bounds,
        "target_source": target_source,
        "camera_model": str(raw_spec.get("camera_model") or ANCHOR_ORBIT_CAMERA_MODEL),
        "coordinate_frame": str(raw_spec.get("coordinate_frame") or ""),
        "camera_orbit": dict(_lane_camera_orbit(raw_spec, "isaaclab-prepared-usd")),
        "lens": dict(raw_spec.get("lens")) if isinstance(raw_spec.get("lens"), dict) else {},
        "calibration_status": str(raw_spec.get("calibration_status") or ""),
        "coordinate_convention": str(raw_spec.get("coordinate_convention") or ""),
    }


def _lane_camera_orbit(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    lane_orbits = raw_spec.get("lane_camera_orbits")
    if isinstance(lane_orbits, dict):
        lane_orbit = lane_orbits.get(lane_id)
        if isinstance(lane_orbit, dict):
            return lane_orbit
    camera_orbit = raw_spec.get("camera_orbit")
    return camera_orbit if isinstance(camera_orbit, dict) else {}


def _backend_transform_for_lane(raw_spec: dict[str, Any], lane_id: str) -> dict[str, Any]:
    transforms = raw_spec.get("backend_transforms")
    if isinstance(transforms, dict):
        transform = transforms.get(lane_id)
        if isinstance(transform, dict):
            return transform
    return {}


def _apply_scene_transform_to_point(point: list[float], transform: dict[str, Any]) -> list[float]:
    scale = float(transform.get("xy_scale", 1.0))
    rotation_rad = math.radians(float(transform.get("rotation_z_deg", 0.0)))
    raw_translation = transform.get("translation")
    translation = raw_translation if isinstance(raw_translation, list) else []
    tx = float(translation[0]) if len(translation) > 0 else 0.0
    ty = float(translation[1]) if len(translation) > 1 else 0.0
    tz = float(translation[2]) if len(translation) > 2 else 0.0
    x = float(point[0])
    y = float(point[1])
    return [
        scale * (math.cos(rotation_rad) * x - math.sin(rotation_rad) * y) + tx,
        scale * (math.sin(rotation_rad) * x + math.cos(rotation_rad) * y) + ty,
        float(point[2]) + tz,
    ]


def _horizontal_aperture_from_lens(
    lens: dict[str, Any],
    *,
    width: int,
    height: int,
    focal_length: float,
) -> float:
    if "vertical_fov_deg" in lens:
        vertical_fov_rad = math.radians(float(lens["vertical_fov_deg"]))
        vertical_aperture = 2.0 * focal_length * math.tan(vertical_fov_rad / 2.0)
        return vertical_aperture * float(width) / float(height)
    return float(lens.get("horizontal_aperture_mm", 20.955))


def _bounds_from_usd_prim_path(
    *,
    stage_utils: Any | None,
    usd_prim_path: str,
    min_target_z: float,
) -> dict[str, Any] | None:
    if stage_utils is None or not usd_prim_path:
        return None
    from pxr import Usd, UsdGeom

    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return None
    stage = get_current_stage()
    if stage is None:
        return None
    prim = stage.GetPrimAtPath(usd_prim_path)
    if not prim or not prim.IsValid():
        return None
    cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    bbox = cache.ComputeWorldBound(prim).ComputeAlignedBox()
    min_point = [float(value) for value in bbox.GetMin()]
    max_point = [float(value) for value in bbox.GetMax()]
    size = [max_v - min_v for min_v, max_v in zip(min_point, max_point, strict=True)]
    if any(not math.isfinite(value) for value in [*min_point, *max_point, *size]):
        return None
    if max(size) <= 0:
        return None
    center = [(min_v + max_v) / 2.0 for min_v, max_v in zip(min_point, max_point, strict=True)]
    target = list(center)
    target[2] = max(target[2], min_target_z)
    return {
        "min": min_point,
        "max": max_point,
        "size": size,
        "center": center,
        "target": target,
        "target_z_floor": min_target_z,
    }


def _eye_from_lookat_spec(
    *,
    target: list[float],
    distance: float,
    azimuth: float,
    elevation: float,
) -> list[float]:
    azimuth_rad = math.radians(azimuth)
    elevation_rad = math.radians(elevation)
    horizontal = math.cos(elevation_rad) * distance
    return [
        float(target[0]) + math.sin(azimuth_rad) * horizontal,
        float(target[1]) + math.cos(azimuth_rad) * horizontal,
        float(target[2]) + math.sin(elevation_rad) * distance,
    ]


def _camera_vec3(value: Any, *, default: list[float]) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return [float(default[0]), float(default[1]), float(default[2])]
    return [float(value[0]), float(value[1]), float(value[2])]


def _image_has_variance(array: Any, *, np: Any) -> bool:
    return bool(np.max(array) > np.min(array))


def _module_version(module_name: str) -> str | None:
    try:
        module = __import__(module_name)
    except Exception:
        return None
    return str(getattr(module, "__version__", "unknown"))


def _usd_safe_name(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value)
    if not cleaned:
        return "unnamed"
    if cleaned[0].isdigit():
        return f"_{cleaned}"
    return cleaned


def runtime_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    isaac_lab_version = real_smoke.get("isaac_lab_version") if real_smoke else None
    isaac_sim_version = real_smoke.get("isaac_sim_version") if real_smoke else None
    if runtime_mode == "real":
        try:
            import isaaclab

            isaac_lab_version = isaac_lab_version or getattr(isaaclab, "__version__", "unknown")
        except Exception:
            isaac_lab_version = isaac_lab_version or None
        try:
            import isaacsim

            isaac_sim_version = isaac_sim_version or getattr(isaacsim, "__version__", "unknown")
        except Exception:
            isaac_sim_version = isaac_sim_version or None
    cuda_available = False
    gpu_name = ""
    gpu_vram_mb = None
    try:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        if cuda_available:
            gpu_name = str(torch.cuda.get_device_name(0))
            props = torch.cuda.get_device_properties(0)
            gpu_vram_mb = int(props.total_memory / (1024 * 1024))
    except Exception:
        pass
    rendering = rendering_diagnostics(runtime_mode, real_smoke=real_smoke)
    camera_resolution = (
        list(real_smoke["camera_resolution"])
        if real_smoke and real_smoke.get("camera_resolution")
        else [DEFAULT_WIDTH, DEFAULT_HEIGHT]
    )
    return {
        "runtime_mode": runtime_mode,
        "python_version": platform.python_version(),
        "isaac_sim_version": isaac_sim_version,
        "isaac_lab_version": isaac_lab_version,
        "cuda_available": cuda_available,
        "gpu_name": gpu_name,
        "gpu_vram_mb": gpu_vram_mb,
        "renderer_mode": rendering["renderer_mode"],
        "rendering": rendering,
        "visual_artifact_provenance": rendering["visual_artifact_provenance"],
        "camera_resolution": camera_resolution,
        "physical_robot": False,
        "planner_backed": False,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
    }


def rendering_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if real_smoke is not None:
        return {
            "status": "real_rendering_proven",
            "renderer_mode": str(real_smoke.get("renderer_mode") or REAL_SMOKE_RENDERER_MODE),
            "real_rendering_proven": True,
            "placeholder_visuals": False,
            "visual_artifact_provenance": REAL_SMOKE_CAPTURE_METHOD,
            "capture_method": str(real_smoke.get("capture_method") or REAL_SMOKE_CAPTURE_METHOD),
            "render_steps": int(real_smoke.get("render_steps") or 0),
            "image_path": str(real_smoke["image_path"]),
            "reason": (
                "The worker launched Isaac Lab, loaded a generated Phase A USD "
                "stage, and saved an RGB camera frame from the Isaac renderer."
            ),
        }
    if runtime_mode == "real":
        return {
            "status": "runtime_import_only",
            "renderer_mode": "isaac_runtime_unvalidated",
            "real_rendering_proven": False,
            "placeholder_visuals": True,
            "visual_artifact_provenance": "placeholder_protocol_image",
            "reason": (
                "The worker imports Isaac Lab in real mode, but real Isaac app "
                "launch, scene loading, and camera capture are not implemented "
                "in this semantic-pose scaffold yet."
            ),
        }
    return {
        "status": "fake_protocol",
        "renderer_mode": "fake_isaac_protocol",
        "real_rendering_proven": False,
        "placeholder_visuals": True,
        "visual_artifact_provenance": "fake_protocol_placeholder_image",
        "reason": "CI-safe fake mode writes deterministic placeholder images only.",
    }


def scene_load_diagnostics(
    runtime_mode: str,
    scene_source: str,
    scene_index: int,
    *,
    real_smoke: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if real_smoke is not None:
        loaded_asset_kind = str(
            real_smoke.get("loaded_asset_kind") or "generated_runtime_smoke_usd"
        )
        reason = (
            "Phase A loaded a generated local USD stage through Isaac Sim. "
            "MolmoSpaces USD scene loading remains a separate parity gate."
        )
        if loaded_asset_kind == "local_scene_usd":
            reason = (
                "Real mode loaded the caller-supplied local USD stage through Isaac Sim. "
                "If this is a MolmoSpaces scene, object/receptacle parity is recorded "
                "in the USD scene index diagnostics."
            )
        return {
            "status": "loaded",
            "scene_source": scene_source,
            "scene_index": scene_index,
            "scene_usd": str(real_smoke["scene_usd"]),
            "usd_stage_loaded": True,
            "loaded_asset_kind": loaded_asset_kind,
            "requested_molmospaces_scene_usd": _scene_usd_path(scene_source, scene_index),
            "manual_editor_steps_required": False,
            "stage_prim_count": int(real_smoke.get("stage_prim_count") or 0),
            "reason": reason,
        }
    if runtime_mode == "real":
        status = "blocked_capability"
        reason = (
            "Real Isaac USD scene loading is not implemented in this "
            "semantic-pose scaffold. A future local-dev pass must launch Isaac "
            "Sim/Lab and prove the selected USD scene loads."
        )
    else:
        status = "fake_protocol"
        reason = (
            "Fake mode derives scenario state from synthetic/map fixtures, not an Isaac USD stage."
        )
    return {
        "status": status,
        "scene_source": scene_source,
        "scene_index": scene_index,
        "scene_usd": _scene_usd_path(scene_source, scene_index),
        "usd_stage_loaded": False,
        "manual_editor_steps_required": None if runtime_mode == "real" else False,
        "reason": reason,
    }


def segmentation_diagnostics(
    runtime_mode: str,
    *,
    real_smoke: dict[str, Any] | None = None,
    scene_binding_diagnostics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selected_paths = _selected_bound_usd_prim_paths(scene_binding_diagnostics)
    selected_unrenderable_paths = _selected_unrenderable_usd_prim_paths(scene_binding_diagnostics)
    if real_smoke is None:
        source = "fake_protocol" if runtime_mode == "fake" else "real_isaac_pending"
        return {
            "schema": SEGMENTATION_SCHEMA,
            "available": False,
            "status": "blocked_capability",
            "source": source,
            "capture_method": "not_attempted",
            "requested_data_types": list(ISAAC_SEGMENTATION_DATA_TYPES),
            "output_data_types": [],
            "tensor_output_available": False,
            "candidate_overlay_status": "blocked_capability",
            "candidate_bbox_count": 0,
            "selected_usd_prim_match_count": 0,
            "selected_usd_prim_paths": selected_paths,
            "candidate_bboxes": [],
            "blockers": [
                "Isaac semantic/instance segmentation requires a real Isaac camera capture."
            ],
            "agent_facing": False,
            "no_simulator_label_fallback": True,
            "reason": (
                "Semantic or instance segmentation is not exposed by fake protocol "
                "artifacts and no simulator-label fallback was used."
            ),
        }

    captured = _dict(real_smoke.get("segmentation"))
    output_data_types = [str(item) for item in captured.get("output_data_types", []) if str(item)]
    candidates = [
        dict(candidate)
        for candidate in captured.get("candidate_bboxes", [])
        if isinstance(candidate, dict)
    ][:MAX_SEGMENTATION_CANDIDATES]
    selected_matches = _segmentation_selected_matches(candidates, selected_paths)
    blockers: list[str] = []
    if not output_data_types:
        blockers.append("Isaac camera capture returned no segmentation tensors.")
    if not candidates:
        blockers.append("Isaac segmentation tensors did not produce label-mapped bbox candidates.")
    if selected_paths and not selected_matches:
        blockers.append("Isaac segmentation candidates did not match selected cleanup USD prims.")
    if selected_unrenderable_paths:
        blockers.append(
            "Selected cleanup USD prims have no renderable geometry: "
            + ", ".join(selected_unrenderable_paths[:5])
        )
    if not selected_paths:
        blockers.append("Selected cleanup handles are not bound to USD prim paths.")
    status = "available" if not blockers else "blocked_capability"
    reason = (
        "Isaac camera segmentation tensors produced label-mapped bbox candidates "
        "for selected cleanup USD prims."
        if status == "available"
        else " ".join(blockers)
    )
    return {
        "schema": SEGMENTATION_SCHEMA,
        "available": status == "available",
        "status": status,
        "source": captured.get("source") or "isaac_lab_camera",
        "capture_method": captured.get("capture_method") or "isaac_lab_camera_segmentation",
        "requested_data_types": captured.get("requested_data_types")
        or list(ISAAC_SEGMENTATION_DATA_TYPES),
        "output_data_types": output_data_types,
        "tensor_output_available": bool(output_data_types),
        "semantic_filter": captured.get("semantic_filter"),
        "candidate_overlay_status": (
            "available" if status == "available" else "blocked_capability"
        ),
        "candidate_bbox_count": len(candidates),
        "selected_usd_prim_match_count": len(selected_matches),
        "selected_usd_prim_paths": selected_paths,
        "selected_usd_unrenderable_prim_paths": selected_unrenderable_paths,
        "selected_candidate_bboxes": selected_matches[:MAX_SEGMENTATION_CANDIDATES],
        "candidate_bboxes": candidates,
        "view_outputs": captured.get("view_outputs", []),
        "semantic_label_application": _dict(captured.get("semantic_label_application")),
        "blockers": blockers,
        "agent_facing": False,
        "no_simulator_label_fallback": captured.get("no_simulator_label_fallback") is not False,
        "reason": reason,
    }


def _selected_bound_usd_prim_paths(
    scene_binding_diagnostics: dict[str, Any] | None,
) -> list[str]:
    bindings = _dict(scene_binding_diagnostics)
    selected_paths: list[str] = []
    for group_key in ("selected_object_bindings", "selected_target_receptacle_bindings"):
        for binding in _dict(bindings.get(group_key)).values():
            item = _dict(binding)
            if item.get("status") == "bound" and item.get("usd_prim_path"):
                selected_paths.append(str(item["usd_prim_path"]))
    return _dedupe(selected_paths)


def _selected_unrenderable_usd_prim_paths(
    scene_binding_diagnostics: dict[str, Any] | None,
) -> list[str]:
    bindings = _dict(scene_binding_diagnostics)
    selected_paths: list[str] = []
    for group_key in ("selected_object_bindings", "selected_target_receptacle_bindings"):
        for binding in _dict(bindings.get(group_key)).values():
            item = _dict(binding)
            if item.get("status") != "bound":
                continue
            if item.get("has_renderable_geometry") is False and item.get("usd_prim_path"):
                selected_paths.append(str(item["usd_prim_path"]))
    return _dedupe(selected_paths)


def _segmentation_selected_matches(
    candidates: list[dict[str, Any]],
    selected_paths: list[str],
) -> list[dict[str, Any]]:
    selected = set(selected_paths)
    selected_normalized = {_normalize_usd_path(path) for path in selected_paths if path}
    matches: list[dict[str, Any]] = []
    for candidate in candidates:
        prim_path = str(candidate.get("usd_prim_path") or "")
        label = str(candidate.get("label") or "")
        prim_path_normalized = _normalize_usd_path(prim_path)
        label_normalized = _normalize_usd_path(label)
        if (
            prim_path in selected
            or prim_path_normalized in selected_normalized
            or any(path and path in label for path in selected)
            or any(path and path in label_normalized for path in selected_normalized)
        ):
            matches.append(candidate)
    return matches


def _normalize_usd_path(value: str) -> str:
    return str(value or "").strip().casefold()


def mapping_gap_diagnostics(
    *,
    runtime_mode: str,
    map_bundle_dir: Path | None,
    real_smoke: dict[str, Any] | None = None,
    scene_binding_diagnostics: dict[str, Any] | None = None,
    segmentation: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source = "real_isaac_pending" if runtime_mode == "real" else "fake_protocol"
    scene_bindings = _dict(scene_binding_diagnostics)
    segmentation = _dict(segmentation)
    if real_smoke is not None:
        loaded_asset_kind = str(
            real_smoke.get("loaded_asset_kind") or "generated_runtime_smoke_usd"
        )
        scene_index = _dict(real_smoke.get("scene_index_diagnostics"))
        scene_loading_gap = {
            "area": "molmospaces_usd_scene_loading",
            "status": "not_attempted",
            "source": _scene_usd_path(
                str(real_smoke.get("requested_scene_source") or ""),
                int(real_smoke.get("requested_scene_index") or 0),
            ),
            "detail": (
                "The real smoke proves Isaac renderer/USD plumbing only; loading "
                "the MolmoSpaces USD shard remains a Phase B blocker."
            ),
        }
        if loaded_asset_kind == "local_scene_usd":
            scene_loading_gap = {
                "area": "local_usd_scene_loading",
                "status": "loaded",
                "source": str(real_smoke["scene_usd"]),
                "detail": (
                    "The worker loaded the caller-supplied USD stage. Use a "
                    "MolmoSpaces USD here for Phase B parity evidence."
                ),
            }
        stage_loading_detail = "Generated local Phase A USD stage loaded through Isaac Sim."
        if loaded_asset_kind == "local_scene_usd":
            stage_loading_detail = "Caller-supplied local USD stage loaded through Isaac Sim."
        robot_view_images = _real_smoke_robot_view_images(real_smoke)
        robot_view_status = (
            "real_rendering_proven"
            if _has_required_robot_view_images(robot_view_images)
            else "blocked_capability"
        )
        robot_view_detail = (
            "FPV, chase, map, and verification images were captured from the loaded USD scene. "
            "They are static Phase B camera evidence; semantic pose edits are not yet rendered "
            "back into Isaac USD state."
            if robot_view_status == "real_rendering_proven"
            else "FPV/chase/map/verify Isaac camera variants are not fully captured yet."
        )
        gaps = [
            {
                "area": "phase_a_usd_stage_loading",
                "status": "loaded",
                "source": str(real_smoke["scene_usd"]),
                "detail": stage_loading_detail,
            },
            scene_loading_gap,
            {
                "area": "usd_prim_index",
                "status": scene_index.get("status", "partial"),
                "source": scene_index.get("source", "usd_stage_traversal"),
                "detail": (
                    f"USD traversal found {scene_index.get('object_candidate_count', 0)} "
                    "object candidates and "
                    f"{scene_index.get('receptacle_candidate_count', 0)} receptacle candidates."
                ),
            },
            {
                "area": "public_scene_bindings",
                "status": scene_bindings.get("status", "unknown"),
                "source": scene_bindings.get("source", "usd_stage_traversal"),
                "detail": (
                    "Selected cleanup USD bindings: "
                    f"{scene_bindings.get('selected_object_bound_count', 0)}/"
                    f"{scene_bindings.get('selected_object_count', 0)} objects and "
                    f"{scene_bindings.get('selected_target_receptacle_bound_count', 0)}/"
                    f"{scene_bindings.get('selected_target_receptacle_count', 0)} target "
                    "receptacles."
                ),
            },
            {
                "area": "camera_capture",
                "status": "real_rendering_proven",
                "source": REAL_SMOKE_CAPTURE_METHOD,
                "detail": "An Isaac Lab RGB camera frame was written as the runtime smoke image.",
            },
            {
                "area": "robot_view_variants",
                "status": robot_view_status,
                "source": REAL_ROBOT_VIEW_CAPTURE_METHOD,
                "detail": robot_view_detail,
            },
            {
                "area": "segmentation",
                "status": segmentation.get("status", "blocked_capability"),
                "source": segmentation.get("source", "isaac_lab_camera"),
                "detail": str(
                    segmentation.get("reason")
                    or "Semantic or instance segmentation masks are not exposed yet."
                ),
            },
            {
                "area": "articulation_and_collision",
                "status": "semantic_pose_only",
                "source": "generated_runtime_smoke_usd",
                "detail": (
                    "Open/place effects are semantic state edits, not physics or planner proof."
                ),
            },
        ]
    else:
        gaps = [
            {
                "area": "usd_stage_loading",
                "status": "blocked_capability" if runtime_mode == "real" else "not_attempted",
                "source": source,
                "detail": "MolmoSpaces USD stage loading has not been proven by this worker.",
            },
            {
                "area": "usd_prim_index",
                "status": "placeholder_mapping",
                "source": source,
                "detail": "Object and receptacle USD prim paths are deterministic placeholders.",
            },
            {
                "area": "public_scene_bindings",
                "status": scene_bindings.get("status", "placeholder_mapping"),
                "source": scene_bindings.get("source", source),
                "detail": (
                    "Selected cleanup object and target-receptacle bindings are "
                    "derived from synthetic scenario fixtures, not real USD prims."
                ),
            },
            {
                "area": "camera_capture",
                "status": "placeholder_visuals",
                "source": source,
                "detail": "FPV, chase, map, and verification images are generated placeholders.",
            },
            {
                "area": "segmentation",
                "status": segmentation.get("status", "blocked_capability"),
                "source": segmentation.get("source", source),
                "detail": str(
                    segmentation.get("reason")
                    or "Semantic or instance segmentation masks are not exposed yet."
                ),
            },
            {
                "area": "articulation_and_collision",
                "status": "semantic_pose_only",
                "source": source,
                "detail": (
                    "Open/place effects are semantic state edits, not physics or planner proof."
                ),
            },
        ]
    if map_bundle_dir is not None:
        map_bundle_detail = (
            "Public map and fixture context still come from the selected Nav2 bundle."
        )
        gaps.append(
            {
                "area": "public_map_source",
                "status": "external_map_bundle",
                "source": str(map_bundle_dir),
                "detail": map_bundle_detail,
            }
        )
    return gaps


def _initial_semantic_pose_state(
    *,
    scenario: CleanupScenario,
    object_index: dict[str, Any],
    receptacle_index: dict[str, Any],
    scene_binding_diagnostics: dict[str, Any] | None,
    initial_receptacle_id: str,
) -> dict[str, Any]:
    state = {
        "scenario": scenario.public_payload(),
        "locations": scenario.object_locations(),
        "containment": {},
        "held_object_id": None,
        "current_receptacle_id": initial_receptacle_id,
        "open_receptacle_ids": [],
        "object_index": object_index,
        "receptacle_index": receptacle_index,
        "scene_binding_diagnostics": scene_binding_diagnostics or {},
        "object_pose_overrides": {},
    }
    return _semantic_pose_state_from_backend_state(state, transform_events=[])


def _initial_semantic_pose_state_from_state(state: dict[str, Any]) -> dict[str, Any]:
    return _semantic_pose_state_from_backend_state(state, transform_events=[])


def _semantic_pose_state_from_backend_state(
    state: dict[str, Any],
    *,
    transform_events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
        "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "rendered_to_usd": False,
        "planner_backed": False,
        "physical_robot": False,
        "semantic_pose_only": True,
        "robot_pose": _robot_pose_for_receptacle(
            state,
            str(state.get("current_receptacle_id") or ""),
        ),
        "held_object_id": state.get("held_object_id"),
        "open_receptacle_ids": sorted(state.get("open_receptacle_ids") or []),
        "object_poses": _semantic_object_poses_from_state(state),
        "articulations": _semantic_articulations_from_state(state),
        "object_pose_overrides": dict(_dict(state.get("object_pose_overrides"))),
        "transform_events": transform_events,
        "evidence_note": (
            "Semantic cleanup primitives update backend JSON pose/articulation state "
            "against public USD prim handles. These edits are not rendered back into "
            "the Isaac USD stage and are not planner-backed manipulation proof."
        ),
    }


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
    semantic_pose_state = _dict(state.get("semantic_pose_state"))
    events = [
        dict(item)
        for item in semantic_pose_state.get("transform_events", [])
        if isinstance(item, dict)
    ]
    event = {
        "schema": ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
        "sequence": len(events) + 1,
        "tool": tool,
        "state_mutation": state_mutation,
        "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "rendered_to_usd": False,
        "planner_backed": False,
        "physical_robot": False,
        "object_id": object_id,
        "object_usd_prim_path": _object_usd_prim_path(state, object_id),
        "receptacle_id": receptacle_id,
        "receptacle_usd_prim_path": _receptacle_usd_prim_path(state, receptacle_id),
        "previous_location_id": previous_location_id,
        "location_id": location_id,
        "location_relation": relation,
        "robot_pose": _robot_pose_for_receptacle(
            state,
            str(state.get("current_receptacle_id") or receptacle_id),
        ),
    }
    event.update({key: value for key, value in extra.items() if value is not None})
    events.append(event)
    semantic_pose_state.update(
        {
            "schema": ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
            "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
            "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
            "rendered_to_usd": False,
            "planner_backed": False,
            "physical_robot": False,
            "semantic_pose_only": True,
            "robot_pose": _robot_pose_for_receptacle(
                state,
                str(state.get("current_receptacle_id") or receptacle_id),
            ),
            "held_object_id": state.get("held_object_id"),
            "open_receptacle_ids": sorted(state.get("open_receptacle_ids") or []),
            "object_poses": _semantic_object_poses_from_state(state),
            "articulations": _semantic_articulations_from_state(state),
            "object_pose_overrides": dict(_dict(state.get("object_pose_overrides"))),
            "transform_events": events,
            "evidence_note": (
                "Semantic cleanup primitives update backend JSON pose/articulation state "
                "against public USD prim handles. These edits are not rendered back into "
                "the Isaac USD stage and are not planner-backed manipulation proof."
            ),
        }
    )
    state["semantic_pose_state"] = semantic_pose_state
    return event


def _seed_generated_mess_placements(state: dict[str, Any]) -> None:
    targets = [_dict(item) for item in _dict(state.get("private_manifest")).get("targets", [])]
    if not targets:
        return
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
        wrong = wrong_pool[index % len(wrong_pool)]
        if len(wrong_pool) > 1 and str(wrong.get("receptacle_id") or "") in target_ids:
            wrong = wrong_pool[(index + 1) % len(wrong_pool)]
        receptacle_id = str(wrong.get("receptacle_id") or "")
        if not receptacle_id:
            continue
        relation = "inside" if _receptacle_prefers_inside(wrong) else "on"
        placement_resolution = _apply_object_location(
            state,
            object_id=object_id,
            receptacle_id=receptacle_id,
            relation=relation,
            placement_index=index,
            source="mess_seed",
        )
        diagnostic = _isaac_placement_diagnostic(
            state=state,
            object_id=object_id,
            receptacle_id=receptacle_id,
            relation=relation,
            source="mess_seed",
            placement_resolution=placement_resolution,
        )
        diagnostics.append(diagnostic)
    state["mess_placement_diagnostics"] = diagnostics


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


def _resolve_isaac_placement(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
    source: str,
) -> dict[str, Any]:
    if relation == "on":
        direct = _isaac_direct_support_placement(
            state,
            object_id=object_id,
            receptacle_id=receptacle_id,
            index=index,
        )
        if direct is not None:
            direct["source"] = source
            return direct
    position = _isaac_fallback_placement_position(
        state,
        object_id=object_id,
        receptacle_id=receptacle_id,
        index=index,
        relation=relation,
    )
    support_status = (
        "semantic_contained_in_receptacle" if relation == "inside" else "degraded_elevated"
    )
    contact_proof = (
        "semantic_containment" if relation == "inside" else "degraded_no_direct_support_surface"
    )
    return {
        "position": position,
        "support_status": support_status,
        "contact_proof": contact_proof,
        "resolution_source": "isaac_category_fallback",
        "candidate_count": 0,
        "degraded": relation == "on",
        "source": source,
    }


def _isaac_state_objects_for_clearance(state: dict[str, Any]) -> dict[str, dict[str, Any]]:
    objects = dict(_objects_by_id(state))
    for object_id, entry in _dict(state.get("object_index")).items():
        object_id = str(object_id)
        if object_id in objects:
            continue
        item = _dict(entry)
        if not item:
            continue
        objects[object_id] = {
            "object_id": object_id,
            "category": str(item.get("category") or ""),
            "name": str(item.get("public_label") or object_id),
            "location_id": str(item.get("parent") or ""),
            "pickupable": True,
        }
    return objects


def _isaac_direct_support_placement(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
) -> dict[str, Any] | None:
    surfaces = _isaac_receptacle_support_surfaces(state, receptacle_id)
    if not surfaces:
        return None
    footprint = _isaac_object_footprint_half_extents(state, object_id)
    bottom_offset = _isaac_object_bottom_offset(state, object_id)
    clearance = _isaac_direct_support_clearance(
        _dict(_objects_by_id(state).get(object_id)),
        _dict(_receptacles_by_id(state).get(receptacle_id)),
    )
    candidate_count = 0
    for surface in sorted(
        surfaces,
        key=lambda item: (
            float(item.get("area_m2") or 0.0),
            float(item.get("top_z") or 0.0),
        ),
        reverse=True,
    ):
        for candidate in _surface_candidate_positions(
            surface,
            footprint=footprint,
            bottom_offset=bottom_offset,
            clearance=clearance,
            index=index,
        ):
            candidate_count += 1
            if not _candidate_has_direct_support(candidate, surface, footprint):
                continue
            if not _isaac_candidate_is_clear_of_dynamic_objects(
                state,
                object_id=object_id,
                position=candidate,
                footprint=footprint,
                bottom_offset=bottom_offset,
            ):
                continue
            return {
                "position": candidate,
                "support_status": "direct_support",
                "contact_proof": "usd_bounds_direct_support",
                "resolution_source": "isaac_support_surface",
                "candidate_count": candidate_count,
                "degraded": False,
                "support_surface": surface,
                "object_bottom_offset_m": round(float(bottom_offset), 6),
                "support_clearance_m": round(float(clearance), 6),
                "object_footprint_half_extents_m": [
                    round(float(footprint[0]), 6),
                    round(float(footprint[1]), 6),
                ],
            }
    surface = surfaces[0]
    return {
        "position": _elevated_position_over_surface(surface, bottom_offset=bottom_offset),
        "support_status": "degraded_elevated",
        "contact_proof": "degraded_no_candidate_inside_support_surface",
        "resolution_source": "isaac_support_surface_elevated_fallback",
        "candidate_count": candidate_count,
        "degraded": True,
        "support_surface": surface,
        "object_bottom_offset_m": round(float(bottom_offset), 6),
        "support_clearance_m": round(float(clearance), 6),
        "object_footprint_half_extents_m": [
            round(float(footprint[0]), 6),
            round(float(footprint[1]), 6),
        ],
    }


def _isaac_receptacle_support_surface(
    state: dict[str, Any],
    receptacle_id: str,
) -> dict[str, Any] | None:
    surfaces = _isaac_receptacle_support_surfaces(state, receptacle_id)
    return surfaces[0] if surfaces else None


def _isaac_receptacle_support_surfaces(
    state: dict[str, Any],
    receptacle_id: str,
) -> list[dict[str, Any]]:
    entry = _isaac_index_entry(
        state,
        receptacle_id,
        index_name="receptacle_index",
        binding_groups=("selected_target_receptacle_bindings", "receptacle_bindings"),
    )
    surfaces = []
    for surface in entry.get("support_surfaces") or []:
        normalized = _normalize_support_surface(surface)
        if normalized is not None:
            surfaces.append(normalized)
    if surfaces:
        return sorted(
            surfaces,
            key=lambda item: (
                float(item.get("area_m2") or 0.0),
                float(item.get("top_z") or 0.0),
            ),
            reverse=True,
        )
    surface = _support_surface_from_usd_bounds(
        bounds=_dict(entry.get("usd_world_bounds")),
        surface_id=_receptacle_usd_prim_path(state, receptacle_id) or receptacle_id,
        source=ISAAC_WORLD_BOUNDS_SUPPORT_SURFACE_SOURCE,
    )
    if surface is not None:
        return [surface]
    support_pose = _receptacle_support_pose(state, receptacle_id)
    center = _support_pose_position(support_pose)
    radius = float(support_pose.get("support_radius_m") or 0.0) if support_pose else 0.0
    if center is None or radius <= 0.0:
        return []
    area = 4.0 * radius * radius
    return [
        {
            "surface_id": _receptacle_usd_prim_path(state, receptacle_id) or receptacle_id,
            "center": [round(float(center[0]), 6), round(float(center[1]), 6)],
            "top_z": round(float(center[2]), 6),
            "half_extents": [round(float(radius), 6), round(float(radius), 6)],
            "area_m2": round(float(area), 6),
            "source": str(support_pose.get("source") or "isaac_support_pose"),
        }
    ]


def _normalize_support_surface(surface: Any) -> dict[str, Any] | None:
    raw = _dict(surface)
    center = raw.get("center")
    half_extents = raw.get("half_extents")
    if not isinstance(center, (list, tuple)) or len(center) < 2:
        return None
    if not isinstance(half_extents, (list, tuple)) or len(half_extents) < 2:
        return None
    try:
        center_xy = [round(float(center[0]), 6), round(float(center[1]), 6)]
        top_z = round(float(raw["top_z"]), 6)
        half_xy = [
            round(abs(float(half_extents[0])), 6),
            round(abs(float(half_extents[1])), 6),
        ]
    except (KeyError, TypeError, ValueError):
        return None
    if min(half_xy) < 0.03:
        return None
    area = float(raw.get("area_m2") or (4.0 * half_xy[0] * half_xy[1]))
    if area <= 0.0:
        return None
    normalized = {
        "surface_id": str(raw.get("surface_id") or ""),
        "center": center_xy,
        "top_z": top_z,
        "half_extents": half_xy,
        "area_m2": round(area, 6),
        "source": str(raw.get("source") or ISAAC_DESCENDANT_SUPPORT_SURFACE_SOURCE),
    }
    if raw.get("selection_score") is not None:
        try:
            normalized["selection_score"] = round(float(raw["selection_score"]), 6)
        except (TypeError, ValueError):
            pass
    return normalized


def _surface_candidate_positions(
    surface: dict[str, Any],
    *,
    footprint: tuple[float, float],
    bottom_offset: float,
    clearance: float,
    index: int,
) -> list[list[float]]:
    center = surface["center"]
    half_extents = surface["half_extents"]
    margin_x = float(footprint[0]) + 0.04
    margin_y = float(footprint[1]) + 0.04
    available_x = max(float(half_extents[0]) - margin_x, 0.0)
    available_y = max(float(half_extents[1]) - margin_y, 0.0)
    slot_x = min(available_x * 0.55, 0.28)
    slot_y = min(available_y * 0.55, 0.28)
    offsets = [
        (0.0, 0.0),
        (-slot_x, 0.0),
        (slot_x, 0.0),
        (0.0, -slot_y),
        (0.0, slot_y),
        (-slot_x, -slot_y),
        (slot_x, -slot_y),
        (-slot_x, slot_y),
        (slot_x, slot_y),
    ]
    if len(offsets) > 1:
        shift = index % len(offsets)
        offsets = offsets[shift:] + offsets[:shift]
    z = float(surface["top_z"]) + float(bottom_offset) + float(clearance)
    return [
        [
            round(float(center[0]) + float(dx), 6),
            round(float(center[1]) + float(dy), 6),
            round(z, 6),
        ]
        for dx, dy in offsets
    ]


def _candidate_has_direct_support(
    position: list[float],
    surface: dict[str, Any],
    footprint: tuple[float, float],
) -> bool:
    center = surface["center"]
    half_extents = surface["half_extents"]
    margin_x = float(footprint[0]) + 0.015
    margin_y = float(footprint[1]) + 0.015
    return abs(float(position[0]) - float(center[0])) + margin_x <= float(half_extents[0]) and abs(
        float(position[1]) - float(center[1])
    ) + margin_y <= float(half_extents[1])


def _isaac_candidate_is_clear_of_dynamic_objects(
    state: dict[str, Any],
    *,
    object_id: str,
    position: list[float],
    footprint: tuple[float, float],
    bottom_offset: float,
) -> bool:
    candidate_bottom = float(position[2]) - float(bottom_offset)
    candidate_height = max(_isaac_object_height(state, object_id), 0.04)
    candidate_top = candidate_bottom + candidate_height
    candidate_aabb = {
        "min_x": float(position[0]) - float(footprint[0]),
        "max_x": float(position[0]) + float(footprint[0]),
        "min_y": float(position[1]) - float(footprint[1]),
        "max_y": float(position[1]) + float(footprint[1]),
        "min_z": candidate_bottom,
        "max_z": candidate_top,
    }
    for other_id in _isaac_state_objects_for_clearance(state):
        if other_id == object_id:
            continue
        if _dict(state.get("locations")).get(other_id) == HELD_LOCATION_ID:
            continue
        other_aabb = _isaac_object_current_aabb(state, other_id)
        if other_aabb is None:
            continue
        if not _aabb_xy_overlaps(
            (
                candidate_aabb["min_x"],
                candidate_aabb["max_x"],
                candidate_aabb["min_y"],
                candidate_aabb["max_y"],
            ),
            other_aabb,
            margin=0.025,
        ):
            continue
        if (
            candidate_bottom - 0.015 <= other_aabb["max_z"]
            and candidate_top + 0.015 >= other_aabb["min_z"]
        ):
            return False
    return True


def _aabb_xy_overlaps(
    first: tuple[float, float, float, float],
    second: dict[str, float],
    *,
    margin: float,
) -> bool:
    min_x, max_x, min_y, max_y = first
    return (
        min_x - margin <= float(second["max_x"])
        and max_x + margin >= float(second["min_x"])
        and min_y - margin <= float(second["max_y"])
        and max_y + margin >= float(second["min_y"])
    )


def _isaac_object_current_aabb(state: dict[str, Any], object_id: str) -> dict[str, float] | None:
    bounds = _isaac_object_world_bounds(state, object_id)
    size = _vec3(_dict(bounds).get("size"))
    center = _vec3(_dict(bounds).get("center"))
    if center is None or size is None:
        return None
    override = _dict(_dict(state.get("object_pose_overrides")).get(object_id))
    override_position = _vec3(override.get("position"))
    if override_position is not None:
        center = override_position
    half_x = max(abs(float(size[0])) / 2.0, 0.025)
    half_y = max(abs(float(size[1])) / 2.0, 0.025)
    half_z = max(abs(float(size[2])) / 2.0, 0.02)
    return {
        "min_x": float(center[0]) - half_x,
        "max_x": float(center[0]) + half_x,
        "min_y": float(center[1]) - half_y,
        "max_y": float(center[1]) + half_y,
        "min_z": float(center[2]) - half_z,
        "max_z": float(center[2]) + half_z,
    }


def _elevated_position_over_surface(
    surface: dict[str, Any],
    *,
    bottom_offset: float,
) -> list[float]:
    center = surface["center"]
    return [
        round(float(center[0]), 6),
        round(float(center[1]), 6),
        round(float(surface["top_z"]) + float(bottom_offset) + 0.08, 6),
    ]


def _isaac_fallback_placement_position(
    state: dict[str, Any],
    *,
    object_id: str,
    receptacle_id: str,
    index: int,
    relation: str,
) -> list[float]:
    receptacle = _dict(_receptacles_by_id(state).get(receptacle_id))
    support = _receptacle_support_pose(state, receptacle_id)
    base = _support_pose_position(support)
    if base is None:
        base = _vec3(_dict(_isaac_receptacle_world_bounds(state, receptacle_id)).get("center"))
    if base is None:
        pose = _pose_near(receptacle_id)
        base = [float(pose["x"]), float(pose["y"]), float(pose.get("z", 0.0))]
    text = _receptacle_text(receptacle)
    if relation == "inside" and ("fridge" in text or "refrigerator" in text):
        return _round_vec3([base[0] + 0.08, base[1] - 0.16, base[2] + 0.35])
    offset = ((index % 3) - 1) * 0.12
    y_offset = 0.08 * (index % 2)
    category = str(_dict(_objects_by_id(state).get(object_id)).get("category") or "")
    if _norm(category) in {"apple", "food"}:
        y_offset = 0.16
    return _round_vec3([base[0] + offset, base[1] + y_offset, base[2] + 0.18])


def _isaac_object_footprint_half_extents(
    state: dict[str, Any],
    object_id: str,
) -> tuple[float, float]:
    size = _vec3(_dict(_isaac_object_world_bounds(state, object_id)).get("size"))
    if size is not None:
        return (max(abs(float(size[0])) / 2.0, 0.025), max(abs(float(size[1])) / 2.0, 0.025))
    category = _norm(_dict(_objects_by_id(state).get(object_id)).get("category"))
    if category in {"remotecontrol", "remote", "electronics"}:
        return (0.09, 0.045)
    if category in {"plate", "dish"}:
        return (0.13, 0.13)
    if category in {"apple", "potato", "food"}:
        return (0.065, 0.065)
    if category == "book":
        return (0.12, 0.08)
    if category == "pillow":
        return (0.22, 0.16)
    return (0.08, 0.08)


def _isaac_object_bottom_offset(state: dict[str, Any], object_id: str) -> float:
    bounds = _dict(_isaac_object_world_bounds(state, object_id))
    center = _vec3(bounds.get("center"))
    min_point = _vec3(bounds.get("min"))
    if center is not None and min_point is not None:
        offset = float(center[2]) - float(min_point[2])
        if 0.0 < offset <= 1.0:
            return max(offset, 0.01)
    return _isaac_object_surface_lift(_dict(_objects_by_id(state).get(object_id)).get("category"))


def _isaac_object_height(state: dict[str, Any], object_id: str) -> float:
    size = _vec3(_dict(_isaac_object_world_bounds(state, object_id)).get("size"))
    if size is not None:
        return max(abs(float(size[2])), 0.01)
    return _isaac_object_surface_lift(_dict(_objects_by_id(state).get(object_id)).get("category"))


def _isaac_object_surface_lift(category: Any) -> float:
    normalized = _norm(category)
    if normalized in {"book", "plate", "remotecontrol", "remote", "electronics"}:
        return 0.04
    if normalized in {"apple", "potato", "food"}:
        return 0.08
    if normalized == "pillow":
        return 0.12
    return 0.06


def _isaac_direct_support_clearance(
    obj: dict[str, Any],
    receptacle: dict[str, Any],
) -> float:
    receptacle_text = _receptacle_text(receptacle)
    object_category = _norm(obj.get("category"))
    if "bed" in receptacle_text or "sofa" in receptacle_text:
        return 0.035
    if object_category in {"book", "plate", "remotecontrol", "remote", "electronics"}:
        return 0.02
    return 0.015


def _isaac_object_world_bounds(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    return _dict(
        _isaac_index_entry(
            state,
            object_id,
            index_name="object_index",
            binding_groups=("selected_object_bindings", "object_bindings"),
        ).get("usd_world_bounds")
    )


def _isaac_receptacle_world_bounds(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    return _dict(
        _isaac_index_entry(
            state,
            receptacle_id,
            index_name="receptacle_index",
            binding_groups=("selected_target_receptacle_bindings", "receptacle_bindings"),
        ).get("usd_world_bounds")
    )


def _isaac_index_entry(
    state: dict[str, Any],
    public_id: str,
    *,
    index_name: str,
    binding_groups: tuple[str, ...],
) -> dict[str, Any]:
    binding = _binding_for_handle(state.get("scene_binding_diagnostics"), public_id, binding_groups)
    index = _dict(state.get(index_name))
    for handle in (binding.get("usd_handle"), public_id):
        entry = _dict(index.get(str(handle)))
        if entry:
            return entry
    return {}


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
    placement_resolution: dict[str, Any] | None = None,
) -> dict[str, Any]:
    obj = _dict(_objects_by_id(state).get(object_id))
    receptacle = _dict(_receptacles_by_id(state).get(receptacle_id))
    placement_resolution = placement_resolution or {}
    requested_position = _vec3(placement_resolution.get("position")) or []
    object_position = requested_position or _semantic_object_position_from_state(
        state,
        object_id=object_id,
        location_id=str(_dict(state.get("locations")).get(object_id) or ""),
        original_location_id=str(obj.get("location_id") or ""),
        support_receptacle_id=receptacle_id,
    )
    if object_position is None:
        object_position = []
    receptacle_position = _support_pose_position(_receptacle_support_pose(state, receptacle_id))
    if receptacle_position is None:
        receptacle_position = _vec3(
            _dict(_isaac_receptacle_world_bounds(state, receptacle_id)).get("center")
        )
    if receptacle_position is None:
        receptacle_position = []
    xy_distance = (
        math.dist(object_position[:2], receptacle_position[:2])
        if len(object_position) >= 2 and len(receptacle_position) >= 2
        else None
    )
    z_delta = (
        float(object_position[2]) - float(receptacle_position[2])
        if len(object_position) >= 3 and len(receptacle_position) >= 3
        else None
    )
    default_support_status = (
        "semantic_contained_in_receptacle" if relation == "inside" else "semantic_on_receptacle"
    )
    support_status = str(placement_resolution.get("support_status") or default_support_status)
    diagnostic = {
        "schema": PLACEMENT_DIAGNOSTIC_SCHEMA,
        "status": support_status,
        "object_id": object_id,
        "object_category": obj.get("category"),
        "object_usd_prim_path": _object_usd_prim_path(state, object_id),
        "receptacle_id": receptacle_id,
        "receptacle_category": receptacle.get("category") or receptacle.get("kind"),
        "receptacle_usd_prim_path": _receptacle_usd_prim_path(state, receptacle_id),
        "relation": relation,
        "requested_position": _round_vec3(requested_position) if requested_position else [],
        "object_position": _round_vec3(object_position) if object_position else [],
        "receptacle_position": _round_vec3(receptacle_position) if receptacle_position else [],
        "xy_distance_m": round(float(xy_distance), 6) if xy_distance is not None else None,
        "z_delta_m": round(float(z_delta), 6) if z_delta is not None else None,
        "support_status": support_status,
        "placement_support_status": support_status,
        "direct_support_proven": support_status == "direct_support",
        "contact_proof": str(
            placement_resolution.get("contact_proof") or "not_measured_isaac_semantic_pose"
        ),
        "diagnostic_source": source,
        "resolution_source": placement_resolution.get("resolution_source", "isaac_semantic"),
        "candidate_count": int(placement_resolution.get("candidate_count") or 0),
        "degraded": bool(placement_resolution.get("degraded", False)),
        "state_mutation": "isaac_prim_transform",
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "planner_backed": False,
        "physical_robot": False,
    }
    support_surface = placement_resolution.get("support_surface")
    if isinstance(support_surface, dict):
        diagnostic["support_surface_id"] = support_surface.get("surface_id")
        diagnostic["support_surface_center"] = support_surface.get("center")
        diagnostic["support_surface_half_extents"] = support_surface.get("half_extents")
        diagnostic["support_surface_top_z"] = support_surface.get("top_z")
        diagnostic["support_surface_source"] = support_surface.get("source")
        if support_surface.get("member_count") is not None:
            diagnostic["support_surface_member_count"] = support_surface.get("member_count")
    for key in (
        "object_bottom_offset_m",
        "support_clearance_m",
        "object_footprint_half_extents_m",
    ):
        if placement_resolution.get(key) is not None:
            diagnostic[key] = placement_resolution[key]
    return diagnostic


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
        focus=focus,
        views={key: str(path) for key, path in views.items()},
        shapes=shapes,
        render_resolution={"width": args.render_width, "height": args.render_height},
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
        )
        contract.update(
            {
                "semantic_pose_state_refreshed": semantic_pose_state_refreshed,
                "evidence_note": (
                    "Isaac cleanup FPV uses the imported RBY1M mounted head camera "
                    "when the robot USD import artifact is present. Without that "
                    "artifact it remains explicitly marked as head-camera-equivalent. "
                    "Chase/map views remain auxiliary report evidence."
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
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
) -> dict[str, str]:
    runtime = _dict(state.get("runtime"))
    scene_usd = str(state.get("scene_usd") or "")
    if runtime.get("runtime_mode") != "real" or not scene_usd or not Path(scene_usd).is_file():
        return {}
    try:
        capture = capture_semantic_pose_robot_views(
            state=state,
            scene_usd=Path(scene_usd),
            view_paths=target_images,
            width=width,
            height=height,
            focus_object_id=focus_object_id,
            focus_receptacle_id=focus_receptacle_id,
        )
    except Exception as exc:
        state.setdefault("mapping_gaps", []).append(
            {
                "area": "semantic_pose_robot_view_rerender",
                "status": "blocked_capability",
                "source": scene_usd,
                "detail": str(exc),
            }
        )
        write_state_from_state_arg(state)
        return {}
    images = {
        key: str(value)
        for key, value in _dict(capture.get("robot_view_images")).items()
        if key in ROBOT_VIEW_KEYS and value
    }
    if not _has_required_robot_view_images(images):
        return {}
    mounted_head_camera = bool(capture.get("robot_view_uses_mounted_head_camera"))
    state["robot_view_images"] = images
    state["robot_view_provenance"] = _semantic_pose_robot_view_provenance(
        mounted_head_camera=mounted_head_camera,
        head_camera_equivalent=not mounted_head_camera,
    )
    state["semantic_pose_view_capture"] = {
        "schema": "isaac_semantic_pose_robot_view_capture_v1",
        "capture_method": REAL_ROBOT_VIEW_RERENDER_METHOD,
        "scene_usd": scene_usd,
        "rendered_to_usd": True,
        "render_steps": int(capture.get("render_steps") or 0),
        "canonical_camera_control": False,
        "robot_mounted_head_camera": mounted_head_camera,
        "head_camera_equivalent": not mounted_head_camera,
        "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM if mounted_head_camera else "",
        "robot_stage": _dict(capture.get("robot_stage")),
        "robot_pose_stage_application": _dict(capture.get("robot_pose_stage_application")),
    }
    state.pop("canonical_robot_view_camera_control_request", None)
    state.pop("canonical_robot_view_camera_control_capture", None)
    mapping_gaps = [
        item
        for item in state.get("mapping_gaps", [])
        if not (isinstance(item, dict) and item.get("area") == "robot_view_variants")
    ]
    mapping_gaps.append(
        {
            "area": "robot_view_variants",
            "status": "real_rendering_proven",
            "source": REAL_ROBOT_VIEW_RERENDER_METHOD,
            "detail": (
                "Robot-view images were recaptured from the loaded USD scene after "
                "applying backend semantic pose state. FPV uses the imported RBY1M "
                "mounted head camera when the robot USD import artifact is present; "
                "otherwise it is explicitly marked as a head-camera equivalent. "
                "Chase/map remain auxiliary report views. This is semantic pose "
                "report evidence, not planner-backed or physics-backed "
                "manipulation proof."
            ),
        }
    )
    state["mapping_gaps"] = mapping_gaps
    semantic_pose_state = _dict(state.get("semantic_pose_state"))
    semantic_pose_state["rendered_to_usd"] = True
    semantic_pose_state["semantic_pose_view_capture"] = dict(state["semantic_pose_view_capture"])
    semantic_pose_state["evidence_note"] = (
        "Semantic cleanup primitives still update backend JSON pose/articulation state "
        "and are not planner-backed manipulation proof. The current report robot-view "
        "images were recaptured from Isaac after applying that semantic pose state to "
        "the loaded USD stage."
    )
    state["semantic_pose_state"] = semantic_pose_state
    write_state_from_state_arg(state)
    return images


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
    images = {
        key: str(value)
        for key, value in _dict(state.get("robot_view_images")).items()
        if key in ROBOT_VIEW_KEYS and value
    }
    if _has_required_robot_view_images(images):
        return images
    return {}


def _real_smoke_robot_view_images(real_smoke: dict[str, Any] | None) -> dict[str, str]:
    if real_smoke is None:
        return {}
    images = {
        key: str(value)
        for key, value in _dict(real_smoke.get("robot_view_images")).items()
        if key in ROBOT_VIEW_KEYS and value
    }
    if not _has_required_robot_view_images(images):
        return {}
    return images if all(Path(value).is_file() for value in images.values()) else {}


def _has_required_robot_view_images(images: dict[str, str]) -> bool:
    return all(bool(images.get(key)) for key in ROBOT_VIEW_KEYS)


def _copy_real_robot_view_images(
    source_images: dict[str, str],
    target_images: dict[str, Path],
    *,
    width: int,
    height: int,
) -> dict[str, list[int]]:
    shapes: dict[str, list[int]] = {}
    for key in ROBOT_VIEW_KEYS:
        source = Path(source_images[key])
        target = target_images[key]
        shapes[key] = _copy_nonblank_rgb_image(
            source,
            target,
            width=width,
            height=height,
            description=f"real Isaac {key} view image",
        )
    return shapes


def _real_snapshot_source_image(state: dict[str, Any]) -> Path:
    real_smoke = _dict(state.get("real_runtime_smoke"))
    image_path = str(real_smoke.get("image_path") or "")
    if image_path:
        return Path(image_path)
    robot_views = _real_robot_view_images(state)
    fpv_path = str(robot_views.get("fpv") or "")
    if fpv_path:
        return Path(fpv_path)
    raise RuntimeError("real Isaac rendering is proven, but no RGB snapshot source is recorded")


def _copy_real_snapshot_image(
    source: Path,
    target: Path,
    *,
    width: int,
    height: int,
) -> list[int]:
    return _copy_nonblank_rgb_image(
        source,
        target,
        width=width,
        height=height,
        description="real Isaac snapshot source image",
    )


def _copy_nonblank_rgb_image(
    source: Path,
    target: Path,
    *,
    width: int,
    height: int,
    description: str,
) -> list[int]:
    if not source.is_file():
        raise RuntimeError(f"missing {description}: {source}")
    target.parent.mkdir(parents=True, exist_ok=True)
    same_path = source.resolve() == target.resolve()
    with Image.open(source) as image:
        rgb = image.convert("RGB")
        if not _pil_image_has_variance(rgb):
            raise RuntimeError(f"{description} appears blank: {source}")
        if not same_path and rgb.size != (width, height):
            rgb = rgb.resize((width, height))
        if not same_path:
            rgb.save(target)
        return [rgb.height, rgb.width, 3]


def _pil_image_has_variance(image: Image.Image) -> bool:
    return any(high > low for low, high in image.getextrema())


def _real_rendering_proven(state: dict[str, Any]) -> bool:
    rendering = _dict(_dict(state.get("runtime")).get("rendering"))
    return rendering.get("real_rendering_proven") is True


def _robot_view_provenance(
    runtime_mode: str,
    real_smoke: dict[str, Any] | None,
) -> dict[str, Any]:
    if _has_required_robot_view_images(_real_smoke_robot_view_images(real_smoke)):
        method = str(real_smoke.get("robot_view_capture_method") or REAL_ROBOT_VIEW_CAPTURE_METHOD)
        provenance = {key: f"{method}:{key}" for key in ROBOT_VIEW_KEYS}
        mounted_head_camera = bool(real_smoke.get("robot_view_uses_mounted_head_camera"))
        if mounted_head_camera:
            provenance["fpv"] = "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv"
        else:
            provenance["fpv"] = "isaac_lab_camera_rgb_head_camera_equivalent:fpv"
        provenance["semantic_pose_state_refreshed"] = False
        provenance["canonical_camera_control"] = False
        provenance["robot_mounted_head_camera"] = mounted_head_camera
        provenance["head_camera_equivalent"] = not mounted_head_camera
        provenance["evidence_note"] = (
            "Robot-view images are static captures from the loaded USD scene during init. "
            "FPV uses the imported RBY1M mounted head camera when the robot USD import "
            "artifact is present; otherwise it is marked as a head-camera equivalent. "
            "Semantic pose edits are tracked in backend JSON state and are not rendered "
            "back into Isaac yet."
        )
        return provenance
    if runtime_mode == "real":
        provenance = {key: "isaac_robot_view_capture_pending" for key in ROBOT_VIEW_KEYS}
        provenance.update(
            {
                "semantic_pose_state_refreshed": False,
                "evidence_note": "Real Isaac robot-view captures were not recorded.",
            }
        )
        return provenance
    provenance = {key: "fake_protocol_placeholder_image" for key in ROBOT_VIEW_KEYS}
    provenance.update(
        {
            "semantic_pose_state_refreshed": False,
            "evidence_note": "CI fake mode writes deterministic placeholder robot-view images.",
        }
    )
    return provenance


def _robot_view_command_provenance(
    state: dict[str, Any],
    *,
    semantic_pose_state_refreshed: bool,
) -> dict[str, Any]:
    if semantic_pose_state_refreshed:
        provenance = _dict(state.get("robot_view_provenance"))
        return _semantic_pose_robot_view_provenance(
            mounted_head_camera=bool(
                provenance.get("robot_mounted_head_camera")
                or _dict(state.get("semantic_pose_view_capture")).get("robot_mounted_head_camera")
            ),
            head_camera_equivalent=bool(
                provenance.get("head_camera_equivalent")
                or _dict(state.get("semantic_pose_view_capture")).get("head_camera_equivalent")
            ),
        )
    return _dict(state.get("robot_view_provenance"))


def _semantic_pose_robot_view_provenance(
    *,
    mounted_head_camera: bool = False,
    head_camera_equivalent: bool = False,
) -> dict[str, Any]:
    provenance = {key: f"{REAL_ROBOT_VIEW_RERENDER_METHOD}:{key}" for key in ROBOT_VIEW_KEYS}
    if mounted_head_camera:
        provenance["fpv"] = "isaac_lab_camera_rgb_robot_mounted_head_camera:fpv"
    elif head_camera_equivalent:
        provenance["fpv"] = "isaac_lab_camera_rgb_head_camera_equivalent:fpv"
    provenance["semantic_pose_state_refreshed"] = True
    provenance["canonical_camera_control"] = False
    provenance["robot_mounted_head_camera"] = mounted_head_camera
    provenance["head_camera_equivalent"] = head_camera_equivalent
    provenance["evidence_note"] = (
        "Robot-view images were recaptured from the loaded USD scene after applying "
        "backend semantic pose state. FPV is either the imported RBY1M mounted head "
        "camera or an explicit head-camera-equivalent view; chase/map remain auxiliary report "
        "views. This is still semantic pose rendering, not planner-backed or "
        "physics-backed manipulation."
    )
    return provenance


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


def _scenario_for_init(args: argparse.Namespace) -> CleanupScenario:
    if args.map_bundle_dir is None:
        return _limit_scenario_to_generated_mess_count(
            build_cleanup_scenario(seed=args.seed),
            generated_mess_count=args.generated_mess_count,
        )
    return _limit_scenario_to_generated_mess_count(
        _scenario_from_map_bundle(
            args.map_bundle_dir,
            seed=args.seed,
            generated_mess_count=args.generated_mess_count,
        ),
        generated_mess_count=args.generated_mess_count,
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
    scene_binding_diagnostics: dict[str, Any],
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
    real_smoke: dict[str, Any] | None,
) -> CleanupScenario | None:
    if real_smoke is None or args.scene_usd_path is None:
        return None
    if scene_binding_diagnostics.get("status") == "selected_bound":
        return None
    return _scenario_from_scene_index(
        scene_source=args.scene_source,
        scene_index=args.scene_index,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        generated_mess_object_ids=tuple(getattr(args, "generated_mess_object_id", None) or ()),
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

    selected = select_generated_mess_targets(
        selectable_objects,
        [receptacle.to_public_dict() for receptacle in receptacles],
        target_count=max(1, int(generated_mess_count)),
        seed=seed,
        object_ids=generated_mess_object_ids or None,
    )
    if not selected:
        return None

    objects = tuple(
        CleanupObject(
            object_id=str(item["object_id"]),
            name=str(item["name"]),
            category=str(item["category"]),
            location_id=str(item["location_id"]),
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

    if not targets:
        return None
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
        if any(alias in tokens for alias in category_aliases):
            return _canonical_cleanup_category(category, category_aliases)
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
    ("Pillow", ("pillow", "teddybear", "cushion")),
    ("Towel", ("linen", "towel", "cloth", "blanket", "shirt", "clothing")),
    ("ToyCar", ("toy", "toycar", "ball", "basketball", "soccer")),
)


def _limit_scenario_to_generated_mess_count(
    scenario: CleanupScenario,
    *,
    generated_mess_count: int,
) -> CleanupScenario:
    count = max(1, int(generated_mess_count))
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
    robot_import = _rby1m_robot_import_plan(robot_name)
    imported = robot_import.get("status") == "imported"
    return {
        "robot_name": robot_name,
        "embodiment": "rby1m" if imported else "rby1m_head_camera_equivalent",
        "physical_robot": False,
        "planner_backed": False,
        "robot_import_status": robot_import.get("status") if robot_import else "not_requested",
        "robot_usd_path": robot_import.get("usd_path") if robot_import else "",
        "head_camera_prim_path": robot_import.get("head_camera_prim_path") if robot_import else "",
        "robot_mounted_head_camera": imported,
    }


def _rby1m_robot_import_plan(robot_name: str) -> dict[str, Any]:
    if robot_name not in {"rby1m", "rby1"}:
        return {
            "schema": ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA,
            "robot_name": robot_name,
            "status": "unsupported_robot",
            "head_camera_prim_path": "",
            "blockers": [f"unsupported Isaac robot import target: {robot_name}"],
        }
    urdf = _find_rby1m_isaac_urdf()
    usd_path = _repo_path(ISAAC_RBY1M_ROBOT_USD_PATH)
    summary_path = _repo_path(ISAAC_RBY1M_ROBOT_IMPORT_SUMMARY_PATH)
    summary = _load_json_if_file(summary_path)
    summary_ready = summary.get("schema") == "isaac_rby1m_robot_usd_import_v1" and (
        summary.get("status") == "ready"
    )
    imported = usd_path.is_file() and summary_ready
    blockers: list[str] = []
    if not urdf:
        blockers.append("RBY1M Isaac URDF not found in MolmoSpaces asset cache.")
    if not imported:
        if not usd_path.is_file():
            blockers.append(f"RBY1M Isaac robot USD import artifact is missing: {usd_path}")
        if not summary_ready:
            blockers.append(f"RBY1M Isaac robot import summary is not ready: {summary_path}")
    return {
        "schema": ISAAC_RBY1M_ROBOT_IMPORT_SCHEMA,
        "robot_name": robot_name,
        "status": "imported"
        if imported
        else ("pending_usd_conversion" if urdf else "missing_urdf"),
        "physical_robot": False,
        "importer": "isaacsim.asset.importer.urdf",
        "source_urdf": str(urdf) if urdf else "",
        "expected_usd_path": str(usd_path),
        "usd_path": str(usd_path) if imported else "",
        "import_summary_path": str(summary_path),
        "stage_prim_path": "/World/robot_0",
        "head_link_name": "link_head_2",
        "head_camera_prim_path": ISAAC_RBY1M_HEAD_CAMERA_PRIM,
        "head_camera_source": "rby1m_mujoco_robot_0/head_camera_extrinsics_and_fov",
        "head_camera_mounted": imported,
        "head_camera_equivalent": not imported,
        "required_joints": ["base_x", "base_y", "base_theta", "head_0", "head_1"],
        "blockers": blockers,
        "import_summary": summary if summary_ready else {},
        "evidence_note": (
            "Isaac imports the RBY1M holobase URDF to USD, references it at "
            "/World/robot_0, and uses a head_camera prim authored from the MuJoCo "
            "robot_0/head_camera extrinsics/FOV. If the import artifact is absent, "
            "Isaac FPV is reported as a head-camera-equivalent view instead of a "
            "robot-mounted camera."
        ),
    }


def _repo_path(path: Path) -> Path:
    return Path(__file__).resolve().parents[2] / path


def _load_json_if_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _find_rby1m_isaac_urdf() -> Path | None:
    candidates: list[Path] = []
    env_root = os.environ.get("MLSPACES_ASSETS_DIR")
    if env_root:
        candidates.append(
            Path(env_root).expanduser()
            / "robots"
            / "rby1m"
            / "curobo_config"
            / "urdf"
            / "model_holobase_isaac"
            / "model_holobase_isaac.urdf"
        )
    candidates.extend(
        Path("/home/mi/.cache/molmospaces/assets").glob(
            "*/robots/rby1m/curobo_config/urdf/model_holobase_isaac/model_holobase_isaac.urdf"
        )
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def _scene_usd_path(scene_source: str, scene_index: int) -> str:
    return f"molmospaces://{scene_source}/scene-{scene_index}.usd"


if __name__ == "__main__":
    raise SystemExit(main())

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
from roboclaws.molmo_cleanup.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_EVENT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
)
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
MAX_SEGMENTATION_CANDIDATES = 24
REAL_SMOKE_CAPTURE_METHOD = "isaac_lab_camera_rgb"
REAL_ROBOT_VIEW_CAPTURE_METHOD = "isaac_lab_camera_rgb_static_robot_views"
REAL_SMOKE_RENDERER_MODE = "isaac_lab_headless_rtx"
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
    init.add_argument("--robot-name", default="simple_camera_rig")
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
        print(json.dumps(result, sort_keys=True), flush=True)
        _close_deferred_simulation_app()
        return 0
    else:
        state = read_state(args.state_path)
        if args.command == "locations":
            result = {"ok": True, "tool": "locations", "final_locations": state["locations"]}
        elif args.command == "snapshot":
            result = write_snapshot(args, state)
        elif args.command == "robot_views":
            result = write_robot_views(args, state)
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
    print(json.dumps(result, sort_keys=True), flush=True)
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
        "tool_event_counts": {},
        "placement_diagnostics": [],
        "semantic_pose_state": _initial_semantic_pose_state(
            scenario=scenario,
            object_index=object_index,
            receptacle_index=receptacle_index,
            scene_binding_diagnostics=scene_binding_diagnostics,
            initial_receptacle_id=initial_receptacle_id,
        ),
        "mapping_gaps": mapping_gaps,
        "object_index": object_index,
        "receptacle_index": receptacle_index,
        "scene_index_diagnostics": scene_index_diagnostics,
        "scene_binding_diagnostics": scene_binding_diagnostics,
        "robot_view_images": _real_smoke_robot_view_images(real_smoke),
        "robot_view_provenance": _robot_view_provenance(args.runtime_mode, real_smoke),
        "segmentation": segmentation,
        "robot": _robot_payload(args.robot_name) if args.include_robot else None,
    }
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
        include_segmentation=args.enable_segmentation,
        segmentation_data_types=tuple(args.segmentation_data_type or ISAAC_SEGMENTATION_DATA_TYPES),
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
        "camera_resolution": [DEFAULT_WIDTH, DEFAULT_HEIGHT],
        "scene_bounds": capture.get("scene_bounds"),
        "stage_prim_count": stage_prim_count,
        "render_steps": render_steps,
        "scene_index_diagnostics": scene_index_diagnostics,
        "object_index": scene_index_diagnostics["object_index"],
        "receptacle_index": scene_index_diagnostics["receptacle_index"],
        "segmentation": segmentation,
    }


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
    prim_paths_by_name: dict[str, list[str]] = {}
    stage_prim_count = 0
    for prim in stage.Traverse():
        stage_prim_count += 1
        prim_path = str(prim.GetPath())
        prim_paths_by_name.setdefault(prim.GetName(), []).append(prim_path)
        handle = _usd_handle_from_prim(prim_path, object_index, receptacle_index)
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
    }


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
        "parent": str(metadata.get("parent") or ""),
        "is_static": bool(metadata.get("is_static")),
    }


def _is_molmospaces_object_metadata(metadata: dict[str, Any]) -> bool:
    return metadata.get("is_static") is False


def _is_molmospaces_receptacle_metadata(metadata: dict[str, Any]) -> bool:
    category = _norm(metadata.get("category"))
    if not category:
        return False
    if category in _MOLMOSPACES_RECEPTACLE_CATEGORY_NORMS:
        return True
    return bool(metadata.get("children")) and metadata.get("is_static") is True


_MOLMOSPACES_RECEPTACLE_CATEGORY_NORMS = {
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
    include_segmentation: bool = False,
    segmentation_data_types: tuple[str, ...] = ISAAC_SEGMENTATION_DATA_TYPES,
    scene_index_diagnostics: dict[str, Any] | None = None,
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
    semantic_filter = ["class"] if include_segmentation else "*:*"
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(device=device))
    sim_utils.create_prim("/World/RoboclawsSmokeCameraRig", "Xform")
    camera = Camera(
        cfg=CameraCfg(
            prim_path="/World/RoboclawsSmokeCameraRig/Camera",
            update_period=0.0,
            height=height,
            width=width,
            data_types=[
                "rgb",
                *(segmentation_data_types if include_segmentation else ()),
            ],
            semantic_filter=semantic_filter,
            colorize_semantic_segmentation=False,
            colorize_instance_segmentation=False,
            colorize_instance_id_segmentation=False,
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=24.0,
                focus_distance=4.0,
                horizontal_aperture=20.955,
            ),
        )
    )
    view_poses = _isaac_camera_view_poses(torch=torch, device=sim.device, scene_bounds=scene_bounds)
    sim.reset()
    saved: dict[str, str] = {}
    segmentation_views: list[dict[str, Any]] = []
    total_render_steps = 0
    for view_name in ROBOT_VIEW_KEYS:
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
        "segmentation": _camera_segmentation_capture_diagnostics(
            segmentation_views,
            requested_data_types=segmentation_data_types,
            semantic_label_application=semantic_label_application,
            semantic_filter=semantic_filter,
        )
        if include_segmentation
        else _camera_segmentation_not_requested_diagnostics(),
    }


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


def _ensure_capture_lighting(stage_utils: Any) -> None:
    from pxr import Gf, UsdGeom, UsdLux

    get_current_stage = getattr(stage_utils, "get_current_stage", None)
    if not callable(get_current_stage):
        return
    stage = get_current_stage()
    if stage is None:
        return
    dome = UsdLux.DomeLight.Define(stage, "/RoboclawsSmokeDomeLight")
    dome.CreateIntensityAttr(1500.0)
    key = UsdLux.DistantLight.Define(stage, "/RoboclawsSmokeKeyLight")
    key.CreateIntensityAttr(7000.0)
    UsdGeom.XformCommonAPI(key).SetRotate(Gf.Vec3f(-55.0, 0.0, 35.0))


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
    }
    return {
        "schema": ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
        "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "rendered_to_usd": False,
        "planner_backed": False,
        "physical_robot": False,
        "semantic_pose_only": True,
        "robot_pose": _pose_near(initial_receptacle_id),
        "held_object_id": None,
        "open_receptacle_ids": [],
        "object_poses": _semantic_object_poses_from_state(state),
        "articulations": _semantic_articulations_from_state(state),
        "transform_events": [],
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
        "robot_pose": _pose_near(str(state.get("current_receptacle_id") or receptacle_id)),
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
            "robot_pose": _pose_near(str(state.get("current_receptacle_id") or receptacle_id)),
            "held_object_id": state.get("held_object_id"),
            "open_receptacle_ids": sorted(state.get("open_receptacle_ids") or []),
            "object_poses": _semantic_object_poses_from_state(state),
            "articulations": _semantic_articulations_from_state(state),
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
        poses[object_id] = {
            "object_id": object_id,
            "usd_prim_path": _object_usd_prim_path(state, object_id),
            "location_id": location_id,
            "support_receptacle_id": support_receptacle_id,
            "support_usd_prim_path": _receptacle_usd_prim_path(state, support_receptacle_id),
            "attached_to_robot": location_id == HELD_LOCATION_ID,
            "location_relation": relation,
            "state_source": ISAAC_SEMANTIC_POSE_STATE_SOURCE,
            "rendered_to_usd": False,
        }
    return poses


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
        robot_pose=_pose_near(str(location_id)),
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
        robot_pose=_pose_near(receptacle_id),
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
    state["locations"][object_id] = receptacle_id
    state["held_object_id"] = None
    state["current_receptacle_id"] = receptacle_id
    containment = dict(state.get("containment") or {})
    containment[object_id] = {
        "contained_in": receptacle_id if relation == "inside" else "",
        "location_relation": relation,
    }
    state["containment"] = containment
    diagnostic = {
        "schema": "isaac_semantic_pose_placement_v1",
        "direct_support_proven": False,
        "degradation": "semantic_pose_only",
        "object_id": object_id,
        "receptacle_id": receptacle_id,
        "relation": relation,
    }
    state["placement_diagnostics"].append(diagnostic)
    event = _record_semantic_pose_event(
        state,
        tool=tool,
        state_mutation="isaac_prim_transform",
        object_id=object_id,
        receptacle_id=receptacle_id,
        previous_location_id=HELD_LOCATION_ID,
        location_id=receptacle_id,
        relation=relation,
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
    return _ok(
        "robot_views",
        output_dir=str(args.output_dir),
        view_variant=ISAACLAB_ROBOT_VIEW_VARIANT,
        view_provenance=state.get("robot_view_provenance", {}),
        robot_pose=_pose_near(str(state.get("current_receptacle_id") or "floor_01")),
        robot_trajectory=[_pose_near(str(state.get("current_receptacle_id") or "floor_01"))],
        room_outline_count=len(state.get("receptacle_index") or {}),
        focus=_focus_payload(
            focus_object_id=args.focus_object_id,
            focus_receptacle_id=args.focus_receptacle_id,
        ),
        views={key: str(path) for key, path in views.items()},
        shapes=shapes,
        render_resolution={"width": args.render_width, "height": args.render_height},
    )


def _focus_payload(
    *,
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    has_focus = bool(focus_object_id or focus_receptacle_id)
    segmentation_unavailable = {
        "status": "segmentation_unavailable",
        "reason": "Isaac semantic-pose worker has no segmentation mask evidence.",
    }
    return {
        "has_focus": has_focus,
        "object_id": focus_object_id,
        "receptacle_id": focus_receptacle_id,
        "source": "isaac_semantic_pose",
        "visibility": dict(segmentation_unavailable),
        "fpv_visibility": dict(segmentation_unavailable),
    }


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
        provenance["semantic_pose_state_refreshed"] = False
        provenance["evidence_note"] = (
            "Robot-view images are static captures from the loaded USD scene during init; "
            "semantic pose edits are tracked in backend JSON state and are not rendered "
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
        match = re.fullmatch(r"val_(\d+)", part)
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
        object_index=object_index,
        receptacle_index=receptacle_index,
    )


def _scenario_from_scene_index(
    *,
    scene_source: str,
    scene_index: int,
    seed: int,
    generated_mess_count: int,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> CleanupScenario | None:
    receptacles = tuple(
        _cleanup_receptacle_from_scene_index(handle, entry)
        for handle, entry in sorted(receptacle_index.items())
    )
    if not receptacles:
        return None

    objects: list[CleanupObject] = []
    targets: list[TargetRule] = []
    count = max(1, int(generated_mess_count))
    for handle, entry in sorted(object_index.items()):
        target_id = _scene_target_receptacle_id(entry, receptacle_index)
        if not target_id:
            continue
        source_id = _scene_source_receptacle_id(entry, receptacle_index, target_id=target_id)
        objects.append(
            CleanupObject(
                object_id=handle,
                name=_scene_object_name(handle, entry),
                category=_scene_object_category(entry),
                location_id=source_id,
            )
        )
        targets.append(TargetRule(object_id=handle, valid_receptacle_ids=(target_id,)))
        if len(targets) >= count:
            break

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
            targets=tuple(targets),
            success_threshold=len(targets),
        ),
    )


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


def _scene_target_receptacle_id(
    entry: dict[str, Any],
    receptacle_index: dict[str, dict[str, Any]],
) -> str:
    entry_tokens = _scene_entry_tokens("", entry)
    for category_aliases, target_aliases in _SCENE_CLEANUP_TARGET_ALIASES:
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
    return {
        "robot_name": robot_name,
        "embodiment": "isaac_simple_camera_rig",
        "physical_robot": False,
        "planner_backed": False,
    }


def _scene_usd_path(scene_source: str, scene_index: int) -> str:
    return f"molmospaces://{scene_source}/scene-{scene_index}.usd"


if __name__ == "__main__":
    raise SystemExit(main())

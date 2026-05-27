#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import platform
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.backend import HELD_LOCATION_ID
from roboclaws.molmo_cleanup.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_PROVENANCE,
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
REAL_SMOKE_CAPTURE_METHOD = "isaac_lab_camera_rgb"
REAL_ROBOT_VIEW_CAPTURE_METHOD = "isaac_lab_camera_rgb_static_robot_views"
REAL_SMOKE_RENDERER_MODE = "isaac_lab_headless_rtx"


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
    init.add_argument("--runtime-mode", choices=("real", "fake"), default="real")
    init.add_argument("--include-robot", action="store_true")
    init.add_argument("--robot-name", default="simple_camera_rig")
    init.add_argument("--map-bundle-dir", type=Path)
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
        result = init_state(args)
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
    print(json.dumps(result, sort_keys=True))
    return 0


def init_state(args: argparse.Namespace) -> dict[str, Any]:
    scenario = _scenario_for_init(args)
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
    initial_receptacle_id = _initial_receptacle_id(scenario)
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
    mapping_gaps = mapping_gap_diagnostics(
        runtime_mode=args.runtime_mode,
        map_bundle_dir=args.map_bundle_dir,
        real_smoke=real_smoke,
        scene_binding_diagnostics=scene_binding_diagnostics,
    )
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
        "mapping_gaps": mapping_gaps,
        "object_index": object_index,
        "receptacle_index": receptacle_index,
        "scene_index_diagnostics": scene_index_diagnostics,
        "scene_binding_diagnostics": scene_binding_diagnostics,
        "robot_view_images": _real_smoke_robot_view_images(real_smoke),
        "robot_view_provenance": _robot_view_provenance(args.runtime_mode, real_smoke),
        "segmentation": {
            "available": False,
            "status": "blocked_capability",
            "reason": (
                "semantic or instance segmentation is not exposed by this "
                "initial Isaac semantic-pose worker"
            ),
        },
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
        scene_usd = args.run_dir / "roboclaws_phase_a_smoke_scene.usda"
        _write_generated_runtime_smoke_usd(scene_usd, scenario)
        loaded_asset_kind = "generated_runtime_smoke_usd"
    scene_index_diagnostics = _inspect_usd_scene_index(scene_usd)
    stage_prim_count = int(scene_index_diagnostics["stage_prim_count"])

    simulation_app = None
    render_steps = 0
    try:
        from isaaclab.app import AppLauncher

        launcher_args = _isaac_app_launcher_args(AppLauncher)
        app_launcher = AppLauncher(launcher_args)
        simulation_app = app_launcher.app

        capture = _capture_isaac_lab_camera_views(
            scene_usd=scene_usd,
            view_paths=robot_view_paths,
            width=DEFAULT_WIDTH,
            height=DEFAULT_HEIGHT,
            simulation_app=simulation_app,
        )
        render_steps = int(capture["render_steps"])
        robot_view_images = dict(capture["robot_view_images"])
    finally:
        if simulation_app is not None:
            simulation_app.close()

    if not smoke_image.is_file():
        raise RuntimeError(f"Isaac Lab camera capture did not write {smoke_image}")
    missing_views = sorted(
        key for key in ROBOT_VIEW_KEYS if not Path(str(robot_view_images.get(key, ""))).is_file()
    )
    if missing_views:
        raise RuntimeError(f"Isaac Lab robot view capture missed views: {', '.join(missing_views)}")
    return {
        "image_path": str(smoke_image),
        "scene_usd": str(scene_usd),
        "loaded_asset_kind": loaded_asset_kind,
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
        "stage_prim_count": stage_prim_count,
        "render_steps": render_steps,
        "scene_index_diagnostics": scene_index_diagnostics,
        "object_index": scene_index_diagnostics["object_index"],
        "receptacle_index": scene_index_diagnostics["receptacle_index"],
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


def _write_generated_runtime_smoke_usd(
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


def _inspect_usd_scene_index(usd_path: Path) -> dict[str, Any]:
    from pxr import Usd

    stage = Usd.Stage.Open(str(usd_path))
    if stage is None:
        raise RuntimeError(f"Isaac USD stage could not be opened for indexing: {usd_path}")

    object_index: dict[str, dict[str, Any]] = {}
    receptacle_index: dict[str, dict[str, Any]] = {}
    stage_prim_count = 0
    for prim in stage.Traverse():
        stage_prim_count += 1
        prim_path = str(prim.GetPath())
        handle = _usd_handle_from_prim(prim_path, object_index, receptacle_index)
        if _is_object_prim_path(prim_path):
            object_index[handle] = _usd_index_entry(prim_path, prim.GetName(), "object")
        elif _is_receptacle_prim_path(prim_path):
            receptacle_index[handle] = {
                **_usd_index_entry(prim_path, prim.GetName(), "receptacle"),
                "support_pose": _pose_near(handle),
            }

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
    }


def _scene_index_match(
    *,
    public_id: str,
    public_label: str,
    category: str | None,
    index: dict[str, dict[str, Any]],
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

    category_norm = _norm(category)
    if not category_norm:
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

    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    sim = sim_utils.SimulationContext(sim_utils.SimulationCfg(device=device))
    sim_utils.create_prim("/World/RoboclawsSmokeCameraRig", "Xform")
    camera = Camera(
        cfg=CameraCfg(
            prim_path="/World/RoboclawsSmokeCameraRig/Camera",
            update_period=0.0,
            height=height,
            width=width,
            data_types=["rgb"],
            spawn=sim_utils.PinholeCameraCfg(
                focal_length=24.0,
                focus_distance=4.0,
                horizontal_aperture=20.955,
            ),
        )
    )
    view_poses = _isaac_camera_view_poses(torch=torch, device=sim.device)
    sim.reset()
    saved: dict[str, str] = {}
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
    return {
        "render_steps": total_render_steps,
        "robot_view_images": saved,
    }


def _isaac_camera_view_poses(*, torch: Any, device: Any) -> dict[str, tuple[Any, Any]]:
    def tensor(values: list[list[float]]) -> Any:
        return torch.tensor(values, dtype=torch.float32, device=device)

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


def mapping_gap_diagnostics(
    *,
    runtime_mode: str,
    map_bundle_dir: Path | None,
    real_smoke: dict[str, Any] | None = None,
    scene_binding_diagnostics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    source = "real_isaac_pending" if runtime_mode == "real" else "fake_protocol"
    scene_bindings = _dict(scene_binding_diagnostics)
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
                "status": "blocked_capability",
                "source": "generated_runtime_smoke_usd",
                "detail": "Semantic or instance segmentation masks are not exposed yet.",
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
                "status": "blocked_capability",
                "source": source,
                "detail": "Semantic or instance segmentation masks are not exposed yet.",
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
    write_state_from_state_arg(state)
    return _ok(
        "navigate_to_object",
        object_id=object_id,
        source_receptacle_id=str(location_id),
        previous_receptacle_id=previous,
        location_id=str(location_id),
        robot_pose=_pose_near(str(location_id)),
        state_mutation="isaac_root_pose",
    )


def navigate_to_receptacle(args: argparse.Namespace, state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "navigate_to_receptacle")
    receptacle_id = args.receptacle_id
    if receptacle_id not in _receptacles_by_id(state):
        return _error("navigate_to_receptacle", "stale_reference", receptacle_id=receptacle_id)
    previous = state["current_receptacle_id"]
    state["current_receptacle_id"] = receptacle_id
    held_object_id = state.get("held_object_id")
    write_state_from_state_arg(state)
    return _ok(
        "navigate_to_receptacle",
        receptacle_id=receptacle_id,
        object_id=held_object_id,
        previous_receptacle_id=previous,
        robot_pose=_pose_near(receptacle_id),
        state_mutation="isaac_root_pose",
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
    write_state_from_state_arg(state)
    return _ok(
        "pick",
        object_id=object_id,
        previous_location_id=previous_location_id,
        location_id=HELD_LOCATION_ID,
        state_mutation="isaac_prim_attach",
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
    write_state_from_state_arg(state)
    return _ok(
        "open_receptacle",
        receptacle_id=receptacle_id,
        object_id=state.get("held_object_id"),
        opened=opened,
        state_mutation="isaac_articulation_joint_pose",
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
    write_state_from_state_arg(state)
    return _ok(
        "close_receptacle",
        receptacle_id=receptacle_id,
        object_id=state.get("held_object_id"),
        closed=was_open,
        state_mutation="isaac_articulation_joint_pose",
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
    _write_placeholder_image(
        args.output_path,
        title=args.title,
        subtitle=state["runtime"]["renderer_mode"],
        state=state,
        width=args.render_width,
        height=args.render_height,
    )
    write_state_from_state_arg(state)
    return _ok("snapshot", output_path=str(args.output_path))


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
        if not source.is_file():
            raise RuntimeError(f"missing real Isaac {key} view image: {source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.resolve() == target.resolve():
            with Image.open(source) as image:
                rgb = image.convert("RGB")
                if not _pil_image_has_variance(rgb):
                    raise RuntimeError(f"real Isaac {key} view image appears blank: {source}")
                shapes[key] = [rgb.height, rgb.width, 3]
            continue
        with Image.open(source) as image:
            rgb = image.convert("RGB")
            if not _pil_image_has_variance(rgb):
                raise RuntimeError(f"real Isaac {key} view image appears blank: {source}")
            if rgb.size != (width, height):
                rgb = rgb.resize((width, height))
            rgb.save(target)
            shapes[key] = [rgb.height, rgb.width, 3]
    return shapes


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

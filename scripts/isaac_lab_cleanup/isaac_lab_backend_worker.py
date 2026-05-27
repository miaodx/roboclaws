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
    if args.runtime_mode == "real":
        _require_isaac_import()
    scenario = _scenario_for_init(args)
    runtime = runtime_diagnostics(args.runtime_mode)
    scene_load = scene_load_diagnostics(args.runtime_mode, args.scene_source, args.scene_index)
    mapping_gaps = mapping_gap_diagnostics(
        runtime_mode=args.runtime_mode,
        map_bundle_dir=args.map_bundle_dir,
    )
    initial_receptacle_id = _initial_receptacle_id(scenario)
    state = {
        "schema": STATE_SCHEMA,
        "backend": ISAACLAB_SUBPROCESS_BACKEND,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
        "runtime": runtime,
        "scene_load": scene_load,
        "scene_source": args.scene_source,
        "scene_index": args.scene_index,
        "scene_usd": _scene_usd_path(args.scene_source, args.scene_index),
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
        "object_index": _object_index(scenario),
        "receptacle_index": _receptacle_index(scenario),
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
    before_path = args.run_dir / "isaac_runtime_smoke.png"
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
        "object_index": state["object_index"],
        "receptacle_index": state["receptacle_index"],
        "mapping_gaps": mapping_gaps,
        "segmentation": state["segmentation"],
        "requested_generated_mess_count": args.generated_mess_count,
        "generated_mess_count": len(state["private_manifest"]["targets"]),
        "robot": state["robot"],
        "artifacts": {"runtime_smoke_image": str(before_path)},
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


def runtime_diagnostics(runtime_mode: str) -> dict[str, Any]:
    isaac_lab_version = None
    isaac_sim_version = None
    if runtime_mode == "real":
        try:
            import isaaclab

            isaac_lab_version = getattr(isaaclab, "__version__", "unknown")
        except Exception:
            isaac_lab_version = None
        try:
            import isaacsim

            isaac_sim_version = getattr(isaacsim, "__version__", "unknown")
        except Exception:
            isaac_sim_version = None
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
    rendering = rendering_diagnostics(runtime_mode)
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
        "camera_resolution": [DEFAULT_WIDTH, DEFAULT_HEIGHT],
        "physical_robot": False,
        "planner_backed": False,
        "primitive_provenance": ISAAC_SEMANTIC_POSE_PROVENANCE,
    }


def rendering_diagnostics(runtime_mode: str) -> dict[str, Any]:
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
) -> dict[str, Any]:
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
) -> list[dict[str, Any]]:
    source = "real_isaac_pending" if runtime_mode == "real" else "fake_protocol"
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
            "detail": "Open/place effects are semantic state edits, not physics or planner proof.",
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
    args.output_dir.mkdir(parents=True, exist_ok=True)
    views = {
        "fpv": args.output_dir / f"{args.label}_fpv.png",
        "chase": args.output_dir / f"{args.label}_chase.png",
        "map": args.output_dir / f"{args.label}_map.png",
        "verify": args.output_dir / f"{args.label}_verify.png",
    }
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
    write_state_from_state_arg(state)
    return _ok(
        "robot_views",
        output_dir=str(args.output_dir),
        view_variant=ISAACLAB_ROBOT_VIEW_VARIANT,
        view_provenance="isaac_lab_worker",
        robot_pose=_pose_near(str(state.get("current_receptacle_id") or "floor_01")),
        robot_trajectory=[_pose_near(str(state.get("current_receptacle_id") or "floor_01"))],
        room_outline_count=len(state.get("receptacle_index") or {}),
        focus=_focus_payload(
            focus_object_id=args.focus_object_id,
            focus_receptacle_id=args.focus_receptacle_id,
        ),
        views={key: str(path) for key, path in views.items()},
    )


def _focus_payload(
    *,
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    has_focus = bool(focus_object_id or focus_receptacle_id)
    segmentation_unavailable = {
        "status": "segmentation_unavailable",
        "reason": "Isaac semantic-pose fake protocol has no segmentation mask evidence.",
    }
    return {
        "has_focus": has_focus,
        "object_id": focus_object_id,
        "receptacle_id": focus_receptacle_id,
        "source": "isaac_semantic_pose",
        "visibility": dict(segmentation_unavailable),
        "fpv_visibility": dict(segmentation_unavailable),
    }


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
        return build_cleanup_scenario(seed=args.seed)
    return _scenario_from_map_bundle(
        args.map_bundle_dir,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
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

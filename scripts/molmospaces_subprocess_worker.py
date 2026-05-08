#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from typing import Any

import mujoco
from PIL import Image, ImageDraw

BACKEND = "molmospaces_subprocess"
API_SEMANTIC_PROVENANCE = "api_semantic"
HELD_LOCATION_ID = "held_by_agent"

TARGET_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("Cup", "Mug", "Plate", "Bowl"), ("Sink",)),
    (("Book", "Newspaper"), ("ShelvingUnit", "Desk")),
    (("Apple", "Bread", "Egg", "Potato", "Lettuce"), ("Fridge",)),
    (("RemoteControl",), ("TVStand",)),
    (("Pillow", "TeddyBear"), ("Bed", "Sofa")),
)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="MolmoSpaces JSON worker for roboclaws.")
    parser.add_argument("--state-path", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init")
    init.add_argument("--seed", type=int, default=7)
    init.add_argument("--scene-source", default="procthor-10k-val")
    init.add_argument("--scene-index", type=int, default=0)
    init.add_argument("--include-robot", action="store_true")
    init.add_argument("--robot-name", default="rby1m")

    subparsers.add_parser("observe")
    subparsers.add_parser("scene_objects")
    subparsers.add_parser("locations")

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--output-path", type=Path, required=True)
    snapshot.add_argument("--title", default="")

    robot_views = subparsers.add_parser("robot_views")
    robot_views.add_argument("--output-dir", type=Path, required=True)
    robot_views.add_argument("--label", required=True)
    robot_views.add_argument("--focus-object-id")
    robot_views.add_argument("--focus-receptacle-id")

    goto = subparsers.add_parser("goto")
    goto.add_argument("--receptacle-id", required=True)

    navigate_object = subparsers.add_parser("navigate_to_object")
    navigate_object.add_argument("--object-id", required=True)

    navigate_receptacle = subparsers.add_parser("navigate_to_receptacle")
    navigate_receptacle.add_argument("--receptacle-id", required=True)

    pick = subparsers.add_parser("pick")
    pick.add_argument("--object-id", required=True)

    open_receptacle_parser = subparsers.add_parser("open_receptacle")
    open_receptacle_parser.add_argument("--receptacle-id", required=True)

    place = subparsers.add_parser("place")
    place.add_argument("--receptacle-id", required=True)

    place_inside_parser = subparsers.add_parser("place_inside")
    place_inside_parser.add_argument("--receptacle-id", required=True)

    object_done_parser = subparsers.add_parser("object_done")
    object_done_parser.add_argument("--object-id", required=True)
    object_done_parser.add_argument("--receptacle-id", required=True)

    done = subparsers.add_parser("done")
    done.add_argument("--reason", default="")

    args = parser.parse_args(argv)
    if args.command == "init":
        result = init_state(
            state_path=args.state_path,
            seed=args.seed,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
            include_robot=args.include_robot,
            robot_name=args.robot_name,
        )
    else:
        state = _read_state(args.state_path)
        if args.command == "observe":
            result = observe(state)
            _write_state(args.state_path, state)
        elif args.command == "scene_objects":
            result = scene_objects(state)
            _write_state(args.state_path, state)
        elif args.command == "locations":
            result = _ok("locations", final_locations=_read_locations(state))
        elif args.command == "snapshot":
            result = write_snapshot(state, args.output_path, args.title)
        elif args.command == "robot_views":
            result = write_robot_views(
                state,
                args.output_dir,
                args.label,
                focus_object_id=args.focus_object_id,
                focus_receptacle_id=args.focus_receptacle_id,
            )
        elif args.command == "goto":
            result = goto_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "navigate_to_object":
            result = navigate_to_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "navigate_to_receptacle":
            result = navigate_to_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "pick":
            result = pick_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "open_receptacle":
            result = open_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "place":
            result = place_object(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "place_inside":
            result = place_inside_object(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "object_done":
            result = object_done(state, args.object_id, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "done":
            result = done_cleanup(state, args.reason)
        else:
            raise AssertionError(args.command)

    print(json.dumps(result, sort_keys=True))


def init_state(
    *,
    state_path: Path,
    seed: int,
    scene_source: str,
    scene_index: int,
    include_robot: bool = False,
    robot_name: str = "rby1m",
) -> dict[str, Any]:
    from molmo_spaces.molmo_spaces_constants import get_robot_path, get_scenes_root
    from molmo_spaces.utils.lazy_loading_utils import install_scene_from_source_index
    from molmo_spaces.utils.scene_metadata_utils import get_scene_metadata

    install_scene_from_source_index(scene_source, scene_index)
    scene_xml = get_scenes_root() / scene_source / f"val_{scene_index}.xml"
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
    targets = _select_targets(objects, receptacles)
    if len(targets) < 5:
        raise RuntimeError(f"expected at least 5 cleanup targets, found {len(targets)}")

    state = {
        "backend": BACKEND,
        "seed": seed,
        "scene_source": scene_source,
        "scene_index": scene_index,
        "scene_xml": str(scene_xml),
        "robot_included": include_robot,
        "robot_name": robot_name if include_robot else None,
        "robot_xml": str(robot_xml) if robot_xml is not None else None,
        "python_executable": sys.executable,
        "runtime": {
            "python_version": sys.version.split()[0],
            "mujoco_version": mujoco.__version__,
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
        "qpos": [float(value) for value in data.qpos],
        "held_object_id": None,
        "current_receptacle_id": None,
        "open_receptacle_ids": [],
        "tool_event_counts": {},
    }
    _seed_misplaced_objects(model, data, state, targets)
    _refresh_object_positions(model, data, state)
    state["room_outlines"] = _collect_room_outlines(model, data, state)
    if include_robot:
        initial_receptacle = state["receptacles"][_first_wrong_receptacle(state, targets[0])]
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
    state["current_receptacle_id"] = _first_wrong_receptacle(state, targets[0])
    state["private_manifest"] = {
        "scenario_id": f"molmospaces-procthor-val-{scene_index}-{seed}",
        "success_threshold": 3,
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
        scene_xml=state["scene_xml"],
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


def scene_objects(state: dict[str, Any]) -> dict[str, Any]:
    _count(state, "scene_objects")
    state["scenario_public"] = _public_scenario(state)
    return _ok(
        "scene_objects",
        backend=BACKEND,
        objects=state["scenario_public"]["objects"],
        receptacles=state["scenario_public"]["receptacles"],
        inventory_source="molmospaces_metadata+mujoco_state",
        metadata_object_count=state["metadata_object_count"],
    )


def write_snapshot(state: dict[str, Any], output_path: Path, title: str) -> dict[str, Any]:
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    renderer = mujoco.Renderer(model, height=360, width=540)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [8.5, 6.5, 0.8]
    camera.distance = 9.5
    camera.azimuth = 225
    camera.elevation = -45
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(output_path)
    return _ok("snapshot", path=str(output_path), title=title, shape=list(frame.shape))


def write_robot_views(
    state: dict[str, Any],
    output_dir: Path,
    label: str,
    *,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
) -> dict[str, Any]:
    if not state.get("robot_included"):
        return _error("robot_views", "robot_not_included")
    if focus_object_id is not None and focus_object_id not in state["objects"]:
        return _error("robot_views", "stale_reference", object_id=focus_object_id)
    if focus_receptacle_id is not None and focus_receptacle_id not in state["receptacles"]:
        return _error("robot_views", "stale_reference", receptacle_id=focus_receptacle_id)
    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)

    output_dir.mkdir(parents=True, exist_ok=True)
    safe_label = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in label)
    fpv_path = output_dir / f"{safe_label}.fpv.png"
    chase_path = output_dir / f"{safe_label}.chase.png"
    map_path = output_dir / f"{safe_label}.map.png"
    verify_path = output_dir / f"{safe_label}.verify.png"

    focus = _focus_payload(state, focus_object_id, focus_receptacle_id)
    fpv = _render_fixed_camera(model, data, "robot_0/head_camera")
    chase = _render_fixed_camera(model, data, "robot_0/camera_follower")
    verify_camera = _focus_camera(state, focus)
    verify = _render_free_camera(model, data, verify_camera)
    focus["fpv_visibility"] = _focus_visibility(
        model,
        data,
        "robot_0/head_camera",
        focus,
        frame=fpv,
    )
    focus["visibility"] = _focus_visibility(model, data, verify_camera, focus, frame=verify)
    Image.fromarray(fpv).save(fpv_path)
    Image.fromarray(chase).save(chase_path)
    verify_image = Image.fromarray(verify)
    _annotate_focus_image(verify_image, focus)
    verify_image.save(verify_path)
    _render_robot_map(state, focus=focus).save(map_path)

    return _ok(
        "robot_views",
        backend=BACKEND,
        robot_name=state.get("robot_name"),
        robot_pose=state.get("robot_pose"),
        robot_trajectory=state.get("robot_trajectory", []),
        view_variant="molmospaces-rby1m-fpv-map-chase-verify",
        view_provenance=state.get("robot_view_provenance", {}),
        focus=focus,
        room_outline_count=len(state.get("room_outlines", [])),
        views={
            "fpv": str(fpv_path),
            "chase": str(chase_path),
            "map": str(map_path),
            "verify": str(verify_path),
        },
        shapes={
            "fpv": list(fpv.shape),
            "chase": list(chase.shape),
            "verify": list(verify.shape),
            "map": [420, 620, 3],
        },
    )


def goto_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "goto")
    return _navigate_to_receptacle(state, receptacle_id, tool="goto")


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
    if relation == "inside" and receptacle_id not in set(state.get("open_receptacle_ids", [])):
        return _error(tool, "receptacle_closed", receptacle_id=receptacle_id)

    model, data = _load_model_data_for_state(state)
    _apply_qpos(data, state["qpos"])
    obj = state["objects"][object_id]
    target_position = _placement_position(
        receptacle,
        index=state["selected_object_ids"].index(object_id),
        relation=relation,
        object_category=obj.get("category"),
    )
    _set_free_body_position(model, data, obj["body_name"], target_position)
    mujoco.mj_forward(model, data)
    _refresh_object_positions(model, data, state)

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


def object_done(state: dict[str, Any], object_id: str, receptacle_id: str) -> dict[str, Any]:
    _count(state, "object_done")
    if object_id not in state["objects"]:
        return _error("object_done", "stale_reference", object_id=object_id)
    if receptacle_id not in state["receptacles"]:
        return _error("object_done", "stale_reference", receptacle_id=receptacle_id)
    final_locations = _read_locations(state)
    obj = state["objects"][object_id]
    return _ok(
        "object_done",
        object_id=object_id,
        receptacle_id=receptacle_id,
        location_id=final_locations.get(object_id),
        contained_in=obj.get("contained_in"),
        location_relation=obj.get("location_relation", "on"),
        matches_expected_location=final_locations.get(object_id) == receptacle_id,
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
            }
        )
    return sorted(items, key=lambda item: (item["category"], item["receptacle_id"]))


def _select_targets(
    objects: list[dict[str, Any]],
    receptacles: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    selected = []
    used: set[str] = set()
    for object_categories, receptacle_categories in TARGET_RULES:
        obj = next(
            (
                item
                for item in objects
                if item["object_id"] not in used and item["category"] in object_categories
            ),
            None,
        )
        receptacle = _first_receptacle_for_categories(receptacles, receptacle_categories)
        if obj is None or receptacle is None:
            continue
        obj = dict(obj)
        obj["target_receptacle_id"] = receptacle["receptacle_id"]
        selected.append(obj)
        used.add(obj["object_id"])
    return selected


def _first_receptacle_for_categories(
    receptacles: list[dict[str, Any]],
    categories: tuple[str, ...],
) -> dict[str, Any] | None:
    for category in categories:
        for receptacle in receptacles:
            if receptacle["category"] == category:
                return receptacle
    return None


def _seed_misplaced_objects(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
    targets: list[dict[str, Any]],
) -> None:
    wrong_pool = [
        item
        for item in state["receptacles"].values()
        if item["receptacle_id"] not in {target["target_receptacle_id"] for target in targets}
    ]
    if not wrong_pool:
        wrong_pool = list(state["receptacles"].values())
    for index, target in enumerate(targets):
        wrong = wrong_pool[index % len(wrong_pool)]
        if wrong["receptacle_id"] == target["target_receptacle_id"]:
            wrong = wrong_pool[(index + 1) % len(wrong_pool)]
        state["objects"][target["object_id"]]["target_receptacle_id"] = target[
            "target_receptacle_id"
        ]
        state["objects"][target["object_id"]]["seeded_start_receptacle_id"] = wrong["receptacle_id"]
        _set_free_body_position(
            model,
            data,
            target["body_name"],
            _placement_position(wrong, index=index, object_category=target.get("category")),
        )
    mujoco.mj_forward(model, data)


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
    status = "success" if len(restored) >= manifest["success_threshold"] else "failed"
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


def _placement_position(
    receptacle: dict[str, Any],
    *,
    index: int,
    relation: str = "on",
    object_category: str | None = None,
) -> list[float]:
    base = receptacle["position"]
    if receptacle.get("category") == "Fridge" and relation == "inside":
        return [float(base[0]) + 0.08, float(base[1]) - 0.16, float(base[2]) + 0.35]
    if receptacle.get("category") == "Fridge":
        return [float(base[0]) + 0.25, float(base[1]) + 0.5, float(base[2]) + 0.55]
    offset = ((index % 3) - 1) * 0.12
    y_offset = 0.08 * (index % 2)
    if object_category == "Apple":
        y_offset = 0.16
    elif object_category == "RemoteControl":
        offset = 0.0
        y_offset = 0.34
    if object_category == "Apple":
        height = 0.58
    elif object_category == "RemoteControl":
        height = 0.45
    else:
        height = 0.35
    return [float(base[0]) + offset, float(base[1]) + y_offset, float(base[2]) + height]


def _load_model_data(scene_xml: Path) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(scene_xml))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


def _load_model_data_for_state(state: dict[str, Any]) -> tuple[mujoco.MjModel, mujoco.MjData]:
    if state.get("robot_included"):
        robot_xml = state.get("robot_xml")
        if not robot_xml:
            raise ValueError("robot_included state missing robot_xml")
        return _load_robot_model_data(Path(state["scene_xml"]), Path(robot_xml))
    return _load_model_data(Path(state["scene_xml"]))


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
    return [
        round(float(pose["x"]) + math.cos(theta) * 0.45, 6),
        round(float(pose["y"]) + math.sin(theta) * 0.45, 6),
        1.05,
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
            joints.append(
                {
                    "joint_name": joint_name,
                    "joint_type": "hinge"
                    if joint_type == int(mujoco.mjtJoint.mjJNT_HINGE)
                    else "slide",
                    "open_value": round(open_value, 6),
                }
            )
    return joints


def _robot_pose_near_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, float]:
    target = receptacle["position"]
    target_room_id = _target_room_id(state, receptacle)
    pose = _robot_pose_near_position(
        state,
        target,
        target_room_id=target_room_id,
        target_receptacle_id=receptacle["receptacle_id"],
    )
    pose["robot_room_id"] = pose.get("robot_room_id")
    pose.update(_room_relation_payload(state, receptacle, [pose["x"], pose["y"]]))
    return pose


def _robot_pose_for_open_receptacle(
    state: dict[str, Any],
    receptacle: dict[str, Any],
) -> dict[str, float]:
    if receptacle.get("category") != "Fridge":
        return _robot_pose_near_receptacle(state, receptacle)

    base = receptacle["position"]
    target_room_id = _target_room_id(state, receptacle)
    candidates = [
        (float(base[0]) - 0.76, float(base[1]) + 0.20),
        (float(base[0]) - 0.72, float(base[1]) + 0.36),
        (float(base[0]) - 0.90, float(base[1]) + 0.08),
    ]
    x, y = _first_same_room_point(state, candidates, target_room_id)
    target = [float(base[0]), float(base[1]), float(base[2]) + 0.35]
    theta = math.atan2(target[1] - y, target[0] - x)
    pose = {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "z": 0.0,
        "theta": round(float(theta), 6),
        "theta_source": "opened_receptacle_access_yaw",
        "head_yaw": 0.0,
        "head_yaw_source": "base_yaw_handles_target_bearing",
        "head_pitch": _robot_head_pitch_for_target(target, [x, y]),
        "head_pitch_source": "target_framing_head_pitch",
        "target_receptacle_id": receptacle["receptacle_id"],
        "robot_room_id": _room_for_point(state, [x, y]) or target_room_id,
    }
    pose.update(_room_relation_payload(state, receptacle, [pose["x"], pose["y"]]))
    return {key: value for key, value in pose.items() if value is not None}


def _first_same_room_point(
    state: dict[str, Any],
    candidates: list[tuple[float, float]],
    target_room_id: str | None,
) -> tuple[float, float]:
    for x, y in candidates:
        if _room_for_point(state, [x, y]) == target_room_id:
            return x, y
    return candidates[0]


def _robot_pose_near_object(
    state: dict[str, Any],
    obj: dict[str, Any],
    *,
    source_receptacle_id: str | None = None,
) -> dict[str, float]:
    target = obj["position"]
    source_receptacle = state["receptacles"].get(
        source_receptacle_id or obj.get("seeded_start_receptacle_id", "")
    )
    source_room_id = _target_room_id(state, source_receptacle) if source_receptacle else None
    target_room_id = _room_for_point(state, target) or source_room_id
    pose = _robot_pose_near_position(
        state,
        target,
        target_room_id=target_room_id,
        target_object_id=obj["object_id"],
    )
    robot_room_id = pose.get("robot_room_id")
    pose.update(
        {
            "target_room_id": target_room_id,
            "same_room_as_target": robot_room_id == target_room_id,
            "room_relation_source": "mujoco_room_outline",
            "room_plausibility": "same_room"
            if robot_room_id == target_room_id
            else "room_mismatch",
        }
    )
    return pose


def _robot_pose_near_position(
    state: dict[str, Any],
    target: list[float],
    *,
    target_room_id: str | None,
    target_receptacle_id: str | None = None,
    target_object_id: str | None = None,
) -> dict[str, float]:
    center = _scene_center(list(state["receptacles"].values()))
    stand_off = _robot_stand_off_for_target(state, target_object_id)
    preferred_angle = math.atan2(center[1] - target[1], center[0] - target[0])
    target_room = _room_outline_for_id(state, target_room_id)
    candidate_angles = [preferred_angle] + [index * math.tau / 24.0 for index in range(24)]
    candidates = []
    for angle in candidate_angles:
        x = float(target[0]) + math.cos(angle) * stand_off
        y = float(target[1]) + math.sin(angle) * stand_off
        robot_room = _room_for_point(state, [x, y])
        same_room = robot_room == target_room_id
        inside_target_room = target_room is not None and _point_inside_outline(
            [x, y], target_room, margin=0.08
        )
        clearance = _outline_clearance([x, y], target_room) if target_room is not None else 0.0
        angle_penalty = _angle_delta(angle, preferred_angle)
        candidates.append(
            (
                1 if same_room or inside_target_room else 0,
                clearance,
                -angle_penalty,
                x,
                y,
                robot_room,
            )
        )
    _, _, _, x, y, robot_room = max(candidates)
    if robot_room is None and target_room_id is not None:
        robot_room = target_room_id
    theta = math.atan2(float(target[1]) - y, float(target[0]) - x)
    head_pitch = _robot_head_pitch_for_target(target, [x, y])
    pose = {
        "x": round(float(x), 6),
        "y": round(float(y), 6),
        "z": 0.0,
        "theta": round(float(theta), 6),
        "theta_source": "target_facing_base_yaw",
        "head_yaw": 0.0,
        "head_yaw_source": "base_yaw_handles_target_bearing",
        "head_pitch": head_pitch,
        "head_pitch_source": "target_framing_head_pitch",
        "target_receptacle_id": target_receptacle_id,
        "target_object_id": target_object_id,
        "robot_room_id": robot_room,
    }
    return {key: value for key, value in pose.items() if value is not None}


def _robot_stand_off_for_target(state: dict[str, Any], target_object_id: str | None) -> float:
    obj = state.get("objects", {}).get(target_object_id or "")
    if not obj:
        return 1.15
    if obj.get("category") == "RemoteControl":
        return 0.85
    if obj.get("category") == "Apple":
        return 1.0
    return 1.15


def _robot_head_pitch_for_target(target: list[float], robot_xy: list[float]) -> float:
    horizontal = math.hypot(
        float(target[0]) - float(robot_xy[0]),
        float(target[1]) - float(robot_xy[1]),
    )
    horizontal = max(horizontal, 0.25)
    camera_height = 1.55
    focus_height = float(target[2]) + 0.2
    pitch = math.atan2(camera_height - focus_height, horizontal)
    return round(max(0.25, min(0.75, pitch)), 6)


def _scene_center(items: list[dict[str, Any]]) -> tuple[float, float]:
    if not items:
        return (0.0, 0.0)
    return (
        sum(float(item["position"][0]) for item in items) / len(items),
        sum(float(item["position"][1]) for item in items) / len(items),
    )


def _render_fixed_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera_name: str,
) -> Any:
    renderer = mujoco.Renderer(model, height=360, width=540, max_geom=20000)
    renderer.update_scene(data, camera=camera_name)
    frame = renderer.render()
    renderer.close()
    return frame


def _focus_camera(state: dict[str, Any], focus: dict[str, Any]) -> mujoco.MjvCamera:
    focus_position = focus.get("focus_position") or _scene_focus_position(state)
    camera = mujoco.MjvCamera()
    camera.type = mujoco.mjtCamera.mjCAMERA_FREE
    camera.lookat[:] = [
        float(focus_position[0]),
        float(focus_position[1]),
        float(focus_position[2]) + 0.35,
    ]
    if focus.get("focus_mode") == "object_closeup":
        camera.lookat[:] = [
            float(focus_position[0]),
            float(focus_position[1]),
            float(focus_position[2]) + 0.05,
        ]
        camera.distance = 1.8
        camera.elevation = -65
    else:
        camera.distance = 4.0 if focus.get("has_focus") else 7.5
        camera.elevation = -68 if focus.get("has_focus") else -45
    camera.azimuth = _focus_camera_azimuth(state, focus_position, focus)
    return camera


def _render_free_camera(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera,
) -> Any:
    renderer = mujoco.Renderer(model, height=360, width=540, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    return frame


def _annotate_focus_image(image: Image.Image, focus: dict[str, Any]) -> None:
    if not focus.get("has_focus"):
        return
    draw = ImageDraw.Draw(image)
    object_label = str(focus.get("object_label") or "object")
    receptacle_label = str(focus.get("receptacle_label") or "target")
    label = f"Object: {object_label}   Target: {receptacle_label}"
    draw.rectangle((0, 0, image.width, 28), fill=(15, 23, 42))
    draw.text((10, 8), label, fill=(248, 250, 252))
    visibility = focus.get("visibility") or {}
    for box in visibility.get("boxes", []):
        left, top, right, bottom = box["bbox"]
        color = tuple(box["color"])
        draw.rectangle((left, top, right, bottom), outline=color, width=4)
        draw.text((left, max(30, top - 14)), box["label"], fill=color)


def _focus_camera_azimuth(
    state: dict[str, Any],
    focus_position: list[float],
    focus: dict[str, Any] | None = None,
) -> float:
    if (
        focus is not None
        and focus.get("receptacle_category") == "Fridge"
        and focus.get("object_contained_in") != focus.get("receptacle_id")
    ):
        return 45.0
    pose = state.get("robot_pose") or {}
    if "x" not in pose or "y" not in pose:
        return 225.0
    dx = float(focus_position[0]) - float(pose["x"])
    dy = float(focus_position[1]) - float(pose["y"])
    if math.hypot(dx, dy) < 0.001:
        return 225.0
    return math.degrees(math.atan2(dx, dy))


def _focus_payload(
    state: dict[str, Any],
    focus_object_id: str | None,
    focus_receptacle_id: str | None,
) -> dict[str, Any]:
    obj = state["objects"].get(focus_object_id) if focus_object_id else None
    receptacle = state["receptacles"].get(focus_receptacle_id) if focus_receptacle_id else None
    positions = []
    if obj is not None:
        positions.append(obj["position"])
    if receptacle is not None:
        positions.append(receptacle["position"])
    if obj is not None and receptacle is not None:
        object_position = obj["position"]
        receptacle_position = receptacle["position"]
        if receptacle.get("category") == "Fridge" and (
            obj.get("location_relation") == "held"
            or obj.get("contained_in") == receptacle.get("receptacle_id")
        ):
            focus_position = receptacle_position
            focus_mode = "receptacle_context"
        elif math.dist(object_position[:2], receptacle_position[:2]) > 1.2:
            focus_position = receptacle_position
            focus_mode = "receptacle_context"
        else:
            focus_position = object_position
            focus_mode = "object_closeup"
    else:
        focus_position = _average_position(positions) if positions else _scene_focus_position(state)
        focus_mode = "receptacle_context" if receptacle is not None else "scene_context"
    return {
        "has_focus": obj is not None or receptacle is not None,
        "object_id": focus_object_id,
        "object_label": _item_label(obj, "object_id") if obj is not None else None,
        "object_category": obj.get("category") if obj is not None else None,
        "object_position": obj.get("position") if obj is not None else None,
        "object_body_name": obj.get("body_name") if obj is not None else None,
        "object_contained_in": obj.get("contained_in") if obj is not None else None,
        "object_location_relation": obj.get("location_relation") if obj is not None else None,
        "receptacle_id": focus_receptacle_id,
        "receptacle_label": _item_label(receptacle, "receptacle_id")
        if receptacle is not None
        else None,
        "receptacle_category": receptacle.get("category") if receptacle is not None else None,
        "receptacle_position": receptacle.get("position") if receptacle is not None else None,
        "receptacle_body_name": receptacle.get("body_name") if receptacle is not None else None,
        "focus_position": focus_position,
        "focus_mode": focus_mode,
        "provenance": "public_mujoco_state_report_aid",
    }


def _average_position(positions: list[list[float]]) -> list[float]:
    return [
        round(sum(float(position[index]) for position in positions) / len(positions), 6)
        for index in range(3)
    ]


def _scene_focus_position(state: dict[str, Any]) -> list[float]:
    points = [item["position"] for item in state["receptacles"].values()]
    if not points:
        return [0.0, 0.0, 0.0]
    return _average_position(points)


def _item_label(item: dict[str, Any] | None, id_key: str) -> str:
    if item is None:
        return ""
    category = str(item.get("category") or item.get("kind") or "item")
    identifier = str(item.get(id_key, ""))
    short_id = identifier.split("_", 1)[0]
    return f"{category} {short_id}"


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
        segmentation = _render_segmentation(model, data, camera)
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


def _render_segmentation(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    camera: mujoco.MjvCamera | str,
) -> Any:
    renderer = mujoco.Renderer(model, height=360, width=540, max_geom=20000)
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

    baseline = frame if frame is not None else _render_color_frame(model, data, camera)
    baseline = np.asarray(baseline)
    previous_rgba = model.geom_rgba[geom_ids].copy()
    previous_matid = model.geom_matid[geom_ids].copy()
    try:
        for geom_id in geom_ids:
            model.geom_rgba[geom_id] = np.array([1.0, 0.0, 1.0, 1.0])
            model.geom_matid[geom_id] = -1
        highlighted = _render_color_frame(model, data, camera)
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
) -> Any:
    renderer = mujoco.Renderer(model, height=360, width=540, max_geom=20000)
    renderer.update_scene(data, camera=camera)
    frame = renderer.render()
    renderer.close()
    return frame


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
    width, height = 620, 420
    margin = 34
    image = Image.new("RGB", (width, height), (247, 248, 250))
    draw = ImageDraw.Draw(image)
    draw.rectangle((12, 12, width - 12, height - 12), outline=(187, 193, 204), width=2)

    focus = focus or {}
    points = _map_points(state, focus)
    min_x, max_x, min_y, max_y = _map_bounds(points)

    def project(x: float, y: float) -> tuple[int, int]:
        px = margin + (x - min_x) / max(max_x - min_x, 0.001) * (width - 2 * margin)
        py = height - margin - (y - min_y) / max(max_y - min_y, 0.001) * (height - 2 * margin)
        return (int(round(px)), int(round(py)))

    for outline in state.get("room_outlines", []):
        center = outline["center"]
        half_x, half_y = outline["half_extents"]
        x1, y1 = project(float(center[0]) - float(half_x), float(center[1]) - float(half_y))
        x2, y2 = project(float(center[0]) + float(half_x), float(center[1]) + float(half_y))
        left, right = sorted((x1, x2))
        top, bottom = sorted((y1, y2))
        draw.rectangle((left, top, right, bottom), outline=(148, 163, 184), width=2)
        draw.text((left + 5, top + 5), str(outline.get("label", "room")), fill=(71, 85, 105))

    focus_receptacle_id = focus.get("receptacle_id")
    focus_object_id = focus.get("object_id")
    if focus_receptacle_id in state["receptacles"]:
        receptacle = state["receptacles"][focus_receptacle_id]
        x, y = project(float(receptacle["position"][0]), float(receptacle["position"][1]))
        draw.rounded_rectangle(
            (x - 13, y - 13, x + 13, y + 13),
            radius=5,
            outline=(8, 145, 178),
            width=4,
        )
        draw.text(
            (x + 10, y - 20),
            _item_label(receptacle, "receptacle_id"),
            fill=(8, 92, 116),
        )

    for receptacle in state["receptacles"].values():
        x, y = project(float(receptacle["position"][0]), float(receptacle["position"][1]))
        draw.rounded_rectangle((x - 5, y - 5, x + 5, y + 5), radius=2, fill=(99, 116, 139))

    for object_id in state["selected_object_ids"]:
        obj = state["objects"][object_id]
        x, y = project(float(obj["position"][0]), float(obj["position"][1]))
        draw.ellipse((x - 4, y - 4, x + 4, y + 4), fill=(192, 88, 68))
        if object_id == focus_object_id:
            draw.ellipse((x - 11, y - 11, x + 11, y + 11), outline=(220, 38, 38), width=4)
            draw.text((x + 10, y + 4), _item_label(obj, "object_id"), fill=(153, 27, 27))

    trajectory = state.get("robot_trajectory", [])
    projected_path = [project(float(pose["x"]), float(pose["y"])) for pose in trajectory]
    if len(projected_path) >= 2:
        draw.line(projected_path, fill=(37, 99, 235), width=3)
    for index, (x, y) in enumerate(projected_path):
        radius = 5 if index == len(projected_path) - 1 else 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(37, 99, 235))
    if trajectory:
        pose = trajectory[-1]
        x, y = projected_path[-1]
        heading = float(pose["theta"])
        tip = (int(round(x + math.cos(heading) * 18)), int(round(y - math.sin(heading) * 18)))
        left = (
            int(round(x + math.cos(heading + 2.45) * 10)),
            int(round(y - math.sin(heading + 2.45) * 10)),
        )
        right = (
            int(round(x + math.cos(heading - 2.45) * 10)),
            int(round(y - math.sin(heading - 2.45) * 10)),
        )
        draw.polygon([tip, left, right], fill=(15, 23, 42))

    draw.text((24, 22), "RBY1M map", fill=(31, 41, 55))
    draw.text(
        (24, height - 30),
        "blue: robot path  gray: receptacles  red: objects  cyan/red rings: focus",
        fill=(75, 85, 99),
    )
    return image


def _map_points(state: dict[str, Any], focus: dict[str, Any]) -> list[list[float]]:
    points = [item["position"] for item in state["receptacles"].values()]
    points += [state["objects"][oid]["position"] for oid in state["selected_object_ids"]]
    points += [[pose["x"], pose["y"], 0.0] for pose in state.get("robot_trajectory", [])]
    if focus.get("focus_position"):
        points.append(focus["focus_position"])
    for outline in state.get("room_outlines", []):
        center = outline["center"]
        half_x, half_y = outline["half_extents"]
        points.extend(
            [
                [float(center[0]) - float(half_x), float(center[1]) - float(half_y), 0.0],
                [float(center[0]) + float(half_x), float(center[1]) + float(half_y), 0.0],
            ]
        )
    return points


def _room_relation_payload(
    state: dict[str, Any],
    receptacle: dict[str, Any],
    robot_point: list[float],
) -> dict[str, Any]:
    target_room_id = _target_room_id(state, receptacle)
    robot_room_id = _room_for_point(state, robot_point)
    same_room = robot_room_id == target_room_id
    return {
        "target_room_id": target_room_id,
        "same_room_as_target": same_room,
        "room_relation_source": "mujoco_room_outline",
        "room_plausibility": "same_room" if same_room else "room_mismatch",
    }


def _target_room_id(state: dict[str, Any], receptacle: dict[str, Any]) -> str:
    return _room_for_point(state, receptacle["position"]) or str(
        receptacle.get("room_area") or "room_unknown"
    )


def _room_outline_for_id(
    state: dict[str, Any],
    room_id: Any,
) -> dict[str, Any] | None:
    if room_id is None:
        return None
    for outline in state.get("room_outlines", []):
        if outline.get("room_id") == room_id:
            return outline
    return None


def _room_for_point(state: dict[str, Any], point: list[float]) -> str | None:
    containing = [
        outline
        for outline in state.get("room_outlines", [])
        if _point_inside_outline(point, outline, margin=0.0)
    ]
    if not containing:
        return None
    return max(containing, key=lambda outline: _outline_clearance(point, outline)).get("room_id")


def _point_inside_outline(
    point: list[float],
    outline: dict[str, Any],
    *,
    margin: float,
) -> bool:
    center = outline["center"]
    half_x, half_y = outline["half_extents"]
    return (
        float(center[0]) - float(half_x) + margin
        <= float(point[0])
        <= float(center[0]) + float(half_x) - margin
        and float(center[1]) - float(half_y) + margin
        <= float(point[1])
        <= float(center[1]) + float(half_y) - margin
    )


def _outline_clearance(point: list[float], outline: dict[str, Any] | None) -> float:
    if outline is None:
        return 0.0
    center = outline["center"]
    half_x, half_y = outline["half_extents"]
    return min(
        float(point[0]) - (float(center[0]) - float(half_x)),
        (float(center[0]) + float(half_x)) - float(point[0]),
        float(point[1]) - (float(center[1]) - float(half_y)),
        (float(center[1]) + float(half_y)) - float(point[1]),
    )


def _angle_delta(a: float, b: float) -> float:
    return abs((a - b + math.pi) % math.tau - math.pi)


def _collect_room_outlines(
    model: mujoco.MjModel,
    data: mujoco.MjData,
    state: dict[str, Any],
) -> list[dict[str, Any]]:
    outlines: list[dict[str, Any]] = []
    seen: set[str] = set()
    for geom_id in range(model.ngeom):
        name = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, geom_id)
        if name is None:
            continue
        match = re.match(r"^(room_\d+)_visual", name)
        if match is None:
            continue
        room_id = match.group(1)
        if room_id in seen:
            continue
        size = [float(value) for value in model.geom_size[geom_id]]
        half_extents = sorted(size)[-2:]
        if half_extents[0] < 0.25 or half_extents[1] < 0.25:
            continue
        center = _xyz(data.geom_xpos[geom_id])
        outlines.append(
            {
                "room_id": room_id,
                "label": room_id.replace("_", " ").title(),
                "center": [center[0], center[1]],
                "half_extents": [round(half_extents[1], 6), round(half_extents[0], 6)],
                "provenance": "mujoco_room_geom",
            }
        )
        seen.add(room_id)
    if outlines:
        return sorted(outlines, key=lambda item: item["room_id"])
    return _fallback_room_outlines(state)


def _fallback_room_outlines(state: dict[str, Any]) -> list[dict[str, Any]]:
    grouped: dict[str, list[list[float]]] = {}
    for receptacle in state["receptacles"].values():
        grouped.setdefault(str(receptacle.get("room_area", "room_unknown")), []).append(
            receptacle["position"]
        )
    for obj in state["objects"].values():
        location_id = obj.get("seeded_start_receptacle_id") or obj.get("target_receptacle_id")
        receptacle = state["receptacles"].get(location_id)
        if receptacle is None:
            continue
        grouped.setdefault(str(receptacle.get("room_area", "room_unknown")), []).append(
            obj["position"]
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
                "provenance": "public_object_room_area_bounds",
            }
        )
    return sorted(outlines, key=lambda item: item["room_id"])


def _map_bounds(points: list[list[float]]) -> tuple[float, float, float, float]:
    if not points:
        return (0.0, 1.0, 0.0, 1.0)
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    pad = 0.8
    return (min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad)


def _apply_qpos(data: mujoco.MjData, qpos: list[float]) -> None:
    data.qpos[:] = qpos


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

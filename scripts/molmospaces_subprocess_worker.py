#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

import mujoco
from PIL import Image

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

    subparsers.add_parser("observe")
    subparsers.add_parser("scene_objects")
    subparsers.add_parser("locations")

    snapshot = subparsers.add_parser("snapshot")
    snapshot.add_argument("--output-path", type=Path, required=True)
    snapshot.add_argument("--title", default="")

    goto = subparsers.add_parser("goto")
    goto.add_argument("--receptacle-id", required=True)

    pick = subparsers.add_parser("pick")
    pick.add_argument("--object-id", required=True)

    place = subparsers.add_parser("place")
    place.add_argument("--receptacle-id", required=True)

    done = subparsers.add_parser("done")
    done.add_argument("--reason", default="")

    args = parser.parse_args(argv)
    if args.command == "init":
        result = init_state(
            state_path=args.state_path,
            seed=args.seed,
            scene_source=args.scene_source,
            scene_index=args.scene_index,
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
        elif args.command == "goto":
            result = goto_receptacle(state, args.receptacle_id)
            _write_state(args.state_path, state)
        elif args.command == "pick":
            result = pick_object(state, args.object_id)
            _write_state(args.state_path, state)
        elif args.command == "place":
            result = place_object(state, args.receptacle_id)
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
) -> dict[str, Any]:
    from molmo_spaces.molmo_spaces_constants import get_scenes_root
    from molmo_spaces.utils.lazy_loading_utils import install_scene_from_source_index
    from molmo_spaces.utils.scene_metadata_utils import get_scene_metadata

    install_scene_from_source_index(scene_source, scene_index)
    scene_xml = get_scenes_root() / scene_source / f"val_{scene_index}.xml"
    if not scene_xml.is_file():
        raise FileNotFoundError(scene_xml)

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
        "tool_event_counts": {},
    }
    _seed_misplaced_objects(model, data, state, targets)
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
    model, data = _load_model_data(Path(state["scene_xml"]))
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(frame).save(output_path)
    return _ok("snapshot", path=str(output_path), title=title, shape=list(frame.shape))


def goto_receptacle(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "goto")
    if receptacle_id not in state["receptacles"]:
        return _error("goto", "stale_reference", receptacle_id=receptacle_id)
    previous = state.get("current_receptacle_id")
    state["current_receptacle_id"] = receptacle_id
    return _ok(
        "goto",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        receptacle_id=receptacle_id,
        previous_receptacle_id=previous,
        state_mutation="agent_pose_semantic",
        backend=BACKEND,
    )


def pick_object(state: dict[str, Any], object_id: str) -> dict[str, Any]:
    _count(state, "pick")
    if object_id not in state["objects"]:
        return _error("pick", "stale_reference", object_id=object_id)
    if state.get("held_object_id") is not None:
        return _error("pick", "already_holding", held_object_id=state["held_object_id"])
    locations = _read_locations(state)
    state["held_object_id"] = object_id
    return _ok(
        "pick",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        previous_location_id=locations.get(object_id),
        location_id=HELD_LOCATION_ID,
        state_mutation="held_state_only",
        backend=BACKEND,
    )


def place_object(state: dict[str, Any], receptacle_id: str) -> dict[str, Any]:
    _count(state, "place")
    if receptacle_id not in state["receptacles"]:
        return _error("place", "stale_reference", receptacle_id=receptacle_id)
    object_id = state.get("held_object_id")
    if object_id is None:
        return _error("place", "not_holding")

    model, data = _load_model_data(Path(state["scene_xml"]))
    _apply_qpos(data, state["qpos"])
    obj = state["objects"][object_id]
    receptacle = state["receptacles"][receptacle_id]
    target_position = _placement_position(
        receptacle,
        index=state["selected_object_ids"].index(object_id),
    )
    _set_free_body_position(model, data, obj["body_name"], target_position)
    mujoco.mj_forward(model, data)

    state["qpos"] = [float(value) for value in data.qpos]
    state["held_object_id"] = None
    state["current_receptacle_id"] = receptacle_id
    final_locations = _read_locations(state)
    return _ok(
        "place",
        primitive_provenance=API_SEMANTIC_PROVENANCE,
        object_id=object_id,
        receptacle_id=receptacle_id,
        location_id=final_locations.get(object_id),
        mujoco_body_name=obj["body_name"],
        qpos_changed=True,
        state_mutation="mujoco_freejoint_qpos",
        backend=BACKEND,
    )


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
            _placement_position(wrong, index=index),
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
    model, data = _load_model_data(Path(state["scene_xml"]))
    _apply_qpos(data, state["qpos"])
    mujoco.mj_forward(model, data)
    receptacles = list(state["receptacles"].values())
    locations = {}
    for object_id in state["selected_object_ids"]:
        obj = state["objects"][object_id]
        body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, obj["body_name"])
        if body_id < 0:
            continue
        locations[object_id] = _nearest_receptacle(_xyz(data.xpos[body_id]), receptacles)
    return locations


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


def _placement_position(receptacle: dict[str, Any], *, index: int) -> list[float]:
    base = receptacle["position"]
    offset = ((index % 3) - 1) * 0.12
    return [float(base[0]) + offset, float(base[1]) + 0.08 * (index % 2), float(base[2]) + 0.35]


def _load_model_data(scene_xml: Path) -> tuple[mujoco.MjModel, mujoco.MjData]:
    model = mujoco.MjModel.from_xml_path(str(scene_xml))
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    return model, data


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

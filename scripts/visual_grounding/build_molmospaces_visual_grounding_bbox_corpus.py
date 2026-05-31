#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.visual_grounding.build_visual_grounding_corpus_from_cleanup_run import (  # noqa: E402
    CORPUS_SCHEMA,
    DEFAULT_CATEGORY_FAMILY_MAP,
    VISUAL_GROUNDING_CATEGORY_HINTS,
    _category_family,
)

DEFAULT_SCENE_SOURCE = "procthor-10k-val"
DEFAULT_SCENE_INDICES = "0-9"
DEFAULT_SEED = 7
DEFAULT_TARGETS_PER_SCENE = 10
DEFAULT_MIN_VISIBLE_PIXELS = 20
FRAME_CLASS_TARGET_FOCUSED = "target_focused_fpv"
FRAME_CLASS_SWEEP = "sweep_fpv"
SUPPORTED_FRAME_CLASSES = {FRAME_CLASS_TARGET_FOCUSED, FRAME_CLASS_SWEEP}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a fresh MolmoSpaces visual-grounding corpus with private "
            "MuJoCo segmentation bbox labels."
        )
    )
    parser.add_argument("--output", type=Path, required=True, help="Output corpus JSON path.")
    parser.add_argument("--name", default="molmospaces-bbox-target-focused")
    parser.add_argument("--scene-source", default=DEFAULT_SCENE_SOURCE)
    parser.add_argument(
        "--scene-indices",
        default=DEFAULT_SCENE_INDICES,
        help="Comma-separated scene indices and ranges, e.g. 0-9,12.",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--targets-per-scene",
        type=int,
        default=DEFAULT_TARGETS_PER_SCENE,
        help="Cleanup targets to sample per scene.",
    )
    parser.add_argument(
        "--generated-mess-count",
        type=int,
        default=0,
        help="Generated mess count passed to MolmoSpaces; defaults to targets per scene.",
    )
    parser.add_argument(
        "--frame-classes",
        default=FRAME_CLASS_TARGET_FOCUSED,
        help=(
            "Comma-separated frame classes. Supported: "
            f"{', '.join(sorted(SUPPORTED_FRAME_CLASSES))}."
        ),
    )
    parser.add_argument(
        "--min-visible-pixels",
        type=int,
        default=DEFAULT_MIN_VISIBLE_PIXELS,
        help="Minimum segmented target pixels required for a private bbox label.",
    )
    parser.add_argument(
        "--include-invisible",
        action="store_true",
        help="Keep observations without a visible target bbox as negative/weak-visibility rows.",
    )
    parser.add_argument(
        "--molmospaces-python",
        type=Path,
        default=None,
        help="Python executable for the MolmoSpaces subprocess worker.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    output_path = args.output
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    scene_indices = parse_scene_indices(args.scene_indices)
    frame_classes = parse_frame_classes(args.frame_classes)
    generated_mess_count = args.generated_mess_count or args.targets_per_scene
    observations: list[dict[str, Any]] = []
    scene_summaries: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for scene_index in scene_indices:
        try:
            scene_observations, scene_summary = generate_scene_observations(
                output_dir=output_dir,
                scene_source=args.scene_source,
                scene_index=scene_index,
                seed=args.seed,
                targets_per_scene=args.targets_per_scene,
                generated_mess_count=generated_mess_count,
                frame_classes=frame_classes,
                min_visible_pixels=args.min_visible_pixels,
                include_invisible=args.include_invisible,
                molmospaces_python=args.molmospaces_python,
            )
        except Exception as exc:  # pragma: no cover - exercised by local runtime failures
            errors.append(
                {
                    "scene_index": scene_index,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            continue
        observations.extend(scene_observations)
        scene_summaries.append(scene_summary)

    if not observations:
        raise SystemExit(
            "no MolmoSpaces bbox observations were generated; "
            f"scene errors: {json.dumps(errors, sort_keys=True)}"
        )

    observations = _renumber_observations(observations)
    corpus = {
        "schema": CORPUS_SCHEMA,
        "name": args.name,
        "description": (
            "Fresh MolmoSpaces perception-only visual-grounding corpus. Public "
            "requests use only image bytes, category hints, fixture hints, and "
            "capture context; private bbox labels are MuJoCo segmentation truth "
            "for benchmark scoring only."
        ),
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "scene_source": args.scene_source,
        "label_source": "private_mujoco_segmentation_bbox",
        "category_family_map": DEFAULT_CATEGORY_FAMILY_MAP,
        "sampling": sampling_summary(
            observations=observations,
            scene_indices=scene_indices,
            frame_classes=frame_classes,
            targets_per_scene=args.targets_per_scene,
            generated_mess_count=generated_mess_count,
            min_visible_pixels=args.min_visible_pixels,
            include_invisible=args.include_invisible,
            scene_summaries=scene_summaries,
            errors=errors,
        ),
        "observations": observations,
    }
    output_path.write_text(json.dumps(corpus, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"MolmoSpaces bbox visual-grounding corpus: {output_path}")
    print(f"observations: {len(observations)}")
    print(f"scenes completed: {len(scene_summaries)} / {len(scene_indices)}")
    print(f"scene errors: {len(errors)}")
    return 0


def generate_scene_observations(
    *,
    output_dir: Path,
    scene_source: str,
    scene_index: int,
    seed: int,
    targets_per_scene: int,
    generated_mess_count: int,
    frame_classes: list[str],
    min_visible_pixels: int,
    include_invisible: bool,
    molmospaces_python: Path | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    from roboclaws.molmo_cleanup.subprocess_backend import MolmoSpacesSubprocessBackend

    scene_run_dir = output_dir / "_molmospaces_bbox_runs" / f"scene_{scene_index}_seed_{seed}"
    scene_run_dir.mkdir(parents=True, exist_ok=True)
    backend = MolmoSpacesSubprocessBackend(
        run_dir=scene_run_dir,
        seed=seed,
        python_executable=molmospaces_python,
        scene_source=scene_source,
        scene_index=scene_index,
        include_robot=True,
        generated_mess_count=generated_mess_count,
    )
    try:
        scenario = backend.scenario
        objects_by_id = {item.object_id: item for item in scenario.objects}
        receptacles_by_id = {item.receptacle_id: item for item in scenario.receptacles}
        fixture_hints_by_room = public_fixture_hints_by_room(scenario)
        observations: list[dict[str, Any]] = []
        skipped: list[dict[str, Any]] = []
        targets = list(scenario.private_manifest.targets)[:targets_per_scene]
        views_dir = output_dir / "molmospaces_fpv_frames" / f"scene_{scene_index}_seed_{seed}"
        for target_index, target in enumerate(targets, start=1):
            object_id = target.object_id
            target_receptacle_id = (
                target.valid_receptacle_ids[0] if target.valid_receptacle_ids else ""
            )
            obj = objects_by_id.get(object_id)
            source_receptacle = receptacles_by_id.get(obj.location_id) if obj is not None else None
            if obj is None:
                skipped.append(
                    {
                        "object_id": object_id,
                        "reason": "target_object_missing_from_public_scenario",
                    }
                )
                continue
            for frame_class in frame_classes:
                if frame_class == FRAME_CLASS_TARGET_FOCUSED:
                    backend.navigate_to_object(object_id)
                view_label = (
                    f"scene_{scene_index}_seed_{seed}_target_{target_index:03d}_{frame_class}"
                )
                view_result = backend.write_robot_views(
                    views_dir,
                    label=view_label,
                    focus_object_id=object_id,
                    focus_receptacle_id=target_receptacle_id or None,
                )
                observation = observation_from_robot_view(
                    output_dir=output_dir,
                    view_result=view_result,
                    scene_source=scene_source,
                    scene_index=scene_index,
                    seed=seed,
                    target_index=target_index,
                    frame_class=frame_class,
                    obj=obj.to_public_dict(),
                    source_receptacle=source_receptacle.to_public_dict()
                    if source_receptacle is not None
                    else {},
                    fixture_hints_by_room=fixture_hints_by_room,
                    min_visible_pixels=min_visible_pixels,
                    include_invisible=include_invisible,
                )
                if observation is None:
                    skipped.append(
                        {
                            "object_id": object_id,
                            "target_index": target_index,
                            "frame_class": frame_class,
                            "reason": "target_bbox_not_visible",
                        }
                    )
                    continue
                observations.append(observation)
        return observations, {
            "scene_index": scene_index,
            "requested_target_count": targets_per_scene,
            "generated_mess_count": backend.generated_mess_count,
            "exported_observation_count": len(observations),
            "skipped_observation_count": len(skipped),
            "skipped": skipped,
        }
    finally:
        backend.close()


def observation_from_robot_view(
    *,
    output_dir: Path,
    view_result: dict[str, Any],
    scene_source: str,
    scene_index: int,
    seed: int,
    target_index: int,
    frame_class: str,
    obj: dict[str, Any],
    source_receptacle: dict[str, Any],
    fixture_hints_by_room: dict[str, list[dict[str, Any]]],
    min_visible_pixels: int,
    include_invisible: bool,
) -> dict[str, Any] | None:
    if view_result.get("status") != "ok":
        return None
    views = view_result.get("views") or {}
    image_path = Path(str(views.get("fpv") or ""))
    if not image_path.is_file():
        return None
    width, height = image_dimensions(image_path)
    focus = view_result.get("focus") or {}
    visibility = focus.get("fpv_visibility") or {}
    object_box = object_box_from_visibility(visibility)
    private_label = private_label_from_object_box(
        object_box=object_box,
        obj=obj,
        width=width,
        height=height,
        min_visible_pixels=min_visible_pixels,
        scene_source=scene_source,
        scene_index=scene_index,
        seed=seed,
        target_index=target_index,
        frame_class=frame_class,
        camera="robot_0/head_camera",
    )
    if private_label is None and not include_invisible:
        return None

    room_id = str(_room_id_for_object(obj, source_receptacle) or "")
    observation_id = (
        f"molmo_scene_{scene_index}_seed_{seed}_target_{target_index:03d}_{frame_class}"
    )
    capture_context = {
        "discovered_during": "molmospaces_visual_grounding_corpus_builder",
        "scene_source": scene_source,
        "scene_index": scene_index,
        "seed": seed,
        "target_index": target_index,
        "frame_class": frame_class,
        "camera": "robot_0/head_camera",
        "view_variant": str(view_result.get("view_variant") or ""),
        "view_provenance": dict(view_result.get("view_provenance") or {}),
        "robot_pose": public_robot_pose(view_result.get("robot_pose") or {}),
        "visibility_status": str(visibility.get("status") or ""),
    }
    private_labels = [private_label] if private_label is not None else []
    if private_label is None:
        capture_context["weak_visibility_reason"] = "target_bbox_not_visible"
    return {
        "observation_id": observation_id,
        "waypoint_id": f"scene_{scene_index}_target_{target_index:03d}",
        "room_id": room_id,
        "capture_context": capture_context,
        "category_hints": list(VISUAL_GROUNDING_CATEGORY_HINTS),
        "fixture_hints": fixture_hints_by_room.get(room_id, []),
        "image": {
            "source": "path",
            "path": str(_relative_path(image_path, output_dir)),
            "width": width,
            "height": height,
        },
        "private_labels": private_labels,
    }


def private_label_from_object_box(
    *,
    object_box: dict[str, Any] | None,
    obj: dict[str, Any],
    width: int,
    height: int,
    min_visible_pixels: int,
    scene_source: str,
    scene_index: int,
    seed: int,
    target_index: int,
    frame_class: str,
    camera: str,
) -> dict[str, Any] | None:
    if object_box is None:
        return None
    visible_pixels = int(object_box.get("pixels") or 0)
    if visible_pixels < min_visible_pixels:
        return None
    xyxy = [int(value) for value in object_box.get("bbox") or []]
    if len(xyxy) != 4:
        return None
    category = str(obj.get("category") or "")
    family = _category_family(category) or category.lower()
    return {
        "label_source": "private_mujoco_segmentation_bbox",
        "visibility_source": "fpv_visibility",
        "object_id": str(obj.get("object_id") or ""),
        "object_category": category,
        "category": family,
        "category_family": family,
        "bbox": normalized_xywh_bbox(xyxy, width=width, height=height),
        "bbox_xyxy_pixels": xyxy,
        "visible_pixels": visible_pixels,
        "visible": True,
        "bbox_source": str(object_box.get("source") or "segmentation"),
        "scene_source": scene_source,
        "scene_index": scene_index,
        "seed": seed,
        "target_index": target_index,
        "frame_class": frame_class,
        "camera": camera,
        "image_width": width,
        "image_height": height,
    }


def object_box_from_visibility(visibility: dict[str, Any]) -> dict[str, Any] | None:
    boxes = [box for box in visibility.get("boxes") or [] if isinstance(box, dict)]
    if not boxes:
        return None
    object_boxes = [
        box for box in boxes if [int(value) for value in box.get("color") or []] == [239, 68, 68]
    ]
    if object_boxes:
        return max(object_boxes, key=lambda box: int(box.get("pixels") or 0))
    return max(boxes, key=lambda box: int(box.get("pixels") or 0))


def normalized_xywh_bbox(xyxy: list[int], *, width: int, height: int) -> list[float]:
    left, top, right, bottom = xyxy
    x = max(0.0, min(1.0, left / width))
    y = max(0.0, min(1.0, top / height))
    w = max(0.0, min(1.0 - x, (right - left) / width))
    h = max(0.0, min(1.0 - y, (bottom - top) / height))
    return [round(x, 6), round(y, 6), round(w, 6), round(h, 6)]


def public_fixture_hints_by_room(scenario: Any) -> dict[str, list[dict[str, Any]]]:
    output: dict[str, list[dict[str, Any]]] = {}
    for receptacle in scenario.receptacles:
        public = receptacle.to_public_dict()
        room_id = str(public.get("room_area") or "")
        hint = {
            "fixture_id": str(public.get("receptacle_id") or ""),
            "room_id": room_id,
            "category": str(public.get("category") or public.get("kind") or ""),
            "name": str(public.get("name") or ""),
            "affordances": _fixture_affordances(public),
        }
        output.setdefault(room_id, []).append(hint)
    return output


def public_robot_pose(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    allowed = (
        "x",
        "y",
        "z",
        "theta",
        "head_pitch",
        "head_yaw",
        "robot_room_id",
        "room_plausibility",
        "room_relation_source",
        "same_room_as_target",
    )
    return {key: value[key] for key in allowed if key in value}


def sampling_summary(
    *,
    observations: list[dict[str, Any]],
    scene_indices: list[int],
    frame_classes: list[str],
    targets_per_scene: int,
    generated_mess_count: int,
    min_visible_pixels: int,
    include_invisible: bool,
    scene_summaries: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    private_label_count = sum(len(item.get("private_labels") or []) for item in observations)
    visible_private_label_count = sum(
        1
        for item in observations
        for label in item.get("private_labels") or []
        if label.get("visible")
    )
    return {
        "requested_scene_indices": scene_indices,
        "completed_scene_indices": [int(item["scene_index"]) for item in scene_summaries],
        "failed_scene_count": len(errors),
        "scene_errors": errors,
        "frame_classes": frame_classes,
        "targets_per_scene": targets_per_scene,
        "generated_mess_count": generated_mess_count,
        "min_visible_pixels": min_visible_pixels,
        "include_invisible": include_invisible,
        "observation_count": len(observations),
        "private_bbox_label_count": private_label_count,
        "visible_private_bbox_label_count": visible_private_label_count,
        "frame_class_distribution": dict(
            sorted(
                Counter(
                    str((item.get("capture_context") or {}).get("frame_class") or "")
                    for item in observations
                ).items()
            )
        ),
        "scene_distribution": dict(
            sorted(
                Counter(
                    _string_value((item.get("capture_context") or {}).get("scene_index"))
                    for item in observations
                ).items()
            )
        ),
        "category_family_distribution": dict(
            sorted(
                Counter(
                    str(label.get("category_family") or label.get("category") or "")
                    for item in observations
                    for label in item.get("private_labels") or []
                ).items()
            )
        ),
        "scene_summaries": scene_summaries,
    }


def parse_scene_indices(value: str) -> list[int]:
    indices: list[int] = []
    seen: set[int] = set()
    for part in str(value).split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            left, right = part.split("-", maxsplit=1)
            start = int(left)
            end = int(right)
            step = 1 if end >= start else -1
            values = range(start, end + step, step)
        else:
            values = [int(part)]
        for item in values:
            if item not in seen:
                indices.append(item)
                seen.add(item)
    if not indices:
        raise SystemExit("scene index list is empty")
    return indices


def parse_frame_classes(value: str) -> list[str]:
    classes = [part.strip() for part in str(value).split(",") if part.strip()]
    invalid = [item for item in classes if item not in SUPPORTED_FRAME_CLASSES]
    if invalid:
        raise SystemExit(f"unsupported frame class: {', '.join(invalid)}")
    return classes or [FRAME_CLASS_TARGET_FOCUSED]


def image_dimensions(path: Path) -> tuple[int, int]:
    with Image.open(path) as image:
        return int(image.width), int(image.height)


def _renumber_observations(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output = []
    for index, observation in enumerate(observations, start=1):
        item = dict(observation)
        original_id = str(item.get("observation_id") or "")
        item["observation_id"] = f"molmo_vg_{index:04d}"
        capture_context = dict(item.get("capture_context") or {})
        capture_context["source_observation_id"] = original_id
        item["capture_context"] = capture_context
        output.append(item)
    return output


def _relative_path(path: Path, base_dir: Path) -> Path:
    try:
        return path.relative_to(base_dir)
    except ValueError:
        return path


def _room_id_for_object(obj: dict[str, Any], receptacle: dict[str, Any]) -> str:
    if receptacle.get("room_area"):
        return str(receptacle["room_area"])
    location_id = str(obj.get("location_id") or "")
    match = re.search(r"room[_-]?\d+", location_id)
    return match.group(0) if match else ""


def _fixture_affordances(public: dict[str, Any]) -> list[str]:
    category = str(public.get("category") or public.get("name") or "").lower()
    if "fridge" in category:
        return ["inside", "openable"]
    if "sink" in category:
        return ["inside"]
    return ["surface"]


def _string_value(value: Any) -> str:
    return "" if value is None else str(value)


if __name__ == "__main__":
    raise SystemExit(main())

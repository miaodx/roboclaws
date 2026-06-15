from __future__ import annotations

import copy
import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_CANDIDATE,
    ALIGNMENT_STATUS_NATIVE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_rooms,
    source_frame_spatial_contract,
)

ROOM_SEMANTIC_OVERLAY_SCHEMA = "scene_room_semantic_overlay_v1"
SCENE_MAP_CORRESPONDENCE_SCHEMA = "scene_map_correspondence_v1"

_PARTITION_RE = re.compile(r'over\s+"([^"]+)"')
_INSTANCE_SUFFIX_RE = re.compile(r"(?:_\d+)+$")

_CATEGORY_LABELS = {
    "kitchen": "Open kitchen",
    "living_room": "Living room",
    "reception_area": "Lobby / reception area",
    "meeting_room": "Meeting room",
    "corridor": "Corridor",
    "storage_room": "Storage room",
    "room_area": "Room area",
}

_CATEGORY_TERMS = {
    "kitchen": ("kitchen", "bar", "counter", "sink", "fridge", "oven", "stove", "cook"),
    "living_room": ("living", "lounge", "sofa", "coffee_table"),
    "reception_area": ("reception", "lobby", "front_desk"),
    "meeting_room": ("meeting", "conference"),
    "corridor": ("corridor", "hallway", "hall"),
    "storage_room": ("storage", "store", "utility", "closet"),
}

_OBJECT_CATEGORY_TERMS = {
    "kitchen": ("sink", "fridge", "counter", "oven", "stove", "microwave"),
    "living_room": ("sofa", "coffee_table", "tv_closet", "speaker", "plant"),
    "reception_area": ("sofa", "desk", "plant", "fire_extinguisher", "tv_closet", "speaker"),
    "meeting_room": ("conference_table", "meeting_table", "whiteboard"),
    "corridor": ("corridor",),
    "storage_room": ("storage", "black_machine", "trash_bin"),
}

_REVIEW_CATEGORIES = {"room_area"}


def build_scene_room_semantic_overlay(
    scene_root: str | Path,
    *,
    source_bundle_dir: str | Path | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    scene_root = Path(scene_root)
    partitions = _scene_partitions(scene_root)
    object_index = _object_index(scene_root)
    override_rooms = _override_rooms(overrides)
    correspondence = _scene_map_correspondence(overrides)
    rooms: list[dict[str, Any]] = []
    for partition_id in partitions:
        objects = object_index.get(partition_id, Counter())
        override = override_rooms.get(partition_id, {})
        room = _room_from_partition(partition_id, objects, override=override)
        rooms.append(room)

    navigation_rooms = _navigation_rooms(source_bundle_dir)
    rooms = _attach_scene_map_correspondence(
        rooms,
        navigation_rooms,
        correspondence=correspondence,
    )
    overlay = {
        "schema": ROOM_SEMANTIC_OVERLAY_SCHEMA,
        "scene_root": str(scene_root),
        "source_bundle_dir": str(source_bundle_dir or ""),
        "scene_map_correspondence_schema": SCENE_MAP_CORRESPONDENCE_SCHEMA,
        "scene_map_correspondence_v1": correspondence,
        "producer": {
            "type": "scene_engine_asset_room_semantic_overlay",
            "method": "partition_and_object_name_heuristics",
            "uses_rendered_review": False,
        },
        "rooms": rooms,
        "room_category_hints": _room_category_hints(rooms),
        "review_queue": [
            _review_item(room)
            for room in rooms
            if room.get("review_status") in {"needs_review", "render_review_recommended"}
        ],
        "summary": {
            "room_count": len(rooms),
            "review_count": sum(
                1
                for room in rooms
                if room.get("review_status") in {"needs_review", "render_review_recommended"}
            ),
            "categories": dict(Counter(str(room.get("category") or "") for room in rooms)),
        },
        "public_contract_note": (
            "This overlay maps scene-engine asset partitions into public room semantic "
            "labels. Folder and USD prim names are evidence, not private evaluator truth."
        ),
    }
    return overlay


def apply_room_semantic_overlay_to_bundle(
    source_bundle_dir: str | Path,
    output_bundle_dir: str | Path,
    overlay: dict[str, Any],
    *,
    validate: bool = True,
) -> dict[str, Any]:
    source_bundle_dir = Path(source_bundle_dir)
    output_bundle_dir = Path(output_bundle_dir)
    if output_bundle_dir.exists():
        shutil.rmtree(output_bundle_dir)
    shutil.copytree(source_bundle_dir, output_bundle_dir)
    semantics_path = output_bundle_dir / "semantics.json"
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    frame_id = str((semantics.get("frame_ids") or {}).get("map") or "map")
    fallback_rooms = normalize_spatial_rooms(
        semantics.get("rooms") or [],
        frame_id=frame_id,
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        alignment_status=ALIGNMENT_STATUS_NATIVE,
    )
    rooms = _rooms_for_semantics(overlay, fallback_rooms=fallback_rooms, frame_id=frame_id)
    room_by_navigation_area = {
        str(room.get("navigation_area_id") or ""): str(room.get("room_id") or "")
        for room in rooms
        if str(room.get("navigation_area_id") or "") and str(room.get("room_id") or "")
    }
    waypoints = _retarget_waypoints(
        semantics.get("inspection_waypoints") or [],
        room_by_navigation_area=room_by_navigation_area,
    )
    semantics["rooms"] = rooms
    semantics["spatial_contract"] = source_frame_spatial_contract(
        frame_id=frame_id,
        alignment_status=ALIGNMENT_STATUS_CANDIDATE,
    )
    semantics["display_frame"] = None
    semantics["room_category_hints"] = _room_category_hints(rooms)
    semantics["inspection_waypoints"] = waypoints
    semantics["driveable_ways"] = _driveable_ways(rooms, semantics.get("driveable_ways") or [])
    provenance = (
        semantics.get("provenance") if isinstance(semantics.get("provenance"), dict) else {}
    )
    semantics["provenance"] = {
        **provenance,
        "room_semantic_overlay_schema": overlay.get("schema"),
        "room_semantic_overlay_source": overlay.get("scene_root", ""),
        "room_semantic_overlay_producer": (overlay.get("producer") or {}).get("type", ""),
        "scene_map_correspondence_schema": overlay.get("scene_map_correspondence_schema", ""),
        "contains_runtime_observations": False,
        "contains_private_scoring_truth": False,
    }
    semantics_path.write_text(
        json.dumps(semantics, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    validation = validate_nav2_map_bundle(output_bundle_dir)
    if validate:
        validation.raise_for_errors()
    return {
        "schema": "scene_room_semantic_overlay_bundle_application_v1",
        "source_bundle_dir": str(source_bundle_dir),
        "output_bundle_dir": str(output_bundle_dir),
        "overlay_schema": overlay.get("schema"),
        "room_count": len(rooms),
        "validation": validation.as_dict(),
    }


def _scene_partitions(scene_root: Path) -> list[str]:
    if not scene_root.is_dir():
        raise FileNotFoundError(f"scene root does not exist: {scene_root}")
    partitions = []
    for path in sorted(item for item in scene_root.iterdir() if item.is_dir()):
        if path.name == "storey_1":
            continue
        if (path / "scene.usd").is_file() or (path / "scene_gs.usda").is_file():
            partitions.append(path.name)
    if not partitions:
        raise ValueError(f"no scene-engine room partitions found under {scene_root}")
    return partitions


def _object_index(scene_root: Path) -> dict[str, Counter[str]]:
    index: dict[str, Counter[str]] = defaultdict(Counter)
    for path in sorted(scene_root.glob("*/scene_gs.usda")):
        text = path.read_text(encoding="utf-8", errors="ignore")
        for name in _PARTITION_RE.findall(text):
            if "__" not in name:
                continue
            partition_id, raw_object = name.split("__", 1)
            if partition_id == "storey_1":
                continue
            object_name = _INSTANCE_SUFFIX_RE.sub("", raw_object)
            object_name = re.sub(r"__.*$", "", object_name)
            if object_name:
                index[partition_id][object_name] += 1
    return index


def _override_rooms(overrides: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not overrides:
        return {}
    raw_rooms = overrides.get("rooms") if isinstance(overrides.get("rooms"), list) else []
    output = {}
    for item in raw_rooms:
        if not isinstance(item, dict):
            continue
        partition_id = str(item.get("asset_partition_id") or item.get("room_id") or "")
        if partition_id:
            output[partition_id] = item
    return output


def _room_from_partition(
    partition_id: str,
    objects: Counter[str],
    *,
    override: dict[str, Any],
) -> dict[str, Any]:
    category, evidence, confidence, conflict, weak_evidence = _infer_category(partition_id, objects)
    category = str(override.get("category") or category)
    room_label = str(override.get("room_label") or _room_label(partition_id, category))
    confidence = float(override.get("confidence") or confidence)
    review_status = str(
        override.get("review_status")
        or _review_status(category, confidence, conflict=conflict, weak_evidence=weak_evidence)
    )
    room = {
        "room_id": str(override.get("room_id") or partition_id),
        "room_label": room_label,
        "category": category,
        "asset_partition_id": partition_id,
        "semantic_source": str(
            override.get("semantic_source") or "scene_engine_asset_name_heuristic"
        ),
        "classification_status": str(override.get("classification_status") or "map_prior"),
        "confidence": round(confidence, 3),
        "review_status": review_status,
        "render_review_recommended": review_status != "accepted",
        "evidence": {
            "partition_name": partition_id,
            "object_name_counts": dict(objects.most_common()),
            "matched_terms": evidence,
            "conflicting_evidence": conflict,
            "weak_evidence": weak_evidence,
            "artifacts": list(override.get("evidence_artifacts") or []),
        },
        "aliases": _aliases(partition_id, room_label, category),
    }
    for key in ("polygon", "map_center", "navigation_area_id"):
        if key in override:
            room[key] = copy.deepcopy(override[key])
    for key in (
        "polygon_role",
        "geometry_source",
        "alignment_status",
        "source_map_frame_id",
        "polygon_usage",
        "scene_map_correspondence",
    ):
        if key in override:
            room[key] = copy.deepcopy(override[key])
    return room


def _infer_category(
    partition_id: str,
    objects: Counter[str],
) -> tuple[str, list[str], float, list[str], bool]:
    text = partition_id.lower()
    scores: Counter[str] = Counter()
    evidence: defaultdict[str, list[str]] = defaultdict(list)
    for category, terms in _CATEGORY_TERMS.items():
        for term in terms:
            if term in text:
                scores[category] += 4
                evidence[category].append(f"partition:{term}")
    object_names = " ".join(objects)
    for category, terms in _OBJECT_CATEGORY_TERMS.items():
        for term in terms:
            if term in object_names:
                scores[category] += 1
                evidence[category].append(f"object:{term}")
    if not scores:
        return "room_area", [], 0.35, [], True
    category, score = scores.most_common(1)[0]
    confidence = min(0.95, 0.55 + score * 0.08)
    conflicts = [
        f"{other}:{','.join(evidence[other])}"
        for other, other_score in scores.items()
        if other != category and other_score >= 2
    ]
    if conflicts:
        confidence = min(confidence, 0.72)
    object_evidence = [item for item in evidence[category] if item.startswith("object:")]
    partition_evidence = [item for item in evidence[category] if item.startswith("partition:")]
    weak_evidence = bool(partition_evidence and not object_evidence)
    if weak_evidence:
        confidence = min(confidence, 0.68)
    return category, evidence[category], confidence, conflicts, weak_evidence


def _room_label(partition_id: str, category: str) -> str:
    base = _CATEGORY_LABELS.get(category, _CATEGORY_LABELS["room_area"])
    suffix = partition_id.rsplit("_", 1)[-1].upper() if "_" in partition_id else ""
    if category in {"meeting_room", "room_area"} and suffix:
        return f"{base} {suffix}"
    return base


def _review_status(
    category: str,
    confidence: float,
    *,
    conflict: list[str],
    weak_evidence: bool,
) -> str:
    if conflict:
        return "render_review_recommended"
    if weak_evidence:
        return "render_review_recommended"
    if category in _REVIEW_CATEGORIES or confidence < 0.65:
        return "render_review_recommended"
    return "accepted"


def _aliases(partition_id: str, room_label: str, category: str) -> list[str]:
    aliases = [partition_id, partition_id.replace("_", " "), room_label, category]
    return list(dict.fromkeys(item for item in aliases if item))


def _navigation_rooms(source_bundle_dir: str | Path | None) -> list[dict[str, Any]]:
    if not source_bundle_dir:
        return []
    semantics_path = Path(source_bundle_dir) / "semantics.json"
    if not semantics_path.is_file():
        return []
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    return [dict(item) for item in semantics.get("rooms") or [] if isinstance(item, dict)]


def _scene_map_correspondence(overrides: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not overrides:
        return []
    raw = overrides.get(SCENE_MAP_CORRESPONDENCE_SCHEMA)
    if raw is None:
        raw = overrides.get("scene_map_correspondence")
    if not isinstance(raw, list):
        return []
    output: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        asset_partition_id = str(item.get("asset_partition_id") or "")
        navigation_area_id = str(item.get("navigation_area_id") or "")
        if not asset_partition_id or not navigation_area_id:
            continue
        output.append(
            {
                "asset_partition_id": asset_partition_id,
                "navigation_area_id": navigation_area_id,
                "alignment_status": str(item.get("alignment_status") or ALIGNMENT_STATUS_CANDIDATE),
                "transform_source": str(item.get("transform_source") or "operator_review"),
                "evidence_artifacts": list(item.get("evidence_artifacts") or []),
                **(
                    {"geometry_source": str(item["geometry_source"])}
                    if "geometry_source" in item
                    else {}
                ),
                **(
                    {"map_polygon": copy.deepcopy(item["map_polygon"])}
                    if "map_polygon" in item
                    else {}
                ),
            }
        )
    return output


def _attach_scene_map_correspondence(
    rooms: list[dict[str, Any]],
    navigation_rooms: list[dict[str, Any]],
    *,
    correspondence: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not correspondence:
        return rooms
    navigation_by_id = {str(room.get("room_id") or ""): room for room in navigation_rooms}
    correspondence_by_partition = {
        str(item.get("asset_partition_id") or ""): item for item in correspondence
    }
    output = []
    for room in rooms:
        item = dict(room)
        match = correspondence_by_partition.get(str(item.get("asset_partition_id") or ""))
        if not match:
            output.append(item)
            continue
        navigation_area_id = str(match.get("navigation_area_id") or "")
        nav_room = navigation_by_id.get(navigation_area_id, {})
        item["navigation_area_id"] = navigation_area_id
        polygon = match.get("map_polygon")
        if polygon is None:
            polygon = nav_room.get("polygon") or []
        item["polygon"] = copy.deepcopy(polygon)
        if "map_center" not in item:
            item["map_center"] = _polygon_center(item.get("polygon") or [])
        item["polygon_role"] = POLYGON_ROLE_NAVIGATION_AREA
        item["geometry_source"] = str(
            match.get("geometry_source") or GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE
        )
        item["alignment_status"] = str(match.get("alignment_status") or ALIGNMENT_STATUS_CANDIDATE)
        item["source_map_frame_id"] = str(nav_room.get("source_map_frame_id") or "map")
        item["polygon_usage"] = {
            "navigation": True,
            "semantic_labeling": item["alignment_status"],
            "review": True,
        }
        item["scene_map_correspondence"] = {
            "schema": SCENE_MAP_CORRESPONDENCE_SCHEMA,
            "asset_partition_id": str(match.get("asset_partition_id") or ""),
            "navigation_area_id": navigation_area_id,
            "alignment_status": item["alignment_status"],
            "transform_source": str(match.get("transform_source") or ""),
            "evidence_artifacts": list(match.get("evidence_artifacts") or []),
            "map_polygon_provided": "map_polygon" in match,
        }
        output.append(item)
    return output


def _rooms_for_semantics(
    overlay: dict[str, Any],
    *,
    fallback_rooms: list[dict[str, Any]],
    frame_id: str,
) -> list[dict[str, Any]]:
    overlay_rooms = [item for item in overlay.get("rooms") or [] if isinstance(item, dict)]
    fallback_by_id = {str(room.get("room_id") or ""): room for room in fallback_rooms}
    correspondence_by_partition = {
        str(item.get("asset_partition_id") or ""): item
        for item in overlay.get("scene_map_correspondence_v1") or []
        if isinstance(item, dict)
    }
    overlay_navigation_ids = {
        str(room.get("navigation_area_id") or "")
        for room in overlay_rooms
        if str(room.get("navigation_area_id") or "")
    }
    rooms = []
    for item in overlay_rooms:
        room = dict(item)
        fallback = fallback_by_id.get(str(room.get("navigation_area_id") or ""))
        if fallback:
            room.setdefault("polygon", copy.deepcopy(fallback.get("polygon") or []))
            room.setdefault("geometry_source", fallback.get("geometry_source"))
            room.setdefault("source_map_frame_id", fallback.get("source_map_frame_id"))
        if "map_center" not in room:
            room["map_center"] = _polygon_center(room.get("polygon") or [])
        if not room.get("polygon") and not str(room.get("navigation_area_id") or ""):
            continue
        if room.get("polygon"):
            room = normalize_spatial_rooms(
                [room],
                frame_id=frame_id,
                polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
                geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
                alignment_status=ALIGNMENT_STATUS_CANDIDATE,
                semantic_label_status=str(
                    room.get("alignment_status") or ALIGNMENT_STATUS_CANDIDATE
                ),
            )[0]
        match = correspondence_by_partition.get(str(room.get("asset_partition_id") or ""))
        if match:
            room.setdefault(
                "scene_map_correspondence",
                {
                    "schema": SCENE_MAP_CORRESPONDENCE_SCHEMA,
                    "asset_partition_id": str(match.get("asset_partition_id") or ""),
                    "navigation_area_id": str(match.get("navigation_area_id") or ""),
                    "alignment_status": str(
                        match.get("alignment_status")
                        or room.get("alignment_status")
                        or ALIGNMENT_STATUS_CANDIDATE
                    ),
                    "transform_source": str(match.get("transform_source") or ""),
                    "evidence_artifacts": list(match.get("evidence_artifacts") or []),
                    "map_polygon_provided": "map_polygon" in match,
                },
            )
        rooms.append(room)
    for fallback in fallback_rooms:
        room_id = str(fallback.get("room_id") or "")
        if (
            room_id
            and room_id not in overlay_navigation_ids
            and not any(str(room.get("room_id") or "") == room_id for room in rooms)
        ):
            rooms.append(dict(fallback))
    return rooms


def _room_category_hints(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id.replace("_", " "))
        if not room_id:
            continue
        hints.append(
            {
                "anchor_type": "room_area",
                "category": str(room.get("category") or "room_area"),
                "label": room_label,
                "room_id": room_id,
                "room_label": room_label,
                "waypoint_id": "",
                "affordances": ["navigate", "observe"],
                "classification_status": str(room.get("classification_status") or "map_prior"),
                "confidence": float(room.get("confidence") or 0.0),
                "aliases": list(room.get("aliases") or [room_id, room_label]),
                "producer_type": "scene_room_semantic_overlay",
                "review_status": str(room.get("review_status") or ""),
            }
        )
    return hints


def _driveable_ways(
    rooms: list[dict[str, Any]],
    existing_ways: list[dict[str, Any]],
) -> list[dict[str, str]]:
    nav_to_room = {
        str(room.get("navigation_area_id") or ""): str(room.get("room_id") or "")
        for room in rooms
        if str(room.get("navigation_area_id") or "") and str(room.get("room_id") or "")
    }
    ways: list[dict[str, str]] = []
    for way in existing_ways:
        start = nav_to_room.get(str(way.get("from_room_id") or ""))
        goal = nav_to_room.get(str(way.get("to_room_id") or ""))
        if start and goal and start != goal:
            ways.append({"from_room_id": start, "to_room_id": goal})
    if ways:
        return _dedupe_ways(ways)
    return _dedupe_ways(
        [
            {
                "from_room_id": str(left.get("room_id") or ""),
                "to_room_id": str(right.get("room_id") or ""),
            }
            for left, right in zip(rooms, rooms[1:], strict=False)
            if str(left.get("room_id") or "") and str(right.get("room_id") or "")
        ]
    )


def _dedupe_ways(ways: list[dict[str, str]]) -> list[dict[str, str]]:
    output = []
    seen = set()
    for way in ways:
        key = (way["from_room_id"], way["to_room_id"])
        if key not in seen:
            output.append(way)
            seen.add(key)
    return output


def _retarget_waypoints(
    waypoints: list[dict[str, Any]],
    *,
    room_by_navigation_area: dict[str, str],
) -> list[dict[str, Any]]:
    output = []
    for waypoint in waypoints:
        if not isinstance(waypoint, dict):
            continue
        item = dict(waypoint)
        navigation_area_id = str(item.get("room_id") or "")
        room_id = room_by_navigation_area.get(navigation_area_id)
        if room_id:
            item["navigation_area_id"] = navigation_area_id
            item["room_id"] = room_id
        output.append(item)
    return output


def _polygon_center(polygon: list[dict[str, Any]]) -> dict[str, float]:
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        return {}
    return {"x": round(sum(xs) / len(xs), 3), "y": round(sum(ys) / len(ys), 3)}


def _review_item(room: dict[str, Any]) -> dict[str, Any]:
    return {
        "room_id": room.get("room_id"),
        "asset_partition_id": room.get("asset_partition_id"),
        "proposed_room_label": room.get("room_label"),
        "proposed_category": room.get("category"),
        "confidence": room.get("confidence"),
        "reason": "render_or_operator_review_recommended",
        "render_hint": {
            "asset_partition_id": room.get("asset_partition_id"),
            "preferred_view": "room_overview",
        },
    }

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.core.json_sources import read_json_object  # noqa: E402

REALWORLD_CONTRACT = "realworld_cleanup_v1"
METRIC_MAP_SCHEMA = "real_robot_map_bundle_v1"
STATIC_FIXTURE_PROJECTION_SCHEMA = "static_fixture_projection_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Roboclaws metric_map/static_fixture_projection JSON from a completed "
            "Agibot GDK map-context authoring file."
        )
    )
    parser.add_argument("context_json", type=Path)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory. Defaults to <context-dir>/generated_metric_map.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    context = _read_context_source(args.context_json)
    errors = validate_context(context)
    if errors:
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        raise SystemExit("Agibot map context is incomplete")

    output_dir = args.output_dir or args.context_json.parent / "generated_metric_map"
    output_dir.mkdir(parents=True, exist_ok=True)
    context_copy = output_dir / "agibot_map_context.completed.json"
    context_copy.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    preview_path = output_dir / "semantic_preview.png"
    write_semantic_preview(context, preview_path)

    metric_map = metric_map_from_context(
        context,
        semantic_preview_artifact=preview_path.name,
    )
    static_fixture_projection = static_fixture_projection_from_context(context)
    agent_view = {"metric_map": metric_map, "static_fixture_projection": static_fixture_projection}

    _write_json(output_dir / "metric_map.json", metric_map)
    _write_json(output_dir / "static_fixture_projection.json", static_fixture_projection)
    _write_json(output_dir / "agent_view.json", agent_view)
    _copy_capture_images(context, output_dir, source_root=args.context_json.parent)

    fixture_count = sum(
        len(room.get("fixtures") or []) for room in static_fixture_projection["rooms"]
    )
    print(
        "agibot metric_map generated: "
        f"{output_dir} rooms={len(metric_map['rooms'])} "
        f"fixtures={fixture_count} "
        f"waypoints={len(metric_map['inspection_waypoints'])}"
    )


def validate_context(context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    rooms = _list(context.get("rooms"))
    fixtures = _list(context.get("fixtures"))
    waypoints = _list(context.get("inspection_waypoints"))
    _validate_context_header(context, errors)
    _validate_context_mode(
        context,
        rooms=rooms,
        fixtures=fixtures,
        waypoints=waypoints,
        errors=errors,
    )
    room_ids = _validate_context_rooms(rooms, errors)
    fixture_ids = _validate_context_fixtures(fixtures, room_ids=room_ids, errors=errors)
    _validate_context_waypoints(
        waypoints,
        room_ids=room_ids,
        fixture_ids=fixture_ids,
        errors=errors,
    )
    return errors


def _validate_context_header(context: dict[str, Any], errors: list[str]) -> None:
    if context.get("schema") != "agibot_gdk_map_context_authoring_v1":
        errors.append("schema must be agibot_gdk_map_context_authoring_v1")
    map_source = _dict(context.get("map_source"))
    if map_source.get("type") != "agibot_gdk_map_context":
        errors.append("map_source.type must be agibot_gdk_map_context")
    if _is_blank(map_source.get("map_name")) and map_source.get("map_id") is None:
        errors.append("map_source must include map_name or map_id")


def _validate_context_mode(
    context: dict[str, Any],
    *,
    rooms: list[dict[str, Any]],
    fixtures: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
    errors: list[str],
) -> None:
    if _base_metric_map_context(context):
        _validate_base_metric_map_context(context, errors)
        return
    if not rooms:
        errors.append("rooms must contain at least one room")
        return
    if not fixtures:
        errors.append("fixtures must contain at least one fixture")
    if not waypoints:
        errors.append("inspection_waypoints must contain at least one waypoint")


def _validate_base_metric_map_context(context: dict[str, Any], errors: list[str]) -> None:
    if not _list(_dict(context.get("safety_bounds")).get("polygon")):
        errors.append(
            "base navigation map context safety_bounds.polygon must contain at least one point"
        )
    if not generated_exploration_candidates(context):
        errors.append(
            "base navigation map context must include free_space_samples, "
            "exploration_candidates, or generated_exploration_candidates"
        )


def _validate_context_rooms(rooms: list[dict[str, Any]], errors: list[str]) -> set[str]:
    room_ids = set()
    for index, room in enumerate(rooms):
        room_id = _required_text(room, "room_id", f"rooms[{index}]", errors)
        _required_text(room, "room_label", f"rooms[{index}]", errors)
        if room_id:
            room_ids.add(room_id)
    return room_ids


def _validate_context_fixtures(
    fixtures: list[dict[str, Any]],
    *,
    room_ids: set[str],
    errors: list[str],
) -> set[str]:
    fixture_ids = set()
    for index, fixture in enumerate(fixtures):
        fixture_id = _required_text(fixture, "fixture_id", f"fixtures[{index}]", errors)
        room_id = _required_text(fixture, "room_id", f"fixtures[{index}]", errors)
        _required_text(fixture, "label", f"fixtures[{index}]", errors)
        _required_text(fixture, "category", f"fixtures[{index}]", errors)
        if room_id and room_id not in room_ids:
            errors.append(f"fixtures[{index}].room_id does not match a room: {room_id}")
        if fixture_id:
            fixture_ids.add(fixture_id)
    return fixture_ids


def _validate_context_waypoints(
    waypoints: list[dict[str, Any]],
    *,
    room_ids: set[str],
    fixture_ids: set[str],
    errors: list[str],
) -> None:
    for index, waypoint in enumerate(waypoints):
        room_id = _required_text(waypoint, "room_id", f"inspection_waypoints[{index}]", errors)
        fixture_id = str(waypoint.get("fixture_id") or "")
        _required_text(waypoint, "waypoint_id", f"inspection_waypoints[{index}]", errors)
        _required_text(waypoint, "label", f"inspection_waypoints[{index}]", errors)
        _required_number(waypoint, "x", f"inspection_waypoints[{index}]", errors)
        _required_number(waypoint, "y", f"inspection_waypoints[{index}]", errors)
        _required_number(waypoint, "yaw", f"inspection_waypoints[{index}]", errors)
        if room_id and room_id not in room_ids:
            errors.append(f"inspection_waypoints[{index}].room_id does not match a room: {room_id}")
        if fixture_id and fixture_id not in fixture_ids:
            errors.append(
                f"inspection_waypoints[{index}].fixture_id does not match a fixture: {fixture_id}"
            )


def metric_map_from_context(
    context: dict[str, Any],
    *,
    semantic_preview_artifact: str,
) -> dict[str, Any]:
    map_id = str(context.get("environment_id") or "operator_authored_map")
    map_version = str(context.get("map_version") or "operator-authored-v1")
    frame_id = str(context.get("frame_id") or "map")
    bounds = _coordinate_bounds(context)
    robot_pose = _robot_pose(context, frame_id=frame_id)
    base_metric_map = _base_metric_map_context(context)
    generated_candidates = generated_exploration_candidates(context)
    waypoints = (
        generated_candidates if base_metric_map else _list(context.get("inspection_waypoints"))
    )
    rooms = [_room_payload(room) for room in _list(context.get("rooms"))]
    return {
        "ok": True,
        "tool": "metric_map",
        "status": "ok",
        "contract": REALWORLD_CONTRACT,
        "schema": METRIC_MAP_SCHEMA,
        "frame_id": frame_id,
        "map_id": map_id,
        "map_version": map_version,
        "resolution_m": 0.05,
        "origin": {"x": bounds["min_x"], "y": bounds["min_y"], "yaw": 0.0},
        "width": max(int(math.ceil((bounds["max_x"] - bounds["min_x"]) / 0.05)), 1),
        "height": max(int(math.ceil((bounds["max_y"] - bounds["min_y"]) / 0.05)), 1),
        "occupancy_values": {"unknown": -1, "free": 0, "occupied": 100},
        "occupancy_grid_artifact": None,
        "map_preview_artifact": semantic_preview_artifact,
        "rooms": rooms,
        "room_category_hints": (_room_category_hints(rooms, waypoints) if base_metric_map else []),
        "driveable_ways": _list(context.get("driveable_ways")),
        "robot_pose": robot_pose,
        "inspection_waypoints": [_waypoint_payload(item, frame_id=frame_id) for item in waypoints],
        **(
            {
                "generated_exploration_candidates": [
                    _waypoint_payload(item, frame_id=frame_id) for item in generated_candidates
                ],
                "safety_bounds": _public_safety_bounds(context),
                "base_metric_map": {
                    "enabled": True,
                    "source": "public_occupancy_free_space",
                    "generated_candidate_count": len(generated_candidates),
                    "source_rooms_hidden": False,
                    "source_room_labels_visible": bool(rooms),
                    "source_fixtures_hidden": True,
                    "source_inspection_waypoints_hidden": True,
                    "public_contract_note": (
                        "Base Metric Map projection exposes operator safety bounds and "
                        "generated exploration candidates plus public room labels when "
                        "available, not authored fixture semantics."
                    ),
                },
            }
            if base_metric_map
            else {}
        ),
        "public_contract_note": (
            "Metric map projection contains backend-agnostic public rooms, fixtures, "
            "and operator-recorded waypoints. Runtime movable objects and private "
            "scoring truth are not encoded."
            if not base_metric_map
            else "Base Metric Map projection contains backend-agnostic safety bounds, "
            "generated exploration candidates, and public room labels when available. "
            "Runtime movable objects, private "
            "scoring truth, and Agibot backend internals are not encoded."
        ),
    }


def static_fixture_projection_from_context(context: dict[str, Any]) -> dict[str, Any]:
    if _base_metric_map_context(context):
        return {
            "ok": True,
            "tool": "static_fixture_projection",
            "status": "ok",
            "contract": REALWORLD_CONTRACT,
            "schema": STATIC_FIXTURE_PROJECTION_SCHEMA,
            "static_fixture_projection_mode": "base_metric_map_no_fixtures",
            "contains_runtime_observations": False,
            "generated_exploration_candidate_count": len(generated_exploration_candidates(context)),
            "public_contract_note": (
                "Base Metric Map contexts may expose public room labels but do not "
                "require hand-authored fixture semantics. Runtime observations may add "
                "public anchors later."
            ),
            "rooms": [],
        }
    fixtures_by_room: dict[str, list[dict[str, Any]]] = {}
    for fixture in _list(context.get("fixtures")):
        room_id = str(fixture.get("room_id"))
        fixtures_by_room.setdefault(room_id, []).append(_fixture_payload(fixture))
    rooms = []
    for room in _list(context.get("rooms")):
        item = _room_payload(room)
        item["fixtures"] = fixtures_by_room.get(item["room_id"], [])
        rooms.append(item)
    return {
        "ok": True,
        "tool": "static_fixture_projection",
        "status": "ok",
        "contract": REALWORLD_CONTRACT,
        "schema": STATIC_FIXTURE_PROJECTION_SCHEMA,
        "static_fixture_projection_mode": "operator_authored_static_projection",
        "contains_runtime_observations": False,
        "public_contract_note": (
            "Static fixture projection is derived from the operator-authored semantic "
            "overlay, not from runtime observed movable objects."
        ),
        "rooms": rooms,
    }


def write_semantic_preview(context: dict[str, Any], output_path: Path) -> None:
    width, height = 1000, 700
    image = Image.new("RGB", (width, height), (248, 249, 251))
    draw = ImageDraw.Draw(image)
    bounds = _coordinate_bounds(context)

    def point(x: float, y: float) -> tuple[float, float]:
        span_x = max(bounds["max_x"] - bounds["min_x"], 1.0)
        span_y = max(bounds["max_y"] - bounds["min_y"], 1.0)
        margin = 70
        scale = min((width - 2 * margin) / span_x, (height - 2 * margin) / span_y)
        px = margin + (x - bounds["min_x"]) * scale
        py = height - margin - (y - bounds["min_y"]) * scale
        return px, py

    draw.text((24, 22), "Semantic overlay preview (not an occupancy map)", fill=(35, 41, 53))
    for room in _list(context.get("rooms")):
        polygon = _list(room.get("polygon"))
        if len(polygon) >= 3:
            points = [point(float(item["x"]), float(item["y"])) for item in polygon]
            draw.polygon(points, outline=(125, 140, 165), fill=(235, 240, 247))
        else:
            y = 52 + 18 * len(str(room.get("room_id", "")))
            draw.text((24, y), str(room.get("room_label")), fill=(70, 82, 104))

    for fixture in _list(context.get("fixtures")):
        pose = _dict(fixture.get("pose"))
        if _number_or_none(pose.get("x")) is None or _number_or_none(pose.get("y")) is None:
            continue
        px, py = point(float(pose["x"]), float(pose["y"]))
        draw.rectangle((px - 8, py - 8, px + 8, py + 8), fill=(198, 84, 71))
        draw.text((px + 10, py - 6), str(fixture.get("label", ""))[:28], fill=(80, 35, 30))

    for waypoint in _list(context.get("inspection_waypoints")):
        px, py = point(float(waypoint["x"]), float(waypoint["y"]))
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(43, 116, 185))
        draw.text((px + 9, py + 5), str(waypoint.get("waypoint_id", ""))[:28], fill=(30, 72, 120))

    for waypoint in generated_exploration_candidates(context):
        px, py = point(float(waypoint["x"]), float(waypoint["y"]))
        draw.ellipse((px - 7, py - 7, px + 7, py + 7), fill=(43, 116, 185))
        draw.text((px + 9, py + 5), str(waypoint.get("waypoint_id", ""))[:28], fill=(30, 72, 120))

    robot = _dict(context.get("robot_pose"))
    if _number_or_none(robot.get("x")) is not None and _number_or_none(robot.get("y")) is not None:
        px, py = point(float(robot["x"]), float(robot["y"]))
        draw.polygon([(px, py - 12), (px - 10, py + 10), (px + 10, py + 10)], fill=(68, 150, 92))
        draw.text((px + 12, py - 6), "robot capture pose", fill=(35, 98, 58))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def _room_payload(room: dict[str, Any]) -> dict[str, Any]:
    return {
        "room_id": str(room["room_id"]),
        "room_label": str(room["room_label"]),
        "fixture_count": 0,
        "polygon": _list(room.get("polygon")),
    }


def _fixture_payload(fixture: dict[str, Any]) -> dict[str, Any]:
    return {
        "fixture_id": str(fixture["fixture_id"]),
        "room_id": str(fixture["room_id"]),
        "label": str(fixture["label"]),
        "category": str(fixture["category"]),
        "pose": _dict(fixture.get("pose")),
        "footprint": _list(fixture.get("footprint")),
    }


def _room_category_hints(
    rooms: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    waypoint_by_room: dict[str, str] = {}
    for waypoint in waypoints:
        room_id = str(waypoint.get("room_id") or "")
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if room_id and waypoint_id:
            waypoint_by_room.setdefault(room_id, waypoint_id)
    hints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id.replace("_", " "))
        if not room_id:
            continue
        hints.append(
            {
                "anchor_type": "room_area",
                "category": "room_area",
                "label": room_label,
                "room_id": room_id,
                "room_label": room_label,
                "waypoint_id": waypoint_by_room.get(room_id, ""),
                "affordances": ["navigate", "observe"],
                "classification_status": "map_prior",
                "confidence": 0.8,
                "producer_type": "agibot_base_metric_map_context",
            }
        )
    return hints


def _waypoint_payload(waypoint: dict[str, Any], *, frame_id: str) -> dict[str, Any]:
    payload = {
        "waypoint_id": str(waypoint["waypoint_id"]),
        "frame_id": frame_id,
        "x": float(waypoint["x"]),
        "y": float(waypoint["y"]),
        "yaw": float(waypoint["yaw"]),
        "room_id": str(waypoint["room_id"]),
        "room_label": str(waypoint.get("room_label") or ""),
        "fixture_id": str(waypoint.get("fixture_id") or ""),
        "label": str(waypoint["label"]),
        "purpose": str(waypoint.get("purpose") or "inspect_fixture"),
        "waypoint_source": str(waypoint.get("waypoint_source") or "operator_recorded_pose"),
        "visited": bool(waypoint.get("visited", False)),
    }
    if waypoint.get("fixture_id"):
        payload["coverage_estimate"] = [
            {"fixture_id": str(waypoint["fixture_id"]), "confidence": 1.0}
        ]
    if isinstance(waypoint.get("capture"), dict):
        payload["capture"] = waypoint["capture"]
    if waypoint.get("reachability_status"):
        payload["reachability_status"] = _public_reachability_status(
            str(waypoint["reachability_status"])
        )
    if isinstance(waypoint.get("candidate_provenance"), dict):
        payload["candidate_provenance"] = waypoint["candidate_provenance"]
    return payload


def _robot_pose(context: dict[str, Any], *, frame_id: str) -> dict[str, Any]:
    pose = _dict(context.get("robot_pose"))
    if _number_or_none(pose.get("x")) is None or _number_or_none(pose.get("y")) is None:
        waypoints = (
            generated_exploration_candidates(context)
            if _base_metric_map_context(context)
            else _list(context.get("inspection_waypoints"))
        )
        waypoint = waypoints[0]
        pose = {"x": waypoint["x"], "y": waypoint["y"], "yaw": waypoint["yaw"]}
    return {
        "frame_id": frame_id,
        "x": float(pose.get("x", 0.0)),
        "y": float(pose.get("y", 0.0)),
        "yaw": float(pose.get("yaw", 0.0)),
        "room_id": str(pose.get("room_id") or ""),
        "waypoint_id": str(pose.get("waypoint_id") or ""),
        "pose_source": "generated_exploration_candidate"
        if _base_metric_map_context(context)
        else "operator_recorded_pose",
    }


def _coordinate_bounds(context: dict[str, Any]) -> dict[str, float]:
    points = _coordinate_bound_points(context)
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    if not xs or not ys:
        return {"min_x": -2.0, "min_y": -2.0, "max_x": 2.0, "max_y": 2.0}
    pad = 1.0
    return {
        "min_x": min(xs) - pad,
        "min_y": min(ys) - pad,
        "max_x": max(xs) + pad,
        "max_y": max(ys) + pad,
    }


def _coordinate_bound_points(context: dict[str, Any]) -> list[tuple[float, float]]:
    points = []
    points.extend(
        (float(waypoint["x"]), float(waypoint["y"]))
        for waypoint in generated_exploration_candidates(context)
    )
    points.extend(
        (float(waypoint["x"]), float(waypoint["y"]))
        for waypoint in _list(context.get("inspection_waypoints"))
    )
    points.extend(_numbered_xy_points(_list(_dict(context.get("safety_bounds")).get("polygon"))))
    points.extend(_fixture_pose_points(_list(context.get("fixtures"))))
    for room in _list(context.get("rooms")):
        points.extend(_numbered_xy_points(_list(room.get("polygon"))))
    return points


def _fixture_pose_points(fixtures: list[dict[str, Any]]) -> list[tuple[float, float]]:
    points = []
    for fixture in fixtures:
        pose = _dict(fixture.get("pose"))
        point = _numbered_xy_point(pose)
        if point is not None:
            points.append(point)
    return points


def _numbered_xy_points(items: list[dict[str, Any]]) -> list[tuple[float, float]]:
    return [point for item in items if (point := _numbered_xy_point(item)) is not None]


def _numbered_xy_point(item: dict[str, Any]) -> tuple[float, float] | None:
    x = _number_or_none(item.get("x"))
    y = _number_or_none(item.get("y"))
    if x is None or y is None:
        return None
    return x, y


def _copy_capture_images(context: dict[str, Any], output_dir: Path, *, source_root: Path) -> None:
    captures = []
    capture = _dict(context.get("capture"))
    if capture:
        captures.append(capture)
    captures.extend(
        item for item in _list(context.get("waypoint_captures")) if isinstance(item, dict)
    )
    for waypoint in _list(context.get("inspection_waypoints")):
        waypoint_capture = waypoint.get("capture") if isinstance(waypoint, dict) else None
        if isinstance(waypoint_capture, dict):
            captures.append(waypoint_capture)
    images_dir = output_dir / "capture_images"
    copied: set[Path] = set()
    for capture_item in captures:
        for item in _list(capture_item.get("camera_images")):
            image_path = str(item.get("image_path") or "")
            if not image_path:
                continue
            src = source_root / image_path
            if src.is_file() and src not in copied:
                copied.add(src)
                images_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, images_dir / src.name)


def generated_exploration_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    explicit = _list(context.get("generated_exploration_candidates")) or _list(
        context.get("exploration_candidates")
    )
    source_candidates = explicit or _list(context.get("free_space_samples"))
    frame_id = str(context.get("frame_id") or "map")
    room_labels = {
        str(room.get("room_id") or ""): str(room.get("room_label") or "")
        for room in _list(context.get("rooms"))
        if isinstance(room, dict) and str(room.get("room_id") or "")
    }
    generated = []
    for index, source in enumerate(source_candidates, start=1):
        if not isinstance(source, dict):
            continue
        x = _number_or_none(source.get("x"))
        y = _number_or_none(source.get("y"))
        if x is None or y is None:
            continue
        waypoint_id = str(source.get("waypoint_id") or f"generated_exploration_{index:03d}")
        room_id = str(source.get("room_id") or "generated_area")
        room_label = str(source.get("room_label") or room_labels.get(room_id) or "")
        generated.append(
            {
                "waypoint_id": waypoint_id,
                "frame_id": str(source.get("frame_id") or frame_id),
                "x": x,
                "y": y,
                "yaw": _number_or_none(source.get("yaw")) or 0.0,
                "room_id": room_id,
                "room_label": room_label,
                "fixture_id": str(source.get("fixture_id") or ""),
                "label": str(source.get("label") or f"Generated exploration candidate {index}"),
                "purpose": "base_metric_map_exploration",
                "waypoint_source": "generated_exploration_candidate",
                "visited": bool(source.get("visited", False)),
                "reachability_status": str(source.get("reachability_status") or "unverified"),
                "coverage_estimate": source.get(
                    "coverage_estimate", round(1.0 / max(len(source_candidates), 1), 6)
                ),
                "candidate_provenance": {
                    "source": str(source.get("source") or "public_free_space_sample"),
                    "candidate_index": index,
                    "source_pose": str(source.get("source_pose") or "free_space_sample"),
                    "source_room_hidden": False,
                    "source_room_label_available": bool(room_label),
                    "source_fixtures_hidden": True,
                    "source_waypoint_hidden": True,
                },
            }
        )
    return generated


def _base_metric_map_context(context: dict[str, Any]) -> bool:
    return not _list(context.get("fixtures")) and not _list(context.get("inspection_waypoints"))


def _public_safety_bounds(context: dict[str, Any]) -> dict[str, Any]:
    bounds = _dict(context.get("safety_bounds"))
    return {
        "frame_id": str(bounds.get("frame_id") or context.get("frame_id") or "map"),
        "polygon": _list(bounds.get("polygon")),
        "max_linear_speed_mps": bounds.get("max_linear_speed_mps"),
        "max_angular_speed_radps": bounds.get("max_angular_speed_radps"),
        "operator_approved": bool(bounds.get("operator_approved", False)),
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _read_context_source(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path, label="Agibot map context")
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc


def _required_text(
    item: dict[str, Any],
    key: str,
    prefix: str,
    errors: list[str],
) -> str:
    value = item.get(key)
    if _is_blank(value):
        errors.append(f"{prefix}.{key} is required")
        return ""
    return str(value)


def _required_number(
    item: dict[str, Any],
    key: str,
    prefix: str,
    errors: list[str],
) -> None:
    if _number_or_none(item.get(key)) is None:
        errors.append(f"{prefix}.{key} must be a number")


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return not text or text.startswith("TODO")


def _number_or_none(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _slug(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "_" for ch in value).strip("_")
    return text or "agibot_map"


def _public_reachability_status(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "verified":
        return "verified"
    if "timeout" in normalized:
        return "timeout"
    if "blocked" in normalized or "failed" in normalized:
        return "blocked"
    if not normalized:
        return "unverified"
    return "unverified"


if __name__ == "__main__":
    main()

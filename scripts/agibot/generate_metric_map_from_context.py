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

REALWORLD_CONTRACT = "realworld_cleanup_v1"
METRIC_MAP_SCHEMA = "real_robot_map_bundle_v1"
FIXTURE_HINTS_SCHEMA = "static_fixture_semantic_map_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate Roboclaws metric_map/fixture_hints JSON from a completed "
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
    context = json.loads(args.context_json.read_text(encoding="utf-8"))
    if not isinstance(context, dict):
        raise SystemExit("context JSON must be an object")
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
    fixture_hints = fixture_hints_from_context(context)
    agent_view = {"metric_map": metric_map, "fixture_hints": fixture_hints}

    _write_json(output_dir / "metric_map.json", metric_map)
    _write_json(output_dir / "fixture_hints.json", fixture_hints)
    _write_json(output_dir / "agent_view.json", agent_view)
    _copy_capture_images(context, output_dir, source_root=args.context_json.parent)

    print(
        "agibot metric_map generated: "
        f"{output_dir} rooms={len(metric_map['rooms'])} "
        f"fixtures={sum(len(room.get('fixtures') or []) for room in fixture_hints['rooms'])} "
        f"waypoints={len(metric_map['inspection_waypoints'])}"
    )


def validate_context(context: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if context.get("schema") != "agibot_gdk_map_context_authoring_v1":
        errors.append("schema must be agibot_gdk_map_context_authoring_v1")
    map_source = _dict(context.get("map_source"))
    if map_source.get("type") != "agibot_gdk_map_context":
        errors.append("map_source.type must be agibot_gdk_map_context")
    if _is_blank(map_source.get("map_name")) and map_source.get("map_id") is None:
        errors.append("map_source must include map_name or map_id")

    rooms = _list(context.get("rooms"))
    fixtures = _list(context.get("fixtures"))
    waypoints = _list(context.get("inspection_waypoints"))
    if not rooms:
        errors.append("rooms must contain at least one room")
    if not fixtures:
        errors.append("fixtures must contain at least one fixture")
    if not waypoints:
        errors.append("inspection_waypoints must contain at least one waypoint")

    room_ids = set()
    for index, room in enumerate(rooms):
        room_id = _required_text(room, "room_id", f"rooms[{index}]", errors)
        _required_text(room, "room_label", f"rooms[{index}]", errors)
        if room_id:
            room_ids.add(room_id)

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
    return errors


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
        "rooms": [_room_payload(room) for room in _list(context.get("rooms"))],
        "driveable_ways": _list(context.get("driveable_ways")),
        "robot_pose": robot_pose,
        "inspection_waypoints": [
            _waypoint_payload(item, frame_id=frame_id)
            for item in _list(context.get("inspection_waypoints"))
        ],
        "public_contract_note": (
            "Metric map projection contains backend-agnostic public rooms, fixtures, "
            "and operator-recorded waypoints. Runtime movable objects and private "
            "scoring truth are not encoded."
        ),
    }


def fixture_hints_from_context(context: dict[str, Any]) -> dict[str, Any]:
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
        "tool": "fixture_hints",
        "status": "ok",
        "contract": REALWORLD_CONTRACT,
        "schema": FIXTURE_HINTS_SCHEMA,
        "fixture_hint_mode": "operator_authored_semantic_map",
        "contains_runtime_observations": False,
        "public_contract_note": (
            "Static fixture hints are projected from the operator-authored semantic "
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


def _waypoint_payload(waypoint: dict[str, Any], *, frame_id: str) -> dict[str, Any]:
    payload = {
        "waypoint_id": str(waypoint["waypoint_id"]),
        "frame_id": frame_id,
        "x": float(waypoint["x"]),
        "y": float(waypoint["y"]),
        "yaw": float(waypoint["yaw"]),
        "room_id": str(waypoint["room_id"]),
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
    return payload


def _robot_pose(context: dict[str, Any], *, frame_id: str) -> dict[str, Any]:
    pose = _dict(context.get("robot_pose"))
    if _number_or_none(pose.get("x")) is None or _number_or_none(pose.get("y")) is None:
        waypoint = _list(context.get("inspection_waypoints"))[0]
        pose = {"x": waypoint["x"], "y": waypoint["y"], "yaw": waypoint["yaw"]}
    return {
        "frame_id": frame_id,
        "x": float(pose.get("x", 0.0)),
        "y": float(pose.get("y", 0.0)),
        "yaw": float(pose.get("yaw", 0.0)),
        "room_id": str(pose.get("room_id") or ""),
        "waypoint_id": str(pose.get("waypoint_id") or ""),
        "pose_source": "operator_recorded_pose",
    }


def _coordinate_bounds(context: dict[str, Any]) -> dict[str, float]:
    xs: list[float] = []
    ys: list[float] = []
    for waypoint in _list(context.get("inspection_waypoints")):
        xs.append(float(waypoint["x"]))
        ys.append(float(waypoint["y"]))
    for fixture in _list(context.get("fixtures")):
        pose = _dict(fixture.get("pose"))
        x = _number_or_none(pose.get("x"))
        y = _number_or_none(pose.get("y"))
        if x is not None and y is not None:
            xs.append(x)
            ys.append(y)
    for room in _list(context.get("rooms")):
        for point in _list(room.get("polygon")):
            x = _number_or_none(point.get("x"))
            y = _number_or_none(point.get("y"))
            if x is not None and y is not None:
                xs.append(x)
                ys.append(y)
    if not xs or not ys:
        return {"min_x": -2.0, "min_y": -2.0, "max_x": 2.0, "max_y": 2.0}
    pad = 1.0
    return {
        "min_x": min(xs) - pad,
        "min_y": min(ys) - pad,
        "max_x": max(xs) + pad,
        "max_y": max(ys) + pad,
    }


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


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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
    if "verified" in normalized:
        return "verified"
    if "blocked" in normalized or "failed" in normalized or "timeout" in normalized:
        return "blocked"
    if not normalized:
        return "unverified"
    return "unverified"


if __name__ == "__main__":
    main()

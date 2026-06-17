from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

ReportAssetSrcResolver = Callable[[Any, Path | None], str]


def write_semantic_map_artifacts(
    run_dir: Path,
    run_result: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    *,
    report_asset_src: ReportAssetSrcResolver,
) -> str:
    """Write stable public semantic-map review artifacts when map evidence exists."""

    payload = _semantic_map_overlay_payload(run_result, robot_view_steps)
    if not _semantic_map_overlay_has_content(payload):
        return ""
    overlay_path = run_dir / "map_overlay.json"
    semantic_map_path = run_dir / "semantic_map.png"
    overlay_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _draw_semantic_map_preview(payload, semantic_map_path)
    artifacts = run_result.setdefault("artifacts", {})
    artifacts["semantic_map"] = str(semantic_map_path)
    artifacts["map_overlay"] = str(overlay_path)
    return report_asset_src(semantic_map_path, run_dir)


def _semantic_map_overlay_payload(
    run_result: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    agent_view = run_result.get("agent_view") or {}
    metric_map = agent_view.get("metric_map") or {}
    runtime_metric_map = (
        agent_view.get("runtime_metric_map") or run_result.get("runtime_metric_map") or {}
    )
    fixture_hints = agent_view.get("fixture_hints") or {}
    waypoints = _semantic_map_waypoints(metric_map, runtime_metric_map)
    anchors = _semantic_map_anchors(runtime_metric_map)
    robot_pose = _map_pose(metric_map.get("robot_pose")) or _map_pose(
        runtime_metric_map.get("robot_pose")
    )
    return {
        "schema": "roboclaws_map_overlay_v1",
        "frame_id": str(metric_map.get("frame_id") or runtime_metric_map.get("frame_id") or "map"),
        "semantic_map": {
            "source": "runtime_metric_map_and_navigation_map",
            "runtime_metric_map_schema": runtime_metric_map.get("schema", ""),
            "map_mode": runtime_metric_map.get("map_mode", run_result.get("map_mode", "")),
            "minimal_map_mode": bool(runtime_metric_map.get("minimal_map_mode", False)),
            "private_truth_included": False,
        },
        "scene_overlay": _scene_overlay_provenance(run_result, robot_view_steps),
        "rooms": _semantic_map_rooms(metric_map),
        "fixtures": _semantic_map_fixtures(metric_map, fixture_hints, runtime_metric_map),
        "waypoints": waypoints,
        "public_semantic_anchors": anchors,
        "robot_pose": robot_pose,
        "trajectory": _semantic_map_trajectory(run_result, robot_view_steps, waypoints, robot_pose),
    }


def _semantic_map_overlay_has_content(payload: dict[str, Any]) -> bool:
    return any(
        payload.get(key)
        for key in (
            "rooms",
            "fixtures",
            "waypoints",
            "public_semantic_anchors",
            "robot_pose",
            "trajectory",
        )
    )


def _semantic_map_waypoints(
    metric_map: dict[str, Any],
    runtime_metric_map: dict[str, Any],
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for item in metric_map.get("inspection_waypoints") or []:
        pose = _map_pose(item)
        if not pose:
            continue
        waypoint_id = str(item.get("waypoint_id") or f"waypoint_{len(by_id) + 1:03d}")
        by_id[waypoint_id] = {
            "waypoint_id": waypoint_id,
            "label": str(item.get("label") or waypoint_id),
            "purpose": str(item.get("purpose") or ""),
            "visited": bool(item.get("visited", False)),
            **pose,
        }
    for item in runtime_metric_map.get("generated_exploration_candidates") or []:
        pose = _map_pose(item)
        if not pose:
            continue
        waypoint_id = str(item.get("waypoint_id") or f"generated_{len(by_id) + 1:03d}")
        existing = by_id.get(waypoint_id, {})
        by_id[waypoint_id] = {
            "waypoint_id": waypoint_id,
            "label": str(item.get("label") or existing.get("label") or waypoint_id),
            "purpose": str(item.get("purpose") or existing.get("purpose") or ""),
            "visited": bool(item.get("visited", existing.get("visited", False))),
            **pose,
        }
    return list(by_id.values())


def _semantic_map_anchors(runtime_metric_map: dict[str, Any]) -> list[dict[str, Any]]:
    anchors: list[dict[str, Any]] = []
    for item in runtime_metric_map.get("public_semantic_anchors") or []:
        pose = _map_pose(item.get("pose"))
        if not pose:
            continue
        anchors.append(
            {
                "anchor_id": str(item.get("anchor_id") or ""),
                "anchor_type": str(item.get("anchor_type") or ""),
                "category": str(item.get("category") or ""),
                "label": str(item.get("label") or item.get("category") or ""),
                "waypoint_id": str(item.get("waypoint_id") or ""),
                "producer_type": str(item.get("producer_type") or ""),
                "promotion_status": str(item.get("promotion_status") or ""),
                **pose,
            }
        )
    return anchors


def _semantic_map_rooms(metric_map: dict[str, Any]) -> list[dict[str, Any]]:
    rooms: list[dict[str, Any]] = []
    for room in metric_map.get("rooms") or []:
        points = []
        for point in room.get("polygon") or []:
            pose = _map_pose(point)
            if pose:
                points.append({"x": pose["x"], "y": pose["y"]})
        if len(points) < 3:
            continue
        rooms.append(
            {
                "room_id": str(room.get("room_id") or ""),
                "label": str(room.get("room_label") or room.get("room_id") or ""),
                "polygon_role": str(room.get("polygon_role") or ""),
                "geometry_source": str(room.get("geometry_source") or ""),
                "alignment_status": str(room.get("alignment_status") or ""),
                "source_map_frame_id": str(room.get("source_map_frame_id") or ""),
                "polygon": points,
            }
        )
    return rooms


def _semantic_map_fixtures(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    runtime_metric_map: dict[str, Any],
) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for source in (
        metric_map.get("fixtures") or [],
        runtime_metric_map.get("static_map", {}).get("fixtures") or [],
    ):
        for item in source:
            fixture = _semantic_map_fixture_from_payload(item)
            if fixture:
                fixtures.append(fixture)
    for room in fixture_hints.get("rooms") or []:
        for item in room.get("fixtures") or []:
            fixture = _semantic_map_fixture_from_payload(item)
            if fixture:
                fixtures.append(fixture)
    return fixtures


def _semantic_map_fixture_from_payload(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    pose = _map_pose(item.get("pose") or item)
    if not pose:
        return None
    return {
        "fixture_id": str(item.get("fixture_id") or item.get("id") or ""),
        "label": str(item.get("label") or item.get("name") or item.get("category") or ""),
        "category": str(item.get("category") or ""),
        **pose,
    }


def _semantic_map_trajectory(
    run_result: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
    robot_pose: dict[str, Any] | None,
) -> list[dict[str, float]]:
    waypoint_by_id = {str(item.get("waypoint_id") or ""): item for item in waypoints}
    trajectory: list[dict[str, float]] = []
    seen: set[tuple[float, float]] = set()

    def append_pose(pose: dict[str, Any] | None) -> None:
        if not pose:
            return
        point = {"x": float(pose["x"]), "y": float(pose["y"])}
        key = (round(point["x"], 4), round(point["y"], 4))
        if key not in seen:
            trajectory.append(point)
            seen.add(key)

    for event in (run_result.get("cleanup_policy_trace") or {}).get("events") or []:
        append_pose(waypoint_by_id.get(str(event.get("waypoint_id") or "")))
    for step in robot_view_steps:
        append_pose(_map_pose(step.get("robot_pose")))
    if not trajectory:
        append_pose(robot_pose)
    return trajectory


def _scene_overlay_provenance(
    run_result: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    route_world = str(run_result.get("world") or run_result.get("world_id") or "")
    backend = str(run_result.get("backend") or "")
    map_view_provenance = ""
    for step in robot_view_steps:
        provenance = step.get("view_provenance")
        if isinstance(provenance, dict) and provenance.get("map"):
            map_view_provenance = str(provenance.get("map") or "")
            break
    is_gaussian_like = "b1" in route_world.lower() or "gaussian" in map_view_provenance.lower()
    return {
        "top_down_scene_available": any(
            (step.get("views") or {}).get("map") for step in robot_view_steps
        ),
        "top_down_scene_label": "Top-down Scene View",
        "backend": backend,
        "map_view_provenance": map_view_provenance,
        "alignment_status": "candidate" if is_gaussian_like else "native",
        "note": (
            "Top-down scene imagery is rendered from the backend scene and may use a "
            "candidate transform; semantic-map data remains the authoritative public map."
            if is_gaussian_like
            else "Top-down scene imagery is review evidence; semantic-map data remains separate."
        ),
    }


def _map_pose(payload: Any) -> dict[str, float] | None:
    if not isinstance(payload, dict):
        return None
    try:
        pose = {"x": float(payload.get("x")), "y": float(payload.get("y"))}
    except (TypeError, ValueError):
        return None
    if payload.get("yaw") is not None:
        try:
            pose["yaw"] = float(payload.get("yaw"))
        except (TypeError, ValueError):
            pass
    return pose


def _draw_semantic_map_preview(payload: dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1100, 560
    image = Image.new("RGB", (width, height), (248, 250, 252))
    draw = ImageDraw.Draw(image, "RGBA")
    draw.text((28, 22), "Semantic Map", fill=(30, 34, 42))
    draw.text(
        (28, 44),
        "Raw/source-map aligned public view; no rectified display frame.",
        fill=(86, 95, 112),
    )
    transform = _semantic_map_transform(payload, width=width, height=height)
    for room in payload.get("rooms") or []:
        points = [
            transform(float(point.get("x", 0.0)), float(point.get("y", 0.0)))
            for point in room.get("polygon") or []
        ]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=(72, 121, 210, 36), outline=(31, 79, 168, 190))
        _draw_label(draw, points[0][0], points[0][1] - 20, str(room.get("label") or "room"))
    for fixture in payload.get("fixtures") or []:
        x, y = transform(float(fixture.get("x", 0.0)), float(fixture.get("y", 0.0)))
        draw.rounded_rectangle(
            (x - 11, y - 8, x + 11, y + 8),
            radius=3,
            fill=(113, 124, 141, 220),
            outline=(71, 85, 105, 235),
        )
    trajectory = payload.get("trajectory") or []
    if len(trajectory) >= 2:
        points = [
            transform(float(point.get("x", 0.0)), float(point.get("y", 0.0)))
            for point in trajectory
        ]
        draw.line(points, fill=(245, 158, 11, 230), width=4)
    for waypoint in payload.get("waypoints") or []:
        x, y = transform(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        fill = (35, 134, 90, 245) if waypoint.get("visited") else (148, 163, 184, 230)
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=fill, outline=(17, 94, 57, 240))
    for anchor in payload.get("public_semantic_anchors") or []:
        if str(anchor.get("anchor_type") or "").startswith("observation_waypoint"):
            continue
        x, y = transform(float(anchor.get("x", 0.0)), float(anchor.get("y", 0.0)))
        draw.rectangle((x - 9, y - 9, x + 9, y + 9), outline=(126, 34, 206, 235), width=2)
        label = str(anchor.get("label") or anchor.get("category") or "")
        if label:
            _draw_label(draw, x + 12, y - 9, label[:26])
    robot_pose = payload.get("robot_pose") or {}
    if robot_pose:
        x, y = transform(float(robot_pose.get("x", 0.0)), float(robot_pose.get("y", 0.0)))
        draw.ellipse((x - 13, y - 13, x + 13, y + 13), fill=(46, 88, 178, 245))
        draw.ellipse((x - 18, y - 18, x + 18, y + 18), outline=(30, 64, 130, 190), width=2)
        _draw_label(draw, x + 16, y - 9, "robot")
    _draw_semantic_map_legend(draw, width=width)
    image.save(output_path, format="PNG")


def _semantic_map_transform(payload: dict[str, Any], *, width: int, height: int) -> Any:
    xs: list[float] = []
    ys: list[float] = []

    def add_pose(item: Any) -> None:
        pose = _map_pose(item)
        if pose:
            xs.append(pose["x"])
            ys.append(pose["y"])

    for room in payload.get("rooms") or []:
        for point in room.get("polygon") or []:
            add_pose(point)
    for key in ("fixtures", "waypoints", "public_semantic_anchors", "trajectory"):
        for item in payload.get(key) or []:
            add_pose(item)
    add_pose(payload.get("robot_pose"))
    min_x, max_x = (min(xs), max(xs)) if xs else (0.0, 1.0)
    min_y, max_y = (min(ys), max(ys)) if ys else (0.0, 1.0)
    x_span = max(max_x - min_x, 1.0)
    y_span = max(max_y - min_y, 1.0)
    margin_x = 58
    margin_top = 88
    margin_bottom = 58
    scale = min((width - margin_x * 2) / x_span, (height - margin_top - margin_bottom) / y_span)

    def transform(x: float, y: float) -> tuple[int, int]:
        return (
            int(margin_x + (x - min_x) * scale),
            int(height - margin_bottom - (y - min_y) * scale),
        )

    return transform


def _draw_label(draw: ImageDraw.ImageDraw, x: int, y: int, text: str) -> None:
    if not text:
        return
    text_box = draw.textbbox((x, y), text)
    draw.rounded_rectangle(
        (text_box[0] - 4, text_box[1] - 2, text_box[2] + 4, text_box[3] + 2),
        radius=3,
        fill=(255, 255, 255, 230),
        outline=(213, 220, 230, 230),
    )
    draw.text((x, y), text, fill=(51, 65, 85, 255))


def _draw_semantic_map_legend(draw: ImageDraw.ImageDraw, *, width: int) -> None:
    items = [
        ((35, 134, 90), "visited waypoint"),
        ((148, 163, 184), "unvisited waypoint"),
        ((245, 158, 11), "trajectory"),
        ((126, 34, 206), "semantic anchor"),
        ((46, 88, 178), "robot"),
    ]
    x = width - 250
    y = 22
    draw.rounded_rectangle(
        (x - 14, y - 10, width - 28, y + 110),
        radius=6,
        fill=(255, 255, 255, 235),
        outline=(213, 220, 230, 230),
    )
    for index, (color, label) in enumerate(items):
        row_y = y + index * 20
        draw.rectangle((x, row_y + 3, x + 12, row_y + 15), fill=(*color, 240))
        draw.text((x + 20, row_y), label, fill=(51, 65, 85, 255))

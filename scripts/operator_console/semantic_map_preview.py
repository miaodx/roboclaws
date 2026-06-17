from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageDraw

WAYPOINT_COLOR = (99, 102, 241)
RECEPTACLE_COLOR = (86, 103, 140)
OBJECT_COLOR = (245, 158, 11)
SELECTED_OBJECT_COLOR = (239, 68, 68)
ROBOT_PATH_COLOR = (37, 99, 235)
ROBOT_HEADING_COLOR = (15, 23, 42)
ROOM_BORDER_COLOR = (111, 124, 138)
BACKGROUND_COLOR = (246, 248, 247)


def render_semantic_map_preview(
    state: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    alignment: dict[str, Any],
    world_label: str,
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), BACKGROUND_COLOR)
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(190, 201, 195), width=2)
    projection_summary = semantic_map_preview_projection_summary(
        state,
        metric_map=metric_map,
        alignment=alignment,
    )
    _draw_rooms(draw, state, alignment=alignment, width=width, height=height)
    _draw_waypoints(
        draw,
        projection_summary=projection_summary,
        alignment=alignment,
        width=width,
        height=height,
    )
    _draw_receptacles(draw, state, alignment=alignment, width=width, height=height)
    _draw_objects(draw, state, alignment=alignment, width=width, height=height)
    _draw_trajectory(draw, state, alignment=alignment, width=width, height=height)
    _draw_legend(draw, world_label, projection_summary=projection_summary, width=width)
    return image


def semantic_map_preview_projection_summary(
    state: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    alignment: dict[str, Any],
) -> dict[str, Any]:
    waypoints = _public_waypoints(metric_map)
    projected = _projected_waypoints(state, metric_map=metric_map, alignment=alignment)
    remapped = [item for item in projected if item["projection"] == "room_remapped"]
    raw_scene = [item for item in projected if item["projection"] == "raw_scene"]
    skipped = max(len(waypoints) - len(projected), 0)
    bounds = _point_bounds(projected)
    return {
        "schema": "operator_console_semantic_map_projection_v1",
        "waypoint_count": len(waypoints),
        "rendered_waypoint_count": len(projected),
        "room_remapped_waypoint_count": len(remapped),
        "raw_scene_waypoint_count": len(raw_scene),
        "skipped_waypoint_count": skipped,
        "projected_waypoint_bounds": bounds,
        "projected_waypoints": projected,
    }


def _draw_rooms(
    draw: ImageDraw.ImageDraw,
    state: dict[str, Any],
    *,
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    room_fills = [
        (229, 217, 238),
        (215, 235, 238),
        (219, 238, 227),
        (221, 230, 244),
        (241, 229, 213),
    ]
    room_names = _semantic_room_names(state)
    for index, outline in enumerate(state.get("room_outlines") or []):
        if not isinstance(outline, dict):
            continue
        rect = _outline_screen_rect(outline, alignment, width=width, height=height)
        if rect is None:
            continue
        left, top, right, bottom = rect
        fill = room_fills[index % len(room_fills)]
        draw.rectangle((left, top, right, bottom), fill=fill, outline=ROOM_BORDER_COLOR, width=2)
        label = room_names.get(str(outline.get("room_id") or "")) or str(
            outline.get("label") or "Room"
        )
        label_x = int(round((left + right) / 2))
        label_y = int(round((top + bottom) / 2))
        draw.text((label_x - max(14, len(label) * 3), label_y - 6), label, fill=(45, 55, 72))


def _draw_waypoints(
    draw: ImageDraw.ImageDraw,
    *,
    projection_summary: dict[str, Any],
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    for waypoint in projection_summary.get("projected_waypoints") or []:
        x, y = _project_to_aligned_preview(
            float(waypoint.get("x") or 0.0),
            float(waypoint.get("y") or 0.0),
            alignment,
            width=width,
            height=height,
        )
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=WAYPOINT_COLOR)


def _draw_receptacles(
    draw: ImageDraw.ImageDraw,
    state: dict[str, Any],
    *,
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    for receptacle in (state.get("receptacles") or {}).values():
        if not isinstance(receptacle, dict) or not _is_vec(receptacle.get("position"), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(receptacle["position"][0]),
            float(receptacle["position"][1]),
            alignment,
            width=width,
            height=height,
        )
        draw.rounded_rectangle((x - 5, y - 5, x + 5, y + 5), radius=3, fill=RECEPTACLE_COLOR)


def _draw_objects(
    draw: ImageDraw.ImageDraw,
    state: dict[str, Any],
    *,
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    selected_object_ids = set(str(item) for item in state.get("selected_object_ids") or [])
    for object_id, obj in (state.get("objects") or {}).items():
        if not isinstance(obj, dict) or not _is_vec(obj.get("position"), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(obj["position"][0]),
            float(obj["position"][1]),
            alignment,
            width=width,
            height=height,
        )
        color = SELECTED_OBJECT_COLOR if str(object_id) in selected_object_ids else OBJECT_COLOR
        radius = 5 if str(object_id) in selected_object_ids else 3
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def _draw_trajectory(
    draw: ImageDraw.ImageDraw,
    state: dict[str, Any],
    *,
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    trajectory = [
        item
        for item in state.get("robot_trajectory") or []
        if isinstance(item, dict) and "x" in item and "y" in item
    ]
    projected_path = [
        _project_to_aligned_preview(
            float(pose["x"]),
            float(pose["y"]),
            alignment,
            width=width,
            height=height,
        )
        for pose in trajectory
    ]
    if len(projected_path) >= 2:
        draw.line(projected_path, fill=ROBOT_PATH_COLOR, width=4)
    for index, (x, y) in enumerate(projected_path):
        radius = 8 if index == len(projected_path) - 1 else 4
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=ROBOT_PATH_COLOR)
    if trajectory:
        _draw_heading(draw, projected_path[-1], float(trajectory[-1].get("theta") or 0.0))


def _draw_heading(draw: ImageDraw.ImageDraw, position: tuple[int, int], heading: float) -> None:
    x, y = position
    tip = (int(round(x + math.cos(heading) * 20)), int(round(y - math.sin(heading) * 20)))
    left = (
        int(round(x + math.cos(heading + 2.45) * 12)),
        int(round(y - math.sin(heading + 2.45) * 12)),
    )
    right = (
        int(round(x + math.cos(heading - 2.45) * 12)),
        int(round(y - math.sin(heading - 2.45) * 12)),
    )
    draw.polygon([tip, left, right], fill=ROBOT_HEADING_COLOR)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    world_label: str,
    *,
    projection_summary: dict[str, Any],
    width: int,
) -> None:
    panel_width = min(max(width * 0.2, 156), 180)
    left = 18
    top = 16
    right = left + panel_width
    bottom = top + 164
    draw.rectangle((left, top, right, bottom), fill=BACKGROUND_COLOR, outline=(190, 201, 195))
    draw.text((28, 24), world_label, fill=(31, 41, 55))
    draw.text((28, 40), "Semantic map aligned to top-down bounds", fill=(92, 105, 118))
    rows = [
        ("room", (229, 217, 238), "room bounds"),
        ("waypoint", WAYPOINT_COLOR, "waypoint"),
        ("receptacle", RECEPTACLE_COLOR, "receptacle"),
        ("object", OBJECT_COLOR, "object"),
        ("selected", SELECTED_OBJECT_COLOR, "selected"),
        ("path", ROBOT_PATH_COLOR, "robot path"),
    ]
    for index, (kind, color, label) in enumerate(rows):
        row_y = 64 + index * 17
        if kind == "waypoint":
            draw.ellipse((30, row_y + 3, 38, row_y + 11), fill=color)
        elif kind == "receptacle":
            draw.rounded_rectangle((29, row_y + 2, 39, row_y + 12), radius=2, fill=color)
        elif kind == "path":
            draw.line((28, row_y + 7, 40, row_y + 7), fill=color, width=3)
            draw.ellipse((33, row_y + 2, 43, row_y + 12), fill=color)
        else:
            draw.rectangle((29, row_y + 3, 39, row_y + 11), fill=color)
        draw.text((48, row_y), label, fill=(51, 65, 85))
    rendered = int(projection_summary.get("rendered_waypoint_count") or 0)
    remapped = int(projection_summary.get("room_remapped_waypoint_count") or 0)
    total = int(projection_summary.get("waypoint_count") or 0)
    skipped = int(projection_summary.get("skipped_waypoint_count") or 0)
    draw.text((28, 169), f"WP {rendered}/{total}; remap {remapped}", fill=(92, 105, 118))
    if skipped:
        draw.text((28, 184), f"WP skipped {skipped} outside scene bounds", fill=(146, 64, 14))


def _semantic_room_names(state: dict[str, Any]) -> dict[str, str]:
    room_ids = [str(item.get("room_id") or "") for item in state.get("room_outlines") or []]
    if len(room_ids) == 2:
        return {room_ids[0]: "Bedroom", room_ids[1]: "Bathroom"}
    if len(room_ids) == 4:
        return {
            room_ids[0]: "Bedroom",
            room_ids[1]: "Bathroom",
            room_ids[2]: "Kitchen",
            room_ids[3]: "Living",
        }
    return {}


def _outline_screen_rect(
    outline: dict[str, Any],
    alignment: dict[str, Any],
    *,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    center = outline.get("center")
    half_extents = outline.get("half_extents")
    if not _is_vec(center, 2) or not _is_vec(half_extents, 2):
        return None
    x1, y1 = _project_to_aligned_preview(
        float(center[0]) - float(half_extents[0]),
        float(center[1]) - float(half_extents[1]),
        alignment,
        width=width,
        height=height,
    )
    x2, y2 = _project_to_aligned_preview(
        float(center[0]) + float(half_extents[0]),
        float(center[1]) + float(half_extents[1]),
        alignment,
        width=width,
        height=height,
    )
    return min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)


def _project_to_aligned_preview(
    x: float,
    y: float,
    alignment: dict[str, Any],
    *,
    width: int,
    height: int,
) -> tuple[int, int]:
    bounds = alignment["bounds"]
    min_x = float(bounds["min_x"])
    max_x = float(bounds["max_x"])
    min_y = float(bounds["min_y"])
    max_y = float(bounds["max_y"])
    px = (float(x) - min_x) / max(max_x - min_x, 0.001) * (width - 1)
    py = (1.0 - (float(y) - min_y) / max(max_y - min_y, 0.001)) * (height - 1)
    return int(round(px)), int(round(py))


def _projected_waypoints(
    state: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    alignment: dict[str, Any],
) -> list[dict[str, Any]]:
    scene_rooms = _scene_room_bounds_by_id(state)
    metric_rooms = _metric_room_bounds_by_id(metric_map)
    projected = []
    for waypoint in _public_waypoints(metric_map):
        if not _is_vec((waypoint.get("x"), waypoint.get("y")), 2):
            continue
        room_id = str(waypoint.get("room_id") or "")
        remapped = _remap_point_between_room_bounds(
            float(waypoint.get("x") or 0.0),
            float(waypoint.get("y") or 0.0),
            source_bounds=metric_rooms.get(room_id),
            target_bounds=scene_rooms.get(room_id),
        )
        if remapped is not None:
            x, y = remapped
            projection = "room_remapped"
        else:
            x = float(waypoint.get("x") or 0.0)
            y = float(waypoint.get("y") or 0.0)
            if not _point_within_alignment_bounds(x, y, alignment):
                continue
            projection = "raw_scene"
        projected.append(
            {
                "waypoint_id": str(waypoint.get("waypoint_id") or ""),
                "room_id": room_id,
                "x": round(float(x), 6),
                "y": round(float(y), 6),
                "projection": projection,
            }
        )
    return projected


def _scene_room_bounds_by_id(state: dict[str, Any]) -> dict[str, dict[str, float]]:
    rooms: dict[str, dict[str, float]] = {}
    for outline in state.get("room_outlines") or []:
        if not isinstance(outline, dict):
            continue
        room_id = str(outline.get("room_id") or "")
        center = outline.get("center")
        half_extents = outline.get("half_extents")
        if not room_id or not _is_vec(center, 2) or not _is_vec(half_extents, 2):
            continue
        cx = float(center[0])
        cy = float(center[1])
        hx = abs(float(half_extents[0]))
        hy = abs(float(half_extents[1]))
        rooms[room_id] = {"min_x": cx - hx, "max_x": cx + hx, "min_y": cy - hy, "max_y": cy + hy}
    return rooms


def _metric_room_bounds_by_id(metric_map: dict[str, Any]) -> dict[str, dict[str, float]]:
    rooms: dict[str, dict[str, float]] = {}
    for room in metric_map.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        points = [
            (float(point.get("x")), float(point.get("y")))
            for point in room.get("polygon") or []
            if isinstance(point, dict) and point.get("x") is not None and point.get("y") is not None
        ]
        if not room_id or not points:
            continue
        xs = [point[0] for point in points]
        ys = [point[1] for point in points]
        rooms[room_id] = {"min_x": min(xs), "max_x": max(xs), "min_y": min(ys), "max_y": max(ys)}
    return rooms


def _remap_point_between_room_bounds(
    x: float,
    y: float,
    *,
    source_bounds: dict[str, float] | None,
    target_bounds: dict[str, float] | None,
) -> tuple[float, float] | None:
    if not source_bounds or not target_bounds:
        return None
    source_span_x = max(float(source_bounds["max_x"]) - float(source_bounds["min_x"]), 0.001)
    source_span_y = max(float(source_bounds["max_y"]) - float(source_bounds["min_y"]), 0.001)
    x_ratio = (x - float(source_bounds["min_x"])) / source_span_x
    y_ratio = (y - float(source_bounds["min_y"])) / source_span_y
    target_x = float(target_bounds["min_x"]) + x_ratio * (
        float(target_bounds["max_x"]) - float(target_bounds["min_x"])
    )
    target_y = float(target_bounds["min_y"]) + y_ratio * (
        float(target_bounds["max_y"]) - float(target_bounds["min_y"])
    )
    return target_x, target_y


def _point_within_alignment_bounds(x: float, y: float, alignment: dict[str, Any]) -> bool:
    bounds = alignment.get("bounds") or {}
    return (
        float(bounds.get("min_x", x)) <= x <= float(bounds.get("max_x", x))
        and float(bounds.get("min_y", y)) <= y <= float(bounds.get("max_y", y))
    )


def _point_bounds(points: list[dict[str, Any]]) -> dict[str, float]:
    if not points:
        return {}
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    return {
        "min_x": round(min(xs), 6),
        "max_x": round(max(xs), 6),
        "min_y": round(min(ys), 6),
        "max_y": round(max(ys), 6),
    }


def _public_waypoints(metric_map: dict[str, Any]) -> list[dict[str, Any]]:
    waypoints = metric_map.get("inspection_waypoints")
    if not isinstance(waypoints, list):
        return []
    return [
        dict(item)
        for item in waypoints
        if isinstance(item, dict) and str(item.get("waypoint_id") or "")
    ]


def _is_vec(value: Any, min_length: int) -> bool:
    return isinstance(value, (list, tuple)) and len(value) >= min_length

from __future__ import annotations

import math
from typing import Any

from PIL import Image, ImageDraw


def render_semantic_map_preview(
    state: dict[str, Any],
    *,
    metric_map: dict[str, Any],
    alignment: dict[str, Any],
    world_label: str,
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), (246, 248, 247))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width - 1, height - 1), outline=(190, 201, 195), width=2)
    _draw_rooms(draw, state, alignment=alignment, width=width, height=height)
    _draw_waypoints(draw, metric_map, alignment=alignment, width=width, height=height)
    _draw_receptacles(draw, state, alignment=alignment, width=width, height=height)
    _draw_objects(draw, state, alignment=alignment, width=width, height=height)
    _draw_trajectory(draw, state, alignment=alignment, width=width, height=height)
    _draw_legend(draw, world_label)
    return image


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
        draw.rectangle((left, top, right, bottom), fill=fill, outline=(111, 124, 138), width=2)
        label = room_names.get(str(outline.get("room_id") or "")) or str(
            outline.get("label") or "Room"
        )
        label_x = int(round((left + right) / 2))
        label_y = int(round((top + bottom) / 2))
        draw.text((label_x - max(14, len(label) * 3), label_y - 6), label, fill=(45, 55, 72))


def _draw_waypoints(
    draw: ImageDraw.ImageDraw,
    metric_map: dict[str, Any],
    *,
    alignment: dict[str, Any],
    width: int,
    height: int,
) -> None:
    for waypoint in _public_waypoints(metric_map):
        if not _is_vec((waypoint.get("x"), waypoint.get("y")), 2):
            continue
        x, y = _project_to_aligned_preview(
            float(waypoint.get("x") or 0.0),
            float(waypoint.get("y") or 0.0),
            alignment,
            width=width,
            height=height,
        )
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=(99, 102, 241))


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
        draw.rounded_rectangle((x - 5, y - 5, x + 5, y + 5), radius=3, fill=(86, 103, 140))


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
        color = (239, 68, 68) if str(object_id) in selected_object_ids else (245, 158, 11)
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
        draw.line(projected_path, fill=(37, 99, 235), width=4)
    for index, (x, y) in enumerate(projected_path):
        radius = 8 if index == len(projected_path) - 1 else 4
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(37, 99, 235))
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
    draw.polygon([tip, left, right], fill=(15, 23, 42))


def _draw_legend(draw: ImageDraw.ImageDraw, world_label: str) -> None:
    draw.rectangle((18, 16, 280, 56), fill=(246, 248, 247))
    draw.text((28, 24), world_label, fill=(31, 41, 55))
    draw.text((28, 40), "Semantic map aligned to top-down bounds", fill=(92, 105, 118))


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

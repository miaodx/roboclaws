#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from roboclaws.maps.bundle import parse_map_yaml  # noqa: E402
from roboclaws.maps.rasterize import load_pgm, world_to_grid  # noqa: E402

_COLORS = [
    (75, 135, 190, 92),
    (235, 150, 70, 92),
    (95, 170, 115, 92),
    (180, 110, 170, 92),
    (220, 190, 70, 92),
    (120, 120, 210, 92),
]
_LEGEND_WIDTH = 620
_LEGEND_MARGIN = 24


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a top-down confirmation image for room semantic overlay bundles."
    )
    parser.add_argument("bundle_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    render_room_semantic_topdown(args.bundle_dir, args.output)
    print(f"room semantic topdown rendered: {args.output}")


def render_room_semantic_topdown(bundle_dir: Path, output_path: Path) -> None:
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    overlay_path = bundle_dir / "room_semantic_overlay.json"
    overlay_payload = (
        json.loads(overlay_path.read_text(encoding="utf-8")) if overlay_path.is_file() else {}
    )
    map_yaml = parse_map_yaml((bundle_dir / "map.yaml").read_text(encoding="utf-8"))
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else [0, 0, 0]
    grid = load_pgm(
        bundle_dir / str(map_yaml.get("image") or "map.pgm"),
        resolution_m=float(map_yaml.get("resolution") or 0.05),
        origin_x=float(origin[0]),
        origin_y=float(origin[1]),
    )
    base = Image.open(bundle_dir / str(map_yaml.get("image") or "map.pgm")).convert("RGB")
    map_image = Image.new("RGB", base.size, (248, 249, 251))
    map_image.paste(base)
    map_image = map_image.resize(
        (base.width * 2, base.height * 2),
        resample=Image.Resampling.NEAREST,
    )
    alpha_layer = Image.new("RGBA", map_image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(alpha_layer)
    scale = map_image.width / max(base.width, 1)

    rooms_by_navigation_area: dict[str, list[dict[str, Any]]] = {}
    for room in semantics.get("rooms") or []:
        rooms_by_navigation_area.setdefault(str(room.get("navigation_area_id") or ""), []).append(
            room
        )

    drawn_navigation_areas: set[str] = set()
    legend_entries: list[dict[str, Any]] = []
    for index, room in enumerate(semantics.get("rooms") or []):
        navigation_area_id = str(room.get("navigation_area_id") or room.get("room_id") or "")
        if navigation_area_id in drawn_navigation_areas:
            continue
        drawn_navigation_areas.add(navigation_area_id)
        polygon = room.get("polygon") or []
        if len(polygon) < 3:
            continue
        points = [_scale_point(world_to_grid_point(point, grid), scale) for point in polygon]
        color = _COLORS[index % len(_COLORS)]
        draw.polygon(points, fill=color, outline=(*color[:3], 220))
        cx, cy = _polygon_center(points)
        area_rooms = rooms_by_navigation_area.get(navigation_area_id) or [room]
        tag = f"A{len(legend_entries) + 1}"
        _draw_tag(draw, tag, cx, cy)
        legend_entries.append(
            {
                "tag": tag,
                "navigation_area_id": navigation_area_id,
                "rooms": area_rooms,
                "color": color,
            }
        )

    for waypoint in semantics.get("inspection_waypoints") or []:
        x, y = _scale_point(
            world_to_grid(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)), grid),
            scale,
        )
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(20, 88, 55, 255))
        draw.text((x + 7, y - 4), str(waypoint.get("waypoint_id") or "")[:20], fill=(20, 70, 48))

    map_image = Image.alpha_composite(map_image.convert("RGBA"), alpha_layer).convert("RGB")
    image = Image.new("RGB", (map_image.width + _LEGEND_WIDTH, map_image.height), (248, 249, 251))
    image.paste(map_image, (0, 0))
    legend_draw = ImageDraw.Draw(image)
    _draw_legend(legend_draw, legend_entries, overlay_payload, (map_image.width, 0), image.size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


def world_to_grid_point(point: dict[str, Any], grid: Any) -> tuple[int, int]:
    return world_to_grid(float(point.get("x", 0.0)), float(point.get("y", 0.0)), grid)


def _scale_point(point: tuple[int, int], scale: float) -> tuple[int, int]:
    return (int(point[0] * scale), int(point[1] * scale))


def _polygon_center(points: list[tuple[int, int]]) -> tuple[int, int]:
    if not points:
        return (0, 0)
    return (
        sum(point[0] for point in points) // len(points),
        sum(point[1] for point in points) // len(points),
    )


def _draw_tag(draw: ImageDraw.ImageDraw, tag: str, cx: int, cy: int) -> None:
    x0 = cx - 14
    y0 = cy - 10
    x1 = cx + 14
    y1 = cy + 10
    draw.rectangle((x0, y0, x1, y1), fill=(255, 255, 255, 235), outline=(20, 28, 38, 255))
    draw.text((x0 + 5, y0 + 4), tag, fill=(20, 28, 38, 255))


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    entries: list[dict[str, Any]],
    overlay: dict[str, Any],
    origin: tuple[int, int],
    size: tuple[int, int],
) -> None:
    left = origin[0] + _LEGEND_MARGIN
    top = origin[1] + _LEGEND_MARGIN
    right = size[0] - _LEGEND_MARGIN
    draw.rectangle(
        (origin[0], origin[1], size[0], size[1]),
        fill=(246, 247, 249),
    )
    draw.text((left, top), "B1 / Map12 room semantics", fill=(20, 28, 38))
    y = top + 30
    for entry in entries:
        color = tuple(entry["color"])
        tag = str(entry["tag"])
        area_id = str(entry["navigation_area_id"])
        draw.rectangle((left, y + 2, left + 18, y + 20), fill=color[:3], outline=(70, 78, 88))
        draw.text((left + 28, y + 4), f"{tag}  Map12 area: {area_id}", fill=(20, 28, 38))
        y += 28
        for room in entry["rooms"]:
            label = str(room.get("room_label") or room.get("room_id") or "")
            category = str(room.get("category") or "room_area")
            status = str(room.get("review_status") or "")
            line = f"- {label} ({category})"
            if status and status != "accepted":
                line += f" [{status}]"
            for wrapped in _wrap_text(line, width=54):
                draw.text((left + 30, y), wrapped, fill=(38, 48, 62))
                y += 17
        y += 14
    _draw_review_box(draw, overlay, (left, max(y, size[1] - 130), right, size[1] - _LEGEND_MARGIN))


def _wrap_text(text: str, *, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if len(candidate) <= width:
            current = candidate
            continue
        if current:
            lines.append(current)
        current = word
    if current:
        lines.append(current)
    return lines or [text]


def _draw_review_box(
    draw: ImageDraw.ImageDraw,
    overlay: dict[str, Any],
    box: tuple[int, int, int, int],
) -> None:
    review = overlay.get("review_queue") if isinstance(overlay.get("review_queue"), list) else []
    if not review:
        text = "Review queue: none"
    else:
        lines = ["Review queue:"]
        lines.extend(f"- {item.get('room_id')}: {item.get('proposed_category')}" for item in review)
        text = "\n".join(lines)
    x0, y0, x1, y1 = box
    draw.rectangle((x0, y0, x1, y1), fill=(255, 255, 255, 225), outline=(90, 100, 110, 255))
    draw.multiline_text((x0 + 10, y0 + 10), text, fill=(20, 28, 38, 255), spacing=3)


if __name__ == "__main__":
    main()

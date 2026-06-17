from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from PIL import Image, ImageDraw

FREE_PIXEL = 254
OCCUPIED_PIXEL = 0
UNKNOWN_PIXEL = 205


@dataclass(frozen=True)
class OccupancyGrid:
    width: int
    height: int
    resolution_m: float
    origin_x: float
    origin_y: float
    rows: tuple[tuple[int, ...], ...]

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.width and 0 <= row < self.height

    def is_free_cell(self, col: int, row: int) -> bool:
        return self.in_bounds(col, row) and self.rows[row][col] >= 250

    def is_free_world(self, x: float, y: float) -> bool:
        col, row = world_to_grid(x, y, self)
        return self.is_free_cell(col, row)


def occupancy_grid_from_metric_map(
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
) -> OccupancyGrid:
    resolution = max(float(metric_map.get("resolution_m") or 0.05), 0.001)
    origin = metric_map.get("origin") if isinstance(metric_map.get("origin"), dict) else {}
    origin_x = float(origin.get("x") or 0.0)
    origin_y = float(origin.get("y") or 0.0)
    width = _metric_map_dimension(metric_map, "width")
    height = _metric_map_dimension(metric_map, "height")
    width, height = _expand_dimensions_for_public_geometry(
        metric_map,
        static_fixture_projection,
        width=width,
        height=height,
        resolution_m=resolution,
        origin_x=origin_x,
        origin_y=origin_y,
    )
    image = Image.new("L", (width, height), OCCUPIED_PIXEL)
    draw = ImageDraw.Draw(image)
    grid_shell = OccupancyGrid(
        width=width,
        height=height,
        resolution_m=resolution,
        origin_x=origin_x,
        origin_y=origin_y,
        rows=tuple(tuple(OCCUPIED_PIXEL for _ in range(width)) for _ in range(height)),
    )

    rooms = metric_map.get("rooms") or []
    for room in rooms:
        polygon = room.get("polygon") or []
        if len(polygon) < 3:
            continue
        points = [
            world_to_grid(float(point.get("x", 0.0)), float(point.get("y", 0.0)), grid_shell)
            for point in polygon
        ]
        draw.polygon(points, fill=FREE_PIXEL)

    if not rooms:
        draw.rectangle((1, 1, width - 2, height - 2), fill=FREE_PIXEL)

    centers = _room_centers(metric_map)
    for way in metric_map.get("driveable_ways") or []:
        start = centers.get(str(way.get("from_room_id") or ""))
        goal = centers.get(str(way.get("to_room_id") or ""))
        if start is None or goal is None:
            continue
        draw.line(
            (
                world_to_grid(start[0], start[1], grid_shell),
                world_to_grid(goal[0], goal[1], grid_shell),
            ),
            fill=FREE_PIXEL,
            width=max(3, int(round(0.35 / resolution))),
        )

    for fixture in fixtures_from_static_projection(static_fixture_projection):
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        footprint = fixture.get("footprint") if isinstance(fixture.get("footprint"), dict) else {}
        x = float(pose.get("x") or 0.0)
        y = float(pose.get("y") or 0.0)
        width_m = float(footprint.get("width_m") or 0.45)
        depth_m = float(footprint.get("depth_m") or 0.35)
        left, top = world_to_grid(x - width_m / 2.0, y + depth_m / 2.0, grid_shell)
        right, bottom = world_to_grid(x + width_m / 2.0, y - depth_m / 2.0, grid_shell)
        draw.rectangle(
            (min(left, right), min(top, bottom), max(left, right), max(top, bottom)),
            fill=OCCUPIED_PIXEL,
        )

    rows = tuple(tuple(image.getpixel((col, row)) for col in range(width)) for row in range(height))
    return OccupancyGrid(
        width=width,
        height=height,
        resolution_m=resolution,
        origin_x=origin_x,
        origin_y=origin_y,
        rows=rows,
    )


def write_pgm(path: Any, grid: OccupancyGrid) -> None:
    text_rows = [" ".join(str(value) for value in row) for row in grid.rows]
    path.write_text(
        f"P2\n{grid.width} {grid.height}\n255\n" + "\n".join(text_rows) + "\n",
        encoding="ascii",
    )


def load_pgm(
    path: Any, *, resolution_m: float = 0.05, origin_x: float = 0.0, origin_y: float = 0.0
) -> OccupancyGrid:
    data = path.read_bytes()
    if data.startswith(b"P2"):
        tokens = _pgm_tokens(data.decode("ascii", errors="ignore"))
        magic = next(tokens)
        if magic != "P2":
            raise ValueError(f"unsupported PGM magic: {magic}")
        width = int(next(tokens))
        height = int(next(tokens))
        max_value = int(next(tokens))
        if max_value <= 0:
            raise ValueError("invalid PGM max value")
        values = [int(next(tokens)) for _ in range(width * height)]
        rows = tuple(
            tuple(
                int(round(value / max_value * 255))
                for value in values[row * width : (row + 1) * width]
            )
            for row in range(height)
        )
        return OccupancyGrid(width, height, resolution_m, origin_x, origin_y, rows)

    image = Image.open(path).convert("L")
    width, height = image.size
    rows = tuple(tuple(image.getpixel((col, row)) for col in range(width)) for row in range(height))
    return OccupancyGrid(width, height, resolution_m, origin_x, origin_y, rows)


def world_to_grid(x: float, y: float, grid: OccupancyGrid) -> tuple[int, int]:
    col = int(round((x - grid.origin_x) / grid.resolution_m))
    row = grid.height - 1 - int(round((y - grid.origin_y) / grid.resolution_m))
    return col, row


def fixtures_from_static_projection(
    static_fixture_projection: dict[str, Any],
) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for room in static_fixture_projection.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            item = dict(fixture)
            item.setdefault("room_id", room.get("room_id", ""))
            fixtures.append(item)
    return fixtures


def _room_centers(metric_map: dict[str, Any]) -> dict[str, tuple[float, float]]:
    centers: dict[str, tuple[float, float]] = {}
    for room in metric_map.get("rooms") or []:
        room_id = str(room.get("room_id") or "")
        polygon = room.get("polygon") or []
        if not room_id or not polygon:
            continue
        xs = [float(point.get("x", 0.0)) for point in polygon]
        ys = [float(point.get("y", 0.0)) for point in polygon]
        centers[room_id] = (sum(xs) / len(xs), sum(ys) / len(ys))
    return centers


def _pgm_tokens(text: str):
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        yield from line.split()


def _metric_map_dimension(
    metric_map: dict[str, Any], key: str, *, lower: int = 16, upper: int = 4096
) -> int:
    raw = metric_map.get(key)
    if raw is None:
        raise ValueError(f"metric_map.{key} is required for occupancy grid projection")
    value = _dimension_int(raw, field=f"metric_map.{key}", lower=lower, upper=upper)
    if not lower <= value <= upper:
        raise ValueError(
            f"metric_map.{key} must be an integer between {lower} and {upper}, got {raw!r}"
        )
    return value


def _dimension_int(value: Any, *, field: str, lower: int, upper: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field} must be an integer between {lower} and {upper}, got {value!r}"
        ) from exc
    if isinstance(value, float) and not value.is_integer():
        raise ValueError(f"{field} must be an integer between {lower} and {upper}, got {value!r}")
    return parsed


def _clamped_dimension(value: int, *, lower: int, upper: int) -> int:
    return max(lower, min(value, upper))


def _expand_dimensions_for_public_geometry(
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    *,
    width: int,
    height: int,
    resolution_m: float,
    origin_x: float,
    origin_y: float,
) -> tuple[int, int]:
    max_x = origin_x + (width - 1) * resolution_m
    max_y = origin_y + (height - 1) * resolution_m
    for x, y in _public_geometry_points(metric_map, static_fixture_projection):
        max_x = max(max_x, x)
        max_y = max(max_y, y)
    margin_m = 0.5
    required_width = int(math.ceil((max_x + margin_m - origin_x) / resolution_m)) + 1
    required_height = int(math.ceil((max_y + margin_m - origin_y) / resolution_m)) + 1
    return (
        _clamped_dimension(required_width, lower=width, upper=4096),
        _clamped_dimension(required_height, lower=height, upper=4096),
    )


def _public_geometry_points(
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
):
    for room in metric_map.get("rooms") or []:
        for point in room.get("polygon") or []:
            yield float(point.get("x", 0.0)), float(point.get("y", 0.0))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        yield float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))
    for fixture in fixtures_from_static_projection(static_fixture_projection):
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        footprint = fixture.get("footprint") if isinstance(fixture.get("footprint"), dict) else {}
        x = float(pose.get("x") or 0.0)
        y = float(pose.get("y") or 0.0)
        half_width = float(footprint.get("width_m") or 0.45) / 2.0
        half_depth = float(footprint.get("depth_m") or 0.35) / 2.0
        yield x - half_width, y - half_depth
        yield x + half_width, y + half_depth

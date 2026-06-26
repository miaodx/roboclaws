from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.core.json_sources import read_json_object

BASE_NAVIGATION_MAP_PREVIEW_ROLE = "base_navigation_map_preview"
RUNTIME_METRIC_MAP_PREVIEW_ROLE = "runtime_metric_map_preview"
TOPDOWN_SCENE_RENDER_ROLE = "topdown_scene_render"

BASE_MAP_SOURCE_FAMILY = "base_navigation_map_bundle"
RUNTIME_MAP_SOURCE_FAMILY = "runtime_metric_map"
SCENE_RENDER_SOURCE_FAMILY = "scene_camera_render"

DEFAULT_PREVIEW_WIDTH = 900
DEFAULT_PREVIEW_HEIGHT = 560
_MAP_MARGIN_X = 46
_MAP_MARGIN_TOP = 58
_MAP_MARGIN_BOTTOM = 44

_AREA_COLORS = (
    (72, 121, 210, 42),
    (20, 184, 166, 42),
    (245, 158, 11, 38),
    (139, 92, 246, 38),
    (14, 165, 233, 40),
)
_AREA_OUTLINES = (
    (31, 79, 168, 210),
    (15, 118, 110, 210),
    (180, 83, 9, 205),
    (109, 40, 217, 205),
    (3, 105, 161, 205),
)
_WAYPOINT_COLOR = (34, 158, 91, 245)
_WAYPOINT_VISITED_COLOR = (22, 101, 52, 255)
_WAYPOINT_UNVISITED_COLOR = (203, 121, 43, 245)
_OBJECT_COLOR = (220, 38, 38, 245)
_SELECTED_OBJECT_COLOR = (239, 68, 68, 255)
_ANCHOR_COLOR = (8, 145, 178, 245)
_TARGET_COLOR = (168, 85, 247, 245)
_ROBOT_PATH_COLOR = (37, 99, 235, 230)
_ROBOT_HEADING_COLOR = (15, 23, 42, 255)
_MANUAL_ADJUSTMENT_COLOR = (168, 85, 247, 255)


@dataclass(frozen=True)
class MapPreviewResult:
    path: Path
    metadata: dict[str, Any]


@dataclass(frozen=True)
class _Projection:
    min_x: float
    max_x: float
    min_y: float
    max_y: float
    width: int
    height: int

    def project(self, x: Any, y: Any) -> tuple[int, int]:
        x_float = _float_or_none(x)
        y_float = _float_or_none(y)
        if x_float is None or y_float is None:
            return (0, 0)
        usable_width = self.width - _MAP_MARGIN_X * 2
        usable_height = self.height - _MAP_MARGIN_TOP - _MAP_MARGIN_BOTTOM
        px = _MAP_MARGIN_X + (x_float - self.min_x) / max(self.max_x - self.min_x, 0.001) * (
            usable_width
        )
        py = (
            self.height
            - _MAP_MARGIN_BOTTOM
            - (y_float - self.min_y) / max(self.max_y - self.min_y, 0.001) * usable_height
        )
        return (int(round(px)), int(round(py)))


def visual_role_metadata(
    *,
    visual_role: str,
    artifact_source_family: str,
    artifact_path: str = "",
    provenance: str = "",
    view: str | None = None,
    role_label: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "visual_role": visual_role,
        "artifact_source_family": artifact_source_family,
        "view": view or visual_role,
        "role_label": role_label or _role_label(visual_role),
    }
    if artifact_path:
        payload["artifact_path"] = artifact_path
    if provenance:
        payload["provenance"] = provenance
    if extra:
        payload.update(dict(extra))
    return payload


def render_base_navigation_map_preview(
    *,
    semantics: dict[str, Any],
    output_path: Path,
    width: int = DEFAULT_PREVIEW_WIDTH,
    height: int = DEFAULT_PREVIEW_HEIGHT,
    provenance: str = "map_bundle_preview_png",
) -> MapPreviewResult:
    metadata = visual_role_metadata(
        visual_role=BASE_NAVIGATION_MAP_PREVIEW_ROLE,
        artifact_source_family=BASE_MAP_SOURCE_FAMILY,
        artifact_path=str(output_path),
        provenance=provenance,
        extra={
            "schema": "map_visual_role_metadata_v1",
            "render_policy": "base_navigation_map_only",
            "contains_runtime_overlays": False,
            "contains_private_truth": False,
            "width": width,
            "height": height,
        },
    )
    image = _render_map_preview(
        semantics=semantics,
        runtime_metric_map=None,
        metadata=metadata,
        width=width,
        height=height,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return MapPreviewResult(path=output_path, metadata=metadata)


def render_runtime_metric_map_preview(
    *,
    runtime_metric_map: dict[str, Any],
    output_path: Path,
    width: int = DEFAULT_PREVIEW_WIDTH,
    height: int = DEFAULT_PREVIEW_HEIGHT,
    provenance: str = "runtime_metric_map_json",
) -> MapPreviewResult:
    semantics = _runtime_map_base_semantics(runtime_metric_map)
    metadata = visual_role_metadata(
        visual_role=RUNTIME_METRIC_MAP_PREVIEW_ROLE,
        artifact_source_family=RUNTIME_MAP_SOURCE_FAMILY,
        artifact_path=str(output_path),
        provenance=provenance,
        extra={
            "schema": "map_visual_role_metadata_v1",
            "render_policy": "base_navigation_map_plus_runtime_overlays",
            "contains_runtime_overlays": True,
            "contains_private_truth": False,
            "width": width,
            "height": height,
            "observed_object_count": len(runtime_metric_map.get("observed_objects") or []),
            "public_semantic_anchor_count": len(
                runtime_metric_map.get("public_semantic_anchors") or []
            ),
            "target_candidate_count": len(runtime_metric_map.get("target_candidates") or []),
        },
    )
    image = _render_map_preview(
        semantics=semantics,
        runtime_metric_map=runtime_metric_map,
        metadata=metadata,
        width=width,
        height=height,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return MapPreviewResult(path=output_path, metadata=metadata)


def render_base_navigation_map_bundle_preview(
    bundle_dir: Path,
    *,
    output_path: Path | None = None,
    width: int = DEFAULT_PREVIEW_WIDTH,
    height: int = DEFAULT_PREVIEW_HEIGHT,
) -> MapPreviewResult:
    bundle_dir = Path(bundle_dir)
    semantics = read_json_object(bundle_dir / "semantics.json", label="Nav2 semantics")
    output_path = output_path or bundle_dir / "preview.png"
    return render_base_navigation_map_preview(
        semantics=semantics,
        output_path=output_path,
        width=width,
        height=height,
    )


def _render_map_preview(
    *,
    semantics: dict[str, Any],
    runtime_metric_map: dict[str, Any] | None,
    metadata: dict[str, Any],
    width: int,
    height: int,
) -> Image.Image:
    image = Image.new("RGB", (width, height), (247, 249, 252))
    draw = ImageDraw.Draw(image, "RGBA")
    projection = _projection(semantics, runtime_metric_map, width=width, height=height)
    _draw_canvas(draw, width=width, height=height, metadata=metadata)
    _draw_navigation_areas(draw, semantics, projection)
    _draw_waypoints(draw, semantics, runtime_metric_map, projection)
    if runtime_metric_map is not None:
        _draw_runtime_overlays(draw, runtime_metric_map, semantics, projection)
    _draw_legend(draw, width=width, height=height, runtime=runtime_metric_map is not None)
    return image


def _draw_canvas(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    metadata: dict[str, Any],
) -> None:
    draw.rectangle((18, 18, width - 18, height - 18), outline=(190, 199, 210, 225), width=2)
    draw.rectangle((28, 26, 312, 94), fill=(255, 255, 255, 226), outline=(213, 220, 230, 230))
    draw.text((42, 38), str(metadata.get("role_label") or ""), fill=(30, 41, 59, 255))
    note = (
        "source map frame; display_frame absent"
        if metadata.get("visual_role") == BASE_NAVIGATION_MAP_PREVIEW_ROLE
        else "runtime overlays on source map frame"
    )
    draw.text((42, 60), note, fill=(86, 95, 112, 255))


def _draw_navigation_areas(
    draw: ImageDraw.ImageDraw,
    semantics: dict[str, Any],
    projection: _Projection,
) -> None:
    for index, area in enumerate(semantics.get("rooms") or []):
        points = _project_polygon(area.get("polygon"), projection)
        if len(points) < 3:
            continue
        fill = _AREA_COLORS[index % len(_AREA_COLORS)]
        outline = _AREA_OUTLINES[index % len(_AREA_OUTLINES)]
        draw.polygon(points, fill=fill, outline=outline)
        label = str(
            area.get("room_label")
            or area.get("semantic_label")
            or area.get("category")
            or area.get("room_id")
            or area.get("navigation_area_id")
            or ""
        )
        if label:
            cx = sum(point[0] for point in points) / len(points)
            cy = sum(point[1] for point in points) / len(points)
            draw.text((cx - 28, cy - 7), label[:18], fill=(15, 39, 82, 230))


def _draw_waypoints(
    draw: ImageDraw.ImageDraw,
    semantics: dict[str, Any],
    runtime_metric_map: dict[str, Any] | None,
    projection: _Projection,
) -> None:
    visited = _visited_waypoint_ids(runtime_metric_map)
    for waypoint in semantics.get("inspection_waypoints") or []:
        point = _point_from_mapping(waypoint)
        if point is None:
            continue
        x, y = projection.project(point[0], point[1])
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if runtime_metric_map is None:
            color = _WAYPOINT_COLOR
        else:
            color = _WAYPOINT_VISITED_COLOR if waypoint_id in visited else _WAYPOINT_UNVISITED_COLOR
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=color)


def _draw_runtime_overlays(
    draw: ImageDraw.ImageDraw,
    runtime_metric_map: dict[str, Any],
    semantics: dict[str, Any],
    projection: _Projection,
) -> None:
    waypoint_points = _waypoint_points(semantics, runtime_metric_map)
    _draw_points(
        draw,
        _runtime_rows_with_positions(runtime_metric_map.get("public_semantic_anchors") or []),
        projection,
        color=_ANCHOR_COLOR,
        radius=6,
    )
    _draw_points(
        draw,
        _runtime_rows_with_positions(runtime_metric_map.get("target_candidates") or []),
        projection,
        color=_TARGET_COLOR,
        radius=7,
    )
    _draw_points(
        draw,
        _runtime_rows_with_positions(runtime_metric_map.get("observed_objects") or []),
        projection,
        color=_OBJECT_COLOR,
        radius=6,
        selected_color=_SELECTED_OBJECT_COLOR,
    )
    robot_path = _robot_path(runtime_metric_map)
    if not robot_path and waypoint_points:
        robot_path = _path_from_visited_waypoints(runtime_metric_map, waypoint_points)
    _draw_robot_path(draw, robot_path, projection)
    robot_pose = _robot_pose(runtime_metric_map, robot_path)
    if robot_pose is not None:
        _draw_robot_pose(draw, robot_pose, projection)


def _draw_points(
    draw: ImageDraw.ImageDraw,
    rows: list[dict[str, Any]],
    projection: _Projection,
    *,
    color: tuple[int, int, int, int],
    radius: int,
    selected_color: tuple[int, int, int, int] | None = None,
) -> None:
    for item in rows:
        point = _point_from_mapping(item)
        if point is None:
            continue
        x, y = projection.project(point[0], point[1])
        active = str(item.get("state") or item.get("actionability") or "") in {
            "held",
            "actionable",
            "selected",
        }
        draw.ellipse(
            (x - radius, y - radius, x + radius, y + radius),
            fill=selected_color if active and selected_color else color,
            outline=(255, 255, 255, 230),
            width=1,
        )


def _draw_robot_path(
    draw: ImageDraw.ImageDraw,
    robot_path: list[dict[str, Any]],
    projection: _Projection,
) -> None:
    projected = []
    for pose in robot_path:
        point = _point_from_mapping(pose)
        if point is not None:
            projected.append(projection.project(point[0], point[1]))
    if len(projected) >= 2:
        draw.line(projected, fill=_ROBOT_PATH_COLOR, width=3)
    for index, (x, y) in enumerate(projected):
        pose = robot_path[index]
        manual_adjustment = str(
            pose.get("pose_source") or ""
        ) == "relative_robot_frame" or isinstance(pose.get("relative_pose_delta"), dict)
        radius = 7 if manual_adjustment else 4
        color = _MANUAL_ADJUSTMENT_COLOR if manual_adjustment else _ROBOT_PATH_COLOR
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)


def _draw_robot_pose(
    draw: ImageDraw.ImageDraw,
    pose: dict[str, Any],
    projection: _Projection,
) -> None:
    point = _point_from_mapping(pose)
    if point is None:
        return
    x, y = projection.project(point[0], point[1])
    draw.ellipse((x - 10, y - 10, x + 10, y + 10), fill=(47, 91, 175, 245))
    heading = _float_or_none(pose.get("theta", pose.get("yaw", pose.get("yaw_rad"))))
    if heading is None and pose.get("yaw_deg") is not None:
        heading = math.radians(float(pose["yaw_deg"]))
    if heading is None:
        return
    tip = (int(round(x + math.cos(heading) * 22)), int(round(y - math.sin(heading) * 22)))
    left = (
        int(round(x + math.cos(heading + 2.45) * 11)),
        int(round(y - math.sin(heading + 2.45) * 11)),
    )
    right = (
        int(round(x + math.cos(heading - 2.45) * 11)),
        int(round(y - math.sin(heading - 2.45) * 11)),
    )
    draw.polygon([tip, left, right], fill=_ROBOT_HEADING_COLOR)


def _draw_legend(
    draw: ImageDraw.ImageDraw,
    *,
    width: int,
    height: int,
    runtime: bool,
) -> None:
    entries = [
        ("area", (72, 121, 210, 88), "navigation areas"),
        ("waypoint", _WAYPOINT_COLOR, "base waypoints"),
    ]
    if runtime:
        entries.extend(
            [
                ("object", _OBJECT_COLOR, "observed objects"),
                ("anchor", _ANCHOR_COLOR, "public anchors"),
                ("target", _TARGET_COLOR, "targets"),
                ("robot", _ROBOT_PATH_COLOR, "robot/path"),
            ]
        )
    legend_width = 236 if runtime else 184
    top = 104
    row_h = 22
    draw.rectangle(
        (28, top, 28 + legend_width, top + 18 + row_h * len(entries)),
        fill=(255, 255, 255, 222),
        outline=(213, 220, 230, 230),
    )
    draw.text((42, top + 8), "Legend", fill=(30, 41, 59, 255))
    for idx, (_key, color, label) in enumerate(entries):
        y = top + 30 + idx * row_h
        draw.rectangle((42, y, 56, y + 10), fill=color, outline=(255, 255, 255, 230))
        draw.text((64, y - 3), label, fill=(75, 85, 99, 255))
    draw.text(
        (42, height - 35),
        "review image only; source contracts remain JSON/map artifacts",
        fill=(100, 116, 139, 255),
    )


def _projection(
    semantics: dict[str, Any],
    runtime_metric_map: dict[str, Any] | None,
    *,
    width: int,
    height: int,
) -> _Projection:
    points = _base_points(semantics)
    if runtime_metric_map is not None:
        points.extend(_runtime_points(runtime_metric_map))
    if not points:
        points = [(-1.0, -1.0), (1.0, 1.0)]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    pad_x = max((max_x - min_x) * 0.08, 0.5)
    pad_y = max((max_y - min_y) * 0.08, 0.5)
    min_x -= pad_x
    max_x += pad_x
    min_y -= pad_y
    max_y += pad_y
    target_aspect = (width - _MAP_MARGIN_X * 2) / max(
        height - _MAP_MARGIN_TOP - _MAP_MARGIN_BOTTOM,
        1,
    )
    span_x = max(max_x - min_x, 0.001)
    span_y = max(max_y - min_y, 0.001)
    current_aspect = span_x / span_y
    if current_aspect < target_aspect:
        extra = (span_y * target_aspect - span_x) / 2.0
        min_x -= extra
        max_x += extra
    elif current_aspect > target_aspect:
        extra = (span_x / target_aspect - span_y) / 2.0
        min_y -= extra
        max_y += extra
    return _Projection(
        min_x=min_x,
        max_x=max_x,
        min_y=min_y,
        max_y=max_y,
        width=width,
        height=height,
    )


def _runtime_map_base_semantics(runtime_metric_map: dict[str, Any]) -> dict[str, Any]:
    static_map = (
        runtime_metric_map.get("static_map")
        if isinstance(runtime_metric_map.get("static_map"), dict)
        else {}
    )
    return {
        "rooms": list(runtime_metric_map.get("rooms") or static_map.get("rooms") or []),
        "inspection_waypoints": list(
            runtime_metric_map.get("generated_exploration_candidates")
            or runtime_metric_map.get("inspection_waypoints")
            or static_map.get("inspection_waypoints")
            or []
        ),
        "driveable_ways": list(runtime_metric_map.get("driveable_ways") or []),
        "display_frame": None,
        "provenance": {
            "source": "runtime_metric_map_static_map",
            "contains_private_scoring_truth": False,
        },
    }


def _base_points(semantics: dict[str, Any]) -> list[tuple[float, float]]:
    points = []
    for area in semantics.get("rooms") or []:
        for point in area.get("polygon") or []:
            xy = _point_from_mapping(point)
            if xy is not None:
                points.append(xy)
    for waypoint in semantics.get("inspection_waypoints") or []:
        xy = _point_from_mapping(waypoint)
        if xy is not None:
            points.append(xy)
    return points


def _runtime_points(runtime_metric_map: dict[str, Any]) -> list[tuple[float, float]]:
    points = []
    for collection in (
        runtime_metric_map.get("public_semantic_anchors") or [],
        runtime_metric_map.get("observed_objects") or [],
        runtime_metric_map.get("target_candidates") or [],
        runtime_metric_map.get("robot_path") or [],
        runtime_metric_map.get("robot_trajectory") or [],
    ):
        for item in collection:
            xy = _point_from_mapping(item)
            if xy is not None:
                points.append(xy)
    pose = _robot_pose(runtime_metric_map, [])
    xy = _point_from_mapping(pose) if pose is not None else None
    if xy is not None:
        points.append(xy)
    return points


def _runtime_rows_with_positions(rows: list[Any]) -> list[dict[str, Any]]:
    return [dict(item) for item in rows if isinstance(item, dict) and _point_from_mapping(item)]


def _project_polygon(raw_polygon: Any, projection: _Projection) -> list[tuple[int, int]]:
    points = []
    for point in raw_polygon or []:
        xy = _point_from_mapping(point)
        if xy is not None:
            points.append(projection.project(xy[0], xy[1]))
    return points


def _point_from_mapping(item: Any) -> tuple[float, float] | None:
    if not isinstance(item, dict):
        return None
    candidates = [
        item,
        item.get("pose") if isinstance(item.get("pose"), dict) else None,
        item.get("position") if isinstance(item.get("position"), dict) else None,
        item.get("map_position") if isinstance(item.get("map_position"), dict) else None,
        item.get("source_map_position")
        if isinstance(item.get("source_map_position"), dict)
        else None,
    ]
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        x = _float_or_none(candidate.get("x"))
        y = _float_or_none(candidate.get("y"))
        if x is not None and y is not None:
            return (x, y)
    raw_position = item.get("position")
    if isinstance(raw_position, (list, tuple)) and len(raw_position) >= 2:
        x = _float_or_none(raw_position[0])
        y = _float_or_none(raw_position[1])
        if x is not None and y is not None:
            return (x, y)
    return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _visited_waypoint_ids(runtime_metric_map: dict[str, Any] | None) -> set[str]:
    if runtime_metric_map is None:
        return set()
    visited = set()
    for collection in (
        runtime_metric_map.get("observed_waypoint_ids") or [],
        runtime_metric_map.get("visited_waypoint_ids") or [],
    ):
        visited.add(str(collection))
    for waypoint in runtime_metric_map.get("generated_exploration_candidates") or []:
        if isinstance(waypoint, dict) and waypoint.get("visited"):
            visited.add(str(waypoint.get("waypoint_id") or ""))
    for item in runtime_metric_map.get("public_semantic_anchors") or []:
        if not isinstance(item, dict):
            continue
        evidence = item.get("evidence") if isinstance(item.get("evidence"), dict) else {}
        if evidence.get("visited") or item.get("source_observation_id"):
            visited.add(str(item.get("waypoint_id") or ""))
    return {item for item in visited if item}


def _waypoint_points(
    semantics: dict[str, Any],
    runtime_metric_map: dict[str, Any],
) -> dict[str, tuple[float, float]]:
    points: dict[str, tuple[float, float]] = {}
    for collection in (
        semantics.get("inspection_waypoints") or [],
        runtime_metric_map.get("generated_exploration_candidates") or [],
        runtime_metric_map.get("generated_target_inspection_candidates") or [],
    ):
        for item in collection:
            if not isinstance(item, dict):
                continue
            waypoint_id = str(item.get("waypoint_id") or "")
            point = _point_from_mapping(item)
            if waypoint_id and point is not None:
                points[waypoint_id] = point
    return points


def _path_from_visited_waypoints(
    runtime_metric_map: dict[str, Any],
    waypoint_points: dict[str, tuple[float, float]],
) -> list[dict[str, Any]]:
    rows = []
    for waypoint_id in _visited_waypoint_ids(runtime_metric_map):
        if waypoint_id in waypoint_points:
            x, y = waypoint_points[waypoint_id]
            rows.append({"x": x, "y": y})
    return rows


def _robot_path(runtime_metric_map: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("robot_path", "robot_trajectory"):
        rows = [dict(item) for item in runtime_metric_map.get(key) or [] if isinstance(item, dict)]
        if rows:
            return rows
    return []


def _robot_pose(
    runtime_metric_map: dict[str, Any],
    robot_path: list[dict[str, Any]],
) -> dict[str, Any] | None:
    pose = runtime_metric_map.get("robot_pose")
    if isinstance(pose, dict) and _point_from_mapping(pose) is not None:
        return dict(pose)
    if robot_path:
        return dict(robot_path[-1])
    return None


def _role_label(visual_role: str) -> str:
    if visual_role == BASE_NAVIGATION_MAP_PREVIEW_ROLE:
        return "Base Navigation Map preview"
    if visual_role == RUNTIME_METRIC_MAP_PREVIEW_ROLE:
        return "Runtime Metric Map preview"
    if visual_role == TOPDOWN_SCENE_RENDER_ROLE:
        return "Top-down Scene View"
    return visual_role.replace("_", " ").title()

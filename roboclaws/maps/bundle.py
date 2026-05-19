from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.maps.rasterize import (
    fixtures_from_hints,
    load_pgm,
    occupancy_grid_from_metric_map,
    write_pgm,
)
from roboclaws.maps.route import validate_metric_map_route

NAV2_MAP_BUNDLE_SCHEMA = "nav2_map_bundle_v1"
NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA = "nav2_map_bundle_snapshot_v1"
DEFAULT_ROBOT_PROFILE_ID = "rby1m"
DEFAULT_COSTMAP_PROFILE_ID = "rby1m_static_global"
DEFAULT_COSTMAP_PARAMETERS = {
    "resolution_m": 0.05,
    "inflation_radius_m": 0.45,
    "cost_scaling_factor": 3.0,
    "occupied_threshold": 0.65,
    "free_threshold": 0.25,
}
DEFAULT_ROBOT_PROFILE = {
    "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
    "base_frame_id": "base_link",
    "map_frame_id": "map",
    "footprint": {"type": "radius", "radius_m": 0.35},
    "camera": {"frame_id": "head_camera_rgb_optical_frame", "mount": "rby1m_head"},
    "navigation_tolerances": {"xy_goal_tolerance_m": 0.25, "yaw_goal_tolerance_rad": 0.35},
}
RUNTIME_COSTMAP_GAPS = (
    "runtime_obstacle_layer_not_simulated",
    "voxel_layer_not_simulated",
    "rolling_local_costmap_not_simulated",
    "tf_timing_not_simulated",
)
PRIVATE_MAP_KEYS = frozenset(
    {
        "acceptable_destination_sets",
        "generated_mess_set",
        "global_movable_object_inventory",
        "is_misplaced",
        "private_manifest",
        "target_receptacle_id",
        "valid_receptacle_ids",
    }
)


@dataclass(frozen=True)
class MapBundleValidation:
    root: Path
    errors: tuple[str, ...]
    warnings: tuple[str, ...]
    metadata: dict[str, Any]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema": "nav2_map_bundle_validation_v1",
            "root": str(self.root),
            "ok": self.ok,
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "metadata": self.metadata,
        }

    def raise_for_errors(self) -> None:
        if self.errors:
            raise AssertionError(f"invalid Nav2 map bundle {self.root}: {self.errors}")


def metric_map_bundle_metadata(
    *,
    environment_id: str,
    map_id: str,
    map_version: str,
    artifact_root: str = "map_bundle",
) -> dict[str, Any]:
    parameters = {
        "environment_id": environment_id,
        "map_id": map_id,
        "map_version": map_version,
        "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
        "costmap_profile_id": DEFAULT_COSTMAP_PROFILE_ID,
        "costmap_defaults": DEFAULT_COSTMAP_PARAMETERS,
    }
    return {
        "schema": NAV2_MAP_BUNDLE_SCHEMA,
        "environment_id": environment_id,
        "map_id": map_id,
        "map_version": map_version,
        "source_provenance": "molmospaces_public_semantic_map",
        "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
        "costmap_profile_id": DEFAULT_COSTMAP_PROFILE_ID,
        "artifact_paths": _bundle_relative_paths(artifact_root=artifact_root),
        "costmap_defaults": dict(DEFAULT_COSTMAP_PARAMETERS),
        "runtime_costmap_gaps": list(RUNTIME_COSTMAP_GAPS),
        "parameter_hash": _stable_hash(parameters),
        "public_contract_note": (
            "Map bundle paths are public static environment artifacts. Runtime movable "
            "objects and private scoring truth are not encoded in this bundle."
        ),
    }


def write_nav2_map_bundle_snapshot(
    *,
    run_dir: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any]:
    bundle_dir = run_dir / "map_bundle"
    snapshot = write_nav2_map_bundle(bundle_dir, metric_map=metric_map, fixture_hints=fixture_hints)
    snapshot["schema"] = NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA
    snapshot["snapshot_root"] = "map_bundle"
    snapshot["artifact_paths"] = {
        key: (bundle_dir / relative).relative_to(run_dir).as_posix()
        for key, relative in _bundle_local_paths().items()
    }
    return snapshot


def write_nav2_map_bundle(
    bundle_dir: Path,
    *,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any]:
    profiles_dir = bundle_dir / "profiles"
    costmaps_dir = bundle_dir / "costmaps"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    costmaps_dir.mkdir(parents=True, exist_ok=True)

    map_id = str(metric_map.get("map_id") or "realworld_cleanup_semantic_map")
    map_version = str(metric_map.get("map_version") or "static-fixture-map-v1")
    environment_id = str(
        (metric_map.get("map_bundle") or {}).get("environment_id")
        if isinstance(metric_map.get("map_bundle"), dict)
        else ""
    ) or map_id.removesuffix("_semantic_map")
    metadata = (
        metric_map.get("map_bundle") if isinstance(metric_map.get("map_bundle"), dict) else {}
    )
    parameter_hash = str(
        metadata.get("parameter_hash")
        or metric_map_bundle_metadata(
            environment_id=environment_id,
            map_id=map_id,
            map_version=map_version,
        )["parameter_hash"]
    )

    paths = _bundle_local_paths()
    map_yaml_path = bundle_dir / paths["map_yaml"]
    map_pgm_path = bundle_dir / paths["occupancy_image"]
    semantics_path = bundle_dir / paths["semantics_json"]
    robot_profile_path = bundle_dir / paths["robot_profile"]
    costmap_params_path = bundle_dir / paths["costmap_params"]
    preview_path = bundle_dir / paths["preview_png"]

    grid = occupancy_grid_from_metric_map(metric_map, fixture_hints)
    write_pgm(map_pgm_path, grid)
    map_yaml_path.write_text(_map_yaml(metric_map), encoding="utf-8")
    semantics_path.write_text(
        json.dumps(_semantics_payload(metric_map, fixture_hints), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    robot_profile_path.write_text(_simple_yaml(DEFAULT_ROBOT_PROFILE), encoding="utf-8")
    costmap_params_path.write_text(_costmap_yaml(metric_map), encoding="utf-8")
    _write_preview(preview_path, metric_map, fixture_hints)

    artifact_paths = {
        "map_yaml": map_yaml_path,
        "occupancy_image": map_pgm_path,
        "semantics_json": semantics_path,
        "robot_profile": robot_profile_path,
        "costmap_params": costmap_params_path,
        "preview_png": preview_path,
    }
    hashes = {key: _file_sha256(path) for key, path in artifact_paths.items() if path.is_file()}
    return {
        "schema": NAV2_MAP_BUNDLE_SCHEMA,
        "source_schema": metric_map.get("schema", ""),
        "environment_id": environment_id,
        "map_id": map_id,
        "map_version": map_version,
        "source_provenance": "molmospaces_public_semantic_map",
        "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
        "costmap_profile_id": DEFAULT_COSTMAP_PROFILE_ID,
        "parameter_hash": parameter_hash,
        "snapshot_root": bundle_dir.name,
        "snapshot_complete": set(artifact_paths) <= set(hashes),
        "artifact_paths": {
            key: path.relative_to(bundle_dir).as_posix() for key, path in artifact_paths.items()
        },
        "artifact_hashes": hashes,
        "runtime_costmap_gaps": list(RUNTIME_COSTMAP_GAPS),
        "public_contract_note": (
            "Snapshot files freeze the public Nav2-shaped map contract used by this run. "
            "They do not encode movable-object target truth or private scoring data."
        ),
    }


def validate_nav2_map_bundle(bundle_dir: Path) -> MapBundleValidation:
    errors: list[str] = []
    warnings: list[str] = []
    bundle_dir = Path(bundle_dir)
    paths = _bundle_local_paths()
    for key, relative in paths.items():
        if not (bundle_dir / relative).is_file():
            errors.append(f"missing required artifact: {relative} ({key})")
    if errors:
        return MapBundleValidation(bundle_dir, tuple(errors), tuple(warnings), {})

    try:
        map_yaml = parse_map_yaml((bundle_dir / paths["map_yaml"]).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive CLI path
        errors.append(f"invalid map.yaml: {exc}")
        map_yaml = {}
    try:
        semantics = json.loads((bundle_dir / paths["semantics_json"]).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid semantics.json: {exc}")
        semantics = {}
    private_hits = sorted(_find_private_keys(semantics))
    if private_hits:
        errors.append(f"private cleanup truth encoded in semantics.json: {private_hits}")

    image_name = str(map_yaml.get("image") or "")
    if image_name != "map.pgm":
        errors.append(f"map.yaml image must resolve to map.pgm, got {image_name!r}")
    resolution = _positive_float(map_yaml.get("resolution"), "map.yaml resolution", errors)
    origin = map_yaml.get("origin")
    if not isinstance(origin, list) or len(origin) != 3:
        errors.append("map.yaml origin must be a 3-item list")
        origin = [0.0, 0.0, 0.0]
    occupied = _positive_float(map_yaml.get("occupied_thresh"), "map.yaml occupied_thresh", errors)
    free = _positive_float(map_yaml.get("free_thresh"), "map.yaml free_thresh", errors)
    if occupied <= free:
        errors.append("map.yaml occupied_thresh must be greater than free_thresh")

    try:
        grid = load_pgm(
            bundle_dir / paths["occupancy_image"],
            resolution_m=resolution or DEFAULT_COSTMAP_PARAMETERS["resolution_m"],
            origin_x=float(origin[0]),
            origin_y=float(origin[1]),
        )
        free_cells = sum(1 for row in grid.rows for value in row if value >= 250)
        occupied_cells = sum(1 for row in grid.rows for value in row if value <= 5)
        if free_cells == 0 or occupied_cells == 0:
            errors.append(
                "occupancy image must contain free and occupied cells, "
                f"got free={free_cells} occupied={occupied_cells}"
            )
    except Exception as exc:  # pragma: no cover - defensive CLI path
        errors.append(f"invalid occupancy image: {exc}")
        grid = None

    rooms = semantics.get("rooms") if isinstance(semantics.get("rooms"), list) else []
    fixtures = semantics.get("fixtures") if isinstance(semantics.get("fixtures"), list) else []
    waypoints = (
        semantics.get("inspection_waypoints")
        if isinstance(semantics.get("inspection_waypoints"), list)
        else []
    )
    driveable = (
        semantics.get("driveable_ways") if isinstance(semantics.get("driveable_ways"), list) else []
    )
    if not rooms:
        errors.append("semantics.json must contain rooms")
    if not fixtures:
        errors.append("semantics.json must contain fixtures")
    if not waypoints:
        errors.append("semantics.json must contain inspection_waypoints")
    if not driveable:
        errors.append("semantics.json must contain driveable_ways")
    if not isinstance(semantics.get("frame_ids"), dict) or not semantics["frame_ids"].get("map"):
        errors.append("semantics.json must contain frame_ids.map")
    if not isinstance(semantics.get("provenance"), dict):
        errors.append("semantics.json must contain provenance")
    else:
        provenance = semantics["provenance"]
        if provenance.get("contains_runtime_observations") is not False:
            errors.append("semantics.json provenance must exclude runtime observations")
        if provenance.get("contains_private_scoring_truth") is not False:
            errors.append("semantics.json provenance must exclude private scoring truth")

    waypoint_by_id = {str(item.get("waypoint_id") or ""): item for item in waypoints}
    if grid is not None:
        for waypoint in waypoints:
            waypoint_id = str(waypoint.get("waypoint_id") or "")
            if not waypoint_id:
                errors.append("inspection waypoint missing waypoint_id")
                continue
            if not grid.is_free_world(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))):
                errors.append(f"inspection waypoint is not on free costmap cell: {waypoint_id}")
    for fixture in fixtures:
        fixture_id = str(fixture.get("fixture_id") or "")
        if not fixture_id:
            errors.append("fixture missing fixture_id")
        if not fixture.get("affordances"):
            errors.append(f"fixture missing affordances: {fixture_id}")
        if not isinstance(fixture.get("footprint"), dict):
            errors.append(f"fixture missing footprint: {fixture_id}")
        preferred = str(
            fixture.get("preferred_inspection_waypoint_id")
            or fixture.get("preferred_manipulation_waypoint_id")
            or ""
        )
        if preferred not in waypoint_by_id:
            errors.append(f"fixture has no reachable preferred waypoint: {fixture_id}")
    route_failures = _validate_declared_routes(semantics)
    errors.extend(route_failures)

    metadata = {
        "map_id": semantics.get("map_id"),
        "map_version": semantics.get("map_version"),
        "room_count": len(rooms),
        "fixture_count": len(fixtures),
        "waypoint_count": len(waypoints),
        "driveable_way_count": len(driveable),
    }
    return MapBundleValidation(bundle_dir, tuple(errors), tuple(warnings), metadata)


def parse_map_yaml(text: str) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            payload[key.strip()] = [
                float(item.strip()) for item in value.removeprefix("[").removesuffix("]").split(",")
            ]
        elif re.fullmatch(r"-?\d+(\.\d+)?", value):
            payload[key.strip()] = float(value) if "." in value else int(value)
        else:
            payload[key.strip()] = value.strip('"')
    return payload


def _validate_declared_routes(semantics: dict[str, Any]) -> list[str]:
    rooms = semantics.get("rooms") or []
    waypoints = semantics.get("inspection_waypoints") or []
    fixtures = semantics.get("fixtures") or []
    fixture_hints = {"rooms": []}
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        item = dict(room)
        item["fixtures"] = [
            fixture for fixture in fixtures if str(fixture.get("room_id") or "") == room_id
        ]
        fixture_hints["rooms"].append(item)
    metric_map = {
        "resolution_m": DEFAULT_COSTMAP_PARAMETERS["resolution_m"],
        "origin": {"x": 0.0, "y": 0.0, "yaw": 0.0},
        "width": 240,
        "height": 180,
        "rooms": rooms,
        "driveable_ways": semantics.get("driveable_ways") or [],
        "inspection_waypoints": waypoints,
    }
    waypoints_by_room: dict[str, str] = {}
    for waypoint in waypoints:
        waypoints_by_room.setdefault(
            str(waypoint.get("room_id") or ""), str(waypoint.get("waypoint_id") or "")
        )
    failures: list[str] = []
    for way in semantics.get("driveable_ways") or []:
        start = waypoints_by_room.get(str(way.get("from_room_id") or ""))
        goal = waypoints_by_room.get(str(way.get("to_room_id") or ""))
        if not start or not goal:
            failures.append(f"driveable way missing room waypoint: {way}")
            continue
        result = validate_metric_map_route(
            metric_map,
            fixture_hints,
            start_waypoint_id=start,
            goal_waypoint_id=goal,
        )
        if not result.ok:
            failures.append(
                f"driveable way has no static route: {start}->{goal}:{result.failure_type}"
            )
    return failures


def _bundle_local_paths() -> dict[str, Path]:
    return {
        "map_yaml": Path("map.yaml"),
        "occupancy_image": Path("map.pgm"),
        "semantics_json": Path("semantics.json"),
        "robot_profile": Path("profiles") / f"{DEFAULT_ROBOT_PROFILE_ID}.yaml",
        "costmap_params": Path("costmaps") / f"{DEFAULT_ROBOT_PROFILE_ID}.costmap_params.yaml",
        "preview_png": Path("preview.png"),
    }


def _bundle_relative_paths(*, artifact_root: str) -> dict[str, str]:
    prefix = f"{artifact_root.rstrip('/')}/" if artifact_root else ""
    return {key: f"{prefix}{path.as_posix()}" for key, path in _bundle_local_paths().items()}


def _map_yaml(metric_map: dict[str, Any]) -> str:
    origin = metric_map.get("origin") if isinstance(metric_map.get("origin"), dict) else {}
    return "\n".join(
        [
            "image: map.pgm",
            f"resolution: {float(metric_map.get('resolution_m') or 0.05):.6f}",
            "origin: "
            f"[{float(origin.get('x') or 0.0):.6f}, "
            f"{float(origin.get('y') or 0.0):.6f}, "
            f"{float(origin.get('yaw') or 0.0):.6f}]",
            "negate: 0",
            f"occupied_thresh: {DEFAULT_COSTMAP_PARAMETERS['occupied_threshold']:.6f}",
            f"free_thresh: {DEFAULT_COSTMAP_PARAMETERS['free_threshold']:.6f}",
            "",
        ]
    )


def _costmap_yaml(metric_map: dict[str, Any]) -> str:
    payload = {
        "global_costmap": {
            "global_costmap": {
                "ros__parameters": {
                    "global_frame": str(metric_map.get("frame_id") or "map"),
                    "robot_base_frame": DEFAULT_ROBOT_PROFILE["base_frame_id"],
                    "resolution": DEFAULT_COSTMAP_PARAMETERS["resolution_m"],
                    "footprint_padding": 0.01,
                    "plugins": ["static_layer", "inflation_layer"],
                    "static_layer": {
                        "plugin": "nav2_costmap_2d::StaticLayer",
                        "map_subscribe_transient_local": True,
                    },
                    "inflation_layer": {
                        "plugin": "nav2_costmap_2d::InflationLayer",
                        "inflation_radius": DEFAULT_COSTMAP_PARAMETERS["inflation_radius_m"],
                        "cost_scaling_factor": DEFAULT_COSTMAP_PARAMETERS["cost_scaling_factor"],
                    },
                    "runtime_gaps": list(RUNTIME_COSTMAP_GAPS),
                }
            }
        }
    }
    return _simple_yaml(payload)


def _semantics_payload(metric_map: dict[str, Any], fixture_hints: dict[str, Any]) -> dict[str, Any]:
    metadata = (
        metric_map.get("map_bundle") if isinstance(metric_map.get("map_bundle"), dict) else {}
    )
    return {
        "schema": "nav2_cleanup_semantics_v1",
        "environment_id": metadata.get("environment_id") or metric_map.get("map_id"),
        "frame_ids": {
            "map": str(metric_map.get("frame_id") or "map"),
            "base": DEFAULT_ROBOT_PROFILE["base_frame_id"],
            "camera": DEFAULT_ROBOT_PROFILE["camera"]["frame_id"],
        },
        "map_id": metric_map.get("map_id"),
        "map_version": metric_map.get("map_version"),
        "rooms": metric_map.get("rooms") or [],
        "fixtures": fixtures_from_hints(fixture_hints),
        "inspection_waypoints": metric_map.get("inspection_waypoints") or [],
        "driveable_ways": metric_map.get("driveable_ways") or [],
        "provenance": {
            "source": "molmospaces_public_semantic_map",
            "contains_runtime_observations": False,
            "contains_private_scoring_truth": False,
        },
    }


def _write_preview(path: Path, metric_map: dict[str, Any], fixture_hints: dict[str, Any]) -> None:
    image = Image.new("RGB", (900, 560), (247, 249, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 882, 542), outline=(175, 184, 196), width=2)
    draw.text((34, 32), "Nav2 static map bundle preview", fill=(28, 35, 48))
    bounds = _coordinate_bounds(metric_map, fixture_hints)
    for room in metric_map.get("rooms") or []:
        polygon = room.get("polygon") or []
        if len(polygon) >= 3:
            points = [
                _project(point.get("x", 0.0), point.get("y", 0.0), bounds) for point in polygon
            ]
            draw.polygon(points, fill=(232, 238, 245), outline=(130, 145, 164))
            center = _polygon_center(points)
            draw.text(
                (center[0] - 34, center[1] - 8),
                str(room.get("room_label", ""))[:22],
                fill=(45, 55, 70),
            )
    for fixture in fixtures_from_hints(fixture_hints):
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        x, y = _project(pose.get("x", 0.0), pose.get("y", 0.0), bounds)
        draw.rectangle((x - 18, y - 12, x + 18, y + 12), fill=(120, 132, 150), outline=(54, 63, 78))
        draw.text((x + 22, y - 8), str(fixture.get("fixture_id", ""))[:20], fill=(35, 43, 56))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        x, y = _project(waypoint.get("x", 0.0), waypoint.get("y", 0.0), bounds)
        color = (31, 132, 94) if waypoint.get("visited") else (203, 121, 43)
        draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=color)
        draw.text((x + 10, y + 6), str(waypoint.get("waypoint_id", ""))[:24], fill=(35, 43, 56))
    robot_pose = (
        metric_map.get("robot_pose") if isinstance(metric_map.get("robot_pose"), dict) else {}
    )
    rx, ry = _project(robot_pose.get("x", 0.0), robot_pose.get("y", 0.0), bounds)
    draw.ellipse((rx - 12, ry - 12, rx + 12, ry + 12), fill=(47, 91, 175), outline=(20, 38, 74))
    draw.text((rx + 16, ry - 8), "robot", fill=(20, 38, 74))
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")


def _coordinate_bounds(
    metric_map: dict[str, Any], fixture_hints: dict[str, Any]
) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for room in metric_map.get("rooms") or []:
        for point in room.get("polygon") or []:
            xs.append(float(point.get("x", 0.0)))
            ys.append(float(point.get("y", 0.0)))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        xs.append(float(waypoint.get("x", 0.0)))
        ys.append(float(waypoint.get("y", 0.0)))
    for fixture in fixtures_from_hints(fixture_hints):
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        xs.append(float(pose.get("x", 0.0)))
        ys.append(float(pose.get("y", 0.0)))
    if not xs or not ys:
        return (-1.0, -1.0, 1.0, 1.0)
    return (min(xs) - 0.5, min(ys) - 0.5, max(xs) + 0.5, max(ys) + 0.5)


def _project(x_raw: Any, y_raw: Any, bounds: tuple[float, float, float, float]) -> tuple[int, int]:
    min_x, min_y, max_x, max_y = bounds
    x = float(x_raw or 0.0)
    y = float(y_raw or 0.0)
    width = max(max_x - min_x, 0.001)
    height = max(max_y - min_y, 0.001)
    px = 48 + int((x - min_x) / width * 804)
    py = 512 - int((y - min_y) / height * 448)
    return px, py


def _polygon_center(points: list[tuple[int, int]]) -> tuple[int, int]:
    if not points:
        return (0, 0)
    return (
        sum(point[0] for point in points) // len(points),
        sum(point[1] for point in points) // len(points),
    )


def _simple_yaml(value: Any, *, indent: int = 0) -> str:
    lines = _yaml_lines(value, indent=indent)
    return "\n".join(lines) + "\n"


def _yaml_lines(value: Any, *, indent: int) -> list[str]:
    pad = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list, tuple)):
                lines.append(f"{pad}{key}:")
                lines.extend(_yaml_lines(item, indent=indent + 2))
            else:
                lines.append(f"{pad}{key}: {_yaml_scalar(item)}")
        return lines
    if isinstance(value, (list, tuple)):
        lines = []
        for item in value:
            if isinstance(item, (dict, list, tuple)):
                lines.append(f"{pad}-")
                lines.extend(_yaml_lines(item, indent=indent + 2))
            else:
                lines.append(f"{pad}- {_yaml_scalar(item)}")
        return lines
    return [f"{pad}{_yaml_scalar(value)}"]


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    if not text or any(ch in text for ch in ":#[]{}&,"):
        return json.dumps(text)
    return text


def _find_private_keys(value: Any, *, prefix: str = "") -> set[str]:
    hits: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in PRIVATE_MAP_KEYS:
                hits.add(path)
            hits.update(_find_private_keys(item, prefix=path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.update(_find_private_keys(item, prefix=f"{prefix}[{index}]"))
    return hits


def _positive_float(value: Any, label: str, errors: list[str]) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        errors.append(f"{label} must be numeric")
        return 0.0
    if parsed <= 0:
        errors.append(f"{label} must be positive")
    return parsed


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

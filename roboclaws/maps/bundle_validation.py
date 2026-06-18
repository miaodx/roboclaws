from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from roboclaws.maps.rasterize import load_pgm
from roboclaws.maps.route import validate_metric_map_route
from roboclaws.maps.spatial_contract import (
    require_source_frame_spatial_contract,
    validate_spatial_room_contract,
)


def validate_nav2_map_bundle_payload(
    bundle_dir: Path,
    *,
    paths: dict[str, Path],
    default_resolution_m: float,
    private_map_keys: frozenset[str],
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    bundle_dir = Path(bundle_dir)
    if not _validate_required_bundle_artifacts(bundle_dir, paths, errors):
        return tuple(errors), tuple(warnings), {}

    map_yaml = _load_bundle_map_yaml(bundle_dir, paths, errors)
    semantics = _load_bundle_semantics(bundle_dir, paths, errors)
    _validate_semantics_private_truth(semantics, private_map_keys, errors)
    resolution, origin = _validate_map_yaml_contract(map_yaml, errors)
    grid = _load_bundle_occupancy_grid(
        bundle_dir,
        paths,
        resolution or default_resolution_m,
        origin,
        errors,
    )
    rooms, landmarks, waypoints, driveable = _validate_semantics_contract(semantics, errors)
    waypoint_by_id = _validate_inspection_waypoints(waypoints, grid, errors)
    _validate_landmark_waypoint_references(landmarks, waypoint_by_id, errors)
    errors.extend(
        _validate_declared_routes(semantics, grid=grid, default_resolution_m=default_resolution_m)
    )
    metadata = {
        "map_id": semantics.get("map_id"),
        "map_version": semantics.get("map_version"),
        "room_count": len(rooms),
        "static_landmark_count": len(landmarks),
        "waypoint_count": len(waypoints),
        "driveable_way_count": len(driveable),
    }
    return tuple(errors), tuple(warnings), metadata


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


def _validate_required_bundle_artifacts(
    bundle_dir: Path,
    paths: dict[str, Path],
    errors: list[str],
) -> bool:
    for key, relative in paths.items():
        if not (bundle_dir / relative).is_file():
            errors.append(f"missing required artifact: {relative} ({key})")
    return not errors


def _load_bundle_map_yaml(
    bundle_dir: Path,
    paths: dict[str, Path],
    errors: list[str],
) -> dict[str, Any]:
    try:
        return parse_map_yaml((bundle_dir / paths["map_yaml"]).read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - defensive CLI path
        errors.append(f"invalid map.yaml: {exc}")
        return {}


def _load_bundle_semantics(
    bundle_dir: Path,
    paths: dict[str, Path],
    errors: list[str],
) -> dict[str, Any]:
    try:
        return json.loads((bundle_dir / paths["semantics_json"]).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"invalid semantics.json: {exc}")
        return {}


def _validate_semantics_private_truth(
    semantics: dict[str, Any],
    private_map_keys: frozenset[str],
    errors: list[str],
) -> None:
    private_hits = sorted(_find_private_keys(semantics, private_map_keys=private_map_keys))
    if private_hits:
        errors.append(f"private cleanup truth encoded in semantics.json: {private_hits}")


def _validate_map_yaml_contract(
    map_yaml: dict[str, Any],
    errors: list[str],
) -> tuple[float, list[Any]]:
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
    return resolution, origin


def _load_bundle_occupancy_grid(
    bundle_dir: Path,
    paths: dict[str, Path],
    resolution_m: float,
    origin: list[Any],
    errors: list[str],
) -> Any | None:
    try:
        grid = load_pgm(
            bundle_dir / paths["occupancy_image"],
            resolution_m=resolution_m,
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
        return grid
    except Exception as exc:  # pragma: no cover - defensive CLI path
        errors.append(f"invalid occupancy image: {exc}")
        return None


def _validate_semantics_contract(
    semantics: dict[str, Any],
    errors: list[str],
) -> tuple[list[Any], list[Any], list[Any], list[Any]]:
    rooms = semantics.get("rooms") if isinstance(semantics.get("rooms"), list) else []
    landmarks = (
        semantics.get("static_landmarks")
        if isinstance(semantics.get("static_landmarks"), list)
        else []
    )
    waypoints = (
        semantics.get("inspection_waypoints")
        if isinstance(semantics.get("inspection_waypoints"), list)
        else []
    )
    driveable = (
        semantics.get("driveable_ways") if isinstance(semantics.get("driveable_ways"), list) else []
    )
    base_navigation_map = not rooms and not landmarks
    if not waypoints:
        errors.append("semantics.json must contain inspection_waypoints")
    if not driveable and not base_navigation_map:
        errors.append("semantics.json must contain driveable_ways")
    if base_navigation_map and waypoints:
        _validate_generated_waypoints(waypoints, errors)
    if not isinstance(semantics.get("frame_ids"), dict) or not semantics["frame_ids"].get("map"):
        errors.append("semantics.json must contain frame_ids.map")
    require_source_frame_spatial_contract(semantics, errors)
    for index, room in enumerate(rooms):
        if isinstance(room, dict):
            validate_spatial_room_contract(room, index=index, errors=errors)
        else:
            errors.append(f"semantics.json rooms[{index}] must be an object")
    _validate_semantics_provenance(semantics, errors)
    return rooms, landmarks, waypoints, driveable


def _validate_generated_waypoints(waypoints: list[Any], errors: list[str]) -> None:
    generated_waypoints = [
        waypoint
        for waypoint in waypoints
        if waypoint.get("waypoint_source") == "generated_exploration_candidate"
    ]
    if not generated_waypoints:
        errors.append(
            "fixtureless semantics.json must contain generated_exploration_candidate "
            "inspection_waypoints"
        )


def _validate_semantics_provenance(semantics: dict[str, Any], errors: list[str]) -> None:
    if not isinstance(semantics.get("provenance"), dict):
        errors.append("semantics.json must contain provenance")
        return
    provenance = semantics["provenance"]
    if provenance.get("contains_runtime_observations") is not False:
        errors.append("semantics.json provenance must exclude runtime observations")
    if provenance.get("contains_private_scoring_truth") is not False:
        errors.append("semantics.json provenance must exclude private scoring truth")


def _validate_inspection_waypoints(
    waypoints: list[Any],
    grid: Any | None,
    errors: list[str],
) -> dict[str, Any]:
    waypoint_by_id = {str(item.get("waypoint_id") or ""): item for item in waypoints}
    if grid is None:
        return waypoint_by_id
    for waypoint in waypoints:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if not waypoint_id:
            errors.append("inspection waypoint missing waypoint_id")
            continue
        if not grid.is_free_world(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0))):
            errors.append(f"inspection waypoint is not on free costmap cell: {waypoint_id}")
    return waypoint_by_id


def _validate_landmark_waypoint_references(
    landmarks: list[Any],
    waypoint_by_id: dict[str, Any],
    errors: list[str],
) -> None:
    for landmark in landmarks:
        landmark_id = str(landmark.get("landmark_id") or landmark.get("fixture_id") or "")
        if not landmark_id:
            errors.append("static landmark missing landmark_id")
        if not landmark.get("affordances"):
            errors.append(f"static landmark missing affordances: {landmark_id}")
        if not isinstance(landmark.get("footprint"), dict):
            errors.append(f"static landmark missing footprint: {landmark_id}")
        preferred = str(
            landmark.get("preferred_inspection_waypoint_id")
            or landmark.get("preferred_manipulation_waypoint_id")
            or ""
        )
        if preferred not in waypoint_by_id:
            errors.append(f"static landmark has no reachable preferred waypoint: {landmark_id}")


def _validate_declared_routes(
    semantics: dict[str, Any],
    *,
    grid: Any | None,
    default_resolution_m: float,
) -> list[str]:
    rooms = semantics.get("rooms") or []
    waypoints = semantics.get("inspection_waypoints") or []
    static_landmarks = semantics.get("static_landmarks") or []
    metric_map = {
        "resolution_m": grid.resolution_m if grid is not None else default_resolution_m,
        "origin": {
            "x": grid.origin_x if grid is not None else 0.0,
            "y": grid.origin_y if grid is not None else 0.0,
            "yaw": 0.0,
        },
        "width": grid.width if grid is not None else 240,
        "height": grid.height if grid is not None else 180,
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
            static_landmarks,
            start_waypoint_id=start,
            goal_waypoint_id=goal,
        )
        if not result.ok:
            failures.append(
                f"driveable way has no static route: {start}->{goal}:{result.failure_type}"
            )
    return failures


def _find_private_keys(
    value: Any,
    *,
    private_map_keys: frozenset[str],
    prefix: str = "",
) -> set[str]:
    hits: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            path = f"{prefix}.{key_text}" if prefix else key_text
            if key_text in private_map_keys:
                hits.add(path)
            hits.update(_find_private_keys(item, private_map_keys=private_map_keys, prefix=path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            hits.update(
                _find_private_keys(
                    item, private_map_keys=private_map_keys, prefix=f"{prefix}[{index}]"
                )
            )
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

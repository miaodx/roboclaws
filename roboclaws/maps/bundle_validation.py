from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object
from roboclaws.maps.rasterize import load_pgm
from roboclaws.maps.route import validate_metric_map_route
from roboclaws.maps.spatial_contract import (
    require_source_frame_spatial_contract,
    validate_spatial_room_contract,
)

BASE_NAVIGATION_MAP_SCHEMA = "base_navigation_map_v1"
UNKNOWN_REVIEW_REQUIRED_CATEGORY = "unknown_review_required"
PRODUCT_SEMANTIC_CATEGORIES = frozenset(
    {
        "bathroom",
        "bedroom",
        "corridor",
        "dining_area",
        "entry",
        "kitchen",
        "living_room",
        "meeting_room",
        "open_area",
        "storage",
        "utility",
    }
)
BASE_NAVIGATION_FORBIDDEN_SEMANTIC_COLLECTIONS = (
    "static_landmarks",
    "fixtures",
    "receptacles",
    "movable_objects",
    "global_movable_object_inventory",
    "navigation_memory_anchors",
)
BASE_WAYPOINT_FORBIDDEN_KEYS = frozenset(
    {
        "acceptable_destination_sets",
        "fixture_id",
        "generated_mess_set",
        "landmark_id",
        "object_id",
        "preferred_inspection_waypoint_id",
        "preferred_manipulation_waypoint_id",
        "receptacle_id",
        "target_fixture_id",
        "target_receptacle_id",
        "valid_receptacle_ids",
    }
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
    if semantics is None:
        return tuple(errors), tuple(warnings), {}
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


def validate_base_navigation_map_v1_payload(
    bundle_dir: Path,
    *,
    paths: dict[str, Path],
    default_resolution_m: float,
    private_map_keys: frozenset[str],
) -> tuple[tuple[str, ...], tuple[str, ...], dict[str, Any]]:
    errors, warnings, metadata = validate_nav2_map_bundle_payload(
        bundle_dir,
        paths=paths,
        default_resolution_m=default_resolution_m,
        private_map_keys=private_map_keys,
    )
    errors_list = list(errors)
    bundle_dir = Path(bundle_dir)
    semantics = _load_bundle_semantics(bundle_dir, paths, errors_list)
    if semantics is None:
        metadata = {**metadata, "base_navigation_map_v1_ready": False}
        return tuple(errors_list), warnings, metadata
    _validate_base_navigation_map_v1_contract(semantics, errors_list)
    metadata = {
        **metadata,
        "base_navigation_map_schema": (semantics.get("base_navigation_map_contract") or {}).get(
            "schema"
        )
        if isinstance(semantics.get("base_navigation_map_contract"), dict)
        else None,
        "base_navigation_map_v1_ready": not errors_list,
    }
    return tuple(errors_list), warnings, metadata


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
) -> dict[str, Any] | None:
    try:
        return read_json_object(bundle_dir / paths["semantics_json"], label="Nav2 semantics")
    except (FileNotFoundError, ValueError) as exc:
        errors.append(str(exc))
        return None


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


def _validate_base_navigation_map_v1_contract(
    semantics: dict[str, Any],
    errors: list[str],
) -> None:
    contract = semantics.get("base_navigation_map_contract")
    if not isinstance(contract, dict) or contract.get("schema") != BASE_NAVIGATION_MAP_SCHEMA:
        errors.append(
            f"semantics.json must contain base_navigation_map_contract.schema="
            f"{BASE_NAVIGATION_MAP_SCHEMA}"
        )

    _validate_base_navigation_forbidden_semantics(semantics, errors)
    rooms = semantics.get("rooms") if isinstance(semantics.get("rooms"), list) else []
    navigation_areas = _base_navigation_areas(rooms, errors)
    if not navigation_areas:
        errors.append("Base Navigation Map v1 must contain navigation areas")
    _validate_base_navigation_area_semantics(navigation_areas, errors)
    _validate_base_navigation_waypoints(
        semantics.get("inspection_waypoints")
        if isinstance(semantics.get("inspection_waypoints"), list)
        else [],
        navigation_areas=navigation_areas,
        errors=errors,
    )
    _validate_base_navigation_provenance(semantics, errors)
    _validate_base_navigation_sidecar_scope(semantics, errors)


def _validate_base_navigation_forbidden_semantics(
    semantics: dict[str, Any],
    errors: list[str],
) -> None:
    for key in BASE_NAVIGATION_FORBIDDEN_SEMANTIC_COLLECTIONS:
        value = semantics.get(key)
        if value:
            errors.append(f"Base Navigation Map v1 must not contain {key}")


def _base_navigation_areas(
    rooms: list[Any],
    errors: list[str],
) -> dict[str, dict[str, Any]]:
    navigation_areas: dict[str, dict[str, Any]] = {}
    for index, room in enumerate(rooms):
        if not isinstance(room, dict):
            continue
        polygon_usage = (
            room.get("polygon_usage") if isinstance(room.get("polygon_usage"), dict) else {}
        )
        if polygon_usage.get("navigation") is not True:
            continue
        area_id = str(
            room.get("navigation_area_id")
            or room.get("map_area_id")
            or room.get("room_id")
            or ""
        )
        if not area_id:
            errors.append(f"navigation area rooms[{index}] missing navigation_area_id")
            continue
        if area_id in navigation_areas:
            errors.append(f"duplicate navigation_area_id in Base Navigation Map v1: {area_id}")
            continue
        navigation_areas[area_id] = room
    return navigation_areas


def _validate_base_navigation_area_semantics(
    navigation_areas: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    for area_id, area in navigation_areas.items():
        polygon = area.get("polygon") if isinstance(area.get("polygon"), list) else []
        if len(polygon) < 3:
            errors.append(f"navigation area {area_id} must contain a source-frame polygon")
        if not str(area.get("room_label") or area.get("semantic_label") or area.get("label") or ""):
            errors.append(f"navigation area {area_id} missing semantic label")
        category = str(area.get("semantic_category") or area.get("category") or "")
        if not category:
            errors.append(f"navigation area {area_id} missing semantic category")
        elif category == UNKNOWN_REVIEW_REQUIRED_CATEGORY:
            errors.append(
                f"navigation area {area_id} category {UNKNOWN_REVIEW_REQUIRED_CATEGORY} "
                "is not valid for product Base Navigation Map v1"
            )
        elif category not in PRODUCT_SEMANTIC_CATEGORIES:
            errors.append(
                f"navigation area {area_id} semantic category {category!r} is not in "
                "the product Base Navigation Map v1 vocabulary"
            )
        if not str(area.get("geometry_source") or ""):
            errors.append(f"navigation area {area_id} missing geometry_source")
        if not str(area.get("label_source") or area.get("semantic_source") or ""):
            errors.append(f"navigation area {area_id} missing label_source")
        if area.get("review_status") != "accepted":
            errors.append(f"navigation area {area_id} review_status must be accepted")
        polygon_usage = (
            area.get("polygon_usage") if isinstance(area.get("polygon_usage"), dict) else {}
        )
        if polygon_usage.get("semantic_labeling") != "accepted":
            errors.append(f"navigation area {area_id} semantic_labeling must be accepted")


def _validate_base_navigation_waypoints(
    waypoints: list[Any],
    *,
    navigation_areas: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    if not waypoints:
        errors.append("Base Navigation Map v1 must contain base inspection waypoints")
        return
    seen_waypoint_ids: set[str] = set()
    for index, waypoint in enumerate(waypoints):
        if not isinstance(waypoint, dict):
            errors.append(f"Base Navigation Map waypoint {index} must be an object")
            continue
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if not waypoint_id:
            errors.append(f"Base Navigation Map waypoint {index} missing waypoint_id")
            continue
        if waypoint_id in seen_waypoint_ids:
            errors.append(f"duplicate Base Navigation Map waypoint_id: {waypoint_id}")
        seen_waypoint_ids.add(waypoint_id)
        _validate_base_navigation_waypoint_pose(waypoint, waypoint_id=waypoint_id, errors=errors)
        _validate_base_navigation_waypoint_area_binding(
            waypoint,
            waypoint_id=waypoint_id,
            navigation_areas=navigation_areas,
            errors=errors,
        )
        _validate_base_navigation_waypoint_policy(
            waypoint,
            waypoint_id=waypoint_id,
            errors=errors,
        )
        forbidden_keys = sorted(BASE_WAYPOINT_FORBIDDEN_KEYS.intersection(waypoint))
        if forbidden_keys:
            errors.append(
                f"Base Navigation Map waypoint {waypoint_id} contains forbidden fields: "
                f"{forbidden_keys}"
            )


def _validate_base_navigation_waypoint_pose(
    waypoint: dict[str, Any],
    *,
    waypoint_id: str,
    errors: list[str],
) -> None:
    for key in ("x", "y", "yaw"):
        try:
            float(waypoint.get(key))
        except (TypeError, ValueError):
            errors.append(f"Base Navigation Map waypoint {waypoint_id} missing numeric {key}")
    if not str(waypoint.get("frame_id") or ""):
        errors.append(f"Base Navigation Map waypoint {waypoint_id} missing frame_id")


def _validate_base_navigation_waypoint_area_binding(
    waypoint: dict[str, Any],
    *,
    waypoint_id: str,
    navigation_areas: dict[str, dict[str, Any]],
    errors: list[str],
) -> None:
    area_id = str(
        waypoint.get("navigation_area_id")
        or waypoint.get("map_area_id")
        or waypoint.get("area_id")
        or ""
    )
    if not area_id:
        errors.append(f"Base Navigation Map waypoint {waypoint_id} missing navigation_area_id")
    elif area_id not in navigation_areas:
        errors.append(
            f"Base Navigation Map waypoint {waypoint_id} binds unknown navigation_area_id "
            f"{area_id!r}"
        )


def _validate_base_navigation_waypoint_policy(
    waypoint: dict[str, Any],
    *,
    waypoint_id: str,
    errors: list[str],
) -> None:
    if waypoint.get("purpose") != "base_navigation_area_inspection":
        errors.append(
            f"Base Navigation Map waypoint {waypoint_id} purpose must be "
            "base_navigation_area_inspection"
        )
    if not str(waypoint.get("generation_policy") or ""):
        errors.append(
            f"Base Navigation Map waypoint {waypoint_id} missing generation_policy"
        )
    try:
        sweep_index = int(waypoint.get("sweep_index"))
    except (TypeError, ValueError):
        errors.append(f"Base Navigation Map waypoint {waypoint_id} missing numeric sweep_index")
        return
    if sweep_index <= 0:
        errors.append(f"Base Navigation Map waypoint {waypoint_id} sweep_index must be positive")


def _validate_base_navigation_provenance(
    semantics: dict[str, Any],
    errors: list[str],
) -> None:
    provenance = (
        semantics.get("provenance") if isinstance(semantics.get("provenance"), dict) else {}
    )
    for key in (
        "contains_static_fixtures",
        "contains_receptacles",
        "contains_movable_objects",
        "contains_runtime_observations",
        "contains_private_scoring_truth",
        "uses_navigation_memory_as_waypoint_source",
    ):
        if provenance.get(key) is not False:
            errors.append(f"Base Navigation Map v1 provenance.{key} must be false")


def _validate_base_navigation_sidecar_scope(
    semantics: dict[str, Any],
    errors: list[str],
) -> None:
    if "digital_twin_capabilities" not in semantics:
        return
    provenance = (
        semantics.get("provenance") if isinstance(semantics.get("provenance"), dict) else {}
    )
    if not provenance.get("b1_base_navigation_sidecar"):
        errors.append(
            "digital_twin_capabilities are allowed only as sidecar capability metadata"
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

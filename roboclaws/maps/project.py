from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.maps.bundle import (
    DEFAULT_COSTMAP_PARAMETERS,
    metric_map_bundle_metadata,
    parse_map_yaml,
)
from roboclaws.maps.rasterize import load_pgm

REAL_ROBOT_MAP_BUNDLE_SCHEMA = "real_robot_map_bundle_v1"
REALWORLD_CONTRACT = "realworld_cleanup_v1"


def metric_map_from_bundle(
    bundle_dir: Path,
    *,
    contract: str = REALWORLD_CONTRACT,
) -> dict[str, Any]:
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    map_yaml = parse_map_yaml((bundle_dir / "map.yaml").read_text(encoding="utf-8"))
    resolution = float(map_yaml.get("resolution") or DEFAULT_COSTMAP_PARAMETERS["resolution_m"])
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else [0.0, 0.0, 0.0]
    image_path = bundle_dir / str(map_yaml.get("image") or "map.pgm")
    grid = load_pgm(
        image_path,
        resolution_m=resolution,
        origin_x=float(origin[0] if len(origin) > 0 else 0.0),
        origin_y=float(origin[1] if len(origin) > 1 else 0.0),
    )
    map_id = str(semantics.get("map_id") or bundle_dir.name)
    map_version = str(semantics.get("map_version") or "static-fixture-map-v1")
    waypoints = []
    for item in semantics.get("inspection_waypoints") or []:
        waypoint = dict(item)
        waypoint.setdefault("frame_id", (semantics.get("frame_ids") or {}).get("map", "map"))
        waypoint.setdefault("visited", False)
        waypoints.append(waypoint)
    robot_pose = (
        {
            "frame_id": "map",
            **_waypoint_pose(waypoints[0]),
            "waypoint_id": waypoints[0]["waypoint_id"],
        }
        if waypoints
        else {"frame_id": "map", "x": 0.0, "y": 0.0, "yaw": 0.0, "waypoint_id": ""}
    )
    return {
        "ok": True,
        "tool": "metric_map",
        "status": "ok",
        "contract": contract,
        "schema": REAL_ROBOT_MAP_BUNDLE_SCHEMA,
        "frame_id": (semantics.get("frame_ids") or {}).get("map", "map"),
        "map_id": map_id,
        "map_version": map_version,
        "resolution_m": resolution,
        "origin": {
            "x": float(origin[0] if len(origin) > 0 else 0.0),
            "y": float(origin[1] if len(origin) > 1 else 0.0),
            "yaw": float(origin[2] if len(origin) > 2 else 0.0),
        },
        "width": grid.width,
        "height": grid.height,
        "occupancy_values": {"unknown": -1, "free": 0, "occupied": 100},
        "occupancy_grid_artifact": "map_bundle/map.pgm",
        "map_bundle": metric_map_bundle_metadata(
            environment_id=str(semantics.get("environment_id") or bundle_dir.name),
            map_id=map_id,
            map_version=map_version,
        ),
        "rooms": semantics.get("rooms") or [],
        "driveable_ways": semantics.get("driveable_ways") or [],
        "robot_pose": robot_pose,
        "inspection_waypoints": waypoints,
        "public_contract_note": (
            "Metric map projection was derived from a prebuilt Nav2 map bundle. "
            "Runtime movable objects and private scoring truth are not encoded."
        ),
    }


def fixture_hints_from_bundle(
    bundle_dir: Path,
    *,
    fixture_hint_mode: str = "room_only",
    contract: str = REALWORLD_CONTRACT,
) -> dict[str, Any]:
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    fixtures_by_room: dict[str, list[dict[str, Any]]] = {}
    for fixture in semantics.get("fixtures") or []:
        fixtures_by_room.setdefault(str(fixture.get("room_id") or ""), []).append(dict(fixture))
    rooms = []
    for room in semantics.get("rooms") or []:
        item = dict(room)
        item["fixtures"] = fixtures_by_room.get(str(room.get("room_id") or ""), [])
        rooms.append(item)
    return {
        "ok": True,
        "tool": "fixture_hints",
        "status": "ok",
        "contract": contract,
        "schema": "static_fixture_semantic_map_v1",
        "fixture_hint_mode": fixture_hint_mode,
        "contains_runtime_observations": False,
        "public_contract_note": (
            "Static fixture hints are projected from the selected Nav2 map bundle."
        ),
        "rooms": rooms,
    }


def _waypoint_pose(waypoint: dict[str, Any]) -> dict[str, float]:
    return {
        "x": float(waypoint.get("x", 0.0)),
        "y": float(waypoint.get("y", 0.0)),
        "yaw": float(waypoint.get("yaw", 0.0)),
    }

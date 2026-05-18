from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

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
    "footprint": {
        "type": "radius",
        "radius_m": 0.35,
    },
    "camera": {
        "frame_id": "head_camera_rgb_optical_frame",
        "mount": "rby1m_head",
    },
    "navigation_tolerances": {
        "xy_goal_tolerance_m": 0.25,
        "yaw_goal_tolerance_rad": 0.35,
    },
}
RUNTIME_COSTMAP_GAPS = (
    "runtime_obstacle_layer_not_simulated",
    "voxel_layer_not_simulated",
    "rolling_local_costmap_not_simulated",
    "tf_timing_not_simulated",
)
_BUNDLE_RELATIVE_PATHS = {
    "map_yaml": "map_bundle/map.yaml",
    "occupancy_image": "map_bundle/map.pgm",
    "semantics_json": "map_bundle/semantics.json",
    "robot_profile": "map_bundle/profiles/rby1m.yaml",
    "costmap_params": "map_bundle/costmaps/rby1m.costmap_params.yaml",
    "preview_png": "map_bundle/preview.png",
}


def metric_map_bundle_metadata(
    *,
    environment_id: str,
    map_id: str,
    map_version: str,
) -> dict[str, Any]:
    """Return public Nav2 bundle metadata for the metric map response."""
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
        "artifact_paths": dict(_BUNDLE_RELATIVE_PATHS),
        "costmap_defaults": dict(DEFAULT_COSTMAP_PARAMETERS),
        "runtime_costmap_gaps": list(RUNTIME_COSTMAP_GAPS),
        "parameter_hash": _stable_hash(parameters),
        "public_contract_note": (
            "Map bundle paths are public static environment artifacts. Runtime movable "
            "objects and private scoring truth are not encoded in this bundle."
        ),
    }


def attach_nav2_map_bundle_snapshot(*, run_result: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    """Write a run-local Nav2-shaped map bundle and attach evidence to ``run_result``."""
    agent_view = (
        run_result.get("agent_view") if isinstance(run_result.get("agent_view"), dict) else {}
    )
    metric_map = (
        agent_view.get("metric_map") if isinstance(agent_view.get("metric_map"), dict) else {}
    )
    fixture_hints = (
        agent_view.get("fixture_hints") if isinstance(agent_view.get("fixture_hints"), dict) else {}
    )
    snapshot = write_nav2_map_bundle_snapshot(
        run_dir=run_dir,
        metric_map=metric_map,
        fixture_hints=fixture_hints,
    )
    run_result["nav2_map_bundle"] = snapshot
    artifacts = run_result.setdefault("artifacts", {})
    artifacts["map_bundle"] = str(run_dir / "map_bundle")
    artifacts["nav2_map_yaml"] = str(run_dir / _BUNDLE_RELATIVE_PATHS["map_yaml"])
    artifacts["nav2_occupancy_image"] = str(run_dir / _BUNDLE_RELATIVE_PATHS["occupancy_image"])
    artifacts["nav2_map_preview"] = str(run_dir / _BUNDLE_RELATIVE_PATHS["preview_png"])
    readiness = run_result.get("real_robot_readiness")
    if isinstance(readiness, dict):
        readiness["map_bundle_snapshot_present"] = snapshot["snapshot_complete"]
        readiness["map_bundle_artifact_count"] = len(snapshot["artifact_hashes"])
        readiness["map_bundle_parameter_hash"] = snapshot["parameter_hash"]
        readiness["map_bundle_snapshot_root"] = snapshot["snapshot_root"]
        readiness["runtime_costmap_gaps"] = list(RUNTIME_COSTMAP_GAPS)
        readiness["readiness_sections_complete"] = bool(
            readiness.get("readiness_sections_complete") and snapshot["snapshot_complete"]
        )
    return snapshot


def write_nav2_map_bundle_snapshot(
    *,
    run_dir: Path,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any]:
    bundle_dir = run_dir / "map_bundle"
    profiles_dir = bundle_dir / "profiles"
    costmaps_dir = bundle_dir / "costmaps"
    profiles_dir.mkdir(parents=True, exist_ok=True)
    costmaps_dir.mkdir(parents=True, exist_ok=True)

    map_id = str(metric_map.get("map_id") or "realworld_cleanup_semantic_map")
    map_version = str(metric_map.get("map_version") or "static-fixture-map-v1")
    environment_id = map_id.removesuffix("_semantic_map")
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

    map_yaml_path = bundle_dir / "map.yaml"
    map_pgm_path = bundle_dir / "map.pgm"
    semantics_path = bundle_dir / "semantics.json"
    robot_profile_path = profiles_dir / "rby1m.yaml"
    costmap_params_path = costmaps_dir / "rby1m.costmap_params.yaml"
    preview_path = bundle_dir / "preview.png"

    _write_pgm(map_pgm_path, metric_map)
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
        "schema": NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA,
        "source_schema": metric_map.get("schema", ""),
        "environment_id": environment_id,
        "map_id": map_id,
        "map_version": map_version,
        "source_provenance": "molmospaces_public_semantic_map",
        "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
        "costmap_profile_id": DEFAULT_COSTMAP_PROFILE_ID,
        "parameter_hash": parameter_hash,
        "snapshot_root": "map_bundle",
        "snapshot_complete": set(artifact_paths) <= set(hashes),
        "artifact_paths": {
            key: path.relative_to(run_dir).as_posix() for key, path in artifact_paths.items()
        },
        "artifact_hashes": hashes,
        "runtime_costmap_gaps": list(RUNTIME_COSTMAP_GAPS),
        "public_contract_note": (
            "Snapshot files freeze the public Nav2-shaped map contract used by this run. "
            "They do not encode movable-object target truth or private scoring data."
        ),
    }


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
    return {
        "schema": "nav2_cleanup_semantics_v1",
        "frame_ids": {
            "map": str(metric_map.get("frame_id") or "map"),
            "base": DEFAULT_ROBOT_PROFILE["base_frame_id"],
            "camera": DEFAULT_ROBOT_PROFILE["camera"]["frame_id"],
        },
        "map_id": metric_map.get("map_id"),
        "map_version": metric_map.get("map_version"),
        "rooms": metric_map.get("rooms") or [],
        "fixtures": _fixtures_from_hints(fixture_hints),
        "inspection_waypoints": metric_map.get("inspection_waypoints") or [],
        "driveable_ways": metric_map.get("driveable_ways") or [],
        "provenance": {
            "source": "molmospaces_public_semantic_map",
            "contains_runtime_observations": False,
            "contains_private_scoring_truth": False,
        },
    }


def _fixtures_from_hints(fixture_hints: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            item = dict(fixture)
            item.setdefault("room_id", room.get("room_id", ""))
            fixtures.append(item)
    return fixtures


def _write_pgm(path: Path, metric_map: dict[str, Any]) -> None:
    width = int(metric_map.get("width") or 240)
    height = int(metric_map.get("height") or 180)
    width = max(16, min(width, 1024))
    height = max(16, min(height, 1024))
    rows = [[254 for _ in range(width)] for _ in range(height)]
    for x in range(width):
        rows[0][x] = 0
        rows[height - 1][x] = 0
    for y in range(height):
        rows[y][0] = 0
        rows[y][width - 1] = 0
    text_rows = [" ".join(str(value) for value in row) for row in rows]
    path.write_text(f"P2\n{width} {height}\n255\n" + "\n".join(text_rows) + "\n", encoding="ascii")


def _write_preview(path: Path, metric_map: dict[str, Any], fixture_hints: dict[str, Any]) -> None:
    image = Image.new("RGB", (900, 560), (247, 249, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 882, 542), outline=(175, 184, 196), width=2)
    draw.text((34, 32), "Nav2 static map bundle preview", fill=(28, 35, 48))

    bounds = _coordinate_bounds(metric_map)

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

    for fixture in _fixtures_from_hints(fixture_hints):
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


def _coordinate_bounds(metric_map: dict[str, Any]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    for room in metric_map.get("rooms") or []:
        for point in room.get("polygon") or []:
            xs.append(float(point.get("x", 0.0)))
            ys.append(float(point.get("y", 0.0)))
    for waypoint in metric_map.get("inspection_waypoints") or []:
        xs.append(float(waypoint.get("x", 0.0)))
        ys.append(float(waypoint.get("y", 0.0)))
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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

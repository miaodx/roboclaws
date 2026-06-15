from __future__ import annotations

import copy
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from roboclaws.maps.bundle_validation import (
    parse_map_yaml as parse_map_yaml,
)
from roboclaws.maps.bundle_validation import (
    validate_nav2_map_bundle_payload,
)
from roboclaws.maps.rasterize import (
    OccupancyGrid,
    fixtures_from_hints,
    load_pgm,
    occupancy_grid_from_metric_map,
    world_to_grid,
    write_pgm,
)
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_NATIVE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_rooms,
    source_frame_spatial_contract,
)

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


def copy_nav2_map_bundle_snapshot(
    *,
    source_bundle_dir: Path,
    run_dir: Path,
) -> dict[str, Any]:
    """Copy a validated prebuilt Nav2 map bundle into a run-local snapshot."""
    source_bundle_dir = Path(source_bundle_dir)
    validation = validate_nav2_map_bundle(source_bundle_dir)
    validation.raise_for_errors()

    bundle_dir = Path(run_dir) / "map_bundle"
    for key, relative in _bundle_local_paths().items():
        source = source_bundle_dir / relative
        destination = bundle_dir / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    snapshot = _existing_bundle_snapshot(
        bundle_dir=bundle_dir,
        run_dir=Path(run_dir),
        source_bundle_dir=source_bundle_dir,
    )
    snapshot["schema"] = NAV2_MAP_BUNDLE_SNAPSHOT_SCHEMA
    snapshot["snapshot_root"] = "map_bundle"
    return snapshot


def write_nav2_map_bundle(
    bundle_dir: Path,
    *,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> dict[str, Any]:
    metric_map, fixture_hints = _normalized_bundle_inputs(metric_map, fixture_hints)
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
    write_source_frame_bundle_preview(bundle_dir, output_path=preview_path)

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


def _existing_bundle_snapshot(
    *,
    bundle_dir: Path,
    run_dir: Path,
    source_bundle_dir: Path | None = None,
) -> dict[str, Any]:
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    environment_id = str(semantics.get("environment_id") or bundle_dir.name)
    map_id = str(semantics.get("map_id") or f"{environment_id}_semantic_map")
    map_version = str(semantics.get("map_version") or "static-fixture-map-v1")
    metadata = metric_map_bundle_metadata(
        environment_id=environment_id,
        map_id=map_id,
        map_version=map_version,
    )
    artifact_paths = {key: bundle_dir / relative for key, relative in _bundle_local_paths().items()}
    hashes = {key: _file_sha256(path) for key, path in artifact_paths.items() if path.is_file()}
    payload = {
        "schema": NAV2_MAP_BUNDLE_SCHEMA,
        "source_schema": semantics.get("schema", ""),
        "environment_id": environment_id,
        "map_id": map_id,
        "map_version": map_version,
        "source_provenance": (semantics.get("provenance") or {}).get(
            "source",
            "prebuilt_nav2_map_bundle",
        ),
        "robot_profile_id": DEFAULT_ROBOT_PROFILE_ID,
        "costmap_profile_id": DEFAULT_COSTMAP_PROFILE_ID,
        "parameter_hash": metadata["parameter_hash"],
        "snapshot_root": bundle_dir.name,
        "snapshot_complete": set(artifact_paths) <= set(hashes),
        "artifact_paths": {
            key: path.relative_to(run_dir).as_posix() for key, path in artifact_paths.items()
        },
        "artifact_hashes": hashes,
        "runtime_costmap_gaps": list(RUNTIME_COSTMAP_GAPS),
        "public_contract_note": (
            "Snapshot files freeze the selected prebuilt Nav2 map bundle used by this run. "
            "They do not encode movable-object target truth or private scoring data."
        ),
    }
    if source_bundle_dir is not None:
        payload["source_bundle_root"] = str(source_bundle_dir)
    return payload


def validate_nav2_map_bundle(bundle_dir: Path) -> MapBundleValidation:
    bundle_dir = Path(bundle_dir)
    errors, warnings, metadata = validate_nav2_map_bundle_payload(
        bundle_dir,
        paths=_bundle_local_paths(),
        default_resolution_m=DEFAULT_COSTMAP_PARAMETERS["resolution_m"],
        private_map_keys=PRIVATE_MAP_KEYS,
    )
    return MapBundleValidation(bundle_dir, errors, warnings, metadata)


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


def _normalized_bundle_inputs(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_map = copy.deepcopy(metric_map)
    normalized_hints = copy.deepcopy(fixture_hints)
    _normalize_room_only_fixture_poses(normalized_map, normalized_hints)
    return normalized_map, normalized_hints


def _normalize_room_only_fixture_poses(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> None:
    rooms_by_id = {str(room.get("room_id") or ""): room for room in metric_map.get("rooms") or []}
    waypoints_by_room: dict[str, list[dict[str, Any]]] = {}
    for waypoint in metric_map.get("inspection_waypoints") or []:
        waypoints_by_room.setdefault(str(waypoint.get("room_id") or ""), []).append(waypoint)

    next_slot_by_room: dict[str, int] = {}
    for hint_room in fixture_hints.get("rooms") or []:
        if not isinstance(hint_room, dict):
            continue
        room_id = str(hint_room.get("room_id") or "")
        room = rooms_by_id.get(room_id) or hint_room
        waypoints = waypoints_by_room.get(room_id, [])
        if not waypoints:
            continue
        for fixture in hint_room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            if str(fixture.get("position_detail") or "") != "room_only":
                continue
            if not _fixture_blocks_waypoint(fixture, waypoints):
                continue
            candidates = _fixture_slot_candidates(room, fixture)
            offset = next_slot_by_room.get(room_id, 0)
            candidate, index = _next_nonblocking_fixture_pose(
                fixture,
                waypoints=waypoints,
                candidates=candidates,
                offset=offset,
            )
            if candidate is None:
                continue
            pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
            fixture["pose"] = {
                "frame_id": str(pose.get("frame_id") or "map"),
                "x": round(candidate[0], 3),
                "y": round(candidate[1], 3),
                "yaw": float(pose.get("yaw") or 0.0),
            }
            next_slot_by_room[room_id] = (offset + index + 1) % max(len(candidates), 1)


def _fixture_blocks_waypoint(
    fixture: dict[str, Any],
    waypoints: list[dict[str, Any]],
) -> bool:
    pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
    center = (float(pose.get("x") or 0.0), float(pose.get("y") or 0.0))
    return _fixture_pose_blocks_waypoint(fixture, center, waypoints)


def _next_nonblocking_fixture_pose(
    fixture: dict[str, Any],
    *,
    waypoints: list[dict[str, Any]],
    candidates: list[tuple[float, float]],
    offset: int,
) -> tuple[tuple[float, float] | None, int]:
    ordered_candidates = candidates[offset:] + candidates[:offset]
    for index, candidate in enumerate(ordered_candidates):
        if not _fixture_pose_blocks_waypoint(fixture, candidate, waypoints):
            return candidate, index
    return None, 0


def _fixture_pose_blocks_waypoint(
    fixture: dict[str, Any],
    center: tuple[float, float],
    waypoints: list[dict[str, Any]],
) -> bool:
    width_m, depth_m = _fixture_footprint_size(fixture)
    half_width = width_m / 2.0 + 0.05
    half_depth = depth_m / 2.0 + 0.05
    center_x, center_y = center
    for waypoint in waypoints:
        waypoint_x = float(waypoint.get("x", 0.0))
        waypoint_y = float(waypoint.get("y", 0.0))
        if abs(waypoint_x - center_x) <= half_width and abs(waypoint_y - center_y) <= half_depth:
            return True
    return False


def _fixture_slot_candidates(
    room: dict[str, Any],
    fixture: dict[str, Any],
) -> list[tuple[float, float]]:
    min_x, min_y, max_x, max_y = _room_bounds(room)
    width_m, depth_m = _fixture_footprint_size(fixture)
    x_pad = max(width_m / 2.0 + 0.1, 0.2)
    y_pad = max(depth_m / 2.0 + 0.1, 0.2)
    left = min(max_x, min_x + x_pad)
    right = max(min_x, max_x - x_pad)
    bottom = min(max_y, min_y + y_pad)
    top = max(min_y, max_y - y_pad)
    mid_x = (min_x + max_x) / 2.0
    mid_y = (min_y + max_y) / 2.0
    return [
        (left, bottom),
        (right, bottom),
        (left, top),
        (right, top),
        (left, mid_y),
        (right, mid_y),
        (mid_x, bottom),
        (mid_x, top),
    ]


def _fixture_footprint_size(fixture: dict[str, Any]) -> tuple[float, float]:
    footprint = fixture.get("footprint") if isinstance(fixture.get("footprint"), dict) else {}
    return (
        float(footprint.get("width_m") or 0.45),
        float(footprint.get("depth_m") or 0.35),
    )


def _room_bounds(room: dict[str, Any]) -> tuple[float, float, float, float]:
    polygon = room.get("polygon") or []
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        return (0.0, 0.0, 2.0, 2.0)
    return (min(xs), min(ys), max(xs), max(ys))


def _semantics_payload(metric_map: dict[str, Any], fixture_hints: dict[str, Any]) -> dict[str, Any]:
    metadata = (
        metric_map.get("map_bundle") if isinstance(metric_map.get("map_bundle"), dict) else {}
    )
    frame_id = str(metric_map.get("frame_id") or "map")
    return {
        "schema": "nav2_cleanup_semantics_v1",
        "environment_id": metadata.get("environment_id") or metric_map.get("map_id"),
        "frame_ids": {
            "map": frame_id,
            "base": DEFAULT_ROBOT_PROFILE["base_frame_id"],
            "camera": DEFAULT_ROBOT_PROFILE["camera"]["frame_id"],
        },
        "spatial_contract": source_frame_spatial_contract(
            frame_id=frame_id,
            alignment_status=ALIGNMENT_STATUS_NATIVE,
        ),
        "display_frame": None,
        "map_id": metric_map.get("map_id"),
        "map_version": metric_map.get("map_version"),
        "rooms": normalize_spatial_rooms(
            metric_map.get("rooms") or [],
            frame_id=frame_id,
            polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
            geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
            alignment_status=ALIGNMENT_STATUS_NATIVE,
        ),
        "fixtures": fixtures_from_hints(fixture_hints),
        "inspection_waypoints": metric_map.get("inspection_waypoints") or [],
        "driveable_ways": metric_map.get("driveable_ways") or [],
        "provenance": {
            "source": "molmospaces_public_semantic_map",
            "contains_runtime_observations": False,
            "contains_private_scoring_truth": False,
        },
    }


def write_source_frame_bundle_preview(bundle_dir: Path, *, output_path: Path | None = None) -> Path:
    """Render preview.png from the bundle's source occupancy image and map-frame semantics."""

    bundle_dir = Path(bundle_dir)
    output_path = output_path or bundle_dir / "preview.png"
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))
    map_yaml = parse_map_yaml((bundle_dir / "map.yaml").read_text(encoding="utf-8"))
    resolution = float(map_yaml.get("resolution") or 0.05)
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]
    grid = load_pgm(
        bundle_dir / str(map_yaml.get("image") or "map.pgm"),
        resolution_m=resolution,
        origin_x=float(origin[0]),
        origin_y=float(origin[1]),
    )
    image = _source_grid_preview_image(grid)
    draw = ImageDraw.Draw(image, "RGBA")

    def project(x: float, y: float) -> tuple[int, int]:
        return world_to_grid(x, y, grid)

    draw.rectangle((10, 10, 430, 46), fill=(255, 255, 255, 225), outline=(213, 220, 230, 230))
    draw.text((18, 17), "Source map frame; display_frame absent", fill=(30, 41, 59, 255))

    for room in semantics.get("rooms") or []:
        points = [
            project(float(point.get("x", 0.0)), float(point.get("y", 0.0)))
            for point in room.get("polygon") or []
            if isinstance(point, dict)
        ]
        if len(points) < 3:
            continue
        draw.polygon(points, fill=(72, 121, 210, 44), outline=(31, 79, 168, 210))
        cx = sum(point[0] for point in points) / len(points)
        cy = sum(point[1] for point in points) / len(points)
        label = str(room.get("room_label") or room.get("room_id") or "")
        draw.text((cx - 28, cy - 7), label[:18], fill=(15, 39, 82, 255))

    for fixture in semantics.get("fixtures") or []:
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        x, y = project(float(pose.get("x", 0.0)), float(pose.get("y", 0.0)))
        draw.rectangle((x - 7, y - 5, x + 7, y + 5), fill=(130, 82, 32, 230))

    for waypoint in semantics.get("inspection_waypoints") or []:
        x, y = project(float(waypoint.get("x", 0.0)), float(waypoint.get("y", 0.0)))
        draw.ellipse((x - 5, y - 5, x + 5, y + 5), fill=(34, 158, 91, 245))
        draw.text((x + 7, y - 6), str(waypoint.get("waypoint_id") or ""), fill=(12, 74, 38, 255))

    max_width = 1200
    if image.width > max_width:
        ratio = max_width / image.width
        image = image.resize((max_width, max(1, int(image.height * ratio))))
    image = _pad_preview_canvas(image)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path, format="PNG")
    return output_path


def _source_grid_preview_image(grid: OccupancyGrid) -> Image.Image:
    pixels = bytes(
        255 if value >= 250 else 25 if value <= 5 else 205 for row in grid.rows for value in row
    )
    return Image.frombytes("L", (grid.width, grid.height), pixels).convert("RGB")


def _pad_preview_canvas(image: Image.Image) -> Image.Image:
    margin_x = 10
    margin_top = 10
    margin_bottom = 28
    min_height = 240
    output = Image.new(
        "RGB",
        (image.width + margin_x * 2, max(min_height, image.height + margin_top + margin_bottom)),
        (205, 205, 205),
    )
    output.paste(image, (margin_x, margin_top))
    return output


def _write_preview(path: Path, metric_map: dict[str, Any], fixture_hints: dict[str, Any]) -> None:
    image = Image.new("RGB", (900, 560), (247, 249, 252))
    draw = ImageDraw.Draw(image)
    draw.rectangle((18, 18, 882, 542), outline=(175, 184, 196), width=2)
    draw.text((34, 32), "Nav2 static map bundle preview", fill=(28, 35, 48))
    draw.text((34, 52), "Raw/source-map aligned; display_frame absent", fill=(86, 95, 112))
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


def _stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

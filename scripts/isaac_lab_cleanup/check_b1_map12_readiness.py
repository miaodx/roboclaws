#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.maps.bundle import parse_map_yaml
from roboclaws.maps.rasterize import load_pgm

READINESS_SCHEMA = "b1_map12_digital_twin_readiness_v1"
NAVIGATION_SMOKE_SCHEMA = "b1_map12_navigation_smoke_v1"
SEMANTIC_SOURCE = "robot_map_12_navigation_memory_overlay"
SEMANTIC_USD_BLOCKED = "blocked_until_segmentation_or_manifest"
NAVIGATION_PROVENANCE = "isaac_b1_map12_navigation_smoke"
DEFAULT_B1_LIVINGROOM_USD = Path("usda/livingroom/livingroom_usdz_unpacked/livingroom.usda")
DEFAULT_B1_FULL_FLOOR_USD = Path("usda/F2_all/F2_all.usda")
DEFAULT_B1_FULL_FLOOR_DEFAULT_USD = Path("usda/F2_all/default.usda")
DEFAULT_MAP12_NAV2 = Path("agibot/nav2.yaml")
DEFAULT_MAP12_OCCUPANCY = Path("agibot/occupancy.pgm")
DEFAULT_MAP12_MEMORY = Path("navigation_memory.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build the static B1 / robot_map_12 Digital Twin readiness artifact. "
            "Run this with .venv-isaaclab/bin/python so pxr.Usd is available."
        )
    )
    parser.add_argument("--b1-root", type=Path, required=True)
    parser.add_argument("--map12-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--navigation-artifact",
        type=Path,
        help=(
            "Optional B1 navigation-smoke artifact. When it passes contract validation, "
            "the output readiness artifact may claim robot_navigation_supported=true."
        ),
    )
    parser.add_argument("--require-navigation-success", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_readiness_artifact(args.b1_root, args.map12_root)
    navigation_payload: dict[str, Any] | None = None
    if args.navigation_artifact is not None:
        navigation_payload = json.loads(args.navigation_artifact.read_text(encoding="utf-8"))
        payload = readiness_artifact_with_navigation(
            payload,
            navigation_payload,
            navigation_artifact_path=args.navigation_artifact,
        )
    errors = validate_readiness_artifact(
        payload,
        require_navigation_success=bool(args.require_navigation_success),
    )
    if args.require_navigation_success and navigation_payload is not None:
        errors.extend(
            f"navigation artifact: {error}"
            for error in validate_navigation_smoke_artifact(
                navigation_payload,
                require_files=True,
            )
        )
    payload["validation"] = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": READINESS_SCHEMA,
                "status": payload["validation"]["status"],
                "output": str(args.output),
                "robot_navigation_supported": payload.get("robot_navigation_supported"),
                "map12_overlay_status": payload.get("map12_overlay_status"),
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if not errors else 2


def build_readiness_artifact(b1_root: Path, map12_root: Path) -> dict[str, Any]:
    b1_root = Path(b1_root)
    map12_root = Path(map12_root)
    livingroom = inspect_usd_stage(b1_root / DEFAULT_B1_LIVINGROOM_USD)
    full_floor = inspect_usd_stage(b1_root / DEFAULT_B1_FULL_FLOOR_USD)
    full_floor_default = inspect_usd_stage(b1_root / DEFAULT_B1_FULL_FLOOR_DEFAULT_USD)
    obj_meshes = [inspect_obj_mesh(path) for path in sorted((b1_root / "mesh-files").glob("*.obj"))]
    gaussian_plys = [
        inspect_ply_header(path)
        for path in sorted((b1_root / "point_cloud" / "iteration_100").glob("*.ply"))
    ]
    map12 = inspect_map12(map12_root)
    overlay = build_overlay_report(
        livingroom_bounds=_dict(livingroom.get("world_bounds")),
        map12=map12,
    )
    b1_geometry_loaded = bool(livingroom.get("opened")) and bool(
        _dict(livingroom.get("world_bounds")).get("valid")
    )
    blockers = []
    if not b1_geometry_loaded:
        blockers.append("B1 livingroom USD did not open with finite world bounds.")
    if overlay["status"] == "blocked":
        blockers.append(str(overlay.get("reason") or "Map 12 overlay could not be derived."))
    return {
        "schema": READINESS_SCHEMA,
        "readiness_status": "static_ready_navigation_pending"
        if not blockers
        else "blocked_static_precheck",
        "static_precheck_only": True,
        "b1_root": str(b1_root),
        "map12_root": str(map12_root),
        "b1_geometry_loaded": b1_geometry_loaded,
        "b1_geometry_source": "coarse_usd_or_obj",
        "b1_geometry": {
            "local_geometry": livingroom,
            "full_floor_usd": full_floor,
            "full_floor_default_usd": full_floor_default,
            "obj_meshes": obj_meshes,
            "gaussian_point_clouds": gaussian_plys,
        },
        "usd_object_index_ready": False,
        "usd_receptacle_index_ready": False,
        "reason": "B1 assets are currently coarse meshes without object-level segmentation",
        "map12": map12,
        "map12_overlay_status": overlay["status"],
        "map12_to_b1_usd_transform_status": overlay["transform_status"],
        "map12_overlay": overlay,
        "semantic_source": SEMANTIC_SOURCE,
        "semantic_usd_binding_status": SEMANTIC_USD_BLOCKED,
        "semantic_anchors_are_usd_truth": False,
        "robot_navigation_supported": False,
        "robot_navigation_provenance": "pending_local_isaac_b1_map12_navigation_smoke",
        "robot_navigation_pending_reason": (
            "Static geometry and overlay evidence does not prove robot navigation. "
            "Run the local Isaac B1 / Map 12 navigation smoke before setting "
            "robot_navigation_supported=true."
        ),
        "candidate_navigation_waypoint_count": len(overlay.get("candidate_waypoints") or []),
        "navigation_waypoint_count": 0,
        "robot_view_evidence_status": "pending_local_isaac_navigation_smoke",
        "manipulation_supported": False,
        "blocked_capabilities": [
            "semantic_usd_object_receptacle_binding",
            "pick_place_manipulation",
            "planner_backed_nav2_parity",
        ],
        "blockers": blockers,
    }


def readiness_artifact_with_navigation(
    readiness: dict[str, Any],
    navigation: dict[str, Any],
    *,
    navigation_artifact_path: Path | None = None,
) -> dict[str, Any]:
    payload = json.loads(json.dumps(readiness))
    navigation_errors = validate_navigation_smoke_artifact(navigation, require_files=True)
    payload["static_precheck_only"] = False
    payload["navigation_smoke"] = {
        "artifact": str(navigation_artifact_path) if navigation_artifact_path else "",
        "status": navigation.get("status"),
        "validation_status": "passed" if not navigation_errors else "failed",
        "validation_errors": navigation_errors,
    }
    if navigation_errors:
        payload["robot_navigation_supported"] = False
        payload["robot_navigation_provenance"] = "blocked_local_isaac_b1_map12_navigation_smoke"
        payload["robot_navigation_pending_reason"] = "; ".join(navigation_errors)
        payload["robot_view_evidence_status"] = "blocked"
        payload["navigation_waypoint_count"] = 0
        return payload
    payload["readiness_status"] = "navigation_ready"
    payload["robot_navigation_supported"] = True
    payload["robot_navigation_provenance"] = NAVIGATION_PROVENANCE
    payload["robot_navigation_pending_reason"] = ""
    payload["robot_view_evidence_status"] = "available"
    payload["navigation_waypoint_count"] = int(navigation.get("navigation_waypoint_count") or 0)
    payload["navigation_provenance"] = navigation.get("navigation_provenance")
    payload["navigation_artifact"] = (
        str(navigation_artifact_path) if navigation_artifact_path else ""
    )
    return payload


def inspect_usd_stage(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        return {
            "path": str(path),
            "opened": False,
            "status": "missing",
            "reason": f"USD file is missing: {path}",
        }
    from pxr import Usd, UsdGeom

    stage = Usd.Stage.Open(str(path))
    if stage is None:
        return {
            "path": str(path),
            "opened": False,
            "status": "open_failed",
            "reason": f"pxr.Usd could not open {path}",
        }
    prims = list(stage.Traverse())
    type_counts: dict[str, int] = {}
    for prim in prims:
        type_name = str(prim.GetTypeName() or "typeless")
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    default_prim = stage.GetDefaultPrim()
    used_layers = [
        str(Path(layer.realPath).resolve())
        for layer in stage.GetUsedLayers()
        if str(getattr(layer, "realPath", "") or "")
    ]
    root_path = str(path.resolve())
    local_layers = sorted(layer for layer in used_layers if layer != root_path)
    return {
        "path": str(path),
        "opened": True,
        "status": "opened",
        "default_prim": default_prim.GetName() if default_prim else "",
        "meters_per_unit": float(UsdGeom.GetStageMetersPerUnit(stage)),
        "up_axis": str(UsdGeom.GetStageUpAxis(stage)),
        "prim_count": len(prims),
        "mesh_count": type_counts.get("Mesh", 0),
        "type_counts": type_counts,
        "local_referenced_layers": local_layers,
        "local_referenced_layer_count": len(local_layers),
        "world_bounds": usd_world_bounds(stage, Usd=Usd, UsdGeom=UsdGeom),
        "object_candidate_count": sum(1 for prim in prims if "/Objects/" in str(prim.GetPath())),
        "receptacle_candidate_count": sum(
            1 for prim in prims if "/Receptacles/" in str(prim.GetPath())
        ),
    }


def usd_world_bounds(stage: Any, *, Usd: Any, UsdGeom: Any) -> dict[str, Any]:
    default_prim = stage.GetDefaultPrim()
    if not default_prim:
        return {"valid": False, "reason": "missing default prim"}
    bbox_cache = UsdGeom.BBoxCache(
        Usd.TimeCode.Default(),
        [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy],
    )
    bbox = bbox_cache.ComputeWorldBound(default_prim).ComputeAlignedBox()
    min_point = [float(value) for value in bbox.GetMin()]
    max_point = [float(value) for value in bbox.GetMax()]
    if not _finite_reasonable_bounds(min_point, max_point):
        return {
            "valid": False,
            "min": _round_vec(min_point),
            "max": _round_vec(max_point),
            "reason": (
                "USD world bounds were empty or non-finite for default/render/proxy purposes."
            ),
        }
    size = [max_v - min_v for min_v, max_v in zip(min_point, max_point, strict=True)]
    center = [(min_v + max_v) / 2.0 for min_v, max_v in zip(min_point, max_point, strict=True)]
    return {
        "valid": True,
        "min": _round_vec(min_point),
        "max": _round_vec(max_point),
        "size": _round_vec(size),
        "center": _round_vec(center),
    }


def inspect_obj_mesh(path: Path) -> dict[str, Any]:
    vertex_count = 0
    face_count = 0
    min_point = [math.inf, math.inf, math.inf]
    max_point = [-math.inf, -math.inf, -math.inf]
    with Path(path).open("r", encoding="utf-8", errors="ignore") as handle:
        for line in handle:
            if line.startswith("v "):
                parts = line.split()
                if len(parts) < 4:
                    continue
                try:
                    point = [float(parts[1]), float(parts[2]), float(parts[3])]
                except ValueError:
                    continue
                vertex_count += 1
                for index, value in enumerate(point):
                    min_point[index] = min(min_point[index], value)
                    max_point[index] = max(max_point[index], value)
            elif line.startswith("f "):
                face_count += 1
    valid = vertex_count > 0 and _finite_reasonable_bounds(min_point, max_point)
    return {
        "path": str(path),
        "vertex_count": vertex_count,
        "face_count": face_count,
        "world_bounds": _bounds_payload(min_point, max_point) if valid else {"valid": False},
    }


def inspect_ply_header(path: Path) -> dict[str, Any]:
    comments: dict[str, str] = {}
    vertex_count = 0
    with Path(path).open("rb") as handle:
        for raw_line in handle:
            line = raw_line.decode("ascii", errors="ignore").strip()
            if line.startswith("element vertex "):
                try:
                    vertex_count = int(line.rsplit(" ", 1)[-1])
                except ValueError:
                    vertex_count = 0
            elif line.startswith("comment "):
                parts = line.split(maxsplit=2)
                if len(parts) == 3:
                    key_value = parts[2].split(maxsplit=1)
                    if len(key_value) == 2:
                        comments[key_value[0]] = key_value[1]
            elif line == "end_header":
                break
    min_point = [_float_or_nan(comments.get(key)) for key in ("minx", "miny", "minz")]
    max_point = [_float_or_nan(comments.get(key)) for key in ("maxx", "maxy", "maxz")]
    valid = _finite_reasonable_bounds(min_point, max_point)
    return {
        "path": str(path),
        "vertex_count": vertex_count,
        "header_comment_bounds": _bounds_payload(min_point, max_point)
        if valid
        else {"valid": False},
        "source": comments.get("source", ""),
    }


def inspect_map12(map12_root: Path) -> dict[str, Any]:
    map12_root = Path(map12_root)
    nav2_path = map12_root / DEFAULT_MAP12_NAV2
    occupancy_path = map12_root / DEFAULT_MAP12_OCCUPANCY
    memory_path = map12_root / DEFAULT_MAP12_MEMORY
    nav2 = parse_map_yaml(nav2_path.read_text(encoding="utf-8"))
    origin = nav2.get("origin") if isinstance(nav2.get("origin"), list) else [0.0, 0.0, 0.0]
    resolution = float(nav2.get("resolution") or 0.05)
    grid = load_pgm(
        occupancy_path,
        resolution_m=resolution,
        origin_x=float(origin[0]),
        origin_y=float(origin[1]),
    )
    memory = json.loads(memory_path.read_text(encoding="utf-8"))
    anchors = [_anchor_summary(item, index) for index, item in enumerate(memory.get("items") or [])]
    nav_goal_bounds = _xy_pose_bounds([anchor["nav_goal"] for anchor in anchors])
    pose_bounds = _xy_pose_bounds([anchor["pose"] for anchor in anchors])
    return {
        "schema": "robot_map_12_navigation_memory_inventory_v1",
        "nav2_yaml": str(nav2_path),
        "navigation_memory": str(memory_path),
        "occupancy_pgm": str(occupancy_path),
        "resolution_m": resolution,
        "origin": {"x": float(origin[0]), "y": float(origin[1]), "yaw": float(origin[2])},
        "occupancy_grid": {
            "width": grid.width,
            "height": grid.height,
            "bounds": _bounds_payload(
                [grid.origin_x, grid.origin_y, 0.0],
                [
                    grid.origin_x + grid.width * grid.resolution_m,
                    grid.origin_y + grid.height * grid.resolution_m,
                    0.0,
                ],
            ),
        },
        "anchor_count": len(anchors),
        "anchors_with_nav_goal_count": sum(1 for anchor in anchors if _has_xy(anchor["nav_goal"])),
        "anchors": anchors,
        "nav_goal_bounds": nav_goal_bounds,
        "pose_bounds": pose_bounds,
        "semantic_source": SEMANTIC_SOURCE,
    }


def build_overlay_report(
    *,
    livingroom_bounds: dict[str, Any],
    map12: dict[str, Any],
) -> dict[str, Any]:
    if livingroom_bounds.get("valid") is not True:
        return {
            "status": "blocked",
            "transform_status": "blocked",
            "reason": "B1 livingroom USD bounds are unavailable.",
            "candidate_waypoints": [],
        }
    source_bounds = _dict(map12.get("nav_goal_bounds"))
    if source_bounds.get("valid") is not True:
        return {
            "status": "blocked",
            "transform_status": "blocked",
            "reason": "Map 12 navigation-memory nav_goal bounds are unavailable.",
            "candidate_waypoints": [],
        }
    b1_min = livingroom_bounds["min"]
    b1_max = livingroom_bounds["max"]
    source_min = source_bounds["min"]
    source_max = source_bounds["max"]
    source_width = max(float(source_max[0]) - float(source_min[0]), 1e-6)
    source_depth = max(float(source_max[1]) - float(source_min[1]), 1e-6)
    b1_width = max(float(b1_max[0]) - float(b1_min[0]), 1e-6)
    b1_depth = max(float(b1_max[1]) - float(b1_min[1]), 1e-6)
    transform = {
        "method": "bbox_fit_navigation_memory_nav_goals_to_livingroom_usd_bounds",
        "scale_x": b1_width / source_width,
        "scale_y": b1_depth / source_depth,
        "translate_x": float(b1_min[0]) - float(source_min[0]) * (b1_width / source_width),
        "translate_y": float(b1_min[1]) - float(source_min[1]) * (b1_depth / source_depth),
        "source_frame": "robot_map_12_map",
        "target_frame": "b1_livingroom_usd_world_candidate",
    }
    anchors = [
        anchor
        for anchor in map12.get("anchors") or []
        if isinstance(anchor, dict) and _has_xy(_dict(anchor.get("nav_goal")))
    ]
    floor_z = 0.0
    candidate_waypoints = [
        _candidate_waypoint_from_anchor(anchor, transform=transform, floor_z=floor_z)
        for anchor in anchors[: min(4, len(anchors))]
    ]
    return {
        "status": "candidate" if len(candidate_waypoints) >= 2 else "blocked",
        "transform_status": "unverified",
        "semantic_source": SEMANTIC_SOURCE,
        "source_bounds": source_bounds,
        "target_bounds": livingroom_bounds,
        "transform": {key: _round_float(value) for key, value in transform.items()},
        "candidate_waypoints": candidate_waypoints,
        "candidate_waypoint_count": len(candidate_waypoints),
        "residual_evidence": {
            "status": "not_available",
            "matched_anchor_count": 0,
            "reason": (
                "No human-authored B1/USD anchor correspondences are available. "
                "The overlay is a bounding-box candidate, not verified frame parity."
            ),
        },
        "reason": (
            "Map 12 navigation-memory anchors were projected into the B1 livingroom USD "
            "bounds by a candidate bbox fit. At least three matched anchors with residuals "
            "are required before this can become verified."
        ),
    }


def validate_readiness_artifact(
    payload: dict[str, Any],
    *,
    require_navigation_success: bool = False,
) -> list[str]:
    errors: list[str] = []
    _require(payload.get("schema") == READINESS_SCHEMA, "unexpected readiness schema", errors)
    _require(payload.get("b1_geometry_loaded") is True, "B1 geometry is not loaded", errors)
    _require(
        payload.get("usd_object_index_ready") is False,
        "B1 USD object index must remain false until segmentation or manifest exists",
        errors,
    )
    _require(
        payload.get("usd_receptacle_index_ready") is False,
        "B1 USD receptacle index must remain false until segmentation or manifest exists",
        errors,
    )
    _require(
        payload.get("semantic_source") == SEMANTIC_SOURCE,
        "semantic source must be Map 12 navigation-memory overlay",
        errors,
    )
    _require(
        payload.get("semantic_usd_binding_status") == SEMANTIC_USD_BLOCKED,
        "semantic USD binding must remain blocked",
        errors,
    )
    _require(
        payload.get("semantic_anchors_are_usd_truth") is False,
        "semantic anchors must not be presented as USD prim truth",
        errors,
    )
    _require(
        payload.get("manipulation_supported") is False,
        "manipulation must not be presented as supported",
        errors,
    )
    _require(
        payload.get("map12_overlay_status") in {"candidate", "verified", "blocked"},
        "overlay status must be candidate, verified, or blocked",
        errors,
    )
    if payload.get("static_precheck_only") is True:
        _require(
            payload.get("robot_navigation_supported") is not True,
            "static-only readiness must not claim robot navigation support",
            errors,
        )
    if payload.get("robot_navigation_supported") is True:
        _require(
            payload.get("robot_navigation_provenance") == NAVIGATION_PROVENANCE,
            "navigation support requires B1 navigation-smoke provenance",
            errors,
        )
        _require(
            int(payload.get("navigation_waypoint_count") or 0) >= 2,
            "navigation support requires at least two waypoints",
            errors,
        )
        _require(
            payload.get("robot_view_evidence_status") == "available",
            "navigation support requires robot-view evidence",
            errors,
        )
    elif require_navigation_success:
        errors.append("robot_navigation_supported is not true")
    return errors


def validate_navigation_smoke_artifact(
    payload: dict[str, Any],
    *,
    require_files: bool = False,
) -> list[str]:
    errors: list[str] = []
    _require(
        payload.get("schema") == NAVIGATION_SMOKE_SCHEMA,
        "unexpected navigation schema",
        errors,
    )
    _require(payload.get("status") == "passed", "navigation smoke did not pass", errors)
    _require(
        payload.get("robot_navigation_supported") is True,
        "navigation artifact must claim robot_navigation_supported=true only on pass",
        errors,
    )
    _require(
        payload.get("robot_navigation_provenance") == NAVIGATION_PROVENANCE,
        "navigation artifact provenance must be isaac_b1_map12_navigation_smoke",
        errors,
    )
    _require(
        payload.get("navigation_provenance") in {"kinematic_pose_driven", "planner_backed"},
        "navigation artifact must state kinematic or planner-backed provenance",
        errors,
    )
    _require(
        payload.get("planner_backed") in {True, False},
        "planner_backed must be explicit",
        errors,
    )
    _require(
        payload.get("semantic_source") == SEMANTIC_SOURCE,
        "navigation semantic source must remain Map 12 overlay",
        errors,
    )
    _require(
        payload.get("semantic_usd_binding_status") == SEMANTIC_USD_BLOCKED,
        "navigation artifact must not claim semantic USD binding",
        errors,
    )
    _require(
        payload.get("manipulation_supported") is False,
        "navigation artifact must not claim manipulation support",
        errors,
    )
    waypoints = [item for item in payload.get("waypoint_evidence") or [] if isinstance(item, dict)]
    _require(
        len(waypoints) >= 2,
        "navigation artifact needs at least two waypoint evidence rows",
        errors,
    )
    _require(
        int(payload.get("navigation_waypoint_count") or 0) >= 2,
        "navigation waypoint count must be at least two",
        errors,
    )
    pose_keys = {
        (
            round(float(_dict(item.get("robot_pose")).get("x") or 0.0), 3),
            round(float(_dict(item.get("robot_pose")).get("y") or 0.0), 3),
        )
        for item in waypoints
    }
    _require(len(pose_keys) >= 2, "navigation waypoint robot poses must be distinct", errors)
    for index, item in enumerate(waypoints, start=1):
        views = _dict(item.get("views"))
        _require(bool(views.get("fpv")), f"waypoint {index} missing FPV image", errors)
        if require_files:
            for view_name, raw_path in views.items():
                if not raw_path:
                    continue
                path = Path(str(raw_path))
                _require(
                    path.is_file(),
                    f"waypoint {index} view {view_name} missing: {path}",
                    errors,
                )
    return errors


def _candidate_waypoint_from_anchor(
    anchor: dict[str, Any],
    *,
    transform: dict[str, Any],
    floor_z: float,
) -> dict[str, Any]:
    nav_goal = _dict(anchor.get("nav_goal"))
    yaw = _optional_float(nav_goal.get("yaw"))
    yaw_deg = (
        math.degrees(yaw) if yaw is not None else _optional_float(nav_goal.get("yaw_deg")) or 0.0
    )
    b1_x = float(nav_goal["x"]) * float(transform["scale_x"]) + float(transform["translate_x"])
    b1_y = float(nav_goal["y"]) * float(transform["scale_y"]) + float(transform["translate_y"])
    return {
        "waypoint_id": f"b1_overlay_{anchor['id']}",
        "source_anchor_id": anchor["id"],
        "label": anchor.get("label") or anchor["id"],
        "semantic_source": SEMANTIC_SOURCE,
        "map12_nav_goal": nav_goal,
        "b1_pose": {
            "frame": "b1_livingroom_usd_world_candidate",
            "x": round(b1_x, 6),
            "y": round(b1_y, 6),
            "z": round(float(floor_z), 6),
            "yaw_deg": round(float(yaw_deg), 6),
            "pose_source": SEMANTIC_SOURCE,
        },
    }


def _anchor_summary(item: Any, index: int) -> dict[str, Any]:
    entry = item if isinstance(item, dict) else {}
    return {
        "id": str(entry.get("id") or f"anchor_{index:03d}"),
        "label": str(entry.get("label") or entry.get("id") or f"anchor_{index:03d}"),
        "kind": str(entry.get("kind") or ""),
        "pose": _pose_dict(entry.get("pose")),
        "nav_goal": _pose_dict(entry.get("nav_goal") or entry.get("pose")),
        "confidence": _optional_float(entry.get("confidence")),
        "source": str(entry.get("source") or ""),
    }


def _pose_dict(value: Any) -> dict[str, Any]:
    pose = _dict(value)
    result: dict[str, Any] = {}
    for key in ("x", "y", "z", "yaw", "yaw_deg"):
        parsed = _optional_float(pose.get(key))
        if parsed is not None:
            result[key] = parsed
    return result


def _xy_pose_bounds(poses: list[dict[str, Any]]) -> dict[str, Any]:
    points = [pose for pose in poses if _has_xy(pose)]
    if not points:
        return {"valid": False, "reason": "no xy poses"}
    xs = [float(point["x"]) for point in points]
    ys = [float(point["y"]) for point in points]
    return _bounds_payload([min(xs), min(ys), 0.0], [max(xs), max(ys), 0.0])


def _bounds_payload(min_point: list[float], max_point: list[float]) -> dict[str, Any]:
    if not _finite_reasonable_bounds(min_point, max_point):
        return {"valid": False, "min": _round_vec(min_point), "max": _round_vec(max_point)}
    size = [max_v - min_v for min_v, max_v in zip(min_point, max_point, strict=True)]
    center = [(min_v + max_v) / 2.0 for min_v, max_v in zip(min_point, max_point, strict=True)]
    return {
        "valid": True,
        "min": _round_vec(min_point),
        "max": _round_vec(max_point),
        "size": _round_vec(size),
        "center": _round_vec(center),
    }


def _finite_reasonable_bounds(min_point: list[float], max_point: list[float]) -> bool:
    values = [*min_point, *max_point]
    if any(not math.isfinite(value) or abs(value) > 1e20 for value in values):
        return False
    return all(max_v >= min_v for min_v, max_v in zip(min_point, max_point, strict=True))


def _round_vec(values: list[float]) -> list[float]:
    return [
        round(float(value), 6) if math.isfinite(float(value)) else float(value) for value in values
    ]


def _round_float(value: Any) -> Any:
    if isinstance(value, (int, float)):
        return round(float(value), 9)
    return value


def _float_or_nan(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _optional_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _has_xy(value: dict[str, Any]) -> bool:
    return (
        _optional_float(value.get("x")) is not None and _optional_float(value.get("y")) is not None
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


if __name__ == "__main__":
    raise SystemExit(main())

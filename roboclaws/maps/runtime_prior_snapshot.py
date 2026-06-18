from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from roboclaws.maps.bundle import parse_map_yaml
from roboclaws.maps.rasterize import OccupancyGrid, load_pgm, world_to_grid
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_CANDIDATE,
    GEOMETRY_SOURCE_RUNTIME_OBSERVATION,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_room,
)

RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA = "runtime_map_prior_snapshot_v1"
RUNTIME_METRIC_MAP_SCHEMA = "runtime_metric_map_v1"
PRIVATE_TRUTH_KEYS = frozenset(
    {
        "acceptable_destination_sets",
        "generated_mess_set",
        "global_movable_object_inventory",
        "is_misplaced",
        "private_manifest",
        "target_count",
        "target_receptacle_id",
        "valid_receptacle_ids",
    }
)
MOVABLE_ANCHOR_TYPES = {"movable_object", "object"}
ACTIONABLE_ANCHOR_STATUSES = {"actionable"}


def runtime_prior_snapshot_from_runtime_metric_map(
    runtime_metric_map: dict[str, Any],
    *,
    source_navigation_map: dict[str, Any] | None = None,
    producer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap an online runtime map in the canonical downstream snapshot contract."""

    runtime_metric_map = copy.deepcopy(runtime_metric_map)
    if runtime_metric_map.get("schema") != RUNTIME_METRIC_MAP_SCHEMA:
        raise ValueError(
            "runtime_metric_map must use schema "
            f"{RUNTIME_METRIC_MAP_SCHEMA}, got {runtime_metric_map.get('schema')!r}"
        )
    snapshot = {
        "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
        "source_navigation_map": _source_navigation_map_reference(
            source_navigation_map or runtime_metric_map.get("static_map") or {}
        ),
        "runtime_metric_map": runtime_metric_map,
        "public_semantic_anchors": copy.deepcopy(
            runtime_metric_map.get("public_semantic_anchors") or []
        ),
        "inspection_waypoints": _materialized_waypoints_from_runtime_map(runtime_metric_map),
        "fixture_candidates": _materialized_fixtures_from_runtime_map(runtime_metric_map),
        "producer": {
            "type": "online_map_build",
            "provenance": "map_build_runtime_metric_map",
            **dict(producer or {}),
        },
        "contract": {
            "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
            "runtime_metric_map_schema": RUNTIME_METRIC_MAP_SCHEMA,
            "online_offline_equivalent_shape": True,
            "private_truth_included": False,
            "source_map_mutated": False,
            "movable_object_priors_require_current_run_confirmation": True,
        },
    }
    snapshot["summary"] = _snapshot_summary(snapshot)
    _assert_no_private_truth(snapshot)
    return snapshot


def runtime_prior_snapshot_from_agibot_navigation_memory(
    map_dir: str | Path,
    *,
    producer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convert an Agibot navigation-memory map folder into the canonical snapshot."""

    map_dir = Path(map_dir)
    navigation_memory_path = map_dir / "navigation_memory.json"
    agibot_dir = map_dir / "agibot"
    nav2_yaml_path = agibot_dir / "nav2.yaml"
    occupancy_path = agibot_dir / "occupancy.pgm"
    source_path = agibot_dir / "source.json"
    _require_file(navigation_memory_path)
    _require_file(nav2_yaml_path)
    _require_file(occupancy_path)
    _require_file(source_path)

    navigation_memory = json.loads(navigation_memory_path.read_text(encoding="utf-8"))
    map_yaml = parse_map_yaml(nav2_yaml_path.read_text(encoding="utf-8"))
    grid = load_pgm(
        occupancy_path,
        resolution_m=float(map_yaml.get("resolution") or 0.05),
        origin_x=float((map_yaml.get("origin") or [0.0, 0.0, 0.0])[0]),
        origin_y=float((map_yaml.get("origin") or [0.0, 0.0, 0.0])[1]),
    )
    source = json.loads(source_path.read_text(encoding="utf-8"))

    anchors: list[dict[str, Any]] = []
    waypoints: list[dict[str, Any]] = []
    fixture_candidates: list[dict[str, Any]] = []
    observed_objects: list[dict[str, Any]] = []
    for index, raw_item in enumerate(_navigation_memory_items(navigation_memory), start=1):
        item = raw_item if isinstance(raw_item, dict) else {}
        anchor = _anchor_from_navigation_memory_item(item, index=index, grid=grid)
        anchors.append(anchor)
        waypoint = _waypoint_from_anchor(anchor)
        waypoints.append(waypoint)
        if anchor["anchor_type"] in MOVABLE_ANCHOR_TYPES:
            observed_objects.append(_prior_observed_object_from_anchor(anchor))
        elif anchor["materialization"]["fixture_candidate"]["enabled"]:
            fixture_candidates.append(anchor["materialization"]["fixture_candidate"])
    rooms = _rooms_from_anchors(anchors)
    room_category_hints = _room_category_hints_from_rooms(rooms)

    runtime_metric_map = {
        "schema": RUNTIME_METRIC_MAP_SCHEMA,
        "contract": "realworld_cleanup_contract_v1",
        "freshness": "offline_converted_prior",
        "map_mode": "minimal",
        "minimal_map_mode": True,
        "source_map_mutated": False,
        "private_truth_included": False,
        "static_map": {
            "schema": "agibot_navigation_memory_source_map_v1",
            "contains_runtime_observations": False,
            "contains_private_scoring_truth": False,
            "map_frame": "map",
            "map_id": _map_id(map_dir, source),
            "artifact_paths": _artifact_paths(map_dir),
            "costmap": {
                "resolution_m": grid.resolution_m,
                "origin": {"x": grid.origin_x, "y": grid.origin_y, "yaw": _yaw(map_yaml)},
                "width": grid.width,
                "height": grid.height,
                "occupancy_grid_artifact": "agibot/occupancy.pgm",
            },
        },
        "rooms": rooms,
        "room_category_hints": room_category_hints,
        "driveable_ways": _driveable_ways(rooms),
        "public_semantic_anchors": anchors,
        "observed_objects": observed_objects,
        "map_update_candidates": [],
        "producer_summary": {
            "observed_object_count": len(observed_objects),
            "producer_types": {"agibot_navigation_memory_conversion": len(observed_objects)}
            if observed_objects
            else {},
            "public_semantic_anchor_count": len(anchors),
            "public_semantic_anchor_producer_types": {
                "agibot_navigation_memory_conversion": len(anchors)
            },
            "map_update_candidate_count": 0,
        },
        "public_contract_note": (
            "Offline Agibot navigation memory conversion produces the same downstream "
            "Runtime Metric Map payload used by online intent=map-build output. "
            "Movable objects are preserved only as needs_confirm priors."
        ),
    }
    snapshot = {
        "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
        "source_navigation_map": {
            "schema": "agibot_navigation_memory_source_v1",
            "map_id": _map_id(map_dir, source),
            "source_type": "agibot_navigation_memory",
            "source_root": str(map_dir),
            "navigation_memory": "navigation_memory.json",
            "nav2_yaml": "agibot/nav2.yaml",
            "occupancy_grid_artifact": "agibot/occupancy.pgm",
            "raw_map_artifact": "agibot/raw_map.json.gz"
            if (agibot_dir / "raw_map.json.gz").is_file()
            else "",
            "source_json": "agibot/source.json",
            "rooms": rooms,
            "room_category_hints": room_category_hints,
            "source_hashes": _source_hashes(
                navigation_memory_path,
                nav2_yaml_path,
                occupancy_path,
                source_path,
                agibot_dir / "raw_map.json.gz",
            ),
            "source_map_mutated": False,
        },
        "runtime_metric_map": runtime_metric_map,
        "public_semantic_anchors": anchors,
        "inspection_waypoints": waypoints,
        "fixture_candidates": fixture_candidates,
        "producer": {
            "type": "offline_navigation_memory_conversion",
            "provenance": "agibot_navigation_memory",
            "input_schema_version": navigation_memory.get("schema_version"),
            "updated_at": str(navigation_memory.get("updated_at") or ""),
            **dict(producer or {}),
        },
        "contract": {
            "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
            "runtime_metric_map_schema": RUNTIME_METRIC_MAP_SCHEMA,
            "online_offline_equivalent_shape": True,
            "private_truth_included": False,
            "source_map_mutated": False,
            "movable_object_priors_require_current_run_confirmation": True,
        },
    }
    snapshot["summary"] = _snapshot_summary(snapshot)
    _assert_no_private_truth(snapshot)
    return snapshot


def runtime_prior_snapshot_from_nav2_cleanup_bundle(
    bundle_dir: str | Path,
    *,
    producer: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Wrap a compiled Nav2 cleanup map bundle in the canonical prior contract."""

    bundle_dir = Path(bundle_dir)
    map_yaml_path = bundle_dir / "map.yaml"
    occupancy_path = bundle_dir / "map.pgm"
    semantics_path = bundle_dir / "semantics.json"
    _require_file(map_yaml_path)
    _require_file(occupancy_path)
    _require_file(semantics_path)

    map_yaml = parse_map_yaml(map_yaml_path.read_text(encoding="utf-8"))
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    origin = (origin + [0.0, 0.0, 0.0])[:3]
    grid = load_pgm(
        occupancy_path,
        resolution_m=float(map_yaml.get("resolution") or 0.05),
        origin_x=float(origin[0]),
        origin_y=float(origin[1]),
    )
    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
    if semantics.get("schema") != "nav2_cleanup_semantics_v1":
        raise ValueError(
            "compiled cleanup bundle semantics must use schema nav2_cleanup_semantics_v1"
        )
    rooms = copy.deepcopy(semantics.get("rooms") or [])
    inspection_waypoints = [
        _bundle_waypoint(waypoint)
        for waypoint in semantics.get("inspection_waypoints") or []
        if isinstance(waypoint, dict)
    ]
    anchors = [
        _anchor_from_bundle_waypoint(waypoint, index=index)
        for index, waypoint in enumerate(inspection_waypoints, start=1)
    ]
    runtime_metric_map = {
        "schema": RUNTIME_METRIC_MAP_SCHEMA,
        "contract": "realworld_cleanup_contract_v1",
        "freshness": "offline_compiled_prior",
        "map_mode": "minimal",
        "minimal_map_mode": True,
        "source_map_mutated": False,
        "private_truth_included": False,
        "static_map": {
            "schema": "nav2_cleanup_bundle_source_map_v1",
            "contains_runtime_observations": bool(
                (semantics.get("provenance") or {}).get("contains_runtime_observations")
            ),
            "contains_private_scoring_truth": bool(
                (semantics.get("provenance") or {}).get("contains_private_scoring_truth")
            ),
            "map_frame": _bundle_frame_id(semantics),
            "map_id": str(semantics.get("map_id") or bundle_dir.name),
            "artifact_paths": {
                "nav2_yaml": "map.yaml",
                "occupancy_grid": "map.pgm",
                "semantics": "semantics.json",
            },
            "costmap": {
                "resolution_m": grid.resolution_m,
                "origin": {"x": grid.origin_x, "y": grid.origin_y, "yaw": _yaw(map_yaml)},
                "width": grid.width,
                "height": grid.height,
                "occupancy_grid_artifact": "map.pgm",
            },
        },
        "rooms": rooms,
        "room_category_hints": copy.deepcopy(semantics.get("room_category_hints") or []),
        "driveable_ways": copy.deepcopy(semantics.get("driveable_ways") or []),
        "public_semantic_anchors": anchors,
        "observed_objects": [],
        "map_update_candidates": [],
        "producer_summary": {
            "observed_object_count": 0,
            "producer_types": {},
            "public_semantic_anchor_count": len(anchors),
            "public_semantic_anchor_producer_types": {
                "nav2_cleanup_bundle_conversion": len(anchors)
            }
            if anchors
            else {},
            "map_update_candidate_count": 0,
        },
        "digital_twin_capabilities": copy.deepcopy(
            semantics.get("digital_twin_capabilities") or {}
        ),
        "public_contract_note": (
            "Compiled Nav2 cleanup bundle conversion produces the same downstream "
            "Runtime Metric Map payload used by online intent=map-build output. "
            "It carries public map/waypoint context only; object priors require a "
            "dedicated semantic projection artifact."
        ),
    }
    snapshot = {
        "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
        "source_navigation_map": {
            "schema": "nav2_cleanup_bundle_source_v1",
            "map_id": str(semantics.get("map_id") or bundle_dir.name),
            "source_type": "nav2_cleanup_bundle",
            "source_root": str(bundle_dir),
            "nav2_yaml": "map.yaml",
            "occupancy_grid_artifact": "map.pgm",
            "semantics": "semantics.json",
            "rooms": rooms,
            "room_category_hints": copy.deepcopy(semantics.get("room_category_hints") or []),
            "digital_twin_capabilities": copy.deepcopy(
                semantics.get("digital_twin_capabilities") or {}
            ),
            "source_hashes": _source_hashes(map_yaml_path, occupancy_path, semantics_path),
            "source_map_mutated": False,
        },
        "runtime_metric_map": runtime_metric_map,
        "public_semantic_anchors": anchors,
        "inspection_waypoints": inspection_waypoints,
        "fixture_candidates": [],
        "producer": {
            "type": "offline_nav2_cleanup_bundle_conversion",
            "provenance": "nav2_cleanup_bundle",
            "source_schema": str(semantics.get("schema") or ""),
            "source_provenance": str((semantics.get("provenance") or {}).get("source") or ""),
            **dict(producer or {}),
        },
        "contract": {
            "schema": RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA,
            "runtime_metric_map_schema": RUNTIME_METRIC_MAP_SCHEMA,
            "online_offline_equivalent_shape": True,
            "private_truth_included": False,
            "source_map_mutated": False,
            "movable_object_priors_require_current_run_confirmation": True,
        },
    }
    snapshot["summary"] = _snapshot_summary(snapshot)
    _assert_no_private_truth(snapshot)
    return snapshot


def runtime_metric_map_from_prior_artifact(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Accept either raw runtime_metric_map.json or the canonical snapshot wrapper."""

    if payload is None:
        return None
    schema = payload.get("schema")
    if schema == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA:
        runtime_metric_map = payload.get("runtime_metric_map")
        if not isinstance(runtime_metric_map, dict):
            raise ValueError("runtime map prior snapshot lacks runtime_metric_map")
        if runtime_metric_map.get("schema") != RUNTIME_METRIC_MAP_SCHEMA:
            raise ValueError(
                "runtime map prior snapshot runtime_metric_map must use schema "
                f"{RUNTIME_METRIC_MAP_SCHEMA}, got {runtime_metric_map.get('schema')!r}"
            )
        return copy.deepcopy(runtime_metric_map)
    if schema != RUNTIME_METRIC_MAP_SCHEMA:
        raise ValueError(
            "runtime map prior artifact must be raw "
            f"{RUNTIME_METRIC_MAP_SCHEMA} or {RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA}, got {schema!r}"
        )
    return copy.deepcopy(payload)


def materialize_runtime_prior_targets(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return consumer-facing waypoint and fixture targets from either producer path."""

    if snapshot.get("schema") == RUNTIME_MAP_PRIOR_SNAPSHOT_SCHEMA:
        waypoints = [dict(item) for item in snapshot.get("inspection_waypoints") or []]
        fixtures = [dict(item) for item in snapshot.get("fixture_candidates") or []]
    else:
        wrapped = runtime_prior_snapshot_from_runtime_metric_map(snapshot)
        waypoints = [dict(item) for item in wrapped.get("inspection_waypoints") or []]
        fixtures = [dict(item) for item in wrapped.get("fixture_candidates") or []]
    return {
        "schema": "runtime_map_prior_materialized_targets_v1",
        "inspection_waypoints": waypoints,
        "fixture_candidates": fixtures,
        "actionable_waypoint_ids": [
            str(item.get("waypoint_id") or "")
            for item in waypoints
            if item.get("actionability") == "actionable"
        ],
        "actionable_fixture_ids": [
            str(item.get("fixture_id") or "")
            for item in fixtures
            if item.get("actionability") == "actionable"
        ],
    }


def _anchor_from_navigation_memory_item(
    item: dict[str, Any],
    *,
    index: int,
    grid: OccupancyGrid,
) -> dict[str, Any]:
    item_id = str(item.get("id") or f"navigation_memory_{index:03d}")
    anchor_type = _anchor_type(item)
    nav_goal = _pose_dict(item.get("nav_goal") or item.get("pose") or {})
    object_pose = _pose_dict(item.get("pose") or item.get("nav_goal") or {})
    reachability = _reachability_status(nav_goal, grid=grid)
    classification_status = _classification_status(item, anchor_type=anchor_type)
    actionability = _actionability(anchor_type, reachability["status"], classification_status)
    waypoint_id = _stable_id("wp", item_id)
    affordances = _affordances(item, anchor_type=anchor_type)
    anchor_id = item_id if item_id.startswith("anchor_") else f"anchor_{_safe_id(item_id)}"
    evidence = {
        "type": "agibot_navigation_memory_entry",
        "source": str(item.get("source") or ""),
        "evidence": copy.deepcopy(item.get("evidence") or {}),
        "successful_run_count": len(item.get("successful_runs") or []),
        "notes": str(item.get("notes") or ""),
    }
    materialization = {
        "waypoint": {
            "waypoint_id": waypoint_id,
            "frame_id": "map",
            **nav_goal,
            "anchor_id": anchor_id,
            "anchor_type": anchor_type,
            "label": str(item.get("label") or item_id),
            "room_id": _room_id(item, anchor_type=anchor_type),
            "room_label": _room_label(item, anchor_type=anchor_type),
            "waypoint_source": "agibot_navigation_memory_conversion",
            "actionability": actionability,
            "reachability_status": reachability["status"],
            "costmap_cell": reachability["cell"],
            "costmap_value": reachability["costmap_value"],
        },
        "fixture_candidate": _fixture_candidate(
            anchor_id=anchor_id,
            waypoint_id=waypoint_id,
            item=item,
            anchor_type=anchor_type,
            affordances=affordances,
            actionability=actionability,
            enabled=anchor_type not in MOVABLE_ANCHOR_TYPES
            and anchor_type not in {"landmark", "room_area"},
        ),
    }
    return {
        "anchor_id": anchor_id,
        "source_anchor_id": item_id,
        "anchor_type": anchor_type,
        "category": _category(item, anchor_type=anchor_type),
        "label": str(item.get("label") or item_id),
        "room_id": _room_id(item, anchor_type=anchor_type),
        "room_label": _room_label(item, anchor_type=anchor_type),
        "waypoint_id": waypoint_id,
        "pose": nav_goal,
        "object_pose": object_pose,
        "affordances": affordances,
        "aliases": [str(alias) for alias in item.get("aliases") or []],
        "producer_type": "agibot_navigation_memory_conversion",
        "producer_id": "navigation_memory.json",
        "confidence": _confidence(item),
        "freshness": "prior",
        "classification_status": classification_status,
        "reachability_status": reachability["status"],
        "actionability": actionability,
        "promotion_status": _promotion_status(anchor_type, actionability),
        "materialization": materialization,
        "evidence": evidence,
        "review_status": "needs_review" if classification_status == "needs_review" else "converted",
    }


def _bundle_waypoint(waypoint: dict[str, Any]) -> dict[str, Any]:
    waypoint_id = str(waypoint.get("waypoint_id") or waypoint.get("id") or "")
    return {
        "waypoint_id": waypoint_id,
        "frame_id": str(waypoint.get("frame_id") or "map"),
        "x": _float(waypoint.get("x")),
        "y": _float(waypoint.get("y")),
        "yaw": _float(waypoint.get("yaw")),
        "room_id": str(waypoint.get("room_id") or ""),
        "label": str(waypoint.get("label") or waypoint_id),
        "waypoint_source": str(waypoint.get("waypoint_source") or "nav2_cleanup_bundle"),
        "actionability": _bundle_waypoint_actionability(waypoint),
    }


def _anchor_from_bundle_waypoint(waypoint: dict[str, Any], *, index: int) -> dict[str, Any]:
    waypoint_id = str(waypoint.get("waypoint_id") or f"bundle_waypoint_{index:03d}")
    anchor_id = f"anchor_{_safe_id(waypoint_id)}"
    actionability = str(waypoint.get("actionability") or "actionable")
    return {
        "anchor_id": anchor_id,
        "source_anchor_id": waypoint_id,
        "anchor_type": "room_area" if waypoint.get("room_id") else "landmark",
        "category": "room_area" if waypoint.get("room_id") else "navigation_waypoint",
        "label": str(waypoint.get("label") or waypoint_id),
        "room_id": str(waypoint.get("room_id") or ""),
        "room_label": str(waypoint.get("label") or waypoint.get("room_id") or ""),
        "waypoint_id": waypoint_id,
        "pose": {
            "x": _float(waypoint.get("x")),
            "y": _float(waypoint.get("y")),
            "yaw": _float(waypoint.get("yaw")),
        },
        "affordances": ["navigate", "observe"],
        "aliases": [waypoint_id],
        "producer_type": "nav2_cleanup_bundle_conversion",
        "producer_id": "semantics.json",
        "confidence": 0.8 if actionability == "actionable" else 0.5,
        "freshness": "prior",
        "classification_status": "map_prior",
        "reachability_status": actionability,
        "actionability": actionability,
        "promotion_status": "materialized_static_anchor"
        if actionability == "actionable"
        else actionability,
        "materialization": {
            "waypoint": copy.deepcopy(waypoint),
            "fixture_candidate": {
                "enabled": False,
                "reason": "compiled_bundle_waypoint_not_fixture_anchor",
                "anchor_type": "room_area" if waypoint.get("room_id") else "landmark",
            },
        },
        "evidence": {
            "type": "nav2_cleanup_bundle_waypoint",
            "source": "semantics.json",
        },
        "review_status": "converted",
    }


def _bundle_waypoint_actionability(waypoint: dict[str, Any]) -> str:
    explicit = str(waypoint.get("actionability") or "")
    if explicit:
        return explicit
    source = str(waypoint.get("waypoint_source") or "")
    if source == "generated_exploration_candidate":
        return "actionable"
    return "observe_only"


def _bundle_frame_id(semantics: dict[str, Any]) -> str:
    frame_ids = semantics.get("frame_ids") if isinstance(semantics.get("frame_ids"), dict) else {}
    return str(frame_ids.get("map") or "map")


def _waypoint_from_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    return copy.deepcopy(anchor["materialization"]["waypoint"])


def _prior_observed_object_from_anchor(anchor: dict[str, Any]) -> dict[str, Any]:
    return {
        "object_id": anchor["source_anchor_id"],
        "category": anchor["category"],
        "room_id": anchor["room_id"],
        "waypoint_id": anchor["waypoint_id"],
        "source_fixture_id": "",
        "source_observation_id": _selected_frame(anchor),
        "image_region": {},
        "producer_type": anchor["producer_type"],
        "producer_id": anchor["producer_id"],
        "confidence": anchor["confidence"],
        "freshness": "prior",
        "actionability": "needs_confirm",
        "state": "prior",
        "grounding_status": "prior",
        "candidate_fixture_id": "",
        "candidate_source": "runtime_map_prior_snapshot",
        "promotion_status": "movable_prior_not_static_fixture",
    }


def _fixture_candidate(
    *,
    anchor_id: str,
    waypoint_id: str,
    item: dict[str, Any],
    anchor_type: str,
    affordances: list[str],
    actionability: str,
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "enabled": False,
            "reason": "not_a_fixture_or_receptacle_anchor",
            "anchor_type": anchor_type,
        }
    return {
        "enabled": True,
        "fixture_id": anchor_id,
        "receptacle_id": anchor_id,
        "anchor_id": anchor_id,
        "category": _category(item, anchor_type=anchor_type),
        "name": str(item.get("label") or item.get("id") or anchor_id),
        "room_id": _room_id(item, anchor_type=anchor_type),
        "room_label": _room_label(item, anchor_type=anchor_type),
        "affordances": list(affordances),
        "preferred_inspection_waypoint_id": waypoint_id,
        "preferred_manipulation_waypoint_id": waypoint_id,
        "public_fixture_source": "runtime_map_prior_snapshot",
        "actionability": actionability,
    }


def _materialized_waypoints_from_runtime_map(
    runtime_metric_map: dict[str, Any],
) -> list[dict[str, Any]]:
    anchors = runtime_metric_map.get("public_semantic_anchors") or []
    waypoints: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in anchors:
        if not isinstance(anchor, dict):
            continue
        waypoint_id = str(anchor.get("waypoint_id") or "")
        if not waypoint_id or waypoint_id in seen:
            continue
        pose = _pose_dict(anchor.get("pose") or {})
        waypoints.append(
            {
                "waypoint_id": waypoint_id,
                "frame_id": "map",
                **pose,
                "anchor_id": str(anchor.get("anchor_id") or ""),
                "anchor_type": str(anchor.get("anchor_type") or ""),
                "label": str(anchor.get("label") or waypoint_id),
                "waypoint_source": "runtime_metric_map_public_semantic_anchor",
                "actionability": _anchor_actionability(anchor),
            }
        )
        seen.add(waypoint_id)
    for waypoint in runtime_metric_map.get("generated_exploration_candidates") or []:
        if not isinstance(waypoint, dict):
            continue
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if waypoint_id and waypoint_id not in seen:
            item = copy.deepcopy(waypoint)
            item.setdefault("actionability", "actionable")
            waypoints.append(item)
            seen.add(waypoint_id)
    return waypoints


def _materialized_fixtures_from_runtime_map(
    runtime_metric_map: dict[str, Any],
) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for anchor in runtime_metric_map.get("public_semantic_anchors") or []:
        if not isinstance(anchor, dict):
            continue
        anchor_type = str(anchor.get("anchor_type") or "")
        affordances = [str(item) for item in anchor.get("affordances") or []]
        if anchor_type not in {"fixture", "surface", "receptacle"}:
            continue
        if not {"place", "place_inside", "open", "close"}.intersection(affordances):
            continue
        anchor_id = str(anchor.get("anchor_id") or "")
        if not anchor_id:
            continue
        fixtures.append(
            {
                "enabled": True,
                "fixture_id": anchor_id,
                "receptacle_id": anchor_id,
                "anchor_id": anchor_id,
                "category": str(anchor.get("category") or anchor_type),
                "name": str(anchor.get("label") or anchor_id),
                "room_id": str(anchor.get("room_id") or ""),
                "affordances": affordances,
                "preferred_inspection_waypoint_id": str(anchor.get("waypoint_id") or ""),
                "preferred_manipulation_waypoint_id": str(anchor.get("waypoint_id") or ""),
                "public_fixture_source": "runtime_metric_map_public_semantic_anchor",
                "actionability": _anchor_actionability(anchor),
            }
        )
    return fixtures


def _snapshot_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    anchors = snapshot.get("public_semantic_anchors") or []
    fixtures = snapshot.get("fixture_candidates") or []
    waypoints = snapshot.get("inspection_waypoints") or []
    movable_priors = [
        item
        for item in snapshot.get("runtime_metric_map", {}).get("observed_objects", [])
        if isinstance(item, dict) and item.get("freshness") == "prior"
    ]
    return {
        "anchor_count": len(anchors),
        "inspection_waypoint_count": len(waypoints),
        "fixture_candidate_count": len(fixtures),
        "actionable_anchor_count": sum(
            1 for item in anchors if item.get("actionability") in ACTIONABLE_ANCHOR_STATUSES
        ),
        "movable_prior_count": len(movable_priors),
    }


def _navigation_memory_items(payload: dict[str, Any]) -> list[Any]:
    if isinstance(payload.get("items"), list):
        return list(payload["items"])
    catalog = payload.get("catalog") if isinstance(payload.get("catalog"), dict) else {}
    memory = catalog.get("navigation_memory")
    return list(memory) if isinstance(memory, list) else []


def _anchor_type(item: dict[str, Any]) -> str:
    kind = str(item.get("kind") or "").lower()
    item_id = str(item.get("id") or "").lower()
    label = str(item.get("label") or "").lower()
    text = " ".join(
        [kind, item_id, label, " ".join(str(a).lower() for a in item.get("aliases") or [])]
    )
    if kind in {"room", "area"} or "center" in item_id:
        return "room_area"
    if kind in {"plastic_bottle", "bottle"} or any(term in text for term in ("bottle", "水瓶")):
        return "movable_object"
    if kind in {"sink"} or any(
        term in text for term in ("sink", "fridge", "refrigerator", "水槽", "冰箱")
    ):
        return "receptacle"
    if kind in {"surface", "table", "sofa"} or any(
        term in text for term in ("table", "desk", "sofa", "counter", "茶几", "桌", "沙发")
    ):
        return "surface"
    if _confidence(item) < 0.65:
        return "landmark"
    return "fixture"


def _category(item: dict[str, Any], *, anchor_type: str) -> str:
    kind = str(item.get("kind") or "").strip()
    if kind:
        return kind
    if anchor_type == "room_area":
        return "room_area"
    return anchor_type


def _room_label(item: dict[str, Any], *, anchor_type: str) -> str:
    if anchor_type == "room_area":
        return str(item.get("label") or item.get("id") or "room area")
    explicit = str(item.get("room_label") or item.get("room_area") or "").strip()
    if explicit:
        return explicit
    room_id = _room_id(item, anchor_type=anchor_type)
    return room_id.replace("_", " ")


def _room_id(item: dict[str, Any], *, anchor_type: str) -> str:
    if anchor_type == "room_area":
        return _safe_id(str(item.get("id") or "room_area"))
    text = " ".join(
        [
            str(item.get("id") or "").lower(),
            str(item.get("label") or "").lower(),
            " ".join(str(a).lower() for a in item.get("aliases") or []),
        ]
    )
    if any(term in text for term in ("sink", "fridge", "kitchen", "水槽", "冰箱", "厨房")):
        return "kitchen_area"
    if any(
        term in text for term in ("sofa", "coffee", "monitor", "decor", "茶几", "沙发", "显示器")
    ):
        return "living_area"
    return "agibot_map_area"


def _rooms_from_anchors(anchors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rooms: list[dict[str, Any]] = []
    seen: set[str] = set()
    for anchor in anchors:
        if str(anchor.get("anchor_type") or "") != "room_area":
            continue
        room_id = str(anchor.get("room_id") or "")
        if not room_id or room_id in seen:
            continue
        pose = dict(anchor.get("pose") or {})
        room_label = str(
            anchor.get("room_label") or anchor.get("label") or room_id.replace("_", " ")
        )
        rooms.append(
            normalize_spatial_room(
                {
                    "room_id": room_id,
                    "room_label": room_label,
                    "category": _room_category_from_label(room_label, room_id),
                    "map_center": {
                        "x": float(pose.get("x") or 0.0),
                        "y": float(pose.get("y") or 0.0),
                    },
                    "polygon": [],
                    "source_anchor_id": str(anchor.get("anchor_id") or ""),
                    "public_room_source": "agibot_navigation_memory_room_area",
                },
                frame_id=str(anchor.get("frame_id") or "map"),
                polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
                geometry_source=GEOMETRY_SOURCE_RUNTIME_OBSERVATION,
                alignment_status=ALIGNMENT_STATUS_CANDIDATE,
            )
        )
        seen.add(room_id)
    return rooms


def _room_category_hints_from_rooms(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    hints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id.replace("_", " "))
        if not room_id:
            continue
        hints.append(
            {
                "anchor_type": "room_area",
                "category": str(
                    room.get("category") or _room_category_from_label(room_label, room_id)
                ),
                "label": room_label,
                "room_id": room_id,
                "room_label": room_label,
                "affordances": ["navigate", "observe"],
                "classification_status": "map_prior",
                "confidence": 0.8,
                "aliases": [room_id, room_label],
                "producer_type": "agibot_navigation_memory_conversion",
            }
        )
    return hints


def _driveable_ways(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    return [
        {
            "from_room_id": str(previous.get("room_id") or ""),
            "to_room_id": str(current.get("room_id") or ""),
        }
        for previous, current in zip(rooms, rooms[1:], strict=False)
        if previous.get("room_id") and current.get("room_id")
    ]


def _room_category_from_label(room_label: str, room_id: str) -> str:
    text = f"{room_label} {room_id}".lower()
    if any(term in text for term in ("kitchen", "dining", "bar", "counter", "厨房", "吧台")):
        return "kitchen"
    if any(term in text for term in ("living", "sofa", "lounge", "客厅", "沙发")):
        return "living_room"
    if any(term in text for term in ("storage", "store", "utility", "储藏", "库房")):
        return "storage_room"
    if any(term in text for term in ("meeting", "conference", "会议")):
        return "meeting_room"
    if any(term in text for term in ("bed", "卧室")):
        return "bedroom"
    if any(term in text for term in ("bath", "toilet", "卫生间")):
        return "bathroom"
    return "room_area"


def _affordances(item: dict[str, Any], *, anchor_type: str) -> list[str]:
    if anchor_type == "movable_object":
        return ["observe"]
    if anchor_type == "room_area":
        return ["navigate", "observe"]
    if anchor_type == "landmark":
        return ["navigate", "observe"]
    text = " ".join(
        [
            str(item.get("id") or "").lower(),
            str(item.get("label") or "").lower(),
            str(item.get("kind") or "").lower(),
            " ".join(str(a).lower() for a in item.get("aliases") or []),
        ]
    )
    affordances = ["navigate", "observe", "place"]
    if any(term in text for term in ("fridge", "refrigerator", "冰箱")):
        affordances.extend(["open", "place_inside", "close"])
    elif any(term in text for term in ("sink", "水槽", "hamper", "bin", "cabinet")):
        affordances.append("place_inside")
    return list(dict.fromkeys(affordances))


def _classification_status(item: dict[str, Any], *, anchor_type: str) -> str:
    if anchor_type == "landmark" or _confidence(item) < 0.65:
        return "needs_review"
    return "classified"


def _actionability(anchor_type: str, reachability_status: str, classification_status: str) -> str:
    if anchor_type in MOVABLE_ANCHOR_TYPES:
        return "needs_confirm"
    if classification_status == "needs_review":
        return "needs_review"
    if reachability_status == "reachable":
        return "actionable"
    if reachability_status == "costmap_disagrees":
        return "costmap_disagrees"
    return "observe_only"


def _promotion_status(anchor_type: str, actionability: str) -> str:
    if anchor_type in MOVABLE_ANCHOR_TYPES:
        return "movable_prior_needs_current_run_confirmation"
    if actionability == "actionable":
        return "materialized_static_anchor"
    return actionability


def _reachability_status(pose: dict[str, Any], *, grid: OccupancyGrid) -> dict[str, Any]:
    if "x" not in pose or "y" not in pose:
        return {"status": "projected", "cell": None, "costmap_value": None}
    x = float(pose["x"])
    y = float(pose["y"])
    col, row = world_to_grid(x, y, grid)
    if not grid.in_bounds(col, row):
        return {"status": "costmap_disagrees", "cell": [col, row], "costmap_value": None}
    value = grid.rows[row][col]
    return {
        "status": "reachable" if grid.is_free_cell(col, row) else "costmap_disagrees",
        "cell": [col, row],
        "costmap_value": value,
    }


def _anchor_actionability(anchor: dict[str, Any]) -> str:
    explicit = str(anchor.get("actionability") or "")
    if explicit:
        return explicit
    if str(anchor.get("freshness") or "") == "prior" and str(anchor.get("anchor_type") or "") in (
        "object",
        "movable_object",
    ):
        return "needs_confirm"
    if str(anchor.get("promotion_status") or "") in {"needs_review", "observe_only"}:
        return str(anchor.get("promotion_status"))
    return "actionable"


def _pose_dict(raw: dict[str, Any]) -> dict[str, float]:
    pose: dict[str, float] = {}
    for key in ("x", "y", "yaw"):
        pose[key] = _float(raw.get(key))
    return pose


def _float(value: Any) -> float:
    try:
        return round(float(value or 0.0), 6)
    except (TypeError, ValueError):
        return 0.0


def _confidence(item: dict[str, Any]) -> float:
    try:
        return round(float(item.get("confidence") or 0.0), 6)
    except (TypeError, ValueError):
        return 0.0


def _selected_frame(anchor: dict[str, Any]) -> str:
    evidence = anchor.get("evidence") if isinstance(anchor.get("evidence"), dict) else {}
    raw_evidence = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else {}
    return str(raw_evidence.get("selected_frame") or raw_evidence.get("grounding_artifact") or "")


def _source_navigation_map_reference(source: dict[str, Any]) -> dict[str, Any]:
    if not source:
        return {
            "schema": "source_navigation_map_reference_v1",
            "source_type": "runtime_metric_map_static_map",
        }
    return {
        "schema": "source_navigation_map_reference_v1",
        "source_type": "minimal_navigation_map_artifact",
        "map_id": str(source.get("map_id") or source.get("environment_id") or ""),
        "map_frame": str(source.get("frame_id") or "map"),
        "source_schema": str(source.get("schema") or ""),
        "source_map_mutated": False,
    }


def _source_hashes(*paths: Path) -> dict[str, str]:
    hashes = {}
    for path in paths:
        if path.is_file():
            hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def _artifact_paths(map_dir: Path) -> dict[str, str]:
    result = {
        "navigation_memory": "navigation_memory.json",
        "nav2_yaml": "agibot/nav2.yaml",
        "occupancy_grid": "agibot/occupancy.pgm",
        "source": "agibot/source.json",
    }
    if (map_dir / "agibot" / "raw_map.json.gz").is_file():
        result["raw_map"] = "agibot/raw_map.json.gz"
    return result


def _map_id(map_dir: Path, source: dict[str, Any]) -> str:
    return str(source.get("alias") or source.get("requested_map_id") or map_dir.name)


def _yaw(map_yaml: dict[str, Any]) -> float:
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    try:
        return round(float(origin[2]), 6)
    except (IndexError, TypeError, ValueError):
        return 0.0


def _safe_id(value: str) -> str:
    result = "".join(ch.lower() if ch.isalnum() else "_" for ch in value.strip())
    while "__" in result:
        result = result.replace("__", "_")
    return result.strip("_") or "anchor"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{_safe_id(value)}"


def _require_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(path)


def _assert_no_private_truth(value: Any) -> None:
    hits = sorted(_find_private_keys(value))
    if hits:
        raise ValueError(f"private truth keys present in runtime map prior snapshot: {hits}")


def _find_private_keys(value: Any) -> set[str]:
    hits: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key) in PRIVATE_TRUTH_KEYS:
                hits.add(str(key))
            hits.update(_find_private_keys(item))
    elif isinstance(value, list):
        for item in value:
            hits.update(_find_private_keys(item))
    return hits

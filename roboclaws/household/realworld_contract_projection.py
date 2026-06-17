from __future__ import annotations

from collections import defaultdict
from typing import Any

from roboclaws.household import realworld_contract_fixture_projection
from roboclaws.household.types import CleanupScenario
from roboclaws.maps.spatial_contract import (
    ALIGNMENT_STATUS_NATIVE,
    GEOMETRY_SOURCE_GENERATED_CANDIDATE,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    POLYGON_ROLE_NAVIGATION_AREA,
    normalize_spatial_room,
)

_PROJECTION_FORBIDDEN_AGENT_VIEW_KEYS = frozenset(
    {
        "generated_mess_set",
        "generated_mess_count",
        "environment_setup",
        "relocation_policy",
        "relocation_count",
        "relocated_object_ids",
        "relocated_objects",
        "before_relocation_positions",
        "after_relocation_positions",
        "target_count",
        "acceptable_destination_sets",
        "valid_receptacle_ids",
        "private_manifest",
        "is_misplaced",
        "global_movable_object_inventory",
        "target_receptacle_id",
    }
)

_OBJECT_CATEGORY_TARGETS = realworld_contract_fixture_projection._OBJECT_CATEGORY_TARGETS
_INSIDE_DESTINATION_CATEGORY_TERMS = (
    realworld_contract_fixture_projection._INSIDE_DESTINATION_CATEGORY_TERMS
)
_anchor_affordances_for_fixture = (
    realworld_contract_fixture_projection._anchor_affordances_for_fixture
)
_driveable_ways = realworld_contract_fixture_projection._driveable_ways
_first_fixture_for_waypoint = realworld_contract_fixture_projection._first_fixture_for_waypoint
_first_matching_fixture = realworld_contract_fixture_projection._first_matching_fixture
_fixture_affordances = realworld_contract_fixture_projection._fixture_affordances
_fixture_footprint = realworld_contract_fixture_projection._fixture_footprint
_fixture_is_open_container = realworld_contract_fixture_projection._fixture_is_open_container
_fixture_navigation_obstacles = realworld_contract_fixture_projection._fixture_navigation_obstacles
_fixture_prefers_inside = realworld_contract_fixture_projection._fixture_prefers_inside
_fixture_requires_open = realworld_contract_fixture_projection._fixture_requires_open
_fixture_text = realworld_contract_fixture_projection._fixture_text
_inspection_waypoints = realworld_contract_fixture_projection._inspection_waypoints
_is_place_anchor = realworld_contract_fixture_projection._is_place_anchor
_normalize_fixture_category_label = (
    realworld_contract_fixture_projection._normalize_fixture_category_label
)
_point_overlaps_fixture_obstacle = (
    realworld_contract_fixture_projection._point_overlaps_fixture_obstacle
)
_polygon_center_world = realworld_contract_fixture_projection._polygon_center_world
_polygon_from_room_outline = realworld_contract_fixture_projection._polygon_from_room_outline
_public_destination_policy_for_category = (
    realworld_contract_fixture_projection._public_destination_policy_for_category
)
_public_destination_policy_tool_for_fixture_category = (
    realworld_contract_fixture_projection._public_destination_policy_tool_for_fixture_category
)
_recommended_place_tool = realworld_contract_fixture_projection._recommended_place_tool
_room_id = realworld_contract_fixture_projection._room_id
_room_outline_by_id_from_fixtures = (
    realworld_contract_fixture_projection._room_outline_by_id_from_fixtures
)
_room_outline_center = realworld_contract_fixture_projection._room_outline_center
_room_outline_metadata = realworld_contract_fixture_projection._room_outline_metadata
_room_polygon_bounds = realworld_contract_fixture_projection._room_polygon_bounds
_rooms_from_fixtures = realworld_contract_fixture_projection._rooms_from_fixtures
_scene_outline_waypoint_candidates = (
    realworld_contract_fixture_projection._scene_outline_waypoint_candidates
)
_scene_outline_waypoint_slots_for_room = (
    realworld_contract_fixture_projection._scene_outline_waypoint_slots_for_room
)
_semantic_anchor_type_for_fixture = (
    realworld_contract_fixture_projection._semantic_anchor_type_for_fixture
)
_split_fixture_groups = realworld_contract_fixture_projection._split_fixture_groups
_vec3 = realworld_contract_fixture_projection._vec3
_waypoint_slots_for_room = realworld_contract_fixture_projection._waypoint_slots_for_room


def _map_bundle_fields_present(metric_map: dict[str, Any]) -> bool:
    required = {
        "schema",
        "frame_id",
        "map_id",
        "map_version",
        "resolution_m",
        "origin",
        "width",
        "height",
        "occupancy_values",
        "map_bundle",
        "robot_pose",
        "inspection_waypoints",
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    required = {
        "waypoint_id",
        "frame_id",
        "x",
        "y",
        "yaw",
        "room_id",
        "label",
        "visited",
        "purpose",
    }
    return bool(waypoints) and all(required <= set(item) for item in waypoints)


def _fixtures_from_bundle_fixture_hints(
    fixture_hints: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id)
        for raw_fixture in room.get("fixtures") or []:
            if not isinstance(raw_fixture, dict):
                continue
            fixture = dict(raw_fixture)
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if not fixture_id:
                continue
            fixture.setdefault("fixture_id", fixture_id)
            fixture.setdefault("receptacle_id", fixture_id)
            fixture.setdefault("room_id", room_id)
            fixture.setdefault("room_area", room_label or room_id)
            fixture.setdefault("kind", "receptacle")
            fixture.setdefault("name", fixture_id)
            fixture.setdefault("category", fixture.get("name", fixture_id))
            fixtures[fixture_id] = fixture
    return fixtures


def _scene_index_public_fixture_overlay(
    *,
    backend: Any,
    scenario: CleanupScenario,
    existing_fixtures: dict[str, dict[str, Any]],
    fallback_waypoint_id: str,
) -> dict[str, dict[str, Any]]:
    if str(getattr(backend, "scenario_source", "")) != "isaac_scene_index":
        return {}

    overlay: dict[str, dict[str, Any]] = {}
    for receptacle in scenario.receptacles:
        fixture_id = str(receptacle.receptacle_id)
        if not fixture_id:
            continue
        fixture = dict(existing_fixtures.get(fixture_id, {}))
        fixture["fixture_id"] = fixture_id
        fixture["receptacle_id"] = fixture_id
        fixture["category"] = str(
            receptacle.category or fixture.get("category") or receptacle.name or fixture_id
        )
        fixture["name"] = str(receptacle.name or fixture.get("name") or fixture_id)
        fixture.setdefault("kind", receptacle.kind)
        fixture.setdefault("room_area", receptacle.room_area)
        fixture.setdefault("room_id", _room_id(str(receptacle.room_area)))
        fixture.setdefault("preferred_inspection_waypoint_id", fallback_waypoint_id)
        fixture.setdefault("preferred_manipulation_waypoint_id", fallback_waypoint_id)
        fixture["public_fixture_source"] = "isaac_scene_index"
        overlay[fixture_id] = fixture
    return overlay


def _metric_map_room_payload(room: dict[str, Any]) -> dict[str, Any]:
    payload = normalize_spatial_room(
        {
            "room_id": room["room_id"],
            "room_label": room["room_label"],
            "fixture_count": len(room["fixture_ids"]),
            "polygon": room.get("polygon", []),
        },
        frame_id="map",
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        alignment_status=ALIGNMENT_STATUS_NATIVE,
    )
    if isinstance(room.get("scene_room_outline"), dict):
        payload["scene_room_outline"] = dict(room["scene_room_outline"])
    return payload


def _public_room_hints_from_metric_map(
    metric_map: dict[str, Any],
    *,
    fallback_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_rooms = [item for item in metric_map.get("rooms") or [] if isinstance(item, dict)] or [
        item for item in fallback_rooms if isinstance(item, dict)
    ]
    rooms: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_room in source_rooms:
        room = _public_room_hint_payload(raw_room)
        room_id = str(room.get("room_id") or "")
        if not room_id or room_id in seen:
            continue
        rooms.append(room)
        seen.add(room_id)
    return rooms


def _public_room_hint_payload(room: dict[str, Any]) -> dict[str, Any]:
    room_id = str(room.get("room_id") or _room_id(str(room.get("room_label") or "room_area")))
    room_label = str(room.get("room_label") or room_id.replace("_", " "))
    polygon = [dict(point) for point in room.get("polygon") or [] if isinstance(point, dict)]
    map_center = (
        dict(room.get("map_center") or {})
        if isinstance(room.get("map_center"), dict)
        else _polygon_center_world(polygon)
    )
    payload: dict[str, Any] = {
        "room_id": room_id,
        "room_label": room_label,
        "category": str(room.get("category") or _room_category_from_label(room_label, room_id)),
        "polygon": polygon,
        "map_center": map_center,
        "public_room_source": "base_navigation_map",
    }
    payload = normalize_spatial_room(
        payload,
        frame_id=str(room.get("source_map_frame_id") or "map"),
        polygon_role=POLYGON_ROLE_NAVIGATION_AREA,
        geometry_source=str(room.get("geometry_source") or GEOMETRY_SOURCE_GENERATED_CANDIDATE),
        alignment_status=str(room.get("alignment_status") or ALIGNMENT_STATUS_NATIVE),
    )
    if isinstance(room.get("scene_room_outline"), dict):
        payload["scene_room_outline"] = dict(room["scene_room_outline"])
    return payload


def _room_category_hints_from_public_rooms(
    rooms: list[dict[str, Any]],
    waypoints: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    waypoint_by_room: dict[str, str] = {}
    for waypoint in waypoints:
        room_id = str(waypoint.get("room_id") or "")
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        if room_id and waypoint_id:
            waypoint_by_room.setdefault(room_id, waypoint_id)
    hints = []
    for room in rooms:
        room_id = str(room.get("room_id") or "")
        room_label = str(room.get("room_label") or room_id.replace("_", " "))
        if not room_id:
            continue
        hint = {
            "anchor_type": "room_area",
            "category": str(room.get("category") or _room_category_from_label(room_label, room_id)),
            "label": room_label,
            "room_id": room_id,
            "room_label": room_label,
            "waypoint_id": waypoint_by_room.get(room_id, ""),
            "affordances": ["navigate", "observe"],
            "classification_status": "map_prior",
            "confidence": 0.8,
            "aliases": [room_id, room_label],
            "producer_type": "base_navigation_map",
        }
        _assert_no_forbidden_agent_view_keys(hint)
        hints.append(hint)
    return hints


def _merge_public_rooms(
    base_rooms: list[dict[str, Any]],
    prior_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for raw_room in [*base_rooms, *prior_rooms]:
        if not isinstance(raw_room, dict):
            continue
        room = _public_room_hint_payload(raw_room)
        room_id = str(room.get("room_id") or "")
        if not room_id or room_id in seen:
            continue
        merged.append(room)
        seen.add(room_id)
    return merged


def _public_driveable_ways(
    metric_map: dict[str, Any],
    rooms: list[dict[str, Any]],
) -> list[dict[str, str]]:
    public_room_ids = {str(room.get("room_id") or "") for room in rooms}
    ways = []
    for way in metric_map.get("driveable_ways") or []:
        if not isinstance(way, dict):
            continue
        start = str(way.get("from_room_id") or "")
        goal = str(way.get("to_room_id") or "")
        if start in public_room_ids and goal in public_room_ids:
            ways.append({"from_room_id": start, "to_room_id": goal})
    if ways:
        return ways
    return _driveable_ways(rooms)


def _room_label_by_id(rooms: list[dict[str, Any]]) -> dict[str, str]:
    return {
        str(room.get("room_id") or ""): str(room.get("room_label") or "")
        for room in rooms
        if str(room.get("room_id") or "")
    }


def _room_category_from_label(room_label: str, room_id: str = "") -> str:
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


def _scene_room_outlines_from_backend(backend: Any) -> list[dict[str, Any]]:
    if str(getattr(backend, "scenario_source", "")) != "isaac_scene_index":
        return []
    outlines = getattr(backend, "room_outlines", None)
    if outlines is None:
        diagnostics = getattr(backend, "scene_index_diagnostics", {})
        if isinstance(diagnostics, dict):
            outlines = diagnostics.get("room_outlines")
    return [
        dict(item)
        for item in (outlines or [])
        if isinstance(item, dict) and item.get("center") and item.get("half_extents")
    ]


def _scene_index_fixture_pose(backend: Any, fixture_id: str) -> list[float] | None:
    receptacle_index = getattr(backend, "receptacle_index", {})
    if not isinstance(receptacle_index, dict):
        return None
    entry = receptacle_index.get(fixture_id)
    if not isinstance(entry, dict):
        return None
    support_pose = entry.get("support_pose")
    if isinstance(support_pose, dict):
        position = support_pose.get("position")
        pose = _vec3(position)
        if pose is not None:
            return pose
    bounds = entry.get("usd_world_bounds")
    if isinstance(bounds, dict):
        pose = _vec3(bounds.get("center"))
        if pose is not None:
            return pose
    return None


def _room_outline_by_id(
    room_outlines: list[dict[str, Any]],
    room_id: str,
) -> dict[str, Any] | None:
    return next((item for item in room_outlines if str(item.get("room_id") or "") == room_id), None)


def _fixture_hints_with_scene_index_overlay(
    rooms: list[Any],
    overlay_fixtures: dict[str, dict[str, Any]],
    *,
    fixture_hint_mode: str,
) -> list[dict[str, Any]]:
    overlay_room = {
        "room_id": "isaac_scene_index",
        "room_label": "Isaac scene index fixtures",
        "fixture_source": "isaac_scene_index",
        "fixtures": [
            _scene_index_fixture_hint_row(fixture_id, fixture, fixture_hint_mode)
            for fixture_id, fixture in sorted(overlay_fixtures.items())
        ],
    }
    return [overlay_room] + [dict(room) for room in rooms if isinstance(room, dict)]


def _scene_index_fixture_hint_row(
    fixture_id: str,
    fixture: dict[str, Any],
    fixture_hint_mode: str,
) -> dict[str, Any]:
    pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
    return {
        "fixture_id": fixture_id,
        "category": str(fixture.get("category") or fixture.get("name") or fixture_id),
        "name": str(fixture.get("name") or fixture_id),
        "room_id": "isaac_scene_index",
        "affordances": _fixture_affordances(fixture),
        "footprint": _fixture_footprint(fixture_id),
        "pose": {
            "frame_id": str(pose.get("frame_id") or "map"),
            "x": float(pose.get("x", 0.0)),
            "y": float(pose.get("y", 0.0)),
            "yaw": float(pose.get("yaw", 0.0)),
        },
        "manipulation_frame": f"{fixture_id}_manipulation",
        "preferred_inspection_waypoint_id": str(
            fixture.get("preferred_inspection_waypoint_id") or ""
        ),
        "preferred_manipulation_waypoint_id": str(
            fixture.get("preferred_manipulation_waypoint_id") or ""
        ),
        "position_detail": fixture_hint_mode,
        "public_fixture_source": "isaac_scene_index",
    }


def _first_waypoint_id(waypoints: list[dict[str, Any]]) -> str:
    if not waypoints:
        return ""
    return str(waypoints[0].get("waypoint_id") or "")


def _rooms_from_bundle_projection(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[dict[str, Any]]:
    fixture_ids_by_room: dict[str, list[str]] = defaultdict(list)
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        room_id = str(room.get("room_id") or "")
        for fixture in room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if fixture_id:
                fixture_ids_by_room[room_id].append(fixture_id)

    rooms = []
    for raw_room in metric_map.get("rooms") or []:
        if not isinstance(raw_room, dict):
            continue
        room = dict(raw_room)
        room_id = str(room.get("room_id") or "")
        room["fixture_ids"] = sorted(fixture_ids_by_room.get(room_id, []))
        room.setdefault("room_label", room_id.replace("_", " "))
        room.setdefault("map_center", _polygon_center_world(room.get("polygon") or []))
        rooms.append(room)
    return rooms


def _inspection_waypoints_from_bundle_projection(
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
) -> list[dict[str, Any]]:
    fixture_waypoint_ids, room_fixture_ids = _bundle_fixture_projection_indexes(fixture_hints)
    waypoints = []
    frame_id = str(metric_map.get("frame_id") or "map")
    for raw_waypoint in metric_map.get("inspection_waypoints") or []:
        if not isinstance(raw_waypoint, dict):
            continue
        waypoints.append(
            _bundle_inspection_waypoint(
                raw_waypoint=raw_waypoint,
                frame_id=frame_id,
                fixture_waypoint_ids=fixture_waypoint_ids,
                room_fixture_ids=room_fixture_ids,
            )
        )
    return waypoints


def _bundle_fixture_projection_indexes(
    fixture_hints: dict[str, Any],
) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
    fixture_waypoint_ids: dict[str, list[str]] = defaultdict(list)
    room_fixture_ids: dict[str, list[str]] = defaultdict(list)
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        _add_bundle_room_fixture_indexes(
            room=room,
            fixture_waypoint_ids=fixture_waypoint_ids,
            room_fixture_ids=room_fixture_ids,
        )
    return fixture_waypoint_ids, room_fixture_ids


def _add_bundle_room_fixture_indexes(
    *,
    room: dict[str, Any],
    fixture_waypoint_ids: dict[str, list[str]],
    room_fixture_ids: dict[str, list[str]],
) -> None:
    room_id = str(room.get("room_id") or "")
    for fixture in room.get("fixtures") or []:
        if not isinstance(fixture, dict):
            continue
        fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
        if not fixture_id:
            continue
        room_fixture_ids[room_id].append(fixture_id)
        for key in ("preferred_inspection_waypoint_id", "preferred_manipulation_waypoint_id"):
            waypoint_id = str(fixture.get(key) or "")
            if waypoint_id and fixture_id not in fixture_waypoint_ids[waypoint_id]:
                fixture_waypoint_ids[waypoint_id].append(fixture_id)


def _bundle_inspection_waypoint(
    *,
    raw_waypoint: dict[str, Any],
    frame_id: str,
    fixture_waypoint_ids: dict[str, list[str]],
    room_fixture_ids: dict[str, list[str]],
) -> dict[str, Any]:
    waypoint = dict(raw_waypoint)
    waypoint_id = str(waypoint.get("waypoint_id") or "")
    room_id = str(waypoint.get("room_id") or "")
    waypoint.setdefault("frame_id", frame_id)
    waypoint["visited"] = False
    if not waypoint.get("fixture_ids"):
        waypoint["fixture_ids"] = sorted(
            fixture_waypoint_ids.get(waypoint_id) or room_fixture_ids.get(room_id, [])
        )
    return waypoint


def _minimal_generated_exploration_waypoints(
    metric_map: dict[str, Any],
    *,
    fallback_waypoints: list[dict[str, Any]],
    public_rooms: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    source_waypoints = [
        item for item in metric_map.get("inspection_waypoints") or [] if isinstance(item, dict)
    ] or [item for item in fallback_waypoints if isinstance(item, dict)]
    frame_id = str(metric_map.get("frame_id") or "map")
    room_labels = _room_label_by_id(public_rooms)
    generated = []
    for index, source in enumerate(source_waypoints, start=1):
        waypoint_id = f"generated_exploration_{index:03d}"
        room_id = str(source.get("room_id") or "generated_area")
        room_label = str(room_labels.get(room_id) or source.get("room_label") or "")
        generated.append(
            {
                "waypoint_id": waypoint_id,
                "frame_id": frame_id,
                "x": float(source.get("x", 0.0)),
                "y": float(source.get("y", 0.0)),
                "yaw": float(source.get("yaw", 0.0)),
                "room_id": room_id,
                "room_label": room_label,
                "label": f"Generated exploration candidate {index}",
                "purpose": "minimal_map_exploration",
                "waypoint_source": "generated_exploration_candidate",
                "coverage_estimate": round(1.0 / max(len(source_waypoints), 1), 6),
                "candidate_provenance": {
                    "source": "public_occupancy_free_space",
                    "candidate_index": index,
                    "source_pose": "free_space_sample",
                    "source_room_hidden": False,
                    "source_room_label_available": bool(room_label),
                    "source_fixtures_hidden": True,
                    "source_waypoint_hidden": True,
                },
            }
        )
    return generated


def _private_waypoint_map_for_generated_candidates(
    generated_waypoints: list[dict[str, Any]],
    private_waypoints: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    result = {}
    for generated, private in zip(generated_waypoints, private_waypoints, strict=False):
        result[str(generated.get("waypoint_id") or "")] = private
    return result


def _assert_no_forbidden_agent_view_keys(payload: Any) -> None:
    if isinstance(payload, dict):
        forbidden = _PROJECTION_FORBIDDEN_AGENT_VIEW_KEYS.intersection(payload)
        if forbidden:
            raise AssertionError(f"forbidden agent-view keys present: {sorted(forbidden)}")
        for value in payload.values():
            _assert_no_forbidden_agent_view_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_agent_view_keys(value)

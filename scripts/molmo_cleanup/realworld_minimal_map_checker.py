from __future__ import annotations

from typing import Any

from roboclaws.household.realworld_contract import forbidden_agent_view_keys


def assert_minimal_map(data: dict[str, Any], agent_view: dict[str, Any]) -> None:
    assert data.get("map_mode") == "minimal", data
    metric_map = agent_view.get("metric_map") or {}
    static_fixture_projection = agent_view.get("static_fixture_projection") or {}
    runtime_map = data.get("runtime_metric_map") or agent_view.get("runtime_metric_map") or {}
    static_map = runtime_map.get("static_map") or {}
    _assert_minimal_core(metric_map, static_fixture_projection, runtime_map)
    _assert_minimal_rooms_and_static_map(metric_map, static_fixture_projection, static_map)
    _assert_minimal_waypoints(metric_map, runtime_map)
    semantic_sweep = data.get("semantic_sweep")
    if semantic_sweep is not None:
        assert semantic_sweep.get("minimal_map_mode") is True, data
    _assert_no_forbidden_keys(metric_map)
    _assert_no_forbidden_keys(static_fixture_projection)


def _assert_minimal_core(
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    runtime_map: dict[str, Any],
) -> None:
    assert metric_map.get("mode") == "minimal", metric_map
    assert static_fixture_projection.get("mode") == "minimal", static_fixture_projection
    assert runtime_map.get("map_mode") == "minimal", runtime_map
    assert runtime_map.get("minimal_map_mode") is True, runtime_map


def _assert_minimal_rooms_and_static_map(
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    static_map: dict[str, Any],
) -> None:
    rooms = metric_map.get("rooms") or []
    driveable_ways = metric_map.get("driveable_ways") or []
    room_category_hints = metric_map.get("room_category_hints") or []
    assert isinstance(rooms, list), metric_map
    assert all(isinstance(room, dict) and room.get("room_label") for room in rooms), rooms
    assert isinstance(driveable_ways, list), metric_map
    assert isinstance(room_category_hints, list), metric_map
    assert all(
        isinstance(hint, dict) and hint.get("anchor_type") == "room_area"
        for hint in room_category_hints
    ), room_category_hints
    assert static_fixture_projection.get("rooms") == [], static_fixture_projection
    _assert_static_map(static_map)


def _assert_static_map(static_map: dict[str, Any]) -> None:
    static_rooms = static_map.get("rooms") or []
    static_driveable_ways = static_map.get("driveable_ways") or []
    assert isinstance(static_rooms, list), static_map
    assert all(isinstance(room, dict) and room.get("room_label") for room in static_rooms), (
        static_rooms
    )
    assert static_map.get("fixtures") == [], static_map
    assert isinstance(static_driveable_ways, list), static_map


def _assert_minimal_waypoints(
    metric_map: dict[str, Any],
    runtime_map: dict[str, Any],
) -> None:
    waypoints = metric_map.get("inspection_waypoints") or []
    assert waypoints, metric_map
    generated = runtime_map.get("generated_exploration_candidates") or []
    generated_target_inspection = runtime_map.get("generated_target_inspection_candidates") or []
    exploration_waypoints = _waypoints_by_source(waypoints, "generated_exploration_candidate")
    target_inspection_waypoints = _waypoints_by_source(
        waypoints,
        "generated_target_inspection_candidate",
    )
    assert len(generated) == len(exploration_waypoints), runtime_map
    assert len(generated_target_inspection) == len(target_inspection_waypoints), runtime_map
    _assert_public_anchors(runtime_map)
    for waypoint in exploration_waypoints:
        _assert_exploration_waypoint(waypoint)
    for waypoint in target_inspection_waypoints:
        _assert_target_inspection_waypoint(waypoint)


def _waypoints_by_source(waypoints: list[dict[str, Any]], source: str) -> list[dict[str, Any]]:
    return [item for item in waypoints if item.get("waypoint_source") == source]


def _assert_public_anchors(runtime_map: dict[str, Any]) -> None:
    anchors = runtime_map.get("public_semantic_anchors") or []
    assert anchors, runtime_map
    assert any(item.get("anchor_type") == "observation_waypoint" for item in anchors), anchors


def _assert_exploration_waypoint(waypoint: dict[str, Any]) -> None:
    assert str(waypoint.get("waypoint_id") or "").startswith("generated_"), waypoint
    assert waypoint.get("waypoint_source") == "generated_exploration_candidate", waypoint
    assert waypoint.get("purpose") == "minimal_map_exploration", waypoint
    provenance = waypoint.get("candidate_provenance") or {}
    assert provenance.get("source") == "public_occupancy_free_space", waypoint
    assert provenance.get("source_room_hidden") is False, waypoint
    assert provenance.get("source_room_label_available") is bool(waypoint.get("room_label")), (
        waypoint
    )
    assert provenance.get("source_fixtures_hidden") is True, waypoint
    assert provenance.get("source_waypoint_hidden") is True, waypoint
    assert "source_waypoint_id" not in provenance, waypoint


def _assert_target_inspection_waypoint(waypoint: dict[str, Any]) -> None:
    assert str(waypoint.get("waypoint_id") or "").startswith("generated_inspection_"), waypoint
    assert waypoint.get("purpose") == "target_inspection", waypoint
    assert waypoint.get("verified_navigation") is True, waypoint
    assert waypoint.get("source_observation_id"), waypoint
    assert waypoint.get("source_target_candidate_id"), waypoint
    provenance = waypoint.get("candidate_provenance") or {}
    assert provenance.get("source") == "server_verified_standoff_from_visible_evidence", waypoint
    assert provenance.get("source_waypoint_id"), waypoint
    assert provenance.get("source_observation_id"), waypoint


def _assert_no_forbidden_keys(payload: Any) -> None:
    if isinstance(payload, dict):
        forbidden = forbidden_agent_view_keys().intersection(payload)
        assert not forbidden, (sorted(forbidden), payload)
        for value in payload.values():
            _assert_no_forbidden_keys(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_no_forbidden_keys(value)

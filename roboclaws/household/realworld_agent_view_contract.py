from __future__ import annotations

import math
from collections.abc import Callable
from typing import Any


def forbidden_agent_view_keys(forbidden_keys: frozenset[str]) -> set[str]:
    return set(forbidden_keys)


def cleanup_policy_trace_from_events(
    trace_events: list[dict[str, Any]],
    agent_view: dict[str, Any],
    *,
    builder: Callable[..., dict[str, Any]],
    schema: str,
) -> dict[str, Any]:
    return builder(
        trace_events,
        agent_view,
        schema=schema,
    )


def real_robot_readiness_from_events(
    *,
    agent_view: dict[str, Any],
    trace_events: list[dict[str, Any]],
    robot_view_steps: list[dict[str, Any]],
    schema: str,
    api_semantic_provenance: str,
    sim_costmap_planner: str,
    map_bundle_fields_present: Callable[[dict[str, Any]], bool],
    pose_stamped_waypoints_present: Callable[[dict[str, Any]], bool],
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    metric_map = agent_view.get("metric_map") or {}
    static_fixture_projection = agent_view.get("static_fixture_projection") or {}
    policy_view = agent_view.get("policy_view") or {}
    navigation_backends: dict[str, int] = {}
    pose_sources: dict[str, int] = {}
    for raw in trace_events:
        if raw.get("event") != "response":
            continue
        response = raw.get("response") if isinstance(raw.get("response"), dict) else {}
        backend = response.get("navigation_backend")
        if backend:
            navigation_backends[str(backend)] = navigation_backends.get(str(backend), 0) + 1
        pose_source = response.get("pose_source")
        if pose_source:
            pose_sources[str(pose_source)] = pose_sources.get(str(pose_source), 0) + 1
    report_only_count = sum(
        1 for step in robot_view_steps if (step.get("views") or {}).get("chase")
    )
    evidence = {
        "schema": schema,
        "status": "simulation_semantic_not_real_robot_ready",
        "real_robot_ready": False,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": map_bundle_fields_present(metric_map),
        "pose_stamped_waypoints": pose_stamped_waypoints_present(metric_map),
        "static_fixture_projection": (
            static_fixture_projection.get("schema") == "static_fixture_projection_v1"
            and static_fixture_projection.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": policy_view.get("chase_camera_policy_input") is False,
        "report_only_simulation_view_count": report_only_count,
        "report_only_simulation_view_label": "report_only_simulation_view",
        "navigation_backend_summary": navigation_backends,
        "pose_source_summary": pose_sources,
        "semantic_navigation_only": set(navigation_backends)
        <= {
            api_semantic_provenance,
            sim_costmap_planner,
        },
        "sim_costmap_route_validation": navigation_backends.get(sim_costmap_planner, 0) > 0,
        "physical_navigation_pilot": False,
        "physical_cleanup_ready": False,
        "blocked_capabilities": [
            "physical_navigation_backend",
            "live_ros_graph",
            "planner_backed_cleanup_primitives",
        ],
        "public_contract_note": (
            "This artifact aligns data boundaries with a real robot contract, but "
            "semantic simulator navigation remains labelled api_semantic."
        ),
    }
    evidence["readiness_sections_complete"] = bool(
        evidence["map_bundle_fields_present"]
        and evidence["pose_stamped_waypoints"]
        and evidence["static_fixture_projection"]
        and evidence["policy_view_chase_excluded"]
        and navigation_backends
    )
    assert_no_forbidden_agent_view_keys(evidence)
    return evidence


def assert_no_forbidden_agent_view_keys(payload: Any, forbidden_keys: frozenset[str]) -> None:
    if isinstance(payload, dict):
        forbidden = forbidden_keys.intersection(payload)
        if forbidden:
            raise AssertionError(f"forbidden agent-view keys present: {sorted(forbidden)}")
        for value in payload.values():
            assert_no_forbidden_agent_view_keys(value, forbidden_keys)
    elif isinstance(payload, list):
        for value in payload:
            assert_no_forbidden_agent_view_keys(value, forbidden_keys)


def strip_forbidden_agent_view_keys(payload: Any, forbidden_keys: frozenset[str]) -> Any:
    if isinstance(payload, dict):
        return {
            key: strip_forbidden_agent_view_keys(value, forbidden_keys)
            for key, value in payload.items()
            if key not in forbidden_keys
        }
    if isinstance(payload, list):
        return [strip_forbidden_agent_view_keys(value, forbidden_keys) for value in payload]
    return payload


def public_acceptance_config(
    config: dict[str, Any] | None,
    *,
    normalize_household_intent: Callable[[Any], str],
    assert_no_forbidden_agent_view_keys: Callable[[Any], None],
) -> dict[str, Any]:
    source = dict(config or {})
    accepted: dict[str, Any] = {}
    for key in (
        "requested_run_size",
        "required_grounded_cleanup_chains",
        "required_model_declared_observations",
    ):
        value = positive_int(source.get(key))
        if value is not None:
            accepted[key] = value
    policy = str(source.get("done_readiness_policy") or "").strip()
    if policy:
        accepted["done_readiness_policy"] = policy
    task_intent = str(source.get("task_intent") or "").strip()
    if task_intent:
        accepted["task_intent"] = normalize_household_intent(task_intent)
    assert_no_forbidden_agent_view_keys(accepted)
    return accepted


def public_success_threshold(count: int | None) -> int:
    if count is None or count <= 0:
        return 0
    return max(1, math.ceil(count * 0.70))


def positive_int(value: Any) -> int | None:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if result > 0 else None


def nonnegative_int(value: Any) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        return 0
    return max(0, result)

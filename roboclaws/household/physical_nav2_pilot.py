from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Protocol

from roboclaws.household.nav2_adapter import (
    BLOCKED_CAPABILITY_PROVENANCE,
    NAV2_ACTION_PROVENANCE,
    DirectNav2Adapter,
)
from roboclaws.household.profiles import (
    PHYSICAL_ROBOT_EVIDENCE_LANE,
    physical_robot_evidence_metadata,
)
from roboclaws.household.realworld_contract import REALWORLD_CONTRACT
from roboclaws.household.report import render_cleanup_report, write_state_snapshot
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.types import CleanupScenario
from roboclaws.maps.bundle import copy_nav2_map_bundle_snapshot, validate_nav2_map_bundle
from roboclaws.maps.project import fixture_hints_from_bundle, metric_map_from_bundle

PHYSICAL_NAV2_PILOT_SCHEMA = "physical_nav2_cleanup_pilot_v1"
PHYSICAL_NAV2_PILOT_POLICY = "physical_nav2_navigation_perception_pilot"
BLOCKED_MANIPULATION_TOOLS = (
    "pick",
    "place",
    "place_inside",
    "open_receptacle",
    "close_receptacle",
)


class PhysicalObservationProvider(Protocol):
    def observe(
        self,
        *,
        waypoint: dict[str, Any],
        navigation_result: dict[str, Any],
    ) -> dict[str, Any]:
        """Return public camera-derived perception for a reached waypoint."""


class CameraLabelObservationProvider:
    """Default first-pilot observer: public camera labels, no private cleanup truth."""

    def __init__(self) -> None:
        self._count = 0

    def observe(
        self,
        *,
        waypoint: dict[str, Any],
        navigation_result: dict[str, Any],
    ) -> dict[str, Any]:
        self._count += 1
        waypoint_id = str(waypoint.get("waypoint_id") or navigation_result.get("waypoint_id") or "")
        room_id = str(waypoint.get("room_id") or "")
        fixture_ids = [str(item) for item in waypoint.get("fixture_ids") or []]
        return {
            "ok": True,
            "tool": "observe",
            "status": "ok",
            "contract": REALWORLD_CONTRACT,
            "observation_id": f"physical_observe_{self._count:03d}",
            "waypoint_id": waypoint_id,
            "current_room_id": room_id,
            "observation_role": "physical_navigation_perception_check",
            "perception_mode": "camera_labels",
            "perception_source": "camera_derived_labels",
            "structured_detections_available": True,
            "visible_object_detections": [],
            "camera_labels": [
                {
                    "label": "static_fixture_view",
                    "fixture_ids": fixture_ids,
                    "confidence": 0.5,
                    "source": "physical_camera_label_provider",
                }
            ],
            "source_navigation_backend": navigation_result.get("navigation_backend", ""),
            "private_target_truth_included": False,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
        }


def run_physical_nav2_cleanup_pilot(
    *,
    run_dir: Path,
    map_bundle_dir: Path,
    adapter: DirectNav2Adapter,
    observer: PhysicalObservationProvider | None = None,
    robot_profile_id: str = "rby1m",
    scenario: CleanupScenario | None = None,
    backend_name: str = "nav2_action",
) -> dict[str, Any]:
    """Run the first hardware Navigation + Perception Pilot contract path.

    The caller owns the concrete Nav2 client behind ``adapter``. CI can pass a
    mock client while a local robot run can pass a ROS-backed client with the
    same protocol.
    """

    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    pilot_inputs = _load_physical_nav2_pilot_inputs(
        run_dir=run_dir,
        map_bundle_dir=map_bundle_dir,
        observer=observer,
        robot_profile_id=robot_profile_id,
        scenario=scenario,
    )
    nav2_map_bundle = pilot_inputs["nav2_map_bundle"]
    metric_map = pilot_inputs["metric_map"]
    fixture_hints = pilot_inputs["fixture_hints"]
    observer = pilot_inputs["observer"]
    scenario = pilot_inputs["scenario"]

    before_snapshot = write_state_snapshot(
        scenario,
        _initial_locations(scenario),
        run_dir / "before.png",
        title="Before physical Nav2 pilot",
    )
    after_snapshot = write_state_snapshot(
        scenario,
        _initial_locations(scenario),
        run_dir / "after.png",
        title="After physical Nav2 pilot",
    )

    started_at = time.time()
    trace_events: list[dict[str, Any]] = []
    policy_events: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    inspection_attempts: list[dict[str, Any]] = []
    fixture_attempts: list[dict[str, Any]] = []
    manipulation_results: list[dict[str, Any]] = []
    current_pose = dict(metric_map.get("robot_pose") or {})
    waypoints_by_id = {
        str(item.get("waypoint_id") or ""): dict(item)
        for item in metric_map.get("inspection_waypoints") or []
    }

    _record(trace_events, started_at, "metric_map", {}, metric_map)
    _record(trace_events, started_at, "fixture_hints", {}, fixture_hints)

    current_pose = _run_physical_inspection_sweep(
        adapter=adapter,
        observer=observer,
        metric_map=metric_map,
        current_pose=current_pose,
        trace_events=trace_events,
        policy_events=policy_events,
        observations=observations,
        inspection_attempts=inspection_attempts,
        started_at=started_at,
    )
    _run_physical_fixture_sweep(
        adapter=adapter,
        observer=observer,
        fixture_hints=fixture_hints,
        waypoints_by_id=waypoints_by_id,
        current_pose=current_pose,
        trace_events=trace_events,
        policy_events=policy_events,
        observations=observations,
        fixture_attempts=fixture_attempts,
        started_at=started_at,
    )
    _record_blocked_manipulation_tools(
        adapter=adapter,
        started_at=started_at,
        trace_events=trace_events,
        policy_events=policy_events,
        manipulation_results=manipulation_results,
    )

    trace_path = run_dir / "trace.jsonl"
    trace_path.write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in trace_events),
        encoding="utf-8",
    )

    readiness = _readiness_payload(
        metric_map=metric_map,
        fixture_hints=fixture_hints,
        inspection_attempts=inspection_attempts,
        fixture_attempts=fixture_attempts,
        observations=observations,
        manipulation_results=manipulation_results,
    )
    readiness["map_bundle_snapshot_present"] = bool(nav2_map_bundle.get("snapshot_complete"))
    readiness["robot_profile_id"] = robot_profile_id
    run_result = {
        "schema": PHYSICAL_NAV2_PILOT_SCHEMA,
        "contract": REALWORLD_CONTRACT,
        "evidence_lane": PHYSICAL_ROBOT_EVIDENCE_LANE,
        "evidence_lane_metadata": physical_robot_evidence_metadata(backend=backend_name),
        "backend": backend_name,
        "policy": PHYSICAL_NAV2_PILOT_POLICY,
        "agent_driven": False,
        "mcp_server": "none",
        "cleanup_status": readiness["status"],
        "primitive_provenance": _dominant_primitive_provenance(
            inspection_attempts + fixture_attempts
        ),
        "generated_mess_count": 0,
        "requested_generated_mess_count": 0,
        "sweep_coverage_rate": readiness["observed_reached_waypoint_rate"],
        "disturbance_count": 0,
        "score": _empty_score(),
        "private_evaluation": {
            "generated_mess_count": 0,
            "generated_mess_set": [],
            "acceptable_destination_sets": {},
            "mess_restoration_rate": 0.0,
            "sweep_coverage_rate": readiness["observed_reached_waypoint_rate"],
            "disturbance_count": 0,
            "public_contract_note": "Physical pilot does not run private cleanup scoring.",
        },
        "agent_view": {
            "metric_map": metric_map,
            "fixture_hints": fixture_hints,
            "observed_objects": [],
            "raw_fpv_observations": [],
            "perception_mode": "camera_labels",
            "structured_detections_available": True,
            "policy_view": {"chase_camera_policy_input": False},
            "cleanup_worklist": {"schema": "cleanup_worklist_v1", "objects": []},
            "forbidden_private_fields_absent": True,
        },
        "cleanup_policy_trace": {
            "schema": "cleanup_policy_trace_v1",
            "waypoint_source": "prebuilt_nav2_map_bundle",
            "loop_style": "physical_navigation_perception_pilot",
            "total_waypoints": len(metric_map.get("inspection_waypoints") or []),
            "observed_waypoint_count": len(
                {str(item.get("waypoint_id") or "") for item in observations}
            ),
            "scan_observe_count": len(observations),
            "cleanup_action_count": 0,
            "placed_object_count": 0,
            "post_place_observe_count": 0,
            "post_place_observe_complete": True,
            "first_cleanup_before_full_survey": False,
            "events": policy_events,
            "public_contract_note": (
                "Physical pilot attempts public map waypoints and fixture preferred waypoints; "
                "cleanup manipulation remains blocked."
            ),
        },
        "real_robot_readiness": readiness,
        "nav2_map_bundle": nav2_map_bundle,
        "physical_nav2_pilot": {
            "schema": PHYSICAL_NAV2_PILOT_SCHEMA,
            "inspection_attempts": inspection_attempts,
            "fixture_preferred_waypoint_attempts": fixture_attempts,
            "observations": observations,
            "blocked_manipulation_results": manipulation_results,
        },
        "manipulation_evidence": {
            "schema": "physical_manipulation_block_v1",
            "status": "blocked_capability",
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "planner_backed": False,
            "strict_proof_eligible": False,
            "api_semantic_state_edits": 0,
            "evidence_note": ("First physical pilot intentionally blocks pick/place/open/close."),
            "blockers": [str(item["tool"]) for item in manipulation_results],
            "strict_proof_requirements": [
                "planner-backed manipulation binding",
                "operator safety approval",
                "hardware pick/place validation",
            ],
        },
        "artifacts": {
            "run_result": "run_result.json",
            "trace": "trace.jsonl",
            "report": "report.html",
            "map_bundle": "map_bundle",
        },
        "runtime_timing": {
            "total_elapsed_s": time.time() - started_at,
            "tool_handler_s": 0.0,
            "robot_view_capture_s": 0.0,
            "between_tool_gap_s": 0.0,
            "tool_call_count": len(trace_events) // 2,
        },
    }
    run_result_path = run_dir / "run_result.json"
    run_result_path.write_text(
        json.dumps(run_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    render_cleanup_report(
        run_dir=run_dir,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        robot_view_steps=[],
    )
    return run_result


def _load_physical_nav2_pilot_inputs(
    *,
    run_dir: Path,
    map_bundle_dir: Path,
    observer: PhysicalObservationProvider | None,
    robot_profile_id: str,
    scenario: CleanupScenario | None,
) -> dict[str, Any]:
    source_bundle_dir = Path(map_bundle_dir)
    validation = validate_nav2_map_bundle(source_bundle_dir)
    validation.raise_for_errors()
    nav2_map_bundle = copy_nav2_map_bundle_snapshot(
        source_bundle_dir=source_bundle_dir,
        run_dir=run_dir,
    )
    bundle_dir = run_dir / "map_bundle"
    robot_profile_path = bundle_dir / "profiles" / f"{robot_profile_id}.yaml"
    if not robot_profile_path.is_file():
        raise FileNotFoundError(
            f"robot profile {robot_profile_id!r} is missing from {bundle_dir / 'profiles'}"
        )
    return {
        "nav2_map_bundle": nav2_map_bundle,
        "metric_map": metric_map_from_bundle(bundle_dir),
        "fixture_hints": fixture_hints_from_bundle(bundle_dir),
        "observer": observer or CameraLabelObservationProvider(),
        "scenario": scenario or build_cleanup_scenario(seed=7),
    }


def _run_physical_inspection_sweep(
    *,
    adapter: DirectNav2Adapter,
    observer: PhysicalObservationProvider,
    metric_map: dict[str, Any],
    current_pose: dict[str, Any],
    trace_events: list[dict[str, Any]],
    policy_events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    inspection_attempts: list[dict[str, Any]],
    started_at: float,
) -> dict[str, Any]:
    for waypoint in metric_map.get("inspection_waypoints") or []:
        waypoint_id = str(waypoint.get("waypoint_id") or "")
        navigation = adapter.navigate_to_waypoint(
            waypoint_id=waypoint_id,
            waypoint_pose=waypoint,
            current_pose=current_pose,
            goal_source="inspection_waypoint",
        )
        inspection_attempts.append(dict(navigation))
        policy_events.append(_policy_event(len(policy_events), navigation, "inspection_waypoint"))
        _record(
            trace_events,
            started_at,
            "navigate_to_waypoint",
            {"waypoint_id": waypoint_id},
            navigation,
        )
        if navigation.get("ok"):
            current_pose = dict(navigation.get("current_pose") or current_pose)
            observation = observer.observe(waypoint=waypoint, navigation_result=navigation)
            observations.append(observation)
            policy_events.append(
                _policy_event(len(policy_events), observation, "reached_waypoint_observe")
            )
            _record(trace_events, started_at, "observe", {"waypoint_id": waypoint_id}, observation)
    return current_pose


def _run_physical_fixture_sweep(
    *,
    adapter: DirectNav2Adapter,
    observer: PhysicalObservationProvider,
    fixture_hints: dict[str, Any],
    waypoints_by_id: dict[str, dict[str, Any]],
    current_pose: dict[str, Any],
    trace_events: list[dict[str, Any]],
    policy_events: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    fixture_attempts: list[dict[str, Any]],
    started_at: float,
) -> None:
    for fixture in _fixtures(fixture_hints):
        fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
        navigation = adapter.navigate_to_fixture_preferred_waypoint(
            fixture_id=fixture_id,
            fixture=fixture,
            waypoints_by_id=waypoints_by_id,
            current_pose=current_pose,
        )
        fixture_attempts.append(dict(navigation))
        policy_events.append(
            _policy_event(len(policy_events), navigation, "fixture_preferred_waypoint")
        )
        _record(
            trace_events,
            started_at,
            "navigate_to_receptacle",
            {"fixture_id": fixture_id},
            navigation,
        )
        waypoint = waypoints_by_id.get(str(navigation.get("preferred_waypoint_id") or ""))
        if navigation.get("ok") and waypoint is not None:
            current_pose = dict(navigation.get("current_pose") or current_pose)
            observation = observer.observe(waypoint=waypoint, navigation_result=navigation)
            observations.append(observation)
            policy_events.append(
                _policy_event(len(policy_events), observation, "reached_fixture_observe")
            )
            _record(trace_events, started_at, "observe", {"fixture_id": fixture_id}, observation)


def _record_blocked_manipulation_tools(
    *,
    adapter: DirectNav2Adapter,
    started_at: float,
    trace_events: list[dict[str, Any]],
    policy_events: list[dict[str, Any]],
    manipulation_results: list[dict[str, Any]],
) -> None:
    for tool in BLOCKED_MANIPULATION_TOOLS:
        result = adapter.blocked_manipulation(tool=tool)
        manipulation_results.append(result)
        policy_events.append(_policy_event(len(policy_events), result, "blocked_manipulation"))
        _record(trace_events, started_at, tool, {}, result)


def _fixtures(fixture_hints: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    seen: set[str] = set()
    for room in fixture_hints.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            if not isinstance(fixture, dict):
                continue
            fixture_id = str(fixture.get("fixture_id") or fixture.get("receptacle_id") or "")
            if not fixture_id or fixture_id in seen:
                continue
            item = dict(fixture)
            item.setdefault("fixture_id", fixture_id)
            fixtures.append(item)
            seen.add(fixture_id)
    return fixtures


def _readiness_payload(
    *,
    metric_map: dict[str, Any],
    fixture_hints: dict[str, Any],
    inspection_attempts: list[dict[str, Any]],
    fixture_attempts: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    manipulation_results: list[dict[str, Any]],
) -> dict[str, Any]:
    navigation_attempts = inspection_attempts + fixture_attempts
    navigation_backends = _count_values(navigation_attempts, "navigation_backend")
    pose_sources = _count_values(navigation_attempts, "pose_source")
    reached = [item for item in navigation_attempts if item.get("ok")]
    observed_waypoints = {str(item.get("waypoint_id") or "") for item in observations}
    all_manipulation_blocked = all(
        item.get("primitive_provenance") == BLOCKED_CAPABILITY_PROVENANCE
        and item.get("physical_cleanup_ready") is False
        for item in manipulation_results
    )
    observed_reached_rate = len(observations) / len(reached) if reached else 0.0
    complete = bool(
        inspection_attempts
        and len(fixture_attempts) == len(_fixtures(fixture_hints))
        and all(item.get("ok") for item in navigation_attempts)
        and len(observations) >= len(reached)
        and all_manipulation_blocked
    )
    return {
        "schema": "real_robot_readiness_v1",
        "status": "physical_navigation_pilot_complete"
        if complete
        else "physical_navigation_pilot_incomplete",
        "real_robot_ready": False,
        "navigation_perception_ready": complete,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": _map_bundle_fields_present(metric_map),
        "pose_stamped_waypoints": _pose_stamped_waypoints_present(metric_map),
        "static_fixture_semantic_map": (
            fixture_hints.get("schema") == "static_fixture_semantic_map_v1"
            and fixture_hints.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": True,
        "report_only_simulation_view_count": 0,
        "report_only_simulation_view_label": "not_simulated",
        "navigation_backend_summary": navigation_backends,
        "pose_source_summary": pose_sources,
        "semantic_navigation_only": False,
        "sim_costmap_route_validation": False,
        "physical_navigation_pilot": True,
        "physical_cleanup_ready": False,
        "inspection_waypoint_attempt_count": len(inspection_attempts),
        "inspection_waypoint_total": len(metric_map.get("inspection_waypoints") or []),
        "fixture_preferred_waypoint_attempt_count": len(fixture_attempts),
        "fixture_total": len(_fixtures(fixture_hints)),
        "reached_waypoint_count": len(reached),
        "observed_reached_waypoint_count": len(observations),
        "observed_reached_waypoint_rate": observed_reached_rate,
        "observed_waypoint_ids": sorted(observed_waypoints),
        "manipulation_blocked": all_manipulation_blocked,
        "blocked_capabilities": list(BLOCKED_MANIPULATION_TOOLS),
        "public_contract_note": (
            "Physical navigation/perception pilot: Nav2 waypoint attempts are allowed, "
            "but physical cleanup manipulation remains blocked."
        ),
    }


def _record(
    trace_events: list[dict[str, Any]],
    started_at: float,
    tool: str,
    arguments: dict[str, Any],
    response: dict[str, Any],
) -> None:
    elapsed = time.time() - started_at
    trace_events.append(
        {
            "tool": tool,
            "event": "request",
            "arguments": arguments,
            "wallclock_elapsed": elapsed,
        }
    )
    trace_events.append(
        {
            "tool": tool,
            "event": "response",
            "response": response,
            "wallclock_elapsed": time.time() - started_at,
        }
    )


def _policy_event(index: int, response: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "index": index + 1,
        "tool": response.get("tool", ""),
        "role": role,
        "waypoint_id": response.get("waypoint_id") or response.get("preferred_waypoint_id") or "",
        "fixture_id": response.get("fixture_id", ""),
        "navigation_backend": response.get("navigation_backend", ""),
        "status": response.get("status") or response.get("navigation_status", ""),
    }


def _map_bundle_fields_present(metric_map: dict[str, Any]) -> bool:
    required = {
        "schema",
        "frame_id",
        "resolution_m",
        "origin",
        "width",
        "height",
        "rooms",
        "driveable_ways",
        "inspection_waypoints",
        "map_bundle",
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    return bool(waypoints) and all(
        {"frame_id", "x", "y", "yaw", "waypoint_id"} <= set(item) for item in waypoints
    )


def _count_values(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = item.get(key)
        if value:
            counts[str(value)] = counts.get(str(value), 0) + 1
    return counts


def _dominant_primitive_provenance(items: list[dict[str, Any]]) -> str:
    if any(item.get("primitive_provenance") == NAV2_ACTION_PROVENANCE for item in items):
        return NAV2_ACTION_PROVENANCE
    return BLOCKED_CAPABILITY_PROVENANCE


def _empty_score() -> dict[str, Any]:
    return {
        "restored_count": 0,
        "total_targets": 0,
        "object_results": [],
        "semantic_acceptability": {
            "accepted_count": 0,
            "total_targets": 0,
            "acceptance_rate": 0.0,
        },
    }


def _initial_locations(scenario: CleanupScenario) -> dict[str, str]:
    return {item.object_id: item.location_id for item in scenario.objects}

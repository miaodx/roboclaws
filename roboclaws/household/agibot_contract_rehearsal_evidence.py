from __future__ import annotations

from typing import Any

from roboclaws.household.agibot_sdk_runner import BLOCKED_MANIPULATION_TOOLS
from roboclaws.household.manipulation_provenance import api_semantic_manipulation_evidence
from roboclaws.household.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.household.profiles import MOLMOSPACES_SIM_BACKEND
from roboclaws.household.types import CleanupScenario

EXECUTION_BACKEND = MOLMOSPACES_SIM_BACKEND
NAVIGATION_BACKEND = MOLMOSPACES_SIM_BACKEND
REHEARSAL_MODE_CLEANUP_ACTIONS = "cleanup-actions"


def private_evaluation(
    *,
    scenario: CleanupScenario,
    score: dict[str, Any],
    cleanup_actions_enabled: bool,
) -> dict[str, Any]:
    if not cleanup_actions_enabled:
        return {
            "generated_mess_count": 0,
            "generated_mess_set": [],
            "acceptable_destination_sets": {},
            "mess_restoration_rate": 0.0,
            "sweep_coverage_rate": 0.0,
            "disturbance_count": 0,
            "public_contract_note": ("Contract rehearsal does not run private cleanup scoring."),
        }
    targets = scenario.private_manifest.targets
    return {
        "generated_mess_count": len(targets),
        "generated_mess_set": [target.object_id for target in targets],
        "acceptable_destination_sets": {
            target.object_id: list(target.valid_receptacle_ids) for target in targets
        },
        "mess_restoration_rate": float(score.get("mess_restoration_rate") or 0.0),
        "sweep_coverage_rate": float(score.get("sweep_coverage_rate") or 0.0),
        "disturbance_count": int(score.get("disturbance_count") or 0),
        "completion_status": score.get("completion_status", ""),
        "object_results": list(score.get("object_results") or []),
        "public_contract_note": (
            "Private scoring is report/evaluation evidence only. Cleanup-action "
            "target selection used public observations and static fixture projection."
        ),
    }


def cleanup_action_manipulation_evidence(
    cleanup_primitive_evidence: dict[str, Any],
) -> dict[str, Any]:
    evidence = api_semantic_manipulation_evidence(
        backend=EXECUTION_BACKEND,
        primitive_summary=cleanup_primitive_evidence.get("primitive_provenance_summary", {}),
    )
    evidence["evidence_note"] = (
        "MolmoSpaces Agibot Cleanup Action Rehearsal used api_semantic simulated "
        "state updates for pick/place actions. This is not planner-backed "
        "manipulation proof and not Agibot GDK execution."
    )
    evidence["execution_backend"] = EXECUTION_BACKEND
    evidence["simulated"] = True
    evidence["physical_robot"] = False
    evidence["agibot_gdk_execution"] = False
    return evidence


def blocked_manipulation_evidence(
    manipulation_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema": "molmospaces_agibot_contract_rehearsal_manipulation_block_v1",
        "status": "blocked_capability",
        "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
        "planner_backed": False,
        "strict_proof_eligible": False,
        "api_semantic_state_edits": 0,
        "evidence_note": (
            "MolmoSpaces Agibot Contract Rehearsal intentionally blocks "
            "pick/place/open/close manipulation."
        ),
        "blockers": [str(item["tool"]) for item in manipulation_results],
        "strict_proof_requirements": [
            "planner-backed manipulation binding",
            "real hardware safety approval",
            "Agibot manipulation validation",
        ],
    }


def readiness_payload(
    *,
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    observation: dict[str, Any],
    navigation: dict[str, Any],
    manipulation_results: list[dict[str, Any]],
    runtime: str,
    rehearsal_mode: str,
    cleanup_actions: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
) -> dict[str, Any]:
    cleanup_actions_enabled = rehearsal_mode == REHEARSAL_MODE_CLEANUP_ACTIONS
    all_manipulation_blocked = (
        all(
            item.get("primitive_provenance") == BLOCKED_CAPABILITY_PROVENANCE
            for item in manipulation_results
        )
        if manipulation_results
        else False
    )
    complete = bool(
        observation.get("ok")
        and navigation.get("ok")
        and (
            int(cleanup_actions.get("completed_object_count") or 0) > 0
            if cleanup_actions_enabled
            else all_manipulation_blocked
        )
    )
    return {
        "schema": "real_robot_readiness_v1",
        "status": (
            "molmospaces_agibot_cleanup_action_rehearsal_complete"
            if cleanup_actions_enabled and complete
            else "molmospaces_agibot_contract_rehearsal_complete"
            if complete
            else "molmospaces_agibot_contract_rehearsal_blocked"
        ),
        "real_robot_ready": False,
        "navigation_perception_ready": complete,
        "backend_variant": EXECUTION_BACKEND,
        "rehearsal_mode": rehearsal_mode,
        "runtime": runtime,
        "simulated": True,
        "physical_robot": False,
        "movement_enabled": False,
        "map_bundle_schema": metric_map.get("schema", ""),
        "map_bundle_fields_present": _map_fields_present(metric_map),
        "pose_stamped_waypoints": _pose_stamped_waypoints_present(metric_map),
        "static_fixture_projection": (
            static_fixture_projection.get("schema") == "static_fixture_projection_v1"
            and static_fixture_projection.get("contains_runtime_observations") is False
        ),
        "policy_view_chase_excluded": True,
        "report_only_simulation_view_count": max(1, len(robot_view_steps)),
        "report_only_simulation_view_label": "molmospaces_sim_policy_observation",
        "robot_view_step_count": len(robot_view_steps),
        "navigation_backend_summary": {NAVIGATION_BACKEND: 1},
        "pose_source_summary": {"molmospaces_sim_waypoint_arrival": 1},
        "semantic_navigation_only": False,
        "sim_costmap_route_validation": True,
        "physical_navigation_pilot": False,
        "physical_cleanup_ready": False,
        "inspection_waypoint_attempt_count": max(
            1,
            int(cleanup_actions.get("navigation_attempt_count") or 0),
        ),
        "inspection_waypoint_total": len(metric_map.get("inspection_waypoints") or []),
        "fixture_preferred_waypoint_attempt_count": 0,
        "fixture_total": len(_fixtures(static_fixture_projection)),
        "reached_waypoint_count": max(
            1 if navigation.get("ok") else 0,
            int(cleanup_actions.get("navigation_attempt_count") or 0),
        ),
        "observed_reached_waypoint_count": max(
            1 if observation.get("ok") else 0,
            int(cleanup_actions.get("observation_count") or 0),
        ),
        "observed_reached_waypoint_rate": 1.0 if complete else 0.0,
        "observed_waypoint_ids": [str(navigation.get("waypoint_id") or "")]
        if observation.get("ok")
        else [],
        "manipulation_blocked": all_manipulation_blocked,
        "blocked_capabilities": list(BLOCKED_MANIPULATION_TOOLS),
        "cleanup_action_attempted_object_count": int(
            cleanup_actions.get("attempted_object_count") or 0
        ),
        "cleanup_action_completed_object_count": int(
            cleanup_actions.get("completed_object_count") or 0
        ),
        "operator_run_enablement_gate": {
            "movement_enabled": False,
            "scope": "not_applicable_simulated_contract_rehearsal",
        },
        "public_contract_note": (
            "MolmoSpaces Agibot Contract Rehearsal validates public contract shape "
            "and Agibot-shaped evidence plumbing. It is simulated and is not real "
            "Agibot GDK execution."
        ),
    }


def _map_fields_present(metric_map: dict[str, Any]) -> bool:
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
    }
    return required <= set(metric_map)


def _pose_stamped_waypoints_present(metric_map: dict[str, Any]) -> bool:
    waypoints = metric_map.get("inspection_waypoints") or []
    return bool(waypoints) and all(
        {"x", "y", "yaw", "waypoint_id"} <= set(item) for item in waypoints
    )


def _fixtures(static_fixture_projection: dict[str, Any]) -> list[dict[str, Any]]:
    fixtures: list[dict[str, Any]] = []
    for room in static_fixture_projection.get("rooms") or []:
        for fixture in room.get("fixtures") or []:
            if isinstance(fixture, dict):
                fixtures.append(fixture)
    return fixtures

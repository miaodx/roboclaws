from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    DETERMINISTIC_SWEEP_POLICY,
    MINIMAL_MAP_MODE,
    RealWorldCleanupContract,
)
from roboclaws.household.skill_scratchpad import empty_skill_scratchpad

SEMANTIC_SWEEP_POLICY = "semantic_sweep_baseline"
SEMANTIC_SWEEP_CAMERA_SCHEDULE: tuple[dict[str, float], ...] = (
    {"yaw_delta_deg": 0.0, "pitch_delta_deg": 0.0},
    {"yaw_delta_deg": -30.0, "pitch_delta_deg": 0.0},
    {"yaw_delta_deg": 60.0, "pitch_delta_deg": 0.0},
)

ToolCaller = Callable[..., dict[str, Any]]
ObservationPostprocessor = Callable[..., dict[str, Any]]


@dataclass(frozen=True)
class DirectCleanupLoopHooks:
    call_tool: ToolCaller
    attach_raw_fpv_robot_view: ObservationPostprocessor
    view_index_after_raw_fpv: Callable[[list[dict[str, Any]], int], int]
    detections_for_policy: Callable[..., list[dict[str, Any]]]
    maybe_clean_visible_object: Callable[..., int]
    semantic_sweep_done: Callable[..., dict[str, Any]]
    failed_score: Callable[[RealWorldCleanupContract], dict[str, Any]]


def record_direct_cleanup_robot_view(
    *,
    base_contract: CleanupBackendSession,
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    label_suffix: str,
    action: str,
) -> int:
    if not record_robot_views:
        return view_index
    return base_contract.record_robot_view_step(
        steps=robot_view_steps,
        output_dir=output_dir,
        index=view_index,
        label_suffix=label_suffix,
        action=action,
    )


def direct_cleanup_policy_name(*, semantic_sweep: bool, perception_mode: str) -> str:
    if semantic_sweep:
        return SEMANTIC_SWEEP_POLICY
    if perception_mode == CAMERA_MODEL_POLICY_MODE:
        return CAMERA_MODEL_POLICY_NAME
    return DETERMINISTIC_SWEEP_POLICY


def direct_cleanup_scratchpad(policy_name: str) -> dict[str, Any]:
    scratchpad = empty_skill_scratchpad(
        note="Deterministic direct demo scratchpad; cleanup_worklist is authoritative."
    )
    scratchpad["policy"] = policy_name
    return scratchpad


def run_direct_cleanup_scan(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    metric_map: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    semantic_sweep: bool,
    map_mode: str,
    perception_mode: str,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    hooks: DirectCleanupLoopHooks,
) -> int:
    handled_handles: set[str] = set()
    pending_minimal_detections: dict[str, dict[str, Any]] = {}
    for waypoint in metric_map["inspection_waypoints"]:
        view_index = _scan_direct_cleanup_waypoint(
            trace_events=trace_events,
            started_at=started_at,
            contract=contract,
            base_contract=base_contract,
            waypoint=waypoint,
            static_fixture_projection=static_fixture_projection,
            robot_view_steps=robot_view_steps,
            output_dir=output_dir,
            view_index=view_index,
            record_robot_views=record_robot_views,
            semantic_sweep=semantic_sweep,
            map_mode=map_mode,
            perception_mode=perception_mode,
            planner_proof_evidence=planner_proof_evidence,
            agent_scratchpad=agent_scratchpad,
            handled_handles=handled_handles,
            pending_minimal_detections=pending_minimal_detections,
            hooks=hooks,
        )
    if not semantic_sweep and map_mode == MINIMAL_MAP_MODE:
        return _clean_pending_minimal_detections(
            trace_events=trace_events,
            started_at=started_at,
            contract=contract,
            base_contract=base_contract,
            static_fixture_projection=static_fixture_projection,
            robot_view_steps=robot_view_steps,
            output_dir=output_dir,
            view_index=view_index,
            record_robot_views=record_robot_views,
            planner_proof_evidence=planner_proof_evidence,
            agent_scratchpad=agent_scratchpad,
            handled_handles=handled_handles,
            pending_minimal_detections=pending_minimal_detections,
            perception_mode=perception_mode,
            hooks=hooks,
        )
    return view_index


def _scan_direct_cleanup_waypoint(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    waypoint: dict[str, Any],
    static_fixture_projection: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    semantic_sweep: bool,
    map_mode: str,
    perception_mode: str,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    handled_handles: set[str],
    pending_minimal_detections: dict[str, dict[str, Any]],
    hooks: DirectCleanupLoopHooks,
) -> int:
    waypoint_id = str(waypoint["waypoint_id"])
    hooks.call_tool(
        trace_events,
        started_at,
        "navigate_to_waypoint",
        {"waypoint_id": waypoint_id},
        lambda selected=waypoint_id: contract.navigate_to_waypoint(selected),
    )
    detections, view_index = _observe_direct_cleanup_waypoint(
        trace_events=trace_events,
        started_at=started_at,
        contract=contract,
        base_contract=base_contract,
        robot_view_steps=robot_view_steps,
        output_dir=output_dir,
        view_index=view_index,
        record_robot_views=record_robot_views,
        semantic_sweep=semantic_sweep,
        perception_mode=perception_mode,
        hooks=hooks,
    )
    if semantic_sweep:
        return view_index
    return _handle_direct_cleanup_detections(
        trace_events=trace_events,
        started_at=started_at,
        contract=contract,
        base_contract=base_contract,
        detections=detections,
        static_fixture_projection=static_fixture_projection,
        robot_view_steps=robot_view_steps,
        output_dir=output_dir,
        view_index=view_index,
        record_robot_views=record_robot_views,
        map_mode=map_mode,
        planner_proof_evidence=planner_proof_evidence,
        agent_scratchpad=agent_scratchpad,
        handled_handles=handled_handles,
        pending_minimal_detections=pending_minimal_detections,
        perception_mode=perception_mode,
        hooks=hooks,
    )


def _observe_direct_cleanup_waypoint(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    semantic_sweep: bool,
    perception_mode: str,
    hooks: DirectCleanupLoopHooks,
) -> tuple[list[dict[str, Any]], int]:
    detections = []
    for camera_index, camera_step in enumerate(_camera_schedule_for_direct_scan(semantic_sweep)):
        if semantic_sweep and camera_index > 0:
            hooks.call_tool(
                trace_events,
                started_at,
                "adjust_camera",
                dict(camera_step),
                lambda step=camera_step: contract.adjust_camera(**step),
            )
        observation = hooks.call_tool(
            trace_events,
            started_at,
            "observe",
            {},
            contract.observe,
            postprocess=lambda response: hooks.attach_raw_fpv_robot_view(
                response=response,
                contract=contract,
                base_contract=base_contract,
                robot_view_steps=robot_view_steps,
                output_dir=output_dir,
                view_index_ref=[view_index],
                record_robot_views=record_robot_views,
            ),
        )
        view_index = hooks.view_index_after_raw_fpv(robot_view_steps, view_index)
        detections.extend(
            hooks.detections_for_policy(
                trace_events=trace_events,
                started_at=started_at,
                contract=contract,
                observation=observation,
                perception_mode=perception_mode,
            )
        )
    return detections, view_index


def _camera_schedule_for_direct_scan(semantic_sweep: bool) -> tuple[dict[str, float], ...]:
    if semantic_sweep:
        return SEMANTIC_SWEEP_CAMERA_SCHEDULE
    return ({"yaw_delta_deg": 0.0, "pitch_delta_deg": 0.0},)


def _handle_direct_cleanup_detections(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    detections: list[dict[str, Any]],
    static_fixture_projection: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    map_mode: str,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    handled_handles: set[str],
    pending_minimal_detections: dict[str, dict[str, Any]],
    perception_mode: str,
    hooks: DirectCleanupLoopHooks,
) -> int:
    if map_mode == MINIMAL_MAP_MODE:
        for detection in detections:
            pending_minimal_detections[str(detection["object_id"])] = dict(detection)
        return view_index
    return _clean_direct_cleanup_detections(
        trace_events=trace_events,
        started_at=started_at,
        contract=contract,
        base_contract=base_contract,
        detections=detections,
        static_fixture_projection=static_fixture_projection,
        robot_view_steps=robot_view_steps,
        output_dir=output_dir,
        view_index=view_index,
        record_robot_views=record_robot_views,
        planner_proof_evidence=planner_proof_evidence,
        agent_scratchpad=agent_scratchpad,
        handled_handles=handled_handles,
        perception_mode=perception_mode,
        hooks=hooks,
    )


def _clean_direct_cleanup_detections(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    detections: list[dict[str, Any]],
    static_fixture_projection: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    handled_handles: set[str],
    perception_mode: str,
    hooks: DirectCleanupLoopHooks,
) -> int:
    for detection in detections:
        view_index = hooks.maybe_clean_visible_object(
            trace_events=trace_events,
            started_at=started_at,
            contract=contract,
            base_contract=base_contract,
            detection=detection,
            static_fixture_projection=static_fixture_projection,
            robot_view_steps=robot_view_steps,
            output_dir=output_dir,
            view_index=view_index,
            record_robot_views=record_robot_views,
            planner_proof_evidence=planner_proof_evidence,
            agent_scratchpad=agent_scratchpad,
            handled_handles=handled_handles,
            perception_mode=perception_mode,
        )
    return view_index


def _clean_pending_minimal_detections(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    static_fixture_projection: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    handled_handles: set[str],
    pending_minimal_detections: dict[str, dict[str, Any]],
    perception_mode: str,
    hooks: DirectCleanupLoopHooks,
) -> int:
    return _clean_direct_cleanup_detections(
        trace_events=trace_events,
        started_at=started_at,
        contract=contract,
        base_contract=base_contract,
        detections=list(pending_minimal_detections.values()),
        static_fixture_projection=static_fixture_projection,
        robot_view_steps=robot_view_steps,
        output_dir=output_dir,
        view_index=view_index,
        record_robot_views=record_robot_views,
        planner_proof_evidence=planner_proof_evidence,
        agent_scratchpad=agent_scratchpad,
        handled_handles=handled_handles,
        perception_mode=perception_mode,
        hooks=hooks,
    )


def complete_direct_cleanup(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    policy_name: str,
    semantic_sweep: bool,
    hooks: DirectCleanupLoopHooks,
) -> dict[str, Any]:
    reason = f"{policy_name} complete"
    done = hooks.call_tool(
        trace_events,
        started_at,
        "done",
        {"reason": reason},
        lambda: (
            hooks.semantic_sweep_done(contract, base_contract, reason)
            if semantic_sweep
            else contract.done(reason)
        ),
    )
    if "score" in done:
        return done
    return _done_with_failed_score(
        contract=contract,
        base_contract=base_contract,
        done=done,
        reason=f"{policy_name} incomplete",
        hooks=hooks,
    )


def _done_with_failed_score(
    *,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    done: dict[str, Any],
    reason: str,
    hooks: DirectCleanupLoopHooks,
) -> dict[str, Any]:
    base_done = base_contract.done(reason=reason)
    score = dict(base_done.get("score") or {})
    final_locations = base_contract.final_locations(base_done.get("final_locations"))
    if score:
        metrics = contract._realworld_metrics(score, final_locations)  # noqa: SLF001
        score.update(metrics)
    else:
        score = hooks.failed_score(contract)
    return {
        **done,
        "cleanup_status": "failed",
        "score": score,
        "final_locations": final_locations,
        "final_containment": base_done.get("final_containment", {}),
        "tool_event_counts": base_done.get("tool_event_counts", {}),
    }

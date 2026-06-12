#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any

from roboclaws.household.advisory_scoring import build_advisory_evaluation
from roboclaws.household.backend import API_SEMANTIC_PROVENANCE
from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.cleanup_primitive_evidence import (
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.household.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
    IsaacLabSubprocessBackend,
)
from roboclaws.household.manipulation_provenance import (
    api_semantic_manipulation_evidence,
    isaac_semantic_pose_manipulation_evidence,
    planner_backed_cleanup_manipulation_evidence,
)
from roboclaws.household.nav2_map_bundle import (
    attach_nav2_map_bundle_snapshot,
    selected_nav2_map_bundle_dir,
)
from roboclaws.household.planner_cleanup_bridge import (
    planner_cleanup_bridge_evidence,
)
from roboclaws.household.planner_primitive_executor import (
    PlannerBackedCleanupContractAdapter,
)
from roboclaws.household.planner_probe_primitive_executor import (
    ProbeBackedCleanupPrimitiveExecutor,
)
from roboclaws.household.planner_proof_attachment import attach_planner_proof
from roboclaws.household.planner_proof_bundle import (
    attach_planner_proof_bundle,
    planner_proof_attachment_for_target,
)
from roboclaws.household.planner_proof_requests import (
    write_planner_proof_requests,
)
from roboclaws.household.profiles import (
    camera_labeler_from_visual_grounding_pipeline,
    cleanup_profile_metadata_for_run,
    cleanup_profile_names,
)
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    DEFAULT_MAP_MODE,
    DEFAULT_REALWORLD_TASK,
    DETERMINISTIC_SWEEP_POLICY,
    MAIN_CLEANUP_AGENT_PRODUCER,
    MINIMAL_MAP_MODE,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    REALWORLD_MAP_MODES,
    SIMULATED_CAMERA_MODEL_PROVENANCE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
    cleanup_policy_trace_from_events,
    real_robot_readiness_from_events,
)
from roboclaws.household.report import (
    render_cleanup_report,
    write_state_snapshot,
    write_trace_jsonl,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.semantic_cleanup_loop import (
    run_semantic_cleanup_loop,
)
from roboclaws.household.semantic_timeline import (
    ROBOT_VIEW_VARIANT,
    SEMANTIC_LOOP_VARIANT,
    camera_offsets_from_raw_fpv_observation,
    primitive_provenance_counts,
    record_robot_view_step,
    robot_view_camera_control_summary,
    robot_view_capture_for_tool,
    semantic_substeps,
)
from roboclaws.household.skill_scratchpad import empty_skill_scratchpad
from roboclaws.household.subprocess_backend import (
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)
from roboclaws.household.visual_grounding import (
    SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_client_from_env,
)
from roboclaws.launch.goals import (
    completion_claim_from_done_reason,
    goal_contract_from_file,
    goal_contract_from_json,
    write_goal_contract,
)
from roboclaws.maps.actionable_snapshot import runtime_metric_map_from_prior_artifact

SYNTHETIC_BACKEND = "api_semantic_synthetic"
SEMANTIC_SWEEP_POLICY = "semantic_sweep_baseline"
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"
SEMANTIC_SWEEP_CAMERA_SCHEDULE: tuple[dict[str, float], ...] = (
    {"yaw_delta_deg": 0.0, "pitch_delta_deg": 0.0},
    {"yaw_delta_deg": -30.0, "pitch_delta_deg": 0.0},
    {"yaw_delta_deg": 60.0, "pitch_delta_deg": 0.0},
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ADR-0003 real-world-style MolmoSpaces cleanup harness."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--goal-contract", type=Path)
    parser.add_argument("--goal-contract-json")
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND, ISAACLAB_SUBPROCESS_BACKEND),
        default=SYNTHETIC_BACKEND,
    )
    parser.add_argument(
        "--fixture-hint-mode",
        choices=("room_only", "exact_fixtures"),
        default="room_only",
    )
    parser.add_argument(
        "--perception-mode",
        choices=(VISIBLE_OBJECT_DETECTIONS_MODE, RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE),
        default=VISIBLE_OBJECT_DETECTIONS_MODE,
    )
    parser.add_argument(
        "--visual-grounding",
        default=SIM_VISUAL_GROUNDING_PIPELINE_ID,
        help=(
            "Internal External Visual Grounding Service pipeline id. Public task "
            "commands should use camera_labeler instead."
        ),
    )
    parser.add_argument(
        "--visual-grounding-base-url",
        help="External Visual Grounding Service base URL for non-sim pipelines.",
    )
    parser.add_argument(
        "--visual-grounding-timeout-s",
        type=float,
        help="External Visual Grounding Service timeout in seconds.",
    )
    parser.add_argument(
        "--cleanup-profile",
        choices=cleanup_profile_names(),
        help="Public cleanup evidence lane or smoke preset selected by the command facade.",
    )
    parser.add_argument(
        "--semantic-sweep",
        action="store_true",
        help=(
            "Visit inspection waypoints and update the runtime metric map without "
            "attempting cleanup actions."
        ),
    )
    parser.add_argument(
        "--map-mode",
        choices=tuple(sorted(REALWORLD_MAP_MODES)),
        default=DEFAULT_MAP_MODE,
        help=(
            "Agent-facing map projection. Default minimal exposes occupancy geometry and "
            "generated exploration candidates; rich is an explicit legacy/debug projection "
            "with authored public semantics."
        ),
    )
    parser.add_argument(
        "--runtime-map-prior",
        type=Path,
        help="Prior runtime_metric_map.json snapshot to seed this run as non-actionable priors.",
    )
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument(
        "--generated-mess-object-id",
        action="append",
        help="Private run-control object id to include in the generated mess set. Repeatable.",
    )
    parser.add_argument("--scene-source", default="procthor-10k-val")
    parser.add_argument("--scene-index", type=int, default=0)
    parser.add_argument(
        "--isaac-scene-usd-path",
        type=Path,
        help=(
            "Optional local USD/USDA scene for backend=isaaclab_subprocess real-mode "
            "scene parity checks."
        ),
    )
    parser.add_argument(
        "--isaac-enable-segmentation",
        action="store_true",
        help=(
            "Request Isaac semantic/instance segmentation tensors for "
            "backend=isaaclab_subprocess local probes."
        ),
    )
    parser.add_argument(
        "--isaac-segmentation-data-type",
        action="append",
        choices=(
            "semantic_segmentation",
            "instance_segmentation_fast",
            "instance_id_segmentation_fast",
        ),
        help=(
            "Isaac segmentation data type to request for backend=isaaclab_subprocess. "
            "Repeat to probe individual annotators."
        ),
    )
    parser.add_argument(
        "--isaac-segmentation-semantic-filter",
        action="append",
        help=(
            "Isaac camera semantic filter instance name for "
            "backend=isaaclab_subprocess. Repeat to probe prepared USD labels "
            "such as usd_prim_path."
        ),
    )
    parser.add_argument(
        "--map-bundle-dir",
        type=Path,
        help=(
            "Prebuilt Nav2 map bundle path, or environment id under assets/maps, "
            "to project metric_map/fixture_hints and snapshot into the run."
        ),
    )
    parser.add_argument(
        "--require-map-bundle",
        action="store_true",
        help="Fail fast if --map-bundle-dir is missing or invalid.",
    )
    parser.add_argument(
        "--planner-proof-run-result",
        type=Path,
        action="append",
        help=(
            "Attach a strict planner proof run_result.json. Repeat to provide "
            "one bound proof per cleanup object."
        ),
    )
    parser.add_argument(
        "--use-planner-proof-for-cleanup-primitives",
        action="store_true",
        help=(
            "Opt in to using attached bound planner proof as cleanup primitive executor "
            "evidence when it matches the current observed handle and target."
        ),
    )
    return parser.parse_args(argv)


def run_realworld_cleanup(
    *,
    output_dir: Path,
    seed: int = 1,
    task_prompt: str = DEFAULT_REALWORLD_TASK,
    backend: str = SYNTHETIC_BACKEND,
    fixture_hint_mode: str = "room_only",
    perception_mode: str = VISIBLE_OBJECT_DETECTIONS_MODE,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    molmospaces_python: str | Path | None = None,
    record_robot_views: bool = False,
    generated_mess_count: int = 10,
    generated_mess_object_ids: tuple[str, ...] = (),
    scene_source: str = "procthor-10k-val",
    scene_index: int = 0,
    isaac_scene_usd_path: str | Path | None = None,
    isaac_enable_segmentation: bool = False,
    isaac_segmentation_data_types: tuple[str, ...] | None = None,
    isaac_segmentation_semantic_filter: tuple[str, ...] | None = None,
    map_bundle_dir: str | Path | None = None,
    require_map_bundle: bool = False,
    cleanup_profile: str | None = None,
    semantic_sweep: bool = False,
    map_mode: str = DEFAULT_MAP_MODE,
    runtime_map_prior_path: str | Path | None = None,
    planner_proof_run_result: Path | None = None,
    planner_proof_run_results: list[Path] | None = None,
    use_planner_proof_for_cleanup_primitives: bool = False,
    visual_grounding: str = SIM_VISUAL_GROUNDING_PIPELINE_ID,
    visual_grounding_base_url: str | None = None,
    visual_grounding_timeout_s: float | None = None,
    goal_contract_json: str | None = None,
    goal_contract_path: str | Path | None = None,
    run_metadata_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    visual_backend_names = {MOLMOSPACES_SUBPROCESS_BACKEND, ISAACLAB_SUBPROCESS_BACKEND}
    if include_robot and backend not in visual_backend_names:
        raise ValueError("robot inclusion requires a visual subprocess backend")
    if record_robot_views and (backend not in visual_backend_names or not include_robot):
        raise ValueError(
            "record_robot_views requires a visual subprocess backend and include_robot"
        )
    if generated_mess_count < 1:
        raise ValueError("generated_mess_count must be >= 1")
    if map_mode not in REALWORLD_MAP_MODES:
        allowed = ", ".join(sorted(REALWORLD_MAP_MODES))
        raise ValueError(f"map_mode must be one of: {allowed}")
    selected_bundle_dir = selected_nav2_map_bundle_dir(
        map_bundle_dir,
        required=require_map_bundle,
    )
    planner_proof_paths = _planner_proof_paths(
        planner_proof_run_result=planner_proof_run_result,
        planner_proof_run_results=planner_proof_run_results,
    )
    if use_planner_proof_for_cleanup_primitives and not planner_proof_paths:
        raise ValueError(
            "use_planner_proof_for_cleanup_primitives requires planner_proof_run_result"
        )
    runtime_map_prior = _load_runtime_map_prior(runtime_map_prior_path)
    goal_contract = goal_contract_from_json(goal_contract_json) or goal_contract_from_file(
        goal_contract_path
    )

    backend_instance: Any | None = None
    if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        backend_instance = MolmoSpacesSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            python_executable=Path(molmospaces_python) if molmospaces_python else None,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
            generated_mess_object_ids=generated_mess_object_ids,
            scene_source=scene_source,
            scene_index=scene_index,
        )
        scenario = backend_instance.scenario
    elif backend == ISAACLAB_SUBPROCESS_BACKEND:
        backend_instance = IsaacLabSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
            generated_mess_object_ids=generated_mess_object_ids,
            scene_source=scene_source,
            scene_index=scene_index,
            map_bundle_dir=selected_bundle_dir,
            scene_usd_path=Path(isaac_scene_usd_path) if isaac_scene_usd_path else None,
            enable_segmentation=isaac_enable_segmentation,
            segmentation_data_types=isaac_segmentation_data_types,
            segmentation_semantic_filter=isaac_segmentation_semantic_filter,
        )
        scenario = backend_instance.scenario
    else:
        scenario = build_cleanup_scenario(seed=seed)

    base_contract = CleanupBackendSession(scenario, backend=backend_instance)
    contract = RealWorldCleanupContract(
        base_contract,
        task_prompt=task_prompt,
        fixture_hint_mode=fixture_hint_mode,
        perception_mode=perception_mode,
        map_bundle_dir=selected_bundle_dir,
        visual_grounding_client=visual_grounding_client_from_env(
            visual_grounding,
            base_url=visual_grounding_base_url,
            timeout_s=visual_grounding_timeout_s,
        ),
        visual_grounding_pipeline_id=visual_grounding,
        visual_grounding_artifact_base_dir=output_dir,
        visual_grounding_run_id=f"seed-{seed}",
        runtime_map_prior=runtime_map_prior,
        map_mode=map_mode,
        cleanup_profile=cleanup_profile,
    )
    planner_proof_evidence: dict[str, Any] | None = None
    if len(planner_proof_paths) == 1:
        planner_proof_evidence = attach_planner_proof(
            proof_run_result_path=planner_proof_paths[0],
            cleanup_run_dir=output_dir,
        )
    elif len(planner_proof_paths) > 1:
        planner_proof_evidence = attach_planner_proof_bundle(
            proof_run_result_paths=planner_proof_paths,
            cleanup_run_dir=output_dir,
        )
    trace_events: list[dict[str, Any]] = []
    started_at = time.time()

    before_snapshot = _write_snapshot(
        backend=backend,
        contract=base_contract,
        scenario=scenario,
        output_path=output_dir / "before.png",
        title="Before real-world cleanup",
    )
    robot_view_steps: list[dict[str, Any]] = []
    view_index = 0
    if record_robot_views:
        view_index = record_robot_view_step(
            steps=robot_view_steps,
            backend=base_contract.backend,
            output_dir=output_dir,
            index=view_index,
            label_suffix="before",
            action="before",
        )

    metric_map = _call_tool(trace_events, started_at, "metric_map", {}, contract.metric_map)
    fixture_hints = _call_tool(
        trace_events, started_at, "fixture_hints", {}, contract.fixture_hints
    )

    if semantic_sweep:
        policy_name = SEMANTIC_SWEEP_POLICY
    elif perception_mode == CAMERA_MODEL_POLICY_MODE:
        policy_name = CAMERA_MODEL_POLICY_NAME
    else:
        policy_name = DETERMINISTIC_SWEEP_POLICY
    agent_scratchpad = empty_skill_scratchpad(
        note="Deterministic direct demo scratchpad; cleanup_worklist is authoritative."
    )
    agent_scratchpad["policy"] = policy_name
    handled_handles: set[str] = set()
    pending_minimal_detections: dict[str, dict[str, Any]] = {}

    for waypoint in metric_map["inspection_waypoints"]:
        waypoint_id = str(waypoint["waypoint_id"])
        _call_tool(
            trace_events,
            started_at,
            "navigate_to_waypoint",
            {"waypoint_id": waypoint_id},
            lambda selected=waypoint_id: contract.navigate_to_waypoint(selected),
        )
        camera_schedule = (
            SEMANTIC_SWEEP_CAMERA_SCHEDULE
            if semantic_sweep
            else ({"yaw_delta_deg": 0.0, "pitch_delta_deg": 0.0},)
        )
        detections = []
        for camera_index, camera_step in enumerate(camera_schedule):
            if semantic_sweep and camera_index > 0:
                _call_tool(
                    trace_events,
                    started_at,
                    "adjust_camera",
                    dict(camera_step),
                    lambda step=camera_step: contract.adjust_camera(**step),
                )
            observation = _call_tool(
                trace_events,
                started_at,
                "observe",
                {},
                contract.observe,
                postprocess=lambda response: _attach_raw_fpv_robot_view(
                    response=response,
                    contract=contract,
                    base_contract=base_contract,
                    robot_view_steps=robot_view_steps,
                    output_dir=output_dir,
                    view_index_ref=[view_index],
                    record_robot_views=record_robot_views,
                ),
            )
            view_index = _view_index_after_raw_fpv(robot_view_steps, view_index)
            detections.extend(
                _detections_for_policy(
                    trace_events=trace_events,
                    started_at=started_at,
                    contract=contract,
                    observation=observation,
                    perception_mode=perception_mode,
                )
            )
        if semantic_sweep:
            continue
        for detection in detections:
            if map_mode == MINIMAL_MAP_MODE:
                pending_minimal_detections[str(detection["object_id"])] = dict(detection)
                continue
            view_index = _maybe_clean_visible_object(
                trace_events=trace_events,
                started_at=started_at,
                contract=contract,
                base_contract=base_contract,
                detection=detection,
                fixture_hints=fixture_hints,
                robot_view_steps=robot_view_steps,
                output_dir=output_dir,
                view_index=view_index,
                record_robot_views=record_robot_views,
                planner_proof_evidence=(
                    planner_proof_evidence if use_planner_proof_for_cleanup_primitives else None
                ),
                agent_scratchpad=agent_scratchpad,
                handled_handles=handled_handles,
                perception_mode=perception_mode,
            )

    if not semantic_sweep and map_mode == MINIMAL_MAP_MODE:
        for detection in pending_minimal_detections.values():
            view_index = _maybe_clean_visible_object(
                trace_events=trace_events,
                started_at=started_at,
                contract=contract,
                base_contract=base_contract,
                detection=detection,
                fixture_hints=fixture_hints,
                robot_view_steps=robot_view_steps,
                output_dir=output_dir,
                view_index=view_index,
                record_robot_views=record_robot_views,
                planner_proof_evidence=(
                    planner_proof_evidence if use_planner_proof_for_cleanup_primitives else None
                ),
                agent_scratchpad=agent_scratchpad,
                handled_handles=handled_handles,
                perception_mode=perception_mode,
            )

    done = _call_tool(
        trace_events,
        started_at,
        "done",
        {"reason": f"{policy_name} complete"},
        lambda: (
            _semantic_sweep_done(contract, base_contract, f"{policy_name} complete")
            if semantic_sweep
            else contract.done(f"{policy_name} complete")
        ),
    )
    if "score" not in done:
        base_done = base_contract.done(reason=f"{policy_name} incomplete")
        score = dict(base_done.get("score") or {})
        final_locations = dict(
            base_done.get("final_locations") or base_contract.backend.object_locations()
        )
        if score:
            metrics = contract._realworld_metrics(score, final_locations)  # noqa: SLF001
            score.update(metrics)
        else:
            score = _failed_score(contract)
        done = {
            **done,
            "cleanup_status": "failed",
            "score": score,
            "final_locations": final_locations,
            "final_containment": base_done.get("final_containment", {}),
            "tool_event_counts": base_done.get("tool_event_counts", {}),
        }

    after_snapshot = _write_snapshot(
        backend=backend,
        contract=base_contract,
        scenario=scenario,
        output_path=output_dir / "after.png",
        title="After real-world cleanup",
    )
    if record_robot_views:
        view_index = record_robot_view_step(
            steps=robot_view_steps,
            backend=base_contract.backend,
            output_dir=output_dir,
            index=view_index,
            label_suffix="after",
            action="after",
        )
    trace_path = output_dir / "trace.jsonl"
    write_trace_jsonl(trace_path, trace_events)

    agent_view_path = output_dir / "agent_view.json"
    runtime_metric_map_path = output_dir / "runtime_metric_map.json"
    private_evaluation_path = output_dir / "private_evaluation.json"
    agent_view = contract.agent_view_payload()
    runtime_metric_map = agent_view.get("runtime_metric_map", {})
    cleanup_policy_trace = cleanup_policy_trace_from_events(trace_events, agent_view)
    real_robot_readiness = real_robot_readiness_from_events(
        agent_view=agent_view,
        trace_events=trace_events,
        robot_view_steps=robot_view_steps,
    )
    private_evaluation = contract.private_evaluation_payload(done["score"])
    private_evaluation["requested_generated_mess_count"] = generated_mess_count
    advisory_evaluation = build_advisory_evaluation(
        score=done["score"],
        scenario_id=scenario.scenario_id,
    )
    agent_view_path.write_text(json.dumps(agent_view, indent=2, sort_keys=True) + "\n")
    runtime_metric_map_path.write_text(
        json.dumps(runtime_metric_map, indent=2, sort_keys=True) + "\n"
    )
    private_evaluation_path.write_text(
        json.dumps(private_evaluation, indent=2, sort_keys=True) + "\n"
    )
    advisory_evaluation_path = output_dir / "advisory_evaluation.json"
    advisory_evaluation_path.write_text(
        json.dumps(advisory_evaluation, indent=2, sort_keys=True) + "\n"
    )
    goal_contract_path_out = output_dir / "goal_contract.json"
    goal_contract_payload: dict[str, Any] = {}
    agent_completion_claim: dict[str, Any] = {}
    if goal_contract is not None:
        write_goal_contract(goal_contract_path_out, goal_contract)
        goal_contract_payload = goal_contract.to_payload()
        agent_completion_claim = completion_claim_from_done_reason(
            str(done.get("reason") or f"{policy_name} complete"),
            goal_contract=goal_contract,
        )
    agent_scratchpad_path = output_dir / "agent_scratchpad.json"
    agent_scratchpad_path.write_text(json.dumps(agent_scratchpad, indent=2, sort_keys=True) + "\n")
    substeps = semantic_substeps(trace_events, contract.public_receptacles_by_id())
    cleanup_primitive_evidence = cleanup_primitive_evidence_from_substeps(substeps)
    planner_proof_requests_path = output_dir / "planner_proof_requests.json"
    planner_proof_requests = write_planner_proof_requests(
        output_path=planner_proof_requests_path,
        contract=contract,
        substeps=substeps,
    )

    primitive_summary = primitive_provenance_counts(trace_events)
    cleanup_primitives_planner_backed = cleanup_primitive_evidence.get("planner_backed") is True
    if cleanup_primitives_planner_backed:
        run_primitive_provenance = "planner_backed"
    elif backend == ISAACLAB_SUBPROCESS_BACKEND:
        run_primitive_provenance = ISAAC_SEMANTIC_POSE_PROVENANCE
    else:
        run_primitive_provenance = API_SEMANTIC_PROVENANCE
    manipulation_evidence = (
        planner_backed_cleanup_manipulation_evidence(
            backend=backend,
            primitive_summary=primitive_summary,
        )
        if cleanup_primitives_planner_backed
        else isaac_semantic_pose_manipulation_evidence(
            backend=backend,
            primitive_summary=primitive_summary,
        )
        if backend == ISAACLAB_SUBPROCESS_BACKEND
        else api_semantic_manipulation_evidence(
            backend=backend,
            primitive_summary=primitive_summary,
        )
    )
    public_tool_counts = _tool_event_counts(trace_events)
    profile_metadata = (
        cleanup_profile_metadata_for_run(
            profile_name=cleanup_profile,
            backend=backend,
            perception_mode=perception_mode,
            record_robot_views=record_robot_views,
            camera_labeler=camera_labeler_from_visual_grounding_pipeline(
                contract.visual_grounding_pipeline_id
            )
            if perception_mode == CAMERA_MODEL_POLICY_MODE
            else None,
        )
        if cleanup_profile is not None
        else None
    )
    run_result = {
        "backend": backend,
        "scenario_id": scenario.scenario_id,
        "seed": seed,
        "task_prompt": task_prompt,
        "task_surface": goal_contract_payload.get("surface", "household-world"),
        "task_intent": goal_contract_payload.get(
            "intent",
            "map-build" if semantic_sweep else "cleanup",
        ),
        "goal_contract": goal_contract_payload,
        "agent_completion_claim": agent_completion_claim,
        "contract": REALWORLD_CONTRACT,
        "adr_0003_satisfied": True,
        "final_status": done["cleanup_status"],
        "terminate_reason": f"{policy_name} complete",
        "cleanup_status": done["cleanup_status"],
        "completion_status": done["score"]["completion_status"],
        "primitive_provenance": run_primitive_provenance,
        "primitive_provenance_summary": primitive_summary,
        "manipulation_evidence": manipulation_evidence,
        "policy": policy_name,
        "planner": policy_name,
        "agent_driven": False,
        "policy_uses_private_truth": False,
        "planner_uses_private_manifest": False,
        "planner_proof_cleanup_executor_enabled": use_planner_proof_for_cleanup_primitives,
        "fixture_hint_mode": fixture_hint_mode,
        "perception_mode": perception_mode,
        "map_mode": map_mode,
        "semantic_sweep_mode": semantic_sweep,
        "cleanup_actions_disabled": semantic_sweep,
        "runtime_metric_map_prior": {
            "loaded": bool(runtime_map_prior),
            "source": str(runtime_map_prior_path or ""),
            "observed_object_count": len((runtime_map_prior or {}).get("observed_objects") or []),
        },
        "camera_labeler": camera_labeler_from_visual_grounding_pipeline(
            contract.visual_grounding_pipeline_id
        )
        if perception_mode == CAMERA_MODEL_POLICY_MODE
        else "",
        "visual_grounding_pipeline_id": contract.visual_grounding_pipeline_id,
        "requested_generated_mess_count": generated_mess_count,
        "generated_mess_count": private_evaluation["generated_mess_count"],
        "mess_restoration_rate": done["score"]["mess_restoration_rate"],
        "sweep_coverage_rate": done["score"]["sweep_coverage_rate"],
        "disturbance_count": done["score"]["disturbance_count"],
        "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
        "semantic_substeps": substeps,
        "cleanup_primitive_evidence": cleanup_primitive_evidence,
        "planner_proof_requests": planner_proof_requests,
        "cleanup_policy_trace": cleanup_policy_trace,
        "real_robot_readiness": real_robot_readiness,
        "agent_view": agent_view,
        "runtime_metric_map": runtime_metric_map,
        "raw_fpv_observations": agent_view.get("raw_fpv_observations", []),
        "camera_model_policy_evidence": agent_view.get("camera_model_policy_evidence", {}),
        "model_declared_observations": agent_view.get("model_declared_observations", []),
        "model_declared_observation_evidence": agent_view.get(
            "model_declared_observation_evidence",
            {},
        ),
        "semantic_sweep": {
            "enabled": semantic_sweep,
            "map_mode": map_mode,
            "minimal_map_mode": map_mode == MINIMAL_MAP_MODE,
            "camera_schedule": list(SEMANTIC_SWEEP_CAMERA_SCHEDULE) if semantic_sweep else [],
            "snapshot_artifact": str(runtime_metric_map_path) if semantic_sweep else "",
            "cleanup_actions_disabled": semantic_sweep,
        },
        "agent_scratchpad": agent_scratchpad,
        "private_evaluation": private_evaluation,
        "advisory_evaluation": advisory_evaluation,
        "score": done["score"],
        "final_locations": done["final_locations"],
        "final_containment": done.get("final_containment", {}),
        "tool_event_counts": public_tool_counts,
        "backend_tool_event_counts": done["tool_event_counts"],
        "rerun_command": os.environ.get(REPORT_RERUN_COMMAND_ENV, "").strip(),
        "artifacts": {
            "agent_view": str(agent_view_path),
            "runtime_metric_map": str(runtime_metric_map_path),
            "private_evaluation": str(private_evaluation_path),
            "advisory_evaluation": str(advisory_evaluation_path),
            "agent_scratchpad": str(agent_scratchpad_path),
            "planner_proof_requests": str(planner_proof_requests_path),
            "trace": str(trace_path),
            "before_snapshot": str(before_snapshot),
            "after_snapshot": str(after_snapshot),
        },
    }
    if goal_contract is not None:
        run_result["artifacts"]["goal_contract"] = str(goal_contract_path_out)
    if profile_metadata is not None:
        run_result["evidence_lane"] = profile_metadata["evidence_lane"]
        run_result["cleanup_profile"] = profile_metadata["evidence_lane"]
        run_result["cleanup_profile_metadata"] = profile_metadata
    attach_nav2_map_bundle_snapshot(
        run_result=run_result,
        run_dir=output_dir,
        source_bundle_dir=selected_bundle_dir,
    )
    if backend_instance is not None:
        mess_diagnostics = getattr(backend_instance, "mess_placement_diagnostics", None)
        placement_diagnostics = getattr(backend_instance, "placement_diagnostics", None)
        if mess_diagnostics is not None:
            run_result["mess_placement_diagnostics"] = mess_diagnostics
        if placement_diagnostics is not None:
            run_result["placement_diagnostics"] = placement_diagnostics
        if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
            run_result["molmospaces_runtime"] = {
                "python_executable": str(backend_instance.python_executable),
                "runtime": backend_instance.runtime,
                "model_stats": backend_instance.model_stats,
                "scene_xml": backend_instance.scene_xml,
                "metadata_object_count": backend_instance.metadata_object_count,
                "requested_generated_mess_count": backend_instance.requested_generated_mess_count,
                "generated_mess_count": backend_instance.generated_mess_count,
            }
        elif backend == ISAACLAB_SUBPROCESS_BACKEND:
            isaac_scene_index_path = output_dir / "isaac_scene_index.json"
            isaac_scene_index_path.write_text(
                json.dumps(
                    backend_instance.scene_index_artifact_payload(),
                    indent=2,
                    sort_keys=True,
                )
                + "\n"
            )
            run_result["artifacts"]["isaac_scene_index"] = str(isaac_scene_index_path)
            run_result["isaac_runtime"] = {
                "python_executable": str(backend_instance.python_executable),
                "runtime": backend_instance.runtime,
                "scenario_source": backend_instance.scenario_source,
                "scene_usd": backend_instance.scene_usd,
                "scene_index": backend_instance.scene_index,
                "scene_index_artifact": str(isaac_scene_index_path),
                "object_index_count": len(backend_instance.object_index),
                "receptacle_index_count": len(backend_instance.receptacle_index),
                "object_index": backend_instance.object_index,
                "receptacle_index": backend_instance.receptacle_index,
                "scene_index_diagnostics": backend_instance.scene_index_diagnostics,
                "scene_binding_diagnostics": backend_instance.scene_binding_diagnostics,
                "segmentation": backend_instance.segmentation,
                "scene_load": backend_instance.scene_load,
                "mapping_gaps": backend_instance.current_mapping_gaps,
                "snapshot_artifacts": backend_instance.snapshot_artifacts,
                "semantic_pose_state": backend_instance.semantic_pose_state,
                "semantic_pose_view_capture": backend_instance.semantic_pose_view_capture,
                "robot": backend_instance.robot,
                "robot_import": getattr(backend_instance, "robot_import", {}),
                "requested_generated_mess_count": backend_instance.requested_generated_mess_count,
                "generated_mess_count": backend_instance.generated_mess_count,
            }
        if getattr(backend_instance, "robot", None) is not None:
            run_result["robot"] = backend_instance.robot
            run_result["robot_import"] = getattr(backend_instance, "robot_import", {})
            run_result["robot_name"] = backend_instance.robot.get("robot_name")
    if robot_view_steps:
        run_result["view_variant"] = (
            ISAACLAB_ROBOT_VIEW_VARIANT
            if backend == ISAACLAB_SUBPROCESS_BACKEND
            else ROBOT_VIEW_VARIANT
        )
        run_result["robot_view_steps"] = robot_view_steps
        run_result["robot_view_camera_control"] = robot_view_camera_control_summary(
            robot_view_steps
        )
        run_result["artifacts"]["robot_views"] = str(output_dir / "robot_views")
    if planner_proof_evidence is not None:
        run_result["planner_backed_manipulation_proof"] = planner_proof_evidence
        run_result["planner_cleanup_bridge_evidence"] = planner_cleanup_bridge_evidence(
            planner_proof_attachment=run_result["planner_backed_manipulation_proof"],
            cleanup_primitive_evidence=cleanup_primitive_evidence,
        )
        run_result["artifacts"]["planner_proof_views"] = str(output_dir / "planner_proof")
    if run_metadata_overrides:
        run_result = _merge_run_metadata(run_result, run_metadata_overrides)

    report_path = render_cleanup_report(
        run_dir=output_dir,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        robot_view_steps=robot_view_steps,
    )
    run_result["artifacts"]["report"] = str(report_path)
    run_result_path = output_dir / "run_result.json"
    run_result_path.write_text(json.dumps(run_result, indent=2, sort_keys=True) + "\n")
    return run_result


def _load_runtime_map_prior(path: str | Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    prior_path = Path(path)
    payload = json.loads(prior_path.read_text(encoding="utf-8"))
    return runtime_metric_map_from_prior_artifact(payload)


def _failed_score(contract: RealWorldCleanupContract) -> dict[str, Any]:
    total_targets = len(contract.scenario.private_manifest.targets)
    return {
        "status": "failed",
        "restored_count": 0,
        "total_targets": total_targets,
        "success_threshold": contract.scenario.private_manifest.success_threshold,
        "restored_object_ids": [],
        "missed_object_ids": [
            target.object_id for target in contract.scenario.private_manifest.targets
        ],
        "object_results": [],
        "mess_restoration_rate": 0.0,
        "sweep_coverage_rate": 0.0,
        "disturbance_count": 0,
        "completion_status": "failed",
        "semantic_acceptability": {
            "accepted_count": 0,
            "total_targets": total_targets,
            "rate": 0.0,
            "status": "failed",
        },
    }


def _merge_run_metadata(
    run_result: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    merged = dict(run_result)
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    return merged


def _semantic_sweep_done(
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    reason: str,
) -> dict[str, Any]:
    done = base_contract.done(reason=reason)
    score = dict(done["score"])
    final_locations = dict(done["final_locations"])
    metrics = contract._realworld_metrics(score, final_locations)  # noqa: SLF001
    score.update(metrics)
    return {
        "ok": True,
        "tool": "done",
        "status": "ok",
        "reason": reason,
        "cleanup_status": "semantic_sweep_complete",
        "score": score,
        "final_locations": final_locations,
        "final_containment": done.get("final_containment", {}),
        "tool_event_counts": done.get("tool_event_counts", {}),
        "contract": REALWORLD_CONTRACT,
        "policy_uses_private_truth": False,
        "semantic_sweep_mode": True,
        "cleanup_actions_disabled": True,
    }


def _detections_for_policy(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    observation: dict[str, Any],
    perception_mode: str,
) -> list[dict[str, Any]]:
    if perception_mode not in {CAMERA_MODEL_POLICY_MODE, RAW_FPV_ONLY_MODE}:
        return list(observation.get("visible_object_detections", []))
    raw = observation.get("raw_fpv_observation") or {}
    if perception_mode == RAW_FPV_ONLY_MODE:
        waypoint = contract._waypoint_by_id(str(raw.get("waypoint_id") or ""))
        candidate_inputs = (
            contract._simulated_declaration_inputs_for_waypoint(
                waypoint,
                observation_id=str(raw.get("observation_id", "")),
            )
            if waypoint is not None
            else []
        )
        detections: list[dict[str, Any]] = []
        for candidate in candidate_inputs:
            response = _call_tool(
                trace_events,
                started_at,
                "navigate_to_visual_candidate",
                {
                    "source_observation_id": raw.get("observation_id", ""),
                    "category": candidate.get("category", ""),
                    "producer_type": MAIN_CLEANUP_AGENT_PRODUCER,
                    "producer_id": "deterministic_raw_fpv_agent",
                },
                lambda item=candidate: contract.navigate_to_visual_candidate(
                    str(raw.get("observation_id", "")),
                    category=str(item.get("category") or ""),
                    evidence_note=str(item.get("evidence_note") or ""),
                    image_region=item.get("image_region") or {},
                    source_fixture_id=str(item.get("source_fixture_id") or ""),
                    confidence=item.get("confidence"),
                    producer_type=MAIN_CLEANUP_AGENT_PRODUCER,
                    producer_id="deterministic_raw_fpv_agent",
                ),
            )
            if not response.get("ok"):
                continue
            detection = contract.inspect_visible_object(str(response.get("object_id") or ""))
            if detection.get("ok") and isinstance(detection.get("detection"), dict):
                detections.append(dict(detection["detection"]))
        return detections
    candidate_inputs = None
    producer_type = (
        SIMULATED_CAMERA_MODEL_PROVENANCE
        if perception_mode == CAMERA_MODEL_POLICY_MODE
        else MAIN_CLEANUP_AGENT_PRODUCER
    )
    producer_id = (
        CAMERA_MODEL_POLICY_NAME
        if perception_mode == CAMERA_MODEL_POLICY_MODE
        else "deterministic_raw_fpv_agent"
    )
    candidates = _call_tool(
        trace_events,
        started_at,
        "declare_visual_candidates",
        {
            "observation_id": raw.get("observation_id", ""),
            "producer_type": producer_type,
            "producer_id": producer_id,
            "candidate_count": len(candidate_inputs or []),
        },
        lambda: contract.declare_visual_candidates(
            str(raw.get("observation_id", "")),
            candidates=candidate_inputs,
            producer_type=producer_type,
            producer_id=producer_id,
        ),
    )
    return list(candidates.get("camera_model_candidates", []))


def _decision_reason(perception_mode: str) -> str:
    if perception_mode == CAMERA_MODEL_POLICY_MODE:
        return "camera model category/fixture affordance heuristic"
    if perception_mode == RAW_FPV_ONLY_MODE:
        return "model-declared raw FPV category/fixture affordance heuristic"
    return "public category/fixture affordance heuristic"


def _tool_event_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        tool = event.get("tool")
        event_name = event.get("event")
        if not tool or not event_name:
            continue
        key = f"{tool}:{event_name}"
        counts[key] = counts.get(key, 0) + 1
    return counts


def _clean_visible_object(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    detection: dict[str, Any],
    target_fixture: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    planner_proof_evidence: dict[str, Any] | None = None,
) -> int:
    handle = str(detection["object_id"])
    target_fixture_id = str(target_fixture["fixture_id"])

    def record_loop_robot_view(
        tool: str,
        request: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        nonlocal view_index
        if not record_robot_views or not response.get("ok"):
            return
        capture = robot_view_capture_for_tool(
            tool,
            request,
            response,
            object_id_transform=lambda value: (
                _internal_object_id(contract, value) if value is not None else None
            ),
        )
        if capture is None:
            return
        view_index = record_robot_view_step(
            steps=robot_view_steps,
            backend=base_contract.backend,
            output_dir=output_dir,
            index=view_index,
            action=str(capture["action"]),
            label_suffix=str(capture["label_suffix"]),
            focus_object_id=capture.get("focus_object_id"),
            focus_receptacle_id=contract.internal_fixture_id_for_public_reference(
                capture.get("focus_receptacle_id")
            ),
            semantic_phase=capture.get("semantic_phase"),
            action_evidence=capture.get("action_evidence"),
        )

    loop_contract = _cleanup_loop_contract_for_target(
        contract=contract,
        planner_proof_evidence=planner_proof_evidence,
        object_id=handle,
        target_receptacle_id=target_fixture_id,
    )

    run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": handle,
                "target_receptacle_id": target_fixture_id,
                "target_receptacle": target_fixture,
            }
        ],
        contract=loop_contract,
        call_tool=lambda tool, request, fn: _call_tool(
            trace_events,
            started_at,
            tool,
            request,
            fn,
        ),
        record_tool_view=record_loop_robot_view,
        target_request_key="fixture_id",
        include_object_id_in_receptacle_request=False,
        include_object_id_in_target_requests=False,
    )
    post_place_observation = _call_tool(
        trace_events,
        started_at,
        "observe",
        {},
        contract.observe,
        postprocess=lambda response: _attach_raw_fpv_robot_view(
            response=response,
            contract=contract,
            base_contract=base_contract,
            robot_view_steps=robot_view_steps,
            output_dir=output_dir,
            view_index_ref=[view_index],
            record_robot_views=record_robot_views,
        ),
    )
    if post_place_observation.get("ok"):
        view_index = _view_index_after_raw_fpv(robot_view_steps, view_index)

    return view_index


def _maybe_clean_visible_object(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    detection: dict[str, Any],
    fixture_hints: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
    planner_proof_evidence: dict[str, Any] | None,
    agent_scratchpad: dict[str, Any],
    handled_handles: set[str],
    perception_mode: str,
) -> int:
    handle = str(detection["object_id"])
    if handle in handled_handles:
        return view_index
    agent_scratchpad["observed_handles"].setdefault(handle, {"object_id": handle})
    live_detection = contract.inspect_visible_object(handle)
    if live_detection.get("ok") and isinstance(live_detection.get("detection"), dict):
        detection = dict(live_detection["detection"])
    target_fixture = contract.target_fixture_for_detection(detection, fixture_hints)
    if target_fixture is None:
        agent_scratchpad["failed_attempts"].append(
            {"object_id": handle, "reason": "no_public_fixture_match"}
        )
        return view_index
    target_fixture_id = str(target_fixture["fixture_id"])
    support = detection.get("support_estimate") or {}
    if support.get("fixture_id") == target_fixture_id:
        agent_scratchpad["notes"].append(
            {"object_id": handle, "reason": "already_on_inferred_fixture"}
        )
        return view_index
    if str(detection.get("candidate_state") or "") == "visual_scan_required":
        source_waypoint_id = str(
            detection.get("waypoint_id")
            or detection.get("last_waypoint_id")
            or (detection.get("support_estimate") or {}).get("waypoint_id")
            or ""
        )
        if source_waypoint_id:
            _call_tool(
                trace_events,
                started_at,
                "navigate_to_waypoint",
                {"waypoint_id": source_waypoint_id, "reason": "source_fpv_scan_confirm"},
                lambda selected=source_waypoint_id: contract.navigate_to_waypoint(selected),
            )
        _call_tool(
            trace_events,
            started_at,
            "adjust_camera",
            {"yaw_delta_deg": 15.0, "pitch_delta_deg": 0.0},
            lambda: contract.adjust_camera(yaw_delta_deg=15.0, pitch_delta_deg=0.0),
        )
        confirmed_observation = _call_tool(
            trace_events,
            started_at,
            "observe",
            {},
            contract.observe,
            postprocess=lambda response: _attach_raw_fpv_robot_view(
                response=response,
                contract=contract,
                base_contract=base_contract,
                robot_view_steps=robot_view_steps,
                output_dir=output_dir,
                view_index_ref=[view_index],
                record_robot_views=record_robot_views,
            ),
        )
        view_index = _view_index_after_raw_fpv(robot_view_steps, view_index)
        confirmed = next(
            (
                item
                for item in confirmed_observation.get("visible_object_detections", [])
                if item.get("object_id") == handle
            ),
            None,
        )
        if confirmed is None:
            agent_scratchpad["failed_attempts"].append(
                {"object_id": handle, "reason": "visual_scan_confirmation_missing"}
            )
            return view_index
        detection = dict(confirmed)
    next_view_index = _clean_visible_object(
        trace_events=trace_events,
        started_at=started_at,
        contract=contract,
        base_contract=base_contract,
        detection=detection,
        target_fixture=target_fixture,
        robot_view_steps=robot_view_steps,
        output_dir=output_dir,
        view_index=view_index,
        record_robot_views=record_robot_views,
        planner_proof_evidence=planner_proof_evidence,
    )
    handled_handles.add(handle)
    agent_scratchpad["observed_handles"][handle].update(
        {
            "object_id": handle,
            "category": detection.get("category"),
            "from_fixture_id": support.get("fixture_id"),
            "to_fixture_id": target_fixture_id,
            "reason": _decision_reason(perception_mode),
            "perception_source": detection.get("perception_source", "visible_detection"),
            "model_provenance": detection.get("model_provenance"),
            "source_observation_id": detection.get("source_observation_id"),
            "handled": True,
        }
    )
    return next_view_index


def _write_snapshot(
    *,
    backend: str,
    contract: CleanupBackendSession,
    scenario: Any,
    output_path: Path,
    title: str,
) -> Path:
    if backend in {MOLMOSPACES_SUBPROCESS_BACKEND, ISAACLAB_SUBPROCESS_BACKEND}:
        return contract.backend.write_snapshot(output_path, title=title)
    return write_state_snapshot(
        scenario,
        contract.backend.object_locations(),
        output_path,
        title=title,
    )


def _internal_object_id(contract: RealWorldCleanupContract, handle: str) -> str | None:
    return contract._internal_object_id(handle)


def _cleanup_loop_contract_for_target(
    *,
    contract: RealWorldCleanupContract,
    planner_proof_evidence: dict[str, Any] | None,
    object_id: str,
    target_receptacle_id: str,
) -> Any:
    if planner_proof_evidence is None:
        return contract
    planner_proof_attachment = planner_proof_attachment_for_target(
        planner_proof_evidence,
        object_id=object_id,
        target_receptacle_id=target_receptacle_id,
    )
    if planner_proof_attachment is None:
        return contract
    executor = ProbeBackedCleanupPrimitiveExecutor(
        planner_proof_attachment,
        executor_name="probe_backed_realworld_cleanup_executor",
    )
    return PlannerBackedCleanupContractAdapter(
        contract,
        executor=executor,
        executor_name="probe_backed_realworld_cleanup_executor",
    )


def _planner_proof_paths(
    *,
    planner_proof_run_result: Path | None,
    planner_proof_run_results: list[Path] | None,
) -> list[Path]:
    paths = []
    if planner_proof_run_result is not None:
        paths.append(planner_proof_run_result)
    paths.extend(planner_proof_run_results or [])
    return paths


def _call_tool(
    events: list[dict[str, Any]],
    started_at: float,
    tool: str,
    request: dict[str, Any],
    fn: Any,
    *,
    postprocess: Any | None = None,
) -> dict[str, Any]:
    events.append(_trace_event(started_at, tool=tool, event="request", request=request))
    response = fn()
    if postprocess is not None:
        response = postprocess(response)
    events.append(_trace_event(started_at, tool=tool, event="response", response=response))
    return response


def _attach_raw_fpv_robot_view(
    *,
    response: dict[str, Any],
    contract: RealWorldCleanupContract,
    base_contract: CleanupBackendSession,
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index_ref: list[int],
    record_robot_views: bool,
) -> dict[str, Any]:
    if (
        contract.perception_mode not in {RAW_FPV_ONLY_MODE, CAMERA_MODEL_POLICY_MODE}
        or not record_robot_views
        or not response.get("ok")
    ):
        return response
    raw = response.get("raw_fpv_observation")
    if not isinstance(raw, dict):
        return response
    observation_id = str(raw.get("observation_id", ""))
    if not observation_id:
        return response
    view_index_ref[0] = record_robot_view_step(
        steps=robot_view_steps,
        backend=base_contract.backend,
        output_dir=output_dir,
        index=view_index_ref[0],
        label_suffix=observation_id,
        action=f"observe {observation_id}",
        **camera_offsets_from_raw_fpv_observation(raw),
    )
    step = robot_view_steps[-1]
    attached = contract.attach_raw_fpv_observation_artifact(
        observation_id,
        views=step.get("views") or {},
        robot_view_label=str(step.get("label", "")),
    )
    if attached is None:
        return response
    updated = dict(response)
    updated["raw_fpv_observation"] = attached
    return updated


def _view_index_after_raw_fpv(steps: list[dict[str, Any]], fallback_index: int) -> int:
    if not steps:
        return fallback_index
    try:
        label = str(steps[-1].get("label", ""))
        return max(fallback_index, int(label.split("_", 1)[0]) + 1)
    except (TypeError, ValueError):
        return fallback_index


def _trace_event(started_at: float, *, tool: str, event: str, **payload: Any) -> dict[str, Any]:
    now = time.time()
    return {
        "ts": now,
        "wallclock_elapsed": round(now - started_at, 6),
        "tool": tool,
        "event": event,
        **payload,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    result = run_realworld_cleanup(
        output_dir=args.output_dir,
        seed=args.seed,
        task_prompt=args.task,
        backend=args.backend,
        fixture_hint_mode=args.fixture_hint_mode,
        perception_mode=args.perception_mode,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        molmospaces_python=None,
        record_robot_views=args.record_robot_views,
        generated_mess_count=args.generated_mess_count,
        generated_mess_object_ids=tuple(args.generated_mess_object_id or ()),
        scene_source=args.scene_source,
        scene_index=args.scene_index,
        isaac_scene_usd_path=args.isaac_scene_usd_path,
        isaac_enable_segmentation=args.isaac_enable_segmentation,
        isaac_segmentation_data_types=tuple(args.isaac_segmentation_data_type or ()),
        isaac_segmentation_semantic_filter=tuple(args.isaac_segmentation_semantic_filter or ()),
        map_bundle_dir=args.map_bundle_dir,
        require_map_bundle=args.require_map_bundle,
        cleanup_profile=args.cleanup_profile,
        semantic_sweep=args.semantic_sweep,
        map_mode=args.map_mode,
        runtime_map_prior_path=args.runtime_map_prior,
        planner_proof_run_results=args.planner_proof_run_result,
        use_planner_proof_for_cleanup_primitives=args.use_planner_proof_for_cleanup_primitives,
        visual_grounding=args.visual_grounding,
        visual_grounding_base_url=args.visual_grounding_base_url,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
        goal_contract_json=args.goal_contract_json,
        goal_contract_path=args.goal_contract,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

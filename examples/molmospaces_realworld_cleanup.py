#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.advisory_scoring import build_advisory_evaluation  # noqa: E402
from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE  # noqa: E402
from roboclaws.molmo_cleanup.cleanup_primitive_evidence import (  # noqa: E402
    cleanup_primitive_evidence_from_substeps,
)
from roboclaws.molmo_cleanup.manipulation_provenance import (  # noqa: E402
    api_semantic_manipulation_evidence,
)
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract  # noqa: E402
from roboclaws.molmo_cleanup.planner_proof_attachment import attach_planner_proof  # noqa: E402
from roboclaws.molmo_cleanup.realworld_contract import (  # noqa: E402
    CAMERA_MODEL_POLICY_MODE,
    CAMERA_MODEL_POLICY_NAME,
    DEFAULT_REALWORLD_TASK,
    DETERMINISTIC_SWEEP_POLICY,
    RAW_FPV_ONLY_MODE,
    REALWORLD_CONTRACT,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    RealWorldCleanupContract,
)
from roboclaws.molmo_cleanup.report import (  # noqa: E402
    render_cleanup_report,
    write_state_snapshot,
    write_trace_jsonl,
)
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario  # noqa: E402
from roboclaws.molmo_cleanup.semantic_cleanup_loop import (  # noqa: E402
    run_semantic_cleanup_loop,
)
from roboclaws.molmo_cleanup.semantic_timeline import (  # noqa: E402
    ROBOT_VIEW_VARIANT,
    SEMANTIC_LOOP_VARIANT,
    primitive_provenance_counts,
    record_robot_view_step,
    robot_view_capture_for_tool,
    semantic_substeps,
)
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)

SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the ADR-0003 real-world-style MolmoSpaces cleanup harness."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND),
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
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--planner-proof-run-result", type=Path)
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
    record_robot_views: bool = False,
    generated_mess_count: int = 10,
    planner_proof_run_result: Path | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    if include_robot and backend != MOLMOSPACES_SUBPROCESS_BACKEND:
        raise ValueError("robot inclusion requires backend=molmospaces_subprocess")
    if record_robot_views and (backend != MOLMOSPACES_SUBPROCESS_BACKEND or not include_robot):
        raise ValueError(
            "record_robot_views requires backend=molmospaces_subprocess and include_robot"
        )
    if generated_mess_count < 1:
        raise ValueError("generated_mess_count must be >= 1")

    backend_instance: Any | None = None
    if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        backend_instance = MolmoSpacesSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
            generated_mess_count=generated_mess_count,
        )
        scenario = backend_instance.scenario
    else:
        scenario = build_cleanup_scenario(seed=seed)

    base_contract = MolmoCleanupToolContract(scenario, backend=backend_instance)
    contract = RealWorldCleanupContract(
        base_contract,
        task_prompt=task_prompt,
        fixture_hint_mode=fixture_hint_mode,
        perception_mode=perception_mode,
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

    policy_name = (
        CAMERA_MODEL_POLICY_NAME
        if perception_mode == CAMERA_MODEL_POLICY_MODE
        else DETERMINISTIC_SWEEP_POLICY
    )
    agent_memory: dict[str, Any] = {
        "policy": policy_name,
        "observed_handles": [],
        "decisions": [],
        "skipped_handles": [],
    }
    handled_handles: set[str] = set()

    for waypoint in metric_map["inspection_waypoints"]:
        waypoint_id = str(waypoint["waypoint_id"])
        _call_tool(
            trace_events,
            started_at,
            "navigate_to_waypoint",
            {"waypoint_id": waypoint_id},
            lambda selected=waypoint_id: contract.navigate_to_waypoint(selected),
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
        detections = _detections_for_policy(
            trace_events=trace_events,
            started_at=started_at,
            contract=contract,
            observation=observation,
            perception_mode=perception_mode,
        )
        for detection in detections:
            handle = str(detection["object_id"])
            if handle in handled_handles:
                continue
            if handle not in agent_memory["observed_handles"]:
                agent_memory["observed_handles"].append(handle)
            target_fixture = contract.target_fixture_for_detection(detection, fixture_hints)
            if target_fixture is None:
                agent_memory["skipped_handles"].append(
                    {"object_id": handle, "reason": "no_public_fixture_match"}
                )
                continue
            target_fixture_id = str(target_fixture["fixture_id"])
            support = detection.get("support_estimate") or {}
            if support.get("fixture_id") == target_fixture_id:
                agent_memory["skipped_handles"].append(
                    {"object_id": handle, "reason": "already_on_inferred_fixture"}
                )
                continue
            view_index = _clean_visible_object(
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
            )
            handled_handles.add(handle)
            agent_memory["decisions"].append(
                {
                    "object_id": handle,
                    "category": detection.get("category"),
                    "from_fixture_id": support.get("fixture_id"),
                    "to_fixture_id": target_fixture_id,
                    "reason": _decision_reason(perception_mode),
                    "perception_source": detection.get("perception_source", "visible_detection"),
                    "model_provenance": detection.get("model_provenance"),
                    "source_observation_id": detection.get("source_observation_id"),
                }
            )

    done = _call_tool(
        trace_events,
        started_at,
        "done",
        {"reason": f"{policy_name} complete"},
        lambda: contract.done(f"{policy_name} complete"),
    )

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
    private_evaluation_path = output_dir / "private_evaluation.json"
    agent_view = contract.agent_view_payload()
    private_evaluation = contract.private_evaluation_payload(done["score"])
    private_evaluation["requested_generated_mess_count"] = generated_mess_count
    advisory_evaluation = build_advisory_evaluation(
        score=done["score"],
        scenario_id=scenario.scenario_id,
    )
    agent_view_path.write_text(json.dumps(agent_view, indent=2, sort_keys=True) + "\n")
    private_evaluation_path.write_text(
        json.dumps(private_evaluation, indent=2, sort_keys=True) + "\n"
    )
    advisory_evaluation_path = output_dir / "advisory_evaluation.json"
    advisory_evaluation_path.write_text(
        json.dumps(advisory_evaluation, indent=2, sort_keys=True) + "\n"
    )
    substeps = semantic_substeps(trace_events, contract.public_receptacles_by_id())
    cleanup_primitive_evidence = cleanup_primitive_evidence_from_substeps(substeps)

    primitive_summary = primitive_provenance_counts(trace_events)
    public_tool_counts = _tool_event_counts(trace_events)
    run_result = {
        "backend": backend,
        "scenario_id": scenario.scenario_id,
        "seed": seed,
        "task_prompt": task_prompt,
        "contract": REALWORLD_CONTRACT,
        "adr_0003_satisfied": True,
        "final_status": done["cleanup_status"],
        "terminate_reason": f"{policy_name} complete",
        "cleanup_status": done["cleanup_status"],
        "completion_status": done["score"]["completion_status"],
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "primitive_provenance_summary": primitive_summary,
        "manipulation_evidence": api_semantic_manipulation_evidence(
            backend=backend,
            primitive_summary=primitive_summary,
        ),
        "policy": policy_name,
        "planner": policy_name,
        "agent_driven": False,
        "policy_uses_private_truth": False,
        "planner_uses_private_manifest": False,
        "fixture_hint_mode": fixture_hint_mode,
        "perception_mode": perception_mode,
        "requested_generated_mess_count": generated_mess_count,
        "generated_mess_count": private_evaluation["generated_mess_count"],
        "mess_restoration_rate": done["score"]["mess_restoration_rate"],
        "sweep_coverage_rate": done["score"]["sweep_coverage_rate"],
        "disturbance_count": done["score"]["disturbance_count"],
        "semantic_loop_variant": SEMANTIC_LOOP_VARIANT,
        "semantic_substeps": substeps,
        "cleanup_primitive_evidence": cleanup_primitive_evidence,
        "agent_view": agent_view,
        "raw_fpv_observations": agent_view.get("raw_fpv_observations", []),
        "camera_model_policy_evidence": agent_view.get("camera_model_policy_evidence", {}),
        "agent_memory": agent_memory,
        "private_evaluation": private_evaluation,
        "advisory_evaluation": advisory_evaluation,
        "score": done["score"],
        "final_locations": done["final_locations"],
        "final_containment": done.get("final_containment", {}),
        "tool_event_counts": public_tool_counts,
        "backend_tool_event_counts": done["tool_event_counts"],
        "artifacts": {
            "agent_view": str(agent_view_path),
            "private_evaluation": str(private_evaluation_path),
            "advisory_evaluation": str(advisory_evaluation_path),
            "trace": str(trace_path),
            "before_snapshot": str(before_snapshot),
            "after_snapshot": str(after_snapshot),
        },
    }
    if backend_instance is not None:
        run_result["molmospaces_runtime"] = {
            "python_executable": str(backend_instance.python_executable),
            "runtime": backend_instance.runtime,
            "model_stats": backend_instance.model_stats,
            "scene_xml": backend_instance.scene_xml,
            "metadata_object_count": backend_instance.metadata_object_count,
            "requested_generated_mess_count": backend_instance.requested_generated_mess_count,
            "generated_mess_count": backend_instance.generated_mess_count,
        }
        if getattr(backend_instance, "robot", None) is not None:
            run_result["robot"] = backend_instance.robot
            run_result["robot_name"] = backend_instance.robot.get("robot_name")
    if robot_view_steps:
        run_result["view_variant"] = ROBOT_VIEW_VARIANT
        run_result["robot_view_steps"] = robot_view_steps
        run_result["artifacts"]["robot_views"] = str(output_dir / "robot_views")
    if planner_proof_run_result is not None:
        run_result["planner_backed_manipulation_proof"] = attach_planner_proof(
            proof_run_result_path=planner_proof_run_result,
            cleanup_run_dir=output_dir,
        )
        run_result["artifacts"]["planner_proof_views"] = str(output_dir / "planner_proof")

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


def _detections_for_policy(
    *,
    trace_events: list[dict[str, Any]],
    started_at: float,
    contract: RealWorldCleanupContract,
    observation: dict[str, Any],
    perception_mode: str,
) -> list[dict[str, Any]]:
    if perception_mode != CAMERA_MODEL_POLICY_MODE:
        return list(observation.get("visible_object_detections", []))
    raw = observation.get("raw_fpv_observation") or {}
    candidates = _call_tool(
        trace_events,
        started_at,
        "infer_camera_model_candidates",
        {"observation_id": raw.get("observation_id", "")},
        lambda: contract.infer_camera_model_candidates(str(raw.get("observation_id", ""))),
    )
    return list(candidates.get("camera_model_candidates", []))


def _decision_reason(perception_mode: str) -> str:
    if perception_mode == CAMERA_MODEL_POLICY_MODE:
        return "camera model category/fixture affordance heuristic"
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
    base_contract: MolmoCleanupToolContract,
    detection: dict[str, Any],
    target_fixture: dict[str, Any],
    robot_view_steps: list[dict[str, Any]],
    output_dir: Path,
    view_index: int,
    record_robot_views: bool,
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
            focus_receptacle_id=capture.get("focus_receptacle_id"),
            semantic_phase=capture.get("semantic_phase"),
        )

    run_semantic_cleanup_loop(
        targets=[
            {
                "object_id": handle,
                "target_receptacle_id": target_fixture_id,
                "target_receptacle": target_fixture,
            }
        ],
        contract=contract,
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

    return view_index


def _write_snapshot(
    *,
    backend: str,
    contract: MolmoCleanupToolContract,
    scenario: Any,
    output_path: Path,
    title: str,
) -> Path:
    if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        return contract.backend.write_snapshot(output_path, title=title)
    return write_state_snapshot(
        scenario,
        contract.backend.object_locations(),
        output_path,
        title=title,
    )


def _internal_object_id(contract: RealWorldCleanupContract, handle: str) -> str | None:
    return contract._internal_object_id(handle)


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
    base_contract: MolmoCleanupToolContract,
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
        record_robot_views=args.record_robot_views,
        generated_mess_count=args.generated_mess_count,
        planner_proof_run_result=args.planner_proof_run_result,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

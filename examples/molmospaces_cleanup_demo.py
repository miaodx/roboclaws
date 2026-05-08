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

from roboclaws.molmo_cleanup.backend import API_SEMANTIC_PROVENANCE  # noqa: E402
from roboclaws.molmo_cleanup.mcp_contract import MolmoCleanupToolContract  # noqa: E402
from roboclaws.molmo_cleanup.policy import build_public_cleanup_plan  # noqa: E402
from roboclaws.molmo_cleanup.report import (  # noqa: E402
    render_cleanup_report,
    write_state_snapshot,
    write_trace_jsonl,
)
from roboclaws.molmo_cleanup.scenario import (  # noqa: E402
    build_cleanup_scenario,
    write_scenario_bundle,
)
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
)

DEFAULT_PROMPT = "帮我整理这个房间"
SCRIPTED_REFERENCE = "scripted_reference"
PUBLIC_HEURISTIC = "public_heuristic"
SYNTHETIC_BACKEND = "api_semantic_synthetic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MolmoSpaces cleanup pilot demo.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--restore-count", type=int, default=5)
    parser.add_argument("--task", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--backend",
        choices=(SYNTHETIC_BACKEND, MOLMOSPACES_SUBPROCESS_BACKEND),
        default=SYNTHETIC_BACKEND,
    )
    parser.add_argument(
        "--planner",
        choices=(SCRIPTED_REFERENCE, PUBLIC_HEURISTIC),
        default=SCRIPTED_REFERENCE,
    )
    parser.add_argument("--include-robot", action="store_true")
    parser.add_argument("--robot-name", default="rby1m")
    parser.add_argument("--record-robot-views", action="store_true")
    return parser.parse_args(argv)


def run_demo(
    *,
    output_dir: Path,
    seed: int = 7,
    restore_count: int = 5,
    planner: str = SCRIPTED_REFERENCE,
    task_prompt: str = DEFAULT_PROMPT,
    backend: str = SYNTHETIC_BACKEND,
    include_robot: bool = False,
    robot_name: str = "rby1m",
    record_robot_views: bool = False,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    backend_instance: Any | None = None
    if include_robot and backend != MOLMOSPACES_SUBPROCESS_BACKEND:
        raise ValueError("robot inclusion requires backend=molmospaces_subprocess")
    if backend == MOLMOSPACES_SUBPROCESS_BACKEND:
        backend_instance = MolmoSpacesSubprocessBackend(
            run_dir=output_dir,
            seed=seed,
            include_robot=include_robot,
            robot_name=robot_name,
        )
        scenario = backend_instance.scenario
    else:
        scenario = build_cleanup_scenario(seed=seed)
    paths = write_scenario_bundle(output_dir, scenario)
    contract = MolmoCleanupToolContract(scenario, backend=backend_instance)
    trace_events: list[dict[str, Any]] = []
    started_at = time.time()

    before_snapshot = _write_snapshot(
        backend=backend,
        contract=contract,
        scenario=scenario,
        output_path=output_dir / "before.png",
        title="Before cleanup",
    )
    robot_view_steps: list[dict[str, Any]] = []
    if record_robot_views:
        _record_robot_views(robot_view_steps, contract, output_dir, "0000_before", "before")

    _call_tool(trace_events, started_at, "observe", {}, contract.observe)
    if record_robot_views:
        _record_robot_views(robot_view_steps, contract, output_dir, "0001_observe", "observe")
    scene_objects = _call_tool(
        trace_events,
        started_at,
        "scene_objects",
        {},
        contract.scene_objects,
    )
    if record_robot_views:
        _record_robot_views(
            robot_view_steps,
            contract,
            output_dir,
            "0002_scene_objects",
            "scene_objects",
        )
    cleanup_plan, uses_private_manifest = _build_cleanup_plan(
        planner=planner,
        task_prompt=task_prompt,
        scene_objects=scene_objects,
        scenario=scenario,
        restore_count=restore_count,
    )

    view_index = 3
    for action_index, action in enumerate(cleanup_plan, start=1):
        object_id = action["object_id"]
        target_receptacle_id = action["receptacle_id"]
        _call_tool(
            trace_events,
            started_at,
            "goto",
            {"object_id": object_id, "receptacle_id": target_receptacle_id},
            lambda target=target_receptacle_id: contract.goto(target),
        )
        if record_robot_views:
            _record_robot_views(
                robot_view_steps,
                contract,
                output_dir,
                f"{view_index:04d}_goto_{action_index}",
                f"goto {target_receptacle_id}",
                focus_object_id=object_id,
                focus_receptacle_id=target_receptacle_id,
            )
            view_index += 1
        _call_tool(
            trace_events,
            started_at,
            "pick",
            {"object_id": object_id},
            lambda selected_object=object_id: contract.pick(selected_object),
        )
        _call_tool(
            trace_events,
            started_at,
            "place",
            {"receptacle_id": target_receptacle_id},
            lambda target=target_receptacle_id: contract.place(target),
        )
        if record_robot_views:
            _record_robot_views(
                robot_view_steps,
                contract,
                output_dir,
                f"{view_index:04d}_place_{action_index}",
                f"place {object_id}",
                focus_object_id=object_id,
                focus_receptacle_id=target_receptacle_id,
            )
            view_index += 1

    done = _call_tool(
        trace_events,
        started_at,
        "done",
        {"reason": f"{planner} cleanup complete"},
        lambda: contract.done(f"{planner} cleanup complete"),
    )

    after_snapshot = _write_snapshot(
        backend=backend,
        contract=contract,
        scenario=scenario,
        output_path=output_dir / "after.png",
        title="After cleanup",
    )
    if record_robot_views:
        _record_robot_views(
            robot_view_steps,
            contract,
            output_dir,
            f"{view_index:04d}_after",
            "after",
        )
    trace_path = output_dir / "trace.jsonl"
    write_trace_jsonl(trace_path, trace_events)

    run_result = {
        "backend": backend,
        "scenario_id": scenario.scenario_id,
        "seed": seed,
        "task_prompt": task_prompt,
        "final_status": done["cleanup_status"],
        "terminate_reason": f"{planner} cleanup complete",
        "cleanup_status": done["cleanup_status"],
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
        "primitive_provenance_summary": {
            API_SEMANTIC_PROVENANCE: sum(
                1
                for event in trace_events
                if event.get("event") == "response"
                and isinstance(event.get("response"), dict)
                and event["response"].get("primitive_provenance") == API_SEMANTIC_PROVENANCE
            )
        },
        "planner": planner,
        "planner_uses_private_manifest": uses_private_manifest,
        "scripted_reference_uses_private_manifest": uses_private_manifest
        if planner == SCRIPTED_REFERENCE
        else False,
        "cleanup_plan": cleanup_plan,
        "score": done["score"],
        "final_locations": done["final_locations"],
        "tool_event_counts": done["tool_event_counts"],
        "artifacts": {
            "scenario": str(paths["scenario"]),
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
        }
        if getattr(backend_instance, "robot", None) is not None:
            run_result["robot"] = backend_instance.robot
            run_result["robot_name"] = backend_instance.robot.get("robot_name")
    if robot_view_steps:
        run_result["view_variant"] = "molmospaces-rby1m-fpv-map-chase-verify"
        run_result["robot_view_steps"] = robot_view_steps
        run_result["artifacts"]["robot_views"] = str(output_dir / "robot_views")
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


def _build_cleanup_plan(
    *,
    planner: str,
    task_prompt: str,
    scene_objects: dict[str, Any],
    scenario: Any,
    restore_count: int,
) -> tuple[list[dict[str, str]], bool]:
    if planner == SCRIPTED_REFERENCE:
        return (
            [
                {
                    "object_id": rule.object_id,
                    "receptacle_id": rule.valid_receptacle_ids[0],
                    "reason": "private manifest reference target",
                }
                for rule in scenario.private_manifest.targets[:restore_count]
            ],
            True,
        )
    if planner == PUBLIC_HEURISTIC:
        actions = build_public_cleanup_plan(
            task_prompt=task_prompt,
            scene_payload=scene_objects,
        )
        return ([action.to_dict() for action in actions[:restore_count]], False)
    raise ValueError(f"unknown cleanup planner: {planner}")


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


def _record_robot_views(
    steps: list[dict[str, Any]],
    contract: MolmoCleanupToolContract,
    output_dir: Path,
    label: str,
    action: str,
    *,
    focus_object_id: str | None = None,
    focus_receptacle_id: str | None = None,
) -> None:
    result = contract.backend.write_robot_views(
        output_dir / "robot_views",
        label=label,
        focus_object_id=focus_object_id,
        focus_receptacle_id=focus_receptacle_id,
    )
    if not result.get("ok"):
        raise RuntimeError(f"robot view capture failed: {result}")
    steps.append(
        {
            "label": label,
            "action": action,
            "robot_pose": result.get("robot_pose"),
            "robot_trajectory_count": len(result.get("robot_trajectory", [])),
            "view_variant": result.get("view_variant"),
            "view_provenance": result.get("view_provenance"),
            "focus": result.get("focus"),
            "room_outline_count": result.get("room_outline_count"),
            "views": _relative_view_paths(output_dir, result["views"]),
        }
    )


def _relative_view_paths(output_dir: Path, views: dict[str, str]) -> dict[str, str]:
    relative = {}
    for key, value in views.items():
        path = Path(value)
        try:
            relative[key] = str(path.relative_to(output_dir))
        except ValueError:
            relative[key] = str(path)
    return relative


def _call_tool(
    events: list[dict[str, Any]],
    started_at: float,
    tool: str,
    request: dict[str, Any],
    fn: Any,
) -> dict[str, Any]:
    events.append(_trace_event(started_at, tool=tool, event="request", request=request))
    response = fn()
    events.append(_trace_event(started_at, tool=tool, event="response", response=response))
    return response


def _trace_event(started_at: float, *, tool: str, event: str, **payload: Any) -> dict[str, Any]:
    now = time.time()
    return {
        "ts": now,
        "wallclock_elapsed": round(now - started_at, 6),
        "tool": tool,
        "event": event,
        **payload,
    }


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = run_demo(
        output_dir=args.output_dir,
        seed=args.seed,
        restore_count=args.restore_count,
        planner=args.planner,
        task_prompt=args.task,
        backend=args.backend,
        include_robot=args.include_robot,
        robot_name=args.robot_name,
        record_robot_views=args.record_robot_views,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

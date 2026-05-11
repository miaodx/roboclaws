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

DEFAULT_PROMPT = "帮我整理这个房间"
SCRIPTED_REFERENCE = "scripted_reference"
PUBLIC_HEURISTIC = "public_heuristic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the MolmoSpaces cleanup pilot demo.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--restore-count", type=int, default=5)
    parser.add_argument("--task", default=DEFAULT_PROMPT)
    parser.add_argument(
        "--planner",
        choices=(SCRIPTED_REFERENCE, PUBLIC_HEURISTIC),
        default=SCRIPTED_REFERENCE,
    )
    return parser.parse_args(argv)


def run_demo(
    *,
    output_dir: Path,
    seed: int = 7,
    restore_count: int = 5,
    planner: str = SCRIPTED_REFERENCE,
    task_prompt: str = DEFAULT_PROMPT,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    scenario = build_cleanup_scenario(seed=seed)
    paths = write_scenario_bundle(output_dir, scenario)
    contract = MolmoCleanupToolContract(scenario)
    trace_events: list[dict[str, Any]] = []
    started_at = time.time()

    before_snapshot = write_state_snapshot(
        scenario,
        contract.backend.object_locations(),
        output_dir / "before.png",
        title="Before cleanup",
    )

    _call_tool(trace_events, started_at, "observe", {}, contract.observe)
    scene_objects = _call_tool(
        trace_events,
        started_at,
        "scene_objects",
        {},
        contract.scene_objects,
    )
    cleanup_plan, uses_private_manifest = _build_cleanup_plan(
        planner=planner,
        task_prompt=task_prompt,
        scene_objects=scene_objects,
        scenario=scenario,
        restore_count=restore_count,
    )

    for action in cleanup_plan:
        object_id = action["object_id"]
        target_receptacle_id = action["receptacle_id"]
        _call_tool(
            trace_events,
            started_at,
            "goto",
            {"object_id": object_id, "receptacle_id": target_receptacle_id},
            lambda target=target_receptacle_id: contract.goto(target),
        )
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

    done = _call_tool(
        trace_events,
        started_at,
        "done",
        {"reason": f"{planner} cleanup complete"},
        lambda: contract.done(f"{planner} cleanup complete"),
    )

    after_snapshot = write_state_snapshot(
        scenario,
        contract.backend.object_locations(),
        output_dir / "after.png",
        title="After cleanup",
    )
    trace_path = output_dir / "trace.jsonl"
    write_trace_jsonl(trace_path, trace_events)

    run_result = {
        "scenario_id": scenario.scenario_id,
        "task_prompt": task_prompt,
        "cleanup_status": done["cleanup_status"],
        "primitive_provenance": API_SEMANTIC_PROVENANCE,
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
    report_path = render_cleanup_report(
        run_dir=output_dir,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
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
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

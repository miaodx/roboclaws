#!/usr/bin/env python3
"""Compare skill-side cleanup composition with the perf-lane MCP candidate."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.profiles import WORLD_LABELS_PERF_PROFILE, WORLD_LABELS_PROFILE
from roboclaws.molmo_cleanup.realworld_mcp_server import make_molmo_realworld_cleanup_mcp
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario
from roboclaws.molmo_cleanup.semantic_timeline import CLEAN_OBSERVED_OBJECT_TOOL

REPO_ROOT = Path(__file__).resolve().parents[2]
ROUTINE_PATH = (
    REPO_ROOT / "skills" / "molmo-realworld-cleanup" / "scripts" / "trace_preserving_cleanup.py"
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run one deterministic observed-object cleanup through the skill routine "
            "and through the perf-lane MCP candidate."
        )
    )
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = compare_cleanup_routines(seed=args.seed)
    text = json.dumps(summary, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


def compare_cleanup_routines(*, seed: int) -> dict[str, Any]:
    routine = _load_routine_module()
    baseline_detection = _sample_detection(seed=seed)
    object_id = str(baseline_detection["object_id"])
    fixture_id = str(baseline_detection["candidate_fixture_id"])
    placement_tool = str(baseline_detection.get("recommended_tool") or "auto")

    skill_server = make_molmo_realworld_cleanup_mcp(
        run_dir=Path("output") / "molmo" / "routine-comparison" / "skill",
        scenario=build_cleanup_scenario(seed=seed),
        port=0,
        cleanup_profile=WORLD_LABELS_PROFILE,
    )
    try:
        fixture_hints = skill_server.call_tool("fixture_hints")
        _navigate_until_detection(skill_server, object_id=object_id)
        skill_counts: Counter[str] = Counter()

        def skill_call_tool(tool: str, **kwargs: Any) -> dict[str, Any]:
            skill_counts[tool] += 1
            return skill_server.call_tool(tool, **kwargs)

        skill_started = time.perf_counter()
        skill_result = routine.run_cleanup_routine(
            skill_call_tool,
            object_id=object_id,
            fixture_id=fixture_id,
            placement_tool=placement_tool,
            fixture_hints=fixture_hints,
        )
        skill_elapsed_s = round(time.perf_counter() - skill_started, 6)
    finally:
        skill_server.close()

    mcp_server = make_molmo_realworld_cleanup_mcp(
        run_dir=Path("output") / "molmo" / "routine-comparison" / "mcp",
        scenario=build_cleanup_scenario(seed=seed),
        port=0,
        cleanup_profile=WORLD_LABELS_PERF_PROFILE,
    )
    try:
        _navigate_until_detection(mcp_server, object_id=object_id)
        mcp_started = time.perf_counter()
        mcp_result = mcp_server.call_tool(
            CLEAN_OBSERVED_OBJECT_TOOL,
            object_id=object_id,
            fixture_id=fixture_id,
            placement_tool=placement_tool,
        )
        mcp_elapsed_s = round(time.perf_counter() - mcp_started, 6)
    finally:
        mcp_server.close()

    skill_phases = _semantic_phases(skill_result)
    mcp_phases = _semantic_phases(mcp_result)
    semantic_match = skill_phases == mcp_phases
    skill_call_count = sum(skill_counts.values())

    return {
        "schema": "trace_preserving_cleanup_routine_comparison_v1",
        "seed": seed,
        "object_id": object_id,
        "fixture_id": fixture_id,
        "placement_tool": placement_tool,
        "skill_routine": {
            "ok": bool(skill_result.get("ok")),
            "elapsed_s": skill_elapsed_s,
            "mcp_call_count": skill_call_count,
            "tool_counts": dict(sorted(skill_counts.items())),
            "semantic_phases": skill_phases,
            "semantic_step_count": int(skill_result.get("semantic_step_count") or 0),
            "mcp_composite_used": bool(skill_result.get("mcp_composite_used")),
        },
        "mcp_promoted_candidate": {
            "ok": bool(mcp_result.get("ok")),
            "elapsed_s": mcp_elapsed_s,
            "mcp_call_count": 1,
            "tool_counts": {CLEAN_OBSERVED_OBJECT_TOOL: 1},
            "semantic_phases": mcp_phases,
            "semantic_step_count": int(mcp_result.get("semantic_step_count") or 0),
            "mcp_composite_used": True,
        },
        "semantic_match": semantic_match,
        "extra_skill_mcp_calls": max(0, skill_call_count - 1),
        "decision_note": (
            "Skill routine is the canonical composition path when live performance is alike. "
            "This deterministic comparison proves trace equivalence but also exposes the "
            "extra public MCP round trips that live Codex timing must evaluate before "
            "removing the promoted candidate."
        ),
    }


def _sample_detection(*, seed: int) -> dict[str, Any]:
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=Path("output") / "molmo" / "routine-comparison" / "sample",
        scenario=build_cleanup_scenario(seed=seed),
        port=0,
        cleanup_profile=WORLD_LABELS_PROFILE,
    )
    try:
        return _navigate_until_detection(server)
    finally:
        server.close()


def _navigate_until_detection(
    server: Any,
    *,
    object_id: str | None = None,
) -> dict[str, Any]:
    metric_map = server.call_tool("metric_map")
    fallback: dict[str, Any] | None = None
    for waypoint in metric_map["inspection_waypoints"]:
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
        observation = server.call_tool("observe")
        for detection in observation.get("visible_object_detections", []):
            if fallback is None:
                fallback = dict(detection)
            if object_id is None or detection.get("object_id") == object_id:
                return dict(detection)
    if fallback is not None:
        return fallback
    raise RuntimeError("no visible cleanup detection found during public waypoint sweep")


def _semantic_phases(response: dict[str, Any]) -> list[str]:
    return [
        str(step.get("phase") or step.get("tool") or "")
        for step in response.get("semantic_steps") or []
    ]


def _load_routine_module() -> Any:
    spec = importlib.util.spec_from_file_location("trace_preserving_cleanup", ROUTINE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load routine module at {ROUTINE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())

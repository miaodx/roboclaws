from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.profiles import WORLD_LABELS_PROFILE
from roboclaws.molmo_cleanup.realworld_mcp_server import make_molmo_realworld_cleanup_mcp
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario

ROOT = Path(__file__).resolve().parents[3]
ROUTINE_PATH = (
    ROOT / "skills" / "molmo-realworld-cleanup" / "scripts" / "trace_preserving_cleanup.py"
)


def _load_routine_module() -> Any:
    spec = importlib.util.spec_from_file_location("trace_preserving_cleanup", ROUTINE_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _first_detection(server: Any) -> dict[str, Any]:
    metric_map = server.call_tool("metric_map")
    for waypoint in metric_map["inspection_waypoints"]:
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
        observation = server.call_tool("observe")
        detections = observation.get("visible_object_detections", [])
        if detections:
            return dict(detections[0])
    raise AssertionError("expected at least one visible detection")


def test_trace_preserving_skill_routine_uses_atomic_public_mcp_tools(tmp_path: Path) -> None:
    routine = _load_routine_module()
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        cleanup_profile=WORLD_LABELS_PROFILE,
    )
    try:
        fixture_hints = server.call_tool("fixture_hints")
        detection = _first_detection(server)
        cleaned = routine.run_cleanup_routine(
            server.call_tool,
            object_id=detection["object_id"],
            fixture_id=detection["candidate_fixture_id"],
            placement_tool=detection.get("recommended_tool") or "auto",
            fixture_hints=fixture_hints,
        )
    finally:
        server.close()

    trace_text = (tmp_path / "trace.jsonl").read_text(encoding="utf-8")
    phases = [step["phase"] for step in cleaned["semantic_steps"]]

    assert cleaned["ok"] is True
    assert cleaned["routine"] == "canonical_cleanup_routine_v1"
    assert cleaned["mcp_composite_used"] is False
    assert cleaned["composite_preserves_semantic_substeps"] is True
    assert phases[:3] == ["navigate_to_object", "pick", "navigate_to_receptacle"]
    assert {"place", "place_inside"}.intersection(phases)
    assert '"tool": "clean_observed_object"' not in trace_text


def test_trace_preserving_skill_routine_plans_public_open_close_from_fixture_hints(
    tmp_path: Path,
) -> None:
    routine = _load_routine_module()
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
    )
    try:
        fixture_hints = server.call_tool("fixture_hints")
    finally:
        server.close()

    assert routine.routine_plan(
        fixture_id="fridge_01",
        placement_tool="auto",
        fixture_hints=fixture_hints,
    ) == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "open_receptacle",
        "place_inside",
        "close_receptacle",
    ]
    assert routine.routine_plan(
        fixture_id="sink_01",
        placement_tool="auto",
        fixture_hints=fixture_hints,
    ) == ["navigate_to_object", "pick", "navigate_to_receptacle", "place"]


def test_trace_preserving_skill_routine_records_recovery_substeps() -> None:
    routine = _load_routine_module()
    calls: list[tuple[str, dict[str, Any]]] = []
    pick_attempts = 0

    def call_tool(tool: str, **kwargs: Any) -> dict[str, Any]:
        nonlocal pick_attempts
        calls.append((tool, kwargs))
        if tool == "pick":
            pick_attempts += 1
            if pick_attempts == 1:
                return {
                    "ok": False,
                    "tool": "pick",
                    "status": "error",
                    "error_reason": "semantic_order",
                    "required_tool": "navigate_to_object",
                    "recovery_hint": "navigate first",
                }
        return {"ok": True, "tool": tool, "status": "ok"}

    cleaned = routine.run_cleanup_routine(
        call_tool,
        object_id="observed_001",
        fixture_id="sink_01",
        placement_tool="place",
    )

    assert cleaned["ok"] is True
    assert [tool for tool, _ in calls] == [
        "navigate_to_object",
        "pick",
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "place",
    ]
    assert json.dumps(cleaned["semantic_steps"])
    assert any(step.get("skill_recovery_for_phase") == "pick" for step in cleaned["semantic_steps"])
    assert any(step.get("skill_recovery_retry") is True for step in cleaned["semantic_steps"])

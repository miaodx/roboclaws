from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

from roboclaws.household.cleanup_routine import routine_plan
from roboclaws.household.profiles import WORLD_LABELS_PROFILE
from roboclaws.household.realworld_contract import MINIMAL_MAP_MODE
from roboclaws.household.realworld_mcp_server import make_molmo_realworld_cleanup_mcp
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.semantic_timeline import (
    FOCUSED_SEMANTIC_PHASES,
    successful_semantic_phases,
)

ROOT = Path(__file__).resolve().parents[3]
ROUTINE_PATH = (
    ROOT / "skills" / "molmo-realworld-cleanup" / "scripts" / "trace_preserving_cleanup.py"
)
SKILL_PATH = ROOT / "skills" / "molmo-realworld-cleanup" / "SKILL.md"


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


def _first_detection_by_category(server: Any, category: str) -> dict[str, Any]:
    metric_map = server.call_tool("metric_map")
    for waypoint in metric_map["inspection_waypoints"]:
        server.call_tool("navigate_to_waypoint", waypoint_id=waypoint["waypoint_id"])
        observation = server.call_tool("observe")
        for detection in observation.get("visible_object_detections", []):
            if detection.get("category") == category:
                return dict(detection)
    raise AssertionError(f"expected at least one visible {category} detection")


def test_cleanup_skill_prioritizes_done_over_optional_reclean_loops() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    compact = " ".join(text.split())

    assert "call `done` as the authoritative closeout probe" in compact
    assert "clean exactly those listed handles using their `candidate_fixture_id`" in compact
    assert "or `destination_options`, then call `done` again" in compact
    assert "top-level `required_tool` or `completion.blockers[*].required_tool`" in compact
    assert "continue the waypoint sweep rather than inventing fixture ids" in compact
    assert "first complete an anchor discovery sweep" not in compact
    assert "before the first pick" not in compact
    assert "`already_handled`" in compact
    assert "same stale area" in compact


def test_trace_preserving_skill_routine_uses_atomic_public_mcp_tools(tmp_path: Path) -> None:
    routine = _load_routine_module()
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        evidence_lane=WORLD_LABELS_PROFILE,
        map_mode=MINIMAL_MAP_MODE,
    )
    try:
        detection = _first_detection_by_category(server, "food")
        fixture_hints = {
            "rooms": [
                {
                    "room_id": "runtime_semantic_anchors",
                    "fixtures": [
                        server.contract.public_receptacles_by_id()[
                            str(detection["candidate_fixture_id"])
                        ]
                    ],
                }
            ]
        }
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
    successful_phases = successful_semantic_phases(cleaned["semantic_steps"])
    successful_cleanup_phases = [
        phase for phase in successful_phases if phase in FOCUSED_SEMANTIC_PHASES
    ]

    assert cleaned["ok"] is True
    assert cleaned["routine"] == "canonical_cleanup_routine_v1"
    assert cleaned["mcp_composite_used"] is False
    assert cleaned["composite_preserves_semantic_substeps"] is True
    assert phases[:3] == ["navigate_to_object", "adjust_camera", "observe"]
    assert successful_cleanup_phases[:3] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
    ]
    assert {"place", "place_inside"}.intersection(phases)
    assert any(
        step.get("skill_recovery_for_phase") == "navigate_to_object"
        for step in cleaned["semantic_steps"]
    )
    assert '"tool": "clean_observed_object"' not in trace_text


def test_trace_preserving_skill_routine_plans_public_open_close_from_fixture_hints(
    tmp_path: Path,
) -> None:
    routine = _load_routine_module()
    server = make_molmo_realworld_cleanup_mcp(
        run_dir=tmp_path,
        scenario=build_cleanup_scenario(seed=7),
        port=0,
        map_mode=MINIMAL_MAP_MODE,
    )
    try:
        detection = _first_detection_by_category(server, "food")
        fixture_hints = {
            "rooms": [
                {
                    "room_id": "runtime_semantic_anchors",
                    "fixtures": [
                        server.contract.public_receptacles_by_id()[
                            str(detection["candidate_fixture_id"])
                        ]
                    ],
                }
            ]
        }
    finally:
        server.close()

    assert str(detection["candidate_fixture_id"]).startswith("anchor_fixture_")
    assert routine_plan(
        fixture_id=str(detection["candidate_fixture_id"]),
        placement_tool="auto",
        target_fixture=fixture_hints["rooms"][0]["fixtures"][0],
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

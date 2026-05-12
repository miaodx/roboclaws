#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.report_visual_core import assert_cleanup_report_visual_core
from roboclaws.molmo_cleanup.semantic_timeline import (
    CANONICAL_SURFACE_CLEANUP_PHASES,
    CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT,
    FOCUSED_SEMANTIC_ACTION_PREFIXES,
    OBJECT_DONE_PHASE,
    OPEN_RECEPTACLE_PHASE,
    PLACE_INSIDE_PHASE,
    fridge_sequence_ok,
    has_complete_semantic_sequence,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Molmo agent-bridge run_result.")
    parser.add_argument("run_result", type=Path)
    parser.add_argument("--expect-policy")
    parser.add_argument("--require-agent-driven", action="store_true")
    parser.add_argument("--require-clean", action="store_true")
    parser.add_argument("--require-openclaw-minimum", action="store_true")
    parser.add_argument("--expect-backend")
    parser.add_argument("--expect-robot")
    parser.add_argument("--require-robot-views", action="store_true")
    parser.add_argument("--require-semantic-acceptability", action="store_true")
    parser.add_argument("--compare-rule-result", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.run_result.read_text(encoding="utf-8"))
    _assert_common(data, args.run_result.parent)
    if args.expect_backend is not None:
        assert data.get("backend") == args.expect_backend, data
    if args.expect_robot is not None:
        assert data.get("robot_name") == args.expect_robot, data
        robot = data.get("robot") or {}
        assert robot.get("robot_included") is True, data
        assert robot.get("robot_model_stats", {}).get("nbody", 0) > 0, data
    if args.expect_policy is not None:
        assert data.get("policy") == args.expect_policy, data
    if args.require_agent_driven:
        assert data.get("agent_driven") is True, data
        assert data.get("policy_uses_private_truth") is False, data
    if args.require_clean:
        _assert_clean_agent_run(data, args.run_result.parent)
    if args.require_semantic_acceptability:
        _assert_semantic_acceptability(data, args.run_result.parent)
    if args.require_openclaw_minimum:
        _assert_openclaw_minimum(data)
    if args.require_robot_views:
        _assert_robot_views(data, args.run_result.parent)
    if args.compare_rule_result is not None:
        rule = json.loads(args.compare_rule_result.read_text(encoding="utf-8"))
        _assert_rule_comparison(data, rule)
    print(f"molmo-agent-bridge ok: {args.run_result}")


def _assert_common(data: dict[str, Any], base: Path) -> None:
    assert data.get("contract") == "current_contract", data
    assert data.get("mcp_server") == "molmo_cleanup", data
    assert data.get("adr_0003_satisfied") is False, data
    assert data.get("policy_uses_private_truth") is False, data
    assert data.get("planner_uses_private_manifest") is False, data
    assert data.get("primitive_provenance") == "api_semantic", data
    assert "global_scene_objects" in data.get("current_contract_shortcuts", []), data
    artifacts = data.get("artifacts") or {}
    for key in ("scenario", "trace", "before_snapshot", "after_snapshot", "report"):
        path = _resolve_path(base, artifacts.get(key, ""))
        assert path.is_file(), path
        assert path.stat().st_size > 0, path
    report_text = _resolve_path(base, artifacts["report"]).read_text(encoding="utf-8")
    assert "current_contract" in report_text, report_text[:500]
    assert "ADR-0003" in report_text, report_text[:500]
    assert_cleanup_report_visual_core(
        report_text,
        require_semantic_subphases=bool(data.get("semantic_substeps"))
        and data.get("cleanup_status") == "success",
        require_robot_timeline=bool(data.get("robot_view_steps")),
    )


def _assert_clean_agent_run(data: dict[str, Any], base: Path) -> None:
    score = data.get("score") or {}
    diagnostics = data.get("agent_bridge") or {}
    assert data.get("cleanup_status") == "success", data
    assert score.get("restored_count") == score.get("total_targets") == 5, data
    assert diagnostics.get("stale_reference_errors") == 0, data
    assert diagnostics.get("premature_done") is False, data
    assert diagnostics.get("object_done_count") == score.get("total_targets"), data
    assert diagnostics.get("complete_semantic_substep_objects") == score.get("total_targets"), data
    assert diagnostics.get("fridge_inside_sequence_ok") is True, data
    _assert_semantic_substeps(data)
    _assert_semantic_acceptability(data, base)


def _assert_openclaw_minimum(data: dict[str, Any]) -> None:
    assert data.get("policy") == "openclaw_agent", data
    counts = data.get("tool_event_counts") or {}
    assert int(counts.get("observe:request") or 0) >= 1, data
    assert int(counts.get("scene_objects:request") or 0) >= 1, data
    attempted = (data.get("agent_bridge") or {}).get("attempted_semantic_substeps", 0)
    assert int(attempted) >= 1, data
    artifacts = data.get("artifacts") or {}
    assert artifacts.get("trace"), data


def _assert_rule_comparison(data: dict[str, Any], rule: dict[str, Any]) -> None:
    score = data.get("score") or {}
    rule_score = rule.get("score") or {}
    assert rule.get("planner") == "public_heuristic", rule
    assert rule.get("planner_uses_private_manifest") is False, rule
    assert score.get("restored_count") >= rule_score.get("restored_count"), (data, rule)
    assert data.get("cleanup_status") == rule.get("cleanup_status") == "success", (data, rule)


def _assert_semantic_acceptability(data: dict[str, Any], base: Path) -> None:
    score = data.get("score") or {}
    semantic = score.get("semantic_acceptability") or {}
    assert semantic.get("accepted_count") is not None, data
    assert semantic.get("total_targets") == score.get("total_targets"), data
    assert semantic.get("accepted_count") >= score.get("success_threshold"), data
    counts = semantic.get("counts") or {}
    for level in ("preferred", "acceptable", "questionable", "wrong", "unknown"):
        assert level in counts, data
    rows = score.get("object_results") or []
    assert rows, data
    for row in rows:
        assert "exact_private_match" in row, row
        assert row.get("semantic_acceptability") in {
            "preferred",
            "acceptable",
            "questionable",
            "wrong",
            "unknown",
        }, row
        assert row.get("semantic_reason"), row
        assert row.get("object_category"), row
        assert row.get("actual_receptacle_category"), row
    artifacts = data.get("artifacts") or {}
    report_path = _resolve_path(base, artifacts.get("report", ""))
    report_text = report_path.read_text(encoding="utf-8")
    assert "Semantic acceptability" in report_text, report_text[:500]


def _assert_robot_views(data: dict[str, Any], base: Path) -> None:
    assert data.get("view_variant") == "molmospaces-rby1m-fpv-map-chase-verify", data
    artifacts = data.get("artifacts") or {}
    robot_views_dir = _resolve_path(base, artifacts.get("robot_views", ""))
    assert robot_views_dir.is_dir(), robot_views_dir
    report_path = _resolve_path(base, artifacts.get("report", ""))
    report_text = report_path.read_text(encoding="utf-8")
    assert "Robot View Timeline" in report_text, report_text[:500]
    steps = data.get("robot_view_steps") or []
    assert len(steps) >= 2, data
    focused_actions: set[str] = set()
    for step in steps:
        views = step.get("views") or {}
        assert int(step.get("room_outline_count") or 0) > 0, step
        for key in ("fpv", "chase", "map", "verify"):
            path = _resolve_path(report_path.parent, views[key])
            assert path.is_file(), path
            assert path.stat().st_size > 0, path
        action = str(step.get("action", ""))
        if _is_focused_robot_action(action):
            focused_actions.add(action.split(" ", 1)[0])
            _assert_focused_robot_step(step)
    for expected in CANONICAL_SURFACE_CLEANUP_PHASES:
        assert expected in focused_actions, (expected, focused_actions, data)
    if any(
        item.get("target_receptacle_category") == "Fridge"
        for item in data.get("semantic_substeps") or []
    ):
        assert OPEN_RECEPTACLE_PHASE in focused_actions, data
        assert PLACE_INSIDE_PHASE in focused_actions, data


def _is_focused_robot_action(action: str) -> bool:
    return action.startswith(FOCUSED_SEMANTIC_ACTION_PREFIXES)


def _assert_focused_robot_step(step: dict[str, Any]) -> None:
    action = str(step.get("action", ""))
    focus = step.get("focus") or {}
    pose = step.get("robot_pose") or {}
    assert focus.get("has_focus") is True, step
    assert focus.get("object_id"), step
    assert focus.get("provenance") == "public_mujoco_state_report_aid", step
    assert pose.get("head_pitch_source") == "target_framing_head_pitch", step
    assert pose.get("same_room_as_target") is True, step
    if action.startswith(("open_receptacle ", "place_inside ")) and (
        focus.get("receptacle_category") == "Fridge"
    ):
        assert pose.get("theta_source") == "opened_receptacle_access_yaw", step
    else:
        assert pose.get("theta_source") == "target_facing_base_yaw", step
    fpv_visibility = focus.get("fpv_visibility") or {}
    assert fpv_visibility.get("status") == "ok", step
    assert fpv_visibility.get("boxes"), step
    if action.startswith("navigate_to_object "):
        assert int(fpv_visibility.get("object_pixels") or 0) >= 250, step
        visibility = focus.get("visibility") or {}
        assert int(visibility.get("object_pixels") or 0) >= 100, step
    elif action.startswith("pick "):
        assert focus.get("object_position"), step
    elif action.startswith("navigate_to_receptacle ") and (
        focus.get("object_location_relation") == "held"
    ):
        assert focus.get("object_position"), step
        _assert_held_object_tracks_robot(step)
        assert int(fpv_visibility.get("object_pixels") or 0) >= 100, step
        assert int(fpv_visibility.get("receptacle_pixels") or 0) > 0, step
    else:
        assert focus.get("receptacle_id"), step
        assert int(fpv_visibility.get("receptacle_pixels") or 0) > 0, step
        if focus.get("object_location_relation") == "held":
            _assert_held_object_tracks_robot(step)
    visibility = focus.get("visibility") or {}
    assert visibility.get("status") == "ok", step
    if not action.startswith(("pick ", "place_inside ")):
        assert visibility.get("boxes"), step


def _assert_held_object_tracks_robot(step: dict[str, Any]) -> None:
    focus = step.get("focus") or {}
    pose = step.get("robot_pose") or {}
    object_position = focus.get("object_position") or []
    assert len(object_position) >= 3, step
    assert {"x", "y", "theta"} <= set(pose), step
    expected = [
        float(pose["x"]) + math.cos(float(pose["theta"])) * 0.45,
        float(pose["y"]) + math.sin(float(pose["theta"])) * 0.45,
        1.05,
    ]
    assert math.dist([float(value) for value in object_position[:3]], expected) <= 0.02, step


def _assert_semantic_substeps(data: dict[str, Any]) -> None:
    assert data.get("semantic_loop_variant") == CURRENT_CONTRACT_SEMANTIC_LOOP_VARIANT
    saw_fridge = False
    for item in data.get("semantic_substeps") or []:
        phases = [str(step.get("phase") or "") for step in item.get("steps", [])]
        assert has_complete_semantic_sequence(phases), item
        assert phases[-1:] == [OBJECT_DONE_PHASE], item
        done_step = item["steps"][-1]
        assert done_step.get("matches_expected_location") is True, item
        if item.get("target_receptacle_category") == "Fridge":
            saw_fridge = True
            assert OPEN_RECEPTACLE_PHASE in phases, item
            assert PLACE_INSIDE_PHASE in phases, item
            assert fridge_sequence_ok(phases), item
    assert saw_fridge, data


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    repo_path = Path(__file__).resolve().parents[2] / path
    if repo_path.exists():
        return repo_path
    return base / path


if __name__ == "__main__":
    main()

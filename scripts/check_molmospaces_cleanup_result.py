#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a MolmoSpaces cleanup run_result.")
    parser.add_argument("run_result", type=Path)
    parser.add_argument("--require-public-planner", action="store_true")
    parser.add_argument("--expect-task")
    parser.add_argument("--expect-backend")
    parser.add_argument("--expect-robot")
    parser.add_argument("--require-robot-views", action="store_true")
    parser.add_argument("--require-semantic-substeps", action="store_true")
    parser.add_argument("--require-semantic-acceptability", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    data = json.loads(args.run_result.read_text(encoding="utf-8"))
    score = data["score"]
    assert data["cleanup_status"] == "success", data
    assert data["primitive_provenance"] == "api_semantic", data
    if args.expect_backend is not None:
        assert data.get("backend") == args.expect_backend, data
    if args.expect_robot is not None:
        assert data.get("robot_name") == args.expect_robot, data
        robot = data.get("robot") or {}
        assert robot.get("robot_included") is True, data
        assert robot.get("robot_model_stats", {}).get("nbody", 0) > 0, data
        assert "robot_0/head_camera" in robot.get("robot_camera_names", []), data
    if args.expect_task is not None:
        assert data.get("task_prompt") == args.expect_task, data
    if args.require_public_planner:
        assert data.get("planner") == "public_heuristic", data
        assert data.get("planner_uses_private_manifest") is False, data
    if args.require_semantic_substeps:
        _assert_semantic_substeps(data)
    if args.require_semantic_acceptability:
        _assert_semantic_acceptability(data, args.run_result.parent)
    assert score["restored_count"] >= score["success_threshold"], data
    artifacts = data["artifacts"]
    for key in ("trace", "before_snapshot", "after_snapshot", "report"):
        path = _resolve_path(args.run_result.parent, artifacts[key])
        assert path.is_file(), path
    report = _resolve_path(args.run_result.parent, artifacts["report"])
    assert report.is_file(), report
    if args.require_robot_views:
        steps = data.get("robot_view_steps") or []
        assert len(steps) >= 2, data
        for step in steps:
            views = step.get("views") or {}
            assert int(step.get("room_outline_count") or 0) > 0, step
            for key in ("fpv", "chase", "map", "verify"):
                path = _resolve_path(report.parent, views[key])
                assert path.is_file(), path
                assert path.stat().st_size > 0, path
            if _is_focused_robot_action(str(step.get("action", ""))):
                focus = step.get("focus") or {}
                assert focus.get("has_focus") is True, step
                assert focus.get("object_id"), step
                assert focus.get("provenance") == "public_mujoco_state_report_aid", step
                pose = step.get("robot_pose") or {}
                action = str(step.get("action", ""))
                if action.startswith(("open_receptacle ", "place_inside ")) and (
                    focus.get("receptacle_category") == "Fridge"
                ):
                    assert pose.get("theta_source") == "opened_receptacle_access_yaw", step
                else:
                    assert pose.get("theta_source") == "target_facing_base_yaw", step
                assert pose.get("head_pitch_source") == "target_framing_head_pitch", step
                assert pose.get("same_room_as_target") is True, step
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
                if (
                    str(step.get("action", "")).startswith("place ")
                    and focus.get("object_category") == "Apple"
                ):
                    assert int(visibility.get("object_pixels") or 0) > 0, step
        assert data.get("view_variant") == "molmospaces-rby1m-fpv-map-chase-verify", data
    print(f"molmo-cleanup ok: {args.run_result} -> {report}")


def _assert_semantic_acceptability(data: dict, base: Path) -> None:
    score = data.get("score") or {}
    semantic = score.get("semantic_acceptability") or {}
    assert semantic.get("accepted_count") is not None, data
    assert semantic.get("total_targets") == score.get("total_targets"), data
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
    artifacts = data.get("artifacts") or {}
    report = _resolve_path(base, artifacts.get("report", ""))
    assert "Semantic acceptability" in report.read_text(encoding="utf-8"), data


def _assert_semantic_substeps(data: dict) -> None:
    assert data.get("semantic_loop_variant") == "navigate-pick-navigate-open-place-object_done", (
        data
    )
    semantic_substeps = data.get("semantic_substeps") or []
    assert semantic_substeps, data
    final_containment = data.get("final_containment") or {}
    saw_inside = False
    for item in semantic_substeps:
        phases = [step.get("phase") for step in item.get("steps", [])]
        assert phases[:3] == ["navigate_to_object", "pick", "navigate_to_receptacle"], item
        assert phases[-1:] == ["object_done"], item
        assert "place" in phases or "place_inside" in phases, item
        done_step = item["steps"][-1]
        assert done_step.get("matches_expected_location") is True, item
        if item.get("target_receptacle_category") == "Fridge":
            assert "open_receptacle" in phases, item
            assert "place_inside" in phases, item
            containment = final_containment.get(item["object_id"]) or {}
            assert containment.get("contained_in") == item["target_receptacle_id"], item
            assert containment.get("location_relation") == "inside", item
            assert done_step.get("contained_in") == item["target_receptacle_id"], item
            assert done_step.get("location_relation") == "inside", item
            saw_inside = True
    assert saw_inside, semantic_substeps


def _is_focused_robot_action(action: str) -> bool:
    return action.startswith(
        (
            "navigate_to_object ",
            "pick ",
            "navigate_to_receptacle ",
            "open_receptacle ",
            "place ",
            "place_inside ",
        )
    )


def _assert_held_object_tracks_robot(step: dict) -> None:
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


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    repo_path = Path(__file__).resolve().parents[1] / path
    if repo_path.exists():
        return repo_path
    return base / path


if __name__ == "__main__":
    main()

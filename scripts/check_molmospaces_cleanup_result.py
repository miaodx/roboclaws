#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a MolmoSpaces cleanup run_result.")
    parser.add_argument("run_result", type=Path)
    parser.add_argument("--require-public-planner", action="store_true")
    parser.add_argument("--expect-task")
    parser.add_argument("--expect-backend")
    parser.add_argument("--expect-robot")
    parser.add_argument("--require-robot-views", action="store_true")
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
    assert score["restored_count"] >= score["success_threshold"], data
    report = Path(data["artifacts"]["report"])
    assert report.is_file(), report
    if args.require_robot_views:
        steps = data.get("robot_view_steps") or []
        assert len(steps) >= 2, data
        for step in steps:
            views = step.get("views") or {}
            for key in ("fpv", "chase", "map"):
                path = report.parent / views[key]
                assert path.is_file(), path
        assert data.get("view_variant") == "molmospaces-rby1m-fpv-map-chase", data
    print(f"molmo-cleanup ok: {args.run_result} -> {report}")


if __name__ == "__main__":
    main()

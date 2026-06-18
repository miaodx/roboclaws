#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (
    ALIGNMENT_RESIDUALS_SCHEMA,
    SEMANTIC_SOURCE,
    WAYPOINT_POSE_REQUESTS_SCHEMA,
    residual_backed_waypoint_from_nav_goal,
    validate_alignment_residual_artifact,
    validate_waypoint_pose_requests_artifact,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build residual-backed B1 scene robot pose requests from arbitrary Map12 nav "
            "points. This does not claim planner-backed navigation or physical robot parity."
        )
    )
    parser.add_argument("--alignment-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--points",
        type=Path,
        help=(
            "JSON array of {waypoint_id,x,y,yaw|yaw_deg,label}. Use this for multiple "
            "on-demand navigation points."
        ),
    )
    parser.add_argument("--waypoint-id", default="map12_on_demand_001")
    parser.add_argument("--label", default="")
    parser.add_argument("--x", type=float)
    parser.add_argument("--y", type=float)
    parser.add_argument("--yaw", type=float)
    parser.add_argument("--yaw-deg", type=float)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    requests = build_pose_request_artifact(
        alignment_artifact=args.alignment_artifact,
        points=load_points(args),
    )
    errors = validate_waypoint_pose_requests_artifact(requests)
    requests["validation"] = {
        "status": "passed" if not errors else "failed",
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(requests, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": requests["schema"],
                "status": requests["status"],
                "output": str(args.output),
                "waypoint_count": requests["waypoint_count"],
                "blocked_request_count": requests["blocked_request_count"],
                "errors": errors,
            },
            sort_keys=True,
        )
    )
    return 0 if requests["status"] == "ready" and not errors else 2


def build_pose_request_artifact(
    *,
    alignment_artifact: Path,
    points: list[dict[str, Any]],
) -> dict[str, Any]:
    alignment, artifact_errors = load_alignment_for_requests(alignment_artifact)
    transform = alignment.get("selected_transform") if isinstance(alignment, dict) else {}
    coverage = coverage_decision(alignment)
    if not points:
        artifact_errors = [*artifact_errors, "at least one Map12 point is required"]
    waypoints = []
    blocked_requests = []
    for index, point in enumerate(points, start=1):
        waypoint_id = str(point.get("waypoint_id") or f"map12_on_demand_{index:03d}")
        nav_goal, nav_goal_error = nav_goal_from_point(point)
        if nav_goal_error:
            blocked_requests.append(
                blocked_request_row(
                    point,
                    waypoint_id=waypoint_id,
                    reason=nav_goal_error,
                    nav_goal=nav_goal,
                )
            )
            continue
        if artifact_errors:
            blocked_requests.append(
                blocked_request_row(
                    point,
                    waypoint_id=waypoint_id,
                    reason="; ".join(artifact_errors),
                    nav_goal=nav_goal,
                )
            )
            continue
        if coverage["status"] == "blocked":
            blocked_requests.append(
                blocked_request_row(
                    point,
                    waypoint_id=waypoint_id,
                    reason=str(coverage.get("reason") or "alignment coverage is not verified"),
                    nav_goal=nav_goal,
                    coverage=coverage,
                )
            )
            continue
        waypoint = residual_backed_waypoint_from_nav_goal(
            nav_goal=nav_goal,
            waypoint_id=waypoint_id,
            label=str(point.get("label") or waypoint_id),
            source_anchor_id=str(point.get("source_anchor_id") or ""),
            transform=transform,
            alignment_artifact_path=alignment_artifact,
            coverage_decision=coverage,
        )
        if not waypoint:
            blocked_requests.append(
                blocked_request_row(
                    point,
                    waypoint_id=waypoint_id,
                    reason="point is missing finite x/y",
                    nav_goal=nav_goal,
                    coverage=coverage,
                )
            )
            continue
        waypoints.append(waypoint)
    status = "ready" if waypoints and not blocked_requests and not artifact_errors else "blocked"
    return {
        "schema": WAYPOINT_POSE_REQUESTS_SCHEMA,
        "status": status,
        "semantic_source": SEMANTIC_SOURCE,
        "alignment_artifact": str(alignment_artifact),
        "alignment_transform_source": "reviewed_correspondence_fit" if not artifact_errors else "",
        "selected_transform_type": str(transform.get("type") or ""),
        "source_map_frame": str(transform.get("source_frame") or "robot_map_12_map"),
        "target_scene_frame": str(transform.get("target_frame") or "b1_rebuilt_scene_usd_world"),
        "waypoint_count": len(waypoints),
        "waypoints": waypoints,
        "blocked_request_count": len(blocked_requests),
        "blocked_requests": blocked_requests,
        "artifact_errors": artifact_errors,
        "planner_backed": False,
        "physical_robot": False,
        "robot_navigation_supported": False,
        "robot_navigation_pending_reason": (
            "This artifact only converts Map12 nav goals into residual-backed B1 scene "
            "robot poses. Isaac pose application plus robot-view evidence is still required."
        ),
    }


def load_alignment_for_requests(path: Path) -> tuple[dict[str, Any], list[str]]:
    if not path.is_file():
        return {}, [f"alignment artifact missing: {path}"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != ALIGNMENT_RESIDUALS_SCHEMA:
        return payload, [f"unexpected alignment artifact schema: {payload.get('schema')!r}"]
    errors = validate_alignment_residual_artifact(payload)
    if errors:
        return payload, ["invalid alignment artifact: " + "; ".join(errors)]
    if payload.get("global_alignment_status") != "verified":
        return payload, ["alignment artifact must be globally verified"]
    transform = payload.get("selected_transform")
    if not isinstance(transform, dict) or not transform:
        return payload, ["alignment artifact missing selected_transform"]
    if str(transform.get("source") or "") != "reviewed_correspondence_fit":
        return payload, ["alignment transform must come from reviewed_correspondence_fit"]
    return payload, []


def load_points(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.points is not None:
        payload = json.loads(args.points.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            raise ValueError("--points must be a JSON array")
        return [point if isinstance(point, dict) else {} for point in payload]
    if args.x is None or args.y is None:
        raise ValueError("provide either --points or both --x and --y")
    point = {
        "waypoint_id": args.waypoint_id,
        "label": args.label or args.waypoint_id,
        "x": float(args.x),
        "y": float(args.y),
    }
    if args.yaw is not None:
        point["yaw"] = float(args.yaw)
    if args.yaw_deg is not None:
        point["yaw_deg"] = float(args.yaw_deg)
    return [point]


def coverage_decision(alignment: dict[str, Any]) -> dict[str, Any]:
    if alignment.get("global_alignment_status") == "verified":
        residual = alignment.get("residual_evidence") if isinstance(alignment, dict) else {}
        return {
            "status": "verified_global",
            "fit_scope": "global_transform",
            "matched_anchor_count": int(dict(residual or {}).get("matched_anchor_count") or 0),
            "residual_evidence_status": str(dict(residual or {}).get("status") or ""),
        }
    return {
        "status": "blocked",
        "fit_scope": "global_transform",
        "reason": "alignment artifact is not globally verified",
    }


def blocked_request_row(
    point: dict[str, Any],
    *,
    waypoint_id: str,
    reason: str,
    nav_goal: dict[str, float] | None,
    coverage: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "waypoint_id": waypoint_id,
        "label": str(point.get("label") or waypoint_id),
        "request_status": "blocked",
        "reason": reason,
        "map12_nav_goal": dict(nav_goal or {}),
        "coverage_decision": dict(
            coverage
            or {
                "status": "blocked",
                "fit_scope": "global_transform",
                "reason": reason,
            }
        ),
        "planner_backed": False,
        "physical_robot": False,
    }


def nav_goal_from_point(point: dict[str, Any]) -> tuple[dict[str, float], str]:
    try:
        nav_goal = {"x": float(point["x"]), "y": float(point["y"])}
    except (KeyError, TypeError, ValueError):
        return {}, f"point must contain finite x/y: {point!r}"
    try:
        if "yaw" in point and point.get("yaw") is not None:
            nav_goal["yaw"] = float(point["yaw"])
        if "yaw_deg" in point and point.get("yaw_deg") is not None:
            nav_goal["yaw_deg"] = float(point["yaw_deg"])
    except (TypeError, ValueError):
        return nav_goal, f"point yaw must be finite when provided: {point!r}"
    return nav_goal, ""


if __name__ == "__main__":
    raise SystemExit(main())

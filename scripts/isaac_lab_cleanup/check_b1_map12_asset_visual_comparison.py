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
    NAVIGATION_SMOKE_SCHEMA,
    SEMANTIC_SOURCE,
    _dict,
    reviewable_image_errors,
    validate_robot_view_waypoint_evidence,
)

ASSET_VISUAL_COMPARISON_SCHEMA = "b1_map12_asset_visual_comparison_v1"
DEFAULT_REQUIRED_VIEWS = ("fpv", "chase")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate same-waypoint B1 / Map 12 custom-asset visual comparison artifacts. "
            "This reuses navigation-smoke robot-view evidence without claiming the default "
            "B1_floor2_slow navigation route passed."
        )
    )
    parser.add_argument("--baseline-name", default="v1")
    parser.add_argument("--baseline-navigation", type=Path, required=True)
    parser.add_argument("--candidate-name", default="v2")
    parser.add_argument("--candidate-navigation", type=Path, required=True)
    parser.add_argument("--contact-sheet", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--allow-low-detail",
        action="store_true",
        help=(
            "Keep low-detail FPV/chase findings as warnings instead of failing the "
            "comparison. Missing files, mismatched waypoints, and mismatched poses still fail."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    artifact = build_asset_visual_comparison(
        baseline_name=args.baseline_name,
        baseline_navigation_path=args.baseline_navigation,
        candidate_name=args.candidate_name,
        candidate_navigation_path=args.candidate_navigation,
        contact_sheet=args.contact_sheet,
        allow_low_detail=bool(args.allow_low_detail),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": artifact["schema"],
                "status": artifact["status"],
                "output": str(args.output),
                "comparison_ready": artifact["comparison_ready"],
                "waypoint_count": artifact["waypoint_count"],
                "errors": artifact["validation"]["errors"],
                "warning_count": len(artifact["warnings"]),
            },
            sort_keys=True,
        )
    )
    return 0 if artifact["status"] == "passed" else 2


def build_asset_visual_comparison(
    *,
    baseline_name: str,
    baseline_navigation_path: Path,
    candidate_name: str,
    candidate_navigation_path: Path,
    contact_sheet: Path | None = None,
    allow_low_detail: bool = False,
) -> dict[str, Any]:
    baseline = _load_navigation_artifact(baseline_navigation_path)
    candidate = _load_navigation_artifact(candidate_navigation_path)
    errors: list[str] = []
    warnings: list[str] = []
    errors.extend(_navigation_artifact_shape_errors(baseline, label=baseline_name))
    errors.extend(_navigation_artifact_shape_errors(candidate, label=candidate_name))
    baseline_rows = _waypoints_by_id(baseline)
    candidate_rows = _waypoints_by_id(candidate)
    baseline_ids = list(baseline_rows)
    candidate_ids = list(candidate_rows)
    if baseline_ids != candidate_ids:
        errors.append(
            f"waypoint order mismatch: {baseline_name}={baseline_ids}, "
            f"{candidate_name}={candidate_ids}"
        )
    shared_ids = [waypoint_id for waypoint_id in baseline_ids if waypoint_id in candidate_rows]
    scene_baseline = str(baseline.get("b1_scene_usd") or "")
    scene_candidate = str(candidate.get("b1_scene_usd") or "")
    if not scene_baseline:
        errors.append(f"{baseline_name} missing b1_scene_usd")
    if not scene_candidate:
        errors.append(f"{candidate_name} missing b1_scene_usd")
    if scene_baseline and scene_candidate and scene_baseline == scene_candidate:
        errors.append("asset visual comparison requires two distinct render scene USDs")

    errors.extend(
        f"{baseline_name}: {error}"
        for error in validate_robot_view_waypoint_evidence(
            list(baseline_rows.values()),
            require_files=False,
            required_views=DEFAULT_REQUIRED_VIEWS,
            reviewable_views=DEFAULT_REQUIRED_VIEWS,
        )
    )
    errors.extend(
        f"{candidate_name}: {error}"
        for error in validate_robot_view_waypoint_evidence(
            list(candidate_rows.values()),
            require_files=False,
            required_views=DEFAULT_REQUIRED_VIEWS,
            reviewable_views=DEFAULT_REQUIRED_VIEWS,
        )
    )

    rows = []
    for waypoint_id in shared_ids:
        baseline_row = baseline_rows[waypoint_id]
        candidate_row = candidate_rows[waypoint_id]
        pose_errors = _pose_match_errors(
            _dict(baseline_row.get("robot_pose")),
            _dict(candidate_row.get("robot_pose")),
            waypoint_id=waypoint_id,
            baseline_name=baseline_name,
            candidate_name=candidate_name,
        )
        errors.extend(pose_errors)
        image_errors = []
        for label, row in (
            (baseline_name, baseline_row),
            (candidate_name, candidate_row),
        ):
            for view_name in DEFAULT_REQUIRED_VIEWS:
                image_errors.extend(
                    f"{label} {waypoint_id} {view_name}: {error}"
                    for error in _view_image_errors(row, view_name)
                )
        if allow_low_detail:
            hard_errors, soft_warnings = _split_low_detail_errors(image_errors)
            errors.extend(hard_errors)
            warnings.extend(soft_warnings)
        else:
            errors.extend(image_errors)
        rows.append(
            {
                "waypoint_id": waypoint_id,
                "map12_nav_goal": baseline_row.get("map12_nav_goal"),
                "robot_pose": baseline_row.get("robot_pose"),
                "views": {
                    baseline_name: _required_view_paths(baseline_row),
                    candidate_name: _required_view_paths(candidate_row),
                },
            }
        )

    if contact_sheet is not None:
        if contact_sheet.is_file():
            contact_sheet_status = "available"
        else:
            contact_sheet_status = "missing"
            errors.append(f"contact sheet missing: {contact_sheet}")
    else:
        contact_sheet_status = "not_provided"

    status = "passed" if not errors and len(shared_ids) >= 2 else "failed"
    if len(shared_ids) < 2:
        errors.append("asset visual comparison requires at least two shared waypoints")
        status = "failed"
    return {
        "schema": ASSET_VISUAL_COMPARISON_SCHEMA,
        "status": status,
        "comparison_ready": status == "passed",
        "semantic_source": SEMANTIC_SOURCE,
        "comparison_scope": "custom_asset_same_pose_visual_review",
        "baseline": _navigation_summary(
            name=baseline_name,
            path=baseline_navigation_path,
            payload=baseline,
        ),
        "candidate": _navigation_summary(
            name=candidate_name,
            path=candidate_navigation_path,
            payload=candidate,
        ),
        "waypoint_count": len(shared_ids),
        "required_views": list(DEFAULT_REQUIRED_VIEWS),
        "rows": rows,
        "contact_sheet": str(contact_sheet) if contact_sheet else "",
        "contact_sheet_status": contact_sheet_status,
        "navigation_smoke_pass_required": False,
        "default_visual_route_required": False,
        "planner_backed": False,
        "physical_robot": False,
        "warnings": warnings,
        "validation": {
            "status": "passed" if status == "passed" else "failed",
            "errors": errors,
        },
    }


def _load_navigation_artifact(path: Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _navigation_artifact_shape_errors(payload: dict[str, Any], *, label: str) -> list[str]:
    errors: list[str] = []
    if payload.get("schema") != NAVIGATION_SMOKE_SCHEMA:
        errors.append(f"{label} unexpected navigation schema: {payload.get('schema')!r}")
    if payload.get("semantic_source") != SEMANTIC_SOURCE:
        errors.append(f"{label} semantic source must be Map 12 overlay")
    if payload.get("planner_backed") is not False:
        errors.append(f"{label} must not claim planner-backed navigation")
    if payload.get("physical_robot") is not False:
        errors.append(f"{label} must not claim physical robot navigation")
    if payload.get("child_failures"):
        errors.append(f"{label} has child capture failures")
    return errors


def _waypoints_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for item in payload.get("waypoint_evidence") or []:
        if not isinstance(item, dict):
            continue
        waypoint_id = str(item.get("waypoint_id") or "")
        if waypoint_id:
            rows[waypoint_id] = item
    return rows


def _pose_match_errors(
    baseline_pose: dict[str, Any],
    candidate_pose: dict[str, Any],
    *,
    waypoint_id: str,
    baseline_name: str,
    candidate_name: str,
) -> list[str]:
    errors: list[str] = []
    for key in ("x", "y", "z", "yaw_deg"):
        try:
            baseline_value = float(baseline_pose[key])
            candidate_value = float(candidate_pose[key])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{waypoint_id} missing comparable robot_pose.{key}")
            continue
        if abs(baseline_value - candidate_value) > 1e-6:
            errors.append(
                f"{waypoint_id} pose mismatch for {key}: "
                f"{baseline_name}={baseline_value}, {candidate_name}={candidate_value}"
            )
    return errors


def _view_image_errors(row: dict[str, Any], view_name: str) -> list[str]:
    raw_path = _dict(row.get("views")).get(view_name)
    if not raw_path:
        return [f"missing {view_name} image"]
    path = Path(str(raw_path))
    if not path.is_file():
        return [f"view image missing: {path}"]
    return reviewable_image_errors(path)


def _split_low_detail_errors(errors: list[str]) -> tuple[list[str], list[str]]:
    hard_errors = []
    warnings = []
    for error in errors:
        if (
            "image has too little visual detail" in error
            or "image has too few distinct colors" in error
        ):
            warnings.append(error)
        else:
            hard_errors.append(error)
    return hard_errors, warnings


def _required_view_paths(row: dict[str, Any]) -> dict[str, str]:
    views = _dict(row.get("views"))
    return {view_name: str(views.get(view_name) or "") for view_name in DEFAULT_REQUIRED_VIEWS}


def _navigation_summary(*, name: str, path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "navigation_artifact": str(path),
        "navigation_status": str(payload.get("status") or ""),
        "navigation_validation_status": str(_dict(payload.get("validation")).get("status") or ""),
        "scene_usd": str(payload.get("b1_scene_usd") or ""),
        "waypoint_count": int(payload.get("navigation_waypoint_count") or 0),
        "child_failure_count": len(payload.get("child_failures") or []),
    }


if __name__ == "__main__":
    raise SystemExit(main())

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

from roboclaws.core.json_sources import read_gzip_json_object
from roboclaws.maps.bundle_validation import parse_map_yaml
from roboclaws.maps.navigation_memory import (
    navigation_memory_item,
    navigation_memory_items,
    navigation_memory_point_source,
    read_navigation_memory,
)
from roboclaws.maps.rasterize import load_pgm, world_to_grid

DEFAULT_MAP12_ROOT = Path("vendors/agibot_sdk/artifacts/maps/robot_map_12")
SCHEMA = "robot_map12_consistency_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check robot_map_12 Agibot map metadata against navigation_memory.json "
            "without scene or Gaussian inputs."
        )
    )
    parser.add_argument("map12_root", nargs="?", type=Path, default=DEFAULT_MAP12_ROOT)
    parser.add_argument("--json", action="store_true", help="Print machine-readable output.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    result = check_robot_map12_consistency(args.map12_root)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    elif result["ok"]:
        print(
            "robot-map12 consistent: "
            f"{args.map12_root} "
            f"items={result['navigation_memory']['item_count']} "
            f"occupied_nav_goals={len(result['warnings'])}"
        )
    else:
        print(f"robot-map12 inconsistent: {args.map12_root}", file=sys.stderr)
        for error in result["errors"]:
            print(f"- {error}", file=sys.stderr)
    if not result["ok"]:
        raise SystemExit(1)


def check_robot_map12_consistency(map12_root: Path) -> dict[str, Any]:
    map12_root = Path(map12_root)
    agibot_dir = map12_root / "agibot"
    nav2_path = agibot_dir / "nav2.yaml"
    occupancy_path = agibot_dir / "occupancy.pgm"
    raw_map_path = agibot_dir / "raw_map.json.gz"
    navigation_memory_path = map12_root / "navigation_memory.json"
    required = [nav2_path, occupancy_path, raw_map_path, navigation_memory_path]

    errors = [f"missing required artifact: {path}" for path in required if not path.is_file()]
    if errors:
        return _result(map12_root, errors=errors, warnings=[], anchors=[])

    nav2 = parse_map_yaml(nav2_path.read_text(encoding="utf-8"))
    origin = _origin(nav2)
    resolution = float(nav2.get("resolution") or 0.05)
    grid = load_pgm(
        occupancy_path,
        resolution_m=resolution,
        origin_x=origin[0],
        origin_y=origin[1],
    )
    warnings: list[str] = []
    try:
        raw_map = _load_raw_map(raw_map_path)
    except ValueError as exc:
        errors.append(str(exc))
        return _result(map12_root, errors=errors, warnings=warnings, anchors=[])
    errors.extend(_raw_map_metadata_errors(raw_map, grid=grid, yaw=origin[2]))

    map_summary = {
        "frame_id": "map",
        "resolution_m": grid.resolution_m,
        "origin": {"x": grid.origin_x, "y": grid.origin_y, "yaw": origin[2]},
        "width": grid.width,
        "height": grid.height,
    }
    try:
        navigation_memory = read_navigation_memory(navigation_memory_path)
        anchors = [
            _anchor_check(
                navigation_memory_item(raw_item, index=index),
                index=index,
                grid=grid,
            )
            for index, raw_item in enumerate(navigation_memory_items(navigation_memory), start=1)
        ]
    except ValueError as exc:
        errors.append(str(exc))
        return _result(
            map12_root,
            errors=errors,
            warnings=warnings,
            anchors=[],
            map_summary=map_summary,
        )
    for anchor in anchors:
        for field in ("pose", "nav_goal"):
            check = anchor.get(field)
            if not isinstance(check, dict) or not check.get("present"):
                continue
            if not check.get("in_bounds"):
                errors.append(f"{anchor['id']} {field} is outside occupancy grid")
            elif field == "nav_goal" and not check.get("free"):
                warnings.append(f"{anchor['id']} nav_goal is in occupied/unknown cell")

    return _result(
        map12_root,
        errors=errors,
        warnings=warnings,
        anchors=anchors,
        map_summary=map_summary,
        navigation_memory_summary={
            "schema_version": navigation_memory.get("schema_version"),
            "updated_at": str(navigation_memory.get("updated_at") or ""),
            "item_count": len(anchors),
        },
    )


def _result(
    map12_root: Path,
    *,
    errors: list[str],
    warnings: list[str],
    anchors: list[dict[str, Any]],
    map_summary: dict[str, Any] | None = None,
    navigation_memory_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "ok": not errors,
        "map12_root": str(map12_root),
        "scope": "agibot_nav2_occupancy_and_navigation_memory_only",
        "excluded_inputs": ["scene_root", "gaussian_map", "b1_alignment_review"],
        "map": map_summary or {},
        "navigation_memory": navigation_memory_summary or {"item_count": len(anchors)},
        "anchors": anchors,
        "warnings": warnings,
        "errors": errors,
    }


def _load_raw_map(path: Path) -> dict[str, Any]:
    return read_gzip_json_object(path, label="raw map")


def _raw_map_metadata_errors(
    raw_map: dict[str, Any],
    *,
    grid: Any,
    yaw: float,
) -> list[str]:
    errors: list[str] = []
    occupancy = raw_map.get("occupancy_grid")
    if not isinstance(occupancy, dict):
        return ["raw_map.json.gz lacks occupancy_grid metadata"]
    expected = {
        "width": grid.width,
        "height": grid.height,
        "resolution": grid.resolution_m,
        "origin_x": grid.origin_x,
        "origin_y": grid.origin_y,
        "origin_yaw": yaw,
    }
    actual_origin = occupancy.get("origin") if isinstance(occupancy.get("origin"), dict) else {}
    position = (
        actual_origin.get("position") if isinstance(actual_origin.get("position"), dict) else {}
    )
    orientation = (
        actual_origin.get("orientation")
        if isinstance(actual_origin.get("orientation"), dict)
        else {}
    )
    actual = {
        "width": occupancy.get("width"),
        "height": occupancy.get("height"),
        "resolution": occupancy.get("resolution"),
        "origin_x": position.get("x"),
        "origin_y": position.get("y"),
        "origin_yaw": 0.0 if float(orientation.get("w") or 1.0) == 1.0 else None,
    }
    for key, expected_value in expected.items():
        if not _near(actual.get(key), expected_value):
            errors.append(
                f"raw_map {key}={actual.get(key)!r} does not match nav2 {expected_value!r}"
            )
    return errors


def _anchor_check(item: dict[str, Any], *, index: int, grid: Any) -> dict[str, Any]:
    item_id = str(item.get("id") or f"navigation_memory_{index:03d}")
    return {
        "id": item_id,
        "label": str(item.get("label") or ""),
        "kind": str(item.get("kind") or ""),
        # ponytail: in-bounds proves same-frame plausibility; use residual landmarks for Gaussian.
        "pose": _point_check(
            item.get("pose"),
            grid=grid,
            label=f"navigation_memory.json item {item_id} pose",
        ),
        "nav_goal": _point_check(
            item.get("nav_goal"),
            grid=grid,
            label=f"navigation_memory.json item {item_id} nav_goal",
        ),
    }


def _point_check(raw: Any, *, grid: Any, label: str) -> dict[str, Any]:
    point = navigation_memory_point_source(raw, label=label, required=False)
    if not point:
        return {"present": False}
    x = point["x"]
    y = point["y"]
    col, row = world_to_grid(x, y, grid)
    in_bounds = grid.in_bounds(col, row)
    value = grid.rows[row][col] if in_bounds else None
    return {
        "present": True,
        "x": round(x, 6),
        "y": round(y, 6),
        "cell": [col, row],
        "in_bounds": in_bounds,
        "costmap_value": value,
        "free": grid.is_free_cell(col, row) if in_bounds else False,
    }


def _origin(map_yaml: dict[str, Any]) -> tuple[float, float, float]:
    origin = map_yaml.get("origin") if isinstance(map_yaml.get("origin"), list) else []
    return (
        float(origin[0]) if len(origin) > 0 else 0.0,
        float(origin[1]) if len(origin) > 1 else 0.0,
        float(origin[2]) if len(origin) > 2 else 0.0,
    )


def _near(left: Any, right: Any, *, tolerance: float = 1e-6) -> bool:
    try:
        return abs(float(left) - float(right)) <= tolerance
    except (TypeError, ValueError):
        return left == right


if __name__ == "__main__":
    main()

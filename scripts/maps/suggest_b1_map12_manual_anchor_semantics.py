#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

SUGGESTION_SCHEMA = "b1_map12_manual_anchor_semantic_suggestions_v1"
DEFAULT_DRAFT = Path("docs/status/active/b1-map12-scene-correspondences-draft.json")
DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_SCENE_DIAGNOSTIC = Path(
    "output/b1-map12/scene-topdown-label-overlay/scene_topdown_diagnostic.json"
)
DEFAULT_OUTPUT = Path("output/b1-map12/manual-draft-anchor-semantic-suggestions.json")
STRONG_DISTANCE_M = 0.5


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Suggest Map12 navigation area and B1 scene partition candidates for manual "
            "draft anchors. Writes review suggestions only; never accepts anchors."
        )
    )
    parser.add_argument("--draft", type=Path, default=DEFAULT_DRAFT)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    parser.add_argument("--scene-diagnostic", type=Path, default=DEFAULT_SCENE_DIAGNOSTIC)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    payload = build_semantic_suggestions(
        draft=json.loads(args.draft.read_text(encoding="utf-8")),
        review_manifest=json.loads(args.review_manifest.read_text(encoding="utf-8")),
        scene_diagnostic=json.loads(args.scene_diagnostic.read_text(encoding="utf-8")),
        draft_path=args.draft,
        review_manifest_path=args.review_manifest,
        scene_diagnostic_path=args.scene_diagnostic,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "anchor_count": payload["anchor_count"],
                "strong_candidate_count": payload["strong_candidate_count"],
                "output": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


def build_semantic_suggestions(
    *,
    draft: dict[str, Any],
    review_manifest: dict[str, Any],
    scene_diagnostic: dict[str, Any],
    draft_path: Path | None = None,
    review_manifest_path: Path | None = None,
    scene_diagnostic_path: Path | None = None,
) -> dict[str, Any]:
    labels = map_labels(review_manifest)
    partitions = scene_partitions(scene_diagnostic)
    suggestions = []
    for anchor in explicit_anchor_picks(draft):
        map_xy = anchor["map_xy"]
        scene_xyz = anchor["scene_xyz"]
        map_candidates = nearest_map_candidates(float(map_xy[0]), float(map_xy[1]), labels)
        scene_candidates = nearest_scene_candidates(
            float(scene_xyz[0]),
            float(scene_xyz[1]),
            partitions,
        )
        strong = bool(
            map_candidates
            and scene_candidates
            and map_candidates[0]["distance_m"] <= STRONG_DISTANCE_M
            and scene_candidates[0]["distance_m"] <= STRONG_DISTANCE_M
        )
        suggestions.append(
            {
                "anchor_id": str(anchor.get("anchor_id") or ""),
                "review_status": "proposed_suggestion",
                "suggestion_status": "strong_candidate_needs_review"
                if strong
                else "nearest_only_needs_review",
                "map_xy": map_xy,
                "scene_xyz": scene_xyz,
                "recommended_navigation_area_id": map_candidates[0]["map_area_id"]
                if strong
                else "",
                "recommended_asset_partition_id": scene_candidates[0]["partition_id"]
                if strong
                else "",
                "map_candidates": map_candidates[:3],
                "scene_candidates": scene_candidates[:3],
            }
        )
    return {
        "schema": SUGGESTION_SCHEMA,
        "draft": str(draft_path or ""),
        "review_manifest": str(review_manifest_path or ""),
        "scene_diagnostic": str(scene_diagnostic_path or ""),
        "policy": {
            "status": "review_suggestions_only",
            "strong_distance_m": STRONG_DISTANCE_M,
            "accepted_manifest_mutated": False,
            "note": (
                "Nearest candidates are hints. They must be reviewed before accepted anchors "
                "use them."
            ),
        },
        "anchor_count": len(suggestions),
        "strong_candidate_count": sum(
            item["suggestion_status"] == "strong_candidate_needs_review" for item in suggestions
        ),
        "suggestions": suggestions,
    }


def explicit_anchor_picks(draft: dict[str, Any]) -> list[dict[str, Any]]:
    anchors = [
        anchor
        for anchor in draft.get("anchors") or []
        if isinstance(anchor, dict)
        and isinstance(anchor.get("map_xy"), list)
        and len(anchor["map_xy"]) == 2
        and isinstance(anchor.get("scene_xyz"), list)
        and len(anchor["scene_xyz"]) == 3
    ]
    if not anchors:
        raise ValueError("draft has no anchors with explicit map_xy and scene_xyz")
    return anchors


def map_labels(review_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    labels = []
    for label in review_manifest.get("labels") or []:
        if not isinstance(label, dict):
            continue
        geometry = label.get("geometry")
        if not isinstance(geometry, dict) or geometry.get("type") != "map_polygon":
            continue
        points = geometry.get("points")
        if not isinstance(points, list) or len(points) < 3:
            continue
        labels.append(label)
    if not labels:
        raise ValueError("review manifest has no map_polygon labels")
    return labels


def scene_partitions(scene_diagnostic: dict[str, Any]) -> list[dict[str, Any]]:
    partitions = []
    for partition in scene_diagnostic.get("partitions") or []:
        if not isinstance(partition, dict):
            continue
        bounds = partition.get("scene_frame_bounds")
        if not isinstance(bounds, dict):
            continue
        partitions.append(
            {
                "partition_id": str(partition.get("partition_id") or ""),
                "bounds": bounds,
            }
        )
    if not partitions:
        raise ValueError("scene diagnostic has no partition bounds")
    return partitions


def nearest_map_candidates(
    x: float, y: float, labels: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for label in labels:
        points = label["geometry"]["points"]
        distance = polygon_distance(x, y, points)
        rows.append(
            {
                "label_id": str(label.get("label_id") or ""),
                "map_area_id": str(label.get("map_area_id") or ""),
                "scene_partition_id": str(label.get("scene_partition_id") or ""),
                "room_label": str(label.get("room_label") or ""),
                "review_status": str(label.get("review_status") or ""),
                "inside": distance == 0.0,
                "distance_m": round(distance, 6),
            }
        )
    return sorted(rows, key=lambda item: (item["distance_m"], item["label_id"]))


def nearest_scene_candidates(
    x: float, y: float, partitions: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    rows = []
    for partition in partitions:
        distance = bounds_distance(x, y, partition["bounds"])
        rows.append(
            {
                "partition_id": partition["partition_id"],
                "inside": distance == 0.0,
                "distance_m": round(distance, 6),
            }
        )
    return sorted(rows, key=lambda item: (item["distance_m"], item["partition_id"]))


def polygon_distance(x: float, y: float, points: list[dict[str, Any]]) -> float:
    if point_in_polygon(x, y, points):
        return 0.0
    distances = []
    for index, point in enumerate(points):
        next_point = points[(index + 1) % len(points)]
        distances.append(
            segment_distance(
                x,
                y,
                float(point["x"]),
                float(point["y"]),
                float(next_point["x"]),
                float(next_point["y"]),
            )
        )
    return min(distances)


def point_in_polygon(x: float, y: float, points: list[dict[str, Any]]) -> bool:
    inside = False
    previous = points[-1]
    for point in points:
        xi = float(point["x"])
        yi = float(point["y"])
        xj = float(previous["x"])
        yj = float(previous["y"])
        crosses_y = (yi > y) != (yj > y)
        if crosses_y and x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi:
            inside = not inside
        previous = point
    return inside


def segment_distance(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx = bx - ax
    vy = by - ay
    wx = px - ax
    wy = py - ay
    segment_len_sq = vx * vx + vy * vy
    if segment_len_sq == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / segment_len_sq))
    return math.hypot(px - (ax + t * vx), py - (ay + t * vy))


def bounds_distance(x: float, y: float, bounds: dict[str, Any]) -> float:
    dx = max(float(bounds["min_x"]) - x, 0.0, x - float(bounds["max_x"]))
    dy = max(float(bounds["min_y"]) - y, 0.0, y - float(bounds["max_y"]))
    return math.hypot(dx, dy)


if __name__ == "__main__":
    raise SystemExit(main())

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

from roboclaws.core.json_sources import read_json_object  # noqa: E402
from scripts.maps.fit_b1_map12_scene_alignment import (  # noqa: E402
    B1_MAP12_CORRESPONDENCES_SCHEMA,
    SEMANTIC_ANCHOR_ROLE,
    anchor_role,
    validate_correspondence_manifest,
)

SEMANTIC_PROJECTION_SCHEMA = "b1_map12_semantic_projection_v1"
DEFAULT_CORRESPONDENCES = Path("assets/maps/b1-map12-scene-correspondences.json")
DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_OUTPUT = Path("output/b1-map12/semantic-projection/semantic_projection.json")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Project B1 room labels into Map12 semantics only after accepted semantic "
            "anchors exist in the promoted correspondence manifest."
        )
    )
    parser.add_argument("--correspondences", type=Path, default=DEFAULT_CORRESPONDENCES)
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        payload = build_semantic_projection(
            correspondences=read_json_object(
                args.correspondences,
                label="correspondence manifest",
            ),
            review_manifest=read_json_object(args.review_manifest, label="review manifest"),
            correspondences_path=args.correspondences,
            review_manifest_path=args.review_manifest,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": payload["schema"],
                "status": payload["status"],
                "output": str(args.output),
                "room_projection_count": payload["room_projection_count"],
                "object_projection_status": payload["object_projection_status"],
            },
            sort_keys=True,
        )
    )
    return 0


def build_semantic_projection(
    *,
    correspondences: dict[str, Any],
    review_manifest: dict[str, Any],
    correspondences_path: Path | None = None,
    review_manifest_path: Path | None = None,
) -> dict[str, Any]:
    semantic_anchors = accepted_semantic_anchors(correspondences)
    labels_by_partition = accepted_review_labels_by_partition(review_manifest)
    anchors_by_partition: dict[str, list[dict[str, Any]]] = {}
    missing_labels = []
    for anchor in semantic_anchors:
        partition_id = str(anchor.get("asset_partition_id") or "")
        label = labels_by_partition.get(partition_id)
        if label is None:
            missing_labels.append(partition_id)
            continue
        anchors_by_partition.setdefault(partition_id, []).append(anchor)
    if missing_labels:
        raise ValueError(
            "accepted semantic anchors reference missing accepted review labels: "
            + ", ".join(sorted(set(missing_labels)))
        )
    rooms = [
        projected_room(anchors, labels_by_partition[partition_id])
        for partition_id, anchors in sorted(anchors_by_partition.items())
    ]
    if not rooms:
        raise ValueError("no accepted semantic anchors could be projected")
    return {
        "schema": SEMANTIC_PROJECTION_SCHEMA,
        "status": "verified_room_semantics",
        "source_correspondences": str(correspondences_path or ""),
        "source_review_manifest": str(review_manifest_path or ""),
        "source_map_frame": str(correspondences.get("source_map_frame") or ""),
        "target_scene_frame": str(correspondences.get("target_scene_frame") or ""),
        "semantic_anchor_count": len(semantic_anchors),
        "room_projection_count": len(rooms),
        "rooms": rooms,
        "object_projection_status": "blocked_until_object_semantic_anchors",
        "objects": [],
        "policy": {
            "requires_promoted_correspondence_manifest": True,
            "requires_accepted_semantic_anchors": True,
            "proposed_anchors_are_rejected": True,
            "object_labels_are_not_inferred_from_room_anchors": True,
        },
    }


def accepted_semantic_anchors(correspondences: dict[str, Any]) -> list[dict[str, Any]]:
    if correspondences.get("schema") != B1_MAP12_CORRESPONDENCES_SCHEMA:
        raise ValueError(f"unexpected correspondence schema: {correspondences.get('schema')!r}")
    promotion_policy = correspondences.get("promotion_policy")
    if not isinstance(promotion_policy, dict):
        raise ValueError("correspondence manifest must be produced by the strict promoter")
    if promotion_policy.get("requires_review_status") != "accepted":
        raise ValueError("correspondence manifest promotion policy must require accepted anchors")
    errors = validate_correspondence_manifest(correspondences)
    if errors:
        raise ValueError("invalid correspondence manifest: " + "; ".join(errors))
    anchors = [
        anchor
        for anchor in correspondences.get("anchors") or []
        if isinstance(anchor, dict)
        and anchor.get("review_status") == "accepted"
        and anchor_role(anchor) == SEMANTIC_ANCHOR_ROLE
    ]
    if not anchors:
        raise ValueError("accepted semantic anchors are required before projecting room labels")
    return anchors


def accepted_review_labels_by_partition(
    review_manifest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    if review_manifest.get("schema") != "b1_map12_alignment_review_v1":
        raise ValueError(f"unexpected review manifest schema: {review_manifest.get('schema')!r}")
    rows = {}
    for label in review_manifest.get("labels") or []:
        row = label if isinstance(label, dict) else {}
        if row.get("review_status") != "accepted":
            continue
        partition_id = accepted_review_label_partition_id(row)
        validate_accepted_review_label(row)
        if partition_id in rows:
            raise ValueError(
                f"duplicate accepted review label for scene partition {partition_id!r}"
            )
        rows[partition_id] = row
    if not rows:
        raise ValueError("review manifest has no accepted room labels")
    return rows


def accepted_review_label_partition_id(row: dict[str, Any]) -> str:
    partition_id = str(row.get("scene_partition_id") or "")
    if not partition_id:
        raise ValueError("accepted review labels need scene_partition_id")
    return partition_id


def validate_accepted_review_label(row: dict[str, Any]) -> None:
    if not row.get("label_id") or not row.get("map_area_id"):
        raise ValueError("accepted review labels need label_id and map_area_id")
    validate_accepted_review_label_geometry(row)


def validate_accepted_review_label_geometry(row: dict[str, Any]) -> None:
    geometry = row.get("geometry") if isinstance(row.get("geometry"), dict) else {}
    points = geometry.get("points")
    if geometry.get("type") != "map_polygon" or not isinstance(points, list) or len(points) < 3:
        raise ValueError(
            f"accepted review label {row.get('label_id')!r} needs map_polygon geometry"
        )
    if any(not isinstance(point, dict) or "x" not in point or "y" not in point for point in points):
        raise ValueError(
            f"accepted review label {row.get('label_id')!r} has malformed polygon point"
        )


def projected_room(anchors: list[dict[str, Any]], label: dict[str, Any]) -> dict[str, Any]:
    navigation_area_ids = {str(anchor.get("navigation_area_id") or "") for anchor in anchors}
    if len(navigation_area_ids) != 1:
        raise ValueError(
            "accepted semantic anchors for a scene partition must share one navigation_area_id"
        )
    navigation_area_id = navigation_area_ids.pop()
    if navigation_area_id != str(label.get("map_area_id") or ""):
        raise ValueError(
            "accepted semantic anchor navigation_area_id does not match review label map_area_id"
        )
    semantic_anchors = [
        {
            "source_anchor_id": str(anchor.get("anchor_id") or ""),
            "map_xy": [float(value) for value in anchor.get("map_xy") or []],
            "scene_xyz": [float(value) for value in anchor.get("scene_xyz") or []],
        }
        for anchor in anchors
    ]
    return {
        "room_id": str(label.get("label_id") or anchors[0].get("asset_partition_id") or ""),
        "room_label": str(label.get("room_label") or label.get("label_id") or ""),
        "category": str(label.get("category") or ""),
        "navigation_area_id": navigation_area_id,
        "asset_partition_id": str(anchors[0].get("asset_partition_id") or ""),
        "semantic_anchor_count": len(anchors),
        "semantic_anchors": semantic_anchors,
        "map_polygon": [
            {"x": float(point["x"]), "y": float(point["y"])}
            for point in dict(label.get("geometry") or {}).get("points") or []
        ],
        "alignment_status": "accepted_semantic_anchor",
        "semantic_source": "reviewed_b1_map12_semantic_anchor",
        "review_status": "accepted",
        "source_label_id": str(label.get("label_id") or ""),
        "source_anchor_ids": [item["source_anchor_id"] for item in semantic_anchors],
    }


if __name__ == "__main__":
    raise SystemExit(main())

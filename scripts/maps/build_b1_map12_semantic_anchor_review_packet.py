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

from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (  # noqa: E402
    ALIGNMENT_RESIDUALS_SCHEMA,
    residual_backed_waypoint_from_nav_goal,
    validate_alignment_residual_artifact,
)
from scripts.maps.suggest_b1_map12_manual_anchor_semantics import (  # noqa: E402
    REVIEW_PACKET_SCHEMA,
)

DEFAULT_REVIEW_MANIFEST = Path("assets/maps/b1-map12-alignment-review.json")
DEFAULT_ALIGNMENT_ARTIFACT = Path("output/b1-map12/alignment/alignment_residuals.json")
DEFAULT_OUTPUT = Path("docs/status/active/b1-map12-semantic-anchor-review-packet.json")
SEMANTIC_ANCHOR_ROLE = "semantic"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a proposed semantic-anchor review packet from accepted B1 / Map12 "
            "room labels and the verified residual transform. This never accepts anchors."
        )
    )
    parser.add_argument("--review-manifest", type=Path, default=DEFAULT_REVIEW_MANIFEST)
    parser.add_argument("--alignment-artifact", type=Path, default=DEFAULT_ALIGNMENT_ARTIFACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    packet = build_semantic_anchor_review_packet(
        review_manifest=json.loads(args.review_manifest.read_text(encoding="utf-8")),
        alignment=json.loads(args.alignment_artifact.read_text(encoding="utf-8")),
        review_manifest_path=args.review_manifest,
        alignment_artifact_path=args.alignment_artifact,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "schema": packet["schema"],
                "status": packet["status"],
                "output": str(args.output),
                "proposed_anchor_count": packet["proposed_anchor_count"],
                "accepted_anchor_count": packet["accepted_anchor_count"],
            },
            sort_keys=True,
        )
    )
    return 0


def build_semantic_anchor_review_packet(
    *,
    review_manifest: dict[str, Any],
    alignment: dict[str, Any],
    review_manifest_path: Path | None = None,
    alignment_artifact_path: Path | None = None,
) -> dict[str, Any]:
    transform = verified_transform(alignment)
    labels = accepted_room_labels(review_manifest)
    anchors = []
    for label in labels:
        map_xy = polygon_center(label)
        waypoint = residual_backed_waypoint_from_nav_goal(
            {"x": map_xy[0], "y": map_xy[1], "yaw_deg": 0.0},
            waypoint_id=f"semantic_{label['label_id']}",
            label=str(label.get("room_label") or label["label_id"]),
            source_anchor_id=str(label["label_id"]),
            transform=transform,
            alignment_artifact_path=alignment_artifact_path,
            coverage_decision={
                "status": "verified_global",
                "fit_scope": "global_transform",
                "navigation_area_id": str(label["map_area_id"]),
                "asset_partition_id": str(label["scene_partition_id"]),
            },
        )
        b1_pose = waypoint["b1_pose"]
        anchors.append(
            {
                "anchor_id": f"semantic_{label['label_id']}",
                "anchor_type": "room_interior_center",
                "anchor_role": SEMANTIC_ANCHOR_ROLE,
                "review_status": "proposed",
                "navigation_area_id": str(label["map_area_id"]),
                "asset_partition_id": str(label["scene_partition_id"]),
                "map_xy": [round(map_xy[0], 6), round(map_xy[1], 6)],
                "scene_xyz": [float(b1_pose["x"]), float(b1_pose["y"]), 0.0],
                "map_coordinate_source": "accepted_review_label_polygon_center",
                "scene_coordinate_source": "reviewed_correspondence_fit_projection",
                "confidence": 0.0,
                "evidence": {
                    "review_manifest": str(review_manifest_path or ""),
                    "alignment_artifact": str(alignment_artifact_path or ""),
                    "label_id": str(label["label_id"]),
                    "room_label": str(label.get("room_label") or ""),
                    "category": str(label.get("category") or ""),
                    "operator_note": (
                        "Proposed room-interior semantic anchor generated from an accepted "
                        "Map12 room label center and verified residual transform. Human review "
                        "must set review_status=accepted before promotion."
                    ),
                },
                "semantic_review": {
                    "status": "needs_human_review",
                    "source_review_status": str(label.get("review_status") or ""),
                    "source_label_id": str(label["label_id"]),
                    "source_room_label": str(label.get("room_label") or ""),
                    "acceptance_instructions": (
                        "Accept only if this room-interior center is a valid semantic "
                        "correspondence between the Map12 navigation area and B1 asset "
                        "partition. Do not use this packet directly as an accepted manifest."
                    ),
                },
            }
        )
    return {
        "schema": REVIEW_PACKET_SCHEMA,
        "status": "needs_human_review",
        "source_map_frame": str(alignment.get("source_map_frame") or "robot_map_12_map"),
        "target_scene_frame": str(
            alignment.get("target_scene_frame") or "b1_rebuilt_scene_usd_world"
        ),
        "bbox_seed_policy": str(alignment.get("bbox_seed_policy") or "known_poor_seed_only"),
        "scene_projection_policy": alignment.get("scene_projection_policy") or {},
        "source_review_manifest": str(review_manifest_path or ""),
        "source_alignment_artifact": str(alignment_artifact_path or ""),
        "accepted_manifest_mutated": False,
        "accepted_anchor_count": 0,
        "proposed_anchor_count": len(anchors),
        "strong_candidate_count": len(anchors),
        "policy": {
            "auto_accept": False,
            "review_required": True,
            "accepted_manifest_mutated": False,
            "note": (
                "Generated anchors are proposed semantic anchors only. The strict promoter "
                "must reject this packet until a human changes selected anchors to accepted."
            ),
        },
        "anchors": anchors,
    }


def verified_transform(alignment: dict[str, Any]) -> dict[str, Any]:
    if alignment.get("schema") != ALIGNMENT_RESIDUALS_SCHEMA:
        raise ValueError(f"unexpected alignment schema: {alignment.get('schema')!r}")
    errors = validate_alignment_residual_artifact(alignment)
    if errors:
        raise ValueError("invalid alignment artifact: " + "; ".join(errors))
    if alignment.get("global_alignment_status") != "verified":
        raise ValueError("alignment artifact must be globally verified")
    transform = alignment.get("selected_transform")
    if not isinstance(transform, dict):
        raise ValueError("alignment artifact missing selected_transform")
    if str(transform.get("source") or "") != "reviewed_correspondence_fit":
        raise ValueError("alignment transform must come from reviewed_correspondence_fit")
    return transform


def accepted_room_labels(review_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if review_manifest.get("schema") != "b1_map12_alignment_review_v1":
        raise ValueError(f"unexpected review manifest schema: {review_manifest.get('schema')!r}")
    labels = []
    for label in review_manifest.get("labels") or []:
        row = label if isinstance(label, dict) else {}
        if row.get("review_status") != "accepted":
            continue
        if (
            not row.get("label_id")
            or not row.get("map_area_id")
            or not row.get("scene_partition_id")
        ):
            raise ValueError(
                "accepted review labels need label_id, map_area_id, and scene_partition_id"
            )
        geometry = row.get("geometry") if isinstance(row.get("geometry"), dict) else {}
        points = geometry.get("points")
        if geometry.get("type") != "map_polygon" or not isinstance(points, list) or len(points) < 3:
            raise ValueError(f"accepted label {row.get('label_id')!r} needs map_polygon geometry")
        labels.append(row)
    if not labels:
        raise ValueError("review manifest has no accepted labels")
    return labels


def polygon_center(label: dict[str, Any]) -> tuple[float, float]:
    geometry = label.get("geometry") if isinstance(label.get("geometry"), dict) else {}
    points = [point for point in geometry.get("points") or [] if isinstance(point, dict)]
    if not points:
        raise ValueError(f"label {label.get('label_id')!r} has no polygon points")
    return (
        sum(float(point["x"]) for point in points) / len(points),
        sum(float(point["y"]) for point in points) / len(points),
    )


if __name__ == "__main__":
    raise SystemExit(main())

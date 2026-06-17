from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (
    KNOWN_POOR_BBOX_SEED_SOURCE,
    readiness_artifact_with_alignment,
    validate_readiness_artifact,
)
from scripts.maps.fit_b1_map12_scene_alignment import (
    B1_MAP12_ALIGNMENT_RESIDUALS_SCHEMA,
    B1_MAP12_CORRESPONDENCES_SCHEMA,
    build_alignment_residuals,
    validate_alignment_residual_artifact,
    validate_correspondence_manifest,
)
from scripts.maps.render_b1_map12_correspondence_review import build_review_packet
from tests.contract.maps.test_b1_map12_digital_twin_readiness import static_readiness_payload

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "maps" / "fit_b1_map12_scene_alignment.py"
RAW_MAP12_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"


def correspondence_manifest(*, anchors: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": B1_MAP12_CORRESPONDENCES_SCHEMA,
        "source_map_frame": "robot_map_12_map",
        "target_scene_frame": "b1_rebuilt_scene_usd_world",
        "bbox_seed_policy": "known_poor_seed_only",
        "scene_projection_policy": {
            "horizontal_axes": ["x", "z"],
            "up_axis": "y",
            "source": "usd_stage_up_axis_and_robot_pose_convention",
        },
        "anchors": anchors,
    }


def accepted_anchor(
    anchor_id: str,
    map_xy: tuple[float, float],
    scene_xz: tuple[float, float],
    *,
    navigation_area_id: str,
    asset_partition_id: str,
) -> dict[str, object]:
    return {
        "anchor_id": anchor_id,
        "anchor_type": "door_center",
        "navigation_area_id": navigation_area_id,
        "asset_partition_id": asset_partition_id,
        "map_xy": [map_xy[0], map_xy[1]],
        "scene_xyz": [scene_xz[0], 0.0, scene_xz[1]],
        "evidence": {
            "map_image": "output/b1-map12/alignment/map_anchor.png",
            "scene_image": "output/b1-map12/alignment/scene_anchor.png",
            "operator_note": f"reviewed {anchor_id}",
        },
        "confidence": 0.85,
        "review_status": "accepted",
        "map_coordinate_source": "operator_map_pick",
        "scene_coordinate_source": "operator_scene_pick",
    }


def passing_anchors() -> list[dict[str, object]]:
    source_points = [
        (-8.0, 0.0),
        (-5.0, 0.5),
        (-2.0, 2.0),
        (1.0, 4.0),
        (3.0, -2.0),
        (5.0, 3.5),
    ]
    areas = [
        ("west_corridor", "meeting_room_a"),
        ("west_corridor", "meeting_room_a"),
        ("central_floor", "meeting_room_b"),
        ("north_fixture_area", "meeting_room_c"),
        ("south_fixture_area", "reception_area_a"),
        ("storage_room_a", "storage_room_a"),
    ]
    anchors = []
    for index, ((x, y), (area_id, partition_id)) in enumerate(
        zip(source_points, areas, strict=True),
        start=1,
    ):
        scene = (1.2 * x + 3.0, 1.2 * y - 8.0)
        anchors.append(
            accepted_anchor(
                f"anchor_{index}",
                (x, y),
                scene,
                navigation_area_id=area_id,
                asset_partition_id=partition_id,
            )
        )
    return anchors


def test_manifest_rejects_accepted_anchor_from_known_poor_bbox_seed() -> None:
    anchor = accepted_anchor(
        "bbox_seed_prefill",
        (-1.0, 2.0),
        (3.0, -4.0),
        navigation_area_id="central_floor",
        asset_partition_id="meeting_room_b",
    )
    anchor["scene_coordinate_source"] = "known_poor_bbox_seed"
    manifest = correspondence_manifest(anchors=[anchor])

    errors = validate_correspondence_manifest(manifest)

    assert (
        "accepted anchor bbox_seed_prefill must not use known-poor bbox seed coordinates" in errors
    )


def test_fitter_keeps_alignment_candidate_without_six_reviewed_anchors(tmp_path: Path) -> None:
    manifest = correspondence_manifest(anchors=passing_anchors()[:3])

    payload = build_alignment_residuals(
        manifest,
        map_bundle=RAW_MAP12_BUNDLE,
        output_dir=tmp_path,
    )

    assert payload["schema"] == B1_MAP12_ALIGNMENT_RESIDUALS_SCHEMA
    assert payload["status"] == "insufficient_reviewed_anchors"
    assert payload["global_alignment_status"] == "candidate"
    assert payload["residual_evidence"]["status"] == "not_available"
    assert payload["previews"]["before_overlay"].endswith("alignment_before.png")


def test_fitter_selects_simple_verified_similarity_transform(tmp_path: Path) -> None:
    manifest = correspondence_manifest(anchors=passing_anchors())

    payload = build_alignment_residuals(
        manifest,
        map_bundle=RAW_MAP12_BUNDLE,
        output_dir=tmp_path,
    )

    assert validate_alignment_residual_artifact(payload) == []
    assert payload["global_alignment_status"] == "verified"
    assert payload["selected_transform_type"] == "similarity_2d"
    assert payload["residual_evidence"]["matched_anchor_count"] == 6
    assert payload["residual_evidence"]["max_residual_m"] == pytest.approx(0.0)
    assert payload["diagnostic_affine_transform"]["diagnostic_only"] is True


def test_readiness_promotes_verified_only_from_residual_artifact(tmp_path: Path) -> None:
    readiness = static_readiness_payload()
    readiness["map12_overlay"] = {
        "bbox_seed_policy": "known_poor_seed_only",
        "transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
    }
    alignment = build_alignment_residuals(
        correspondence_manifest(anchors=passing_anchors()),
        map_bundle=RAW_MAP12_BUNDLE,
        output_dir=tmp_path,
    )

    merged = readiness_artifact_with_alignment(
        readiness,
        alignment,
        alignment_artifact_path=tmp_path / "alignment_residuals.json",
    )

    assert merged["map12_overlay_status"] == "verified"
    assert merged["map12_to_b1_usd_transform_status"] == "verified"
    assert merged["residual_evidence"]["matched_anchor_count"] == 6
    assert validate_readiness_artifact(merged) == []


def test_readiness_records_area_verified_only_when_global_fit_fails(tmp_path: Path) -> None:
    anchors = [
        accepted_anchor(
            "central_a",
            (0.0, 0.0),
            (10.0, -4.0),
            navigation_area_id="central_floor",
            asset_partition_id="meeting_room_b",
        ),
        accepted_anchor(
            "central_b",
            (1.0, 0.0),
            (11.0, -4.0),
            navigation_area_id="central_floor",
            asset_partition_id="meeting_room_b",
        ),
        accepted_anchor(
            "central_c",
            (0.0, 1.0),
            (10.0, -3.0),
            navigation_area_id="central_floor",
            asset_partition_id="meeting_room_b",
        ),
        accepted_anchor(
            "west_a",
            (10.0, 0.0),
            (-20.0, 30.0),
            navigation_area_id="west_corridor",
            asset_partition_id="meeting_room_a",
        ),
        accepted_anchor(
            "north_a",
            (0.0, 10.0),
            (35.0, 22.0),
            navigation_area_id="north_fixture_area",
            asset_partition_id="meeting_room_c",
        ),
        accepted_anchor(
            "south_a",
            (-10.0, -7.0),
            (-32.0, -24.0),
            navigation_area_id="south_fixture_area",
            asset_partition_id="reception_area_a",
        ),
    ]
    alignment = build_alignment_residuals(
        correspondence_manifest(anchors=anchors),
        map_bundle=RAW_MAP12_BUNDLE,
        output_dir=tmp_path,
    )

    merged = readiness_artifact_with_alignment(
        {
            **static_readiness_payload(),
            "map12_overlay": {
                "bbox_seed_policy": "known_poor_seed_only",
                "transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
            },
        },
        alignment,
        alignment_artifact_path=tmp_path / "alignment_residuals.json",
    )

    assert alignment["global_alignment_status"] == "candidate"
    assert alignment["residual_evidence"]["passed"] is False
    assert any(
        item["navigation_area_id"] == "central_floor"
        and item["alignment_status"] == "verified"
        and item["matched_anchor_count"] == 3
        for item in alignment["area_alignment"]
    )
    assert merged["map12_overlay_status"] == "candidate"
    assert merged["map12_to_b1_usd_transform_status"] == "area_verified_only"
    assert validate_readiness_artifact(merged) == []


def test_readiness_rejects_verified_overlay_without_residual_evidence() -> None:
    payload = static_readiness_payload()
    payload["map12_overlay"] = {
        "bbox_seed_policy": "known_poor_seed_only",
        "transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
        "verified_transform": {"source": "reviewed_correspondence_fit"},
    }
    payload["map12_overlay_status"] = "verified"
    payload["map12_to_b1_usd_transform_status"] = "verified"

    errors = validate_readiness_artifact(payload)

    assert "verified overlay requires residual evidence" in errors
    assert "verified overlay requires at least six matched anchors" in errors


def test_readiness_rejects_verified_overlay_from_bbox_seed() -> None:
    payload = static_readiness_payload()
    payload["map12_overlay"] = {
        "bbox_seed_policy": "known_poor_seed_only",
        "transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
        "verified_transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
    }
    payload["map12_overlay_status"] = "verified"
    payload["map12_to_b1_usd_transform_status"] = "verified"
    payload["residual_evidence"] = {
        "status": "available",
        "matched_anchor_count": 6,
        "transform_source": KNOWN_POOR_BBOX_SEED_SOURCE,
    }

    errors = validate_readiness_artifact(payload)

    assert "verified overlay must not use known-poor bbox seed" in errors
    assert "verified overlay cannot use the bbox-fit transform as its verified transform" in errors


def test_area_verified_only_requires_verified_area_with_three_anchors() -> None:
    payload = static_readiness_payload()
    payload["map12_overlay"] = {
        "bbox_seed_policy": "known_poor_seed_only",
        "transform": {"source": KNOWN_POOR_BBOX_SEED_SOURCE},
    }
    payload["map12_to_b1_usd_transform_status"] = "area_verified_only"
    payload["area_alignment"] = [
        {
            "navigation_area_id": "central_floor",
            "alignment_status": "verified",
            "matched_anchor_count": 3,
            "max_residual_m": 0.3,
        }
    ]

    assert validate_readiness_artifact(payload) == []

    payload["area_alignment"][0]["matched_anchor_count"] = 2
    alignment_errors = validate_alignment_residual_artifact(
        {
            "schema": B1_MAP12_ALIGNMENT_RESIDUALS_SCHEMA,
            "bbox_seed_policy": "known_poor_seed_only",
            "manipulation_supported": False,
            "object_receptacle_usd_binding_status": "blocked_out_of_scope",
            "global_alignment_status": "candidate",
            "residual_evidence": {"status": "not_available", "matched_anchor_count": 0},
            "selected_transform": {},
            "area_alignment": payload["area_alignment"],
        }
    )

    assert "area verified alignment requires at least three matched anchors" in alignment_errors


def test_alignment_fitter_cli_writes_residual_artifact(tmp_path: Path) -> None:
    manifest_path = tmp_path / "scene_correspondences.json"
    output_dir = tmp_path / "alignment"
    manifest_path.write_text(
        json.dumps(correspondence_manifest(anchors=passing_anchors())),
        encoding="utf-8",
    )

    subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--correspondences",
            str(manifest_path),
            "--map-bundle",
            str(RAW_MAP12_BUNDLE),
            "--output-dir",
            str(output_dir),
        ],
        check=True,
    )

    payload = json.loads((output_dir / "alignment_residuals.json").read_text(encoding="utf-8"))
    assert payload["global_alignment_status"] == "verified"
    assert payload["validation"]["status"] == "passed"


def test_review_packet_keeps_proposed_anchor_pending() -> None:
    manifest = correspondence_manifest(
        anchors=[
            {
                "anchor_id": "draft_anchor",
                "anchor_type": "door_center",
                "navigation_area_id": "central_floor",
                "asset_partition_id": "meeting_room_b",
                "map_xy": None,
                "scene_xyz": None,
                "review_status": "proposed",
                "evidence": {"operator_note": "needs explicit picks"},
            }
        ]
    )

    packet = build_review_packet(
        manifest,
        map_bundle=RAW_MAP12_BUNDLE,
    )

    assert packet["schema"] == "b1_map12_correspondence_review_packet_v1"
    assert packet["review_status"] == "review_pending"
    assert packet["accepted_anchor_count"] == 0
    assert packet["fit_ready_anchor_count"] == 0
    assert packet["anchors"][0]["review_action"] == (
        "pick explicit map_xy and scene_xyz, then mark accepted after operator review"
    )


def test_review_packet_flags_seed_derived_accepted_anchor_not_fit_ready() -> None:
    anchor = accepted_anchor(
        "seed_anchor",
        (-1.0, 2.0),
        (3.0, -4.0),
        navigation_area_id="central_floor",
        asset_partition_id="meeting_room_b",
    )
    anchor["scene_coordinate_source"] = "known_poor_bbox_seed"
    manifest = correspondence_manifest(anchors=[anchor])

    packet = build_review_packet(
        manifest,
        map_bundle=RAW_MAP12_BUNDLE,
    )

    assert packet["review_status"] == "manifest_needs_fix"
    assert packet["accepted_anchor_count"] == 1
    assert packet["fit_ready_anchor_count"] == 0
    assert packet["anchors"][0]["uses_known_poor_bbox_seed"] is True
    assert "replace seed-derived coordinates" in packet["anchors"][0]["review_action"]

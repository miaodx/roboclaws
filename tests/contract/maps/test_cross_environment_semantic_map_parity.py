from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.spatial_contract import (
    DISPLAY_FRAME_STATUS_ABSENT,
    GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
    MAP_SPATIAL_CONTRACT_SCHEMA,
    POLYGON_ROLE_NAVIGATION_AREA,
    POLYGON_ROLE_ROOM_BOUNDARY,
    validate_spatial_room_contract,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
STATIC_MAP_BUNDLES = tuple(
    sorted(
        path
        for path in (REPO_ROOT / "assets" / "maps").iterdir()
        if (path / "map.yaml").is_file() and (path / "semantics.json").is_file()
    )
)


@pytest.mark.parametrize("bundle_dir", STATIC_MAP_BUNDLES, ids=lambda path: path.name)
def test_all_static_map_bundles_declare_source_frame_spatial_contract(
    bundle_dir: Path,
) -> None:
    semantics = _semantics(bundle_dir)

    validation = validate_nav2_map_bundle(bundle_dir)

    assert validation.ok, validation.as_dict()
    assert semantics["display_frame"] is None
    assert semantics["spatial_contract"]["schema"] == MAP_SPATIAL_CONTRACT_SCHEMA
    assert semantics["spatial_contract"]["semantic_geometry_frame"] == "source_map_frame"
    assert semantics["spatial_contract"]["display_frame_status"] == DISPLAY_FRAME_STATUS_ABSENT
    assert (
        semantics["spatial_contract"]["source_map_frame"]["frame_id"]
        == (semantics["frame_ids"]["map"])
    )
    assert semantics["rooms"]
    for room in semantics["rooms"]:
        assert room["polygon_role"] == POLYGON_ROLE_NAVIGATION_AREA
        assert room["geometry_source"] == GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE
        assert room["source_map_frame_id"] == semantics["frame_ids"]["map"]
        assert room["polygon_usage"]["review"] is True


def test_static_map_bundle_inventory_is_not_empty() -> None:
    assert STATIC_MAP_BUNDLES


def test_b1_uses_separate_review_and_correspondence_manifests() -> None:
    review = json.loads(
        (REPO_ROOT / "assets" / "maps" / "b1-map12-alignment-review.json").read_text(
            encoding="utf-8"
        )
    )
    correspondences = json.loads(
        (REPO_ROOT / "assets" / "maps" / "b1-map12-scene-correspondences.json").read_text(
            encoding="utf-8"
        )
    )
    raw_map = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"

    assert review["schema"] == "b1_map12_alignment_review_v1"
    assert review["source_assets"]["map_bundle"] == "assets/maps/agibot-robot-map-12"
    assert correspondences["schema"] == "b1_map12_scene_correspondences_v1"
    assert correspondences["anchors"] == []
    assert validate_nav2_map_bundle(raw_map).ok
    assert not (REPO_ROOT / "assets" / "maps" / "b1-map12-room-semantics").exists()


def test_candidate_navigation_zone_cannot_be_validated_as_room_boundary() -> None:
    room = {
        "room_id": "candidate_box",
        "room_label": "Candidate box",
        "polygon": [
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
        ],
        "polygon_role": POLYGON_ROLE_ROOM_BOUNDARY,
        "geometry_source": GEOMETRY_SOURCE_OPERATOR_NAVIGATION_ZONE,
        "alignment_status": "candidate",
        "source_map_frame_id": "map",
        "polygon_usage": {"navigation": True, "semantic_labeling": "candidate", "review": True},
    }
    errors: list[str] = []

    validate_spatial_room_contract(room, index=0, errors=errors)

    assert any("operator navigation zone" in error for error in errors)
    assert any("candidate geometry" in error for error in errors)


def _semantics(bundle_dir: Path) -> dict:
    return json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))

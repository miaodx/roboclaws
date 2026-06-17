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


def test_b1_room_semantics_uses_explicit_scene_map_correspondence_manifest() -> None:
    bundle_dir = REPO_ROOT / "assets" / "maps" / "b1-map12-room-semantics"
    semantics = _semantics(bundle_dir)
    overlay = json.loads((bundle_dir / "room_semantic_overlay.json").read_text(encoding="utf-8"))
    correspondences = overlay["scene_map_correspondence_v1"]
    by_partition = {item["asset_partition_id"]: item for item in correspondences}

    assert overlay["scene_map_correspondence_schema"] == "scene_map_correspondence_v1"
    assert by_partition
    for room in semantics["rooms"]:
        partition_id = room["asset_partition_id"]
        correspondence = by_partition[partition_id]
        assert room["navigation_area_id"] == correspondence["navigation_area_id"]
        assert room["alignment_status"] == correspondence["alignment_status"]
        assert room["scene_map_correspondence"]["asset_partition_id"] == partition_id
        assert room["scene_map_correspondence"]["navigation_area_id"] == room["navigation_area_id"]
    assert {item["asset_partition_id"] for item in correspondences} == {
        item["asset_partition_id"] for item in semantics["rooms"]
    }


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

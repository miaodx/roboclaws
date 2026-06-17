from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.room_semantics import (
    ROOM_SEMANTIC_OVERLAY_SCHEMA,
    build_scene_room_semantic_overlay,
)
from scripts.maps.compile_b1_map12_runtime_bundle import compile_runtime_bundle

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENE_ROOT = (
    REPO_ROOT / "data" / "robot-data-lab" / "scene-engine" / "data" / ("2rd_floor_seperated")
)
MAP12_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"
REVIEW_MANIFEST = REPO_ROOT / "assets" / "maps" / "b1-map12-alignment-review.json"
GENERATOR_PATH = (
    REPO_ROOT
    / "skills"
    / "actionable-semantic-map-conversion"
    / "scripts"
    / ("generate_scene_room_overlay.py")
)
OVERRIDES_PATH = (
    REPO_ROOT
    / "skills"
    / "actionable-semantic-map-conversion"
    / "examples"
    / "b1_map12_room_semantic_overrides.json"
)


def test_scene_room_overlay_labels_gaussian_partitions_as_public_room_semantics() -> None:
    _require_scene_root()

    overlay = build_scene_room_semantic_overlay(SCENE_ROOT, source_bundle_dir=MAP12_BUNDLE)
    rooms = {item["asset_partition_id"]: item for item in overlay["rooms"]}

    assert overlay["schema"] == ROOM_SEMANTIC_OVERLAY_SCHEMA
    assert set(rooms) == {
        "meeting_room_a",
        "meeting_room_b",
        "meeting_room_c",
        "reception_area_a",
        "short_corridor_a",
        "storage_room_a",
    }
    assert rooms["meeting_room_a"]["category"] == "meeting_room"
    assert rooms["reception_area_a"]["category"] == "reception_area"
    assert rooms["short_corridor_a"]["category"] == "corridor"
    assert rooms["storage_room_a"]["category"] == "storage_room"
    assert rooms["meeting_room_a"]["room_label"] != "Room A"
    assert rooms["reception_area_a"]["room_label"] == "Lobby / reception area"
    assert "room_category_hints" in overlay
    assert all(item["category"] for item in overlay["room_category_hints"])


def test_scene_room_overlay_accepts_operator_overrides_for_open_kitchen_and_living_room() -> None:
    _require_scene_root()

    overlay = build_scene_room_semantic_overlay(
        SCENE_ROOT,
        source_bundle_dir=MAP12_BUNDLE,
        overrides={
            "rooms": [
                {
                    "asset_partition_id": "meeting_room_a",
                    "room_label": "Meeting room A",
                    "category": "meeting_room",
                    "confidence": 0.86,
                    "semantic_source": "operator_authored_room_overlay",
                    "review_status": "accepted",
                },
                {
                    "asset_partition_id": "meeting_room_b",
                    "room_label": "Open kitchen",
                    "category": "kitchen",
                    "confidence": 0.92,
                    "semantic_source": "operator_authored_room_overlay",
                    "review_status": "accepted",
                },
                {
                    "asset_partition_id": "reception_area_a",
                    "room_label": "Living room / main hall",
                    "category": "living_room",
                    "confidence": 0.9,
                    "semantic_source": "operator_authored_room_overlay",
                    "review_status": "accepted",
                },
                {
                    "asset_partition_id": "meeting_room_c",
                    "room_label": "Meeting room B",
                    "category": "meeting_room",
                    "confidence": 0.86,
                    "semantic_source": "operator_authored_room_overlay",
                    "review_status": "accepted",
                },
            ]
        },
    )
    rooms = {item["asset_partition_id"]: item for item in overlay["rooms"]}

    assert rooms["meeting_room_b"]["room_label"] == "Open kitchen"
    assert rooms["meeting_room_b"]["category"] == "kitchen"
    assert rooms["meeting_room_b"]["semantic_source"] == "operator_authored_room_overlay"
    assert rooms["meeting_room_a"]["room_label"] == "Meeting room A"
    assert rooms["meeting_room_a"]["category"] == "meeting_room"
    assert rooms["meeting_room_c"]["room_label"] == "Meeting room B"
    assert rooms["meeting_room_c"]["category"] == "meeting_room"
    assert rooms["reception_area_a"]["category"] == "living_room"


def test_b1_runtime_compiler_materializes_review_labels_without_retargeting_map(
    tmp_path: Path,
) -> None:
    _require_scene_root()

    raw_semantics = json.loads((MAP12_BUNDLE / "semantics.json").read_text(encoding="utf-8"))
    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
        output_dir=tmp_path / "runtime-map-bundle",
    )
    bundle_dir = Path(result["output_dir"])
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))

    assert result["validation"]["ok"] is True
    assert validate_nav2_map_bundle(bundle_dir).ok
    assert semantics["rooms"] == raw_semantics["rooms"]
    assert semantics["inspection_waypoints"] == raw_semantics["inspection_waypoints"]
    assert semantics["driveable_ways"] == raw_semantics["driveable_ways"]
    assert {item["label_id"] for item in semantics["review_labels"]} == {
        "meeting_room_a",
        "meeting_room_b",
        "meeting_room_c",
    }


def test_scene_room_overlay_skill_script_writes_overlay_and_bundle(
    tmp_path: Path,
) -> None:
    _require_scene_root()

    generator = _load_module(GENERATOR_PATH, "generate_scene_room_overlay")
    output = tmp_path / "room_semantic_overlay.json"

    generator.main(
        [
            str(SCENE_ROOT),
            "--source-bundle-dir",
            str(MAP12_BUNDLE),
            "--overrides-json",
            str(OVERRIDES_PATH),
            "--output",
            str(output),
        ]
    )

    overlay = json.loads(output.read_text(encoding="utf-8"))

    assert overlay["schema"] == ROOM_SEMANTIC_OVERLAY_SCHEMA
    assert {item["asset_partition_id"] for item in overlay["rooms"]} >= {
        "meeting_room_a",
        "storage_room_a",
    }
    assert any(item["room_label"] == "Open kitchen" for item in overlay["rooms"])
    assert not (tmp_path / "bundle").exists()


def test_checked_in_b1_review_manifest_is_runtime_source_of_truth() -> None:
    manifest = json.loads(REVIEW_MANIFEST.read_text(encoding="utf-8"))
    labels = {item["label_id"]: item for item in manifest["labels"]}

    assert manifest["schema"] == "b1_map12_alignment_review_v1"
    assert manifest["source_assets"]["map_bundle"] == "assets/maps/agibot-robot-map-12"
    assert labels["meeting_room_b"]["review_status"] == "accepted"
    assert labels["short_corridor_a"]["review_status"] == "draft"
    assert labels["reception_area_a"]["review_status"] == "blocked_shared_area"
    assert labels["storage_room_a"]["review_status"] == "blocked_shared_area"


def _require_scene_root() -> None:
    if not SCENE_ROOT.is_dir():
        pytest.skip("robot-data-lab scene-engine data is unavailable in this checkout")


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

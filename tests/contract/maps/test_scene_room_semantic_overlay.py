from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.household.backend_contract import CleanupBackendSession
from roboclaws.household.realworld_contract import MINIMAL_MAP_MODE, RealWorldCleanupContract
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.room_semantics import (
    ROOM_SEMANTIC_OVERLAY_SCHEMA,
    apply_room_semantic_overlay_to_bundle,
    build_scene_room_semantic_overlay,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
SCENE_ROOT = (
    REPO_ROOT / "data" / "robot-data-lab" / "scene-engine" / "data" / ("2rd_floor_seperated")
)
MAP12_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"
B1_MAP12_ROOM_SEMANTICS_BUNDLE = REPO_ROOT / "assets" / "maps" / "b1-map12-room-semantics"
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


def test_scene_room_overlay_can_materialize_b1_baseline_map_bundle(tmp_path: Path) -> None:
    _require_scene_root()

    overlay = build_scene_room_semantic_overlay(
        SCENE_ROOT,
        source_bundle_dir=MAP12_BUNDLE,
        overrides={
            "rooms": [
                {
                    "asset_partition_id": "meeting_room_b",
                    "room_label": "Open kitchen",
                    "category": "kitchen",
                    "confidence": 0.92,
                    "semantic_source": "operator_authored_room_overlay",
                    "review_status": "accepted",
                }
            ]
        },
    )
    bundle_dir = tmp_path / "b1-map12-room-semantics"

    application = apply_room_semantic_overlay_to_bundle(MAP12_BUNDLE, bundle_dir, overlay)

    validation = validate_nav2_map_bundle(bundle_dir)
    contract = RealWorldCleanupContract(
        CleanupBackendSession(build_cleanup_scenario(seed=7)),
        map_bundle_dir=bundle_dir,
        map_mode=MINIMAL_MAP_MODE,
    )
    metric_rooms = {item["room_id"]: item for item in contract.metric_map()["rooms"]}
    hints = {item["room_id"]: item for item in contract.metric_map()["room_category_hints"]}

    assert application["validation"]["ok"] is True
    assert validation.ok, validation.as_dict()
    assert metric_rooms["meeting_room_b"]["room_label"] == "Open kitchen"
    assert metric_rooms["meeting_room_b"]["category"] == "kitchen"
    assert hints["meeting_room_b"]["category"] == "kitchen"
    assert contract.metric_map()["minimal_map"]["source_room_labels_visible"] is True


def test_scene_room_overlay_skill_script_writes_overlay_and_bundle(
    tmp_path: Path,
) -> None:
    _require_scene_root()

    generator = _load_module(GENERATOR_PATH, "generate_scene_room_overlay")
    output = tmp_path / "room_semantic_overlay.json"
    bundle_dir = tmp_path / "bundle"

    generator.main(
        [
            str(SCENE_ROOT),
            "--source-bundle-dir",
            str(MAP12_BUNDLE),
            "--overrides-json",
            str(OVERRIDES_PATH),
            "--output",
            str(output),
            "--apply-to-bundle",
            str(bundle_dir),
        ]
    )

    overlay = json.loads(output.read_text(encoding="utf-8"))
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))

    assert overlay["schema"] == ROOM_SEMANTIC_OVERLAY_SCHEMA
    assert {item["room_id"] for item in semantics["rooms"]} >= {"meeting_room_a", "storage_room_a"}
    assert any(item["room_label"] == "Open kitchen" for item in semantics["rooms"])
    assert validate_nav2_map_bundle(bundle_dir).ok


def test_solidified_b1_map12_room_semantic_bundle_contains_public_room_labels() -> None:
    semantics = json.loads(
        (B1_MAP12_ROOM_SEMANTICS_BUNDLE / "semantics.json").read_text(encoding="utf-8")
    )
    overlay = json.loads(
        (B1_MAP12_ROOM_SEMANTICS_BUNDLE / "room_semantic_overlay.json").read_text(encoding="utf-8")
    )
    rooms = {item["room_id"]: item for item in semantics["rooms"]}
    hints = {item["room_id"]: item for item in semantics["room_category_hints"]}

    validation = validate_nav2_map_bundle(B1_MAP12_ROOM_SEMANTICS_BUNDLE)

    assert validation.ok, validation.as_dict()
    assert overlay["schema"] == ROOM_SEMANTIC_OVERLAY_SCHEMA
    assert rooms["meeting_room_a"]["room_label"] == "Meeting room A"
    assert rooms["meeting_room_a"]["category"] == "meeting_room"
    assert rooms["meeting_room_b"]["room_label"] == "Open kitchen"
    assert rooms["meeting_room_b"]["category"] == "kitchen"
    assert rooms["meeting_room_c"]["room_label"] == "Meeting room B"
    assert rooms["meeting_room_c"]["category"] == "meeting_room"
    assert rooms["reception_area_a"]["room_label"] == "Main hall / living area"
    assert rooms["reception_area_a"]["category"] == "living_room"
    assert hints["meeting_room_a"]["category"] == "meeting_room"
    assert hints["meeting_room_b"]["category"] == "kitchen"
    assert hints["meeting_room_c"]["category"] == "meeting_room"
    assert hints["reception_area_a"]["category"] == "living_room"
    assert semantics["provenance"]["contains_private_scoring_truth"] is False
    assert (B1_MAP12_ROOM_SEMANTICS_BUNDLE / "room_semantic_topdown.png").is_file()
    assert (B1_MAP12_ROOM_SEMANTICS_BUNDLE / "preview.png").is_file()


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

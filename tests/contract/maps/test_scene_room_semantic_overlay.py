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
MAP12_BUNDLE = (
    REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / ("robot_map_12") / "agibot"
)
ROOM_SEMANTICS = REPO_ROOT / "assets" / "maps" / "b1-map12-room-semantics.json"
GENERATOR_PATH = (
    REPO_ROOT
    / "skills"
    / "runtime-map-prior-conversion"
    / "scripts"
    / ("generate_scene_room_overlay.py")
)
OVERRIDES_PATH = (
    REPO_ROOT
    / "skills"
    / "runtime-map-prior-conversion"
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


def test_scene_room_overlay_does_not_fabricate_geometry_without_source_semantics(
    tmp_path: Path,
) -> None:
    scene_root = _minimal_scene_root(tmp_path)
    source_bundle = tmp_path / "bundle"
    source_bundle.mkdir()

    overlay = build_scene_room_semantic_overlay(
        scene_root,
        source_bundle_dir=source_bundle,
        overrides={
            "scene_map_correspondence": [
                {
                    "asset_partition_id": "meeting_room_a",
                    "navigation_area_id": "nav_room_a",
                }
            ]
        },
    )

    room = overlay["rooms"][0]
    assert room["navigation_area_id"] == "nav_room_a"
    assert "polygon" not in room
    assert "map_center" not in room
    assert "geometry_source" not in room
    assert "polygon_usage" not in room
    assert room["scene_map_correspondence"]["map_polygon_provided"] is False


@pytest.mark.parametrize(
    ("source_text", "message"),
    [
        ("{not-json\n", r"room semantics source must contain valid JSON object: .*semantics\.json"),
        ("[]\n", r"room semantics source must contain a JSON object: .*semantics\.json"),
    ],
)
def test_scene_room_overlay_rejects_bad_source_bundle_semantics(
    tmp_path: Path,
    source_text: str,
    message: str,
) -> None:
    scene_root = _minimal_scene_root(tmp_path)
    source_bundle = tmp_path / "bundle"
    source_bundle.mkdir()
    (source_bundle / "semantics.json").write_text(source_text, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        build_scene_room_semantic_overlay(scene_root, source_bundle_dir=source_bundle)


def test_scene_room_overlay_uses_source_bundle_room_geometry(tmp_path: Path) -> None:
    scene_root = _minimal_scene_root(tmp_path)
    source_bundle = tmp_path / "bundle"
    source_bundle.mkdir()
    (source_bundle / "semantics.json").write_text(
        json.dumps(
            {
                "rooms": [
                    {
                        "room_id": "nav_room_a",
                        "polygon": [
                            {"x": 0, "y": 0},
                            {"x": 2, "y": 0},
                            {"x": 2, "y": 2},
                            {"x": 0, "y": 2},
                        ],
                        "source_map_frame_id": "map",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    overlay = build_scene_room_semantic_overlay(
        scene_root,
        source_bundle_dir=source_bundle,
        overrides={
            "scene_map_correspondence": [
                {
                    "asset_partition_id": "meeting_room_a",
                    "navigation_area_id": "nav_room_a",
                }
            ]
        },
    )

    room = overlay["rooms"][0]
    assert room["navigation_area_id"] == "nav_room_a"
    assert room["polygon"] == [
        {"x": 0, "y": 0},
        {"x": 2, "y": 0},
        {"x": 2, "y": 2},
        {"x": 0, "y": 2},
    ]
    assert room["map_center"] == {"x": 1.0, "y": 1.0}


def test_b1_runtime_compiler_materializes_review_labels_without_retargeting_map(
    tmp_path: Path,
) -> None:
    _require_scene_root()

    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        room_semantics_path=ROOM_SEMANTICS,
        output_dir=tmp_path / "runtime-map-bundle",
    )
    bundle_dir = Path(result["output_dir"])
    semantics = json.loads((bundle_dir / "semantics.json").read_text(encoding="utf-8"))

    assert result["validation"]["ok"] is True
    assert validate_nav2_map_bundle(bundle_dir).ok
    assert semantics["rooms"] == []
    assert semantics["fixtures"] == []
    assert len(semantics["navigation_memory_anchors"]) == 9
    assert semantics["review_labels"] == []
    assert semantics["provenance"]["room_semantics_reference"] == str(ROOM_SEMANTICS)


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


def test_checked_in_b1_room_semantics_is_dt_label_reference_only() -> None:
    payload = json.loads(ROOM_SEMANTICS.read_text(encoding="utf-8"))
    rooms = {item["asset_partition_id"]: item for item in payload["rooms"]}

    assert payload["schema"] == "scene_room_semantic_overlay_overrides_v1"
    assert payload["policy"]["source_of_truth"] == "digital_twin_scene_partitions"
    assert payload["policy"]["contains_map12_candidate_polygons"] is False
    assert payload["policy"]["contains_navigation_area_bindings"] is False
    assert rooms["meeting_room_b"]["room_label"] == "Open kitchen"
    assert rooms["meeting_room_b"]["review_status"] == "needs_review"
    assert rooms["meeting_room_b"]["semantic_source"] == "legacy_operator_room_overlay_candidate"
    assert rooms["reception_area_a"]["category"] == "living_room"
    assert {room["review_status"] for room in rooms.values()} == {"accepted", "needs_review"}
    assert all(
        "map_polygon" not in room and "navigation_area_id" not in room for room in rooms.values()
    )


def _require_scene_root() -> None:
    if not SCENE_ROOT.is_dir():
        pytest.skip("robot-data-lab scene-engine data is unavailable in this checkout")


def _minimal_scene_root(tmp_path: Path) -> Path:
    partition = tmp_path / "scene" / "meeting_room_a"
    partition.mkdir(parents=True)
    (partition / "scene.usd").write_text("#usda 1.0\n", encoding="utf-8")
    return tmp_path / "scene"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

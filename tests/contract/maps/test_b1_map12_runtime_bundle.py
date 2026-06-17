from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from roboclaws.maps.bundle import validate_nav2_map_bundle
from scripts.maps.compile_b1_map12_runtime_bundle import (
    B1_MAP12_ALIGNMENT_REVIEW_SCHEMA,
    compile_runtime_bundle,
    review_manifest_errors,
    runtime_labels_from_review,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MAP12_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"
SCENE_ROOT = (
    REPO_ROOT / "data" / "robot-data-lab" / "scene-engine" / "data" / "2rd_floor_seperated"
)
REVIEW_MANIFEST = REPO_ROOT / "assets" / "maps" / "b1-map12-alignment-review.json"


def test_checked_in_review_manifest_blocks_shared_south_area_from_runtime() -> None:
    manifest = _review_manifest()

    assert manifest["schema"] == B1_MAP12_ALIGNMENT_REVIEW_SCHEMA
    assert review_manifest_errors(
        manifest,
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
    ) == []

    labels = runtime_labels_from_review(manifest, frame_id="map")
    label_ids = {label["label_id"] for label in labels}

    assert label_ids == {"meeting_room_a", "meeting_room_b", "meeting_room_c"}
    assert {"reception_area_a", "short_corridor_a", "storage_room_a"} - label_ids == {
        "reception_area_a",
        "short_corridor_a",
        "storage_room_a",
    }


def test_runtime_compiler_preserves_raw_navigation_layers(tmp_path: Path) -> None:
    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
        output_dir=tmp_path / "runtime",
    )
    output_dir = Path(result["output_dir"])
    raw_semantics = json.loads((MAP12_BUNDLE / "semantics.json").read_text(encoding="utf-8"))
    runtime_semantics = json.loads((output_dir / "semantics.json").read_text(encoding="utf-8"))

    assert result["status"] == "compiled"
    assert validate_nav2_map_bundle(output_dir).ok
    assert runtime_semantics["rooms"] == raw_semantics["rooms"]
    assert runtime_semantics["inspection_waypoints"] == raw_semantics["inspection_waypoints"]
    assert runtime_semantics["driveable_ways"] == raw_semantics["driveable_ways"]
    assert runtime_semantics["fixtures"] == raw_semantics["fixtures"]
    assert runtime_semantics["provenance"]["generated_from_review_manifest"] is True
    assert {label["label_id"] for label in runtime_semantics["review_labels"]} == {
        "meeting_room_a",
        "meeting_room_b",
        "meeting_room_c",
    }
    assert (output_dir / "b1_runtime_provenance.json").is_file()
    assert (output_dir / "review_labels_topdown.png").is_file()


def test_runtime_compiler_rejects_duplicate_accepted_shared_area(tmp_path: Path) -> None:
    manifest = _review_manifest()
    for label in manifest["labels"]:
        if label["label_id"] in {"reception_area_a", "storage_room_a"}:
            label["review_status"] = "accepted"

    path = tmp_path / "review.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="accepted labels share geometry"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_allows_explicit_composite_shared_area(tmp_path: Path) -> None:
    manifest = _review_manifest()
    for label in manifest["labels"]:
        if label["label_id"] in {"reception_area_a", "storage_room_a"}:
            label["review_status"] = "accepted"
            label["shared_area_policy"] = "composite_area"

    path = tmp_path / "review.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=path,
        output_dir=tmp_path / "runtime",
    )

    assert result["runtime_label_count"] == 5


def _review_manifest() -> dict:
    return copy.deepcopy(json.loads(REVIEW_MANIFEST.read_text(encoding="utf-8")))

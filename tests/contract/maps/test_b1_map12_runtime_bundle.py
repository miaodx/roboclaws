from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.maps.bundle import validate_nav2_map_bundle
from scripts.isaac_lab_cleanup.check_b1_map12_readiness import NAVIGATION_PROVENANCE
from scripts.maps.compile_b1_map12_runtime_bundle import (
    B1_MAP12_ALIGNMENT_REVIEW_SCHEMA,
    compile_runtime_bundle,
    review_manifest_errors,
    runtime_labels_from_review,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
MAP12_BUNDLE = (
    REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / ("robot_map_12") / "agibot"
)
REMOVED_AUTHORED_BUNDLE = REPO_ROOT / "assets" / "maps" / "agibot-robot-map-12"
SCENE_ROOT = REPO_ROOT / "data" / "robot-data-lab" / "scene-engine" / "data" / "2rd_floor_seperated"
REVIEW_MANIFEST = REPO_ROOT / "assets" / "maps" / "b1-map12-alignment-review.json"


def test_checked_in_review_manifest_blocks_shared_south_area_from_runtime() -> None:
    manifest = _review_manifest()

    assert not REMOVED_AUTHORED_BUNDLE.exists()
    assert manifest["schema"] == B1_MAP12_ALIGNMENT_REVIEW_SCHEMA
    assert (
        review_manifest_errors(
            manifest,
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
        )
        == []
    )

    labels = runtime_labels_from_review(manifest, frame_id="map")
    label_ids = {label["label_id"] for label in labels}

    assert label_ids == {"meeting_room_a", "meeting_room_b", "meeting_room_c"}
    assert {"reception_area_a", "short_corridor_a", "storage_room_a"} - label_ids == {
        "reception_area_a",
        "short_corridor_a",
        "storage_room_a",
    }


def test_runtime_compiler_uses_vendor_map12_and_review_labels(tmp_path: Path) -> None:
    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
        output_dir=tmp_path / "runtime",
    )
    output_dir = Path(result["output_dir"])
    runtime_semantics = json.loads((output_dir / "semantics.json").read_text(encoding="utf-8"))

    assert result["status"] == "compiled"
    assert validate_nav2_map_bundle(output_dir).ok
    assert len(runtime_semantics["rooms"]) == 3
    assert runtime_semantics["fixtures"] == []
    assert len(runtime_semantics["navigation_memory_anchors"]) == 9
    assert all(
        waypoint["waypoint_source"] == "generated_exploration_candidate"
        for waypoint in runtime_semantics["inspection_waypoints"]
    )
    assert runtime_semantics["provenance"]["generated_from_review_manifest"] is True
    assert runtime_semantics["provenance"]["raw_map_bundle"].endswith(
        "vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot"
    )
    assert {label["label_id"] for label in runtime_semantics["review_labels"]} == {
        "meeting_room_a",
        "meeting_room_b",
        "meeting_room_c",
    }
    assert (output_dir / "b1_runtime_provenance.json").is_file()
    assert (output_dir / "review_labels_topdown.png").is_file()
    proof = runtime_semantics["digital_twin_capabilities"]["robot_consumption_proof"]
    assert proof["status"] == "blocked_missing_verified_alignment"
    assert proof["robot_navigation_supported"] is False
    assert runtime_semantics["spatial_contract"]["alignment_status"] == "candidate"


def test_runtime_compiler_materializes_verified_robot_consumption_proof(
    tmp_path: Path,
) -> None:
    alignment_path = tmp_path / "alignment_residuals.json"
    navigation_path = tmp_path / "navigation_smoke.json"
    alignment_path.write_text(json.dumps(_verified_alignment_artifact()), encoding="utf-8")
    navigation_path.write_text(
        json.dumps(_navigation_artifact(tmp_path, alignment_path=alignment_path)),
        encoding="utf-8",
    )

    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
        alignment_artifact_path=alignment_path,
        navigation_artifact_path=navigation_path,
        output_dir=tmp_path / "runtime",
    )
    output_dir = Path(result["output_dir"])
    runtime_semantics = json.loads((output_dir / "semantics.json").read_text(encoding="utf-8"))
    provenance = json.loads((output_dir / "b1_runtime_provenance.json").read_text(encoding="utf-8"))
    proof = runtime_semantics["digital_twin_capabilities"]["robot_consumption_proof"]

    assert result["robot_navigation_supported"] is True
    assert validate_nav2_map_bundle(output_dir).ok
    assert runtime_semantics["spatial_contract"]["alignment_status"] == "verified"
    assert proof["status"] == "robot_navigation_verified"
    assert proof["alignment_status"] == "verified"
    assert proof["navigation_status"] == "verified"
    assert proof["robot_navigation_supported"] is True
    assert proof["robot_navigation_provenance"] == NAVIGATION_PROVENANCE
    assert proof["navigation_waypoint_count"] == 2
    assert proof["waypoint_ids"] == ["wp_1", "wp_2"]
    assert proof["alignment_artifact"] == str(alignment_path)
    assert proof["navigation_artifact"] == str(navigation_path)
    assert proof["manipulation_supported"] is False
    assert runtime_semantics["provenance"]["contains_private_scoring_truth"] is False
    assert runtime_semantics["provenance"]["contains_runtime_observations"] is False
    assert runtime_semantics["provenance"]["contains_verified_robot_consumption_proof"] is True
    assert provenance["robot_consumption_proof"]["robot_navigation_supported"] is True


def test_runtime_compiler_rejects_navigation_without_alignment(
    tmp_path: Path,
) -> None:
    navigation_path = tmp_path / "navigation_smoke.json"
    navigation_path.write_text(
        json.dumps(_navigation_artifact(tmp_path, alignment_path=tmp_path / "missing.json")),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="navigation artifact requires --alignment-artifact"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            navigation_artifact_path=navigation_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_navigation_alignment_mismatch(
    tmp_path: Path,
) -> None:
    alignment_path = tmp_path / "alignment_residuals.json"
    other_alignment_path = tmp_path / "other_alignment_residuals.json"
    navigation_path = tmp_path / "navigation_smoke.json"
    alignment_path.write_text(json.dumps(_verified_alignment_artifact()), encoding="utf-8")
    navigation_path.write_text(
        json.dumps(_navigation_artifact(tmp_path, alignment_path=other_alignment_path)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="navigation artifact alignment_artifact must match"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            alignment_artifact_path=alignment_path,
            navigation_artifact_path=navigation_path,
            output_dir=tmp_path / "runtime",
        )


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


def _verified_alignment_artifact() -> dict:
    return {
        "schema": "b1_map12_scene_alignment_residuals_v1",
        "bbox_seed_policy": "known_poor_seed_only",
        "manipulation_supported": False,
        "object_receptacle_usd_binding_status": "blocked_out_of_scope",
        "global_alignment_status": "verified",
        "selected_transform_type": "rigid_2d",
        "selected_transform": {
            "source": "reviewed_correspondence_fit",
            "type": "rigid_2d",
        },
        "residual_evidence": {
            "status": "available",
            "matched_anchor_count": 6,
            "transform_source": "reviewed_correspondence_fit",
            "mean_residual_m": 0.1,
            "median_residual_m": 0.1,
            "p90_residual_m": 0.2,
            "max_residual_m": 0.3,
        },
        "area_alignment": [],
    }


def _navigation_artifact(tmp_path: Path, *, alignment_path: Path) -> dict:
    first = tmp_path / "first.fpv.png"
    second = tmp_path / "second.fpv.png"
    _write_reviewable_image(first, offset=0)
    _write_reviewable_image(second, offset=40)
    return {
        "schema": "b1_map12_navigation_smoke_v1",
        "status": "passed",
        "robot_navigation_supported": True,
        "robot_navigation_provenance": NAVIGATION_PROVENANCE,
        "navigation_provenance": "kinematic_pose_driven",
        "alignment_artifact": str(alignment_path),
        "alignment_transform_source": "reviewed_correspondence_fit",
        "planner_backed": False,
        "physical_robot": False,
        "semantic_source": "robot_map_12_navigation_memory_overlay",
        "semantic_usd_binding_status": "blocked_until_segmentation_or_manifest",
        "semantic_anchors_are_usd_truth": False,
        "usd_object_index_ready": False,
        "usd_receptacle_index_ready": False,
        "manipulation_supported": False,
        "navigation_waypoint_count": 2,
        "robot_view_evidence_status": "available",
        "waypoint_evidence": [
            {
                "waypoint_id": "wp_1",
                "robot_pose": {
                    "frame": "b1_rebuilt_scene_usd_world_candidate",
                    "x": -4.0,
                    "y": -8.0,
                    "z": 0.0,
                    "yaw_deg": 0.0,
                },
                "robot_pose_applied": True,
                "alignment_artifact": str(alignment_path),
                "alignment_transform_source": "reviewed_correspondence_fit",
                "views": {"fpv": str(first)},
            },
            {
                "waypoint_id": "wp_2",
                "robot_pose": {
                    "frame": "b1_rebuilt_scene_usd_world_candidate",
                    "x": -2.0,
                    "y": -7.0,
                    "z": 0.0,
                    "yaw_deg": 0.0,
                },
                "robot_pose_applied": True,
                "alignment_artifact": str(alignment_path),
                "alignment_transform_source": "reviewed_correspondence_fit",
                "views": {"fpv": str(second)},
            },
        ],
    }


def _write_reviewable_image(path: Path, *, offset: int) -> None:
    image = Image.new("RGB", (32, 24))
    pixels = image.load()
    for y in range(image.height):
        for x in range(image.width):
            pixels[x, y] = (
                (x * 7 + offset) % 256,
                (y * 11 + offset * 2) % 256,
                ((x + y) * 5 + offset * 3) % 256,
            )
    image.save(path)

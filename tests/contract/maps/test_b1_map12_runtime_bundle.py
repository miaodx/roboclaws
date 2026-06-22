from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
from PIL import Image

from roboclaws.maps.bundle import validate_nav2_map_bundle
from roboclaws.maps.runtime_prior_snapshot import (
    materialize_runtime_prior_targets,
    runtime_metric_map_from_prior_artifact,
    runtime_prior_snapshot_from_nav2_cleanup_bundle,
)
from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (
    DEFAULT_B1_VISUAL_ROUTE_SCENE_USD,
    NAVIGATION_PROVENANCE,
)
from scripts.maps.compile_b1_map12_runtime_bundle import (
    B1_MAP12_ALIGNMENT_REVIEW_SCHEMA,
    B1_ROBOT_CONSUMPTION_MANIFEST_SCHEMA,
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
    assert (output_dir / "b1_robot_consumption_manifest.json").is_file()
    assert not (output_dir / "review_labels_topdown.png").exists()
    proof = runtime_semantics["digital_twin_capabilities"]["robot_consumption_proof"]
    render_proof = runtime_semantics["digital_twin_capabilities"]["render_observation_proof"]
    room_proof = runtime_semantics["digital_twin_capabilities"]["room_semantic_projection_proof"]
    manifest = json.loads(
        (output_dir / "b1_robot_consumption_manifest.json").read_text(encoding="utf-8")
    )
    assert proof["status"] == "blocked_missing_verified_alignment"
    assert proof["robot_navigation_supported"] is False
    assert render_proof["status"] == "blocked_missing_verified_same_pose_render_evidence"
    assert render_proof["render_observation_supported"] is False
    assert render_proof["default_visual_route"]["scene_id"] == "B1_floor2_slow"
    assert render_proof["default_visual_route"]["selected"] is False
    assert (
        render_proof["default_visual_route"]["status"]
        == "blocked_missing_verified_b1_floor2_slow_render_proof"
    )
    assert room_proof["status"] == "blocked_missing_accepted_semantic_anchors"
    assert room_proof["room_semantics_supported"] is False
    assert room_proof["object_projection_status"] == "blocked_until_object_semantic_anchors"
    assert runtime_semantics["spatial_contract"]["alignment_status"] == "candidate"
    assert manifest["schema"] == B1_ROBOT_CONSUMPTION_MANIFEST_SCHEMA
    assert manifest["status"] == "blocked"
    assert manifest["capabilities"]["robot_navigation"] is False
    assert manifest["capabilities"]["room_semantics"] is False
    assert manifest["capabilities"]["object_semantics"] is False
    assert manifest["policy"]["no_output_directory_autodiscovery"] is True


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
    manifest = json.loads(
        (output_dir / "b1_robot_consumption_manifest.json").read_text(encoding="utf-8")
    )

    assert result["robot_navigation_supported"] is True
    assert result["robot_consumption_manifest"] == str(
        output_dir / "b1_robot_consumption_manifest.json"
    )
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
    assert manifest["status"] == "robot_navigation_ready"
    assert manifest["navigation"]["ready"] is True
    assert manifest["navigation"]["waypoint_ids"] == ["wp_1", "wp_2"]
    assert manifest["capabilities"]["robot_navigation"] is True
    assert manifest["capabilities"]["room_semantics"] is False
    assert manifest["blocked_capabilities"][0]["capability"] == "room_semantics"


def test_runtime_compiler_materializes_verified_room_semantic_projection(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "semantic_projection.json"
    projection_path.write_text(
        json.dumps(_semantic_projection_artifact(review_manifest_path=REVIEW_MANIFEST)),
        encoding="utf-8",
    )

    result = compile_runtime_bundle(
        map_bundle=MAP12_BUNDLE,
        scene_root=SCENE_ROOT,
        review_manifest_path=REVIEW_MANIFEST,
        semantic_projection_artifact_path=projection_path,
        output_dir=tmp_path / "runtime",
    )
    output_dir = Path(result["output_dir"])
    runtime_semantics = json.loads((output_dir / "semantics.json").read_text(encoding="utf-8"))
    provenance = json.loads((output_dir / "b1_runtime_provenance.json").read_text(encoding="utf-8"))
    room_proof = runtime_semantics["digital_twin_capabilities"]["room_semantic_projection_proof"]
    manifest = json.loads(
        (output_dir / "b1_robot_consumption_manifest.json").read_text(encoding="utf-8")
    )

    assert result["room_semantics_supported"] is True
    assert validate_nav2_map_bundle(output_dir).ok
    assert runtime_semantics["spatial_contract"]["alignment_status"] == "candidate"
    assert room_proof["status"] == "verified_room_semantics"
    assert room_proof["semantic_projection_artifact"] == str(projection_path)
    assert room_proof["room_semantics_supported"] is True
    assert room_proof["room_projection_count"] == 1
    assert room_proof["semantic_anchor_count"] == 1
    assert room_proof["object_projection_status"] == "blocked_until_object_semantic_anchors"
    assert runtime_semantics["provenance"]["contains_verified_room_semantics"] is True
    assert provenance["room_semantic_projection_proof"]["room_semantics_supported"] is True
    assert str(projection_path) in provenance["source_file_hashes"]
    assert [room["room_id"] for room in runtime_semantics["rooms"]] == ["meeting_room_a"]
    room = runtime_semantics["rooms"][0]
    assert room["alignment_status"] == "verified"
    assert room["polygon_usage"]["semantic_labeling"] == "verified"
    assert room["semantic_anchor_count"] == 1
    assert room["source_anchor_ids"] == ["semantic_meeting_room_a"]
    assert runtime_semantics["inspection_waypoints"][0]["room_id"] == "meeting_room_a"
    assert manifest["capabilities"]["room_semantics"] is True
    assert manifest["semantics"]["room_projection_count"] == 1
    assert manifest["semantics"]["object_projection_status"] == (
        "blocked_until_object_semantic_anchors"
    )


@pytest.mark.parametrize(
    ("source_text", "expected_error"),
    [
        (
            "{not-json\n",
            r"review manifest must contain valid JSON object: .*review\.json",
        ),
        (
            "[]\n",
            r"review manifest must contain a JSON object: .*review\.json",
        ),
    ],
)
def test_runtime_compiler_rejects_bad_review_manifest_source(
    tmp_path: Path,
    source_text: str,
    expected_error: str,
) -> None:
    review_path = tmp_path / "review.json"
    review_path.write_text(source_text, encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=review_path,
            output_dir=tmp_path / "runtime",
        )


@pytest.mark.parametrize(
    ("artifact_kind", "source_text", "expected_error"),
    [
        (
            "alignment",
            "{not-json\n",
            r"alignment artifact must contain valid JSON object: .*alignment_residuals\.json",
        ),
        (
            "alignment",
            "[]\n",
            r"alignment artifact must contain a JSON object: .*alignment_residuals\.json",
        ),
        (
            "navigation",
            "{not-json\n",
            r"navigation artifact must contain valid JSON object: .*navigation_smoke\.json",
        ),
        (
            "navigation",
            "[]\n",
            r"navigation artifact must contain a JSON object: .*navigation_smoke\.json",
        ),
    ],
)
def test_runtime_compiler_rejects_bad_robot_consumption_proof_artifact_sources(
    tmp_path: Path,
    artifact_kind: str,
    source_text: str,
    expected_error: str,
) -> None:
    alignment_path = tmp_path / "alignment_residuals.json"
    navigation_path = tmp_path / "navigation_smoke.json"
    if artifact_kind == "alignment":
        alignment_path.write_text(source_text, encoding="utf-8")
        navigation_artifact_path = None
    else:
        alignment_path.write_text(json.dumps(_verified_alignment_artifact()), encoding="utf-8")
        navigation_path.write_text(source_text, encoding="utf-8")
        navigation_artifact_path = navigation_path

    with pytest.raises(
        ValueError,
        match=expected_error,
    ):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            alignment_artifact_path=alignment_path,
            navigation_artifact_path=navigation_artifact_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_bundle_exports_canonical_runtime_map_prior_snapshot(
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

    snapshot = runtime_prior_snapshot_from_nav2_cleanup_bundle(result["output_dir"])
    materialized = materialize_runtime_prior_targets(snapshot)
    runtime_map = runtime_metric_map_from_prior_artifact(snapshot)

    assert snapshot["schema"] == "runtime_map_prior_snapshot_v1"
    assert snapshot["producer"]["type"] == "offline_nav2_cleanup_bundle_conversion"
    assert snapshot["contract"]["online_offline_equivalent_shape"] is True
    assert snapshot["contract"]["private_truth_included"] is False
    assert snapshot["source_navigation_map"]["source_type"] == "nav2_cleanup_bundle"
    assert (
        snapshot["source_navigation_map"]["digital_twin_capabilities"]["robot_consumption_proof"][
            "robot_navigation_supported"
        ]
        is True
    )
    assert runtime_map["schema"] == "runtime_metric_map_v1"
    assert (
        runtime_map["digital_twin_capabilities"]["robot_consumption_proof"][
            "robot_navigation_supported"
        ]
        is True
    )
    assert (
        runtime_map["digital_twin_capabilities"]["render_observation_proof"][
            "render_observation_supported"
        ]
        is True
    )
    assert (
        runtime_map["digital_twin_capabilities"]["render_observation_proof"][
            "default_visual_route"
        ]["selected"]
        is True
    )
    assert snapshot["inspection_waypoints"]
    assert snapshot["public_semantic_anchors"]
    assert materialized["actionable_waypoint_ids"]
    assert materialized["fixture_candidates"] == []
    assert (
        materialized["capability_summary"]["robot_consumption_status"]
        == "robot_navigation_verified"
    )
    assert materialized["capability_summary"]["robot_navigation_supported"] is True
    assert materialized["capability_summary"]["render_observation_supported"] is True
    assert materialized["capability_summary"]["same_pose_fpv_supported"] is True
    assert materialized["capability_summary"]["same_pose_chase_supported"] is True
    assert materialized["capability_summary"]["same_pose_topdown_supported"] is True
    assert materialized["capability_summary"]["default_visual_route_status"] == (
        "selected_verified_same_pose_render_route"
    )
    assert materialized["capability_summary"]["default_visual_route_selected"] is True
    assert materialized["capability_summary"]["room_semantics_supported"] is False
    assert materialized["capability_summary"]["object_projection_status"] == (
        "blocked_until_object_semantic_anchors"
    )
    assert materialized["digital_twin_capabilities"]["robot_consumption_proof"][
        "navigation_artifact"
    ] == str(navigation_path)


def test_runtime_compiler_rejects_missing_semantic_projection_artifact(
    tmp_path: Path,
) -> None:
    with pytest.raises(ValueError, match="semantic projection artifact missing"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            semantic_projection_artifact_path=tmp_path / "missing.json",
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_malformed_semantic_projection_artifact(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "semantic_projection.json"
    projection_path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            r"semantic projection artifact must contain valid JSON object: "
            r".*semantic_projection\.json"
        ),
    ):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            semantic_projection_artifact_path=projection_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_non_object_semantic_projection_artifact(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "semantic_projection.json"
    projection_path.write_text("[]\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=(
            r"semantic projection artifact must contain a JSON object: "
            r".*semantic_projection\.json"
        ),
    ):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            semantic_projection_artifact_path=projection_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_semantic_projection_review_mismatch(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "semantic_projection.json"
    projection = _semantic_projection_artifact(review_manifest_path=tmp_path / "other_review.json")
    projection_path.write_text(json.dumps(projection), encoding="utf-8")

    with pytest.raises(ValueError, match="source_review_manifest must match"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            semantic_projection_artifact_path=projection_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_malformed_semantic_projection_room(
    tmp_path: Path,
) -> None:
    projection_path = tmp_path / "semantic_projection.json"
    projection = _semantic_projection_artifact(review_manifest_path=REVIEW_MANIFEST)
    projection["rooms"] = ["meeting_room_a"]
    projection_path.write_text(json.dumps(projection), encoding="utf-8")

    with pytest.raises(ValueError, match=r"rooms\[1\]: room must be an object"):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            semantic_projection_artifact_path=projection_path,
            output_dir=tmp_path / "runtime",
        )


@pytest.mark.parametrize(
    ("navigation_memory", "expected_error"),
    [
        (
            [],
            r"navigation memory must contain a JSON object: .*navigation_memory\.json",
        ),
        (
            {},
            "navigation_memory.json must contain a non-empty items list "
            "or catalog.navigation_memory list",
        ),
        (
            {"items": []},
            "navigation_memory.json items must be a non-empty list",
        ),
        (
            {"items": [[]]},
            "navigation_memory.json item 1 must be a JSON object",
        ),
        (
            {"items": [{"id": "bad_anchor", "nav_goal": {"x": "bad", "y": 1.0}}]},
            "navigation_memory.json item bad_anchor nav_goal x must be a finite number",
        ),
    ],
)
def test_runtime_compiler_rejects_malformed_navigation_memory_sources(
    tmp_path: Path,
    navigation_memory: object,
    expected_error: str,
) -> None:
    navigation_memory_path = tmp_path / "navigation_memory.json"
    navigation_memory_path.write_text(json.dumps(navigation_memory), encoding="utf-8")

    with pytest.raises(ValueError, match=expected_error):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            navigation_memory_path=navigation_memory_path,
            output_dir=tmp_path / "runtime",
        )


def test_runtime_compiler_rejects_malformed_navigation_memory_json(tmp_path: Path) -> None:
    navigation_memory_path = tmp_path / "navigation_memory.json"
    navigation_memory_path.write_text("{not-json\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match=r"navigation memory must contain valid JSON object: .*navigation_memory\.json",
    ):
        compile_runtime_bundle(
            map_bundle=MAP12_BUNDLE,
            scene_root=SCENE_ROOT,
            review_manifest_path=REVIEW_MANIFEST,
            navigation_memory_path=navigation_memory_path,
            output_dir=tmp_path / "runtime",
        )


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
    first_chase = tmp_path / "first.chase.png"
    second_chase = tmp_path / "second.chase.png"
    first_topdown = tmp_path / "first.map.png"
    second_topdown = tmp_path / "second.map.png"
    _write_reviewable_image(first, offset=0)
    _write_reviewable_image(second, offset=40)
    _write_reviewable_image(first_chase, offset=80)
    _write_reviewable_image(second_chase, offset=120)
    _write_reviewable_image(first_topdown, offset=160)
    _write_reviewable_image(second_topdown, offset=200)
    return {
        "schema": "b1_map12_navigation_smoke_v1",
        "status": "passed",
        "b1_scene_usd": str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD),
        "visual_route": {
            "scene_id": "B1_floor2_slow",
            "scene_usd": str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD),
            "selected": True,
            "status": "same_pose_render_verified",
        },
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
                "scene_usd": str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD),
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
                "views": {"fpv": str(first), "chase": str(first_chase), "map": str(first_topdown)},
            },
            {
                "waypoint_id": "wp_2",
                "scene_usd": str(DEFAULT_B1_VISUAL_ROUTE_SCENE_USD),
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
                "views": {
                    "fpv": str(second),
                    "chase": str(second_chase),
                    "map": str(second_topdown),
                },
            },
        ],
    }


def _semantic_projection_artifact(*, review_manifest_path: Path) -> dict:
    review = _review_manifest()
    label = next(item for item in review["labels"] if item["label_id"] == "meeting_room_a")
    map_polygon = [
        {"x": float(point["x"]), "y": float(point["y"])} for point in label["geometry"]["points"]
    ]
    return {
        "schema": "b1_map12_semantic_projection_v1",
        "status": "verified_room_semantics",
        "source_correspondences": "assets/maps/b1-map12-scene-correspondences.json",
        "source_review_manifest": str(review_manifest_path),
        "source_map_frame": "robot_map_12",
        "target_scene_frame": "b1_rebuilt_scene_usd_world_candidate",
        "semantic_anchor_count": 1,
        "room_projection_count": 1,
        "rooms": [
            {
                "room_id": "meeting_room_a",
                "room_label": "Meeting room A",
                "category": "meeting_room",
                "navigation_area_id": "west_corridor",
                "asset_partition_id": "meeting_room_a",
                "semantic_anchor_count": 1,
                "semantic_anchors": [
                    {
                        "source_anchor_id": "semantic_meeting_room_a",
                        "map_xy": [-5.0, -6.0],
                        "scene_xyz": [1.0, 2.0, 0.0],
                    }
                ],
                "map_polygon": map_polygon,
                "alignment_status": "accepted_semantic_anchor",
                "semantic_source": "reviewed_b1_map12_semantic_anchor",
                "review_status": "accepted",
                "source_label_id": "meeting_room_a",
                "source_anchor_ids": ["semantic_meeting_room_a"],
            }
        ],
        "object_projection_status": "blocked_until_object_semantic_anchors",
        "objects": [],
        "policy": {
            "requires_promoted_correspondence_manifest": True,
            "requires_accepted_semantic_anchors": True,
            "proposed_anchors_are_rejected": True,
            "object_labels_are_not_inferred_from_room_anchors": True,
        },
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

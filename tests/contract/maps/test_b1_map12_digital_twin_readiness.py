from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from scripts.isaac_lab_cleanup.check_b1_map12_readiness import (
    NAVIGATION_PROVENANCE,
    NAVIGATION_SMOKE_SCHEMA,
    READINESS_SCHEMA,
    SEMANTIC_SOURCE,
    SEMANTIC_USD_BLOCKED,
    readiness_artifact_with_navigation,
    validate_navigation_smoke_artifact,
    validate_readiness_artifact,
)


def static_readiness_payload() -> dict[str, object]:
    return {
        "schema": READINESS_SCHEMA,
        "static_precheck_only": True,
        "b1_geometry_loaded": True,
        "b1_geometry_source": "coarse_usd_or_obj",
        "usd_object_index_ready": False,
        "usd_receptacle_index_ready": False,
        "map12_overlay_status": "candidate",
        "map12_to_b1_usd_transform_status": "unverified",
        "semantic_source": SEMANTIC_SOURCE,
        "semantic_usd_binding_status": SEMANTIC_USD_BLOCKED,
        "semantic_anchors_are_usd_truth": False,
        "robot_navigation_supported": False,
        "robot_navigation_provenance": "pending_local_isaac_b1_map12_navigation_smoke",
        "navigation_waypoint_count": 0,
        "robot_view_evidence_status": "pending_local_isaac_navigation_smoke",
        "manipulation_supported": False,
    }


def navigation_payload(tmp_path: Path, *, same_pose: bool = False) -> dict[str, object]:
    first = tmp_path / "first.fpv.png"
    second = tmp_path / "second.fpv.png"
    Image.new("RGB", (12, 8), color=(10, 40, 90)).save(first)
    Image.new("RGB", (12, 8), color=(90, 40, 10)).save(second)
    pose_1 = {
        "frame": "b1_livingroom_usd_world_candidate",
        "x": -4.0,
        "y": -8.0,
        "z": 0.0,
        "yaw_deg": 0.0,
    }
    pose_2 = dict(pose_1 if same_pose else {**pose_1, "x": -2.0, "y": -7.0})
    return {
        "schema": NAVIGATION_SMOKE_SCHEMA,
        "status": "passed",
        "robot_navigation_supported": True,
        "robot_navigation_provenance": NAVIGATION_PROVENANCE,
        "navigation_provenance": "kinematic_pose_driven",
        "planner_backed": False,
        "physical_robot": False,
        "semantic_source": SEMANTIC_SOURCE,
        "semantic_usd_binding_status": SEMANTIC_USD_BLOCKED,
        "semantic_anchors_are_usd_truth": False,
        "usd_object_index_ready": False,
        "usd_receptacle_index_ready": False,
        "manipulation_supported": False,
        "navigation_waypoint_count": 2,
        "robot_view_evidence_status": "available",
        "waypoint_evidence": [
            {"waypoint_id": "wp_1", "robot_pose": pose_1, "views": {"fpv": str(first)}},
            {"waypoint_id": "wp_2", "robot_pose": pose_2, "views": {"fpv": str(second)}},
        ],
    }


def test_static_readiness_does_not_claim_navigation_or_manipulation() -> None:
    errors = validate_readiness_artifact(static_readiness_payload())

    assert errors == []


def test_static_readiness_rejects_robot_navigation_claim() -> None:
    payload = static_readiness_payload()
    payload["robot_navigation_supported"] = True
    payload["robot_navigation_provenance"] = NAVIGATION_PROVENANCE
    payload["navigation_waypoint_count"] = 2
    payload["robot_view_evidence_status"] = "available"

    errors = validate_readiness_artifact(payload)

    assert "static-only readiness must not claim robot navigation support" in errors


def test_readiness_rejects_usd_semantic_and_manipulation_claims() -> None:
    payload = static_readiness_payload()
    payload["usd_object_index_ready"] = True
    payload["usd_receptacle_index_ready"] = True
    payload["semantic_source"] = "usd_segmentation"
    payload["semantic_usd_binding_status"] = "ready"
    payload["semantic_anchors_are_usd_truth"] = True
    payload["manipulation_supported"] = True

    errors = validate_readiness_artifact(payload)

    assert "B1 USD object index must remain false until segmentation or manifest exists" in errors
    assert (
        "B1 USD receptacle index must remain false until segmentation or manifest exists" in errors
    )
    assert "semantic source must be Map 12 navigation-memory overlay" in errors
    assert "semantic USD binding must remain blocked" in errors
    assert "semantic anchors must not be presented as USD prim truth" in errors
    assert "manipulation must not be presented as supported" in errors


def test_navigation_artifact_accepts_distinct_pose_robot_view_evidence(tmp_path: Path) -> None:
    payload = navigation_payload(tmp_path)

    errors = validate_navigation_smoke_artifact(payload, require_files=True)

    assert errors == []


def test_navigation_artifact_rejects_same_pose_evidence(tmp_path: Path) -> None:
    payload = navigation_payload(tmp_path, same_pose=True)

    errors = validate_navigation_smoke_artifact(payload, require_files=True)

    assert "navigation waypoint robot poses must be distinct" in errors


def test_navigation_artifact_rejects_semantic_usd_or_manipulation_claim(tmp_path: Path) -> None:
    payload = navigation_payload(tmp_path)
    payload["semantic_source"] = "usd_segmentation"
    payload["semantic_usd_binding_status"] = "ready"
    payload["manipulation_supported"] = True

    errors = validate_navigation_smoke_artifact(payload, require_files=True)

    assert "navigation semantic source must remain Map 12 overlay" in errors
    assert "navigation artifact must not claim semantic USD binding" in errors
    assert "navigation artifact must not claim manipulation support" in errors


def test_readiness_merge_only_claims_navigation_after_valid_smoke(tmp_path: Path) -> None:
    readiness = static_readiness_payload()
    navigation = navigation_payload(tmp_path)

    merged = readiness_artifact_with_navigation(
        readiness,
        navigation,
        navigation_artifact_path=tmp_path / "navigation_smoke.json",
    )

    assert merged["robot_navigation_supported"] is True
    assert merged["robot_navigation_provenance"] == NAVIGATION_PROVENANCE
    assert merged["robot_view_evidence_status"] == "available"
    assert validate_readiness_artifact(merged, require_navigation_success=True) == []
    json.dumps(merged)

from __future__ import annotations

import pytest

from roboclaws.household.profiles import (
    CAMERA_LABELS_PROFILE,
    CAMERA_RAW_PROFILE,
    ISAACLAB_SUBPROCESS_BACKEND,
    ROBOT_VIEW_REPORT,
    SEMANTIC_REPORT,
    SMOKE_PROFILE,
    WORLD_LABELS_PROFILE,
    WORLD_LABELS_SANITIZED_PROFILE,
    cleanup_profile,
    cleanup_profile_metadata,
    cleanup_profile_metadata_for_run,
    cleanup_profile_names,
    validate_cleanup_profile_metadata,
)
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    RAW_FPV_ONLY_MODE,
    SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    WORLD_LABELS_DETECTION_POLICY,
)
from roboclaws.household.subprocess_backend import MOLMOSPACES_SUBPROCESS_BACKEND


def test_cleanup_profile_registry_contains_public_profiles_only() -> None:
    assert cleanup_profile_names() == (
        SMOKE_PROFILE,
        WORLD_LABELS_PROFILE,
        WORLD_LABELS_SANITIZED_PROFILE,
        CAMERA_RAW_PROFILE,
        CAMERA_LABELS_PROFILE,
    )

    for legacy_name in ("visual", "semantic", "raw-fpv", "camera_model_policy"):
        with pytest.raises(ValueError):
            cleanup_profile(legacy_name)


@pytest.mark.parametrize(
    ("profile_name", "agent_input", "perception_mode", "report"),
    [
        (SMOKE_PROFILE, "world_labels", VISIBLE_OBJECT_DETECTIONS_MODE, "semantic_report"),
        (WORLD_LABELS_PROFILE, "world_labels", VISIBLE_OBJECT_DETECTIONS_MODE, ROBOT_VIEW_REPORT),
        (
            WORLD_LABELS_SANITIZED_PROFILE,
            "sanitized_world_labels",
            VISIBLE_OBJECT_DETECTIONS_MODE,
            ROBOT_VIEW_REPORT,
        ),
        (CAMERA_RAW_PROFILE, "raw_camera", RAW_FPV_ONLY_MODE, ROBOT_VIEW_REPORT),
        (CAMERA_LABELS_PROFILE, "camera_labels", CAMERA_MODEL_POLICY_MODE, ROBOT_VIEW_REPORT),
    ],
)
def test_cleanup_profile_expands_to_contract_metadata(
    profile_name: str,
    agent_input: str,
    perception_mode: str,
    report: str,
) -> None:
    metadata = cleanup_profile_metadata(profile_name)

    validate_cleanup_profile_metadata(metadata, expected_profile=profile_name)
    assert metadata["agent_input"] == agent_input
    assert metadata["perception_mode"] == perception_mode
    assert metadata["report"] == report


def test_world_labels_sanitized_profile_is_no_destination_detector_ablation() -> None:
    metadata = cleanup_profile_metadata(WORLD_LABELS_SANITIZED_PROFILE)

    validate_cleanup_profile_metadata(metadata, expected_profile=WORLD_LABELS_SANITIZED_PROFILE)
    assert metadata["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND
    assert metadata["agent_input"] == "sanitized_world_labels"
    assert metadata["perception_mode"] == VISIBLE_OBJECT_DETECTIONS_MODE
    assert metadata["detection_exposure_policy"] == SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY
    assert "destination" in metadata["summary"].lower()
    assert "withheld" in metadata["model_input_note"].lower()


def test_world_labels_lane_is_not_image_reasoning_or_map_mode() -> None:
    metadata = cleanup_profile_metadata(WORLD_LABELS_PROFILE)

    assert metadata["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND
    assert metadata["agent_input"] == "world_labels"
    assert metadata["input_provenance"] == "simulator_state"
    assert metadata["detection_exposure_policy"] == WORLD_LABELS_DETECTION_POLICY
    assert "input lane" in metadata["summary"].lower()
    assert "not model input for this lane" in metadata["model_input_note"]
    assert "map_mode" in metadata["model_input_note"]
    assert "runtime_map_prior" in metadata["model_input_note"]
    assert "image reasoning" not in metadata["summary"].lower()
    assert "online" not in metadata["summary"].lower()
    assert "offline" not in metadata["summary"].lower()


def test_world_labels_run_metadata_can_disable_robot_view_capture() -> None:
    metadata = cleanup_profile_metadata_for_run(
        profile_name=WORLD_LABELS_PROFILE,
        backend=MOLMOSPACES_SUBPROCESS_BACKEND,
        perception_mode=VISIBLE_OBJECT_DETECTIONS_MODE,
        record_robot_views=False,
    )

    assert metadata["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND
    assert metadata["include_robot"] is True
    assert metadata["record_robot_views"] is False
    assert metadata["report"] == SEMANTIC_REPORT
    assert "robot-view timeline capture was disabled" in metadata["model_input_note"].lower()


def test_camera_raw_profile_withholds_structured_labels() -> None:
    metadata = cleanup_profile_metadata(CAMERA_RAW_PROFILE)

    assert metadata["agent_input"] == "raw_camera"
    assert metadata["perception_mode"] == RAW_FPV_ONLY_MODE
    assert "withheld" in metadata["summary"]
    assert "structured object labels" in metadata["summary"]


def test_camera_raw_run_metadata_allows_isaac_head_camera_backend() -> None:
    metadata = cleanup_profile_metadata_for_run(
        profile_name=CAMERA_RAW_PROFILE,
        backend=ISAACLAB_SUBPROCESS_BACKEND,
        perception_mode=RAW_FPV_ONLY_MODE,
        record_robot_views=True,
    )

    validate_cleanup_profile_metadata(
        metadata,
        expected_profile=CAMERA_RAW_PROFILE,
        expected_backend=ISAACLAB_SUBPROCESS_BACKEND,
        expected_perception_mode=RAW_FPV_ONLY_MODE,
    )
    assert metadata["world_backend"] == "isaac_sim"
    assert metadata["agent_input"] == "raw_camera"
    assert "Isaac" in metadata["summary"]
    assert "robot-mounted head camera" in metadata["model_input_note"]

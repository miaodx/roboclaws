from __future__ import annotations

import pytest

from roboclaws.molmo_cleanup.profiles import (
    CAMERA_LABELS_PROFILE,
    CAMERA_RAW_PROFILE,
    ROBOT_VIEW_REPORT,
    SEMANTIC_PERFORMANCE_REPORT,
    SMOKE_PROFILE,
    WORLD_LABELS_PERF_PROFILE,
    WORLD_LABELS_PROFILE,
    cleanup_profile,
    cleanup_profile_metadata,
    cleanup_profile_names,
    validate_cleanup_profile_metadata,
)
from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    RAW_FPV_ONLY_MODE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
)
from roboclaws.molmo_cleanup.subprocess_backend import MOLMOSPACES_SUBPROCESS_BACKEND


def test_cleanup_profile_registry_contains_public_profiles_only() -> None:
    assert cleanup_profile_names() == (
        SMOKE_PROFILE,
        WORLD_LABELS_PROFILE,
        WORLD_LABELS_PERF_PROFILE,
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
            WORLD_LABELS_PERF_PROFILE,
            "world_labels",
            VISIBLE_OBJECT_DETECTIONS_MODE,
            SEMANTIC_PERFORMANCE_REPORT,
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


def test_world_labels_profile_is_not_image_reasoning() -> None:
    metadata = cleanup_profile_metadata(WORLD_LABELS_PROFILE)

    assert metadata["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND
    assert metadata["agent_input"] == "world_labels"
    assert metadata["input_provenance"] == "simulator_state"
    assert "not model input" in metadata["model_input_note"]
    assert "image reasoning" not in metadata["summary"].lower()


def test_world_labels_perf_profile_skips_robot_view_capture() -> None:
    metadata = cleanup_profile_metadata(WORLD_LABELS_PERF_PROFILE)

    assert metadata["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND
    assert metadata["include_robot"] is True
    assert metadata["record_robot_views"] is False
    assert metadata["report"] == SEMANTIC_PERFORMANCE_REPORT
    assert "waypoint_honesty" in metadata["verifiers"]
    assert (
        "robot-view timeline capture is intentionally skipped"
        in metadata["model_input_note"].lower()
    )


def test_camera_raw_profile_withholds_structured_labels() -> None:
    metadata = cleanup_profile_metadata(CAMERA_RAW_PROFILE)

    assert metadata["agent_input"] == "raw_camera"
    assert metadata["perception_mode"] == RAW_FPV_ONLY_MODE
    assert "withheld" in metadata["summary"]
    assert "structured object labels" in metadata["summary"]

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboclaws.molmo_cleanup.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    RAW_FPV_ONLY_MODE,
    VISIBLE_OBJECT_DETECTIONS_MODE,
)
from roboclaws.molmo_cleanup.subprocess_backend import MOLMOSPACES_SUBPROCESS_BACKEND

CLEANUP_PROFILE_SCHEMA = "molmo_cleanup_profile_v1"

SYNTHETIC_BACKEND = "api_semantic_synthetic"

SMOKE_PROFILE = "smoke"
WORLD_LABELS_PROFILE = "world-labels"
CAMERA_RAW_PROFILE = "camera-raw"
CAMERA_LABELS_PROFILE = "camera-labels"

WORLD_LABELS_INPUT = "world_labels"
RAW_CAMERA_INPUT = "raw_camera"
CAMERA_LABELS_INPUT = "camera_labels"

SYNTHETIC_CONTRACT_PROVENANCE = "synthetic_contract"
SIMULATOR_STATE_PROVENANCE = "simulator_state"
CAMERA_ARTIFACT_PROVENANCE = "camera_artifact"
SIMULATED_CAMERA_MODEL_PROVENANCE = "simulated_camera_model"

SYNTHETIC_CONTRACT_BACKEND = "synthetic_contract"
MOLMOSPACES_SIM_BACKEND = "molmospaces_sim"

SEMANTIC_REPORT = "semantic_report"
ROBOT_VIEW_REPORT = "robot_view_report"

CONTRACT_ONLY_VERIFIER = "contract_only"
CLEANUP_SUCCESS_VERIFIER = "cleanup_success"
ROBOT_VIEW_HONESTY_VERIFIER = "robot_view_honesty"
IMAGE_INPUT_CONTRACT_VERIFIER = "image_input_contract"
REAL_ROBOT_ALIGNMENT_VERIFIER = "real_robot_alignment"


@dataclass(frozen=True)
class CleanupProfile:
    profile: str
    agent_input: str
    input_provenance: str
    world_backend: str
    report: str
    verifiers: tuple[str, ...]
    backend: str
    perception_mode: str
    include_robot: bool
    record_robot_views: bool
    requires_clean_success: bool
    summary: str
    model_input_note: str

    def metadata(self) -> dict[str, Any]:
        return {
            "schema": CLEANUP_PROFILE_SCHEMA,
            "profile": self.profile,
            "agent_input": self.agent_input,
            "input_provenance": self.input_provenance,
            "world_backend": self.world_backend,
            "report": self.report,
            "verifiers": list(self.verifiers),
            "backend": self.backend,
            "perception_mode": self.perception_mode,
            "include_robot": self.include_robot,
            "record_robot_views": self.record_robot_views,
            "requires_clean_success": self.requires_clean_success,
            "summary": self.summary,
            "model_input_note": self.model_input_note,
        }


_PROFILES: dict[str, CleanupProfile] = {
    SMOKE_PROFILE: CleanupProfile(
        profile=SMOKE_PROFILE,
        agent_input=WORLD_LABELS_INPUT,
        input_provenance=SYNTHETIC_CONTRACT_PROVENANCE,
        world_backend=SYNTHETIC_CONTRACT_BACKEND,
        report=SEMANTIC_REPORT,
        verifiers=(CONTRACT_ONLY_VERIFIER,),
        backend=SYNTHETIC_BACKEND,
        perception_mode=VISIBLE_OBJECT_DETECTIONS_MODE,
        include_robot=False,
        record_robot_views=False,
        requires_clean_success=True,
        summary="Cheap deterministic contract sanity with synthetic world labels.",
        model_input_note=(
            "The agent receives structured world labels from the synthetic contract; "
            "this profile is not a visual or image-reasoning claim."
        ),
    ),
    WORLD_LABELS_PROFILE: CleanupProfile(
        profile=WORLD_LABELS_PROFILE,
        agent_input=WORLD_LABELS_INPUT,
        input_provenance=SIMULATOR_STATE_PROVENANCE,
        world_backend=MOLMOSPACES_SIM_BACKEND,
        report=ROBOT_VIEW_REPORT,
        verifiers=(
            CLEANUP_SUCCESS_VERIFIER,
            ROBOT_VIEW_HONESTY_VERIFIER,
            REAL_ROBOT_ALIGNMENT_VERIFIER,
        ),
        backend=MOLMOSPACES_SUBPROCESS_BACKEND,
        perception_mode=VISIBLE_OBJECT_DETECTIONS_MODE,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary="Structured world-label cleanup with RBY1M robot-view report artifacts.",
        model_input_note=(
            "The agent receives observed object handles and structured labels. "
            "FPV, chase, map, and verification images are report evidence, not "
            "model input for this profile."
        ),
    ),
    CAMERA_RAW_PROFILE: CleanupProfile(
        profile=CAMERA_RAW_PROFILE,
        agent_input=RAW_CAMERA_INPUT,
        input_provenance=CAMERA_ARTIFACT_PROVENANCE,
        world_backend=MOLMOSPACES_SIM_BACKEND,
        report=ROBOT_VIEW_REPORT,
        verifiers=(IMAGE_INPUT_CONTRACT_VERIFIER, ROBOT_VIEW_HONESTY_VERIFIER),
        backend=MOLMOSPACES_SUBPROCESS_BACKEND,
        perception_mode=RAW_FPV_ONLY_MODE,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=False,
        summary="Raw camera-input contract with structured object labels withheld.",
        model_input_note=(
            "The agent receives raw camera artifacts and must not receive observed "
            "object handles, categories, support estimates, or candidate fixtures."
        ),
    ),
    CAMERA_LABELS_PROFILE: CleanupProfile(
        profile=CAMERA_LABELS_PROFILE,
        agent_input=CAMERA_LABELS_INPUT,
        input_provenance=SIMULATED_CAMERA_MODEL_PROVENANCE,
        world_backend=MOLMOSPACES_SIM_BACKEND,
        report=ROBOT_VIEW_REPORT,
        verifiers=(
            IMAGE_INPUT_CONTRACT_VERIFIER,
            CLEANUP_SUCCESS_VERIFIER,
            ROBOT_VIEW_HONESTY_VERIFIER,
        ),
        backend=MOLMOSPACES_SUBPROCESS_BACKEND,
        perception_mode=CAMERA_MODEL_POLICY_MODE,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary="Camera-derived structured-label cleanup with simulated camera-model provenance.",
        model_input_note=(
            "The agent receives camera-derived object candidates registered from raw "
            "FPV observations. Today those candidates come from deterministic "
            "simulated camera-model evidence, not real VLM pixel inference."
        ),
    ),
}


def cleanup_profile_names() -> tuple[str, ...]:
    return tuple(_PROFILES)


def cleanup_profile(name: str) -> CleanupProfile:
    normalized = normalize_cleanup_profile_name(name)
    try:
        return _PROFILES[normalized]
    except KeyError as exc:
        expected = "|".join(cleanup_profile_names())
        raise ValueError(f"unsupported cleanup profile {name!r} (expected {expected})") from exc


def cleanup_profile_metadata(name: str) -> dict[str, Any]:
    return cleanup_profile(name).metadata()


def normalize_cleanup_profile_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def infer_cleanup_profile_name(
    *,
    backend: str,
    perception_mode: str,
    record_robot_views: bool,
) -> str:
    if backend == SYNTHETIC_BACKEND:
        return SMOKE_PROFILE
    if perception_mode == RAW_FPV_ONLY_MODE:
        return CAMERA_RAW_PROFILE
    if perception_mode == CAMERA_MODEL_POLICY_MODE:
        return CAMERA_LABELS_PROFILE
    if record_robot_views:
        return WORLD_LABELS_PROFILE
    return SMOKE_PROFILE


def cleanup_profile_metadata_for_run(
    *,
    profile_name: str | None,
    backend: str,
    perception_mode: str,
    record_robot_views: bool,
) -> dict[str, Any]:
    selected_name = profile_name or infer_cleanup_profile_name(
        backend=backend,
        perception_mode=perception_mode,
        record_robot_views=record_robot_views,
    )
    profile = cleanup_profile(selected_name)
    _assert_profile_matches_run(
        profile,
        backend=backend,
        perception_mode=perception_mode,
        record_robot_views=record_robot_views,
    )
    return profile.metadata()


def validate_cleanup_profile_metadata(
    metadata: dict[str, Any],
    *,
    expected_profile: str | None = None,
    expected_backend: str | None = None,
    expected_perception_mode: str | None = None,
) -> None:
    assert metadata.get("schema") == CLEANUP_PROFILE_SCHEMA, metadata
    profile = cleanup_profile(str(metadata.get("profile", "")))
    expected = profile.metadata()
    for key in (
        "agent_input",
        "input_provenance",
        "world_backend",
        "report",
        "backend",
        "perception_mode",
        "include_robot",
        "record_robot_views",
        "requires_clean_success",
    ):
        assert metadata.get(key) == expected[key], (key, metadata, expected)
    assert metadata.get("verifiers") == expected["verifiers"], metadata
    if expected_profile is not None:
        assert metadata.get("profile") == normalize_cleanup_profile_name(expected_profile), metadata
    if expected_backend is not None:
        assert metadata.get("backend") == expected_backend, metadata
    if expected_perception_mode is not None:
        assert metadata.get("perception_mode") == expected_perception_mode, metadata


def _assert_profile_matches_run(
    profile: CleanupProfile,
    *,
    backend: str,
    perception_mode: str,
    record_robot_views: bool,
) -> None:
    if profile.backend != backend:
        raise ValueError(
            f"profile={profile.profile} requires backend={profile.backend}, got {backend}"
        )
    if profile.perception_mode != perception_mode:
        raise ValueError(
            "profile="
            f"{profile.profile} requires perception_mode={profile.perception_mode}, "
            f"got {perception_mode}"
        )
    if profile.record_robot_views and not record_robot_views:
        raise ValueError(f"profile={profile.profile} requires record_robot_views=true")

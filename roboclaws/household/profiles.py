from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    RAW_FPV_ONLY_MODE,
    SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY,
    VISIBLE_OBJECT_DETECTIONS_MODE,
    WORLD_LABELS_DETECTION_POLICY,
)
from roboclaws.household.subprocess_backend import MOLMOSPACES_SUBPROCESS_BACKEND

CLEANUP_PROFILE_SCHEMA = "cleanup_evidence_lane_v1"

SYNTHETIC_BACKEND = "api_semantic_synthetic"
ISAACLAB_SUBPROCESS_BACKEND = "isaaclab_subprocess"

SMOKE_PROFILE = "smoke"
WORLD_ORACLE_LABELS_LANE = "world-oracle-labels"
WORLD_PUBLIC_LABELS_LANE = "world-public-labels"
CAMERA_GROUNDED_LABELS_LANE = "camera-grounded-labels"
CAMERA_RAW_FPV_LANE = "camera-raw-fpv"

# Compatibility names for existing Python call sites. The public values are the
# evidence-lane names above.
WORLD_LABELS_PROFILE = WORLD_ORACLE_LABELS_LANE
WORLD_LABELS_SANITIZED_PROFILE = WORLD_PUBLIC_LABELS_LANE
CAMERA_RAW_PROFILE = CAMERA_RAW_FPV_LANE
CAMERA_LABELS_PROFILE = CAMERA_GROUNDED_LABELS_LANE

SIM_PROJECTED_LABELS_CAMERA_LABELER = "sim-projected-labels"
CAMERA_LABELERS: tuple[str, ...] = (
    SIM_PROJECTED_LABELS_CAMERA_LABELER,
    "grounding-dino",
    "yoloe",
    "omdet-turbo",
    "yolo-world",
    "fake-http",
    "contract-fake",
)

_CAMERA_LABELER_TO_VISUAL_GROUNDING_PIPELINE = {
    SIM_PROJECTED_LABELS_CAMERA_LABELER: "sim",
}
_VISUAL_GROUNDING_PIPELINE_TO_CAMERA_LABELER = {
    "sim": SIM_PROJECTED_LABELS_CAMERA_LABELER,
}

ISAAC_COMPATIBLE_PROFILES = frozenset(
    {WORLD_LABELS_PROFILE, WORLD_LABELS_SANITIZED_PROFILE, CAMERA_RAW_PROFILE}
)

WORLD_LABELS_INPUT = "world_labels"
SANITIZED_WORLD_LABELS_INPUT = "sanitized_world_labels"
RAW_CAMERA_INPUT = "raw_camera"
CAMERA_LABELS_INPUT = "camera_labels"

SYNTHETIC_CONTRACT_PROVENANCE = "synthetic_contract"
SIMULATOR_STATE_PROVENANCE = "simulator_state"
CAMERA_ARTIFACT_PROVENANCE = "camera_artifact"
SIMULATED_CAMERA_MODEL_PROVENANCE = "simulated_camera_model"

SYNTHETIC_CONTRACT_BACKEND = "synthetic_contract"
MOLMOSPACES_SIM_BACKEND = "molmospaces_sim"
ISAAC_SIM_BACKEND = "isaac_sim"

SEMANTIC_REPORT = "semantic_report"
ROBOT_VIEW_REPORT = "robot_view_report"

CONTRACT_ONLY_VERIFIER = "contract_only"
CLEANUP_SUCCESS_VERIFIER = "cleanup_success"
ROBOT_VIEW_HONESTY_VERIFIER = "robot_view_honesty"
IMAGE_INPUT_CONTRACT_VERIFIER = "image_input_contract"
REAL_ROBOT_ALIGNMENT_VERIFIER = "real_robot_alignment"
WAYPOINT_HONESTY_VERIFIER = "waypoint_honesty"


@dataclass(frozen=True)
class CleanupProfile:
    profile: str
    evidence_lane: str
    preset: str
    agent_input: str
    input_provenance: str
    world_backend: str
    report: str
    verifiers: tuple[str, ...]
    backend: str
    perception_mode: str
    detection_exposure_policy: str
    include_robot: bool
    record_robot_views: bool
    requires_clean_success: bool
    summary: str
    model_input_note: str

    def metadata(self) -> dict[str, Any]:
        metadata = {
            "schema": CLEANUP_PROFILE_SCHEMA,
            "mode": self.profile,
            "evidence_lane": self.evidence_lane,
            "agent_input": self.agent_input,
            "input_provenance": self.input_provenance,
            "world_backend": self.world_backend,
            "report": self.report,
            "verifiers": list(self.verifiers),
            "backend": self.backend,
            "perception_mode": self.perception_mode,
            "detection_exposure_policy": self.detection_exposure_policy,
            "include_robot": self.include_robot,
            "record_robot_views": self.record_robot_views,
            "requires_clean_success": self.requires_clean_success,
            "summary": self.summary,
            "model_input_note": self.model_input_note,
        }
        if self.preset:
            metadata["preset"] = self.preset
        return metadata


_PROFILES: dict[str, CleanupProfile] = {
    SMOKE_PROFILE: CleanupProfile(
        profile=SMOKE_PROFILE,
        evidence_lane=WORLD_ORACLE_LABELS_LANE,
        preset=SMOKE_PROFILE,
        agent_input=WORLD_LABELS_INPUT,
        input_provenance=SYNTHETIC_CONTRACT_PROVENANCE,
        world_backend=SYNTHETIC_CONTRACT_BACKEND,
        report=SEMANTIC_REPORT,
        verifiers=(CONTRACT_ONLY_VERIFIER,),
        backend=SYNTHETIC_BACKEND,
        perception_mode=VISIBLE_OBJECT_DETECTIONS_MODE,
        detection_exposure_policy=WORLD_LABELS_DETECTION_POLICY,
        include_robot=False,
        record_robot_views=False,
        requires_clean_success=True,
        summary="Cheap deterministic contract sanity with synthetic world labels.",
        model_input_note=(
            "The agent receives structured world labels from the synthetic contract; "
            "this preset is not a visual or image-reasoning claim."
        ),
    ),
    WORLD_LABELS_PROFILE: CleanupProfile(
        profile=WORLD_LABELS_PROFILE,
        evidence_lane=WORLD_ORACLE_LABELS_LANE,
        preset="",
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
        detection_exposure_policy=WORLD_LABELS_DETECTION_POLICY,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary=(
            "World-oracle structured-label cleanup evidence lane upper bound with RBY1M "
            "robot-view report artifacts."
        ),
        model_input_note=(
            "The agent receives observed object handles, structured labels, and "
            "cleanup-ready destination hints from simulator state. "
            "FPV, chase, map, and verification images are report evidence, not "
            "model input for this lane. This lane does not select online/offline "
            "map behavior; use map_mode and runtime_map_prior for that."
        ),
    ),
    WORLD_LABELS_SANITIZED_PROFILE: CleanupProfile(
        profile=WORLD_LABELS_SANITIZED_PROFILE,
        evidence_lane=WORLD_PUBLIC_LABELS_LANE,
        preset="",
        agent_input=SANITIZED_WORLD_LABELS_INPUT,
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
        detection_exposure_policy=SANITIZED_VISIBLE_OBJECT_DETECTIONS_POLICY,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary=(
            "World-public structured-label ablation with destination and "
            "cleanup oracle fields removed."
        ),
        model_input_note=(
            "The agent receives run-local observed object handles, categories, "
            "regions, source observations, and public support evidence from "
            "simulator labels. Candidate destinations, cleanup recommendations, "
            "and placement-tool hints are withheld so destination selection "
            "remains policy-required."
        ),
    ),
    CAMERA_RAW_PROFILE: CleanupProfile(
        profile=CAMERA_RAW_PROFILE,
        evidence_lane=CAMERA_RAW_FPV_LANE,
        preset="",
        agent_input=RAW_CAMERA_INPUT,
        input_provenance=CAMERA_ARTIFACT_PROVENANCE,
        world_backend=MOLMOSPACES_SIM_BACKEND,
        report=ROBOT_VIEW_REPORT,
        verifiers=(
            IMAGE_INPUT_CONTRACT_VERIFIER,
            CLEANUP_SUCCESS_VERIFIER,
            ROBOT_VIEW_HONESTY_VERIFIER,
        ),
        backend=MOLMOSPACES_SUBPROCESS_BACKEND,
        perception_mode=RAW_FPV_ONLY_MODE,
        detection_exposure_policy=WORLD_LABELS_DETECTION_POLICY,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary=(
            "Camera raw-FPV cleanup via model-declared visual observations with "
            "structured object labels withheld before declaration."
        ),
        model_input_note=(
            "The agent receives raw camera image blocks first, then creates "
            "model-declared observed handles from public image evidence. Structured "
            "labels remain withheld before declaration."
        ),
    ),
    CAMERA_LABELS_PROFILE: CleanupProfile(
        profile=CAMERA_LABELS_PROFILE,
        evidence_lane=CAMERA_GROUNDED_LABELS_LANE,
        preset="",
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
        detection_exposure_policy=WORLD_LABELS_DETECTION_POLICY,
        include_robot=True,
        record_robot_views=True,
        requires_clean_success=True,
        summary="Camera-grounded structured-label cleanup from FPV observations.",
        model_input_note=(
            "The agent receives camera-derived object candidates registered from raw "
            "FPV observations. camera_labeler selects the producer that turns FPV "
            "evidence into structured candidates."
        ),
    ),
}


def cleanup_evidence_lane_names() -> tuple[str, ...]:
    return (
        WORLD_ORACLE_LABELS_LANE,
        WORLD_PUBLIC_LABELS_LANE,
        CAMERA_GROUNDED_LABELS_LANE,
        CAMERA_RAW_FPV_LANE,
    )


def cleanup_profile_names() -> tuple[str, ...]:
    return tuple(_PROFILES)


def camera_labeler_names() -> tuple[str, ...]:
    return CAMERA_LABELERS


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
    normalized = name.strip().lower().replace("_", "-")
    return normalized


def normalize_camera_labeler_name(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def camera_labeler_to_visual_grounding_pipeline(camera_labeler: str) -> str:
    normalized = normalize_camera_labeler_name(camera_labeler)
    if normalized not in CAMERA_LABELERS:
        expected = "|".join(CAMERA_LABELERS)
        raise ValueError(f"unsupported camera_labeler {camera_labeler!r} (expected {expected})")
    return _CAMERA_LABELER_TO_VISUAL_GROUNDING_PIPELINE.get(normalized, normalized)


def camera_labeler_from_visual_grounding_pipeline(pipeline_id: str) -> str:
    normalized = normalize_camera_labeler_name(pipeline_id)
    return _VISUAL_GROUNDING_PIPELINE_TO_CAMERA_LABELER.get(normalized, normalized)


def validate_evidence_lane_camera_labeler(
    *,
    evidence_lane: str,
    camera_labeler: str | None,
) -> str:
    lane = normalize_cleanup_profile_name(evidence_lane)
    if lane not in cleanup_evidence_lane_names():
        expected = "|".join(cleanup_evidence_lane_names())
        raise ValueError(f"unsupported evidence_lane {evidence_lane!r} (expected {expected})")
    selected_labeler = normalize_camera_labeler_name(camera_labeler or "")
    if lane == CAMERA_GROUNDED_LABELS_LANE:
        if not selected_labeler:
            raise ValueError("evidence_lane=camera-grounded-labels requires camera_labeler")
        if selected_labeler not in CAMERA_LABELERS:
            expected = "|".join(CAMERA_LABELERS)
            raise ValueError(f"unsupported camera_labeler {camera_labeler!r} (expected {expected})")
        return selected_labeler
    if selected_labeler:
        raise ValueError(
            f"camera_labeler is only valid for evidence_lane={CAMERA_GROUNDED_LABELS_LANE}"
        )
    return ""


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
    if backend in {MOLMOSPACES_SUBPROCESS_BACKEND, ISAACLAB_SUBPROCESS_BACKEND}:
        return WORLD_LABELS_PROFILE
    return SMOKE_PROFILE


def cleanup_profile_metadata_for_run(
    *,
    profile_name: str | None,
    backend: str,
    perception_mode: str,
    record_robot_views: bool,
    camera_labeler: str | None = None,
) -> dict[str, Any]:
    selected_name = profile_name or infer_cleanup_profile_name(
        backend=backend,
        perception_mode=perception_mode,
        record_robot_views=record_robot_views,
    )
    profile = cleanup_profile(selected_name)
    selected_camera_labeler = validate_evidence_lane_camera_labeler(
        evidence_lane=profile.evidence_lane,
        camera_labeler=camera_labeler,
    )
    _assert_profile_matches_run(
        profile,
        backend=backend,
        perception_mode=perception_mode,
        record_robot_views=record_robot_views,
    )
    metadata = profile.metadata()
    if selected_camera_labeler:
        metadata["camera_labeler"] = selected_camera_labeler
    if profile.profile in ISAAC_COMPATIBLE_PROFILES and backend == ISAACLAB_SUBPROCESS_BACKEND:
        metadata["backend"] = backend
        metadata["world_backend"] = ISAAC_SIM_BACKEND
        if profile.profile == WORLD_LABELS_PROFILE:
            metadata["summary"] = (
                "Structured-label cleanup input lane with Isaac Lab semantic-pose "
                "backend artifacts."
            )
            metadata["model_input_note"] = (
                "The agent receives observed object handles and structured labels. "
                "Isaac FPV, chase, and verification images are report evidence, not "
                "model input for this lane. This lane does not select online/offline "
                "map behavior; use map_mode and runtime_map_prior for that."
            )
        elif profile.profile == WORLD_LABELS_SANITIZED_PROFILE:
            metadata["summary"] = (
                "Sanitized structured-label cleanup ablation with Isaac Lab "
                "semantic-pose backend artifacts."
            )
            metadata["model_input_note"] = (
                "The agent receives run-local observed object handles, categories, "
                "regions, source observations, and public support evidence from "
                "Isaac semantic labels. Candidate destinations, cleanup "
                "recommendations, and placement-tool hints are withheld."
            )
        elif profile.profile == CAMERA_RAW_PROFILE:
            metadata["summary"] = (
                "Raw camera-input cleanup via Isaac Lab mounted head-camera artifacts "
                "with structured object labels withheld before declaration."
            )
            metadata["model_input_note"] = (
                "The agent receives raw Isaac FPV image blocks from the robot-mounted "
                "head camera first, then creates model-declared observed handles from "
                "public image evidence. Structured labels remain withheld before declaration."
            )
    metadata["record_robot_views"] = bool(record_robot_views)
    if profile.profile in {WORLD_LABELS_PROFILE, WORLD_LABELS_SANITIZED_PROFILE} and (
        not record_robot_views
    ):
        metadata["report"] = SEMANTIC_REPORT
        metadata["model_input_note"] = (
            metadata["model_input_note"]
            + " Robot-view timeline capture was disabled for this run as an explicit "
            "evidence/capture option."
        )
    return metadata


def validate_cleanup_profile_metadata(
    metadata: dict[str, Any],
    *,
    expected_profile: str | None = None,
    expected_backend: str | None = None,
    expected_perception_mode: str | None = None,
) -> None:
    assert metadata.get("schema") == CLEANUP_PROFILE_SCHEMA, metadata
    profile = cleanup_profile(str(metadata.get("mode") or metadata.get("evidence_lane") or ""))
    expected = profile.metadata()
    for key in (
        "agent_input",
        "input_provenance",
        "perception_mode",
        "detection_exposure_policy",
        "include_robot",
        "requires_clean_success",
    ):
        assert metadata.get(key) == expected[key], (key, metadata, expected)
    if profile.profile in ISAAC_COMPATIBLE_PROFILES:
        assert metadata.get("backend") in {
            MOLMOSPACES_SUBPROCESS_BACKEND,
            ISAACLAB_SUBPROCESS_BACKEND,
        }, metadata
        assert metadata.get("world_backend") in {MOLMOSPACES_SIM_BACKEND, ISAAC_SIM_BACKEND}, (
            metadata,
            expected,
        )
    else:
        assert metadata.get("backend") == expected["backend"], metadata
        assert metadata.get("world_backend") == expected["world_backend"], metadata
    if profile.profile in {WORLD_LABELS_PROFILE, WORLD_LABELS_SANITIZED_PROFILE}:
        assert metadata.get("report") in {ROBOT_VIEW_REPORT, SEMANTIC_REPORT}, metadata
    else:
        assert metadata.get("report") == expected["report"], metadata
    assert isinstance(metadata.get("record_robot_views"), bool), metadata
    assert metadata.get("verifiers") == expected["verifiers"], metadata
    if expected_profile is not None:
        expected_name = normalize_cleanup_profile_name(expected_profile)
        expected_profile_obj = cleanup_profile(expected_name)
        assert metadata.get("mode") == expected_profile_obj.profile, metadata
        assert metadata.get("evidence_lane") == expected_profile_obj.evidence_lane, metadata
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
    if profile.profile in ISAAC_COMPATIBLE_PROFILES and backend == ISAACLAB_SUBPROCESS_BACKEND:
        pass
    elif profile.backend != backend:
        raise ValueError(
            f"profile={profile.profile} requires backend={profile.backend}, got {backend}"
        )
    if profile.perception_mode != perception_mode:
        raise ValueError(
            "profile="
            f"{profile.profile} requires perception_mode={profile.perception_mode}, "
            f"got {perception_mode}"
        )

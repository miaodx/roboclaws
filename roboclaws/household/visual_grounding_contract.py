from __future__ import annotations

import base64
import binascii
from typing import Any

VISUAL_GROUNDING_REQUEST_SCHEMA = "visual_grounding_request_v2"
VISUAL_GROUNDING_RESPONSE_SCHEMA = "visual_grounding_response_v1"
VISUAL_GROUNDING_PIPELINE_SCHEMA = "visual_grounding_pipeline_v1"
_FORBIDDEN_REQUEST_HINT_KEYS = frozenset(
    {
        "acceptable_destination_sets",
        "generated_mess_count",
        "generated_mess_set",
        "hidden_target_ids",
        "private_evaluation",
        "private_manifest",
        "private_scorer_truth",
        "relocation_manifest",
        "scenario_setup",
        "target_count",
    }
)


class VisualGroundingContractError(ValueError):
    """The service request or response did not match the public HTTP contract."""


def validate_visual_grounding_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise VisualGroundingContractError("visual grounding request must be an object")
    _require_schema(payload, VISUAL_GROUNDING_REQUEST_SCHEMA, "visual grounding request")
    _validate_request_identity(payload)
    _validate_request_image(payload.get("image"))
    _validate_request_hints(payload)
    _validate_pipeline_request(payload.get("pipeline_request"))
    return payload


def validate_visual_grounding_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise VisualGroundingContractError("visual grounding response must be an object")
    _require_schema(payload, VISUAL_GROUNDING_RESPONSE_SCHEMA, "visual grounding response")
    status = _response_status(payload)
    _validate_response_pipeline(payload.get("pipeline"), status=status)
    candidates = _response_candidates(payload, status=status)
    for candidate in candidates:
        validate_visual_grounding_candidate(candidate)
    if status == "failed":
        _validate_failure_error(payload.get("error"))
    return payload


def validate_visual_grounding_candidate(candidate: Any) -> None:
    if not isinstance(candidate, dict):
        raise VisualGroundingContractError("candidate must be an object")
    if not str(candidate.get("category") or ""):
        raise VisualGroundingContractError("candidate.category is required")
    _validate_candidate_region(candidate.get("image_region"))
    _validate_candidate_confidence(candidate.get("confidence"))


def validate_number_list(
    value: Any,
    *,
    expected: int,
    normalized: bool,
    field: str,
) -> None:
    if not isinstance(value, list) or len(value) != expected:
        raise VisualGroundingContractError(f"{field} must be a list of {expected} numbers")
    numbers = [_numeric_value(item, field=field) for item in value]
    if normalized and any(number < 0.0 or number > 1.0 for number in numbers):
        raise VisualGroundingContractError(f"{field} values must be normalized to [0, 1]")


def _require_schema(payload: dict[str, Any], schema: str, label: str) -> None:
    if payload.get("schema") != schema:
        raise VisualGroundingContractError(f"{label} schema mismatch")


def _validate_request_identity(payload: dict[str, Any]) -> None:
    for field in ("run_id", "observation_id", "waypoint_id", "room_id"):
        if not isinstance(payload.get(field), str):
            raise VisualGroundingContractError(f"{field} must be a string")


def _validate_request_image(image: Any) -> None:
    if not isinstance(image, dict):
        raise VisualGroundingContractError("image must be an object")
    if not isinstance(image.get("bytes_base64"), str):
        raise VisualGroundingContractError("image.bytes_base64 must be a string")
    if not image["bytes_base64"]:
        raise VisualGroundingContractError("image.bytes_base64 is required")
    _validate_base64(image.get("bytes_base64"))
    for field in ("width", "height"):
        if not isinstance(image.get(field), int):
            raise VisualGroundingContractError(f"image.{field} must be an integer")
        if image[field] <= 0:
            raise VisualGroundingContractError(f"image.{field} must be positive")


def _validate_base64(raw: Any) -> None:
    try:
        base64.b64decode(raw, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise VisualGroundingContractError("image.bytes_base64 is not valid base64") from exc


def _validate_request_hints(payload: dict[str, Any]) -> None:
    if not isinstance(payload.get("category_hints"), list):
        raise VisualGroundingContractError("category_hints must be a list")
    public_map_hints = payload.get("public_map_hints")
    if not isinstance(public_map_hints, dict):
        raise VisualGroundingContractError("public_map_hints must be an object")
    if not isinstance(public_map_hints.get("fixture_hints"), list):
        raise VisualGroundingContractError("public_map_hints.fixture_hints must be a list")
    if public_map_hints.get("private_truth_included") is True:
        raise VisualGroundingContractError("public_map_hints must not include private truth")
    _assert_no_forbidden_request_hint_keys(public_map_hints)
    if "static_fixture_projection" in payload:
        raise VisualGroundingContractError(
            "static_fixture_projection is not a live visual grounding request field; "
            "use public_map_hints.fixture_hints"
        )


def _assert_no_forbidden_request_hint_keys(value: Any) -> None:
    if isinstance(value, dict):
        forbidden = _FORBIDDEN_REQUEST_HINT_KEYS.intersection(value)
        if forbidden:
            raise VisualGroundingContractError(
                f"public_map_hints contains forbidden private fields: {sorted(forbidden)}"
            )
        for item in value.values():
            _assert_no_forbidden_request_hint_keys(item)
    elif isinstance(value, list):
        for item in value:
            _assert_no_forbidden_request_hint_keys(item)


def _validate_pipeline_request(pipeline_request: Any) -> None:
    if not isinstance(pipeline_request, dict) or not str(pipeline_request.get("pipeline_id") or ""):
        raise VisualGroundingContractError("pipeline_request.pipeline_id is required")


def _response_status(payload: dict[str, Any]) -> str:
    status = str(payload.get("status") or "")
    if status not in {"ok", "failed"}:
        raise VisualGroundingContractError("visual grounding status must be ok or failed")
    return status


def _validate_response_pipeline(pipeline: Any, *, status: str) -> None:
    if not isinstance(pipeline, dict) or not str(pipeline.get("pipeline_id") or ""):
        raise VisualGroundingContractError("pipeline.pipeline_id is required")
    stages = pipeline.get("stages")
    if not isinstance(stages, list) or not stages:
        raise VisualGroundingContractError("pipeline.stages must be a non-empty list")
    for stage in stages:
        _validate_pipeline_stage(stage, status=status)


def _validate_pipeline_stage(stage: Any, *, status: str) -> None:
    if not isinstance(stage, dict):
        raise VisualGroundingContractError("pipeline stage must be an object")
    if not str(stage.get("stage") or ""):
        raise VisualGroundingContractError("pipeline stage name is required")
    stage.setdefault("status", "ok" if status == "ok" else "failed")
    stage.setdefault("latency_ms", 0)


def _response_candidates(payload: dict[str, Any], *, status: str) -> list[Any]:
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise VisualGroundingContractError("candidates must be a list")
    if status == "failed" and candidates:
        raise VisualGroundingContractError(
            "failed visual grounding response must not include candidates"
        )
    return candidates


def _validate_failure_error(error: Any) -> None:
    if not isinstance(error, dict) or not str(error.get("reason") or ""):
        raise VisualGroundingContractError("failed response requires error.reason")


def _validate_candidate_region(region: Any) -> None:
    if not isinstance(region, dict):
        raise VisualGroundingContractError("candidate.image_region must be an object")
    region_type = str(region.get("type") or "")
    if region_type not in {"bbox", "point", "verbal_region"}:
        raise VisualGroundingContractError(
            "candidate.image_region.type must be bbox, point, or verbal_region"
        )
    _validate_region_value(region_type, region.get("value"))


def _validate_region_value(region_type: str, value: Any) -> None:
    if region_type == "bbox":
        validate_number_list(value, expected=4, normalized=True, field="bbox")
    elif region_type == "point":
        validate_number_list(value, expected=2, normalized=True, field="point")
    elif not str(value or "").strip():
        raise VisualGroundingContractError("verbal_region value is required")


def _validate_candidate_confidence(confidence: Any) -> None:
    if confidence is None:
        return
    confidence_value = _numeric_value(confidence, field="candidate.confidence")
    if confidence_value < 0 or confidence_value > 1:
        raise VisualGroundingContractError("candidate.confidence must be in [0, 1]")


def _numeric_value(value: Any, *, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise VisualGroundingContractError(f"{field} values must be numeric") from exc

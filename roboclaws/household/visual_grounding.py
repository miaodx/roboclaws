from __future__ import annotations

import base64
import binascii
import json
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VISUAL_GROUNDING_REQUEST_SCHEMA = "visual_grounding_request_v1"
VISUAL_GROUNDING_RESPONSE_SCHEMA = "visual_grounding_response_v1"
VISUAL_GROUNDING_PIPELINE_SCHEMA = "visual_grounding_pipeline_v1"
SIM_VISUAL_GROUNDING_PIPELINE_ID = "sim"
DEFAULT_VISUAL_GROUNDING_BASE_URL = "http://127.0.0.1:18880"
DEFAULT_VISUAL_GROUNDING_TIMEOUT_S = 20.0
EXTERNAL_VISUAL_GROUNDING_PROVENANCE = "external_visual_grounding_service"

_ENDPOINT_PATH = "/v1/visual-grounding/candidates"


class VisualGroundingContractError(ValueError):
    """The service request or response did not match the public HTTP contract."""


@dataclass(frozen=True)
class VisualGroundingClientConfig:
    pipeline_id: str
    base_url: str = DEFAULT_VISUAL_GROUNDING_BASE_URL
    timeout_s: float = DEFAULT_VISUAL_GROUNDING_TIMEOUT_S
    api_key: str = ""
    proposer_id: str = ""
    proposer_model_id: str = ""
    refiner_id: str = ""
    refiner_model_id: str = ""

    @property
    def auth_mode(self) -> str:
        return "bearer_configured" if self.api_key else "none"

    def redacted_metadata(self) -> dict[str, Any]:
        return {
            "base_url_configured": bool(self.base_url),
            "auth_mode": self.auth_mode,
            "timeout_s": self.timeout_s,
        }


class VisualGroundingClient:
    """Small protocol-style base for swappable visual-grounding producers."""

    pipeline_id: str

    def request_candidates(self, request: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError


class HttpVisualGroundingClient(VisualGroundingClient):
    """Provider-neutral JSON-over-HTTP client for external grounding services."""

    def __init__(self, config: VisualGroundingClientConfig) -> None:
        self.config = config
        self.pipeline_id = config.pipeline_id

    def request_candidates(self, request: dict[str, Any]) -> dict[str, Any]:
        validate_visual_grounding_request(request)
        if not self.config.base_url:
            return visual_grounding_failure_response(
                pipeline_id=self.pipeline_id,
                reason="missing_base_url",
                message="VISUAL_GROUNDING_BASE_URL is required for non-sim visual grounding",
                latency_ms=0,
            )

        body = json.dumps(request).encode("utf-8")
        url = self.config.base_url.rstrip("/") + _ENDPOINT_PATH
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "roboclaws-visual-grounding/1.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"

        started = time.monotonic()
        last_error: BaseException | None = None
        for attempt in range(2):
            http_request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(http_request, timeout=self.config.timeout_s) as resp:
                    payload = json.loads(resp.read().decode("utf-8"))
                return validate_visual_grounding_response(payload)
            except urllib.error.HTTPError as exc:
                try:
                    payload = json.loads(exc.read().decode("utf-8"))
                    return validate_visual_grounding_response(payload)
                except (json.JSONDecodeError, UnicodeDecodeError) as parse_exc:
                    raise VisualGroundingContractError(
                        f"visual grounding HTTP {exc.code} response was not valid JSON"
                    ) from parse_exc
            except (socket.timeout, TimeoutError):
                latency = round((time.monotonic() - started) * 1000)
                return visual_grounding_failure_response(
                    pipeline_id=self.pipeline_id,
                    reason="timeout",
                    message="visual grounding service timed out",
                    latency_ms=latency,
                )
            except urllib.error.URLError as exc:
                last_error = exc
                reason = getattr(exc, "reason", None)
                if isinstance(reason, (socket.timeout, TimeoutError)):
                    latency = round((time.monotonic() - started) * 1000)
                    return visual_grounding_failure_response(
                        pipeline_id=self.pipeline_id,
                        reason="timeout",
                        message="visual grounding service timed out",
                        latency_ms=latency,
                    )
                if attempt == 0:
                    continue
            except json.JSONDecodeError as exc:
                raise VisualGroundingContractError(
                    "visual grounding response was not valid JSON"
                ) from exc

        latency = round((time.monotonic() - started) * 1000)
        return visual_grounding_failure_response(
            pipeline_id=self.pipeline_id,
            reason="connection_error",
            message=str(last_error or "visual grounding service connection failed"),
            latency_ms=latency,
        )


def visual_grounding_client_from_env(
    pipeline_id: str | None = None,
    *,
    base_url: str | None = None,
    timeout_s: float | None = None,
) -> VisualGroundingClient | None:
    selected = str(pipeline_id or os.environ.get("VISUAL_GROUNDING_PIPELINE_ID") or "sim")
    if selected == SIM_VISUAL_GROUNDING_PIPELINE_ID:
        return None
    configured_timeout = timeout_s
    if configured_timeout is None:
        configured_timeout = _float_env(
            "VISUAL_GROUNDING_TIMEOUT_S",
            DEFAULT_VISUAL_GROUNDING_TIMEOUT_S,
        )
    return HttpVisualGroundingClient(
        VisualGroundingClientConfig(
            pipeline_id=selected,
            base_url=str(
                base_url
                or os.environ.get("VISUAL_GROUNDING_BASE_URL")
                or DEFAULT_VISUAL_GROUNDING_BASE_URL
            ),
            timeout_s=float(configured_timeout),
            api_key=os.environ.get("VISUAL_GROUNDING_API_KEY", ""),
            proposer_id=os.environ.get("VISUAL_GROUNDING_PROPOSER_ID", ""),
            proposer_model_id=os.environ.get("VISUAL_GROUNDING_PROPOSER_MODEL_ID", ""),
            refiner_id=os.environ.get("VISUAL_GROUNDING_REFINER_ID", ""),
            refiner_model_id=os.environ.get("VISUAL_GROUNDING_REFINER_MODEL_ID", ""),
        )
    )


def visual_grounding_request(
    *,
    run_id: str,
    raw_observation: dict[str, Any],
    category_hints: list[str],
    fixture_hints: list[dict[str, Any]],
    pipeline_id: str,
    image: dict[str, Any],
    proposer: dict[str, Any] | None = None,
    refiner: dict[str, Any] | None = None,
) -> dict[str, Any]:
    request = {
        "schema": VISUAL_GROUNDING_REQUEST_SCHEMA,
        "run_id": run_id,
        "observation_id": str(raw_observation.get("observation_id") or ""),
        "waypoint_id": str(raw_observation.get("waypoint_id") or ""),
        "room_id": str(raw_observation.get("room_id") or ""),
        "capture_context": {
            "discovered_during": "waypoint_observe",
            "artifact_status": str(raw_observation.get("artifact_status") or ""),
        },
        "image": image,
        "category_hints": category_hints,
        "fixture_hints": fixture_hints,
        "pipeline_request": {
            "pipeline_id": pipeline_id,
            "proposer": proposer or {},
            "refiner": refiner or {},
        },
    }
    validate_visual_grounding_request(request)
    return request


def image_payload_for_raw_observation(
    raw_observation: dict[str, Any],
    *,
    base_dir: Path | None = None,
) -> dict[str, Any]:
    artifact_path = _raw_observation_image_path(raw_observation, base_dir=base_dir)
    if artifact_path is None or not artifact_path.is_file():
        return {
            "mime_type": "application/octet-stream",
            "bytes_base64": "",
            "width": 0,
            "height": 0,
        }
    data = artifact_path.read_bytes()
    width, height = _image_dimensions(artifact_path)
    return {
        "mime_type": _mime_type_for_path(artifact_path),
        "bytes_base64": base64.b64encode(data).decode("ascii"),
        "width": width,
        "height": height,
    }


def visual_grounding_failure_response(
    *,
    pipeline_id: str,
    reason: str,
    message: str,
    latency_ms: int | float,
) -> dict[str, Any]:
    return {
        "schema": VISUAL_GROUNDING_RESPONSE_SCHEMA,
        "status": "failed",
        "pipeline": {
            "pipeline_id": pipeline_id,
            "stages": [
                {
                    "stage": "service",
                    "producer_id": pipeline_id,
                    "model_id": "",
                    "status": reason,
                    "latency_ms": int(latency_ms),
                }
            ],
        },
        "candidates": [],
        "error": {"reason": reason, "message": message},
    }


def sim_visual_grounding_pipeline(*, candidate_count: int, latency_ms: int = 0) -> dict[str, Any]:
    return {
        "schema": VISUAL_GROUNDING_PIPELINE_SCHEMA,
        "pipeline_id": SIM_VISUAL_GROUNDING_PIPELINE_ID,
        "status": "ok",
        "stages": [
            {
                "stage": "simulated_camera_model",
                "producer_id": "camera_model_policy_baseline",
                "model_id": "simulated_camera_model",
                "version": "deterministic",
                "status": "ok",
                "latency_ms": latency_ms,
            }
        ],
        "candidate_count": candidate_count,
        "unresolved_count": 0,
        "duplicate_rate": 0.0,
    }


def pipeline_summary_from_response(
    response: dict[str, Any],
    *,
    auth_mode: str = "none",
) -> dict[str, Any]:
    validated = validate_visual_grounding_response(response)
    candidates = list(validated.get("candidates") or [])
    status = str(validated.get("status") or "failed")
    error = validated.get("error") or {}
    pipeline = validated.get("pipeline") or {}
    diagnostics = validated.get("diagnostics") or {}
    response_auth_mode = str(diagnostics.get("auth_mode") or auth_mode)
    return {
        "schema": VISUAL_GROUNDING_PIPELINE_SCHEMA,
        "pipeline_id": str(pipeline.get("pipeline_id") or ""),
        "status": status,
        "stages": list(pipeline.get("stages") or []),
        "candidate_count": len(candidates),
        "unresolved_count": 0,
        "duplicate_rate": _duplicate_rate(candidates),
        "failure_reason": str(error.get("reason") or "") if status == "failed" else "",
        "failure_message": str(error.get("message") or "") if status == "failed" else "",
        "auth_mode": response_auth_mode,
    }


def validate_visual_grounding_request(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise VisualGroundingContractError("visual grounding request must be an object")
    if payload.get("schema") != VISUAL_GROUNDING_REQUEST_SCHEMA:
        raise VisualGroundingContractError("visual grounding request schema mismatch")
    for field in ("run_id", "observation_id", "waypoint_id", "room_id"):
        if not isinstance(payload.get(field), str):
            raise VisualGroundingContractError(f"{field} must be a string")
    image = payload.get("image")
    if not isinstance(image, dict):
        raise VisualGroundingContractError("image must be an object")
    if not isinstance(image.get("bytes_base64"), str):
        raise VisualGroundingContractError("image.bytes_base64 must be a string")
    try:
        if image.get("bytes_base64"):
            base64.b64decode(image["bytes_base64"], validate=True)
    except (binascii.Error, ValueError) as exc:
        raise VisualGroundingContractError("image.bytes_base64 is not valid base64") from exc
    for field in ("width", "height"):
        if not isinstance(image.get(field), int):
            raise VisualGroundingContractError(f"image.{field} must be an integer")
    if not isinstance(payload.get("category_hints"), list):
        raise VisualGroundingContractError("category_hints must be a list")
    if not isinstance(payload.get("fixture_hints"), list):
        raise VisualGroundingContractError("fixture_hints must be a list")
    pipeline_request = payload.get("pipeline_request")
    if not isinstance(pipeline_request, dict) or not str(pipeline_request.get("pipeline_id") or ""):
        raise VisualGroundingContractError("pipeline_request.pipeline_id is required")
    return payload


def validate_visual_grounding_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise VisualGroundingContractError("visual grounding response must be an object")
    if payload.get("schema") != VISUAL_GROUNDING_RESPONSE_SCHEMA:
        raise VisualGroundingContractError("visual grounding response schema mismatch")
    status = str(payload.get("status") or "")
    if status not in {"ok", "failed"}:
        raise VisualGroundingContractError("visual grounding status must be ok or failed")
    pipeline = payload.get("pipeline")
    if not isinstance(pipeline, dict) or not str(pipeline.get("pipeline_id") or ""):
        raise VisualGroundingContractError("pipeline.pipeline_id is required")
    stages = pipeline.get("stages")
    if not isinstance(stages, list) or not stages:
        raise VisualGroundingContractError("pipeline.stages must be a non-empty list")
    for stage in stages:
        if not isinstance(stage, dict):
            raise VisualGroundingContractError("pipeline stage must be an object")
        if not str(stage.get("stage") or ""):
            raise VisualGroundingContractError("pipeline stage name is required")
        stage.setdefault("status", "ok" if status == "ok" else "failed")
        stage.setdefault("latency_ms", 0)
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        raise VisualGroundingContractError("candidates must be a list")
    if status == "failed" and candidates:
        raise VisualGroundingContractError(
            "failed visual grounding response must not include candidates"
        )
    for candidate in candidates:
        _validate_visual_grounding_candidate(candidate)
    if status == "failed":
        error = payload.get("error")
        if not isinstance(error, dict) or not str(error.get("reason") or ""):
            raise VisualGroundingContractError("failed response requires error.reason")
    return payload


def _validate_visual_grounding_candidate(candidate: Any) -> None:
    if not isinstance(candidate, dict):
        raise VisualGroundingContractError("candidate must be an object")
    if not str(candidate.get("category") or ""):
        raise VisualGroundingContractError("candidate.category is required")
    region = candidate.get("image_region")
    if not isinstance(region, dict):
        raise VisualGroundingContractError("candidate.image_region must be an object")
    region_type = str(region.get("type") or "")
    if region_type not in {"bbox", "point", "verbal_region"}:
        raise VisualGroundingContractError(
            "candidate.image_region.type must be bbox, point, or verbal_region"
        )
    value = region.get("value")
    if region_type == "bbox":
        _validate_number_list(value, expected=4, normalized=True, field="bbox")
    elif region_type == "point":
        _validate_number_list(value, expected=2, normalized=True, field="point")
    elif not str(value or "").strip():
        raise VisualGroundingContractError("verbal_region value is required")
    confidence = candidate.get("confidence")
    if confidence is not None:
        try:
            confidence_value = float(confidence)
        except (TypeError, ValueError) as exc:
            raise VisualGroundingContractError("candidate.confidence must be numeric") from exc
        if confidence_value < 0 or confidence_value > 1:
            raise VisualGroundingContractError("candidate.confidence must be in [0, 1]")


def _validate_number_list(
    value: Any,
    *,
    expected: int,
    normalized: bool,
    field: str,
) -> None:
    if not isinstance(value, list) or len(value) != expected:
        raise VisualGroundingContractError(f"{field} must be a list of {expected} numbers")
    numbers: list[float] = []
    for item in value:
        try:
            numbers.append(float(item))
        except (TypeError, ValueError) as exc:
            raise VisualGroundingContractError(f"{field} values must be numeric") from exc
    if normalized and any(number < 0.0 or number > 1.0 for number in numbers):
        raise VisualGroundingContractError(f"{field} values must be normalized to [0, 1]")


def _raw_observation_image_path(
    raw_observation: dict[str, Any],
    *,
    base_dir: Path | None,
) -> Path | None:
    image_artifacts = raw_observation.get("image_artifacts") or {}
    raw_path = image_artifacts.get("fpv") or raw_observation.get("fpv_image")
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if not path.is_absolute() and base_dir is not None:
        path = base_dir / path
    return path


def _image_dimensions(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return int(image.width), int(image.height)
    except Exception:
        return 0, 0


def _mime_type_for_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    return "application/octet-stream"


def _duplicate_rate(candidates: list[dict[str, Any]]) -> float:
    if not candidates:
        return 0.0
    seen: set[tuple[str, str]] = set()
    duplicates = 0
    for candidate in candidates:
        region = candidate.get("image_region") or {}
        key = (str(candidate.get("category") or ""), json.dumps(region, sort_keys=True))
        if key in seen:
            duplicates += 1
        seen.add(key)
    return round(duplicates / len(candidates), 6)


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default

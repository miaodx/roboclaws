from __future__ import annotations

import base64
import json
import math
import os
import socket
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import parse_json_object_text
from roboclaws.household.visual_grounding_contract import (
    VISUAL_GROUNDING_PIPELINE_SCHEMA,
    VISUAL_GROUNDING_REQUEST_SCHEMA,
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
    VisualGroundingContractError,
    validate_visual_grounding_request,
    validate_visual_grounding_response,
)

SIM_VISUAL_GROUNDING_PIPELINE_ID = "sim"
DEFAULT_VISUAL_GROUNDING_BASE_URL = "http://127.0.0.1:18880"
DEFAULT_VISUAL_GROUNDING_TIMEOUT_S = 20.0
EXTERNAL_VISUAL_GROUNDING_PROVENANCE = "external_visual_grounding_service"

_ENDPOINT_PATH = "/v1/visual-grounding/candidates"
_MAX_HTTP_ATTEMPTS = 2


@dataclass(frozen=True)
class VisualGroundingClientConfig:
    pipeline_id: str
    base_url: str = DEFAULT_VISUAL_GROUNDING_BASE_URL
    timeout_s: float = DEFAULT_VISUAL_GROUNDING_TIMEOUT_S
    api_key: str = ""
    proposer_id: str = ""
    proposer_model_id: str = ""

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

        return self._request_candidates_with_retry(
            url=self._endpoint_url(),
            body=json.dumps(request).encode("utf-8"),
            headers=self._request_headers(),
            started=time.monotonic(),
        )

    def _endpoint_url(self) -> str:
        return self.config.base_url.rstrip("/") + _ENDPOINT_PATH

    def _request_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "roboclaws-visual-grounding/1.0",
        }
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def _request_candidates_with_retry(
        self,
        *,
        url: str,
        body: bytes,
        headers: dict[str, str],
        started: float,
    ) -> dict[str, Any]:
        last_error: BaseException | None = None
        for attempt in range(_MAX_HTTP_ATTEMPTS):
            try:
                return _post_visual_grounding_json(
                    url=url,
                    body=body,
                    headers=headers,
                    timeout_s=self.config.timeout_s,
                )
            except (socket.timeout, TimeoutError):
                return self._timeout_response(started)
            except urllib.error.URLError as exc:
                last_error = exc
                if _url_error_is_timeout(exc):
                    return self._timeout_response(started)
                if attempt + 1 < _MAX_HTTP_ATTEMPTS:
                    continue

        return self._connection_error_response(last_error, started)

    def _timeout_response(self, started: float) -> dict[str, Any]:
        return visual_grounding_failure_response(
            pipeline_id=self.pipeline_id,
            reason="timeout",
            message="visual grounding service timed out",
            latency_ms=_elapsed_ms(started),
        )

    def _connection_error_response(
        self,
        error: BaseException | None,
        started: float,
    ) -> dict[str, Any]:
        return visual_grounding_failure_response(
            pipeline_id=self.pipeline_id,
            reason="connection_error",
            message=str(error or "visual grounding service connection failed"),
            latency_ms=_elapsed_ms(started),
        )


def _post_visual_grounding_json(
    *,
    url: str,
    body: bytes,
    headers: dict[str, str],
    timeout_s: float,
) -> dict[str, Any]:
    http_request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(http_request, timeout=timeout_s) as resp:
            return _validated_response_json(
                resp.read(),
                source="visual grounding HTTP response",
            )
    except urllib.error.HTTPError as exc:
        return _validated_response_json(
            exc.read(),
            source=f"visual grounding HTTP {exc.code} response",
        )


def _validated_response_json(body: bytes, *, source: str) -> dict[str, Any]:
    try:
        text = body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise VisualGroundingContractError(
            f"{source} source must contain UTF-8 JSON object"
        ) from exc
    try:
        payload = parse_json_object_text(text, label=source)
    except ValueError as exc:
        raise VisualGroundingContractError(str(exc)) from exc
    return validate_visual_grounding_response(payload)


def _url_error_is_timeout(exc: urllib.error.URLError) -> bool:
    return isinstance(getattr(exc, "reason", None), (socket.timeout, TimeoutError))


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


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
        configured_timeout = _positive_float_env(
            "VISUAL_GROUNDING_TIMEOUT_S",
            DEFAULT_VISUAL_GROUNDING_TIMEOUT_S,
        )
    else:
        configured_timeout = _positive_float(timeout_s, "visual_grounding_timeout_s")
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
        )
    )


def visual_grounding_request(
    *,
    run_id: str,
    raw_observation: dict[str, Any],
    category_hints: list[str],
    public_map_hints: dict[str, Any],
    pipeline_id: str,
    image: dict[str, Any],
    proposer: dict[str, Any] | None = None,
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
        "public_map_hints": public_map_hints,
        "pipeline_request": {
            "pipeline_id": pipeline_id,
            "proposer": proposer or {},
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


def _positive_float_env(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    return _positive_float(value, name)


def _positive_float(value: Any, setting_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{setting_name} must be a positive finite number of seconds, got {value!r}"
        ) from exc
    if not math.isfinite(parsed) or parsed <= 0:
        raise ValueError(
            f"{setting_name} must be a positive finite number of seconds, got {value!r}"
        )
    return parsed

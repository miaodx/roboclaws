"""Generic OpenAI-compatible image→text adapter for nav models that can't see directly.

Used by ``roboclaws.mcp.server`` when the configured main model is text-only
(auto-detected via model name suffix in ``_TEXT_ONLY_MODEL_SUFFIXES``). The
module has no OpenClaw-specific dependencies — any caller with an
OpenAI-compatible vision model API key can use it.
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Literal, Sequence

import numpy as np
from PIL import Image as PILImage

from roboclaws.core.provider_catalog import model_supports_images

ObserveDelivery = Literal["images", "text-bridge"]

_VALID_OBSERVE_MODES = frozenset({"auto", "images", "text-bridge"})
_MIMO_BASE_URL = "https://token-plan-cn.xiaomimimo.com/v1"
_DEFAULT_BRIDGE_MAX_TOKENS = 600
_DEFAULT_BRIDGE_FALLBACK = (
    "Vision bridge unavailable; use structured state only. Favor cautious moves "
    "and re-observe before committing to a turn."
)
_DEFAULT_SYSTEM_PROMPT = (
    "You summarize navigation images for a separate text-only robot planner. "
    "Be concise and factual. Mention immediate obstacles, open directions, "
    "notable landmarks, and what the overhead view implies for the next move."
)


@dataclass
class VisionBridgeResult:
    delivery: ObserveDelivery
    description: str
    bridge_model: str | None
    latency_s: float | None
    error: str | None = None


def _model_suffix(model_name: str | None) -> str:
    if not model_name:
        return ""
    return model_name.rsplit("/", 1)[-1].lower()


def _bridge_request_model(model_name: str | None) -> str | None:
    if not model_name:
        return None
    if model_name.startswith(("mimo_openai/", "mimo_anthropic/", "anthropic_kimi/")):
        return model_name.split("/", 1)[1]
    return model_name


def normalize_observe_mode(
    observe_mode: str | None = None,
) -> Literal["auto", "images", "text-bridge"]:
    mode = (observe_mode or os.environ.get("ROBOCLAWS_OBSERVE_MODE") or "auto").strip().lower()
    if mode not in _VALID_OBSERVE_MODES:
        raise ValueError(
            f"ROBOCLAWS_OBSERVE_MODE must be one of auto, images, text-bridge (got {mode!r})"
        )
    return mode  # type: ignore[return-value]


def resolve_observe_delivery(
    model_name: str | None,
    *,
    observe_mode: str | None = None,
) -> ObserveDelivery:
    mode = normalize_observe_mode(observe_mode)
    if mode != "auto":
        return mode
    return "images" if model_supports_images(model_name) else "text-bridge"


def resolve_bridge_model(
    *,
    bridge_model: str | None = None,
    image_model: str | None = None,
) -> str | None:
    explicit = bridge_model or os.environ.get("ROBOCLAWS_VISION_BRIDGE_MODEL")
    if explicit:
        return explicit
    return image_model or os.environ.get("IMAGE_MODEL")


def observe_runtime_config(
    *,
    model_name: str | None = None,
    image_model: str | None = None,
    observe_mode: str | None = None,
    vision_bridge_model: str | None = None,
) -> dict[str, str | None]:
    mode = normalize_observe_mode(observe_mode)
    delivery = resolve_observe_delivery(model_name, observe_mode=mode)
    bridge_model = resolve_bridge_model(
        bridge_model=vision_bridge_model,
        image_model=image_model,
    )
    return {
        "model_name": model_name,
        "image_model": image_model,
        "observe_mode": mode,
        "observe_delivery": delivery,
        "vision_bridge_model": bridge_model if delivery == "text-bridge" else None,
    }


def _default_api_key(model_name: str | None) -> str | None:
    model = (model_name or "").lower()
    if "mimo" in model:
        return os.environ.get("MIMO_TP_KEY")
    if "kimi" in model or _model_suffix(model_name) in {"k2p5", "k2.6"}:
        return os.environ.get("KIMI_API_KEY")
    if "nvidia/" in model:
        return os.environ.get("NV_API_KEY") or os.environ.get("NVIDIA_API_KEY")
    if model.startswith("gpt-") or model.startswith("openai/"):
        return os.environ.get("OPENAI_API_KEY")
    return None


def _default_base_url(model_name: str | None) -> str | None:
    return _MIMO_BASE_URL if "mimo" in (model_name or "").lower() else None


def _encode_frame_data_url(frame: np.ndarray, *, max_dim: int = 640, quality: int = 75) -> str:
    image = PILImage.fromarray(frame, mode="RGB")
    width, height = image.size
    long_edge = max(width, height)
    if long_edge > max_dim:
        scale = max_dim / float(long_edge)
        image = image.resize(
            (max(1, int(width * scale)), max(1, int(height * scale))),
            PILImage.Resampling.BILINEAR,
        )
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def _extract_response_text(response: Any) -> str:
    if not (choices := getattr(response, "choices", None) or []):
        return ""
    if (message := getattr(choices[0], "message", None)) is None:
        return ""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        chunks = [
            str(part.get("text") if isinstance(part, dict) else getattr(part, "text", "")).strip()
            for part in content
        ]
        return "\n".join(chunk for chunk in chunks if chunk)
    return str(content).strip()


def _fallback_result(
    *, bridge_model: str | None, error: str, started: float | None = None
) -> VisionBridgeResult:
    return VisionBridgeResult(
        delivery="text-bridge",
        description=_DEFAULT_BRIDGE_FALLBACK,
        bridge_model=bridge_model,
        latency_s=0.0 if started is None else round(time.monotonic() - started, 3),
        error=error,
    )


class VisionBridge:
    """Small OpenAI-compatible helper that turns navigation images into nav text."""

    def __init__(
        self,
        *,
        bridge_model: str | None = None,
        image_model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        client: Any | None = None,
        max_tokens: int = _DEFAULT_BRIDGE_MAX_TOKENS,
    ) -> None:
        self.bridge_model = resolve_bridge_model(
            bridge_model=bridge_model,
            image_model=image_model,
        )
        self._request_model = _bridge_request_model(self.bridge_model)
        self._api_key = api_key or _default_api_key(self.bridge_model)
        self._base_url = base_url or _default_base_url(self.bridge_model)
        self._client = client
        self._max_tokens = max_tokens

    def _client_handle(self) -> Any:
        if self._client is not None:
            return self._client
        if not self.bridge_model:
            raise RuntimeError("vision bridge model is not configured")
        if not self._api_key:
            raise RuntimeError(
                f"no API key configured for vision bridge model {self.bridge_model!r}"
            )
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover - exercised only when deps missing
            raise ImportError("openai package required for the vision bridge") from exc
        kwargs: dict[str, Any] = {"api_key": self._api_key}
        if self._base_url:
            kwargs["base_url"] = self._base_url
        self._client = OpenAI(**kwargs)
        return self._client

    def describe(
        self,
        *,
        images: Sequence[np.ndarray],
        image_labels: Sequence[str],
        state: dict[str, Any] | None = None,
        view_variant: str | None = None,
    ) -> VisionBridgeResult:
        started = time.monotonic()
        if not self.bridge_model:
            return _fallback_result(
                bridge_model=None,
                error="vision bridge model is not configured",
            )

        state_data = state or {}
        state_summary = {
            "view_variant": view_variant,
            "image_labels": list(image_labels),
            "position": state_data.get("position"),
            "rotation": state_data.get("rotation"),
            "camera_horizon": state_data.get("camera_horizon"),
            "human_message": state_data.get("human_message"),
        }
        content: list[dict[str, Any]] = [
            {
                "type": "text",
                "text": (
                    "Summarize these navigation images for a text-only robot planner.\n"
                    "Reply with short sections named: Immediate view, Overhead summary, "
                    "Navigation cues.\n"
                    f"State: {json.dumps(state_summary, separators=(',', ':'))}"
                ),
            },
            *(
                {"type": "image_url", "image_url": {"url": _encode_frame_data_url(frame)}}
                for frame in images
            ),
        ]

        try:
            response = self._client_handle().chat.completions.create(
                model=self._request_model,
                messages=[
                    {"role": "system", "content": _DEFAULT_SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                max_tokens=self._max_tokens,
            )
            description = _extract_response_text(response)
            if not description:
                raise RuntimeError("empty vision bridge response")
            return VisionBridgeResult(
                delivery="text-bridge",
                description=description,
                bridge_model=self.bridge_model,
                latency_s=round(time.monotonic() - started, 3),
            )
        except Exception as exc:
            return _fallback_result(
                bridge_model=self.bridge_model,
                error=str(exc),
                started=started,
            )

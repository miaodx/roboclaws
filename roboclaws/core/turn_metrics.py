from __future__ import annotations

import base64
import io
import json
import time
from typing import Any

import numpy as np
from PIL import Image


def round_seconds(value: float) -> float:
    """Return a stable precision for wallclock metrics written to replay JSON."""
    return round(value, 6)


def encode_frame_to_b64_jpeg(
    frame: np.ndarray,
    *,
    width: int = 320,
    height: int = 240,
    quality: int = 70,
) -> tuple[str, dict[str, Any]]:
    """Encode one RGB frame to base64 JPEG and return payload metrics."""
    started = time.perf_counter()
    image = Image.fromarray(frame, mode="RGB").resize((width, height), Image.Resampling.BILINEAR)
    buf = io.BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    jpeg_bytes = buf.getvalue()
    b64 = base64.b64encode(jpeg_bytes).decode("ascii")
    return b64, {
        "jpeg_bytes": len(jpeg_bytes),
        "base64_chars": len(b64),
        "width": width,
        "height": height,
        "jpeg_quality": quality,
        "encode_seconds": round_seconds(time.perf_counter() - started),
    }


def serialize_prompt_state(state: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Serialize prompt state the same way direct VLM providers do."""
    started = time.perf_counter()
    text = json.dumps(state, indent=2, default=str)
    return text, {
        "chars": len(text),
        "serialize_seconds": round_seconds(time.perf_counter() - started),
    }


def summarize_payload_metrics(
    *,
    transport: str,
    prompt_state_chars: int,
    image_metrics: list[dict[str, Any]],
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact payload summary for one turn."""
    payload = {
        "transport": transport,
        "image_count": len(image_metrics),
        "state_json_chars": prompt_state_chars,
        "images": image_metrics,
        "total_jpeg_bytes": sum(int(m.get("jpeg_bytes", 0)) for m in image_metrics),
        "total_base64_chars": sum(int(m.get("base64_chars", 0)) for m in image_metrics),
    }
    if extra:
        payload.update(extra)
    return payload


def get_provider_turn_metrics(provider: Any) -> dict[str, Any]:
    """Return provider-specific last-turn metrics when the backend exposes them."""
    getter = getattr(provider, "get_last_turn_metrics", None)
    if not callable(getter):
        return {}
    metrics = getter()
    return metrics if isinstance(metrics, dict) else {}

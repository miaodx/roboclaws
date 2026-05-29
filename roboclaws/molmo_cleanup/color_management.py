from __future__ import annotations

from typing import Any


def apply_camera_color_profile(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any] | None,
) -> tuple[Any, dict[str, Any]]:
    """Apply the display color profile carried by a camera-control request."""

    profile = dict(profile or {})
    array = np.asarray(image)
    before = image_luminance_metrics(array, np=np)
    if str(profile.get("profile_id") or "") == "display_srgb_soft_highlight_v1":
        adjusted = _soft_highlight_compress(array, np=np, profile=profile)
    else:
        adjusted = array
    adjusted = np.clip(adjusted, 0, 255).astype("uint8")
    after = image_luminance_metrics(adjusted, np=np)
    return adjusted, {
        "schema": "camera_color_management_diagnostics_v1",
        "profile": profile,
        "status": "applied" if profile else "missing_profile",
        "before": before,
        "after": after,
    }


def image_luminance_metrics(image: Any, *, np: Any) -> dict[str, float]:
    array = np.asarray(image)
    if array.ndim == 4:
        array = array[0]
    if array.ndim != 3 or array.shape[-1] < 3:
        return {
            "mean_luminance": 0.0,
            "overexposed_fraction": 0.0,
            "underexposed_fraction": 0.0,
        }
    rgb = array[..., :3].astype("float32")
    luminance = rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722
    return {
        "mean_luminance": float(luminance.mean()),
        "overexposed_fraction": float((luminance >= 245.0).mean()),
        "underexposed_fraction": float((luminance <= 10.0).mean()),
    }


def _soft_highlight_compress(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any],
) -> Any:
    array = np.asarray(image).astype("float32")
    knee = max(0.0, min(254.0, float(profile.get("highlight_knee", 225.0))))
    compression = max(0.0, min(1.0, float(profile.get("highlight_compression", 0.55))))
    gamma = max(0.1, float(profile.get("gamma", 1.0)))
    highlight = array > knee
    adjusted = array.copy()
    adjusted[highlight] = knee + (array[highlight] - knee) * compression
    if gamma != 1.0:
        adjusted = 255.0 * np.power(np.clip(adjusted / 255.0, 0.0, 1.0), 1.0 / gamma)
    return adjusted

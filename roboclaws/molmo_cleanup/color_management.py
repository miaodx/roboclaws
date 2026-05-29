from __future__ import annotations

from typing import Any


def apply_camera_color_profile(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any] | None,
    backend: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Apply the display color profile carried by a camera-control request."""

    profile = dict(profile or {})
    array = np.asarray(image)
    before = image_luminance_metrics(array, np=np)
    if str(profile.get("profile_id") or "") == "display_srgb_soft_highlight_v1":
        adjusted, calibration = _apply_backend_luminance_gain(
            array,
            np=np,
            profile=profile,
            backend=backend,
        )
        adjusted = _soft_highlight_compress(adjusted, np=np, profile=profile)
    else:
        adjusted = array
        calibration = _backend_luminance_gain_diagnostics(profile=profile, backend=backend)
    adjusted = np.clip(adjusted, 0, 255).astype("uint8")
    after = image_luminance_metrics(adjusted, np=np)
    return adjusted, {
        "schema": "camera_color_management_diagnostics_v1",
        "profile": profile,
        "status": "applied" if profile else "missing_profile",
        "backend": backend,
        "backend_luminance_gain": calibration,
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


def _apply_backend_luminance_gain(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any],
    backend: str | None,
) -> tuple[Any, dict[str, Any]]:
    diagnostics = _backend_luminance_gain_diagnostics(profile=profile, backend=backend)
    gain = diagnostics.get("gain")
    if diagnostics["status"] != "applied" or gain is None:
        return np.asarray(image).astype("float32"), diagnostics
    adjusted = np.asarray(image).astype("float32") * float(gain)
    return adjusted, diagnostics


def _backend_luminance_gain_diagnostics(
    *,
    profile: dict[str, Any],
    backend: str | None,
) -> dict[str, Any]:
    gains = profile.get("backend_luminance_gain")
    if not isinstance(gains, dict):
        return {"status": "not_configured", "backend": backend, "gain": None}
    if not backend:
        return {"status": "missing_backend", "backend": backend, "gain": None}
    if backend not in gains:
        return {"status": "backend_not_configured", "backend": backend, "gain": None}
    try:
        gain = float(gains[backend])
    except (TypeError, ValueError):
        return {"status": "invalid_gain", "backend": backend, "gain": None}
    return {
        "status": "applied",
        "backend": backend,
        "gain": gain,
        "source": profile.get("backend_luminance_gain_source"),
    }

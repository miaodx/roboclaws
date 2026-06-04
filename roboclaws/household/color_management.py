from __future__ import annotations

from typing import Any


def apply_camera_color_profile(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any] | None,
    backend: str | None = None,
    view_id: str | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Apply the display color profile carried by a camera-control request."""

    profile = dict(profile or {})
    array = np.asarray(image)
    before = image_luminance_metrics(array, np=np)
    if str(profile.get("profile_id") or "") == "display_srgb_soft_highlight_v1":
        adjusted, rgb_calibration = _apply_backend_rgb_gain(
            array,
            np=np,
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
        adjusted, calibration = _apply_backend_luminance_gain(
            adjusted,
            np=np,
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
        adjusted, tone_adjustment = _apply_backend_tone_adjustment(
            adjusted,
            np=np,
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
        adjusted = _soft_highlight_compress(adjusted, np=np, profile=profile)
    else:
        adjusted = array
        rgb_calibration = _backend_rgb_gain_diagnostics(
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
        calibration = _backend_luminance_gain_diagnostics(
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
        tone_adjustment = _backend_tone_adjustment_diagnostics(
            profile=profile,
            backend=backend,
            view_id=view_id,
        )
    adjusted = np.clip(adjusted, 0, 255).astype("uint8")
    after = image_luminance_metrics(adjusted, np=np)
    return adjusted, {
        "schema": "camera_color_management_diagnostics_v1",
        "profile": profile,
        "status": "applied" if profile else "missing_profile",
        "backend": backend,
        "view_id": view_id,
        "backend_rgb_gain": rgb_calibration,
        "backend_luminance_gain": calibration,
        "backend_tone_adjustment": tone_adjustment,
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
    view_id: str | None,
) -> tuple[Any, dict[str, Any]]:
    diagnostics = _backend_luminance_gain_diagnostics(
        profile=profile,
        backend=backend,
        view_id=view_id,
    )
    gain = diagnostics.get("gain")
    if diagnostics["status"] not in {"applied", "applied_view_gain"} or gain is None:
        return np.asarray(image).astype("float32"), diagnostics
    adjusted = np.asarray(image).astype("float32") * float(gain)
    return adjusted, diagnostics


def _apply_backend_rgb_gain(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any],
    backend: str | None,
    view_id: str | None,
) -> tuple[Any, dict[str, Any]]:
    diagnostics = _backend_rgb_gain_diagnostics(
        profile=profile,
        backend=backend,
        view_id=view_id,
    )
    gain = diagnostics.get("gain")
    if diagnostics["status"] not in {"applied", "applied_view_gain"} or gain is None:
        return np.asarray(image).astype("float32"), diagnostics
    adjusted = np.asarray(image).astype("float32") * np.asarray(gain, dtype="float32").reshape(
        1, 1, 3
    )
    return adjusted, diagnostics


def _apply_backend_tone_adjustment(
    image: Any,
    *,
    np: Any,
    profile: dict[str, Any],
    backend: str | None,
    view_id: str | None,
) -> tuple[Any, dict[str, Any]]:
    diagnostics = _backend_tone_adjustment_diagnostics(
        profile=profile,
        backend=backend,
        view_id=view_id,
    )
    if diagnostics["status"] not in {"applied", "applied_view_adjustment"}:
        return np.asarray(image).astype("float32"), diagnostics
    adjustment = diagnostics["adjustment"]
    adjusted = np.asarray(image).astype("float32")
    shadow_lift = float(adjustment.get("shadow_lift", 0.0))
    if shadow_lift:
        shadow_floor = max(1.0, float(adjustment.get("shadow_floor", 135.0)))
        luminance = (
            adjusted[..., 0] * 0.2126
            + adjusted[..., 1] * 0.7152
            + adjusted[..., 2] * 0.0722
        )
        shadow_weight = np.clip((shadow_floor - luminance) / shadow_floor, 0.0, 1.0)[..., None]
        adjusted = adjusted + shadow_lift * shadow_weight
    saturation = float(adjustment.get("saturation", 1.0))
    if saturation != 1.0:
        gray = (
            adjusted[..., 0] * 0.2126
            + adjusted[..., 1] * 0.7152
            + adjusted[..., 2] * 0.0722
        )[..., None]
        adjusted = gray + (adjusted - gray) * saturation
    gamma = max(0.1, float(adjustment.get("gamma", 1.0)))
    if gamma != 1.0:
        adjusted = 255.0 * np.power(np.clip(adjusted / 255.0, 0.0, 1.0), 1.0 / gamma)
    gain = float(adjustment.get("gain", 1.0))
    if gain != 1.0:
        adjusted = adjusted * gain
    return adjusted, diagnostics


def _backend_rgb_gain_diagnostics(
    *,
    profile: dict[str, Any],
    backend: str | None,
    view_id: str | None,
) -> dict[str, Any]:
    view_gains = profile.get("backend_view_rgb_gain")
    if isinstance(view_gains, dict) and backend and view_id:
        backend_view_gains = view_gains.get(backend)
        if isinstance(backend_view_gains, dict) and view_id in backend_view_gains:
            gain = _rgb_gain(backend_view_gains[view_id])
            if gain is None:
                return {
                    "status": "invalid_view_gain",
                    "backend": backend,
                    "view_id": view_id,
                    "gain": None,
                }
            return {
                "status": "applied_view_gain",
                "backend": backend,
                "view_id": view_id,
                "gain": gain,
                "source": profile.get("backend_view_rgb_gain_source")
                or profile.get("backend_rgb_gain_source"),
            }
    gains = profile.get("backend_rgb_gain")
    if not isinstance(gains, dict):
        return {"status": "not_configured", "backend": backend, "view_id": view_id, "gain": None}
    if not backend:
        return {"status": "missing_backend", "backend": backend, "view_id": view_id, "gain": None}
    if backend not in gains:
        return {
            "status": "backend_not_configured",
            "backend": backend,
            "view_id": view_id,
            "gain": None,
        }
    gain = _rgb_gain(gains[backend])
    if gain is None:
        return {"status": "invalid_gain", "backend": backend, "view_id": view_id, "gain": None}
    return {
        "status": "applied",
        "backend": backend,
        "view_id": view_id,
        "gain": gain,
        "source": profile.get("backend_rgb_gain_source"),
    }


def _backend_tone_adjustment_diagnostics(
    *,
    profile: dict[str, Any],
    backend: str | None,
    view_id: str | None,
) -> dict[str, Any]:
    view_adjustments = profile.get("backend_view_tone_adjustment")
    if isinstance(view_adjustments, dict) and backend and view_id:
        backend_view_adjustments = view_adjustments.get(backend)
        if isinstance(backend_view_adjustments, dict) and view_id in backend_view_adjustments:
            adjustment = _tone_adjustment(backend_view_adjustments[view_id])
            if adjustment is None:
                return {
                    "status": "invalid_view_adjustment",
                    "backend": backend,
                    "view_id": view_id,
                    "adjustment": None,
                }
            return {
                "status": "applied_view_adjustment",
                "backend": backend,
                "view_id": view_id,
                "adjustment": adjustment,
                "source": profile.get("backend_view_tone_adjustment_source")
                or profile.get("backend_tone_adjustment_source"),
            }
    adjustments = profile.get("backend_tone_adjustment")
    if not isinstance(adjustments, dict):
        return {
            "status": "not_configured",
            "backend": backend,
            "view_id": view_id,
            "adjustment": None,
        }
    if not backend:
        return {
            "status": "missing_backend",
            "backend": backend,
            "view_id": view_id,
            "adjustment": None,
        }
    if backend not in adjustments:
        return {
            "status": "backend_not_configured",
            "backend": backend,
            "view_id": view_id,
            "adjustment": None,
        }
    adjustment = _tone_adjustment(adjustments[backend])
    if adjustment is None:
        return {
            "status": "invalid_adjustment",
            "backend": backend,
            "view_id": view_id,
            "adjustment": None,
        }
    return {
        "status": "applied",
        "backend": backend,
        "view_id": view_id,
        "adjustment": adjustment,
        "source": profile.get("backend_tone_adjustment_source"),
    }


def _rgb_gain(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _tone_adjustment(value: Any) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    parsed: dict[str, float] = {}
    for key in ("shadow_lift", "shadow_floor", "gamma", "saturation", "gain"):
        if key not in value:
            continue
        try:
            parsed[key] = float(value[key])
        except (TypeError, ValueError):
            return None
    if not parsed:
        return None
    parsed.setdefault("shadow_lift", 0.0)
    parsed.setdefault("shadow_floor", 135.0)
    parsed.setdefault("gamma", 1.0)
    parsed.setdefault("saturation", 1.0)
    parsed.setdefault("gain", 1.0)
    return parsed


def _backend_luminance_gain_diagnostics(
    *,
    profile: dict[str, Any],
    backend: str | None,
    view_id: str | None,
) -> dict[str, Any]:
    view_gains = profile.get("backend_view_luminance_gain")
    if isinstance(view_gains, dict) and backend and view_id:
        backend_view_gains = view_gains.get(backend)
        if isinstance(backend_view_gains, dict) and view_id in backend_view_gains:
            try:
                gain = float(backend_view_gains[view_id])
            except (TypeError, ValueError):
                return {
                    "status": "invalid_view_gain",
                    "backend": backend,
                    "view_id": view_id,
                    "gain": None,
                }
            return {
                "status": "applied_view_gain",
                "backend": backend,
                "view_id": view_id,
                "gain": gain,
                "source": profile.get("backend_view_luminance_gain_source")
                or profile.get("backend_luminance_gain_source"),
            }
    gains = profile.get("backend_luminance_gain")
    if not isinstance(gains, dict):
        return {"status": "not_configured", "backend": backend, "view_id": view_id, "gain": None}
    if not backend:
        return {"status": "missing_backend", "backend": backend, "view_id": view_id, "gain": None}
    if backend not in gains:
        return {
            "status": "backend_not_configured",
            "backend": backend,
            "view_id": view_id,
            "gain": None,
        }
    try:
        gain = float(gains[backend])
    except (TypeError, ValueError):
        return {"status": "invalid_gain", "backend": backend, "view_id": view_id, "gain": None}
    return {
        "status": "applied",
        "backend": backend,
        "view_id": view_id,
        "gain": gain,
        "source": profile.get("backend_luminance_gain_source"),
    }

from __future__ import annotations

import argparse
from typing import Any


def parse_rgb_gain(value: str) -> tuple[float, float, float]:
    parts = [part.strip() for part in str(value).split(",")]
    if len(parts) != 3:
        raise argparse.ArgumentTypeError("RGB gain must be three comma-separated floats")
    try:
        red, green, blue = (float(part) for part in parts)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("RGB gain must contain only floats") from exc
    gain = (red, green, blue)
    if any(item <= 0.0 for item in gain):
        raise argparse.ArgumentTypeError("RGB gain values must be positive")
    return gain


def capture_quality_probe_config(args: argparse.Namespace) -> dict[str, Any]:
    render_resolution = resolution_dict(args.render_width, args.render_height)
    saved_resolution = _paired_dimension(
        args,
        "saved_report_width",
        "saved_report_height",
        default_width=args.render_width,
        default_height=args.render_height,
    )
    metric_resolution = _paired_dimension(
        args,
        "metric_width",
        "metric_height",
        default_width=saved_resolution["width"],
        default_height=saved_resolution["height"],
    )
    render_settle_frames = int(getattr(args, "render_settle_frames", 0) or 0)
    saved_mode = (
        "direct_capture"
        if saved_resolution == render_resolution
        else "downsampled_from_render_capture"
    )
    metric_mode = (
        "direct_capture"
        if metric_resolution == render_resolution
        else "downsampled_from_render_capture"
    )
    downsample_filter = str(getattr(args, "downsample_filter", "lanczos") or "lanczos")
    return {
        "schema": "robot_camera_capture_quality_probe_v1",
        "status": "capture_quality_probe_configured",
        "render_resolution_requested": render_resolution,
        "render_resolution_saved": saved_resolution,
        "metric_resolution": metric_resolution,
        "saved_image_mode": saved_mode,
        "metric_image_mode": metric_mode,
        "direct_capture_metrics": metric_mode == "direct_capture",
        "downsampled_metrics": metric_mode != "direct_capture",
        "downsample_filter": (
            downsample_filter
            if saved_mode != "direct_capture" or metric_mode != "direct_capture"
            else ""
        ),
        "render_settle_frames": render_settle_frames,
        "samples_per_pixel": _quality_setting_not_available("samples_per_pixel"),
        "anti_aliasing": _quality_setting_request(
            "anti_aliasing",
            value=getattr(args, "isaac_aa_op", None),
            setting_path="/rtx/post/aa/op",
        ),
        "tonemap_operator": _quality_setting_request(
            "tonemap_operator",
            value=getattr(args, "isaac_tonemap_op", None),
            setting_path="/rtx/post/tonemap/op",
        ),
        "exposure_bias": _quality_setting_request(
            "exposure_bias",
            value=getattr(args, "isaac_exposure_bias", None),
            setting_path="/rtx/post/tonemap/exposureBias",
        ),
        "colorcorr_gain": _quality_setting_request(
            "colorcorr_gain",
            value=getattr(args, "isaac_colorcorr_gain", None),
            setting_path="/rtx/post/colorcorr/gain",
        ),
        "denoise": _quality_setting_not_available("denoise"),
        "taa": _quality_setting_not_available("taa"),
        "texture_filtering": _quality_setting_not_available("texture_filtering"),
        "policy_classification": "capture_quality_probe",
        "default_renderer_promotion": False,
        "interpretation": (
            "This records capture-quality probe metadata only. Direct high-resolution "
            "review images and downsampled apple-to-apple metrics are kept separate, and "
            "no native renderer default is promoted by this manifest."
        ),
    }


def ensure_capture_quality_probe_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    existing = _dict(manifest.get("capture_quality_probe"))
    if existing:
        return existing
    scene = _dict(manifest.get("scene"))
    width = _required_positive_int(scene, "render_width")
    height = _required_positive_int(scene, "render_height")
    saved_width = _optional_positive_int(scene, "saved_report_width", default=width)
    saved_height = _optional_positive_int(scene, "saved_report_height", default=height)
    metric_width = _optional_positive_int(scene, "metric_width", default=saved_width)
    metric_height = _optional_positive_int(scene, "metric_height", default=saved_height)
    probe = {
        "schema": "robot_camera_capture_quality_probe_v1",
        "status": "inferred_legacy_manifest",
        "render_resolution_requested": resolution_dict(width, height),
        "render_resolution_saved": resolution_dict(saved_width, saved_height),
        "metric_resolution": resolution_dict(metric_width, metric_height),
        "saved_image_mode": "direct_capture"
        if (saved_width, saved_height) == (width, height)
        else "downsampled_from_render_capture",
        "metric_image_mode": "direct_capture"
        if (metric_width, metric_height) == (width, height)
        else "downsampled_from_render_capture",
        "direct_capture_metrics": (metric_width, metric_height) == (width, height),
        "downsampled_metrics": (metric_width, metric_height) != (width, height),
        "downsample_filter": "",
        "render_settle_frames": 0,
        "samples_per_pixel": _quality_setting_not_available("samples_per_pixel"),
        "anti_aliasing": _quality_setting_not_available("anti_aliasing"),
        "tonemap_operator": _quality_setting_not_available("tonemap_operator"),
        "exposure_bias": _quality_setting_not_available("exposure_bias"),
        "denoise": _quality_setting_not_available("denoise"),
        "taa": _quality_setting_not_available("taa"),
        "texture_filtering": _quality_setting_not_available("texture_filtering"),
        "policy_classification": "capture_quality_probe",
        "default_renderer_promotion": False,
    }
    manifest["capture_quality_probe"] = probe
    return probe


def render_settle_args(capture_quality: dict[str, Any]) -> list[str]:
    args: list[str] = []
    render_settle_frames = max(0, int(capture_quality.get("render_settle_frames") or 0))
    anti_aliasing = _dict(capture_quality.get("anti_aliasing"))
    if anti_aliasing.get("status") == "requested" and anti_aliasing.get("value") is not None:
        args.extend(["--isaac-aa-op", str(int(anti_aliasing["value"]))])
    tonemap_operator = _dict(capture_quality.get("tonemap_operator"))
    if tonemap_operator.get("status") == "requested" and tonemap_operator.get("value") is not None:
        args.extend(["--isaac-tonemap-op", str(int(tonemap_operator["value"]))])
    exposure_bias = _dict(capture_quality.get("exposure_bias"))
    if exposure_bias.get("status") == "requested" and exposure_bias.get("value") is not None:
        args.extend(["--isaac-exposure-bias", str(float(exposure_bias["value"]))])
    colorcorr_gain = _dict(capture_quality.get("colorcorr_gain"))
    if colorcorr_gain.get("status") == "requested" and colorcorr_gain.get("value") is not None:
        values = colorcorr_gain["value"]
        if isinstance(values, (list, tuple)) and len(values) == 3:
            args.extend(
                [
                    "--isaac-colorcorr-gain",
                    ",".join(f"{float(value):.6g}" for value in values),
                ]
            )
    if render_settle_frames <= 0:
        return args
    args.extend(["--render-settle-frames", str(render_settle_frames)])
    return args


def resolution_dict(width: Any, height: Any) -> dict[str, int]:
    width_int = _positive_int(width, field_name="width")
    height_int = _positive_int(height, field_name="height")
    return {"width": width_int, "height": height_int}


def _required_positive_int(data: dict[str, Any], field_name: str) -> int:
    if field_name not in data:
        raise ValueError(f"legacy comparison manifest scene.{field_name} is required")
    return _positive_int(data[field_name], field_name=f"scene.{field_name}")


def _optional_positive_int(data: dict[str, Any], field_name: str, *, default: int) -> int:
    value = data.get(field_name)
    if value is None or value == "":
        return default
    return _positive_int(value, field_name=f"scene.{field_name}")


def _positive_int(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    if isinstance(value, int):
        parsed = value
    elif isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
        parsed = int(value)
    elif isinstance(value, str):
        try:
            parsed = int(value.strip())
        except ValueError:
            raise ValueError(f"{field_name} must be a positive integer; got {value!r}") from None
    else:
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    if parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer; got {value!r}")
    return parsed


def _paired_dimension(
    args: argparse.Namespace,
    width_attr: str,
    height_attr: str,
    *,
    default_width: int,
    default_height: int,
) -> dict[str, int]:
    width = getattr(args, width_attr, None)
    height = getattr(args, height_attr, None)
    if (width is None) != (height is None):
        raise ValueError(
            f"--{width_attr.replace('_', '-')} and --{height_attr.replace('_', '-')} "
            "must be set together"
        )
    if width is None:
        width = default_width
        height = default_height
    return resolution_dict(width, height)


def _quality_setting_not_available(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "status": "not_available",
        "value": None,
        "setting_path": "",
        "default_render_settings_changed": False,
    }


def _quality_setting_request(
    name: str,
    *,
    value: Any,
    setting_path: str,
) -> dict[str, Any]:
    if value is None:
        return _quality_setting_not_available(name)
    return {
        "name": name,
        "status": "requested",
        "value": value,
        "setting_path": setting_path,
        "requested_value": value,
        "default_render_settings_changed": True,
    }


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}

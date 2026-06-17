from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageFilter, ImageStat

from roboclaws.household.artifact_paths import output_relpath
from roboclaws.household.scene_camera_image_metrics import pixel_visual_metrics

ROBOT_VIEW_KEYS = ("fpv", "chase")


def prepare_saved_report_images(
    mujoco_views: dict[str, Any],
    isaac_views: dict[str, Any],
    *,
    capture_quality: dict[str, Any],
) -> None:
    for result in (mujoco_views, isaac_views):
        raw_views = {
            key: str(path)
            for key, path in _dict(result.get("views")).items()
            if key in ROBOT_VIEW_KEYS and path
        }
        result["raw_render_views"] = dict(raw_views)
        if capture_quality.get("saved_image_mode") == "direct_capture":
            result["saved_report_views"] = dict(raw_views)
            continue
        saved: dict[str, str] = {}
        for view_key, raw_path in raw_views.items():
            saved_path = derived_image_path(
                Path(raw_path),
                suffix=f"saved_{resolution_suffix(capture_quality['render_resolution_saved'])}",
            )
            resize_image(
                Path(raw_path),
                saved_path,
                resolution=_dict(capture_quality.get("render_resolution_saved")),
                filter_name=str(capture_quality.get("downsample_filter") or "lanczos"),
            )
            saved[view_key] = str(saved_path)
        result["views"] = {**_dict(result.get("views")), **saved}
        result["saved_report_views"] = saved


def location_image_artifacts(
    *,
    mujoco_views: dict[str, Any],
    isaac_views: dict[str, Any],
    output_dir: Path,
    capture_quality: dict[str, Any],
) -> dict[str, Any]:
    comparisons: dict[str, Any] = {}
    metric_artifacts: dict[str, Any] = {}
    for view_key in ROBOT_VIEW_KEYS:
        mujoco_path = Path(
            str(
                _dict(mujoco_views.get("raw_render_views")).get(view_key)
                or mujoco_views["views"][view_key]
            )
        )
        isaac_path = Path(
            str(
                _dict(isaac_views.get("raw_render_views")).get(view_key)
                or isaac_views["views"][view_key]
            )
        )
        metric_paths = metric_image_paths(
            mujoco_path,
            isaac_path,
            view_key=view_key,
            capture_quality=capture_quality,
        )
        metric_artifacts[view_key] = {
            "mujoco": output_relpath(metric_paths["mujoco"], output_dir),
            "isaac": output_relpath(metric_paths["isaac"], output_dir),
            "mode": capture_quality.get("metric_image_mode"),
            "resolution": capture_quality.get("metric_resolution"),
            "downsample_filter": capture_quality.get("downsample_filter"),
        }
        comparisons[view_key] = image_diff(
            metric_paths["mujoco"],
            metric_paths["isaac"],
            capture_quality=capture_quality,
        )
    return {
        "views": {
            "mujoco": {
                key: output_relpath(Path(str(path)), output_dir)
                for key, path in dict(mujoco_views.get("views") or {}).items()
                if key in {"fpv", "chase", "map", "verify"}
            },
            "isaac": {
                key: output_relpath(Path(str(path)), output_dir)
                for key, path in dict(isaac_views.get("views") or {}).items()
                if key in {"fpv", "chase", "map", "verify"}
            },
        },
        "raw_render_views": {
            "mujoco": {
                key: output_relpath(Path(str(path)), output_dir)
                for key, path in _dict(mujoco_views.get("raw_render_views")).items()
                if key in ROBOT_VIEW_KEYS
            },
            "isaac": {
                key: output_relpath(Path(str(path)), output_dir)
                for key, path in _dict(isaac_views.get("raw_render_views")).items()
                if key in ROBOT_VIEW_KEYS
            },
        },
        "metric_views": metric_artifacts,
        "image_diffs": comparisons,
    }


def metric_image_paths(
    mujoco_path: Path,
    isaac_path: Path,
    *,
    view_key: str,
    capture_quality: dict[str, Any],
) -> dict[str, Path]:
    if capture_quality.get("metric_image_mode") == "direct_capture":
        return {"mujoco": mujoco_path, "isaac": isaac_path}
    suffix = f"metric_{view_key}_{resolution_suffix(capture_quality['metric_resolution'])}"
    metric_mujoco = derived_image_path(mujoco_path, suffix=suffix)
    metric_isaac = derived_image_path(isaac_path, suffix=suffix)
    resize_image(
        mujoco_path,
        metric_mujoco,
        resolution=_dict(capture_quality.get("metric_resolution")),
        filter_name=str(capture_quality.get("downsample_filter") or "lanczos"),
    )
    resize_image(
        isaac_path,
        metric_isaac,
        resolution=_dict(capture_quality.get("metric_resolution")),
        filter_name=str(capture_quality.get("downsample_filter") or "lanczos"),
    )
    return {"mujoco": metric_mujoco, "isaac": metric_isaac}


def derived_image_path(path: Path, *, suffix: str) -> Path:
    return path.with_name(f"{path.stem}.{suffix}{path.suffix}")


def resolution_suffix(resolution: dict[str, Any]) -> str:
    return f"{int(resolution['width'])}x{int(resolution['height'])}"


def resize_image(
    source_path: Path,
    target_path: Path,
    *,
    resolution: dict[str, Any],
    filter_name: str,
) -> None:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    size = (int(resolution["width"]), int(resolution["height"]))
    with Image.open(source_path) as source:
        source.convert("RGB").resize(size, _pil_resample_filter(filter_name)).save(target_path)


def image_diff(
    left_path: Path,
    right_path: Path,
    *,
    capture_quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    with Image.open(left_path) as left_raw, Image.open(right_path) as right_raw:
        left = left_raw.convert("RGB")
        right = right_raw.convert("RGB")
        if right.size != left.size:
            right = right.resize(left.size)
        diff = ImageChops.difference(left, right)
        stat = ImageStat.Stat(diff)
        mean_abs = sum(stat.mean) / len(stat.mean)
        rms = sum(value * value for value in stat.rms) ** 0.5 / len(stat.rms)
        extrema = diff.getextrema()
        pixel_count = max(left.size[0] * left.size[1], 1)
        nonzero = 0
        diff_gt_40 = 0
        diff_gt_80 = 0
        for pixel in diff.getdata():
            if pixel != (0, 0, 0):
                nonzero += 1
            mean_pixel_delta = sum(pixel) / 3.0
            if mean_pixel_delta > 40.0:
                diff_gt_40 += 1
            if mean_pixel_delta > 80.0:
                diff_gt_80 += 1
        residual = render_residual_diagnostics(left, right)
        return {
            "left": str(left_path),
            "right": str(right_path),
            "size": list(left.size),
            "mean_abs_rgb": round(float(mean_abs), 4),
            "rms_rgb": round(float(rms), 4),
            "max_channel_diff": max(max(channel) for channel in extrema),
            "nonzero_fraction": round(nonzero / pixel_count, 6),
            "diff_gt_40_fraction": round(diff_gt_40 / pixel_count, 6),
            "diff_gt_80_fraction": round(diff_gt_80 / pixel_count, 6),
            "residual": residual,
            "capture_quality_probe": _dict(capture_quality),
        }


def render_residual_diagnostics(left: Image.Image, right: Image.Image) -> dict[str, Any]:
    left = left.convert("RGB")
    right = right.convert("RGB")
    if right.size != left.size:
        right = right.resize(left.size)
    left_metrics = image_visual_metrics(left)
    right_metrics = image_visual_metrics(right)
    luma_gain, luma_gain_diff = _luminance_gain_oracle(left, right)
    rgb_gain, rgb_gain_diff = _rgb_gain_oracle(left, right)
    left_edge = _edge_image(left)
    right_edge = _edge_image(right)
    edge_abs_diff = _mean_abs_grayscale_diff(left_edge, right_edge)
    residual_class = _residual_class(
        mean_abs_rgb=_mean_abs_rgb(left, right),
        left_metrics=left_metrics,
        right_metrics=right_metrics,
        edge_abs_diff=edge_abs_diff,
        rgb_gain_diff=rgb_gain_diff,
    )
    return {
        "schema": "robot_camera_render_residual_diagnostics_v1",
        "left_metrics": left_metrics,
        "right_metrics": right_metrics,
        "luminance_gain_oracle": {
            "gain": round(luma_gain, 6),
            "mean_abs_rgb_after_gain": round(luma_gain_diff, 4),
            "interpretation": (
                "Per-view oracle only; this is diagnostic evidence, not a runtime "
                "color-calibration contract."
            ),
        },
        "rgb_gain_oracle": {
            "gain": [round(value, 6) for value in rgb_gain],
            "mean_abs_rgb_after_gain": round(rgb_gain_diff, 4),
            "interpretation": (
                "Per-view RGB oracle only; use it to classify residuals, not as "
                "backend output post-processing."
            ),
        },
        "edge_abs_diff": round(edge_abs_diff, 4),
        "residual_class": residual_class,
        "recommended_next_action": _residual_next_action(residual_class),
    }


def image_visual_metrics(image: Image.Image) -> dict[str, float]:
    rgb = image.convert("RGB")
    pixels = list(rgb.getdata())
    if not pixels:
        return {
            "mean_luminance": 0.0,
            "overexposed_fraction": 0.0,
            "underexposed_fraction": 0.0,
            "edge_mean": 0.0,
        }
    base_metrics = pixel_visual_metrics(pixels)
    edge = _edge_image(rgb)
    return {
        "mean_luminance": round(float(base_metrics.get("mean_luminance") or 0.0), 4),
        "overexposed_fraction": round(
            float(base_metrics.get("overexposed_fraction") or 0.0),
            6,
        ),
        "underexposed_fraction": round(
            float(base_metrics.get("underexposed_fraction") or 0.0),
            6,
        ),
        "edge_mean": round(float(ImageStat.Stat(edge).mean[0]), 4),
    }


def residual_triage(locations: list[dict[str, Any]]) -> dict[str, Any]:
    per_view: dict[str, dict[str, Any]] = {}
    for view_key in ROBOT_VIEW_KEYS:
        diffs = [
            _dict_path(item, ("image_diffs", view_key, "residual"))
            for item in locations
            if item.get("status") == "success"
        ]
        diffs = [item for item in diffs if item]
        classes = [str(item.get("residual_class") or "") for item in diffs]
        per_view[view_key] = {
            "view_count": len(diffs),
            "residual_classes": {name: classes.count(name) for name in sorted(set(classes))},
            "mean_abs_rgb_avg": _avg(
                _get_float(item, ("image_diffs", view_key, "mean_abs_rgb")) for item in locations
            ),
            "rgb_gain_oracle_mean_abs_rgb_avg": _avg(
                _get_float(item, ("rgb_gain_oracle", "mean_abs_rgb_after_gain")) for item in diffs
            ),
            "edge_abs_diff_avg": _avg(_get_float(item, ("edge_abs_diff",)) for item in diffs),
        }
    fpv = per_view.get("fpv") or {}
    fpv_classes = dict(fpv.get("residual_classes") or {})
    if fpv_classes.get("geometry_or_texture_edge_residual"):
        status = "render_domain_geometry_or_texture_residual"
        next_action = (
            "Camera pose/color are improved; next compare visible geometry/material/texture "
            "contracts and static head articulation for high-residual FPV views."
        )
    elif fpv_classes.get("view_dependent_color_residual"):
        status = "view_dependent_color_residual"
        next_action = (
            "A single global color profile is insufficient; inspect per-room lighting and "
            "material albedo before tuning camera geometry."
        )
    elif float(fpv.get("mean_abs_rgb_avg") or 0.0) <= 40.0:
        status = "fpv_residual_low"
        next_action = "FPV residual is low for this probe; broaden scene/seed coverage."
    else:
        status = "render_domain_residual_pending_triage"
        next_action = "Inspect high-residual views before changing camera pose."
    return {
        "schema": "robot_camera_render_residual_triage_v1",
        "status": status,
        "views": per_view,
        "recommended_next_action": next_action,
    }


def _pil_resample_filter(filter_name: str) -> int:
    filters = {
        "nearest": Image.Resampling.NEAREST,
        "bilinear": Image.Resampling.BILINEAR,
        "bicubic": Image.Resampling.BICUBIC,
        "lanczos": Image.Resampling.LANCZOS,
    }
    return int(filters.get(filter_name, Image.Resampling.LANCZOS))


def _edge_image(image: Image.Image) -> Image.Image:
    edge = image.convert("L").filter(ImageFilter.FIND_EDGES)
    width, height = edge.size
    if width > 2 and height > 2:
        return edge.crop((1, 1, width - 1, height - 1))
    return edge


def _luminance(pixel: tuple[int, int, int]) -> float:
    return float(pixel[0]) * 0.2126 + float(pixel[1]) * 0.7152 + float(pixel[2]) * 0.0722


def _luminance_gain_oracle(left: Image.Image, right: Image.Image) -> tuple[float, float]:
    left_pixels = list(left.convert("RGB").getdata())
    right_pixels = list(right.convert("RGB").getdata())
    numerator = 0.0
    denominator = 0.0
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        left_luma = _luminance(left_pixel)
        right_luma = _luminance(right_pixel)
        numerator += left_luma * right_luma
        denominator += right_luma * right_luma
    gain = numerator / denominator if denominator > 0.0 else 1.0
    return gain, _mean_abs_rgb_after_gain(left_pixels, right_pixels, (gain, gain, gain))


def _rgb_gain_oracle(
    left: Image.Image, right: Image.Image
) -> tuple[tuple[float, float, float], float]:
    left_pixels = list(left.convert("RGB").getdata())
    right_pixels = list(right.convert("RGB").getdata())
    gains = []
    for channel in range(3):
        numerator = 0.0
        denominator = 0.0
        for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
            numerator += float(left_pixel[channel]) * float(right_pixel[channel])
            denominator += float(right_pixel[channel]) * float(right_pixel[channel])
        gains.append(numerator / denominator if denominator > 0.0 else 1.0)
    gain_tuple = (float(gains[0]), float(gains[1]), float(gains[2]))
    return gain_tuple, _mean_abs_rgb_after_gain(left_pixels, right_pixels, gain_tuple)


def _mean_abs_rgb_after_gain(
    left_pixels: list[tuple[int, int, int]],
    right_pixels: list[tuple[int, int, int]],
    gain: tuple[float, float, float],
) -> float:
    if not left_pixels:
        return 0.0
    total = 0.0
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        for channel in range(3):
            adjusted = max(0.0, min(255.0, float(right_pixel[channel]) * gain[channel]))
            total += abs(float(left_pixel[channel]) - adjusted)
    return total / (len(left_pixels) * 3.0)


def _mean_abs_rgb(left: Image.Image, right: Image.Image) -> float:
    diff = ImageChops.difference(left.convert("RGB"), right.convert("RGB"))
    stat = ImageStat.Stat(diff)
    return float(sum(stat.mean) / len(stat.mean))


def _mean_abs_grayscale_diff(left: Image.Image, right: Image.Image) -> float:
    if right.size != left.size:
        right = right.resize(left.size)
    stat = ImageStat.Stat(ImageChops.difference(left.convert("L"), right.convert("L")))
    return float(stat.mean[0])


def _residual_class(
    *,
    mean_abs_rgb: float,
    left_metrics: dict[str, float],
    right_metrics: dict[str, float],
    edge_abs_diff: float,
    rgb_gain_diff: float,
) -> str:
    if mean_abs_rgb <= 35.0:
        return "low_residual"
    left_edge = float(left_metrics.get("edge_mean") or 0.0)
    right_edge = float(right_metrics.get("edge_mean") or 0.0)
    if left_edge > 4.0 and right_edge < left_edge * 0.45:
        return "geometry_or_texture_edge_residual"
    if edge_abs_diff > 8.0:
        return "geometry_or_texture_edge_residual"
    if rgb_gain_diff <= mean_abs_rgb * 0.7:
        return "view_dependent_color_residual"
    if (
        abs(
            float(right_metrics.get("mean_luminance") or 0.0)
            - float(left_metrics.get("mean_luminance") or 0.0)
        )
        > 35.0
    ):
        return "luminance_residual"
    return "render_domain_residual"


def _residual_next_action(residual_class: str) -> str:
    if residual_class == "low_residual":
        return "Residual is low enough for this probe; inspect other views before changing code."
    if residual_class == "view_dependent_color_residual":
        return (
            "Per-view color gain helps, but a global post-process would overfit; inspect "
            "room/object lighting, material albedo, and tone response."
        )
    if residual_class == "geometry_or_texture_edge_residual":
        return (
            "Edge/detail residual is high; compare visible USD/MuJoCo geometry, material "
            "bindings, texture availability, and static robot/head articulation."
        )
    if residual_class == "luminance_residual":
        return "Try a renderer/light/color-profile calibration probe before changing camera pose."
    return "Inspect render-domain differences before changing camera geometry."


def _dict_path(item: dict[str, Any], path: tuple[str, ...]) -> dict[str, Any]:
    value: Any = item
    for key in path:
        value = _dict(value).get(key)
    return _dict(value)


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _get_float(item: dict[str, Any], path: tuple[str, ...]) -> float | None:
    value: Any = item
    for key in path:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _avg(values: Any) -> float | None:
    numbers = [float(value) for value in values if value is not None]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 4)

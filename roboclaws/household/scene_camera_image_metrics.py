from __future__ import annotations

import math
from pathlib import Path
from typing import Any

from PIL import Image


def image_visual_metrics(path: Path) -> dict[str, Any]:
    with Image.open(path).convert("RGB") as image:
        pixels = list(image.getdata())
    return pixel_visual_metrics(pixels)


def image_region_visual_metrics(path: Path, *, region_id: str) -> dict[str, Any]:
    with Image.open(path).convert("RGB") as image:
        width, height = image.size
        if region_id == "upper_center_wall_proxy":
            left = int(width * 0.30)
            right = max(left + 1, int(width * 0.70))
            top = int(height * 0.08)
            bottom = max(top + 1, int(height * 0.42))
        else:
            left, top, right, bottom = 0, 0, width, height
        pixels = list(image.crop((left, top, right, bottom)).getdata())
    metrics = pixel_visual_metrics(pixels)
    metrics["region_id"] = region_id
    metrics["region_box_fraction"] = {
        "left": left / max(width, 1),
        "top": top / max(height, 1),
        "right": right / max(width, 1),
        "bottom": bottom / max(height, 1),
    }
    return metrics


def pixel_visual_metrics(pixels: list[tuple[int, int, int]]) -> dict[str, Any]:
    count = max(len(pixels), 1)
    sums = [0.0, 0.0, 0.0]
    luminance_sum = 0.0
    luminance_sq_sum = 0.0
    overexposed_count = 0
    underexposed_count = 0
    for red, green, blue in pixels:
        red_f = float(red)
        green_f = float(green)
        blue_f = float(blue)
        sums[0] += red_f
        sums[1] += green_f
        sums[2] += blue_f
        luminance = 0.2126 * red_f + 0.7152 * green_f + 0.0722 * blue_f
        luminance_sum += luminance
        luminance_sq_sum += luminance * luminance
        if red >= 250 and green >= 250 and blue >= 250:
            overexposed_count += 1
        if red <= 5 and green <= 5 and blue <= 5:
            underexposed_count += 1
    mean_luminance = luminance_sum / count
    variance = max(luminance_sq_sum / count - mean_luminance * mean_luminance, 0.0)
    return {
        "mean_rgb": [value / count for value in sums],
        "mean_luminance": mean_luminance,
        "std_luminance": math.sqrt(variance),
        "overexposed_fraction": overexposed_count / count,
        "underexposed_fraction": underexposed_count / count,
    }


def image_pair_visual_delta(left_path: Path, right_path: Path) -> dict[str, Any]:
    with Image.open(left_path).convert("RGB") as left_image:
        with Image.open(right_path).convert("RGB") as right_image:
            if left_image.size != right_image.size:
                right_image = right_image.resize(left_image.size, Image.Resampling.BILINEAR)
            left_pixels = list(left_image.getdata())
            right_pixels = list(right_image.getdata())
    count = max(len(left_pixels), 1)
    absolute_sum = 0.0
    rms_sum = 0.0
    max_delta = 0.0
    for left, right in zip(left_pixels, right_pixels, strict=True):
        channel_deltas = [abs(float(left[index]) - float(right[index])) for index in range(3)]
        pixel_delta = sum(channel_deltas) / 3.0
        absolute_sum += pixel_delta
        rms_sum += sum(delta * delta for delta in channel_deltas) / 3.0
        max_delta = max(max_delta, max(channel_deltas))
    return {
        "mean_absolute_pixel_delta": absolute_sum / count,
        "rms_pixel_delta": math.sqrt(rms_sum / count),
        "max_channel_delta": max_delta,
    }

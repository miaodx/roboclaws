#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

SCHEMA = "roboclaws_robot_camera_rgb_gain_profile_v1"
DEFAULT_BACKEND = "isaaclab_subprocess"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build a comparison-only robot-camera RGB gain profile from an apple-to-apple "
            "comparison manifest. The output is a color-profile override for probe runs, "
            "not a default rendering change."
        )
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-profile", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument("--view", default="fpv", choices=("fpv", "chase"))
    parser.add_argument("--backend", default=DEFAULT_BACKEND)
    parser.add_argument(
        "--target-id",
        action="append",
        default=[],
        help="Restrict fitting to one target id. Repeat to include multiple targets.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = make_rgb_gain_profile(
        manifest_path=args.manifest,
        output_profile_path=args.output_profile,
        summary_output=args.summary_output,
        view=args.view,
        backend=args.backend,
        target_ids=args.target_id,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] == "ready" else 2


def make_rgb_gain_profile(
    *,
    manifest_path: Path,
    output_profile_path: Path,
    summary_output: Path | None = None,
    view: str = "fpv",
    backend: str = DEFAULT_BACKEND,
    target_ids: list[str] | None = None,
) -> dict[str, Any]:
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    selected_targets = {str(item) for item in target_ids or [] if str(item)}
    numerator = [0.0, 0.0, 0.0]
    denominator = [0.0, 0.0, 0.0]
    used_pairs: list[dict[str, Any]] = []
    skipped_pairs: list[dict[str, Any]] = []
    for location in manifest.get("locations") or []:
        if not isinstance(location, dict) or location.get("status") != "success":
            continue
        target_id = str((location.get("target") or {}).get("target_id") or "")
        if selected_targets and target_id not in selected_targets:
            continue
        image_diff = (location.get("image_diffs") or {}).get(view) or {}
        left_path = _resolve_artifact_path(image_diff.get("left"), manifest_path=manifest_path)
        right_path = _resolve_artifact_path(image_diff.get("right"), manifest_path=manifest_path)
        if left_path is None or right_path is None:
            skipped_pairs.append(
                {"target_id": target_id, "reason": "missing_image_path", "view": view}
            )
            continue
        left = Image.open(left_path).convert("RGB")
        right = Image.open(right_path).convert("RGB")
        if right.size != left.size:
            right = right.resize(left.size)
        pixel_count = _accumulate_least_squares(left, right, numerator, denominator)
        used_pairs.append(
            {
                "target_id": target_id,
                "left": str(left_path),
                "right": str(right_path),
                "pixel_count": pixel_count,
                "view": view,
            }
        )
    gains = [
        numerator[index] / denominator[index] if denominator[index] > 0.0 else 1.0
        for index in range(3)
    ]
    status = "ready" if used_pairs else "no_pairs"
    profile = {
        "backend_rgb_gain": {backend: [round(value, 6) for value in gains]},
        "backend_rgb_gain_source": (
            f"{manifest_path} global least-squares {view.upper()} RGB gain"
        ),
    }
    if status == "ready":
        output_profile_path.parent.mkdir(parents=True, exist_ok=True)
        output_profile_path.write_text(
            json.dumps(profile, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    summary = {
        "schema": SCHEMA,
        "status": status,
        "comparison_only": True,
        "manifest_path": str(manifest_path),
        "output_profile_path": str(output_profile_path),
        "view": view,
        "backend": backend,
        "target_ids": sorted(selected_targets),
        "used_pair_count": len(used_pairs),
        "skipped_pair_count": len(skipped_pairs),
        "used_pairs": used_pairs,
        "skipped_pairs": skipped_pairs,
        "backend_rgb_gain": profile["backend_rgb_gain"],
        "backend_rgb_gain_source": profile["backend_rgb_gain_source"],
    }
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def _resolve_artifact_path(raw_path: Any, *, manifest_path: Path) -> Path | None:
    if not raw_path:
        return None
    path = Path(str(raw_path))
    if path.is_absolute():
        return path if path.is_file() else None
    if path.is_file():
        return path
    candidate = manifest_path.parent / path
    if candidate.is_file():
        return candidate
    return None


def _accumulate_least_squares(
    left: Image.Image,
    right: Image.Image,
    numerator: list[float],
    denominator: list[float],
) -> int:
    left_pixels = list(left.getdata())
    right_pixels = list(right.getdata())
    for left_pixel, right_pixel in zip(left_pixels, right_pixels, strict=True):
        for channel in range(3):
            left_value = float(left_pixel[channel])
            right_value = float(right_pixel[channel])
            numerator[channel] += left_value * right_value
            denominator[channel] += right_value * right_value
    return len(left_pixels)


if __name__ == "__main__":
    raise SystemExit(main())

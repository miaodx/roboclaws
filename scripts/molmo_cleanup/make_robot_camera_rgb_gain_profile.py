#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from PIL import Image

from roboclaws.core.json_sources import read_json_object

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
    parser.add_argument(
        "--view-gain",
        action="append",
        default=[],
        metavar="VIEW=MANIFEST",
        help=(
            "Add a view-specific RGB gain fitted from another manifest, for example "
            "fpv=path/to/fpv_manifest.json or chase=path/to/chase_manifest.json. Repeat for "
            "multiple views. The base --manifest/--view still writes backend_rgb_gain."
        ),
    )
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
        view_gain_specs=args.view_gain,
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
    view_gain_specs: list[str] | None = None,
    backend: str = DEFAULT_BACKEND,
    target_ids: list[str] | None = None,
) -> dict[str, Any]:
    selected_targets = {str(item) for item in target_ids or [] if str(item)}
    base_fit = _fit_rgb_gain(
        manifest_path=manifest_path,
        view=view,
        target_ids=selected_targets,
    )
    view_fits = [
        _view_fit_summary(
            spec,
            backend=backend,
            target_ids=selected_targets,
        )
        for spec in view_gain_specs or []
    ]
    ready_view_fits = [fit for fit in view_fits if fit["status"] == "ready"]
    status = "ready" if base_fit["status"] == "ready" else "no_pairs"
    profile = {
        "backend_rgb_gain": {backend: base_fit["backend_rgb_gain"]},
        "backend_rgb_gain_source": base_fit["backend_rgb_gain_source"],
    }
    if ready_view_fits:
        profile["backend_view_rgb_gain"] = {
            backend: {fit["view"]: fit["backend_rgb_gain"] for fit in ready_view_fits}
        }
        profile["backend_view_rgb_gain_source"] = "; ".join(
            fit["backend_rgb_gain_source"] for fit in ready_view_fits
        )
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
        "used_pair_count": len(base_fit["used_pairs"]),
        "skipped_pair_count": len(base_fit["skipped_pairs"]),
        "used_pairs": base_fit["used_pairs"],
        "skipped_pairs": base_fit["skipped_pairs"],
        "backend_rgb_gain": profile["backend_rgb_gain"],
        "backend_rgb_gain_source": profile["backend_rgb_gain_source"],
        "view_gain_specs": view_gain_specs or [],
        "view_fits": view_fits,
        "backend_view_rgb_gain": profile.get("backend_view_rgb_gain", {}),
        "backend_view_rgb_gain_source": profile.get("backend_view_rgb_gain_source"),
    }
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def _view_fit_summary(
    spec: str,
    *,
    backend: str,
    target_ids: set[str],
) -> dict[str, Any]:
    view, manifest_path = _parse_view_gain_spec(spec)
    fit = _fit_rgb_gain(
        manifest_path=manifest_path,
        view=view,
        target_ids=target_ids,
    )
    fit["backend"] = backend
    return fit


def _parse_view_gain_spec(spec: str) -> tuple[str, Path]:
    if "=" not in spec:
        raise ValueError(f"--view-gain must be VIEW=MANIFEST, got: {spec}")
    raw_view, raw_path = spec.split("=", 1)
    view = raw_view.strip()
    if view not in {"fpv", "chase"}:
        raise ValueError(f"unsupported view-gain view: {view}")
    path = Path(raw_path)
    return view, path


def _fit_rgb_gain(
    *,
    manifest_path: Path,
    view: str,
    target_ids: set[str],
) -> dict[str, Any]:
    manifest = read_json_object(manifest_path, label="robot-camera RGB gain comparison manifest")
    numerator = [0.0, 0.0, 0.0]
    denominator = [0.0, 0.0, 0.0]
    used_pairs: list[dict[str, Any]] = []
    skipped_pairs: list[dict[str, Any]] = []
    for location in manifest.get("locations") or []:
        if not isinstance(location, dict) or location.get("status") != "success":
            continue
        target_id = str((location.get("target") or {}).get("target_id") or "")
        if target_ids and target_id not in target_ids:
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
    return {
        "status": "ready" if used_pairs else "no_pairs",
        "manifest_path": str(manifest_path),
        "view": view,
        "used_pair_count": len(used_pairs),
        "skipped_pair_count": len(skipped_pairs),
        "used_pairs": used_pairs,
        "skipped_pairs": skipped_pairs,
        "backend_rgb_gain": [round(value, 6) for value in gains],
        "backend_rgb_gain_source": (
            f"{manifest_path} global least-squares {view.upper()} RGB gain"
        ),
    }


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

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "roboclaws_molmospaces_material_response_probe_usd_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a comparison-only MolmoSpaces USD variant for Isaac material-response "
            "probes. The source scene is copied; default cleanup rendering is not changed."
        )
    )
    parser.add_argument("--scene-usd-path", type=Path, required=True)
    parser.add_argument("--output-usd-path", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument(
        "--source-color-space",
        choices=("auto", "raw", "sRGB"),
        help="Rewrite USD texture token inputs:sourceColorSpace values for a probe.",
    )
    parser.add_argument(
        "--roughness",
        type=float,
        help="Rewrite PreviewSurface float inputs:roughness values for a probe.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = make_material_response_probe_usd(
        scene_usd_path=args.scene_usd_path,
        output_usd_path=args.output_usd_path,
        summary_output=args.summary_output,
        source_color_space=args.source_color_space,
        roughness=args.roughness,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"ready", "no_changes"} else 2


def make_material_response_probe_usd(
    *,
    scene_usd_path: Path,
    output_usd_path: Path,
    summary_output: Path | None = None,
    source_color_space: str | None = None,
    roughness: float | None = None,
) -> dict[str, Any]:
    if not scene_usd_path.is_file():
        raise FileNotFoundError(scene_usd_path)
    if scene_usd_path.resolve() == output_usd_path.resolve():
        raise ValueError("output_usd_path must not overwrite scene_usd_path")
    text = scene_usd_path.read_text(encoding="utf-8", errors="ignore")
    updated = text
    source_color_space_rewrite_count = 0
    roughness_rewrite_count = 0
    if source_color_space is not None:
        updated, source_color_space_rewrite_count = re.subn(
            r'token inputs:sourceColorSpace = "[^"]+"',
            f'token inputs:sourceColorSpace = "{source_color_space}"',
            updated,
        )
    if roughness is not None:
        updated, roughness_rewrite_count = re.subn(
            r"float inputs:roughness = [^\s]+",
            f"float inputs:roughness = {_format_float(roughness)}",
            updated,
        )
    output_usd_path.parent.mkdir(parents=True, exist_ok=True)
    output_usd_path.write_text(updated, encoding="utf-8")
    metadata_copied = _copy_metadata_next_to_output(
        scene_usd_path=scene_usd_path,
        output_usd_path=output_usd_path,
    )
    total_rewrite_count = source_color_space_rewrite_count + roughness_rewrite_count
    status = "ready" if total_rewrite_count else "no_changes"
    summary = {
        "schema": SCHEMA,
        "status": status,
        "source_scene_usd_path": str(scene_usd_path),
        "output_usd_path": str(output_usd_path),
        "comparison_only": True,
        "requested_overrides": {
            "source_color_space": source_color_space,
            "roughness": roughness,
        },
        "source_color_space_rewrite_count": source_color_space_rewrite_count,
        "roughness_rewrite_count": roughness_rewrite_count,
        "total_rewrite_count": total_rewrite_count,
        "scene_metadata_copied": metadata_copied,
    }
    if summary_output is not None:
        summary_output.parent.mkdir(parents=True, exist_ok=True)
        summary_output.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def _copy_metadata_next_to_output(*, scene_usd_path: Path, output_usd_path: Path) -> bool:
    metadata_path = scene_usd_path.parent / "scene_metadata.json"
    if not metadata_path.is_file():
        return False
    output_metadata_path = output_usd_path.parent / "scene_metadata.json"
    output_metadata_path.write_text(metadata_path.read_text(encoding="utf-8"), encoding="utf-8")
    return True


def _format_float(value: float) -> str:
    return f"{value:.6g}"


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

SCHEMA = "roboclaws_molmospaces_light_shadow_probe_usd_v1"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Create a comparison-only MolmoSpaces USD variant for Isaac light/shadow "
            "probes. The source scene is copied; default cleanup rendering is not changed."
        )
    )
    parser.add_argument("--scene-usd-path", type=Path, required=True)
    parser.add_argument("--output-usd-path", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path)
    parser.add_argument(
        "--remove-dome-lights",
        action="store_true",
        help="Remove DomeLight prim blocks from the probe USD.",
    )
    parser.add_argument(
        "--enable-shadows",
        action="store_true",
        help="Rewrite primvars:doNotCastShadows=true/1 to false.",
    )
    parser.add_argument(
        "--distant-light-intensity",
        type=float,
        help="Rewrite all DistantLight inputs:intensity values.",
    )
    parser.add_argument(
        "--distant-light-rotate-x",
        type=float,
        help="Rewrite or add xformOp:rotateX on all DistantLight prim blocks.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = make_light_shadow_probe_usd(
        scene_usd_path=args.scene_usd_path,
        output_usd_path=args.output_usd_path,
        summary_output=args.summary_output,
        remove_dome_lights=args.remove_dome_lights,
        enable_shadows=args.enable_shadows,
        distant_light_intensity=args.distant_light_intensity,
        distant_light_rotate_x=args.distant_light_rotate_x,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"ready", "no_changes"} else 2


def make_light_shadow_probe_usd(
    *,
    scene_usd_path: Path,
    output_usd_path: Path,
    summary_output: Path | None = None,
    remove_dome_lights: bool = False,
    enable_shadows: bool = False,
    distant_light_intensity: float | None = None,
    distant_light_rotate_x: float | None = None,
) -> dict[str, Any]:
    if not scene_usd_path.is_file():
        raise FileNotFoundError(scene_usd_path)
    if scene_usd_path.resolve() == output_usd_path.resolve():
        raise ValueError("output_usd_path must not overwrite scene_usd_path")
    text = scene_usd_path.read_text(encoding="utf-8", errors="ignore")
    updated = text
    dome_light_remove_count = 0
    shadow_enable_rewrite_count = 0
    distant_light_intensity_rewrite_count = 0
    distant_light_rotate_x_rewrite_count = 0
    distant_light_rotate_x_insert_count = 0
    if remove_dome_lights:
        updated, dome_light_remove_count = _remove_light_blocks(updated, light_type="DomeLight")
    if enable_shadows:
        updated, shadow_enable_rewrite_count = re.subn(
            r"(primvars:doNotCastShadows\s*=\s*)(?:1|true)",
            r"\g<1>false",
            updated,
        )
    if distant_light_intensity is not None or distant_light_rotate_x is not None:
        (
            updated,
            distant_light_intensity_rewrite_count,
            distant_light_rotate_x_rewrite_count,
            distant_light_rotate_x_insert_count,
        ) = _rewrite_distant_light_blocks(
            updated,
            intensity=distant_light_intensity,
            rotate_x=distant_light_rotate_x,
        )
    output_usd_path.parent.mkdir(parents=True, exist_ok=True)
    output_usd_path.write_text(updated, encoding="utf-8")
    metadata_copied = _copy_metadata_next_to_output(
        scene_usd_path=scene_usd_path,
        output_usd_path=output_usd_path,
    )
    total_rewrite_count = (
        dome_light_remove_count
        + shadow_enable_rewrite_count
        + distant_light_intensity_rewrite_count
        + distant_light_rotate_x_rewrite_count
        + distant_light_rotate_x_insert_count
    )
    summary = {
        "schema": SCHEMA,
        "status": "ready" if total_rewrite_count else "no_changes",
        "source_scene_usd_path": str(scene_usd_path),
        "output_usd_path": str(output_usd_path),
        "comparison_only": True,
        "requested_overrides": {
            "remove_dome_lights": remove_dome_lights,
            "enable_shadows": enable_shadows,
            "distant_light_intensity": distant_light_intensity,
            "distant_light_rotate_x": distant_light_rotate_x,
        },
        "dome_light_remove_count": dome_light_remove_count,
        "shadow_enable_rewrite_count": shadow_enable_rewrite_count,
        "distant_light_intensity_rewrite_count": distant_light_intensity_rewrite_count,
        "distant_light_rotate_x_rewrite_count": distant_light_rotate_x_rewrite_count,
        "distant_light_rotate_x_insert_count": distant_light_rotate_x_insert_count,
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


def _remove_light_blocks(text: str, *, light_type: str) -> tuple[str, int]:
    parts: list[str] = []
    cursor = 0
    removed = 0
    for match in re.finditer(rf'(?m)^(\s*)def {re.escape(light_type)} "[^"]+"\s*\{{\s*$', text):
        block_start = match.start()
        block_end = _balanced_block_end(text, match.end() - 1)
        if block_end is None:
            continue
        parts.append(text[cursor:block_start])
        cursor = block_end
        removed += 1
    if not parts:
        return text, 0
    parts.append(text[cursor:])
    return "".join(parts), removed


def _rewrite_distant_light_blocks(
    text: str,
    *,
    intensity: float | None,
    rotate_x: float | None,
) -> tuple[str, int, int, int]:
    parts: list[str] = []
    cursor = 0
    intensity_rewrites = 0
    rotate_rewrites = 0
    rotate_inserts = 0
    for match in re.finditer(r'(?m)^(\s*)def DistantLight "[^"]+"\s*\{\s*$', text):
        block_start = match.start()
        block_end = _balanced_block_end(text, match.end() - 1)
        if block_end is None:
            continue
        block = text[block_start:block_end]
        rewritten = block
        if intensity is not None:
            rewritten, count = re.subn(
                r"float inputs:intensity = [^\s]+",
                f"float inputs:intensity = {_format_float(intensity)}",
                rewritten,
            )
            intensity_rewrites += count
        if rotate_x is not None:
            rewritten, count = re.subn(
                r"float xformOp:rotateX = [^\s]+",
                f"float xformOp:rotateX = {_format_float(rotate_x)}",
                rewritten,
            )
            rotate_rewrites += count
            if count == 0:
                rewritten = _insert_rotate_x(rewritten, rotate_x=rotate_x)
                rotate_inserts += int(rewritten != block)
        parts.append(text[cursor:block_start])
        parts.append(rewritten)
        cursor = block_end
    if not parts:
        return text, 0, 0, 0
    parts.append(text[cursor:])
    return "".join(parts), intensity_rewrites, rotate_rewrites, rotate_inserts


def _insert_rotate_x(block: str, *, rotate_x: float) -> str:
    close_index = block.rfind("}")
    if close_index < 0:
        return block
    match = re.search(r'(?m)^(\s*)def DistantLight "', block)
    indent = match.group(1) + "    " if match else "    "
    insertion = (
        f"{indent}float xformOp:rotateX = {_format_float(rotate_x)}\n"
        f'{indent}uniform token[] xformOpOrder = ["xformOp:rotateX"]\n'
    )
    return block[:close_index] + insertion + block[close_index:]


def _balanced_block_end(text: str, open_brace_index: int) -> int | None:
    depth = 0
    for index in range(open_brace_index, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                if index + 1 < len(text) and text[index + 1] == "\n":
                    return index + 2
                return index + 1
    return None


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

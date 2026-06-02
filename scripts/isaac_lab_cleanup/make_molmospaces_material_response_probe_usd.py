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
        "--material-path-contains",
        help=(
            "Restrict rewrites to Material blocks whose text contains this path fragment. "
            "Use this for target-specific comparison probes."
        ),
    )
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
    parser.add_argument(
        "--diffuse-texture-file",
        type=Path,
        help=(
            "Comparison-only targeted probe: connect PreviewSurface diffuseColor to a "
            "UsdUVTexture shader using this texture file. Requires --material-path-contains."
        ),
    )
    parser.add_argument(
        "--texture-scale-mode",
        choices=("identity", "square"),
        help=(
            "Comparison-only probe for UsdUVTexture scale/fallback response. "
            "'identity' rewrites texture scale/fallback to ones; 'square' applies the "
            "existing RGB scale a second time while preserving alpha."
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    summary = make_material_response_probe_usd(
        scene_usd_path=args.scene_usd_path,
        output_usd_path=args.output_usd_path,
        summary_output=args.summary_output,
        material_path_contains=args.material_path_contains,
        source_color_space=args.source_color_space,
        roughness=args.roughness,
        diffuse_texture_file=args.diffuse_texture_file,
        texture_scale_mode=args.texture_scale_mode,
    )
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["status"] in {"ready", "no_changes"} else 2


def make_material_response_probe_usd(
    *,
    scene_usd_path: Path,
    output_usd_path: Path,
    summary_output: Path | None = None,
    material_path_contains: str | None = None,
    source_color_space: str | None = None,
    roughness: float | None = None,
    diffuse_texture_file: Path | None = None,
    texture_scale_mode: str | None = None,
) -> dict[str, Any]:
    if not scene_usd_path.is_file():
        raise FileNotFoundError(scene_usd_path)
    if scene_usd_path.resolve() == output_usd_path.resolve():
        raise ValueError("output_usd_path must not overwrite scene_usd_path")
    text = scene_usd_path.read_text(encoding="utf-8", errors="ignore")
    if diffuse_texture_file is not None and material_path_contains is None:
        raise ValueError("--diffuse-texture-file requires --material-path-contains")
    if diffuse_texture_file is not None and not diffuse_texture_file.is_file():
        raise FileNotFoundError(diffuse_texture_file)
    if material_path_contains:
        (
            updated,
            source_color_space_rewrite_count,
            roughness_rewrite_count,
            diffuse_texture_injection_count,
            texture_scale_rewrite_count,
            matched_material_block_count,
        ) = _rewrite_matching_material_blocks(
            text,
            material_path_contains=material_path_contains,
            source_color_space=source_color_space,
            roughness=roughness,
            diffuse_texture_file=diffuse_texture_file,
            texture_scale_mode=texture_scale_mode,
        )
    else:
        matched_material_block_count = None
        updated = text
        source_color_space_rewrite_count = 0
        roughness_rewrite_count = 0
        diffuse_texture_injection_count = 0
        texture_scale_rewrite_count = 0
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
        if texture_scale_mode is not None:
            updated, texture_scale_rewrite_count = _rewrite_texture_scale_inputs(
                updated,
                mode=texture_scale_mode,
            )
    output_usd_path.parent.mkdir(parents=True, exist_ok=True)
    output_usd_path.write_text(updated, encoding="utf-8")
    metadata_copied = _copy_metadata_next_to_output(
        scene_usd_path=scene_usd_path,
        output_usd_path=output_usd_path,
    )
    total_rewrite_count = (
        source_color_space_rewrite_count
        + roughness_rewrite_count
        + diffuse_texture_injection_count
        + texture_scale_rewrite_count
    )
    status = "ready" if total_rewrite_count else "no_changes"
    summary = {
        "schema": SCHEMA,
        "status": status,
        "source_scene_usd_path": str(scene_usd_path),
        "output_usd_path": str(output_usd_path),
        "comparison_only": True,
        "requested_overrides": {
            "material_path_contains": material_path_contains,
            "source_color_space": source_color_space,
            "roughness": roughness,
            "diffuse_texture_file": str(diffuse_texture_file) if diffuse_texture_file else None,
            "texture_scale_mode": texture_scale_mode,
        },
        "matched_material_block_count": matched_material_block_count,
        "source_color_space_rewrite_count": source_color_space_rewrite_count,
        "roughness_rewrite_count": roughness_rewrite_count,
        "diffuse_texture_injection_count": diffuse_texture_injection_count,
        "texture_scale_rewrite_count": texture_scale_rewrite_count,
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


def _rewrite_matching_material_blocks(
    text: str,
    *,
    material_path_contains: str,
    source_color_space: str | None,
    roughness: float | None,
    diffuse_texture_file: Path | None,
    texture_scale_mode: str | None,
) -> tuple[str, int, int, int, int, int]:
    parts: list[str] = []
    cursor = 0
    source_color_space_rewrite_count = 0
    roughness_rewrite_count = 0
    diffuse_texture_injection_count = 0
    texture_scale_rewrite_count = 0
    matched_material_block_count = 0
    for match in re.finditer(r'(?m)^(\s*)def Material "[^"]+"\s*\{\s*$', text):
        block_start = match.start()
        block_end = _balanced_block_end(text, match.end() - 1)
        if block_end is None:
            continue
        block = text[block_start:block_end]
        if material_path_contains not in block:
            continue
        matched_material_block_count += 1
        rewritten = block
        if source_color_space is not None:
            rewritten, count = re.subn(
                r'token inputs:sourceColorSpace = "[^"]+"',
                f'token inputs:sourceColorSpace = "{source_color_space}"',
                rewritten,
            )
            source_color_space_rewrite_count += count
        if roughness is not None:
            rewritten, count = re.subn(
                r"float inputs:roughness = [^\s]+",
                f"float inputs:roughness = {_format_float(roughness)}",
                rewritten,
            )
            roughness_rewrite_count += count
        if diffuse_texture_file is not None:
            rewritten, count = _inject_diffuse_texture_shader(
                rewritten,
                texture_file=diffuse_texture_file,
            )
            diffuse_texture_injection_count += count
        if texture_scale_mode is not None:
            rewritten, count = _rewrite_texture_scale_inputs(
                rewritten,
                mode=texture_scale_mode,
            )
            texture_scale_rewrite_count += count
        parts.append(text[cursor:block_start])
        parts.append(rewritten)
        cursor = block_end
    if not parts:
        return text, 0, 0, 0, 0, 0
    parts.append(text[cursor:])
    return (
        "".join(parts),
        source_color_space_rewrite_count,
        roughness_rewrite_count,
        diffuse_texture_injection_count,
        texture_scale_rewrite_count,
        matched_material_block_count,
    )


def _rewrite_texture_scale_inputs(text: str, *, mode: str) -> tuple[str, int]:
    def replacement(match: re.Match[str]) -> str:
        values = _parse_float_values(match.group(2))
        if not values:
            return match.group(0)
        if mode == "identity":
            rewritten = [1.0 for _ in values]
        elif mode == "square":
            rewritten = [value * value for value in values]
            if len(rewritten) >= 4:
                rewritten[3] = values[3]
        else:
            raise ValueError(f"unsupported texture scale mode: {mode}")
        return f"{match.group(1)}({_format_float_list(rewritten)})"

    return re.subn(
        r"(float[234]? inputs:(?:scale|fallback) = )\(([^)]+)\)",
        replacement,
        text,
    )


def _inject_diffuse_texture_shader(block: str, *, texture_file: Path) -> tuple[str, int]:
    material_path = _material_path_from_connect(block)
    if not material_path or 'def Shader "PreviewSurface"' not in block:
        return block, 0
    texture_shader_path = f"{material_path}/DiffuseTexture"
    if 'def Shader "DiffuseTexture"' in block:
        updated = re.sub(
            r"asset inputs:file = @[^@]+@",
            f"asset inputs:file = @{texture_file}@",
            block,
            count=1,
        )
        updated = _ensure_diffuse_color_connect(updated, texture_shader_path)
        return updated, int(updated != block)
    updated = _ensure_diffuse_color_connect(block, texture_shader_path)
    preview_end = _preview_surface_block_end(updated)
    if preview_end is None:
        return block, 0
    indent = _preview_surface_indent(updated)
    shader = (
        f'\n{indent}def Shader "DiffuseTexture"\n'
        f"{indent}{{\n"
        f'{indent}    uniform token info:id = "UsdUVTexture"\n'
        f"{indent}    float4 inputs:fallback = (1, 1, 1, 1)\n"
        f"{indent}    asset inputs:file = @{texture_file}@\n"
        f'{indent}    token inputs:sourceColorSpace = "auto"\n'
        f'{indent}    token inputs:wrapS = "repeat"\n'
        f'{indent}    token inputs:wrapT = "repeat"\n'
        f"{indent}    float3 outputs:rgb\n"
        f"{indent}}}\n"
    )
    return updated[:preview_end] + shader + updated[preview_end:], 1


def _material_path_from_connect(block: str) -> str | None:
    match = re.search(
        r"outputs:surface\.connect = <([^>]+)/PreviewSurface\.outputs:surface>", block
    )
    if not match:
        return None
    return match.group(1)


def _ensure_diffuse_color_connect(block: str, texture_shader_path: str) -> str:
    connect = f"color3f inputs:diffuseColor.connect = <{texture_shader_path}.outputs:rgb>"
    if "inputs:diffuseColor.connect" in block:
        return re.sub(r"color3f inputs:diffuseColor\.connect = <[^>]+>", connect, block, count=1)
    return re.sub(
        r"color3f inputs:diffuseColor = \([^\n]+\)",
        connect,
        block,
        count=1,
    )


def _preview_surface_block_end(block: str) -> int | None:
    match = re.search(r'(?m)^(\s*)def Shader "PreviewSurface"\s*\{\s*$', block)
    if not match:
        return None
    return _balanced_block_end(block, match.end() - 1)


def _preview_surface_indent(block: str) -> str:
    match = re.search(r'(?m)^(\s*)def Shader "PreviewSurface"', block)
    return str(match.group(1)) if match else "    "


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


def _format_float_list(values: list[float]) -> str:
    return ", ".join(_format_float(value) for value in values)


def _parse_float_values(text: str) -> list[float]:
    values: list[float] = []
    for raw in re.split(r"[\s,]+", text.strip()):
        if not raw:
            continue
        try:
            values.append(float(raw))
        except ValueError:
            return []
    return values


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "make_molmospaces_material_response_probe_usd.py"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_material_response_probe_rewrites_texture_color_space_and_roughness(
    tmp_path: Path,
) -> None:
    probe = _load_module(SCRIPT_PATH, "make_molmospaces_material_response_probe_usd")
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_usd = source_dir / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Material "mat"
{
    def Shader "PreviewSurface"
    {
        uniform token info:id = "UsdPreviewSurface"
        float inputs:roughness = 0.5
    }
    def Shader "DiffuseTexture"
    {
        token inputs:sourceColorSpace = "auto"
    }
}
""",
        encoding="utf-8",
    )
    (source_dir / "scene_metadata.json").write_text('{"objects": {}}', encoding="utf-8")
    output_usd = tmp_path / "probe" / "scene_semantic.usda"
    summary_path = tmp_path / "probe" / "summary.json"

    summary = probe.make_material_response_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        summary_output=summary_path,
        source_color_space="raw",
        roughness=1.0,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["schema"] == "roboclaws_molmospaces_material_response_probe_usd_v1"
    assert summary["status"] == "ready"
    assert summary["comparison_only"] is True
    assert summary["source_color_space_rewrite_count"] == 1
    assert summary["roughness_rewrite_count"] == 1
    assert summary["scene_metadata_copied"] is True
    assert 'token inputs:sourceColorSpace = "raw"' in text
    assert "float inputs:roughness = 1" in text
    assert 'token inputs:sourceColorSpace = "auto"' in source_usd.read_text(encoding="utf-8")
    assert (output_usd.parent / "scene_metadata.json").is_file()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == "ready"


def test_material_response_probe_can_target_one_material_block(tmp_path: Path) -> None:
    probe = _load_module(SCRIPT_PATH, "make_molmospaces_material_response_probe_usd_targeted")
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Xform "a"
{
    def Scope "Materials"
    {
        def Material "material_LightWoodCounters3"
        {
            token outputs:surface.connect = </a/M/material_LightWoodCounters3/PS.outputs:surface>
            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                float inputs:roughness = 0.5
            }
            def Shader "DiffuseTexture"
            {
                token inputs:sourceColorSpace = "auto"
            }
        }
    }
}
def Xform "b"
{
    def Scope "Materials"
    {
        def Material "material_LightWoodCounters3"
        {
            token outputs:surface.connect = </b/M/material_LightWoodCounters3/PS.outputs:surface>
            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                float inputs:roughness = 0.5
            }
            def Shader "DiffuseTexture"
            {
                token inputs:sourceColorSpace = "auto"
            }
        }
    }
}
""",
        encoding="utf-8",
    )
    output_usd = tmp_path / "targeted" / "scene_semantic.usda"

    summary = probe.make_material_response_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        material_path_contains="/a/M/material_LightWoodCounters3",
        source_color_space="raw",
        roughness=1.0,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["matched_material_block_count"] == 1
    assert summary["source_color_space_rewrite_count"] == 1
    assert summary["roughness_rewrite_count"] == 1
    assert "float inputs:roughness = 1" in text
    assert 'token inputs:sourceColorSpace = "raw"' in text
    assert text.count("float inputs:roughness = 0.5") == 1
    assert text.count('token inputs:sourceColorSpace = "auto"') == 1


def test_material_response_probe_can_inject_targeted_diffuse_texture(
    tmp_path: Path,
) -> None:
    probe = _load_module(
        SCRIPT_PATH,
        "make_molmospaces_material_response_probe_usd_diffuse_texture",
    )
    texture = tmp_path / "PillowD_AO.png"
    texture.write_bytes(b"fake-png")
    source_usd = tmp_path / "scene_semantic.usda"
    connect_line = (
        "            token outputs:surface.connect = "
        "</pillow/Materials/material_Pillow14_Mat/PreviewSurface.outputs:surface>"
    )
    source_usd.write_text(
        """#usda 1.0
def Xform "pillow"
{
    def Scope "Materials"
    {
        def Material "material_Pillow14_Mat"
        {
CONNECT_LINE
            def Shader "PreviewSurface"
            {
                uniform token info:id = "UsdPreviewSurface"
                color3f inputs:diffuseColor = (0.298039, 0.12549, 0.376471)
                float inputs:roughness = 0.5
                token outputs:surface
            }
        }
    }
}
""".replace("CONNECT_LINE", connect_line),
        encoding="utf-8",
    )
    output_usd = tmp_path / "targeted" / "scene_semantic.usda"

    summary = probe.make_material_response_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        material_path_contains="/pillow/Materials/material_Pillow14_Mat",
        diffuse_texture_file=texture,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["status"] == "ready"
    assert summary["matched_material_block_count"] == 1
    assert summary["diffuse_texture_injection_count"] == 1
    assert summary["total_rewrite_count"] == 1
    assert (
        "color3f inputs:diffuseColor.connect = "
        "</pillow/Materials/material_Pillow14_Mat/DiffuseTexture.outputs:rgb>"
    ) in text
    assert 'def Shader "DiffuseTexture"' in text
    assert f"asset inputs:file = @{texture}@" in text
    assert "color3f inputs:diffuseColor = (0.298039, 0.12549, 0.376471)" not in text
    assert "color3f inputs:diffuseColor =" in source_usd.read_text(encoding="utf-8")


def test_material_response_probe_can_rewrite_targeted_texture_scale(
    tmp_path: Path,
) -> None:
    probe = _load_module(
        SCRIPT_PATH,
        "make_molmospaces_material_response_probe_usd_texture_scale",
    )
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Xform "a"
{
    def Scope "Materials"
    {
        def Material "material_LightWoodCounters3"
        {
            token outputs:surface.connect = </a/M/material_LightWoodCounters3/PS.outputs:surface>
            def Shader "DiffuseTexture"
            {
                float4 inputs:fallback = (0.5, 0.25, 0.1, 1)
                float4 inputs:scale = (0.5, 0.25, 0.1, 1)
            }
        }
    }
}
def Xform "b"
{
    def Scope "Materials"
    {
        def Material "material_LightWoodCounters3"
        {
            token outputs:surface.connect = </b/M/material_LightWoodCounters3/PS.outputs:surface>
            def Shader "DiffuseTexture"
            {
                float4 inputs:fallback = (0.8, 0.7, 0.6, 1)
                float4 inputs:scale = (0.8, 0.7, 0.6, 1)
            }
        }
    }
}
""",
        encoding="utf-8",
    )
    output_usd = tmp_path / "targeted" / "scene_semantic.usda"

    summary = probe.make_material_response_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        material_path_contains="/a/M/material_LightWoodCounters3",
        texture_scale_mode="square",
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["status"] == "ready"
    assert summary["matched_material_block_count"] == 1
    assert summary["texture_scale_rewrite_count"] == 2
    assert summary["total_rewrite_count"] == 2
    assert "float4 inputs:fallback = (0.25, 0.0625, 0.01, 1)" in text
    assert "float4 inputs:scale = (0.25, 0.0625, 0.01, 1)" in text
    assert "float4 inputs:fallback = (0.8, 0.7, 0.6, 1)" in text
    assert "float4 inputs:scale = (0.8, 0.7, 0.6, 1)" in text


def test_material_response_probe_can_rewrite_texture_scale_with_power(
    tmp_path: Path,
) -> None:
    probe = _load_module(
        SCRIPT_PATH,
        "make_molmospaces_material_response_probe_usd_texture_scale_power",
    )
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Xform "a"
{
    def Scope "Materials"
    {
        def Material "material_LightWoodCounters3"
        {
            token outputs:surface.connect = </a/M/material_LightWoodCounters3/PS.outputs:surface>
            def Shader "DiffuseTexture"
            {
                float4 inputs:fallback = (0.5, 0.25, 0.1, 1)
                float4 inputs:scale = (0.5, 0.25, 0.1, 1)
            }
        }
    }
}
""",
        encoding="utf-8",
    )
    output_usd = tmp_path / "targeted" / "scene_semantic.usda"

    summary = probe.make_material_response_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        material_path_contains="/a/M/material_LightWoodCounters3",
        texture_scale_power=1.5,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["status"] == "ready"
    assert summary["requested_overrides"]["texture_scale_power"] == 1.5
    assert summary["texture_scale_rewrite_count"] == 2
    assert "float4 inputs:fallback = (0.353553, 0.125, 0.0316228, 1)" in text
    assert "float4 inputs:scale = (0.353553, 0.125, 0.0316228, 1)" in text


def test_material_response_probe_rejects_texture_scale_mode_and_power(
    tmp_path: Path,
) -> None:
    probe = _load_module(
        SCRIPT_PATH,
        "make_molmospaces_material_response_probe_usd_texture_scale_power_invalid",
    )
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")

    try:
        probe.make_material_response_probe_usd(
            scene_usd_path=source_usd,
            output_usd_path=tmp_path / "targeted" / "scene_semantic.usda",
            texture_scale_mode="square",
            texture_scale_power=1.5,
        )
    except ValueError as exc:
        assert "mutually exclusive" in str(exc)
    else:
        raise AssertionError("expected mutually exclusive texture scale options to fail")

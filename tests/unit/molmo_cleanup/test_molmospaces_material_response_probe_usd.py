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

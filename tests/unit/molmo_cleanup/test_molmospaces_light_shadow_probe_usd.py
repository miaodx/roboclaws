from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = (
    REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "make_molmospaces_light_shadow_probe_usd.py"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_light_shadow_probe_removes_dome_and_enables_shadows(tmp_path: Path) -> None:
    probe = _load_module(SCRIPT_PATH, "make_molmospaces_light_shadow_probe_usd")
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    source_usd = source_dir / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Xform "World"
{
    def Mesh "wall"
    {
        bool primvars:doNotCastShadows = true
    }

    def Mesh "ceiling"
    {
        bool primvars:doNotCastShadows = 1
    }

    def DomeLight "scene_skybox_light"
    {
        float inputs:intensity = 1000
    }

    def DistantLight "scene_dir_light"
    {
        float inputs:intensity = 1000
        float xformOp:rotateX = -10
        uniform token[] xformOpOrder = ["xformOp:rotateX"]
    }
}
""",
        encoding="utf-8",
    )
    (source_dir / "scene_metadata.json").write_text('{"scene": "unit"}', encoding="utf-8")
    output_usd = tmp_path / "probe" / "scene_semantic.usda"
    summary_path = tmp_path / "probe" / "summary.json"

    summary = probe.make_light_shadow_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        summary_output=summary_path,
        remove_dome_lights=True,
        enable_shadows=True,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["schema"] == "roboclaws_molmospaces_light_shadow_probe_usd_v1"
    assert summary["status"] == "ready"
    assert summary["comparison_only"] is True
    assert summary["dome_light_remove_count"] == 1
    assert summary["shadow_enable_rewrite_count"] == 2
    assert summary["total_rewrite_count"] == 3
    assert summary["scene_metadata_copied"] is True
    assert 'def DomeLight "scene_skybox_light"' not in text
    assert "bool primvars:doNotCastShadows = false" in text
    assert 'def DistantLight "scene_dir_light"' in text
    assert 'def DomeLight "scene_skybox_light"' in source_usd.read_text(encoding="utf-8")
    assert (output_usd.parent / "scene_metadata.json").is_file()
    assert json.loads(summary_path.read_text(encoding="utf-8"))["status"] == "ready"


def test_light_shadow_probe_rewrites_distant_light_intensity_and_rotation(
    tmp_path: Path,
) -> None:
    probe = _load_module(SCRIPT_PATH, "make_molmospaces_light_shadow_probe_usd_lights")
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text(
        """#usda 1.0
def Xform "World"
{
    def DistantLight "scene_dir_light"
    {
        float inputs:intensity = 1000
        float xformOp:rotateX = -10
        uniform token[] xformOpOrder = ["xformOp:rotateX"]
    }

    def DistantLight "fill_light"
    {
        float inputs:intensity = 250
    }
}
""",
        encoding="utf-8",
    )
    output_usd = tmp_path / "probe" / "scene_semantic.usda"

    summary = probe.make_light_shadow_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
        distant_light_intensity=500.0,
        distant_light_rotate_x=-35.0,
    )

    text = output_usd.read_text(encoding="utf-8")
    assert summary["status"] == "ready"
    assert summary["distant_light_intensity_rewrite_count"] == 2
    assert summary["distant_light_rotate_x_rewrite_count"] == 1
    assert summary["distant_light_rotate_x_insert_count"] == 1
    assert text.count("float inputs:intensity = 500") == 2
    assert text.count("float xformOp:rotateX = -35") == 2
    assert 'uniform token[] xformOpOrder = ["xformOp:rotateX"]' in text


def test_light_shadow_probe_reports_no_changes(tmp_path: Path) -> None:
    probe = _load_module(SCRIPT_PATH, "make_molmospaces_light_shadow_probe_usd_noop")
    source_usd = tmp_path / "scene_semantic.usda"
    source_usd.write_text("#usda 1.0\n", encoding="utf-8")
    output_usd = tmp_path / "probe" / "scene_semantic.usda"

    summary = probe.make_light_shadow_probe_usd(
        scene_usd_path=source_usd,
        output_usd_path=output_usd,
    )

    assert summary["status"] == "no_changes"
    assert summary["total_rewrite_count"] == 0
    assert output_usd.read_text(encoding="utf-8") == "#usda 1.0\n"

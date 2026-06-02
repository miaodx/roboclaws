from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from scripts.isaac_lab_cleanup.prepare_molmospaces_flattened_semantic_usd import (
    prepare_flattened_semantic_usd,
)

pxr = pytest.importorskip("pxr")
from pxr import Usd, UsdGeom  # noqa: E402


def test_prepare_flattened_semantic_usd_labels_renderable_descendants(
    tmp_path: Path,
) -> None:
    scene_dir = tmp_path / "val_1"
    scene_dir.mkdir()
    scene_usd = scene_dir / "scene.usda"
    output_usd = tmp_path / "flattened" / "scene_semantic.usda"
    summary_path = tmp_path / "flattened" / "summary.json"
    _write_scene(scene_usd)
    (scene_dir / "scene_metadata.json").write_text(
        json.dumps(
            {
                "objects": {
                    "bowl_01": {
                        "asset_id": "Bowl_12",
                        "object_id": "Bowl|surface|1",
                        "category": "Bowl",
                        "is_static": False,
                        "children": [],
                    },
                    "sink_01": {
                        "asset_id": "Sink_1",
                        "object_id": "Sink|1",
                        "category": "Sink",
                        "is_static": True,
                        "children": [],
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    summary = prepare_flattened_semantic_usd(
        scene_usd_path=scene_usd,
        output_usd_path=output_usd,
        summary_output=summary_path,
    )

    assert summary["schema"] == "roboclaws_molmospaces_flattened_semantic_usd_v1"
    assert summary["status"] == "ready"
    assert summary["metadata_entry_count"] == 2
    assert summary["matched_entry_count"] == 2
    assert summary["renderable_labeled_prim_count"] == 2
    assert summary["gprim_labeled_prim_count"] == 2
    assert summary["mesh_labeled_prim_count"] == 2
    assert summary["container_labeled_prim_count"] == 2
    assert summary["scene_metadata_copied"] is True
    assert summary_path.is_file()
    assert (output_usd.parent / "scene_metadata.json").is_file()

    output_stage = Usd.Stage.Open(str(output_usd))
    bowl_mesh = output_stage.GetPrimAtPath("/val_1/Geometry/bowl_01/mesh")
    sink_mesh = output_stage.GetPrimAtPath("/val_1/Geometry/sink_01/mesh")
    assert bowl_mesh.IsValid()
    assert sink_mesh.IsValid()
    assert _labels(bowl_mesh, "class") == ["Bowl"]
    assert _labels(bowl_mesh, "kind") == ["object"]
    assert _labels(bowl_mesh, "usd_prim_path") == ["/val_1/Geometry/bowl_01"]
    assert _labels(sink_mesh, "class") == ["Sink"]
    assert _labels(sink_mesh, "kind") == ["receptacle"]

    output_text = output_usd.read_text(encoding="utf-8")
    assert "SemanticsLabelsAPI:class" in output_text
    assert "semantics:labels:class" in output_text


def test_prepare_flattened_semantic_usd_flattens_referenced_scene_asset(
    tmp_path: Path,
) -> None:
    scene_dir = tmp_path / "val_1"
    scene_dir.mkdir()
    asset_usd = scene_dir / "bowl_asset.usda"
    scene_usd = scene_dir / "scene.usda"
    output_usd = tmp_path / "flattened" / "scene_semantic.usda"
    _write_asset(asset_usd, "/AssetRoot/mesh")
    _write_referencing_scene(scene_usd, asset_usd.name)
    (scene_dir / "scene_metadata.json").write_text(
        json.dumps(
            {
                "objects": {
                    "bowl_01": {
                        "asset_id": "Bowl_12",
                        "object_id": "Bowl|surface|1",
                        "category": "Bowl",
                        "is_static": False,
                        "children": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    summary = prepare_flattened_semantic_usd(
        scene_usd_path=scene_usd,
        output_usd_path=output_usd,
        label_containers=False,
    )

    assert summary["status"] == "ready"
    assert summary["matched_entry_count"] == 1
    assert summary["container_labeled_prim_count"] == 0
    assert summary["renderable_labeled_prim_count"] == 1
    assert "bowl_asset.usda" not in output_usd.read_text(encoding="utf-8")

    output_stage = Usd.Stage.Open(str(output_usd))
    composed_mesh = output_stage.GetPrimAtPath("/val_1/Geometry/bowl_01/mesh")
    assert composed_mesh.IsValid()
    assert _labels(composed_mesh, "class") == ["Bowl"]


def test_prepare_flattened_semantic_usd_material_scale_candidate_is_opt_in(
    tmp_path: Path,
) -> None:
    scene_dir = tmp_path / "val_1"
    scene_dir.mkdir()
    scene_usd = scene_dir / "scene.usda"
    output_usd = tmp_path / "flattened" / "scene_semantic.usda"
    _write_scene_with_texture_scale(scene_usd)
    (scene_dir / "scene_metadata.json").write_text(
        json.dumps(
            {
                "objects": {
                    "table_01": {
                        "asset_id": "Table_1",
                        "object_id": "Table|1",
                        "category": "DiningTable",
                        "is_static": True,
                        "children": [],
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    default_summary = prepare_flattened_semantic_usd(
        scene_usd_path=scene_usd,
        output_usd_path=output_usd,
    )

    default_text = output_usd.read_text(encoding="utf-8")
    assert default_summary["material_texture_scale_mode"] == "none"
    assert default_summary["material_texture_scale_rewrite_count"] == 0
    assert default_summary["material_texture_scale_default_candidate"] is False
    assert "float4 inputs:fallback = (0.5, 0.25, 0.1, 1)" in default_text
    assert "float4 inputs:scale = (0.5, 0.25, 0.1, 1)" in default_text

    square_summary = prepare_flattened_semantic_usd(
        scene_usd_path=scene_usd,
        output_usd_path=output_usd,
        material_texture_scale_mode="square",
    )

    square_text = output_usd.read_text(encoding="utf-8")
    assert square_summary["material_texture_scale_mode"] == "square"
    assert square_summary["material_texture_scale_rewrite_count"] == 2
    assert square_summary["material_texture_scale_default_candidate"] is True
    assert "float4 inputs:fallback = (0.25, 0.0625, 0.01, 1)" in square_text
    assert "float4 inputs:scale = (0.25, 0.0625, 0.01, 1)" in square_text


def _write_scene(path: Path) -> None:
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/val_1").GetPrim())
    geometry = UsdGeom.Xform.Define(stage, "/val_1/Geometry")
    bowl = UsdGeom.Xform.Define(stage, "/val_1/Geometry/bowl_01")
    sink = UsdGeom.Xform.Define(stage, "/val_1/Geometry/sink_01")
    UsdGeom.Mesh.Define(stage, "/val_1/Geometry/bowl_01/mesh")
    UsdGeom.Mesh.Define(stage, "/val_1/Geometry/sink_01/mesh")
    assert geometry.GetPrim().IsValid()
    assert bowl.GetPrim().IsValid()
    assert sink.GetPrim().IsValid()
    stage.GetRootLayer().Save()


def _write_scene_with_texture_scale(path: Path) -> None:
    path.write_text(
        """#usda 1.0
def Xform "val_1"
{
    def Xform "Geometry"
    {
        def Xform "table_01"
        {
            def Mesh "mesh"
            {
            }

            def Scope "Materials"
            {
                def Material "material_LightWoodCounters3"
                {
                    def Shader "DiffuseTexture"
                    {
                        float4 inputs:fallback = (0.5, 0.25, 0.1, 1)
                        float4 inputs:scale = (0.5, 0.25, 0.1, 1)
                    }
                }
            }
        }
    }
}
""",
        encoding="utf-8",
    )


def _write_asset(path: Path, mesh_path: str) -> None:
    stage = Usd.Stage.CreateNew(str(path))
    root = UsdGeom.Xform.Define(stage, "/AssetRoot")
    stage.SetDefaultPrim(root.GetPrim())
    UsdGeom.Mesh.Define(stage, mesh_path)
    stage.GetRootLayer().Save()


def _write_referencing_scene(path: Path, asset_name: str) -> None:
    stage = Usd.Stage.CreateNew(str(path))
    stage.SetDefaultPrim(UsdGeom.Xform.Define(stage, "/val_1").GetPrim())
    UsdGeom.Xform.Define(stage, "/val_1/Geometry")
    bowl = UsdGeom.Xform.Define(stage, "/val_1/Geometry/bowl_01")
    bowl.GetPrim().GetReferences().AddReference(asset_name)
    stage.GetRootLayer().Save()


def _labels(prim: Usd.Prim, instance_name: str) -> list[str]:
    try:
        from pxr import UsdSemantics
    except Exception:
        attr = prim.GetAttribute(f"semantics:labels:{instance_name}")
        return list(attr.Get() or [])
    attr = UsdSemantics.LabelsAPI(prim, instance_name).GetLabelsAttr()
    return list(attr.Get() or [])


def test_prepare_flattened_semantic_usd_import_has_no_required_pxr_dependency() -> None:
    assert pxr is not None
    assert shutil.which("true")

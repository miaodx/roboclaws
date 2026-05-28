from __future__ import annotations

import json
from pathlib import Path

from scripts.isaac_lab_cleanup import install_molmospaces_usd_references as installer


class FakeTrie:
    def __init__(self, leaves: list[str]) -> None:
        self._leaves = leaves

    def leaf_paths(self) -> list[str]:
        return self._leaves


def test_missing_referenced_assets_are_collected_from_nested_artifacts(tmp_path: Path) -> None:
    artifact = tmp_path / "state.json"
    artifact.write_text(
        json.dumps(
            {
                "scene_binding_diagnostics": {
                    "selected_object_bindings": {
                        "bowl_01": {
                            "missing_referenced_assets": [
                                "/repo/output/isaaclab/molmospaces-usd/objects/thor/Bowl_12_mesh/Bowl_12_mesh.usda"
                            ]
                        }
                    },
                    "selected_target_receptacle_bindings": {
                        "sink_01": {
                            "missing_referenced_assets": [
                                "/repo/output/isaaclab/molmospaces-usd/objects/thor/Sink_1_mesh/Sink_1_mesh.usda"
                            ]
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    assert installer._missing_referenced_assets([artifact]) == [
        "/repo/output/isaaclab/molmospaces-usd/objects/thor/Bowl_12_mesh/Bowl_12_mesh.usda",
        "/repo/output/isaaclab/molmospaces-usd/objects/thor/Sink_1_mesh/Sink_1_mesh.usda",
    ]


def test_install_plan_maps_missing_usd_references_to_object_packages() -> None:
    plan = installer._build_install_plan(
        asset_paths=[
            "/repo/output/isaaclab/molmospaces-usd/objects/thor/Bowl_12_mesh/Bowl_12_mesh.usda",
            "/repo/output/isaaclab/molmospaces-usd/objects/thor/Sink_1_mesh/Sink_1_mesh.usda",
        ],
        package_names=[],
        available_packages=["thor_Bowl.tar.zst", "thor_Sink.tar.zst"],
        tries={
            "thor_Bowl.tar.zst": FakeTrie(["Bowl_12_mesh/Bowl_12_mesh.usda"]),
            "thor_Sink.tar.zst": FakeTrie(["Sink_1_mesh/Sink_1_mesh.usda"]),
        },
        install_dir=Path("/repo/output/isaaclab/molmospaces-usd"),
        source="thor",
        all_objects=False,
    )

    assert plan.asset_suffixes == [
        "Bowl_12_mesh/Bowl_12_mesh.usda",
        "Sink_1_mesh/Sink_1_mesh.usda",
    ]
    assert plan.packages == ["thor_Bowl.tar.zst", "thor_Sink.tar.zst"]
    assert plan.unresolved_assets == []


def test_install_plan_reports_unresolved_references() -> None:
    plan = installer._build_install_plan(
        asset_paths=["/repo/output/isaaclab/molmospaces-usd/objects/thor/Missing.usda"],
        package_names=[],
        available_packages=["thor_Bowl.tar.zst"],
        tries={"thor_Bowl.tar.zst": FakeTrie(["Bowl_12_mesh/Bowl_12_mesh.usda"])},
        install_dir=Path("/repo/output/isaaclab/molmospaces-usd"),
        source="thor",
        all_objects=False,
    )

    assert plan.packages == []
    assert plan.unresolved_assets == [
        "/repo/output/isaaclab/molmospaces-usd/objects/thor/Missing.usda"
    ]


def test_cache_root_asset_links_expose_versioned_assets_for_kit(tmp_path: Path) -> None:
    versioned_bowl = tmp_path / "usd" / "objects" / "thor" / "20260128" / "Bowl_12_mesh"
    versioned_bowl.mkdir(parents=True)

    result = installer._ensure_cache_root_asset_links(
        cache_dir=tmp_path,
        source="thor",
        version="20260128",
        asset_suffixes=["Bowl_12_mesh/Bowl_12_mesh.usda"],
        dry_run=False,
    )

    root_link = tmp_path / "usd" / "objects" / "thor" / "Bowl_12_mesh"
    kit_scene_link = tmp_path / "usd" / "scenes" / "objects" / "thor" / "Bowl_12_mesh"
    assert result["created"] == ["Bowl_12_mesh"]
    assert result["created_count"] == 2
    assert root_link.is_symlink()
    assert root_link.resolve() == versioned_bowl
    assert kit_scene_link.is_symlink()
    assert kit_scene_link.resolve() == versioned_bowl
    assert result["link_roots"] == [
        {
            "kind": "cache_object_root",
            "path": str(tmp_path / "usd" / "objects" / "thor"),
            "created": ["Bowl_12_mesh"],
            "present": [],
            "conflicts": [],
        },
        {
            "kind": "kit_scene_object_root",
            "path": str(tmp_path / "usd" / "scenes" / "objects" / "thor"),
            "created": ["Bowl_12_mesh"],
            "present": [],
            "conflicts": [],
        },
    ]

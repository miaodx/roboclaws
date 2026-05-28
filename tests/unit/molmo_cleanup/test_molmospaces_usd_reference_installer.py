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

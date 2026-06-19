from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GENERATOR_PATH = REPO_ROOT / "scripts" / "maps" / "generate_molmospaces_scene_bundles.py"


def test_active_sampler_generation_targets_current_product_scene_set() -> None:
    generator = _load_generator()

    targets = generator.generation_targets(
        active_sampler_scenes=True,
        scene_specs=(),
        scene_source=None,
        scene_index=None,
    )
    tokens = [target.token for target in targets]

    assert tokens == [
        "procthor-10k-val/0",
        "procthor-objaverse-val/0",
        "procthor-objaverse-val/1",
        "procthor-objaverse-val/10",
        "procthor-10k-val/10",
        "procthor-10k-val/11",
        "procthor-10k-val/12",
        "procthor-10k-val/13",
        "procthor-10k-val/15",
        "procthor-objaverse-val/4",
        "procthor-objaverse-val/5",
        "procthor-objaverse-val/7",
        "procthor-objaverse-val/11",
        "procthor-objaverse-val/12",
        "procthor-objaverse-val/13",
        "procthor-objaverse-val/14",
    ]


def test_generation_plan_uses_canonical_molmospaces_asset_paths(tmp_path: Path) -> None:
    generator = _load_generator()
    targets = generator.generation_targets(
        active_sampler_scenes=False,
        scene_specs=("procthor-objaverse-val/10",),
        scene_source=None,
        scene_index=None,
    )

    plan = generator.generation_plan(targets, asset_root=tmp_path / "assets" / "maps")

    assert plan["schema"] == "molmospaces_scene_nav2_bundle_generation_v1"
    assert plan["target_count"] == 1
    assert plan["targets"][0]["output_dir"].endswith(
        "assets/maps/molmospaces/procthor-objaverse-val/10"
    )


def test_generation_targets_reject_partial_explicit_scene() -> None:
    generator = _load_generator()

    with pytest.raises(SystemExit, match="provide both --scene-source and --scene-index"):
        generator.generation_targets(
            active_sampler_scenes=False,
            scene_specs=(),
            scene_source="procthor-10k-val",
            scene_index=None,
        )


def test_canonical_scene_metric_map_identity_does_not_include_seed() -> None:
    generator = _load_generator()
    metric_map = {
        "map_id": "molmospaces-procthor-10k-val-0-7_base_navigation_map",
        "map_version": "base-navigation-map-v1",
        "map_bundle": {
            "environment_id": "molmospaces-procthor-10k-val-0-7",
            "parameter_hash": "seed-specific",
        },
    }

    canonical = generator.canonical_scene_metric_map(
        metric_map,
        scene_source="procthor-10k-val",
        scene_index=0,
    )

    assert canonical["map_id"] == "molmospaces-procthor-10k-val-0_base_navigation_map"
    assert canonical["map_bundle"]["environment_id"] == "molmospaces-procthor-10k-val-0"
    assert canonical["map_bundle"]["map_id"] == canonical["map_id"]
    assert canonical["map_bundle"]["parameter_hash"] != "seed-specific"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "generate_molmospaces_scene_bundles",
        GENERATOR_PATH,
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

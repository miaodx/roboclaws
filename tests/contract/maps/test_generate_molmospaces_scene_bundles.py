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


def test_generation_uses_source_map_static_fixtures_not_agent_view_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = _load_generator()
    captured: dict[str, object] = {}

    class FakeSession:
        def close(self) -> None:
            captured["closed"] = True

    class FakeValidation:
        def __init__(self, root: Path) -> None:
            self.root = root

        def raise_for_errors(self) -> None:
            captured["validated"] = self.root

        def as_dict(self) -> dict[str, object]:
            return {"ok": True, "root": self.root.as_posix()}

    class FakeContract:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def agent_view_payload(self) -> dict[str, object]:
            return {
                "metric_map": _minimal_metric_map(),
                "static_fixture_projection": {
                    "schema": "static_fixture_projection_v1",
                    "rooms": [],
                },
            }

        def source_map_static_fixture_projection(self) -> dict[str, object]:
            return {
                "schema": "static_fixture_projection_v1",
                "rooms": [
                    {
                        "room_id": "room_1",
                        "fixtures": [
                            {
                                "fixture_id": "sink_01",
                                "category": "sink",
                                "name": "sink",
                                "room_id": "room_1",
                                "affordances": ["place"],
                                "footprint": {
                                    "shape": "rectangle",
                                    "width_m": 0.5,
                                    "depth_m": 0.4,
                                },
                                "pose": {
                                    "frame_id": "map",
                                    "x": 0.3,
                                    "y": 0.3,
                                    "yaw": 0.0,
                                },
                                "preferred_inspection_waypoint_id": "wp_1",
                                "preferred_manipulation_waypoint_id": "wp_1",
                            }
                        ],
                    }
                ],
            }

    def fake_write_nav2_map_bundle(
        bundle_dir: Path,
        *,
        metric_map: dict[str, object],
        static_landmarks: list[dict[str, object]],
    ) -> dict[str, object]:
        captured["metric_map"] = metric_map
        captured["static_landmarks"] = static_landmarks
        bundle_dir.mkdir(parents=True, exist_ok=True)
        return {
            "map_id": metric_map["map_id"],
            "environment_id": metric_map["map_bundle"]["environment_id"],  # type: ignore[index]
            "parameter_hash": "hash",
        }

    monkeypatch.setattr(generator, "build_cleanup_backend_session", lambda **_kwargs: FakeSession())
    monkeypatch.setattr(generator, "RealWorldCleanupContract", FakeContract)
    monkeypatch.setattr(generator, "write_nav2_map_bundle", fake_write_nav2_map_bundle)
    monkeypatch.setattr(generator, "validate_nav2_map_bundle", lambda path: FakeValidation(path))
    monkeypatch.setattr(generator.shutil, "move", lambda source, destination: None)

    result = generator._generate_scene_bundle(
        generator.SceneTarget("procthor-10k-val", 0),
        asset_root=tmp_path / "assets" / "maps",
        run_root=tmp_path / "runs",
        seed=7,
        molmospaces_python=None,
        force=True,
    )

    assert result["validation"]["ok"] is True
    assert captured["closed"] is True
    assert captured["static_landmarks"] == [
        {
            "fixture_id": "sink_01",
            "category": "sink",
            "name": "sink",
            "room_id": "room_1",
            "affordances": ["place"],
            "footprint": {"shape": "rectangle", "width_m": 0.5, "depth_m": 0.4},
            "pose": {"frame_id": "map", "x": 0.3, "y": 0.3, "yaw": 0.0},
            "preferred_inspection_waypoint_id": "wp_1",
            "preferred_manipulation_waypoint_id": "wp_1",
            "landmark_id": "sink_01",
        }
    ]


def _minimal_metric_map() -> dict[str, object]:
    return {
        "schema": "real_robot_map_bundle_v1",
        "frame_id": "map",
        "map_id": "source_map",
        "map_version": "base-navigation-map-v1",
        "resolution_m": 0.05,
        "origin": {"x": 0.0, "y": 0.0, "yaw": 0.0},
        "width": 20,
        "height": 20,
        "rooms": [
            {
                "room_id": "room_1",
                "room_label": "room 1",
                "polygon": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 1.0, "y": 0.0},
                    {"x": 1.0, "y": 1.0},
                    {"x": 0.0, "y": 1.0},
                ],
            }
        ],
        "inspection_waypoints": [
            {
                "waypoint_id": "wp_1",
                "frame_id": "map",
                "x": 0.5,
                "y": 0.5,
                "yaw": 0.0,
                "room_id": "room_1",
                "label": "room 1 scan",
                "visited": False,
                "purpose": "base_navigation_map_exploration",
                "waypoint_source": "generated_exploration_candidate",
                "coverage_estimate": 1.0,
            }
        ],
        "driveable_ways": [],
        "map_bundle": {
            "environment_id": "source-env",
            "map_id": "source_map",
            "map_version": "base-navigation-map-v1",
        },
    }


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

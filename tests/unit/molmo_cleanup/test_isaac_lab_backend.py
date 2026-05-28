from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.isaac_lab_backend import (
    ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA,
    ISAAC_SEMANTIC_POSE_PROVENANCE,
    ISAAC_SEMANTIC_POSE_STATE_SCHEMA,
    ISAAC_SEMANTIC_POSE_STATE_SOURCE,
    ISAACLAB_ROBOT_VIEW_VARIANT,
    ISAACLAB_SUBPROCESS_BACKEND,
    IsaacLabSubprocessBackend,
)
from scripts.isaac_lab_cleanup import isaac_lab_backend_worker


def test_isaac_lab_backend_reports_missing_runtime(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Isaac Lab Python runtime is missing"):
        IsaacLabSubprocessBackend(
            run_dir=tmp_path,
            python_executable=tmp_path / "missing-python",
        )


def test_isaac_lab_fake_worker_protocol_produces_views_and_semantic_pose(
    tmp_path: Path,
) -> None:
    backend = IsaacLabSubprocessBackend(
        run_dir=tmp_path,
        python_executable=Path(sys.executable),
        runtime_mode="fake",
        include_robot=True,
        generated_mess_count=1,
    )

    assert backend.backend == ISAACLAB_SUBPROCESS_BACKEND
    assert backend.runtime["runtime_mode"] == "fake"
    assert backend.runtime["renderer_mode"] == "fake_isaac_protocol"
    assert backend.runtime["rendering"]["status"] == "fake_protocol"
    assert backend.runtime["rendering"]["real_rendering_proven"] is False
    assert backend.runtime["visual_artifact_provenance"] == "fake_protocol_placeholder_image"
    assert backend.object_index
    assert backend.receptacle_index
    assert backend.scenario_source == "default_cleanup_scenario"
    assert backend.scene_binding_diagnostics["schema"] == "isaac_public_scene_bindings_v1"
    assert backend.scene_binding_diagnostics["status"] == "placeholder_mapping"
    assert backend.scene_binding_diagnostics["source"] == "scenario_fixture"
    assert backend.scene_binding_diagnostics["selected_object_count"] == 1
    assert backend.scene_binding_diagnostics["selected_object_bound_count"] == 1
    assert backend.scene_binding_diagnostics["selected_target_receptacle_count"] == 1
    assert backend.scene_binding_diagnostics["selected_target_receptacle_bound_count"] == 1
    assert backend.scene_binding_diagnostics["private_manifest_exposed_to_agent"] is False
    assert backend.segmentation["status"] == "blocked_capability"
    assert backend.segmentation["agent_facing"] is False
    assert backend.segmentation["no_simulator_label_fallback"] is True
    assert backend.scene_load["status"] == "fake_protocol"
    assert backend.scene_load["usd_stage_loaded"] is False
    assert any(item["area"] == "camera_capture" for item in backend.mapping_gaps)
    assert any(item["status"] == "placeholder_visuals" for item in backend.mapping_gaps)
    assert any(item["area"] == "public_scene_bindings" for item in backend.mapping_gaps)
    scene_index_payload = backend.scene_index_artifact_payload()
    assert scene_index_payload["schema"] == ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA
    assert scene_index_payload["backend"] == ISAACLAB_SUBPROCESS_BACKEND
    assert scene_index_payload["agent_facing"] is False
    assert scene_index_payload["private_manifest_exposed_to_agent"] is False
    assert "private_manifest" not in scene_index_payload
    assert scene_index_payload["scene_load"]["status"] == "fake_protocol"
    assert scene_index_payload["scenario_source"] == "default_cleanup_scenario"
    assert scene_index_payload["generated_mess_count"] == 1
    assert scene_index_payload["object_index_count"] == len(scene_index_payload["object_index"])
    assert scene_index_payload["receptacle_index_count"] == len(
        scene_index_payload["receptacle_index"]
    )

    snapshot_path = tmp_path / "snapshot.png"
    backend.write_snapshot(snapshot_path, title="Fake Isaac snapshot")
    assert snapshot_path.is_file()
    assert snapshot_path.stat().st_size > 0
    assert backend.snapshot_artifacts[-1]["placeholder_visuals"] is True
    assert (
        backend.snapshot_artifacts[-1]["snapshot_provenance"]["source"]
        == "placeholder_protocol_image"
    )

    views = backend.write_robot_views(
        tmp_path / "robot_views",
        label="0001_pick",
        focus_object_id=backend.scenario.objects[0].object_id,
        focus_receptacle_id=backend.scenario.receptacles[0].receptacle_id,
    )
    assert views["ok"] is True
    assert views["view_variant"] == ISAACLAB_ROBOT_VIEW_VARIANT
    assert set(views["views"]) == {"fpv", "chase", "map", "verify"}
    for path in views["views"].values():
        assert Path(path).is_file()

    object_id = backend.scenario.objects[0].object_id
    receptacle_id = backend.scenario.private_manifest.targets[0].valid_receptacle_ids[0]
    nav = backend.navigate_to_object(object_id)
    pick = backend.pick(object_id)
    target = backend.navigate_to_receptacle(receptacle_id)
    place = backend.place(receptacle_id)
    done = backend.done("fake protocol test complete")

    for response in (nav, pick, target, place):
        assert response["ok"] is True
        assert response["primitive_provenance"] == ISAAC_SEMANTIC_POSE_PROVENANCE
        assert response["planner_backed"] is False
        assert response["physical_robot"] is False
        assert response["semantic_pose_event"]["rendered_to_usd"] is False
        assert response["semantic_pose_event"]["state_source"] == ISAAC_SEMANTIC_POSE_STATE_SOURCE
    assert done["final_locations"][object_id] == receptacle_id
    semantic_pose_state = backend.semantic_pose_state
    assert semantic_pose_state["schema"] == ISAAC_SEMANTIC_POSE_STATE_SCHEMA
    assert semantic_pose_state["primitive_provenance"] == ISAAC_SEMANTIC_POSE_PROVENANCE
    assert semantic_pose_state["rendered_to_usd"] is False
    assert semantic_pose_state["planner_backed"] is False
    assert semantic_pose_state["physical_robot"] is False
    assert semantic_pose_state["object_poses"][object_id]["location_id"] == receptacle_id
    assert semantic_pose_state["object_poses"][object_id]["rendered_to_usd"] is False
    assert [event["tool"] for event in semantic_pose_state["transform_events"]] == [
        "navigate_to_object",
        "pick",
        "navigate_to_receptacle",
        "place",
    ]


def test_isaac_lab_backend_can_request_segmentation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_init_args: list[str] = []
    original_run_worker = IsaacLabSubprocessBackend._run_worker

    def wrapped_run_worker(
        self: IsaacLabSubprocessBackend,
        command: str,
        *args: str,
    ) -> dict[str, object]:
        if command == "init":
            captured_init_args.extend(args)
        return original_run_worker(self, command, *args)

    monkeypatch.setattr(IsaacLabSubprocessBackend, "_run_worker", wrapped_run_worker)

    IsaacLabSubprocessBackend(
        run_dir=tmp_path,
        python_executable=Path(sys.executable),
        runtime_mode="fake",
        enable_segmentation=True,
        segmentation_data_types=("instance_id_segmentation_fast",),
    )

    assert "--enable-segmentation" in captured_init_args
    assert captured_init_args[-2:] == [
        "--segmentation-data-type",
        "instance_id_segmentation_fast",
    ]


def test_isaac_lab_fake_worker_can_align_to_nav2_map_bundle(tmp_path: Path) -> None:
    map_bundle = Path("assets/maps/molmospaces-procthor-val-0-7")
    backend = IsaacLabSubprocessBackend(
        run_dir=tmp_path,
        python_executable=Path(sys.executable),
        runtime_mode="fake",
        include_robot=True,
        generated_mess_count=1,
        map_bundle_dir=map_bundle,
    )

    object_id = backend.scenario.objects[0].object_id
    target_id = backend.scenario.private_manifest.targets[0].valid_receptacle_ids[0]

    assert backend.generated_mess_count == 1
    assert target_id in {item.receptacle_id for item in backend.scenario.receptacles}
    assert backend.navigate_to_object(object_id)["ok"] is True
    assert backend.pick(object_id)["ok"] is True
    assert backend.navigate_to_receptacle(target_id)["ok"] is True
    assert backend.place(target_id)["ok"] is True
    assert backend.done("map aligned fake protocol")["cleanup_status"] == "success"


def test_isaac_usd_index_path_heuristics_skip_container_prims() -> None:
    assert isaac_lab_backend_worker._is_object_prim_path("/World/Objects") is False
    assert isaac_lab_backend_worker._is_object_prim_path("/World/Objects/mug_01") is True
    assert isaac_lab_backend_worker._is_receptacle_prim_path("/World/Receptacles") is False
    assert isaac_lab_backend_worker._is_receptacle_prim_path("/World/Receptacles/sink_01") is True


def test_isaac_molmospaces_scene_metadata_indexes_real_geometry_prims(
    tmp_path: Path,
) -> None:
    scene_dir = tmp_path / "val_0"
    scene_dir.mkdir()
    scene_usd = scene_dir / "scene.usda"
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")
    (scene_dir / "scene_metadata.json").write_text(
        json.dumps(
            {
                "objects": {
                    "mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7": {
                        "hash_name": "mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7",
                        "asset_id": "Mug_1",
                        "object_id": "Mug|surface|7|71",
                        "category": "Mug",
                        "is_static": False,
                        "parent": "desk_767b7ce268898119aaeb97804ba52bdd_1_0_7",
                        "children": [],
                    },
                    "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5": {
                        "hash_name": "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5",
                        "asset_id": "Sink_1",
                        "object_id": "Sink|5|1|0",
                        "category": "Sink",
                        "is_static": True,
                        "children": [],
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    object_index: dict[str, dict[str, object]] = {}
    receptacle_index: dict[str, dict[str, object]] = {}

    isaac_lab_backend_worker._merge_molmospaces_metadata_index(
        usd_path=scene_usd,
        prim_paths_by_name={
            "mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7": [
                "/val_0/Geometry/mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7"
            ],
            "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5": [
                "/val_0/Geometry/sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5"
            ],
        },
        object_index=object_index,
        receptacle_index=receptacle_index,
    )

    mug = object_index["mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7"]
    sink = receptacle_index["sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5"]
    assert mug["usd_prim_path"] == "/val_0/Geometry/mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7"
    assert mug["category"] == "Mug"
    assert mug["index_source"] == "usd_stage_traversal"
    assert mug["metadata_source"] == "molmospaces_scene_metadata"
    assert sink["usd_prim_path"] == "/val_0/Geometry/sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5"
    assert sink["category"] == "Sink"
    assert sink["kind"] == "receptacle"


def test_isaac_molmospaces_metadata_prefers_top_level_geometry_prim() -> None:
    assert (
        isaac_lab_backend_worker._molmospaces_metadata_prim_path(
            "mug_01",
            {
                "mug_01": [
                    "/val_0/A/mug_01",
                    "/val_0/Geometry/mug_01",
                    "/val_0/Geometry/mug_01/mesh",
                ]
            },
        )
        == "/val_0/Geometry/mug_01"
    )


def test_isaac_scene_binding_can_match_synthetic_handle_to_real_usd_metadata() -> None:
    object_index = {
        "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6": {
            "usd_prim_path": "/val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6",
            "category": "Mug",
            "public_label": "Mug Mug|surface|6|56 RoboTHOR_mug_ai2_2_v",
            "index_source": "usd_stage_traversal",
            "metadata_handle": "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6",
        },
        "mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7": {
            "usd_prim_path": "/val_0/Geometry/mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7",
            "category": "Mug",
            "public_label": "Mug Mug|surface|7|71 Mug_1",
            "index_source": "usd_stage_traversal",
            "metadata_handle": "mug_8caf1bb3f88e9a00e02dfe9e6518aeb0_1_0_7",
        },
    }

    binding = isaac_lab_backend_worker._bind_public_scene_item(
        public_id="mug_01",
        public_label="ceramic mug",
        category="dish",
        index=object_index,
        kind="object",
    )

    assert binding["status"] == "bound"
    assert binding["usd_handle"] == "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6"
    assert binding["usd_prim_path"] == (
        "/val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6"
    )
    assert binding["match_strategy"] == "public_id_prefix_first"
    assert binding["index_source"] == "usd_stage_traversal"

    state = {
        "scene_binding_diagnostics": {"selected_object_bindings": {"mug_01": binding}},
        "object_index": object_index,
    }
    assert isaac_lab_backend_worker._object_usd_prim_path(state, "mug_01") == (
        "/val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6"
    )


def test_isaac_scene_binding_does_not_bind_generic_dish_to_unrelated_category() -> None:
    object_index = {
        "sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3": {
            "usd_prim_path": "/val_1/Geometry/sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3",
            "category": "DishSponge",
            "public_label": "DishSponge DishSponge|surface|3|17 Dish_Sponge_1",
            "index_source": "usd_stage_traversal",
            "metadata_handle": "sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3",
        }
    }

    binding = isaac_lab_backend_worker._bind_public_scene_item(
        public_id="mug_01",
        public_label="ceramic mug",
        category="dish",
        index=object_index,
        kind="object",
    )

    assert binding["status"] == "unresolved"
    assert binding["match_strategy"] == "none"
    assert binding["usd_prim_path"] == ""


def test_isaac_scene_binding_still_allows_specific_unique_category() -> None:
    object_index = {
        "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6": {
            "usd_prim_path": "/val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6",
            "category": "Mug",
            "public_label": "Mug Mug|surface|6|56 RoboTHOR_mug_ai2_2_v",
            "index_source": "usd_stage_traversal",
            "metadata_handle": "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6",
        }
    }

    binding = isaac_lab_backend_worker._bind_public_scene_item(
        public_id="cleanup_object_01",
        public_label="unlabeled cleanup object",
        category="Mug",
        index=object_index,
        kind="object",
    )

    assert binding["status"] == "bound"
    assert binding["usd_handle"] == "mug_3ebc45568ed53a18c8797978b3744a99_1_0_6"
    assert binding["match_strategy"] in {"semantic_category_token_unique", "unique_category"}


def test_isaac_scene_index_can_generate_scene_specific_cleanup_scenario() -> None:
    object_index = {
        "baseballbat_37665ef33aee57e330674e8ff865507e_1_0_2": {
            "asset_id": "BaseballBat_2",
            "category": "BaseballBat",
            "index_source": "usd_stage_traversal",
            "is_static": False,
            "kind": "object",
            "metadata_handle": "baseballbat_37665ef33aee57e330674e8ff865507e_1_0_2",
            "metadata_object_id": "BaseballBat|surface|2|10",
            "parent": "bed_258d27d5fe50e324961c7a8698ace951_1_0_2",
            "public_label": "BaseballBat BaseballBat|surface|2|10 BaseballBat_2",
            "usd_prim_path": "/val_1/Geometry/baseballbat_37665ef33aee57e330674e8ff865507e_1_0_2",
        },
        "bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2": {
            "asset_id": "Bowl_12",
            "category": "Bowl",
            "index_source": "usd_stage_traversal",
            "is_static": False,
            "kind": "object",
            "metadata_handle": "bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
            "metadata_object_id": "Bowl|surface|2|4",
            "parent": "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
            "public_label": "Bowl Bowl|surface|2|4 Bowl_12",
            "usd_prim_path": "/val_1/Geometry/bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2",
        },
        "sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3": {
            "asset_id": "Dish_Sponge_1",
            "category": "DishSponge",
            "index_source": "usd_stage_traversal",
            "is_static": False,
            "kind": "object",
            "metadata_handle": "sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3",
            "metadata_object_id": "DishSponge|surface|3|17",
            "parent": "crapper_cd6fa77f725b7ec4a4ced5913731ae93_1_0_3",
            "public_label": "DishSponge DishSponge|surface|3|17 Dish_Sponge_1",
            "usd_prim_path": "/val_1/Geometry/sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3",
        },
    }
    receptacle_index = {
        "ashcan_a20a3404d9e4ddd7e8d84c88e9975333_1_0_3": {
            "asset_id": "bin_16",
            "category": "GarbageCan",
            "index_source": "usd_stage_traversal",
            "kind": "receptacle",
            "metadata_handle": "ashcan_a20a3404d9e4ddd7e8d84c88e9975333_1_0_3",
            "public_label": "GarbageCan GarbageCan|3|2 bin_16",
            "usd_prim_path": "/val_1/Geometry/ashcan_a20a3404d9e4ddd7e8d84c88e9975333_1_0_3",
        },
        "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2": {
            "asset_id": "Dining_Table_203_1",
            "category": "DiningTable",
            "index_source": "usd_stage_traversal",
            "kind": "receptacle",
            "metadata_handle": "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
            "public_label": "DiningTable DiningTable|2|1|0 Dining_Table_203_1",
            "usd_prim_path": "/val_1/Geometry/diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2",
        },
        "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3": {
            "asset_id": "Sink_1",
            "category": "Sink",
            "index_source": "usd_stage_traversal",
            "kind": "receptacle",
            "metadata_handle": "sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",
            "public_label": "Sink Sink|3|1|0 Sink_1",
            "usd_prim_path": "/val_1/Geometry/sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",
        },
    }

    scenario = isaac_lab_backend_worker._scenario_from_scene_index(
        scene_source="procthor-10k-val",
        scene_index=1,
        seed=7,
        generated_mess_count=1,
        object_index=object_index,
        receptacle_index=receptacle_index,
    )

    assert scenario is not None
    assert scenario.scenario_id == "isaac-scene-index-procthor-10k-val-1-7-1"
    assert scenario.objects[0].object_id == "bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2"
    assert scenario.objects[0].location_id == "diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2"
    target = scenario.private_manifest.targets[0]
    assert target.object_id == "bowl_847a24bfa9d8b1a1f26661ebbb850f56_1_0_2"
    assert target.valid_receptacle_ids == ("sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3",)
    bindings = isaac_lab_backend_worker._scene_binding_diagnostics(
        runtime_mode="real",
        scenario=scenario,
        object_index=object_index,
        receptacle_index=receptacle_index,
        real_smoke={},
    )
    assert bindings["status"] == "selected_bound"
    assert bindings["selected_object_bound_count"] == 1
    assert bindings["selected_target_receptacle_bound_count"] == 1


def test_isaac_worker_infers_scene_index_from_local_val_path() -> None:
    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            "state.json",
            "init",
            "--run-dir",
            "run",
            "--scene-index",
            "0",
            "--scene-usd-path",
            "output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_12/scene.usda",
        ]
    )

    assert isaac_lab_backend_worker._effective_scene_index(args) == 12


def test_isaac_lab_real_init_uses_phase_a_smoke_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
    robot_view_images = _write_robot_view_images(run_dir)
    scene_usd = run_dir / "roboclaws_phase_a_smoke_scene.usda"
    _write_nonblank_image(image_path)
    scene_usd.parent.mkdir(parents=True, exist_ok=True)
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")

    def fake_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del scenario
        assert getattr(args, "runtime_mode") == "real"
        assert getattr(args, "scene_usd_path") == scene_usd
        return {
            "image_path": str(image_path),
            "scene_usd": str(scene_usd),
            "loaded_asset_kind": "local_scene_usd",
            "requested_scene_source": "procthor-10k-val",
            "requested_scene_index": 0,
            "requested_molmospaces_scene_usd": "molmospaces://procthor-10k-val/scene-0.usd",
            "isaac_lab_version": "unit-isaaclab",
            "isaac_sim_version": "unit-isaacsim",
            "renderer_mode": "isaac_lab_headless_rtx",
            "capture_method": "isaac_lab_camera_rgb",
            "robot_view_capture_method": "isaac_lab_camera_rgb_static_robot_views",
            "robot_view_images": robot_view_images,
            "camera_resolution": [540, 360],
            "stage_prim_count": 6,
            "render_steps": 3,
            "scene_index_diagnostics": {
                "schema": "isaac_usd_scene_index_v1",
                "status": "indexed",
                "source": str(scene_usd),
                "stage_prim_count": 6,
                "object_candidate_count": 1,
                "receptacle_candidate_count": 1,
                "blockers": [],
            },
            "object_index": {
                "mug_01": {
                    "usd_prim_path": "/World/Objects/mug_01",
                    "category": "mug01",
                    "public_label": "mug_01",
                    "index_source": "usd_stage_traversal",
                }
            },
            "receptacle_index": {
                "sink_01": {
                    "usd_prim_path": "/World/Receptacles/sink_01",
                    "category": "sink01",
                    "public_label": "sink_01",
                    "index_source": "usd_stage_traversal",
                    "support_pose": {"frame": "world", "x": 0.0, "y": 0.0, "z": 0.0},
                }
            },
            "segmentation": {
                "schema": "isaac_segmentation_diagnostics_v1",
                "source": "isaac_lab_camera",
                "capture_method": "isaac_lab_camera_segmentation",
                "requested_data_types": [
                    "semantic_segmentation",
                    "instance_segmentation_fast",
                    "instance_id_segmentation_fast",
                ],
                "output_data_types": ["instance_id_segmentation_fast"],
                "tensor_output_available": True,
                "candidate_bbox_count": 1,
                "candidate_bboxes": [
                    {
                        "view": "fpv",
                        "data_type": "instance_id_segmentation_fast",
                        "label_id": 3,
                        "label": "/World/Objects/mug_01",
                        "usd_prim_path": "/World/Objects/mug_01",
                        "bbox_xyxy": [8, 8, 32, 36],
                        "pixel_count": 144,
                        "image_size": [540, 360],
                    }
                ],
                "no_simulator_label_fallback": True,
            },
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fake_real_runtime_smoke,
    )

    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "init",
            "--run-dir",
            str(run_dir),
            "--runtime-mode",
            "real",
            "--generated-mess-count",
            "1",
            "--scene-usd-path",
            str(scene_usd),
        ]
    )
    result = isaac_lab_backend_worker.init_state(args)

    assert result["ok"] is True
    assert result["runtime"]["runtime_mode"] == "real"
    assert result["runtime"]["rendering"]["status"] == "real_rendering_proven"
    assert result["runtime"]["rendering"]["real_rendering_proven"] is True
    assert result["runtime"]["rendering"]["placeholder_visuals"] is False
    assert result["runtime"]["visual_artifact_provenance"] == "isaac_lab_camera_rgb"
    assert result["scene_usd"] == str(scene_usd)
    assert result["scene_load"]["status"] == "loaded"
    assert result["scene_load"]["usd_stage_loaded"] is True
    assert result["scene_load"]["loaded_asset_kind"] == "local_scene_usd"
    assert result["artifacts"]["runtime_smoke_image"] == str(image_path)
    assert result["artifacts"]["robot_view_images"] == robot_view_images
    assert result["scene_index_diagnostics"]["status"] == "indexed"
    assert result["scene_index_diagnostics"]["object_candidate_count"] == 1
    assert result["object_index"]["mug_01"]["usd_prim_path"] == "/World/Objects/mug_01"
    assert result["receptacle_index"]["sink_01"]["usd_prim_path"] == ("/World/Receptacles/sink_01")
    assert any(
        item["area"] == "camera_capture" and item["status"] == "real_rendering_proven"
        for item in result["mapping_gaps"]
    )
    assert any(
        item["area"] == "local_usd_scene_loading" and item["status"] == "loaded"
        for item in result["mapping_gaps"]
    )
    assert any(
        item["area"] == "robot_view_variants" and item["status"] == "real_rendering_proven"
        for item in result["mapping_gaps"]
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["runtime"]["rendering"]["status"] == "real_rendering_proven"
    assert state["scene_load"]["usd_stage_loaded"] is True
    assert state["real_runtime_smoke"]["scene_usd"] == str(scene_usd)
    assert state["robot_view_images"] == robot_view_images
    assert state["scene_index_diagnostics"]["status"] == "indexed"
    assert state["scene_binding_diagnostics"]["status"] == "selected_bound"
    assert state["scene_binding_diagnostics"]["selected_object_bound_count"] == 1
    assert state["scene_binding_diagnostics"]["selected_target_receptacle_bound_count"] == 1
    assert state["segmentation"]["status"] == "available"
    assert state["segmentation"]["candidate_bbox_count"] == 1
    assert state["segmentation"]["selected_usd_prim_match_count"] == 1
    assert state["segmentation"]["agent_facing"] is False
    assert state["segmentation"]["no_simulator_label_fallback"] is True


def test_isaac_lab_segmentation_capture_extracts_selected_bbox() -> None:
    import numpy as np

    class CameraData:
        output = {
            "instance_id_segmentation_fast": np.array(
                [
                    [[0], [0], [0], [0]],
                    [[0], [3], [3], [0]],
                    [[0], [3], [3], [0]],
                    [[0], [0], [0], [0]],
                ]
            )
        }
        info = {
            "instance_id_segmentation_fast": {
                "idToLabels": {3: "/World/Objects/mug_01"},
            }
        }

    class Camera:
        data = CameraData()

    view = isaac_lab_backend_worker._camera_segmentation_view_diagnostics(
        Camera(),
        data_types=("instance_id_segmentation_fast",),
        view_name="fpv",
        np=np,
    )
    capture = isaac_lab_backend_worker._camera_segmentation_capture_diagnostics(
        [view],
        requested_data_types=("instance_id_segmentation_fast",),
    )
    diagnostics = isaac_lab_backend_worker.segmentation_diagnostics(
        "real",
        real_smoke={"segmentation": capture},
        scene_binding_diagnostics={
            "selected_object_bindings": {
                "mug_01": {
                    "status": "bound",
                    "usd_prim_path": "/World/Objects/mug_01",
                }
            },
            "selected_target_receptacle_bindings": {},
        },
    )

    assert capture["output_data_types"] == ["instance_id_segmentation_fast"]
    assert capture["requested_data_types"] == ["instance_id_segmentation_fast"]
    assert capture["candidate_bbox_count"] == 1
    assert diagnostics["status"] == "available"
    assert diagnostics["candidate_bbox_count"] == 1
    assert diagnostics["selected_usd_prim_match_count"] == 1
    assert diagnostics["selected_candidate_bboxes"][0]["bbox_xyxy"] == [1, 1, 3, 3]
    assert diagnostics["agent_facing"] is False
    assert diagnostics["no_simulator_label_fallback"] is True


def test_isaac_lab_segmentation_capture_accepts_list_info_shape() -> None:
    import numpy as np

    class CameraData:
        output = {
            "semantic_segmentation": np.array(
                [
                    [[0], [0], [0], [0]],
                    [[0], [5], [5], [0]],
                    [[0], [5], [5], [0]],
                    [[0], [0], [0], [0]],
                ]
            )
        }
        info = [
            {
                "semantic_segmentation": {
                    "idToLabels": {"5": {"usd_prim_path": "/World/Objects/bowl_01"}},
                }
            }
        ]

    class Camera:
        data = CameraData()

    view = isaac_lab_backend_worker._camera_segmentation_view_diagnostics(
        Camera(),
        data_types=("semantic_segmentation",),
        view_name="fpv",
        np=np,
    )
    capture = isaac_lab_backend_worker._camera_segmentation_capture_diagnostics(
        [view],
        requested_data_types=("semantic_segmentation",),
    )

    assert capture["output_data_types"] == ["semantic_segmentation"]
    assert capture["candidate_bbox_count"] == 1
    assert capture["candidate_bboxes"][0]["label"] == "/World/Objects/bowl_01"
    assert capture["candidate_bboxes"][0]["bbox_xyxy"] == [1, 1, 3, 3]


def test_isaac_lab_generated_count_selects_private_targets_not_first_object(
    tmp_path: Path,
) -> None:
    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(tmp_path / "state.json"),
            "init",
            "--run-dir",
            str(tmp_path / "run"),
            "--runtime-mode",
            "fake",
            "--generated-mess-count",
            "1",
        ]
    )
    result = isaac_lab_backend_worker.init_state(args)

    object_ids = [item["object_id"] for item in result["scenario"]["objects"]]
    target_ids = [item["object_id"] for item in result["private_manifest"]["targets"]]

    assert object_ids == ["mug_01"]
    assert target_ids == ["mug_01"]
    assert object_ids != ["toy_car_01"]
    assert result["scene_binding_diagnostics"]["selected_object_count"] == 1
    assert result["scene_binding_diagnostics"]["selected_target_receptacle_count"] == 1


def test_isaac_lab_real_worker_views_reuse_real_smoke_images(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
    robot_view_images = _write_robot_view_images(run_dir)
    _write_nonblank_image(image_path)

    def fake_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
        return {
            "image_path": str(image_path),
            "scene_usd": str(run_dir / "scene.usda"),
            "loaded_asset_kind": "generated_runtime_smoke_usd",
            "requested_scene_source": "procthor-10k-val",
            "requested_scene_index": 0,
            "requested_molmospaces_scene_usd": "molmospaces://procthor-10k-val/scene-0.usd",
            "isaac_lab_version": "unit-isaaclab",
            "isaac_sim_version": "unit-isaacsim",
            "renderer_mode": "isaac_lab_headless_rtx",
            "capture_method": "isaac_lab_camera_rgb",
            "robot_view_capture_method": "isaac_lab_camera_rgb_static_robot_views",
            "robot_view_images": robot_view_images,
            "camera_resolution": [540, 360],
            "stage_prim_count": 6,
            "render_steps": 4,
            "scene_index_diagnostics": {
                "schema": "isaac_usd_scene_index_v1",
                "status": "indexed",
                "source": str(run_dir / "scene.usda"),
                "stage_prim_count": 6,
                "object_candidate_count": 1,
                "receptacle_candidate_count": 1,
                "blockers": [],
            },
            "object_index": {"mug_01": {"usd_prim_path": "/World/Objects/mug_01"}},
            "receptacle_index": {"sink_01": {"usd_prim_path": "/World/Receptacles/sink_01"}},
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fake_real_runtime_smoke,
    )
    init_args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "init",
            "--run-dir",
            str(run_dir),
            "--runtime-mode",
            "real",
            "--include-robot",
        ]
    )
    isaac_lab_backend_worker.init_state(init_args)
    view_args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "robot_views",
            "--output-dir",
            str(run_dir / "robot_views"),
            "--label",
            "runtime smoke",
            "--render-width",
            "64",
            "--render-height",
            "48",
        ]
    )
    result = isaac_lab_backend_worker.write_robot_views(
        view_args,
        isaac_lab_backend_worker.read_state(state_path),
    )

    assert result["ok"] is True
    assert result["view_variant"] == ISAACLAB_ROBOT_VIEW_VARIANT
    assert "placeholder" not in json.dumps(result["view_provenance"])
    assert set(result["views"]) == {"fpv", "chase", "map", "verify"}
    assert result["shapes"]["fpv"] == [48, 64, 3]
    for path in result["views"].values():
        assert Path(path).is_file()


def test_isaac_lab_real_worker_snapshot_reuses_real_smoke_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
    _write_nonblank_image(image_path)

    def fake_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
        return {
            "image_path": str(image_path),
            "scene_usd": str(run_dir / "scene.usda"),
            "loaded_asset_kind": "generated_runtime_smoke_usd",
            "requested_scene_source": "procthor-10k-val",
            "requested_scene_index": 0,
            "requested_molmospaces_scene_usd": "molmospaces://procthor-10k-val/scene-0.usd",
            "isaac_lab_version": "unit-isaaclab",
            "isaac_sim_version": "unit-isaacsim",
            "renderer_mode": "isaac_lab_headless_rtx",
            "capture_method": "isaac_lab_camera_rgb",
            "camera_resolution": [540, 360],
            "stage_prim_count": 6,
            "render_steps": 4,
            "scene_index_diagnostics": {
                "schema": "isaac_usd_scene_index_v1",
                "status": "indexed",
                "source": str(run_dir / "scene.usda"),
                "stage_prim_count": 6,
                "object_candidate_count": 1,
                "receptacle_candidate_count": 1,
                "blockers": [],
            },
            "object_index": {"mug_01": {"usd_prim_path": "/World/Objects/mug_01"}},
            "receptacle_index": {"sink_01": {"usd_prim_path": "/World/Receptacles/sink_01"}},
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fake_real_runtime_smoke,
    )
    init_args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "init",
            "--run-dir",
            str(run_dir),
            "--runtime-mode",
            "real",
        ]
    )
    isaac_lab_backend_worker.init_state(init_args)
    snapshot_path = run_dir / "before.png"
    snapshot_args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "snapshot",
            "--output-path",
            str(snapshot_path),
            "--title",
            "Before cleanup",
            "--render-width",
            "64",
            "--render-height",
            "48",
        ]
    )
    result = isaac_lab_backend_worker.write_snapshot(
        snapshot_args,
        isaac_lab_backend_worker.read_state(state_path),
    )

    assert result["ok"] is True
    assert result["placeholder_visuals"] is False
    assert result["visual_artifact_provenance"] == "isaac_lab_camera_rgb"
    assert result["snapshot_provenance"]["source_path"] == str(image_path)
    assert result["snapshot_provenance"]["static_isaac_capture"] is True
    assert result["snapshot_provenance"]["semantic_pose_rendered"] is False
    with Image.open(snapshot_path) as image:
        assert image.size == (64, 48)


def test_isaac_lab_real_init_fails_without_renderer_proof(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"

    def fail_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
        raise RuntimeError("camera capture failed")

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fail_real_runtime_smoke,
    )
    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "init",
            "--run-dir",
            str(tmp_path / "run"),
            "--runtime-mode",
            "real",
        ]
    )

    with pytest.raises(RuntimeError, match="Real Isaac runtime smoke failed"):
        isaac_lab_backend_worker.init_state(args)
    assert state_path.exists() is False


def test_isaac_lab_real_init_does_not_persist_missing_smoke_image(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    missing_image = tmp_path / "run" / "missing.png"

    def missing_image_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
        return {
            "image_path": str(missing_image),
            "scene_usd": str(tmp_path / "run" / "scene.usda"),
            "loaded_asset_kind": "generated_runtime_smoke_usd",
            "requested_scene_source": "procthor-10k-val",
            "requested_scene_index": 0,
            "renderer_mode": "isaac_lab_headless_rtx",
            "capture_method": "isaac_lab_camera_rgb",
            "camera_resolution": [540, 360],
            "stage_prim_count": 6,
            "render_steps": 3,
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        missing_image_real_runtime_smoke,
    )
    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "init",
            "--run-dir",
            str(tmp_path / "run"),
            "--runtime-mode",
            "real",
        ]
    )

    with pytest.raises(RuntimeError, match="real Isaac smoke image is missing"):
        isaac_lab_backend_worker.init_state(args)
    assert state_path.exists() is False


def _write_nonblank_image(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (64, 48), color=(18, 32, 48))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 40), outline=(240, 180, 60), width=3)
    image.save(path)


def _write_robot_view_images(run_dir: Path) -> dict[str, str]:
    paths = {
        "fpv": run_dir / "isaac_runtime_smoke.png",
        "chase": run_dir / "isaac_runtime_smoke.chase.png",
        "map": run_dir / "isaac_runtime_smoke.map.png",
        "verify": run_dir / "isaac_runtime_smoke.verify.png",
    }
    for index, path in enumerate(paths.values(), start=1):
        path.parent.mkdir(parents=True, exist_ok=True)
        image = Image.new("RGB", (64, 48), color=(18 + index, 32, 48))
        draw = ImageDraw.Draw(image)
        draw.rectangle((8, 8, 56, 40), outline=(240, 180 - index, 60), width=3)
        image.save(path)
    return {key: str(path) for key, path in paths.items()}

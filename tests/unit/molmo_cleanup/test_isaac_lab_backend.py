from __future__ import annotations

import json
import math
import sys
import types
from pathlib import Path
from types import SimpleNamespace

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


def test_isaac_lab_backend_can_request_segmentation_semantic_filter(
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
        segmentation_data_types=("semantic_segmentation",),
        segmentation_semantic_filter=("usd_prim_path",),
    )

    assert "--enable-segmentation" in captured_init_args
    assert [
        "--segmentation-data-type",
        "semantic_segmentation",
        "--segmentation-semantic-filter",
        "usd_prim_path",
    ] == captured_init_args[-4:]


def test_isaac_worker_can_request_semantic_filter_override(tmp_path: Path) -> None:
    args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(tmp_path / "state.json"),
            "init",
            "--run-dir",
            str(tmp_path),
            "--runtime-mode",
            "fake",
            "--enable-segmentation",
            "--segmentation-semantic-filter",
            "usd_prim_path",
        ]
    )

    assert getattr(args, "segmentation_semantic_filter") == ["usd_prim_path"]


def test_isaac_worker_hard_exits_after_deferred_app_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_codes: list[int] = []

    def fake_exit(code: int) -> None:
        exit_codes.append(code)
        raise SystemExit(code)

    class BlockingClose:
        def close(self, **_: object) -> None:  # pragma: no cover - should not be called.
            raise AssertionError("deferred SimulationApp close should not run on success")

    monkeypatch.setattr(isaac_lab_backend_worker.os, "_exit", fake_exit)
    isaac_lab_backend_worker._DEFERRED_SIMULATION_APP = BlockingClose()

    with pytest.raises(SystemExit) as exc:
        isaac_lab_backend_worker._finish_command({"ok": True, "tool": "robot_views"})

    assert exc.value.code == 0
    assert exit_codes == [0]
    assert '"tool": "robot_views"' in capsys.readouterr().out
    assert isaac_lab_backend_worker._DEFERRED_SIMULATION_APP is not None
    isaac_lab_backend_worker._DEFERRED_SIMULATION_APP = None


def test_isaac_lab_backend_exposes_camera_control_request_api(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    backend = IsaacLabSubprocessBackend.__new__(IsaacLabSubprocessBackend)
    backend.state_path = tmp_path / "state.json"
    backend.python_executable = tmp_path / "python"
    captured: dict[str, object] = {}

    def fake_run_worker(command: str, *args: str) -> dict[str, object]:
        captured["command"] = command
        captured["args"] = args
        return {"ok": True}

    monkeypatch.setattr(backend, "_run_worker", fake_run_worker)
    request_path = tmp_path / "camera_control_request.json"
    request_path.write_text(
        json.dumps({"render_resolution": {"width": 960, "height": 640}, "views": []}),
        encoding="utf-8",
    )

    result = backend.render_camera_control_request(
        tmp_path / "camera_views",
        request_path=request_path,
    )

    assert result["ok"] is True
    assert captured["command"] == "camera_views"
    assert captured["args"] == (
        "--output-dir",
        str(tmp_path / "camera_views"),
        "--camera-request-path",
        str(request_path),
        "--render-width",
        "960",
        "--render-height",
        "640",
    )


def test_isaac_scene_camera_spec_uses_camera_control_orbit() -> None:
    spec = isaac_lab_backend_worker._isaac_scene_camera_view_spec(
        {
            "view_id": "view 01/table",
            "target": [2.7, 5.9, 1.0],
            "camera_orbit": {"distance_m": 4.4, "azimuth_deg": 225.0, "elevation_deg": 28.0},
            "lane_camera_orbits": {
                "isaaclab-prepared-usd": {
                    "distance_m": 4.4,
                    "azimuth_deg": 270.0,
                    "elevation_deg": 28.0,
                }
            },
            "camera_model": "anchor_orbit_lookat_camera_v1",
            "calibration_status": "anchor_orbit_relative_calibrated_v1",
            "lens": {"focal_length_mm": 24.0},
        },
        index=1,
    )

    assert spec["view_id"] == "view_01_table"
    assert spec["target"] == pytest.approx([2.7, 5.9, 1.0])
    assert spec["camera_model"] == "anchor_orbit_lookat_camera_v1"
    assert spec["calibration_status"] == "anchor_orbit_relative_calibrated_v1"
    assert spec["eye"][2] > spec["target"][2]
    assert spec["camera_orbit"]["azimuth_deg"] == 270.0
    assert spec["lens"] == {"focal_length_mm": 24.0}


def test_isaac_scene_camera_spec_honors_canonical_explicit_pose() -> None:
    spec = isaac_lab_backend_worker._isaac_scene_camera_view_spec(
        {
            "view_id": "view 01/table",
            "camera_model": "canonical_eye_target_camera_v1",
            "coordinate_frame": "molmospaces_scene_frame_v1",
            "robot_view_role": "fpv",
            "camera_basis": "robot_pose_eye_target",
            "camera_mode": "canonical_robot_fpv",
            "eye": [1.0, 2.0, 3.0],
            "target": [2.7, 5.9, 1.0],
            "usd_prim_path": "/val_1/Geometry/table_01",
            "backend_transforms": {
                "isaaclab-prepared-usd": {
                    "xy_scale": 1.0,
                    "rotation_z_deg": 0.0,
                    "translation": [0.0, 0.0, 0.0],
                }
            },
            "calibration_status": "canonical_scene_frame_similarity_fit_v1",
        },
        index=1,
    )

    assert spec["view_id"] == "view_01_table"
    assert spec["target"] == pytest.approx([2.7, 5.9, 1.0])
    assert spec["eye"] == pytest.approx([1.0, 2.0, 3.0])
    assert spec["backend_eye"] == pytest.approx([1.0, 2.0, 3.0])
    assert spec["target_source"] == "canonical_explicit_target"
    assert spec["robot_view_role"] == "fpv"
    assert spec["camera_basis"] == "robot_pose_eye_target"
    assert spec["camera_mode"] == "canonical_robot_fpv"
    assert spec["camera_model"] == "canonical_eye_target_camera_v1"
    assert spec["coordinate_frame"] == "molmospaces_scene_frame_v1"


def test_isaac_camera_lens_derives_horizontal_aperture_from_vertical_fov() -> None:
    aperture = isaac_lab_backend_worker._horizontal_aperture_from_lens(
        {"vertical_fov_deg": 45.0, "horizontal_aperture_mm": 20.955},
        width=960,
        height=640,
        focal_length=24.0,
    )

    assert aperture == pytest.approx(29.82337649)


def test_isaac_scene_camera_capture_applies_color_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import numpy as np

    class _FakeSim:
        device = "cpu"

        def __init__(self) -> None:
            self.steps = 0

        def reset(self) -> None:
            self.steps = 0

        def step(self) -> None:
            self.steps += 1

        def get_physics_dt(self) -> float:
            return 1 / 60

    class _FakeSimUtils:
        @staticmethod
        def create_prim(*_args: object, **_kwargs: object) -> None:
            return None

        class PinholeCameraCfg:
            def __init__(self, **kwargs: object) -> None:
                self.kwargs = kwargs

    class _FakeCameraCfg:
        def __init__(self, **kwargs: object) -> None:
            self.kwargs = kwargs

    class _FakeTensor:
        def __init__(self, array: np.ndarray) -> None:
            self._array = array

        def detach(self) -> "_FakeTensor":
            return self

        def cpu(self) -> "_FakeTensor":
            return self

        def numpy(self) -> np.ndarray:
            return self._array

    class _FakeCamera:
        def __init__(self, cfg: _FakeCameraCfg) -> None:
            self.cfg = cfg
            self.data = SimpleNamespace(output={})

        def set_world_poses_from_view(self, *_args: object, **_kwargs: object) -> None:
            return None

        def update(self, *, dt: float) -> None:
            del dt
            frame = np.full((1, 4, 6, 3), 250, dtype=np.uint8)
            frame[:, 0, 0, :] = 230
            self.data.output["rgb"] = _FakeTensor(frame)

    class _FakeTorch:
        float32 = "float32"

        @staticmethod
        def tensor(value: object, **_kwargs: object) -> object:
            return value

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "_ensure_capture_lighting",
        lambda *_args, **_kwargs: {"status": "unit_lighting_skipped"},
    )

    result = isaac_lab_backend_worker._capture_scene_camera_request_with_existing_sim(
        camera_request={
            "camera_model": "canonical_eye_target_camera_v1",
            "views": [
                {
                    "view_id": "fpv",
                    "eye": [0.0, 0.0, 1.0],
                    "target": [1.0, 0.0, 1.0],
                }
            ],
        },
        output_dir=tmp_path,
        width=6,
        height=4,
        sim=_FakeSim(),
        sim_utils=_FakeSimUtils,
        stage_utils=SimpleNamespace(),
        camera_type=_FakeCamera,
        camera_cfg_type=_FakeCameraCfg,
        torch=_FakeTorch,
        np=np,
        scene_bounds={},
    )

    assert result["color_profile"]["profile_id"] == "display_srgb_soft_highlight_v1"
    assert result["color_management"]["fpv"]["before"]["overexposed_fraction"] > 0.9
    assert result["color_management"]["fpv"]["after"]["overexposed_fraction"] == pytest.approx(0.0)
    assert Path(result["images"]["fpv"]).is_file()


def test_isaac_write_camera_views_returns_color_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_path = tmp_path / "state.json"
    scene_usd = tmp_path / "scene.usda"
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")
    state = {
        "runtime": {"runtime_mode": "real"},
        "scene_usd": str(scene_usd),
        "tool_event_counts": {},
    }
    state_path.write_text(json.dumps(state), encoding="utf-8")
    request_path = tmp_path / "camera_control_request.json"
    request_path.write_text(
        json.dumps(
            {
                "camera_model": "canonical_eye_target_camera_v1",
                "render_resolution": {"width": 6, "height": 4},
                "color_profile": {"profile_id": "display_srgb_soft_highlight_v1"},
                "views": [
                    {
                        "view_id": "fpv",
                        "eye": [0.0, 0.0, 1.0],
                        "target": [1.0, 0.0, 1.0],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    def fake_capture_scene_camera_views(
        *,
        scene_usd: Path,
        camera_request: dict[str, object],
        output_dir: Path,
        width: int,
        height: int,
    ) -> dict[str, object]:
        output_path = output_dir / "fpv.png"
        _write_nonblank_image(output_path)
        return {
            "camera_control_api": "roboclaws.camera_control.render_views",
            "camera_request_schema": camera_request.get("schema"),
            "calibration_status": camera_request.get("calibration_status"),
            "lighting_profile": camera_request.get("lighting_profile"),
            "lighting_diagnostics": {"status": "unit"},
            "color_profile": camera_request.get("color_profile"),
            "color_management": {
                "fpv": {
                    "after": {"overexposed_fraction": 0.0},
                }
            },
            "lens": camera_request.get("lens"),
            "derived_lens": {"horizontal_aperture_mm": 29.8},
            "views": [
                {
                    "view_id": "fpv",
                    "camera_model": "canonical_eye_target_camera_v1",
                    "image_path": str(output_path),
                }
            ],
            "images": {"fpv": str(output_path)},
            "shapes": {"fpv": [height, width, 3]},
            "scene_bounds": {},
            "render_steps": 1,
            "scene_usd": str(scene_usd),
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "capture_scene_camera_views",
        fake_capture_scene_camera_views,
    )

    result = isaac_lab_backend_worker.write_camera_views(
        isaac_lab_backend_worker.parse_args(
            [
                "--state-path",
                str(state_path),
                "camera_views",
                "--output-dir",
                str(tmp_path / "camera_views"),
                "--camera-request-path",
                str(request_path),
            ]
        ),
        isaac_lab_backend_worker.read_state(state_path),
    )

    assert result["ok"] is True
    assert result["color_profile"]["profile_id"] == "display_srgb_soft_highlight_v1"
    assert result["color_management"]["fpv"]["after"]["overexposed_fraction"] == 0.0


def test_isaac_scene_camera_spec_records_usd_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakePrim:
        def IsValid(self) -> bool:
            return True

    class _FakeStage:
        def GetPrimAtPath(self, _path: str) -> _FakePrim:
            return _FakePrim()

    class _StageUtils:
        @staticmethod
        def get_current_stage() -> _FakeStage:
            return _FakeStage()

    class _FakeAlignedBox:
        def GetMin(self) -> list[float]:
            return [2.0, 5.0, 0.3]

        def GetMax(self) -> list[float]:
            return [3.0, 6.0, 1.2]

    class _FakeWorldBound:
        def ComputeAlignedBox(self) -> _FakeAlignedBox:
            return _FakeAlignedBox()

    class _FakeBBoxCache:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def ComputeWorldBound(self, _prim: _FakePrim) -> _FakeWorldBound:
            return _FakeWorldBound()

    fake_pxr = types.SimpleNamespace(
        Usd=types.SimpleNamespace(TimeCode=types.SimpleNamespace(Default=lambda: object())),
        UsdGeom=types.SimpleNamespace(
            BBoxCache=_FakeBBoxCache,
            Tokens=types.SimpleNamespace(default_="default", render="render", proxy="proxy"),
        ),
    )
    monkeypatch.setitem(sys.modules, "pxr", fake_pxr)

    spec = isaac_lab_backend_worker._isaac_scene_camera_view_spec(
        {
            "view_id": "view 01/table",
            "camera_model": "canonical_eye_target_camera_v1",
            "eye": [1.0, 2.0, 3.0],
            "target": [2.7, 5.9, 1.0],
            "usd_prim_path": "/val_1/Geometry/table_01",
        },
        index=1,
        stage_utils=_StageUtils(),
    )

    assert spec["usd_bounds_target"] == pytest.approx([2.5, 5.5, 0.75])
    assert spec["usd_bounds"]["min"] == pytest.approx([2.0, 5.0, 0.3])
    assert spec["usd_bounds"]["max"] == pytest.approx([3.0, 6.0, 1.2])
    assert spec["usd_bounds"]["center"] == pytest.approx([2.5, 5.5, 0.75])


def test_isaac_support_pose_uses_usd_world_bounds_center() -> None:
    support = isaac_lab_backend_worker._support_pose_from_usd_bounds(
        {
            "center": [2.5, 5.5, 0.75],
            "max": [3.0, 6.0, 1.2],
            "size": [1.0, 2.0, 0.9],
        },
        fallback={"frame": "world", "x": 99.0, "y": 99.0, "z": 0.0, "yaw_deg": 45.0},
    )

    assert support is not None
    assert support["frame"] == "usd_world"
    assert support["x"] == pytest.approx(2.5)
    assert support["y"] == pytest.approx(5.5)
    assert support["z"] == pytest.approx(1.2)
    assert support["yaw_deg"] == pytest.approx(45.0)
    assert support["support_radius_m"] == pytest.approx(1.0)
    assert support["source"] == "usd_world_bounds_top_center"


def test_isaac_robot_pose_prefers_bound_receptacle_support_pose() -> None:
    state = {
        "scene_binding_diagnostics": {
            "selected_target_receptacle_bindings": {
                "sink_01": {
                    "status": "bound",
                    "usd_handle": "real_sink",
                    "usd_prim_path": "/val_1/Geometry/real_sink",
                }
            }
        },
        "receptacle_index": {
            "real_sink": {
                "support_pose": {
                    "frame": "usd_world",
                    "x": 2.5,
                    "y": 5.5,
                    "z": 0.75,
                    "source": "usd_world_bounds_top_center",
                    "support_radius_m": 0.8,
                },
                "usd_world_bounds": {"center": [2.5, 5.5, 0.75]},
            }
        },
        "object_index": {
            "bowl_01": {
                "usd_world_bounds": {"center": [4.5, 7.5, 0.9]},
            }
        },
    }

    pose = isaac_lab_backend_worker._robot_pose_for_receptacle(state, "sink_01")

    assert pose["frame"] == "molmospaces_scene_frame_v1"
    assert pose["schema"] == "cleanup_robot_pose_result_v1"
    assert pose["pose_source"] == "roboclaws_shared_scene_frame_support_pose"
    assert pose["pose_request"]["schema"] == "cleanup_robot_pose_request_v1"
    assert pose["pose_request"]["resolver"] == "roboclaws.cleanup_robot_pose.near_target_v1"
    assert pose["support_pose_source"] == "usd_world_bounds_top_center"
    assert pose["target_position"] == pytest.approx([2.5, 5.5, 0.75])
    distance_to_target = math.hypot(pose["x"] - 2.5, pose["y"] - 5.5)
    assert distance_to_target == pytest.approx(1.15)


def test_isaac_usd_scene_index_extracts_room_outlines(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakePrim:
        def __init__(self, path: str, name: str) -> None:
            self._path = path
            self._name = name

        def GetPath(self) -> str:
            return self._path

        def GetName(self) -> str:
            return self._name

    fake_prim = _FakePrim("/val_1/Geometry/room_2_visual_0", "room_2_visual_0")

    class _FakeStage:
        def Traverse(self) -> list[_FakePrim]:
            return [fake_prim]

    class _FakeUsdStage:
        @staticmethod
        def Open(_path: str) -> _FakeStage:
            return _FakeStage()

    class _FakeUsdGeom:
        pass

    monkeypatch.setitem(
        sys.modules,
        "pxr",
        types.SimpleNamespace(Usd=types.SimpleNamespace(Stage=_FakeUsdStage), UsdGeom=_FakeUsdGeom),
    )
    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "_usd_world_bounds",
        lambda _prim, *, usd_geom: {
            "center": [2.99, 4.983, 1.2],
            "size": [5.98, 9.966, 0.2],
        },
    )
    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "_annotate_usd_index_geometry",
        lambda **_kwargs: None,
    )

    diagnostics = isaac_lab_backend_worker._inspect_usd_scene_index(Path("scene.usda"))

    assert diagnostics["room_outline_count"] == 1
    assert diagnostics["room_outlines"][0]["room_id"] == "room_2"
    assert diagnostics["room_outlines"][0]["center"] == pytest.approx([2.99, 4.983])
    assert diagnostics["room_outlines"][0]["half_extents"] == pytest.approx([2.99, 4.983])
    assert diagnostics["room_outlines"][0]["provenance"] == "isaac_usd_room_mesh_world_bounds"


def test_isaac_canonical_robot_view_focus_prefers_object_pose() -> None:
    state = {
        "scene_binding_diagnostics": {
            "selected_object_bindings": {
                "mug_01": {
                    "status": "bound",
                    "usd_handle": "mug_01",
                    "usd_prim_path": "/World/Objects/mug_01",
                }
            }
        },
        "object_index": _unit_isaac_object_index(),
        "receptacle_index": _unit_isaac_receptacle_index(),
    }
    state["semantic_pose_state"] = {
        "object_poses": isaac_lab_backend_worker._semantic_object_poses_from_state(
            {
                **state,
                "scenario": {
                    "objects": [{"object_id": "mug_01", "location_id": "sink_01"}],
                },
                "locations": {"mug_01": "sink_01"},
                "containment": {},
                "current_receptacle_id": "sink_01",
            }
        )
    }

    focus = isaac_lab_backend_worker._canonical_robot_view_focus(
        state,
        {"target_position": [2.5, 5.5, 1.2]},
        focus_object_id="mug_01",
        focus_receptacle_id="sink_01",
    )

    assert focus["source"] == "isaac_semantic_pose_object_pose"
    assert focus["focus_position"] == pytest.approx([4.0, 5.0, 0.4])


def test_isaac_stage_light_paths_detects_existing_lights_without_pxr() -> None:
    class _FakePrim:
        def __init__(self, path: str, is_light: bool, type_name: str = "") -> None:
            self._path = path
            self._is_light = is_light
            self._type_name = type_name

        def IsValid(self) -> bool:
            return True

        def GetPath(self) -> str:
            return self._path

        def IsA(self, _api: object) -> bool:
            return self._is_light

        def GetTypeName(self) -> str:
            return self._type_name

    class _FakeStage:
        def Traverse(self) -> list[_FakePrim]:
            return [
                _FakePrim("/val_1/scene_skybox_light", True),
                _FakePrim("/val_1/scene_dir_light", False, "DistantLight"),
                _FakePrim("/val_1/Geometry/table", False),
            ]

    paths = isaac_lab_backend_worker._stage_light_paths(
        _FakeStage(),
        light_api=object(),
    )

    assert paths == [
        "/val_1/scene_skybox_light",
        "/val_1/scene_dir_light",
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


def test_isaac_worker_infers_scene_index_from_prepared_val_path() -> None:
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
            (
                "output/isaaclab/flattened-semantic-usd/"
                "0529_val1_flattened_semantic_scene/scene_semantic.usda"
            ),
        ]
    )

    assert isaac_lab_backend_worker._effective_scene_index(args) == 1


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
            "object_index": _unit_isaac_object_index(),
            "receptacle_index": _unit_isaac_receptacle_index(),
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
        semantic_filter=["class"],
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
    assert capture["semantic_filter"] == ["class"]
    assert capture["candidate_bbox_count"] == 1
    assert diagnostics["status"] == "available"
    assert diagnostics["semantic_filter"] == ["class"]
    assert diagnostics["candidate_bbox_count"] == 1
    assert diagnostics["selected_usd_prim_match_count"] == 1
    assert diagnostics["selected_candidate_bboxes"][0]["bbox_xyxy"] == [1, 1, 3, 3]
    assert diagnostics["agent_facing"] is False
    assert diagnostics["no_simulator_label_fallback"] is True


def test_isaac_segmentation_diagnostics_reports_unrenderable_selected_prims() -> None:
    diagnostics = isaac_lab_backend_worker.segmentation_diagnostics(
        "real",
        real_smoke={
            "segmentation": {
                "requested_data_types": ["semantic_segmentation"],
                "output_data_types": ["semantic_segmentation"],
                "candidate_bboxes": [
                    {
                        "data_type": "semantic_segmentation",
                        "label": "BACKGROUND",
                        "label_id": 0,
                        "usd_prim_path": "",
                        "bbox_xyxy": [0, 0, 540, 360],
                        "pixel_count": 194400,
                        "image_size": [540, 360],
                    }
                ],
                "no_simulator_label_fallback": True,
            }
        },
        scene_binding_diagnostics={
            "selected_object_bindings": {
                "bowl_01": {
                    "status": "bound",
                    "usd_prim_path": "/World/Objects/bowl_01",
                    "has_renderable_geometry": False,
                }
            },
            "selected_target_receptacle_bindings": {
                "sink_01": {
                    "status": "bound",
                    "usd_prim_path": "/World/Receptacles/sink_01",
                    "has_renderable_geometry": True,
                }
            },
        },
    )

    assert diagnostics["available"] is False
    assert diagnostics["selected_usd_unrenderable_prim_paths"] == ["/World/Objects/bowl_01"]
    assert any("no renderable geometry" in blocker for blocker in diagnostics["blockers"])


def test_isaac_segmentation_matches_usd_paths_case_insensitively() -> None:
    diagnostics = isaac_lab_backend_worker.segmentation_diagnostics(
        "real",
        real_smoke={
            "segmentation": {
                "requested_data_types": ["semantic_segmentation"],
                "output_data_types": ["semantic_segmentation"],
                "candidate_bboxes": [
                    {
                        "data_type": "semantic_segmentation",
                        "label": "/world/objects/mug_01",
                        "label_id": 4,
                        "usd_prim_path": "/world/objects/mug_01",
                        "bbox_xyxy": [8, 8, 32, 36],
                        "pixel_count": 144,
                        "image_size": [540, 360],
                    }
                ],
                "no_simulator_label_fallback": True,
            }
        },
        scene_binding_diagnostics={
            "selected_object_bindings": {
                "mug_01": {
                    "status": "bound",
                    "usd_prim_path": "/World/Objects/mug_01",
                    "has_renderable_geometry": True,
                }
            },
            "selected_target_receptacle_bindings": {},
        },
    )

    assert diagnostics["available"] is True
    assert diagnostics["selected_usd_prim_match_count"] == 1


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


def test_isaac_scene_index_semantic_labels_are_applied_to_stage_prims(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    records: list[tuple[str, str, tuple[str, ...]]] = []

    class Prim:
        def __init__(self, path: str, valid: bool = True, type_name: str = "") -> None:
            self.path = path
            self.valid = valid
            self.type_name = type_name

        def IsValid(self) -> bool:
            return self.valid

    bowl = Prim("/World/Objects/bowl_01")
    bowl_mesh = Prim("/World/Objects/bowl_01/mesh", type_name="Mesh")
    sink = Prim("/World/Receptacles/sink_01", type_name="Cube")

    class Stage:
        def __init__(self) -> None:
            self.prims = {
                "/World/Objects/bowl_01": bowl,
                "/World/Receptacles/sink_01": sink,
            }

        def GetPrimAtPath(self, path: str) -> Prim:
            return self.prims.get(path, Prim(path, valid=False))

    class StageUtils:
        @staticmethod
        def get_current_stage() -> Stage:
            return Stage()

    class SimUtils:
        @staticmethod
        def add_labels(
            prim: Prim,
            *,
            labels: list[str],
            instance_name: str,
            overwrite: bool,
        ) -> None:
            assert overwrite is True
            records.append((prim.path, instance_name, tuple(labels)))

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "_semantic_label_target_prims",
        lambda prim: [bowl, bowl_mesh] if prim is bowl else [prim],
    )

    result = isaac_lab_backend_worker._apply_scene_index_semantic_labels(
        stage_utils=StageUtils(),
        sim_utils=SimUtils(),
        scene_index_diagnostics={
            "object_index": {
                "bowl_01": {
                    "usd_prim_path": "/World/Objects/bowl_01",
                    "category": "Bowl",
                    "kind": "object",
                }
            },
            "receptacle_index": {
                "sink_01": {
                    "usd_prim_path": "/World/Receptacles/sink_01",
                    "category": "Sink",
                    "kind": "receptacle",
                },
                "missing": {
                    "usd_prim_path": "/World/Receptacles/missing",
                    "category": "CounterTop",
                    "kind": "receptacle",
                },
            },
        },
    )

    assert result["status"] == "applied"
    assert result["applied_count"] == 2
    assert result["labeled_prim_count"] == 3
    assert result["descendant_label_count"] == 1
    assert result["gprim_label_count"] == 2
    assert result["mesh_label_count"] == 1
    assert result["missing_prim_count"] == 1
    assert {
        "source_prim_path": "/World/Objects/bowl_01",
        "target_prim_path": "/World/Objects/bowl_01/mesh",
        "target_type": "Mesh",
        "target_kind": "gprim:Mesh",
    } in result["target_samples"]
    assert ("/World/Objects/bowl_01", "class", ("Bowl",)) in records
    assert ("/World/Objects/bowl_01/mesh", "class", ("Bowl",)) in records
    assert (
        "/World/Objects/bowl_01",
        "usd_prim_path",
        ("/World/Objects/bowl_01",),
    ) in records
    assert ("/World/Receptacles/sink_01", "kind", ("receptacle",)) in records


def test_isaac_runtime_smoke_accepts_official_blocks_generated_scene(
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
            "--generated-scene-kind",
            "isaac_official_blocks",
        ]
    )

    assert args.generated_scene_kind == "isaac_official_blocks"
    assert (
        isaac_lab_backend_worker._generated_scene_filename(args.generated_scene_kind)
        == "roboclaws_isaac_official_blocks_scene.usda"
    )


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
            "object_index": _unit_isaac_object_index(),
            "receptacle_index": _unit_isaac_receptacle_index(),
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


def test_isaac_lab_real_worker_views_recapture_semantic_pose_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
    robot_view_images = _write_robot_view_images(run_dir)
    scene_usd = run_dir / "scene.usda"
    scene_usd.parent.mkdir(parents=True, exist_ok=True)
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")
    _write_nonblank_image(image_path)

    def fake_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
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
            "render_steps": 4,
            "scene_index_diagnostics": {
                "schema": "isaac_usd_scene_index_v1",
                "status": "indexed",
                "source": str(scene_usd),
                "stage_prim_count": 6,
                "object_candidate_count": 1,
                "receptacle_candidate_count": 1,
                "blockers": [],
            },
            "object_index": _unit_isaac_object_index(),
            "receptacle_index": _unit_isaac_receptacle_index(),
        }

    def fake_capture_semantic_pose_robot_views(
        *,
        state: dict[str, object],
        scene_usd: Path,
        view_paths: dict[str, Path],
        width: int,
        height: int,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
    ) -> dict[str, object]:
        del focus_object_id, focus_receptacle_id
        assert scene_usd == run_dir / "scene.usda"
        assert width == 64
        assert height == 48
        semantic_pose = state["semantic_pose_state"]
        assert isinstance(semantic_pose, dict)
        assert semantic_pose["rendered_to_usd"] is False
        for path in view_paths.values():
            _write_nonblank_image(path)
        canonical_dir = (
            view_paths["fpv"].parent / f"{view_paths['fpv'].stem}.canonical_camera_control"
        )
        canonical_dir.mkdir(parents=True, exist_ok=True)
        canonical_fpv = canonical_dir / "isaac_robot_view_fpv.png"
        canonical_verify = canonical_dir / "isaac_robot_view_verify.png"
        _write_nonblank_image(canonical_fpv)
        _write_nonblank_image(canonical_verify)
        return {
            "robot_view_images": {key: str(path) for key, path in view_paths.items()},
            "render_steps": 9,
            "canonical_camera_control": {
                "request": {
                    "api_name": "roboclaws.camera_control.render_views",
                    "color_profile": {"profile_id": "display_srgb_soft_highlight_v1"},
                    "views": [
                        {
                            "robot_view_role": "fpv",
                            "eye": [0.0, 0.0, 1.0],
                            "target": [1.0, 0.0, 1.0],
                        },
                        {
                            "robot_view_role": "verify",
                            "eye": [0.0, -1.0, 2.0],
                            "target": [0.0, 0.0, 1.0],
                        },
                    ],
                },
                "views": [
                    {
                        "robot_view_role": "fpv",
                        "image_path": str(canonical_fpv),
                    },
                    {
                        "robot_view_role": "verify",
                        "image_path": str(canonical_verify),
                    },
                ],
                "render_steps": 6,
                "color_profile": {"profile_id": "display_srgb_soft_highlight_v1"},
                "color_management": {
                    "isaac_robot_view_fpv": {
                        "after": {"overexposed_fraction": 0.0},
                    }
                },
            },
        }

    def fake_capture_scene_camera_views(
        *,
        scene_usd: Path,
        camera_request: dict[str, object],
        output_dir: Path,
        width: int,
        height: int,
        simulation_app: object,
    ) -> dict[str, object]:
        assert scene_usd == run_dir / "scene.usda"
        assert simulation_app == "unit-simulation-app"
        assert camera_request["api_name"] == "roboclaws.camera_control.render_views"
        output_dir.mkdir(parents=True, exist_ok=True)
        views = []
        images: dict[str, str] = {}
        for item in camera_request["views"]:
            assert isinstance(item, dict)
            assert item["robot_view_role"] in {"fpv", "verify"}
            image_path = output_dir / f"{item['view_id']}.png"
            _write_nonblank_image(image_path)
            views.append({**item, "image_path": str(image_path), "shape": [height, width, 3]})
            images[str(item["view_id"])] = str(image_path)
        return {
            "camera_control_api": camera_request["api_name"],
            "color_profile": camera_request.get("color_profile"),
            "color_management": {
                "isaac_robot_view_fpv": {
                    "after": {"overexposed_fraction": 0.0},
                }
            },
            "views": views,
            "images": images,
            "render_steps": 6,
        }

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fake_real_runtime_smoke,
    )
    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "capture_semantic_pose_robot_views",
        fake_capture_semantic_pose_robot_views,
    )
    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "_capture_isaac_lab_scene_camera_views",
        fake_capture_scene_camera_views,
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
            "--scene-usd-path",
            str(scene_usd),
        ]
    )
    isaac_lab_backend_worker.init_state(init_args)
    nav_args = isaac_lab_backend_worker.parse_args(
        [
            "--state-path",
            str(state_path),
            "navigate_to_receptacle",
            "--receptacle-id",
            "sink_01",
        ]
    )
    nav_result = isaac_lab_backend_worker.navigate_to_receptacle(
        nav_args,
        isaac_lab_backend_worker.read_state(state_path),
    )
    assert nav_result["ok"] is True
    assert nav_result["robot_pose"]["pose_source"] == "roboclaws_shared_scene_frame_support_pose"
    result = isaac_lab_backend_worker.write_robot_views(
        isaac_lab_backend_worker.parse_args(
            [
                "--state-path",
                str(state_path),
                "robot_views",
                "--output-dir",
                str(run_dir / "robot_views"),
                "--label",
                "0001_semantic_pose",
                "--render-width",
                "64",
                "--render-height",
                "48",
            ]
        ),
        isaac_lab_backend_worker.read_state(state_path),
    )

    assert result["ok"] is True
    assert result["view_provenance"]["semantic_pose_state_refreshed"] is True
    assert result["view_provenance"]["canonical_camera_control"] is True
    assert result["camera_control_contract"]["same_pose_api"] is True
    assert result["camera_control_contract"]["camera_control_api"] == (
        "roboclaws.camera_control.render_views"
    )
    assert result["camera_control_contract"]["robot_pose"]["pose_source"] == (
        "roboclaws_shared_scene_frame_support_pose"
    )
    assert result["camera_control_contract"]["robot_pose"]["pose_request"]["resolver"] == (
        "roboclaws.cleanup_robot_pose.near_target_v1"
    )
    assert "isaac_lab_camera_rgb_canonical_robot_view" in json.dumps(result["view_provenance"])
    state = isaac_lab_backend_worker.read_state(state_path)
    assert state["semantic_pose_state"]["rendered_to_usd"] is True
    assert state["robot_view_provenance"]["semantic_pose_state_refreshed"] is True
    assert state["robot_view_provenance"]["canonical_camera_control"] is True
    assert state["semantic_pose_view_capture"]["render_steps"] == 9
    assert state["semantic_pose_view_capture"]["canonical_camera_control"] is True
    assert state["semantic_pose_view_capture"]["canonical_camera_control_render_steps"] == 6
    assert state["canonical_robot_view_camera_control_capture"]["schema"] == (
        "isaac_canonical_robot_view_camera_capture_v1"
    )
    assert state["canonical_robot_view_camera_control_capture"]["camera_control_api"] == (
        "roboclaws.camera_control.render_views"
    )
    assert state["canonical_robot_view_camera_control_capture"]["color_profile"]["profile_id"] == (
        "display_srgb_soft_highlight_v1"
    )
    assert (
        state["canonical_robot_view_camera_control_capture"]["color_management"][
            "isaac_robot_view_fpv"
        ]["after"]["overexposed_fraction"]
        == 0.0
    )
    assert len(state["canonical_robot_view_camera_control_capture"]["views"]) == 2
    fpv_capture = state["canonical_robot_view_camera_control_capture"]["views"][0]
    assert fpv_capture["robot_view_role"] == "fpv"
    assert fpv_capture["image_path"].endswith("isaac_robot_view_fpv.png")
    assert fpv_capture["eye"] == [0.0, 0.0, 1.0]
    assert fpv_capture["target"] == [1.0, 0.0, 1.0]
    assert state["semantic_pose_state"]["semantic_pose_view_capture"]["render_steps"] == 9
    robot_view_gap = next(
        item for item in state["mapping_gaps"] if item["area"] == "robot_view_variants"
    )
    assert robot_view_gap["source"] == "isaac_lab_camera_rgb_semantic_pose_robot_views"
    assert "recaptured from the loaded USD scene" in robot_view_gap["detail"]
    assert "static Phase B" not in robot_view_gap["detail"]


def test_isaac_lab_real_worker_views_fallback_when_semantic_pose_rerender_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
    robot_view_images = _write_robot_view_images(run_dir)
    scene_usd = run_dir / "scene.usda"
    scene_usd.parent.mkdir(parents=True, exist_ok=True)
    scene_usd.write_text("#usda 1.0\n", encoding="utf-8")
    _write_nonblank_image(image_path)

    def fake_real_runtime_smoke(
        args: object,
        scenario: object,
    ) -> dict[str, object]:
        del args, scenario
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
            "render_steps": 4,
            "scene_index_diagnostics": {
                "schema": "isaac_usd_scene_index_v1",
                "status": "indexed",
                "source": str(scene_usd),
                "stage_prim_count": 6,
                "object_candidate_count": 1,
                "receptacle_candidate_count": 1,
                "blockers": [],
            },
            "object_index": _unit_isaac_object_index(),
            "receptacle_index": _unit_isaac_receptacle_index(),
        }

    def fail_capture_semantic_pose_robot_views(**_: object) -> dict[str, object]:
        raise RuntimeError("unit rerender failure")

    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "real_runtime_smoke",
        fake_real_runtime_smoke,
    )
    monkeypatch.setattr(
        isaac_lab_backend_worker,
        "capture_semantic_pose_robot_views",
        fail_capture_semantic_pose_robot_views,
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
            "--scene-usd-path",
            str(scene_usd),
        ]
    )
    isaac_lab_backend_worker.init_state(init_args)
    result = isaac_lab_backend_worker.write_robot_views(
        isaac_lab_backend_worker.parse_args(
            [
                "--state-path",
                str(state_path),
                "robot_views",
                "--output-dir",
                str(run_dir / "robot_views"),
                "--label",
                "0001_semantic_pose",
                "--render-width",
                "64",
                "--render-height",
                "48",
            ]
        ),
        isaac_lab_backend_worker.read_state(state_path),
    )

    assert result["ok"] is True
    assert result["view_provenance"]["semantic_pose_state_refreshed"] is False
    assert "isaac_lab_camera_rgb_static_robot_views" in json.dumps(result["view_provenance"])
    state = isaac_lab_backend_worker.read_state(state_path)
    assert state["semantic_pose_state"]["rendered_to_usd"] is False
    assert any(
        item["area"] == "semantic_pose_robot_view_rerender"
        and item["status"] == "blocked_capability"
        and "unit rerender failure" in item["detail"]
        for item in state["mapping_gaps"]
    )


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
            "object_index": _unit_isaac_object_index(),
            "receptacle_index": _unit_isaac_receptacle_index(),
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


def _unit_isaac_object_index() -> dict[str, dict[str, object]]:
    return {
        "mug_01": {
            "usd_prim_path": "/World/Objects/mug_01",
            "category": "mug01",
            "public_label": "mug_01",
            "index_source": "usd_stage_traversal",
            "usd_world_bounds": {
                "center": [4.0, 5.0, 0.4],
                "max": [4.2, 5.2, 0.8],
                "size": [0.4, 0.4, 0.8],
            },
        }
    }


def _unit_isaac_receptacle_index() -> dict[str, dict[str, object]]:
    return {
        "sink_01": {
            "usd_prim_path": "/World/Receptacles/sink_01",
            "category": "sink01",
            "public_label": "sink_01",
            "index_source": "usd_stage_traversal",
            "usd_world_bounds": {
                "center": [2.5, 5.5, 0.75],
                "max": [3.0, 6.0, 1.2],
                "size": [1.0, 1.0, 0.9],
            },
            "support_pose": {
                "frame": "usd_world",
                "x": 2.5,
                "y": 5.5,
                "z": 1.2,
                "source": "usd_world_bounds_top_center",
                "support_radius_m": 0.5,
            },
        }
    }

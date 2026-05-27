from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from roboclaws.molmo_cleanup.isaac_lab_backend import (
    ISAAC_SEMANTIC_POSE_PROVENANCE,
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
    assert backend.segmentation["status"] == "blocked_capability"
    assert backend.scene_load["status"] == "fake_protocol"
    assert backend.scene_load["usd_stage_loaded"] is False
    assert any(item["area"] == "camera_capture" for item in backend.mapping_gaps)
    assert any(item["status"] == "placeholder_visuals" for item in backend.mapping_gaps)

    snapshot_path = tmp_path / "snapshot.png"
    backend.write_snapshot(snapshot_path, title="Fake Isaac snapshot")
    assert snapshot_path.is_file()
    assert snapshot_path.stat().st_size > 0

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
    assert done["final_locations"][object_id] == receptacle_id


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


def test_isaac_lab_real_init_uses_phase_a_smoke_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    state_path = tmp_path / "state.json"
    image_path = run_dir / "isaac_runtime_smoke.png"
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
        return {
            "image_path": str(image_path),
            "scene_usd": str(scene_usd),
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
            "render_steps": 3,
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
    assert result["scene_load"]["loaded_asset_kind"] == "generated_runtime_smoke_usd"
    assert result["artifacts"]["runtime_smoke_image"] == str(image_path)
    assert any(
        item["area"] == "camera_capture" and item["status"] == "real_rendering_proven"
        for item in result["mapping_gaps"]
    )
    assert any(
        item["area"] == "molmospaces_usd_scene_loading" and item["status"] == "not_attempted"
        for item in result["mapping_gaps"]
    )

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["runtime"]["rendering"]["status"] == "real_rendering_proven"
    assert state["scene_load"]["usd_stage_loaded"] is True
    assert state["real_runtime_smoke"]["scene_usd"] == str(scene_usd)


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

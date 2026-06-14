from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from roboclaws.household.backend_contract import (
    SYNTHETIC_BACKEND,
    CleanupBackendSession,
    attach_cleanup_backend_runtime_metadata,
    build_cleanup_backend_session,
    cleanup_backend_name,
)


def test_cleanup_backend_name_uses_explicit_backend_id() -> None:
    backend = SimpleNamespace(backend="molmospaces_subprocess")

    assert cleanup_backend_name(backend) == "molmospaces_subprocess"
    assert cleanup_backend_name(backend, override="isaaclab_subprocess") == "isaaclab_subprocess"
    assert cleanup_backend_name(SimpleNamespace()) == SYNTHETIC_BACKEND


def test_synthetic_backend_factory_can_build_baseline_scenario(tmp_path: Path) -> None:
    session = build_cleanup_backend_session(
        backend_name=SYNTHETIC_BACKEND,
        run_dir=tmp_path,
        seed=7,
        generated_mess_count=0,
    )

    assert isinstance(session, CleanupBackendSession)
    assert session.backend_name() == SYNTHETIC_BACKEND
    assert session.backend.scenario.private_manifest.targets == ()
    assert session.backend.scenario.private_manifest.success_threshold == 0


def test_molmospaces_runtime_metadata_attaches_common_backend_payload(tmp_path: Path) -> None:
    backend = SimpleNamespace(
        backend="molmospaces_subprocess",
        python_executable=tmp_path / "python",
        runtime={"runtime": "fake"},
        model_stats={"object_count": 3},
        scene_xml=str(tmp_path / "scene.xml"),
        metadata_object_count=3,
        requested_generated_mess_count=5,
        generated_mess_count=4,
        mess_placement_diagnostics=[{"object_id": "apple_1"}],
        placement_diagnostics=[{"object_id": "mug_1"}],
        robot={"robot_name": "rby1m"},
    )
    run_result = {"artifacts": {}}

    attach_cleanup_backend_runtime_metadata(
        run_result=run_result,
        backend=backend,
        run_dir=tmp_path,
    )

    assert run_result["molmospaces_runtime"]["runtime"] == {"runtime": "fake"}
    assert run_result["mess_placement_diagnostics"] == [{"object_id": "apple_1"}]
    assert run_result["placement_diagnostics"] == [{"object_id": "mug_1"}]
    assert run_result["robot_name"] == "rby1m"


def test_isaac_runtime_metadata_writes_scene_index_artifact(tmp_path: Path) -> None:
    scene_index_payload = {
        "schema": "isaac_scene_index_artifact_v1",
        "backend": "isaaclab_subprocess",
        "agent_facing": False,
        "private_manifest_exposed_to_agent": False,
    }
    backend = SimpleNamespace(
        backend="isaaclab_subprocess",
        python_executable=tmp_path / "python",
        runtime={"runtime_mode": "fake"},
        scenario_source="default_cleanup_scenario",
        scene_usd="",
        scene_index=0,
        object_index={"obj": {}},
        receptacle_index={"sink": {}},
        scene_index_diagnostics={"status": "fake"},
        scene_binding_diagnostics={"status": "placeholder_mapping"},
        segmentation={"status": "blocked_capability"},
        scene_load={"status": "fake_protocol"},
        current_mapping_gaps=[{"area": "camera_capture"}],
        snapshot_artifacts=[{"placeholder_visuals": True}],
        semantic_pose_state={"schema": "isaac_semantic_pose_state_v1"},
        semantic_pose_view_capture={},
        robot_import={"status": "missing_urdf"},
        robot={"robot_name": "rby1m"},
        requested_generated_mess_count=1,
        generated_mess_count=1,
        scene_index_artifact_payload=lambda: scene_index_payload,
    )
    run_result = {"artifacts": {}}

    attach_cleanup_backend_runtime_metadata(
        run_result=run_result,
        backend=backend,
        run_dir=tmp_path,
    )

    scene_index_path = tmp_path / "isaac_scene_index.json"
    assert json.loads(scene_index_path.read_text(encoding="utf-8")) == scene_index_payload
    assert run_result["artifacts"]["isaac_scene_index"] == str(scene_index_path)
    assert run_result["isaac_runtime"]["object_index_count"] == 1
    assert run_result["isaac_runtime"]["receptacle_index_count"] == 1
    assert run_result["robot_import"] == {"status": "missing_urdf"}

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.generated_mess import (
    generated_mess_success_threshold,
    select_generated_mess_targets,
)
from roboclaws.molmo_cleanup.subprocess_backend import (
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
    _parse_last_json_object,
)


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "justfile").is_file():
            return parent
    raise AssertionError("could not locate repo root")


REPO_ROOT = _repo_root()
WORKER_PATH = REPO_ROOT / "scripts" / "molmospaces_subprocess_worker.py"


def _load_worker_module():
    spec = importlib.util.spec_from_file_location("molmospaces_subprocess_worker", WORKER_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_parse_last_json_object_tolerates_upstream_stdout_noise() -> None:
    payload = _parse_last_json_object(
        "Using SCENES_ROOT: /tmp/assets\n"
        + json.dumps({"ok": True, "tool": "init", "backend": MOLMOSPACES_SUBPROCESS_BACKEND})
        + "\n"
    )

    assert payload["backend"] == MOLMOSPACES_SUBPROCESS_BACKEND


def test_subprocess_backend_reports_missing_runtime(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="Python 3.11 runtime is missing"):
        MolmoSpacesSubprocessBackend(
            run_dir=tmp_path,
            python_executable=tmp_path / "missing-python",
        )


def test_worker_select_targets_honors_requested_generated_count() -> None:
    receptacles = [
        {"receptacle_id": "sink_01", "category": "Sink"},
        {"receptacle_id": "shelf_01", "category": "ShelvingUnit"},
        {"receptacle_id": "fridge_01", "category": "Fridge"},
        {"receptacle_id": "tvstand_01", "category": "TVStand"},
        {"receptacle_id": "bed_01", "category": "Bed"},
    ]
    objects = (
        [{"object_id": f"mug_{index:02d}", "category": "Mug"} for index in range(3)]
        + [{"object_id": f"book_{index:02d}", "category": "Book"} for index in range(3)]
        + [{"object_id": f"apple_{index:02d}", "category": "Apple"} for index in range(3)]
        + [{"object_id": f"remote_{index:02d}", "category": "RemoteControl"} for index in range(3)]
        + [{"object_id": f"pillow_{index:02d}", "category": "Pillow"} for index in range(3)]
    )

    selected = select_generated_mess_targets(objects, receptacles, target_count=10)

    assert len(selected) == 10
    assert len({item["object_id"] for item in selected}) == 10
    assert all(item["target_receptacle_id"] for item in selected)
    assert generated_mess_success_threshold(10) == 7


def test_worker_select_targets_uses_seed_for_source_pool_diversity() -> None:
    receptacles = [
        {"receptacle_id": "sink_01", "category": "Sink"},
        {"receptacle_id": "shelf_01", "category": "ShelvingUnit"},
        {"receptacle_id": "fridge_01", "category": "Fridge"},
        {"receptacle_id": "tvstand_01", "category": "TVStand"},
        {"receptacle_id": "bed_01", "category": "Bed"},
    ]
    objects = (
        [{"object_id": f"mug_{index:02d}", "category": "Mug"} for index in range(5)]
        + [{"object_id": f"book_{index:02d}", "category": "Book"} for index in range(5)]
        + [{"object_id": f"apple_{index:02d}", "category": "Apple"} for index in range(5)]
        + [{"object_id": f"remote_{index:02d}", "category": "RemoteControl"} for index in range(5)]
        + [{"object_id": f"pillow_{index:02d}", "category": "Pillow"} for index in range(5)]
    )

    first = select_generated_mess_targets(objects, receptacles, target_count=10, seed=11)
    second = select_generated_mess_targets(objects, receptacles, target_count=10, seed=11)
    third = select_generated_mess_targets(objects, receptacles, target_count=10, seed=12)

    assert [item["object_id"] for item in first] == [item["object_id"] for item in second]
    assert [item["object_id"] for item in first] != [item["object_id"] for item in third]
    assert [item["target_receptacle_id"] for item in first] == [
        item["target_receptacle_id"] for item in third
    ]


def test_sync_held_object_to_robot_pose_moves_freejoint_body() -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()
    model = worker.mujoco.MjModel.from_xml_string(
        """
        <mujoco>
          <worldbody>
            <body name="apple" pos="0 0 0">
              <freejoint name="apple_free"/>
              <geom type="sphere" size="0.03"/>
            </body>
          </worldbody>
        </mujoco>
        """
    )
    data = worker.mujoco.MjData(model)
    state = {
        "held_object_id": "apple_01",
        "robot_pose": {"x": 1.0, "y": 2.0, "theta": 0.0},
        "objects": {"apple_01": {"body_name": "apple", "position": [0.0, 0.0, 0.0]}},
    }

    result = worker._sync_held_object_to_robot_pose(model, data, state)
    worker.mujoco.mj_forward(model, data)

    body_id = worker.mujoco.mj_name2id(model, worker.mujoco.mjtObj.mjOBJ_BODY, "apple")
    assert result == {
        "object_id": "apple_01",
        "position": [1.45, 2.0, 1.05],
        "position_source": "robot_relative_held_pose",
    }
    assert data.xpos[body_id].tolist() == pytest.approx([1.45, 2.0, 1.05])

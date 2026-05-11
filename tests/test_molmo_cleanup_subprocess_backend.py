from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from roboclaws.molmo_cleanup.subprocess_backend import (
    MOLMOSPACES_SUBPROCESS_BACKEND,
    MolmoSpacesSubprocessBackend,
    _parse_last_json_object,
)

REPO_ROOT = Path(__file__).resolve().parent.parent
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

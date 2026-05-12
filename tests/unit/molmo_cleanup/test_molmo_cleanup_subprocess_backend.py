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
WORKER_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "molmospaces_subprocess_worker.py"


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
    with pytest.raises(RuntimeError, match="Python runtime is missing"):
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


def test_worker_placement_diagnostic_records_support_relation() -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()
    state = {
        "objects": {
            "book_01": {
                "object_id": "book_01",
                "category": "Book",
                "body_name": "book/body",
                "position": [5.12, 6.08, 0.73],
            }
        },
        "receptacles": {
            "table_01": {
                "receptacle_id": "table_01",
                "category": "DiningTable",
                "body_name": "table/body",
                "position": [5.0, 6.0, 0.38],
            }
        },
    }

    diagnostic = worker._placement_diagnostic(
        state=state,
        object_id="book_01",
        receptacle_id="table_01",
        relation="on",
        requested_position=[5.12, 6.08, 0.73],
        source="unit_test",
    )

    assert diagnostic["schema"] == "molmospaces_semantic_placement_diagnostic_v1"
    assert diagnostic["support_status"] == "semantic_on_receptacle"
    assert diagnostic["relation"] == "on"
    assert diagnostic["xy_distance_m"] == pytest.approx(0.144222)
    assert diagnostic["z_delta_m"] == pytest.approx(0.35)
    assert diagnostic["contact_proof"] == "not_measured_mujoco_freejoint_qpos"


def test_worker_allows_open_shelf_place_inside_without_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()

    class _FakeData:
        qpos = [0.0]

    state = {
        "held_object_id": "book_01",
        "selected_object_ids": ["book_01"],
        "qpos": [0.0],
        "open_receptacle_ids": [],
        "current_receptacle_id": None,
        "objects": {
            "book_01": {
                "object_id": "book_01",
                "category": "Book",
                "body_name": "book/body",
                "position": [0.0, 0.0, 0.0],
            }
        },
        "receptacles": {
            "shelf_01": {
                "receptacle_id": "shelf_01",
                "category": "ShelvingUnit",
                "body_name": "shelf/body",
                "position": [1.0, 2.0, 0.4],
            },
            "fridge_01": {
                "receptacle_id": "fridge_01",
                "category": "Fridge",
                "body_name": "fridge/body",
                "position": [3.0, 4.0, 0.6],
            },
        },
    }

    monkeypatch.setattr(
        worker,
        "_load_model_data_for_state",
        lambda _state: (object(), _FakeData()),
    )
    monkeypatch.setattr(worker, "_apply_qpos", lambda _data, _qpos: None)
    monkeypatch.setattr(worker, "_set_free_body_position", lambda *_args: None)
    monkeypatch.setattr(worker, "_refresh_object_positions", lambda *_args: None)
    monkeypatch.setattr(worker.mujoco, "mj_forward", lambda *_args: None)

    placed = worker._place_object_at_receptacle(
        state,
        "shelf_01",
        tool="place_inside",
        relation="inside",
    )

    assert placed["ok"] is True
    assert placed["location_relation"] == "inside"
    assert placed["contained_in"] == "shelf_01"
    state["held_object_id"] = "book_01"
    rejected = worker._place_object_at_receptacle(
        state,
        "fridge_01",
        tool="place_inside",
        relation="inside",
    )
    assert rejected["ok"] is False
    assert rejected["error_reason"] == "receptacle_closed"


def test_worker_visual_grounding_marks_zero_pixels_weak_or_contained() -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()

    weak = worker._annotate_focus_visual_grounding(
        {
            "has_focus": True,
            "object_id": "book_01",
            "receptacle_id": "desk_01",
            "fpv_visibility": {"status": "ok", "object_pixels": 0},
            "visibility": {"status": "ok", "object_pixels": 0},
        }
    )
    contained = worker._annotate_focus_visual_grounding(
        {
            "has_focus": True,
            "object_id": "apple_01",
            "receptacle_id": "fridge_01",
            "receptacle_category": "Fridge",
            "object_contained_in": "fridge_01",
            "object_location_relation": "inside",
            "fpv_visibility": {"status": "ok", "object_pixels": 0},
            "visibility": {"status": "ok", "object_pixels": 0},
        }
    )
    open_shelf = worker._annotate_focus_visual_grounding(
        {
            "has_focus": True,
            "object_id": "book_01",
            "receptacle_id": "shelf_01",
            "receptacle_category": "ShelvingUnit",
            "object_contained_in": "shelf_01",
            "object_location_relation": "inside",
            "fpv_visibility": {"status": "ok", "object_pixels": 0},
            "visibility": {"status": "ok", "object_pixels": 0},
        }
    )

    assert weak["fpv_visibility"]["status"] == "weak_object_visibility"
    assert weak["visibility"]["status"] == "weak_object_visibility"
    assert contained["fpv_visibility"]["status"] == "contained_inside"
    assert contained["visibility"]["status"] == "contained_inside"
    assert open_shelf["fpv_visibility"]["status"] == "weak_object_visibility"
    assert open_shelf["visibility"]["status"] == "weak_object_visibility"


def test_worker_focus_payload_uses_held_object_closeup_before_receptacle_place() -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()
    state = {
        "objects": {
            "potato_01": {
                "object_id": "potato_01",
                "category": "Potato",
                "body_name": "potato/body",
                "position": [8.2, 5.0, 1.22],
                "contained_in": None,
                "location_relation": "held",
            }
        },
        "receptacles": {
            "fridge_01": {
                "receptacle_id": "fridge_01",
                "category": "Fridge",
                "body_name": "fridge/body",
                "position": [8.2, 4.7, 0.7],
            }
        },
    }

    focus = worker._focus_payload(state, "potato_01", "fridge_01")

    assert focus["focus_mode"] == "object_closeup"
    assert focus["focus_position"] == [8.2, 5.0, 1.22]


def test_worker_focus_camera_azimuth_does_not_apply_fridge_angle_to_held_object() -> None:
    pytest.importorskip("mujoco")
    worker = _load_worker_module()
    focus = {
        "focus_mode": "object_closeup",
        "receptacle_category": "Fridge",
        "object_contained_in": None,
        "receptacle_id": "fridge_01",
    }

    azimuth = worker._focus_camera_azimuth(
        {"robot_pose": {"x": 8.2, "y": 5.8}},
        [8.2, 5.0, 1.22],
        focus,
    )

    assert azimuth == pytest.approx(180.0)


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
        "position": [1.8, 2.0, 1.22],
        "position_source": "robot_relative_held_pose",
    }
    assert data.xpos[body_id].tolist() == pytest.approx([1.8, 2.0, 1.22])

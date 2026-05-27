from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "check_isaac_lab_runtime_smoke_result.py"


def write_smoke_image(path: Path) -> None:
    image = Image.new("RGB", (64, 48), color=(20, 40, 60))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 40), outline=(220, 180, 40), width=3)
    image.save(path)


def run_checker(
    tmp_path: Path,
    result: dict[str, object],
    *args: str,
    robot_views: dict[str, object] | None = None,
    prefix_logs: bool = False,
) -> subprocess.CompletedProcess[str]:
    result_path = tmp_path / "init_result.json"
    text = json.dumps(result)
    if prefix_logs:
        text = f"Isaac startup log line\n{text}\n"
    result_path.write_text(text, encoding="utf-8")
    robot_views_args: list[str] = []
    if robot_views is not None:
        robot_views_path = tmp_path / "robot_views_result.json"
        robot_views_path.write_text(json.dumps(robot_views), encoding="utf-8")
        robot_views_args = ["--robot-views-result", str(robot_views_path)]
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--init-result",
            str(result_path),
            *robot_views_args,
            *args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_isaac_runtime_smoke_checker_rejects_placeholder_real_mode(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": False,
                "placeholder_visuals": True,
            },
        },
        "scene_load": {
            "status": "blocked_capability",
            "usd_stage_loaded": False,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-real-rendering",
        "--require-usd-stage-loaded",
        "--require-nonblank-image",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["status"] == "failed"
    assert "real Isaac rendering is not proven" in summary["errors"]
    assert "USD stage loading is not proven" in summary["errors"]
    assert "smoke image appears blank" not in summary["errors"]


def test_isaac_runtime_smoke_checker_accepts_real_rendering_evidence(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    state_path = tmp_path / "state.json"
    write_smoke_image(image_path)
    robot_views = write_robot_views_result(tmp_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "scene_index_diagnostics": {
            "status": "indexed",
            "stage_prim_count": 6,
            "object_candidate_count": 1,
            "receptacle_candidate_count": 1,
        },
        "scene_binding_diagnostics": {
            "schema": "isaac_public_scene_bindings_v1",
            "status": "selected_bound",
            "source": "usd_stage_traversal",
            "selected_object_count": 1,
            "selected_target_receptacle_count": 1,
            "selected_object_bound_count": 1,
            "selected_target_receptacle_bound_count": 1,
            "blockers": [],
            "private_manifest_exposed_to_agent": False,
        },
        "object_index": {"mug_01": {"usd_prim_path": "/World/Objects/mug_01"}},
        "receptacle_index": {"sink_01": {"usd_prim_path": "/World/Receptacles/sink_01"}},
        "segmentation": available_segmentation_diagnostics(),
        "scene_usd": "/tmp/example.usd",
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }
    state_path.write_text(
        json.dumps(
            {
                "backend": "isaaclab_subprocess",
                "runtime": {"runtime_mode": "real"},
            }
        ),
        encoding="utf-8",
    )

    completed = run_checker(
        tmp_path,
        result,
        "--state-path",
        str(state_path),
        "--require-real-rendering",
        "--require-usd-stage-loaded",
        "--require-usd-scene-index",
        "--require-selected-usd-bindings",
        "--require-robot-view-images",
        "--require-nonblank-image",
        "--require-segmentation-evidence",
        robot_views=robot_views,
        prefix_logs=True,
    )

    assert completed.returncode == 0
    summary = json.loads(completed.stdout)
    assert summary["status"] == "passed"
    assert summary["errors"] == []
    assert summary["scene_index_status"] == "indexed"
    assert summary["scene_binding_status"] == "selected_bound"
    assert summary["robot_view_status"] == "present"


def test_isaac_runtime_smoke_checker_rejects_blocked_segmentation(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "segmentation": {
            "schema": "isaac_segmentation_diagnostics_v1",
            "status": "blocked_capability",
            "available": False,
            "tensor_output_available": False,
            "candidate_bbox_count": 0,
            "selected_usd_prim_match_count": 0,
            "candidate_overlay_status": "blocked_capability",
            "agent_facing": False,
            "no_simulator_label_fallback": True,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-segmentation-evidence",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "Isaac segmentation evidence is not available" in summary["errors"]
    assert "Isaac segmentation tensors were not captured" in summary["errors"]
    assert "Isaac segmentation produced no bbox candidates" in summary["errors"]


def test_isaac_runtime_smoke_checker_rejects_missing_usd_scene_index(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-usd-scene-index",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "missing USD scene index diagnostics" in summary["errors"]
    assert "USD scene index has no object candidates" in summary["errors"]


def test_isaac_runtime_smoke_checker_rejects_missing_selected_usd_bindings(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-selected-usd-bindings",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "missing selected USD binding diagnostics" in summary["errors"]


def test_isaac_runtime_smoke_checker_rejects_partial_selected_usd_bindings(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "scene_binding_diagnostics": {
            "schema": "isaac_public_scene_bindings_v1",
            "status": "partial",
            "source": "usd_stage_traversal",
            "selected_object_count": 1,
            "selected_target_receptacle_count": 1,
            "selected_object_bound_count": 1,
            "selected_target_receptacle_bound_count": 0,
            "blockers": ["Selected target receptacle has no USD binding: sink_01"],
            "private_manifest_exposed_to_agent": False,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-selected-usd-bindings",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "selected cleanup handles are not fully bound to USD prims" in summary["errors"]
    assert "not all selected target receptacles have USD prim bindings" in summary["errors"]
    assert "selected USD binding diagnostics still report blockers" in summary["errors"]


def test_isaac_runtime_smoke_checker_rejects_missing_robot_views(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-real-rendering",
        "--require-robot-view-images",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "missing robot views result" in summary["errors"]


def test_isaac_runtime_smoke_checker_rejects_placeholder_robot_views(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }
    robot_views = write_robot_views_result(tmp_path)
    robot_views["view_provenance"] = {"fpv": "fake_protocol_placeholder_image"}

    completed = run_checker(
        tmp_path,
        result,
        "--require-real-rendering",
        "--require-robot-view-images",
        robot_views=robot_views,
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert "robot view provenance still reports placeholder visuals" in summary["errors"]


def write_robot_views_result(tmp_path: Path) -> dict[str, object]:
    view_dir = tmp_path / "robot_views"
    view_dir.mkdir(parents=True, exist_ok=True)
    views = {}
    for key in ("fpv", "chase", "map", "verify"):
        path = view_dir / f"runtime_smoke.{key}.png"
        write_smoke_image(path)
        views[key] = str(path)
    return {
        "ok": True,
        "view_variant": "isaaclab-fpv-map-chase-verify",
        "view_provenance": {
            "fpv": "isaac_lab_camera_rgb_static_robot_views:fpv",
            "chase": "isaac_lab_camera_rgb_static_robot_views:chase",
            "map": "isaac_lab_camera_rgb_static_robot_views:map",
            "verify": "isaac_lab_camera_rgb_static_robot_views:verify",
        },
        "views": views,
    }


def available_segmentation_diagnostics() -> dict[str, object]:
    return {
        "schema": "isaac_segmentation_diagnostics_v1",
        "status": "available",
        "available": True,
        "source": "isaac_lab_camera",
        "capture_method": "isaac_lab_camera_segmentation",
        "requested_data_types": [
            "semantic_segmentation",
            "instance_segmentation_fast",
            "instance_id_segmentation_fast",
        ],
        "output_data_types": ["instance_id_segmentation_fast"],
        "tensor_output_available": True,
        "candidate_overlay_status": "available",
        "candidate_bbox_count": 1,
        "selected_usd_prim_match_count": 1,
        "agent_facing": False,
        "no_simulator_label_fallback": True,
        "candidate_bboxes": [
            {
                "view": "fpv",
                "data_type": "instance_id_segmentation_fast",
                "label_id": 3,
                "label": "/World/Objects/mug_01",
                "usd_prim_path": "/World/Objects/mug_01",
                "bbox_xyxy": [8, 8, 32, 36],
                "pixel_count": 144,
                "image_size": [64, 48],
            }
        ],
    }

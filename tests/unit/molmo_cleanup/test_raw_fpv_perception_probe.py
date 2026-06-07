from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_raw_fpv_perception_probe.py"
LABEL_SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "generate_raw_fpv_private_labels.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_raw_fpv_perception_probe", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_label_module():
    spec = importlib.util.spec_from_file_location(
        "generate_raw_fpv_private_labels", LABEL_SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_raw_fpv_probe_keeps_private_labels_out_of_prompt_inputs(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )
    predictions = _write_predictions(
        tmp_path / "predictions.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
        coarse_region="upper_left",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "privacy",
                "--prompt-variant",
                "baseline_json",
            ]
        )
    )

    prompt_inputs = json.loads(Path(report["artifacts"]["prompt_inputs"]).read_text())
    prompt_text = json.dumps(prompt_inputs, sort_keys=True)
    score = json.loads(Path(report["artifacts"]["private_score"]).read_text())

    assert report["status"] == "success"
    assert report["privacy"]["private_labels_in_prompt_inputs"] is False
    assert report["privacy"]["agent_facing_input_contains_executable_prior_handles"] is False
    assert "private_plate_001" not in prompt_text
    assert "private_plate_001" in json.dumps(score)


def test_raw_fpv_probe_scores_live_like_top_candidate_and_duplicates(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path, observation_ids=("raw_fpv_001", "raw_fpv_002"))
    labels = tmp_path / "private_labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_private_label_manifest_v1",
                "labels": [
                    {
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "source_observation_id": "raw_fpv_001",
                        "object_id": "private_plate_001",
                        "category": "plate",
                        "bbox": [0.1, 0.2, 0.2, 0.2],
                    },
                    {
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_002"
                        ),
                        "source_observation_id": "raw_fpv_002",
                        "object_id": "private_plate_001",
                        "category": "plate",
                        "bbox": [0.11, 0.21, 0.2, 0.2],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "response": _response("raw_fpv_001", "plate", [0.1, 0.2, 0.2, 0.2]),
                    },
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_002"
                        ),
                        "response": _response("raw_fpv_002", "plate", [0.11, 0.21, 0.2, 0.2]),
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "duplicates",
                "--prompt-variant",
                "baseline_json",
                "--threshold",
                "2",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]
    live_like = metrics["live_like_top_candidate"]

    assert metrics["strict_bbox_unique_confirmable_count"] == 1
    assert metrics["coarse_unique_confirmable_count"] == 1
    assert metrics["unique_confirmable_count"] == 1
    assert metrics["duplicate_count"] >= 1
    assert live_like["strict_bbox_threshold_met"] is False
    assert live_like["coarse_threshold_met"] is False
    assert report["route_recommendation"] == "prefer_camera_grounded_labels"


def test_raw_fpv_probe_reports_coarse_locality_route(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_book_001",
        category="book",
        bbox=[0.7, 0.7, 0.1, 0.1],
    )
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "response": {
                            "schema": "raw_fpv_probe_response_v1",
                            "candidates": [
                                {
                                    "source_observation_id": "raw_fpv_001",
                                    "category": "book",
                                    "evidence_note": "book visible on lower right shelf",
                                    "confidence": 0.8,
                                    "locality": {
                                        "coarse_region": "lower_right",
                                        "surface_hint": "shelf",
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "coarse",
                "--prompt-variant",
                "baseline_json",
                "--threshold",
                "1",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]

    assert metrics["strict_bbox_unique_confirmable_count"] == 0
    assert metrics["coarse_unique_confirmable_count"] == 1
    assert report["route_recommendation"] == "try_live_coarse_locality_contract"
    assert Path(report["artifacts"]["html_report"]).is_file()


def test_private_label_generator_reads_only_pre_cleanup_sweep(tmp_path: Path) -> None:
    labels = _load_label_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {
                            "raw_fpv_observation": _raw_observation(
                                "raw_fpv_001",
                                "robot_views/0001_raw_fpv_001.fpv.png",
                            )
                        },
                    }
                ),
                json.dumps({"event": "request", "tool": "pick", "request": {}}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {
                            "raw_fpv_observation": _raw_observation(
                                "raw_fpv_002",
                                "robot_views/0002_raw_fpv_002.fpv.png",
                            )
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    observations = labels.first_sweep_observations_from_trace(trace_path)

    assert [item["observation_id"] for item in observations] == ["raw_fpv_001"]
    assert observations[0]["robot_pose"]["x"] == 1.25
    assert observations[0]["image_artifact"] == "robot_views/0001_raw_fpv_001.fpv.png"


def test_private_label_generator_full_trace_keeps_later_observations(tmp_path: Path) -> None:
    labels = _load_label_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {"raw_fpv_observation": _raw_observation("raw_fpv_001", "")},
                    }
                ),
                json.dumps({"event": "request", "tool": "pick", "request": {}}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {"raw_fpv_observation": _raw_observation("raw_fpv_002", "")},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    observations = labels.observations_from_trace(
        labels._iter_trace_rows(trace_path), replay_mode="full_trace"
    )

    assert [item["observation_id"] for item in observations] == [
        "raw_fpv_001",
        "raw_fpv_002",
    ]


def test_private_label_generator_extracts_private_placement_bindings() -> None:
    labels = _load_label_module()
    bindings = labels.placement_bindings_from_trace(
        [
            {
                "event": "response",
                "tool": "place_inside",
                "response": {
                    "ok": True,
                    "object_id": "observed_007",
                    "placement_diagnostic": {
                        "object_id": "book_private_001",
                        "receptacle_id": "shelf_private_001",
                        "relation": "inside",
                    },
                },
            }
        ]
    )

    assert bindings == {
        "observed_007": {
            "private_object_id": "book_private_001",
            "receptacle_id": "shelf_private_001",
            "relation": "inside",
            "place_tool": "place_inside",
        }
    }


def test_private_label_generator_reconstructs_generated_mess_manifest() -> None:
    labels = _load_label_module()
    state = {
        "seed": 7,
        "scene_source": "procthor-10k-val",
        "scene_index": 0,
        "private_manifest": {
            "success_threshold": 5,
            "targets": [
                {
                    "object_id": "plate_private_001",
                    "valid_receptacle_ids": ["sink_private_001"],
                }
            ],
        },
        "mess_placement_diagnostics": [
            {
                "object_id": "plate_private_001",
                "object_category": "Plate",
                "receptacle_id": "table_private_001",
                "relation": "on",
            }
        ],
    }

    manifest = labels.generated_mess_manifest_from_state(state)

    assert manifest["schema"] == "roboclaws_generated_mess_manifest_v1"
    assert manifest["targets"] == [
        {
            "object_id": "plate_private_001",
            "category": "Plate",
            "target_receptacle_id": "sink_private_001",
            "valid_receptacle_ids": ["sink_private_001"],
            "start_receptacle_id": "table_private_001",
            "relation": "on",
            "placement_index": 0,
        }
    ]


def test_private_label_generator_normalizes_bbox_and_grid_region() -> None:
    labels = _load_label_module()

    bbox = labels.normalize_box_xywh([270, 180, 539, 359], width=540, height=360)

    assert bbox == [0.5, 0.5, 0.5, 0.5]
    assert labels.coarse_regions_from_bbox(bbox) == ["lower_right"]


def _raw_run_dir(
    base: Path,
    *,
    observation_ids: tuple[str, ...] = ("raw_fpv_001",),
) -> Path:
    run_dir = base / "household-cleanup" / "codex-camera-raw" / "0606_1537" / "seed-7"
    robot_views = run_dir / "robot_views"
    robot_views.mkdir(parents=True)
    observations = []
    for index, observation_id in enumerate(observation_ids, start=1):
        name = f"{index:04d}_{observation_id}.fpv.png"
        Image.new("RGB", (120, 90), color=(index * 30, 20, 80)).save(robot_views / name)
        observations.append(
            {
                "observation_id": observation_id,
                "waypoint_id": f"generated_exploration_{index:03d}",
                "room_id": "generated_area",
                "perception_mode": "raw_fpv_only",
                "structured_detections_available": False,
                "image_artifacts": {"fpv": f"robot_views/{name}"},
            }
        )
    (run_dir / "agent_view.json").write_text(
        json.dumps({"raw_fpv_observations": observations}) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _raw_observation(observation_id: str, image_artifact: str) -> dict[str, object]:
    return {
        "observation_id": observation_id,
        "waypoint_id": "generated_exploration_001",
        "room_id": "generated_area",
        "image_artifacts": {"fpv": image_artifact},
        "robot_view_label": observation_id,
        "camera_control_contract": {
            "robot_pose": {
                "x": 1.25,
                "y": 2.5,
                "z": 0.0,
                "theta": 0.0,
                "head_yaw": 0.0,
                "head_pitch": 0.25,
            }
        },
    }


def _write_private_labels(
    path: Path,
    *,
    frame_id: str,
    object_id: str,
    category: str,
    bbox: list[float],
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_private_label_manifest_v1",
                "labels": [
                    {
                        "frame_id": frame_id,
                        "source_observation_id": frame_id.rsplit("/", 1)[-1],
                        "object_id": object_id,
                        "category": category,
                        "bbox": bbox,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_predictions(
    path: Path,
    *,
    frame_id: str,
    category: str,
    bbox: list[float],
    coarse_region: str,
) -> Path:
    observation_id = frame_id.rsplit("/", 1)[-1]
    path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": frame_id,
                        "response": _response(observation_id, category, bbox, coarse_region),
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _response(
    observation_id: str,
    category: str,
    bbox: list[float],
    coarse_region: str = "upper_left",
) -> dict[str, object]:
    return {
        "schema": "raw_fpv_probe_response_v1",
        "candidates": [
            {
                "source_observation_id": observation_id,
                "category": category,
                "evidence_note": f"{category} visible in current frame",
                "confidence": 0.9,
                "locality": {
                    "bbox": bbox,
                    "coarse_region": coarse_region,
                    "surface_hint": "table",
                },
            }
        ],
    }

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
BUILDER = (
    REPO_ROOT / "scripts" / "visual_grounding" / "build_visual_grounding_corpus_from_cleanup_run.py"
)
REPRESENTATIVE_BUILDER = (
    REPO_ROOT / "scripts" / "visual_grounding" / "build_representative_visual_grounding_corpus.py"
)
BBOX_BUILDER = (
    REPO_ROOT / "scripts" / "visual_grounding" / "build_molmospaces_visual_grounding_bbox_corpus.py"
)


def test_builder_creates_path_backed_corpus_from_cleanup_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    image_dir = run_dir / "robot_views"
    image_dir.mkdir(parents=True)
    Image.new("RGB", (16, 12), (240, 240, 240)).save(image_dir / "0001_raw_fpv_001.fpv.png")
    run_result = {
        "scenario_id": "scenario-seed-7",
        "agent_view": {
            "static_fixture_projection": {
                "rooms": [
                    {
                        "room_id": "room_2",
                        "fixtures": [
                            {
                                "fixture_id": "sink_01",
                                "room_id": "room_2",
                                "category": "Sink",
                                "name": "Sink",
                                "affordances": ["place_inside"],
                                "pose": {"x": 1, "y": 2},
                            }
                        ],
                    }
                ]
            },
            "raw_fpv_observations": [
                {
                    "observation_id": "raw_fpv_001",
                    "waypoint_id": "room_2_scan_1",
                    "room_id": "room_2",
                    "artifact_status": "recorded",
                    "image_artifacts": {"fpv": "robot_views/0001_raw_fpv_001.fpv.png"},
                }
            ],
        },
        "private_evaluation": {
            "generated_mess_set": ["plate_abc_1_0_2", "remotecontrol_def_1_0_3"],
            "object_results": [
                {
                    "object_id": "plate_abc_1_0_2",
                    "object_category": "Plate",
                },
                {
                    "object_id": "remotecontrol_def_1_0_3",
                    "object_category": "RemoteControl",
                },
            ],
        },
    }
    (run_dir / "run_result.json").write_text(
        json.dumps(run_result),
        encoding="utf-8",
    )
    output = tmp_path / "corpus" / "raw_fpv_corpus.json"

    subprocess.run(
        [sys.executable, str(BUILDER), str(run_dir), "--output", str(output)],
        cwd=REPO_ROOT,
        check=True,
    )

    corpus = json.loads(output.read_text(encoding="utf-8"))
    assert corpus["schema"] == "visual_grounding_benchmark_corpus_v1"
    assert corpus["name"] == "scenario-seed-7-raw-fpv"
    assert corpus["label_source"] == "private_evaluation_room_presence"
    observation = corpus["observations"][0]
    assert observation["image"]["source"] == "path"
    assert observation["image"]["path"] == "raw_fpv/raw_fpv_001.png"
    assert observation["image"]["width"] == 16
    assert observation["image"]["height"] == 12
    assert (output.parent / observation["image"]["path"]).is_file()
    assert observation["static_fixture_projection"] == [
        {
            "fixture_id": "sink_01",
            "room_id": "room_2",
            "category": "Sink",
            "name": "Sink",
            "affordances": ["place_inside"],
        }
    ]
    assert observation["private_labels"] == [
        {
            "category": "dish",
            "category_family": "dish",
            "object_id": "plate_abc_1_0_2",
            "object_category": "Plate",
            "label_source": "private_evaluation_room_presence",
            "room_assignment_source": "object_id_suffix",
        }
    ]


def test_builder_prefers_mess_placement_fixture_room_over_object_id_suffix(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "seed-7"
    image_dir = run_dir / "robot_views"
    image_dir.mkdir(parents=True)
    Image.new("RGB", (16, 12), (240, 240, 240)).save(image_dir / "0001_raw_fpv_001.fpv.png")
    object_id = "remotecontrol_def_1_0_3"
    run_result = {
        "scenario_id": "scenario-seed-7",
        "agent_view": {
            "static_fixture_projection": {
                "rooms": [
                    {
                        "room_id": "room_2",
                        "fixtures": [
                            {
                                "fixture_id": "sink_01",
                                "room_id": "room_2",
                                "category": "Sink",
                                "name": "Sink",
                                "affordances": ["place_inside"],
                            }
                        ],
                    },
                    {
                        "room_id": "room_3",
                        "fixtures": [
                            {
                                "fixture_id": "shelf_03",
                                "room_id": "room_3",
                                "category": "Shelf",
                                "name": "Shelf",
                                "affordances": ["place"],
                            }
                        ],
                    },
                ]
            },
            "raw_fpv_observations": [
                {
                    "observation_id": "raw_fpv_001",
                    "waypoint_id": "room_2_scan_1",
                    "room_id": "room_2",
                    "artifact_status": "recorded",
                    "image_artifacts": {"fpv": "robot_views/0001_raw_fpv_001.fpv.png"},
                }
            ],
        },
        "mess_placement_diagnostics": [
            {
                "object_id": object_id,
                "receptacle_id": "sink_01",
            }
        ],
        "private_evaluation": {
            "generated_mess_set": [object_id],
            "object_results": [
                {
                    "object_id": object_id,
                    "object_category": "RemoteControl",
                }
            ],
        },
    }
    (run_dir / "run_result.json").write_text(
        json.dumps(run_result),
        encoding="utf-8",
    )
    output = tmp_path / "corpus" / "raw_fpv_corpus.json"

    subprocess.run(
        [sys.executable, str(BUILDER), str(run_dir), "--output", str(output)],
        cwd=REPO_ROOT,
        check=True,
    )

    corpus = json.loads(output.read_text(encoding="utf-8"))
    observation = corpus["observations"][0]
    assert observation["room_id"] == "room_2"
    assert observation["private_labels"] == [
        {
            "category": "electronics",
            "category_family": "electronics",
            "object_id": object_id,
            "object_category": "RemoteControl",
            "label_source": "private_evaluation_room_presence",
            "room_assignment_source": "mess_placement_fixture_room",
        }
    ]


def test_builder_rejects_malformed_run_result_source(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    run_result_path = run_dir / "run_result.json"
    run_result_path.write_text("{not json", encoding="utf-8")
    output = tmp_path / "corpus" / "raw_fpv_corpus.json"

    result = subprocess.run(
        [sys.executable, str(BUILDER), str(run_dir), "--output", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "cleanup run result source must contain valid JSON object" in result.stderr
    assert str(run_result_path) in result.stderr
    assert not output.exists()
    assert "Traceback" not in result.stderr


def test_builder_rejects_non_object_run_result_source(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    run_dir.mkdir()
    run_result_path = run_dir / "run_result.json"
    run_result_path.write_text("[]", encoding="utf-8")
    output = tmp_path / "corpus" / "raw_fpv_corpus.json"

    result = subprocess.run(
        [sys.executable, str(BUILDER), str(run_result_path), "--output", str(output)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    assert "cleanup run result source must contain a JSON object" in result.stderr
    assert str(run_result_path) in result.stderr
    assert not output.exists()
    assert "Traceback" not in result.stderr


def test_representative_builder_samples_multiple_runs_and_dedupes_images(
    tmp_path: Path,
) -> None:
    root = tmp_path / "runs"
    first = _write_raw_fpv_run(
        root / "run-a" / "seed-7",
        scenario_id="run-a",
        colors=[(240, 10, 10), (20, 220, 20), (30, 30, 230)],
        object_category="Plate",
        object_id="plate_a_1_0_2",
        room_id="room_2",
    )
    second = _write_raw_fpv_run(
        root / "run-b" / "seed-8",
        scenario_id="run-b",
        colors=[(240, 10, 10), (240, 220, 30), (40, 40, 40)],
        object_category="Book",
        object_id="book_b_1_0_3",
        room_id="room_3",
    )
    output = tmp_path / "corpus" / "representative.json"

    subprocess.run(
        [
            sys.executable,
            str(REPRESENTATIVE_BUILDER),
            str(root),
            "--output",
            str(output),
            "--min-raw-fpv",
            "1",
            "--max-observations",
            "10",
        ],
        cwd=REPO_ROOT,
        check=True,
    )

    corpus = json.loads(output.read_text(encoding="utf-8"))
    assert corpus["schema"] == "visual_grounding_benchmark_corpus_v1"
    assert corpus["source_run_results"] == [str(first), str(second)]
    assert corpus["sampling"]["candidate_observation_count"] == 6
    assert corpus["sampling"]["post_image_dedupe_observation_count"] == 5
    assert corpus["sampling"]["removed_duplicate_image_count"] == 1
    assert corpus["sampling"]["source_run_count"] == 2
    assert corpus["sampling"]["label_family_distribution"] == {"book": 2, "dish": 3}
    assert len(corpus["observations"]) == 5
    observation_ids = [item["observation_id"] for item in corpus["observations"]]
    assert observation_ids == [
        "raw_fpv_rep_001",
        "raw_fpv_rep_002",
        "raw_fpv_rep_003",
        "raw_fpv_rep_004",
        "raw_fpv_rep_005",
    ]
    for observation in corpus["observations"]:
        image_path = output.parent / observation["image"]["path"]
        assert image_path.is_file()
        assert observation["capture_context"]["source_image_sha256"]
        assert observation["capture_context"]["source_run_result"] in {str(first), str(second)}


def test_molmospaces_bbox_builder_normalizes_private_bbox_without_public_object_id() -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("bbox_builder", BBOX_BUILDER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    label = module.private_label_from_object_box(
        object_box={
            "bbox": [54, 36, 162, 108],
            "pixels": 512,
            "source": "segmentation",
        },
        obj={"object_id": "plate_private_1", "category": "Plate"},
        width=540,
        height=360,
        min_visible_pixels=20,
        scene_source="procthor-10k-val",
        scene_index=3,
        seed=7,
        target_index=2,
        frame_class="target_focused_fpv",
        camera="robot_0/head_camera",
    )

    assert label == {
        "label_source": "private_mujoco_segmentation_bbox",
        "visibility_source": "fpv_visibility",
        "object_id": "plate_private_1",
        "object_category": "Plate",
        "category": "dish",
        "category_family": "dish",
        "bbox": [0.1, 0.1, 0.2, 0.2],
        "bbox_xyxy_pixels": [54, 36, 162, 108],
        "visible_pixels": 512,
        "visible": True,
        "bbox_source": "segmentation",
        "scene_source": "procthor-10k-val",
        "scene_index": 3,
        "seed": 7,
        "target_index": 2,
        "frame_class": "target_focused_fpv",
        "camera": "robot_0/head_camera",
        "image_width": 540,
        "image_height": 360,
    }

    assert (
        module.private_label_from_object_box(
            object_box={"bbox": [1, 2, 3, 4], "pixels": 4},
            obj={"object_id": "plate_private_1", "category": "Plate"},
            width=540,
            height=360,
            min_visible_pixels=20,
            scene_source="procthor-10k-val",
            scene_index=3,
            seed=7,
            target_index=2,
            frame_class="target_focused_fpv",
            camera="robot_0/head_camera",
        )
        is None
    )


def test_molmospaces_bbox_observation_keeps_private_truth_out_of_public_context(
    tmp_path: Path,
) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location("bbox_builder", BBOX_BUILDER)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    image = tmp_path / "views" / "frame.fpv.png"
    image.parent.mkdir()
    Image.new("RGB", (540, 360), (20, 20, 20)).save(image)

    observation = module.observation_from_robot_view(
        output_dir=tmp_path,
        view_result={
            "status": "ok",
            "view_variant": "molmospaces-rby1m-fpv-map-chase-verify",
            "view_provenance": {"fpv": "rby1m_head_camera_target_framed"},
            "robot_pose": {"x": 1.0, "y": 2.0, "target_object_id": "plate_private_1"},
            "views": {"fpv": str(image)},
            "focus": {
                "fpv_visibility": {
                    "status": "ok",
                    "boxes": [
                        {
                            "bbox": [54, 36, 162, 108],
                            "pixels": 512,
                            "color": [239, 68, 68],
                            "source": "segmentation",
                        }
                    ],
                }
            },
        },
        scene_source="procthor-10k-val",
        scene_index=3,
        seed=7,
        target_index=2,
        frame_class="target_focused_fpv",
        obj={
            "object_id": "plate_private_1",
            "category": "Plate",
            "location_id": "sink_01",
        },
        source_receptacle={
            "receptacle_id": "sink_01",
            "room_area": "room_2",
            "category": "Sink",
        },
        static_fixture_projection_by_room={
            "room_2": [
                {
                    "fixture_id": "sink_01",
                    "room_id": "room_2",
                    "category": "Sink",
                    "name": "Sink",
                    "affordances": ["inside"],
                }
            ]
        },
        min_visible_pixels=20,
        include_invisible=False,
    )

    assert observation is not None
    public_blob = json.dumps(
        {
            "observation_id": observation["observation_id"],
            "waypoint_id": observation["waypoint_id"],
            "room_id": observation["room_id"],
            "capture_context": observation["capture_context"],
            "category_hints": observation["category_hints"],
            "static_fixture_projection": observation["static_fixture_projection"],
            "image": observation["image"],
        },
        sort_keys=True,
    )
    assert "plate_private_1" not in public_blob
    assert "bbox" not in public_blob.lower()
    assert "object_id" not in public_blob
    assert observation["private_labels"][0]["object_id"] == "plate_private_1"
    assert observation["private_labels"][0]["bbox"] == [0.1, 0.1, 0.2, 0.2]


def _write_raw_fpv_run(
    run_dir: Path,
    *,
    scenario_id: str,
    colors: list[tuple[int, int, int]],
    object_category: str,
    object_id: str,
    room_id: str,
) -> Path:
    image_dir = run_dir / "robot_views"
    image_dir.mkdir(parents=True)
    observations = []
    for index, color in enumerate(colors, start=1):
        image_name = f"{index:04d}_raw_fpv_{index:03d}.fpv.png"
        Image.new("RGB", (16, 12), color).save(image_dir / image_name)
        observations.append(
            {
                "observation_id": f"raw_fpv_{index:03d}",
                "waypoint_id": f"{room_id}_scan_{index}",
                "room_id": room_id,
                "artifact_status": "recorded",
                "image_artifacts": {"fpv": f"robot_views/{image_name}"},
            }
        )
    fixture_id = f"fixture_{room_id}"
    run_result = {
        "scenario_id": scenario_id,
        "agent_view": {
            "static_fixture_projection": {
                "rooms": [
                    {
                        "room_id": room_id,
                        "fixtures": [
                            {
                                "fixture_id": fixture_id,
                                "room_id": room_id,
                                "category": "Table",
                                "name": "Table",
                                "affordances": ["place_on"],
                            }
                        ],
                    }
                ]
            },
            "raw_fpv_observations": observations,
        },
        "mess_placement_diagnostics": [
            {
                "object_id": object_id,
                "receptacle_id": fixture_id,
            }
        ],
        "private_evaluation": {
            "generated_mess_set": [object_id],
            "object_results": [
                {
                    "object_id": object_id,
                    "object_category": object_category,
                }
            ],
        },
    }
    run_result_path = run_dir / "run_result.json"
    run_result_path.write_text(json.dumps(run_result), encoding="utf-8")
    return run_result_path

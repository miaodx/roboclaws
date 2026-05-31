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


def test_builder_creates_path_backed_corpus_from_cleanup_run(tmp_path: Path) -> None:
    run_dir = tmp_path / "seed-7"
    image_dir = run_dir / "robot_views"
    image_dir.mkdir(parents=True)
    Image.new("RGB", (16, 12), (240, 240, 240)).save(image_dir / "0001_raw_fpv_001.fpv.png")
    run_result = {
        "scenario_id": "scenario-seed-7",
        "agent_view": {
            "fixture_hints": {
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
    assert observation["fixture_hints"] == [
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
            "fixture_hints": {
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

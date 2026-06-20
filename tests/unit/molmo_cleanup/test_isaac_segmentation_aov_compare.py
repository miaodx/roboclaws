from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.isaac_lab_cleanup.compare_isaac_segmentation_aov import compare_states
from scripts.isaac_lab_cleanup.summarize_isaac_aov_matrix import summarize_entries

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPARE_SCRIPT = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "compare_isaac_segmentation_aov.py"
MATRIX_SCRIPT = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "summarize_isaac_aov_matrix.py"


def test_compare_states_identifies_candidate_tensor_collapse(tmp_path: Path) -> None:
    control = tmp_path / "control.json"
    candidate = tmp_path / "candidate.json"
    control.write_text(
        json.dumps(_state(unique_id_count=4, label="/world/objects/mug_01")), encoding="utf-8"
    )
    candidate.write_text(
        json.dumps(_state(unique_id_count=1, label="BACKGROUND")), encoding="utf-8"
    )

    result = compare_states(control_state_path=control, candidate_state_path=candidate)

    assert result["schema"] == "isaac_segmentation_aov_comparison_v1"
    assert result["status"] == "decision_ready"
    assert result["decision"]["first_divergent_layer"] == (
        "semantic_tensor_ids_collapsed_to_background"
    )
    assert result["decision"]["root_cause_classification"] == (
        "semantic_aov_rendered_geometry_not_labelled"
    )
    assert result["candidate"]["full_frame_background_view_count"] == 1
    assert result["control"]["non_background_label_count"] == 1
    assert result["candidate"]["label_application"]["gprim_label_count"] == 1
    assert result["candidate"]["label_application"]["mesh_label_count"] == 1


def test_aov_matrix_identifies_official_control_vs_molmospaces_collapse(
    tmp_path: Path,
) -> None:
    generated = tmp_path / "generated.json"
    official = tmp_path / "official.json"
    molmospaces = tmp_path / "molmospaces.json"
    preflight = tmp_path / "preflight.json"
    generated.write_text(
        json.dumps(
            _state(
                unique_id_count=4,
                label="/World/Objects/mug_01",
                loaded_asset_kind="generated_runtime_smoke_usd",
                generated_scene_kind="roboclaws_smoke",
            )
        ),
        encoding="utf-8",
    )
    official.write_text(
        json.dumps(
            _state(
                unique_id_count=4,
                label="asset,blue,cube,mug01",
                loaded_asset_kind="generated_runtime_smoke_usd",
                generated_scene_kind="isaac_official_blocks",
            )
        ),
        encoding="utf-8",
    )
    molmospaces.write_text(
        json.dumps(
            _state(
                unique_id_count=1,
                label="BACKGROUND",
                loaded_asset_kind="local_scene_usd",
                generated_scene_kind="",
                gprim_label_count=0,
                mesh_label_count=0,
            )
        ),
        encoding="utf-8",
    )
    preflight.write_text(
        json.dumps(
            {
                "schema": "roboclaws_isaac_lab_runtime_preflight_v1",
                "status": "ready",
                "runtime_dir": ".venv-isaaclab",
                "isaaclab_source": ".venv-isaaclab-src/IsaacLab",
                "checks": [],
            }
        ),
        encoding="utf-8",
    )

    result = summarize_entries(
        [
            f"A={generated}",
            f"B={official}",
            f"C={molmospaces}",
            f"D={preflight}",
        ]
    )

    assert result["schema"] == "isaac_segmentation_aov_matrix_v1"
    assert result["status"] == "decision_ready"
    assert result["decision"]["official_control_has_non_background"] is True
    assert result["decision"]["candidate_collapsed_to_background"] is True
    assert result["decision"]["candidate_labelled_gprims_or_meshes"] is False
    assert result["decision"]["root_cause_classification"] == (
        "molmospaces_scene_usd_semantic_aov_projection"
    )
    assert result["decision"]["runtime_preflight_count"] == 1


@pytest.mark.parametrize(
    ("bad_arg", "source", "message"),
    (
        ("--control-state", "{not-json\n", "state artifact must contain valid JSON object"),
        ("--control-state", "[]\n", "state artifact must contain a JSON object"),
        ("--candidate-state", "{not-json\n", "state artifact must contain valid JSON object"),
        ("--candidate-state", "[]\n", "state artifact must contain a JSON object"),
    ),
)
def test_aov_comparison_cli_rejects_bad_state_source(
    tmp_path: Path,
    bad_arg: str,
    source: str,
    message: str,
) -> None:
    control_path = tmp_path / "control_state.json"
    candidate_path = tmp_path / "candidate_state.json"
    output_path = tmp_path / "aov_comparison.json"
    control_path.write_text(
        json.dumps(_state(unique_id_count=4, label="/World/mug")), encoding="utf-8"
    )
    candidate_path.write_text(
        json.dumps(_state(unique_id_count=1, label="BACKGROUND")), encoding="utf-8"
    )
    bad_path = control_path if bad_arg == "--control-state" else candidate_path
    bad_path.write_text(source, encoding="utf-8")

    completed = _run_comparison(
        control_path=control_path,
        candidate_path=candidate_path,
        output_path=output_path,
    )

    assert completed.returncode == 2
    assert message in completed.stderr
    assert str(bad_path) in completed.stderr
    assert not output_path.exists()


@pytest.mark.parametrize(
    "missing_arg",
    ("--control-state", "--candidate-state"),
)
def test_aov_comparison_cli_rejects_missing_state_source(
    tmp_path: Path,
    missing_arg: str,
) -> None:
    control_path = tmp_path / "control_state.json"
    candidate_path = tmp_path / "candidate_state.json"
    output_path = tmp_path / "aov_comparison.json"
    control_path.write_text(
        json.dumps(_state(unique_id_count=4, label="/World/mug")), encoding="utf-8"
    )
    candidate_path.write_text(
        json.dumps(_state(unique_id_count=1, label="BACKGROUND")), encoding="utf-8"
    )
    missing_path = tmp_path / f"missing_{missing_arg.removeprefix('--')}.json"
    if missing_arg == "--control-state":
        control_path = missing_path
    else:
        candidate_path = missing_path

    completed = _run_comparison(
        control_path=control_path,
        candidate_path=candidate_path,
        output_path=output_path,
    )

    assert completed.returncode == 2
    assert "state artifact is missing" in completed.stderr
    assert str(missing_path) in completed.stderr
    assert not output_path.exists()


@pytest.mark.parametrize(
    ("source", "message"),
    (
        ("{not-json\n", "artifact must contain valid JSON object"),
        ("[]\n", "artifact must contain a JSON object"),
    ),
)
def test_aov_matrix_cli_rejects_bad_entry_source(
    tmp_path: Path,
    source: str,
    message: str,
) -> None:
    entry_path = tmp_path / "candidate_state.json"
    output_path = tmp_path / "aov_matrix.json"
    entry_path.write_text(source, encoding="utf-8")

    completed = _run_matrix(entry_path=entry_path, output_path=output_path)

    assert completed.returncode == 2
    assert message in completed.stderr
    assert str(entry_path) in completed.stderr
    assert not output_path.exists()


def test_aov_matrix_cli_rejects_missing_entry_source(tmp_path: Path) -> None:
    entry_path = tmp_path / "missing_candidate_state.json"
    output_path = tmp_path / "aov_matrix.json"

    completed = _run_matrix(entry_path=entry_path, output_path=output_path)

    assert completed.returncode == 2
    assert "artifact is missing" in completed.stderr
    assert str(entry_path) in completed.stderr
    assert not output_path.exists()


def _run_comparison(
    *,
    control_path: Path,
    candidate_path: Path,
    output_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(COMPARE_SCRIPT),
            "--control-state",
            str(control_path),
            "--candidate-state",
            str(candidate_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )


def _run_matrix(
    *,
    entry_path: Path,
    output_path: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(MATRIX_SCRIPT),
            "--entry",
            f"A={entry_path}",
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )


def _state(
    *,
    unique_id_count: int,
    label: str,
    loaded_asset_kind: str = "",
    generated_scene_kind: str = "",
    gprim_label_count: int = 1,
    mesh_label_count: int = 1,
) -> dict[str, object]:
    return {
        "scene_usd": "scene.usda",
        "scene_load": {"loaded_asset_kind": loaded_asset_kind},
        "real_runtime_smoke": {
            "stage_prim_count": 10,
            "generated_scene_kind": generated_scene_kind,
        },
        "segmentation": {
            "status": "available",
            "available": True,
            "output_data_types": ["semantic_segmentation"],
            "tensor_output_available": True,
            "candidate_bbox_count": 1,
            "selected_usd_prim_match_count": 1 if label.startswith("/") else 0,
            "semantic_label_application": {
                "status": "applied",
                "applied_count": 1,
                "failed_count": 0,
                "missing_prim_count": 0,
                "gprim_label_count": gprim_label_count,
                "mesh_label_count": mesh_label_count,
                "target_samples": [
                    {
                        "source_prim_path": "/World/Objects/bowl_01",
                        "target_prim_path": "/World/Objects/bowl_01/mesh",
                        "target_type": "Mesh",
                        "target_kind": "gprim:Mesh",
                    }
                ],
            },
            "candidate_bboxes": [
                {
                    "view": "fpv",
                    "data_type": "semantic_segmentation",
                    "label_id": 1,
                    "label": label,
                    "bbox_xyxy": [0, 0, 10, 10],
                    "pixel_count": 100,
                    "image_size": [10, 10],
                }
            ],
            "view_outputs": [
                {
                    "view": "fpv",
                    "outputs": {
                        "semantic_segmentation": {
                            "present": True,
                            "shape": [10, 10],
                            "dtype": "int32",
                            "label_count": 2,
                            "unique_id_count": unique_id_count,
                            "labels_available": True,
                        }
                    },
                    "candidate_bboxes": [
                        {
                            "view": "fpv",
                            "data_type": "semantic_segmentation",
                            "label_id": 1,
                            "label": label,
                            "bbox_xyxy": [0, 0, 10, 10],
                            "pixel_count": 100,
                            "image_size": [10, 10],
                        }
                    ],
                }
            ],
        },
    }

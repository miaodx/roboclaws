from __future__ import annotations

import json
from pathlib import Path

from scripts.isaac_lab_cleanup.compare_isaac_segmentation_aov import compare_states


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


def _state(*, unique_id_count: int, label: str) -> dict[str, object]:
    return {
        "scene_usd": "scene.usda",
        "real_runtime_smoke": {"stage_prim_count": 10},
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

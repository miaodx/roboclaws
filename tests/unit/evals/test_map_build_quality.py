from __future__ import annotations

from roboclaws.evals.map_build_quality import grade_runtime_metric_map_quality
from tests.support.eval_runtime_map import (
    quality_observed_objects,
    quality_public_anchors,
    quality_target_candidates,
)

QUALITY_CONFIG = {
    "min_public_semantic_anchors": 20,
    "min_generated_exploration_candidates": 7,
    "min_stable_semantic_anchor_categories": 8,
    "min_runtime_enrichment_anchors": 8,
    "min_observed_objects": 1,
    "min_target_candidates": 20,
    "require_semantic_enrichment_over_base": True,
    "max_duplicate_fixture_viewpoint_groups": 0,
    "forbid_rgb_only_object_pose": True,
    "require_runtime_metric_map_schema": "runtime_metric_map_v1",
    "require_private_truth_absent": True,
    "require_source_map_not_mutated": True,
    "min_sim_truth_fixture_category_recall": 1.0,
    "min_sim_truth_fixture_category_precision": 1.0,
    "min_sim_truth_best_view_waypoint_accuracy": 1.0,
}

PRIVATE_GOAL_REFERENCE = {
    "simulator_fixture_truth": {
        "categories": [
            "armchair",
            "bookshelf",
            "coffee table",
            "desk",
            "floor",
            "fridge",
            "kitchen sink",
            "laundry hamper",
            "sofa",
            "toy bin",
        ],
        "best_view_waypoint_truth": [
            {"category": "armchair", "waypoint_ids": ["room_3_inspection"]},
            {"category": "bookshelf", "waypoint_ids": ["room_3_inspection"]},
            {"category": "coffee table", "waypoint_ids": ["room_3_inspection"]},
            {"category": "desk", "waypoint_ids": ["room_4_inspection"]},
            {"category": "floor", "waypoint_ids": ["room_3_inspection"]},
            {"category": "fridge", "waypoint_ids": ["room_2_inspection"]},
            {"category": "kitchen sink", "waypoint_ids": ["room_2_inspection"]},
            {"category": "laundry hamper", "waypoint_ids": ["room_6_inspection"]},
            {"category": "sofa", "waypoint_ids": ["room_3_inspection"]},
            {"category": "toy bin", "waypoint_ids": ["room_3_inspection"]},
        ],
    }
}


def test_map_build_quality_passes_rich_viewpoint_only_runtime_map() -> None:
    outcome = grade_runtime_metric_map_quality(
        runtime_map=_quality_runtime_map(),
        runtime_map_exists=True,
        runtime_map_error="",
        config=QUALITY_CONFIG,
        private_goal_reference=PRIVATE_GOAL_REFERENCE,
    )

    assert outcome["status"] == "passed"
    assert outcome["public_semantic_anchor_count"] >= 20
    assert outcome["base_map_anchor_like_count"] == 12
    assert outcome["runtime_enrichment_anchor_count"] == 10
    assert outcome["semantic_enrichment_over_base"] is True
    assert outcome["stable_semantic_anchor_category_count"] == 10
    assert outcome["observed_object_count"] == 1
    assert outcome["target_candidate_count"] == 20
    assert outcome["observed_object_threshold_passed"] is True
    assert outcome["target_candidate_threshold_passed"] is True
    assert outcome["actionable_runtime_map_evidence"] is True
    assert outcome["duplicate_fixture_viewpoint_group_count"] == 0
    assert outcome["rgb_only_object_pose_claim_count"] == 0
    assert outcome["sim_truth_fixture_category_recall"] == 1.0
    assert outcome["sim_truth_fixture_category_precision"] == 1.0
    assert outcome["sim_truth_best_view_waypoint_accuracy"] == 1.0


def test_map_build_quality_accepts_target_candidates_without_observed_objects() -> None:
    runtime_map = _quality_runtime_map()
    runtime_map["observed_objects"] = []

    outcome = grade_runtime_metric_map_quality(
        runtime_map=runtime_map,
        runtime_map_exists=True,
        runtime_map_error="",
        config=QUALITY_CONFIG,
        private_goal_reference=PRIVATE_GOAL_REFERENCE,
    )

    assert outcome["status"] == "passed"
    assert outcome["observed_object_count"] == 0
    assert outcome["target_candidate_count"] == 20
    assert outcome["observed_object_threshold_passed"] is False
    assert outcome["target_candidate_threshold_passed"] is True
    assert outcome["actionable_runtime_map_evidence"] is True


def test_map_build_quality_rejects_sparse_duplicate_and_rgb_only_pose_claim() -> None:
    runtime_map = _quality_runtime_map()
    fixture_anchor = next(
        item
        for item in runtime_map["public_semantic_anchors"]
        if item.get("anchor_type") in {"fixture", "surface", "receptacle"}
    )
    runtime_map["public_semantic_anchors"] = [
        fixture_anchor,
        {**fixture_anchor, "anchor_id": "anchor_fixture_duplicate"},
    ]
    runtime_map["observed_objects"] = [
        {
            "object_id": "observed_bad_pose",
            "category": "book",
            "object_pose": {"x": 1.0, "y": 2.0, "yaw": 0.0},
        }
    ]
    runtime_map["target_candidates"] = []

    outcome = grade_runtime_metric_map_quality(
        runtime_map=runtime_map,
        runtime_map_exists=True,
        runtime_map_error="",
        config=QUALITY_CONFIG,
        private_goal_reference=PRIVATE_GOAL_REFERENCE,
    )

    assert outcome["status"] == "failed"
    assert outcome["failure_class"] == "map_actionability_failure"
    assert outcome["stable_semantic_anchor_category_count"] == 1
    assert outcome["semantic_enrichment_over_base"] is True
    assert outcome["target_candidate_count"] == 0
    assert outcome["actionable_runtime_map_evidence"] is True
    assert outcome["duplicate_fixture_viewpoint_group_count"] == 1
    assert outcome["rgb_only_object_pose_claim_count"] == 1


def test_map_build_quality_rejects_when_no_actionable_runtime_map_evidence() -> None:
    runtime_map = _quality_runtime_map()
    runtime_map["observed_objects"] = []
    runtime_map["target_candidates"] = []

    outcome = grade_runtime_metric_map_quality(
        runtime_map=runtime_map,
        runtime_map_exists=True,
        runtime_map_error="",
        config=QUALITY_CONFIG,
        private_goal_reference=PRIVATE_GOAL_REFERENCE,
    )

    assert outcome["status"] == "failed"
    assert outcome["failure_class"] == "map_actionability_failure"
    assert outcome["observed_object_threshold_passed"] is False
    assert outcome["target_candidate_threshold_passed"] is False
    assert outcome["actionable_runtime_map_evidence"] is False


def test_map_build_quality_rejects_wrong_best_view_waypoint_binding() -> None:
    runtime_map = _quality_runtime_map()
    for anchor in runtime_map["public_semantic_anchors"]:
        if anchor.get("anchor_type") in {"fixture", "surface", "receptacle"}:
            anchor["waypoint_id"] = "room_8_inspection"
            anchor["room_id"] = "room_8"
            anchor["pose"] = {"x": 10.7, "y": 3.2, "yaw": 0.0}

    outcome = grade_runtime_metric_map_quality(
        runtime_map=runtime_map,
        runtime_map_exists=True,
        runtime_map_error="",
        config=QUALITY_CONFIG,
        private_goal_reference=PRIVATE_GOAL_REFERENCE,
    )

    assert outcome["status"] == "failed"
    assert outcome["failure_class"] == "map_actionability_failure"
    assert outcome["sim_truth_fixture_category_recall"] == 1.0
    assert outcome["sim_truth_best_view_waypoint_accuracy"] < 1.0
    assert outcome["sim_truth_best_view_waypoint_mismatches"]


def _quality_runtime_map() -> dict:
    return {
        "schema": "runtime_metric_map_v1",
        "public_semantic_anchors": [
            {"anchor_id": f"anchor_room_{index}", "anchor_type": "room_area"}
            for index in range(1, 4)
        ]
        + quality_public_anchors(),
        "generated_exploration_candidates": [
            {"waypoint_id": f"generated_exploration_{index:03d}"} for index in range(1, 8)
        ],
        "observed_objects": quality_observed_objects(),
        "target_candidates": quality_target_candidates(),
        "private_truth_included": False,
        "source_map_mutated": False,
    }

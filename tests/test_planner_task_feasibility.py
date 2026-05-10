from __future__ import annotations

from roboclaws.molmo_cleanup.planner_task_feasibility import (
    grasp_feasibility_signature,
    grasp_feasibility_signature_counts,
    task_feasibility_blocker_kind,
    task_feasibility_blocker_summary,
)


def test_task_feasibility_signature_groups_repeated_grasp_blockers() -> None:
    diagnostics = {
        "robot_placement_attempt_count": 17,
        "robot_placement_failure_count": 0,
        "place_robot_near_call_count": 17,
        "grasp_failure_count": 17,
        "candidate_removal_count": 15,
        "image_artifacts": {"post_placement_attempt_001_head_camera": "view.png"},
        "grasp_failures": [
            {"object_name": "bread_1", "count_before": 0, "count_after": 1},
            {"object_name": "bread_1", "count_before": 1, "count_after": 2},
        ],
    }

    kind = task_feasibility_blocker_kind([], diagnostics)
    signature = grasp_feasibility_signature(diagnostics)
    groups = grasp_feasibility_signature_counts(
        [
            {
                "request_id": "proof_001",
                "object_id": "observed_001",
                "target_receptacle_id": "fridge_01",
                "report": "proofs/001/report.html",
                "grasp_feasibility_signature": signature,
            },
            {
                "request_id": "proof_002",
                "object_id": "observed_002",
                "target_receptacle_id": "fridge_01",
                "report": "proofs/002/report.html",
                "grasp_feasibility_signature": {
                    **signature,
                    "object_names": ["bread_2"],
                },
            },
        ]
    )

    assert kind == "grasp_feasibility"
    assert task_feasibility_blocker_summary(kind, diagnostics) == (
        "17 grasp failures; 15 candidate-removal calls"
    )
    assert signature["pattern_key"] == (
        '{"candidate_removal_count":15,"grasp_failure_count":17,'
        '"place_robot_near_call_count":17,"robot_placement_failure_count":0}'
    )
    assert signature["object_names"] == ["bread_1"]
    assert groups[0]["count"] == 2
    assert groups[0]["request_ids"] == ["proof_001", "proof_002"]
    assert groups[0]["object_names"] == ["bread_1", "bread_2"]


def test_grasp_summary_includes_candidate_removal_effectiveness_when_present() -> None:
    diagnostics = {
        "grasp_failure_count": 17,
        "candidate_removal_count": 15,
        "candidate_effective_removal_count": 0,
        "candidate_name_miss_count": 15,
        "grasp_threshold_exceeded_count": 15,
        "grasp_failures": [{"object_name": "bread_1"}],
    }

    kind = task_feasibility_blocker_kind([], diagnostics)
    signature = grasp_feasibility_signature(diagnostics)

    assert task_feasibility_blocker_summary(kind, diagnostics) == (
        "17 grasp failures; 15 candidate-removal calls; "
        "0 effective removals; 15 candidate-name misses"
    )
    assert signature["candidate_effective_removal_count"] == 0
    assert signature["candidate_name_miss_count"] == 15
    assert signature["grasp_threshold_exceeded_count"] == 15
    assert '"candidate_effective_removal_count":0' in signature["pattern_key"]

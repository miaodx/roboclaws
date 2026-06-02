from __future__ import annotations

from roboclaws.household.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)


def test_semantic_acceptability_marks_reasonable_non_private_targets() -> None:
    scenario = {
        "objects": [
            {
                "object_id": "pillow_6afe3635cad7781073478ce57191cfc3_1_0_3",
                "name": "Pillow",
                "category": "Pillow",
            },
            {
                "object_id": "bowl_46a21212675e4d90993a86b1232e6f40_1_0_8",
                "name": "Bowl",
                "category": "Bowl",
            },
            {
                "object_id": "book_be4d759484637aeb579b28e6a954b18d_1_0_8",
                "name": "Book",
                "category": "Book",
            },
        ],
        "receptacles": [
            {
                "receptacle_id": "bed_a830c3c80bd030e6cc4fe9d07eb42b2f_1_0_8",
                "name": "Bed (Bed|8|0)",
            },
            {
                "receptacle_id": "diningtable_15d4d7c88896632c7f36ae642a41eb46_1_0_4",
                "name": "DiningTable (DiningTable|4|0)",
            },
            {
                "receptacle_id": "countertop_aa26fd5b3d56251659034cbb8b20053d_1_0_2",
                "name": "CounterTop (CounterTop|2|0)",
            },
            {
                "receptacle_id": "desk_767b7ce268898119aaeb97804ba52bdd_1_0_7",
                "name": "Desk (Desk|7|0)",
            },
        ],
    }
    score = {
        "status": "failed",
        "restored_count": 0,
        "total_targets": 4,
        "success_threshold": 3,
        "restored_object_ids": [],
        "missed_object_ids": [
            "pillow_6afe3635cad7781073478ce57191cfc3_1_0_3",
            "bowl_46a21212675e4d90993a86b1232e6f40_1_0_8",
            "book_be4d759484637aeb579b28e6a954b18d_1_0_8",
        ],
        "object_results": [
            {
                "object_id": "pillow_6afe3635cad7781073478ce57191cfc3_1_0_3",
                "actual_location_id": "bed_a830c3c80bd030e6cc4fe9d07eb42b2f_1_0_8",
                "restored": False,
            },
            {
                "object_id": "bowl_46a21212675e4d90993a86b1232e6f40_1_0_8",
                "actual_location_id": "diningtable_15d4d7c88896632c7f36ae642a41eb46_1_0_4",
                "restored": False,
            },
            {
                "object_id": "bowl_46a21212675e4d90993a86b1232e6f40_1_0_8",
                "actual_location_id": "countertop_aa26fd5b3d56251659034cbb8b20053d_1_0_2",
                "restored": False,
            },
            {
                "object_id": "book_be4d759484637aeb579b28e6a954b18d_1_0_8",
                "actual_location_id": "desk_767b7ce268898119aaeb97804ba52bdd_1_0_7",
                "restored": False,
            },
        ],
    }

    annotated = annotate_score_with_semantic_acceptability(score, scenario)

    rows = annotated["object_results"]
    assert rows[0]["exact_private_match"] is False
    assert rows[0]["semantic_acceptability"] == "preferred"
    assert rows[1]["semantic_acceptability"] == "acceptable"
    assert rows[2]["semantic_acceptability"] == "preferred"
    assert rows[3]["semantic_acceptability"] == "acceptable"
    assert annotated["semantic_acceptability"]["accepted_count"] == 4
    assert annotated["semantic_acceptability"]["counts"] == {
        "preferred": 2,
        "acceptable": 2,
        "questionable": 0,
        "wrong": 0,
        "unknown": 0,
    }

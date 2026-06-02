from __future__ import annotations

import json

from roboclaws.household.policy import build_public_cleanup_plan
from roboclaws.household.scenario import build_cleanup_scenario


def test_public_cleanup_policy_restores_default_targets_without_private_manifest() -> None:
    scenario = build_cleanup_scenario(seed=7)
    public_payload = scenario.public_payload()

    plan = build_public_cleanup_plan(
        task_prompt="帮我整理这个房间",
        scene_payload=public_payload,
    )

    assert {action.object_id for action in plan} == {
        "mug_01",
        "book_01",
        "towel_01",
        "apple_01",
        "toy_car_01",
    }
    assert {action.receptacle_id for action in plan} == {
        "sink_01",
        "bookshelf_01",
        "laundry_hamper_01",
        "fridge_01",
        "toy_bin_01",
    }
    assert "valid_receptacle_ids" not in json.dumps(public_payload)
    assert "private_manifest" not in json.dumps(public_payload)


def test_public_cleanup_policy_skips_non_cleanup_prompt() -> None:
    scenario = build_cleanup_scenario(seed=7)

    plan = build_public_cleanup_plan(
        task_prompt="Count the objects in this room.",
        scene_payload=scenario.public_payload(),
    )

    assert plan == []


def test_public_cleanup_policy_skips_already_correct_objects() -> None:
    scenario = build_cleanup_scenario(seed=7)
    payload = scenario.public_payload()
    for obj in payload["objects"]:
        if obj["object_id"] == "book_01":
            obj["location_id"] = "bookshelf_01"

    plan = build_public_cleanup_plan(
        task_prompt="Clean up this room.",
        scene_payload=payload,
    )

    assert "book_01" not in {action.object_id for action in plan}


def test_public_cleanup_policy_does_not_need_scorer_fields() -> None:
    scenario = build_cleanup_scenario(seed=7)
    payload = scenario.public_payload()
    payload.pop("seed")
    payload.pop("scenario_id")

    plan = build_public_cleanup_plan(
        task_prompt="帮我收拾这个房间",
        scene_payload=payload,
    )

    assert len(plan) == 5

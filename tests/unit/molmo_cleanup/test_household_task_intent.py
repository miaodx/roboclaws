from __future__ import annotations

from types import SimpleNamespace

from roboclaws.household.task_intent import (
    household_intent_from_args,
    normalize_household_intent,
)


def test_current_household_intents_normalize_from_public_tokens() -> None:
    assert normalize_household_intent("household-world.cleanup") == "cleanup"
    assert normalize_household_intent("household-world.map-build") == "map-build"
    assert normalize_household_intent("open-ended") == "open-ended"


def test_removed_map_build_task_token_does_not_select_map_build_intent() -> None:
    assert normalize_household_intent("semantic-map-build") == "cleanup"


def test_household_intent_from_args_ignores_removed_task_name_field() -> None:
    args = SimpleNamespace(task_name="semantic-map-build", intent="")

    assert household_intent_from_args(args, env={}, fallback="cleanup") == "cleanup"

"""Shared household task-intent mode helpers."""

from __future__ import annotations

from typing import Any

TASK_INTENT_MODE_DEFAULT = "default_cleanup"
TASK_INTENT_MODES = frozenset({TASK_INTENT_MODE_DEFAULT})
HOUSEHOLD_INTENT_CLEANUP = "cleanup"
HOUSEHOLD_INTENT_MAP_BUILD = "map-build"
HOUSEHOLD_INTENT_OPEN_ENDED = "open-ended"


def normalize_task_intent_mode(_value: str | None) -> str:
    return TASK_INTENT_MODE_DEFAULT


def normalize_household_intent(value: str | None, *, task_name: str = "") -> str:
    """Normalize the first-class household intent.

    Legacy task-intent aliases are tolerated only as historical artifact input;
    current runtime semantics use ``intent=open-ended``.
    """

    normalized = str(value or "").strip().lower().replace("_", "-")
    if normalized in {"open-ended", "open-ended-task", "operator-task", "custom", "custom-task"}:
        return HOUSEHOLD_INTENT_OPEN_ENDED
    if normalized in {"map-build", "semantic-map-build"}:
        return HOUSEHOLD_INTENT_MAP_BUILD
    if normalized == HOUSEHOLD_INTENT_CLEANUP:
        return HOUSEHOLD_INTENT_CLEANUP
    if task_name == "semantic-map-build":
        return HOUSEHOLD_INTENT_MAP_BUILD
    return HOUSEHOLD_INTENT_CLEANUP


def household_intent_from_goal_contract(goal_contract: Any | None, *, fallback: str = "") -> str:
    if goal_contract is None:
        return normalize_household_intent(fallback)
    return normalize_household_intent(str(getattr(goal_contract, "intent", "") or fallback))


def household_intent_is_open_ended(value: str | None) -> bool:
    return normalize_household_intent(value) == HOUSEHOLD_INTENT_OPEN_ENDED

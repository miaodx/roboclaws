"""Shared household task-intent mode helpers."""

from __future__ import annotations

TASK_INTENT_MODE_DEFAULT = "default_cleanup"
TASK_INTENT_MODE_CUSTOM = "custom"
TASK_INTENT_MODES = frozenset({TASK_INTENT_MODE_DEFAULT, TASK_INTENT_MODE_CUSTOM})


def normalize_task_intent_mode(value: str | None) -> str:
    normalized = str(value or TASK_INTENT_MODE_DEFAULT).strip().lower().replace("_", "-")
    if normalized in {"custom", "operator-custom", "custom-task"}:
        return TASK_INTENT_MODE_CUSTOM
    return TASK_INTENT_MODE_DEFAULT


def task_intent_is_custom(value: str | None) -> bool:
    return normalize_task_intent_mode(value) == TASK_INTENT_MODE_CUSTOM

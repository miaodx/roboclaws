from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CleanupAction:
    object_id: str
    receptacle_id: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "object_id": self.object_id,
            "receptacle_id": self.receptacle_id,
            "reason": self.reason,
        }


_CLEANUP_INTENT_TERMS = ("clean", "tidy", "organize", "整理", "收拾")

_CATEGORY_TARGET_KEYWORDS: dict[str, tuple[str, ...]] = {
    "dish": ("sink",),
    "book": ("bookshelf", "shelf"),
    "linen": ("laundry hamper", "hamper"),
    "food": ("fridge", "refrigerator"),
    "toy": ("toy bin", "bin"),
}

_NAME_TARGET_KEYWORDS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("mug", "cup", "plate", "dish"), ("sink",)),
    (("book", "paperback"), ("bookshelf", "shelf")),
    (("towel", "linen", "cloth"), ("laundry hamper", "hamper")),
    (("apple", "food", "fruit"), ("fridge", "refrigerator")),
    (("toy",), ("toy bin", "bin")),
)


def build_public_cleanup_plan(
    *,
    task_prompt: str,
    scene_payload: dict[str, Any],
) -> list[CleanupAction]:
    """Plan cleanup moves from public task/object/receptacle data only."""
    if not _looks_like_cleanup(task_prompt):
        return []
    objects = _as_list(scene_payload.get("objects"))
    receptacles = _as_list(scene_payload.get("receptacles"))
    receptacle_by_keyword = _index_receptacles_by_keyword(receptacles)

    actions: list[CleanupAction] = []
    for obj in objects:
        if not obj.get("pickupable", True):
            continue
        target = _infer_target_receptacle(obj, receptacle_by_keyword)
        if target is None:
            continue
        if obj.get("location_id") == target["receptacle_id"]:
            continue
        actions.append(
            CleanupAction(
                object_id=str(obj["object_id"]),
                receptacle_id=str(target["receptacle_id"]),
                reason=_reason_for(obj, target),
            )
        )
    return actions


def _looks_like_cleanup(task_prompt: str) -> bool:
    lowered = task_prompt.lower()
    return any(term in lowered for term in _CLEANUP_INTENT_TERMS)


def _as_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _index_receptacles_by_keyword(
    receptacles: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    by_keyword: dict[str, dict[str, Any]] = {}
    for receptacle in receptacles:
        name = str(receptacle.get("name", "")).lower()
        receptacle_id = str(receptacle.get("receptacle_id", "")).lower()
        for keyword in _all_target_keywords():
            if keyword in name or keyword.replace(" ", "_") in receptacle_id:
                by_keyword.setdefault(keyword, receptacle)
    return by_keyword


def _all_target_keywords() -> set[str]:
    keywords: set[str] = set()
    for values in _CATEGORY_TARGET_KEYWORDS.values():
        keywords.update(values)
    for _object_terms, targets in _NAME_TARGET_KEYWORDS:
        keywords.update(targets)
    return keywords


def _infer_target_receptacle(
    obj: dict[str, Any],
    receptacle_by_keyword: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    category = str(obj.get("category", "")).lower()
    for keyword in _CATEGORY_TARGET_KEYWORDS.get(category, ()):
        if keyword in receptacle_by_keyword:
            return receptacle_by_keyword[keyword]

    name = str(obj.get("name", "")).lower()
    for object_terms, target_keywords in _NAME_TARGET_KEYWORDS:
        if not any(term in name for term in object_terms):
            continue
        for keyword in target_keywords:
            if keyword in receptacle_by_keyword:
                return receptacle_by_keyword[keyword]
    return None


def _reason_for(obj: dict[str, Any], receptacle: dict[str, Any]) -> str:
    return (
        f"{obj.get('name', obj.get('object_id'))} belongs near "
        f"{receptacle.get('name', receptacle.get('receptacle_id'))}"
    )

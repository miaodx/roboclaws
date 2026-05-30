from __future__ import annotations

import math
import random
from collections.abc import Sequence
from typing import Any

TARGET_RULES: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("Cup", "Mug", "Plate", "Bowl"), ("Sink",)),
    (("Book", "Newspaper"), ("ShelvingUnit", "Desk")),
    (("Apple", "Bread", "Egg", "Potato", "Lettuce"), ("Fridge",)),
    (("RemoteControl",), ("TVStand",)),
    (("Pillow", "TeddyBear"), ("Bed", "Sofa")),
)


def select_generated_mess_targets(
    objects: list[dict[str, Any]],
    receptacles: list[dict[str, Any]],
    *,
    target_count: int,
    seed: int | None = None,
    object_ids: Sequence[str] | None = None,
) -> list[dict[str, Any]]:
    """Select a diverse hidden Generated Mess Set from public scene metadata."""
    if target_count < 1:
        raise ValueError("target_count must be >= 1")
    if object_ids is not None:
        return select_explicit_generated_mess_targets(
            objects,
            receptacles,
            object_ids=object_ids,
            target_count=target_count,
        )

    rng = random.Random(seed) if seed is not None else None
    selected = []
    used: set[str] = set()
    eligible_rules = []
    for object_categories, receptacle_categories in TARGET_RULES:
        receptacle = first_receptacle_for_categories(receptacles, receptacle_categories)
        if receptacle is None:
            continue
        rule_objects = [item for item in objects if item["category"] in object_categories]
        if rng is not None:
            rule_objects = sorted(rule_objects, key=lambda item: str(item["object_id"]))
            rng.shuffle(rule_objects)
        if rule_objects:
            eligible_rules.append((rule_objects, receptacle))

    while len(selected) < target_count:
        made_progress = False
        for rule_objects, receptacle in eligible_rules:
            obj = next(
                (item for item in rule_objects if item["object_id"] not in used),
                None,
            )
            if obj is None:
                continue
            selected_obj = dict(obj)
            selected_obj["target_receptacle_id"] = receptacle["receptacle_id"]
            selected.append(selected_obj)
            used.add(selected_obj["object_id"])
            made_progress = True
            if len(selected) >= target_count:
                break
        if not made_progress:
            break
    return selected


def select_explicit_generated_mess_targets(
    objects: list[dict[str, Any]],
    receptacles: list[dict[str, Any]],
    *,
    object_ids: Sequence[str],
    target_count: int,
) -> list[dict[str, Any]]:
    """Select an exact hidden Generated Mess Set by object id."""
    requested_ids = tuple(str(object_id) for object_id in object_ids if str(object_id))
    if len(requested_ids) != target_count:
        raise ValueError(
            "explicit generated mess object id count must match target_count "
            f"({len(requested_ids)} != {target_count})"
        )
    object_by_id = {str(item["object_id"]): item for item in objects}
    selected: list[dict[str, Any]] = []
    for object_id in requested_ids:
        obj = object_by_id.get(object_id)
        if obj is None:
            raise ValueError(f"explicit generated mess object id is unavailable: {object_id}")
        receptacle = target_receptacle_for_object(obj, receptacles)
        if receptacle is None:
            category = str(obj.get("category") or "")
            raise ValueError(
                "explicit generated mess object id has no cleanup target receptacle: "
                f"{object_id} ({category})"
            )
        selected_obj = dict(obj)
        selected_obj["target_receptacle_id"] = receptacle["receptacle_id"]
        selected.append(selected_obj)
    return selected


def target_receptacle_for_object(
    obj: dict[str, Any],
    receptacles: list[dict[str, Any]],
) -> dict[str, Any] | None:
    category = str(obj.get("category") or "")
    for object_categories, receptacle_categories in TARGET_RULES:
        if category not in object_categories:
            continue
        return first_receptacle_for_categories(receptacles, receptacle_categories)
    return None


def first_receptacle_for_categories(
    receptacles: list[dict[str, Any]],
    categories: tuple[str, ...],
) -> dict[str, Any] | None:
    for category in categories:
        for receptacle in receptacles:
            if receptacle["category"] == category:
                return receptacle
    return None


def generated_mess_success_threshold(target_count: int) -> int:
    return max(1, math.ceil(target_count * 0.70))

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from roboclaws.household.types import CleanupScenario


def room_outline_from_usd_prim(
    prim_path: str,
    prim: Any,
    *,
    usd_geom: Any,
    world_bounds: Callable[..., dict[str, Any] | None],
) -> dict[str, Any] | None:
    match = re.search(r"/(room_\d+)_visual(?:_\d+)?$", prim_path)
    if match is None:
        return None
    bounds = world_bounds(prim, usd_geom=usd_geom)
    if bounds is None:
        return None
    center = _vec3(bounds.get("center"))
    size = _vec3(bounds.get("size"))
    if center is None or size is None:
        return None
    half_extents = [abs(size[0]) / 2.0, abs(size[1]) / 2.0]
    if min(half_extents) < 0.25:
        return None
    room_id = match.group(1)
    return {
        "room_id": room_id,
        "label": room_id.replace("_", " ").title(),
        "center": [round(center[0], 6), round(center[1], 6)],
        "half_extents": [round(half_extents[0], 6), round(half_extents[1], 6)],
        "provenance": "isaac_usd_room_mesh_world_bounds",
        "usd_prim_path": prim_path,
    }


def room_outlines_from_scene_index_diagnostics(
    diagnostics: dict[str, Any],
) -> list[dict[str, Any]]:
    return [dict(item) for item in diagnostics.get("room_outlines") or [] if isinstance(item, dict)]


def fallback_room_outlines_from_indices(
    *,
    scenario: CleanupScenario,
    object_index: dict[str, dict[str, Any]],
    receptacle_index: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[list[float]]] = {}
    room_by_receptacle = {
        item.receptacle_id: str(item.room_area or "isaac_scene") for item in scenario.receptacles
    }
    for receptacle in scenario.receptacles:
        position = _support_pose_position(
            _dict(_dict(receptacle_index.get(receptacle.receptacle_id)).get("support_pose"))
        )
        if position is None:
            position = _vec3(
                _dict(
                    _dict(receptacle_index.get(receptacle.receptacle_id)).get("usd_world_bounds")
                ).get("center")
            )
        if position is None:
            continue
        grouped.setdefault(room_by_receptacle[receptacle.receptacle_id], []).append(position)
    for obj in scenario.objects:
        position = _vec3(
            _dict(_dict(object_index.get(obj.object_id)).get("usd_world_bounds")).get("center")
        )
        if position is None:
            continue
        grouped.setdefault(room_by_receptacle.get(obj.location_id, "isaac_scene"), []).append(
            position
        )
    outlines = []
    for room_id, points in grouped.items():
        if not points:
            continue
        xs = [float(point[0]) for point in points]
        ys = [float(point[1]) for point in points]
        center = [round((min(xs) + max(xs)) / 2.0, 6), round((min(ys) + max(ys)) / 2.0, 6)]
        half_extents = [
            round(max((max(xs) - min(xs)) / 2.0, 0.8), 6),
            round(max((max(ys) - min(ys)) / 2.0, 0.8), 6),
        ]
        outlines.append(
            {
                "room_id": room_id,
                "label": room_id.replace("_", " ").title(),
                "center": center,
                "half_extents": half_extents,
                "provenance": "scenario_fixture_room_bounds",
            }
        )
    return sorted(outlines, key=lambda item: str(item.get("room_id") or ""))


def round_vec3(values: list[float] | tuple[float, ...]) -> list[float]:
    return [round(float(value), 6) for value in values[:3]]


def authored_reference_asset_paths(*, usd_path: Path, prim: Any) -> list[str]:
    assets: list[str] = []
    for spec in prim.GetPrimStack():
        reference_list = getattr(spec, "referenceList", None)
        for reference in usd_list_op_items(reference_list):
            asset_path = str(getattr(reference, "assetPath", "") or "")
            if not asset_path:
                continue
            layer_path = Path(str(getattr(spec.layer, "realPath", "") or usd_path))
            if not is_local_reference_asset_path(asset_path):
                assets.append(asset_path)
            else:
                assets.append(str((layer_path.parent / asset_path).resolve()))
    return sorted(dict.fromkeys(assets))


def usd_list_op_items(list_op: Any) -> list[Any]:
    items: list[Any] = []
    for attr in ("prependedItems", "addedItems", "appendedItems", "explicitItems"):
        values = getattr(list_op, attr, None)
        if values:
            items.extend(list(values))
    return items


def is_local_reference_asset_path(asset_path: str) -> bool:
    return "://" not in asset_path and not asset_path.startswith("@")


def local_reference_asset_missing(asset_path: str) -> bool:
    return is_local_reference_asset_path(asset_path) and not Path(asset_path).exists()


def _support_pose_position(pose: dict[str, Any]) -> list[float] | None:
    try:
        return [float(pose["x"]), float(pose["y"]), float(pose.get("z", 0.0))]
    except (KeyError, TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None

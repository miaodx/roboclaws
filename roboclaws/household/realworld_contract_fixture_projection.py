from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

_OBJECT_CATEGORY_TARGETS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("dish", "cup", "mug", "plate", "bowl", "utensil", "fork", "knife", "spoon"),
        ("sink", "countertop"),
    ),
    (
        ("book", "newspaper", "notebook", "paper", "magazine"),
        ("shelvingunit", "bookshelf", "shelf", "desk"),
    ),
    (
        (
            "food",
            "apple",
            "bread",
            "egg",
            "potato",
            "lettuce",
            "tomato",
            "banana",
            "orange",
            "fruit",
            "vegetable",
            "produce",
        ),
        ("fridge", "refrigerator"),
    ),
    (
        (
            "remotecontrol",
            "remote",
            "electronics",
            "phone",
            "cellphone",
            "smartphone",
            "mobilephone",
            "laptop",
            "computer",
            "tablet",
            "controller",
            "alarmclock",
            "clock",
        ),
        ("tvstand", "tv stand"),
    ),
    (("pillow", "teddybear", "teddy", "plush", "cushion"), ("bed", "sofa")),
    (
        ("linen", "towel", "cloth", "blanket", "shirt", "clothing", "clothes"),
        ("laundryhamper", "laundry hamper", "hamper"),
    ),
    (
        ("toy", "toycar", "ball", "basketball", "soccer", "game", "teddybear", "teddy", "plush"),
        ("toybin", "toy bin"),
    ),
)

_INSIDE_DESTINATION_CATEGORY_TERMS = frozenset(
    {
        "bookcase",
        "bookshelf",
        "fridge",
        "refrigerator",
        "shelf",
        "shelving",
        "shelvingunit",
    }
)


def _polygon_center_world(polygon: list[Any]) -> dict[str, float]:
    points = [point for point in polygon if isinstance(point, dict)]
    if not points:
        return {"x": 0.0, "y": 0.0}
    return {
        "x": round(sum(float(point.get("x", 0.0)) for point in points) / len(points), 3),
        "y": round(sum(float(point.get("y", 0.0)) for point in points) / len(points), 3),
    }


def _rooms_from_fixtures(fixtures: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    by_room: dict[str, list[str]] = defaultdict(list)
    labels: dict[str, str] = {}
    for fixture_id, fixture in fixtures.items():
        raw_room = str(fixture.get("room_area", "unknown"))
        room_id = _room_id(raw_room)
        by_room[room_id].append(fixture_id)
        labels[room_id] = raw_room.replace("_", " ")
    rooms = []
    for index, (room_id, fixture_ids) in enumerate(sorted(by_room.items())):
        outline = _room_outline_by_id_from_fixtures(fixtures, room_id, fixture_ids)
        if outline is not None:
            polygon = _polygon_from_room_outline(outline)
            center_xy = _room_outline_center(outline)
            room_label = str(outline.get("label") or labels[room_id])
            map_center = {"x": center_xy[0], "y": center_xy[1]}
        else:
            x0 = float(index * 3)
            polygon = [
                {"x": x0, "y": 0.0},
                {"x": x0 + 2.0, "y": 0.0},
                {"x": x0 + 2.0, "y": 2.0},
                {"x": x0, "y": 2.0},
            ]
            room_label = labels[room_id]
            map_center = {"x": x0 + 1.0, "y": 1.0}
        rooms.append(
            {
                "room_id": room_id,
                "room_label": room_label,
                "fixture_ids": sorted(fixture_ids),
                "polygon": polygon,
                "map_center": map_center,
                "fixture_navigation_obstacles": _fixture_navigation_obstacles(
                    fixtures,
                    fixture_ids,
                ),
                **_room_outline_metadata(outline),
            }
        )
    return rooms


def _inspection_waypoints(rooms: list[dict[str, Any]]) -> list[dict[str, Any]]:
    waypoints = []
    for room in rooms:
        fixture_ids = list(room["fixture_ids"])
        groups = _split_fixture_groups(fixture_ids)
        slots = _waypoint_slots_for_room(room, len(groups))
        for index, group in enumerate(groups, start=1):
            x, y = slots[index - 1]
            waypoints.append(
                {
                    "waypoint_id": f"{room['room_id']}_scan_{index}",
                    "room_id": room["room_id"],
                    "label": f"{room['room_label']} scan {index}",
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "yaw": 0.0,
                    "fixture_ids": group,
                    "purpose": "fixture_coverage",
                    "waypoint_source": "static_map_coverage",
                    "coverage_estimate": round(1.0 / max(len(groups), 1), 2),
                }
            )
    return waypoints


def _room_outline_by_id_from_fixtures(
    fixtures: dict[str, dict[str, Any]],
    room_id: str,
    fixture_ids: list[str],
) -> dict[str, Any] | None:
    for fixture_id in fixture_ids:
        outline = fixtures.get(fixture_id, {}).get("scene_room_outline")
        if isinstance(outline, dict) and str(outline.get("room_id") or "") == room_id:
            return dict(outline)
    return None


def _polygon_from_room_outline(outline: dict[str, Any]) -> list[dict[str, float]]:
    center = _vec2(outline.get("center"))
    half_extents = _vec2(outline.get("half_extents"))
    if center is None or half_extents is None:
        return []
    cx, cy = center
    hx, hy = abs(half_extents[0]), abs(half_extents[1])
    return [
        {"x": round(cx - hx, 6), "y": round(cy - hy, 6)},
        {"x": round(cx + hx, 6), "y": round(cy - hy, 6)},
        {"x": round(cx + hx, 6), "y": round(cy + hy, 6)},
        {"x": round(cx - hx, 6), "y": round(cy + hy, 6)},
    ]


def _room_outline_center(outline: dict[str, Any]) -> tuple[float, float]:
    center = _vec2(outline.get("center"))
    if center is None:
        return (0.0, 0.0)
    return (round(center[0], 6), round(center[1], 6))


def _room_outline_metadata(outline: dict[str, Any] | None) -> dict[str, Any]:
    if outline is None:
        return {}
    return {
        "scene_room_outline": {
            "room_id": str(outline.get("room_id") or ""),
            "center": list(_room_outline_center(outline)),
            "half_extents": list(_vec2(outline.get("half_extents")) or (0.0, 0.0)),
            "provenance": str(outline.get("provenance") or "scene_room_outline"),
            "usd_prim_path": str(outline.get("usd_prim_path") or ""),
        }
    }


def _room_polygon_bounds(room: dict[str, Any] | None) -> dict[str, float] | None:
    if room is None:
        return None
    polygon = room.get("polygon") or []
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        center = room.get("map_center") or {}
        if "x" not in center or "y" not in center:
            return None
        x = float(center.get("x", 0.0))
        y = float(center.get("y", 0.0))
        return {"min_x": x - 1.0, "max_x": x + 1.0, "min_y": y - 1.0, "max_y": y + 1.0}
    return {
        "min_x": round(min(xs), 6),
        "max_x": round(max(xs), 6),
        "min_y": round(min(ys), 6),
        "max_y": round(max(ys), 6),
    }


def _waypoint_slots_for_room(
    room: dict[str, Any],
    count: int,
) -> list[tuple[float, float]]:
    count = max(1, int(count))
    polygon = room.get("polygon") or []
    xs = [float(point.get("x", 0.0)) for point in polygon if isinstance(point, dict)]
    ys = [float(point.get("y", 0.0)) for point in polygon if isinstance(point, dict)]
    if not xs or not ys:
        center = room.get("map_center") or {}
        x = float(center.get("x", 0.0))
        y = float(center.get("y", 0.0))
        return [(x, y + index * 0.45) for index in range(count)]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    center = room.get("map_center") or {}
    x = float(center.get("x", (min_x + max_x) / 2.0))
    y = float(center.get("y", (min_y + max_y) / 2.0))
    if isinstance(room.get("scene_room_outline"), dict):
        return _scene_outline_waypoint_slots_for_room(
            room,
            count=count,
            center=(x, y),
            bounds=(min_x, max_x, min_y, max_y),
        )
    if count == 1:
        return [(round(x, 3), round(y, 3))]
    margin = min(0.75, max((max_y - min_y) * 0.15, 0.25))
    start_y = min_y + margin
    end_y = max_y - margin
    if end_y < start_y:
        start_y = end_y = y
    step = (end_y - start_y) / max(count - 1, 1)
    return [(round(x, 3), round(start_y + step * index, 3)) for index in range(count)]


def _scene_outline_waypoint_slots_for_room(
    room: dict[str, Any],
    *,
    count: int,
    center: tuple[float, float],
    bounds: tuple[float, float, float, float],
) -> list[tuple[float, float]]:
    min_x, max_x, min_y, max_y = bounds
    width = max_x - min_x
    depth = max_y - min_y
    radius = min(0.8, max(min(width, depth) * 0.12, 0.35))
    candidates = _scene_outline_waypoint_candidates(center, radius)
    obstacles = [
        item for item in room.get("fixture_navigation_obstacles") or [] if isinstance(item, dict)
    ]
    slots: list[tuple[float, float]] = []
    for raw_x, raw_y in candidates:
        x = _clamp(raw_x, min_x + 0.35, max_x - 0.35)
        y = _clamp(raw_y, min_y + 0.35, max_y - 0.35)
        if _point_overlaps_fixture_obstacle(x, y, obstacles):
            continue
        point = (round(x, 3), round(y, 3))
        if point not in slots:
            slots.append(point)
        if len(slots) >= count:
            return slots
    fallback = (round(center[0], 3), round(center[1], 3))
    if not slots:
        slots.append(fallback)
    while len(slots) < count:
        slots.append(slots[len(slots) % len(slots)])
    return slots[:count]


def _scene_outline_waypoint_candidates(
    center: tuple[float, float],
    radius: float,
) -> list[tuple[float, float]]:
    cx, cy = center
    return [
        (cx, cy),
        (cx, cy - radius),
        (cx, cy + radius),
        (cx - radius, cy),
        (cx + radius, cy),
        (cx - radius, cy - radius),
        (cx + radius, cy - radius),
        (cx - radius, cy + radius),
        (cx + radius, cy + radius),
        (cx, cy - radius * 1.6),
        (cx, cy + radius * 1.6),
        (cx - radius * 1.6, cy),
        (cx + radius * 1.6, cy),
    ]


def _fixture_navigation_obstacles(
    fixtures: dict[str, dict[str, Any]],
    fixture_ids: list[str],
) -> list[dict[str, float]]:
    obstacles = []
    for fixture_id in fixture_ids:
        fixture = fixtures.get(fixture_id, {})
        pose = fixture.get("pose") if isinstance(fixture.get("pose"), dict) else {}
        if not pose:
            continue
        footprint = _fixture_footprint(fixture_id)
        obstacles.append(
            {
                "x": float(pose.get("x", 0.0)),
                "y": float(pose.get("y", 0.0)),
                "half_width": float(footprint.get("width_m") or 0.45) / 2.0,
                "half_depth": float(footprint.get("depth_m") or 0.35) / 2.0,
            }
        )
    return obstacles


def _point_overlaps_fixture_obstacle(
    x: float,
    y: float,
    obstacles: list[dict[str, float]],
) -> bool:
    clearance_m = 0.2
    for obstacle in obstacles:
        if (
            abs(x - obstacle["x"]) <= obstacle["half_width"] + clearance_m
            and abs(y - obstacle["y"]) <= obstacle["half_depth"] + clearance_m
        ):
            return True
    return False


def _split_fixture_groups(fixture_ids: list[str]) -> list[list[str]]:
    if len(fixture_ids) <= 1:
        return [fixture_ids, fixture_ids]
    return [fixture_ids[::2], fixture_ids[1::2]]


def _driveable_ways(rooms: list[dict[str, Any]]) -> list[dict[str, str]]:
    ways = []
    for previous, current in zip(rooms, rooms[1:]):
        ways.append(
            {
                "from_room_id": str(previous["room_id"]),
                "to_room_id": str(current["room_id"]),
                "kind": "doorway",
            }
        )
    return ways


def _fixture_affordances(fixture: dict[str, Any]) -> list[str]:
    affordances = ["place"]
    if _fixture_requires_open(fixture):
        affordances.extend(["open", "place_inside", "close"])
    elif _fixture_is_open_container(fixture):
        affordances.append("place_inside")
    return affordances


def _recommended_place_tool(fixture_id: str, fixtures: dict[str, dict[str, Any]]) -> str:
    fixture = fixtures.get(fixture_id, {})
    return "place_inside" if _fixture_prefers_inside(fixture) else "place"


def _public_destination_policy_for_category(category: Any) -> dict[str, Any]:
    category_norm = _norm(category)
    preferred: tuple[str, ...] = ()
    for object_aliases, fixture_aliases in _OBJECT_CATEGORY_TARGETS:
        if any(_norm(alias) and _norm(alias) in category_norm for alias in object_aliases):
            preferred = fixture_aliases
            break
    if not preferred:
        preferred = (
            "countertop",
            "table",
            "desk",
        )
    normalized = [_normalize_fixture_category_label(item) for item in preferred]
    normalized = [
        item for index, item in enumerate(normalized) if item and item not in normalized[:index]
    ]
    placement_tool_by_category = {
        item: _public_destination_policy_tool_for_fixture_category(item) for item in normalized
    }
    placement_tool = (
        placement_tool_by_category.get(normalized[0], "place") if normalized else "place"
    )
    return {
        "schema": "public_cleanup_destination_policy_v1",
        "source": "public_category_fixture_affordance",
        "preferred_fixture_categories": normalized,
        "acceptable_fixture_categories": normalized,
        "placement_tool": placement_tool,
        "placement_tool_by_fixture_category": placement_tool_by_category,
        "requires_public_anchor_selection": True,
        "private_truth_included": False,
        "instruction": (
            "Select a public semantic anchor or fixture whose category matches one of "
            "preferred_fixture_categories; do not infer or request private destination ids."
        ),
    }


def _public_destination_policy_tool_for_fixture_category(category: Any) -> str:
    return "place_inside" if _norm(category) in _INSIDE_DESTINATION_CATEGORY_TERMS else "place"


def _normalize_fixture_category_label(value: Any) -> str:
    text = str(value or "").strip().lower()
    compact = _norm(text)
    aliases = {
        "kitchen sink": "sink",
        "kitchensink": "sink",
        "tvstand": "tvstand",
        "tv stand": "tvstand",
        "shelvingunit": "shelvingunit",
        "shelving unit": "shelvingunit",
        "book shelf": "bookshelf",
        "laundry hamper": "laundryhamper",
        "toy bin": "toybin",
    }
    if text in aliases:
        return aliases[text]
    if compact in aliases:
        return aliases[compact]
    return compact or text


def _fixture_footprint(fixture_id: str) -> dict[str, Any]:
    suffix = sum(ord(ch) for ch in fixture_id) % 7
    width = round(0.45 + suffix * 0.03, 3)
    depth = round(0.35 + suffix * 0.02, 3)
    return {"shape": "rectangle", "width_m": width, "depth_m": depth}


def _fixture_requires_open(fixture: dict[str, Any]) -> bool:
    text = _fixture_text(fixture)
    return "fridge" in text or "refrigerator" in text


def _fixture_prefers_inside(fixture: dict[str, Any]) -> bool:
    return _fixture_requires_open(fixture) or _fixture_is_open_container(fixture)


def _fixture_is_open_container(fixture: dict[str, Any]) -> bool:
    text = _fixture_text(fixture)
    return any(term in text for term in ("shelvingunit", "bookshelf", "bookcase", "shelf"))


def _semantic_anchor_type_for_fixture(fixture: dict[str, Any]) -> str:
    text = _fixture_text(fixture)
    if any(
        term in text
        for term in (
            "sink",
            "fridge",
            "refrigerator",
            "cabinet",
            "drawer",
            "hamper",
            "bin",
            "shelvingunit",
            "bookshelf",
            "bookcase",
            "shelf",
        )
    ):
        return "receptacle"
    if any(term in text for term in ("table", "counter", "desk", "stand", "sofa", "bed")):
        return "surface"
    return "fixture"


def _is_place_anchor(anchor: dict[str, Any]) -> bool:
    actionability = str(anchor.get("actionability") or "actionable")
    if actionability != "actionable":
        return False
    anchor_type = str(anchor.get("anchor_type") or "")
    if anchor_type not in {"surface", "receptacle", "fixture"}:
        return False
    affordances = {str(item).lower() for item in anchor.get("affordances") or []}
    return bool({"place", "place_inside", "open"}.intersection(affordances))


def _anchor_affordances_for_fixture(fixture: dict[str, Any]) -> list[str]:
    affordances = ["observe"]
    for affordance in _fixture_affordances(fixture):
        if affordance not in affordances:
            affordances.append(affordance)
    return affordances


def _fixture_text(fixture: dict[str, Any]) -> str:
    return f"{fixture.get('name', '')} {fixture.get('category', '')}".lower()


def _first_fixture_for_waypoint(waypoint: dict[str, Any]) -> str | None:
    fixture_ids = waypoint.get("fixture_ids") or []
    return str(fixture_ids[0]) if fixture_ids else None


def _first_matching_fixture(
    fixtures: list[dict[str, Any]],
    alias: str,
) -> dict[str, Any] | None:
    alias_norm = _norm(alias)
    for fixture in fixtures:
        text = _norm(
            " ".join(str(fixture.get(key, "")) for key in ("fixture_id", "category", "name"))
        )
        if alias_norm in text:
            return fixture
    return None


def _room_id(room_area: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", room_area.strip().lower()).strip("_")
    return slug or "unknown"


def _vec2(value: Any) -> tuple[float, float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        return None
    try:
        return (float(value[0]), float(value[1]))
    except (TypeError, ValueError):
        return None


def _vec3(value: Any) -> list[float] | None:
    if not isinstance(value, (list, tuple)) or len(value) < 3:
        return None
    try:
        return [float(value[0]), float(value[1]), float(value[2])]
    except (TypeError, ValueError):
        return None


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))

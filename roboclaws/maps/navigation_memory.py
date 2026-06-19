"""Strict Agibot navigation-memory source parsing."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


def read_navigation_memory(
    path: Path, *, source_name: str = "navigation_memory.json"
) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise ValueError(f"{source_name} missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source_name} must contain valid JSON object: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{source_name} must contain a JSON object: {path}")
    return payload


def navigation_memory_items(
    payload: dict[str, Any],
    *,
    source_name: str = "navigation_memory.json",
) -> list[Any]:
    if "items" in payload:
        items = payload["items"]
        if not isinstance(items, list) or not items:
            raise ValueError(f"{source_name} items must be a non-empty list")
        return list(items)
    catalog = payload.get("catalog") if isinstance(payload.get("catalog"), dict) else {}
    memory = catalog.get("navigation_memory")
    if "navigation_memory" in catalog:
        if not isinstance(memory, list) or not memory:
            raise ValueError(f"{source_name} catalog.navigation_memory must be a non-empty list")
        return list(memory)
    raise ValueError(
        f"{source_name} must contain a non-empty items list or catalog.navigation_memory list"
    )


def navigation_memory_item(
    raw_item: Any,
    *,
    index: int,
    source_name: str = "navigation_memory.json",
) -> dict[str, Any]:
    if not isinstance(raw_item, dict):
        raise ValueError(f"{source_name} item {index} must be a JSON object")
    return raw_item


def navigation_memory_point_source(
    payload: Any,
    *,
    label: str,
    required: bool,
) -> dict[str, float]:
    if payload is None and not required:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object with x, y, and optional yaw/z")
    if "x" not in payload or "y" not in payload:
        raise ValueError(f"{label} must include x and y")
    point = {
        "x": _required_float(payload.get("x"), label=f"{label} x"),
        "y": _required_float(payload.get("y"), label=f"{label} y"),
    }
    if "yaw" in payload:
        point["yaw"] = _required_float(payload.get("yaw"), label=f"{label} yaw")
    if "z" in payload:
        point["z"] = _required_float(payload.get("z"), label=f"{label} z")
    return point


def _required_float(value: Any, *, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label} must be a finite number")
    return result

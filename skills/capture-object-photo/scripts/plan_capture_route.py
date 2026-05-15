#!/usr/bin/env python3
"""Build a deterministic photo-capture route from an AI2-THOR scene inventory."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

PLAN_SCHEMA = "roboclaws_capture_object_photo_plan_v1"
DEFAULT_FILTER_TYPES = "Sofa,Chair,ArmChair"


def build_capture_plan(
    scene_objects: dict[str, Any] | list[dict[str, Any]],
    *,
    filter_types: str = DEFAULT_FILTER_TYPES,
    standoff_m: float = 1.0,
) -> dict[str, Any]:
    """Return a route plan using object IDs from a scene_objects payload."""

    allowed_types = _parse_filter_types(filter_types)
    objects = _extract_objects(scene_objects)
    if allowed_types:
        objects = [obj for obj in objects if str(obj.get("objectType", "")) in allowed_types]

    route = sorted(objects, key=lambda obj: (_distance_xz(obj), str(obj.get("objectId", ""))))
    label_counts: dict[str, int] = {}
    targets: list[dict[str, Any]] = []

    for obj in route:
        object_id = str(obj.get("objectId", ""))
        object_type = str(obj.get("objectType", "object"))
        if not object_id:
            continue
        label_base = _label_base(object_type)
        label_counts[label_base] = label_counts.get(label_base, 0) + 1
        label = f"{label_base}-{label_counts[label_base]}"
        targets.append(
            {
                "label": label,
                "object_id": object_id,
                "object_type": object_type,
                "distance_xz": _json_number_or_none(_distance_xz(obj)),
                "actions": [
                    {
                        "tool": "goto",
                        "classification": "privileged_tool",
                        "arguments": {
                            "object_id": object_id,
                            "distance": standoff_m,
                            "face": True,
                        },
                    },
                    {
                        "tool": "observe",
                        "classification": "canonical",
                        "arguments": {"label": label},
                    },
                ],
            }
        )

    return {
        "schema": PLAN_SCHEMA,
        "profile": "ai2thor_navigation_v1",
        "skill": "capture-object-photo",
        "filter_types": sorted(allowed_types),
        "target_count": len(targets),
        "privileged_tools_used": ["scene_objects", "goto"],
        "canonical_tools_used": ["observe", "done"],
        "optional_tools": ["observe_archived", "move"],
        "targets": targets,
        "done_reason_template": _done_reason(target["label"] for target in targets),
    }


def _parse_filter_types(raw: str) -> set[str]:
    return {item.strip() for item in raw.split(",") if item.strip()}


def _extract_objects(scene_objects: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    if isinstance(scene_objects, list):
        return scene_objects
    objects = scene_objects.get("objects", [])
    if not isinstance(objects, list):
        raise ValueError("scene_objects payload must contain an objects list")
    return [obj for obj in objects if isinstance(obj, dict)]


def _distance_xz(obj: dict[str, Any]) -> float:
    value = obj.get("distance_xz")
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.inf
    return number if math.isfinite(number) else math.inf


def _json_number_or_none(value: float) -> float | None:
    return value if math.isfinite(value) else None


def _label_base(object_type: str) -> str:
    special = {"ArmChair": "armchair"}
    if object_type in special:
        return special[object_type]
    words = re.sub(r"(?<!^)(?=[A-Z])", "-", object_type).lower()
    return re.sub(r"[^a-z0-9]+", "-", words).strip("-") or "object"


def _done_reason(labels: Any) -> str:
    label_list = list(labels)
    if not label_list:
        return "Photographed no matching targets"
    return "Photographed " + ", ".join(label_list)


def _load_payload(path: str) -> dict[str, Any] | list[dict[str, Any]]:
    if path == "-":
        return json.load(sys.stdin)
    with Path(path).open(encoding="utf-8") as fp:
        return json.load(fp)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan capture-object-photo goto/observe calls from scene_objects JSON.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--input",
        default="-",
        help="Path to scene_objects JSON, or '-' for stdin.",
    )
    parser.add_argument("--filter-types", default=DEFAULT_FILTER_TYPES)
    parser.add_argument("--standoff", type=float, default=1.0)
    parser.add_argument("--pretty", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    plan = build_capture_plan(
        _load_payload(args.input),
        filter_types=args.filter_types,
        standoff_m=args.standoff,
    )
    json.dump(plan, sys.stdout, indent=2 if args.pretty else None, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

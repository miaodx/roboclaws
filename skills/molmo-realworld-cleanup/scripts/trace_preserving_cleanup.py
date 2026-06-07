#!/usr/bin/env python3
"""Skill helper for the canonical Molmo cleanup routine."""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

from roboclaws.household.cleanup_routine import (
    PUBLIC_ATOMIC_TOOLS,
    ROUTINE_NAME,
    fixture_requires_open,
    normalize_placement_tool,
    routine_plan,
)
from roboclaws.household.cleanup_routine import (
    run_cleanup_routine as _run_canonical_cleanup_routine,
)

CallTool = Callable[..., dict[str, Any]]


class _McpToolAdapter:
    def __init__(self, call_tool: CallTool) -> None:
        self._call_tool = call_tool

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self._call_tool("navigate_to_object", object_id=object_id)

    def adjust_camera(
        self,
        yaw_delta_deg: float = 0.0,
        pitch_delta_deg: float = 0.0,
    ) -> dict[str, Any]:
        return self._call_tool(
            "adjust_camera",
            yaw_delta_deg=yaw_delta_deg,
            pitch_delta_deg=pitch_delta_deg,
        )

    def observe(self) -> dict[str, Any]:
        return self._call_tool("observe")

    def pick(self, object_id: str) -> dict[str, Any]:
        return self._call_tool("pick", object_id=object_id)

    def navigate_to_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._call_tool("navigate_to_receptacle", fixture_id=fixture_id)

    def open_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._call_tool("open_receptacle", fixture_id=fixture_id)

    def place(self, fixture_id: str) -> dict[str, Any]:
        return self._call_tool("place", fixture_id=fixture_id)

    def place_inside(self, fixture_id: str) -> dict[str, Any]:
        return self._call_tool("place_inside", fixture_id=fixture_id)

    def close_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._call_tool("close_receptacle", fixture_id=fixture_id)


def run_cleanup_routine(
    call_tool: CallTool,
    *,
    object_id: str,
    fixture_id: str,
    placement_tool: str = "auto",
    fixture_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Clean one observed object through the shared canonical routine engine."""

    adapter = _McpToolAdapter(call_tool)
    return _run_canonical_cleanup_routine(
        contract=adapter,
        object_id=object_id,
        fixture_id=fixture_id,
        placement_tool=placement_tool,
        fixture_hints=fixture_hints,
        target_request_key="fixture_id",
        include_object_id_in_receptacle_request=False,
        include_object_id_in_target_requests=False,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Describe the canonical Molmo cleanup skill routine.",
    )
    parser.add_argument("--fixture-id", default="")
    parser.add_argument("--placement-tool", default="auto")
    parser.add_argument("--fixture-hints-json", default="")
    args = parser.parse_args(argv)

    fixture_hints = json.loads(args.fixture_hints_json) if args.fixture_hints_json else None
    payload = {
        "routine": ROUTINE_NAME,
        "public_atomic_tools": list(PUBLIC_ATOMIC_TOOLS),
        "fixture_id": args.fixture_id,
        "placement_tool": normalize_placement_tool(
            args.placement_tool,
            fixture_id=args.fixture_id,
            fixture_hints=fixture_hints,
        )
        if args.fixture_id
        else args.placement_tool,
        "fixture_requires_open": fixture_requires_open(
            args.fixture_id,
            fixture_hints=fixture_hints,
        )
        if args.fixture_id
        else False,
        "tool_chain": routine_plan(
            fixture_id=args.fixture_id,
            placement_tool=args.placement_tool,
            fixture_hints=fixture_hints,
        )
        if args.fixture_id
        else [
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            "place|place_inside",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

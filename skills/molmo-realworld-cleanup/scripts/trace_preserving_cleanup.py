#!/usr/bin/env python3
"""Skill-side trace-preserving cleanup routine.

The routine deliberately accepts a public MCP ``call_tool`` function instead of
importing Roboclaws internals. That keeps composition in the skill layer while
preserving the exact atomic tool responses that reports and recovery use.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any

ROUTINE_NAME = "trace_preserving_cleanup_routine_v1"

NAVIGATE_TO_OBJECT = "navigate_to_object"
PICK = "pick"
NAVIGATE_TO_RECEPTACLE = "navigate_to_receptacle"
OPEN_RECEPTACLE = "open_receptacle"
PLACE = "place"
PLACE_INSIDE = "place_inside"
CLOSE_RECEPTACLE = "close_receptacle"

PUBLIC_ATOMIC_TOOLS = (
    NAVIGATE_TO_OBJECT,
    PICK,
    NAVIGATE_TO_RECEPTACLE,
    OPEN_RECEPTACLE,
    PLACE,
    PLACE_INSIDE,
    CLOSE_RECEPTACLE,
)

CallTool = Callable[..., dict[str, Any]]


def run_cleanup_routine(
    call_tool: CallTool,
    *,
    object_id: str,
    fixture_id: str,
    placement_tool: str = "auto",
    fixture_hints: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Clean one observed object through public atomic MCP tools.

    ``call_tool`` is expected to have the shape
    ``call_tool(tool_name: str, **kwargs) -> dict``. The routine never calls the
    promoted ``clean_observed_object`` MCP candidate and never reads private
    scoring or backend state.
    """

    selected_tool = normalize_placement_tool(
        placement_tool,
        fixture_id=fixture_id,
        fixture_hints=fixture_hints,
    )
    steps: list[dict[str, Any]] = []

    def run_phase(phase: str, **kwargs: Any) -> dict[str, Any]:
        response = _coerce_response(call_tool(phase, **kwargs))
        response.setdefault("tool", phase)
        response["phase"] = phase
        response.setdefault("object_id", object_id)
        steps.append(response)
        return response

    def fail(response: dict[str, Any]) -> dict[str, Any]:
        return _routine_response(
            ok=False,
            object_id=object_id,
            fixture_id=fixture_id,
            selected_tool=selected_tool,
            steps=steps,
            failed_phase=str(response.get("phase") or response.get("tool") or ""),
            error_reason=str(response.get("error_reason") or "cleanup_routine_failed"),
            recovery_hint=str(response.get("recovery_hint") or ""),
            required_tool=response.get("required_tool"),
        )

    for phase, kwargs in (
        (NAVIGATE_TO_OBJECT, {"object_id": object_id}),
        (PICK, {"object_id": object_id}),
        (NAVIGATE_TO_RECEPTACLE, {"fixture_id": fixture_id}),
    ):
        response = run_phase(phase, **kwargs)
        if not response.get("ok"):
            recovered = _recover_once(
                call_tool=call_tool,
                failed_phase=phase,
                failed_kwargs=kwargs,
                failed_response=response,
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
            )
            if recovered is None or not recovered.get("ok"):
                return fail(recovered or response)

    if selected_tool == PLACE_INSIDE and fixture_requires_open(fixture_id, fixture_hints):
        response = run_phase(OPEN_RECEPTACLE, fixture_id=fixture_id)
        if not response.get("ok"):
            return fail(response)

    response = run_phase(selected_tool, fixture_id=fixture_id)
    if not response.get("ok"):
        return fail(response)

    if selected_tool == PLACE_INSIDE and fixture_requires_open(fixture_id, fixture_hints):
        response = run_phase(CLOSE_RECEPTACLE, fixture_id=fixture_id)
        if not response.get("ok"):
            return fail(response)

    return _routine_response(
        ok=True,
        object_id=object_id,
        fixture_id=fixture_id,
        selected_tool=selected_tool,
        steps=steps,
    )


def normalize_placement_tool(
    placement_tool: str | None,
    *,
    fixture_id: str,
    fixture_hints: dict[str, Any] | None = None,
) -> str:
    requested = (placement_tool or "auto").strip()
    if requested in {"", "auto"}:
        fixture = fixture_by_id(fixture_hints, fixture_id)
        if fixture is None:
            return PLACE
        affordances = {str(item).strip().lower() for item in fixture.get("affordances") or []}
        category = str(fixture.get("category") or fixture.get("name") or "").lower()
        if PLACE_INSIDE in affordances:
            return PLACE_INSIDE
        if any(term in category for term in ("fridge", "refrigerator", "shelf", "bookcase")):
            return PLACE_INSIDE
        return PLACE
    if requested not in {PLACE, PLACE_INSIDE}:
        raise ValueError("placement_tool must be auto, place, or place_inside")
    return requested


def fixture_requires_open(fixture_id: str, fixture_hints: dict[str, Any] | None) -> bool:
    fixture = fixture_by_id(fixture_hints, fixture_id)
    if fixture is None:
        return False
    affordances = {str(item).strip().lower() for item in fixture.get("affordances") or []}
    category = str(fixture.get("category") or fixture.get("name") or "").lower()
    return OPEN_RECEPTACLE in affordances or "fridge" in category or "refrigerator" in category


def fixture_by_id(
    fixture_hints: dict[str, Any] | None,
    fixture_id: str,
) -> dict[str, Any] | None:
    if not fixture_hints:
        return None
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, dict):
            continue
        for fixture in room.get("fixtures") or []:
            if isinstance(fixture, dict) and str(fixture.get("fixture_id") or "") == fixture_id:
                return fixture
    return None


def routine_plan(
    *,
    fixture_id: str,
    placement_tool: str = "auto",
    fixture_hints: dict[str, Any] | None = None,
) -> list[str]:
    selected_tool = normalize_placement_tool(
        placement_tool,
        fixture_id=fixture_id,
        fixture_hints=fixture_hints,
    )
    plan = [NAVIGATE_TO_OBJECT, PICK, NAVIGATE_TO_RECEPTACLE]
    if selected_tool == PLACE_INSIDE and fixture_requires_open(fixture_id, fixture_hints):
        plan.append(OPEN_RECEPTACLE)
    plan.append(selected_tool)
    if selected_tool == PLACE_INSIDE and fixture_requires_open(fixture_id, fixture_hints):
        plan.append(CLOSE_RECEPTACLE)
    return plan


def _recover_once(
    *,
    call_tool: CallTool,
    failed_phase: str,
    failed_kwargs: dict[str, Any],
    failed_response: dict[str, Any],
    object_id: str,
    fixture_id: str,
    steps: list[dict[str, Any]],
) -> dict[str, Any] | None:
    required_tool = str(failed_response.get("required_tool") or "")
    if failed_response.get("error_reason") != "semantic_order":
        return None
    if required_tool not in PUBLIC_ATOMIC_TOOLS or required_tool == failed_phase:
        return None

    recovery_kwargs = _kwargs_for_tool(required_tool, object_id=object_id, fixture_id=fixture_id)
    recovery_response = _coerce_response(call_tool(required_tool, **recovery_kwargs))
    recovery_response.setdefault("tool", required_tool)
    recovery_response["phase"] = required_tool
    recovery_response.setdefault("object_id", object_id)
    recovery_response["skill_recovery_for_phase"] = failed_phase
    steps.append(recovery_response)
    if not recovery_response.get("ok"):
        return recovery_response

    retry_response = _coerce_response(call_tool(failed_phase, **failed_kwargs))
    retry_response.setdefault("tool", failed_phase)
    retry_response["phase"] = failed_phase
    retry_response.setdefault("object_id", object_id)
    retry_response["skill_recovery_retry"] = True
    steps.append(retry_response)
    return retry_response


def _kwargs_for_tool(tool: str, *, object_id: str, fixture_id: str) -> dict[str, Any]:
    if tool in {NAVIGATE_TO_OBJECT, PICK}:
        return {"object_id": object_id}
    return {"fixture_id": fixture_id}


def _routine_response(
    *,
    ok: bool,
    object_id: str,
    fixture_id: str,
    selected_tool: str,
    steps: list[dict[str, Any]],
    failed_phase: str = "",
    error_reason: str = "",
    recovery_hint: str = "",
    required_tool: Any = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "ok": ok,
        "routine": ROUTINE_NAME,
        "object_id": object_id,
        "fixture_id": fixture_id,
        "receptacle_id": fixture_id,
        "placement_tool": selected_tool,
        "semantic_steps": steps,
        "semantic_step_count": len(steps),
        "composite_preserves_semantic_substeps": True,
        "mcp_composite_used": False,
        "public_tool_chain": [str(step.get("phase") or step.get("tool") or "") for step in steps],
        "instruction": (
            "Skill routine used public atomic MCP tools only. Call observe once in the "
            "current room/fixture area before choosing the next object or waypoint."
        ),
    }
    if not ok:
        payload.update(
            {
                "failed_phase": failed_phase,
                "error_reason": error_reason,
                "recovery_hint": recovery_hint,
            }
        )
        if required_tool:
            payload["required_tool"] = required_tool
    return payload


def _coerce_response(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {"ok": False, "status": "error", "error_reason": "non_dict_response", "raw": value}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Describe the Molmo cleanup trace-preserving skill routine.",
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
        "tool_chain": routine_plan(
            fixture_id=args.fixture_id,
            placement_tool=args.placement_tool,
            fixture_hints=fixture_hints,
        )
        if args.fixture_id
        else [
            NAVIGATE_TO_OBJECT,
            PICK,
            NAVIGATE_TO_RECEPTACLE,
            "place|place_inside",
        ],
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

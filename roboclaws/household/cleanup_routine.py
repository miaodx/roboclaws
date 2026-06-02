from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from roboclaws.household.semantic_timeline import (
    CLOSE_RECEPTACLE_PHASE,
    NAVIGATE_TO_OBJECT_PHASE,
    NAVIGATE_TO_RECEPTACLE_PHASE,
    OPEN_RECEPTACLE_PHASE,
    PICK_PHASE,
    PLACE_INSIDE_PHASE,
    PLACE_PHASE,
)

ROUTINE_SCHEMA = "cleanup_routine_result_v1"
ROUTINE_NAME = "canonical_cleanup_routine_v1"

PUBLIC_ATOMIC_TOOLS = (
    NAVIGATE_TO_OBJECT_PHASE,
    PICK_PHASE,
    NAVIGATE_TO_RECEPTACLE_PHASE,
    OPEN_RECEPTACLE_PHASE,
    PLACE_PHASE,
    PLACE_INSIDE_PHASE,
    CLOSE_RECEPTACLE_PHASE,
)

ToolCall = Callable[[str, dict[str, Any], Callable[[], dict[str, Any]]], dict[str, Any]]
ToolViewRecorder = Callable[[str, dict[str, Any], dict[str, Any]], None]


def run_cleanup_routine(
    *,
    contract: Any,
    object_id: str,
    fixture_id: str,
    placement_tool: str = "auto",
    source_receptacle_id: str = "",
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
    call_tool: ToolCall | None = None,
    record_tool_view: ToolViewRecorder | None = None,
    target_request_key: str = "fixture_id",
    include_object_id_in_receptacle_request: bool = False,
    include_object_id_in_target_requests: bool = False,
) -> dict[str, Any]:
    """Run one already-selected cleanup transport chain over public tools.

    This routine deliberately does not scan rooms, choose candidates, maintain
    memory, read private truth, write reports, or decide when cleanup is done.
    """

    object_id = str(object_id)
    fixture_id = str(fixture_id)
    selected_tool = normalize_placement_tool(
        placement_tool,
        fixture_id=fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    incompatible = explicit_placement_incompatibility(
        placement_tool,
        selected_tool=selected_tool,
        fixture_id=fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    if incompatible:
        return _routine_response(
            ok=False,
            object_id=object_id,
            fixture_id=fixture_id,
            selected_tool=selected_tool,
            steps=[],
            failed_phase=selected_tool,
            error_reason="incompatible_placement_tool",
            recovery_hint=incompatible,
        )

    steps: list[dict[str, Any]] = []

    def run_phase(phase: str, request: dict[str, Any], fn: Callable[[], dict[str, Any]]) -> dict:
        response = _invoke(
            contract=contract,
            call_tool=call_tool,
            record_tool_view=record_tool_view,
            tool=phase,
            request=request,
            fn=fn,
        )
        step = dict(response)
        step.setdefault("tool", phase)
        step["phase"] = phase
        step.setdefault("object_id", object_id)
        steps.append(step)
        return step

    for phase, request, fn in (
        (
            NAVIGATE_TO_OBJECT_PHASE,
            _navigate_object_request(
                object_id=object_id,
                source_receptacle_id=source_receptacle_id,
            ),
            lambda: contract.navigate_to_object(object_id),
        ),
        (PICK_PHASE, {"object_id": object_id}, lambda: contract.pick(object_id)),
        (
            NAVIGATE_TO_RECEPTACLE_PHASE,
            _navigate_receptacle_request(
                fixture_id=fixture_id,
                object_id=object_id,
                include_object_id=include_object_id_in_receptacle_request,
            ),
            lambda: contract.navigate_to_receptacle(fixture_id),
        ),
    ):
        response = run_phase(phase, request, fn)
        if not response.get("ok"):
            recovered = _recover_once(
                contract=contract,
                call_tool=call_tool,
                record_tool_view=record_tool_view,
                failed_phase=phase,
                failed_request=request,
                failed_fn=fn,
                failed_response=response,
                object_id=object_id,
                fixture_id=fixture_id,
                steps=steps,
                target_request_key=target_request_key,
            )
            if recovered is None or not recovered.get("ok"):
                return _failure_response(
                    object_id=object_id,
                    fixture_id=fixture_id,
                    selected_tool=selected_tool,
                    steps=steps,
                    response=recovered or response,
                )

    requires_open = fixture_requires_open(
        fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    if selected_tool == PLACE_INSIDE_PHASE and requires_open:
        request = _target_request(
            object_id=object_id,
            fixture_id=fixture_id,
            target_request_key=target_request_key,
            include_object_id=include_object_id_in_target_requests,
        )
        response = run_phase(
            OPEN_RECEPTACLE_PHASE,
            request,
            lambda: contract.open_receptacle(fixture_id),
        )
        if not response.get("ok"):
            return _failure_response(
                object_id=object_id,
                fixture_id=fixture_id,
                selected_tool=selected_tool,
                steps=steps,
                response=response,
            )

    place_request = _target_request(
        object_id=object_id,
        fixture_id=fixture_id,
        target_request_key=target_request_key,
        include_object_id=include_object_id_in_target_requests,
    )
    if selected_tool == PLACE_INSIDE_PHASE:
        response = run_phase(
            PLACE_INSIDE_PHASE,
            place_request,
            lambda: contract.place_inside(fixture_id),
        )
    else:
        response = run_phase(
            PLACE_PHASE,
            place_request,
            lambda: contract.place(fixture_id),
        )
    if not response.get("ok"):
        return _failure_response(
            object_id=object_id,
            fixture_id=fixture_id,
            selected_tool=selected_tool,
            steps=steps,
            response=response,
        )

    if selected_tool == PLACE_INSIDE_PHASE and requires_open:
        request = _target_request(
            object_id=object_id,
            fixture_id=fixture_id,
            target_request_key=target_request_key,
            include_object_id=include_object_id_in_target_requests,
        )
        response = run_phase(
            CLOSE_RECEPTACLE_PHASE,
            request,
            lambda: contract.close_receptacle(fixture_id),
        )
        if not response.get("ok"):
            return _failure_response(
                object_id=object_id,
                fixture_id=fixture_id,
                selected_tool=selected_tool,
                steps=steps,
                response=response,
            )

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
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
) -> str:
    requested = str(placement_tool or "auto").strip()
    if requested in {"", "auto"}:
        fixture = _fixture_for_policy(
            fixture_id,
            target_fixture=target_fixture,
            fixture_hints=fixture_hints,
        )
        if fixture is None:
            return PLACE_PHASE
        if _fixture_prefers_inside(fixture, fixture_id):
            return PLACE_INSIDE_PHASE
        return PLACE_PHASE
    if requested not in {PLACE_PHASE, PLACE_INSIDE_PHASE}:
        raise ValueError("placement_tool must be auto, place, or place_inside")
    return requested


def routine_plan(
    *,
    fixture_id: str,
    placement_tool: str = "auto",
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
) -> list[str]:
    selected_tool = normalize_placement_tool(
        placement_tool,
        fixture_id=fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    plan = [NAVIGATE_TO_OBJECT_PHASE, PICK_PHASE, NAVIGATE_TO_RECEPTACLE_PHASE]
    if selected_tool == PLACE_INSIDE_PHASE and fixture_requires_open(
        fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    ):
        plan.append(OPEN_RECEPTACLE_PHASE)
    plan.append(selected_tool)
    if selected_tool == PLACE_INSIDE_PHASE and fixture_requires_open(
        fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    ):
        plan.append(CLOSE_RECEPTACLE_PHASE)
    return plan


def fixture_requires_open(
    fixture_id: str,
    *,
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
) -> bool:
    fixture = _fixture_for_policy(
        fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    if fixture is None:
        return False
    affordances = _fixture_affordances(fixture)
    text = _fixture_text(fixture, fixture_id)
    return OPEN_RECEPTACLE_PHASE in affordances or "fridge" in text or "refrigerator" in text


def explicit_placement_incompatibility(
    placement_tool: str | None,
    *,
    selected_tool: str,
    fixture_id: str,
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
) -> str:
    requested = str(placement_tool or "auto").strip()
    if requested in {"", "auto"}:
        return ""
    fixture = _fixture_for_policy(
        fixture_id,
        target_fixture=target_fixture,
        fixture_hints=fixture_hints,
    )
    if fixture is None:
        return ""
    if requested == PLACE_PHASE and _fixture_prefers_inside(fixture, fixture_id):
        return (
            "Requested placement_tool=place is incompatible with this public fixture; "
            "use placement_tool=auto or place_inside."
        )
    if requested == PLACE_INSIDE_PHASE and not _fixture_accepts_inside(fixture, fixture_id):
        return (
            "Requested placement_tool=place_inside is incompatible with this public "
            "fixture; use placement_tool=auto or place."
        )
    return ""


def _invoke(
    *,
    contract: Any,
    call_tool: ToolCall | None,
    record_tool_view: ToolViewRecorder | None,
    tool: str,
    request: dict[str, Any],
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    response = call_tool(tool, request, fn) if call_tool is not None else fn()
    response = dict(response)
    if record_tool_view is not None:
        record_tool_view(tool, request, response)
    return response


def _recover_once(
    *,
    contract: Any,
    call_tool: ToolCall | None,
    record_tool_view: ToolViewRecorder | None,
    failed_phase: str,
    failed_request: dict[str, Any],
    failed_fn: Callable[[], dict[str, Any]],
    failed_response: dict[str, Any],
    object_id: str,
    fixture_id: str,
    steps: list[dict[str, Any]],
    target_request_key: str,
) -> dict[str, Any] | None:
    required_tool = str(failed_response.get("required_tool") or "")
    if failed_response.get("error_reason") != "semantic_order":
        return None
    if required_tool not in PUBLIC_ATOMIC_TOOLS or required_tool == failed_phase:
        return None

    recovery_request = _request_for_tool(
        required_tool,
        object_id=object_id,
        fixture_id=fixture_id,
        target_request_key=target_request_key,
    )
    recovery_response = _invoke(
        contract=contract,
        call_tool=call_tool,
        record_tool_view=record_tool_view,
        tool=required_tool,
        request=recovery_request,
        fn=_fn_for_tool(contract, required_tool, object_id=object_id, fixture_id=fixture_id),
    )
    recovery_step = dict(recovery_response)
    recovery_step.setdefault("tool", required_tool)
    recovery_step["phase"] = required_tool
    recovery_step.setdefault("object_id", object_id)
    recovery_step["routine_recovery_for_phase"] = failed_phase
    recovery_step["skill_recovery_for_phase"] = failed_phase
    steps.append(recovery_step)
    if not recovery_step.get("ok"):
        return recovery_step

    retry_response = _invoke(
        contract=contract,
        call_tool=call_tool,
        record_tool_view=record_tool_view,
        tool=failed_phase,
        request=failed_request,
        fn=failed_fn,
    )
    retry_step = dict(retry_response)
    retry_step.setdefault("tool", failed_phase)
    retry_step["phase"] = failed_phase
    retry_step.setdefault("object_id", object_id)
    retry_step["routine_recovery_retry"] = True
    retry_step["skill_recovery_retry"] = True
    steps.append(retry_step)
    return retry_step


def _fn_for_tool(
    contract: Any,
    tool: str,
    *,
    object_id: str,
    fixture_id: str,
) -> Callable[[], dict[str, Any]]:
    if tool == NAVIGATE_TO_OBJECT_PHASE:
        return lambda: contract.navigate_to_object(object_id)
    if tool == PICK_PHASE:
        return lambda: contract.pick(object_id)
    if tool == NAVIGATE_TO_RECEPTACLE_PHASE:
        return lambda: contract.navigate_to_receptacle(fixture_id)
    if tool == OPEN_RECEPTACLE_PHASE:
        return lambda: contract.open_receptacle(fixture_id)
    if tool == PLACE_INSIDE_PHASE:
        return lambda: contract.place_inside(fixture_id)
    if tool == CLOSE_RECEPTACLE_PHASE:
        return lambda: contract.close_receptacle(fixture_id)
    return lambda: contract.place(fixture_id)


def _request_for_tool(
    tool: str,
    *,
    object_id: str,
    fixture_id: str,
    target_request_key: str,
) -> dict[str, Any]:
    if tool in {NAVIGATE_TO_OBJECT_PHASE, PICK_PHASE}:
        return {"object_id": object_id}
    if tool == NAVIGATE_TO_RECEPTACLE_PHASE:
        return {"receptacle_id": fixture_id}
    return _target_request(
        object_id=object_id,
        fixture_id=fixture_id,
        target_request_key=target_request_key,
        include_object_id=False,
    )


def _navigate_receptacle_request(
    *,
    fixture_id: str,
    object_id: str,
    include_object_id: bool,
) -> dict[str, Any]:
    request = {"receptacle_id": fixture_id}
    if include_object_id:
        request["object_id"] = object_id
    return request


def _navigate_object_request(
    *,
    object_id: str,
    source_receptacle_id: str,
) -> dict[str, Any]:
    request = {"object_id": object_id}
    if source_receptacle_id:
        request["source_receptacle_id"] = source_receptacle_id
    return request


def _target_request(
    *,
    object_id: str,
    fixture_id: str,
    target_request_key: str,
    include_object_id: bool,
) -> dict[str, Any]:
    request = {target_request_key: fixture_id}
    if include_object_id:
        request["object_id"] = object_id
    return request


def _failure_response(
    *,
    object_id: str,
    fixture_id: str,
    selected_tool: str,
    steps: list[dict[str, Any]],
    response: Mapping[str, Any],
) -> dict[str, Any]:
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
    response = {
        "schema": ROUTINE_SCHEMA,
        "routine": ROUTINE_NAME,
        "ok": ok,
        "status": "ok" if ok else "error",
        "object_id": object_id,
        "fixture_id": fixture_id,
        "receptacle_id": fixture_id,
        "selected_placement_tool": selected_tool,
        "placement_tool": selected_tool,
        "steps": steps,
        "semantic_steps": steps,
        "semantic_step_count": len(steps),
        "failed_phase": failed_phase,
        "error_reason": error_reason,
        "recovery_hint": recovery_hint,
        "required_tool": required_tool or "",
        "recovery_attempted": any(
            step.get("routine_recovery_for_phase") or step.get("routine_recovery_retry")
            for step in steps
        ),
        "mcp_composite_used": False,
        "routine_preserves_semantic_substeps": True,
        "composite_preserves_semantic_substeps": True,
    }
    if not ok:
        response["tool"] = "cleanup_routine"
    return response


def _fixture_for_policy(
    fixture_id: str,
    *,
    target_fixture: Mapping[str, Any] | None = None,
    fixture_hints: Mapping[str, Any] | None = None,
) -> Mapping[str, Any] | None:
    if target_fixture is not None:
        return target_fixture
    if not fixture_hints:
        return None
    for room in fixture_hints.get("rooms") or []:
        if not isinstance(room, Mapping):
            continue
        for fixture in room.get("fixtures") or []:
            if isinstance(fixture, Mapping) and str(fixture.get("fixture_id") or "") == fixture_id:
                return fixture
    return None


def _fixture_prefers_inside(fixture: Mapping[str, Any], fixture_id: str) -> bool:
    return PLACE_INSIDE_PHASE in _fixture_affordances(fixture) or any(
        term in _fixture_text(fixture, fixture_id)
        for term in ("fridge", "refrigerator", "shelvingunit", "bookshelf", "bookcase", "shelf")
    )


def _fixture_accepts_inside(fixture: Mapping[str, Any], fixture_id: str) -> bool:
    return _fixture_prefers_inside(fixture, fixture_id)


def _fixture_affordances(fixture: Mapping[str, Any]) -> set[str]:
    return {str(item).strip().lower() for item in fixture.get("affordances") or []}


def _fixture_text(fixture: Mapping[str, Any], fixture_id: str) -> str:
    return " ".join(
        str(value)
        for value in (
            fixture.get("category"),
            fixture.get("name"),
            fixture.get("receptacle_id"),
            fixture.get("fixture_id"),
            fixture_id,
        )
        if value is not None
    ).lower()

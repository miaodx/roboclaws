from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from roboclaws.molmo_cleanup.semantic_timeline import (
    CLOSE_RECEPTACLE_PHASE,
    NAVIGATE_TO_OBJECT_PHASE,
    NAVIGATE_TO_RECEPTACLE_PHASE,
    OPEN_RECEPTACLE_PHASE,
    PICK_PHASE,
    PLACE_INSIDE_PHASE,
    PLACE_PHASE,
)

ToolCall = Callable[[str, dict[str, Any], Callable[[], dict[str, Any]]], dict[str, Any]]
ToolViewRecorder = Callable[[str, dict[str, Any], dict[str, Any]], None]


@dataclass(frozen=True)
class SemanticCleanupLoopResult:
    attempted_objects: int
    completed_objects: int
    failed_objects: tuple[dict[str, Any], ...]


def run_semantic_cleanup_loop(
    *,
    targets: Sequence[Mapping[str, Any]],
    contract: Any,
    call_tool: ToolCall,
    receptacles_by_id: Mapping[str, Mapping[str, Any]] | None = None,
    record_tool_view: ToolViewRecorder | None = None,
    target_request_key: str = "receptacle_id",
    include_object_id_in_receptacle_request: bool = True,
    include_object_id_in_target_requests: bool = True,
) -> SemanticCleanupLoopResult:
    """Run the canonical object cleanup loop over already-selected targets."""
    completed = 0
    failed: list[dict[str, Any]] = []
    receptacles = receptacles_by_id or {}

    for target in targets:
        object_id = _required_target_value(target, "object_id")
        target_receptacle_id = _target_receptacle_id(target)
        source_receptacle_id = _optional_target_value(target, "source_receptacle_id")

        ok, failed_step = _run_one_object(
            target=target,
            contract=contract,
            call_tool=call_tool,
            record_tool_view=record_tool_view,
            receptacles_by_id=receptacles,
            object_id=object_id,
            target_receptacle_id=target_receptacle_id,
            source_receptacle_id=source_receptacle_id,
            target_request_key=target_request_key,
            include_object_id_in_receptacle_request=include_object_id_in_receptacle_request,
            include_object_id_in_target_requests=include_object_id_in_target_requests,
        )
        if ok:
            completed += 1
        else:
            failed.append(
                {
                    "object_id": object_id,
                    "target_receptacle_id": target_receptacle_id,
                    **failed_step,
                }
            )

    return SemanticCleanupLoopResult(
        attempted_objects=len(targets),
        completed_objects=completed,
        failed_objects=tuple(failed),
    )


def _run_one_object(
    *,
    target: Mapping[str, Any],
    contract: Any,
    call_tool: ToolCall,
    record_tool_view: ToolViewRecorder | None,
    receptacles_by_id: Mapping[str, Mapping[str, Any]],
    object_id: str,
    target_receptacle_id: str,
    source_receptacle_id: str,
    target_request_key: str,
    include_object_id_in_receptacle_request: bool,
    include_object_id_in_target_requests: bool,
) -> tuple[bool, dict[str, Any]]:
    navigate_object_request = {"object_id": object_id}
    if source_receptacle_id:
        navigate_object_request["source_receptacle_id"] = source_receptacle_id
    response = _invoke(
        call_tool,
        record_tool_view,
        NAVIGATE_TO_OBJECT_PHASE,
        navigate_object_request,
        lambda: contract.navigate_to_object(object_id),
    )
    if not response.get("ok"):
        return False, _failed_step(NAVIGATE_TO_OBJECT_PHASE, response)

    pick_request = {"object_id": object_id}
    response = _invoke(
        call_tool,
        record_tool_view,
        PICK_PHASE,
        pick_request,
        lambda: contract.pick(object_id),
    )
    if not response.get("ok"):
        return False, _failed_step(PICK_PHASE, response)

    navigate_receptacle_request = {"receptacle_id": target_receptacle_id}
    if include_object_id_in_receptacle_request:
        navigate_receptacle_request["object_id"] = object_id
    response = _invoke(
        call_tool,
        record_tool_view,
        NAVIGATE_TO_RECEPTACLE_PHASE,
        navigate_receptacle_request,
        lambda: contract.navigate_to_receptacle(target_receptacle_id),
    )
    if not response.get("ok"):
        return False, _failed_step(NAVIGATE_TO_RECEPTACLE_PHASE, response)

    target_receptacle = _target_receptacle(target, receptacles_by_id, target_receptacle_id)
    requires_open = _requires_open_for_inside_place(target_receptacle, target_receptacle_id)
    if _requires_inside_place(target, target_receptacle, target_receptacle_id):
        open_request = _target_request(
            object_id=object_id,
            target_receptacle_id=target_receptacle_id,
            target_request_key=target_request_key,
            include_object_id=include_object_id_in_target_requests,
        )
        if requires_open:
            response = _invoke(
                call_tool,
                record_tool_view,
                OPEN_RECEPTACLE_PHASE,
                open_request,
                lambda: contract.open_receptacle(target_receptacle_id),
            )
            if not response.get("ok"):
                return False, _failed_step(OPEN_RECEPTACLE_PHASE, response)
        place_tool = PLACE_INSIDE_PHASE
    else:
        place_tool = PLACE_PHASE

    place_request = _target_request(
        object_id=object_id,
        target_receptacle_id=target_receptacle_id,
        target_request_key=target_request_key,
        include_object_id=include_object_id_in_target_requests,
    )
    if place_tool == PLACE_INSIDE_PHASE:
        response = _invoke(
            call_tool,
            record_tool_view,
            place_tool,
            place_request,
            lambda: contract.place_inside(target_receptacle_id),
        )
    else:
        response = _invoke(
            call_tool,
            record_tool_view,
            place_tool,
            place_request,
            lambda: contract.place(target_receptacle_id),
        )
    if not response.get("ok"):
        return False, _failed_step(place_tool, response)

    if place_tool == PLACE_INSIDE_PHASE and requires_open:
        close_request = _target_request(
            object_id=object_id,
            target_receptacle_id=target_receptacle_id,
            target_request_key=target_request_key,
            include_object_id=include_object_id_in_target_requests,
        )
        response = _invoke(
            call_tool,
            record_tool_view,
            CLOSE_RECEPTACLE_PHASE,
            close_request,
            lambda: contract.close_receptacle(target_receptacle_id),
        )
        if not response.get("ok"):
            return False, _failed_step(CLOSE_RECEPTACLE_PHASE, response)

    return True, {}


def _invoke(
    call_tool: ToolCall,
    record_tool_view: ToolViewRecorder | None,
    tool: str,
    request: dict[str, Any],
    fn: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    response = call_tool(tool, request, fn)
    if record_tool_view is not None:
        record_tool_view(tool, request, response)
    return response


def _target_request(
    *,
    object_id: str,
    target_receptacle_id: str,
    target_request_key: str,
    include_object_id: bool,
) -> dict[str, Any]:
    request = {target_request_key: target_receptacle_id}
    if include_object_id:
        request["object_id"] = object_id
    return request


def _failed_step(tool: str, response: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "failed_tool": tool,
        "status": str(response.get("status") or "error"),
        "error_reason": str(response.get("error_reason") or ""),
    }


def _target_receptacle(
    target: Mapping[str, Any],
    receptacles_by_id: Mapping[str, Mapping[str, Any]],
    target_receptacle_id: str,
) -> Mapping[str, Any]:
    raw = target.get("target_receptacle") or target.get("receptacle")
    if isinstance(raw, Mapping):
        return raw
    return receptacles_by_id.get(target_receptacle_id, {})


def _requires_inside_place(
    target: Mapping[str, Any],
    receptacle: Mapping[str, Any],
    receptacle_id: str,
) -> bool:
    if "requires_inside_place" in target:
        return bool(target["requires_inside_place"])
    if PLACE_INSIDE_PHASE in target:
        return bool(target[PLACE_INSIDE_PHASE])
    text = " ".join(
        str(value)
        for value in (
            receptacle.get("category"),
            receptacle.get("name"),
            receptacle.get("receptacle_id"),
            receptacle.get("fixture_id"),
            receptacle_id,
        )
        if value is not None
    ).lower()
    return any(
        term in text
        for term in ("fridge", "refrigerator", "shelvingunit", "bookshelf", "bookcase", "shelf")
    )


def _requires_open_for_inside_place(
    receptacle: Mapping[str, Any],
    receptacle_id: str,
) -> bool:
    text = " ".join(
        str(value)
        for value in (
            receptacle.get("category"),
            receptacle.get("name"),
            receptacle.get("receptacle_id"),
            receptacle.get("fixture_id"),
            receptacle_id,
        )
        if value is not None
    ).lower()
    return "fridge" in text or "refrigerator" in text


def _target_receptacle_id(target: Mapping[str, Any]) -> str:
    for key in ("target_receptacle_id", "receptacle_id", "fixture_id", "to_fixture_id"):
        value = target.get(key)
        if value:
            return str(value)
    raise ValueError(f"cleanup target lacks a receptacle id: {target}")


def _required_target_value(target: Mapping[str, Any], key: str) -> str:
    value = target.get(key)
    if not value:
        raise ValueError(f"cleanup target lacks {key}: {target}")
    return str(value)


def _optional_target_value(target: Mapping[str, Any], key: str) -> str:
    value = target.get(key)
    return "" if value is None else str(value)

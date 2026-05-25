from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from roboclaws.molmo_cleanup.cleanup_routine import run_cleanup_routine
from roboclaws.molmo_cleanup.semantic_timeline import PLACE_INSIDE_PHASE

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
    if source_receptacle_id:
        target = dict(target)
        target["source_receptacle_id"] = source_receptacle_id
    target_receptacle = _target_receptacle(target, receptacles_by_id, target_receptacle_id)
    placement_tool = PLACE_INSIDE_PHASE if bool(target.get(PLACE_INSIDE_PHASE)) else "auto"
    result = run_cleanup_routine(
        contract=contract,
        object_id=object_id,
        fixture_id=target_receptacle_id,
        placement_tool=placement_tool,
        source_receptacle_id=source_receptacle_id,
        target_fixture=target_receptacle,
        call_tool=call_tool,
        record_tool_view=record_tool_view,
        target_request_key=target_request_key,
        include_object_id_in_receptacle_request=include_object_id_in_receptacle_request,
        include_object_id_in_target_requests=include_object_id_in_target_requests,
    )
    if result.get("ok"):
        return True, {}
    return False, _failed_step(str(result.get("failed_phase") or ""), result)


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

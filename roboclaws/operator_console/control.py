"""Direct active-run control helpers for the operator console."""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client

from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleLaunchSelection
from roboclaws.operator_console.state import derive_operator_state

CONTROL_ARTIFACT = "operator_control.jsonl"
INTERVENTIONS_ARTIFACT = "operator_interventions.json"
CONTROL_ACTION_NAVIGATE = "navigate_to_relative_pose"
CONTROL_ACTION_OBSERVE = "observe"
ALLOWED_CONTROL_ACTIONS = frozenset({CONTROL_ACTION_NAVIGATE, CONTROL_ACTION_OBSERVE})
MAX_CONTROL_STEP_M = 1.0
MAX_CONTROL_TURN_DEG = 90.0


class OperatorControlError(ValueError):
    """Raised when an operator control request is invalid or cannot run."""

    def __init__(self, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def run_operator_control(
    root: Path,
    run_id: str,
    route: ConsoleLaunchSelection | None,
    payload: dict[str, object],
) -> dict[str, Any]:
    run_dir = console_output_root(root) / "runs" / run_id
    if not run_dir.is_dir() or not (run_dir / "operator_state.json").is_file():
        raise OperatorControlError("unknown run", status=404)
    state = derive_operator_state(root, run_dir, route)
    _validate_control_state(state, route)
    action = str(payload.get("action") or "").strip()
    if action not in ALLOWED_CONTROL_ACTIONS:
        raise OperatorControlError(f"unsupported control action: {action or '<empty>'}")
    arguments = _control_arguments(action, payload)
    status = _read_json(run_dir / "operator_state.json")
    mcp_url = str(status.get("mcp_url") or "").strip()
    if not mcp_url:
        host = str(status.get("mcp_host") or "").strip()
        port = status.get("mcp_port")
        if host and port:
            mcp_url = f"http://{host}:{int(port)}/mcp"
    if not mcp_url:
        raise OperatorControlError("active run has no recorded MCP endpoint", status=409)

    request_row = _append_control_row(
        run_dir,
        {
            "event": "request",
            "actor": "operator",
            "action": action,
            "arguments": arguments,
            "mcp_url": mcp_url,
        },
    )
    try:
        tool_response = asyncio.run(_call_mcp_tool(mcp_url, action, arguments))
        response_row = _append_control_row(
            run_dir,
            {
                "event": "response",
                "actor": "operator",
                "action": action,
                "arguments": arguments,
                "mcp_url": mcp_url,
                "response": tool_response,
            },
        )
    except Exception as exc:
        response_row = _append_control_row(
            run_dir,
            {
                "event": "response",
                "actor": "operator",
                "action": action,
                "arguments": arguments,
                "mcp_url": mcp_url,
                "error": str(exc),
            },
        )
        _update_operator_state_with_control(run_dir, response_row)
        raise OperatorControlError(f"control call failed: {exc}", status=502) from exc

    _update_operator_state_with_control(run_dir, response_row)
    return {
        "ok": True,
        "run_id": run_id,
        "actor": "operator",
        "action": action,
        "arguments": arguments,
        "response": tool_response,
        "request_event_id": request_row["event_id"],
        "response_event_id": response_row["event_id"],
        "operator_interventions": _operator_intervention_summary(run_dir),
    }


def _validate_control_state(
    state: dict[str, Any],
    route: ConsoleLaunchSelection | None,
) -> None:
    if not state.get("run_id"):
        raise OperatorControlError("unknown run", status=404)
    controls = state.get("controls") or {}
    if not route:
        raise OperatorControlError("control requires a known console route", status=409)
    if not route.supports_relative_navigation_control:
        raise OperatorControlError("route does not support relative navigation control", status=409)
    if controls.get("next_goal_available"):
        raise OperatorControlError("terminal run cannot be controlled", status=409)
    if not controls.get("relative_navigation_control_available"):
        raise OperatorControlError("relative navigation control is unavailable", status=409)


def _control_arguments(action: str, payload: dict[str, object]) -> dict[str, Any]:
    if action == CONTROL_ACTION_OBSERVE:
        return {}
    forward_m = _float(payload.get("forward_m"))
    lateral_m = _float(payload.get("lateral_m"))
    yaw_delta_deg = _float(payload.get("yaw_delta_deg"))
    if not any((forward_m, lateral_m, yaw_delta_deg)):
        raise OperatorControlError("relative movement request is a no-op")
    if (
        abs(forward_m) > MAX_CONTROL_STEP_M
        or abs(lateral_m) > MAX_CONTROL_STEP_M
        or abs(yaw_delta_deg) > MAX_CONTROL_TURN_DEG
    ):
        raise OperatorControlError("relative movement request exceeds console limits")
    return {
        "forward_m": forward_m,
        "lateral_m": lateral_m,
        "yaw_delta_deg": yaw_delta_deg,
    }


async def _call_mcp_tool(
    mcp_url: str,
    action: str,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    async with streamablehttp_client(mcp_url, timeout=30, sse_read_timeout=30) as (
        read_stream,
        write_stream,
        _,
    ):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(action, arguments or None)
    return _serialize_tool_result(result)


def _serialize_tool_result(result: Any) -> dict[str, Any]:
    if hasattr(result, "model_dump"):
        payload = result.model_dump(mode="json")
    elif hasattr(result, "dict"):
        payload = result.dict()
    else:
        payload = {"result": str(result)}
    content = payload.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    parsed = None
                if isinstance(parsed, dict):
                    return parsed
    return payload


def _append_control_row(run_dir: Path, row: dict[str, Any]) -> dict[str, Any]:
    rows = _read_control_rows(run_dir)
    event_id = f"operator_control_{len(rows) + 1:03d}"
    payload = {
        "schema": "operator_console_control_event_v1",
        "event_id": event_id,
        "ts": time.time(),
        **row,
    }
    path = run_dir / CONTROL_ARTIFACT
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")
    return payload


def _update_operator_state_with_control(run_dir: Path, response_row: dict[str, Any]) -> None:
    state_path = run_dir / "operator_state.json"
    state = _read_json(state_path)
    summary = _operator_intervention_summary(run_dir)
    state["latest_operator_control"] = response_row
    state["operator_interventions"] = summary
    state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (run_dir / INTERVENTIONS_ARTIFACT).write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _operator_intervention_summary(run_dir: Path) -> dict[str, Any]:
    rows = [
        row
        for row in _read_control_rows(run_dir)
        if row.get("actor") == "operator" and row.get("event") == "response"
    ]
    return {
        "schema": "operator_console_interventions_v1",
        "count": len(rows),
        "assisted": bool(rows),
        "autonomous_behavior_proof": not rows,
        "events": rows[-10:],
    }


def _read_control_rows(run_dir: Path) -> list[dict[str, Any]]:
    path = run_dir / CONTROL_ARTIFACT
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise OperatorControlError(
            f"operator control source cannot be read at {path}: {exc}",
            status=409,
        ) from exc
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise OperatorControlError(
                f"operator control source contains invalid JSON at {path}:{line_number}: {exc.msg}",
                status=409,
            ) from exc
        if not isinstance(payload, dict):
            raise OperatorControlError(
                f"operator control source row must be an object at {path}:{line_number}",
                status=409,
            )
        rows.append(payload)
    return rows


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _float(value: object) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise OperatorControlError(f"invalid numeric control value: {value}") from exc

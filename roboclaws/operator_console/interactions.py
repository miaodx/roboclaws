"""Operator-session and message artifacts for the local console."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any

from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleRoute, get_route
from roboclaws.operator_console.state import (
    derive_operator_state,
    resolve_display_run_dir,
)

SESSION_SCHEMA = "operator_console_session_v1"
MESSAGE_SCHEMA = "operator_console_message_v1"
MESSAGE_LOG = "operator_messages.jsonl"
SESSION_LOG = "sessions.jsonl"
SESSION_DIR = "sessions"
ASK_WHY_DIR = "ask_why"
CONTINUE_QUEUE = "continue_queue.jsonl"

TERMINAL_STATUSES = {
    "done",
    "finished",
    "passed",
    "stopped_by_operator",
    "human_takeover_stop",
    "emergency_stopped",
    "failed",
}

PRIVATE_TERMS = (
    "generated_mess_set",
    "acceptable_destination_sets",
    "private_manifest",
    "target_receptacle_id",
    "private_target_truth",
    "global_movable_object_inventory",
)


class InteractionError(ValueError):
    """User-facing interaction validation error."""


def create_operator_session(root: Path) -> dict[str, Any]:
    """Create a durable operator session record."""

    session_id = _new_id("session")
    now = _utc_now()
    payload = {
        "schema": SESSION_SCHEMA,
        "operator_session_id": session_id,
        "created_at_epoch": now,
        "created_at": _format_epoch(now),
        "active_run_id": "",
        "run_ids": [],
        "message_ids": [],
    }
    path = _session_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _append_jsonl(_session_log_path(root), payload)
    return payload


def get_operator_session(root: Path, session_id: str) -> dict[str, Any]:
    payload = _read_json(_session_path(root, session_id))
    if not payload:
        raise InteractionError(f"unknown operator session: {session_id}")
    return payload


def attach_run_to_session(root: Path, run_id: str, session_id: str = "") -> dict[str, Any]:
    """Attach a run to an existing or new operator session."""

    session = (
        get_operator_session(root, session_id) if session_id else create_operator_session(root)
    )
    run_ids = list(session.get("run_ids") or [])
    if run_id not in run_ids:
        run_ids.append(run_id)
    session["run_ids"] = run_ids
    session["active_run_id"] = run_id
    _write_session(root, session)
    return session


def append_ask_why(root: Path, run_id: str, question: str) -> dict[str, Any]:
    """Answer a read-only operator question from public run artifacts."""

    question = _clean_text(question)
    if not question:
        raise InteractionError("Ask Why requires a question.")
    run_dir, route = _run_context(root, run_id)
    state = derive_operator_state(root, run_dir, route)
    message = _base_message(
        command_type="ask_why",
        run_id=run_id,
        body=question,
        status="answered",
    )
    answer = _ask_why_answer(root, state, question)
    message["answer"] = answer
    message["artifact_scope"] = answer["artifact_scope"]
    ask_dir = run_dir / ASK_WHY_DIR
    ask_dir.mkdir(parents=True, exist_ok=True)
    (ask_dir / f"{message['message_id']}.json").write_text(
        json.dumps(message, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _append_message(run_dir, message)
    _record_session_message(root, run_dir, message)
    return message


def append_steer_message(root: Path, run_id: str, body: str) -> dict[str, Any]:
    """Append an active-run steering message for routes that support the MCP inbox."""

    body = _clean_text(body)
    if not body:
        raise InteractionError("Steer Current Run requires message text.")
    run_dir, route = _run_context(root, run_id)
    state = derive_operator_state(root, run_dir, route)
    if _is_terminal_state(state):
        raise InteractionError("Robot Run is terminal; use Continue After Run instead.")
    if route is None or not route.supports_operator_steer:
        raise InteractionError("Steer Current Run is unavailable for this route.")
    message = _base_message(command_type="steer", run_id=run_id, body=body, status="queued")
    message["delivery"] = {
        "transport": "mcp_check_operator_messages",
        "operator_message_pending": True,
    }
    _append_message(run_dir, message)
    _record_session_message(root, run_dir, message)
    return message


def append_continue_request(root: Path, run_id: str, prompt: str) -> dict[str, Any]:
    """Create or queue a linked follow-up run request."""

    prompt = _clean_text(prompt)
    if not prompt:
        raise InteractionError("Continue After Run requires a follow-up prompt.")
    run_dir, route = _run_context(root, run_id)
    state = derive_operator_state(root, run_dir, route)
    session = _session_for_run(root, run_dir, run_id)
    terminal = _is_terminal_state(state)
    requires_confirmation = _requires_continue_confirmation(route)
    result_available = _parent_result_available(run_dir, state)
    terminal_success = _terminal_success(state)
    status = (
        "ready_to_start"
        if terminal and result_available and terminal_success and not requires_confirmation
        else "queued"
    )
    if not terminal:
        reason = "waiting_for_parent_terminal_state"
    elif not result_available:
        reason = "waiting_for_parent_result_artifacts"
    elif not terminal_success:
        reason = "operator_confirmation_required_after_parent_terminal_status"
    elif requires_confirmation:
        reason = "operator_confirmation_required"
    else:
        reason = "parent_terminal_and_result_available"
    message = _base_message(
        command_type="continue",
        run_id=run_id,
        body=prompt,
        status=status,
    )
    message.update(
        {
            "operator_session_id": session["operator_session_id"],
            "parent_run_id": run_id,
            "route_id": route.id if route else "",
            "queue_reason": reason,
            "auto_start_allowed": status == "ready_to_start",
            "continuation_packet": _continuation_packet(state, session, run_id, prompt),
        }
    )
    _append_jsonl(run_dir / CONTINUE_QUEUE, message)
    _append_message(run_dir, message)
    _record_session_message(root, run_dir, message)
    return message


def list_operator_messages(root: Path, run_id: str) -> dict[str, Any]:
    run_dir, route = _run_context(root, run_id)
    state = derive_operator_state(root, run_dir, route)
    messages = _read_message_rows(run_dir)
    return {
        "run_id": run_id,
        "operator_session_id": _session_id_from_run_state(run_dir),
        "messages": messages,
        "operator_message_pending": any(
            item.get("command_type") == "steer" and item.get("status") == "queued"
            for item in messages
        ),
        "steer_available": bool(
            route and route.supports_operator_steer and not _is_terminal_state(state)
        ),
    }


def operator_message_state(root: Path, run_dir: Path) -> dict[str, Any]:
    """Return summarized interaction state for ``derive_operator_state``."""

    del root
    rows = _read_message_rows(run_dir)
    pending_steer = [
        item
        for item in rows
        if item.get("command_type") == "steer" and item.get("status") == "queued"
    ]
    return {
        "operator_session_id": _session_id_from_run_state(run_dir),
        "message_count": len(rows),
        "pending_steer_count": len(pending_steer),
        "operator_message_pending": bool(pending_steer),
        "latest_message": rows[-1] if rows else {},
    }


def check_operator_messages_for_mcp(run_dir: Path, *, max_messages: int = 10) -> dict[str, Any]:
    """Return queued steer messages and mark them seen for MCP delivery."""

    wrapper_dir = _wrapper_dir_for_display(run_dir)
    rows = _read_message_rows(wrapper_dir)
    selected: list[dict[str, Any]] = []
    next_rows: list[dict[str, Any]] = []
    now = _utc_now()
    for row in rows:
        if (
            row.get("command_type") == "steer"
            and row.get("status") == "queued"
            and len(selected) < max_messages
        ):
            updated = dict(row)
            updated["status"] = "seen"
            updated["seen_at_epoch"] = now
            updated["seen_at"] = _format_epoch(now)
            selected.append(_public_mcp_message(updated))
            next_rows.append(updated)
            continue
        next_rows.append(row)
    if selected:
        _rewrite_messages(wrapper_dir, next_rows)
    return {
        "ok": True,
        "tool": "check_operator_messages",
        "status": "seen" if selected else "empty",
        "operator_message_pending": any(
            item.get("command_type") == "steer" and item.get("status") == "queued"
            for item in next_rows
        ),
        "messages": selected,
        "message_count": len(selected),
        "instruction": (
            "Treat seen operator messages as public steering hints. Acknowledge by "
            "following the safe checkpoint guidance or explain why a message cannot be applied."
        ),
    }


def pending_operator_message_hint(run_dir: Path) -> dict[str, Any]:
    wrapper_dir = _wrapper_dir_for_display(run_dir)
    pending = [
        row
        for row in _read_message_rows(wrapper_dir)
        if row.get("command_type") == "steer" and row.get("status") == "queued"
    ]
    if not pending:
        return {}
    return {
        "operator_message_pending": True,
        "pending_operator_message_count": len(pending),
        "operator_message_instruction": (
            "Unread operator steering exists. Call check_operator_messages at the next "
            "safe checkpoint to read and acknowledge it."
        ),
    }


def _base_message(
    *,
    command_type: str,
    run_id: str,
    body: str,
    status: str,
) -> dict[str, Any]:
    now = _utc_now()
    return {
        "schema": MESSAGE_SCHEMA,
        "message_id": _new_id(command_type),
        "command_type": command_type,
        "run_id": run_id,
        "body": body,
        "status": status,
        "created_at_epoch": now,
        "created_at": _format_epoch(now),
    }


def _ask_why_answer(root: Path, state: dict[str, Any], question: str) -> dict[str, Any]:
    decision = state.get("latest_public_decision_evidence")
    if not isinstance(decision, dict):
        decision = {}
    public_result = state.get("public_run_result")
    if not isinstance(public_result, dict):
        public_result = {}
    artifacts = state.get("artifact_paths") if isinstance(state.get("artifact_paths"), list) else []
    public_artifacts = _public_artifact_scope(artifacts)
    evidence_bits = [
        str(decision.get("observation_summary") or ""),
        str(decision.get("decision") or decision.get("reasoning") or ""),
        str(state.get("latest_action") or ""),
        json.dumps(public_result, sort_keys=True),
    ]
    text = " ".join(item for item in evidence_bits if item).strip()
    if not text:
        text = "No public robot-tool evidence has been written for this run yet."
    text = _strip_private_terms(text)
    return {
        "question": question,
        "summary": text[:1200],
        "basis": "public_operator_artifacts_only",
        "robot_mcp_tools_called": False,
        "private_evaluation_used": False,
        "artifact_scope": public_artifacts,
        "report_href": _first_artifact_href(artifacts, "Report"),
        "run_dir": str(state.get("display_run_dir") or state.get("run_dir") or root),
    }


def _continuation_packet(
    state: dict[str, Any],
    session: dict[str, Any],
    parent_run_id: str,
    prompt: str,
) -> dict[str, Any]:
    artifacts = state.get("artifact_paths") if isinstance(state.get("artifact_paths"), list) else []
    packet = {
        "schema": "operator_console_continuation_packet_v1",
        "operator_session_id": session["operator_session_id"],
        "parent_run_id": parent_run_id,
        "operator_prompt": prompt,
        "parent_public_summary": {
            "status": state.get("status"),
            "phase": state.get("phase"),
            "latest_action": state.get("latest_action"),
            "public_run_result": state.get("public_run_result") or {},
            "latest_public_decision_evidence": state.get("latest_public_decision_evidence") or {},
        },
        "artifact_scope": _public_artifact_scope(artifacts),
        "instruction": (
            "This is a linked follow-up Robot Run. Use only public parent context; "
            "do not mutate or reinterpret the parent run report."
        ),
    }
    return _strip_private_payload(packet)


def _public_artifact_scope(artifacts: list[Any]) -> list[dict[str, str]]:
    allowed_labels = {
        "Operator State",
        "Report",
        "Run Result",
        "Trace",
        "Agent Events",
        "Claude Events",
        "OpenAI Agents Events",
        "Runtime Map",
        "Actionable Map",
    }
    output: list[dict[str, str]] = []
    for item in artifacts:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "")
        if label not in allowed_labels:
            continue
        output.append(
            {
                "label": label,
                "kind": str(item.get("kind") or ""),
                "href": str(item.get("href") or ""),
                "path": str(item.get("path") or ""),
            }
        )
    return output


def _run_context(root: Path, run_id: str) -> tuple[Path, ConsoleRoute | None]:
    if not run_id:
        raise InteractionError("run_id is required.")
    run_dir = console_output_root(root) / "runs" / run_id
    if not run_dir.is_dir():
        raise InteractionError(f"unknown run: {run_id}")
    state = _read_json(run_dir / "operator_state.json")
    route_payload = state.get("route") if isinstance(state.get("route"), dict) else {}
    route_id = str(route_payload.get("id") or "")
    try:
        route = get_route(route_id) if route_id else None
    except KeyError:
        route = None
    return run_dir, route


def _is_terminal_state(state: dict[str, Any]) -> bool:
    values = {
        str(state.get("status") or "").lower(),
        str(state.get("phase") or "").lower(),
        str(state.get("terminal_reason") or "").lower(),
    }
    if values & TERMINAL_STATUSES:
        return True
    checker = state.get("checker_status")
    return isinstance(checker, dict) and str(checker.get("status") or "").lower() == "passed"


def _parent_result_available(run_dir: Path, state: dict[str, Any]) -> bool:
    if (resolve_display_run_dir(run_dir) / "run_result.json").is_file():
        return True
    checker = state.get("checker_status")
    return isinstance(checker, dict) and bool(checker.get("report_exists"))


def _terminal_success(state: dict[str, Any]) -> bool:
    status = str(state.get("status") or "").lower()
    phase = str(state.get("phase") or "").lower()
    if status in {"failed", "stopped_by_operator", "human_takeover_stop", "emergency_stopped"}:
        return False
    if phase in {"failed", "stopped_by_operator", "human_takeover_stop", "emergency_stopped"}:
        return False
    checker = state.get("checker_status")
    if isinstance(checker, dict) and str(checker.get("status") or "").lower() == "failed":
        return False
    return True


def _requires_continue_confirmation(route: ConsoleRoute | None) -> bool:
    if route is None:
        return True
    return route.emergency_stop_required or route.resource_kind in {"physical_robot", "real_robot"}


def _session_for_run(root: Path, run_dir: Path, run_id: str) -> dict[str, Any]:
    session_id = _session_id_from_run_state(run_dir)
    if session_id:
        try:
            return get_operator_session(root, session_id)
        except InteractionError:
            pass
    return attach_run_to_session(root, run_id)


def _record_session_message(root: Path, run_dir: Path, message: dict[str, Any]) -> None:
    state = _read_json(run_dir / "operator_state.json")
    session_id = str(state.get("operator_session_id") or message.get("operator_session_id") or "")
    if not session_id:
        session = attach_run_to_session(root, str(message.get("run_id") or run_dir.name))
        session_id = session["operator_session_id"]
    try:
        session = get_operator_session(root, session_id)
    except InteractionError:
        return
    message_ids = list(session.get("message_ids") or [])
    message_id = str(message.get("message_id") or "")
    if message_id and message_id not in message_ids:
        message_ids.append(message_id)
    session["message_ids"] = message_ids
    if str(message.get("run_id") or ""):
        run_ids = list(session.get("run_ids") or [])
        if message["run_id"] not in run_ids:
            run_ids.append(message["run_id"])
        session["run_ids"] = run_ids
    _write_session(root, session)


def _session_id_from_run_state(run_dir: Path) -> str:
    state = _read_json(run_dir / "operator_state.json")
    return str(state.get("operator_session_id") or "")


def _write_session(root: Path, session: dict[str, Any]) -> None:
    session_id = str(session.get("operator_session_id") or "")
    if not session_id:
        raise InteractionError("operator session id is required.")
    path = _session_path(root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(session, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _append_message(run_dir: Path, message: dict[str, Any]) -> None:
    _append_jsonl(run_dir / MESSAGE_LOG, _strip_private_payload(message))


def _read_message_rows(run_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    path = _message_log_path(run_dir)
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _rewrite_messages(run_dir: Path, rows: list[dict[str, Any]]) -> None:
    path = _message_log_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True) + "\n")


def _message_log_path(run_dir: Path) -> Path:
    return run_dir / MESSAGE_LOG


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _session_path(root: Path, session_id: str) -> Path:
    return console_output_root(root) / SESSION_DIR / f"{session_id}.json"


def _session_log_path(root: Path) -> Path:
    return console_output_root(root) / SESSION_LOG


def _new_id(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def _utc_now() -> float:
    return time.time()


def _format_epoch(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").split())


def _strip_private_payload(payload: dict[str, Any]) -> dict[str, Any]:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for term in PRIVATE_TERMS:
        text = text.replace(term, "[redacted_private_field]")
    try:
        redacted = json.loads(text)
    except json.JSONDecodeError:
        return payload
    return redacted if isinstance(redacted, dict) else payload


def _strip_private_terms(text: str) -> str:
    output = text
    for term in PRIVATE_TERMS:
        output = output.replace(term, "[redacted_private_field]")
    return output


def _first_artifact_href(artifacts: list[Any], label: str) -> str:
    for item in artifacts:
        if isinstance(item, dict) and item.get("label") == label:
            return str(item.get("href") or "")
    return ""


def _public_mcp_message(message: dict[str, Any]) -> dict[str, Any]:
    return {
        "message_id": str(message.get("message_id") or ""),
        "status": str(message.get("status") or ""),
        "body": str(message.get("body") or ""),
        "created_at": str(message.get("created_at") or ""),
    }


def _wrapper_dir_for_display(run_dir: Path) -> Path:
    run_dir = Path(run_dir).resolve()
    if (run_dir / "operator_state.json").exists():
        return run_dir
    for parent in run_dir.parents:
        if (parent / "operator_state.json").exists():
            return parent
    return run_dir

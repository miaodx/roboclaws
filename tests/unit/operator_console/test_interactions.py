from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.operator_console.interactions import (
    InteractionError,
    append_next_goal_request,
    append_steer_message,
    attach_run_to_session,
    check_operator_messages_for_mcp,
    list_operator_messages,
    operator_message_state,
    pending_operator_message_hint,
)
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import get_selection

MUJOCO_CODEX_OPEN_TASK = (
    "molmospaces/procthor-objaverse-val/0::mujoco::open-task::codex-cli::world-public-labels"
)


def _write_run(
    root: Path,
    *,
    run_id: str = "run-a",
    selection_id: str = MUJOCO_CODEX_OPEN_TASK,
    phase: str = "running-codex",
    run_result: dict[str, object] | None = None,
) -> Path:
    route = get_selection(selection_id)
    run_dir = console_output_root(root) / "runs" / run_id
    run_dir.mkdir(parents=True)
    session = attach_run_to_session(root, run_id)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "operator_session_id": session["operator_session_id"],
                "route": route.to_payload(),
                "phase": phase,
                "backend_lock": route.lock_name,
                "run_dir": str(run_dir),
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "event": "response",
                "tool": "observe",
                "response": {
                    "ok": True,
                    "visible_object_detections": [{"object_id": "observed_001"}],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    if run_result is not None:
        (run_dir / "run_result.json").write_text(json.dumps(run_result), encoding="utf-8")
        (run_dir / "report.html").write_text("<html>ok</html>", encoding="utf-8")
    return run_dir


def test_steer_rejects_terminal_run_and_offers_next_goal(tmp_path: Path) -> None:
    _write_run(tmp_path, phase="finished", run_result={"cleanup_success": True})

    with pytest.raises(InteractionError, match="use Next Goal"):
        append_steer_message(tmp_path, "run-a", "Do not move the cup")


def test_next_goal_rejects_active_run_without_touching_steer_inbox(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, phase="running-codex")

    with pytest.raises(InteractionError, match="Use Steer"):
        append_next_goal_request(tmp_path, "run-a", "Now build the Runtime Metric Map")
    messages = list_operator_messages(tmp_path, "run-a")

    assert not any(item["command_type"] == "steer" for item in messages["messages"])
    assert not (run_dir / "next_goal_queue.jsonl").exists()
    assert not (run_dir / "continue_queue.jsonl").exists()


def test_terminal_simulator_next_goal_is_ready_with_public_packet(tmp_path: Path) -> None:
    _write_run(tmp_path, phase="finished", run_result={"cleanup_success": True})

    request = append_next_goal_request(tmp_path, "run-a", "Run the next sweep")

    assert request["command_type"] == "next_goal"
    assert request["status"] == "ready_to_start"
    assert request["auto_start_allowed"] is True
    assert request["queue_reason"] == "parent_terminal_and_result_available"
    assert request["operator_session_id"].startswith("session-")
    assert request["selection_id"] == MUJOCO_CODEX_OPEN_TASK
    assert request["next_goal_packet"]["instruction"].startswith(
        "This is a linked follow-up Robot Run"
    )


def test_failed_parent_next_goal_requires_confirmation(tmp_path: Path) -> None:
    _write_run(tmp_path, phase="failed", run_result={"cleanup_success": False})

    request = append_next_goal_request(tmp_path, "run-a", "Try the next goal")
    confirmed = append_next_goal_request(
        tmp_path,
        "run-a",
        "Try the next goal",
        confirmed=True,
    )

    assert request["command_type"] == "next_goal"
    assert request["status"] == "confirmation_required"
    assert request["auto_start_allowed"] is False
    assert request["confirmation_required"] is True
    assert request["queue_reason"] == "operator_confirmation_required_after_parent_terminal_status"
    assert confirmed["status"] == "ready_to_start"
    assert confirmed["confirmed"] is True


def test_active_steer_is_seen_only_by_check_operator_messages(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, phase="running-codex")

    steer = append_steer_message(tmp_path, "run-a", "Observe the desk again")
    before = list_operator_messages(tmp_path, "run-a")
    seen = check_operator_messages_for_mcp(run_dir)
    after = list_operator_messages(tmp_path, "run-a")

    assert steer["status"] == "queued"
    assert before["operator_message_pending"] is True
    assert seen["message_count"] == 1
    assert seen["messages"][0]["body"] == "Observe the desk again"
    assert after["operator_message_pending"] is False
    assert after["messages"][0]["status"] == "seen"


def test_operator_message_state_surfaces_malformed_source_errors(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, phase="running-codex")
    (run_dir / "operator_messages.jsonl").write_text("\n{not-json}\n", encoding="utf-8")

    messages = list_operator_messages(tmp_path, "run-a")
    state = operator_message_state(tmp_path, run_dir)
    seen = check_operator_messages_for_mcp(run_dir)
    hint = pending_operator_message_hint(run_dir)

    assert messages["source_error"] is True
    assert messages["source_errors"][0]["line"] == 2
    assert "invalid JSON" in messages["source_errors"][0]["message"]
    assert messages["operator_message_pending"] is False
    assert state["source_error"] is True
    assert state["pending_steer_count"] == 0
    assert seen["ok"] is False
    assert seen["status"] == "source_error"
    assert seen["error_reason"] == "operator_message_source_error"
    assert "operator_messages.jsonl" in seen["source_errors"][0]["path"]
    assert hint["operator_message_source_error"] is True
    assert (run_dir / "operator_messages.jsonl").read_text(encoding="utf-8") == "\n{not-json}\n"


def test_operator_message_state_surfaces_non_object_source_errors(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, phase="running-codex")
    (run_dir / "operator_messages.jsonl").write_text("[]\n", encoding="utf-8")

    messages = list_operator_messages(tmp_path, "run-a")
    seen = check_operator_messages_for_mcp(run_dir)

    assert messages["source_error"] is True
    assert messages["source_errors"][0]["line"] == 1
    assert messages["source_errors"][0]["message"] == "row must be a JSON object"
    assert messages["messages"] == []
    assert seen["ok"] is False
    assert seen["message_count"] == 0

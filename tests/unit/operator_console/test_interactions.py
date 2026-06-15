from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.operator_console.interactions import (
    InteractionError,
    append_ask_why,
    append_next_goal_request,
    append_steer_message,
    attach_run_to_session,
    check_operator_messages_for_mcp,
    list_operator_messages,
)
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import get_selection

MUJOCO_CODEX_CLEANUP = "molmospaces/val_0::mujoco::cleanup::codex-cli::world-oracle-labels"


def _write_run(
    root: Path,
    *,
    run_id: str = "run-a",
    selection_id: str = MUJOCO_CODEX_CLEANUP,
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


def test_ask_why_uses_public_artifacts_without_private_terms(tmp_path: Path) -> None:
    _write_run(
        tmp_path,
        phase="finished",
        run_result={
            "cleanup_success": True,
            "private_manifest": {"must_not": "leak"},
            "generated_mess_set": ["cup"],
        },
    )

    answer = append_ask_why(tmp_path, "run-a", "Why did it observe first?")

    assert answer["command_type"] == "ask_why"
    assert answer["status"] == "answered"
    assert answer["answer"]["robot_mcp_tools_called"] is False
    assert answer["answer"]["private_evaluation_used"] is False
    assert "private_manifest" not in json.dumps(answer)
    assert "generated_mess_set" not in json.dumps(answer)


def test_ask_why_explains_missing_target_from_public_trace_and_runtime_map(
    tmp_path: Path,
) -> None:
    run_dir = _write_run(tmp_path, phase="finished")
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "request",
                        "tool": "resolve_target_query",
                        "request": {
                            "operation": "photograph",
                            "query": "chair",
                            "max_results": 10,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "resolve_target_query",
                        "response": {
                            "ok": True,
                            "query": "chair",
                            "status": "not_found",
                            "missing_target_reason": "public_search_budget_exhausted",
                            "match_count": 0,
                            "candidate_count": 51,
                            "public_search_budget": {
                                "viewpoint_budget": {
                                    "visited_waypoint_count": 14,
                                    "total_public_waypoints": 14,
                                    "unvisited_waypoint_count": 0,
                                },
                                "inspection_observation_count": 14,
                            },
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "runtime_metric_map.json").write_text(
        json.dumps(
            {
                "target_search_summary": {
                    "candidate_count": 51,
                    "viewpoint_budget": {
                        "visited_waypoint_count": 14,
                        "total_public_waypoints": 14,
                        "unvisited_waypoint_count": 0,
                    },
                    "inspection_observations": [{}, {}],
                },
                "target_candidates": [
                    {"category": "DiningTable", "label": "DiningTable"},
                    {"category": "Sofa", "label": "Sofa"},
                ],
            }
        ),
        encoding="utf-8",
    )

    answer = append_ask_why(tmp_path, "run-a", "为什么没有看到椅子？")
    summary = answer["answer"]["summary"]

    assert "resolve_target_query(chair)" in summary
    assert "public_search_budget_exhausted" in summary
    assert "visited 14/14 public waypoint(s)" in summary
    assert "runtime map has 51 target candidate(s)" in summary
    assert "private" not in summary.lower()


def test_steer_rejects_terminal_run_and_offers_next_goal(tmp_path: Path) -> None:
    _write_run(tmp_path, phase="finished", run_result={"cleanup_success": True})

    with pytest.raises(InteractionError, match="use Next Goal"):
        append_steer_message(tmp_path, "run-a", "Do not move the cup")


def test_next_goal_rejects_active_run_without_touching_steer_inbox(tmp_path: Path) -> None:
    run_dir = _write_run(tmp_path, phase="running-codex")

    with pytest.raises(InteractionError, match="Use Steer or Ask Why"):
        append_next_goal_request(tmp_path, "run-a", "Now build the semantic map")
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
    assert request["selection_id"] == MUJOCO_CODEX_CLEANUP
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

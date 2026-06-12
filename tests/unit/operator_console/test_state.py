from __future__ import annotations

import json
import os
from pathlib import Path

from roboclaws.operator_console.routes import get_route
from roboclaws.operator_console.state import (
    derive_operator_state,
    redacted_artifact_text,
    resolve_display_run_dir,
)


def test_state_derives_latest_tool_checker_and_artifact_links(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "running",
                "backend_lock": "molmospaces_mujoco",
                "started_at_epoch": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text(
        json.dumps({"event": "request", "tool": "observe"})
        + "\n"
        + json.dumps(
            {
                "event": "response",
                "tool": "pick",
                "ok": True,
                "observation_summary": "saw a mug",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "task": "clean the room",
                "success": True,
                "private_target_truth": {"must_not": "leak"},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "report.html").write_text("<html></html>", encoding="utf-8")

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["status"] == "passed"
    assert state["latest_action"] == "pick"
    assert state["latest_public_decision_evidence"]["observation_summary"] == "saw a mug"
    assert state["checker_status"]["status"] == "passed"
    assert "private_target_truth" not in json.dumps(state["public_run_result"])
    assert any(item["label"] == "Report" for item in state["artifact_paths"])


def test_state_follows_nested_live_attempt_under_console_wrapper(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "wrapper-run"
    attempt_dir = run_dir / "0608_1807" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "wrapper-run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "starting",
                "backend_lock": "molmospaces_mujoco",
                "started_at_epoch": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "console-launch.log").write_text("detached\n", encoding="utf-8")
    (attempt_dir / "live_status.json").write_text(
        json.dumps(
            {
                "phase": "running-codex",
                "started_at_epoch": 2.0,
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "trace.jsonl").write_text(
        json.dumps({"tool": "observe", "ok": True, "observation_summary": "plate visible"}) + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "driver.log").write_text("==> Codex turn 2/9\n", encoding="utf-8")

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert resolve_display_run_dir(run_dir) == attempt_dir.resolve()
    assert state["run_id"] == "wrapper-run"
    assert state["display_run_id"] == "0608_1807/seed-7"
    assert state["run_dir"] == str(run_dir.resolve())
    assert state["display_run_dir"] == str(attempt_dir.resolve())
    assert state["phase"] == "running-codex"
    assert state["latest_action"] == "observe"
    assert state["latest_public_decision_evidence"]["observation_summary"] == "plate visible"
    assert any(
        item["label"] == "Driver Log" and "0608_1807" in item["path"]
        for item in state["artifact_paths"]
    )
    assert any(item["label"] == "Console Launch Log" for item in state["artifact_paths"])


def test_state_summarizes_nested_mcp_trace_responses_for_live_decision(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "wrapper-run"
    attempt_dir = run_dir / "0608_2103" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "wrapper-run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "starting",
                "backend_lock": "molmospaces_mujoco",
                "started_at_epoch": 1.0,
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex", "started_at_epoch": 2.0}),
        encoding="utf-8",
    )
    (attempt_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "event": "response",
                "tool": "navigate_to_waypoint",
                "request": {"waypoint_id": "generated_exploration_005"},
                "response": {
                    "ok": True,
                    "status": "ok",
                    "tool": "navigate_to_waypoint",
                    "waypoint_id": "generated_exploration_005",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (attempt_dir / "codex-events.jsonl").write_text(
        json.dumps(
            {
                "type": "item.completed",
                "item": {
                    "type": "agent_message",
                    "text": "Moving to waypoint 005 and continuing the sweep.",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["status"] == "running-codex"
    assert state["latest_action"] == "navigate_to_waypoint"
    assert (
        state["latest_public_decision_evidence"]["observation_summary"]
        == "navigate_to_waypoint completed for waypoint_id=generated_exploration_005."
    )
    assert (
        state["latest_public_decision_evidence"]["decision"]
        == "Moving to waypoint 005 and continuing the sweep."
    )
    assert state["latest_tool_call"]["ok"] is True
    assert state["latest_tool_call"]["arguments"] == {"waypoint_id": "generated_exploration_005"}
    assert state["checker_status"]["status"] == "waiting"
    assert (
        state["checker_status"]["message"]
        == "Checker will run when the live agent hands off to result checking."
    )


def test_state_ignores_runtime_capture_when_selecting_latest_robot_tool(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "wrapper-run"
    attempt_dir = run_dir / "0608_2103" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "wrapper-run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "starting",
                "backend_lock": "molmospaces_mujoco",
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex"}),
        encoding="utf-8",
    )
    (attempt_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "event": "response",
                "tool": "observe",
                "request": {},
                "response": {
                    "ok": True,
                    "status": "ok",
                    "tool": "observe",
                    "visible_object_detections": [{"object_id": "observed_004"}],
                },
            }
        )
        + "\n"
        + json.dumps(
            {
                "event": "robot_view_capture",
                "tool": "<runtime>",
                "action": "observe",
                "label": "0042_observe",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["latest_action"] == "observe"
    assert (
        state["latest_public_decision_evidence"]["observation_summary"]
        == "observe completed with 1 visible detection(s)."
    )
    assert state["latest_tool_call"]["name"] == "observe"
    assert state["latest_tool_call"]["ok"] is True


def test_state_prefers_robot_view_map_over_newer_report_map_bundle_preview(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "run"
    robot_views = run_dir / "robot_views"
    map_bundle = run_dir / "map_bundle"
    robot_views.mkdir(parents=True)
    map_bundle.mkdir()
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "running",
                "backend_lock": "molmospaces_mujoco",
            }
        ),
        encoding="utf-8",
    )
    robot_map = robot_views / "0042_observe.map.png"
    report_map = map_bundle / "report_static_navigation_map.png"
    robot_map.write_bytes(b"robot map")
    report_map.write_bytes(b"report map")
    os.utime(robot_map, (1, 1))
    os.utime(report_map, (2, 2))

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["latest_view_assets"]["map"]["path"] == str(robot_map.resolve())


def test_state_surfaces_provider_transient_reason(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "wrapper-run"
    attempt_dir = run_dir / "0608_1921" / "seed-7"
    attempt_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "wrapper-run",
                "route": get_route("codex-mujoco-cleanup").to_payload(),
                "phase": "starting",
                "backend_lock": "molmospaces_mujoco",
            }
        ),
        encoding="utf-8",
    )
    (attempt_dir / "live_status.json").write_text(
        json.dumps(
            {
                "phase": "failed",
                "exit_status": 1,
                "reason": "provider_transient_failure",
                "provider_reason": "rate_limit",
                "retryable": True,
                "resume_available": True,
            }
        ),
        encoding="utf-8",
    )

    state = derive_operator_state(tmp_path, run_dir, get_route("codex-mujoco-cleanup"))

    assert state["phase"] == "failed"
    assert state["status"] == "provider_transient_failed"
    assert state["status_label"] == "Provider transient failure"
    assert state["terminal_reason"] == "provider_transient_failure"


def test_redacted_artifact_text_redacts_secrets(tmp_path: Path) -> None:
    log = tmp_path / "driver.log"
    log.write_text("Authorization: Bearer top-secret\n", encoding="utf-8")
    assert "top-secret" not in redacted_artifact_text(log)


def test_redacted_artifact_text_truncates_with_tail_visible(tmp_path: Path) -> None:
    log = tmp_path / "driver.log"
    log.write_text(
        "start\n" + ("middle\n" * 20) + "final molmospaces import error\n",
        encoding="utf-8",
    )

    text = redacted_artifact_text(log, max_bytes=80)

    assert "start" in text
    assert "operator console truncated" in text
    assert "final molmospaces import error" in text

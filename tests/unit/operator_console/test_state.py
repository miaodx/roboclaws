from __future__ import annotations

import json
from pathlib import Path

from roboclaws.operator_console.routes import get_route
from roboclaws.operator_console.state import derive_operator_state, redacted_artifact_text


def test_state_derives_latest_tool_checker_and_artifact_links(tmp_path: Path) -> None:
    run_dir = tmp_path / "output" / "operator-console" / "runs" / "run"
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": "run",
                "route": get_route("mujoco-cleanup").to_payload(),
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

    state = derive_operator_state(tmp_path, run_dir, get_route("mujoco-cleanup"))

    assert state["status"] == "passed"
    assert state["latest_action"] == "pick"
    assert state["latest_public_decision_evidence"]["observation_summary"] == "saw a mug"
    assert state["checker_status"]["status"] == "passed"
    assert "private_target_truth" not in json.dumps(state["public_run_result"])
    assert any(item["label"] == "Report" for item in state["artifact_paths"])


def test_redacted_artifact_text_redacts_secrets(tmp_path: Path) -> None:
    log = tmp_path / "driver.log"
    log.write_text("Authorization: Bearer top-secret\n", encoding="utf-8")
    assert "top-secret" not in redacted_artifact_text(log)

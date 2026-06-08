from __future__ import annotations

import json
from pathlib import Path

import pytest

from roboclaws.agents.drivers.openai_agents_live import OpenAIAgentsLiveRuntime
from roboclaws.agents.live_runtime import (
    LiveAgentMCPServer,
    LiveAgentRequest,
    LiveAgentResult,
    live_agent_result_from_artifacts,
)
from roboclaws.agents.live_status import LiveAgentFailure


def test_live_agent_request_keeps_one_turn_policy_explicit(tmp_path: Path) -> None:
    request = LiveAgentRequest(
        task_name="household-cleanup",
        skill_name="molmo-realworld-cleanup",
        kickoff_prompt="clean the room",
        mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
        run_dir=tmp_path / "run",
        artifact_paths={"live_status": tmp_path / "status.json"},
    )

    assert request.one_turn is True
    assert request.max_turns is None
    assert request.artifact_path("live_status", "live_status.json") == tmp_path / "status.json"
    assert request.artifact_path("events", "events.jsonl") == tmp_path / "run" / "events.jsonl"


def test_live_agent_request_rejects_invalid_sdk_turn_budget(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="max_turns must be >= 1"):
        LiveAgentRequest(
            task_name="household-cleanup",
            skill_name="molmo-realworld-cleanup",
            kickoff_prompt="clean the room",
            mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
            run_dir=tmp_path / "run",
            max_turns=0,
        )


def test_live_agent_result_from_failure_matches_live_status_fields() -> None:
    result = LiveAgentResult.from_failure(
        phase="failed",
        exit_status=1,
        failure=LiveAgentFailure(
            reason="provider_transient_failure",
            provider_reason="rate_limit",
            retryable=True,
            resume_available=True,
            detail="429 Too Many Requests",
        ),
        started_at_epoch=10.0,
        finished_at_epoch=12.0,
    )

    assert result.to_live_status_payload() == {
        "phase": "failed",
        "started_at_epoch": 10.0,
        "finished_at_epoch": 12.0,
        "exit_status": 1,
        "reason": "provider_transient_failure",
        "provider_reason": "rate_limit",
        "retryable": True,
        "resume_available": True,
        "detail": "429 Too Many Requests",
    }


def test_live_agent_result_reads_existing_cli_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "live_status.json").write_text(
        json.dumps(
            {
                "phase": "failed",
                "exit_status": 1,
                "reason": "tool_binding_failure",
                "retryable": False,
                "resume_available": False,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "run_result.json").write_text(
        json.dumps(
            {
                "task_name": "household-cleanup",
                "cleanup_success": False,
                "private_target_truth": {"must_not": "drive runtime status"},
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "codex-events.jsonl").write_text('{"type":"error"}\n', encoding="utf-8")

    result = live_agent_result_from_artifacts(run_dir)

    assert result.phase == "failed"
    assert result.reason == "tool_binding_failure"
    assert result.retryable is False
    assert result.resume_available is False
    assert result.run_result_present is True
    assert result.task_completion == {
        "task_name": "household-cleanup",
        "cleanup_success": False,
    }
    assert result.artifact_paths["codex_events"] == run_dir / "codex-events.jsonl"


def test_openai_agents_runtime_missing_sdk_writes_normalized_failure(
    tmp_path: Path, monkeypatch
) -> None:
    def missing_sdk(*_args, **_kwargs):
        raise ImportError("no module named agents")

    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_openai_agents",
        missing_sdk,
    )
    request = LiveAgentRequest(
        task_name="household-cleanup",
        skill_name="molmo-realworld-cleanup",
        kickoff_prompt="clean the room",
        mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
        run_dir=tmp_path / "run",
    )

    result = OpenAIAgentsLiveRuntime().run(request)

    assert result.phase == "failed"
    assert result.exit_status == 1
    assert result.reason == "provider_config_failure"
    assert result.retryable is False
    payload = json.loads((tmp_path / "run" / "live_status.json").read_text(encoding="utf-8"))
    assert payload["reason"] == "provider_config_failure"
    assert "not installed" in payload["detail"]


def test_openai_agents_runtime_turn_completion_does_not_infer_cleanup_success(
    tmp_path: Path, monkeypatch
) -> None:
    class FakeSDKResult:
        final_output = "I stopped before calling done."
        trace_id = "trace_123"
        usage = {"requests": 1}

    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_openai_agents",
        lambda *_args, **_kwargs: FakeSDKResult(),
    )
    request = LiveAgentRequest(
        task_name="household-cleanup",
        skill_name="molmo-realworld-cleanup",
        kickoff_prompt="clean the room",
        mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
        run_dir=tmp_path / "run",
    )

    result = OpenAIAgentsLiveRuntime().run(request)

    assert result.phase == "agent-turn-complete"
    assert result.exit_status == 0
    assert result.run_result_present is False
    assert result.trace_id == "trace_123"
    payload = json.loads((tmp_path / "run" / "live_status.json").read_text(encoding="utf-8"))
    assert payload["phase"] == "agent-turn-complete"
    assert payload["trace_id"] == "trace_123"
    trace_payload = json.loads((tmp_path / "run" / "openai-agents-trace.json").read_text())
    assert trace_payload["final_output"] == "I stopped before calling done."

from __future__ import annotations

import json
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

from roboclaws.agents.drivers.openai_agents_live import OpenAIAgentsLiveRuntime
from roboclaws.agents.live_runtime import (
    LiveAgentMCPServer,
    LiveAgentRequest,
    LiveAgentResult,
    live_agent_result_from_artifacts,
)
from roboclaws.agents.live_status import LiveAgentFailure
from scripts.molmo_cleanup.run_live_openai_agents_cleanup import LiveOpenAIAgentsCleanupRunner


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


def test_openai_agents_runtime_defaults_to_codex_env_responses_profile(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIResponsesModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["responses_model"] = self
            captured["model"] = model
            captured["client"] = openai_client

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setenv("CODEX_BASE_URL", "https://codex.example.test/v1")
    monkeypatch.setenv("CODEX_API_KEY", "fake-codex-key")
    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_with_async_mcp_server",
        lambda *_args, **_kwargs: SimpleNamespace(final_output="done"),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents",
        SimpleNamespace(
            Agent=lambda **kwargs: captured.setdefault("agent_kwargs", kwargs),
            Runner=SimpleNamespace(
                run_sync=lambda *_args, **kwargs: (
                    captured.setdefault("runner_kwargs", kwargs) or SimpleNamespace()
                )
            ),
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(MCPServerStreamableHttp=lambda **kwargs: SimpleNamespace(kwargs=kwargs)),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "openai",
        SimpleNamespace(AsyncOpenAI=FakeAsyncOpenAI),
    )
    request = LiveAgentRequest(
        task_name="household-cleanup",
        skill_name="molmo-realworld-cleanup",
        kickoff_prompt="clean the room",
        mcp_server=LiveAgentMCPServer(name="cleanup", url="http://127.0.0.1:18788/mcp"),
        run_dir=tmp_path / "run",
    )

    OpenAIAgentsLiveRuntime().run(request)

    assert captured["model"] == "gpt-5.5"
    assert captured["base_url"] == "https://codex.example.test/v1"
    assert captured["api_key"] == "fake-codex-key"
    assert captured["agent_kwargs"]["model"] is captured["responses_model"]
    assert captured["runner_kwargs"]["max_turns"] == 128


def test_openai_agents_cleanup_runner_invokes_sdk_then_checker(tmp_path: Path, monkeypatch) -> None:
    run_dir = tmp_path / "run"
    checker_commands: list[list[str]] = []

    class FakeProcess:
        pid = 4242

        def __init__(self, *_args, **_kwargs) -> None:
            self._poll: int | None = None

        def poll(self) -> int | None:
            return self._poll

        def wait(self, timeout: float | None = None) -> int:
            self._poll = 0
            return 0

        def terminate(self) -> None:
            self._poll = 0

        def kill(self) -> None:
            self._poll = 0

    class FakeRuntime:
        def run(self, request: LiveAgentRequest) -> LiveAgentResult:
            assert request.mcp_server.url == "http://127.0.0.1:18788/mcp"
            assert request.provider_profile == "codex-env"
            (request.run_dir / "run_result.json").write_text(
                json.dumps(
                    {
                        "task": "clean",
                        "task_name": "household-cleanup",
                        "backend": "molmospaces_subprocess",
                        "policy": "openai_agents_agent",
                        "cleanup_success": True,
                    }
                ),
                encoding="utf-8",
            )
            (request.run_dir / "openai-agents-events.jsonl").write_text(
                '{"event":"result"}\n',
                encoding="utf-8",
            )
            (request.run_dir / "openai-agents-trace.json").write_text(
                '{"trace_id":"trace_1"}\n',
                encoding="utf-8",
            )
            return LiveAgentResult(
                phase="finished",
                exit_status=0,
                trace_id="trace_1",
                run_result_present=True,
                usage={"requests": 1},
            )

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.subprocess.Popen",
        FakeProcess,
    )
    port_checks = iter([False, True])
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._port_accepting",
        lambda *_args, **_kwargs: next(port_checks),
    )
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.OpenAIAgentsLiveRuntime",
        lambda: FakeRuntime(),
    )

    def fake_run_and_tee(command, *, cwd, stdout_path, stderr_path, env):
        checker_commands.append(command)
        stdout_path.write_text("checker ok\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        fake_run_and_tee,
    )
    lock_path = tmp_path / "live.lock"
    args = Namespace(
        run_dir=run_dir,
        repo_root=Path.cwd(),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=lock_path,
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        server_startup_timeout_s=1.0,
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        task_name="household-cleanup",
        policy="openai_agents_agent",
        task="clean",
        min_generated_mess_count="5",
        profile="smoke",
        server_arg=[],
        checker_visual_arg=[],
    )

    status = LiveOpenAIAgentsCleanupRunner(args).run()

    assert status == 0
    status_payload = json.loads((run_dir / "live_status.json").read_text(encoding="utf-8"))
    assert status_payload["phase"] == "finished"
    assert status_payload["exit_status"] == 0
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert timing["runtime"] == "openai-agents-live"
    assert timing["openai_agents"]["trace_id"] == "trace_1"
    assert checker_commands
    checker_command = checker_commands[0]
    assert "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py" in checker_command
    assert "--expect-policy" in checker_command
    assert "openai_agents_agent" in checker_command
    assert "--require-clean-agent-run" in checker_command


def test_openai_agents_cleanup_runner_continues_incomplete_sdk_turn(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    checker_commands: list[list[str]] = []
    prompts: list[str] = []
    event_paths: list[Path] = []

    class FakeProcess:
        pid = 4242

        def __init__(self, *_args, **_kwargs) -> None:
            self._poll: int | None = None

        def poll(self) -> int | None:
            return self._poll

        def wait(self, timeout: float | None = None) -> int:
            self._poll = 0
            return 0

        def terminate(self) -> None:
            self._poll = 0

        def kill(self) -> None:
            self._poll = 0

    class FakeRuntime:
        def run(self, request: LiveAgentRequest) -> LiveAgentResult:
            prompts.append(request.kickoff_prompt)
            event_paths.append(request.artifact_path("openai_agents_events", "missing.jsonl"))
            if len(prompts) == 1:
                return LiveAgentResult(
                    phase="agent-turn-complete",
                    exit_status=0,
                    run_result_present=False,
                    trace_id="trace_initial",
                )
            assert "Continuation recovery" in request.kickoff_prompt
            assert request.metadata["attempt_role"] == "continuation"
            (request.run_dir / "run_result.json").write_text(
                json.dumps(
                    {
                        "task": "clean",
                        "task_name": "household-cleanup",
                        "backend": "molmospaces_subprocess",
                        "policy": "openai_agents_agent",
                        "cleanup_success": True,
                    }
                ),
                encoding="utf-8",
            )
            return LiveAgentResult(
                phase="finished",
                exit_status=0,
                run_result_present=True,
                trace_id="trace_continuation",
            )

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.subprocess.Popen",
        FakeProcess,
    )
    port_checks = iter([False, True])
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._port_accepting",
        lambda *_args, **_kwargs: next(port_checks),
    )
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.OpenAIAgentsLiveRuntime",
        lambda: FakeRuntime(),
    )

    def fake_run_and_tee(command, *, cwd, stdout_path, stderr_path, env):
        checker_commands.append(command)
        stdout_path.write_text("checker ok\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        fake_run_and_tee,
    )
    args = Namespace(
        run_dir=run_dir,
        repo_root=Path.cwd(),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=2,
        server_startup_timeout_s=1.0,
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        task_name="household-cleanup",
        policy="openai_agents_agent",
        task="clean",
        min_generated_mess_count="5",
        profile="smoke",
        server_arg=[],
        checker_visual_arg=[],
    )

    status = LiveOpenAIAgentsCleanupRunner(args).run()

    assert status == 0
    assert len(prompts) == 2
    assert event_paths == [
        run_dir / "openai-agents-events.jsonl",
        run_dir / "openai-agents-events.continuation-1.jsonl",
    ]
    assert checker_commands
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert [item["attempt_role"] for item in timing["openai_agents_attempts"]] == [
        "initial",
        "continuation",
    ]
    assert timing["openai_agents_attempts"][0]["recovery_action"] == "continue"
    assert timing["openai_agents"]["trace_id"] == "trace_continuation"


def test_openai_agents_cleanup_runner_fails_after_bounded_continuation(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    prompts: list[str] = []
    checker_called = False

    class FakeProcess:
        pid = 4242

        def __init__(self, *_args, **_kwargs) -> None:
            self._poll: int | None = None

        def poll(self) -> int | None:
            return self._poll

        def wait(self, timeout: float | None = None) -> int:
            self._poll = 0
            return 0

        def terminate(self) -> None:
            self._poll = 0

        def kill(self) -> None:
            self._poll = 0

    class FakeRuntime:
        def run(self, request: LiveAgentRequest) -> LiveAgentResult:
            prompts.append(request.kickoff_prompt)
            return LiveAgentResult(
                phase="agent-turn-complete",
                exit_status=0,
                run_result_present=False,
                trace_id=f"trace_{len(prompts)}",
            )

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.subprocess.Popen",
        FakeProcess,
    )
    port_checks = iter([False, True])
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._port_accepting",
        lambda *_args, **_kwargs: next(port_checks),
    )
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup.OpenAIAgentsLiveRuntime",
        lambda: FakeRuntime(),
    )

    def fake_run_and_tee(*_args, **_kwargs):
        nonlocal checker_called
        checker_called = True
        return 0

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        fake_run_and_tee,
    )
    args = Namespace(
        run_dir=run_dir,
        repo_root=Path.cwd(),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=1,
        server_startup_timeout_s=1.0,
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        task_name="household-cleanup",
        policy="openai_agents_agent",
        task="clean",
        min_generated_mess_count="5",
        profile="smoke",
        server_arg=[],
        checker_visual_arg=[],
    )

    status = LiveOpenAIAgentsCleanupRunner(args).run()

    assert status == 1
    assert len(prompts) == 2
    assert checker_called is False
    status_payload = json.loads((run_dir / "live_status.json").read_text(encoding="utf-8"))
    assert status_payload["phase"] == "failed"
    assert status_payload["exit_status"] == 1
    assert (
        status_payload["reason"]
        == "OpenAI Agents SDK turn ended without done after 2 OpenAI Agents SDK invocation(s)"
    )
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert len(timing["openai_agents_attempts"]) == 2
    assert timing["openai_agents"]["phase"] == "agent-turn-complete"

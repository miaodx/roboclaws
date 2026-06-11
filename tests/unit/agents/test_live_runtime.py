from __future__ import annotations

import asyncio
import json
from argparse import Namespace
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from roboclaws.agents.drivers.openai_agents_live import (
    OpenAIAgentsLiveRuntime,
    _compact_model_input_items,
    _failure_from_exception,
    _RetryingModel,
    _RoboclawsSpanRecorder,
    _should_retry_model_service_failure,
)
from roboclaws.agents.live_runtime import (
    LiveAgentMCPServer,
    LiveAgentRequest,
    LiveAgentResult,
    live_agent_result_from_artifacts,
)
from roboclaws.agents.live_status import LiveAgentFailure
from scripts.molmo_cleanup.run_live_openai_agents_cleanup import (
    IncompleteTurnRecoveryPolicy,
    LiveOpenAIAgentsCleanupRunner,
    _budget_failure_from_run_state,
    _cache_metrics,
    _context_growth_metrics,
    _context_metrics,
    _live_timing_timeline,
    _load_agent_sdk_skill_context,
    _mcp_control_plane_metrics,
    _model_input_filter_metrics,
    _model_service_fallback_metrics,
    _openai_agents_event_metrics,
    _openai_agents_span_metrics,
    _resolve_agent_sdk_perf_profile,
)


def _isolated_repo_root(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    return repo_root


class FakeModelSettings:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


class FakeRunConfig:
    def __init__(self, **kwargs) -> None:
        self.__dict__.update(kwargs)


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
    (run_dir / "openai-agents-spans.jsonl").write_text('{"event":"span_end"}\n', encoding="utf-8")

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
    assert result.artifact_paths["openai_agents_spans"] == run_dir / "openai-agents-spans.jsonl"


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


def test_openai_agents_runtime_classifies_context_window_before_502() -> None:
    failure = _failure_from_exception(
        RuntimeError(
            "Error code: 502 - {'error': {'message': 'Your input exceeds the context "
            "window of this model. Please adjust your input and try again.'}}"
        )
    )

    assert failure.reason == "provider_context_failure"
    assert failure.retryable is False
    assert failure.resume_available is False


def test_openai_agents_runtime_classifies_sdk_max_turn_budget() -> None:
    class MaxTurnsExceeded(Exception):
        pass

    failure = _failure_from_exception(MaxTurnsExceeded("Max turns (40) exceeded"))

    assert failure.reason == "agent_sdk_turn_budget_exceeded"
    assert failure.retryable is False
    assert failure.resume_available is False


def test_openai_agents_runtime_classifies_model_service_retryability() -> None:
    retryable_messages = [
        "Error code: 500 - internal server error",
        "model unavailable",
        "transport error: connection reset",
    ]
    for message in retryable_messages:
        should_retry, failure = _should_retry_model_service_failure(
            RuntimeError(message),
            attempt_index=0,
            retry_attempts=1,
        )
        assert should_retry is True
        assert failure.reason == "provider_transient_failure"
        assert failure.retryable is True

    non_retryable_messages = [
        "invalid api key 401",
        "codex-env requires CODEX_API_KEY",
        "Your input exceeds the context window",
        "tool failed while calling cleanup MCP",
    ]
    for message in non_retryable_messages:
        should_retry, failure = _should_retry_model_service_failure(
            RuntimeError(message),
            attempt_index=0,
            retry_attempts=1,
        )
        assert should_retry is False
        assert failure.retryable is False


def test_openai_agents_retrying_model_retries_transient_once(tmp_path: Path) -> None:
    class FakeModel:
        def __init__(self) -> None:
            self.calls = 0

        async def get_response(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("Error code: 503 - service unavailable")
            return SimpleNamespace(output="ok")

        async def close(self) -> None:
            return None

        def stream_response(self, *_args, **_kwargs):
            raise AssertionError("not used")

    events_path = tmp_path / "openai-agents-events.jsonl"
    spans_path = tmp_path / "openai-agents-spans.jsonl"
    model = _RetryingModel(
        FakeModel(),
        retry_attempts=1,
        retry_sleep_s=0,
        events_path=events_path,
        spans_path=spans_path,
        runtime_config={
            "runtime": "openai-agents-live",
            "provider_profile": "codex-env",
            "wire_api": "responses",
            "model": "gpt-5.5",
        },
    )

    result = asyncio.run(
        model.get_response(
            None,
            "clean the room",
            object(),
            [],
            None,
            [],
            object(),
            previous_response_id=None,
            conversation_id=None,
            prompt=None,
        )
    )

    assert result.output == "ok"
    events = [json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == [
        "model_service_attempt",
        "model_service_failure",
        "model_service_retry_scheduled",
        "model_service_attempt",
        "model_service_success",
    ]
    assert events[1]["failure_class"] == "provider_transient_failure"
    assert "clean the room" not in events_path.read_text(encoding="utf-8")
    span_events = [json.loads(line) for line in spans_path.read_text(encoding="utf-8").splitlines()]
    assert all(event["span_type"] == "model_service_fallback" for event in span_events)


def test_openai_agents_retrying_model_reports_retry_exhaustion(tmp_path: Path) -> None:
    class FakeModel:
        async def get_response(self, *_args, **_kwargs):
            raise RuntimeError("model unavailable")

        def stream_response(self, *_args, **_kwargs):
            raise AssertionError("not used")

    events_path = tmp_path / "openai-agents-events.jsonl"
    spans_path = tmp_path / "openai-agents-spans.jsonl"
    model = _RetryingModel(
        FakeModel(),
        retry_attempts=1,
        retry_sleep_s=0,
        events_path=events_path,
        spans_path=spans_path,
        runtime_config={
            "runtime": "openai-agents-live",
            "provider_profile": "mify",
            "wire_api": "responses",
            "model": "xiaomi/mimo-v2.5",
        },
    )

    with pytest.raises(RuntimeError, match="model unavailable"):
        asyncio.run(
            model.get_response(
                None,
                "clean the room",
                object(),
                [],
                None,
                [],
                object(),
                previous_response_id=None,
                conversation_id=None,
                prompt=None,
            )
        )

    metrics = _model_service_fallback_metrics(tmp_path)
    assert metrics["available"] is True
    assert metrics["attempt_event_count"] == 2
    assert metrics["retry_scheduled_count"] == 1
    assert metrics["failure_event_count"] == 2
    assert metrics["retry_exhausted"] is True
    assert metrics["failure_classes"] == {"provider_transient_failure": 2}
    assert metrics["provider_reasons"] == {"upstream_unavailable": 2}
    assert metrics["attempted_models"] == ["xiaomi/mimo-v2.5"]
    assert metrics["attempted_provider_profiles"] == ["mify"]
    assert metrics["attempted_wire_apis"] == ["responses"]


def test_openai_agents_retrying_model_satisfies_sdk_model_contract(tmp_path: Path) -> None:
    pytest.importorskip("agents")
    from agents.models.interface import Model

    class FakeModel:
        async def get_response(self, *_args, **_kwargs):
            return SimpleNamespace(output="ok")

        def stream_response(self, *_args, **_kwargs):
            raise AssertionError("not used")

    model = _RetryingModel(
        FakeModel(),
        retry_attempts=0,
        retry_sleep_s=0,
        events_path=tmp_path / "openai-agents-events.jsonl",
        spans_path=tmp_path / "openai-agents-spans.jsonl",
        runtime_config={"runtime": "openai-agents-live"},
    )

    assert isinstance(model, Model)


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
    assert "I stopped before calling done." not in json.dumps(trace_payload)
    assert trace_payload["final_output_present"] is True
    assert trace_payload["final_output_chars"] == len("I stopped before calling done.")
    assert trace_payload["message"].startswith("OpenAI Agents SDK result captured")


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
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
    wrapped_model = captured["agent_kwargs"]["model"]
    assert isinstance(wrapped_model, _RetryingModel)
    assert wrapped_model.base_model is captured["responses_model"]
    assert captured["agent_kwargs"]["model_settings"].tool_choice == "auto"
    assert captured["agent_kwargs"]["model_settings"].parallel_tool_calls is False
    assert captured["agent_kwargs"]["model_settings"].truncation == "auto"
    assert captured["runner_kwargs"]["run_config"].trace_include_sensitive_data is False
    assert captured["runner_kwargs"]["run_config"].workflow_name == "roboclaws-openai-agents-live"
    assert captured["mcp_server_kwargs"]["cache_tools_list"] is True
    assert "client_session_timeout_seconds" not in captured["mcp_server_kwargs"]
    assert captured["agent_kwargs"]["mcp_config"]["failure_error_function"]
    assert captured["runner_kwargs"]["max_turns"] == 128
    events = [
        json.loads(line)
        for line in (tmp_path / "run" / "openai-agents-events.jsonl").read_text().splitlines()
    ]
    assert events[0]["wire_api"] == "responses"
    assert events[0]["sdk_model_settings"]["store"] is False
    assert events[0]["sdk_run_config"]["trace_include_sensitive_data"] is False
    assert events[0]["agent_sdk_responses_features"]["available"] is True
    assert events[0]["agent_sdk_responses_features"]["server_managed_continuation_default"] is False
    assert events[0]["model_input_compaction"]["enabled"] is False
    assert events[0]["model_input_compaction"]["mode"] == "off"


def test_openai_agents_runtime_includes_skill_context_without_persisting_body(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}
    skill_text = "# Molmo Real-World Cleanup\n\nCall metric_map first."

    class FakeOpenAIResponsesModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            pass

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
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
        metadata={
            "skill_context": {
                "skill_name": "molmo-realworld-cleanup",
                "included": True,
                "reason": "included",
                "relative_path": "skills/molmo-realworld-cleanup/SKILL.md",
                "sha256": "abc123",
                "bytes": len(skill_text),
                "estimated_tokens": 12,
                "policy": "canonical_skill_markdown",
                "content": skill_text,
            }
        },
    )

    result = OpenAIAgentsLiveRuntime().run(request)

    assert result.artifact_paths["openai_agents_skill_context"] == (
        tmp_path / "run" / "openai-agents-skill-context.json"
    )
    instructions = str(captured["agent_kwargs"]["instructions"])
    assert "Canonical skill context" in instructions
    assert skill_text in instructions
    assert instructions.endswith("clean the room")
    artifact = json.loads(
        (tmp_path / "run" / "openai-agents-skill-context.json").read_text(encoding="utf-8")
    )
    assert artifact == {
        "schema": "openai_agents_skill_context_v1",
        "skill_name": "molmo-realworld-cleanup",
        "included": True,
        "reason": "included",
        "relative_path": "skills/molmo-realworld-cleanup/SKILL.md",
        "sha256": "abc123",
        "bytes": len(skill_text),
        "estimated_tokens": 12,
        "policy": "canonical_skill_markdown",
    }
    assert skill_text not in json.dumps(artifact)
    events_text = (tmp_path / "run" / "openai-agents-events.jsonl").read_text(encoding="utf-8")
    assert "abc123" in events_text
    assert skill_text not in events_text


def test_openai_agents_runtime_can_use_mimo_openai_chat_profile(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIChatCompletionsModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["chat_model"] = self
            captured["model"] = model
            captured["client"] = openai_client

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setenv("MIMO_TP_KEY", "fake-mimo-key")
    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_with_async_mcp_server",
        lambda *_args, **_kwargs: SimpleNamespace(final_output="done"),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents",
        SimpleNamespace(
            Agent=lambda **kwargs: captured.setdefault("agent_kwargs", kwargs),
            Runner=SimpleNamespace(run_sync=lambda *_args, **_kwargs: SimpleNamespace()),
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIChatCompletionsModel=FakeOpenAIChatCompletionsModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
        provider_profile="mimo-openai-chat",
    )

    OpenAIAgentsLiveRuntime().run(request)

    assert captured["model"] == "mimo-v2.5"
    assert captured["base_url"] == "https://token-plan-cn.xiaomimimo.com/v1"
    assert captured["api_key"] == "fake-mimo-key"
    wrapped_model = captured["agent_kwargs"]["model"]
    assert isinstance(wrapped_model, _RetryingModel)
    assert wrapped_model.base_model is captured["chat_model"]
    assert captured["agent_kwargs"]["model_settings"].include_usage is True
    assert captured["agent_kwargs"]["model_settings"].parallel_tool_calls is False
    events = [
        json.loads(line)
        for line in (tmp_path / "run" / "openai-agents-events.jsonl").read_text().splitlines()
    ]
    assert events[0]["provider_profile"] == "mimo-openai-chat"
    assert events[0]["wire_api"] == "chat-completions"
    assert events[0]["sdk_model_settings"]["include_usage"] is True
    assert events[0]["agent_sdk_responses_features"]["available"] is False


def test_openai_agents_runtime_configures_model_input_compaction_filter(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIResponsesModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            pass

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
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
        metadata={
            "agent_sdk_perf_profile": {
                "profile_id": "custom",
                "provider_profile": "codex-env",
                "wire_api": "responses",
                "model_input_compaction": {
                    "enabled": True,
                    "mode": "public_tool_result_summary_v1",
                    "min_chars": 80,
                },
            }
        },
    )

    OpenAIAgentsLiveRuntime().run(request)

    run_config = captured["runner_kwargs"]["run_config"]
    assert callable(run_config.call_model_input_filter)
    events = [
        json.loads(line)
        for line in (tmp_path / "run" / "openai-agents-events.jsonl").read_text().splitlines()
    ]
    assert events[0]["model_input_compaction"]["enabled"] is True
    assert events[0]["model_input_compaction"]["mode"] == "public_tool_result_summary_v1"
    assert "call_model_input_filter" not in events[0]["sdk_run_config"]


def test_model_input_compaction_reduces_oversized_public_tool_outputs() -> None:
    large_output = json.dumps(
        {
            "metric_map": {
                "inspection_waypoints": [
                    {"waypoint_id": f"wp_{idx}", "room": "kitchen", "objects": ["cup", "plate"]}
                    for idx in range(20)
                ]
            }
        }
    )
    items = [
        {"role": "user", "content": "clean the room"},
        {
            "type": "function_call_output",
            "call_id": "call_metric_map",
            "output": large_output,
        },
    ]

    filtered, metrics = _compact_model_input_items(items, min_chars=80)

    assert metrics["input_item_count"] == 2
    assert metrics["compacted_item_count"] == 1
    assert metrics["input_bytes_after"] < metrics["input_bytes_before"]
    assert filtered[0] == items[0]
    assert filtered[1]["call_id"] == "call_metric_map"
    replacement = json.loads(filtered[1]["output"])
    assert replacement["schema"] == "roboclaws_public_tool_output_summary_v1"
    assert replacement["original_chars"] == len(large_output)
    assert "wp_19" not in json.dumps(filtered)


def test_model_input_compaction_summarizes_repeated_metric_map_outputs() -> None:
    first_map = {
        "ok": True,
        "tool": "metric_map",
        "map_id": "home",
        "map_version": "v1",
        "mode": "minimal",
        "inspection_waypoints": [
            {
                "waypoint_id": f"wp_{idx}",
                "room": "kitchen",
                "navigation_note": "large public map waypoint payload",
            }
            for idx in range(80)
        ],
        "runtime_metric_map": {
            "observed_objects": [{"object_id": "cup_1"}],
            "target_candidates": [{"object_id": "cup_1"}],
        },
    }
    second_map = {
        **first_map,
        "runtime_metric_map": {
            "observed_objects": [{"object_id": "cup_1"}, {"object_id": "book_1"}],
            "target_candidates": [{"object_id": "cup_1"}, {"object_id": "book_1"}],
        },
    }
    items = [
        {
            "type": "function_call_output",
            "call_id": "call_metric_map_first",
            "output": json.dumps(first_map),
        },
        {
            "type": "function_call_output",
            "call_id": "call_metric_map_second",
            "output": json.dumps(second_map),
        },
    ]

    filtered, metrics = _compact_model_input_items(items, min_chars=999_999)

    assert filtered[0] == items[0]
    replacement = json.loads(filtered[1]["output"])
    assert replacement["schema"] == "roboclaws_repeated_metric_map_delta_summary_v1"
    assert replacement["map_id"] == "home"
    assert replacement["inspection_waypoint_count"] == 80
    assert replacement["runtime_observed_object_count"] == 2
    assert "book_1" not in json.dumps(filtered[1])
    assert metrics["metric_map_output_count"] == 2
    assert metrics["repeated_metric_map_output_count"] == 1
    assert metrics["metric_map_delta_compacted_count"] == 1
    assert metrics["metric_map_bytes_after"] < metrics["metric_map_bytes_before"]
    assert metrics["metric_map_bytes_reduced"] > 0


def test_openai_agents_runtime_can_use_kimi_openai_chat_profile(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIChatCompletionsModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setenv("KIMI_API_KEY", "fake-kimi-key")
    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_with_async_mcp_server",
        lambda *_args, **_kwargs: SimpleNamespace(final_output="done"),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents",
        SimpleNamespace(
            Agent=lambda **kwargs: captured.setdefault("agent_kwargs", kwargs),
            Runner=SimpleNamespace(run_sync=lambda *_args, **_kwargs: SimpleNamespace()),
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIChatCompletionsModel=FakeOpenAIChatCompletionsModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
        provider_profile="kimi-openai-chat",
    )

    OpenAIAgentsLiveRuntime().run(request)

    assert captured["model"] == "kimi-k2.6"
    assert captured["base_url"] == "https://api.kimi.com/coding/v1"
    assert captured["api_key"] == "fake-kimi-key"


def test_openai_agents_runtime_allows_disabling_mcp_tool_list_cache(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIResponsesModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            pass

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
            Runner=SimpleNamespace(run_sync=lambda *_args, **_kwargs: SimpleNamespace()),
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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
        metadata={"cache_tools_list": False},
    )

    OpenAIAgentsLiveRuntime().run(request)

    assert captured["mcp_server_kwargs"]["cache_tools_list"] is False


def test_openai_agents_runtime_configures_mcp_client_session_timeout(
    tmp_path: Path, monkeypatch
) -> None:
    captured: dict[str, object] = {}

    class FakeOpenAIResponsesModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model

    class FakeAsyncOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            pass

    monkeypatch.setenv("CODEX_BASE_URL", "https://codex.example.test/v1")
    monkeypatch.setenv("CODEX_API_KEY", "fake-codex-key")
    monkeypatch.setenv("ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S", "30")
    monkeypatch.setattr(
        "roboclaws.agents.drivers.openai_agents_live._run_with_async_mcp_server",
        lambda *_args, **_kwargs: SimpleNamespace(final_output="done"),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents",
        SimpleNamespace(
            Agent=lambda **kwargs: captured.setdefault("agent_kwargs", kwargs),
            Runner=SimpleNamespace(run_sync=lambda *_args, **_kwargs: SimpleNamespace()),
            ModelSettings=FakeModelSettings,
            RunConfig=FakeRunConfig,
            OpenAIResponsesModel=FakeOpenAIResponsesModel,
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "agents.mcp",
        SimpleNamespace(
            MCPServerStreamableHttp=lambda **kwargs: (
                captured.setdefault("mcp_server_kwargs", kwargs) or SimpleNamespace(kwargs=kwargs)
            )
        ),
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

    assert captured["mcp_server_kwargs"]["client_session_timeout_seconds"] == 30.0
    events = [
        json.loads(line)
        for line in (tmp_path / "run" / "openai-agents-events.jsonl").read_text().splitlines()
    ]
    assert events[0]["event"] == "start"
    assert events[0]["mcp_client_session_timeout_s"] == 30.0


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
        repo_root=_isolated_repo_root(tmp_path),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=lock_path,
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
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
    assert timing["surface"] == "household-world"
    assert timing["intent"] == "cleanup"
    assert timing["task_name"] == "household-cleanup"
    assert timing["task_intent_mode"] == "default_cleanup"
    assert timing["evidence_lane"] == "smoke"
    assert timing["mcp_client_session_timeout_s"] == 30.0
    assert timing["agent_sdk_perf_profile"]["schema"] == "agent_sdk_perf_profile_v1"
    assert timing["agent_sdk_perf_profile"]["profile_id"] == "baseline"
    assert timing["agent_sdk_perf_profile"]["prompt_mode"] == "full"
    assert timing["agent_sdk_perf_profile"]["continuation_mode"] == "repeat_full_prompt"
    assert timing["agent_sdk_perf_profile"]["max_turns"] == 128
    assert timing["agent_sdk_perf_profile"]["model_service_retry_attempts"] == 1
    assert timing["agent_sdk_perf_profile"]["model_service_retry_sleep_s"] == 1.0
    assert timing["agent_sdk_perf_profile"]["sdk_model_settings"] == {
        "parallel_tool_calls": False,
        "store": False,
        "tool_choice": "auto",
        "truncation": "auto",
    }
    assert timing["agent_sdk_perf_profile"]["sdk_run_config"] == {
        "trace_include_sensitive_data": False,
        "workflow_name": "roboclaws-openai-agents-live",
    }
    assert timing["kickoff_prompt_stable_prefix"]["schema"] == "agent_sdk_stable_prefix_v1"
    assert timing["kickoff_prompt_stable_prefix"]["hash"]
    assert (
        timing["cache_metrics"]["stable_prefix_hash"]
        == timing["kickoff_prompt_stable_prefix"]["hash"]
    )
    assert timing["openai_agents"]["trace_id"] == "trace_1"
    assert timing["mcp_control_plane_metrics"]["available"] is False
    assert timing["openai_agents_event_metrics"]["available"] is True
    assert timing["openai_agents_span_metrics"]["available"] is False
    assert timing["timeline"]["schema"] == "live_agent_timeline_v1"
    assert timing["timeline"]["surface"] == "household-world"
    assert timing["timeline"]["intent"] == "cleanup"
    assert timing["timeline"]["runtime"] == "openai-agents-live"
    assert timing["timeline"]["evidence_lane"] == "smoke"
    assert [item["name"] for item in timing["timeline"]["runner_segments"]] == [
        "pre_agent_setup",
        "openai_agents_runtime",
        "post_agent_server_wait",
        "checker",
        "final_overhead",
    ]
    assert timing["timeline"]["latency_attribution"]["mcp_client_session_timeout_s"] == 30.0
    assert checker_commands
    checker_command = checker_commands[0]
    assert "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py" in checker_command
    assert "--expect-policy" in checker_command
    assert "openai_agents_agent" in checker_command
    assert "--require-clean-agent-run" in checker_command


def test_openai_agents_cleanup_runner_loads_canonical_skill_context(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    repo_root = tmp_path / "repo"
    skill_path = repo_root / "skills/molmo-realworld-cleanup/SKILL.md"
    skill_path.parent.mkdir(parents=True)
    skill_text = "# Molmo Real-World Cleanup\n\nCall metric_map first."
    skill_path.write_text(skill_text, encoding="utf-8")
    captured_contexts: list[dict[str, object]] = []

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
            captured_contexts.append(dict(request.metadata["skill_context"]))
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
            (request.run_dir / "openai-agents-skill-context.json").write_text(
                json.dumps(
                    {
                        "schema": "openai_agents_skill_context_v1",
                        "skill_name": "molmo-realworld-cleanup",
                        "included": True,
                        "sha256": request.metadata["skill_context"]["sha256"],
                    }
                ),
                encoding="utf-8",
            )
            return LiveAgentResult(
                phase="finished",
                exit_status=0,
                run_result_present=True,
                artifact_paths={
                    "openai_agents_skill_context": request.artifact_path(
                        "openai_agents_skill_context",
                        "missing.json",
                    )
                },
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
        stdout_path.write_text("checker ok\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        fake_run_and_tee,
    )
    args = Namespace(
        run_dir=run_dir,
        repo_root=repo_root,
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=2,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
        server_startup_timeout_s=1.0,
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        task_name="household-cleanup",
        task_intent_mode="default_cleanup",
        policy="openai_agents_agent",
        task="clean",
        min_generated_mess_count="5",
        profile="world-public-labels",
        server_arg=[],
        checker_visual_arg=[],
    )

    status = LiveOpenAIAgentsCleanupRunner(args).run()

    assert status == 0
    assert captured_contexts
    skill_context = captured_contexts[0]
    assert skill_context["included"] is True
    assert skill_context["content"] == skill_text
    assert skill_context["relative_path"] == "skills/molmo-realworld-cleanup/SKILL.md"
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert timing["agent_sdk_skill_context"]["included"] is True
    assert timing["agent_sdk_skill_context"]["relative_path"] == (
        "skills/molmo-realworld-cleanup/SKILL.md"
    )
    assert timing["agent_sdk_skill_context"]["bytes"] == len(skill_text.encode("utf-8"))
    assert "content" not in timing["agent_sdk_skill_context"]
    assert skill_text not in json.dumps(timing)


def test_agent_sdk_skill_context_loader_reports_missing_source(tmp_path: Path) -> None:
    context = _load_agent_sdk_skill_context(
        tmp_path / "repo",
        skill_name="molmo-realworld-cleanup",
    )

    assert context["included"] is False
    assert context["reason"] == "source_unavailable"
    assert context["relative_path"] == "skills/molmo-realworld-cleanup/SKILL.md"
    assert "content" not in context


def test_openai_agents_cleanup_runner_continues_incomplete_sdk_turn(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    checker_commands: list[list[str]] = []
    prompts: list[str] = []
    event_paths: list[Path] = []
    span_paths: list[Path] = []

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
            span_paths.append(request.artifact_path("openai_agents_spans", "missing.jsonl"))
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
        repo_root=_isolated_repo_root(tmp_path),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=2,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
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
    assert span_paths == [
        run_dir / "openai-agents-spans.jsonl",
        run_dir / "openai-agents-spans.continuation-1.jsonl",
    ]
    assert checker_commands
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert [item["attempt_role"] for item in timing["openai_agents_attempts"]] == [
        "initial",
        "continuation",
    ]
    assert timing["openai_agents_attempts"][0]["recovery_action"] == "continue"
    assert timing["openai_agents"]["trace_id"] == "trace_continuation"


def test_openai_agents_cleanup_runner_compact_continuation_excludes_full_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    prompts: list[str] = []

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
            if len(prompts) == 1:
                (request.run_dir / "trace.jsonl").write_text(
                    "\n".join(
                        [
                            json.dumps(
                                {
                                    "event": "molmo_realworld_cleanup_mcp_initialized",
                                    "cleanup_profile": "world-public-labels",
                                    "goal_contract": {
                                        "surface": "household-world",
                                        "intent": "cleanup",
                                        "normalized_goal": "clean the room",
                                    },
                                }
                            ),
                            json.dumps(
                                {
                                    "event": "response",
                                    "tool": "observe",
                                    "response": {
                                        "ok": True,
                                        "waypoint_id": "generated_exploration_001",
                                    },
                                }
                            ),
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
                return LiveAgentResult(
                    phase="agent-turn-complete",
                    exit_status=0,
                    run_result_present=False,
                )
            assert request.metadata["agent_sdk_perf_profile"]["profile_id"] == "gpt_compact_v1"
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
            return LiveAgentResult(phase="finished", exit_status=0, run_result_present=True)

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
        stdout_path.write_text("checker ok\n", encoding="utf-8")
        return 0

    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        fake_run_and_tee,
    )
    full_prompt = "FULL ORIGINAL PROMPT THAT SHOULD NOT REPEAT"
    args = Namespace(
        run_dir=run_dir,
        repo_root=_isolated_repo_root(tmp_path),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=2,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="gpt_compact_v1",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
        server_startup_timeout_s=1.0,
        kickoff_prompt=full_prompt,
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
    assert prompts[0] == full_prompt
    assert full_prompt not in prompts[1]
    assert "compact_continuation_state" in prompts[1]
    assert "generated_exploration_001" in prompts[1]
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert timing["openai_agents_attempts"][0]["recovery_action"] == "continue"
    assert timing["openai_agents_attempts"][0]["continuation_prompt_chars"] == len(prompts[1])


def test_openai_agents_cleanup_runner_uses_profiled_compact_kickoff_prompt(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "run"
    prompts: list[str] = []

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
            return LiveAgentResult(phase="finished", exit_status=0, run_result_present=True)

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
    monkeypatch.setattr(
        "scripts.molmo_cleanup.run_live_openai_agents_cleanup._run_and_tee",
        lambda command, *, cwd, stdout_path, stderr_path, env: 0,
    )
    args = Namespace(
        run_dir=run_dir,
        repo_root=_isolated_repo_root(tmp_path),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=2,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="gpt_compact_v1",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
        server_startup_timeout_s=1.0,
        kickoff_prompt="FULL PROMPT THAT SHOULD BE REPLACED",
        backend="molmospaces_subprocess",
        task_name="household-cleanup",
        task_intent_mode="default_cleanup",
        policy="openai_agents_agent",
        task="clean",
        min_generated_mess_count="5",
        profile="world-public-labels",
        server_arg=[],
        checker_visual_arg=[],
    )

    status = LiveOpenAIAgentsCleanupRunner(args).run()

    assert status == 0
    assert len(prompts) == 1
    assert "FULL PROMPT THAT SHOULD BE REPLACED" not in prompts[0]
    assert "Compact action cadence for world-public-labels" in prompts[0]
    assert "pending_cleanup_candidates" in prompts[0]
    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert timing["kickoff_prompt_source"] == "profile-rendered-compact"


def test_incomplete_turn_recovery_compacts_after_context_soft_limit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "trace.jsonl").write_text(
        json.dumps(
            {
                "event": "molmo_realworld_cleanup_mcp_initialized",
                "cleanup_profile": "world-public-labels",
                "goal_contract": {
                    "surface": "household-world",
                    "intent": "cleanup",
                    "normalized_goal": "clean the room",
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = LiveAgentResult(phase="agent-turn-complete", exit_status=0)

    prompt = IncompleteTurnRecoveryPolicy(max_attempts=1).continuation_prompt(
        original_prompt="ORIGINAL FULL PROMPT",
        result=result,
        run_dir=run_dir,
        attempt_index=0,
        profile={
            "profile_id": "baseline",
            "continuation_mode": "repeat_full_prompt",
            "context_soft_limit_tokens": 100,
        },
        context_metrics={"available": True, "total_input_tokens": 100},
    )

    assert prompt is not None
    assert "compact_continuation_state" in prompt
    assert "ORIGINAL FULL PROMPT" not in prompt


def test_openai_agents_budget_guard_classifies_context_hard_limit(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-spans.jsonl").write_text(
        json.dumps(
            {
                "event": "span_end",
                "span_type": "response",
                "usage": {"input_tokens": 150, "input_tokens_details": {"cached_tokens": 50}},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    failure = _budget_failure_from_run_state(
        run_dir,
        {"evidence_lane": "world-public-labels", "cache_tools_list": True},
        {
            "profile_id": "custom",
            "context_hard_limit_tokens": 100,
            "raw_fpv_candidate_budget": None,
            "max_observe_per_waypoint": None,
        },
    )

    assert failure is not None
    assert failure.reason == "provider_context_budget_exceeded"
    assert failure.retryable is False
    detail = json.loads(failure.detail)
    assert detail["current_input_tokens"] == 150
    assert detail["total_input_tokens"] == 150
    assert detail["context_hard_limit_tokens"] == 100


def test_openai_agents_budget_guard_uses_current_context_not_cumulative_tokens(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-spans.jsonl").write_text(
        "\n".join(
            json.dumps(
                {
                    "event": "span_end",
                    "span_type": "response",
                    "usage": {
                        "input_tokens": 40_000,
                        "input_tokens_details": {"cached_tokens": 38_000},
                    },
                }
            )
            for _ in range(4)
        )
        + "\n",
        encoding="utf-8",
    )

    failure = _budget_failure_from_run_state(
        run_dir,
        {"evidence_lane": "world-public-labels", "cache_tools_list": True},
        {
            "profile_id": "mimo_compact_v1",
            "context_hard_limit_tokens": 96_000,
            "raw_fpv_candidate_budget": None,
            "max_observe_per_waypoint": None,
        },
    )

    assert failure is None


def test_openai_agents_budget_guard_classifies_raw_fpv_candidate_exhaustion(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    events = [
        {
            "event": "request",
            "tool": "navigate_to_visual_candidate",
            "request": {
                "source_observation_id": "raw_fpv_001",
                "category": "cup",
                "image_region": {"type": "bbox", "value": [1, 2, 3, 4]},
            },
        },
        {
            "event": "response",
            "tool": "navigate_to_visual_candidate",
            "response": {
                "ok": False,
                "source_observation_id": "raw_fpv_001",
                "category": "cup",
                "error_reason": "invalid_visual_candidate",
            },
        },
        {
            "event": "request",
            "tool": "navigate_to_visual_candidate",
            "request": {
                "source_observation_id": "raw_fpv_002",
                "category": "book",
                "image_region": {"type": "bbox", "value": [5, 6, 7, 8]},
            },
        },
    ]
    (run_dir / "trace.jsonl").write_text(
        "\n".join(json.dumps(item) for item in events) + "\n",
        encoding="utf-8",
    )

    failure = _budget_failure_from_run_state(
        run_dir,
        {"evidence_lane": "camera-raw-fpv", "cache_tools_list": True},
        {
            "profile_id": "raw_fpv_budgeted_v1",
            "context_hard_limit_tokens": None,
            "raw_fpv_candidate_budget": 2,
            "max_observe_per_waypoint": None,
        },
    )

    assert failure is not None
    assert failure.reason == "raw_fpv_candidate_budget_exhausted"
    detail = json.loads(failure.detail)
    assert detail["candidate_attempt_count"] == 2
    assert detail["raw_fpv_candidate_budget"] == 2
    assert detail["candidate_attempts_sample"][0]["source_observation_id"] == "raw_fpv_001"


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
        repo_root=_isolated_repo_root(tmp_path),
        status_path=run_dir / "live_status.json",
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "live.lock",
        provider_profile="codex-env",
        model="gpt-5.5",
        max_turns=128,
        incomplete_turn_continuation_attempts=1,
        mcp_client_session_timeout_s=30.0,
        agent_sdk_perf_profile="",
        prompt_mode="",
        continuation_mode="",
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
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


def test_openai_agents_perf_profiles_resolve_known_defaults(monkeypatch) -> None:
    monkeypatch.delenv("ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE", raising=False)
    base_args = Namespace(
        provider_profile="codex-env",
        model="gpt-5.5",
        agent_sdk_perf_profile="",
        prompt_mode="",
        continuation_mode="",
        max_turns=None,
        incomplete_turn_continuation_attempts=None,
        cache_tools_list=True,
        mcp_client_session_timeout_s=30.0,
        context_soft_limit_tokens=None,
        context_hard_limit_tokens=None,
        max_observe_per_waypoint=None,
        raw_fpv_candidate_budget=None,
        done_retry_budget=None,
        model_service_retry_attempts=None,
        model_service_retry_sleep_s=None,
    )

    baseline = _resolve_agent_sdk_perf_profile(base_args)
    assert baseline["profile_id"] == "baseline"
    assert baseline["source"] == "default"
    assert baseline["provider_profile"] == "codex-env"
    assert baseline["wire_api"] == "responses"
    assert baseline["model_family"] == "gpt"
    assert baseline["prompt_mode"] == "full"
    assert baseline["continuation_mode"] == "repeat_full_prompt"
    assert baseline["max_turns"] == 128
    assert baseline["max_continuations"] == 2
    assert baseline["context_soft_limit_tokens"] is None
    assert baseline["sdk_model_settings"] == {
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "truncation": "auto",
        "store": False,
    }
    assert baseline["sdk_run_config"] == {
        "trace_include_sensitive_data": False,
        "workflow_name": "roboclaws-openai-agents-live",
    }

    gpt_args = Namespace(**{**vars(base_args), "agent_sdk_perf_profile": "gpt_compact_v1"})
    gpt = _resolve_agent_sdk_perf_profile(gpt_args)
    assert gpt["source"] == "cli"
    assert gpt["prompt_mode"] == "compact"
    assert gpt["continuation_mode"] == "state_summary_only"
    assert gpt["max_turns"] == 128
    assert gpt["max_continuations"] == 1
    assert gpt["context_soft_limit_tokens"] == 96_000
    assert gpt["context_hard_limit_tokens"] == 128_000
    assert gpt["done_retry_budget"] == 2
    assert gpt["sdk_model_settings"]["prompt_cache_retention"] == "in_memory"
    assert gpt["model_input_compaction"]["candidate_ids"] == ["I", "N"]
    assert gpt["model_input_compaction"]["repeated_metric_map_delta"] is False

    mimo_args = Namespace(
        **{
            **vars(base_args),
            "provider_profile": "mify",
            "model": "xiaomi/mimo-v2.5",
            "agent_sdk_perf_profile": "mimo_compact_v1",
        }
    )
    mimo = _resolve_agent_sdk_perf_profile(mimo_args)
    assert mimo["provider_profile"] == "mify"
    assert mimo["wire_api"] == "responses"
    assert mimo["model_family"] == "mimo"
    assert mimo["max_continuations"] == 1
    assert mimo["context_soft_limit_tokens"] == 64_000
    assert mimo["context_hard_limit_tokens"] == 96_000

    chat_args = Namespace(
        **{
            **vars(base_args),
            "provider_profile": "mimo-chat",
            "model": "mimo-v2.5",
        }
    )
    chat = _resolve_agent_sdk_perf_profile(chat_args)
    assert chat["provider_profile"] == "mimo-openai-chat"
    assert chat["wire_api"] == "chat-completions"
    assert chat["model_family"] == "mimo"
    assert chat["sdk_model_settings"] == {
        "tool_choice": "auto",
        "parallel_tool_calls": False,
        "include_usage": True,
    }

    raw = _resolve_agent_sdk_perf_profile(
        Namespace(**{**vars(base_args), "agent_sdk_perf_profile": "raw_fpv_budgeted_v1"})
    )
    assert raw["prompt_mode"] == "raw_fpv_compact"
    assert raw["max_turns"] == 40
    assert raw["max_continuations"] == 1
    assert raw["raw_fpv_candidate_budget"] == 24
    assert raw["done_retry_budget"] == 1

    custom = _resolve_agent_sdk_perf_profile(
        Namespace(
            **{
                **vars(base_args),
                "agent_sdk_perf_profile": "custom",
                "prompt_mode": "compact",
                "continuation_mode": "state_summary_only",
                "max_turns": 9,
                "incomplete_turn_continuation_attempts": 3,
                "context_soft_limit_tokens": 12,
                "context_hard_limit_tokens": 34,
                "max_observe_per_waypoint": 2,
                "raw_fpv_candidate_budget": 3,
                "done_retry_budget": 4,
            }
        )
    )
    assert custom["profile_id"] == "custom"
    assert custom["prompt_mode"] == "compact"
    assert custom["max_turns"] == 9
    assert custom["max_continuations"] == 3
    assert custom["context_soft_limit_tokens"] == 12
    assert custom["context_hard_limit_tokens"] == 34
    assert custom["max_observe_per_waypoint"] == 2
    assert custom["model_input_compaction"]["candidate_ids"] == ["I", "N"]

    compaction = _resolve_agent_sdk_perf_profile(
        Namespace(
            **{
                **vars(base_args),
                "agent_sdk_perf_profile": "custom",
                "model_input_compaction": True,
                "model_input_compaction_min_chars": 80,
            }
        )
    )
    assert compaction["model_input_compaction"] == {
        "schema": "agent_sdk_model_input_compaction_v1",
        "enabled": True,
        "mode": "public_tool_result_summary_v1+repeated_metric_map_delta_v1",
        "min_chars": 80,
        "candidate_ids": ["I", "N"],
        "hook": "RunConfig.call_model_input_filter",
        "repeated_metric_map_delta": True,
        "private_artifact_policy": (
            "model-facing compaction only; MCP traces, reports, and run artifacts remain complete"
        ),
    }


def test_openai_agents_control_plane_metrics_parse_server_log(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-server.log").write_text(
        "\n".join(
            [
                "[2026-06-09] INFO Created new transport with session ID: abc",
                'INFO:     127.0.0.1:1 - "POST /mcp HTTP/1.1" 200 OK',
                "[2026-06-09] INFO Processing request of type ListToolsRequest",
                'INFO:     127.0.0.1:2 - "POST /mcp HTTP/1.1" 202 Accepted',
                "[2026-06-09] INFO Processing request of type CallToolRequest",
                "[2026-06-09] INFO Processing request of type CallToolRequest",
                "OPENAI_API_KEY is not set, skipping trace export",
                "[2026-06-09] INFO Terminating session: abc",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = _mcp_control_plane_metrics(run_dir)

    assert metrics["available"] is True
    assert metrics["request_type_counts"] == {
        "CallToolRequest": 2,
        "ListToolsRequest": 1,
    }
    assert metrics["total_mcp_request_count"] == 3
    assert metrics["call_tool_request_count"] == 2
    assert metrics["list_tools_request_count"] == 1
    assert metrics["control_request_count"] == 1
    assert metrics["list_tools_per_call_tool"] == 0.5
    assert metrics["streamable_http_session_count"] == 1
    assert metrics["session_termination_count"] == 1
    assert metrics["trace_export_skip_count"] == 1
    assert metrics["http_status_counts"] == {
        "200 OK": 1,
        "202 Accepted": 1,
    }


def test_openai_agents_event_metrics_parse_tool_errors(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-events.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event": "start", "mcp_client_session_timeout_s": 5}),
                json.dumps(
                    {
                        "event": "tool_error",
                        "classification": "mcp_client_request_timeout",
                        "message": (
                            "Timed out while waiting for response to ClientRequest. "
                            "Waited 5.0 seconds."
                        ),
                    }
                ),
                json.dumps({"event": "result"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = _openai_agents_event_metrics(run_dir)

    assert metrics["available"] is True
    assert metrics["event_counts"]["tool_error"] == 1
    assert metrics["tool_error_count"] == 1
    assert metrics["tool_error_classifications"] == {"mcp_client_request_timeout": 1}
    assert "Waited 5.0 seconds" in metrics["tool_error_messages_sample"][0]


def test_openai_agents_span_recorder_writes_sanitized_span_events(tmp_path: Path) -> None:
    spans_path = tmp_path / "openai-agents-spans.jsonl"
    recorder = _RoboclawsSpanRecorder(
        spans_path,
        runtime_config={
            "runtime": "openai-agents-live",
            "provider_profile": "codex-env",
            "model": "gpt-5.5",
        },
    )

    class FakeSpanData:
        type = "function"

        def export(self) -> dict[str, object]:
            return {
                "type": "function",
                "name": "pickup_object",
                "input": '{"secret":"prompt text"}',
                "output": '{"private_target_truth": true}',
                "mcp_data": {"server": "cleanup", "tool_name": "pickup_object"},
            }

    class FakeSpan:
        trace_id = "trace_1"
        span_id = "span_1"
        parent_id = "span_parent"
        started_at = datetime.fromtimestamp(100, UTC).isoformat()
        ended_at = datetime.fromtimestamp(102.5, UTC).isoformat()
        span_data = FakeSpanData()
        error = {"message": "tool failed", "data": {"raw": "not persisted"}}

    recorder.on_span_end(FakeSpan())
    recorder.shutdown()
    recorder.on_span_end(FakeSpan())

    events = [json.loads(line) for line in spans_path.read_text(encoding="utf-8").splitlines()]

    assert len(events) == 1
    event = events[0]
    assert event["schema"] == "openai_agents_sanitized_span_v1"
    assert event["event"] == "span_end"
    assert event["runtime"] == "openai-agents-live"
    assert event["span_type"] == "function"
    assert event["span_name"] == "pickup_object"
    assert event["duration_s"] == 2.5
    assert event["mcp"] == {"server": "cleanup", "tool_name": "pickup_object"}
    assert event["error"] == {"message": "tool failed", "data_keys": ["raw"]}
    assert "input" not in event
    assert "output" not in event


def test_openai_agents_span_metrics_parse_span_artifacts(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-spans.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event": "trace_start", "trace_id": "trace_1"}),
                json.dumps({"event": "span_end", "span_type": "response"}),
                json.dumps({"event": "span_end", "span_type": "function"}),
                json.dumps(
                    {
                        "event": "span_capture_unavailable",
                        "reason": "sdk_trace_processor_registration_failed",
                        "error_type": "RuntimeError",
                        "message": "cannot register",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = _openai_agents_span_metrics(run_dir)

    assert metrics["available"] is True
    assert metrics["span_files"] == ["openai-agents-spans.jsonl"]
    assert metrics["event_counts"]["span_end"] == 2
    assert metrics["span_end_count"] == 2
    assert metrics["span_type_counts"] == {"function": 1, "response": 1}
    assert metrics["limitations"] == [
        {
            "reason": "sdk_trace_processor_registration_failed",
            "error_type": "RuntimeError",
            "message": "cannot register",
        }
    ]
    assert "Raw prompts" in metrics["sanitization_note"]


def test_openai_agents_context_metrics_parse_response_span_usage(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-spans.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "span_end",
                        "span_type": "response",
                        "duration_s": 1.5,
                        "usage": {
                            "input_tokens": 100,
                            "input_tokens_details": {"cached_tokens": 25},
                            "output_tokens": 10,
                            "output_tokens_details": {"reasoning_tokens": 4},
                        },
                    }
                ),
                json.dumps(
                    {
                        "event": "span_end",
                        "span_type": "custom",
                        "duration_s": 1.6,
                        "usage": {
                            "input_tokens": 100,
                            "cached_input_tokens": 25,
                            "output_tokens": 10,
                        },
                    }
                ),
                json.dumps(
                    {
                        "event": "span_end",
                        "span_type": "response",
                        "duration_s": 2.5,
                        "usage": {
                            "input_tokens": 400,
                            "cached_input_tokens": 100,
                            "output_tokens": 20,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event": "request", "tool": "observe"}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "payload": {"observation_id": "raw_fpv_1"},
                    }
                ),
                json.dumps({"event": "response", "tool": "done", "payload": {"ok": True}}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    timing = {
        "kickoff_prompt_chars": 80,
        "cache_tools_list": True,
        "sdk_model_settings": {"prompt_cache_retention": "in_memory"},
        "kickoff_prompt_stable_prefix": {"hash": "stable-hash"},
        "openai_agents_attempts": [
            {"attempt_index": 0, "continuation_prompt_chars": 0},
            {"attempt_index": 1, "continuation_prompt_chars": 40},
        ],
    }

    context = _context_metrics(run_dir, timing)
    cache = _cache_metrics(context, timing)
    growth = _context_growth_metrics(run_dir, timing)

    assert context["available"] is True
    assert context["source"] == "openai_agents_span_usage"
    assert context["response_span_count"] == 2
    assert context["total_input_tokens"] == 500
    assert context["total_cached_input_tokens"] == 125
    assert context["total_uncached_input_tokens"] == 375
    assert context["cache_hit_ratio"] == 0.25
    assert context["p50_input_tokens"] == 100
    assert context["p95_input_tokens"] == 400
    assert context["total_reasoning_tokens"] == 4
    assert context["response_span_duration_s"] == 4.0
    assert context["kickoff_prompt_estimated_tokens"] == 20
    assert context["continuation_prompt_estimated_tokens"] == 10
    assert cache["available"] is True
    assert cache["provider_prompt_cache_observed"] is True
    assert cache["first_response_cached_tokens"] == 25
    assert cache["prompt_cache_retention"] == "in_memory"
    assert cache["stable_prefix_hash"] == "stable-hash"
    assert cache["mcp_tool_catalog_cache_enabled"] is True
    assert growth["available"] is True
    assert growth["trace_event_count"] == 3
    assert growth["observe_response_count"] == 1
    assert growth["raw_fpv_observation_count"] == 1
    assert growth["continuation_attempt_count"] == 1
    assert growth["tool_response_bytes_total"] > 0


def test_openai_agents_context_metrics_missing_usage_is_unavailable(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-spans.jsonl").write_text(
        json.dumps({"event": "span_end", "span_type": "response"}) + "\n",
        encoding="utf-8",
    )

    context = _context_metrics(run_dir, {"cache_tools_list": True})
    cache = _cache_metrics(
        context,
        {
            "cache_tools_list": True,
            "sdk_model_settings": {"prompt_cache_retention": "in_memory"},
            "kickoff_prompt_stable_prefix": {"hash": "stable-hash"},
        },
    )

    assert context["available"] is False
    assert context["source"] == "openai_agents_span_usage"
    assert "response_span_usage_missing" in context["limitations"]
    assert "total_input_tokens" not in context
    assert cache["available"] is False
    assert cache["source"] == "openai_agents_span_usage"
    assert "response_span_usage_missing" in cache["limitations"]
    assert cache["prompt_cache_retention"] == "in_memory"
    assert cache["stable_prefix_hash"] == "stable-hash"


def test_openai_agents_model_input_filter_metrics_are_aggregate_only(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "openai-agents-events.jsonl").write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "schema": "openai_agents_model_input_filter_v1",
                        "event": "model_input_filter",
                        "provider_profile": "codex-env",
                        "wire_api": "responses",
                        "model": "gpt-5.5",
                        "config": {
                            "enabled": True,
                            "mode": "public_tool_result_summary_v1",
                        },
                        "metrics": {
                            "input_item_count": 3,
                            "compacted_item_count": 2,
                            "unchanged_item_count": 1,
                            "repeated_item_count": 1,
                            "input_bytes_before": 2000,
                            "input_bytes_after": 800,
                            "input_bytes_reduced": 1200,
                            "metric_map_output_count": 2,
                            "repeated_metric_map_output_count": 1,
                            "metric_map_delta_compacted_count": 1,
                            "metric_map_bytes_before": 1400,
                            "metric_map_bytes_after": 500,
                            "metric_map_bytes_reduced": 900,
                        },
                    }
                ),
                json.dumps(
                    {
                        "schema": "openai_agents_model_input_filter_v1",
                        "event": "model_input_filter",
                        "provider_profile": "codex-env",
                        "wire_api": "responses",
                        "model": "gpt-5.5",
                        "config": {
                            "enabled": True,
                            "mode": "public_tool_result_summary_v1",
                        },
                        "metrics": {
                            "input_item_count": 2,
                            "compacted_item_count": 0,
                            "unchanged_item_count": 2,
                            "input_bytes_before": 500,
                            "input_bytes_after": 500,
                            "input_bytes_reduced": 0,
                            "metric_map_output_count": 1,
                            "metric_map_bytes_before": 300,
                            "metric_map_bytes_after": 300,
                            "metric_map_bytes_reduced": 0,
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    metrics = _model_input_filter_metrics(run_dir)

    assert metrics["available"] is True
    assert metrics["source"] == "openai_agents_model_input_filter_events"
    assert metrics["event_count"] == 2
    assert metrics["enabled"] is True
    assert metrics["modes"] == ["public_tool_result_summary_v1"]
    assert metrics["attempted_provider_profiles"] == ["codex-env"]
    assert metrics["attempted_wire_apis"] == ["responses"]
    assert metrics["compacted_item_count"] == 2
    assert metrics["unchanged_item_count"] == 3
    assert metrics["repeated_item_count"] == 1
    assert metrics["input_bytes_before"] == 2500
    assert metrics["input_bytes_after"] == 1300
    assert metrics["input_bytes_reduced"] == 1200
    assert metrics["input_byte_reduction_ratio"] == 0.48
    assert metrics["metric_map_output_count"] == 3
    assert metrics["repeated_metric_map_output_count"] == 1
    assert metrics["metric_map_delta_compacted_count"] == 1
    assert metrics["metric_map_bytes_before"] == 1700
    assert metrics["metric_map_bytes_after"] == 800
    assert metrics["metric_map_bytes_reduced"] == 900
    assert metrics["metric_map_byte_reduction_ratio"] == 0.529412
    assert "Raw prompts" in metrics["privacy_note"]
    assert "tool payload bodies" in metrics["privacy_note"]


def test_openai_agents_live_timing_timeline_partitions_runner_and_attribution() -> None:
    timing = {
        "surface": "household-world",
        "intent": "open-ended",
        "task_name": "household-cleanup",
        "task_intent_mode": "default_cleanup",
        "runtime": "openai-agents-live",
        "provider_profile": "codex-env",
        "wire_api": "responses",
        "model": "gpt-5.5",
        "evidence_lane": "world-public-labels",
        "started_at_epoch": 100.0,
        "openai_agents_start_epoch": 105.0,
        "openai_agents_end_epoch": 145.0,
        "server_finished_epoch": 146.0,
        "checker_start_epoch": 146.5,
        "checker_end_epoch": 148.0,
        "finished_at_epoch": 149.0,
        "mcp_client_session_timeout_s": 30.0,
        "runner_timing": {
            "total_elapsed_s": 49.0,
            "openai_agents_elapsed_s": 40.0,
        },
        "mcp_trace_timing": {
            "total_elapsed_s": 33.0,
            "between_tool_gap_s": 20.0,
            "robot_view_capture_s": 6.0,
            "tool_handler_s": 5.0,
            "other_mcp_overhead_s": 2.0,
            "tool_call_count": 10,
        },
        "mcp_control_plane_metrics": {"list_tools_request_count": 2},
        "openai_agents_event_metrics": {
            "tool_error_count": 1,
            "tool_error_classifications": {"mcp_client_request_timeout": 1},
        },
        "openai_agents_span_metrics": {
            "available": True,
            "span_end_count": 3,
            "span_type_counts": {"function": 2, "response": 1},
            "limitations": [],
        },
        "model_service_fallback_metrics": {
            "available": True,
            "source": "openai_agents_model_service_fallback_events",
            "limitations": [],
            "attempt_event_count": 2,
            "retry_scheduled_count": 1,
            "failure_event_count": 1,
            "success_event_count": 1,
            "failure_classes": {"provider_transient_failure": 1},
            "provider_reasons": {"upstream_unavailable": 1},
            "attempted_models": ["gpt-5.5"],
            "attempted_provider_profiles": ["codex-env"],
            "attempted_wire_apis": ["responses"],
            "retry_delay_s_total": 1.0,
            "retry_delay_count": 1,
            "retry_exhausted": False,
            "final_outcomes": {"success": 1},
        },
        "model_input_filter_metrics": {
            "available": True,
            "source": "openai_agents_model_input_filter_events",
            "limitations": [],
            "event_count": 2,
            "enabled": True,
            "modes": ["public_tool_result_summary_v1"],
            "attempted_models": ["gpt-5.5"],
            "attempted_provider_profiles": ["codex-env"],
            "attempted_wire_apis": ["responses"],
            "compacted_item_count": 2,
            "unchanged_item_count": 3,
            "repeated_item_count": 1,
            "input_bytes_before": 2500,
            "input_bytes_after": 1300,
            "input_bytes_reduced": 1200,
            "input_byte_reduction_ratio": 0.48,
            "metric_map_output_count": 3,
            "repeated_metric_map_output_count": 1,
            "metric_map_delta_compacted_count": 1,
            "metric_map_bytes_before": 1700,
            "metric_map_bytes_after": 800,
            "metric_map_bytes_reduced": 900,
            "metric_map_byte_reduction_ratio": 0.529412,
        },
        "context_metrics": {
            "available": True,
            "source": "openai_agents_span_usage",
            "limitations": [],
            "total_input_tokens": 500,
            "total_cached_input_tokens": 125,
            "total_uncached_input_tokens": 375,
            "cache_hit_ratio": 0.25,
            "response_span_duration_s": 4.0,
        },
        "cache_metrics": {
            "available": True,
            "source": "openai_agents_span_usage",
            "limitations": [],
            "provider_prompt_cache_observed": True,
            "cached_input_token_ratio": 0.25,
        },
        "context_growth_metrics": {
            "available": True,
            "source": "live_timing_and_trace",
            "limitations": [],
            "trace_event_count": 10,
            "observe_response_count": 2,
            "raw_fpv_observation_count": 0,
            "tool_response_bytes_total": 1000,
            "continuation_attempt_count": 1,
        },
        "openai_agents_attempts": [
            {
                "attempt_index": 0,
                "attempt_role": "initial",
                "phase": "agent-turn-complete",
                "started_at_epoch": 105.0,
                "finished_at_epoch": 115.0,
                "run_result_present": False,
                "recovery_action": "continue",
                "recovery_reason": "incomplete_agent_turn",
            },
            {
                "attempt_index": 1,
                "attempt_role": "continuation",
                "phase": "finished",
                "started_at_epoch": 115.0,
                "finished_at_epoch": 145.0,
                "run_result_present": True,
            },
        ],
    }

    timeline = _live_timing_timeline(timing)

    assert timeline["schema"] == "live_agent_timeline_v1"
    assert timeline["surface"] == "household-world"
    assert timeline["intent"] == "open-ended"
    assert timeline["task_name"] == "household-cleanup"
    assert timeline["task_intent_mode"] == "default_cleanup"
    assert timeline["runtime"] == "openai-agents-live"
    assert timeline["provider_profile"] == "codex-env"
    assert timeline["wire_api"] == "responses"
    assert timeline["model"] == "gpt-5.5"
    assert timeline["evidence_lane"] == "world-public-labels"
    assert [segment["duration_s"] for segment in timeline["runner_segments"]] == [
        5.0,
        40.0,
        1.0,
        1.5,
        1.0,
    ]
    assert [segment["name"] for segment in timeline["openai_agents_attempt_segments"]] == [
        "sdk_attempt_0",
        "sdk_attempt_1",
    ]
    assert timeline["latency_attribution"]["model_or_sdk_unattributed_s"] == 3.0
    assert timeline["latency_attribution"]["openai_agents_tool_error_classifications"] == {
        "mcp_client_request_timeout": 1
    }
    assert timeline["latency_attribution"]["openai_agents_span_artifact_available"] is True
    assert timeline["latency_attribution"]["openai_agents_span_count"] == 3
    assert timeline["latency_attribution"]["openai_agents_span_type_counts"] == {
        "function": 2,
        "response": 1,
    }
    assert timeline["latency_attribution"]["model_service_fallback_metrics"] == {
        "available": True,
        "source": "openai_agents_model_service_fallback_events",
        "limitations": [],
        "attempt_event_count": 2,
        "retry_scheduled_count": 1,
        "failure_event_count": 1,
        "success_event_count": 1,
        "failure_classes": {"provider_transient_failure": 1},
        "provider_reasons": {"upstream_unavailable": 1},
        "attempted_models": ["gpt-5.5"],
        "attempted_provider_profiles": ["codex-env"],
        "attempted_wire_apis": ["responses"],
        "retry_delay_s_total": 1.0,
        "retry_delay_count": 1,
        "retry_exhausted": False,
        "final_outcomes": {"success": 1},
    }
    assert timeline["latency_attribution"]["model_input_filter_metrics"] == {
        "available": True,
        "source": "openai_agents_model_input_filter_events",
        "limitations": [],
        "event_count": 2,
        "enabled": True,
        "modes": ["public_tool_result_summary_v1"],
        "attempted_models": ["gpt-5.5"],
        "attempted_provider_profiles": ["codex-env"],
        "attempted_wire_apis": ["responses"],
        "compacted_item_count": 2,
        "unchanged_item_count": 3,
        "repeated_item_count": 1,
        "input_bytes_before": 2500,
        "input_bytes_after": 1300,
        "input_bytes_reduced": 1200,
        "input_byte_reduction_ratio": 0.48,
        "metric_map_output_count": 3,
        "repeated_metric_map_output_count": 1,
        "metric_map_delta_compacted_count": 1,
        "metric_map_bytes_before": 1700,
        "metric_map_bytes_after": 800,
        "metric_map_bytes_reduced": 900,
        "metric_map_byte_reduction_ratio": 0.529412,
    }
    assert timeline["latency_attribution"]["context_metrics"] == {
        "available": True,
        "source": "openai_agents_span_usage",
        "limitations": [],
        "total_input_tokens": 500,
        "total_cached_input_tokens": 125,
        "total_uncached_input_tokens": 375,
        "cache_hit_ratio": 0.25,
    }
    assert timeline["latency_attribution"]["cache_metrics"] == {
        "available": True,
        "source": "openai_agents_span_usage",
        "limitations": [],
        "cached_input_token_ratio": 0.25,
        "provider_prompt_cache_observed": True,
    }
    assert timeline["latency_attribution"]["context_growth_metrics"] == {
        "available": True,
        "source": "live_timing_and_trace",
        "limitations": [],
        "trace_event_count": 10,
        "observe_response_count": 2,
        "raw_fpv_observation_count": 0,
        "tool_response_bytes_total": 1000,
        "continuation_attempt_count": 1,
    }

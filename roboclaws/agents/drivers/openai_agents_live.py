"""Experimental OpenAI Agents SDK live-agent runtime."""

from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from roboclaws.agents.live_runtime import LiveAgentRequest, LiveAgentResult, LiveAgentRuntime
from roboclaws.agents.live_status import LiveAgentFailure

DEFAULT_OPENAI_AGENTS_MAX_TURNS = 128
MCP_CLIENT_SESSION_TIMEOUT_ENV = "ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S"
DEFAULT_MODEL_SERVICE_RETRY_ATTEMPTS = 1
DEFAULT_MODEL_SERVICE_RETRY_SLEEP_S = 1.0
MODEL_SERVICE_RETRY_ATTEMPTS_ENV = "ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_ATTEMPTS"
MODEL_SERVICE_RETRY_SLEEP_ENV = "ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_SLEEP_S"


class OpenAIAgentsLiveRuntime(LiveAgentRuntime):
    """Run one Roboclaws live-agent turn through the OpenAI Agents SDK.

    This runtime is intentionally private/experimental. It does not claim Codex
    CLI equivalence and it does not infer cleanup completion; the MCP server's
    ``done`` path still owns ``run_result.json`` and checker eligibility.
    """

    runtime_name = "openai-agents-live"

    def run(self, request: LiveAgentRequest) -> LiveAgentResult:
        started_at = time.time()
        request.run_dir.mkdir(parents=True, exist_ok=True)
        events_path = request.artifact_path("openai_agents_events", "openai-agents-events.jsonl")
        trace_path = request.artifact_path("openai_agents_trace", "openai-agents-trace.json")
        spans_path = request.artifact_path("openai_agents_spans", "openai-agents-spans.jsonl")
        status_path = request.artifact_path("live_status", "live_status.json")

        try:
            result = _run_openai_agents(request, events_path=events_path, spans_path=spans_path)
        except ImportError:
            failure = LiveAgentFailure(
                "provider_config_failure",
                retryable=False,
                detail=(
                    "OpenAI Agents SDK is not installed. Install it in a local experimental "
                    "environment before running openai-agents-live."
                ),
            )
            normalized = LiveAgentResult.from_failure(
                phase="failed",
                exit_status=1,
                failure=failure,
                started_at_epoch=started_at,
                finished_at_epoch=time.time(),
                artifact_paths={
                    "openai_agents_events": events_path,
                    "openai_agents_spans": spans_path,
                    "live_status": status_path,
                },
            )
            _write_json(status_path, normalized.to_live_status_payload())
            return normalized
        except Exception as exc:
            failure = _failure_from_exception(exc)
            normalized = LiveAgentResult.from_failure(
                phase="failed",
                exit_status=1,
                failure=failure,
                started_at_epoch=started_at,
                finished_at_epoch=time.time(),
                artifact_paths={
                    "openai_agents_events": events_path,
                    "openai_agents_spans": spans_path,
                    "live_status": status_path,
                },
            )
            _write_json(status_path, normalized.to_live_status_payload())
            return normalized

        finished_at = time.time()
        run_result_path = request.run_dir / "run_result.json"
        artifact_paths = {
            "openai_agents_events": events_path,
            "openai_agents_trace": trace_path,
            "openai_agents_spans": spans_path,
            "live_status": status_path,
        }
        if run_result_path.exists():
            artifact_paths["run_result"] = run_result_path
        sdk_result = _summarize_sdk_result(result)
        _write_json(trace_path, sdk_result)
        normalized = LiveAgentResult(
            phase="finished" if run_result_path.exists() else "agent-turn-complete",
            exit_status=0,
            started_at_epoch=started_at,
            finished_at_epoch=finished_at,
            artifact_paths=artifact_paths,
            provider_session_id=str(sdk_result.get("session_id") or ""),
            trace_id=str(sdk_result.get("trace_id") or ""),
            run_result_present=run_result_path.exists(),
            usage=sdk_result.get("usage") if isinstance(sdk_result.get("usage"), dict) else {},
            timing={"runtime_wall_seconds": round(finished_at - started_at, 3)},
        )
        _write_json(status_path, normalized.to_live_status_payload())
        return normalized


def _run_openai_agents(
    request: LiveAgentRequest,
    *,
    events_path: Path,
    spans_path: Path,
) -> Any:
    try:
        from agents import Agent, Runner  # type: ignore[import-not-found]
        from agents.mcp import MCPServerStreamableHttp  # type: ignore[import-not-found]
    except ImportError:
        raise
    try:
        from agents import add_trace_processor, flush_traces  # type: ignore[import-not-found]
    except ImportError:
        add_trace_processor = None
        flush_traces = None

    model = _responses_model(request)
    timeout_configured, timeout_s = _mcp_client_session_timeout_seconds(request)
    runtime_config = _runtime_config(
        request,
        mcp_client_session_timeout_configured=timeout_configured,
        mcp_client_session_timeout_s=timeout_s,
    )
    server_kwargs: dict[str, Any] = {
        "name": request.mcp_server.name,
        "params": {"url": request.mcp_server.url},
        "cache_tools_list": _cache_tools_list(request),
    }
    if timeout_configured:
        server_kwargs["client_session_timeout_seconds"] = timeout_s
    server = MCPServerStreamableHttp(
        **server_kwargs,
    )
    agent_kwargs: dict[str, Any] = {
        "name": f"roboclaws-{request.task_name}",
        "instructions": request.kickoff_prompt,
        "mcp_servers": [server],
        "mcp_config": {
            "failure_error_function": _recording_tool_error_function(
                events_path,
                runtime_config=runtime_config,
            )
        },
        "model": model,
    }
    agent = Agent(**agent_kwargs)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")
    spans_path.parent.mkdir(parents=True, exist_ok=True)
    spans_path.write_text("", encoding="utf-8")
    _append_event(events_path, {"event": "start", "ts_epoch": time.time(), **runtime_config})
    span_processor = _RoboclawsSpanRecorder(spans_path, runtime_config=runtime_config)
    if add_trace_processor is None:
        _append_span_limitation(
            spans_path,
            runtime_config=runtime_config,
            reason="sdk_trace_processor_api_unavailable",
        )
        span_processor = None
    else:
        try:
            add_trace_processor(span_processor)
        except Exception as exc:
            _append_span_limitation(
                spans_path,
                runtime_config=runtime_config,
                reason="sdk_trace_processor_registration_failed",
                exc=exc,
            )
            span_processor = None

    try:
        if hasattr(server, "__aenter__"):
            return _run_with_async_mcp_server(server, agent, request, events_path)
        runner_kwargs: dict[str, Any] = {"max_turns": _max_turns(request)}
        result = Runner.run_sync(agent, request.kickoff_prompt, **runner_kwargs)
        _append_event(
            events_path,
            {"event": "result", "ts_epoch": time.time(), "summary": _summarize_sdk_result(result)},
        )
        return result
    finally:
        if flush_traces is not None:
            try:
                flush_traces()
            except Exception as exc:
                _append_event(
                    events_path,
                    {
                        "event": "trace_flush_error",
                        "ts_epoch": time.time(),
                        "error_type": exc.__class__.__name__,
                        "message": str(exc),
                    },
                )
        if span_processor is not None:
            span_processor.force_flush()
            span_processor.shutdown()


def _run_with_async_mcp_server(
    server: Any,
    agent: Any,
    request: LiveAgentRequest,
    events_path: Path,
) -> Any:
    import asyncio

    async def _run() -> Any:
        from agents import Runner  # type: ignore[import-not-found]

        async with server:
            runner_kwargs: dict[str, Any] = {"max_turns": _max_turns(request)}
            result = await Runner.run(agent, request.kickoff_prompt, **runner_kwargs)
        _append_event(
            events_path,
            {"event": "result", "ts_epoch": time.time(), "summary": _summarize_sdk_result(result)},
        )
        return result

    return asyncio.run(_run())


def _max_turns(request: LiveAgentRequest) -> int:
    if request.max_turns is not None:
        return request.max_turns
    configured = request.metadata.get("max_turns") if isinstance(request.metadata, dict) else None
    try:
        value = int(configured) if configured is not None else DEFAULT_OPENAI_AGENTS_MAX_TURNS
    except (TypeError, ValueError):
        return DEFAULT_OPENAI_AGENTS_MAX_TURNS
    return max(1, value)


def _cache_tools_list(request: LiveAgentRequest) -> bool:
    configured = None
    if isinstance(request.metadata, dict):
        configured = request.metadata.get("cache_tools_list")
    if configured is None:
        configured = os.environ.get("ROBOCLAWS_OPENAI_AGENTS_CACHE_TOOLS_LIST")
    if configured is None:
        return True
    if isinstance(configured, bool):
        return configured
    return str(configured).strip().lower() not in {"0", "false", "no", "off"}


def _mcp_client_session_timeout_seconds(request: LiveAgentRequest) -> tuple[bool, float | None]:
    configured = None
    if isinstance(request.metadata, dict):
        configured = request.metadata.get("mcp_client_session_timeout_s")
    if configured is None:
        configured = os.environ.get(MCP_CLIENT_SESSION_TIMEOUT_ENV)
    if configured is None or str(configured).strip() == "":
        return False, None
    try:
        value = float(configured)
    except (TypeError, ValueError):
        return False, None
    if value <= 0:
        return True, None
    return True, round(value, 3)


def _runtime_config(
    request: LiveAgentRequest,
    *,
    mcp_client_session_timeout_configured: bool,
    mcp_client_session_timeout_s: float | None,
) -> dict[str, Any]:
    model_retry = _model_service_retry_config(request)
    return {
        "runtime": "openai-agents-live",
        "provider_profile": request.provider_profile,
        "model": request.model,
        "max_turns": _max_turns(request),
        "cache_tools_list": _cache_tools_list(request),
        "mcp_server": {
            "name": request.mcp_server.name,
            "transport": request.mcp_server.transport,
            "url": request.mcp_server.url,
        },
        "mcp_client_session_timeout_configured": mcp_client_session_timeout_configured,
        "mcp_client_session_timeout_s": mcp_client_session_timeout_s,
        "model_service_retry_attempts": model_retry["retry_attempts"],
        "model_service_retry_sleep_s": model_retry["retry_sleep_s"],
    }


def _recording_tool_error_function(
    events_path: Path,
    *,
    runtime_config: dict[str, Any],
) -> Any:
    def _format_tool_error(_context: Any, error: Exception) -> str:
        message = str(error)
        _append_event(
            events_path,
            {
                "event": "tool_error",
                "ts_epoch": time.time(),
                "error_type": error.__class__.__name__,
                "classification": _classify_tool_error(message),
                "message": message,
                "mcp_client_session_timeout_s": runtime_config.get("mcp_client_session_timeout_s"),
            },
        )
        return f"An error occurred while running the tool. Please try again. Error: {message}"

    return _format_tool_error


def _classify_tool_error(message: str) -> str:
    lowered = message.lower()
    if "timed out while waiting for response to clientrequest" in lowered:
        return "mcp_client_request_timeout"
    if "connection timeout" in lowered or "timed out" in lowered or "timeout" in lowered:
        return "timeout"
    if "connection lost" in lowered or "connection reset" in lowered:
        return "connection_lost"
    return "tool_error"


def _summarize_sdk_result(result: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for attr in ("final_output", "last_agent", "trace_id"):
        value = getattr(result, attr, None)
        if value is None:
            continue
        payload[attr] = str(value)
    usage = getattr(result, "usage", None)
    if usage is not None:
        payload["usage"] = _to_jsonable(usage)
    session_id = getattr(result, "session_id", None)
    if session_id:
        payload["session_id"] = str(session_id)
    return payload


class _RoboclawsSpanRecorder:
    """Tracing processor that writes sanitized SDK span metadata.

    The OpenAI Agents SDK span export can include raw model input/output and
    function input/output. Roboclaws keeps only identifiers, timing, span type,
    model/usage, MCP tool names, and error metadata so live artifacts stay useful
    without persisting prompts, credentials, or private evaluator truth.
    """

    def __init__(self, path: Path, *, runtime_config: dict[str, Any]) -> None:
        self.path = path
        self.runtime_config = runtime_config
        self.active = True

    def on_trace_start(self, trace: Any) -> None:
        self._append(
            {
                "event": "trace_start",
                "ts_epoch": time.time(),
                "trace_id": str(getattr(trace, "trace_id", "") or ""),
                "workflow_name": str(getattr(trace, "name", "") or ""),
            }
        )

    def on_trace_end(self, trace: Any) -> None:
        self._append(
            {
                "event": "trace_end",
                "ts_epoch": time.time(),
                "trace_id": str(getattr(trace, "trace_id", "") or ""),
                "workflow_name": str(getattr(trace, "name", "") or ""),
            }
        )

    def on_span_start(self, span: Any) -> None:
        self._append(_sanitized_span_event(span, event="span_start", runtime_config=None))

    def on_span_end(self, span: Any) -> None:
        self._append(_sanitized_span_event(span, event="span_end", runtime_config=None))

    def shutdown(self) -> None:
        self.active = False

    def force_flush(self) -> None:
        return None

    def _append(self, payload: dict[str, Any]) -> None:
        if not self.active:
            return
        payload.setdefault("schema", "openai_agents_sanitized_span_v1")
        payload.setdefault("runtime", self.runtime_config.get("runtime"))
        payload.setdefault("provider_profile", self.runtime_config.get("provider_profile"))
        payload.setdefault("model", self.runtime_config.get("model"))
        _append_event(self.path, _drop_empty(payload))


def _append_span_limitation(
    path: Path,
    *,
    runtime_config: dict[str, Any],
    reason: str,
    exc: Exception | None = None,
) -> None:
    payload = {
        "schema": "openai_agents_sanitized_span_v1",
        "event": "span_capture_unavailable",
        "ts_epoch": time.time(),
        "runtime": runtime_config.get("runtime"),
        "provider_profile": runtime_config.get("provider_profile"),
        "model": runtime_config.get("model"),
        "reason": reason,
    }
    if exc is not None:
        payload["error_type"] = exc.__class__.__name__
        payload["message"] = str(exc)
    _append_event(path, _drop_empty(payload))


def _sanitized_span_event(
    span: Any,
    *,
    event: str,
    runtime_config: dict[str, Any] | None,
) -> dict[str, Any]:
    span_data = getattr(span, "span_data", None)
    exported = _span_data_export(span_data)
    payload: dict[str, Any] = {
        "schema": "openai_agents_sanitized_span_v1",
        "event": event,
        "ts_epoch": time.time(),
        "trace_id": str(getattr(span, "trace_id", "") or ""),
        "span_id": str(getattr(span, "span_id", "") or ""),
        "parent_id": str(getattr(span, "parent_id", "") or ""),
        "started_at": getattr(span, "started_at", None),
        "ended_at": getattr(span, "ended_at", None),
        "duration_s": _iso_duration_seconds(
            getattr(span, "started_at", None),
            getattr(span, "ended_at", None),
        ),
        "span_type": str(_span_export_value(exported, "type") or getattr(span_data, "type", "")),
        "span_name": _safe_span_name(exported, span_data),
        "error": _sanitized_span_error(getattr(span, "error", None)),
        "usage": _span_usage(exported),
        "mcp": _span_mcp(exported),
        "model": _span_model(exported),
    }
    if runtime_config:
        payload.update(
            {
                "runtime": runtime_config.get("runtime"),
                "provider_profile": runtime_config.get("provider_profile"),
                "model": runtime_config.get("model"),
            }
        )
    return _drop_empty(payload)


def _span_data_export(span_data: Any) -> dict[str, Any]:
    if span_data is None or not hasattr(span_data, "export"):
        return {}
    try:
        exported = span_data.export()
    except Exception:
        return {}
    return exported if isinstance(exported, dict) else {}


def _span_export_value(exported: dict[str, Any], key: str) -> Any:
    if key in exported:
        return exported[key]
    data = exported.get("data")
    if isinstance(data, dict):
        return data.get(key) or data.get(f"sdk_span_{key}")
    return None


def _safe_span_name(exported: dict[str, Any], span_data: Any) -> str:
    span_type = str(_span_export_value(exported, "type") or getattr(span_data, "type", "") or "")
    name = _span_export_value(exported, "name")
    if span_type == "function":
        return str(name or "")
    if span_type in {"agent", "task", "turn", "custom", "mcp_list_tools"}:
        return str(name or "")
    return ""


def _span_usage(exported: dict[str, Any]) -> dict[str, Any]:
    usage = _span_export_value(exported, "usage")
    return _to_jsonable(usage) if isinstance(usage, dict) else {}


def _span_mcp(exported: dict[str, Any]) -> dict[str, Any]:
    mcp: dict[str, Any] = {}
    mcp_data = exported.get("mcp_data")
    if isinstance(mcp_data, dict):
        for key in ("server", "tool_name", "name"):
            if key in mcp_data:
                mcp[key] = mcp_data[key]
    server = exported.get("server")
    if server:
        mcp["server"] = server
    result = exported.get("result")
    if isinstance(result, list):
        mcp["tool_names"] = [str(item) for item in result]
        mcp["tool_count"] = len(result)
    return _to_jsonable(mcp) if mcp else {}


def _span_model(exported: dict[str, Any]) -> str:
    model = _span_export_value(exported, "model")
    return str(model or "")


def _sanitized_span_error(error: Any) -> dict[str, Any]:
    if not isinstance(error, dict):
        return {}
    payload: dict[str, Any] = {}
    message = str(error.get("message") or "")
    if message:
        payload["message"] = message
    data = error.get("data")
    if isinstance(data, dict):
        payload["data_keys"] = sorted(str(key) for key in data.keys())
    return payload


def _iso_duration_seconds(started_at: Any, ended_at: Any) -> float | None:
    if not started_at or not ended_at:
        return None
    from datetime import datetime

    try:
        start = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        end = datetime.fromisoformat(str(ended_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return round(max(0.0, (end - start).total_seconds()), 3)


def _drop_empty(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if not _is_empty_json_value(value)}


def _is_empty_json_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str) and value == "":
        return True
    if isinstance(value, (list, tuple, dict)) and not value:
        return True
    return False


def _responses_model(request: LiveAgentRequest) -> Any:
    from agents import OpenAIResponsesModel  # type: ignore[import-not-found]
    from openai import AsyncOpenAI  # type: ignore[import-not-found]

    settings = _responses_model_settings(request)
    client = AsyncOpenAI(
        api_key=settings["api_key"],
        base_url=settings["base_url"],
    )
    base_model = OpenAIResponsesModel(settings["model"], openai_client=client)
    retry_config = _model_service_retry_config(request)
    if retry_config["retry_attempts"] <= 0:
        return base_model
    return _RetryingModel(
        base_model,
        retry_attempts=int(retry_config["retry_attempts"]),
        retry_sleep_s=float(retry_config["retry_sleep_s"]),
        events_path=request.artifact_path("openai_agents_events", "openai-agents-events.jsonl"),
        spans_path=request.artifact_path("openai_agents_spans", "openai-agents-spans.jsonl"),
        runtime_config=_runtime_config(
            request,
            mcp_client_session_timeout_configured=_mcp_client_session_timeout_seconds(request)[0],
            mcp_client_session_timeout_s=_mcp_client_session_timeout_seconds(request)[1],
        ),
    )


def _model_service_retry_config(request: LiveAgentRequest) -> dict[str, int | float]:
    metadata = dict(request.metadata)
    attempts = _non_negative_int(
        metadata.get("model_service_retry_attempts"),
        env_name=MODEL_SERVICE_RETRY_ATTEMPTS_ENV,
        default=DEFAULT_MODEL_SERVICE_RETRY_ATTEMPTS,
    )
    sleep_s = _non_negative_float(
        metadata.get("model_service_retry_sleep_s"),
        env_name=MODEL_SERVICE_RETRY_SLEEP_ENV,
        default=DEFAULT_MODEL_SERVICE_RETRY_SLEEP_S,
    )
    return {"retry_attempts": attempts, "retry_sleep_s": sleep_s}


class _RetryingModel:
    """Retry transient provider failures at the SDK model request boundary."""

    def __init__(
        self,
        base_model: Any,
        *,
        retry_attempts: int,
        retry_sleep_s: float,
        events_path: Path,
        spans_path: Path,
        runtime_config: dict[str, Any],
    ) -> None:
        self.base_model = base_model
        self.retry_attempts = max(0, retry_attempts)
        self.retry_sleep_s = max(0.0, retry_sleep_s)
        self.events_path = events_path
        self.spans_path = spans_path
        self.runtime_config = dict(runtime_config)

    async def close(self) -> None:
        close = getattr(self.base_model, "close", None)
        if close is None:
            return None
        result = close()
        if hasattr(result, "__await__"):
            await result
        return None

    def get_retry_advice(self, request: Any) -> Any:
        get_retry_advice = getattr(self.base_model, "get_retry_advice", None)
        if get_retry_advice is None:
            return None
        return get_retry_advice(request)

    async def get_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any,
    ) -> Any:
        attempt_index = 0
        while True:
            started = time.time()
            _append_model_service_event(
                self.events_path,
                self.spans_path,
                "model_service_attempt",
                runtime_config=self.runtime_config,
                attempt_index=attempt_index,
                retry_budget=self.retry_attempts,
                method="get_response",
            )
            try:
                result = await self.base_model.get_response(
                    system_instructions,
                    input,
                    model_settings,
                    tools,
                    output_schema,
                    handoffs,
                    tracing,
                    previous_response_id=previous_response_id,
                    conversation_id=conversation_id,
                    prompt=prompt,
                )
            except Exception as exc:
                should_retry, failure = _should_retry_model_service_failure(
                    exc,
                    attempt_index=attempt_index,
                    retry_attempts=self.retry_attempts,
                )
                _append_model_service_failure_events(
                    self.events_path,
                    self.spans_path,
                    runtime_config=self.runtime_config,
                    attempt_index=attempt_index,
                    retry_budget=self.retry_attempts,
                    method="get_response",
                    started_at=started,
                    failure=failure,
                    will_retry=should_retry,
                    retry_delay_s=self.retry_sleep_s if should_retry else None,
                    safe_to_replay=True,
                )
                if not should_retry:
                    raise
                if self.retry_sleep_s:
                    await asyncio.sleep(self.retry_sleep_s)
                attempt_index += 1
                continue
            _append_model_service_event(
                self.events_path,
                self.spans_path,
                "model_service_success",
                runtime_config=self.runtime_config,
                attempt_index=attempt_index,
                retry_budget=self.retry_attempts,
                method="get_response",
                elapsed_s=_round_duration(time.time() - started),
                final_outcome="success",
            )
            return result

    async def stream_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any,
    ) -> Any:
        attempt_index = 0
        while True:
            started = time.time()
            yielded_event = False
            _append_model_service_event(
                self.events_path,
                self.spans_path,
                "model_service_attempt",
                runtime_config=self.runtime_config,
                attempt_index=attempt_index,
                retry_budget=self.retry_attempts,
                method="stream_response",
            )
            try:
                stream = self.base_model.stream_response(
                    system_instructions,
                    input,
                    model_settings,
                    tools,
                    output_schema,
                    handoffs,
                    tracing,
                    previous_response_id=previous_response_id,
                    conversation_id=conversation_id,
                    prompt=prompt,
                )
                async for event in stream:
                    yielded_event = True
                    yield event
            except Exception as exc:
                safe_to_replay = not yielded_event
                should_retry, failure = _should_retry_model_service_failure(
                    exc,
                    attempt_index=attempt_index,
                    retry_attempts=self.retry_attempts,
                    safe_to_replay=safe_to_replay,
                )
                _append_model_service_failure_events(
                    self.events_path,
                    self.spans_path,
                    runtime_config=self.runtime_config,
                    attempt_index=attempt_index,
                    retry_budget=self.retry_attempts,
                    method="stream_response",
                    started_at=started,
                    failure=failure,
                    will_retry=should_retry,
                    retry_delay_s=self.retry_sleep_s if should_retry else None,
                    safe_to_replay=safe_to_replay,
                )
                if not should_retry:
                    raise
                if self.retry_sleep_s:
                    await asyncio.sleep(self.retry_sleep_s)
                attempt_index += 1
                continue
            _append_model_service_event(
                self.events_path,
                self.spans_path,
                "model_service_success",
                runtime_config=self.runtime_config,
                attempt_index=attempt_index,
                retry_budget=self.retry_attempts,
                method="stream_response",
                elapsed_s=_round_duration(time.time() - started),
                final_outcome="success",
            )
            return


def _should_retry_model_service_failure(
    exc: Exception,
    *,
    attempt_index: int,
    retry_attempts: int,
    safe_to_replay: bool = True,
) -> tuple[bool, LiveAgentFailure]:
    failure = _failure_from_exception(exc)
    should_retry = (
        safe_to_replay
        and failure.reason == "provider_transient_failure"
        and failure.retryable
        and attempt_index < retry_attempts
    )
    return should_retry, failure


def _append_model_service_failure_events(
    events_path: Path,
    spans_path: Path,
    *,
    runtime_config: dict[str, Any],
    attempt_index: int,
    retry_budget: int,
    method: str,
    started_at: float,
    failure: LiveAgentFailure,
    will_retry: bool,
    retry_delay_s: float | None,
    safe_to_replay: bool,
) -> None:
    base_payload = {
        "attempt_index": attempt_index,
        "retry_budget": retry_budget,
        "method": method,
        "failure_class": failure.reason,
        "provider_reason": failure.provider_reason,
        "retryable": failure.retryable,
        "safe_to_replay": safe_to_replay,
        "elapsed_s": _round_duration(time.time() - started_at),
        "final_outcome": "" if will_retry else "failure",
        "retry_exhausted": (
            failure.reason == "provider_transient_failure"
            and failure.retryable
            and not will_retry
            and safe_to_replay
        ),
    }
    _append_model_service_event(
        events_path,
        spans_path,
        "model_service_failure",
        runtime_config=runtime_config,
        **base_payload,
    )
    if will_retry:
        _append_model_service_event(
            events_path,
            spans_path,
            "model_service_retry_scheduled",
            runtime_config=runtime_config,
            **{
                **base_payload,
                "retry_delay_s": retry_delay_s,
                "next_attempt_index": attempt_index + 1,
                "final_outcome": "",
                "retry_exhausted": False,
            },
        )


def _append_model_service_event(
    events_path: Path,
    spans_path: Path,
    event: str,
    *,
    runtime_config: dict[str, Any],
    attempt_index: int,
    retry_budget: int,
    method: str,
    **extra: Any,
) -> None:
    payload = _drop_empty(
        {
            "schema": "openai_agents_model_service_fallback_v1",
            "event": event,
            "ts_epoch": time.time(),
            "runtime": runtime_config.get("runtime"),
            "provider_profile": runtime_config.get("provider_profile"),
            "model": runtime_config.get("model"),
            "attempt_index": attempt_index,
            "retry_budget": retry_budget,
            "method": method,
            **extra,
        }
    )
    _append_event(events_path, payload)
    span_payload = {
        **payload,
        "schema": "openai_agents_sanitized_span_v1",
        "span_type": "model_service_fallback",
    }
    _append_event(spans_path, span_payload)


def _responses_model_settings(request: LiveAgentRequest) -> dict[str, str]:
    metadata = dict(request.metadata)
    provider = str(
        metadata.get("provider_profile")
        or request.provider_profile
        or os.environ.get("ROBOCLAWS_OPENAI_AGENTS_PROVIDER")
        or os.environ.get("ROBOCLAWS_CODEX_PROVIDER")
        or "codex-env"
    )
    provider = provider.strip()
    if provider in {"codex-mify", "mify"}:
        base_url = str(
            metadata.get("base_url")
            or os.environ.get("XM_LLM_BASE_URL")
            or "https://api.llm.mioffice.cn/v1"
        )
        api_key = str(metadata.get("api_key") or os.environ.get("XM_LLM_API_KEY") or "")
        model = str(
            metadata.get("model")
            or request.model
            or os.environ.get("ROBOCLAWS_OPENAI_AGENTS_MODEL")
            or os.environ.get("ROBOCLAWS_CODEX_MODEL")
            or "xiaomi/mimo-v2.5"
        )
        _require_setting("mify", "XM_LLM_API_KEY", api_key)
        return {
            "provider_profile": "mify",
            "base_url": base_url,
            "api_key": api_key,
            "model": model,
        }
    if provider != "codex-env":
        raise RuntimeError(
            "openai-agents-live supports Responses provider profiles codex-env and mify only"
        )

    base_url = str(metadata.get("base_url") or os.environ.get("CODEX_BASE_URL") or "")
    api_key = str(metadata.get("api_key") or os.environ.get("CODEX_API_KEY") or "")
    model = str(
        metadata.get("model")
        or request.model
        or os.environ.get("ROBOCLAWS_OPENAI_AGENTS_MODEL")
        or os.environ.get("ROBOCLAWS_CODEX_MODEL")
        or "gpt-5.5"
    )
    _require_setting("codex-env", "CODEX_BASE_URL", base_url)
    _require_setting("codex-env", "CODEX_API_KEY", api_key)
    return {
        "provider_profile": "codex-env",
        "base_url": base_url,
        "api_key": api_key,
        "model": model,
    }


def _require_setting(provider: str, name: str, value: str) -> None:
    if not value:
        raise RuntimeError(f"{provider} requires {name}")


def _non_negative_int(value: Any, *, env_name: str, default: int) -> int:
    if value is None:
        raw_env = os.environ.get(env_name)
        value = raw_env if raw_env not in {None, ""} else default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, parsed)


def _non_negative_float(value: Any, *, env_name: str, default: float) -> float:
    if value is None:
        raw_env = os.environ.get(env_name)
        value = raw_env if raw_env not in {None, ""} else default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(0.0, parsed)


def _failure_from_exception(exc: Exception) -> LiveAgentFailure:
    detail = str(exc)
    if exc.__class__.__name__ == "MaxTurnsExceeded":
        return LiveAgentFailure(
            "agent_sdk_turn_budget_exceeded",
            retryable=False,
            resume_available=False,
            detail=detail,
        )
    lowered = detail.lower()
    if any(item in lowered for item in ("requires codex_base_url", "requires codex_api_key")):
        return LiveAgentFailure("provider_config_failure", retryable=False, detail=detail)
    if any(item in lowered for item in ("requires xm_llm_api_key", "supports responses provider")):
        return LiveAgentFailure("provider_config_failure", retryable=False, detail=detail)
    if any(
        item in lowered for item in ("authentication", "unauthorized", "invalid api key", "401")
    ):
        return LiveAgentFailure("provider_auth_failure", retryable=False, detail=detail)
    if any(
        item in lowered
        for item in (
            "context length",
            "context_length",
            "context window",
            "maximum context",
            "input exceeds the context",
            "too large",
        )
    ):
        return LiveAgentFailure("provider_context_failure", retryable=False, detail=detail)
    if any(
        item in lowered
        for item in (
            "429",
            "rate limit",
            "too many requests",
            "500",
            "502",
            "503",
            "504",
            "model unavailable",
            "model_unavailable",
            "temporarily unavailable",
            "service unavailable",
            "internal server error",
            "bad gateway",
            "gateway timeout",
        )
    ):
        provider_reason = (
            "rate_limit" if "429" in lowered or "rate limit" in lowered else "upstream_unavailable"
        )
        return LiveAgentFailure(
            "provider_transient_failure",
            retryable=True,
            provider_reason=provider_reason,
            resume_available=True,
            detail=detail,
        )
    if any(
        item in lowered
        for item in (
            "timed out",
            "timeout",
            "connection reset",
            "connection refused",
            "connection error",
            "transport error",
            "broken pipe",
            "econnreset",
        )
    ):
        return LiveAgentFailure(
            "provider_transient_failure",
            retryable=True,
            provider_reason="upstream_timeout",
            resume_available=True,
            detail=detail,
        )
    return LiveAgentFailure("agent_cli_failure", retryable=False, detail=detail)


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _round_duration(value: float) -> float:
    return round(max(0.0, value), 3)


def _to_jsonable(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _to_jsonable(value.model_dump())
    if hasattr(value, "__dict__"):
        return _to_jsonable(vars(value))
    return str(value)

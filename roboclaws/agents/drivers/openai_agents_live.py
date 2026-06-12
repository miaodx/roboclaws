"""Experimental OpenAI Agents SDK live-agent runtime."""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.agents.live_runtime import LiveAgentRequest, LiveAgentResult, LiveAgentRuntime
from roboclaws.agents.live_status import LiveAgentFailure
from roboclaws.agents.provider_registry import (
    normalize_provider_route,
    provider_route_spec,
    route_base_url,
)

try:
    from agents.models.interface import Model as _AgentsModel  # type: ignore[import-not-found]
except ImportError:
    _AgentsModel = object

DEFAULT_OPENAI_AGENTS_MAX_TURNS = 128
MCP_CLIENT_SESSION_TIMEOUT_ENV = "ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S"
DEFAULT_MODEL_SERVICE_RETRY_ATTEMPTS = 1
DEFAULT_MODEL_SERVICE_RETRY_SLEEP_S = 1.0
MODEL_SERVICE_RETRY_ATTEMPTS_ENV = "ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_ATTEMPTS"
MODEL_SERVICE_RETRY_SLEEP_ENV = "ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_SLEEP_S"
DEFAULT_MODEL_INPUT_COMPACTION_MIN_CHARS = 1200
MODEL_INPUT_COMPACTION_MIN_CHARS_ENV = "ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS"
RAW_FPV_OBSERVATION_ID_RE = re.compile(r"raw_fpv_\d+")
MODEL_RACING_OBSERVABILITY_SCHEMA = "agent_sdk_model_racing_observability_v1"
MODEL_RACING_EVENT_SCHEMA = "openai_agents_model_racing_observability_v1"


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
        skill_context_path = request.artifact_path(
            "openai_agents_skill_context",
            "openai-agents-skill-context.json",
        )
        status_path = request.artifact_path("live_status", "live_status.json")

        try:
            result = _run_openai_agents(
                request,
                events_path=events_path,
                spans_path=spans_path,
                skill_context_path=skill_context_path,
            )
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
                    "openai_agents_skill_context": skill_context_path,
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
                    "openai_agents_skill_context": skill_context_path,
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
            "openai_agents_skill_context": skill_context_path,
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
    skill_context_path: Path,
) -> Any:
    try:
        from agents import Agent, ModelSettings, RunConfig, Runner  # type: ignore[import-not-found]
        from agents.mcp import MCPServerStreamableHttp  # type: ignore[import-not-found]
    except ImportError:
        raise
    try:
        from agents import add_trace_processor, flush_traces  # type: ignore[import-not-found]
    except ImportError:
        add_trace_processor = None
        flush_traces = None

    model = _model_for_request(request)
    timeout_configured, timeout_s = _mcp_client_session_timeout_seconds(request)
    runtime_config = _runtime_config(
        request,
        mcp_client_session_timeout_configured=timeout_configured,
        mcp_client_session_timeout_s=timeout_s,
    )
    model_settings_payload = _sdk_model_settings_payload(request)
    run_config_payload = _sdk_run_config_payload(request, events_path=events_path)
    model_settings = ModelSettings(**model_settings_payload)
    run_config = RunConfig(model_settings=model_settings, **run_config_payload)
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
    instructions, skill_context_summary = _instructions_with_skill_context(request)
    _write_skill_context_summary(skill_context_path, skill_context_summary)
    agent_kwargs: dict[str, Any] = {
        "name": f"roboclaws-{request.task_name}",
        "instructions": instructions,
        "mcp_servers": [server],
        "mcp_config": {
            "failure_error_function": _recording_tool_error_function(
                events_path,
                runtime_config=runtime_config,
            )
        },
        "model": model,
        "model_settings": model_settings,
    }
    agent = Agent(**agent_kwargs)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")
    spans_path.parent.mkdir(parents=True, exist_ok=True)
    spans_path.write_text("", encoding="utf-8")
    _append_event(
        events_path,
        {
            "event": "start",
            "ts_epoch": time.time(),
            **runtime_config,
            "skill_context": skill_context_summary,
        },
    )
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
            return _run_with_async_mcp_server(
                server,
                agent,
                request,
                events_path,
                run_config=run_config,
            )
        runner_kwargs: dict[str, Any] = {"max_turns": _max_turns(request)}
        runner_kwargs["run_config"] = run_config
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
    *,
    run_config: Any,
) -> Any:
    import asyncio

    async def _run() -> Any:
        from agents import Runner  # type: ignore[import-not-found]

        async with server:
            runner_kwargs: dict[str, Any] = {
                "max_turns": _max_turns(request),
                "run_config": run_config,
            }
            result = await Runner.run(agent, request.kickoff_prompt, **runner_kwargs)
        _append_event(
            events_path,
            {"event": "result", "ts_epoch": time.time(), "summary": _summarize_sdk_result(result)},
        )
        return result

    return asyncio.run(_run())


def _instructions_with_skill_context(request: LiveAgentRequest) -> tuple[str, dict[str, Any]]:
    context = request.metadata.get("skill_context") if isinstance(request.metadata, dict) else None
    if not isinstance(context, dict):
        return request.kickoff_prompt, _skill_context_summary(
            {
                "skill_name": request.skill_name,
                "included": False,
                "reason": "not_configured",
            }
        )
    content = str(context.get("content") or "")
    summary = _skill_context_summary(
        {
            "skill_name": context.get("skill_name") or request.skill_name,
            "included": bool(content),
            "reason": context.get("reason") or ("included" if content else "empty"),
            "source_path": context.get("source_path"),
            "relative_path": context.get("relative_path"),
            "sha256": context.get("sha256"),
            "bytes": context.get("bytes"),
            "estimated_tokens": context.get("estimated_tokens"),
            "policy": context.get("policy"),
        }
    )
    if not content:
        return request.kickoff_prompt, summary
    instructions = (
        "Canonical skill context for this private OpenAI Agents SDK run:\n\n"
        f"{content.rstrip()}\n\n"
        "Run-specific kickoff instructions:\n\n"
        f"{request.kickoff_prompt}"
    )
    return instructions, summary


def _skill_context_summary(payload: dict[str, Any]) -> dict[str, Any]:
    return _drop_empty(_to_jsonable(payload))


def _write_skill_context_summary(path: Path, summary: dict[str, Any]) -> None:
    payload = {
        "schema": "openai_agents_skill_context_v1",
        **summary,
    }
    _write_json(path, _drop_empty(payload))


def _sdk_model_settings_payload(request: LiveAgentRequest) -> dict[str, Any]:
    metadata = dict(request.metadata)
    profile = metadata.get("agent_sdk_perf_profile")
    configured = profile.get("sdk_model_settings") if isinstance(profile, dict) else None
    if not isinstance(configured, dict):
        configured = metadata.get("sdk_model_settings")
    if isinstance(configured, dict):
        return _drop_empty(_to_jsonable(configured))
    settings = _safe_model_settings(request)
    provider_profile = str(settings.get("provider_profile") or request.provider_profile or "")
    wire_api = str(settings.get("wire_api") or "")
    profile_id = str(profile.get("profile_id") if isinstance(profile, dict) else "baseline")
    return _default_sdk_model_settings_payload(
        provider_profile=provider_profile,
        wire_api=wire_api,
        profile_id=profile_id,
    )


def _sdk_run_config_payload(
    request: LiveAgentRequest,
    *,
    events_path: Path | None = None,
) -> dict[str, Any]:
    metadata = dict(request.metadata)
    profile = metadata.get("agent_sdk_perf_profile")
    configured = profile.get("sdk_run_config") if isinstance(profile, dict) else None
    if not isinstance(configured, dict):
        configured = metadata.get("sdk_run_config")
    allowed = {"trace_include_sensitive_data", "workflow_name", "trace_metadata"}
    if not isinstance(configured, dict):
        configured = _default_sdk_run_config_payload()
    payload = {
        key: value for key, value in _drop_empty(_to_jsonable(configured)).items() if key in allowed
    }
    filter_config = _input_compaction_config(request)
    if filter_config.get("enabled") and events_path is not None:
        payload["call_model_input_filter"] = _model_input_compaction_filter(
            events_path,
            runtime_config=_runtime_config(
                request,
                mcp_client_session_timeout_configured=_mcp_client_session_timeout_seconds(request)[
                    0
                ],
                mcp_client_session_timeout_s=_mcp_client_session_timeout_seconds(request)[1],
            ),
            config=filter_config,
        )
    return payload


def _default_sdk_model_settings_payload(
    *,
    provider_profile: str,
    wire_api: str,
    profile_id: str,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }
    if wire_api == "chat-completions":
        payload["include_usage"] = True
    else:
        payload.update(
            {
                "truncation": "auto",
                "store": False,
            }
        )
        if provider_profile == "codex-env" and profile_id != "baseline":
            payload["prompt_cache_retention"] = "in_memory"
    return payload


def _default_sdk_run_config_payload() -> dict[str, Any]:
    return {
        "trace_include_sensitive_data": False,
        "workflow_name": "roboclaws-openai-agents-live",
    }


def _input_compaction_config(request: LiveAgentRequest) -> dict[str, Any]:
    metadata = dict(request.metadata)
    profile = metadata.get("agent_sdk_perf_profile")
    config = profile.get("model_input_compaction") if isinstance(profile, dict) else None
    if not isinstance(config, dict):
        config = metadata.get("model_input_compaction")
    if not isinstance(config, dict):
        config = {}
    enabled = _bool_setting(config.get("enabled"), default=False)
    mode = str(config.get("mode") or ("public_tool_result_summary_v1" if enabled else "off"))
    min_chars = _non_negative_int(
        config.get("min_chars"),
        env_name=MODEL_INPUT_COMPACTION_MIN_CHARS_ENV,
        default=DEFAULT_MODEL_INPUT_COMPACTION_MIN_CHARS,
    )
    payload = {
        "schema": "agent_sdk_model_input_compaction_v1",
        "enabled": enabled,
        "mode": mode,
        "min_chars": max(1, min_chars),
        "private_artifact_policy": (
            "filter is model-facing only; MCP traces, reports, and run artifacts remain complete"
        ),
    }
    for nested_key in ("raw_fpv_image_memory", "camera_grounded_history"):
        nested = config.get(nested_key)
        if isinstance(nested, dict):
            payload[nested_key] = nested
    return payload


def _bool_setting(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off"}


def _boolish(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _positive_int(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(1, parsed)


def _model_input_compaction_filter(
    events_path: Path,
    *,
    runtime_config: dict[str, Any],
    config: dict[str, Any],
) -> Any:
    async def _filter(data: Any) -> Any:
        model_data = getattr(data, "model_data", None)
        original_items = getattr(model_data, "input", None)
        instructions = getattr(model_data, "instructions", None)
        if not isinstance(original_items, list):
            return model_data
        filtered_items, metrics = _compact_model_input_items(
            original_items,
            min_chars=int(config.get("min_chars") or DEFAULT_MODEL_INPUT_COMPACTION_MIN_CHARS),
            public_tool_output_summary="public_tool_result_summary_v1"
            in str(config.get("mode") or ""),
            repeated_metric_map_delta="repeated_metric_map_delta_v1"
            in str(config.get("mode") or ""),
            raw_fpv_image_memory=config.get("raw_fpv_image_memory")
            if isinstance(config.get("raw_fpv_image_memory"), dict)
            else None,
            camera_grounded_history=config.get("camera_grounded_history")
            if isinstance(config.get("camera_grounded_history"), dict)
            else None,
        )
        _append_model_input_filter_event(
            events_path,
            runtime_config=runtime_config,
            config=config,
            metrics=metrics,
            input_items=original_items,
        )
        return _model_input_data_like(
            model_data,
            input_items=filtered_items,
            instructions=instructions,
        )

    return _filter


def _model_input_data_like(model_data: Any, *, input_items: list[Any], instructions: Any) -> Any:
    cls = model_data.__class__
    try:
        return cls(input=input_items, instructions=instructions)
    except Exception:
        try:
            from agents.run_config import ModelInputData  # type: ignore[import-not-found]

            return ModelInputData(input=input_items, instructions=instructions)
        except Exception:
            return type(
                "_RoboclawsModelInputData",
                (),
                {"input": input_items, "instructions": instructions},
            )()


def _compact_model_input_items(
    items: list[Any],
    *,
    min_chars: int,
    public_tool_output_summary: bool = True,
    repeated_metric_map_delta: bool = True,
    raw_fpv_image_memory: dict[str, Any] | None = None,
    camera_grounded_history: dict[str, Any] | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    image_policy = _raw_fpv_image_memory_policy(raw_fpv_image_memory)
    image_plan = _raw_fpv_image_memory_plan(items, image_policy)
    image_metrics = _new_raw_fpv_image_memory_metrics(image_policy)
    camera_policy = _camera_grounded_history_policy(camera_grounded_history)
    tool_names_by_call_id = _tool_names_by_call_id(items)
    camera_plan = _camera_grounded_history_plan(
        items,
        camera_policy,
        tool_names_by_call_id=tool_names_by_call_id,
    )
    camera_metrics = _new_camera_grounded_history_metrics(camera_policy)
    filtered: list[Any] = []
    items_seen: dict[str, int] = {}
    metric_map_seen = False
    metric_map_output_count = 0
    repeated_metric_map_output_count = 0
    metric_map_delta_compacted_count = 0
    metric_map_bytes_before = 0
    metric_map_bytes_after = 0
    input_bytes_before = 0
    input_bytes_after = 0
    compacted_count = 0
    for index, item in enumerate(items):
        item_bytes = _json_size_bytes(item)
        input_bytes_before += item_bytes
        image_info = image_plan.get(index)
        if image_info is not None:
            candidate, candidate_kind = _raw_fpv_image_memory_candidate(
                item,
                image_info=image_info,
                policy=image_policy,
                metrics=image_metrics,
            )
        elif (camera_info := camera_plan.get(index)) is not None:
            candidate, candidate_kind = _camera_grounded_history_candidate(
                item,
                camera_info=camera_info,
                policy=camera_policy,
                metrics=camera_metrics,
            )
        else:
            candidate, candidate_kind = _compaction_candidate(
                item,
                min_chars=min_chars,
                metric_map_seen=metric_map_seen,
                public_tool_output_summary=public_tool_output_summary,
                repeated_metric_map_delta=repeated_metric_map_delta,
            )
        if _is_metric_map_tool_output(item):
            metric_map_output_count += 1
            metric_map_bytes_before += item_bytes
            if metric_map_seen:
                repeated_metric_map_output_count += 1
            metric_map_seen = True
        item_hash = _stable_item_hash(item)
        items_seen[item_hash] = items_seen.get(item_hash, 0) + 1
        if candidate is None:
            filtered_item = item
        else:
            filtered_item = candidate
            compacted_count += 1
            if candidate_kind == "repeated_metric_map_delta":
                metric_map_delta_compacted_count += 1
        filtered.append(filtered_item)
        filtered_item_bytes = _json_size_bytes(filtered_item)
        input_bytes_after += filtered_item_bytes
        if _is_metric_map_tool_output(item):
            metric_map_bytes_after += filtered_item_bytes
    return filtered, {
        "schema": "agent_sdk_model_input_compaction_metrics_v1",
        "input_item_count": len(items),
        "compacted_item_count": compacted_count,
        "unchanged_item_count": len(items) - compacted_count,
        "repeated_item_count": sum(count - 1 for count in items_seen.values() if count > 1),
        "input_bytes_before": input_bytes_before,
        "input_bytes_after": input_bytes_after,
        "input_bytes_reduced": max(0, input_bytes_before - input_bytes_after),
        "metric_map_output_count": metric_map_output_count,
        "repeated_metric_map_output_count": repeated_metric_map_output_count,
        "metric_map_delta_compacted_count": metric_map_delta_compacted_count,
        "metric_map_bytes_before": metric_map_bytes_before,
        "metric_map_bytes_after": metric_map_bytes_after,
        "metric_map_bytes_reduced": max(0, metric_map_bytes_before - metric_map_bytes_after),
        **image_metrics,
        **camera_metrics,
    }


def _compaction_candidate(
    item: Any,
    *,
    min_chars: int,
    metric_map_seen: bool,
    public_tool_output_summary: bool,
    repeated_metric_map_delta: bool,
) -> tuple[Any | None, str]:
    payload = _to_jsonable(item)
    if not isinstance(payload, dict):
        return None, ""
    item_type = str(payload.get("type") or "")
    if item_type not in {
        "function_call_output",
        "computer_call_output",
        "mcp_call",
        "mcp_approval_response",
    }:
        return None, ""
    output_key = "output" if "output" in payload else "content" if "content" in payload else ""
    if not output_key:
        return None, ""
    output = payload.get(output_key)
    output_text = output if isinstance(output, str) else json.dumps(output, sort_keys=True)
    if repeated_metric_map_delta and metric_map_seen and _is_metric_map_tool_output(payload):
        compacted = copy.deepcopy(payload)
        summary = json.dumps(
            _repeated_metric_map_delta_summary(output_text, item_type=item_type),
            sort_keys=True,
        )
        if len(summary) < len(output_text):
            compacted[output_key] = summary
            return compacted, "repeated_metric_map_delta"
    if not public_tool_output_summary or len(output_text) < min_chars:
        return None, ""
    compacted = copy.deepcopy(payload)
    compacted[output_key] = json.dumps(
        _public_tool_output_summary(output_text, item_type=item_type),
        sort_keys=True,
    )
    return compacted, "generic_public_tool_output_summary"


def _raw_fpv_image_memory_policy(config: dict[str, Any] | None) -> dict[str, Any]:
    config = config if isinstance(config, dict) else {}
    enabled = _boolish(config.get("enabled"), default=False)
    retained = _positive_int(config.get("retained_full_frame_limit"), default=1)
    if not enabled:
        retained = 0
    return {
        "schema": "agent_sdk_raw_fpv_image_memory_policy_v1",
        "enabled": enabled,
        "mode": str(config.get("mode") or ("retain_latest_full_frame" if enabled else "off")),
        "retained_full_frame_limit": retained,
        "summary_kind": "raw_fpv_evicted_image_frame_summary_v1",
        "candidate_ids": ["AA"] if enabled else [],
        "private_artifact_policy": (
            "model-facing raw-FPV image memory only; MCP traces, reports, and image artifacts "
            "remain complete"
        ),
    }


def _new_raw_fpv_image_memory_metrics(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "raw_fpv_image_memory_enabled": bool(policy.get("enabled")),
        "raw_fpv_image_memory_mode": str(policy.get("mode") or "off"),
        "raw_fpv_image_retained_limit": int(policy.get("retained_full_frame_limit") or 0),
        "raw_fpv_image_item_count": 0,
        "raw_fpv_image_retained_count": 0,
        "raw_fpv_image_evicted_count": 0,
        "raw_fpv_image_bytes_before": 0,
        "raw_fpv_image_bytes_after": 0,
        "raw_fpv_image_bytes_reduced": 0,
    }


def _raw_fpv_image_memory_plan(
    items: list[Any],
    policy: dict[str, Any],
) -> dict[int, dict[str, Any]]:
    if not policy.get("enabled"):
        return {}
    candidates = []
    last_observation_id = ""
    for index, item in enumerate(items):
        item_text = json.dumps(_to_jsonable(item), sort_keys=True)
        matches = RAW_FPV_OBSERVATION_ID_RE.findall(item_text)
        if matches:
            last_observation_id = matches[-1]
        info = _raw_fpv_image_info(item)
        if info is not None:
            if not info.get("observation_id"):
                info["observation_id"] = last_observation_id
            candidates.append((index, info))
    retain_limit = int(policy.get("retained_full_frame_limit") or 0)
    retained = {index for index, _info in candidates[-retain_limit:]} if retain_limit > 0 else set()
    return {
        index: {
            **info,
            "retain_full_frame": index in retained,
        }
        for index, info in candidates
    }


def _raw_fpv_image_info(item: Any) -> dict[str, Any] | None:
    payload = _to_jsonable(item)
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if isinstance(data, (bytes, bytearray)):
        data_len = len(data)
    else:
        data_text = str(data or "")
        data_len = len(data_text.encode("utf-8")) if data_text else 0
    if data_len <= 0:
        return None
    mime = str(payload.get("_mime_type") or payload.get("mime_type") or payload.get("mime") or "")
    fmt = str(payload.get("_format") or payload.get("format") or "")
    if "image" not in mime and fmt.lower() not in {"png", "jpg", "jpeg", "webp"}:
        return None
    material = json.dumps(payload, sort_keys=True).encode("utf-8")
    text = material.decode("utf-8", errors="ignore")
    matches = RAW_FPV_OBSERVATION_ID_RE.findall(text)
    observation_id = matches[-1] if matches else ""
    return {
        "observation_id": observation_id,
        "mime_type": mime or (f"image/{fmt.lower()}" if fmt else "image/unknown"),
        "format": fmt,
        "data_bytes": data_len,
        "item_bytes": len(material),
        "sha256": hashlib.sha256(material).hexdigest(),
    }


def _raw_fpv_image_memory_candidate(
    item: Any,
    *,
    image_info: dict[str, Any],
    policy: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[Any | None, str]:
    metrics["raw_fpv_image_item_count"] += 1
    metrics["raw_fpv_image_bytes_before"] += _json_size_bytes(item)
    if image_info.get("retain_full_frame"):
        metrics["raw_fpv_image_retained_count"] += 1
        metrics["raw_fpv_image_bytes_after"] += _json_size_bytes(item)
        return None, ""
    summary = {
        "schema": "raw_fpv_evicted_image_frame_summary_v1",
        "observation_id": image_info.get("observation_id") or "",
        "mime_type": image_info.get("mime_type") or "",
        "format": image_info.get("format") or "",
        "original_data_bytes": image_info.get("data_bytes") or 0,
        "original_item_bytes": image_info.get("item_bytes") or 0,
        "original_sha256": image_info.get("sha256") or "",
        "retention_policy": {
            "mode": policy.get("mode"),
            "retained_full_frame_limit": policy.get("retained_full_frame_limit"),
        },
        "summary": (
            "Older raw-FPV image frame compacted before this SDK model call. "
            "Use the latest retained frame and current raw-FPV MCP tools for visual work; "
            "Roboclaws trace/report artifacts retain complete image evidence."
        ),
        "private_artifact_policy": policy.get("private_artifact_policy"),
    }
    if _json_size_bytes(summary) >= _json_size_bytes(item):
        metrics["raw_fpv_image_retained_count"] += 1
        metrics["raw_fpv_image_bytes_after"] += _json_size_bytes(item)
        return None, ""
    metrics["raw_fpv_image_evicted_count"] += 1
    metrics["raw_fpv_image_bytes_after"] += _json_size_bytes(summary)
    metrics["raw_fpv_image_bytes_reduced"] = max(
        0,
        metrics["raw_fpv_image_bytes_before"] - metrics["raw_fpv_image_bytes_after"],
    )
    return summary, "raw_fpv_image_memory"


def _camera_grounded_history_policy(config: dict[str, Any] | None) -> dict[str, Any]:
    config = config if isinstance(config, dict) else {}
    enabled = _boolish(config.get("enabled"), default=False)
    retained = _positive_int(config.get("retained_recent_outputs"), default=4)
    if not enabled:
        retained = 0
    return {
        "schema": "agent_sdk_camera_grounded_history_policy_v1",
        "enabled": enabled,
        "mode": str(
            config.get("mode") or ("retain_latest_actionable_outputs" if enabled else "off")
        ),
        "retained_recent_outputs": retained,
        "summary_kind": "roboclaws_camera_grounded_history_summary_v1",
        "candidate_ids": ["AC"] if enabled else [],
        "private_artifact_policy": (
            "model-facing camera-grounded history compaction only; MCP traces, reports, "
            "and run artifacts remain complete"
        ),
    }


def _new_camera_grounded_history_metrics(policy: dict[str, Any]) -> dict[str, Any]:
    return {
        "camera_grounded_history_enabled": bool(policy.get("enabled")),
        "camera_grounded_history_mode": str(policy.get("mode") or "off"),
        "camera_grounded_history_retained_limit": int(policy.get("retained_recent_outputs") or 0),
        "camera_grounded_history_item_count": 0,
        "camera_grounded_history_retained_count": 0,
        "camera_grounded_history_compacted_count": 0,
        "camera_grounded_history_bytes_before": 0,
        "camera_grounded_history_bytes_after": 0,
        "camera_grounded_history_bytes_reduced": 0,
    }


def _camera_grounded_history_plan(
    items: list[Any],
    policy: dict[str, Any],
    *,
    tool_names_by_call_id: dict[str, str] | None = None,
) -> dict[int, dict[str, Any]]:
    if not policy.get("enabled"):
        return {}
    tool_names_by_call_id = tool_names_by_call_id or {}
    candidates = [
        (index, info)
        for index, item in enumerate(items)
        if (
            info := _camera_grounded_history_info(
                item,
                tool_names_by_call_id=tool_names_by_call_id,
            )
        )
        is not None
    ]
    retain_limit = int(policy.get("retained_recent_outputs") or 0)
    retained = {index for index, _info in candidates[-retain_limit:]} if retain_limit > 0 else set()
    return {
        index: {
            **info,
            "retain_full_output": index in retained,
        }
        for index, info in candidates
    }


def _tool_names_by_call_id(items: list[Any]) -> dict[str, str]:
    names: dict[str, str] = {}
    for item in items:
        payload = _to_jsonable(item)
        if not isinstance(payload, dict):
            continue
        item_type = str(payload.get("type") or "")
        if item_type not in {"function_call", "mcp_call"}:
            continue
        call_id = str(payload.get("call_id") or "")
        if not call_id:
            continue
        tool = _normalize_mcp_tool_name(
            payload.get("name") or payload.get("tool") or payload.get("tool_name") or ""
        )
        if tool:
            names[call_id] = tool
    return names


def _camera_grounded_history_info(
    item: Any,
    *,
    tool_names_by_call_id: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    payload = _to_jsonable(item)
    if not isinstance(payload, dict):
        return None
    item_type = str(payload.get("type") or "")
    if item_type not in {
        "function_call_output",
        "computer_call_output",
        "mcp_call",
        "mcp_approval_response",
    }:
        return None
    call_id = str(payload.get("call_id") or "")
    tool = _normalize_mcp_tool_name(
        (tool_names_by_call_id or {}).get(call_id)
        or payload.get("name")
        or payload.get("tool")
        or payload.get("tool_name")
        or ""
    )
    if not tool and "observe_camera_grounded_candidates" in call_id:
        tool = "observe_camera_grounded_candidates"
    if not tool and "declare_visual_candidates" in call_id:
        tool = "declare_visual_candidates"
    if not tool and "observe" in call_id:
        tool = "observe"
    output = payload.get("output") if "output" in payload else payload.get("content")
    if output is None:
        return None
    decoded = _decode_tool_output_payload(output)
    decoded = decoded if isinstance(decoded, dict) else {}
    if not tool:
        tool = _normalize_mcp_tool_name(decoded.get("tool") or "")
    if tool not in {
        "observe_camera_grounded_candidates",
        "declare_visual_candidates",
        "observe",
    }:
        return None
    if tool == "observe" and str(decoded.get("perception_mode") or "") != "camera_model_policy":
        return None
    if tool == "declare_visual_candidates" and not (
        "camera_model_candidates" in decoded
        or "model_declared_observations" in decoded
        or "visual_grounding_pipeline" in decoded
    ):
        return None
    output_text = output if isinstance(output, str) else json.dumps(output, sort_keys=True)
    raw_fpv_observation = decoded.get("raw_fpv_observation")
    raw_fpv_observation = raw_fpv_observation if isinstance(raw_fpv_observation, dict) else {}
    return {
        "item_type": item_type,
        "tool": tool,
        "output_key": "output" if "output" in payload else "content",
        "output_text": output_text,
        "observation_id": str(
            decoded.get("observation_id") or raw_fpv_observation.get("observation_id") or ""
        ),
        "waypoint_id": str(decoded.get("waypoint_id") or ""),
        "room_id": str(decoded.get("room_id") or decoded.get("current_room_id") or ""),
        "status": str(decoded.get("status") or ""),
        "ok": bool(decoded.get("ok", False)),
        "candidate_count": _camera_grounded_candidate_count(decoded),
        "actionable_candidate_count": _camera_grounded_actionable_candidate_count(decoded),
        "candidate_refs": _camera_grounded_candidate_refs(decoded),
    }


def _normalize_mcp_tool_name(value: Any) -> str:
    tool = str(value or "").strip()
    if "__" in tool:
        tool = tool.rsplit("__", 1)[-1]
    return tool


def _camera_grounded_candidate_count(decoded: dict[str, Any]) -> int:
    for key in ("camera_model_candidates", "model_declared_observations"):
        value = decoded.get(key)
        if isinstance(value, list):
            return len(value)
    declaration = decoded.get("declaration")
    if isinstance(declaration, dict):
        return _camera_grounded_candidate_count(declaration)
    return 0


def _camera_grounded_actionable_candidate_count(decoded: dict[str, Any]) -> int:
    candidates = _camera_grounded_candidates(decoded)
    return sum(
        1
        for candidate in candidates
        if isinstance(candidate, dict)
        and (
            candidate.get("cleanup_recommended") is True
            or str(candidate.get("actionability_status") or "") == "actionable"
            or (
                isinstance(candidate.get("visual_grounding_evidence"), dict)
                and str(candidate["visual_grounding_evidence"].get("candidate_state") or "")
                == "navigation_authorized"
            )
        )
    )


def _camera_grounded_candidates(decoded: dict[str, Any]) -> list[Any]:
    for key in ("camera_model_candidates", "model_declared_observations"):
        value = decoded.get(key)
        if isinstance(value, list):
            return value
    declaration = decoded.get("declaration")
    if isinstance(declaration, dict):
        return _camera_grounded_candidates(declaration)
    return []


def _camera_grounded_candidate_refs(decoded: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for candidate in _camera_grounded_candidates(decoded)[:8]:
        if not isinstance(candidate, dict):
            continue
        evidence = candidate.get("visual_grounding_evidence")
        evidence = evidence if isinstance(evidence, dict) else {}
        refs.append(
            _drop_empty(
                {
                    "object_id": candidate.get("object_id"),
                    "category": candidate.get("category"),
                    "recommended_tool": candidate.get("recommended_tool"),
                    "source_observation_id": candidate.get("source_observation_id")
                    or evidence.get("source_observation_id"),
                    "waypoint_id": candidate.get("waypoint_id"),
                    "room_id": candidate.get("room_id") or candidate.get("current_room_id"),
                    "cleanup_recommended": candidate.get("cleanup_recommended"),
                    "actionability_status": candidate.get("actionability_status"),
                    "candidate_state": evidence.get("candidate_state"),
                }
            )
        )
    return refs


def _camera_grounded_history_candidate(
    item: Any,
    *,
    camera_info: dict[str, Any],
    policy: dict[str, Any],
    metrics: dict[str, Any],
) -> tuple[Any | None, str]:
    original_bytes = _json_size_bytes(item)
    metrics["camera_grounded_history_item_count"] += 1
    metrics["camera_grounded_history_bytes_before"] += original_bytes
    if camera_info.get("retain_full_output"):
        metrics["camera_grounded_history_retained_count"] += 1
        metrics["camera_grounded_history_bytes_after"] += original_bytes
        return None, ""
    output_text = str(camera_info.get("output_text") or "")
    summary = {
        "schema": "roboclaws_camera_grounded_history_summary_v1",
        "item_type": camera_info.get("item_type") or "",
        "tool": camera_info.get("tool") or "",
        "original_chars": len(output_text),
        "original_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "observation_id": camera_info.get("observation_id") or "",
        "waypoint_id": camera_info.get("waypoint_id") or "",
        "room_id": camera_info.get("room_id") or "",
        "status": camera_info.get("status") or "",
        "ok": bool(camera_info.get("ok")),
        "candidate_count": camera_info.get("candidate_count") or 0,
        "actionable_candidate_count": camera_info.get("actionable_candidate_count") or 0,
        "candidate_refs": camera_info.get("candidate_refs") or [],
        "retention_policy": {
            "mode": policy.get("mode"),
            "retained_recent_outputs": policy.get("retained_recent_outputs"),
        },
        "summary": (
            "Older camera-grounded observation/declaration output compacted before this SDK "
            "model call. Use the latest retained camera-grounded outputs and current MCP "
            "tools for actionable state; Roboclaws trace/report artifacts retain complete "
            "tool responses."
        ),
        "private_artifact_policy": policy.get("private_artifact_policy"),
    }
    if _json_size_bytes(summary) >= original_bytes:
        metrics["camera_grounded_history_retained_count"] += 1
        metrics["camera_grounded_history_bytes_after"] += original_bytes
        return None, ""
    compacted = copy.deepcopy(_to_jsonable(item))
    compacted[str(camera_info.get("output_key") or "output")] = json.dumps(
        _drop_empty(summary),
        sort_keys=True,
    )
    compacted_bytes = _json_size_bytes(compacted)
    metrics["camera_grounded_history_compacted_count"] += 1
    metrics["camera_grounded_history_bytes_after"] += compacted_bytes
    metrics["camera_grounded_history_bytes_reduced"] = max(
        0,
        metrics["camera_grounded_history_bytes_before"]
        - metrics["camera_grounded_history_bytes_after"],
    )
    return compacted, "camera_grounded_history"


def _is_metric_map_tool_output(item: Any) -> bool:
    payload = _to_jsonable(item)
    if not isinstance(payload, dict):
        return False
    for key in ("name", "tool", "tool_name"):
        if str(payload.get(key) or "") == "metric_map":
            return True
    call_id = str(payload.get("call_id") or "")
    if "metric_map" in call_id:
        return True
    output = payload.get("output") if "output" in payload else payload.get("content")
    decoded = _decode_tool_output_payload(output)
    if isinstance(decoded, dict):
        if decoded.get("tool") == "metric_map":
            return True
        nested = decoded.get("metric_map")
        return isinstance(nested, dict) and nested.get("tool") == "metric_map"
    return False


def _decode_tool_output_payload(output: Any) -> Any:
    if isinstance(output, str):
        try:
            decoded = json.loads(output)
        except json.JSONDecodeError:
            return None
        if isinstance(decoded, str):
            try:
                return _unwrap_mcp_text_content_payload(json.loads(decoded))
            except json.JSONDecodeError:
                return decoded
        return _unwrap_mcp_text_content_payload(decoded)
    return _unwrap_mcp_text_content_payload(output)


def _unwrap_mcp_text_content_payload(decoded: Any) -> Any:
    if isinstance(decoded, dict):
        content = decoded.get("content")
        if isinstance(content, list):
            unwrapped = _unwrap_mcp_text_content_payload(content)
            if unwrapped is not content:
                return unwrapped
        text = decoded.get("text")
        if isinstance(text, str) and str(decoded.get("type") or "") in {"", "text"}:
            try:
                return _unwrap_mcp_text_content_payload(json.loads(text))
            except json.JSONDecodeError:
                return decoded
        return decoded
    if isinstance(decoded, list):
        for item in decoded:
            if not isinstance(item, dict):
                continue
            if str(item.get("type") or "") not in {"", "text"}:
                continue
            text = item.get("text")
            if not isinstance(text, str):
                continue
            try:
                return _unwrap_mcp_text_content_payload(json.loads(text))
            except json.JSONDecodeError:
                continue
        return decoded
    return decoded


def _repeated_metric_map_delta_summary(output_text: str, *, item_type: str) -> dict[str, Any]:
    decoded = _decode_tool_output_payload(output_text)
    metric_map = decoded.get("metric_map") if isinstance(decoded, dict) else None
    if not isinstance(metric_map, dict) and isinstance(decoded, dict):
        metric_map = decoded
    metric_map = metric_map if isinstance(metric_map, dict) else {}
    runtime_map = (
        metric_map.get("runtime_metric_map")
        if isinstance(metric_map.get("runtime_metric_map"), dict)
        else {}
    )
    return {
        "schema": "roboclaws_repeated_metric_map_delta_summary_v1",
        "item_type": item_type,
        "original_chars": len(output_text),
        "original_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "map_id": str(metric_map.get("map_id") or ""),
        "map_version": str(metric_map.get("map_version") or ""),
        "mode": str(metric_map.get("mode") or ""),
        "inspection_waypoint_count": len(metric_map.get("inspection_waypoints") or []),
        "generated_target_candidate_count": len(
            metric_map.get("generated_target_inspection_candidates") or []
        ),
        "runtime_observed_object_count": len(runtime_map.get("observed_objects") or []),
        "runtime_target_candidate_count": len(runtime_map.get("target_candidates") or []),
        "summary": (
            "Repeated metric_map output compacted before this SDK model call. "
            "Use the current metric_map tool again when full map fields are needed; "
            "Roboclaws trace/report artifacts retain complete tool responses."
        ),
        "private_artifact_policy": (
            "model-facing repeated-map delta only; raw map body is not persisted in "
            "OpenAI Agents SDK events"
        ),
    }


def _public_tool_output_summary(output_text: str, *, item_type: str) -> dict[str, Any]:
    return {
        "schema": "roboclaws_public_tool_output_summary_v1",
        "item_type": item_type,
        "original_chars": len(output_text),
        "original_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
        "summary": (
            "Oversized public tool output compacted before this SDK model call. "
            "Use current MCP tools for fresh state; full tool responses remain in "
            "Roboclaws trace/report artifacts."
        ),
    }


def _append_model_input_filter_event(
    events_path: Path,
    *,
    runtime_config: dict[str, Any],
    config: dict[str, Any],
    metrics: dict[str, Any],
    input_items: list[Any] | None = None,
) -> None:
    _append_event(
        events_path,
        _drop_empty(
            {
                "schema": "openai_agents_model_input_filter_v1",
                "event": "model_input_filter",
                "ts_epoch": time.time(),
                "runtime": runtime_config.get("runtime"),
                "provider_profile": runtime_config.get("provider_profile"),
                "wire_api": runtime_config.get("wire_api"),
                "model": runtime_config.get("model"),
                "config": _drop_empty(_to_jsonable(config)),
                "metrics": _drop_empty(_to_jsonable(metrics)),
                "input_shape_summary": _model_input_shape_summary(input_items or []),
                "privacy_note": (
                    "Only aggregate counts, byte sizes, hashes, and policy metadata are persisted. "
                    "Raw prompts, model text, tool payload bodies, credentials, and private truth "
                    "are not stored by this event."
                ),
            }
        ),
    )


def _model_input_shape_summary(items: list[Any]) -> dict[str, Any]:
    type_counts: dict[str, int] = {}
    key_set_counts: dict[str, int] = {}
    tool_field_counts: dict[str, int] = {}
    output_field_counts: dict[str, int] = {}
    role_counts: dict[str, int] = {}
    for item in items:
        payload = _to_jsonable(item)
        if not isinstance(payload, dict):
            item_type = type(payload).__name__
            type_counts[item_type] = type_counts.get(item_type, 0) + 1
            continue
        item_type = str(payload.get("type") or "<missing>")
        type_counts[item_type] = type_counts.get(item_type, 0) + 1
        key_set = ",".join(sorted(str(key) for key in payload.keys()))
        key_set_counts[key_set] = key_set_counts.get(key_set, 0) + 1
        role = str(payload.get("role") or "")
        if role:
            role_counts[role] = role_counts.get(role, 0) + 1
        for key in ("name", "tool", "tool_name", "call_id", "id"):
            if key in payload:
                tool_field_counts[key] = tool_field_counts.get(key, 0) + 1
        for key in ("output", "content", "result", "error"):
            if key in payload:
                output_field_counts[key] = output_field_counts.get(key, 0) + 1
    return {
        "schema": "openai_agents_model_input_shape_summary_v1",
        "input_item_count": len(items),
        "type_counts": dict(sorted(type_counts.items())),
        "key_set_counts": dict(sorted(key_set_counts.items())),
        "tool_field_counts": dict(sorted(tool_field_counts.items())),
        "output_field_counts": dict(sorted(output_field_counts.items())),
        "role_counts": dict(sorted(role_counts.items())),
        "privacy_note": (
            "Aggregate model-input item shape only. Values, prompts, model text, tool output "
            "bodies, credentials, and private truth are not persisted."
        ),
    }


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
    model_settings = _safe_model_settings(request)
    sdk_model_settings = _sdk_model_settings_payload(request)
    sdk_run_config = _sdk_run_config_payload(request, events_path=None)
    input_compaction = _input_compaction_config(request)
    racing_observability = _model_racing_observability_config(request)
    responses_feature_surface = _responses_feature_surface(model_settings)
    return {
        "runtime": "openai-agents-live",
        "provider_profile": model_settings.get("provider_profile") or request.provider_profile,
        "model": model_settings.get("model") or request.model,
        "wire_api": model_settings.get("wire_api") or "",
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
        "sdk_model_settings": sdk_model_settings,
        "sdk_run_config": sdk_run_config,
        "agent_sdk_responses_features": responses_feature_surface,
        "model_input_compaction": input_compaction,
        "model_racing_observability": racing_observability,
        "prompt_cache_retention": sdk_model_settings.get("prompt_cache_retention") or "",
        "trace_include_sensitive_data": sdk_run_config.get("trace_include_sensitive_data"),
    }


def _responses_feature_surface(model_settings: dict[str, Any]) -> dict[str, Any]:
    wire_api = str(model_settings.get("wire_api") or "")
    enabled = wire_api == "responses"
    return {
        "schema": "agent_sdk_responses_feature_surface_v1",
        "wire_api": wire_api,
        "available": enabled,
        "previous_response_id": enabled,
        "auto_previous_response_id": enabled,
        "conversation_id": enabled,
        "session": enabled,
        "server_managed_continuation_default": False,
        "decision": (
            "available_but_gated_for_live_ab"
            if enabled
            else "unavailable_for_chat_completions_wire_api"
        ),
        "privacy_note": (
            "Responses continuation/session levers are recorded as capability surface only; "
            "they are not enabled by default because task state and report completeness must "
            "remain MCP-visible."
        ),
    }


def _model_racing_observability_config(request: LiveAgentRequest) -> dict[str, Any]:
    metadata = dict(request.metadata)
    profile = metadata.get("agent_sdk_perf_profile")
    config = profile.get("model_racing_observability") if isinstance(profile, dict) else None
    if not isinstance(config, dict):
        config = metadata.get("model_racing_observability")
    if not isinstance(config, dict):
        config = {}
    enabled = _bool_setting(config.get("enabled"), default=False)
    arm_count = _positive_int(config.get("arm_count"), default=1)
    if not enabled:
        arm_count = 1
    else:
        arm_count = max(2, arm_count)
    configured_multiplier = float(config.get("racing_multiplier") or arm_count)
    racing_multiplier = max(float(arm_count), configured_multiplier) if enabled else 1.0
    racing_mode = str(
        config.get("mode") or ("get_response_racing_v1" if enabled else "per_arm_observability_v1")
    )
    candidate_ids = (
        config.get("candidate_ids") if isinstance(config.get("candidate_ids"), list) else []
    )
    return {
        "schema": MODEL_RACING_OBSERVABILITY_SCHEMA,
        "enabled": enabled,
        "mode": racing_mode,
        "candidate_ids": [str(item) for item in candidate_ids],
        "arm_count": arm_count,
        "racing_multiplier": racing_multiplier,
        "winner_selection": str(
            config.get("winner_selection")
            or ("first_successful_sdk_response" if enabled else "single_arm_no_racing")
        ),
        "loser_cancellation": str(
            config.get("loser_cancellation")
            or ("cancel_pending_losers" if enabled else "not_applicable_until_racing_enabled")
        ),
        "unknown_loser_billing": True
        if enabled
        else bool(config.get("unknown_loser_billing", False)),
        "private_artifact_policy": (
            "records model-call arm lifecycle, winner/cancel fields, timing, provider/model ids, "
            "and usage availability only; raw prompts, model text, tool payload bodies, "
            "credentials, and private truth are not persisted"
        ),
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
    final_output = getattr(result, "final_output", None)
    if final_output is not None:
        final_output_text = str(final_output)
        payload["final_output_present"] = True
        payload["final_output_chars"] = len(final_output_text)
        payload["message"] = (
            "OpenAI Agents SDK result captured; assistant output redacted by "
            "artifact privacy policy."
        )
    last_agent = getattr(result, "last_agent", None)
    if last_agent is not None:
        name = getattr(last_agent, "name", None)
        if name:
            payload["last_agent_name"] = str(name)
        payload["last_agent_class"] = last_agent.__class__.__name__
    trace_id = getattr(result, "trace_id", None)
    if trace_id is not None:
        payload["trace_id"] = str(trace_id)
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


def _model_for_request(request: LiveAgentRequest) -> Any:
    from openai import AsyncOpenAI  # type: ignore[import-not-found]

    settings = _model_settings(request)
    client = AsyncOpenAI(
        api_key=settings["api_key"],
        base_url=settings["base_url"],
    )
    if settings["wire_api"] == "responses":
        from agents import OpenAIResponsesModel  # type: ignore[import-not-found]

        base_model = OpenAIResponsesModel(settings["model"], openai_client=client)
    elif settings["wire_api"] == "chat-completions":
        from agents import OpenAIChatCompletionsModel  # type: ignore[import-not-found]

        base_model = OpenAIChatCompletionsModel(settings["model"], openai_client=client)
    else:  # pragma: no cover - guarded by _model_settings.
        raise RuntimeError(f"unsupported OpenAI Agents wire API: {settings['wire_api']}")
    retry_config = _model_service_retry_config(request)
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


def _safe_model_settings(request: LiveAgentRequest) -> dict[str, str]:
    try:
        return _model_settings(request)
    except Exception:
        return {}


@dataclass(frozen=True)
class _ModelRacingArmOutcome:
    arm_index: int
    arm_id: str
    elapsed_s: float
    result: Any = None
    exc: Exception | None = None


class _RetryingModel(_AgentsModel):
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
        self._model_call_index = 0

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
            call_index = self._next_model_call_index()
            racing_enabled = self._get_response_racing_enabled()
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
                if racing_enabled:
                    result = await self._race_get_response(
                        call_index=call_index,
                        attempt_index=attempt_index,
                        system_instructions=system_instructions,
                        input=input,
                        model_settings=model_settings,
                        tools=tools,
                        output_schema=output_schema,
                        handoffs=handoffs,
                        tracing=tracing,
                        previous_response_id=previous_response_id,
                        conversation_id=conversation_id,
                        prompt=prompt,
                    )
                else:
                    arm_id = _model_racing_arm_id(
                        call_index=call_index,
                        attempt_index=attempt_index,
                        arm_index=0,
                    )
                    _append_model_racing_event(
                        self.events_path,
                        self.spans_path,
                        "model_racing_arm_start",
                        runtime_config=self.runtime_config,
                        call_index=call_index,
                        attempt_index=attempt_index,
                        arm_id=arm_id,
                        arm_index=0,
                        method="get_response",
                        arm_role="single",
                    )
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
                if not racing_enabled:
                    _append_model_racing_event(
                        self.events_path,
                        self.spans_path,
                        "model_racing_arm_failure",
                        runtime_config=self.runtime_config,
                        call_index=call_index,
                        attempt_index=attempt_index,
                        arm_id=_model_racing_arm_id(
                            call_index=call_index,
                            attempt_index=attempt_index,
                            arm_index=0,
                        ),
                        arm_index=0,
                        method="get_response",
                        arm_role="single",
                        elapsed_s=_round_duration(time.time() - started),
                        final_outcome="retry_scheduled" if should_retry else "failure",
                        failure_class=failure.reason,
                        provider_reason=failure.provider_reason,
                        retryable=failure.retryable,
                        winner=False,
                        cancelled=False,
                        cancellation_observed=False,
                        loser_billing_unknown=False,
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
            if not racing_enabled:
                _append_model_racing_event(
                    self.events_path,
                    self.spans_path,
                    "model_racing_arm_finish",
                    runtime_config=self.runtime_config,
                    call_index=call_index,
                    attempt_index=attempt_index,
                    arm_id=_model_racing_arm_id(
                        call_index=call_index,
                        attempt_index=attempt_index,
                        arm_index=0,
                    ),
                    arm_index=0,
                    method="get_response",
                    arm_role="single",
                    elapsed_s=_round_duration(time.time() - started),
                    final_outcome="success",
                    winner=True,
                    cancelled=False,
                    cancellation_observed=False,
                    loser_billing_unknown=False,
                    usage_summary=_usage_summary(result),
                )
            return result

    def _get_response_racing_enabled(self) -> bool:
        config = (
            self.runtime_config.get("model_racing_observability")
            if isinstance(self.runtime_config.get("model_racing_observability"), dict)
            else {}
        )
        return bool(config.get("enabled")) and self._racing_arm_count() > 1

    def _racing_arm_count(self) -> int:
        config = (
            self.runtime_config.get("model_racing_observability")
            if isinstance(self.runtime_config.get("model_racing_observability"), dict)
            else {}
        )
        return _positive_int(config.get("arm_count"), default=1)

    async def _race_get_response(
        self,
        *,
        call_index: int,
        attempt_index: int,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any,
    ) -> Any:
        tasks = [
            asyncio.create_task(
                self._get_response_racing_arm(
                    arm_index=arm_index,
                    call_index=call_index,
                    attempt_index=attempt_index,
                    system_instructions=system_instructions,
                    input=input,
                    model_settings=model_settings,
                    tools=tools,
                    output_schema=output_schema,
                    handoffs=handoffs,
                    tracing=tracing,
                    previous_response_id=previous_response_id,
                    conversation_id=conversation_id,
                    prompt=prompt,
                )
            )
            for arm_index in range(self._racing_arm_count())
        ]
        pending = set(tasks)
        failures: list[_ModelRacingArmOutcome] = []
        try:
            while pending:
                done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)
                successful = [
                    outcome for task in done for outcome in [task.result()] if outcome.exc is None
                ]
                failures.extend(
                    outcome
                    for task in done
                    for outcome in [task.result()]
                    if outcome.exc is not None
                )
                if not successful:
                    continue

                winner = min(successful, key=lambda outcome: outcome.arm_index)
                for outcome in successful:
                    _append_model_racing_event(
                        self.events_path,
                        self.spans_path,
                        "model_racing_arm_finish",
                        runtime_config=self.runtime_config,
                        call_index=call_index,
                        attempt_index=attempt_index,
                        arm_id=outcome.arm_id,
                        arm_index=outcome.arm_index,
                        method="get_response",
                        arm_role="winner" if outcome is winner else "loser",
                        elapsed_s=outcome.elapsed_s,
                        final_outcome="success" if outcome is winner else "success_loser",
                        winner=outcome is winner,
                        cancelled=False,
                        cancellation_observed=False,
                        loser_billing_unknown=outcome is not winner,
                        usage_summary=_usage_summary(outcome.result),
                    )
                for task in pending:
                    task.cancel()
                if pending:
                    await asyncio.gather(*pending, return_exceptions=True)
                return winner.result
            if failures and failures[-1].exc is not None:
                raise failures[-1].exc
            raise RuntimeError("model racing completed without a winning arm")
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            if any(not task.done() for task in tasks):
                await asyncio.gather(*tasks, return_exceptions=True)

    async def _get_response_racing_arm(
        self,
        *,
        arm_index: int,
        call_index: int,
        attempt_index: int,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: Any,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any,
    ) -> "_ModelRacingArmOutcome":
        started = time.time()
        arm_id = _model_racing_arm_id(
            call_index=call_index,
            attempt_index=attempt_index,
            arm_index=arm_index,
        )
        _append_model_racing_event(
            self.events_path,
            self.spans_path,
            "model_racing_arm_start",
            runtime_config=self.runtime_config,
            call_index=call_index,
            attempt_index=attempt_index,
            arm_id=arm_id,
            arm_index=arm_index,
            method="get_response",
            arm_role="candidate",
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
        except asyncio.CancelledError:
            _append_model_racing_event(
                self.events_path,
                self.spans_path,
                "model_racing_arm_cancelled",
                runtime_config=self.runtime_config,
                call_index=call_index,
                attempt_index=attempt_index,
                arm_id=arm_id,
                arm_index=arm_index,
                method="get_response",
                arm_role="loser",
                elapsed_s=_round_duration(time.time() - started),
                final_outcome="cancelled",
                winner=False,
                cancelled=True,
                cancellation_observed=True,
                loser_billing_unknown=True,
            )
            raise
        except Exception as exc:
            failure = _failure_from_exception(exc)
            _append_model_racing_event(
                self.events_path,
                self.spans_path,
                "model_racing_arm_failure",
                runtime_config=self.runtime_config,
                call_index=call_index,
                attempt_index=attempt_index,
                arm_id=arm_id,
                arm_index=arm_index,
                method="get_response",
                arm_role="candidate",
                elapsed_s=_round_duration(time.time() - started),
                final_outcome="failure",
                failure_class=failure.reason,
                provider_reason=failure.provider_reason,
                retryable=failure.retryable,
                winner=False,
                cancelled=False,
                cancellation_observed=False,
                loser_billing_unknown=False,
                safe_to_replay=True,
            )
            return _ModelRacingArmOutcome(
                arm_index=arm_index,
                arm_id=arm_id,
                elapsed_s=_round_duration(time.time() - started),
                exc=exc,
            )
        return _ModelRacingArmOutcome(
            arm_index=arm_index,
            arm_id=arm_id,
            elapsed_s=_round_duration(time.time() - started),
            result=result,
        )

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
            call_index = self._next_model_call_index()
            arm_id = _model_racing_arm_id(call_index=call_index, attempt_index=attempt_index)
            _append_model_racing_event(
                self.events_path,
                self.spans_path,
                "model_racing_arm_start",
                runtime_config=self.runtime_config,
                call_index=call_index,
                attempt_index=attempt_index,
                arm_id=arm_id,
                method="stream_response",
                arm_role="single",
                arm_count=1,
                racing_enabled=False,
                racing_mode="stream_response_single_arm_no_racing",
                racing_multiplier=1.0,
                winner_selection="stream_response_single_arm_no_racing",
                loser_cancellation="not_applicable_stream_response",
            )
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
                _append_model_racing_event(
                    self.events_path,
                    self.spans_path,
                    "model_racing_arm_failure",
                    runtime_config=self.runtime_config,
                    call_index=call_index,
                    attempt_index=attempt_index,
                    arm_id=arm_id,
                    method="stream_response",
                    arm_role="single",
                    arm_count=1,
                    racing_enabled=False,
                    racing_mode="stream_response_single_arm_no_racing",
                    racing_multiplier=1.0,
                    winner_selection="stream_response_single_arm_no_racing",
                    loser_cancellation="not_applicable_stream_response",
                    elapsed_s=_round_duration(time.time() - started),
                    final_outcome="retry_scheduled" if should_retry else "failure",
                    failure_class=failure.reason,
                    provider_reason=failure.provider_reason,
                    retryable=failure.retryable,
                    winner=False,
                    cancelled=False,
                    cancellation_observed=False,
                    loser_billing_unknown=False,
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
            _append_model_racing_event(
                self.events_path,
                self.spans_path,
                "model_racing_arm_finish",
                runtime_config=self.runtime_config,
                call_index=call_index,
                attempt_index=attempt_index,
                arm_id=arm_id,
                method="stream_response",
                arm_role="single",
                arm_count=1,
                racing_enabled=False,
                racing_mode="stream_response_single_arm_no_racing",
                racing_multiplier=1.0,
                winner_selection="stream_response_single_arm_no_racing",
                loser_cancellation="not_applicable_stream_response",
                elapsed_s=_round_duration(time.time() - started),
                final_outcome="success",
                winner=True,
                cancelled=False,
                cancellation_observed=False,
                loser_billing_unknown=False,
            )
            return

    def _next_model_call_index(self) -> int:
        value = self._model_call_index
        self._model_call_index += 1
        return value


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
            "wire_api": runtime_config.get("wire_api"),
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


def _model_racing_arm_id(
    *,
    call_index: int,
    attempt_index: int,
    arm_index: int = 0,
) -> str:
    return f"call-{call_index}-attempt-{attempt_index}-arm-{arm_index}"


def _append_model_racing_event(
    events_path: Path,
    spans_path: Path,
    event: str,
    *,
    runtime_config: dict[str, Any],
    call_index: int,
    attempt_index: int,
    arm_id: str,
    method: str,
    arm_role: str,
    arm_index: int = 0,
    **extra: Any,
) -> None:
    config = (
        runtime_config.get("model_racing_observability")
        if isinstance(runtime_config.get("model_racing_observability"), dict)
        else {}
    )
    payload = _drop_empty(
        {
            "schema": MODEL_RACING_EVENT_SCHEMA,
            "event": event,
            "ts_epoch": time.time(),
            "runtime": runtime_config.get("runtime"),
            "provider_profile": runtime_config.get("provider_profile"),
            "wire_api": runtime_config.get("wire_api"),
            "model": runtime_config.get("model"),
            "call_index": call_index,
            "attempt_index": attempt_index,
            "arm_id": arm_id,
            "arm_index": arm_index,
            "arm_count": config.get("arm_count", 1),
            "arm_role": arm_role,
            "method": method,
            "racing_enabled": bool(config.get("enabled")),
            "racing_mode": config.get("mode") or "off",
            "racing_multiplier": config.get("racing_multiplier", 1.0),
            "winner_selection": config.get("winner_selection") or "single_arm_no_racing",
            "loser_cancellation": config.get("loser_cancellation")
            or "not_applicable_until_racing_enabled",
            **extra,
        }
    )
    _append_event(events_path, payload)
    span_payload = {
        **payload,
        "schema": "openai_agents_sanitized_span_v1",
        "span_type": "model_racing_observability",
    }
    _append_event(spans_path, span_payload)


def _usage_summary(result: Any) -> dict[str, Any]:
    raw_usage = getattr(result, "usage", None)
    usage = _to_jsonable(raw_usage) if raw_usage is not None else {}
    if not isinstance(usage, dict) or not usage:
        return {"usage_available": False}
    input_tokens = _int_from_any(usage.get("input_tokens"))
    cached_tokens = _cached_input_tokens_from_usage(usage)
    output_tokens = _int_from_any(usage.get("output_tokens"))
    reasoning_tokens = _reasoning_tokens_from_usage(usage)
    payload: dict[str, Any] = {
        "usage_available": True,
        "input_tokens": input_tokens,
        "cached_input_tokens": cached_tokens,
        "output_tokens": output_tokens,
        "reasoning_tokens": reasoning_tokens,
    }
    if input_tokens is not None and cached_tokens is not None:
        payload["uncached_input_tokens"] = max(0, input_tokens - cached_tokens)
    return _drop_empty(payload)


def _cached_input_tokens_from_usage(usage: dict[str, Any]) -> int | None:
    details = usage.get("input_tokens_details")
    if isinstance(details, dict):
        cached = _int_from_any(details.get("cached_tokens"))
        if cached is not None:
            return cached
    return _int_from_any(usage.get("cached_input_tokens"))


def _reasoning_tokens_from_usage(usage: dict[str, Any]) -> int | None:
    details = usage.get("output_tokens_details")
    if isinstance(details, dict):
        reasoning = _int_from_any(details.get("reasoning_tokens"))
        if reasoning is not None:
            return reasoning
    return _int_from_any(usage.get("reasoning_tokens"))


def _int_from_any(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _model_settings(request: LiveAgentRequest) -> dict[str, str]:
    metadata = dict(request.metadata)
    raw_provider = str(
        metadata.get("provider_profile")
        or request.provider_profile
        or os.environ.get("ROBOCLAWS_OPENAI_AGENTS_PROVIDER")
        or os.environ.get("ROBOCLAWS_CODEX_PROVIDER")
        or "codex-env"
    ).strip()
    try:
        provider = normalize_provider_route(raw_provider, default="codex-env")
        route = provider_route_spec(provider)
    except KeyError as exc:
        raise RuntimeError(
            "openai-agents-live supports provider profiles codex-env, mify, "
            "minimax, mimo-openai-chat, and kimi-openai-chat"
        ) from exc
    if "openai-agents-sdk" not in route.supported_engines:
        raise RuntimeError(f"openai-agents-live does not support provider profile {provider}")

    base_url = str(metadata.get("base_url") or route_base_url(route))
    api_key = str(
        metadata.get("api_key")
        or (os.environ.get(route.api_key_env or "") if route.api_key_env else "")
        or ""
    )
    model = str(
        metadata.get("model")
        or request.model
        or os.environ.get("ROBOCLAWS_OPENAI_AGENTS_MODEL")
        or os.environ.get("ROBOCLAWS_CODEX_MODEL")
        or route.default_model_id
    )
    if route.base_url_env == "CODEX_BASE_URL":
        _require_setting(provider, route.base_url_env, base_url)
    if route.api_key_env:
        _require_setting(provider, route.api_key_env, api_key)
    return {
        "provider_profile": provider,
        "wire_api": route.wire_api,
        "wire_source": route.wire_source,
        "route_status": route.status_for_engine("openai-agents-sdk"),
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
    if any(
        item in lowered
        for item in (
            "requires xm_llm_api_key",
            "requires mm_api_key",
            "supports responses provider",
        )
    ):
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


def _json_size_bytes(value: Any) -> int:
    return len(json.dumps(_to_jsonable(value), sort_keys=True).encode("utf-8"))


def _stable_item_hash(value: Any) -> str:
    material = json.dumps(_to_jsonable(value), sort_keys=True).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


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

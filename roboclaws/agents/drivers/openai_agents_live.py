"""Experimental OpenAI Agents SDK live-agent runtime."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from roboclaws.agents.live_runtime import LiveAgentRequest, LiveAgentResult, LiveAgentRuntime
from roboclaws.agents.live_status import LiveAgentFailure


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
        status_path = request.artifact_path("live_status", "live_status.json")

        try:
            result = _run_openai_agents(request, events_path=events_path)
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
                artifact_paths={"openai_agents_events": events_path, "live_status": status_path},
            )
            _write_json(status_path, normalized.to_live_status_payload())
            return normalized
        except Exception as exc:
            failure = LiveAgentFailure("agent_cli_failure", retryable=False, detail=str(exc))
            normalized = LiveAgentResult.from_failure(
                phase="failed",
                exit_status=1,
                failure=failure,
                started_at_epoch=started_at,
                finished_at_epoch=time.time(),
                artifact_paths={"openai_agents_events": events_path, "live_status": status_path},
            )
            _write_json(status_path, normalized.to_live_status_payload())
            return normalized

        finished_at = time.time()
        run_result_path = request.run_dir / "run_result.json"
        artifact_paths = {
            "openai_agents_events": events_path,
            "openai_agents_trace": trace_path,
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


def _run_openai_agents(request: LiveAgentRequest, *, events_path: Path) -> Any:
    try:
        from agents import Agent, Runner  # type: ignore[import-not-found]
        from agents.mcp import MCPServerStreamableHttp  # type: ignore[import-not-found]
    except ImportError:
        raise

    server = MCPServerStreamableHttp(
        name=request.mcp_server.name,
        params={"url": request.mcp_server.url},
    )
    agent_kwargs: dict[str, Any] = {
        "name": f"roboclaws-{request.task_name}",
        "instructions": request.kickoff_prompt,
        "mcp_servers": [server],
    }
    if request.model:
        agent_kwargs["model"] = request.model
    agent = Agent(**agent_kwargs)
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text("", encoding="utf-8")

    if hasattr(server, "__aenter__"):
        return _run_with_async_mcp_server(server, agent, request, events_path)
    runner_kwargs: dict[str, Any] = {}
    if request.max_turns is not None:
        runner_kwargs["max_turns"] = request.max_turns
    result = Runner.run_sync(agent, request.kickoff_prompt, **runner_kwargs)
    _append_event(events_path, {"event": "result", "summary": _summarize_sdk_result(result)})
    return result


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
            runner_kwargs: dict[str, Any] = {}
            if request.max_turns is not None:
                runner_kwargs["max_turns"] = request.max_turns
            result = await Runner.run(agent, request.kickoff_prompt, **runner_kwargs)
        _append_event(events_path, {"event": "result", "summary": _summarize_sdk_result(result)})
        return result

    return asyncio.run(_run())


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


def _append_event(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

#!/usr/bin/env python3
"""Benchmark model route support across OpenAI Chat, Responses, and Anthropic APIs.

Architecture layer: Harness recipes / dev provider benchmark. This script is a
periodic route-support probe; it does not register product provider routes.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shlex
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from roboclaws.agents.provider_registry import provider_route_spec, route_base_url
from roboclaws.operator_console.redaction import redact_text

WireApi = Literal["openai-chat", "openai-responses", "anthropic-messages"]
BenchmarkLayer = Literal["health", "first-content", "throughput", "stream-throughput", "agent-case"]

DEFAULT_PROMPT = "Health check. Reply exactly ok."
DEFAULT_FIRST_CONTENT_PROMPT = "First-content latency benchmark. Reply exactly: ok"
DEFAULT_THROUGHPUT_PROMPT = (
    "Throughput benchmark. Write one continuous English passage of about 700 words about "
    "household robotics evaluation, semantic maps, and model-provider reliability. Do not use "
    "bullet points or tables. Keep writing until the passage is complete."
)
DEFAULT_STREAM_THROUGHPUT_PROMPT = (
    "Sustained streaming throughput benchmark. Write one continuous English passage of about "
    "2500 words about household robotics evaluation, semantic maps, route reliability, "
    "simulation evidence, and long-running model-provider operations. Do not use bullet points, "
    "tables, headings, code blocks, or lists. Keep writing until the passage is complete."
)
DEFAULT_LAYERS: tuple[BenchmarkLayer, ...] = ("health", "throughput")
LAYER_CHOICES: tuple[BenchmarkLayer, ...] = (
    "health",
    "first-content",
    "throughput",
    "stream-throughput",
    "agent-case",
)
DEFAULT_ITERATIONS = 1
DEFAULT_TIMEOUT_S = 60.0
DEFAULT_MAX_TOKENS = 512
DEFAULT_FIRST_CONTENT_MAX_TOKENS = 256
DEFAULT_THROUGHPUT_MAX_TOKENS = 2048
DEFAULT_STREAM_THROUGHPUT_MAX_TOKENS = 4096
DEFAULT_AGENT_CASE_MAX_TOKENS = 768


@dataclass(frozen=True)
class AgentBenchmarkCase:
    case_id: str
    label: str
    source: str
    prompt: str


AGENT_BENCHMARK_CASES: tuple[AgentBenchmarkCase, ...] = (
    AgentBenchmarkCase(
        case_id="cleanup-worklist-plan",
        label="Cleanup worklist next-action plan",
        source="output/household/verify-done-held-mify-mimo/0605_1507/seed-7/agent_view.json",
        prompt=(
            "You are driving the Roboclaws household-world cleanup MCP surface. Use only public "
            "evidence. Private scorer truth is unavailable. Given this public cleanup worklist, "
            "produce the next six MCP actions and a one-sentence stop condition. Keep it "
            "concise.\n\n"
            "Tool surface: metric_map, observe, navigate_to_waypoint, navigate_to_object, pick, "
            "navigate_to_receptacle, open_receptacle, place, place_inside, close_receptacle, "
            "done.\n"
            "Worklist objects:\n"
            "- observed_001 Potato, room_2, last seen at generated_exploration_001, candidate "
            "anchor_fixture_002, recommended_tool=place_inside, state=observed.\n"
            "- observed_002 Plate, room_5, last seen at generated_exploration_008, candidate "
            "anchor_fixture_009, recommended_tool=place, state=observed.\n"
            "- observed_003 RemoteControl, room_3, last seen at generated_exploration_003, "
            "candidate anchor_fixture_006, recommended_tool=place, state=observed.\n"
            "- observed_004 Book, room_2, last seen at generated_exploration_002, candidate "
            "anchor_fixture_004, recommended_tool=place_inside, state=observed.\n"
            "- observed_005 Pillow, room_2, last seen at generated_exploration_002, candidate "
            "anchor_fixture_004, recommended_tool=place, state=observed.\n"
            "Return compact JSON with keys actions, risk_notes, stop_condition."
        ),
    ),
    AgentBenchmarkCase(
        case_id="runtime-map-summary",
        label="Runtime metric map status summary",
        source=(
            "output/evals/household_world_cleanup_capability/20260615_verify_cleanup/"
            "runs/cleanup_repeated_seed7/trial-0000/runtime_metric_map.json"
        ),
        prompt=(
            "Summarize this public Runtime Metric Map state for a coding agent about to continue "
            "a cleanup run. Do not invent private destinations. Include: coverage gaps, likely "
            "next waypoint, and what evidence should be requested before picking anything.\n\n"
            "Map state: schema=runtime_metric_map_v1, world=molmospaces/val_0, "
            "evidence_lane=world-oracle-labels, generated exploration candidates "
            "generated_exploration_001 through generated_exploration_014. Visited waypoints: "
            "001, 002, 003, 004, 005, 006, 007, 008, 009, 010, 011. Observed categories: "
            "Potato, Plate, RemoteControl, Book, Pillow. Public semantic anchors include "
            "countertop-like, table-like, desk-like, cabinet-like, sofa-like, and bed-like "
            "fixtures. Several observed objects have candidate_inferred destination policy, "
            "not private truth. Output 5 short bullets."
        ),
    ),
    AgentBenchmarkCase(
        case_id="camera-grounded-composite",
        label="Camera-grounded composite decision",
        source="docs/status/active/live-agent-runtime-sdk-spike.md",
        prompt=(
            "You are reviewing a camera-grounded cleanup turn from the OpenAI Agents SDK route. "
            "The optimized route should prefer a composite declare-and-act cadence when visual "
            "evidence is actionable, but it must preserve traceability. Decide the next tool call "
            "and explain briefly.\n\n"
            "Current turn: observe returned three visible candidates. vc_01 appears to be a plate "
            "on a dining table with bbox confidence 0.84. vc_02 appears to be a remote control on "
            "a sofa with confidence 0.79. vc_03 is uncertain clutter near a cabinet with "
            "confidence 0.41. Previous turn already moved a book to a shelf. The active policy "
            "says do not "
            "call standalone declaration tools after SDK continuation if a composite action can "
            "carry the declaration internally. Available tools: declare_visual_candidates, "
            "navigate_to_visual_candidate, inspect_visible_object, pick, place, place_inside, "
            "done. "
            "Return: selected_tool, arguments, why_not_the_others."
        ),
    ),
    AgentBenchmarkCase(
        case_id="sdk-speedup-verdict",
        label="Agent SDK speedup verdict",
        source="docs/status/active/agent-sdk-speedup-live-refresh-matrix.json",
        prompt=(
            "Given this sanitized Agent SDK performance row, decide whether it is an accepted "
            "speedup, expected-rejected evidence, or blocked evidence. Keep private data out.\n\n"
            "Row: provider_profile=mify, model=mimo-v2.5, evidence_lane=camera-grounded-labels. "
            "Baseline completed with done and report artifacts. Candidate O+AC completed with "
            "done and same-or-better quality. Observed wall time delta=-659.477s and model API "
            "time delta=-653.563s. Same-dataset calibration has low explanatory power "
            "(r2=0.048291), and holdout calibration is weaker (r2=-4.79098), so normalized model "
            "work is diagnostic only. Privacy gate passed; source rows are sanitized and do not "
            "store raw prompts or model text. Output a verdict, the evidence that supports it, "
            "and one follow-up benchmark to run next."
        ),
    ),
)


@dataclass(frozen=True)
class MatrixCase:
    case_id: str
    provider_id: str
    provider_label: str
    model: str
    wire_api: WireApi
    api_key_env: str
    base_url: str
    api_key_alt_env: str = ""
    headers: tuple[tuple[str, str], ...] = ()
    expected_support: str = "unknown"
    note: str = ""


@dataclass(frozen=True)
class TrialResult:
    index: int
    layer: BenchmarkLayer
    status: str
    elapsed_s: float
    agent_case_id: str = ""
    agent_case_label: str = ""
    response_model: str = ""
    output_preview: str = ""
    output_chars: int = 0
    measured_output_tokens: int | None = None
    output_token_count_source: str = ""
    output_tokens_per_s: float | None = None
    output_chars_per_s: float | None = None
    first_content_s: float | None = None
    decode_s: float | None = None
    decode_output_tokens_per_s: float | None = None
    decode_output_chars_per_s: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    error_type: str = ""
    error: str = ""


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    provider_id: str
    provider_label: str
    model: str
    wire_api: WireApi
    layer: BenchmarkLayer
    agent_case_id: str
    agent_case_label: str
    agent_case_source: str
    expected_support: str
    status: str
    api_key_env: str
    api_key_alt_env: str
    base_url_configured: bool
    iterations: int
    max_tokens: int
    success_count: int
    failure_count: int
    skipped_reason: str = ""
    mean_s: float | None = None
    median_s: float | None = None
    min_s: float | None = None
    max_s: float | None = None
    mean_output_tokens_per_s: float | None = None
    median_output_tokens_per_s: float | None = None
    mean_output_chars_per_s: float | None = None
    median_output_chars_per_s: float | None = None
    mean_decode_output_tokens_per_s: float | None = None
    median_decode_output_tokens_per_s: float | None = None
    mean_decode_output_chars_per_s: float | None = None
    median_decode_output_chars_per_s: float | None = None
    median_first_content_s: float | None = None
    median_decode_s: float | None = None
    output_token_count_source: str = ""
    response_model: str = ""
    output_preview: str = ""
    note: str = ""
    trials: tuple[TrialResult, ...] = ()


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = raw_value.strip()
        try:
            parts = shlex.split(value, comments=False, posix=True)
        except ValueError:
            parts = [value]
        os.environ[key] = parts[0] if parts else ""


def default_cases() -> tuple[MatrixCase, ...]:
    return (
        *_codex_env_cases(),
        *_mify_cases(),
        *_minimax_cases(),
        *_mimo_token_plan_cases(),
        *_mimo_inside_cases(),
        *_kimi_cases(),
        *_nvidia_cases(),
    )


def _codex_env_cases() -> tuple[MatrixCase, ...]:
    route = provider_route_spec("codex-env")
    base_url = route_base_url(route)
    return (
        MatrixCase(
            case_id="codex-env:gpt-5.5:responses",
            provider_id="codex-env",
            provider_label="Codex env",
            model="gpt-5.5",
            wire_api="openai-responses",
            api_key_env=route.api_key_env or "",
            base_url=base_url,
            expected_support="native",
        ),
        MatrixCase(
            case_id="codex-env:gpt-5.5:chat",
            provider_id="codex-env",
            provider_label="Codex env",
            model="gpt-5.5",
            wire_api="openai-chat",
            api_key_env=route.api_key_env or "",
            base_url=base_url,
            expected_support="probe",
        ),
    )


def _mify_cases() -> tuple[MatrixCase, ...]:
    route = provider_route_spec("mify")
    anthropic_route = provider_route_spec("mify-anthropic")
    base_url = route_base_url(route)
    return (
        *(
            MatrixCase(
                case_id=f"mify:{_case_model_id(model)}:{wire}",
                provider_id="mify",
                provider_label="MiMo mify",
                model=model,
                wire_api=wire,
                api_key_env=route.api_key_env or "",
                base_url=base_url,
                expected_support="probe" if wire == "openai-chat" else "native",
            )
            for model in ("xiaomi/mimo-v2.5", "xiaomi/mimo-v2.5-pro")
            for wire in ("openai-chat", "openai-responses")
        ),
        MatrixCase(
            case_id="mify:xiaomi-mimo-v2.5:anthropic",
            provider_id="mify",
            provider_label="MiMo mify",
            model="xiaomi/mimo-v2.5",
            wire_api="anthropic-messages",
            api_key_env=anthropic_route.api_key_env or "",
            base_url=route_base_url(anthropic_route),
            expected_support="native",
        ),
    )


def _minimax_cases() -> tuple[MatrixCase, ...]:
    route = provider_route_spec("minimax")
    base_url = route_base_url(route)
    return tuple(
        MatrixCase(
            case_id=f"minimax:{model}:responses",
            provider_id="minimax",
            provider_label="MiniMax",
            model=model,
            wire_api="openai-responses",
            api_key_env=route.api_key_env or "",
            base_url=base_url,
            expected_support="native",
        )
        for model in ("MiniMax-M3", "MiniMax-M2.7-highspeed")
    )


def _mimo_token_plan_cases() -> tuple[MatrixCase, ...]:
    chat_route = provider_route_spec("mimo-openai-chat")
    anthropic_route = provider_route_spec("mimo-anthropic")
    return (
        *(
            MatrixCase(
                case_id=f"mimo-token-plan:{model}:{wire}",
                provider_id="mimo-token-plan",
                provider_label="MiMo token plan",
                model=model,
                wire_api=wire,
                api_key_env=chat_route.api_key_env or "",
                base_url=route_base_url(chat_route),
                expected_support="native" if wire == "openai-chat" else "probe",
            )
            for model in ("mimo-v2.5", "mimo-v2.5-pro")
            for wire in ("openai-chat", "openai-responses")
        ),
        MatrixCase(
            case_id="mimo-token-plan:mimo-v2.5:anthropic",
            provider_id="mimo-token-plan",
            provider_label="MiMo token plan",
            model="mimo-v2.5",
            wire_api="anthropic-messages",
            api_key_env=anthropic_route.api_key_env or "",
            base_url=route_base_url(anthropic_route),
            expected_support="native",
        ),
    )


def _mimo_inside_cases() -> tuple[MatrixCase, ...]:
    return tuple(
        MatrixCase(
            case_id=f"mimo-inside:{model}:{wire}",
            provider_id="mimo-inside",
            provider_label="MiMo inside",
            model=model,
            wire_api=wire,
            api_key_env="MIMO_API_KEY",
            base_url=os.environ.get("MIMO_BASE_URL", ""),
            expected_support="native" if wire == "openai-chat" else "probe",
        )
        for model in ("mimo-v2.5", "mimo-v2.5-pro", "mimo-1000")
        for wire in ("openai-chat", "openai-responses")
    )


def _kimi_cases() -> tuple[MatrixCase, ...]:
    chat_route = provider_route_spec("kimi-openai-chat")
    anthropic_route = provider_route_spec("kimi-anthropic")
    return (
        MatrixCase(
            case_id="kimi:kimi-k2.7-code:chat",
            provider_id="kimi",
            provider_label="Kimi",
            model="kimi-k2.7-code",
            wire_api="openai-chat",
            api_key_env=chat_route.api_key_env or "",
            base_url=route_base_url(chat_route),
            headers=(("User-Agent", "claude-code/1.0.0"),),
            expected_support="native",
        ),
        MatrixCase(
            case_id="kimi:kimi-k2.7-code:responses",
            provider_id="kimi",
            provider_label="Kimi",
            model="kimi-k2.7-code",
            wire_api="openai-responses",
            api_key_env=chat_route.api_key_env or "",
            base_url=route_base_url(chat_route),
            headers=(("User-Agent", "claude-code/1.0.0"),),
            expected_support="probe",
        ),
        MatrixCase(
            case_id="kimi:k2.6:anthropic",
            provider_id="kimi",
            provider_label="Kimi",
            model="k2.6",
            wire_api="anthropic-messages",
            api_key_env=anthropic_route.api_key_env or "",
            base_url=route_base_url(anthropic_route),
            headers=(("User-Agent", "Claude-Code/1.0"),),
            expected_support="native",
        ),
    )


def _nvidia_cases() -> tuple[MatrixCase, ...]:
    base_url = os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    return (
        MatrixCase(
            case_id="nvidia:nemotron-nano-vl:chat",
            provider_id="nvidia",
            provider_label="NVIDIA",
            model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            wire_api="openai-chat",
            api_key_env="NV_API_KEY",
            api_key_alt_env="NVIDIA_API_KEY",
            base_url=base_url,
            expected_support="native",
        ),
        MatrixCase(
            case_id="nvidia:nemotron-nano-vl:responses",
            provider_id="nvidia",
            provider_label="NVIDIA",
            model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            wire_api="openai-responses",
            api_key_env="NV_API_KEY",
            api_key_alt_env="NVIDIA_API_KEY",
            base_url=base_url,
            expected_support="probe",
        ),
    )


def _case_model_id(model: str) -> str:
    return model.replace("/", "-")


def selected_cases(
    cases: tuple[MatrixCase, ...],
    *,
    providers: set[str],
    wires: set[str],
    case_ids: set[str],
) -> tuple[MatrixCase, ...]:
    selected = cases
    if providers:
        selected = tuple(case for case in selected if case.provider_id in providers)
    if wires:
        selected = tuple(case for case in selected if case.wire_api in wires)
    if case_ids:
        selected = tuple(case for case in selected if case.case_id in case_ids)
    return selected


def run_case(
    case: MatrixCase,
    *,
    layer: BenchmarkLayer,
    prompt: str,
    iterations: int,
    max_tokens: int,
    timeout_s: float,
    agent_case: AgentBenchmarkCase | None = None,
    env: dict[str, str] | None = None,
) -> CaseResult:
    env_map = os.environ if env is None else env
    api_key = env_map.get(case.api_key_env) or env_map.get(case.api_key_alt_env) or ""
    base_url = case.base_url.strip()
    if layer == "stream-throughput" and case.wire_api != "openai-chat":
        return _skipped_case(
            case,
            layer=layer,
            reason="stream-throughput is only implemented for OpenAI Chat streaming",
            iterations=iterations,
            max_tokens=max_tokens,
            base_url_configured=bool(base_url),
            agent_case=agent_case,
        )
    if not api_key:
        return _skipped_case(
            case,
            layer=layer,
            reason=_missing_key_label(case),
            iterations=iterations,
            max_tokens=max_tokens,
            base_url_configured=bool(base_url),
            agent_case=agent_case,
        )
    if not base_url:
        return _skipped_case(
            case,
            layer=layer,
            reason="missing base URL",
            iterations=iterations,
            max_tokens=max_tokens,
            base_url_configured=False,
            agent_case=agent_case,
        )

    trials = tuple(
        run_trial(
            case,
            index=index + 1,
            layer=layer,
            prompt=prompt,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            api_key=api_key,
            agent_case=agent_case,
        )
        for index in range(iterations)
    )
    return summarize_case(
        case,
        layer=layer,
        trials=trials,
        iterations=iterations,
        max_tokens=max_tokens,
        base_url_configured=True,
        agent_case=agent_case,
    )


def run_trial(
    case: MatrixCase,
    *,
    index: int,
    layer: BenchmarkLayer,
    prompt: str,
    max_tokens: int,
    timeout_s: float,
    api_key: str,
    agent_case: AgentBenchmarkCase | None = None,
) -> TrialResult:
    url = endpoint_url(case.base_url, case.wire_api)
    payload = payload_for_case(case, prompt=prompt, max_tokens=max_tokens)
    stream_openai_chat = case.wire_api == "openai-chat" and layer in {
        "first-content",
        "stream-throughput",
    }
    if stream_openai_chat:
        payload["stream"] = True
        if layer == "stream-throughput":
            payload["stream_options"] = {"include_usage": True}
    headers = headers_for_case(case, api_key=api_key)
    started = time.monotonic()
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            status_code = response.status
            content_type = response.headers.get("content-type", "")
            if stream_openai_chat:
                if status_code < 200 or status_code >= 300:
                    body = response.read().decode("utf-8", errors="replace")
                    raise RuntimeError(f"HTTP {status_code}: {body[:500]}")
                return _read_openai_chat_stream_trial(
                    response,
                    case=case,
                    index=index,
                    layer=layer,
                    started=started,
                    url=url,
                    agent_case=agent_case,
                )
            body = response.read().decode("utf-8", errors="replace")
        if status_code < 200 or status_code >= 300:
            raise RuntimeError(f"HTTP {status_code}: {body[:500]}")
        if "json" not in content_type.lower():
            raise RuntimeError(f"expected JSON response, got {content_type}: {body[:500]}")
        data = json.loads(body)
        output = output_text(case.wire_api, data)
        if not output:
            raise RuntimeError("provider call completed without visible output")
        elapsed_s = time.monotonic() - started
        prompt_tokens, completion_tokens, total_tokens = usage_tokens(case.wire_api, data)
        measured_output_tokens, token_source = measured_output_token_count(
            output=output,
            completion_tokens=completion_tokens,
        )
        output_preview = _redact_benchmark_text(output[:120], extra_values=(case.base_url, url))
        return TrialResult(
            index=index,
            layer=layer,
            status="PASS",
            elapsed_s=round(elapsed_s, 3),
            agent_case_id=agent_case.case_id if agent_case else "",
            agent_case_label=agent_case.label if agent_case else "",
            response_model=response_model(case.wire_api, data),
            output_preview=output_preview,
            output_chars=len(output),
            measured_output_tokens=measured_output_tokens,
            output_token_count_source=token_source,
            output_tokens_per_s=_per_second(measured_output_tokens, elapsed_s),
            output_chars_per_s=_per_second(len(output), elapsed_s),
            first_content_s=round(elapsed_s, 3) if layer == "first-content" else None,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
    except urllib.error.HTTPError as exc:
        body = exc.read(800).decode("utf-8", errors="replace")
        return TrialResult(
            index=index,
            layer=layer,
            status="FAIL",
            elapsed_s=round(time.monotonic() - started, 3),
            agent_case_id=agent_case.case_id if agent_case else "",
            agent_case_label=agent_case.label if agent_case else "",
            error_type="HTTPError",
            error=_redact_benchmark_text(
                f"HTTP {exc.code} {exc.reason}: {body[:600]}",
                extra_values=(case.base_url, url),
            ),
        )
    except Exception as exc:  # pragma: no cover - live provider shapes vary
        return TrialResult(
            index=index,
            layer=layer,
            status="FAIL",
            elapsed_s=round(time.monotonic() - started, 3),
            agent_case_id=agent_case.case_id if agent_case else "",
            agent_case_label=agent_case.label if agent_case else "",
            error_type=exc.__class__.__name__,
            error=_redact_benchmark_text(
                str(exc).replace("\n", " ")[:800],
                extra_values=(case.base_url, url),
            ),
        )


def _read_openai_chat_stream_trial(
    response: Any,
    *,
    case: MatrixCase,
    index: int,
    layer: BenchmarkLayer,
    started: float,
    url: str,
    agent_case: AgentBenchmarkCase | None = None,
) -> TrialResult:
    output_parts: list[str] = []
    response_model_name = ""
    first_content_at: float | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    try:
        for raw_line in response:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            if line.startswith("data:"):
                line = line.removeprefix("data:").strip()
            elif line.startswith(("event:", "id:", "retry:", ":")):
                continue
            elif not line.startswith("{"):
                continue
            if not line or line == "[DONE]":
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            response_model_name = response_model_name or str(event.get("model") or "")
            usage_prompt, usage_completion, usage_total = usage_tokens(case.wire_api, event)
            prompt_tokens = usage_prompt if usage_prompt is not None else prompt_tokens
            completion_tokens = (
                usage_completion if usage_completion is not None else completion_tokens
            )
            total_tokens = usage_total if usage_total is not None else total_tokens
            choices = event.get("choices")
            if not isinstance(choices, list) or not choices:
                continue
            first = choices[0] if isinstance(choices[0], dict) else {}
            delta = first.get("delta") if isinstance(first, dict) else {}
            if not isinstance(delta, dict):
                continue
            piece = delta.get("content") or delta.get("reasoning_content") or ""
            if not piece:
                continue
            if first_content_at is None:
                first_content_at = time.monotonic()
            output_parts.append(str(piece))
        completed_at = time.monotonic()
        output = "".join(output_parts).strip()
        if not output:
            raise RuntimeError("stream completed without visible output")
        elapsed_s = completed_at - started
        first_content_s = (first_content_at - started) if first_content_at is not None else None
        decode_s = (
            completed_at - first_content_at
            if first_content_at is not None and completed_at > first_content_at
            else None
        )
        measured_output_tokens, token_source = measured_output_token_count(
            output=output,
            completion_tokens=completion_tokens,
        )
        return TrialResult(
            index=index,
            layer=layer,
            status="PASS",
            elapsed_s=round(elapsed_s, 3),
            agent_case_id=agent_case.case_id if agent_case else "",
            agent_case_label=agent_case.label if agent_case else "",
            response_model=response_model_name,
            output_preview=_redact_benchmark_text(output[:120], extra_values=(case.base_url, url)),
            output_chars=len(output),
            measured_output_tokens=measured_output_tokens,
            output_token_count_source=token_source,
            output_tokens_per_s=_per_second(measured_output_tokens, elapsed_s),
            output_chars_per_s=_per_second(len(output), elapsed_s),
            first_content_s=round(first_content_s, 3) if first_content_s is not None else None,
            decode_s=round(decode_s, 3) if decode_s is not None else None,
            decode_output_tokens_per_s=_per_second(measured_output_tokens, decode_s or 0),
            decode_output_chars_per_s=_per_second(len(output), decode_s or 0),
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )
    except Exception as exc:  # pragma: no cover - live provider stream chunks vary
        return TrialResult(
            index=index,
            layer=layer,
            status="FAIL",
            elapsed_s=round(time.monotonic() - started, 3),
            agent_case_id=agent_case.case_id if agent_case else "",
            agent_case_label=agent_case.label if agent_case else "",
            error_type=exc.__class__.__name__,
            error=_redact_benchmark_text(
                str(exc).replace("\n", " ")[:800],
                extra_values=(case.base_url, url),
            ),
        )


def endpoint_url(base_url: str, wire_api: WireApi) -> str:
    base = base_url.strip().rstrip("/")
    if wire_api == "openai-chat":
        return _openai_endpoint(base, "chat/completions")
    if wire_api == "openai-responses":
        return _openai_endpoint(base, "responses")
    return _anthropic_endpoint(base)


def _openai_endpoint(base: str, suffix: str) -> str:
    if base.endswith("/" + suffix):
        return base
    parsed = urllib.parse.urlparse(base)
    path = parsed.path.rstrip("/")
    if not path.endswith("/v1"):
        base = f"{base}/v1"
    return f"{base}/{suffix}"


def _anthropic_endpoint(base: str) -> str:
    if base.endswith("/v1/messages"):
        return base
    return f"{base}/v1/messages"


def payload_for_case(case: MatrixCase, *, prompt: str, max_tokens: int) -> dict[str, Any]:
    if case.wire_api == "openai-chat":
        return {
            "model": case.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }
    if case.wire_api == "openai-responses":
        return {
            "model": case.model,
            "input": prompt,
            "max_output_tokens": max_tokens,
            "stream": False,
        }
    return {
        "model": case.model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }


def headers_for_case(case: MatrixCase, *, api_key: str) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if case.wire_api == "anthropic-messages":
        headers["anthropic-version"] = "2023-06-01"
        headers["x-api-key"] = api_key
    headers.update(dict(case.headers))
    return headers


def output_text(wire_api: WireApi, data: dict[str, Any]) -> str:
    if wire_api == "openai-chat":
        choices = data.get("choices")
        if not isinstance(choices, list) or not choices:
            return ""
        message = choices[0].get("message") if isinstance(choices[0], dict) else None
        if not isinstance(message, dict):
            return ""
        return str(message.get("content") or message.get("reasoning_content") or "").strip()
    if wire_api == "openai-responses":
        direct = data.get("output_text")
        if direct:
            return str(direct).strip()
        output = data.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("text"):
                            parts.append(str(part["text"]))
            return "\n".join(parts).strip()
        return ""
    content = data.get("content")
    if isinstance(content, list):
        return "\n".join(
            str(part.get("text"))
            for part in content
            if isinstance(part, dict) and part.get("type") == "text" and part.get("text")
        ).strip()
    return ""


def response_model(wire_api: WireApi, data: dict[str, Any]) -> str:
    if wire_api in {"openai-chat", "openai-responses"}:
        return str(data.get("model") or "")
    return str(data.get("model") or "")


def usage_tokens(
    wire_api: WireApi, data: dict[str, Any]
) -> tuple[int | None, int | None, int | None]:
    usage = data.get("usage") if isinstance(data, dict) else {}
    if not isinstance(usage, dict):
        return None, None, None
    if wire_api == "anthropic-messages":
        prompt_tokens = _int_or_none(usage.get("input_tokens"))
        completion_tokens = _int_or_none(usage.get("output_tokens"))
        total_tokens = (
            prompt_tokens + completion_tokens
            if prompt_tokens is not None and completion_tokens is not None
            else None
        )
        return prompt_tokens, completion_tokens, total_tokens
    return (
        _int_or_none(usage.get("prompt_tokens")),
        _int_or_none(usage.get("completion_tokens")),
        _int_or_none(usage.get("total_tokens")),
    )


def measured_output_token_count(
    *,
    output: str,
    completion_tokens: int | None,
) -> tuple[int, str]:
    if completion_tokens is not None:
        return completion_tokens, "provider_usage"
    # Coarse fallback only. It keeps trend reports useful for providers that omit
    # usage, but it should not be treated as billing/tokenizer-accurate data.
    return max(1, round(len(output) / 4)), "estimated_chars_div_4"


def _per_second(value: int | None, elapsed_s: float) -> float | None:
    if value is None or elapsed_s <= 0:
        return None
    return round(value / elapsed_s, 3)


def _redact_benchmark_text(text: str, *, extra_values: tuple[str, ...] = ()) -> str:
    redacted = redact_text(text)
    for value in extra_values:
        if value and len(value) >= 6:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted


def summarize_case(
    case: MatrixCase,
    *,
    layer: BenchmarkLayer,
    trials: tuple[TrialResult, ...],
    iterations: int,
    max_tokens: int,
    base_url_configured: bool,
    agent_case: AgentBenchmarkCase | None = None,
) -> CaseResult:
    successes = [trial for trial in trials if trial.status == "PASS"]
    failures = [trial for trial in trials if trial.status != "PASS"]
    elapsed = [trial.elapsed_s for trial in successes]
    token_rates = [
        trial.output_tokens_per_s for trial in successes if trial.output_tokens_per_s is not None
    ]
    char_rates = [
        trial.output_chars_per_s for trial in successes if trial.output_chars_per_s is not None
    ]
    decode_token_rates = [
        trial.decode_output_tokens_per_s
        for trial in successes
        if trial.decode_output_tokens_per_s is not None
    ]
    decode_char_rates = [
        trial.decode_output_chars_per_s
        for trial in successes
        if trial.decode_output_chars_per_s is not None
    ]
    first_content = [
        trial.first_content_s for trial in successes if trial.first_content_s is not None
    ]
    decode_elapsed = [trial.decode_s for trial in successes if trial.decode_s is not None]
    token_sources = sorted(
        {trial.output_token_count_source for trial in successes if trial.output_token_count_source}
    )
    status = "PASS" if successes and not failures else "PARTIAL" if successes else "FAIL"
    first_success = successes[0] if successes else None
    return CaseResult(
        case_id=case.case_id,
        provider_id=case.provider_id,
        provider_label=case.provider_label,
        model=case.model,
        wire_api=case.wire_api,
        layer=layer,
        agent_case_id=agent_case.case_id if agent_case else "",
        agent_case_label=agent_case.label if agent_case else "",
        agent_case_source=agent_case.source if agent_case else "",
        expected_support=case.expected_support,
        status=status,
        api_key_env=case.api_key_env,
        api_key_alt_env=case.api_key_alt_env,
        base_url_configured=base_url_configured,
        iterations=iterations,
        max_tokens=max_tokens,
        success_count=len(successes),
        failure_count=len(failures),
        mean_s=round(statistics.fmean(elapsed), 3) if elapsed else None,
        median_s=round(statistics.median(elapsed), 3) if elapsed else None,
        min_s=round(min(elapsed), 3) if elapsed else None,
        max_s=round(max(elapsed), 3) if elapsed else None,
        mean_output_tokens_per_s=round(statistics.fmean(token_rates), 3) if token_rates else None,
        median_output_tokens_per_s=round(statistics.median(token_rates), 3)
        if token_rates
        else None,
        mean_output_chars_per_s=round(statistics.fmean(char_rates), 3) if char_rates else None,
        median_output_chars_per_s=round(statistics.median(char_rates), 3) if char_rates else None,
        mean_decode_output_tokens_per_s=round(statistics.fmean(decode_token_rates), 3)
        if decode_token_rates
        else None,
        median_decode_output_tokens_per_s=round(statistics.median(decode_token_rates), 3)
        if decode_token_rates
        else None,
        mean_decode_output_chars_per_s=round(statistics.fmean(decode_char_rates), 3)
        if decode_char_rates
        else None,
        median_decode_output_chars_per_s=round(statistics.median(decode_char_rates), 3)
        if decode_char_rates
        else None,
        median_first_content_s=round(statistics.median(first_content), 3)
        if first_content
        else None,
        median_decode_s=round(statistics.median(decode_elapsed), 3) if decode_elapsed else None,
        output_token_count_source=",".join(token_sources),
        response_model=first_success.response_model if first_success else "",
        output_preview=(first_success.output_preview if first_success else ""),
        note=case.note,
        trials=trials,
    )


def _skipped_case(
    case: MatrixCase,
    *,
    layer: BenchmarkLayer,
    reason: str,
    iterations: int,
    max_tokens: int,
    base_url_configured: bool,
    agent_case: AgentBenchmarkCase | None = None,
) -> CaseResult:
    return CaseResult(
        case_id=case.case_id,
        provider_id=case.provider_id,
        provider_label=case.provider_label,
        model=case.model,
        wire_api=case.wire_api,
        layer=layer,
        agent_case_id=agent_case.case_id if agent_case else "",
        agent_case_label=agent_case.label if agent_case else "",
        agent_case_source=agent_case.source if agent_case else "",
        expected_support=case.expected_support,
        status="SKIP",
        api_key_env=case.api_key_env,
        api_key_alt_env=case.api_key_alt_env,
        base_url_configured=base_url_configured,
        iterations=iterations,
        max_tokens=max_tokens,
        success_count=0,
        failure_count=0,
        skipped_reason=reason,
        note=case.note,
    )


def _missing_key_label(case: MatrixCase) -> str:
    if case.api_key_alt_env:
        return f"missing {case.api_key_env} or {case.api_key_alt_env}"
    return f"missing {case.api_key_env}"


def _int_or_none(value: Any) -> int | None:
    return value if isinstance(value, int) else None


def result_payload(results: list[CaseResult], *, args: argparse.Namespace) -> dict[str, Any]:
    statuses = {
        status: sum(1 for result in results if result.status == status)
        for status in (
            "PASS",
            "PARTIAL",
            "FAIL",
            "SKIP",
        )
    }
    return {
        "benchmark": "roboclaws_model_matrix_wire_support_v1",
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "layers": args.layer or list(DEFAULT_LAYERS),
        "prompts": {
            "health": _redact_benchmark_text(args.prompt),
            "first-content": _redact_benchmark_text(args.first_content_prompt),
            "throughput": _redact_benchmark_text(args.throughput_prompt),
            "stream-throughput": _redact_benchmark_text(args.stream_throughput_prompt),
            "agent-case": [
                {
                    "case_id": agent_case.case_id,
                    "label": agent_case.label,
                    "source": agent_case.source,
                    "prompt_preview": _redact_benchmark_text(agent_case.prompt[:240]),
                }
                for agent_case in selected_agent_cases(
                    case_ids=set(args.agent_case),
                )
            ],
        },
        "iterations": args.iterations,
        "max_tokens": args.max_tokens,
        "first_content_max_tokens": args.first_content_max_tokens,
        "throughput_max_tokens": args.throughput_max_tokens,
        "stream_throughput_max_tokens": args.stream_throughput_max_tokens,
        "agent_case_max_tokens": args.agent_case_max_tokens,
        "timeout_s": args.timeout_s,
        "status_counts": statuses,
        "results": [asdict(result) for result in results],
    }


def write_payload(payload: dict[str, Any], output_dir: Path) -> Path:
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = output_dir / stamp
    run_dir.mkdir(parents=True, exist_ok=True)
    path = run_dir / "model_matrix_benchmark.json"
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def print_table(results: list[CaseResult], *, output_path: Path) -> None:
    print("Roboclaws Model Matrix Benchmark")
    print(f"artifact: {output_path}")
    print(
        f"{'status':8} {'layer':17} {'case':40} {'wire':19} {'ok':>3} "
        f"{'p50':>8} {'tok/s':>9} {'dec/s':>9} detail"
    )
    for result in results:
        detail = result.skipped_reason if result.status == "SKIP" else result.response_model
        if result.status not in {"PASS", "SKIP"}:
            detail = _first_error(result)
        if result.layer == "agent-case" and result.agent_case_id:
            detail = f"{result.agent_case_id} {detail}".strip()
        if result.layer in {"first-content", "stream-throughput"} and result.status == "PASS":
            detail = f"{detail} first={_fmt(result.median_first_content_s)}"
        print(
            f"{result.status:8} {result.layer:17} {result.case_id:40} {result.wire_api:19} "
            f"{result.success_count:>3} {_fmt(result.median_s):>8} "
            f"{_fmt_rate(result.median_output_tokens_per_s):>9} "
            f"{_fmt_rate(result.median_decode_output_tokens_per_s):>9} {detail}"
        )


def _first_error(result: CaseResult) -> str:
    for trial in result.trials:
        if trial.status != "PASS":
            return f"{trial.error_type}: {trial.error}"
    return ""


def _fmt(value: float | None) -> str:
    return "-" if value is None else f"{value:.3f}s"


def _fmt_rate(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    cases = default_cases()
    providers = sorted({case.provider_id for case in cases})
    wires = sorted({case.wire_api for case in cases})
    agent_case_ids = [agent_case.case_id for agent_case in AGENT_BENCHMARK_CASES]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dotenv", default=".env")
    parser.add_argument("--output-dir", type=Path, default=Path("output/dev/model-matrix"))
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument(
        "--first-content-max-tokens",
        type=int,
        default=DEFAULT_FIRST_CONTENT_MAX_TOKENS,
    )
    parser.add_argument("--throughput-max-tokens", type=int, default=DEFAULT_THROUGHPUT_MAX_TOKENS)
    parser.add_argument(
        "--stream-throughput-max-tokens",
        type=int,
        default=DEFAULT_STREAM_THROUGHPUT_MAX_TOKENS,
    )
    parser.add_argument("--agent-case-max-tokens", type=int, default=DEFAULT_AGENT_CASE_MAX_TOKENS)
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--first-content-prompt", default=DEFAULT_FIRST_CONTENT_PROMPT)
    parser.add_argument("--throughput-prompt", default=DEFAULT_THROUGHPUT_PROMPT)
    parser.add_argument("--stream-throughput-prompt", default=DEFAULT_STREAM_THROUGHPUT_PROMPT)
    parser.add_argument("--layer", action="append", choices=list(LAYER_CHOICES), default=[])
    parser.add_argument("--provider", action="append", choices=providers, default=[])
    parser.add_argument("--wire", action="append", choices=wires, default=[])
    parser.add_argument("--case", action="append", default=[])
    parser.add_argument("--agent-case", action="append", choices=agent_case_ids, default=[])
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--list-agent-cases", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--fail-on-fail",
        action="store_true",
        help="Return failure when a selected case fails or is partial.",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Return failure when a selected case is skipped.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.iterations < 1:
        raise SystemExit("--iterations must be >= 1")
    if args.max_tokens < 1:
        raise SystemExit("--max-tokens must be >= 1")
    if args.first_content_max_tokens < 1:
        raise SystemExit("--first-content-max-tokens must be >= 1")
    if args.throughput_max_tokens < 1:
        raise SystemExit("--throughput-max-tokens must be >= 1")
    if args.stream_throughput_max_tokens < 1:
        raise SystemExit("--stream-throughput-max-tokens must be >= 1")
    if args.agent_case_max_tokens < 1:
        raise SystemExit("--agent-case-max-tokens must be >= 1")
    if args.dotenv:
        load_dotenv(Path(args.dotenv))
    cases = default_cases()
    if args.list_cases:
        for case in cases:
            print(f"{case.case_id}\t{case.provider_id}\t{case.wire_api}\t{case.model}")
        return 0
    if args.list_agent_cases:
        for agent_case in AGENT_BENCHMARK_CASES:
            print(f"{agent_case.case_id}\t{agent_case.label}\t{agent_case.source}")
        return 0
    selected = selected_cases(
        cases,
        providers=set(args.provider),
        wires=set(args.wire),
        case_ids=set(args.case),
    )
    unknown_cases = set(args.case) - {case.case_id for case in cases}
    if unknown_cases:
        raise SystemExit(f"unknown benchmark case(s): {', '.join(sorted(unknown_cases))}")
    if not selected:
        raise SystemExit("no benchmark cases selected")
    layers: tuple[BenchmarkLayer, ...] = tuple(args.layer or DEFAULT_LAYERS)

    results: list[CaseResult] = []
    for case in selected:
        for layer in layers:
            agent_cases = selected_agent_cases(case_ids=set(args.agent_case))
            if layer != "agent-case":
                agent_cases = (None,)
            for agent_case in agent_cases:
                results.append(
                    run_case(
                        case,
                        layer=layer,
                        prompt=_prompt_for_layer(args, layer, agent_case=agent_case),
                        iterations=args.iterations,
                        max_tokens=_max_tokens_for_layer(args, layer),
                        timeout_s=args.timeout_s,
                        agent_case=agent_case,
                    )
                )
    payload = result_payload(results, args=args)
    output_path = write_payload(payload, args.output_dir)
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True))
    else:
        print_table(results, output_path=output_path)

    if args.fail_on_fail and any(result.status in {"FAIL", "PARTIAL"} for result in results):
        return 1
    if args.require_all and any(result.status == "SKIP" for result in results):
        return 1
    if all(result.status == "SKIP" for result in results):
        return 1
    return 0


def _max_tokens_for_layer(args: argparse.Namespace, layer: BenchmarkLayer) -> int:
    if layer == "stream-throughput":
        return args.stream_throughput_max_tokens
    if layer == "agent-case":
        return args.agent_case_max_tokens
    if layer == "first-content":
        return args.first_content_max_tokens
    if layer == "throughput":
        return args.throughput_max_tokens
    return args.max_tokens


def _prompt_for_layer(
    args: argparse.Namespace,
    layer: BenchmarkLayer,
    *,
    agent_case: AgentBenchmarkCase | None = None,
) -> str:
    if layer == "stream-throughput":
        return args.stream_throughput_prompt
    if layer == "agent-case":
        if agent_case is None:
            raise ValueError("agent-case layer requires an agent benchmark case")
        return agent_case.prompt
    if layer == "first-content":
        return args.first_content_prompt
    if layer == "throughput":
        return args.throughput_prompt
    return args.prompt


def selected_agent_cases(
    *,
    case_ids: set[str],
) -> tuple[AgentBenchmarkCase, ...]:
    if not case_ids:
        return AGENT_BENCHMARK_CASES
    return tuple(
        agent_case for agent_case in AGENT_BENCHMARK_CASES if agent_case.case_id in case_ids
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""Probe configured model-provider routes with small text-only health checks.

This script is intentionally narrower than Roboclaws product gates: it verifies
that provider endpoints accept a minimal request and return a response. It does
not start simulators, MCP servers, or coding-agent runtimes.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

from roboclaws.agents.provider_registry import (
    WIRE_CHAT_COMPLETIONS,
    WIRE_RESPONSES,
    provider_route_spec,
    route_base_url,
)

DEFAULT_PROMPT = "Health check. Reply exactly ok."
DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS = 256
DEFAULT_CHAT_MAX_TOKENS = 512
DEFAULT_TIMEOUT_S = 30.0

ProbeMode = Literal["agents-sdk", "direct"]


@dataclass(frozen=True)
class ProbeSpec:
    probe_id: str
    mode: ProbeMode
    wire_api: str
    model: str
    api_key_env: str
    base_url: str
    max_tokens: int
    route_id: str = ""
    api_key_alt_env: str = ""
    provider_note: str = ""
    unsupported_reason: str = ""


@dataclass(frozen=True)
class ProbeResult:
    probe_id: str
    mode: ProbeMode
    wire_api: str
    model: str
    status: str
    elapsed_s: float
    output: str = ""
    error_type: str = ""
    error: str = ""
    skipped_reason: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"PASS", "SKIP", "UNSUPPORTED"}


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries from a gitignored dotenv file."""

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


def build_agent_sdk_probes(
    *,
    responses_max_tokens: int = DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
    chat_max_tokens: int = DEFAULT_CHAT_MAX_TOKENS,
) -> list[ProbeSpec]:
    probes: list[ProbeSpec] = []
    for route_id in (
        "codex-env",
        "mify",
        "minimax",
        "mimo-openai-chat",
        "mimo-inside",
        "kimi-openai-chat",
    ):
        route = provider_route_spec(route_id)
        probes.append(
            ProbeSpec(
                probe_id=f"agents-sdk:{route_id}",
                mode="agents-sdk",
                route_id=route_id,
                wire_api=route.wire_api,
                model=route.default_model_id,
                api_key_env=route.api_key_env or "",
                base_url=route_base_url(route),
                max_tokens=(
                    responses_max_tokens if route.wire_api == WIRE_RESPONSES else chat_max_tokens
                ),
            )
        )
    return probes


def build_direct_probes(
    *,
    responses_max_tokens: int = DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
    chat_max_tokens: int = DEFAULT_CHAT_MAX_TOKENS,
) -> list[ProbeSpec]:
    codex = provider_route_spec("codex-env")
    mify = provider_route_spec("mify")
    minimax = provider_route_spec("minimax")
    mimo = provider_route_spec("mimo-openai-chat")
    mimo_inside = provider_route_spec("mimo-inside")

    return [
        _direct_from_route("codex-env", codex, max_tokens=responses_max_tokens),
        _direct_from_route("mify", mify, max_tokens=responses_max_tokens),
        _direct_from_route("minimax-m3", minimax, max_tokens=responses_max_tokens),
        ProbeSpec(
            probe_id="direct:minimax-m27",
            mode="direct",
            route_id="minimax",
            wire_api=WIRE_RESPONSES,
            model="MiniMax-M2.7-highspeed",
            api_key_env=minimax.api_key_env or "",
            base_url=route_base_url(minimax),
            max_tokens=responses_max_tokens,
            provider_note="MiniMax highspeed can spend early tokens on reasoning.",
        ),
        _direct_from_route("mimo-chat", mimo, max_tokens=chat_max_tokens),
        _direct_from_route("mimo-inside", mimo_inside, max_tokens=chat_max_tokens),
        ProbeSpec(
            probe_id="direct:kimi-coding-chat",
            mode="direct",
            route_id="kimi-openai-chat",
            wire_api=WIRE_CHAT_COMPLETIONS,
            model="kimi-k2.7-code",
            api_key_env="KIMI_API_KEY",
            base_url=os.environ.get("KIMI_OPENAI_BASE_URL", "https://api.kimi.com/coding/v1"),
            max_tokens=chat_max_tokens,
            provider_note=(
                "Kimi coding requires a coding-agent User-Agent. Kimi K2.7 Code "
                "runs with provider-side Thinking On; this probe keeps reasoning "
                "content handling and omits temperature because the provider pins "
                "model-specific values."
            ),
        ),
        ProbeSpec(
            probe_id="direct:nvidia-chat",
            mode="direct",
            wire_api=WIRE_CHAT_COMPLETIONS,
            model="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            api_key_env="NV_API_KEY",
            api_key_alt_env="NVIDIA_API_KEY",
            base_url=os.environ.get("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1"),
            max_tokens=chat_max_tokens,
        ),
    ]


def _direct_from_route(name: str, route: Any, *, max_tokens: int) -> ProbeSpec:
    return ProbeSpec(
        probe_id=f"direct:{name}",
        mode="direct",
        route_id=route.route_id,
        wire_api=route.wire_api,
        model=route.default_model_id,
        api_key_env=route.api_key_env or "",
        base_url=route_base_url(route),
        max_tokens=max_tokens,
    )


def run_probe(
    spec: ProbeSpec,
    *,
    prompt: str,
    timeout_s: float,
    force_unsupported: bool = False,
) -> ProbeResult:
    started = time.monotonic()
    api_key = _api_key_for(spec)
    if not api_key:
        return ProbeResult(
            probe_id=spec.probe_id,
            mode=spec.mode,
            wire_api=spec.wire_api,
            model=spec.model,
            status="SKIP",
            elapsed_s=0.0,
            skipped_reason=f"missing {_api_key_label(spec)}",
        )
    if spec.unsupported_reason and not force_unsupported:
        return ProbeResult(
            probe_id=spec.probe_id,
            mode=spec.mode,
            wire_api=spec.wire_api,
            model=spec.model,
            status="UNSUPPORTED",
            elapsed_s=0.0,
            skipped_reason=spec.unsupported_reason,
        )
    try:
        if spec.mode == "agents-sdk":
            output = _run_agents_sdk_probe(
                spec, prompt=prompt, timeout_s=timeout_s, api_key=api_key
            )
        elif spec.probe_id == "direct:kimi-coding-chat":
            output = _run_kimi_coding_probe(
                spec, prompt=prompt, timeout_s=timeout_s, api_key=api_key
            )
        elif spec.wire_api == WIRE_RESPONSES:
            output = _run_responses_probe(spec, prompt=prompt, timeout_s=timeout_s, api_key=api_key)
        elif spec.wire_api == WIRE_CHAT_COMPLETIONS:
            output = _run_chat_probe(spec, prompt=prompt, timeout_s=timeout_s, api_key=api_key)
        else:
            raise RuntimeError(f"unsupported wire API: {spec.wire_api}")
        output = output.strip()
        if not output:
            raise RuntimeError("provider call completed without visible output")
        return ProbeResult(
            probe_id=spec.probe_id,
            mode=spec.mode,
            wire_api=spec.wire_api,
            model=spec.model,
            status="PASS",
            elapsed_s=round(time.monotonic() - started, 3),
            output=output,
        )
    except Exception as exc:  # pragma: no cover - exercised by live provider state
        return ProbeResult(
            probe_id=spec.probe_id,
            mode=spec.mode,
            wire_api=spec.wire_api,
            model=spec.model,
            status="FAIL",
            elapsed_s=round(time.monotonic() - started, 3),
            error_type=exc.__class__.__name__,
            error=str(exc).replace("\n", " ")[:800],
        )


def _api_key_for(spec: ProbeSpec) -> str:
    return os.environ.get(spec.api_key_env) or os.environ.get(spec.api_key_alt_env) or ""


def _api_key_label(spec: ProbeSpec) -> str:
    if spec.api_key_alt_env:
        return f"{spec.api_key_env} or {spec.api_key_alt_env}"
    return spec.api_key_env


def _run_agents_sdk_probe(
    spec: ProbeSpec,
    *,
    prompt: str,
    timeout_s: float,
    api_key: str,
) -> str:
    from agents import (  # type: ignore[import-not-found]
        Agent,
        ModelSettings,
        OpenAIChatCompletionsModel,
        OpenAIResponsesModel,
        Runner,
        set_tracing_disabled,
    )
    from openai import AsyncOpenAI  # type: ignore[import-not-found]

    set_tracing_disabled(True)
    client = AsyncOpenAI(
        api_key=api_key,
        base_url=spec.base_url or None,
        timeout=timeout_s,
        max_retries=0,
    )
    if spec.wire_api == WIRE_RESPONSES:
        model = OpenAIResponsesModel(spec.model, openai_client=client)
    elif spec.wire_api == WIRE_CHAT_COMPLETIONS:
        model = OpenAIChatCompletionsModel(spec.model, openai_client=client)
    else:
        raise RuntimeError(f"unsupported Agents SDK wire API: {spec.wire_api}")
    model_settings_payload: dict[str, Any] = {"max_tokens": spec.max_tokens}
    if spec.route_id == "kimi-openai-chat":
        model_settings_payload["extra_headers"] = {"User-Agent": "claude-code/1.0.0"}
    agent = Agent(
        name=f"roboclaws-provider-health-{spec.route_id or spec.model}",
        instructions="Reply with exactly: ok",
        model=model,
        model_settings=ModelSettings(**model_settings_payload),
    )
    result = Runner.run_sync(agent, prompt, max_turns=2)
    return str(getattr(result, "final_output", "") or "")


def _run_responses_probe(
    spec: ProbeSpec,
    *,
    prompt: str,
    timeout_s: float,
    api_key: str,
) -> str:
    from openai import OpenAI  # type: ignore[import-not-found]

    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": timeout_s, "max_retries": 0}
    if spec.base_url:
        kwargs["base_url"] = spec.base_url
    client = OpenAI(**kwargs)
    response = client.responses.create(
        model=spec.model,
        input=prompt,
        max_output_tokens=spec.max_tokens,
        temperature=0,
    )
    status = str(getattr(response, "status", "") or "")
    output = str(getattr(response, "output_text", "") or "")
    if status and status != "completed":
        raise RuntimeError(
            f"responses status={status} incomplete={getattr(response, 'incomplete_details', None)}"
        )
    if not output:
        raise RuntimeError("responses call completed without output_text")
    return output


def _run_chat_probe(
    spec: ProbeSpec,
    *,
    prompt: str,
    timeout_s: float,
    api_key: str,
) -> str:
    from openai import OpenAI  # type: ignore[import-not-found]

    client = OpenAI(api_key=api_key, base_url=spec.base_url, timeout=timeout_s, max_retries=0)
    response = client.chat.completions.create(
        model=spec.model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=spec.max_tokens,
    )
    output = response.choices[0].message.content or ""
    if not output:
        raise RuntimeError("chat completion returned an empty message content")
    return output


def _run_kimi_coding_probe(
    spec: ProbeSpec,
    *,
    prompt: str,
    timeout_s: float,
    api_key: str,
) -> str:
    import httpx  # type: ignore[import-not-found]

    payload = kimi_coding_payload(prompt=prompt, model=spec.model, max_tokens=spec.max_tokens)
    with httpx.Client(base_url=spec.base_url, timeout=timeout_s) as client:
        response = client.post(
            "/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "User-Agent": "claude-code/1.0.0",
            },
            json=payload,
        )
        response.raise_for_status()
        data = response.json()
    message = data["choices"][0]["message"]
    output = str(message.get("content") or message.get("reasoning_content") or "")
    if not output:
        raise RuntimeError("Kimi coding completion returned empty content")
    return output


def kimi_coding_payload(*, prompt: str, model: str, max_tokens: int) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "stream": False,
    }


def select_probes(args: argparse.Namespace) -> list[ProbeSpec]:
    probes: list[ProbeSpec] = []
    if args.mode in {"agents-sdk", "all"}:
        probes.extend(
            build_agent_sdk_probes(
                responses_max_tokens=args.responses_max_output_tokens,
                chat_max_tokens=args.chat_max_tokens,
            )
        )
    if args.mode in {"direct", "all"}:
        probes.extend(
            build_direct_probes(
                responses_max_tokens=args.responses_max_output_tokens,
                chat_max_tokens=args.chat_max_tokens,
            )
        )
    if args.probe:
        wanted = set(args.probe)
        probes = [probe for probe in probes if probe.probe_id in wanted or probe.route_id in wanted]
    return probes


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.dotenv:
        load_dotenv(Path(args.dotenv))
    probes = select_probes(args)
    results = [
        run_probe(
            probe,
            prompt=args.prompt,
            timeout_s=args.timeout_s,
            force_unsupported=args.force_unsupported,
        )
        for probe in probes
    ]
    if args.json:
        print(json.dumps([asdict(result) for result in results], indent=2, ensure_ascii=False))
    else:
        print_results(results)
    if args.require_all:
        return 1 if any(result.status != "PASS" for result in results) else 0
    return 1 if any(not result.ok for result in results) else 0


def print_results(results: list[ProbeResult]) -> None:
    for result in results:
        base = (
            f"{result.status:4} {result.probe_id:32} "
            f"wire={result.wire_api:16} model={result.model:32} "
            f"elapsed={result.elapsed_s:.2f}s"
        )
        if result.status == "PASS":
            print(f"{base} output={result.output[:80]!r}")
        elif result.status in {"SKIP", "UNSUPPORTED"}:
            print(f"{base} skipped={result.skipped_reason}")
        else:
            print(f"{base} error={result.error_type}: {result.error}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode",
        choices=("all", "agents-sdk", "direct"),
        default="all",
        help="Which probe family to run.",
    )
    parser.add_argument(
        "--probe",
        action="append",
        default=[],
        help="Limit to a probe id or route id. Repeatable.",
    )
    parser.add_argument(
        "--dotenv",
        default=".env",
        help="Dotenv file to load before probing. Pass an empty value to disable.",
    )
    parser.add_argument("--prompt", default=DEFAULT_PROMPT)
    parser.add_argument("--timeout-s", type=float, default=DEFAULT_TIMEOUT_S)
    parser.add_argument(
        "--responses-max-output-tokens",
        type=int,
        default=DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS,
        help=(
            "Default max_output_tokens for Responses probes. Kept above 32 because "
            "some models spend early tokens on reasoning before visible text."
        ),
    )
    parser.add_argument(
        "--chat-max-tokens",
        type=int,
        default=DEFAULT_CHAT_MAX_TOKENS,
        help=(
            "Default max_tokens for Chat Completions probes. Kept above 32 because "
            "some models spend early tokens on reasoning before visible text."
        ),
    )
    parser.add_argument("--json", action="store_true", help="Print JSON results.")
    parser.add_argument(
        "--force-unsupported",
        action="store_true",
        help="Run probes that are normally classified as known unsupported routes.",
    )
    parser.add_argument(
        "--require-all",
        action="store_true",
        help="Fail unless every selected probe passes. CI uses this for planned live routes.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

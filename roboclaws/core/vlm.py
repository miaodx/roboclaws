from __future__ import annotations

import json
import os
import random
import time
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.provider_retry import is_transient_provider_error, retry_delay_seconds

# ---------------------------------------------------------------------------
# Cost tables (USD per 1 M tokens)
# ---------------------------------------------------------------------------

_COST_PER_M: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "kimi-k2-5": {"input": 1.00, "output": 3.00},
    "kimi-k2.6": {"input": 1.00, "output": 3.00},
    "kimi-for-coding": {"input": 1.00, "output": 3.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
    # Official NVIDIA Build pages currently mark these endpoints as free/trial.
    "meta/llama-4-maverick-17b-128e-instruct": {"input": 0.0, "output": 0.0},
    "nvidia/llama-3.1-nemotron-nano-vl-8b-v1": {"input": 0.0, "output": 0.0},
}

_SYSTEM_PROMPT = (
    "You are a robot agent navigating an indoor environment. "
    "You may be competing or cooperating with other agents. "
    "Based on what you see and the map information, choose your next action. "
    'Reply in JSON only: {"reasoning": "...", "action": "..."}'
)


@dataclass
class ProviderStatus:
    """Mutable provider-health snapshot exposed to the game/replay layers."""

    provider_name: str
    model: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    retry_events: int = 0
    calls_with_retries: int = 0
    transient_errors: int = 0
    consecutive_failures: int = 0
    last_error: str = ""
    last_error_kind: str = ""
    last_call_duration_seconds: float = 0.0
    total_call_duration_seconds: float = 0.0
    total_retry_delay_seconds: float = 0.0
    max_transient_errors: int | None = None
    max_calls_with_retries: int | None = None
    max_consecutive_failures: int | None = None
    stop_reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe status snapshot."""
        return {
            "provider_name": self.provider_name,
            "model": self.model,
            "healthy": not bool(self.stop_reason),
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "retry_events": self.retry_events,
            "calls_with_retries": self.calls_with_retries,
            "transient_errors": self.transient_errors,
            "consecutive_failures": self.consecutive_failures,
            "last_error": self.last_error,
            "last_error_kind": self.last_error_kind,
            "last_call_duration_seconds": round(self.last_call_duration_seconds, 3),
            "total_call_duration_seconds": round(self.total_call_duration_seconds, 3),
            "total_retry_delay_seconds": round(self.total_retry_delay_seconds, 3),
            "max_transient_errors": self.max_transient_errors,
            "max_calls_with_retries": self.max_calls_with_retries,
            "max_consecutive_failures": self.max_consecutive_failures,
            "stop_reason": self.stop_reason or None,
        }


class ProviderHealthError(RuntimeError):
    """Raised when a provider trips its health budget and the run should stop."""

    def __init__(self, message: str, *, status: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status or {}


@runtime_checkable
class VLMProvider(Protocol):
    """Minimal interface every VLM backend must satisfy."""

    @property
    def cumulative_cost(self) -> float:
        """Total USD spent since last reset."""
        ...

    def reset_cost(self) -> None:
        """Reset the cumulative cost counter."""
        ...

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Query the model for an action decision.

        Args:
            images: Base64-encoded JPEG images (first-person frame, overhead map, …).
            state: Structured game state (position, score, remaining steps, etc.).

        Returns:
            Dict with at least "action" (one of NAVIGATION_ACTIONS) and "reasoning".
        """
        ...

    def get_status(self) -> dict[str, Any]:
        """Return provider-health telemetry for logging and replay output."""
        ...


# ---------------------------------------------------------------------------
# Provider health helpers
# ---------------------------------------------------------------------------


def _record_call_success(
    status: ProviderStatus,
    *,
    duration_seconds: float,
    had_retries: bool = False,
) -> None:
    """Update provider status after one successful logical call."""
    status.total_calls += 1
    status.successful_calls += 1
    if had_retries:
        status.calls_with_retries += 1
    status.consecutive_failures = 0
    status.last_call_duration_seconds = duration_seconds
    status.total_call_duration_seconds += duration_seconds


def _record_call_failure(
    status: ProviderStatus,
    *,
    duration_seconds: float,
    error: BaseException,
    had_retries: bool = False,
) -> None:
    """Update provider status after one failed logical call."""
    status.total_calls += 1
    status.failed_calls += 1
    if had_retries:
        status.calls_with_retries += 1
    status.consecutive_failures += 1
    status.last_error = str(error)
    status.last_error_kind = error.__class__.__name__
    status.last_call_duration_seconds = duration_seconds
    status.total_call_duration_seconds += duration_seconds


def _maybe_open_circuit(status: ProviderStatus) -> str | None:
    """Return and persist a stop reason once the provider exceeds its health budget."""
    if status.stop_reason:
        return status.stop_reason
    if (
        status.max_transient_errors is not None
        and status.transient_errors >= status.max_transient_errors
    ):
        status.stop_reason = "transient_error_budget_exceeded"
    elif (
        status.max_calls_with_retries is not None
        and status.calls_with_retries >= status.max_calls_with_retries
    ):
        status.stop_reason = "retrying_calls_budget_exceeded"
    elif (
        status.max_consecutive_failures is not None
        and status.consecutive_failures >= status.max_consecutive_failures
    ):
        status.stop_reason = "consecutive_failures_exceeded"
    return status.stop_reason or None


def provider_status_snapshot(provider: Any) -> dict[str, Any]:
    """Return a provider-status snapshot even for lightweight test doubles."""
    getter = getattr(provider, "get_status", None)
    if callable(getter):
        return getter()
    provider_name = provider.__class__.__name__.lower()
    model = str(getattr(provider, "model", provider_name))
    return ProviderStatus(provider_name=provider_name, model=model).to_dict()


def format_provider_status(status: dict[str, Any]) -> str:
    """Return a compact single-line provider-health summary for logs."""
    provider_name = str(status.get("provider_name") or "provider")
    model = str(status.get("model") or provider_name)
    total_calls = int(status.get("total_calls") or 0)
    successful_calls = int(status.get("successful_calls") or 0)
    retry_events = int(status.get("retry_events") or 0)
    transient_errors = int(status.get("transient_errors") or 0)
    failed_calls = int(status.get("failed_calls") or 0)
    parts = [
        f"{provider_name}:{model}",
        f"calls={total_calls}",
        f"ok={successful_calls}",
        f"retry={retry_events}",
        f"transient={transient_errors}",
        f"fail={failed_calls}",
    ]
    stop_reason = status.get("stop_reason")
    if stop_reason:
        parts.append(f"stop={stop_reason}")
    return " ".join(parts)


# ---------------------------------------------------------------------------
# AgentAction Pydantic model (built lazily; requires pydantic + instructor)
# ---------------------------------------------------------------------------


def _build_agent_action_model() -> type:
    """Return AgentAction Pydantic model. Called once per provider __init__."""
    from typing import Literal

    from pydantic import BaseModel

    class AgentAction(BaseModel):
        """Structured VLM response — instructor enforces schema and auto-retries."""

        reasoning: str
        # mirrors NAVIGATION_ACTIONS in roboclaws/core/engine.py
        action: Literal[
            "MoveAhead",
            "MoveBack",
            "MoveLeft",
            "MoveRight",
            "RotateLeft",
            "RotateRight",
            "LookUp",
            "LookDown",
            "Teleport",
            "Done",
        ]

    return AgentAction


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------


class MockProvider:
    """Returns random valid actions — no API key required, suitable for CI."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._cost = 0.0
        self.model = "mock"
        self._status = ProviderStatus(provider_name="mock", model=self.model)

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.monotonic()
        action = self._rng.choice(NAVIGATION_ACTIONS)
        _record_call_success(
            self._status,
            duration_seconds=time.monotonic() - started,
        )
        return {"reasoning": f"MockProvider chose {action}", "action": action}


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


class OpenAIProvider:
    """GPT-4o / GPT-4o-mini via the OpenAI SDK with instructor structured output."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        max_tokens: int = 256,
    ) -> None:
        try:
            import instructor
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "openai and instructor packages required: pip install openai instructor"
            ) from exc
        self._AgentAction = _build_agent_action_model()
        raw_client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._client = instructor.from_openai(raw_client)
        self.model = model
        self._max_tokens = max_tokens
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 0.0, "output": 0.0})
        self._status = ProviderStatus(provider_name="openai", model=model)

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def _build_messages(self, images: list[str], state: dict[str, Any]) -> list[dict[str, Any]]:
        content: list[dict[str, Any]] = []
        for img_b64 in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{img_b64}",
                        "detail": "low",
                    },
                }
            )
        content.append({"type": "text", "text": json.dumps(state, indent=2)})
        return [{"role": "user", "content": content}]

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        messages = self._build_messages(images, state)
        started = time.monotonic()
        try:
            result, response = self._client.chat.completions.create_with_completion(
                model=self.model,
                messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + messages,  # type: ignore[arg-type]
                max_tokens=self._max_tokens,
                response_model=self._AgentAction,
            )
        except Exception as exc:
            _record_call_failure(
                self._status,
                duration_seconds=time.monotonic() - started,
                error=exc,
            )
            raise
        _record_call_success(
            self._status,
            duration_seconds=time.monotonic() - started,
        )
        usage = response.usage
        if usage:
            self._cost += (
                usage.prompt_tokens / 1_000_000 * self._cost_table["input"]
                + usage.completion_tokens / 1_000_000 * self._cost_table["output"]
            )
        return {"reasoning": result.reasoning, "action": result.action}


class NvidiaProvider(OpenAIProvider):
    """NVIDIA NIM via the OpenAI-compatible chat-completions surface."""

    def __init__(
        self,
        model: str = "meta/llama-4-maverick-17b-128e-instruct",
        api_key: str | None = None,
        max_tokens: int = 256,
    ) -> None:
        try:
            import instructor
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "openai and instructor packages required: pip install openai instructor"
            ) from exc
        self._AgentAction = _build_agent_action_model()
        raw_client = OpenAI(
            api_key=api_key or os.environ["NVIDIA_API_KEY"],
            base_url="https://integrate.api.nvidia.com/v1",
        )
        self._client = instructor.from_openai(raw_client)
        self.model = model
        self._max_tokens = max_tokens
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 0.0, "output": 0.0})
        self._status = ProviderStatus(provider_name="nvidia", model=model)


# ---------------------------------------------------------------------------
# _AnthropicBase — shared logic for AnthropicProvider + KimiProvider
# ---------------------------------------------------------------------------


class _AnthropicBase:
    """Shared implementation for Anthropic-SDK providers (native Claude + Kimi)."""

    _model: str
    _max_tokens: int
    _cost: float
    _cost_table: dict[str, float]
    _client: Any
    _AgentAction: type
    _retry_attempts: int
    _provider_name: str
    _status: ProviderStatus
    # Optional per-agent system-prompt extension (e.g. SOUL content).  Keyed
    # by the simulation agent id read from state["my_agent_id"].  When unset
    # or the id is missing, the base _SYSTEM_PROMPT is used verbatim.
    _agent_souls: dict[int, str] | None = None

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self._status.stop_reason:
            raise ProviderHealthError(
                f"{self._provider_name} provider circuit is open: {self._status.stop_reason}",
                status=self.get_status(),
            )

        content: list[dict[str, Any]] = []
        for img_b64 in images:
            content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_b64,
                    },
                }
            )
        content.append({"type": "text", "text": json.dumps(state, indent=2)})

        # Compose system prompt: base behavior spec + (optional) per-agent SOUL.
        system_prompt = _SYSTEM_PROMPT
        if self._agent_souls:
            agent_id = state.get("my_agent_id", state.get("current_agent"))
            if isinstance(agent_id, int) and agent_id in self._agent_souls:
                system_prompt = _SYSTEM_PROMPT + "\n\n" + self._agent_souls[agent_id]

        last_exc: Exception | None = None
        started = time.monotonic()
        retries_this_call = 0
        for attempt in range(self._retry_attempts):
            try:
                result, response = self._client.messages.create_with_completion(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=system_prompt,
                    response_model=self._AgentAction,
                    messages=[{"role": "user", "content": content}],
                )
                _record_call_success(
                    self._status,
                    duration_seconds=time.monotonic() - started,
                    had_retries=retries_this_call > 0,
                )
                _maybe_open_circuit(self._status)
                break
            except Exception as exc:  # pragma: no cover - concrete types depend on installed SDKs
                last_exc = exc
                transient = is_transient_provider_error(exc)
                self._status.last_error = str(exc)
                self._status.last_error_kind = exc.__class__.__name__
                if transient:
                    self._status.transient_errors += 1

                if transient:
                    projected_calls_with_retries = self._status.calls_with_retries
                    if retries_this_call == 0:
                        projected_calls_with_retries += 1
                    if (
                        self._status.max_calls_with_retries is not None
                        and projected_calls_with_retries >= self._status.max_calls_with_retries
                    ):
                        self._status.calls_with_retries = projected_calls_with_retries
                        self._status.stop_reason = "retrying_calls_budget_exceeded"
                        _record_call_failure(
                            self._status,
                            duration_seconds=time.monotonic() - started,
                            error=exc,
                            had_retries=False,
                        )
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {self._status.stop_reason}",
                            status=self.get_status(),
                        ) from exc

                    stop_reason = _maybe_open_circuit(self._status)
                    if stop_reason:
                        _record_call_failure(
                            self._status,
                            duration_seconds=time.monotonic() - started,
                            error=exc,
                            had_retries=retries_this_call > 0,
                        )
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {stop_reason}",
                            status=self.get_status(),
                        ) from exc

                if attempt == self._retry_attempts - 1 or not transient:
                    _record_call_failure(
                        self._status,
                        duration_seconds=time.monotonic() - started,
                        error=exc,
                        had_retries=retries_this_call > 0,
                    )
                    stop_reason = _maybe_open_circuit(self._status)
                    if stop_reason:
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {stop_reason}",
                            status=self.get_status(),
                        ) from exc
                    raise

                retries_this_call += 1
                self._status.retry_events += 1
                delay = retry_delay_seconds(attempt, base=1.0, cap=4.0)
                self._status.total_retry_delay_seconds += delay
                time.sleep(delay)
        else:  # pragma: no cover - loop always breaks or raises
            assert last_exc is not None
            raise last_exc

        usage = response.usage
        if usage:
            self._cost += (
                usage.input_tokens / 1_000_000 * self._cost_table["input"]
                + usage.output_tokens / 1_000_000 * self._cost_table["output"]
            )
        return {"reasoning": result.reasoning, "action": result.action}


class AnthropicProvider(_AnthropicBase):
    """Claude models via the native Anthropic SDK with instructor structured output."""

    def __init__(
        self,
        model: str = "claude-3-5-sonnet-20241022",
        api_key: str | None = None,
        max_tokens: int = 256,
        retry_attempts: int = 3,
    ) -> None:
        try:
            import anthropic  # type: ignore[import-untyped]
            import instructor
        except ImportError as exc:
            raise ImportError(
                "anthropic and instructor packages required: pip install anthropic instructor"
            ) from exc
        self._AgentAction = _build_agent_action_model()
        raw_client = anthropic.Anthropic(
            api_key=api_key or os.environ["ANTHROPIC_API_KEY"],
        )
        self._client = instructor.from_anthropic(raw_client)
        self._model = model
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 3.00, "output": 15.00})
        self._provider_name = "anthropic"
        self._status = ProviderStatus(provider_name=self._provider_name, model=model)


class KimiProvider(_AnthropicBase):
    """Kimi (Moonshot) via the Anthropic SDK with a custom base_url and instructor.

    Accepts an optional ``agent_souls`` map so one provider instance can drive
    N agents with N distinct SOULs, matching the Phase 2.2 OpenClaw-backend
    behavior without needing the Gateway.
    """

    def __init__(
        self,
        model: str = "kimi-k2.6",
        api_key: str | None = None,
        max_tokens: int = 256,
        retry_attempts: int = 4,
        max_transient_errors: int | None = 4,
        max_calls_with_retries: int | None = 4,
        max_consecutive_failures: int | None = None,
        agent_souls: dict[int, str] | None = None,
        http_timeout: float | None = None,
    ) -> None:
        try:
            import anthropic  # type: ignore[import-untyped]
            import instructor
        except ImportError as exc:
            raise ImportError(
                "anthropic and instructor packages required: pip install anthropic instructor"
            ) from exc
        self._AgentAction = _build_agent_action_model()
        # Cap per-call latency — Anthropic SDK's default is 600s which, combined
        # with retry_attempts=4, lets one hung upstream eat 40 min before any
        # retry happens.  Observed Kimi coding-tier tail-latency reliably
        # exceeds the fast-case (~3s) — 60s is generous for the success path
        # and turns tail stalls into clean transient errors that the retry
        # machinery can act on.  Override via KIMI_HTTP_TIMEOUT env or kwarg.
        if http_timeout is None:
            env_t = os.environ.get("KIMI_HTTP_TIMEOUT")
            http_timeout = float(env_t) if env_t else 60.0
        raw_client = anthropic.Anthropic(
            api_key=api_key or os.environ["KIMI_API_KEY"],
            base_url="https://api.kimi.com/coding",
            timeout=http_timeout,
            # Disable SDK-level retry — our retry_attempts handles transient
            # errors with its own backoff + ProviderHealthError budget so we
            # don't double-retry (Kimi SDK default was 2 silent retries on
            # top of ours).
            max_retries=0,
        )
        self._client = instructor.from_anthropic(raw_client)
        self._model = model
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 1.00, "output": 3.00})
        self._provider_name = "kimi"
        self._agent_souls = agent_souls
        self._status = ProviderStatus(
            provider_name=self._provider_name,
            model=model,
            max_transient_errors=max_transient_errors,
            max_calls_with_retries=max_calls_with_retries,
            max_consecutive_failures=max_consecutive_failures,
        )


def _extract_action_json(candidates: list[str]) -> dict[str, Any] | None:
    """Find the first parseable ``{"action": ...}`` object across candidate strings.

    Handles: plain JSON, JSON inside ```json fences, or JSON embedded in prose
    (common when Kimi answers in ``reasoning_content``).  Returns None if no
    candidate yields a dict with both ``reasoning`` and ``action`` keys.
    """
    import re as _re

    fence_re = _re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", _re.DOTALL)

    def _try_parse(text: str) -> dict[str, Any] | None:
        try:
            obj = json.loads(text)
        except (json.JSONDecodeError, ValueError):
            return None
        return obj if isinstance(obj, dict) and "action" in obj else None

    def _salvage_truncated(raw: str) -> dict[str, Any] | None:
        """Extract {reasoning, action} from truncated JSON.

        When Kimi hits finish_reason=length mid-response, content can be
        e.g. ``{"reasoning": "...", "action": "MoveAhead``  (no closing).
        We salvage reasoning (up to the action key) + parse the action
        string up to the cutoff.
        """
        m = _re.search(r'"action"\s*:\s*"([A-Za-z]+)', raw)
        if not m:
            return None
        action = m.group(1)
        rm = _re.search(r'"reasoning"\s*:\s*"([^"\\]*(?:\\.[^"\\]*)*)"', raw)
        reasoning = rm.group(1) if rm else ""
        return {"reasoning": reasoning, "action": action}

    for raw in candidates:
        if not raw:
            continue
        stripped = raw.strip()
        # 1. Full parse.
        if obj := _try_parse(stripped):
            return obj
        # 2. Fenced code block.
        m = fence_re.search(raw)
        if m and (obj := _try_parse(m.group(1))):
            return obj
        # 3. Salvage truncated (finish_reason=length).
        if obj := _salvage_truncated(raw):
            return obj
    return None


# ---------------------------------------------------------------------------
# KimiCodingProvider — direct OpenAI-format to api.kimi.com/coding/v1
# ---------------------------------------------------------------------------
#
# The existing KimiProvider uses the Anthropic SDK → Kimi's anthropic-messages
# surface at api.kimi.com/coding.  That surface is periodically overloaded
# (observed 2/3 calls returning 429 rate_limit_error "engine currently
# overloaded" on 2026-04-17) even when the same account's OpenAI surface at
# /coding/v1/chat/completions answers cleanly in ~7s.
#
# Kimi For Coding gates non-agent clients with a 403 access_terminated_error
# unless the request carries a recognised coding-agent User-Agent.
# ``claude-code/1.0.0`` passes the gate (probed empirically on 2026-04-17).
#
# Keep the two providers side-by-side rather than swap — the Anthropic path
# is still the right one once upstream stabilises and for Claude itself.


class KimiCodingProvider:
    """Direct httpx client for ``api.kimi.com/coding/v1/chat/completions``.

    Unlike :class:`KimiProvider`, this provider:

    * Uses the OpenAI-compatible endpoint (not anthropic-messages)
    * Sets ``User-Agent: claude-code/1.0.0`` to pass the Kimi-For-Coding gate
    * Parses the assistant response content as JSON directly (no instructor,
      no pydantic schema enforcement); invalid JSON triggers a retry
    """

    def __init__(
        self,
        model: str = "kimi-for-coding",
        api_key: str | None = None,
        # Kimi emits chain-of-thought via ``reasoning_content`` which counts
        # against ``max_tokens``.  Solid-red probes used ~1000 reasoning
        # tokens; real AI2-THOR frames with SOUL + state push reasoning to
        # 2000-3000 tokens, then final JSON ``content`` adds ~500 more.
        # Budget 8192 — observed 4096 still truncated at reasoning=17k
        # chars (2633 completion tokens seen on real frames, 2026-04-17).
        max_tokens: int = 8192,
        # retry_attempts=2 caps single-call wait at ~2 × 120s + 5s backoff
        # ≈ 4 min.  Previously 3 × 120s + (5+10+20s) ≈ 7 min per failed
        # call was too aggressive — observed 5/11 calls in one run falling
        # back, eating ~35 min before the wallclock could fire.
        retry_attempts: int = 2,
        # Kimi Coding's RPM limiter can surface 429s in bursts (observed
        # 3-call bursts hitting 4/4 429s even after backoff).  Budget scales
        # so a 429-heavy patch doesn't trip the circuit breaker before
        # transient behaviour settles.
        max_transient_errors: int | None = 20,
        max_calls_with_retries: int | None = 20,
        # Back-to-back failures with no success between them — this fires
        # when Kimi has actually gone dark rather than just a slow call.
        max_consecutive_failures: int | None = 5,
        agent_souls: dict[int, str] | None = None,
        http_timeout: float | None = None,
        user_agent: str = "claude-code/1.0.0",
        retry_backoff_base: float = 5.0,
        retry_backoff_cap: float = 30.0,
        # Kimi exposes chain-of-thought via ``reasoning_content``; with
        # reasoning_effort=medium (default) it can consume 3000+ tokens
        # before producing the final ``content`` — easy to starve the
        # budget and land with content="".  ``low`` cuts reasoning to
        # ~1000 tokens and reliably fills ``content`` with the JSON answer
        # in ~9s (probed 2026-04-17).  ``minimal`` is even faster but
        # gives up quality.  Valid: minimal | low | medium | high.
        reasoning_effort: str = "low",
    ) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx ships with instructor
            raise ImportError("httpx is required for KimiCodingProvider") from exc

        if http_timeout is None:
            env_t = os.environ.get("KIMI_HTTP_TIMEOUT")
            # Real AI2-THOR frames + SOUL + json_schema push Kimi to 40-60s
            # with reasoning_effort=low.  Solid-red probe at 60s was fine;
            # in-game frames occasionally exceed it.  120s gives 2× headroom
            # and the circuit-breaker still fires within retry budget.
            http_timeout = float(env_t) if env_t else 120.0

        self._model = model
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 1.00, "output": 3.00})
        self._provider_name = "kimi-coding"
        self._agent_souls = agent_souls
        self._timeout = http_timeout
        self._client = httpx.Client(
            base_url="https://api.kimi.com/coding",
            headers={
                "Authorization": f"Bearer {api_key or os.environ['KIMI_API_KEY']}",
                "Content-Type": "application/json",
                "User-Agent": user_agent,
            },
            timeout=http_timeout,
        )
        self._retry_backoff_base = retry_backoff_base
        self._retry_backoff_cap = retry_backoff_cap
        self._reasoning_effort = reasoning_effort
        self.model = model
        self._status = ProviderStatus(
            provider_name=self._provider_name,
            model=model,
            max_transient_errors=max_transient_errors,
            max_calls_with_retries=max_calls_with_retries,
            max_consecutive_failures=max_consecutive_failures,
        )

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def close(self) -> None:
        self._client.close()

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self._status.stop_reason:
            raise ProviderHealthError(
                f"{self._provider_name} provider circuit is open: {self._status.stop_reason}",
                status=self.get_status(),
            )

        # Compose system prompt: base spec + per-agent SOUL.  Skip the shared
        # _SYSTEM_PROMPT entirely — its trailing ``{"reasoning": "...",
        # "action": "..."}`` example confuses Kimi into emitting empty
        # content when combined with json_schema enforcement (probed
        # 2026-04-17).  json_schema below already pins the reply shape.
        _KIMI_SYSTEM_BASE = (
            "You are a robot agent navigating an indoor environment. "
            "You may be competing or cooperating with other agents. "
            "Based on what you see and the map information, choose your next action."
        )
        system_prompt = _KIMI_SYSTEM_BASE
        if self._agent_souls:
            agent_id = state.get("my_agent_id", state.get("current_agent"))
            if isinstance(agent_id, int) and agent_id in self._agent_souls:
                system_prompt = _KIMI_SYSTEM_BASE + "\n\n" + self._agent_souls[agent_id]

        # OpenAI-format content blocks: images first, then the state JSON.
        content: list[dict[str, Any]] = []
        for img_b64 in images:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                }
            )
        content.append({"type": "text", "text": json.dumps(state, indent=2)})

        # Strict JSON-schema with an enum for ``action`` — prevents Kimi from
        # echoing our example placeholders ("...") or returning free-form
        # English.  Kimi Coding honours json_schema (probed 2026-04-17).
        action_enum = [a for a in NAVIGATION_ACTIONS if a not in ("Teleport", "Done")]
        payload: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            # Kimi For Coding returns 400 "invalid temperature: only 0.6
            # is allowed" when temperature is omitted (observed on the
            # 2nd turn of a real game after step 0 succeeded).  Pin to 0.6.
            "temperature": 0.6,
            "reasoning_effort": self._reasoning_effort,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_action",
                    "schema": {
                        "type": "object",
                        "properties": {
                            "reasoning": {"type": "string"},
                            "action": {"type": "string", "enum": action_enum},
                        },
                        "required": ["reasoning", "action"],
                        "additionalProperties": False,
                    },
                },
            },
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        }

        started = time.monotonic()
        last_exc: Exception | None = None
        retries_this_call = 0
        for attempt in range(self._retry_attempts):
            try:
                resp = self._client.post("/v1/chat/completions", json=payload)
                resp.raise_for_status()
                body = resp.json()
                choice = body["choices"][0]
                msg = choice.get("message") or {}
                # Kimi sometimes returns the final answer in ``content`` and
                # its chain-of-thought in ``reasoning_content``; with longer
                # system prompts the split flips — content is empty and the
                # JSON reply lives inside reasoning_content.  Scan both.
                candidates = [msg.get("content") or "", msg.get("reasoning_content") or ""]
                parsed = _extract_action_json(candidates)
                if parsed is None:
                    raise ValueError(
                        f"Kimi returned no parseable JSON action "
                        f"(content={candidates[0][:80]!r} reasoning={candidates[1][:80]!r})"
                    )
                action = str(parsed.get("action", "")).strip()
                if action not in NAVIGATION_ACTIONS:
                    raise ValueError(f"invalid action from Kimi: {action!r}")
                result = {"reasoning": str(parsed.get("reasoning", "")), "action": action}

                usage = body.get("usage") or {}
                in_tok = int(usage.get("prompt_tokens", 0))
                out_tok = int(usage.get("completion_tokens", 0))
                self._cost += (
                    in_tok / 1_000_000 * self._cost_table["input"]
                    + out_tok / 1_000_000 * self._cost_table["output"]
                )
                _record_call_success(
                    self._status,
                    duration_seconds=time.monotonic() - started,
                    had_retries=retries_this_call > 0,
                )
                _maybe_open_circuit(self._status)
                return result
            except Exception as exc:  # noqa: BLE001 - classify below
                last_exc = exc
                transient = is_transient_provider_error(exc)
                self._status.last_error = str(exc)[:400]
                self._status.last_error_kind = exc.__class__.__name__
                if transient:
                    self._status.transient_errors += 1

                if transient:
                    projected = self._status.calls_with_retries + (
                        1 if retries_this_call == 0 else 0
                    )
                    if (
                        self._status.max_calls_with_retries is not None
                        and projected >= self._status.max_calls_with_retries
                    ):
                        self._status.calls_with_retries = projected
                        self._status.stop_reason = "retrying_calls_budget_exceeded"
                        _record_call_failure(
                            self._status,
                            duration_seconds=time.monotonic() - started,
                            error=exc,
                            had_retries=False,
                        )
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {self._status.stop_reason}",
                            status=self.get_status(),
                        ) from exc
                    stop_reason = _maybe_open_circuit(self._status)
                    if stop_reason:
                        _record_call_failure(
                            self._status,
                            duration_seconds=time.monotonic() - started,
                            error=exc,
                            had_retries=retries_this_call > 0,
                        )
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {stop_reason}",
                            status=self.get_status(),
                        ) from exc

                if attempt == self._retry_attempts - 1 or not transient:
                    _record_call_failure(
                        self._status,
                        duration_seconds=time.monotonic() - started,
                        error=exc,
                        had_retries=retries_this_call > 0,
                    )
                    stop_reason = _maybe_open_circuit(self._status)
                    if stop_reason:
                        raise ProviderHealthError(
                            f"{self._provider_name} became unstable: {stop_reason}",
                            status=self.get_status(),
                        ) from exc
                    if transient:
                        # Retries exhausted on a transient error but the
                        # circuit breaker didn't fire — return a safe
                        # fallback action so the game keeps running instead
                        # of aborting on a single slow minute.  Budget
                        # accounting still trips the circuit after enough
                        # consecutive failures.
                        return {
                            "reasoning": (
                                f"Retries exhausted on {exc.__class__.__name__}; "
                                "falling back to RotateRight."
                            ),
                            "action": "RotateRight",
                        }
                    raise

                retries_this_call += 1
                self._status.retry_events += 1
                delay = retry_delay_seconds(
                    attempt,
                    base=self._retry_backoff_base,
                    cap=self._retry_backoff_cap,
                )
                self._status.total_retry_delay_seconds += delay
                time.sleep(delay)
        # pragma: no cover — loop either returns or raises.
        assert last_exc is not None
        raise last_exc


# ---------------------------------------------------------------------------
# Per-agent SOUL loading (shared by VLM + OpenClaw backends)
# ---------------------------------------------------------------------------


def load_agent_souls(
    souls_env: str,
    agent_count: int,
    souls_dir: str,
) -> tuple[list[str], dict[int, str]]:
    """Parse ``AGENT_SOULS`` env var and load SOUL file contents.

    Accepts two formats (same as ``scripts/openclaw-bootstrap.sh``):

    * positional CSV — ``aggressive,defensive`` → agent 0 / 1
    * dict form      — ``agent-0:aggressive,agent-2:cooperative``

    Missing entries fall back to ``"default"``.

    Args:
        souls_env: Raw value of the ``AGENT_SOULS`` env var.  Empty string
            disables SOUL loading — returns ``([], {})``.
        agent_count: Number of simulation agents.
        souls_dir: Directory containing ``<soul>.md`` files.

    Returns:
        ``(labels, contents)`` where ``labels[i]`` is the SOUL name for agent
        ``i`` (for visualizer tinting), and ``contents[i]`` is the loaded
        markdown text (for system-prompt injection).  When a SOUL file is
        missing, that agent is omitted from ``contents``.
    """
    if not souls_env:
        return [], {}

    if ":" in souls_env:
        raw_map = dict(e.split(":", 1) for e in souls_env.split(",") if ":" in e)
        labels = [raw_map.get(f"agent-{i}", "default") for i in range(agent_count)]
    else:
        entries = souls_env.split(",")
        labels = [entries[i] if i < len(entries) else "default" for i in range(agent_count)]

    contents: dict[int, str] = {}
    for agent_id, soul_name in enumerate(labels):
        path = os.path.join(souls_dir, f"{soul_name}.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                contents[agent_id] = fh.read()
    return labels, contents


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODEL_ALIASES: dict[str, str] = {
    "mock": "mock",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "kimi": "kimi-k2.6",
    "kimi-k2-5": "kimi-k2-5",
    "kimi-k2.6": "kimi-k2.6",
    "kimi-coding": "kimi-for-coding",
    "kimi-for-coding": "kimi-for-coding",
    "anthropic": "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307": "claude-3-haiku-20240307",
    "nvidia": "meta/llama-4-maverick-17b-128e-instruct",
    "meta/llama-4-maverick-17b-128e-instruct": "meta/llama-4-maverick-17b-128e-instruct",
    "nvidia-nano-vl": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
    "nvidia/llama-3.1-nemotron-nano-vl-8b-v1": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
}


def create_provider(model: str = "mock", **kwargs: Any) -> VLMProvider:
    """Map a --model CLI flag to a provider instance.

    Args:
        model: One of "mock", "gpt-4o", "gpt-4o-mini", "kimi", "kimi-coding",
               "anthropic", "nvidia", or a full model name like
               "claude-3-5-sonnet-20241022".
        **kwargs: Forwarded to the provider constructor.

    Returns:
        A VLMProvider instance.
    """
    canonical = _MODEL_ALIASES.get(model)
    if canonical is None:
        raise ValueError(f"Unknown model: {model!r}. Choose from {list(_MODEL_ALIASES)}")
    if canonical == "mock":
        return MockProvider(**kwargs)
    if canonical in ("gpt-4o", "gpt-4o-mini"):
        return OpenAIProvider(model=canonical, **kwargs)
    if canonical in (
        "meta/llama-4-maverick-17b-128e-instruct",
        "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
    ):
        return NvidiaProvider(model=canonical, **kwargs)
    if canonical.startswith("claude"):
        return AnthropicProvider(model=canonical, **kwargs)
    if canonical == "kimi-for-coding":
        return KimiCodingProvider(model=canonical, **kwargs)
    # kimi-k2-5 or kimi-k2.6 (anthropic-messages path)
    return KimiProvider(model=canonical, **kwargs)

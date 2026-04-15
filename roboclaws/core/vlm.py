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
    "kimi-k2.6-code-preview": {"input": 1.00, "output": 3.00},
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
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

        last_exc: Exception | None = None
        started = time.monotonic()
        retries_this_call = 0
        for attempt in range(self._retry_attempts):
            try:
                result, response = self._client.messages.create_with_completion(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=_SYSTEM_PROMPT,
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
    """Kimi (Moonshot) via the Anthropic SDK with a custom base_url and instructor."""

    def __init__(
        self,
        model: str = "kimi-k2.6-code-preview",
        api_key: str | None = None,
        max_tokens: int = 256,
        retry_attempts: int = 4,
        max_transient_errors: int | None = 4,
        max_calls_with_retries: int | None = 4,
        max_consecutive_failures: int | None = None,
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
            api_key=api_key or os.environ["KIMI_API_KEY"],
            base_url="https://api.kimi.com/coding",
        )
        self._client = instructor.from_anthropic(raw_client)
        self._model = model
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 1.00, "output": 3.00})
        self._provider_name = "kimi"
        self._status = ProviderStatus(
            provider_name=self._provider_name,
            model=model,
            max_transient_errors=max_transient_errors,
            max_calls_with_retries=max_calls_with_retries,
            max_consecutive_failures=max_consecutive_failures,
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODEL_ALIASES: dict[str, str] = {
    "mock": "mock",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "kimi": "kimi-k2.6-code-preview",
    "kimi-k2-5": "kimi-k2-5",
    "kimi-k2.6-code-preview": "kimi-k2.6-code-preview",
    "anthropic": "claude-3-5-sonnet-20241022",
    "claude-3-5-sonnet-20241022": "claude-3-5-sonnet-20241022",
    "claude-3-haiku-20240307": "claude-3-haiku-20240307",
}


def create_provider(model: str = "mock", **kwargs: Any) -> VLMProvider:
    """Map a --model CLI flag to a provider instance.

    Args:
        model: One of "mock", "gpt-4o", "gpt-4o-mini", "kimi", "anthropic",
               or a full model name like "claude-3-5-sonnet-20241022".
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
    if canonical.startswith("claude"):
        return AnthropicProvider(model=canonical, **kwargs)
    # kimi-k2-5 or kimi-k2.6-code-preview
    return KimiProvider(model=canonical, **kwargs)

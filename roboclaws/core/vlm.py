from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

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
    # MiMo token-plan pricing TBD — set to 0 until confirmed.
    # mimo-v2-omni: vision + tool-calls (probed 2026-04-23)
    # mimo-v2.5-pro / mimo-v2.5: text + tool-calls only (no vision)
    "mimo-v2-omni": {"input": 0.0, "output": 0.0},
    "mimo-v2.5-pro": {"input": 0.0, "output": 0.0},
    "mimo-v2.5": {"input": 0.0, "output": 0.0},
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
# Provider re-exports (implementations live in roboclaws/core/providers/)
# ---------------------------------------------------------------------------

from roboclaws.core.providers.anthropic import AnthropicProvider, _AnthropicBase  # noqa: E402
from roboclaws.core.providers.kimi import KimiCodingProvider, KimiProvider  # noqa: E402
from roboclaws.core.providers.mock import MockProvider  # noqa: E402
from roboclaws.core.providers.openai import (  # noqa: E402
    MimoProvider,
    NvidiaProvider,
    OpenAIProvider,
)

__all__ = [
    "_AnthropicBase",
    "AnthropicProvider",
    "KimiCodingProvider",
    "KimiProvider",
    "MimoProvider",
    "MockProvider",
    "NvidiaProvider",
    "OpenAIProvider",
]

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
    # MiMo: only mimo-omni is exposed for direct VLM use (vision + tool-calls).
    # mimo-v2.5-pro / mimo-v2.5 are text-only; use OpenClaw IMAGE_MODEL delegation instead.
    "mimo-omni": "mimo-v2-omni",
    "mimo-v2-omni": "mimo-v2-omni",
    "mimo-v2.5-pro": "mimo-v2.5-pro",
    "mimo-v2.5": "mimo-v2.5",
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
    if canonical in ("mimo-v2-omni", "mimo-v2.5-pro", "mimo-v2.5"):
        return MimoProvider(model=canonical, **kwargs)
    if canonical.startswith("claude"):
        return AnthropicProvider(model=canonical, **kwargs)
    if canonical == "kimi-for-coding":
        return KimiCodingProvider(model=canonical, **kwargs)
    # kimi-k2-5 or kimi-k2.6 (anthropic-messages path)
    return KimiProvider(model=canonical, **kwargs)

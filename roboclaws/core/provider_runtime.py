from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

from roboclaws.agents.provider_registry import cost_table_by_model

_COST_PER_M: dict[str, dict[str, float]] = cost_table_by_model()

_SYSTEM_PROMPT = (
    "You are a robot agent navigating an indoor environment. "
    "You may be competing or cooperating with other agents. "
    "Based on what you see and the map information, choose your next action. "
    'Reply in JSON only: {"reasoning": "...", "action": "..."}'
)

NAVIGATION_ACTIONS: tuple[str, ...] = (
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
)
SAFE_FALLBACK_ACTION = "RotateRight"
ALLOWED_NAVIGATION_ACTIONS = NAVIGATION_ACTIONS
_CODE_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


@dataclass(frozen=True)
class ActionDecision:
    reasoning: str
    action: str

    def to_dict(self) -> dict[str, str]:
        return {"reasoning": self.reasoning, "action": self.action}


def action_decision_from_fields(reasoning: Any, action: Any) -> ActionDecision:
    """Return a validated provider decision from already-split fields."""
    reasoning_text = str(reasoning or "")
    action_text = str(action or "").strip()
    if action_text not in ALLOWED_NAVIGATION_ACTIONS:
        action_text = SAFE_FALLBACK_ACTION
    return ActionDecision(reasoning=reasoning_text, action=action_text)


def fallback_action_decision(raw: Any) -> ActionDecision:
    """Return the safe fallback decision while preserving debug context."""
    return ActionDecision(
        reasoning=str(raw or "").strip()[:500],
        action=SAFE_FALLBACK_ACTION,
    )


def parse_action_decision(raw_content: Any) -> ActionDecision:
    """Parse and validate a model/Gateway decision."""
    content = str(raw_content or "")
    stripped = _CODE_FENCE_RE.sub("", content).strip()
    if not stripped.startswith("{"):
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1 and end > start:
            stripped = stripped[start : end + 1]

    try:
        parsed = json.loads(stripped)
    except json.JSONDecodeError:
        return fallback_action_decision(content)

    if not isinstance(parsed, dict) or "action" not in parsed:
        return fallback_action_decision(content)
    return action_decision_from_fields(parsed.get("reasoning", ""), parsed.get("action", ""))


@dataclass
class ProviderStatus:
    """Mutable provider-health snapshot exposed to replay and report layers."""

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
    """Minimal interface every model backend must satisfy."""

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
        """Query the model for an action decision."""
        ...

    def get_status(self) -> dict[str, Any]:
        """Return provider-health telemetry for logging and replay output."""
        ...


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


def _build_agent_action_model() -> type:
    """Return AgentAction Pydantic model. Called once per provider __init__."""
    from typing import Literal

    from pydantic import BaseModel

    class AgentAction(BaseModel):
        """Structured model response; instructor enforces schema and auto-retries."""

        reasoning: str
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


def load_agent_souls(
    souls_env: str,
    agent_count: int,
    souls_dir: str,
) -> tuple[list[str], dict[int, str]]:
    """Parse ``AGENT_SOULS`` env var and load SOUL file contents."""
    if not souls_env:
        return [], {}

    labels = _parse_soul_labels(souls_env, agent_count)

    contents: dict[int, str] = {}
    for agent_id, soul_name in enumerate(labels):
        path = os.path.join(souls_dir, f"{soul_name}.md")
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                contents[agent_id] = fh.read()
    return labels, contents


def _parse_soul_labels(souls_env: str, agent_count: int) -> list[str]:
    if ":" in souls_env:
        raw_map = dict(entry.split(":", 1) for entry in souls_env.split(",") if ":" in entry)
        return [raw_map.get(f"agent-{idx}", "default") for idx in range(agent_count)]

    entries = souls_env.split(",")
    return [entries[idx] if idx < len(entries) else "default" for idx in range(agent_count)]

from __future__ import annotations

import json
import os
import random
import time
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
    "claude-3-5-sonnet-20241022": {"input": 3.00, "output": 15.00},
    "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
}

_SYSTEM_PROMPT = (
    "You are a robot agent navigating an indoor environment. "
    "You may be competing or cooperating with other agents. "
    "Based on what you see and the map information, choose your next action. "
    'Reply in JSON only: {"reasoning": "...", "action": "..."}'
)

# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


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

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        action = self._rng.choice(NAVIGATION_ACTIONS)
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

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

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
        result, response = self._client.chat.completions.create_with_completion(
            model=self.model,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + messages,  # type: ignore[arg-type]
            max_tokens=self._max_tokens,
            response_model=self._AgentAction,
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

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
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
        for attempt in range(self._retry_attempts):
            try:
                result, response = self._client.messages.create_with_completion(
                    model=self._model,
                    max_tokens=self._max_tokens,
                    system=_SYSTEM_PROMPT,
                    response_model=self._AgentAction,
                    messages=[{"role": "user", "content": content}],
                )
                break
            except Exception as exc:  # pragma: no cover - concrete types depend on installed SDKs
                last_exc = exc
                if attempt == self._retry_attempts - 1 or not is_transient_provider_error(exc):
                    raise
                time.sleep(retry_delay_seconds(attempt, base=1.0, cap=4.0))
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


class KimiProvider(_AnthropicBase):
    """Kimi (Moonshot) via the Anthropic SDK with a custom base_url and instructor."""

    def __init__(
        self,
        model: str = "kimi-k2-5",
        api_key: str | None = None,
        max_tokens: int = 256,
        retry_attempts: int = 4,
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


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODEL_ALIASES: dict[str, str] = {
    "mock": "mock",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "kimi": "kimi-k2-5",
    "kimi-k2-5": "kimi-k2-5",
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
    # kimi-k2-5
    return KimiProvider(model=canonical, **kwargs)

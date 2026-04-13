from __future__ import annotations

import json
import os
import random
from typing import Any, Protocol, runtime_checkable

from roboclaws.core.engine import NAVIGATION_ACTIONS

# ---------------------------------------------------------------------------
# Cost tables (USD per 1 M tokens)
# ---------------------------------------------------------------------------

_COST_PER_M: dict[str, dict[str, float]] = {
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "kimi-k2-5": {"input": 1.00, "output": 3.00},
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
    """GPT-4o / GPT-4o-mini via the official OpenAI SDK."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: str | None = None,
        max_tokens: int = 256,
    ) -> None:
        try:
            from openai import OpenAI  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("openai package required: pip install openai") from exc
        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
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
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + messages,  # type: ignore[arg-type]
            max_tokens=self._max_tokens,
            response_format={"type": "json_object"},
        )
        usage = response.usage
        if usage:
            self._cost += (
                usage.prompt_tokens / 1_000_000 * self._cost_table["input"]
                + usage.completion_tokens / 1_000_000 * self._cost_table["output"]
            )
        raw = response.choices[0].message.content or ""
        return _parse_response(raw)


# ---------------------------------------------------------------------------
# KimiProvider
# ---------------------------------------------------------------------------


class KimiProvider:
    """Kimi (Moonshot) via the Anthropic SDK with a custom base_url."""

    def __init__(
        self,
        model: str = "kimi-k2-5",
        api_key: str | None = None,
        max_tokens: int = 256,
    ) -> None:
        try:
            import anthropic  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError("anthropic package required: pip install anthropic") from exc
        self._client = anthropic.Anthropic(
            api_key=api_key or os.environ["KIMI_API_KEY"],
            base_url="https://api.kimi.com/coding",
        )
        self.model = model
        self._max_tokens = max_tokens
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 1.00, "output": 3.00})

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

        response = self._client.messages.create(
            model=self.model,
            max_tokens=self._max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )
        usage = response.usage
        if usage:
            self._cost += (
                usage.input_tokens / 1_000_000 * self._cost_table["input"]
                + usage.output_tokens / 1_000_000 * self._cost_table["output"]
            )
        raw = response.content[0].text if response.content else ""
        return _parse_response(raw)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_response(raw: str) -> dict[str, Any]:
    """Parse model output; fall back to a random action on failure."""
    raw = raw.strip()
    # Strip markdown code fences if present
    if raw.startswith("```"):
        lines = raw.splitlines()
        raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
    try:
        result = json.loads(raw)
        if isinstance(result, dict) and result.get("action") in NAVIGATION_ACTIONS:
            return result
    except (json.JSONDecodeError, KeyError):
        pass
    fallback = random.choice(NAVIGATION_ACTIONS)
    return {"reasoning": f"Parse error; falling back to {fallback}", "action": fallback}


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_MODEL_ALIASES: dict[str, str] = {
    "mock": "mock",
    "gpt-4o": "gpt-4o",
    "gpt-4o-mini": "gpt-4o-mini",
    "kimi": "kimi-k2-5",
    "kimi-k2-5": "kimi-k2-5",
}


def create_provider(model: str = "mock", **kwargs: Any) -> VLMProvider:
    """Map a --model CLI flag to a provider instance.

    Args:
        model: One of "mock", "gpt-4o", "gpt-4o-mini", "kimi".
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
    # kimi-k2-5
    return KimiProvider(model=canonical, **kwargs)

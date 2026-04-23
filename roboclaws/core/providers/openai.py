from __future__ import annotations

import json
import os
import time
from typing import Any

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.vlm import (
    _COST_PER_M,
    _SYSTEM_PROMPT,
    ProviderStatus,
    _build_agent_action_model,
    _record_call_failure,
    _record_call_success,
)


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


class MimoProvider(NvidiaProvider):
    """MiMo via the OpenAI-compatible chat-completions surface (token-plan).

    Uses forced tool_choice instead of instructor so the model emits proper
    tool_calls JSON rather than its native <tool_call> XML format.
    max_tokens defaults to 2048 to accommodate the model's reasoning chain.
    """

    def __init__(
        self,
        model: str = "mimo-v2-omni",
        api_key: str | None = None,
        max_tokens: int = 2048,
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
            api_key=api_key or os.environ["MIMO_TP_KEY"],
            base_url="https://token-plan-cn.xiaomimimo.com/v1",
        )
        self._raw_client = raw_client
        self._client = instructor.from_openai(raw_client)
        self.model = model
        self._max_tokens = max_tokens
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, {"input": 0.0, "output": 0.0})
        self._status = ProviderStatus(provider_name="mimo", model=model)

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        messages = self._build_messages(images, state)
        tool_schema = {
            "type": "function",
            "function": {
                "name": "AgentAction",
                "parameters": self._AgentAction.model_json_schema(),
            },
        }
        started = time.monotonic()
        try:
            response = self._raw_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": _SYSTEM_PROMPT}] + messages,  # type: ignore[arg-type]
                max_tokens=self._max_tokens,
                tools=[tool_schema],
                tool_choice={"type": "function", "function": {"name": "AgentAction"}},
            )
        except Exception as exc:
            _record_call_failure(
                self._status,
                duration_seconds=time.monotonic() - started,
                error=exc,
            )
            raise
        _record_call_success(self._status, duration_seconds=time.monotonic() - started)

        msg = response.choices[0].message
        tool_calls = msg.tool_calls or []
        if tool_calls:
            args = json.loads(tool_calls[0].function.arguments)
            action = args.get("action", "MoveAhead")
            reasoning = args.get("reasoning", getattr(msg, "reasoning_content", "") or "")
        else:
            content = msg.content or ""
            try:
                parsed = json.loads(content)
                action = parsed.get("action", "MoveAhead")
                reasoning = parsed.get("reasoning", "")
            except json.JSONDecodeError:
                action = "MoveAhead"
                reasoning = content[:200]

        if action not in NAVIGATION_ACTIONS:
            action = "MoveAhead"

        usage = response.usage
        if usage:
            self._cost += (
                usage.prompt_tokens / 1_000_000 * self._cost_table["input"]
                + usage.completion_tokens / 1_000_000 * self._cost_table["output"]
            )
        return {"reasoning": reasoning, "action": action}

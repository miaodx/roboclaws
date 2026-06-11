from __future__ import annotations

import os
import time
from typing import Any

from roboclaws.core.provider_safety import (
    build_provider_status,
    handle_provider_exception,
    raise_if_provider_circuit_open,
)
from roboclaws.core.vlm import (
    _COST_PER_M,
    _SYSTEM_PROMPT,
    ProviderStatus,
    _build_agent_action_model,
    _maybe_open_circuit,
    _record_call_success,
    action_decision_from_fields,
)


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
        raise_if_provider_circuit_open(provider_name=self._provider_name, status=self._status)

        import json

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
                decision = handle_provider_exception(
                    provider_name=self._provider_name,
                    status=self._status,
                    exc=exc,
                    started=started,
                    attempt=attempt,
                    retry_attempts=self._retry_attempts,
                    retries_this_call=retries_this_call,
                    retry_backoff_base=1.0,
                    retry_backoff_cap=4.0,
                )
                if not decision.should_retry:
                    raise

                retries_this_call += 1
                time.sleep(decision.delay_seconds or 0.0)
        else:  # pragma: no cover - loop always breaks or raises
            assert last_exc is not None
            raise last_exc

        usage = response.usage
        if usage:
            self._cost += (
                usage.input_tokens / 1_000_000 * self._cost_table["input"]
                + usage.output_tokens / 1_000_000 * self._cost_table["output"]
            )
        return action_decision_from_fields(result.reasoning, result.action).to_dict()


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
        self._status = build_provider_status(provider_name=self._provider_name, model=model)

from __future__ import annotations

import os
import time
from typing import Any

from roboclaws.core.provider_retry import is_transient_provider_error, retry_delay_seconds
from roboclaws.core.vlm import (
    _COST_PER_M,
    _SYSTEM_PROMPT,
    ProviderHealthError,
    ProviderStatus,
    _build_agent_action_model,
    _maybe_open_circuit,
    _record_call_failure,
    _record_call_success,
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
        if self._status.stop_reason:
            raise ProviderHealthError(
                f"{self._provider_name} provider circuit is open: {self._status.stop_reason}",
                status=self.get_status(),
            )

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

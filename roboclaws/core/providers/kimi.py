from __future__ import annotations

import json
import os
import time
from typing import Any

from roboclaws.core.action_decision import (
    action_decision_from_fields,
    fallback_action_decision,
    parse_action_decision,
)
from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.provider_retry import is_transient_provider_error, retry_delay_seconds
from roboclaws.core.providers.anthropic import _AnthropicBase
from roboclaws.core.vlm import (
    _COST_PER_M,
    ProviderHealthError,
    ProviderStatus,
    _build_agent_action_model,
    _maybe_open_circuit,
    _record_call_failure,
    _record_call_success,
)

_KIMI_HTTP_TIMEOUT_ENV = "KIMI_HTTP_TIMEOUT"
_KIMI_DEFAULT_COST = {"input": 1.00, "output": 3.00}
_KIMI_SYSTEM_BASE = (
    "You are a robot agent navigating an indoor environment. "
    "You may be competing or cooperating with other agents. "
    "Based on what you see and the map information, choose your next action."
)


def _kimi_timeout(default: float) -> float:
    env_timeout = os.environ.get(_KIMI_HTTP_TIMEOUT_ENV)
    return float(env_timeout) if env_timeout else default


def _provider_status(
    provider_name: str,
    model: str,
    *,
    max_transient_errors: int | None,
    max_calls_with_retries: int | None,
    max_consecutive_failures: int | None,
) -> ProviderStatus:
    return ProviderStatus(
        provider_name=provider_name,
        model=model,
        max_transient_errors=max_transient_errors,
        max_calls_with_retries=max_calls_with_retries,
        max_consecutive_failures=max_consecutive_failures,
    )


def _build_content(images: list[str], state: dict[str, Any]) -> list[dict[str, Any]]:
    content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
        }
        for img_b64 in images
    ]
    content.append({"type": "text", "text": json.dumps(state, indent=2)})
    return content


def _kimi_system_prompt(state: dict[str, Any], agent_souls: dict[int, str] | None) -> str:
    if not agent_souls:
        return _KIMI_SYSTEM_BASE

    agent_id = state.get("my_agent_id", state.get("current_agent"))
    if isinstance(agent_id, int) and agent_id in agent_souls:
        return _KIMI_SYSTEM_BASE + "\n\n" + agent_souls[agent_id]
    return _KIMI_SYSTEM_BASE


def _kimi_response_format() -> dict[str, Any]:
    action_enum = [action for action in NAVIGATION_ACTIONS if action not in ("Teleport", "Done")]
    return {
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
    }


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


class KimiProvider(_AnthropicBase):
    """Kimi (Moonshot) via the Anthropic SDK with optional per-agent SOUL prompts."""

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
        if http_timeout is None:
            http_timeout = _kimi_timeout(60.0)
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
        self._cost_table = _COST_PER_M.get(model, _KIMI_DEFAULT_COST)
        self._provider_name = "kimi"
        self._agent_souls = agent_souls
        self._status = _provider_status(
            self._provider_name,
            model,
            max_transient_errors=max_transient_errors,
            max_calls_with_retries=max_calls_with_retries,
            max_consecutive_failures=max_consecutive_failures,
        )


class KimiCodingProvider:
    """Direct httpx client for ``api.kimi.com/coding/v1/chat/completions``."""

    def __init__(
        self,
        model: str = "kimi-for-coding",
        api_key: str | None = None,
        max_tokens: int = 8192,
        retry_attempts: int = 2,
        max_transient_errors: int | None = 20,
        max_calls_with_retries: int | None = 20,
        max_consecutive_failures: int | None = 5,
        agent_souls: dict[int, str] | None = None,
        http_timeout: float | None = None,
        user_agent: str = "claude-code/1.0.0",
        retry_backoff_base: float = 5.0,
        retry_backoff_cap: float = 30.0,
        reasoning_effort: str = "low",
    ) -> None:
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - httpx ships with instructor
            raise ImportError("httpx is required for KimiCodingProvider") from exc

        if http_timeout is None:
            # Real AI2-THOR frames + SOUL + json_schema push Kimi to 40-60s
            # with reasoning_effort=low.  Solid-red probe at 60s was fine;
            # in-game frames occasionally exceed it.  120s gives 2× headroom
            # and the circuit-breaker still fires within retry budget.
            http_timeout = _kimi_timeout(120.0)

        self._model = model
        self._max_tokens = max_tokens
        self._retry_attempts = retry_attempts
        self._cost = 0.0
        self._cost_table = _COST_PER_M.get(model, _KIMI_DEFAULT_COST)
        self._provider_name = "kimi-coding"
        self._agent_souls = agent_souls
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
        self._status = _provider_status(
            self._provider_name,
            model,
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

    def _build_payload(self, images: list[str], state: dict[str, Any]) -> dict[str, Any]:
        return {
            "model": self._model,
            "max_tokens": self._max_tokens,
            # Kimi For Coding returns 400 "invalid temperature: only 0.6
            # is allowed" when temperature is omitted (observed on the
            # 2nd turn of a real game after step 0 succeeded).  Pin to 0.6.
            "temperature": 0.6,
            "reasoning_effort": self._reasoning_effort,
            "response_format": _kimi_response_format(),
            "messages": [
                {"role": "system", "content": _kimi_system_prompt(state, self._agent_souls)},
                {"role": "user", "content": _build_content(images, state)},
            ],
        }

    def _parse_response(self, body: dict[str, Any]) -> dict[str, str]:
        choice = body["choices"][0]
        msg = choice.get("message") or {}
        # Kimi sometimes returns the final answer in ``content`` and its
        # chain-of-thought in ``reasoning_content``; with longer system
        # prompts the split flips. Scan both before falling back.
        candidates = [msg.get("content") or "", msg.get("reasoning_content") or ""]
        parsed = _extract_action_json(candidates)
        if parsed is None:
            return parse_action_decision("\n".join(candidates)).to_dict()
        return action_decision_from_fields(
            parsed.get("reasoning", ""), parsed.get("action", "")
        ).to_dict()

    def _record_usage(self, usage: dict[str, Any]) -> None:
        self._cost += (
            int(usage.get("prompt_tokens", 0)) / 1_000_000 * self._cost_table["input"]
            + int(usage.get("completion_tokens", 0)) / 1_000_000 * self._cost_table["output"]
        )

    def _fallback_action(self, error: Exception) -> dict[str, str]:
        return fallback_action_decision(
            f"Retries exhausted on {error.__class__.__name__}; falling back to RotateRight."
        ).to_dict()

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

        payload = self._build_payload(images, state)
        started = time.monotonic()
        last_exc: Exception | None = None
        retries_this_call = 0
        for attempt in range(self._retry_attempts):
            try:
                resp = self._client.post("/v1/chat/completions", json=payload)
                resp.raise_for_status()
                body = resp.json()
                result = self._parse_response(body)
                self._record_usage(body.get("usage") or {})
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
                        return self._fallback_action(exc)
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

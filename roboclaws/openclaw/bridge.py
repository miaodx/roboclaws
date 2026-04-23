"""VLMProvider adapter for the OpenClaw Gateway — Phase 2.1 bridge.

The low-level HTTP transport (:class:`OpenClawBridge`, dataclasses, helpers)
lives in :mod:`roboclaws.openclaw.transport`.  This module exposes the
high-level :class:`OpenClawProvider` (a VLMProvider-compatible wrapper) and
the :func:`build_openclaw_provider_or_die` convenience factory.

All public names from transport are re-exported here so existing callers that
``from roboclaws.openclaw.bridge import OpenClawBridge`` keep working.
"""

from __future__ import annotations

import os
import time
from typing import Any

import numpy as np

from roboclaws.core.turn_metrics import round_seconds
from roboclaws.core.vlm import ProviderStatus
from roboclaws.openclaw.transport import (
    _DEFAULT_AGENT_PREFIX,
    _RETRY_ATTEMPTS,
    OpenClawBridge,
    OpenClawUnavailable,
    RunResult,
    TranscriptMessage,
    _extract_content,
    _extract_text_blocks,
    _is_terminal_stop_reason,
    _ndarray_to_data_url,
    _parse_action,
    _SessionStoreCapture,
    _StartRunCapture,
    _timestamp_to_epoch_seconds,
    _warn_invalid_action,
    _warn_malformed,
)

__all__ = [
    "OpenClawBridge",
    "OpenClawProvider",
    "OpenClawUnavailable",
    "RunResult",
    "TranscriptMessage",
    "_SessionStoreCapture",
    "_StartRunCapture",
    "_extract_content",
    "_extract_text_blocks",
    "_is_terminal_stop_reason",
    "_ndarray_to_data_url",
    "_parse_action",
    "_timestamp_to_epoch_seconds",
    "_warn_invalid_action",
    "_warn_malformed",
    "build_openclaw_provider_or_die",
]


# ---------------------------------------------------------------------------
# VLMProvider-compatible adapter
# ---------------------------------------------------------------------------


class OpenClawProvider:
    """Drop-in :class:`~roboclaws.core.vlm.VLMProvider` backed by :class:`OpenClawBridge`.

    Wraps the bridge so the demo's main loop can treat the Gateway like any
    other VLM provider.  No filesystem exchange — frames flow inline as
    base64 data URLs.

    Cost tracking is not available for an external Gateway; ``cumulative_cost``
    is always ``0.0``.
    """

    def __init__(
        self,
        bridge: OpenClawBridge | None = None,
        **bridge_kwargs: Any,
    ) -> None:
        self._bridge = bridge or OpenClawBridge(**bridge_kwargs)
        self._owns_bridge = bridge is None
        self._cost = 0.0
        self._step = 0
        self.model = f"openclaw:{self._bridge._agent_prefix}*"
        self._status = ProviderStatus(provider_name="openclaw", model=self.model)
        self._last_turn_metrics: dict[str, Any] = {}

    # -- VLMProvider protocol -----------------------------------------

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_last_turn_metrics(self) -> dict[str, Any]:
        return dict(self._last_turn_metrics)

    def get_action(
        self,
        images: list[np.ndarray],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one turn to the Gateway for the requested agent.

        Parameters
        ----------
        images:
            Ordered list of numpy RGB frames.  ``images[0]`` is treated as
            the first-person frame; ``images[1]`` (if present) as the
            overhead map.  Missing or empty entries fall back to a 1×1
            black placeholder so the named agent still gets a valid payload.
        state:
            Structured game state.  ``state["my_agent_id"]`` (preferred) or
            ``state["current_agent"]`` routes the turn to the right agent.
        """
        agent_id = int(state.get("my_agent_id", state.get("current_agent", 0)))
        step_idx = int(state.get("step", self._step))

        frame = images[0] if images else _placeholder_frame()
        overhead = images[1] if len(images) > 1 else _placeholder_frame()

        started = time.monotonic()
        last_exc: Exception | None = None
        retry_delay_seconds_this_call = 0.0
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                result = self._bridge.step(
                    agent_id=agent_id,
                    frame=frame,
                    overhead=overhead,
                    state=state,
                    step_idx=step_idx,
                )
            except OpenClawUnavailable as exc:
                last_exc = exc
                self._status.last_error = str(exc)
                self._status.last_error_kind = exc.__class__.__name__
                is_timeout = "read timeout" in str(exc).lower()
                if is_timeout and attempt < _RETRY_ATTEMPTS - 1:
                    self._status.transient_errors += 1
                    self._status.retry_events += 1
                    delay = min(2.0 * (2**attempt), 8.0)
                    self._status.total_retry_delay_seconds += delay
                    retry_delay_seconds_this_call += delay
                    time.sleep(delay)
                    continue
                self._status.total_calls += 1
                self._status.failed_calls += 1
                self._status.consecutive_failures += 1
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                    },
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                        "error_kind": exc.__class__.__name__,
                    },
                }
                if is_timeout:
                    raise OpenClawUnavailable(
                        f"Model unavailable: openclaw/{self._bridge._agent_prefix}{agent_id} "
                        f"timed out on {_RETRY_ATTEMPTS} consecutive attempts — last: {exc}"
                    ) from exc
                raise
            except Exception as exc:
                self._status.total_calls += 1
                self._status.failed_calls += 1
                self._status.consecutive_failures += 1
                self._status.last_error = str(exc)
                self._status.last_error_kind = exc.__class__.__name__
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                    },
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                        "error_kind": exc.__class__.__name__,
                    },
                }
                raise
            else:
                self._status.total_calls += 1
                self._status.successful_calls += 1
                self._status.consecutive_failures = 0
                self._status.last_call_duration_seconds = time.monotonic() - started
                self._status.total_call_duration_seconds += self._status.last_call_duration_seconds
                bridge_metrics = self._bridge.get_last_step_metrics()
                bridge_timings = (
                    bridge_metrics.get("timings", {}) if isinstance(bridge_metrics, dict) else {}
                )
                bridge_payload = (
                    bridge_metrics.get("payload", {}) if isinstance(bridge_metrics, dict) else {}
                )
                self._last_turn_metrics = {
                    "timings": {
                        "openclaw_provider_call_seconds": round_seconds(time.monotonic() - started),
                        "openclaw_retry_delay_seconds": round_seconds(
                            retry_delay_seconds_this_call
                        ),
                        **bridge_timings,
                    },
                    "payload": bridge_payload,
                    "provider": {
                        "attempts": attempt + 1,
                        "retries_this_call": attempt,
                    },
                }
                self._step += 1
                return result
        # Defensive: loop should always return or raise above.
        assert last_exc is not None
        raise last_exc

    # -- Convenience --------------------------------------------------

    def ping(self, agent_id: int = 0) -> str:
        """Expose :meth:`OpenClawBridge.ping` for precondition probes."""
        return self._bridge.ping(agent_id)

    # -- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        if self._owns_bridge:
            self._bridge.close()


def _placeholder_frame() -> np.ndarray:
    """1×1 black RGB frame used when the caller omits an image."""
    return np.zeros((1, 1, 3), dtype=np.uint8)


def build_openclaw_provider_or_die(
    *,
    gateway_url: str | None = None,
    agent_count: int,
) -> "OpenClawProvider":
    """Construct an :class:`OpenClawProvider` and fail fast if the Gateway is unreachable.

    Reads ``OPENCLAW_GATEWAY_TOKEN`` and ``OPENCLAW_AGENT_PREFIX`` from the
    environment (no CLI flags — tokens must not appear in shell history).

    Parameters
    ----------
    gateway_url:
        Override the Gateway base URL.  Defaults to the ``OPENCLAW_GATEWAY_URL``
        env var, then ``http://localhost:18789``.
    agent_count:
        Number of simulation agents; used to compose the hint message when
        the Gateway is unreachable.

    Raises
    ------
    SystemExit
        With a human-readable hint when the Gateway is unreachable, the token
        is expired, or the named agent hasn't been registered.
    """
    kwargs: dict[str, Any] = {}
    if gateway_url is not None:
        kwargs["gateway_url"] = gateway_url
    agent_prefix = os.environ.get("OPENCLAW_AGENT_PREFIX", _DEFAULT_AGENT_PREFIX)
    kwargs["agent_prefix"] = agent_prefix

    provider = OpenClawProvider(**kwargs)
    try:
        provider.ping(agent_id=0)
    except OpenClawUnavailable as exc:
        provider.close()
        msg = str(exc)
        if "401" in msg or "bearer token" in msg.lower():
            hint = (
                "Token likely expired — re-capture with: TOKEN=$(./scripts/openclaw-bootstrap.sh)"
            )
        elif "400" in msg and "Invalid model" in msg:
            hint = (
                f"Agent 0 not registered — re-run with AGENTS={agent_count}: "
                "TOKEN=$(AGENTS={agent_count} ./scripts/openclaw-bootstrap.sh)"
            )
        else:
            hint = (
                "Gateway not running — check `docker ps` and re-run ./scripts/openclaw-bootstrap.sh"
            )
        raise SystemExit(f"Gateway precondition failed: {exc}\nHint: {hint}") from exc
    return provider

"""VLMProvider adapter for the OpenClaw Gateway — Phase 2.1 bridge.

The low-level HTTP transport (:class:`OpenClawBridge`, dataclasses, helpers)
lives in :mod:`roboclaws.openclaw.transport`.  This module exposes the
high-level :class:`OpenClawProvider` (a VLMProvider-compatible wrapper) and
the :func:`build_openclaw_provider_or_die` convenience factory.

The long-standing public compatibility exports are kept here
(``OpenClawBridge``, ``RunResult``, and ``TranscriptMessage``). Transcript
recovery internals live in :mod:`roboclaws.openclaw.transcript_recovery` and
are intentionally not re-exported from this provider adapter.
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
)

__all__ = [
    "OpenClawBridge",
    "OpenClawProvider",
    "OpenClawUnavailable",
    "RunResult",
    "TranscriptMessage",
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

    def _record_call_outcome(
        self,
        *,
        started: float,
        retry_delay_seconds: float,
        attempt: int,
        error: Exception | None = None,
        bridge_metrics: dict[str, Any] | None = None,
    ) -> None:
        duration = time.monotonic() - started
        self._status.total_calls += 1
        self._status.last_call_duration_seconds = duration
        self._status.total_call_duration_seconds += duration

        timings: dict[str, Any] = {
            "openclaw_provider_call_seconds": round_seconds(duration),
            "openclaw_retry_delay_seconds": round_seconds(retry_delay_seconds),
        }
        provider_metrics: dict[str, Any] = {
            "attempts": attempt + 1,
            "retries_this_call": attempt,
        }
        metrics: dict[str, Any] = {"timings": timings, "provider": provider_metrics}

        if error is None:
            self._status.successful_calls += 1
            self._status.consecutive_failures = 0
            payload: dict[str, Any] = {}
            if isinstance(bridge_metrics, dict):
                bridge_timings = bridge_metrics.get("timings", {})
                if isinstance(bridge_timings, dict):
                    timings.update(bridge_timings)
                bridge_payload = bridge_metrics.get("payload", {})
                if isinstance(bridge_payload, dict):
                    payload = bridge_payload
            metrics["payload"] = payload
        else:
            self._status.failed_calls += 1
            self._status.consecutive_failures += 1
            self._status.last_error = str(error)
            self._status.last_error_kind = error.__class__.__name__
            provider_metrics["error_kind"] = error.__class__.__name__

        self._last_turn_metrics = metrics

    def get_action(
        self,
        images: list[np.ndarray],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        """Route one turn to the Gateway for the requested agent.

        Parameters
        ----------
        images:
            Ordered list of numpy RGB frames for the normal navigation
            contract: first-person frame, structured map-v2 overhead, and
            chase camera.  Partial image sets are rejected so the runtime does
            not silently downgrade back to the older two-image prompt shape.
        state:
            Structured game state.  ``state["my_agent_id"]`` (preferred) or
            ``state["current_agent"]`` routes the turn to the right agent.
        """
        if len(images) != 3:
            raise ValueError(f"OpenClaw navigation requires exactly 3 images, got {len(images)}.")
        agent_id = int(state.get("my_agent_id", state.get("current_agent", 0)))
        step_idx = int(state.get("step", self._step))

        started = time.monotonic()
        retry_delay_seconds_this_call = 0.0
        for attempt in range(_RETRY_ATTEMPTS):
            try:
                result = self._bridge.step(
                    agent_id=agent_id,
                    frame=images[0],
                    map_v2=images[1],
                    chase=images[2],
                    state=state,
                    step_idx=step_idx,
                )
            except OpenClawUnavailable as exc:
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
                self._record_call_outcome(
                    started=started,
                    retry_delay_seconds=retry_delay_seconds_this_call,
                    attempt=attempt,
                    error=exc,
                )
                if is_timeout:
                    raise OpenClawUnavailable(
                        f"Model unavailable: openclaw/{self._bridge._agent_prefix}{agent_id} "
                        f"timed out on {_RETRY_ATTEMPTS} consecutive attempts — last: {exc}"
                    ) from exc
                raise
            except Exception as exc:
                self._record_call_outcome(
                    started=started,
                    retry_delay_seconds=retry_delay_seconds_this_call,
                    attempt=attempt,
                    error=exc,
                )
                raise
            else:
                self._record_call_outcome(
                    started=started,
                    retry_delay_seconds=retry_delay_seconds_this_call,
                    attempt=attempt,
                    bridge_metrics=self._bridge.get_last_step_metrics(),
                )
                self._step += 1
                return result
        raise AssertionError("OpenClawProvider retry loop exhausted unexpectedly")

    # -- Convenience --------------------------------------------------

    def ping(self, agent_id: int = 0) -> str:
        """Expose :meth:`OpenClawBridge.ping` for precondition probes."""
        return self._bridge.ping(agent_id)

    # -- Lifecycle ----------------------------------------------------

    def close(self) -> None:
        if self._owns_bridge:
            self._bridge.close()


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
                "Token likely expired — re-capture with: "
                "TOKEN=$(./scripts/openclaw/openclaw-bootstrap.sh)"
            )
        elif "400" in msg and "Invalid model" in msg:
            hint = (
                f"Agent 0 not registered — re-run with AGENTS={agent_count}: "
                "TOKEN=$(AGENTS={agent_count} ./scripts/openclaw/openclaw-bootstrap.sh)"
            )
        else:
            hint = (
                "Gateway not running — check `docker ps` and re-run "
                "./scripts/openclaw/openclaw-bootstrap.sh"
            )
        raise SystemExit(f"Gateway precondition failed: {exc}\nHint: {hint}") from exc
    return provider

from __future__ import annotations

import time

import pytest

from roboclaws.core.provider_safety import handle_provider_exception
from roboclaws.core.vlm import ProviderHealthError, ProviderStatus


class RateLimitError(Exception):
    pass


def test_handle_provider_exception_returns_retry_decision_for_transient_error() -> None:
    status = ProviderStatus(
        provider_name="kimi",
        model="mock",
        max_transient_errors=3,
        max_calls_with_retries=3,
    )
    started = time.monotonic()

    decision = handle_provider_exception(
        provider_name="kimi",
        status=status,
        exc=RateLimitError("engine is currently overloaded"),
        started=started,
        attempt=0,
        retry_attempts=2,
        retries_this_call=0,
        retry_backoff_base=1.0,
        retry_backoff_cap=4.0,
    )

    assert decision.should_retry is True
    assert decision.transient is True
    assert decision.delay_seconds == 1.0
    assert status.retry_events == 1
    assert status.transient_errors == 1


def test_handle_provider_exception_opens_retry_budget_circuit() -> None:
    status = ProviderStatus(
        provider_name="kimi",
        model="mock",
        max_transient_errors=None,
        max_calls_with_retries=1,
    )

    with pytest.raises(ProviderHealthError, match="retrying_calls_budget_exceeded"):
        handle_provider_exception(
            provider_name="kimi",
            status=status,
            exc=RateLimitError("engine is currently overloaded"),
            started=time.monotonic(),
            attempt=0,
            retry_attempts=2,
            retries_this_call=0,
            retry_backoff_base=1.0,
            retry_backoff_cap=4.0,
        )

    assert status.stop_reason == "retrying_calls_budget_exceeded"
    assert status.failed_calls == 1

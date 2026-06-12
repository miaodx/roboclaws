from __future__ import annotations

import time
from dataclasses import dataclass

from roboclaws.core.provider_retry import is_transient_provider_error, retry_delay_seconds
from roboclaws.core.provider_runtime import (
    ProviderHealthError,
    ProviderStatus,
    _maybe_open_circuit,
    _record_call_failure,
)


@dataclass(frozen=True)
class ProviderExceptionDecision:
    """Decision returned after one provider exception has been accounted for."""

    transient: bool
    should_retry: bool
    delay_seconds: float | None = None


def raise_if_provider_circuit_open(
    *,
    provider_name: str,
    status: ProviderStatus,
) -> None:
    """Raise when the provider's safety circuit has already opened."""
    if status.stop_reason:
        raise ProviderHealthError(
            f"{provider_name} provider circuit is open: {status.stop_reason}",
            status=status.to_dict(),
        )


def build_provider_status(
    provider_name: str,
    model: str,
    *,
    max_transient_errors: int | None = None,
    max_calls_with_retries: int | None = None,
    max_consecutive_failures: int | None = None,
) -> ProviderStatus:
    """Return a provider status snapshot configured with safety budgets."""
    return ProviderStatus(
        provider_name=provider_name,
        model=model,
        max_transient_errors=max_transient_errors,
        max_calls_with_retries=max_calls_with_retries,
        max_consecutive_failures=max_consecutive_failures,
    )


def handle_provider_exception(
    *,
    provider_name: str,
    status: ProviderStatus,
    exc: Exception,
    started: float,
    attempt: int,
    retry_attempts: int,
    retries_this_call: int,
    retry_backoff_base: float,
    retry_backoff_cap: float,
) -> ProviderExceptionDecision:
    """Account for a provider exception and return whether the caller should retry."""
    transient = is_transient_provider_error(exc)
    status.last_error = str(exc)[:400]
    status.last_error_kind = exc.__class__.__name__
    if transient:
        status.transient_errors += 1

    if transient:
        projected = status.calls_with_retries + (1 if retries_this_call == 0 else 0)
        if status.max_calls_with_retries is not None and projected >= status.max_calls_with_retries:
            status.calls_with_retries = projected
            status.stop_reason = "retrying_calls_budget_exceeded"
            _record_call_failure(
                status,
                duration_seconds=time.monotonic() - started,
                error=exc,
                had_retries=False,
            )
            raise ProviderHealthError(
                f"{provider_name} became unstable: {status.stop_reason}",
                status=status.to_dict(),
            ) from exc

        stop_reason = _maybe_open_circuit(status)
        if stop_reason:
            _record_call_failure(
                status,
                duration_seconds=time.monotonic() - started,
                error=exc,
                had_retries=retries_this_call > 0,
            )
            raise ProviderHealthError(
                f"{provider_name} became unstable: {stop_reason}",
                status=status.to_dict(),
            ) from exc

    if attempt == retry_attempts - 1 or not transient:
        _record_call_failure(
            status,
            duration_seconds=time.monotonic() - started,
            error=exc,
            had_retries=retries_this_call > 0,
        )
        stop_reason = _maybe_open_circuit(status)
        if stop_reason:
            raise ProviderHealthError(
                f"{provider_name} became unstable: {stop_reason}",
                status=status.to_dict(),
            ) from exc
        return ProviderExceptionDecision(transient=transient, should_retry=False)

    status.retry_events += 1
    delay = retry_delay_seconds(attempt, base=retry_backoff_base, cap=retry_backoff_cap)
    status.total_retry_delay_seconds += delay
    return ProviderExceptionDecision(
        transient=transient,
        should_retry=True,
        delay_seconds=delay,
    )

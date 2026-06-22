from __future__ import annotations

import pytest

from roboclaws.core.provider_retry import (
    is_transient_provider_error,
    retry_delay_seconds,
    transient_status_code,
)


class _Response:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


class _StatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"status={status_code}")
        self.status_code = status_code


class _ResponseStatusError(Exception):
    def __init__(self, status_code: int) -> None:
        super().__init__(f"response={status_code}")
        self.response = _Response(status_code)


class RateLimitError(Exception):
    pass


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_StatusError(429), 429),
        (_ResponseStatusError(503), 503),
        (Exception("no status"), None),
    ],
)
def test_transient_status_code_reads_sdk_status_shapes(
    exc: BaseException,
    expected: int | None,
) -> None:
    assert transient_status_code(exc) == expected


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (ConnectionError("connection reset"), True),
        (RateLimitError("busy"), True),
        (_StatusError(429), True),
        (_ResponseStatusError(503), True),
        (Exception("The engine is currently overloaded"), True),
        (ValueError("bad request"), False),
    ],
)
def test_is_transient_provider_error_classifies_retryable_failures(
    exc: BaseException,
    expected: bool,
) -> None:
    assert is_transient_provider_error(exc) is expected


@pytest.mark.parametrize(
    ("attempt_index", "expected_delay"),
    [
        (0, 2.0),
        (1, 4.0),
        (2, 8.0),
        (5, 8.0),
    ],
)
def test_retry_delay_seconds_is_capped_exponential_backoff(
    attempt_index: int,
    expected_delay: float,
) -> None:
    assert retry_delay_seconds(attempt_index) == expected_delay


def test_retry_delay_seconds_rejects_negative_attempt_index():
    try:
        retry_delay_seconds(-1)
    except ValueError as exc:
        assert "attempt_index" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")

from __future__ import annotations

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


def test_transient_status_code_prefers_exception_status_code():
    assert transient_status_code(_StatusError(429)) == 429


def test_transient_status_code_reads_response_status_code():
    assert transient_status_code(_ResponseStatusError(503)) == 503


def test_transient_status_code_returns_none_when_missing():
    assert transient_status_code(Exception("no status")) is None


def test_is_transient_provider_error_for_connection_error():
    assert is_transient_provider_error(ConnectionError("connection reset")) is True


def test_is_transient_provider_error_for_named_rate_limit_error():
    assert is_transient_provider_error(RateLimitError("busy")) is True


def test_is_transient_provider_error_for_status_code():
    assert is_transient_provider_error(_StatusError(429)) is True
    assert is_transient_provider_error(_ResponseStatusError(503)) is True


def test_is_transient_provider_error_for_overload_text():
    assert is_transient_provider_error(Exception("The engine is currently overloaded")) is True


def test_is_transient_provider_error_rejects_non_transient_error():
    assert is_transient_provider_error(ValueError("bad request")) is False


def test_retry_delay_seconds_is_capped_exponential_backoff():
    assert retry_delay_seconds(0) == 2.0
    assert retry_delay_seconds(1) == 4.0
    assert retry_delay_seconds(2) == 8.0
    assert retry_delay_seconds(5) == 8.0


def test_retry_delay_seconds_rejects_negative_attempt_index():
    try:
        retry_delay_seconds(-1)
    except ValueError as exc:
        assert "attempt_index" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("expected ValueError")

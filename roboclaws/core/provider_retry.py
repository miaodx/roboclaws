from __future__ import annotations

_TRANSIENT_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_TRANSIENT_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "ConnectError",
    "InternalServerError",
    "RateLimitError",
    "ReadError",
    "ReadTimeout",
    "RemoteProtocolError",
    "ServiceUnavailableError",
    "WriteError",
    "WriteTimeout",
}
_TRANSIENT_TEXT_FRAGMENTS = (
    "connection refused",
    "connection reset",
    "engine is currently overloaded",
    "overloaded",
    "rate limit",
    "temporarily unavailable",
    "timed out",
    "timeout",
    "try again later",
)


def transient_status_code(exc: BaseException) -> int | None:
    """Return an HTTP-like status code when the SDK exposes one."""
    status_code = getattr(exc, "status_code", None)
    if isinstance(status_code, int):
        return status_code

    response = getattr(exc, "response", None)
    if response is None:
        return None

    response_status_code = getattr(response, "status_code", None)
    if isinstance(response_status_code, int):
        return response_status_code
    return None


def is_transient_provider_error(exc: BaseException) -> bool:
    """Return True for retryable transport / overload failures."""
    if isinstance(exc, (ConnectionError, TimeoutError)):
        return True

    if exc.__class__.__name__ in _TRANSIENT_ERROR_NAMES:
        return True

    status_code = transient_status_code(exc)
    if status_code in _TRANSIENT_STATUS_CODES:
        return True

    message = str(exc).lower()
    return any(fragment in message for fragment in _TRANSIENT_TEXT_FRAGMENTS)


def retry_delay_seconds(attempt_index: int, base: float = 2.0, cap: float = 8.0) -> float:
    """Return capped exponential backoff for a zero-based retry index."""
    if attempt_index < 0:
        raise ValueError("attempt_index must be >= 0")
    return min(base * (2**attempt_index), cap)

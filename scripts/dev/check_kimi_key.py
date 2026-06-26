"""Minimal smoke-test for KIMI_API_KEY validity.

Usage:
    KIMI_API_KEY=sk-... python scripts/dev/check_kimi_key.py
"""

from __future__ import annotations

import os
import sys
import time

import anthropic

from roboclaws.core.json_sources import parse_json_object_text
from roboclaws.core.provider_retry import is_transient_provider_error, retry_delay_seconds

EXPECTED_ACTION = "MoveAhead"


def create_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(
        api_key=os.environ["KIMI_API_KEY"],
        base_url="https://api.kimi.com/coding",
    )


def validate_kimi_key(max_attempts: int = 4) -> str:
    client = create_client()
    prompt = f'Reply with valid JSON: {{"action": "{EXPECTED_ACTION}"}}'

    last_exc: Exception | None = None
    for attempt in range(max_attempts):
        try:
            msg = client.messages.create(
                model="kimi-k2.7-code",
                max_tokens=64,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text.strip()
            _validate_response_text(text)
            return text
        except Exception as exc:  # pragma: no cover - concrete SDK exceptions are integration-only
            last_exc = exc
            if attempt == max_attempts - 1 or not is_transient_provider_error(exc):
                raise
            delay = retry_delay_seconds(attempt, base=2.0, cap=10.0)
            attempt_label = f"{attempt + 1}/{max_attempts}"
            print(
                f"Transient Kimi validation failure on attempt {attempt_label}: {exc}. "
                f"Retrying in {delay:.1f}s...",
                file=sys.stderr,
                flush=True,
            )
            time.sleep(delay)

    assert last_exc is not None
    raise last_exc


def _validate_response_text(text: str) -> None:
    payload = parse_json_object_text(
        text,
        label="KIMI_API_KEY validation response",
        source="model content",
    )
    action = payload.get("action")
    if action != EXPECTED_ACTION:
        raise ValueError(
            "KIMI_API_KEY validation response source must contain "
            f"action {EXPECTED_ACTION!r}; got {action!r}"
        )


def main() -> int:
    try:
        text = validate_kimi_key()
    except Exception as exc:
        print(f"ERROR: KIMI_API_KEY validation failed: {exc}", file=sys.stderr)
        return 1

    print("response:", text)
    print("✓ KIMI_API_KEY is valid and returns parseable JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Minimal smoke-test for KIMI_API_KEY validity.

Usage:
    KIMI_API_KEY=sk-... python scripts/check_kimi_key.py
"""

from __future__ import annotations

import os
import sys

import anthropic

client = anthropic.Anthropic(
    api_key=os.environ["KIMI_API_KEY"],
    base_url="https://api.kimi.com/coding",
)

msg = client.messages.create(
    model="kimi-k2-5",
    max_tokens=64,
    messages=[{"role": "user", "content": 'Reply with valid JSON: {"action": "MoveAhead"}'}],
)

text = msg.content[0].text.strip()
print("response:", text)

if '"action"' not in text:
    print(f"ERROR: Unexpected response: {text}", file=sys.stderr)
    sys.exit(1)

print("✓ KIMI_API_KEY is valid and returns parseable JSON")

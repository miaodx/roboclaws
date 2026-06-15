from __future__ import annotations

from roboclaws.operator_console.redaction import redact_text


def test_redacts_env_values_authorization_and_api_key_patterns() -> None:
    text = (
        "Authorization: Bearer live-secret-token\n"
        "api_key=visible-secret\n"
        "base=https://secret.internal/v1\n"
        "sk-abcdefghijklmnopqrstuvwxyz\n"
    )
    redacted = redact_text(
        text,
        env={
            "XM_LLM_BASE_URL": "https://secret.internal/v1",
            "CODEX_API_KEY": "visible-secret",
            "MIMO_API_KEY": "inside-secret",
            "MIMO_BASE_URL": "https://inside.secret/v1",
            "KIMI_OPENAI_BASE_URL": "https://kimi.secret/v1",
            "NVIDIA_BASE_URL": "https://nvidia.secret/v1",
        },
    )
    assert "live-secret-token" not in redacted
    assert "visible-secret" not in redacted
    assert "inside-secret" not in redacted
    assert "https://secret.internal/v1" not in redacted
    assert "https://inside.secret/v1" not in redacted
    assert "https://kimi.secret/v1" not in redacted
    assert "https://nvidia.secret/v1" not in redacted
    assert "sk-abcdefghijklmnopqrstuvwxyz" not in redacted
    assert redacted.count("[REDACTED]") >= 4

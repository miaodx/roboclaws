from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_script_module():
    path = Path("scripts/dev/check_kimi_key.py")
    spec = importlib.util.spec_from_file_location("check_kimi_key", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _fake_client(response_text: str):
    class FakeMessages:
        @staticmethod
        def create(**_kwargs):
            content = [type("TextBlock", (), {"text": response_text})()]
            return type("Message", (), {"content": content})()

    return type("FakeClient", (), {"messages": FakeMessages()})()


def test_validate_kimi_key_requires_json_object_action(monkeypatch) -> None:
    script = _load_script_module()
    monkeypatch.setattr(
        script,
        "create_client",
        lambda: _fake_client('prefix {"action": "MoveAhead"}'),
    )

    with pytest.raises(ValueError, match="must contain valid JSON object"):
        script.validate_kimi_key(max_attempts=1)


@pytest.mark.parametrize(
    "response_text",
    [
        '{"status": "ok"}',
        '{"action": "LookUp"}',
    ],
)
def test_validate_kimi_key_requires_expected_action(response_text: str, monkeypatch) -> None:
    script = _load_script_module()
    monkeypatch.setattr(script, "create_client", lambda: _fake_client(response_text))

    with pytest.raises(ValueError, match="must contain action 'MoveAhead'"):
        script.validate_kimi_key(max_attempts=1)


def test_validate_kimi_key_returns_valid_response_text(monkeypatch) -> None:
    script = _load_script_module()
    response_text = '{"action": "MoveAhead"}'
    monkeypatch.setattr(script, "create_client", lambda: _fake_client(response_text))

    assert script.validate_kimi_key(max_attempts=1) == response_text

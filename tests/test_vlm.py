from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.vlm import (
    KimiProvider,
    MockProvider,
    OpenAIProvider,
    VLMProvider,
    _parse_response,
    create_provider,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

SAMPLE_IMAGES = ["aGVsbG8=", "d29ybGQ="]  # arbitrary base64 strings
SAMPLE_STATE = {
    "position": {"x": 1.0, "y": 0.0, "z": -2.5},
    "facing": "East",
    "score": 10,
    "remaining_steps": 150,
}


# ---------------------------------------------------------------------------
# MockProvider
# ---------------------------------------------------------------------------


def test_mock_provider_returns_valid_action():
    p = MockProvider(seed=42)
    result = p.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert result["action"] in NAVIGATION_ACTIONS
    assert "reasoning" in result


def test_mock_provider_cost_is_zero():
    p = MockProvider()
    p.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert p.cumulative_cost == 0.0


def test_mock_provider_reset_cost():
    p = MockProvider()
    p.reset_cost()  # no-op but must not raise
    assert p.cumulative_cost == 0.0


def test_mock_provider_deterministic_with_seed():
    p1 = MockProvider(seed=0)
    p2 = MockProvider(seed=0)
    r1 = p1.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    r2 = p2.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert r1["action"] == r2["action"]


def test_mock_provider_satisfies_protocol():
    p = MockProvider()
    assert isinstance(p, VLMProvider)


# ---------------------------------------------------------------------------
# create_provider factory
# ---------------------------------------------------------------------------


def test_create_provider_mock():
    p = create_provider("mock")
    assert isinstance(p, MockProvider)


def test_create_provider_mock_with_seed():
    p = create_provider("mock", seed=99)
    assert isinstance(p, MockProvider)


def test_create_provider_unknown_raises():
    with pytest.raises(ValueError, match="Unknown model"):
        create_provider("unknown-model")


def test_create_provider_gpt4o(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.OpenAIProvider.__init__", return_value=None):
        p = create_provider("gpt-4o")
    assert isinstance(p, OpenAIProvider)


def test_create_provider_gpt4o_mini(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.OpenAIProvider.__init__", return_value=None):
        p = create_provider("gpt-4o-mini")
    assert isinstance(p, OpenAIProvider)


def test_create_provider_kimi(monkeypatch):
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.KimiProvider.__init__", return_value=None):
        p = create_provider("kimi")
    assert isinstance(p, KimiProvider)


def test_create_provider_kimi_alias(monkeypatch):
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.KimiProvider.__init__", return_value=None):
        p = create_provider("kimi-k2-5")
    assert isinstance(p, KimiProvider)


# ---------------------------------------------------------------------------
# _parse_response
# ---------------------------------------------------------------------------


def test_parse_valid_json():
    raw = json.dumps({"reasoning": "Going ahead", "action": "MoveAhead"})
    result = _parse_response(raw)
    assert result["action"] == "MoveAhead"
    assert result["reasoning"] == "Going ahead"


def test_parse_strips_code_fence():
    raw = '```json\n{"reasoning": "ok", "action": "RotateLeft"}\n```'
    result = _parse_response(raw)
    assert result["action"] == "RotateLeft"


def test_parse_invalid_json_falls_back():
    result = _parse_response("this is not json")
    assert result["action"] in NAVIGATION_ACTIONS
    assert "Parse error" in result["reasoning"]


def test_parse_invalid_action_falls_back():
    raw = json.dumps({"reasoning": "test", "action": "FlyAway"})
    result = _parse_response(raw)
    assert result["action"] in NAVIGATION_ACTIONS


def test_parse_empty_string_falls_back():
    result = _parse_response("")
    assert result["action"] in NAVIGATION_ACTIONS


# ---------------------------------------------------------------------------
# OpenAIProvider (mocked)
# ---------------------------------------------------------------------------


def _make_openai_mock(content: str, prompt_tokens: int = 100, completion_tokens: int = 50):
    """Build a mock OpenAI chat completion response."""
    usage = MagicMock()
    usage.prompt_tokens = prompt_tokens
    usage.completion_tokens = completion_tokens

    choice = MagicMock()
    choice.message.content = content

    resp = MagicMock()
    resp.choices = [choice]
    resp.usage = usage
    return resp


@pytest.fixture()
def openai_provider(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    mock_client = MagicMock()
    mock_openai = MagicMock()
    mock_openai.OpenAI.return_value = mock_client
    with patch.dict("sys.modules", {"openai": mock_openai}):
        provider = OpenAIProvider(model="gpt-4o-mini", api_key="test-key")
    provider._cost_table = {"input": 0.15, "output": 0.60}
    return provider, mock_client


def test_openai_get_action_calls_api(openai_provider):
    provider, mock_client = openai_provider
    mock_client.chat.completions.create.return_value = _make_openai_mock(
        '{"reasoning": "Move ahead", "action": "MoveAhead"}'
    )
    result = provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert result["action"] == "MoveAhead"
    mock_client.chat.completions.create.assert_called_once()


def test_openai_accumulates_cost(openai_provider):
    provider, mock_client = openai_provider
    mock_client.chat.completions.create.return_value = _make_openai_mock(
        '{"reasoning": "ok", "action": "RotateLeft"}',
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
    )
    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    # 1M input @ $0.15/M + 1M output @ $0.60/M = $0.75
    assert abs(provider.cumulative_cost - 0.75) < 1e-9


def test_openai_reset_cost(openai_provider):
    provider, mock_client = openai_provider
    mock_client.chat.completions.create.return_value = _make_openai_mock(
        '{"reasoning": "ok", "action": "Done"}',
        prompt_tokens=100,
        completion_tokens=50,
    )
    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert provider.cumulative_cost > 0
    provider.reset_cost()
    assert provider.cumulative_cost == 0.0


def test_openai_build_messages_includes_images(openai_provider):
    provider, _ = openai_provider
    messages = provider._build_messages(SAMPLE_IMAGES, SAMPLE_STATE)
    assert len(messages) == 1
    content = messages[0]["content"]
    image_entries = [c for c in content if c.get("type") == "image_url"]
    assert len(image_entries) == len(SAMPLE_IMAGES)
    text_entries = [c for c in content if c.get("type") == "text"]
    assert len(text_entries) == 1


# ---------------------------------------------------------------------------
# KimiProvider (mocked)
# ---------------------------------------------------------------------------


def _make_kimi_mock(text: str, input_tokens: int = 100, output_tokens: int = 50):
    """Build a mock Anthropic messages response."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens

    content_block = MagicMock()
    content_block.text = text

    resp = MagicMock()
    resp.content = [content_block]
    resp.usage = usage
    return resp


@pytest.fixture()
def kimi_provider(monkeypatch):
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    mock_anthropic_cls = MagicMock()
    mock_client = MagicMock()
    mock_anthropic_cls.return_value = mock_client
    with patch.dict("sys.modules", {"anthropic": MagicMock(Anthropic=mock_anthropic_cls)}):
        provider = KimiProvider(model="kimi-k2-5", api_key="test-key")
    provider._client = mock_client
    provider._cost_table = {"input": 1.00, "output": 3.00}
    return provider, mock_client


def test_kimi_get_action_calls_api(kimi_provider):
    provider, mock_client = kimi_provider
    mock_client.messages.create.return_value = _make_kimi_mock(
        '{"reasoning": "Rotate", "action": "RotateRight"}'
    )
    result = provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert result["action"] == "RotateRight"
    mock_client.messages.create.assert_called_once()


def test_kimi_accumulates_cost(kimi_provider):
    provider, mock_client = kimi_provider
    mock_client.messages.create.return_value = _make_kimi_mock(
        '{"reasoning": "ok", "action": "MoveAhead"}',
        input_tokens=1_000_000,
        output_tokens=1_000_000,
    )
    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    # 1M input @ $1.00/M + 1M output @ $3.00/M = $4.00
    assert abs(provider.cumulative_cost - 4.00) < 1e-9


def test_kimi_reset_cost(kimi_provider):
    provider, mock_client = kimi_provider
    mock_client.messages.create.return_value = _make_kimi_mock(
        '{"reasoning": "ok", "action": "Done"}',
        input_tokens=100,
        output_tokens=50,
    )
    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert provider.cumulative_cost > 0
    provider.reset_cost()
    assert provider.cumulative_cost == 0.0


def test_kimi_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("KIMI_API_KEY", raising=False)
    mock_anthropic = MagicMock()
    mock_anthropic.Anthropic.side_effect = KeyError("KIMI_API_KEY")
    with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
        with pytest.raises(KeyError):
            KimiProvider(model="kimi-k2-5")


def test_openai_missing_api_key_raises(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    mock_openai = MagicMock()
    mock_openai.OpenAI.side_effect = KeyError("OPENAI_API_KEY")
    with patch.dict("sys.modules", {"openai": mock_openai}):
        with pytest.raises(KeyError):
            OpenAIProvider(model="gpt-4o-mini")

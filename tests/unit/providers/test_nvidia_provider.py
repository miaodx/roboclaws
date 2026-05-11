from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from roboclaws.core.vlm import NvidiaProvider, create_provider

SAMPLE_IMAGES = ["aGVsbG8=", "d29ybGQ=", "aW1hZ2Uz"]
SAMPLE_STATE = {"position": {"x": 1.0, "y": 0.0, "z": -2.5}, "my_agent_id": 0}


def _mock_action_result(reasoning: str = "ok", action: str = "MoveAhead") -> MagicMock:
    result = MagicMock()
    result.reasoning = reasoning
    result.action = action
    return result


@pytest.fixture()
def nvidia_provider(monkeypatch):
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    mock_raw_client = MagicMock()
    mock_instructor_client = MagicMock()

    mock_openai_mod = MagicMock()
    mock_openai_mod.OpenAI.return_value = mock_raw_client

    mock_instructor_mod = MagicMock()
    mock_instructor_mod.from_openai.return_value = mock_instructor_client

    with patch.dict("sys.modules", {"openai": mock_openai_mod, "instructor": mock_instructor_mod}):
        provider = NvidiaProvider(api_key="test-key")
    return provider, mock_openai_mod, mock_instructor_client


def test_nvidia_provider_uses_nvidia_base_url(nvidia_provider) -> None:
    _provider, mock_openai_mod, _client = nvidia_provider
    kwargs = mock_openai_mod.OpenAI.call_args.kwargs
    assert kwargs["base_url"] == "https://integrate.api.nvidia.com/v1"


def test_nvidia_provider_serializes_three_images(nvidia_provider) -> None:
    provider, _mock_openai_mod, client = nvidia_provider
    response = MagicMock()
    response.usage = MagicMock(prompt_tokens=10, completion_tokens=5)
    client.chat.completions.create_with_completion.return_value = (
        _mock_action_result(),
        response,
    )

    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)

    kwargs = client.chat.completions.create_with_completion.call_args.kwargs
    content = kwargs["messages"][1]["content"]
    assert [item["type"] for item in content[:3]] == ["image_url", "image_url", "image_url"]
    assert content[3]["type"] == "text"


def test_nvidia_provider_cost_table_miss_does_not_crash(nvidia_provider) -> None:
    provider, _mock_openai_mod, client = nvidia_provider
    provider._cost_table = {"input": 0.0, "output": 0.0}
    response = MagicMock()
    response.usage = MagicMock(prompt_tokens=1_000_000, completion_tokens=1_000_000)
    client.chat.completions.create_with_completion.return_value = (
        _mock_action_result(action="RotateLeft"),
        response,
    )
    provider.get_action(SAMPLE_IMAGES, SAMPLE_STATE)
    assert provider.cumulative_cost == 0.0
    status = provider.get_status()
    assert status["provider_name"] == "nvidia"
    assert status["model"] == "meta/llama-4-maverick-17b-128e-instruct"


def test_create_provider_nvidia_alias(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.NvidiaProvider.__init__", return_value=None):
        provider = create_provider("nvidia")
    assert isinstance(provider, NvidiaProvider)


def test_create_provider_nvidia_full_model(monkeypatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    with patch("roboclaws.core.vlm.NvidiaProvider.__init__", return_value=None):
        provider = create_provider("nvidia/llama-3.1-nemotron-nano-vl-8b-v1")
    assert isinstance(provider, NvidiaProvider)

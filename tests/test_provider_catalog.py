from __future__ import annotations

from unittest.mock import patch

from roboclaws.core.provider_catalog import (
    model_aliases,
    model_supports_images,
    openclaw_model_id,
    required_env_keys,
    resolve_model,
)
from roboclaws.core.vlm import KimiProvider, MimoProvider, NvidiaProvider, create_provider
from roboclaws.mcp.text_bridge import resolve_observe_delivery


def test_resolve_model_records_alias_env_and_capabilities() -> None:
    meta = resolve_model("kimi")

    assert meta.canonical_model == "kimi-k2.6"
    assert meta.provider == "kimi"
    assert meta.adapter == "kimi"
    assert meta.required_env_keys == ("KIMI_API_KEY",)
    assert meta.supports_images is True
    assert meta.supports_tool_calls is False


def test_provider_catalog_exposes_aliases_without_duplicate_source() -> None:
    aliases = model_aliases()

    assert aliases["nvidia"] == "meta/llama-4-maverick-17b-128e-instruct"
    assert aliases["mimo-v2.5-pro"] == "mimo-v2.5-pro"


def test_provider_catalog_reports_required_env_keys() -> None:
    assert required_env_keys("nvidia") == ("NVIDIA_API_KEY", "NV_API_KEY")
    assert required_env_keys("mimo-omni") == ("MIMO_TP_KEY",)


def test_provider_factory_routes_through_catalog(monkeypatch) -> None:
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("MIMO_TP_KEY", "test-key")

    with patch("roboclaws.core.vlm.KimiProvider.__init__", return_value=None):
        assert isinstance(create_provider("kimi"), KimiProvider)
    with patch("roboclaws.core.vlm.NvidiaProvider.__init__", return_value=None):
        assert isinstance(create_provider("nvidia"), NvidiaProvider)
    with patch("roboclaws.core.vlm.MimoProvider.__init__", return_value=None):
        assert isinstance(create_provider("mimo-omni"), MimoProvider)


def test_text_bridge_uses_catalog_image_capabilities() -> None:
    assert model_supports_images("mimo_openai/mimo-v2.5-pro") is False
    assert model_supports_images("mimo_openai/mimo-v2-omni") is True
    assert (
        resolve_observe_delivery("mimo_openai/mimo-v2.5-pro", observe_mode="auto") == "text-bridge"
    )
    assert resolve_observe_delivery("mimo_openai/mimo-v2-omni", observe_mode="auto") == "images"


def test_catalog_returns_openclaw_model_identifier() -> None:
    assert openclaw_model_id("mimo-v2-omni") == "mimo_openai/mimo-v2-omni"
    assert openclaw_model_id("kimi-k2.6") == "anthropic_kimi/k2.6"

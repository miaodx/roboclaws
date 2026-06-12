from __future__ import annotations

from unittest.mock import patch

from roboclaws.agents.provider_registry import (
    ROUTE_BLOCKED,
    ROUTE_CAP_UNKNOWN,
    ROUTE_DEGRADED,
    ROUTE_HEALTHY,
    model_aliases,
    model_supports_images,
    openclaw_model_id,
    provider_readiness,
    provider_route_spec,
    required_env_keys,
    resolve_model,
    route_capabilities_for_engine,
)
from roboclaws.core.provider_factory import create_provider
from roboclaws.core.providers.kimi import KimiProvider
from roboclaws.core.providers.openai import MimoProvider, NvidiaProvider


def test_resolve_model_records_alias_env_and_capabilities() -> None:
    meta = resolve_model("kimi")

    assert meta.model_id == "kimi-k2.6"
    assert meta.family == "kimi"
    assert meta.direct_provider_adapter == "kimi"
    assert meta.direct_required_env_keys == ("KIMI_API_KEY",)
    assert meta.supports_image_input is True


def test_provider_registry_exposes_aliases_without_duplicate_source() -> None:
    aliases = model_aliases()

    assert aliases["nvidia"] == "meta/llama-4-maverick-17b-128e-instruct"
    assert aliases["mimo"] == "mimo-v2.5"
    assert aliases["mimo-v2.5"] == "mimo-v2.5"
    assert "mimo-v2.5-" + "pro" not in aliases
    assert "mimo-" + "omni" not in aliases
    assert "mimo-v2-" + "omni" not in aliases


def test_provider_registry_reports_required_env_keys() -> None:
    assert required_env_keys("nvidia") == ("NVIDIA_API_KEY", "NV_API_KEY")
    assert required_env_keys("mimo") == ("MIMO_TP_KEY",)


def test_provider_factory_routes_through_catalog(monkeypatch) -> None:
    monkeypatch.setenv("KIMI_API_KEY", "test-key")
    monkeypatch.setenv("NVIDIA_API_KEY", "test-key")
    monkeypatch.setenv("MIMO_TP_KEY", "test-key")

    with patch("roboclaws.core.provider_factory.KimiProvider.__init__", return_value=None):
        assert isinstance(create_provider("kimi"), KimiProvider)
    with patch("roboclaws.core.provider_factory.NvidiaProvider.__init__", return_value=None):
        assert isinstance(create_provider("nvidia"), NvidiaProvider)
    with patch("roboclaws.core.provider_factory.MimoProvider.__init__", return_value=None):
        assert isinstance(create_provider("mimo"), MimoProvider)


def test_catalog_reports_all_real_models_image_capable() -> None:
    # mimo-v2.5 has native vision; every non-mock catalog model is image-capable.
    assert model_supports_images("mimo_openai/mimo-v2.5") is True
    assert model_supports_images("mimo_anthropic/mimo-v2.5") is True
    assert model_supports_images("anthropic_kimi/k2p5") is True


def test_catalog_returns_openclaw_model_identifier() -> None:
    assert openclaw_model_id("mimo-v2.5") == "mimo_openai/mimo-v2.5"
    assert openclaw_model_id("kimi-k2.6") == "anthropic_kimi/k2.6"


def test_registry_marks_mify_codex_degraded_but_supported() -> None:
    route = provider_route_spec("mify")

    assert "codex-cli" in route.supported_engines
    assert route.status_for_engine("codex-cli") == ROUTE_DEGRADED
    assert route.wire_api == "responses"
    assert route.default_model_id == "xiaomi/mimo-v2.5"


def test_registry_keeps_raw_fpv_transport_separate_from_model_modality() -> None:
    route = provider_route_spec("minimax")
    model = resolve_model("MiniMax-M3")

    assert model.supports_image_input is True
    assert route.status_for_engine("codex-cli") == ROUTE_BLOCKED
    assert route.status_for_engine("openai-agents-sdk") == ROUTE_HEALTHY
    assert route_capabilities_for_engine(route, "codex-cli")["image_transport"] == (
        ROUTE_CAP_UNKNOWN
    )
    assert "unsupported calls" in route.status_note


def test_provider_readiness_reports_status_and_missing_env() -> None:
    readiness = provider_readiness(
        agent_engine="codex-cli",
        provider_profile="mify",
        env={},
    )

    assert readiness["provider"] == "mify"
    assert readiness["route_status"] == ROUTE_DEGRADED
    assert readiness["missing_env"] == ["XM_LLM_API_KEY"]

from __future__ import annotations

from unittest.mock import patch

from roboclaws.agents.provider_registry import (
    ROUTE_BLOCKED,
    ROUTE_CAP_UNKNOWN,
    ROUTE_DEGRADED,
    ROUTE_EXPERIMENTAL,
    ROUTE_HEALTHY,
    ROUTE_PROVISIONAL,
    _main,
    default_enabled_models,
    default_enabled_provider_routes,
    model_aliases,
    model_supports_images,
    normalize_provider_route,
    openclaw_model_id,
    provider_readiness,
    provider_route_spec,
    required_env_keys,
    resolve_model,
    route_base_url,
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
    assert aliases["mimo-ultraspeed"] == "mimo-1000"
    assert aliases["kimi-code"] == "kimi-k2.7-code"
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
    route = provider_route_spec("mimo-mify-responses")

    assert "codex-cli" in route.supported_engines
    assert route.status_for_engine("codex-cli") == ROUTE_DEGRADED
    assert route.wire_api == "responses"
    assert route.default_model_id == "xiaomi/mimo-v2.5"


def test_kimi_openai_chat_defaults_to_current_code_model() -> None:
    route = provider_route_spec("kimi-openai-chat")
    model = resolve_model(route.default_model_id)

    assert route.default_model_id == "kimi-k2.7-code"
    assert route.status_for_engine("openai-agents-sdk") == ROUTE_EXPERIMENTAL
    assert route.default_use is True
    assert model.default_use is True
    assert "Thinking On" in route.default_use_note
    assert "model_thinking_mode" in route.default_use_note
    assert "provider-specific" in model.default_use_note


def test_default_enabled_routes_include_requested_api_sources() -> None:
    routes = default_enabled_provider_routes()
    route_ids = {route.route_id for route in routes}
    public_profiles = {route.public_profile for route in routes}
    model_ids = {model.model_id for model in default_enabled_models()}

    assert {
        "codex-router-responses",
        "mimo-mify-responses",
        "mimo-tp-openai-chat",
        "mimo-inside-openai-chat",
        "minimax-responses",
        "kimi-openai-chat",
    } <= route_ids
    assert {
        "codex-router-responses",
        "mimo-mify-responses",
        "mimo-tp-openai-chat",
        "mimo-inside-openai-chat",
        "minimax-responses",
        "kimi-openai-chat",
    } <= public_profiles
    assert {
        "gpt-5.5",
        "xiaomi/mimo-v2.5",
        "mimo-v2.5",
        "mimo-1000",
        "MiniMax-M3",
        "kimi-k2.7-code",
    } <= model_ids
    assert "MiniMax-M2.7-highspeed" not in model_ids


def test_mimo_inside_is_default_enabled_openai_chat_route() -> None:
    route = provider_route_spec("mimo-inside-openai-chat")

    assert route.default_model_id == "mimo-1000"
    assert route.default_use is True
    assert route.supported_engines == ("openai-agents-sdk",)
    assert route.base_url_env == "MIMO_BASE_URL"
    assert route.api_key_env == "MIMO_API_KEY"
    assert route.status_for_engine("openai-agents-sdk") == ROUTE_PROVISIONAL


def test_provider_route_aliases_normalize_to_public_profiles() -> None:
    assert provider_route_spec("mimo-mify-responses").public_profile == "mimo-mify-responses"
    assert provider_route_spec("mimo-mify-responses").route_id == "mimo-mify-responses"
    assert provider_route_spec("mimo-inside-openai-chat").route_id == "mimo-inside-openai-chat"
    assert provider_route_spec("mimo-mify-anthropic").route_id == "mimo-mify-anthropic"
    assert normalize_provider_route("minimax-responses") == "minimax-responses"


def test_provider_routes_accept_adjacent_base_url_env_overrides() -> None:
    assert provider_route_spec("mimo-tp-anthropic").base_url_env == "MIMO_ANTHROPIC_BASE_URL"
    assert (
        route_base_url(
            provider_route_spec("mimo-tp-anthropic"),
            env={"MIMO_ANTHROPIC_BASE_URL": "https://mimo.example/anthropic"},
        )
        == "https://mimo.example/anthropic"
    )
    assert provider_route_spec("kimi-anthropic").base_url_env == "KIMI_ANTHROPIC_BASE_URL"
    assert (
        route_base_url(
            provider_route_spec("kimi-anthropic"),
            env={"KIMI_ANTHROPIC_BASE_URL": "https://kimi.example/coding/"},
        )
        == "https://kimi.example/coding/"
    )


def test_registry_keeps_raw_fpv_transport_separate_from_model_modality() -> None:
    route = provider_route_spec("minimax-responses")
    model = resolve_model("MiniMax-M3")

    assert model.supports_image_input is True
    assert route.default_model_id == "MiniMax-M3"
    assert route.default_use is True
    assert route.status_for_engine("codex-cli") == ROUTE_BLOCKED
    assert route.status_for_engine("openai-agents-sdk") == ROUTE_HEALTHY
    assert route_capabilities_for_engine(route, "codex-cli")["image_transport"] == (
        ROUTE_CAP_UNKNOWN
    )
    assert "unsupported calls" in route.status_note


def test_provider_readiness_reports_status_and_missing_env() -> None:
    readiness = provider_readiness(
        agent_engine="codex-cli",
        provider_profile="mimo-mify-responses",
        env={},
    )

    assert readiness["provider"] == "mimo-mify-responses"
    assert readiness["route_status"] == ROUTE_DEGRADED
    assert readiness["missing_env"] == ["XM_LLM_API_KEY"]


def test_provider_registry_cli_dispatches_route_and_json_commands(
    tmp_path,
    capsys,
) -> None:
    output = tmp_path / "providers.json"

    assert _main(["json", "--output", str(output)]) == 0
    assert "codex-router-responses" in output.read_text(encoding="utf-8")
    assert _main(["default-model", "minimax-responses"]) == 0
    assert capsys.readouterr().out.strip() == "MiniMax-M3"
    assert _main(["supports-engine", "minimax-responses", "openai-agents-sdk"]) == 0
    assert _main(["supports-engine", "mimo-tp-openai-chat", "codex-cli"]) == 1

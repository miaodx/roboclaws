from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script_module():
    path = Path("scripts/dev/check_model_providers.py")
    spec = importlib.util.spec_from_file_location("check_model_providers", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_provider_health_defaults_leave_room_for_reasoning_tokens() -> None:
    script = _load_script_module()

    assert script.DEFAULT_RESPONSES_MAX_OUTPUT_TOKENS >= 256
    assert script.DEFAULT_CHAT_MAX_TOKENS >= 128


def test_direct_probe_defaults_cover_minimax_highspeed_and_kimi_payload() -> None:
    script = _load_script_module()

    probes = {probe.probe_id: probe for probe in script.build_direct_probes()}

    assert probes["direct:minimax-m27"].max_tokens >= 256
    assert probes["direct:mimo-chat"].max_tokens >= 128
    assert probes["direct:mimo-inside"].model == "mimo-1000"
    assert probes["direct:mimo-inside"].max_tokens >= 128
    kimi = probes["direct:kimi-coding-chat"]
    payload = script.kimi_coding_payload(
        prompt="Health check. Reply exactly ok.",
        model=kimi.model,
        max_tokens=kimi.max_tokens,
    )
    assert payload["max_tokens"] >= 128
    assert payload["stream"] is False
    assert "temperature" not in payload


def test_direct_probe_defaults_exclude_unavailable_official_openai_route() -> None:
    script = _load_script_module()

    probes = {probe.probe_id: probe for probe in script.build_direct_probes()}

    assert "direct:openai-responses" not in probes
    assert all(probe.api_key_env != "OPENAI_API_KEY" for probe in probes.values())


def test_require_all_fails_on_skipped_probe(monkeypatch) -> None:
    script = _load_script_module()
    monkeypatch.delenv("MM_API_KEY", raising=False)
    monkeypatch.setattr(
        script,
        "build_agent_sdk_probes",
        lambda responses_max_tokens, chat_max_tokens: [
            script.ProbeSpec(
                probe_id="agents-sdk:minimax",
                mode="agents-sdk",
                route_id="minimax",
                wire_api=script.WIRE_RESPONSES,
                model="MiniMax-M3",
                api_key_env="MM_API_KEY",
                base_url="https://api.minimaxi.com/v1",
                max_tokens=responses_max_tokens,
            )
        ],
    )
    monkeypatch.setattr(script, "build_direct_probes", lambda **_kwargs: [])

    assert script.main(["--mode", "agents-sdk", "--dotenv", "", "--require-all"]) == 1


def test_agents_sdk_probe_defaults_use_larger_responses_budget() -> None:
    script = _load_script_module()

    probes = {probe.probe_id: probe for probe in script.build_agent_sdk_probes()}

    assert probes["agents-sdk:minimax"].max_tokens >= 256
    assert probes["agents-sdk:codex-env"].max_tokens >= 256
    assert probes["agents-sdk:mimo-openai-chat"].max_tokens >= 128
    assert probes["agents-sdk:mimo-inside"].model == "mimo-1000"
    assert probes["agents-sdk:mimo-inside"].max_tokens >= 128
    assert probes["agents-sdk:kimi-openai-chat"].model == "kimi-k2.7-code"
    assert not probes["agents-sdk:kimi-openai-chat"].unsupported_reason


def test_kimi_agents_sdk_probe_uses_coding_agent_user_agent_header(
    monkeypatch,
) -> None:
    script = _load_script_module()
    captured: dict[str, object] = {}
    monkeypatch.setenv("KIMI_API_KEY", "fake-kimi-key")

    class FakeModelSettings:
        def __init__(self, **kwargs) -> None:
            captured["model_settings"] = kwargs

    class FakeAgent:
        def __init__(self, **kwargs) -> None:
            captured["agent"] = kwargs

    class FakeRunner:
        @staticmethod
        def run_sync(*_args, **_kwargs):
            return type("Result", (), {"final_output": "ok"})()

    class FakeAsyncOpenAI:
        def __init__(self, **kwargs) -> None:
            captured["client"] = kwargs

    class FakeChatModel:
        def __init__(self, model: str, *, openai_client: object) -> None:
            captured["model"] = model
            captured["model_client"] = openai_client

    monkeypatch.setitem(
        sys.modules,
        "agents",
        type(
            "FakeAgentsModule",
            (),
            {
                "Agent": FakeAgent,
                "ModelSettings": FakeModelSettings,
                "OpenAIChatCompletionsModel": FakeChatModel,
                "OpenAIResponsesModel": object,
                "Runner": FakeRunner,
                "set_tracing_disabled": staticmethod(lambda *_args, **_kwargs: None),
            },
        ),
    )
    monkeypatch.setitem(
        sys.modules,
        "openai",
        type("FakeOpenAIModule", (), {"AsyncOpenAI": FakeAsyncOpenAI}),
    )
    probe = {probe.probe_id: probe for probe in script.build_agent_sdk_probes()}[
        "agents-sdk:kimi-openai-chat"
    ]

    result = script.run_probe(
        probe,
        prompt="Health check. Reply exactly ok.",
        timeout_s=1.0,
    )

    assert result.status == "PASS"
    assert result.ok is True
    assert captured["model"] == "kimi-k2.7-code"
    assert captured["model_settings"]["extra_headers"] == {"User-Agent": "claude-code/1.0.0"}


def test_select_probe_can_limit_by_route_or_probe_id() -> None:
    script = _load_script_module()
    args = script.parse_args(["--mode", "all", "--probe", "minimax"])

    selected = script.select_probes(args)

    assert {probe.probe_id for probe in selected} == {
        "agents-sdk:minimax",
        "direct:minimax-m3",
        "direct:minimax-m27",
    }


def test_select_probe_can_limit_kimi_route_across_sdk_and_direct_probes() -> None:
    script = _load_script_module()
    args = script.parse_args(["--mode", "all", "--probe", "kimi-openai-chat"])

    selected = script.select_probes(args)

    assert {probe.probe_id for probe in selected} == {
        "agents-sdk:kimi-openai-chat",
        "direct:kimi-coding-chat",
    }

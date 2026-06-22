from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MODEL_CAP_TEXT = "text"
MODEL_CAP_IMAGE_INPUT = "image_input"

PROVIDER_PROFILE_CODEX_RESPONSES = "codex-router-responses"
PROVIDER_PROFILE_MIMO_MIFY_RESPONSES = "mimo-mify-responses"
PROVIDER_PROFILE_MINIMAX_RESPONSES = "minimax-responses"
PROVIDER_PROFILE_MIMO_OPENAI_CHAT = "mimo-tp-openai-chat"
PROVIDER_PROFILE_MIMO_INSIDE_OPENAI_CHAT = "mimo-inside-openai-chat"
PROVIDER_PROFILE_KIMI_OPENAI_CHAT = "kimi-openai-chat"
PROVIDER_PROFILE_KIMI_ANTHROPIC = "kimi-anthropic"
PROVIDER_PROFILE_MIMO_ANTHROPIC = "mimo-tp-anthropic"
PROVIDER_PROFILE_MIMO_MIFY_ANTHROPIC = "mimo-mify-anthropic"

ROUTE_CAP_SUPPORTED = "supported"
ROUTE_CAP_UNSUPPORTED = "unsupported"
ROUTE_CAP_UNKNOWN = "unknown"

WIRE_RESPONSES = "responses"
WIRE_CHAT_COMPLETIONS = "chat-completions"
WIRE_ANTHROPIC = "anthropic"

WIRE_SOURCE_NATIVE = "native"
WIRE_SOURCE_GATEWAY = "gateway"
WIRE_SOURCE_SHIM = "shim"
WIRE_SOURCE_UNKNOWN = "unknown"

ROUTE_HEALTHY = "healthy"
ROUTE_EXPERIMENTAL = "experimental"
ROUTE_PROVISIONAL = "provisional"
ROUTE_DEGRADED = "degraded"
ROUTE_BLOCKED = "blocked"


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    aliases: tuple[str, ...]
    family: str
    model_capabilities: frozenset[str]
    default_use: bool = False
    default_use_note: str = ""
    direct_provider_adapter: str | None = None
    direct_required_env_keys: tuple[str, ...] = ()
    cost_per_m: dict[str, float] = field(default_factory=dict)
    openclaw_model_id: str | None = None

    @property
    def supports_image_input(self) -> bool:
        return MODEL_CAP_IMAGE_INPUT in self.model_capabilities


@dataclass(frozen=True)
class ProviderRouteSpec:
    route_id: str
    public_profile: str
    label: str
    supported_engines: tuple[str, ...]
    default_model_id: str
    required_env_keys: tuple[str, ...]
    api_key_env: str | None
    base_url_env: str | None
    base_url_default: str
    wire_api: str
    wire_source: str
    default_use: bool = False
    default_use_note: str = ""
    aliases: tuple[str, ...] = ()
    per_engine_status: dict[str, str] = field(default_factory=dict)
    route_capabilities: dict[str, str] = field(default_factory=dict)
    per_engine_route_capability_overrides: dict[str, dict[str, str]] = field(default_factory=dict)
    status_note: str = ""

    def status_for_engine(self, agent_engine: str) -> str:
        return self.per_engine_status.get(agent_engine, ROUTE_EXPERIMENTAL)

    def route_capability(self, capability: str, *, agent_engine: str) -> str:
        overrides = self.per_engine_route_capability_overrides.get(agent_engine, {})
        return overrides.get(
            capability,
            self.route_capabilities.get(capability, ROUTE_CAP_UNKNOWN),
        )


def _caps(*values: str) -> frozenset[str]:
    return frozenset(values)


_MODEL_SPECS: tuple[ModelSpec, ...] = (
    ModelSpec(
        model_id="mock",
        aliases=("mock",),
        family="mock",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="mock",
    ),
    ModelSpec(
        model_id="gpt-5.5",
        aliases=("gpt-5.5",),
        family="gpt",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        default_use=True,
        default_use_note="Best current Codex router model and default Codex route model.",
    ),
    ModelSpec(
        model_id="gpt-4o",
        aliases=("gpt-4o",),
        family="gpt",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="openai",
        direct_required_env_keys=("OPENAI_API_KEY",),
        cost_per_m={"input": 5.00, "output": 15.00},
    ),
    ModelSpec(
        model_id="gpt-4o-mini",
        aliases=("gpt-4o-mini",),
        family="gpt",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="openai",
        direct_required_env_keys=("OPENAI_API_KEY",),
        cost_per_m={"input": 0.15, "output": 0.60},
    ),
    ModelSpec(
        model_id="kimi-k2-5",
        aliases=("kimi-k2-5", "k2p5"),
        family="kimi",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="kimi",
        direct_required_env_keys=("KIMI_API_KEY",),
        cost_per_m={"input": 1.00, "output": 3.00},
        openclaw_model_id="anthropic_kimi/k2p5",
    ),
    ModelSpec(
        model_id="kimi-k2.6",
        aliases=("kimi", "kimi-k2.6", "k2.6"),
        family="kimi",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="kimi",
        direct_required_env_keys=("KIMI_API_KEY",),
        cost_per_m={"input": 1.00, "output": 3.00},
        openclaw_model_id="anthropic_kimi/k2.6",
    ),
    ModelSpec(
        model_id="kimi-k2.7-code",
        aliases=("kimi-k2.7-code", "k2.7-code", "kimi-code"),
        family="kimi",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        default_use=True,
        default_use_note=(
            "Default Kimi coding model. Kimi K2.7 Code requires Thinking On for "
            "the new code-model behavior. OpenAI Agents SDK routes use the "
            "normalized model_thinking_mode switch and map it to provider-specific "
            "request fields."
        ),
        direct_provider_adapter="kimi-coding",
        direct_required_env_keys=("KIMI_API_KEY",),
        cost_per_m={"input": 1.00, "output": 3.00},
    ),
    ModelSpec(
        model_id="kimi-for-coding",
        aliases=("kimi-coding", "kimi-for-coding"),
        family="kimi",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="kimi-coding",
        direct_required_env_keys=("KIMI_API_KEY",),
        cost_per_m={"input": 1.00, "output": 3.00},
        openclaw_model_id="anthropic_kimi/k2.6",
    ),
    ModelSpec(
        model_id="claude-3-5-sonnet-20241022",
        aliases=("anthropic", "claude-3-5-sonnet-20241022"),
        family="anthropic",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="anthropic",
        direct_required_env_keys=("ANTHROPIC_API_KEY",),
        cost_per_m={"input": 3.00, "output": 15.00},
    ),
    ModelSpec(
        model_id="claude-3-haiku-20240307",
        aliases=("claude-3-haiku-20240307",),
        family="anthropic",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="anthropic",
        direct_required_env_keys=("ANTHROPIC_API_KEY",),
        cost_per_m={"input": 0.25, "output": 1.25},
    ),
    ModelSpec(
        model_id="meta/llama-4-maverick-17b-128e-instruct",
        aliases=("nvidia", "meta/llama-4-maverick-17b-128e-instruct"),
        family="nvidia",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="nvidia",
        direct_required_env_keys=("NVIDIA_API_KEY", "NV_API_KEY"),
        cost_per_m={"input": 0.0, "output": 0.0},
    ),
    ModelSpec(
        model_id="nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        aliases=("nvidia-nano-vl", "nvidia/llama-3.1-nemotron-nano-vl-8b-v1"),
        family="nvidia",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        direct_provider_adapter="nvidia",
        direct_required_env_keys=("NVIDIA_API_KEY", "NV_API_KEY"),
        cost_per_m={"input": 0.0, "output": 0.0},
    ),
    ModelSpec(
        model_id="mimo-v2.5",
        aliases=("mimo", "mimo-v2.5"),
        family="mimo",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        default_use=True,
        default_use_note="Default MiMo token-plan model.",
        direct_provider_adapter="mimo",
        direct_required_env_keys=("MIMO_TP_KEY",),
        cost_per_m={"input": 0.0, "output": 0.0},
        openclaw_model_id="mimo_openai/mimo-v2.5",
    ),
    ModelSpec(
        model_id="xiaomi/mimo-v2.5",
        aliases=("xiaomi/mimo-v2.5", "mimo-mify-v2.5"),
        family="mimo",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        default_use=True,
        default_use_note="Default MiMo model through the mify gateway.",
    ),
    ModelSpec(
        model_id="mimo-1000",
        aliases=("mimo-1000", "mimo-inside-1000", "mimo-ultraspeed"),
        family="mimo",
        model_capabilities=_caps(MODEL_CAP_TEXT),
        default_use=True,
        default_use_note=(
            "Default-enabled MiMo inside UltraSpeed route for explicit on-demand "
            "benchmark and text-agent use; product cleanup promotion still requires "
            "a route decision."
        ),
    ),
    ModelSpec(
        model_id="MiniMax-M3",
        aliases=("minimax", "minimax-m3", "MiniMax-M3"),
        family="minimax",
        model_capabilities=_caps(MODEL_CAP_TEXT, MODEL_CAP_IMAGE_INPUT),
        default_use=True,
        default_use_note=(
            "Default MiniMax model; multimodal and faster than the M2.7 row in "
            "local cleanup evidence."
        ),
    ),
    ModelSpec(
        model_id="MiniMax-M2.7-highspeed",
        aliases=("minimax-highspeed", "minimax-m2.7-highspeed", "MiniMax-M2.7-highspeed"),
        family="minimax",
        model_capabilities=_caps(MODEL_CAP_TEXT),
        default_use=False,
        default_use_note="Available explicit variant only; not the default MiniMax route.",
    ),
)

_PROVIDER_ROUTE_SPECS: tuple[ProviderRouteSpec, ...] = (
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_CODEX_RESPONSES,
        public_profile=PROVIDER_PROFILE_CODEX_RESPONSES,
        label="Codex Router Responses",
        supported_engines=("codex-cli", "openai-agents-sdk"),
        default_model_id="gpt-5.5",
        required_env_keys=("CODEX_BASE_URL", "CODEX_API_KEY"),
        api_key_env="CODEX_API_KEY",
        base_url_env="CODEX_BASE_URL",
        base_url_default="",
        wire_api=WIRE_RESPONSES,
        wire_source=WIRE_SOURCE_NATIVE,
        default_use=True,
        default_use_note="Default Codex router route; uses gpt-5.5.",
        per_engine_status={
            "codex-cli": ROUTE_HEALTHY,
            "openai-agents-sdk": ROUTE_EXPERIMENTAL,
        },
        route_capabilities={
            "image_transport": ROUTE_CAP_SUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MIMO_MIFY_RESPONSES,
        public_profile=PROVIDER_PROFILE_MIMO_MIFY_RESPONSES,
        label="MiMo mify Responses Gateway",
        supported_engines=("codex-cli", "openai-agents-sdk"),
        default_model_id="xiaomi/mimo-v2.5",
        required_env_keys=("XM_LLM_API_KEY",),
        api_key_env="XM_LLM_API_KEY",
        base_url_env="XM_LLM_BASE_URL",
        base_url_default="https://api.llm.mioffice.cn/v1",
        wire_api=WIRE_RESPONSES,
        wire_source=WIRE_SOURCE_GATEWAY,
        default_use=True,
        default_use_note=(
            "Default-enabled MiMo mify route; uses xiaomi/mimo-v2.5 unless explicitly overridden."
        ),
        per_engine_status={
            "codex-cli": ROUTE_DEGRADED,
            "openai-agents-sdk": ROUTE_PROVISIONAL,
        },
        route_capabilities={
            "image_transport": ROUTE_CAP_UNKNOWN,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
        status_note=(
            "MiMo via mify can call MCP tools in Codex, but current Codex probes "
            "early-stop after one live-agent turn."
        ),
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MINIMAX_RESPONSES,
        public_profile=PROVIDER_PROFILE_MINIMAX_RESPONSES,
        label="MiniMax Responses",
        supported_engines=("codex-cli", "openai-agents-sdk"),
        default_model_id="MiniMax-M3",
        required_env_keys=("MM_API_KEY",),
        api_key_env="MM_API_KEY",
        base_url_env="MM_BASE_URL",
        base_url_default="https://api.minimaxi.com/v1",
        wire_api=WIRE_RESPONSES,
        wire_source=WIRE_SOURCE_NATIVE,
        default_use=True,
        default_use_note="Default-enabled MiniMax route; uses MiniMax-M3, not M2.7-highspeed.",
        per_engine_status={
            "codex-cli": ROUTE_BLOCKED,
            "openai-agents-sdk": ROUTE_HEALTHY,
        },
        route_capabilities={
            "image_transport": ROUTE_CAP_UNKNOWN,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
        status_note=(
            "OpenAI Agents SDK structured cleanup works. Codex CLI is blocked by "
            "MiniMax Responses MCP tool-name shape; Codex rejects flattened names "
            "such as mcp__cleanup__metric_map or cleanup__ping_tool as unsupported calls."
        ),
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MIMO_OPENAI_CHAT,
        public_profile=PROVIDER_PROFILE_MIMO_OPENAI_CHAT,
        label="MiMo token plan OpenAI Chat",
        supported_engines=("openai-agents-sdk",),
        default_model_id="mimo-v2.5",
        required_env_keys=("MIMO_TP_KEY",),
        api_key_env="MIMO_TP_KEY",
        base_url_env="MIMO_OPENAI_BASE_URL",
        base_url_default="https://token-plan-cn.xiaomimimo.com/v1",
        wire_api=WIRE_CHAT_COMPLETIONS,
        wire_source=WIRE_SOURCE_NATIVE,
        default_use=True,
        default_use_note="Default-enabled MiMo token-plan chat route; uses mimo-v2.5.",
        per_engine_status={"openai-agents-sdk": ROUTE_HEALTHY},
        route_capabilities={
            "image_transport": ROUTE_CAP_UNSUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MIMO_INSIDE_OPENAI_CHAT,
        public_profile=PROVIDER_PROFILE_MIMO_INSIDE_OPENAI_CHAT,
        label="MiMo inside OpenAI Chat",
        supported_engines=("openai-agents-sdk",),
        default_model_id="mimo-1000",
        required_env_keys=("MIMO_API_KEY",),
        api_key_env="MIMO_API_KEY",
        base_url_env="MIMO_BASE_URL",
        base_url_default="",
        wire_api=WIRE_CHAT_COMPLETIONS,
        wire_source=WIRE_SOURCE_NATIVE,
        default_use=True,
        default_use_note=(
            "Default-enabled on-demand MiMo inside route for speed benchmarks and "
            "explicit text-agent experiments. Not a product cleanup default until "
            "a separate route decision promotes it."
        ),
        per_engine_status={"openai-agents-sdk": ROUTE_PROVISIONAL},
        route_capabilities={
            "image_transport": ROUTE_CAP_UNKNOWN,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id="kimi-openai-chat",
        public_profile=PROVIDER_PROFILE_KIMI_OPENAI_CHAT,
        label="Kimi OpenAI Chat",
        supported_engines=("openai-agents-sdk",),
        default_model_id="kimi-k2.7-code",
        required_env_keys=("KIMI_API_KEY",),
        api_key_env="KIMI_API_KEY",
        base_url_env="KIMI_OPENAI_BASE_URL",
        base_url_default="https://api.kimi.com/coding/v1",
        wire_api=WIRE_CHAT_COMPLETIONS,
        wire_source=WIRE_SOURCE_NATIVE,
        default_use=True,
        default_use_note=(
            "Default-enabled Kimi coding route. K2.7 Code requires Thinking On "
            "for the new code-model behavior. Default OpenAI Agents SDK payloads "
            "enable thinking through the provider-aware model_thinking_mode policy."
        ),
        per_engine_status={"openai-agents-sdk": ROUTE_EXPERIMENTAL},
        route_capabilities={
            "image_transport": ROUTE_CAP_UNSUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id="kimi-anthropic",
        public_profile=PROVIDER_PROFILE_KIMI_ANTHROPIC,
        label="Kimi Anthropic",
        supported_engines=("claude-code",),
        default_model_id="kimi-k2.6",
        required_env_keys=("KIMI_API_KEY",),
        api_key_env="KIMI_API_KEY",
        base_url_env="KIMI_ANTHROPIC_BASE_URL",
        base_url_default="https://api.kimi.com/coding/",
        wire_api=WIRE_ANTHROPIC,
        wire_source=WIRE_SOURCE_NATIVE,
        per_engine_status={"claude-code": ROUTE_HEALTHY},
        route_capabilities={
            "image_transport": ROUTE_CAP_SUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MIMO_ANTHROPIC,
        public_profile=PROVIDER_PROFILE_MIMO_ANTHROPIC,
        label="MiMo token plan Anthropic",
        supported_engines=("claude-code",),
        default_model_id="mimo-v2.5",
        required_env_keys=("MIMO_TP_KEY",),
        api_key_env="MIMO_TP_KEY",
        base_url_env="MIMO_ANTHROPIC_BASE_URL",
        base_url_default="https://token-plan-cn.xiaomimimo.com/anthropic",
        wire_api=WIRE_ANTHROPIC,
        wire_source=WIRE_SOURCE_SHIM,
        per_engine_status={"claude-code": ROUTE_HEALTHY},
        route_capabilities={
            "image_transport": ROUTE_CAP_SUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id=PROVIDER_PROFILE_MIMO_MIFY_ANTHROPIC,
        public_profile=PROVIDER_PROFILE_MIMO_MIFY_ANTHROPIC,
        label="MiMo mify Anthropic Gateway",
        supported_engines=("claude-code",),
        default_model_id="xiaomi/mimo-v2.5",
        required_env_keys=("XM_LLM_API_KEY",),
        api_key_env="XM_LLM_API_KEY",
        base_url_env="XM_LLM_ANTHROPIC_BASE_URL",
        base_url_default="https://api.llm.mioffice.cn/anthropic",
        wire_api=WIRE_ANTHROPIC,
        wire_source=WIRE_SOURCE_GATEWAY,
        per_engine_status={"claude-code": ROUTE_EXPERIMENTAL},
        route_capabilities={
            "image_transport": ROUTE_CAP_SUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
    ProviderRouteSpec(
        route_id="kimi",
        public_profile="kimi",
        label="Kimi OpenClaw",
        supported_engines=("openclaw-gateway",),
        default_model_id="kimi-k2.6",
        required_env_keys=("KIMI_API_KEY",),
        api_key_env="KIMI_API_KEY",
        base_url_env=None,
        base_url_default="https://api.kimi.com/coding/",
        wire_api=WIRE_ANTHROPIC,
        wire_source=WIRE_SOURCE_NATIVE,
        per_engine_status={"openclaw-gateway": ROUTE_EXPERIMENTAL},
        route_capabilities={
            "image_transport": ROUTE_CAP_SUPPORTED,
            "tool_call_transport": ROUTE_CAP_SUPPORTED,
        },
    ),
)


def _normalize_model_name(model_name: str) -> str:
    normalized = str(model_name or "").strip()
    if normalized.startswith(("mimo_openai/", "mimo_anthropic/", "anthropic_kimi/")):
        normalized = normalized.split("/", 1)[1]
    return normalized


_MODEL_BY_ID = {spec.model_id: spec for spec in _MODEL_SPECS}
_MODEL_BY_ALIAS = {
    _normalize_model_name(alias): spec for spec in _MODEL_SPECS for alias in spec.aliases
}
_ROUTE_BY_ALIAS = {
    alias: spec for spec in _PROVIDER_ROUTE_SPECS for alias in (spec.route_id, *spec.aliases)
}


def model_specs() -> tuple[ModelSpec, ...]:
    return _MODEL_SPECS


def provider_route_specs() -> tuple[ProviderRouteSpec, ...]:
    return _PROVIDER_ROUTE_SPECS


def default_enabled_models() -> tuple[ModelSpec, ...]:
    return tuple(spec for spec in _MODEL_SPECS if spec.default_use)


def default_enabled_provider_routes() -> tuple[ProviderRouteSpec, ...]:
    return tuple(spec for spec in _PROVIDER_ROUTE_SPECS if spec.default_use)


def model_aliases() -> dict[str, str]:
    return {alias: spec.model_id for spec in _MODEL_SPECS for alias in spec.aliases}


def resolve_model(model_name: str) -> ModelSpec:
    normalized = _normalize_model_name(model_name)
    spec = _MODEL_BY_ALIAS.get(normalized) or _MODEL_BY_ID.get(normalized)
    if spec is None:
        raise KeyError(model_name)
    return spec


def maybe_resolve_model(model_name: str | None) -> ModelSpec | None:
    if not model_name:
        return None
    try:
        return resolve_model(model_name)
    except KeyError:
        return None


def model_supports_images(model_name: str | None) -> bool:
    spec = maybe_resolve_model(model_name)
    return True if spec is None else spec.supports_image_input


def required_env_keys(model_name: str) -> tuple[str, ...]:
    return resolve_model(model_name).direct_required_env_keys


def openclaw_model_id(model_name: str) -> str:
    spec = resolve_model(model_name)
    return spec.openclaw_model_id or spec.model_id


def cost_table_by_model() -> dict[str, dict[str, float]]:
    return {spec.model_id: dict(spec.cost_per_m) for spec in _MODEL_SPECS if spec.cost_per_m}


def provider_route_spec(route_id: str) -> ProviderRouteSpec:
    spec = _ROUTE_BY_ALIAS.get(route_id)
    if spec is None:
        raise KeyError(route_id)
    return spec


def normalize_provider_route(route_id: str | None, *, default: str = "") -> str:
    raw = str(route_id or default).strip()
    if not raw:
        return ""
    return provider_route_spec(raw).public_profile


def provider_routes_for_engine(agent_engine: str) -> tuple[ProviderRouteSpec, ...]:
    return tuple(spec for spec in _PROVIDER_ROUTE_SPECS if agent_engine in spec.supported_engines)


def supported_provider_profiles(agent_engine: str) -> tuple[str, ...]:
    return tuple(spec.public_profile for spec in provider_routes_for_engine(agent_engine))


def default_provider_profile(agent_engine: str) -> str | None:
    defaults = {
        "codex-cli": PROVIDER_PROFILE_CODEX_RESPONSES,
        "openai-agents-sdk": PROVIDER_PROFILE_CODEX_RESPONSES,
        "claude-code": PROVIDER_PROFILE_MIMO_ANTHROPIC,
        "openclaw-gateway": "kimi",
    }
    return defaults.get(agent_engine)


def provider_env_key(agent_engine: str) -> str | None:
    if agent_engine in {"codex-cli", "openai-agents-sdk", "claude-code"}:
        return "ROBOCLAWS_PROVIDER_PROFILE"
    return None


def resolve_provider_route_for_engine(
    agent_engine: str,
    provider_profile: str | None,
) -> ProviderRouteSpec:
    selected = normalize_provider_route(
        provider_profile,
        default=default_provider_profile(agent_engine) or "",
    )
    spec = provider_route_spec(selected)
    if agent_engine not in spec.supported_engines:
        raise ValueError(
            f"provider_profile '{selected}' is unsupported for agent_engine '{agent_engine}'"
        )
    return spec


def model_family_for_route_model(provider_profile: str, model_id: str | None = None) -> str:
    route = provider_route_spec(provider_profile)
    spec = maybe_resolve_model(model_id or route.default_model_id)
    return spec.family if spec is not None else "unknown"


def route_capabilities_for_engine(route: ProviderRouteSpec, agent_engine: str) -> dict[str, str]:
    keys = set(route.route_capabilities)
    keys.update(route.per_engine_route_capability_overrides.get(agent_engine, {}).keys())
    return {key: route.route_capability(key, agent_engine=agent_engine) for key in sorted(keys)}


def route_base_url(route: ProviderRouteSpec, env: dict[str, str] | None = None) -> str:
    env_map = os.environ if env is None else env
    if route.route_id == PROVIDER_PROFILE_MIMO_MIFY_ANTHROPIC:
        return _mify_anthropic_base_url(env_map)
    if route.base_url_env and env_map.get(route.base_url_env):
        return str(env_map[route.base_url_env])
    return route.base_url_default


def provider_readiness(
    *,
    agent_engine: str,
    provider_profile: str | None,
    model: str | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    env_map = os.environ if env is None else env
    try:
        route = resolve_provider_route_for_engine(agent_engine, provider_profile)
    except (KeyError, ValueError) as exc:
        selected = str(provider_profile or default_provider_profile(agent_engine) or "")
        return {
            "driver": _driver_for_agent_engine(agent_engine),
            "agent_engine": agent_engine,
            "provider": selected,
            "provider_profile": selected,
            "model": model or "",
            "required_env": [],
            "missing_env": [],
            "ok": False,
            "message": str(exc),
        }
    selected_model = model or route.default_model_id
    required_env = list(route.required_env_keys)
    missing_env = [key for key in required_env if not env_map.get(key)]
    if missing_env:
        required = " and ".join(required_env)
        message = (
            f"{_engine_label(agent_engine)} provider "
            f"{route.public_profile} requires {required}."
        )
    else:
        message = ""
    model_spec = maybe_resolve_model(selected_model)
    return {
        "driver": _driver_for_agent_engine(agent_engine),
        "agent_engine": agent_engine,
        "provider": route.public_profile,
        "provider_profile": route.public_profile,
        "label": route.label,
        "model": selected_model,
        "model_family": model_spec.family if model_spec else "unknown",
        "model_capabilities": sorted(model_spec.model_capabilities) if model_spec else [],
        "model_default_use": bool(model_spec.default_use) if model_spec else False,
        "model_default_use_note": model_spec.default_use_note if model_spec else "",
        "wire_api": route.wire_api,
        "wire_source": route.wire_source,
        "default_use": route.default_use,
        "default_use_note": route.default_use_note,
        "route_status": route.status_for_engine(agent_engine),
        "route_status_note": route.status_note,
        "route_capabilities": route_capabilities_for_engine(route, agent_engine),
        "required_env": required_env,
        "missing_env": missing_env,
        "base_url_env": route.base_url_env or "",
        "base_url_default": route.base_url_default,
        "ok": not missing_env,
        "message": message,
    }


def route_payload(route: ProviderRouteSpec, *, agent_engine: str) -> dict[str, Any]:
    model = resolve_model(route.default_model_id)
    return {
        "provider_profile": route.public_profile,
        "route_id": route.route_id,
        "label": route.label,
        "default_model_id": route.default_model_id,
        "model_family": model.family,
        "model_capabilities": sorted(model.model_capabilities),
        "model_default_use": model.default_use,
        "model_default_use_note": model.default_use_note,
        "required_env": list(route.required_env_keys),
        "wire_api": route.wire_api,
        "wire_source": route.wire_source,
        "default_use": route.default_use,
        "default_use_note": route.default_use_note,
        "route_status": route.status_for_engine(agent_engine),
        "route_status_note": route.status_note,
        "route_capabilities": route_capabilities_for_engine(route, agent_engine),
    }


def _mify_anthropic_base_url(env_map: dict[str, str]) -> str:
    base = env_map.get("XM_LLM_ANTHROPIC_BASE_URL") or ""
    if base:
        return base
    base = env_map.get("XM_LLM_BASE_URL") or ""
    if base:
        base = base.rstrip("/")
        if base.endswith("/anthropic"):
            return base
        if base.endswith("/v1"):
            return f"{base[:-3]}/anthropic"
        return f"{base}/anthropic"
    return "https://api.llm.mioffice.cn/anthropic"


def _driver_for_agent_engine(agent_engine: str) -> str:
    return {
        "codex-cli": "codex",
        "openai-agents-sdk": "openai-agents-sdk",
        "claude-code": "claude",
        "openclaw-gateway": "openclaw",
    }.get(agent_engine, agent_engine)


def _engine_label(agent_engine: str) -> str:
    return {
        "codex-cli": "Codex",
        "openai-agents-sdk": "OpenAI Agents SDK",
        "claude-code": "Claude",
        "openclaw-gateway": "OpenClaw",
    }.get(agent_engine, agent_engine)


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print Roboclaws provider registry facts.")
    parser.add_argument(
        "command",
        choices=[
            "base-url",
            "default-model",
            "json",
            "key-env",
            "public-profile",
            "supports-engine",
            "wire-api",
        ],
    )
    parser.add_argument("route_id", nargs="?")
    parser.add_argument("agent_engine", nargs="?")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    if args.command == "json":
        payload = {
            "models": [
                asdict(spec) | {"model_capabilities": sorted(spec.model_capabilities)}
                for spec in _MODEL_SPECS
            ],
            "provider_routes": [asdict(spec) for spec in _PROVIDER_ROUTE_SPECS],
        }
        text = json.dumps(payload, indent=2, sort_keys=True)
        if args.output:
            args.output.write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
        return 0

    if not args.route_id:
        parser.error("route_id is required")
    route = provider_route_spec(args.route_id)
    if args.command == "default-model":
        print(route.default_model_id)
    elif args.command == "base-url":
        print(route_base_url(route))
    elif args.command == "key-env":
        print(route.api_key_env or "")
    elif args.command == "public-profile":
        print(route.public_profile)
    elif args.command == "wire-api":
        print(route.wire_api)
    elif args.command == "supports-engine":
        if not args.agent_engine:
            parser.error("agent_engine is required")
        return 0 if args.agent_engine in route.supported_engines else 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised through shell helpers.
    raise SystemExit(_main())

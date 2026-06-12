"""Agent-engine and provider-profile metadata."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentEngineSpec:
    """Operator-facing agent engine with derived private runner metadata."""

    id: str
    label: str
    dispatch_runner: str
    internal_runner_class: str
    supported_provider_profiles: tuple[str, ...]
    default_provider_profile: str | None
    provider_env_key: str | None = None
    availability: str = "enabled"
    experimental: bool = False


AGENT_ENGINE_SPECS: dict[str, AgentEngineSpec] = {
    "codex-cli": AgentEngineSpec(
        id="codex-cli",
        label="Codex CLI",
        dispatch_runner="codex",
        internal_runner_class="live-agent",
        supported_provider_profiles=("codex-env", "mify"),
        default_provider_profile="codex-env",
        provider_env_key="ROBOCLAWS_CODEX_PROVIDER",
    ),
    "claude-code": AgentEngineSpec(
        id="claude-code",
        label="Claude Code",
        dispatch_runner="claude",
        internal_runner_class="live-agent",
        supported_provider_profiles=("kimi-anthropic", "mimo-anthropic", "mify-anthropic"),
        default_provider_profile="mimo-anthropic",
        provider_env_key="ROBOCLAWS_CLAUDE_PROVIDER",
    ),
    "openai-agents-sdk": AgentEngineSpec(
        id="openai-agents-sdk",
        label="OpenAI Agents SDK",
        dispatch_runner="openai-agents-live",
        internal_runner_class="live-agent",
        supported_provider_profiles=("codex-env", "mify"),
        default_provider_profile="codex-env",
        provider_env_key="ROBOCLAWS_CODEX_PROVIDER",
        availability="experimental",
        experimental=True,
    ),
    "direct-runner": AgentEngineSpec(
        id="direct-runner",
        label="Direct Runner",
        dispatch_runner="direct",
        internal_runner_class="deterministic",
        supported_provider_profiles=(),
        default_provider_profile=None,
    ),
    "openclaw-gateway": AgentEngineSpec(
        id="openclaw-gateway",
        label="OpenClaw Gateway",
        dispatch_runner="openclaw",
        internal_runner_class="gateway",
        supported_provider_profiles=("kimi",),
        default_provider_profile="kimi",
    ),
    "script-runner": AgentEngineSpec(
        id="script-runner",
        label="Script Runner",
        dispatch_runner="script",
        internal_runner_class="script",
        supported_provider_profiles=(),
        default_provider_profile=None,
    ),
}


def agent_engine_spec(agent_engine_id: str) -> AgentEngineSpec:
    """Return an agent engine spec by id."""

    return AGENT_ENGINE_SPECS[agent_engine_id]

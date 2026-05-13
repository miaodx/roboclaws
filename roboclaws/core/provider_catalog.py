from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelMetadata:
    alias: str
    canonical_model: str
    provider: str
    adapter: str
    required_env_keys: tuple[str, ...]
    supports_images: bool
    supports_tool_calls: bool = False
    openclaw_model: str | None = None


_MODELS: tuple[ModelMetadata, ...] = (
    ModelMetadata("mock", "mock", "mock", "mock", (), True),
    ModelMetadata("gpt-4o", "gpt-4o", "openai", "openai", ("OPENAI_API_KEY",), True),
    ModelMetadata(
        "gpt-4o-mini",
        "gpt-4o-mini",
        "openai",
        "openai",
        ("OPENAI_API_KEY",),
        True,
    ),
    ModelMetadata("kimi", "kimi-k2.6", "kimi", "kimi", ("KIMI_API_KEY",), True),
    ModelMetadata("kimi-k2-5", "kimi-k2-5", "kimi", "kimi", ("KIMI_API_KEY",), True),
    ModelMetadata("kimi-k2.6", "kimi-k2.6", "kimi", "kimi", ("KIMI_API_KEY",), True),
    ModelMetadata(
        "kimi-coding",
        "kimi-k2.6",
        "kimi",
        "kimi-coding",
        ("KIMI_API_KEY",),
        True,
    ),
    ModelMetadata(
        "kimi-for-coding",
        "kimi-for-coding",
        "kimi",
        "kimi-coding",
        ("KIMI_API_KEY",),
        True,
    ),
    ModelMetadata(
        "anthropic",
        "claude-3-5-sonnet-20241022",
        "anthropic",
        "anthropic",
        ("ANTHROPIC_API_KEY",),
        True,
    ),
    ModelMetadata(
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20241022",
        "anthropic",
        "anthropic",
        ("ANTHROPIC_API_KEY",),
        True,
    ),
    ModelMetadata(
        "claude-3-haiku-20240307",
        "claude-3-haiku-20240307",
        "anthropic",
        "anthropic",
        ("ANTHROPIC_API_KEY",),
        True,
    ),
    ModelMetadata(
        "nvidia",
        "meta/llama-4-maverick-17b-128e-instruct",
        "nvidia",
        "nvidia",
        ("NVIDIA_API_KEY", "NV_API_KEY"),
        True,
    ),
    ModelMetadata(
        "meta/llama-4-maverick-17b-128e-instruct",
        "meta/llama-4-maverick-17b-128e-instruct",
        "nvidia",
        "nvidia",
        ("NVIDIA_API_KEY", "NV_API_KEY"),
        True,
    ),
    ModelMetadata(
        "nvidia-nano-vl",
        "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        "nvidia",
        "nvidia",
        ("NVIDIA_API_KEY", "NV_API_KEY"),
        True,
    ),
    ModelMetadata(
        "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
        "nvidia",
        "nvidia",
        ("NVIDIA_API_KEY", "NV_API_KEY"),
        True,
    ),
    ModelMetadata(
        "mimo-omni",
        "mimo-v2-omni",
        "mimo",
        "mimo",
        ("MIMO_TP_KEY",),
        True,
        True,
        "mimo_openai/mimo-v2-omni",
    ),
    ModelMetadata(
        "mimo-v2-omni",
        "mimo-v2-omni",
        "mimo",
        "mimo",
        ("MIMO_TP_KEY",),
        True,
        True,
        "mimo_openai/mimo-v2-omni",
    ),
    ModelMetadata(
        "mimo-v2.5-pro",
        "mimo-v2.5-pro",
        "mimo",
        "mimo",
        ("MIMO_TP_KEY",),
        False,
        True,
        "mimo_openai/mimo-v2.5-pro",
    ),
    ModelMetadata(
        "mimo-v2.5",
        "mimo-v2.5",
        "mimo",
        "mimo",
        ("MIMO_TP_KEY",),
        False,
        True,
        "mimo_openai/mimo-v2.5",
    ),
)

_ALIASES = {model.alias: model for model in _MODELS}
_CANONICAL_DEFAULTS = {model.canonical_model: model for model in reversed(_MODELS)}
_OPENCLAW_IDS = {
    "kimi-k2-5": "anthropic_kimi/k2p5",
    "kimi-k2.6": "anthropic_kimi/k2.6",
    "kimi-for-coding": "anthropic_kimi/k2.6",
}


def model_aliases() -> dict[str, str]:
    return {alias: metadata.canonical_model for alias, metadata in _ALIASES.items()}


def resolve_model(model_name: str) -> ModelMetadata:
    normalized = _normalize_model_name(model_name)
    metadata = _ALIASES.get(normalized) or _CANONICAL_DEFAULTS.get(normalized)
    if metadata is None:
        raise KeyError(model_name)
    return metadata


def required_env_keys(model_name: str) -> tuple[str, ...]:
    return resolve_model(model_name).required_env_keys


def model_supports_images(model_name: str | None) -> bool:
    if not model_name:
        return True
    try:
        return resolve_model(model_name).supports_images
    except KeyError:
        return True


def openclaw_model_id(model_name: str) -> str:
    metadata = resolve_model(model_name)
    return (
        metadata.openclaw_model
        or _OPENCLAW_IDS.get(metadata.canonical_model)
        or metadata.canonical_model
    )


def _normalize_model_name(model_name: str) -> str:
    normalized = model_name.strip()
    if normalized.startswith(("mimo_openai/", "mimo_anthropic/", "anthropic_kimi/")):
        normalized = normalized.split("/", 1)[1]
    if normalized == "k2p5":
        return "kimi-k2-5"
    if normalized == "k2.6":
        return "kimi-k2.6"
    return normalized

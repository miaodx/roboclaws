#!/usr/bin/env python3
"""Seed OpenClaw config directly for the single-container Railway appliance.

This is the appliance equivalent of ``scripts/openclaw-bootstrap.sh``. It does
not run Docker. It writes ``/home/node/.openclaw/openclaw.json``, credentials,
agent workspaces, skill files, and a runtime env file consumed by supervisord.
"""

from __future__ import annotations

import json
import os
import pwd
import shlex
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# When loaded via ``python3 scripts/appliance_seed_openclaw.py`` the script's
# dir is auto-prepended to sys.path; when loaded via ``importlib`` (test path)
# it is not. Make the sibling import work in both cases.
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from openclaw_plugin_allowlist import ALLOWED as OPENCLAW_PLUGIN_ALLOW  # noqa: E402

from roboclaws.core.provider_catalog import (  # noqa: E402
    model_supports_images,
    openclaw_model_id,
)


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str
    custom_provider_id: str
    provider_env_var: str
    provider_api_key: str
    model: str
    image_model: str
    provider_base_url: str = ""
    extra_models: list[dict[str, Any]] | None = None
    provider_entry: dict[str, Any] | None = None


@dataclass(frozen=True)
class RuntimeConfig:
    provider: ProviderConfig
    token: str
    agent_ids: list[str]
    base_dir: Path
    data_dir: Path
    run_dir: Path
    snapshots_root: Path
    env_file: Path
    mcp_url: str
    tool_profile: str
    timeout_seconds: int
    allowed_origins: list[str]
    trusted_proxies: list[str]
    control_ui_disable_device_auth: bool


def _env_int(env: dict[str, str], name: str, default: int) -> int:
    raw = env.get(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer, got {raw!r}") from exc
    return value


def _env_bool(env: dict[str, str], name: str, default: bool) -> bool:
    raw = env.get(name)
    if raw is None or raw.strip() == "":
        return default
    normalized = raw.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SystemExit(f"{name} must be a boolean, got {raw!r}")


def _agent_ids(env: dict[str, str]) -> list[str]:
    count = _env_int(env, "AGENTS", 1)
    if count < 1 or count > 8:
        raise SystemExit(f"AGENTS must be 1..8, got {count}")
    prefix = env.get("AGENT_PREFIX", "agent-")
    return [f"{prefix}{i}" for i in range(count)]


def _csv_values(env: dict[str, str], name: str) -> list[str]:
    return [value.strip() for value in env.get(name, "").split(",") if value.strip()]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _allowed_origins(env: dict[str, str]) -> list[str]:
    port = env.get("PORT", "8080").strip() or "8080"
    public_url = env.get("ROBOCLAWS_PUBLIC_URL", "").strip().rstrip("/")
    railway_domain = env.get("RAILWAY_PUBLIC_DOMAIN", "").strip()

    values: list[str] = []
    if public_url:
        values.append(public_url)
    if railway_domain:
        values.append(f"https://{railway_domain}")
    values.extend(
        [
            f"http://127.0.0.1:{port}",
            f"http://localhost:{port}",
        ]
    )
    values.extend(_csv_values(env, "OPENCLAW_ALLOWED_ORIGINS"))
    return _unique(values)


def _trusted_proxies(env: dict[str, str]) -> list[str]:
    values = ["127.0.0.1", "::1"]
    values.extend(_csv_values(env, "OPENCLAW_TRUSTED_PROXIES"))
    return _unique(values)


def _provider_config(env: dict[str, str]) -> ProviderConfig:
    provider = env.get("PROVIDER", "mimo")
    if provider == "mimo":
        api_key = env.get("MIMO_TP_KEY", "")
        if not api_key:
            raise SystemExit("MIMO_TP_KEY is required for PROVIDER=mimo")
        mode = env.get("MIMO_PROVIDER_MODE", "openai")
        if mode != "openai":
            raise SystemExit("The appliance currently supports MIMO_PROVIDER_MODE=openai")
        model = env.get("MODEL", openclaw_model_id("mimo-v2-omni"))
        image_model = env.get("IMAGE_MODEL", "")
        if not image_model and not model_supports_images(model):
            image_model = openclaw_model_id("mimo-v2-omni")
        image_model = image_model or model
        return ProviderConfig(
            provider_id="mimo",
            custom_provider_id="mimo_openai",
            provider_env_var="MIMO_TP_KEY",
            provider_api_key=api_key,
            model=model,
            image_model=image_model,
            provider_entry={
                "baseUrl": "https://token-plan-cn.xiaomimimo.com/v1",
                "apiKey": api_key,
                "auth": "api-key",
                "api": "openai-completions",
                "models": [
                    {
                        "id": "mimo-v2-omni",
                        "name": "MiMo V2 Omni (vision+tools)",
                        "input": ["text", "image"],
                        "reasoning": False,
                        "contextWindow": 262144,
                        "maxTokens": 32768,
                    },
                    {
                        "id": "mimo-v2.5-pro",
                        "name": "MiMo V2.5 Pro (text+tools)",
                        "input": ["text"],
                        "reasoning": False,
                        "contextWindow": 1048576,
                        "maxTokens": 32768,
                    },
                    {
                        "id": "mimo-v2.5",
                        "name": "MiMo V2.5 (text+tools)",
                        "input": ["text"],
                        "reasoning": False,
                        "contextWindow": 1048576,
                        "maxTokens": 32768,
                    },
                ],
            },
        )

    if provider == "kimi":
        api_key = env.get("KIMI_API_KEY", "")
        if not api_key:
            raise SystemExit("KIMI_API_KEY is required for PROVIDER=kimi")
        model = env.get("MODEL", openclaw_model_id("kimi-k2.6"))
        image_model = env.get("IMAGE_MODEL", model)
        return ProviderConfig(
            provider_id="kimi",
            custom_provider_id="anthropic_kimi",
            provider_env_var="KIMI_API_KEY",
            provider_api_key=api_key,
            model=model,
            image_model=image_model,
            provider_entry={
                "baseUrl": "https://api.kimi.com/coding/",
                "apiKey": api_key,
                "auth": "api-key",
                "api": "anthropic-messages",
                "headers": {
                    "User-Agent": "Claude-Code/1.0",
                    "anthropic-version": "2023-06-01",
                },
                "models": [
                    {
                        "id": "k2p5",
                        "name": "Kimi K2.5 (anthropic-messages)",
                        "input": ["text", "image"],
                        "reasoning": False,
                        "contextWindow": 262144,
                        "maxTokens": 32768,
                    },
                    {
                        "id": "k2.6",
                        "name": "Kimi 2.6 (anthropic-messages)",
                        "input": ["text", "image"],
                        "reasoning": False,
                        "contextWindow": 262144,
                        "maxTokens": 32768,
                    },
                ],
            },
        )

    if provider == "nvidia":
        api_key = env.get("NV_API_KEY") or env.get("NVIDIA_API_KEY", "")
        if not api_key:
            raise SystemExit("NV_API_KEY or NVIDIA_API_KEY is required for PROVIDER=nvidia")
        model = env.get("MODEL", "nvidia/nvidia/nemotron-nano-12b-v2-vl")
        image_model = env.get("IMAGE_MODEL", model)
        return ProviderConfig(
            provider_id="nvidia",
            custom_provider_id="nvidia",
            provider_env_var="NVIDIA_API_KEY",
            provider_api_key=api_key,
            model=model,
            image_model=image_model,
            provider_base_url="https://integrate.api.nvidia.com/v1",
            extra_models=[
                {
                    "id": "nvidia/nemotron-nano-12b-v2-vl",
                    "name": "NVIDIA Nemotron Nano 12B V2 VL",
                    "input": ["text", "image"],
                    "reasoning": False,
                    "contextWindow": 131072,
                    "maxTokens": 4096,
                }
            ],
        )

    raise SystemExit(f"Unsupported PROVIDER={provider!r}; expected mimo, kimi, or nvidia")


def _copy_skill_tree(src: Path, dest: Path) -> None:
    if not src.is_dir():
        raise SystemExit(f"Skill directory not found: {src}")
    if dest.exists() or dest.is_symlink():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def _replace_with_symlink(link: Path, target: Path) -> None:
    target.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target)


def _openclaw_json(runtime: RuntimeConfig) -> dict[str, Any]:
    provider = runtime.provider
    defaults_cfg: dict[str, Any] = {
        "model": {"primary": provider.model},
        "imageModel": {"primary": provider.image_model},
        "timeoutSeconds": runtime.timeout_seconds,
    }
    if runtime.tool_profile == "minimal":
        defaults_cfg["compaction"] = {"memoryFlush": {"enabled": False}}

    control_ui_cfg: dict[str, Any] = {"allowedOrigins": runtime.allowed_origins}
    if runtime.control_ui_disable_device_auth:
        control_ui_cfg["dangerouslyDisableDeviceAuth"] = True

    config: dict[str, Any] = {
        "gateway": {
            "auth": {"mode": "token", "token": runtime.token},
            "http": {"endpoints": {"chatCompletions": {"enabled": True}}},
            "controlUi": control_ui_cfg,
            "trustedProxies": runtime.trusted_proxies,
        },
        "agents": {
            "defaults": defaults_cfg,
            "list": [
                {
                    "id": agent_id,
                    "workspace": f"/home/node/.openclaw/workspaces/{agent_id}",
                    "agentDir": f"/home/node/.openclaw/agents/{agent_id}/agent",
                    "model": {"primary": provider.model},
                    # alsoAllow=["bundle-mcp"] mirrors the openclaw-bootstrap.sh
                    # fix from commit 934fa88. Image 2026.4.25-beta.11+ no
                    # longer auto-includes the bundle-mcp policy in the
                    # `minimal` profile, so without this splice the agent ends
                    # up with only `session_status` and every roboclaws__* tool
                    # disappears from the tool list — the model then sees an
                    # empty toolset and hallucinates "I have no tools".
                    # See docs/openclw/openclaw-tool-profiles.md for the image diff.
                    "tools": {
                        "profile": runtime.tool_profile,
                        "alsoAllow": ["bundle-mcp"],
                    },
                }
                for agent_id in runtime.agent_ids
            ],
        },
        "mcp": {
            "servers": {
                "roboclaws": {
                    "transport": "streamable-http",
                    "url": runtime.mcp_url,
                }
            }
        },
        # Strict allow-list: only these plugins activate, regardless of the
        # gateway image's enabled-by-default set. See
        # ``scripts/openclaw_plugin_allowlist.py`` for the rationale and
        # per-entry justification. Adding a provider (or upgrading to a
        # gateway image whose new enabled-by-default plugin we actually
        # need) requires editing that file in lockstep.
        #
        # ``entries.acpx.config.probeAgent`` pins the embedded-ACP health
        # probe to one of OUR agents instead of the upstream default
        # ``codex`` — which isn't installed and was suspected of stalling
        # the post-pricing-fetch sidecar startup window (~90s of
        # ``chat.history unavailable during gateway startup``).
        # See acpx manifest ``probeAgent`` field for the documented
        # rationale: "Set this explicitly so the whole embedded ACP
        # backend does not get marked unavailable" when the default isn't
        # authenticated.
        "plugins": {
            "allow": list(OPENCLAW_PLUGIN_ALLOW),
            # ``enabled: true`` is required alongside ``config`` — without it
            # the entries-system marks the plugin as
            # ``bundled (disabled by default)`` and silently ignores the
            # config block. Probed live 2026-04-28: setting only
            # ``config.probeAgent`` produced ``plugin disabled but config is
            # present`` and the embedded ACP backend stayed unconfigured.
            "entries": {
                "acpx": {
                    "enabled": True,
                    "config": {"probeAgent": runtime.agent_ids[0]},
                },
            },
        },
    }

    if provider.provider_entry is not None:
        config["models"] = {
            "mode": "replace",
            "providers": {provider.custom_provider_id: provider.provider_entry},
        }
    elif provider.extra_models:
        entry: dict[str, Any] = {"models": provider.extra_models}
        if provider.provider_base_url:
            entry["baseUrl"] = provider.provider_base_url
            entry["api"] = "openai-completions"
        config["models"] = {
            "mode": "merge",
            "providers": {provider.provider_id: entry},
        }
    return config


def _write_auth_profiles(runtime: RuntimeConfig) -> None:
    provider = runtime.provider
    profile = {
        "profiles": {
            f"{provider.custom_provider_id}:manual": {
                "type": "api_key",
                "provider": provider.custom_provider_id,
                "key": provider.provider_api_key,
            }
        }
    }
    if provider.custom_provider_id != provider.provider_id:
        profile["profiles"][f"{provider.provider_id}:manual"] = {
            "type": "api_key",
            "provider": provider.provider_id,
            "key": provider.provider_api_key,
        }
    for agent_id in runtime.agent_ids + ["main"]:
        path = runtime.base_dir / "agents" / agent_id / "agent" / "auth-profiles.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
        path.chmod(0o600)


def _write_runtime_env(runtime: RuntimeConfig) -> None:
    provider = runtime.provider
    values = {
        "OPENCLAW_TOKEN": runtime.token,
        "OPENCLAW_GATEWAY_TOKEN": runtime.token,
        "PROVIDER": provider.provider_id,
        "MODEL": provider.model,
        "IMAGE_MODEL": provider.image_model,
        "ROBOCLAWS_MCP_URL": runtime.mcp_url,
        "ROBOCLAWS_TOOL_PROFILE": runtime.tool_profile,
        "ROBOCLAWS_RUN_DIR": str(runtime.run_dir),
        "ROBOCLAWS_SNAPSHOTS_DIR": str(runtime.snapshots_root),
        provider.provider_env_var: provider.provider_api_key,
    }
    runtime.env_file.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"export {key}={shlex.quote(value)}" for key, value in values.items()]
    runtime.env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    runtime.env_file.chmod(0o600)


def _chown_node(path: Path) -> None:
    if os.name != "posix" or not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    try:
        node = pwd.getpwnam("node")
    except KeyError:
        return
    for current in [path, *path.rglob("*")]:
        try:
            os.chown(current, node.pw_uid, node.pw_gid)
        except FileNotFoundError:
            continue


def seed(env: dict[str, str] | None = None) -> RuntimeConfig:
    env = dict(os.environ if env is None else env)
    base_dir = Path(env.get("OPENCLAW_HOME", "/home/node/.openclaw"))
    data_dir = Path(env.get("DATA_DIR", "/data"))
    run_dir = Path(env.get("ROBOCLAWS_RUN_DIR", data_dir / "runs" / "current"))
    snapshots_root = Path(env.get("ROBOCLAWS_SNAPSHOTS_DIR", run_dir / "snapshots"))
    env_file = Path(env.get("APPLIANCE_ENV_FILE", data_dir / "appliance" / "runtime.env"))
    token = env.get("OPENCLAW_TOKEN") or env.get("DEMO_PASSWORD", "")
    if not token:
        raise SystemExit("DEMO_PASSWORD or OPENCLAW_TOKEN is required")
    tool_profile = env.get("ROBOCLAWS_TOOL_PROFILE", "minimal")
    if tool_profile not in {"minimal", "coding", "messaging"}:
        raise SystemExit(f"Unsupported ROBOCLAWS_TOOL_PROFILE={tool_profile!r}")

    runtime = RuntimeConfig(
        provider=_provider_config(env),
        token=token,
        agent_ids=_agent_ids(env),
        base_dir=base_dir,
        data_dir=data_dir,
        run_dir=run_dir,
        snapshots_root=snapshots_root,
        env_file=env_file,
        mcp_url=env.get("ROBOCLAWS_MCP_URL", "http://127.0.0.1:18788/mcp"),
        tool_profile=tool_profile,
        timeout_seconds=_env_int(env, "TIMEOUT_SECONDS", 600),
        allowed_origins=_allowed_origins(env),
        trusted_proxies=_trusted_proxies(env),
        control_ui_disable_device_auth=_env_bool(
            env,
            "OPENCLAW_CONTROL_UI_DISABLE_DEVICE_AUTH",
            True,
        ),
    )

    skill_src = Path(env.get("SKILLS_DIR", "/opt/roboclaws/skills/ai2thor-navigator"))
    skill_name = skill_src.name
    base_dir.mkdir(parents=True, exist_ok=True)
    (base_dir / "logs").mkdir(parents=True, exist_ok=True)
    runtime.run_dir.mkdir(parents=True, exist_ok=True)
    runtime.snapshots_root.mkdir(parents=True, exist_ok=True)

    for agent_id in runtime.agent_ids:
        agent_dir = base_dir / "agents" / agent_id / "agent"
        workspace = base_dir / "workspaces" / agent_id
        agent_dir.mkdir(parents=True, exist_ok=True)
        (workspace / "skills").mkdir(parents=True, exist_ok=True)
        (workspace / "state").mkdir(parents=True, exist_ok=True)
        _copy_skill_tree(skill_src, workspace / "skills" / skill_name)
        _replace_with_symlink(workspace / "snapshots", runtime.snapshots_root / agent_id)

    (base_dir / "agents" / "main" / "agent").mkdir(parents=True, exist_ok=True)
    (base_dir / "workspace" / "skills").mkdir(parents=True, exist_ok=True)
    (base_dir / "workspace" / "state").mkdir(parents=True, exist_ok=True)

    (base_dir / "openclaw.json").write_text(
        json.dumps(_openclaw_json(runtime), indent=2),
        encoding="utf-8",
    )
    _write_auth_profiles(runtime)
    _write_runtime_env(runtime)
    _chown_node(base_dir)
    _chown_node(runtime.data_dir)
    return runtime


def main() -> int:
    runtime = seed()
    print(f"seeded OpenClaw appliance config at {runtime.base_dir}")
    print(f"agent ids: {', '.join(runtime.agent_ids)}")
    print(f"model: {runtime.provider.model}")
    print(f"runtime env: {runtime.env_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

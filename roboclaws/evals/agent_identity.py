"""Agent-engine identity helpers for eval runs."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from roboclaws.agents.provider_registry import provider_readiness
from roboclaws.evals.models import (
    MISSING_NOT_APPLICABLE,
    MISSING_SENTINELS,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalTrial,
)
from roboclaws.launch.agent_engines import AGENT_ENGINE_SPECS, AgentEngineSpec

REPO_ROOT = Path(__file__).resolve().parents[2]


def agent_engine_spec(agent_engine: str) -> AgentEngineSpec:
    engine_id = str(agent_engine or "direct-runner").strip()
    try:
        return AGENT_ENGINE_SPECS[engine_id]
    except KeyError as exc:
        raise ValueError(f"unknown eval agent_engine {engine_id!r}") from exc


def eval_provider_profile(*, agent_engine: str, provider_profile: str | None) -> str:
    engine = AGENT_ENGINE_SPECS[agent_engine]
    if not engine.supported_provider_profiles:
        if provider_profile:
            raise ValueError(f"agent_engine {agent_engine!r} does not accept provider_profile")
        return MISSING_NOT_APPLICABLE
    selected = str(provider_profile or engine.default_provider_profile or "").strip()
    if selected not in engine.supported_provider_profiles:
        expected = "|".join(engine.supported_provider_profiles)
        raise ValueError(
            f"provider_profile {selected!r} is unsupported for agent_engine {agent_engine!r}; "
            f"expected {expected}"
        )
    return selected


def validate_sample_agent(sample: EvalSample, *, agent_engine: str) -> None:
    if agent_engine not in sample.allowed_agent_engines:
        if agent_engine == "direct-runner":
            raise ValueError(
                f"sample {sample.sample_id!r} does not allow the deterministic direct-runner"
            )
        raise ValueError(
            f"sample {sample.sample_id!r} does not allow agent_engine {agent_engine!r}"
        )


def blocked_result_from_live_agent_request(
    trial: EvalTrial,
    *,
    agent_engine: str,
    run_dir: Path,
) -> EvalResult:
    preflight = live_agent_eval_preflight(
        agent_engine=agent_engine,
        provider_profile=trial.provider_profile,
        model=None if trial.model in MISSING_SENTINELS else trial.model,
    )
    missing_env = preflight.get("provider_readiness", {}).get("missing_env") or []
    missing_detail = (
        f"; missing provider env: {', '.join(str(item) for item in missing_env)}"
        if missing_env
        else ""
    )
    return EvalResult.from_trial(
        trial,
        status="blocked",
        failure_class="model_or_provider_unavailable",
        grader_outputs={
            "runner": {
                "status": "blocked",
                "error_type": "LiveAgentEvalNotExecuted",
                "message": (
                    f"eval runner recorded live-agent identity for {agent_engine}, "
                    "but provider/runtime execution is not implemented in the repo-native "
                    f"eval runner yet{missing_detail}"
                ),
                "preflight": preflight,
                "required_action": "run a supported live-agent eval runtime on an allowed network",
            }
        },
        artifacts={"run_dir": str(run_dir)},
        artifact_schema_versions={"run_dir": MISSING_UNAVAILABLE},
        metrics={"pass": 0.0},
        limitations=(*trial.limitations, "live_agent_eval_runtime_not_implemented"),
    )


def live_agent_eval_preflight(
    *,
    agent_engine: str,
    provider_profile: str,
    model: str | None,
) -> dict[str, Any]:
    """Return non-secret readiness details for a blocked live-agent eval request."""

    return {
        "schema": "roboclaws_live_eval_preflight_v1",
        "agent_engine": agent_engine,
        "provider_profile": provider_profile,
        "model": model or MISSING_UNAVAILABLE,
        "provider_readiness": provider_readiness(
            agent_engine=agent_engine,
            provider_profile=None if provider_profile in MISSING_SENTINELS else provider_profile,
            model=model,
        ),
        "runtime_readiness": _runtime_readiness(agent_engine),
        "execution_status": "blocked",
        "blocker": "repo_native_live_eval_execution_not_integrated",
    }


def _runtime_readiness(agent_engine: str) -> dict[str, Any]:
    runtime: dict[str, Any] = {
        "repo_native_live_eval_runner": "not_implemented",
        "product_route_available": "use just run::surface for manual live proof",
    }
    if agent_engine in {"codex-cli", "claude-code"}:
        script = REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh"
        runtime.update(
            {
                "required_runtime": "docker-backed coding-agent CLI",
                "coding_agent_docker_script": "available" if script.exists() else "missing",
                "docker_cli": "available" if shutil.which("docker") else "missing",
                "tmux_cli": "available" if shutil.which("tmux") else "missing",
            }
        )
    elif agent_engine == "openai-agents-sdk":
        script = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_openai_agents_cleanup.py"
        runtime.update(
            {
                "required_runtime": "OpenAI Agents SDK cleanup runner",
                "live_runner_script": "available" if script.exists() else "missing",
            }
        )
    else:
        runtime["required_runtime"] = MISSING_UNAVAILABLE
    return runtime

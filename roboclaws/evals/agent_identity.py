"""Agent-engine identity helpers for eval runs."""

from __future__ import annotations

from pathlib import Path

from roboclaws.evals.models import (
    MISSING_NOT_APPLICABLE,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalTrial,
)
from roboclaws.launch.agent_engines import AGENT_ENGINE_SPECS, AgentEngineSpec


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
                    "eval runner yet"
                ),
                "required_action": "run a supported live-agent eval runtime on an allowed network",
            }
        },
        artifacts={"run_dir": str(run_dir)},
        artifact_schema_versions={"run_dir": MISSING_UNAVAILABLE},
        metrics={"pass": 0.0},
        limitations=(*trial.limitations, "live_agent_eval_runtime_not_implemented"),
    )

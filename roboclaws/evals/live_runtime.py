"""Live product-route adapter for eval trials."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from roboclaws.evals.dependencies import dependency_failure, resolve_artifact_dependencies
from roboclaws.evals.models import (
    MISSING_NOT_APPLICABLE,
    MISSING_SENTINELS,
    MISSING_UNAVAILABLE,
    EvalResult,
    EvalSample,
    EvalTrial,
)
from roboclaws.household.backend_contract import SYNTHETIC_BACKEND
from roboclaws.launch.backends import BACKEND_SPECS
from roboclaws.launch.catalog import SURFACE_SPECS
from roboclaws.launch.goals import normalize_goal_contract
from roboclaws.launch.intents import TASK_INTENT_SPECS

REPO_ROOT = Path(__file__).resolve().parents[2]
ProductRun = Callable[..., dict[str, Any]]
DEFAULT_DETACHED_LIVE_TIMEOUT_S = 3600.0
DEFAULT_LIVE_TIMEOUT_COMPLETION_GRACE_S = 30.0


@dataclass(frozen=True)
class LiveTrialHooks:
    """Runner-owned grading hooks needed after a live surface run completes."""

    failed_result_from_dependency: Callable[[EvalTrial, Path, dict[str, Any]], EvalResult]
    blocked_result_from_exception: Callable[[EvalTrial, Exception], EvalResult]
    grade_trial: Callable[..., dict[str, Any]]
    status_from_graders: Callable[[dict[str, Any]], tuple[str, str]]
    artifact_paths: Callable[[Path], dict[str, Any]]
    metrics_from_graders: Callable[..., dict[str, Any]]


def run_live_eval_trial(
    *,
    sample: EvalSample,
    trial: EvalTrial,
    run_dir: Path,
    budget: str,
    repetition_index: int,
    sample_artifacts: dict[str, dict[str, Any]],
    agent_engine: str,
    provider_profile: str,
    model: str | None,
    live_timeout_s: float | None,
    live_product_runner: ProductRun,
    hooks: LiveTrialHooks,
) -> EvalResult:
    """Run and grade one live-agent eval trial through the product surface."""

    dependency_artifacts = resolve_artifact_dependencies(
        sample,
        repetition_index=repetition_index,
        sample_artifacts=sample_artifacts,
    )
    failure = dependency_failure(dependency_artifacts)
    if failure is not None:
        return hooks.failed_result_from_dependency(trial, run_dir, failure)
    try:
        run_result = live_product_runner(
            **live_product_run_kwargs(
                sample,
                run_dir=run_dir,
                budget=budget,
                dependency_artifacts=dependency_artifacts,
                agent_engine=agent_engine,
                provider_profile=provider_profile,
                model=model,
                live_timeout_s=live_timeout_s,
            )
        )
    except Exception as exc:  # noqa: BLE001 - eval packets must classify runner failures.
        return hooks.blocked_result_from_exception(trial, exc)

    effective_run_dir = Path(str(run_result.get("eval_effective_run_dir") or run_dir))
    grader_outputs = hooks.grade_trial(
        sample=sample,
        run_dir=effective_run_dir,
        run_result=run_result,
        dependency_artifacts=dependency_artifacts,
    )
    status, failure_class = hooks.status_from_graders(grader_outputs)
    artifacts = hooks.artifact_paths(effective_run_dir)
    metrics = hooks.metrics_from_graders(
        grader_outputs,
        status=status,
        run_result=run_result,
    )
    return EvalResult.from_trial(
        trial,
        status=status,
        failure_class=failure_class,
        grader_outputs=grader_outputs,
        artifacts=artifacts,
        artifact_schema_versions={key: MISSING_UNAVAILABLE for key in artifacts},
        metrics=metrics,
        limitations=trial.limitations,
    )


def run_live_surface_product(**kwargs: Any) -> dict[str, Any]:
    """Run one live eval trial through the public surface runner and load artifacts."""

    run_dir = Path(kwargs["output_dir"])
    sample_run_root = run_dir / "surface-run"
    sample_run_root.mkdir(parents=True, exist_ok=True)
    sample_run_dir = live_surface_run_dir(kwargs, output_dir=sample_run_root)
    command = live_surface_command(kwargs, output_dir=sample_run_root)
    env = live_surface_env(kwargs, base_env=os.environ)
    started = time.monotonic()
    record: dict[str, Any] = {
        "command": command,
        "returncode": None,
        "stdout": "",
        "stderr": "",
        "effective_run_dir": str(sample_run_dir),
    }
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            env=env,
            check=False,
            capture_output=True,
            text=True,
            timeout=kwargs.get("live_timeout_s"),
        )
    except subprocess.TimeoutExpired as exc:
        sample_run_dir = discover_live_surface_run_dir(
            kwargs,
            output_dir=sample_run_root,
            fallback_run_dir=sample_run_dir,
            stdout=exc.stdout or "",
        )
        sample_run_dir = wait_for_timed_out_live_surface_artifact(
            kwargs,
            output_dir=sample_run_root,
            effective_run_dir=sample_run_dir,
        )
        record.update(
            {
                "returncode": "timeout",
                "stdout": exc.stdout or "",
                "stderr": exc.stderr or "",
                "timeout_s": kwargs.get("live_timeout_s"),
                "timeout_completion_grace_s": live_timeout_completion_grace_s(),
                "effective_run_dir": str(sample_run_dir),
                "live_status": _load_json(sample_run_dir / "live_status.json"),
            }
        )
        run_result_path = sample_run_dir / "run_result.json"
        run_result = _load_json(run_result_path)
        if run_result:
            record["returncode"] = "timeout_after_completion"
            _write_live_eval_command_record(run_dir / "live_eval_command.json", record)
            run_result["eval_effective_run_dir"] = str(sample_run_dir)
            return run_result
        _write_live_eval_command_record(run_dir / "live_eval_command.json", record)
        raise TimeoutError(
            f"live eval trial timed out after {kwargs.get('live_timeout_s')}s"
        ) from exc

    sample_run_dir = discover_live_surface_run_dir(
        kwargs,
        output_dir=sample_run_root,
        fallback_run_dir=sample_run_dir,
        stdout=completed.stdout,
    )
    record.update(
        {
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "effective_run_dir": str(sample_run_dir),
            "live_status": _load_json(sample_run_dir / "live_status.json"),
        }
    )
    if completed.returncode != 0:
        _write_live_eval_command_record(run_dir / "live_eval_command.json", record)
        run_result = _recover_open_ended_run_result_after_nonzero_exit(
            kwargs,
            sample_run_dir=sample_run_dir,
        )
        if run_result:
            sample_run_dir = wait_for_live_surface_completion(
                kwargs,
                output_dir=sample_run_root,
                effective_run_dir=sample_run_dir,
                elapsed_s=time.monotonic() - started,
                allow_open_ended_checker_failure=True,
            )
            run_result["eval_effective_run_dir"] = str(sample_run_dir)
            return run_result
        message = completed.stderr.strip() or completed.stdout.strip()
        raise RuntimeError(f"live surface run failed with exit {completed.returncode}: {message}")
    sample_run_dir = wait_for_live_surface_completion(
        kwargs,
        output_dir=sample_run_root,
        effective_run_dir=sample_run_dir,
        elapsed_s=time.monotonic() - started,
        allow_open_ended_checker_failure=_is_open_ended_eval_sample(kwargs),
    )
    record["effective_run_dir"] = str(sample_run_dir)
    record["live_status"] = _load_json(sample_run_dir / "live_status.json")
    _write_live_eval_command_record(run_dir / "live_eval_command.json", record)
    run_result_path = sample_run_dir / "run_result.json"
    run_result = _load_json(run_result_path)
    if not run_result:
        raise RuntimeError(f"live surface run finished without {run_result_path}")
    run_result["eval_effective_run_dir"] = str(sample_run_dir)
    return run_result


def live_surface_command(kwargs: dict[str, Any], *, output_dir: Path) -> list[str]:
    """Build the public surface command for one live eval trial."""

    sample: EvalSample | None = kwargs.get("eval_sample")
    evidence_lane = live_evidence_lane(kwargs)
    command = [
        sys.executable,
        "-m",
        "roboclaws.cli.main",
        "run",
        "surface",
        "surface=household-world",
        f"world={sample.world if sample else 'molmospaces/val_0'}",
        f"backend={_public_backend_from_implementation(str(kwargs.get('backend') or ''))}",
        f"agent_engine={kwargs['agent_engine']}",
        f"provider_profile={kwargs['provider_profile']}",
        f"evidence_lane={evidence_lane}",
        f"seed={kwargs['seed']}",
        f"output_dir={output_dir}",
        f"run_dir={live_surface_run_dir(kwargs, output_dir=output_dir)}",
        f"scene_source={kwargs['scene_source']}",
        f"scene_index={kwargs['scene_index']}",
    ]
    if sample is not None and sample.preset not in {"", MISSING_NOT_APPLICABLE}:
        command.append(f"preset={sample.preset}")
    elif sample is not None and sample.intent == "map-build":
        command.append("preset=map-build")
    if _is_smoke_budget(kwargs):
        command.append("run_preset=smoke")
    else:
        relocation_count = _generated_mess_count(kwargs)
        if relocation_count:
            command.append("scenario_setup=relocate-cleanup-related-objects")
            command.append(f"relocation_count={relocation_count}")
    runtime_map_prior = str(kwargs.get("runtime_map_prior_path") or "")
    if runtime_map_prior:
        command.append(f"runtime_map_prior={runtime_map_prior}")
    goal_contract = str(kwargs.get("goal_contract_json") or "")
    if goal_contract:
        command.append(f"goal_contract_json={goal_contract}")
    task_prompt = str(kwargs.get("task_prompt") or "")
    if task_prompt and (sample is None or sample.prompt not in {"", MISSING_NOT_APPLICABLE}):
        command.append(f"prompt={task_prompt}")
    return command


def live_surface_run_dir(kwargs: dict[str, Any], *, output_dir: Path) -> Path:
    """Return the preferred artifact directory for one public surface run."""

    return output_dir / f"seed-{int(kwargs['seed'])}"


def discover_live_surface_run_dir(
    kwargs: dict[str, Any],
    *,
    output_dir: Path,
    fallback_run_dir: Path,
    stdout: str = "",
) -> Path:
    """Return the actual artifact directory created by the public live route."""

    seed_leaf = f"seed-{int(kwargs['seed'])}"
    candidates = [fallback_run_dir]
    stdout_dir = _live_surface_run_dir_from_stdout(stdout)
    if stdout_dir is not None:
        candidates.append(stdout_dir)
    candidates.extend(
        sorted(
            (candidate for candidate in output_dir.glob(f"*/{seed_leaf}") if candidate.is_dir()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    )
    candidates.extend(
        sorted(
            (candidate for candidate in output_dir.glob(seed_leaf) if candidate.is_dir()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
    )
    for candidate in candidates:
        if _live_surface_run_dir_has_evidence(candidate):
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return fallback_run_dir


def wait_for_live_surface_completion(
    kwargs: dict[str, Any],
    *,
    output_dir: Path,
    effective_run_dir: Path,
    elapsed_s: float = 0.0,
    poll_s: float = 1.0,
    allow_open_ended_checker_failure: bool = False,
) -> Path:
    """Wait for a detached live product route to finish when the route returns early."""

    if (
        (effective_run_dir / "run_result.json").is_file()
        and not allow_open_ended_checker_failure
    ):
        return effective_run_dir
    if _live_surface_run_is_terminal(
        effective_run_dir,
        allow_open_ended_checker_failure=allow_open_ended_checker_failure,
    ):
        return effective_run_dir
    if not _live_surface_route_can_detach(kwargs):
        return effective_run_dir

    timeout_s = kwargs.get("live_timeout_s")
    if timeout_s is None:
        timeout_s = DEFAULT_DETACHED_LIVE_TIMEOUT_S
    remaining_s = max(float(timeout_s) - max(elapsed_s, 0.0), 0.0)
    deadline = time.monotonic() + remaining_s
    while time.monotonic() <= deadline:
        effective_run_dir = discover_live_surface_run_dir(
            kwargs,
            output_dir=output_dir,
            fallback_run_dir=effective_run_dir,
        )
        if (effective_run_dir / "run_result.json").is_file():
            status = _load_json(effective_run_dir / "live_status.json")
            if status and status.get("exit_status") in {0}:
                return effective_run_dir
            if _live_surface_run_is_terminal(
                effective_run_dir,
                allow_open_ended_checker_failure=allow_open_ended_checker_failure,
            ):
                return effective_run_dir
        elif _live_surface_run_is_terminal(
            effective_run_dir,
            allow_open_ended_checker_failure=allow_open_ended_checker_failure,
        ):
            return effective_run_dir
        time.sleep(max(poll_s, 0.05))
    effective_run_dir = wait_for_timed_out_live_surface_artifact(
        kwargs,
        output_dir=output_dir,
        effective_run_dir=effective_run_dir,
        poll_s=poll_s,
    )
    if (effective_run_dir / "run_result.json").is_file():
        return effective_run_dir
    raise TimeoutError(
        f"detached live eval trial did not finish within {timeout_s:g}s: {effective_run_dir}"
    )


def wait_for_timed_out_live_surface_artifact(
    kwargs: dict[str, Any],
    *,
    output_dir: Path,
    effective_run_dir: Path,
    poll_s: float = 1.0,
) -> Path:
    """Give detached routes a short grace window after subprocess timeout."""

    if not _live_surface_route_can_detach(kwargs):
        return effective_run_dir
    deadline = time.monotonic() + live_timeout_completion_grace_s()
    while time.monotonic() <= deadline:
        effective_run_dir = discover_live_surface_run_dir(
            kwargs,
            output_dir=output_dir,
            fallback_run_dir=effective_run_dir,
        )
        if (effective_run_dir / "run_result.json").is_file():
            return effective_run_dir
        time.sleep(max(poll_s, 0.05))
    return discover_live_surface_run_dir(
        kwargs,
        output_dir=output_dir,
        fallback_run_dir=effective_run_dir,
    )


def live_timeout_completion_grace_s() -> float:
    raw = str(os.environ.get("ROBOCLAWS_LIVE_EVAL_TIMEOUT_COMPLETION_GRACE_S") or "").strip()
    if not raw:
        return DEFAULT_LIVE_TIMEOUT_COMPLETION_GRACE_S
    try:
        return max(float(raw), 0.0)
    except ValueError:
        return DEFAULT_LIVE_TIMEOUT_COMPLETION_GRACE_S


def live_product_run_kwargs(
    sample: EvalSample,
    *,
    run_dir: Path,
    budget: str,
    dependency_artifacts: dict[str, Any] | None,
    agent_engine: str,
    provider_profile: str,
    model: str | None,
    live_timeout_s: float | None,
) -> dict[str, Any]:
    """Return product-run kwargs plus live-agent routing metadata."""

    kwargs = product_run_kwargs(
        sample,
        run_dir=run_dir,
        budget=budget,
        dependency_artifacts=dependency_artifacts,
    )
    kwargs.update(
        {
            "eval_sample": sample,
            "agent_engine": agent_engine,
            "provider_profile": provider_profile,
            "model": model,
            "live_timeout_s": live_timeout_s,
        }
    )
    return kwargs


def product_run_kwargs(
    sample: EvalSample,
    *,
    run_dir: Path,
    budget: str,
    dependency_artifacts: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return shared cleanup product-run kwargs for direct and live eval trials."""

    launch_overrides = sample.launch_overrides or {}
    semantic_sweep = sample.intent == "map-build" or sample.preset == "map-build"
    kwargs: dict[str, Any] = {
        "output_dir": run_dir,
        "seed": sample.seed,
        "task_prompt": task_prompt(sample),
        "backend": implementation_backend(sample, budget=budget),
        "evidence_lane": evidence_lane(sample, budget=budget),
        "semantic_sweep": semantic_sweep,
        "generated_mess_count": generated_mess_count(sample),
        "scene_source": str(launch_overrides.get("scene_source") or "procthor-10k-val"),
        "scene_index": int(launch_overrides.get("scene_index") or 0),
        "run_metadata_overrides": {
            "eval_sample_id": sample.sample_id,
            "eval_sample_version": sample.version,
            "eval_suite_runner": "roboclaws.evals.runner",
        },
    }
    goal_contract = _goal_contract_json(sample)
    if goal_contract:
        kwargs["goal_contract_json"] = goal_contract
    runtime_map_prior = str((dependency_artifacts or {}).get("runtime_map_prior_path") or "")
    if runtime_map_prior:
        kwargs["runtime_map_prior_path"] = runtime_map_prior
    return kwargs


def implementation_backend(sample: EvalSample, *, budget: str) -> str:
    if budget == "smoke":
        return SYNTHETIC_BACKEND
    backend = BACKEND_SPECS.get(sample.backend)
    if backend is None:
        return sample.backend
    return backend.implementation_backend


def evidence_lane(sample: EvalSample, *, budget: str) -> str:
    if budget == "smoke":
        return "smoke"
    return sample.evidence_lane


def task_prompt(sample: EvalSample) -> str:
    if sample.prompt not in {"", MISSING_NOT_APPLICABLE, MISSING_UNAVAILABLE}:
        return sample.prompt
    if sample.intent == "map-build":
        return "帮我建立这个房间的语义地图"
    return "帮我收拾这个房间"


def generated_mess_count(sample: EvalSample) -> int:
    reference = sample.private_goal_reference
    if isinstance(reference.get("generated_mess_count"), int):
        return int(reference["generated_mess_count"])
    launch_overrides = sample.launch_overrides or {}
    for key in ("generated_mess_count", "relocation_count"):
        value = launch_overrides.get(key)
        if value is not None:
            return int(value)
    if sample.intent == "map-build":
        return 0
    return 10


def _goal_contract_json(sample: EvalSample) -> str:
    launch_overrides = sample.launch_overrides or {}
    override = str(launch_overrides.get("goal_contract_json") or "")
    if override:
        return override
    if sample.intent not in TASK_INTENT_SPECS:
        return ""
    surface = SURFACE_SPECS.get(sample.surface)
    if surface is None:
        return ""
    return normalize_goal_contract(
        surface=surface,
        intent=TASK_INTENT_SPECS[sample.intent],
        raw_prompt="" if sample.prompt in MISSING_SENTINELS else sample.prompt,
    ).to_json()


def live_surface_env(kwargs: dict[str, Any], *, base_env: Any) -> dict[str, str]:
    """Return environment overrides for the selected live agent engine."""

    env = dict(base_env)
    provider_profile = str(kwargs.get("provider_profile") or "")
    if provider_profile:
        if kwargs["agent_engine"] in {"codex-cli", "openai-agents-sdk"}:
            env["ROBOCLAWS_CODEX_PROVIDER"] = provider_profile
        elif kwargs["agent_engine"] == "claude-code":
            env["ROBOCLAWS_CLAUDE_PROVIDER"] = provider_profile
    model = str(kwargs.get("model") or "")
    if model:
        if kwargs["agent_engine"] in {"codex-cli", "openai-agents-sdk"}:
            env["ROBOCLAWS_CODEX_MODEL"] = model
        elif kwargs["agent_engine"] == "claude-code":
            env["ROBOCLAWS_CLAUDE_MODEL"] = model
    return env


def live_evidence_lane(kwargs: dict[str, Any]) -> str:
    lane = str(kwargs.get("evidence_lane") or "")
    if lane == "smoke":
        return "world-oracle-labels"
    return lane or "world-oracle-labels"


def _is_smoke_budget(kwargs: dict[str, Any]) -> bool:
    return str(kwargs.get("evidence_lane") or "") == "smoke"


def _generated_mess_count(kwargs: dict[str, Any]) -> int:
    try:
        return int(kwargs.get("generated_mess_count") or 0)
    except (TypeError, ValueError):
        return 0


def _public_backend_from_implementation(backend: str) -> str:
    if backend in {MISSING_NOT_APPLICABLE, MISSING_UNAVAILABLE, ""}:
        return "mujoco"
    if backend == "api_semantic_synthetic":
        return "mujoco"
    for spec in BACKEND_SPECS.values():
        if spec.implementation_backend == backend:
            return spec.id
    return backend


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _write_live_eval_command_record(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _recover_open_ended_run_result_after_nonzero_exit(
    kwargs: dict[str, Any],
    *,
    sample_run_dir: Path,
) -> dict[str, Any]:
    if not _is_open_ended_eval_sample(kwargs):
        return {}
    return _load_json(sample_run_dir / "run_result.json")


def _is_open_ended_eval_sample(kwargs: dict[str, Any]) -> bool:
    sample: EvalSample | None = kwargs.get("eval_sample")
    return sample is not None and sample.intent == "open-ended"


def _live_surface_run_is_terminal(
    run_dir: Path,
    *,
    allow_open_ended_checker_failure: bool = False,
) -> bool:
    status = _load_json(run_dir / "live_status.json")
    if not status:
        return False
    exit_status = status.get("exit_status")
    if exit_status == 0:
        return True
    if exit_status not in {None, 0}:
        if allow_open_ended_checker_failure and _is_open_ended_checker_failure(status):
            return True
        _raise_for_terminal_live_status(run_dir, status)
    return False


def _is_open_ended_checker_failure(status: dict[str, Any]) -> bool:
    reason = str(status.get("reason") or "").lower()
    return "cleanup checker exited with status" in reason


def _live_surface_run_dir_has_evidence(path: Path) -> bool:
    return (
        (path / "run_result.json").is_file()
        or (path / "live_status.json").is_file()
        or (path / "trace.jsonl").is_file()
    )


def _live_surface_run_dir_from_stdout(stdout: str) -> Path | None:
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("Artifacts"):
            continue
        _, _, value = line.partition(":")
        path = value.strip()
        if path:
            return Path(path)
    return None


def _live_surface_route_can_detach(kwargs: dict[str, Any]) -> bool:
    return str(kwargs.get("agent_engine") or "") == "codex-cli"


def _raise_for_terminal_live_status(run_dir: Path, status: dict[str, Any]) -> None:
    if not status:
        return
    exit_status = status.get("exit_status")
    if exit_status in {None, 0}:
        return
    reason = str(status.get("reason") or status.get("provider_reason") or "").strip()
    detail = f": {reason}" if reason else ""
    raise RuntimeError(
        f"detached live surface run failed with exit {exit_status} at {run_dir}{detail}"
    )

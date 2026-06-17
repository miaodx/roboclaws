from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_agent_eval_public_facade_routes_to_eval_cli() -> None:
    trace = _trace_agent_eval(
        "suite=smoke_regression",
        "budget=smoke",
        "stamp=trace",
        "agent_engine=codex-cli",
        "provider_profile=codex-env",
        "live_execution=run",
        "live_timeout_s=30",
    )

    assert trace[:5] == ["cmd", ".venv/bin/python", "-m", "roboclaws.cli.main", "eval"]
    assert "suite=smoke_regression" in trace
    assert "budget=smoke" in trace
    assert "agent_engine=codex-cli" in trace
    assert "provider_profile=codex-env" in trace
    assert "live_execution=run" in trace
    assert "live_timeout_s=30" in trace


def test_agent_eval_public_facade_routes_promotion_cli() -> None:
    trace = _trace_agent_eval(
        "promote-regression",
        "eval_results=output/evals/demo/eval_results.json",
        "source_sample_id=cleanup.smoke_seed7",
        "regression_sample_id=regression.cleanup_demo",
    )

    assert trace[:5] == ["cmd", ".venv/bin/python", "-m", "roboclaws.cli.main", "eval"]
    assert "promote-regression" in trace
    assert "eval_results=output/evals/demo/eval_results.json" in trace
    assert "source_sample_id=cleanup.smoke_seed7" in trace
    assert "regression_sample_id=regression.cleanup_demo" in trace


def test_surface_cleanup_live_run_dir_reaches_molmo_impl() -> None:
    route, plan_trace = _trace_surface_run_with_plan(
        "surface=household-world",
        "preset=cleanup",
        "agent_engine=codex-cli",
        "provider_profile=codex-env",
        "evidence_lane=world-oracle-labels",
        "seed=7",
        "output_dir=/tmp/roboclaws-eval-surface-test",
        "run_dir=/tmp/roboclaws-eval-surface-test/seed-7",
        "run_preset=smoke",
    )

    assert route[:5] == [
        "just",
        "molmo::household-cleanup-impl",
        "codex-live",
        "smoke",
        "7",
    ]
    assert route[-1] == "/tmp/roboclaws-eval-surface-test/seed-7"
    assert (
        "target=just agent::run household-world.cleanup codex-cli smoke "
        "seed=7 output_dir=/tmp/roboclaws-eval-surface-test "
        "run_dir=/tmp/roboclaws-eval-surface-test/seed-7"
    ) in " ".join(plan_trace)


def _trace_agent_eval(*args: str) -> list[str]:
    binary = _just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "agent::eval", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t")


def _trace_surface_run_with_plan(*args: str) -> tuple[list[str], list[str]]:
    binary = _just_bin()
    env = os.environ.copy()
    env["ROBOCLAWS_JUST_TRACE"] = "1"
    env["PATH"] = f"{Path(binary).parent}{os.pathsep}{env.get('PATH', '')}"
    result = subprocess.run(
        [binary, "run::surface", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip().split("\t"), result.stderr.strip().split("\t")


def _just_bin() -> str:
    path = shutil.which("just")
    if path:
        return path
    local_path = Path.home() / ".local/bin" / "just"
    if local_path.exists():
        return str(local_path)
    pytest.skip("just binary is not available")

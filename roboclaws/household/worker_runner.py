from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any


def run_json_worker_once(
    *,
    worker_name: str,
    python_executable: Path,
    missing_runtime_hint: str,
    worker_script: Path,
    state_path: Path,
    command: str,
    args: tuple[str, ...],
    env: dict[str, str],
    timeout_s: float,
) -> dict[str, Any]:
    if not python_executable.is_file():
        raise RuntimeError(
            f"{worker_name} Python runtime is missing: {python_executable}. "
            f"{missing_runtime_hint}"
        )
    worker_command = worker_command_args(
        python_executable=python_executable,
        worker_script=worker_script,
        state_path=state_path,
        command=command,
        args=args,
    )
    try:
        completed = subprocess.run(
            worker_command,
            check=False,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"{worker_name} subprocess worker timed out ({command}, {timeout_s:g}s)"
        ) from exc
    if completed.returncode != 0:
        raise RuntimeError(
            f"{worker_name} subprocess worker failed "
            f"({command}, exit {completed.returncode}): {completed.stderr.strip()}"
        )
    return parse_last_json_object(completed.stdout, worker_name=worker_name)


def worker_command_args(
    *,
    python_executable: Path,
    worker_script: Path,
    state_path: Path,
    command: str,
    args: tuple[str, ...],
) -> list[str]:
    return [
        str(python_executable),
        str(worker_script),
        "--state-path",
        str(state_path),
        command,
        *args,
    ]


def parse_last_json_object(stdout: str, *, worker_name: str = "subprocess") -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    raise RuntimeError(f"{worker_name} worker returned no JSON object: {stdout!r}")


def read_process_stderr(process: subprocess.Popen[str]) -> str:
    if process.stderr is None:
        return ""
    try:
        return process.stderr.read()
    except Exception:
        return ""


def worker_timeout_s(
    *,
    command: str,
    override_env_var: str,
    command_timeouts: dict[str, float],
    default_timeout_s: float,
) -> float:
    override = os.environ.get(override_env_var)
    if override:
        return float(override)
    return command_timeouts.get(command, default_timeout_s)


def worker_env(
    *,
    defaults: dict[str, str] | None = None,
    remove: tuple[str, ...] = (),
) -> dict[str, str]:
    env = os.environ.copy()
    for key in remove:
        env.pop(key, None)
    for key, value in (defaults or {}).items():
        env.setdefault(key, value)
    return env

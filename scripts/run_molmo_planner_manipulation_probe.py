#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import traceback
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.manipulation_provenance import (  # noqa: E402
    BLOCKED_CAPABILITY_PROVENANCE,
    MANIPULATION_PROBE_CONTRACT,
    PLANNER_BACKED_PROVENANCE,
    blocked_planner_probe_evidence,
    planner_backed_probe_evidence,
)
from roboclaws.molmo_cleanup.report import render_planner_manipulation_report  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    DEFAULT_MOLMOSPACES_PYTHON,
    MOLMOSPACES_SUBPROCESS_BACKEND,
)

DEFAULT_MOLMOSPACES_ROOT = Path("/tmp/roboclaws-molmospaces-spike/molmospaces")
PROBE_TASK = "pick_and_place"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a MolmoSpaces planner-backed manipulation probe artifact."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output/molmo-planner-manipulation-probe-harness"),
    )
    parser.add_argument(
        "--python-executable",
        type=Path,
        default=Path(
            os.environ.get("ROBOCLAWS_MOLMOSPACES_PYTHON", str(DEFAULT_MOLMOSPACES_PYTHON))
        ),
    )
    parser.add_argument("--molmospaces-root", type=Path, default=DEFAULT_MOLMOSPACES_ROOT)
    parser.add_argument("--embodiment", choices=("franka", "rby1m"), default="franka")
    parser.add_argument(
        "--probe-mode", choices=("config_import", "execute"), default="config_import"
    )
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker:
        worker_payload = _run_worker_probe(args)
        print(json.dumps(worker_payload, sort_keys=True))
        if not worker_payload.get("ok"):
            raise SystemExit(3)
        return

    run_result = run_probe(
        output_dir=args.output_dir,
        python_executable=args.python_executable,
        molmospaces_root=args.molmospaces_root,
        embodiment=args.embodiment,
        probe_mode=args.probe_mode,
        steps=args.steps,
        timeout_s=args.timeout_s,
    )
    print(
        json.dumps(
            {
                "status": run_result["status"],
                "run_result": str(args.output_dir / "run_result.json"),
            }
        )
    )


def run_probe(
    *,
    output_dir: Path,
    python_executable: Path,
    molmospaces_root: Path,
    embodiment: str,
    probe_mode: str,
    steps: int,
    timeout_s: float,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = output_dir / "planner_probe_stdout.txt"
    stderr_path = output_dir / "planner_probe_stderr.txt"
    if not python_executable.is_file():
        stdout_path.write_text("", encoding="utf-8")
        stderr_path.write_text("", encoding="utf-8")
        worker_payload: dict[str, Any] | None = None
        return _write_probe_result(
            output_dir=output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            embodiment=embodiment,
            probe_mode=probe_mode,
            steps=steps,
            worker_payload=worker_payload,
            returncode=127,
            blockers=[
                {
                    "code": "missing_molmospaces_python",
                    "message": f"Missing MolmoSpaces Python executable: {python_executable}",
                }
            ],
        )

    env = os.environ.copy()
    env["PYTHONPATH"] = _prepend_pythonpath(molmospaces_root, env.get("PYTHONPATH"))
    command = [
        str(python_executable),
        str(Path(__file__).resolve()),
        "--worker",
        "--output-dir",
        str(output_dir),
        "--embodiment",
        embodiment,
        "--probe-mode",
        probe_mode,
        "--steps",
        str(steps),
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=env,
        )
        stdout_path.write_text(completed.stdout, encoding="utf-8")
        stderr_path.write_text(completed.stderr, encoding="utf-8")
        worker_payload = _parse_last_json_object(completed.stdout)
        blockers = _blockers_from_completed(completed.returncode, worker_payload)
        return _write_probe_result(
            output_dir=output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            embodiment=embodiment,
            probe_mode=probe_mode,
            steps=steps,
            worker_payload=worker_payload,
            returncode=completed.returncode,
            blockers=blockers,
        )
    except subprocess.TimeoutExpired as exc:
        stdout_path.write_text(exc.stdout or "", encoding="utf-8")
        stderr_path.write_text(exc.stderr or "", encoding="utf-8")
        return _write_probe_result(
            output_dir=output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            embodiment=embodiment,
            probe_mode=probe_mode,
            steps=steps,
            worker_payload=None,
            returncode=124,
            blockers=[{"code": "timeout", "message": f"Probe exceeded {timeout_s:.1f}s"}],
        )


def _run_worker_probe(args: argparse.Namespace) -> dict[str, Any]:
    try:
        if args.embodiment == "franka":
            payload = _probe_franka(args)
        else:
            payload = _probe_rby1m(args)
        return {"ok": True, **payload}
    except BaseException as exc:  # noqa: BLE001 - worker must report capability blockers.
        return {
            "ok": False,
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "embodiment": args.embodiment,
            "probe_mode": args.probe_mode,
            "execution_attempted": args.probe_mode == "execute",
        }


def _probe_franka(args: argparse.Namespace) -> dict[str, Any]:
    from mlspaces_tests.data_generation.config import FrankaPickAndPlaceDroidTestConfig

    config = FrankaPickAndPlaceDroidTestConfig()
    config.use_passive_viewer = False
    config.profile = False
    config.use_wandb = False
    policy_cls = config.policy_config.policy_cls
    payload: dict[str, Any] = {
        "embodiment": "franka",
        "task": PROBE_TASK,
        "probe_mode": args.probe_mode,
        "upstream_policy_class": policy_cls.__name__,
        "upstream_policy_module": policy_cls.__module__,
        "policy_type": config.policy_config.policy_type,
        "planner_class_available": True,
        "execution_attempted": False,
    }
    if args.probe_mode == "execute":
        payload.update(_execute_policy_probe(config, args.output_dir, args.steps))
    return payload


def _probe_rby1m(args: argparse.Namespace) -> dict[str, Any]:
    from molmo_spaces.data_generation.config.object_manipulation_datagen_configs import (
        RBY1PickAndPlaceDataGenConfig,
    )

    config = RBY1PickAndPlaceDataGenConfig()
    config.use_passive_viewer = False
    config.profile = False
    config.use_wandb = False
    config.policy_config.server_urls = []
    policy_cls = config.policy_config.policy_cls
    payload: dict[str, Any] = {
        "embodiment": "rby1m",
        "task": PROBE_TASK,
        "probe_mode": args.probe_mode,
        "upstream_policy_class": policy_cls.__name__,
        "upstream_policy_module": policy_cls.__module__,
        "policy_type": config.policy_config.policy_type,
        "planner_class_available": True,
        "execution_attempted": False,
    }
    if args.probe_mode == "execute":
        payload.update(_execute_policy_probe(config, args.output_dir, args.steps))
    return payload


def _execute_policy_probe(config: Any, output_dir: Path, steps: int) -> dict[str, Any]:
    import numpy as np
    from molmo_spaces.utils.test_utils import run_task_for_steps_with_observations

    task_sampler = config.task_sampler_config.task_sampler_class(config)
    task_sampler.reset()
    task = task_sampler.sample_task()
    task.reset()
    policy = config.policy_config.policy_cls(config, task)
    policy.reset()
    initial_qpos, final_qpos, initial_obs, final_obs = run_task_for_steps_with_observations(
        task,
        policy,
        num_steps=steps,
        profiler=None,
    )
    views_dir = output_dir / "planner_views"
    image_artifacts = {}
    initial = _write_first_camera_image(initial_obs, views_dir, "initial")
    final = _write_first_camera_image(final_obs, views_dir, "final")
    if initial:
        image_artifacts["initial"] = str(initial.relative_to(output_dir))
    if final:
        image_artifacts["final"] = str(final.relative_to(output_dir))
    return {
        "execution_attempted": True,
        "steps_requested": steps,
        "steps_executed": steps,
        "max_abs_qpos_delta": float(np.max(np.abs(final_qpos - initial_qpos))),
        "image_artifacts": image_artifacts,
        "policy_phases": [item.get_current_phase() for item in policy.action_primitives],
    }


def _write_first_camera_image(
    obs_dict: dict[str, Any], output_dir: Path, prefix: str
) -> Path | None:
    import numpy as np
    from PIL import Image

    output_dir.mkdir(parents=True, exist_ok=True)
    for sensor_name, value in obs_dict.items():
        if "camera" not in sensor_name or "sensor_param" in sensor_name:
            continue
        if not isinstance(value, np.ndarray) or value.ndim != 3 or value.shape[2] != 3:
            continue
        image = Image.fromarray(np.clip(value, 0, 255).astype("uint8"))
        path = output_dir / f"{prefix}_{sensor_name}.png"
        image.save(path)
        return path
    return None


def _write_probe_result(
    *,
    output_dir: Path,
    stdout_path: Path,
    stderr_path: Path,
    embodiment: str,
    probe_mode: str,
    steps: int,
    worker_payload: dict[str, Any] | None,
    returncode: int,
    blockers: list[dict[str, Any]],
) -> dict[str, Any]:
    worker_payload = worker_payload or {}
    executed = bool(worker_payload.get("execution_attempted"))
    max_delta = float(worker_payload.get("max_abs_qpos_delta") or 0.0)
    planner_success = returncode == 0 and executed and max_delta > 0.0 and not blockers
    if planner_success:
        evidence = planner_backed_probe_evidence(
            backend=MOLMOSPACES_SUBPROCESS_BACKEND,
            embodiment=embodiment,
            task=PROBE_TASK,
            probe_mode=probe_mode,
            upstream_policy_class=str(worker_payload["upstream_policy_class"]),
            steps_requested=steps,
            steps_executed=int(worker_payload.get("steps_executed") or 0),
            max_abs_qpos_delta=max_delta,
            image_artifacts=worker_payload.get("image_artifacts") or {},
        )
        status = PLANNER_BACKED_PROVENANCE
        primitive_provenance = PLANNER_BACKED_PROVENANCE
    else:
        blockers = blockers or _default_blockers(worker_payload, probe_mode)
        evidence = blocked_planner_probe_evidence(
            backend=MOLMOSPACES_SUBPROCESS_BACKEND,
            embodiment=embodiment,
            task=PROBE_TASK,
            probe_mode=probe_mode,
            blockers=blockers,
            upstream_policy_class=worker_payload.get("upstream_policy_class"),
            execution_attempted=executed,
        )
        status = BLOCKED_CAPABILITY_PROVENANCE
        primitive_provenance = BLOCKED_CAPABILITY_PROVENANCE
    evidence["worker_returncode"] = returncode
    evidence["worker_payload"] = worker_payload
    run_result = {
        "artifact_kind": "molmo_planner_backed_manipulation_probe",
        "contract": MANIPULATION_PROBE_CONTRACT,
        "backend": MOLMOSPACES_SUBPROCESS_BACKEND,
        "status": status,
        "final_status": status,
        "primitive_provenance": primitive_provenance,
        "manipulation_evidence": evidence,
        "artifacts": {
            "stdout": stdout_path.name,
            "stderr": stderr_path.name,
        },
    }
    report_path = render_planner_manipulation_report(run_dir=output_dir, run_result=run_result)
    run_result["artifacts"]["report"] = report_path.name
    (output_dir / "run_result.json").write_text(
        json.dumps(run_result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return run_result


def _blockers_from_completed(
    returncode: int,
    worker_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if returncode == 0 and worker_payload and worker_payload.get("ok"):
        return []
    if returncode < 0:
        signum = -returncode
        name = (
            signal.Signals(signum).name
            if signum in {item.value for item in signal.Signals}
            else signum
        )
        return [{"code": "process_signal", "message": f"worker terminated by {name}"}]
    if worker_payload and not worker_payload.get("ok"):
        message = (
            worker_payload.get("message") or worker_payload.get("exception_type") or "worker failed"
        )
        return [
            {
                "code": str(worker_payload.get("exception_type", "worker_exception")),
                "message": str(message),
            }
        ]
    if returncode != 0:
        return [{"code": "worker_exit", "message": f"worker exited {returncode}"}]
    return []


def _default_blockers(worker_payload: dict[str, Any], probe_mode: str) -> list[dict[str, Any]]:
    if probe_mode == "config_import":
        return [
            {
                "code": "execution_not_attempted",
                "message": (
                    "Planner config/class import succeeded, but execution proof was not attempted."
                ),
            }
        ]
    if not worker_payload.get("execution_attempted"):
        return [
            {
                "code": "execution_not_reached",
                "message": "Planner execution did not start.",
            }
        ]
    return [
        {"code": "no_robot_state_delta", "message": "Planner execution did not move robot state."}
    ]


def _parse_last_json_object(stdout: str) -> dict[str, Any] | None:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    return None


def _prepend_pythonpath(path: Path, existing: str | None) -> str:
    value = str(path)
    if existing:
        return value + os.pathsep + existing
    return value


if __name__ == "__main__":
    main()

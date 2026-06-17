#!/usr/bin/env python3
from __future__ import annotations

import argparse
import faulthandler
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from types import MethodType, SimpleNamespace
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.planner_probe_primitive_executor import (  # noqa: E402
    PLANNER_PROBE_PRIMITIVE_BINDING_SCHEMA,
)
from roboclaws.household.semantic_timeline import (  # noqa: E402
    canonical_cleanup_tool_sequence,
)
from roboclaws.household.subprocess_backend import (  # noqa: E402
    DEFAULT_MOLMOSPACES_PYTHON,
)
from scripts.molmo_cleanup import planner_probe_runtime_diagnostics as probe_runtime
from scripts.molmo_cleanup.planner_manipulation_probe_result import (  # noqa: E402
    blockers_from_completed as _blockers_from_completed,
)
from scripts.molmo_cleanup.planner_manipulation_probe_result import (
    process_output_text as _process_output_text,
)
from scripts.molmo_cleanup.planner_manipulation_probe_result import (
    worker_payload_from_stdout as _worker_payload_from_stdout,
)
from scripts.molmo_cleanup.planner_manipulation_probe_result import (
    write_probe_result as _write_probe_result,
)

DEFAULT_MOLMOSPACES_ROOT = Path("/tmp/roboclaws-molmospaces-spike/molmospaces")
PROBE_TASK = "pick_and_place"
_WORKER_EVENT_STARTED_AT = time.monotonic()
_CUDA_MEMORY_SNAPSHOTS: list[dict[str, Any]] = []
_WORKER_EXCEPTION_CONTEXT: dict[str, Any] = {}
CUROBO_LOW_MEMORY_PROFILE: dict[str, dict[str, Any]] = {
    "policy": {
        "batch_size": 1,
        "max_batch_plan_attempts": 1,
    },
    "planner": {
        "num_trajopt_seeds": 1,
        "num_ik_seeds": 16,
        "max_attempts": 1,
        "trajopt_tsteps": 24,
        "enable_finetune_trajopt": False,
    },
}
EXACT_PICKUP_RETRY_BUDGET = 3
TASK_SAMPLER_RELAXED_ROBOT_PLACEMENT_PROFILE: dict[str, dict[str, Any]] = {
    "task_sampler_config": {
        "base_pose_sampling_radius_range": (0.0, 1.2),
        "robot_safety_radius": 0.15,
        "check_robot_placement_visibility": False,
        "max_robot_placement_attempts": 50,
    },
    "place_robot_near_overrides": {
        "max_tries": 50,
        "sampling_radius_range": (0.0, 1.2),
        "robot_safety_radius": 0.15,
        "check_camera_visibility": False,
    },
}
TASK_SAMPLER_WIDE_ROBOT_PLACEMENT_PROFILE: dict[str, dict[str, Any]] = {
    "task_sampler_config": {
        "base_pose_sampling_radius_range": (0.0, 2.0),
        "robot_safety_radius": 0.15,
        "check_robot_placement_visibility": False,
        "max_robot_placement_attempts": 100,
    },
    "place_robot_near_overrides": {
        "max_tries": 100,
        "sampling_radius_range": (0.0, 2.0),
        "robot_safety_radius": 0.15,
        "check_camera_visibility": False,
    },
}


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
    parser.add_argument(
        "--torch-extensions-dir",
        type=Path,
        default=(
            Path(os.environ["TORCH_EXTENSIONS_DIR"])
            if os.environ.get("TORCH_EXTENSIONS_DIR")
            else None
        ),
        help="Optional isolated Torch extension cache directory for CuRobo JIT builds.",
    )
    parser.add_argument(
        "--renderer-device-id",
        type=int,
        default=int(os.environ.get("ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID", "0")),
        help=(
            "EGL renderer device id for execute-mode probes. Use a negative value to "
            "disable the probe-local headless renderer adapter."
        ),
    )
    parser.add_argument(
        "--rby1m-curobo-memory-profile",
        choices=("none", "low"),
        default="none",
        help="Probe-local RBY1M/CuRobo memory profile. Default leaves upstream settings unchanged.",
    )
    parser.add_argument(
        "--task-sampler-robot-placement-profile",
        choices=("none", "relaxed", "wide"),
        default="none",
        help=(
            "Probe-local task-sampler robot placement profile. Non-default profiles "
            "widen sampling, lower safety radius, disable visibility gating, and "
            "override the actual place_robot_near max_tries call."
        ),
    )
    parser.add_argument("--curobo-policy-batch-size", type=int, default=None)
    parser.add_argument("--curobo-max-batch-plan-attempts", type=int, default=None)
    parser.add_argument("--curobo-num-trajopt-seeds", type=int, default=None)
    parser.add_argument("--curobo-num-ik-seeds", type=int, default=None)
    parser.add_argument("--curobo-max-attempts", type=int, default=None)
    parser.add_argument("--curobo-trajopt-tsteps", type=int, default=None)
    parser.add_argument("--curobo-disable-finetune-trajopt", action="store_true")
    parser.add_argument(
        "--cleanup-object-id",
        default="",
        help=(
            "Optional cleanup object id that the sampled planner task must match before "
            "emitting cleanup primitive binding."
        ),
    )
    parser.add_argument(
        "--cleanup-target-receptacle-id",
        default="",
        help=(
            "Optional cleanup target receptacle id that the sampled planner task must match "
            "before emitting target-side cleanup primitive binding."
        ),
    )
    parser.add_argument(
        "--cleanup-source-receptacle-id",
        default="",
        help="Optional source receptacle id to record in promoted cleanup primitive binding.",
    )
    parser.add_argument(
        "--cleanup-planner-object-id",
        default="",
        help=(
            "Optional planner-facing pickup object name used for sampled-task matching while "
            "cleanup-object-id remains the cleanup-facing id."
        ),
    )
    parser.add_argument(
        "--cleanup-planner-target-receptacle-id",
        default="",
        help=(
            "Optional planner-facing place receptacle name used for sampled-task matching "
            "while cleanup-target-receptacle-id remains the cleanup-facing id."
        ),
    )
    parser.add_argument(
        "--cleanup-scene-xml",
        default="",
        help=(
            "Optional MolmoSpaces scene XML for exact cleanup proof probes. When set, "
            "the worker samples the planner task from the same scene that produced the "
            "cleanup artifact."
        ),
    )
    parser.add_argument(
        "--cleanup-tools",
        default="",
        help="Comma-separated cleanup tools covered by the requested binding.",
    )
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=180.0)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.worker:
        faulthandler.enable(all_threads=True)
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
        renderer_device_id=args.renderer_device_id,
        torch_extensions_dir=args.torch_extensions_dir,
        rby1m_curobo_memory_profile=args.rby1m_curobo_memory_profile,
        task_sampler_robot_placement_profile=args.task_sampler_robot_placement_profile,
        curobo_policy_batch_size=args.curobo_policy_batch_size,
        curobo_max_batch_plan_attempts=args.curobo_max_batch_plan_attempts,
        curobo_num_trajopt_seeds=args.curobo_num_trajopt_seeds,
        curobo_num_ik_seeds=args.curobo_num_ik_seeds,
        curobo_max_attempts=args.curobo_max_attempts,
        curobo_trajopt_tsteps=args.curobo_trajopt_tsteps,
        curobo_disable_finetune_trajopt=args.curobo_disable_finetune_trajopt,
        cleanup_object_id=args.cleanup_object_id,
        cleanup_target_receptacle_id=args.cleanup_target_receptacle_id,
        cleanup_source_receptacle_id=args.cleanup_source_receptacle_id,
        cleanup_planner_object_id=args.cleanup_planner_object_id,
        cleanup_planner_target_receptacle_id=args.cleanup_planner_target_receptacle_id,
        cleanup_scene_xml=args.cleanup_scene_xml,
        cleanup_tools=args.cleanup_tools,
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
    renderer_device_id: int,
    torch_extensions_dir: Path | None,
    rby1m_curobo_memory_profile: str,
    task_sampler_robot_placement_profile: str,
    curobo_policy_batch_size: int | None,
    curobo_max_batch_plan_attempts: int | None,
    curobo_num_trajopt_seeds: int | None,
    curobo_num_ik_seeds: int | None,
    curobo_max_attempts: int | None,
    curobo_trajopt_tsteps: int | None,
    curobo_disable_finetune_trajopt: bool,
    cleanup_object_id: str,
    cleanup_target_receptacle_id: str,
    cleanup_source_receptacle_id: str,
    cleanup_planner_object_id: str,
    cleanup_planner_target_receptacle_id: str,
    cleanup_scene_xml: str,
    cleanup_tools: str,
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
    env["PYTHONFAULTHANDLER"] = "1"
    if torch_extensions_dir is not None:
        torch_extensions_dir = torch_extensions_dir.expanduser().resolve()
        torch_extensions_dir.mkdir(parents=True, exist_ok=True)
        env["TORCH_EXTENSIONS_DIR"] = str(torch_extensions_dir)
    worker_renderer_device_id = probe_runtime.renderer_device_id_for_probe(
        probe_mode=probe_mode,
        renderer_device_id=renderer_device_id,
    )
    if worker_renderer_device_id is not None:
        env["MUJOCO_GL"] = "egl"
        env["PYOPENGL_PLATFORM"] = "egl"
        env["ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID"] = str(worker_renderer_device_id)
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
        "--renderer-device-id",
        str(renderer_device_id),
        "--steps",
        str(steps),
        "--rby1m-curobo-memory-profile",
        rby1m_curobo_memory_profile,
        "--task-sampler-robot-placement-profile",
        task_sampler_robot_placement_profile,
    ]
    if torch_extensions_dir is not None:
        command.extend(["--torch-extensions-dir", str(torch_extensions_dir)])
    _append_optional_int_arg(command, "--curobo-policy-batch-size", curobo_policy_batch_size)
    _append_optional_int_arg(
        command,
        "--curobo-max-batch-plan-attempts",
        curobo_max_batch_plan_attempts,
    )
    _append_optional_int_arg(command, "--curobo-num-trajopt-seeds", curobo_num_trajopt_seeds)
    _append_optional_int_arg(command, "--curobo-num-ik-seeds", curobo_num_ik_seeds)
    _append_optional_int_arg(command, "--curobo-max-attempts", curobo_max_attempts)
    _append_optional_int_arg(command, "--curobo-trajopt-tsteps", curobo_trajopt_tsteps)
    if curobo_disable_finetune_trajopt:
        command.append("--curobo-disable-finetune-trajopt")
    _append_optional_str_arg(command, "--cleanup-object-id", cleanup_object_id)
    _append_optional_str_arg(
        command,
        "--cleanup-target-receptacle-id",
        cleanup_target_receptacle_id,
    )
    _append_optional_str_arg(
        command,
        "--cleanup-source-receptacle-id",
        cleanup_source_receptacle_id,
    )
    _append_optional_str_arg(command, "--cleanup-planner-object-id", cleanup_planner_object_id)
    _append_optional_str_arg(
        command,
        "--cleanup-planner-target-receptacle-id",
        cleanup_planner_target_receptacle_id,
    )
    _append_optional_str_arg(command, "--cleanup-scene-xml", cleanup_scene_xml)
    _append_optional_str_arg(command, "--cleanup-tools", cleanup_tools)
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
        worker_payload = _worker_payload_from_stdout(completed.stdout)
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
        stdout_text = _process_output_text(exc.stdout)
        stderr_text = _process_output_text(exc.stderr)
        stdout_path.write_text(stdout_text, encoding="utf-8")
        stderr_path.write_text(stderr_text, encoding="utf-8")
        worker_payload = _worker_payload_from_stdout(stdout_text)
        return _write_probe_result(
            output_dir=output_dir,
            stdout_path=stdout_path,
            stderr_path=stderr_path,
            embodiment=embodiment,
            probe_mode=probe_mode,
            steps=steps,
            worker_payload=worker_payload,
            returncode=124,
            blockers=[{"code": "timeout", "message": f"Probe exceeded {timeout_s:.1f}s"}],
        )


def _run_worker_probe(args: argparse.Namespace) -> dict[str, Any]:
    _WORKER_EXCEPTION_CONTEXT.clear()
    probe_runtime.configure_headless_renderer_env(args)
    _emit_worker_event(
        "worker_start",
        stage="worker_start",
        embodiment=args.embodiment,
        probe_mode=args.probe_mode,
    )
    runtime_diagnostics = probe_runtime.runtime_diagnostics(
        args,
        curobo_memory_profile_request=_curobo_memory_profile_request(args),
    )
    _emit_worker_event(
        "runtime_diagnostics",
        stage="runtime_diagnostics",
        runtime_diagnostics=runtime_diagnostics,
    )
    _record_cuda_memory_snapshot("worker_runtime_diagnostics")
    try:
        if args.embodiment == "franka":
            payload = _probe_franka(args)
        else:
            payload = _probe_rby1m(args)
        _record_cuda_memory_snapshot("worker_success")
        return {
            "ok": True,
            "initial_runtime_diagnostics": runtime_diagnostics,
            "runtime_diagnostics": probe_runtime.runtime_diagnostics(
                args,
                curobo_memory_profile_request=_curobo_memory_profile_request(args),
            ),
            "cuda_memory_snapshots": list(_CUDA_MEMORY_SNAPSHOTS),
            **payload,
        }
    except BaseException as exc:  # noqa: BLE001 - worker must report capability blockers.
        _record_cuda_memory_snapshot("worker_exception")
        final_runtime_diagnostics = probe_runtime.runtime_diagnostics(
            args,
            curobo_memory_profile_request=_curobo_memory_profile_request(args),
        )
        return {
            "ok": False,
            "exception_type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc(),
            "embodiment": args.embodiment,
            "probe_mode": args.probe_mode,
            "execution_attempted": args.probe_mode == "execute",
            "initial_runtime_diagnostics": runtime_diagnostics,
            "runtime_diagnostics": final_runtime_diagnostics,
            "cuda_memory_snapshots": list(_CUDA_MEMORY_SNAPSHOTS),
            **_worker_exception_probe_context(args),
        }


def _emit_worker_event(event: str, **payload: Any) -> None:
    print(
        json.dumps(
            {
                "event": event,
                "elapsed_s": round(time.monotonic() - _WORKER_EVENT_STARTED_AT, 6),
                **payload,
            },
            sort_keys=True,
        ),
        flush=True,
    )


def _record_worker_exception_context(**payload: Any) -> None:
    for key, value in payload.items():
        if value is not None:
            _WORKER_EXCEPTION_CONTEXT[key] = value


def _worker_exception_probe_context(args: argparse.Namespace) -> dict[str, Any]:
    context = {
        "cleanup_task_config": _WORKER_EXCEPTION_CONTEXT.get("cleanup_task_config")
        or _cleanup_task_config_request_from_args(args),
        "task_sampler_robot_placement_profile": _WORKER_EXCEPTION_CONTEXT.get(
            "task_sampler_robot_placement_profile"
        )
        or _task_sampler_robot_placement_profile_request_from_args(args),
        "cleanup_task_sampler_adapter": _WORKER_EXCEPTION_CONTEXT.get(
            "cleanup_task_sampler_adapter"
        )
        or {},
        "requested_cleanup_primitive_binding": _WORKER_EXCEPTION_CONTEXT.get(
            "requested_cleanup_primitive_binding"
        )
        or _requested_cleanup_primitive_binding(args),
        "task_sampler_failure_diagnostics": _WORKER_EXCEPTION_CONTEXT.get(
            "task_sampler_failure_diagnostics"
        )
        or {},
        "image_artifacts": _WORKER_EXCEPTION_CONTEXT.get("image_artifacts") or {},
    }
    for key in (
        "curobo_memory_profile",
        "sampled_task_binding",
        "cleanup_primitive_binding",
        "cleanup_primitive_binding_blockers",
        "policy_exception_context",
    ):
        if key in _WORKER_EXCEPTION_CONTEXT:
            context[key] = _WORKER_EXCEPTION_CONTEXT[key]
    return context


def _record_cuda_memory_snapshot(stage: str) -> dict[str, Any]:
    snapshot = probe_runtime.cuda_memory_snapshot(stage, started_at=_WORKER_EVENT_STARTED_AT)
    _CUDA_MEMORY_SNAPSHOTS.append(snapshot)
    _emit_worker_event("cuda_memory_snapshot", stage=stage, cuda_memory=snapshot)
    return snapshot


def _curobo_memory_profile_request(args: argparse.Namespace) -> dict[str, Any]:
    explicit = _explicit_curobo_memory_overrides(args)
    profile = getattr(args, "rby1m_curobo_memory_profile", "none")
    return {
        "profile": profile,
        "profile_defaults": (
            CUROBO_LOW_MEMORY_PROFILE if profile == "low" else {"policy": {}, "planner": {}}
        ),
        "explicit_overrides": explicit,
        "requested": profile != "none" or bool(explicit["policy"]) or bool(explicit["planner"]),
    }


def _task_sampler_robot_placement_profile_request_from_args(
    args: argparse.Namespace,
) -> dict[str, Any]:
    profile = str(getattr(args, "task_sampler_robot_placement_profile", "none") or "none")
    defaults = _task_sampler_robot_placement_profile_defaults(profile)
    return {
        "schema": "planner_probe_task_sampler_robot_placement_profile_v1",
        "profile": profile,
        "requested": profile != "none",
        "applied": False,
        "profile_defaults": _diagnostic_json_value(defaults),
        "applied_overrides": {},
        "place_robot_near_overrides": _diagnostic_json_value(
            defaults.get("place_robot_near_overrides") or {}
        ),
        "evidence_note": (
            "Probe-local robot-placement profile request. It is not a cleanup "
            "contract change and does not promote planner-backed readiness by itself."
        ),
    }


def _apply_task_sampler_robot_placement_profile(
    config: Any,
    args: argparse.Namespace,
) -> dict[str, Any]:
    request = _task_sampler_robot_placement_profile_request_from_args(args)
    sampler_config = getattr(config, "task_sampler_config", None)
    before = _task_sampler_robot_placement_config_from_config(sampler_config)
    profile = request["profile"]
    defaults = _task_sampler_robot_placement_profile_defaults(profile)
    config_overrides = dict(defaults.get("task_sampler_config") or {})
    applied_overrides: dict[str, Any] = {}
    if sampler_config is not None:
        for name, value in config_overrides.items():
            if hasattr(sampler_config, name):
                setattr(sampler_config, name, value)
                applied_overrides[name] = value
    after = _task_sampler_robot_placement_config_from_config(sampler_config)
    result = {
        **request,
        "applied": bool(applied_overrides or defaults.get("place_robot_near_overrides")),
        "applied_overrides": _diagnostic_json_value(applied_overrides),
        "place_robot_near_overrides": _diagnostic_json_value(
            defaults.get("place_robot_near_overrides") or {}
        ),
        "before": before,
        "after": after,
        "evidence_note": (
            "Probe-local task-sampler robot-placement mitigation. Config fields are "
            "mutated before task-sampler construction and place_robot_near call "
            "arguments are overridden inside the diagnostics adapter so upstream "
            "hardcoded max_tries values remain visible."
        ),
    }
    if profile != "none" and sampler_config is None:
        result["blockers"] = [
            {
                "code": "task_sampler_config_missing",
                "message": "Cannot apply task-sampler robot-placement profile without config.",
            }
        ]
    return result


def _task_sampler_robot_placement_profile_defaults(profile: str) -> dict[str, Any]:
    if profile == "relaxed":
        return TASK_SAMPLER_RELAXED_ROBOT_PLACEMENT_PROFILE
    if profile == "wide":
        return TASK_SAMPLER_WIDE_ROBOT_PLACEMENT_PROFILE
    return {"task_sampler_config": {}, "place_robot_near_overrides": {}}


def _task_sampler_robot_placement_config_from_config(sampler_config: Any) -> dict[str, Any]:
    if sampler_config is None:
        return {}
    return {
        field: _diagnostic_json_value(getattr(sampler_config, field))
        for field in (
            "base_pose_sampling_radius_range",
            "robot_safety_radius",
            "check_robot_placement_visibility",
            "robot_object_z_offset",
            "robot_object_z_offset_random_min",
            "robot_object_z_offset_random_max",
            "max_robot_placement_attempts",
        )
        if hasattr(sampler_config, field)
    }


def _explicit_curobo_memory_overrides(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    policy: dict[str, Any] = {}
    planner: dict[str, Any] = {}
    if getattr(args, "curobo_policy_batch_size", None) is not None:
        policy["batch_size"] = args.curobo_policy_batch_size
    if getattr(args, "curobo_max_batch_plan_attempts", None) is not None:
        policy["max_batch_plan_attempts"] = args.curobo_max_batch_plan_attempts
    if getattr(args, "curobo_num_trajopt_seeds", None) is not None:
        planner["num_trajopt_seeds"] = args.curobo_num_trajopt_seeds
    if getattr(args, "curobo_num_ik_seeds", None) is not None:
        planner["num_ik_seeds"] = args.curobo_num_ik_seeds
    if getattr(args, "curobo_max_attempts", None) is not None:
        planner["max_attempts"] = args.curobo_max_attempts
    if getattr(args, "curobo_trajopt_tsteps", None) is not None:
        planner["trajopt_tsteps"] = args.curobo_trajopt_tsteps
    if getattr(args, "curobo_disable_finetune_trajopt", False):
        planner["enable_finetune_trajopt"] = False
    return {"policy": policy, "planner": planner}


def _apply_rby1m_curobo_memory_profile(config: Any, args: argparse.Namespace) -> dict[str, Any]:
    request = _curobo_memory_profile_request(args)
    before = _rby1m_curobo_memory_profile_values(config)
    overrides = _merged_curobo_memory_overrides(args)
    policy_config = config.policy_config
    for name, value in overrides["policy"].items():
        setattr(policy_config, name, value)
    for planner_config in _rby1m_curobo_planner_configs(policy_config).values():
        for name, value in overrides["planner"].items():
            setattr(planner_config, name, value)
    after = _rby1m_curobo_memory_profile_values(config)
    return {
        "schema": "rby1m_curobo_memory_profile_v1",
        "profile": args.rby1m_curobo_memory_profile,
        "requested": request["requested"],
        "applied": bool(overrides["policy"] or overrides["planner"]),
        "request": request,
        "applied_overrides": overrides,
        "before": before,
        "after": after,
    }


def _merged_curobo_memory_overrides(args: argparse.Namespace) -> dict[str, dict[str, Any]]:
    policy: dict[str, Any] = {}
    planner: dict[str, Any] = {}
    if getattr(args, "rby1m_curobo_memory_profile", "none") == "low":
        policy.update(CUROBO_LOW_MEMORY_PROFILE["policy"])
        planner.update(CUROBO_LOW_MEMORY_PROFILE["planner"])
    explicit = _explicit_curobo_memory_overrides(args)
    policy.update(explicit["policy"])
    planner.update(explicit["planner"])
    return {"policy": policy, "planner": planner}


def _rby1m_curobo_memory_profile_values(config: Any) -> dict[str, Any]:
    policy_config = config.policy_config
    return {
        "policy": {
            "batch_size": getattr(policy_config, "batch_size", None),
            "max_batch_plan_attempts": getattr(policy_config, "max_batch_plan_attempts", None),
            "enable_collision_avoidance": getattr(
                policy_config,
                "enable_collision_avoidance",
                None,
            ),
        },
        "planners": {
            name: _curobo_planner_memory_values(planner_config)
            for name, planner_config in _rby1m_curobo_planner_configs(policy_config).items()
        },
    }


def _rby1m_curobo_planner_configs(policy_config: Any) -> dict[str, Any]:
    return {
        name: planner_config
        for name, planner_config in {
            "left": getattr(policy_config, "left_curobo_planner_config", None),
            "right": getattr(policy_config, "right_curobo_planner_config", None),
        }.items()
        if planner_config is not None
    }


def _curobo_planner_memory_values(planner_config: Any) -> dict[str, Any]:
    return {
        "num_trajopt_seeds": getattr(planner_config, "num_trajopt_seeds", None),
        "num_ik_seeds": getattr(planner_config, "num_ik_seeds", None),
        "max_attempts": getattr(planner_config, "max_attempts", None),
        "trajopt_tsteps": getattr(planner_config, "trajopt_tsteps", None),
        "enable_finetune_trajopt": getattr(planner_config, "enable_finetune_trajopt", None),
    }


def _probe_franka(args: argparse.Namespace) -> dict[str, Any]:
    _emit_worker_event("franka_config_import_start", stage="franka_config_import")
    from mlspaces_tests.data_generation.config import FrankaPickAndPlaceDroidTestConfig

    _emit_worker_event("franka_config_import_done", stage="franka_config_import")
    _emit_worker_event("franka_config_construct_start", stage="franka_config_construct")
    config = FrankaPickAndPlaceDroidTestConfig()
    config.use_passive_viewer = False
    config.profile = False
    config.use_wandb = False
    cleanup_task_config = _configure_exact_cleanup_task(config, args)
    task_sampler_robot_placement_profile = _apply_task_sampler_robot_placement_profile(
        config,
        args,
    )
    _record_worker_exception_context(
        cleanup_task_config=cleanup_task_config,
        task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
    )
    policy_cls = config.policy_config.policy_cls
    _emit_worker_event(
        "franka_policy_class_ready",
        stage="franka_policy_class",
        upstream_policy_class=policy_cls.__name__,
        upstream_policy_module=policy_cls.__module__,
    )
    payload: dict[str, Any] = {
        "embodiment": "franka",
        "task": PROBE_TASK,
        "probe_mode": args.probe_mode,
        "upstream_policy_class": policy_cls.__name__,
        "upstream_policy_module": policy_cls.__module__,
        "policy_type": config.policy_config.policy_type,
        "planner_class_available": True,
        "execution_attempted": False,
        "cleanup_task_config": cleanup_task_config,
        "task_sampler_robot_placement_profile": task_sampler_robot_placement_profile,
    }
    if args.probe_mode == "execute":
        payload.update(
            _execute_policy_probe(
                config,
                args.output_dir,
                args.steps,
                renderer_device_id=probe_runtime.renderer_device_id_for_probe(
                    probe_mode=args.probe_mode,
                    renderer_device_id=args.renderer_device_id,
                ),
                requested_cleanup_binding=_requested_cleanup_primitive_binding(args),
                task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
            )
        )
    return payload


def _probe_rby1m(args: argparse.Namespace) -> dict[str, Any]:
    _emit_worker_event("rby1m_config_import_start", stage="rby1m_config_import")
    from molmo_spaces.data_generation.config.object_manipulation_datagen_configs import (
        RBY1PickAndPlaceDataGenConfig,
    )

    _emit_worker_event("rby1m_config_import_done", stage="rby1m_config_import")
    _emit_worker_event("rby1m_config_construct_start", stage="rby1m_config_construct")
    config = RBY1PickAndPlaceDataGenConfig()
    config.use_passive_viewer = False
    config.profile = False
    config.use_wandb = False
    config.policy_config.server_urls = []
    cleanup_task_config = _configure_exact_cleanup_task(config, args)
    task_sampler_robot_placement_profile = _apply_task_sampler_robot_placement_profile(
        config,
        args,
    )
    _record_worker_exception_context(
        cleanup_task_config=cleanup_task_config,
        task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
    )
    curobo_memory_profile = _apply_rby1m_curobo_memory_profile(config, args)
    _record_worker_exception_context(curobo_memory_profile=curobo_memory_profile)
    _emit_worker_event(
        "task_sampler_robot_placement_profile_ready",
        stage="task_sampler_robot_placement_profile",
        task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
    )
    _emit_worker_event(
        "rby1m_curobo_memory_profile_ready",
        stage="rby1m_curobo_memory_profile",
        curobo_memory_profile=curobo_memory_profile,
    )
    policy_cls = config.policy_config.policy_cls
    _emit_worker_event(
        "rby1m_policy_class_ready",
        stage="rby1m_policy_class",
        upstream_policy_class=policy_cls.__name__,
        upstream_policy_module=policy_cls.__module__,
    )
    payload: dict[str, Any] = {
        "embodiment": "rby1m",
        "task": PROBE_TASK,
        "probe_mode": args.probe_mode,
        "upstream_policy_class": policy_cls.__name__,
        "upstream_policy_module": policy_cls.__module__,
        "policy_type": config.policy_config.policy_type,
        "planner_class_available": True,
        "execution_attempted": False,
        "curobo_memory_profile": curobo_memory_profile,
        "cleanup_task_config": cleanup_task_config,
        "task_sampler_robot_placement_profile": task_sampler_robot_placement_profile,
    }
    if args.probe_mode == "execute":
        _emit_worker_event("rby1m_execute_probe_start", stage="rby1m_execute")
        payload.update(
            _execute_policy_probe(
                config,
                args.output_dir,
                args.steps,
                renderer_device_id=probe_runtime.renderer_device_id_for_probe(
                    probe_mode=args.probe_mode,
                    renderer_device_id=args.renderer_device_id,
                ),
                requested_cleanup_binding=_requested_cleanup_primitive_binding(args),
                task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
            )
        )
        _emit_worker_event(
            "rby1m_execute_probe_done",
            stage="rby1m_execute",
            execution_attempted=payload.get("execution_attempted"),
            steps_executed=payload.get("steps_executed"),
            max_abs_qpos_delta=payload.get("max_abs_qpos_delta"),
        )
    return payload


def _execute_policy_probe(
    config: Any,
    output_dir: Path,
    steps: int,
    *,
    renderer_device_id: int | None,
    requested_cleanup_binding: dict[str, Any],
    task_sampler_robot_placement_profile: dict[str, Any],
) -> dict[str, Any]:
    import numpy as np
    from molmo_spaces.utils.test_utils import run_task_for_steps_with_observations

    renderer_adapter = _prepare_execute_renderer(renderer_device_id)
    sampler_context = _prepare_execute_task_sampler(
        config,
        output_dir,
        requested_cleanup_binding=requested_cleanup_binding,
        task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
    )
    task, task_binding_context = _sample_execute_task(
        sampler_context["task_sampler"],
        requested_cleanup_binding,
    )
    _emit_worker_event("execute_warp_adapter_start", stage="execute_warp_adapter")
    warp_adapter = probe_runtime.apply_warp_torch_adapter()
    _emit_worker_event(
        "execute_warp_adapter_ready",
        stage="execute_warp_adapter",
        warp_adapter=warp_adapter,
    )
    policy, initial_qpos, final_qpos, initial_obs, final_obs = _run_execute_policy(
        config,
        task,
        steps,
        run_task_for_steps_with_observations,
    )
    image_artifacts = _execute_probe_image_artifacts(
        output_dir,
        initial_obs,
        final_obs,
    )
    max_abs_qpos_delta = float(np.max(np.abs(final_qpos - initial_qpos)))
    _emit_worker_event(
        "execute_probe_evidence_ready",
        stage="execute_probe_evidence",
        steps_executed=steps,
        max_abs_qpos_delta=max_abs_qpos_delta,
        image_artifacts=image_artifacts,
    )
    return {
        "execution_attempted": True,
        "steps_requested": steps,
        "steps_executed": steps,
        "max_abs_qpos_delta": max_abs_qpos_delta,
        "image_artifacts": image_artifacts,
        "policy_phases": [item.get_current_phase() for item in policy.action_primitives],
        "renderer_adapter": renderer_adapter,
        "task_sampler_robot_placement_profile": task_sampler_robot_placement_profile,
        "cleanup_task_sampler_adapter": sampler_context["cleanup_task_sampler_adapter"],
        "task_sampler_failure_diagnostics": sampler_context["task_sampler_failure_diagnostics"],
        "sampled_task_binding": task_binding_context["sampled_task_binding"],
        "requested_cleanup_primitive_binding": requested_cleanup_binding,
        "cleanup_primitive_binding": task_binding_context["cleanup_binding_result"].get(
            "cleanup_primitive_binding"
        ),
        "cleanup_primitive_binding_blockers": task_binding_context["cleanup_binding_result"].get(
            "blockers", []
        ),
    }


def _prepare_execute_renderer(renderer_device_id: int | None) -> dict[str, Any]:
    _emit_worker_event("execute_renderer_adapter_start", stage="execute_renderer_adapter")
    renderer_adapter = probe_runtime.apply_headless_renderer_adapter(renderer_device_id)
    _emit_worker_event(
        "execute_renderer_adapter_ready",
        stage="execute_renderer_adapter",
        renderer_adapter=renderer_adapter,
    )
    return renderer_adapter


def _prepare_execute_task_sampler(
    config: Any,
    output_dir: Path,
    *,
    requested_cleanup_binding: dict[str, Any],
    task_sampler_robot_placement_profile: dict[str, Any],
) -> dict[str, Any]:
    _emit_worker_event("execute_task_sampler_construct_start", stage="execute_task_sampler")
    task_sampler = config.task_sampler_config.task_sampler_class(config)
    cleanup_task_sampler_adapter = _apply_exact_cleanup_task_sampler_adapter(
        task_sampler,
        requested_cleanup_binding,
    )
    task_sampler_failure_diagnostics = _apply_task_sampler_failure_diagnostics_adapter(
        task_sampler,
        task_sampler_robot_placement_profile,
        output_dir=output_dir,
    )
    _record_worker_exception_context(
        cleanup_task_sampler_adapter=cleanup_task_sampler_adapter,
        requested_cleanup_primitive_binding=requested_cleanup_binding,
        task_sampler_robot_placement_profile=task_sampler_robot_placement_profile,
        task_sampler_failure_diagnostics=task_sampler_failure_diagnostics,
    )
    _emit_worker_event("execute_task_sampler_construct_done", stage="execute_task_sampler")
    return {
        "task_sampler": task_sampler,
        "cleanup_task_sampler_adapter": cleanup_task_sampler_adapter,
        "task_sampler_failure_diagnostics": task_sampler_failure_diagnostics,
    }


def _sample_execute_task(
    task_sampler: Any,
    requested_cleanup_binding: dict[str, Any],
) -> tuple[Any, dict[str, Any]]:
    _emit_worker_event("execute_task_sampler_reset_start", stage="execute_task_sampler_reset")
    task_sampler.reset()
    _emit_worker_event("execute_task_sampler_reset_done", stage="execute_task_sampler_reset")
    _emit_worker_event("execute_task_sample_start", stage="execute_task_sample")
    sample_variant = "base" if requested_cleanup_binding.get("scene_xml") else "ceiling"
    task = task_sampler.sample_task(variant=sample_variant)
    sampled_task_binding = _sampled_task_binding(task)
    cleanup_binding_result = _cleanup_primitive_binding_from_sampled_task(
        requested_cleanup_binding,
        sampled_task_binding,
    )
    _record_worker_exception_context(
        sampled_task_binding=sampled_task_binding,
        cleanup_primitive_binding=cleanup_binding_result.get("cleanup_primitive_binding"),
        cleanup_primitive_binding_blockers=cleanup_binding_result.get("blockers", []),
    )
    _emit_worker_event(
        "execute_task_sample_done",
        stage="execute_task_sample",
        sampled_task_binding=sampled_task_binding,
        requested_cleanup_primitive_binding=requested_cleanup_binding,
        cleanup_primitive_binding=cleanup_binding_result.get("cleanup_primitive_binding"),
        cleanup_primitive_binding_blockers=cleanup_binding_result.get("blockers", []),
    )
    _emit_worker_event("execute_task_reset_start", stage="execute_task_reset")
    task.reset()
    _emit_worker_event("execute_task_reset_done", stage="execute_task_reset")
    return task, {
        "sampled_task_binding": sampled_task_binding,
        "cleanup_binding_result": cleanup_binding_result,
    }


def _run_execute_policy(
    config: Any,
    task: Any,
    steps: int,
    run_task_for_steps_with_observations: Any,
) -> tuple[Any, Any, Any, dict[str, Any], dict[str, Any]]:
    _record_cuda_memory_snapshot("execute_policy_construct_before")
    _emit_worker_event("execute_policy_construct_start", stage="execute_policy_construct")
    policy = config.policy_config.policy_cls(config, task)
    _record_cuda_memory_snapshot("execute_policy_construct_after")
    _emit_worker_event("execute_policy_construct_done", stage="execute_policy_construct")
    _record_cuda_memory_snapshot("execute_policy_reset_before")
    _emit_worker_event("execute_policy_reset_start", stage="execute_policy_reset")
    policy.reset()
    _record_cuda_memory_snapshot("execute_policy_reset_after")
    _emit_worker_event("execute_policy_reset_done", stage="execute_policy_reset")
    _record_cuda_memory_snapshot("execute_policy_run_start")
    _emit_worker_event("execute_policy_run_start", stage="execute_policy_run", steps=steps)
    try:
        initial_qpos, final_qpos, initial_obs, final_obs = run_task_for_steps_with_observations(
            task,
            policy,
            num_steps=steps,
            profiler=None,
        )
    except BaseException as exc:  # noqa: BLE001 - preserve target-runtime diagnosis.
        _record_policy_run_exception(policy, exc, steps=steps)
        raise
    _record_cuda_memory_snapshot("execute_policy_run_done")
    _emit_worker_event("execute_policy_run_done", stage="execute_policy_run", steps=steps)
    return policy, initial_qpos, final_qpos, initial_obs, final_obs


def _record_policy_run_exception(policy: Any, exc: BaseException, *, steps: int) -> None:
    policy_exception_context = _policy_exception_context(
        policy,
        exc,
        stage="execute_policy_run",
        steps_requested=steps,
    )
    _record_worker_exception_context(
        policy_exception_context=policy_exception_context,
    )
    _emit_worker_event(
        "execute_policy_run_exception",
        stage="execute_policy_run",
        policy_exception_context=policy_exception_context,
    )
    _record_cuda_memory_snapshot("execute_policy_run_exception")


def _execute_probe_image_artifacts(
    output_dir: Path,
    initial_obs: dict[str, Any],
    final_obs: dict[str, Any],
) -> dict[str, str]:
    views_dir = output_dir / "planner_views"
    image_artifacts = {}
    initial = _write_first_camera_image(initial_obs, views_dir, "initial")
    final = _write_first_camera_image(final_obs, views_dir, "final")
    if initial:
        image_artifacts["initial"] = str(initial.relative_to(output_dir))
    if final:
        image_artifacts["final"] = str(final.relative_to(output_dir))
    return image_artifacts


def _policy_exception_context(
    policy: Any,
    exc: BaseException,
    *,
    stage: str,
    steps_requested: int,
) -> dict[str, Any]:
    action_primitives = [
        _policy_action_primitive_context(index, primitive)
        for index, primitive in enumerate(getattr(policy, "action_primitives", []) or [])
    ]
    return {
        "schema": "planner_probe_policy_exception_context_v1",
        "stage": stage,
        "steps_requested": steps_requested,
        "exception_type": type(exc).__name__,
        "message": str(exc),
        "failure_kind": _policy_exception_failure_kind(exc),
        "no_planned_trajectory": _policy_exception_is_no_planned_trajectory(exc),
        "policy_class": type(policy).__name__,
        "policy_module": type(policy).__module__,
        "policy_current_phase": _safe_current_phase(policy),
        "action_primitive_count": len(action_primitives),
        "action_primitives": action_primitives,
    }


def _policy_exception_failure_kind(exc: BaseException) -> str:
    if _policy_exception_is_no_planned_trajectory(exc):
        return "curobo_no_planned_trajectory"
    return "policy_exception"


def _policy_exception_is_no_planned_trajectory(exc: BaseException) -> bool:
    message = str(exc).lower()
    return "no planned trajectory" in message or "trajectory index >= len" in message


def _policy_action_primitive_context(index: int, primitive: Any) -> dict[str, Any]:
    trajectory = _safe_attr(primitive, "planned_trajectory")
    if trajectory is None:
        trajectory = _safe_attr(primitive, "_planned_trajectory")
    return {
        "index": index,
        "primitive_class": type(primitive).__name__,
        "primitive_module": type(primitive).__module__,
        "current_phase": _safe_current_phase(primitive),
        "planned_trajectory_present": trajectory is not None,
        "planned_trajectory_len": _safe_len(trajectory),
        "trajectory_index": _diagnostic_json_value(
            _first_present_attr(
                primitive,
                (
                    "trajectory_index",
                    "_trajectory_index",
                    "current_trajectory_index",
                    "_current_trajectory_index",
                ),
            )
        ),
    }


def _safe_current_phase(obj: Any) -> str:
    getter = getattr(obj, "get_current_phase", None)
    if callable(getter):
        try:
            return str(getter())
        except Exception as exc:  # pragma: no cover - diagnostic only
            return f"{type(exc).__name__}: {exc}"
    for attr in ("current_phase", "phase"):
        value = _safe_attr(obj, attr)
        if value is not None:
            return str(value)
    return ""


def _first_present_attr(obj: Any, names: tuple[str, ...]) -> Any:
    for name in names:
        value = _safe_attr(obj, name)
        if value is not None:
            return value
    return None


def _safe_attr(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:  # pragma: no cover - diagnostic only
        return None


def _safe_len(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return len(value)
    except TypeError:
        return None


def _configure_exact_cleanup_task(config: Any, args: argparse.Namespace) -> dict[str, Any]:
    requested = _requested_cleanup_primitive_binding(args)
    scene_xml = str(getattr(args, "cleanup_scene_xml", "") or "")
    planner_object_id = str(requested.get("planner_object_id") or "")
    planner_target_id = str(requested.get("planner_target_receptacle_id") or "")
    blockers = []
    scene_applied = _apply_exact_cleanup_scene_override(config, scene_xml, blockers)
    alias_applied = _apply_exact_cleanup_alias_overrides(
        config,
        planner_object_id=planner_object_id,
        planner_target_id=planner_target_id,
    )
    for attr in ("task_config_preset_exp", "task_config_preset_scn"):
        if hasattr(config, attr):
            setattr(config, attr, None)
    return {
        "schema": "planner_probe_exact_cleanup_task_config_v1",
        "applied": scene_applied or alias_applied,
        "scene_xml": scene_xml,
        "planner_object_id": planner_object_id,
        "planner_target_receptacle_id": planner_target_id,
        "blockers": blockers,
        "evidence_note": (
            "Probe-local config override for sampling a planner task from the cleanup "
            "artifact scene with requested cleanup object/target aliases."
        ),
    }


def _apply_exact_cleanup_scene_override(
    config: Any,
    scene_xml: str,
    blockers: list[dict[str, Any]],
) -> bool:
    if not scene_xml:
        return False
    scene_path = Path(scene_xml)
    if not scene_path.is_file():
        blockers.append(
            {
                "code": "cleanup_scene_xml_missing",
                "message": f"Requested cleanup scene XML does not exist: {scene_xml}",
            }
        )
        return False
    config.scene_dataset = str(scene_path)
    config.data_split = "val"
    config.task_sampler_config.house_inds = [0]
    config.task_sampler_config.samples_per_house = 1
    config.task_sampler_config.max_tasks = 1
    return True


def _apply_exact_cleanup_alias_overrides(
    config: Any,
    *,
    planner_object_id: str,
    planner_target_id: str,
) -> bool:
    task_config = getattr(config, "task_config", None)
    if task_config is None:
        return False
    applied = False
    if planner_object_id:
        task_config.pickup_obj_name = planner_object_id
        if hasattr(config.task_sampler_config, "pickup_obj_name"):
            config.task_sampler_config.pickup_obj_name = planner_object_id
        applied = True
    if planner_target_id:
        if hasattr(task_config, "place_receptacle_name"):
            task_config.place_receptacle_name = planner_target_id
        if hasattr(task_config, "place_target_name"):
            task_config.place_target_name = planner_target_id
        if hasattr(config.task_sampler_config, "place_target_name"):
            config.task_sampler_config.place_target_name = planner_target_id
        applied = True
    return applied


def _cleanup_task_config_request_from_args(args: argparse.Namespace) -> dict[str, Any]:
    requested = _requested_cleanup_primitive_binding(args)
    scene_xml = str(getattr(args, "cleanup_scene_xml", "") or "")
    blockers = []
    if scene_xml and not Path(scene_xml).is_file():
        blockers.append(
            {
                "code": "cleanup_scene_xml_missing",
                "message": f"Requested cleanup scene XML does not exist: {scene_xml}",
            }
        )
    return {
        "schema": "planner_probe_exact_cleanup_task_config_v1",
        "applied": bool(
            scene_xml
            or requested.get("planner_object_id")
            or requested.get("planner_target_receptacle_id")
        ),
        "scene_xml": scene_xml,
        "planner_object_id": str(requested.get("planner_object_id") or ""),
        "planner_target_receptacle_id": str(requested.get("planner_target_receptacle_id") or ""),
        "blockers": blockers,
        "evidence_note": (
            "Probe-local config request for sampling a planner task from the cleanup "
            "artifact scene with requested cleanup object/target aliases."
        ),
    }


def _apply_exact_cleanup_task_sampler_adapter(
    task_sampler: Any,
    requested_cleanup_binding: dict[str, Any],
) -> dict[str, Any]:
    planner_object_id = str(
        requested_cleanup_binding.get("planner_object_id")
        or requested_cleanup_binding.get("object_id")
        or ""
    )
    planner_target_id = str(
        requested_cleanup_binding.get("planner_target_receptacle_id")
        or requested_cleanup_binding.get("target_receptacle_id")
        or ""
    )
    if not planner_target_id:
        return {
            "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
            "applied": False,
            "reason": "no_requested_planner_target",
        }
    if not (
        hasattr(task_sampler, "_get_place_target_candidates")
        and hasattr(task_sampler, "_prepare_place_target")
    ):
        return {
            "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
            "applied": False,
            "reason": "task_sampler_has_no_place_target_hooks",
            "task_sampler_class": type(task_sampler).__name__,
            "planner_target_receptacle_id": planner_target_id,
        }

    def exact_place_target_candidates(
        self: Any,
        env: Any,
        pickup_obj_name: str,
        supporting_geom_id: int,
    ) -> list[str]:
        return [planner_target_id]

    def exact_prepare_place_target(
        self: Any,
        env: Any,
        place_target_name: str,
        pickup_obj_name: str,
        pickup_obj_pos: Any,
        supporting_geom_id: int,
    ) -> bool:
        om = env.object_managers[env.current_batch_index]
        om.get_object_by_name(planner_target_id)
        self.place_receptacle_name = planner_target_id
        return True

    task_sampler._get_place_target_candidates = MethodType(  # noqa: SLF001
        exact_place_target_candidates,
        task_sampler,
    )
    task_sampler._prepare_place_target = MethodType(  # noqa: SLF001
        exact_prepare_place_target,
        task_sampler,
    )
    adapter = {
        "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
        "applied": True,
        "task_sampler_class": type(task_sampler).__name__,
        "planner_object_id": planner_object_id,
        "planner_target_receptacle_id": planner_target_id,
        "hooks": ["_get_place_target_candidates", "_prepare_place_target"],
        "evidence_note": (
            "Probe-local adapter makes the upstream pick-and-place sampler use the "
            "cleanup request's object and target instead of unrelated generated candidates."
        ),
    }
    select_pickup_object = getattr(task_sampler, "_select_pickup_object", None)
    reset = getattr(task_sampler, "reset", None)
    if planner_object_id and callable(select_pickup_object):

        def exact_select_pickup_object(self: Any, env: Any) -> Any:
            _apply_exact_pickup_candidate_binding(self, planner_object_id, adapter)
            return select_pickup_object(env)

        task_sampler._select_pickup_object = MethodType(  # noqa: SLF001
            exact_select_pickup_object,
            task_sampler,
        )
        adapter["hooks"].append("_select_pickup_object_exact_pickup_candidate_pool")
    elif planner_object_id and callable(reset):

        def exact_reset(self: Any, *args: Any, **kwargs: Any) -> Any:
            result = reset(*args, **kwargs)
            _apply_exact_pickup_candidate_binding(self, planner_object_id, adapter)
            return result

        task_sampler.reset = MethodType(exact_reset, task_sampler)
        adapter["hooks"].append("reset_exact_pickup_candidate_pool")
    return adapter


def _apply_exact_pickup_candidate_binding(
    task_sampler: Any,
    planner_object_id: str,
    adapter: dict[str, Any],
) -> None:
    candidate_objects = getattr(task_sampler, "candidate_objects", None)
    binding = {
        "schema": "planner_probe_exact_pickup_candidate_binding_v1",
        "planner_object_id": planner_object_id,
        "retry_budget": EXACT_PICKUP_RETRY_BUDGET,
        "retry_budget_applied": False,
        "candidate_count_before": _candidate_object_count(task_sampler),
        "candidate_names_before": _candidate_object_names(task_sampler),
        "requested_present_before": None,
        "candidate_count_after": None,
        "candidate_names_after": None,
        "requested_present_after": None,
        "action": "no_candidate_pool",
    }
    if candidate_objects is None:
        adapter["exact_pickup_candidate_binding"] = binding
        return
    try:
        candidates = list(candidate_objects)
    except TypeError:
        adapter["exact_pickup_candidate_binding"] = binding
        return
    matches = [item for item in candidates if str(getattr(item, "name", item)) == planner_object_id]
    binding["requested_present_before"] = bool(matches)
    if matches:
        task_sampler.candidate_objects = _repeat_candidate_objects(
            matches,
            EXACT_PICKUP_RETRY_BUDGET,
        )
        binding["action"] = "filtered_to_requested_candidate"
    else:
        task_sampler.candidate_objects = _repeat_candidate_objects(
            [SimpleNamespace(name=planner_object_id)],
            EXACT_PICKUP_RETRY_BUDGET,
        )
        binding["action"] = "injected_requested_candidate_name"
    binding["retry_budget_applied"] = int(binding["candidate_count_before"] or 0) != len(
        task_sampler.candidate_objects
    )
    binding["candidate_count_after"] = _candidate_object_count(task_sampler)
    binding["candidate_names_after"] = _candidate_object_names(task_sampler)
    binding["requested_present_after"] = _candidate_name_present(
        binding["candidate_names_after"],
        planner_object_id,
    )
    adapter["exact_pickup_candidate_binding"] = binding


def _repeat_candidate_objects(candidates: list[Any], retry_budget: int) -> list[Any]:
    if retry_budget <= 0 or len(candidates) >= retry_budget:
        return list(candidates)
    return [candidates[index % len(candidates)] for index in range(retry_budget)]


def _apply_task_sampler_failure_diagnostics_adapter(
    task_sampler: Any,
    robot_placement_profile: dict[str, Any] | None = None,
    *,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    profile = robot_placement_profile or {}
    diagnostics: dict[str, Any] = {
        "schema": "planner_probe_task_sampler_failure_diagnostics_v1",
        "applied": False,
        "task_sampler_class": type(task_sampler).__name__,
        "robot_placement_config": _task_sampler_robot_placement_config(task_sampler),
        "robot_placement_profile": {
            "profile": profile.get("profile", "none"),
            "applied": bool(profile.get("applied")),
        },
        "place_robot_near_overrides": dict(profile.get("place_robot_near_overrides") or {}),
        "hooks": [],
        "robot_placement_attempts": [],
        "place_robot_near_calls": [],
        "placement_scene_diagnostics": [],
        "asset_failures": [],
        "grasp_load_attempts": [],
        "grasp_collision_checks": [],
        "grasp_failures": [],
        "candidate_removals": [],
        "candidate_removal_effectiveness": [],
        "image_artifacts": {},
        "visual_capture_failures": [],
    }
    _install_robot_placement_diagnostics(
        task_sampler,
        diagnostics,
        profile,
        output_dir=output_dir,
    )
    _install_asset_failure_diagnostics(task_sampler, diagnostics)
    _install_grasp_collision_diagnostics(task_sampler, diagnostics)
    _install_grasp_failure_diagnostics(task_sampler, diagnostics)
    _install_candidate_removal_diagnostics(task_sampler, diagnostics)
    diagnostics["applied"] = bool(diagnostics["hooks"])
    _refresh_task_sampler_failure_diagnostics(diagnostics)
    return diagnostics


def _install_robot_placement_diagnostics(
    task_sampler: Any,
    diagnostics: dict[str, Any],
    profile: dict[str, Any],
    *,
    output_dir: Path | None,
) -> None:
    sample_and_place_robot = getattr(task_sampler, "_sample_and_place_robot", None)
    if callable(sample_and_place_robot):

        def recording_sample_and_place_robot(self: Any, env: Any) -> Any:
            attempt = _task_sampler_robot_placement_attempt(self, env, diagnostics)
            started_at = time.monotonic()
            restore_place_robot_near = _install_place_robot_near_profile_adapter(
                env,
                diagnostics,
                profile,
            )
            try:
                result = sample_and_place_robot(env)
            except BaseException as exc:  # noqa: BLE001 - diagnostic wrapper must re-raise.
                attempt.update(
                    {
                        "result": "failed",
                        "exception_type": type(exc).__name__,
                        "message": str(exc),
                    }
                )
                raise
            else:
                attempt["result"] = "placed"
                image_artifacts = _capture_task_sampler_diagnostic_views(
                    env,
                    output_dir,
                    prefix=f"post_placement_attempt_{attempt['attempt_index']:03d}",
                    diagnostics=diagnostics,
                )
                if image_artifacts:
                    attempt["image_artifacts"] = image_artifacts
                    diagnostics["image_artifacts"].update(image_artifacts)
                    _record_worker_exception_context(
                        image_artifacts=diagnostics["image_artifacts"],
                    )
                return result
            finally:
                restore_place_robot_near()
                attempt["elapsed_s"] = round(time.monotonic() - started_at, 6)
                diagnostics["robot_placement_attempts"].append(attempt)
                _refresh_task_sampler_failure_diagnostics(diagnostics)

        task_sampler._sample_and_place_robot = MethodType(  # noqa: SLF001
            recording_sample_and_place_robot,
            task_sampler,
        )
        diagnostics["hooks"].append("_sample_and_place_robot")


def _install_asset_failure_diagnostics(
    task_sampler: Any,
    diagnostics: dict[str, Any],
) -> None:
    report_asset_failure = getattr(task_sampler, "report_asset_failure", None)
    if callable(report_asset_failure):

        def recording_report_asset_failure(self: Any, asset_uid: Any, reason: Any) -> Any:
            diagnostics["asset_failures"].append(
                {
                    "asset_uid": str(asset_uid or ""),
                    "reason": str(reason or ""),
                }
            )
            _refresh_task_sampler_failure_diagnostics(diagnostics)
            return report_asset_failure(asset_uid, reason)

        task_sampler.report_asset_failure = MethodType(  # noqa: SLF001
            recording_report_asset_failure,
            task_sampler,
        )
        diagnostics["hooks"].append("report_asset_failure")


def _install_grasp_failure_diagnostics(
    task_sampler: Any,
    diagnostics: dict[str, Any],
) -> None:
    report_grasp_failure = getattr(task_sampler, "report_grasp_failure", None)
    if callable(report_grasp_failure):

        def recording_report_grasp_failure(
            self: Any,
            obj_name: Any,
            max_failures: int = 2,
        ) -> Any:
            before_candidates = _candidate_object_count(self)
            before_count = _grasp_failure_count(self, obj_name)
            before_names = _candidate_object_names(self)
            removal_count_before = len(diagnostics.get("candidate_removals") or [])
            result = report_grasp_failure(obj_name, max_failures)
            after_candidates = _candidate_object_count(self)
            after_count = _grasp_failure_count(self, obj_name)
            after_names = _candidate_object_names(self)
            removal_count_after = len(diagnostics.get("candidate_removals") or [])
            diagnostics["grasp_failures"].append(
                {
                    "object_name": str(obj_name or ""),
                    "count_before": before_count,
                    "count_after": after_count,
                    "max_failures": int(max_failures),
                    "threshold_exceeded": after_count > int(max_failures),
                    "threshold_crossed": before_count <= int(max_failures) < after_count,
                    "candidate_count_before": before_candidates,
                    "candidate_count_after": after_candidates,
                    "candidate_name_present_before": _candidate_name_present(
                        before_names,
                        obj_name,
                    ),
                    "candidate_name_present_after": _candidate_name_present(after_names, obj_name),
                    "candidate_removal_call_count_before": removal_count_before,
                    "candidate_removal_call_count_after": removal_count_after,
                    "candidate_removal_call_count_delta": (
                        removal_count_after - removal_count_before
                    ),
                    "removed_candidate": (
                        before_candidates is not None
                        and after_candidates is not None
                        and after_candidates < before_candidates
                    ),
                }
            )
            _refresh_task_sampler_failure_diagnostics(diagnostics)
            return result

        task_sampler.report_grasp_failure = MethodType(  # noqa: SLF001
            recording_report_grasp_failure,
            task_sampler,
        )
        diagnostics["hooks"].append("report_grasp_failure")


def _install_candidate_removal_diagnostics(
    task_sampler: Any,
    diagnostics: dict[str, Any],
) -> None:
    remove_candidate_object = getattr(task_sampler, "_remove_candidate_object", None)
    if callable(remove_candidate_object):

        def recording_remove_candidate_object(self: Any, object_name: Any) -> Any:
            before_candidates = _candidate_object_count(self)
            before_names = _candidate_object_names(self)
            result = remove_candidate_object(object_name)
            after_candidates = _candidate_object_count(self)
            after_names = _candidate_object_names(self)
            record = {
                "object_name": str(object_name or ""),
                "candidate_count_before": before_candidates,
                "candidate_count_after": after_candidates,
                "candidate_name_present_before": _candidate_name_present(
                    before_names,
                    object_name,
                ),
                "candidate_name_present_after": _candidate_name_present(after_names, object_name),
                "effective_removal": (
                    before_candidates is not None
                    and after_candidates is not None
                    and after_candidates < before_candidates
                ),
                "candidate_names_before": before_names,
                "candidate_names_after": after_names,
            }
            diagnostics["candidate_removals"].append(record)
            diagnostics["candidate_removal_effectiveness"].append(record)
            _refresh_task_sampler_failure_diagnostics(diagnostics)
            return result

        task_sampler._remove_candidate_object = MethodType(  # noqa: SLF001
            recording_remove_candidate_object,
            task_sampler,
        )
        diagnostics["hooks"].append("_remove_candidate_object")


def _install_grasp_collision_diagnostics(task_sampler: Any, diagnostics: dict[str, Any]) -> None:
    installed_hooks = []
    for module in _task_sampler_grasp_modules(task_sampler):
        for hook_name in (
            _install_grasp_load_diagnostic_hook(module, task_sampler, diagnostics),
            _install_grasp_mask_diagnostic_hook(module, task_sampler, diagnostics),
        ):
            if hook_name:
                installed_hooks.append(hook_name)

    if installed_hooks:
        diagnostics["hooks"].append("grasp_collision_diagnostics")
        diagnostics["grasp_collision_hooks"] = installed_hooks


def _install_grasp_load_diagnostic_hook(
    module: Any,
    task_sampler: Any,
    diagnostics: dict[str, Any],
) -> str | None:
    load_grasps_for_object = getattr(module, "load_grasps_for_object", None)
    if not callable(load_grasps_for_object):
        return None
    original_load = getattr(
        load_grasps_for_object,
        "__roboclaws_original__",
        load_grasps_for_object,
    )
    module_name = str(getattr(module, "__name__", ""))

    def recording_load_grasps_for_object(
        object_name: Any,
        num_grasps: int = 50,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        record: dict[str, Any] = {
            "schema": "planner_probe_grasp_load_attempt_v1",
            "module": module_name,
            "asset_uid": str(object_name or ""),
            "pickup_obj_name": _task_sampler_config_pickup_obj_name(task_sampler),
            "requested_grasp_count": _safe_count_value(num_grasps),
        }
        started_at = time.monotonic()
        try:
            result = original_load(object_name, num_grasps, *args, **kwargs)
        except BaseException as exc:  # noqa: BLE001 - diagnostic wrapper must re-raise.
            record.update(
                {
                    "result": "exception",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            raise
        else:
            gripper, cached_grasps = result
            record.update(
                {
                    "result": "loaded",
                    "gripper": str(gripper or ""),
                    "cached_grasp_count": _safe_len(cached_grasps),
                }
            )
            return result
        finally:
            record["elapsed_s"] = round(time.monotonic() - started_at, 6)
            diagnostics["grasp_load_attempts"].append(record)
            _refresh_task_sampler_failure_diagnostics(diagnostics)

    recording_load_grasps_for_object.__roboclaws_original__ = original_load  # type: ignore[attr-defined]
    setattr(module, "load_grasps_for_object", recording_load_grasps_for_object)
    return f"{module_name}.load_grasps_for_object"


def _install_grasp_mask_diagnostic_hook(
    module: Any,
    task_sampler: Any,
    diagnostics: dict[str, Any],
) -> str | None:
    get_noncolliding_grasp_mask = getattr(module, "get_noncolliding_grasp_mask", None)
    if not callable(get_noncolliding_grasp_mask):
        return None
    original_mask = getattr(
        get_noncolliding_grasp_mask,
        "__roboclaws_original__",
        get_noncolliding_grasp_mask,
    )
    module_name = str(getattr(module, "__name__", ""))

    def recording_get_noncolliding_grasp_mask(
        mj_model: Any,
        mj_data: Any,
        grasp_poses_world: Any,
        batch_size: int,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        record = {
            "schema": "planner_probe_grasp_collision_check_v1",
            "module": module_name,
            "asset_uid": _latest_grasp_load_asset_uid(diagnostics),
            "pickup_obj_name": _task_sampler_config_pickup_obj_name(task_sampler),
            "grasp_pose_count": _safe_len(grasp_poses_world),
            "batch_size": _safe_count_value(batch_size),
        }
        started_at = time.monotonic()
        try:
            result = original_mask(
                mj_model,
                mj_data,
                grasp_poses_world,
                batch_size,
                *args,
                **kwargs,
            )
        except BaseException as exc:  # noqa: BLE001 - diagnostic wrapper must re-raise.
            record.update(
                {
                    "result": "exception",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            raise
        else:
            noncolliding_count = _truthy_count(result)
            grasp_pose_count = _safe_len(grasp_poses_world)
            record.update(
                {
                    "result": "checked",
                    "noncolliding_grasp_count": noncolliding_count,
                    "colliding_grasp_count": (
                        grasp_pose_count - noncolliding_count
                        if grasp_pose_count is not None and noncolliding_count is not None
                        else None
                    ),
                    "zero_noncolliding": noncolliding_count == 0,
                }
            )
            return result
        finally:
            record["elapsed_s"] = round(time.monotonic() - started_at, 6)
            diagnostics["grasp_collision_checks"].append(record)
            _refresh_task_sampler_failure_diagnostics(diagnostics)

    recording_get_noncolliding_grasp_mask.__roboclaws_original__ = original_mask  # type: ignore[attr-defined]
    setattr(module, "get_noncolliding_grasp_mask", recording_get_noncolliding_grasp_mask)
    return f"{module_name}.get_noncolliding_grasp_mask"


def _task_sampler_grasp_modules(task_sampler: Any) -> list[Any]:
    modules: list[Any] = []
    module_names = {"molmo_spaces.tasks.pick_task_sampler"}
    for method_name in ("_sample_task", "sample", "next_task"):
        method = getattr(task_sampler, method_name, None)
        module_name = getattr(method, "__module__", None)
        if module_name:
            module_names.add(str(module_name))
    for module_name in sorted(module_names):
        module = sys.modules.get(module_name)
        if module is None:
            continue
        if module not in modules and (
            hasattr(module, "load_grasps_for_object")
            or hasattr(module, "get_noncolliding_grasp_mask")
        ):
            modules.append(module)
    return modules


def _task_sampler_config_pickup_obj_name(task_sampler: Any) -> str:
    task_config = getattr(getattr(task_sampler, "config", None), "task_config", None)
    return str(getattr(task_config, "pickup_obj_name", "") or "")


def _latest_grasp_load_asset_uid(diagnostics: dict[str, Any]) -> str:
    for item in reversed(diagnostics.get("grasp_load_attempts") or []):
        if isinstance(item, dict) and item.get("asset_uid"):
            return str(item.get("asset_uid") or "")
    return ""


def _safe_len(value: Any) -> int | None:
    try:
        return len(value)
    except TypeError:
        return None


def _safe_count_value(value: Any) -> Any:
    try:
        return int(value)
    except Exception:
        return _diagnostic_json_value(value)


def _truthy_count(value: Any) -> int | None:
    try:
        import numpy as np

        return int(np.sum(value))
    except Exception:
        pass
    try:
        return sum(1 for item in value if bool(item))
    except TypeError:
        return None


def _capture_task_sampler_diagnostic_views(
    env: Any,
    output_dir: Path | None,
    *,
    prefix: str,
    diagnostics: dict[str, Any],
) -> dict[str, str]:
    if output_dir is None or int(diagnostics.get("visual_capture_count") or 0) >= 1:
        return {}
    try:
        camera_manager = getattr(env, "camera_manager", None)
        registry = getattr(camera_manager, "registry", None)
        update_all = getattr(registry, "update_all_cameras", None)
        if callable(update_all):
            update_all(env)
        camera_names = _task_sampler_diagnostic_camera_names(env)
        if not camera_names:
            return {}
        views_dir = output_dir / "planner_views"
        artifacts = {}
        for camera_name in camera_names[:1]:
            path = _write_env_camera_image(env, camera_name, views_dir, prefix)
            if path:
                key = f"{prefix}_{_safe_artifact_key(camera_name)}"
                artifacts[key] = str(path.relative_to(output_dir))
        if artifacts:
            diagnostics["visual_capture_count"] = (
                int(diagnostics.get("visual_capture_count") or 0) + 1
            )
        return artifacts
    except Exception as exc:  # pragma: no cover - best-effort failure evidence.
        diagnostics.setdefault("visual_capture_failures", []).append(
            {
                "prefix": prefix,
                "exception_type": type(exc).__name__,
                "message": str(exc),
            }
        )
        return {}


def _task_sampler_diagnostic_camera_names(env: Any) -> list[str]:
    registry = getattr(getattr(env, "camera_manager", None), "registry", None)
    keys = getattr(registry, "keys", None)
    if not callable(keys):
        return []
    names = [str(name) for name in keys()]
    preferred = [
        "head_camera",
        "camera_follower",
        "wrist_camera",
        "wrist_camera_l",
        "wrist_camera_r",
        "exo_camera_1",
    ]
    ordered = [name for name in preferred if name in names]
    ordered.extend(name for name in names if name not in ordered)
    return ordered


def _write_env_camera_image(
    env: Any,
    camera_name: str,
    output_dir: Path,
    prefix: str,
) -> Path | None:
    import numpy as np
    from PIL import Image

    render = getattr(env, "render_rgb_frame", None)
    if not callable(render):
        return None
    frame = np.asarray(render(camera_name))
    if frame.ndim != 3:
        return None
    if frame.shape[2] > 3:
        frame = frame[:, :, :3]
    if frame.dtype.kind == "f" and float(np.nanmax(frame)) <= 1.0:
        frame = frame * 255.0
    image = Image.fromarray(np.clip(frame, 0, 255).astype("uint8"))
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{prefix}_{_safe_artifact_key(camera_name)}.png"
    image.save(path)
    return path


def _safe_artifact_key(value: str) -> str:
    cleaned = "".join(char if char.isalnum() else "_" for char in value.strip())
    return cleaned.strip("_") or "camera"


def _candidate_object_count(task_sampler: Any) -> int | None:
    candidate_objects = getattr(task_sampler, "candidate_objects", None)
    try:
        return len(candidate_objects) if candidate_objects is not None else None
    except TypeError:
        return None


def _candidate_object_names(task_sampler: Any, *, limit: int = 40) -> list[str] | None:
    candidate_objects = getattr(task_sampler, "candidate_objects", None)
    if candidate_objects is None:
        return None
    names = []
    try:
        iterator = iter(candidate_objects)
    except TypeError:
        return None
    for item in iterator:
        if len(names) >= limit:
            break
        name = getattr(item, "name", None)
        names.append(str(name if name is not None else item))
    return names


def _candidate_name_present(candidate_names: list[str] | None, object_name: Any) -> bool | None:
    if candidate_names is None:
        return None
    return str(object_name or "") in candidate_names


def _grasp_failure_count(task_sampler: Any, obj_name: Any) -> int:
    counts = getattr(task_sampler, "_grasp_failure_counts", None) or {}
    return int(counts.get(obj_name, 0))


def _install_place_robot_near_profile_adapter(
    env: Any,
    diagnostics: dict[str, Any],
    robot_placement_profile: dict[str, Any],
) -> Any:
    overrides = dict(robot_placement_profile.get("place_robot_near_overrides") or {})
    original = getattr(env, "place_robot_near", None)
    if not callable(original):
        return lambda: None
    should_apply_overrides = bool(overrides and robot_placement_profile.get("applied"))

    def profiled_place_robot_near(*args: Any, **kwargs: Any) -> Any:
        call = {
            "call_index": len(diagnostics.get("place_robot_near_calls") or []) + 1,
            "requested": _place_robot_near_call_values(kwargs),
        }
        effective_kwargs = dict(kwargs)
        if should_apply_overrides:
            for name, value in overrides.items():
                effective_kwargs[name] = value
        call["effective"] = _place_robot_near_call_values(effective_kwargs)
        scene_diagnostic = _place_robot_near_scene_diagnostic(
            env,
            call["call_index"],
            effective_kwargs,
        )
        if scene_diagnostic:
            call["scene_diagnostic"] = scene_diagnostic
            diagnostics["placement_scene_diagnostics"].append(scene_diagnostic)
        started_at = time.monotonic()
        try:
            result = original(*args, **effective_kwargs)
        except BaseException as exc:  # noqa: BLE001 - diagnostic wrapper must re-raise.
            call.update(
                {
                    "result": "exception",
                    "exception_type": type(exc).__name__,
                    "message": str(exc),
                }
            )
            raise
        else:
            call["result"] = _diagnostic_json_value(result)
            return result
        finally:
            call["elapsed_s"] = round(time.monotonic() - started_at, 6)
            diagnostics["place_robot_near_calls"].append(call)
            _refresh_task_sampler_failure_diagnostics(diagnostics)

    setattr(env, "place_robot_near", profiled_place_robot_near)

    def restore() -> None:
        setattr(env, "place_robot_near", original)

    return restore


def _place_robot_near_scene_diagnostic(
    env: Any,
    call_index: int,
    kwargs: dict[str, Any],
) -> dict[str, Any]:
    diagnostic: dict[str, Any] = {
        "schema": "planner_probe_placement_scene_diagnostic_v1",
        "call_index": call_index,
        "target_name": _target_name(kwargs.get("target")),
        "sampling_radius_range": _diagnostic_json_value(
            kwargs.get("sampling_radius_range", (0.0, 1.0))
        ),
        "robot_safety_radius": _diagnostic_json_value(kwargs.get("robot_safety_radius")),
    }
    try:
        import numpy as np
    except Exception as exc:  # pragma: no cover - diagnostic only.
        diagnostic["error"] = f"{type(exc).__name__}: {exc}"
        return diagnostic

    target_position = _target_position(env, kwargs.get("target"))
    if target_position is None:
        diagnostic["error"] = "target_position_unavailable"
        return diagnostic
    target_position_array = np.asarray(target_position, dtype=float)
    diagnostic["target_position"] = _diagnostic_json_value(target_position_array)
    radius_range = _radius_range(kwargs.get("sampling_radius_range", (0.0, 1.0)))
    if radius_range is None:
        diagnostic["error"] = "sampling_radius_range_unavailable"
        return diagnostic
    radius_min, radius_max = radius_range
    diagnostic["sampling_area_m2"] = round(
        float(np.pi * (radius_max**2 - radius_min**2)),
        6,
    )
    try:
        thormap = env.get_thormap(
            agent_radius=float(kwargs.get("robot_safety_radius") or 0.35),
            px_per_m=200,
        )
        free_points = thormap.get_free_points()
        diagnostic["px_per_m"] = _diagnostic_json_value(getattr(thormap, "px_per_m", ""))
        diagnostic["total_free_point_count"] = int(len(free_points))
        if len(free_points) == 0:
            diagnostic["valid_free_point_count"] = 0
            diagnostic["valid_neighborhood_fraction"] = 0.0
            diagnostic["low_free_space"] = True
            return diagnostic
        target_dist = np.linalg.norm(free_points[:, :2] - target_position_array[:2], axis=1)
        valid_mask = (target_dist > radius_min) & (target_dist < radius_max)
        valid_count = int(valid_mask.sum())
        sq_m_per_sq_px = 1 / float(getattr(thormap, "px_per_m", 200) ** 2)
        area = np.pi * (radius_max**2 - radius_min**2)
        fraction = float(valid_count * sq_m_per_sq_px / area) if area > 0 else 0.0
        nearest_index = int(np.argmin(target_dist))
        diagnostic.update(
            {
                "valid_free_point_count": valid_count,
                "valid_neighborhood_fraction": round(fraction, 6),
                "low_free_space": fraction <= 0.05,
                "nearest_free_point_distance_m": round(float(target_dist[nearest_index]), 6),
                "nearest_free_point": _diagnostic_json_value(free_points[nearest_index]),
                "radius_band_counts": _radius_band_counts(target_dist, radius_max),
            }
        )
    except Exception as exc:  # pragma: no cover - best-effort diagnostics.
        diagnostic["error"] = f"{type(exc).__name__}: {exc}"
    return diagnostic


def _target_name(target: Any) -> str:
    if isinstance(target, str):
        return target
    name = getattr(target, "name", None)
    return str(name or "")


def _target_position(env: Any, target: Any) -> Any:
    shape = getattr(target, "shape", None)
    if shape == (3,):
        return target
    if hasattr(target, "position"):
        return getattr(target, "position")
    if isinstance(target, str):
        try:
            om = env.object_managers[env.current_batch_index]
            return getattr(om.get_object_by_name(target), "position", None)
        except Exception:
            return None
    return None


def _radius_range(value: Any) -> tuple[float, float] | None:
    try:
        radius_min, radius_max = value
        return float(radius_min), float(radius_max)
    except Exception:
        return None


def _radius_band_counts(target_dist: Any, radius_max: float) -> list[dict[str, Any]]:
    if radius_max <= 0:
        return []
    bands = sorted({0.25, 0.5, 0.75, 1.0, round(radius_max, 6)})
    rows = []
    previous = 0.0
    for radius in bands:
        if radius > radius_max:
            continue
        count = int(((target_dist > previous) & (target_dist <= radius)).sum())
        rows.append(
            {
                "radius_min_m": previous,
                "radius_max_m": radius,
                "free_point_count": count,
            }
        )
        previous = radius
    if previous < radius_max:
        count = int(((target_dist > previous) & (target_dist <= radius_max)).sum())
        rows.append(
            {
                "radius_min_m": previous,
                "radius_max_m": radius_max,
                "free_point_count": count,
            }
        )
    return rows


def _place_robot_near_call_values(kwargs: dict[str, Any]) -> dict[str, Any]:
    values = {}
    for field in (
        "max_tries",
        "sampling_radius_range",
        "robot_safety_radius",
        "preserve_z",
        "face_target",
        "check_camera_visibility",
    ):
        if field in kwargs:
            values[field] = _diagnostic_json_value(kwargs[field])
    target = kwargs.get("target")
    target_name = getattr(target, "name", None)
    if target_name:
        values["target_name"] = str(target_name)
    return values


def _task_sampler_robot_placement_config(task_sampler: Any) -> dict[str, Any]:
    sampler_config = getattr(getattr(task_sampler, "config", None), "task_sampler_config", None)
    fields = (
        "base_pose_sampling_radius_range",
        "robot_safety_radius",
        "check_robot_placement_visibility",
        "robot_object_z_offset",
        "robot_object_z_offset_random_min",
        "robot_object_z_offset_random_max",
        "max_robot_placement_attempts",
    )
    return {
        field: _diagnostic_json_value(getattr(sampler_config, field))
        for field in fields
        if sampler_config is not None and hasattr(sampler_config, field)
    }


def _task_sampler_robot_placement_attempt(
    task_sampler: Any,
    env: Any,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    task_config = getattr(getattr(task_sampler, "config", None), "task_config", None)
    pickup_obj_name = str(getattr(task_config, "pickup_obj_name", "") or "")
    attempt: dict[str, Any] = {
        "attempt_index": len(diagnostics.get("robot_placement_attempts") or []) + 1,
        "pickup_obj_name": pickup_obj_name,
    }
    if not pickup_obj_name:
        return attempt
    try:
        asset_uid = task_sampler.get_asset_uid_from_object(env, pickup_obj_name)
        if asset_uid:
            attempt["asset_uid"] = str(asset_uid)
    except Exception as exc:  # pragma: no cover - best-effort diagnostics.
        attempt["asset_uid_error"] = f"{type(exc).__name__}: {exc}"
    try:
        om = env.object_managers[env.current_batch_index]
        pickup_obj = om.get_object_by_name(pickup_obj_name)
        if hasattr(pickup_obj, "position"):
            attempt["pickup_position"] = _diagnostic_json_value(pickup_obj.position)
    except Exception as exc:  # pragma: no cover - best-effort diagnostics.
        attempt["pickup_position_error"] = f"{type(exc).__name__}: {exc}"
    return attempt


def _refresh_task_sampler_failure_diagnostics(diagnostics: dict[str, Any]) -> None:
    attempts = diagnostics.get("robot_placement_attempts") or []
    failures = [item for item in attempts if item.get("result") == "failed"]
    diagnostics["robot_placement_attempt_count"] = len(attempts)
    diagnostics["robot_placement_failure_count"] = len(failures)
    diagnostics["place_robot_near_call_count"] = len(
        diagnostics.get("place_robot_near_calls") or []
    )
    scene_diagnostics = diagnostics.get("placement_scene_diagnostics") or []
    diagnostics["placement_scene_diagnostic_count"] = len(scene_diagnostics)
    diagnostics["asset_failure_count"] = len(diagnostics.get("asset_failures") or [])
    grasp_load_attempts = diagnostics.get("grasp_load_attempts") or []
    diagnostics["grasp_load_attempt_count"] = len(grasp_load_attempts)
    diagnostics["grasp_load_failure_count"] = sum(
        1
        for item in grasp_load_attempts
        if isinstance(item, dict) and item.get("result") != "loaded"
    )
    grasp_collision_checks = diagnostics.get("grasp_collision_checks") or []
    diagnostics["grasp_collision_check_count"] = len(grasp_collision_checks)
    diagnostics["zero_noncolliding_grasp_check_count"] = sum(
        1
        for item in grasp_collision_checks
        if isinstance(item, dict) and item.get("zero_noncolliding")
    )
    grasp_failures = diagnostics.get("grasp_failures") or []
    candidate_removals = diagnostics.get("candidate_removals") or []
    diagnostics["grasp_failure_count"] = len(grasp_failures)
    diagnostics["candidate_removal_count"] = len(candidate_removals)
    diagnostics["candidate_effective_removal_count"] = sum(
        1 for item in candidate_removals if isinstance(item, dict) and item.get("effective_removal")
    )
    diagnostics["candidate_name_miss_count"] = sum(
        1
        for item in candidate_removals
        if isinstance(item, dict) and item.get("candidate_name_present_before") is False
    )
    diagnostics["grasp_threshold_exceeded_count"] = sum(
        1 for item in grasp_failures if isinstance(item, dict) and item.get("threshold_exceeded")
    )
    diagnostics["grasp_threshold_crossed_count"] = sum(
        1 for item in grasp_failures if isinstance(item, dict) and item.get("threshold_crossed")
    )
    if failures:
        diagnostics["last_robot_placement_failure"] = failures[-1]
    place_robot_near_calls = diagnostics.get("place_robot_near_calls") or []
    if place_robot_near_calls:
        diagnostics["last_place_robot_near_call"] = place_robot_near_calls[-1]
    if scene_diagnostics:
        diagnostics["last_placement_scene_diagnostic"] = scene_diagnostics[-1]
    if grasp_load_attempts:
        diagnostics["last_grasp_load_attempt"] = grasp_load_attempts[-1]
    if grasp_collision_checks:
        diagnostics["last_grasp_collision_check"] = grasp_collision_checks[-1]


def _diagnostic_json_value(value: Any) -> Any:
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    if isinstance(value, tuple | list):
        return [_diagnostic_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _diagnostic_json_value(item) for key, item in value.items()}
    tolist = getattr(value, "tolist", None)
    if callable(tolist):
        return _diagnostic_json_value(tolist())
    return str(value)


def _sampled_task_binding(task: Any) -> dict[str, Any]:
    task_config = getattr(getattr(task, "config", None), "task_config", None)
    pickup_obj_name = str(getattr(task_config, "pickup_obj_name", "") or "")
    place_receptacle_name = str(getattr(task_config, "place_receptacle_name", "") or "")
    place_target_name = str(getattr(task_config, "place_target_name", "") or "")
    binding = {
        "schema": "planner_probe_sampled_task_binding_v1",
        "pickup_obj_name": pickup_obj_name,
        "place_receptacle_name": place_receptacle_name,
        "place_target_name": place_target_name,
    }
    description = getattr(task, "get_task_description", None)
    if callable(description):
        try:
            binding["task_description"] = str(description())
        except Exception as exc:  # pragma: no cover - diagnostic only
            binding["task_description_error"] = f"{type(exc).__name__}: {exc}"
    return binding


def _requested_cleanup_primitive_binding(args: argparse.Namespace) -> dict[str, Any]:
    object_id = str(getattr(args, "cleanup_object_id", "") or "")
    target_receptacle_id = str(getattr(args, "cleanup_target_receptacle_id", "") or "")
    source_receptacle_id = str(getattr(args, "cleanup_source_receptacle_id", "") or "")
    planner_object_id = str(getattr(args, "cleanup_planner_object_id", "") or "")
    planner_target_receptacle_id = str(
        getattr(args, "cleanup_planner_target_receptacle_id", "") or ""
    )
    tools = _cleanup_tools_from_arg(str(getattr(args, "cleanup_tools", "") or ""))
    requested = bool(
        object_id
        or target_receptacle_id
        or source_receptacle_id
        or planner_object_id
        or planner_target_receptacle_id
        or tools
    )
    return {
        "schema": PLANNER_PROBE_PRIMITIVE_BINDING_SCHEMA,
        "requested": requested,
        "object_id": object_id,
        "target_receptacle_id": target_receptacle_id,
        "source_receptacle_id": source_receptacle_id,
        "scene_xml": str(getattr(args, "cleanup_scene_xml", "") or ""),
        "planner_object_id": planner_object_id,
        "planner_target_receptacle_id": planner_target_receptacle_id,
        "tools": tools,
    }


def _cleanup_primitive_binding_from_sampled_task(
    requested: dict[str, Any],
    sampled: dict[str, Any],
) -> dict[str, Any]:
    if not requested.get("requested"):
        return {
            "requested": False,
            "promoted": False,
            "cleanup_primitive_binding": None,
            "blockers": [],
        }
    blockers = []
    requested_object = str(requested.get("object_id") or "")
    requested_planner_object = str(requested.get("planner_object_id") or requested_object)
    sampled_object = str(sampled.get("pickup_obj_name") or "")
    if requested_planner_object != sampled_object:
        blockers.append(
            {
                "code": "cleanup_binding_object_mismatch",
                "message": (
                    f"Requested planner object_id={requested_planner_object} does not match "
                    f"sampled pickup_obj_name={sampled_object}."
                ),
            }
        )
    requested_target = str(requested.get("target_receptacle_id") or "")
    requested_planner_target = str(
        requested.get("planner_target_receptacle_id") or requested_target
    )
    sampled_target = str(
        sampled.get("place_receptacle_name") or sampled.get("place_target_name") or ""
    )
    if requested_planner_target and requested_planner_target != sampled_target:
        blockers.append(
            {
                "code": "cleanup_binding_target_mismatch",
                "message": (
                    f"Requested planner target_receptacle_id={requested_planner_target} "
                    "does not match "
                    f"sampled place_receptacle_name={sampled_target}."
                ),
            }
        )
    tools = list(requested.get("tools") or [])
    if not tools:
        blockers.append(
            {
                "code": "cleanup_binding_missing_tools",
                "message": "Requested cleanup binding must include at least one tool.",
            }
        )
    if blockers:
        return {
            "requested": True,
            "promoted": False,
            "cleanup_primitive_binding": None,
            "blockers": blockers,
            "sampled_task_binding": sampled,
            "requested_cleanup_primitive_binding": requested,
        }
    return {
        "requested": True,
        "promoted": True,
        "cleanup_primitive_binding": {
            "schema": PLANNER_PROBE_PRIMITIVE_BINDING_SCHEMA,
            "object_id": requested_object,
            "target_receptacle_id": requested_target,
            "source_receptacle_id": str(requested.get("source_receptacle_id") or ""),
            "tools": canonical_cleanup_tool_sequence(tools),
            "planner_object_id": requested_planner_object,
            "planner_target_receptacle_id": requested_planner_target,
            "sampled_task_binding": sampled,
            "evidence_note": "Requested cleanup primitive binding matched sampled planner task.",
        },
        "blockers": [],
    }


def _cleanup_tools_from_arg(value: str) -> list[str]:
    return canonical_cleanup_tool_sequence(value)


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


def _append_optional_int_arg(command: list[str], name: str, value: int | None) -> None:
    if value is not None:
        command.extend([name, str(value)])


def _append_optional_str_arg(command: list[str], name: str, value: str | None) -> None:
    if value:
        command.extend([name, str(value)])


def _prepend_pythonpath(path: Path, existing: str | None) -> str:
    value = str(path)
    if existing:
        return value + os.pathsep + existing
    return value


if __name__ == "__main__":
    main()

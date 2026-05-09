#!/usr/bin/env python3
from __future__ import annotations

import argparse
import faulthandler
import importlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path
from types import MethodType, SimpleNamespace
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
from roboclaws.molmo_cleanup.planner_probe_primitive_executor import (  # noqa: E402
    PLANNER_PROBE_PRIMITIVE_BINDING_SCHEMA,
)
from roboclaws.molmo_cleanup.rby1m_curobo_gate import (  # noqa: E402
    rby1m_curobo_gate_from_planner_probe,
)
from roboclaws.molmo_cleanup.report import render_planner_manipulation_report  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import (  # noqa: E402
    DEFAULT_MOLMOSPACES_PYTHON,
    MOLMOSPACES_SUBPROCESS_BACKEND,
)

DEFAULT_MOLMOSPACES_ROOT = Path("/tmp/roboclaws-molmospaces-spike/molmospaces")
PROBE_TASK = "pick_and_place"
CUROBO_EXTENSION_NAMES = (
    "geom_cu",
    "kinematics_fused_cu",
    "tensor_step_cu",
    "lbfgs_step_cu",
    "line_search_cu",
)
_WORKER_EVENT_STARTED_AT = time.monotonic()
_WARP_COMPATIBILITY_ADAPTER: dict[str, Any] = {"applied": False}
_CUDA_MEMORY_SNAPSHOTS: list[dict[str, Any]] = []
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
    worker_renderer_device_id = _renderer_device_id_for_probe(
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
    _configure_headless_renderer_env(args)
    _emit_worker_event(
        "worker_start",
        stage="worker_start",
        embodiment=args.embodiment,
        probe_mode=args.probe_mode,
    )
    runtime_diagnostics = _runtime_diagnostics(args)
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
            "runtime_diagnostics": _runtime_diagnostics(args),
            "cuda_memory_snapshots": list(_CUDA_MEMORY_SNAPSHOTS),
            **payload,
        }
    except BaseException as exc:  # noqa: BLE001 - worker must report capability blockers.
        _record_cuda_memory_snapshot("worker_exception")
        final_runtime_diagnostics = _runtime_diagnostics(args)
        requested_cleanup_binding = _requested_cleanup_primitive_binding(args)
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
            "cleanup_task_config": _cleanup_task_config_request_from_args(args),
            "requested_cleanup_primitive_binding": requested_cleanup_binding,
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


def _runtime_diagnostics(args: argparse.Namespace) -> dict[str, Any]:
    modules = {}
    for module_name in (
        "molmo_spaces",
        "mujoco",
        "jax",
        "jaxlib",
        "curobo",
        "warp",
        "mujoco_warp",
        "mlspaces_tests",
    ):
        spec = importlib.util.find_spec(module_name)
        package_name = module_name.replace("_", "-")
        modules[module_name] = {
            "available": spec is not None,
            "version": _package_version(package_name),
        }
    renderer_device_id = _renderer_device_id_for_probe(
        probe_mode=args.probe_mode,
        renderer_device_id=args.renderer_device_id,
    )
    return {
        "python_executable": sys.executable,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "embodiment": args.embodiment,
        "probe_mode": args.probe_mode,
        "modules": modules,
        "faulthandler_enabled": faulthandler.is_enabled(),
        "python_faulthandler_env": os.environ.get("PYTHONFAULTHANDLER", ""),
        "mujoco_gl_env": os.environ.get("MUJOCO_GL", ""),
        "pyopengl_platform_env": os.environ.get("PYOPENGL_PLATFORM", ""),
        "cuda_home_env": os.environ.get("CUDA_HOME", ""),
        "torch_cuda_arch_list_env": os.environ.get("TORCH_CUDA_ARCH_LIST", ""),
        "cuda_visible_devices_env": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "pytorch_cuda_alloc_conf_env": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", ""),
        "torch_extensions_dir_env": os.environ.get("TORCH_EXTENSIONS_DIR", ""),
        "torch": _torch_diagnostics(),
        "cuda_memory": _cuda_memory_diagnostics(),
        "curobo_extension_cache": _curobo_extension_cache_diagnostics(),
        "warp_compatibility": _warp_compatibility_diagnostics(),
        "renderer_adapter_enabled": renderer_device_id is not None,
        "renderer_device_id": renderer_device_id,
        "curobo_memory_profile_request": _curobo_memory_profile_request(args),
    }


def _package_version(package_name: str) -> str | None:
    try:
        return importlib.metadata.version(package_name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _torch_diagnostics() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"available": False}
    try:
        import torch
        from torch.utils import cpp_extension

        return {
            "available": True,
            "version": getattr(torch, "__version__", None),
            "cuda_version": getattr(torch.version, "cuda", None),
            "cuda_available": bool(torch.cuda.is_available()),
            "cpp_extension_cuda_home": cpp_extension.CUDA_HOME,
        }
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        return {
            "available": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _cuda_memory_diagnostics() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {
            "available": False,
            "torch_available": False,
            "cuda_visible_devices_env": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "pytorch_cuda_alloc_conf_env": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", ""),
        }
    try:
        import torch

        return _cuda_memory_diagnostics_from_torch(torch)
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        return {
            "available": False,
            "torch_available": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "cuda_visible_devices_env": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
            "pytorch_cuda_alloc_conf_env": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", ""),
        }


def _cuda_memory_diagnostics_from_torch(torch_module: Any) -> dict[str, Any]:
    cuda = getattr(torch_module, "cuda", None)
    available = bool(cuda and cuda.is_available())
    diagnostics: dict[str, Any] = {
        "available": available,
        "torch_available": True,
        "cuda_visible_devices_env": os.environ.get("CUDA_VISIBLE_DEVICES", ""),
        "pytorch_cuda_alloc_conf_env": os.environ.get("PYTORCH_CUDA_ALLOC_CONF", ""),
        "device_count": _cuda_device_count(cuda),
    }
    if not available:
        return diagnostics
    diagnostics["current_device_index"] = _cuda_current_device(cuda)
    diagnostics["devices"] = [
        _cuda_device_entry(cuda, index) for index in range(int(diagnostics["device_count"] or 0))
    ]
    diagnostics["current_snapshot"] = _cuda_memory_snapshot_from_torch(
        torch_module,
        "runtime_diagnostics",
    )
    return diagnostics


def _record_cuda_memory_snapshot(stage: str) -> dict[str, Any]:
    snapshot = _cuda_memory_snapshot(stage)
    _CUDA_MEMORY_SNAPSHOTS.append(snapshot)
    _emit_worker_event("cuda_memory_snapshot", stage=stage, cuda_memory=snapshot)
    return snapshot


def _cuda_memory_snapshot(stage: str) -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {
            "stage": stage,
            "elapsed_s": round(time.monotonic() - _WORKER_EVENT_STARTED_AT, 6),
            "available": False,
            "torch_available": False,
        }
    try:
        import torch

        return _cuda_memory_snapshot_from_torch(torch, stage)
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        return {
            "stage": stage,
            "elapsed_s": round(time.monotonic() - _WORKER_EVENT_STARTED_AT, 6),
            "available": False,
            "torch_available": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }


def _cuda_memory_snapshot_from_torch(torch_module: Any, stage: str) -> dict[str, Any]:
    cuda = getattr(torch_module, "cuda", None)
    snapshot: dict[str, Any] = {
        "stage": stage,
        "elapsed_s": round(time.monotonic() - _WORKER_EVENT_STARTED_AT, 6),
        "torch_available": True,
        "available": bool(cuda and cuda.is_available()),
    }
    if not snapshot["available"]:
        return snapshot
    device_index = _cuda_current_device(cuda)
    snapshot["device_index"] = device_index
    device_entry = _cuda_device_entry(cuda, device_index)
    snapshot["device_name"] = device_entry.get("name")
    snapshot["device_total_memory_bytes"] = device_entry.get("total_memory_bytes")
    free_bytes, total_bytes = _cuda_mem_get_info(cuda, device_index)
    if free_bytes is not None:
        snapshot["free_bytes"] = free_bytes
    if total_bytes is not None:
        snapshot["total_bytes"] = total_bytes
        if free_bytes is not None:
            snapshot["used_bytes"] = total_bytes - free_bytes
            snapshot["free_fraction"] = round(free_bytes / total_bytes, 6) if total_bytes else None
    snapshot["torch_allocated_bytes"] = _cuda_memory_metric(
        cuda,
        "memory_allocated",
        device_index,
    )
    snapshot["torch_reserved_bytes"] = _cuda_memory_metric(
        cuda,
        "memory_reserved",
        device_index,
    )
    snapshot["torch_max_allocated_bytes"] = _cuda_memory_metric(
        cuda,
        "max_memory_allocated",
        device_index,
    )
    snapshot["torch_max_reserved_bytes"] = _cuda_memory_metric(
        cuda,
        "max_memory_reserved",
        device_index,
    )
    return snapshot


def _cuda_device_count(cuda: Any) -> int:
    if not cuda or not hasattr(cuda, "device_count"):
        return 0
    try:
        return int(cuda.device_count())
    except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
        return 0


def _cuda_current_device(cuda: Any) -> int:
    try:
        return int(cuda.current_device())
    except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
        return 0


def _cuda_device_entry(cuda: Any, index: int) -> dict[str, Any]:
    entry: dict[str, Any] = {"index": index}
    try:
        props = cuda.get_device_properties(index)
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        entry.update({"error_type": type(exc).__name__, "error": str(exc)})
        return entry
    entry["name"] = getattr(props, "name", "")
    entry["total_memory_bytes"] = getattr(props, "total_memory", None)
    major = getattr(props, "major", None)
    minor = getattr(props, "minor", None)
    if major is not None and minor is not None:
        entry["compute_capability"] = f"{major}.{minor}"
    return entry


def _cuda_mem_get_info(cuda: Any, device_index: int) -> tuple[int | None, int | None]:
    try:
        free_bytes, total_bytes = cuda.mem_get_info(device_index)
    except TypeError:
        try:
            free_bytes, total_bytes = cuda.mem_get_info()
        except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
            return None, None
    except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
        return None, None
    return int(free_bytes), int(total_bytes)


def _cuda_memory_metric(cuda: Any, name: str, device_index: int) -> int | None:
    metric = getattr(cuda, name, None)
    if not callable(metric):
        return None
    try:
        return int(metric(device_index))
    except TypeError:
        try:
            return int(metric())
        except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
            return None
    except BaseException:  # noqa: BLE001 - diagnostics should not fail the probe.
        return None


def _curobo_extension_cache_diagnostics() -> dict[str, Any]:
    if importlib.util.find_spec("torch") is None:
        return {"available": False, "extensions": {}}
    try:
        from torch.utils.cpp_extension import _get_build_directory

        extensions = {}
        for name in CUROBO_EXTENSION_NAMES:
            build_dir = Path(_get_build_directory(name, verbose=False))
            extensions[name] = _curobo_extension_cache_entry(name, build_dir)
        return {
            "available": True,
            "configured_dir": os.environ.get("TORCH_EXTENSIONS_DIR", ""),
            "extensions": extensions,
        }
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        return {
            "available": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "configured_dir": os.environ.get("TORCH_EXTENSIONS_DIR", ""),
            "extensions": {},
        }


def _curobo_extension_cache_entry(name: str, build_dir: Path) -> dict[str, Any]:
    files = []
    if build_dir.is_dir():
        for path in sorted(build_dir.iterdir(), key=lambda item: item.name):
            if not path.is_file():
                continue
            stat = path.stat()
            files.append(
                {
                    "name": path.name,
                    "size_bytes": stat.st_size,
                    "modified_time": round(stat.st_mtime, 3),
                }
            )
    return {
        "build_dir": str(build_dir),
        "exists": build_dir.is_dir(),
        "so_exists": (build_dir / f"{name}.so").is_file(),
        "lock_exists": (build_dir / "lock").exists(),
        "files": files,
    }


def _warp_compatibility_diagnostics() -> dict[str, Any]:
    if importlib.util.find_spec("warp") is None:
        return {"available": False, "adapter": dict(_WARP_COMPATIBILITY_ADAPTER)}
    try:
        import warp as wp

        return _warp_compatibility_from_module(wp, _WARP_COMPATIBILITY_ADAPTER)
    except BaseException as exc:  # noqa: BLE001 - diagnostics should not fail the probe.
        return {
            "available": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
            "adapter": dict(_WARP_COMPATIBILITY_ADAPTER),
        }


def _warp_compatibility_from_module(
    wp_module: Any, adapter: dict[str, Any] | None = None
) -> dict[str, Any]:
    return {
        "available": True,
        "version": getattr(wp_module, "__version__", None),
        "has_torch_attr": hasattr(wp_module, "torch"),
        "has_device_from_torch": hasattr(wp_module, "device_from_torch"),
        "has_from_torch": hasattr(wp_module, "from_torch"),
        "has_stream_from_torch": hasattr(wp_module, "stream_from_torch"),
        "adapter": dict(adapter or {}),
    }


def _apply_warp_torch_adapter() -> dict[str, Any]:
    try:
        import warp as wp
    except BaseException as exc:  # noqa: BLE001 - adapter should report failures.
        adapter = {
            "available": False,
            "applied": False,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        _WARP_COMPATIBILITY_ADAPTER.clear()
        _WARP_COMPATIBILITY_ADAPTER.update(adapter)
        return adapter
    adapter = _apply_warp_torch_adapter_to_module(wp)
    _WARP_COMPATIBILITY_ADAPTER.clear()
    _WARP_COMPATIBILITY_ADAPTER.update(adapter)
    return adapter


def _apply_warp_torch_adapter_to_module(wp_module: Any) -> dict[str, Any]:
    if hasattr(wp_module, "torch"):
        return {
            "available": True,
            "applied": False,
            "reason": "warp.torch already available",
        }
    if not hasattr(wp_module, "device_from_torch"):
        return {
            "available": True,
            "applied": False,
            "reason": "warp.device_from_torch unavailable",
        }
    setattr(
        wp_module,
        "torch",
        SimpleNamespace(device_from_torch=getattr(wp_module, "device_from_torch")),
    )
    return {
        "available": True,
        "applied": True,
        "provided": ["warp.torch.device_from_torch"],
    }


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
    }
    if args.probe_mode == "execute":
        payload.update(
            _execute_policy_probe(
                config,
                args.output_dir,
                args.steps,
                renderer_device_id=_renderer_device_id_for_probe(
                    probe_mode=args.probe_mode,
                    renderer_device_id=args.renderer_device_id,
                ),
                requested_cleanup_binding=_requested_cleanup_primitive_binding(args),
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
    curobo_memory_profile = _apply_rby1m_curobo_memory_profile(config, args)
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
    }
    if args.probe_mode == "execute":
        _emit_worker_event("rby1m_execute_probe_start", stage="rby1m_execute")
        payload.update(
            _execute_policy_probe(
                config,
                args.output_dir,
                args.steps,
                renderer_device_id=_renderer_device_id_for_probe(
                    probe_mode=args.probe_mode,
                    renderer_device_id=args.renderer_device_id,
                ),
                requested_cleanup_binding=_requested_cleanup_primitive_binding(args),
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
) -> dict[str, Any]:
    import numpy as np
    from molmo_spaces.utils.test_utils import run_task_for_steps_with_observations

    _emit_worker_event("execute_renderer_adapter_start", stage="execute_renderer_adapter")
    renderer_adapter = _apply_headless_renderer_adapter(renderer_device_id)
    _emit_worker_event(
        "execute_renderer_adapter_ready",
        stage="execute_renderer_adapter",
        renderer_adapter=renderer_adapter,
    )
    _emit_worker_event("execute_task_sampler_construct_start", stage="execute_task_sampler")
    task_sampler = config.task_sampler_config.task_sampler_class(config)
    cleanup_task_sampler_adapter = _apply_exact_cleanup_task_sampler_adapter(
        task_sampler,
        requested_cleanup_binding,
    )
    _emit_worker_event("execute_task_sampler_construct_done", stage="execute_task_sampler")
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
    _emit_worker_event("execute_warp_adapter_start", stage="execute_warp_adapter")
    warp_adapter = _apply_warp_torch_adapter()
    _emit_worker_event(
        "execute_warp_adapter_ready",
        stage="execute_warp_adapter",
        warp_adapter=warp_adapter,
    )
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
    initial_qpos, final_qpos, initial_obs, final_obs = run_task_for_steps_with_observations(
        task,
        policy,
        num_steps=steps,
        profiler=None,
    )
    _record_cuda_memory_snapshot("execute_policy_run_done")
    _emit_worker_event("execute_policy_run_done", stage="execute_policy_run", steps=steps)
    views_dir = output_dir / "planner_views"
    image_artifacts = {}
    initial = _write_first_camera_image(initial_obs, views_dir, "initial")
    final = _write_first_camera_image(final_obs, views_dir, "final")
    if initial:
        image_artifacts["initial"] = str(initial.relative_to(output_dir))
    if final:
        image_artifacts["final"] = str(final.relative_to(output_dir))
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
        "cleanup_task_sampler_adapter": cleanup_task_sampler_adapter,
        "sampled_task_binding": sampled_task_binding,
        "requested_cleanup_primitive_binding": requested_cleanup_binding,
        "cleanup_primitive_binding": cleanup_binding_result.get("cleanup_primitive_binding"),
        "cleanup_primitive_binding_blockers": cleanup_binding_result.get("blockers", []),
    }


def _configure_exact_cleanup_task(config: Any, args: argparse.Namespace) -> dict[str, Any]:
    requested = _requested_cleanup_primitive_binding(args)
    scene_xml = str(getattr(args, "cleanup_scene_xml", "") or "")
    planner_object_id = str(requested.get("planner_object_id") or "")
    planner_target_id = str(requested.get("planner_target_receptacle_id") or "")
    applied = False
    blockers = []
    if scene_xml:
        scene_path = Path(scene_xml)
        if scene_path.is_file():
            config.scene_dataset = str(scene_path)
            config.data_split = "val"
            config.task_sampler_config.house_inds = [0]
            config.task_sampler_config.samples_per_house = 1
            config.task_sampler_config.max_tasks = 1
            applied = True
        else:
            blockers.append(
                {
                    "code": "cleanup_scene_xml_missing",
                    "message": f"Requested cleanup scene XML does not exist: {scene_xml}",
                }
            )
    task_config = getattr(config, "task_config", None)
    if planner_object_id and task_config is not None:
        task_config.pickup_obj_name = planner_object_id
        if hasattr(config.task_sampler_config, "pickup_obj_name"):
            config.task_sampler_config.pickup_obj_name = planner_object_id
        applied = True
    if planner_target_id and task_config is not None:
        if hasattr(task_config, "place_receptacle_name"):
            task_config.place_receptacle_name = planner_target_id
        if hasattr(task_config, "place_target_name"):
            task_config.place_target_name = planner_target_id
        if hasattr(config.task_sampler_config, "place_target_name"):
            config.task_sampler_config.place_target_name = planner_target_id
        applied = True
    for attr in ("task_config_preset_exp", "task_config_preset_scn"):
        if hasattr(config, attr):
            setattr(config, attr, None)
    return {
        "schema": "planner_probe_exact_cleanup_task_config_v1",
        "applied": applied,
        "scene_xml": scene_xml,
        "planner_object_id": planner_object_id,
        "planner_target_receptacle_id": planner_target_id,
        "blockers": blockers,
        "evidence_note": (
            "Probe-local config override for sampling a planner task from the cleanup "
            "artifact scene with requested cleanup object/target aliases."
        ),
    }


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
    return {
        "schema": "planner_probe_exact_cleanup_task_sampler_adapter_v1",
        "applied": True,
        "task_sampler_class": type(task_sampler).__name__,
        "planner_target_receptacle_id": planner_target_id,
        "hooks": ["_get_place_target_candidates", "_prepare_place_target"],
        "evidence_note": (
            "Probe-local adapter makes the upstream pick-and-place sampler use the "
            "cleanup request's target object instead of an unrelated generated receptacle."
        ),
    }


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
            "tools": sorted(set(str(tool) for tool in tools)),
            "planner_object_id": requested_planner_object,
            "planner_target_receptacle_id": requested_planner_target,
            "sampled_task_binding": sampled,
            "evidence_note": "Requested cleanup primitive binding matched sampled planner task.",
        },
        "blockers": [],
    }


def _cleanup_tools_from_arg(value: str) -> list[str]:
    return sorted({item.strip() for item in value.split(",") if item.strip()})


def _renderer_device_id_for_probe(
    *,
    probe_mode: str,
    renderer_device_id: int,
) -> int | None:
    if probe_mode != "execute" or renderer_device_id < 0:
        return None
    return renderer_device_id


def _configure_headless_renderer_env(args: argparse.Namespace) -> None:
    renderer_device_id = _renderer_device_id_for_probe(
        probe_mode=args.probe_mode,
        renderer_device_id=args.renderer_device_id,
    )
    if renderer_device_id is None:
        return
    os.environ["MUJOCO_GL"] = "egl"
    os.environ["PYOPENGL_PLATFORM"] = "egl"
    os.environ["ROBOCLAWS_MOLMOSPACES_RENDERER_DEVICE_ID"] = str(renderer_device_id)


def _apply_headless_renderer_adapter(renderer_device_id: int | None) -> dict[str, Any]:
    if renderer_device_id is None:
        return {"enabled": False}
    targets = []
    already_patched = []
    for module_name in (
        "molmo_spaces.env.env",
        "molmo_spaces.utils.scene_maps",
    ):
        module = importlib.import_module(module_name)
        if not hasattr(module, "MjOpenGLRenderer"):
            continue
        targets.append(f"{module_name}.MjOpenGLRenderer")
        module_already_patched = bool(
            getattr(module.MjOpenGLRenderer, "_roboclaws_renderer_adapter", False)
        )
        already_patched.append(module_already_patched)
        if not module_already_patched:
            _patch_renderer_constructor(module, renderer_device_id)
    return {
        "enabled": True,
        "device_id": renderer_device_id,
        "targets": targets,
        "already_patched": all(already_patched) if already_patched else False,
    }


def _patch_renderer_constructor(env_module: Any, renderer_device_id: int) -> None:
    renderer_cls = env_module.MjOpenGLRenderer

    def renderer_with_device(*args: Any, **kwargs: Any) -> Any:
        if kwargs.get("device_id") is None:
            kwargs["device_id"] = renderer_device_id
        return renderer_cls(*args, **kwargs)

    renderer_with_device._roboclaws_renderer_adapter = True  # type: ignore[attr-defined]
    renderer_with_device._roboclaws_renderer_device_id = renderer_device_id  # type: ignore[attr-defined]
    env_module.MjOpenGLRenderer = renderer_with_device


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
    if worker_payload.get("runtime_diagnostics"):
        evidence["runtime_diagnostics"] = worker_payload["runtime_diagnostics"]
    if worker_payload.get("cuda_memory_snapshots"):
        evidence["cuda_memory_snapshots"] = worker_payload["cuda_memory_snapshots"]
    if worker_payload.get("curobo_memory_profile"):
        evidence["curobo_memory_profile"] = worker_payload["curobo_memory_profile"]
    if worker_payload.get("cleanup_task_config"):
        evidence["cleanup_task_config"] = worker_payload["cleanup_task_config"]
    if worker_payload.get("cleanup_task_sampler_adapter"):
        evidence["cleanup_task_sampler_adapter"] = worker_payload["cleanup_task_sampler_adapter"]
    if worker_payload.get("sampled_task_binding"):
        evidence["sampled_task_binding"] = worker_payload["sampled_task_binding"]
    if worker_payload.get("requested_cleanup_primitive_binding"):
        evidence["requested_cleanup_primitive_binding"] = worker_payload[
            "requested_cleanup_primitive_binding"
        ]
    if worker_payload.get("cleanup_primitive_binding"):
        evidence["cleanup_primitive_binding"] = worker_payload["cleanup_primitive_binding"]
    if worker_payload.get("cleanup_primitive_binding_blockers"):
        evidence["cleanup_primitive_binding_blockers"] = worker_payload[
            "cleanup_primitive_binding_blockers"
        ]
    worker_stage_events = list(worker_payload.get("worker_stage_events") or [])
    if worker_stage_events:
        evidence["worker_stage_events"] = worker_stage_events
        evidence["last_worker_stage"] = worker_payload.get("last_worker_stage")
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
    run_result["rby1m_curobo_gate"] = rby1m_curobo_gate_from_planner_probe(run_result)
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


def _worker_payload_from_stdout(stdout: str) -> dict[str, Any] | None:
    json_objects = _parse_stdout_json_objects(stdout)
    if not json_objects:
        return None
    final_payload = next((item for item in reversed(json_objects) if "ok" in item), None)
    payload: dict[str, Any] = dict(final_payload or {})
    worker_events = [item for item in json_objects if item.get("event")]
    runtime_diagnostics = next(
        (
            item.get("runtime_diagnostics")
            for item in reversed(worker_events)
            if item.get("event") == "runtime_diagnostics"
        ),
        None,
    )
    if runtime_diagnostics and "runtime_diagnostics" not in payload:
        payload["runtime_diagnostics"] = runtime_diagnostics
    if worker_events:
        payload["worker_stage_events"] = worker_events
        last_stage = str(worker_events[-1].get("stage") or worker_events[-1].get("event") or "")
        payload["last_worker_stage"] = last_stage
        memory_snapshots = [
            item["cuda_memory"]
            for item in worker_events
            if item.get("event") == "cuda_memory_snapshot" and item.get("cuda_memory")
        ]
        if memory_snapshots and "cuda_memory_snapshots" not in payload:
            payload["cuda_memory_snapshots"] = memory_snapshots
    return payload or None


def _parse_stdout_json_objects(stdout: str) -> list[dict[str, Any]]:
    objects = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            objects.append(payload)
    return objects


def _process_output_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


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

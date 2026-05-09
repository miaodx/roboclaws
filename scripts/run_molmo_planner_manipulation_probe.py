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
from types import SimpleNamespace
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
    ]
    if torch_extensions_dir is not None:
        command.extend(["--torch-extensions-dir", str(torch_extensions_dir)])
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


def _probe_franka(args: argparse.Namespace) -> dict[str, Any]:
    _emit_worker_event("franka_config_import_start", stage="franka_config_import")
    from mlspaces_tests.data_generation.config import FrankaPickAndPlaceDroidTestConfig

    _emit_worker_event("franka_config_import_done", stage="franka_config_import")
    _emit_worker_event("franka_config_construct_start", stage="franka_config_construct")
    config = FrankaPickAndPlaceDroidTestConfig()
    config.use_passive_viewer = False
    config.profile = False
    config.use_wandb = False
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
    _emit_worker_event("execute_task_sampler_construct_done", stage="execute_task_sampler")
    _emit_worker_event("execute_task_sampler_reset_start", stage="execute_task_sampler_reset")
    task_sampler.reset()
    _emit_worker_event("execute_task_sampler_reset_done", stage="execute_task_sampler_reset")
    _emit_worker_event("execute_task_sample_start", stage="execute_task_sample")
    task = task_sampler.sample_task()
    _emit_worker_event("execute_task_sample_done", stage="execute_task_sample")
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
    }


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


def _prepend_pythonpath(path: Path, existing: str | None) -> str:
    value = str(path)
    if existing:
        return value + os.pathsep + existing
    return value


if __name__ == "__main__":
    main()

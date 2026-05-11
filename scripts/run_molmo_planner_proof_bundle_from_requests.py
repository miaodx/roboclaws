#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[1]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.molmo_cleanup.planner_proof_requests import (  # noqa: E402
    PLANNER_PROOF_REQUESTS_SCHEMA,
    build_cleanup_rerun_command,
    build_probe_commands,
    proof_bundle_run_manifest,
)
from roboclaws.molmo_cleanup.report import render_planner_proof_bundle_runner_report  # noqa: E402
from roboclaws.molmo_cleanup.subprocess_backend import DEFAULT_MOLMOSPACES_PYTHON  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROBE_SCRIPT = REPO_ROOT / "scripts" / "run_molmo_planner_manipulation_probe.py"
DEFAULT_CLEANUP_SCRIPT = REPO_ROOT / "examples" / "molmospaces_realworld_cleanup.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate or run bound planner proof bundle commands from a cleanup artifact."
    )
    parser.add_argument("cleanup_run_result", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runner-python", type=Path, default=Path(sys.executable))
    parser.add_argument("--probe-script", type=Path, default=DEFAULT_PROBE_SCRIPT)
    parser.add_argument("--cleanup-script", type=Path, default=DEFAULT_CLEANUP_SCRIPT)
    parser.add_argument("--molmospaces-python", type=Path, default=DEFAULT_MOLMOSPACES_PYTHON)
    parser.add_argument("--molmospaces-root", type=Path)
    parser.add_argument("--embodiment", choices=("franka", "rby1m"), default="rby1m")
    parser.add_argument("--probe-mode", choices=("config_import", "execute"), default="execute")
    parser.add_argument("--steps", type=int, default=2)
    parser.add_argument("--timeout-s", type=float, default=600.0)
    parser.add_argument("--renderer-device-id", type=int, default=0)
    parser.add_argument("--torch-extensions-dir", type=Path)
    parser.add_argument(
        "--rby1m-curobo-memory-profile",
        choices=("none", "low"),
        default="low",
    )
    parser.add_argument("--execute-probes", action="store_true")
    parser.add_argument("--rerun-cleanup", action="store_true")
    parser.add_argument("--cleanup-output-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = run_from_cleanup_result(
        cleanup_run_result=args.cleanup_run_result,
        output_dir=args.output_dir,
        runner_python=args.runner_python,
        probe_script=args.probe_script,
        cleanup_script=args.cleanup_script,
        molmospaces_python=args.molmospaces_python,
        molmospaces_root=args.molmospaces_root,
        embodiment=args.embodiment,
        probe_mode=args.probe_mode,
        steps=args.steps,
        timeout_s=args.timeout_s,
        renderer_device_id=args.renderer_device_id,
        torch_extensions_dir=args.torch_extensions_dir,
        rby1m_curobo_memory_profile=args.rby1m_curobo_memory_profile,
        execute_probes=args.execute_probes,
        rerun_cleanup=args.rerun_cleanup,
        cleanup_output_dir=args.cleanup_output_dir,
    )
    print(
        json.dumps(
            {
                "manifest": str(result["manifest_path"]),
                "report": str(result["report_path"]),
                "status": result["status"],
            }
        )
    )


def run_from_cleanup_result(
    *,
    cleanup_run_result: Path,
    output_dir: Path,
    runner_python: Path,
    probe_script: Path,
    cleanup_script: Path,
    molmospaces_python: Path | None,
    molmospaces_root: Path | None,
    embodiment: str,
    probe_mode: str,
    steps: int,
    timeout_s: float,
    renderer_device_id: int,
    torch_extensions_dir: Path | None,
    rby1m_curobo_memory_profile: str,
    execute_probes: bool = False,
    rerun_cleanup: bool = False,
    cleanup_output_dir: Path | None = None,
) -> dict[str, Any]:
    cleanup_run_result = cleanup_run_result.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    source_run = json.loads(cleanup_run_result.read_text(encoding="utf-8"))
    requests = _load_proof_requests(source_run, cleanup_run_result.parent)
    commands = build_probe_commands(
        manifest=requests,
        output_dir=output_dir,
        runner_python=runner_python,
        probe_script=probe_script,
        molmospaces_python=molmospaces_python,
        molmospaces_root=molmospaces_root,
        embodiment=embodiment,
        probe_mode=probe_mode,
        steps=steps,
        timeout_s=timeout_s,
        renderer_device_id=renderer_device_id,
        torch_extensions_dir=torch_extensions_dir,
        rby1m_curobo_memory_profile=rby1m_curobo_memory_profile,
    )
    proof_results: list[Path] = []
    status = "dry_run"
    if execute_probes:
        status = "probes_executed"
        for item in commands:
            _run_command(item["command"])
            proof_results.append(Path(item["run_result"]))
    cleanup_command: list[str] = []
    cleanup_rerun: dict[str, Any] = {}
    if rerun_cleanup:
        if not execute_probes:
            raise ValueError("--rerun-cleanup requires --execute-probes")
        cleanup_output = cleanup_output_dir or output_dir / "cleanup_with_planner_proof_bundle"
        cleanup_command = build_cleanup_rerun_command(
            runner_python=runner_python,
            cleanup_script=cleanup_script,
            cleanup_output_dir=cleanup_output,
            source_run_result=source_run,
            proof_run_results=proof_results,
        )
        _run_command(cleanup_command)
        status = "cleanup_rerun"
        cleanup_rerun = {
            "output_dir": str(cleanup_output),
            "run_result": str(cleanup_output / "run_result.json"),
            "report": str(cleanup_output / "report.html"),
        }
    manifest = proof_bundle_run_manifest(
        cleanup_run_result=cleanup_run_result,
        output_dir=output_dir,
        proof_requests=requests,
        commands=commands,
        cleanup_command=cleanup_command,
        cleanup_rerun=cleanup_rerun,
    )
    manifest["status"] = status
    report_path = output_dir / "report.html"
    manifest["report"] = str(report_path)
    manifest_path = output_dir / "proof_bundle_run_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path = render_planner_proof_bundle_runner_report(
        output_dir=output_dir,
        manifest=manifest,
    )
    return {
        "status": status,
        "manifest_path": manifest_path,
        "report_path": report_path,
        "manifest": manifest,
    }


def _load_proof_requests(source_run: dict[str, Any], base: Path) -> dict[str, Any]:
    inline = source_run.get("planner_proof_requests")
    if isinstance(inline, dict) and inline.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA:
        return inline
    artifacts = source_run.get("artifacts") or {}
    request_path = _resolve_path(base, str(artifacts.get("planner_proof_requests") or ""))
    if request_path.is_file():
        data = json.loads(request_path.read_text(encoding="utf-8"))
        assert data.get("schema") == PLANNER_PROOF_REQUESTS_SCHEMA, data
        return data
    raise ValueError("cleanup run_result does not include planner proof requests")


def _run_command(command: list[str]) -> None:
    subprocess.run(command, check=True, cwd=REPO_ROOT)


def _resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    if path.is_absolute() or path.exists():
        return path
    repo_path = REPO_ROOT / path
    if repo_path.exists():
        return repo_path
    return base / path


if __name__ == "__main__":
    main()

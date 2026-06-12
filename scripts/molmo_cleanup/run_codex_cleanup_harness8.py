#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import html
import json
import os
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.core.rerun import shell_join  # noqa: E402
from roboclaws.household.apple2apple_test_grid import (  # noqa: E402
    DEFAULT_MAP_BUNDLE,
    RUNTIME_MAP_PRIOR_PLACEHOLDER,
)
from roboclaws.household.realworld_contract import DEFAULT_REALWORLD_TASK  # noqa: E402
from roboclaws.household.visual_grounding import (  # noqa: E402
    DEFAULT_VISUAL_GROUNDING_BASE_URL,
    VISUAL_GROUNDING_REQUEST_SCHEMA,
    VISUAL_GROUNDING_RESPONSE_SCHEMA,
)
from scripts.visual_grounding.serve_fake_visual_grounding import (  # noqa: E402
    ENDPOINT as VISUAL_GROUNDING_ENDPOINT,
)

HARNESS_SCHEMA = "codex_cleanup_harness8_v1"
ROW_SCHEMA = "codex_cleanup_harness8_row_v1"
DIRECT_MAP_MODE = "direct"
PRIOR_MAP_MODE = "dino-prior"
VISUAL_GROUNDING_INFRA_FAILURE_REASONS = {
    "connection_error",
    "timeout",
    "service_unavailable",
}
DINO_VISUAL_GROUNDING_PIPELINE_ID = "grounding-dino"
DINO_SIDECAR_LOCK_PATH = Path("output/molmo/.visual-grounding-dino.lock")
DINO_SIDECAR_LOG_NAME = "visual-grounding-dino-sidecar.log"
DEFAULT_CLEANUP_MCP_PORT = 18788
DINO_SIDECAR_PROBE_IMAGE_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADElEQVR42mP8z8AARQAFAAH/"
    "e+m+7wAAAABJRU5ErkJggg=="
)
DEFAULT_DINO_SIDECAR_ENV = {
    "VISUAL_GROUNDING_DEVICE": "auto",
    "VISUAL_GROUNDING_TORCH_DTYPE": "auto",
    "VISUAL_GROUNDING_DINO_MODEL_ID": "IDEA-Research/grounding-dino-base",
    "VISUAL_GROUNDING_DINO_BOX_THRESHOLD": "0.25",
    "VISUAL_GROUNDING_DINO_TEXT_THRESHOLD": "0.20",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build or execute the eight-case Codex household-cleanup harness: "
            "four evidence lanes without a Runtime Metric Map prior and the same "
            "four lanes using a DINO semantic-map-build prior."
        )
    )
    parser.add_argument("--output-dir", type=Path, default=Path("output/molmo/codex-harness8"))
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--generated-mess-count", type=int, default=10)
    parser.add_argument("--task", default=DEFAULT_REALWORLD_TASK)
    parser.add_argument("--map-bundle", default=DEFAULT_MAP_BUNDLE)
    parser.add_argument("--runtime-map-prior", default="")
    parser.add_argument("--visual-grounding-timeout-s", default="auto")
    parser.add_argument("--parallelism", type=int, default=1)
    parser.add_argument("--base-port", type=int, default=DEFAULT_CLEANUP_MCP_PORT)
    parser.add_argument("--just-bin", default="just")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--row", action="append", default=[])
    parser.add_argument("--live-wait-timeout-s", type=float, default=7200.0)
    parser.add_argument("--live-wait-poll-s", type=float, default=10.0)
    parser.add_argument(
        "--provider-retry-attempts",
        type=int,
        default=1,
        help=(
            "Additional whole-row retries for explicit retryable provider-transient "
            "failures. Ordinary cleanup and launcher failures are not retried."
        ),
    )
    parser.add_argument(
        "--provider-retry-sleep-s",
        type=float,
        default=60.0,
    )
    parser.add_argument(
        "--dino-sidecar-lifecycle",
        choices=("auto", "reuse-only", "off"),
        default="auto",
        help=(
            "Lifecycle policy for Grounding DINO rows. auto reuses a healthy "
            "real sidecar or starts one and stops it after the harness; "
            "reuse-only requires a healthy pre-existing sidecar; off restores "
            "the old unmanaged behavior."
        ),
    )
    parser.add_argument("--dino-sidecar-startup-timeout-s", type=float, default=180.0)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    harness = build_harness(
        output_dir=args.output_dir,
        seed=args.seed,
        generated_mess_count=args.generated_mess_count,
        task=args.task,
        map_bundle=args.map_bundle,
        runtime_map_prior=args.runtime_map_prior,
        visual_grounding_timeout_s=args.visual_grounding_timeout_s,
    )
    _configure_harness_parallelism(
        harness,
        parallelism=args.parallelism,
        base_port=args.base_port,
    )
    if args.execute:
        if args.row:
            _merge_existing_state(harness, args.output_dir, selected_row_ids=set(args.row))
        if args.runtime_map_prior:
            _mark_explicit_runtime_map_prior(harness, args.runtime_map_prior)
        status = _execute_harness(harness, args)
    else:
        _mark_dry_run(harness)
        status = 0
    _write_outputs(harness, args.output_dir)
    print(f"codex harness8 manifest: {args.output_dir / 'codex_cleanup_harness8.json'}")
    print(f"codex harness8 report: {args.output_dir / 'codex_cleanup_harness8.html'}")
    return status


def build_harness(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    runtime_map_prior: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    prior_value = runtime_map_prior or RUNTIME_MAP_PRIOR_PLACEHOLDER
    setup_rows = [
        _semantic_map_prior_row(
            output_dir=output_dir,
            seed=seed,
            generated_mess_count=generated_mess_count,
            task=task,
            map_bundle=map_bundle,
            visual_grounding_timeout_s=visual_grounding_timeout_s,
        )
    ]
    rows = []
    for map_mode in (DIRECT_MAP_MODE, PRIOR_MAP_MODE):
        for lane in _harness_lanes():
            rows.append(
                _cleanup_row(
                    output_dir=output_dir,
                    seed=seed,
                    generated_mess_count=generated_mess_count,
                    task=task,
                    map_bundle=map_bundle,
                    map_mode=map_mode,
                    lane=lane,
                    runtime_map_prior=prior_value if map_mode == PRIOR_MAP_MODE else "",
                    visual_grounding_timeout_s=visual_grounding_timeout_s,
                )
            )
    return {
        "schema": HARNESS_SCHEMA,
        "generated_at": _utc_timestamp(),
        "name": "codex_cleanup_harness8",
        "description": (
            "Eight-case live Codex cleanup harness for source/skill regression "
            "checks: two world-label lanes, Grounding DINO camera labels, and "
            "RAW_FPV, each run directly and with a DINO semantic-map prior."
        ),
        "seed": seed,
        "generated_mess_count": generated_mess_count,
        "task": task,
        "map_bundle": map_bundle,
        "runtime_map_prior": runtime_map_prior,
        "runtime_map_prior_placeholder": RUNTIME_MAP_PRIOR_PLACEHOLDER,
        "parallelism": 1,
        "base_port": DEFAULT_CLEANUP_MCP_PORT,
        "setup_rows": setup_rows,
        "rows": rows,
    }


def _configure_harness_parallelism(
    harness: dict[str, Any],
    *,
    parallelism: int,
    base_port: int,
) -> None:
    parallelism = max(int(parallelism), 1)
    base_port = int(base_port)
    harness["parallelism"] = parallelism
    harness["base_port"] = base_port
    for row in [*(harness.get("setup_rows") or []), *(harness.get("rows") or [])]:
        if _is_setup_row(row):
            row["harness_parallelism"] = 1
            row["parallel_group"] = "setup"
            _set_row_port(row, base_port)
            row["rerun_command"] = row_rerun_command(row)
            continue
        row["harness_parallelism"] = parallelism
        row["parallel_group"] = "cleanup"
        if parallelism > 1:
            row_env = row.get("env") if isinstance(row.get("env"), dict) else {}
            row["env"] = {
                **row_env,
                "ROBOCLAWS_MOLMO_ALLOW_BATCH_VISUAL_BACKENDS": "1",
                "ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS": str(parallelism),
            }
        _set_row_port(row, _planned_row_port(row, base_port=base_port, parallelism=parallelism))
        row["rerun_command"] = row_rerun_command(row)


def _planned_row_port(row: dict[str, Any], *, base_port: int, parallelism: int) -> int:
    if parallelism <= 1:
        return base_port
    index = _cleanup_row_index(row)
    return base_port + index * 2


def _cleanup_row_index(row: dict[str, Any]) -> int:
    row_id = str(row.get("row_id") or "")
    all_ids = [
        f"{DIRECT_MAP_MODE}-world-oracle-labels",
        f"{DIRECT_MAP_MODE}-world-public-labels",
        f"{DIRECT_MAP_MODE}-camera-grounded-labels-grounding-dino",
        f"{DIRECT_MAP_MODE}-camera-raw-fpv",
        f"{PRIOR_MAP_MODE}-world-oracle-labels",
        f"{PRIOR_MAP_MODE}-world-public-labels",
        f"{PRIOR_MAP_MODE}-camera-grounded-labels-grounding-dino",
        f"{PRIOR_MAP_MODE}-camera-raw-fpv",
    ]
    try:
        return all_ids.index(row_id)
    except ValueError:
        return 0


def _set_row_port(row: dict[str, Any], port: int) -> None:
    command = [str(item) for item in row.get("command") or []]
    command = [item for item in command if not item.startswith("port=")]
    command.append(f"port={int(port)}")
    row["command"] = command
    row["assigned_port"] = int(port)


def _harness_lanes() -> tuple[dict[str, str], ...]:
    return (
        {
            "lane_id": "world-oracle-labels",
            "label": "World oracle labels",
            "profile": "world-oracle-labels",
            "camera_labeler": "",
        },
        {
            "lane_id": "world-public-labels",
            "label": "World public labels",
            "profile": "world-public-labels",
            "camera_labeler": "",
        },
        {
            "lane_id": "camera-grounded-labels-grounding-dino",
            "label": "Grounding DINO camera labels",
            "profile": "camera-grounded-labels",
            "camera_labeler": "grounding-dino",
        },
        {
            "lane_id": "camera-raw-fpv",
            "label": "RAW_FPV",
            "profile": "camera-raw-fpv",
            "camera_labeler": "",
        },
    )


def _semantic_map_prior_row(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    row_output_dir = output_dir / "_semantic-map-prior-dino"
    command = [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=map-build",
        "agent_engine=direct-runner",
        "evidence_lane=camera-grounded-labels",
        "scenario_setup=baseline",
        f"seed={seed}",
        f"output_dir={row_output_dir}",
        f"task={task}",
        f"map_bundle={map_bundle}",
        "camera_labeler=grounding-dino",
    ]
    if visual_grounding_timeout_s != "auto":
        command.append(f"visual_grounding_timeout_s={visual_grounding_timeout_s}")
    return _row_payload(
        row_id="setup-semantic-map-prior-dino",
        label="Build DINO semantic-map prior",
        grid_role="setup",
        map_mode="setup",
        lane_id="camera-grounded-labels-grounding-dino",
        command=command,
        output_dir=row_output_dir,
        requires_runtime_map_prior=False,
        expected_artifacts=["runtime_metric_map.json", "report.html"],
    )


def _cleanup_row(
    *,
    output_dir: Path,
    seed: int,
    generated_mess_count: int,
    task: str,
    map_bundle: str,
    map_mode: str,
    lane: dict[str, str],
    runtime_map_prior: str,
    visual_grounding_timeout_s: str,
) -> dict[str, Any]:
    row_id = f"{map_mode}-{lane['lane_id']}"
    row_output_dir = output_dir / row_id
    command = [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=codex-cli",
        "provider_profile=codex-env",
        f"evidence_lane={lane['profile']}",
        f"seed={seed}",
        "scenario_setup=relocate-cleanup-related-objects",
        f"relocation_count={generated_mess_count}",
        f"output_dir={row_output_dir}",
        f"task={task}",
        f"map_bundle={map_bundle}",
    ]
    if lane.get("camera_labeler"):
        command.append(f"camera_labeler={lane['camera_labeler']}")
    if visual_grounding_timeout_s != "auto":
        command.append(f"visual_grounding_timeout_s={visual_grounding_timeout_s}")
    if runtime_map_prior:
        command.append(f"runtime_map_prior={runtime_map_prior}")
    return _row_payload(
        row_id=row_id,
        label=f"{map_mode} Codex {lane['label']}",
        grid_role="cleanup",
        map_mode=map_mode,
        lane_id=lane["lane_id"],
        command=command,
        output_dir=row_output_dir,
        requires_runtime_map_prior=bool(runtime_map_prior),
        expected_artifacts=["run_result.json", "report.html", "runtime_metric_map.json"],
    )


def _row_payload(
    *,
    row_id: str,
    label: str,
    grid_role: str,
    map_mode: str,
    lane_id: str,
    command: list[str],
    output_dir: Path,
    requires_runtime_map_prior: bool,
    expected_artifacts: list[str],
) -> dict[str, Any]:
    row = {
        "schema": ROW_SCHEMA,
        "row_id": row_id,
        "label": label,
        "grid_role": grid_role,
        "axes": {
            "agent_route": "codex",
            "map_mode": map_mode,
            "evidence_lane": lane_id,
        },
        "command": [str(item) for item in command],
        "env": {},
        "required_env": ["XM_LLM_API_KEY|CODEX_API_KEY+CODEX_BASE_URL"]
        if grid_role == "cleanup"
        else [],
        "output_dir": str(output_dir),
        "requires_runtime_map_prior": requires_runtime_map_prior,
        "expected_artifacts": expected_artifacts,
        "status": "pending",
        "reason": "",
        "run_dir": "",
        "report_path": "",
        "run_result_path": "",
        "metrics": {},
    }
    row["rerun_command"] = row_rerun_command(row)
    return row


def _execute_harness(harness: dict[str, Any], args: argparse.Namespace) -> int:
    selected_rows = _selected_rows(harness, filters=set(args.row))
    if not selected_rows:
        raise SystemExit("no cleanup rows selected")

    selected_ids = {str(row.get("row_id") or "") for row in selected_rows}
    for row in harness.get("rows") or []:
        if str(row.get("row_id") or "") not in selected_ids and not _has_existing_row_evidence(row):
            row["status"] = "not_selected"
            row["reason"] = "row was not selected for this execution"
            row["updated_at"] = _utc_timestamp()

    dino_rows = _selected_rows_requiring_dino_sidecar(
        harness,
        selected_rows,
        explicit_runtime_map_prior=str(args.runtime_map_prior or ""),
    )
    with _dino_sidecar_for_harness(harness, args, dino_rows) as sidecar:
        if sidecar.blocking_reason:
            _mark_dino_dependent_rows_blocked(dino_rows, sidecar.blocking_reason)
            return 1

        prior_path = args.runtime_map_prior
        if any(row.get("requires_runtime_map_prior") for row in selected_rows) and not prior_path:
            prior_path = _execute_prior_build(harness, args)
            harness["runtime_map_prior"] = prior_path
            if not prior_path:
                _mark_prior_dependent_rows_blocked(selected_rows, harness)
                return 1
            _replace_runtime_map_prior(harness, prior_path)

        failure_count = _execute_cleanup_rows(selected_rows, args)
        return 1 if failure_count else 0


def _execute_cleanup_rows(rows: list[dict[str, Any]], args: argparse.Namespace) -> int:
    parallelism = max(int(getattr(args, "parallelism", 1) or 1), 1)
    if parallelism == 1:
        failure_count = 0
        for row in rows:
            status = _execute_row_with_retries(row, args)
            if status != 0:
                failure_count += 1
                if not args.continue_on_error:
                    break
        return failure_count

    failure_count = 0
    pending = list(rows)
    with ThreadPoolExecutor(max_workers=parallelism) as executor:
        futures = {}
        while pending and (args.continue_on_error or failure_count == 0):
            while pending and len(futures) < parallelism:
                row = pending.pop(0)
                futures[executor.submit(_execute_row_with_retries, row, args)] = row
            if not futures:
                break
            done_future = next(as_completed(futures))
            row = futures.pop(done_future)
            status = done_future.result()
            if status != 0:
                failure_count += 1
                if not args.continue_on_error:
                    for future in as_completed(futures):
                        if future.result() != 0:
                            failure_count += 1
                    futures.clear()
                    for remaining in pending:
                        remaining["status"] = "not_started"
                        remaining["reason"] = (
                            f"not started because {row.get('row_id')} failed and "
                            "continue_on_error is false"
                        )
                        remaining["updated_at"] = _utc_timestamp()
                    break
        for future in as_completed(futures):
            if future.result() != 0:
                failure_count += 1
    return failure_count


def _execute_prior_build(harness: dict[str, Any], args: argparse.Namespace) -> str:
    setup_rows = list(harness.get("setup_rows") or [])
    if not setup_rows:
        raise RuntimeError("prior rows require a runtime-map prior but no setup row exists")
    row = setup_rows[0]
    status = _execute_row_with_retries(row, args)
    prior = _latest_runtime_map(Path(row["output_dir"]), seed=args.seed)
    if prior is None:
        if str(row.get("status") or "") == "provider_transient_failed":
            harness["setup_status"] = "provider_transient_failed"
            harness["behavior_status"] = "infra_failure"
            harness["reason"] = (
                row.get("reason") or "semantic-map prior build hit a provider transient failure"
            )
            return ""
        if status != 0:
            raise RuntimeError("semantic-map prior build failed")
        raise RuntimeError("semantic-map prior build produced no runtime_metric_map.json")
    if status != 0:
        row["status"] = "artifact_success"
        row["reason"] = (
            f"runtime_metric_map.json was produced; setup command exited with status {status}"
        )
    row["runtime_map_prior"] = str(prior)
    return str(prior)


def _mark_prior_dependent_rows_blocked(
    rows: list[dict[str, Any]],
    harness: dict[str, Any],
) -> None:
    reason = str(
        harness.get("reason")
        or "runtime_map_prior unavailable because semantic-map prior setup failed"
    )
    for row in rows:
        if not row.get("requires_runtime_map_prior"):
            continue
        row["status"] = "blocked"
        row["behavior_status"] = "infra_failure"
        row["reason"] = reason
        row["updated_at"] = _utc_timestamp()


class _DinoSidecarForHarness:
    def __init__(
        self,
        harness: dict[str, Any],
        args: argparse.Namespace,
        rows: list[dict[str, Any]],
    ) -> None:
        self.harness = harness
        self.args = args
        self.rows = rows
        self.blocking_reason = ""
        self.process: subprocess.Popen[bytes] | None = None
        self.lock_file = None
        self.log_path: Path | None = None
        self.metadata: dict[str, Any] = {
            "schema": "codex_cleanup_harness8_dino_sidecar_lifecycle_v1",
            "required": bool(rows),
            "policy": str(getattr(args, "dino_sidecar_lifecycle", "auto")),
            "base_url": _visual_grounding_base_url(),
            "row_ids": [str(row.get("row_id") or "") for row in rows],
            "status": "pending" if rows else "not_required",
            "owner": "none",
            "started_by_harness": False,
        }

    def __enter__(self) -> _DinoSidecarForHarness:
        self.harness["dino_sidecar"] = self.metadata
        if not self.rows:
            return self

        policy = str(getattr(self.args, "dino_sidecar_lifecycle", "auto") or "auto")
        if policy == "off":
            self.metadata["status"] = "unmanaged"
            self.metadata["reason"] = "dino sidecar lifecycle management was disabled"
            return self

        if not self._acquire_lock():
            return self

        base_url = str(self.metadata["base_url"])
        probe = _probe_dino_sidecar(base_url)
        self.metadata["initial_probe"] = probe
        if probe.get("healthy"):
            self.metadata["status"] = "reused"
            self.metadata["owner"] = "external"
            self.metadata["ready_at"] = _utc_timestamp()
            return self

        if policy == "reuse-only":
            self._block(
                "Grounding DINO sidecar lifecycle is reuse-only, but no healthy real sidecar "
                f"was reachable at {base_url}: {probe.get('reason') or 'not ready'}"
            )
            return self

        try:
            host, port = _visual_grounding_host_port(base_url)
        except RuntimeError as exc:
            self._block(str(exc))
            return self
        if _tcp_accepting(host, port):
            self._block(
                f"TCP port {host}:{port} is already in use, but it is not a healthy real "
                f"Grounding DINO sidecar: {probe.get('reason') or 'not ready'}"
            )
            return self

        self._start_owned_sidecar(host=host, port=port)
        return self

    def __exit__(self, _exc_type: object, _exc: object, _tb: object) -> None:
        self._stop_owned_sidecar()
        self._release_lock()

    def _acquire_lock(self) -> bool:
        lock_path = REPO_ROOT / DINO_SIDECAR_LOCK_PATH
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            lock_file.seek(0)
            active = lock_file.read().strip()
            lock_file.close()
            detail = f": {active}" if active else ""
            self._block(
                f"another Codex harness owns the Grounding DINO sidecar lock {lock_path}{detail}"
            )
            return False
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "output_dir": str(_harness_output_dir(self.args, self.rows)),
                    "base_url": self.metadata["base_url"],
                    "started_at": _utc_timestamp(),
                },
                sort_keys=True,
            )
            + "\n"
        )
        lock_file.flush()
        self.lock_file = lock_file
        self.metadata["lock_path"] = str(lock_path)
        return True

    def _start_owned_sidecar(self, *, host: str, port: int) -> None:
        python_bin = _dino_sidecar_python_bin()
        if not python_bin:
            self._block(
                "Grounding DINO sidecar was not reachable and no sidecar Python runtime "
                "was found. Set ROBOCLAWS_VISUAL_GROUNDING_PYTHON or create "
                ".venv-visual-grounding/."
            )
            return

        sidecar_dir = _harness_output_dir(self.args, self.rows) / "_sidecars"
        sidecar_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = sidecar_dir / DINO_SIDECAR_LOG_NAME
        command = [
            str(python_bin),
            "scripts/visual_grounding/serve_visual_grounding_service.py",
            "--host",
            host,
            "--port",
            str(port),
            "--pipeline",
            "real-router",
            "--adapter-mode",
            "real",
        ]
        env = os.environ.copy()
        for key, value in DEFAULT_DINO_SIDECAR_ENV.items():
            env.setdefault(key, value)
        with self.log_path.open("ab") as log_file:
            self.process = subprocess.Popen(
                command,
                cwd=REPO_ROOT,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT,
            )
        self.metadata.update(
            {
                "status": "starting",
                "owner": "harness",
                "started_by_harness": True,
                "pid": self.process.pid,
                "log_path": str(self.log_path),
                "command": command,
                "started_at": _utc_timestamp(),
            }
        )

        probe = _wait_for_dino_sidecar_ready(
            base_url=str(self.metadata["base_url"]),
            process=self.process,
            timeout_s=float(getattr(self.args, "dino_sidecar_startup_timeout_s", 180.0)),
        )
        self.metadata["ready_probe"] = probe
        if probe.get("healthy"):
            self.metadata["status"] = "started"
            self.metadata["ready_at"] = _utc_timestamp()
            return

        self._block(
            "Grounding DINO sidecar was started by the harness but did not become "
            f"ready: {probe.get('reason') or 'not ready'}"
        )

    def _stop_owned_sidecar(self) -> None:
        process = self.process
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        self.metadata["stopped_at"] = _utc_timestamp()
        self.metadata["stop_exit_status"] = process.returncode
        if self.metadata.get("status") in {"started", "starting"}:
            self.metadata["status"] = "stopped"

    def _release_lock(self) -> None:
        if self.lock_file is None:
            return
        try:
            fcntl.flock(self.lock_file.fileno(), fcntl.LOCK_UN)
        finally:
            self.lock_file.close()
            self.lock_file = None

    def _block(self, reason: str) -> None:
        self.blocking_reason = reason
        self.metadata["status"] = "infra_failed"
        self.metadata["owner"] = "none"
        self.metadata["reason"] = reason
        self.metadata["updated_at"] = _utc_timestamp()


def _dino_sidecar_for_harness(
    harness: dict[str, Any],
    args: argparse.Namespace,
    rows: list[dict[str, Any]],
) -> _DinoSidecarForHarness:
    return _DinoSidecarForHarness(harness, args, rows)


def _selected_rows_requiring_dino_sidecar(
    harness: dict[str, Any],
    selected_rows: list[dict[str, Any]],
    *,
    explicit_runtime_map_prior: str = "",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    prior_already_available = bool(explicit_runtime_map_prior or harness.get("runtime_map_prior"))
    if any(row.get("requires_runtime_map_prior") for row in selected_rows) and not (
        prior_already_available
    ):
        rows.extend(
            row for row in harness.get("setup_rows") or [] if _row_command_uses_grounding_dino(row)
        )
        rows.extend(row for row in selected_rows if row.get("requires_runtime_map_prior"))
    rows.extend(row for row in selected_rows if _row_command_uses_grounding_dino(row))
    return _dedupe_rows(rows)


def _mark_dino_dependent_rows_blocked(
    rows: list[dict[str, Any]],
    reason: str,
) -> None:
    for row in _dedupe_rows(rows):
        direct_dino_dependency = _is_setup_row(row) or _row_command_uses_grounding_dino(row)
        row["status"] = "infra_failed" if direct_dino_dependency else "blocked"
        row["behavior_status"] = "infra_failure"
        row["reason"] = reason
        row["updated_at"] = _utc_timestamp()


def _dedupe_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        row_id = str(row.get("row_id") or "")
        if row_id in seen:
            continue
        seen.add(row_id)
        deduped.append(row)
    return deduped


def _row_command_uses_grounding_dino(row: dict[str, Any]) -> bool:
    for item in row.get("command") or []:
        text = str(item)
        if not text.startswith(("camera_labeler=", "visual_grounding=")):
            continue
        value = text.split("=", maxsplit=1)[1]
        producers = value.replace(",", "+").split("+")
        if DINO_VISUAL_GROUNDING_PIPELINE_ID in producers:
            return True
    return False


def _visual_grounding_base_url() -> str:
    return os.environ.get("VISUAL_GROUNDING_BASE_URL") or DEFAULT_VISUAL_GROUNDING_BASE_URL


def _visual_grounding_host_port(base_url: str) -> tuple[str, int]:
    parsed = urllib_parse.urlparse(base_url)
    if parsed.scheme not in {"http", "https"}:
        raise RuntimeError(f"unsupported visual grounding base URL: {base_url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    return host, int(port)


def _dino_sidecar_python_bin() -> Path | None:
    configured = os.environ.get("ROBOCLAWS_VISUAL_GROUNDING_PYTHON")
    if configured and Path(configured).is_file():
        return Path(configured)
    candidates = [REPO_ROOT / ".venv-visual-grounding/bin/python"]
    return next((path for path in candidates if path.is_file()), None)


def _harness_output_dir(args: argparse.Namespace, rows: list[dict[str, Any]]) -> Path:
    output_dir = getattr(args, "output_dir", None)
    if output_dir:
        return Path(output_dir)
    for row in rows:
        row_output_dir = row.get("output_dir")
        if row_output_dir:
            return Path(str(row_output_dir)).parent
    return Path("output/molmo/codex-harness8")


def _wait_for_dino_sidecar_ready(
    *,
    base_url: str,
    process: subprocess.Popen[bytes],
    timeout_s: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + max(timeout_s, 0.0)
    last_probe = _probe_dino_sidecar(base_url)
    while True:
        if last_probe.get("healthy"):
            return last_probe
        if process.poll() is not None:
            last_probe["reason"] = (
                f"sidecar process exited before readiness with status {process.returncode}; "
                f"{last_probe.get('reason') or 'not ready'}"
            )
            return last_probe
        if time.monotonic() >= deadline:
            last_probe["reason"] = (
                f"sidecar did not become ready within {timeout_s:g}s; "
                f"{last_probe.get('reason') or 'not ready'}"
            )
            return last_probe
        time.sleep(1.0)
        last_probe = _probe_dino_sidecar(base_url)


def _probe_dino_sidecar(base_url: str, *, timeout_s: float = 2.0) -> dict[str, Any]:
    endpoint_url = base_url.rstrip("/") + VISUAL_GROUNDING_ENDPOINT
    request = urllib_request.Request(
        endpoint_url,
        data=json.dumps(_dino_probe_request()).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "roboclaws-codex-harness8-dino-probe/1.0",
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with urllib_request.urlopen(request, timeout=timeout_s) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib_error.HTTPError as exc:
        return {
            "healthy": False,
            "base_url": base_url,
            "endpoint_url": endpoint_url,
            "reason": f"http_error_{exc.code}",
            "latency_ms": _elapsed_ms(started),
        }
    except (urllib_error.URLError, TimeoutError, socket.timeout) as exc:
        return {
            "healthy": False,
            "base_url": base_url,
            "endpoint_url": endpoint_url,
            "reason": _probe_error_reason(exc),
            "latency_ms": _elapsed_ms(started),
        }
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        return {
            "healthy": False,
            "base_url": base_url,
            "endpoint_url": endpoint_url,
            "reason": f"invalid_json_response: {exc}",
            "latency_ms": _elapsed_ms(started),
        }
    return _dino_probe_summary(
        payload,
        base_url=base_url,
        endpoint_url=endpoint_url,
        started=started,
    )


def _dino_probe_request() -> dict[str, Any]:
    return {
        "schema": VISUAL_GROUNDING_REQUEST_SCHEMA,
        "run_id": "codex-harness8-dino-sidecar-probe",
        "observation_id": "readiness_probe",
        "waypoint_id": "readiness_probe",
        "room_id": "readiness_probe",
        "capture_context": {"discovered_during": "harness_readiness_probe"},
        "image": {
            "mime_type": "image/png",
            "bytes_base64": DINO_SIDECAR_PROBE_IMAGE_BASE64,
            "width": 1,
            "height": 1,
        },
        "category_hints": [],
        "fixture_hints": [],
        "pipeline_request": {
            "pipeline_id": DINO_VISUAL_GROUNDING_PIPELINE_ID,
            "proposer": {"producer_id": DINO_VISUAL_GROUNDING_PIPELINE_ID},
            "refiner": {},
        },
    }


def _dino_probe_summary(
    payload: Any,
    *,
    base_url: str,
    endpoint_url: str,
    started: float,
) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {
            "healthy": False,
            "base_url": base_url,
            "endpoint_url": endpoint_url,
            "reason": "response was not a JSON object",
            "latency_ms": _elapsed_ms(started),
        }
    pipeline = payload.get("pipeline") if isinstance(payload.get("pipeline"), dict) else {}
    stages = pipeline.get("stages") if isinstance(pipeline.get("stages"), list) else []
    diagnostics = payload.get("diagnostics") if isinstance(payload.get("diagnostics"), dict) else {}
    stage_summaries = [
        {
            "stage": stage.get("stage") or "",
            "producer_id": stage.get("producer_id") or "",
            "version": stage.get("version") or "",
            "status": stage.get("status") or "",
        }
        for stage in stages
        if isinstance(stage, dict)
    ]
    summary = {
        "healthy": False,
        "base_url": base_url,
        "endpoint_url": endpoint_url,
        "schema": payload.get("schema") or "",
        "status": payload.get("status") or "",
        "pipeline_id": pipeline.get("pipeline_id") or "",
        "diagnostic_mode": diagnostics.get("diagnostic_mode") or "",
        "stages": stage_summaries,
        "latency_ms": _elapsed_ms(started),
    }
    if (
        payload.get("schema") == VISUAL_GROUNDING_RESPONSE_SCHEMA
        and payload.get("status") == "ok"
        and pipeline.get("pipeline_id") == DINO_VISUAL_GROUNDING_PIPELINE_ID
        and _probe_response_is_real_dino(summary)
    ):
        summary["healthy"] = True
        summary["reason"] = ""
        return summary
    summary["reason"] = _unhealthy_dino_probe_reason(payload, summary)
    return summary


def _probe_response_is_real_dino(summary: dict[str, Any]) -> bool:
    if summary.get("diagnostic_mode") == "real_grounding_dino":
        return True
    stages = summary.get("stages")
    if not isinstance(stages, list):
        return False
    return any(
        isinstance(stage, dict)
        and stage.get("producer_id") == DINO_VISUAL_GROUNDING_PIPELINE_ID
        and stage.get("version") == "real-sidecar-adapter-v1"
        for stage in stages
    )


def _unhealthy_dino_probe_reason(payload: dict[str, Any], summary: dict[str, Any]) -> str:
    if payload.get("schema") != VISUAL_GROUNDING_RESPONSE_SCHEMA:
        return "visual grounding response schema mismatch"
    if payload.get("status") != "ok":
        error = payload.get("error") if isinstance(payload.get("error"), dict) else {}
        return str(error.get("reason") or payload.get("status") or "sidecar returned failure")
    if summary.get("pipeline_id") != DINO_VISUAL_GROUNDING_PIPELINE_ID:
        return (
            "sidecar answered with pipeline "
            f"{summary.get('pipeline_id')!r}, not {DINO_VISUAL_GROUNDING_PIPELINE_ID!r}"
        )
    return "sidecar did not report the real Grounding DINO adapter"


def _probe_error_reason(exc: BaseException) -> str:
    if isinstance(exc, urllib_error.URLError):
        reason = getattr(exc, "reason", None)
        if isinstance(reason, (TimeoutError, socket.timeout)):
            return "timeout"
        if reason:
            return f"connection_error: {reason}"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    return f"connection_error: {exc}"


def _tcp_accepting(host: str, port: int, *, timeout_s: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _elapsed_ms(started: float) -> int:
    return round((time.monotonic() - started) * 1000)


def _execute_row_with_retries(row: dict[str, Any], args: argparse.Namespace) -> int:
    attempts: list[dict[str, Any]] = []
    max_attempts = max(int(args.provider_retry_attempts), 0) + 1
    status = 1
    final_provider_transient: dict[str, Any] | None = None
    started_at_epoch = time.time()
    row["started_at"] = _utc_timestamp()
    row["started_at_epoch"] = started_at_epoch
    row["harness_parallelism"] = max(int(getattr(args, "parallelism", 1) or 1), 1)
    for attempt_index in range(max_attempts):
        if attempt_index:
            sleep_s = max(float(args.provider_retry_sleep_s), 0.0)
            if sleep_s:
                time.sleep(sleep_s)
        status = _execute_row(row, args)
        provider_transient = _provider_transient_evidence(row)
        final_provider_transient = provider_transient
        attempts.append(
            {
                "attempt": attempt_index + 1,
                "exit_status": status,
                "run_dir": row.get("run_dir") or "",
                "provider_transient": bool(provider_transient),
                "provider_transient_evidence": provider_transient,
                "finished_at": _utc_timestamp(),
            }
        )
        if status == 0 or not provider_transient or attempt_index == max_attempts - 1:
            break
        print(
            f"provider transient failure detected for {row.get('row_id')}; "
            f"retrying attempt {attempt_index + 2}/{max_attempts}"
        )

    row["attempts"] = attempts
    row["retry_count"] = max(len(attempts) - 1, 0)
    row["provider_retry_count"] = sum(1 for attempt in attempts if attempt["provider_transient"])
    finished_at_epoch = time.time()
    row["finished_at"] = _utc_timestamp()
    row["finished_at_epoch"] = finished_at_epoch
    row["wallclock_s"] = round(max(0.0, finished_at_epoch - started_at_epoch), 3)
    if status == 0 and len(attempts) > 1:
        row["infra_note"] = "succeeded after provider-transient retry"
    elif status != 0 and final_provider_transient:
        row["status"] = "provider_transient_failed"
        row["behavior_status"] = "infra_failure"
        provider_reason = str(final_provider_transient.get("provider_reason") or "")
        if provider_reason:
            row["provider_reason"] = provider_reason
        row["retryable"] = bool(final_provider_transient.get("retryable"))
        row["resume_available"] = bool(final_provider_transient.get("resume_available"))
        row["reason"] = f"provider transient failure after {len(attempts)} attempt(s)" + (
            f": {provider_reason}" if provider_reason else ""
        )
    return status


def _execute_row(row: dict[str, Any], args: argparse.Namespace) -> int:
    command = _command_for_row(row, just_bin=args.just_bin)
    print("+ " + row_rerun_command({**row, "command": command}))
    env = os.environ.copy()
    row_env = row.get("env") if isinstance(row.get("env"), dict) else {}
    env.update({str(key): str(value) for key, value in row_env.items()})
    status = subprocess.run(command, env=env, check=False).returncode
    run_dir = _latest_seed_dir(Path(row["output_dir"]), seed=args.seed)
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
        live_status = _wait_for_live_terminal_status(
            run_dir,
            timeout_s=args.live_wait_timeout_s,
            poll_s=args.live_wait_poll_s,
        )
        if live_status is not None:
            status = int(live_status.get("exit_status") or 0)
            row["live_status"] = live_status
    _refresh_row_from_evidence(row, status=status, run_dir=run_dir)
    return status


def _refresh_row_from_evidence(
    row: dict[str, Any],
    *,
    status: int | None = None,
    run_dir: Path | None = None,
) -> None:
    if run_dir is None:
        row_run_dir = row.get("run_dir")
        if row_run_dir:
            candidate = Path(str(row_run_dir))
            if candidate.is_dir():
                run_dir = candidate
    if run_dir is not None:
        row["run_dir"] = str(run_dir)
        live_status = _read_status(run_dir / "live_status.json")
        if live_status.get("phase") != "unknown":
            row["live_status"] = live_status
            if status is None and "exit_status" in live_status:
                status = int(live_status.get("exit_status") or 0)
        _refresh_row_artifacts(row, run_dir)
    elif row.get("run_result_path"):
        _refresh_row_artifacts(row, Path(str(row["run_result_path"])).parent)

    if status is None:
        existing_status = row.get("strict_exit_status", row.get("exit_status"))
        if isinstance(existing_status, int):
            status = existing_status
    if status is None:
        return
    row["exit_status"] = status
    row["updated_at"] = _utc_timestamp()
    _refresh_row_status(row, status)


def _refresh_row_status(row: dict[str, Any], status: int) -> None:
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    completion_status = str(metrics.get("completion_status") or "")
    score_status = str(metrics.get("score_status") or "")
    visual_grounding_infra_failure = _visual_grounding_infra_failure(metrics)
    row["strict_exit_status"] = status
    if _is_setup_row(row):
        if row.get("runtime_map_path"):
            row["status"] = "artifact_success"
            row["behavior_status"] = "artifact_success"
            row["reason"] = (
                ""
                if status == 0
                else f"runtime_metric_map.json was produced; command exited with status {status}"
            )
        elif status == 0:
            row["status"] = "launched"
            row["behavior_status"] = "artifact_pending"
            row["reason"] = "command returned before runtime_metric_map.json existed"
        else:
            row["status"] = "failed"
            row["behavior_status"] = "failed"
            row["reason"] = f"command exited with status {status}"
        return
    if status == 0:
        row["status"] = "success" if row.get("report_path") else "launched"
        row["reason"] = (
            "" if row.get("report_path") else "command returned before seed report existed"
        )
        row["behavior_status"] = completion_status or score_status or row["status"]
    elif completion_status == "success" or score_status == "success":
        row["status"] = "strict_checker_failed"
        row["behavior_status"] = "success"
        row["reason"] = (
            f"strict cleanup checker exited with status {status}; "
            "run_result.json reports cleanup success"
        )
    elif visual_grounding_infra_failure:
        row["status"] = "infra_failed"
        row["behavior_status"] = "infra_failure"
        row["reason"] = visual_grounding_infra_failure
    else:
        row["status"] = "failed"
        row["behavior_status"] = completion_status or score_status or "failed"
        row["reason"] = f"command exited with status {status}"


def _refresh_row_artifacts(row: dict[str, Any], run_dir: Path) -> None:
    report_path = run_dir / "report.html"
    if report_path.is_file():
        row["report_path"] = str(report_path)
    run_result_path = run_dir / "run_result.json"
    if run_result_path.is_file():
        row["run_result_path"] = str(run_result_path)
        row["metrics"] = (
            _setup_result_metrics(run_result_path)
            if _is_setup_row(row)
            else _run_result_metrics(run_result_path)
        )
    runtime_map_path = run_dir / "runtime_metric_map.json"
    if runtime_map_path.is_file():
        row["runtime_map_path"] = str(runtime_map_path)


def _run_result_metrics(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    score = data.get("score") if isinstance(data.get("score"), dict) else {}
    advisory = (
        data.get("advisory_evaluation") if isinstance(data.get("advisory_evaluation"), dict) else {}
    )
    advisory_counts = advisory.get("counts") if isinstance(advisory.get("counts"), dict) else {}
    runtime = data.get("runtime_timing") if isinstance(data.get("runtime_timing"), dict) else {}
    score_semantic = (
        score.get("semantic_acceptability")
        if isinstance(score.get("semantic_acceptability"), dict)
        else {}
    )
    diagnostics = (
        data.get("agent_diagnostics") if isinstance(data.get("agent_diagnostics"), dict) else {}
    )
    visual_grounding_failures = _visual_grounding_failures(data)
    return {
        "completion_status": data.get("completion_status") or score.get("completion_status") or "",
        "score_status": score.get("status") or "",
        "exact_restored": score.get("restored_count"),
        "total_targets": score.get("total_targets"),
        "semantic_accepted": _semantic_accepted_count(score, advisory_counts),
        "score_semantic_accepted": score_semantic.get("accepted_count"),
        "supports_exact": advisory_counts.get("supports_exact"),
        "benign_disagreement": advisory_counts.get("benign_disagreement"),
        "disagrees": advisory_counts.get("disagrees"),
        "semantic_order_errors": diagnostics.get("semantic_order_errors"),
        "semantic_order_recovered_errors": diagnostics.get("semantic_order_recovered_errors"),
        "semantic_order_unrecovered_errors": diagnostics.get("semantic_order_unrecovered_errors"),
        "sweep_coverage_rate": data.get("sweep_coverage_rate")
        if data.get("sweep_coverage_rate") is not None
        else score.get("sweep_coverage_rate"),
        "disturbance_count": data.get("disturbance_count")
        if data.get("disturbance_count") is not None
        else score.get("disturbance_count"),
        "tool_call_count": runtime.get("tool_call_count"),
        "total_elapsed_s": runtime.get("total_elapsed_s"),
        "visual_grounding_failures": visual_grounding_failures,
        "report_path": str(path.parent / "report.html"),
    }


def _setup_result_metrics(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    runtime_map = (
        data.get("runtime_metric_map") if isinstance(data.get("runtime_metric_map"), dict) else {}
    )
    return {
        "sweep_coverage_rate": data.get("sweep_coverage_rate"),
        "disturbance_count": data.get("disturbance_count"),
        "runtime_semantic_anchor_count": len(runtime_map.get("public_semantic_anchors") or []),
        "visual_grounding_pipeline_id": data.get("visual_grounding_pipeline_id") or "",
        "visual_grounding_failures": _visual_grounding_failures(data),
        "report_path": str(path.parent / "report.html"),
    }


def _visual_grounding_failures(data: Any) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    stack: list[Any] = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            pipeline = current.get("visual_grounding_pipeline")
            if isinstance(pipeline, dict) and str(pipeline.get("status") or "") == "failed":
                failures.append(
                    {
                        "pipeline_id": pipeline.get("pipeline_id") or "",
                        "status": pipeline.get("status") or "",
                        "failure_reason": pipeline.get("failure_reason") or "",
                        "failure_message": pipeline.get("failure_message") or "",
                        "candidate_count": pipeline.get("candidate_count"),
                    }
                )
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)
    return failures


def _visual_grounding_infra_failure(metrics: dict[str, Any]) -> str:
    failures = metrics.get("visual_grounding_failures")
    if not isinstance(failures, list):
        return ""
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        reason = str(failure.get("failure_reason") or "")
        if reason not in VISUAL_GROUNDING_INFRA_FAILURE_REASONS:
            continue
        pipeline = str(failure.get("pipeline_id") or "visual_grounding")
        message = str(failure.get("failure_message") or reason)
        return f"{pipeline} visual grounding infra failure: {reason}; {message}"
    return ""


def _semantic_accepted_count(score: dict[str, Any], advisory_counts: dict[str, Any]) -> int | None:
    score_semantic = (
        score.get("semantic_acceptability")
        if isinstance(score.get("semantic_acceptability"), dict)
        else {}
    )
    accepted = score_semantic.get("accepted_count")
    if isinstance(accepted, int):
        return accepted
    total = advisory_counts.get("total_reviewed")
    rejected = 0
    for key in ("needs_review", "disagrees"):
        value = advisory_counts.get(key)
        if isinstance(value, int):
            rejected += value
    if isinstance(total, int):
        return total - rejected
    rows = score.get("object_results")
    if isinstance(rows, list):
        return sum(
            1
            for item in rows
            if isinstance(item, dict)
            and str(item.get("semantic_acceptability") or "") in {"preferred", "acceptable"}
        )
    return None


def _selected_rows(harness: dict[str, Any], *, filters: set[str]) -> list[dict[str, Any]]:
    rows = list(harness.get("rows") or [])
    if not filters:
        return rows
    return [row for row in rows if str(row.get("row_id") or "") in filters]


def _mark_dry_run(harness: dict[str, Any]) -> None:
    for row in [*(harness.get("setup_rows") or []), *(harness.get("rows") or [])]:
        row["status"] = "dry_run"
        row["reason"] = "dry run requested; command was not executed"
        row["updated_at"] = _utc_timestamp()


def _mark_explicit_runtime_map_prior(harness: dict[str, Any], prior_path: str) -> None:
    prior = Path(prior_path)
    for row in harness.get("setup_rows") or []:
        row["runtime_map_prior"] = str(prior)
        row["updated_at"] = _utc_timestamp()
        if prior.is_file():
            row["status"] = "artifact_success"
            row["behavior_status"] = "artifact_success"
            row["reason"] = (
                "using explicit runtime_map_prior; setup command was not executed by this harness"
            )
            row["run_dir"] = str(prior.parent)
            _refresh_row_artifacts(row, prior.parent)
        else:
            row["status"] = "failed"
            row["reason"] = "explicit runtime_map_prior does not exist"


def _merge_existing_state(
    harness: dict[str, Any],
    output_dir: Path,
    *,
    selected_row_ids: set[str],
) -> None:
    manifest_path = output_dir / "codex_cleanup_harness8.json"
    if not manifest_path.is_file():
        return
    try:
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(existing, dict):
        return
    existing_setup = _rows_by_id(existing.get("setup_rows") or [])
    harness["setup_rows"] = [
        _merged_existing_row(existing_setup, row) for row in harness.get("setup_rows") or []
    ]
    existing_rows = _rows_by_id(existing.get("rows") or [])
    merged_rows = []
    for row in harness.get("rows") or []:
        row_id = str(row.get("row_id") or "")
        if row_id not in selected_row_ids and row_id in existing_rows:
            merged_rows.append(_merged_existing_row(existing_rows, row))
        else:
            merged_rows.append(row)
    harness["rows"] = merged_rows


def _merged_existing_row(
    existing_rows: dict[str, dict[str, Any]],
    row: dict[str, Any],
) -> dict[str, Any]:
    row_id = str(row.get("row_id") or "")
    existing = existing_rows.get(row_id)
    if existing is None:
        return row
    _refresh_row_from_evidence(existing)
    return existing


def _replace_runtime_map_prior(harness: dict[str, Any], prior_path: str) -> None:
    for row in harness.get("rows") or []:
        row["command"] = [
            (
                f"runtime_map_prior={prior_path}"
                if item == f"runtime_map_prior={RUNTIME_MAP_PRIOR_PLACEHOLDER}"
                else item
            )
            for item in row.get("command") or []
        ]
        row["rerun_command"] = row_rerun_command(row)


def _rows_by_id(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(row.get("row_id") or ""): row for row in rows if isinstance(row, dict)}


def _has_existing_row_evidence(row: dict[str, Any]) -> bool:
    return bool(
        row.get("run_result_path")
        or row.get("report_path")
        or row.get("runtime_map_path")
        or row.get("live_status")
        or row.get("run_dir")
        or row.get("exit_status") is not None
        or row.get("status") in {"success", "failed", "artifact_success", "launched"}
    )


def _is_setup_row(row: dict[str, Any]) -> bool:
    return str(row.get("grid_role") or "") == "setup"


def _provider_transient_evidence(row: dict[str, Any]) -> dict[str, Any] | None:
    live_status = row.get("live_status") if isinstance(row.get("live_status"), dict) else {}
    if live_status.get("reason") != "provider_transient_failure":
        return None
    if live_status.get("retryable") is not True:
        return None
    return {
        "source": "live_status.json",
        "provider_reason": str(live_status.get("provider_reason") or ""),
        "retryable": True,
        "resume_available": bool(live_status.get("resume_available")),
    }


def _tail_text(path: Path, *, max_bytes: int = 256_000) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(size - max_bytes, 0), os.SEEK_SET)
            data = handle.read(max_bytes)
    except OSError:
        return ""
    return data.decode("utf-8", errors="replace")


def _command_for_row(row: dict[str, Any], *, just_bin: str) -> list[str]:
    command = [str(item) for item in row.get("command") or []]
    if command and command[0] == "just":
        command[0] = just_bin
    return command


def _latest_runtime_map(output_dir: Path, *, seed: int) -> Path | None:
    seed_dir = _latest_seed_dir(output_dir, seed=seed)
    if seed_dir is None:
        return None
    path = seed_dir / "runtime_metric_map.json"
    return path if path.is_file() else None


def _latest_seed_dir(output_dir: Path, *, seed: int) -> Path | None:
    direct = output_dir / f"seed-{seed}"
    if direct.is_dir():
        return direct
    candidates = sorted(
        path
        for path in output_dir.glob(f"*/seed-{seed}")
        if path.is_dir()
        and (
            (path / "run_result.json").is_file()
            or (path / "runtime_metric_map.json").is_file()
            or (path / "report.html").is_file()
            or (path / "live_status.json").is_file()
            or (path / "tmux_session.txt").is_file()
        )
    )
    return candidates[-1] if candidates else None


def _wait_for_live_terminal_status(
    run_dir: Path,
    *,
    timeout_s: float,
    poll_s: float,
) -> dict[str, Any] | None:
    status_path = run_dir / "live_status.json"
    if not status_path.is_file():
        return None
    deadline = time.monotonic() + timeout_s
    last_status = _read_status(status_path)
    while True:
        phase = str(last_status.get("phase") or "")
        if phase in {"finished", "failed"} and "exit_status" in last_status:
            return last_status
        if time.monotonic() >= deadline:
            timed_out = dict(last_status)
            timed_out["phase"] = "failed"
            timed_out["exit_status"] = 124
            timed_out["reason"] = "live row did not reach terminal status before timeout"
            return timed_out
        time.sleep(max(float(poll_s), 0.1))
        last_status = _read_status(status_path)


def _read_status(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"phase": "unknown"}
    return data if isinstance(data, dict) else {"phase": "unknown"}


def row_rerun_command(row: dict[str, Any]) -> str:
    env = row.get("env") or {}
    env_prefix = " ".join(f"{key}={value}" for key, value in sorted(env.items()))
    command = shell_join(row.get("command") or [])
    return f"{env_prefix} {command}".strip()


def _write_outputs(harness: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "codex_cleanup_harness8.json").write_text(
        json.dumps(harness, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output_dir / "codex_cleanup_harness8.html").write_text(
        _render_report(harness),
        encoding="utf-8",
    )


def _render_report(harness: dict[str, Any]) -> str:
    setup_rows = "\n".join(_render_row(row) for row in harness.get("setup_rows") or [])
    rows = "\n".join(_render_row(row) for row in harness.get("rows") or [])
    if not setup_rows:
        setup_rows = '<tr><td colspan="11">No setup row.</td></tr>'
    if not rows:
        rows = '<tr><td colspan="11">No cleanup rows.</td></tr>'
    return (
        "\n".join(
            [
                "<!doctype html>",
                '<meta charset="utf-8">',
                "<title>Codex Cleanup Harness 8</title>",
                "<style>",
                "body{font-family:system-ui,sans-serif;max-width:1280px;margin:2rem auto;"
                "padding:0 1rem;color:#202331;background:#f7f8fb}",
                "table{border-collapse:collapse;width:100%;background:white;margin:1rem 0}",
                "th,td{border:1px solid #d9dee8;padding:.55rem;text-align:left;vertical-align:top}",
                "th{background:#edf1f7}",
                "code{background:#f0f3f8;padding:1px 4px;border-radius:4px;white-space:pre-wrap}",
                ".sub{color:#5f6675}",
                "</style>",
                "<h1>Codex Cleanup Harness 8</h1>",
                f'<p class="sub">{html.escape(str(harness.get("description") or ""))}</p>',
                "<h2>Setup</h2>",
                f"<table>{_thead()}{setup_rows}</table>",
                "<h2>Cleanup Rows</h2>",
                f"<table>{_thead()}{rows}</table>",
            ]
        )
        + "\n"
    )


def _thead() -> str:
    return (
        "<thead><tr><th>Row</th><th>Status</th><th>Behavior</th><th>Map</th><th>Lane</th>"
        "<th>Exact</th><th>Semantic</th><th>Sweep</th><th>Disturb</th>"
        "<th>Order</th><th>Port</th><th>Parallelism</th><th>Elapsed</th>"
        "<th>Report</th><th>Command / reason</th></tr></thead>"
    )


def _render_row(row: dict[str, Any]) -> str:
    axes = row.get("axes") or {}
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    report_path = str(row.get("report_path") or "")
    if report_path:
        report = f'<a href="{html.escape(report_path, quote=True)}">report.html</a>'
    else:
        report = ""
    exact = _ratio(metrics.get("exact_restored"), metrics.get("total_targets"))
    semantic = _ratio(metrics.get("semantic_accepted"), metrics.get("total_targets"))
    if not semantic:
        semantic = _ratio(metrics.get("score_semantic_accepted"), metrics.get("total_targets"))
    elapsed = metrics.get("total_elapsed_s")
    if isinstance(elapsed, (int, float)):
        elapsed_text = f"{float(elapsed):.1f}s"
    else:
        elapsed_text = ""
    order_errors = metrics.get("semantic_order_unrecovered_errors")
    if isinstance(order_errors, int):
        order_text = str(order_errors)
    else:
        order_text = ""
    reason = str(row.get("reason") or "")
    retry_text = ""
    retry_count = row.get("retry_count")
    if isinstance(retry_count, int) and retry_count:
        retry_text = f"<br>retry_count={retry_count}"
    infra_note = str(row.get("infra_note") or "")
    if infra_note:
        retry_text += f"<br>{html.escape(infra_note)}"
    command = str(row.get("rerun_command") or "")
    return (
        "<tr>"
        f"<td>{html.escape(str(row.get('label') or row.get('row_id') or 'row'))}"
        f"<br><code>{html.escape(str(row.get('row_id') or ''))}</code></td>"
        f"<td><code>{html.escape(str(row.get('status') or 'pending'))}</code></td>"
        f"<td><code>{html.escape(str(row.get('behavior_status') or ''))}</code></td>"
        f"<td><code>{html.escape(str(axes.get('map_mode') or ''))}</code></td>"
        f"<td><code>{html.escape(str(axes.get('evidence_lane') or ''))}</code></td>"
        f"<td>{html.escape(exact)}</td>"
        f"<td>{html.escape(semantic)}</td>"
        f"<td>{html.escape(str(metrics.get('sweep_coverage_rate') or ''))}</td>"
        f"<td>{html.escape(str(metrics.get('disturbance_count') or ''))}</td>"
        f"<td>{html.escape(order_text)}</td>"
        f"<td><code>{html.escape(str(row.get('assigned_port') or ''))}</code></td>"
        f"<td><code>{html.escape(str(row.get('harness_parallelism') or ''))}</code></td>"
        f"<td>{html.escape(elapsed_text)}</td>"
        f"<td>{report}</td>"
        f"<td><code>{html.escape(command)}</code><br>{html.escape(reason)}{retry_text}</td>"
        "</tr>"
    )


def _ratio(value: Any, total: Any) -> str:
    if isinstance(value, int) and isinstance(total, int) and total:
        return f"{value}/{total}"
    return ""


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


if __name__ == "__main__":
    raise SystemExit(main())

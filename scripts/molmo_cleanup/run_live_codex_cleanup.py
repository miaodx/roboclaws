#!/usr/bin/env python3
"""Run a Molmo cleanup Codex live-agent session inside a detached shell."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO

from roboclaws.agents.drivers.household_live import household_cleanup_server_argv
from roboclaws.agents.live_status import LiveAgentFailure, classify_live_agent_failure
from roboclaws.household.generated_mess import generated_mess_success_threshold
from roboclaws.household.report import runtime_timing_from_trace
from roboclaws.household.task_intent import (
    TASK_INTENT_MODE_CUSTOM,
    TASK_INTENT_MODE_DEFAULT,
    normalize_task_intent_mode,
)
from roboclaws.household.visual_backend_slots import (
    MOLMOSPACES_SUBPROCESS_BACKEND,
    VisualBackendSlotError,
    VisualBackendSlotLease,
    acquire_visual_backend_slot,
)

try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except AttributeError:
    pass

FULL_PERMISSION_ARG = "--dangerously-bypass-approvals-and-sandbox"
CHECKER_SCRIPT = "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py"
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"
CODEX_CLEANUP_MCP_SERVER_NAME = "cleanup"
CODEX_TURN_IDLE_TIMEOUT_ENV = "ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S"
CODEX_TURN_IDLE_TIMEOUT_EXIT_STATUS = 124
DEFAULT_CODEX_TURN_IDLE_TIMEOUT_S = 300.0
CODEX_LIVE_NO_PLAN_TOOL_INSTRUCTION = (
    "Live MCP route constraint: do not call update_plan, do not create todo/checklist "
    "tool items, and do not use any planning tool. In this Docker Codex live MCP "
    "route, planning/resource helpers can be misrouted as robot tools by some "
    "Responses-compatible providers. Do not call read_mcp_resource or any "
    "resources/read tool; the task skill is already copied into the task workspace "
    "and the operative cleanup instructions are included in the prompt. Track "
    "progress in normal text only. When you call a robot tool, choose the cleanup "
    "MCP tool entry exactly as exposed by Codex: Codex events should show "
    "server=cleanup and tool=metric_map/observe/pick/place/done. If the tool "
    "protocol requires a function namespace, use namespace cleanup with the "
    "unprefixed tool name; never emit a bare function_call named metric_map, "
    "and never use mcp__cleanup__, mcp__roboclaws__, roboclaws__, or any other "
    "double-underscore provider prefix. Do not call exec_command, "
    "shell, bash, python, apply_patch, or any coding/developer tool; this live "
    "route exposes only robot cleanup MCP tools."
)
CODEX_LIVE_SEMANTIC_ORDER_INSTRUCTION = (
    "Cleanup tool-order rule: after navigate_to_receptacle, use place_inside for "
    "fridge, refrigerator, shelf, bookshelf, bookcase, or shelving targets. Open a "
    "receptacle first only for fridge/refrigerator targets. Use place only for "
    "surface targets such as table, sofa, bed, desk, sink, counter, or stand. If a "
    "tool returns error_reason=semantic_order with required_tool, call that exact "
    "required_tool next instead of substituting another cleanup tool. After "
    "open_receptacle succeeds while you are holding an object, the next cleanup "
    "tool must be place_inside with that same fixture_id before done, metric_map, "
    "observe, or another navigate call."
)


class LiveAgentRunFailure(RuntimeError):
    """Raised after a live-agent turn writes structured failure status."""

    def __init__(self, message: str, failure: LiveAgentFailure) -> None:
        super().__init__(message)
        self.failure = failure


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Own the server, Codex exec, checker, and status files for one live run.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--client-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--tmux-session", required=True)
    parser.add_argument("--codex-bin", required=True)
    parser.add_argument("--codex-model", default="")
    parser.add_argument("--codex-provider-summary", default="system defaults")
    parser.add_argument(
        "--codex-turn-idle-timeout-s",
        type=float,
        default=None,
        help=(
            "Maximum quiet time for the Codex exec turn before killing it and "
            "failing this live run. Set to 0 to disable."
        ),
    )
    parser.add_argument("--server-startup-timeout-s", type=float, default=600.0)
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--min-generated-mess-count", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--codex-model-arg", action="append", default=[])
    parser.add_argument("--checker-visual-arg", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runner = LiveCodexCleanupRunner(args)
    return runner.run()


class LiveCodexCleanupRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.run_dir = args.run_dir
        self.status_path = args.status_path
        self.timing_path = self.run_dir / "live_timing.json"
        self.started_at_epoch = time.time()
        self.server_proc: subprocess.Popen[bytes] | None = None
        self.lock_file = None
        self.visual_slot: VisualBackendSlotLease | None = None
        self.live_timing: dict[str, Any] = {
            "schema": "molmo_live_timing_v1",
            "started_at_epoch": self.started_at_epoch,
            "profile": getattr(args, "profile", ""),
            "backend": getattr(args, "backend", ""),
            "policy": getattr(args, "policy", ""),
        }

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._acquire_lock()
            self._write_status("starting-server")
            self._start_server()
            self._wait_for_mcp_ready()
            self._run_codex()
            self._wait_for_server_finish()
            self._check_result()
        except KeyboardInterrupt:
            self._write_status("failed", 130)
            self._write_live_timing("failed", 130, reason="keyboard_interrupt")
            self._cleanup_server()
            self._release_visual_slot()
            return 130
        except LiveAgentRunFailure as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, **exc.failure.status_fields())
            self._write_live_timing("failed", 1, **exc.failure.status_fields())
            self._cleanup_server()
            self._release_visual_slot()
            return 1
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, reason=str(exc))
            self._write_live_timing("failed", 1, reason=str(exc))
            self._cleanup_server()
            self._release_visual_slot()
            return 1

        self._write_live_timing("finished", 0)
        self._write_status("finished", 0)
        self._release_visual_slot()
        return 0

    def _acquire_lock(self) -> None:
        if self.args.backend == MOLMOSPACES_SUBPROCESS_BACKEND:
            try:
                self.visual_slot = acquire_visual_backend_slot(
                    repo_root=self.args.repo_root,
                    run_id=_run_id_from_run_dir(self.run_dir),
                    pid=os.getpid(),
                    backend=self.args.backend,
                    port=self.args.port,
                    output_dir=self.run_dir,
                    status_path=self.status_path,
                    owner="codex-live",
                )
            except VisualBackendSlotError as exc:
                detail = (
                    f": {json.dumps(exc.active_slots, sort_keys=True)}" if exc.active_slots else ""
                )
                raise RuntimeError(
                    "no MolmoSpaces visual backend slot is available"
                    f" under {self.args.repo_root / 'output/molmo/visual-backend-slots'}{detail}"
                ) from exc
            return

        self.args.lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = self.args.lock_path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            lock_file.seek(0)
            active = lock_file.read().strip()
            lock_file.close()
            detail = f": {active}" if active else ""
            raise RuntimeError(
                f"another live Molmo cleanup run holds {self.args.lock_path}{detail}"
            ) from exc
        lock_file.seek(0)
        lock_file.truncate()
        lock_file.write(
            json.dumps(
                {
                    "pid": os.getpid(),
                    "run_dir": str(self.run_dir),
                    "status_path": str(self.status_path),
                    "tmux_session": self.args.tmux_session,
                    "started_at_epoch": self.started_at_epoch,
                },
                sort_keys=True,
            )
            + "\n"
        )
        lock_file.flush()
        self.lock_file = lock_file

    def _release_visual_slot(self) -> None:
        if self.visual_slot is None:
            return
        try:
            self.visual_slot.release()
        except VisualBackendSlotError as exc:
            print(f"warning: could not release visual backend slot: {exc}", file=sys.stderr)
        finally:
            self.visual_slot = None

    def _start_server(self) -> None:
        print("==> detached Codex Molmo cleanup runner")
        print(f"    repo    : {self.args.repo_root}")
        print(f"    run dir : {self.run_dir}")
        print(f"    MCP URL : {self.args.client_url}")
        self._mark_timing("server_start")

        probe_host = _probe_host(self.args.host)
        if _port_accepting(probe_host, self.args.port):
            raise RuntimeError(
                f"TCP port {self.args.host}:{self.args.port} is already in use before server start"
            )

        command = [
            *household_cleanup_server_argv(str(self.args.repo_root / ".venv/bin/python")),
            *self.args.server_arg,
        ]
        env = os.environ.copy()
        if env.get(REPORT_RERUN_COMMAND_ENV):
            command.extend(["--rerun-command", env[REPORT_RERUN_COMMAND_ENV]])
        self.server_proc = subprocess.Popen(command, cwd=self.args.repo_root, env=env)
        (self.run_dir / "server.pid").write_text(f"{self.server_proc.pid}\n", encoding="utf-8")

    def _wait_for_mcp_ready(self) -> None:
        assert self.server_proc is not None
        probe_host = _probe_host(self.args.host)
        deadline = time.monotonic() + self.args.server_startup_timeout_s
        while time.monotonic() < deadline:
            if self.server_proc.poll() is not None:
                raise RuntimeError("cleanup MCP server exited before becoming ready")
            if _port_accepting(probe_host, self.args.port):
                self._mark_timing("server_ready")
                return
            time.sleep(0.5)
        raise RuntimeError(
            f"cleanup MCP server did not become ready at {self.args.host}:{self.args.port} "
            f"within {self.args.server_startup_timeout_s:g}s"
        )

    def _run_codex(self) -> None:
        self._write_status("running-codex")
        self._mark_timing("codex_exec_start")
        task_name = getattr(self.args, "task_name", "household-cleanup")
        env = os.environ.copy()
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE", "1")
        env.setdefault(
            "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE",
            str(self.run_dir / "agent-docker-workspace"),
        )
        agent_workspace, agent_task_dir = _prepare_agent_workspace(
            repo_root=self.args.repo_root,
            task_name=task_name,
            skill_name="molmo-realworld-cleanup",
            workspace=Path(env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"]),
        )
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_TASK", task_name)
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS", "molmo-realworld-cleanup")
        env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"] = str(agent_workspace)
        container_isolated = _docker_isolated_workspace_enabled(env)
        agent_cd = "/workspace/task" if container_isolated else str(agent_task_dir)
        last_message_host_path = agent_task_dir / "codex-last-message.md"
        last_message_cli_path = (
            "/workspace/task/codex-last-message.md"
            if container_isolated
            else str(last_message_host_path)
        )

        for server_name in (CODEX_CLEANUP_MCP_SERVER_NAME, "roboclaws"):
            subprocess.run(
                [self.args.codex_bin, "mcp", "remove", server_name],
                cwd=agent_task_dir,
                env=env,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        subprocess.run(
            [
                self.args.codex_bin,
                "mcp",
                "add",
                CODEX_CLEANUP_MCP_SERVER_NAME,
                "--url",
                self.args.client_url,
            ],
            cwd=agent_task_dir,
            env=env,
            check=True,
        )

        print("==> launching Codex exec with full permissions")
        if self.args.codex_provider_summary != "system defaults":
            print(f"==> Codex provider for this run: {self.args.codex_provider_summary}")
        print(f"==> kickoff: {self.args.kickoff_prompt}")

        turn_idle_timeout_s = _codex_turn_idle_timeout_s(
            getattr(self.args, "codex_turn_idle_timeout_s", None)
        )
        prompt = _codex_live_prompt(self.args.kickoff_prompt)
        command = [
            self.args.codex_bin,
            "exec",
            "--json",
            "--output-last-message",
            last_message_cli_path,
            *self.args.codex_model_arg,
            FULL_PERMISSION_ARG,
            "--cd",
            agent_cd,
            prompt,
        ]
        (self.run_dir / "codex-command.txt").write_text(
            " ".join(_shell_quote(item) for item in command) + "\n",
            encoding="utf-8",
        )
        codex_events_path = self.run_dir / "codex-events.jsonl"
        stderr_path = self.run_dir / "codex.stderr.log"
        print("==> Codex turn 1/1")
        status = _run_and_tee(
            command,
            cwd=agent_task_dir,
            stdout_path=codex_events_path,
            stderr_path=stderr_path,
            env=env,
            idle_timeout_s=turn_idle_timeout_s,
        )
        if last_message_host_path.is_file():
            shutil.copyfile(last_message_host_path, self.run_dir / "codex-last-message.md")
        self._mark_timing("codex_exec_end")
        self.live_timing["codex_events"] = _combined_codex_event_summary([codex_events_path])
        if status != 0 and not (self.run_dir / "run_result.json").is_file():
            failure = classify_live_agent_failure(
                codex_events_path,
                stderr_path,
                exit_status=status,
            )
            raise LiveAgentRunFailure(
                f"Codex exec failed after one live-agent turn: {failure.reason}",
                failure,
            )
        if (
            self.server_proc is not None
            and self.server_proc.poll() is None
            and not (self.run_dir / "run_result.json").is_file()
        ):
            raise RuntimeError("Codex exec ended without done after one live-agent turn")

    def _wait_for_server_finish(self) -> None:
        assert self.server_proc is not None
        self._write_status("waiting-for-server-finish")
        print("==> waiting for cleanup MCP server to finish after agent done")
        self._mark_timing("server_wait_start")
        status = self.server_proc.wait()
        self._mark_timing("server_finished")
        self.server_proc = None
        if status != 0:
            raise RuntimeError(f"cleanup MCP server exited with status {status}")

    def _check_result(self) -> None:
        self._write_status("checking-result")
        self._mark_timing("checker_start")
        task_name = getattr(self.args, "task_name", "household-cleanup")
        custom_task = (
            normalize_task_intent_mode(getattr(self.args, "task_intent_mode", ""))
            == TASK_INTENT_MODE_CUSTOM
        )
        checker_visual_args = list(self.args.checker_visual_arg)
        if custom_task:
            checker_visual_args = _without_full_cleanup_checker_gates(checker_visual_args)
        run_result = self.run_dir / "run_result.json"
        if not run_result.is_file():
            raise RuntimeError(f"live run finished without {run_result}")

        checker_args = [
            str(self.args.repo_root / ".venv/bin/python"),
            CHECKER_SCRIPT,
            "--expect-task",
            self.args.task,
            "--expect-task-name",
            task_name,
            "--expect-backend",
            self.args.backend,
            "--expect-policy",
            self.args.policy,
            "--expect-profile",
            self.args.profile,
            "--expect-mcp-server",
            "molmo_cleanup_realworld",
            "--min-generated-mess-count",
            self.args.min_generated_mess_count,
            "--require-agent-driven",
            "--require-advisory-scoring",
            *checker_visual_args,
        ]
        if task_name == "household-cleanup" and self.args.profile in {
            "smoke",
            "world-oracle-labels",
            "camera-grounded-labels",
            "camera-raw-fpv",
        }:
            if custom_task:
                _append_missing_checker_flag(checker_args, "--allow-partial-cleanup")
            else:
                checker_args.append("--require-clean-agent-run")
        if self.args.profile == "world-oracle-labels":
            _append_missing_checker_flag(checker_args, "--require-waypoint-honesty")
            _append_missing_checker_flag(checker_args, "--require-real-robot-alignment")
            if task_name == "household-cleanup" and not custom_task:
                _append_missing_checker_value(checker_args, "--min-semantic-accepted-count", "5")
            if not custom_task:
                _append_missing_checker_value(checker_args, "--min-sweep-coverage", "1.0")
        if self.args.profile == "camera-raw-fpv":
            raw_fpv_required_cleanup_count = str(
                generated_mess_success_threshold(int(self.args.min_generated_mess_count))
            )
            if not custom_task:
                _append_missing_checker_flag(checker_args, "--require-model-declared-observations")
                _append_missing_checker_value(
                    checker_args,
                    "--min-model-declared-observations",
                    raw_fpv_required_cleanup_count,
                )
                _append_missing_checker_value(
                    checker_args,
                    "--min-model-declared-actions",
                    raw_fpv_required_cleanup_count,
                )
                if task_name == "household-cleanup":
                    _append_missing_checker_value(
                        checker_args,
                        "--min-semantic-accepted-count",
                        raw_fpv_required_cleanup_count,
                    )
                _append_missing_checker_value(checker_args, "--min-sweep-coverage", "1.0")
            elif task_name == "household-cleanup":
                _append_missing_checker_flag(checker_args, "--allow-partial-cleanup")
        checker_args.append(str(run_result))

        try:
            status = _run_and_tee(
                checker_args,
                cwd=self.args.repo_root,
                stdout_path=self.run_dir / "checker.log",
                stderr_path=self.run_dir / "checker.log",
                env=os.environ.copy(),
            )
        finally:
            self._mark_timing("checker_end")
        if status != 0:
            raise RuntimeError(f"cleanup checker exited with status {status}")
        print(f"==> report: {self.run_dir / 'report.html'}")

    def _mark_timing(self, name: str) -> None:
        self.live_timing[f"{name}_epoch"] = time.time()

    def _write_live_timing(
        self,
        phase: str,
        exit_status: int,
        *,
        reason: str = "",
        provider_reason: str = "",
        retryable: bool | None = None,
        resume_available: bool | None = None,
        detail: str = "",
    ) -> None:
        finished_at = time.time()
        payload = dict(self.live_timing)
        payload.update(
            {
                "phase": phase,
                "exit_status": exit_status,
                "finished_at_epoch": finished_at,
            }
        )
        if reason:
            payload["reason"] = reason
        if provider_reason:
            payload["provider_reason"] = provider_reason
        if retryable is not None:
            payload["retryable"] = retryable
        if resume_available is not None:
            payload["resume_available"] = resume_available
        if detail:
            payload["detail"] = detail
        payload["runner_timing"] = _runner_timing_breakdown(payload, finished_at)
        payload["mcp_trace_timing"] = _mcp_trace_timing(self.run_dir)
        first_request = _first_mcp_request_epoch(self.run_dir)
        if first_request is not None:
            payload["time_to_first_mcp_request_s"] = _round_duration(
                first_request - self.started_at_epoch
            )
            server_ready = _float_or_none(payload.get("server_ready_epoch"))
            if server_ready is not None:
                payload["first_mcp_request_after_server_ready_s"] = _round_duration(
                    first_request - server_ready
                )
        payload["model_api_time_s"] = payload.get("codex_events", {}).get("model_api_time_s")
        payload["model_api_time_note"] = payload.get("codex_events", {}).get(
            "model_api_time_note",
            "Codex event timing was not available.",
        )
        self.timing_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _cleanup_server(self) -> None:
        proc = self.server_proc
        if proc is None or proc.poll() is not None:
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    def _write_status(
        self,
        phase: str,
        exit_status: int | None = None,
        *,
        reason: str = "",
        provider_reason: str = "",
        retryable: bool | None = None,
        resume_available: bool | None = None,
        detail: str = "",
    ) -> None:
        payload: dict[str, object] = {
            "phase": phase,
            "started_at_epoch": self.started_at_epoch,
        }
        if reason:
            payload["reason"] = reason
        if provider_reason:
            payload["provider_reason"] = provider_reason
        if retryable is not None:
            payload["retryable"] = retryable
        if resume_available is not None:
            payload["resume_available"] = resume_available
        if detail:
            payload["detail"] = detail
        if self.visual_slot is not None:
            payload["visual_backend_slot"] = self.visual_slot.to_payload()
        if exit_status is not None:
            payload["finished_at_epoch"] = time.time()
            payload["exit_status"] = exit_status
        self.status_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _run_and_tee(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str],
    idle_timeout_s: float | None = None,
) -> int:
    last_output_monotonic = time.monotonic()
    output_lock = threading.Lock()

    def mark_output() -> None:
        nonlocal last_output_monotonic
        with output_lock:
            last_output_monotonic = time.monotonic()

    def idle_elapsed_s() -> float:
        with output_lock:
            return time.monotonic() - last_output_monotonic

    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        start_new_session=True,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    with stdout_path.open("ab") as stdout_file:
        if stdout_path == stderr_path:
            stderr_file_context = stdout_file
            stderr_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, [stderr_file_context, sys.stderr.buffer]),
                kwargs={"on_chunk": mark_output},
                daemon=True,
            )
            stdout_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stdout, [stdout_file, sys.stdout.buffer]),
                kwargs={"on_chunk": mark_output},
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            status = _wait_for_process_with_idle_timeout(
                proc,
                idle_timeout_s=idle_timeout_s,
                idle_elapsed_s=idle_elapsed_s,
                timeout_log=stderr_file_context,
            )
            stdout_thread.join()
            stderr_thread.join()
            return status

        with stderr_path.open("ab") as stderr_file:
            stdout_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stdout, [stdout_file, sys.stdout.buffer]),
                kwargs={"on_chunk": mark_output},
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, [stderr_file, sys.stderr.buffer]),
                kwargs={"on_chunk": mark_output},
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            status = _wait_for_process_with_idle_timeout(
                proc,
                idle_timeout_s=idle_timeout_s,
                idle_elapsed_s=idle_elapsed_s,
                timeout_log=stderr_file,
            )
            stdout_thread.join()
            stderr_thread.join()
            return status


def _wait_for_process_with_idle_timeout(
    proc: subprocess.Popen[bytes],
    *,
    idle_timeout_s: float | None,
    idle_elapsed_s,
    timeout_log: BinaryIO,
) -> int:
    if idle_timeout_s is None or idle_timeout_s <= 0:
        return proc.wait()
    while True:
        try:
            return proc.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            if idle_elapsed_s() < idle_timeout_s:
                continue
            timeout_log.write(
                (
                    f"codex turn idle timeout after {idle_timeout_s:g}s; "
                    "terminating process group and failing live run\n"
                ).encode("utf-8")
            )
            timeout_log.flush()
            _terminate_process_group(proc)
            return CODEX_TURN_IDLE_TIMEOUT_EXIT_STATUS


def _terminate_process_group(proc: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            return
        except OSError:
            proc.kill()
        proc.wait(timeout=10)


def _runner_timing_breakdown(timing: dict[str, Any], finished_at: float) -> dict[str, Any]:
    started = _float_or_none(timing.get("started_at_epoch"))
    codex_start = _float_or_none(timing.get("codex_exec_start_epoch"))
    codex_end = _float_or_none(timing.get("codex_exec_end_epoch"))
    checker_start = _float_or_none(timing.get("checker_start_epoch"))
    checker_end = _float_or_none(timing.get("checker_end_epoch"))
    server_start = _float_or_none(timing.get("server_start_epoch"))
    server_ready = _float_or_none(timing.get("server_ready_epoch"))
    server_finished = _float_or_none(timing.get("server_finished_epoch"))
    total = _round_duration(finished_at - started) if started is not None else None

    segments: dict[str, float] = {}
    if started is not None and codex_start is not None:
        segments["pre_codex_setup_s"] = _round_duration(codex_start - started)
    if codex_start is not None and codex_end is not None:
        segments["codex_exec_elapsed_s"] = _round_duration(codex_end - codex_start)
    if codex_end is not None and server_finished is not None:
        segments["post_codex_server_wait_s"] = _round_duration(server_finished - codex_end)
    if checker_start is not None and checker_end is not None:
        segments["checker_elapsed_s"] = _round_duration(checker_end - checker_start)
    if checker_end is not None:
        segments["final_overhead_s"] = _round_duration(finished_at - checker_end)
    if server_start is not None and server_ready is not None:
        segments["server_startup_s"] = _round_duration(server_ready - server_start)

    partition_keys = (
        "pre_codex_setup_s",
        "codex_exec_elapsed_s",
        "post_codex_server_wait_s",
        "checker_elapsed_s",
        "final_overhead_s",
    )
    accounted = sum(segments.get(key, 0.0) for key in partition_keys)
    breakdown: dict[str, Any] = {"total_elapsed_s": total, **segments}
    if total is not None:
        breakdown["accounted_elapsed_s"] = _round_duration(accounted)
        breakdown["unaccounted_elapsed_s"] = _round_duration(max(0.0, total - accounted))
        breakdown["accounting_note"] = (
            "The partitioned runner buckets sum to total wall time. MCP trace timing "
            "runs inside codex_exec_elapsed_s and is reported separately to avoid "
            "double counting concurrent server work."
        )
    return breakdown


def _mcp_trace_timing(run_dir: Path) -> dict[str, Any]:
    run_result_path = run_dir / "run_result.json"
    if run_result_path.is_file():
        try:
            run_result = json.loads(run_result_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            run_result = {}
        timing = run_result.get("runtime_timing")
        if isinstance(timing, dict):
            return timing
    trace_events = _read_jsonl_path(run_dir / "trace.jsonl")
    return runtime_timing_from_trace(trace_events)


def _first_mcp_request_epoch(run_dir: Path) -> float | None:
    for event in _read_jsonl_path(run_dir / "trace.jsonl"):
        if event.get("event") == "request" and not str(event.get("tool", "")).startswith("<"):
            return _float_or_none(event.get("ts"))
    return None


def _codex_event_summary(path: Path) -> dict[str, Any]:
    events = _read_jsonl_path(path)
    type_counts: dict[str, int] = {}
    item_counts: dict[str, int] = {}
    usage: dict[str, Any] = {}
    api_durations: list[float] = []
    for event in events:
        event_type = str(event.get("type") or "")
        if event_type:
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        item = event.get("item")
        if isinstance(item, dict):
            item_type = str(item.get("type") or "")
            if item_type:
                item_counts[item_type] = item_counts.get(item_type, 0) + 1
        if isinstance(event.get("usage"), dict):
            usage = dict(event["usage"])
        api_durations.extend(_model_api_durations_from_event(event))

    model_api_time_s: float | None = None
    note = (
        "Codex JSON events did not expose per-request model API duration. "
        "Model/API latency is therefore included in MCP between-tool gaps and "
        "the overall codex_exec_elapsed_s bucket."
    )
    if api_durations:
        model_api_time_s = _round_duration(sum(api_durations))
        note = "Summed model API duration fields emitted by Codex JSON events."

    return {
        "event_count": len(events),
        "type_counts": type_counts,
        "item_counts": item_counts,
        "usage": usage,
        "model_api_time_s": model_api_time_s,
        "model_api_time_note": note,
    }


def _combined_codex_event_summary(paths: list[Path]) -> dict[str, Any]:
    summaries = [_codex_event_summary(path) for path in paths if path.is_file()]
    type_counts: dict[str, int] = {}
    item_counts: dict[str, int] = {}
    event_count = 0
    usage: dict[str, Any] = {}
    model_api_time_s = 0.0
    model_api_time_known = False
    notes = []
    for summary in summaries:
        event_count += int(summary.get("event_count") or 0)
        for key, value in (summary.get("type_counts") or {}).items():
            type_counts[str(key)] = type_counts.get(str(key), 0) + int(value or 0)
        for key, value in (summary.get("item_counts") or {}).items():
            item_counts[str(key)] = item_counts.get(str(key), 0) + int(value or 0)
        if summary.get("usage"):
            usage = dict(summary["usage"])
        api_time = summary.get("model_api_time_s")
        if isinstance(api_time, (int, float)):
            model_api_time_known = True
            model_api_time_s += float(api_time)
        note = str(summary.get("model_api_time_note") or "")
        if note and note not in notes:
            notes.append(note)
    return {
        "turn_count": len(summaries),
        "event_count": event_count,
        "type_counts": type_counts,
        "item_counts": item_counts,
        "usage": usage,
        "model_api_time_s": _round_duration(model_api_time_s) if model_api_time_known else None,
        "model_api_time_note": " ".join(notes)
        if notes
        else "Codex event timing was not available.",
    }


def _codex_live_prompt(prompt: str) -> str:
    return (
        f"{CODEX_LIVE_NO_PLAN_TOOL_INSTRUCTION}\n"
        f"{CODEX_LIVE_SEMANTIC_ORDER_INSTRUCTION}\n\n"
        f"{prompt}"
    )


def _codex_turn_idle_timeout_s(configured: float | None) -> float | None:
    if configured is not None:
        return configured
    env_value = os.environ.get(CODEX_TURN_IDLE_TIMEOUT_ENV)
    if env_value:
        try:
            return float(env_value)
        except ValueError:
            return DEFAULT_CODEX_TURN_IDLE_TIMEOUT_S
    return DEFAULT_CODEX_TURN_IDLE_TIMEOUT_S


def _model_api_durations_from_event(event: dict[str, Any]) -> list[float]:
    durations: list[float] = []
    stack: list[Any] = [event]
    while stack:
        item = stack.pop()
        if isinstance(item, dict):
            for key, value in item.items():
                key_text = str(key).lower()
                if isinstance(value, (int, float)) and key_text in {
                    "model_api_time_s",
                    "api_time_s",
                    "api_elapsed_s",
                    "model_latency_s",
                }:
                    durations.append(float(value))
                elif isinstance(value, (int, float)) and key_text in {
                    "model_api_time_ms",
                    "api_time_ms",
                    "api_elapsed_ms",
                    "model_latency_ms",
                }:
                    durations.append(float(value) / 1000.0)
                elif isinstance(value, (dict, list)):
                    stack.append(value)
        elif isinstance(item, list):
            stack.extend(item)
    return durations


def _read_jsonl_path(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _round_duration(value: float) -> float:
    return round(max(0.0, value), 3)


def _tee_stream(stream: BinaryIO, outputs: list[BinaryIO], *, on_chunk=None) -> None:
    for chunk in iter(lambda: stream.readline(), b""):
        if on_chunk is not None:
            on_chunk()
        for output in outputs:
            try:
                output.write(chunk)
                output.flush()
            except BlockingIOError:
                # Interactive terminals may be nonblocking under agent control. Keep
                # teeing to the artifact file even if live console mirroring drops a chunk.
                continue


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _docker_isolated_workspace_enabled(env: dict[str, str]) -> bool:
    return (
        env.get("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE") == "1"
        or env.get("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_NAV_WORKSPACE") == "1"
    )


def _prepare_agent_workspace(
    *,
    repo_root: Path,
    task_name: str,
    skill_name: str,
    workspace: Path | None = None,
) -> tuple[Path, Path]:
    workspace = _agent_workspace_root(repo_root=repo_root, task_name=task_name, workspace=workspace)
    task_dir = workspace / "task"
    skills_dir = workspace / "skills"
    task_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name in ("AGENTS.md", "CLAUDE.md"):
        (workspace / name).unlink(missing_ok=True)
        (task_dir / name).unlink(missing_ok=True)
    source_skill_dir = repo_root / "skills" / skill_name
    if not (source_skill_dir / "SKILL.md").is_file():
        raise RuntimeError(f"requested skill not found: {source_skill_dir / 'SKILL.md'}")
    workspace_skill_dir = skills_dir / skill_name
    if workspace_skill_dir.exists() or workspace_skill_dir.is_symlink():
        if workspace_skill_dir.is_dir() and not workspace_skill_dir.is_symlink():
            shutil.rmtree(workspace_skill_dir)
        else:
            workspace_skill_dir.unlink()
    shutil.copytree(source_skill_dir, workspace_skill_dir)
    task_skills_dir = task_dir / "skills"
    if task_skills_dir.exists() or task_skills_dir.is_symlink():
        if task_skills_dir.is_dir() and not task_skills_dir.is_symlink():
            shutil.rmtree(task_skills_dir)
        else:
            task_skills_dir.unlink()
    shutil.copytree(skills_dir, task_skills_dir)
    (task_dir / "README.md").write_text(
        "# Roboclaws Molmo Cleanup Agent Workspace\n\n"
        f"Read `skills/{skill_name}/SKILL.md`, then use the roboclaws MCP tools.\n",
        encoding="utf-8",
    )
    return workspace, task_dir


def _agent_workspace_root(
    *,
    repo_root: Path,
    task_name: str,
    workspace: Path | None = None,
) -> Path:
    if workspace is not None:
        selected = workspace.expanduser()
        if not selected.is_absolute():
            selected = repo_root / selected
        return selected
    workspace_env = os.environ.get("ROBOCLAWS_CODE_AGENT_WORKSPACE") or os.environ.get(
        "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"
    )
    if not workspace_env:
        return Path(tempfile.mkdtemp(prefix=f"roboclaws-{task_name}-agent-"))

    workspace = Path(workspace_env).expanduser()
    if not workspace.is_absolute():
        workspace = repo_root / workspace
    return workspace


def _shell_quote(value: str) -> str:
    if not value:
        return "''"
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-"
    if all(char in safe for char in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


def _append_missing_checker_flag(args: list[str], flag: str) -> None:
    if flag not in args:
        args.append(flag)


def _append_missing_checker_value(args: list[str], flag: str, value: str) -> None:
    if flag not in args:
        args.extend([flag, value])


def _without_full_cleanup_checker_gates(args: list[str]) -> list[str]:
    filtered: list[str] = []
    skip_value = False
    for arg in args:
        if skip_value:
            skip_value = False
            continue
        if arg in {
            "--min-semantic-accepted-count",
            "--min-model-declared-observations",
            "--min-model-declared-actions",
            "--min-sweep-coverage",
        }:
            skip_value = True
            continue
        if arg in {
            "--require-clean-agent-run",
            "--require-model-declared-observations",
        }:
            continue
        filtered.append(arg)
    return filtered


def _run_id_from_run_dir(run_dir: Path) -> str:
    name = run_dir.name
    parent = run_dir.parent.name
    if parent:
        return f"{parent}/{name}"
    return name


if __name__ == "__main__":
    raise SystemExit(main())

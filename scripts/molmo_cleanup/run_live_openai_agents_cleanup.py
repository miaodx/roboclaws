#!/usr/bin/env python3
"""Run one experimental OpenAI Agents SDK Molmo cleanup live-agent session."""

from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO

from roboclaws.agents.drivers.household_live import household_cleanup_server_argv
from roboclaws.agents.drivers.openai_agents_live import (
    MCP_CLIENT_SESSION_TIMEOUT_ENV,
    OpenAIAgentsLiveRuntime,
)
from roboclaws.agents.live_runtime import LiveAgentMCPServer, LiveAgentRequest
from roboclaws.agents.live_status import LiveAgentFailure
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
from roboclaws.launch.evaluation import (
    checker_flags_for_household_intent,
    household_intent_id_for_checker,
    merge_checker_flags,
)

CHECKER_SCRIPT = "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py"
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"
DEFAULT_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS = 2
DEFAULT_MCP_CLIENT_SESSION_TIMEOUT_S = 30.0


DEFAULT_INCOMPLETE_TURN_CONTINUATION_PROMPT = """
Continuation recovery for the same live household cleanup run:

The previous OpenAI Agents SDK invocation ended without calling `done`, so no
`run_result.json` was produced. Continue from the current cleanup MCP server
state. Do not summarize progress as a final answer. First inspect the current
runtime state through cleanup tools, then continue only missing waypoint,
visual-grounding, pick/place, or completion steps. Call `done` only after the
MCP-visible task state satisfies the cleanup instructions. The runner will count
success only when MCP `done` produces `run_result.json`.
""".strip()


class LiveAgentRunFailure(RuntimeError):
    """Raised after the SDK runtime writes structured failure status."""

    def __init__(self, message: str, failure: LiveAgentFailure) -> None:
        super().__init__(message)
        self.failure = failure


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Own the cleanup MCP server, OpenAI Agents SDK runtime, checker, and "
            "status files for one experimental live run."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--client-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--provider-profile", default="codex-env")
    parser.add_argument("--model", default="")
    parser.add_argument(
        "--max-turns",
        type=int,
        default=int(os.environ.get("ROBOCLAWS_OPENAI_AGENTS_MAX_TURNS", "128")),
        help=(
            "Maximum OpenAI Agents SDK agent turns inside one runner invocation. "
            "This is not runner-side continuation."
        ),
    )
    parser.add_argument(
        "--incomplete-turn-continuation-attempts",
        type=int,
        default=int(
            os.environ.get(
                "ROBOCLAWS_OPENAI_AGENTS_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS",
                str(DEFAULT_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS),
            )
        ),
        help=(
            "Bounded continuation attempts after a successful SDK turn ends without "
            "MCP done/run_result.json. The runner still never infers cleanup success."
        ),
    )
    parser.add_argument(
        "--cache-tools-list",
        action=argparse.BooleanOptionalAction,
        default=_env_bool("ROBOCLAWS_OPENAI_AGENTS_CACHE_TOOLS_LIST", default=True),
        help=(
            "Ask the OpenAI Agents SDK MCP client to cache the cleanup tool list. "
            "The cleanup MCP tool catalog is static within one live run."
        ),
    )
    parser.add_argument(
        "--mcp-client-session-timeout-s",
        type=float,
        default=float(
            os.environ.get(
                MCP_CLIENT_SESSION_TIMEOUT_ENV,
                str(DEFAULT_MCP_CLIENT_SESSION_TIMEOUT_S),
            )
        ),
        help=(
            "OpenAI Agents SDK MCP ClientSession read timeout. Visual cleanup lanes can "
            "exceed the SDK's short default while robot-view artifacts are captured."
        ),
    )
    parser.add_argument("--server-startup-timeout-s", type=float, default=600.0)
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--task-name", default="household-cleanup")
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    parser.add_argument("--policy", default="openai_agents_agent")
    parser.add_argument("--task", required=True)
    parser.add_argument("--min-generated-mess-count", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--checker-visual-arg", action="append", default=[])
    return parser.parse_args(argv)


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def main(argv: list[str] | None = None) -> int:
    return LiveOpenAIAgentsCleanupRunner(parse_args(argv)).run()


class LiveOpenAIAgentsCleanupRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.run_dir = args.run_dir
        self.status_path = args.status_path
        self.timing_path = self.run_dir / "live_timing.json"
        self.started_at_epoch = time.time()
        self.server_proc: subprocess.Popen[bytes] | None = None
        self.server_log_path = self.run_dir / "openai-agents-server.log"
        self.server_log_file: BinaryIO | None = None
        self.server_log_thread: threading.Thread | None = None
        self.lock_file = None
        self.visual_slot: VisualBackendSlotLease | None = None
        self.live_timing: dict[str, Any] = {
            "schema": "molmo_live_timing_v1",
            "started_at_epoch": self.started_at_epoch,
            "profile": getattr(args, "profile", ""),
            "backend": getattr(args, "backend", ""),
            "policy": getattr(args, "policy", ""),
            "runtime": "openai-agents-live",
            "provider_profile": getattr(args, "provider_profile", ""),
            "model": getattr(args, "model", ""),
            "cache_tools_list": bool(getattr(args, "cache_tools_list", True)),
            "mcp_client_session_timeout_s": _round_duration(
                max(0.0, float(getattr(args, "mcp_client_session_timeout_s", 0.0) or 0.0))
            ),
        }

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._acquire_lock()
            self._write_status("starting-server")
            self._start_server()
            self._wait_for_mcp_ready()
            self._run_sdk_agent()
            self._wait_for_server_finish()
            self._check_result()
        except KeyboardInterrupt:
            self._write_status("failed", 130, reason="keyboard_interrupt")
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
                    owner="openai-agents-live",
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
                    "started_at_epoch": self.started_at_epoch,
                    "runtime": "openai-agents-live",
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
        print("==> OpenAI Agents SDK Molmo cleanup runner")
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
        self.server_proc = subprocess.Popen(
            command,
            cwd=self.args.repo_root,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        self._start_server_log_tee()
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

    def _run_sdk_agent(self) -> None:
        self._write_status("running-openai-agents")
        self._mark_timing("openai_agents_start")
        recovery_policy = IncompleteTurnRecoveryPolicy(
            max_attempts=int(
                getattr(
                    self.args,
                    "incomplete_turn_continuation_attempts",
                    DEFAULT_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS,
                )
            )
        )
        runtime = OpenAIAgentsLiveRuntime()
        prompt = self.args.kickoff_prompt
        attempt_index = 0
        result = None
        attempts: list[dict[str, Any]] = []
        while True:
            if attempt_index:
                self._write_status("running-openai-agents-continuation")
            request = self._sdk_request(prompt=prompt, attempt_index=attempt_index)
            result = runtime.run(request)
            attempt_summary = _sdk_attempt_summary(result, attempt_index=attempt_index)
            attempts.append(attempt_summary)
            self.live_timing["openai_agents_attempts"] = attempts
            if result.exit_status not in {0, None}:
                break
            if (self.run_dir / "run_result.json").is_file():
                break
            continuation_prompt = recovery_policy.continuation_prompt(
                original_prompt=self.args.kickoff_prompt,
                result=result,
                run_dir=self.run_dir,
                attempt_index=attempt_index,
            )
            if continuation_prompt is None:
                break
            attempt_summary["recovery_action"] = "continue"
            attempt_summary["recovery_reason"] = recovery_policy.reason
            attempt_index += 1
            prompt = continuation_prompt

        assert result is not None
        self._mark_timing("openai_agents_end")
        self.live_timing["openai_agents"] = {
            "phase": result.phase,
            "exit_status": result.exit_status,
            "reason": result.reason,
            "provider_reason": result.provider_reason,
            "retryable": result.retryable,
            "resume_available": result.resume_available,
            "usage": dict(result.usage),
            "trace_id": result.trace_id,
            "provider_session_id": result.provider_session_id,
        }
        if result.exit_status not in {0, None}:
            failure = LiveAgentFailure(
                reason=result.reason or "agent_cli_failure",
                retryable=bool(result.retryable),
                provider_reason=result.provider_reason,
                resume_available=bool(result.resume_available),
                detail=result.detail,
            )
            raise LiveAgentRunFailure(
                f"OpenAI Agents SDK runtime failed: {failure.reason}",
                failure,
            )
        if not (self.run_dir / "run_result.json").is_file():
            raise RuntimeError(
                "OpenAI Agents SDK turn ended without done after "
                f"{len(attempts)} OpenAI Agents SDK invocation(s)"
            )

    def _sdk_request(self, *, prompt: str, attempt_index: int) -> LiveAgentRequest:
        artifact_paths = {
            "live_status": self.status_path,
            "openai_agents_events": self.run_dir / "openai-agents-events.jsonl",
            "openai_agents_trace": self.run_dir / "openai-agents-trace.json",
        }
        if attempt_index:
            artifact_paths.update(
                {
                    "openai_agents_events": self.run_dir
                    / f"openai-agents-events.continuation-{attempt_index}.jsonl",
                    "openai_agents_trace": self.run_dir
                    / f"openai-agents-trace.continuation-{attempt_index}.json",
                }
            )
        return LiveAgentRequest(
            task_name=self.args.task_name,
            skill_name="molmo-realworld-cleanup",
            kickoff_prompt=prompt,
            mcp_server=LiveAgentMCPServer(name="cleanup", url=self.args.client_url),
            run_dir=self.run_dir,
            model=self.args.model,
            provider_profile=self.args.provider_profile,
            max_turns=self.args.max_turns,
            one_turn=True,
            metadata={
                "provider_profile": self.args.provider_profile,
                "max_turns": self.args.max_turns,
                "attempt_index": attempt_index,
                "attempt_role": "continuation" if attempt_index else "initial",
                "cache_tools_list": bool(getattr(self.args, "cache_tools_list", True)),
                "mcp_client_session_timeout_s": float(
                    getattr(self.args, "mcp_client_session_timeout_s", 0.0) or 0.0
                ),
            },
            artifact_paths=artifact_paths,
        )

    def _wait_for_server_finish(self) -> None:
        assert self.server_proc is not None
        self._write_status("waiting-for-server-finish")
        print("==> waiting for cleanup MCP server to finish after agent done")
        self._mark_timing("server_wait_start")
        status = self.server_proc.wait()
        self._mark_timing("server_finished")
        self._finish_server_log_tee()
        self.server_proc = None
        if status != 0:
            raise RuntimeError(f"cleanup MCP server exited with status {status}")

    def _check_result(self) -> None:
        self._write_status("checking-result")
        self._mark_timing("checker_start")
        task_name = getattr(self.args, "task_name", "household-cleanup")
        task_intent = os.environ.get("ROBOCLAWS_TASK_INTENT", "")
        custom_task = (
            normalize_task_intent_mode(getattr(self.args, "task_intent_mode", ""))
            == TASK_INTENT_MODE_CUSTOM
        )
        checker_visual_args = list(self.args.checker_visual_arg)
        if custom_task:
            checker_visual_args = _without_full_cleanup_checker_gates(checker_visual_args)
        intent_id = household_intent_id_for_checker(
            task_name=task_name,
            task_intent=task_intent,
            custom_task=custom_task,
        )
        checker_policy_args = checker_flags_for_household_intent(
            intent_id=intent_id,
            profile=self.args.profile,
            min_generated_mess_count=self.args.min_generated_mess_count,
        )
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
            *merge_checker_flags(checker_policy_args, checker_visual_args),
        ]
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
        payload["mcp_control_plane_metrics"] = _mcp_control_plane_metrics(self.run_dir)
        payload["openai_agents_event_metrics"] = _openai_agents_event_metrics(self.run_dir)
        payload["timeline"] = _live_timing_timeline(payload)
        self.timing_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")

    def _cleanup_server(self) -> None:
        proc = self.server_proc
        if proc is None:
            return
        if proc.poll() is not None:
            self._finish_server_log_tee()
            return
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        self._finish_server_log_tee()

    def _start_server_log_tee(self) -> None:
        proc = self.server_proc
        if proc is None:
            return
        stream = getattr(proc, "stdout", None)
        if stream is None:
            return
        self.server_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.server_log_file = self.server_log_path.open("ab")
        self.server_log_thread = threading.Thread(
            target=_tee_stream,
            args=(stream, [self.server_log_file, sys.stdout.buffer]),
            daemon=True,
        )
        self.server_log_thread.start()

    def _finish_server_log_tee(self) -> None:
        thread = self.server_log_thread
        if thread is not None:
            thread.join(timeout=5)
            self.server_log_thread = None
        log_file = self.server_log_file
        if log_file is not None:
            log_file.close()
            self.server_log_file = None

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


@dataclass(frozen=True)
class IncompleteTurnRecoveryPolicy:
    """Bounded recovery for SDK turns that end cleanly before MCP completion."""

    max_attempts: int
    reason: str = "incomplete_agent_turn"
    continuation_suffix: str = DEFAULT_INCOMPLETE_TURN_CONTINUATION_PROMPT

    def continuation_prompt(
        self,
        *,
        original_prompt: str,
        result: Any,
        run_dir: Path,
        attempt_index: int,
    ) -> str | None:
        if self.max_attempts <= 0:
            return None
        if attempt_index >= self.max_attempts:
            return None
        if (run_dir / "run_result.json").is_file():
            return None
        if getattr(result, "exit_status", None) not in {0, None}:
            return None
        if getattr(result, "phase", "") != "agent-turn-complete":
            return None
        return f"{original_prompt.rstrip()}\n\n{self.continuation_suffix}\n"


def _sdk_attempt_summary(result: Any, *, attempt_index: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "attempt_index": attempt_index,
        "attempt_role": "continuation" if attempt_index else "initial",
        "phase": getattr(result, "phase", ""),
        "exit_status": getattr(result, "exit_status", None),
        "reason": getattr(result, "reason", ""),
        "provider_reason": getattr(result, "provider_reason", ""),
        "run_result_present": bool(getattr(result, "run_result_present", False)),
        "trace_id": getattr(result, "trace_id", ""),
        "provider_session_id": getattr(result, "provider_session_id", ""),
    }
    started = _float_or_none(getattr(result, "started_at_epoch", None))
    finished = _float_or_none(getattr(result, "finished_at_epoch", None))
    if started is not None:
        payload["started_at_epoch"] = started
    if finished is not None:
        payload["finished_at_epoch"] = finished
    if started is not None and finished is not None:
        payload["elapsed_s"] = _round_duration(finished - started)
    return payload


def _run_and_tee(
    command: list[str],
    *,
    cwd: Path,
    stdout_path: Path,
    stderr_path: Path,
    env: dict[str, str],
) -> int:
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    with stdout_path.open("ab") as stdout_file:
        if stdout_path == stderr_path:
            stderr_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, [stdout_file, sys.stderr.buffer]),
                daemon=True,
            )
            stdout_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stdout, [stdout_file, sys.stdout.buffer]),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            status = proc.wait()
            stdout_thread.join()
            stderr_thread.join()
            return status

        with stderr_path.open("ab") as stderr_file:
            stdout_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stdout, [stdout_file, sys.stdout.buffer]),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, [stderr_file, sys.stderr.buffer]),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            status = proc.wait()
            stdout_thread.join()
            stderr_thread.join()
            return status


def _runner_timing_breakdown(timing: dict[str, Any], finished_at: float) -> dict[str, Any]:
    started = _float_or_none(timing.get("started_at_epoch"))
    sdk_start = _float_or_none(timing.get("openai_agents_start_epoch"))
    sdk_end = _float_or_none(timing.get("openai_agents_end_epoch"))
    checker_start = _float_or_none(timing.get("checker_start_epoch"))
    checker_end = _float_or_none(timing.get("checker_end_epoch"))
    server_start = _float_or_none(timing.get("server_start_epoch"))
    server_ready = _float_or_none(timing.get("server_ready_epoch"))
    server_finished = _float_or_none(timing.get("server_finished_epoch"))
    total = _round_duration(finished_at - started) if started is not None else None

    segments: dict[str, float] = {}
    if started is not None and sdk_start is not None:
        segments["pre_agent_setup_s"] = _round_duration(sdk_start - started)
    if sdk_start is not None and sdk_end is not None:
        segments["openai_agents_elapsed_s"] = _round_duration(sdk_end - sdk_start)
    if sdk_end is not None and server_finished is not None:
        segments["post_agent_server_wait_s"] = _round_duration(server_finished - sdk_end)
    if checker_start is not None and checker_end is not None:
        segments["checker_elapsed_s"] = _round_duration(checker_end - checker_start)
    if checker_end is not None:
        segments["final_overhead_s"] = _round_duration(finished_at - checker_end)
    if server_start is not None and server_ready is not None:
        segments["server_startup_s"] = _round_duration(server_ready - server_start)

    partition_keys = (
        "pre_agent_setup_s",
        "openai_agents_elapsed_s",
        "post_agent_server_wait_s",
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
            "runs inside openai_agents_elapsed_s and is reported separately to avoid "
            "double counting concurrent server work."
        )
    return breakdown


def _live_timing_timeline(timing: dict[str, Any]) -> dict[str, Any]:
    """Build a normalized timeline for cross-run latency comparisons."""

    finished_at = _float_or_none(timing.get("finished_at_epoch"))
    started_at = _float_or_none(timing.get("started_at_epoch"))
    runner_segments = _runner_timeline_segments(timing, finished_at)
    attempt_segments = _attempt_timeline_segments(timing)
    attribution = _latency_attribution(timing)
    return {
        "schema": "openai_agents_cleanup_timeline_v1",
        "started_at_epoch": started_at,
        "finished_at_epoch": finished_at,
        "total_elapsed_s": (timing.get("runner_timing") or {}).get("total_elapsed_s"),
        "runner_segments": runner_segments,
        "openai_agents_attempt_segments": attempt_segments,
        "latency_attribution": attribution,
        "notes": [
            "runner_segments partition end-to-end wall clock.",
            (
                "latency_attribution nests MCP trace attribution inside the SDK agent window; "
                "do not add it to runner_segments as extra wall time."
            ),
            (
                "between_tool_gap_s is the response-to-next-request window and includes model "
                "reasoning, SDK orchestration, transport, and other agent-side delay."
            ),
        ],
    }


def _runner_timeline_segments(
    timing: dict[str, Any],
    finished_at: float | None,
) -> list[dict[str, Any]]:
    started_at = _float_or_none(timing.get("started_at_epoch"))
    sdk_start = _float_or_none(timing.get("openai_agents_start_epoch"))
    sdk_end = _float_or_none(timing.get("openai_agents_end_epoch"))
    server_finished = _float_or_none(timing.get("server_finished_epoch"))
    checker_start = _float_or_none(timing.get("checker_start_epoch"))
    checker_end = _float_or_none(timing.get("checker_end_epoch"))
    segments = [
        _timeline_segment(
            "pre_agent_setup",
            "runner",
            started_at,
            sdk_start,
            "Launcher setup, lock acquisition, MCP server startup, and readiness wait.",
        ),
        _timeline_segment(
            "openai_agents_runtime",
            "sdk_agent",
            sdk_start,
            sdk_end,
            "OpenAI Agents SDK execution window including model calls and MCP tool use.",
        ),
        _timeline_segment(
            "post_agent_server_wait",
            "runner",
            sdk_end,
            server_finished,
            "Wait for the cleanup MCP server to flush artifacts and exit after done.",
        ),
        _timeline_segment(
            "checker",
            "verification",
            checker_start,
            checker_end,
            "Cleanup artifact checker.",
        ),
        _timeline_segment(
            "final_overhead",
            "runner",
            checker_end,
            finished_at,
            "Final timing/status write.",
        ),
    ]
    return [segment for segment in segments if segment is not None]


def _attempt_timeline_segments(timing: dict[str, Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    attempts = timing.get("openai_agents_attempts")
    if not isinstance(attempts, list):
        return segments
    for attempt in attempts:
        if not isinstance(attempt, dict):
            continue
        attempt_index = _int_or_none(attempt.get("attempt_index"))
        label = "sdk_attempt"
        if attempt_index is not None:
            label = f"sdk_attempt_{attempt_index}"
        segment = _timeline_segment(
            label,
            "sdk_agent_attempt",
            _float_or_none(attempt.get("started_at_epoch")),
            _float_or_none(attempt.get("finished_at_epoch")),
            str(attempt.get("attempt_role") or ""),
            extra={
                "attempt_index": attempt_index,
                "attempt_role": attempt.get("attempt_role"),
                "phase": attempt.get("phase"),
                "run_result_present": bool(attempt.get("run_result_present")),
                "recovery_action": attempt.get("recovery_action", ""),
                "recovery_reason": attempt.get("recovery_reason", ""),
            },
        )
        if segment is not None:
            segments.append(segment)
    return segments


def _latency_attribution(timing: dict[str, Any]) -> dict[str, Any]:
    mcp_timing = (
        timing.get("mcp_trace_timing") if isinstance(timing.get("mcp_trace_timing"), dict) else {}
    )
    runner_timing = (
        timing.get("runner_timing") if isinstance(timing.get("runner_timing"), dict) else {}
    )
    event_metrics = (
        timing.get("openai_agents_event_metrics")
        if isinstance(timing.get("openai_agents_event_metrics"), dict)
        else {}
    )
    sdk_elapsed = _float_or_none(runner_timing.get("openai_agents_elapsed_s"))
    mcp_elapsed = _float_or_none(mcp_timing.get("total_elapsed_s"))
    model_or_sdk_unattributed_s = None
    if sdk_elapsed is not None:
        model_or_sdk_unattributed_s = sdk_elapsed
        if mcp_elapsed is not None:
            model_or_sdk_unattributed_s = max(0.0, sdk_elapsed - mcp_elapsed)
    return {
        "openai_agents_elapsed_s": sdk_elapsed,
        "mcp_trace_elapsed_s": mcp_elapsed,
        "model_or_sdk_unattributed_s": (
            _round_duration(model_or_sdk_unattributed_s)
            if model_or_sdk_unattributed_s is not None
            else None
        ),
        "mcp_between_tool_gap_s": mcp_timing.get("between_tool_gap_s"),
        "mcp_robot_view_capture_s": mcp_timing.get("robot_view_capture_s"),
        "mcp_tool_handler_s": mcp_timing.get("tool_handler_s"),
        "mcp_other_overhead_s": mcp_timing.get("other_mcp_overhead_s"),
        "mcp_tool_call_count": mcp_timing.get("tool_call_count"),
        "mcp_list_tools_request_count": (timing.get("mcp_control_plane_metrics") or {}).get(
            "list_tools_request_count"
        ),
        "openai_agents_tool_error_count": event_metrics.get("tool_error_count"),
        "openai_agents_tool_error_classifications": event_metrics.get("tool_error_classifications"),
        "mcp_client_session_timeout_s": timing.get("mcp_client_session_timeout_s"),
    }


def _timeline_segment(
    name: str,
    category: str,
    started_at: float | None,
    finished_at: float | None,
    detail: str,
    *,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if started_at is None or finished_at is None:
        return None
    duration = _round_duration(finished_at - started_at)
    payload: dict[str, Any] = {
        "name": name,
        "category": category,
        "started_at_epoch": started_at,
        "finished_at_epoch": finished_at,
        "duration_s": duration,
        "detail": detail,
    }
    if extra:
        payload.update({key: value for key, value in extra.items() if value not in {None, ""}})
    return payload


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
    return runtime_timing_from_trace(_read_jsonl_path(run_dir / "trace.jsonl"))


def _mcp_control_plane_metrics(run_dir: Path) -> dict[str, Any]:
    log_path = run_dir / "openai-agents-server.log"
    if not log_path.is_file():
        return {
            "available": False,
            "reason": "openai-agents-server.log not present",
        }

    request_counts: dict[str, int] = {}
    http_status_counts: dict[str, int] = {}
    session_create_count = 0
    session_termination_count = 0
    trace_export_skip_count = 0
    line_count = 0
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line_count += 1
        request_match = re.search(r"Processing request of type ([A-Za-z0-9_]+)", line)
        if request_match:
            request_type = request_match.group(1)
            request_counts[request_type] = request_counts.get(request_type, 0) + 1
        status_match = re.search(r'HTTP/[^"]+"\s+([0-9]{3})\s+([A-Za-z][A-Za-z ]*)$', line)
        if status_match:
            status_key = f"{status_match.group(1)} {status_match.group(2).strip()}"
            http_status_counts[status_key] = http_status_counts.get(status_key, 0) + 1
        if "Created new transport with session ID:" in line:
            session_create_count += 1
        if "Terminating session:" in line:
            session_termination_count += 1
        if "OPENAI_API_KEY is not set, skipping trace export" in line:
            trace_export_skip_count += 1

    call_tool_count = request_counts.get("CallToolRequest", 0)
    list_tools_count = request_counts.get("ListToolsRequest", 0)
    total_requests = sum(request_counts.values())
    control_request_count = total_requests - call_tool_count
    return {
        "available": True,
        "log": log_path.name,
        "line_count": line_count,
        "request_type_counts": dict(sorted(request_counts.items())),
        "total_mcp_request_count": total_requests,
        "call_tool_request_count": call_tool_count,
        "list_tools_request_count": list_tools_count,
        "control_request_count": control_request_count,
        "list_tools_per_call_tool": (
            _round_duration(list_tools_count / call_tool_count) if call_tool_count else None
        ),
        "streamable_http_session_count": session_create_count,
        "session_termination_count": session_termination_count,
        "trace_export_skip_count": trace_export_skip_count,
        "http_status_counts": dict(sorted(http_status_counts.items())),
        "optimization_note": (
            "Control-plane counts are parsed from the MCP server log. Per-request "
            "control-plane latency is not exposed by the server log yet."
        ),
    }


def _openai_agents_event_metrics(run_dir: Path) -> dict[str, Any]:
    event_paths = sorted(run_dir.glob("openai-agents-events*.jsonl"))
    if not event_paths:
        return {
            "available": False,
            "reason": "openai-agents event files not present",
        }

    event_counts: dict[str, int] = {}
    tool_error_classifications: dict[str, int] = {}
    tool_error_messages: list[str] = []
    result_count = 0
    for path in event_paths:
        for event in _read_jsonl_path(path):
            event_type = str(event.get("event") or "")
            if event_type:
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if event_type == "result":
                result_count += 1
            if event_type != "tool_error":
                continue
            classification = str(event.get("classification") or "tool_error")
            tool_error_classifications[classification] = (
                tool_error_classifications.get(classification, 0) + 1
            )
            message = str(event.get("message") or "")
            if message and len(tool_error_messages) < 8:
                tool_error_messages.append(message)

    return {
        "available": True,
        "event_files": [path.name for path in event_paths],
        "event_counts": dict(sorted(event_counts.items())),
        "result_count": result_count,
        "tool_error_count": sum(tool_error_classifications.values()),
        "tool_error_classifications": dict(sorted(tool_error_classifications.items())),
        "tool_error_messages_sample": tool_error_messages,
    }


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


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _round_duration(value: float) -> float:
    return round(max(0.0, value), 3)


def _tee_stream(stream: BinaryIO, outputs: list[BinaryIO]) -> None:
    for chunk in iter(lambda: stream.readline(), b""):
        for output in outputs:
            try:
                output.write(chunk)
                output.flush()
            except BlockingIOError:
                continue


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


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

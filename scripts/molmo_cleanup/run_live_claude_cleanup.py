#!/usr/bin/env python3
"""Run a Molmo cleanup Claude Code live-agent session non-interactively."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import BinaryIO

from roboclaws.agents.drivers.household_live import (
    HouseholdLiveRunLease,
    acquire_household_live_run_lease,
    add_household_cleanup_live_runner_args,
    household_cleanup_server_argv,
    without_full_cleanup_checker_gates,
)
from roboclaws.agents.live_status import LiveAgentFailure, classify_live_agent_failure
from roboclaws.agents.provider_timing_proxy import (
    PROVIDER_TIMING_PROXY_UPSTREAM_ENV,
    ProviderTimingProxyHandle,
    provider_timing_proxy_enabled,
    replace_base_url_origin,
    start_provider_timing_proxy,
    stop_provider_timing_proxy,
)
from roboclaws.household.report_sections_timing import runtime_timing_from_trace
from roboclaws.household.task_intent import household_intent_from_args as _household_intent
from roboclaws.household.task_intent import household_task_name_from_args as _household_run_id
from roboclaws.launch.evaluation import (
    checker_flags_for_household_intent,
    household_intent_id_for_checker,
    merge_checker_flags,
)
from roboclaws.reports.live_performance import (
    extract_model_call_metrics,
    write_model_call_metrics_jsonl,
)

FULL_PERMISSION_ARGS = ("--dangerously-skip-permissions", "--permission-mode", "bypassPermissions")
CHECKER_SCRIPT = "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py"
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"


class LiveAgentRunFailure(RuntimeError):
    """Raised after a live-agent turn writes structured failure status."""

    def __init__(self, message: str, failure: LiveAgentFailure) -> None:
        super().__init__(message)
        self.failure = failure


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Own the server, Claude Code print run, checker, and status files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    add_household_cleanup_live_runner_args(parser)
    parser.add_argument("--claude-bin", required=True)
    parser.add_argument("--claude-provider-summary", default="system defaults")
    parser.add_argument("--claude-model-arg", action="append", default=[])
    parser.add_argument("--claude-env", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runner = LiveClaudeCleanupRunner(args)
    return runner.run()


class LiveClaudeCleanupRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.run_dir = args.run_dir
        self.status_path = args.status_path
        self.timing_path = self.run_dir / "live_timing.json"
        self.started_at_epoch = time.time()
        self.server_proc: subprocess.Popen[bytes] | None = None
        self.provider_timing_proxy: ProviderTimingProxyHandle | None = None
        self.run_lease = HouseholdLiveRunLease()
        self.live_timing: dict[str, object] = {
            "schema": "molmo_live_timing_v1",
            "runtime": "claude-code",
            "started_at_epoch": self.started_at_epoch,
            "profile": getattr(args, "profile", ""),
            "backend": getattr(args, "backend", ""),
            "policy": getattr(args, "policy", ""),
            "provider_profile": getattr(args, "claude_provider_summary", ""),
        }

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._acquire_lock()
            self._write_status("starting-server")
            self._start_server()
            self._wait_for_mcp_ready()
            self._run_claude()
            self._wait_for_server_finish()
            self._check_result()
        except KeyboardInterrupt:
            self._write_status("failed", 130)
            self._write_live_timing("failed", 130, reason="keyboard_interrupt")
            self._cleanup_provider_timing_proxy()
            self._cleanup_server()
            self._release_visual_slot()
            return 130
        except LiveAgentRunFailure as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, **exc.failure.status_fields())
            self._write_live_timing("failed", 1, **exc.failure.status_fields())
            self._cleanup_provider_timing_proxy()
            self._cleanup_server()
            self._release_visual_slot()
            return 1
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, reason=str(exc))
            self._write_live_timing("failed", 1, reason=str(exc))
            self._cleanup_provider_timing_proxy()
            self._cleanup_server()
            self._release_visual_slot()
            return 1

        source_error = self._write_live_timing("finished", 0)
        if source_error:
            self._write_status("failed", 1, reason=source_error)
            self._cleanup_provider_timing_proxy()
            self._release_visual_slot()
            return 1
        self._write_status("finished", 0)
        self._cleanup_provider_timing_proxy()
        self._release_visual_slot()
        return 0

    def _acquire_lock(self) -> None:
        self.run_lease = acquire_household_live_run_lease(
            backend=self.args.backend,
            repo_root=self.args.repo_root,
            run_dir=self.run_dir,
            status_path=self.status_path,
            lock_path=self.args.lock_path,
            port=self.args.port,
            owner="claude-live",
            started_at_epoch=self.started_at_epoch,
        )

    def _release_visual_slot(self) -> None:
        self.run_lease.release_visual_slot()

    def _start_server(self) -> None:
        print("==> Claude Code Molmo cleanup runner")
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

    def _run_claude(self) -> None:
        self._write_status("running-claude")
        self._mark_timing("claude_exec_start")
        env = os.environ.copy()
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE", "1")
        for item in self.args.claude_env:
            key, sep, value = item.partition("=")
            if not sep:
                raise RuntimeError(f"invalid --claude-env value: {item!r}")
            env[key] = value
        self._configure_provider_timing_proxy(env)
        run_id = _household_run_id(self.args)
        skill_name = getattr(self.args, "skill_name", None) or "molmo-realworld-cleanup"
        agent_workspace, agent_task_dir = _prepare_agent_workspace(
            repo_root=self.args.repo_root,
            run_id=run_id,
            skill_name=skill_name,
        )
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_TASK", run_id)
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS", skill_name)
        env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"] = str(agent_workspace)
        container_isolated = _docker_isolated_workspace_enabled(env)
        subprocess.run(
            [self.args.claude_bin, "mcp", "remove", "roboclaws"],
            cwd=agent_task_dir,
            env=env,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [
                self.args.claude_bin,
                "mcp",
                "add",
                "--transport",
                "http",
                "roboclaws",
                self.args.client_url,
            ],
            cwd=agent_task_dir,
            env=env,
            check=True,
        )
        mcp_config_path = agent_task_dir / "claude-mcp-config.json"
        mcp_config_path.write_text(
            json.dumps(
                {
                    "mcpServers": {
                        "roboclaws": {
                            "type": "http",
                            "url": self.args.client_url,
                        }
                    }
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        shutil.copyfile(mcp_config_path, self.run_dir / "claude-mcp-config.json")

        print("==> launching Claude Code print mode with full permissions")
        if self.args.claude_provider_summary != "system defaults":
            print(f"==> Claude Code provider for this run: {self.args.claude_provider_summary}")
        print(f"==> kickoff: {self.args.kickoff_prompt}")
        version_proc = subprocess.run(
            [self.args.claude_bin, "--version"],
            cwd=agent_task_dir,
            env=env,
            check=False,
            capture_output=True,
            text=True,
        )
        version_text = (
            (getattr(version_proc, "stdout", "") or "")
            + (getattr(version_proc, "stderr", "") or "")
        ).strip()
        if version_text:
            (self.run_dir / "claude-version.txt").write_text(version_text + "\n", encoding="utf-8")

        command = [
            self.args.claude_bin,
            "-p",
            "--verbose",
            "--output-format",
            "stream-json",
            "--mcp-config",
            (
                "/workspace/task/claude-mcp-config.json"
                if container_isolated
                else str(mcp_config_path.resolve())
            ),
            "--strict-mcp-config",
            "--bare",
            "--no-session-persistence",
            *self.args.claude_model_arg,
            *FULL_PERMISSION_ARGS,
            self.args.kickoff_prompt,
        ]
        (self.run_dir / "claude-command.txt").write_text(
            " ".join(_shell_quote(item) for item in command) + "\n",
            encoding="utf-8",
        )
        status = _run_and_tee(
            command,
            cwd=agent_task_dir,
            stdout_path=self.run_dir / "claude-events.jsonl",
            stderr_path=self.run_dir / "claude.stderr.log",
            env=env,
        )
        self._mark_timing("claude_exec_end")
        if status != 0:
            failure = classify_live_agent_failure(
                self.run_dir / "claude-events.jsonl",
                self.run_dir / "claude.stderr.log",
                exit_status=status,
            )
            raise LiveAgentRunFailure(
                f"Claude Code failed after one live-agent turn: {failure.reason}",
                failure,
            )

    def _configure_provider_timing_proxy(self, env: dict[str, str]) -> None:
        if not provider_timing_proxy_enabled(env):
            self.live_timing["provider_timing_proxy"] = {"enabled": False}
            return
        upstream_base_url = env.get(PROVIDER_TIMING_PROXY_UPSTREAM_ENV) or env.get(
            "ANTHROPIC_BASE_URL",
            "",
        )
        if not upstream_base_url:
            raise RuntimeError("ROBOCLAWS_PROVIDER_TIMING_PROXY=1 requires ANTHROPIC_BASE_URL")
        provider_profile = _first_provider_summary_token(self.args.claude_provider_summary)
        handle = asyncio.run(
            start_provider_timing_proxy(
                repo_root=self.args.repo_root,
                run_dir=self.run_dir,
                upstream_base_url=upstream_base_url,
                agent_engine="claude-code",
                provider_profile=provider_profile,
                model=_model_from_claude_args(self.args.claude_model_arg),
            )
        )
        proxy_base_url = replace_base_url_origin(upstream_base_url, bind_url=handle.bind_url)
        env["ANTHROPIC_BASE_URL"] = proxy_base_url
        env[PROVIDER_TIMING_PROXY_UPSTREAM_ENV] = upstream_base_url
        self.provider_timing_proxy = handle
        self.live_timing["provider_timing_proxy"] = {
            "enabled": True,
            "agent_engine": "claude-code",
            "provider_profile": provider_profile,
            "upstream_base_url": upstream_base_url,
            "bind_url": handle.bind_url,
            "client_base_url": proxy_base_url,
            "metrics_path": str(handle.metrics_path),
        }

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
        run_id = _household_run_id(self.args)
        task_intent = _household_intent(self.args)
        open_ended_task = task_intent == "open-ended"
        checker_profile = str(getattr(self.args, "checker_profile", "") or self.args.profile)
        checker_visual_args = list(self.args.checker_visual_arg)
        if open_ended_task:
            checker_visual_args = without_full_cleanup_checker_gates(checker_visual_args)
        intent_id = household_intent_id_for_checker(
            task_intent=task_intent,
            open_ended_task=open_ended_task,
        )
        checker_policy_args = checker_flags_for_household_intent(
            intent_id=intent_id,
            profile=checker_profile,
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
            run_id,
            "--expect-backend",
            self.args.backend,
            "--expect-policy",
            self.args.policy,
            "--expect-profile",
            checker_profile,
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
    ) -> str:
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
        source_error = ""
        try:
            payload["mcp_trace_timing"] = _mcp_trace_timing(self.run_dir)
        except ValueError as exc:
            source_error = f"live_timing_source_error: {exc}"
            payload["live_timing_source_error"] = source_error
            if phase == "finished" and exit_status == 0:
                payload["phase"] = "failed"
                payload["exit_status"] = 1
                payload["reason"] = source_error
            payload["mcp_trace_timing"] = {"available": False, "source_error": str(exc)}
        self.timing_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        write_model_call_metrics_jsonl(
            self.run_dir / "model_call_metrics.jsonl",
            extract_model_call_metrics(self.run_dir, live_timing=payload),
        )
        return source_error

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

    def _cleanup_provider_timing_proxy(self) -> None:
        if self.provider_timing_proxy is None:
            return
        try:
            asyncio.run(stop_provider_timing_proxy(self.provider_timing_proxy.process))
        finally:
            self.provider_timing_proxy = None

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
        payload.update(self.run_lease.status_fields())
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


def _runner_timing_breakdown(timing: dict[str, object], finished_at: float) -> dict[str, object]:
    started = _float_or_none(timing.get("started_at_epoch"))
    claude_start = _float_or_none(timing.get("claude_exec_start_epoch"))
    claude_end = _float_or_none(timing.get("claude_exec_end_epoch"))
    checker_start = _float_or_none(timing.get("checker_start_epoch"))
    checker_end = _float_or_none(timing.get("checker_end_epoch"))
    server_start = _float_or_none(timing.get("server_start_epoch"))
    server_ready = _float_or_none(timing.get("server_ready_epoch"))
    server_finished = _float_or_none(timing.get("server_finished_epoch"))
    total = _round_duration(finished_at - started) if started is not None else None

    segments: dict[str, float] = {}
    if started is not None and claude_start is not None:
        segments["pre_claude_setup_s"] = _round_duration(claude_start - started)
    if claude_start is not None and claude_end is not None:
        segments["claude_exec_elapsed_s"] = _round_duration(claude_end - claude_start)
    if claude_end is not None and server_finished is not None:
        segments["post_claude_server_wait_s"] = _round_duration(server_finished - claude_end)
    if checker_start is not None and checker_end is not None:
        segments["checker_elapsed_s"] = _round_duration(checker_end - checker_start)
    if checker_end is not None:
        segments["final_overhead_s"] = _round_duration(finished_at - checker_end)
    if server_start is not None and server_ready is not None:
        segments["server_startup_s"] = _round_duration(server_ready - server_start)

    partition_keys = (
        "pre_claude_setup_s",
        "claude_exec_elapsed_s",
        "post_claude_server_wait_s",
        "checker_elapsed_s",
        "final_overhead_s",
    )
    accounted = sum(segments.get(key, 0.0) for key in partition_keys)
    breakdown: dict[str, object] = {"total_elapsed_s": total, **segments}
    if total is not None:
        breakdown["accounted_elapsed_s"] = _round_duration(accounted)
        breakdown["unaccounted_elapsed_s"] = _round_duration(max(0.0, total - accounted))
        breakdown["accounting_note"] = (
            "The partitioned runner buckets sum to total wall time. MCP trace timing "
            "runs inside claude_exec_elapsed_s and is reported separately to avoid "
            "double counting concurrent server work."
        )
    return breakdown


def _mcp_trace_timing(run_dir: Path) -> dict[str, object]:
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


def _read_jsonl_path(path: Path) -> list[dict[str, object]]:
    if not path.is_file():
        return []
    events: list[dict[str, object]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1
    ):
        if not line.strip():
            continue
        source = f"{path}:{line_number}"
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Claude live source {source}: invalid JSON: {exc.msg}") from exc
        if isinstance(item, dict):
            events.append(item)
        else:
            raise ValueError(f"Claude live source {source}: non-object JSON: {type(item).__name__}")
    return events


def _float_or_none(value: object) -> float | None:
    try:
        return float(value)
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
    run_id: str,
    skill_name: str,
) -> tuple[Path, Path]:
    workspace = _agent_workspace_root(repo_root=repo_root, run_id=run_id)
    task_dir = workspace / "task"
    skills_dir = workspace / "skills"
    task_dir.mkdir(parents=True, exist_ok=True)
    skills_dir.mkdir(parents=True, exist_ok=True)
    for name in ("AGENTS.md", "CLAUDE.md"):
        (workspace / name).unlink(missing_ok=True)
        (task_dir / name).unlink(missing_ok=True)
    skill_link = skills_dir / skill_name
    if skill_link.exists() or skill_link.is_symlink():
        if skill_link.is_dir() and not skill_link.is_symlink():
            shutil.rmtree(skill_link)
        else:
            skill_link.unlink()
    skill_link.symlink_to(repo_root / "skills" / skill_name, target_is_directory=True)
    task_skills_link = task_dir / "skills"
    if task_skills_link.exists() or task_skills_link.is_symlink():
        if task_skills_link.is_dir() and not task_skills_link.is_symlink():
            shutil.rmtree(task_skills_link)
        else:
            task_skills_link.unlink()
    task_skills_link.symlink_to(Path("..") / "skills", target_is_directory=True)
    (task_dir / "README.md").write_text(
        "# Roboclaws Molmo Cleanup Agent Workspace\n\n"
        f"Read `skills/{skill_name}/SKILL.md`, then use the roboclaws MCP tools.\n",
        encoding="utf-8",
    )
    return workspace, task_dir


def _agent_workspace_root(*, repo_root: Path, run_id: str) -> Path:
    workspace_env = os.environ.get("ROBOCLAWS_CODE_AGENT_WORKSPACE") or os.environ.get(
        "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"
    )
    if not workspace_env:
        return Path(tempfile.mkdtemp(prefix=f"roboclaws-{run_id}-agent-"))

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


def _model_from_claude_args(args: list[str]) -> str:
    for index, item in enumerate(args):
        if item == "--model" and index + 1 < len(args):
            return args[index + 1]
    return ""


def _first_provider_summary_token(summary: str) -> str:
    return summary.split(" ", 1)[0] if summary and summary != "system defaults" else ""


if __name__ == "__main__":
    raise SystemExit(main())

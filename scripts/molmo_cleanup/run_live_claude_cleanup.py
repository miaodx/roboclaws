#!/usr/bin/env python3
"""Run a Molmo cleanup Claude Code live-agent session non-interactively."""

from __future__ import annotations

import argparse
import fcntl
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

from roboclaws.agents.drivers.household_live import household_cleanup_server_argv
from roboclaws.agents.live_status import LiveAgentFailure, classify_live_agent_failure
from roboclaws.household.task_intent import (
    TASK_INTENT_MODE_CUSTOM,
    TASK_INTENT_MODE_DEFAULT,
    normalize_task_intent_mode,
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
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--client-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--lock-path", type=Path, required=True)
    parser.add_argument("--claude-bin", required=True)
    parser.add_argument("--claude-provider-summary", default="system defaults")
    parser.add_argument("--server-startup-timeout-s", type=float, default=600.0)
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--task-intent-mode", default=TASK_INTENT_MODE_DEFAULT)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--min-generated-mess-count", required=True)
    parser.add_argument("--profile", required=True)
    parser.add_argument("--server-arg", action="append", default=[])
    parser.add_argument("--claude-model-arg", action="append", default=[])
    parser.add_argument("--claude-env", action="append", default=[])
    parser.add_argument("--checker-visual-arg", action="append", default=[])
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
        self.started_at_epoch = time.time()
        self.server_proc: subprocess.Popen[bytes] | None = None
        self.lock_file = None

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
            self._cleanup_server()
            return 130
        except LiveAgentRunFailure as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, **exc.failure.status_fields())
            self._cleanup_server()
            return 1
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, reason=str(exc))
            self._cleanup_server()
            return 1

        self._write_status("finished", 0)
        return 0

    def _acquire_lock(self) -> None:
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
                },
                sort_keys=True,
            )
            + "\n"
        )
        lock_file.flush()
        self.lock_file = lock_file

    def _start_server(self) -> None:
        print("==> Claude Code Molmo cleanup runner")
        print(f"    repo    : {self.args.repo_root}")
        print(f"    run dir : {self.run_dir}")
        print(f"    MCP URL : {self.args.client_url}")

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
                return
            time.sleep(0.5)
        raise RuntimeError(
            f"cleanup MCP server did not become ready at {self.args.host}:{self.args.port} "
            f"within {self.args.server_startup_timeout_s:g}s"
        )

    def _run_claude(self) -> None:
        self._write_status("running-claude")
        env = os.environ.copy()
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE", "1")
        for item in self.args.claude_env:
            key, sep, value = item.partition("=")
            if not sep:
                raise RuntimeError(f"invalid --claude-env value: {item!r}")
            env[key] = value
        agent_workspace, agent_task_dir = _prepare_agent_workspace(
            repo_root=self.args.repo_root,
            task_name="household-cleanup",
            skill_name="molmo-realworld-cleanup",
        )
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_TASK", "household-cleanup")
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS", "molmo-realworld-cleanup")
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

    def _wait_for_server_finish(self) -> None:
        assert self.server_proc is not None
        self._write_status("waiting-for-server-finish")
        print("==> waiting for cleanup MCP server to finish after agent done")
        status = self.server_proc.wait()
        self.server_proc = None
        if status != 0:
            raise RuntimeError(f"cleanup MCP server exited with status {status}")

    def _check_result(self) -> None:
        self._write_status("checking-result")
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
        if self.args.profile in {
            "smoke",
            "world-oracle-labels",
            "camera-grounded-labels",
            "camera-raw-fpv",
        }:
            if custom_task:
                _append_missing_checker_flag(checker_args, "--allow-partial-cleanup")
            else:
                checker_args.append("--require-clean-agent-run")
        checker_args.append(str(run_result))

        status = _run_and_tee(
            checker_args,
            cwd=self.args.repo_root,
            stdout_path=self.run_dir / "checker.log",
            stderr_path=self.run_dir / "checker.log",
            env=os.environ.copy(),
        )
        if status != 0:
            raise RuntimeError(f"cleanup checker exited with status {status}")
        print(f"==> report: {self.run_dir / 'report.html'}")

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
    task_name: str,
    skill_name: str,
) -> tuple[Path, Path]:
    workspace = _agent_workspace_root(repo_root=repo_root, task_name=task_name)
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


def _agent_workspace_root(*, repo_root: Path, task_name: str) -> Path:
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


if __name__ == "__main__":
    raise SystemExit(main())

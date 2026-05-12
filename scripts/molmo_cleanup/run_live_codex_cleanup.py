#!/usr/bin/env python3
"""Run a Molmo cleanup Codex live-agent session inside a detached shell."""

from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import BinaryIO

FULL_PERMISSION_ARG = "--dangerously-bypass-approvals-and-sandbox"
SERVER_SCRIPT = "examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py"
CHECKER_SCRIPT = "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py"


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
    parser.add_argument("--codex-bin", required=True)
    parser.add_argument("--codex-model", default="")
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", required=True)
    parser.add_argument("--policy", required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--min-generated-mess-count", required=True)
    parser.add_argument("--evidence", required=True)
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
        self.started_at_epoch = time.time()
        self.server_proc: subprocess.Popen[bytes] | None = None

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._write_status("starting-server")
            self._start_server()
            self._wait_for_mcp_ready()
            self._run_codex()
            self._wait_for_server_finish()
            self._check_result()
        except KeyboardInterrupt:
            self._write_status("failed", 130)
            self._cleanup_server()
            return 130
        except Exception as exc:
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1)
            self._cleanup_server()
            return 1

        self._write_status("finished", 0)
        return 0

    def _start_server(self) -> None:
        print("==> detached Codex Molmo cleanup runner")
        print(f"    repo    : {self.args.repo_root}")
        print(f"    run dir : {self.run_dir}")
        print(f"    MCP URL : {self.args.client_url}")

        probe_host = _probe_host(self.args.host)
        if _port_accepting(probe_host, self.args.port):
            raise RuntimeError(
                f"TCP port {self.args.host}:{self.args.port} is already in use before server start"
            )

        command = [
            str(self.args.repo_root / ".venv/bin/python"),
            SERVER_SCRIPT,
            *self.args.server_arg,
        ]
        self.server_proc = subprocess.Popen(command, cwd=self.args.repo_root)
        (self.run_dir / "server.pid").write_text(f"{self.server_proc.pid}\n", encoding="utf-8")

    def _wait_for_mcp_ready(self) -> None:
        assert self.server_proc is not None
        probe_host = _probe_host(self.args.host)
        deadline = time.monotonic() + 120.0
        while time.monotonic() < deadline:
            if self.server_proc.poll() is not None:
                raise RuntimeError("cleanup MCP server exited before becoming ready")
            if _port_accepting(probe_host, self.args.port):
                return
            time.sleep(0.5)
        raise RuntimeError(
            f"cleanup MCP server did not become ready at {self.args.host}:{self.args.port}"
        )

    def _run_codex(self) -> None:
        self._write_status("running-codex")
        subprocess.run(
            ["codex", "mcp", "remove", "roboclaws"],
            cwd=self.args.repo_root,
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["codex", "mcp", "add", "roboclaws", "--url", self.args.client_url],
            cwd=self.args.repo_root,
            check=True,
        )

        print("==> launching Codex exec with full permissions")
        if self.args.codex_model:
            print(f"==> Codex model override for this run: {self.args.codex_model}")
        print(f"==> kickoff: {self.args.kickoff_prompt}")

        command = [
            self.args.codex_bin,
            "exec",
            "--json",
            "--output-last-message",
            str(self.run_dir / "codex-last-message.md"),
            *self.args.codex_model_arg,
            FULL_PERMISSION_ARG,
            "--cd",
            str(self.args.repo_root),
            self.args.kickoff_prompt,
        ]
        (self.run_dir / "codex-command.txt").write_text(
            " ".join(_shell_quote(item) for item in command) + "\n",
            encoding="utf-8",
        )
        status = _run_and_tee(
            command,
            cwd=self.args.repo_root,
            stdout_path=self.run_dir / "codex-events.jsonl",
            stderr_path=self.run_dir / "codex.stderr.log",
        )
        if status != 0:
            raise RuntimeError(f"Codex exec exited with status {status}")

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
            "--expect-mcp-server",
            "molmo_cleanup_realworld",
            "--min-generated-mess-count",
            self.args.min_generated_mess_count,
            "--require-agent-driven",
            "--require-advisory-scoring",
            *self.args.checker_visual_arg,
        ]
        if self.args.evidence == "visual":
            checker_args.append("--require-clean-agent-run")
        checker_args.append(str(run_result))

        status = _run_and_tee(
            checker_args,
            cwd=self.args.repo_root,
            stdout_path=self.run_dir / "checker.log",
            stderr_path=self.run_dir / "checker.log",
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

    def _write_status(self, phase: str, exit_status: int | None = None) -> None:
        payload: dict[str, object] = {
            "phase": phase,
            "started_at_epoch": self.started_at_epoch,
        }
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
) -> int:
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert proc.stdout is not None
    assert proc.stderr is not None

    with stdout_path.open("ab") as stdout_file:
        if stdout_path == stderr_path:
            stderr_file_context = stdout_file
            stderr_thread = threading.Thread(
                target=_tee_stream,
                args=(proc.stderr, [stderr_file_context, sys.stderr.buffer]),
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
            output.write(chunk)
            output.flush()


def _port_accepting(host: str, port: int, *, timeout_s: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _probe_host(host: str) -> str:
    return "127.0.0.1" if host in {"0.0.0.0", "::"} else host


def _shell_quote(value: str) -> str:
    if not value:
        return "''"
    safe = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_@%+=:,./-"
    if all(char in safe for char in value):
        return value
    return "'" + value.replace("'", "'\"'\"'") + "'"


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

from roboclaws.household.agibot_map_build_mcp_server import MCP_SERVER_NAME
from scripts.molmo_cleanup.run_live_codex_cleanup import (
    CODEX_CLEANUP_MCP_SERVER_NAME,
    CODEX_LIVE_NO_PLAN_TOOL_INSTRUCTION,
    FULL_PERMISSION_ARG,
    _agent_workspace_root,
    _codex_event_summary,
    _docker_isolated_workspace_enabled,
    _port_accepting,
    _prepare_agent_workspace,
    _probe_host,
    _run_and_tee,
    _shell_quote,
)

SERVER_SCRIPT = "examples/molmo_cleanup/agibot_semantic_map_build_agent_server.py"
AGIBOT_MAP_BUILD_SKILL = "molmo-realworld-cleanup"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a live Codex semantic-map-build pilot against Agibot MCP tools."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--status-path", type=Path, required=True)
    parser.add_argument("--client-url", required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--tmux-session", default="")
    parser.add_argument("--codex-bin", required=True)
    parser.add_argument("--codex-model", default="")
    parser.add_argument("--codex-provider-summary", default="system defaults")
    parser.add_argument("--server-startup-timeout-s", type=float, default=600.0)
    parser.add_argument("--kickoff-prompt", required=True)
    parser.add_argument("--backend", default="agibot_gdk")
    parser.add_argument("--policy", default="codex_agent")
    parser.add_argument("--task", required=True)
    parser.add_argument("--codex-model-arg", action="append", default=[])
    parser.add_argument("--server-arg", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    runner = LiveCodexAgibotMapBuildRunner(args)
    return runner.run()


class LiveCodexAgibotMapBuildRunner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.run_dir = args.run_dir
        self.status_path = args.status_path
        self.server_proc: subprocess.Popen[bytes] | None = None

    def run(self) -> int:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        try:
            self._write_status("starting-server")
            self._start_server()
            self._wait_for_mcp_ready()
            self._write_status("running-codex")
            self._run_codex()
            self._write_status("waiting-for-server-finish")
            self._wait_for_server_finish()
            self._check_result()
        except KeyboardInterrupt:
            self._write_status("failed", 130, reason="keyboard_interrupt")
            self._cleanup_server()
            return 130
        except Exception as exc:  # noqa: BLE001
            print(f"error: {exc}", file=sys.stderr)
            self._write_status("failed", 1, reason=str(exc))
            self._cleanup_server()
            return 1
        self._write_status("finished", 0)
        return 0

    def _start_server(self) -> None:
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
        self.server_proc = subprocess.Popen(
            command,
            cwd=self.args.repo_root,
            env=os.environ.copy(),
        )
        (self.run_dir / "server.pid").write_text(f"{self.server_proc.pid}\n", encoding="utf-8")

    def _wait_for_mcp_ready(self) -> None:
        assert self.server_proc is not None
        probe_host = _probe_host(self.args.host)
        import time

        deadline = time.monotonic() + self.args.server_startup_timeout_s
        while time.monotonic() < deadline:
            if self.server_proc.poll() is not None:
                raise RuntimeError("Agibot map-build MCP server exited before becoming ready")
            if _port_accepting(probe_host, self.args.port):
                return
            time.sleep(0.5)
        raise RuntimeError(
            f"Agibot map-build MCP server did not become ready at {self.args.host}:{self.args.port}"
        )

    def _run_codex(self) -> None:
        env = os.environ.copy()
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE", "1")
        env.setdefault(
            "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE",
            str(self.run_dir / "agent-docker-workspace"),
        )
        workspace = _agent_workspace_root(
            repo_root=self.args.repo_root,
            task_name="semantic-map-build",
            workspace=Path(env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"]),
        )
        agent_workspace, agent_task_dir = _prepare_agent_workspace(
            repo_root=self.args.repo_root,
            task_name="semantic-map-build",
            skill_name=AGIBOT_MAP_BUILD_SKILL,
            workspace=workspace,
        )
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_TASK", "semantic-map-build")
        env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS", AGIBOT_MAP_BUILD_SKILL)
        env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"] = str(agent_workspace)
        container_isolated = _docker_isolated_workspace_enabled(env)
        agent_cd = "/workspace/task" if container_isolated else str(agent_task_dir)
        last_message_cli_path = (
            "/workspace/task/codex-last-message.md"
            if container_isolated
            else str(agent_task_dir / "codex-last-message.md")
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

        prompt = _codex_agibot_map_build_prompt(self.args.kickoff_prompt)
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
        events_path = self.run_dir / "codex-events.jsonl"
        status = _run_and_tee(
            command,
            cwd=agent_task_dir,
            stdout_path=events_path,
            stderr_path=self.run_dir / "codex.stderr.log",
            env=env,
        )
        (self.run_dir / "codex_event_summary.json").write_text(
            json.dumps(_codex_event_summary(events_path), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if status != 0 and not (self.run_dir / "run_result.json").is_file():
            raise RuntimeError(f"Codex exec exited with status {status}")
        if not (self.run_dir / "run_result.json").is_file():
            raise RuntimeError("Codex exec ended without calling done")
        last_message = agent_task_dir / "codex-last-message.md"
        if last_message.is_file():
            last_message.replace(self.run_dir / "codex-last-message.md")

    def _wait_for_server_finish(self) -> None:
        assert self.server_proc is not None
        status = self.server_proc.wait()
        self.server_proc = None
        if status != 0:
            raise RuntimeError(f"Agibot map-build MCP server exited with status {status}")

    def _check_result(self) -> None:
        run_result = self.run_dir / "run_result.json"
        if not run_result.is_file():
            raise RuntimeError(f"live Agibot map-build run finished without {run_result}")
        payload = json.loads(run_result.read_text(encoding="utf-8"))
        if payload.get("mcp_server") != MCP_SERVER_NAME:
            raise RuntimeError(f"run_result has unexpected mcp_server: {payload.get('mcp_server')}")
        if payload.get("backend_variant") != "agibot_gdk":
            raise RuntimeError(
                f"run_result has unexpected backend_variant: {payload.get('backend_variant')}"
            )
        if payload.get("agent_driven") is not True:
            raise RuntimeError("run_result is not marked agent_driven=true")
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
    ) -> None:
        payload: dict[str, Any] = {"phase": phase}
        if reason:
            payload["reason"] = reason
        if exit_status is not None:
            payload["exit_status"] = exit_status
        self.status_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _codex_agibot_map_build_prompt(prompt: str) -> str:
    return (
        f"{CODEX_LIVE_NO_PLAN_TOOL_INSTRUCTION}\n\n"
        "Agibot semantic-map-build route: use the cleanup MCP server only. "
        "Call metric_map and fixture_hints first. Build a waypoint checklist from "
        "metric_map.inspection_waypoints. Visit public waypoint ids only with "
        "navigate_to_waypoint, then call observe. Do not invent coordinates, do not "
        "call raw Agibot/GDK/PNC tools, do not inspect private files, and do not use "
        "manipulation tools except to verify they remain blocked when needed. "
        "Call done after every selected public waypoint has either been observed or "
        "explicitly left for operator review.\n\n"
        f"{prompt}"
    )


if __name__ == "__main__":
    raise SystemExit(main())

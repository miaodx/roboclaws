#!/usr/bin/env python3
"""Run one experimental OpenAI Agents SDK Molmo cleanup live-agent session."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
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
    DEFAULT_MODEL_SERVICE_RETRY_ATTEMPTS,
    DEFAULT_MODEL_SERVICE_RETRY_SLEEP_S,
    DEFAULT_OPENAI_AGENTS_MAX_TURNS,
    MCP_CLIENT_SESSION_TIMEOUT_ENV,
    MODEL_SERVICE_RETRY_ATTEMPTS_ENV,
    MODEL_SERVICE_RETRY_SLEEP_ENV,
    OpenAIAgentsLiveRuntime,
)
from roboclaws.agents.live_runtime import LiveAgentMCPServer, LiveAgentRequest
from roboclaws.agents.live_status import LiveAgentFailure
from roboclaws.agents.prompts.household_cleanup import render_kickoff_prompt
from roboclaws.agents.provider_registry import (
    model_family_for_route_model,
    normalize_provider_route,
    provider_route_spec,
    route_capabilities_for_engine,
)
from roboclaws.household.realworld_mcp_server import (
    ROBOT_VIEW_CAPTURE_POLICIES,
    ROBOT_VIEW_CAPTURE_POLICY_FULL,
)
from roboclaws.household.report import runtime_timing_from_trace
from roboclaws.household.task_intent import (
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
from roboclaws.reports.live_performance import (
    extract_model_call_metrics,
    write_model_call_metrics_jsonl,
)

CHECKER_SCRIPT = "scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py"
REPORT_RERUN_COMMAND_ENV = "ROBOCLAWS_REPORT_RERUN_COMMAND"
DEFAULT_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS = 2
DEFAULT_MCP_CLIENT_SESSION_TIMEOUT_S = 30.0
AGENT_SDK_PERF_PROFILE_ENV = "ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE"
PROMPT_MODE_ENV = "ROBOCLAWS_OPENAI_AGENTS_PROMPT_MODE"
CONTINUATION_MODE_ENV = "ROBOCLAWS_OPENAI_AGENTS_CONTINUATION_MODE"
CONTEXT_SOFT_LIMIT_ENV = "ROBOCLAWS_OPENAI_AGENTS_CONTEXT_SOFT_LIMIT_TOKENS"
CONTEXT_HARD_LIMIT_ENV = "ROBOCLAWS_OPENAI_AGENTS_CONTEXT_HARD_LIMIT_TOKENS"
MODEL_INPUT_COMPACTION_ENV = "ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION"
MODEL_INPUT_COMPACTION_MIN_CHARS_ENV = "ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS"
RAW_FPV_IMAGE_MEMORY_ENV = "ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_IMAGE_MEMORY"
RAW_FPV_IMAGE_MEMORY_RETAIN_ENV = "ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_IMAGE_MEMORY_RETAIN"
CAMERA_GROUNDED_COMPOSITE_TOOLS_ENV = "ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_COMPOSITE_TOOLS"
ROBOT_VIEW_CAPTURE_POLICY_ENV = "ROBOCLAWS_OPENAI_AGENTS_ROBOT_VIEW_CAPTURE_POLICY"
MAX_OBSERVE_PER_WAYPOINT_ENV = "ROBOCLAWS_OPENAI_AGENTS_MAX_OBSERVE_PER_WAYPOINT"
RAW_FPV_CANDIDATE_BUDGET_ENV = "ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET"
RAW_FPV_REPEATED_FAILURE_LIMIT_ENV = "ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_REPEATED_FAILURE_LIMIT"
DONE_RETRY_BUDGET_ENV = "ROBOCLAWS_OPENAI_AGENTS_DONE_RETRY_BUDGET"
MOLMO_REALWORLD_CLEANUP_SKILL_RELATIVE_PATH = Path("skills/molmo-realworld-cleanup/SKILL.md")
MAX_AGENT_SDK_SKILL_CONTEXT_BYTES = 24_000


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
        default=None,
        help=(
            "Maximum OpenAI Agents SDK agent turns inside one runner invocation. "
            "This is not runner-side continuation."
        ),
    )
    parser.add_argument(
        "--incomplete-turn-continuation-attempts",
        type=int,
        default=None,
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
    parser.add_argument(
        "--agent-sdk-perf-profile",
        default="",
        help=(
            "Private OpenAI Agents SDK performance profile id. Known values: "
            "baseline, gpt_compact_v1, mimo_compact_v1, raw_fpv_budgeted_v1, custom."
        ),
    )
    parser.add_argument("--prompt-mode", default="")
    parser.add_argument("--continuation-mode", default="")
    parser.add_argument(
        "--model-input-compaction",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Opt in to the SDK call_model_input_filter compaction arm. This is private "
            "OpenAI Agents SDK candidate-I evidence and is disabled by default."
        ),
    )
    parser.add_argument("--model-input-compaction-min-chars", type=int, default=None)
    parser.add_argument(
        "--raw-fpv-image-memory",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Opt in to private Agent SDK Candidate-AA raw-FPV image-memory policy. "
            "This only compacts older image blocks before SDK model calls; reports and "
            "MCP traces keep full image artifacts."
        ),
    )
    parser.add_argument("--raw-fpv-image-memory-retain", type=int, default=None)
    parser.add_argument(
        "--camera-grounded-composite-tools",
        action=argparse.BooleanOptionalAction,
        default=None,
        help=(
            "Opt in to private Agent SDK Candidate-O MCP composite tools for "
            "camera-grounded-labels. The cleanup server enables the extra tool only "
            "for this SDK run."
        ),
    )
    parser.add_argument(
        "--robot-view-capture-policy",
        default="",
        help=(
            "Private Agent SDK Candidate-F robot-view report capture policy. "
            "Use action_timeline to keep before/after and cleanup action views while "
            "skipping report-only observe/scene_objects captures."
        ),
    )
    parser.add_argument("--context-soft-limit-tokens", type=int, default=None)
    parser.add_argument("--context-hard-limit-tokens", type=int, default=None)
    parser.add_argument("--max-observe-per-waypoint", type=int, default=None)
    parser.add_argument("--raw-fpv-candidate-budget", type=int, default=None)
    parser.add_argument("--raw-fpv-repeated-failure-limit", type=int, default=None)
    parser.add_argument("--done-retry-budget", type=int, default=None)
    parser.add_argument(
        "--model-service-retry-attempts",
        type=int,
        default=None,
        help=(
            "Bounded same-provider Agent SDK model-request retries for classified "
            "transient provider/model service failures. Set 0 to disable."
        ),
    )
    parser.add_argument(
        "--model-service-retry-sleep-s",
        type=float,
        default=None,
        help="Delay between Agent SDK model-service retry attempts.",
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
        self.agent_sdk_perf_profile = _resolve_agent_sdk_perf_profile(args)
        self.skill_context = _load_agent_sdk_skill_context(
            args.repo_root,
            skill_name="molmo-realworld-cleanup",
        )
        self.initial_kickoff_prompt = _profiled_kickoff_prompt(
            args,
            profile=self.agent_sdk_perf_profile,
        )
        self.live_timing: dict[str, Any] = {
            "schema": "molmo_live_timing_v1",
            "started_at_epoch": self.started_at_epoch,
            "surface": "household-world",
            "intent": _intent_for_task_name(getattr(args, "task_name", "")),
            "task_name": getattr(args, "task_name", ""),
            "task_intent_mode": _task_intent_mode_for_timing(args),
            "evidence_lane": getattr(args, "profile", ""),
            "profile": getattr(args, "profile", ""),
            "backend": getattr(args, "backend", ""),
            "policy": getattr(args, "policy", ""),
            "runtime": "openai-agents-live",
            "provider_profile": getattr(args, "provider_profile", ""),
            "wire_api": self.agent_sdk_perf_profile["wire_api"],
            "model": getattr(args, "model", ""),
            "cache_tools_list": bool(getattr(args, "cache_tools_list", True)),
            "kickoff_prompt_chars": len(self.initial_kickoff_prompt),
            "kickoff_prompt_estimated_tokens": _estimated_tokens_from_chars(
                len(self.initial_kickoff_prompt)
            ),
            "kickoff_prompt_source": _kickoff_prompt_source(args, self.agent_sdk_perf_profile),
            "kickoff_prompt_stable_prefix": _stable_prefix_packet(
                self.initial_kickoff_prompt,
                self.skill_context,
                self.agent_sdk_perf_profile,
            ),
            "mcp_client_session_timeout_s": _round_duration(
                max(0.0, float(getattr(args, "mcp_client_session_timeout_s", 0.0) or 0.0))
            ),
            "agent_sdk_perf_profile": self.agent_sdk_perf_profile,
            "agent_sdk_camera_grounded_composite_tools": (
                self.agent_sdk_perf_profile["camera_grounded_composite_tools"]
            ),
            "agent_sdk_robot_view_capture_policy": (
                self.agent_sdk_perf_profile["robot_view_capture_policy"]
            ),
            "prompt_profile_id": self.agent_sdk_perf_profile["profile_id"],
            "agent_sdk_skill_context": _skill_context_timing_summary(self.skill_context),
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
        if _camera_grounded_composite_tools_enabled_for_run(
            self.agent_sdk_perf_profile,
            evidence_lane=str(getattr(self.args, "profile", "") or ""),
        ):
            command.append("--agent-sdk-camera-grounded-composite-tools")
        robot_view_capture_policy = self.agent_sdk_perf_profile["robot_view_capture_policy"]
        if robot_view_capture_policy["policy"] != ROBOT_VIEW_CAPTURE_POLICY_FULL:
            command.extend(["--robot-view-capture-policy", robot_view_capture_policy["policy"]])
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
            max_attempts=int(self.agent_sdk_perf_profile["max_continuations"])
        )
        runtime = OpenAIAgentsLiveRuntime()
        prompt = self.initial_kickoff_prompt
        attempt_index = 0
        result = None
        attempts: list[dict[str, Any]] = []
        while True:
            preflight_failure = _budget_failure_from_run_state(
                self.run_dir,
                self.live_timing,
                self.agent_sdk_perf_profile,
            )
            if preflight_failure is not None:
                self.live_timing["agent_sdk_budget_terminal"] = preflight_failure.status_fields()
                raise LiveAgentRunFailure(
                    f"OpenAI Agents SDK budget guard stopped before attempt {attempt_index}: "
                    f"{preflight_failure.reason}",
                    preflight_failure,
                )
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
            budget_failure = _budget_failure_from_run_state(
                self.run_dir,
                self.live_timing,
                self.agent_sdk_perf_profile,
            )
            if budget_failure is not None:
                self.live_timing["agent_sdk_budget_terminal"] = budget_failure.status_fields()
                raise LiveAgentRunFailure(
                    f"OpenAI Agents SDK budget guard stopped after attempt {attempt_index}: "
                    f"{budget_failure.reason}",
                    budget_failure,
                )
            continuation_prompt = recovery_policy.continuation_prompt(
                original_prompt=self.initial_kickoff_prompt,
                result=result,
                run_dir=self.run_dir,
                attempt_index=attempt_index,
                profile=self.agent_sdk_perf_profile,
                context_metrics=_context_metrics(self.run_dir, self.live_timing),
            )
            if continuation_prompt is None:
                break
            attempt_summary["recovery_action"] = "continue"
            attempt_summary["recovery_reason"] = recovery_policy.reason
            attempt_summary["continuation_prompt_chars"] = len(continuation_prompt)
            attempt_summary["continuation_prompt_estimated_tokens"] = _estimated_tokens_from_chars(
                len(continuation_prompt)
            )
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
            failure = _failure_from_sdk_result(
                result,
                run_dir=self.run_dir,
                timing=self.live_timing,
                profile=self.agent_sdk_perf_profile,
            )
            if result.reason == "agent_sdk_turn_budget_exceeded":
                self.live_timing["agent_sdk_budget_terminal"] = failure.status_fields()
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
            "openai_agents_spans": self.run_dir / "openai-agents-spans.jsonl",
            "openai_agents_skill_context": self.run_dir / "openai-agents-skill-context.json",
        }
        if attempt_index:
            artifact_paths.update(
                {
                    "openai_agents_events": self.run_dir
                    / f"openai-agents-events.continuation-{attempt_index}.jsonl",
                    "openai_agents_trace": self.run_dir
                    / f"openai-agents-trace.continuation-{attempt_index}.json",
                    "openai_agents_spans": self.run_dir
                    / f"openai-agents-spans.continuation-{attempt_index}.jsonl",
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
            max_turns=int(self.agent_sdk_perf_profile["max_turns"]),
            one_turn=True,
            metadata={
                "provider_profile": self.args.provider_profile,
                "max_turns": int(self.agent_sdk_perf_profile["max_turns"]),
                "attempt_index": attempt_index,
                "attempt_role": "continuation" if attempt_index else "initial",
                "cache_tools_list": bool(self.agent_sdk_perf_profile["cache_tools_list"]),
                "mcp_client_session_timeout_s": float(
                    self.agent_sdk_perf_profile["mcp_client_session_timeout_s"] or 0.0
                ),
                "model_service_retry_attempts": int(
                    self.agent_sdk_perf_profile["model_service_retry_attempts"] or 0
                ),
                "model_service_retry_sleep_s": float(
                    self.agent_sdk_perf_profile["model_service_retry_sleep_s"] or 0.0
                ),
                "agent_sdk_perf_profile": self.agent_sdk_perf_profile,
                "sdk_model_settings": self.agent_sdk_perf_profile["sdk_model_settings"],
                "sdk_run_config": self.agent_sdk_perf_profile["sdk_run_config"],
                "skill_context": self.skill_context,
                "surface": "household-world",
                "intent": _intent_for_task_name(getattr(self.args, "task_name", "")),
                "task_name": getattr(self.args, "task_name", ""),
                "task_intent_mode": _task_intent_mode_for_timing(self.args),
                "evidence_lane": getattr(self.args, "profile", ""),
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
        open_ended_task = task_intent == "open-ended"
        checker_visual_args = list(self.args.checker_visual_arg)
        if open_ended_task:
            checker_visual_args = _without_full_cleanup_checker_gates(checker_visual_args)
        intent_id = household_intent_id_for_checker(
            task_name=task_name,
            task_intent=task_intent,
            open_ended_task=open_ended_task,
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
        payload["openai_agents_span_metrics"] = _openai_agents_span_metrics(self.run_dir)
        payload["model_service_fallback_metrics"] = _model_service_fallback_metrics(self.run_dir)
        payload["model_input_filter_metrics"] = _model_input_filter_metrics(self.run_dir)
        payload["context_metrics"] = _context_metrics(self.run_dir, payload)
        payload["cache_metrics"] = _cache_metrics(payload["context_metrics"], payload)
        payload["context_growth_metrics"] = _context_growth_metrics(self.run_dir, payload)
        payload["model_or_sdk_unattributed_s"] = _model_or_sdk_unattributed_seconds(payload)
        payload["timeline"] = _live_timing_timeline(payload)
        self.timing_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        write_model_call_metrics_jsonl(
            self.run_dir / "model_call_metrics.jsonl",
            extract_model_call_metrics(self.run_dir, live_timing=payload),
        )

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
        profile: dict[str, Any] | None = None,
        context_metrics: dict[str, Any] | None = None,
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
        profile = profile or {}
        context_metrics = context_metrics or {}
        continuation_mode = str(profile.get("continuation_mode") or "repeat_full_prompt")
        total_input_tokens = _int_or_none(context_metrics.get("total_input_tokens"))
        soft_limit = _int_or_none(profile.get("context_soft_limit_tokens"))
        if continuation_mode == "state_summary_only" or (
            soft_limit is not None
            and total_input_tokens is not None
            and total_input_tokens >= soft_limit
        ):
            return _compact_continuation_prompt(
                run_dir,
                profile=profile,
                context_metrics=context_metrics,
            )
        return f"{original_prompt.rstrip()}\n\n{self.continuation_suffix}\n"


def _resolve_agent_sdk_perf_profile(args: argparse.Namespace) -> dict[str, Any]:
    provider_profile = _normal_provider_profile(str(getattr(args, "provider_profile", "") or ""))
    model = str(getattr(args, "model", "") or "")
    model_family = _registry_model_family(provider_profile, model)
    route = provider_route_spec(provider_profile)
    profile_id, profile_source = _profile_id_with_source(args, provider_profile, model_family)
    defaults = _profile_defaults(profile_id)
    payload = {
        "schema": "agent_sdk_perf_profile_v1",
        "profile_id": profile_id,
        "source": profile_source,
        "provider_profile": provider_profile,
        "wire_api": _wire_api_for_provider_profile(provider_profile),
        "wire_source": route.wire_source,
        "route_status": route.status_for_engine("openai-agents-sdk"),
        "route_status_note": route.status_note,
        "route_capabilities": route_capabilities_for_engine(route, "openai-agents-sdk"),
        "model_family": model_family,
        "prompt_mode": _string_setting(
            args,
            "prompt_mode",
            PROMPT_MODE_ENV,
            default=defaults["prompt_mode"],
            allowed={"full", "compact", "raw_fpv_compact"},
        ),
        "continuation_mode": _string_setting(
            args,
            "continuation_mode",
            CONTINUATION_MODE_ENV,
            default=defaults["continuation_mode"],
            allowed={"repeat_full_prompt", "state_summary_only"},
        ),
        "max_turns": _positive_int_setting(
            args,
            "max_turns",
            "ROBOCLAWS_OPENAI_AGENTS_MAX_TURNS",
            default=defaults["max_turns"],
        ),
        "max_continuations": _int_setting(
            args,
            "incomplete_turn_continuation_attempts",
            "ROBOCLAWS_OPENAI_AGENTS_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS",
            default=defaults["max_continuations"],
        ),
        "cache_tools_list": bool(getattr(args, "cache_tools_list", True)),
        "mcp_client_session_timeout_s": _round_duration(
            max(0.0, float(getattr(args, "mcp_client_session_timeout_s", 0.0) or 0.0))
        ),
        "raw_fpv_candidate_budget": _int_setting(
            args,
            "raw_fpv_candidate_budget",
            RAW_FPV_CANDIDATE_BUDGET_ENV,
            default=defaults["raw_fpv_candidate_budget"],
            allow_none=True,
        ),
        "raw_fpv_repeated_failure_limit": _int_setting(
            args,
            "raw_fpv_repeated_failure_limit",
            RAW_FPV_REPEATED_FAILURE_LIMIT_ENV,
            default=defaults["raw_fpv_repeated_failure_limit"],
            allow_none=True,
        ),
        "done_retry_budget": _int_setting(
            args,
            "done_retry_budget",
            DONE_RETRY_BUDGET_ENV,
            default=defaults["done_retry_budget"],
            allow_none=True,
        ),
        "max_observe_per_waypoint": _int_setting(
            args,
            "max_observe_per_waypoint",
            MAX_OBSERVE_PER_WAYPOINT_ENV,
            default=defaults["max_observe_per_waypoint"],
            allow_none=True,
        ),
        "context_soft_limit_tokens": _int_setting(
            args,
            "context_soft_limit_tokens",
            CONTEXT_SOFT_LIMIT_ENV,
            default=defaults["context_soft_limit_tokens"],
            allow_none=True,
        ),
        "context_hard_limit_tokens": _int_setting(
            args,
            "context_hard_limit_tokens",
            CONTEXT_HARD_LIMIT_ENV,
            default=defaults["context_hard_limit_tokens"],
            allow_none=True,
        ),
        "model_input_compaction": _model_input_compaction_profile(args, defaults),
        "camera_grounded_composite_tools": _camera_grounded_composite_tools_profile(
            args,
            defaults,
        ),
        "robot_view_capture_policy": _robot_view_capture_policy_profile(args, defaults),
        "model_service_retry_attempts": _int_setting(
            args,
            "model_service_retry_attempts",
            MODEL_SERVICE_RETRY_ATTEMPTS_ENV,
            default=DEFAULT_MODEL_SERVICE_RETRY_ATTEMPTS,
        ),
        "model_service_retry_sleep_s": _float_setting(
            args,
            "model_service_retry_sleep_s",
            MODEL_SERVICE_RETRY_SLEEP_ENV,
            default=DEFAULT_MODEL_SERVICE_RETRY_SLEEP_S,
        ),
    }
    payload["sdk_model_settings"] = _sdk_model_settings_for_profile(payload)
    payload["sdk_run_config"] = _sdk_run_config_for_profile(payload)
    _validate_context_limits(payload)
    return payload


def _load_agent_sdk_skill_context(repo_root: Path, *, skill_name: str) -> dict[str, Any]:
    source_path = Path(repo_root) / MOLMO_REALWORLD_CLEANUP_SKILL_RELATIVE_PATH
    base_payload: dict[str, Any] = {
        "schema": "agent_sdk_skill_context_v1",
        "skill_name": skill_name,
        "source_path": str(source_path),
        "relative_path": str(MOLMO_REALWORLD_CLEANUP_SKILL_RELATIVE_PATH),
        "policy": "canonical_skill_markdown",
    }
    try:
        raw = source_path.read_bytes()
    except OSError as exc:
        return {
            **base_payload,
            "included": False,
            "reason": "source_unavailable",
            "error_type": exc.__class__.__name__,
        }
    truncated = raw[:MAX_AGENT_SDK_SKILL_CONTEXT_BYTES]
    text = truncated.decode("utf-8", errors="replace")
    return {
        **base_payload,
        "included": bool(text),
        "reason": "included" if text else "empty",
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "included_bytes": len(truncated),
        "truncated": len(raw) > len(truncated),
        "estimated_tokens": _estimated_tokens_from_chars(len(text)),
        "content": text,
    }


def _skill_context_timing_summary(skill_context: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in skill_context.items()
        if key
        in {
            "schema",
            "skill_name",
            "source_path",
            "relative_path",
            "policy",
            "included",
            "reason",
            "sha256",
            "bytes",
            "included_bytes",
            "truncated",
            "estimated_tokens",
            "error_type",
        }
    }


def _stable_prefix_packet(
    prompt: str,
    skill_context: dict[str, Any],
    profile: dict[str, Any],
) -> dict[str, Any]:
    skill_hash = str(skill_context.get("sha256") or "")
    prompt_prefix = str(prompt or "")[:2048]
    material = "\n".join(
        [
            str(skill_context.get("relative_path") or ""),
            skill_hash,
            str(profile.get("prompt_mode") or ""),
            str(profile.get("provider_profile") or ""),
            str(profile.get("wire_api") or ""),
            prompt_prefix,
        ]
    )
    return {
        "schema": "agent_sdk_stable_prefix_v1",
        "hash": hashlib.sha256(material.encode("utf-8")).hexdigest(),
        "material": "skill-path+skill-hash+prompt-mode+provider-profile+wire-api+prompt-prefix",
        "skill_context_sha256": skill_hash,
        "prompt_prefix_chars": len(prompt_prefix),
        "prompt_cache_retention": (profile.get("sdk_model_settings") or {}).get(
            "prompt_cache_retention"
        )
        or "",
    }


def _profile_id_with_source(
    args: argparse.Namespace,
    provider_profile: str,
    model_family: str,
) -> tuple[str, str]:
    cli_value = str(getattr(args, "agent_sdk_perf_profile", "") or "").strip()
    if cli_value:
        return _validate_profile_id(cli_value), "cli"
    env_value = os.environ.get(AGENT_SDK_PERF_PROFILE_ENV, "").strip()
    if env_value:
        return _validate_profile_id(env_value), "environment"
    return _validate_profile_id(_default_profile_id(provider_profile, model_family)), "default"


def _default_profile_id(_provider_profile: str, _model_family: str) -> str:
    return "baseline"


def _validate_profile_id(value: str) -> str:
    profile_id = value.strip()
    if profile_id not in {
        "baseline",
        "gpt_compact_v1",
        "mimo_compact_v1",
        "raw_fpv_budgeted_v1",
        "custom",
    }:
        raise ValueError(f"unsupported OpenAI Agents SDK performance profile '{value}'")
    return profile_id


def _profile_defaults(profile_id: str) -> dict[str, Any]:
    baseline = {
        "prompt_mode": "full",
        "continuation_mode": "repeat_full_prompt",
        "max_turns": DEFAULT_OPENAI_AGENTS_MAX_TURNS,
        "max_continuations": DEFAULT_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS,
        "raw_fpv_candidate_budget": None,
        "raw_fpv_repeated_failure_limit": None,
        "done_retry_budget": None,
        "max_observe_per_waypoint": None,
        "context_soft_limit_tokens": None,
        "context_hard_limit_tokens": None,
        "model_input_compaction": {
            "schema": "agent_sdk_model_input_compaction_v1",
            "enabled": False,
            "mode": "off",
            "min_chars": 1200,
            "raw_fpv_image_memory": {
                "schema": "agent_sdk_raw_fpv_image_memory_policy_v1",
                "enabled": False,
                "mode": "off",
                "retained_full_frame_limit": 0,
                "candidate_ids": [],
                "private_artifact_policy": (
                    "model-facing raw-FPV image memory only; MCP traces, reports, and "
                    "image artifacts remain complete"
                ),
            },
        },
        "camera_grounded_composite_tools": {
            "schema": "agent_sdk_camera_grounded_composite_tools_v1",
            "enabled": False,
            "tool_names": [],
            "candidate_ids": ["O"],
            "private_artifact_policy": (
                "SDK-private MCP tool addition only; default public MCP/profile tools remain "
                "unchanged"
            ),
        },
        "robot_view_capture_policy": {
            "schema": "agent_sdk_robot_view_capture_policy_v1",
            "policy": ROBOT_VIEW_CAPTURE_POLICY_FULL,
            "candidate_ids": [],
            "scope": "report-only robot-view capture",
            "private_artifact_policy": (
                "full report robot-view capture; default public route behavior unchanged"
            ),
        },
    }
    if profile_id in {"baseline", "custom"}:
        return baseline
    if profile_id == "gpt_compact_v1":
        return {
            **baseline,
            "prompt_mode": "compact",
            "continuation_mode": "state_summary_only",
            "max_continuations": 1,
            "done_retry_budget": 2,
            "max_observe_per_waypoint": 1,
            "context_soft_limit_tokens": 96_000,
            "context_hard_limit_tokens": 128_000,
        }
    if profile_id == "mimo_compact_v1":
        return {
            **baseline,
            "prompt_mode": "compact",
            "continuation_mode": "state_summary_only",
            "max_continuations": 1,
            "done_retry_budget": 2,
            "max_observe_per_waypoint": 1,
            "context_soft_limit_tokens": 64_000,
            "context_hard_limit_tokens": 96_000,
        }
    if profile_id == "raw_fpv_budgeted_v1":
        return {
            **baseline,
            "prompt_mode": "raw_fpv_compact",
            "continuation_mode": "state_summary_only",
            "max_turns": 40,
            "max_continuations": 1,
            "raw_fpv_candidate_budget": 24,
            "raw_fpv_repeated_failure_limit": 3,
            "done_retry_budget": 1,
            "max_observe_per_waypoint": 1,
            "context_soft_limit_tokens": 64_000,
            "context_hard_limit_tokens": 96_000,
            "model_input_compaction": {
                "schema": "agent_sdk_model_input_compaction_v1",
                "enabled": True,
                "mode": (
                    "public_tool_result_summary_v1+repeated_metric_map_delta_v1+"
                    "raw_fpv_image_memory_v1"
                ),
                "min_chars": 1200,
                "raw_fpv_image_memory": {
                    "schema": "agent_sdk_raw_fpv_image_memory_policy_v1",
                    "enabled": True,
                    "mode": "retain_latest_full_frame",
                    "retained_full_frame_limit": 1,
                    "candidate_ids": ["AA"],
                    "private_artifact_policy": (
                        "model-facing raw-FPV image memory only; MCP traces, reports, and "
                        "image artifacts remain complete"
                    ),
                },
            },
        }
    raise ValueError(f"unsupported OpenAI Agents SDK performance profile '{profile_id}'")


def _model_input_compaction_profile(
    args: argparse.Namespace,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    default_config = (
        defaults.get("model_input_compaction")
        if isinstance(defaults.get("model_input_compaction"), dict)
        else {}
    )
    default_enabled = bool(default_config.get("enabled", False))
    enabled = _bool_arg_setting(
        args,
        "model_input_compaction",
        MODEL_INPUT_COMPACTION_ENV,
        default=default_enabled,
    )
    min_chars = _int_setting(
        args,
        "model_input_compaction_min_chars",
        MODEL_INPUT_COMPACTION_MIN_CHARS_ENV,
        default=int(default_config.get("min_chars") or 1200),
    )
    raw_fpv_image_memory = _raw_fpv_image_memory_profile(args, default_config)
    mode_parts = []
    candidate_ids = []
    if enabled:
        mode_parts.extend(["public_tool_result_summary_v1", "repeated_metric_map_delta_v1"])
        candidate_ids.extend(["I", "N"])
    if raw_fpv_image_memory["enabled"]:
        mode_parts.append("raw_fpv_image_memory_v1")
        candidate_ids.append("AA")
    hook_enabled = enabled or bool(raw_fpv_image_memory["enabled"])
    return {
        "schema": "agent_sdk_model_input_compaction_v1",
        "enabled": hook_enabled,
        "mode": "+".join(mode_parts) if mode_parts else "off",
        "min_chars": int(min_chars or 1200),
        "candidate_ids": candidate_ids,
        "hook": "RunConfig.call_model_input_filter",
        "repeated_metric_map_delta": enabled,
        "raw_fpv_image_memory": raw_fpv_image_memory,
        "private_artifact_policy": (
            "model-facing compaction only; MCP traces, reports, and run artifacts remain complete"
        ),
    }


def _raw_fpv_image_memory_profile(
    args: argparse.Namespace,
    default_config: dict[str, Any],
) -> dict[str, Any]:
    default_policy = (
        default_config.get("raw_fpv_image_memory")
        if isinstance(default_config.get("raw_fpv_image_memory"), dict)
        else {}
    )
    default_enabled = bool(default_policy.get("enabled", False))
    enabled = _bool_arg_setting(
        args,
        "raw_fpv_image_memory",
        RAW_FPV_IMAGE_MEMORY_ENV,
        default=default_enabled,
    )
    retain = _int_setting(
        args,
        "raw_fpv_image_memory_retain",
        RAW_FPV_IMAGE_MEMORY_RETAIN_ENV,
        default=int(default_policy.get("retained_full_frame_limit") or (1 if enabled else 0)),
    )
    retain = max(1, int(retain or 1)) if enabled else 0
    return {
        "schema": "agent_sdk_raw_fpv_image_memory_policy_v1",
        "enabled": enabled,
        "mode": "retain_latest_full_frame" if enabled else "off",
        "retained_full_frame_limit": retain,
        "candidate_ids": ["AA"] if enabled else [],
        "private_artifact_policy": (
            "model-facing raw-FPV image memory only; MCP traces, reports, and image artifacts "
            "remain complete"
        ),
    }


def _camera_grounded_composite_tools_profile(
    args: argparse.Namespace,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    default_config = (
        defaults.get("camera_grounded_composite_tools")
        if isinstance(defaults.get("camera_grounded_composite_tools"), dict)
        else {}
    )
    default_enabled = bool(default_config.get("enabled", False))
    enabled = _bool_arg_setting(
        args,
        "camera_grounded_composite_tools",
        CAMERA_GROUNDED_COMPOSITE_TOOLS_ENV,
        default=default_enabled,
    )
    return {
        "schema": "agent_sdk_camera_grounded_composite_tools_v1",
        "enabled": enabled,
        "tool_names": ["observe_camera_grounded_candidates"] if enabled else [],
        "candidate_ids": ["O"],
        "scope": "camera-grounded-labels only",
        "hook": "cleanup MCP server private extra tool",
        "private_artifact_policy": (
            "SDK-private MCP tool addition only; default public MCP/profile tools remain unchanged"
        ),
    }


def _camera_grounded_composite_tools_enabled_for_run(
    profile: dict[str, Any],
    *,
    evidence_lane: str,
) -> bool:
    config = profile.get("camera_grounded_composite_tools")
    if not isinstance(config, dict) or not config.get("enabled"):
        return False
    return evidence_lane == "camera-grounded-labels"


def _robot_view_capture_policy_profile(
    args: argparse.Namespace,
    defaults: dict[str, Any],
) -> dict[str, Any]:
    default_config = (
        defaults.get("robot_view_capture_policy")
        if isinstance(defaults.get("robot_view_capture_policy"), dict)
        else {}
    )
    policy = _string_setting(
        args,
        "robot_view_capture_policy",
        ROBOT_VIEW_CAPTURE_POLICY_ENV,
        default=str(default_config.get("policy") or ROBOT_VIEW_CAPTURE_POLICY_FULL),
        allowed=set(ROBOT_VIEW_CAPTURE_POLICIES),
    )
    enabled = policy != ROBOT_VIEW_CAPTURE_POLICY_FULL
    return {
        "schema": "agent_sdk_robot_view_capture_policy_v1",
        "policy": policy,
        "candidate_ids": ["F"] if enabled else [],
        "scope": "report-only robot-view capture",
        "hook": "cleanup MCP server --robot-view-capture-policy",
        "private_artifact_policy": (
            "SDK-private report-capture reduction; before/after snapshots, cleanup action "
            "views, raw-FPV observe artifacts, traces, and reports remain complete"
            if enabled
            else "full report robot-view capture; default public route behavior unchanged"
        ),
    }


def _sdk_model_settings_for_profile(profile: dict[str, Any]) -> dict[str, Any]:
    wire_api = str(profile.get("wire_api") or "")
    provider_profile = str(profile.get("provider_profile") or "")
    profile_id = str(profile.get("profile_id") or "baseline")
    settings: dict[str, Any] = {
        "tool_choice": "auto",
        "parallel_tool_calls": False,
    }
    if wire_api == "responses":
        settings.update(
            {
                "truncation": "auto",
                "store": False,
            }
        )
        if provider_profile == "codex-env" and profile_id != "baseline":
            settings["prompt_cache_retention"] = "in_memory"
    elif wire_api == "chat-completions":
        settings["include_usage"] = True
    return settings


def _sdk_run_config_for_profile(_profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "trace_include_sensitive_data": False,
        "workflow_name": "roboclaws-openai-agents-live",
    }


def _normal_provider_profile(provider_profile: str) -> str:
    return normalize_provider_route(provider_profile, default="codex-env")


def _wire_api_for_provider_profile(provider_profile: str) -> str:
    return provider_route_spec(provider_profile).wire_api


def _registry_model_family(provider_profile: str, model: str) -> str:
    return model_family_for_route_model(provider_profile, model or None)


def _string_setting(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    *,
    default: str,
    allowed: set[str],
) -> str:
    value = str(getattr(args, attr, "") or os.environ.get(env_name, "") or default).strip()
    if value not in allowed:
        raise ValueError(f"unsupported OpenAI Agents SDK {attr.replace('_', '-')} '{value}'")
    return value


def _int_setting(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    *,
    default: int | None,
    allow_none: bool = False,
) -> int | None:
    raw = getattr(args, attr, None)
    if raw is None:
        env_raw = os.environ.get(env_name)
        raw = env_raw if env_raw not in {None, ""} else default
    if raw is None:
        if allow_none:
            return None
        raise ValueError(f"{attr} is required")
    value = int(raw)
    if value < 0:
        raise ValueError(f"{attr} must be non-negative")
    return value


def _positive_int_setting(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    *,
    default: int,
) -> int:
    raw = getattr(args, attr, None)
    if raw is None:
        env_raw = os.environ.get(env_name)
        raw = env_raw if env_raw not in {None, ""} else default
    value = int(raw)
    if value < 1:
        raise ValueError(f"{attr} must be >= 1")
    return value


def _float_setting(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    *,
    default: float,
) -> float:
    raw = getattr(args, attr, None)
    if raw is None:
        env_raw = os.environ.get(env_name)
        raw = env_raw if env_raw not in {None, ""} else default
    value = float(raw)
    if value < 0:
        raise ValueError(f"{attr} must be non-negative")
    return _round_duration(value)


def _bool_arg_setting(
    args: argparse.Namespace,
    attr: str,
    env_name: str,
    *,
    default: bool,
) -> bool:
    raw = getattr(args, attr, None)
    if raw is None:
        env_raw = os.environ.get(env_name)
        if env_raw not in {None, ""}:
            raw = env_raw
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() not in {"0", "false", "no", "off"}


def _validate_context_limits(profile: dict[str, Any]) -> None:
    soft = profile.get("context_soft_limit_tokens")
    hard = profile.get("context_hard_limit_tokens")
    if soft is not None and hard is not None and int(soft) > int(hard):
        raise ValueError("context_soft_limit_tokens must be <= context_hard_limit_tokens")


def _profiled_kickoff_prompt(args: argparse.Namespace, *, profile: dict[str, Any]) -> str:
    mode = str(profile.get("prompt_mode") or "full")
    original = str(getattr(args, "kickoff_prompt", "") or "")
    lane = str(getattr(args, "profile", "") or "")
    composite_tools = _camera_grounded_composite_tools_enabled_for_run(
        profile,
        evidence_lane=lane,
    )
    if _prompt_already_matches_profile(
        original,
        mode=mode,
        camera_grounded_composite_tools=composite_tools,
    ):
        return original
    task_name = str(getattr(args, "task_name", "") or "")
    intent = os.environ.get("ROBOCLAWS_TASK_INTENT", "")
    can_render = (
        task_name == "household-cleanup"
        and mode in {"compact", "raw_fpv_compact"}
        and lane in {"world-public-labels", "camera-grounded-labels", "camera-raw-fpv"}
    )
    if not can_render:
        return original
    target_cleanup_count = _target_cleanup_count_for_prompt(args, lane=lane)
    try:
        return render_kickoff_prompt(
            lane,
            task=str(getattr(args, "task", "") or ""),
            target_cleanup_count=target_cleanup_count,
            task_intent_mode=str(getattr(args, "task_intent_mode", "") or TASK_INTENT_MODE_DEFAULT),
            intent=intent,
            goal_contract=None,
            prompt_mode=mode,
            raw_fpv_candidate_budget=int(profile.get("raw_fpv_candidate_budget") or 24),
            max_observe_per_waypoint=int(profile.get("max_observe_per_waypoint") or 1),
            done_retry_budget=int(profile.get("done_retry_budget") or 1),
            camera_grounded_composite_tools=composite_tools,
        )
    except ValueError:
        return original


def _target_cleanup_count_for_prompt(args: argparse.Namespace, *, lane: str) -> int:
    raw_count = str(getattr(args, "min_generated_mess_count", "") or "")
    try:
        count = int(raw_count)
    except ValueError:
        count = 7
    if lane == "camera-raw-fpv":
        return max(1, (count * 7 + 9) // 10)
    return max(1, count)


def _kickoff_prompt_source(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    original = str(getattr(args, "kickoff_prompt", "") or "")
    mode = str(profile.get("prompt_mode") or "full")
    composite_tools = _camera_grounded_composite_tools_enabled_for_run(
        profile,
        evidence_lane=str(getattr(args, "profile", "") or ""),
    )
    if _prompt_already_matches_profile(
        original,
        mode=mode,
        camera_grounded_composite_tools=composite_tools,
    ):
        return f"provided-profile-rendered-{mode}"
    rendered = _profiled_kickoff_prompt(args, profile=profile)
    if rendered == original:
        return "just-rendered-full"
    return f"profile-rendered-{profile.get('prompt_mode') or 'full'}"


def _prompt_already_matches_profile(
    prompt: str,
    *,
    mode: str,
    camera_grounded_composite_tools: bool = False,
) -> bool:
    if mode == "compact":
        if camera_grounded_composite_tools:
            return "observe_camera_grounded_candidates" in prompt
        return (
            "Compact action cadence for world-public-labels" in prompt
            or "Compact action cadence for camera-grounded-labels" in prompt
        )
    if mode == "raw_fpv_compact":
        return "Compact action cadence for camera-raw-fpv" in prompt
    return False


def _budget_failure_from_run_state(
    run_dir: Path,
    timing: dict[str, Any],
    profile: dict[str, Any],
) -> LiveAgentFailure | None:
    context_failure = _context_budget_failure(run_dir, timing, profile)
    if context_failure is not None:
        return context_failure
    return _raw_fpv_budget_failure(run_dir, timing, profile)


def _failure_from_sdk_result(
    result: Any,
    *,
    run_dir: Path,
    timing: dict[str, Any],
    profile: dict[str, Any],
) -> LiveAgentFailure:
    if (
        str(getattr(result, "reason", "") or "") == "agent_sdk_turn_budget_exceeded"
        and str(timing.get("evidence_lane") or timing.get("profile") or "") == "camera-raw-fpv"
    ):
        context_metrics = _context_metrics(run_dir, timing)
        detail = json.dumps(
            {
                "schema": "agent_sdk_raw_fpv_budget_terminal_v1",
                "profile_id": profile.get("profile_id") or "baseline",
                "reason": "raw_fpv_sdk_turn_budget_exhausted",
                "max_turns": profile.get("max_turns"),
                "context_hard_limit_tokens": profile.get("context_hard_limit_tokens"),
                "max_input_tokens": context_metrics.get("max_input_tokens"),
                "total_input_tokens": context_metrics.get("total_input_tokens"),
                "total_uncached_input_tokens": context_metrics.get("total_uncached_input_tokens"),
                "response_span_count": context_metrics.get("response_span_count"),
            },
            sort_keys=True,
        )
        return LiveAgentFailure(
            "raw_fpv_sdk_turn_budget_exhausted",
            retryable=False,
            resume_available=False,
            detail=detail,
        )
    return LiveAgentFailure(
        reason=getattr(result, "reason", "") or "agent_cli_failure",
        retryable=bool(getattr(result, "retryable", False)),
        provider_reason=getattr(result, "provider_reason", ""),
        resume_available=bool(getattr(result, "resume_available", False)),
        detail=getattr(result, "detail", ""),
    )


def _context_budget_failure(
    run_dir: Path,
    timing: dict[str, Any],
    profile: dict[str, Any],
) -> LiveAgentFailure | None:
    hard_limit = _int_or_none(profile.get("context_hard_limit_tokens"))
    if hard_limit is None:
        return None
    context_metrics = _context_metrics(run_dir, timing)
    current_input = _int_or_none(context_metrics.get("max_input_tokens"))
    if current_input is None or current_input < hard_limit:
        return None
    detail = json.dumps(
        {
            "schema": "agent_sdk_context_budget_terminal_v1",
            "profile_id": profile.get("profile_id") or "baseline",
            "context_hard_limit_tokens": hard_limit,
            "current_input_tokens": current_input,
            "max_input_tokens": current_input,
            "total_input_tokens": context_metrics.get("total_input_tokens"),
            "total_uncached_input_tokens": context_metrics.get("total_uncached_input_tokens"),
            "response_span_count": context_metrics.get("response_span_count"),
            "evidence_source": context_metrics.get("source") or "unavailable",
        },
        sort_keys=True,
    )
    return LiveAgentFailure(
        "provider_context_budget_exceeded",
        retryable=False,
        resume_available=False,
        detail=detail,
    )


def _raw_fpv_budget_failure(
    run_dir: Path,
    timing: dict[str, Any],
    profile: dict[str, Any],
) -> LiveAgentFailure | None:
    if str(timing.get("evidence_lane") or timing.get("profile") or "") != "camera-raw-fpv":
        return None
    candidate_budget = _int_or_none(profile.get("raw_fpv_candidate_budget"))
    repeated_failure_limit = _int_or_none(profile.get("raw_fpv_repeated_failure_limit"))
    observe_budget = _int_or_none(profile.get("max_observe_per_waypoint"))
    if candidate_budget is None and observe_budget is None and repeated_failure_limit is None:
        return None
    trace_events = _read_jsonl_path(run_dir / "trace.jsonl")
    if not trace_events:
        return None
    metrics = _raw_fpv_budget_metrics(trace_events)
    reasons: list[str] = []
    if repeated_failure_limit is not None:
        repeated_failures = [
            item
            for item in metrics["repeated_failure_fingerprints"]
            if int(item.get("count") or 0) >= repeated_failure_limit
        ]
        if repeated_failures:
            metrics["repeated_failure_limit"] = repeated_failure_limit
            metrics["repeated_failure_limit_hits"] = repeated_failures[:12]
            reasons.append("raw_fpv_repeated_candidate_failure")
    if candidate_budget is not None and metrics["candidate_attempt_count"] >= candidate_budget:
        reasons.append("raw_fpv_candidate_budget_exhausted")
    if observe_budget is not None:
        over_budget = {
            waypoint_id: count
            for waypoint_id, count in metrics["observe_count_by_waypoint"].items()
            if waypoint_id and count > observe_budget
        }
        if over_budget:
            metrics["observe_over_budget_by_waypoint"] = dict(sorted(over_budget.items()))
            reasons.append("raw_fpv_observe_budget_exhausted")
    if not reasons:
        return None
    reason = "raw_fpv_repeated_candidate_failure"
    if "raw_fpv_repeated_candidate_failure" not in reasons:
        reason = "raw_fpv_candidate_budget_exhausted"
    if (
        "raw_fpv_repeated_candidate_failure" not in reasons
        and "raw_fpv_candidate_budget_exhausted" not in reasons
    ):
        reason = "raw_fpv_observe_budget_exhausted"
    detail = json.dumps(
        {
            "schema": "agent_sdk_raw_fpv_budget_terminal_v1",
            "profile_id": profile.get("profile_id") or "baseline",
            "reasons": reasons,
            "raw_fpv_candidate_budget": candidate_budget,
            "raw_fpv_repeated_failure_limit": repeated_failure_limit,
            "max_observe_per_waypoint": observe_budget,
            **metrics,
        },
        sort_keys=True,
    )
    return LiveAgentFailure(
        reason,
        retryable=False,
        resume_available=False,
        detail=detail,
    )


def _raw_fpv_budget_metrics(trace_events: list[dict[str, Any]]) -> dict[str, Any]:
    candidate_attempts: list[dict[str, str]] = []
    observe_count_by_waypoint: dict[str, int] = {}
    failure_fingerprints: dict[str, int] = {}
    failure_fingerprint_details: dict[str, dict[str, str]] = {}
    for event in trace_events:
        tool = str(event.get("tool") or "")
        event_type = str(event.get("event") or "")
        if tool == "observe" and event_type == "response":
            response = event.get("response") if isinstance(event.get("response"), dict) else {}
            waypoint_id = _waypoint_from_response(response)
            observe_count_by_waypoint[waypoint_id] = (
                observe_count_by_waypoint.get(waypoint_id, 0) + 1
            )
            continue
        if tool not in {"navigate_to_visual_candidate", "declare_visual_candidates"}:
            continue
        request = event.get("request") if isinstance(event.get("request"), dict) else {}
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        source_id = str(
            request.get("source_observation_id")
            or request.get("observation_id")
            or response.get("observation_id")
            or response.get("source_observation_id")
            or ""
        )
        if not source_id and "raw_fpv" not in json.dumps(event, sort_keys=True, ensure_ascii=True):
            continue
        category = str(request.get("category") or response.get("category") or "")
        region = _region_fingerprint(request.get("image_region"))
        candidate_id = str(response.get("candidate_id") or response.get("object_id") or "")
        failure_reason = str(
            response.get("error_reason")
            or response.get("failure_reason")
            or response.get("status")
            or ""
        )
        if event_type == "request":
            candidate_attempts.append(
                {
                    "source_observation_id": source_id,
                    "category": category,
                    "region": region,
                    "candidate_id": candidate_id,
                }
            )
        if event_type == "response" and failure_reason:
            fingerprint = "|".join((source_id, category, region, candidate_id, failure_reason))
            failure_fingerprints[fingerprint] = failure_fingerprints.get(fingerprint, 0) + 1
            failure_fingerprint_details.setdefault(
                fingerprint,
                {
                    "source_observation_id": source_id,
                    "category": category,
                    "region": region,
                    "candidate_id": candidate_id,
                    "failure_reason": failure_reason,
                },
            )
    repeated_failures = [
        {
            "fingerprint": key,
            "count": count,
            **failure_fingerprint_details.get(key, {}),
        }
        for key, count in sorted(failure_fingerprints.items())
        if count > 1
    ][:12]
    return {
        "candidate_attempt_count": len(candidate_attempts),
        "candidate_attempts_sample": candidate_attempts[-12:],
        "observe_count_by_waypoint": dict(sorted(observe_count_by_waypoint.items())),
        "repeated_failure_fingerprints": repeated_failures,
    }


def _waypoint_from_response(response: dict[str, Any]) -> str:
    waypoint_id = str(response.get("waypoint_id") or "")
    if waypoint_id:
        return waypoint_id
    raw_payload = response.get("raw_fpv_observation")
    raw = raw_payload if isinstance(raw_payload, dict) else {}
    return str(raw.get("waypoint_id") or "unknown")


def _region_fingerprint(value: Any) -> str:
    if isinstance(value, dict):
        region_type = str(value.get("type") or "")
        region_value = value.get("value")
        if isinstance(region_value, list):
            compact = ",".join(str(item) for item in region_value[:4])
        else:
            compact = str(region_value or "")
        return f"{region_type}:{compact}"[:120]
    return str(value or "")[:120]


def _compact_continuation_prompt(
    run_dir: Path,
    *,
    profile: dict[str, Any],
    context_metrics: dict[str, Any],
) -> str:
    state = _compact_continuation_state(
        run_dir,
        profile=profile,
        context_metrics=context_metrics,
    )
    return (
        "Continuation recovery for the same live household cleanup run.\n\n"
        "Use this compact public state packet instead of replaying the original "
        "kickoff prompt. Do not summarize progress as a final answer. Inspect "
        "current public MCP state if needed, continue only missing cleanup work, "
        "and call done only after MCP-visible public state satisfies the task. "
        "The runner will count success only when MCP done produces run_result.json.\n\n"
        f"compact_continuation_state:\n{json.dumps(state, ensure_ascii=False, sort_keys=True)}\n"
    )


def _compact_continuation_state(
    run_dir: Path,
    *,
    profile: dict[str, Any],
    context_metrics: dict[str, Any],
) -> dict[str, Any]:
    trace_events = _read_jsonl_path(run_dir / "trace.jsonl")
    goal_contract = _goal_contract_summary(trace_events)
    completed_waypoints = _completed_waypoints(trace_events)
    handled_objects = _handled_object_handles(trace_events)
    public_pending = _public_pending_object_handles(trace_events)
    blocked_candidates = _blocked_candidates(trace_events)
    recent_failures = _recent_tool_failures(trace_events)
    return {
        "schema": "compact_agent_state_v1",
        "surface": goal_contract.get("surface") or "household-world",
        "intent": goal_contract.get("intent") or "cleanup",
        "evidence_lane": _trace_field(trace_events, "cleanup_profile"),
        "goal_summary": goal_contract.get("normalized_goal") or "",
        "agent_sdk_perf_profile_id": profile.get("profile_id") or "baseline",
        "completed_waypoints": completed_waypoints[-32:],
        "handled_object_handles": handled_objects[-32:],
        "public_pending_object_handles": public_pending[-32:],
        "blocked_candidates": blocked_candidates[-12:],
        "recent_tool_failures": recent_failures[-8:],
        "remaining_public_gates": _remaining_public_gates(completed_waypoints, public_pending),
        "next_requested_action": _next_requested_action(completed_waypoints, public_pending),
        "context_metrics": _compact_metric_group(context_metrics),
    }


def _goal_contract_summary(trace_events: list[dict[str, Any]]) -> dict[str, Any]:
    for event in trace_events:
        goal_contract = event.get("goal_contract")
        if isinstance(goal_contract, dict):
            return {
                "surface": goal_contract.get("surface"),
                "intent": goal_contract.get("intent"),
                "normalized_goal": goal_contract.get("normalized_goal"),
                "goal_scope": goal_contract.get("goal_scope"),
            }
    return {}


def _trace_field(trace_events: list[dict[str, Any]], field: str) -> str:
    for event in trace_events:
        value = event.get(field)
        if value:
            return str(value)
    return ""


def _completed_waypoints(trace_events: list[dict[str, Any]]) -> list[str]:
    completed: list[str] = []
    for event in trace_events:
        if event.get("event") != "response" or event.get("tool") != "observe":
            continue
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        waypoint_id = str(response.get("waypoint_id") or "")
        if waypoint_id and waypoint_id not in completed:
            completed.append(waypoint_id)
    return completed


def _handled_object_handles(trace_events: list[dict[str, Any]]) -> list[str]:
    handled: list[str] = []
    for event in trace_events:
        if event.get("event") != "response" or event.get("tool") not in {"place", "place_inside"}:
            continue
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        for key in ("object_id", "held_object_id", "source_object_id", "target_object_id"):
            value = str(response.get(key) or "")
            if value and value not in handled:
                handled.append(value)
    return handled


def _public_pending_object_handles(trace_events: list[dict[str, Any]]) -> list[str]:
    pending: list[str] = []
    for event in trace_events:
        if event.get("event") != "response":
            continue
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        pending_candidates = response.get("pending_cleanup_candidates")
        if not isinstance(pending_candidates, list):
            continue
        for item in pending_candidates:
            if not isinstance(item, dict):
                continue
            public_id = str(
                item.get("object_id") or item.get("public_id") or item.get("handle") or ""
            )
            if public_id and public_id not in pending:
                pending.append(public_id)
    return pending


def _blocked_candidates(trace_events: list[dict[str, Any]]) -> list[dict[str, str]]:
    blocked: list[dict[str, str]] = []
    for event in trace_events:
        if event.get("event") != "response":
            continue
        tool = str(event.get("tool") or "")
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        status = str(response.get("status") or "")
        ok = response.get("ok")
        if ok is not False and status not in {"blocked", "failed", "error"}:
            continue
        public_id = str(
            response.get("object_id")
            or response.get("candidate_id")
            or response.get("public_id")
            or response.get("source_observation_id")
            or ""
        )
        reason = str(response.get("reason") or response.get("error") or status or "tool_failed")
        item = {
            "public_id": public_id,
            "reason": reason[:160],
            "last_failure_tool": tool,
        }
        if item not in blocked:
            blocked.append(item)
    return blocked


def _recent_tool_failures(trace_events: list[dict[str, Any]]) -> list[dict[str, str]]:
    failures: list[dict[str, str]] = []
    for event in trace_events:
        if event.get("event") != "response":
            continue
        response = event.get("response") if isinstance(event.get("response"), dict) else {}
        ok = response.get("ok")
        status = str(response.get("status") or "")
        if ok is not False and status not in {"blocked", "failed", "error"}:
            continue
        failures.append(
            {
                "tool": str(event.get("tool") or ""),
                "public_error_class": status or "tool_failed",
                "public_target": str(
                    response.get("object_id")
                    or response.get("candidate_id")
                    or response.get("waypoint_id")
                    or response.get("source_observation_id")
                    or ""
                ),
            }
        )
    return failures


def _remaining_public_gates(completed_waypoints: list[str], pending: list[str]) -> list[str]:
    gates: list[str] = []
    if not completed_waypoints:
        gates.append("inspect public waypoint checklist with metric_map and observe waypoints")
    if pending:
        gates.append("clean public pending handles returned by done")
    gates.append("call done only after public cleanup gates are satisfied")
    return gates


def _next_requested_action(completed_waypoints: list[str], pending: list[str]) -> str:
    if pending:
        return "clean the public pending handles before broad re-sweep"
    if not completed_waypoints:
        return "call metric_map, fixture_hints, navigate_to_waypoint, then observe"
    return "inspect public MCP state, finish missing objects or waypoints, then call done"


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


def _intent_for_task_name(task_name: str) -> str:
    if task_name == "semantic-map-build":
        return "map-build"
    return "cleanup"


def _task_intent_mode_for_timing(args: Any) -> str:
    return normalize_task_intent_mode(
        getattr(args, "task_intent_mode", "") or TASK_INTENT_MODE_DEFAULT
    )


def _live_timing_timeline(timing: dict[str, Any]) -> dict[str, Any]:
    """Build a normalized timeline for cross-run latency comparisons."""

    finished_at = _float_or_none(timing.get("finished_at_epoch"))
    started_at = _float_or_none(timing.get("started_at_epoch"))
    runner_segments = _runner_timeline_segments(timing, finished_at)
    attempt_segments = _attempt_timeline_segments(timing)
    attribution = _latency_attribution(timing)
    return {
        "schema": "live_agent_timeline_v1",
        "surface": timing.get("surface", ""),
        "intent": timing.get("intent", ""),
        "task_name": timing.get("task_name", ""),
        "task_intent_mode": timing.get("task_intent_mode", ""),
        "runtime": timing.get("runtime", ""),
        "provider_profile": timing.get("provider_profile", ""),
        "wire_api": timing.get("wire_api", ""),
        "model": timing.get("model", ""),
        "evidence_lane": timing.get("evidence_lane") or timing.get("profile", ""),
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
    span_metrics = (
        timing.get("openai_agents_span_metrics")
        if isinstance(timing.get("openai_agents_span_metrics"), dict)
        else {}
    )
    fallback_metrics = (
        timing.get("model_service_fallback_metrics")
        if isinstance(timing.get("model_service_fallback_metrics"), dict)
        else {}
    )
    model_input_filter_metrics = (
        timing.get("model_input_filter_metrics")
        if isinstance(timing.get("model_input_filter_metrics"), dict)
        else {}
    )
    context_metrics = (
        timing.get("context_metrics") if isinstance(timing.get("context_metrics"), dict) else {}
    )
    cache_metrics = (
        timing.get("cache_metrics") if isinstance(timing.get("cache_metrics"), dict) else {}
    )
    context_growth_metrics = (
        timing.get("context_growth_metrics")
        if isinstance(timing.get("context_growth_metrics"), dict)
        else {}
    )
    budget_terminal = (
        timing.get("agent_sdk_budget_terminal")
        if isinstance(timing.get("agent_sdk_budget_terminal"), dict)
        else {}
    )
    sdk_elapsed = _float_or_none(runner_timing.get("openai_agents_elapsed_s"))
    mcp_elapsed = _float_or_none(mcp_timing.get("total_elapsed_s"))
    model_or_sdk_unattributed_s = _model_or_sdk_unattributed_seconds(timing)
    return {
        "openai_agents_elapsed_s": sdk_elapsed,
        "mcp_trace_elapsed_s": mcp_elapsed,
        "model_or_sdk_unattributed_s": model_or_sdk_unattributed_s,
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
        "openai_agents_span_artifact_available": span_metrics.get("available"),
        "openai_agents_span_count": span_metrics.get("span_end_count"),
        "openai_agents_span_type_counts": span_metrics.get("span_type_counts"),
        "openai_agents_span_capture_limitations": span_metrics.get("limitations"),
        "model_service_fallback_metrics": _compact_metric_group(fallback_metrics),
        "model_input_filter_metrics": _compact_metric_group(model_input_filter_metrics),
        "agent_sdk_budget_terminal": _compact_metric_group(budget_terminal),
        "mcp_client_session_timeout_s": timing.get("mcp_client_session_timeout_s"),
        "context_metrics": _compact_metric_group(context_metrics),
        "cache_metrics": _compact_metric_group(cache_metrics),
        "context_growth_metrics": _compact_metric_group(context_growth_metrics),
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


def _model_service_fallback_metrics(run_dir: Path) -> dict[str, Any]:
    events = [
        event
        for path in sorted(run_dir.glob("openai-agents-events*.jsonl"))
        for event in _read_jsonl_path(path)
        if event.get("schema") == "openai_agents_model_service_fallback_v1"
    ]
    if not events:
        return {
            "available": False,
            "source": "openai_agents_model_service_fallback_events",
            "limitations": ["model_service_fallback_events_missing"],
        }

    event_counts: dict[str, int] = {}
    failure_classes: dict[str, int] = {}
    provider_reasons: dict[str, int] = {}
    attempted_models: set[str] = set()
    attempted_provider_profiles: set[str] = set()
    attempted_wire_apis: set[str] = set()
    retry_delay_s_total = 0.0
    retry_delay_count = 0
    retry_exhausted = False
    final_outcomes: dict[str, int] = {}
    for event in events:
        event_type = str(event.get("event") or "")
        if event_type:
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
        model = str(event.get("model") or "")
        if model:
            attempted_models.add(model)
        provider_profile = str(event.get("provider_profile") or "")
        if provider_profile:
            attempted_provider_profiles.add(provider_profile)
        wire_api = str(event.get("wire_api") or "")
        if wire_api:
            attempted_wire_apis.add(wire_api)
        if event_type == "model_service_failure":
            failure_class = str(event.get("failure_class") or "")
            if failure_class:
                failure_classes[failure_class] = failure_classes.get(failure_class, 0) + 1
            provider_reason = str(event.get("provider_reason") or "")
            if provider_reason:
                provider_reasons[provider_reason] = provider_reasons.get(provider_reason, 0) + 1
        delay = _float_or_none(event.get("retry_delay_s"))
        if delay is not None:
            retry_delay_s_total += delay
            retry_delay_count += 1
        if event.get("retry_exhausted") is True:
            retry_exhausted = True
        final_outcome = str(event.get("final_outcome") or "")
        if final_outcome:
            final_outcomes[final_outcome] = final_outcomes.get(final_outcome, 0) + 1

    return {
        "available": True,
        "source": "openai_agents_model_service_fallback_events",
        "limitations": [],
        "attempt_event_count": event_counts.get("model_service_attempt", 0),
        "retry_scheduled_count": event_counts.get("model_service_retry_scheduled", 0),
        "failure_event_count": event_counts.get("model_service_failure", 0),
        "success_event_count": event_counts.get("model_service_success", 0),
        "failure_classes": dict(sorted(failure_classes.items())),
        "provider_reasons": dict(sorted(provider_reasons.items())),
        "attempted_models": sorted(attempted_models),
        "attempted_provider_profiles": sorted(attempted_provider_profiles),
        "attempted_wire_apis": sorted(attempted_wire_apis),
        "retry_delay_s_total": _round_duration(retry_delay_s_total),
        "retry_delay_count": retry_delay_count,
        "retry_exhausted": retry_exhausted,
        "final_outcomes": dict(sorted(final_outcomes.items())),
        "privacy_note": (
            "Fallback metrics retain attempt counts, provider/model ids, failure classes, "
            "retry delays, and outcomes only. Raw prompts, model text, credentials, and "
            "tool payload bodies are not persisted."
        ),
    }


def _model_input_filter_metrics(run_dir: Path) -> dict[str, Any]:
    events = [
        event
        for path in sorted(run_dir.glob("openai-agents-events*.jsonl"))
        for event in _read_jsonl_path(path)
        if event.get("schema") == "openai_agents_model_input_filter_v1"
    ]
    if not events:
        return {
            "available": False,
            "source": "openai_agents_model_input_filter_events",
            "limitations": ["model_input_filter_events_missing"],
        }

    attempted_models: set[str] = set()
    attempted_provider_profiles: set[str] = set()
    attempted_wire_apis: set[str] = set()
    input_bytes_before = 0
    input_bytes_after = 0
    input_bytes_reduced = 0
    compacted_item_count = 0
    unchanged_item_count = 0
    repeated_item_count = 0
    metric_map_output_count = 0
    repeated_metric_map_output_count = 0
    metric_map_delta_compacted_count = 0
    metric_map_bytes_before = 0
    metric_map_bytes_after = 0
    metric_map_bytes_reduced = 0
    raw_fpv_image_item_count = 0
    raw_fpv_image_retained_count = 0
    raw_fpv_image_evicted_count = 0
    raw_fpv_image_bytes_before = 0
    raw_fpv_image_bytes_after = 0
    raw_fpv_image_bytes_reduced = 0
    raw_fpv_image_memory_enabled = False
    raw_fpv_image_memory_modes: set[str] = set()
    max_input_bytes_before = 0
    max_input_bytes_after = 0
    max_input_bytes_reduced = 0
    enabled = False
    modes: set[str] = set()
    for event in events:
        model = str(event.get("model") or "")
        if model:
            attempted_models.add(model)
        provider_profile = str(event.get("provider_profile") or "")
        if provider_profile:
            attempted_provider_profiles.add(provider_profile)
        wire_api = str(event.get("wire_api") or "")
        if wire_api:
            attempted_wire_apis.add(wire_api)
        config = event.get("config") if isinstance(event.get("config"), dict) else {}
        enabled = enabled or bool(config.get("enabled"))
        mode = str(config.get("mode") or "")
        if mode:
            modes.add(mode)
        metrics = event.get("metrics") if isinstance(event.get("metrics"), dict) else {}
        before = _int_or_none(metrics.get("input_bytes_before")) or 0
        after = _int_or_none(metrics.get("input_bytes_after")) or 0
        reduced = _int_or_none(metrics.get("input_bytes_reduced")) or 0
        input_bytes_before += before
        input_bytes_after += after
        input_bytes_reduced += reduced
        compacted_item_count += _int_or_none(metrics.get("compacted_item_count")) or 0
        unchanged_item_count += _int_or_none(metrics.get("unchanged_item_count")) or 0
        repeated_item_count += _int_or_none(metrics.get("repeated_item_count")) or 0
        metric_map_output_count += _int_or_none(metrics.get("metric_map_output_count")) or 0
        repeated_metric_map_output_count += (
            _int_or_none(metrics.get("repeated_metric_map_output_count")) or 0
        )
        metric_map_delta_compacted_count += (
            _int_or_none(metrics.get("metric_map_delta_compacted_count")) or 0
        )
        metric_map_bytes_before += _int_or_none(metrics.get("metric_map_bytes_before")) or 0
        metric_map_bytes_after += _int_or_none(metrics.get("metric_map_bytes_after")) or 0
        metric_map_bytes_reduced += _int_or_none(metrics.get("metric_map_bytes_reduced")) or 0
        raw_fpv_image_item_count += _int_or_none(metrics.get("raw_fpv_image_item_count")) or 0
        raw_fpv_image_retained_count += (
            _int_or_none(metrics.get("raw_fpv_image_retained_count")) or 0
        )
        raw_fpv_image_evicted_count += _int_or_none(metrics.get("raw_fpv_image_evicted_count")) or 0
        raw_fpv_image_bytes_before += _int_or_none(metrics.get("raw_fpv_image_bytes_before")) or 0
        raw_fpv_image_bytes_after += _int_or_none(metrics.get("raw_fpv_image_bytes_after")) or 0
        raw_fpv_image_bytes_reduced += _int_or_none(metrics.get("raw_fpv_image_bytes_reduced")) or 0
        raw_fpv_image_memory_enabled = raw_fpv_image_memory_enabled or bool(
            metrics.get("raw_fpv_image_memory_enabled")
        )
        raw_fpv_mode = str(metrics.get("raw_fpv_image_memory_mode") or "")
        if raw_fpv_mode:
            raw_fpv_image_memory_modes.add(raw_fpv_mode)
        max_input_bytes_before = max(max_input_bytes_before, before)
        max_input_bytes_after = max(max_input_bytes_after, after)
        max_input_bytes_reduced = max(max_input_bytes_reduced, reduced)

    return {
        "available": True,
        "source": "openai_agents_model_input_filter_events",
        "limitations": [],
        "event_count": len(events),
        "enabled": enabled,
        "modes": sorted(modes),
        "attempted_models": sorted(attempted_models),
        "attempted_provider_profiles": sorted(attempted_provider_profiles),
        "attempted_wire_apis": sorted(attempted_wire_apis),
        "compacted_item_count": compacted_item_count,
        "unchanged_item_count": unchanged_item_count,
        "repeated_item_count": repeated_item_count,
        "metric_map_output_count": metric_map_output_count,
        "repeated_metric_map_output_count": repeated_metric_map_output_count,
        "metric_map_delta_compacted_count": metric_map_delta_compacted_count,
        "metric_map_bytes_before": metric_map_bytes_before,
        "metric_map_bytes_after": metric_map_bytes_after,
        "metric_map_bytes_reduced": metric_map_bytes_reduced,
        "metric_map_byte_reduction_ratio": _ratio(
            metric_map_bytes_reduced,
            metric_map_bytes_before,
        ),
        "raw_fpv_image_memory_enabled": raw_fpv_image_memory_enabled,
        "raw_fpv_image_memory_modes": sorted(raw_fpv_image_memory_modes),
        "raw_fpv_image_item_count": raw_fpv_image_item_count,
        "raw_fpv_image_retained_count": raw_fpv_image_retained_count,
        "raw_fpv_image_evicted_count": raw_fpv_image_evicted_count,
        "raw_fpv_image_bytes_before": raw_fpv_image_bytes_before,
        "raw_fpv_image_bytes_after": raw_fpv_image_bytes_after,
        "raw_fpv_image_bytes_reduced": raw_fpv_image_bytes_reduced,
        "raw_fpv_image_byte_reduction_ratio": _ratio(
            raw_fpv_image_bytes_reduced,
            raw_fpv_image_bytes_before,
        ),
        "input_bytes_before": input_bytes_before,
        "input_bytes_after": input_bytes_after,
        "input_bytes_reduced": input_bytes_reduced,
        "input_byte_reduction_ratio": _ratio(input_bytes_reduced, input_bytes_before),
        "max_input_bytes_before": max_input_bytes_before,
        "max_input_bytes_after": max_input_bytes_after,
        "max_input_bytes_reduced": max_input_bytes_reduced,
        "privacy_note": (
            "Model-input filter metrics retain aggregate counts, byte sizes, mode, provider, "
            "wire API, and model ids only. Raw prompts, model text, tool payload bodies, "
            "credentials, and private truth are not persisted."
        ),
    }


def _openai_agents_span_metrics(run_dir: Path) -> dict[str, Any]:
    span_paths = sorted(run_dir.glob("openai-agents-spans*.jsonl"))
    if not span_paths:
        return {
            "available": False,
            "reason": "openai-agents span files not present",
        }

    event_counts: dict[str, int] = {}
    span_type_counts: dict[str, int] = {}
    limitations: list[dict[str, Any]] = []
    span_end_count = 0
    for path in span_paths:
        for event in _read_jsonl_path(path):
            event_type = str(event.get("event") or "")
            if event_type:
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if event_type == "span_capture_unavailable":
                limitations.append(
                    {
                        "reason": event.get("reason", ""),
                        "error_type": event.get("error_type", ""),
                        "message": event.get("message", ""),
                    }
                )
            if event_type != "span_end":
                continue
            span_end_count += 1
            span_type = str(event.get("span_type") or "unknown")
            span_type_counts[span_type] = span_type_counts.get(span_type, 0) + 1

    return {
        "available": True,
        "span_files": [path.name for path in span_paths],
        "event_counts": dict(sorted(event_counts.items())),
        "span_end_count": span_end_count,
        "span_type_counts": dict(sorted(span_type_counts.items())),
        "limitations": limitations,
        "sanitization_note": (
            "Span artifacts retain IDs, timing, span types, model/usage, MCP tool metadata, "
            "and errors. Raw prompts, model text, function inputs, and function outputs are "
            "not persisted."
        ),
    }


def _context_metrics(run_dir: Path, timing: dict[str, Any]) -> dict[str, Any]:
    response_spans = _response_span_end_events(run_dir)
    kickoff_prompt_chars = _int_or_none(timing.get("kickoff_prompt_chars")) or 0
    attempts = timing.get("openai_agents_attempts")
    if not isinstance(attempts, list):
        attempts = []
    continuation_prompt_chars = sum(
        _int_or_none(attempt.get("continuation_prompt_chars")) or 0
        for attempt in attempts
        if isinstance(attempt, dict)
    )
    base_payload: dict[str, Any] = {
        "kickoff_prompt_chars": kickoff_prompt_chars,
        "kickoff_prompt_estimated_tokens": _estimated_tokens_from_chars(kickoff_prompt_chars),
        "continuation_prompt_chars": continuation_prompt_chars,
        "continuation_prompt_estimated_tokens": _estimated_tokens_from_chars(
            continuation_prompt_chars
        ),
        "context_window_failure_detected": _context_window_failure_detected(timing, run_dir),
    }
    if not response_spans:
        return {
            "available": False,
            "source": "unavailable",
            "limitations": ["span_usage_missing"],
            **base_payload,
        }

    usage_rows: list[dict[str, int | float | None]] = []
    limitations: list[str] = []
    for event in response_spans:
        usage = event.get("usage") if isinstance(event.get("usage"), dict) else {}
        if not usage:
            limitations.append("response_span_usage_missing")
            continue
        input_tokens = _int_or_none(usage.get("input_tokens"))
        if input_tokens is None:
            limitations.append("response_span_input_tokens_missing")
            continue
        cached_tokens = _cached_input_tokens(usage)
        output_tokens = _int_or_none(usage.get("output_tokens")) or 0
        reasoning_tokens = _reasoning_tokens(usage) or 0
        usage_rows.append(
            {
                "input_tokens": input_tokens,
                "cached_tokens": min(max(cached_tokens, 0), input_tokens),
                "output_tokens": output_tokens,
                "reasoning_tokens": reasoning_tokens,
                "duration_s": _float_or_none(event.get("duration_s")),
            }
        )

    if not usage_rows:
        return {
            "available": False,
            "source": "openai_agents_span_usage",
            "limitations": sorted(set(limitations or ["span_usage_missing"])),
            "response_span_count": len(response_spans),
            **base_payload,
        }

    input_values = [int(row["input_tokens"] or 0) for row in usage_rows]
    total_input = sum(input_values)
    total_cached = sum(int(row["cached_tokens"] or 0) for row in usage_rows)
    total_uncached = max(0, total_input - total_cached)
    total_output = sum(int(row["output_tokens"] or 0) for row in usage_rows)
    total_reasoning = sum(int(row["reasoning_tokens"] or 0) for row in usage_rows)
    durations = [
        float(row["duration_s"])
        for row in usage_rows
        if _float_or_none(row.get("duration_s")) is not None
    ]
    return {
        "available": True,
        "source": "openai_agents_span_usage",
        "limitations": sorted(set(limitations)),
        "response_span_count": len(usage_rows),
        "total_input_tokens": total_input,
        "total_cached_input_tokens": total_cached,
        "total_uncached_input_tokens": total_uncached,
        "cache_hit_ratio": _ratio(total_cached, total_input),
        "max_input_tokens": max(input_values),
        "p50_input_tokens": _nearest_rank_percentile(input_values, 0.50),
        "p95_input_tokens": _nearest_rank_percentile(input_values, 0.95),
        "total_output_tokens": total_output,
        "total_reasoning_tokens": total_reasoning,
        "max_reasoning_tokens": max(int(row["reasoning_tokens"] or 0) for row in usage_rows),
        "first_response_cached_tokens": int(usage_rows[0]["cached_tokens"] or 0),
        "response_span_duration_s": _round_duration(sum(durations)) if durations else None,
        **base_payload,
    }


def _cache_metrics(context_metrics: dict[str, Any], timing: dict[str, Any]) -> dict[str, Any]:
    model_settings = (
        timing.get("sdk_model_settings")
        if isinstance(timing.get("sdk_model_settings"), dict)
        else {}
    )
    stable_prefix = (
        timing.get("kickoff_prompt_stable_prefix")
        if isinstance(timing.get("kickoff_prompt_stable_prefix"), dict)
        else {}
    )
    if not context_metrics.get("available"):
        return {
            "available": False,
            "source": context_metrics.get("source") or "unavailable",
            "limitations": context_metrics.get("limitations") or ["span_usage_missing"],
            "cache_tools_list": bool(timing.get("cache_tools_list")),
            "prompt_cache_retention": str(model_settings.get("prompt_cache_retention") or ""),
            "stable_prefix_hash": str(stable_prefix.get("hash") or ""),
            "mcp_tool_catalog_cache_enabled": bool(timing.get("cache_tools_list")),
        }
    total_input = _int_or_none(context_metrics.get("total_input_tokens")) or 0
    total_cached = _int_or_none(context_metrics.get("total_cached_input_tokens")) or 0
    return {
        "available": True,
        "source": "openai_agents_span_usage",
        "limitations": list(context_metrics.get("limitations") or []),
        "cache_tools_list": bool(timing.get("cache_tools_list")),
        "prompt_cache_retention": str(model_settings.get("prompt_cache_retention") or ""),
        "provider_prompt_cache_observed": total_cached > 0,
        "cached_input_token_ratio": _ratio(total_cached, total_input),
        "first_response_cached_tokens": context_metrics.get("first_response_cached_tokens"),
        "stable_prefix_hash": str(stable_prefix.get("hash") or ""),
        "prompt_profile_id": str(timing.get("prompt_profile_id") or "baseline"),
        "mcp_tool_catalog_cache_enabled": bool(timing.get("cache_tools_list")),
    }


def _context_growth_metrics(run_dir: Path, timing: dict[str, Any]) -> dict[str, Any]:
    trace_events = _read_jsonl_path(run_dir / "trace.jsonl")
    if not trace_events:
        return {
            "available": False,
            "source": "unavailable",
            "limitations": ["trace_missing"],
            "continuation_attempt_count": _continuation_attempt_count(timing),
        }

    response_events = [event for event in trace_events if event.get("event") == "response"]
    observe_events = [event for event in response_events if event.get("tool") == "observe"]
    raw_fpv_events = [
        event
        for event in response_events
        if "raw_fpv" in json.dumps(event, sort_keys=True, ensure_ascii=True)
    ]
    response_sizes = [len(json.dumps(event, sort_keys=True)) for event in response_events]
    return {
        "available": True,
        "source": "live_timing_and_trace",
        "limitations": [],
        "trace_event_count": len(trace_events),
        "observe_response_count": len(observe_events),
        "raw_fpv_observation_count": len(raw_fpv_events),
        "tool_response_bytes_total": sum(response_sizes),
        "largest_tool_response_bytes": max(response_sizes) if response_sizes else 0,
        "agent_visible_state_bytes_p95": _nearest_rank_percentile(response_sizes, 0.95)
        if response_sizes
        else 0,
        "continuation_attempt_count": _continuation_attempt_count(timing),
    }


def _response_span_end_events(run_dir: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for path in sorted(run_dir.glob("openai-agents-spans*.jsonl")):
        for event in _read_jsonl_path(path):
            if event.get("event") == "span_end" and event.get("span_type") == "response":
                events.append(event)
    return events


def _cached_input_tokens(usage: dict[str, Any]) -> int:
    details = usage.get("input_tokens_details")
    if isinstance(details, dict):
        nested = _int_or_none(details.get("cached_tokens"))
        if nested is not None:
            return nested
    return _int_or_none(usage.get("cached_input_tokens")) or 0


def _reasoning_tokens(usage: dict[str, Any]) -> int | None:
    details = usage.get("output_tokens_details")
    if isinstance(details, dict):
        return _int_or_none(details.get("reasoning_tokens"))
    return _int_or_none(usage.get("reasoning_tokens"))


def _context_window_failure_detected(timing: dict[str, Any], run_dir: Path) -> bool:
    haystack_parts = [
        str(timing.get("reason") or ""),
        str(timing.get("provider_reason") or ""),
        str(timing.get("detail") or ""),
    ]
    for path in sorted(run_dir.glob("openai-agents-*.jsonl")):
        text = path.read_text(encoding="utf-8", errors="replace")[:200_000].lower()
        haystack_parts.append(text)
    haystack = " ".join(haystack_parts).lower()
    return any(
        marker in haystack
        for marker in (
            "context window",
            "context length",
            "context_length",
            "maximum context",
            "input exceeds the context",
            "context-budget",
            "provider_context_failure",
        )
    )


def _model_or_sdk_unattributed_seconds(timing: dict[str, Any]) -> float | None:
    runner_timing = (
        timing.get("runner_timing") if isinstance(timing.get("runner_timing"), dict) else {}
    )
    mcp_timing = (
        timing.get("mcp_trace_timing") if isinstance(timing.get("mcp_trace_timing"), dict) else {}
    )
    context_metrics = (
        timing.get("context_metrics") if isinstance(timing.get("context_metrics"), dict) else {}
    )
    sdk_elapsed = _float_or_none(runner_timing.get("openai_agents_elapsed_s"))
    if sdk_elapsed is None:
        return None
    residual = sdk_elapsed
    mcp_elapsed = _float_or_none(mcp_timing.get("total_elapsed_s"))
    if mcp_elapsed is not None:
        residual -= mcp_elapsed
    if context_metrics.get("available"):
        span_duration = _float_or_none(context_metrics.get("response_span_duration_s"))
        if span_duration is not None:
            residual -= span_duration
    return _round_duration(residual)


def _compact_metric_group(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "available",
        "source",
        "limitations",
        "total_input_tokens",
        "total_cached_input_tokens",
        "total_uncached_input_tokens",
        "cache_hit_ratio",
        "cached_input_token_ratio",
        "provider_prompt_cache_observed",
        "trace_event_count",
        "observe_response_count",
        "raw_fpv_observation_count",
        "tool_response_bytes_total",
        "largest_tool_response_bytes",
        "continuation_attempt_count",
        "attempt_event_count",
        "retry_scheduled_count",
        "failure_event_count",
        "success_event_count",
        "failure_classes",
        "provider_reasons",
        "attempted_models",
        "attempted_provider_profiles",
        "attempted_wire_apis",
        "retry_delay_s_total",
        "retry_delay_count",
        "retry_exhausted",
        "final_outcomes",
        "event_count",
        "enabled",
        "modes",
        "compacted_item_count",
        "unchanged_item_count",
        "repeated_item_count",
        "input_bytes_before",
        "input_bytes_after",
        "input_bytes_reduced",
        "input_byte_reduction_ratio",
        "max_input_bytes_before",
        "max_input_bytes_after",
        "max_input_bytes_reduced",
        "metric_map_output_count",
        "repeated_metric_map_output_count",
        "metric_map_delta_compacted_count",
        "metric_map_bytes_before",
        "metric_map_bytes_after",
        "metric_map_bytes_reduced",
        "metric_map_byte_reduction_ratio",
        "raw_fpv_image_memory_enabled",
        "raw_fpv_image_memory_modes",
        "raw_fpv_image_item_count",
        "raw_fpv_image_retained_count",
        "raw_fpv_image_evicted_count",
        "raw_fpv_image_bytes_before",
        "raw_fpv_image_bytes_after",
        "raw_fpv_image_bytes_reduced",
        "raw_fpv_image_byte_reduction_ratio",
        "reason",
        "provider_reason",
        "retryable",
        "resume_available",
        "detail_schema",
        "raw_fpv_candidate_budget",
        "raw_fpv_repeated_failure_limit",
        "max_observe_per_waypoint",
        "candidate_attempt_count",
        "repeated_failure_count",
        "repeated_failure_limit_hit_count",
        "observe_waypoint_count",
    )
    compact = {key: metrics.get(key) for key in keys if key in metrics}
    detail = metrics.get("detail")
    if isinstance(detail, str) and detail:
        try:
            parsed = json.loads(detail)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            compact.setdefault("detail_schema", parsed.get("schema"))
            for key in (
                "raw_fpv_candidate_budget",
                "raw_fpv_repeated_failure_limit",
                "max_observe_per_waypoint",
                "candidate_attempt_count",
            ):
                if key in parsed:
                    compact.setdefault(key, parsed.get(key))
            repeated = parsed.get("repeated_failure_fingerprints")
            if isinstance(repeated, list):
                compact.setdefault("repeated_failure_count", len(repeated))
            hits = parsed.get("repeated_failure_limit_hits")
            if isinstance(hits, list):
                compact.setdefault("repeated_failure_limit_hit_count", len(hits))
            observe_counts = parsed.get("observe_count_by_waypoint")
            if isinstance(observe_counts, dict):
                compact.setdefault("observe_waypoint_count", len(observe_counts))
    return compact


def _nearest_rank_percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(len(ordered) * percentile + 0.999999) - 1))
    return ordered[index]


def _ratio(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


def _estimated_tokens_from_chars(char_count: int) -> int:
    if char_count <= 0:
        return 0
    return max(1, round(char_count / 4))


def _continuation_attempt_count(timing: dict[str, Any]) -> int:
    attempts = timing.get("openai_agents_attempts")
    if not isinstance(attempts, list):
        return 0
    return sum(
        1
        for attempt in attempts
        if isinstance(attempt, dict) and int(attempt.get("attempt_index") or 0) > 0
    )


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

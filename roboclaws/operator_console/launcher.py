"""Safe launcher for operator-console coding-agent routes."""

from __future__ import annotations

import json
import os
import signal
import socket
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.launch.catalog import resolve_task_launch
from roboclaws.operator_console.locks import ResourceLock
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleRoute, accepted_isaac_preflight, get_route
from roboclaws.operator_console.state import resolve_display_run_dir

DEFAULT_MCP_HOST = "127.0.0.1"
DEFAULT_MCP_PORT = 18788
CODEX_PROVIDER_DEFAULT = "codex-env"
CODEX_PROVIDER_DEFAULT_MODELS = {
    "codex-env": "gpt-5.5",
    "mify": "xiaomi/mimo-v2.5",
}
CODEX_PROVIDER_REQUIRED_ENV = {
    "codex-env": ("CODEX_BASE_URL", "CODEX_API_KEY"),
    "mify": ("XM_LLM_API_KEY",),
}
CLAUDE_PROVIDER_DEFAULT = "mimo-anthropic"
CLAUDE_PROVIDER_DEFAULT_MODELS = {
    "kimi-anthropic": "kimi-k2.6",
    "mimo-anthropic": "mimo-v2.5",
    "mify-anthropic": "xiaomi/mimo-v2.5",
}
CLAUDE_PROVIDER_REQUIRED_ENV = {
    "kimi-anthropic": ("KIMI_API_KEY",),
    "mimo-anthropic": ("MIMO_TP_KEY",),
    "mify-anthropic": ("XM_LLM_API_KEY",),
}
ALLOWED_ENV_OVERRIDES = {"ROBOCLAWS_CODEX_PROVIDER", "ROBOCLAWS_CLAUDE_PROVIDER"}


class ConsoleLaunchError(ValueError):
    """User-facing launch validation error."""


@dataclass(frozen=True)
class LaunchRequest:
    route_id: str
    prompt: str = ""
    overrides: dict[str, str] | None = None
    env_overrides: dict[str, str] | None = None
    gates: dict[str, bool] | None = None


def load_repo_dotenv(root: Path, env: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment with repo-local ``.env`` values loaded when present."""

    env_map = dict(os.environ if env is None else env)
    dotenv_path = root / ".env"
    if not dotenv_path.exists():
        return env_map
    for raw_line in dotenv_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in env_map:
            continue
        env_map[key] = _clean_dotenv_value(value)
    return env_map


def provider_key_present(route: ConsoleRoute, env: dict[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    if route.driver == "claude":
        return _claude_provider_status(env_map)["ok"]
    if route.driver == "codex":
        return _codex_provider_status(env_map)["ok"]
    return False


def build_launch_argv(
    route: ConsoleRoute,
    *,
    root: Path,
    run_id: str,
    prompt: str = "",
    overrides: dict[str, str] | None = None,
) -> list[str]:
    """Build a fixed argv list for a console route."""

    request_overrides = overrides or {}
    _validate_override_keys(route, request_overrides)
    output_dir = console_output_root(root) / "runs" / run_id
    overridden_keys = set(request_overrides)
    default_overrides = [
        item for item in route.default_overrides if _override_key(item) not in overridden_keys
    ]
    args = [
        route.task,
        route.driver,
        route.profile,
        f"backend={route.backend}",
        *default_overrides,
    ]
    args.append(f"output_dir={output_dir}")
    for key in route.required_overrides:
        value = request_overrides.get(key)
        if not value:
            raise ConsoleLaunchError(f"missing required route parameter: {key}")
        args.append(f"{key}={value}")
    for key in sorted(request_overrides):
        if key in route.required_overrides:
            continue
        args.append(f"{key}={request_overrides[key]}")
    if prompt:
        if not route.supports_prompt:
            raise ConsoleLaunchError(
                "This route cannot accept a custom prompt safely. Use the default task prompt."
            )
        args.append(f"prompt={prompt}")

    resolve_task_launch(args)
    return ["just", "task::run", *args]


def start_console_run(
    root: Path,
    request: LaunchRequest,
    *,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Validate gates, acquire the route lock, and spawn the live run."""

    run_env = load_repo_dotenv(root, env)
    route = get_route(request.route_id)
    gate_payload = request.gates or {}
    overrides = request.overrides or {}
    env_overrides = request.env_overrides or {}
    run_env = _apply_env_overrides(route, run_env, env_overrides)
    readiness = route_readiness(root, route, overrides=overrides, gates=gate_payload, env=run_env)
    if not readiness["can_start"]:
        raise ConsoleLaunchError(str(readiness["blocker"]))

    run_id = _new_run_id(route)
    argv = build_launch_argv(
        route,
        root=root,
        run_id=run_id,
        prompt=request.prompt,
        overrides=overrides,
    )
    run_dir = console_output_root(root) / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log_path = run_dir / "console-launch.log"
    lock = ResourceLock(root, route.lock_name)
    lock_state = lock.acquire(run_id=run_id)
    process: subprocess.Popen[bytes] | None = None
    try:
        with log_path.open("ab") as log_stream:
            process = subprocess.Popen(
                argv,
                cwd=root,
                env=run_env,
                stdout=log_stream,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        lock_state = lock.update_pid(run_id=run_id, pid=process.pid)
    except Exception:
        if process is not None:
            process.terminate()
        lock.release(run_id=run_id, force=True)
        raise
    state = {
        "run_id": run_id,
        "route": route.to_payload(),
        "phase": "starting",
        "pid": process.pid,
        "started_at_epoch": time.time(),
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "backend_lock": route.lock_name,
        "lock": lock_state.to_payload(),
        "argv": argv,
        "env_overrides": _public_env_overrides(env_overrides),
        "run_dir": str(run_dir),
    }
    (run_dir / "operator_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def route_readiness(
    root: Path,
    route: ConsoleRoute,
    *,
    overrides: dict[str, str] | None = None,
    env_overrides: dict[str, str] | None = None,
    gates: dict[str, bool] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return route gate state used by both API and UI."""

    if not route.enabled:
        return {
            "can_start": False,
            "blocker": route.disabled_reason,
            "blocker_kind": "unavailable",
            "gates": [],
        }

    env_map = _apply_env_overrides(route, load_repo_dotenv(root, env), env_overrides or {})
    override_map = overrides or {}
    gate_map = gates or {}
    gate_rows: list[dict[str, Any]] = []
    blocker = ""
    lock_state = ResourceLock(root, route.lock_name).read()
    attachable_run = _attachable_run_payload(root, lock_state)
    lock_active = lock_state.held and (not lock_state.stale or bool(attachable_run))
    real_movement_enabled = _truthy_override(override_map.get("real_movement_enabled"))
    if lock_active:
        if attachable_run:
            blocker = (
                f"Backend lock is held by run {attachable_run['run_id']}. "
                "Attach to the existing run or wait for it to finish."
            )
        else:
            blocker = "Backend lock is held by another run. Open that run or wait for it to finish."
        blocker_kind = "locked"
    else:
        blocker_kind = ""
    for gate in route.gates:
        ok = True
        message = "Ready"
        evidence = ""
        kind = "ready"
        severity = gate.severity
        blocks_start = gate.required
        if gate.kind == "provider_key":
            provider_status = _provider_status(route, env_map)
            ok = provider_status["ok"]
            if not ok:
                label = route.driver_label or route.driver
                message = str(provider_status["message"] or f"No {label} provider route found.")
                kind = "needs_provider"
        elif gate.kind == "isaac_preflight":
            accepted = accepted_isaac_preflight(root)
            ok = accepted is not None
            evidence = str(accepted or "")
            if not ok:
                message = (
                    "No accepted Isaac runtime preflight or smoke marker found. "
                    "Launch can start; backend diagnostics will report concrete runtime failures."
                )
                kind = "isaac_runtime_unverified"
        elif gate.kind == "mcp_port_free":
            host = _override_host(override_map)
            port = _override_port(override_map)
            ok = _tcp_port_free(host, port)
            evidence = f"{host}:{port}"
            if not ok:
                message = (
                    f"MCP port {host}:{port} is already accepting connections. "
                    "Pick another port or stop the existing server."
                )
                kind = "mcp_port_in_use"
        elif gate.kind == "request_field":
            ok = bool(override_map.get(gate.id))
            if not ok:
                message = "Attach a completed Agibot map context JSON."
                kind = "needs_agibot_context"
        elif gate.kind == "operator_gate":
            blocks_start = real_movement_enabled
            ok = gate_map.get(gate.id) is True
            if not ok:
                if real_movement_enabled:
                    message = (
                        "Real movement is enabled; localization, run enablement, "
                        "and E-stop/manual-stop readiness must be accepted before launch."
                    )
                    kind = "needs_real_movement_gate"
                else:
                    message = (
                        "Dry-run launch can start; this evidence is required for real movement."
                    )
                    kind = "real_movement_gate_pending"
        if ok:
            kind = "ready"
        if not ok and blocks_start and not blocker:
            blocker = message
            blocker_kind = kind
        gate_rows.append(
            {
                "id": gate.id,
                "label": gate.label,
                "status": "ready" if ok else "needs_action",
                "kind": kind,
                "severity": severity,
                "required": blocks_start,
                "blocks_start": blocks_start,
                "message": message,
                "evidence": evidence,
                "help_text": gate.help_text,
            }
        )
    return {
        "can_start": not blocker,
        "blocker": blocker,
        "blocker_kind": blocker_kind,
        "lock": lock_state.to_payload(),
        "attachable_run": attachable_run,
        "provider": _provider_status(route, env_map),
        "gates": gate_rows,
    }


def stop_console_run(root: Path, run_id: str, *, emergency: bool = False) -> dict[str, Any]:
    run_dir = console_output_root(root) / "runs" / run_id
    state_path = run_dir / "operator_state.json"
    if not state_path.exists():
        raise ConsoleLaunchError(f"unknown run id: {run_id}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    display_run_dir = resolve_display_run_dir(run_dir)
    terminal_phase = "human_takeover_stop" if emergency else "stopped_by_operator"
    _stop_live_child_run(display_run_dir)
    _mark_live_child_stopped(display_run_dir, terminal_phase)
    pid = state.get("pid")
    _terminate_process_group(pid if isinstance(pid, int) else None)
    state["phase"] = terminal_phase
    state["terminal_reason"] = state["phase"]
    state["stopped_at_epoch"] = time.time()
    state["display_run_dir"] = str(display_run_dir)
    state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    route_payload = state.get("route") or {}
    lock_name = str(route_payload.get("lock_name") or state.get("backend_lock") or "")
    if lock_name:
        ResourceLock(root, lock_name).release(run_id=run_id, force=True)
    return state


def _validate_override_keys(route: ConsoleRoute, overrides: dict[str, str]) -> None:
    allowed = {
        "seed",
        "seeds",
        "generated_mess_count",
        "context_json",
        "visual_grounding",
        "visual_grounding_timeout",
        "visual_grounding_timeout_s",
        "scene_source",
        "scene_index",
        "isaac_scene_usd_path",
        "robot_views",
        "record_robot_views",
        "real_movement_enabled",
        "run_dir",
        "policy",
        "host",
        "port",
    }
    for key, value in overrides.items():
        if key not in allowed:
            raise ConsoleLaunchError(f"unsupported route parameter: {key}")
        if "\x00" in value:
            raise ConsoleLaunchError(f"invalid NUL byte in route parameter: {key}")
        if key == "port":
            _parse_port(value)
    for key in route.required_overrides:
        if key not in allowed:
            raise ConsoleLaunchError(f"route registry uses unsupported parameter: {key}")


def _validate_env_overrides(route: ConsoleRoute, env_overrides: dict[str, str]) -> None:
    if env_overrides and route.driver not in {"codex", "claude"}:
        raise ConsoleLaunchError("provider overrides are only supported for coding-agent routes")
    for key, value in env_overrides.items():
        if key not in ALLOWED_ENV_OVERRIDES:
            raise ConsoleLaunchError(f"unsupported provider override: {key}")
        if "\x00" in value or "\n" in value or "\r" in value:
            raise ConsoleLaunchError(f"invalid control character in provider override: {key}")
        if key == "ROBOCLAWS_CODEX_PROVIDER" and route.driver != "codex":
            raise ConsoleLaunchError("Codex provider override is only supported for Codex routes")
        if key == "ROBOCLAWS_CLAUDE_PROVIDER" and route.driver != "claude":
            raise ConsoleLaunchError("Claude provider override is only supported for Claude routes")
        if key == "ROBOCLAWS_CODEX_PROVIDER" and value not in CODEX_PROVIDER_DEFAULT_MODELS:
            raise ConsoleLaunchError(
                f"unsupported Codex provider override: {value}; expected codex-env or mify"
            )
        if key == "ROBOCLAWS_CLAUDE_PROVIDER" and value not in CLAUDE_PROVIDER_DEFAULT_MODELS:
            raise ConsoleLaunchError(
                "unsupported Claude provider override: "
                f"{value}; expected kimi-anthropic, mimo-anthropic, or mify-anthropic"
            )


def _apply_env_overrides(
    route: ConsoleRoute,
    env_map: dict[str, str],
    env_overrides: dict[str, str],
) -> dict[str, str]:
    clean = {str(key): str(value) for key, value in env_overrides.items() if str(value) != ""}
    _validate_env_overrides(route, clean)
    if not clean:
        return env_map
    merged = dict(env_map)
    merged.update(clean)
    return merged


def _public_env_overrides(env_overrides: dict[str, str]) -> dict[str, str]:
    return {
        str(key): str(value)
        for key, value in env_overrides.items()
        if key in ALLOWED_ENV_OVERRIDES and str(value) != ""
    }


def _provider_status(route: ConsoleRoute, env_map: dict[str, str]) -> dict[str, Any]:
    if route.driver == "codex":
        return _codex_provider_status(env_map)
    if route.driver == "claude":
        return _claude_provider_status(env_map)
    return {
        "driver": route.driver,
        "provider": "",
        "model": "",
        "required_env": [],
        "missing_env": [],
        "ok": provider_key_present(route, env_map),
        "message": "",
    }


def _claude_provider_status(env_map: dict[str, str]) -> dict[str, Any]:
    provider = (
        env_map.get("ROBOCLAWS_CLAUDE_PROVIDER")
        or env_map.get("ROBOCLAWS_CODE_AGENT_PROVIDER")
        or CLAUDE_PROVIDER_DEFAULT
    )
    model = env_map.get("ROBOCLAWS_CLAUDE_MODEL") or env_map.get("ROBOCLAWS_CODE_AGENT_MODEL")
    if provider not in CLAUDE_PROVIDER_DEFAULT_MODELS:
        return {
            "driver": "claude",
            "provider": provider,
            "model": model or "",
            "required_env": [],
            "missing_env": [],
            "ok": False,
            "message": (
                f"Unsupported Claude provider {provider!r}; choose Kimi, MiMo token plan, "
                "or MiMo mify."
            ),
        }
    model = model or CLAUDE_PROVIDER_DEFAULT_MODELS[provider]
    required_env = list(CLAUDE_PROVIDER_REQUIRED_ENV[provider])
    missing_env = [key for key in required_env if not env_map.get(key)]
    if missing_env:
        required = " and ".join(required_env)
        message = f"Claude provider {provider} requires {required} in repo .env."
    else:
        message = ""
    return {
        "driver": "claude",
        "provider": provider,
        "model": model,
        "required_env": required_env,
        "missing_env": missing_env,
        "ok": not missing_env,
        "message": message,
    }


def _codex_provider_status(env_map: dict[str, str]) -> dict[str, Any]:
    provider = (
        env_map.get("ROBOCLAWS_CODEX_PROVIDER")
        or env_map.get("ROBOCLAWS_CODE_AGENT_PROVIDER")
        or CODEX_PROVIDER_DEFAULT
    )
    model = env_map.get("ROBOCLAWS_CODEX_MODEL") or env_map.get("ROBOCLAWS_CODE_AGENT_MODEL")
    if provider not in CODEX_PROVIDER_DEFAULT_MODELS:
        return {
            "driver": "codex",
            "provider": provider,
            "model": model or "",
            "required_env": [],
            "missing_env": [],
            "ok": False,
            "message": f"Unsupported Codex provider {provider!r}; choose codex-env or mify.",
        }
    model = model or CODEX_PROVIDER_DEFAULT_MODELS[provider]
    required_env = list(CODEX_PROVIDER_REQUIRED_ENV[provider])
    missing_env = [key for key in required_env if not env_map.get(key)]
    if missing_env:
        if provider == "codex-env":
            message = (
                "Codex provider codex-env requires CODEX_BASE_URL and CODEX_API_KEY "
                "in repo .env. Choose mify explicitly only when using XM_LLM_API_KEY."
            )
        else:
            message = "Codex provider mify requires XM_LLM_API_KEY in repo .env."
    else:
        message = ""
    return {
        "driver": "codex",
        "provider": provider,
        "model": model,
        "required_env": required_env,
        "missing_env": missing_env,
        "ok": not missing_env,
        "message": message,
    }


def _attachable_run_payload(root: Path, lock_state: Any) -> dict[str, Any] | None:
    if not lock_state.held or not lock_state.owner_run_id:
        return None
    run_dir = console_output_root(root) / "runs" / lock_state.owner_run_id
    state_path = run_dir / "operator_state.json"
    if not state_path.exists():
        return None
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    route_payload = state.get("route") if isinstance(state.get("route"), dict) else {}
    display_run_dir = resolve_display_run_dir(run_dir)
    live_status = _read_json(display_run_dir / "live_status.json")
    active_pid = _live_run_pid(display_run_dir) or lock_state.pid
    if lock_state.stale and not _display_run_attachable(display_run_dir, live_status, active_pid):
        return None
    return {
        "run_id": str(state.get("run_id") or lock_state.owner_run_id),
        "route_id": str(route_payload.get("id") or ""),
        "route_label": str(route_payload.get("label") or "Agent run"),
        "phase": str(live_status.get("phase") or state.get("phase") or "running"),
        "run_dir": str(state.get("run_dir") or run_dir),
        "display_run_dir": str(display_run_dir),
        "backend_lock": str(state.get("backend_lock") or lock_state.name),
        "pid": active_pid,
        "started_at": str(state.get("started_at") or ""),
    }


def _display_run_attachable(
    display_run_dir: Path,
    live_status: dict[str, Any],
    active_pid: int | None,
) -> bool:
    phase = str(live_status.get("phase") or "").lower()
    if phase in {"finished", "failed", "stopped_by_operator", "human_takeover_stop"} and (
        "exit_status" in live_status
    ):
        return False
    if phase:
        return True
    if active_pid and _pid_exists(active_pid):
        return True
    if _tmux_session_active(display_run_dir):
        return True
    return False


def _live_run_pid(display_run_dir: Path) -> int | None:
    server_pid_path = display_run_dir / "server.pid"
    if not server_pid_path.is_file():
        return None
    try:
        pid = int(server_pid_path.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None
    return pid if pid > 0 else None


def _stop_live_child_run(display_run_dir: Path) -> None:
    live_pid = _live_run_pid(display_run_dir)
    stop_pids = _live_run_stop_pids(live_pid)
    _stop_docker_containers_for_run(display_run_dir)
    _kill_tmux_session(display_run_dir)
    for pid in stop_pids:
        _terminate_process_group(pid)


def _mark_live_child_stopped(display_run_dir: Path, phase: str) -> None:
    display_run_dir.mkdir(parents=True, exist_ok=True)
    status_path = display_run_dir / "live_status.json"
    payload = _read_json(status_path)
    payload.update(
        {
            "phase": phase,
            "terminal_reason": phase,
            "finished_at_epoch": time.time(),
            "exit_status": 130,
        }
    )
    status_path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def _live_run_stop_pids(live_pid: int | None) -> list[int]:
    if not live_pid or live_pid <= 0:
        return []
    pids = [live_pid]
    parent_pid = _process_parent_pid(live_pid)
    if parent_pid and _safe_process_pid(parent_pid):
        pids.append(parent_pid)
        pids.extend(_descendant_pids(parent_pid))
    else:
        pids.extend(_descendant_pids(live_pid))
    return _dedupe_pids(pids)


def _terminate_process_group(pid: int | None) -> None:
    if not pid or pid <= 0:
        return
    _signal_process_group_or_pid(pid, signal.SIGTERM)
    deadline = time.monotonic() + 1.0
    while _pid_exists(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    if _pid_exists(pid):
        _signal_process_group_or_pid(pid, signal.SIGKILL)


def _signal_process_group_or_pid(pid: int, sig: signal.Signals) -> None:
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError:
        pgid = pid
    except (PermissionError, OSError):
        pgid = None
    if pgid and pgid > 0:
        try:
            os.killpg(pgid, int(sig))
            return
        except ProcessLookupError:
            pass
        except (PermissionError, OSError):
            pass
    try:
        os.kill(pid, int(sig))
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _process_parent_pid(pid: int) -> int | None:
    try:
        raw = (Path("/proc") / str(pid) / "stat").read_text(encoding="utf-8")
    except OSError:
        return None
    return _parse_proc_stat_parent_pid(raw)


def _descendant_pids(root_pid: int) -> list[int]:
    children_by_parent: dict[int, list[int]] = {}
    try:
        stat_paths = list(Path("/proc").glob("[0-9]*/stat"))
    except OSError:
        return []
    for stat_path in stat_paths:
        try:
            pid = int(stat_path.parent.name)
            parent_pid = _parse_proc_stat_parent_pid(stat_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if parent_pid is None:
            continue
        children_by_parent.setdefault(parent_pid, []).append(pid)
    descendants: list[int] = []
    queue = list(children_by_parent.get(root_pid, []))
    while queue:
        pid = queue.pop(0)
        if not _safe_process_pid(pid):
            continue
        descendants.append(pid)
        queue.extend(children_by_parent.get(pid, []))
    return descendants


def _parse_proc_stat_parent_pid(raw: str) -> int | None:
    try:
        suffix = raw.rsplit(") ", 1)[1]
        fields = suffix.split()
        return int(fields[1])
    except (IndexError, ValueError):
        return None


def _safe_process_pid(pid: int) -> bool:
    return pid > 1 and pid not in {os.getpid(), os.getppid()}


def _dedupe_pids(pids: list[int]) -> list[int]:
    seen: set[int] = set()
    output: list[int] = []
    for pid in pids:
        if pid in seen or not _safe_process_pid(pid):
            continue
        seen.add(pid)
        output.append(pid)
    return output


def _stop_docker_containers_for_run(display_run_dir: Path) -> None:
    workspace = (display_run_dir / "agent-docker-workspace").resolve()
    if not workspace.exists():
        return
    for container_id in _docker_container_ids_with_mount(workspace):
        subprocess.run(
            ["docker", "stop", "--time", "5", container_id],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )


def _docker_container_ids_with_mount(source: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["docker", "ps", "-q"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    container_ids: list[str] = []
    for container_id in result.stdout.split():
        try:
            inspect = subprocess.run(
                ["docker", "inspect", "--format", "{{json .Mounts}}", container_id],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (FileNotFoundError, OSError):
            continue
        if inspect.returncode != 0:
            continue
        try:
            mounts = json.loads(inspect.stdout)
        except json.JSONDecodeError:
            continue
        if not isinstance(mounts, list):
            continue
        for mount in mounts:
            if not isinstance(mount, dict):
                continue
            mount_source = mount.get("Source")
            if not mount_source:
                continue
            try:
                candidate = Path(str(mount_source)).resolve()
            except OSError:
                continue
            if candidate == source:
                container_ids.append(container_id)
                break
    return container_ids


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _tmux_session_active(display_run_dir: Path) -> bool:
    session_path = display_run_dir / "tmux_session.txt"
    if not session_path.is_file():
        return False
    try:
        session_name = session_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if not session_name:
        return False
    result = subprocess.run(
        ["tmux", "has-session", "-t", session_name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return result.returncode == 0


def _kill_tmux_session(display_run_dir: Path) -> None:
    session_path = display_run_dir / "tmux_session.txt"
    if not session_path.is_file():
        return
    try:
        session_name = session_path.read_text(encoding="utf-8").strip()
    except OSError:
        return
    if not session_name:
        return
    subprocess.run(
        ["tmux", "kill-session", "-t", session_name],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _override_key(value: str) -> str:
    return value.split("=", 1)[0]


def _clean_dotenv_value(value: str) -> str:
    clean = value.strip()
    if clean.startswith("export "):
        clean = clean.removeprefix("export ").strip()
    if len(clean) >= 2 and clean[0] == clean[-1] and clean[0] in {"'", '"'}:
        clean = clean[1:-1]
    return clean


def _override_host(overrides: dict[str, str]) -> str:
    host = str(overrides.get("host") or DEFAULT_MCP_HOST).strip()
    return host or DEFAULT_MCP_HOST


def _override_port(overrides: dict[str, str]) -> int:
    return _parse_port(str(overrides.get("port") or DEFAULT_MCP_PORT))


def _parse_port(value: str) -> int:
    try:
        port = int(str(value).strip())
    except ValueError as exc:
        raise ConsoleLaunchError(f"invalid MCP port: {value}") from exc
    if not 1 <= port <= 65535:
        raise ConsoleLaunchError(f"invalid MCP port: {value}")
    return port


def _truthy_override(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _tcp_port_free(host: str, port: int) -> bool:
    probe_host = "127.0.0.1" if host in {"0.0.0.0", "::"} else host
    try:
        with socket.create_connection((probe_host, port), timeout=0.2):
            return False
    except OSError:
        return True


def _new_run_id(route: ConsoleRoute) -> str:
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    return f"{timestamp}-{route.id}"

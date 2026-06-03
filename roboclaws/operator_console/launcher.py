"""Safe launcher for Codex operator-console routes."""

from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.launch.catalog import resolve_task_launch
from roboclaws.operator_console.locks import ResourceLock
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleRoute, accepted_isaac_preflight, get_route


class ConsoleLaunchError(ValueError):
    """User-facing launch validation error."""


@dataclass(frozen=True)
class LaunchRequest:
    route_id: str
    prompt: str = ""
    overrides: dict[str, str] | None = None
    gates: dict[str, bool] | None = None


def provider_key_present(env: dict[str, str] | None = None) -> bool:
    env_map = os.environ if env is None else env
    return any(
        env_map.get(key)
        for key in (
            "XM_LLM_API_KEY",
            "CODEX_API_KEY",
            "KIMI_API_KEY",
            "MIMO_TP_KEY",
            "OPENAI_API_KEY",
        )
    )


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

    route = get_route(request.route_id)
    gate_payload = request.gates or {}
    overrides = request.overrides or {}
    readiness = route_readiness(root, route, overrides=overrides, gates=gate_payload, env=env)
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
                env=env,
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
        "run_dir": str(run_dir),
    }
    (run_dir / "operator_state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def route_readiness(
    root: Path,
    route: ConsoleRoute,
    *,
    overrides: dict[str, str] | None = None,
    gates: dict[str, bool] | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Return route gate state used by both API and UI."""

    if not route.enabled:
        return {"can_start": False, "blocker": route.disabled_reason, "gates": []}

    override_map = overrides or {}
    gate_map = gates or {}
    gate_rows: list[dict[str, Any]] = []
    blocker = ""
    lock_state = ResourceLock(root, route.lock_name).read()
    if lock_state.held and not lock_state.stale:
        blocker = "Backend lock is held by another run. Open that run or wait for it to finish."
    for gate in route.gates:
        ok = True
        message = "Ready"
        evidence = ""
        if gate.kind == "provider_key":
            ok = provider_key_present(env)
            if not ok:
                message = "Load a repo-local Codex provider key route before launch."
        elif gate.kind == "isaac_preflight":
            accepted = accepted_isaac_preflight(root)
            ok = accepted is not None or gate_map.get(gate.id) is True
            evidence = str(accepted or "")
            if not ok:
                message = "Isaac preflight has not passed. Run the preflight gate before launch."
        elif gate.kind == "request_field":
            ok = bool(override_map.get(gate.id))
            if not ok:
                message = (
                    "Attach context, localization, run enablement, and "
                    "E-stop readiness evidence."
                )
        elif gate.kind == "operator_gate":
            ok = gate_map.get(gate.id) is True
            if not ok:
                message = "Agibot operator gates are incomplete."
        if not ok and not blocker:
            blocker = message
        gate_rows.append(
            {
                "id": gate.id,
                "label": gate.label,
                "status": "ready" if ok else "needs_action",
                "message": message,
                "evidence": evidence,
            }
        )
    return {
        "can_start": not blocker,
        "blocker": blocker,
        "lock": lock_state.to_payload(),
        "gates": gate_rows,
    }


def stop_console_run(root: Path, run_id: str, *, emergency: bool = False) -> dict[str, Any]:
    run_dir = console_output_root(root) / "runs" / run_id
    state_path = run_dir / "operator_state.json"
    if not state_path.exists():
        raise ConsoleLaunchError(f"unknown run id: {run_id}")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    pid = state.get("pid")
    if isinstance(pid, int) and pid > 0:
        try:
            os.killpg(pid, 15)
        except ProcessLookupError:
            pass
        except PermissionError:
            os.kill(pid, 15)
    state["phase"] = "human_takeover_stop" if emergency else "stopped_by_operator"
    state["terminal_reason"] = state["phase"]
    state["stopped_at_epoch"] = time.time()
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
    for key in route.required_overrides:
        if key not in allowed:
            raise ConsoleLaunchError(f"route registry uses unsupported parameter: {key}")


def _override_key(value: str) -> str:
    return value.split("=", 1)[0]


def _new_run_id(route: ConsoleRoute) -> str:
    timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
    return f"{timestamp}-{route.id}"

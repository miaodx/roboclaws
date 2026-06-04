"""Normalize existing run artifacts into one operator-state payload."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.operator_console.redaction import redact_text
from roboclaws.operator_console.routes import ConsoleRoute


@dataclass(frozen=True)
class ArtifactLink:
    label: str
    path: Path
    kind: str

    def to_payload(self, root: Path) -> dict[str, str]:
        return {
            "label": self.label,
            "kind": self.kind,
            "path": str(self.path),
            "href": f"/artifacts/{self.path.relative_to(root)}"
            if _is_relative_to(self.path, root)
            else "",
        }


def derive_operator_state(
    root: Path, run_dir: Path, route: ConsoleRoute | None = None
) -> dict[str, Any]:
    """Read a run directory and return the console's normalized live state."""

    run_dir = run_dir.resolve()
    status = _read_json(run_dir / "operator_state.json")
    live_status = _read_json(run_dir / "live_status.json")
    run_result = _read_json(_latest_existing(run_dir, ("run_result.json",)))
    trace_path = _latest_existing(run_dir, ("trace.jsonl",))
    latest_trace = _last_jsonl(trace_path)
    checker = _checker_status(run_dir, run_result)
    terminal_reason = _terminal_reason(status, live_status, run_result)
    phase = str(
        status.get("phase")
        or live_status.get("phase")
        or live_status.get("status")
        or run_result.get("status")
        or "idle"
    )
    artifacts = [link.to_payload(root) for link in _artifact_links(run_dir)]
    latest_view_assets = _latest_view_assets(root, run_dir)
    public_result = _public_run_result_summary(run_result)

    return {
        "run_id": str(status.get("run_id") or run_dir.name),
        "route": status.get("route") or (route.to_payload() if route else None),
        "run_dir": str(run_dir),
        "phase": phase,
        "status": _status_from_phase(phase, checker, terminal_reason),
        "backend_lock": status.get("backend_lock") or (route.lock_name if route else ""),
        "pid": status.get("pid"),
        "started_at": status.get("started_at"),
        "elapsed_seconds": _elapsed_seconds(status),
        "latest_action": _latest_action(latest_trace, run_result),
        "latest_public_decision_evidence": _decision_evidence(latest_trace, run_result),
        "latest_tool_call": _tool_call_summary(latest_trace),
        "artifact_paths": artifacts,
        "latest_view_assets": latest_view_assets,
        "checker_status": checker,
        "terminal_reason": terminal_reason,
        "public_run_result": public_result,
        "controls": {
            "pause_available": bool(route.pause_supported) if route else False,
            "stop_available": phase not in {"passed", "failed", "stopped_by_operator"},
            "emergency_stop_required": bool(route.emergency_stop_required) if route else False,
        },
    }


def redacted_artifact_text(path: Path, *, max_bytes: int = 200_000) -> str:
    """Read a raw text artifact and redact secrets before serving it."""

    data = path.read_bytes()[:max_bytes]
    text = data.decode("utf-8", errors="replace")
    return redact_text(text)


def _read_json(path: Path) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _last_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


def _latest_existing(run_dir: Path, names: tuple[str, ...]) -> Path:
    candidates: list[Path] = []
    for name in names:
        candidates.extend(path for path in run_dir.rglob(name) if path.is_file())
    if not candidates:
        return run_dir / names[0]
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _artifact_links(run_dir: Path) -> list[ArtifactLink]:
    specs = (
        ("Report", "report.html", "html"),
        ("Run Result", "run_result.json", "json"),
        ("Trace", "trace.jsonl", "jsonl"),
        ("Agent Events", "codex-events.jsonl", "jsonl"),
        ("Driver Log", "driver.log", "log"),
        ("Checker Output", "checker.log", "log"),
        ("Runtime Map", "runtime_metric_map.json", "json"),
        ("Actionable Map", "actionable_semantic_map_snapshot.json", "json"),
    )
    links: list[ArtifactLink] = []
    for label, name, kind in specs:
        path = _latest_existing(run_dir, (name,))
        if path.exists():
            links.append(ArtifactLink(label=label, path=path.resolve(), kind=kind))
    return links


def _latest_view_assets(root: Path, run_dir: Path) -> dict[str, dict[str, str]]:
    patterns = {
        "fpv": ("*.fpv*.png", "*.fpv*.jpg", "*fpv*.png", "*fpv*.jpg"),
        "chase": ("*.chase*.png", "*.chase*.jpg", "*chase*.png", "*chase*.jpg"),
        "map": ("*map*.png", "*map*.jpg"),
        "grounding": ("*grounding*.png", "*bbox*.png", "*detection*.png"),
    }
    output: dict[str, dict[str, str]] = {}
    for key, globs in patterns.items():
        matches: list[Path] = []
        for pattern in globs:
            matches.extend(path for path in run_dir.rglob(pattern) if path.is_file())
        if not matches:
            continue
        path = max(matches, key=lambda item: item.stat().st_mtime).resolve()
        output[key] = {
            "path": str(path),
            "href": f"/artifacts/{path.relative_to(root)}" if _is_relative_to(path, root) else "",
            "mtime": str(path.stat().st_mtime),
        }
    return output


def _checker_status(run_dir: Path, run_result: dict[str, Any]) -> dict[str, Any]:
    checker_log = _latest_existing(run_dir, ("checker.log",))
    report = _latest_existing(run_dir, ("report.html",))
    ok = bool(
        run_result.get("ok")
        or run_result.get("success")
        or run_result.get("cleanup_success")
        or run_result.get("semantic_map_success")
    )
    return {
        "status": "passed" if ok and report.exists() else "pending" if not run_result else "failed",
        "report_exists": report.exists(),
        "checker_log": str(checker_log) if checker_log.exists() else "",
    }


def _terminal_reason(
    status: dict[str, Any], live_status: dict[str, Any], run_result: dict[str, Any]
) -> str:
    for payload in (status, live_status, run_result):
        for key in ("terminal_reason", "terminate_reason", "error_reason", "status"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def _status_from_phase(phase: str, checker: dict[str, Any], terminal_reason: str) -> str:
    lower = phase.lower()
    if lower in {"stopped_by_operator", "human_takeover_stop", "failed", "passed"}:
        return lower
    if checker.get("status") == "passed":
        return "passed"
    if terminal_reason and lower in {"failed", "error", "terminated"}:
        return "failed"
    if lower in {"running", "starting", "queued", "paused", "stopping"}:
        return lower
    return "idle"


def _elapsed_seconds(status: dict[str, Any]) -> float | None:
    value = status.get("started_at_epoch") or status.get("started_at")
    try:
        start = float(value)
    except (TypeError, ValueError):
        return None
    return max(0.0, time.time() - start)


def _latest_action(trace: dict[str, Any], run_result: dict[str, Any]) -> str:
    for payload in (trace, run_result):
        for key in ("action", "tool", "tool_name", "selected_action", "latest_action"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def _decision_evidence(trace: dict[str, Any], run_result: dict[str, Any]) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for key in ("goal", "observation_summary", "reasoning", "decision", "blocked_reason"):
        value = trace.get(key) or run_result.get(key)
        if value:
            evidence[key] = str(value)
    return evidence


def _tool_call_summary(trace: dict[str, Any]) -> dict[str, Any]:
    if not trace:
        return {}
    return {
        "name": trace.get("tool") or trace.get("tool_name") or trace.get("action") or "",
        "ok": trace.get("ok"),
        "latency_ms": trace.get("latency_ms") or trace.get("duration_ms"),
        "error": trace.get("error") or trace.get("error_reason") or "",
    }


def _public_run_result_summary(run_result: dict[str, Any]) -> dict[str, Any]:
    allowed = (
        "task",
        "backend",
        "policy",
        "profile",
        "status",
        "ok",
        "success",
        "cleanup_success",
        "semantic_map_success",
        "terminate_reason",
        "primitive_provenance",
    )
    return {key: run_result[key] for key in allowed if key in run_result}


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

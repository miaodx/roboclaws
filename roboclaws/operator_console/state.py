"""Normalize existing run artifacts into one operator-state payload."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.operator_console.redaction import redact_text
from roboclaws.operator_console.routes import ConsoleRoute

LIVE_RUN_MARKERS = (
    "live_status.json",
    "run_result.json",
    "trace.jsonl",
    "codex-events.jsonl",
    "claude-events.jsonl",
    "report.html",
    "runtime_metric_map.json",
    "tmux_session.txt",
    "driver.log",
    "openai-agents-events.jsonl",
    "openai-agents-trace.json",
)

AGENT_EVENT_GLOBS = (
    "codex-events*.jsonl",
    "claude-events*.jsonl",
    "openai-agents-events*.jsonl",
)


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
    display_run_dir = resolve_display_run_dir(run_dir)
    status = _read_json(run_dir / "operator_state.json")
    live_status = _read_json(_latest_existing(display_run_dir, ("live_status.json",)))
    run_result = _read_json(_latest_existing(display_run_dir, ("run_result.json",)))
    trace_path = _latest_existing(display_run_dir, ("trace.jsonl",))
    latest_trace = _last_robot_tool_jsonl(trace_path) or _last_jsonl(trace_path)
    phase = str(
        live_status.get("phase")
        or status.get("phase")
        or live_status.get("status")
        or run_result.get("status")
        or "idle"
    )
    checker = _checker_status(display_run_dir, run_result, phase)
    terminal_reason = _terminal_reason(status, live_status, run_result)
    artifacts = [link.to_payload(root) for link in _artifact_links(display_run_dir)]
    if display_run_dir != run_dir:
        artifacts.extend(link.to_payload(root) for link in _wrapper_artifact_links(run_dir))
    latest_view_assets = _latest_view_assets(root, display_run_dir)
    public_result = _public_run_result_summary(run_result)
    latest_agent_message = _latest_agent_message(display_run_dir)

    return {
        "run_id": str(status.get("run_id") or run_dir.name),
        "display_run_id": _display_run_id(run_dir, display_run_dir),
        "route": status.get("route") or (route.to_payload() if route else None),
        "run_dir": str(run_dir),
        "display_run_dir": str(display_run_dir),
        "phase": phase,
        "status": _status_from_phase(phase, checker, terminal_reason),
        "status_label": _status_label(phase, terminal_reason),
        "backend_lock": status.get("backend_lock") or (route.lock_name if route else ""),
        "pid": status.get("pid"),
        "started_at": status.get("started_at"),
        "elapsed_seconds": _elapsed_seconds(status),
        "latest_action": _latest_action(latest_trace, run_result),
        "latest_public_decision_evidence": _decision_evidence(
            latest_trace, run_result, latest_agent_message
        ),
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


def resolve_display_run_dir(run_dir: Path) -> Path:
    """Return the nested live-attempt directory that currently owns evidence."""

    run_dir = run_dir.resolve()
    candidates = (
        [run_dir] if any((run_dir / marker).exists() for marker in LIVE_RUN_MARKERS) else []
    )
    for marker in LIVE_RUN_MARKERS:
        try:
            matches = run_dir.rglob(marker)
        except OSError:
            continue
        for path in matches:
            if not path.is_file():
                continue
            parent = path.parent.resolve()
            if parent not in candidates:
                candidates.append(parent)
    if not candidates:
        return run_dir
    return max(candidates, key=_run_dir_activity_mtime)


def redacted_artifact_text(path: Path, *, max_bytes: int = 200_000) -> str:
    """Read a raw text artifact and redact secrets before serving it."""

    data = path.read_bytes()
    if max_bytes > 0 and len(data) > max_bytes:
        head_bytes = max_bytes // 2
        tail_bytes = max_bytes - head_bytes
        omitted = len(data) - max_bytes
        marker = (
            f"\n\n[operator console truncated {omitted} raw bytes; "
            "showing beginning and end of artifact]\n\n"
        ).encode()
        data = data[:head_bytes] + marker + data[-tail_bytes:]
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


def _last_robot_tool_jsonl(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    payloads: list[dict[str, Any]] = []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads.append(payload)
    for index in range(len(payloads) - 1, -1, -1):
        payload = payloads[index]
        if isinstance(payload, dict) and _is_robot_tool_trace(payload):
            return _paired_tool_trace(payload, payloads[:index])
    return {}


def _is_robot_tool_trace(payload: dict[str, Any]) -> bool:
    tool = str(payload.get("tool") or payload.get("tool_name") or "")
    if not tool or tool == "<runtime>":
        return False
    return True


def _paired_tool_trace(trace: dict[str, Any], previous: list[dict[str, Any]]) -> dict[str, Any]:
    if trace.get("event") != "response":
        return trace
    request = trace.get("request") if isinstance(trace.get("request"), dict) else None
    if request:
        return _with_latency_from_request(trace, None)
    tool = str(trace.get("tool") or trace.get("tool_name") or "")
    for candidate in reversed(previous):
        if candidate.get("event") != "request":
            continue
        candidate_tool = str(candidate.get("tool") or candidate.get("tool_name") or "")
        if candidate_tool != tool:
            continue
        merged = dict(trace)
        candidate_request = candidate.get("request")
        if isinstance(candidate_request, dict):
            merged["request"] = candidate_request
        return _with_latency_from_request(merged, candidate)
    return trace


def _with_latency_from_request(
    trace: dict[str, Any], request_trace: dict[str, Any] | None
) -> dict[str, Any]:
    if trace.get("latency_ms") is not None or trace.get("duration_ms") is not None:
        return trace
    start = _numeric_trace_time(request_trace) if request_trace is not None else None
    end = _numeric_trace_time(trace)
    if start is None or end is None or end < start:
        return trace
    merged = dict(trace)
    merged["latency_ms"] = round((end - start) * 1000, 3)
    return merged


def _numeric_trace_time(trace: dict[str, Any] | None) -> float | None:
    if not trace:
        return None
    for key in ("ts", "timestamp", "wallclock_elapsed"):
        try:
            return float(trace.get(key))
        except (TypeError, ValueError):
            continue
    return None


def _latest_agent_message(run_dir: Path) -> str:
    event_paths: list[Path] = []
    for pattern in AGENT_EVENT_GLOBS:
        event_paths.extend(path for path in run_dir.glob(pattern) if path.is_file())
    event_paths = sorted(set(event_paths), key=_safe_mtime)
    for path in reversed(event_paths):
        message = _last_agent_message(path)
        if message:
            return message
    return ""


def _last_agent_message(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue
        text = _agent_message_text(payload)
        if text:
            return text
    return ""


def _agent_message_text(payload: dict[str, Any]) -> str:
    item = payload.get("item")
    if isinstance(item, dict) and item.get("type") == "agent_message":
        text = item.get("text")
        if text:
            return str(text)

    message = payload.get("message")
    if isinstance(message, dict) and _is_assistant_message_payload(payload, message):
        text = _message_content_text(message.get("content"))
        if text:
            return text

    if _is_assistant_payload(payload):
        text = _message_content_text(payload.get("content"))
        if text:
            return text

    summary = payload.get("summary")
    if isinstance(summary, dict):
        for key in ("final_output", "output_text", "message"):
            value = summary.get(key)
            if value:
                return str(value)
    return ""


def _is_assistant_message_payload(payload: dict[str, Any], message: dict[str, Any]) -> bool:
    return (
        str(payload.get("type") or "").lower() == "assistant"
        or str(message.get("role") or "").lower() == "assistant"
    )


def _is_assistant_payload(payload: dict[str, Any]) -> bool:
    return str(payload.get("role") or "").lower() == "assistant"


def _message_content_text(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    texts: list[str] = []
    for item in content:
        if isinstance(item, str):
            texts.append(item)
            continue
        if not isinstance(item, dict):
            continue
        if item.get("type") in {None, "text", "output_text"} and item.get("text"):
            texts.append(str(item["text"]))
    return "\n".join(text.strip() for text in texts if text and text.strip())


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
        ("Claude Events", "claude-events.jsonl", "jsonl"),
        ("OpenAI Agents Events", "openai-agents-events.jsonl", "jsonl"),
        ("OpenAI Agents Trace", "openai-agents-trace.json", "json"),
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


def _wrapper_artifact_links(run_dir: Path) -> list[ArtifactLink]:
    specs = (
        ("Console Launch Log", "console-launch.log", "log"),
        ("Operator State", "operator_state.json", "json"),
    )
    links: list[ArtifactLink] = []
    for label, name, kind in specs:
        path = run_dir / name
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
    preferred_dirs = {
        "fpv": ("robot_views",),
        "chase": ("robot_views",),
        "map": ("robot_views",),
    }
    output: dict[str, dict[str, str]] = {}
    for key, globs in patterns.items():
        matches: list[Path] = []
        for directory in preferred_dirs.get(key, ()):
            base = run_dir / directory
            if not base.is_dir():
                continue
            for pattern in globs:
                matches.extend(path for path in base.rglob(pattern) if path.is_file())
        if not matches:
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


def _checker_status(run_dir: Path, run_result: dict[str, Any], phase: str) -> dict[str, Any]:
    checker_log = _latest_existing(run_dir, ("checker.log",))
    report = _latest_existing(run_dir, ("report.html",))
    normalized_phase = phase.lower()
    if normalized_phase in {"failed", "error", "terminated"}:
        return {
            "status": "failed",
            "report_exists": report.exists(),
            "checker_log": str(checker_log) if checker_log.exists() else "",
            "message": "Checker failed." if checker_log.exists() else "Run failed.",
        }
    ok = _run_result_success(run_result)
    if ok and report.exists():
        return {
            "status": "passed",
            "report_exists": True,
            "checker_log": str(checker_log) if checker_log.exists() else "",
            "message": "Checker passed.",
        }
    if run_result:
        return {
            "status": "failed",
            "report_exists": report.exists(),
            "checker_log": str(checker_log) if checker_log.exists() else "",
            "message": "Checker failed." if checker_log.exists() else "Run result is present.",
        }
    if normalized_phase == "checking-result":
        return {
            "status": "running",
            "report_exists": report.exists(),
            "checker_log": str(checker_log) if checker_log.exists() else "",
            "message": "Checker is running.",
        }
    if _phase_is_active(normalized_phase):
        return {
            "status": "waiting",
            "report_exists": False,
            "checker_log": "",
            "message": "Checker will run when the live agent hands off to result checking.",
        }
    return {
        "status": "pending",
        "report_exists": False,
        "checker_log": str(checker_log) if checker_log.exists() else "",
        "message": "Checker has not run yet.",
    }


def _run_result_success(run_result: dict[str, Any]) -> bool:
    if not run_result:
        return False
    if _run_result_has_failure(run_result):
        return False
    for key in ("ok", "success", "cleanup_success", "semantic_map_success"):
        if run_result.get(key) is True:
            return True
    for key in ("cleanup_status", "completion_status", "final_status", "status"):
        if _is_success_string(run_result.get(key)):
            return True
    score = run_result.get("score")
    if isinstance(score, dict):
        for key in ("completion_status", "status"):
            if _is_success_string(score.get(key)):
                return True
    return False


def _run_result_has_failure(run_result: dict[str, Any]) -> bool:
    for key in ("ok", "success", "cleanup_success", "semantic_map_success"):
        if run_result.get(key) is False:
            return True
    for key in ("cleanup_status", "completion_status", "final_status", "status"):
        if _is_failure_string(run_result.get(key)):
            return True
    return False


def _is_success_string(value: Any) -> bool:
    return str(value).strip().lower() in {"success", "ok", "passed"}


def _is_failure_string(value: Any) -> bool:
    return str(value).strip().lower() in {"failed", "failure", "error"}


def _terminal_reason(
    status: dict[str, Any], live_status: dict[str, Any], run_result: dict[str, Any]
) -> str:
    for payload in (live_status, status, run_result):
        for key in ("terminal_reason", "terminate_reason", "error_reason", "reason", "status"):
            value = payload.get(key)
            if value:
                return str(value)
    return ""


def _status_from_phase(phase: str, checker: dict[str, Any], terminal_reason: str) -> str:
    lower = phase.lower()
    if _is_provider_transient_reason(terminal_reason):
        return "provider_transient_failed"
    if lower in {"stopped_by_operator", "human_takeover_stop", "failed", "passed"}:
        return lower
    if checker.get("status") == "passed":
        return "passed"
    if terminal_reason and lower in {"failed", "error", "terminated"}:
        return "failed"
    if _phase_is_active(lower):
        return lower
    return "idle"


def _status_label(phase: str, terminal_reason: str) -> str:
    if _is_provider_transient_reason(terminal_reason):
        return "Provider transient failure"
    return phase


def _is_provider_transient_reason(reason: str) -> bool:
    normalized = reason.lower()
    return "provider_transient_failure" in normalized or "provider transient" in normalized


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


def _phase_is_active(phase: str) -> bool:
    return phase in {
        "queued",
        "starting",
        "starting-server",
        "running",
        "running-codex",
        "running-claude",
        "running-openai-agents",
        "waiting-for-server-finish",
        "checking-result",
        "paused",
        "stopping",
    }


def _decision_evidence(
    trace: dict[str, Any], run_result: dict[str, Any], agent_message: str = ""
) -> dict[str, str]:
    evidence: dict[str, str] = {}
    for key in ("goal", "observation_summary", "reasoning", "decision", "blocked_reason"):
        value = trace.get(key) or run_result.get(key)
        if value:
            evidence[key] = str(value)
    if "observation_summary" not in evidence:
        summary = _trace_summary(trace)
        if summary:
            evidence["observation_summary"] = summary
    if agent_message:
        evidence.setdefault("decision", agent_message)
    return evidence


def _trace_summary(trace: dict[str, Any]) -> str:
    event = str(trace.get("event") or "")
    tool = str(trace.get("tool") or trace.get("tool_name") or trace.get("action") or "")
    if not tool:
        return ""
    response = trace.get("response") if isinstance(trace.get("response"), dict) else {}
    request = trace.get("request") if isinstance(trace.get("request"), dict) else {}
    if event == "request":
        args = _compact_tool_arguments(request)
        return f"Calling {tool}{args}."
    if event == "response" or response:
        status = response.get("status") or response.get("navigation_status") or ""
        ok = response.get("ok")
        suffix = _compact_response_detail(tool, response)
        if ok is True:
            return f"{tool} completed{suffix}."
        if ok is False:
            error = response.get("error") or response.get("error_reason") or "not ok"
            return f"{tool} failed: {error}."
        if status:
            return f"{tool} returned {status}{suffix}."
        return f"{tool} returned a response{suffix}."
    return f"Latest trace event: {tool}."


def _compact_tool_arguments(request: dict[str, Any]) -> str:
    for key in ("object_id", "fixture_id", "waypoint_id"):
        value = request.get(key)
        if value:
            return f" {key}={value}"
    return ""


def _compact_response_detail(tool: str, response: dict[str, Any]) -> str:
    for key in ("object_id", "fixture_id", "waypoint_id", "receptacle_id"):
        value = response.get(key)
        if value:
            return f" for {key}={value}"
    if tool == "observe":
        detections = response.get("visible_object_detections")
        if isinstance(detections, list):
            return f" with {len(detections)} visible detection(s)"
    return ""


def _tool_call_summary(trace: dict[str, Any]) -> dict[str, Any]:
    if not trace:
        return {}
    response = trace.get("response") if isinstance(trace.get("response"), dict) else {}
    request = trace.get("request") if isinstance(trace.get("request"), dict) else {}
    return {
        "name": trace.get("tool") or trace.get("tool_name") or trace.get("action") or "",
        "ok": trace.get("ok") if "ok" in trace else response.get("ok"),
        "arguments": request,
        "latency_ms": trace.get("latency_ms") or trace.get("duration_ms"),
        "error": trace.get("error") or trace.get("error_reason") or response.get("error") or "",
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
        "cleanup_status",
        "completion_status",
        "final_status",
        "terminate_reason",
        "primitive_provenance",
    )
    return {key: run_result[key] for key in allowed if key in run_result}


def _display_run_id(wrapper_run_dir: Path, display_run_dir: Path) -> str:
    if wrapper_run_dir == display_run_dir:
        return wrapper_run_dir.name
    try:
        return str(display_run_dir.relative_to(wrapper_run_dir))
    except ValueError:
        return display_run_dir.name


def _run_dir_activity_mtime(path: Path) -> float:
    mtimes: list[float] = []
    for marker in LIVE_RUN_MARKERS:
        marker_path = path / marker
        if marker_path.exists():
            try:
                mtimes.append(marker_path.stat().st_mtime)
            except OSError:
                pass
    if mtimes:
        return max(mtimes)
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True

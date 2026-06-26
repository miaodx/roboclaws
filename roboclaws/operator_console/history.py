"""Append-only run history for the operator console."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from roboclaws.core.json_sources import read_json_object
from roboclaws.operator_console.jsonl_sources import collect_jsonl_objects
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleLaunchSelection
from roboclaws.operator_console.state import (
    LIVE_RUN_MARKERS,
    display_run_id,
    resolve_display_run_dir,
)

HISTORY_FILENAME = "runs.jsonl"


@dataclass(frozen=True)
class HistorySourceError:
    """Operator-visible source error for latest-run history attachment."""

    path: Path
    label: str
    reason: str

    def to_payload(self) -> dict[str, str]:
        return {
            "label": self.label,
            "path": str(self.path),
            "reason": self.reason,
        }


def append_run_history(
    root: Path,
    *,
    run_id: str,
    selection: ConsoleLaunchSelection,
    run_dir: Path,
    started_at_epoch: float,
    started_at: str,
) -> None:
    """Append one launched run to the durable operator-console run index."""

    history_path = _history_path(root)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "operator_console_run_history_v1",
        "run_id": run_id,
        "selection_id": selection.id,
        "launch_label": selection.label,
        "world_id": selection.world_id,
        "backend_id": selection.backend_id,
        "intent_id": selection.intent_id,
        "agent_engine_id": selection.agent_engine_id,
        "provider_profile": selection.provider_profile or "",
        "evidence_lane": selection.evidence_lane,
        "scenario_setup": selection.scenario_setup,
        "lock_name": selection.lock_name,
        "run_dir": str(run_dir),
        "started_at_epoch": started_at_epoch,
        "started_at": started_at,
    }
    with history_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def latest_run_payload(root: Path) -> dict[str, Any]:
    """Return the newest artifact-backed run payload for history attach."""

    candidates, source_errors = _history_candidates(root)
    if source_errors:
        return _source_error_payload(source_errors)
    if not candidates:
        return {}
    return max(candidates, key=lambda item: float(item.get("activity_epoch") or 0.0))


def _history_candidates(root: Path) -> tuple[list[dict[str, Any]], tuple[HistorySourceError, ...]]:
    output_root = console_output_root(root)
    by_run_id: dict[str, dict[str, Any]] = {}
    rows, source_errors = _read_history_rows(root)
    for row in rows:
        run_id = str(row.get("run_id") or "")
        if not run_id:
            continue
        by_run_id[run_id] = row
    runs_dir = output_root / "runs"
    if runs_dir.is_dir():
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            by_run_id.setdefault(
                run_dir.name,
                {
                    "run_id": run_dir.name,
                    "run_dir": str(run_dir),
                },
            )
    candidates: list[dict[str, Any]] = []
    for run_id, row in by_run_id.items():
        payload, _payload_errors = _candidate_payload(root, run_id, row)
        if payload:
            candidates.append(payload)
    return candidates, source_errors


def _candidate_payload(
    root: Path, run_id: str, row: dict[str, Any]
) -> tuple[dict[str, Any], tuple[HistorySourceError, ...]]:
    output_root = console_output_root(root)
    run_dir = Path(str(row.get("run_dir") or output_root / "runs" / run_id))
    if not run_dir.is_absolute():
        run_dir = root / run_dir
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        return {}, ()
    display_run_dir = resolve_display_run_dir(run_dir)
    if not _has_attachable_artifact(display_run_dir):
        return {}, ()
    state, state_error = _read_json_source(run_dir / "operator_state.json", label="Operator State")
    if state_error:
        return (
            _candidate_source_error_payload(
                run_id=run_id,
                run_dir=run_dir,
                display_run_dir=display_run_dir,
                source_errors=(state_error,),
                row=row,
            ),
            (state_error,),
        )
    route_payload = (
        state.get("launch_selection") if isinstance(state.get("launch_selection"), dict) else {}
    )
    if not route_payload:
        route_payload = state.get("route") if isinstance(state.get("route"), dict) else {}
    selection_id = str(
        row.get("selection_id")
        or route_payload.get("selection_id")
        or route_payload.get("id")
        or ""
    )
    launch_label = str(row.get("launch_label") or route_payload.get("label") or "Agent run")
    activity_epoch = _run_activity_epoch(display_run_dir, run_dir, row)
    live_status, live_status_error = _read_json_source(
        display_run_dir / "live_status.json",
        label="Live Status",
    )
    source_errors = (live_status_error,) if live_status_error else ()
    payload = {
        "run_id": run_id,
        "selection_id": selection_id,
        "launch_label": launch_label,
        "run_dir": str(run_dir),
        "display_run_dir": str(display_run_dir),
        "display_run_id": display_run_id(run_dir, display_run_dir),
        "activity_epoch": activity_epoch,
        "started_at": str(row.get("started_at") or state.get("started_at") or ""),
        "phase": _latest_phase(live_status, state, source_errors=source_errors),
    }
    if source_errors:
        payload.update(_source_error_fields(source_errors))
    return payload, source_errors


def _read_history_rows(root: Path) -> tuple[list[dict[str, Any]], tuple[HistorySourceError, ...]]:
    path = _history_path(root)
    rows, issues = collect_jsonl_objects(path, label="Run History")
    return rows, tuple(
        HistorySourceError(path=issue.path, label=issue.label, reason=issue.history_reason())
        for issue in issues
    )


def _history_path(root: Path) -> Path:
    return console_output_root(root) / HISTORY_FILENAME


def _has_attachable_artifact(display_run_dir: Path) -> bool:
    return any((display_run_dir / marker).exists() for marker in LIVE_RUN_MARKERS)


def _run_activity_epoch(display_run_dir: Path, run_dir: Path, row: dict[str, Any]) -> float:
    mtimes: list[float] = []
    for marker in LIVE_RUN_MARKERS:
        marker_path = display_run_dir / marker
        if marker_path.exists():
            try:
                mtimes.append(marker_path.stat().st_mtime)
            except OSError:
                pass
    if mtimes:
        return max(mtimes)
    try:
        return run_dir.stat().st_mtime
    except OSError:
        pass
    try:
        return float(row.get("started_at_epoch") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _latest_phase(
    live_status: dict[str, Any],
    state: dict[str, Any],
    *,
    source_errors: tuple[HistorySourceError, ...] = (),
) -> str:
    if source_errors:
        return "failed"
    return str(live_status.get("phase") or state.get("phase") or "")


def _read_json_source(
    path: Path,
    *,
    label: str,
) -> tuple[dict[str, Any], HistorySourceError | None]:
    if not path.exists():
        return {}, None
    try:
        return read_json_object(path, label=label), None
    except ValueError as exc:
        cause = exc.__cause__
        if isinstance(cause, json.JSONDecodeError):
            return {}, HistorySourceError(
                path=path.resolve(),
                label=label,
                reason=f"invalid JSON at line {cause.lineno} column {cause.colno}",
            )
        return {}, HistorySourceError(
            path=path.resolve(), label=label, reason="expected JSON object"
        )
    except OSError as exc:
        return {}, HistorySourceError(path=path.resolve(), label=label, reason=str(exc))


def _candidate_source_error_payload(
    *,
    run_id: str,
    run_dir: Path,
    display_run_dir: Path,
    source_errors: tuple[HistorySourceError, ...],
    row: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "run_id": run_id,
        "selection_id": str(row.get("selection_id") or ""),
        "launch_label": str(row.get("launch_label") or "Agent run"),
        "run_dir": str(run_dir),
        "display_run_dir": str(display_run_dir),
        "display_run_id": display_run_id(run_dir, display_run_dir),
        "activity_epoch": _run_activity_epoch(display_run_dir, run_dir, row),
        "started_at": str(row.get("started_at") or ""),
        "phase": "failed",
    }
    payload.update(_source_error_fields(source_errors))
    return payload


def _source_error_payload(source_errors: tuple[HistorySourceError, ...]) -> dict[str, Any]:
    payload = {"run_id": "", "phase": "failed"}
    payload.update(_source_error_fields(source_errors))
    return payload


def _source_error_fields(source_errors: tuple[HistorySourceError, ...]) -> dict[str, Any]:
    labels = ", ".join(dict.fromkeys(error.label for error in source_errors))
    return {
        "status": "source_error",
        "status_label": "Source error",
        "error": f"operator history source error: {labels}",
        "source_errors": [error.to_payload() for error in source_errors],
    }

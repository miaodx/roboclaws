"""Append-only run history for the operator console."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import ConsoleLaunchSelection, ConsoleRoute
from roboclaws.operator_console.state import LIVE_RUN_MARKERS, resolve_display_run_dir

HISTORY_FILENAME = "runs.jsonl"


def append_run_history(
    root: Path,
    *,
    run_id: str,
    selection: ConsoleLaunchSelection | ConsoleRoute,
    run_dir: Path,
    started_at_epoch: float,
    started_at: str,
) -> None:
    """Append one launched run to the durable operator-console run index."""

    history_path = _history_path(root)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    launch = selection.selection if isinstance(selection, ConsoleRoute) else selection
    payload = {
        "schema": "operator_console_run_history_v1",
        "run_id": run_id,
        "selection_id": launch.id,
        "launch_label": launch.label,
        "world_id": launch.world_id,
        "backend_id": launch.backend_id,
        "intent_id": launch.intent_id,
        "agent_engine_id": launch.agent_engine_id,
        "provider_profile": launch.provider_profile or "",
        "evidence_lane": launch.evidence_lane,
        "scenario_setup": launch.scenario_setup,
        "lock_name": launch.lock_name,
        "run_dir": str(run_dir),
        "started_at_epoch": started_at_epoch,
        "started_at": started_at,
    }
    with history_path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(payload, sort_keys=True) + "\n")


def latest_run_payload(root: Path) -> dict[str, Any]:
    """Return the newest artifact-backed run payload for history attach."""

    candidates = _history_candidates(root)
    if not candidates:
        return {}
    return max(candidates, key=lambda item: float(item.get("activity_epoch") or 0.0))


def _history_candidates(root: Path) -> list[dict[str, Any]]:
    output_root = console_output_root(root)
    by_run_id: dict[str, dict[str, Any]] = {}
    for row in _read_history_rows(root):
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
        payload = _candidate_payload(root, run_id, row)
        if payload:
            candidates.append(payload)
    return candidates


def _candidate_payload(root: Path, run_id: str, row: dict[str, Any]) -> dict[str, Any]:
    output_root = console_output_root(root)
    run_dir = Path(str(row.get("run_dir") or output_root / "runs" / run_id))
    if not run_dir.is_absolute():
        run_dir = root / run_dir
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        return {}
    display_run_dir = resolve_display_run_dir(run_dir)
    if not _has_attachable_artifact(display_run_dir):
        return {}
    state = _read_json(run_dir / "operator_state.json")
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
    payload = {
        "run_id": run_id,
        "selection_id": selection_id,
        "launch_label": launch_label,
        "route_id": str(row.get("route_id") or route_payload.get("legacy_route_id") or ""),
        "route_label": str(row.get("route_label") or ""),
        "run_dir": str(run_dir),
        "display_run_dir": str(display_run_dir),
        "display_run_id": _display_run_id(run_dir, display_run_dir),
        "activity_epoch": activity_epoch,
        "started_at": str(row.get("started_at") or state.get("started_at") or ""),
        "phase": _latest_phase(display_run_dir, state),
    }
    return payload


def _read_history_rows(root: Path) -> list[dict[str, Any]]:
    path = _history_path(root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


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


def _latest_phase(display_run_dir: Path, state: dict[str, Any]) -> str:
    live_status = _read_json(display_run_dir / "live_status.json")
    return str(live_status.get("phase") or state.get("phase") or "")


def _display_run_id(wrapper_run_dir: Path, display_run_dir: Path) -> str:
    if wrapper_run_dir == display_run_dir:
        return wrapper_run_dir.name
    try:
        return str(display_run_dir.relative_to(wrapper_run_dir))
    except ValueError:
        return display_run_dir.name


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}

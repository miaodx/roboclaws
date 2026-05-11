from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.report import render_cleanup_report
from roboclaws.molmo_cleanup.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
)


def rerender_cleanup_report_from_run_result(run_result_path: Path) -> Path:
    """Render a cleanup report from an existing run_result artifact.

    This is the adapter for stale MolmoSpaces cleanup artifacts: callers provide
    the run_result path, and the adapter owns scenario, trace, snapshot, and
    private-manifest loading before delegating to the shared report underlay.
    """
    run_result_path = Path(run_result_path).resolve()
    run_dir = run_result_path.parent
    run_result = _read_json(run_result_path)
    artifacts = run_result.get("artifacts") or {}
    scenario = load_cleanup_scenario_artifact(
        _resolve_artifact(run_dir, artifacts.get("scenario"), default_name="scenario.json")
    )
    trace_events = load_trace_events(
        _resolve_artifact(run_dir, artifacts.get("trace"), default_name="trace.jsonl")
    )
    before_snapshot = _resolve_artifact(
        run_dir,
        artifacts.get("before_snapshot"),
        default_name="before.png",
    )
    after_snapshot = _resolve_artifact(
        run_dir,
        artifacts.get("after_snapshot"),
        default_name="after.png",
    )
    return render_cleanup_report(
        run_dir=run_dir,
        scenario=scenario,
        run_result=run_result,
        trace_events=trace_events,
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        robot_view_steps=run_result.get("robot_view_steps") or [],
    )


def load_cleanup_scenario_artifact(scenario_path: Path) -> CleanupScenario:
    """Load the public cleanup scenario plus adjacent private manifest if present."""
    scenario_path = Path(scenario_path)
    payload = _read_json(scenario_path)
    private_manifest_path = scenario_path.with_name("private_manifest.json")
    if private_manifest_path.is_file():
        private_manifest = PrivateScoringManifest.from_dict(_read_json(private_manifest_path))
    else:
        private_manifest = PrivateScoringManifest(
            scenario_id=str(payload["scenario_id"]),
            targets=(),
            success_threshold=0,
        )
    return CleanupScenario(
        scenario_id=str(payload["scenario_id"]),
        task=str(payload.get("task", "")),
        seed=int(payload.get("seed", 0)),
        objects=tuple(_cleanup_object_from_dict(item) for item in payload.get("objects", [])),
        receptacles=tuple(
            _cleanup_receptacle_from_dict(item) for item in payload.get("receptacles", [])
        ),
        private_manifest=private_manifest,
    )


def load_trace_events(trace_path: Path) -> list[dict[str, Any]]:
    trace_events: list[dict[str, Any]] = []
    for line in Path(trace_path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if isinstance(event, dict):
            trace_events.append(event)
    return trace_events


def _cleanup_object_from_dict(data: dict[str, Any]) -> CleanupObject:
    return CleanupObject(
        object_id=str(data["object_id"]),
        name=str(data.get("name", data["object_id"])),
        category=str(data.get("category", "")),
        location_id=str(data.get("location_id", "")),
        pickupable=bool(data.get("pickupable", True)),
    )


def _cleanup_receptacle_from_dict(data: dict[str, Any]) -> CleanupReceptacle:
    return CleanupReceptacle(
        receptacle_id=str(data["receptacle_id"]),
        name=str(data.get("name", data["receptacle_id"])),
        room_area=str(data.get("room_area", "")),
        kind=str(data.get("kind", "receptacle")),
        category=str(data["category"]) if data.get("category") is not None else None,
    )


def _resolve_artifact(
    run_dir: Path,
    value: Any,
    *,
    default_name: str,
) -> Path:
    text = str(value or default_name)
    candidate = Path(text)
    if candidate.is_absolute():
        return candidate
    if candidate.exists():
        return candidate
    colocated = run_dir / candidate.name
    if colocated.exists():
        return colocated
    return run_dir / candidate


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object in {path}")
    return data

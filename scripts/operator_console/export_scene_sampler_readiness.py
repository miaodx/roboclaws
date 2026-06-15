#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.launch.scene_sampler import (  # noqa: E402
    candidate_readiness_report,
    eval_projection_metadata,
    eval_sample_payload,
    eval_sampler_rows,
    eval_suite_payload,
    next_flow_worklist_report,
    readiness_report,
    sampler_manifest,
    scanner_admission_report,
    scanner_execution_plan,
    selection_gap_report,
    source_availability_report,
    source_prep_report,
    validate_sampler_manifest,
)

DEFAULT_OUTPUT_DIR = Path("output/scene-sampler-readiness")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    candidate_indices = _candidate_indices(
        candidate_indexes=tuple(args.candidate_indexes),
        candidate_ranges=tuple(args.candidate_ranges),
    )
    report = export_readiness_artifacts(
        output_dir=args.output_dir,
        candidate_indices=candidate_indices,
        write_manifest=not args.no_manifest,
        write_eval_projection=not args.no_eval_projection,
        write_readiness_report=not args.no_readiness_report,
        write_source_availability=not args.no_source_availability,
        write_candidate_readiness=not args.no_candidate_readiness,
        write_selection_gaps=not args.no_selection_gaps,
        write_source_prep=not args.no_source_prep,
        write_scanner_admission=not args.no_scanner_admission,
        write_scanner_execution_plan=not args.no_scanner_execution_plan,
        write_next_flow_worklist=not args.no_next_flow_worklist,
        write_generated_eval=not args.no_generated_eval,
        required_ui_supported_sources=tuple(args.require_ui_supported_sources),
        required_eval_complete_sources=tuple(args.require_eval_complete_sources),
        required_selection_capacity_sources=tuple(args.require_selection_capacity_sources),
        required_scanner_ready_sources=tuple(args.require_scanner_ready_sources),
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "success" else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export source-aware MolmoSpaces scene-sampler readiness artifacts "
            "without downloading assets or calling live labelers."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--no-manifest", action="store_true")
    parser.add_argument("--no-eval-projection", action="store_true")
    parser.add_argument("--no-readiness-report", action="store_true")
    parser.add_argument("--no-source-availability", action="store_true")
    parser.add_argument("--no-candidate-readiness", action="store_true")
    parser.add_argument("--no-selection-gaps", action="store_true")
    parser.add_argument("--no-source-prep", action="store_true")
    parser.add_argument("--no-scanner-admission", action="store_true")
    parser.add_argument("--no-scanner-execution-plan", action="store_true")
    parser.add_argument("--no-next-flow-worklist", action="store_true")
    parser.add_argument("--no-generated-eval", action="store_true")
    parser.add_argument(
        "--candidate-index",
        action="append",
        type=int,
        dest="candidate_indexes",
        default=[],
        metavar="INDEX",
        help=(
            "Candidate scene index to include in no-download availability, candidate, "
            "and selection-gap artifacts. Defaults to 0..9 when no index/range is passed."
        ),
    )
    parser.add_argument(
        "--candidate-range",
        action="append",
        dest="candidate_ranges",
        default=[],
        metavar="START:END",
        help=(
            "Inclusive candidate scene-index range to include, for example 0:19. "
            "May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--require-ui-supported-source",
        action="append",
        dest="require_ui_supported_sources",
        default=[],
        metavar="SCENE_SOURCE",
        help=(
            "Fail unless SCENE_SOURCE has exactly the sampler UI target count ready. "
            "May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--require-eval-complete-source",
        action="append",
        dest="require_eval_complete_sources",
        default=[],
        metavar="SCENE_SOURCE",
        help=(
            "Fail unless SCENE_SOURCE has exactly the sampler eval-stress target count ready. "
            "May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--require-selection-capacity-source",
        action="append",
        dest="require_selection_capacity_sources",
        default=[],
        metavar="SCENE_SOURCE",
        help=(
            "Fail unless SCENE_SOURCE has enough next scan candidates to cover both "
            "current UI and eval-stress gaps. May be passed multiple times."
        ),
    )
    parser.add_argument(
        "--require-scanner-ready-source",
        action="append",
        dest="require_scanner_ready_sources",
        default=[],
        metavar="SCENE_SOURCE",
        help=(
            "Fail unless SCENE_SOURCE has at least one candidate ready for preview plus "
            "map-build product smoke. May be passed multiple times."
        ),
    )
    return parser.parse_args(argv)


def export_readiness_artifacts(
    *,
    output_dir: Path,
    candidate_indices: tuple[int, ...] = tuple(range(10)),
    write_manifest: bool = True,
    write_eval_projection: bool = True,
    write_readiness_report: bool = True,
    write_source_availability: bool = True,
    write_candidate_readiness: bool = True,
    write_selection_gaps: bool = True,
    write_source_prep: bool = True,
    write_scanner_admission: bool = True,
    write_scanner_execution_plan: bool = True,
    write_next_flow_worklist: bool = True,
    write_generated_eval: bool = True,
    required_ui_supported_sources: tuple[str, ...] = (),
    required_eval_complete_sources: tuple[str, ...] = (),
    required_selection_capacity_sources: tuple[str, ...] = (),
    required_scanner_ready_sources: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Write deterministic sampler artifacts for review and later scanner slices."""

    validate_sampler_manifest()
    manifest = sampler_manifest()
    projection = eval_projection_metadata()
    readiness = readiness_report()
    selection = selection_gap_report(candidate_indices=candidate_indices)
    availability = (
        source_availability_report(candidate_indices=candidate_indices)
        if write_source_availability
        else None
    )
    candidates = (
        candidate_readiness_report(candidate_indices=candidate_indices)
        if write_candidate_readiness
        else None
    )
    source_prep = (
        source_prep_report(candidate_indices=candidate_indices) if write_source_prep else None
    )
    scanner_admission = (
        scanner_admission_report(candidate_indices=candidate_indices)
        if write_scanner_admission
        else None
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    if write_manifest:
        manifest_path = output_dir / "scene_sampler_manifest.json"
        _write_json(manifest_path, manifest)
        artifacts["manifest"] = str(manifest_path)
    if write_eval_projection:
        projection_path = output_dir / "scene_sampler_eval_projection.json"
        _write_json(projection_path, projection)
        artifacts["eval_projection"] = str(projection_path)
    if write_readiness_report:
        readiness_path = output_dir / "scene_sampler_readiness_report.json"
        _write_json(readiness_path, readiness)
        artifacts["readiness_report"] = str(readiness_path)
    if write_source_availability:
        availability_path = output_dir / "scene_sampler_source_availability.json"
        _write_json(availability_path, availability or {})
        artifacts["source_availability"] = str(availability_path)
    if write_candidate_readiness:
        candidate_path = output_dir / "scene_sampler_candidate_readiness.json"
        _write_json(candidate_path, candidates or {})
        artifacts["candidate_readiness"] = str(candidate_path)
    if write_selection_gaps:
        selection_path = output_dir / "scene_sampler_selection_gaps.json"
        _write_json(selection_path, selection)
        artifacts["selection_gaps"] = str(selection_path)
    if write_source_prep:
        source_prep_path = output_dir / "scene_sampler_source_prep.json"
        _write_json(source_prep_path, source_prep or {})
        artifacts["source_prep"] = str(source_prep_path)
    if write_scanner_admission:
        scanner_admission_path = output_dir / "scene_sampler_scanner_admission.json"
        _write_json(scanner_admission_path, scanner_admission or {})
        artifacts["scanner_admission"] = str(scanner_admission_path)
    scanner_execution: dict[str, Any] | None = None
    if write_scanner_execution_plan or required_scanner_ready_sources:
        scanner_execution = scanner_execution_plan(candidate_indices=candidate_indices)
    if write_scanner_execution_plan:
        scanner_execution_path = output_dir / "scene_sampler_scanner_execution_plan.json"
        _write_json(scanner_execution_path, scanner_execution or {})
        artifacts["scanner_execution_plan"] = str(scanner_execution_path)
    next_flow_worklist = (
        next_flow_worklist_report(candidate_indices=candidate_indices, output_dir=output_dir)
        if write_next_flow_worklist
        else None
    )
    if write_next_flow_worklist:
        next_flow_worklist_path = output_dir / "scene_sampler_next_flow_worklist.json"
        _write_json(next_flow_worklist_path, next_flow_worklist or {})
        artifacts["next_flow_worklist"] = str(next_flow_worklist_path)
    if write_generated_eval:
        generated_eval_dir = output_dir / "generated_eval"
        generated_samples_dir = generated_eval_dir / "samples" / "scene_sampler"
        generated_samples_dir.mkdir(parents=True, exist_ok=True)
        generated_suite_path = generated_eval_dir / "scene_sampler_stress.json"
        _write_json(generated_suite_path, eval_suite_payload())
        sample_paths = []
        for row in eval_sampler_rows():
            sample_path = generated_samples_dir / (
                f"{row.scene_source}_{row.scene_index}_map_build.json"
            )
            _write_json(sample_path, eval_sample_payload(row))
            sample_paths.append(str(sample_path))
        artifacts["generated_eval_suite"] = str(generated_suite_path)
        artifacts["generated_eval_samples"] = sample_paths
    failures = _threshold_failures(
        readiness,
        selection,
        required_ui_supported_sources=required_ui_supported_sources,
        required_eval_complete_sources=required_eval_complete_sources,
        required_selection_capacity_sources=required_selection_capacity_sources,
        required_scanner_ready_sources=required_scanner_ready_sources,
        scanner_execution=scanner_execution,
    )
    return {
        "schema": "molmospaces_scene_sampler_readiness_export_v1",
        "status": "failed" if failures else "success",
        "output_dir": str(output_dir),
        "candidate_indices": list(candidate_indices),
        "artifacts": artifacts,
        "summary": _export_summary(
            manifest=manifest,
            projection=projection,
            readiness=readiness,
            selection=selection,
            availability=availability,
            candidates=candidates,
            source_prep=source_prep,
            scanner_admission=scanner_admission,
            scanner_execution=scanner_execution,
            next_flow_worklist=next_flow_worklist,
        ),
        "threshold_failures": failures,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _export_summary(
    *,
    manifest: dict[str, Any],
    projection: dict[str, Any],
    readiness: dict[str, Any],
    selection: dict[str, Any],
    availability: dict[str, Any] | None,
    candidates: dict[str, Any] | None,
    source_prep: dict[str, Any] | None,
    scanner_admission: dict[str, Any] | None,
    scanner_execution: dict[str, Any] | None,
    next_flow_worklist: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "supported_scene_sources": manifest.get("supported_scene_sources", []),
        "ui_world_ids": (manifest.get("projections") or {}).get("ui_world_ids", []),
        "eval_sample_ids": (manifest.get("projections") or {}).get("eval_sample_ids", []),
        "eval_projection": projection.get("summary", {}),
        "readiness": readiness.get("summary", {}),
        "source_availability": (availability or {}).get("summary", {}),
        "candidate_readiness": (candidates or {}).get("summary", {}),
        "selection_gaps": (selection or {}).get("summary", {}),
        "source_prep": (source_prep or {}).get("summary", {}),
        "scanner_admission": (scanner_admission or {}).get("summary", {}),
        "scanner_execution": (scanner_execution or {}).get("summary", {}),
        "next_flow_worklist": (next_flow_worklist or {}).get("summary", {}),
    }


def _candidate_indices(
    *,
    candidate_indexes: tuple[int, ...],
    candidate_ranges: tuple[str, ...],
) -> tuple[int, ...]:
    values: set[int] = set()
    for index in candidate_indexes:
        if index < 0:
            raise ValueError(f"candidate-index must be >= 0, got {index}")
        values.add(index)
    for raw_range in candidate_ranges:
        values.update(_parse_candidate_range(raw_range))
    if not values:
        values.update(range(10))
    return tuple(sorted(values))


def _parse_candidate_range(raw_range: str) -> range:
    try:
        raw_start, raw_end = raw_range.split(":", 1)
        start = int(raw_start)
        end = int(raw_end)
    except ValueError as exc:
        raise ValueError(
            f"candidate-range must be START:END with integer bounds, got {raw_range!r}"
        ) from exc
    if start < 0 or end < 0:
        raise ValueError(f"candidate-range bounds must be >= 0, got {raw_range!r}")
    if end < start:
        raise ValueError(f"candidate-range end must be >= start, got {raw_range!r}")
    return range(start, end + 1)


def _threshold_failures(
    readiness: dict[str, Any],
    selection: dict[str, Any],
    *,
    required_ui_supported_sources: tuple[str, ...],
    required_eval_complete_sources: tuple[str, ...],
    required_selection_capacity_sources: tuple[str, ...],
    required_scanner_ready_sources: tuple[str, ...],
    scanner_execution: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    sources = readiness.get("sources") if isinstance(readiness.get("sources"), dict) else {}
    failures: list[dict[str, Any]] = []
    for source in required_ui_supported_sources:
        payload = sources.get(source)
        if not isinstance(payload, dict):
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "ui_supported",
                    "reason": "unknown_scene_source",
                }
            )
            continue
        if payload.get("ui_status") != "ready":
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "ui_supported",
                    "reason": "ui_not_ready",
                    "ready_count": payload.get("ui_ready_count"),
                    "target_count": payload.get("ui_target_count"),
                }
            )
    for source in required_eval_complete_sources:
        payload = sources.get(source)
        if not isinstance(payload, dict):
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "eval_complete",
                    "reason": "unknown_scene_source",
                }
            )
            continue
        if payload.get("eval_status") != "complete":
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "eval_complete",
                    "reason": "eval_not_complete",
                    "ready_count": payload.get("eval_ready_count"),
                    "target_count": payload.get("eval_target_count"),
                }
            )
    selection_sources = (
        selection.get("sources") if isinstance(selection.get("sources"), dict) else {}
    )
    for source in required_selection_capacity_sources:
        payload = selection_sources.get(source)
        if not isinstance(payload, dict):
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "selection_capacity",
                    "reason": "unknown_scene_source",
                }
            )
            continue
        ui_needed = int(payload.get("ui_needed_count") or 0)
        eval_needed = int(payload.get("eval_needed_count") or 0)
        ui_available = len(payload.get("next_ui_scan_world_ids") or [])
        eval_available = len(payload.get("next_eval_scan_world_ids") or [])
        if ui_available < ui_needed or eval_available < eval_needed:
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "selection_capacity",
                    "reason": "insufficient_candidate_scan_capacity",
                    "ui_needed_count": ui_needed,
                    "ui_available_count": ui_available,
                    "eval_needed_count": eval_needed,
                    "eval_available_count": eval_available,
                }
            )
    scanner_sources = (
        scanner_execution.get("sources")
        if isinstance(scanner_execution, dict)
        and isinstance(scanner_execution.get("sources"), dict)
        else {}
    )
    for source in required_scanner_ready_sources:
        payload = scanner_sources.get(source)
        if not isinstance(payload, dict):
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "scanner_ready",
                    "reason": "unknown_scene_source",
                }
            )
            continue
        ready_count = int(payload.get("ready_for_product_smoke_count") or 0)
        if ready_count < 1:
            failures.append(
                {
                    "scene_source": source,
                    "threshold": "scanner_ready",
                    "reason": "no_ready_product_smoke_candidates",
                    "ready_for_product_smoke_count": ready_count,
                    "candidate_count": int(payload.get("candidate_count") or 0),
                    "blocked_count": int(payload.get("blocked_count") or 0),
                    "prep_status": payload.get("prep_status", ""),
                }
            )
    return failures


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

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
    eval_projection_metadata,
    readiness_report,
    sampler_manifest,
    validate_sampler_manifest,
)

DEFAULT_OUTPUT_DIR = Path("output/scene-sampler-readiness")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = export_readiness_artifacts(
        output_dir=args.output_dir,
        write_manifest=not args.no_manifest,
        write_eval_projection=not args.no_eval_projection,
        write_readiness_report=not args.no_readiness_report,
        required_ui_supported_sources=tuple(args.require_ui_supported_sources),
        required_eval_complete_sources=tuple(args.require_eval_complete_sources),
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
    return parser.parse_args(argv)


def export_readiness_artifacts(
    *,
    output_dir: Path,
    write_manifest: bool = True,
    write_eval_projection: bool = True,
    write_readiness_report: bool = True,
    required_ui_supported_sources: tuple[str, ...] = (),
    required_eval_complete_sources: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Write deterministic sampler artifacts for review and later scanner slices."""

    validate_sampler_manifest()
    readiness = readiness_report()
    output_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}
    if write_manifest:
        manifest_path = output_dir / "scene_sampler_manifest.json"
        _write_json(manifest_path, sampler_manifest())
        artifacts["manifest"] = str(manifest_path)
    if write_eval_projection:
        projection_path = output_dir / "scene_sampler_eval_projection.json"
        _write_json(projection_path, eval_projection_metadata())
        artifacts["eval_projection"] = str(projection_path)
    if write_readiness_report:
        readiness_path = output_dir / "scene_sampler_readiness_report.json"
        _write_json(readiness_path, readiness)
        artifacts["readiness_report"] = str(readiness_path)
    failures = _threshold_failures(
        readiness,
        required_ui_supported_sources=required_ui_supported_sources,
        required_eval_complete_sources=required_eval_complete_sources,
    )
    return {
        "schema": "molmospaces_scene_sampler_readiness_export_v1",
        "status": "failed" if failures else "success",
        "output_dir": str(output_dir),
        "artifacts": artifacts,
        "threshold_failures": failures,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _threshold_failures(
    readiness: dict[str, Any],
    *,
    required_ui_supported_sources: tuple[str, ...],
    required_eval_complete_sources: tuple[str, ...],
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
    return failures


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

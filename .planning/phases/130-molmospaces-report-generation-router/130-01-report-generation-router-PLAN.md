# Phase 130 Plan: MolmoSpaces Report Generation Router

## Goal

Route Molmo cleanup artifact report generation through the shared Cleanup Report
Artifact Adapter even when callers use the generic report-generation entrypoint.

## Tasks

1. Add cleanup artifact detection for run directories and `run_result.json`
   paths.
2. Add adapter entrypoints that accept either artifact shape.
3. Delegate generic `generate()` calls to the cleanup adapter for Molmo cleanup
   artifacts.
4. Update the Molmo regeneration script to accept directories as well as files.
5. Add focused tests and update ADR, plan, `CONTEXT.md`, pilot plan, and
   `.planning/STATE.md`.

## Acceptance Checks

- Molmo cleanup run directories route to the shared cleanup underlay.
- Molmo cleanup `run_result.json` paths route to the same underlay.
- Generic replay report generation still works for `replay.json` artifacts.
- Custom output paths are rejected for cleanup reports to preserve relative
  robot-view assets.
- Focused lint, format, and pytest gates pass.

## Result

Complete on 2026-05-10.

The generic report entrypoint now routes Molmo cleanup artifacts to
`artifact_report.py`, and the regeneration CLI accepts both run directories and
run-result files.

Verification:

- `.venv/bin/ruff check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_dir_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_result_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_route_rejects_custom_output_path tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_report_from_artifact_path_accepts_run_directory tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_reports_from_artifact_paths_reuses_directory_adapter`
- `.venv/bin/python -m roboclaws.core.reporter output/molmo-agent-bridge-visual-codex` preserved the existing `report.html` hash, proving the generic entrypoint routes the reference artifact through the shared cleanup adapter.

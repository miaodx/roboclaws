# MolmoSpaces Report Generation Router

**Status:** Completed under GSD Phase 130 on 2026-05-10
**Created:** 2026-05-10
**Source:** User visual review of `output/molmo-agent-bridge-visual-codex/report.html`, ADR-0009, ADR-0021, ADR-0115, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The cleanup report renderer itself is shared, and the reference artifact
`output/molmo-agent-bridge-visual-codex/report.html` regenerates byte-for-byte
through the cleanup adapter. The remaining problem is routing: the repo also
has an older generic replay report generator for non-Molmo game replays.

That leaves an avoidable ambiguity around "generate report.html" for
MolmoSpaces cleanup demos.

## Decision

Make the report-generation entrypoint route Molmo cleanup artifacts through the
Cleanup Report Artifact Adapter.

The artifact adapter now accepts either a run directory or `run_result.json`.
`roboclaws.core.reporter.generate()` detects cleanup run-result artifacts and
delegates to the shared cleanup adapter instead of the generic replay reporter.
The Molmo regeneration script uses the same directory-or-file adapter.

## Non-Goals

- Do not merge AI2-THOR/OpenClaw replay reports with Molmo cleanup reports.
- Do not change the visual design of the shared Cleanup Artifact Report.
- Do not move or commit ignored `output/` artifacts.
- Do not support custom output paths for cleanup reports, because relative
  robot-view assets are part of the artifact contract.

## Acceptance Criteria

- Passing a Molmo cleanup run directory to `roboclaws.core.reporter.generate()`
  produces the shared Cleanup Artifact Report.
- Passing a Molmo cleanup `run_result.json` path does the same.
- The generated report contains semantic subphase visual core markers and does
  not render generic replay-reporter UI.
- The Molmo regeneration script accepts both directories and `run_result.json`.
- Focused lint, format, and pytest gates pass.

## Result

Complete.

Molmo cleanup artifact detection now lives in `artifact_report.py`, generic
report generation delegates to it when appropriate, and tests assert that
cleanup run directories and run-result paths produce shared visual-core reports.

Verification:

- `.venv/bin/ruff check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_dir_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_result_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_route_rejects_custom_output_path tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_report_from_artifact_path_accepts_run_directory tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_reports_from_artifact_paths_reuses_directory_adapter`
- `.venv/bin/python -m roboclaws.core.reporter output/molmo-agent-bridge-visual-codex` preserved the existing `report.html` hash, proving the generic entrypoint routes the reference artifact through the shared cleanup adapter.

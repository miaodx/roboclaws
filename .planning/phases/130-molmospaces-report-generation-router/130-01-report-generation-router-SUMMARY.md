# Phase 130 Summary: MolmoSpaces Report Generation Router

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `130-01-report-generation-router-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Route Molmo cleanup artifact report generation through the shared Cleanup Report
Artifact Adapter even when callers use the generic report-generation entrypoint.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The generic report entrypoint now routes Molmo cleanup artifacts to
`artifact_report.py`, and the regeneration CLI accepts both run directories and
run-result files.

Verification:

- `.venv/bin/ruff check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_dir_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_result_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_route_rejects_custom_output_path tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_report_from_artifact_path_accepts_run_directory tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_reports_from_artifact_paths_reuses_directory_adapter`
- `.venv/bin/python -m roboclaws.core.reporter output/molmo-agent-bridge-visual-codex` preserved the existing `report.html` hash, proving the generic entrypoint routes the reference artifact through the shared cleanup adapter.

## Evidence

- `.venv/bin/ruff check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `.venv/bin/ruff format --check roboclaws/core/reporter.py roboclaws/molmo_cleanup/artifact_report.py scripts/regenerate_molmo_cleanup_report.py tests/test_reporter.py tests/test_molmo_cleanup_artifact_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_dir_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_run_result_routes_to_shared_underlay tests/test_reporter.py::TestGenerate::test_molmo_cleanup_route_rejects_custom_output_path tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_report_from_artifact_path_accepts_run_directory tests/test_molmo_cleanup_artifact_report.py::test_rerender_cleanup_reports_from_artifact_paths_reuses_directory_adapter`
- `.venv/bin/python -m roboclaws.core.reporter output/molmo-agent-bridge-visual-codex` preserved the existing `report.html` hash, proving the generic entrypoint routes the reference artifact through the shared cleanup adapter.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

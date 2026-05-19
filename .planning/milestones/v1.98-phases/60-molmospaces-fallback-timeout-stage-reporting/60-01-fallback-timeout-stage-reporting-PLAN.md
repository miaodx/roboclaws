# Phase 60 Plan: MolmoSpaces Fallback Timeout Stage Reporting

## Goal

Make generated fallback proof-bundle reports show where timeout failures stop,
without requiring manual inspection of individual proof stdout or JSON files.

## Tasks

1. Extend `proof_result_summary_from_commands` with timeout counts, last worker
   stage, compact worker stage events, and proof stdout/stderr artifact paths.
2. Render those fields in `render_planner_proof_bundle_runner_report`.
3. Update the proof-bundle checker and focused tests.
4. Record ADR/source-plan/state docs.

## Acceptance Checks

- A timeout proof result with worker events renders `Last worker stage` and
  `Worker stages` in the runner report.
- Bundle metrics include timeout counts.
- Checker validates timeout-stage fields when present.
- Focused ruff and pytest checks pass.

## Result

Completed on 2026-05-10.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

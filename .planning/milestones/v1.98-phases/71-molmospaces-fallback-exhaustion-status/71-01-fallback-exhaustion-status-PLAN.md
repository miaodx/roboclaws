# Phase 71 Plan: MolmoSpaces Fallback Exhaustion Status

## Goal

Make exhausted generated-fallback candidate pools a first-class runner
manifest/report state.

## Tasks

1. Add fallback-generation status values for disabled, not-required, generated,
   and exhausted states.
2. Render the status in the proof-bundle runner report metrics.
3. Validate the status in the runner checker.
4. Update focused unit tests for generated and exhausted fallback states.
5. Dry-run the merged prior evidence artifact and validate the report/checker.

## Acceptance Checks

- A generated fallback run reports `status=generated`.
- A no-command fallback run with blocked requests and no available candidates
  reports `status=exhausted`.
- `report.html` includes `Fallback status`.
- The proof-bundle runner checker rejects invalid/missing status when fallback
  generation evidence exists.

## Result

Completed on 2026-05-10.

The Phase 71 dry-run reports `Fallback status: exhausted`, zero generated
commands, five discovered aliases, seven filtered aliases, and two filtered
pairs. The runner checker validates that report.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase71-fallback-exhaustion-status-dry-run`

## Status

Complete.

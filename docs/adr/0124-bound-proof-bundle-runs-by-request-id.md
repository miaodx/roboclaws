# 0124. Bound Proof Bundle Runs By Request ID

Date: 2026-05-10

## Status

Accepted

## Context

After ADR-0122 and ADR-0123, proof-bundle dry-run reports show both proof
execution horizon and cleanup semantic subphase intent. The next blocker is
actual stronger proof coverage, but the current Phase 126 cleanup artifact
generates ten selected proof commands when the stricter two-step horizon is
requested.

Running all ten commands is a broad local RBY1M/CuRobo job. The next local proof
attempt needs a bounded path for one cleanup request at a time.

## Decision

The proof-bundle runner now accepts repeatable `--request-id` flags. Selection
records a `request_filter` block with requested, matched, unavailable, and
missing IDs. Runner reports render this as `Request ID Filter`, and the runner
checker validates the filter view when present.

The filter is applied before task-feasibility and prior-covered exclusion, so it
can be combined with existing selection modes.

## Consequences

- Local proof attempts can target a single cleanup request without executing the
  whole generated bundle.
- Dry-run reports show exactly why only one request was selected.
- This does not replace full-bundle execution; it creates a safer one-request
  path for iterative proof expansion.

## Evidence

Implemented in Phase 133 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_filters_to_requested_request_ids tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase133-request-filter-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase133-request-filter-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`

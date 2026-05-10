# Phase 133 Plan: MolmoSpaces Proof Bundle Request Filter

## Goal

Allow bounded proof-bundle dry-runs and future local executions for one explicit
cleanup proof request at a time.

## Tasks

1. Add repeatable `--request-id` to the proof-bundle runner.
2. Apply request-id filtering before existing exclusion modes.
3. Record requested, matched, unavailable, and missing request IDs in selection
   evidence.
4. Render and validate the request filter view.
5. Add focused tests and update ADR, plan, `CONTEXT.md`, pilot plan, and
   `.planning/STATE.md`.

## Acceptance Checks

- Bounded dry-run can select only `proof_001` from the Phase 126 cleanup
  artifact.
- Report includes `Request ID Filter`.
- Checker accepts the bounded dry-run with `--max-selected-requests 1`.
- Focused lint, format, pytest, and bounded dry-run artifact gate pass.

## Result

Complete on 2026-05-10.

The proof-bundle runner can now select a named request before execution. The
Phase 126 stricter dry-run selects only `proof_001` when passed
`--request-id proof_001`.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_filters_to_requested_request_ids tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase133-request-filter-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2 --request-id proof_001`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase133-request-filter-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1 --max-selected-requests 1`

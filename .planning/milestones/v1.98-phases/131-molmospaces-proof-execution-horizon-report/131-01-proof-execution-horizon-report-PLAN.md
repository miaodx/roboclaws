# Phase 131 Plan: MolmoSpaces Proof Execution Horizon Report

## Goal

Make proof-bundle dry-run reports show the requested proof-strength horizon
before local proof execution.

## Tasks

1. Add a `proof_execution_horizon` manifest block.
2. Render the horizon in proof-bundle runner reports.
3. Show blockers when command steps are below the prior-covered coverage
   horizon.
4. Add a runner checker flag for requiring the horizon view.
5. Add focused tests and update ADR, plan, `CONTEXT.md`, pilot plan, and
   `.planning/STATE.md`.

## Acceptance Checks

- Runner manifests include command-step and prior-covered horizon fields.
- Runner reports render `Proof Execution Horizon`.
- Misalignment between command steps and requested coverage floor is visible.
- Checker can require the horizon section.
- Focused lint, format, pytest, and one dry-run artifact gate pass.

## Result

Complete on 2026-05-10.

The proof-bundle runner now reports proof-strength intent before execution and
the checker can require it.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_reports_misaligned_proof_execution_horizon tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_execution_horizon`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase131-proof-execution-horizon-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase131-proof-execution-horizon-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`

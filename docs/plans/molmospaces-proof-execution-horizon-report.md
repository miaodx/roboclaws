# MolmoSpaces Proof Execution Horizon Report

**Status:** Completed under GSD Phase 131 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0118, ADR-0119, ADR-0120, `CONTEXT.md`, `docs/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Proof quality is visible after execution, and prior-covered selection can
require a stricter coverage horizon. But dry-run proof-bundle reports did not
state the proof-strength target of the generated commands.

That made it possible to reselect one-step prior memory for a two-step horizon
while accidentally generating one-step commands again.

## Decision

Add a report-visible proof execution horizon to the proof-bundle runner.

The manifest and report now show command steps, command quality target, coverage
minimum, coverage floor, and explicit blockers when command steps are below the
prior-covered horizon. The checker can require this view.

## Non-Goals

- Do not execute new RBY1M/CuRobo proofs.
- Do not claim proof success from dry-run command configuration.
- Do not raise global cleanup checker requirements.
- Do not change planner policy behavior.

## Acceptance Criteria

- Proof-bundle runner manifests include `proof_execution_horizon`.
- Runner reports render a `Proof Execution Horizon` visual section.
- Misaligned command-step and coverage horizons are visible in manifest and
  report.
- The runner checker can require the horizon view.
- Focused lint, format, pytest, and one dry-run artifact gate pass.

## Result

Complete.

The proof-bundle runner now records and renders requested proof-strength
horizons. A dry-run against the Phase 126 cleanup artifact generated a report
with the new view and passed the runner checker with
`--require-proof-execution-horizon`.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_reports_misaligned_proof_execution_horizon tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_can_require_proof_execution_horizon`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase131-proof-execution-horizon-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase131-proof-execution-horizon-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`

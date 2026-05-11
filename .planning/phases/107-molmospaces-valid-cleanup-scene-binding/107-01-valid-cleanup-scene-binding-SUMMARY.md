# Phase 107 Summary: Phase 107-01: Valid Cleanup Scene Binding

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `107-01-valid-cleanup-scene-binding-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Prevent stale cleanup scene paths from being accepted as exact-scene planner
proof evidence, then rerun the exact pickup binding probe against the canonical
cleanup scene.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

Code changes:

- `scripts/check_molmo_planner_manipulation_probe.py`
- `scripts/check_molmo_planner_proof_bundle_runner_result.py`
- `roboclaws/molmo_cleanup/report.py`
- focused test coverage

Verification:

- `.venv/bin/ruff format --check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`

Runtime evidence:

- `output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`
- `output/debug-phase107-valid-cleanup-scene-pickup-binding/report.html`

Observed runtime result:

- status: `blocked_capability`
- cleanup task config blockers: none
- exact pickup candidate action: `injected_requested_candidate_name`
- candidate count before: 17
- candidate count after: 1
- robot placement attempts: 1
- placement failures: 0
- grasp failures: 1
- candidate-removal calls: 0

## Evidence

- `.venv/bin/ruff format --check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`

Runtime evidence:

- `output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`
- `output/debug-phase107-valid-cleanup-scene-pickup-binding/report.html`

Observed runtime result:

- status: `blocked_capability`
- cleanup task config blockers: none
- exact pickup candidate action: `injected_requested_candidate_name`
- candidate count before: 17
- candidate count after: 1
- robot placement attempts: 1
- placement failures: 0
- grasp failures: 1
- candidate-removal calls: 0

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

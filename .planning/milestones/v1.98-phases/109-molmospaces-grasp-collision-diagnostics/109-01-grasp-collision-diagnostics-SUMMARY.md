# Phase 109 Summary: Phase 109-01: Grasp Collision Diagnostics

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `109-01-grasp-collision-diagnostics-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Explain the remaining exact-object post-placement grasp-feasibility blocker by
recording upstream grasp-load and collision-mask facts.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

Code changes:

- `scripts/run_molmo_planner_manipulation_probe.py`
- `roboclaws/molmo_cleanup/report.py`
- planner probe and proof-bundle checker updates
- focused test coverage

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase109-grasp-collision-diagnostics/run_result.json`

Runtime evidence:

- `output/debug-phase109-grasp-collision-diagnostics/run_result.json`
- `output/debug-phase109-grasp-collision-diagnostics/report.html`

Observed runtime result:

- status: `blocked_capability`
- grasp load attempts: 3
- grasp load failures: 3
- last grasp asset UID: `Bread_1`
- last grasp load exception: `ValueError`
- grasp collision checks: 0
- grasp failures: 3
- candidate-removal calls: 1
- effective removals: 1
- candidate-name misses: 0

[Backfill note: source section truncated; see the phase PLAN for full embedded evidence.]

## Evidence

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase109-grasp-collision-diagnostics/run_result.json`

Runtime evidence:

- `output/debug-phase109-grasp-collision-diagnostics/run_result.json`
- `output/debug-phase109-grasp-collision-diagnostics/report.html`

Observed runtime result:

- status: `blocked_capability`
- grasp load attempts: 3
- grasp load failures: 3
- last grasp asset UID: `Bread_1`
- last grasp load exception: `ValueError`
- grasp collision checks: 0
- grasp failures: 3
- candidate-removal calls: 1
- effective removals: 1
- candidate-name misses: 0

The exact-object blocker is missing cached grasps for `Bread_1`; collision
masking is never reached.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

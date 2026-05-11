# Phase 109-01: Grasp Collision Diagnostics

## Goal

Explain the remaining exact-object post-placement grasp-feasibility blocker by
recording upstream grasp-load and collision-mask facts.

## Tasks

- Wrap upstream grasp loading and non-colliding mask calls in the probe-local
  task-sampler diagnostics adapter.
- Record cached-grasp count, collision-checked grasp count, non-colliding
  count, zero-feasible flag, asset UID, and exception details.
- Render those diagnostics in standalone planner reports and proof-bundle
  result cards.
- Update checker gates and focused tests.
- Rerun the valid-scene bread-to-refrigerator proof and record the outcome.

## Acceptance

- Post-placement grasp failures include grasp-load and collision-mask
  diagnostics when upstream reaches those hooks.
- Reports show Grasp Collision Diagnostics.
- Focused ruff, pytest, checker, and real local proof checks pass.

## Result

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

The exact-object blocker is missing cached grasps for `Bread_1`; collision
masking is never reached.

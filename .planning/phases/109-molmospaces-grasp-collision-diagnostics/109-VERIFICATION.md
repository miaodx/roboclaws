# Phase 109 Verification: Phase 109-01: Grasp Collision Diagnostics

Date: 2026-05-11
Source plan: `109-01-grasp-collision-diagnostics-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
109. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Post-placement grasp failures include grasp-load and collision-mask
  diagnostics when upstream reaches those hooks.
- Reports show Grasp Collision Diagnostics.
- Focused ruff, pytest, checker, and real local proof checks pass.

## Recorded Verification Evidence

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

## Artifact Integrity Checks

- Source plan exists: `109-01-grasp-collision-diagnostics-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `109-01-grasp-collision-diagnostics-SUMMARY.md`.
- Backfilled verification exists: `109-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 109 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.

# MolmoSpaces Grasp Collision Diagnostics

**Status:** Completed under GSD Phase 109 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0099
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 108 narrowed the exact-scene cleanup blocker to post-placement grasp
feasibility for the requested bread object. The report still only showed grasp
failure counts and candidate removal; it did not expose whether the upstream
grasp loader found cached grasps or whether collision checking found any
non-colliding grasp poses.

## Decision

Record grasp-load and collision-mask diagnostics in the existing probe-local
task-sampler adapter.

This phase should:

- wrap upstream `load_grasps_for_object` and `get_noncolliding_grasp_mask`;
- record cached-grasp count, total collision-checked grasp count, and
  non-colliding grasp count;
- render the diagnostics through the shared report underlay and proof-bundle
  result cards;
- keep the diagnostics probe-local, with no change to MolmoSpaces task success
  semantics;
- rerun the valid-scene proof and record which exact grasp blocker remains.

## Non-Goals

- Do not change upstream MolmoSpaces source files.
- Do not relax grasp feasibility or force success.
- Do not promote cleanup binding from a blocked proof.

## Deliverables

- ADR-0100 and this source plan.
- `.planning/milestones/v1.98-phases/109-molmospaces-grasp-collision-diagnostics/109-01-grasp-collision-diagnostics-PLAN.md`.
- Grasp collision diagnostics in the sampler failure payload.
- Shared report/checker support for those diagnostics.
- Focused unit coverage and one real local RBY1M valid-scene rerun.

## Verification

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase109-grasp-collision-diagnostics/run_result.json`

## Result

Runtime evidence:

- `output/debug-phase109-grasp-collision-diagnostics/run_result.json`
- `output/debug-phase109-grasp-collision-diagnostics/report.html`

Observed result:

- status: `blocked_capability`
- cleanup scene blockers: none
- exact pickup action: `injected_requested_candidate_name`
- retry budget: 3
- grasp load attempts: 3
- grasp load failures: 3
- last grasp asset UID: `Bread_1`
- last grasp load exception: `ValueError`
- last grasp load message: `Failed to find grasp file for: Bread_1`
- grasp collision checks: 0
- grasp failures: 3
- candidate-removal calls: 1
- effective removals: 1
- candidate-name misses: 0

The remaining blocker is now classified as missing cached grasps for `Bread_1`,
not zero non-colliding grasps after collision masking.

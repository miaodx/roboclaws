# MolmoSpaces Exact Pickup Retry Budget

**Status:** Completed under GSD Phase 108 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0098
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 107 proved the scene and alias were valid, but exact pickup binding
collapsed upstream retry count to one. Upstream removes grasp-infeasible
candidates only after the grasp-failure count exceeds the default threshold of
2, so the exact candidate never reached the removal/effectiveness path.

## Decision

Preserve a small exact-candidate retry budget in the existing exact cleanup
sampler adapter.

This phase should:

- repeat the requested pickup candidate to a retry budget of 3 after exact
  binding;
- keep the pool exact, with no unrelated candidate retries;
- record retry-budget evidence in the pickup binding payload;
- render the retry budget through the shared report underlay;
- rerun the valid-scene proof and record whether the upstream threshold path
  crosses.

## Non-Goals

- Do not change upstream MolmoSpaces source files.
- Do not claim planner-backed proof from a blocked exact-scene probe.
- Do not rerun cleanup until a proof becomes planner-backed and promotes
  cleanup binding.

## Deliverables

- ADR-0099 and this source plan.
- `.planning/milestones/v1.98-phases/108-molmospaces-exact-pickup-retry-budget/108-01-exact-pickup-retry-budget-PLAN.md`.
- Exact pickup retry budget in the sampler adapter.
- Shared report/checker support for retry-budget evidence.
- Focused unit coverage and one real local RBY1M valid-scene rerun.

## Verification

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase108-exact-pickup-retry-budget/run_result.json`

## Result

Runtime evidence:

- `output/debug-phase108-exact-pickup-retry-budget/run_result.json`
- `output/debug-phase108-exact-pickup-retry-budget/report.html`

Observed result:

- status: `blocked_capability`
- exact pickup action: `injected_requested_candidate_name`
- retry budget: 3
- candidate count before: 17
- candidate count after: 3 exact requested-candidate entries
- robot placement attempts: 3
- robot placement failures: 0
- grasp failures: 3
- threshold-crossed rows: 1
- threshold-exceeded rows: 1
- candidate-removal calls: 1
- effective removals: 1
- candidate-name misses: 0

The remaining blocker is now a clean post-placement grasp-feasibility failure
for the exact requested object.

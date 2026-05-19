# MolmoSpaces Exact Pickup Candidate Binding

**Status:** Completed under GSD Phase 106 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0096
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 105 showed that candidate-removal calls were ineffective because the
requested planner object was absent from upstream `candidate_objects`. The
exact cleanup task adapter forced the target-side place receptacle, but the
pickup side still let unrelated upstream candidates drive retry and removal
behavior.

The first attempt to bind the pickup pool at `reset()` was too early. Upstream
MolmoSpaces populates `candidate_objects` during scene initialization before
`_select_pickup_object()`, so a reset-time adapter recorded
`no_candidate_pool` and the real probe still matched the Phase 105 failure
shape.

## Decision

Move pickup candidate binding into the existing exact cleanup sampler adapter
at `_select_pickup_object()`, with a reset-time fallback only for samplers
without that selection hook.

This phase should:

- force the live pickup candidate pool to the requested planner object before
  upstream selection;
- record before/after candidate counts, candidate names, requested-name
  presence, and binding action;
- render that evidence through the shared planner report underlay and
  proof-bundle result cards;
- keep cleanup report semantic subphases as `nav -> pick -> nav -> open? ->
  place` while private proof evidence stays secondary;
- update checker gates and focused tests.

## Non-Goals

- Do not claim planner-backed proof from a blocked exact-scene probe.
- Do not replace the upstream proof candidate source in this slice.
- Do not create another report renderer or alternate semantic timeline model.

## Deliverables

- ADR-0097 and this source plan.
- `.planning/milestones/v1.98-phases/106-molmospaces-exact-pickup-candidate-binding/106-01-exact-pickup-candidate-binding-PLAN.md`.
- Exact pickup candidate binding in the sampler adapter.
- Shared report/checker support for the new binding evidence.
- Focused unit coverage and one real local RBY1M probe rerun.

## Verification

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked output/debug-phase106-exact-pickup-candidate-binding-fixed/run_result.json`

## Result

The exact cleanup sampler adapter now binds pickup candidates at upstream
selection time. The shared report renders `Exact pickup candidate action`,
requested-name presence, and before/after candidate counts next to the exact
target adapter evidence.

Runtime evidence:

- `output/debug-phase106-exact-pickup-candidate-binding-fixed/run_result.json`
- `output/debug-phase106-exact-pickup-candidate-binding-fixed/report.html`

Observed result:

- status: `blocked_capability`
- adapter hooks: `_get_place_target_candidates`, `_prepare_place_target`,
  `_select_pickup_object_exact_pickup_candidate_pool`
- pickup action: `injected_requested_candidate_name`
- candidate count before: 4
- requested present before: false
- candidate count after: 1
- requested present after: true
- grasp failures: 0
- candidate-removal calls: 0
- effective removals: 0
- candidate-name misses: 0
- remaining blocker: direct `KeyError` invalid planner object name for the
  requested bread alias

The blocker is no longer an opaque repeated grasp-feasibility loop. The next
slice should address proof candidate source / runtime object alias validity
before another cleanup rerun.

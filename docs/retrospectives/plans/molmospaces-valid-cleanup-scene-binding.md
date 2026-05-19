# MolmoSpaces Valid Cleanup Scene Binding

**Status:** Completed under GSD Phase 107 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0097
**Workflow:** `hybrid-phase-pipeline`

## Problem

The Phase 106 proof run closed the adapter implementation gap but exposed a
weaker evidence gap: the command used a stale cleanup scene XML path. Because
that path was missing, the exact-scene probe fell back to an upstream default
scene before reporting an invalid planner-object alias.

That means missing scene binding, invalid aliasing, and task feasibility can be
confused unless exact-scene runs have a hard checker gate.

## Decision

Require valid cleanup scene binding for exact-scene proof evidence.

This phase should:

- render cleanup task config blocker codes in shared planner reports and
  proof-bundle result cards;
- add a checker gate that requires the cleanup scene XML path to exist and have
  no `cleanup_scene_xml_missing` blocker;
- prove that the old Phase 106 artifact fails that stricter gate;
- rerun the exact pickup binding probe with the canonical seed-10 scene XML;
- record the corrected blocker shape in ADR, CONTEXT, source plan, and GSD
  state.

## Non-Goals

- Do not rewrite ADR-0097's adapter decision.
- Do not claim planner-backed proof from a blocked exact-scene probe.
- Do not rerun cleanup until a proof becomes planner-backed and promotes
  cleanup binding.

## Deliverables

- ADR-0098 and this source plan.
- `.planning/milestones/v1.98-phases/107-molmospaces-valid-cleanup-scene-binding/107-01-valid-cleanup-scene-binding-PLAN.md`.
- Shared report rendering for exact task config blockers.
- Planner probe checker option `--require-cleanup-scene-bound`.
- Focused unit coverage and one real local RBY1M valid-scene probe rerun.

## Verification

- `.venv/bin/ruff format --check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py roboclaws/molmo_cleanup/report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_manipulation_probe.py --accept-blocked-capability --accept-rby1m-curobo-blocked --require-cleanup-scene-bound output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`

## Result

Runtime evidence:

- `output/debug-phase107-valid-cleanup-scene-pickup-binding/run_result.json`
- `output/debug-phase107-valid-cleanup-scene-pickup-binding/report.html`

Observed result:

- status: `blocked_capability`
- cleanup scene XML: canonical seed-10 `procthor-10k-val/val_0.xml`
- cleanup task config blockers: none
- exact pickup action: `injected_requested_candidate_name`
- candidate count before: 17
- candidate count after: 1
- robot placement attempts: 1
- robot placement failures: 0
- placement scene diagnostics: 1
- visual capture count: 1
- grasp failures: 1
- candidate-removal calls: 0
- remaining blocker: `HouseInvalidForTask` after post-placement grasp
  feasibility, not missing scene binding

The next slice should target the one-failure post-placement grasp-feasibility
path for the exact requested object.

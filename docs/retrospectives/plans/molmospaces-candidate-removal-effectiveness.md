# MolmoSpaces Candidate Removal Effectiveness

**Status:** Completed under GSD Phase 105 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0072, ADR-0073, ADR-0094, ADR-0095
**Workflow:** `hybrid-phase-pipeline`

## Problem

Seed 10 is exhausted as a proof source, and the repeated executed blocker is
now grouped as one grasp-feasibility signature. The signature still hides the
next architectural question: do the 15 candidate-removal calls actually remove
the requested candidate from upstream `candidate_objects`, or are they
ineffective because the object name being removed does not match the candidate
pool?

## Decision

Add candidate-removal effectiveness diagnostics to the existing planner probe
adapter and shared report renderer.

This phase should:

- record threshold-exceeded and threshold-crossed state for each grasp failure;
- record candidate pool counts and candidate-name presence before/after each
  removal call;
- classify each removal call as effective or ineffective;
- include effective-removal and candidate-name-miss counts in proof summaries
  and signatures when present;
- render the new evidence in planner reports and proof-bundle reports without
  adding a second report implementation.

## Non-Goals

- Do not change upstream MolmoSpaces sampling behavior in this phase.
- Do not mark a blocked proof as planner-backed.
- Do not rerun a cleanup artifact unless a proof actually promotes binding.

## Deliverables

- ADR-0096 and this source plan.
- `.planning/milestones/v1.98-phases/105-molmospaces-candidate-removal-effectiveness/105-01-candidate-removal-effectiveness-PLAN.md`.
- Probe diagnostics for candidate-removal effectiveness.
- Shared report rendering for removal-call effectiveness.
- Checker and focused test coverage for the new fields.

## Verification

- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_task_feasibility.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_planner_task_feasibility.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_planner_task_feasibility.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`

## Result

The planner probe now distinguishes removal calls from effective candidate
removals. The report shows `Candidate Removal Effectiveness`, effective
removals, candidate-name misses, threshold rows, and removal-call deltas.

Runtime evidence:

- `output/debug-phase105-grasp-removal-effectiveness-probe/run_result.json`
- `output/debug-phase105-grasp-removal-effectiveness-probe/report.html`

Observed result:

- status: `blocked_capability`
- blocker: `HouseInvalidForTask`
- grasp failures: 17
- candidate-removal calls: 15
- effective removals: 0
- candidate-name misses: 15
- threshold-exceeded rows: 15
- threshold-crossed rows: 1
- robot-placement failures: 0

The evidence shows the repeated seed-10 blocker is not simply successful
candidate exhaustion. The requested planner object name was absent from the
upstream candidate pool for every removal call, so the candidate count stayed
at 17 while threshold-triggered removal calls accumulated.

The next runtime slice can use this to decide whether to fix candidate identity
binding, change proof candidate sourcing, or relax the upstream grasp check.

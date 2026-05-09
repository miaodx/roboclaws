# MolmoSpaces Bounded Planner Cleanup Executor

**Status:** Completed in GSD Phase 43 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0031, ADR-0032, ADR-0033, ADR-0034
**Workflow:** `hybrid-phase-pipeline`

## Problem

The architecture now has the pieces for planner-backed cleanup primitives:

- a shared semantic cleanup loop;
- a strict planner-backed cleanup primitive executor seam;
- probe-backed executor adaptation;
- exact sampled-task binding;
- observed-handle to planner-alias binding.

But the ADR-0003 cleanup harness still calls the semantic contract directly, so
reports remain `api_semantic` at the cleanup subphase level.

## Decision

Add a bounded, opt-in executor wiring path to the ADR-0003 cleanup harness.

This phase should:

- add a harness flag/parameter that uses attached planner proof for cleanup
  primitives;
- wrap the shared semantic cleanup loop with `PlannerBackedCleanupContractAdapter`
  only when the proof binding matches the current observed handle and target;
- leave non-matching objects on the normal semantic path;
- render the resulting planner-backed subphase evidence through the existing
  Cleanup Primitive Gate and Planner Cleanup Bridge report sections;
- keep default runs unchanged.

## Non-Goals

- Do not require live CuRobo execution in unit tests.
- Do not claim full multi-object planner-backed cleanup replacement.
- Do not use mismatched proof to block normal deterministic cleanup.
- Do not leak private observed-handle planner binding into Agent View.

## Deliverables

- ADR-0034 and this source plan.
- `.planning/phases/43-molmospaces-bounded-planner-cleanup-executor/43-01-bounded-planner-cleanup-executor-PLAN.md`.
- Optional harness executor wiring.
- Tests for matching proof, mismatched proof fallback, report/gate readiness,
  and default behavior unchanged.

## Verification Plan

- Passed focused tests around
  `run_realworld_cleanup(..., use_planner_proof_for_cleanup_primitives=True)`
  for matching proof and mismatched-proof fallback.
- Matching bound proof now produces planner-backed evidence for the matching
  bounded object while leaving the rest of the run `api_semantic`.
- Ruff check/format passed on changed Python/test files.
- Existing blocked real visual artifact checker remains valid.

## Completion Notes

The implementation deliberately does not claim full multi-object planner-backed
cleanup. It proves the shared loop has one executor wiring point: when attached
proof binding matches the observed handle and target fixture, that object's
`nav`, `pick`, `nav`, `open?`, and `place` subphases can be backed by
probe-derived planner primitive evidence. Default runs and mismatched proof
remain normal semantic cleanup.

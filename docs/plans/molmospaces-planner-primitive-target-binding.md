# MolmoSpaces Planner Primitive Target Binding

**Status:** Planned for GSD Phase 39 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0029, ADR-0030
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 38 added the planner-backed cleanup primitive executor seam. That closes
the architecture gap, but the strict gate should also reject executor evidence
that is not bound to the exact cleanup object and target fixture in the
semantic subphase.

Tool-level evidence alone is not enough for real object-specific RBY1M/CuRobo
replacement. A `pick` proof for one object must not satisfy a `pick` subphase
for another object, and a `place` proof must match the destination fixture.

## Decision

Tighten `cleanup_primitive_evidence` to require object and target binding for
strict planner-backed subphases.

This phase should:

- validate `planner_primitive_evidence.object_id` against the semantic object;
- validate target fixture binding for `navigate_to_receptacle`,
  `open_receptacle`, `place`, and `place_inside`;
- keep `navigate_to_object` and `pick` strict on object binding even when no
  target fixture is involved;
- report explicit blockers for mismatched or missing bindings;
- keep the current real artifact bridge-blocked until true object-bound
  planner primitive evidence exists.

## Non-Goals

- Do not implement the actual RBY1M/CuRobo executor in this slice.
- Do not weaken the Phase 38 executor schema.
- Do not create a second report or cleanup loop.

## Deliverables

- ADR-0030 and this source plan.
- `.planning/phases/39-molmospaces-planner-primitive-target-binding/39-01-planner-primitive-target-binding-PLAN.md`.
- Gate validation changes and focused tests for mismatch blockers.
- Current visual artifact checker verification in the expected blocked mode.

## Verification Plan

- Unit tests for matching, mismatched object, and mismatched target evidence.
- Focused executor/gate/bridge tests.
- Ruff check/format on changed files.
- Current ADR-0003 real visual artifact checker remains accepted as blocked.

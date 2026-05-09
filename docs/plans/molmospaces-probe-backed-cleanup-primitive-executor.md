# MolmoSpaces Probe-Backed Cleanup Primitive Executor

**Status:** Planned for GSD Phase 40 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0029, ADR-0030, ADR-0031
**Workflow:** `hybrid-phase-pipeline`

## Problem

The cleanup loop now has a strict executor seam and object/target-bound gate.
It still lacks the adapter that converts planner probe artifacts into executor
results safely.

The existing strict RBY1M/CuRobo proof is target-runtime proof only. It is not
cleanup primitive proof because it does not bind to an ADR-0003 observed object,
target fixture, or subphase.

## Decision

Add a probe-backed cleanup primitive executor adapter.

This phase should:

- preserve optional cleanup primitive binding fields when attaching planner
  proof to a cleanup report;
- add a callable executor adapter that reads a planner proof attachment;
- accept only strict target RBY1M/CuRobo execute proof with matching cleanup
  primitive binding;
- return blocked capability for generic standalone proof;
- prove through the shared semantic cleanup loop that bound probe proof can pass
  the Phase 38/39 gates while generic proof cannot.

## Non-Goals

- Do not claim the existing Phase 35 target proof is object-specific cleanup
  execution.
- Do not modify upstream MolmoSpaces task sampling in this slice.
- Do not run CuRobo during unit tests.

## Deliverables

- ADR-0031 and this source plan.
- `.planning/phases/40-molmospaces-probe-backed-cleanup-primitive-executor/40-01-probe-backed-cleanup-primitive-executor-PLAN.md`.
- Probe-backed executor adapter module.
- Attachment preservation for optional cleanup primitive binding.
- Focused tests for bound proof acceptance and generic proof rejection.
- Current real visual artifact checker remains accepted as blocked.

## Verification Plan

- Unit tests for attachment binding preservation.
- Unit tests for probe-backed executor match/mismatch/generic-block behavior.
- Focused shared-loop/gate/bridge tests.
- Ruff check/format on changed files.
- Current ADR-0003 visual artifact checker in blocked mode.

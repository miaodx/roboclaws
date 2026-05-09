# MolmoSpaces Planner Cleanup Bridge Readiness

**Status:** Planned for GSD Phase 37 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0018, ADR-0019, ADR-0026, ADR-0027, ADR-0028
**Workflow:** `hybrid-phase-pipeline`

## Problem

The repo now has strict standalone target RBY1M/CuRobo planner proof and a
shared cleanup-loop execution driver. The missing link is explicit bridge
readiness: cleanup reports should show whether the attached target proof is
usable for cleanup primitive replacement and whether the cleanup subphases
themselves have been replaced.

Today that state is spread across separate evidence panels. That makes it too
easy to over-read a standalone proof as cleanup-loop execution.

## Decision

Add planner cleanup bridge readiness evidence to ADR-0003 cleanup artifacts.

This phase should:

- add a bridge-readiness evidence builder and validator;
- derive target-runtime readiness from an attached planner proof;
- derive cleanup-subphase readiness from `cleanup_primitive_evidence`;
- render bridge evidence in the shared Cleanup Artifact Report;
- add checker flags for accepted blocked bridge evidence and strict future
  bridge readiness;
- generate an artifact using the Phase 35 RBY1M/CuRobo proof that still blocks
  on cleanup subphases remaining `api_semantic`.

## Non-Goals

- Do not mark cleanup subphases planner-backed.
- Do not replace object-specific cleanup primitives in this phase.
- Do not weaken the cleanup primitive gate or target runtime gate.
- Do not create a second report renderer.

## Deliverables

- ADR-0028 and this source plan.
- `.planning/phases/37-molmospaces-planner-cleanup-bridge-readiness/37-01-planner-cleanup-bridge-readiness-PLAN.md`.
- `planner_cleanup_bridge_evidence` schema, builder, and validator.
- Cleanup report section for bridge readiness.
- Realworld cleanup checker flags for bridge readiness.
- Focused tests and a generated artifact with attached RBY1M/CuRobo target
  proof.

## Verification Plan

- Unit tests for bridge evidence acceptance and blockers.
- Report rendering test for the bridge section.
- Checker tests for accepted blocked bridge evidence and rejected strict bridge
  readiness.
- Focused realworld cleanup generation with the Phase 35 target proof attached.
- Ruff check/format on changed files.

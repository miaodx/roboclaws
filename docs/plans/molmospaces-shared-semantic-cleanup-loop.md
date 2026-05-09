# MolmoSpaces Shared Semantic Cleanup Loop

**Status:** Planned for GSD Phase 36 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0003, ADR-0018, ADR-0021, ADR-0026, ADR-0027
**Workflow:** `hybrid-phase-pipeline`

## Problem

Report presentation is now shared, but cleanup-loop execution is still split
across multiple MolmoSpaces demos. The current-contract demo and ADR-0003
real-world cleanup harness both run:

`nav -> pick -> nav -> open? -> place`

through local inline code. That makes the demos look like separate
implementations even when they target the same underlying architecture, and it
creates a weak insertion point for planner-backed primitive replacement.

## Decision

Create a package-level semantic cleanup loop driver and refactor the two
cleanup demos to use it.

This phase should:

- add a shared driver for one object cleanup chain;
- keep report-facing semantic subphases canonical;
- let callers attach tracing and robot-view capture through callbacks;
- support optional `object_done` readback for the current-contract demo;
- support ADR-0003 fixture-style request keys without changing public contract
  behavior;
- keep cleanup primitive provenance unchanged until actual planner-backed
  primitive calls replace the backend behavior.

## Non-Goals

- Do not mark any current cleanup primitive as planner-backed.
- Do not change the scoring thresholds or public/private ADR-0003 contract.
- Do not add a second report renderer or special-case artifact layout.
- Do not wire the RBY1M/CuRobo probe directly into cleanup placement in this
  phase.

## Deliverables

- ADR-0027 and this source plan.
- `.planning/phases/36-molmospaces-shared-semantic-cleanup-loop/36-01-shared-semantic-cleanup-loop-PLAN.md`.
- Shared semantic cleanup loop driver.
- Refactored current-contract and ADR-0003 real-world cleanup demos.
- Focused tests proving canonical phase ordering and unchanged provenance.
- Regenerated lightweight artifacts showing the shared loop still renders the
  canonical report underlay.

## Verification Plan

- Focused unit tests for the shared driver and robot-view capture metadata.
- Existing current-contract cleanup demo tests.
- Existing ADR-0003 real-world cleanup harness tests.
- Ruff check/format on changed files.
- Generate small synthetic artifacts for both demo paths and inspect/check
  `semantic_substeps`.

# MolmoSpaces Observed Handle Planner Binding

**Status:** Planned for GSD Phase 42 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0003, ADR-0032, ADR-0033
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 41 made the planner probe emit cleanup primitive binding, but a real
ADR-0003 cleanup subphase still uses an Observed Object Handle while the
upstream planner task may use a MuJoCo body name or upstream sampled task name.

That means the current proof binding has only one object field trying to satisfy
two different jobs:

- match the sampled upstream planner task;
- match the public cleanup subphase request.

Those jobs need to be split before the probe-backed executor can be used for
ADR-0003 cleanup subphases.

## Decision

Add an **Observed Handle Planner Binding** slice.

This phase should:

- add a private mapping/evidence helper from observed handle plus target fixture
  to planner-facing pickup/place names;
- expose backend runtime planner names from MolmoSpaces state without putting
  them into Agent View;
- extend the planner probe binding request so planner aliases can match the
  sampled task while emitted cleanup primitive binding keeps the observed
  handle and public target fixture;
- keep generic Phase 41 behavior unchanged when no planner aliases are supplied;
- render/report the alias mapping as artifact evidence.

## Non-Goals

- Do not expose planner aliases or private handle mapping through ADR-0003 MCP
  tools.
- Do not force the upstream planner sampler to a specific object in this slice.
- Do not require a live CuRobo run in unit tests.
- Do not claim cleanup subphases are planner-backed until the executor is wired
  into the shared semantic cleanup loop with matching proof.

## Deliverables

- ADR-0033 and this source plan.
- `.planning/phases/42-molmospaces-observed-handle-planner-binding/42-01-observed-handle-planner-binding-PLAN.md`.
- Observed-handle planner binding helper/schema.
- Backend/runtime binding data for semantic and MolmoSpaces subprocess
  backends.
- Planner probe alias fields and exact-match promotion behavior.
- Focused tests for observed-handle binding, alias match, mismatch blockers,
  and executor compatibility.

## Verification Plan

- Unit tests for observed-handle to planner-name mapping.
- Unit tests for alias-backed probe promotion and mismatch blockers.
- Executor tests proving emitted binding still matches observed-handle cleanup
  requests.
- Report/checker tests showing visual binding evidence.
- Ruff check/format on changed files.

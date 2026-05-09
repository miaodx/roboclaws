# MolmoSpaces Planner Probe Cleanup Binding

**Status:** Planned for GSD Phase 41 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0031, ADR-0032
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 40 added the adapter that can consume bound planner proof. The actual
planner probe does not yet emit that binding. Current RBY1M/CuRobo proof is
strict runtime evidence, but it remains generic sampled-task evidence.

Before real cleanup primitive replacement, the probe artifact must say which
pickup object and place receptacle it sampled, and whether those names match a
requested cleanup primitive.

## Decision

Add cleanup primitive binding diagnostics to
`scripts/run_molmo_planner_manipulation_probe.py`.

This phase should:

- add optional CLI fields for requested cleanup object, target, source, and
  tools;
- record sampled task binding from the upstream task config;
- promote `cleanup_primitive_binding` only when the requested binding exactly
  matches the sampled pickup/place task;
- record mismatch blockers otherwise;
- preserve generic probe behavior when no cleanup binding request is supplied.

## Non-Goals

- Do not force the upstream sampler to pick a specific object in this slice.
- Do not claim the existing Phase 35 proof is cleanup primitive proof.
- Do not run CuRobo in unit tests.

## Deliverables

- ADR-0032 and this source plan.
- `.planning/phases/41-molmospaces-planner-probe-cleanup-binding/41-01-planner-probe-cleanup-binding-PLAN.md`.
- Probe script binding fields and diagnostics.
- Focused tests for no request, matching request, and mismatch blockers.
- Current visual artifact checker remains accepted as blocked.

## Verification Plan

- Unit tests for requested binding parsing and sampled-task matching.
- Existing probe, attachment, primitive executor, and report tests.
- Ruff check/format on changed files.
- Current ADR-0003 real visual artifact checker in blocked mode.

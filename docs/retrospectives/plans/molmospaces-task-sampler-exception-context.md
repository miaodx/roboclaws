# MolmoSpaces Task Sampler Exception Context

**Status:** Completed in Phase 76 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0067-preserve-task-sampler-exception-context.md`

## Goal

Make exact task-sampler context survive planner-probe worker exceptions so
target-side `HouseInvalidForTask` blockers are reviewable without manual
artifact archaeology.

## Problem

The Phase 75 target-feasibility blocker matrix links the current target-side
fallback blockers, but the linked proof reports failed during upstream task
sampling. Because `sample_task()` can raise before normal policy execution
returns, the worker-exception path did not prove that the exact sampler adapter
had already forced the requested cleanup target into the upstream task sampler.

That left a gap between the blocker matrix and the original discussion: reports
had the right shared visual architecture, but a target-feasibility failure still
lost important binding context before it reached the shared proof-result view.

## Scope

- Preserve exact cleanup task config and sampler adapter state on worker
  exceptions.
- Carry sampler adapter evidence into planner proof result summaries.
- Render sampler adapter state in the proof-bundle runner report.
- Tighten probe and bundle checkers so reports cannot silently omit sampler
  context that exists in evidence.
- Validate with focused unit tests and one warmed local RBY1M/CuRobo probe that
  reaches task sampling and fails with `HouseInvalidForTask`.

## Non-Goals

- Do not solve upstream `HouseInvalidForTask` or robot placement feasibility.
- Do not promote cleanup primitive binding without strict proof outputs.
- Do not create another report renderer or duplicate the shared MolmoSpaces
  underlay.

## Acceptance Criteria

- A worker exception after exact sampler adapter application includes
  `cleanup_task_sampler_adapter` in `run_result.json`.
- Proof-result summaries preserve that adapter evidence.
- Proof-bundle runner reports render whether the exact adapter was applied, its
  sampler class, and the forced planner target.
- Checkers validate the new report text when sampler adapter evidence is
  present.
- The local warmed probe artifact shows `HouseInvalidForTask` with exact sampler
  adapter context preserved.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase76-task-sampler-context-probe-warmed/report.html` reached
`execute_task_sample_start`, failed with real `HouseInvalidForTask`, and
preserved exact task config, exact sampler adapter state, requested cleanup
binding, and worker-stage evidence. Planner-backed cleanup readiness remains
blocked on upstream task feasibility.

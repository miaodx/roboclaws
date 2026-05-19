# MolmoSpaces Task Sampler Failure Diagnostics

**Status:** Completed in Phase 77 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0068-capture-task-sampler-failure-diagnostics.md`

## Goal

Turn target-side `HouseInvalidForTask` from a generic upstream exception into a
structured report view that names the sampler failure mode.

## Problem

Phase 76 proved that exact task config and the exact sampler adapter are applied
before the sampler raises. The report still did not say what inside the sampler
caused the failure. The only clue was an upstream stderr line saying the book
asset was dynamically blacklisted after repeated robot-placement failures.

## Scope

- Add a probe-local diagnostic adapter around upstream task-sampler hooks.
- Record robot-placement attempts, asset failure reasons, candidate removals,
  and placement config.
- Persist the diagnostics in planner probe run results.
- Render the diagnostics in the planner manipulation report and compact proof
  bundle result cards.
- Validate with focused tests and a warmed local RBY1M/CuRobo probe.

## Non-Goals

- Do not patch MolmoSpaces upstream source.
- Do not change cleanup semantics or report visual-core ordering.
- Do not claim planner-backed cleanup readiness.
- Do not solve robot placement feasibility in this slice.

## Acceptance Criteria

- `run_result.json` includes `task_sampler_failure_diagnostics` when the sampler
  reaches robot-placement attempts.
- `report.html` renders a `Task Sampler Failure Diagnostics` section with
  placement attempt counts, asset failure counts, and failure messages.
- Proof-result summaries preserve the diagnostics for future bundle reports.
- The warmed local artifact confirms the current blocker is repeated robot
  placement failure for `Book_23`.

## Result

Completed on 2026-05-10.

The warmed local artifact
`output/debug-phase77-task-sampler-failure-diagnostics/report.html` reports
17 robot-placement attempts and 17 asset failures for `Book_23`, all ending in
`RobotPlacementError` for
`book_be4d759484637aeb579b28e6a954b18d_1_0_8`. The next phase can now target
robot-placement feasibility directly instead of adding more alias plumbing.

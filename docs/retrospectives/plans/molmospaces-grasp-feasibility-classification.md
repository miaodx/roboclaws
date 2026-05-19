# MolmoSpaces Grasp-Feasibility Classification

**Status:** Completed for Phase 82 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0073-classify-grasp-feasibility-blockers.md`

## Goal

Carry post-placement grasp/candidate rejection evidence into proof-bundle result
summaries and runner reports.

## Problem

Individual planner probe reports now show grasp-failure evidence, but
proof-bundle summaries still expose only generic task-feasibility blocked state.
The runner needs a compact blocker kind so future selection can avoid retrying
known grasp-infeasible exact aliases.

## Scope

- Add `task_feasibility_blocker_kind`.
- Add `task_feasibility_blocker_summary`.
- Count `grasp_feasibility` blockers in proof-result summaries.
- Render those fields in proof-bundle runner reports.
- Validate checker and focused unit-test coverage.

## Non-Goals

- Do not generate replacement proof requests in this phase.
- Do not rerun the local simulator; Phase 81 already produced the artifact
  shape being classified.
- Do not change cleanup-loop semantics or proof readiness gates.

## Acceptance Criteria

- Grasp-only blocked proof outputs classify as `grasp_feasibility`.
- Robot-placement blocked proof outputs keep `robot_placement`.
- Runner reports show `Grasp-feasible blocked` and per-result blocker details.
- Focused tests and checkers pass.

## Result

Implemented.

Proof-result summaries now distinguish:

- `robot_placement` blockers from robot-placement failure diagnostics;
- `grasp_feasibility` blockers from post-placement grasp failures;
- generic `task_sampling` blockers when no more specific diagnostic exists.

The Phase 81 exact-book artifact now classifies as `grasp_feasibility` with
`17 grasp failures; 15 candidate-removal calls`. Runner reports render
`Grasp-feasible blocked` plus per-result blocker kind/detail, and the checker
validates those visible fields.

Verification:

- Focused ruff checks passed for changed Python/test files.
- Focused pytest passed for proof-result summaries, report rendering, and the
  runner checker.
- Manual Phase 81 artifact classification returned
  `grasp_feasibility_blocked_count=1`.

# MolmoSpaces Grasp-Feasibility Selection Memory

**Status:** Completed for Phase 83 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0074-surface-grasp-feasibility-selection-memory.md`

## Goal

Make proof request selection consume the Phase 82 `grasp_feasibility`
classification as durable retry memory.

## Problem

Proof-result summaries can now classify post-placement grasp/candidate
rejection, but selection artifacts still mostly speak in generic
task-feasibility terms. That is enough to exclude a request, but not enough to
review whether the active blocker is grasp feasibility or a broader target
task-sampling failure.

## Scope

- Preserve blocker kind/detail on excluded source requests.
- Preserve blocker kind/detail on generated fallback request provenance.
- Preserve blocker kind/detail on filtered fallback alias pairs.
- Render a dedicated `Grasp Feasibility Blockers` view in runner reports.
- Extend checker and focused unit-test coverage.

## Non-Goals

- Do not generate a new alias source in this phase.
- Do not rerun the local simulator.
- Do not promote cleanup primitive binding or planner-backed cleanup readiness.

## Acceptance Criteria

- Selection reports `grasp_feasibility_blocker_count`.
- Excluded source requests retain `grasp_feasibility` kind/detail.
- Filtered fallback pairs retain `grasp_feasibility` kind/detail.
- Runner reports show `Grasp blockers` and `Grasp Feasibility Blockers`.
- Focused tests and checkers pass.

## Result

Implemented.

Proof request selection now carries optional
`prior_task_feasibility_blocker_kind` and
`prior_task_feasibility_blocker_summary` fields through excluded requests,
generated fallback provenance, filtered pairs, and target/grasp blocker rows.
The report renders those fields and the checker validates them.

Verification:

- Focused ruff checks passed for changed Python/test files.
- Focused pytest passed for proof request selection, report rendering, and the
  runner checker.
- Manual Phase 81 artifact selection check returned
  `grasp_feasibility_blocker_count=1` and preserved
  `17 grasp failures; 15 candidate-removal calls`.

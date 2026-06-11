# MolmoSpaces Selected Proof Candidate Execution

**Status:** Completed for Phase 87 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0078-record-selected-proof-candidate-execution.md`

## Goal

Execute the selected exact-scene proof candidate after prior grasp-infeasible
requests are filtered, then record whether it is feasible or blocked.

## Problem

Phase 86 made the prior evidence path reviewable, but the active capability
blocker still depended on the selected candidate. The runner selected `proof_002`
after excluding the known `proof_001` book/shelf request. That selected request
needed local execution evidence.

## Scope

- Run the proof-bundle runner with prior standalone evidence, fallback filtering,
  RBY1M/CuRobo warmup, wide task-sampler placement profile, and
  `--execute-probes`.
- Validate the executed manifest with `--require-proof-outputs`.
- Update checker behavior so grasp-only task-sampler diagnostics do not require
  placement-failure rows.
- Add regression coverage for grasp-only diagnostics.

## Non-Goals

- Do not claim planner-backed cleanup readiness from a blocked proof.
- Do not rerun final cleanup.
- Do not broaden fallback generation yet.
- Do not commit generated output artifacts.

## Acceptance Criteria

- The selected proof candidate is executed locally.
- The runner checker passes with required proof outputs.
- The report classifies the selected proof result.
- If the candidate is blocked, the blocker is explicit and the next phase is
  narrowed accordingly.
- Focused lint, format, pytest, and manual checker validation pass.

## Result

Implemented.

The selected `proof_002` candidate executed but did not become planner-backed.
It failed as `blocked_capability` with
`task_feasibility_blocker_kind=grasp_feasibility` and
`17 grasp failures; 15 candidate-removal calls`. No planner-view image artifacts
were recorded because policy execution was not reached.

Verification:

- Focused ruff and format checks passed for the checker and tests.
- Focused pytest passed for checker coverage.
- `output/debug-phase87-selected-proof-execution/proof_bundle_run_manifest.json`
  passed the runner checker with `--require-proof-outputs`.

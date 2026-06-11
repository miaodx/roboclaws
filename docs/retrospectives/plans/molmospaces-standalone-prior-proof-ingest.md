# MolmoSpaces Standalone Prior Proof Ingest

**Status:** Completed for Phase 85 on 2026-05-10
**Parent plan:** `docs/retrospectives/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/archive/execution-log/0076-ingest-standalone-prior-proof-results.md`

## Goal

Let proof-bundle selection consume standalone planner-probe `run_result.json`
artifacts through the same prior-result summary interface used for prior
proof-bundle manifests.

## Problem

The Phase 81 standalone planner probe contains the exact grasp-feasibility
blocker the runner should remember, but the Phase 84 runner only consumed prior
bundle manifests. That forced either manual wrapping or re-running evidence
before selection could skip the known-infeasible cleanup pair.

## Scope

- Add `--prior-planner-probe-run-result` to the proof-bundle runner.
- Normalize standalone probe results into `Planner Proof Result Summary`.
- Reuse cleanup-pair selection memory from Phase 84.
- Preserve source run-result/report links and grasp-feasibility blocker detail.
- Relax the runner checker for partial selection with exhausted fallback pools.

## Non-Goals

- Do not scrape standalone HTML reports.
- Do not infer prior evidence when cleanup binding is absent.
- Do not claim new planner-backed cleanup readiness.
- Do not execute new RBY1M/CuRobo proofs.

## Acceptance Criteria

- A standalone prior probe can exclude a regenerated proof request by cleanup
  object/target pair.
- Excluded request evidence carries `prior_result_match_kind=object_target`.
- Runner reports render the prior match kind and grasp-feasibility blocker.
- Checker accepts the valid mixed state where one request is selected while a
  different exhausted fallback pool is recorded.
- Focused tests, lint, format checks, and manual runner checker pass.

## Result

Implemented.

The runner now normalizes standalone planner-probe run results into prior proof
result summaries before selection. Existing Phase 84 cleanup-pair matching then
filters regenerated requests without any manual wrapper manifest.

Verification:

- Focused ruff and format checks passed for changed runner, checker, and tests.
- Focused pytest passed for standalone prior probe ingestion and partial
  exhausted-fallback checking.
- Manual Phase 85 dry-run selected `proof_002`, excluded `proof_001` by
  `object_target`, carried `grasp_feasibility`, and passed
  `scripts/check_molmo_planner_proof_bundle_runner_result.py`.

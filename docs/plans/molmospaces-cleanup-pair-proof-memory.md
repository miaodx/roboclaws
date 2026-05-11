# MolmoSpaces Cleanup-Pair Proof Memory

**Status:** Completed for Phase 84 on 2026-05-10
**Parent plan:** `docs/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0075-match-proof-selection-memory-by-cleanup-pair.md`

## Goal

Keep proof selection memory attached to cleanup object/target identity even when
proof request IDs change across regenerated manifests.

## Problem

The Phase 83 selection-memory path preserves grasp-feasibility blockers, but
only after a prior result is found. Request IDs are not the strongest identity
for cleanup retry decisions; `object_id` plus `target_receptacle_id` is the
public cleanup pair that should remain stable across manifest regeneration.

## Scope

- Match prior proof results by request ID first.
- Fall back to matching by cleanup object/target pair.
- Record `prior_result_match_kind`.
- Render `Prior match` in runner selection tables.
- Extend checker and focused unit-test coverage.

## Non-Goals

- Do not infer matches from planner aliases alone.
- Do not generate new fallback alias sources.
- Do not rerun local RBY1M/CuRobo proofs.

## Acceptance Criteria

- A regenerated request with the same object/target pair inherits prior blocked
  memory even when `request_id` differs.
- Existing request-id matches remain supported.
- Runner reports expose whether memory matched by `request_id` or
  `object_target`.
- Focused tests and checkers pass.

## Result

Implemented.

Proof request selection now builds prior-result indexes by request ID and by
cleanup object/target pair. Request ID wins when present; otherwise matching by
`object_id` plus `target_receptacle_id` carries the prior blocker into
selection memory and report views.

Verification:

- Focused ruff checks passed for changed Python/test files.
- Focused pytest passed for proof request selection, report rendering, and the
  runner checker.
- Manual regenerated-request selection check returned
  `prior_result_match_kind=object_target`.

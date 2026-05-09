# 38-01 Planner-Backed Cleanup Primitive Executor Plan

## Goal

Add the strict execution seam that lets the shared semantic cleanup loop replace
`api_semantic` subphases with planner-backed primitive execution only when the
exact subphase has per-call planner evidence.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add planner-backed cleanup primitive request/result models.
3. [ ] Add a contract adapter that calls a supplied primitive executor before
   delegating state synchronization to the underlying cleanup contract.
4. [ ] Ensure missing or blocked executor results fail closed in strict mode.
5. [ ] Add focused tests through `run_semantic_cleanup_loop`,
   `cleanup_primitive_evidence`, and `planner_cleanup_bridge_evidence`.
6. [ ] Re-run visual artifact checker against the current real
   MolmoSpaces/RBY1M report to guard the shared report views.

## Acceptance

- All cleanup subphases can report `primitive_provenance=planner_backed` through
  the shared semantic loop only when a primitive executor returns strict
  per-subphase evidence.
- Missing executor evidence does not silently fall back to planner-backed
  provenance.
- The cleanup primitive gate and planner cleanup bridge become strict-ready for
  all-planner-backed executor results.
- The default ADR-0003 cleanup path remains `api_semantic` until an executor is
  supplied.
- The existing Cleanup Artifact Report visual core remains intact.

## Verification

- `uv run ruff check` on changed Python files.
- `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q` on focused executor/gate/report tests.
- Real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  robot views, attached proof, cleanup primitive gate, and planner cleanup
  bridge accepted as blocked.

## Risks

- The adapter could be mistaken for real RBY1M/CuRobo cleanup execution. Keep
  default demos unchanged and require explicit executor evidence before
  `planner_backed`.
- Semantic state synchronization after planner execution could blur provenance.
  Record planner execution separately from state sync in each response.

# 37-01 Planner Cleanup Bridge Readiness Plan

## Goal

Make ADR-0003 cleanup reports and checkers explicitly show whether the attached
planner proof plus cleanup subphase provenance are sufficient for planner-backed
cleanup primitive replacement.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add planner cleanup bridge evidence builder and validator.
3. [ ] Render bridge evidence in the shared cleanup report.
4. [ ] Wire ADR-0003 cleanup artifacts to build bridge evidence when a planner
   proof is attached.
5. [ ] Add realworld checker flags and focused tests.
6. [ ] Generate an artifact with the Phase 35 RBY1M/CuRobo target proof and
   record whether bridge readiness remains blocked.

## Acceptance

- A cleanup artifact with an attached RBY1M/CuRobo proof records target runtime
  readiness separately from cleanup subphase readiness.
- A cleanup artifact with `api_semantic` subphases keeps bridge status
  `blocked_capability`.
- Strict bridge readiness requires both target RBY1M/CuRobo proof and
  cleanup subphases that are all `planner_backed`.
- The report renders a visible `Planner Cleanup Bridge` panel without moving
  the canonical visual sections.

## Verification

- `uv run ruff check` on changed Python files.
- `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q` on focused bridge/report/checker
  tests.
- Generate a cleanup artifact with
  `--planner-proof-run-result output/molmo-planner-rby1m-curobo-memory-profile-execute/run_result.json`.

## Risks

- Bridge evidence can be mistaken for primitive replacement if labels are too
  soft; use `blocked_capability` while subphases remain `api_semantic`.
- Older attached Franka proof artifacts should not count as target RBY1M/CuRobo
  readiness.

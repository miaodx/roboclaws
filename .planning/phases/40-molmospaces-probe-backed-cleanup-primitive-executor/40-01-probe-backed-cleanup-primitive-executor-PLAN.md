# 40-01 Probe-Backed Cleanup Primitive Executor Plan

## Goal

Convert planner proof attachments into cleanup primitive executor results only
when the proof is strict target RBY1M/CuRobo evidence and carries a matching
cleanup primitive binding.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Preserve optional cleanup primitive binding fields in planner proof
   attachments.
3. [x] Add a probe-backed cleanup primitive executor callable.
4. [x] Block generic standalone proof with explicit missing-binding evidence.
5. [x] Add focused tests for bound proof, generic proof, and mismatch cases.
6. [x] Re-run focused executor/gate/bridge/report tests and the current real
   visual artifact checker.

## Acceptance

- Generic strict RBY1M/CuRobo proof cannot become cleanup primitive executor
  evidence.
- Bound strict RBY1M/CuRobo proof can produce `planner_backed` executor results
  for the matching object/tool/target.
- Mismatched object, tool, or target returns blocked capability.
- The shared cleanup primitive gate and bridge remain strict.
- Current ADR-0003 visual artifacts remain blocked until real bound proof exists.

## Verification

- Passed `uv run ruff check` on changed Python/tests.
- Passed `uv run ruff format --check` on changed Python/tests.
- Passed `./scripts/run_pytest_standalone.sh -q` on focused probe-backed executor,
  attachment, primitive-gate, bridge, and report tests.
- Passed real visual artifact checker against
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json` with
  bridge accepted as blocked.

## Risks

- Accidentally treating target runtime proof as primitive proof. The adapter
  must require explicit binding and fail closed when absent.
- Overfitting binding to one proof shape. Keep the binding schema small and
  explicit: object id, target receptacle id, and allowed tools.

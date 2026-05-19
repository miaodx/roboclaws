# 37-01 Planner Cleanup Bridge Readiness Plan

## Goal

Make ADR-0003 cleanup reports and checkers explicitly show whether the attached
planner proof plus cleanup subphase provenance are sufficient for planner-backed
cleanup primitive replacement.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add planner cleanup bridge evidence builder and validator.
3. [x] Render bridge evidence in the shared cleanup report.
4. [x] Wire ADR-0003 cleanup artifacts to build bridge evidence when a planner
   proof is attached.
5. [x] Add realworld checker flags and focused tests.
6. [x] Generate an artifact with the Phase 35 RBY1M/CuRobo target proof and
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

- `uv run ruff check roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py`
  passed.
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py`
  passed with 33 tests.
- `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`
  records `backend=molmospaces_subprocess`, `generated_mess_count=10`,
  `primitive_provenance=api_semantic`, `robot_view_steps=44`,
  `planner_cleanup_bridge_evidence.target_runtime_ready=true`,
  `planner_cleanup_bridge_evidence.cleanup_primitives_ready=false`, and
  `planner_cleanup_bridge_evidence.status=blocked_capability`.
- The realworld checker passed with `--require-robot-views`,
  `--require-planner-proof-attachment`,
  `--accept-blocked-planner-cleanup-primitives`, and
  `--accept-blocked-planner-cleanup-bridge`.

## Evidence

- `roboclaws/molmo_cleanup/planner_cleanup_bridge.py` owns the bridge schema,
  builder, and validator.
- `examples/molmospaces_realworld_cleanup.py` writes bridge evidence when a
  planner proof is attached.
- `roboclaws/molmo_cleanup/report.py` renders `Planner Cleanup Bridge`.
- `scripts/check_molmo_realworld_cleanup_result.py` can accept blocked bridge
  evidence or require future bridge readiness.
- The generated report includes Robot View Timeline, Attached Planner-Backed
  Proof, Cleanup Primitive Gate, and Planner Cleanup Bridge panels.

## Risks

- Bridge evidence can be mistaken for primitive replacement if labels are too
  soft; use `blocked_capability` while subphases remain `api_semantic`.
- Older attached Franka proof artifacts should not count as target RBY1M/CuRobo
  readiness.

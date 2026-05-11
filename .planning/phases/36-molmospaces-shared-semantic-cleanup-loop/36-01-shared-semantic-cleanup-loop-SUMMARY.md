# Phase 36 Summary: Shared Semantic Cleanup Loop

Completed: 2026-05-09
Backfilled: 2026-05-11
Source plan: `36-01-shared-semantic-cleanup-loop-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Unify MolmoSpaces cleanup-loop execution behind one shared semantic driver so
current-contract and ADR-0003 demos run the same `nav -> pick -> nav -> open? ->
place` architecture before planner-backed primitive replacement begins.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context references.
- Add a shared semantic cleanup loop driver with callback-based trace and robot-view hooks.
- Refactor `examples/molmospaces_cleanup_demo.py` to use the shared driver while keeping `object_done` readback.
- Refactor `examples/molmospaces_realworld_cleanup.py` to use the shared driver while preserving ADR-0003 public fixture requests.
- Add focused tests and rerun existing cleanup demo/report checks.
- Generate lightweight artifacts for both demo paths and record evidence.

## Recorded Status

Completed 2026-05-09.

## Evidence

- `uv run ruff check roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py tests/test_molmo_semantic_cleanup_loop.py`
  passed.
- `uv run ruff format --check roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py tests/test_molmo_semantic_cleanup_loop.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_semantic_cleanup_loop.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_primitive_evidence.py`
  passed with 19 tests.
- `output/molmospaces-shared-semantic-loop-current/run_result.json` records
  `cleanup_status=success`, `primitive_provenance=api_semantic`, and
  `semantic_loop_variant=navigate-pick-navigate-open-place-object_done`.
- `output/molmospaces-shared-semantic-loop-realworld/run_result.json` records
  `cleanup_status=success`, `primitive_provenance=api_semantic`,
  `semantic_loop_variant=navigate-pick-navigate-open-place`, and
  `cleanup_primitive_evidence.status=blocked_capability`.
- The realworld checker passed in accepted blocked-capability mode:
  `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --accept-blocked-planner-cleanup-primitives output/molmospaces-shared-semantic-loop-realworld/run_result.json`.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

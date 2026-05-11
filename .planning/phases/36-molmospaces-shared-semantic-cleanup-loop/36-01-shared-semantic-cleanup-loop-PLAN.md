# 36-01 Shared Semantic Cleanup Loop Plan

## Goal

Unify MolmoSpaces cleanup-loop execution behind one shared semantic driver so
current-contract and ADR-0003 demos run the same `nav -> pick -> nav -> open? ->
place` architecture before planner-backed primitive replacement begins.

## Status

Completed 2026-05-09.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [x] Add a shared semantic cleanup loop driver with callback-based trace and
   robot-view hooks.
3. [x] Refactor `examples/molmospaces_cleanup_demo.py` to use the shared
   driver while keeping `object_done` readback.
4. [x] Refactor `examples/molmospaces_realworld_cleanup.py` to use the shared
   driver while preserving ADR-0003 public fixture requests.
5. [x] Add focused tests and rerun existing cleanup demo/report checks.
6. [x] Generate lightweight artifacts for both demo paths and record evidence.

## Acceptance

- Both demos use the shared driver for object-level cleanup subphases.
- Semantic substeps still render as `nav, pick, nav, open?, place`.
- Current-contract artifacts keep `object_done`; ADR-0003 artifacts do not add
  it.
- Primitive provenance remains `api_semantic` in existing cleanup artifacts.
- The cleanup primitive gate remains blocked for current artifacts, not
  accidentally satisfied by refactoring.

## Verification

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

## Evidence

- `roboclaws/molmo_cleanup/semantic_cleanup_loop.py` owns the shared object
  cleanup chain.
- `robot_view_capture_for_tool` now supports caller-supplied object-id
  translation for ADR-0003 observed handles.
- Current-contract and ADR-0003 demos both call `run_semantic_cleanup_loop`.
- Fridge targets still render `navigate_to_object -> pick ->
  navigate_to_receptacle -> open_receptacle -> place_inside`.
- Existing cleanup primitives remain `api_semantic`; Phase 36 is architecture
  consolidation, not planner-backed primitive replacement.

## Risks

- Robot-view focus IDs differ between current-contract and ADR-0003 observed
  handles; the shared capture path must allow caller-specific object-id
  translation.
- Refactoring trace payloads can break checkers if public request keys change;
  ADR-0003 fixture-style keys need to be preserved where they matter.
- This is architecture consolidation only. Treating it as planner-backed
  primitive replacement would violate ADR-0018.

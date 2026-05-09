# 36-01 Shared Semantic Cleanup Loop Plan

## Goal

Unify MolmoSpaces cleanup-loop execution behind one shared semantic driver so
current-contract and ADR-0003 demos run the same `nav -> pick -> nav -> open? ->
place` architecture before planner-backed primitive replacement begins.

## Status

Planned 2026-05-09.

## Tasks

1. [ ] Add ADR/source-plan documentation and update roadmap/state/context
   references.
2. [ ] Add a shared semantic cleanup loop driver with callback-based trace and
   robot-view hooks.
3. [ ] Refactor `examples/molmospaces_cleanup_demo.py` to use the shared
   driver while keeping `object_done` readback.
4. [ ] Refactor `examples/molmospaces_realworld_cleanup.py` to use the shared
   driver while preserving ADR-0003 public fixture requests.
5. [ ] Add focused tests and rerun existing cleanup demo/report checks.
6. [ ] Generate lightweight artifacts for both demo paths and record evidence.

## Acceptance

- Both demos use the shared driver for object-level cleanup subphases.
- Semantic substeps still render as `nav, pick, nav, open?, place`.
- Current-contract artifacts keep `object_done`; ADR-0003 artifacts do not add
  it.
- Primitive provenance remains `api_semantic` in existing cleanup artifacts.
- The cleanup primitive gate remains blocked for current artifacts, not
  accidentally satisfied by refactoring.

## Verification

- `uv run ruff check` on changed Python files.
- `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q` on focused cleanup-loop/demo/report
  tests.
- Synthetic current-contract and ADR-0003 artifact generation.

## Risks

- Robot-view focus IDs differ between current-contract and ADR-0003 observed
  handles; the shared capture path must allow caller-specific object-id
  translation.
- Refactoring trace payloads can break checkers if public request keys change;
  ADR-0003 fixture-style keys need to be preserved where they matter.
- This is architecture consolidation only. Treating it as planner-backed
  primitive replacement would violate ADR-0018.

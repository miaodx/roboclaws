# Phase 36 Verification: Shared Semantic Cleanup Loop

Date: 2026-05-11
Source plan: `36-01-shared-semantic-cleanup-loop-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
36. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- Both demos use the shared driver for object-level cleanup subphases.
- Semantic substeps still render as `nav, pick, nav, open?, place`.
- Current-contract artifacts keep `object_done`; ADR-0003 artifacts do not add
  it.
- Primitive provenance remains `api_semantic` in existing cleanup artifacts.
- The cleanup primitive gate remains blocked for current artifacts, not
  accidentally satisfied by refactoring.

## Recorded Verification Evidence

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

## Artifact Integrity Checks

- Source plan exists: `36-01-shared-semantic-cleanup-loop-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-09`.
- Backfilled summary exists: `36-01-shared-semantic-cleanup-loop-SUMMARY.md`.
- Backfilled verification exists: `36-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 36 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.

# MolmoSpaces Shared Semantic Cleanup Loop

**Status:** Completed under GSD Phase 36 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0003, ADR-0018, ADR-0021, ADR-0026, ADR-0027
**Workflow:** `hybrid-phase-pipeline`

## Problem

Report presentation is now shared, but cleanup-loop execution is still split
across multiple MolmoSpaces demos. The current-contract demo and ADR-0003
real-world cleanup harness both run:

`nav -> pick -> nav -> open? -> place`

through local inline code. That makes the demos look like separate
implementations even when they target the same underlying architecture, and it
creates a weak insertion point for planner-backed primitive replacement.

## Decision

Create a package-level semantic cleanup loop driver and refactor the two
cleanup demos to use it.

This phase should:

- add a shared driver for one object cleanup chain;
- keep report-facing semantic subphases canonical;
- let callers attach tracing and robot-view capture through callbacks;
- support optional `object_done` readback for the current-contract demo;
- support ADR-0003 fixture-style request keys without changing public contract
  behavior;
- keep cleanup primitive provenance unchanged until actual planner-backed
  primitive calls replace the backend behavior.

## Non-Goals

- Do not mark any current cleanup primitive as planner-backed.
- Do not change the scoring thresholds or public/private ADR-0003 contract.
- Do not add a second report renderer or special-case artifact layout.
- Do not wire the RBY1M/CuRobo probe directly into cleanup placement in this
  phase.

## Deliverables

- ADR-0027 and this source plan.
- `.planning/milestones/v1.98-phases/36-molmospaces-shared-semantic-cleanup-loop/36-01-shared-semantic-cleanup-loop-PLAN.md`.
- Shared semantic cleanup loop driver.
- Refactored current-contract and ADR-0003 real-world cleanup demos.
- Focused tests proving canonical phase ordering and unchanged provenance.
- Regenerated lightweight artifacts showing the shared loop still renders the
  canonical report underlay.

## Verification Plan

- Focused unit tests for the shared driver and robot-view capture metadata.
- Existing current-contract cleanup demo tests.
- Existing ADR-0003 real-world cleanup harness tests.
- Ruff check/format on changed files.
- Generate small synthetic artifacts for both demo paths and inspect/check
  `semantic_substeps`.

## Completion Result

Phase 36 added `roboclaws/molmo_cleanup/semantic_cleanup_loop.py` as the
shared object-level cleanup driver. Both
`examples/molmospaces_cleanup_demo.py` and
`examples/molmospaces_realworld_cleanup.py` now call the same driver for
`navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? ->
place/place_inside`.

The current-contract demo keeps `object_done` as an optional readback step. The
ADR-0003 real-world cleanup harness keeps its stricter public loop without
`object_done`, while preserving fixture-style request payloads and observed
object handles.

Primitive provenance did not change. The generated ADR-0003 artifact still
records `primitive_provenance=api_semantic`, and
`cleanup_primitive_evidence.status=blocked_capability`.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py tests/test_molmo_semantic_cleanup_loop.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/semantic_cleanup_loop.py roboclaws/molmo_cleanup/semantic_timeline.py examples/molmospaces_cleanup_demo.py examples/molmospaces_realworld_cleanup.py tests/test_molmo_semantic_cleanup_loop.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_semantic_cleanup_loop.py tests/test_molmo_cleanup_demo.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_cleanup_report.py tests/test_molmo_cleanup_primitive_evidence.py`
- `.venv/bin/python examples/molmospaces_cleanup_demo.py --output-dir output/molmospaces-shared-semantic-loop-current --planner public_heuristic --restore-count 5`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmospaces-shared-semantic-loop-realworld --generated-mess-count 10`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --accept-blocked-planner-cleanup-primitives output/molmospaces-shared-semantic-loop-realworld/run_result.json`

# MolmoSpaces Planner Primitive Target Binding

**Status:** Completed GSD Phase 39 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0029, ADR-0030
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 38 added the planner-backed cleanup primitive executor seam. That closes
the architecture gap, but the strict gate should also reject executor evidence
that is not bound to the exact cleanup object and target fixture in the
semantic subphase.

Tool-level evidence alone is not enough for real object-specific RBY1M/CuRobo
replacement. A `pick` proof for one object must not satisfy a `pick` subphase
for another object, and a `place` proof must match the destination fixture.

## Decision

Tighten `cleanup_primitive_evidence` to require object and target binding for
strict planner-backed subphases.

This phase should:

- validate `planner_primitive_evidence.object_id` against the semantic object;
- validate target fixture binding for `navigate_to_receptacle`,
  `open_receptacle`, `place`, and `place_inside`;
- keep `navigate_to_object` and `pick` strict on object binding even when no
  target fixture is involved;
- report explicit blockers for mismatched or missing bindings;
- keep the current real artifact bridge-blocked until true object-bound
  planner primitive evidence exists.

## Non-Goals

- Do not implement the actual RBY1M/CuRobo executor in this slice.
- Do not weaken the Phase 38 executor schema.
- Do not create a second report or cleanup loop.

## Deliverables

- ADR-0030 and this source plan.
- `.planning/phases/39-molmospaces-planner-primitive-target-binding/39-01-planner-primitive-target-binding-PLAN.md`.
- Gate validation changes and focused tests for mismatch blockers.
- Current visual artifact checker verification in the expected blocked mode.

## Verification Plan

- Unit tests for matching, mismatched object, and mismatched target evidence.
- Focused executor/gate/bridge tests.
- Ruff check/format on changed files.
- Current ADR-0003 real visual artifact checker remains accepted as blocked.

## Completion Result

Phase 39 tightened the cleanup primitive gate so strict planner-backed
subphases must carry evidence for the exact semantic cleanup object. Target-side
subphases also require evidence for the same target receptacle. Mismatches now
produce explicit object or target blockers.

The Cleanup Primitive Gate report table now includes a binding column, so future
artifacts show whether planner evidence is object-bound, target-bound, or
mismatched. Current ADR-0003 artifacts remain correctly blocked because they
still use `api_semantic` cleanup primitives.

## Verification Evidence

- `uv run ruff check roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/report.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/report.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_report.py tests/test_molmo_semantic_cleanup_loop.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

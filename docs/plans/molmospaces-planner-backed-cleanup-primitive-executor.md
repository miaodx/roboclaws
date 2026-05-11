# MolmoSpaces Planner-Backed Cleanup Primitive Executor

**Status:** Completed GSD Phase 38 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0018, ADR-0027, ADR-0028, ADR-0029
**Workflow:** `hybrid-phase-pipeline`

## Problem

The MolmoSpaces cleanup architecture now has one shared semantic loop and one
shared Cleanup Artifact Report. It still lacks the execution seam that can
replace `api_semantic` cleanup primitives with per-subphase planner-backed
execution.

Without that seam, actual RBY1M/CuRobo integration would have to patch the
backend, ADR-0003 wrapper, MCP server, or demo runners directly. That would
recreate the multi-implementation drift the report-underlay work just removed.

## Decision

Add a strict planner-backed cleanup primitive executor interface and adapter.

This phase should:

- define a `CleanupPrimitiveRequest` and `CleanupPrimitiveResult` model for
  `nav -> pick -> nav -> open? -> place`;
- add an adapter that wraps a cleanup contract and only reports
  `primitive_provenance=planner_backed` when a supplied executor returns
  strict per-call planner evidence;
- keep default cleanup demos unchanged unless an executor is explicitly
  supplied;
- prove through tests that the existing cleanup primitive gate and planner
  cleanup bridge pass with an all-planner-backed executor and fail closed when
  an executor is missing or blocked;
- verify the current generated report still contains the canonical visual
  sections and remains blocked without the object-specific executor.

## Non-Goals

- Do not claim current real MolmoSpaces cleanup artifacts are planner-backed
  unless a real object-specific executor has run every subphase.
- Do not create a second cleanup loop or report renderer.
- Do not patch upstream MolmoSpaces in place.
- Do not require CuRobo JIT during unit tests.

## Deliverables

- ADR-0029 and this source plan.
- `.planning/phases/38-molmospaces-planner-backed-cleanup-primitive-executor/38-01-planner-backed-cleanup-primitive-executor-PLAN.md`.
- Planner-backed cleanup primitive executor module.
- Focused tests for strict pass, fail-closed behavior, and bridge readiness.
- Current visual artifact/checker verification showing the report still includes
  all shared visual views and remains blocked without object-specific planner
  execution.

## Verification Plan

- Unit tests for the executor adapter over the shared semantic loop.
- Unit tests proving cleanup primitive evidence and bridge readiness become
  strict-ready only with all-planner-backed subphase evidence.
- Ruff check/format on changed files.
- Run the ADR-0003 visual artifact checker against the latest real
  MolmoSpaces/RBY1M cleanup report with robot views, attached proof, cleanup
  primitive gate, and planner cleanup bridge.

## Completion Result

Phase 38 added `PlannerBackedCleanupContractAdapter` and the
`planner_cleanup_primitive_executor_v1` per-call evidence schema. The shared
semantic cleanup loop can now produce `planner_backed` subphases only through an
explicit executor result with strict evidence for that exact tool call.

The cleanup primitive gate was tightened so a manually relabeled
`planner_backed` substep without executor evidence still blocks. The report
keeps the shared visual core and now shows planner primitive evidence and state
sync provenance in the Cleanup Primitive Gate table.

Default ADR-0003 and current-contract demos remain `api_semantic` unless an
executor is explicitly supplied. The remaining follow-up is the real
object-specific RBY1M/CuRobo executor that calls this seam.

## Verification Evidence

- `uv run ruff check roboclaws/molmo_cleanup/planner_primitive_executor.py roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/types.py roboclaws/molmo_cleanup/__init__.py tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_primitive_executor.py roboclaws/molmo_cleanup/cleanup_primitive_evidence.py roboclaws/molmo_cleanup/semantic_timeline.py roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/types.py roboclaws/molmo_cleanup/__init__.py tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_primitive_executor.py tests/test_molmo_cleanup_primitive_evidence.py tests/test_molmo_planner_cleanup_bridge.py tests/test_molmo_semantic_cleanup_loop.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

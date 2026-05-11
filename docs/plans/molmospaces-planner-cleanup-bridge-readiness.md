# MolmoSpaces Planner Cleanup Bridge Readiness

**Status:** Completed under GSD Phase 37 on 2026-05-09
**Created:** 2026-05-09
**Source:** CONTEXT.md, ADR-0018, ADR-0019, ADR-0026, ADR-0027, ADR-0028
**Workflow:** `hybrid-phase-pipeline`

## Problem

The repo now has strict standalone target RBY1M/CuRobo planner proof and a
shared cleanup-loop execution driver. The missing link is explicit bridge
readiness: cleanup reports should show whether the attached target proof is
usable for cleanup primitive replacement and whether the cleanup subphases
themselves have been replaced.

Today that state is spread across separate evidence panels. That makes it too
easy to over-read a standalone proof as cleanup-loop execution.

## Decision

Add planner cleanup bridge readiness evidence to ADR-0003 cleanup artifacts.

This phase should:

- add a bridge-readiness evidence builder and validator;
- derive target-runtime readiness from an attached planner proof;
- derive cleanup-subphase readiness from `cleanup_primitive_evidence`;
- render bridge evidence in the shared Cleanup Artifact Report;
- add checker flags for accepted blocked bridge evidence and strict future
  bridge readiness;
- generate an artifact using the Phase 35 RBY1M/CuRobo proof that still blocks
  on cleanup subphases remaining `api_semantic`.

## Non-Goals

- Do not mark cleanup subphases planner-backed.
- Do not replace object-specific cleanup primitives in this phase.
- Do not weaken the cleanup primitive gate or target runtime gate.
- Do not create a second report renderer.

## Deliverables

- ADR-0028 and this source plan.
- `.planning/phases/37-molmospaces-planner-cleanup-bridge-readiness/37-01-planner-cleanup-bridge-readiness-PLAN.md`.
- `planner_cleanup_bridge_evidence` schema, builder, and validator.
- Cleanup report section for bridge readiness.
- Realworld cleanup checker flags for bridge readiness.
- Focused tests and a generated artifact with attached RBY1M/CuRobo target
  proof.

## Verification Plan

- Unit tests for bridge evidence acceptance and blockers.
- Report rendering test for the bridge section.
- Checker tests for accepted blocked bridge evidence and rejected strict bridge
  readiness.
- Focused realworld cleanup generation with the Phase 35 target proof attached.
- Ruff check/format on changed files.

## Completion Result

Phase 37 added `planner_cleanup_bridge_evidence` to ADR-0003 cleanup artifacts
when a strict planner proof is attached. The bridge evidence joins:

- the attached planner proof's target-runtime status;
- the cleanup primitive gate's per-subphase provenance.

The generated artifact
`output/molmospaces-planner-cleanup-bridge-readiness/report.html` includes all
canonical visual sections: before/after snapshots, semantic substeps, robot
view timeline with FPV/chase/map/verification views, attached planner initial
and final images, cleanup primitive gate, and planner cleanup bridge panel.

The bridge status is intentionally `blocked_capability`: the attached Phase 35
RBY1M/CuRobo proof is target-ready, but the cleanup subphases still carry
`primitive_provenance=api_semantic`.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py`
  passed.
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_cleanup_bridge.py roboclaws/molmo_cleanup/report.py examples/molmospaces_realworld_cleanup.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py`
  passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_cleanup_bridge.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py`
  passed with 33 tests.
- Generated:
  `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmospaces-planner-cleanup-bridge-readiness --backend molmospaces_subprocess --include-robot --record-robot-views --generated-mess-count 10 --planner-proof-run-result output/molmo-planner-rby1m-curobo-memory-profile-execute/run_result.json`.
- Checked:
  `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`.

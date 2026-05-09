# MolmoSpaces Planner Proof Request Report View

**Status:** Completed in GSD Phase 47 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0037, ADR-0038, Phase 46 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 46 writes private planner proof request manifests and a dry-run runner,
but the shared cleanup report does not yet show that handoff. A reviewer opening
`report.html` sees the visual core, cleanup primitive gate, and planner cleanup
bridge, but has to inspect sidecar JSON to learn which proof requests are ready
for local RBY1M/CuRobo generation.

## Decision

Render planner proof requests inside the shared Cleanup Artifact Report when a
run includes `planner_cleanup_proof_requests_v1`.

This phase should:

- add a `Planner Proof Requests` report section;
- show ready/blocked counts, cleanup object/source/target IDs, semantic tools,
  private planner aliases, and blockers;
- keep the section out of Agent View and public traces;
- teach the ADR-0003 checker to require the report section when a request
  manifest is present;
- keep older artifacts without request manifests valid;
- test deterministic and MCP cleanup reports through the shared renderer.

## Non-Goals

- Do not run real RBY1M/CuRobo proof generation.
- Do not move planner aliases into Agent View.
- Do not change proof request schema semantics from ADR-0037.
- Do not change cleanup primitive provenance.

## Deliverables

- ADR-0038 and this source plan.
- `.planning/phases/47-molmospaces-planner-proof-request-report-view/47-01-planner-proof-request-report-view-PLAN.md`.
- Shared report renderer support for planner proof requests.
- Checker and tests that enforce the report view when request manifests exist.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/report_visual_core.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py tests/test_check_molmo_realworld_cleanup_result.py`
- Existing pre-Phase-47 ADR-0003 artifacts without proof request manifests still pass the checker.

## Completion

Phase 47 shipped the shared report section, visual-core/checker coverage, and
focused tests for deterministic and MCP ADR-0003 cleanup paths. Existing
artifacts without request manifests remain checker-compatible.

# MolmoSpaces MCP Smoke Shared Semantic Loop

**Status:** Completed in GSD Phase 50 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0027, ADR-0036, ADR-0041, user visual-parity review
**Workflow:** `hybrid-phase-pipeline`

## Problem

MolmoSpaces cleanup demos now have a shared semantic cleanup loop and a shared
Cleanup Artifact Report visual core. However, the MCP smoke scripts still drive
the object cleanup sequence by hand. That leaves a second implementation of the
same domain behavior, and it is exactly where report drift can reappear.

## Decision

Refactor MCP smoke demos so they call `run_semantic_cleanup_loop`.

This phase should:

- route `scripts/run_molmo_agent_bridge_smoke.py` through the shared loop while
  preserving current-contract `object_done`;
- route `scripts/run_molmo_realworld_agent_mcp_smoke.py` through the shared loop
  while preserving fixture-style ADR-0003 requests and no `object_done`;
- add focused tests that fail if either smoke script returns to hand-written
  `nav/pick/nav/open/place` sequencing;
- keep report differences limited to evidence mode and contract-specific
  sections.

## Non-Goals

- Do not change MCP public tool names.
- Do not change the Cleanup Artifact Report renderer.
- Do not claim planner-backed cleanup primitives.
- Do not run real MolmoSpaces/RBY1M local-dev gates in this phase.

## Deliverables

- ADR-0041 and this source plan.
- `.planning/milestones/v1.98-phases/50-molmospaces-mcp-smoke-shared-semantic-loop/50-01-mcp-smoke-shared-semantic-loop-PLAN.md`.
- Refactored MCP smoke scripts using `run_semantic_cleanup_loop`.
- Focused tests for the shared-loop call path.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check scripts/run_molmo_agent_bridge_smoke.py scripts/run_molmo_realworld_agent_mcp_smoke.py tests/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `uv run ruff format --check scripts/run_molmo_agent_bridge_smoke.py scripts/run_molmo_realworld_agent_mcp_smoke.py tests/test_molmo_mcp_smoke_shared_semantic_loop.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_mcp_smoke_shared_semantic_loop.py tests/test_molmo_semantic_cleanup_loop.py tests/test_verify_just_recipes.py`

## Completion

Phase 50 refactored the current-contract MCP bridge smoke and ADR-0003 MCP smoke
to reuse `run_semantic_cleanup_loop`. Focused tests now monkeypatch that seam and
assert the current-contract smoke keeps `object_done`, while the ADR-0003 smoke
keeps fixture-style target requests and no `object_done`.

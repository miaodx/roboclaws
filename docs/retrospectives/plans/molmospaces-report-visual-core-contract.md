# MolmoSpaces Report Visual Core Contract

**Status:** Completed in GSD Phase 45 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0009, ADR-0021, ADR-0036
**Workflow:** `hybrid-phase-pipeline`

## Problem

The cleanup report renderer is now shared, but the validation surface still let
old and new artifact shapes pass. That is why `output/molmo-agent-bridge-visual-codex/report.html`
can look different from newer ADR-0003 reports while still satisfying the
looser checker gates.

There is also one remaining duplicate implementation around robot-view
semantics: the ADR-0003 MCP server hand-rolled the same
`nav -> pick -> nav -> open? -> place` capture mapping used by deterministic
cleanup paths.

## Decision

Centralize the report visual-core contract in code and make both cleanup
checkers use it. Then route the ADR-0003 MCP robot-view capture path through
the shared semantic timeline adapter.

This phase should:

- add a package-level visual-core checker for Cleanup Artifact Reports;
- require canonical section order in current-contract and ADR-0003 checkers;
- require report-facing semantic subphase labels when semantic cleanup
  substeps are present;
- let `robot_view_capture_for_tool` accept ADR-0003 `fixture_id` fields as
  target IDs;
- remove the ADR-0003 MCP server's duplicated robot-view capture mapping;
- add focused tests for stale raw semantic reports and fixture-ID capture.

## Non-Goals

- Do not add another HTML renderer.
- Do not regenerate all ignored `output/` artifacts in git.
- Do not change the private/public ADR-0003 contract.
- Do not claim planner-backed cleanup primitives or live multi-proof artifact
  generation.

## Deliverables

- ADR-0036 and this source plan.
- `.planning/milestones/v1.98-phases/45-molmospaces-report-visual-core-contract/45-01-report-visual-core-contract-PLAN.md`.
- Shared report visual-core contract helper.
- Checker updates for current-contract and ADR-0003 cleanup artifacts.
- ADR-0003 MCP robot-view capture reuse of `semantic_timeline`.
- Focused regression tests.

## Verification Plan

- Passed ruff check/format on changed Python and checker/test files.
- Passed focused checker/report/MCP pytest set.
- Passed broader cleanup report, deterministic cleanup, current-contract MCP,
  ADR-0003 MCP, and cleanup demo tests.
- Passed the existing real ADR-0003 visual artifact checker for
  `output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`.

## Completion Notes

The visual-core contract is now executable code instead of per-checker string
smoke tests. Old ignored artifacts may fail until regenerated; specifically,
`output/molmo-agent-bridge-visual-codex/report.html` is now identified as stale
because it lacks the canonical `Before And After` heading and semantic rail
shape.

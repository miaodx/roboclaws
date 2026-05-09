# MolmoSpaces Cleanup Planner Proof Attachment

**Status:** Planned under GSD Phase 26
**Created:** 2026-05-09
**Source:** ADR-0014, ADR-0016, ADR-0017, Phase 25 verification
**Workflow:** `hybrid-phase-pipeline`

## Problem

The standalone Franka planner proof now passes, but ADR-0003 cleanup artifacts
still show only `api_semantic` object moves. The report should be able to show
the strict planner proof alongside the cleanup loop without claiming that
cleanup object moves are planner-backed.

## Decision

Add an optional planner-proof attachment to ADR-0003 cleanup outputs.

This phase should:

- load and validate a strict planner probe `run_result.json`;
- copy planner proof initial/final images into the cleanup output directory;
- include a `planner_backed_manipulation_proof` block in cleanup `run_result.json`;
- render `Attached Planner-Backed Proof` in the shared cleanup report;
- add a checker flag that verifies the attachment while preserving
  `api_semantic` cleanup primitive provenance.

## Non-Goals

- Do not replace cleanup `pick`/`place` primitives with planner-backed
  execution.
- Do not make `api_semantic` cleanup pass as strict planner-backed cleanup.
- Do not alter the standalone planner proof checker.
- Do not require RBY1M CuRobo.

## Deliverables

- ADR-0017 and this source plan.
- `.planning/phases/26-molmospaces-cleanup-planner-proof-attachment/26-01-cleanup-planner-proof-attachment-PLAN.md`.
- Shared helper for validating/copying strict planner proof attachments.
- Cleanup harness/report/checker support for the attachment.
- A local ADR-0003 cleanup artifact with attached strict Franka proof views.

## Verification

- `uv run ruff check` / `uv run ruff format --check` on changed Python files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/python examples/molmospaces_realworld_cleanup.py --output-dir output/molmo-realworld-cleanup-planner-proof --backend molmospaces_subprocess --include-robot --record-robot-views --planner-proof-run-result output/molmo-planner-manipulation-probe-headless/run_result.json`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --require-robot-views --require-advisory-scoring --require-planner-proof-attachment output/molmo-realworld-cleanup-planner-proof/run_result.json`

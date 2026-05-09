# MolmoSpaces Planner Proof Bundle Runner Report

**Status:** Planned for GSD Phase 48
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0037, ADR-0038, ADR-0039, Phase 47 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

The Phase 46 runner writes a JSON command manifest, but the broader MolmoSpaces
demo architecture expects reviewable visual artifacts. A local operator should
not have to inspect JSON to see the exact proof commands, expected output
locations, or cleanup rerun command.

## Decision

Add a visual `report.html` for proof-bundle runner output.

This phase should:

- render `proof_bundle_run_manifest.json` through the shared report styling;
- include source cleanup artifact, status, counts, command rows, expected proof
  `run_result.json` and `report.html` paths, and cleanup rerun command;
- write the report in dry-run mode and executed modes;
- return the report path from the runner API and CLI status payload;
- test the dry-run path without invoking real RBY1M/CuRobo execution.

## Non-Goals

- Do not execute real planner probes in CI.
- Do not validate proof success inside the bundle runner report.
- Do not expose the runner report as Agent View.
- Do not replace individual planner probe reports.

## Deliverables

- ADR-0039 and this source plan.
- `.planning/phases/48-molmospaces-planner-proof-bundle-runner-report/48-01-planner-proof-bundle-runner-report-PLAN.md`.
- Shared report renderer support for proof-bundle runner manifests.
- Runner integration and tests.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`

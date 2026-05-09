# MolmoSpaces Planner Proof Bundle Runner Checker

**Status:** Planned for GSD Phase 49
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0039, ADR-0040, Phase 48 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

The proof-bundle runner now produces both JSON and HTML, but there is no
artifact checker for that pair. Without a checker, report drift or missing
command metadata would only be found manually.

## Decision

Add `scripts/check_molmo_planner_proof_bundle_runner_result.py`.

This phase should:

- validate `planner_cleanup_proof_bundle_run_manifest_v1`;
- accept either an output directory or `proof_bundle_run_manifest.json`;
- require `report.html` and its core sections;
- check request/command counts and command metadata;
- require expected proof `run_result.json` and proof `report.html` paths to be
  named in each command row;
- optionally require expected proof outputs to exist;
- add unit tests for valid, report-missing, command-missing, and
  require-proof-output failure cases.

## Non-Goals

- Do not execute real planner probes.
- Do not validate planner proof success.
- Do not validate cleanup rerun success.

## Deliverables

- ADR-0040 and this source plan.
- `.planning/phases/49-molmospaces-planner-proof-bundle-runner-checker/49-01-planner-proof-bundle-runner-checker-PLAN.md`.
- New checker script and focused tests.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_proof_bundle_runner_result.py`

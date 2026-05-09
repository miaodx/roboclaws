# MolmoSpaces Planner Proof Bundle Cleanup Rerun Artifacts

**Status:** Planned for GSD Phase 52 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0039, ADR-0040, ADR-0042, ADR-0043
**Workflow:** `hybrid-phase-pipeline`

## Problem

`run_molmo_planner_proof_bundle_from_requests.py --rerun-cleanup` can execute a
cleanup rerun after proof generation, but the runner manifest/report currently
show only the command. They do not make the resulting cleanup `run_result.json`
and `report.html` review targets.

## Decision

Promote cleanup rerun artifacts to first-class runner metadata.

This phase should:

- add `cleanup_rerun` metadata with output dir, run result, and report paths
  when `--rerun-cleanup` is requested;
- render a `Cleanup Rerun Artifact` report section;
- extend the runner checker to validate rerun metadata and optionally require
  rerun outputs to exist;
- add tests that cover repo-relative paths and cleanup-rerun output checks.

## Non-Goals

- Do not execute real GPU planner probes in CI.
- Do not validate planner proof success in the runner checker.
- Do not replace the ADR-0003 cleanup checker.

## Deliverables

- ADR-0043 and this source plan.
- `.planning/phases/52-molmospaces-planner-proof-bundle-cleanup-rerun-artifacts/52-01-proof-bundle-cleanup-rerun-artifacts-PLAN.md`.
- Runner manifest/report/checker updates.
- Focused tests.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

## Completion

Pending Phase 52 implementation.

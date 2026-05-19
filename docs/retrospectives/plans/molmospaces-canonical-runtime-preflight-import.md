# MolmoSpaces Canonical Runtime Preflight Import

**Status:** Completed under GSD Phase 100 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0090, local Phase99 preflight evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

The proof-bundle local runtime preflight checked `import molmospaces`, but the
upstream Python package is named `molmo_spaces`. That false-negative check
would block real proof execution even when the local MolmoSpaces runtime is
available.

## Decision

Change the preflight to check `import molmo_spaces` and update check/blocker
names to match the canonical package.

## Non-Goals

- Do not execute real proof commands.
- Do not change proof request selection.
- Do not change the Phase 99 manifest/report shape.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- The configured local MolmoSpaces Python passes the canonical import check.
- The runner report renders `molmo_spaces_import`.
- Tests cover blocked preflight using the canonical package name.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Implemented:

- canonical `molmo_spaces` import check;
- canonical check/blocker names in manifest/report/test evidence;
- updated Phase99 docs to avoid the colloquial import name.

Verification:

- `/tmp/roboclaws-molmospaces-spike/.venv/bin/python -c "import molmo_spaces; print('molmo_spaces import ok')"`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Local ready evidence: `output/debug-phase100-local-runtime-preflight-ready/proof_bundle_run_manifest.json`

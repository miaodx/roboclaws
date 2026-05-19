# Phase 100-01: Canonical Runtime Preflight Import

## Goal

Make proof-bundle local runtime preflight check the actual upstream Python
package, `molmo_spaces`, instead of the colloquial project name.

## Tasks

- Replace the preflight import command with `import molmo_spaces`.
- Rename preflight check and blocker codes to use `molmo_spaces`.
- Update tests and checker fixtures.
- Update Phase99 docs and add Phase100 ADR/plan/state.
- Generate local ready preflight evidence without running proof commands.

## Acceptance

- Local `/tmp/roboclaws-molmospaces-spike/.venv/bin/python` passes the
  canonical import check.
- Runner/checker tests pass with canonical check names.
- Local ready preflight evidence validates.
- The phase is committed with code, tests, and docs.

## Result

Complete on 2026-05-10.

Implemented:

- canonical `molmo_spaces` preflight import;
- canonical check/blocker code names;
- focused tests and local ready evidence.

Verification:

- `/tmp/roboclaws-molmospaces-spike/.venv/bin/python -c "import molmo_spaces; print('molmo_spaces import ok')"`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase100-local-runtime-preflight-ready/proof_bundle_run_manifest.json --min-selected-requests 0`

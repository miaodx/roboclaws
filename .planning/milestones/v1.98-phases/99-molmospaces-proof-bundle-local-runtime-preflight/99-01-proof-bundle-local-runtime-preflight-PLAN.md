# Phase 99-01: Proof-Bundle Local Runtime Preflight

## Goal

Make local proof-bundle execution fail reviewably when the configured
MolmoSpaces Python runtime is unavailable or cannot import the canonical
`molmo_spaces` package.

## Tasks

- Add a local runtime preflight to the proof-bundle runner.
- Short-circuit `--execute-probes` to `local_runtime_blocked` when preflight
  fails.
- Render a `Local Runtime Preflight` report section.
- Extend the proof-bundle checker for the new status/evidence.
- Add focused tests.
- Update ADR, plan, CONTEXT, and planning state.

## Acceptance

- Blocked local runtime attempts still produce manifest/report artifacts.
- The report shows Python path, import command, return code, and blocker.
- Proof/warmup commands do not execute when preflight fails.
- Checker validates the blocked status and evidence.
- Focused lint and pytest pass.
- The phase is committed with code, tests, and docs.

## Result

Complete on 2026-05-10.

Implemented:

- `local_runtime_preflight` manifest evidence;
- `local_runtime_blocked` runner status;
- report rendering and checker coverage;
- focused tests and local blocked evidence generation.

Verification:

- `.venv/bin/ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_proof_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase99-local-runtime-preflight-blocked/proof_bundle_run_manifest.json --min-selected-requests 0`

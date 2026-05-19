# Phase 132 Plan: MolmoSpaces Proof Command Semantic Subphases

## Goal

Make proof-bundle command rows show the cleanup semantic subphases they are
intended to prove before local proof execution.

## Tasks

1. Add `tools` and `semantic_subphases` to generated proof command manifest
   rows.
2. Render semantic subphase rails in proof-bundle runner command rows.
3. Validate semantic subphase report content in the runner checker when command
   rows include it.
4. Add focused tests.
5. Update ADR, plan, `CONTEXT.md`, pilot plan, and `.planning/STATE.md`.

## Acceptance Checks

- Command manifest rows include cleanup tools and display-ready semantic
  subphases.
- Runner reports render `Semantic subphases` using the shared phase-rail visual
  style.
- Checker validates subphase labels/details when present.
- Focused lint, format, pytest, and one dry-run artifact gate pass.

## Result

Complete on 2026-05-10.

The proof-bundle runner now carries and renders proof command semantic subphase
intent in the shared `nav, pick, nav, open?, place` vocabulary.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_writes_dry_run_manifest_and_report_from_inline_requests tests/test_molmo_cleanup_report.py::test_planner_proof_bundle_runner_report_renders_commands tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_valid_runner_artifact`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-phase126-phase125-bound-proof-cleanup-rerun/run_result.json --output-dir output/debug-phase132-proof-command-subphases-dry-run --runner-python python --probe-script scripts/run_molmo_planner_manipulation_probe.py --cleanup-script examples/molmospaces_realworld_cleanup.py --molmospaces-python /home/mi/.cache/molmospaces/venv/bin/python --steps 2 --exclude-prior-covered --prior-covered-min-proof-steps 2`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase132-proof-command-subphases-dry-run/proof_bundle_run_manifest.json --require-proof-execution-horizon --min-selected-requests 1`

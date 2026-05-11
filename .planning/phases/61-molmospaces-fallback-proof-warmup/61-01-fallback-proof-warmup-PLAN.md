# Phase 61 Plan: MolmoSpaces Fallback Proof Warmup

## Goal

Make the local proof-bundle runner able to warm RBY1M/CuRobo once before
executing generated fallback proof commands, with the warmup visible in the
shared runner manifest, report, and checker.

## Tasks

1. Add a proof-bundle runner warmup option and manifest field.
2. Build a reusable `config_import` warmup command that shares the proof command
   MolmoSpaces runtime and Torch extension cache.
3. Render the warmup command/artifacts in `render_planner_proof_bundle_runner_report`.
4. Validate warmup manifest/report consistency in the proof-bundle checker.
5. Add focused runner/report/checker tests and update source docs.

## Acceptance Checks

- Warmup command appears before proof commands when execution is requested.
- Warmup and proof commands share the same `--torch-extensions-dir`.
- The runner report includes `RBY1M/CuRobo Warmup`, warmup command, run result,
  and report path.
- Checker rejects missing warmup artifact fields when warmup is present.
- Focused ruff and pytest checks pass.

## Result

Completed on 2026-05-10.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

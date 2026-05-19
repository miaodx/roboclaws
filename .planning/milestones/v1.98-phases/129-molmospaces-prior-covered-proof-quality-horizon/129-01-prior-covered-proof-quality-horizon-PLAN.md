# Phase 129 Plan: MolmoSpaces Prior-Covered Proof Quality Horizon

## Goal

Make prior-covered proof selection respect the requested Planner Proof Quality
Evidence horizon, so one-step prior proofs do not suppress stricter proof
reruns.

## Tasks

1. Add a `prior_covered_min_proof_steps` selection option.
2. Require prior planner-backed cleanup-bound results to satisfy shared proof
   quality before counting as covered at stricter horizons.
3. Expose the option on the proof-bundle runner CLI.
4. Render the coverage horizon and prior proof quality in runner reports.
5. Add focused unit coverage and update ADR, plan, `CONTEXT.md`, pilot plan,
   and `.planning/STATE.md`.

## Acceptance Checks

- Default one-step prior-covered exclusion remains compatible.
- A one-step prior result is reselected when the requested horizon is two
  executed proof steps.
- Runner reports show the coverage minimum and prior proof quality evidence.
- Focused lint, format, and pytest gates pass.

## Result

Complete on 2026-05-10.

The proof-bundle runner now exposes `--prior-covered-min-proof-steps`, and the
selection/report path uses shared proof-quality evidence to decide whether a
prior result satisfies the coverage horizon.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_reselects_prior_covered_below_quality_horizon tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests`

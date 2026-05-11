# Phase 129 Summary: MolmoSpaces Prior-Covered Proof Quality Horizon

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `129-01-prior-covered-proof-quality-horizon-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make prior-covered proof selection respect the requested Planner Proof Quality
Evidence horizon, so one-step prior proofs do not suppress stricter proof
reruns.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The proof-bundle runner now exposes `--prior-covered-min-proof-steps`, and the
selection/report path uses shared proof-quality evidence to decide whether a
prior result satisfies the coverage horizon.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_reselects_prior_covered_below_quality_horizon tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests`

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py::test_proof_request_selection_reselects_prior_covered_below_quality_horizon tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_excludes_prior_covered_requests`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

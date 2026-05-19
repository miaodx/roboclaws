# Phase 85 Plan: MolmoSpaces Standalone Prior Proof Ingest

## Goal

Normalize standalone planner-probe prior evidence into the proof-bundle runner's
existing prior-result selection path.

## Tasks

1. Add a CLI option for standalone prior planner-probe run-result paths.
2. Extract cleanup-facing object/target binding from standalone probe evidence.
3. Convert standalone probe artifacts into prior proof result summaries.
4. Reuse existing request-id and cleanup-pair selection memory.
5. Update checker behavior for partial selection plus exhausted fallback pools.
6. Add focused tests and run a manual dry-run against Phase 81 evidence.

## Acceptance Checks

- Focused ruff checks pass for changed runner, checker, and tests.
- Focused format checks pass for changed Python files.
- Focused pytest covers standalone prior probe ingestion and checker behavior.
- Manual runner dry-run shows standalone Phase 81 evidence excluding the known
  grasp-infeasible request by cleanup pair.
- Runner checker passes on the manual dry-run manifest.

## Result

Implemented.

Standalone planner-probe `run_result.json` artifacts are now normalized into
the same prior-result summary interface as prior proof-bundle manifests. The
selection path then carries the Phase 81 grasp-feasibility blocker into the
Phase 85 dry-run and filters by `prior_result_match_kind=object_target`.

Focused validation passed:

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py::test_runner_ingests_standalone_prior_probe_run_result_by_cleanup_pair tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_partial_selection_with_exhausted_fallbacks`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase85-standalone-prior-proof-ingest-dry-run/proof_bundle_run_manifest.json`

## Status

Complete.

# 0078. Record Selected Proof Candidate Execution

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0076 lets standalone prior probe evidence exclude known grasp-infeasible
cleanup pairs. ADR-0077 makes that consumed prior evidence visible in the runner
report. After those changes, the runner selected the remaining source request
from `output/debug-real-binding/run_result.json`: `proof_002`, the bowl-to-sink
cleanup pair.

The next blocker was no longer report architecture. It was whether the selected
exact-scene request could produce a strict planner-backed proof with visual
artifacts, or whether it would reveal another task-feasibility blocker.

## Decision

Record selected proof candidate execution as local-dev evidence before searching
for broader fallback candidates.

The proof-bundle runner will be checker-gated with `--require-proof-outputs`
even when the executed proof is blocked. The checker must accept grasp-only
task-sampler diagnostics without requiring robot-placement failure rows, because
post-placement grasp/candidate rejection is a distinct blocker class.

## Consequences

- `proof_002` is not a grasp-feasible exact-scene proof candidate. It executed
  into `blocked_capability` with `task_feasibility_blocker_kind=grasp_feasibility`
  and `17 grasp failures; 15 candidate-removal calls`.
- The proof produced no planner-view image artifacts because it failed before
  policy execution.
- The next phase should search for or generate a different grasp-feasible
  exact-scene request, not retry the same selected source request unchanged.
- The runner checker now distinguishes grasp-only diagnostics from placement
  diagnostics when validating executed proof reports.

## Evidence

Phase 87 validates selected proof execution with:

- local execution at `output/debug-phase87-selected-proof-execution/`;
- runner checker pass with `--require-proof-outputs`;
- regression coverage for grasp-only task-sampler diagnostics without placement
  failure rows.

Verification on 2026-05-10:

- `uv run ruff check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_grasp_only_task_sampler_diagnostics tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase87-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs`

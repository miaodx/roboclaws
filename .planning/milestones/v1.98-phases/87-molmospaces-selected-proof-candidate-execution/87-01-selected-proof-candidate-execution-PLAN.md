# Phase 87 Plan: MolmoSpaces Selected Proof Candidate Execution

## Goal

Execute the currently selected exact-scene proof request and record whether it
is grasp-feasible.

## Tasks

1. Run the proof-bundle runner against `output/debug-real-binding/run_result.json`
   with Phase 81 standalone prior evidence.
2. Enable fallback filtering, wide task-sampler placement profile, warmup, and
   `--execute-probes`.
3. Validate the executed manifest with `--require-proof-outputs`.
4. Fix checker handling for grasp-only diagnostics if the executed proof exposes
   a checker/report contract gap.
5. Add focused regression coverage.
6. Record the result in ADR, plan, CONTEXT, ROADMAP, and STATE.

## Acceptance Checks

- Executed proof-bundle runner artifact exists under
  `output/debug-phase87-selected-proof-execution/`.
- Runner checker passes with `--require-proof-outputs`.
- Focused ruff checks pass for changed checker/test files.
- Focused format checks pass for changed checker/test files.
- Focused pytest covers grasp-only task-sampler diagnostics.

## Result

Implemented.

The selected `proof_002` bowl/sink request executed and produced a required
proof output, but it is not feasible. The proof result is
`blocked_capability`, classified as `grasp_feasibility`, with
`17 grasp failures; 15 candidate-removal calls`. The report has no planner-view
images because the proof failed before policy execution.

Focused validation passed:

- `uv run ruff check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_proof_bundle_runner_result.py::test_checker_accepts_grasp_only_task_sampler_diagnostics tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase87-selected-proof-execution/proof_bundle_run_manifest.json --require-proof-outputs`

## Status

Complete.

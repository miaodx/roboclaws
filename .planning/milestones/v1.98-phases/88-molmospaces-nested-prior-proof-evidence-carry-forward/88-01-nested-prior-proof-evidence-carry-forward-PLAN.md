# Phase 88 Plan: MolmoSpaces Nested Prior Proof Evidence Carry-Forward

## Goal

Carry nested prior proof evidence forward when a proof-bundle manifest is reused
as the next prior input.

## Tasks

1. Extend prior manifest loading to merge nested `prior_proof_result_summary`
   with the prior manifest's current `proof_result_summary`.
2. Preserve cleanup object/target IDs and grasp-feasibility blocker detail when
   excluded requests are converted into prior proof-result rows.
3. Add focused regression coverage for nested prior evidence and preserved
   blocker detail.
4. Run a dry-run using the Phase87 manifest as the only prior proof-bundle
   input.
5. Record the result in ADR, plan, CONTEXT, ROADMAP, and STATE.

## Acceptance Checks

- Nested prior evidence is consumed before proof request selection.
- The Phase88 dry-run excludes both current source requests and generates zero
  proof commands.
- The runner report includes `Prior Proof Evidence` for both older and newer
  carried proof results.
- Focused ruff checks pass for changed runner/test files.
- Focused format checks pass for changed runner/test files.
- Focused pytest passes for the proof-bundle runner tests.
- The Phase88 dry-run manifest passes the proof-bundle runner checker.

## Result

Implemented.

The runner now treats a prior proof-bundle manifest as a complete prior-evidence
carrier: nested `prior_proof_result_summary`, current `proof_result_summary`,
and excluded-request blocker details are merged into the same normalized prior
summary before selection.

The Phase88 dry-run at
`output/debug-phase88-nested-prior-carry-forward-dry-run/` used only the Phase87
manifest as prior input. It carried forward Phase81 evidence, excluded
`proof_001` and `proof_002` as `grasp_feasibility` blocked, generated no proof
commands, and rendered the carried evidence in `report.html`.

Focused validation passed:

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase88-nested-prior-carry-forward-dry-run/proof_bundle_run_manifest.json`

## Status

Complete.

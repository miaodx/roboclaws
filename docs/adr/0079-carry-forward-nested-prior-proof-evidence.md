# 0079. Carry Forward Nested Prior Proof Evidence

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0076 lets the proof-bundle runner ingest standalone planner-probe
`run_result.json` artifacts. ADR-0077 makes consumed prior proof evidence
visible in runner reports. ADR-0078 then executed the remaining selected source
request and produced a newer proof-bundle manifest.

That newer manifest already carried its own `proof_result_summary`, but it also
carried older consumed evidence in `prior_proof_result_summary`. If a later
runner pass used only the newer manifest as prior input, it could forget the
nested older evidence and reopen known blocked cleanup pairs.

## Decision

Treat a prior proof-bundle manifest as the complete prior-evidence carrier at
the runner normalization seam.

When loading a prior manifest, the runner will merge:

- the manifest's nested `prior_proof_result_summary`, if present;
- the manifest's current `proof_result_summary`;
- excluded-request blocker detail from its proof request selection.

The merged result remains the single `prior_proof_result_summary` interface
consumed by selection and rendered by the existing runner report. No new report
renderer or alternate visual path is introduced.

## Consequences

- A later proof-bundle manifest can stand alone as the next prior input without
  losing older consumed evidence.
- Grasp-feasibility blocker detail survives across multiple runner generations,
  including excluded-request rows synthesized from prior selection memory.
- The report stays on the shared proof-bundle runner visual path: `Prior Proof
  Evidence`, `Proof Request Selection`, and command tables are populated from
  one normalized evidence structure.
- The next capability blocker is unchanged: the current source/fallback alias
  pool is exhausted and both known source requests are grasp-infeasible, so a
  future slice must generate or discover different exact-scene candidates.

## Evidence

Phase 88 validates nested prior carry-forward with:

- regression coverage for consuming a prior manifest whose matching blocker
  exists only inside nested `prior_proof_result_summary`;
- regression coverage that excluded-request blocker details preserve cleanup
  object/target IDs and grasp-feasibility classification;
- dry-run output at
  `output/debug-phase88-nested-prior-carry-forward-dry-run/`, where the Phase87
  manifest alone excludes both current source requests, generates zero
  commands, and renders Phase81 plus Phase87 prior proof evidence.

Verification on 2026-05-10:

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff format --check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase88-nested-prior-carry-forward-dry-run/proof_bundle_run_manifest.json`

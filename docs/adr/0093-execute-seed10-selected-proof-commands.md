# 0093. Execute Seed 10 Selected Proof Commands

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0092 recorded seed 10 source rotation and selected five prior-aware proof
commands. Those commands were only dry-run evidence. The next decision was
whether to execute them immediately or keep rotating sources without proving
what seed 10 actually contributes.

Executing selected commands is necessary before claiming or rejecting new
planner-backed cleanup coverage from the seed 10 source pool.

## Decision

Execute the five selected seed 10 proof commands as a separate local-dev phase
using the same shared proof-bundle runner, RBY1M/CuRobo warmup, low CuRobo
memory profile, wide task-sampler placement profile, and local runtime
preflight.

Do not rerun cleanup unless at least one selected proof becomes
planner-backed and promotes cleanup binding.

## Consequences

- The seed 10 selected command set is no longer speculative.
- All five selected commands executed and produced proof artifacts.
- No command became planner-backed or promoted cleanup binding.
- All five commands were classified as `grasp_feasibility` blocked, with
  17 grasp failures, 15 candidate-removal calls, and one diagnostic view
  artifact per proof.
- The next useful work is not another cleanup rerun; it is reducing the shared
  RBY1M grasp-feasibility blocker or changing the proof candidate source.

## Evidence

Implemented in Phase 102 on 2026-05-10.

Artifacts:

- `output/debug-phase102-seed10-selected-proof-execution/proof_bundle_run_manifest.json`
- `output/debug-phase102-seed10-selected-proof-execution/report.html`
- `output/debug-phase102-seed10-selected-proof-execution/rby1m_curobo_warmup/run_result.json`

Key results:

- status: `probes_executed`
- local runtime preflight: `ready`
- command count: 5
- execution attempted: 5
- planner-backed count: 0
- cleanup-binding-promoted count: 0
- blocked count: 5
- task-feasibility-blocked count: 5
- grasp-feasibility-blocked count: 5
- timeout count: 0
- proof view artifact count: 5
- selected request IDs: `proof_001`, `proof_003`, `proof_005`, `proof_008`, `proof_010`

Verification:

- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase102-seed10-selected-proof-execution/proof_bundle_run_manifest.json --min-selected-requests 0 --require-proof-outputs`

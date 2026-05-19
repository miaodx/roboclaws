# 53-01 Planner Proof Bundle Execute Rerun Plan

## Goal

Provide one named local-dev command that executes a bound planner proof bundle,
reruns cleanup with those proof outputs, and gates the final cleanup artifact.

## Status

Completed 2026-05-10 with explicit local blocker.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add local-dev proof-bundle execute-rerun harness recipe.
3. [x] Add verify recipe that delegates to the local-dev harness.
4. [x] Add recipe-shape tests for strict runner and cleanup checker flags.
5. [x] Run focused static/unit verification.
6. [x] Attempt local GPU execution and record the result.

## Acceptance

- Existing `molmo-planner-proof-bundle-runner` remains a dry-run gate.
- New local-dev recipe uses `--execute-probes` and `--rerun-cleanup`.
- Runner checker requires proof outputs and cleanup rerun outputs.
- Final cleanup checker requires planner proof attachment, planner-backed
  cleanup primitives, and planner cleanup bridge readiness.
- Local execution result is recorded as pass or explicit blocker.

## Verification

- `uv run ruff check tests/test_verify_just_recipes.py` passed.
- `uv run ruff format --check tests/test_verify_just_recipes.py` passed.
- `./scripts/run_pytest_standalone.sh -q tests/test_verify_just_recipes.py` passed with 10 tests.
- `just harness::molmo-planner-proof-bundle-execute-rerun` executed all five
  RBY1M/CuRobo proof probes and produced `planner_backed` proof artifacts, then
  failed the final strict cleanup checker because no proof promoted cleanup
  primitive binding.
- `scripts/check_molmo_planner_proof_bundle_runner_result.py
  --require-proof-outputs --require-cleanup-rerun-output
  output/molmo-planner-proof-bundle-execute-rerun/proof_bundle/proof_bundle_run_manifest.json`
  passed.
- `scripts/check_molmo_realworld_cleanup_result.py ... --require-planner-proof-attachment
  --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge
  output/molmo-planner-proof-bundle-execute-rerun/cleanup_rerun/run_result.json`
  passed.

## Completion Notes

- The local gate is now named and strict. It intentionally fails until the
  final cleanup rerun is planner-backed.
- Local artifact summary:
  - runner status: `cleanup_rerun`;
  - proof commands: 5;
  - proof statuses: all `planner_backed`;
  - final cleanup status: `success`;
  - cleanup primitive gate: `blocked_capability`;
  - planner cleanup bridge: `blocked_capability`.
- Root blocker: the planner probes execute sampled upstream tasks, but those
  sampled `pickup_obj_name` / `place_receptacle_name` values do not match the
  requested cleanup object/target aliases, so `cleanup_primitive_binding` is
  not promoted and the cleanup rerun correctly remains `api_semantic`.

## Risks

- The local gate may be expensive because it launches multiple RBY1M/CuRobo
  proof probes. Keep it out of default CI and report exact blockers if runtime
  execution fails.

# 53-01 Planner Proof Bundle Execute Rerun Plan

## Goal

Provide one named local-dev command that executes a bound planner proof bundle,
reruns cleanup with those proof outputs, and gates the final cleanup artifact.

## Status

Planned 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add local-dev proof-bundle execute-rerun harness recipe.
3. [ ] Add verify recipe that delegates to the local-dev harness.
4. [ ] Add recipe-shape tests for strict runner and cleanup checker flags.
5. [ ] Run focused static/unit verification.
6. [ ] Attempt local GPU execution and record the result.

## Acceptance

- Existing `molmo-planner-proof-bundle-runner` remains a dry-run gate.
- New local-dev recipe uses `--execute-probes` and `--rerun-cleanup`.
- Runner checker requires proof outputs and cleanup rerun outputs.
- Final cleanup checker requires planner proof attachment, planner-backed
  cleanup primitives, and planner cleanup bridge readiness.
- Local execution result is recorded as pass or explicit blocker.

## Verification

- `uv run ruff check tests/test_verify_just_recipes.py`
- `uv run ruff format --check tests/test_verify_just_recipes.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_verify_just_recipes.py`
- `just harness::molmo-planner-proof-bundle-execute-rerun`

## Risks

- The local gate may be expensive because it launches multiple RBY1M/CuRobo
  proof probes. Keep it out of default CI and report exact blockers if runtime
  execution fails.

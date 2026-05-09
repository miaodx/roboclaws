# 51-01 Planner Proof Bundle Runner Harness Plan

## Goal

Add a repeatable dry-run harness that proves the handoff from a fresh ADR-0003
cleanup artifact to a checked planner proof bundle runner report.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add `harness::molmo-planner-proof-bundle-runner`.
3. [x] Add `verify::molmo-planner-proof-bundle-runner`.
4. [x] Extend just recipe tests for the new harness and verify gate.
5. [x] Run focused verification gates.

## Acceptance

- The harness creates a fresh synthetic ADR-0003 cleanup artifact.
- The harness runs `run_molmo_planner_proof_bundle_from_requests.py` without
  `--execute-probes`.
- The harness checks the runner output with
  `check_molmo_planner_proof_bundle_runner_result.py`.
- The verify gate runs focused runner/checker/recipe tests before delegating to
  the harness.

## Verification

- `uv run ruff check tests/test_verify_just_recipes.py`
- `uv run ruff format --check tests/test_verify_just_recipes.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_verify_just_recipes.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `just harness::molmo-planner-proof-bundle-runner`
- `just verify::molmo-planner-proof-bundle-runner`

## Completion Notes

- Added `harness::molmo-planner-proof-bundle-runner` and
  `verify::molmo-planner-proof-bundle-runner`.
- The harness generates a fresh synthetic ADR-0003 cleanup artifact, dry-runs
  planner proof command generation, and checks the runner manifest/report.
- The default recipe does not pass `--execute-probes`.
- The harness exposed a checker path-resolution gap for repo-relative manifest
  paths; the checker now accepts existing relative paths before rebasing paths
  under the runner output directory.

## Risks

- The default recipe must stay dry-run. Executing real planner probes would move
  this from CI-safe artifact handoff into local-dev/GPU validation.

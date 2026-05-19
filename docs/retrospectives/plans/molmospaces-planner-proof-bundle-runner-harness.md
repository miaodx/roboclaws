# MolmoSpaces Planner Proof Bundle Runner Harness

**Status:** Completed in GSD Phase 51 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0037, ADR-0038, ADR-0039, ADR-0040, ADR-0042
**Workflow:** `hybrid-phase-pipeline`

## Problem

The proof request manifest, proof-bundle runner report, and runner checker now
exist, but the handoff is still a multi-command local recipe. That makes it easy
to skip the cleanup artifact, run the runner against stale proof requests, or
forget the checker.

## Decision

Add a dry-run harness and verify gate for the planner proof bundle runner.

This phase should:

- add `harness::molmo-planner-proof-bundle-runner`;
- generate a fresh synthetic ADR-0003 cleanup artifact with planner proof
  requests;
- run the proof-bundle runner without `--execute-probes`;
- check the runner output with the dedicated checker;
- add recipe tests that require the cleanup, runner, and checker scripts in the
  harness body.

## Non-Goals

- Do not execute real planner probes.
- Do not rerun cleanup with proof attachments.
- Do not require MolmoSpaces/RBY1M local-dev assets.
- Do not claim planner-backed cleanup primitive success.

## Deliverables

- ADR-0042 and this source plan.
- `.planning/milestones/v1.98-phases/51-molmospaces-planner-proof-bundle-runner-harness/51-01-planner-proof-bundle-runner-harness-PLAN.md`.
- New `harness::` and `verify::` recipes.
- Focused recipe tests and dry-run harness verification.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_verify_just_recipes.py`
- `uv run ruff format --check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_verify_just_recipes.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_verify_just_recipes.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `just harness::molmo-planner-proof-bundle-runner`
- `just verify::molmo-planner-proof-bundle-runner`

## Completion

Phase 51 added the proof-bundle runner dry-run harness and verify gate. The
harness writes a fresh synthetic ADR-0003 cleanup artifact, generates planner
proof commands without `--execute-probes`, and validates the runner report. It
also fixed the runner checker so repo-relative manifest paths resolve correctly.

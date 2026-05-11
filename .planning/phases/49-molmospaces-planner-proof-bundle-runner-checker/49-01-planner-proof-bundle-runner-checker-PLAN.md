# 49-01 Planner Proof Bundle Runner Checker Plan

## Goal

Add a focused checker for proof-bundle runner manifests and reports so dry-run
handoffs are gateable before local planner proof execution.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add checker script for runner manifest/report artifacts.
3. [x] Add tests for valid artifacts and failure modes.
4. [x] Run focused verification gates.

## Acceptance

- Checker accepts a runner output directory or `proof_bundle_run_manifest.json`.
- Checker validates schema, status, counts, command rows, expected proof
  `run_result.json`, expected proof `report.html`, and `report.html` sections.
- Checker has an opt-in flag to require expected proof outputs to exist.
- Tests cover valid, missing report, missing command metadata, and missing proof
  output when required.

## Verification

- `uv run ruff check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_proof_bundle_runner_result.py`

## Completion Notes

- Added `scripts/check_molmo_planner_proof_bundle_runner_result.py`.
- The checker accepts a bundle output directory or direct manifest path.
- It validates schema, status, counts, command metadata, report sections, and
  optional expected proof output existence.
- Focused tests cover the valid artifact plus missing report, missing command
  metadata, and required-proof-output failure modes.

## Risks

- The checker must not imply proof success. It validates runner handoff
  integrity only; real proof success remains checked per proof run.

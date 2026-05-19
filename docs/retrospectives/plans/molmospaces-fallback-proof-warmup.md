# MolmoSpaces Fallback Proof Warmup

**Status:** Completed in GSD Phase 61 on 2026-05-10
**Source:** CONTEXT.md, ADR-0052, Phase 58/60 fallback timeout evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

Generated fallback proof execution now shows that all four attempted fallback
proofs timeout at `rby1m_config_import`. The proof-bundle runner executes each
proof command directly, so first-use RBY1M/CuRobo config import and Torch
extension warmup can consume the proof budget before any generated alias reaches
task sampling.

## Decision

Add an explicit optional warmup step to the proof-bundle runner.

This phase should:

- add a runner flag for RBY1M/CuRobo warmup before proof execution;
- build a shared `config_import` warmup command with the same runtime/cache
  settings as proof commands;
- default the effective Torch extension cache to `output_dir/torch_extensions`
  when warmup is enabled and no cache path was provided;
- record warmup command/run-result/report paths in the runner manifest;
- render the warmup section in the runner report and validate it in the checker;
- add focused tests for command shape, report visibility, and checker coverage.

## Acceptance

- Dry-run manifests can include a visible warmup command when requested.
- Executed runs perform warmup before proof commands.
- Warmup and proof commands share the same Torch extension cache path.
- Runner report includes the warmup command and artifact paths.
- Checker validates warmup manifest/report consistency.
- Focused ruff and pytest checks pass.

## Out Of Scope

- Claiming generated fallback proof success.
- Relaxing strict per-proof validation or cleanup primitive binding promotion.
- Running the long local RBY1M/CuRobo retry as part of the code commit.

## Result

Completed in code and tests. The proof-bundle runner now accepts
`--warmup-rby1m-curobo`, records a visible `config_import` warmup command in
the manifest, renders a `RBY1M/CuRobo Warmup` report section, and validates the
warmup with the runner checker. When warmup is enabled without an explicit
Torch extension cache, the runner uses `output_dir/torch_extensions` for both
the warmup and proof commands.

## Validation

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

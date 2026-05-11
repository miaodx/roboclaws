# 52-01 Proof Bundle Cleanup Rerun Artifacts Plan

## Goal

Make cleanup rerun outputs from executed proof-bundle runner flows explicit,
reviewable, and checker-gated.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add cleanup-rerun artifact metadata to proof-bundle runner manifests.
3. [x] Render cleanup-rerun artifact paths in runner reports.
4. [x] Extend the runner checker and tests for cleanup-rerun outputs.
5. [x] Run focused verification gates.

## Acceptance

- Runner manifests include `cleanup_rerun.output_dir`, `cleanup_rerun.run_result`,
  and `cleanup_rerun.report` when `--rerun-cleanup` is requested.
- Runner reports render a `Cleanup Rerun Artifact` section.
- The runner checker validates cleanup rerun metadata and can require output
  existence.
- Existing dry-run manifests remain valid.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py` passed.
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py` passed after formatting `roboclaws/molmo_cleanup/report.py`.
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_check_molmo_planner_proof_bundle_runner_result.py` passed with 12 tests.

## Completion Notes

- `--rerun-cleanup` now records `cleanup_rerun.output_dir`,
  `cleanup_rerun.run_result`, and `cleanup_rerun.report` in the runner
  manifest.
- Runner reports now render `Cleanup Rerun Artifact` paths alongside proof
  commands and the cleanup rerun command.
- The runner checker validates cleanup-rerun metadata and can require the
  referenced final cleanup artifacts to exist.

## Risks

- The runner checker must not treat cleanup rerun output existence as proof of
  planner-backed cleanup success. The ADR-0003 cleanup checker owns that final
  semantic claim.

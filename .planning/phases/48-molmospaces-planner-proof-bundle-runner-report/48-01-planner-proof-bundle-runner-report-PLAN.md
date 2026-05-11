# 48-01 Planner Proof Bundle Runner Report Plan

## Goal

Make the local planner proof bundle runner produce a reviewable `report.html`
alongside its JSON command manifest.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add shared report rendering for proof bundle runner manifests.
3. [x] Add expected proof report paths to generated command metadata.
4. [x] Make the runner write and return the report path.
5. [x] Add dry-run tests for the report and API/CLI payload.
6. [x] Run focused verification gates.

## Acceptance

- The runner writes `proof_bundle_run_manifest.json` and `report.html`.
- The report shows source cleanup artifact, status, request counts, command
  count, exact probe commands, expected proof `run_result.json` paths, expected
  proof `report.html` paths, and optional cleanup rerun command.
- The runner API and CLI status payload include the report path.
- Dry-run tests do not invoke real RBY1M/CuRobo execution.
- Existing request-manifest and cleanup-report behavior remains unchanged.

## Verification

- `uv run ruff check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/report.py roboclaws/molmo_cleanup/planner_proof_requests.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py`

## Completion Notes

- `build_probe_commands` now records expected proof `report.html` paths.
- `run_molmo_planner_proof_bundle_from_requests.py` writes and returns
  `report.html` alongside `proof_bundle_run_manifest.json`.
- The runner CLI prints both manifest and report paths.
- The new report is explicit command evidence, not proof success.

## Risks

- A command report can be mistaken for proof success. Keep the report language
  explicit: it is command evidence and links to proof outputs, not proof
  validation.

# Phase 101-01: Seed 10 Source Rotation

## Goal

Record a new MolmoSpaces seeded source artifact and prove that prior-aware
proof selection can generate non-duplicate proof commands from it.

## Tasks

- Generate a seed 10 MolmoSpaces real-world cleanup artifact with robot views.
- Validate the source artifact with the real-world cleanup checker.
- Run proof-bundle selection in dry-run mode with prior proof memory enabled.
- Record selected and excluded proof requests.
- Update ADR, context, GSD state, and the broad manipulation spike plan.

## Acceptance

- Seed 10 source artifact validates with at least 10 generated objects and robot
  views.
- The proof-bundle dry-run validates.
- The phase records command count, selected requests, and blocker reason for
  excluded requests.
- The phase does not claim planner-backed coverage until selected commands are
  executed.

## Result

Complete on 2026-05-10.

Evidence:

- Source artifact: `output/debug-phase101-seeded-source-candidate-seed10/run_result.json`
- Source report: `output/debug-phase101-seeded-source-candidate-seed10/report.html`
- Dry-run manifest: `output/debug-phase101-seeded-source-candidate-selection-dry-run/proof_bundle_run_manifest.json`
- Dry-run report: `output/debug-phase101-seeded-source-candidate-selection-dry-run/report.html`

Observed results:

- cleanup status: `success`
- generated mess count: 10
- robot view step count: 44
- ready proof requests: 10 of 10
- selected dry-run commands: 5
- selected request IDs: `proof_001`, `proof_003`, `proof_005`, `proof_008`, `proof_010`
- excluded request count: 5
- exclusion reason: `prior_task_feasibility_blocked`

Verification:

- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py output/debug-phase101-seeded-source-candidate-seed10/run_result.json --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase101-seeded-source-candidate-selection-dry-run/proof_bundle_run_manifest.json --min-selected-requests 0`

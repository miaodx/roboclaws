# Phase 97-01: Post-Placement Rejection Views

## Goal

Make the current RBY1M grasp-feasibility blocker visually reviewable in the
same shared report underlay used by cleanup artifacts, standalone planner
probes, proof-bundle results, and prior-proof evidence.

## Tasks

- Add a shared post-placement rejection diagnostic view for grasp-failure
  diagnostics.
- Render it in standalone planner reports.
- Render it in proof-bundle result cards.
- Require checker coverage when grasp-failure diagnostics exist.
- Add focused tests for report rendering and checker gates.
- Update ADR, plan, CONTEXT, and planning state with the result.

## Acceptance

- Reports with `task_sampler_failure_diagnostics.grasp_failures` show
  `Post-Placement Rejection Views`.
- The view renders from one report helper rather than a per-report clone.
- Planner probe and proof-bundle checkers require the visual.
- Focused lint and pytest pass.
- The phase is committed with code, tests, and docs.

## Result

Complete on 2026-05-10.

Implemented:

- shared `Post-Placement Rejection Views` renderer;
- standalone planner report integration;
- proof-bundle result card integration;
- checker assertions for grasp-failure visual coverage;
- focused tests for the new report surface.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

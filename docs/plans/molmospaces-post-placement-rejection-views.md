# MolmoSpaces Post-Placement Rejection Views

**Status:** Completed under GSD Phase 97 on 2026-05-10
**Created:** 2026-05-10
**Source:** `CONTEXT.md`, ADR-0003, ADR-0088, Phase95/96 grasp-feasibility evidence
**Workflow:** `hybrid-phase-pipeline`

## Problem

The current broader MolmoSpaces proof path is blocked after robot placement:
selected RBY1M/CuRobo proof attempts clear the wide placement profile, then
fail through repeated grasp-failure reports and candidate-removal calls.

Phase 96 made blocked proofs visually reviewable in general, but the specific
post-placement rejection sequence still appeared mostly as tables. The broader
plan needs report visual parity for this blocker before another cleanup rerun
or proof-source rotation is interpreted.

## Decision

Add a shared post-placement rejection visual:

- render grasp failures, candidate removals, threshold removals, and candidate
  count movement as a compact diagnostic view;
- show that view in standalone planner reports;
- show the same view in proof-bundle result cards and prior-proof report paths;
- require checker coverage when grasp-failure diagnostics are present.

## Non-Goals

- Do not execute new real MolmoSpaces proof commands in this phase.
- Do not change proof request selection or fallback generation.
- Do not treat `grasp_feasibility` evidence as planner-backed cleanup success.
- Do not commit ignored `output/` artifacts.

## Acceptance Criteria

- Reports containing `task_sampler_failure_diagnostics.grasp_failures` render
  `Post-Placement Rejection Views`.
- Standalone planner reports and proof-bundle runner reports use one shared
  report helper for the view.
- Checkers fail if grasp-failure diagnostics exist but the visual is absent.
- Focused lint and pytest pass.

## Result

Complete on 2026-05-10.

Implemented:

- added a shared `Post-Placement Rejection Views` renderer for grasp-failure
  diagnostics;
- rendered the view in standalone planner reports and proof-bundle result
  cards;
- tightened planner-probe and proof-bundle checkers to require the visual when
  grasp-failure diagnostics are present;
- added focused report/checker tests.

Verification:

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`

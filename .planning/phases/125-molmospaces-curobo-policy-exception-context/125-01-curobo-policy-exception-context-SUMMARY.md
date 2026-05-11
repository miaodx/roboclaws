# Phase 125 Summary: MolmoSpaces CuRobo Policy Exception Context

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `125-01-curobo-policy-exception-context-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Preserve the real CuRobo pre-grasp failure state in the planner-probe artifact,
report, and checker after the valid `Bread_1` grasp cache has cleared the prior
blocker.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The artifact/report/checker seam is implemented and focused tests pass. The
real warmed exact proof rerun at
`output/debug-phase125-curobo-pregrasp-exception-context/run_result.json`
returned `planner_backed` with `steps_executed=1`,
`max_abs_qpos_delta=0.018310936580938183`, preserved CuRobo profile, sampled
task binding, cleanup primitive binding, and no cleanup binding blockers.
Because the real run succeeded, `policy_exception_context` was not emitted by
that artifact; the exception branch is covered by the focused unit tests.

## Evidence

- `.venv/bin/ruff check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/ruff format --check scripts/run_molmo_planner_manipulation_probe.py scripts/check_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_headless_renderer.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

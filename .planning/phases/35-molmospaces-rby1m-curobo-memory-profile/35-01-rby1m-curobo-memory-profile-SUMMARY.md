# Phase 35 Summary: RBY1M CuRobo Memory Profile

Completed: 2026-05-09
Backfilled: 2026-05-11
Source plan: `35-01-rby1m-curobo-memory-profile-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Retry target RBY1M/CuRobo execute mode with a visible, probe-local low-memory
planning profile before deciding whether cleanup primitive replacement is
blocked on planner tuning or hardware.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context references.
- Add probe CLI/profile support for RBY1M CuRobo low-memory settings.
- Record requested/effective profile settings in runtime evidence.
- Render/checker/test `CuRobo Memory Profile` report evidence.
- Rerun local RBY1M/CuRobo execute mode with the low-memory profile and record whether the blocker changes or strict target proof passes.

## Recorded Status

Completed 2026-05-09.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo execute artifact under
  `output/molmo-planner-rby1m-curobo-memory-profile-execute/`.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

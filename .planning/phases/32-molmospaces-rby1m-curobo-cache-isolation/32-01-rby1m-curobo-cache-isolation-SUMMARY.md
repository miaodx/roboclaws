# Phase 32 Summary: RBY1M CuRobo Cache Isolation

Completed: 2026-05-09
Backfilled: 2026-05-11
Source plan: `32-01-rby1m-curobo-cache-isolation-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Make the RBY1M/CuRobo warmup retry independent of stale global Torch extension
cache state and record extension-cache evidence in the planner probe artifact.

## Completed Tasks

- Add ADR/source-plan documentation and update roadmap/state/context references.
- Add a planner probe option for an explicit `TORCH_EXTENSIONS_DIR`.
- Record CuRobo extension cache diagnostics for known CUDA extensions.
- Render cache diagnostics in planner probe reports and checker/test it.
- Rerun local RBY1M/CuRobo config-import with an output-local cache and a longer timeout; if it passes, attempt execute mode and strict readiness.

## Recorded Status

Completed 2026-05-09.

## Evidence

- `uv run ruff check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `uv run ruff format --check scripts/run_molmo_planner_manipulation_probe.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_manipulation_probe.py tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_check_molmo_planner_manipulation_probe.py tests/test_molmo_cleanup_report.py tests/test_molmo_planner_headless_renderer.py`
- Local RBY1M/CuRobo isolated-cache artifact under
  `output/molmo-planner-rby1m-curobo-cache-isolation/`.

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

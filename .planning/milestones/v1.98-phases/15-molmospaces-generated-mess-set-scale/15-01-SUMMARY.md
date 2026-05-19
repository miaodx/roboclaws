# 15-01 Generated Mess Set Scale Summary

**Status:** Complete
**Completed:** 2026-05-09

## What Changed

- Added `roboclaws/molmo_cleanup/generated_mess.py` as the shared, pure
  Generated Mess Set selector and success-threshold helper.
- Threaded `generated_mess_count` through the real MolmoSpaces subprocess
  worker, backend wrapper, ADR-0003 harness CLI, and `just` recipes.
- Updated `report.html` and `private_evaluation.json` to show requested and
  actual generated counts.
- Added checker support for `--min-generated-mess-count`.
- Preserved the five-object synthetic fixture for fast tests while making the
  real ADR-0003 harness recipe request 10 objects by default.

## Evidence

- `./scripts/run_pytest_standalone.sh -q tests/test_molmospaces_realworld_cleanup.py tests/test_check_molmo_realworld_cleanup_result.py tests/test_molmo_cleanup_subprocess_backend.py tests/test_molmo_cleanup_report.py tests/test_verify_just_recipes.py tests/test_molmo_realworld_contract.py`
  - Result: 19 passed, 1 skipped.
- `.venv/bin/ruff check` on changed Python files
  - Result: passed.
- `.venv/bin/ruff format --check` on changed Python files
  - Result: passed.
- `just harness::molmo-realworld-cleanup "1" "output/molmo-realworld-cleanup-harness-scale-check" "帮我收拾这个房间" "10"`
  - Result: checker passed for one real MolmoSpaces/RBY1M seed.

## Real Run Summary

`output/molmo-realworld-cleanup-harness-scale-check/seed-1/run_result.json`:

- `requested_generated_mess_count`: 10
- `generated_mess_count`: 10
- `cleanup_status`: `success`
- `completion_status`: `success`
- `mess_restoration_rate`: 0.8
- `sweep_coverage_rate`: 1.0
- `disturbance_count`: 0
- `semantic_substeps`: 10
- `robot_view_steps`: 44
- robot-view PNGs: 176

## Residual Follow-Ups

- Multi-seed Phase 15 scale evidence can be run later if runtime cost is worth
  it. This phase intentionally used one real visual seed because 10-object
  RBY1M report capture took about 17 minutes.
- Model-agent/OpenClaw policy evaluation against the ADR-0003 contract remains
  a separate follow-up.
- Planner-backed RBY1M/Franka manipulation remains a separate follow-up.

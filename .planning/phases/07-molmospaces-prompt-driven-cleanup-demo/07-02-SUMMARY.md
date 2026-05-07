# Phase 7 Plan 02 Summary - Demo Harness And Verify

**Commit:** `a6e154a feat: add MolmoSpaces prompt cleanup harness`
**Status:** Complete

## Changes

- Extended `examples/molmospaces_cleanup_demo.py` with
  `--planner public_heuristic` and `--task`.
- Added `planner`, `task_prompt`, `planner_uses_private_manifest`, and
  `cleanup_plan` fields to `run_result.json`.
- Added `just harness::molmo-prompt-cleanup` and
  `just verify::molmo-prompt-cleanup`.
- Hardened `scripts/check_molmospaces_cleanup_result.py` with
  `--require-public-planner` and `--expect-task`.
- Kept the Phase 6 `scripted_reference` harness compatible.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py tests/test_molmo_cleanup_demo.py tests/test_verify_just_recipes.py`
- `just harness::molmo-prompt-cleanup`
- `just verify::molmo-prompt-cleanup`
- `just verify::molmo-cleanup`
- Pre-commit fast non-integration pytest subset passed.

## Harness Result

`output/molmo-prompt-cleanup-harness/run_result.json` recorded:

- `task_prompt=帮我整理这个房间`
- `planner=public_heuristic`
- `planner_uses_private_manifest=false`
- `cleanup_status=success`
- `restored_count=5/5`
- `primitive_provenance=api_semantic`

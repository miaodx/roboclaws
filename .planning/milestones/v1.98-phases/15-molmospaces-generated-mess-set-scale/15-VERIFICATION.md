# Phase 15 Verification

**Phase:** MolmoSpaces Generated Mess Set scale
**Status:** Verified complete
**Date:** 2026-05-09

## Goal-Backward Check

Phase 15 needed to close the `CONTEXT.md` gap where ADR-0003 still used a
five-object hidden Generated Mess Set. The completed implementation now lets the
real MolmoSpaces subprocess harness request a configurable hidden set and the
canonical ADR-0003 `just` recipe requests 10 generated objects by default.

## Acceptance Criteria

| Criterion | Result |
| --- | --- |
| `just harness::molmo-realworld-cleanup` requests 10 generated objects by default. | Passed. Recipe default is `generated_mess_count="10"` and passes `--generated-mess-count`. |
| Worker fails clearly if requested count cannot be satisfied. | Passed. Worker raises `expected at least N cleanup targets, found M`. |
| `run_result.json` records requested and actual generated counts. | Passed. Real evidence records both as 10. |
| Private evaluation generated count is at least 10 for real evidence. | Passed. `private_evaluation.generated_mess_count=10`. |
| Checker can enforce a minimum generated count. | Passed. Added `--min-generated-mess-count`; focused tests cover failure and success. |
| Report keeps Agent View, Private Evaluation, Final Result/Score, Cleanup Trace, and Robot View Timeline. | Passed. Real report contains all sections and 176 robot-view PNGs. |

## Commands Run

```bash
./scripts/run_pytest_standalone.sh -q \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_subprocess_backend.py \
  tests/test_molmo_cleanup_report.py \
  tests/test_verify_just_recipes.py \
  tests/test_molmo_realworld_contract.py

.venv/bin/ruff check \
  examples/molmospaces_realworld_cleanup.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  scripts/molmospaces_subprocess_worker.py \
  roboclaws/molmo_cleanup/generated_mess.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/subprocess_backend.py \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_subprocess_backend.py

.venv/bin/ruff format --check \
  examples/molmospaces_realworld_cleanup.py \
  scripts/check_molmo_realworld_cleanup_result.py \
  scripts/molmospaces_subprocess_worker.py \
  roboclaws/molmo_cleanup/generated_mess.py \
  roboclaws/molmo_cleanup/report.py \
  roboclaws/molmo_cleanup/subprocess_backend.py \
  tests/test_molmospaces_realworld_cleanup.py \
  tests/test_check_molmo_realworld_cleanup_result.py \
  tests/test_molmo_cleanup_subprocess_backend.py

just harness::molmo-realworld-cleanup \
  "1" \
  "output/molmo-realworld-cleanup-harness-scale-check" \
  "帮我收拾这个房间" \
  "10"
```

## Real Evidence

`output/molmo-realworld-cleanup-harness-scale-check/seed-1/run_result.json`:

```json
{
  "backend": "molmospaces_subprocess",
  "seed": 1,
  "requested_generated_mess_count": 10,
  "generated_mess_count": 10,
  "cleanup_status": "success",
  "completion_status": "success",
  "mess_restoration_rate": 0.8,
  "sweep_coverage_rate": 1.0,
  "disturbance_count": 0,
  "semantic_substeps": 10,
  "robot_view_steps": 44
}
```

Robot-view artifact count:

```text
176 PNGs under output/molmo-realworld-cleanup-harness-scale-check/seed-1/robot_views
```

## Residual Risk

The selector is still category-rule based and uses `api_semantic` MuJoCo state
mutation. That is acceptable for Phase 15 because the phase scope was hidden
mess-set scale, not model-agent policy evaluation or planner-backed robot
manipulation.

# Phase 82 Plan: MolmoSpaces Grasp-Feasibility Classification

## Goal

Classify post-placement grasp/candidate rejection as a proof-result blocker
kind in proof-bundle summaries and reports.

## Tasks

1. Add `task_feasibility_blocker_kind` to proof-result summaries.
2. Add `task_feasibility_blocker_summary` for compact report text.
3. Count `grasp_feasibility` blockers at summary level.
4. Render blocker kind/detail in proof-bundle runner reports.
5. Validate checker and focused tests.

## Acceptance Checks

- Focused ruff checks pass for changed Python files.
- Focused pytest covers robot-placement and grasp-feasibility classification.
- Proof-bundle runner report tests cover the new visual fields.

## Result

Implemented.

Proof-result summaries now emit `task_feasibility_blocker_kind`,
`task_feasibility_blocker_summary`, and
`grasp_feasibility_blocked_count`. Proof-bundle runner reports render the new
summary metric and per-result blocker details, and the checker validates those
fields when present.

Focused validation passed:

- `uv run ruff check` on the changed implementation, checker, and test files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual classification of the Phase 81 artifact reports
  `task_feasibility_blocker_kind=grasp_feasibility`.

## Status

Complete.

# Phase 83 Plan: MolmoSpaces Grasp-Feasibility Selection Memory

## Goal

Carry proof-result `grasp_feasibility` blocker classification into proof
request selection memory and runner report views.

## Tasks

1. Preserve prior blocker kind/detail on excluded source requests.
2. Preserve prior blocker kind/detail on generated fallback request metadata.
3. Preserve prior blocker kind/detail on filtered fallback pairs.
4. Add `grasp_feasibility_blocker_count` and a dedicated blocker list.
5. Render and checker-gate the new selection-memory view.

## Acceptance Checks

- Focused ruff checks pass for changed implementation, checker, and tests.
- Focused pytest covers source request, generated fallback, and filtered-pair
  grasp-feasibility memory.
- Runner report tests cover the `Grasp Feasibility Blockers` visual view.

## Result

Implemented.

Selection artifacts now expose `grasp_feasibility` as first-class retry memory
instead of only generic task-feasibility blocked state. The runner report
renders `Grasp blockers`, `Grasp Feasibility Blockers`, blocker kind, and
blocker detail across selection tables.

Focused validation passed:

- `uv run ruff check` on changed implementation, checker, and test files.
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py`
- Manual selection against the Phase 81 artifact reports
  `grasp_feasibility_blocker_count=1`.

## Status

Complete.

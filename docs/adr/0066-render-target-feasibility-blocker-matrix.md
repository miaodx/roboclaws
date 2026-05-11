# 0066. Render Target Feasibility Blocker Matrix

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0065 made filtered fallback pairs point to the exact prior proof artifacts
that established target-side `HouseInvalidForTask` blockers. The report still
split the evidence across `Excluded Requests` and `Filtered Fallback Pairs`,
which made the current blocker harder to review: source requests and generated
fallback pairs were both target-feasibility blocked, but no single view showed
that complete matrix.

The current source request blockers also do not have executed per-proof report
links in the available prior evidence. They should remain visible without
pretending that source proof links exist.

## Decision

Proof request selection will emit a `target_feasibility_blockers` manifest
section and count. The section will include:

- excluded source requests whose prior task-feasibility status is `blocked`;
- filtered generated fallback pairs whose reason is
  `prior_task_feasibility_blocked_pair`;
- prior status, task-feasibility status, blockers, proof artifacts, last worker
  stage, and execution-attempted state when available.

The proof-bundle runner report will render those rows as `Target Feasibility
Blockers`, and the runner checker will validate the count and report text.

## Consequences

- Reviewers can see the full target-feasibility blocker set in one runner
  report table instead of comparing source and fallback tables manually.
- Source request blockers remain honest: they appear as source rows even when
  no prior per-proof report path exists.
- This preserves the shared report architecture. The renderer consumes
  selection-owned evidence instead of re-deriving target-feasibility state.
- This does not solve upstream task feasibility or claim planner-backed cleanup
  readiness.

## Evidence

Phase 75 wrote
`output/debug-phase75-target-feasibility-blocker-matrix-dry-run/report.html`
and `proof_bundle_run_manifest.json`.

The dry-run reported:

- `fallback_status=exhausted`
- `generated_fallback_request_count=0`
- `target_feasibility_blocker_count=4`
- two `source_request` blockers for the original source requests;
- two `fallback_pair` blockers linked to Phase 65 proof reports with
  `last_worker_stage=worker_exception`;
- blocker codes remain `target_task_feasibility_blocked_pairs` and
  `no_fallback_candidate_available`.

Validation passed with:

```bash
uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase75-target-feasibility-blocker-matrix-dry-run
```

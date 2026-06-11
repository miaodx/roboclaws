# 0065. Preserve Target Feasibility Proof Links

Date: 2026-05-10

## Status

Accepted

## Context

After ADR-0064, the current fallback pool is no longer blocked by missing
pickup root aliases. The remaining actionable blocker is target-side
task-feasibility: prior exact-scene fallback attempts reached task sampling and
failed with `HouseInvalidForTask`.

The runner already rendered filtered object/target pairs, but those rows did
not carry the proof report, run result, or worker stage from the prior failed
attempt. While testing the richer evidence path, another issue surfaced:
generated fallback request IDs are local to a run. Two different prior manifests
can both contain `proof_001_fallback_01` for different planner aliases, so
merging prior results only by request ID can overwrite a distinct failed
attempt.

## Decision

Prior fallback proof results will merge by generated request ID plus planner
object alias plus planner target alias. Source proof requests still merge by
request ID.

Filtered task-feasibility pair rows will carry prior proof artifact fields when
available:

- prior status and task-feasibility status;
- prior `run_result.json`;
- prior `report.html`;
- stdout/stderr artifact paths;
- last worker stage;
- execution-attempted state.

The proof-bundle runner report will show prior feasibility, last worker stage,
blockers, and proof report in the `Filtered Fallback Pairs` table. The checker
will validate those values when present.

## Consequences

- A target-side filtered pair points to the exact prior proof artifact that
  established the `HouseInvalidForTask` filter.
- Prior fallback attempts from different manifests no longer overwrite each
  other just because their generated request IDs match.
- This remains private runner evidence. It does not bypass upstream task
  feasibility or claim planner-backed cleanup readiness.

## Evidence

Phase 74 wrote
`output/debug-phase74-target-feasibility-proof-links-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

The dry-run reported:

- `fallback_status=exhausted`
- `generated_fallback_request_count=0`
- `filtered_pair_count=2`
- both filtered pairs include prior proof report paths from Phase 65;
- `last_worker_stage=worker_exception` for both target-feasibility blocked
  pairs;
- blocker codes remain `target_task_feasibility_blocked_pairs` and
  `no_fallback_candidate_available`.

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase74-target-feasibility-proof-links-dry-run
```

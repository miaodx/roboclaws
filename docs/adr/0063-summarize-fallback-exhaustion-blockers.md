# 0063. Summarize Fallback Exhaustion Blockers

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0062 made generated fallback exhaustion visible as a first-class status.
That closed the "did the runner skip fallback generation or exhaust it?"
ambiguity, but the report still required a reviewer to infer the actual next
blocker from lower-level filtered alias, filtered pair, and unavailable source
rows.

For the current merged prior evidence artifact, the important answer is not
only `Fallback status: exhausted`. It is that no generated fallback commands
remain because:

- known object-side runtime siblings are non-root pickup bodies;
- known object/target fallback pairs are already task-feasibility blocked;
- excluded source requests have no remaining generated candidate after filters.

## Decision

When fallback generation reaches `status=exhausted`, the proof-bundle runner
will emit an `exhaustion_blockers` summary in the private fallback-generation
manifest section.

The summary uses stable blocker codes:

- `pickup_root_body_alias_required`
- `target_task_feasibility_blocked_pairs`
- `no_fallback_candidate_available`
- `fallback_candidate_pool_exhausted` as a generic fallback only when no
  evidence-specific blocker can be derived

The proof-bundle runner report renders those rows as `Fallback Exhaustion
Blockers`, and the checker validates the manifest counts plus report text.

## Consequences

- Exhausted fallback runs now name the next required work instead of forcing
  reviewers to manually combine low-level evidence rows.
- The fallback-generation schema remains private runner evidence; it does not
  alter Cleanup Agent inputs or claim planner-backed cleanup readiness.
- Future fallback alias derivation or upstream task-feasibility work can target
  blocker codes directly.

## Evidence

Phase 72 wrote
`output/debug-phase72-fallback-exhaustion-blockers-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

The dry-run reported:

- `fallback_status=exhausted`
- `generated_fallback_request_count=0`
- `fallback_required=true`
- `exhaustion_blocker_count=3`
- `pickup_root_body_alias_required=3`
- `target_task_feasibility_blocked_pairs=2`
- `no_fallback_candidate_available=2`

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase72-fallback-exhaustion-blockers-dry-run
```

# 0062. Surface Fallback Exhaustion Status

Date: 2026-05-10

## Status

Accepted

## Context

After Phase 70, the proof-bundle runner can merge alias discovery and
failed-candidate memory from multiple prior manifests. The resulting dry-run
correctly generated zero fallback commands, but the terminal state was still
spread across several fields:

- `fallback_required=true`
- `generated_fallback_request_count=0`
- empty selected/generated tables
- filtered alias and pair rows

That is enough for code, but weak for report review. A local-dev operator should
see at a glance that the fallback pool is exhausted rather than simply not run.

## Decision

Fallback generation will expose a first-class `status`:

- `disabled`
- `not_required`
- `generated`
- `exhausted`

The proof-bundle runner report will render this as `Fallback status`, and the
runner checker will validate the status/report consistency.

## Consequences

- Exhausted fallback pools are visible in the report metrics.
- The checker rejects malformed fallback-generation status values.
- The status does not alter proof readiness; it only classifies fallback command
  generation.

## Evidence

Phase 71 wrote
`output/debug-phase71-fallback-exhaustion-status-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

The dry-run reported:

- `fallback_status=exhausted`
- `generated_fallback_request_count=0`
- `fallback_required=true`
- `discovered_alias_count=5`
- `filtered_alias_count=7`
- `filtered_pair_count=2`

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase71-fallback-exhaustion-status-dry-run
```

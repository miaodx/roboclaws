# 0064. Normalize Pickup Root Runtime Aliases

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0063 made fallback exhaustion blockers visible. On the current merged prior
evidence, one blocker was `pickup_root_body_alias_required` because all
object-side discovered runtime siblings had already failed as non-root pickup
bodies.

Those aliases carry enough structure to test a narrower claim before searching
for another source. MolmoSpaces runtime aliases follow the observed pattern:

```text
<prefix>_<group>_<variant>_<room>
```

The failed pickup aliases have nonzero `variant` values. The original cleanup
binding already uses the corresponding variant-0 alias for each source request,
so the report should show that normalization instead of continuing to imply
that a root-body alias source is completely missing.

## Decision

Fallback generation will normalize object-axis runtime aliases with nonzero
variants to their variant-0 pickup root alias before command generation.

The runner will persist this as `normalized_aliases` in the private fallback
generation section and render it as `Normalized Pickup Root Aliases` in
`report.html`.

When an exhausted fallback pool has normalized all non-root object aliases, the
exhaustion blocker summary will not report `pickup_root_body_alias_required`.
The remaining blockers should then reflect target-side task feasibility and
candidate exhaustion.

## Consequences

- The runner uses the runtime alias naming structure as a small, local
  derivation rule instead of treating every non-root alias as a missing source.
- Reviewers can see whether object-side aliases were normalized to an existing
  root candidate or still need a richer source.
- This does not prove the normalized pair is task-feasible; strict proof output
  and prior pair filters remain authoritative.

## Evidence

Phase 73 wrote
`output/debug-phase73-pickup-root-alias-normalization-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

The dry-run reported:

- `fallback_status=exhausted`
- `generated_fallback_request_count=0`
- `normalized_alias_count=3`
- `exhaustion_blocker_count=2`
- blocker codes: `target_task_feasibility_blocked_pairs` and
  `no_fallback_candidate_available`

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase73-pickup-root-alias-normalization-dry-run
```

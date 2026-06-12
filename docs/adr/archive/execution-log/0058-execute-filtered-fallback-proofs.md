# 0058. Execute Filtered Fallback Proofs

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0057 made the proof-bundle runner remember failed generated fallback
candidates. The Phase 66 dry-run left two remaining proof commands for the
untried book runtime sibling
`book_be4d759484637aeb579b28e6a954b18d_1_2_8`.

Those commands needed local RBY1M/CuRobo execution evidence before any further
fallback generation work could decide whether the remaining sibling was viable
or whether the object-side fallback family was exhausted.

## Decision

Execute the failed-candidate-filtered fallback bundle locally with:

- the Phase 65 executed proof-bundle manifest as prior evidence;
- generated fallback request selection enabled;
- Phase 66 failed-candidate memory active;
- `--warmup-rby1m-curobo`;
- an output-local Torch extension cache;
- `--require-proof-outputs` runner validation.

The phase records the exact result even though cleanup readiness remains
blocked.

## Consequences

- The two remaining generated fallback commands were executed locally.
- Both reached task sampling with no timeout and no config-import timeout.
- Both failed with `AssertionError: Object is not a root body`.
- No proof became planner-backed, promoted cleanup binding, or recorded planner
  views.
- The next blocker is deriving or validating pickup root-body aliases before
  object-side fallback generation, not simply trying more sibling names from
  the same valid-name list.

## Evidence

The Phase 67 run wrote
`output/debug-phase67-filtered-fallback-execute/report.html` and
`proof_bundle_run_manifest.json`.

The proof request selection recorded:

- `generated_request_count=2`
- `discovered_alias_count=5`
- `filtered_alias_count=6`
- `filtered_pair_count=2`
- `unavailable_source_request_count=1`

The proof result summary recorded:

- `expected_count=2`
- `result_count=2`
- `execution_attempted_count=2`
- `task_feasibility_blocked_count=2`
- `planner_backed_count=0`
- `cleanup_binding_promoted_count=0`
- `timeout_count=0`
- `rby1m_config_import_timeout_count=0`
- `view_artifact_count=0`

Both `proof_001_fallback_01` and `proof_001_fallback_02` used
`book_be4d759484637aeb579b28e6a954b18d_1_2_8` and failed with
`AssertionError: Object is not a root body`.

Validation passed with:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py --require-proof-outputs output/debug-phase67-filtered-fallback-execute
```

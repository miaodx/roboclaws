# 0057. Remember Failed Fallback Candidates

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0056 executed runtime-sibling fallback proof commands. The run proved that
some generated candidates are not useful to retry:

- target-sibling alias pairs reached task sampling and blocked with
  `HouseInvalidForTask`;
- object-sibling aliases failed with `AssertionError: Object is not a root body`.

Before another local execution, the proof-bundle runner should use that prior
evidence to avoid regenerating known-bad candidates and should make every
filtered candidate visible in the runner report.

## Decision

Carry prior fallback generation metadata forward when a prior proof-bundle
manifest is used. During fallback generation:

- keep previously discovered runtime aliases available as candidate memory;
- filter object aliases that prior generated proofs reported as non-root bodies;
- filter exact object/target alias pairs that prior generated proofs already
  reported as task-feasibility blocked;
- render filtered aliases and filtered pairs in `report.html`;
- validate filtered-pair report consistency through the runner checker.

## Consequences

- Re-running fallback generation against the Phase 65 manifest no longer
  retries the known non-root body aliases.
- The runner no longer retries previously blocked target-sibling alias pairs.
- The report now shows both `Filtered Fallback Aliases` and
  `Filtered Fallback Pairs`, so candidate pruning remains reviewable.
- Planner-backed cleanup readiness remains blocked until a generated proof
  actually becomes planner-backed and promotes cleanup primitive binding.

## Evidence

The Phase 66 dry-run wrote
`output/debug-phase66-failed-fallback-candidate-memory-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

Using the Phase 65 executed bundle as prior input, the runner reported:

- `generated_request_count=2`
- `discovered_alias_count=5`
- `filtered_alias_count=6`
- `filtered_pair_count=2`
- `unavailable_source_request_count=1`

The remaining generated commands both use
`book_be4d759484637aeb579b28e6a954b18d_1_2_8` for `proof_001`. The runner
filtered:

- `book_be4d759484637aeb579b28e6a954b18d_1_1_8` and
  `bowl_46a21212675e4d90993a86b1232e6f40_1_1_8` as
  `prior_non_root_body_alias`;
- the prior target-sibling pairs from `proof_001_fallback_01` and
  `proof_002_fallback_01` as `prior_task_feasibility_blocked_pair`.

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py roboclaws/molmo_cleanup/report.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_planner_proof_bundle_runner_result.py tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_planner_proof_bundle_runner_result.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase66-failed-fallback-candidate-memory-dry-run
```

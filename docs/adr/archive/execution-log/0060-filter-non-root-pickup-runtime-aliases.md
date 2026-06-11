# 0060. Filter Non-Root Pickup Runtime Aliases

Date: 2026-05-10

## Status

Accepted

## Context

Phase 67 proved that discovered object-side runtime siblings such as
`book_..._1_1_8`, `book_..._1_2_8`, and `bowl_..._1_1_8` are not viable pickup
aliases: the MolmoSpaces sampler rejects them with `Object is not a root body`.

The alias names follow the runtime pattern:

```text
<prefix>_<group>_<variant>_<room>
```

The observed viable pickup aliases use variant `0`; the failed object siblings
use nonzero variants. The runner should reject those object-side candidates
before local execution instead of waiting for the sampler to fail.

## Decision

For object-axis fallback candidates that match the runtime alias pattern, only
variant `0` is eligible for command generation. Nonzero variants are filtered
with reason `not_pickup_root_body_alias`.

This filter applies only to object/pickup aliases. Target aliases are not
filtered by this rule because the current evidence shows target-side variant
changes can reach task sampling and fail for task feasibility instead of root
body validity.

## Consequences

- Fallback generation no longer creates object-side proof commands for runtime
  siblings that can be identified as non-root variants.
- The runner report makes this visible through `Filtered Fallback Aliases`.
- A dry-run against the Phase 62 KeyError evidence now generates only
  target-side fallback commands and filters three object-side non-root
  candidates up front.
- Planner-backed cleanup readiness remains blocked; this is a candidate-quality
  filter, not proof success.

## Evidence

The Phase 69 dry-run wrote
`output/debug-phase69-pickup-root-variant-filter-dry-run/report.html` and
`proof_bundle_run_manifest.json`.

Using the Phase 62 warmed fallback manifest as prior input, the runner reported:

- `generated_request_count=2`
- `discovered_alias_count=5`
- `filtered_alias_count=7`
- `filtered_pair_count=0`

The generated commands are target-side retries only:

- `proof_001_fallback_01`: current book root alias to shelf runtime sibling
- `proof_002_fallback_01`: current bowl root alias to sink runtime sibling

The object-side runtime siblings were filtered as `not_pickup_root_body_alias`.

Validation passed with:

```bash
uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase69-pickup-root-variant-filter-dry-run
```

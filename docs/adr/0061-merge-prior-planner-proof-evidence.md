# 0061. Merge Prior Planner Proof Evidence

Date: 2026-05-10

## Status

Accepted

## Context

The proof-bundle runner currently consumes one prior proof-bundle manifest.
That was enough while each retry produced one complete next input, but the
fallback path now has evidence spread across several artifacts:

- Phase 62 has the useful exact-scene `KeyError` valid-name evidence that
  enables runtime alias discovery.
- Phase 65 and Phase 67 have local execution results proving target-side
  fallback pairs can be task-feasibility blocked and object-side runtime
  siblings can be non-root bodies.
- Phase 68 carries the latest exhausted candidate memory.

Using only an older manifest can rediscover useful aliases while forgetting
newer filtered aliases or filtered pairs. Using only the latest manifest avoids
known failures but makes the local-dev handoff depend on picking the right
single artifact.

## Decision

The proof-bundle runner will accept multiple prior proof-bundle manifests and
merge them into one prior evidence summary before request selection.

The merge keeps:

- prior proof results, deduplicated by request id;
- carried discovered runtime aliases;
- carried filtered aliases;
- carried filtered alias pairs.

Later manifests may add evidence, but no manifest should erase earlier failed
candidate memory. The generated runner report remains the visible review
artifact for the merged selection result.

## Consequences

- Local-dev fallback runs can combine older alias-discovery evidence with newer
  failed-candidate memory in one command.
- Reusing Phase 62 KeyError evidence no longer requires losing Phase 65/67/68
  feasibility filters.
- The runner CLI remains backward-compatible for one prior manifest.
- This does not prove planner-backed cleanup readiness; it only improves the
  private proof request selection input.

## Evidence

Phase 70 added a dry-run using multiple prior manifests:

```bash
.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase70-prior-evidence-merge-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase68-filter-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4
```

The runner reported:

- `selected_count=0`
- `generated_fallback_request_count=0`
- `fallback_required=true`
- `discovered_alias_count=5`
- `filtered_alias_count=7`
- `filtered_pair_count=2`

The checker passed:

```bash
.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase70-prior-evidence-merge-dry-run
```

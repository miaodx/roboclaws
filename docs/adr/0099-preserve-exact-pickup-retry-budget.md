# 0099. Preserve Exact Pickup Retry Budget

Date: 2026-05-10

## Status

Accepted

## Context

Phase 107 proved the exact cleanup scene XML was valid and the requested bread
alias existed in the scene. It also exposed a smaller adapter-side artifact:
exact pickup binding reduced `candidate_objects` to a single requested object,
and upstream `PickTaskSampler._select_pickup_object()` sets
`max_attempts = len(candidate_objects)`.

Upstream `report_grasp_failure()` removes a candidate only after its failure
count exceeds the default threshold of 2. With a candidate pool of length 1,
the exact-scene adapter stopped after one grasp failure, before the upstream
threshold/removal path could run.

That made the evidence less useful. It proved the requested object could be
placed, but not whether the exact object would be removed effectively once the
upstream grasp threshold was reached.

## Decision

Preserve an exact pickup retry budget inside the same exact-task sampler
adapter.

When the adapter filters or injects the requested pickup candidate, it repeats
that same exact candidate to a probe-local retry budget of 3. This keeps the
pool exact while allowing upstream's default `max_failures=2` threshold to be
crossed on the third failed grasp.

The binding evidence now records:

- `retry_budget`;
- `retry_budget_applied`;
- before/after candidate counts and names;
- requested-name presence before/after binding.

The shared report underlay renders the retry budget in standalone planner
reports and proof-bundle result cards.

## Consequences

- The adapter no longer trades unrelated candidate retries for only one exact
  candidate attempt.
- A corrected Phase 108 rerun against the valid seed-10 scene stayed
  `blocked_capability`, but now reached the intended threshold path:
  3 grasp failures, 1 threshold-crossed row, 1 candidate-removal call,
  1 effective removal, and 0 candidate-name misses.
- The remaining blocker is real post-placement grasp feasibility for the exact
  bread object, not scene binding, alias validity, candidate-name mismatch, or
  retry-budget collapse.
- This is still probe-local mitigation/evidence. It does not make a cleanup
  primitive planner-backed and does not change the shared semantic cleanup
  loop.

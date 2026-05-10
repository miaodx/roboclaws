# 0097. Bind Exact Pickup Candidate Pool

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0096 showed the repeated seed-10 grasp-feasibility signature was not true
candidate exhaustion. The proof probe recorded 17 grasp failures and 15
candidate-removal calls, but 0 effective removals and 15 candidate-name misses.
The requested planner object was not present in the upstream sampler's
`candidate_objects`, so removal calls never shrank the pool.

The exact cleanup sampler adapter already forced the requested place target,
but pickup-side binding still leaked through upstream sampling order. Applying
pickup binding at `reset()` was too early: the upstream sampler populates
`candidate_objects` later during scene initialization, immediately before
`_select_pickup_object()`.

Leaving this split in place creates two problems:

- reports can imply a grasp-feasibility blocker when the actual issue is
  pickup candidate identity;
- future cleanup proof work has to reason across multiple partial adapter
  implementations instead of one exact-task sampler adapter.

## Decision

Extend the existing exact cleanup sampler adapter to bind the pickup candidate
pool at the live upstream selection point.

The adapter now wraps `_select_pickup_object()` when available and records
**Exact Pickup Candidate Binding** evidence before upstream selection proceeds.
It filters the pool to the requested planner object when present, injects the
requested candidate name when absent, and records candidate counts/names plus
requested-name presence before and after binding. A `reset()` wrapper remains
only as a fallback for samplers without the selection hook.

Render the evidence through the shared planner/cleanup report underlay:

- standalone planner manipulation reports;
- proof-bundle result cards;
- checker gates for both generated report types.

This keeps ADR-0003/current-contract report parity intact: cleanup reports
still show semantic subphases as `nav -> pick -> nav -> open? -> place`, while
private proof reports add exact-task adapter evidence without creating a second
renderer.

## Consequences

- Future exact-scene probes can distinguish unrelated candidate-pool retries
  from direct planner-object alias invalidity.
- The Phase 106 bread-to-refrigerator rerun bound the pickup pool from four
  unrelated candidates to the requested bread alias:
  `candidate_count_before=4`, `requested_present_before=false`,
  `action=injected_requested_candidate_name`, `candidate_count_after=1`.
- The rerun still ended `blocked_capability`, but now with a direct `KeyError`
  for invalid planner object name rather than 17 grasp failures and 15
  ineffective removal calls.
- This does not make a proof planner-backed and does not promote cleanup
  primitive binding. It narrows the next blocker to proof candidate source /
  runtime object alias validity.
- The exact-task behavior remains localized in one adapter seam instead of
  spreading pickup, target, report, and checker logic across multiple
  implementations.

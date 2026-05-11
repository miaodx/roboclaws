# 0101. Classify Missing Grasp Cache Signatures

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0100 made upstream grasp-load diagnostics visible and the Phase 109
valid-scene rerun classified the exact bread blocker as missing cached grasps
for `Bread_1`.

The proof-result summary still treated that as a generic `grasp_feasibility`
pattern. That is too coarse for the broader cleanup plan: selection memory and
reports need to distinguish missing grasp-cache failures from zero
collision-free grasps and from generic post-placement candidate rejection.

## Decision

Keep the top-level task-feasibility blocker kind as `grasp_feasibility`, but
add a machine-readable signature subkind.

`grasp_feasibility_signature` now records:

- `subkind`, including `grasp_cache_missing`;
- grasp-load attempt/failure counts;
- grasp collision check counts;
- zero non-colliding grasp check counts;
- asset UIDs and exception types from failed grasp-load attempts.

The human summary appends missing-cache detail, for example:

`3 grasp failures; 1 candidate-removal calls; 3 grasp-load failures; missing grasp cache: Bread_1`

The shared proof-bundle signature matrix renders the subkind, grasp-load
failures, collision checks, zero non-colliding checks, and missing asset UIDs.

## Consequences

- Future selection/reporting can separate missing asset data from true
  collision-mask infeasibility.
- Existing selection rules that filter `grasp_feasibility` continue to work.
- The next mitigation can target grasp-cache availability or source rotation
  without losing the broader grasp-feasibility category.

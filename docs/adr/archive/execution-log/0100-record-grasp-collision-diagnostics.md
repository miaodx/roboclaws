# 0100. Record Grasp Collision Diagnostics

Date: 2026-05-10

## Status

Accepted

## Context

Phase 108 preserved exact pickup retry semantics and proved the requested
bread alias reaches upstream's grasp-failure threshold path. The remaining
blocker was still too coarse: the report showed three post-placement grasp
failures and one effective candidate removal, but did not say whether the
upstream sampler failed because cached grasps were missing, because collision
checking found zero non-colliding grasps, or because a lower-level collision
check raised.

The exact-scene proof should not move forward until this distinction is visible
in the shared report underlay.

## Decision

Add probe-local grasp collision diagnostics around upstream MolmoSpaces grasp
checks.

The task-sampler diagnostics adapter now wraps the upstream
`load_grasps_for_object` and `get_noncolliding_grasp_mask` globals used by the
pick task sampler. It records:

- asset UID and pickup object alias;
- requested and cached grasp counts;
- gripper type when load succeeds;
- total grasp poses passed into collision checking;
- non-colliding and colliding grasp counts;
- whether a collision check returned zero non-colliding grasps;
- exception type and message when either hook raises.

The shared planner report renders a dedicated Grasp Collision Diagnostics
section, and proof-bundle result cards expose the same summary fields.

## Consequences

- Post-placement grasp failures are now explainable as missing cached grasps,
  zero collision-free grasps, or hook exceptions.
- The Phase 109 valid-scene rerun classified the exact bread blocker as missing
  cached grasps: `load_grasps_for_object("Bread_1", 512)` raised
  `ValueError` three times before collision masking was reached.
- The diagnostics remain probe-local and do not change the upstream sampler's
  success criteria.
- A future mitigation can be chosen from evidence instead of guessing between
  grasp-cache, object pose, collision-body, or robot placement causes.

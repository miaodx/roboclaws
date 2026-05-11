# 0019. Gate RBY1M CuRobo Runtime Before Cleanup Primitive Replacement

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0016 produced a strict standalone Franka planner proof, ADR-0017 attached
that proof to cleanup reports, and ADR-0018 added a per-subphase cleanup
primitive gate. The target visible cleanup embodiment is still RBY1M, and the
known RBY1M planner blocker is CuRobo availability.

Without a dedicated RBY1M/CuRobo runtime gate, a future artifact could satisfy
"planner-backed" with Franka proof while still being unable to run the target
RBY1M cleanup primitive path.

## Decision

Add an explicit RBY1M/CuRobo gate to planner probe artifacts and checkers.

The gate should:

- summarize the probe embodiment, probe mode, execution attempt, planner-backed
  status, and CuRobo module availability;
- accept explicit blocked-capability evidence when CuRobo is missing;
- reject Franka planner proof as evidence for RBY1M/CuRobo readiness;
- require `embodiment=rby1m`, `curobo.available=true`, execution attempted,
  planner-backed provenance, and no blockers before cleanup primitive
  replacement can depend on the RBY1M planner path;
- render in the shared planner probe report.

## Consequences

- Planner-backed cleanup primitive replacement gets a concrete target-runtime
  precondition.
- Current local artifacts remain honest: Franka strict proof is useful planner
  evidence, but not RBY1M/CuRobo readiness.
- This ADR does not install CuRobo or claim RBY1M planner execution.

# 0031. Add Probe-Backed Cleanup Primitive Executor Adapter

Date: 2026-05-09

## Status

Accepted

## Context

Phase 38 added the strict planner-backed cleanup primitive executor seam, and
Phase 39 made the cleanup primitive gate require object/target binding. The
remaining wiring risk is that an attached standalone RBY1M/CuRobo proof could
still be converted into executor evidence without proving it belongs to the
cleanup subphase.

Current target proof from Phase 35 is strict RBY1M/CuRobo execute evidence, but
it is generic sampled upstream task evidence. It does not name the ADR-0003
observed object handle, target fixture, or semantic subphase.

## Decision

Add a probe-backed cleanup primitive executor adapter that consumes planner
proof attachments but fails closed unless the proof carries an explicit cleanup
primitive binding.

The adapter should:

- implement the Phase 38 `CleanupPrimitiveExecutor` callable shape;
- require strict target RBY1M/CuRobo execute proof;
- require binding fields for the exact object id, target receptacle id when
  target-side, and tool/subphase;
- return `planner_backed` only when proof and binding match the request;
- return `blocked_capability` for generic standalone proof.

## Consequences

- Future real RBY1M/CuRobo probe output has a clear artifact contract to satisfy
  before it can drive cleanup-loop provenance.
- Existing generic proof remains useful as target runtime readiness, but cannot
  be reused as object-specific executor evidence.
- The next implementation gap becomes producing a real bound probe from the same
  cleanup object and target fixture.

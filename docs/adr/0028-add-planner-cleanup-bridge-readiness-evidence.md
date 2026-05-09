# 0028. Add Planner Cleanup Bridge Readiness Evidence

Date: 2026-05-09

## Status

Accepted

## Context

Phase 35 proved a strict standalone RBY1M/CuRobo manipulation probe can execute
with nonzero robot-state movement. Phase 36 put the current-contract and
ADR-0003 cleanup demos behind one shared semantic cleanup loop.

Those two facts are necessary for planner-backed cleanup primitive replacement,
but they are still not sufficient. The target runtime proof is standalone, and
the ADR-0003 cleanup subphases still report `primitive_provenance=api_semantic`.

Without an explicit bridge-readiness artifact, a reviewer has to mentally join
three panels:

- the attached planner proof;
- the RBY1M/CuRobo runtime state inside that proof;
- the cleanup primitive gate showing current subphase provenance.

That creates another ambiguity gap right before actual primitive replacement.

## Decision

Add a `planner_cleanup_bridge_evidence` block to ADR-0003 cleanup artifacts
when a planner proof is attached.

The bridge evidence should:

- require a strict attached planner proof;
- distinguish target-runtime readiness from cleanup-subphase execution;
- treat RBY1M/CuRobo proof as target-ready only when the attached proof is for
  `embodiment=rby1m`, `probe_mode=execute`, planner-backed, and CuRobo is
  available;
- reuse `cleanup_primitive_evidence` to decide whether cleanup subphases are
  planner-backed;
- render a report panel that lists blockers when the bridge is not ready;
- add checker support for both explicit blocked bridge evidence and future
  strict bridge readiness.

## Consequences

- A report can now say "target runtime is ready, cleanup primitive bridge is
  still blocked" without relying on reviewer inference.
- Standalone target proof is still not enough to satisfy the cleanup primitive
  gate.
- The future primitive replacement phase has a concrete bridge-readiness gate:
  target RBY1M/CuRobo proof plus all cleanup subphases
  `primitive_provenance=planner_backed`.

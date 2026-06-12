# 0030. Bind Planner Primitive Evidence to Cleanup Targets

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0029 added a strict planner-backed cleanup primitive executor seam. The
executor evidence is per tool call, but the cleanup primitive gate still needs
to prove that evidence belongs to the same cleanup object and target fixture
shown in the semantic subphase row.

Without this binding, a generic planner-backed result for the right tool name
could be attached to an unrelated object or receptacle and still appear strict.
That would recreate the standalone-proof problem at a smaller granularity.

## Decision

Require planner primitive evidence to match the cleanup semantic row before a
subphase becomes strict-ready.

The cleanup primitive gate should validate:

- `planner_primitive_evidence.object_id` matches the semantic substep object;
- target-side subphases match the semantic target receptacle;
- tool name, provenance, strict flags, and nonempty per-call payload still pass;
- mismatches create explicit blockers instead of silently passing.

## Consequences

- The executor seam becomes object-specific, not just tool-specific.
- Future RBY1M/CuRobo executor code must provide evidence for the exact cleanup
  request it executed.
- Current artifacts remain blocked until they carry both planner-backed
  execution and object/target-bound evidence.

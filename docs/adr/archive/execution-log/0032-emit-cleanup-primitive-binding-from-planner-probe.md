# 0032. Emit Cleanup Primitive Binding from Planner Probe

Date: 2026-05-09

## Status

Accepted

## Context

Phase 40 added a probe-backed cleanup primitive executor adapter. It correctly
rejects generic standalone planner proof unless the proof attachment carries
cleanup primitive binding.

The remaining artifact gap is at the probe source: the RBY1M/CuRobo probe
currently records strict target runtime execution, but not which sampled pickup
object and place receptacle the upstream task used, and not whether those names
match a requested cleanup primitive.

## Decision

Teach the planner probe to emit sampled task binding diagnostics and promote
cleanup primitive binding only when the requested cleanup object, target, and
tools match the sampled task.

The probe should:

- accept optional requested cleanup object, target, source, and tool fields;
- record sampled upstream pickup and place target names;
- emit `cleanup_primitive_binding` only on exact request/sample match;
- emit blockers when a request is present but does not match the sampled task;
- keep generic probe runs unchanged as target runtime proof only.

## Consequences

- Future real executor attempts can produce the binding required by Phase 40.
- A generic sampled proof still cannot become cleanup primitive evidence.
- Mismatches become visible in probe artifacts before any cleanup report tries
  to consume them.

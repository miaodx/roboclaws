# 0034. Use Probe-Backed Executor for Bounded Cleanup Loop

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0033 split ADR-0003 observed-handle cleanup IDs from planner-facing sampled
task aliases. The cleanup loop can now produce proof binding that both matches
the upstream sampled planner task and still names the observed handle used by
the shared semantic cleanup loop.

The remaining integration gap is execution path wiring. Cleanup reports can
attach strict RBY1M/CuRobo proof and can display readiness gates, but the
ADR-0003 cleanup subphases still call the normal semantic contract directly.

## Decision

Add an opt-in bounded planner cleanup executor path to the ADR-0003 cleanup
harness.

When a strict planner proof attachment carries cleanup primitive binding that
matches the currently observed cleanup object and target fixture, the shared
semantic cleanup loop may wrap the public cleanup contract with the
probe-backed planner executor for that object. The wrapper still performs the
existing semantic state sync after the executor succeeds, but the emitted
subphase provenance becomes `planner_backed` with executor evidence.

The default harness path remains unchanged. Generic or mismatched proof must not
block normal cleanup, and must not relabel subphases.

## Consequences

- A bounded ADR-0003 cleanup attempt can show actual planner-backed subphase
  provenance in the existing report visual core.
- The cleanup primitive gate can pass for a matching bounded attempt.
- Full multi-object cleanup replacement remains a follow-up until proof can be
  produced for every cleaned object/subphase.

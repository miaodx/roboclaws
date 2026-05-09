# 0022. Capture RBY1M CuRobo Warmup Readiness

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0019 added a target-runtime gate for RBY1M/CuRobo before Roboclaws can
replace cleanup-loop primitives with planner-backed execution. The current
local artifact proves CuRobo is importable with CUDA Torch, but the probe times
out during CuRobo CUDA-extension JIT/config import before planner execution is
attempted.

That is not enough evidence for the next implementation step. A timeout with
stderr compile lines tells us the broad area, but it does not expose the probe
stage, elapsed time, or whether a longer warmup can reach config import and
then execute mode.

## Decision

Add a dedicated RBY1M/CuRobo warmup-readiness slice before planner-backed
cleanup primitive replacement.

The planner probe should emit staged worker events around RBY1M config import,
config construction, policy-class discovery, and execute-mode task/policy
startup. Timeout artifacts should preserve the last emitted stage so the report
and checker can distinguish:

- dependency unavailable;
- CUDA extension JIT/config import still warming;
- config import complete but execution not attempted;
- execution attempted but not planner-backed;
- strict RBY1M/CuRobo readiness.

This phase may rerun the local RBY1M probe with a longer timeout to let CuRobo
JIT finish. It must not claim cleanup primitive replacement unless execute mode
produces strict planner-backed RBY1M evidence.

## Consequences

- A long first-time CuRobo JIT warmup becomes explicit evidence instead of a
  vague timeout.
- If warmup succeeds, the next gate can attempt execute mode with the target
  RBY1M runtime.
- If warmup still times out, the blocked artifact identifies the exact stage
  and remains acceptable only in explicit blocked-capability mode.
- Cleanup reports continue to label cleanup-loop primitives as `api_semantic`
  until the RBY1M/CuRobo execution gate passes and a later phase replaces the
  primitives.

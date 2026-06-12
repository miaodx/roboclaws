# 0018. Gate Planner-Backed Cleanup Primitives Per Cleanup Subphase

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0014 created the strict planner-backed manipulation proof gate, ADR-0016
made the standalone Franka proof pass, and ADR-0017 rendered that proof inside
ADR-0003 cleanup reports. The cleanup loop itself still performs `nav, pick,
nav, open?, place` through semantic MuJoCo state edits labeled `api_semantic`.

The next cleanup integration needs a stricter target than "the report contains
a standalone proof." Each cleanup subphase that claims planner-backed execution
must carry its own primitive evidence. Otherwise an artifact could blend a
passing standalone proof with semantic cleanup state edits and appear more
robotic than it is.

## Decision

Add a planner-backed cleanup primitive gate before replacing cleanup primitives.

The gate should:

- summarize cleanup subphases by object as `nav, pick, nav, open?, place`;
- record per-subphase primitive provenance in a dedicated
  `cleanup_primitive_evidence` block;
- reject `api_semantic` as planner-backed cleanup primitive evidence;
- provide a checker flag that requires all manipulation subphases to be
  `planner_backed`;
- render the gate in the shared Cleanup Artifact Report so reviewers can see
  which subphases are still semantic;
- allow blocked-capability evidence when the local runtime cannot satisfy the
  strict gate yet.

## Consequences

- The next real planner-backed cleanup phase has a concrete acceptance target.
- Current ADR-0003 cleanup reports remain honest and visibly fail the strict
  planner-backed cleanup primitive gate.
- RBY1M CuRobo setup, Franka-to-cleanup object mapping, and actual planner
  primitive replacement remain implementation work after the gate exists.

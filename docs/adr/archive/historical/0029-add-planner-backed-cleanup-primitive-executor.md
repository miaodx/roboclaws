# 0029. Add Planner-Backed Cleanup Primitive Executor

Date: 2026-05-09

## Status

Accepted

## Context

Phase 36 consolidated current-contract and ADR-0003 cleanup demos behind one
shared semantic cleanup loop. Phase 37 then joined the strict target
RBY1M/CuRobo proof with cleanup subphase provenance in one bridge-readiness
panel.

The remaining gap is actual primitive replacement. The cleanup loop still calls
contract methods whose implementation mutates semantic MuJoCo state and reports
`primitive_provenance=api_semantic`.

The next implementation seam must be strict enough that future code cannot
accidentally relabel those state edits. Attached standalone planner proof is
not sufficient. Each cleanup subphase needs proof for that exact call:
`navigate_to_object`, `pick`, `navigate_to_receptacle`, `open_receptacle`, and
`place` or `place_inside`.

## Decision

Add a planner-backed cleanup primitive executor seam behind the shared semantic
cleanup loop.

The executor should:

- receive the semantic primitive name, object handle, target fixture, and public
  cleanup context for the exact subphase;
- return per-call execution evidence before a subphase can report
  `primitive_provenance=planner_backed`;
- fail closed in strict mode when no planner result exists;
- keep semantic state synchronization separate from planner execution evidence;
- leave the default ADR-0003 cleanup path as `api_semantic` until a real
  object-specific MolmoSpaces/RBY1M executor is wired in;
- preserve the shared Cleanup Artifact Report visual core and existing bridge
  panel.

## Consequences

- Future object-specific RBY1M/CuRobo integration has a concrete module seam
  instead of scattering planner calls across demos, MCP servers, or report code.
- Tests can prove that the cleanup primitive gate and planner cleanup bridge
  become strict-ready only when every cleanup subphase carries per-call
  planner-backed evidence.
- Current visual artifacts remain honest: without a real object-specific
  executor, they continue to report `api_semantic` and the bridge remains
  blocked.

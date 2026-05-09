# 0027. Use Shared Semantic Cleanup Loop Driver

Date: 2026-05-09

## Status

Accepted

## Context

The MolmoSpaces cleanup demos now share the Cleanup Artifact Report visual
underlay, but they still execute the object cleanup loop through separate
inline implementations. The current-contract demo and ADR-0003 real-world
harness both manually spell out the same semantic sequence:

`navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? -> place/place_inside`

That duplication is why report artifacts can drift even after the renderer is
shared: robot-view capture, trace request payloads, fridge-open handling, and
future primitive provenance hooks can diverge before the data reaches the
report.

Phase 35 proved a standalone RBY1M/CuRobo target manipulation can execute with
planner-backed provenance under a visible low-memory profile. The next cleanup
architecture step needs one execution seam for the semantic cleanup loop before
planner-backed primitive implementations are attached to it.

## Decision

Add a shared semantic cleanup loop driver in `roboclaws/molmo_cleanup/` and
route MolmoSpaces cleanup demos through it.

The driver should:

- execute the canonical object sequence `nav, pick, nav, open?, place`;
- keep `object_done` optional so current-contract artifacts can keep their
  readback step while ADR-0003 real-world artifacts keep the stricter public
  loop;
- expose a per-tool callback for trace and robot-view capture;
- reuse the shared semantic subphase labels and robot-view capture metadata;
- leave primitive provenance untouched, so current cleanup-loop primitives stay
  `api_semantic` until a real planner-backed primitive bridge executes them.

## Consequences

- Current-contract and ADR-0003 MolmoSpaces demos share the same cleanup-loop
  execution architecture instead of copying semantic subphase code.
- Future planner-backed primitive replacement has one insertion point for
  `navigate`, `pick`, `open`, and `place` implementations.
- The report visual core remains a downstream renderer concern; the execution
  loop no longer has multiple places that can create incompatible semantic
  timelines.
- Strict planner-backed cleanup gates remain honest: reuse does not satisfy the
  gate without per-subphase `primitive_provenance=planner_backed` evidence.

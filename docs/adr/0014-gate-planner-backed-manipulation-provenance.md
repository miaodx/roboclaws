# 0014. Gate Planner-Backed Manipulation Provenance

Date: 2026-05-09

## Status

Accepted

## Context

The MolmoSpaces cleanup demos now share one report underlay and a consistent
semantic loop: `nav -> pick -> nav -> open? -> place`. Those demos still execute
cleanup effects through `api_semantic` primitives. In the real MolmoSpaces
subprocess backend, pick/place/open are currently implemented as semantic state
changes and MuJoCo joint edits, not as RBY1M/Franka planner-backed manipulation
rollouts.

The broader context deliberately deferred low-level planner-backed manipulation
until the cleanup contract, visual reports, and provenance labels were stable.
The local MolmoSpaces checkout contains planner policy classes, but a usable
planner-backed proof requires evidence that a planner policy actually executed
robot actions and changed robot state. Importing a planner class is not enough,
and an `api_semantic` cleanup success must never be relabeled as real
manipulation.

## Decision

Add a dedicated planner-backed manipulation evidence gate:

- Keep existing cleanup primitives labeled `api_semantic`.
- Add a shared manipulation-provenance payload to cleanup artifacts and reports.
- Add a separate planner manipulation probe artifact with its own report section
  that reuses the same Molmo cleanup report underlay styling.
- Treat planner API availability, blocked capability, and actual planner-backed
  execution as separate states.
- Require a checker flag for actual planner-backed proof. A passing proof must
  show planner policy execution, nonzero robot-state movement, no
  `api_semantic` state-edit fallback, and no capability blockers.
- Allow blocked-capability artifacts as honest evidence while the local
  MolmoSpaces runtime lacks required planner dependencies or crashes during
  execution.

## Consequences

- Existing ADR-0003 cleanup gates continue to prove decision/search/report
  behavior, not real manipulation.
- Future RBY1M/Franka planner work has a concrete artifact schema and checker
  target before implementation starts.
- Reports make the current manipulation boundary visible instead of burying it
  in trace logs.
- A future phase can replace blocked-capability evidence with a real
  planner-backed proof without changing the cleanup report architecture.

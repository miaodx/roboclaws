---
refactor_scope: actionable-semantic-map-snapshot
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: null
---

# Refactor Scope: Actionable Semantic Map Snapshot

## Status

CONTINUE

## Target

Define one canonical semantic-map-build completion artifact that both online
build runs and offline/prebuilt semantic-memory conversion can produce.

The target shape is:

```text
Minimal Navigation Map Artifact
  -> semantic-map-build
  -> Actionable Semantic Map Snapshot
  -> household-cleanup / open household tasks

Agibot navigation_memory.json
  -> conversion skill
  -> Actionable Semantic Map Snapshot
  -> household-cleanup / open household tasks
```

The snapshot should preserve the current Runtime Metric Map safety boundary
while also carrying enough materialized navigation and fixture/receptacle
targets for downstream tools to consume it directly.

## Accepted Severities

- P0: Any private scoring truth, generated mess truth, or hidden acceptable
  destination data leaked into agent-facing semantic-map artifacts.
- P1: Online semantic-map-build output and offline converted semantic memory
  cannot be consumed through the same canonical artifact contract.
- P1: A semantic target is visible in Agent View but cannot be materialized as a
  valid navigation waypoint or fixture/receptacle target when its status says it
  is actionable.
- P2: Naming, documentation, test, or adapter drift that makes future agents
  rediscover the difference between visible semantic anchors and tool-valid
  registered targets.

## Accepted Cleanup Checklist

- [ ] Define the canonical **Actionable Semantic Map Snapshot** contract:
      source navigation-map reference, `runtime_metric_map_v1`, public semantic
      anchors, materialized inspection waypoints, materialized
      fixture/receptacle candidates, affordances, reachability/actionability
      status, and evidence/provenance.
- [ ] Make the contract explicit that online `semantic-map-build` output and
      offline `navigation_memory.json` conversion produce the same downstream
      artifact shape. Only provenance should differ.
- [ ] Add a conversion boundary for
      `vendors/agibot_sdk/artifacts/maps/*/navigation_memory.json` that can be
      owned by a skill: deterministic scripts perform file parsing, map-frame
      checks, and scaffold generation; an agent supplies semantic
      classification such as anchor type, affordances, object-vs-fixture, and
      review status.
- [ ] Add contract tests proving a converted Agibot navigation-memory artifact
      can be loaded as the same semantic-map snapshot shape expected from an
      online build result.
- [ ] Add contract tests proving cleanup/open-task consumers can materialize
      actionable anchors as valid navigation waypoints and fixture/receptacle
      targets without reading private truth.
- [ ] Preserve existing Runtime Metric Map prior safety for movable objects:
      observed-object priors remain `needs_confirm` until current-run evidence
      confirms them.
- [ ] Update human/agent docs only where they describe the map artifact
      boundary: Minimal Navigation Map Artifact, Runtime Metric Map, Public
      Semantic Anchor, Prebuilt Robot Map Bundle, and semantic-map-build output.

## Parked Cross-Seam / Future Ideas

- Full room-wide semantic annotation is out of scope; the first conversion may
  use only the semantic entries already present in `navigation_memory.json`.
- Real Agibot GDK, OpenClaw Gateway, VLM, and physical robot validation are out
  of scope for the first contract slice.
- Cleanup policy strategy changes are out of scope. The goal is to make the
  world artifact consumable, not to redesign object-selection behavior.
- Persistent source-map mutation remains out of scope. The snapshot is a
  derived, reviewable artifact; it is not a silent rewrite of the original
  source map.
- A polished public skill UX for semantic labeling can follow after the
  contract and core conversion proof are stable.

## Evidence Ladder

- L0 Static: `ruff check` for touched Python modules and tests.
- L1 Unit/mock: unit tests for deterministic conversion helpers, map-frame
  projection, reachability status assignment, and affordance normalization.
- L2 Contract: contract tests for snapshot schema, no-private-truth guarantees,
  online/offline artifact equivalence, and cleanup consumer materialization.
- L3 Mock regression: one mock or smoke cleanup/open-task run consuming the
  converted snapshot through the same path used for online build output.
- L4+ Local-only gates are optional follow-up evidence for real Agibot/OpenClaw
  runs and should not block the first contract slice unless explicitly requested.

## Stop Condition

Stop when all accepted P0/P1/P2 checklist items inside this target are either
implemented and verified through L2 contract tests, or explicitly parked with a
reason. The final state must let future agents state one rule:

```text
Online semantic-map-build output and offline converted navigation_memory output
produce the same Actionable Semantic Map Snapshot contract. Cleanup and open
household tasks consume that contract through one path.
```

Do not start broad cleanup, policy redesign, full map annotation, or local
hardware validation under this gate.

## Execution Log

- 2026-06-03: Created scope gate after discussion of
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json`.
  Decision: the prebuilt semantic memory should not be treated as minimal-map
  input. It should convert to the same canonical completion artifact as an
  online semantic-map-build run, with different provenance only.

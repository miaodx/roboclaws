---
plan_scope: b1-map12-semantic-and-public-nav-followups
status: Follow-up plan; not required for P0 digital-twin navigation/render execution
created: 2026-06-18
last_reviewed: 2026-06-18
implementation_allowed: false
source:
  - split non-P0 work out of docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md
  - user decision that P0 should not block on room semantics
  - user decision that B1_floor2_slow visual route belongs in P0 instead of this follow-up
related_context:
  - STATUS.md
  - docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md
  - docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md
  - docs/status/active/b1-map12-semantic-anchor-review-packet.json
  - assets/maps/b1-map12-scene-correspondences.json
---

# B1 / Map 12 Semantic And Public Navigation Follow-ups

## Purpose

This document parks the B1 / Map 12 work that is useful after the P0
digital-twin navigation/render slice, but must not block it.

The P0 execution source is
`docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`. P0 should make
the verified B1 / Map12 asset robot-consumable through explicit runtime-prior /
MCP context and render evidence. P0 may evaluate `B1_floor2_slow` as the
preferred photorealistic visual route, but it does not require human room
semantic review.

## Follow-up P1: Room Semantics

Goal: project accepted B1 room / scene-partition semantics into Map12 only after
human-accepted semantic anchors exist.

Tasks:

- Split promotion gates by anchor role:
  - `anchor_role=alignment` keeps the global geometry gate: at least six
    accepted geometry anchors for global residual fitting.
  - `anchor_role=semantic` is a room-label evidence group appended to an already
    verified alignment manifest. It must not be blocked by the six-point global
    geometry threshold.
- Human-review `docs/status/active/b1-map12-semantic-anchor-review-packet.json`.
  This packet is review input only; it is not accepted truth.
- Promote only human-accepted `anchor_role=semantic` room-interior anchors with
  real `navigation_area_id` and `asset_partition_id`.
- Keep independent per-area transform claims stricter: require at least three
  accepted, non-collinear semantic anchors for that area.
- Run `scripts/maps/build_b1_map12_semantic_projection.py` only after accepted
  semantic anchors exist.
- Consume the verified projection artifact only through an explicit
  `b1_semantic_projection_artifact=...` / `--semantic-projection-artifact`
  input. Do not auto-discover generated `output/**`.

Acceptance:

- Proposed-only packets and alignment-only manifests still fail room semantic
  projection loudly.
- Accepted semantic anchors can enable room semantic projection without
  requiring another global six-point geometry review.
- The projection artifact records the accepted semantic anchors, matching
  `navigation_area_id`, matching `asset_partition_id`, and source review label.

## Follow-up P2: Object Semantics

Goal: add object-level semantic projection only after a separate object-anchor
acceptance contract exists.

Tasks:

- Define object-level anchor schema and review workflow.
- Require object anchors or object evidence directly. Do not infer object labels
  from room semantic anchors.
- Keep object/receptacle USD binding blocked until there is dedicated proof for
  object identity, receptacle identity, and usable manipulation affordances.
- Add tests proving object projection remains blocked from room-only inputs.

Acceptance:

- Object projection cannot be produced from room anchors alone.
- Any projected object labels include provenance, accepted object-level anchors,
  and blocked/ready status for object/receptacle binding.

## Follow-up Public Navigation Contract

Goal: decide whether agents should get a public absolute `map_xy/yaw`
navigation tool.

Current state:

- P0 agent-facing proof stays waypoint-based through the existing MCP surface:
  `metric_map -> navigate_to_waypoint -> observe`.
- Explicit `map_xy/yaw` support exists as an internal pose-request artifact path
  for operator/runtime proof.

Decision needed before implementation:

- If multiple skills or clients need direct absolute map navigation, make a new
  public MCP contract plan for that tool.
- Otherwise keep `map_xy/yaw` as operator/internal artifact support and expose
  agent navigation through public waypoints.

Non-goals:

- Do not add a public MCP tool as part of this follow-up without a new approved
  contract.
- Do not claim planner-backed navigation, physical robot navigation,
  manipulation, or object/receptacle binding from the current P0 proof.

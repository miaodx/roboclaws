# Agibot Robot Map 9 Semantic Actions Rehearsal

**Status:** Accepted intermediate confidence layer
**Created:** 2026-05-21
**Source:** `CONTEXT.md`, `STATUS.md`,
`docs/plans/agibot-robot-map-9-dry-run-rehearsal.md`, and prior
robot_map_9 semantic cleanup discussion
**Workflow:** Pre-GSD plan/context preservation. Keep separate from both the
SDK dry-run report and the MolmoSpaces Agibot contract rehearsal.

## Problem

The `robot_map_9` dry-run report proves the map artifact and SDK runner boundary
are reviewable, but its top-level cleanup report intentionally has no semantic
cleanup actions. Jumping straight from that report to the MolmoSpaces Agibot
contract rehearsal skips a useful middle confidence layer:

- use the real `robot_map_9` map artifact and authored context;
- run Roboclaws semantic cleanup actions over the Agibot-shaped map bundle;
- produce normal cleanup `nav -> pick -> nav -> place/open?` substeps;
- keep the action evidence labeled as semantic/mock, not SDK runner execution
  and not physical Agibot GDK movement.

## Goal

Add a deterministic `robot_map_9` semantic actions rehearsal:

- generate a Nav2-shaped map bundle from
  `vendors/agibot_sdk/artifacts/maps/robot_map_9`;
- run the existing Roboclaws semantic cleanup loop against that map bundle;
- render semantic action substeps in the shared Cleanup Artifact Report;
- preserve the distinction between Agibot map/SDK dry-run evidence, semantic
  cleanup mock evidence, the future MolmoSpaces Agibot contract rehearsal, and
  real Agibot GDK execution.

## Locked Boundary

This layer is:

- **semantic/mock cleanup evidence** over an Agibot-shaped public map bundle;
- useful proof that cleanup planning and report rails can consume `robot_map_9`
  map semantics;
- a bridge between SDK dry-run reports with empty action tabs and the later
  MolmoSpaces-backed contract rehearsal.

This layer is not:

- an SDK runner subphase report;
- an Agibot GDK navigation run;
- a physical robot observation or arrival claim;
- a MolmoSpaces Agibot contract rehearsal;
- a digital twin of the Agibot lab floor.

## Report Requirements

- The report should clearly say **Agibot Robot Map 9 Semantic Actions
  Rehearsal**.
- The report should show semantic cleanup substeps instead of empty action
  state.
- The run result should expose a machine-readable confidence-layer block.
- The map source should remain
  `vendors/agibot_sdk/artifacts/maps/robot_map_9`.
- The backend and primitive provenance should remain `api_semantic_synthetic`
  / `api_semantic`.
- The report should make clear that the next confidence layer is
  `MolmoSpaces Agibot Contract Rehearsal`.

## Acceptance Criteria

- A deterministic local command regenerates the semantic-actions report.
- The report uses `robot_map_9` as the map artifact source.
- The report includes at least one semantic cleanup substep.
- The report does not claim SDK runner execution, `--execute`, physical robot
  movement, or `agibot_gdk_normal_navi` provenance.
- Focused tests prove the confidence-layer fields, semantic substeps, map
  source, and provenance labels.

## Follow-Up

After this layer stays stable, implement the separate
`docs/plans/molmospaces-agibot-contract-rehearsal.md` plan. That later layer
should consume Agibot-shaped runner artifacts and provide simulated
MolmoSpaces-backed `observe` / `navigate_waypoint` evidence, not just semantic
mock cleanup actions.

# Agibot Robot Map 9 Dry-Run Rehearsal

**Status:** Accepted current rehearsal boundary
**Created:** 2026-05-21
**Source:** Agibot integration review, `CONTEXT.md`, `STATUS.md`,
`vendors/agibot_sdk/CONTEXT.md`, and generated report review
**Workflow:** Pre-GSD plan/context preservation. Keep separate from the
MolmoSpaces Agibot contract rehearsal plan.

## Problem

The Agibot integration now has a useful dry-run report over
`vendors/agibot_sdk/artifacts/maps/robot_map_9`, but the name "semantic cleanup
rehearsal" was easy to overread as actual robot action or as the planned
MolmoSpaces-backed Agibot runner contract rehearsal.

That ambiguity matters because the current artifact is valuable but has a
specific proof level:

- it uses a real Agibot map artifact from part of the lab floor;
- it previews rooms, public waypoints, route plausibility, and report shape;
- it does not submit navigation to the GDK;
- it does not move a real robot;
- it is not a MolmoSpaces sim backend driven by Agibot runner semantics.

## Goal

Keep the current `robot_map_9` work as an honest confidence layer before real
Agibot G2 testing:

- use `vendors/agibot_sdk/artifacts/maps/robot_map_9` as the demo map source;
- render the map and authored context in the Agibot integration report;
- keep the report explicit that this is dry-run or rehearsal evidence only;
- preserve the distinction between map visual dry-run, SDK dry-run, semantic
  cleanup mock evidence, and real Agibot GDK execution.

## Locked Boundary

This plan covers the first two confidence layers:

1. **Agibot Map Visual Dry Run**: real Agibot map artifacts are used to preview
   target, waypoint, and route plausibility. No GDK navigation is submitted.
2. **Agibot SDK Dry Run**: the SDK standalone runner is invoked without
   `--execute`, producing SDK-owned agent-view, observe, and navigation-stage
   artifacts. No real robot motion occurs.

It intentionally stops before Roboclaws semantic cleanup evidence over
Agibot-shaped map data. That evidence now lives in
`docs/plans/agibot-robot-map-9-semantic-actions-rehearsal.md` and must stay
labeled as semantic/mock rather than Agibot SDK runner or GDK execution.

## Current Evidence

- Map source:
  `vendors/agibot_sdk/artifacts/maps/robot_map_9`
- Current report:
  `output/agibot/adr0131-robot-map-9-rehearsal/report.html`
- SDK runner stages:
  `agent-view`, `observe`, `navigate-waypoint`
- Public Roboclaws tool mapping:
  `metric_map`, `fixture_hints`, `observe`, `navigate_to_waypoint`

## Non-Goals

- Do not claim `agibot_gdk_normal_navi` execution.
- Do not use `--execute`.
- Do not call real GDK navigation.
- Do not claim physical robot observation or arrival.
- Do not treat `robot_map_9` as a MolmoSpaces digital twin.
- Do not collapse this dry-run layer into the MolmoSpaces Agibot contract
  rehearsal.

## Report Requirements

- The report should show the real `robot_map_9` map artifact and authored
  context clearly.
- Empty tabs should show explicit empty states rather than stale previous
  content.
- The robot/backend section should explain that subphases are SDK runner
  evidence, not normal semantic cleanup substeps.
- Stage labels should map SDK runner actions to public tool semantics:
  `agent_view_export -> metric_map, fixture_hints`,
  `observe -> observe`, and
  `navigate_waypoint -> navigate_to_waypoint`.
- Blocked or dry-run movement should be shown as dry-run blocked, not as failed
  physical execution.

## Acceptance Criteria

- A deterministic local run can regenerate the `robot_map_9` Agibot report.
- The report uses `vendors/agibot_sdk/artifacts/maps/robot_map_9` as its source
  map artifact.
- The report does not imply that robot movement happened.
- The report distinguishes SDK-owned subphase evidence from normal cleanup
  semantic substeps.
- The plan and report both make clear that the missing next layer is
  `Agibot Robot Map 9 Semantic Actions Rehearsal`, not more map dry-run polish.

## Follow-Up

After this layer stays stable, run the separate
`docs/plans/agibot-robot-map-9-semantic-actions-rehearsal.md` layer. After that
semantic/mock layer is stable, implement
`docs/plans/molmospaces-agibot-contract-rehearsal.md` as the extra
pre-real-robot simulation step.

# MolmoSpaces Visual Verification Report

## Problem / Goal

The RBY1M MolmoSpaces cleanup report proves that a real MuJoCo scene is loaded and mutated, but several manipulation steps are hard to inspect visually. In the current report the map has no room boundaries, the FPV/chase images are raw camera frames without target context, and small or occluded targets such as apples, books, shelves, sinks, beds, and pillows can be hard to find.

Goal: make the demo more like the AI2-THOR visual review artifact by adding room boundaries, target focus metadata, and a report-only target verification camera for each manipulation step, while preserving the distinction between robot-visible camera frames and simulator-state report aids.

## Decisions Already Made

- Keep the MolmoSpaces subprocess backend as the real-run path.
- Keep RBY1M as the visual robot for this phase.
- Keep manipulation provenance as `api_semantic` until planner-backed RBY1M/Franka pick/place exists.
- Keep FPV and chase camera frames as honest MuJoCo camera renders.
- Add visual aids only as report artifacts with explicit provenance.

## Non-Goals

- Do not claim planner-backed robotic manipulation.
- Do not use `private_manifest` for planner decisions.
- Do not replace the public cleanup loop with a scripted reference path.
- Do not hand-author static images; all artifacts must come from the run.
- Do not solve full robot navigation or collision-free base planning in this phase.

## Smallest Demo

Run the existing real MolmoSpaces RBY1M cleanup harness and produce:

- `before.png`
- `after.png`
- `trace.jsonl`
- `run_result.json`
- `report.html`
- robot FPV, chase, map, and verification images for each recorded step

For every `goto` and `place` robot timeline step, the report must show the focused object/receptacle metadata, a map with room outlines and target highlights, and a target verification image generated from public simulator state.

## Fuller Demo

The report can become a step-by-step inspection surface:

- Map room borders and room labels.
- Robot path and current pose.
- Highlight rings for the focused object and receptacle.
- FPV and chase camera panels.
- A verification camera panel that makes small or occluded targets inspectable.
- Provenance text that states which panels are robot cameras and which panels are report aids from public MuJoCo state.

## Acceptance Criteria

- `just harness::molmo-robot-visual` runs against a real MolmoSpaces/MuJoCo scene with RBY1M included.
- `just verify::molmo-robot-visual` passes.
- `run_result.json` records `backend=molmospaces_subprocess`.
- `run_result.json` records `planner=public_heuristic` and `planner_uses_private_manifest=false`.
- `run_result.json` records `primitive_provenance=api_semantic`.
- `run_result.json` records `view_variant=molmospaces-rby1m-fpv-map-chase-verify`.
- Every `goto` and `place` robot view step records focus metadata.
- Every focused robot view step writes `fpv`, `chase`, `map`, and `verify` image paths.
- Map images record a positive `room_outline_count`.
- `report.html` includes the robot timeline, focus metadata, map, FPV, chase, and verification panels.

## Proposed Vertical Slices

1. Add focus metadata to robot view capture calls in the public cleanup loop.
2. Add room-outline and focus-highlight rendering to the MolmoSpaces map artifact.
3. Add a target verification camera render with explicit report-aid provenance.
4. Update the HTML report to surface the new visual evidence clearly.
5. Strengthen the checker so fake/non-focused visual runs do not pass the robot visual gate.
6. Run focused tests and the real MolmoSpaces RBY1M harness.

## GSD Handoff Trigger

If the existing harness cannot produce target-focused robot visual artifacts from the real MolmoSpaces subprocess backend, create and execute the next GSD phase before marking the work complete.

## Follow-Up: FPV Orientation And Room Plausibility

Artifact review after the first visual-verification pass found three follow-up issues:

- FPV/chase are real RBY1M camera renders, but FPV can face away from the active target when base orientation is held fixed for readability.
- Some semantic `goto` poses can land on the wrong side of room borders even though placement mutates real MuJoCo state.
- Refrigerator/apple verification needs stronger target visibility than the first top-down context camera provides.

The accepted follow-up is tracked as GSD phase 09:
`.planning/phases/09-molmospaces-fpv-room-plausibility/09-01-target-facing-base-and-room-plausibility-PLAN.md`.

Phase 09 closed the follow-up by making base yaw target-facing, adding
same-room stand-off evidence, pitching the RBY1M head camera for target
framing, and recording segmentation-derived FPV visibility pixels. The final
`just verify::molmo-robot-visual` run passed against the real
`molmospaces_subprocess` backend with `planner=public_heuristic`,
`planner_uses_private_manifest=false`, and 5/5 restored objects.

## Follow-Up: Semantic Cleanup Substeps

Artifact review after Phase 09 found that the visual timeline was readable but
the loop was still too coarse: it jumped from source state to target placement
instead of showing object-side navigation, pick, target-side navigation,
receptacle opening when needed, placement, and object-level completion.

The accepted follow-up is tracked as GSD phase 10:
`.planning/phases/10-molmospaces-semantic-substeps/10-01-semantic-cleanup-substeps-PLAN.md`.

Phase 10 closed the follow-up by recording each cleanup target as:

`navigate_to_object -> pick -> navigate_to_receptacle -> optional open_receptacle -> place/place_inside -> object_done`

The apple/fridge path now opens the real fridge joint, records `place_inside`,
and finishes with public readback showing the apple `inside` the refrigerator
rather than visible outside it. The report now shows semantic phase badges and
suppresses the Verification panel plus zero-pixel visibility badges on
non-focused context rows such as `before`, `observe`, `scene_objects`, and
`after`. The final `just verify::molmo-robot-visual` run passed against
`backend=molmospaces_subprocess`, with
`planner_uses_private_manifest=false`, `primitive_provenance=api_semantic`,
25 robot-view timeline rows, and 5/5 restored objects.

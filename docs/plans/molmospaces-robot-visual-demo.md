# MolmoSpaces Robot Visual Demo Plan

## Problem / Goal

The current MolmoSpaces cleanup proof loads a real upstream MuJoCo scene and
mutates real object state, but it does not include an embodied robot. The report
therefore looks less like the AI2-THOR demos: users cannot see an agent body,
robot-view camera, chase view, or map trail.

Build the smallest real-robot visual extension that makes the MolmoSpaces demo
reviewable like the AI2-THOR `map-v2+chase` path without overstating
manipulation capability.

## Decisions Already Made

- Use the isolated Python 3.11 MolmoSpaces runtime at
  `/tmp/roboclaws-molmospaces-spike/.venv/bin/python`.
- Use the existing real scene path: upstream `procthor-10k-val`, scene index 0.
- Use `RBY1M` as the target robot because it is the best household mobile
  manipulator fit and is already present in the local MolmoSpaces asset cache.
- Keep manipulation provenance as `api_semantic` until RBY1M/Franka
  planner-backed pick/place is proven.
- It is acceptable for this phase to move the RBY1M base by direct MuJoCo qpos
  edits as long as the report labels that as semantic robot-base control, not
  planner-backed navigation.

## Non-Goals

- Do not claim planner-backed pick/place.
- Do not require OpenClaw, VLM keys, Docker, or GPU for this visual proof.
- Do not make the planner read `private_manifest`.
- Do not replace the current cleanup proof; add a more embodied review demo.
- Do not add G1 or custom robot imports.

## Smallest Demo

Run `帮我整理这个房间` through the public cleanup loop against the real
MolmoSpaces scene with RBY1M included in the MuJoCo model. For each meaningful
step, write:

- robot FPV image from the RBY1M/head or robot-pose camera path
- chase image from an RBY1M follower camera
- map image showing robot base trajectory, current pose, target receptacles,
  and selected cleanup objects

The final `report.html` should show before/after images and a readable timeline
of FPV/chase/map frames so a reviewer can see robot position changes.

## Fuller Demo

After this visual proof, add planner-backed RBY1M or Franka pick/place. Only
that later phase may change manipulation provenance from `api_semantic` to
`real`.

## Acceptance Criteria

- A real upstream MolmoSpaces/MuJoCo scene loads in the isolated Python 3.11
  runtime.
- The scene model includes an actual `rby1m` robot body and robot camera names.
- The public cleanup prompt `帮我整理这个房间` runs through the public cleanup
  tool loop.
- The planner does not read `private_manifest`; it remains scorer-only.
- The run writes `before.png`, `after.png`, `trace.jsonl`, `run_result.json`,
  and one reviewable `report.html`.
- The run writes per-step FPV/chase/map images and records them in
  `run_result.json`.
- `run_result.json` records `backend=molmospaces_subprocess`,
  `robot_name=rby1m`, and robot model stats that prove the robot-augmented model
  loaded.
- Robot movement records direct MuJoCo qpos changes for RBY1M base pose and is
  labeled as semantic robot-base control, not planner-backed navigation.
- Manipulation remains `primitive_provenance=api_semantic`.
- A harness/verify gate produces the final nice HTML under `output/`.

## Proposed Vertical Slices

1. Add RBY1M scene inclusion support to the MolmoSpaces subprocess worker.
2. Add robot base pose movement on cleanup `goto` when robot inclusion is
   enabled.
3. Add FPV/chase/map rendering and artifact provenance.
4. Add a demo runner and HTML report timeline.
5. Add focused tests plus a real harness/verify recipe.

## GSD Handoff Trigger

This plan is approved for direct execution when the user asks to "do this" and
finish with a working HTML artifact.

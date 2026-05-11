# Phase 11 Plan 01 Summary - Held-Object Carry Visuals

Completed on 2026-05-08.

## What Changed

- Added a real MuJoCo held-object sync helper in
  `scripts/molmospaces_subprocess_worker.py`.
- `navigate_to_receptacle` now updates the held object's free-joint qpos after
  moving RBY1M, so carried objects visually follow the robot instead of staying
  at the pickup pose.
- `open_receptacle` now also syncs the held object after moving RBY1M to the
  opened-fridge access pose.
- Tool responses disclose the extra mutation with
  `held_object_freejoint_qpos` in `state_mutation` and include
  `held_object_pose`.
- The visual checker now requires carried-object FPV pixels on
  `navigate_to_receptacle` rows and verifies the object is at the expected
  robot-relative held pose.
- Fridge held-object focus now keeps verification centered on the receptacle so
  open/place rows remain readable.

## Verification

See `11-VERIFICATION.md`.

Key final evidence:

- `just verify::molmo-robot-visual` passed.
- Latest real visual output: `output/molmo-robot-visual-harness/report.html`
- Latest real visual run result:
  `output/molmo-robot-visual-harness/run_result.json`
- All five carried `navigate_to_receptacle` rows have positive FPV object
  pixels and robot-relative position error <= `0.000001`.

## Boundaries

- The backend remains real MolmoSpaces/MuJoCo through
  `molmospaces_subprocess`.
- Primitive provenance remains `api_semantic`, because the phase mutates real
  MuJoCo scene state but does not prove planner-backed RBY1M/Franka
  manipulation.
- `primitive_provenance=real` remains deferred until an actual robot
  manipulation planner controls pick/place.
- The planner is still deterministic `public_heuristic`, not a real
  VLM/OpenClaw policy.

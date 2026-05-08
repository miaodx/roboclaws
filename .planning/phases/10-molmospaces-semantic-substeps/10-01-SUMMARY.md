# Phase 10 Plan 01 Summary - Semantic Cleanup Substeps

Completed on 2026-05-08.

## What Changed

- Added public cleanup tools for `navigate_to_object`, `navigate_to_receptacle`, `open_receptacle`, `place_inside`, and `object_done`.
- Replaced the coarse cleanup loop with object-level semantic substeps:
  `navigate_to_object -> pick -> navigate_to_receptacle -> optional open_receptacle -> place/place_inside -> object_done`.
- Implemented real MuJoCo state mutation for held-object pickup pose, articulated fridge opening, and fridge containment placement.
- Added `semantic_substeps`, `semantic_loop_variant`, and `final_containment` to `run_result.json`.
- Updated the robot visual report to show semantic phase badges and to suppress the Verification panel for non-focused bootstrap rows.
- Tightened the harness checker so the real robot visual gate requires semantic substeps, public planner use, same-room robot poses, and apple fridge containment.
- Adjusted tiny `RemoteControl` placement height in the real scene so the robot-view demo does not select a target hidden inside desk clutter.

## Verification

See `10-VERIFICATION.md`.

Key final evidence:

- `just harness::molmo-real-cleanup` passed.
- `just verify::molmo-robot-visual` passed.
- Latest real visual output: `output/molmo-robot-visual-harness/report.html`
- Latest real visual run result: `output/molmo-robot-visual-harness/run_result.json`

## Boundaries

- The backend is real MolmoSpaces/MuJoCo through `molmospaces_subprocess`.
- Primitive provenance remains `api_semantic`, because the phase mutates real MuJoCo scene state but does not prove planner-backed RBY1M/Franka manipulation.
- `primitive_provenance=real` remains deferred until an actual robot manipulation planner controls pick/place.
- The planner is still deterministic `public_heuristic`, not a real VLM/OpenClaw policy.

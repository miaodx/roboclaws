# Phase 09 Context - MolmoSpaces FPV Room Plausibility

## Source Feedback

The RBY1M visual cleanup report is now useful enough to inspect the run, but the latest artifact review found three remaining issues:

- FPV frames can point away from the active target because the robot base orientation was fixed for review readability.
- The sink step placed the robot on the wrong side of a room boundary, making the semantic `goto` visually implausible even though the MuJoCo state mutation succeeded.
- The refrigerator/apple verification view is less clear than shelf/book, sink/bowl, and bed/pillow steps.

## Existing Boundaries

- Backend remains the real `molmospaces_subprocess` path.
- The public cleanup planner must not read `private_manifest`.
- Primitive provenance remains `api_semantic`; this phase improves visual and physical-plausibility evidence, not planner-backed robot manipulation.
- FPV/chase remain real RBY1M MuJoCo cameras.
- Map/verification panels remain report aids from public MuJoCo state.

## Prior Evidence

- Commit `fbae87c` added room outlines, focus metadata, verification panels, and a stricter robot-view gate.
- `just verify::molmo-robot-visual` passed after that commit.
- Artifact review showed step 6/7 verification can see shelf/book and step 8/9, 10/11 can see sink/bowl and bed/pillow, but FPV orientation and fridge/apple clarity still need work.

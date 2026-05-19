# Phase 09 Plan 01 Summary - Target-Facing Base And Room Plausibility

## Outcome

Implemented the MolmoSpaces visual follow-up requested after artifact review.
The robot now turns its base toward the target receptacle for semantic `goto`
steps, selects same-room stand-off candidates from MuJoCo room outlines, pitches
the RBY1M head camera to frame close low targets, and records both FPV and
verification visibility evidence in `run_result.json` and `report.html`.

## Changes

- `scripts/molmospaces_subprocess_worker.py`
  - Sets `robot_0/base_theta` from target-bearing yaw and records
    `theta_source=target_facing_base_yaw`.
  - Chooses target stand-off poses that are inside the target room outline when
    possible and records room relation metadata.
  - Sets RBY1M head pitch from public target geometry for FPV framing while
    leaving yaw to the base; records `head_pitch_source` separately.
  - Renders segmentation visibility for the real head camera and the
    report-only verification camera.
  - Makes apple/fridge placement visually inspectable by placing the apple in a
    visible fridge-adjacent position.
- `roboclaws/molmo_cleanup/report.py`
  - Surfaces base yaw, head pitch, room relation, FPV visibility, and
    verification visibility evidence in the robot timeline.
- `scripts/check_molmospaces_cleanup_result.py`
  - Requires target-facing base yaw, target-framing head pitch, same-room
    focused steps, positive FPV target pixels, verification boxes, and apple
    place object pixels.
- `tests/test_molmo_cleanup_report.py`
  - Covers the new report evidence badges.
- `docs/retrospectives/plans/molmospaces-visual-verification-report.md`
  - Records the phase 09 follow-up and its closed status.

## Verification

Passed:

```bash
.venv/bin/ruff format --check scripts/molmospaces_subprocess_worker.py roboclaws/molmo_cleanup/report.py scripts/check_molmospaces_cleanup_result.py tests/test_molmo_cleanup_report.py
.venv/bin/ruff check scripts/molmospaces_subprocess_worker.py roboclaws/molmo_cleanup/report.py scripts/check_molmospaces_cleanup_result.py tests/test_molmo_cleanup_report.py
./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_report.py
just harness::molmo-robot-visual
just verify::molmo-robot-visual
```

Final real harness evidence is in
`output/molmo-robot-visual-harness/run_result.json` and
`output/molmo-robot-visual-harness/report.html`.

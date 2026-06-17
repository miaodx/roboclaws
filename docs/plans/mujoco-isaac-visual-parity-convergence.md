# MuJoCo Isaac Visual Parity Convergence

**Status:** Superseded by
[`2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md`](2026-06-15-separate-digital-twin-isaac-from-molmospaces-mainline.md)
and ADR-0142. This file is historical MolmoSpaces Isaac visual-parity planning,
not a current execution contract.
**Created:** 2026-06-03
**Source:** MuJoCo/Isaac FPV, chase camera, object-state, and Isaac exposure
discussion after `seed=6`/`0008` visual review.
**Historical workflow:** Pre-GSD plan superseded before current execution. Use
[`mujoco-isaac-object-render-parity-audit.md`](mujoco-isaac-object-render-parity-audit.md)
only as historical object/render audit context.

## Context

The immediate FPV issue is mostly resolved: both backends should use the
robot-mounted head camera for policy/input evidence. The chase camera remains
auxiliary report evidence from behind and above the robot, not an input camera.

The remaining problem is broader. Isaac can still look materially different
from MuJoCo even when camera pose is correct, because the two paths differ in
USD/MJCF asset import, renderable geometry, articulated visual state, material
conversion, lighting, shadows, tone mapping, exposure, and report-side color
comparison profiles. The box open/closed mismatch is the concrete example, but
the engineering question is whether other categories can fail in the same way.

## Goal

Make MuJoCo and Isaac comparable enough that visual reports support honest
apple-to-apple review for:

- `semantic-map-build` and `household-cleanup`;
- `world-labels`, `world-labels-sanitized`, `camera-labels`, and `camera-raw`
  evidence lanes where applicable;
- robot FPV/head-camera input evidence and chase/snapshot report evidence;
- at least the current `procthor-10k-val` slices plus held-out scenes before
  promoting new defaults.

The desired claim is conservative: audited scenes/categories are comparable
within documented gates. Do not claim every future MolmoSpaces scene is
identical until corpus evidence proves it.

## Non-Goals

- Do not replace the FPV contract with an external scene camera.
- Do not make chase camera a policy/input view.
- Do not hide object mismatches with post-render color compensation.
- Do not add one-off per-object hacks unless they are temporary diagnostics
  clearly marked for removal.
- Do not promote native Isaac exposure/tone changes without held-out FPV and
  chase evidence.
- Do not change cleanup public defaults before reports can explain the
  resulting visual differences.

## Decisions

### Camera Contract

- FPV means robot-mounted head camera in both backends.
- MuJoCo camera discovery should report all `robot_0` cameras and explicitly
  identify the selected head camera.
- Isaac should bind the equivalent robot head camera prim and record the prim
  path.
- Chase camera remains robot-relative rear/high report evidence. It should
  contain the real imported robot, not a fake proxy unless the report labels it
  as synthetic.

### Object Contract

Treat object parity as a gate before render residuals:

- First decide whether each selected object is bound, renderable, posed, and in
  the same visual/articulated state in both backends.
- Only comparable objects may contribute to aggregate RGB/tone/residual
  conclusions.
- The current box fix should be treated as category-level evidence backed by
  the prepared-USD visual-physics freeze, not as proof that every other object
  category is safe.
- New category contracts should be added only when corpus evidence shows a
  repeated risk, such as drawers, doors, lids, appliances, or other articulated
  receptacles.

### Isaac Exposure Contract

- Report-side RGB/gain/tone profiles are comparison diagnostics, not native
  Isaac renderer settings.
- Isaac native render diagnostics must record RTX/camera settings before
  brightness differences are interpreted.
- Auto exposure should be logged and usually disabled for deterministic
  apple-to-apple probes unless it is the explicit variable under test.
- A fixed native exposure/tone preset can become a default candidate only after
  held-out slices improve without creating chase regressions.

## Execution Plan

### Phase 1: Stabilize Evidence Surfaces

Use existing reports, do not create a new runnable task yet.

- Robot-camera apple-to-apple report:
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- Visual parity summary:
  `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- Scene-camera comparison:
  `roboclaws/household/scene_camera_comparison.py`
- Isaac worker diagnostics:
  `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`

Acceptance:

- Reports embed image pairs, not just links, for direct visual review.
- Camera provenance is visible for FPV, chase, snapshot, and scene-camera
  views.
- Native Isaac render diagnostics appear in robot-camera and scene-camera
  manifests/reports.

### Phase 2: Object-Gate Corpus

Run the detailed object/render subplan for current and held-out slices.

Minimum corpus:

- current reviewed `seed=6`/`0008` artifacts if reproducible;
- `procthor-10k-val` `val_0` and `val_1`;
- at least one held-out scene before default promotion;
- both structured world-label evidence and RAW_FPV/camera-raw evidence when
  the same backend setup supports both.

Object-gate output per selected object:

- MuJoCo object/body/joint binding;
- Isaac USD prim binding;
- referenced asset and renderable geometry status;
- FPV/chase crop nonblank status;
- pose/extent delta where available;
- material/texture summary;
- visual/articulated state risk;
- final status such as `comparable`, `missing_binding`,
  `missing_renderable_geometry`, `pose_delta`, `material_delta`,
  `visual_state_delta`, or `not_comparable`.

Acceptance:

- Missing or unrenderable objects are explicit report failures.
- Box remains covered by the visual-state contract.
- Any newly risky category gets either a category-level contract or a tracked
  blocker.

### Phase 3: Render-Gate And Exposure Probe

After object-gate failures are separated, evaluate render-domain differences.

Probe matrix:

- current native Isaac defaults with settings recorded;
- deterministic fixed-exposure/tone preset;
- one or two native tone-mapping candidates;
- existing post-render RGB/view-gain profiles as comparison-only controls.

Acceptance:

- Reports distinguish native Isaac settings from post-render comparison
  profiles.
- FPV brightness improves on held-out evidence before any native preset is
  considered.
- Chase does not regress beyond the agreed tolerance, or the report marks
  chase as warning-only with explicit rationale.

### Phase 4: Task-Level Apple-To-Apple Runs

Once camera, object, and render gates are visible, rerun task-level evidence.

Run shapes:

```bash
just task::run semantic-map-build direct world-labels seed=6 generated_mess_count=5
just task::run household-cleanup direct world-labels seed=6 generated_mess_count=5
just task::run household-cleanup direct camera-raw seed=6 generated_mess_count=5
```

Use equivalent MuJoCo and Isaac backend settings for each lane. If Isaac cannot
support a lane, record that as an environment/backend gap rather than comparing
against a different input contract.

Acceptance:

- The report identifies which images are model input and which are report-only
  evidence.
- Semantic-map and cleanup outputs use the same public map/input contract
  across backends.
- Any score or behavior difference is interpreted only after visual comparability
  gates pass.

## Engineering Review Gates

Fast CI-safe gates:

```bash
ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py

ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py

./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py \
  tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py \
  tests/unit/molmo_cleanup/test_isaac_lab_backend.py \
  tests/contract/molmo_cleanup/test_scene_camera_comparison.py
```

Local GPU gates:

- regenerate prepared USD artifacts for audited scenes;
- rerun MuJoCo/Isaac robot-camera apple-to-apple comparison;
- rerun scene-camera comparison;
- rerun at least one RAW_FPV/camera-raw cleanup probe;
- inspect `report.html` image pairs before changing defaults.

## Reduce-Entropy Rules

- Keep one detailed object/render audit plan:
  `docs/plans/mujoco-isaac-object-render-parity-audit.md`.
- Keep this file as the higher-level convergence plan and decision checklist.
- Do not create another task name unless public command shape or report shape
  changes materially.
- Prefer shared diagnostics in existing reports over new standalone scripts.
- Keep per-category fixes in a registry with tests and real artifact evidence.
- Keep run evidence in `docs/status/active/mujoco-isaac-camera-visual-parity.md`
  or generated output reports, not in scattered ad hoc notes.

## Open Questions

- What exact tolerance makes chase a hard gate versus warning-only report
  evidence?
- How many held-out scenes are enough before promoting native Isaac exposure or
  material/light defaults? Initial target: current two scenes plus one held-out
  scene; stronger target: five scenes and at least three seeds.
- Which categories beyond box need explicit visual-state contracts after the
  first corpus run?
- Should Isaac fixed exposure be one global preset or scene-calibrated with
  strict held-out validation?

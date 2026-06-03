# MuJoCo Isaac Object And Render Parity Audit

**Status:** Planned
**Created:** 2026-06-03
**Last updated:** 2026-06-03
**Source:** MuJoCo/Isaac visual parity discussion after FPV head-camera
alignment, chase-camera repair, combined material/light default path, and box
visual-state freeze.
**Workflow:** Pre-GSD plan. Use this file as the next execution source before
creating any `.planning/` phase.

## Intuitive-Flow Autoplan Reconciliation

**Review date:** 2026-06-03
**Review route:** `intuitive-flow` inline review. The vendored gstack
`autoplan` skill document is available in this environment, but no runnable
autoplan executable tree is available from this checkout. The review decisions
below are reconciled into this plan before implementation, following the
existing Roboclaws pre-GSD plan pattern.

Accepted decisions:

- Keep the first implementation to one CI-safe diagnostics slice: add explicit
  Object Gate and Render Gate classification to existing robot-camera
  apple-to-apple manifests and reports.
- Reuse the existing object parity audit, render contract diagnostics,
  residual triage, and visual parity summary surfaces. Do not add a new
  runnable task or default cleanup path for this slice.
- Make missing bindings, missing renderable geometry, pose/category/support
  deltas, material/texture deltas, and visual-state deltas visible as Object
  Gate failures before any render residual can be treated as renderer-domain
  evidence.
- Classify render residuals only for objects already comparable enough for
  image residual interpretation. Do not fold object failures into aggregate
  RGB/color/tone residual claims.
- Prove the slice with synthetic CI-safe state and fake manifest tests. Real
  MuJoCo/Isaac corpus regeneration stays a local GPU gate.

Deferred decisions:

- Do not promote new Isaac tone, exposure, material, or light defaults in this
  slice.
- Do not expand `OBJECT_VISUAL_STATE_CATEGORIES` beyond `box` until corpus
  evidence shows a repeatable category-level state risk.
- Do not create a `.planning/` GSD phase until this diagnostics slice is
  proof-backed and the next broader execution source is clear.

## Problem

The current MuJoCo/Isaac apple-to-apple evidence has closed the most visible
camera and box regressions:

- FPV is aligned to the real robot-mounted head camera in both backends.
- Chase camera is auxiliary report evidence and now follows the same
  robot-relative rear/high contract.
- The prepared Isaac USD default path uses the combined material/light parity
  preset.
- The user-flagged box open/closed mismatch is fixed by freezing visual
  physics after USD flattening and labeling.

The remaining risk is broader than that one box. We need an auditable answer to
whether other large or small objects can be missing, rendered differently,
posed differently, or drifting to a different articulated/physics state in
Isaac versus MuJoCo. We also need to move the brightness/exposure discussion
from report-side color compensation to explicit Isaac/RTX renderer settings.

## Goal

Build a corpus-level visual parity gate for MolmoSpaces MuJoCo and Isaac that
answers two questions separately:

1. **Object Gate:** Are the same target objects present, renderable, posed, and
   in the same visual state in both backends?
2. **Render Gate:** Given matched objects and camera geometry, are remaining
   differences caused by materials, lights, shadows, tone mapping, exposure, or
   unavoidable renderer response?

The first production claim should be conservative: "the audited categories and
scene slices are comparable, with known residual classes visible in the
report," not "all future MolmoSpaces scenes are guaranteed identical."

## Non-Goals

- Do not change the FPV contract away from `robot_0/head_camera` in MuJoCo and
  `/World/robot_0/head_camera` in Isaac.
- Do not make chase camera a policy/input camera.
- Do not hand-tune every object instance or create per-object-id hacks.
- Do not promote report-side RGB/luminance compensation as default Isaac
  rendering.
- Do not claim physical-robot or planner-backed manipulation from semantic
  pose edits.
- Do not block existing cleanup defaults while the broader audit is still in
  progress.

## Current Decisions

### Box Handling

The box fix has two layers:

- **Global layer:** prepared Isaac USD now freezes visual physics after
  flattening/labeling. That removes PhysX joints, physics APIs, and physics
  properties from the static visual report stage so Isaac cannot re-solve the
  box flaps open during capture.
- **Category-contract layer:** the apple-to-apple report currently records an
  explicit `visual_state_contract` for `box`, because that is the category with
  concrete user-visible evidence.

This is not a one-off per-object-id patch, but the explicit state contract is
currently box-focused. Other categories should be added only after the corpus
audit shows a repeatable category-level state risk.

### Object Policy

Use category-level rules when possible:

- Missing USD references should be fixed by reference installation or prepared
  scene generation, not by hiding the object from comparison.
- Material/light fixes should be default candidates only when they improve
  held-out slices without breaking FPV or chase gates.
- Articulated/physics-state fixes should be category-level contracts backed by
  report evidence and tests.
- If an object cannot be fairly bound in both backends, mark it
  `not_comparable` and keep it out of aggregate residual claims.

### Isaac Exposure Policy

Current Roboclaws color profiles are post-render/report-side comparison tools.
They are useful diagnostics, but they are not the same as configuring Isaac
Sim/RTX rendering. The next exposure work should first record the native RTX
post-processing state, then probe explicit native settings.

Primary implementation references:

- Omniverse RTX post-processing settings:
  `https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx_post-processing.html`
- Isaac Lab camera/render separation and ISP constraints:
  `https://isaac-sim.github.io/IsaacLab/release/3.0.0-beta2/source/overview/core-concepts/sensors/camera.html`
- Isaac Sim camera sensors and render products:
  `https://docs.isaacsim.omniverse.nvidia.com/latest/sensors/isaacsim_sensors_camera.html`

Relevant native axes include tone mapping operator, camera exposure, ISO,
f-stop, white point, OCIO, auto exposure, color correction, and color grading.
For deterministic apple-to-apple comparison, auto exposure should be logged and
usually disabled unless it is the explicit probe under test.

## Plan

### Phase 0: Baseline Inventory

Record a root-visible baseline before new changes:

- current commit;
- current prepared USD summary for the combined material/light default path;
- current robot-camera apple-to-apple manifest/report;
- current scene-camera calibration manifest/report;
- current RAW_FPV cleanup probe evidence.

Output:

- `docs/status/active/mujoco-isaac-camera-visual-parity.md` remains the long
  evidence ledger.
- This plan remains the execution source for new work.

Acceptance:

- Baseline artifacts are named in the first implementation PR or closeout note.
- Existing FPV head-camera and box visual-state checks still pass.

### Phase 1: Object Parity Corpus Audit

Extend the apple-to-apple comparison so each selected object receives a compact
object-gate record:

- exact MuJoCo object/body/joint binding;
- exact Isaac USD prim binding;
- referenced-asset/renderability status;
- RGB crop nonblank status in FPV and chase views;
- segmentation/bbox evidence when available;
- pose/extent delta when both backends expose comparable geometry;
- material/texture contract summary;
- articulated or physics-state risk;
- final status: `comparable`, `not_comparable`, `missing_binding`,
  `missing_renderable_geometry`, `pose_delta`, `material_delta`,
  `visual_state_delta`, or `render_domain_residual`.

Initial corpus:

- keep the known `val_0` and `val_1` seed slices for regression continuity;
- add at least one held-out scene before any new default promotion;
- cover both `world-labels` report evidence and `camera-raw` RAW_FPV input
  lane;
- include both `semantic-map-build` and `household-cleanup` style captures
  when the same backend setup supports both without changing public task
  defaults.

Output:

- `object_visual_parity_audit` section in `comparison_manifest.json`;
- HTML report table grouped by category and status;
- a machine-readable summary with per-category counts.

Acceptance:

- Selected objects that contribute to aggregate residual metrics are explicitly
  comparable in both backends.
- Missing or unrenderable objects are visible as audit failures, not silently
  folded into color residuals.
- Current box evidence remains `visual_state_static_ref_baked`.

### Phase 2: Category-Level Visual State Registry

Turn repeated state risks into category-level contracts. Start with `box`;
only add more categories after Phase 1 shows repeatable evidence.

Candidate categories to watch:

- boxes or containers with flaps/lids;
- cabinets, drawers, doors, and other articulated receptacles;
- appliances with open/closed parts;
- small deformable-looking objects whose USD/MJCF visual state may be
  materially different;
- fixtures where Isaac imports dynamic state even though comparison capture
  should be static.

Rules:

- Prefer registry entries by semantic category and USD/MJCF structure, not by
  one object id.
- Every registry entry must have a report field, a unit test, and at least one
  real artifact path in the evidence note.
- If the fix is global USD prep behavior, still report which categories are
  protected by it.

Acceptance:

- `OBJECT_VISUAL_STATE_CATEGORIES` is either still only `box` with audit
  evidence that no other category needs promotion, or expanded with tests and
  real corpus evidence.
- Report wording makes clear whether a category is protected by global visual
  physics freeze, an explicit state check, or both.

### Phase 3: Native Isaac Tone And Exposure Probe

Add native renderer diagnostics to the Isaac capture path before tuning.

Record at minimum:

- tone mapping operator and active post-processing settings;
- camera exposure, ISO, f-stop, white point;
- auto-exposure enabled/disabled state and clamp settings;
- OCIO config/display/view/look when active;
- color correction and color grading settings;
- renderer mode and render-product/camera prim paths;
- whether any Isaac Lab ISP path is active.

Probe matrix:

- current native defaults, with all settings recorded;
- deterministic fixed-exposure preset, auto exposure disabled;
- one or two native tone-mapping candidates, held out from the fitting slice;
- existing report-side RGB/view-gain profiles as comparison-only controls.

Promotion rule:

- A native exposure/tone preset can become a default candidate only if it
  improves held-out FPV without introducing chase regressions above tolerance,
  and if the report shows the native settings directly. Post-render profiles
  remain report-side only.

Acceptance:

- Isaac manifests contain native RTX/camera exposure diagnostics for every
  capture.
- The visual report can tell the difference between native renderer settings
  and post-render comparison profiles.
- No default exposure/tone change lands without held-out evidence.

### Phase 4: Report UX Split

Rework the report summary around the two gates:

- **Object Gate:** binding, renderability, pose/extent, and visual state.
- **Render Gate:** camera geometry, material/texture, light/shadow, native
  exposure/tone, and residual class.

The report should make the common maintainer questions answerable without
opening JSON:

- Is this object actually present in both renderers?
- Is this a missing-asset/state issue or a renderer-response issue?
- Are FPV and chase using the intended cameras?
- Is brightness coming from Isaac native settings or report-side compensation?
- Which categories need a real fix before broader scene rollout?

Acceptance:

- `report.html` embeds enough image pairs and tables for visual review.
- The top-level summary does not collapse object failures into render-domain
  residuals.
- RAW_FPV input status is separate from world-label report evidence.

## Implementation Touchpoints

- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `roboclaws/household/scene_camera_comparison.py`
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
- `scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py`
- `roboclaws/household/color_management.py`
- `roboclaws/household/camera_control.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
- `tests/unit/molmo_cleanup/test_prepare_molmospaces_flattened_semantic_usd.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`

## Verification Gates

Fast local/CI-safe gates:

```bash
ruff check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
  scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py

ruff format --check scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  roboclaws/household/scene_camera_comparison.py \
  scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
  scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py

./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py \
  tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py \
  tests/unit/molmo_cleanup/test_isaac_lab_backend.py

.venv-isaaclab/bin/python -m pytest -q \
  tests/unit/molmo_cleanup/test_prepare_molmospaces_flattened_semantic_usd.py
```

Real local GPU gates:

- regenerate prepared USD for each audited scene;
- run MuJoCo/Isaac apple-to-apple robot-camera comparison on the corpus;
- run at least one RAW_FPV cleanup probe after native exposure diagnostics land;
- refresh the visual parity summary report;
- inspect `report.html` image pairs for representative high-residual objects.

## Risks

- Isaac segmentation can fail independently of RGB renderability. The object
  gate must not depend on segmentation alone.
- Some residuals are true renderer/material-model differences. The report
  should classify these honestly instead of forcing fake equality.
- New scenes may expose missing USD references. Treat that as an asset-prep
  failure to fix, not as a reason to drop those scenes quietly.
- Native tone/exposure settings may improve FPV and hurt chase, or vice versa.
  Keep promotion gated by both views unless chase is explicitly re-scoped.
- More corpus coverage may reveal that the current combined material/light path
  is good but not universal. That should become category/scene evidence, not a
  rollback of already-proven camera alignment.

## Open Questions

- What corpus size is enough before promoting another default? Initial target:
  current two scenes plus one held-out scene; stronger target: five scenes and
  at least three seeds.
- Should chase remain a hard blocker for default-rendering promotion, or only a
  report-side warning once FPV and object gates are green?
- Which object categories should receive explicit visual-state contracts after
  the first corpus audit?
- Should native exposure use a fixed deterministic preset for all reports, or
  a scene-calibrated preset with strict held-out validation?

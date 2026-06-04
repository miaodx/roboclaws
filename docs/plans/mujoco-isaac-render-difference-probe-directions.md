---
status: ACTIVE_SUBPHASE
plan_scope: mujoco-isaac-render-difference-probe-directions
created: 2026-06-04
last_updated: 2026-06-04
accepted_severities:
  - P1
  - P2
---

# MuJoCo Isaac Render Difference Probe Directions

## Status

ACTIVE_SUBPHASE

This is a focused direction file for the visible MuJoCo/Isaac render differences
after FPV camera parity improved. The 2026-06-04 bounded worker sub-phase makes
the existing robot-camera visual-parity summary executable enough to stop on a
ranked probe batch. The follow-up capture-quality sub-phase focuses on the
remaining soft/noisy Isaac FPV and chase views by separating resolution,
downsampling, render-settle, sampling, denoise/TAA, and texture filtering. It
is still not a default-renderer promotion phase.

The accepted sub-phase scope is:

- derive candidate rows from existing `--probe-manifest label=path` summary
  inputs instead of adding a new renderer framework;
- emit `render_difference_probe_batch` in `visual_parity_summary.json`;
- render the same ranked table in `report.html`;
- classify rows as `native_default_candidate`, `report_side_only`, or
  `rejected`;
- keep L4 MuJoCo/Isaac GPU rendering as the local evidence step.
- keep direct high-resolution images separate from fair downsampled
  apple-to-apple metrics, so human-review usefulness does not get confused with
  policy/input image quality.

Hard-stop decisions found: none. The plan remains scoped to report/probe
contract execution and does not promote renderer defaults.

2026-06-04 continuation evidence:

- The current best primary baseline remains
  `output/molmo/robot-camera-apple2apple/0604_val1_seed6_2mess_4loc_body_pose_fix_latest_gate_6b7c282c/report.html`
  with FPV/chase mean-abs-RGB `25.4550` / `41.7204`.
- Alarm-clock material probes are rejected as default candidates:
  `sourceColorSpace=raw` was noise-level and `roughness=1.0` changed FPV
  `25.4550 -> 25.4441` while regressing chase `41.7204 -> 41.7532`.
- High-resolution 1080->540 downsample is not a default candidate on the
  primary slice: FPV regressed `25.4550 -> 25.6557` even though chase improved
  `41.7204 -> 37.3285`. A follow-up `1620x1080 -> 540x360` probe needed a
  MuJoCo offscreen-framebuffer fix, then improved chase less strongly
  (`41.7204 -> 37.8022`) while leaving FPV effectively unchanged
  (`25.4550 -> 25.4521`). Treat high-resolution/downsample alone as
  comparison evidence, not a default candidate. Summary:
  `output/molmo/robot-camera-apple2apple/0604_val1_seed6_4loc_capture_resolution_settle_summary_framebufferfix_ae02e705/report.html`.
- `render_settle_frames=16` is the strongest stable capture-quality candidate
  so far:
  primary slice improves FPV/chase `25.4550` / `41.7204` to `24.9437` /
  `34.7722`; a comparable val_0 four-location skip-audit held-out run improves
  `32.8863` / `37.6759` to `32.7532` / `37.4365`. Do not promote it as a
  default yet because per-target rows still regress (`atomizer` and
  `baseballbat` chase on primary, one bed FPV on val_0). Treat it as a
  capture-quality candidate, not a solved visual-parity fix.
- The only supported combined capture-quality probe,
  `1620x1080 -> 540x360 + render_settle_frames=16`, ranks best on the primary
  slice and makes all FPV residuals low (`25.4550 -> 24.5468`, chase
  `41.7204 -> 35.5907`), but it fails held-out promotion: on the val_0
  four-location skip-audit slice, FPV slightly regresses
  `32.8863 -> 32.9267` and chase improves only marginally
  `37.6759 -> 37.5460`, ranking behind plain `settle16`. Keep this combination
  as primary-slice evidence only; do not promote resolution/downsample or the
  combo. Summaries:
  `output/molmo/robot-camera-apple2apple/0604_val1_seed6_4loc_capture_resolution_settle_combo_summary_framebufferfix_ae02e705/report.html`
  and
  `output/molmo/robot-camera-apple2apple/0604_latest_code_val0_seed6_4loc_capture_combo_heldout_summary_framebufferfix/report.html`.
- Capture-quality comparison runs may use `--skip-object-parity-audit` to avoid
  val_0 full-scene object-audit/report postprocessing dominating the probe. A
  skip-audit artifact is valid for image-metric ranking only; rerun without the
  flag before making object-level parity claims.
- `render_settle_frames=32` on the same latest-code primary slice is not better
  than `settle_16_540`: it improves baseline FPV/chase to `24.7595` / `34.9813`,
  but `settle16` remains slightly better on chase (`34.7722`) and has the same
  residual-class distribution. Keep `settle16` as the preferred
  capture-timing candidate.
- A DistantLight `rotateX=+25` probe is not a valid new primary-slice axis
  because the current prepared body-pose USD already has `xformOp:rotateX = 25`.
  The non-no-op `DistantLight.inputs:intensity=750` single-axis probe improved
  average FPV `25.4550 -> 24.7753` and chase `41.7204 -> 40.9913`, but regressed
  box/alarm-clock FPV residual classification (`1 -> 2`
  geometry/texture-edge FPV residuals) and remains far worse than `settle16` for
  chase. Reject this light-intensity direction for the current slice.
- A native exposure probe now has explicit CLI support via
  `--isaac-exposure-bias`, with set/restore evidence recorded by the Isaac
  worker. The primary `exposure_bias=-1` run is effectively noise-level and
  slightly regresses FPV (`25.4550 -> 25.4658`) while leaving chase unchanged
  (`41.7204 -> 41.7163`), so do not expand an exposure grid unless a new
  targeted reason appears.
- The matching primary `exposure_bias=+1` run is also rejected: FPV changes only
  at noise level (`25.4550 -> 25.4479`) while chase regresses
  (`41.7204 -> 41.8282`), and the alarm-clock FPV residual class worsens. Close
  the native exposure axis unless a later targeted hypothesis reopens it.
  Summary:
  `output/molmo/robot-camera-apple2apple/0604_val1_seed6_4loc_exposure_probe_summary_ae02e705/report.html`.
- A matched latest-code `val_1` / seed 6 / two-mess / eight-location combined
  USD rerun gives stronger but still incomplete support for `settle16`: with
  identical selected targets, baseline FPV/chase `28.5147` / `43.5060` improves
  to `28.0558` / `40.0803`, FPV residual classes improve from
  `2 geometry_or_texture_edge_residual + 6 low_residual` to
  `1 geometry_or_texture_edge_residual + 7 low_residual`, and chase improves
  from `6 geometry_or_texture_edge_residual + 2 low_residual` to
  `4 geometry_or_texture_edge_residual + 3 low_residual + 1 render_domain_residual`.
  However, per-target regressions remain (`atomizer` FPV/chase,
  `baseballbat` FPV/chase, one cellphone FPV/chase, and box chase), so
  `settle16` is still a capture-timing candidate rather than a default-renderer
  solution. Summary:
  `output/molmo/robot-camera-apple2apple/0604_latest_code_val1_seed6_8loc_settle16_matched_summary_ec2d25c8/report.html`.
- A targeted current-code bed/fabric material probe on the val_0 bed-heavy
  four-location held-out slice is rejected. Starting from the current combined
  USD, `bed_source_raw` rewrote 8 bed texture `sourceColorSpace` fields to
  `raw`; real MuJoCo/Isaac render metrics regressed FPV
  `32.8863 -> 33.4799` and chase `37.6759 -> 37.7414`. The same slice with
  `bed_scale_power05`, a category-level bed texture scale/fallback power-0.5
  probe, also regressed FPV `32.8863 -> 33.9983` while only slightly improving
  chase `37.6759 -> 37.5649`. Both rows keep the same residual class counts and
  are ranked as rejected behind `settle_16_540`. Do not expand these bed
  color-space or partial-scale directions without a new target-specific
  mechanism. Summary:
  `output/molmo/robot-camera-apple2apple/0604_latest_code_val0_seed6_4loc_material_bed_probe_summary/report.html`.
- A native Isaac color-correction gain probe is rejected. The gain fitted from
  the val_0 FPV baseline (`1.088088,1.06136,1.099827`) was applied through
  `/rtx/post/colorcorr/enabled` and `/rtx/post/colorcorr/gain`; the worker
  recorded previous values and restored them after capture. The real
  MuJoCo/Isaac render regressed FPV and chase strongly versus the same baseline
  (`+10.0156` FPV, `+7.4897` chase), so close this native colorcorr gain axis
  and do not expand it without a new non-global, target-specific hypothesis.
  Summary:
  `output/molmo/robot-camera-apple2apple/0604_latest_code_val0_seed6_4loc_native_colorcorr_gain_summary/report.html`.
- The DistantLight angle micro-grid is rejected on the latest-code val_0
  four-location held-out slice. `rotateX=15` completed a real rerun and
  changed FPV/chase versus baseline by `+0.4188` / `-0.0292`, so it failed FPV.
  `rotateX=30` initially exposed a worker interface regression
  (`camera_yaw_offset_deg` / `camera_pitch_offset_deg` not accepted by the
  MuJoCo robot-view worker path); after fixing that execution blocker, a fresh
  real MuJoCo+Isaac rerun completed 4/4 locations and changed FPV/chase by
  `-0.0465` / `+0.2345`, still below the FPV improvement threshold and with a
  chase regression. Both rows keep the same residual class distribution. Close
  the light-angle axis for this slice unless a new mechanism targets material
  or shadow response directly. Summary:
  `output/molmo/robot-camera-apple2apple/0604_latest_code_val0_seed6_4loc_light_angle_probe_summary/report.html`.

## Target

Robot-camera apple-to-apple visual parity for MolmoSpaces MuJoCo versus Isaac
Lab, after camera geometry has already been aligned.

Current baseline evidence:

- Review report:
  `output/molmo/robot-camera-apple2apple/0604_val0_seed6_5mess_8loc_canonical_mess_review/report.html`
- FPV lens is aligned: `vertical_fov_delta_deg_max ~= 1e-6`.
- FPV world pose is aligned: `position_delta_m_max = 0.005m`.
- Current Isaac native render settings are default RTX:
  `default_render_settings_changed=false`, `filmIso=100`, `fNumber=5`,
  `cameraShutter=50`, tone map `op=6`, and color correction disabled.
- Remaining residuals are classified as render-domain:
  FPV has 5/8 `low_residual`, 2/8 `geometry_or_texture_edge_residual`, and
  1/8 `view_dependent_color_residual`; chase is still high and auxiliary.
- The latest `val_1`, seed 6, two-mess, four-location body-pose fix artifact
  shows the box open/closed state is now aligned, but the alarm-clock row still
  has visibly softer Isaac FPV and noisy/poor Isaac chase:
  `output/molmo/robot-camera-apple2apple/0604_val1_mujoco_body_pose_fix_seed6_2mess_4loc/report.html`.
  The alarm-clock FPV camera contract is aligned
  (`vertical_fov_delta_deg=1e-6`, camera position delta `0.005m`) and the FPV
  residual is already classified `low_residual` (`mean_abs_rgb=29.5349`), while
  chase remains `geometry_or_texture_edge_residual` (`mean_abs_rgb=56.2775`).
  Treat this as capture/render quality evidence first, not another camera-pose
  fix.

## Accepted Severity

- **P1:** Avoid false attribution. Reports must not make the remaining visual
  differences look like camera geometry problems when evidence points at
  renderer/material/light response.
- **P2:** Make the experiment matrix structured enough that future agents do
  not keep trying one-off brightness tweaks without held-out evidence.

## Directions To Try

### 1. Native Tone And Exposure

Question: is the grey/flat Isaac appearance coming from RTX tone mapping or
native camera exposure rather than object geometry?

Probe axes:

- tone map operator candidates, held out from fitting;
- exposure compensation around current default;
- `filmIso`, `cameraShutter`, and `fNumber`;
- `maxWhiteLuminance` and white point;
- auto-exposure state, logged explicitly and disabled unless it is the
  deliberate probe under test.

Rules:

- Prefer native RTX/Isaac settings over post-render RGB gain when evaluating a
  default-rendering candidate.
- Keep report-side RGB/view gain as comparison-only evidence unless explicitly
  promoted later.
- A native preset may become a default candidate only if held-out FPV improves
  without chase regression above tolerance.

References:

- Omniverse RTX post-processing:
  `https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx_post-processing.html`
- Omniverse camera exposure attributes:
  `https://docs.omniverse.nvidia.com/materials-and-rendering/latest/cameras.html`

### 2. DistantLight Grid

Question: is Isaac lighting direction/intensity making surfaces look washed out
or shadow response too different from MuJoCo?

Existing evidence:

- Simple DomeLight removal worsened prior residuals.
- Enabling wall/ceiling shadows worsened prior residuals.
- DistantLight orientation was the more promising axis; `rotateX=+25` was the
  best previous candidate in the prepared material/light path.

Probe axes:

- `DistantLight.rotateX`: 15, 20, 25, 30;
- intensity multiplier: 0.5, 0.75, 1.0;
- exposure: -1, 0, +1;
- angle: small range only, to separate sharpness/soft-shadow effects from
  global brightness.

Rules:

- Do not promote simple DomeLight removal or broad shadow enabling without new
  held-out evidence.
- The latest val_0 `rotateX=15/30` micro-grid is already closed as rejected;
  do not continue angle-only probes without a new, target-specific light/shadow
  mechanism.
- Keep light probes separate from native tone/exposure probes first, then test
  one combined best candidate only after each axis has an individual result.

Reference:

- USD DistantLight intensity/exposure/angle:
  `https://openusd.org/dev/user_guides/schemas/usdLux/DistantLight.html`

### 3. Fabric And Material Response

Question: are bed, pillow, and cloth-like surfaces different because USD
PreviewSurface material conversion does not match MuJoCo material/texture
response?

Probe axes:

- texture color space: sRGB versus linear handling;
- texture scale and wrap mode;
- diffuse fallback color and texture fallback values;
- roughness/specular defaults;
- category-specific fabric/bed material records.

Rules:

- Do not fix fabric differences with global exposure unless the held-out corpus
  shows it does not hurt other categories.
- Prefer category/material-level evidence over per-object-id patches.
- Keep `box` visual-state handling separate from material response; box was a
  physics/visual-state issue, not a brightness issue.

### 4. Resolution, Sampling, Denoise, And Texture Filtering

Question: is the Isaac "soft" or defocused appearance caused by render
resolution, sampling, denoise/TAA, or mip/filter behavior?

Probe axes:

- render resolution: 540x360, 1080x720, 1620x1080;
- downsample high-resolution images back to 540x360 for fair comparison;
- keep direct high-resolution comparison images as human-review artifacts;
- RTX sample count;
- render-settle / warm-up frame count before saving RGB;
- denoiser/TAA enablement;
- texture mip/filter/anisotropy settings if exposed by the current runtime.

Expected interpretation:

- If high-resolution-downsampled Isaac becomes closer to MuJoCo, sampling,
  mip/filter, or denoise is a real contributor.
- If direct high-resolution images look better but downsampled metrics do not
  improve, the report display/resolution is the useful change, not the
  apple-to-apple policy/input camera.
- If color/brightness remains similar while edges sharpen, resolution is not
  the primary cause; continue with tone/light/material work.
- If chase speckling remains at high resolution but improves with extra settle
  frames or samples, the root cause is RTX convergence / capture timing, not
  material identity.
- If neither resolution nor settle/sampling improves FPV/chase, return to
  native tone/light/material probes.

Rules:

- Do not increase default resolution to mask a render-domain mismatch.
- Run this as a separate probe from light and tone changes so the cause stays
  attributable.
- Do not compare high-resolution direct images against 540x360 baseline metrics.
  Either compare both backends at the same high resolution, or downsample both
  high-resolution outputs to the baseline size before computing metric deltas.

## Full Capture-Quality Probe Plan

### Scope Gate

- **Target:** Isaac robot-view capture quality inside the existing
  robot-camera apple-to-apple report path.
- **In scope:** FPV softness, chase noise/speckle, high-resolution direct
  review images, high-resolution-to-540x360 downsample metrics, render-settle
  frames, RTX sample/AA/denoise settings when exposed, and report fields that
  make those variables visible.
- **Out of scope:** changing the robot FPV camera pose/FOV, promoting a new
  default renderer preset, changing cleanup public defaults, or adding
  per-object material hacks.
- **Accepted severities:** P1 false-attribution fixes and P2 structured probe
  cleanup inside this target.
- **Minimum confidence:** L1/L2 for any report/schema edits; L4 for real
  MuJoCo/Isaac probe evidence.

### Probe Corpus

Use two slices so the first pass catches both current visible failures and a
small held-out check:

- **Primary reviewed slice:** `procthor-10k-val`, `val_1`, seed `6`,
  `generated_mess_count=2`, `location_count=4`, prepared body-pose USD:
  `output/isaaclab/flattened-semantic-usd/0604_val1_mujoco_body_pose_fix/scene_semantic.usda`.
  This contains the user-reviewed alarm-clock row and the now-fixed box row.
- **Continuity slice:** `procthor-10k-val`, `val_0`, seed `6`,
  `generated_mess_count=5`, `location_count=8`, current combined
  material/light prepared USD. Use the latest known prepared scene for the
  existing visual-parity baseline.

### Candidate Matrix

Run these as independent candidates first. Combine axes only after one axis
shows a clear benefit.

| Label | Render Size | Saved Report Image | Metric Size | Extra Variable | Purpose |
| --- | --- | --- | --- | --- | --- |
| `baseline_540` | 540x360 | 540x360 | 540x360 | current defaults | Current comparable baseline. |
| `hires_1080_direct` | 1080x720 | 1080x720 | 1080x720 | current defaults | Human-review direct high-res quality. |
| `hires_1080_downsample540` | 1080x720 | 540x360 downsample | 540x360 | current defaults | Fair test for sampling/filter/denoise quality. |
| `hires_1620_downsample540` | 1620x1080 | 540x360 downsample | 540x360 | current defaults | Stronger downsample signal if 1080 is ambiguous. |
| `settle_16_540` | 540x360 | 540x360 | 540x360 | 16 warm-up/settle frames before save | Test RTX convergence/capture timing without resolution changes. |
| `settle_32_540` | 540x360 | 540x360 | 540x360 | 32 warm-up/settle frames before save | Escalate only if 16 helps or chase remains noisy. |
| `samples_hi_540` | 540x360 | 540x360 | 540x360 | higher RTX samples/AA if setting is exposed | Test sampling/AA independent of resolution. |
| `denoise_toggle_540` | 540x360 | 540x360 | 540x360 | denoise/TAA toggle if setting is exposed | Isolate denoise/TAA blur or speckle. |
| `hires_1080_downsample540_settle16` | 1080x720 | 540x360 downsample | 540x360 | high-res plus settle | Only run if both resolution and settle individually help. |

If a runtime setting is not exposed, record `setting_status=not_available` in
the candidate metadata and skip that row rather than guessing at an Omniverse
path.

### Required Manifest Fields

Each probe manifest or summary row should record:

- `render_resolution_requested` and `render_resolution_saved`;
- `metric_resolution`;
- whether images were direct captures or downsampled;
- downsample filter used;
- render-settle frame count;
- samples/AA/denoise/TAA setting values or `not_available`;
- native Isaac render diagnostics before capture;
- FPV and chase mean-abs-RGB deltas versus same-size baseline;
- FPV and chase residual class distribution;
- edge/noise/blur metrics per view if available;
- policy classification: `native_default_candidate`, `report_side_only`,
  `capture_quality_probe`, or `rejected`.

### Interpretation Rules

- **High-res direct improves but downsample does not:** keep as report UX /
  human-review improvement only. Do not call it policy/input camera improvement.
- **High-res downsample improves FPV and chase:** sampling/filter/AA is likely
  contributing; test 1620-downsample and samples/AA next.
- **High-res downsample improves FPV but chase still speckles:** split the next
  action: keep resolution as FPV candidate and test settle/samples for chase.
- **Settle improves chase without changing FPV much:** capture timing /
  convergence is likely the chase problem. Prefer a small settle default only
  after held-out proof.
- **Samples/AA improves both direct and downsample rows:** native capture
  quality preset may be a candidate, subject to runtime cost and held-out proof.
- **Only post-render gain improves metrics:** classify as `report_side_only`;
  do not promote to native renderer or policy/input path.
- **No capture-quality row improves:** park resolution/sampling and continue
  with tone/light/material probes.

### Suggested Commands

Baseline shape:

```bash
.venv/bin/python scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  --output-dir output/molmo/robot-camera-apple2apple/0604_val1_seed6_2mess_4loc_baseline_540 \
  --seed 6 --generated-mess-count 2 \
  --scene-source procthor-10k-val --scene-index 1 \
  --scene-usd-path output/isaaclab/flattened-semantic-usd/0604_val1_mujoco_body_pose_fix/scene_semantic.usda \
  --location-count 4 \
  --render-width 540 --render-height 360
```

Probe runs use the same command shape with candidate-specific output
directories and the small capture-quality overrides now exposed by the runner:

- `--saved-report-width` / `--saved-report-height` for report-visible
  downsampled images;
- `--metric-width` / `--metric-height` for same-size metric artifacts;
- `--downsample-filter` for explicit resize filter selection;
- `--render-settle-frames` for extra Isaac frames after first nonblank RGB.

Example high-res-downsample row:

```bash
.venv/bin/python scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py \
  --output-dir output/molmo/robot-camera-apple2apple/0604_val1_seed6_2mess_4loc_hires_1080_downsample540 \
  --seed 6 --generated-mess-count 2 \
  --scene-source procthor-10k-val --scene-index 1 \
  --scene-usd-path output/isaaclab/flattened-semantic-usd/0604_val1_mujoco_body_pose_fix/scene_semantic.usda \
  --location-count 4 \
  --render-width 1080 --render-height 720 \
  --saved-report-width 540 --saved-report-height 360 \
  --metric-width 540 --metric-height 360 \
  --downsample-filter lanczos
```

Batch summary shape:

```bash
.venv/bin/python scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  --output-dir output/molmo/robot-camera-apple2apple/0604_capture_quality_probe_batch_summary \
  --baseline-manifest output/molmo/robot-camera-apple2apple/0604_val1_seed6_2mess_4loc_baseline_540/comparison_manifest.json \
  --probe-manifest hires_1080_direct=output/molmo/robot-camera-apple2apple/<candidate>/comparison_manifest.json \
  --probe-manifest hires_1080_downsample540=output/molmo/robot-camera-apple2apple/<candidate>/comparison_manifest.json \
  --probe-manifest settle_16_540=output/molmo/robot-camera-apple2apple/<candidate>/comparison_manifest.json
```

### Stop Condition For This Probe

Stop when the first capture-quality batch produces:

- a ranked table for at least `baseline_540`, `hires_1080_direct`,
  `hires_1080_downsample540`, and one settle/sampling candidate;
- explicit FPV and chase deltas versus the correct same-size baseline;
- direct-vs-downsample distinction in manifest/report;
- a clear next action: promote nothing, test one combined candidate, or park
  resolution/sampling and return to tone/light/material work.

Do not promote any renderer default from this sub-phase unless the same
candidate improves FPV on the primary slice and does not regress chase on the
continuity slice.

### 5. Report-Side Versus Policy/Input Lane

Question: which improvements are acceptable for human comparison, and which can
change the actual policy-input camera?

Rules:

- Report-side color gain or view-specific tone profiles are review aids only.
- RAW_FPV / policy-input images should remain native-renderer output unless a
  native renderer preset is explicitly promoted.
- Reports must label this distinction clearly so cleanup performance cannot be
  attributed to a post-render compensation path.

## Suggested First Probe Matrix

Run a small local-GPU corpus before any default-setting change:

- `val0`, seed 6, 8 locations;
- `val1`, seed 8, 4 locations;
- current baseline;
- native tone/exposure micro-grid;
- DistantLight micro-grid;
- one high-resolution/downsample probe;
- one fabric/material-focused probe on bed/pillow-heavy views.

Keep each candidate output under `output/molmo/robot-camera-apple2apple/` with
a directory name that records scene, seed, candidate axis, and date.

## Evidence Ladder

- **L1:** unit tests for report fields and manifest/schema shape when code
  changes are needed.
- **L2:** report contract includes native settings, probe candidate metadata,
  and explicit report-side versus native-render distinction.
- **L4:** local MuJoCo/Isaac render evidence for the selected scenes/seeds.

No L5/L6 provider or coding-agent run is needed for this render-domain probe.

## Stop Condition

Stop after the first probe batch produces a ranked table with:

- FPV mean-abs-RGB delta versus baseline;
- chase mean-abs-RGB delta versus baseline;
- residual class distribution;
- native settings used;
- whether the change is native-default candidate, report-side only, or rejected.

Promote nothing by default until at least one candidate improves held-out FPV
and does not regress chase above the agreed tolerance.

Implemented local artifact path:

```bash
.venv/bin/python scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  --output-dir output/molmo/robot-camera-apple2apple/<batch-summary> \
  --baseline-manifest output/molmo/robot-camera-apple2apple/<baseline>/comparison_manifest.json \
  --probe-manifest native_tone_exposure=<probe-dir>/comparison_manifest.json \
  --probe-manifest distantlight_rotx25=<probe-dir>/comparison_manifest.json \
  --probe-manifest material_fabric=<probe-dir>/comparison_manifest.json
```

The generated `visual_parity_summary.json` contains
`render_difference_probe_batch.ranked_rows[]` with FPV delta, chase delta,
residual class distribution, native settings used, report-side profile metadata,
and candidate status. The HTML report has a matching "Render Difference Probe
Batch" table for review.

Verified local artifact:

- `output/molmo/robot-camera-apple2apple/0604_render_difference_probe_batch_summary/visual_parity_summary.json`
- `output/molmo/robot-camera-apple2apple/0604_render_difference_probe_batch_summary/report.html`
- Summary status: `active`
- Probe batch status: `ranked_probe_batch_available`
- Ranked rows: 10
- Candidate status counts: `native_default_candidate=7`, `rejected=3`

## Parked Cross-Seam Ideas

- Broader five-scene, three-seed corpus for final default-rendering promotion.
- Category-level visual-state contracts beyond `box`.
- A separate report UX pass for side-by-side zoom/pixel inspection.
- Real cleanup-task reruns using RAW_FPV after a native renderer candidate is
  selected.

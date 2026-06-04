---
status: PARK
plan_scope: mujoco-isaac-render-difference-probe-directions
created: 2026-06-04
last_updated: 2026-06-04
accepted_severities:
  - P1
  - P2
---

# MuJoCo Isaac Render Difference Probe Directions

## Status

PARK

This is a focused direction file for the visible MuJoCo/Isaac render differences
after FPV camera parity improved. It is not an execution phase yet. Use it to
pick the next bounded local-GPU probe before changing default renderer settings.

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
- RTX sample count;
- denoiser/TAA enablement;
- texture mip/filter/anisotropy settings if exposed by the current runtime.

Expected interpretation:

- If high-resolution-downsampled Isaac becomes closer to MuJoCo, sampling,
  mip/filter, or denoise is a real contributor.
- If color/brightness remains similar while edges sharpen, resolution is not
  the primary cause; continue with tone/light/material work.

Rules:

- Do not increase default resolution to mask a render-domain mismatch.
- Run this as a separate probe from light and tone changes so the cause stays
  attributable.

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

## Parked Cross-Seam Ideas

- Broader five-scene, three-seed corpus for final default-rendering promotion.
- Category-level visual-state contracts beyond `box`.
- A separate report UX pass for side-by-side zoom/pixel inspection.
- Real cleanup-task reruns using RAW_FPV after a native renderer candidate is
  selected.


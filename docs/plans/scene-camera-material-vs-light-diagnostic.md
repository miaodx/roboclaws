# Scene Camera Material Vs Light Diagnostic

**Status:** Implemented
**Created:** 2026-06-05
**Source:** Follow-up to the Genesis/Isaac/MuJoCo scene-camera comparison after
`scene_light_rig_v1` was aligned across all three backends.
**Workflow:** Approved `$intuitive-preflight` contract. This file is the single
plan and evidence surface for deciding whether the next visual-fidelity slice
should tune lighting/tone or inspect material/texture conversion.

## Preflight Contract

## Intuitive-Flow Autoplan Reconciliation

**Review date:** 2026-06-05
**Review route:** `intuitive-flow` inline autoplan precheck. The vendored
`autoplan` skill document is available, but this checkout does not expose a
noninteractive `gstack-autoplan` executable. The review decisions below are
reconciled into this plan before implementation.

Accepted decisions:

- Implement one bounded diagnostics slice in the existing
  `scene-camera-comparison` manifest/report path. Do not add a new runnable task
  or default rendering profile.
- Persist a new material-response diagnostic section that samples in-frame
  object crops and records backend material evidence, rather than keeping the
  10-object analysis as an ad hoc notebook/terminal result.
- Reuse existing scene artifact parsers for MuJoCo MJCF and Isaac USDA material
  contracts. Add only the small Genesis OBJ/MTL materialized-asset parser needed
  to inspect the existing Genesis lane output.
- Keep `scene_light_rig_v1`, lighting profile defaults, tone defaults, camera
  geometry, and render-worker behavior unchanged.
- Prove the implementation with synthetic CI-safe crop/material fixtures and
  focused contract tests. Real GPU reruns remain local evidence, not required
  for this implementation slice.

Deferred decisions:

- Do not tune Isaac dome/key intensity, Genesis ambient/tone/shadow lift, or
  MuJoCo light defaults in this slice.
- Do not make per-object/per-view correction tables.
- Do not claim that material conversion is fixed; this slice only makes the
  material-vs-light decision evidence explicit.

### Goal

Create a 10-object material-vs-light diagnostic that decides whether the next
tuning target should be material/texture conversion or backend light/tone
calibration.

### Scope

- Use the latest report:
  `output/molmo/scene-camera-comparison/0605_scene_light_report_rerun/0605_1656/comparison_manifest.json`.
- Select approximately 10 in-frame objects from existing crop evidence,
  stratified across:
  - high-residual views: dining table and bed;
  - room 2 and room 3;
  - material types: fabric, plastic, paper/white, wood or box, shiny/small
    electronics, sports or round object.
- Compare MuJoCo, Isaac, and Genesis crop appearance and, where available,
  material metadata:
  - diffuse/albedo;
  - texture path or texture presence;
  - roughness/specular/shininess mapping;
  - color-space or gamma clues;
  - material binding path/status.
- Produce a concise diagnostic conclusion:
  `material_issue`, `light_tone_issue`, `mixed`, or `insufficient_evidence`.

### Non-Goals

- Do not change default lighting yet.
- Do not tune per-object or per-view defaults.
- Do not rerun the full GPU comparison unless existing artifacts are
  insufficient.
- Do not special-case `box`.

### Context Package

Must read:

- Latest `comparison_manifest.json`.
- `roboclaws/household/camera_control.py`.
- `roboclaws/household/scene_camera_comparison.py`.
- `scripts/genesis_cleanup/genesis_backend_worker.py`.
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`.

Useful evidence:

- `genesis_movable_object_crops/`.
- `render_domain_source_diagnostics`.
- `render_domain_view_triage`.
- `visual_diagnostics`.
- MolmoSpaces material conversion files under `vendors/molmospaces/...`.

Do not read unless needed:

- Old reports before `0605_1656`.
- Broad `.planning/` history.
- Unrelated cleanup task reports.

### Definition Of Done / Acceptance Criteria

SUCCESS only if:

- 10-object sample is listed with rationale.
- Each object has backend crop comparison metrics or material-binding evidence.
- Report says whether material or light/tone is the higher-value next target.
- Recommendation avoids per-object hacks.

PARTIAL if:

- Crop visual evidence works but material metadata is not extractable.

BLOCKED_NEEDS_DECISION if:

- A fresh GPU rerun is required to get missing material/render diagnostics.

Must not regress:

- `scene_light_rig_v1` shared lighting abstraction.
- Current successful compare report path.
- Default lighting behavior.

### Verification

- Run the diagnostic against `0605_1656`.
- If code is added, run focused tests for object selection/material diagnostic.
- No commit unless requested after reviewing output.

## Execution Notes

Execution starts from current HEAD and existing report artifacts. This diagnostic
is evidence-only unless it proves a concrete source change is needed.

## Findings

**Report source:** `output/molmo/scene-camera-comparison/0605_scene_light_report_rerun/0605_1656/`

The latest report already proves the shared light rig is present and aligned:

- `lighting_tone_provenance.missing_environment_light_lanes == []`;
- `shadow_parity_probe.key_light_direction.status == "key_light_direction_aligned"`;
- `backend_swap_geometry_contract.geometry_contract_status == "pass"`;
- `shadow_parity_probe.status == "shadow_capable_profile_accepted"`.

The remaining visual residual is not a single global light-direction problem.
The report classifies it as `view_dependent_render_domain_delta` and points the
highest residual views at `object_material_texture_binding_contract`.

### 10-Object Sample

Sample selection used existing in-frame crop artifacts. The sample covers the
highest residual dining-table/bed views plus room-3 sink evidence, and includes
textured, flat-diffuse, fabric, paper, plastic, electronics, cardboard, and
round/sports objects.

| Object | View | Rationale | MuJoCo Y | Isaac deltaY / MAD | Genesis deltaY / MAD | Signal |
| --- | --- | --- | ---: | ---: | ---: | --- |
| BasketBall | `view_03_diningtable` | sports/round textured | 133.4 | -52.9 / 53.4 | -53.1 / 50.3 | shared brightness/tone drift |
| Box | `view_03_diningtable` | cardboard/articulated | 153.4 | -60.8 / 61.1 | -54.0 / 51.6 | shared brightness/tone drift |
| CellPhone | `view_03_diningtable` | small electronics/screen | 155.7 | -61.6 / 61.7 | -46.9 / 45.1 | shared brightness/tone drift |
| Pen | `view_03_diningtable` | small plastic | 135.0 | -40.8 / 41.6 | -50.5 / 46.8 | shared brightness/tone drift |
| RemoteControl | `view_03_diningtable` | black plastic/electronics | 144.8 | -42.2 / 42.9 | -56.7 / 53.3 | shared brightness/tone drift |
| AlarmClock | `view_02_bed` | metal/readout | 119.3 | -34.1 / 39.3 | -27.4 / 35.4 | shared brightness/tone drift |
| Pillow | `view_02_bed` | fabric/soft | 104.4 | -15.6 / 39.4 | -17.9 / 42.1 | backend-specific tone/material residual |
| Cloth | `view_04_sink` | fabric/cloth | 83.2 | -0.3 / 47.4 | +3.3 / 40.9 | material/texture or local shadow residual |
| SprayBottle | `view_04_sink` | plastic/bottle | 85.4 | -0.8 / 47.6 | +3.1 / 41.7 | material/texture or local shadow residual |
| ToiletPaper | `view_04_sink` | paper/white-or-brown | 81.4 | +2.1 / 46.4 | +5.2 / 40.8 | material/texture or local shadow residual |

Aggregate sample metrics:

- Mean Isaac absolute luminance delta: `31.13`.
- Mean Genesis absolute luminance delta: `31.81`.
- Mean Isaac crop MAD: `48.10`.
- Mean Genesis crop MAD: `44.81`.
- High-MAD objects: Isaac `6/10`, Genesis `5/10`.

### Material Evidence

Genesis materialized OBJ/MTL output provides concrete material and texture
evidence for sampled objects:

| Object | Genesis materialized material evidence | Texture evidence | Diffuse evidence |
| --- | --- | --- | --- |
| BasketBall | `material_BasketBall_BASKETBALL_AlbedoTransparency` | `textures/BasketBall_BASKETBALL_AlbedoTransparency_baked_08249657.png` | `Kd 1.0 1.0 1.0` |
| Box | `material_Cardboard_Mat1` | `textures/Cardboard_AlbedoTransparency_baked_825a8e5c.png` | `Kd 1.0 1.0 1.0` |
| CellPhone | `material_Cellphone_Screen_Off_Mat`, `material_Cellphone_1B_Mat` | `textures/Cellphone_1B_AlbedoTransparency.png` | screen `Kd 0.0 0.0 0.0`; body `Kd 1.0 1.0 1.0` |
| Pen | `material_PensPencils_DefaultMaterial_AlbedoTransparency` | `textures/PensPencils_DefaultMaterial_AlbedoTransparency.png` | `Kd 1.0 1.0 1.0` |
| RemoteControl | `material_Remote_Secondary_Mat`, `material_BlackPlastic_2` | `textures/Remote_Secondary_AlbedoTransparency.png` | black plastic `Kd 0.198529 0.198529 0.198529` |
| AlarmClock | `material_Alarm_Clock_Metal_Mat`, `material_Alarm_Clock_Readout3_Mat`, `material_Alarm_Clock_Primary2_Mat` | `textures/BrushedIron_AlbedoTransparency_baked_37d7d7a1.png`, `textures/Alarm_Clock_Readout3_AlbedoTransparency.png` | primary `Kd 0.477941 0.324913 0.207342` |
| Pillow | `material_Pillow14_Mat` | none | `Kd 0.298039 0.125490 0.376471` |
| Cloth | `material_Cloth_8_Mat` | `textures/Cloth1AO_baked_c92e8d98.png` | `Kd 1.0 1.0 1.0` |
| SprayBottle | `material_SprayBottle1_varA` | `textures/SprayBottle1_DefaultMaterial_AlbedoTransparency.png` | `Kd 1.0 1.0 1.0` |
| ToiletPaper | `material_BrownPaper` | none | `Kd 0.705882 0.443635 0.207612` |

Isaac backend state exposes broad object indexes for these objects, but only
selected cleanup bindings include detailed selected prim rows in this artifact.
For this 10-object diagnostic, the current evidence is therefore crop metrics
plus materialized Genesis OBJ/MTL material names/textures, not a full per-object
MuJoCo-MJCF-to-Isaac-PreviewSurface binding table.

## Diagnostic Conclusion

**Conclusion:** `mixed`, with material/texture response as the higher-value next
slice before any further default light tuning.

The evidence splits into two patterns:

1. Dining-table and bed crops show shared negative luminance deltas in both
   Isaac and Genesis versus MuJoCo. This is a view/room response problem, so a
   small backend light/tone sweep may still be useful later.
2. Room-3 sink crops have near-zero luminance deltas but high crop MAD. That is
   not explained by global exposure or key-light direction. It points at
   material/texture, local shadow, texture filtering, or color-space response.

Because both patterns exist, tuning one global lighting number is likely to
overfit. The next practical slice should make the material conversion boundary
explicit before changing defaults.

## Recommended Next Slice

Add a material-response diagnostic for the scene-camera comparison that records
per-sampled-object material evidence across backend adapters:

- MuJoCo: MJCF material name, RGBA, texture path, specular/shininess when
  available.
- Isaac: USD prim path, bound `UsdShade` material, PreviewSurface diffuse input,
  diffuse texture input, roughness/specular mapping, texture binding warnings.
- Genesis: materialized OBJ material name, MTL `Kd`, `map_Kd`, baked texture
  path, and whether the material came from a baked texture or flat diffuse.

Keep `scene_light_rig_v1` unchanged while this runs. If material evidence is
clean across a broader sample, then run a controlled backend light/tone sweep
with acceptance based on held-out views rather than manual screenshot taste.

## Implementation

Implemented in the existing scene-camera comparison path:

- Added `material_response_diagnostics` to the comparison manifest.
- Added a `Material Response Diagnostics` section to `report.html`.
- The diagnostic samples up to 10 crop-backed movable objects from
  `genesis_movable_object_visibility_diagnostics.crop_artifacts`.
- For each sampled object, it records:
  - crop luminance and mean-absolute RGB deltas from MuJoCo to Isaac/Genesis;
  - MuJoCo MJCF material/texture evidence via the existing scene XML parser;
  - Isaac USDA material binding and PreviewSurface texture evidence via the
    existing scene USD parser;
  - Genesis materialized OBJ/MTL material, `Kd`, and `map_Kd` evidence.
- The diagnostic classifies each object signal and emits a top-level
  conclusion: `material_issue`, `light_tone_issue`, `mixed`, or
  `insufficient_evidence`.

Implementation boundaries preserved:

- No changes to `scene_light_rig_v1`.
- No changes to default lighting, tone, exposure, camera geometry, or backend
  render-worker behavior.
- No per-object/per-view correction tables.

## Verification

- Read latest report manifest and backend state artifacts.
- Computed 10-object crop luminance and mean-absolute RGB deltas from existing
  crop images.
- Extracted materialized Genesis material/texture evidence from:
  `genesis/camera_views/prepared_usd_visual_asset/prepared_usd_visual_asset.mtl`
  and nearby OBJ `usemtl` sections.
- No runtime defaults, lighting profiles, or backend renderer code changed.
- Added CI-safe synthetic tests for:
  - material-response object sampling and material evidence extraction;
  - report rendering of the material-response section.
- Focused verification:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_scene_camera_comparison.py -k "material_response_diagnostics"`
  passed.
- Final focused closeout:
  `ruff check roboclaws/household/scene_camera_comparison.py tests/contract/molmo_cleanup/test_scene_camera_comparison.py`
  passed.
- Final focused closeout:
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_scene_camera_comparison.py -k "material_response_diagnostics or render_domain_contract or render_domain_view_triage or lighting or shadow_parity or scene_light_rig"`
  passed.

## 2026-06-05 Default-Setting Gate

After implementation, refreshed the real comparison report in place:

`output/molmo/scene-camera-comparison/0605_scene_light_report_rerun/0605_1656/`

The refreshed `material_response_diagnostics` result is:

- `status == "computed"`
- `sample_count == 10`
- `conclusion == "mixed"`
- `material_like_signal_count == 1`
- `shared_brightness_tone_signal_count == 6`
- MuJoCo, Isaac, and Genesis material parsers all reported `parsed`.

Object-level split:

- Shared brightness/tone drift:
  AlarmClock, BasketBall, Box, CellPhone, GarbageCan, Pen.
- Backend tone residual:
  Pillow, BaseballBat, Bowl.
- Material/texture or local-shadow residual:
  Cloth.

Decision:

- Do not promote a new default light/tone/exposure setting from this evidence.
- Do not run a held-out light/tone sweep yet; the precondition from this plan
  was "only if material evidence is clean", and the refreshed report still has
  a material/local-shadow residual.
- Keep `scene_light_rig_v1` as the default light abstraction for now.
- The next default-improving slice should inspect material/local-shadow response
  for the Cloth/sink residual and the BaseballBat Genesis material-name miss
  before changing global backend light or exposure defaults.

# MuJoCo Isaac Camera Visual Parity

Owner/session: Codex local
Started: 2026-06-02 16:30 Asia/Shanghai
State: active

## Scope

Make MolmoSpaces MuJoCo and Isaac Sim cleanup robot-view evidence use alike FPV
camera geometry and move visual results as close as practical. FPV must remain
the real robot-mounted head camera; chase camera is auxiliary report evidence.

## Source Of Truth

- Current root commit before latest four-check audit:
  `8388410d feat: probe intermediate texture scale response`
- Four-check summary:
  `output/molmo/robot-camera-apple2apple/0602_visual_parity_summary/visual_parity_summary.json`
- Four-check report:
  `output/molmo/robot-camera-apple2apple/0602_visual_parity_summary/report.html`
- Earlier root commit before this note:
  `5f682eb9 feat: probe targeted diffuse texture material response`
- Camera FOV fix commit: `b5e2be3d fix: align isaac head camera fov`
- Report: `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_headpitch_lightingfix_scene_refs_fix/report.html`
- Color/tone probe:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_global_rgb_gain_probe/report.html`
- FOV fix probes:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_4loc_fovfix_baseline/report.html`
  and
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_4loc_fovfix_baseline/report.html`
- 8-location post-FOV baseline:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_fovfix_baseline/report.html`
- 8-location post-FOV RGB-gain probe:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_fovfix_val0_rgb_gain_probe/report.html`

## Current Evidence

- `val_0` scene-referenced USD assets are complete:
  `/tmp/val0_scene_missing_refs_after_install.json` has
  `scene_missing_referenced_asset_count=0`.
- Prepared semantic USD is ready:
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix/summary.json`
  has `matched_entry_count=139`, `missing_prim_count=0`,
  and `renderable_labeled_prim_count=3357`.
- Earlier 8-location apple2apple report passed with
  `fpv_contract_shared_with_static_head_camera_pitch_correction`,
  `fpv_world_pose_aligned`, FPV position delta avg/max `0.005m`,
  and `target_contract_delta_counts={"material_texture_names_match": 8}`.
- That report still had a hidden FPV lens/intrinsics gap: Isaac recorded
  `focal_length_mm=24` and `horizontal_aperture_mm=20.955`, which is about
  `32.45deg` vertical FOV at `540x360`, while MuJoCo `robot_0/head_camera`
  reports `fovy_deg=45`. Contact-sheet inspection made this visible as Isaac
  appearing zoomed-in/too narrow even when world position was aligned.
- Isaac robot-view capture now rewrites the mounted `/World/robot_0/head_camera`
  lens from the MuJoCo vertical FOV per render resolution and reports
  `fpv_lens_delta_summary.status=fpv_lens_aligned`.
- FOV fix validation:
  - `val_0`, seed-6, first 4 locations:
    old first-4 FPV avg was about `51.24`; FOV-fix FPV avg is `39.1959`.
  - `val_0`, seed-6, 8 locations:
    FPV avg improved from `46.7762` to `38.0980`, with
    `fpv_lens_delta_summary.status=fpv_lens_aligned`,
    `fpv_world_pose_delta_summary.status=fpv_world_pose_aligned`,
    and `fpv_lens_gap_count=0`.
  - `val_1`, seed-6, 2 mess / 4 locations:
    FPV avg improved from `49.9412` to `37.2460`.
  - `val_1` FOV fix plus the old `val_0` RGB gain profile improved FPV further
    to `35.4960`, but this is now a smaller tone-calibration layer, not the
    primary camera-angle fix.
- Post-FOV `val_0` residual split is now specific: 2 low-residual FPV views,
  2 view-dependent color residuals, and 4 geometry/texture edge residuals.
  The worst remaining points still have exact public USD binding, zero missing
  referenced assets, and `material_texture_names_match`, so the next root-cause
  class is renderer/material/texture response rather than camera geometry.
- The refreshed 8-location post-FOV baseline now emits
  `summary.render_domain_checks` with four explicit checks:
  `light_shadow_contract_delta=1`,
  `texture_basenames_match_paths_or_colorspace_unverified=1`,
  `usd_preview_surface_vs_mujoco_material_model_delta=1`, and
  `tone_color_delta_rgb_oracle=1`. This keeps camera parity separate from
  render-domain parity in the report itself.
- The same baseline now expands the `texture_colorspace_material_response`
  check with high-residual target summaries. It reports
  `material_response_status_counts={"texture_path_or_colorspace_unverified": 8}`,
  `high_residual_target_count=6`, `texture_path_full_delta_count=8`,
  `rgba_diffuse_color_mismatch_count=7`, and `texture_backing_mismatch_count=0`.
  The reported `0008`
  `diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2` target still has
  exact public USD binding, zero missing referenced assets, matching
  `LightWoodCounters.png` texture basename, and `material_texture_names_match`,
  but the full texture path/source differs, MuJoCo contributes one RGBA visual
  while Isaac contributes no USD diffuseColor binding, and FPV luminance is
  MuJoCo `88.026` vs Isaac `131.0136`. This supports a texture
  source/colorspace/material-response cause for the visibly pale Isaac table
  rather than another FPV camera-angle change.
- The baseline also now expands the `usd_preview_surface_material_model` check
  with high-residual target summaries and parsed PreviewSurface inputs. For
  `0008`, MuJoCo and Isaac both expose `material_LightWoodCounters3` with the
  same RGBA/texture scale numbers `[0.698113, 0.339363, 0.135012, 1]`, but
  Isaac renders it through a USD texture shader with `sourceColorSpace=auto`,
  `wrapS/wrapT=repeat`, `roughness=0.5`, `opacity=1`, and `metallic=0`. Across
  the 8-location baseline, parsed PreviewSurface input counts are
  `metallic=20`, `opacity=20`, and `roughness=20`. This narrows the next
  material-model probe toward USD texture colorspace/sampler and
  PreviewSurface-vs-MJCF response rather than material identity or camera pose.
- A comparison-only material-response USD variant is prepared at
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix_material_raw_roughness1/scene_semantic.usda`.
  Its summary reports `source_color_space_rewrite_count=179`,
  `roughness_rewrite_count=340`, `total_rewrite_count=519`, and
  `scene_metadata_copied=true`. The source stage remains unchanged. This probe
  rewrites USD texture `sourceColorSpace` to `raw` and PreviewSurface
  `roughness` to `1.0` to test whether that combined material-response
  direction improves FPV residuals.
- The material-response probe has now run at
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_4loc_material_raw_roughness1_probe/report.html`.
  It preserved the shared head-camera contract (`fpv_lens_aligned`,
  `fpv_world_pose_aligned`) but worsened FPV mean-abs-RGB from the comparable
  post-FOV baseline `38.0980` to `45.4954` (`+7.3974`). Chase improved from
  `83.7516` to `72.5027`, but chase is auxiliary report evidence rather than
  the policy/input camera. The refreshed 8-location baseline report now attaches
  this probe under
  `summary.render_domain_checks.checks[usd_preview_surface_material_model].probe_history`
  with `schema=robot_camera_material_response_probe_history_v1`,
  `status=prior_probes_worse`, `comparable_probe_count=1`, and
  `worsened_probe_count=1`. Do not promote the combined
  `sourceColorSpace=raw` plus `roughness=1.0` edit as a default.
- The split material-response probes narrow that result. The raw-only variant
  (`sourceColorSpace=raw`, roughness unchanged) at
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_4loc_material_raw_only_probe/report.html`
  worsened 4-location FPV from `39.1959` to `46.9881` (`+7.7922`) while
  improving chase; treat raw texture colorspace as negative FPV evidence, not a
  default. The roughness-only 4-location variant at
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_4loc_material_roughness1_only_probe/report.html`
  changed FPV from `39.1959` to `38.8417` (`-0.3542`) and worsened chase from
  `82.3657` to `88.7648`; this is below the report's `>1.0` FPV improvement
  threshold. The 8-location roughness-only variant at
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_material_roughness1_only_probe/report.html`
  changed FPV from `38.0980` to `37.5747` (`-0.5233`) and worsened chase from
  `83.7516` to `90.6459`. For the user-flagged `0008` dining table, roughness
  lowered FPV from `45.4961` to `44.3709` (`-1.1252`) and Isaac luminance from
  `131.0136` to `129.7169`, but the object remains a high residual
  `view_dependent_color_residual`. The refreshed 8-location baseline now
  attaches all four material probes with `comparable_probe_count=4`,
  `worsened_probe_count=2`, and `neutral_probe_count=2`.
- A target-specific `0008` dining-table roughness probe is now reproducible via
  `scripts/isaac_lab_cleanup/make_molmospaces_material_response_probe_usd.py`
  with `--material-path-contains`. The prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix_0008_lightwood_roughness1/scene_semantic.usda`
  rewrites only one material block:
  `/val_0/Geometry/diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2/Materials/material_LightWoodCounters3`,
  with `matched_material_block_count=1` and `roughness_rewrite_count=1`.
  The corresponding 8-location report at
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_0008_lightwood_roughness1_probe/report.html`
  is effectively neutral: overall FPV changes from `38.0980` to `38.0044`
  (`-0.0936`), chase is unchanged (`83.7516` to `83.7508`), and `0008` improves
  only from `45.4961` to `44.8164` (`-0.6797`) while remaining a high residual
  `view_dependent_color_residual`. The refreshed baseline report now attaches
  all five material probes with `comparable_probe_count=5`,
  `worsened_probe_count=2`, and `neutral_probe_count=3`.
- The refreshed 8-location post-FOV RGB-gain probe improved FPV avg from
  `38.0980` to `35.0612` and changed the residual split to 4 low-residual FPV
  views, 3 geometry/texture edge residuals, and 1 render-domain residual. Its
  `tone_color_response` check reports
  `tone_color_delta_remaining_after_comparison_gain` with comparison RGB gain
  applied and an FPV RGB-oracle improvement fraction of `0.143278`. RGB gain is
  still comparison-only because light/shadow, texture/colorspace, and
  PreviewSurface-vs-MJCF material-model checks remain active.
- The refreshed 8-location post-FOV baseline report now attaches that same
  `val_0` RGB-gain probe into
  `summary.render_domain_checks.checks[tone_color_response].probe_history`.
  The tone/color history reports `schema=robot_camera_tone_color_probe_history_v1`,
  `status=prior_probe_improved`, `comparable_probe_count=1`,
  `improved_probe_count=1`, and FPV delta `-3.0368` with
  `backend_rgb_gain.isaaclab_subprocess=[0.944061,0.844818,0.822146]`. This made
  RGB/tone calibration the strongest `val_0` comparison-only render-domain
  direction, but not a default renderer or policy-input change.
- The same tone/color report path now also covers the existing `val_1` post-FOV
  2-mess / 4-location corpus. Refreshing
  `0602_val1_seed6_2mess_4loc_fovfix_baseline` with its same-scene
  `val0_rgb_gain_probe` records `status=prior_probe_improved`,
  `comparable_probe_count=1`, `improved_probe_count=1`, and FPV delta `-1.75`
  while preserving `fpv_lens_aligned` and `fpv_world_pose_aligned`. This is a
  second-scene positive signal for the `val_0` RGB gain profile, but still small
  enough that the next decision is broader corpus validation rather than default
  promotion.
- The first `val_1` 8-location broadening attempt exposed a target-selection
  artifact rather than a new camera problem: only 6 targets in the requested
  pool had Isaac USD binding evidence, while 4 ordinary object targets had no
  binding and were counted as `missing_object_binding_evidence`. The comparison
  runner now records `target_selection` and filters to targets both backends can
  bind. The fair `0602_val1_seed6_2mess_8loc_fovfix_bound_baseline` run
  requested 8 locations, selected 6 bound targets, dropped 19 unbound candidates,
  preserved `fpv_lens_aligned` and `fpv_world_pose_aligned`, and removed the
  spurious missing-binding blocker. Its real remaining target delta is
  `material_texture_names_match=5` and `material_or_texture_name_delta=1`
  (the selected pillow texture contract).
- On that fair bound-target `val_1` 6-location slice, the same `val_0` RGB gain
  profile is again FPV-positive: baseline FPV avg `36.5655`, RGB-gain probe
  `34.5577`, delta `-2.0078`, with
  `tone_color_response.probe_history.status=prior_probe_improved`. Chase worsens
  slightly (`+1.0939`), so RGB gain remains comparison-only and FPV-focused, but
  the earlier unfiltered `-0.7708` weak-signal result should not drive the next
  decision.
- A targeted comparison-only pillow texture probe now tests the remaining
  selected-object material delta. The prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_1_pillow_texture_probe/scene_semantic.usda`
  injects one `UsdUVTexture` connection for
  `/val_1/Geometry/pillow_874c097332ffacf84f31fb77733db15c_1_0_2/Materials/material_Pillow14_Mat`
  using `PillowD_AO.png`. It changes the fair bound-target report from
  `material_or_texture_name_delta=1` to `material_texture_names_match=6`, but
  does not improve FPV: baseline `36.5655`, probe `36.6877` (`+0.1222`). The
  refreshed baseline records this material probe as `prior_probes_no_fpv_gain`
  with `neutral_probe_count=1`. Do not promote the pillow texture injection as a
  default; it narrows the cause from missing texture binding to renderer
  material/tone/light response.
- The combined pillow texture plus `val_0` RGB-gain probe ran at
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_pillow_texture_rgb_gain_probe/report.html`.
  It keeps all 6 selected target material/texture names matched and lowers FPV
  versus baseline (`36.5655` to `34.6180`), but it is slightly worse than the
  RGB-only probe (`34.5577`). Treat this as evidence that the global RGB/tone
  layer is the useful part of that combination; the pillow texture injection
  still should not become a default.
- A comparison-only light/shadow USD variant generator now exists at
  `scripts/isaac_lab_cleanup/make_molmospaces_light_shadow_probe_usd.py`, matching
  the material-probe pattern: it copies the prepared USD, writes a summary, and
  leaves default cleanup rendering unchanged. The `val_1` fair bound-target slice
  now has direct light/shadow probes instead of relying only on `val_0` history:
  `output/isaaclab/flattened-semantic-usd/val_1_no_dome_only/summary.json`
  removes 1 DomeLight, and
  `output/isaaclab/flattened-semantic-usd/val_1_no_shadow_only/summary.json`
  rewrites 18 `primvars:doNotCastShadows` flags.
- The corresponding `val_1` fair bound-target reports preserve
  `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the head-camera contract:
  no-dome-only
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_no_dome_only_probe/report.html`
  changes FPV from `36.5655` to `35.8084` (`-0.7571`) but worsens chase from
  `72.2838` to `80.4852`; no-shadow-only
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_no_shadow_only_probe/report.html`
  changes FPV to `36.1211` (`-0.4444`) with chase effectively neutral
  (`72.3379`). The refreshed fair bound baseline records both under
  `light_shadow_contract.probe_history.status=prior_probes_no_fpv_gain` with
  `comparable_probe_count=2`, `improved_probe_count=0`, and
  `worsened_probe_count=0`. Do not promote simple DomeLight removal or shadow
  enabling as defaults from this evidence.
- A light/tone interaction probe also ran at
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_no_dome_rgb_gain_probe/report.html`.
  It uses the same `val_0` RGB gain profile on the no-dome USD and produces FPV
  `36.0175`, far worse than RGB-only `34.5577`, while chase worsens to
  `82.9606`. This keeps the useful signal attributed to RGB/tone calibration,
  not to light-count matching or no-dome-plus-RGB interaction.
- A reproducible comparison-only RGB-gain profile builder now exists at
  `scripts/molmo_cleanup/make_robot_camera_rgb_gain_profile.py`. It reads an
  apple-to-apple manifest, fits a global least-squares RGB gain from FPV image
  pairs, and writes a color-profile override for probe runs only. On the fair
  `val_1` bound-target baseline it writes
  `output/molmo/robot-camera-apple2apple/profiles/0602_val1_seed6_2mess_bound_global_fpv_rgb_gain.json`
  with `backend_rgb_gain.isaaclab_subprocess=[0.972399,0.876524,0.869175]`
  from 6 FPV pairs.
- The corresponding `val_1` self-fit RGB probe ran at
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_val1_self_rgb_gain_probe/report.html`.
  It preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the
  head-camera contract, and lowers FPV from `36.5655` to `34.5828`
  (`-1.9827`). That is effectively tied with, but slightly worse than, the
  cross-scene `val_0` RGB profile result `34.5577` (`-2.0078`); chase is less
  degraded with the `val_1` self-fit profile (`72.8632` vs `73.3777`). This
  strengthens RGB/tone as a robust comparison-only direction, but it does not
  prove a default renderer calibration because the profile was fit and evaluated
  on the same 6-view slice.
- A real Isaac `camera-raw` / RAW_FPV direct cleanup probe now covers the
  agent-input lane that the render-only apple2apple report does not exercise:
  `output/isaaclab/cleanup-smoke/0602_val1_seed6_2mess_camera_raw_direct_probe_visibilityfix/report.html`.
  It used `backend=isaaclab_subprocess`, `cleanup_profile=camera-raw`,
  `perception_mode=raw_fpv_only`, `scene_index=1`, seed `6`, and 2 generated
  mess objects against the prepared `val_1` USD. The strict checker passed with
  `--require-raw-fpv-observations`, `--require-model-declared-observations`,
  `--require-isaac-real-runtime`, `--require-isaac-scene-index-map-context`,
  and `--require-robot-head-camera-fpv`. The run records 6 RAW_FPV
  observations, 2 model-declared observations, 2/2 restored objects,
  `primitive_provenance=isaac_semantic_pose`, and
  `robot_view_camera_control.status=all_robot_views_use_head_camera_fpv` with
  16/16 head-camera robot-view steps. Focus visibility is now honestly recorded
  as `segmentation_unavailable` for Isaac semantic-pose robot views instead of
  being omitted.
- Remaining blocker is visual render-domain parity:
  `render_contract_diagnostics.status=lighting_shadow_contract_delta`,
  MuJoCo lights `1`, Isaac lights `2`, Isaac shadow-disabled prims `44` on
  `val_0` and `18` on `val_1`. Chase remains much less comparable because it is
  auxiliary report evidence rather than the policy/input camera contract.
- A combined MuJoCo-like light/shadow USD probe removed the contract delta but
  made visual error worse: FPV avg `50.8161`, chase avg `114.0763`.
  Do not turn that combined probe into the default.
- The refreshed 8-location post-FOV baseline now attaches three prior
  light/shadow probe manifests into
  `summary.render_domain_checks.checks[light_shadow_contract].probe_history`.
  All three are comparable to the current camera contract and made FPV worse:
  no-dome-only `+11.6197`, no-shadow-only `+11.6982`, and MuJoCo-like
  light+shadow `+12.7181` mean-abs-RGB delta versus the current FOV baseline.
  This rules out promoting simple dome removal, shadow enabling, or the old
  combined MuJoCo-like light/shadow USD edit as a default.
- A comparison-only global Isaac RGB gain probe improved real re-rendered FPV
  from `46.7762` to `43.4240` while preserving the head-camera contract and
  `0.005m` FPV pose delta. The profile used
  `backend_rgb_gain.isaaclab_subprocess=[0.944061,0.844818,0.822146]` from the
  `val_0`/seed-6 FPV least-squares fit. This is evidence that tone/color
  response is a real direction, but it is not yet broad enough for a default
  cleanup rendering calibration.
- A read-only visual-parity summary gate now exists at
  `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`. It folds the
  current post-FOV baselines, RGB/tone probes, light/material probes, and the
  RAW_FPV cleanup run into
  `output/molmo/robot-camera-apple2apple/0602_visual_parity_summary/report.html`.
  The current summary status is `active`, not complete: head-camera geometry is
  aligned, RAW_FPV agent input uses the head camera, RGB/tone is positive but
  still comparison-only, light/material probes are neutral/do-not-promote, corpus
  coverage is only 2 scene signatures / 1 seed, and a root-visible calibration
  artifact is required before any RGB/luminance gain can become default cleanup
  rendering behavior.
- The root-visible calibration-scene report now exists at
  `output/molmo/scene-camera-comparison/0602_val0_scene_refs_calibration/report.html`.
  Refreshing the visual-parity summary with that manifest changes
  `calibration_scene.status` to `calibration_scene_evidence_loaded`. Its
  calibration result is `view_dependent_render_domain_delta` with global Isaac
  scene-level luminance gain `1.0595`, mean calibrated luminance residual
  `14.8384`, and only about `5.7%` mean luminance-delta improvement from the
  original per-view gap. The residual stays view-dependent, so this is stronger
  evidence that the remaining visual gap is per-room light/material/tone
  response rather than camera geometry or one global brightness scale.
- A held-out seed slice now covers `val_1`, seed `8`, 2 mess objects, and 4
  bound targets:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed8_2mess_4loc_fovfix_bound_baseline/report.html`.
  It preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the
  head-camera contract, with FPV `37.2184`. Applying the existing `val_0`
  RGB-gain profile in
  `output/molmo/robot-camera-apple2apple/0602_val1_seed8_2mess_4loc_fovfix_bound_val0_rgb_gain_probe/report.html`
  lowers FPV to `35.5147` (`-1.7037`) while chase improves slightly from
  `71.7464` to `71.0975`. Refreshing the visual-parity summary with this seed
  slice makes the corpus foundation pass (`3` scene signatures, `2` seeds, `18`
  successful locations), but the overall summary stays `active` because
  render-domain residuals remain and RGB/tone is still comparison-only.
- A comparison-only `sourceColorSpace=sRGB` material probe now covers the same
  held-out seed-8 slice. The prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_1_material_srgb_only/scene_semantic.usda`
  rewrites 53 texture sourceColorSpace tokens and leaves default rendering
  unchanged. The corresponding report
  `output/molmo/robot-camera-apple2apple/0602_val1_seed8_2mess_4loc_fovfix_bound_material_srgb_probe/report.html`
  preserves the head-camera contract but does not improve FPV: baseline
  `37.2184`, sRGB probe `37.3884` (`+0.1700`). The refreshed summary now records
  this under material probes as neutral/do-not-promote, alongside pillow texture,
  roughness-only, and target-specific LightWood roughness probes.
- A target-specific texture scale/fallback probe now explains the user-flagged
  `0008` dining-table residual much better than camera or roughness changes.
  The generator supports comparison-only `--texture-scale-mode square`, and the
  prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix_0008_lightwood_scale_square/scene_semantic.usda`
  rewrites only the two `UsdUVTexture` scale/fallback inputs for
  `/val_0/Geometry/diningtable_f113cf7f8367e89f709b53cbee1a1c05_1_0_2/Materials/material_LightWoodCounters3`.
  The corresponding report
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_0008_lightwood_scale_square_probe/report.html`
  preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the head-camera
  contract while lowering overall FPV from `38.0980` to `35.8577` (`-2.2403`).
  The `0008` target itself drops from `45.4961` to `27.6042`, changes from
  `view_dependent_color_residual` to `low_residual`, and lowers Isaac FPV
  luminance from `131.0136` to `112.1958` against MuJoCo `88.0260`. This is the
  strongest target-specific material evidence so far that Isaac/MuJoCo visual
  mismatch includes USD texture scale/fallback versus MJCF RGBA/texture
  modulation response, not a camera-angle problem.
- A global comparison-only texture scale/fallback probe now strengthens that
  root-cause direction. The `val_0` prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix_material_scale_square/scene_semantic.usda`
  rewrites 358 `UsdUVTexture` scale/fallback inputs, and the corresponding
  report
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_material_scale_square_probe/report.html`
  preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the head-camera
  contract while lowering overall FPV from `38.0980` to `32.5266` (`-5.5714`).
  Per-target FPV improves on 7/8 locations, including `0008` from `45.4961` to
  `22.6553`, `0002` bed from `48.5167` to `36.2543`, and `0006` desk from
  `36.0030` to `30.6165`; countertop `0004` is the only small regression
  (`17.3423` to `18.4671`). Chase is effectively unchanged overall
  (`83.7516` to `83.7645`), which keeps chase auxiliary and prevents using it
  as the policy metric.
- A held-out `val_1`, seed-6, 2-mess, fair bound-target scale-square probe now
  covers the same conversion direction outside the original `val_0` slice. The
  prepared USD at
  `output/isaaclab/flattened-semantic-usd/val_1_material_scale_square/scene_semantic.usda`
  rewrites 106 texture scale/fallback inputs. The report
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_material_scale_square_probe/report.html`
  preserves the head-camera contract and lowers FPV from `36.5655` to
  `29.4056` (`-7.1599`), with all 6 bound targets non-worse or better. The
  largest FPV drops are bed `0001` from `47.4883` to `31.2545`, pillow `0006`
  from `42.0106` to `34.3779`, and dining table `0003` from `46.1260` to
  `37.5900`. Chase worsens from `72.2838` to `75.1952`, so this remains an
  FPV-only comparison probe, not a default visual policy.
- The same `val_1` scale-square USD now also covers the held-out seed-8
  4-location bound-target slice. The report
  `output/molmo/robot-camera-apple2apple/0602_val1_seed8_2mess_4loc_fovfix_bound_material_scale_square_probe/report.html`
  preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the head-camera
  contract while lowering FPV from `37.2184` to `29.5022` (`-7.7162`) and chase
  from `71.7464` to `71.2868` (`-0.4596`). Per-target FPV is non-worse or
  better across all 4 bound targets: bed `0001` drops from `47.5110` to
  `31.2138`, bed `0002` from `28.7929` to `22.7825`, dining table `0003` from
  `46.1325` to `37.5748`, and sink `0004` is effectively flat (`26.4371` to
  `26.4375`). This makes scale/fallback squaring the first material-response
  probe with positive FPV evidence across `val_0`, `val_1` seed-6, and
  `val_1` seed-8.
- The refreshed visual-parity summary at
  `output/molmo/robot-camera-apple2apple/0602_visual_parity_summary/report.html`
  now records `val0_global_scale_square` (`fpv_delta=-5.5714`),
  `val1_scale_square` (`fpv_delta=-7.1599`), and
  `val1_seed8_scale_square` (`fpv_delta=-7.7162`) plus maintained
  prepared-USD gates `val0_prepared_scale_square_gate` (`fpv_delta=-5.5750`),
  `val1_seed6_prepared_scale_square_gate` (`fpv_delta=-7.1603`), and
  `val1_seed8_prepared_scale_square_gate` (`fpv_delta=-7.7401`) under
  `material_response=has_fpv_gain_comparison_only`. The overall gate remains
  `active`: head-camera geometry, RAW_FPV input, corpus coverage, and
  calibration evidence are loaded, but render-domain residuals remain and RGB /
  material-response edits are still comparison-only.
- The prepared flattened semantic USD pipeline now has an explicit default-off
  material conversion gate:
  `scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py`
  accepts `--material-texture-scale-mode none|identity|square`, with `none` as
  the default. The summary records `material_texture_scale_mode`,
  `material_texture_scale_rewrite_count`, and
  `material_texture_scale_default_candidate`. Focused tests prove the default
  leaves `UsdUVTexture` scale/fallback inputs unchanged, while explicit
  `square` rewrites those inputs and labels the output as a default-candidate
  artifact. This makes future validation reproducible through the prepared-USD
  path without changing default cleanup rendering.
- A real `val_1` prepared-USD smoke of that new gate passed under the Isaac/USD
  Python environment:
  `output/isaaclab/flattened-semantic-usd/val_1_material_scale_square_prepared_gate/summary.json`
  reports `status=ready`, `material_texture_scale_mode=square`,
  `material_texture_scale_rewrite_count=106`,
  `material_texture_scale_default_candidate=true`, `matched_entry_count=40`,
  and `renderable_labeled_prim_count=817`. The rewrite count matches the prior
  ad hoc `val_1_material_scale_square` probe.
- The maintained prepared-USD gate now also has an apple-to-apple validation
  run for the `val_1` seed-8 bound-target slice:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed8_2mess_4loc_fovfix_bound_prepared_scale_square_gate_probe/report.html`.
  It preserves `fpv_lens_aligned`, `fpv_world_pose_aligned`, and the
  robot-mounted head-camera contract while lowering FPV from the comparable
  seed-8 baseline `37.2184` to `29.4783` (`-7.7401`). Chase moves from
  `71.7464` to `71.2846` (`-0.4618`). The first prepared-gate run looked like
  baseline because the texture scale rewrite happened before the final USD
  stage save and was overwritten by the layer cache; the prepare script now
  applies the opt-in rewrite after `flat_stage.GetRootLayer().Save()`, so the
  final `scene_semantic.usda` contains the squared `UsdUVTexture`
  scale/fallback values used by the report.
- The maintained prepared-USD path now also reproduces the ad hoc scale-square
  result on the `val_1` seed-6 6-target bound slice:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_prepared_scale_square_gate_probe/report.html`.
  FPV moves from `36.5655` to `29.4052` (`-7.1603`), essentially matching the
  ad hoc `29.4056` result, while chase moves from `72.2838` to `75.1960`
  (`+2.9122`). This keeps the edit comparison-only, but confirms the prepared
  gate itself is not seed-8-specific.
- The maintained prepared-USD path now also covers `val_0` seed-6 8 locations.
  The prepared artifact
  `output/isaaclab/flattened-semantic-usd/val_0_material_scale_square_prepared_gate/summary.json`
  reports `status=ready`, `material_texture_scale_mode=square`,
  `material_texture_scale_rewrite_count=358`,
  `material_texture_scale_default_candidate=true`, `matched_entry_count=139`,
  and `renderable_labeled_prim_count=3357`. Its apple-to-apple report
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_prepared_scale_square_gate_probe/report.html`
  preserves the head-camera contract and lowers FPV from `38.0980` to
  `32.5230` (`-5.5750`), matching the ad hoc global scale-square result
  `32.5266`. Chase is effectively flat (`83.7516` to `83.7739`, `+0.0223`).
- The visual-parity summary now has an explicit machine-readable
  `prepared_scale_square_default_gate`. Current status is
  `comparison_only_not_default`: all 3 comparable prepared probes improve FPV,
  but the gate blocks default promotion on `chase_regression`
  (`val1_seed6_prepared_scale_square_gate`, tolerance `1.0`) and
  `render_domain_residuals_active`
  (`lighting_shadow_contract_delta`, `target_material_texture_or_binding_gap`).
- The refreshed summary now classifies that `val1_seed6` chase blocker instead
  of treating it as an opaque number. The paired-view diagnostics say
  `diagnostic_class=tone_luminance_side_effect`: FPV improves on 5/6 locations
  with zero FPV regressions and average FPV delta `-7.1603`, while chase edge
  residual is essentially unchanged (`edge_abs_diff_delta_avg=0.0163`) and the
  chase regression comes from luminance-gap shifts on high-luminance auxiliary
  views. The largest chase regressions are dining table `0003` (`+14.4875`),
  pillow `0006` (`+12.3877`), and bowl `0005` (`+6.9027`). Keep this as a
  default-promotion blocker until render residuals are resolved or the chase
  role is explicitly re-gated, but do not treat it as evidence of camera pose,
  lens, or USD geometry regression.
- A follow-up comparison-only material probe now tests whether the LightWood
  texture-scale response should sit between source values and full squaring.
  `scripts/isaac_lab_cleanup/make_molmospaces_material_response_probe_usd.py`
  accepts opt-in `--texture-scale-power`; the `val_1` target-specific artifact
  at
  `output/isaaclab/flattened-semantic-usd/val_1_diningtable_lightwood_scale_power15/summary.json`
  rewrites only the dining-table `material_LightWoodCounters3` texture
  scale/fallback inputs with `power=1.5`. Its apple-to-apple report
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_diningtable_lightwood_scale_power15_probe/report.html`
  preserves the head-camera contract and leaves chase effectively unchanged
  (`72.2838` to `72.2828`). It improves the dining table FPV from `46.1260` to
  `40.9925`, but this is weaker than full scale-square (`37.5939`) and overall
  FPV only reaches `35.1698`, far behind global/prepared scale-square
  (`29.4052`). Treat `power=1.5` as useful calibration evidence, not a default
  candidate or replacement for the stronger scale-square corpus.

## Next Action

Keep FPV pose and the head-camera FOV contract unchanged. Do not promote global
raw colorspace, combined raw+roughness, global roughness-only, or the `0008`
target-specific roughness edit as defaults from the current evidence. Keep RGB
gain comparison-only: it improves FPV on `val_0`, `val_1` 4-location, and the
fair bound-target `val_1` 6-location slice, but chase can move the other way and
render-domain material checks remain active. The combined pillow texture plus
RGB-gain probe does not beat RGB-only, so texture-binding cleanup is lower
priority than tone/light/material-response work. The next highest-value
render-domain slice is the high-residual exact-bound bed/table/pillow material
response on the fair `val_1` bound-target report, plus RGB/tone interaction on
that same fair target set. For light/shadow specifically, `val_1` now also says
simple dome removal and shadow enabling are neutral/small and no-dome-plus-RGB is
worse than RGB-only; do not retry simple dome removal, shadow enabling, or the
old combined MuJoCo-like light/shadow USD edit. If light/shadow remains the next
slice, make it a comparison-only intensity/direction probe with a clear FPV
threshold. Keep RAW_FPV and world-labels as separate evidence lanes:
world-labels uses images as report evidence only, while camera-raw uses the
head-camera FPV images as agent input.
The next proof-backed step is not more camera work. Keep the calibration report
attached to the summary gate; do not promote any RGB/luminance gain to default
rendering while the calibration result remains view-dependent. Texture
scale/fallback squaring is now the strongest material-response direction, with
positive FPV evidence on `val_0`, held-out `val_1` seed-6, held-out `val_1`
seed-8 bound targets, and maintained prepared-USD reproductions for all three
of those slices. It is still comparison-only because chase worsens on `val_1`
seed-6 and render-domain residuals remain. The `power=1.5` LightWood probe shows
that intermediate scale power can avoid the chase side effect for a targeted
material, but it gives up too much FPV gain to replace full scale-square. The
next useful slice is either a broader prepared-USD
`--material-texture-scale-mode square` default-promotion gate across additional
scenes/targets, or a targeted material-modulation probe that preserves global
scale-square FPV gains while reducing the auxiliary chase luminance side effect.
The summary gate already encodes the current blockers, so future runs should
drive `prepared_scale_square_default_gate` instead of relying on manual report
notes.

## Four-Check Audit 2026-06-02

The current machine-readable summary says the four requested checks are split
cleanly:

- Camera geometry: `head_camera_contract.status=head_camera_geometry_aligned`.
  The active FPV contract is frozen on the robot-mounted head camera, not a
  chase or report-only camera. MuJoCo remains `robot_0/head_camera`; Isaac
  remains `/World/robot_0/head_camera`.
- RAW_FPV input lane:
  `raw_fpv_input_lane.status=raw_fpv_agent_input_uses_head_camera`. The
  `camera-raw` cleanup probe records `perception_mode=raw_fpv_only`,
  `camera_status=all_robot_views_use_head_camera_fpv`, 16 head-camera contract
  steps, and 6 RAW_FPV observations. World-label images remain report evidence,
  not the policy/input lane.
- Material/texture response:
  `render_domain_probe_matrix.status=render_domain_delta_active`. The strongest
  current direction is prepared/global texture scale/fallback squaring. The
  maintained prepared gate improves FPV on all three comparable slices:
  `val_0` seed-6 `-5.5750`, `val_1` seed-6 `-7.1603`, and `val_1` seed-8
  `-7.7401`. It is still `comparison_only_not_default`, blocked by active
  render residuals and one auxiliary chase regression.
- Light/brightness/tone:
  simple light/shadow probes are `neutral_do_not_promote`: no-dome changes FPV
  only `-0.7571` and hurts chase `+8.2014`; no-shadow changes FPV `-0.4444`
  and is chase-neutral. RGB/tone probes are FPV-positive across held-out slices
  but remain comparison-only because calibration is view-dependent and material
  residuals remain active.

The latest intermediate texture-scale probes confirm the main direction but do
not solve the default-promotion blocker. The target-specific
`val1_diningtable_lightwood_power15` probe improves the dining-table FPV from
`46.1260` to `40.9925` with chase unchanged, but gives up too much overall FPV
gain versus full scale-square. The broader
`val1_scale_square_soften_diningtable_lightwood_power075` probe improves FPV by
`-6.2698`, lowers the high-residual count, but leaves the same chase luminance
side effect as full scale-square (`+2.9125`). This means the remaining
Isaac-vs-MuJoCo visual mismatch is not caused by FPV camera pose; it is in the
render domain: USD texture scale/sampler/material response plus lighting/tone
differences.

Current blocker fingerprint:
`render_domain_visual_parity`; root-cause classification:
`texture_scale_sampler_material_response_with_tone_luminance_side_effect`; last
decision delta: camera and RAW_FPV are treated as proven aligned, while
prepared scale-square stays comparison-only until the auxiliary chase luminance
side effect is resolved or explicitly re-gated.

## Tone-Mitigation Probes 2026-06-02

The `val_1` seed-6 prepared scale-square chase blocker is now narrower. It is
not fixed by single global tone compensation:

- Prepared scale-square alone:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_prepared_scale_square_gate_probe/report.html`
  moves FPV `36.5655 -> 29.4052` (`-7.1603`) but moves chase
  `72.2838 -> 75.1960` (`+2.9122`).
- Prepared scale-square plus the held-out `val_0` FPV RGB profile:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_prepared_scale_square_val0_rgb_gain_probe/report.html`
  still improves FPV (`30.2630`, `-6.3025`) but worsens chase further
  (`76.9372`, `+4.6534`). Do not use the cross-scene FPV RGB profile as a
  chase blocker mitigation.
- Prepared scale-square plus a chase-fitted RGB profile:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_prepared_scale_square_chase_rgb_gain_probe/report.html`
  fixes chase (`71.6620`, `-0.6218`) but breaks FPV (`47.8901`, `+11.3246`).
  Do not use one global chase-derived RGB profile for policy/input views.
- Prepared scale-square plus a view-specific RGB profile:
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_8loc_fovfix_bound_prepared_scale_square_view_rgb_gain_probe/report.html`
  keeps FPV strongly improved (`30.2755`, `-6.2900`) and fixes chase
  (`71.6638`, `-0.6200`). This is useful diagnostic evidence that the auxiliary
  chase side effect can be removed by view-specific report-side tone
  compensation, but it is overfit/comparison-only and must not become a default
  renderer profile without held-out validation.
- The same comparison-only view-specific profile has now been sanity-checked on
  two held-out slices. On `val_1` seed-8 it keeps FPV strongly improved
  (`37.2184 -> 30.3806`, `-6.8378`) and keeps chase within tolerance
  (`71.7464 -> 72.1970`, `+0.4506`). On `val_0` seed-6 it keeps FPV improved
  (`38.0980 -> 32.3450`, `-5.7530`) and keeps chase within tolerance
  (`83.7516 -> 84.5279`, `+0.7763`). This strengthens the view-specific tone
  direction, but it is still comparison-only and has not been promoted to a
  default-rendering contract.
- The view-specific tone profile is now reproducible instead of hand-composed:
  `scripts/molmo_cleanup/make_robot_camera_rgb_gain_profile.py` accepts repeated
  `--view-gain VIEW=MANIFEST` inputs and writes
  `backend_view_rgb_gain`. Re-running it for the current evidence writes
  `output/molmo/robot-camera-apple2apple/profiles/0602_val1_seed6_prepared_scale_square_view_rgb_gain.generated.json`
  with base/FPV gain `[0.944061, 0.844818, 0.822146]` and chase gain
  `[1.589143, 1.423057, 1.304406]`, matching the existing comparison-only
  profile core values. This only makes the report-side compensation auditable;
  it does not change MuJoCo/Isaac default rendering or the RAW_FPV policy input.
- The summary calibration reader now prefers the scene-level
  `visual_diagnostics.render_domain_calibration` field over nested candidate
  color-profile calibrations. That prevents comparison-profile replay evidence
  from being mistaken for default-rendering calibration readiness. With that
  source pinned, the baseline `val_0` calibration blocker is
  `view_dependent_render_domain_delta` with residual `14.8384`.
- A real scene-camera calibration probe using the prepared scale-square USD now
  exists at
  `output/molmo/scene-camera-comparison/0602_val0_scene_refs_scale_square_calibration/0603_0003/report.html`.
  It improves scene-level calibration residual from `14.8384` to `11.6923` and
  raises mean luminance-delta improvement from about `5.7%` to `20.4%`, but its
  status remains `view_dependent_render_domain_delta`. This is positive
  material-response evidence, not enough to promote prepared scale-square or
  luminance gain as default cleanup rendering.
- Two real calibration probes then stacked simple light/shadow toggles on top of
  prepared scale-square. Removing the Isaac DomeLight
  (`output/molmo/scene-camera-comparison/0602_val0_scale_square_no_dome_calibration/0603_0009/report.html`)
  worsens residual to `25.5330`. Enabling wall/ceiling shadows
  (`output/molmo/scene-camera-comparison/0602_val0_scale_square_no_shadow_calibration/0603_0011/report.html`)
  also worsens residual to `13.9678`. Both remain
  `view_dependent_render_domain_delta`, so do not promote simple DomeLight
  removal or shadow enabling, even in combination with scale-square.
- The summary gate now requires actual view-specific profile evidence instead
  of only trusting probe labels. Each
  `prepared_scale_square_view_rgb` probe must expose `backend_view_rgb_gain`
  for both `fpv` and `chase` in its Isaac color profile state before
  `view_specific_prepared_scale_square_tone_gate` can be ready for review. The
  refreshed summary records `view_rgb_gain_profile_count=3`,
  `required_view_rgb_gain_views=["fpv","chase"]`, no blockers, and
  `has_required_view_rgb_gain=true` for all three current probes.
- That same gate is now formalized as report-side comparison evidence:
  `view_specific_prepared_scale_square_tone_gate.status=view_specific_report_comparison_gate_ready`,
  `formal_comparison_gate_ready=true`,
  `policy_scope=report_side_comparison_only`, and
  `default_rendering_candidate=false`. The four-check audit now points the
  light/brightness/tone row at this formal report-side gate while keeping the
  row unresolved for default rendering. This lets reports use the view-specific
  compensation as evidence without changing the policy/input RAW_FPV lane or
  promoting Isaac/MuJoCo default renderer changes.

Decision delta: a single global color/tone profile cannot satisfy both FPV and
chase under prepared scale-square. A view-specific tone profile can satisfy the
current FPV and auxiliary chase tolerance across the current three-slice corpus,
and the summary now encodes that as
`view_specific_prepared_scale_square_tone_gate.status=view_specific_report_comparison_gate_ready`.
It remains report-side comparison-only by design. The next useful slice is a
default-rendering decision: resolve the remaining material/texture render
residuals and calibration gates before changing Isaac/MuJoCo default cleanup
rendering.

The summary now exposes that boundary directly as
`report_side_visual_parity.status=report_side_visual_parity_ready` with
`ready=true`, `policy_scope=report_side_comparison_only`,
`default_rendering_candidate=false`, and no blockers. The top-level summary
remains `active` because `four_check_audit.unresolved_check_ids` still contains
`material_texture_response` and `light_brightness_tone` for default-rendering
parity. In short: the report-side comparison can be read as aligned under the
formal view-specific tone gate, but default Isaac/MuJoCo rendering is still not
promoted as visually equivalent.

Default-rendering parity now has its own machine layer:
`default_rendering_visual_parity.status=not_ready`. The current blockers are
`render_domain_probe_matrix=render_domain_delta_active`,
`prepared_scale_square_default_gate=comparison_only_not_default`,
`rgb_tone_cross_validation=comparison_only_rgb_tone_positive`, the
`val1_seed6_prepared_scale_square_gate` auxiliary chase/tone-luminance
regression, active baseline render residuals
(`lighting_shadow_contract_delta`, `target_material_texture_or_binding_gap`),
`calibration_not_default_rendering_ready`,
`render_domain_calibration_not_default_ready`, and `rgb_tone_comparison_only`.
The calibration blocker points at
`output/molmo/scene-camera-comparison/0602_val0_scene_refs_calibration/comparison_manifest.json`
with mean calibrated luminance residual `14.8384`, and the prepared
scale-square calibration probe at
`output/molmo/scene-camera-comparison/0602_val0_scene_refs_scale_square_calibration/0603_0003/comparison_manifest.json`
with residual `11.6923`. The stacked light/shadow calibration probes are also
blocked: scale-square plus no-dome is `25.5330`, and scale-square plus
enable-shadows is `13.9678`. All four report
`render_domain_calibration_status=view_dependent_render_domain_delta`. The
refreshed recommendation now points at resolving or explicitly gating those
default-rendering residuals instead of re-reviewing the already formalized
report-side gate.

## Touched Areas

- `scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py`
- `tests/unit/molmo_cleanup/test_molmospaces_usd_reference_installer.py`
- `scripts/isaac_lab_cleanup/import_rby1m_robot_usd.py`
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
- `scripts/isaac_lab_cleanup/make_molmospaces_light_shadow_probe_usd.py`
- `scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- `scripts/molmo_cleanup/make_robot_camera_rgb_gain_profile.py`
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/unit/molmo_cleanup/test_molmospaces_light_shadow_probe_usd.py`
- `tests/unit/molmo_cleanup/test_prepare_molmospaces_flattened_semantic_usd.py`
- `tests/unit/molmo_cleanup/test_robot_camera_rgb_gain_profile.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- `tests/unit/molmo_cleanup/test_robot_camera_visual_parity_summary.py`
- Generated evidence under `output/isaaclab/` and
  `output/molmo/robot-camera-apple2apple/`

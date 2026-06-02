# MuJoCo Isaac Camera Visual Parity

Owner/session: Codex local
Started: 2026-06-02 16:30 Asia/Shanghai
State: active

## Scope

Make MolmoSpaces MuJoCo and Isaac Sim cleanup robot-view evidence use alike FPV
camera geometry and move visual results as close as practical. FPV must remain
the real robot-mounted head camera; chase camera is auxiliary report evidence.

## Source Of Truth

- Current root commit before this note: `5f682eb9 feat: probe targeted diffuse texture material response`
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
that same fair target set. For light/shadow specifically, do not retry simple
dome removal, shadow enabling, or the old combined MuJoCo-like light/shadow USD
edit; split light count, shadow flags, intensity/direction, and material
response only in a comparison-only probe. Keep RAW_FPV and world-labels as
separate evidence lanes: world-labels uses images as report evidence only, while
camera-raw uses the head-camera FPV images as agent input.

## Touched Areas

- `scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py`
- `tests/unit/molmo_cleanup/test_molmospaces_usd_reference_installer.py`
- `scripts/isaac_lab_cleanup/import_rby1m_robot_usd.py`
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- Generated evidence under `output/isaaclab/` and
  `output/molmo/robot-camera-apple2apple/`

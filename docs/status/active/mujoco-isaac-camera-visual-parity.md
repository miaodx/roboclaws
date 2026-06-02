# MuJoCo Isaac Camera Visual Parity

Owner/session: Codex local
Started: 2026-06-02 16:30 Asia/Shanghai
State: active

## Scope

Make MolmoSpaces MuJoCo and Isaac Sim cleanup robot-view evidence use alike FPV
camera geometry and move visual results as close as practical. FPV must remain
the real robot-mounted head camera; chase camera is auxiliary report evidence.

## Source Of Truth

- Current root commit: the current `fix: align isaac head camera fov` commit
- Camera fix commit: `0329e930 fix: align isaac head camera capture`
- Report: `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_headpitch_lightingfix_scene_refs_fix/report.html`
- Color/tone probe:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_global_rgb_gain_probe/report.html`
- FOV fix probes:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_4loc_fovfix_baseline/report.html`
  and
  `output/molmo/robot-camera-apple2apple/0602_val1_seed6_2mess_4loc_fovfix_baseline/report.html`
- 8-location post-FOV baseline:
  `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_fovfix_baseline/report.html`

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
- Remaining blocker is visual render-domain parity:
  `render_contract_diagnostics.status=lighting_shadow_contract_delta`,
  MuJoCo lights `1`, Isaac lights `2`, Isaac shadow-disabled prims `44` on
  `val_0` and `18` on `val_1`. Chase remains much less comparable because it is
  auxiliary report evidence rather than the policy/input camera contract.
- A combined MuJoCo-like light/shadow USD probe removed the contract delta but
  made visual error worse: FPV avg `50.8161`, chase avg `114.0763`.
  Do not turn that combined probe into the default.
- A comparison-only global Isaac RGB gain probe improved real re-rendered FPV
  from `46.7762` to `43.4240` while preserving the head-camera contract and
  `0.005m` FPV pose delta. The profile used
  `backend_rgb_gain.isaaclab_subprocess=[0.944061,0.844818,0.822146]` from the
  `val_0`/seed-6 FPV least-squares fit. This is evidence that tone/color
  response is a real direction, but it is not yet broad enough for a default
  cleanup rendering calibration.

## Next Action

Keep FPV pose and the head-camera FOV contract unchanged. Next, broaden the FOV
fix to an 8-location `val_0` rerun and more scenes/seeds, then investigate the
remaining render-domain gap: light/shadow, USD PreviewSurface/material response,
texture colorspace, and high-residual geometry/material edges. Keep the RGB gain
profile comparison-only until it improves a broader post-FOV corpus.

## Touched Areas

- `scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py`
- `tests/unit/molmo_cleanup/test_molmospaces_usd_reference_installer.py`
- `scripts/isaac_lab_cleanup/import_rby1m_robot_usd.py`
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py`
- `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py`
- `tests/unit/molmo_cleanup/test_isaac_lab_backend.py`
- `tests/unit/molmo_cleanup/test_robot_camera_apple2apple_comparison.py`
- Generated evidence under `output/isaaclab/` and
  `output/molmo/robot-camera-apple2apple/`

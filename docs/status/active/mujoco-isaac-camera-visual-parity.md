# MuJoCo Isaac Camera Visual Parity

Owner/session: Codex local
Started: 2026-06-02 16:30 Asia/Shanghai
State: active

## Scope

Make MolmoSpaces MuJoCo and Isaac Sim cleanup robot-view evidence use alike FPV
camera geometry and move visual results as close as practical. FPV must remain
the real robot-mounted head camera; chase camera is auxiliary report evidence.

## Source Of Truth

- Current root commit: `ff62ff44 fix: install isaac scene usd references`
- Camera fix commit: `0329e930 fix: align isaac head camera capture`
- Report: `output/molmo/robot-camera-apple2apple/0602_val0_seed6_8loc_headpitch_lightingfix_scene_refs_fix/report.html`

## Current Evidence

- `val_0` scene-referenced USD assets are complete:
  `/tmp/val0_scene_missing_refs_after_install.json` has
  `scene_missing_referenced_asset_count=0`.
- Prepared semantic USD is ready:
  `output/isaaclab/flattened-semantic-usd/val_0_scene_refs_fix/summary.json`
  has `matched_entry_count=139`, `missing_prim_count=0`,
  and `renderable_labeled_prim_count=3357`.
- 8-location apple2apple report passed with
  `fpv_contract_shared_with_static_head_camera_pitch_correction`,
  `fpv_world_pose_aligned`, FPV position delta avg/max `0.005m`,
  and `target_contract_delta_counts={"material_texture_names_match": 8}`.
- Remaining blocker is visual domain parity:
  `render_contract_diagnostics.status=lighting_shadow_contract_delta`,
  MuJoCo lights `1`, Isaac lights `2`, Isaac shadow-disabled prims `44`,
  FPV mean abs RGB avg `46.7762`.
- A combined MuJoCo-like light/shadow USD probe removed the contract delta but
  made visual error worse: FPV avg `50.8161`, chase avg `114.0763`.
  Do not turn that combined probe into the default.

## Next Action

Investigate tone/color response and high-residual geometry/material edges before
changing FPV pose. Use focused comparison probes; only code a lighting/color
change if it improves FPV error, not merely the report contract counters.

## Touched Areas

- `scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py`
- `tests/unit/molmo_cleanup/test_molmospaces_usd_reference_installer.py`
- Generated evidence under `output/isaaclab/` and
  `output/molmo/robot-camera-apple2apple/`

# Isaac Lab AOV Debug Capsule

Last updated: 2026-05-29

## Current Blocker

Isaac Sim/Lab semantic AOV is available for generated controls, including a
control scene that references NVIDIA Isaac 5.1 official Blocks assets.
MolmoSpaces `val_1` still collapses to full-frame `BACKGROUND` through the raw
composed scene path, including the MolmoSpaces official Isaac package route.
The blocker has narrowed: flattened MolmoSpaces `val_0` and `val_1` USDs with
semantic labels authored directly on renderable Gprim/Mesh targets produce
usable Isaac semantic segmentation when the camera semantic filter is
`usd_prim_path`.

## Blocker Fingerprint

- `blocker_kind`: `isaac_semantic_aov`
- `root_cause_classification`:
  `raw_molmospaces_scene_composition_hides_renderable_semantic_label_targets`
- `known_not_root_cause`: request routing, selected USD binding, missing object
  references, renderable geometry, scene-index label application, semantic
  filter breadth, global Isaac runtime AOV support, current runtime preflight,
  Roboclaws-only IsaacSim 6 / IsaacLab 0.54 version skew, MolmoSpaces
  renderable Gprim/Mesh labels after flattening, Isaac semantic AOV path labels

## Last Proven Evidence

- Head-camera FPV cleanup robot-view checker gate:
  `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`
  - new strict flag:
    `--require-robot-head-camera-fpv`
  - requires every robot-view step to report
    `robot_view_camera_control.status=all_robot_views_use_head_camera_fpv`
  - requires FPV to be a real robot head camera or an explicit
    head-camera-equivalent view, with nonblank FPV/verify images
  - the legacy `--require-canonical-robot-view-camera-control` flag remains an
    alias for this stricter head-camera gate, not a free-camera FPV claim
- Flattened `usd_prim_path` cleanup smoke on `val_0`:
  `output/isaaclab/cleanup-smoke/0529_val0_flattened_usdprimpath_cleanup/run_result.json`
  - strict checker passed with real Isaac runtime, local prepared scene USD,
    selected USD bindings, robot-view provenance, snapshot provenance,
    segmentation evidence, and `isaac_semantic_pose`
  - `semantic_filter=["usd_prim_path"]`
  - `segmentation.status=available`
  - `candidate_bbox_count=24`
  - `selected_usd_prim_match_count=1`
  - cleanup score status `success`, `accepted_count=1`,
    `sweep_coverage_rate=1.0`
- Flattened semantic USD prep artifact on `val_0`:
  `output/isaaclab/flattened-semantic-usd/0529_val0_flattened_semantic_scene/summary.json`
  - `status=ready`
  - matched 139 MolmoSpaces metadata entries
  - authored labels on 1124 renderable Gprims, including 651 Mesh prims
  - `missing_prim_count=0`
  - `blockers=[]`
- Flattened `usd_prim_path` cleanup smoke:
  `output/isaaclab/cleanup-smoke/0529_val1_flattened_usdprimpath_cleanup_clean/run_result.json`
  - strict checker passed with real Isaac runtime, local prepared scene USD,
    selected USD bindings, robot-view provenance, snapshot provenance,
    segmentation evidence, and `isaac_semantic_pose`
  - `semantic_filter=["usd_prim_path"]`
  - `segmentation.status=available`
  - `candidate_bbox_count=24`
  - `selected_usd_prim_match_count=2`
  - cleanup score status `success`, `accepted_count=1`,
    `sweep_coverage_rate=1.0`
- Flattened semantic USD prep artifact:
  `output/isaaclab/flattened-semantic-usd/0529_val1_flattened_semantic_scene/summary.json`
  - `status=ready`
  - matched 40 MolmoSpaces metadata entries
  - authored labels on 637 renderable Gprims, including 408 Mesh prims
  - copied `scene_metadata.json` next to the flattened USD for the normal
    scene-index binding path
- Flattened `class` AOV probe:
  `output/isaaclab/runtime-smoke/0529_val1_flattened_semantic_aov_probe/state.json`
  - `semantic_filter=["class"]`
  - semantic tensors no longer collapsed to full-frame `BACKGROUND`
  - produced category candidates such as `bowl` and `sink`
  - still failed selected USD matching because class labels do not carry USD
    prim paths
- Flattened `usd_prim_path` AOV probe:
  `output/isaaclab/runtime-smoke/0529_val1_flattened_usdprimpath_aov_probe/state.json`
  - `semantic_filter=["usd_prim_path"]`
  - `status=available`
  - `candidate_bbox_count=24`
  - `selected_usd_prim_match_count=2`
  - checker passed with selected Bowl/Sink USD prim matches
- A-E matrix artifact:
  `output/isaaclab/aov-comparison/0529_A_to_E_official_isaac51_matrix.json`
  - `status=decision_ready`
  - `root_cause_classification=molmospaces_scene_usd_semantic_aov_projection`
  - generated Roboclaws control produced non-background semantic labels
  - NVIDIA Isaac official Blocks control produced non-background semantic labels
  - MolmoSpaces `val_1` produced `semantic_segmentation` tensors but every
    semantic view collapsed to `BACKGROUND`
  - current default Isaac Lab runtime preflight passed
  - MolmoSpaces official Isaac package route also collapsed to `BACKGROUND`
- Generated control artifact:
  `output/isaaclab/runtime-smoke/0528_A_generated_control_current/state.json`
  - `semantic_segmentation` tensor available
  - `candidate_bbox_count=22`
  - `non_background_label_count=14`
- Isaac official Blocks control artifact:
  `output/isaaclab/runtime-smoke/0528_B_isaac_official_blocks_control_v3/state.json`
  - `semantic_segmentation` tensor available
  - `candidate_bbox_count=22`
  - `non_background_label_count=14`
  - `gprim_label_count=6`
  - `mesh_label_count=3`
- MolmoSpaces `val_1` payload-load artifact:
  `output/isaaclab/runtime-smoke/0528_C_val1_payload_load_gprim_label_probe/state.json`
  - `semantic_segmentation` tensor available
  - four semantic views are full-frame `BACKGROUND`
  - `candidate_bbox_count=4`
  - `selected_usd_prim_match_count=0`
  - scene-index labels applied to 29 prims with `failed_count=0`
  - `gprim_label_count=0`
  - `mesh_label_count=0`
- Runtime preflight artifact:
  `output/isaaclab/preflight/0528_D_current_runtime_preflight/preflight.json`
  - `status=ready`
  - runtime dir: `.venv-isaaclab`
  - Isaac Lab source: `.venv-isaaclab-src/IsaacLab`
- MolmoSpaces official Isaac package artifact:
  `output/isaaclab/runtime-smoke/0529_official_isaac51_lab23_val1_semantic_probe/state.json`
  - installed runtime: `.venv-molmo-isaac-official`
  - package versions: `molmo-spaces-isaac=0.0.1`,
    `isaacsim=5.1.0.0`, `isaaclab=2.3.2.post1`
  - `semantic_segmentation` tensor available
  - four semantic views are full-frame `BACKGROUND`
  - `candidate_bbox_count=4`
  - `selected_usd_prim_match_count=0`
  - scene-index labels applied to 29 prims with `failed_count=0`
  - `gprim_label_count=0`
  - `mesh_label_count=0`

## Next Hypothesis

MolmoSpaces USD composition is the failing layer, not Isaac semantic AOV as a
whole. Raw composed scene loading still hides or prevents effective semantic
projection to rendered Gprims/Meshes, but flattening the composed stage and
authoring `UsdSemantics.LabelsAPI` directly on final renderable descendants
makes selected-object semantic evidence available when the semantic filter asks
for `usd_prim_path`.

## Expected Decision Delta

Do not treat MolmoSpaces Isaac segmentation as globally unavailable anymore.
Keep default cleanup segmentation disabled. The integration slice treats
flattened semantic USD as an explicit pre-cleanup artifact, not as an implicit
online cleanup mutation: prepare `scene_semantic.usda` plus `summary.json`,
then run local Isaac runtime or cleanup smoke against that prepared scene with
`segmentation_semantic_filter=usd_prim_path`. That path now passes strict
cleanup smoke on `val_0` and `val_1`; the next decision is how broad the
prepared-artifact corpus must be before adding a convenience wrapper or
changing defaults.

## Next Command Or Artifact

Prepared semantic USD handoff is wired and proven behind explicit local-dev
opt-ins for cleanup smoke on `val_0` and `val_1`. Next local artifact should
either broaden the prepared-artifact corpus further or add an explicit
maintainer convenience wrapper that still keeps defaults unchanged. Do not
expose this through the default public `household-cleanup` path until broader
coverage passes. Any local cleanup artifact intended to prove agent-facing
robot FPV should also pass `--require-robot-head-camera-fpv`.

## Stop Condition

The root-cause experiment succeeded. Avoid further low-information AOV
observability; continue only with integration work that makes the proven
flattened/path-label route available through a normal command or with upstream
MolmoSpaces/Isaac evidence.

## No-Touch Scope

- No CI-first validation.
- No checker threshold changes.
- No default segmentation-on behavior for cleanup runs.
- No broad Roboclaws refactor.
- No broad cleanup behavior change until the flattened semantic USD prep route
  is explicitly selected.
- No implicit online USD flatten/label mutation inside cleanup until prepared
  artifact coverage is proven across multiple scenes.

## Parked Work

- Broaden segmentation-off MolmoSpaces scene-index cleanup coverage beyond
  `val_0` and `val_1`.
- Broaden prepared flattened semantic USD segmentation cleanup coverage beyond
  `val_0` and `val_1`.

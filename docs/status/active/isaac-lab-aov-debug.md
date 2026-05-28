# Isaac Lab AOV Debug Capsule

Last updated: 2026-05-28

## Current Blocker

Isaac Sim/Lab semantic AOV is available in the current local runtime for
generated controls, including a control scene that references NVIDIA Isaac 5.1
official Blocks assets. MolmoSpaces `val_1` still loads and renders, but its
`semantic_segmentation` output collapses to full-frame `BACKGROUND` in every
view with zero selected USD prim matches.

## Blocker Fingerprint

- `blocker_kind`: `isaac_semantic_aov`
- `root_cause_classification`: `molmospaces_scene_usd_semantic_aov_projection`
- `known_not_root_cause`: request routing, selected USD binding, missing object
  references, renderable geometry, scene-index label application, semantic
  filter breadth, global Isaac runtime AOV support, current runtime preflight

## Last Proven Evidence

- A-D matrix artifact:
  `output/isaaclab/aov-comparison/0528_A_to_D_isaac_aov_matrix.json`
  - `status=decision_ready`
  - `root_cause_classification=molmospaces_scene_usd_semantic_aov_projection`
  - generated Roboclaws control produced non-background semantic labels
  - NVIDIA Isaac official Blocks control produced non-background semantic labels
  - MolmoSpaces `val_1` produced `semantic_segmentation` tensors but every
    semantic view collapsed to `BACKGROUND`
  - current default Isaac Lab runtime preflight passed
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

## Next Hypothesis

MolmoSpaces USD composition differs from generated controls and official Isaac
asset references at the semantic AOV projection layer. The selected
MolmoSpaces top-level prims are valid and renderable, but in the composed stage
they still expose no Gprim/Mesh semantic label targets to the current label
application pass, and the render product reports only background semantic IDs.

## Expected Decision Delta

The official-scene control rules out a global Isaac runtime AOV failure. Treat
MolmoSpaces segmentation as a scene/USD composition blocked capability for now,
and continue the Isaac cleanup path with segmentation disabled unless a later
upstream MolmoSpaces/Isaac USD semantic fix is available.

## Next Command Or Artifact

Use the A-D matrix artifact when explaining the decision. Next implementation
work should continue segmentation-off MolmoSpaces scene coverage, not spend more
turns on low-information AOV observability.

## Stop Condition

Do not make another low-information observability edit for
`isaac_semantic_aov`. Reopen this only with a new root-cause experiment that can
make MolmoSpaces semantic labels reach composed rendered Gprims/Meshes, or with
new upstream Isaac/MolmoSpaces evidence.

## No-Touch Scope

- No CI-first validation.
- No checker threshold changes.
- No default segmentation-on behavior for cleanup runs.
- No broad Roboclaws refactor.
- No `STATUS.md` update unless the project-level blocker or next action changes.

## Parked Work

- Broaden segmentation-off MolmoSpaces scene-index cleanup coverage beyond
  `val_0` and `val_1`.
- Revisit Isaac segmentation only with a root-cause AOV/render-product
  experiment or upstream Isaac evidence.

# Isaac Lab AOV Debug Capsule

Last updated: 2026-05-29

## Current Blocker

Isaac Sim/Lab semantic AOV is available for generated controls, including a
control scene that references NVIDIA Isaac 5.1 official Blocks assets.
MolmoSpaces `val_1` still loads and renders, but its `semantic_segmentation`
output collapses to full-frame `BACKGROUND` in every view with zero selected
USD prim matches. The same collapse now reproduces under the MolmoSpaces
official Isaac package route: `molmo_spaces_isaac[sim]` with IsaacSim 5.1.0.0
and IsaacLab 2.3.2.post1.

## Blocker Fingerprint

- `blocker_kind`: `isaac_semantic_aov`
- `root_cause_classification`: `molmospaces_scene_usd_semantic_aov_projection`
- `known_not_root_cause`: request routing, selected USD binding, missing object
  references, renderable geometry, scene-index label application, semantic
  filter breadth, global Isaac runtime AOV support, current runtime preflight,
  Roboclaws-only IsaacSim 6 / IsaacLab 0.54 version skew

## Last Proven Evidence

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

MolmoSpaces USD composition differs from generated controls and official Isaac
asset references at the semantic AOV projection layer. The selected MolmoSpaces
top-level prims are valid and renderable, but in the composed stage they still
expose no Gprim/Mesh semantic label targets to the current label application
pass, and the render product reports only background semantic IDs. This is no
longer explained by using Roboclaws' IsaacSim 6 / IsaacLab 0.54 runtime instead
of the MolmoSpaces official IsaacSim 5.1 / IsaacLab 2.3.x package route.

## Expected Decision Delta

The official-scene control and official MolmoSpaces Isaac runtime probe rule out
a broad Isaac AOV absence and the first-order version-skew hypothesis. Treat
MolmoSpaces segmentation as a scene/USD composition blocked capability for now,
and continue the Isaac cleanup path with segmentation disabled unless a later
upstream MolmoSpaces/Isaac USD semantic fix is available.

## Next Command Or Artifact

Use the A-E matrix artifact when explaining the decision. Next implementation
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

# Isaac Lab AOV Debug Capsule

Last updated: 2026-05-28

## Current Blocker

MolmoSpaces USD scenes load and render through Isaac Sim/Lab, selected
object/receptacle USD bindings resolve to renderable geometry, and cleanup
parity passes without segmentation. When segmentation is requested, Isaac
returns `semantic_segmentation` tensors for `val_1`, but every view is a
full-frame `BACKGROUND` candidate with zero selected USD prim matches.

## Blocker Fingerprint

- `blocker_kind`: `isaac_semantic_aov`
- `root_cause_classification`: `semantic_aov_rendered_geometry_not_labelled`
- `known_not_root_cause`: request routing, selected USD binding, missing object
  references, renderable geometry, scene-index label application, semantic
  filter breadth

## Last Proven Evidence

- Comparison artifact:
  `output/isaaclab/aov-comparison/0528_generated_vs_val1_semantic_aov.json`
  - `status=decision_ready`
  - `first_divergent_layer=semantic_tensor_ids_collapsed_to_background`
  - both control and candidate produced `semantic_segmentation` tensors
  - control produced non-background semantic labels
  - candidate scene-index labels were applied without failures
  - candidate semantic views each contain one tensor id
- Generated control artifact:
  `output/isaaclab/runtime-smoke/0528_generated_seg_geometry_control_v2/state.json`
  - `semantic_segmentation` tensor available
  - first view has `unique_id_count=6`
  - `candidate_bbox_count=22`
  - `selected_usd_prim_match_count=7`
- MolmoSpaces `val_1` artifact:
  `output/isaaclab/runtime-smoke/0528_val1_seg_semantic_filter_class_probe/state.json`
  - `semantic_segmentation` tensor available
  - first view has `unique_id_count=1`
  - candidate labels are all `BACKGROUND`
  - `candidate_bbox_count=4`
  - `selected_usd_prim_match_count=0`
  - scene-index labels applied to 29 prims with `failed_count=0`

## Next Hypothesis

Generated control USD and MolmoSpaces USD diverge before Roboclaws selected-path
matching: MolmoSpaces labels are applied to composed top-level prims, but Isaac's
semantic AOV sees only background for the rendered geometry. The next meaningful
runtime probe must check whether labels must be authored on rendered
payload/reference Gprims instead of only the MolmoSpaces scene-index prims.

## Expected Decision Delta

The comparison step identified the first divergent layer as
`semantic_tensor_ids_collapsed_to_background`. The next implementation decision
is narrow: either label the rendered payload/reference Gprims and rerun one
MolmoSpaces semantic probe, or defer Phase E segmentation as
`blocked_capability` and continue segmentation-off scene coverage.

## Next Command Or Artifact

Probe label application on rendered payload/reference descendants, or explicitly
defer Phase E segmentation before continuing segmentation-off coverage.

## Stop Condition

Do not make another low-information observability edit for
`isaac_semantic_aov`. The next implementation step must either produce a
root-cause comparison artifact or explicitly defer segmentation in the canonical
plan and continue another Isaac backend requirement.

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

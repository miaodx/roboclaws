---
plan_scope: b1-map12-verified-map-scene-alignment
status: In progress
created: 2026-06-16
last_reviewed: 2026-06-18
implementation_allowed: true
source:
  - user request to promote B1 / Map 12 digital twin from candidate overlay to trustworthy map-scene alignment
  - user note that current bbox-to-map correspondence is poor and must not be treated as a good baseline
  - docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md
  - docs/plans/2026-06-15-cross-environment-semantic-map-parity.md
  - skills/scene-gaussian-map-alignment/SKILL.md
related_context:
  - ARCHITECTURE.md
  - STATUS.md
  - docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md
  - assets/maps/agibot-robot-map-12/semantics.json
  - assets/maps/b1-map12-alignment-review.json
  - assets/maps/b1-map12-scene-correspondences.json
  - scripts/isaac_lab_cleanup/check_b1_map12_readiness.py
  - scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py
  - tests/contract/maps/test_b1_map12_digital_twin_readiness.py
  - tests/contract/maps/test_cross_environment_semantic_map_parity.py
---

# B1 / Map 12 Verified Map-Scene Alignment

## Status

Reviewed with grill-batch on 2026-06-16. The correspondence schema direction,
verification thresholds, and first annotation workflow are accepted. The
implementation slice now has fitter/readiness/probe evidence, but final
room/area semantic acceptance is still pending.

2026-06-17 update: there is not yet an operator-authored room semantic
manifest. Treat `assets/maps/b1-map12-alignment-review.json` as a seed/review
placeholder until manual labeling is redone after naming conflicts are resolved.
Do not use it as proof that room semantics are accepted.

2026-06-18 update: the misleading old source-map-frame
`output/b1-map12/runtime-delete-smoke/review_labels_topdown.png` was deleted
locally. Automatic contour alignment against the cropped B1 Gaussian top-down
was attempted with
`scripts/maps/auto_align_b1_map12_scene_topdown.py`; it remains
`candidate_seed_only` because residuals against the manual draft anchors are
mean `2.152082 m` and max `2.595962 m`. The same probe now also tries semantic
label/partition center matching; that candidate is worse, with best mean
residual `7.891215 m` and max `11.003484 m`. A tracked manual draft snapshot
now lives at `docs/status/active/b1-map12-scene-correspondences-draft.json`.
The explicit verification-only manual fallback passes global rigid alignment
with mean residual `0.352908 m` and max `0.502064 m`, but it uses synthetic
area/partition ids and must not be committed as the final accepted
correspondence asset.

Semantic suggestion pass:
`scripts/maps/suggest_b1_map12_manual_anchor_semantics.py` compares the manual
anchors against the current Map12 review polygons and B1 scene partition bounds.
It found only 1 strong candidate out of 7 anchors, so the current evidence is
not strong enough to auto-fill final `navigation_area_id` /
`asset_partition_id` values. The command now also writes
`output/b1-map12/manual-draft-anchor-semantic-review-packet.json`, a
non-mutating human-review packet that combines each manual pick with semantic
candidates while keeping all anchors proposed and accepted anchor count at zero.
`scripts/maps/promote_b1_map12_semantic_review_packet.py` now provides the
strict promotion path from a human-edited packet into the committed
correspondence manifest. It rejects proposed-only packets, missing real semantic
ids, fewer than six human-accepted anchors, synthetic `manual_draft_*` ids,
bbox/seed coordinate sources, and auto-accepted suggestions before validating
the final manifest.
The suggestion command also writes
`output/b1-map12/manual-draft-anchor-semantic-review.html`, a static read-only
HTML table for operator review of the proposed anchors and candidate semantic
ids.

2026-06-18 planning-loop clarification: this plan remains the prerequisite
alignment evidence contract. It owns reviewed correspondences, real
`navigation_area_id` / `asset_partition_id` semantics, residual thresholds, and
readiness status. `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`
consumes a passing residual artifact for on-demand Map12 waypoint or `map_xy/yaw`
requests, B1 scene pose application, and same-pose Isaac preview proof.

## Goal

Promote the B1 / Map 12 digital twin from a weak candidate overlay to a
trustworthy map-scene alignment for navigation and room/area semantics.

Target claim:

```text
Map 12 source map frame
  + B1 rebuilt USD/Gaussian scene
  + named physical/semantic correspondences
  -> fitted transform with residuals
  -> verified global alignment when residuals pass
  -> otherwise verified per-area alignment where local residuals pass
  -> room/area semantic correspondence with evidence
```

This plan intentionally does not target manipulation, object-level USD truth,
or planner-backed navigation.

## Current Problem

The current overlay is misleading if treated as a baseline. It is a bounding-box
fit from Map 12 navigation-memory nav-goal bounds to B1 USD world bounds:

```text
bbox_fit_navigation_memory_nav_goals_to_scene_usd_bounds
```

The observed bbox-to-map correspondence quality is poor. Treat this transform
only as a known-poor seed for coarse visual search. It must not be described as
a good baseline, a regression target, or evidence that the scene and map are
close to aligned.

Current readiness artifacts already record why the state is not verified:

- `map12_overlay_status` is `candidate`.
- `map12_to_b1_usd_transform_status` is `unverified`.
- residual evidence is `not_available`.
- no human-authored B1/USD anchor correspondences are available.
- existing `scene_map_correspondence_v1` entries bind scene partitions to
  navigation areas at `candidate` level only.
- no final room semantic labels have been reviewed; current label files are
  placeholders or seeds, not accepted operator semantics.

## Scene Asset Roles

There are two B1 Gaussian/scene asset families, and they should not be merged
under one generic "Gaussian map" assumption:

- `data/robot-data-lab/scene-engine/data/2rd_floor_seperated/` is the newer
  split scene. It has room/partition/object labeling and is the first source for
  Map12 registration and future actionable/manipulation-oriented tasks.
- `data/robot-data-lab/scene-engine/data/B1_floor2_slow/` is the older full
  Gaussian capture. It has better photorealistic visual quality, but does not
  carry the same object-level split labels. Keep it for later open-ended visual
  tasks after registration is understood through the newer split scene.

First align Map12 against `2rd_floor_seperated`. After that, evaluate whether
the same transform or a reviewed secondary transform can place
`B1_floor2_slow` into the same Map12 frame for visual-only/open-task use.

## Architecture Layers

This plan touches:

- Backend Runtime / Environment Primitive: B1 Isaac scene inspection and render
  probes.
- Artifacts, reports, and eval suites: readiness, alignment, correspondence,
  residual, and visual review artifacts.
- Worlds / Scenes: `world=b1-map12` and Map 12 static bundle alignment metadata.

This plan must not change:

- public `household-world` / `planner-proof` command grammar;
- MCP capability contracts;
- agent cleanup/search strategy;
- object/receptacle manipulation support.

## Definitions

- `correspondence_anchor`: a named map-scene match such as a door center, wall
  corner, corridor turn, room entrance, fixed column, or room-area centroid that
  exists in both Map 12 and the B1 scene.
- `global_transform`: one map-to-scene transform applied to all verified
  anchors.
- `area_transform`: a transform scoped to a named room or navigation area when
  global alignment residuals are too high.
- `verified`: named anchors match across map and scene with residuals recorded
  and accepted by the threshold policy.
- `known_poor_bbox_seed`: the current bbox-fit transform. It can seed views or
  rough visual search only, but it is not an alignment baseline and must not
  prefill accepted anchor coordinates.

## Scope

### Correspondence Artifact

Add a first-class map-scene correspondence manifest, for example:

```json
{
  "schema": "b1_map12_scene_correspondences_v1",
  "source_map_frame": "robot_map_12_map",
  "target_scene_frame": "b1_rebuilt_scene_usd_world",
  "bbox_seed_policy": "known_poor_seed_only",
  "scene_projection_policy": {
    "horizontal_axes": ["x", "y"],
    "up_axis": "z",
    "source": "2rd_floor_seperated_scene_topdown_policy"
  },
  "anchors": [
    {
      "anchor_id": "meeting_room_a_door_center",
      "anchor_type": "door_center",
      "navigation_area_id": "west_corridor",
      "asset_partition_id": "meeting_room_a",
      "map_xy": [-5.5, 2.4],
      "scene_xyz": [-1.2, -8.7, 0.0],
      "evidence": {
        "map_image": "output/.../map_anchor.png",
        "scene_image": "output/.../scene_anchor.png",
        "operator_note": "doorway between west corridor and meeting_room_a"
      },
      "confidence": 0.8,
      "review_status": "accepted"
    }
  ]
}
```

The manifest must be separate from generated readiness artifacts so
scene-specific assumptions are reviewable instead of hidden in script defaults.
Accepted anchor coordinates must come from an explicit map pick and an explicit
scene pick. The known-poor bbox seed may help a reviewer search for the right
area, but it must not populate `scene_xyz`, mark an anchor accepted, or count
toward residual evidence.

Draft annotations should live under `output/` while they are being reviewed.
Once accepted, the reviewed manifest should be committed as a standalone asset
at `assets/maps/b1-map12-scene-correspondences.json`.
Only human/operator-reviewed picks may use `review_status=accepted`.
Model-generated or script-generated anchor candidates must remain
`review_status=proposed` until reviewed.

Strict promotion from the semantic review packet to the committed manifest is
allowed only after a human/operator changes selected anchors to
`review_status=accepted` and supplies real `navigation_area_id` and
`asset_partition_id` values for at least six anchors. The promotion path must
reject proposed-only packets, partial accepted packets, missing semantic ids,
synthetic `manual_draft_*` ids, bbox/seed coordinate sources, and any attempt to
auto-accept suggestions. It must validate the final manifest before writing
`assets/maps/b1-map12-scene-correspondences.json`.

The checked-in correspondence manifest may remain empty as a fail-loud
placeholder. Empty anchors mean no transform is verified and the fitter/review
workflow must block rather than use old or seed-derived coordinates.

### Fitting And Residual Report

Add a deterministic fitter that consumes the correspondence manifest and emits:

- transform candidates: rigid 2D, similarity 2D, and optionally affine 2D for
  diagnostics only;
- explicit scene horizontal-axis policy derived from USD `up_axis`, robot pose
  convention, or a reviewed manifest override;
- selected transform type and reason;
- per-anchor residuals in meters;
- mean, median, p90, max residual;
- inlier/outlier classification;
- leave-one-out residuals;
- global pass/fail;
- per-area pass/fail when global fit is poor;
- before/after overlay preview and residual arrows.

The first production transform should prefer the simplest model that passes.
Do not use affine transform to hide local distortion unless the report labels it
diagnostic-only.

### Readiness Integration

Extend `check_b1_map12_readiness.py` so it can optionally take a
correspondence/residual artifact. It may set:

```json
{
  "map12_overlay_status": "verified",
  "map12_to_b1_usd_transform_status": "verified",
  "residual_evidence": {
    "status": "available",
    "matched_anchor_count": 6,
    "mean_residual_m": 0.42,
    "max_residual_m": 0.91
  }
}
```

Only set global `verified` when the accepted threshold policy passes. If global
fit fails but some areas pass, preserve:

```json
{
  "map12_overlay_status": "candidate",
  "map12_to_b1_usd_transform_status": "area_verified_only",
  "area_alignment": [
    {
      "navigation_area_id": "central_floor",
      "alignment_status": "verified",
      "matched_anchor_count": 4,
      "max_residual_m": 0.7
    }
  ]
}
```

### Room/Area Semantic Correspondence

Promote `scene_map_correspondence_v1` from candidate room-label evidence to
verified room/area evidence only when anchor residuals support it.

Allowed claim after this plan:

```text
Map 12 navigation_area_id X corresponds to B1 asset_partition_id Y at
room/area level, with residual-backed evidence.
```

Still blocked:

```text
Map 12 fixture/object X is USD prim Y.
B1 scene object/receptacle USD bindings are ready.
Manipulation is supported.
```

## Non-Goals

- Do not implement pick/place, support surfaces, object segmentation, or
  receptacle USD binding.
- Do not claim `semantic_anchors_are_usd_truth=true`.
- Do not claim planner-backed navigation or physical robot parity.
- Do not expose a new public product surface.
- Do not make the bbox-fit transform a maintained baseline.
- Do not silently mark poor global alignment as verified because local visual
  screenshots look plausible.

## Threshold Policy

Initial thresholds are plan defaults and should be confirmed during review:

- Minimum global anchors: 6 accepted anchors.
- Minimum non-collinear anchors: 4.
- Required spatial coverage: anchors must cover at least three navigation areas
  or scene partitions.
- Global verified target: mean residual <= 0.75 m and max residual <= 1.5 m.
- Area verified target: mean residual <= 0.5 m and max residual <= 1.0 m within
  the area.
- Minimum area anchors: 3 accepted, non-collinear anchors for an independently
  fitted area transform. If an area has fewer anchors, it may inherit a passing
  global transform but must not claim an independent local transform.
- Outliers: allowed only when explicitly excluded with a recorded reason.

If the first annotation run shows these thresholds are unrealistic, update this
plan before relaxing the claim. Do not tune thresholds after seeing a report
without recording why the new threshold remains meaningful.

The thresholds above are the accepted first gate for implementation. Changing
them before claiming `verified` requires an explicit plan update.

## Implementation Plan

### Phase 1: Annotation And Review Workflow

- Add the correspondence manifest schema and one sample manifest for B1 / Map
  12.
- Add a small report/script workflow that shows Map 12 topdown image, B1 scene
  view, anchor ids, and evidence paths.
- Require separate map-coordinate and scene-coordinate picks for accepted
  anchors.
- Label the current bbox transform as `known_poor_seed_only` wherever it appears
  in this workflow.
- Defer a custom annotation UI unless the report/script workflow proves too
  slow for selecting the initial anchor set.

### Phase 2: Transform Fitter

- Implement the transform fitter and residual report.
- Compare rigid 2D and similarity 2D fits.
- Generate before/after overlay previews and residual arrows.
- Fail loudly if there are too few anchors, collinear anchors, or poor spatial
  coverage.

### Phase 3: Readiness And Map Bundle Integration

- Teach readiness artifacts to consume the residual report.
- Promote global status to `verified` only when residuals pass.
- Promote room/area correspondences only when area residuals pass.
- First write separate alignment manifest and residual artifacts. Update
  `semantics.json` references only after review, not during the first fitting
  pass.
- Keep object/receptacle USD readiness and manipulation support blocked.

### Phase 4: Contract Tests And Report Evidence

- Add tests that reject verified alignment without residual evidence.
- Add tests that reject verified alignment based on the bbox seed.
- Add tests for global-failed/area-verified status.
- Add report coverage for residual metrics and outlier anchors.

## Suggested Files

- `assets/maps/b1-map12-scene-correspondences.json`
- `scripts/maps/fit_b1_map12_scene_alignment.py`
- `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py`
- `scripts/maps/auto_align_b1_map12_scene_topdown.py`
- `scripts/maps/promote_b1_map12_manual_draft_for_verification.py`
- `scripts/maps/promote_b1_map12_semantic_review_packet.py`
- `scripts/maps/suggest_b1_map12_manual_anchor_semantics.py`
- `tests/contract/maps/test_b1_map12_verified_alignment.py`
- `tests/contract/maps/test_b1_map12_digital_twin_readiness.py`
- `tests/contract/maps/test_cross_environment_semantic_map_parity.py`

## Suggested Proof

```bash
# after a human/operator edits the review packet and accepts real semantic ids:
python scripts/maps/promote_b1_map12_semantic_review_packet.py \
  --review-packet output/b1-map12/manual-draft-anchor-semantic-review-packet.json \
  --output assets/maps/b1-map12-scene-correspondences.json

python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment

.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
  --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --alignment-artifact output/b1-map12/alignment/alignment_residuals.json \
  --output output/b1-map12/alignment/readiness_with_alignment.json

./scripts/dev/run_pytest_standalone.sh \
  tests/contract/maps/test_b1_map12_verified_alignment.py \
  tests/contract/maps/test_b1_map12_digital_twin_readiness.py \
  tests/contract/maps/test_cross_environment_semantic_map_parity.py \
  -q
```

The old manual draft proof remains verification-only. The final production proof
must use `assets/maps/b1-map12-scene-correspondences.json` after the anchors
receive reviewed real `navigation_area_id` and `asset_partition_id` values.

## Definition Of Done

Success only if:

- a reviewable correspondence manifest exists with at least 6 accepted anchors;
- accepted anchors have human-reviewed real `navigation_area_id` and
  `asset_partition_id` values, not synthetic verification-only ids or
  model-generated proposed suggestions;
- bbox seed output is explicitly labeled `known_poor_seed_only`;
- the transform fitter writes residual metrics and overlay previews;
- readiness artifacts cannot claim verified alignment without residual evidence;
- readiness artifacts cannot claim verified alignment from a transform whose
  `source` is `known_poor_bbox_seed`;
- verified global alignment passes the accepted residual threshold, or the
  artifact clearly says global alignment remains candidate;
- per-area verified alignment is supported when global alignment is poor;
- independently fitted per-area alignment requires at least 3 accepted,
  non-collinear anchors for that area;
- room/area semantic correspondence can become verified only with residual
  evidence;
- object/receptacle USD binding, manipulation, and planner-backed navigation
  remain blocked or out of scope;
- reports show residuals and outliers clearly enough for a human to audit the
  claim.

## Blockers And Decisions

- Need first accepted anchor set. Without human/operator-reviewed anchor
  correspondences, verified alignment remains blocked.
- If residuals are high, prefer area-level verified claims over weakening
  global thresholds.
- Accepted annotation lifecycle: draft under `output/`; committed map-bundle
  asset only after review.
- Accepted rollout order: alignment manifest and residual artifact first;
  static `semantics.json` references only after review.
- Accepted tooling scope: report/script workflow first; custom annotation UI is
  deferred.

## Recommended Next Step

Add or run the strict review-packet promotion path for
`output/b1-map12/manual-draft-anchor-semantic-review-packet.json`. It should
write the committed correspondence manifest only after explicit human acceptance
with real semantic ids, then rerun the fitter on
`assets/maps/b1-map12-scene-correspondences.json`. Until that passes, keep the
verification-only synthetic manifest as test evidence only, not production proof.

## Preflight Contract

Preflight status: DRAFT

Task source: mixed user prompt + plan review

Canonical source: `docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md`

Route: durable `$intuitive-flow`

Goal: Implement the B1 / Map 12 map-scene alignment evidence slice so verified
claims require reviewed correspondences and residuals, while poor bbox overlay
remains only a known-poor visual-search seed.

Scope:

- Add the B1 / Map 12 correspondence manifest schema and reviewed-asset
  lifecycle.
- Add a report/script anchor review workflow with separate map and scene picks.
- Add a deterministic transform fitter and residual report.
- Integrate residual evidence into B1 readiness artifacts without promoting
  static semantics prematurely.
- Add report/test coverage for bbox-seed rejection, verified/global vs
  area-verified claims, and blocked object/manipulation claims.

Non-goals:

- No pick/place, support-surface, object segmentation, receptacle binding, or
  manipulation support.
- No planner-backed navigation or physical robot parity claim.
- No new public product surface or command grammar.
- No annotation UI unless the report/script workflow is proven insufficient and
  re-approved.
- No `semantics.json` promotion until the separate alignment manifest and
  residual artifact are reviewed.

Entity budget:

- reuse: B1 readiness script, B1 navigation report, static map bundle,
  `scene_map_correspondence_v1`, cross-environment map parity tests, and
  `scene-gaussian-map-alignment` evidence vocabulary.
- remove/merge: none.
- new: correspondence manifest schema,
  `assets/maps/b1-map12-scene-correspondences.json` after review, transform
  fitter script, residual artifact, focused contract test;
  these are necessary because bbox fit has poor observed quality and cannot be
  reused as a verified baseline.
- expansion triggers: custom annotation UI, object-level USD binding,
  planner-backed navigation, physical robot proof, altered residual thresholds,
  or public surface changes require re-approval.

Context:

- must-read: this plan, `docs/human/domain.md`,
  `docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md`,
  `docs/plans/2026-06-15-cross-environment-semantic-map-parity.md`,
  `docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`,
  `skills/scene-gaussian-map-alignment/SKILL.md`,
  `scripts/isaac_lab_cleanup/check_b1_map12_readiness.py`,
  `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py`,
  `assets/maps/agibot-robot-map-12/semantics.json`,
  `assets/maps/b1-map12-alignment-review.json`,
  `assets/maps/b1-map12-scene-correspondences.json`.
- useful: existing operator-console B1 preview artifacts and any current
  `output/b1-map12/**` readiness/navigation reports.
- avoid-unless-needed: historical MolmoSpaces Isaac parity plans, raw provider
  logs, old Genesis renderer work, and broad `output/` scans.

Acceptance:

- SUCCESS: reviewed correspondences exist; bbox seed is rejected as verification
  evidence; fitter emits residuals and visual overlays; readiness can claim
  global `verified` only when thresholds pass or else records
  `area_verified_only`; object/receptacle/manipulation/planner claims remain
  blocked; reports make residuals and outliers auditable.
- BLOCKED_NEEDS_DECISION: thresholds need relaxation, custom annotation UI is
  required, accepted anchors cannot be chosen from available evidence, or scope
  expands into object/manipulation/planner/public-surface work.
- BLOCKED_NEEDS_LOCAL_VALIDATION: required Isaac scene rendering, local B1
  assets, or human/operator anchor review are unavailable when claiming
  reviewed visual evidence or verified alignment.
- INTERMEDIATE_ONLY: schema, fitter, and tests exist but no reviewed anchor set
  or local/manual evidence is available; this cannot claim verified alignment.
- No regressions: existing B1 navigation readiness, cross-environment map
  parity, Map 12 bundle conversion, and public household-world routes continue
  to pass.

Verification:

- deterministic:

  ```bash
  ./scripts/dev/run_pytest_standalone.sh \
    tests/contract/maps/test_b1_map12_verified_alignment.py \
    tests/contract/maps/test_b1_map12_digital_twin_readiness.py \
    tests/contract/maps/test_cross_environment_semantic_map_parity.py \
    tests/contract/skills/test_scene_gaussian_map_alignment_skill.py \
    -q
  ```

- integration:

  ```bash
  python scripts/maps/fit_b1_map12_scene_alignment.py \
    --correspondences assets/maps/b1-map12-scene-correspondences.json \
    --map-bundle assets/maps/agibot-robot-map-12 \
    --output-dir output/b1-map12/alignment

  .venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py \
    --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
    --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 \
    --alignment-artifact output/b1-map12/alignment/alignment_residuals.json \
    --output output/b1-map12/alignment/readiness_with_alignment.json
  ```

- product-run:

  ```bash
  just harness::b1-map12-navigation-smoke \
    b1_root=data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
    map12_root=vendors/agibot_sdk/artifacts/maps/robot_map_12 \
    output_dir=output/b1-map12/navigation-smoke
  ```

- local-live-manual: human/operator review accepts anchor picks; local Isaac
  rendering or existing reviewed scene images provide scene-side evidence. If
  unavailable, stop at `INTERMEDIATE_ONLY` or `BLOCKED_NEEDS_LOCAL_VALIDATION`
  depending on the claim being made.
- optional: render or update the B1 navigation/alignment HTML report for easier
  review after deterministic gates pass.

Execution:

- main: root session supervises scope, protects bbox/semantic boundaries, and
  makes final complete/blocked judgment.
- worker: none by default.
- worker-goal: none.

To execute: `/goal execute docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md with intuitive-flow`

Optional tracking: none

Approval: `LGTM`, `approve`, or `go ahead` approves this preflight; edits
request revision.

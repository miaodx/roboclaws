# B1 / Map 12 Verified Map-Scene Alignment

Current status: B1 / Map 12 geometry alignment is globally verified from the
seven manually picked `anchor_role=alignment` anchors in the committed
manifest, and the first residual-backed robot-consumption proof now passes.
The official residual artifact reports `selected_transform_type=rigid_2d`,
mean residual `0.352908 m`, p90 `0.491765 m`, and max `0.502064 m`.
`output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`
applies two Map12 navigation-memory points as B1 scene robot poses and captures
same-pose FPV/Chase evidence. Room/object label projection is still separate
and needs additional `anchor_role=semantic` room-interior anchors with reviewed
`navigation_area_id` / `asset_partition_id` values.

Blocker fingerprint:

- blocker_kind: `b1_map12_isaac_same_pose_camera_proof`
- root_cause_classification: passed for preview-grade kinematic pose-driven
  Isaac robot-view proof
- last_decision_delta: geometry alignment no longer blocks on room ids, and
  local Isaac no longer blocks the first robot-consumption proof. The committed
  manifest contains seven accepted `anchor_role=alignment` anchors, the
  official residual fitter verifies global alignment, and two residual-backed
  Map12 points now produce same-pose FPV/Chase evidence.

Last proven evidence:

- `output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json`
  is the current cropped B1 Gaussian top-down packet. It records
  `crop_max_z=1.8`, `geometry_status=rendered_gaussian_scene_topdown`, explicit
  camera height/FOV, and ray-plane `scene_xyz` mapping. The old
  `output/b1-map12/runtime-delete-smoke/review_labels_topdown.png` source-map
  frame image was deleted locally because it was a misleading intermediate, not
  current alignment evidence.
- `python scripts/maps/auto_align_b1_map12_scene_topdown.py --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --scene-topdown-render output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json --manual-draft docs/status/active/b1-map12-scene-correspondences-draft.json --output-dir output/b1-map12/auto-alignment-probe-tracked-draft`
  writes `auto_alignment_status=candidate_seed_only`. The contour seed fails
  against the manual draft anchors with mean residual `2.152082 m` and max
  residual `2.595962 m`. The semantic label/partition center search also fails;
  its best candidate has mean residual `7.891215 m` and max `11.003484 m`.
  Neither automatic route can be promoted.
- `docs/status/active/b1-map12-scene-correspondences-draft.json` snapshots the
  seven operator-picked manual draft anchors from the ignored `tmp/` export so
  the local probe is reproducible. The anchors now explicitly declare
  `anchor_role=alignment`; they intentionally remain `review_status=proposed`
  until promotion, and their blank room/area ids are expected for geometry-only
  alignment.
- `python scripts/maps/promote_b1_map12_manual_draft_for_verification.py --draft docs/status/active/b1-map12-scene-correspondences-draft.json --output output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json`
  explicitly creates a verification-only accepted manifest for the manual
  fallback. It uses `anchor_role=alignment` geometry anchors only; do not commit
  it as the final accepted asset.
- `python scripts/maps/suggest_b1_map12_manual_anchor_semantics.py --draft docs/status/active/b1-map12-scene-correspondences-draft.json --review-manifest assets/maps/b1-map12-alignment-review.json --scene-diagnostic output/b1-map12/scene-topdown-label-overlay/scene_topdown_diagnostic.json --output output/b1-map12/manual-draft-anchor-semantic-suggestions.json`
  writes review suggestions for real `navigation_area_id` /
  `asset_partition_id` values without mutating the accepted manifest. It found
  only 1 strong candidate out of 7 anchors; the rest are nearest-only hints,
  so final semantic acceptance still needs human review.
- The same suggestion command also writes
  `output/b1-map12/manual-draft-anchor-semantic-review-packet.json` by default.
  The packet combines each manual pick with candidate semantic ids for review,
  keeps every anchor `review_status=proposed`, records
  `accepted_manifest_mutated=false`, and reports `accepted_anchor_count=0`,
  `proposed_anchor_count=7`, `strong_candidate_count=1`.
- `python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/manual-draft-alignment`
  writes `global_alignment_status=verified`, `selected_transform_type=rigid_2d`,
  and residual evidence with mean `0.352908 m`, p90 `0.491765 m`, and max
  `0.502064 m`.
- `python scripts/maps/promote_b1_map12_semantic_review_packet.py --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json --output assets/maps/b1-map12-scene-correspondences.json --check`
  validates seven human-accepted geometry anchors without writing the committed
  asset.
- `python scripts/maps/check_b1_map12_semantic_review_packet_fit.py --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment-accepted-fit-check`
  writes a non-mutating fit check with `global_alignment_status=verified` and
  no validation errors.
- `python scripts/maps/promote_b1_map12_semantic_review_packet.py --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json --output assets/maps/b1-map12-scene-correspondences.json`
  writes the committed correspondence manifest with seven accepted
  `anchor_role=alignment` anchors and blank semantic ids.
- `python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment`
  writes the official residual artifact with `status=global_verified`,
  `global_alignment_status=verified`, `selected_transform_type=rigid_2d`, seven
  matched anchors, mean residual `0.352908 m`, p90 `0.491765 m`, and max
  residual `0.502064 m`. Preview overlays are under
  `output/b1-map12/alignment/previews/`.
- `python scripts/maps/render_b1_map12_label_tool.py --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --review-manifest assets/maps/b1-map12-alignment-review.json --output-dir output/b1-map12/label-tool`
  writes `output/b1-map12/label-tool/label_tool.html` and
  `label_tool_packet.json`. The HTML editor loads raw Map12 navigation layers,
  scene partition evidence, and the review manifest as separate layers; it
  supports polygon/circle/point draft labels, movable labels, global display
  tilt, and exports `b1_map12_alignment_review_v1` without mutating either raw
  source.
- `python scripts/maps/render_b1_map12_correspondence_review.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --scene-topdown-render output/b1-map12/scene-gaussian-topdown/scene_gaussian_topdown.json --output-dir output/b1-map12/correspondence-review`
  writes `output/b1-map12/correspondence-review/correspondence_review.html`
  and `correspondence_review_packet.json` with
  `review_status=review_pending`, `accepted_anchor_count=0`, validation
  passed, and the next action to produce at least six accepted anchors with
  explicit map and metric scene picks. The right panel is the rendered B1
  Gaussian scene top-down; missing, malformed, or label-inventory scene packets
  fail the command instead of degrading silently. The picker uses browser-ready
  `output/b1-map12/correspondence-review/map12_source_map.png` while preserving
  the vendor `occupancy.pgm` as `source_map.source_image` and using
  `nav2.yaml` origin/resolution for `map_xy` conversion.
- `python scripts/operator_console/render_scene_previews.py --world b1-map12 --output-dir output/b1-map12/static-preview-proof`
  writes static B1 preview metadata with only `map` and `topdown` views; no
  `views.fpv`, no `views.chase`, and no corresponding camera preview files are
  published before residual-backed Isaac runtime camera evidence exists.
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 --alignment-artifact output/b1-map12/manual-draft-alignment/alignment_residuals.json --output output/b1-map12/manual-draft-alignment/readiness_with_alignment.json`
  passes validation with `map12_overlay_status=verified`,
  `map12_to_b1_usd_transform_status=verified`, and
  `robot_navigation_supported=false`.
- `scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py` writes
  `b1_map12_waypoint_pose_requests_v1` artifacts for on-demand Map12 waypoint
  ids or `map_xy/yaw` points. Globally verified residual alignment and
  explicitly verified local-area transforms produce ready B1 pose rows;
  unverified, malformed, missing-area, or unknown-area requests produce
  blocked rows instead of fallback output.
- `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py` requires at
  least two distinct applied B1 scene poses before setting
  `robot_navigation_supported=true`; duplicate-pose camera rows stay blocked.
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 --alignment-artifact output/b1-map12/alignment/alignment_residuals.json --output output/b1-map12/alignment/readiness_with_alignment.json`
  passes validation with `map12_overlay_status=verified`,
  `map12_to_b1_usd_transform_status=verified`, and
  `robot_navigation_supported=false` before runtime smoke evidence is attached.
- `python scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py --alignment-artifact output/b1-map12/alignment/alignment_residuals.json --points output/b1-map12/navigation-smoke/map12_points.json --output output/b1-map12/navigation-smoke/waypoint_pose_requests.json`
  successfully converts two accepted alignment-corner anchors into
  residual-backed B1 scene poses, but the subsequent smoke run under
  `output/b1-map12/navigation-smoke/navigation_smoke.json` remains blocked
  because both FPV images have too little visual detail. This confirms corner
  alignment anchors are valid geometry evidence but poor camera-smoke points.
- `python scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py --alignment-artifact output/b1-map12/alignment/alignment_residuals.json --points output/b1-map12/navigation-smoke/residual-overlay/map12_points.json --output output/b1-map12/navigation-smoke/residual-overlay/waypoint_pose_requests.json`
  converts the `plastic_bottle_table_1` and `long_table` Map12 navigation-memory
  candidate points into ready residual-backed B1 scene pose requests with no
  blocked rows.
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py --readiness-artifact output/b1-map12/alignment/readiness_with_alignment.json --waypoint-pose-requests output/b1-map12/navigation-smoke/residual-overlay/waypoint_pose_requests.json --output-dir output/b1-map12/navigation-smoke/residual-overlay --accept-nvidia-eula`
  passes. The resulting
  `output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json`
  reports `robot_navigation_supported=true`,
  `robot_navigation_provenance=isaac_b1_map12_navigation_smoke`,
  `navigation_provenance=kinematic_pose_driven`, two applied waypoints, and
  same-pose FPV/Chase/Map/Verify images for each waypoint.
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 --alignment-artifact output/b1-map12/alignment/alignment_residuals.json --navigation-artifact output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json --require-navigation-success --output output/b1-map12/navigation-smoke/residual-overlay/readiness_with_navigation.json`
  passes and promotes the readiness artifact to
  `robot_navigation_supported=true` from the real navigation-smoke artifact.
- `python scripts/operator_console/render_scene_previews.py --world b1-map12 --b1-camera-artifact output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json --output-dir output/b1-map12/operator-preview-residual-overlay`
  succeeds and writes `b1-map12-preview.json`, `b1-map12-fpv.png`,
  `b1-map12-chase.png`, `b1-map12-map.png`, and `b1-map12-topdown.png`. The FPV
  and Chase metadata share `waypoint_id=b1_aligned_long_table`, reference
  `output/b1-map12/alignment/alignment_residuals.json`, use
  `alignment_transform_source=reviewed_correspondence_fit`, and record
  `isaac_runtime_*` provenance.
- `python scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py --run-dir output/b1-map12/navigation-smoke/residual-overlay --readiness-artifact output/b1-map12/alignment/readiness_with_alignment.json --navigation-artifact output/b1-map12/navigation-smoke/residual-overlay/navigation_smoke.json --waypoint-pose-requests output/b1-map12/navigation-smoke/residual-overlay/waypoint_pose_requests.json --output output/b1-map12/navigation-smoke/residual-overlay/report.html`
  passes and writes the reviewable navigation report.
- `just harness::b1-map12-navigation-smoke stamp=residual-overlay-default-harness output_dir=output/b1-map12/navigation-smoke-harness`
  passes as the canonical single-command maintainer replay. It consumes the
  default residual-backed readiness candidate waypoints without an explicit
  `waypoint_pose_requests` override and writes non-empty `navigation_smoke.json`,
  `readiness_with_navigation.json`, `report.html`, and
  `operator-preview/b1-map12-preview.json` under
  `output/b1-map12/navigation-smoke-harness/residual-overlay-default-harness/`.
  The smoke artifact applies `b1_aligned_plastic_bottle_table_1` and
  `b1_aligned_long_table`; the preview metadata uses the same waypoint for
  FPV/Chase, references `output/b1-map12/alignment/alignment_residuals.json`,
  and records `alignment_transform_source=reviewed_correspondence_fit`.
  An explicit
  `waypoint_pose_requests=output/b1-map12/navigation-smoke/residual-overlay/waypoint_pose_requests.json`
  replay also passes under `residual-overlay-harness-4`.
  The earlier interrupted
  `output/b1-map12/navigation-smoke-harness/residual-overlay-harness/` directory
  is a partial run with zero-byte JSON files and is not evidence.
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py` can include
  `waypoint_pose_requests.json` and renders ready/blocked conversion decisions
  in the HTML report before local Isaac camera proof exists.
- `scripts/maps/promote_b1_map12_semantic_review_packet.py` now implements the
  strict promotion gate from a human-edited review packet to the committed
  correspondence manifest. Proposed-only rows, missing `anchor_role`, fewer
  than six human-accepted anchors, bbox/seed coordinate sources, and
  auto-accepted suggestions are rejected before writing output. Accepted
  `alignment` anchors may keep blank semantic ids; accepted `semantic` anchors
  require real ids and reject synthetic `manual_draft_*` values. `--check`
  validates the same gate without writing the committed asset, and write mode
  strips review-only suggestion metadata from promoted anchors.
- The same semantic suggestion command now writes
  `output/b1-map12/manual-draft-anchor-semantic-review.html`, a read-only
  operator table showing each proposed anchor, candidate semantic ids, and
  nearest candidate distances.
- `scripts/maps/check_b1_map12_semantic_review_packet_fit.py` can validate a
  human-edited packet and run the residual fitter against a promoted preview
  manifest under `output/` without writing `assets/maps/b1-map12-scene-correspondences.json`.
- Operator-console B1 FPV/Chase promotion rejects generic `robot_view_steps`
  unless they include a camera-control contract proving the FPV source is a
  robot-mounted or head-camera-equivalent runtime view and not scene-probe/bbox
  evidence. B1 navigation-smoke waypoint evidence remains valid as the
  pose-driven camera artifact path.
- B1 FPV/Chase promotion also rejects artifacts without waypoint ids or with
  mixed FPV/Chase view labels, so accepted preview metadata stays tied to one
  same-waypoint evidence row.
- B1 `--skip-existing` preview reuse now requires the cached camera metadata to
  keep the matching camera artifact path, same waypoint id, residual alignment
  artifact, and `reviewed_correspondence_fit` transform source. Incomplete
  stale camera metadata is rewritten to static map/topdown preview and stale
  FPV/Chase files are removed.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_gaussian_topdown.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py -q`
  passes.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py tests/unit/operator_console/test_render_scene_previews.py -q`
  passes for the pose-request and report-audit contract.
- `ruff check scripts/maps/promote_b1_map12_semantic_review_packet.py scripts/maps/suggest_b1_map12_manual_anchor_semantics.py tests/contract/maps/test_b1_map12_verified_alignment.py`,
  `ruff format --check scripts/maps/promote_b1_map12_semantic_review_packet.py scripts/maps/suggest_b1_map12_manual_anchor_semantics.py tests/contract/maps/test_b1_map12_verified_alignment.py`,
  and `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py -q`
  pass for the strict promotion gate, `--check` mode, and read-only semantic
  review report.
- `ruff check scripts/operator_console/render_scene_previews.py tests/unit/operator_console/test_render_scene_previews.py`,
  `ruff format --check scripts/operator_console/render_scene_previews.py tests/unit/operator_console/test_render_scene_previews.py`,
  `./scripts/dev/run_pytest_standalone.sh tests/unit/operator_console/test_render_scene_previews.py -q`, and
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_navigation_report.py tests/unit/operator_console/test_render_scene_previews.py -q`
  pass for the hardened B1 camera-preview provenance gate.
- `ruff check scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py`,
  `ruff format --check scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py tests/contract/maps/test_b1_map12_verified_alignment.py`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py -q`, and
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py -q`
  pass for the distinct-applied-pose navigation smoke gate.

Next hypothesis: the same residual-backed point path is sufficient for
operator-selected Map12 `map_xy/yaw` points inside verified global coverage, as
long as the points are useful interior navigation/viewpoints rather than
alignment-corner anchors.

Next implementation step: keep the navigation-smoke and operator-preview
artifact path as the accepted first proof. Add semantic anchors later before
projecting room/object labels. If broader robot consumption is required next,
wire this residual-backed pose-request path into the operator workflow instead
of adding a new compatibility route.

Next command/artifact:

```bash
python scripts/maps/auto_align_b1_map12_scene_topdown.py \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --scene-topdown-render output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json \
  --manual-draft docs/status/active/b1-map12-scene-correspondences-draft.json \
  --output-dir output/b1-map12/auto-alignment-probe-tracked-draft

python scripts/maps/render_b1_map12_correspondence_review.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --scene-topdown-render output/b1-map12/scene-gaussian-topdown-crop-z1p8/scene_gaussian_topdown.json \
  --output-dir output/b1-map12/correspondence-review

python scripts/maps/promote_b1_map12_manual_draft_for_verification.py \
  --draft docs/status/active/b1-map12-scene-correspondences-draft.json \
  --output output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json

python scripts/maps/suggest_b1_map12_manual_anchor_semantics.py \
  --draft docs/status/active/b1-map12-scene-correspondences-draft.json \
  --review-manifest assets/maps/b1-map12-alignment-review.json \
  --scene-diagnostic output/b1-map12/scene-topdown-label-overlay/scene_topdown_diagnostic.json \
  --output output/b1-map12/manual-draft-anchor-semantic-suggestions.json \
  --review-packet-output output/b1-map12/manual-draft-anchor-semantic-review-packet.json \
  --review-report-output output/b1-map12/manual-draft-anchor-semantic-review.html

python scripts/maps/promote_b1_map12_semantic_review_packet.py \
  --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json \
  --output assets/maps/b1-map12-scene-correspondences.json \
  --check

python scripts/maps/check_b1_map12_semantic_review_packet_fit.py \
  --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment-accepted-fit-check

python scripts/maps/promote_b1_map12_semantic_review_packet.py \
  --review-packet docs/status/active/b1-map12-alignment-accepted-review-packet.json \
  --output assets/maps/b1-map12-scene-correspondences.json

python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment
```

Stop condition: geometry alignment and preview-grade runtime navigation proof
are verified. Do not claim room/area labels, object labels, manipulation,
planner-backed navigation, physical robot support, or public MCP navigation
until separate accepted semantic anchors and dedicated proof artifacts exist.

No-touch scope: no public surface changes, no MCP contract changes, no object
or receptacle USD binding, no manipulation or planner-backed navigation claim,
and no threshold relaxation without a plan update.

Parked work:

- Use `output/b1-map12/correspondence-review/correspondence_review.html` only if
  more geometry anchors are needed. The first seven accepted alignment anchors
  are already committed.
- Use `output/b1-map12/label-tool/label_tool.html` when the current
  axis-aligned candidate room boxes are too crude. Exported label drafts still
  need an explicit review/merge step before replacing committed map semantics
  or correspondence assets.

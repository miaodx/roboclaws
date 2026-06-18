# B1 / Map 12 Verified Map-Scene Alignment

Current blocker: final verified alignment still needs reviewed
`navigation_area_id` / `asset_partition_id` semantics for the manually picked
B1/Map 12 correspondence anchors. The cropped B1 Gaussian top-down exists, the
old misleading source-map top-down output was deleted locally, and automatic
contour alignment was tried but failed the residual gate.

Blocker fingerprint:

- blocker_kind: `b1_map12_reviewed_correspondence_anchors`
- root_cause_classification: external review evidence missing
- last_decision_delta: rendered Gaussian scene top-down is now required for
  correspondence review; label-inventory diagnostics are rejected, Z-up `x,y`
  correspondence policy remains locked, and residual-backed waypoint
  provenance checks/no-camera static preview gates remain in place. Internal
  waypoint pose request artifacts now cover verified global or explicitly
  verified local-area transforms, and the navigation report can display ready
  and blocked pose-request rows for audit.

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
  the local probe is reproducible. The anchors intentionally remain
  `review_status=proposed`; their room/area ids are not final semantics.
- `python scripts/maps/promote_b1_map12_manual_draft_for_verification.py --draft docs/status/active/b1-map12-scene-correspondences-draft.json --output output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json`
  explicitly creates a verification-only accepted manifest for the manual
  fallback. It uses synthetic area/partition ids only to exercise the residual
  gate; do not commit it as the final accepted asset.
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
- `python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/alignment`
  writes `status=insufficient_reviewed_anchors`,
  `global_alignment_status=candidate`, zero accepted anchors, residual
  evidence unavailable, and `scene_projection_policy` locked to Z-up `x,y`.
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
- `scripts/isaac_lab_cleanup/render_b1_map12_navigation_report.py` can include
  `waypoint_pose_requests.json` and renders ready/blocked conversion decisions
  in the HTML report before local Isaac camera proof exists.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_gaussian_topdown.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py -q`
  passes.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py tests/unit/operator_console/test_render_scene_previews.py -q`
  passes for the pose-request and report-audit contract.

Next hypothesis: once the seven manual anchors receive reviewed real
`navigation_area_id` and `asset_partition_id` values, they can replace the
verification-only synthetic ids in `assets/maps/b1-map12-scene-correspondences.json`
and preserve the same passing residuals without weakening the threshold policy.

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
  --review-packet-output output/b1-map12/manual-draft-anchor-semantic-review-packet.json

python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences output/b1-map12/manual-draft-alignment/b1-map12-scene-correspondences.verification-only.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/manual-draft-alignment
```

Stop condition: do not mark B1 / Map 12 alignment verified until the committed
correspondence manifest has at least six accepted anchors and the residual
artifact passes the threshold policy. Do not use the bbox seed as accepted
coordinate evidence.

No-touch scope: no public surface changes, no MCP contract changes, no object
or receptacle USD binding, no manipulation or planner-backed navigation claim,
and no threshold relaxation without a plan update.

Parked work:

- Use `output/b1-map12/correspondence-review/correspondence_review.html` to drive
  anchor review, then replace the placeholder
  `assets/maps/b1-map12-scene-correspondences.json` with reviewed accepted
  anchors after explicit operator map and scene picks.
- Use `output/b1-map12/label-tool/label_tool.html` when the current
  axis-aligned candidate room boxes are too crude. Exported label drafts still
  need an explicit review/merge step before replacing committed map semantics
  or correspondence assets.

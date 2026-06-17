# B1 / Map 12 Verified Map-Scene Alignment

Current blocker: verified alignment still needs human/operator-reviewed B1/Map 12
correspondence anchors. The scene diagnostic and pre-anchor review/fitter gates
now exist and prove the current state is review-pending, not verified.

Blocker fingerprint:

- blocker_kind: `b1_map12_reviewed_correspondence_anchors`
- root_cause_classification: external review evidence missing
- last_decision_delta: `2rd_floor_seperated` diagnostic, Z-up `x,y`
  correspondence policy, residual-backed waypoint provenance checks, and
  no-camera static preview gate now exist; the remaining stop gate is accepted
  operator anchors.

Last proven evidence:

- `python scripts/maps/render_b1_scene_topdown_diagnostic.py --scene-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --output-dir output/b1-map12/scene-topdown-diagnostic`
  writes `output/b1-map12/scene-topdown-diagnostic/scene_topdown_diagnostic.json`,
  `scene_topdown_diagnostic.html`, and `scene_topdown_diagnostic.png` with
  `up_axis=z`, `horizontal_axes=["x","y"]`,
  `geometry_status=label_inventory_only`, six scene partitions, 16 high-signal
  labels, and validation passed. The artifact is honest label-inventory
  evidence, not a Gaussian asset topdown, not a metric scene projection, and
  not a geometric projection into Map12.
- `python scripts/maps/render_b1_map12_label_tool.py --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --review-manifest assets/maps/b1-map12-alignment-review.json --output-dir output/b1-map12/label-tool`
  writes `output/b1-map12/label-tool/label_tool.html` and
  `label_tool_packet.json`. The HTML editor loads raw Map12 navigation layers,
  scene partition evidence, and the review manifest as separate layers; it
  supports polygon/circle/point draft labels, movable labels, global display
  tilt, and exports `b1_map12_alignment_review_v1` without mutating either raw
  source.
- `python scripts/maps/render_b1_map12_correspondence_review.py --correspondences assets/maps/b1-map12-scene-correspondences.json --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot --output-dir output/b1-map12/correspondence-review`
  writes `output/b1-map12/correspondence-review/correspondence_review.html`
  and `correspondence_review_packet.json` with
  `review_status=review_pending`, `accepted_anchor_count=0`, validation
  passed, and the next action to produce at least six accepted anchors with
  explicit map and metric scene picks. The current right panel is label
  inventory only; it is non-metric context and cannot produce accepted anchors
  until `scene_xyz` is replaced with reviewed metric scene coordinates. The
  picker uses browser-ready
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
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 --alignment-artifact output/b1-map12/alignment-draft/alignment_residuals.json --output output/b1-map12/alignment-draft/readiness_with_alignment.json`
  passes validation while preserving `map12_overlay_status=candidate` and
  `map12_to_b1_usd_transform_status=unverified`.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_scene_topdown_diagnostic.py tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_robot_map12_consistency.py tests/unit/operator_console/test_render_scene_previews.py tests/unit/operator_console/test_static_assets.py -q`
  passes.

Next hypothesis: once a human/operator-reviewed
`assets/maps/b1-map12-scene-correspondences.json` exists with at
least six accepted anchors, the fitter can either promote global alignment to
`verified` under the threshold policy or leave global alignment candidate and
record verified local areas where enough local anchors pass.

Next command/artifact:

```bash
python scripts/maps/fit_b1_map12_scene_alignment.py \
  --correspondences assets/maps/b1-map12-scene-correspondences.json \
  --map-bundle vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot \
  --output-dir output/b1-map12/alignment
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

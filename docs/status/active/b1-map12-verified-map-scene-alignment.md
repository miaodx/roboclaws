# B1 / Map 12 Verified Map-Scene Alignment

Current blocker: verified alignment still needs human/operator-reviewed B1/Map 12
correspondence anchors.

Blocker fingerprint:

- blocker_kind: `b1_map12_reviewed_correspondence_anchors`
- root_cause_classification: external review evidence missing
- last_decision_delta: fitter, residual artifact schema, readiness gate, and
  report summary now exist and reject verification without reviewed residuals

Last proven evidence:

- `python scripts/maps/render_b1_map12_label_tool.py --map-bundle assets/maps/agibot-robot-map-12 --review-manifest assets/maps/b1-map12-alignment-review.json --output-dir output/b1-map12/label-tool`
  writes `output/b1-map12/label-tool/label_tool.html` and
  `label_tool_packet.json`. The HTML editor loads raw Map12 navigation layers,
  scene partition evidence, and the review manifest as separate layers; it
  supports polygon/circle/point draft labels, movable labels, global display
  tilt, and exports `b1_map12_alignment_review_v1` without mutating either raw
  source.
- `python scripts/maps/fit_b1_map12_scene_alignment.py --correspondences docs/status/active/b1-map12-scene-correspondences-draft.json --map-bundle assets/maps/agibot-robot-map-12 --output-dir output/b1-map12/alignment-draft`
  writes `status=insufficient_reviewed_anchors`,
  `global_alignment_status=candidate`, and zero accepted anchors.
- `python scripts/maps/render_b1_map12_correspondence_review.py --correspondences docs/status/active/b1-map12-scene-correspondences-draft.json --map-bundle assets/maps/agibot-robot-map-12 --output-dir output/b1-map12/alignment-draft`
  writes `output/b1-map12/alignment-draft/correspondence_review.html` and
  `correspondence_review_packet.json` with `review_status=review_pending`,
  `accepted_anchor_count=0`, and the next action to produce at least six
  accepted anchors with explicit map and scene picks.
- `.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/check_b1_map12_readiness.py --b1-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated --map12-root vendors/agibot_sdk/artifacts/maps/robot_map_12 --alignment-artifact output/b1-map12/alignment-draft/alignment_residuals.json --output output/b1-map12/alignment-draft/readiness_with_alignment.json`
  passes validation while preserving `map12_overlay_status=candidate` and
  `map12_to_b1_usd_transform_status=unverified`.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_verified_alignment.py tests/contract/maps/test_b1_map12_digital_twin_readiness.py tests/contract/maps/test_b1_map12_navigation_report.py tests/contract/maps/test_cross_environment_semantic_map_parity.py tests/contract/skills/test_scene_gaussian_map_alignment_skill.py -q`
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
  --map-bundle assets/maps/agibot-robot-map-12 \
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

- Use `output/b1-map12/alignment-draft/correspondence_review.html` to drive
  anchor review, then replace
  `docs/status/active/b1-map12-scene-correspondences-draft.json` with a
  reviewed `assets/maps/b1-map12-scene-correspondences.json` asset manifest
  after anchor review.
- Use `output/b1-map12/label-tool/label_tool.html` when the current
  axis-aligned candidate room boxes are too crude. Exported label drafts still
  need an explicit review/merge step before replacing committed map semantics
  or correspondence assets.

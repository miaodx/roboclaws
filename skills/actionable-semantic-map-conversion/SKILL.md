---
name: actionable-semantic-map-conversion
description: Convert robot map artifacts and scene-engine room assets into Actionable Semantic Map Snapshot or public room semantic overlay artifacts.
---

# Actionable Semantic Map Conversion

Use this skill when downstream household tasks need public semantic map
artifacts from offline inputs:

- an offline robot semantic-memory folder such as
  `vendors/agibot_sdk/artifacts/maps/<map>/navigation_memory.json`; or
- a scene-engine / Gaussian asset folder whose room partitions need public
  room labels before a Base Navigation Map is handed to an agent.

## Boundary

This skill works at the map-artifact boundary:

- Input: public `navigation_memory.json`, `agibot/nav2.yaml`,
  `agibot/occupancy.pgm`, `agibot/source.json`, and optional raw map provenance.
- Input: public scene-engine asset partitions such as
  `data/robot-data-lab/scene-engine/data/2rd_floor_seperated/*/scene_gs.usda`.
- Output: `actionable_semantic_map_snapshot_v1` or a
  `scene_room_semantic_overlay_v1` review-evidence artifact.
- Consumer path: pass the snapshot to cleanup or open household tasks through
  `runtime_map_prior=...`. For B1 / Map 12, compile raw Map12 plus
  `assets/maps/b1-map12-alignment-review.json` into a generated runtime bundle
  with `scripts/maps/compile_b1_map12_runtime_bundle.py`.

Do not add an Agibot-specific cleanup loading path. Do not mutate the source
map folder. Do not read or write private cleanup truth such as generated mess
sets, acceptable destination sets, private manifests, scorer target counts, or
hidden target tables.

## Agent Judgment

The deterministic converter parses files, projects map-frame nav goals into the
occupancy grid, checks free cells, assigns stable ids, and scaffolds default
classification/actionability fields.

Agent judgment belongs only in public semantic classification and review state:

- anchor type: `receptacle`, `surface`, `fixture`, `room_area`, `landmark`, or
  `movable_object`;
- affordances such as `navigate`, `observe`, `place`, `place_inside`, `open`,
  and `close`;
- object-vs-fixture decisions;
- `needs_review` or `observe_only` status for ambiguous or low-confidence
  entries.

Scene-engine partition names such as `meeting_room_a` are asset anchors, not
final room truth. Preserve them as `asset_partition_id`; expose task-facing
meaning through `room_label`, `category`, `semantic_source`, `confidence`, and
`review_status`. If the partition/object names are ambiguous, put the room in
`review_queue` and prefer rendering or operator review over guessing.

Movable-object priors must remain `needs_confirm` until current-run evidence
observes them again. A bottle, cup, toy, book, or similar movable object must
not become a static fixture or receptacle candidate.

## Run

Convert an Agibot navigation memory folder:

```bash
python skills/actionable-semantic-map-conversion/scripts/convert_navigation_memory.py \
  vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --output output/maps/robot_map_12/actionable_semantic_map_snapshot.json \
  --summary-json output/maps/robot_map_12/materialized_targets.json
```

Generate a public room semantic overlay from the rebuilt B1 scene-engine asset:

```bash
python skills/actionable-semantic-map-conversion/scripts/generate_scene_room_overlay.py \
  data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --source-bundle-dir assets/maps/agibot-robot-map-12 \
  --output output/maps/b1-map12/scene_room_semantic_overlay.json
```

When the automatically proposed category is not reliable enough, provide an
operator override file:

```json
{
  "rooms": [
    {
      "asset_partition_id": "meeting_room_b",
      "room_label": "Open kitchen",
      "category": "kitchen",
      "semantic_source": "operator_authored_room_overlay",
      "confidence": 0.92,
      "review_status": "accepted"
    }
  ]
}
```

Then pass it with `--overrides-json`.
For the current B1 Map12 rebuilt asset, start from
`examples/b1_map12_room_semantic_overrides.json`, which captures the operator
knowledge that one partition is an open kitchen and the reception partition is
the main hall / living area.

Review the summary before handing the snapshot to a task:

- actionable anchors have materialized `inspection_waypoints`;
- fixture/receptacle/surface anchors have materialized fixture candidates;
- `costmap_disagrees`, `needs_review`, `observe_only`, and `projected` statuses
  are explicit;
- movable objects appear only as non-actionable observed-object priors;
- room overlays keep asset partition ids separate from public semantic labels;
- room overlays are review evidence, not product map bundles;
- low-confidence or generic rooms appear in `review_queue` and should be
  checked with a rendered room overview or operator review;
- no private truth keys are present.

## Acceptance

Run the map contract tests after changing this skill, the converter, or the
snapshot contract:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_actionable_semantic_map_snapshot.py -q
```

For scene room semantic overlays, run:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_scene_room_semantic_overlay.py tests/contract/maps/test_b1_map12_runtime_bundle.py -q
```

For a downstream consumer proof, run a cleanup task with the generated snapshot:

```bash
just run::surface surface=household-world world=agibot-g2/map-12 \
  backend=agibot-gdk intent=cleanup agent_engine=direct-runner \
  evidence_lane=world-public-labels \
  seed=7 runtime_map_prior=output/maps/robot_map_12/actionable_semantic_map_snapshot.json
```

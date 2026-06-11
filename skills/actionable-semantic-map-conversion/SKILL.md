---
name: actionable-semantic-map-conversion
description: Convert Agibot navigation_memory map folders into Actionable Semantic Map Snapshot artifacts.
---

# Actionable Semantic Map Conversion

Use this skill when the input is an offline robot semantic-memory folder such as
`vendors/agibot_sdk/artifacts/maps/<map>/navigation_memory.json` and downstream
household tasks need the same artifact contract as an online
`intent=map-build` run.

## Boundary

This skill works at the map-artifact boundary:

- Input: public `navigation_memory.json`, `agibot/nav2.yaml`,
  `agibot/occupancy.pgm`, `agibot/source.json`, and optional raw map provenance.
- Output: `actionable_semantic_map_snapshot_v1` plus an optional
  materialized-target summary.
- Consumer path: pass the snapshot to cleanup or open household tasks through
  `runtime_map_prior=...`.

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

Movable-object priors must remain `needs_confirm` until current-run evidence
observes them again. A bottle, cup, toy, book, or similar movable object must
not become a static fixture or receptacle candidate.

## Run

```bash
python skills/actionable-semantic-map-conversion/scripts/convert_navigation_memory.py \
  vendors/agibot_sdk/artifacts/maps/robot_map_12 \
  --output output/maps/robot_map_12/actionable_semantic_map_snapshot.json \
  --summary-json output/maps/robot_map_12/materialized_targets.json
```

Review the summary before handing the snapshot to a task:

- actionable anchors have materialized `inspection_waypoints`;
- fixture/receptacle/surface anchors have materialized fixture candidates;
- `costmap_disagrees`, `needs_review`, `observe_only`, and `projected` statuses
  are explicit;
- movable objects appear only as non-actionable observed-object priors;
- no private truth keys are present.

## Acceptance

Run the map contract tests after changing this skill, the converter, or the
snapshot contract:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_actionable_semantic_map_snapshot.py -q
```

For a downstream consumer proof, run a cleanup task with the generated snapshot:

```bash
just run::surface surface=household-world world=agibot-g2/map-12 \
  backend=agibot-gdk intent=cleanup agent_engine=direct-runner \
  evidence_lane=world-oracle-labels \
  seed=7 runtime_map_prior=output/maps/robot_map_12/actionable_semantic_map_snapshot.json
```

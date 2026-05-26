# Auto Semantic Map Build

**Status:** Proposed source plan
**Created:** 2026-05-25
**Source:** Discussion on online-first semantic map build for MolmoSpaces cleanup,
visual grounding, coarse navigation maps, and Agibot map parity.
**Workflow:** Pre-GSD plan. Use this as the source for a later bounded
implementation phase.

## Problem

Roboclaws cleanup already has a public coarse map path: `metric_map()` projects
rooms, fixtures, inspection waypoints, driveable ways, and backend reachability
from a Navigation Map Artifact such as a Nav2 map bundle or an Agibot GDK map
context. Movable cleanup objects are deliberately excluded from that static map;
they become `observed_*` handles only after public camera evidence or
model-declared observation.

The next useful step is to let cleanup runs build and update a semantic view of
the world while the robot is operating. The design should support both:

- online cleanup, where the robot updates the current map while cleaning; and
- offline sweep, where the same map-update loop runs with cleanup actions
  disabled to create a snapshot that can seed later cleanup runs.

The important constraint is to avoid adding unnecessary entities. The agent
should not learn a new `semantic_map()` tool unless a later implementation proves
that a separate query surface is necessary.

## Goals

- Make semantic map build **online-first**: the current cleanup run owns a
  Runtime Metric Map that can grow as observations arrive.
- Keep one agent-facing map surface: extend the meaning of `metric_map()` /
  Agent View rather than adding a new MCP tool.
- Preserve the static/dynamic boundary:
  - static map data contains coarse navigation geometry and fixed or semi-static
    fixtures;
  - small movable cleanup objects appear only as observed handles;
  - large fixture changes appear first as update candidates, not automatic map
    mutations.
- Let offline map build be a no-cleanup-action sweep mode over the same online
  update path.
- Keep the semantic-map builder independent of any one grounding producer:
  simulator labels, coding-agent raw FPV declarations, fake HTTP, and real
  visual grounding service output should all normalize into the same runtime
  map shape.
- Keep private generated mess sets, acceptable destinations, and evaluator
  labels out of Agent View and normal runtime map updates.

## Non-Goals

- Do not add a public `semantic_map` MCP tool in the first implementation.
- Do not silently write runtime observations back into `map_bundle/semantics.json`
  or an Agibot source map context.
- Do not promote small movable cleanup targets into static map semantics.
- Do not make offline sweep a separate map-building architecture. It is a mode
  of the same online map-update logic.
- Do not require a complex next-best-view or global coverage planner for the
  first slice.
- Do not make real Grounding DINO, YOLOE, Qwen, MiMo, vLLM, or SGLang
  dependencies part of the core cleanup runtime.

## Terminology

This plan uses the terms added to `CONTEXT.md`:

- **Runtime Metric Map**: the current-run `metric_map()` view after public
  runtime observation evidence is added.
- **Observed Object Prior**: a movable cleanup-object observation loaded from an
  earlier sweep or snapshot into a later run.
- **Map Update Candidate**: a proposed static-semantics update for a large
  fixture or semi-static furniture item.
- **Semantic Sweep Mode**: a no-cleanup-action mode that navigates and observes
  to build or refresh runtime-map evidence.

## Runtime Map Shape

The first implementation should keep the shape compact and close to existing
contract data:

```json
{
  "schema": "runtime_metric_map_v1",
  "static_map": {
    "rooms": [],
    "fixtures": [],
    "inspection_waypoints": [],
    "driveable_ways": []
  },
  "observed_objects": [
    {
      "object_id": "observed_001",
      "category": "dish",
      "room_id": "kitchen",
      "waypoint_id": "wp_kitchen_01",
      "source_fixture_id": "counter_01",
      "source_observation_id": "raw_fpv_001",
      "image_region": {"type": "bbox", "value": [0.42, 0.51, 0.16, 0.10]},
      "producer_type": "main_cleanup_agent",
      "producer_id": "cleanup_agent",
      "confidence": 0.74,
      "freshness": "current_run",
      "actionability": "actionable",
      "state": "pending"
    }
  ],
  "map_update_candidates": [
    {
      "candidate_id": "fixture_candidate_001",
      "category": "table",
      "room_id": "living_room",
      "source_observation_id": "raw_fpv_014",
      "image_region": {"type": "bbox", "value": [0.12, 0.33, 0.32, 0.24]},
      "confidence": 0.68,
      "promotion_status": "needs_review"
    }
  ]
}
```

`static_map` is a projection of the selected Navigation Map Artifact. It may
contain large fixed or semi-static items such as cabinets, beds, sofas, fridges,
tables, counters, sinks, large receptacles, rooms, waypoints, and driveable
areas.

`observed_objects` contains small movable cleanup targets such as dishes, books,
toys, clothes, pillows, electronics, and other objects that the robot may clean.
These objects must not be written into static map semantics.

`map_update_candidates` contains possible changes to large fixture semantics.
They may be useful during cleanup, but they do not mutate the source map unless
a later promotion workflow accepts them.

## Online And Offline Modes

### Online cleanup

The normal cleanup flow is the primary path:

```text
load static metric_map
optionally load prior runtime-map snapshot
observe / declare_visual_candidates / navigate
update observed_objects and map_update_candidates
derive cleanup worklist from current runtime map
pick/place/open/close according to existing cleanup contract
write final runtime map and report evidence
```

The current runtime map may change after each public observation or grounding
event. This is not a source-map mutation; it is the state of the current run.

### Semantic sweep mode

Offline build is a convenience mode, not a separate architecture:

```text
load static metric_map
follow inspection waypoints and bounded camera view schedule
observe / declare_visual_candidates
update observed_objects and map_update_candidates
disable pick/place/open/close
write runtime-map snapshot for later cleanup runs
```

First slice should use existing inspection waypoints plus a simple bounded
camera-view schedule. Random sampling may be used as a baseline or fallback, but
the default should be deterministic enough to make report comparison useful.
Next-best-view and path-optimized coverage planning are later improvements.

## Prior And Merge Rules

- A runtime-map snapshot may seed a later cleanup run.
- Movable objects loaded from an older snapshot are Observed Object Priors.
- Observed Object Priors default to `actionability=needs_confirm`; they should
  be reobserved in the current run before `pick`.
- When current-run evidence appears to match a prior, create or update a
  current-run observed handle and link it to the prior with
  `prior_object_id` or `snapshot_object_id`.
- Do not assume cross-run identity is exact. The prior is planning evidence, not
  proof that the object is still there.
- Current-run evidence wins over older prior evidence for actionability.

## Grounding Strategy

The semantic-map builder should consume normalized observation events rather
than depending on one model route.

First implementation should support these lanes:

1. **Simulator/control lane**: current deterministic simulator labels or fake
   fixtures, used for CI and schema/report tests.
2. **Coding-agent lane**: the default image-capable cleanup agent creates
   Model-Declared Observations from `camera-raw` or raw FPV evidence. This is
   useful immediately and does not require the HTTP grounding service to be
   finished.
3. **HTTP visual-grounding lane**: once the visual-grounding service is
   integrated, `camera-labels` producer output becomes the preferred real
   camera-label producer for both online cleanup and semantic sweep.

The success path is producer-agnostic: all three lanes should update the same
`observed_objects` shape. The default model/coding-agent route is acceptable for
early local validation, but the longer-term preferred route for automatic map
build is the HTTP visual-grounding service because it can run at higher
frequency, use replaceable detector/refiner pipelines, and avoid spending the
main cleanup agent on every frame.

The first hard implementation gate should not require real Grounding DINO, YOLOE,
Qwen, or MiMo. It should require a deterministic producer plus a fake or mocked
HTTP producer shape. Real visual-grounding pipelines become promotion gates
after the HTTP service is available.

## Success Standards

### Contract success

- `metric_map()` / Agent View can expose a Runtime Metric Map without adding a
  new MCP tool.
- Static map data remains separate from observed movable cleanup objects.
- Small movable cleanup targets never appear in `static_map.fixtures`,
  `Cleanup Map Semantics`, or `map_bundle/semantics.json`.
- Runtime observations never include private generated mess sets, acceptable
  destinations, scorer object results, or private benchmark labels.
- Runtime updates do not silently mutate reusable source map artifacts.

### Online cleanup success

- A cleanup run updates `observed_objects` as public observations arrive.
- The cleanup worklist derives pending/actionable/stale states from the current
  runtime map.
- Current-run observed objects can drive normal cleanup actions only after they
  are grounded and actionable under the existing cleanup contract.
- The final report shows the runtime map state, observed-object lifecycle, and
  producer provenance.

### Semantic sweep success

- A sweep-only run can visit existing inspection waypoints, observe with a
  bounded camera schedule, and produce a runtime-map snapshot without attempting
  cleanup actions.
- The snapshot can seed a later cleanup run as priors.
- Prior movable objects default to needing current-run confirmation before
  action.
- Reports make clear that the sweep produced map evidence, not private cleanup
  target truth.

### Grounding success

- Deterministic/control producer evidence updates the runtime map in tests.
- Coding-agent Model-Declared Observations can update the same runtime map shape
  for early local validation.
- HTTP visual-grounding producer output can later update the same runtime map
  without schema or MCP-tool changes.
- Producer provenance, confidence, image region, observation id, room id, and
  waypoint id are preserved for each accepted observed object.
- Failed producer calls produce visible failure evidence and do not fabricate
  simulator fallback labels.

### Report/checker success

- The report distinguishes `static_map`, `observed_objects`, and
  `map_update_candidates`.
- The checker can reject any runtime map that leaks private truth or promotes
  small movable objects into static map semantics.
- The checker can require prior objects to remain non-actionable until
  confirmed by current-run evidence.
- The checker can prove semantic sweep mode did not call cleanup actions.

## Implementation Slices

### Slice 1: Runtime map schema and report evidence

- Add a runtime-map payload builder from existing `metric_map`, observed
  handles, model-declared observation evidence, and cleanup worklist state.
- Persist the payload in `run_result.json` / `agent_view.json`.
- Render compact runtime-map sections in the cleanup report.
- Add checker rules for static/dynamic separation and private-data exclusion.

### Slice 2: Online cleanup updates

- Update runtime map as `observe`, `declare_visual_candidates`, and cleanup
  lifecycle events occur.
- Mark actionability states such as `prior`, `needs_confirm`, `actionable`,
  `pending`, `held`, `placed`, `stale`, and `skipped`.
- Keep small movable objects out of static map payloads.

### Slice 3: Semantic sweep mode

- Add a no-cleanup-action sweep mode that runs the same observation and
  grounding update path.
- Use existing inspection waypoints and a bounded camera-view schedule.
- Write a runtime-map snapshot artifact that can seed a later cleanup run.

### Slice 4: Snapshot priors and merge

- Load a prior runtime-map snapshot into a new cleanup run.
- Keep prior objects non-actionable until current-run confirmation.
- Link confirmed current-run handles back to prior ids without claiming exact
  cross-run identity.

### Slice 5: HTTP visual-grounding promotion

- After the HTTP grounding service lands, route producer output into the same
  runtime map.
- Compare coding-agent, fake HTTP, simulator/control, and real HTTP producer
  lanes using identical report/checker surfaces.

## Open Implementation Defaults

These should not block planning:

- Exact field names for artifact paths, as long as `static_map`,
  `observed_objects`, and `map_update_candidates` remain conceptually separate.
- Exact camera yaw schedule for sweep mode.
- Whether runtime-map snapshots live under `map_snapshot/`,
  `runtime_metric_map.json`, or another run-local artifact path.
- Exact heuristic for linking a prior object to a current-run observation.
- Whether map-update-candidate promotion is an operator-only command or a later
  reviewed batch exporter.

## GSD Handoff

Preferred first phase:

```text
gsd-plan-phase <phase> --prd docs/plans/auto-semantic-map-build.md
```

Start with Slice 1 and Slice 2. Do not block the first phase on a real visual
grounding model or a global coverage planner.

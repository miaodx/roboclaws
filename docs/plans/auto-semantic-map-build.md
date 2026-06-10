<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0525-autoplan-restore-20260526-132517.md -->

# Auto Semantic Map Build

**Status:** Proposed source plan
**Created:** 2026-05-25
**Source:** Discussion on online-first semantic map build for MolmoSpaces cleanup,
visual grounding, coarse navigation maps, and Agibot map parity.
**Workflow:** Pre-GSD plan. Use this as the source for a later bounded
implementation phase.

**Deployment target:** the same public task/profile/tool layers should support
eventual physical-robot runs. Early real-robot acceptance may prove only
navigation, observation, and runtime-map evidence while manipulation remains a
declared blocked capability.

**Accepted direction, 2026-05-29:** make the minimal source map the real-robot
mainline. Rich authored semantic map bundles may remain as development,
simulation, or explicitly selected aids, but the product path should assume a
sparse occupancy/free-space map and let `semantic-map-build` enrich the
Runtime Metric Map through public observation evidence. Cleanup should consume
that enriched Runtime Metric Map instead of depending on hand-authored fixture
semantics.

## Problem

Roboclaws cleanup already has a public coarse map path: `metric_map()` projects
rooms, fixtures, inspection waypoints, driveable ways, and backend reachability
from a Navigation Map Artifact such as a Nav2 map bundle or an Agibot GDK map
context. Movable cleanup objects are deliberately excluded from that static map;
they become `observed_*` handles only after public camera evidence or
model-declared observation.

That path is currently richer than many physical robot maps. Agibot G2 map
artifacts, for example, can start as occupancy/free-space data without public
rooms, fixtures, or inspection waypoints. To make simulator rehearsal predictive
for that path, semantic-map-build needs an occ-only/minimal-map mode where the
runtime map is enriched from public observation rather than seeded from a
complete authored semantic bundle.

The next useful step is to let household robot tasks build and update a
semantic view of the world while the robot is operating. Cleanup is the first
consumer, but it should not own the map-building abstraction. The design should
support both:

- online cleanup, where the robot updates the current map while cleaning; and
- offline sweep, where the same map-update loop runs with cleanup actions
  disabled to create a snapshot that can seed later cleanup runs.

The important constraint is to avoid adding unnecessary entities. The agent
should not learn a new `semantic_map()` tool unless a later implementation proves
that a separate query surface is necessary.

## Goals

- Make semantic map build **online-first**: the current cleanup run owns a
  Runtime Metric Map that can grow as observations arrive.
- Treat minimal Navigation Map Artifacts as the default deployment starting
  point. The builder should recover cleanup-usable room/fixture/receptacle
  semantics from public observation evidence instead of assuming a preauthored
  semantic map.
- Treat semantic map build as a task-neutral world-understanding capability:
  the clean public task name should be `semantic-map-build`, and cleanup should
  consume its snapshots rather than own the abstraction.
- Keep the public task layer separate from the skill layer: `semantic-map-build`
  and `household-cleanup` are Runnable Tasks; each task selects or defaults an
  Agent Skill that owns prompt strategy, scripts, recovery, and examples.
- Prefer a clean task-neutral contract/profile name such as
  `household_world_v1` for the shared surface instead of making the long-term
  profile cleanup-owned.
- Keep `household_world_v1` broad but not vague: it should cover household
  world understanding and evidence capture, while each Runnable Task keeps its
  own success criteria/report gates and each selected Agent Skill declares its
  capability requirements.
- Keep one agent-facing map surface: extend the meaning of `metric_map()` /
  Agent View rather than adding a new MCP tool.
- Support an occ-only/minimal-map rehearsal mode in simulation so the agent sees
  only occupancy/free-space geometry, pose/frame metadata, safety bounds, and
  generated exploration candidates until public observations enrich the Runtime
  Metric Map.
- Preserve the static/dynamic boundary:
  - static map data contains coarse navigation geometry and fixed or semi-static
    fixtures;
  - public evidence may create Runtime Metric Map anchors for fixed or
    semi-static rooms, surfaces, receptacles, and fixtures;
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
- Preserve simulator/hardware parity: physical backends should reuse the same
  Runnable Task, capability profile, and MCP tool shape, while reporting
  backend provenance, blocked capabilities, safety gates, and operator-selected
  physical map context.

## Non-Goals

- Do not add a public `semantic_map` MCP tool in the first implementation.
- Do not make semantic map build a cleanup profile. It should be a first-class
  task intent with cleanup/manipulation disabled.
- Do not make `household_world_v1` a monolithic profile for every possible
  household task. It should stay world-understanding only; Runnable Tasks and
  their selected Agent Skills compose it through capability requirements when
  they need cleanup, search, inspection, photo capture, navigation rehearsal, or
  later household behaviors.
- Do not require backward-compatible command names when the public task/profile
  surface is cleaned up.
- Do not silently write runtime observations back into `map_bundle/semantics.json`
  or an Agibot source map context.
- Do not promote small movable cleanup targets into static map semantics.
- Do not make rich authored room/fixture semantics the normal real-robot
  prerequisite. They may stay as CI/dev fixtures or explicit comparison modes,
  but the fast hardware path starts from minimal maps.
- Do not make offline sweep a separate map-building architecture. It is a mode
  of the same online map-update logic.
- Do not require a complex next-best-view or global coverage planner for the
  first slice.
- Do not let Codex or another Agent Skill directly invent arbitrary physical
  robot coordinates. For minimal maps, system-generated safe exploration
  candidates form the first navigation surface; physical backends still apply
  localization, run-enablement, and waypoint/reachability gates.
- Do not make real Grounding DINO, YOLOE, Qwen, MiMo, vLLM, or SGLang
  dependencies part of the core cleanup runtime.

## Terminology

This plan uses the terms added to `CONTEXT.md`:

- **Minimal Navigation Map Artifact**: an intentionally sparse map source that
  exposes occupancy/free-space geometry, localization/safety context, and frame
  metadata without preauthored room, fixture, or object semantics.
- **Runtime Metric Map**: the current-run `metric_map()` view after public
  runtime observation evidence is added.
- **Semantic Map Build Task**: a first-class Runnable Task that navigates and
  observes to produce a Runtime Metric Map snapshot for later household tasks.
- **Household World Capability Profile**: the clean task-neutral capability
  profile for shared mapping/perception/world-state tools that can support map
  build, cleanup, inspection, search, and other household tasks. It excludes
  task-specific manipulation tools and success criteria, but may include
  bounded navigation to public rooms or inspection waypoints for evidence
  capture.
- **Skill Capability Requirements**: the profiles, capability modules, required
  tools, optional tools, blocked capabilities, and evidence gates an Agent Skill
  declares. A cleanup skill can require `household_world_v1` plus manipulation
  capabilities without redefining the world contract.
- **Real-Robot Deployment Target**: a physical acceptance target that reuses
  the same public task/profile/tool layers as simulation, while backend variants
  declare physical provenance, blocked capabilities, and safety gates.
- **Observed Object Prior**: a movable cleanup-object observation loaded from an
  earlier sweep or snapshot into a later run.
- **Map Update Candidate**: a proposed static-semantics update for a large
  fixture or semi-static furniture item.
- **Public Semantic Anchor**: a public-evidence-backed room area, surface,
  receptacle, fixture, or observation waypoint in the Runtime Metric Map.
  Anchors carry stable id, label/category, waypoint or pose link, affordances
  when known, producer provenance, and confidence. Cleanup may use
  fixture/receptacle anchors as destination hints, but they do not mutate the
  source map unless a later review workflow accepts them.
- **Semantic Sweep Mode**: a no-cleanup-action mode that navigates and observes
  to build or refresh runtime-map evidence.
- **Generated Exploration Candidate**: a safe navigation or observation
  candidate derived from public free-space geometry and safety bounds. The agent
  may choose among candidates, but they are not source-map semantics or
  arbitrary robot-motion permission.

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

For the minimal-map mainline, the source projection may start with no authored
rooms, fixtures, or inspection waypoints beyond generated exploration
candidates. Runtime evidence should add Public Semantic Anchors for fixed or
semi-static places the robot can use later: room areas, surfaces, receptacles,
fixtures, and observation waypoints. These anchors are current-run public
evidence, not a silent source-map rewrite.

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

### Minimal-map rehearsal mode

Minimal-map rehearsal is the simulator bridge to raw physical maps:

```text
load occupancy/free-space map plus pose/frame/safety metadata
derive safe exploration candidates from public free space
project candidates as generated_* waypoint entries in metric_map
agent chooses candidate order through semantic-map-build skill
navigate / observe / declare_visual_candidates
update runtime semantic anchors, fixture/receptacle candidates, observed objects,
and map candidates
disable source-map mutation and cleanup actions
write runtime-map snapshot plus candidate provenance
```

This mode should run first in simulation, using MolmoSpaces or another backend
with private truth hidden from Agent View. The acceptance bar is not cleanup
success; it is evidence that a sparse map can be enriched into a useful Runtime
Metric Map through the same public observation path a physical Agibot run will
use.

Default command surface for the first slice was superseded on 2026-06-10 by the
orthogonal public launch grammar in
`docs/plans/operator-console-orthogonal-launch-refactor.md`. Use:
`just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=<lane> map_mode=minimal scenario_setup=baseline`.
Keep the deterministic direct runner until the minimal-map contract and report
are stable. Do not add a new MCP tool for exploration candidates in this slice;
represent them as `generated_*` inspection waypoints and use the existing
`navigate_to_waypoint` tool.

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

### Minimal-mainline acceptance

- The default implementation path for physical household world work can start
  from a Minimal Navigation Map Artifact: occupancy/free-space geometry,
  localization/safety context, pose/frame metadata, and generated exploration
  candidates, with no required authored rooms, fixtures, or inspection
  waypoints.
- Rich authored semantic map bundles remain optional dev/test or explicitly
  selected comparison inputs. A real-robot acceptance claim must not depend on
  hand-authored room/fixture semantics being present before the run.
- The agent may choose among generated exploration candidates, but it never
  invents arbitrary robot coordinates. Every executable navigation target is
  generated or verified by the backend/operator navigation layer.
- The first accepted minimal-map artifact and report must show candidate
  provenance, visited/unvisited state, and the absence of hidden source rooms,
  fixtures, source waypoint ids, and private cleanup truth in Agent View.

### Semantic-anchor acceptance

- A semantic-map-build run over a minimal source map can create Public Semantic
  Anchors for fixed or semi-static places: room areas, surfaces, receptacles,
  fixtures, and observation waypoints.
- Each accepted anchor includes a stable public id, label/category, waypoint or
  pose link, affordances when known, producer provenance, confidence, and source
  observation evidence.
- Public Semantic Anchors may appear in the current Runtime Metric Map and in
  run-local snapshots; they must not silently mutate the source Navigation Map
  Artifact or `map_bundle/semantics.json`.
- Small movable cleanup objects are never promoted into Public Semantic Anchors,
  static fixtures, or source map semantics. They remain observed handles or
  priors.
- Ambiguous fixture/receptacle detections remain map update candidates or
  low-confidence anchors that cleanup can ignore; they must not be converted
  into confident destinations without public evidence.

### Contract success

- `metric_map()` / Agent View can expose a Runtime Metric Map without adding a
  new MCP tool.
- Static map data remains separate from observed movable cleanup objects.
- Small movable cleanup targets never appear in `static_map.fixtures`,
  `Cleanup Map Semantics`, or `map_bundle/semantics.json`.
- Runtime observations never include private generated mess sets, acceptable
  destinations, scorer object results, or private benchmark labels.
- Runtime updates do not silently mutate reusable source map artifacts.
- A minimal-map run can start without preauthored rooms, fixtures, or
  inspection waypoints while still exposing bounded navigation geometry and
  generated exploration candidates.
- Runtime-map snapshots distinguish `static_map`, Public Semantic Anchors,
  `observed_objects`, priors, and `map_update_candidates` clearly enough for
  checkers and reports to validate each boundary independently.

### Online cleanup success

- A cleanup run updates `observed_objects` as public observations arrive.
- The cleanup worklist derives pending/actionable/stale states from the current
  runtime map.
- Current-run observed objects can drive normal cleanup actions only after they
  are grounded and actionable under the existing cleanup contract.
- The final report shows the runtime map state, observed-object lifecycle, and
  producer provenance.

### Cleanup-consumer acceptance

- `household-cleanup` can consume a `runtime_map_prior=<runtime_metric_map.json>`
  produced by a minimal-map `semantic-map-build` run.
- Fixture/receptacle Public Semantic Anchors from the current Runtime Metric Map
  can be used as public destination hints for cleanup planning.
- Movable objects loaded from an older runtime-map snapshot enter cleanup only
  as Observed Object Priors with `actionability=needs_confirm`; they cannot be
  picked until current-run camera evidence confirms them.
- A cleanup run that starts from a minimal-map snapshot must not read hidden
  generated mess sets, acceptable destinations, scorer results, or authored
  fixture truth to recover destinations.
- A successful consumer run produces a report showing which anchors came from
  the prior, which observations confirmed current objects, and which cleanup
  decisions used public destination hints.

### Semantic sweep success

- A sweep-only run can visit existing inspection waypoints, observe with a
  bounded camera schedule, and produce a runtime-map snapshot without attempting
  cleanup actions.
- In minimal-map rehearsal, a sweep-only run can visit generated exploration
  candidates instead of preauthored inspection waypoints.
- The snapshot can seed a later cleanup run as priors.
- Prior movable objects default to needing current-run confirmation before
  action.
- Reports make clear that the sweep produced map evidence, not private cleanup
  target truth.

### G2 map-build pilot acceptance

- The first Agibot G2 hardware acceptance target is `semantic-map-build`, not
  full physical cleanup.
- The accepted pilot proves operator/backend-approved waypoint navigation,
  robot-local `head_color` or RAW_FPV observation capture, visual candidate
  declaration or grounding output, Runtime Metric Map snapshot writing, and a
  report with backend provenance and safety gates.
- Manipulation, object/receptacle navigation, pick, place, open, and close
  remain declared blocked capabilities in the G2 map-build pilot.
- Real G2 readiness evidence uses a real camera grounding lane such as
  `camera-labels` with an external visual-grounding producer. Simulator labels,
  `world-labels`, or `visual_grounding=sim` may validate contracts but do not
  satisfy hardware perception acceptance.
- A G2 snapshot may seed a later online run only as public world evidence:
  fixture/receptacle anchors may guide destinations, while movable-object priors
  still need current camera confirmation before manipulation.

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
- The checker can require minimal-mainline runs to expose generated exploration
  candidates and hide authored source rooms/fixtures/waypoint ids from Agent
  View.
- The checker can reject source-map mutation and private-truth leakage when
  Public Semantic Anchors are created from observations.
- The checker can prove semantic sweep mode did not call cleanup actions.

## Implementation Slices

## Intuitive-Flow Review Reconciliation

**Review status:** Reconciled inline on 2026-05-26 because the gstack
`autoplan` executable tree was not available in this checkout; only the skill
document was present. The restore point above preserves the original plan state.

Accepted review decisions:

- Keep the first implementation to Slices 1 and 2: runtime-map schema/report
  evidence plus online cleanup updates.
- Reuse existing public cleanup contract surfaces: `metric_map()`, Agent View,
  `observed_objects`, `cleanup_worklist`, model-declared observations, and the
  existing fake/HTTP visual-grounding lanes.
- Add `runtime_metric_map_v1` as a payload inside Agent View and run artifacts,
  not as a new MCP tool.
- Treat `static_map`, `observed_objects`, and `map_update_candidates` as
  separate report/checker sections. `map_update_candidates` may be empty in the
  first implementation, but the schema field must exist.
- Require checker coverage for private-truth exclusion, no movable objects in
  static map fixtures, prior actionability rules when priors are present, and
  sweep-mode cleanup-action prohibition once sweep mode exists.
- Defer Slice 3 and later work until Slices 1 and 2 are artifact-backed:
  semantic sweep mode, snapshot priors/merge, and real visual-grounding promotion
  remain follow-up slices.

Rejected/deferred review decisions:

- Do not add `semantic_map()` or any separate public MCP tool in this phase.
- Do not introduce a new persistent source-map writer or mutate
  `map_bundle/semantics.json`.
- Do not require real detector/refiner models for the first implementation gate;
  deterministic, model-declared, and fake HTTP producer evidence are sufficient.

## Clean-Slate Layering Decision

Discussion on 2026-05-26 accepted a cleaner task/skill/capability/profile split
with no backward-compatibility requirement for old public names:

- `semantic-map-build` should become the first-class public Runnable Task for
  building a Runtime Metric Map snapshot. It is not a cleanup profile, Agent
  Skill, or new MCP tool.
- `household-cleanup` should remain a first-class public Runnable Task for
  cleanup runs, not the name of the reusable world capability profile.
- Cleanup should be a consumer of household world evidence, not the owner of the
  semantic-map abstraction.
- The long-term shared capability-profile name should be task-neutral. Prefer
  `household_world_v1` over `molmospaces_cleanup_v1` or another cleanup-owned
  name for the reusable world-understanding surface.
- `household_world_v1` is world-understanding only. It may include
  `metric_map()`, `fixture_hints()`, `navigate_to_room()`,
  `navigate_to_waypoint()`, `observe()`, `adjust_camera()`,
  `declare_visual_candidates()`, runtime-map snapshots, observed-object
  priors, and map update candidates.
- `household_world_v1` should exclude manipulation and task-completion tools
  such as `pick`, `place`, `open_receptacle`, and `close_receptacle`.
- Task-specific household Runnable Tasks compose reusable capability profiles
  through their selected Agent Skills and skill capability requirements. Future
  tasks can cover object search, inspection, photo capture, navigation
  rehearsal, or later household work without changing the world capability
  profile.
- `household-cleanup` can accept
  `runtime_map_prior=<runtime_metric_map.json>` from an earlier
  `semantic-map-build` run; its selected cleanup skill consumes that prior as
  part of its strategy.
- Backend variants should be expressed as variant/config metadata, not profile
  names: examples include `molmospaces_subprocess`, `api_semantic_synthetic`,
  `agibot_g2`, and `ros2_nav2`.
- Real-robot deployment should reuse these same layers. A physical
  `semantic-map-build` or `household-cleanup` run should differ by backend
  variant, provenance, safety gates, and blocked-capability status, not by
  inventing a separate robot-only task/profile taxonomy.
- `Semantic Sweep Mode` remains the internal no-cleanup-action execution mode
  behind the public `semantic-map-build` task.
- The clean naming does not change the map contract boundaries: no new
  `semantic_map()` MCP tool, no source-map mutation, and no private evaluator
  truth in the Runtime Metric Map.

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

### Slice 3A: Minimal-map simulator rehearsal

- Add an occ-only/minimal map source for simulation that hides rooms, fixtures,
  and inspection waypoints from Agent View at startup.
- Generate safe exploration candidates from occupancy/free-space geometry,
  current pose, and safety bounds.
- Expose candidates as `generated_*` waypoint entries and run
  `semantic-map-build direct ... map_mode=minimal` over those candidates with
  cleanup actions disabled.
- Produce Runtime Metric Map Public Semantic Anchors for observed fixed or
  semi-static rooms, surfaces, receptacles, fixtures, and observation waypoints
  so a later cleanup run can use the snapshot without relying on the old
  authored semantic bundle.
- Reuse `navigate_to_waypoint` for candidate navigation; defer a dedicated
  `navigate_to_exploration_candidate` tool until waypoint projection proves
  insufficient.
- Require the report to show candidate provenance, runtime enrichment, and no
  private-truth leakage.

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

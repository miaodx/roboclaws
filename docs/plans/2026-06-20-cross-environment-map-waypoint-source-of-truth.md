---
plan_scope: cross-environment-map-waypoint-source-of-truth
status: Implemented
created: 2026-06-20
last_reviewed: 2026-06-21
implementation_allowed: true
source:
  - discussion about repeated waypoint and Nav2 map bundle fixes
  - bug fix f26f2f08 preserving MolmoSpaces sim bundle static landmarks
  - follow-up decision direction: Base Navigation Map should have one minimal
    required schema across sim, real robot, and digital twin, with no
    environment-specific optional semantic fields
related_context:
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/domain.md
  - docs/human/technical-design.md
  - docs/plans/2026-06-15-cross-environment-semantic-map-parity.md
  - docs/plans/2026-06-17-sim-map-surface-simplification.md
  - docs/plans/2026-06-19-base-waypoint-source-contract.md
---

# Cross-Environment Base Navigation Map Source Of Truth

## Status

Status: Implemented.

Implementation progress:

- Checkpoint 1 is implemented by `validate_base_navigation_map_v1_bundle()`.
  B1 / Map 12 generated bundles now pass the strict Base Navigation Map v1
  validator, current MolmoSpaces bundles expose explicit known gaps, and
  targeted negative tests cover missing labels/categories, empty waypoints,
  malformed area bindings, and forbidden fixture/object waypoint fields.
- Checkpoint 2 is implemented by the shared area-based
  `roboclaws.maps.base_waypoints.BaseWaypointBuilder`, with B1 / Map 12 wired
  through the shared builder and focused tests covering B1 waypoint
  preservation, irregular or blocked areas, and forbidden fixture/object/private
  truth inputs.
- Checkpoints 3-5 are implemented by the MolmoSpaces preparation split, product
  Agent View snapshot fallback removal, and runtime consumption cleanup. The
  active MolmoSpaces scene bundle validates as Base Navigation Map v1, product
  runtime copies the selected source bundle into run artifacts, and the
  deterministic direct-runner route observes objects from the generated bundle.

This document records the implemented execution plan for reducing map and
waypoint source-of-truth entropy across simulator, real robot, and Digital Twin
paths. The numbered checkpoints below are ordering and acceptance gates.

The B1 / Map 12 real-robot and Digital Twin path satisfies the key direction:
one Base Navigation Map generator owns map rooms and base waypoints, and the
Digital Twin proof sidecar does not alter the base map. The simulator path now
uses the same artifact-first direction for product bundles.

## Problem

The household map and waypoint logic has been cleaned up several times, but it
still feels too complex because multiple code paths can derive, project, hide,
or regenerate related pieces of the same map state:

- source map geometry;
- base inspection waypoints;
- room or navigation-area semantics;
- static fixture or landmark semantics;
- public Agent View projection;
- Runtime Metric Map observations;
- report or operator-console previews.

The recent MolmoSpaces bug showed the concrete risk. The sim Nav2 bundle
generation path accidentally used the Agent View static fixture projection. The
Agent View intentionally hides authored fixtures, so generated
`semantics.json` files had empty `static_landmarks`. Runtime cleanup then had
waypoints but no fixture anchors, so observation and cleanup behavior degraded.

The bug fix was necessary for the current behavior, but it also exposed the
larger design problem. The better long-term target may be stricter than the
current implementation: Base Navigation Map should not preload fixture,
receptacle, object, or Digital Twin object semantics at all. It should provide
only the smallest navigation and room-semantic context that every environment
can provide in the same shape.

## Current Model

There are four concepts that should stay distinct:

```text
Source Map / Prebuilt Robot Map Bundle
  Static map artifact: occupancy, navigation areas with semantic labels, base
  inspection waypoints, and frame metadata.

Agent View
  Runtime public projection for the agent. It deliberately hides authored
  fixture tables, private scoring truth, generated mess truth, and relocation
  setup truth.

Runtime Metric Map
  Public run evidence created or enriched during map-build, cleanup, and
  observation. It may contain observed objects, public semantic anchors, target
  candidates, and map-update candidates.

Report / Preview
  Human review evidence. It must not become a runtime source of truth.
```

The desired boundary is simple:

```text
Base Navigation Map artifact -> runtime contract consumes -> Agent View projects
Runtime observations -> Runtime Metric Map
Reports render artifacts and evidence
```

The current sim path still partially violates that simplicity because the
offline source-map generation path instantiates the runtime contract.

## Working Recommendation

Promote a single Base Navigation Map v1 preparation contract and make runtime
environment-agnostic:

```text
Environment-specific source evidence
  -> Base Navigation Map v1 preparation
  -> strict validation
  -> product runtime consumes the validated artifact
```

The environment-specific part stops at artifact preparation. Product runtime
should not care whether the artifact was prepared from MolmoSpaces, Agibot
robot maps, or Digital Twin scene evidence.

For this plan, the recommended shape is:

- Use one required Base Navigation Map v1 schema for sim, real robot, and
  Digital Twin.
- Require navigation-area semantics in that schema. High-level household tasks
  need room/category priors such as kitchen, bedroom, living room, corridor,
  bathroom, storage, and open area.
- Use Digital Twin scene labels only as offline evidence to fill the same
  required navigation-area semantic fields. Do not expose richer Digital Twin
  object, fixture, or receptacle data as a runtime contract.
- Treat Agibot `navigation_memory.json` and operator-authored waypoints as
  migration/preparation evidence, not as runtime source-of-truth branches.
- Generate or normalize base inspection waypoints through one area-based
  `BaseWaypointBuilder` and validator.
- Keep runtime-generated target candidates separate from base waypoints.

This intentionally reduces the design to one question at runtime:

```text
Does the selected Base Navigation Map v1 artifact validate?
```

If yes, every environment follows the same runtime path. If no, launch or
artifact preparation fails loudly.

## Approved Decisions

The following decisions are locked for the first implementation pass:

- Base Navigation Map v1 is the product start-of-run map contract for
  simulator, real robot, and Digital Twin paths.
- A Base Navigation Map v1 product artifact must contain navigation areas with
  semantic labels/categories and non-empty base inspection waypoints.
- Base inspection waypoints are area-inspection poses, not object, fixture,
  receptacle, cleanup-target, or Digital Twin object hints.
- Digital Twin labels may be used offline to fill the same required room or
  navigation-area semantic fields used by the real robot. Runtime must not
  carry a richer Digital Twin-only map contract.
- `navigation_memory.json` and hand-authored waypoint files may be migration
  evidence or builder seeds, but product runtime must consume only the
  validated canonical waypoint rows in the selected Base Navigation Map
  artifact.
- Product runtime must not regenerate a source map or base waypoint set from
  Agent View. Missing bundles or missing base waypoints are launch/preparation
  errors.
- Fixture/object/receptacle/static-scoring truth is excluded from Base
  Navigation Map v1. If cleanup still needs any such signal, it must come from
  current-run Runtime Metric Map observations or a separately approved uniform
  contract.

Human review remains useful for the room/category vocabulary, but it is not a
blocker for starting implementation with the categories listed below. Unknown
or disputed labels may exist only in review artifacts, not in product Base
Navigation Map v1 bundles.

## Current Environment Flows

### MolmoSpaces Simulation

Current prebuilt bundle generation:

```text
MolmoSpaces scene
  -> build cleanup backend session
  -> RealWorldCleanupContract(..., allow_synthetic_map_projection=True)
  -> synthetic rooms and waypoints from scenario fixtures
  -> source-map fixture projection
  -> write_nav2_map_bundle()
  -> assets/maps/molmospaces/<scene_source>/<scene_index>/
```

Current product runtime:

```text
just run::surface surface=household-world world=molmospaces/... backend=mujoco
  -> select checked-in Nav2 bundle
  -> RealWorldCleanupContract(map_bundle_dir=...)
  -> load metric_map, static_landmarks, inspection_waypoints
  -> Agent View exposes Base Navigation Map and hides authored fixture table
  -> cleanup/map-build visits public inspection_waypoints
  -> observe() enriches Runtime Metric Map
```

Positive state:

- Product runtime now requires a generated bundle and fails loudly if it is
  missing.
- Base waypoints come from the bundle in product runs.

Remaining complexity:

- Bundle generation still uses `RealWorldCleanupContract`, which is also the
  runtime Agent View boundary.
- `allow_synthetic_map_projection=True` remains a special offline/test escape
  hatch.
- Source-map semantics and Agent View semantics are both reachable through the
  same contract object.
- Current generated sim bundles still include static landmarks to support the
  current cleanup behavior. This plan is considering a stricter future where
  Base Navigation Map v1 does not include those fixture semantics.

### Agibot Real Robot

Current source direction:

```text
Agibot map artifacts / navigation memory / operator-authored context
  -> Roboclaws map artifact conversion or validation
  -> Metric Map / Runtime Map Prior Snapshot / Nav2-shaped bundle
  -> runtime contract consumes artifact
```

Positive state:

- The real robot path is mostly artifact-first.
- Roboclaws is a converter, validator, public projector, and reporter rather
  than the original map author.

Remaining complexity:

- Converted artifacts still need strict validation so missing waypoints or
  missing room semantics fail before runtime.
- Real robot, digital twin, and sim vocabulary must stay aligned: source map
  frame, navigation areas, room semantic labels, inspection waypoints, and
  Runtime Metric Map should mean the same thing.
- Room semantics may be operator-authored today, but the preferred direction is
  to reuse Digital Twin labels when they are the already-maintained team source
  of room names.
- Agibot navigation memory can remain input evidence during migration, but it
  should not remain a separate runtime waypoint source once Base Navigation Map
  v1 is enforced.

### B1 / Map 12 Digital Twin

Current source direction:

```text
Agibot source map and navigation_memory.json
  + B1 scene assets / scene partitions
  + alignment and correspondence evidence
  -> compiled runtime bundle / runtime prior
  -> runtime, report, and operator preview consume
```

Positive state:

- Digital twin work reuses the real robot source-map direction.
- Scene geometry and semantic labels are added through explicit alignment or
  correspondence evidence rather than silently replacing the navigation map.

Remaining complexity:

- Digital twin has more sources by nature: source map, scene partitions,
  alignment proof, render readiness, and runtime prior capability exposure.
- The rule must be explicit: Digital Twin scene information may enrich the
  Base Navigation Map only by producing the same required room or navigation
  area semantic fields. It is not a second navigation map and not a runtime
  source of extra object, receptacle, or fixture truth.
- Digital Twin should not make runtime more capable than real robot simply
  because it has more raw scene information. Any field that becomes product
  visible must be promoted into the uniform Base Navigation Map schema.

## Target State

Use one strict artifact-first Base Navigation Map contract for all product
environments. "Strict" means a field is either required for every environment or
not part of Base Navigation Map v1. There should be no environment-specific
optional semantic fields.

```text
Base Navigation Map v1 owns:
  - source map frame;
  - occupancy / free-space geometry;
  - navigation areas;
  - semantic label and semantic category for every navigation area;
  - base inspection waypoints;
  - provenance and validation metadata.

Runtime Contract owns:
  - consuming the selected source map bundle;
  - runtime pose and visited state;
  - observations;
  - Runtime Metric Map enrichment;
  - public Agent View projection.

Agent View owns:
  - safe public map projection;
  - public inspection waypoints;
  - runtime observations;
  - no authored fixture table, private scoring truth, relocation truth, or
    generated mess truth.
```

In this target state:

- Simulation, real robot, and digital twin all start from a Base Navigation Map
  v1 artifact with the same required fields.
- Base inspection waypoints have one source of truth: the selected source map
  bundle.
- Runtime may create target-specific inspection candidates only after
  current-run observations.
- Missing source map artifacts, missing navigation-area semantics, empty base
  waypoints, or malformed frame/geometry metadata fail loudly.
- No product path silently regenerates map bundles from Agent View.
- Digital Twin may be used as an offline source for required room or
  navigation-area labels. Its richer scene/object information is not exposed by
  default and does not create a special Digital Twin runtime contract.
- Future expansion must be uniform. If Base Navigation Map later needs a new
  field, every product environment must provide it before the field becomes
  part of the product contract.

## Base Navigation Map V1 Required Fields

This is the proposed minimum product schema. It is intentionally small.

### Source Frame And Occupancy

- source map frame id;
- resolution;
- origin;
- width and height;
- occupancy values;
- occupancy image or equivalent grid artifact.

### Navigation Areas

Each navigation area must have:

- stable `area_id`;
- source-frame polygon or equivalent navigable area geometry;
- `semantic_label`, preferably reusing Digital Twin / scene-partition naming
  when that is the maintained team label source;
- normalized `semantic_category`, for example `kitchen`, `bedroom`,
  `living_room`, `corridor`, `bathroom`, `storage`, or `open_area`;
- geometry source;
- label source;
- validation status.

The product Base Navigation Map should not ship with unlabeled areas. If an
area cannot be labeled yet, the artifact-preparation step should fail or stay
in review rather than producing a weaker product bundle.

Suggested initial `semantic_category` vocabulary:

- `kitchen`;
- `bedroom`;
- `living_room`;
- `dining_area`;
- `bathroom`;
- `corridor`;
- `entry`;
- `storage`;
- `utility`;
- `open_area`;
- `unknown_review_required`.

`unknown_review_required` is allowed only inside preparation or review
artifacts. It is not valid for a product Base Navigation Map v1 bundle.

### Base Inspection Waypoints

Base inspection waypoints should be produced, or at least normalized, by one
canonical `BaseWaypointBuilder` for every product environment. The builder
inputs are only Base Navigation Map fields:

- occupancy/free-space;
- navigation areas with required semantic labels/categories;
- robot footprint and clearance parameters;
- inspection coverage radius or per-area waypoint budget.

It must not use fixture groups, receptacle lists, object inventory, Digital
Twin object semantics, private cleanup target truth, relocation truth, or
generated mess truth.

Each waypoint must have:

- stable `waypoint_id`;
- source-frame pose;
- bound `area_id`;
- purpose such as `area_inspection`;
- deterministic sweep or coverage order metadata.

Base waypoints answer "where should the robot inspect this area?" They do not
encode where a specific object or fixture is.

The intended default algorithm is deliberately small, not a full SLAM
exploration stack:

```text
for each navigation area:
  find safe free cells after robot-footprint clearance
  choose a primary max-clearance inspection pose
  add sparse extra poses only when area size exceeds the coverage budget
  validate collision/reachability against the same occupancy map
  fail artifact preparation if the area has no legal inspection pose
```

Externally-authored waypoints from Agibot navigation memory or operator tools
may be used as preparation evidence during migration, but the product artifact
should expose the same canonical waypoint schema and validation result. Runtime
should not branch on whether a waypoint originally came from sim, Agibot, or
Digital Twin.

Builder defaults for the first implementation:

- one primary waypoint per navigation area, with extra waypoints added only
  when a uniform area-size threshold proves necessary in tests;
- clearance threshold and footprint inflation come from the map bundle robot /
  costmap profile when available, otherwise the current B1 clearance default;
- yaw is `0.0` for the first pass;
- product launch requires validation against occupancy/free-space and known
  area binding;
- hand-authored or navigation-memory waypoints are allowed only as preparation
  seeds unless they are normalized into the same canonical waypoint schema and
  pass the same validation.

### Provenance

The artifact must declare:

- environment id;
- map source;
- area label source;
- generation or review timestamp/hash;
- validation result.

## Explicit Exclusions From Base Navigation Map V1

These may exist in private simulator state, Digital Twin assets, reports, or
future runtime evidence, but they should not be part of Base Navigation Map v1:

- static fixture table;
- receptacle list;
- movable object inventory;
- Digital Twin raw object semantics;
- scene partition raw data;
- private cleanup target truth;
- generated mess truth;
- relocation truth;
- hints such as "water is likely in this cabinet."

If one of these later proves necessary, it should be proposed as a uniform
Base Navigation Map v2 field or, preferably, as Runtime Metric Map evidence
created through observation.

## Implementation Flow

Execute the remaining work as one flow in the order below. Checkpoints may be
committed separately if useful for review, but the implementation assignment is
to continue through all remaining checkpoints and the verification ladder before
stopping.

### Checkpoint 1: Base Navigation Map V1 Validator

Create a strict validator or extend the existing bundle validation layer so a
product Base Navigation Map must prove:

- source-frame spatial metadata is present and valid;
- navigation areas are non-empty;
- every product navigation area has a stable id, polygon, semantic label,
  semantic category, geometry source, label source, and accepted validation
  status;
- base `inspection_waypoints` are non-empty and each waypoint binds to a known
  navigation area;
- base waypoint rows do not carry fixture/object/receptacle/private-truth
  fields;
- `unknown_review_required` categories fail product validation;
- Digital Twin proof sidecars are allowed only as sidecar capability metadata,
  not as map-generation inputs.

Acceptance:

- B1 / Map 12 generated Base Navigation Map passes this validator.
- At least one current MolmoSpaces generated bundle fails only for known gaps
  that the remaining flow will fix, not because validation is ambiguous.
- Missing navigation areas, unlabeled areas, empty waypoints, malformed waypoint
  area bindings, and forbidden fixture/object fields have targeted negative
  tests.

Status: Implemented.

Evidence:

- `validate_base_navigation_map_v1_bundle()` is exposed beside the existing
  generic Nav2 bundle validator.
- B1 base-map generation and B1 Digital Twin sidecar generation call the strict
  validator before publishing manifests.
- Current MolmoSpaces bundles intentionally fail the strict validator for known
  gaps that the remaining flow will address; the generic Nav2 bundle validator
  still covers current runtime compatibility.

### Checkpoint 2: Canonical Area-Based BaseWaypointBuilder

Extract a shared builder and validator for sparse area inspection waypoints.
The first implementation should stay intentionally small:

```text
for each navigation area:
  rasterize / sample safe free cells inside the area
  filter by robot footprint clearance
  choose the max-clearance pose nearest the area centroid
  add deterministic extra poses only when area area exceeds a uniform budget
  assign stable <area_id>_inspection[_N] ids
  validate every pose against occupancy and area binding
```

Initial parameters:

- robot clearance radius: use the existing map bundle robot/costmap profile
  where available; otherwise use the current B1 value as the default;
- max waypoint count per area: one primary waypoint for the first pass, with a
  uniform area-size threshold for extras only if existing scenes require it;
- yaw policy: `0.0` until there is a uniform, tested reason to face centroid or
  sweep direction;
- id policy: stable area-based ids, preserving existing accepted B1 ids when
  they already satisfy the schema.

Acceptance:

- B1 builder keeps producing the existing accepted Map 12 waypoints or an
  explicitly reviewed equivalent.
- A synthetic irregular-area test proves unreachable or fully occupied areas
  fail loudly.
- Tests prove builder inputs do not include fixtures, objects, receptacles,
  generated mess truth, relocation truth, or Digital Twin object semantics.

Status: Implemented.

Evidence:

- `roboclaws/maps/base_waypoints.py` owns the shared area-based waypoint
  builder, canonical purpose/source/policy constants, forbidden input checks,
  and `validate_base_waypoints()`.
- `scripts/maps/build_b1_map12_base_navigation_map.py` now delegates B1 / Map
  12 waypoint generation to the shared builder instead of carrying a local
  centroid/clearance sampler.
- `tests/contract/maps/test_base_waypoint_builder.py` covers B1 waypoint
  preservation, deterministic area-only waypoint generation, irregular-area
  selection, fully occupied-area failure, bad area bindings, occupied waypoint
  validation, and fixture/object/receptacle/private-truth input rejection.

### Checkpoint 3: MolmoSpaces Source-Map Builder Split

Split simulator bundle preparation away from `RealWorldCleanupContract` and
Agent View projection. The simulator preparation flow may still instantiate the
backend/session needed to read scene geometry, but it must write the source map
from preparation-time evidence, not from runtime public projections.

Target flow:

```text
MolmoSpaces scene/session evidence
  -> simulator Base Navigation Map preparation
  -> shared BaseWaypointBuilder
  -> strict Base Navigation Map v1 validation
  -> checked-in/prebuilt Nav2 bundle
```

Must not call from product bundle generation:

- `agent_view_payload()`;
- `static_fixture_projection()`;
- `source_map_static_fixture_projection()`;
- runtime observation paths;
- Agent View projection helpers.

Acceptance:

- `scripts/maps/generate_molmospaces_scene_bundles.py` or its replacement uses
  the simulator preparation path, not `RealWorldCleanupContract`, for product
  source maps.
- Current active MolmoSpaces scenarios regenerate and validate.
- Existing product runtime still consumes selected bundles and does not know
  whether the bundle came from MolmoSpaces, Agibot, or B1.

Status: Implemented.

Evidence:

- `roboclaws/maps/molmospaces_preparation.py` prepares MolmoSpaces
  fixture-free Base Navigation Map payloads from simulator source evidence and
  the shared `BaseWaypointBuilder`.
- `scripts/maps/generate_molmospaces_scene_bundles.py` uses the simulator
  preparation path instead of `RealWorldCleanupContract`, `agent_view_payload()`,
  or fixture projections.
- `assets/maps/molmospaces/procthor-10k-val/0` was regenerated as a strict
  Base Navigation Map v1 bundle with 7 rooms, 7 base inspection waypoints, and
  0 static landmarks.
- `tests/contract/maps/test_generate_molmospaces_scene_bundles.py` covers the
  split and validates the regenerated fixture-free contract.

### Checkpoint 4: Remove Agent View Snapshot Fallback

Remove the product branch that writes Nav2 bundle snapshots from
`run_result["agent_view"]` when no `source_bundle_dir` is supplied.

Target behavior:

- product and checker paths copy the selected source bundle into run artifacts;
- missing selected source bundle is a fail-loud error with a generation command
  hint;
- explicit synthetic tests use a named test helper or fixture bundle instead
  of the product snapshot attachment function.

Acceptance:

- Contract tests prove `attach_nav2_map_bundle_snapshot()` refuses to author a
  product source bundle from Agent View.
- Current product reports still contain source-bundle snapshots when a source
  bundle was selected.
- Tests that genuinely need synthetic map projection name that test-only
  contract explicitly.

Status: Implemented.

Evidence:

- `roboclaws/household/nav2_map_bundle.py` requires `source_bundle_dir` in
  `attach_nav2_map_bundle_snapshot()` and copies a selected bundle instead of
  authoring one from Agent View.
- `selected_nav2_map_bundle_dir()` validates strict Base Navigation Map v1
  bundles.
- Contract tests cover selected-bundle snapshots and missing-source refusal.

### Checkpoint 5: Runtime Contract Cleanup

After the artifact builders and validators are strict, clean runtime contracts
so product code has one question:

```text
Did the selected Base Navigation Map v1 artifact validate?
```

Scope:

- remove product-adjacent `allow_synthetic_map_projection` usage;
- keep synthetic projection only in explicit test helpers, if still needed;
- ensure runtime base waypoints are direct projections of artifact rows;
- keep runtime target-inspection candidates separate from base waypoints;
- keep fixture/object/receptacle semantics out of Base Navigation Map v1 and
  out of default Agent View.

Acceptance:

- Product launch paths fail before readiness if the selected artifact is
  missing or invalid.
- Agent View privacy tests still prove private truth and authored fixture tables
  are hidden.
- Cleanup still observes at least one object in the deterministic direct-runner
  MolmoSpaces route.

Status: Implemented.

Evidence:

- Product runtime rejects missing map bundles unless explicit synthetic test
  projection is requested.
- Runtime public base waypoints are direct projections of artifact rows;
  target-inspection waypoints remain generated runtime candidates.
- Fixture/object/receptacle semantics are excluded from Base Navigation Map v1
  and default Agent View; runtime internal fixture overlays are reconstructed
  from backend scenario evidence only for current-run observation/manipulation.
- Product checker coverage accepts canonical area-inspection waypoint ids and
  validates they remain fixture/object/private-truth free.

## Non-Goals

- Do not redesign SLAM or Nav2 itself.
- Do not add a new public map type.
- Do not make Agent View expose authored fixture tables.
- Do not move private scoring truth, relocation truth, or generated mess truth
  into source map artifacts.
- Do not add environment-specific optional Base Navigation Map fields.
- Do not use richer Digital Twin object, fixture, or scene semantics in product
  runtime just because they are available.
- Do not require live hardware, paid provider calls, or GPU validation for the
  first planning pass.
- Do not change Digital Twin scene alignment policy in this plan except to use
  it as offline evidence for required area labels and source-frame review.

## Parked Or Follow-Up Decisions

These are not blockers for the first implementation pass:

- Whether MolmoSpaces can eventually use a lower-level scene metadata API
  instead of a backend/session. The first pass may use the backend/session as
  long as it avoids runtime contract and Agent View projections.
- Whether all synthetic map projection tests should move to tiny checked-in
  bundles. The first pass may preserve named synthetic test helpers while
  removing product fallback behavior.
- Whether existing MolmoSpaces waypoint ids should be renamed for aesthetics.
  Artifact stability and one source of truth are more important than pretty ids.
- Whether Agibot navigation memory should become a long-term preparation seed.
  It may remain migration evidence, but product runtime must consume only
  canonical validated waypoint rows.
- Whether future B1 object/receptacle semantics deserve a uniform map v2 field.
  This plan keeps them out of Base Navigation Map v1.

These are human-review checkpoints, but implementation can start with current
defaults:

- Review normalized `semantic_category` vocabulary after the first simulator
  regeneration shows real labels.
- Review any B1 / Map 12 room label changes against the accepted
  `assets/maps/b1-map12-base-navigation-labels.json` source.
- Review any generated sim waypoint coverage that looks too sparse in report
  previews before broad scene regeneration.

## Acceptance Criteria

- MolmoSpaces bundle generation does not call Agent View projection methods.
- Product runtime copies a selected source bundle into run artifacts rather
  than regenerating it from Agent View.
- Missing product source bundle is an error, not a fallback.
- Generated MolmoSpaces active scene bundles validate and contain required
  navigation-area semantic labels and non-empty base inspection waypoints.
- Real robot and Digital Twin product bundles validate against the same
  Base Navigation Map v1 required fields.
- Sim, real robot, and Digital Twin base inspection waypoints conform to one
  canonical area-based, fixture-free schema and validation contract.
- Base waypoint generation or normalization does not use fixture groups,
  receptacles, object inventory, Digital Twin object semantics, private scoring
  truth, relocation truth, or generated mess truth.
- Base Navigation Map v1 does not expose static fixture tables, receptacle
  lists, object inventories, relocation truth, or private scoring truth.
- Cleanup with a generated sim bundle observes at least one object in the
  existing deterministic regression route.
- Agent View privacy tests still prove authored fixture tables and private
  scoring truth are hidden.
- Real robot and Digital Twin map consumers still pass existing contract tests.

Status: Passed.

Acceptance evidence:

- MolmoSpaces bundle generation no longer calls Agent View projection methods
  for product source maps.
- The successful product run copied
  `assets/maps/molmospaces/procthor-10k-val/0` into
  `output/household/household-world/cleanup/direct-world-public-labels/0621_1719/seed-7/map_bundle`.
- `nav2_map_bundle.snapshot_complete` is `true` and
  `nav2_map_bundle.source_bundle_root` is
  `assets/maps/molmospaces/procthor-10k-val/0`.
- The copied `semantics.json` contains 7 rooms, 7 canonical base inspection
  waypoints, and 0 `static_landmarks`.
- Runtime observed object count is 5 and runtime static-map fixture count is 0.
- Focused contract tests cover Agent View privacy, fixture-free waypoint
  validation, B1/Digital Twin map consumers, and selected-bundle product
  snapshots.

## Verification Ladder

Focused checks:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/maps/test_generate_molmospaces_scene_bundles.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/maps/test_runtime_map_prior_snapshot.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py

ruff check \
  roboclaws/household \
  roboclaws/maps \
  scripts/maps \
  tests/contract/maps
```

Product proof:

```bash
just run::surface \
  surface=household-world \
  world=molmospaces/procthor-10k-val/0 \
  backend=mujoco \
  preset=cleanup \
  agent_engine=direct-runner \
  evidence_lane=world-public-labels \
  seed=7 \
  scenario_setup=relocate-cleanup-related-objects \
  relocation_count=5
```

Final evidence, 2026-06-21:

- Focused tests passed:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/maps/test_generate_molmospaces_scene_bundles.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/maps/test_runtime_map_prior_snapshot.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py
```

- Lint passed:

```bash
ruff check \
  roboclaws/household \
  roboclaws/maps \
  scripts/maps \
  scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  scripts/molmo_cleanup/realworld_base_navigation_map_checker.py \
  tests/contract/maps \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

- Product proof passed:

```bash
just run::surface \
  surface=household-world \
  world=molmospaces/procthor-10k-val/0 \
  backend=mujoco \
  preset=cleanup \
  agent_engine=direct-runner \
  evidence_lane=world-public-labels \
  seed=7 \
  scenario_setup=relocate-cleanup-related-objects \
  relocation_count=5
```

Product run artifact:
`output/household/household-world/cleanup/direct-world-public-labels/0621_1719/seed-7/run_result.json`.

## Open Risks

- A lower-level MolmoSpaces source-map builder may still need scenario fixture
  data from the backend session. The simplification should remove Agent View
  coupling, not pretend the simulator has no source data.
- Removing fixture semantics from Base Navigation Map v1 may require cleanup to
  rely more strictly on runtime observation for receptacle/surface discovery.
  That is desirable for source-of-truth cleanliness, but it may expose current
  places where cleanup still assumes preloaded static landmarks.
- A simple area-based waypoint builder may not initially match hand-authored or
  navigation-memory waypoint quality. The first implementation should prefer a
  conservative, deterministic sampler with strict validation over a complex
  SLAM/exploration dependency.
- Large or irregular areas may need more than one sparse inspection pose. The
  coverage budget should be a uniform Base Navigation Map parameter, not an
  environment-specific optional behavior.
- Removing the Agent View snapshot fallback may expose tests or report paths
  that relied on synthetic map generation. Those should move to explicit test
  fixtures or direct test helpers.
- Renaming existing waypoint ids could churn checked-in map bundles and reports;
  stable semantics may matter more than pretty ids.
- Digital Twin has legitimate extra sources. The simplification should not
  flatten raw scene/object evidence into the same category as Base Navigation
  Map fields.

## Next Implementation

No additional design discussion is required before continuing implementation.
Do not run the remaining work as separate slices. The intended execution shape
is one flow that completes Checkpoints 3-5, then runs the verification ladder
and updates this plan status again.

Recommended next implementation command:

```text
Continue docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md
as one implementation flow: split MolmoSpaces source-map preparation away from
Agent View/runtime projection, remove product Agent View snapshot fallback,
clean runtime consumption around validated Base Navigation Map artifacts, and
run the full verification ladder before stopping.
```

Stop before implementation if any change would:

- preserve product fallback map generation from Agent View;
- add environment-specific optional Base Navigation Map fields;
- expose fixture/object/receptacle/private truth in Base Navigation Map v1;
- make Digital Twin runtime consume richer map fields than real robot runtime;
- require changing cleanup target-inspection candidate semantics.

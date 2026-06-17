---
plan_scope: cross-environment-semantic-map-parity
status: Implemented
created: 2026-06-15
last_reviewed: 2026-06-15
implementation_allowed: true
source:
  - user request to make real robot, digital twin, and simulator map overlays more consistent
  - intuitive-reduce-entropy selection scan on Map 12 overlay mismatch
related_context:
  - ARCHITECTURE.md
  - docs/human/domain.md
  - docs/human/technical-design.md
  - docs/plans/refactor-actionable-semantic-map-snapshot.md
  - docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md
  - skills/actionable-semantic-map-conversion/SKILL.md
  - skills/scene-gaussian-map-alignment/SKILL.md
---

# Cross-Environment Semantic Map Parity

## Status

Status: Implemented
Last reviewed: 2026-06-15
Current decision: Use an additive first slice that keeps `rooms` readable while
requiring polygon role, geometry source, source-frame metadata, explicit
`display_frame` absence, and alignment status. All semantic geometry is
source-frame-first; rectified UI views are parked for a later display-only
slice. The first UI slice shows the raw/source map view and rotates semantic
overlays into that same frame. The first slice is implemented in the map
artifact layer, report rendering, static map bundles, and contract tests.
Next step: Pick a later display-only rectification or true room-boundary tracing
slice only after a new plan; no implementation blocker remains for the first
slice.
Supersession note: the B1 / Map 12 room-semantics merged bundle referenced by
this implemented parity slice is superseded for current B1 digital-twin product
work by `docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`.
Current B1 work should use raw Map12 plus the thin review/runtime contract, not
`assets/maps/b1-map12-room-semantics` as a canonical source.
Open questions: None before execution. The exact serialized field locations and
test fixture edits are implementation details inside the approved contract.
Parked: Full B1 object/receptacle USD segmentation and manipulation parity.

## Goal

Make semantic maps and overlays honest and comparable across:

- real Agibot G2 / Agibot GDK Map 12 runs;
- B1 / Map 12 digital-twin runs;
- simulator household runs such as MolmoSpaces/MuJoCo and Isaac Lab.

The target is not that every environment has identical geometry today. The
target is that every environment exposes the same map contract:

```text
source map frame as the only spatial truth
  -> public navigation areas
  -> public semantic anchors
  -> optional room semantics
  -> explicit alignment tier
  -> Actionable Semantic Map Snapshot / Runtime Metric Map consumers
```

When a report shows an overlay, the human reviewer should be able to tell
whether the geometry is a traced room boundary, a navigation-zone bounding box,
a scene-engine partition, or a runtime observation. The first UI slice renders
the raw/source map view only: if the real robot map is tilted, the semantic
overlay tilts with it. A rectified human display can be added later only as a
derived view of the same source-frame geometry.

## Why Now

The Map 12 report exposed a concrete mismatch:

- the occupancy base image comes from the raw Agibot GDK / SLAM map frame;
- the current `rooms` polygons for Map 12 are hand-authored axis-aligned
  rectangles;
- the B1 / Map 12 room semantic bundle applies scene-engine partition labels
  to Map 12 navigation-area polygons without verified scene-to-map room
  geometry;
- report previews draw those polygons directly over the raw occupancy map.

This creates false confidence. A preview can look like a semantic room overlay
even when the geometry is only a candidate navigation area or a display aid.

## Current Evidence

The raw Agibot map bundle preview projects map-frame points directly onto the
occupancy image:

- `roboclaws/household/agibot_map_bundle.py::_write_agibot_preview`
- `roboclaws/household/report.py::_write_nav2_occupancy_navigation_preview`
- `roboclaws/maps/rasterize.py::world_to_grid`

The B1 / Map 12 room semantic overlay currently attaches scene partitions to
navigation areas by list order:

- `roboclaws/maps/room_semantics.py::_attach_navigation_areas`

The B1 / Map 12 plan already states that coarse B1 geometry and Map 12 overlay
are candidate evidence unless anchor residuals or runtime proof promote them:

- `docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md`

The Actionable Semantic Map Snapshot plan already converged online
semantic-map-build and offline Agibot navigation-memory conversion into one
consumer shape, but it does not yet make display frame, polygon geometry source,
or scene-to-map alignment tier first-class fields.

## Target Vocabulary

Use these terms consistently before implementation:

- `source_map_frame`: the robot or simulator metric map frame used by tools.
- `display_frame`: a rendered coordinate frame for report images. It may be
  rectified for user readability in a later slice, but it is not part of the
  first UI path. If added later, it must be labeled, traceable to
  `source_map_frame`, and must not silently replace navigation coordinates or
  keep a separate semantic overlay that only fits the rectified image.
- `navigation_area`: a public navigable zone or inspection area. It may be a
  rectangle and is not necessarily a room boundary.
- `room_boundary`: a traced or derived room polygon intended to match physical
  walls or room partitions.
- `scene_partition`: a digital-twin asset partition such as a B1 USD/Gaussian
  room folder.
- `semantic_anchor`: an object, fixture, landmark, surface, receptacle, or room
  semantic entry that can carry affordances and evidence.
- `geometry_source`: how a polygon was obtained, for example
  `operator_authored_navigation_zone`, `traced_occupancy_room_boundary`,
  `scene_engine_partition`, `runtime_observation`, or `generated_candidate`.
- `alignment_status`: `native`, `candidate`, `verified`, `runtime_proven`,
  `planner_backed`, or `blocked`.

## Selected Candidates

### Candidate 1: Single Spatial Map Contract

Severity: P0
Entropy source: architecture contract
Materiality: false confidence
Impact radius: repo-wide map artifacts and reports

Add a spatial contract shared by Runtime Metric Map, Actionable Semantic Map
Snapshot, Nav2 map bundles, and scene-room overlays. The contract must declare:

- source map frame as the only spatial truth for semantic geometry;
- no first-slice display rectification; UI previews render raw/source map
  orientation;
- polygon role;
- polygon geometry source;
- alignment status;
- whether the polygon is safe for navigation, semantic labeling, or only review.

Maintainer test:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps -k "semantic_map or room_semantic or actionable" -q
```

### Candidate 2: Stop Presenting Navigation Zones As Room Boundaries

Severity: P0
Entropy source: artifact contract
Materiality: false confidence
Impact radius: Map 12 artifacts, reports, and downstream agent context

Map 12 `rooms` should either become true `room_boundary` geometry or be
renamed/classified as `navigation_area`. Until real room boundaries are traced,
reports must label the overlay as navigation zones. The first slice keeps
existing `rooms` containers readable for compatibility, but requires metadata
that prevents a navigation zone from being presented as a room boundary.

Maintainer test:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_agibot_map_bundle_export.py tests/contract/maps/test_scene_room_semantic_overlay.py -q
```

### Candidate 3: Replace Order-Based B1 Partition Binding

Severity: P1
Entropy source: workflow drift
Materiality: recurring rediscovery
Impact radius: B1 / Map 12 digital-twin map bundle

Replace implicit list-order binding in `_attach_navigation_areas` with an
explicit `scene_map_correspondence_v1` manifest:

```json
{
  "asset_partition_id": "meeting_room_b",
  "navigation_area_id": "central_floor",
  "alignment_status": "candidate",
  "transform_source": "operator_review",
  "evidence_artifacts": ["robot_view_0003"],
  "map_polygon": null
}
```

No scene partition should be treated as map-frame geometry unless the manifest
provides a polygon or verified transform evidence.

Maintainer test:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_scene_room_semantic_overlay.py -q
```

### Candidate 4: Cross-Environment Parity Gate

Severity: P1
Entropy source: tests and eval gap
Materiality: false confidence
Impact radius: validation and eval harness

Add a parity gate that compares one real-robot map bundle, one digital-twin map
bundle, and one simulator map bundle for the same required contract fields.
This gate should not require live hardware. It should fail if a source omits
geometry source, polygon role, or alignment status.

Maintainer test:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_cross_environment_semantic_map_parity.py -q
```

## Non-Goals

- Do not mutate Agibot source map folders.
- Do not claim B1 USD object/receptacle truth without segmentation or a
  manifest.
- Do not add display rectification in the first implementation slice.
- Do not maintain one semantic overlay for raw robot maps and another semantic
  overlay for rectified display maps. One source-frame overlay may be rendered
  through multiple views.
- Do not require real Agibot GDK, Isaac runtime, or live Codex for the first
  contract slice.
- Do not add a new public surface or MCP tool until the artifact contract is
  stable.

## Acceptance Criteria

- Every map overlay artifact declares polygon role and geometry source.
- Report previews distinguish `navigation_area` from `room_boundary`.
- B1 scene partition labels are attached through an explicit manifest, not
  implicit list order.
- UI previews use raw/source map orientation for real robot, digital twin, and
  simulator bundles.
- Semantic polygons render in the same raw/source map frame as the base image;
  on a tilted robot map, the semantic overlay is tilted too.
- Reports label the view as source-frame/raw-map aligned, so users understand
  that non-horizontal/non-vertical geometry reflects the robot map frame rather
  than an overlay mismatch.
- Actionable Semantic Map Snapshot and Runtime Metric Map consumers can read
  the same public semantic anchors without Agibot-only or B1-only branches.
- Tests fail when a candidate or unverified overlay is presented as verified
  room geometry.

## Suggested Sequence

1. Add the minimum contract fields and tests to current artifacts.
2. Keep `rooms` additive-compatible while requiring `polygon_role` and
   `geometry_source` on existing entries.
3. Relabel existing Map 12 rectangles as `navigation_area` unless traced
   occupancy room boundaries are provided.
4. Add explicit B1 partition-to-navigation-area correspondence data.
5. Update report previews to show geometry role and alignment tier.
6. Add the cross-environment parity gate.

## Reduce Entropy Loop 1

Selected mode: plan entropy mode
Why: The plan is a draft execution direction and needs one pass for weak
assumptions, missing decisions, and proof gaps.
Discovery intensity: selection scan

### Finding 1: Vocabulary Must Decide The Contract Boundary First

Severity: P0
Materiality: false confidence
Owner: `$grill-with-docs-batch`

The plan depends on a distinction between `navigation_area`, `room_boundary`,
and `scene_partition`. If that distinction is not accepted before code changes,
implementation can rename fields without preventing the same visual false
confidence. This should be grilled before preflight.

Decision needed:

```text
Can existing Map 12 rectangles remain under a field named rooms if each item
has polygon_role=navigation_area, or must they move to a new navigation_areas
collection?
```

### Finding 2: Existing Consumers May Expect `rooms`

Severity: P1
Materiality: live source drift
Owner: `$intuitive-preflight`

The safer first implementation may be additive: keep `rooms` readable for
compatibility, but require `polygon_role` and `geometry_source` on each room
or navigation area. A disruptive rename to `navigation_areas` should be planned
only after callers and reports are audited.

Suggested proof:

```bash
rg -n "\"rooms\"|room_category_hints|inspection_waypoints|navigation_area" roboclaws tests skills docs
```

Observed proof on 2026-06-15: `rooms` is consumed across map projection,
bundle validation, Runtime Metric Map payloads, report rendering, Agibot map
build, scene room overlays, and multiple contract tests. This confirms the
first implementation should be additive. Do not remove or rename `rooms` in the
first slice; require clearer metadata on the existing entries first.

### Finding 3: B1 Correspondence Manifest Needs A Minimal Schema

Severity: P1
Materiality: recurring rediscovery
Owner: `scene-gaussian-map-alignment`

The plan names a manifest but does not yet define required fields, artifact
location, or whether overrides can inline correspondence. Without this, the
next implementation may preserve the implicit binding in a different shape.

Minimum schema to grill:

```text
scene_map_correspondence_v1:
  asset_partition_id
  navigation_area_id
  alignment_status
  transform_source
  evidence_artifacts
  map_polygon | omitted
```

### Finding 4: Parity Gate Should Start With Static Artifacts

Severity: P2
Materiality: real workflow friction
Owner: `$intuitive-tests`

The original cross-environment gate compared checked-in static bundles:

- `assets/maps/agibot-robot-map-12`
- `assets/maps/b1-map12-room-semantics` (historical B1 merged bundle;
  superseded for current product work)
- `assets/maps/molmospaces-procthor-val-0-7`

Live Agibot, Isaac, and simulator runs can become later eval rows. Starting
with static artifacts keeps the first contract slice deterministic.

Observed proof on 2026-06-15: all three static bundle directories exist in this
checkout. They are sufficient for the first parity gate without live hardware or
GPU runtime.

### Selected Candidates After Loop 1

- Candidate 1 remains P0 and should lead.
- Candidate 2 remains P0 but should likely be additive first, not a hard rename.
- Candidate 3 remains P1 and needs a manifest schema decision before code.
- Candidate 4 remains P1/P2 depending on whether it is limited to static bundles.

### Parked Items

- Automatically estimating a rectification/display yaw from occupancy walls.
- Rectified human display view for prettier map inspection.
- Tracing true Map 12 room boundaries from occupancy in this slice.
- B1 object/receptacle segmentation.
- Planner-backed parity across real robot, digital twin, and simulator.

## Grill Batch 1

Skill: `$grill-with-docs-batch`
Date: 2026-06-15
Result: Accepted with one display-frame nuance.

Resolved decisions:

- Existing `rooms` remain readable in the first implementation slice, but
  entries must declare `polygon_role` and `geometry_source`; no hard rename to
  `navigation_areas` before consumer audit.
- `navigation_area` means a navigable or inspectable zone that may be
  rectangular and not wall-aligned. `room_boundary` is reserved for geometry
  intended to match physical walls or room partitions.
- B1 / Map 12 scene partitions must bind through
  `scene_map_correspondence_v1`; implicit list-order scene partition to map
  polygon binding is forbidden.
- `source_map_frame` is the only spatial truth. Semantic boxes, polygons,
  anchors, and correspondence evidence must be expressed there first. The first
  UI slice renders that raw/source frame directly; `display_frame`
  rectification is parked for a later display-only slice.
- ADR is deferred until the exact public artifact fields and compatibility
  story are selected during preflight / first implementation.

Documentation update:

- `CONTEXT.md` now defines Source Map Frame, Display Frame, Navigation Area,
  Room Boundary, Scene Partition, Polygon Geometry Source, and Alignment
  Status.

## Reduce Entropy Loop 2

Selected mode: plan entropy mode
Why: The plan still allowed two first-slice UI interpretations: raw/source view
or rectified human view.
Discovery intensity: quick scan

Selected candidate: choose raw/source map view as the only first-slice UI path.

Decision:

- First-slice UI previews render the raw/source map orientation for real robot,
  digital twin, and simulator bundles.
- Semantic overlays must be transformed into the same source map frame as the
  base image, so a tilted robot map gets tilted semantic polygons.
- Rectified/prettier human map display is parked for a later display-only slice
  after the source-frame contract and parity gate are stable.

Rationale:

- This removes the highest-risk implementation fork.
- It keeps UI, artifact contract, navigation coordinates, and tests on one
  spatial truth.
- It prevents a visually pleasing but separate display overlay from masking a
  source-frame mismatch.

## Grill Batch 2

Skill: `$grill-with-docs-batch`
Date: 2026-06-15
Result: Saturated; no decision-impact batch needed.

Audit result:

- The plan already chooses the first-slice UI path: raw/source map view only.
- `CONTEXT.md` already defines the durable vocabulary needed for implementation.
- Remaining choices are implementation-contract details for preflight: exact
  field locations, static fixture edits, and test assertions.

Patch applied:

- Tightened the status wording from display/source-frame metadata to
  source-frame metadata plus explicit `display_frame` absence, so preflight does
  not reinterpret the first slice as rectified-display work.

## Preflight Contract

Preflight status: DRAFT
Task source: user request plus grilled plan
Canonical source: `docs/plans/2026-06-15-cross-environment-semantic-map-parity.md`
Route: durable `$intuitive-flow`
Goal: Implement the first-slice cross-environment semantic-map parity contract so
real Agibot Map 12, B1 / Map 12 digital twin, and simulator map previews all use
raw/source map orientation with semantic overlays in the same source map frame.

Scope:

- Add a reusable map spatial contract for bundle/runtime-map artifacts:
  `source_map_frame` is the only spatial truth, first-slice `display_frame` is
  explicitly absent, and entries declare `alignment_status`.
- Keep existing `rooms` containers readable, but require each map polygon entry
  to declare `polygon_role` and `geometry_source`.
- Classify current Map 12 rectangle polygons as `navigation_area`, not
  `room_boundary`, unless true room-boundary geometry is later provided.
- Replace implicit B1 scene-partition to Map 12 polygon list-order binding with
  explicit `scene_map_correspondence_v1` data containing
  `asset_partition_id`, `navigation_area_id`, `alignment_status`,
  `transform_source`, `evidence_artifacts`, and optional `map_polygon`.
- Update static bundles and generators for
  `assets/maps/agibot-robot-map-12`,
  `assets/maps/b1-map12-room-semantics` (historical implementation artifact), and
  `assets/maps/molmospaces-procthor-val-0-7`.
- Update report / preview rendering so UI previews are labeled
  raw/source-map aligned and semantic polygons tilt with the base map when the
  source map is tilted.

Non-goals:

- No rectified / prettier human display in the first implementation slice.
- No second semantic overlay that only fits a rectified image.
- No hard rename from `rooms` to `navigation_areas`.
- No tracing of true Map 12 room boundaries from occupancy data.
- No live Agibot GDK, Isaac Lab, real robot, provider, Docker, or Codex CLI
  requirement for the first contract slice.
- No new public surface, preset, MCP tool, or command grammar.

Context:

- must-read:
  `CONTEXT.md`,
  `ARCHITECTURE.md`,
  `docs/human/domain.md`,
  `docs/human/technical-design.md`,
  this plan,
  `docs/plans/refactor-actionable-semantic-map-snapshot.md`,
  `docs/plans/refactor-reduce-entropy-b1-map12-digital-twin.md`,
  `roboclaws/maps/bundle_validation.py`,
  `roboclaws/maps/project.py`,
  `roboclaws/maps/rasterize.py`,
  `roboclaws/maps/room_semantics.py`,
  `roboclaws/maps/actionable_snapshot.py`,
  `roboclaws/household/agibot_map_bundle.py`,
  `roboclaws/household/report.py`,
  `scripts/operator_console/semantic_map_preview.py`,
  `tests/contract/maps/`.
- useful:
  `assets/maps/agibot-robot-map-12/semantics.json`,
  `assets/maps/b1-map12-room-semantics/semantics.json` for historical
  implementation evidence only,
  `assets/maps/b1-map12-room-semantics/room_semantic_overlay.json` for
  historical implementation evidence only,
  `assets/maps/molmospaces-procthor-val-0-7/semantics.json`,
  `scripts/maps/check_bundle.py`,
  `scripts/maps/export_agibot_map_bundle.py`,
  `skills/actionable-semantic-map-conversion/scripts/render_room_semantic_topdown.py`.
- avoid-unless-needed:
  `output/`, `logs/`, `.planning/`, historical retrospectives, live provider
  traces, Agibot SDK internals, and Isaac Lab runtime assets.

Acceptance:

- SUCCESS: all three static map bundles expose required source-frame spatial
  contract metadata; every overlay polygon has `polygon_role`,
  `geometry_source`, and `alignment_status`; B1 correspondence uses
  `scene_map_correspondence_v1` instead of list order; report previews render
  raw/source orientation and label that choice; semantic overlays share the
  base-image source frame; focused contract tests and bundle checks pass.
- BLOCKED_NEEDS_DECISION: none.
- BLOCKED_NEEDS_LOCAL_VALIDATION: manual visual acceptance remains required if
  generated preview/report images cannot be inspected in the execution
  environment.
- INTERMEDIATE_ONLY: none unless explicitly approved.
- No regressions: existing Nav2 bundle validation, Actionable Semantic Map
  Snapshot conversion, Runtime Metric Map consumption, room semantic overlay
  generation, and simulator map-build product route still work.

Verification:

- deterministic:
  `ruff check roboclaws/maps roboclaws/household/agibot_map_bundle.py roboclaws/household/report.py scripts/maps scripts/operator_console tests/contract/maps`,
  `ruff format --check roboclaws/maps roboclaws/household/agibot_map_bundle.py roboclaws/household/report.py scripts/maps scripts/operator_console tests/contract/maps`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/contract/maps/test_agibot_map_bundle_export.py tests/contract/maps/test_scene_room_semantic_overlay.py tests/contract/maps/test_cross_environment_semantic_map_parity.py -q`.
- integration:
  `.venv/bin/python scripts/maps/check_bundle.py assets/maps/agibot-robot-map-12`,
  `.venv/bin/python scripts/maps/check_bundle.py assets/maps/b1-map12-room-semantics` (historical evidence for this implemented slice),
  `.venv/bin/python scripts/maps/check_bundle.py assets/maps/molmospaces-procthor-val-0-7`,
  `just agent::harness agent-validation recommend plan=docs/plans/2026-06-15-cross-environment-semantic-map-parity.md budget=focused`,
  `just agent::harness agent-validation execute plan=docs/plans/2026-06-15-cross-environment-semantic-map-parity.md budget=focused`.
- product-run:
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline`.
- local-live-manual:
  inspect the generated Agibot Map 12, B1 / Map 12, and simulator preview/report
  images and confirm they are labeled raw/source-map aligned and that semantic
  polygons are not drawn in a separate rectified display frame. No real robot,
  provider, GPU, Docker, or Isaac Lab proof is required for this first slice.
- optional:
  run the generated B1 `room_semantic_topdown.png` render after fixture updates
  to visually compare against prior artifact quality.

Execution:

- main: root session supervises plan fidelity, dirty-worktree safety, and final
  verification summary.
- worker: none required by preflight; `$intuitive-flow` may choose bounded
  workers if useful.
- worker-goal: none.

## Implementation Closeout

Status: Implemented on 2026-06-15.

Shipped contract:

- `roboclaws/maps/spatial_contract.py` defines `map_spatial_contract_v1`,
  source-frame-only display absence, polygon role, geometry source, alignment
  status, source-map frame id, and polygon usage validation.
- Static bundles for Agibot Map 12, B1 / Map 12 room semantics, and
  MolmoSpaces Procthor val 0 seed 7 declare `display_frame: null`, source-frame
  spatial contract metadata, and `navigation_area` polygons instead of
  room-boundary claims. `assets/maps/molmo-cleanup-default-7` was normalized
  because existing contract tests use it as a fixture.
  The B1 room-semantics bundle is historical evidence for this implemented
  parity slice and is superseded as a current product source by the thin
  review/runtime contract.
- B1 scene partition binding uses explicit `scene_map_correspondence_v1`
  records instead of implicit list order.
- Report and bundle previews render raw/source map orientation and label that
  no rectified display frame is substituted.
- Runtime Metric Map and Actionable Semantic Map Snapshot consumers read the
  same compatible room/navigation-area metadata without Agibot-only or B1-only
  consumer branches.

Verification evidence:

- `ruff check roboclaws/maps roboclaws/household/agibot_map_bundle.py roboclaws/household/report.py scripts/maps scripts/operator_console tests/contract/maps`
- `ruff format --check roboclaws/maps roboclaws/household/agibot_map_bundle.py roboclaws/household/report.py scripts/maps scripts/operator_console tests/contract/maps`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/contract/maps/test_agibot_map_bundle_export.py tests/contract/maps/test_scene_room_semantic_overlay.py tests/contract/maps/test_cross_environment_semantic_map_parity.py -q`
- `.venv/bin/python scripts/maps/check_bundle.py assets/maps/agibot-robot-map-12`
- `.venv/bin/python scripts/maps/check_bundle.py assets/maps/b1-map12-room-semantics` (historical evidence for this implemented slice)
- `.venv/bin/python scripts/maps/check_bundle.py assets/maps/molmospaces-procthor-val-0-7`
- `just agent::harness agent-validation execute changed_file=roboclaws/maps/spatial_contract.py changed_file=roboclaws/maps/bundle.py changed_file=roboclaws/maps/bundle_validation.py changed_file=roboclaws/maps/project.py changed_file=roboclaws/maps/room_semantics.py changed_file=roboclaws/maps/actionable_snapshot.py changed_file=roboclaws/household/agibot_map_bundle.py changed_file=roboclaws/household/report.py changed_file=tests/contract/maps/test_cross_environment_semantic_map_parity.py budget=focused output_dir=output/agent-validation-matrix/20260615T-map-parity-changed-files-execute`
  passed and produced
  `output/agent-validation-matrix/20260615T-map-parity-changed-files-execute/validation_matrix.html`.
- `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline`
  produced `output/household/semantic-map-build/direct-report/0615_1536/seed-7/report.html`.
- A broader plan-text validation-matrix run produced
  `output/agent-validation-matrix/20260615T075158Z/validation_matrix.html` and
  blocked only on the selected live Codex cleanup gate because this shell did
  not have `CODEX_BASE_URL` / `CODEX_API_KEY`. Live Codex proof is outside this
  first-slice acceptance contract.

Remaining parked follow-ups:

- Rectified / prettier display-frame rendering as a later display-only slice.
- True Map 12 room-boundary tracing from occupancy or other stronger evidence.
- B1 object/receptacle USD segmentation and manipulation parity.
- Live Agibot GDK, Isaac Lab, real robot, provider, Docker, or Codex CLI proof
  beyond the deterministic first-slice gates.

## Recommended Next Action

Pick a later parked slice only if product needs it. The first-slice parity
contract is implemented.

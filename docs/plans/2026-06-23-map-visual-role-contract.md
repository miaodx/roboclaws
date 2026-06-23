---
plan_scope: map-visual-role-contract
status: Implemented
created: 2026-06-23
last_reviewed: 2026-06-23
implementation_allowed: true
source:
  - User review of latest UI E2E screenshots where Base Navigation Map and Top-down
    previews visually drifted again.
  - User correction on 2026-06-23: do not implement yet; finish this plan first,
    then execute through intuitive-flow.
  - User-supplied visual target: current operator-console default map preview
    style, where the map is a semantic overlay on top-down world bounds.
related_context:
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/domain.md
  - docs/human/technical-design.md
  - docs/plans/2026-06-17-sim-map-surface-simplification.md
  - docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md
---

# Map Visual Role Contract

## Problem

Roboclaws has already separated the data contracts:

- Base Navigation Map is the start-of-run navigation context.
- Runtime Metric Map is current-run semantic evidence.
- Top-down scene views are camera/render evidence.
- Reports and operator-console images are review surfaces, not map contracts.

The UI can still surprise reviewers because the visual role is not carried end
to end. The latest reported failure is that the Top-down slot displayed a
map-like semantic projection instead of a scene render. Separately, active run
`map_bundle/preview.png` can look unlike the operator-console default preview
map, even though the default preview style is the desired visual language.

The result is a false-green failure mode: UI E2E can show image slots while the
human sees three different "semantic map" styles and has to infer which one is
the real contract.

## User Decision

Use the current operator-console default map preview style as the canonical map
visual language.

Reference characteristics:

- 900 x 560 review canvas.
- Light top-down world-bounds background.
- Navigation-area polygons/fills as translucent map overlay polygons. Call them
  room boundaries only when the geometry source and alignment prove that role.
- Small legend in the upper-left corner.
- Stable layer colors for navigation areas, waypoints, receptacles, objects,
  selected objects, robot path, and robot pose/heading.
- Existing local reference:
  `roboclaws/operator_console/static/previews/molmospaces-procthor-objaverse-val-0-map.png`.

Do not revive `semantic_map.png` as the artifact name. The desired style can be
reused without restoring the old artifact surface.

## Target Contract

The UI should have one map visualization system and three clear review roles:

```text
Base Navigation Map preview
  = the start-of-run base map rendered in the default preview overlay style.

Runtime Metric Map preview
  = the same base map visual, with current-run semantic and robot overlays added.

Top-down Scene View
  = a real top-down camera/render view of the scene, with at most robot pose
    and heading annotations. It is not a semantic map artifact.
```

The important unification is visual, not semantic:

- Base and Runtime previews share projection, canvas sizing, room rendering,
  color system, legend style, and map-frame caveats.
- Runtime preview is Base plus additional layers. It should not be a separate
  visual dialect.
- Top-down scene rendering stays visually distinct because it proves a different
  thing: scene/camera evidence rather than map evidence.

## Layer Policy

### Base Navigation Map Preview

Base preview may render only data that belongs to the Base Navigation Map
contract:

- validated Base Navigation Map v1 occupancy/free-space context;
- navigation-area polygons and muted labels;
- public inspection waypoints;
- source/provenance note and legend.

Base preview must not render runtime observed objects, selected/focus objects,
public semantic anchors promoted during the run, target candidates, robot path,
robot pose, static fixture/receptacle/landmark tables, private
relocation/scoring truth, or a full static movable-object inventory.

### Runtime Metric Map Preview

Runtime preview uses the exact same base renderer and adds current-run overlays:

- observed objects;
- selected/focus object state when available;
- public semantic anchors and target candidates that are present in
  `runtime_metric_map.json`;
- visited/unvisited waypoint status;
- robot path, current robot point, and heading arrow;
- optional manual-adjustment point styling if that evidence exists.

The UI label should be **Runtime Metric Map preview**.

The canonical image artifact should be `runtime_metric_map_preview.png`, written
beside `runtime_metric_map.json`.

### Top-down Scene View

Top-down must be a scene/camera artifact. For MolmoSpaces this means a MuJoCo
top-down camera render using the existing scene camera control path, not
`render_robot_map(...)` or another schematic map renderer.

Allowed annotations:

- current robot point;
- robot heading arrow;
- optionally a short path trail if it is projected into the rendered scene frame
  and explicitly labeled as an annotation.

Disallowed annotations:

- room semantic overlay as the primary image;
- receptacle/object semantic map dots as the primary image;
- `Runtime Metric Map preview` content routed through the Top-down slot.

## Current Evidence

- Operator-console default preview map already has the desired visual style:
  `roboclaws/operator_console/static/previews/molmospaces-procthor-objaverse-val-0-map.png`.
- Its metadata currently marks the view as `base_navigation_map_preview` in
  `roboclaws/operator_console/static/previews/molmospaces-procthor-objaverse-val-0-preview.json`.
- Current live run asset discovery in
  `roboclaws/operator_console/state.py::_latest_view_assets` has no dedicated
  Runtime Metric Map preview slot.
- Current MolmoSpaces robot view output writes `render_robot_map(...)` into
  `robot_views/*.topdown.png` in
  `scripts/molmo_cleanup/molmospaces_worker_outputs.py`, which is the direct
  cause of map-like content appearing as Top-down.
- Active run `map_bundle/preview.png` is produced through map bundle preview
  generation in `roboclaws/maps/bundle.py`; it can visually drift from the
  desired operator-console default preview style.
- `docs/plans/2026-06-17-sim-map-surface-simplification.md` intentionally
  removed `semantic_map.png` and made Runtime Metric Map review JSON/table-first.
  This plan deliberately updates that visual-review policy by adding
  `runtime_metric_map_preview.png`; it does not revive `semantic_map.png` or make
  preview images runtime source truth.

## Preflight Contract

Preflight status: IMPLEMENTED

Task source: user prompt plus current plan.

Canonical source: `docs/plans/2026-06-23-map-visual-role-contract.md`.

Route: durable `$intuitive-flow` after approval. Implementation should use a
bounded `$intuitive-refactor` slice because this is a known artifact/UI role
seam.

Goal: make Base Navigation Map preview and Runtime Metric Map preview share one
default-preview overlay visual language, while restoring Top-down to real scene
render evidence.

Scope:

- Promote or recreate the current operator-console default map preview renderer
  as the canonical map preview renderer for MolmoSpaces-style map overlays.
- Make `map_bundle/preview.png` use that canonical visual style for Base
  Navigation Map preview.
- Generate `runtime_metric_map_preview.png` beside `runtime_metric_map.json`
  with the same base visual plus runtime overlays.
- Generate or refresh that preview in both normal run finalization and live MCP
  public-artifact refresh paths.
- Add a dedicated operator-console slot/tab for `Runtime Metric Map preview`.
- Keep `Base Navigation Map preview` as its own slot/tab.
- Restore MolmoSpaces `robot_views/*.topdown.png` to a real top-down scene
  render with robot point/heading annotation.
- Thread explicit visual roles through operator-console payloads and UI DOM
  attributes so E2E tests can assert role/source, not just image presence.
- Update report copy and focused tests to match the three-role contract,
  including replacing JSON/table-only Runtime Metric Map visual language where
  the new preview is available.

Non-goals:

- Do not change Base Navigation Map, Runtime Metric Map, Agent View, or map
  bundle data semantics.
- Do not reintroduce `semantic_map.png`, `map_overlay.json`, or
  `map_bundle/report_static_navigation_map.png` as current proof surfaces.
- Do not add compatibility shims for old map preview names.
- Do not solve all B1 / Agibot map-scene alignment preview work in this slice.
- Do not run paid provider, hardware, or OpenClaw validation.

Entity budget:

- Reuse:
  - current operator-console default preview visual style;
  - `map_bundle/preview.png` as the Base Navigation Map preview artifact;
  - `runtime_metric_map.json` as Runtime Metric Map source truth;
  - existing top-down camera-control/render path used by scene previews;
  - `latest_view_assets` in `roboclaws/operator_console/state.py`;
  - preview metadata roles already used by
    `scripts/operator_console/render_scene_previews.py`.
- Remove/merge:
  - remove current-path treatment of map-like `robot_views/*.topdown.png` as a
    valid Top-down Scene View;
  - remove or reroute any current UI path that treats `semantic_map.png` as a
    live map proof.
- New:
  - `runtime_metric_map_preview.png`, because the user explicitly wants a
    Runtime Metric Map preview rather than JSON/table-only evidence;
  - a small shared renderer module under the map/artifact layer is allowed when
    the existing default preview renderer is not available as reusable code.
    This module must own preview rendering, not define a new map contract.
- Expansion triggers:
  - Stop and re-approve if implementation needs a schema version change for
    Base Navigation Map, Runtime Metric Map, Agent View, or map bundles.
  - Stop and re-approve if checked-in preview regeneration causes broad asset
    churn outside selected operator-console preview fixtures.
  - Stop and re-approve if Base preview would need to show static
    fixture/receptacle tables, runtime objects, robot path, or private truth to
    match the desired visual density.

Canonical renderer owner:

- Preferred owner: `roboclaws/maps/`, because the renderer is shared by Base
  Navigation Map bundle artifacts, Runtime Metric Map preview artifacts, report
  rendering, and operator-console preview generation.
- `scripts/operator_console/render_scene_previews.py` may call the shared
  renderer, but must not remain the only owner of the desired visual style.
- Existing bundle/console preview drawing paths should route through the shared
  renderer or be deleted/narrowed. Do not leave three live map preview dialects.

Visual role payload contract:

- Every operator-console view asset should carry structured metadata:
  `visual_role`, `artifact_source_family`, and provenance/view fields when
  available.
- Required roles are `base_navigation_map_preview`,
  `runtime_metric_map_preview`, and `topdown_scene_render`.
- DOM attributes used by UI E2E should derive from backend payload metadata, not
  hardcoded slot labels alone.

Context:

- Must-read:
  - `docs/plans/2026-06-17-sim-map-surface-simplification.md`
  - `docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md`
  - `roboclaws/maps/bundle.py`
  - `roboclaws/maps/runtime_prior_snapshot.py`
  - `roboclaws/household/realworld_run_artifacts.py`
  - `roboclaws/household/realworld_mcp_server.py`
  - `scripts/operator_console/render_scene_previews.py`
  - `scripts/molmo_cleanup/molmospaces_worker_outputs.py`
  - `scripts/molmo_cleanup/molmospaces_rendering.py`
  - `scripts/molmo_cleanup/molmospaces_room_map.py`
  - `roboclaws/operator_console/state.py`
  - `roboclaws/operator_console/static/index.html`
  - `roboclaws/operator_console/static/app.js`
  - `tests/unit/operator_console/test_state.py`
  - `tests/unit/operator_console/test_static_assets.py`
  - `tests/unit/operator_console/test_render_scene_previews.py`
  - `tests/contract/reports/test_molmo_cleanup_report.py`
- Useful:
  - `roboclaws/operator_console/static/previews/*-map.png`
  - `roboclaws/household/report_sections_nav2_map.py`
  - `roboclaws/household/report_sections_map.py`
  - `roboclaws/household/report_sections_robot.py`
  - `tests/contract/maps/test_nav2_map_bundle_contract.py`
- Avoid unless needed:
  - Historical `.planning/**` and retired semantic-map plans.
  - Generated `output/**` reports except for one or two local validation
    screenshots/examples.
  - Broad B1 / Agibot correspondence tooling.

Acceptance:

- SUCCESS:
  - `map_bundle/preview.png` and operator-console static map previews use the
    same default-preview overlay visual language.
  - `runtime_metric_map_preview.png` is generated from
    `runtime_metric_map.json` and visually reads as the same map with additional
    runtime overlays.
  - Operator console shows **Base Navigation Map preview** and
    **Runtime Metric Map preview** as separate map-role slots.
  - Operator console Top-down shows a real scene/camera render, not the runtime
    map preview or robot schematic map.
  - UI payloads and DOM expose structured visual roles so tests can reject
    wrong-source images.
  - Report copy names Runtime Metric Map preview as the current visual review
    artifact when present, while keeping `runtime_metric_map.json` as source
    truth.
  - Tests fail if `render_robot_map(...)` or any map-like semantic renderer is
    written to `*.topdown.png`.
- BLOCKED_NEEDS_DECISION:
  - none currently. Default decision: Base preview shows only base-map layers;
    Runtime preview carries object/robot overlays.
- BLOCKED_NEEDS_LOCAL_VALIDATION:
  - A browser/UI screenshot review is required before claiming the user-facing
    surprise is fixed.
- INTERMEDIATE_ONLY:
  - Code and deterministic tests may land as an intermediate branch only if
    local/browser visual validation is explicitly deferred.
- No regressions:
  - Existing public launch grammar remains unchanged.
  - Existing map bundle validation remains strict and fixture/private-truth
    boundaries stay intact.
  - B1 routes must omit unverifiable map/topdown previews rather than fabricate
    them.

Verification:

- Deterministic:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py tests/unit/operator_console/test_static_assets.py tests/unit/operator_console/test_render_scene_previews.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py tests/contract/maps/test_nav2_map_bundle_contract.py`
  - `ruff check .`
  - `ruff format --check .`
- Integration:
  - `just agent::eval recommend plan=docs/plans/2026-06-23-map-visual-role-contract.md budget=focused`
  - If static operator-console previews are regenerated, inspect the selected
    regenerated `*-map.png`, `*-topdown.png`, and `*-preview.json` files.
- Product-run:
  - Cheapest deterministic product proof:
    `just run::surface surface=household-world world=molmospaces/procthor-objaverse-val/0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels seed=7`
  - Review the produced `report.html`, `map_bundle/preview.png`,
    `runtime_metric_map.json`, and `runtime_metric_map_preview.png`.
- Local-live-manual:
  - Start the operator console with `just console::run`.
  - In the browser UI, verify a run/attached artifact shows:
    - Base Navigation Map preview in the default overlay style;
    - Runtime Metric Map preview as the same map plus runtime layers;
    - Top-down Scene View as a real scene render with robot point/heading.
  - Use `GSTACK_CHROMIUM_NO_SANDBOX=1` for browser QA if Chromium hits the
    Ubuntu/AppArmor sandbox issue.
- Optional:
  - Run the current UI E2E screenshot flow that produced the reported surprise
    and attach before/after screenshots to the implementation summary.

Execution:

- Main: supervise scope, avoid unrelated dirty files, and decide stop gates.
- Worker: none by default.
- Worker-goal: none.

To execute:

```text
/goal execute docs/plans/2026-06-23-map-visual-role-contract.md with intuitive-flow
```

Optional tracking: none.

Approval: approved and executed through `$intuitive-flow`.

## Implementation Evidence

Implementation capsule:
`docs/status/active/map-visual-role-contract.md`.

Completed behavior:

- Base Navigation Map preview and Runtime Metric Map preview now share the
  canonical 900 x 560 overlay visual language through `roboclaws/maps/preview.py`.
- Runtime preview is written as `runtime_metric_map_preview.png` beside
  `runtime_metric_map.json` in direct finalization and live MCP refresh paths.
- Operator-console view state exposes separate `map`, `runtime_map`, and
  `topdown` roles with `visual_role` and `artifact_source_family`.
- MolmoSpaces `robot_views/*.topdown.png` is scene/camera evidence again, not
  schematic map output.
- Report copy and focused tests now name Runtime Metric Map preview as the
  visual review artifact while keeping `runtime_metric_map.json` as source
  truth.

Proof summary:

- Focused operator-console unit/static/render tests passed.
- Focused report/live/checker tests passed.
- Full B1-inclusive map contract tests passed after initializing local vendor
  submodules.
- `ruff check .`, full `ruff format --check .`, and `git diff --check` passed.
- Product proof passed:
  `just run::surface surface=household-world world=molmospaces/procthor-objaverse-val/0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-public-labels seed=7`.
- Latest product artifacts under
  `output/household/household-world/map-build/direct-world-public-labels/0623_1756/seed-7`
  verified `map_bundle/preview.png` 900x560,
  `runtime_metric_map_preview.png` 900x560, and
  `robot_views/0001_after.topdown.png` 540x360.
- Browser validation passed against the operator console at
  `http://127.0.0.1:18082/`; screenshot:
  `output/operator-console/browser-map-role-proof.png`.

Remaining caveats:

- Static route previews leave Runtime Metric Map empty before a run; the
  canonical role/source browser proof is artifact-backed run state.

## Proposed Implementation Slices

### Slice 1: Canonical Map Preview Renderer

Make the desired default preview style reusable outside
`scripts/operator_console/render_scene_previews.py`.

Expected shape:

- A reusable renderer can produce a 900 x 560 map preview from Base Navigation
  Map-compatible data.
- The renderer supports a layer policy: base-only or runtime-overlay.
- The renderer records role/provenance metadata enough for report/UI checks.
- Existing default operator-console map previews can be regenerated without
  changing visual language.

### Slice 2: Base Navigation Map Preview Unification

Make active run `map_bundle/preview.png` match the default preview visual
language.

Expected shape:

- `write_source_frame_bundle_preview(...)` or its caller uses the canonical
  renderer for MolmoSpaces-style map bundles.
- Base preview contains only Base Navigation Map layers.
- Base preview renders navigation-area polygons/labels, not unverified room
  boundaries.
- Tests reject black occupancy thumbnails, full waypoint-id clutter, and
  static fixture/receptacle/runtime-object overlays in Base preview.

### Slice 3: Runtime Metric Map Preview

Generate and surface `runtime_metric_map_preview.png`.

Expected shape:

- `runtime_metric_map_preview.png` is written whenever
  `runtime_metric_map.json` is written for normal run finalization.
- Live MCP runs refresh the preview together with live
  `runtime_metric_map.json`.
- Direct finalization and live MCP refresh share one helper or one explicit
  contract for writing JSON plus preview metadata, so product proof cannot pass
  while live console refresh remains stale.
- Runtime preview overlays observed objects, anchors/candidates, robot path,
  robot point, and heading arrow using the same projection/colors as Base.
- Reports and operator console link this artifact as **Runtime Metric Map
  preview**.

### Slice 4: Top-down Scene View Restoration

Stop writing schematic maps into `*.topdown.png`.

Expected shape:

- MolmoSpaces robot views render top-down scene images through the existing
  camera-control/render path.
- Robot point and heading are annotated on top of the scene render when
  projection information is available.
- If robot projection is unavailable, Top-down remains a plain scene render and
  records the missing annotation reason rather than falling back to a map.
- Tests reject `render_robot_map(...)` as a Top-down producer.

### Slice 5: Operator Console And UI E2E Contract

Make the UI assert roles structurally.

Expected shape:

- Console has distinct slots/tabs for Base Navigation Map preview, Runtime
  Metric Map preview, and Top-down Scene View.
- `latest_view_assets` exposes visual role and artifact source family for each
  slot.
- Image buttons expose stable `data-view-role` or equivalent DOM attributes.
- Runtime preview appears in artifact links/state discovery as
  `runtime_metric_map_preview.png`.
- E2E checks fail on swapped images even if all slots have PNGs.

## Stop Gates

- Stop if a required change would alter agent-facing Base Navigation Map or
  Runtime Metric Map semantics.
- Stop if Base preview requires runtime-only objects, robot path, selected
  objects, static fixture/receptacle tables, or private truth to look like the
  target screenshot.
- Stop if Top-down cannot be restored without real scene camera evidence; do
  not route the Runtime Metric Map preview into Top-down as a fallback.
- Stop if B1/Agibot routes would need fabricated map/topdown previews to satisfy
  the UI. Missing honest proof is better than a fake preview.
- Stop if asset regeneration affects broad checked-in preview files outside the
  intentionally selected fixture set.
- Stop if deterministic tests pass but local/browser validation cannot be run;
  report `BLOCKED_NEEDS_LOCAL_VALIDATION`.

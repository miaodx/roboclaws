---
refactor_scope: python-quality-backend-entropy
status: COMPLETED_LEDGER
active_plan: docs/plans/refactor-python-quality-backend-entropy.md
last_compacted: 2026-06-15
---

# Completed Ledger: Python Quality And Backend Entropy

## Purpose

This is the only completed-work ledger for the Python quality/backend entropy
stream. Keep it compact so future agents do not need to read old execution
logs before choosing the next slice.

## Ledger Rules

- One completed slice or bundle per bullet.
- Keep each entry to the durable effect, proof class, and metric delta when it
  matters.
- Do not paste full command output or full test command lists.
- If this ledger gets bulky, compress older rows in place. Do not create a
  third related document.

## Metric Story

- Start of loop on 2026-06-14: 217 Ruff complexity violations and 61 oversized
  modules.
- Paused checkpoint on 2026-06-15 dirty worktree: 19 Ruff complexity violations
  and 56 oversized modules.
- Interpretation: control-flow complexity dropped sharply; oversized count
  moves slowly because large files can shrink materially and still remain above
  the 800-line ratchet threshold.

## Completed Bundles

- 2026-06-14: Backend facade started. `CleanupBackendSession` gained backend
  id/runtime-artifact attachment, shared backend construction, and common
  direct/MCP metadata attachment. Proof: focused backend/MCP tests and ratchet.

- 2026-06-14: Ratchet summary mode added. The quality gate can now report top
  oversized modules, high complexity entries, and complexity by file without
  changing default CI output. Proof: ratchet unit tests and ratchet gate.

- 2026-06-14: Shared worker runner extracted for MolmoSpaces/Isaac one-shot
  subprocesses. Persistent Molmo worker behavior stayed Molmo-specific. Proof:
  worker/backend unit tests and ratchet.

- 2026-06-14: Live cleanup checker split into staged assertion families, with
  Isaac runtime and semantic-pose checks moved to focused helpers. Metric:
  complexity baseline 217 -> 211.

- 2026-06-14: Direct cleanup artifact/result assembly moved to
  `realworld_run_artifacts.py`. `run_realworld_cleanup` became more staged and
  dropped substantially in size/complexity.

- 2026-06-14: Live MCP `done` finalization moved to
  `realworld_mcp_run_artifacts.py`, sharing backend metadata attachment instead
  of local backend-name/runtime wrappers. Metric: 211 -> 210.

- 2026-06-14: `RealWorldCleanupContract` constructor setup moved into
  `realworld_contract_init.py`; runtime-map and cleanup-worklist payloads moved
  into `realworld_contract_payloads.py`. Metric: 210 -> 209.

- 2026-06-14: Optional backend capabilities moved behind the backend facade:
  snapshots, robot views, close/final locations, and requested run size. This
  reduced repeated backend probing in direct cleanup and live MCP paths.

- 2026-06-14: Report sections started moving out of `report.py` into focused
  section modules for maps, timing, action evidence, grasp cache, proof bundle,
  agent/runtime-map, robot-view, and planner proof content.

- 2026-06-14: Planner-proof checker/probe, map-bundle validation, actionable
  snapshot, Isaac worker helper families, scene-camera helpers, visual-parity
  diagnostics, and RAW-FPV scoring each received targeted complexity splits.

- 2026-06-14: OpenAI Agents live runtime/budget/metrics helpers removed
  grouped production complexity from the OpenAI live runner and SDK driver
  surfaces, while keeping provider behavior mocked in default proof.

- 2026-06-15: Shared household live-runner helpers centralized CLI args,
  backend leasing, checker-gate filtering, and OpenAI metric readers across
  Codex, Claude Code, and OpenAI Agents SDK cleanup runners.

- 2026-06-15: Several focused production residuals were split without changing
  public schemas: semantic timeline, grasp cache blockers, map-bundle waypoint
  projection, physical Nav2 pilot phases, visual-candidate declaration, and
  Agibot rehearsal helpers.

- 2026-06-15: Test complexity cleanup began for live-runtime perf/profile
  tests, coding-agent Docker toolchain checks, public/private artifact
  contracts, fake Isaac backend assertions, and operator-console static assets.

- 2026-06-15: Dirty-worktree cleanup removed current ratchet blockers from
  model-matrix, operator-console, Agibot identity/readiness, report evidence
  badges, and MCP smoke artifact assertions without blessing unrelated parallel
  changes into the baseline.

- 2026-06-15: Pause checkpoint committed only the operator-console static asset
  test cleanup. Ratchet passed at 19 Ruff complexity violations and 56
  oversized modules; remaining work returned to the active plan.

- 2026-06-15: Scene-sampler scanner evidence/admission helpers moved into
  `scene_sampler_scanner.py`, removing production complexity rows from
  `scene_sampler.py`. Metric: dirty resumed checkpoint 28 -> 25 complexity
  rows; oversized modules stayed at 60. Proof: focused scene-sampler tests,
  ruff, format check, and ratchet.

- 2026-06-16: Scene-sampler source-selection metadata moved into
  `scene_sampler_sources.py` while admitting the `procthor-objaverse-val`
  sampler rows and fixtures. Metric: `scene_sampler.py` is down to 2432 lines
  but remains a P1 hard-ceiling candidate. Proof: focused scene-sampler/eval
  tests, ruff, format check, and ratchet.

- 2026-06-16: Scene-sampler readiness-export artifact assertions moved behind
  focused local helpers, removing that operator-console test from the ratchet
  complexity list. Current ratchet still shows 25 complexity rows and 62
  oversized modules, led next by `export_scene_sampler_readiness.py`,
  `scene_sampler.py`, and one launch test. Proof: focused scene-sampler/eval
  tests, ruff, format check, and ratchet.

- 2026-06-16: Scene-sampler readiness export script split payload construction,
  artifact writes, generated eval emission, summary assembly, and threshold
  checks into focused helpers. Metric: 25 -> 21 complexity rows; oversized
  modules unchanged at 62. Proof: focused scene-sampler/eval tests, ruff,
  format check, and ratchet.

- 2026-06-16: Scene-sampler projection launch test split source-specific
  assertions into focused helpers, removing the last scene-sampler test row
  from the complexity list. Metric: 21 -> 20 complexity rows; oversized modules
  unchanged at 62. Proof: focused scene-sampler/eval tests, ruff, format check,
  and ratchet.

- 2026-06-16: Scene-sampler source prep and availability helpers moved into
  `scene_sampler_prep.py`, keeping `scene_sampler.py` as the public sampler
  facade. Metric: `scene_sampler.py` 2457 -> 1975 lines and no longer above the
  2000-line hard ceiling; ratchet remains 20 complexity rows and 62 oversized
  modules. Proof: focused scene-sampler/eval tests, ruff, format check, and
  ratchet.

- 2026-06-16: Planner proof bundle runner report assertions moved behind
  focused HTML helper families while preserving rendered report coverage.
  Metric: 20 -> 19 complexity rows; oversized modules unchanged at 62. Proof:
  focused report test, ruff, format check, and ratchet.

- 2026-06-16: Fake Isaac backend protocol test split runtime, scene-binding,
  visual-artifact, semantic-pose, and robot-import checks into focused local
  helpers. Metric: 19 -> 18 complexity rows; oversized modules unchanged at 62.
  Proof: focused Isaac backend test, ruff, format check, and ratchet.

- 2026-06-16: Scene-camera comparison report contract test split fixture-image
  setup, review UI, contract-section, lighting/render-domain, and lane-image
  assertions into focused helpers. Metric: 18 -> 17 complexity rows; oversized
  modules unchanged at 62. Proof: focused scene-camera report test, ruff,
  format check, and ratchet.

- 2026-06-16: Planner manipulation probe report assertions moved into focused
  overview, cleanup-binding, sampler-failure, and runtime-diagnostics helper
  families. Metric: removed the `93>50` report row; dirty worktree ratchet
  stayed at 17 because unrelated scene-sampler readiness edits introduced a
  new `52>50` helper row. Proof: focused report test, ruff, format check, and
  ratchet.

- 2026-06-16: Real Isaac worker semantic-pose recapture test split runtime
  setup, capture hooks, worker commands, result assertions, and persisted-state
  assertions into focused helpers. Metric: dirty worktree ratchet 17 -> 15
  complexity rows; oversized modules unchanged at 62. Proof: focused Isaac
  backend test, ruff, format check, and ratchet.

- 2026-06-16: Minimal-map privacy/generated-candidate contract test split
  first-observation lookup, static-map privacy checks, target-candidate search
  checks, public-anchor checks, and observed-object anchor checks into focused
  helpers. Metric: 15 -> 14 complexity rows; oversized modules unchanged at
  62. Proof: focused realworld-contract test, ruff, format check, and ratchet.

- 2026-06-16: Nav2-shaped public map/provenance contract test split detection
  lookup, confirmation/pick/navigation flow, map-shape assertions, navigation
  provenance assertions, and runtime-map assertions into focused helpers.
  Metric: 14 -> 13 complexity rows; oversized modules unchanged at 62. Proof:
  focused realworld-contract test, ruff, format check, and ratchet.

- 2026-06-16: Robot visual timeline report test split render-context setup,
  robot-view step builders, layout/lightbox/semantic-substep/pose/caveat
  assertions, and yaw-rendering proof into focused helpers. Metric: 13 -> 12
  complexity rows; oversized modules unchanged at 62. Proof: focused report
  test, ruff, format check, and ratchet.

- 2026-06-16: Robot-camera object parity audit test split fixture files/state,
  audit assertions, render-parity diagnostics assertions, and report assertions
  into focused helpers. Metric: 12 -> 11 complexity rows; oversized modules
  unchanged at 62. Proof: focused apple-to-apple test, ruff, format check, and
  ratchet.

- 2026-06-16: Robot-camera render-contract diagnostics test split light/shadow
  fixtures, scene-binding diagnostics, summary checks, material response checks,
  preview-surface checks, and tone/location assertions into focused helpers.
  Metric: 11 -> 10 complexity rows; oversized modules unchanged at 62. Proof:
  focused apple-to-apple test, ruff, format check, and ratchet.

- 2026-06-16: Agibot semantic map-build MCP contract test split tool-response,
  run-identity, policy-trace, runtime-map, and artifact/report assertions into
  focused helpers. Metric: 10 -> 9 complexity rows; oversized modules unchanged
  at 62. Proof: focused physical Agibot pilot test, ruff, format check, and
  ratchet.

- 2026-06-16: Isaac semantic-pose stage tests now share fake USD stage, parent
  transform, translate-op, PXR install, and semantic-pose state helpers instead
  of redefining nested fake classes per case. Metric: 9 -> 7 complexity rows;
  oversized modules unchanged at 62. Proof: focused Isaac backend tests, ruff,
  format check, and ratchet.

- 2026-06-16: Isaac head-camera robot-pose test moved fake robot prim/stage,
  PXR install, head-camera xform ops, and shared robot-pose state into focused
  helpers. Metric: 7 -> 6 complexity rows; oversized modules unchanged at 62.
  Proof: focused Isaac backend test, ruff, format check, and ratchet.

- 2026-06-16: Isaac scene-camera color-profile test moved fake sim, sim-utils,
  camera config, tensor, camera type, torch shim, and camera request setup into
  focused helpers. Metric: 6 -> 5 complexity rows; oversized modules unchanged
  at 62. Proof: focused Isaac backend test, ruff, format check, and ratchet.

- 2026-06-16: Planner manipulation checker report fixture builder became
  table-driven, with policy-exception and task-sampler diagnostics fragments in
  focused helpers. Metric: 5 -> 3 complexity rows; oversized modules unchanged
  at 62. Proof: planner manipulation checker contract file, ruff, format check,
  and ratchet.

- 2026-06-16: Realworld cleanup checker Isaac robot-view fixture split image
  writing, report/artifact wiring, per-step provenance, camera-control
  contracts, and summary construction into focused helpers. Metric: 3 -> 1
  complexity rows; oversized modules unchanged at 62. Proof: realworld cleanup
  checker contract file, ruff, format check, and ratchet.

- 2026-06-16: Operator-console scene-preview map transform split semantic-map
  point collection, padded bounds, and plot geometry helpers. Metric: 1 -> 0
  Ruff complexity rows; oversized modules unchanged at 62. Proof:
  operator-console render-preview tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac runtime-smoke USD generation moved from the backend worker
  into `isaac_runtime_smoke_usd.py`, keeping worker-private aliases for the
  existing command/tests. Metric: `isaac_lab_backend_worker.py` 7809 -> 7636
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac backend tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac public scene-binding diagnostics and matcher logic moved
  from the backend worker into `isaac_scene_bindings.py`, keeping worker-private
  aliases for current tests and callers. Metric: `isaac_lab_backend_worker.py`
  7636 -> 7339 lines; Ruff complexity stayed at 0 and oversized modules stayed
  at 62. Proof: focused Isaac scene-binding tests, ruff, format check, and
  ratchet.

- 2026-06-16: Isaac USD scene metadata/path-index helpers moved from the
  backend worker into `isaac_scene_index_metadata.py`, keeping worker-private
  aliases for path heuristics and MolmoSpaces metadata tests. Metric:
  `isaac_lab_backend_worker.py` 7339 -> 7178 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac metadata/index
  tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac USD support-pose and support-surface selection/scoring
  moved from the backend worker into `isaac_support_surface_geometry.py`, with
  worker wrappers preserving monkeypatchable `_usd_world_bounds` and
  `_iter_usd_prim_range` tests. Metric: `isaac_lab_backend_worker.py` 7178 ->
  7020 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac support-pose/support-surface tests, ruff, format check,
  and ratchet.

- 2026-06-16: Isaac scene-index room-outline and USD reference-asset diagnostic
  helpers moved from the backend worker into `isaac_scene_index_geometry.py`,
  keeping worker-private aliases and the `_usd_world_bounds` room-outline
  wrapper. Metric: `isaac_lab_backend_worker.py` 7020 -> 6923 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Isaac room-outline/placement tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac native render diagnostics and capture-quality metadata
  moved from the backend worker into `isaac_render_diagnostics.py`, keeping
  worker-private wrappers for the monkeypatchable settings hook and current
  diagnostics tests. Metric: `isaac_lab_backend_worker.py` 6923 -> 6598 lines;
  Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  focused Isaac render-diagnostics tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac segmentation tensor diagnostics, label-map parsing, bbox
  extraction, and selected-USD-prim matching moved from the backend worker into
  `isaac_segmentation_diagnostics.py`, keeping worker-private wrapper names for
  capture hooks and tests. Metric: `isaac_lab_backend_worker.py` 6598 -> 6278
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac segmentation/fake/real-init tests, ruff, format check,
  and ratchet.

- 2026-06-16: Isaac robot-view camera geometry, RBY1M camera constants, FOV
  metadata, chase-camera pose math, static head-pitch math, and tensor/vector
  coercion moved from the backend worker into `isaac_camera_geometry.py`, with
  worker-private wrappers and constants preserved for tests/capture hooks.
  Metric: `isaac_lab_backend_worker.py` 6278 -> 6155 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Isaac camera
  geometry/robot-pose tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac stage bounds and capture-lighting diagnostics moved from
  the backend worker into `isaac_stage_lighting.py`, keeping lazy PXR imports
  and worker-private wrappers for scene-camera capture hooks and light-path
  tests. Metric: `isaac_lab_backend_worker.py` 6155 -> 5976 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Isaac stage-light/scene-camera tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac RBY1M robot-import planning, import-summary loading, URDF
  discovery, and robot payload construction moved from the backend worker into
  `isaac_robot_import.py`, keeping worker-private wrappers and constants for
  current tests and monkeypatch hooks. Metric: `isaac_lab_backend_worker.py`
  5976 -> 5903 lines; Ruff complexity stayed at 0 and oversized modules stayed
  at 62. Proof: focused Isaac robot-import/robot-view tests, ruff, format
  check, and ratchet.

- 2026-06-16: Isaac scene-load and mapping-gap diagnostics moved from the
  backend worker into `isaac_mapping_diagnostics.py`, with worker wrappers
  injecting existing robot-view image checks and preserving `_scene_usd_path`.
  Metric: `isaac_lab_backend_worker.py` 5903 -> 5715 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Isaac fake
  and real mapping-gap tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac runtime/rendering diagnostics payload construction moved
  from the backend worker into `isaac_runtime_diagnostics.py`, keeping lazy
  module probes and worker wrappers for current runtime metadata tests. Metric:
  `isaac_lab_backend_worker.py` 5715 -> 5634 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac runtime/render
  metadata tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac scene-camera request geometry, view-spec loading,
  lane-orbit/backend-transform math, USD-bound target extraction, and
  image-variance checks moved from the backend worker into
  `isaac_scene_camera_geometry.py`, with worker-private wrappers preserved for
  existing tests and capture hooks. Metric: `isaac_lab_backend_worker.py` 5634
  -> 5524 lines; Ruff complexity stayed at 0 and oversized modules stayed at
  62. Proof: focused Isaac scene-camera geometry/capture tests, ruff, format
  check, and ratchet.

- 2026-06-16: Isaac real robot-view image reuse, snapshot source selection,
  nonblank RGB copying, and robot-view provenance payloads moved from the
  backend worker into `isaac_robot_view_artifacts.py`, preserving worker
  wrappers used by mapping diagnostics and robot-view hooks. Metric:
  `isaac_lab_backend_worker.py` 5524 -> 5446 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac fake/real
  robot-view and snapshot tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac semantic-pose initial state, event recording, waypoint
  pose events, and shared pose-state payload assembly moved from the backend
  worker into `isaac_semantic_pose_state.py`, with injected worker resolvers
  preserving existing object/receptacle pose payloads. Metric:
  `isaac_lab_backend_worker.py` 5446 -> 5355 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac action,
  waypoint, and semantic-pose recapture tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac semantic placement resolution, direct-support candidate
  selection, footprint/clearance math, and placement diagnostics moved from
  the backend worker into `isaac_placement_resolution.py`, with worker-private
  wrappers preserving existing tests and monkeypatch hooks. Metric:
  `isaac_lab_backend_worker.py` 5355 -> 5097 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, and ratchet.

- 2026-06-16: Isaac init scenario shaping, scene-index generated-mess
  selection, map-bundle scenario builders, and cleanup alias matching moved
  from the backend worker into `isaac_scenario_builders.py`, with
  worker-private wrappers preserving current scene-index tests. Metric:
  `isaac_lab_backend_worker.py` 5097 -> 4678 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, and ratchet.

- 2026-06-16: Isaac robot-pose and focus payload helpers moved from the
  backend worker into `isaac_robot_pose_focus.py`, with worker-private wrappers
  preserving current pose/focus tests and placement/semantic-pose hook call
  shapes. Metric: `isaac_lab_backend_worker.py` 4678 -> 4578 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Isaac backend tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac semantic-pose USD stage application moved from the backend
  worker into `isaac_semantic_pose_stage.py`, with worker wrappers preserving
  current camera-capture hooks and stage-application tests. Metric:
  `isaac_lab_backend_worker.py` 4578 -> 4495 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, and ratchet.

- 2026-06-16: Isaac worker protocol/state utilities moved from the backend
  worker into `isaac_worker_protocol.py`, preserving worker-private wrappers
  for state IO, command envelopes, counters, public-state projection, and
  placeholder image generation. Metric: `isaac_lab_backend_worker.py` 4495 ->
  4471 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac backend tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac observe/navigation/manipulation/done command handlers
  moved from the backend worker into `isaac_worker_commands.py`, with
  worker-private wrappers preserving CLI dispatch, tests, semantic-pose event
  hooks, and placement hooks. Metric: `isaac_lab_backend_worker.py` 4471 ->
  4264 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac backend tests, ruff, format check, and ratchet.

- 2026-06-16: Isaac snapshot, robot-view, scene-camera, locations, and
  output-provenance command orchestration moved from the backend worker into
  `isaac_worker_outputs.py`, with worker-private wrappers preserving CLI
  dispatch, monkeypatch hooks, and artifact payload shapes. Metric:
  `isaac_lab_backend_worker.py` 4264 -> 3999 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces snapshot, robot-view, scene-camera, camera adjustment,
  and output-provenance orchestration moved from the subprocess worker into
  `molmospaces_worker_outputs.py`, with worker-private wrappers preserving
  CLI/serve dispatch and monkeypatch render hooks. Metric:
  `molmospaces_subprocess_worker.py` 4130 -> 3956 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Molmo
  subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces placement resolution, support-surface geometry,
  placement diagnostics, receptacle relation policy, and object footprint/AABB
  helpers moved from the subprocess worker into `molmospaces_placement.py`,
  with worker-private wrappers preserving current placement tests and call
  shapes. Metric: `molmospaces_subprocess_worker.py` 3956 -> 3685 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Molmo subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces robot-pose target projection, waypoint room
  projection, room relation payloads, stand-off, head-pitch, and scene-center
  helpers moved from the subprocess worker into `molmospaces_robot_pose.py`,
  with worker-private wrappers preserving current pose command/tests. Metric:
  `molmospaces_subprocess_worker.py` 3685 -> 3577 lines; Ruff complexity stayed
  at 0 and oversized modules stayed at 62. Proof: focused Molmo subprocess
  backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces robot-map rendering, map bounds/points, room-outline
  collection, room mesh XY bounds, fallback room outlines, and map item labels
  moved from the subprocess worker into `molmospaces_room_map.py`, with
  worker-private wrappers preserving current map and room-outline tests.
  Metric: `molmospaces_subprocess_worker.py` 3577 -> 3397 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Molmo subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces generated-mess manifest loading, scene XML
  resolution, scene-ref path normalization, install-prep, and scenario-id
  helpers moved from the subprocess worker into `molmospaces_worker_init.py`,
  with worker-private wrappers preserving current scene-resolution tests.
  Metric: `molmospaces_subprocess_worker.py` 3397 -> 3345 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Molmo subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces focus-camera/view-spec math, focus payloads, focus
  image annotation, and visual-grounding status helpers moved from the
  subprocess worker into `molmospaces_focus_camera.py`, with worker-private
  wrappers preserving direct tests and monkeypatch hooks. Metric:
  `molmospaces_subprocess_worker.py` 3345 -> 3185 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Molmo
  subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces public scenario projection, private score/readback,
  generated-mess placement target selection, and inventory collection helpers
  moved from the subprocess worker into `molmospaces_scenario_state.py`, with
  worker-private wrappers preserving operator-console preview imports and
  current tests. Metric: `molmospaces_subprocess_worker.py` 3185 -> 2978
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Molmo subprocess backend/operator-console tests, ruff, format
  check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces worker JSON-line serving, loaded-state command
  dispatch, CLI-kwargs normalization, scalar parsing, state IO, counters, and
  ok/error envelopes moved from the subprocess worker into
  `molmospaces_worker_protocol.py`, with worker-private wrappers preserving
  CLI/serve call shapes and tests. Metric: `molmospaces_subprocess_worker.py`
  2978 -> 2942 lines; Ruff complexity stayed at 0 and oversized modules
  stayed at 62. Proof: focused Molmo subprocess backend tests, ruff, format
  check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces fixed/free camera rendering, camera diagnostics,
  rendered-image loading, focus segmentation visibility, highlight-diff
  fallback boxes, offscreen framebuffer growth, subtree geometry lookup,
  bbox inflation, and render dimension helpers moved from the subprocess
  worker into `molmospaces_rendering.py`, with worker-private wrappers
  preserving current monkeypatch hooks and geometry helper call sites. Metric:
  `molmospaces_subprocess_worker.py` 2942 -> 2809 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Molmo
  subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces MuJoCo model loading/cache, robot result metadata,
  robot base/head qpos helpers, held-object robot-relative sync, runtime render
  state articulation evidence, and openable-receptacle joint discovery moved
  from the subprocess worker into `molmospaces_runtime_state.py`, with
  worker-private wrappers preserving cache, robot-view, held-object, and
  runtime-state test hooks. Metric: `molmospaces_subprocess_worker.py` 2809 ->
  2627 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Molmo subprocess backend tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-16: MolmoSpaces navigation, pick/place, open/close receptacle,
  place-inside, frame-comparison, done, and state-mutation response helpers
  moved from the subprocess worker into `molmospaces_actions.py`, with
  worker-private wrappers preserving action command names and direct
  `_place_object_at_receptacle` tests. Metric:
  `molmospaces_subprocess_worker.py` 2627 -> 2377 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Molmo
  subprocess backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces `init_state` scene/model setup, generated-mess
  target selection, initial state payload, robot-start placement, and init
  response assembly moved into `molmospaces_worker_state.py`, with the
  subprocess worker retaining a thin `init_state` delegate and wrapper hooks.
  Metric: `molmospaces_subprocess_worker.py` 2377 -> 2272 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Molmo subprocess/backend init-state tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-16: MolmoSpaces subprocess worker delegate imports switched from
  per-symbol `_impl` aliases to helper-module namespace imports, preserving
  worker-private wrapper names while removing import-block hard-ceiling weight.
  Metric: `molmospaces_subprocess_worker.py` 2272 -> 1811 lines, clearing the
  2000-line hard ceiling; Ruff complexity stayed at 0 and oversized modules
  stayed at 62. Proof: focused Molmo subprocess/backend init-state tests, ruff,
  format check, py_compile, and ratchet.

- 2026-06-16: Isaac backend worker delegate imports switched from per-symbol
  `_impl` aliases to helper-module namespace calls for placement, command,
  output, scenario, camera-request, semantic-pose-stage, and worker-protocol
  helpers while preserving worker-private wrapper names and monkeypatch
  surfaces. Metric: `isaac_lab_backend_worker.py` 3999 -> 3828 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: focused
  Isaac backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac generated-mess placement seeding, manifest target lookup,
  wrong-receptacle selection, object location writeback, and first-target
  location selection moved from the backend worker into
  `isaac_scenario_state.py`, with worker-private wrappers preserving current
  init and command hook call shapes. Metric: `isaac_lab_backend_worker.py`
  3828 -> 3742 lines; Ruff complexity stayed at 0 and oversized modules stayed
  at 62. Proof: focused Isaac backend tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-16: Isaac USD scene-index inspection, geometry diagnostics, world
  bounds/root-position extraction, room-outline lookup, and receptacle support
  surface wiring moved from the backend worker into
  `isaac_scene_index_geometry.py`, with worker-private wrappers and monkeypatch
  hooks preserved. Metric: `isaac_lab_backend_worker.py` 3742 -> 3608 lines;
  Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  focused Isaac backend tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac RBY1M robot stage reference, head-camera robot pose
  application, static head-pitch transform, USD camera diagnostics, eye-target
  camera diagnostics, and head-camera lens application moved from the backend
  worker into `isaac_robot_camera_stage.py`, with worker-private wrappers
  preserving current capture hooks and direct tests. Metric:
  `isaac_lab_backend_worker.py` 3608 -> 3404 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac scene-camera request capture with an existing simulation
  moved from the backend worker into `isaac_scene_camera_capture.py`, with the
  worker wrapper preserving the current direct test and monkeypatch hooks.
  Metric: `isaac_lab_backend_worker.py` 3404 -> 3315 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Isaac backend
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac backend `init_state` runtime/scenario bootstrap, initial
  state payload assembly, placeholder smoke artifact write, and init response
  assembly moved into `isaac_worker_state.py`, with the worker preserving the
  public `init_state(args)` entry point and monkeypatchable helper hooks.
  Metric: `isaac_lab_backend_worker.py` 3315 -> 3184 lines; Ruff complexity
  stayed at 0 and oversized modules stayed at 62. Proof: focused Isaac backend
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac real runtime smoke launch/capture orchestration and
  semantic-pose robot-view recapture launch moved into
  `isaac_runtime_capture.py`, while worker wrappers preserve the
  monkeypatchable runtime-smoke and semantic-pose entry points plus deferred
  SimulationApp ownership. Metric: `isaac_lab_backend_worker.py` 3184 -> 3114
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused Isaac backend tests, ruff, format check, py_compile, and
  ratchet.

- 2026-06-16: Isaac scenario-builder delegate wrappers in the backend worker
  were collapsed into worker-private aliases to the extracted builder module,
  preserving direct test names while removing wrapper-only bulk. Metric:
  `isaac_lab_backend_worker.py` 3114 -> 2945 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac semantic-pose object projection, articulation projection,
  USD prim-path resolution, and object world-bounds center lookup moved into
  `isaac_semantic_pose_projection.py`, with worker-private wrappers preserving
  direct test names and semantic-pose hook surfaces. Metric:
  `isaac_lab_backend_worker.py` 2945 -> 2881 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused Isaac backend tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: Isaac backend worker context helpers moved into
  `isaac_worker_context.py`, remaining wrapper-only helper imports were
  collapsed to module namespaces and dynamic hook adapters, and
  worker-private aliases were preserved for direct tests and monkeypatch
  surfaces. Metric: `isaac_lab_backend_worker.py` 2881 -> 1990 lines,
  clearing the 2000-line hard ceiling; Ruff complexity stayed at 0 and
  oversized modules stayed at 62. Proof: focused Isaac backend tests, ruff,
  format check, py_compile, and ratchet.

- 2026-06-16: Real-world contract map-bundle projection, public-room hints,
  fallback waypoint geometry, and fixture destination-policy helpers moved
  into `realworld_contract_projection.py` and
  `realworld_contract_fixture_projection.py`, while `realworld_contract.py`
  keeps compatibility aliases for existing private helper access. Metric:
  `realworld_contract.py` 6606 -> 5637 lines; the new helper modules are 613
  and 561 lines; Ruff complexity stayed at 0 and oversized modules stayed at
  62. Proof: focused realworld-contract/map tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-16: Isaac runtime diagnostics, scene-index artifact rows, and
  semantic-pose state tables moved from `report.py` into
  `report_sections_isaac.py`, with `report.py` passing existing metric,
  artifact-link, and boolean renderers to preserve report markup. Metric:
  `report.py` 6165 -> 5816 lines; Ruff complexity stayed at 0 and oversized
  modules stayed at 62. Proof: focused cleanup report/checker tests, ruff,
  format check, py_compile, and ratchet.

- 2026-06-16: Scene-camera Isaac USD render-contract parsing, material/light
  extraction, and visual-physics summary helpers moved into
  `scene_camera_usda_contract.py`, while `scene_camera_comparison.py` keeps
  private aliases for existing report and apple-to-apple consumers. Metric:
  `scene_camera_comparison.py` 6480 -> 6200 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: focused scene-camera and
  apple-to-apple tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Scene-camera image tone, region, pixel-summary, and pair-delta
  metrics moved into `scene_camera_image_metrics.py`, while
  `scene_camera_comparison.py` keeps private aliases for report diagnostics and
  contract tests. Metric: `scene_camera_comparison.py` 6200 -> 6120 lines;
  Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  focused scene-camera tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Scene-camera native Isaac render diagnostics, lighting/tone
  provenance, shadow-parity, and key-light direction helpers moved into
  `scene_camera_lighting_diagnostics.py`, with private aliases preserved in the
  comparison facade. Metric: `scene_camera_comparison.py` 6120 -> 5476 lines;
  Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  focused scene-camera and apple-to-apple tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-16: Grasp cache generation, pose-policy cache, filter diagnostics,
  and initial-contact report sections moved from `report.py` into
  `report_sections_grasp_diagnostics.py`, while public render imports from
  `roboclaws.household.report` remain stable. Metric: `report.py` 5816 -> 5307
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: focused grasp report tests, ruff, format check, py_compile, and
  ratchet.

- 2026-06-16: Planner proof request-selection tables moved from `report.py`
  into `report_sections_proof_selection.py`, keeping proof-bundle report
  output and checker expectations stable. Metric: `report.py` 5307 -> 4880
  lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: proof-bundle report/checker tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-16: Agent-view forbidden-key checks, cleanup policy trace wrapping,
  real-robot readiness assembly, and public acceptance normalization moved from
  `realworld_contract.py` into `realworld_agent_view_contract.py`, with the
  existing public imports preserved from the contract facade. Metric:
  `realworld_contract.py` 5637 -> 5556 lines; Ruff complexity stayed at 0 and
  oversized modules stayed at 62. Proof: focused realworld-contract/report
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Visual-candidate evidence, state, validation, bbox
  reviewability, and category-alias helpers moved into
  `realworld_visual_candidates.py`, while `realworld_contract.py` keeps facade
  aliases and private-key assertion. Metric: `realworld_contract.py` 5556 ->
  5212 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: full realworld-contract test file, ruff, format check, py_compile,
  and ratchet.

- 2026-06-16: Scene-camera render-domain calibration, backend-swap geometry,
  source-reference, view-triage, and artifact contract probe helpers moved into
  `scene_camera_render_domain.py`, while `scene_camera_comparison.py` keeps
  private facade aliases for tests and apple-to-apple consumers. Metric:
  `scene_camera_comparison.py` 5476 -> 4693 lines; Ruff complexity stayed at 0
  and oversized modules stayed at 62. Proof: full scene-camera contract tests,
  focused apple-to-apple render-contract tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-16: Scene-camera render source references moved from
  `scene_camera_render_domain.py` into `scene_camera_render_sources.py`,
  keeping the new render-domain helper under the 800-line target. Metric:
  `scene_camera_render_domain.py` 873 -> 798 lines; Ruff complexity stayed at
  0 and oversized modules stayed at 62. Proof: full scene-camera contract
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Robot-camera apple-to-apple HTML report rendering moved into
  `robot_camera_apple2apple_report.py`, while the runner keeps private aliases
  for current path-loaded tests. Metric:
  `run_robot_camera_apple2apple_comparison.py` 5332 -> 4900 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: full
  apple-to-apple unit test file, ruff, format check, py_compile, and ratchet.

## Do Not Reopen Without Fresh Evidence

- Backend facade mainline already owns backend id/runtime metadata/artifact
  attachment; reopen only for new backend evidence leakage.
- Live checker and MCP/directed cleanup finalizers already have focused helper
  ownership; reopen only for schema drift or duplicated finalization logic.
- OpenAI live metrics/budget helpers already removed the known production
  complexity rows; file-size hard-ceiling work is still active, but the old
  metrics extraction slice is done.
- Completed report-section extraction is partial evidence, not a reason to
  treat `report.py` as done; the active plan still owns the hard-ceiling split.

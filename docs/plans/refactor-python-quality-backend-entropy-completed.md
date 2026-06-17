---
refactor_scope: python-quality-backend-entropy
status: COMPLETED_LEDGER
active_plan: docs/plans/refactor-python-quality-backend-entropy.md
last_compacted: 2026-06-17
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

- 2026-06-16: Runtime Metric Map prior normalization and target-fixture
  inference moved from `realworld_contract.py` into
  `realworld_runtime_map_contract.py`, while facade wrappers remain for init
  and tests. Metric: `realworld_contract.py` 5212 -> 5126 lines; Ruff
  complexity stayed at 0 and oversized modules stayed at 62. Proof: full
  realworld-contract test file, ruff, format check, py_compile, and ratchet.

- 2026-06-16: Runtime Metric Map candidate typing, producer summary,
  observed-object confidence/actionability, and synthetic observation-id
  helpers also moved into `realworld_runtime_map_contract.py`. Metric:
  `realworld_contract.py` 5126 -> 5095 lines; Ruff complexity stayed at 0 and
  oversized modules stayed at 62. Proof: full realworld-contract test file,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: Nav2 map bundle report rendering moved into
  `report_sections_nav2_map.py`, and semantic-map overlay/artifact generation
  moved into `report_semantic_map_artifacts.py`. Metric: `report.py` 4880 ->
  4051 lines; Ruff complexity stayed at 0 and oversized modules stayed at 62.
  Proof: full cleanup report contract test file, ruff, format check,
  py_compile, and ratchet.

- 2026-06-16: Raw-FPV, model-declared observation, camera-labeler, advisory,
  and private-evaluation report sections moved into `report_sections_agent.py`.
  Metric: `report.py` 4051 -> 3820 lines while `report_sections_agent.py`
  remains under the 800-line target; Ruff complexity stayed at 0 and oversized
  modules stayed at 62. Proof: full cleanup report contract test file, ruff,
  format check, py_compile, and ratchet.

- 2026-06-16: Scene-sampler typed row/ref contracts and readiness lane
  constants moved into `scene_sampler_types.py`, clearing the hard-ceiling drift
  introduced by the diverse-selection sampler update. Metric:
  `scene_sampler.py` 2077 -> 1996 lines; Ruff complexity stayed at 0 and
  oversized modules stayed at 62. Proof: full scene-sampler unit test file,
  ruff, format check, py_compile, and ratchet.

- 2026-06-16: MolmoSpaces Agibot rehearsal private-evaluation,
  manipulation-evidence, and readiness payload helpers moved into
  `agibot_contract_rehearsal_evidence.py`. Metric:
  `agibot_contract_rehearsal.py` 2140 -> 1949 lines, clearing that hard-ceiling
  row; Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  focused Agibot contract rehearsal test file, ruff, format check,
  py_compile, and ratchet.

- 2026-06-16: Realworld cleanup done-readiness blocker and policy helpers
  moved into `realworld_done_readiness.py`, keeping `RealWorldCleanupContract`
  as the public facade. Metric: `realworld_contract.py` 5095 -> 4930 lines;
  Ruff complexity stayed at 0 and oversized modules stayed at 62. Proof:
  realworld contract and MCP server contract test files, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Report-performance skill calibration script now delegates to the
  canonical `scripts/reports/calibrate_model_latency.py`, removing the stale
  skill-local simplified implementation. Metric: skill script 112 -> 14 lines;
  current dirty-checkout ratchet is 15 complexity rows and 65 oversized modules
  because of plan-external render-preview drift tracked in the active plan.
  Proof: wrapper CLI help, report-performance unit tests, ruff, format check,
  and ratchet.

- 2026-06-17: Scene-only prefilter report/policy/evidence helpers moved from
  `scene_sampler.py` into `scene_sampler_prefilter.py`, keeping
  `scene_only_prefilter_report` as the public facade. Metric:
  `scene_sampler.py` 3070 -> 2607 lines; ratchet remains 15 complexity rows
  and 65 oversized modules, so scene sampler stays active P1 debt. Proof:
  focused scene-sampler and readiness-export tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Candidate-profile policy, index expansion, row/status assembly,
  and gate-mismatch profile helpers moved from `scene_sampler.py` into
  `scene_sampler_profile.py`, keeping `candidate_profile_report` as the public
  facade and preserving the existing MolmoSpaces dependency hook surface.
  Metric: `scene_sampler.py` 2607 -> 2241 lines; current dirty-checkout
  ratchet is 18 complexity rows and 65 oversized modules because unrelated B1
  Map 12 runtime-bundle drift is now counted. Proof: focused scene-sampler and
  readiness-export tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Scene-sampler source-prep report assembly moved into
  `scene_sampler_prep.py`, and scanner-admission row assembly moved into
  `scene_sampler_scanner.py`, leaving `scene_sampler.py` as the launch/eval
  facade. Metric: `scene_sampler.py` 2241 -> 1965 lines, clearing the hard
  ceiling; ratchet is 18 complexity rows and 66 oversized modules because the
  scanner owner crossed the 800-line target while staying below the warning
  band. Proof: focused scene-sampler, readiness-export, scanner-runner tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-17: Runtime Metric Map static-map and observed-object payload
  assembly moved from `RealWorldCleanupContract` into
  `realworld_runtime_map_contract.py`, and `realworld_contract_payloads.py`
  now passes explicit public inputs instead of requiring facade-private payload
  methods. Metric: `realworld_contract.py` 5036 -> 4847 lines; ratchet remains
  18 complexity rows and 66 oversized modules. Proof: realworld contract, MCP
  server, and cleanup-checker contract tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-17: B1 Map 12 runtime-bundle review-manifest validation split into
  header, label, shared-area, and explicit-policy helper families while
  preserving existing manifest error text and runtime compiler behavior.
  Metric: ratchet 18 -> 15 complexity rows; oversized modules unchanged at
  66. Proof: B1 runtime-bundle contract tests, B1 operator-preview tests,
  ruff, format check, py_compile, and ratchet.

- 2026-06-17: B1 Map 12 label-tool semantic layer construction and draft
  manifest validation split into fixture/waypoint/driveable-way and
  header/label/geometry helper families while preserving packet keys and
  manifest error text. Metric: ratchet 15 -> 11 complexity rows; oversized
  modules unchanged at 66. Proof: B1 label-tool contract tests, ruff, format
  check, py_compile, and ratchet.

- 2026-06-17: Visual-candidate payload, model-declared observation event,
  fixture-hint request, and overlay artifact assembly moved from
  `RealWorldCleanupContract` into `realworld_visual_candidates.py`; stateful
  registration/navigation stayed in the contract facade. Metric:
  `realworld_contract.py` 4847 -> 4707 lines; ratchet remains 11 complexity
  rows and 66 oversized modules. Proof: realworld contract and MCP server
  contract tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Planner manipulation probe runtime diagnostics report panels
  moved from `report.py` into `report_sections_probe_runtime.py`, covering
  runtime modules, CUDA memory, CuRobo memory profile/cache, Warp
  compatibility, and worker-stage timeline sections. Metric: `report.py` 3806
  -> 3440 lines; ratchet remains 11 complexity rows and 66 oversized modules.
  Proof: cleanup report and planner manipulation checker contract tests, ruff,
  format check, py_compile, and ratchet.

- 2026-06-17: Planning-only ponytail / intuitive-refactor recheck refreshed
  the active cleanup plan without implementation. Metric: ratchet remains 11
  complexity rows and 66 oversized modules. Decision: next default slice is
  `report.py` non-runtime planner-probe panels; completed visual-candidate
  payload and planner-probe runtime-diagnostics slices stay closed; current
  `visual_grounding` schemas/service/artifact fields remain active internal
  contracts, while identity maps, legacy flags/aliases, and runner-private
  report aliases stay scoped small-cut inputs. Proof: ratchet summary, grep
  call-site checks, docs diff.

- 2026-06-17: Planner manipulation probe quality, views, cleanup-binding,
  task-sampler, post-placement rejection, grasp/placement failure, policy
  exception, blocker, artifact, and RBY1M/CuRobo gate report panels moved from
  `report.py` into `report_sections_probe.py` and
  `report_sections_probe_failures.py`. Metric: `report.py` 3440 -> 2525
  lines; ratchet remains 11 complexity rows and 66 oversized modules. Proof:
  cleanup report and planner manipulation checker contract tests, ruff, format
  check, py_compile, and ratchet.

- 2026-06-17: Robot-camera apple-to-apple Object Gate / Render Gate diagnostics
  moved from `run_robot_camera_apple2apple_comparison.py` into
  `robot_camera_apple2apple_object_gate.py`, and report-renderer tests now call
  `robot_camera_apple2apple_report.py` directly instead of runner-private
  aliases. Metric: runner 4900 -> 4573 lines; ratchet remains 11 complexity
  rows and 66 oversized modules. Proof: apple-to-apple unit tests, ruff, format
  check, py_compile, and ratchet.

- 2026-06-17: Planning-only intuitive-refactor recheck after the apple Object
  Gate slice refreshed the hard-ceiling candidate order without implementation.
  Metric: ratchet remains 11 complexity rows and 66 oversized modules.
  Decision: default next slice is `RealWorldCleanupContract` facade-private
  coupling reduction; `scene_camera_comparison.py` capture/projection/report
  diagnostics are the best candidate-B alternate; apple Object Gate / Render
  Gate and report aliases stay closed. Proof: ratchet summary, function-index
  scan, docs diff.

- 2026-06-17: Contract init map-projection and runtime-map-prior setup now call
  `realworld_contract_projection.py` and `realworld_runtime_map_contract.py`
  directly instead of routing through `realworld_contract.py` private aliases.
  Metric: `realworld_contract.py` 4707 -> 4656 lines; ratchet remains 11
  complexity rows and 66 oversized modules. Proof: realworld contract, MCP
  server, and cleanup-checker contract tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-17: Planning-only ponytail / intuitive-refactor recheck compacted
  the active cleanup plan and changed the default next slice to
  `scene_camera_comparison.py` HTML report-rendering ownership. Metric:
  ratchet remains 11 complexity rows and 66 oversized modules. Decision:
  preserve `render_scene_camera_comparison_report` and report HTML claims while
  moving report-only helpers to a report owner; keep contract facade, live
  runtime, B1 preview, behavior-test, MCP/prompt, guidance, and stale-surface
  items as alternates. Proof: ratchet summary, function-index scan,
  ponytail call-site grep, docs diff.

- 2026-06-17: Scene-camera HTML report rendering moved from
  `scene_camera_comparison.py` into report owner modules
  `scene_camera_report*.py`, while preserving the public
  `render_scene_camera_comparison_report` write entry point and report HTML
  contract. Metric: `scene_camera_comparison.py` 4693 -> 2830 lines; ratchet
  remains 11 complexity rows and 66 oversized modules. Proof: scene-camera
  contract tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Planning-only ponytail / intuitive-refactor recheck after the
  scene-camera report split found no new ratchet drift and updated only the
  cleanup plan. Decision: close the dirty scene-camera slice before starting
  candidate A; repo-local underscore imports inside `scene_camera_report*.py`
  are acceptable report-section internals; `visual_grounding` remains an
  active internal artifact/service contract; identity maps, `_task_prefix_legacy`,
  the legacy checker flag, and guidance wording stay small-cut inputs behind
  P1 hard-ceiling work. Proof: ratchet summary and call-site grep.

- 2026-06-17: Visual-candidate declaration orchestration moved from
  `realworld_contract.py` into `realworld_visual_candidate_declarations.py`,
  keeping the public `declare_visual_candidates` facade method as a thin
  delegate and leaving stateful registration/resolution internals for the next
  Candidate A sub-slice. Metric: `realworld_contract.py` 4656 -> 4410 lines,
  new declaration owner 345 lines, `realworld_visual_candidates.py` 627 lines;
  ratchet remains 11 complexity rows and 66 oversized modules. Proof:
  realworld contract and MCP server contract tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Visual-candidate registration/resolution lifecycle moved from
  `realworld_contract.py` into `realworld_visual_candidate_lifecycle.py`,
  covering normalization, match resolution, declaration payloads,
  resolved/unresolved detection materialization, visual-evidence error payloads,
  and handle actionability delegates. Metric: `realworld_contract.py` 4410 ->
  3888 lines, new lifecycle owner 737 lines, declaration owner 345 lines, and
  `realworld_visual_candidates.py` 627 lines; ratchet remains 11 complexity
  rows and 66 oversized modules. Proof: realworld contract and MCP server
  contract tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Robot-camera apple-to-apple capture-quality probe ownership
  moved from `run_robot_camera_apple2apple_comparison.py` into
  `robot_camera_apple2apple_capture_quality.py`, covering probe config,
  legacy-manifest inference, RGB-gain parsing, quality-setting rows, and Isaac
  render-settle argument translation. Tests now call the owner directly instead
  of runner-private helpers. Metric: runner 4573 -> 4357 lines, new owner 225
  lines; ratchet remains 11 complexity rows and 66 oversized modules. Proof:
  apple-to-apple unit tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Robot-camera apple-to-apple material/probe wrapper surface was
  deleted from `run_robot_camera_apple2apple_comparison.py`; runner logic now
  calls `robot_camera_apple2apple_materials.py` directly for material response,
  probe-summary primitives, and texture basename helpers, while the
  material-probe test calls the owner instead of the runner facade.
  Light/shadow and tone/color interpretation stayed in the runner because they
  still combine render-domain context. Metric: runner 4357 -> 4275 lines and
  no new owner module; ratchet remains 11 complexity rows and 66 oversized
  modules. Proof: focused apple-to-apple unit tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Robot-camera apple-to-apple native Isaac render diagnostics
  moved from `run_robot_camera_apple2apple_comparison.py` into
  `robot_camera_apple2apple_native_render.py`, covering native-diagnostics
  source selection, setting-group compaction, status interpretation, and summary
  payload assembly. The runner now attaches the owner output and keeps Object
  Gate compaction in `robot_camera_apple2apple_object_gate.py`. Metric: runner
  4275 -> 4161 lines, new owner 130 lines; ratchet remains 11 complexity rows
  and 66 oversized modules. Proof: focused apple-to-apple unit tests, ruff,
  format check, py_compile, and ratchet.

- 2026-06-17: Planning-only ponytail / intuitive-refactor recheck refreshed
  the cleanup plan after the material/probe and native-render slices. Metric:
  ratchet remains 11 complexity rows and 66 oversized modules; the apple runner
  is now 4161 lines and remains the largest production hard-ceiling file.
  Decision: continue Candidate B with apple image-metric artifact preparation
  and residual diagnostics as the default next slice, but first reuse existing
  `scene_camera_image_metrics.py` generic image math where practical so the
  slice removes duplicate concepts instead of creating another generic metric
  module. Proof: ratchet summary, function-index scan, image-metric call-site
  grep, docs diff.

- 2026-06-17: Robot-camera apple-to-apple saved/metric image artifact
  preparation, image-diff payload assembly, residual diagnostics, and residual
  triage moved from `run_robot_camera_apple2apple_comparison.py` into
  `robot_camera_apple2apple_image_metrics.py`, with generic pixel visual
  metrics reused from `scene_camera_image_metrics.py`. Tests now call the
  image-metric owner directly instead of runner-private image helpers. Metric:
  runner 4161 -> 3740 lines, new owner 484 lines; ratchet remains 11
  complexity rows and 66 oversized modules. Proof: focused apple-to-apple unit
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Done-readiness pending/held cleanup candidate derivation moved
  from `RealWorldCleanupContract` into `realworld_done_readiness.py`, including
  runtime public destination-option derivation. Contract-private
  `_pending_cleanup_candidates()`, `_held_cleanup_candidates()`, and
  `_destination_options_for_policy()` wrappers plus now-unused private aliases
  were deleted after call-site scan. Metric: `realworld_contract.py` 3888 ->
  3774 lines, owner module 276 -> 420 lines; ratchet remains 11 complexity rows
  and 66 oversized modules. Proof: focused realworld contract and MCP server
  contract tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Public manipulation/tool response envelope construction moved
  from `RealWorldCleanupContract` into `realworld_tool_responses.py`, covering
  fixture response ids, pick/place/open/close success/error envelopes, private
  backend error projection, and semantic-order error payloads. Contract methods
  keep sequencing and state mutation. Metric: `realworld_contract.py` 3774 ->
  3741 lines, new owner 129 lines; ratchet remains 11 complexity rows and 66
  oversized modules. Proof: focused realworld contract and MCP server contract
  tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: Camera-label producer declaration inputs moved from
  `RealWorldCleanupContract` into `realworld_visual_candidate_declarations.py`,
  covering simulated camera-model candidate rows, external visual-grounding
  request/failure envelopes, producer destination resolution, model-declared
  observation events, and direct registration calls into the lifecycle owner.
  Direct cleanup and MCP contract tests now call the declaration owner instead
  of contract-private declaration-input helpers. Metric:
  `realworld_contract.py` 3741 -> 3554 lines, declaration owner 345 -> 533
  lines; ratchet remains 11 complexity rows and 66 oversized modules. Proof:
  focused realworld contract and MCP server contract tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Runtime Metric Map target/public-anchor ownership moved from
  `RealWorldCleanupContract` into `realworld_runtime_map_targets.py`, covering
  target candidates, public semantic anchors, fixture-reference/anchor-id
  mapping, target-search summaries, minimal-map target-fixture resolution,
  waypoint anchor seeding, and runtime-anchor target resolution. Payload,
  done-readiness, visual-candidate, tool-response, and init callers now use the
  owner directly where they only need target/public-anchor data; the contract
  facade keeps state mutation and tool sequencing. Closeout also removed the
  now-unused target-owner `_recommended_place_tool` alias and
  `realworld_contract.py` `TARGET_SEARCH_SUMMARY_SCHEMA` constant. Metric:
  `realworld_contract.py` 3554 -> 2836 lines; new owner is 1009 lines, a
  justified cohesive module below the 1200-line warning ceiling; ratchet is 11
  complexity rows and 67 oversized modules. Proof: focused realworld contract,
  actionable-snapshot, and MCP server tests, ruff, format check, py_compile,
  and ratchet.

- 2026-06-17: Proof-bundle result rendering moved from `report.py` into
  `report_sections_proof_bundle.py`, covering proof result summaries,
  proof-quality summary rows, grasp-feasibility signature tables, individual
  proof result cards, view figures, and local artifact hrefs. The runner report
  now composes `proof_bundle_results_section()` from the proof-bundle owner
  instead of rebuilding the helper family inline. Metric: `report.py` 2525 ->
  2108 lines; proof-bundle owner is 828 lines, a justified cohesive module
  below the 1200-line warning ceiling; ratchet is 11 complexity rows and 68
  oversized modules. Proof: cleanup report contract tests, proof-bundle checker
  contract tests, proof-bundle runner script unit tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: Planning-only triage compacted the next P1 map after the
  proof-bundle dirty checkpoint. Ratchet remains 11 complexity rows and 68
  oversized modules; no ponytail dependency/std-lib deletion outranks the
  hard-ceiling frontier. Active P1 candidates now explicitly include the
  planner manipulation probe runner and the OpenAI Agents SDK live
  runtime/runner pair, alongside the existing contract/report and visual
  comparison families. Proof: ratchet summary and static call-site scan only;
  no code behavior changed in this triage row.

- 2026-06-17: Planner-probe runtime diagnostics moved from
  `run_molmo_planner_manipulation_probe.py` into
  `planner_probe_runtime_diagnostics.py`, covering runtime module/version
  discovery, torch/CUDA diagnostics, CUDA memory snapshots, CuRobo extension
  cache evidence, Warp compatibility and minimal `warp.torch` adapter, renderer
  device selection, headless renderer env setup, and renderer constructor
  patching. The runner keeps orchestration and worker event emission. Metric:
  planner probe runner 2948 -> 2510 lines; new owner is 474 lines; ratchet
  remains 11 complexity rows and 68 oversized modules. Proof: planner headless
  renderer unit tests, planner manipulation checker contract tests, ruff,
  format check, py_compile, diff check, and ratchet.

## Do Not Reopen Without Fresh Evidence

- Backend facade mainline already owns backend id/runtime metadata/artifact
  attachment; reopen only for new backend evidence leakage.
- Live checker and MCP/directed cleanup finalizers already have focused helper
  ownership; reopen only for schema drift or duplicated finalization logic.
- OpenAI live metrics/budget helpers already removed the known production
  complexity rows; file-size hard-ceiling work is still active, but the old
  metrics extraction slice is done.
- Report-performance skill calibration now shares the root calibration CLI;
  reopen only if skill/root calibration behavior diverges again.
- Scene sampler is below the hard ceiling and delegates candidate profile,
  source-prep, prefilter, and scanner-admission internals to named owner
  modules; reopen only for fresh hard-ceiling or ownership drift.
- Runtime Metric Map payload assembly is owned by
  `realworld_runtime_map_contract.py`; reopen only if the realworld contract
  facade starts rebuilding observed-object or static-map payload internals.
- Runtime-map prior setup and init-time projection helpers no longer route
  through `realworld_contract.py` private aliases; reopen only if contract init
  or another owner starts using the facade as a compatibility helper bag again.
- Visual-candidate payload/event/overlay assembly is owned by
  `realworld_visual_candidates.py`; reopen only if the realworld contract
  facade starts rebuilding visual-grounding candidate payloads or overlay
  artifact paths directly.
- Visual-candidate declaration orchestration is owned by
  `realworld_visual_candidate_declarations.py`; reopen only if the realworld
  contract facade starts rebuilding declaration inputs, invalid-candidate
  responses, camera-label producer failure responses, or model-declared
  observation response packets directly.
- Camera-label producer declaration inputs are owned by
  `realworld_visual_candidate_declarations.py`; reopen only if the realworld
  contract facade starts rebuilding simulated declaration input rows,
  visual-grounding requests, producer failure envelopes, model-declared
  observation events, or registration wrapper aliases directly.
- Visual-candidate registration/resolution lifecycle is owned by
  `realworld_visual_candidate_lifecycle.py`; reopen only if the realworld
  contract facade starts rebuilding normalization, match resolution,
  declaration payloads, resolved/unresolved detection materialization,
  visual-evidence error payloads, or handle actionability directly.
- Planner manipulation probe runtime diagnostics report panels are owned by
  `report_sections_probe_runtime.py`; reopen only if `report.py` starts
  rebuilding Runtime Diagnostics, CUDA Memory, CuRobo Memory/Profile/Cache,
  Warp Compatibility, or Worker Stage Timeline sections directly.
- Planner manipulation probe non-runtime report panels are owned by
  `report_sections_probe.py` and `report_sections_probe_failures.py`; reopen
  only if `report.py` starts rebuilding quality, views, cleanup-binding,
  task-sampler, post-placement rejection, grasp collision, placement scene,
  policy exception, blocker, artifact, or RBY1M/CuRobo gate sections directly.
- Robot-camera apple-to-apple Object Gate / Render Gate diagnostics are owned
  by `robot_camera_apple2apple_object_gate.py`; reopen only if
  `run_robot_camera_apple2apple_comparison.py` starts rebuilding object gate
  records, object/render parity diagnostic packets, compact diagnostic packets,
  skipped object-gate packets, or runner-private `_render_*` report aliases.
- Robot-camera apple-to-apple capture-quality probe construction is owned by
  `robot_camera_apple2apple_capture_quality.py`; reopen only if the runner
  starts rebuilding probe config, inferred legacy manifests, RGB-gain parsing,
  quality-setting rows, or Isaac render-settle argument translation directly.
- Robot-camera apple-to-apple material/probe helper primitives are owned by
  `robot_camera_apple2apple_materials.py`; reopen only if the runner recreates
  private delegates for material response checks, material/tone probe history
  primitives, preview-surface summaries, texture material summaries, or texture
  basename helpers.
- Robot-camera apple-to-apple native Isaac render diagnostics are owned by
  `robot_camera_apple2apple_native_render.py`; reopen only if the runner
  rebuilds native-diagnostics source selection, setting-group compaction,
  native-status interpretation, or native summary payloads directly.
- Robot-camera apple-to-apple image metric artifacts and residual diagnostics
  are owned by `robot_camera_apple2apple_image_metrics.py`; reopen only if the
  runner rebuilds saved-report image derivation, metric-image paths,
  image-diff payloads, residual diagnostic math, or residual triage summaries
  directly.
- Done-readiness pending/held cleanup candidates and runtime public
  destination options are owned by `realworld_done_readiness.py`; reopen only
  if `realworld_contract.py` starts rebuilding pending candidates, held
  candidates, destination options, or wrapper aliases directly.
- Public manipulation/tool response envelopes are owned by
  `realworld_tool_responses.py`; reopen only if `realworld_contract.py` starts
  rebuilding fixture response ids, pick/place/open/close success/error payloads,
  private backend error projection, or semantic-order error payloads inline.
- Runtime Metric Map target/public-anchor construction is owned by
  `realworld_runtime_map_targets.py`; reopen only if `realworld_contract.py` or
  adjacent callers start rebuilding target candidates, public semantic anchors,
  fixture-reference or anchor-id mapping, target-search summaries, minimal-map
  target-fixture resolution, waypoint anchor seeding, or runtime-anchor target
  resolution directly.
- Proof-bundle result rendering is owned by `report_sections_proof_bundle.py`;
  reopen only if `report.py` starts rebuilding proof-bundle result summaries,
  proof-quality summary rows, grasp-feasibility signature tables, proof result
  cards, or proof-result view figures directly.
- Planner-probe runtime diagnostics are owned by
  `planner_probe_runtime_diagnostics.py`; reopen only if
  `run_molmo_planner_manipulation_probe.py` starts rebuilding runtime
  module/version packets, torch/CUDA diagnostics, CUDA snapshot math, CuRobo
  extension-cache evidence, Warp adapter diagnostics, or headless renderer
  adapter setup directly.
- Robot-camera apple-to-apple object parity audit construction is owned by
  `robot_camera_apple2apple_object_parity.py`, selected RGB/focus evidence is
  owned by `robot_camera_apple2apple_rgb_evidence.py`, and visual-state
  contract evidence plus visual-physics-sensitive target selection are owned by
  `robot_camera_apple2apple_visual_state.py`. Metric: apple runner 3740 ->
  2394 lines; new owners are 689, 402, and 337 lines; staged/add-N ratchet
  still reports 11 complexity rows and 66 oversized modules. Proof: focused
  apple comparison tests, ruff, format check, py_compile, and ratchet. Reopen
  only if the runner rebuilds object/receptacle audit rows, compact/skipped
  audit packets, selected RGB/focus evidence, visual-state contracts,
  semantic-pose index fallback, or category summaries directly.
- Scene-camera USD render-contract parsing, image metrics, native render
  diagnostics, lighting/tone/shadow diagnostics, render-domain calibration,
  and render source references are owned by their focused scene-camera modules;
  report rendering is owned by `scene_camera_report*.py`. Reopen scene-camera
  report rendering only if `scene_camera_comparison.py` starts rebuilding
  report sections directly again.
- B1 runtime-bundle review-manifest validation is split into focused helper
  families; reopen only if `review_manifest_errors` regains ratchet rows or
  false-green review-gate behavior.
- B1 label-tool layer construction and draft-manifest validation are split
  into focused helper families; reopen only if label-tool packet or error
  contracts drift.
- Completed report-section extraction is partial evidence, not a reason to
  treat `report.py` as done; the active plan still owns the hard-ceiling split.

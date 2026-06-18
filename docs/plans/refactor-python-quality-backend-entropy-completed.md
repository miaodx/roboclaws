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

- 2026-06-18: Isaac worker render command numeric configuration now fails
  aloud. The worker CLI rejects non-positive snapshot/robot-view/camera-view
  render dimensions and negative robot-view settle frames at argument parsing
  time instead of allowing invalid dimensions through or clamping settle frames
  to zero in the output hooks. Owner layer: Backend Runtime / Environment
  Primitive. Behavior-change class: fail-aloud Isaac worker render
  configuration; default dimensions, valid positive dimensions,
  zero-as-no-extra-settle behavior, worker command names, output packet schemas,
  placeholder/real-render routing, and higher-level backend argv construction
  are unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `isaac_worker_cli.py` is 269 lines,
  `isaac_worker_outputs.py` is 429 lines, and
  `test_relative_navigation_worker_routing.py` is 247 lines. Proof: focused
  worker-routing tests, `test_isaac_lab_backend.py`, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 / Map 12 navigation-smoke render dimensions now fail aloud.
  The navigation-smoke CLI rejects non-positive `--render-width` /
  `--render-height` values at argument parsing time instead of passing invalid
  dimensions into waypoint capture requests and child render subprocesses.
  Owner layer: Backend Runtime / Environment Primitive. Behavior-change class:
  fail-aloud B1 navigation-smoke render configuration; default dimensions,
  valid positive dimensions, readiness artifact loading/building, waypoint
  selection, smoke artifact schema, and child capture command routing are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `run_b1_map12_navigation_smoke.py` is 342 lines and
  `test_b1_map12_navigation_report.py` is 98 lines. Proof: focused B1
  navigation-smoke contract tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Robot-camera apple-to-apple comparison target count now fails
  aloud. The comparison CLI rejects non-positive `--location-count` at argument
  parsing time instead of clamping zero or negative values to one target before
  selecting render comparison locations. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud comparison artifact
  configuration; default target count, valid positive counts,
  refresh-report-only behavior, target selection ordering, manifest/report
  schemas, and renderer subprocess routing are unchanged. Metric: ratchet
  remains at 0 complexity rows and 79 oversized modules;
  `run_robot_camera_apple2apple_comparison.py` is 1813 lines and
  `test_robot_camera_apple2apple_comparison.py` is 2986 lines. The test file is
  already oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused robot-camera apple-to-apple unit tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Robot-camera apple-to-apple comparison render dimensions now fail
  aloud. The comparison CLI rejects non-positive `--render-width` /
  `--render-height` values at argument parsing time instead of passing invalid
  dimensions into MuJoCo and Isaac render subprocesses. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  comparison render configuration; default dimensions, valid positive
  dimensions, `--refresh-report-only` behavior, target-count validation,
  manifest/report schemas, and renderer subprocess routing are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `run_robot_camera_apple2apple_comparison.py` is 1813 lines and
  `test_robot_camera_apple2apple_comparison.py` is 3043 lines. The test file
  is already oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused robot-camera apple-to-apple unit tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Robot-camera apple-to-apple capture-quality settle frames now
  fail aloud. The comparison CLI rejects negative `--render-settle-frames` at
  argument parsing time instead of clamping it to zero in capture-quality
  configuration. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud comparison capture-quality configuration;
  default zero settle frames, explicit zero-as-no-extra-settle behavior,
  positive settle-frame forwarding, render dimensions, target-count validation,
  manifest/report schemas, and renderer subprocess routing are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `run_robot_camera_apple2apple_comparison.py` is 1825 lines,
  `robot_camera_apple2apple_capture_quality.py` is 226 lines, and
  `test_robot_camera_apple2apple_comparison.py` is 3097 lines. The test file
  is already oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused robot-camera apple-to-apple unit tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Scene-camera comparison render dimensions now fail aloud. The
  scene-camera comparison CLI rejects non-positive `--render-width` /
  `--render-height` values at argument parsing time instead of passing invalid
  dimensions into the shared MuJoCo and Isaac scene-camera comparison artifact
  pipeline. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud scene-camera comparison render
  configuration; default dimensions, valid positive dimensions,
  prepared-USD checks, generated-mess inputs, lighting-profile selection,
  manifest/report schemas, and renderer routing are unchanged. Metric: ratchet
  remains at 0 complexity rows and 79 oversized modules;
  `scene_camera_comparison.py` is 2011 lines and
  `test_scene_camera_comparison.py` is 2085 lines. The test file is already
  oversized; leave pruning/splitting for an `$intuitive-tests` pass. Proof:
  focused scene-camera comparison contract tests, touched-file ruff and format
  check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 scene topdown and operator preview render dimensions now fail
  aloud. The Gaussian topdown, scene topdown diagnostic, and operator-console
  scene preview CLIs reject non-positive `--width` / `--height` values at
  argument parsing time instead of clamping them to one pixel and emitting
  plausible but unusable review artifacts. Owner layers: Artifacts, reports,
  and eval suites; operator console preview artifacts. Behavior-change class:
  fail-aloud render artifact configuration; default dimensions, valid positive
  dimensions, camera request/report schemas, B1 static preview behavior,
  MolmoSpaces preview routing, and rendered artifact names are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `render_b1_scene_gaussian_topdown.py` is 539 lines,
  `render_b1_scene_topdown_diagnostic.py` is 877 lines, and
  `render_scene_previews.py` is 1387 lines. Proof: targeted B1 topdown and
  operator preview tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: RAW-FPV perception probe numeric configuration now fails
  aloud. The probe CLI rejects non-positive `max_frames_per_source`,
  non-positive score thresholds, out-of-contract candidate limits, and
  non-positive/non-finite provider timeouts at argument parsing time instead of
  clamping invalid values before collecting frames, building prompt inputs, or
  scoring reports. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud perception probe configuration; defaults,
  valid candidate limits from one to three, prompt/report schemas, public
  prompt privacy boundaries, offline scoring, and provider execution flow are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `run_raw_fpv_perception_probe.py` is 1873 lines and
  `test_raw_fpv_perception_probe.py` is 1295 lines. Focused regression tests
  grow the existing RAW-FPV test file; leave test pruning/splitting for an
  `$intuitive-tests` pass. Proof: focused RAW-FPV probe parser/unit tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: RAW-FPV corpus generator numeric configuration now fails aloud.
  Private-label and public-sweep corpus CLIs reject non-positive render
  dimensions, non-positive `min_object_pixels`, and negative observation /
  waypoint limits at argument parsing time instead of clamping invalid values to
  one and generating plausible but misconfigured scorer artifacts. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud corpus
  generation configuration; default values, valid positive dimensions,
  zero-as-unlimited observation/waypoint limits, privacy boundaries,
  manifest/report schemas, and replay/corpus generation flow are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `generate_raw_fpv_private_labels.py` is 798 lines and
  `generate_raw_fpv_sweep_corpus.py` is 559 lines. Focused regression tests grow
  `test_raw_fpv_perception_probe.py` to 1254 lines; leave test pruning for an
  `$intuitive-tests` pass. Proof: focused RAW-FPV parser/unit tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: MolmoSpaces JSON worker numeric command kwargs now fail aloud.
  Served worker requests reject malformed, boolean, non-finite, or non-positive
  render dimensions and malformed, boolean, or non-finite camera/relative-motion
  floats instead of silently substituting default dimensions or zero motion
  before rendering or navigation. Owner layer: Backend Runtime / Environment
  Primitive. Behavior-change class: fail-aloud worker command configuration;
  omitted worker kwargs, CLI-parsed numeric args, valid numeric strings, render
  output shape, relative-pose dispatch, worker response/error packet structure,
  public launch axes, and backend wrapper commands are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules;
  `molmospaces_subprocess_worker.py` is 1880 lines and remains below the hard
  ceiling. Proof: focused MolmoSpaces worker routing tests, adjacent subprocess
  backend CLI/render tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Provider timing proxy bind-port configuration now fails aloud.
  `start_provider_timing_proxy()` and the direct proxy CLI reject malformed or
  out-of-range `ROBOCLAWS_TIMING_PROXY_BIND_PORT` / `--bind-port` values instead
  of treating invalid env as omitted and silently choosing a free local port.
  Owner layer: Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud live-agent timing-proxy configuration; omitted bind-port values,
  valid explicit ports, free-port selection, loopback host validation, provider
  URL rewriting, request metric schemas, and live-runner proxy metadata are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `provider_timing_proxy.py` is 493 lines. Proof: focused provider
  timing proxy tests, focused live-runner provider-proxy tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Launch-catalog blank-axis selection now fails aloud.
  `resolve_surface_launch()` rejects explicit blank optional axes for `world=`,
  `backend=`, `intent=`, `preset=`, and `provider_profile=` instead of treating
  them as omitted and silently selecting defaults. Owner layers: Runnable
  Surfaces And Presets, and Agent Engines And Provider Profiles. Behavior-change
  class: fail-aloud launch-axis configuration; omitted axes, valid axis values
  and aliases, unsupported non-empty provider profile errors, public launch
  axes, provider env export, and runner argv construction are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules; `catalog.py` is
  716 lines. Proof: focused launch-catalog blank-axis/provider-profile tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: OpenAI Agents SDK direct provider/model/env precedence now fails
  aloud. Provider profile, model, base URL, and API key selection for the direct
  SDK runtime rejects conflicting explicit request/metadata and env settings
  instead of silently letting one source retarget the route. The conflict policy
  lives in `provider_registry.py`, while `openai_agents_live.py` only applies
  selected runtime settings and missing-setting checks. Owner layer: Agent
  Engines And Provider Profiles. Behavior-change class: fail-aloud OpenAI
  Agents SDK provider/model/env configuration; omitted defaults, matching
  env/request values, canonical provider/model aliases, base-url trailing-slash
  normalization, public launch axes, normalized live-status packets, and event
  schemas are unchanged. Metric: ratchet remains at 0 complexity rows and 79
  oversized modules; `openai_agents_live.py` is 1911 lines and
  `provider_registry.py` is 989 lines. Proof: focused OpenAI Agents live runtime
  and provider catalog tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK model-racing observability numeric config now
  fails aloud. Direct `model_racing_observability.arm_count` and
  `model_racing_observability.racing_multiplier` metadata reject malformed,
  boolean, non-positive, or non-finite values instead of silently clamping
  `arm_count` to the default or surfacing raw float conversion failures.
  Behavior-change class: fail-aloud OpenAI Agents SDK numeric/profile
  configuration; omitted values, empty-string defaults, profile-owned
  model-racing packets, public launch axes, normalized live-status packets, and
  event schemas are unchanged. Metric: ratchet remains at 0 complexity rows and
  79 oversized modules; `openai_agents_live.py` is 1943 lines. Proof: focused
  OpenAI Agents model-racing runtime tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK model-racing observability boolean config now
  fails aloud. Direct `model_racing_observability.enabled` and
  `model_racing_observability.unknown_loser_billing` metadata accept only
  explicit true/false spellings instead of treating arbitrary non-false strings
  as enabled. Behavior-change class: fail-aloud OpenAI Agents SDK
  boolean/profile configuration; omitted values, empty-string defaults, valid
  true/false values, profile-owned model-racing packets, public launch axes,
  normalized live-status packets, and event schemas are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules;
  `openai_agents_live.py` is 1899 lines. Proof: focused OpenAI Agents
  model-racing/cache-tools runtime tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK model-input compaction boolean config now fails
  aloud. Direct `model_input_compaction.enabled`,
  `raw_fpv_image_memory.enabled`, and `camera_grounded_history.enabled`
  metadata accept only explicit true/false spellings instead of treating
  arbitrary non-false strings as enabled. Behavior-change class: fail-aloud
  OpenAI Agents SDK boolean/profile configuration; omitted values,
  empty-string defaults, valid true/false values, profile-owned compaction
  packets, public launch axes, normalized live-status packets, and event schemas
  are unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `openai_agents_model_input.py` stays at 990 lines. Proof: focused
  OpenAI Agents model-input compaction runtime tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK cache-tools-list boolean config now fails
  aloud. Direct runtime metadata, `ROBOCLAWS_OPENAI_AGENTS_CACHE_TOOLS_LIST`,
  and performance-profile resolution accept only explicit true/false spellings
  instead of treating arbitrary non-false strings as enabled. Behavior-change
  class: fail-aloud OpenAI Agents SDK boolean/profile configuration; omitted
  values, default enabled behavior, valid true/false values, matching CLI/env
  values, provider profiles, public launch axes, normalized live-status packets,
  and event schemas are unchanged. Metric: ratchet remains at 0 complexity rows
  and 79 oversized modules; `openai_agents_perf_profile.py` is 796 lines,
  `openai_agents_live.py` is 1887 lines, and
  `run_live_openai_agents_cleanup.py` is 1974 lines. Proof: focused OpenAI
  Agents live runtime/profile tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Visual-grounding benchmark timeout configuration now fails aloud.
  `run_visual_grounding_benchmark.py` validates `--timeout-s` and
  `VISUAL_GROUNDING_TIMEOUT_S` as positive finite seconds during argument
  parsing instead of accepting zero/non-finite values or surfacing raw float
  conversion failures before benchmark setup. Behavior-change class: fail-aloud
  visual-grounding benchmark configuration; default timeout, valid CLI/env
  overrides, visual-grounding client config shape, benchmark result/report
  schemas, public launch axes, and sidecar service behavior are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `scripts/visual_grounding/run_visual_grounding_benchmark.py` is 1278 lines.
  Proof: focused visual-grounding benchmark contract tests, touched-file ruff
  and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Visual-grounding sidecar adapter-mode env configuration now
  fails aloud. `serve_visual_grounding_service.py` validates
  `VISUAL_GROUNDING_ADAPTER_MODE` against `auto`, `real`, and `unavailable`
  before listing adapters or starting the service, instead of allowing an
  unsupported env default to bypass the CLI choices. Behavior-change class:
  fail-aloud visual-grounding sidecar service configuration; valid CLI/env
  values, list-adapter output, service startup with supported modes, sidecar
  request/response schemas, public launch axes, and benchmark behavior are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `scripts/visual_grounding/serve_visual_grounding_service.py` is 170
  lines. Proof: focused visual-grounding service contract tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Shared worker timeout env overrides now fail aloud.
  `worker_timeout_s()` rejects malformed, non-finite, or non-positive
  `ROBOCLAWS_MOLMOSPACES_WORKER_TIMEOUT_S` /
  `ROBOCLAWS_ISAACLAB_WORKER_TIMEOUT_S` style overrides before subprocess
  launch instead of surfacing raw float conversion failures or passing invalid
  timeout values to the runner. Behavior-change class: fail-aloud worker
  runtime configuration; absent env overrides, valid positive overrides,
  command-specific timeout defaults, MolmoSpaces/Isaac worker commands, public
  launch axes, and worker response schemas are unchanged. Metric: ratchet
  remains at 0 complexity rows and 79 oversized modules; `worker_runner.py` is
  130 lines. Proof: focused worker-runner unit tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Codex live-runner idle-timeout env overrides now fail aloud.
  `_codex_turn_idle_timeout_s()` rejects malformed, non-finite, or negative
  `ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S` values instead of silently reusing the
  300s default. Behavior-change class: fail-aloud live-agent runner
  configuration; omitted env values, explicit configured timeout metadata,
  valid non-negative env values including zero as disable, Codex live-run
  commands, public launch axes, live-status packets, and report artifacts are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `run_live_codex_cleanup.py` is 1250 lines. Proof: focused Codex
  live-report unit test, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Live-eval timeout-completion-grace env overrides now fail aloud.
  `live_timeout_completion_grace_s()` rejects malformed, non-finite, or
  negative `ROBOCLAWS_LIVE_EVAL_TIMEOUT_COMPLETION_GRACE_S` values instead of
  silently reusing the 30s default. Behavior-change class: fail-aloud eval
  runner configuration; omitted env values, valid non-negative grace overrides
  including zero, detached live-run polling, `live_eval_command.json` records,
  public launch axes, live-status packets, and product artifacts are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `live_runtime.py` is 728 lines. Proof: focused eval live-runtime unit tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: Visual-grounding real sidecar runtime-parameter parsing now fails
  aloud. Explicit request/runtime and env knobs for Grounding DINO, YOLO,
  OmDet-Turbo, and sidecar candidate limits reject malformed,
  boolean-as-number, non-finite, or out-of-range values with an
  `invalid_runtime_parameter` failure packet instead of silently falling back to
  env or adapter defaults. Behavior-change class: fail-aloud visual-grounding
  sidecar runtime configuration; valid defaults, valid request/env overrides,
  adapter-unavailable responses, missing-dependency responses, visual-grounding
  request/response schemas, public launch axes, and benchmark row construction
  are unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `scripts/visual_grounding/adapters.py` is 1914 lines. Proof: focused
  visual-grounding service, client, and benchmark contract tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK performance-profile integer parsing now uses
  the same fail-aloud setting style as the runtime config paths. Malformed
  integer env/direct settings such as
  `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET`, and non-positive
  positive-only settings such as `max_turns`, produce actionable
  `OpenAI Agents SDK setting ...` errors instead of raw conversion failures or
  terse constraint messages. Behavior-change class: fail-aloud
  runner/provider-profile configuration; valid integer defaults, matching
  CLI/env values, existing conflicts, and profile output schemas are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `openai_agents_perf_profile.py` is 800 lines and stays below the oversized
  threshold. Proof: focused OpenAI Agents live runtime/profile tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: Metric-map rasterization now fails aloud when declared
  projection dimensions are absent or malformed. `occupancy_grid_from_metric_map()`
  requires `metric_map.width` and `metric_map.height` to be present, integer,
  and within the existing 16..4096 bounds instead of silently fabricating the
  default 240x180 grid for invalid map evidence. Behavior-change class:
  fail-aloud source-map/costmap projection; valid metric-map projection, public
  launch axes, Nav2 bundle artifact schemas, and computed geometry expansion
  clamping are unchanged. Metric: ratchet remains at 0 complexity rows and 79
  oversized modules; `rasterize.py` is 268 lines. Proof: focused Nav2
  map-bundle contract tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Runtime Map Prior artifact loading now rejects malformed
  non-empty prior payloads. `runtime_metric_map_from_prior_artifact()` accepts
  only raw `runtime_metric_map_v1` payloads or `runtime_map_prior_snapshot_v1`
  wrappers whose nested runtime map is also `runtime_metric_map_v1`; unknown
  prior artifact schemas fail with a clear schema error instead of being treated
  as usable runtime-map evidence. Behavior-change class: fail-aloud runtime
  artifact/source truth; omitted prior paths, valid raw runtime maps, valid
  snapshot wrappers, public launch axes, and downstream Runtime Map Prior
  Snapshot contracts are unchanged. Metric: ratchet remains at 0 complexity rows
  and 79 oversized modules; `runtime_prior_snapshot.py` is 844 lines and remains
  a justified warning-band owner. Proof: focused Runtime Map Prior contract
  tests, touched-file ruff and format check, py_compile, `git diff --check`,
  and ratchet.

- 2026-06-18: External visual-grounding timeout configuration now fails aloud.
  `visual_grounding_client_from_env()` rejects malformed, non-finite, or
  non-positive `VISUAL_GROUNDING_TIMEOUT_S` / direct
  `visual_grounding_timeout_s` values instead of silently reusing the 20s
  default for non-sim sidecar routes. Behavior-change class: fail-aloud
  external sidecar configuration; the `sim` no-client path, omitted timeout
  default, valid positive timeout values, visual-grounding request/response
  schemas, and public launch axes are unchanged. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules; `visual_grounding.py` is 414 lines.
  Proof: focused visual-grounding client tests, touched-file ruff and format
  check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: External visual-grounding sidecar calls now require raw image
  evidence. Non-sim camera labelers report a failed `missing_raw_fpv_image`
  visual-grounding pipeline before invoking the sidecar when the raw FPV image
  artifact is absent or unreadable, instead of sending an empty image payload to
  the detector. Behavior-change class: fail-aloud runtime evidence/source truth;
  sim camera-model declarations, missing-client status, valid image-backed
  sidecar requests, visual-grounding schemas, and public launch axes are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `realworld_visual_candidate_declarations.py` is 570 lines. Proof:
  focused RealWorldCleanupContract visual-grounding tests, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Visual-grounding HTTP request validation now rejects empty image
  evidence. `validate_visual_grounding_request()` requires non-empty
  `image.bytes_base64` plus positive `image.width` / `image.height` values
  instead of allowing zero-sized image payloads through the sidecar boundary.
  Behavior-change class: fail-aloud visual-grounding contract validation; valid
  image-backed requests, response schema validation, sim camera-model
  declarations, missing-client status, public launch axes, and upstream
  `missing_raw_fpv_image` classification are unchanged. Metric: ratchet remains
  at 0 complexity rows and 79 oversized modules; `visual_grounding_contract.py`
  is 183 lines. Proof: focused visual-grounding client and service contract
  tests, touched-file ruff and format check, py_compile, `git diff --check`,
  and ratchet.

- 2026-06-18: OpenAI Agents SDK runner-side MCP client-session timeout
  default/env validation moved into `openai_agents_perf_profile.py`. Malformed
  `ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S`, negative direct
  timeout values, and CLI/env timeout conflicts now fail through the same
  performance-profile resolver as the other SDK runtime settings instead of
  being parsed early by argparse or silently clamped to zero. Behavior-change
  class: fail-aloud runner/provider-profile configuration; default 30s timeout,
  matching CLI/env values, valid positive values, and explicit zero-as-disable
  profile output are unchanged. Metric: ratchet remains at 0 complexity rows and
  79 oversized modules; `run_live_openai_agents_cleanup.py` is down to 1972
  lines. Proof: focused OpenAI Agents live runtime/profile tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK direct `max_turns` metadata now fails aloud for
  malformed runtime settings. Invalid or non-positive direct `max_turns`
  metadata produces normalized `provider_config_failure` live-status packets
  instead of silently reusing the default SDK turn budget or clamping to one.
  Behavior-change class: fail-aloud SDK runtime configuration; omitted
  metadata, validated `LiveAgentRequest.max_turns`, and positive profile-owned
  `max_turns` values are unchanged. Metric: ratchet remains at 0 complexity
  rows and 79 oversized modules. Proof: focused OpenAI Agents live runtime
  tests, touched-file ruff and format check, py_compile, `git diff --check`,
  and ratchet.

- 2026-06-18: OpenAI Agents SDK MCP client-session timeout config now fails
  aloud for malformed runtime settings. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S` values and negative
  direct `mcp_client_session_timeout_s` metadata produce normalized
  `provider_config_failure` live-status packets instead of being treated as
  absent or disabled timeout configuration. Behavior-change class: fail-aloud
  SDK runtime configuration; omitted values, valid positive timeout values, and
  explicit zero-as-disable behavior are unchanged. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules. Proof: focused OpenAI Agents live
  runtime tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: OpenAI Agents SDK retry config now fails aloud for malformed
  numeric runtime settings. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_MODEL_SERVICE_RETRY_ATTEMPTS` values and invalid
  direct `model_service_retry_sleep_s` metadata produce normalized
  `provider_config_failure` live-status packets instead of silently reusing
  defaults. Behavior-change class: fail-aloud SDK runtime configuration;
  omitted values, valid non-negative retry attempts/sleep values,
  profile-owned retry packets, public launch axes, event schemas, and retry
  observability are unchanged. Metric: ratchet remains at 0 complexity rows and
  79 oversized modules. Proof: focused OpenAI Agents live runtime tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: OpenAI Agents SDK model-input compaction config now fails aloud for
  malformed numeric runtime settings. Invalid
  `ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS` values and invalid direct
  `raw_fpv_image_memory.retained_full_frame_limit` /
  `camera_grounded_history.retained_recent_outputs` metadata produce normalized
  `provider_config_failure` live-status packets instead of silently reusing
  defaults or passing malformed direct policies through to the filter. Behavior-
  change class: fail-aloud SDK runtime configuration; omitted values, valid
  defaults, profile-owned compaction packets, public launch axes, event schemas,
  and valid compaction output are unchanged. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules. Proof: focused OpenAI Agents live
  runtime tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Active-plan Candidate D guidance now matches the closed code and
  completed-ledger state. Stale prompts that still made runner-side OpenAI
  Agents SDK performance-profile/default extraction the next Candidate D slice
  now point to `openai_agents_perf_profile.py` as the owner and say to reopen
  only if the runner starts rebuilding profile/default/config packets inline
  again. Behavior-change class: planning/ledger consistency only; no runtime,
  artifact, profile, or test behavior changed. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules. Proof: focused call-site scan,
  active-plan stale-guidance scan, markdown diff review, and ratchet.

- 2026-06-18: Operator-console runtime artifact discovery now fails honest for
  grounding overlays. `_latest_view_assets()` only treats
  `visual_grounding/overlays/**` images as current grounding overlays;
  report-only `*.bbox*`, `*.detection*`, or loose `*grounding*` images elsewhere
  in the run directory no longer replace the FPV slot or appear as live
  grounding evidence. Behavior-change class: fail-aloud runtime artifact/status
  honesty; real visual-grounding overlays still surface as both `grounding` and
  FPV display source, while report-rendered bbox evidence remains available
  through report artifacts. Metric: ratchet remains at 0 complexity rows and 79
  oversized modules. Proof: focused operator-console state tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Nav2 map-bundle projection now fails aloud before emitting
  projected map evidence from invalid source bundles. `metric_map_from_bundle()`
  and `static_fixture_projection_from_bundle()` call the existing Nav2 bundle
  validator first, so missing `map.yaml` image metadata, missing inspection
  waypoints, missing source-frame metadata, or other bundle-validation errors
  no longer become `ok=true` projected artifacts through direct callers.
  Behavior-change class: fail-aloud source-map artifact projection; valid bundle
  projection, public launch axes, artifact schemas, map report shape, and
  product callers that already validate selected bundles are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules. Proof: focused
  Nav2 map-bundle contract tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: MiMo inside provider readiness now requires the base URL as well
  as the API key. `mimo-inside-openai-chat` declares both `MIMO_BASE_URL` and
  `MIMO_API_KEY` as required env keys, matching its no-default-base-url
  provider contract. Provider readiness and operator-console readiness now
  block when only `MIMO_API_KEY` is present instead of reporting the on-demand
  route startable with an empty base URL. Behavior-change class: fail-aloud
  provider readiness; provider profile ids, route default model, public launch
  axes, and documented operator setup are unchanged. Metric: ratchet remains at
  0 complexity rows and 79 oversized modules. Proof: focused provider catalog
  and operator-console provider/readiness tests, touched-file ruff and format
  check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Coding-agent shell helpers now fail aloud for explicit unknown
  model overrides before launch config generation. `provider_registry.py`
  exposes a `model-id` lookup command, and `scripts/dev/coding_agent_env.sh`
  resolves `ROBOCLAWS_CODEX_MODEL` / `ROBOCLAWS_CODE_AGENT_MODEL` through the
  catalog for non-system provider routes. Known aliases such as
  `minimax-highspeed` still normalize to their catalog model id; omitted model
  input still uses route defaults. Behavior-change class: fail-aloud env
  cleanup; provider profiles, route defaults, system Claude behavior,
  key/base-url precedence, and public launch axes are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules. Proof:
  focused provider catalog and dev-tool shell helper tests, touched-file ruff
  and format check, `bash -n`, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Provider readiness now fails aloud for explicit unknown model
  overrides. `provider_readiness()` no longer reports `ok=true` with
  `model_family=unknown` when required provider env vars are present; unknown
  model ids produce an actionable readiness message while omitted model input
  still uses the route's documented default model. Behavior-change class:
  fail-aloud provider readiness only; provider profiles, route defaults, model
  aliases, launch args, and base-url/key precedence are unchanged. Metric:
  ratchet remains at 0 complexity rows and 79 oversized modules. Proof:
  focused provider catalog and operator-console provider/readiness tests,
  touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: Operator-console provider/evidence-lane compatibility lookup
  drift now fails aloud during readiness. `_with_evidence_lane_compatibility()`
  no longer swallows `KeyError` / `ValueError`; lookup failures mark the
  provider packet `ok=false` and block start through the existing
  `needs_provider` gate with the agent engine, provider profile, evidence lane,
  and lookup error visible to the operator. Behavior-change class: fail-aloud
  readiness only; provider route semantics, launch args, model defaults, and
  supported evidence-lane policy are unchanged. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules. Proof: focused operator-console
  provider/readiness tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Real-world contract public map/projection construction moved from
  `realworld_contract.py` to `realworld_contract_projection.py`; top-level
  agent-view/policy evidence, visible-detection sanitization, camera-model
  policy summaries, model-declared observation evidence, raw-FPV observations,
  and inspection-observation packets moved to `realworld_contract_payloads.py`;
  visible/camera candidate materialization, generated inspection waypoint
  creation, and `navigate_to_visual_candidate()` response assembly moved to
  `realworld_visual_candidate_lifecycle.py`. Dead facade aliases for
  already-owned helpers were removed instead of preserved as compatibility
  shims. Behavior-change class: internal owner split; public tool names,
  agent-view/runtime-map schemas, visual-candidate navigation responses, and
  private-truth guards are unchanged. Metric: `realworld_contract.py` is 1989
  lines, projection is 1074 lines, payloads are 703 lines, lifecycle is 1188
  lines, and the ratchet reports 0 complexity rows and 79 oversized modules.
  Proof: focused real-world contract/MCP/runtime-map-prior contract tests,
  touched-file ruff and format check, py_compile for all tracked Python files,
  `git diff --check`, and ratchet. Global `ruff check .` / format-check remain
  blocked by unrelated pre-existing files outside this slice.

- 2026-06-18: Scene-camera canonical camera geometry contracts moved from
  `scene_camera_comparison.py` to `scene_camera_geometry_contract.py`,
  including camera pose/intrinsics, room-scale, scene-frame-transform, and
  projection diagnostics. Dead facade aliases for already-owned
  USD/render/lighting helpers were removed instead of preserved as compatibility
  shims. Behavior-change class: internal artifact-construction cleanup; public
  comparison run orchestration, report rendering, and diagnostic payload schemas
  are unchanged. Metric: `scene_camera_comparison.py` is 1999 lines, the new
  geometry owner is 744 lines, and the ratchet reports 0 complexity rows and 77
  oversized modules. Proof: full scene-camera contract test file, ruff, format
  check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Operator-console control endpoint assertions moved running-state
  fixture setup, allowlisted transport, blocked-action transport,
  too-large-movement transport, response checks, and persisted operator-artifact
  checks out of
  `test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows()`
  into focused local helpers. Behavior-change class: test-only cleanup; control
  route allowlisting, movement bounds, MCP call payload, and operator artifact
  persistence are unchanged. Metric: ratchet reports 0 complexity rows and 77
  oversized modules, and the remaining
  `test_operator_console.py::test_operator_console_control_endpoint_is_allowlisted_and_records_operator_rows`
  PLR0915 row dropped from the complexity list. Proof: focused
  operator-console control endpoint test, ruff, format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Operator-console scene-preview asset endpoint assertions moved
  registered-asset checks, PNG response checks, JSON response checks, and
  invalid-path rejection checks out of
  `test_operator_console_serves_scene_preview_assets()` into focused local
  helpers. Behavior-change class: test-only cleanup; preview asset route
  behavior and registered preview names are unchanged. Metric: ratchet reports
  1 complexity row and 77 oversized modules, and
  `test_operator_console.py::test_operator_console_serves_scene_preview_assets`
  dropped from the complexity list. Proof: focused operator-console
  scene-preview endpoint test, ruff, format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Scene-sampler next-flow readiness assertions moved summary,
  artifact-path, source-status, and scanner-plan checks out of
  `_assert_next_flow()` into focused local assertion helpers. Behavior-change
  class: test-only cleanup; generated readiness artifact contracts are
  unchanged. Metric: ratchet reports 2 complexity rows and 77 oversized
  modules, and `test_scene_sampler_readiness_export.py::_assert_next_flow`
  dropped from the complexity list. Proof: focused scene-sampler readiness
  export test, ruff, format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Cleanup-checker fixture-id lookup moved semantic-substep,
  cleanup-primitive, agent-view worklist, and destination-option lookup out of
  `_candidate_fixture_id_for_object()` into local fixture-vocabulary helpers.
  Behavior-change class: test-only cleanup; checker semantics and fixture
  artifacts are unchanged. Metric: ratchet reports 3 complexity rows and 77
  oversized modules, and
  `test_check_molmo_realworld_cleanup_result.py::_candidate_fixture_id_for_object`
  dropped from the complexity list. Proof: focused cleanup checker contract
  tests, ruff, format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Semantic cleanup MCP registration moved map/navigation,
  observation, visual-grounding, and target-resolution tool registration out of
  `register_semantic_cleanup_tools()` into focused capability-local helpers.
  Behavior-change class: internal cleanup; public tool names, FastMCP schemas,
  dispatch handlers, and response shapes are unchanged. Metric: ratchet reports
  4 complexity rows and 77 oversized modules, and
  `realworld_mcp_semantic_tools.py::register_semantic_cleanup_tools` dropped
  from the complexity list. Proof: focused MCP server contract tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Operator-console prompt preview goal-contract launch arguments
  moved out of `_goal_contract()` into focused helpers for launch axes, missing
  default overrides, and explicit overrides. Behavior-change class: internal
  cleanup; prompt text, launch args, override precedence, and `LaunchError`
  recovery are unchanged. Metric: ratchet reports 5 complexity rows and 77
  oversized modules, and `prompt_preview.py::_goal_contract` dropped from the
  complexity list. Proof: focused operator-console prompt/launcher tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Eval-harness row blocker routing moved requirement priority and
  per-requirement blocker construction out of `_row_blockers()` into focused
  helpers. Behavior-change class: internal cleanup; selected-row schema,
  blocker details, DINO sidecar autostart behavior, runtime-map-prior gating,
  and execution order are unchanged. Metric: ratchet reports 6 complexity rows
  and 77 oversized modules, and `run_eval_harness.py::_row_blockers` dropped
  from the complexity list. Proof: focused eval-harness selector tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Live-eval detached-route polling moved early completion checks,
  timeout normalization/deadline calculation, per-poll completion handling, and
  post-deadline artifact recovery out of `wait_for_live_surface_completion()`
  into focused helpers. Behavior-change class: internal cleanup; live surface
  commands, artifact discovery, timeout/grace behavior, and `live_status.json`
  semantics are unchanged. Metric: ratchet reports 7 complexity rows and 77
  oversized modules, and `live_runtime.py::wait_for_live_surface_completion`
  dropped from the complexity list. Proof: focused eval-runner tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Provider-registry CLI dispatch moved parser setup, JSON payload
  construction/write, route text output, and supports-engine exit-code handling
  out of `_main()` into focused helpers. Behavior-change class: internal
  cleanup; provider route semantics, env precedence, public profile names,
  command names, and model metadata are unchanged. Metric: ratchet reports 8
  complexity rows and 77 oversized modules, and `provider_registry.py::_main`
  dropped from the complexity list. Proof: focused provider catalog tests,
  ruff, format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: MolmoSpaces robot-map rendering moved projection, frame, room
  outline, focus marker, object marker, trajectory, heading, and legend drawing
  out of `render_robot_map()` into focused helpers inside the existing map
  owner. Behavior-change class: internal cleanup; map dimensions, colors,
  labels, bounds, artifact names, and callers are unchanged. Metric: ratchet
  reports 9 complexity rows and 77 oversized modules, and
  `molmospaces_room_map.py` dropped from the complexity list while staying small
  at 414 lines. Proof: focused map-rendering unit test, ruff, format check,
  py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 camera preview candidate evaluation moved out of
  `_promote_b1_camera_previews()` into focused helpers for candidate
  diagnostics and accepted-score calculation. The promotion function keeps
  artifact readability, highest-score selection, image writes, and promoted
  metadata assembly. Behavior-change class: internal cleanup. Metric: ratchet
  reports 11 complexity rows and 77 oversized modules; the remaining B1 preview
  PLR0915 row is cleared, while `render_scene_previews.py` remains oversized at
  1377 lines. Proof: focused operator-console preview/static tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 preview cache/stale policy moved out of
  `render_b1_map12_preview()` into focused helpers for stale camera-preview
  deletion and `--skip-existing` eligibility. Runtime bundle compilation,
  static map/topdown rendering, and camera promotion remain in the main
  renderer. Behavior-change class: internal cleanup. Metric: ratchet reports
  12 complexity rows and 77 oversized modules; `render_scene_previews.py`
  remains oversized at 1335 lines, but the `render_b1_map12_preview()` C901 row
  is cleared. Proof: focused operator-console preview/static tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 / Map 12 `--skip-existing --b1-camera-artifact <path>` now
  skips only when existing preview metadata records real Isaac camera previews
  from the same requested artifact path. Stale camera previews from a different
  artifact are regenerated from the supplied artifact instead of being treated
  as current evidence. Metric: ratchet reports 13 complexity rows and 76
  oversized modules after the prior slice and 77 with this regression test
  added. Proof: focused operator-console preview tests, ruff,
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: B1 / Map 12 static preview generation no longer carries forward
  stale Isaac runtime FPV/chase previews when no fresh `--b1-camera-artifact` is
  supplied. The renderer now removes stale camera preview files and rewrites
  static map/topdown-only metadata, keeping real camera promotion explicit.
  Metric: ratchet reports 13 complexity rows and 76 oversized modules. Proof:
  focused operator-console preview tests, ruff, format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Operator-console route fixtures and scene-sampler stress eval
  artifacts now match the current source-aware MolmoSpaces catalog. The console
  registry no longer exposes legacy default cleanup rows, disabled Claude
  map-build rows are derived from the console-visible worlds, operator-console
  tests assert current `procthor-objaverse-val` route IDs, and the generated
  scene-sampler stress suite has 15 samples with `procthor-10k-val` recorded as
  partial. Metric: ratchet reports 14 complexity rows and 76 oversized modules.
  Proof: focused operator-console tests, focused eval/model/scene-sampler tests,
  ruff, format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Operator-console provider env override selection moved into the
  existing `launch_support.py` owner and now fails loudly on conflicting
  `provider_profile` / `ROBOCLAWS_PROVIDER_PROFILE` input. Readiness and
  `start_console_run()` resolve one canonical provider profile, apply that same
  value to the child environment, and keep launch state aligned with the argv
  provider profile so ambient `.env` values cannot silently retarget a selected
  route. Metric: `launcher.py` stays below the warning ceiling at 994 lines;
  ratchet reports 14 complexity rows and 75 oversized modules. Proof: focused
  provider-profile selection tests, ruff, format check, py_compile,
  `git diff --check`, and ratchet. Parked: the broader launcher test module has
  pre-existing stale `molmospaces/val_0` cleanup route constants and should be
  migrated separately.

- 2026-06-17: Cleanup report Agibot section rendering moved from
  `report.py` into `report_sections_agibot.py`. The new owner covers
  MolmoSpaces Agibot contract rehearsal rendering, Agibot SDK runner rendering,
  backend-stage/public-tool mapping, and subphase status labels; `report.py`
  keeps the cleanup report section sequence, shared report helpers, generic
  tables, state snapshots, and HTML shell. Two stale private table/format
  helpers left behind by previous section splits were removed. Metric:
  `report.py` 2175 -> 1995 lines, clearing the hard ceiling; new owner is 193
  lines; ratchet reports 14 complexity rows and 74 oversized modules. Owning
  layer: Artifacts, reports, and eval suites. Behavior-change class: internal
  owner split plus stale private helper removal. Proof: focused cleanup-report
  and MolmoSpaces Agibot contract report tests, ruff, touched-file format
  check, py_compile, and ratchet.

- 2026-06-17: Robot-camera visual-parity summary ownership split into focused
  report and payload owners. HTML report rendering now lives in
  `robot_camera_visual_parity_report.py`; object/capture-quality payload
  compaction, native Isaac render diagnostic summaries, metric scene
  signatures, capture-quality probe classification, and status-count helpers
  now live in `robot_camera_visual_parity_payloads.py`. The summarizer keeps
  CLI orchestration, manifest loading, gate/check assembly, probe matrix
  ranking, visual-sample collection, and artifact writes. Metric:
  `summarize_robot_camera_visual_parity.py` 2808 -> 1976 lines, clearing the
  hard ceiling; new owners are 517 and 349 lines; ratchet reports 14
  complexity rows and 74 oversized modules. Owning layer: Artifacts, reports,
  and eval suites. Behavior-change class: internal owner split. Proof: focused
  visual-parity unit tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: OpenAI Agents SDK perf-profile source ambiguity now fails
  aloud. `--agent-sdk-perf-profile` and `ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE`
  may both be present only when they name the same profile; conflicting values
  raise before live-run startup, and matching duplicate configuration is
  surfaced as `source=cli+environment`. Owning layers: Agent Engines And
  Provider Profiles plus Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud runtime configuration cleanup. Proof: focused OpenAI Agents perf
  profile tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: OpenAI Agents SDK profile setting helpers now reject ambiguous
  CLI/env conflicts across string, integer, positive-integer, float, and boolean
  knobs while still accepting the launch recipe's env-to-CLI pass-through when
  both sources resolve to the same value. This covers continuation mode,
  turn/context/budget limits, model-service retry settings, model racing, image
  memory, camera-grounded history, composite tools, and robot-view capture
  policy through the shared helper layer. Owning layers: Agent Engines And
  Provider Profiles plus Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud runtime configuration cleanup. Proof: focused OpenAI Agents perf
  profile tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: RAW-FPV visual-labeler provider config now requires explicit
  `CODEX_BASE_URL` in addition to `CODEX_API_KEY` for
  `codex-router-responses`; it no longer silently defaults to
  `https://api.openai.com/v1`. Owning layers: Agent Engines And Provider
  Profiles plus Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud provider/base-url cleanup. Proof: focused RAW-FPV visual-labeler
  provider tests, ruff, format check, py_compile, and ratchet.

- 2026-06-17: OpenAI Agents SDK runner-side performance-profile/default
  resolution moved from `run_live_openai_agents_cleanup.py` into
  `openai_agents_perf_profile.py`. The new owner covers profile defaults,
  CLI/env conflict checks, SDK model settings/run config, compaction and
  racing policy packets, camera-grounded composite-tool gating, robot-view
  capture policy, retry settings, and context-limit validation; the live runner
  keeps skill-context loading, stable-prefix hashing, prompt/server/timing, and
  artifact orchestration. Metric: live runner 2711 -> 1981 lines, clearing the
  hard ceiling; new owner is 786 lines; ratchet reports 14 complexity rows and
  74 oversized modules. Owning layers: Agent Engines And Provider Profiles plus
  Thin Runtime / Server Adapters. Behavior-change class: internal owner split.
  Proof: focused OpenAI Agents perf-profile tests, ruff, format check,
  py_compile, and ratchet.

- 2026-06-17: OpenAI Agents SDK sanitized span capture moved from
  `openai_agents_live.py` into `openai_agents_spans.py`. The new owner covers
  SDK span recording, span capture-unavailable packets, sanitized span export
  parsing, safe span names, MCP/tool-name extraction, usage/model extraction,
  sanitized error projection, ISO duration parsing, and span JSONL writes.
  Metric: SDK driver 2020 -> 1825 lines, clearing the hard ceiling; new owner
  is 240 lines; ratchet reports 14 complexity rows and 74 oversized modules.
  Owning layer: Agent Engines And Provider Profiles. Behavior-change class:
  internal owner split. Proof: focused OpenAI Agents span/retry/runtime tests,
  ruff, format check, py_compile, and ratchet.

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

- 2026-06-17: Planner-probe task-sampler diagnostics moved from
  `run_molmo_planner_manipulation_probe.py` into
  `planner_probe_task_sampler_diagnostics.py`, covering task-sampler
  robot-placement profiles, exact cleanup task config, exact sampler adapter,
  sampler failure diagnostics, placement scene/grasp/candidate-removal
  diagnostics, diagnostic JSON coercion, sampled task binding, requested
  cleanup primitive binding, and cleanup binding promotion. Tests now call the
  owner directly for sampler/binding behavior while runner tests keep worker
  exception context, CuRobo memory policy, policy execution diagnostics, and
  image artifact coverage on the runner. Metric: planner probe runner 2510 ->
  1103 lines, clearing the hard ceiling; new owner is 1412 lines warning-band
  debt; ratchet is 11 complexity rows and 69 oversized modules. Proof: focused
  planner headless renderer unit tests, planner manipulation checker contract
  tests, ruff, format check, py_compile, and ratchet.

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
- Planner-probe task-sampler diagnostics are owned by
  `planner_probe_task_sampler_diagnostics.py`; reopen only if
  `run_molmo_planner_manipulation_probe.py` starts rebuilding task-sampler
  robot-placement profiles, exact cleanup task config/binding, sampler failure
  diagnostics, placement scene/grasp/candidate diagnostics, diagnostic JSON
  coercion, sampled task binding, requested cleanup primitive binding, or
  cleanup binding promotion directly.
- OpenAI Agents SDK model-input compaction is owned by
  `openai_agents_model_input.py`. Metric: `openai_agents_live.py` 2889 ->
  1994 lines; new owner is 972 lines; staged/add-N ratchet reports 11
  complexity rows and 70 oversized modules. Proof: focused OpenAI Agents live
  runtime tests, ruff, format check, py_compile, and ratchet. Reopen only if
  the SDK driver rebuilds compaction config/filter setup, raw-FPV image-memory
  summaries, camera-grounded history summaries, tool-output unwrapping,
  metric-map/public output summaries, aggregate model-input shape metrics, or
  model-input filter event writing inline.
- Robot-camera apple-to-apple camera-contract diagnostics are owned by
  `robot_camera_apple2apple_camera_contract.py`. Metric: apple runner 2394 ->
  1803 lines; new owner is 626 lines; staged/add-N ratchet remains 11
  complexity rows and 70 oversized modules. Proof: focused apple comparison
  tests, ruff, format check, py_compile, and ratchet. Reopen only if the runner
  rebuilds top-level camera contract metadata, per-location camera contract
  diagnostics, FPV pose/lens delta summaries, compact camera metadata,
  robot-pose delta, Isaac robot import diagnostics, head-articulation
  diagnostics, or chase-contract diagnostics directly.
- OpenAI Agents SDK runner-side performance-profile/default resolution is
  owned by `openai_agents_perf_profile.py`. Metric: live runner 2711 -> 1981
  lines; new owner is 786 lines; ratchet reports 14 complexity rows and 74
  oversized modules. Proof: focused OpenAI Agents perf-profile tests, ruff,
  format check, py_compile, and ratchet. Reopen only if
  `run_live_openai_agents_cleanup.py` starts rebuilding profile id/default
  selection, provider route/model-family packets, SDK settings/run config,
  CLI/env precedence checks, compaction/racing/camera-grounded/robot-view/retry
  profile packets, or context-limit validation inline.
- OpenAI Agents SDK sanitized span capture is owned by
  `openai_agents_spans.py`. Metric: SDK driver 2020 -> 1825 lines; new owner
  is 240 lines; ratchet reports 14 complexity rows and 74 oversized modules.
  Proof: focused OpenAI Agents span/retry/runtime tests, ruff, format check,
  py_compile, and ratchet. Reopen only if `openai_agents_live.py` starts
  rebuilding sanitized span packets, span capture-unavailable records, span
  export parsing, safe span names, MCP/tool-name extraction, usage/model
  extraction, sanitized error projection, or ISO duration parsing inline.
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

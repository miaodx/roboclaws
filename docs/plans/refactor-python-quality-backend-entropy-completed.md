---
refactor_scope: python-quality-backend-entropy
status: COMPLETED_LEDGER
active_plan: docs/plans/refactor-python-quality-backend-entropy.md
last_compacted: 2026-06-18
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

- 2026-06-21: RAW-FPV perception probe Codex event JSONL reads now delegate to
  the shared JSONL source owner, including a new line-numbered row helper for
  consumers that need row-local secondary parsing. Present malformed or
  non-object `codex-events*.jsonl` rows now use canonical `RAW-FPV Codex event`
  row-source diagnostics before observation frames can be collected from
  partial event evidence, while embedded MCP observe-result parse errors still
  point at the original event line. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: internal source-reader consolidation with
  canonical row-source diagnostics. Metric: ratchet remains at 0 Ruff
  complexity rows and reports 80 oversized modules in the current shared
  checkout. Proof: focused core JSON-source and RAW-FPV perception probe
  tests, touched-file ruff/format checks, `git diff --check`,
  changed-code cleanup review, and ratchet. Reopen only if
  `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py` regains a local
  Codex-event JSONL row parser or corrupt present `codex-events*.jsonl` rows
  can again feed RAW-FPV observation-frame collection without canonical
  row-source diagnostics.

- 2026-06-21: Operator-console JSONL row reading now has one console-owned
  source collector for trace/event state display, run-history attachment, and
  operator-control append preflight. State and history paths preserve their
  partial valid-row display behavior while surfacing malformed or non-object
  present rows as source errors, and operator control remains fail-fast before
  adding a new command row. Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: internal source-reader consolidation with stable
  operator-visible diagnostics. Metric: ratchet remains at 0 Ruff complexity
  rows and reports 80 oversized modules in the current shared checkout; three
  local JSONL parsers became one console helper. Proof: focused
  operator-console state/history/control endpoint tests, touched-file
  ruff/format checks, `git diff --check`, changed-code cleanup review, and
  ratchet. Reopen only if console state/history/control regains duplicate row
  parsers or corrupt present JSONL rows can again feed operator-visible status
  or append new operator-control rows without source diagnostics.

- 2026-06-21: OpenAI Agents RAW-FPV budget guard trace parsing now delegates to
  the shared JSONL source helper for present `trace.jsonl` rows. Missing trace
  files remain the deliberate no-budget-evidence path, while malformed or
  non-object present rows now use canonical `OpenAI Agents budget trace`
  `path:row` source wording before candidate-attempt, repeated-failure, or
  observe-per-waypoint budget decisions can derive confidence from partial
  trace history. Owner layer: Agent Engines And Provider Profiles plus
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation with stable missing-source budget semantics and canonical
  row-source diagnostics. Metric: ratchet remains at 0 Ruff complexity rows
  and reports 80 oversized modules in the current shared checkout; new
  source-reader regressions live in a focused OpenAI Agents budget-source test
  file instead of growing the largest live-runtime test module. Proof: focused
  OpenAI Agents budget source/behavior tests, touched-file ruff/format checks,
  `git diff --check`, changed-code cleanup review, and ratchet. Reopen only if
  `scripts/molmo_cleanup/openai_agents_budget.py` regains a local JSONL row
  parser or corrupt present `trace.jsonl` rows can again feed RAW-FPV budget
  decisions without canonical row-source diagnostics.

- 2026-06-21: Model-latency calibration JSONL source parsing now delegates to
  the shared JSONL source helper for present `model_call_metrics.jsonl` rows.
  Missing metric files remain the deliberate empty-source path that produces
  insufficient-sample diagnostics, while malformed or non-object present rows
  now use canonical `model-call metrics` `path:row` source wording before
  calibration fitting, holdout validation, sample counts, or coefficient sets
  can derive confidence from partial telemetry. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader consolidation
  with stable missing-source calibration semantics and canonical row-source
  diagnostics. Metric: ratchet remains at 0 Ruff complexity rows and reports
  80 oversized modules in the current shared checkout; calibration tests now
  live in a focused report test file instead of keeping them in the larger
  live-performance test module. Proof: focused calibration/report-performance
  tests, touched-file ruff/format checks, `git diff --check`,
  changed-code cleanup review, and ratchet. Reopen only if
  `scripts/reports/calibrate_model_latency.py` regains a local JSONL row
  parser or corrupt present `model_call_metrics.jsonl` rows can again feed
  fitting or holdout validation without canonical row-source diagnostics.

- 2026-06-21: MolmoSpaces grasp initial-contact diagnostics now validate
  explicit candidate grasp JSON in the parent process before launching the
  child probe. Present malformed or non-object candidate files fail with
  path-labelled `candidate grasp JSON` source errors, valid candidate files
  still launch the probe, and missing candidate files keep the existing
  blocked-result path. Owner layer: Backend Runtime / Environment Primitive
  plus artifact diagnostics. Behavior-change class: fail-aloud explicit
  artifact source validation. Metric: ratchet remains at 0 Ruff complexity
  rows and reports 80 oversized modules in the current shared checkout. Proof:
  focused initial-contact diagnostics tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if corrupt initial-contact
  candidate grasp JSON can again reach the child probe and be reported as a
  generic probe blocker instead of a candidate source error.

- 2026-06-21: Generated-mess placement seeding now treats manifest
  `relation` and `placement_index` as canonical source truth in both
  MolmoSpaces and Isaac scenario-state helpers. The generated-mess contract
  owner exposes shared validators used by initial manifest materialization and
  later worker-state placement seeding, so persisted or hand-built worker
  state with malformed placement fields fails before backend fallbacks can
  emit plausible `inside`/loop-index placement diagnostics. Non-manifest
  generated-mess seeding keeps its backend fallback behavior. Owner layer:
  Backend Runtime / Environment Primitive plus the Generated Mess Set
  manifest contract. Behavior-change class: fail-aloud runtime manifest field
  validation. Metric: ratchet remains at 0 Ruff complexity rows and reports
  80 oversized modules in the current shared checkout. Proof: focused
  generated-mess scenario-state tests, existing generated-mess manifest and
  MolmoSpaces/Isaac worker tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if manifest-backed
  generated-mess placement can again default invalid `relation` or
  `placement_index` values during backend seeding.

- 2026-06-21: Camera-control request normalization now rejects malformed or
  missing explicit render-pose vectors and non-object view rows before
  renderers can emit valid-looking camera artifacts from fallback origin/default
  pose data. Canonical eye/target views require finite 3-number `eye`,
  `target`/`lookat`, and `up` vectors; anchor-orbit views require finite
  `target`/`lookat`; MolmoSpaces and Isaac camera-view spec helpers reuse the
  shared strict vector parser for direct calls; and Isaac USD-bound target
  derivation remains an explicit covered backend path. Owner layer: Backend
  Runtime / Environment Primitive plus the public household camera-control
  contract. Behavior-change class: fail-aloud camera-control source/vector
  validation. Metric: ratchet remains at 0 Ruff complexity rows and reports
  80 oversized modules in the current shared checkout. Proof: focused
  camera-control, MolmoSpaces camera-view, Isaac camera-view, and scene-camera
  color-profile tests, touched-file ruff/format checks, `git diff --check`,
  changed-code cleanup review, and ratchet. Reopen only if malformed
  camera-control `target`/`lookat`/`eye` rows can again become origin/default
  render poses or disappear from the view list without a source error.

- 2026-06-21: Operator-console runtime inventory now rejects corrupt
  successful Docker mount metadata before deciding whether a running container
  is repo-relevant. Missing Docker and nonzero `docker inspect` stay optional
  host-probe paths, valid repo-mounted containers still appear as running
  Docker tasks, and malformed, non-array, or non-object successful mount JSON
  now becomes a blocking `source_error` task instead of disappearing as "no
  repo-relevant mount." Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: fail-aloud inventory source validation for
  task-container discovery evidence. Metric: ratchet remains at 0 Ruff
  complexity rows and reports 80 oversized modules in the current shared
  checkout. Proof: focused operator-console runtime-inventory tests,
  touched-file ruff/format checks, `git diff --check`, changed-code cleanup
  review, and ratchet. Reopen only if corrupt present Docker mount metadata
  can again remove a running container from operator-console inventory or
  blockers.

- 2026-06-21: Operator-console stop handling now rejects corrupt successful
  Docker mount metadata before deciding whether a task container is attached
  to the run workspace. Missing Docker and nonzero `docker inspect` remain
  optional cleanup paths, while malformed, non-array, or non-object successful
  mount JSON now raises an operator stop source error before live-status or
  operator-state rewrite and before backend-lock release. Owner layer: Thin
  Runtime / Server Adapters. Behavior-change class: fail-aloud stop-source
  validation for task-container cleanup evidence. Metric: ratchet remains at
  0 Ruff complexity rows and reports 80 oversized modules in the current
  shared checkout. Proof: focused operator-console launcher tests,
  touched-file ruff/format checks, `git diff --check`, changed-code cleanup
  review, and ratchet. Reopen only if corrupt present Docker mount metadata
  can again disappear into "no mounted container" during operator stop
  handling.

- 2026-06-21: MolmoSpaces visual backend slot capacity config now rejects
  invalid `ROBOCLAWS_MOLMO_MAX_VISUAL_BACKENDS` and explicit `max_slots`
  values before live launch or operator-console inventory can report a
  plausible one-slot backend. Unset or blank env still uses the documented
  single-slot default, normal slot contention still reports active slot
  evidence, live household launch now names invalid slot config separately
  from contention, and runtime inventory emits a blocking `source_error` task
  for bad slot config. Owner layer: Backend Runtime / Environment Primitive
  plus Thin Runtime / Server Adapters. Behavior-change class: fail-aloud
  runtime capacity config validation. Metric: ratchet remains at 0 Ruff
  complexity rows and reports 80 oversized modules in the current shared
  checkout. Proof: focused visual-slot, household live-driver, and
  operator-console runtime-inventory tests, touched-file ruff/format checks,
  `git diff --check`, changed-code cleanup review, and ratchet. Reopen only
  if invalid MolmoSpaces visual backend slot capacity config again silently
  falls back to a valid-looking slot count or disappears from console
  readiness/inventory evidence.

- 2026-06-21: RAW-FPV perception probe runtime-prior loading now distinguishes
  explicit operator input from the default optional prior. User-supplied
  `--runtime-map-prior` paths, including both split and equals CLI spellings,
  fail aloud when missing instead of silently producing prior-free prompt
  inputs; the missing default prior remains the deliberate no-prior
  convenience. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud explicit artifact source validation.
  Metric: ratchet remains at 0 Ruff complexity rows and reports 80 oversized
  modules in the current shared checkout; the extra regression lives in a
  focused RAW-FPV source test file instead of growing the oversized main
  RAW-FPV test module. Proof: focused RAW-FPV perception probe tests,
  touched-file ruff/format checks, `git diff --check`, changed-code cleanup
  review, and ratchet. Reopen only if explicit runtime-prior CLI input can
  again disappear into empty prior context without a source error.

- 2026-06-21: OpenAI Agents model-input compaction threshold parsing now
  rejects boolean and non-positive values before live runtime or performance
  profile metadata can report plausible compaction thresholds. The live
  runtime path rejects bad `ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION_MIN_CHARS`
  env values and direct `model_input_compaction.min_chars` metadata, and the
  perf-profile producer rejects bad `model_input_compaction_min_chars` inputs
  instead of normalizing `0`, negatives, or booleans to `1`/`1200`. Owner
  layer: Agent Engines And Provider Profiles. Behavior-change class:
  fail-aloud env/direct config validation for model-facing evidence policy.
  Metric: ratchet remains at 0 Ruff complexity rows and reports 80 oversized
  modules in the current shared checkout; the extra regression cases live in a
  focused config test file instead of growing the largest live-runtime test
  module. Proof: focused OpenAI Agents runtime/config tests, touched-file
  ruff/format checks, `git diff --check`, changed-code cleanup review, and
  ratchet. Reopen only if OpenAI Agents model-input compaction or perf-profile
  threshold parsing again accepts booleans or non-positive values as valid
  thresholds.

- 2026-06-21: MolmoSpaces rigid grasp-cache generation preflight now treats
  successful runtime probes with malformed, non-object, or path-less stdout as
  blocked readiness evidence. The runtime probe parses stdout through the
  shared JSON-object text helper, preserves normal subprocess-failure blocking,
  and no longer reports `python_ready=True` with blank MolmoSpaces root/assets
  evidence. Owner layer: Backend Runtime / Environment Primitive plus
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  runtime readiness source validation. Metric: ratchet remains at 0 Ruff
  complexity rows and reports 80 oversized modules in the current shared
  checkout. Proof: focused planner task feasibility tests, touched-file
  ruff/format checks, `git diff --check`, changed-code cleanup review, and
  ratchet. Reopen only if grasp-cache generation preflight again treats
  malformed/non-object runtime-probe stdout or missing runtime paths as ready
  MolmoSpaces evidence.

- 2026-06-21: Scene-camera comparison MolmoSpaces source provenance now
  separates missing packages from installed packages with absent, malformed,
  or non-object `direct_url.json` metadata. Valid installed metadata still
  reports git URL/commit fields, package absence stays `not_installed`, and
  installed-package metadata problems now surface as `metadata_unavailable` or
  `metadata_unreadable` instead of false `not_installed` provenance. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class: report
  provenance status correction with stable render/report flow. Metric: ratchet
  remains at 0 Ruff complexity rows and reports 80 oversized modules in the
  current shared checkout; the new focused source test file avoids growing the
  oversized scene-camera contract test. Proof: focused scene-camera source
  tests, one nearby manifest serialization contract test, touched-file
  ruff/format checks, `git diff --check`, changed-code cleanup review, and
  ratchet. Reopen only if scene-camera comparison again catches corrupt
  installed-package provenance as package absence or accepts wrong-shaped
  `direct_url.json` metadata as installed source evidence.

- 2026-06-21: Environment setup private/report metadata env parsing now routes
  present `ROBOCLAWS_ENVIRONMENT_SETUP_JSON` payloads through the shared
  JSON-object text helper. Missing or blank env stays the documented
  no-metadata default, while malformed or non-object present env values fail
  aloud before run-result private setup provenance can silently disappear.
  Owner layer: Runnable Surfaces And Presets plus Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud env-source validation with stable
  valid metadata merge semantics. Metric: ratchet remains at 0 Ruff complexity
  rows and reports 80 oversized modules in the current shared checkout. Proof:
  focused core JSON-source and environment setup boundary tests, touched-file
  ruff/format checks, `git diff --check`, changed-code cleanup review, and
  ratchet. Reopen only if environment setup metadata env parsing regains a
  local permissive `json.loads` branch that treats present malformed or
  non-object private setup metadata as absent.

- 2026-06-20: Base Navigation Map v1 area semantic validation now splits
  geometry, label, category, source, and review checks into focused helpers in
  `roboclaws/maps/bundle_validation.py`. The strict validator keeps the same
  error wording and contract behavior while clearing the new C901 row from
  `_validate_base_navigation_area_semantics`. Owner layer: Backend Runtime /
  Environment Primitive map artifact validation. Behavior-change class:
  internal validator refactor with stable public validation diagnostics.
  Metric: global ratchet returns to 0 Ruff complexity rows and reports 80
  oversized modules in the current shared checkout. Proof: focused Base
  Navigation Map/Nav2 bundle contract tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if Base Navigation Map v1 area
  validation regains a C901 row or starts changing existing validation error
  wording without a contract update.

- 2026-06-20: Shared JSON source helpers now own parseable source type-name
  reporting through `roboclaws.core.json_sources.json_source_type_name`.
  Live-agent artifact loading and report-performance JSON loading no longer
  keep duplicate local reparsing helpers just to preserve non-object
  diagnostics; existing `non-object JSON: list` and `expected object, got
  list` wording remains covered by focused tests. Owner layer: shared core
  source-reader utility for Agent Engines And Provider Profiles plus
  Artifacts, reports, and eval suites. Behavior-change class: internal
  source-reader consolidation with stable error wording. Metric: touched
  helper/caller files remain clear; the global ratchet command currently
  reports 1 unrelated C901 row in no-touch
  `roboclaws/maps/bundle_validation.py` and 80 oversized modules after
  concurrent map-validation work appeared in the shared checkout. Proof:
  focused core JSON-source, live-runtime source, and report-performance source
  tests, touched-file ruff/format checks, `git diff --check`, and global
  ratchet run with unrelated no-touch regression noted. Reopen only if callers
  reintroduce local file reparsing helpers solely to name parseable non-object
  JSON source types.

- 2026-06-20: Scene-sampler scanner optional preview and product-smoke sidecar
  loading now routes through `roboclaws.core.json_sources.read_json_object`
  while preserving the permissive optional metadata contract: missing,
  unreadable, malformed, and non-object sources return empty metadata. Owner
  layer: Runnable Surfaces And Presets / launch scene sampler. Behavior-change
  class: permissive optional source-reader consolidation with stable
  empty-metadata semantics. Metric: ratchet remains at 0 Ruff complexity rows
  and reports 79 oversized modules in the current shared checkout; the new
  focused scanner-source test file is 45 lines instead of growing the
  oversized scene sampler test module. Proof: focused scene-sampler scanner
  optional JSON tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only if `scene_sampler_scanner.py` regains direct
  `json.loads(read_text(...))` parsing for optional preview/product-smoke
  sidecars or stops preserving empty metadata for missing/corrupt optional
  sources.

- 2026-06-20: OpenAI Agents SDK live timing now routes present
  `run_result.json` reads through
  `roboclaws.core.json_sources.read_json_value` while preserving the existing
  `OpenAI Agents live source ...` timing-source error wording. Malformed and
  non-object run results still fail final timing aloud before falling back to
  trace-derived plausible timing. Owner layer: Agent Engines And Provider
  Profiles / live-agent timing artifacts. Behavior-change class:
  source-reader consolidation for strict live timing evidence. Metric:
  ratchet remains at 0 Ruff complexity rows and reports 79 oversized modules
  in the current shared checkout; this slice added one focused parametrized
  row to the existing oversized `tests/unit/agents/test_live_runtime.py` to
  pin non-object `run_result.json` wording. Proof: focused OpenAI Agents live
  timing source-error tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `run_live_openai_agents_cleanup.py::_mcp_trace_timing` regains direct
  `json.loads(read_text(...))` parsing for `run_result.json` timing sources or
  stops failing malformed/non-object run results before trace fallback.

- 2026-06-20: MolmoSpaces and Isaac Lab backend wrapper state-file reads now
  route through `roboclaws.core.json_sources.read_json_object`. Valid state
  accessors remain unchanged, while missing, malformed, or non-object backend
  state files now fail with path-labelled source errors before wrapper
  properties derive runtime metadata from wrong-shaped evidence. Owner layer:
  Backend Runtime / Environment Primitive. Behavior-change class:
  source-reader consolidation for strict backend runtime state artifacts.
  Metric: ratchet remains at 0 Ruff complexity rows and reports 79 oversized
  modules in the current shared checkout; the module-count drop from 80 is
  affected by unrelated no-touch worktree state, while the new focused
  backend-state source test file is 94 lines instead of growing the oversized
  backend test modules. Proof: focused backend-state source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `MolmoSpacesSubprocessBackend._read_state` or
  `IsaacLabSubprocessBackend._read_state` regains direct
  `json.loads(read_text(...))` parsing for saved backend state.

- 2026-06-20: Scene-sampler required Procthor preview metadata loading now
  routes `molmospaces-val_<N>-preview.json` JSON-object sources through
  `roboclaws.core.json_sources.read_json_object` while preserving
  missing-source, source-id, and backend validation. Malformed or non-object
  preview metadata now fails before scanner admission or eval sample rows
  derive preview status from wrong-shaped metadata. Owner layer: Eval suites /
  launch scene sampler. Behavior-change class: source-reader consolidation
  for strict sampler preview metadata evidence. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched scene sampler is 1944 lines and its focused unit test file is
  1949 lines. Proof: focused scene-sampler unit tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/launch/scene_sampler.py` regains local raw JSON parsing for
  required Procthor preview metadata or malformed/non-object preview metadata
  can reach scanner admission or eval-sample row assembly as loaded metadata.

- 2026-06-20: Cleanup-result Isaac runtime checker scene-index artifact
  loading now routes required `isaac_scene_index.json` JSON-object sources
  through `roboclaws.core.json_sources.read_json_object` while preserving
  assertion-style checker failures. Missing, malformed, or non-object
  scene-index artifacts now fail before schema, privacy, binding, index, or
  segmentation assertions. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation for strict checker
  artifact evidence. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched Isaac runtime checker is 578 lines and the touched existing
  cleanup-result checker contract test file is 5156 lines. Proof: focused
  cleanup-result checker contract tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/isaac_runtime_checker.py` regains local raw JSON
  parsing for required `isaac_scene_index.json` artifacts or
  malformed/non-object scene-index artifacts can reach checker
  schema/privacy/binding/index assertions.

- 2026-06-20: Isaac scenario-builder map-bundle semantics loading now routes
  strict `semantics.json` JSON-object sources through
  `roboclaws.core.json_sources.read_json_object` while preserving valid
  empty-fixture fallback and valid map-aligned scenario construction. Missing,
  malformed, or non-object map-bundle semantics now fail before Isaac
  map-aligned scenario assembly. Owner layer: Backend Runtime / Environment
  Primitive. Behavior-change class: source-reader consolidation for strict
  Isaac map-bundle semantics artifacts. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched Isaac scenario-builder script is 670 lines and its focused test
  file is 131 lines. Proof: focused Isaac scenario-builder source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `scripts/isaac_lab_cleanup/isaac_scenario_builders.py` regains local
  raw JSON parsing for map-bundle `semantics.json` sources or
  malformed/non-object map-bundle semantics can reach map-aligned scenario
  assembly.

- 2026-06-20: Isaac scenario-builder generated-mess manifest loading now
  routes strict manifest JSON-object sources through
  `roboclaws.core.json_sources.read_json_object` while preserving
  schema-mismatch validation. Missing, malformed, or non-object manifests now
  fail before Isaac worker init scenario assembly. Owner layer: Backend
  Runtime / Environment Primitive. Behavior-change class: source-reader
  consolidation for strict Isaac init manifest artifacts. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched Isaac scenario-builder script is 671 lines and its focused test
  file is 64 lines. Proof: focused Isaac scenario-builder source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `scripts/isaac_lab_cleanup/isaac_scenario_builders.py` regains local
  raw JSON parsing for generated-mess manifests or malformed/non-object
  manifest sources can reach Isaac worker init scenario assembly.

- 2026-06-20: Agent SDK performance-matrix manifest loading now routes
  explicit manifest JSON-object sources through
  `roboclaws.core.json_sources.read_json_object` while preserving existing CLI
  failure behavior. Missing, malformed, or non-object manifests now fail before
  schema or row validation with status 1 and stderr evidence. Owner layer:
  Agent Engines And Provider Profiles / eval-support tooling.
  Behavior-change class: source-reader consolidation with stable CLI
  diagnostics. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched matrix script is 991 lines and its focused test file is 1052
  lines. Proof: focused Agent SDK performance matrix tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py` regains local raw JSON
  parsing for matrix manifests or malformed/non-object manifest sources can
  reach schema/row validation as loaded payloads.

- 2026-06-20: MolmoSpaces Agibot contract rehearsal strict JSON-object
  artifact reads now route through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  non-object context/reference artifacts now fail with path-labelled source
  errors before rehearsal reference evidence is assembled. Owner layer:
  Backend Runtime / Environment Primitive. Behavior-change class:
  source-reader consolidation for strict MolmoSpaces Agibot contract rehearsal
  artifacts. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched rehearsal module is 1949 lines and its focused test file is 96
  lines. Proof: focused Agibot contract rehearsal source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/agibot_contract_rehearsal.py` regains local raw JSON
  parsing for strict context/reference artifacts or malformed/non-object
  rehearsal artifacts can reach reference-evidence assembly.

- 2026-06-20: Agibot SDK runner strict JSON-object artifact reads now route
  through `roboclaws.core.json_sources.read_json_object`. Malformed or
  non-object context, agent-view, and subphase result artifacts now fail with
  path-labelled source errors before adapter consumers derive metric-map,
  fixture projection, or stage metadata. Owner layer: Backend Runtime /
  Environment Primitive. Behavior-change class: source-reader consolidation
  for strict Agibot SDK runner artifacts. Metric: current shared-checkout
  ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched runner module is 1189 lines and its focused test file is 44
  lines. Proof: focused Agibot SDK runner source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/agibot_sdk_runner.py` regains local raw JSON parsing for
  context, agent-view, or subphase result artifacts, or corrupt/non-object
  strict artifacts can reach metric-map, fixture-projection, or stage metadata
  consumers.

- 2026-06-20: Scene-camera source artifacts now route optional nearby
  `isaac_scene_index.json` probes through
  `roboclaws.core.json_sources.read_json_object` while preserving the
  permissive optional-index contract: malformed, non-object, unreadable, or
  mismatched nearby indexes are ignored, and matching valid scene indexes still
  provide USD prim hints. Owner layer: Backend Runtime / Environment Primitive
  diagnostics. Behavior-change class: source-reader consolidation with stable
  optional source semantics. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched source-artifacts module is 87 lines and its focused test file is
  49 lines. Proof: focused scene-camera source artifact tests, nearby Isaac
  view-spec tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if
  `roboclaws/household/scene_camera_source_artifacts.py` regains a local raw
  JSON parser for optional scene-index probes or matching valid indexes stop
  providing USD prim hints.

- 2026-06-20: Grasp filter diagnostics now route present candidate-grasp JSON
  artifact reads through `roboclaws.core.json_sources.read_json_object`.
  Missing candidate-grasp files keep the existing blocked-result path, while
  malformed or non-object `*_grasps.json` sources now fail with path-labelled
  source errors before subset generation, candidate counting, or filter-variant
  execution. Owner layer: Backend Runtime / Environment Primitive diagnostics.
  Behavior-change class: fail-aloud source-reader consolidation for diagnostic
  candidate-grasp evidence. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched diagnostics module is 516 lines and its focused test file is 162
  lines. Proof: focused grasp-filter diagnostics tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/grasp_filter_diagnostics.py` regains local raw JSON
  parsing for candidate-grasp artifacts or malformed/non-object
  candidate-grasp sources can reach subset, count, or variant execution.

- 2026-06-20: Grasp initial-contact diagnostics now route parent-side child
  `initial_contact_probe_result.json` reads through
  `roboclaws.core.json_sources.read_json_object`. Present malformed or
  non-object child probe results now fail with path-labelled source errors
  before variant summary/report assembly; the embedded MuJoCo child script and
  candidate-grasp parsing behavior remain unchanged. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud source-reader
  consolidation for diagnostic child-result evidence. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched diagnostics module is 593 lines and its focused test file is 206
  lines. Proof: focused initial-contact diagnostics tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/grasp_initial_contact_diagnostics.py` regains local raw
  JSON parsing for parent-side child probe results or malformed/non-object
  child result artifacts can reach summary/report assembly.

- 2026-06-20: Robot-camera apple-to-apple prior-probe manifest readers now
  route light/shadow, material-response, and tone/color comparison-history
  manifests through `roboclaws.core.json_sources.read_json_object` while
  preserving the optional report contract: missing prior probes stay
  `missing_manifest`, present malformed or non-object probes become
  `read_failed`, and valid probes keep existing summary/history behavior.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation with stable optional report evidence semantics.
  Metric: current shared-checkout ratchet summary reports 1 unrelated Ruff
  complexity row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80
  oversized modules; the apple-to-apple runner remains at 1826 lines and the
  new focused prior-probe source test file is 106 lines. Proof: focused
  prior-probe source tests, nearby apple-to-apple light/shadow,
  material-response, and tone/color history tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/run_robot_camera_apple2apple_comparison.py` or
  `scripts/molmo_cleanup/robot_camera_apple2apple_materials.py` regains local
  raw JSON parsing for prior-probe manifests or malformed/non-object prior
  probes can reach history comparison as loaded evidence.

- 2026-06-20: RAW-FPV perception probe JSON-object source reads now route
  runtime-map prior, private-label manifests, prediction manifests,
  run artifacts, and contrast artifacts through
  `roboclaws.core.json_sources.read_json_object`. Present malformed or
  non-object sources now fail with path-labelled source errors before prompt
  input, label, frame, or scoring assembly; missing optional runtime-map prior
  remains optional. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud source-reader consolidation for
  perception-probe report/scoring inputs. Metric: current shared-checkout
  ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched RAW-FPV test file remains below the 2000-line hard ceiling at
  1997 lines. Proof: focused RAW-FPV perception probe tests, touched-file
  ruff/format checks, stale raw-parser search in the probe script,
  `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/run_raw_fpv_perception_probe.py` regains local raw
  JSON parsing for those object sources or malformed/non-object report inputs
  can reach prompt/scoring assembly.

- 2026-06-20: RAW-FPV public sweep corpus generation now routes required saved
  `molmospaces_backend_state.json` sources through
  `roboclaws.core.json_sources.read_json_object` before sweep replay setup,
  public frame capture, or scorer-private label generation. Missing,
  malformed, and non-object saved backend state now fail with path-labelled
  source errors instead of raw parser/type failures. Owner layer: Backend
  Runtime / Environment Primitive. Behavior-change class: fail-aloud
  source-reader consolidation for public sweep replay input. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused RAW-FPV perception/sweep corpus tests, exact stale
  `_load_json`/raw-parser search in the sweep generator and tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `scripts/molmo_cleanup/generate_raw_fpv_sweep_corpus.py` regains
  local raw JSON parsing for saved backend-state sources or malformed saved
  state can reach public sweep replay.

- 2026-06-20: RAW-FPV private-label generation now routes required saved
  `molmospaces_backend_state.json` sources through
  `roboclaws.core.json_sources.read_json_object` before replay setup or
  scorer-private generated-mess reconstruction. Missing, malformed, and
  non-object saved backend state now fail with path-labelled source errors
  instead of raw parser/type failures. Owner layer: Backend Runtime /
  Environment Primitive. Behavior-change class: fail-aloud source-reader
  consolidation for scorer-private replay input. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused RAW-FPV perception/private-label tests, exact stale
  `_load_json`/raw-parser search in the generator and tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/generate_raw_fpv_private_labels.py` regains local raw
  JSON parsing for saved backend-state sources or malformed saved state can
  reach private-label replay.

- 2026-06-20: Isaac segmentation AOV comparison and matrix summary now share
  the same CLI-facing JSON artifact source adapter. The matrix script no
  longer carries a duplicate `_read_json` wrapper around
  `read_json_object`; it reuses the comparison diagnostic helper while
  preserving missing, malformed, and non-object wording for both
  `state artifact` and `artifact` labels. Owner layer: Backend Runtime /
  Environment Primitive diagnostics. Behavior-change class: source-reader
  adapter consolidation with stable CLI diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused Isaac segmentation AOV comparison/matrix tests, exact stale
  `_read_json(` search in the two AOV scripts, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/summarize_isaac_aov_matrix.py` regains a
  duplicate local JSON-object source adapter instead of reusing the comparison
  artifact reader.

- 2026-06-20: Operator-console state normalization no longer carries the
  unused `_read_json` wrapper that collapsed `JsonSourceError` state into `{}`.
  Active state reads already flow through `_read_json_source` and preserve
  source-error evidence for malformed live status, run-result, operator-state,
  trace, and agent-event artifacts. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: no-caller dead raw-reader removal. Metric:
  current shared-checkout ratchet summary reports 1 unrelated Ruff complexity
  row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized
  modules. Proof: exact no-reference search for `_read_json(` in
  `roboclaws/operator_console/state.py` and operator-console state tests,
  focused operator-console state unit tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `roboclaws/operator_console/state.py` reintroduces a local permissive raw
  JSON object reader instead of using `_read_json_source` /
  `read_json_object`.

- 2026-06-20: Operator-console launcher no longer carries the unused permissive
  `_read_json` helper that duplicated raw JSON parsing. All remaining launcher
  JSON-object reads now flow through the existing strict/optional
  `_read_json_source` path backed by `roboclaws.core.json_sources.read_json_object`.
  Owner layer: Thin Runtime / Server Adapters. Behavior-change class: no-caller
  dead raw-reader removal. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: exact no-reference search for `_read_json(` in launcher/operator-console
  tests, focused launcher unit tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `roboclaws/operator_console/launcher.py` reintroduces a local permissive raw
  JSON object reader instead of using `_read_json_source` / `read_json_object`.

- 2026-06-20: Operator-console passive interaction state reads now route
  present `operator_state.json` summary files through
  `roboclaws.core.json_sources.read_json_object` while preserving the passive
  UI-summary behavior: missing, malformed, unreadable, or non-object state
  sources return `{}` for message listing/state summaries instead of surfacing
  strict interaction errors. Strict steer/next-goal readers remain fail-aloud.
  Owner layer: Thin Runtime / Server Adapters. Behavior-change class:
  source-reader consolidation with stable passive-summary semantics. Metric:
  current shared-checkout ratchet summary reports 1 unrelated Ruff complexity
  row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized
  modules. Proof: focused operator-console interaction unit tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `roboclaws/operator_console/interactions.py` regains local raw JSON
  parsing for passive state reads or passive malformed/non-object state begins
  surfacing as a source error.

- 2026-06-20: Scene-camera USDA prepared-scene summary loading now routes
  present optional `summary.json` sidecars through
  `roboclaws.core.json_sources.read_json_object` while preserving the render
  contract's current optional evidence behavior: missing, malformed,
  unreadable, or non-object summaries contribute no prepared-summary fields
  instead of failing the USDA contract parser. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation with
  stable optional scene-render sidecar semantics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused scene-camera USDA source tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/scene_camera_usda_contract.py` regains local raw JSON
  parsing for prepared-scene summaries or corrupt optional summaries stop
  resolving to `{}`.

- 2026-06-20: Isaac report scene-index artifact loading now routes present
  optional `isaac_scene_index.json` sidecars through
  `roboclaws.core.json_sources.read_json_object` while preserving the report
  layer's current optional evidence behavior: missing, unresolved, malformed,
  unreadable, or non-object sidecars render as absent artifact tables instead
  of failing report generation. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: source-reader consolidation with stable
  optional report-sidecar semantics. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused Isaac report-section source tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/report_sections_isaac.py` regains local raw JSON
  parsing for scene-index report sidecars or corrupt optional sidecars stop
  rendering as absent tables.

- 2026-06-20: Isaac RBY1M robot import summary loading now routes present
  optional `rby1m_holobase_isaac.import_summary.json` files through
  `roboclaws.core.json_sources.read_json_object` while preserving the existing
  optional-source contract: missing, malformed, unreadable, or non-object
  summaries return `{}` and keep the robot-import plan in pending/not-ready
  state. Owner layer: Backend Runtime / Environment Primitive. Behavior-change
  class: source-reader consolidation with stable optional-source semantics.
  Metric: current shared-checkout ratchet summary reports 1 unrelated Ruff
  complexity row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80
  oversized modules. Proof: focused Isaac robot import source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `scripts/isaac_lab_cleanup/isaac_robot_import.py` regains local raw
  JSON parsing for import summaries or optional corrupt summaries stop
  resolving to `{}`.

- 2026-06-20: MolmoSpaces visual backend slot reads now route present slot
  lease JSON through `roboclaws.core.json_sources.read_json_object` while
  preserving the lock manager's fail-closed behavior for malformed,
  unreadable, or non-object slot files. Corrupt slot files still appear held
  and block acquisition instead of silently freeing a backend slot. Owner
  layer: Thin Runtime / Server Adapters. Behavior-change class:
  source-reader consolidation with tested corrupt-lock semantics. Metric:
  current shared-checkout ratchet summary reports 1 unrelated Ruff complexity
  row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized
  modules. Proof: focused visual backend slot unit tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/visual_backend_slots.py` regains local raw JSON parsing
  for slot lease files or corrupt slot files become fail-open.

- 2026-06-20: Scene-camera comparison metadata loading now routes present
  `scene_metadata.json` files through
  `roboclaws.core.json_sources.read_json_object` inside the existing
  RuntimeError translation layer. Missing metadata remains an optional empty
  source, malformed or non-object metadata keeps the tested scene-camera error
  wording, and the permissive local Isaac scene-index cache reader remains
  local by design. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation with stable strict-source
  diagnostics. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused scene-camera comparison contract tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/household/scene_camera_source_artifacts.py` regains local raw JSON
  parsing for present `scene_metadata.json` sources or scene-camera metadata
  error wording drifts from the tested contract.

- 2026-06-20: B1 Map 12 label-tool semantics and source-metadata reads now
  route through `roboclaws.core.json_sources.read_json_object` inside a small
  label-tool translation wrapper. The existing CLI/test wording for missing,
  malformed, and non-object semantics/source metadata stays stable while raw
  file parsing and JSON-object validation are shared. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation with stable CLI diagnostics. Metric: current shared-checkout
  ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused B1 Map 12 label-tool contract tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/maps/render_b1_map12_label_tool.py` regains local raw JSON parsing
  for semantics or source metadata inputs, or if the tested label-tool
  source-error wording drifts.

- 2026-06-20: B1 Map 12 manual alignment overlay scene-topdown and alignment
  artifact reads now route through
  `roboclaws.core.json_sources.read_json_object` inside the existing
  `load_json` wrapper. The CLI keeps its established missing, malformed, and
  non-object source wording while sharing the canonical raw JSON parser.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation with stable CLI diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused B1 Map 12 manual alignment overlay contract tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if `scripts/maps/render_b1_map12_manual_alignment_overlay.py` regains
  local raw JSON parsing for scene-topdown or alignment artifacts, or if the
  overlay CLI source-error wording drifts from the tested current wording.

- 2026-06-20: B1 scene Gaussian topdown capture-result loading now routes the
  child `capture_result.json` artifact through
  `roboclaws.core.json_sources.read_json_object` before attaching the
  `result_path` field. Malformed or non-object child capture results now fail
  with path-labelled source errors instead of parser/type failures during
  topdown packet assembly. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud child
  artifact validation. Metric: current shared-checkout ratchet summary reports
  1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused B1 scene Gaussian topdown contract tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/maps/render_b1_scene_gaussian_topdown.py` regains local raw JSON
  parsing for child capture-result artifacts or malformed child results can
  again reach topdown render packet assembly as parser tracebacks or
  wrong-shaped payloads.

- 2026-06-20: MolmoSpaces subprocess worker camera view-spec loading now routes
  file-backed view-list or `{views: [...]}` payloads through
  `roboclaws.core.json_sources.read_json_value` before the existing
  list/object-with-views shape validation. Missing or malformed view-spec
  files now use canonical path-labelled source wording, while the accepted
  top-level list and wrapped-view payload forms remain unchanged for
  camera-control request normalization. Owner layer: Backend Runtime /
  Environment Primitive camera rendering helper. Behavior-change class:
  source-reader consolidation / fail-aloud source validation. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused MolmoSpaces subprocess backend tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/molmospaces_subprocess_worker.py` regains local raw
  JSON parsing for explicit camera view-spec files or malformed view-spec
  sources can again reach camera-request normalization as parser tracebacks.

- 2026-06-20: Isaac scene camera view-spec loading now routes file-backed
  view-list or `{views: [...]}` payloads through
  `roboclaws.core.json_sources.read_json_value` before the existing
  list/object-with-views shape validation. Missing or malformed view-spec
  files now use canonical path-labelled source wording, while the accepted
  top-level list and wrapped-view payload forms remain unchanged. Owner layer:
  Backend Runtime / Environment Primitive camera geometry helper.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused Isaac backend tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/isaac_scene_camera_geometry.py` regains local raw
  JSON parsing for explicit camera view-spec files or malformed view-spec
  sources can again reach camera-request normalization as parser tracebacks.

- 2026-06-20: Isaac segmentation AOV comparison and matrix summary artifact
  reads now route explicit control/candidate state artifacts and
  `--entry LABEL=PATH` state/preflight artifacts through
  `roboclaws.core.json_sources.read_json_object`. Existing CLI wording remains
  stable for missing, malformed, and non-object state/preflight sources, and
  comparison/matrix decision behavior is unchanged. Owner layer: Backend
  Runtime / Environment Primitive diagnostics. Behavior-change class:
  source-reader consolidation with stable CLI diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused Isaac segmentation AOV comparison/matrix tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/compare_isaac_segmentation_aov.py` or
  `scripts/isaac_lab_cleanup/summarize_isaac_aov_matrix.py` regains local raw
  JSON-object parsing for state/preflight artifact sources or corrupt AOV
  source diagnostics drift from the current CLI wording.

- 2026-06-20: Shared Agibot navigation-memory source loading now routes
  required `navigation_memory.json` object reads through
  `roboclaws.core.json_sources.read_json_object`. Existing
  navigation-memory-specific error wording remains stable for missing,
  malformed, non-object, item-list, and point-geometry failures across
  runtime-prior, consistency, label-tool, and B1 runtime-bundle consumers.
  Owner layer: Runtime Artifacts at the map source parsing boundary.
  Behavior-change class: shared source-reader consolidation with stable
  consumer diagnostics. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused navigation-memory consumer contract tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `roboclaws/maps/navigation_memory.py` regains local raw JSON-object parsing
  or downstream navigation-memory source diagnostics drift from the current
  consumer-specific wording.

- 2026-06-20: Representative visual-grounding corpus building now routes
  discovered cleanup `run_result.json` sources through
  `roboclaws.core.json_sources.read_json_object`. Malformed or non-object
  source runs now fail with path-labelled source errors and no traceback
  instead of being skipped or surfacing raw type failures, while valid
  ineligible-run filtering remains unchanged. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation with
  fail-aloud corpus input diagnostics. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused visual-grounding corpus builder contract tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/visual_grounding/build_representative_visual_grounding_corpus.py`
  regains a local raw JSON-object reader for discovered `run_result.json`
  sources or corrupt representative inputs can disappear from corpus
  generation.

- 2026-06-20: MolmoSpaces worker initialization now routes generated-mess
  manifest and adjacent source scene JSON-object reads through
  `roboclaws.core.json_sources.read_json_object`. Generated-mess schema
  validation stays unchanged, malformed or non-object source scene JSON keeps
  the established worker-init diagnostics, and valid source-room labels remain
  unchanged. Owner layer: Backend Runtime / Environment Primitive.
  Behavior-change class: source-reader consolidation with stable worker-init
  diagnostics. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused MolmoSpaces worker-state tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/molmospaces_worker_init.py` regains local raw
  JSON-object readers for generated-mess manifests or source scene JSON
  metadata.

- 2026-06-20: Visual-grounding benchmark checker result JSON and prediction
  JSONL reads now route through
  `roboclaws.core.json_sources.read_json_object` and
  `read_jsonl_objects` while preserving the checker's existing CLI error
  wording for malformed or non-object sources. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: checker source-reader consolidation
  with stable fail-aloud diagnostics. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused visual-grounding checker source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/visual_grounding/check_visual_grounding_benchmark_result.py`
  regains local raw JSON/JSONL parser loops for result or prediction sources.

- 2026-06-20: B1 / Map 12 waypoint-pose request builder `--points`
  JSON-array reads now route through
  `roboclaws.core.json_sources.read_json_value` before existing array shape
  validation. Missing, malformed, and non-array point sources keep their
  existing CLI diagnostic categories while sharing the canonical parser.
  Owner layer: Backend Runtime / Environment Primitive at the B1 Map 12
  navigation request artifact boundary. Behavior-change class: JSON-value
  source-reader consolidation with stable CLI diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused waypoint-pose request CLI source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/build_b1_map12_waypoint_pose_requests.py` regains
  a local raw JSON parser for explicit `--points` files.

- 2026-06-20: Isaac B1 / Map 12 navigation-smoke child capture request and
  result artifact reads now route through
  `roboclaws.core.json_sources.read_json_object`. Malformed or non-object
  `_capture-one` request files fail with path-labelled source errors before
  worker import/capture, and malformed child result files become explicit
  `child_failures` source-error evidence instead of raw parser crashes during
  aggregation. Owner layer: Backend Runtime / Environment Primitive. Behavior
  change class: required artifact source-reader consolidation with stable
  blocked-run evidence. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules.
  Proof: focused navigation-smoke CLI source-error tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/run_b1_map12_navigation_smoke.py` regains local
  raw JSON-object readers for child request/result artifacts or malformed child
  result sources can crash aggregation instead of becoming source-error
  evidence.

- 2026-06-20: Agibot map-context capture/update and PNC waypoint verification
  now route required operator-authored context reads through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, and
  non-object context files now fail with path-labelled source errors before
  capture upsert or robot waypoint verification, while the verifier's existing
  authoring-schema validation remains unchanged. Owner layer: Backend Runtime
  / Environment Primitive tooling at the Agibot map-authoring boundary.
  Behavior-change class: required CLI source-reader consolidation with
  fail-aloud diagnostics. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the touched Agibot contract test remains oversized at 1112 lines. Proof:
  focused Agibot source-error tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if
  `scripts/agibot/capture_map_context_views.py` or
  `scripts/agibot/verify_waypoints_with_pnc.py` regain local raw JSON-object
  readers for required context files or source diagnostics stop naming the
  failing context path.

- 2026-06-20: MolmoSpaces subprocess worker state loading now routes required
  state-file reads through `roboclaws.core.json_sources.read_json_object`.
  Missing, malformed, and non-object worker state files now fail with
  path-labelled source errors instead of raw parser/type failures, while valid
  state payloads remain unchanged. Owner layer: Backend Runtime / Environment
  Primitive. Behavior-change class: required worker source-reader
  consolidation. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused
  MolmoSpaces worker state source-error and valid-state tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/molmo_cleanup/molmospaces_worker_protocol.py` regains a local raw
  JSON-object reader for required state files.

- 2026-06-20: Isaac worker state loading now routes required state-file reads
  through `roboclaws.core.json_sources.read_json_object` before adding the
  private `_state_path` runtime field. Missing, malformed, and non-object
  worker state files now fail with path-labelled source errors instead of raw
  parser/type failures. Owner layer: Backend Runtime / Environment Primitive.
  Behavior-change class: required worker source-reader consolidation with
  unchanged valid-state behavior. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused
  Isaac worker state source-error and valid-state tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/isaac_lab_cleanup/isaac_worker_protocol.py` regains a local raw
  JSON-object reader for required state files or valid state reads stop
  preserving `_state_path`.

- 2026-06-20: Agibot metric-map generation now routes the required
  `context_json` source through `roboclaws.core.json_sources.read_json_object`
  before map-context schema validation. Missing, malformed, and non-object
  authoring context sources now fail with path-labelled source errors instead
  of raw parser/type failures. Owner layer: Backend Runtime / Environment
  Primitive tooling at the Agibot map-artifact boundary. Behavior-change class:
  required CLI source-reader consolidation with fail-aloud diagnostics. Metric:
  current shared-checkout ratchet summary reports 1 unrelated Ruff complexity
  row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized
  modules; this slice did not add new complexity in touched files. Proof:
  focused Agibot map-context source-error and happy-path tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `scripts/agibot/generate_metric_map_from_context.py` regains a local raw
  JSON-object reader for required context files or source diagnostics stop
  naming the failing context path.

- 2026-06-20: Operator-console launcher strict JSON-object source reads now use
  `roboclaws.core.json_sources.read_json_object` while preserving existing
  `_JsonSourceError` wording for operator stop/readiness diagnostics. The
  permissive optional launcher reader remains local because it intentionally
  treats missing or malformed optional sidecars as absent evidence. Owner
  layer: Thin Runtime / Server Adapters. Behavior-change class: source-reader
  consolidation with stable launcher source diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: focused launcher source-error tests, touched-file ruff/format
  checks, changed-code review, `git diff --check`, and ratchet. Reopen only if
  operator-console launcher strict source loading regains a local raw
  JSON-object reader or stop/readiness source diagnostics drift from the stable
  launcher wording.

- 2026-06-20: Operator-console backend resource-lock reads now use
  `roboclaws.core.json_sources.read_json_object` for lock JSON-object sources.
  Missing lock files remain unheld; malformed, non-object, or unreadable lock
  files remain held-but-stale so a later acquire can recover them. Owner layer:
  Thin Runtime / Server Adapters. Behavior-change class: source-reader
  consolidation plus fail-soft stale-lock recovery for parseable non-object
  lock sources. Metric: current shared-checkout ratchet summary reports 1
  unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: focused operator-console lock tests, touched-file ruff/format
  checks, changed-code review, `git diff --check`, and ratchet. Reopen only if
  operator-console resource locks regain a local raw JSON-object reader or
  malformed/non-object lock artifacts stop being treated as stale recoverable
  locks.

- 2026-06-20: Operator-console runtime inventory optional JSON-object source
  reads now use `roboclaws.core.json_sources.read_json_object` while
  preserving existing `JsonSourceError` reason codes and source-error task
  messages for missing, malformed, non-object, unreadable, and non-file
  sources. Runtime inventory/blocker semantics and host probes stay unchanged.
  Owner layer: Thin Runtime / Server Adapters. Behavior-change class:
  source-reader consolidation with stable runtime-inventory diagnostics.
  Metric: current shared-checkout ratchet summary reports 1 unrelated Ruff
  complexity row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80
  oversized modules; the 801-line
  `tests/contract/maps/test_b1_map12_label_tool.py` entry remains unrelated
  no-touch debt, and this slice did not add new complexity in touched files.
  Proof: focused runtime-inventory tests, touched-file ruff/format checks,
  changed-code review, `git diff --check`, and ratchet. Reopen only if
  operator-console runtime inventory regains a local raw JSON-object reader or
  corrupt present runtime source artifacts stop surfacing stable
  `JsonSourceError` task evidence.

- 2026-06-20: Operator-console control endpoint operator-state reads now use
  `roboclaws.core.json_sources.read_json_object` for strict operator-state
  object sources while preserving existing `OperatorControlError` wording and
  status codes for missing, malformed, non-object, and unreadable sources.
  Control JSONL row parsing remains local because it is row-oriented. Owner
  layer: Thin Runtime / Server Adapters. Behavior-change class: source-reader
  consolidation with stable control endpoint diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: full operator-console tests, touched-file ruff/format checks,
  changed-code review, `git diff --check`, and ratchet. Reopen only if
  operator-console control endpoint state loading regains a local raw
  JSON-object reader or corrupt present operator-state sources stop surfacing
  stable `OperatorControlError` evidence.

- 2026-06-20: Operator-console latest-run history sidecar reads now use
  `roboclaws.core.json_sources.read_json_object` for operator-state and
  live-status object sources while preserving existing `HistorySourceError`
  payloads and invalid/non-object reason text. History JSONL row parsing remains
  local because it is row-oriented. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: source-reader consolidation with stable
  latest-run history diagnostics. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: focused operator-console history tests, touched-file
  ruff/format checks, changed-code review, `git diff --check`, and ratchet.
  Reopen only if latest-run history sidecar loading regains local raw
  JSON-object readers or corrupt present sidecars stop surfacing stable
  `HistorySourceError` evidence.

- 2026-06-20: Operator-console interaction command strict session and
  run-state readers now use `roboclaws.core.json_sources.read_json_object`
  while preserving existing `InteractionError` wording for invalid JSON,
  unreadable sources, non-object JSON, unknown runs, and session id mismatch.
  Passive message-listing state reads remain permissive by design. Owner layer:
  Thin Runtime / Server Adapters. Behavior-change class: source-reader
  consolidation with stable command-write diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: full operator-console interaction unit tests, touched-file
  ruff/format checks, changed-code review, `git diff --check`, and ratchet.
  Reopen only if strict operator-console session/run-state command readers
  regain local raw JSON-object readers or corrupt present sources stop
  preserving stable `InteractionError` evidence.

- 2026-06-20: Operator-console state JSON source normalization now uses
  `roboclaws.core.json_sources.read_json_object` for present operator state,
  live status, and run-result object reads while preserving the existing
  `JsonSourceError` payload shape and operator-visible invalid/non-object
  reason text. Owner layer: Thin Runtime / Server Adapters. Behavior-change
  class: source-reader consolidation with stable operator-state diagnostics.
  Metric: current shared-checkout ratchet summary reports 1 unrelated Ruff
  complexity row in `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80
  oversized modules; the 801-line
  `tests/contract/maps/test_b1_map12_label_tool.py` entry remains unrelated
  no-touch debt, and this slice did not add new complexity in touched files.
  Proof: full operator-console state unit tests, touched-file ruff/format
  checks, changed-code review, `git diff --check`, and ratchet. Reopen only if
  operator-console state loading regains local raw JSON-object readers for
  operator state/live status/run result artifacts or corrupt present state
  artifacts stop surfacing stable `JsonSourceError` evidence.

- 2026-06-20: Operator-console request-field readiness now uses
  `roboclaws.core.json_sources.read_json_object` for attached JSON-object gate
  artifacts while preserving existing gate statuses and operator-facing
  unreadable/non-object message categories. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: source-reader consolidation with stable
  route-readiness diagnostics. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: focused Agibot readiness context tests, touched-file
  ruff/format checks, changed-code review, `git diff --check`, and ratchet.
  Reopen only if operator-console request-field readiness regains a local raw
  JSON-object reader or attached context artifacts stop surfacing stable
  readiness-gate diagnostics.

- 2026-06-20: Provider timing proxy readiness now uses
  `roboclaws.core.json_sources.read_json_object` for present
  `provider_timing_proxy.ready.json` object parsing and writes the child ready
  artifact atomically. Missing ready files remain the polling/not-ready state;
  malformed or non-object ready files now fail startup with a source-specific
  runtime error instead of returning a fabricated proxy handle or drifting into
  a timeout. Owner layer: Agent Engines and Provider Profiles / provider
  timing runtime adapter. Behavior-change class: source-reader consolidation
  and fail-aloud readiness validation. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the 801-line `tests/contract/maps/test_b1_map12_label_tool.py` entry remains
  unrelated no-touch debt, and this slice did not add new complexity in touched
  files. Proof: focused provider timing proxy tests, touched-file ruff/format
  checks, changed-code review, `git diff --check`, and ratchet. Reopen only if
  provider timing proxy readiness regains a local raw JSON-object reader or
  corrupt present ready artifacts can again be treated as ready, missing, or
  timeout-only evidence.

- 2026-06-20: Live-agent artifact JSON loading now uses
  `roboclaws.core.json_sources.read_json_object` for object parsing while
  preserving existing live-runtime artifact error wording for missing,
  malformed, unreadable, and non-object `live_status.json` / `run_result.json`
  sources. Missing artifact behavior remains optional and empty. Owner layer:
  Agent Engines and Provider Profiles / live runtime artifact normalization.
  Behavior-change class: source-reader consolidation with stable normalized
  live-runtime diagnostics. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the added oversized entry is unrelated no-touch dirty
  `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did not
  add new complexity in touched files. Proof: focused live-runtime source
  helper tests, existing live-agent artifact normalization tests, touched-file
  ruff/format checks, changed-code review, `git diff --check`, and ratchet.
  Reopen only if live-agent artifact loading regains a local raw JSON-object
  reader or malformed/non-object status/result artifacts stop surfacing stable
  live-runtime source error wording.

- 2026-06-20: Report-performance JSON artifact loading now uses
  `roboclaws.core.json_sources.read_json_object` for object parsing while
  preserving existing `ReportPerformanceSourceError` wording for missing,
  malformed, unreadable, and non-object JSON sources. JSONL source parsing
  remains unchanged because it is row-oriented. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation with stable report-performance diagnostics. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  dirty `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized
  modules; the added oversized entry is unrelated no-touch dirty
  `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did not
  add new complexity in touched files. Proof: focused report-performance
  malformed JSON/JSONL source tests, touched-file ruff/format checks,
  changed-code review, `git diff --check`, and ratchet. Reopen only if
  report-performance JSON artifact loading regains a local raw JSON-object
  reader or malformed/non-object JSON sources stop surfacing the stable
  report-performance source error wording.

- 2026-06-20: Eval-runner optional and required JSON sidecar grading now uses
  `roboclaws.core.json_sources.read_json_object` for object parsing while
  preserving the existing grader reason-code contract: `missing`,
  `invalid_json`, `invalid_json_object`, and `read_error`. The optional and
  required sidecar loaders now share one internal converter instead of
  duplicating raw file reads, JSON parsing, and object checks. Owner layer:
  Eval suites and eval-run artifact grading. Behavior-change class:
  source-reader consolidation with stable grader failure classification.
  Metric: current shared-checkout ratchet summary reports 1 unrelated Ruff
  complexity row in dirty `scripts/maps/compile_b1_map12_runtime_bundle.py`
  and 80 oversized modules; the added oversized entry is unrelated no-touch
  dirty `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did
  not add new complexity in touched files. Proof: focused eval-runner source
  helper tests, existing malformed artifact/sidecar eval-runner behavior
  tests, touched-file ruff/format checks, changed-code review,
  `git diff --check`, and ratchet. Reopen only if eval-runner JSON sidecar
  grading regains local raw JSON-object readers or corrupt sidecars stop
  producing stable grader reason codes.

- 2026-06-20: Eval regression promotion now uses
  `roboclaws.core.json_sources.read_json_object` for explicit eval-results and
  suite JSON-object inputs while preserving the
  `eval-regression:do-not-promote` stop label before source reads or writes.
  Missing, malformed, or parseable non-object promotion sources now use
  canonical path-labelled source wording before regression sample or suite
  output writes. Owner layer: Eval suites and regression-promotion artifacts.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: current shared-checkout ratchet summary reports
  1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the added oversized entry is unrelated no-touch dirty
  `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did not
  add new complexity in touched files. Proof: focused regression-promotion
  source tests, existing regression-promotion behavior tests, touched-file
  ruff/format checks, changed-code review, `git diff --check`, and ratchet.
  Reopen only if regression promotion regains a local raw JSON reader or
  corrupt explicit promotion sources can again reach sample/suite promotion as
  parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Cleanup report runtime timing now uses
  `roboclaws.core.json_sources.read_json_object` for present
  `live_timing.json` sidecars while preserving missing sidecars as absent
  runner timing. Malformed or parseable non-object timing evidence now uses
  canonical path-labelled source wording before report rendering instead of
  disappearing from the timing section. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud source validation. Metric: current shared-checkout ratchet
  summary reports 1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the added oversized entry is unrelated no-touch dirty
  `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did not
  add new complexity in touched files. Proof: focused runtime-timing report
  tests, touched-file ruff/format checks, changed-code review,
  `git diff --check`, and ratchet. Reopen only if report runtime timing
  loading regains a local raw JSON reader or corrupt present `live_timing.json`
  sidecars can again be hidden as absent runner timing.

- 2026-06-20: Cleanup report artifact re-rendering now uses
  `roboclaws.core.json_sources.read_json_object` for run-result, scenario, and
  adjacent private-manifest JSON-object sources. Malformed or parseable
  non-object report inputs now use canonical path-labelled source wording
  before report assembly, while `is_cleanup_run_result_artifact()` still
  returns false for invalid candidates and declared artifact path validation
  stays unchanged. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: current shared-checkout ratchet summary reports
  1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 80 oversized modules;
  the added oversized entry is unrelated no-touch dirty
  `tests/contract/maps/test_b1_map12_label_tool.py`, and this slice did not
  add new complexity in touched files. Proof: focused
  cleanup report artifact contract tests, touched-file ruff/format checks,
  changed-code review, `git diff --check`, and ratchet. Reopen only if cleanup
  report artifact re-rendering regains a local raw JSON reader or corrupt
  report input artifacts can again reach report assembly as parser tracebacks
  or wrong-shaped payloads.

- 2026-06-20: Skill scratchpad artifact loading now uses
  `roboclaws.core.json_sources.read_json_object` for present
  `agent_scratchpad.json` and legacy `cleanup_scratch.json` sources while
  preserving missing-source creation. Malformed or parseable non-object
  scratchpad artifacts now use canonical path-labelled source wording before
  MCP done-artifact assembly, and legacy scratchpad copying still writes the
  canonical `agent_scratchpad.json` target. Owner layer: Household World
  artifacts under the MCP run artifact boundary. Behavior-change class:
  source-reader consolidation / fail-aloud source validation. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  dirty `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized
  modules; this slice did not add new complexity in touched files. Proof:
  focused scratchpad source tests, touched-file ruff/format checks,
  changed-code review, `git diff --check`, and ratchet. Reopen only if
  scratchpad loading regains a local raw JSON reader or corrupt present
  scratchpad sources can again reach MCP artifact assembly as parser
  tracebacks or wrong-shaped payloads.

- 2026-06-20: Live eval artifact sidecar loading now uses
  `roboclaws.core.json_sources.read_json_object` for present JSON sidecars
  while preserving missing optional sidecars as empty evidence. Malformed or
  parseable non-object live eval artifacts now use canonical path-labelled
  source wording before runner grading, while the existing runner error
  substring remains intact for live-eval result reporting. Owner layer: Eval
  suites and live-run artifact evidence. Behavior-change class: source-reader
  consolidation / fail-aloud source validation. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  dirty `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized
  modules; this slice did not add new complexity in touched files. Proof:
  focused live-artifact source tests, existing malformed run-result live-eval
  regression test, touched-file ruff/format checks, changed-code review,
  `git diff --check`, and ratchet. Reopen only if live eval artifact sidecar
  loading regains a local raw JSON reader or corrupt present sidecars can again
  reach runner grading as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Report-server index summary loading now uses
  `roboclaws.core.json_sources.read_json_object` for present
  `run_result.json` sidecars while preserving missing sidecars as empty
  summary badges. Malformed or parseable non-object report summaries now use
  canonical path-labelled source wording instead of being silently hidden as
  missing metadata. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: current shared-checkout ratchet summary reports
  1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused
  report-server source tests, touched-file ruff/format checks, changed-code
  review, and `git diff --check`; global ratchet is blocked by unrelated dirty
  runtime bundle work. Reopen only if report-server summary loading regains a
  local raw JSON reader or corrupt `run_result.json` sidecars can again be
  treated like absent summary metadata.

- 2026-06-20: Eval suite/sample file loading now uses
  `roboclaws.core.json_sources.read_json_object` for `load_eval_suite()` and
  `load_eval_sample()` sources before schema validation. Missing, malformed,
  or parseable non-object eval suite/sample files now use canonical
  path-labelled source wording instead of raw file/parser errors or
  wrong-shaped payloads reaching schema constructors. Owner layer: Eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: current shared-checkout ratchet summary reports
  1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused eval
  model tests, touched-file ruff/format checks, changed-code review, and
  `git diff --check`; global ratchet is blocked by unrelated dirty runtime
  bundle work. Reopen only if eval suite/sample loading regains a local raw
  JSON file reader or corrupt suite/sample files can again reach schema
  validation as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Detached live-run summary sidecar readers now use
  `roboclaws.core.json_sources.read_json_object` and `read_jsonl_objects` for
  optional `live_status.json`, `live_timing.json`, `run_result.json`, and
  `trace.jsonl` sources while preserving missing sidecars as empty evidence.
  Malformed or parseable non-object sidecars now use canonical path-labelled
  source wording before summary rendering. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud source validation. Metric: current shared-checkout ratchet summary
  reports 1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused
  summarize-live-run tests, touched-file ruff/format checks, and `git diff
  --check`; global ratchet is blocked by unrelated dirty runtime bundle work.
  Reopen only if detached live-run summary sidecar loading regains local raw
  JSON/JSONL file readers or corrupt sidecars can again reach summary rendering
  as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Detached live-run summary comparison manifests now use
  `roboclaws.core.json_sources.read_json_object` before comparison-list
  validation. Missing, malformed, or parseable non-object explicit
  `--comparison-manifest` sources now use canonical path-labelled source
  wording before report-performance comparison output. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud source validation. Metric: current shared-checkout
  ratchet summary reports 1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused
  summarize-live-run tests, touched-file ruff/format checks, and `git diff
  --check`; global ratchet is blocked by unrelated dirty runtime bundle work.
  Reopen only if detached live-run comparison manifest loading regains a local
  raw JSON file reader or corrupt manifests can again reach comparison-list
  validation as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Robot-camera RGB gain profile fitting now uses
  `roboclaws.core.json_sources.read_json_object` for declared comparison
  manifests before selecting image pairs. Missing, malformed, or parseable
  non-object comparison manifests now use canonical path-labelled source
  wording before RGB gain fitting or summary writes. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud source validation. Metric: current shared-checkout
  ratchet summary reports 1 unrelated Ruff complexity row in dirty
  `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized modules;
  this slice did not add new complexity in touched files. Proof: focused RGB
  gain profile tests, touched-file ruff/format checks, and `git diff --check`;
  global ratchet is blocked by unrelated dirty runtime bundle work. Reopen only
  if RGB gain profile fitting regains a local raw JSON file reader for declared
  comparison manifests or corrupt manifests can again reach image-pair
  selection as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Grasp cache generation now uses
  `roboclaws.core.json_sources.read_json_object` for proof-bundle run manifest
  input before extracting `grasp_cache_generation_preflight`. Missing,
  malformed, or parseable non-object proof-bundle manifests now use canonical
  path-labelled source wording before generation preflight shape validation.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation / fail-aloud source validation. Metric: current
  shared-checkout ratchet summary reports 1 unrelated Ruff complexity row in
  dirty `scripts/maps/compile_b1_map12_runtime_bundle.py` and 79 oversized
  modules; this slice did not add new complexity in touched files. Proof:
  focused grasp cache generation tests, touched-file ruff/format checks, and
  `git diff --check`; global ratchet is blocked by unrelated dirty runtime
  bundle work. Reopen only if grasp cache generation regains a local raw JSON
  file reader for proof-bundle manifests or corrupt manifests can again reach
  generation preflight validation as parser tracebacks or wrong-shaped
  payloads.

- 2026-06-20: Grasp pose-policy cache loading now uses
  `roboclaws.core.json_sources.read_json_object` for initial-contact result
  artifacts before best-variant pose-policy selection. Malformed or parseable
  non-object initial-contact result files now use canonical path-labelled
  source wording before pose-policy validation. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud source validation. Metric: ratchet stayed at 0
  Ruff complexity rows and 79 oversized modules. Proof: focused grasp
  pose-policy cache tests, touched-file ruff/format checks, `git diff
  --check`, and ratchet. Reopen only if grasp pose-policy cache loading
  regains a local raw JSON file reader for initial-contact results or corrupt
  results can again reach best-variant validation as parser tracebacks or
  wrong-shaped payloads.

- 2026-06-20: Grasp generation setup now uses
  `roboclaws.core.json_sources.read_json_object` for proof-bundle run manifest
  input before extracting `grasp_cache_availability_preflight`. Missing,
  malformed, or parseable non-object proof-bundle manifests now use canonical
  path-labelled source wording before preflight shape validation. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud source validation. Metric: ratchet stayed at 0
  Ruff complexity rows and 79 oversized modules. Proof: focused grasp
  generation setup tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only if grasp generation setup regains a local raw JSON
  file reader for proof-bundle manifests or corrupt manifests can again reach
  preflight validation as parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Molmo live CI report status loading now uses
  `roboclaws.core.json_sources.read_json_object` for published `status.json`
  artifacts. Missing, malformed, or parseable non-object status files now use
  canonical path-labelled source wording before CI status schema validation,
  live manifest rows, or live index assembly. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud source validation. Metric: ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules. Proof: focused CI live report tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if Molmo live CI status loading regains a local raw JSON file reader or
  corrupt published status files can again reach schema/index logic as parser
  tracebacks or wrong-shaped payloads.

- 2026-06-20: Scene-sampler source-prep, scanner-plan, and next-flow worklist
  runner inputs now use `roboclaws.core.json_sources.read_json_object` for
  file-backed source artifacts. Missing, malformed, or parseable non-object
  `scene_sampler_source_prep.json`,
  `scene_sampler_scanner_execution_plan.json`, and
  `scene_sampler_next_flow_worklist.json` files now use canonical
  path-labelled source wording before runner schema checks, candidate
  selection, worklist alignment, or command execution. Owner layer: Artifacts,
  reports, and eval suites, with operator-console runner evidence.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules.
  Proof: focused scene-sampler source-prep and scanner runner tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if these scene-sampler runner inputs regain local raw JSON file readers
  or corrupt runner source artifacts can again reach schema/alignment logic as
  parser tracebacks or wrong-shaped payloads.

- 2026-06-20: Camera-control request loading now uses
  `roboclaws.core.json_sources.read_json_value` for file-backed request
  payloads. Missing or malformed request files now use canonical
  path-labelled source wording before camera-control request normalization,
  while legacy view-list JSON remains accepted by the existing normalizer.
  Owner layer: Backend Runtime / Environment Primitive. Behavior-change class:
  source-reader consolidation / fail-aloud source validation. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof: focused
  camera-control request loading tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  camera-control request loading regains a local raw JSON file reader or
  corrupt request files can again reach request-shape normalization as parser
  tracebacks.

- 2026-06-20: Report-performance comparison manifest loading now uses
  `roboclaws.core.json_sources.read_json_object` for explicit `--manifest`
  artifacts. Missing, malformed, or parseable non-object comparison manifests
  now use canonical path-labelled source wording before comparison-list
  validation or run-dir extraction. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: source-reader consolidation / fail-aloud
  source validation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused comparison manifest source tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if `compare_live_report_metrics.py` regains a local raw
  JSON file reader for explicit comparison manifests or corrupt manifests can
  again fall through into shape validation as wrong-typed payloads.

- 2026-06-20: Pages index rendering now uses
  `roboclaws.core.json_sources.read_json_object` for present Molmo live
  `live-report-manifest.json` sources. Missing manifests still render the
  documented household placeholder, while malformed or parseable non-object
  manifests now fail with canonical path-labelled source wording before live
  report tiles are rendered. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused Pages index source tests, existing CI live
  report index tests, core JSON-source tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if Pages index rendering
  regains a local raw JSON file reader for live report manifests or corrupt
  manifests can again be treated like empty/missing live-report state.

- 2026-06-20: Planner manipulation-probe and proof-bundle runner checker CLIs
  now use `roboclaws.core.json_sources.read_json_object` for required top-level
  source artifacts before checker assertions. Missing, malformed, or parseable
  non-object `run_result.json` / `proof_bundle_run_manifest.json` inputs now
  use canonical path-labelled source wording instead of raw file/JSON parser
  failures or wrong-shaped assertion drift. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud source validation. Metric: ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules. Proof: focused planner checker source tests,
  existing valid-path checker tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if either
  planner checker CLI regains a local raw JSON file reader or corrupt checker
  source artifacts can again reach assertion logic as wrong-shaped payloads.

- 2026-06-20: Planner-proof attachment loading now uses
  `roboclaws.core.json_sources.read_json_object` for strict proof
  `run_result.json` sources before evidence validation or proof-image copies.
  Missing, malformed, or parseable non-object proof results now use canonical
  path-labelled source wording instead of raw file/JSON parser failures.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation / fail-aloud source validation. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof: focused
  planner-proof attachment tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  planner-proof attachment loading regains a local raw JSON file reader or
  corrupt proof `run_result.json` sources can again reach strict evidence
  validation as wrong-shaped payloads.

- 2026-06-20: Compressed Agibot raw-map loading now uses
  `roboclaws.core.json_sources.read_gzip_json_object` for Map 12 consistency
  checks and Agibot Nav2 bundle export. Malformed, parseable non-object,
  missing, or non-gzip `raw_map.json.gz` sources now use canonical
  path-labelled source wording; the consistency checker records that source
  error instead of returning a generic missing-`occupancy_grid` metadata
  failure or surfacing a parser traceback. Adjacent Agibot map `source.json`
  and context-object loading in the exporter now use the shared JSON-object
  source helper too. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud source
  validation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused core JSON-source tests, Map 12 consistency
  tests, Agibot map-bundle export tests, touched-file ruff/format checks, `git
  diff --check`, and ratchet. Reopen only if Agibot raw-map source readers
  regain local gzip JSON parsing or corrupt `raw_map.json.gz` can again be
  reported as generic map metadata absence.

- 2026-06-20: Nav2 map-bundle semantics loading now routes validation,
  projection, existing-bundle snapshot, and source-frame preview reads through
  `roboclaws.core.json_sources.read_json_object` instead of local
  `json.loads(Path(...).read_text())` readers. Missing, malformed, and
  parseable non-object `semantics.json` packets now use canonical
  path-labelled source wording, and bundle validation stops at unreadable
  semantics source evidence instead of layering secondary shape errors from an
  empty substitute object. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud validation
  tightening. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused Nav2 map-bundle contract tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if Nav2 map-bundle semantics reads regain local
  JSON-object source readers or validation stops surfacing unreadable
  `semantics.json` as source evidence.

- 2026-06-20: Scene room semantic overlays now route present source-bundle
  `semantics.json` artifacts through the shared
  `roboclaws.core.json_sources.read_json_object` reader and stop fabricating
  map geometry for correspondence rows that have only a reviewed navigation
  area id. Missing `semantics.json` remains allowed for heuristic overlays, but
  malformed or parseable non-object source packets fail with path-labelled
  source errors, and geometry claims are emitted only when an override supplies
  `map_polygon` or source-room geometry exists. Owner layer: Artifacts,
  reports, and eval suites, with Backend Runtime / Environment Primitive source
  evidence. Behavior-change class: fail-aloud source-reader consolidation plus
  false-confidence geometry removal. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules. Proof: focused room semantic
  overlay tests, core JSON-source tests, touched-file ruff/format checks, `git
  diff --check`, and ratchet. Reopen only if scene room overlays regain local
  raw JSON source readers or start emitting polygon/map-center/geometry-source
  claims without explicit map geometry again.

- 2026-06-20: Runtime-map-prior file loading now uses shared
  `roboclaws.maps.runtime_prior_snapshot.read_runtime_map_prior_artifact`
  source loading for direct cleanup, household agent server, and MCP smoke
  inputs. This moves explicit prior artifact file parsing into the Runtime Map
  Prior Snapshot owner, removes three local raw
  `json.loads(Path(...).read_text())` readers, and preserves missing,
  malformed, or parseable non-object prior files as path-labelled source
  errors before raw runtime maps or prior snapshots are normalized. Owner
  layer: Artifacts, reports, and eval suites, feeding Thin Runtime / Server
  Adapters. Behavior-change class: fail-aloud source-reader consolidation.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  the existing runtime-prior contract test stayed below the oversized-module
  threshold by moving new source-error cases into a focused source-loading
  test file. Proof: focused runtime-prior contract/source tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if runtime-prior file consumers regain local raw JSON
  file readers or if runtime-prior source diagnostics stop routing through
  the Runtime Map Prior Snapshot owner.

- 2026-06-20: Goal-contract file loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit
  `--goal-contract` artifacts. This removes the launch goal reader's raw
  `json.loads(Path(...).read_text())` path for file-backed contracts and
  preserves file absence, malformed JSON, and parseable non-object failures as
  path-labelled source errors before household launch/runtime consumers
  normalize the payload. Owner layer: Runnable Surfaces And Presets, with
  handoff into Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud source-reader consolidation. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules. Proof: focused launch
  goal-contract source tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if
  `goal_contract_from_file()` stops routing explicit goal-contract file
  artifacts through the shared source helper or if inline goal-contract JSON
  needs its own accepted source-diagnostic slice.

- 2026-06-20: B1 semantic-anchor review packet and semantic projection CLI
  source loading now use the shared
  `roboclaws.core.json_sources.read_json_object` reader for review-manifest,
  alignment-artifact, and correspondence-manifest inputs. This removes both
  CLIs' duplicate local JSON-object readers while preserving concise CLI source
  errors for missing, malformed, or parseable non-object artifacts under the
  canonical helper wording. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud behavior
  preservation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the CLIs dropped to 220 and 235 lines, and the
  verified-alignment test stayed at its 2000-line ceiling without growth.
  Proof: focused B1 verified-alignment source CLI tests, core JSON-source
  tests, touched-file ruff/format checks, `git diff --check`, and ratchet.
  Reopen only if either B1 semantic CLI regains a local JSON-object source
  reader or stops routing explicit source artifacts through the shared source
  helper.

- 2026-06-20: Robot-camera visual parity summary source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for comparison,
  visual-sample, RAW-FPV run-result, prepared-USD, calibration, paired
  baseline/probe, and Isaac state artifacts. This removes the summarizer's
  duplicate local JSON-object reader while preserving concise CLI source
  errors for missing, malformed, or parseable non-object artifacts under the
  canonical helper wording. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud behavior
  preservation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; `summarize_robot_camera_visual_parity.py` dropped to 1977
  lines. Proof: focused robot-camera visual parity source tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the summarizer regains a local JSON-object source
  reader or stops routing parity summary artifacts through the shared source
  helper.

- 2026-06-20: Runtime Map Prior Snapshot conversion now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for Agibot
  `source.json` and Nav2 cleanup `semantics.json` artifacts. This removes the
  runtime prior owner's duplicate local JSON-object reader while preserving
  fail-aloud path-labelled source errors for missing, malformed, or parseable
  non-object artifacts under the canonical helper wording. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; `runtime_prior_snapshot.py`
  dropped to 1162 lines. Proof: focused Runtime Map Prior contract tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if Runtime Map Prior Snapshot conversion regains a local
  JSON-object source reader or stops routing Agibot source and Nav2 semantics
  artifacts through the shared source helper.

- 2026-06-20: B1 runtime bundle compilation now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for review-manifest,
  alignment-artifact, navigation-artifact, and semantic-projection artifacts.
  This removes the compiler's duplicate local JSON-object reader while
  preserving fail-aloud path-labelled source errors for missing, malformed, or
  parseable non-object artifacts under the canonical helper wording. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation / fail-aloud behavior preservation. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; the
  compiler dropped to 1563 lines. Proof: focused B1 runtime bundle tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the compiler regains a local JSON-object source
  reader or stops routing review/alignment/navigation/semantic-projection
  artifacts through the shared source helper.

- 2026-06-20: Codex cleanup apple-to-apple summary source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for cleanup
  run-result and sidecar agent-view artifacts. This removes the summary
  script's duplicate local JSON-object reader while preserving fail-aloud
  path-labelled source errors for missing, malformed, or parseable non-object
  artifacts under the canonical helper wording. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules. Proof: focused Codex
  cleanup apple-to-apple summary tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if the
  summary script regains a local JSON-object source reader or stops routing
  run-result and agent-view artifacts through the shared source helper.

- 2026-06-20: B1 map-scene alignment fitting now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit
  correspondence manifests. This removes the fitter's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for missing, malformed, or parseable non-object correspondence artifacts
  under the canonical helper wording. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud behavior preservation. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules. Proof: focused B1 alignment fit
  CLI tests, core JSON-source tests, touched-file ruff/format checks, `git
  diff --check`, and ratchet. Reopen only if the fitter regains a local
  JSON-object source reader or stops routing correspondence artifacts through
  the shared source helper.

- 2026-06-20: Semantic map spatial-contract normalization now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for bundle
  `semantics.json` artifacts. This removes the normalizer's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for missing, malformed, or parseable non-object semantics artifacts under
  the canonical helper wording. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: source-reader consolidation / fail-aloud
  behavior preservation. Metric: ratchet stayed at 0 Ruff complexity rows and
  79 oversized modules. Proof: focused cross-environment semantic map parity
  tests, core JSON-source tests, touched-file ruff/format checks, `git diff
  --check`, and ratchet. Reopen only if the normalizer regains a local
  JSON-object source reader or stops routing bundle semantics artifacts
  through the shared source helper.

- 2026-06-20: B1 Gaussian scene topdown capture source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for hidden
  `--camera-request` artifacts. This removes the renderer's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for missing, malformed, or parseable non-object camera-request artifacts
  under the canonical helper wording. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud behavior preservation. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules. Proof: focused B1 Gaussian
  topdown tests, core JSON-source tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if the renderer regains a
  local JSON-object source reader or stops routing hidden camera-request
  artifacts through the shared source helper.

- 2026-06-20: B1 manual-anchor semantic suggestion source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for explicit
  draft, review-manifest, and scene-diagnostic artifacts. This removes the
  CLI's duplicate local JSON-object reader while preserving fail-aloud
  path-labelled source errors for missing, malformed, or parseable non-object
  artifacts under the canonical helper wording. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules. Proof: focused B1
  manual-anchor semantic CLI tests, core JSON-source tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet. Reopen only if the CLI
  regains a local JSON-object source reader or stops routing draft,
  review-manifest, and scene-diagnostic artifacts through the shared source
  helper.

- 2026-06-20: B1 correspondence review source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit
  correspondence manifests and required scene topdown render packets. This
  removes the renderer's duplicate local JSON-object reader while preserving
  fail-aloud path-labelled source errors for missing, malformed, or parseable
  non-object artifacts under the canonical helper wording. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the renderer dropped from
  948 to 937 lines. Proof: focused B1 correspondence review tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the renderer regains a local JSON-object source
  reader or stops routing correspondence/scene-topdown artifacts through the
  shared source helper.

- 2026-06-20: B1 waypoint pose request source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for required alignment
  artifacts. This removes the builder's duplicate local JSON-object reader
  while preserving fail-aloud path-labelled source errors for missing,
  malformed, or parseable non-object alignment artifacts under the canonical
  helper wording. The `--points` JSON-array reader stays local because the
  shared helper intentionally covers JSON-object and JSONL sources. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  source-reader consolidation / fail-aloud behavior preservation. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; the
  builder dropped from 359 to 348 lines. Proof: focused B1 waypoint pose
  request tests, core JSON-source tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if the builder regains a local
  JSON-object source reader for alignment artifacts or stops routing alignment
  artifacts through the shared source helper.

- 2026-06-20: B1 navigation report source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for the required
  navigation artifact plus explicit optional readiness and waypoint pose
  request artifacts. This removes the report renderer's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for missing, malformed, or parseable non-object artifacts under the
  canonical helper wording. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud behavior
  preservation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the report renderer dropped from 644 to 633 lines.
  Proof: focused B1 navigation report tests, core JSON-source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if the report renderer regains a local JSON-object source reader or
  stops routing navigation/readiness/waypoint request artifacts through the
  shared source helper.

- 2026-06-20: B1 digital-twin readiness source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit alignment
  artifacts and navigation smoke artifacts. This removes the readiness
  script's duplicate local JSON-object reader while preserving fail-aloud
  path-labelled source errors for missing, malformed, or parseable non-object
  artifacts under the canonical helper wording. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the readiness script
  dropped from 1335 to 1324 lines. Proof: focused B1 readiness tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the readiness script regains a local JSON-object
  source reader or stops routing explicit alignment/navigation artifacts
  through the shared source helper.

- 2026-06-20: B1 navigation smoke source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit readiness
  artifacts and waypoint pose request artifacts. This removes the smoke
  script's duplicate local JSON-object reader while preserving fail-aloud
  path-labelled source errors for missing, malformed, or parseable non-object
  artifacts under the canonical helper wording. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the navigation smoke script
  dropped from 466 to 455 lines. Proof: focused B1 navigation smoke tests,
  core JSON-source tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only if the smoke script regains a local JSON-object
  source reader or stops routing explicit readiness/waypoint request artifacts
  through the shared source helper.

- 2026-06-20: B1 asset visual comparison source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for explicit
  baseline/candidate navigation artifacts. This removes the comparison
  script's duplicate local JSON-object reader while preserving fail-aloud
  path-labelled source errors for missing, malformed, or parseable non-object
  navigation artifacts under the canonical helper wording. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the comparison script
  dropped from 463 to 451 lines. Proof: focused B1 asset visual comparison
  tests, core JSON-source tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if the comparison script
  regains a local JSON-object source reader or stops routing explicit
  baseline/candidate navigation artifacts through the shared source helper.

- 2026-06-20: Visual-grounding benchmark run source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for declared
  corpus and matrix JSON-object artifacts. This removes the runner's duplicate
  local JSON-object parser while preserving no-traceback CLI behavior for
  missing, malformed, or parseable non-object corpus/matrix inputs under the
  canonical helper wording. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud behavior
  preservation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the runner stayed at 1291 lines because the parser became
  a tiny CLI-boundary wrapper. Proof: focused visual-grounding benchmark
  source tests, visual-grounding benchmark contract tests, core JSON-source
  tests, touched-file ruff/format checks, `git diff --check`, and ratchet.
  Reopen only if the runner regains a local JSON parser or stops routing
  declared corpus/matrix JSON-object artifacts through the shared source
  helper.

- 2026-06-20: Visual-grounding cleanup-run corpus source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for declared
  cleanup `run_result.json` artifacts. This removes the corpus builder's
  duplicate local JSON-object reader while preserving fail-aloud no-traceback
  CLI behavior for malformed or parseable non-object run-result artifacts
  under the canonical helper wording. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud behavior preservation. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; the builder dropped from 367 to
  359 lines. Proof: focused visual-grounding corpus-builder tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the builder regains a local JSON-object source
  reader or stops routing declared cleanup run-result artifacts through the
  shared source helper.

- 2026-06-20: Prepared semantic USD summary source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for the
  explicit summary artifact. This removes the checker's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for malformed, missing, or parseable non-object summary artifacts under the
  canonical helper wording. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation / fail-aloud behavior
  preservation. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the checker dropped from 68 to 55 lines. Proof: focused
  prepared-summary tests, core JSON-source tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only if the checker regains
  a local JSON-object source reader or stops routing the explicit summary
  artifact through the shared source helper.

- 2026-06-20: MolmoSpaces apple-to-apple grid source loading now uses the
  shared `roboclaws.core.json_sources.read_json_object` reader for existing
  `apple2apple_test_grid.json` manifests and detached live `live_status.json`
  polling. This removes the runner's duplicate local JSON-object reader while
  preserving fail-aloud path-labelled source errors for malformed or parseable
  non-object artifacts and preserving the small retry window for transient
  live-status partial writes. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: source-reader consolidation / fail-aloud
  behavior preservation. Metric: ratchet stayed at 0 Ruff complexity rows and
  79 oversized modules; the grid runner dropped from 371 to 356 lines. Proof:
  focused apple-to-apple grid tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only if the runner regains a local
  JSON-object source reader or stops routing explicit JSON-object artifacts
  through the shared source helper.

- 2026-06-20: Planner-proof bundle source loading now uses the shared
  `roboclaws.core.json_sources.read_json_object` reader for cleanup
  `run_result.json`, declared `planner_proof_requests.json`, prior
  `proof_bundle_run_manifest.json`, and standalone prior probe
  `run_result.json` inputs. This removes the runner's duplicate local
  JSON-object reader while preserving fail-aloud path-labelled source errors
  for malformed or parseable non-object artifacts. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: source-reader
  consolidation / fail-aloud behavior preservation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the planner-proof bundle
  runner dropped from 876 to 866 lines. Proof: focused planner-proof source
  tests, touched-file ruff/format checks, `git diff --check`, changed-code
  review, and ratchet. Reopen only if the runner regains a local JSON-object
  source reader or stops routing explicit JSON-object artifacts through the
  shared source helper.

- 2026-06-20: Planner-proof bundle prior inputs now treat explicit prior
  `proof_bundle_run_manifest.json` files and standalone prior probe
  `run_result.json` files as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Malformed or parseable
  non-object prior artifacts now fail with path-labelled source errors before
  prior-memory merge or proof-request selection, instead of surfacing raw
  parser/type failures or being folded into misleading empty prior evidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud planner-proof prior-source validation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; focused source coverage
  landed in a small new test file instead of growing the 1900-line runner test.
  Proof: focused prior-source tests, existing prior-manifest success tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet. Reopen only with fresh planner-proof bundle evidence that
  malformed or non-object prior proof-bundle manifests or standalone prior
  probe run results again reach prior-memory merge or selection as plausible
  prior evidence.

- 2026-06-20: Cleanup checker trace JSONL loading now treats `trace.jsonl`
  rows as object-typed source truth through
  `roboclaws.core.json_sources.read_jsonl_objects`. Malformed or parseable
  non-object trace rows now fail with path-and-line-labelled source errors
  before public-trace privacy checks or duplicate post-place navigation checks
  can use partial trace evidence. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud cleanup-checker trace source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules; the checker dropped from 2005 to 2000 lines while focused
  trace-source coverage landed in a small source-test file. Proof: focused
  core JSON-source tests, focused checker trace-source tests, existing
  duplicate-navigation trace tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with fresh
  cleanup-checker evidence that malformed or non-object `trace.jsonl` rows
  again surface raw parser/type failures or allow partial trace evidence into
  privacy or duplicate-navigation validation.

- 2026-06-20: Cleanup checker Isaac scene-index map-context semantics loading
  now treats declared `semantics_json` evidence as JSON-object source truth
  through `roboclaws.core.json_sources.read_json_object`. Missing, malformed,
  or parseable non-object scene-index Nav2 semantics artifacts now fail with
  path-labelled source errors before map-context validation, instead of
  surfacing raw assertion/parser/type failures or wrong-shaped semantics
  packets. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud cleanup-checker scene-index semantics source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  the checker dropped by another line while focused scene-index source
  coverage landed in a small source-test file. Proof: focused scene-index
  source tests, existing scene-index map-context tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh cleanup-checker evidence that missing, malformed, or
  non-object scene-index Nav2 semantics artifacts again produce raw
  assertion/parser/type failures or reach map-context validation as plausible
  semantics evidence.

- 2026-06-20: Cleanup checker B1 robot-consumption semantics loading now
  treats declared `semantics_json` evidence as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  parseable non-object B1 Nav2 semantics artifacts now fail with path-labelled
  source errors before robot-consumption proof validation, instead of
  surfacing raw assertion/parser/type failures or wrong-shaped semantics
  packets. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud cleanup-checker B1 semantics source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules; the checker
  dropped by another line while focused B1 source coverage stayed in the small
  source-test file. Proof: focused B1 source tests, affected B1 checker tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet. Reopen only with fresh cleanup-checker evidence that missing,
  malformed, or non-object B1 Nav2 semantics artifacts again produce raw
  assertion/parser/type failures or reach robot-consumption proof validation
  as plausible semantics evidence.

- 2026-06-20: Cleanup checker B1 robot-consumption manifest loading now treats
  `b1_robot_consumption_manifest.json` as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  parseable non-object manifests now fail with path-labelled source errors
  before readiness validation, instead of surfacing raw file-read or
  parser/type failures. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud cleanup-checker B1 manifest source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  the checker dropped by another line while focused B1 source coverage landed
  in a small source-test file. The existing oversized checker contract test
  grew only to update the affected missing-manifest expectation to the new
  source-error behavior. Proof: focused B1 manifest source tests, affected B1
  checker tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh cleanup-checker
  evidence that malformed or missing B1 robot-consumption manifests again
  produce raw file/parser/type failures or reach readiness validation as
  plausible manifest evidence.

- 2026-06-20: Cleanup checker advisory-scoring artifact loading now treats
  declared advisory-evaluation evidence as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  parseable non-object advisory artifacts now fail with path-labelled source
  errors before advisory validation, instead of surfacing raw file-read or
  parser/type failures. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud cleanup-checker advisory artifact source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules; the checker dropped by another line while focused coverage stayed
  in the small checker source-test file. Proof: focused checker source tests,
  adjacent planner-proof source tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with
  fresh cleanup-checker evidence that malformed declared advisory artifacts
  again produce raw file/parser/type failures or reach advisory validation as
  plausible artifact evidence.

- 2026-06-20: Cleanup checker goal-contract artifact loading now treats
  declared `goal_contract.json` evidence as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  parseable non-object goal-contract artifacts now fail with path-labelled
  source errors before contract comparison, instead of surfacing raw file-read
  or parser/type failures. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud cleanup-checker goal-contract artifact
  source truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the checker dropped by one line while focused coverage
  stayed in the small checker source-test file. Proof: focused checker source
  tests, adjacent planner-proof source tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with
  fresh cleanup-checker evidence that malformed declared goal-contract
  artifacts again produce raw file/parser/type failures or reach contract
  comparison as plausible artifact evidence.

- 2026-06-20: Cleanup checker top-level `run_result.json` loading now treats
  single-file inputs, `seed-*` directories, and run-directory fallback inputs
  as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Malformed or parseable
  non-object run-result sources now fail with path-labelled source errors
  before checker assertions, instead of surfacing raw parser tracebacks or
  allowing wrong-shaped packets into downstream validation. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  cleanup-checker run-result source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; focused coverage landed in a new
  small checker source-test file instead of growing the already oversized
  checker contract module. Proof: focused checker run-result source tests,
  adjacent planner-proof source tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with
  fresh cleanup-checker evidence that malformed top-level run-result sources
  again produce raw parser/type failures or enter checker assertions as
  plausible result evidence.

- 2026-06-20: Scene-sampler room-label manifest loading now treats the
  prepared label manifest as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object` before schema/admission
  validation. Malformed or parseable non-object manifests now fail with
  path-labelled source errors instead of parser tracebacks or wrong-layer
  shape errors. Owner layer: Runnable Surfaces And Presets plus Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud scene-sampler
  admission source truth. Metric: ratchet stayed at 0 Ruff complexity rows and
  79 oversized modules. Proof: focused scene sampler tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh scene-sampler evidence that malformed room-label
  manifests again surface raw parser/type errors or pass into schema/admission
  validation as plausible label evidence.

- 2026-06-20: Codex operator-handoff terminal-phase polling now treats present
  `live_status.json` as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Malformed or parseable
  non-object status sources now fail aloud instead of collapsing to an empty
  phase and allowing generic operator-handoff failure handling to overwrite or
  hide corrupt live-status context. Owner layer: Agent Engines And Provider
  Profiles plus Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud Codex live-status source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules. Proof: focused Codex live report
  tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh operator-handoff
  evidence that malformed present `live_status.json` again becomes an empty
  phase or a generic missing-run-result failure.

- 2026-06-20: Codex live timing now treats present `run_result.json` as
  JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object` before deriving MCP timing.
  Malformed or parseable non-object run-result timing sources now fail the
  final `live_timing.json` packet with `live_timing_source_error` instead of
  silently falling back to trace-derived MCP timing evidence. Owner layer:
  Agent Engines And Provider Profiles plus Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud Codex live timing source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules.
  Proof: focused Codex live report tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with
  fresh Codex live timing evidence that malformed present `run_result.json`
  again falls back to trace timing or writes a passing final timing packet.

- 2026-06-20: B1 operator-console scene previews now treat existing
  `b1-map12-preview.json` metadata and declared camera artifacts as
  JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Malformed or parseable
  non-object skip-existing metadata now returns a concise
  `metadata_unreadable` result without rewriting metadata or deleting
  companion preview images, and malformed or non-object camera artifacts now
  surface `artifact_unreadable` inside the existing
  `camera_preview_unavailable` packet instead of returning raw parser/type
  failures or silently substituting an empty preview packet. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  operator-console B1 preview source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; focused coverage landed in a new
  small source-test file instead of growing the already oversized preview test
  module. Proof: focused B1 preview source tests, existing preview behavior
  tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh B1 preview evidence
  that corrupt existing metadata is overwritten/deletes previews, or malformed
  camera artifacts again produce raw parser/type failures or plausible current
  preview evidence.

- 2026-06-20: The cleanup checker now treats declared planner-proof request
  artifacts as JSON-object source truth through
  `roboclaws.core.json_sources.read_json_object`. Missing, malformed, or
  parseable non-object declared request manifests now fail with concise
  path-labelled source errors before report/checker validation, instead of
  surfacing raw parser tracebacks or generic assertion failures. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  cleanup-checker planner-proof request source truth. Metric: ratchet stayed
  at 0 Ruff complexity rows and 79 oversized modules; the already-over-limit
  checker did not move up the oversized list because the JSON-object source
  guard lives in a shared core helper. Proof: focused cleanup-checker source
  tests, shared JSON-source helper tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh cleanup-checker
  evidence that corrupt or missing declared planner-proof request manifests
  again produce raw JSON/type/assertion failures or pass into report validation
  as plausible request evidence.

- 2026-06-20: Planner-proof bundle generation now treats cleanup
  `run_result.json`, inline `planner_proof_requests`, the cleanup `artifacts`
  envelope, and declared `planner_proof_requests.json` artifacts as explicit
  source truth. Malformed or parseable non-object cleanup run results, inline
  request packets, artifact envelopes, and declared request artifacts now fail
  before bundle generation, and declared-but-missing request artifacts raise
  source-path errors instead of disappearing into generic missing-request
  behavior. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud planner-proof bundle request source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof: focused
  planner-proof bundle tests, touched-file ruff/format checks, `git diff
  --check`, and ratchet. Reopen only with fresh planner-proof bundle evidence
  that malformed cleanup run results, wrong-shaped inline/artifact request
  sources, or missing declared request artifacts again produce raw
  parser/type/assertion failures, write bundle outputs after source-load
  failure, or hide declared request-source errors as generic missing-request
  packets.

- 2026-06-20: Agent SDK speedup matrix manifests now require a non-empty
  `rows` array whose entries are JSON objects. Missing, empty, non-array, or
  wrong-shaped row sources now fail at manifest load before dry-run or
  offline-preflight packet generation, instead of producing successful zero-row
  matrix evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud Agent SDK speedup-matrix manifest source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules. Proof: focused Agent SDK perf-matrix tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh speedup-matrix evidence that wrong-shaped manifest
  rows again produce a successful dry-run/preflight packet or hide missing
  decision-row evidence as an intentional zero-row matrix.

- 2026-06-20: Codex cleanup apple-to-apple summaries now treat declared
  `run_result.json`, present `agent_view.json`, and embedded
  `run_result.agent_view` packets as object-typed source truth. Malformed or
  parseable non-object source packets now raise concise path-labelled errors
  before comparison manifest/report writes, instead of surfacing raw
  parser/type failures or turning wrong-shaped embedded agent views into empty
  worklists. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud Codex cleanup apple-to-apple source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules. Proof: focused Codex cleanup apple-to-apple summary tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet. Reopen only with fresh Codex cleanup apple-to-apple evidence
  that malformed or non-object run-result/agent-view sources again produce
  tracebacks, write comparison outputs after source-load failure, or fabricate
  empty agent-view/worklist evidence from wrong-shaped source packets.

- 2026-06-20: Visual-grounding cleanup-run corpus building now treats the
  declared `run_result.json` as object-typed source truth. Malformed or
  parseable non-object cleanup run-result sources now return concise builder
  errors before corpus artifact writes, instead of surfacing raw parser/type
  tracebacks. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud visual-grounding corpus-builder source
  truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused visual-grounding corpus-builder contract
  tests, touched-file ruff/format checks, `git diff --check`, and ratchet.
  Reopen only with fresh corpus-builder evidence that malformed or non-object
  declared cleanup `run_result.json` inputs again produce tracebacks or write
  corpus outputs after source-load failure.

- 2026-06-20: Visual-grounding benchmark runs now treat declared `--corpus`
  and `--matrix` inputs as source truth. Missing, malformed, or parseable
  non-object corpus/matrix JSON and wrong-shaped matrix row sources now return
  concise runner source errors before benchmark artifact writes, instead of
  surfacing raw file/parser/type tracebacks. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud visual-grounding
  benchmark input source truth. Metric: staged/add-N ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; coverage landed in a small
  dedicated runner-source contract test file instead of expanding the existing
  visual-grounding benchmark contract file. Proof: focused visual-grounding
  benchmark runner/contract tests, touched-file ruff/format checks, `git diff
  --check`, and ratchet. Reopen only with fresh benchmark-runner evidence that
  malformed or wrong-shaped declared corpus/matrix inputs again produce
  tracebacks or write benchmark outputs after source-load failure.

- 2026-06-20: Visual-grounding benchmark result checks now treat
  `visual_grounding_benchmark_result.json` and
  `visual_grounding_predictions.jsonl` as object-typed source truth.
  Malformed or parseable non-object result JSON and prediction JSONL rows now
  return concise checker source errors instead of surfacing raw parser/type
  tracebacks. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud visual-grounding benchmark artifact source
  truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; coverage landed in a small dedicated checker-source
  contract test file instead of expanding the existing visual-grounding
  benchmark contract test toward the oversized threshold. Proof: focused
  visual-grounding benchmark checker/contract tests, touched-file ruff/format
  checks, `git diff --check`, and ratchet. Reopen only with fresh
  visual-grounding checker evidence that malformed or non-object declared
  result/prediction artifacts again produce tracebacks or pass into deeper
  validation as plausible benchmark evidence.

- 2026-06-20: Nav2 map-bundle export now treats missing explicit
  `--agent-view` and `--run-result` sources as source-path errors before
  bundle writes. This extends the existing malformed/non-object exporter
  source guard so absent declared inputs no longer surface as raw file-read
  tracebacks or create partial output directories. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud map/export
  source truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows
  and 79 oversized modules. Proof: focused Nav2 map-bundle contract tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only with fresh exporter evidence that missing declared agent-view or
  run-result sources again read through raw file paths or write bundle outputs
  after source-load failure.

- 2026-06-20: Nav2 map-bundle export now routes explicit `--agent-view` and
  `--run-result` JSON-object source files through
  `roboclaws.core.json_sources.read_json_object`, with a small CLI wrapper that
  preserves no-traceback exits. This removes the exporter's duplicate local
  JSON reader and brings missing, malformed, and parseable non-object exporter
  source diagnostics under the canonical path-labelled wording before bundle
  writes or agent-view extraction. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: source-reader consolidation / fail-aloud
  behavior preservation. Metric: ratchet stayed at 0 Ruff complexity rows and
  79 oversized modules. Proof: focused Nav2 map-bundle contract tests, core
  JSON-source tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only if the exporter regains a local JSON-object source
  reader or stops routing declared agent-view/run-result file sources through
  the shared source helper.

- 2026-06-20: B1 manual-draft verification promotion and semantic
  review-packet promotion now route their explicit draft/review-packet
  JSON-object sources through `roboclaws.core.json_sources.read_json_object`
  instead of local duplicate readers. Existing CLI return codes and
  no-traceback behavior stay intact through the scripts' local exception
  wrappers, while missing, malformed, and parseable non-object source errors
  use the canonical path-labelled wording. The verified-alignment contract's
  scene top-down missing-source assertion was also aligned with the shared
  helper wording already used by that owner. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: source-reader consolidation /
  fail-aloud behavior preservation. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; the verified-alignment contract
  stayed at its 2000-line ceiling. Proof: focused B1 verified-alignment tests,
  core JSON-source tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only if the promotion CLIs regain local JSON-object
  readers or stop routing explicit draft/review-packet file sources through
  the shared source helper.

- 2026-06-20: Semantic map spatial-contract normalization now treats bundle
  `semantics.json` as JSON-object source truth before in-place writes. Missing,
  malformed, or parseable non-object semantics sources now return concise CLI
  source-path errors instead of raw parser/type tracebacks, and the
  cross-environment parity test now reflects the current seven accepted B1
  geometry-only alignment anchors with blank semantic ids. Owner layer:
  Backend Runtime / Environment Primitive and Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud map-bundle source truth plus stale
  test-truth refresh. Metric: staged/add-N ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules. Proof: focused cross-environment semantic-map
  parity tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only with fresh normalizer evidence that `semantics.json`
  again loads through raw parser/type paths or writes after source-load
  failure, or with current B1 manifest evidence contradicting the accepted
  seven-anchor alignment contract.

- 2026-06-20: B1 asset visual comparisons now treat explicit
  `--baseline-navigation` and `--candidate-navigation` artifacts as
  JSON-object source truth. Missing, malformed, or parseable non-object
  navigation artifacts now return concise CLI source-path errors before
  writing comparison outputs, instead of surfacing raw parser/type failures or
  deriving same-pose visual comparison packets from corrupt evidence. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud B1 asset visual comparison source truth. Metric: staged/add-N
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules. Proof:
  focused asset-comparison CLI source tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh asset-comparison
  evidence that explicit baseline or candidate navigation artifacts again load
  through raw parser/type paths, accept plausible non-object packets, or write
  comparison outputs after source-load failure.

- 2026-06-20: Prepared semantic USD summary validation now treats the explicit
  summary path as JSON-object source truth. Missing, malformed, or parseable
  non-object summary sources now return concise CLI source-path errors before
  reporting readiness, instead of surfacing raw parser/type failures or
  assertion-only tracebacks. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud prepared semantic USD summary source
  truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused prepared-summary CLI source tests, existing
  prepared-summary assertion tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh prepared-summary
  evidence that explicit summary artifacts again load through raw parser/type
  paths or report readiness after source-load failure.

- 2026-06-20: Isaac segmentation AOV comparisons now treat explicit
  `--control-state` and `--candidate-state` artifacts as JSON-object source
  truth. Missing, malformed, or parseable non-object state artifacts now return
  concise CLI source-path errors before writing comparison outputs, instead of
  surfacing raw parser/type failures or producing plausible comparison packets
  from corrupt evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud Isaac AOV comparison source truth. Metric:
  staged/add-N ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules. Proof: focused AOV comparison CLI source tests, existing AOV
  comparison/matrix tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only with fresh AOV comparison evidence that explicit
  control or candidate artifacts again load through raw parser/type paths,
  accept plausible non-object packets, or write comparison outputs after
  source-load failure.

- 2026-06-20: Isaac segmentation AOV matrix summaries now treat explicit
  `--entry LABEL=PATH` artifacts as JSON-object source truth. Missing,
  malformed, or parseable non-object entry artifacts now return concise CLI
  source-path errors before writing matrix outputs, instead of surfacing raw
  parser/type failures or producing plausible decision packets from corrupt
  evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud Isaac AOV matrix source truth. Metric:
  staged/add-N ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules. Proof: focused AOV matrix CLI source tests, existing AOV comparison
  tests, touched-file ruff/format checks, `git diff --check`, and ratchet.
  Reopen only with fresh AOV matrix evidence that explicit entry artifacts
  again load through raw parser/type paths, accept plausible non-object
  packets, or write matrix outputs after source-load failure.

- 2026-06-20: B1 digital-twin readiness now treats explicit
  `--alignment-artifact` and `--navigation-artifact` inputs as JSON-object
  source truth. Missing, malformed, or parseable non-object optional proof
  artifacts now return concise CLI source-path errors before writing the
  readiness artifact, instead of surfacing raw parser/type failures or merging
  plausible readiness evidence from corrupt sources. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud B1 readiness
  source truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows
  and 79 oversized modules; coverage landed in a small dedicated readiness CLI
  contract test file. Proof: focused readiness CLI source tests, existing B1
  digital-twin readiness contract tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh B1 readiness
  evidence that explicit alignment or navigation artifacts again load through
  raw parser/type paths, accept plausible non-object packets, or write
  readiness artifacts after source-load failure.

- 2026-06-20: B1 manual alignment overlay rendering now treats explicit
  `--scene-topdown-render` and `--alignment-artifact` inputs as JSON-object
  source truth. Missing, malformed, or parseable non-object scene top-down
  render packets and alignment artifacts now return concise CLI source-path
  errors before writing `map12_on_gaussian_topdown.json` or preview images,
  instead of surfacing raw parser/type failures or publishing plausible overlay
  evidence from corrupt sources. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud B1 manual-overlay source truth.
  Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; coverage landed in a small dedicated manual-overlay CLI
  contract test file instead of expanding the 2000-line B1 alignment
  hard-ceiling test. Proof: focused manual-overlay CLI source tests, selected
  existing overlay transform test, touched-file ruff/format checks, and
  ratchet. Reopen only with fresh B1 manual-overlay evidence that explicit
  topdown or alignment artifacts again load through raw parser/type paths,
  accept plausible non-object packets, or write overlay artifacts after
  source-load failure.

- 2026-06-20: B1 map-scene alignment fitter CLI loading now treats explicit
  `--correspondences` input as JSON-object source truth. Missing, malformed,
  or parseable non-object correspondence manifests now return concise CLI
  source-path errors before writing `alignment_residuals.json` or preview
  artifacts, instead of surfacing raw parser/type failures or producing
  plausible alignment packets from corrupt evidence. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud B1 alignment
  fitter source truth. Metric: staged/add-N ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; coverage landed in a small
  dedicated alignment-fit CLI contract test file instead of expanding the
  2000-line B1 alignment hard-ceiling test. Proof: focused alignment-fit CLI
  source tests, selected existing B1 alignment fitter tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh B1 alignment-fit evidence that explicit
  correspondences are again loaded through raw parser/type paths, accepted as
  plausible non-object packets, or allowed to write artifacts after source-load
  failure.

- 2026-06-20: B1 correspondence review rendering now treats explicit
  `--correspondences` and `--scene-topdown-render` inputs as JSON-object
  source truth. Missing, malformed, or parseable non-object correspondence
  manifests and scene top-down render packets now return concise CLI
  source-path errors before writing `correspondence_review_packet.json` or
  `correspondence_review.html`, instead of surfacing raw parser/type failures
  or publishing plausible review packets from corrupt evidence. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud B1
  correspondence review source truth. Metric: staged/add-N ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; coverage landed in a small
  dedicated correspondence-review CLI contract test file instead of expanding
  the 2000-line B1 alignment hard-ceiling test. Proof: focused
  correspondence-review CLI source tests, selected existing B1
  correspondence-review tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet. Reopen only with fresh B1
  correspondence-review evidence that explicit correspondences or topdown
  render packets are again loaded through raw parser/type paths, accepted as
  plausible non-object packets, or allowed to write artifacts after source-load
  failure.

- 2026-06-20: Robot-camera visual parity summary CLI loading now treats
  explicit baseline/probe manifests, RAW-FPV run results, calibration
  manifests, prepared USD summaries, paired comparison manifests, report
  visual sample manifests, and nested RGB-gain source manifests as JSON-object
  source truth. Missing declared optional sources, malformed JSON, and
  parseable non-object source packets now return concise CLI/source errors
  before writing `visual_parity_summary.json` or `report.html`, instead of
  surfacing raw parser/type failures or publishing plausible parity reports
  from corrupt evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud visual-parity report source truth. Metric:
  staged/add-N ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules; the visual-parity summary script remained in existing warning-band
  debt at 1988 lines, and coverage landed in a small dedicated source-error
  unit test file instead of expanding the 2262-line visual-parity regression
  test. Proof: focused visual-parity source tests, selected existing
  visual-parity regression tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet. Reopen only with fresh
  visual-parity summary evidence that explicit report/calibration/prepared/USD
  or nested source manifests are again loaded through raw parser/type paths,
  accepted as plausible non-object packets, or allowed to write artifacts
  after source-load failure.

- 2026-06-20: B1 manual-anchor semantic suggestion CLI loading now treats
  `--draft`, `--review-manifest`, and `--scene-diagnostic` inputs as
  JSON-object source truth. Missing, malformed, or parseable non-object source
  packets now return concise CLI source-path errors before writing semantic
  suggestions, semantic review packets, or HTML review reports, instead of
  surfacing raw file/parser/type failures or rereading draft state for the
  review packet. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 manual-anchor semantic suggestion
  source truth. Metric: staged/add-N ratchet stayed at 0 Ruff complexity rows
  and 79 oversized modules; coverage landed in a small dedicated CLI contract
  test file instead of adding to the 2000-line B1 alignment hard-ceiling test.
  Proof: focused manual-anchor semantic CLI tests, existing manual-anchor
  semantic alignment tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet. Reopen only with fresh
  manual-anchor semantic suggestion evidence that draft/review/scene sources
  are again loaded through raw parser/type paths, accepted as plausible
  non-object packets, reread inconsistently between outputs, or allowed to
  write artifacts after source-load failure.

- 2026-06-20: B1 navigation report rendering now treats
  `navigation_smoke.json`, explicitly supplied `--readiness-artifact` /
  `--waypoint-pose-requests`, and present default readiness/waypoint request
  sidecars as JSON-object source truth. Missing explicit optional artifacts,
  malformed required navigation artifacts, malformed present default sidecars,
  and parseable non-object waypoint request artifacts now return concise
  source-path errors before `report.html` writes, instead of silently omitting
  corrupt report evidence or surfacing raw parser/type paths. The no-sidecar
  default remains a deliberate report mode only when those optional files are
  absent and not explicitly requested. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud B1 navigation report source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules; report coverage stayed in the small navigation-report contract test
  file instead of the 2000-line B1 alignment hard-ceiling test. Proof: focused
  navigation-report tests, adjacent B1 readiness/report contract tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet. Reopen only with fresh navigation-report evidence that explicit
  optional artifacts or present sidecars are again loaded through raw
  parser/type paths, accepted as plausible non-object packets, silently
  omitted, or allowed to write reports after source-load failure.

- 2026-06-20: B1 navigation smoke now treats explicit
  `--readiness-artifact` and `--waypoint-pose-requests` inputs as source truth.
  Missing, malformed, or parseable non-object readiness or waypoint request
  artifacts return concise source-path errors before `navigation_smoke.json`
  writes, instead of surfacing raw parser/type failures or writing plausible
  blocked navigation artifacts from corrupt source evidence. Schema-valid
  blocked waypoint request artifacts still produce blocked navigation evidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud B1 navigation smoke source truth. Metric: ratchet stayed at 0
  Ruff complexity rows and 79 oversized modules; coverage landed in a small
  dedicated navigation-smoke CLI contract test file instead of adding to the
  2000-line B1 alignment hard-ceiling test. Proof: focused navigation smoke
  CLI tests, existing B1 verified-alignment contract tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh navigation smoke evidence that explicit readiness or
  waypoint request artifacts are again loaded through raw parser/type paths,
  accepted as plausible non-object packets, or allowed to write artifacts after
  source-load failure.

- 2026-06-20: B1 Map 12 waypoint pose request building now treats required
  `--alignment-artifact` input and explicit `--points` input as source truth.
  Missing, malformed, or parseable wrong-shaped alignment artifacts and points
  files return concise source-path errors before `waypoint_pose_requests.json`
  writes, instead of surfacing raw parser/type failures or writing plausible
  blocked pose-request artifacts from absent/corrupt source evidence. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud B1 waypoint pose request source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; coverage landed in a small
  dedicated CLI contract test file instead of adding to the 2000-line B1
  alignment hard-ceiling test. Proof: focused waypoint pose request CLI tests,
  existing B1 verified-alignment contract tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet. Reopen only
  with fresh waypoint pose request evidence that explicit alignment or points
  sources are again loaded through raw parser/type paths, accepted as plausible
  wrong-shaped packets, or allowed to write artifacts after source-load
  failure.

- 2026-06-20: B1 Gaussian scene topdown capture now treats the hidden explicit
  `--camera-request` input as JSON-object source truth. Malformed or parseable
  non-object camera-request packets return concise source-path errors before
  Isaac capture or `capture_result.json` writes, instead of surfacing raw
  parser/type failures or passing wrong-shaped request evidence into the
  capture worker. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 scene camera-request source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  coverage landed in the small Gaussian topdown contract test file. Proof:
  focused B1 scene Gaussian topdown contract tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet. Reopen only
  with fresh Gaussian topdown capture evidence that explicit camera-request
  packets are again loaded through raw parser/type paths, accepted as
  plausible non-object packets, or allowed to write capture artifacts after
  source-load failure.

- 2026-06-20: B1 scene topdown diagnostic overlay loading now treats explicit
  `--scene-topdown-render` input as JSON-object source truth. Malformed or
  parseable non-object render packets return concise source-path errors before
  schema validation or overlay report writes, instead of surfacing raw
  parser/type failures from wrong-shaped Gaussian topdown evidence. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud B1 scene topdown render source truth. Metric: ratchet stayed at 0
  Ruff complexity rows and 79 oversized modules; coverage landed in the small
  topdown diagnostic contract test file instead of the B1 alignment hard
  ceiling test. Proof: focused B1 scene topdown diagnostic contract tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet. Reopen only with fresh scene-topdown diagnostic evidence that
  explicit Gaussian topdown render packets are again loaded through raw
  parser/type paths, accepted as plausible non-object packets, or allowed to
  write overlay artifacts after source-load failure.

- 2026-06-20: B1 scene topdown diagnostic overlay loading now routes explicit
  `--scene-topdown-render` JSON-object packets through
  `roboclaws.core.json_sources.read_json_object` instead of a local duplicate
  reader. Missing, malformed, and parseable non-object Gaussian topdown packets
  keep failing before schema validation or overlay writes, now with the
  canonical path-labelled source wording shared by adjacent scene-topdown
  consumers. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: source-reader consolidation / fail-aloud behavior preservation.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  `render_b1_scene_topdown_diagnostic.py` dropped from 884 to 876 lines. Proof:
  focused B1 scene topdown diagnostic tests, core JSON-source tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only if the diagnostic regains a local JSON-object source reader or stops
  routing explicit Gaussian topdown render packets through the shared source
  helper.

- 2026-06-20: B1 Map 12 manual-draft verification promotion CLI loading now
  treats explicit `--draft` input as JSON-object source truth. Missing,
  malformed, or parseable non-object draft packets return concise CLI
  source-path errors and do not write verification-only correspondence
  manifests, instead of surfacing raw file/parser/type failures before draft
  promotion. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 manual draft source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; the
  touched B1 alignment test stayed at the 2000-line hard-ceiling boundary
  after local table compaction. Proof: focused B1 manual-draft promotion
  contract tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh manual-draft
  promotion CLI evidence that explicit drafts are again loaded through raw
  parser/type paths, accepted as plausible non-object packets, or allowed to
  write verification-only artifacts after source-load failure.

- 2026-06-20: B1 Map 12 semantic review packet promotion and fit-check CLI
  loading now treats explicit `--review-packet` inputs as JSON-object source
  truth. Missing, malformed, or parseable non-object review packets return
  concise CLI source-path errors and do not write promoted correspondence,
  preview, or residual artifacts, instead of surfacing raw file/parser/type
  failures before promotion or fit-check work. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud B1 semantic review packet
  source truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; table-driven tests kept the touched B1 alignment test
  within existing warning-band debt. Proof: focused B1 alignment review-packet
  promotion/fit-check contract tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with fresh
  semantic review packet CLI evidence that explicit review packets are again
  loaded through raw parser/type paths, accepted as plausible non-object source
  packets, or allowed to write artifacts after source-load failure.

- 2026-06-20: B1 Map 12 semantic-anchor review packet CLI loading now treats
  explicit `--review-manifest` and `--alignment-artifact` inputs as JSON-object
  source truth. Missing, malformed, or parseable non-object review/alignment
  files return concise CLI source-path errors and do not write proposed-anchor
  packets, instead of surfacing raw file/parser/type failures before semantic
  review packet construction. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud B1 semantic-anchor review source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized
  modules; table-driven tests kept the touched B1 alignment test within
  existing warning-band debt. Proof: focused B1 alignment/semantic-anchor
  contract tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh semantic-anchor
  review CLI evidence that explicit review or alignment source files are again
  loaded through raw parser/type paths or accepted as plausible non-object
  source packets.

- 2026-06-20: B1 Map 12 semantic projection CLI loading now treats explicit
  `--correspondences` and `--review-manifest` inputs as JSON-object source
  truth. Missing, malformed, or parseable non-object correspondence/review
  files return concise CLI source-path errors and do not write projection
  output, instead of surfacing raw file/parser/type failures before projection
  validation. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 semantic projection source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  the projection script remains small while the touched alignment test remains
  existing warning-band debt. Proof: focused B1 alignment/projection contract
  tests, touched-file ruff/format checks, `git diff --check`, changed-code
  review, and ratchet. Reopen only with fresh semantic-projection CLI evidence
  that explicit correspondence or review source files are again loaded through
  raw parser/type paths or accepted as plausible non-object source packets.

- 2026-06-20: B1 runtime bundle robot-consumption proof loading now reads
  explicit alignment and navigation artifacts through the shared JSON-object
  source guard. Missing, malformed, or parseable non-object
  `--alignment-artifact` / `--navigation-artifact` inputs now raise concise
  source-path errors before proof validation or runtime bundle writes, instead
  of surfacing raw parser/type failures from wrong-shaped proof evidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud B1 runtime proof source truth / source-reader consolidation.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  table-driven tests kept the B1 runtime bundle contract test below warning
  band while the runtime compiler remains in warning-band debt at 1574 lines.
  Proof: focused B1 runtime bundle contract tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet. Reopen only
  with fresh runtime bundle evidence that explicit alignment/navigation proof
  artifacts are again loaded through raw parser/type paths or accepted as
  plausible non-object source packets.

- 2026-06-20: B1 runtime bundle compilation now reads explicit
  `--review-manifest` input through the same JSON-object source guard used for
  explicit semantic projection artifacts. Missing, malformed, or parseable
  non-object review manifests now raise concise source-path errors before
  review validation or artifact writes, instead of surfacing raw parser/type
  failures from wrong-shaped review source truth. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud B1 runtime
  review source truth / source-reader consolidation. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; the runtime bundle compiler
  remains in warning-band debt at 1578 lines. Proof: focused B1 runtime bundle
  contract tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh runtime bundle
  evidence that explicit review manifests are again loaded through raw
  parser/type paths or accepted as plausible non-object source packets.

- 2026-06-20: B1 Map 12 label-tool semantic source loading now treats
  explicitly supplied `--semantics` paths as source truth: missing files,
  malformed JSON, and parseable non-object JSON raise clear source errors
  instead of falling back to the empty vendor semantics packet. The intentional
  no-authored-semantics default still exists for the raw vendor Map 12 bundle,
  but now requires valid `source.json` metadata and fails when that source
  identity packet is missing, malformed, or non-object instead of fabricating
  `robot_map_12`. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud label-tool semantics source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; the
  label-tool script remains in the tracked warning band at 1173 lines. Proof:
  focused B1 label-tool contract tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with fresh
  label-tool evidence that explicit semantics paths or required vendor source
  metadata are again skipped, defaulted, or turned into plausible empty packet
  identity.

- 2026-06-20: B1 Map 12 label-tool review-manifest loading now treats an
  explicitly supplied manifest path as source truth: missing files, malformed
  JSON, parseable non-object JSON, and wrong-schema manifests raise clear
  label-tool source errors instead of silently falling through to the
  no-review-manifest semantics path. The default no-manifest vendor Map 12 path
  remains supported. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud label-tool review source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; the
  label-tool script remains in the tracked warning band at 1151 lines. Proof:
  focused B1 label-tool contract tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet. Reopen only with fresh
  label-tool evidence that explicit review-manifest paths are again ignored,
  schema-skipped, or treated like optional absent inputs.

- 2026-06-20: B1 Map 12 label-tool draft export now preserves
  `polygon_role` as source-truth metadata and rejects missing or invalid draft
  label roles during manifest generation/validation instead of defaulting bad
  source values to `navigation_area`. The slice keeps forced candidate
  `alignment_status`, draft `review_status`, and operator-authored
  `geometry_source` export behavior unchanged. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud semantic-map
  draft source truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; the label-tool script remains in the tracked warning band
  at 1140 lines. Proof: focused B1 label-tool contract tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.
  Reopen only with fresh label-tool evidence that malformed semantic-map role
  metadata is again silently converted into valid-looking draft labels.

- 2026-06-20: Runtime Map Prior Snapshot conversion and B1 runtime bundle
  compilation now reuse the shared `roboclaws.maps.navigation_memory` parser
  for Agibot navigation-memory object loading, item-list selection, item type
  guards, and point/pose numeric validation. This removes the duplicate local
  readers and parsing helpers from both oversized callers while preserving the
  existing Runtime Map Prior and B1 compiler diagnostics for malformed,
  non-object, empty, wrong-shaped, and bad-coordinate sources. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: parser ownership
  consolidation / no intended valid-output change. Metric: ratchet stayed at 0
  Ruff complexity rows and 79 oversized modules; the B1 runtime bundle compiler
  dropped below the previous 1639-line snapshot to 1576 lines, and Runtime Map
  Prior Snapshot moved from 1213 lines before the earlier parser work to 1174
  lines after this consolidation. Proof: focused Runtime Map Prior Snapshot and
  B1 runtime bundle contract tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, duplicate-parser search, and
  ratchet. Reopen only with fresh evidence that these callers have grown
  another local Agibot navigation-memory parser or that shared parser
  diagnostics drift from the covered contract expectations.

- 2026-06-20: B1 Map 12 consistency and label-tool review layers now load
  `navigation_memory.json` through a shared strict parser, require a non-empty
  `items` or `catalog.navigation_memory` list, reject non-object rows, reject
  present malformed `nav_goal` / `pose` point fields, and fail on missing
  selected-bundle sibling memory sources instead of rendering empty navigation
  memory layers or partial consistency packets. The label tool also resolves
  the memory source next to the selected map bundle instead of a stale global
  default. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 review-layer source truth; valid
  item-list and catalog-shaped memory sources remain accepted. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof: focused B1
  Map 12 consistency and label-tool contract tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet. Parked:
  migrating the already-strict Runtime Map Prior Snapshot and B1 runtime bundle
  compiler local parsers onto the shared helper should be a separate
  caller-proof slice, not folded into this review-layer change. Reopen only
  with fresh B1 review-tool evidence that malformed navigation memory sources
  are again skipped, defaulted, or written as valid-looking empty/partial
  packets.

- 2026-06-20: B1 runtime bundle compilation now loads
  `navigation_memory.json` through a strict object parser, requires a non-empty
  `items` or `catalog.navigation_memory` list, rejects non-object rows, and
  rejects present malformed `nav_goal` / `pose` point fields before writing
  `semantics.json` or provenance. Malformed memory sources can no longer crash
  raw, collapse into a generic no-waypoints failure, or be skipped into partial
  runtime semantics. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 runtime source truth; valid memory rows
  and costmap-based waypoint selection remain unchanged. Metric: ratchet stayed
  at 0 Ruff complexity rows and 79 oversized modules. Proof: focused B1 Map 12
  runtime bundle contract tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh runtime bundle
  evidence that malformed navigation memory sources are again skipped,
  genericized, or written into partial bundle artifacts.

- 2026-06-20: Runtime Map Prior Snapshot conversion now requires Nav2
  cleanup-bundle `semantics.json` to provide a non-empty
  `inspection_waypoints` list and rejects non-object waypoint rows before
  materializing anchors. Missing, empty, or wrong-shaped waypoint sources can no
  longer produce a valid-looking zero-waypoint prior snapshot. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  offline prior source-list truth. Metric: ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules after compacting the focused contract tests
  back below the 800-line threshold. Proof: focused Runtime Map Prior Snapshot
  contract tests, touched-file ruff/format checks, `git diff --check`, and
  ratchet. Reopen only with fresh Nav2 cleanup-bundle evidence that missing,
  empty, or wrong-shaped waypoint entries again become empty or partially
  fabricated snapshots.

- 2026-06-20: Runtime Map Prior Snapshot conversion now requires Agibot
  `navigation_memory.json` to provide a non-empty `items` list or non-empty
  `catalog.navigation_memory` list, and rejects non-object memory rows before
  anchor materialization. Missing, empty, or wrong-shaped item sources can no
  longer produce a valid-looking zero-anchor prior snapshot. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  offline prior source-list truth; the existing catalog-shaped alternate source
  remains accepted. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused Runtime Map Prior Snapshot contract tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen only
  with fresh Agibot offline prior evidence that missing, empty, or wrong-shaped
  memory entries again become empty or partially fabricated snapshots.

- 2026-06-20: Runtime Map Prior Snapshot conversion now rejects malformed,
  missing, non-object, non-finite, or boolean Agibot `nav_goal`/`pose`
  coordinates and Nav2 cleanup-bundle waypoint `x`/`y`/`yaw` coordinates before
  materializing offline prior anchors. Present-but-bad Agibot `nav_goal` values
  can no longer fall through to `pose`, and malformed Nav2 waypoint geometry can
  no longer become plausible map-frame zero coordinates. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  offline prior waypoint geometry source truth; online runtime-map wrapping
  remains unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused Runtime Map Prior Snapshot contract tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen only
  with fresh offline prior conversion evidence that waypoint or anchor pose
  geometry is again defaulted, silently coerced, or fallback-substituted.

- 2026-06-20: Runtime Map Prior Snapshot conversion now rejects malformed
  source-map geometry in Agibot `nav2.yaml` and Nav2 cleanup-bundle `map.yaml`
  before building offline prior packets. Missing, non-positive, non-finite, or
  wrong-shaped resolution/origin values can no longer default to `0.05` or
  `[0, 0, 0]`, and yaw now comes from the same validated origin tuple. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud source-map geometry truth; valid Agibot and Nav2 conversion shape
  is unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused Runtime Map Prior Snapshot contract tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only with fresh offline prior conversion evidence that source map geometry is
  again defaulted, silently coerced, or read through a separate parser.

- 2026-06-20: OpenAI Agents SDK performance-profile numeric settings now
  reject direct Python boolean values before runtime profile metadata is
  produced. Direct `max_turns`, `raw_fpv_candidate_budget`,
  `mcp_client_session_timeout_s`, and `model_service_retry_sleep_s` values can
  no longer accept `True` as `1` / `1.0`; string env parsing, finite numeric
  defaults, provider route/model selection, and boolean settings remain
  unchanged. Owner layer: Agent Engines And Provider Profiles. Behavior-change
  class: fail-aloud provider/env numeric config source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules; the profile
  helper remains at the 800-line threshold after local compaction. Proof:
  focused performance-profile validation cases, full `test_live_runtime.py`,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen only
  with fresh numeric config bool/string coercion false-confidence evidence.

- 2026-06-20: Provider retry helper tests now merge one-assertion status-code,
  transient-error classification, and retry-delay checks into three
  behavior-named parameter tables while keeping the negative-attempt error test
  separate. Owner layer: Agent Engines And Provider Profiles.
  Behavior-change class: unit-test pruning / no production behavior change.
  Metric: `tests/unit/providers/test_provider_retry.py` keeps 14 collected
  cases while test functions drop 10 -> 4; the file moves 77 -> 88 lines
  because explicit case tables are longer than one-assertion functions. Proof:
  `$intuitive-tests` audit/propose, focused provider-retry tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet. Reopen
  only with fresh provider retry tests that duplicate the same helper
  classifications instead of adding a distinct retry/error behavior.

- 2026-06-20: OpenAI Agents SDK performance-profile MCP-timeout validation
  tests now fold the duplicate malformed-env and negative-direct one-off tests
  into the existing invalid MCP-timeout value table. Route/profile/model
  compatibility tests remain separate because they protect different provider
  diagnostics. Owner layer: Agent Engines And Provider Profiles.
  Behavior-change class: unit-test pruning / no production behavior change.
  Metric: `tests/unit/agents/test_live_runtime.py` keeps 137 collected cases
  while test functions drop 108 -> 106 and file size drops 5765 -> 5745 lines;
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules. Proof:
  `$intuitive-tests` audit/propose, focused performance-profile validation
  cases, full `test_live_runtime.py`, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh performance-profile
  tests that duplicate simple invalid-value scaffolding without protecting a
  distinct env/direct precedence, route compatibility, or visible diagnostic
  surface.

- 2026-06-20: OpenAI Agents SDK live-runtime config failure tests now fold
  duplicate one-off invalid retry-attempt, retry-sleep, and MCP-timeout
  env/direct tests into the existing parameterized validation tables. The
  slice preserves exact provider-config failure detail checks through the shared
  runtime failure helper while removing repeated request/run/status assertion
  bodies. Owner layer: Agent Engines And Provider Profiles. Behavior-change
  class: unit-test pruning / no production behavior change. Metric:
  `tests/unit/agents/test_live_runtime.py` keeps 137 collected cases while test
  functions drop 112 -> 108 and file size drops 5825 -> 5765 lines; ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof:
  `$intuitive-tests` audit/propose, focused config-validation cases, full
  `test_live_runtime.py`, touched-file ruff/format checks, `git diff --check`,
  and ratchet. Reopen only with fresh provider/env tests that duplicate runtime
  config failure scaffolding without protecting a distinct provider route,
  readiness failure, or visible diagnostic surface.

- 2026-06-20: Operator-console public recipe tests now merge the standalone
  `just/console.just` text-shape assertion into the public `just --summary` /
  `just --dry-run console::run` behavior check. The slice keeps the separate
  CLI default test for `roboclaws.operator_console` while replacing direct
  recipe-file parsing with the launched public recipe surface. Owner layer:
  Thin Runtime / Server Adapters. Behavior-change class: unit-test pruning /
  no production behavior change. Metric: `test_operator_console.py` keeps 42
  collected cases while test functions drop 40 -> 39; the touched file moves
  1578 -> 1581 lines because the stronger public-surface assertion is slightly
  longer. Proof: `$intuitive-tests` audit/propose, focused operator-console
  tests plus route-adjacent coverage, touched-file ruff/format checks,
  `git diff --check`, and ratchet. Reopen only with fresh static
  operator-console recipe/DOM/route wiring assertions that are not already
  covered through public launch readiness, CLI defaults, artifact links,
  redaction, locks, or status transitions.

- 2026-06-20: Eval-runner unit tests now consolidate duplicate launch-metadata
  validation bodies for direct live-surface command kwargs, sample-derived live
  launch metadata, and live runtime-map dependency metadata into behavior tables.
  The slice preserves the same collected parameter cases and keeps direct helper
  validation, suite-level sample validation, direct dependency resolver checks,
  and live-before-launch checks distinct. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: unit-test pruning / no production
  behavior change. Metric: eval-runner collection stayed at 104 cases while
  `tests/unit/evals/test_eval_runner.py` 2613 -> 2580 lines; ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules. Proof: `$intuitive-tests`
  audit/propose, focused eval-runner collection, eval-runner plus adjacent
  eval-harness tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen only with fresh duplicated
  validation bodies; do not collapse helper-level and suite-level checks when
  they prove different failure surfaces.

- 2026-06-20: Eval-harness selector tests now merge low-signal route-selection
  shape checks into two behavior tables for changed-file signals and explicit
  intent axes. The slice preserves provider readiness, runtime-prior,
  detached-live polling, DINO sidecar, budget, manifest-output, and source-error
  regressions as separate behavior tests while dropping one-field row metadata
  assertions. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: unit-test pruning / no production behavior change.
  Metric: selector collection 31 -> 23 tests and
  `tests/unit/evals/test_eval_harness_selector.py` 782 -> 738 lines; ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules. Proof:
  `$intuitive-tests` audit/propose, focused selector collection,
  selector+manifest tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet. Reopen selector-test pruning only with
  fresh duplicate static metadata assertions; keep live/blocker/source-error
  regressions behavior-shaped.

- 2026-06-20: Operator-console B1 camera preview promotion now rejects absolute
  FPV/chase artifact view paths, so external local files cannot be promoted as
  current Isaac runtime camera evidence. Relative view paths remain bound under
  the source artifact directory, matching the existing `../` escape rejection.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud preview artifact source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; the preview script remains under
  the current module-size warning while the focused operator-console preview
  test file remains oversized. Proof: focused operator-console preview tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: Eval-harness detached live-product rows now require terminal
  `live_status.json` evidence before marking a Codex live product row passed
  from `run_result.json`. A row with result artifacts but a still-running live
  status now blocks at the harness layer instead of publishing false-green pass
  evidence. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud detached live eval source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules. Proof: focused
  eval-harness selector tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-20: Detached live eval completion now requires terminal
  `live_status.json` evidence before treating `run_result.json` as completed
  Codex live-route proof. Timeout recovery, deadline recovery, and grace-window
  polling now share the same terminal-status predicate, preserving the explicit
  open-ended checker-failure allowance while rejecting still-running or
  non-checker-failed detached runs. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud detached live eval source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  `roboclaws/evals/live_runtime.py` remains below the module-size warning.
  Focused regression coverage keeps `tests/unit/evals/test_eval_runner.py`
  above the 2000-line warning and remains parked for `$intuitive-tests`. Proof:
  focused live surface product tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-20: Live eval surface artifact discovery now validates
  stdout-declared `Artifacts:` directories before treating them as priority live
  route evidence. Declared paths must stay under the live surface output root
  and end at the expected `seed-*` leaf, preventing trial-directory artifacts,
  malformed parent paths, or escaped paths from substituting for the actual live
  product run. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud live eval artifact source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; focused
  regression coverage keeps `tests/unit/evals/test_eval_runner.py` above the
  2000-line warning and should be handled only through the planned
  `$intuitive-tests` route. Proof: focused live surface artifact discovery
  tests, full eval-runner unit file, touched-file ruff/format checks, `git diff
  --check`, and ratchet.

- 2026-06-20: Eval dependency resolution now treats present
  `runtime_map_prior` fields as source truth even when the value is null or
  empty. Explicit null values now fail as invalid dependency metadata, and
  explicit empty launch overrides now fail as empty prior paths before product
  launch instead of skipping validation or falling through to another dependency
  source. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud eval dependency metadata source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and 79 oversized modules; focused regression
  coverage keeps `tests/unit/evals/test_eval_runner.py` above the 2000-line
  warning and should be handled only through the planned `$intuitive-tests`
  route. Proof: focused explicit-prior dependency tests, full eval-runner unit
  file, touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval dependency resolution now rejects wrong-shaped or empty
  `runtime_map_prior_from_sample` metadata before direct or live product
  launch. Boolean, numeric, list, object, or blank source-sample values now
  become artifact-source eval result failures instead of fabricated source
  sample ids, missing-output dependency errors, or skipped dependencies. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  eval dependency metadata source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and 79 oversized modules; focused regression coverage keeps
  `tests/unit/evals/test_eval_runner.py` above the 2000-line warning and should
  be handled only through the planned `$intuitive-tests` route. Proof: focused
  direct/live source-sample dependency tests, full eval-runner unit file,
  touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval dependency resolution now rejects wrong-shaped explicit
  `runtime_map_prior` metadata before direct or live product launch. Boolean,
  numeric, list, or object prior values now become artifact-source eval result
  failures instead of raw exceptions or stringified path lookups, while the
  existing explicit empty-string prior failure remains a dependency error.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud eval dependency metadata source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; focused regression coverage
  keeps `tests/unit/evals/test_eval_runner.py` above the 2000-line warning and
  should be handled only through the planned `$intuitive-tests` route. Proof:
  focused direct/live dependency tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Open-ended authoritative predicate grading now rejects
  wrong-shaped Runtime Metric Map predicate source fields before converting
  them to empty evidence. Corrupt `public_semantic_anchors`,
  `generated_exploration_candidates`, `target_search_summary`,
  `inspection_observations`, `viewpoint_budget`, `observed_waypoint_ids`, or
  `observed_objects` values now surface as source errors instead of ordinary
  goal-not-satisfied behavior failures. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud runtime-map predicate source
  shape truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules; focused regression coverage keeps
  `tests/unit/evals/test_eval_runner.py` above the 2000-line warning and
  should be handled only through the planned `$intuitive-tests` route. Proof:
  focused open-ended predicate source-shape tests, full eval-runner unit file,
  touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Map-build outcome grading now rejects wrong-shaped
  `runtime_metric_map.json` list fields before applying minimum-count checks.
  Present `public_semantic_anchors` or `generated_exploration_candidates`
  values that are strings, objects, or other non-list JSON can no longer pass
  actionability thresholds via Python `len()` on the wrong type. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  runtime-map source shape truth. Metric: ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules; focused regression coverage keeps
  `tests/unit/evals/test_eval_runner.py` above the 2000-line warning and
  should be handled only through the planned `$intuitive-tests` route. Proof:
  focused map-build runtime-map tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval artifact grading now validates present required JSON
  artifacts (`run_result.json`, `agent_view.json`, `runtime_metric_map.json`,
  and `private_evaluation.json`) as object JSON before marking the artifacts
  grader passed. Malformed or wrong-shaped required evidence now appears as
  artifact source errors instead of letting a valid in-memory product result
  mask corrupt persisted eval evidence. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud eval artifact source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  focused regression coverage keeps `tests/unit/evals/test_eval_runner.py`
  above the 2000-line warning and should be handled only through the planned
  `$intuitive-tests` route. Proof: focused required-artifact regression tests,
  full eval-runner unit file, touched-file ruff/format checks, `git diff
  --check`, and ratchet.

- 2026-06-20: Live eval trial grading now requires live product runners to
  declare an explicit `eval_effective_run_dir` under the trial run directory
  before artifacts are graded. Missing, malformed, nonexistent, or escaped
  effective run directories now fail as artifact-source errors instead of
  letting stale trial-directory artifacts stand in for live route evidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud live eval artifact source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and 79 oversized modules; focused regression coverage
  keeps `tests/unit/evals/test_eval_runner.py` above the 2000-line warning and
  should be handled only through the planned `$intuitive-tests` route. Proof:
  focused live eval tests, full eval-runner unit file, touched-file ruff/format
  checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval regression promotion now requires a declared source sample
  ref and validates promotion source identity before deriving promoted
  sample/suite artifacts. Promotion can no longer fabricate a plausible
  regression sample from eval-result identity fields when `sample_refs` are
  absent, nor write durable source metadata from malformed `sample_id`,
  `trial_id`, or `provider_profile` values. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud regression-promotion
  source truth. Metric: ratchet stayed at 0 Ruff complexity rows and 79
  oversized modules. Proof: focused regression-promotion tests, full
  eval-runner unit file, touched-file ruff/format checks, `git diff --check`,
  and ratchet.

- 2026-06-20: Eval result bundle and HTML report rendering now validate
  scene-sampler projection source truth before publishing compact aggregate
  evidence. Malformed or missing scene-source counts, support/status fields,
  source `sample_ids`, non-object source rows, and malformed summary counts now
  fail with explicit sampler-projection source errors instead of becoming
  default-looking `0` values or silently disappearing from `eval_results.json`
  / `eval_report.html`. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud report/eval artifact source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules. Proof:
  focused eval report regression tests, full eval-runner unit file,
  touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval live-product launch setup now rejects invalid
  `scene_source` metadata before building direct product kwargs or live surface
  commands. Explicit empty or wrong-shaped eval sample launch overrides and
  live command kwargs can no longer fall back to `procthor-10k-val` or render a
  non-string scene source into the command; missing sample overrides still use
  the documented default. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud eval launch metadata source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules;
  `tests/unit/evals/test_eval_runner.py` remains above the 2000-line warning
  from focused regression coverage and should be handled only through the
  planned `$intuitive-tests` route. Proof: focused live-surface command and
  eval-runner regression tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval live-product launch setup now rejects invalid
  `scene_index` metadata before building direct product kwargs or live surface
  commands. Bad eval sample launch overrides or live command kwargs can no
  longer coerce booleans, floats, negative values, or malformed strings into a
  plausible scene id; missing sample overrides still use the documented scene
  `0` default. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud eval launch metadata source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 79 oversized modules; focused
  regression coverage pushed `tests/unit/evals/test_eval_runner.py` above the
  2000-line warning and should be handled only through the planned
  `$intuitive-tests` route. Proof: focused live-surface command and
  eval-runner regression tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Eval live-product launch setup now rejects invalid cleanup
  `generated_mess_count` / `relocation_count` metadata before building direct
  or live surface commands. Bad eval sample private goal references, launch
  overrides, or live command kwargs can no longer silently coerce cleanup mess
  counts to zero and drop scenario setup from the launched product route; valid
  integer counts and map-build zero defaults are unchanged. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud eval
  launch metadata source truth. Metric: ratchet stayed at 0 Ruff complexity
  rows and 79 oversized modules. Proof: focused live-surface command and
  eval-runner regression tests, full eval-runner unit file, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-20: Scene-camera comparison now has a focused
  `scene_camera_source_artifacts.py` owner for prepared-USD source metadata,
  local Isaac scene-index lookup, scene-index entry extraction, and support-pose
  normalization. Present `scene_metadata.json` files now fail aloud when
  malformed, wrong-shaped, or carrying non-object object entries instead of
  degrading into missing Isaac target evidence; missing metadata remains
  optional. The main comparison facade dropped below the 2000-line hard ceiling.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud scene-camera source artifact truth plus ownership split. Metric:
  ratchet stayed at 0 Ruff complexity rows and reports 79 oversized modules;
  `roboclaws/household/scene_camera_comparison.py` fell from 2011 to 1956
  lines. Proof: focused scene-camera comparison contract tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-20: MolmoSpaces worker initialization now fails aloud on malformed,
  wrong-shaped, or label-less adjacent scene JSON before deriving source room
  labels. A present source scene JSON packet can no longer surface as a raw
  parser/type failure or silently fall through to iTHOR-derived labels; missing
  source JSON keeps the explicit iTHOR floorplan fallback. Owner layer:
  Backend Runtime / Environment Primitive. Behavior-change class: fail-aloud
  worker initialization metadata source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused MolmoSpaces worker-state tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-20: B1 runtime bundle compilation now fails aloud when an explicit
  semantic projection artifact is malformed or parses to non-object JSON.
  Corrupt `semantic_projection.json` inputs now produce source-path validation
  errors instead of raw `JSONDecodeError` or attribute failures, while missing
  artifact, review-mismatch, malformed-room, and valid verified-room semantics
  behavior remain unchanged. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud runtime-map source artifact truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and reports 79 oversized modules in
  the current dirty worktree. Proof: focused B1 runtime-bundle contract tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: Nav2 map-bundle validation now fails aloud when
  `semantics.json` parses to a non-object JSON value. Wrong-shaped semantics
  files now produce an explicit bundle validation error and projection callers
  receive the existing assertion path instead of raw attribute failures during
  validation or projection; valid bundle export, checking, route validation,
  and projection behavior are unchanged. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud map-bundle source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and reports 79 oversized
  modules in the current dirty worktree. Proof: focused Nav2 map-bundle
  contract tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-20: Runtime Map Prior Snapshot conversion now fails aloud on
  malformed or parseable non-object source JSON for Agibot navigation memory
  and Nav2 cleanup bundles. Corrupt `navigation_memory.json`, `agibot/source.json`,
  or `semantics.json` files now produce concise source-path errors instead of
  raw parser/type failures or deriving fields from wrong-shaped packets, while
  valid Agibot and Nav2 conversion behavior is unchanged. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  map/source artifact truth. Metric: ratchet stayed at 0 Ruff complexity rows
  and reports 79 oversized modules in the current dirty worktree. Proof:
  focused Runtime Map Prior Snapshot contract tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-20: The Nav2 map-bundle exporter now fails aloud on malformed
  agent-view JSON and parseable non-object run-result JSON. CLI users get
  concise source-path errors instead of tracebacks or raw type failures, while
  valid `--agent-view` / `--run-result` export behavior and bundle validation
  are unchanged. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud map/export source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and reports 79 oversized modules in the
  current dirty worktree. Proof: focused Nav2 map-bundle contract tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: Planner proof bundle result summaries now fail aloud when a
  present proof `run_result.json` source parses to non-object JSON. Wrong-shaped
  proof result files now become explicit unreadable result evidence with
  `proof_run_result_unreadable` instead of crashing or letting proof-summary
  fields derive from an invalid source packet; malformed JSON keeps the same
  unreadable packet path. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud artifact/source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and reports 79 oversized modules in the
  current dirty worktree. Proof: focused planner proof request tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: OpenAI Agents SDK live timing now fails aloud when present MCP
  timing source artifacts are malformed or non-object. Corrupt
  `run_result.json` no longer gets erased before falling back to trace-derived
  timing, and corrupt `trace.jsonl` no longer escapes during downstream metrics
  extraction before `live_timing.json` is written; final successful writes are
  downgraded to failed timing evidence with `live_timing_source_error`. Owner
  layer: Agent Engines And Provider Profiles. Behavior-change class:
  fail-aloud live runtime artifact/source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and reports 79 oversized modules in the current dirty
  worktree; the runner reuses the OpenAI Agents metrics JSONL source parser
  rather than carrying a duplicate partial parser. Proof: focused OpenAI
  Agents live timing tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-20: Operator-console prompt previews now reject malformed or negative
  cleanup `relocation_count` overrides before rendering kickoff prompts.
  Preview-only target cleanup counts can no longer silently coerce invalid
  launch input into a plausible target of one; baseline/default cleanup counts,
  valid relocation counts, and existing prompt-env numeric validation are
  unchanged. Owner layer: Thin Runtime / Server Adapters. Behavior-change
  class: fail-aloud operator-visible launch-input preview. Metric: ratchet
  stayed at 0 Ruff complexity rows and reports 79 oversized modules in the
  current dirty worktree. Proof: focused operator-console prompt-preview tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: The live OpenAI Agents runtime now rejects boolean and non-finite
  numeric settings before status/timing evidence is written. Direct metadata
  and env inputs for max turns, model-service retry attempts,
  model-service retry sleep, and MCP client session timeout now fail with
  `provider_config_failure` instead of accepting booleans as numbers, leaking
  `nan` / `inf`, or surfacing raw conversion failures; zero MCP timeout still
  explicitly disables the client timeout. Owner layer: Agent Engines And
  Provider Profiles.
  Behavior-change class: fail-aloud live runtime env/metadata input; SDK
  perf-profile defaults, provider route/model selection, live provider calls,
  and zero-timeout disable semantics are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused OpenAI Agents live-runtime numeric tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-20: OpenAI Agents SDK performance-profile float settings now reject
  non-finite values before runtime profile metadata is produced. `nan` can no
  longer be clamped to `0.0`, and `inf` can no longer survive as a plausible
  MCP timeout or model-service retry sleep value. Owner layer: Agent Engines
  And Provider Profiles. Behavior-change class: fail-aloud provider/runtime
  env input; finite defaults and finite overrides, provider route semantics,
  model selection, live provider execution, and public defaults are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and reports 79 oversized
  modules in the current dirty worktree. Proof: focused OpenAI Agents
  perf-profile tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-20: Runtime inventory artifact rows now advertise same-origin
  `/artifacts/...` and `/api/raw/...` links only for files under
  `output/operator-console`, matching the operator-console artifact server
  boundary. Eval-harness and other non-console-output runtime files remain
  visible by path and command-copy actions, but no longer publish links that
  the server must reject. Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: fail-aloud/source-boundary protection for
  operator-visible artifact metadata. Metric: ratchet stayed at 0 Ruff
  complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused runtime-inventory tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-20: Operator-console artifact endpoints now serve only files under
  `output/operator-console`. `/artifacts/...` and `/api/raw/...` reject
  arbitrary repo files, directory escapes, and non-file paths instead of
  treating every repo-relative file as operator-visible output, while valid raw
  log serving still applies secret redaction. Owner layer: Thin Runtime /
  Server Adapters. Behavior-change class: fail-aloud/source-boundary protection
  for operator-visible artifacts. Metric: ratchet stayed at 0 Ruff complexity
  rows and reports 79 oversized modules in the current dirty worktree. Proof:
  focused operator-console HTTP tests, touched-file ruff/format checks, `git
  diff --check`, changed-code review, and ratchet.

- 2026-06-20: Operator-console launch starts now reserve a unique run
  directory before launch log or `operator_state.json` writes. Same-second
  route launches or stale run directories can no longer overwrite existing run
  evidence; exhausted reservation attempts fail before process spawn or lock
  ownership, and empty pre-state reservations are removed when launch-build or
  lock-acquire steps fail. Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: fail-aloud operator-visible source truth and artifact
  identity preservation. Metric: ratchet stayed at 0 Ruff complexity rows and
  reports 79 oversized modules in the current dirty worktree. Proof: focused
  operator-console launcher/API tests, touched-file ruff/format checks, `git
  diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console stop requests now reject malformed or
  non-object child `live_status.json` sources before stopping child live runs,
  terminating wrapper processes, releasing backend locks, or rewriting status
  artifacts. Corrupt live child evidence can no longer be replaced by a clean
  `stopped_by_operator` payload, and the HTTP stop endpoint now reports the
  same operator-facing source error; missing child live status and valid
  terminal failed-run preservation are unchanged. Owner layer: Thin Runtime /
  Server Adapters. Behavior-change class: fail-aloud operator-visible source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and reports 79
  oversized modules in the current dirty worktree. Proof: focused
  operator-console launcher/API stop tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console stop requests now reject malformed or
  non-object `operator_state.json` sources before stopping child live runs,
  terminating wrapper processes, releasing backend locks, or rewriting stop
  state. Corrupt stop-state evidence no longer surfaces as a raw JSON/type
  failure or gets overwritten by stop handling; unknown runs and valid
  stopped/failed terminal handling are unchanged. Owner layer: Thin Runtime /
  Server Adapters. Behavior-change class: fail-aloud operator-visible source
  truth. Metric: ratchet stayed at 0 Ruff complexity rows and reports 79
  oversized modules in the current dirty worktree. Proof: focused
  operator-console launcher/API stop tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console request-field readiness now rejects present JSON
  sources that do not contain a JSON object before marking required Agibot/B1
  launch artifacts ready. Parseable-but-wrong-shaped attached context/proof
  files such as arrays no longer satisfy `context_json`,
  `b1_alignment_artifact`, or `b1_navigation_artifact` gates; missing files,
  malformed JSON, relative path resolution, and valid object artifacts keep the
  existing behavior. Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: fail-aloud launch-input source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and reports 79 oversized modules in the
  current dirty worktree. Proof: focused Agibot readiness and neighboring
  operator-console launcher/API readiness tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console session reads now reject malformed,
  non-object, or mismatched `sessions/<id>.json` records as explicit source
  errors. Corrupt session files no longer look like unknown sessions or get
  bypassed while steer messages mutate run artifacts; missing sessions keep the
  existing absent-session behavior. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: fail-aloud operator-visible source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and reports 79 oversized
  modules in the current dirty worktree. Proof: focused operator-console
  interaction, launcher, and HTTP-console tests; touched-file ruff/format
  checks; `git diff --check`; changed-code review; and ratchet.

- 2026-06-19: Operator-console interaction commands now reject malformed or
  non-object run `operator_state.json` sources before appending steer messages,
  next-goal queue rows, or session-link updates. Corrupt run state no longer
  looks like an unsupported route or missing session while mutating interaction
  artifacts; passive normalized-state rendering still surfaces source-error
  payloads through `derive_operator_state`. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: fail-aloud operator-visible source truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and reports 79 oversized
  modules in the current dirty worktree. Proof: focused operator-console
  interaction and state tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console manual control now rejects malformed or
  non-object `operator_state.json` sources at the control endpoint route lookup
  and state-update boundaries. Corrupt operator state no longer collapses into
  a misleading missing MCP endpoint, and a control response cannot overwrite
  the corrupt source while recording operator intervention evidence; unknown
  runs remain 404 and valid state/control rows are unchanged. Owner layer: Thin
  Runtime / Server Adapters. Behavior-change class: fail-aloud
  operator-visible source truth. Metric: ratchet stayed at 0 Ruff complexity
  rows and reports 79 oversized modules in the current dirty worktree. Proof:
  focused operator-console control endpoint tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console latest-run history attachment now surfaces
  malformed `runs.jsonl`, `operator_state.json`, and `live_status.json` source
  artifacts as explicit source-error payloads instead of skipping corrupt
  history rows, attaching a metadata-free fallback run, or erasing bad live
  status into an empty phase. Missing optional sources remain optional, and
  normal history-index plus run-directory fallback attachment behavior is
  unchanged. Owner layer: Thin Runtime / Server Adapters. Behavior-change
  class: fail-aloud operator-visible source truth. Metric: ratchet stayed at
  0 Ruff complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused operator-console history tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: MolmoSpaces apple-to-apple grid execution now rejects malformed
  or non-object existing `apple2apple_test_grid.json` manifests during filtered
  execute, and stable malformed/non-object `live_status.json` sources during
  detached live-row polling. Corrupt manifests no longer get treated as absent
  before row-state merge, and corrupt live status no longer becomes
  `phase=unknown`; the live-status reader keeps a small retry window for
  transient partial writes while preserving missing-source optional behavior.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused apple-to-apple grid tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Live-agent result artifact loading now fails aloud when present
  `live_status.json` or `run_result.json` sources are malformed or contain
  non-object JSON. Corrupt live status no longer becomes `phase=unknown`, and
  corrupt run-result completion evidence no longer disappears as an absent
  task-completion packet; genuinely missing live artifacts keep the existing
  optional incomplete-run behavior. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: fail-aloud artifact/source truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and reports 79 oversized modules in
  the current dirty worktree. Proof: focused live-runtime artifact-loader
  tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-19: Eval regression promotion now validates the promoted sample
  payload and updated suite payload before writing either artifact. Invalid
  suite updates no longer leave orphan promoted sample files behind when
  promotion fails after sample validation; successful promotion and existing
  fail-aloud source-sample guards are unchanged. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud artifact/write
  atomicity. Metric: ratchet stayed at 0 Ruff complexity rows and reports 79
  oversized modules in the current dirty worktree. Proof: focused eval
  regression-promotion tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-19: Eval regression promotion now treats matched suite
  `sample_refs` as declared source truth. Missing or invalid declared source
  samples, plus refs that resolve to a different sample id, now fail before any
  promoted sample or suite artifact is written, instead of silently
  synthesizing a regression sample from eval-result identity fields while
  ignoring corrupt suite/sample source evidence; promotion from a valid source
  sample and passed-result/stop-label guards are unchanged. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused eval regression-promotion tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Eval artifact dependency resolution now treats explicit
  `runtime_map_prior` values as declared source truth and fails before direct
  or live product launch when the path is empty or missing. Missing explicit
  priors now produce an `EvalDependencyError` packet with resolved dependency
  provenance instead of letting the runner launch against a stale/nonexistent
  runtime-map prior; sample-derived prior behavior and valid prior handoff are
  unchanged. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud artifact/source truth. Metric: ratchet stayed at 0 Ruff
  complexity rows and reports 79 oversized modules in the current dirty
  worktree. Proof: focused eval-runner dependency tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Eval HTML reports now validate declared `run_result` and
  `report` artifact links against the eval output directory before rendering
  them as proof links. Missing files, empty paths, absolute paths outside the
  eval output tree, and `../` escapes now render as explicit unavailable source
  evidence instead of clickable stale/substitute links; existing in-output
  artifacts keep relative hyperlinks. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud artifact/source truth; eval
  grading, result schemas, aggregation, and product-run artifact generation are
  unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and reports 79
  oversized modules in the current dirty worktree. Proof: focused eval-report
  tests, existing eval-runner report smoke, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Scene-sampler readiness export now fails aloud when an enabled
  artifact has no payload instead of writing `{}` as a valid-looking readiness
  artifact, and invalid `--candidate-range` input returns a concise CLI error
  before writing artifacts instead of surfacing a traceback. Normal readiness
  artifact generation, threshold failures, generated eval packets, and disabled
  artifact flags are unchanged. Owner layer: Artifacts, reports, and eval
  suites. Behavior-change class: fail-aloud artifact/config input truth.
  Metric: ratchet stayed at 0 Ruff complexity rows and reports 79 oversized
  modules in the current dirty worktree.
  Proof: focused scene-sampler readiness export tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Coding-agent provider profile selection now rejects unknown
  provider profiles at the common shell helper boundary instead of echoing the
  raw value as if it were selected, and the provider-registry CLI reports an
  argparse-style unknown-profile error instead of a Python traceback. Explicit
  `system` Claude fallback, catalog route aliases, route-compatible model
  overrides, and downstream Codex/Claude/OpenAI Agents supported-profile checks
  are unchanged. Owner layer: Agent Engines And Provider Profiles.
  Behavior-change class: fail-aloud provider/profile input truth. Metric:
  ratchet stayed at 0 Ruff complexity rows and 78 oversized modules. Proof:
  focused coding-agent env helper and provider catalog tests, manual unknown
  profile probes, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-19: Detached live-run summary auto-discovery now requires recognized
  live-run evidence before selecting default or parent `seed-*` directories,
  and explicit empty run directories fail aloud instead of printing
  pending/all-missing summaries. The summary CLI no longer reports placeholder
  seed dirs as the latest run; explicit `run_result.json` inputs,
  comparison-manifest handling, timing extraction, and summary rendering are
  unchanged. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud artifact/source truth. Metric: ratchet
  stayed at 0 Ruff complexity rows and 78 oversized modules. Proof: full
  detached live-run summary unit tests, touched-file ruff/format checks,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Molmo CI live failure diagnostics now select the latest
  evidence-bearing `seed-*` directory instead of the newest directory of any
  shape. Failed live entries no longer publish an empty latest seed placeholder
  while hiding an older seed directory with actual failure evidence, and
  runs with no recognized diagnostic artifacts leave the diagnostic link absent
  instead of creating a no-evidence diagnostics page from automatic discovery.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; live launch commands, successful report
  publishing, diagnostic index rendering for explicitly supplied bundles, and
  live status schemas are unchanged. Metric: ratchet stayed at 0 Ruff
  complexity rows and 78 oversized modules. Proof: full CI live reports unit
  tests, touched-file ruff/format checks, `git diff --check`, changed-code
  review, and ratchet.

- 2026-06-19: Operator-console B1 camera preview promotion now resolves
  declared relative FPV/chase view paths only under the source artifact
  directory and rejects relative path escapes before file lookup. The console no
  longer promotes stale same-named CWD files or sibling-run view files as
  current B1 robot camera preview evidence; explicit absolute view paths remain
  accepted. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud artifact/source truth; preview quality scoring, provenance
  checks, skip-existing metadata checks, static B1 preview behavior, and
  MolmoSpaces rendering are unchanged. Metric: ratchet stayed at 0 Ruff
  complexity rows and 78 oversized modules. Proof: focused operator-console
  preview tests, touched-file ruff/format checks, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-19: Codex cleanup apple-to-apple summaries now fail aloud on declared
  top-level artifact links or robot-view sample paths that are empty, missing,
  or not the expected file/directory kind, and resolve declared relative paths
  only under the lane run directory. The summary report no longer links CWD
  substitute artifacts or silently omits missing declared visual evidence; the
  absent-key historical defaults still point at run-directory defaults and are
  omitted when those optional files are absent. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud artifact/source truth;
  comparison math, report layout, live run execution, and camera-contract
  summaries are unchanged. Metric: the summary script shrank to 944 lines, and
  the ratchet stayed at 0 Ruff complexity rows and 78 oversized modules. Proof:
  focused Codex cleanup apple-to-apple summary tests, touched-file ruff/format
  checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Cleanup report regeneration now fails aloud on declared
  scenario/trace/snapshot artifact paths that are empty, missing, or not files,
  and resolves declared relative artifact paths only under the run directory.
  Regenerated reports no longer substitute CWD files or same-basename colocated
  files when `run_result.json` declares a different artifact source; historical
  absent `scenario` artifacts still use the run-result shell fallback. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; report rendering, run-result path
  discovery, historical absent-artifact defaults, and cleanup visual sections
  are unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused cleanup artifact-report contract tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-19: Split the live eval artifact selector's priority,
  current-discovered, and current-existing candidate decisions into named
  helpers after the previous fail-aloud slice introduced one Ruff C901 row.
  The stale/ambiguous artifact behavior is unchanged, but
  `discover_live_surface_run_dir` is back under the complexity gate. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  deterministic helper refactor; public launch command construction,
  artifact freshness rules, detached polling, and grader schemas are
  unchanged. Metric: ratchet returned to 0 Ruff complexity rows and stayed at
  78 oversized modules. Proof: focused eval-runner tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Eval-runner live surface artifact discovery now fails aloud for
  stale or ambiguous sibling `seed-*` run directories. Live eval rows no longer
  silently grade substitute artifacts from an older run or an unclear current
  route when the commanded run directory lacks evidence; the adapter still
  accepts explicit/stdout artifact directories and one unique current
  timestamped directory. The JSON sidecar loader and artifact-dir selector now
  live in `roboclaws/evals/live_artifacts.py`, keeping
  `roboclaws/evals/live_runtime.py` under the default module-size target.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; public launch command construction,
  detached polling timeouts, checker recovery, and grader schemas are
  unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused eval-runner tests, touched-file
  ruff/format checks, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Eval-harness detached live-product polling now fails aloud for
  malformed `live_status.json` source evidence. A corrupt live-status sidecar
  no longer looks absent while the harness waits for `run_result.json` or marks
  the detached live-product row as passed; the row blocks with an explicit
  source-error detail and keeps the live-status/driver artifacts attached.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; row selection, provider readiness, live
  command construction, detached timeout duration, result-artifact attachment,
  and eval aggregate parsing are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  eval-harness selector tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-19: Eval-runner grader sidecar parsing now fails aloud for present
  malformed or non-object optional JSON artifacts. Corrupt
  `live_status.json`, `live_timing.json`, `advisory_evaluation.json`, and
  open-ended `runtime_metric_map.json` sources no longer collapse into
  unavailable live status/timing, advisory-neutral semantic satisfaction, or
  predicate evidence; affected rows fail with `artifact_missing` and compact
  `source_errors` while genuinely missing optional sidecars keep the existing
  unavailable behavior. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud artifact/source truth; suite/sample/result
  schemas, product-runner invocation, required map-build runtime-map grading,
  trace policy, and live execution are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused eval-runner
  tests, touched-file ruff/format checks, `git diff --check`, changed-code
  review, and ratchet.

- 2026-06-19: Codex and Claude live-run timing source parsing now fails aloud
  for present malformed or non-object `trace.jsonl` rows, and Codex event
  summary parsing now fails aloud for malformed or non-object
  `codex-events.jsonl` rows. Corrupt timing/model source evidence no longer
  disappears before `live_timing.json`, MCP trace timing, time-to-first-MCP,
  Codex event summaries, or model-call metrics are written. A would-be
  successful run becomes a failed timing/status packet with
  `live_timing_source_error`; existing failure packets preserve their original
  reason while recording the source error. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud artifact/source truth;
  launch command construction, provider timing proxy behavior, checker gates,
  cleanup-server lifecycle, and model-call metric schemas are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized modules.
  Proof: focused CI live-report runner tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Agent SDK speedup matrix row loading now blocks on present
  malformed or non-object baseline/candidate source artifacts instead of
  deriving quality, speed, or reducible-bucket recommendations from empty or
  partial evidence. The matrix reuses the strict report-performance
  `trace.jsonl` reader for its camera-grounded tool breakdown and turns
  report-performance source errors into explicit row reasons; missing optional
  files still preserve the existing unavailable behavior. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  artifact/source truth; matrix manifest schema, privacy scanning,
  comparison math, candidate coverage, and live-run producers are unchanged.
  Metric: `run_agent_sdk_perf_matrix.py` shrank from 989 to 971 lines, and the
  ratchet stayed at 0 Ruff complexity rows and 78 oversized modules. Proof:
  focused Agent SDK perf-matrix tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Detached live-run summary source parsing now fails aloud for
  present malformed or non-object `live_status.json`, `live_timing.json`,
  `run_result.json`, and `trace.jsonl` artifacts. Corrupt summary inputs no
  longer collapse to pending/unknown runner, timing, result, or trace sections
  that can make a damaged live run look merely incomplete; the CLI exits
  nonzero with the source path and row/location. Missing optional files still
  preserve the existing pending/unknown behavior. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud artifact/source
  truth; report layout, comparison-manifest handling, performance extraction
  math, and live artifact producers are unchanged. Metric: touched production
  module remains under the default 800-line target, and the ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  summarize-live-run tests, touched-file ruff/format checks, `git diff
  --check`, and ratchet.

- 2026-06-19: RAW-FPV OpenAI Agents budget guard trace parsing now fails
  aloud for present malformed or non-object `trace.jsonl` rows. Corrupt trace
  evidence no longer disappears before the RAW-FPV candidate, repeated-failure,
  or observe-per-waypoint budget guard decides whether the live SDK run hit a
  terminal budget condition; diagnostics include the source path and row
  number. Missing trace files still preserve the existing no-budget-failure
  behavior. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud artifact/source truth; budget thresholds,
  context-budget logic, live retry behavior, and trace producers are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized modules.
  Proof: focused OpenAI Agents live-runtime budget tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-19: OpenAI Agents SDK metric JSONL parsing now fails aloud for
  present malformed or non-object event/span/trace rows. Corrupt
  `openai-agents-events.jsonl`, `openai-agents-spans.jsonl`, or `trace.jsonl`
  sources no longer disappear before context/cache/growth, retry/fallback,
  racing, input-filter, event-count, or span metrics are written into
  `live_timing.json`; diagnostics include the source path and row number.
  Missing optional files still preserve the existing unavailable behavior.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; metric schemas, aggregation math, live
  runtime retry behavior, and event/span producers are unchanged. Metric:
  `openai_agents_metrics.py` is 799 lines, and the ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused OpenAI
  Agents live-runtime metrics tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Model-latency calibration source parsing now fails aloud for
  present malformed or non-object `model_call_metrics.jsonl` rows. Calibration
  fitting and holdout validation no longer skip corrupt source rows before
  computing sample counts, fit statistics, validation statistics, or
  coefficient sets, so diagnostic normalized-latency packets cannot look
  cleaner by silently shrinking their source dataset. Missing metric files still
  preserve the existing insufficient-samples / holdout-not-requested behavior,
  and well-formed but unusable metric rows still count as rejected rows. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud artifact/source truth; calibration packet schema, fit math,
  holdout limitation policy, and model-call metric row rejection rules are
  unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused report-performance calibration tests,
  touched-file ruff/format checks, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-19: Report-performance source parsing now fails aloud for present
  malformed or non-object JSON and JSONL artifacts. Corrupt
  `live_timing.json`, `live_status.json`, `run_result.json`, `trace.jsonl`,
  OpenAI/Codex/Claude event or span streams, and provider request metrics no
  longer collapse to empty or partial inputs that can make performance packets,
  model-call telemetry, provider transport evidence, or comparisons look
  cleaner than the artifact source. Missing optional artifacts still preserve
  the existing unavailable/missing behavior. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud artifact/source truth;
  packet schemas, telemetry math, privacy scanning, calibration handling, and
  live-agent artifact producers are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  report-performance tests, touched-file ruff/format checks, `git diff
  --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console route-lock readiness now fails aloud for
  malformed lock-owner `operator_state.json` and nested `live_status.json`
  sources. A backend lock held by a corrupt owner run no longer looks absent,
  silently startable, or attachable; readiness blocks with `blocker_kind:
  source_error` and keeps the lock held for operator inspection. Owner layer:
  Thin Runtime / Server Adapters. Behavior-change class: fail-aloud runtime
  artifact/source truth; valid attachable-run payloads, stale terminal-lock
  release, stop-run process cleanup, provider readiness, route gates, and
  runtime-inventory blockers are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  operator-console launcher tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Operator-console agent event JSONL parsing now fails aloud in
  normalized live-state payloads. Malformed or non-object `codex-events*.jsonl`,
  `claude-events*.jsonl`, and `openai-agents-events*.jsonl` rows no longer
  disappear while latest-decision evidence is selected from remaining valid
  agent messages; the state marks the run failed with the relevant event-source
  label and keeps row-level `source_errors`. Owner layer: Thin Runtime / Server
  Adapters. Behavior-change class: fail-aloud runtime artifact/source truth;
  valid Codex/Claude/OpenAI Agents message extraction, trace-derived latest
  action/tool summaries, artifact links, and checker handoff behavior are
  unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused operator-console state tests,
  touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-19: Operator-console `trace.jsonl` parsing now fails aloud in the
  normalized live-state payload. Present malformed or non-object trace rows no
  longer disappear while latest-action, decision-evidence, and latest-tool
  summaries are derived from the remaining valid rows; the state marks the run
  failed with a deduplicated `operator state source error: Trace` terminal
  reason and preserves row-level `source_errors`. Owner layer: Thin Runtime /
  Server Adapters. Behavior-change class: fail-aloud runtime artifact/source
  truth; valid trace pairing, nested live-attempt discovery, camera-state
  summary, core JSON source errors, agent-message extraction, artifact links,
  and checker handoff behavior are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  operator-console state tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Operator-console message inbox parsing now fails aloud for
  malformed or non-object `operator_messages.jsonl` rows. Corrupt present
  steering evidence no longer disappears from console message state or MCP
  `check_operator_messages` results; list/state payloads expose compact
  `source_errors`, MCP delivery returns an explicit source-error packet, and
  the pending-message hint tells the agent to surface the source error instead
  of treating the inbox as empty. Owner layer: Thin Runtime / Server Adapters.
  Behavior-change class: fail-aloud runtime artifact/source truth; valid queued
  steering delivery, seen-state rewriting, missing-file tolerance, next-goal
  requests, session attachment, and private-payload stripping are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized modules.
  Proof: focused operator-console interaction tests, stale private-reader
  search, touched-file ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-19: Operator-console manual-control source parsing now fails aloud
  for malformed or non-object `operator_control.jsonl` rows. Corrupt present
  control evidence no longer disappears before event-id assignment or
  intervention summary generation, so the console will not append new manual
  control rows around broken operator-intervention history. Owner layer: Thin
  Runtime / Server Adapters. Behavior-change class: fail-aloud runtime
  artifact/source truth; valid manual control calls, route gating, MCP tool
  invocation, operator-state updates, intervention artifact writing, and
  blank-line tolerance are unchanged. Metric: ratchet stayed at 0 Ruff
  complexity rows and 78 oversized modules. Proof: focused operator-console
  control endpoint tests, touched-file ruff/format checks, `git diff --check`,
  and ratchet.

- 2026-06-19: RAW-FPV Codex event source parsing now fails aloud for malformed
  JSONL rows and malformed observe text-result JSON. Corrupt present
  `codex-events*.jsonl` evidence no longer disappears into fewer source
  observations or a generic "no usable FPV frames" error; the probe raises an
  actionable source path and line number before scoring. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  artifact/source truth; JSON artifact loading, valid Codex observe event
  extraction, robot-view fallback discovery, provider execution, private
  scoring, and report rendering are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused RAW-FPV
  perception probe unit tests, touched-file ruff/format checks,
  `git diff --check`, and ratchet.

- 2026-06-19: Removed the stale `model_supports_images` helper from the
  provider registry. The helper had no production callers and treated unknown
  model ids as image-capable, which conflicted with the current fail-aloud
  provider/model registry direction. Remaining tests now use the canonical
  `resolve_model(...).supports_image_input` path. Owner layer: Agent Engines
  And Provider Profiles. Behavior-change class: stale helper deletion;
  provider readiness, route-model compatibility, aliases, direct-provider
  factory routing, and public route payloads are unchanged. Metric: ratchet
  stayed at 0 Ruff complexity rows and 78 oversized modules. Proof:
  stale-reference search, full provider catalog unit tests, touched-file
  ruff/format checks, `git diff --check`, and ratchet.

- 2026-06-19: Provider/profile route selection now fails aloud for
  route-incompatible catalog models. Provider routes declare compatible model
  ids, readiness and route payloads expose them, OpenAI Agents SDK runtime and
  performance-profile resolution reject known-but-wrong-route models such as
  `gpt-5.5` on `minimax-responses`, RAW-FPV evidence-lane checks validate the
  selected provider/model pair, and coding-agent shell helpers preserve the
  existing unknown-model diagnostic while surfacing route incompatibility
  details. Owner layer: Agent Engines And Provider Profiles, with
  evidence-lane impact at the Runnable Surfaces And Presets boundary.
  Behavior-change class: fail-aloud provider/model route compatibility;
  documented defaults, known model aliases, unknown-model failures, supported
  MiniMax variant selection, provider key/base-url validation, Codex/Claude
  unsupported-provider checks, and live SDK execution behavior are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized modules.
  Proof: full impacted provider catalog, OpenAI Agents live-runtime, MiniMax
  provider, model-provider checker, evidence-lane, coding-agent helper, and
  task-agent recipe contract tests, plus touched-file ruff/format checks,
  `bash -n`, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: OpenAI Agents SDK runtime model selection now fails aloud for
  unknown model overrides. Explicit `model`,
  `LiveAgentRequest.model`, `ROBOCLAWS_OPENAI_AGENTS_MODEL`, or
  `ROBOCLAWS_CODEX_MODEL` values must resolve through the provider model
  catalog before the SDK route is constructed, so a typo like
  `not-in-provider-catalog` becomes the existing `provider_config_failure`
  status instead of being passed to the live provider client. Owner layer:
  Agent Engines And Provider Profiles. Behavior-change class: fail-aloud
  provider/model route input; default model selection, known model aliases,
  valid explicit route models such as `MiniMax-M2.7-highspeed`, provider
  profile conflict detection, base-url/API-key validation, and SDK execution
  behavior are unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused provider catalog and live-runtime
  unknown-model tests, full provider catalog and OpenAI Agents live-runtime unit
  files, Minimax SDK route regression, touched-file ruff and format check,
  `git diff --check`, and ratchet.

- 2026-06-19: Operator-console live-state JSON source errors now fail aloud.
  Present malformed or non-object core `operator_state.json`,
  `live_status.json`, and `run_result.json` sources no longer collapse to empty
  payloads that can make the console show idle, missing, or generic pending
  state. `derive_operator_state` now records compact `source_errors`, marks the
  run failed, and routes the existing status/checker/terminal-reason fields
  through an actionable `operator state source error: ...` message, while
  genuinely missing optional files remain absent. Owner layer: Thin Runtime /
  Server Adapters. Behavior-change class: fail-aloud runtime artifact/source
  truth; display-run discovery, valid live status/result handling, artifact
  links, checker diagnostics, controls, JSONL trace parsing, and missing-file
  tolerance are unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules. Proof: focused operator-console state tests, full
  operator-console unit folder, touched-file ruff and format check,
  `git diff --check`, and ratchet.

- 2026-06-19: Operator-console prompt previews now fail aloud for malformed
  OpenAI Agents numeric prompt-env values. Non-empty
  `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET`,
  `ROBOCLAWS_OPENAI_AGENTS_MAX_OBSERVE_PER_WAYPOINT`, and
  `ROBOCLAWS_OPENAI_AGENTS_DONE_RETRY_BUDGET` preview inputs must be integers
  and cannot be negative, so `/api/prompt-preview` no longer renders a
  default-looking kickoff prompt for malformed live-route input that the typed
  runner configuration would reject or reinterpret. Omitted values keep the
  documented prompt defaults, and zero keeps the existing prompt-renderer
  minimum behavior for candidate/observe budgets while allowing zero done
  retries. Owner layer: Thin Runtime / Server Adapters. Behavior-change class:
  fail-aloud operator-preview configuration; route selection, launch env
  application, provider-profile validation, kickoff prompt text for valid
  values, and static console UI request shape are unchanged. Metric: ratchet
  stayed at 0 Ruff complexity rows and 78 oversized modules. Proof: focused
  operator-console prompt-preview tests, full operator-console unit folder,
  touched-file ruff and format check, `git diff --check`, and ratchet.

- 2026-06-19: Eval-harness explicit `since=` diff source selection now fails
  aloud. A bad base ref, missing revision, or other `git diff --name-only`
  failure no longer becomes an empty changed-file set that can make
  recommendations look clean; the selector raises an actionable error while
  preserving best-effort behavior for implicit dirty-worktree discovery. Owner
  layer: Eval suites. Behavior-change class: fail-aloud harness source input;
  explicit changed files, plan-based selection, explicit axes, implicit
  worktree fallback, row selection rules, and execution behavior are unchanged.
  Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized modules.
  Proof: focused eval-harness selector tests, full eval unit folder,
  touched-file ruff and format check, `git diff --check`, and ratchet.

- 2026-06-19: Eval-harness attached result packets now fail aloud when
  malformed. Required `eval_results.json` artifacts linked from selected eval
  rows no longer collapse to an empty aggregate that can leave a zero-exit row
  looking passed; present corrupt JSON or non-object payloads now mark the row
  `outcome=failed` with `failure_class=harness_bug_unclassified` and an
  explicit `eval_results_error`. Owner layer: Eval suites. Behavior-change
  class: fail-aloud harness artifact/source truth; missing result artifacts,
  valid failed/blocked aggregates, detached live-status polling, report
  rendering, and exit-status semantics are unchanged. Metric: ratchet stayed
  at 0 Ruff complexity rows and 78 oversized modules. Proof: focused
  eval-harness manifest tests, full eval unit folder, touched-file ruff and
  format check, `git diff --check`, and ratchet.

- 2026-06-19: Eval-harness provider readiness now fails aloud through the
  provider registry. Live eval rows with unknown provider profiles no longer
  pass preflight merely because Codex router environment variables are present;
  provider readiness now reports an explicit unknown-profile diagnostic, and
  eval-harness blockers consume the canonical readiness packet instead of a
  duplicate hard-coded env table. Owner layer: Agent Engines And Provider
  Profiles, surfaced through Eval suites. Behavior-change class: fail-aloud
  provider/profile input; documented default provider profiles, known profile
  env checks, optional/required row semantics, timing-proxy defaults, and live
  row execution are unchanged. Metric: ratchet stayed at 0 Ruff complexity rows
  and 78 oversized modules. Proof: focused eval-harness and provider catalog
  tests, touched-file ruff and format check, `git diff --check`, and ratchet.

- 2026-06-19: Live eval surface JSON artifact loading now fails aloud.
  Existing malformed or non-object `run_result.json` / `live_status.json`
  files in live eval product-route directories no longer collapse to empty
  payloads that look missing, unfinished, or terminally ambiguous. The live
  adapter preserves missing optional files as absent, but present corrupt JSON
  now raises an explicit source error that the eval packet classifies under the
  existing `artifact_missing` failure class. Owner layer: Eval suites.
  Behavior-change class: fail-aloud artifact/source truth; live command
  construction, detached polling, open-ended checker recovery, provider
  readiness, report rendering, and public eval result failure-class schema are
  unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and 78 oversized
  modules. Proof: focused malformed live-run-result and live-recovery tests,
  full eval-runner unit file, touched-file ruff and format check,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Eval trace JSONL parsing now fails aloud for trajectory grading.
  Malformed or non-object `trace.jsonl` rows no longer disappear while valid
  rows still drive required-tool and completion predicates; trajectory grading
  records `trace_json_invalid` and `trace_parse_errors` under the canonical
  `trajectory_policy_violation` failure class. Owner layer: Eval suites.
  Behavior-change class: fail-aloud artifact/source truth; missing traces,
  valid traces, open-ended success predicates, live eval routing, report
  rendering, and public eval result failure-class schema are unchanged. Metric:
  ratchet stayed at 0 Ruff complexity rows and 78 oversized modules. Proof:
  focused malformed-trace/open-ended predicate tests, full eval-runner unit
  file, touched-file ruff and format check, `git diff --check`, and ratchet.

- 2026-06-19: Eval map-build runtime-map artifact parsing now fails aloud.
  Map-build outcome grading no longer collapses malformed or non-object
  `runtime_metric_map.json` into an empty map that looks like ordinary
  actionability drift. Corrupt required runtime-map evidence now keeps the
  canonical `artifact_missing` failure class while exposing
  `runtime_metric_map_error` in the outcome grader, and missing maps keep the
  existing map-actionability/dependency behavior. Owner layer: Eval suites.
  Behavior-change class: fail-aloud artifact/source truth; live eval routing,
  dependency resolution, open-ended predicates, report rendering, and public
  eval result failure-class schema are unchanged. Metric: ratchet stayed at
  0 Ruff complexity rows and 78 oversized modules. Proof: focused
  map-build/map-consumer tests, full eval-runner unit file, touched-file ruff
  and format check, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console runtime inventory JSON source errors now surface
  explicitly. Malformed or non-object top-level `operator_state.json` and
  `eval_harness.json` files produce non-blocking `source_error` task rows in
  the runtime task payload, and malformed nested `live_status.json` /
  `visual_backend_slot.json` files appear as inactive source-error resources
  on the affected task instead of disappearing as empty metadata. Owner layer:
  Thin Runtime / Server Adapters. Behavior-change class: fail-aloud runtime
  artifact/status source truth; missing optional files, valid active-resource
  blockers, route readiness blocking, artifact links, and tmux/docker/port
  probing are unchanged. Metric: ratchet stayed at 0 Ruff complexity rows and
  78 oversized modules; `runtime_inventory.py` remains oversized and should
  be split only around a future ownership boundary. Proof: focused
  runtime-inventory unit tests, touched-file ruff and format check,
  `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: Operator-console static scene-preview asset coverage was
  consolidated through `$intuitive-tests`: the one long
  `test_static_app_renders_scene_preview_assets` body was split into
  behavior-named assertion helpers for app wiring, MolmoSpaces preview files,
  MolmoSpaces metadata, B1 preview policy, and B1 camera-preview metadata.
  Owner layer: tests for Thin Runtime / Server Adapters static
  operator-console assets. Behavior-change class: test-only consolidation;
  no static app, preview artifact, world catalog, route, or production code was
  changed, and no assertions were intentionally removed. Metric: ratchet
  improved from 1 to 0 Ruff complexity rows and stayed at 78 oversized
  modules. Proof: focused static-assets unit tests, touched-file ruff and
  format check, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: B1 custom-asset visual comparison validation was split into
  input compatibility checks, waypoint-evidence checks, per-waypoint
  pose/image row assembly, and contact-sheet status helpers inside the
  existing comparison checker. Owner layer: Backend Runtime / Environment
  Primitive, with artifact-validation impact on B1 custom render-scene visual
  review. Behavior-change class: helper extraction only; passed same-pose
  custom scene comparisons, pose mismatch failures, low-detail warning mode,
  contact-sheet status, artifact schema, and non-default-route policy flags are
  unchanged. Metric: ratchet improved from 3 to 1 Ruff complexity row and
  stayed at 78 oversized modules; the selected
  `check_b1_map12_asset_visual_comparison.py` complexity rows were cleared.
  Proof: focused asset-visual-comparison contract tests, touched-file ruff and
  format check, `git diff --check`, changed-code review, and ratchet.

- 2026-06-19: B1 semantic-projection accepted review-label validation was
  split into partition-id, label-required-field, and map-polygon geometry
  helpers inside the existing semantic projection builder. Owner layer:
  Backend Runtime / Environment Primitive, with artifact-validation impact on
  B1 room semantic projection inputs. Behavior-change class: helper extraction
  plus focused fail-aloud proof; accepted label projection, duplicate
  partition detection, missing field errors, existing projection payload schema,
  and object-semantic blocked status are unchanged. Metric: ratchet improved
  from 4 to 3 Ruff complexity rows and stayed at 78 oversized modules; the
  selected `build_b1_map12_semantic_projection.py` complexity row was cleared.
  Proof: focused B1 verified-alignment/semantic-projection contract tests,
  touched-file ruff and format check, `git diff --check`, changed-code review,
  and ratchet.

- 2026-06-19: B1 operator-console camera-preview provenance validation was
  split into candidate-shape, alignment-provenance, FPV/chase contract, and
  forbidden-source helpers inside the existing preview renderer owner. Owner
  layer: Thin Runtime / Server Adapters, with artifact credibility impact on
  operator-console B1 preview status. Behavior-change class: helper extraction
  only; accepted Isaac runtime camera previews, navigation-smoke preview
  promotion, rejection error tokens for missing camera contracts, scene-probe
  sources, missing waypoint ids, mixed FPV/chase pairs, and missing residual
  alignment provenance are unchanged. Metric: ratchet improved from 6 to 4
  Ruff complexity rows and stayed at 78 oversized modules; the selected
  `render_scene_previews.py` complexity rows were cleared while the file
  remains oversized at 1400 lines. Proof: focused operator-console scene
  preview unit tests, touched-file ruff and format check, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-19: B1 runtime-bundle semantic projection and robot-consumption
  validation complexity was split into focused helpers inside the existing
  compiler owner. Malformed semantic projection room rows now fail through the
  explicit `ValueError("invalid semantic projection artifact: ...")`
  validation path instead of risking incidental attribute errors during
  duplicate tracking. Owner layer: Backend Runtime / Environment Primitive,
  with artifact-validation impact on B1 Runtime Map Prior Snapshot inputs.
  Behavior-change class: fail-aloud validation cleanup plus helper extraction;
  public CLI arguments, runtime bundle schemas, valid alignment/navigation
  proof handling, valid room-semantic projection materialization, and blocked
  capability payloads are unchanged. Metric: fresh ratchet improved from 10 to
  6 Ruff complexity rows and stayed at 78 oversized modules; the selected
  `compile_b1_map12_runtime_bundle.py` complexity rows were cleared while the
  file remains oversized at 1551 lines. Proof: focused B1 runtime bundle
  contract tests, touched-file ruff and format check, `git diff --check`,
  changed-code review, and ratchet.

- 2026-06-18: Active plan compaction completed. The active plan was rewritten
  from an execution ledger mirror into a concise continuation control doc with
  resume checklist, operating rules, slice selector, active candidates, proof
  ladder, commit-note template, and stop condition. Completed slice detail stays
  in this ledger. Owner layer: process documentation for the refactor stream.
  Behavior-change class: docs/process cleanup only. Metric: active plan reduced
  from 1861 lines to 385 lines. Proof: markdown diff review and
  `git diff --check`.

- 2026-06-18: Live eval product-route timeout configuration now fails aloud.
  Explicit `live_timeout_s` values must be positive finite seconds before the
  live product route is launched or detached completion polling computes a
  deadline, instead of allowing zero, negative, non-finite, or malformed values
  to become immediate/ambiguous wait behavior or late subprocess errors. Owner
  layer: Eval suites and live-run polling. Behavior-change class: fail-aloud
  eval live-run configuration; omitted `live_timeout_s` still leaves the
  blocking subprocess unbounded while using the existing detached-poll default,
  and valid positive timeouts, timeout recovery, completion grace, provider/env
  routing, product commands, grading, and artifact discovery are unchanged.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `test_eval_runner.py` is 1406 lines and remains oversized. Leave test
  pruning/splitting for an `$intuitive-tests` pass. Proof: focused
  invalid-timeout and omitted-timeout regression tests, full eval runner unit
  file, touched-file ruff and format check, py_compile, `git diff --check`, and
  ratchet.

- 2026-06-18: OpenAI Agents SDK performance-profile enabled feature counts now
  fail aloud. Enabled private profile features reject explicit non-positive
  `model_racing_arm_count`, `raw_fpv_image_memory_retain`, and
  `camera_grounded_history_retain` values instead of silently clamping them to
  plausible defaults. Owner layer: Agent Engines And Provider Profiles.
  Behavior-change class: fail-aloud SDK profile configuration; disabled
  feature zero-count metadata, default enabled-profile counts, valid positive
  overrides, CLI/env conflict checks, provider route/default selection, SDK
  model settings, run config payloads, and live runtime behavior are unchanged.
  Same-slice cleanup removed an unused private wire-API wrapper and consolidated
  duplicated private-artifact policy strings without changing payload text.
  Metric: ratchet remains at 0 complexity rows and 79 oversized modules;
  `openai_agents_perf_profile.py` is 799 lines and `test_live_runtime.py` is
  5410 lines. The test file remains oversized; leave pruning/splitting for an
  `$intuitive-tests` pass. Proof: focused non-positive enabled-feature-count
  regression tests, full live-runtime unit test file, touched-file ruff and
  format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: RAW-FPV perception probe private label manifests now fail aloud.
  Explicit `--private-labels` and `--all-visible-labels` manifests require a
  list of object rows with frame identity, object id, category, and bbox/coarse
  locality instead of producing unhelpful attribute errors or silently
  filtering malformed scorer truth out of the report. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: fail-aloud scorer-truth
  input; omitted label inputs, valid hidden/all-visible labels, frame aliasing,
  contrast-derived labels, offline scoring, provider execution, prompt privacy,
  and report artifacts are unchanged. Metric: ratchet remains at 0 complexity
  rows and 79 oversized modules; `run_raw_fpv_perception_probe.py` is 1950
  lines and `test_raw_fpv_perception_probe.py` is 1677 lines. The test file
  remains oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused malformed label-manifest tests, full RAW-FPV perception probe
  test file, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: RAW-FPV perception probe prediction manifests now fail aloud.
  Explicit `--predictions` manifests require list rows, object rows, frame ids,
  and object responses instead of skipping malformed rows or fabricating empty
  candidate responses. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud probe prediction input; omitted
  predictions, valid `predictions` and legacy `runs` rows, JSON-string response
  parsing, offline scoring, provider execution, prompt privacy, and report
  artifacts are unchanged. Metric: ratchet remains at 0 complexity rows and 79
  oversized modules; `run_raw_fpv_perception_probe.py` is 1921 lines and
  `test_raw_fpv_perception_probe.py` is 1595 lines. The test file remains
  oversized; leave pruning/splitting for an `$intuitive-tests` pass. Proof:
  focused malformed prediction-manifest tests, full RAW-FPV perception probe
  test file, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: RAW-FPV perception probe source evidence now fails aloud.
  The probe fails before report generation when an explicit `--raw-run-dir` is
  missing or when all selected RAW-FPV source directories contain no usable FPV
  frames, instead of producing plausible zero-frame prompt/score artifacts.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud probe input evidence; optional contrast-run opt-out, valid raw
  source loading, frame grouping, scorer truth loading, provider execution,
  prompt privacy, scoring, and report artifacts are unchanged. Metric: ratchet
  remains at 0 complexity rows and 79 oversized modules;
  `run_raw_fpv_perception_probe.py` is 1917 lines and
  `test_raw_fpv_perception_probe.py` is 1549 lines. The test file remains
  oversized; leave pruning/splitting for an `$intuitive-tests` pass. Proof:
  focused missing/empty RAW-FPV source regression tests, full RAW-FPV
  perception probe test file, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: RAW-FPV perception probe provider model input now fails aloud.
  The probe validates `codex-router-responses` model input through the provider
  registry before request execution, rejects unknown explicit model ids as
  `provider_config_error`, and resolves blank model input to the route default
  `gpt-5.5`. Owner layer: Agent Engines And Provider Profiles. Behavior-change
  class: fail-aloud probe provider configuration; missing provider env errors,
  valid catalog models, provider route semantics, prompt privacy, scoring, and
  report artifacts are unchanged. Metric: ratchet remains at 0 complexity rows
  and 79 oversized modules; `run_raw_fpv_perception_probe.py` is 1907 lines and
  `test_raw_fpv_perception_probe.py` is 1493 lines. The test file remains
  oversized; leave pruning/splitting for an `$intuitive-tests` pass. Proof:
  focused RAW-FPV provider-model tests, full RAW-FPV perception probe test
  file, touched-file ruff and format check, py_compile, `git diff --check`,
  and ratchet.

- 2026-06-18: RAW-FPV perception probe explicit input files now fail aloud.
  Explicit `--private-labels`, `--all-visible-labels`, and `--predictions`
  paths fail before scoring when the file is absent instead of being treated
  like omitted optional inputs and producing truth-sparse or not-run offline
  reports. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud probe configuration; omitted optional label/prediction
  inputs, valid scorer truth loading, valid prediction loading, provider
  readiness errors, prompt privacy, scoring, and report artifacts are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `run_raw_fpv_perception_probe.py` is 1878 lines and
  `test_raw_fpv_perception_probe.py` is 1385 lines. The test file remains
  oversized; leave pruning/splitting for an `$intuitive-tests` pass. Proof:
  focused missing-input regression tests, full RAW-FPV perception probe test
  file, touched-file ruff and format check, py_compile, `git diff --check`,
  and ratchet.

- 2026-06-18: Visual-parity capture-quality summary metadata now fails aloud.
  The visual-parity summary payload owner rejects missing, malformed, bool,
  non-integer, non-positive, explicit-non-object, or half-specified
  capture-quality resolutions instead of erasing bad values into empty
  resolution metadata and still ranking the row as probe evidence. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud
  manifest/report summary configuration; valid explicit capture-quality probes,
  valid legacy scene dimension inference, saved/metric dimension inheritance,
  report rendering, probe ranking, and native-render metadata classification
  are unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `robot_camera_visual_parity_payloads.py` is 411 lines,
  `summarize_robot_camera_visual_parity.py` is 1976 lines, and
  `test_robot_camera_visual_parity_summary.py` is 2262 lines. The test file is
  already oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused visual-parity capture-quality tests, full visual-parity
  summary test file, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

- 2026-06-18: Robot-camera capture-quality legacy manifests now fail aloud.
  Refresh-report-only capture-quality inference requires explicit legacy scene
  render dimensions and rejects missing, malformed, bool, or non-positive
  dimensions instead of fabricating `540x360` proof metadata. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: fail-aloud legacy
  manifest/report configuration; explicit current-run capture-quality probes,
  valid legacy scene dimensions, saved/metric dimension inheritance, report
  rendering, object-parity skipping, and renderer subprocess routing are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `robot_camera_apple2apple_capture_quality.py` is 258 lines and
  `test_robot_camera_apple2apple_comparison.py` is 3134 lines. The test file is
  already oversized; leave pruning/splitting for an `$intuitive-tests` pass.
  Proof: focused robot-camera capture-quality and parser tests, touched-file
  ruff and format check, py_compile, `git diff --check`, and ratchet.

- 2026-06-18: Shared camera-control request resolution now fails aloud.
  Camera-control request builders and normalizers reject missing, malformed,
  bool, or non-positive render dimensions instead of fabricating `1x1` render
  requests for malformed payloads. Owner layer: Backend Runtime / Environment
  Primitive, with artifact impact on MuJoCo/Isaac scene-probe request
  execution. Behavior-change class: fail-aloud camera-control request
  configuration; explicit valid overrides, valid request payloads, camera model
  defaults, orbit/lens/lighting/color normalization, worker command routing,
  and request artifact schemas are unchanged. Metric: ratchet remains at 0
  complexity rows and 79 oversized modules; `camera_control.py` is 650 lines
  and `test_camera_control.py` is 83 lines. Proof: focused camera-control unit
  tests, selected MuJoCo/Isaac camera-control caller tests, touched-file ruff
  and format check, py_compile, `git diff --check`, and ratchet.

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

- 2026-06-18: MolmoSpaces worker render dimensions now fail aloud. The worker
  CLI rejects non-positive snapshot/robot-view/camera-view `--render-width` /
  `--render-height` values at argument parsing time instead of accepting
  invalid dimensions until worker dispatch validation. Owner layer: Backend
  Runtime / Environment Primitive. Behavior-change class: fail-aloud
  MolmoSpaces worker render configuration; default dimensions, valid positive
  dimensions, existing dispatch-layer validation, worker command names, output
  packet schemas, and backend routing are unchanged. Metric: ratchet remains at
  0 complexity rows and 79 oversized modules; `molmospaces_worker_cli.py` is
  132 lines and `test_relative_navigation_worker_routing.py` is 302 lines.
  Proof: focused worker-routing tests, touched-file ruff and format check,
  py_compile, `git diff --check`, and ratchet.

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

- 2026-06-18: B1 / Map 12 waypoint-capture render dimensions now fail aloud.
  Superseded on 2026-06-19: the approximate bbox waypoint-capture path was
  retired; current B1 / Map12 review uses manual anchors plus the recorded
  top-down camera projector.
  The waypoint capture CLI rejects non-positive `--width` / `--height` values
  at argument parsing time instead of passing invalid dimensions into
  deterministic camera requests and optional old/new Gaussian scene capture
  subprocesses. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud B1 waypoint capture configuration; default
  dimensions, valid positive dimensions, waypoint/extra-point selection,
  approximate bbox transform metadata, capture manifest schema, and capture
  routing are unchanged. Metric at the time: ratchet remained at 0 complexity
  rows and 79 oversized modules; the later-retired waypoint capture path was
  605 lines and its test was 101 lines. Proof: focused B1 waypoint
  capture unit tests, touched-file ruff and format check, py_compile,
  `git diff --check`, and ratchet.

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

- 2026-06-18: B1 Gaussian topdown camera configuration now fails aloud. The
  Gaussian topdown CLI and camera request builder reject non-positive/non-finite
  camera height, non-positive or non-finite near-vertical camera Y offset,
  non-finite target Z, and vertical FOV values outside 1-179 degrees instead of
  writing invalid camera request geometry or silently flipping negative offsets
  positive. Owner layer: Artifacts, reports, and eval suites. Behavior-change
  class: fail-aloud B1 Gaussian topdown camera configuration; default camera
  settings, valid custom positive settings, render dimensions, scene bounds,
  NuRec crop handling, request/report schemas, and capture routing are
  unchanged. Metric: ratchet remains at 0 complexity rows and 79 oversized
  modules; `render_b1_scene_gaussian_topdown.py` is 596 lines and
  `test_b1_scene_gaussian_topdown.py` is 289 lines. Proof: focused B1 Gaussian
  topdown contract tests, touched-file ruff and format check, py_compile,
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
- Cleanup checker robot-camera verification is owned by the current
  `--require-robot-head-camera-fpv` contract; the historical
  `--require-canonical-robot-view-camera-control` spelling is now an explicit
  unsupported checker input instead of a silent alias. Owner layer: Artifacts,
  reports, and eval suites. Behavior-change class: checker-contract migration /
  stale compatibility surface removal. Metric: no new owner; checker/tests
  remain under the current ratchet ceiling. Proof: focused cleanup checker
  contract tests, ruff, format check, diff check, and ratchet. Reopen only if
  active verification commands or tests regain canonical free-camera wording as
  a current robot-FPV acceptance gate.
- Active agent planning guidance now names the staged
  `docs/plans -> review/autoplan/preflight -> GSD` workflow directly instead
  of pointing agents at the unavailable `hybrid-phase-pipeline` skill. Owner
  layer: workflow / agent guidance. Behavior-change class: stale active
  guidance removal. Metric: exact active-guidance search no longer finds the
  old skill name outside this completed ledger. Proof: targeted search and
  docs-only diff check. Reopen only if active repo guidance reintroduces the
  hybrid-router skill as a dependency instead of spelling out the current
  staged workflow.
- The active small-cut checklist no longer carries stale exact-name entries for
  empty camera-labeler maps or `_task_prefix_legacy`. Search found no active
  code, recipe, or human-doc surface with those exact stale artifacts; current
  `_task_prefix` remains a live prompt helper and is not a legacy surface by
  itself. Owner layer: workflow / cleanup plan hygiene. Behavior-change class:
  stale checklist residue removal. Proof: targeted active-surface search and
  docs-only diff check. Reopen only with a concrete active symbol or command
  surface, not the historical checklist names alone.
- Live eval timeout validation is consolidated behind one finite-timeout parser
  with positive and non-negative wrappers, preserving the existing detached
  live route timeout and completion-grace error messages. Owner layer: Eval
  suites / live runtime adapter. Behavior-change class: internal helper
  consolidation. Metric: `live_runtime.py` remains under the current ratchet
  ceiling with no complexity rows. Proof: focused eval runner timeout/live
  runtime tests, ruff, format check, diff check, and ratchet. Reopen only if
  `roboclaws/evals/live_runtime.py` regains duplicated numeric timeout parsing
  policy.
- Eval-harness runtime-prior blocking now checks the current
  `direct-map-build-world-public` source row instead of the retired
  `direct-map-build-world-oracle` id, so the cleanup consumer row can run after
  the selected map-build row passes and writes `runtime_metric_map.json`. Owner
  layer: Eval suites / eval-harness. Behavior-change class: stale launch-axis
  bug fix. Metric: no new owner; harness runner stays under the current
  ratchet ceiling. Proof: focused eval-harness selector tests, ruff, format
  check, diff check, and ratchet. Reopen only if runtime-prior prerequisite
  logic drifts from the row ids declared by `eval_harness_rows.py`.
- Realworld MCP smoke runner result loading now routes required
  `run_result.json` object sources through the shared JSON-source helper, so
  missing, malformed, or non-object smoke result artifacts fail with
  path-labelled source errors before checker/report consumers derive confidence
  from wrong-shaped evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: strict source-reader consolidation. Metric: ratchet
  remains at 1 Ruff complexity row and 80 oversized modules. Proof: focused
  smoke artifact contract tests, ruff, format check, diff check, and ratchet.
  Reopen only if `run_molmo_realworld_agent_mcp_smoke.py` regains direct
  `json.loads(read_text(...))` result artifact parsing or accepts non-object
  result evidence.
- Live Codex Agibot map-build result loading now routes required
  `run_result.json` object sources through the shared JSON-source helper, so
  missing, malformed, or non-object live map-build result artifacts fail with
  path-labelled source errors before route identity checks or report links
  derive confidence from wrong-shaped evidence. Owner layer: Agent Engines and
  Provider Profiles plus Artifacts, reports, and eval suites.
  Behavior-change class: strict source-reader consolidation. Metric: ratchet
  remains at 1 Ruff complexity row and 80 oversized modules. Proof: focused
  Agibot map-build runner unit tests, ruff, format check, diff check, and
  ratchet. Reopen only if `run_live_codex_agibot_map_build.py` regains direct
  `json.loads(read_text(...))` result artifact parsing or accepts non-object
  result evidence.
- Claude live timing now routes present `run_result.json` object sources
  through the shared JSON-source helper, so malformed or non-object Claude
  run-result artifacts fail live timing aloud instead of silently falling back
  to trace-derived timing and preserving a green finished status. Owner layer:
  Agent Engines and Provider Profiles plus Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud source validation. Metric: ratchet remains
  at 1 Ruff complexity row and 80 oversized modules. Proof: focused live
  timing tests, ruff, format check, diff check, and ratchet. Reopen only if
  `run_live_claude_cleanup.py` regains permissive malformed/non-object
  `run_result.json` timing fallback.
- B1 runtime-bundle room-semantics reference validation now delegates per-room
  checks to a focused helper, preserving existing validation errors while
  clearing the last Ruff complexity row. Owner layer: Artifacts, reports, and
  eval suites. Behavior-change class: internal validation helper split. Metric:
  ratchet improved from 1 Ruff complexity row to 0; oversized modules remain
  80. Proof: focused B1 runtime-bundle contract tests, ruff, format check,
  diff check, and ratchet. Reopen only if
  `room_semantics_reference_errors` regains C901 complexity or drifts from the
  checked-in room semantics reference error contract.
- MolmoSpaces USD reference installer state-artifact loading now routes
  required `--state-path` JSON-object sources through the shared JSON-source
  helper while preserving the CLI-facing `SystemExit` wrapper, so missing,
  malformed, or non-object state artifacts use path-labelled source errors
  before missing USD reference collection. Owner layer: Backend Runtime /
  Environment Primitive plus Artifacts, reports, and eval suites.
  Behavior-change class: strict source-reader consolidation. Metric: ratchet
  remains at 0 Ruff complexity rows and 80 oversized modules. Proof: focused
  installer unit tests, ruff, format check, diff check, and ratchet. Reopen
  only if `install_molmospaces_usd_references.py` regains direct
  `json.loads(read_text(...))` parsing for required state artifacts or accepts
  non-object state evidence.
- MolmoSpaces scene metadata optional sidecar loading now routes present
  `scene_metadata.json` object sources through the shared JSON-source helper
  while preserving the missing/corrupt/non-object-as-empty optional metadata
  contract. Owner layer: Backend Runtime / Environment Primitive.
  Behavior-change class: permissive optional source-reader consolidation.
  Metric: ratchet remains at 0 Ruff complexity rows and 80 oversized modules.
  Proof: focused Isaac backend metadata tests, ruff, format check, diff check,
  and ratchet. Reopen only if `isaac_scene_index_metadata.py` regains direct
  `json.loads(read_text(...))` parsing for scene metadata sidecars or starts
  failing missing/corrupt optional metadata that should stay ignorable.
- MolmoSpaces flattened semantic USD scene metadata loading now routes present
  `scene_metadata.json` object sources through the shared JSON-source helper,
  so malformed or non-object metadata fails before semantic label authoring
  while missing metadata still yields the existing blocked summary. Owner
  layer: Backend Runtime / Environment Primitive plus Artifacts, reports, and
  eval suites. Behavior-change class: fail-aloud source-reader consolidation.
  Metric: ratchet remains at 0 Ruff complexity rows and 80 oversized modules.
  Proof: focused source-reader tests, ruff, format check, diff check, and
  ratchet. Reopen only if `prepare_molmospaces_flattened_semantic_usd.py`
  regains direct `json.loads(read_text(...))` parsing for scene metadata
  sidecars or accepts malformed/non-object metadata before semantic label
  authoring.
- Robot-camera apple-to-apple required JSON artifacts and explicit optional
  color-profile artifacts now route through the shared JSON-source helper, so
  required missing, malformed, or non-object state/manifest artifacts fail with
  path-labelled source errors, absent optional color-profile input remains
  empty, and present bad optional input fails aloud. Owner layer: Artifacts,
  reports, and eval suites plus Backend Runtime / Environment Primitive.
  Behavior-change class: strict/permissive source-reader consolidation. Metric:
  ratchet remains at 0 Ruff complexity rows and 80 oversized modules. Proof:
  focused source-reader tests, ruff, format check, diff check, and ratchet.
  Reopen only if `run_robot_camera_apple2apple_comparison.py` regains local
  `json.loads(read_text(...))` helpers for comparison state/manifest artifacts
  or accepts malformed/non-object explicit color-profile inputs.
- Planner proof result summarization now routes proof `run_result.json` reads
  through the shared JSON-source helper while preserving the existing
  missing/malformed/non-object unreadable-result payload shape. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: source-reader
  consolidation with existing unreadable-evidence preservation. Metric:
  ratchet remains at 0 Ruff complexity rows and 80 oversized modules. Proof:
  focused planner-proof summary tests, ruff, format check, diff check, and
  ratchet. Reopen only if `planner_proof_requests.py` regains direct
  `json.loads(read_text(...))` proof-result parsing or stops preserving
  unreadable proof-result evidence for malformed/non-object sources.
- Planner grasp-cache JSON loader validation now routes present
  `*_grasps_filtered.json` sources through the shared JSON-source helper while
  preserving missing, non-object-as-empty, valid transform-count, and
  malformed-as-error preflight behavior. Owner layer: Backend Runtime /
  Environment Primitive plus Artifacts, reports, and eval suites.
  Behavior-change class: source-reader consolidation with existing validation
  status preservation. Metric: ratchet remains at 0 Ruff complexity rows and
  80 oversized modules. Proof: focused planner task feasibility tests, ruff,
  format check, diff check, and ratchet. Reopen only if
  `planner_task_feasibility.py` regains direct `json.loads(read_text(...))`
  grasp-cache parsing or changes JSON cache validation status semantics.
- Scene-sampler prefilter optional JSON sidecar loading now routes through the
  shared JSON-source helper while preserving the permissive optional metadata
  contract: missing, unreadable, malformed, and non-object sources return
  empty metadata. Owner layer: Runnable Surfaces And Presets / launch scene
  sampler. Behavior-change class: permissive optional source-reader
  consolidation with stable empty-metadata semantics. Metric: ratchet remains
  at 0 Ruff complexity rows and 80 oversized modules. Proof: focused
  scene-sampler prefilter optional JSON tests, ruff, format check, diff check,
  and ratchet. Reopen only if `scene_sampler_prefilter.py` regains direct
  `json.loads(read_text(...))` parsing for optional JSON sidecars or stops
  preserving empty metadata for missing/corrupt optional sources.
- B1 base-navigation label validation now splits source, label-row,
  navigation-area, usage, identity, and geometry checks into focused helpers,
  preserving existing validation errors while clearing the two C901 rows
  introduced by the concurrent base-navigation map builder commit. Owner
  layer: Artifacts, reports, and eval suites / map artifact contract.
  Behavior-change class: internal validation helper split. Metric: ratchet
  returns to 0 Ruff complexity rows and 80 oversized modules. Proof: focused
  B1 base-navigation contract tests, ruff, format check, diff check, and
  ratchet. Reopen only if `validate_base_navigation_labels` or
  `_label_contract_errors` regains C901 complexity or base-navigation label
  validation drifts from the checked-in contract tests.
- Scene-sampler facade no longer carries the unused permissive
  `_read_json_if_exists` raw JSON helper or its direct `json` import; active
  preview metadata reads already route through strict scanner/preview source
  readers. Owner layer: Runnable Surfaces And Presets / launch scene sampler.
  Behavior-change class: no-caller dead raw-reader removal. Metric: ratchet
  remains at 0 Ruff complexity rows and 80 oversized modules. Proof: exact
  no-reference search for `_read_json_if_exists` in `scene_sampler.py`,
  focused scene-sampler preview/selection tests, ruff, format check, diff
  check, and ratchet. Reopen only if `scene_sampler.py` reintroduces a local
  permissive raw JSON reader instead of using focused source readers.
- Operator-console MolmoSpaces scene preview rendering now routes required
  `molmospaces_backend_state.json` reads through the shared JSON-source helper,
  so missing, malformed, or non-object backend state fails before scene
  alignment or top-down camera request construction. Owner layer: Thin Runtime
  / Server Adapters. Behavior-change class: strict source-reader
  consolidation. Metric: ratchet remains at 0 Ruff complexity rows and 80
  oversized modules. Proof: focused operator-console preview source tests,
  ruff, format check, diff check, and ratchet. Reopen only if
  `render_scene_previews.py` regains direct `json.loads(read_text(...))`
  parsing for MolmoSpaces backend-state artifacts.
- B1 / Map 12 readiness inspection now routes `navigation_memory.json` through
  the shared navigation-memory source reader, preserving accepted
  `items`/`catalog.navigation_memory` shapes while failing malformed or
  non-object memory sources with canonical path-labelled diagnostics. Owner
  layer: Artifacts, reports, and eval suites / readiness artifact contract.
  Behavior-change class: strict source-reader consolidation. Metric: ratchet
  remains at 0 Ruff complexity rows and 80 oversized modules. Proof: focused
  B1 readiness contract tests, ruff, format check, diff check, and ratchet.
  Reopen only if `check_b1_map12_readiness.py` regains direct
  `json.loads(read_text(...))` parsing for navigation-memory artifacts.
- Isaac Lab runtime smoke checker sidecar loading now reserves stdout-last-JSON
  tolerance for the child-process `--init-result` source only. Explicit
  `--state-path` and `--robot-views-result` artifacts route through the shared
  JSON-object source helper, so prefixed log text, malformed JSON, or
  non-object sidecars fail with path-labelled source errors before state
  consistency or robot-view evidence can produce valid-looking confidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud source validation. Metric: ratchet remains at 0 Ruff complexity
  rows and 80 oversized modules. Proof: focused runtime-smoke checker tests,
  ruff, format check, diff check, changed-code cleanup review, and ratchet.
  Reopen only if `check_isaac_lab_runtime_smoke_result.py` applies
  stdout-last-JSON tolerance to explicit sidecar artifacts again or accepts
  non-object sidecar evidence.
- Agibot map-build checker trace JSONL loading now routes through the shared
  JSONL source helper instead of a local parser. Malformed or non-object trace
  rows fail with row-labelled `Agibot map-build trace` source errors before
  public-trace privacy checks or duplicate-navigation checks can pass from
  partial trace evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud source-reader consolidation. Metric:
  ratchet remains at 0 Ruff complexity rows and 80 oversized modules. Proof:
  focused Agibot and cleanup trace-source checker tests, ruff, format check,
  diff check, changed-code cleanup review, and ratchet. Reopen only if
  `realworld_agibot_map_build_checker.py` regains local raw JSONL trace
  parsing or accepts malformed/non-object trace rows.
- Isaac semantic-pose checker trace JSONL loading now routes through the shared
  JSONL source helper instead of a local parser. Malformed or non-object trace
  rows fail with row-labelled `Isaac semantic-pose trace` source errors before
  semantic-pose pick/place provenance checks can pass from partial trace
  evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud source-reader consolidation. Metric:
  ratchet remains at 0 Ruff complexity rows and 80 oversized modules. Proof:
  focused semantic-pose and cleanup trace-source checker tests, ruff, format
  check, diff check, changed-code cleanup review, and ratchet. Reopen only if
  `isaac_semantic_pose_checker.py` regains local raw JSONL trace parsing or
  accepts malformed/non-object trace rows.
- RAW-FPV private-label trace JSONL loading now routes through the shared JSONL
  source helper instead of a local parser. Malformed or non-object trace rows
  fail with row-labelled `RAW-FPV private-label trace` source errors before
  first-sweep observation extraction can pass from partial trace evidence.
  Owner layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud source-reader consolidation. Metric: ratchet remains at 0 Ruff
  complexity rows and 80 oversized modules. Proof: focused RAW-FPV perception
  probe tests, ruff, format check, diff check, changed-code cleanup review, and
  ratchet. Reopen only if `generate_raw_fpv_private_labels.py` regains local
  raw JSONL trace parsing or accepts malformed/non-object trace rows.
- Cleanup artifact-report trace JSONL loading now routes through the shared
  JSONL source helper instead of a local parser. Malformed or non-object trace
  rows fail with row-labelled `cleanup report trace` source errors before
  stale cleanup report re-rendering can pass semantic timeline evidence from
  partial trace data into report generation. Owner layer: Artifacts, reports,
  and eval suites. Behavior-change class: fail-aloud source-reader
  consolidation. Metric: ratchet remains at 0 Ruff complexity rows and
  80 oversized modules. Proof: focused artifact-report contract tests, ruff,
  format check, diff check, changed-code cleanup review, and ratchet. Reopen
  only if `artifact_report.py` regains local raw JSONL trace parsing or accepts
  malformed/non-object trace rows.
- Planner manipulation probe stdout parsing now fails malformed or non-object
  JSON-looking worker rows aloud instead of silently skipping them before
  runtime diagnostics, CUDA snapshots, worker stage events, or blocked/proven
  manipulation evidence are assembled. Ordinary non-JSON log lines remain
  tolerated. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud structured stdout source validation.
  Metric: ratchet remains at 0 Ruff complexity rows and 80 oversized modules.
  Proof: focused planner manipulation checker tests, ruff, format check, diff
  check, changed-code cleanup review, and ratchet. Reopen only if
  `planner_manipulation_probe_result.py` again silently skips malformed or
  non-object JSON-looking worker stdout rows.
- Household cleanup and Agibot map-build MCP server self-trace loading now
  routes `trace.jsonl` through the shared JSONL source helper instead of local
  ad hoc readers. Malformed or non-object trace rows surface as
  server-labelled source errors at the `done` boundary before readiness,
  policy trace, raw-FPV observation, or run-result evidence can pass from a
  partial MCP trace. Owner layer: MCP Capability Contract And Tools plus Thin
  Runtime / Server Adapters. Behavior-change class: fail-aloud source-reader
  consolidation. Metric: ratchet remains at 0 Ruff complexity rows and
  80 oversized modules. Proof: focused cleanup and Agibot MCP server contract
  tests, ruff, format check, diff check, changed-code cleanup review, and
  ratchet. Reopen only if `realworld_mcp_server.py` or
  `agibot_map_build_mcp_server.py` regains local permissive/self-trace parsing
  or accepts malformed/non-object `trace.jsonl` rows before done evidence.
- Isaac runtime checker no longer carries the unused `_trace_events_from_path`
  helper. Current cleanup trace and Isaac semantic-pose trace source
  validation live in the cleanup-result and semantic-pose checker owners, so
  the stale raw JSONL reader is deleted instead of hardened. Owner layer:
  Artifacts, reports, and eval suites. Behavior-change class: no-caller stale
  raw-reader deletion. Metric: ratchet remains at 0 Ruff complexity rows and
  80 oversized modules. Proof: exact no-reference search for
  `scripts/molmo_cleanup/isaac_runtime_checker.py`
  `_trace_events_from_path`, focused cleanup-result checker import/contract
  tests, ruff, format check, diff check, changed-code cleanup review, and
  ratchet. Reopen only if a real caller needs Isaac-runtime-specific trace
  parsing instead of the existing cleanup or semantic-pose checker trace
  owners.
- Codex and Claude live cleanup timing trace readers now route present
  `trace.jsonl` and Codex event JSONL rows through the shared JSONL source
  helper instead of duplicate local row parsers. Missing trace sidecars remain
  optional, while malformed or non-object present rows keep route-labelled
  source errors before live timing can derive MCP timing confidence. Owner
  layer: Artifacts, reports, and eval suites. Behavior-change class:
  fail-aloud source-reader consolidation. Metric: ratchet remains at 0 Ruff
  complexity rows and 80 oversized modules. Proof: focused Codex/Claude live
  timing trace-source tests, Codex event-summary source test, ruff, format
  check, diff check, changed-code cleanup review, and ratchet. Reopen only if
  `run_live_codex_cleanup.py` or `run_live_claude_cleanup.py` regains local
  raw JSONL row parsing or accepts malformed/non-object present live trace
  rows before route timing/status confidence.
- Report-performance JSONL reads now route through the shared JSONL source
  helper instead of a local row parser, while preserving the
  `ReportPerformanceSourceError` boundary for trace, OpenAI Agents span,
  Codex/Claude event, and provider-request metrics consumers. Malformed and
  non-object present rows now use canonical `path:row` source wording before
  metrics or comparison rows can derive confidence from partial JSONL
  evidence. Owner layer: Artifacts, reports, and eval suites.
  Behavior-change class: fail-aloud source-reader consolidation. Metric:
  ratchet remains at 0 Ruff complexity rows and 80 oversized modules. Proof:
  focused report-performance trace/span/provider JSONL source tests,
  provider-request happy-path test, ruff, format check, diff check,
  changed-code cleanup review, and ratchet. Reopen only if
  `live_performance.py` regains local raw JSONL row parsing or accepts
  malformed/non-object present report-performance JSONL rows before metrics
  confidence.
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

---
refactor_scope: python-quality-backend-entropy
status: CONTINUE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-20
completed_ledger: docs/plans/refactor-python-quality-backend-entropy-completed.md
---

# Refactor Scope: Python Quality And Backend Entropy

## Status

CONTINUE. This file is the active continuation control doc. Completed slices
live only in
`docs/plans/refactor-python-quality-backend-entropy-completed.md`; do not copy
their full execution notes back here.

Latest quality snapshot from 2026-06-20:

- Ruff complexity rows: 0.
- Oversized modules: 79.
- Current emphasis: fresh Ruff complexity rows are clear again. The latest
  fail-aloud slices kept Ruff complexity rows clear again after splitting the
  live eval artifact selector below the C901 threshold, and surfaced malformed
  operator-console runtime inventory
  JSON, eval runtime-map artifacts, eval trace JSONL artifacts, and live eval
  surface JSON artifacts as explicit source-error evidence. Operator-console
  prompt previews now reject malformed or negative cleanup `relocation_count`
  overrides instead of rendering plausible target-count prompts for invalid
  live-route input. Eval-harness
  provider readiness now rejects unknown provider profiles through the provider
  registry instead of treating them like the Codex router when Codex env vars
  happen to exist, and attached eval-harness `eval_results.json` files now
  fail rows aloud when present but malformed or non-object. Explicit
  eval-harness `since=` source refs now fail aloud when `git diff` cannot read
  them instead of producing an empty recommendation set. Operator-console prompt
  previews now reject malformed or negative OpenAI Agents numeric prompt-env
  values instead of rendering default-looking kickoff prompts for bad live-route
  input. OpenAI Agents SDK performance-profile float settings now reject
  non-finite timeout/retry values instead of clamping `nan` to zero or writing
  `inf` into runtime profile metadata, and the live OpenAI Agents runtime now
  rejects boolean/non-finite max-turn, retry, and MCP-timeout metadata/env
  values before writing status/timing evidence. OpenAI Agents SDK live timing
  now fails final timing packets aloud when present MCP timing sources
  (`run_result.json` or `trace.jsonl`) are malformed or non-object instead of
  deriving plausible timing from substitute/partial evidence. Planner proof
  bundle result summaries now surface parseable non-object proof
  `run_result.json` sources as explicit unreadable result evidence instead of
  crashing or deriving proof-summary fields from wrong-shaped JSON. The Nav2
  map-bundle exporter now reports malformed agent-view JSON and non-object
  run-result JSON as concise CLI source errors instead of surfacing tracebacks
  or raw type failures. Runtime Map Prior Snapshot conversion now reports
  malformed or non-object Agibot `navigation_memory.json`, Agibot
  `source.json`, and Nav2 `semantics.json` sources as explicit source-path
  errors instead of raw parser/type failures or wrong-shaped source packets. The
  Nav2 map-bundle validator now reports parseable non-object `semantics.json`
  sources as bundle validation errors instead of raising raw attribute errors
  during validation or projection. B1 runtime bundle compilation now reports
  malformed or non-object explicit semantic projection artifacts as source-path
  errors instead of raw JSON/type failures. MolmoSpaces worker initialization
  now treats adjacent scene JSON as room-label source truth, so malformed,
  wrong-shaped, or label-less source packets fail aloud instead of falling
  through to raw parser/type errors or iTHOR-derived labels. Scene-camera
  comparison now owns Isaac source artifact loading in
  `scene_camera_source_artifacts.py`, validates present `scene_metadata.json`
  packets, and keeps the main comparison file below the hard ceiling instead
  of degrading corrupt metadata into missing-target evidence. The
  operator-state payload now
  reports malformed core
  `operator_state.json` / `live_status.json` / `run_result.json` sources as
  explicit failed source errors instead of erasing them into idle or missing
  state. OpenAI Agents SDK model selection now rejects unknown model overrides,
  and provider/profile route selection rejects catalog-known models that belong
  to the wrong route instead of treating family-compatible names as launchable.
  Coding-agent provider helper and provider-registry CLI route selection now
  reject unknown provider profiles without raw fallback or Python tracebacks.
  RAW-FPV Codex event JSONL and observe text-result JSON source errors now fail
  aloud instead of being skipped into fewer apparent source observations.
  Operator-console control source JSONL errors now fail aloud before appending
  new manual-control rows, preserving operator-intervention evidence instead
  of silently renumbering around corrupt history. Operator-console message
  inbox JSONL errors now surface as console-state and MCP-visible source-error
  packets instead of hiding queued steering evidence behind empty inbox state.
  Operator-console `trace.jsonl` source errors now fail the normalized state
  explicitly instead of letting latest-action/tool summaries derive from a
  partially skipped trace. Operator-console agent event JSONL errors now fail
  the normalized state explicitly instead of letting latest-decision evidence
  derive from a partially skipped agent log. Operator-console route-lock
  readiness now blocks on malformed lock-owner `operator_state.json` /
  `live_status.json` sources instead of treating corrupt owner evidence as
  absent or startable. Report-performance extraction now fails aloud on present
  malformed or non-object JSON/JSONL sources instead of deriving false-green
  performance packets from empty or partial telemetry. Model-latency
  calibration now fails aloud on present malformed or non-object
  `model_call_metrics.jsonl` rows instead of fitting calibration packets from
  silently skipped source evidence. OpenAI Agents SDK event/span/trace metrics
  now fail aloud on present malformed or non-object JSONL rows instead of
  deriving context/cache/growth, retry/fallback, racing, input-filter, event,
  or span metrics from partially skipped source evidence. RAW-FPV OpenAI
  Agents budget guards now fail aloud on present malformed or non-object
  `trace.jsonl` rows instead of deciding budget exhaustion from partial trace
  history. Detached live-run summaries now fail aloud on present malformed or
  non-object `live_status.json`, `live_timing.json`, `run_result.json`, and
  `trace.jsonl` sources instead of rendering pending/unknown summaries from
  corrupt evidence. Agent SDK speedup matrix rows now block on present
  malformed or non-object baseline/candidate run source artifacts instead of
  accepting, rejecting, or recommending speedup work from empty or partial
  performance evidence. Codex and Claude live-run timing writers now surface
  malformed or non-object `trace.jsonl` / Codex event JSONL source errors in
  failed timing/status evidence instead of skipping corrupt rows while writing
  model/timing summaries. Eval-runner graders now fail rows aloud on present
  malformed or non-object optional sidecars (`live_status.json`,
  `live_timing.json`, `advisory_evaluation.json`, and open-ended
  `runtime_metric_map.json`) instead of collapsing corrupt source evidence into
  unavailable/advisory-neutral grading state. Eval-harness detached live-product
  polling now blocks rows on malformed `live_status.json` source evidence instead
  of treating corrupt status as absent while waiting for or accepting terminal
  artifacts. Eval-runner live surface artifact discovery now rejects stale or
  ambiguous sibling `seed-*` run directories instead of grading substitute
  artifacts from a previous or unclear live route. Cleanup report regeneration
  now treats declared scenario/trace/snapshot artifact values as source truth
  under the run directory, rejecting missing, empty, or substitute paths instead
  of reusing CWD files or same-basename colocated files. The Codex cleanup
  apple-to-apple summary now applies the same run-dir source-truth rule to
  declared summary artifacts and robot-view samples, rejecting missing declared
  visual evidence instead of linking CWD substitutes or silently omitting links.
  Operator-console B1 camera preview promotion now resolves declared relative
  view paths only under the source artifact directory and rejects `../` escapes,
  so stale CWD files or sibling run files cannot be promoted as current robot
  camera evidence. Molmo CI live failure diagnostics now publish only the
  latest seed directory with recognized diagnostic evidence, so empty newer
  `seed-*` placeholders no longer hide or replace real failure artifacts.
  Detached live-run summary auto-discovery now requires live-run evidence in
  selected seed directories and explicit empty run directories fail aloud,
  preventing pending/all-missing summaries from placeholder paths. Scene-sampler
  readiness export now rejects enabled artifacts with missing payloads and
  malformed candidate-range CLI input instead of writing `{}` artifacts or
  surfacing tracebacks. Eval HTML reports now render declared missing or
  output-escaping run/report artifact paths as explicit unavailable source
  evidence instead of clickable proof links while preserving verified in-output
  artifact links. Eval dependency resolution now rejects missing or empty
  explicit `runtime_map_prior` paths before direct or live eval product launch
  instead of passing declared stale priors through to the runner. Eval
  regression promotion now treats matched suite `sample_refs` as source truth
  and fails before writing promoted sample/suite artifacts when the declared
  source sample is missing, invalid, or resolves to a different sample id.
  Regression promotion now also validates both the promoted sample payload and
  updated suite payload before writing either artifact, so invalid suite output
  can no longer leave an orphan promoted sample behind. Regression promotion
  now requires declared suite `sample_refs` and validates promotion source
  identity before writing sample/suite artifacts, so missing refs or malformed
  source identity can no longer fabricate a plausible regression sample from
  eval-result fields. Live-agent result
  grading now requires explicit in-trial `eval_effective_run_dir` source
  metadata, so stale trial-directory artifacts cannot stand in for live route
  evidence when a live product runner omits or escapes the effective run
  directory. Eval artifact grading now validates required persisted JSON
  artifacts as object JSON, so corrupt `run_result.json`, `agent_view.json`,
  `runtime_metric_map.json`, or `private_evaluation.json` files cannot pass
  behind a valid in-memory product result. Map-build outcome grading now rejects
  wrong-shaped Runtime Metric Map list fields before minimum-count checks, so
  strings or objects cannot satisfy actionability thresholds via `len()` on the
  wrong type. Live-agent result
  artifact loading now fails aloud on present malformed or non-object
  `live_status.json` / `run_result.json` sources instead of erasing corrupt
  status or completion evidence into unknown or absent state. Eval live-product
  launch setup now rejects invalid cleanup `generated_mess_count` /
  `relocation_count` metadata instead of silently dropping scenario setup from
  the live surface command, and invalid eval sample `scene_index` overrides now
  fail before selecting a substitute scene. Explicit invalid eval
  `scene_source` metadata now fails instead of falling back to
  `procthor-10k-val`. Eval result bundle and HTML report rendering now reject
  malformed scene-sampler projection summary/source counts and source sample
  ids instead of publishing default-looking `0` counts or silently dropping
  bad source rows. Apple-to-apple
  grid execution now rejects malformed existing grid manifests and stable
  malformed live-status sources instead of silently discarding previous row
  evidence or timing out from a fabricated unknown phase. Operator-console
  latest-run history attachment now surfaces malformed run history, operator
  state, or live-status sources as source-error payloads instead of attaching a
  plausible fallback run or metadata-free row. Operator-console manual control
  now rejects malformed `operator_state.json` sources before route lookup,
  MCP calls, control-row append, or state rewrite instead of collapsing corrupt
  state into a missing endpoint or overwriting source evidence. Operator-console
  interaction commands now reject malformed run `operator_state.json` sources
  before appending steer messages, next-goal queues, or session-link updates
  instead of treating corrupt run state as unsupported route/session absence.
  Operator-console session reads now reject malformed session records as source
  errors before command writes instead of treating present corrupt files as
  unknown sessions or dropping session-link evidence. Operator-console
  request-field readiness now rejects present JSON sources that are not objects
  before marking Agibot/B1 launch artifacts ready, so arrays or scalar JSON can
  no longer satisfy required context/proof gates.
  Operator-console stop requests now reject malformed or non-object
  `operator_state.json` sources before child-stop, process termination, lock
  release, or state rewrite, so corrupt stop-state evidence no longer becomes
  a raw JSON/type failure or gets overwritten during stop handling. Stop
  requests also reject malformed or non-object child `live_status.json`
  sources before child-stop, wrapper termination, lock release, or status
  rewrite, so corrupt live child evidence cannot be replaced by a clean
  operator-stop payload. Operator-console launch starts now reserve a unique
  run directory before writing launch logs or `operator_state.json`, so
  same-second run-id collisions or stale directories cannot overwrite existing
  run evidence; empty pre-state reservations are cleaned up on launch-build or
  lock-acquire failure. Operator-console `/artifacts/...` and `/api/raw/...`
  serving now resolves only files under `output/operator-console`, so raw
  log/artifact links can no longer expose arbitrary repo files or escaped
  paths while retaining redaction for valid operator output logs. Runtime
  inventory artifact rows now follow the same operator-output source boundary:
  non-console-output files such as eval-harness manifests and logs remain
  visible by path but no longer advertise dead same-origin artifact/raw links.
  Continue fail-aloud/runtime-source audits from fresh evidence rather than
  reopening closed helper splits; route any future test-shape cleanup through
  `$intuitive-tests`.

The next implementation run should start with a fresh ratchet summary and a
targeted audit of one owner boundary before editing code.

## Resume Checklist

1. Read the repo first-read set required by `AGENTS.md`.
2. Read `$intuitive-flow` and `$intuitive-refactor` before code changes.
3. Check `git status --short`; do not mix unrelated dirty files into this
   stream.
4. Refresh:

   ```bash
   python scripts/dev/check_python_quality_ratchet.py --summary --top 80
   ```

5. Pick one bounded, non-overlapping slice from `Active Candidates`.
6. Add or update focused regression proof before or with the code change.
7. Run the selected focused tests, touched-file static checks, `git diff
   --check`, and ratchet.
8. Update this plan and the completed ledger, then commit explicit paths only.

## Operating Rules

- Two-document contract: this active plan plus the completed ledger. Do not
  create a third cleanup plan or scratch log.
- One verified vertical slice beats broad line shaving. Each slice names its
  owner layer from `ARCHITECTURE.md`, behavior-change class, touched files,
  proof, and non-goals.
- Fail-aloud rule: missing, ambiguous, or inconsistent runtime/source metadata,
  route support, provider profile, env input, map bundle input, visual artifact,
  readiness fact, or config precedence should become an explicit exception,
  blocked/unavailable status, or operator-visible validation error.
- Keep deliberate public defaults only when they are part of a documented
  launch contract and visible in artifacts, readiness payloads, or provider
  diagnostics.
- Compaction rule: every 3-5 accepted slices, move outcomes into the ledger and
  trim this file back to unresolved decisions, current candidates, proof gates,
  and stop conditions.
- Default Python module target: under 800 lines. 800-1200 lines may be
  acceptable for one cohesive owner. 1200-2000 lines remains tracked warning
  debt. Non-generated, non-vendor files above 2000 lines are P1 unless a narrow
  exception is recorded.
- Unit-test pruning must run through `$intuitive-tests` audit/propose before
  deleting tests.
- Documentation cleanup must run through `$intuitive-doc` and keep the human
  surface focused on `README.md`, `ARCHITECTURE.md`, `STATUS.md`, and
  `docs/human/**`.
- Do not reopen closed owner splits without fresh inline ownership drift or a
  hard-ceiling regression.

## Next Slice Selector

Default order after the latest checkpoint:

1. **S: Fail-Aloud Silent Fallback And Env-Var Cleanup** when a false-green
   family is found.
2. **D: OpenAI Agents timing/timeline split** only if fresh evidence makes it
   the best frontier. Do not reopen the closed performance-profile/default
   owner.
3. **B: Visual comparison ownership** only around fresh scene-camera or
   visual-parity summary/report drift.
4. **A: Contract/report ownership** only with fresh facade-private coupling,
   report-section ownership drift, or hard-ceiling regression.
5. **T: Unit-test pruning** through `$intuitive-tests`.
6. **U: Human documentation cleanup** through `$intuitive-doc`.

Choose by fresh call-site, test-value, doc-truth, and false-confidence
evidence, not file size alone.

## Active Candidates

### S: Fail-Aloud Silent Fallback And Env-Var Cleanup

Severity: P1 when a fallback can create false confidence, hide a missing source
asset, mask unsupported launch/profile input, fabricate room/map/visual
semantics, mask missing or conflicting environment-variable input, or make a
route look ready when required evidence is absent. Severity: P2 for local
developer convenience with clear test coverage and no user-facing claim.

Possible owner layers:

- Runnable Surfaces And Presets for launch/profile normalization.
- Agent Engines And Provider Profiles for provider route defaults and model
  selection.
- Thin Runtime / Server Adapters for readiness and live status packets.
- Backend Runtime / Environment Primitive for simulator/map/source asset
  loading.
- Artifacts, reports, and eval suites for preview/report/evidence generation.

Audit the selected owner for `fallback`, `default`, `legacy`, `unknown`,
`synthetic`, `missing`, broad `except`, `or {}`, `or []`, `os.environ`,
`getenv`, `ROBOCLAWS_`, `_API_KEY`, `_BASE_URL`, `_MODEL`,
`provider_profile`, and `alias`. Classify every hit as public default,
explicit blocked/unavailable status, test fixture convenience, or silent
fallback before changing behavior.

Good next families:

- Runtime artifact discovery: report/preview claims should not reuse stale or
  substitute assets when real camera/map/robot-view evidence is absent.
- Environment-variable route selection: collapse duplicate knobs, remove stale
  aliases, reject conflicting key/base-url/model/profile combinations, and
  surface precedence.
- Provider route and launch profile input: unsupported values should fail
  visibly instead of falling back to another route.
- Source map / preview inputs: missing B1/Molmo labels, semantic labels, or
  preview metadata should not be fabricated.
- Worker initialization: required source metadata should fail before state
  write, not create plausible placeholder room/object/receptacle state.

Allowed fallbacks:

- Documented public launch defaults.
- Provider secrets and local proxy/mirror env vars that fail readiness when
  missing or conflicting.
- Explicit operator-console unavailable/blocked readiness states.
- Test fixtures that intentionally omit optional fields and assert the
  resulting error/blocked behavior.
- Historical artifact readers that preserve old reports without relabeling
  them as current product proof.

### T: Unnecessary Unit-Test Pruning

Route through `$intuitive-tests` first. Start with one domain, classify tests as
keep, merge, delete, or reclassify, and preserve the last meaningful proof of
parser behavior, validation, fail-aloud errors, public CLI/report/MCP
contracts, artifact schemas, provider route semantics, and known regressions.

Good families:

- Provider/env tests that duplicate constants or route tables without
  exercising canonical resolution, readiness failure, or visible diagnostics.
- Operator-console tests that assert static DOM/route wiring without launch
  readiness, redaction, locks, status transitions, or artifact links.
- Eval-harness tests that duplicate manifest keys one field at a time instead
  of proving selected rows, blockers, promotion packets, or result contracts.
- Molmo cleanup worker/report tests that assert helper shape, static file
  names, or copied fixture metadata already covered by stronger tests.

### U: Human Documentation Surface Cleanup

Route through `$intuitive-doc`. Human-authoritative scope is `README.md`,
`ARCHITECTURE.md`, `STATUS.md`, and `docs/human/**`. Process/evidence scope is
`.planning/**`, `docs/plans/**`, `docs/status/active/**`,
`docs/retrospectives/**`, ADR detail, `output/**`, generated reports, and
screenshots unless a curated human doc deliberately promotes a specific item.

Good families:

- Current-looking docs that still show historical command grammar, profile
  names, or retired route names as copyable commands.
- `docs/human/**` pages that duplicate README/ARCHITECTURE/STATUS tables but
  lag behind current launch architecture.
- Agent-only local harness or skill-routing notes that belong in
  `docs/agents/**`.
- Old proof/evidence detail in human docs where a short current summary plus a
  process/evidence link is enough.

### A: Contract And Report Hard-Ceiling Split

Currently not the default next slice. Reopen only with a fresh hard-ceiling
regression or direct facade-private/report ownership drift.

Closed or cohesive owners:

- Public map/projection construction:
  `realworld_contract_projection.py`.
- Agent-view and policy evidence packets:
  `realworld_contract_payloads.py`.
- Done-readiness pending/held cleanup candidates:
  `realworld_done_readiness.py`.
- Public manipulation/tool response envelopes:
  `realworld_tool_responses.py`.
- Visual-candidate lifecycle:
  `realworld_visual_candidate_lifecycle.py`.
- Camera-label producer inputs:
  `realworld_visual_candidate_declarations.py`.
- Runtime Metric Map target/public-anchor construction:
  `realworld_runtime_map_targets.py`.
- Proof-bundle result rendering:
  `report_sections_proof_bundle.py`.

Candidate A is valid only for a new `RealWorldCleanupContract` boundary such as
agent-view wrapper cleanup, runtime-map/cleanup-worklist caller migration,
remaining report-section ownership, or another named facade-private coupling
point.

### B: Visual Comparison Pipeline Split

Candidate B remains valid only around fresh scene-camera / visual-parity
ownership drift. Do not reopen closed boundaries without evidence that the
runner or summarizer is rebuilding those packets inline again.

Closed or cohesive owners:

- Scene-camera report rendering: `scene_camera_report*.py`.
- Apple image metrics and residual diagnostics:
  `robot_camera_apple2apple_image_metrics.py`.
- Apple object parity: `robot_camera_apple2apple_object_parity.py`.
- Selected RGB/focus/nonblank/crop evidence:
  `robot_camera_apple2apple_rgb_evidence.py`.
- Visual-state contract evidence:
  `robot_camera_apple2apple_visual_state.py`.
- Object Gate / Render Gate diagnostics:
  `robot_camera_apple2apple_object_gate.py`.
- Report rendering: `robot_camera_apple2apple_report.py`.
- Camera-contract diagnostics:
  `robot_camera_apple2apple_camera_contract.py`.
- Native Isaac render diagnostics:
  `robot_camera_apple2apple_native_render.py`.
- Scene-camera source artifacts:
  `scene_camera_source_artifacts.py`.

Preserve runner orchestration, top-level manifest/report attachment, capture
worker boundaries, and artifact schemas unless explicitly selected.

### C: Planner Manipulation Probe Runner Split

Cleared from P1 for now. Reopen only if
`scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py` crosses 2000
lines again or starts rebuilding either closed owner directly.

Closed owners:

- Runtime/module/CUDA/headless diagnostics:
  `planner_probe_runtime_diagnostics.py`.
- Task-sampler robot placement, cleanup binding, sampler failure diagnostics,
  and binding promotion:
  `planner_probe_task_sampler_diagnostics.py`.

### D: OpenAI Agents Live Runtime / Runner Split

Candidate D is valid only for fresh runner/driver evidence. Keep SDK driver
internals separate from runner lifecycle.

Closed owners:

- Model-input compaction, raw-FPV/camera-grounded history policy, and metrics:
  `openai_agents_model_input.py`.
- Runner-side Agent SDK performance profile/default/config resolution:
  `scripts/molmo_cleanup/openai_agents_perf_profile.py`.
- SDK span capture:
  `openai_agents_spans.py`.

Possible later slice: timing/latency/timeline ownership. If selected, move
runner timing breakdown, live timing timeline, timeline segment builders,
latency attribution, MCP trace/control-plane timing, unattributed model seconds,
and compact metric groups to a focused owner while preserving
`live_timing.json`.

Non-goals unless explicitly approved: provider route semantics, model thinking
policy, MCP session behavior, continuation policy, checker gates, event/span
schemas, model-input compaction schemas, live-status payloads, and timing
artifact schemas.

### E-H: P2 Rows And Small Cuts

Use these only when they remove stale surface, duplicate concept, or false
confidence without postponing a stronger P1 frontier.

- Live runtime / eval harness rows:
  `roboclaws/evals/live_runtime.py::wait_for_live_surface_completion` and
  `skills/eval-harness/scripts/run_eval_harness.py::_row_blockers`.
- B1 preview row:
  `scripts/operator_console/render_scene_previews.py::render_b1_map12_preview`.
- Behavior-test fixture-builder work in selected operator-console tests.
- Stale small cuts: duplicated lane prose.

Keep public `camera_labeler` / `visual_grounding_pipeline_id` semantics unless
a selected slice explicitly migrates them.

## Cleared Or Parked

Reopen these only with fresh hard-ceiling regression, direct owner drift, or a
product slice that needs them:

- Backend worker hard-ceiling split.
- Scene-sampler hard-ceiling split.
- Agibot contract rehearsal below-ceiling cleanup.
- Report-performance skill wrapper consolidation.
- `PhysicalObservationProvider`.
- Scene-sampler public alias removal.
- Broad behavior-test pruning.
- Closed owner families listed in `Active Candidates`.

## Evidence Ladder

- Static: `ruff check <touched files>`, `ruff format --check <touched files>`,
  and `python scripts/dev/check_python_quality_ratchet.py --summary --top 80`.
- If a future slice creates a new untracked Python owner, run
  `git add -N <path>` before relying on ratchet line-count output.
- Focused tests: use `./scripts/dev/run_pytest_standalone.sh <tests> -q`.
- Contract/report changes: include the relevant contract or report tests.
- Fail-aloud cleanup changes: include at least one regression test where the
  old path silently fabricated/substituted data and the new path raises a clear
  error or returns explicit blocked/unavailable status.
- Unit-test pruning: run focused collection plus the selected domain's
  remaining behavior/contract tests; include keep/merge/delete/reclassify
  counts.
- Documentation cleanup: use `$intuitive-doc` audit/cleanup rules, verify stale
  claims and path consumers with `rg`, and run command/doc build checks only
  when changed runbook commands need validation.
- Changed-code review: after non-doc implementation, run `$intuitive-refactor`
  changed-code review on the changed scope before final verification.
- Agent-facing/eval/launch changes: prefer `just agent::eval recommend` or
  `just agent::eval execute` for gate selection.
- Simulator/live claims: claim them only after an explicit local run on a ready
  environment.
- Docs-only planning refresh: `git diff --check` is enough; do not run behavior
  tests when no code or contracts changed.

## Commit Notes Template

For each completed implementation slice, append one compact bullet to the
completed ledger with:

- durable behavior or ownership effect;
- owner layer;
- behavior-change class;
- metric delta when relevant;
- proof class;
- closed/reopen rule when the slice establishes an owner boundary.

Then update this file only when candidate ordering, stop conditions, or reopen
rules changed.

## Stop Condition

Stop this cleanup stream only after a fresh completion audit proves all of the
following:

- Non-generated, non-vendor files above 2000 lines are split below the ceiling
  or have a recorded narrow exception.
- Production/shared Ruff complexity rows are at or near zero.
- Remaining test complexity is fixture-builder debt with clear ownership, not
  one-off long test bodies.
- Low-signal unit tests in accepted domains have been deleted, merged, or
  reclassified, and remaining unit tests protect behavior/failure modes rather
  than static implementation shape.
- Backend id, runtime metadata, artifacts, and evidence attachments use common
  surfaces instead of repeated concrete-class or `backend == ...` branching.
- Silent fallback families that can create false confidence are removed,
  converted to explicit blocked/unavailable status, or documented as deliberate
  public defaults with tests.
- Env-var families no longer provide hidden route compatibility: canonical
  knobs are documented, duplicate aliases are removed or explicitly blocked,
  precedence is tested, and missing/conflicting provider keys, base URLs, or
  model/profile settings fail before launch readiness.
- The curated human documentation surface is small and current: README,
  ARCHITECTURE, STATUS, and `docs/human/**` describe active project truth;
  stale commands/routes/profile names are gone or historical outside the human
  surface; agent-only runbooks and execution evidence live in agent/process
  surfaces with current links.
- A fresh reduce-entropy round finds no P0/P1 or material P2 candidate in this
  code-size/backend-complexity class.

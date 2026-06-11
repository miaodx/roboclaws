---
plan_scope: report-performance-analysis-skill
status: Proposed
created: 2026-06-11
last_reviewed: 2026-06-11
source:
  - User request: add normalized report performance analysis and custom skill
  - docs/status/active/live-agent-runtime-sdk-spike.md
  - docs/plans/live-agent-runtime-sdk-perf-followups.md
related_adrs:
  - docs/adr/0135-use-sanitized-report-performance-artifacts-for-speed-claims.md
---

# Report Performance Analysis Skill

## Goal

Make live-agent report comparison honest under unstable networks.

The current report workflow can show useful wall-clock timing, but wall time by
itself is not a stable speedup signal. A run can be slower because the agent did
more work, because the provider/network was slower, because cache was missed, or
because robot/report-side work changed. This plan adds a stable analysis layer
that compares effect, call count, model-call work, normalized expected model
time, and residual latency across Agent SDK, Codex, and Claude Code routes.

This plan covers the three approved additions:

1. A unified report performance metric contract.
2. A cross-engine model-call metrics artifact.
3. A custom `report-performance-analysis` skill with fixed scripts and
   agent-assisted analysis.

It also records the additional reduce-entropy candidates found in one bounded
discovery loop over the report/live-agent performance surface.

## Current Evidence

- `openai-agents-live` already records rich SDK telemetry in `live_timing.json`,
  including `context_metrics`, `cache_metrics`, `context_growth_metrics`, and
  `model_or_sdk_unattributed_s`.
- `run_live_codex_cleanup.py` records runner timing, MCP trace timing, Codex
  event counts, usage, and best-effort model API duration when Codex JSON events
  expose duration fields.
- `run_live_claude_cleanup.py` writes `claude-events.jsonl` but does not yet
  write a `live_timing.json` equivalent, so cross-engine comparison is
  asymmetric.
- `summarize_live_run.py` can summarize one run and compare an explicit Agent
  SDK comparison manifest, but it still has a hard-coded `18m30s` single-run
  baseline display and SDK-specific comparison language.
- `run_agent_sdk_perf_matrix.py` has quality and privacy gates, but its metric
  extraction duplicates part of `summarize_live_run.py` and is scoped to the
  Agent SDK speedup matrix.

## Non-Goals

- Do not promote `openai-agents-live` to a public/default route.
- Do not change cleanup success semantics. `done` / `run_result.json` remains
  the task success signal.
- Do not store raw prompts, model text, function inputs/outputs, full tool
  payload bodies, credentials, private evaluator truth, or compact continuation
  packets.
- Do not claim publishable speedup from a single live run. Single-run outputs
  are diagnostic unless a repeatability policy accepts them.
- Do not hide all latency variance by normalizing everything to 0/1. The
  normalized estimate is a diagnostic model, not a replacement for observed
  time.

## Compatibility Policy

No backward compatibility is required for old performance-summary output
formats, old hard-coded baselines, or duplicated SDK-only comparison helpers.
Prefer replacing stale report-analysis paths with the new metric contract over
maintaining adapters. Keep only the active artifact boundary, task success
semantics, and privacy rules stable.

## Resolved Contract Decisions

ADR-0135 owns the durable artifact, privacy, and speed-claim boundary for this
plan.

- `roboclaws_report_performance_metrics_v1` is a durable maintainer run-artifact
  contract, not a public command/API surface. Breaking schema changes should use
  a new version.
- `model_call_metrics.jsonl` is owned by the shared extractor and privacy gate.
  Live runners may call the extractor at run end, but SDK, Codex, and Claude
  routes should not maintain independent metric contracts.
- Version 1 is scoped to Agent SDK, Codex CLI, and Claude Code. Other engines
  are out of scope or explicitly `unavailable` until compatible sanitized
  telemetry exists.
- A single live run remains diagnostic. A speedup claim needs an explicit
  baseline or manifest, same-or-better quality, and repeat rows or a recorded
  waiver in the decision packet.
- Calibration coefficients are not authoritative repo defaults until produced
  by a named calibration dataset with sample counts and error statistics.

## Metric Contract

Each run should expose one normalized performance packet derived from sanitized
artifacts:

```text
report_performance_metrics:
  schema: roboclaws_report_performance_metrics_v1
  run_identity:
    surface
    intent
    task_name
    agent_engine
    provider_profile
    model
    evidence_lane
    seed
    profile_id
  quality:
    checker_state
    terminal
    cleanup_status
    completion_status
    restored_count
    total_targets
    mess_restoration_rate
    sweep_coverage_rate
    disturbance_count
    failed_or_noop_tool_count
  call_counts:
    model_call_count
    agent_attempt_count
    continuation_count
    mcp_tool_call_count
    mcp_tool_counts
    non_tool_turn_count
  model_work:
    total_input_tokens
    total_cached_input_tokens
    total_uncached_input_tokens
    total_output_tokens
    total_reasoning_tokens
    max_input_tokens
    p50_input_tokens
    p95_input_tokens
    image_input_count
    image_input_pixels
    unavailable_metrics
  timing:
    observed_wall_s
    runner_agent_s
    mcp_elapsed_s
    mcp_between_tool_gap_s
    mcp_tool_handler_s
    robot_view_capture_s
    observed_model_api_s
    estimated_model_work_s
    model_latency_residual_s
    non_model_s
```

Comparison must lead with quality and call/work counts before wall time. A
candidate is not accepted as a speed win when it is faster but worse unless the
decision packet explicitly records the waiver.

## Normalized Model-Time Policy

Use a calibrated estimate, not a binary normalization:

```text
estimated_model_work_s =
  intercept_by_provider_model
  + uncached_input_tokens * uncached_input_s_per_token
  + cached_input_tokens * cached_input_s_per_token
  + output_tokens * output_s_per_token
  + reasoning_tokens * reasoning_s_per_token
  + image_input_units * image_s_per_unit
```

Rules:

- Coefficients are grouped by `provider_profile`, `model`, `agent_engine`, and
  optionally `evidence_lane`.
- When no calibrated coefficients exist, report
  `estimated_model_work_s.available=false` with a clear limitation. Do not
  silently use zero.
- `model_latency_residual_s = observed_model_api_s - estimated_model_work_s`
  when per-model-call durations are available.
- If per-call model durations are unavailable, compute the broader residual
  from runner and MCP buckets and label it as `model_or_sdk_residual_s`.
- Residual is diagnostic. It may include provider queueing, network delay,
  SDK/CLI orchestration, retries, and unmodeled model behavior.
- Report p50/p95 residuals when repeated calls exist; do not use only totals.

## Cross-Engine Model Call Artifact

Add a sanitized per-call artifact:

```text
model_call_metrics.jsonl
```

Each line:

```json
{
  "schema": "roboclaws_model_call_metric_v1",
  "agent_engine": "openai-agents-sdk|codex-cli|claude-code",
  "provider_profile": "codex-env|mify|mimo-anthropic|...",
  "model": "gpt-5.5|xiaomi/mimo-v2.5|...",
  "attempt_index": 0,
  "call_index": 0,
  "started_at_epoch": 0.0,
  "duration_s": 0.0,
  "input_tokens": 0,
  "cached_input_tokens": 0,
  "uncached_input_tokens": 0,
  "output_tokens": 0,
  "reasoning_tokens": 0,
  "image_input_count": 0,
  "image_input_pixels": 0,
  "status": "success|failure|unavailable",
  "failure_class": "",
  "source": "openai_agents_span|codex_event|claude_event|unavailable",
  "limitations": []
}
```

Availability policy:

- The shared extractor owns the schema and privacy filtering. Runner-specific
  code may invoke it at run end, but should not duplicate the artifact contract.
- OpenAI Agents SDK should derive rows from sanitized response spans.
- Codex should derive rows from `codex-events.jsonl` where usage and duration
  fields exist; otherwise emit aggregate availability limitations.
- Claude Code should derive rows from `claude-events.jsonl` where stream-json
  usage and timing fields exist; otherwise emit explicit unavailable rows or
  limitations.
- Missing usage or duration is an unavailable field, not zero.

## Custom Skill

Create a repo-local skill:

```text
skills/report-performance-analysis/
  SKILL.md
  scripts/extract_live_report_metrics.py
  scripts/compare_live_report_metrics.py
  scripts/calibrate_model_latency.py
  references/metric-contract.md
  templates/comparison-manifest.json
```

Skill behavior:

1. Read the metric contract and identify target run directories.
2. Run fixed extraction scripts first.
3. Run comparison/calibration scripts when the user asks for A/B, matrix, or
   normalized latency analysis.
4. Answer questions using generated JSON packets, not by scraping `report.html`
   or re-reading raw prompts.
5. Flag missing telemetry, apples-to-oranges baselines, faster-but-worse
   outcomes, and high residual latency.

The skill should support questions like:

- "Which run is actually faster after accounting for model-call work?"
- "Did this optimization reduce calls or only get lucky on network?"
- "Where is the remaining latency bucket?"
- "Is this comparison valid as a speedup claim?"

## Entropy Candidates

### Candidate 1: Unified Report Performance Metric Contract

- Severity: P1
- Entropy source: false confidence.
- Materiality: Wall-clock speedup can pass review while hiding network/provider
  variance or behavior regressions.
- Impact radius: report/live-agent workflow.
- Maintainer test: A reviewer can distinguish observed wall time, model work,
  residual latency, robot/backend time, and task quality in one packet.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`, and a new shared
  metrics module.
- Owner skill: normal implementation.
- Suggested proof: fixtures compare two runs where wall time improves but
  quality regresses, and the decision packet rejects the candidate.
- Execution risk: safe; artifact-only.

### Candidate 2: Cross-Engine `model_call_metrics.jsonl`

- Severity: P1
- Entropy source: instrumentation asymmetry.
- Materiality: SDK spans, Codex events, and Claude events expose different
  levels of model-call usage/timing, so cross-engine comparison is currently
  uneven.
- Impact radius: SDK, Codex, Claude live runners.
- Maintainer test: A single extractor can report model call count and token
  work for every route, with explicit limitations when a provider does not
  expose fields.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `scripts/molmo_cleanup/run_live_codex_cleanup.py`,
  `scripts/molmo_cleanup/run_live_claude_cleanup.py`,
  `roboclaws/agents/live_runtime.py`.
- Owner skill: normal implementation.
- Suggested proof: fixture rows for SDK, Codex, Claude, and unavailable usage.
- Execution risk: privacy-sensitive; gate forbidden raw fields.

### Candidate 3: `report-performance-analysis` Skill

- Severity: P2
- Entropy source: recurring rediscovery.
- Materiality: Without a skill, future comparisons will keep re-deriving the
  same metric rules and limitations from scattered scripts.
- Impact radius: developer workflow and future AI-agent analysis.
- Maintainer test: A user can ask the skill about one run or a manifest and get
  a bounded answer backed by generated metrics.
- Affected paths: `skills/report-performance-analysis/**`.
- Owner skill: skill creator / normal implementation.
- Suggested proof: skill scripts run on committed fixtures and produce JSON.
- Execution risk: safe after metric contract exists.

### Candidate 4: Coding-Agent Timing Parity

- Severity: P1
- Entropy source: live source drift.
- Materiality: Claude Code live runs currently write `claude-events.jsonl` but
  do not appear to write `live_timing.json`, while Codex and SDK runs do. This
  makes single-run and cross-run timing summaries asymmetric.
- Impact radius: Claude live cleanup route and comparison tooling.
- Maintainer test: `summarize_live_run.py` should show runner/MCP/model
  timing for Claude with the same fields it can show for Codex/SDK, or explicit
  unavailable limitations.
- Affected paths: `scripts/molmo_cleanup/run_live_claude_cleanup.py`,
  `tests/unit/molmo_cleanup/test_ci_live_reports.py`.
- Owner skill: normal implementation.
- Suggested proof: Claude runner unit test writes `live_timing.json` with
  runner and MCP timing after a fake run.
- Execution risk: safe; no provider call required.

### Candidate 5: Shared Metric Extraction Module

- Severity: P1
- Entropy source: recurring rediscovery and duplicated logic.
- Materiality: `summarize_live_run.py` and `run_agent_sdk_perf_matrix.py`
  separately parse live timing, quality, trace tools, terminal state, and
  context metrics. Drift here can make the CLI summary and matrix gate disagree.
- Impact radius: report summary, matrix preflight, future skill scripts.
- Maintainer test: One fixture should produce the same performance packet for
  single-run summary, A/B comparison, and matrix decision packet.
- Affected paths: new module such as `roboclaws/reports/live_performance.py`,
  plus the two existing scripts.
- Owner skill: normal implementation.
- Suggested proof: unit tests call the shared extractor directly and both CLIs
  consume it.
- Execution risk: safe; old duplicate parser behavior may be removed rather
  than preserved.

### Candidate 6: Remove Hard-Coded Single-Run Baseline

- Severity: P2
- Entropy source: false comparison.
- Materiality: `summarize_live_run.py` displays a hard-coded `18m30s`
  baseline for single-run summaries. That value is not a valid baseline for all
  providers, lanes, routes, or tasks.
- Impact radius: developer interpretation of single-run output.
- Maintainer test: A single-run summary should not imply speedup unless a
  baseline run or baseline manifest is supplied.
- Affected paths: `scripts/molmo_cleanup/summarize_live_run.py`,
  `tests/unit/molmo_cleanup/test_summarize_live_run.py`.
- Owner skill: normal implementation.
- Suggested proof: summary without baseline prints no speedup claim; summary
  with explicit baseline prints the comparison.
- Execution risk: safe; wording/output change only.

### Candidate 7: Machine-Readable Comparison Output

- Severity: P2
- Entropy source: workflow friction.
- Materiality: Current comparison output is mostly text. Future skills and
  reviewers need JSON decision packets to avoid scraping terminal tables.
- Impact radius: comparison workflow and custom skill.
- Maintainer test: `compare_live_report_metrics.py` can write JSON and optional
  markdown/HTML from the same packet.
- Affected paths: new comparison script and tests.
- Owner skill: normal implementation.
- Suggested proof: comparison manifest writes `comparison.json` with quality,
  observed timing, normalized estimate, residual, and limitations.
- Execution risk: safe.

### Candidate 8: Calibration Dataset And Coefficient Governance

- Severity: P2
- Entropy source: false precision.
- Materiality: A normalized model-time estimate without named coefficients,
  sample counts, and confidence limits can look more authoritative than it is.
- Impact radius: performance analysis interpretation.
- Maintainer test: Every normalized estimate states coefficient source,
  sample count, p50/p95 error or limitation, and whether the estimate is
  calibrated or fallback/unavailable.
- Affected paths:
  `skills/report-performance-analysis/scripts/calibrate_model_latency.py`,
  `references/metric-contract.md`, possibly `docs/status/active/**` for local
  calibration packets.
- Owner skill: diagnose / normal implementation.
- Suggested proof: calibration script fits coefficients from fixture rows and
  reports unavailable estimates when sample count is too low.
- Execution risk: medium; avoid publishable claims from weak calibration.

### Candidate 9: Privacy Gate Expansion For New Telemetry

- Severity: P1
- Entropy source: privacy regression risk.
- Materiality: New per-call artifacts and skill scripts increase telemetry
  volume. Existing privacy scans focus on SDK foundation safe globs and must be
  extended before model-call artifacts become standard.
- Impact radius: report performance artifacts and matrix gates.
- Maintainer test: Privacy gate fails on raw prompt/model text/function
  payloads in `model_call_metrics.jsonl` and passes sanitized token/timing
  fields.
- Affected paths:
  `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`, new extractor tests,
  new skill scripts.
- Owner skill: normal implementation.
- Suggested proof: fixture with forbidden keys in model-call metrics fails the
  gate.
- Execution risk: privacy-sensitive; required before live publication.

## Execution Plan

### Phase 1: Shared Extractor And Contract

- Add a shared report performance extractor module.
- Define `roboclaws_report_performance_metrics_v1`.
- Replace duplicated parsing in `summarize_live_run.py` and
  `run_agent_sdk_perf_matrix.py` with the shared extractor.
- Remove the hard-coded `18m30s` single-run baseline.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_summarize_live_run.py \
  tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py
```

### Phase 2: Model-Call Metrics Across Engines

- Emit or derive `model_call_metrics.jsonl` for SDK, Codex, and Claude routes.
- Add unavailable-state handling for missing provider usage/timing fields.
- Add Claude `live_timing.json` parity. Do not keep a separate Claude-only
  timing adapter unless it is strictly an internal migration step.
- Extend privacy gates to scan new sanitized metric artifacts.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/molmo_cleanup/test_ci_live_reports.py
```

### Phase 3: Normalized Model-Time Estimator

- Add coefficient schema and calibration script.
- Estimate model work from uncached input, cached input, output, reasoning, and
  image units.
- Surface residual latency and unavailable limitations in both single-run and
  A/B outputs.
- Keep observed wall time visible.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_summarize_live_run.py
```

### Phase 4: Stable Compare CLI

- Add `scripts/reports/extract_live_report_metrics.py` or equivalent wrapper.
- Add `scripts/reports/compare_live_report_metrics.py`.
- Accept explicit run dirs and manifest files.
- Write machine-readable JSON plus concise terminal output.
- Reject apples-to-oranges baselines unless explicitly marked diagnostic.

Proof:

```bash
.venv/bin/python scripts/reports/compare_live_report_metrics.py \
  --manifest docs/status/active/agent-sdk-perf-opt-0610-comparison-manifest.json \
  --output output/report-performance-analysis/comparison.json
```

### Phase 5: Repo Skill

- Add `skills/report-performance-analysis/SKILL.md`.
- Reuse the fixed scripts instead of teaching the skill to parse reports
  ad hoc.
- Add templates and reference docs.
- Include examples for one-run, two-run, and manifest comparisons.

Proof:

```bash
find skills/report-performance-analysis -maxdepth 3 -type f -print
.venv/bin/python skills/report-performance-analysis/scripts/extract_live_report_metrics.py \
  tests/fixtures/agent_sdk_speedup_foundation/world_public_candidate
```

## Implementation Preflight

Preflight status: draft, approved for execution only after an explicit user
approval such as `LGTM`, `approve`, or `go ahead`.

Canonical source:

```text
docs/plans/2026-06-11-report-performance-analysis-skill.md
```

Execution route:

```text
/goal execute docs/plans/2026-06-11-report-performance-analysis-skill.md with intuitive-flow
```

Implementation scope:

- Build the shared `roboclaws_report_performance_metrics_v1` extractor.
- Derive sanitized `model_call_metrics.jsonl` rows for Agent SDK, Codex CLI,
  and Claude Code where telemetry exists.
- Add Claude `live_timing.json` parity for deterministic/fake runner tests.
- Remove the hard-coded single-run speed baseline from `summarize_live_run.py`.
- Add normalized model-time estimation with explicit unavailable calibration
  behavior.
- Add report metric extract/compare CLIs with machine-readable JSON output.
- Add `skills/report-performance-analysis/` with fixed scripts and reference
  contract docs.
- Extend privacy/schema gates for the new metric artifacts.

Implementation non-goals:

- No provider-backed live rows are required for the first implementation.
- Do not promote `openai-agents-live`.
- Do not change `done` / `run_result.json` cleanup success semantics.
- Do not preserve obsolete performance-summary formats or duplicated SDK-only
  comparison helpers.
- Do not store raw prompts, model text, full tool payload bodies, credentials,
  private evaluator truth, or compact continuation packets.

Success requires:

- Shared extractor fixtures cover quality, call counts, model work, timing,
  normalized estimate availability, residual latency, and unavailable telemetry.
- Privacy fixtures reject forbidden prompt/model/tool/private-truth fields in
  `model_call_metrics.jsonl`.
- Single-run summaries make no speedup claim without an explicit baseline or
  manifest.
- Comparison output rejects faster-but-worse candidates unless a decision
  packet records the waiver.
- The repo skill scripts run against committed fixtures and answer from
  generated metric JSON, not `report.html` scraping.

Implementation is blocked if:

- A new public artifact field materially changes ADR-0135's privacy or speed
  claim boundary.
- A deterministic gate cannot be made to pass without changing cleanup success
  semantics.

Full route no-regression or live speed claims are blocked until the selected
product/live gates below run successfully with required credentials, runtime,
network preflight, and budget approval.

## Validation Matrix

The focused validation selector was run on 2026-06-11:

```bash
just agent::harness agent-validation recommend \
  plan=docs/plans/2026-06-11-report-performance-analysis-skill.md \
  budget=focused
```

Recommendation artifacts:

- `output/agent-validation-matrix/20260611T084051Z/validation_matrix.json`
- `output/agent-validation-matrix/20260611T084051Z/validation_matrix.html`

Selector signals:

- `agent_sdk`: plan references Agent SDK and
  `run_live_openai_agents_cleanup.py`.
- `cleanup_skill`: plan is scoped to cleanup report artifacts.
- `mcp_checker`: plan preserves `done` / checker success semantics.
- `launch_catalog`: plan references provider profiles and the agent harness.

### Required Implementation Gates

These gates prove the new metric extraction/comparison implementation itself:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_summarize_live_run.py \
  tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/molmo_cleanup/test_ci_live_reports.py

.venv/bin/ruff check \
  scripts/molmo_cleanup/summarize_live_run.py \
  scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py \
  scripts/molmo_cleanup/run_live_openai_agents_cleanup.py \
  scripts/molmo_cleanup/run_live_codex_cleanup.py \
  scripts/molmo_cleanup/run_live_claude_cleanup.py \
  tests/unit/molmo_cleanup/test_summarize_live_run.py \
  tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py \
  tests/unit/agents/test_live_runtime.py
```

### Agent-Validation Selected Deterministic Gates

The selector also requires route and cleanup contract checks because the plan
touches live-agent runner/report boundaries and explicitly preserves cleanup
success semantics:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/dev_tools/test_task_agent_just_recipes.py

./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_molmo_cleanup_policy.py \
  tests/unit/molmo_cleanup/test_molmo_cleanup_semantic_acceptability.py \
  tests/unit/molmo_cleanup/test_molmo_semantic_cleanup_loop.py
```

### Agent-Validation Selected Product And Live Gates

These gates are required before claiming affected route no-regression or any
live speed result. They are not required for the first deterministic
implementation claim when provider/Docker/local runtime approval is unavailable.

```bash
just run::surface \
  surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  intent=cleanup \
  agent_engine=direct-runner \
  evidence_lane=world-oracle-labels \
  seed=7 \
  output_dir=output/agent-validation-matrix/20260611T084051Z/gates/household-direct-world-oracle-product/run

just run::surface \
  surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  intent=cleanup \
  agent_engine=codex-cli \
  evidence_lane=world-oracle-labels \
  seed=7 \
  scenario_setup=relocate-cleanup-related-objects \
  relocation_count=5 \
  output_dir=output/agent-validation-matrix/20260611T084051Z/gates/codex-cleanup-world-oracle/run \
  provider_profile=codex-env

just run::surface \
  surface=household-world \
  world=molmospaces/val_0 \
  backend=mujoco \
  intent=cleanup \
  agent_engine=openai-agents-sdk \
  evidence_lane=world-oracle-labels \
  seed=7 \
  scenario_setup=relocate-cleanup-related-objects \
  relocation_count=5 \
  output_dir=output/agent-validation-matrix/20260611T084051Z/gates/openai-agents-sdk-cleanup/run \
  provider_profile=codex-env
```

Live-agent gates require explicit approval, Docker/runtime availability,
provider credentials, `just dev::network-status`, and budget acknowledgement.

### Agent-Validation Skipped As Irrelevant

The selector skipped these gates because the plan does not change RAW-FPV,
camera-grounded visual labeling, map-build, or runtime-map-prior behavior:

- `codex-cleanup-camera-raw-fpv`
- `direct-camera-grounded-sim-control`
- `direct-camera-grounded-grounding-dino`
- `direct-camera-raw-fpv`
- `direct-map-build-world-oracle`
- `direct-cleanup-runtime-prior-consumer`

## Saturation Result

One bounded reduce-entropy loop over report/live-agent performance surfaces
found nine material candidates above.

Parked as non-material for this plan:

- General `output/**` cleanup. The surface is untracked local evidence and
  only matters here through explicit manifests.
- Broad SDK performance arms A-AA. They are already tracked in
  `docs/plans/live-agent-runtime-sdk-perf-followups.md`; this plan should feed
  better measurement into that queue, not duplicate it.
- Rendering/camera visual comparison scripts. They have separate comparison
  manifests and are outside model-call performance normalization.

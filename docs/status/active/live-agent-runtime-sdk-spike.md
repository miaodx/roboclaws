# Live Agent Runtime SDK Spike Capsule

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`

Current slice: Agent SDK performance optimization, Group 0 matrix foundation,
Candidate A skill-context parity, Candidate G/J deterministic settings
attribution, Candidate I/AB deterministic prep, and Q/Y deterministic
recommendation enrichment, Candidate N deterministic repeated-map prep,
Candidate O deterministic camera-grounded composite prep, and Candidate P
deterministic raw-FPV repeated-failure rails, and Candidate AA deterministic
raw-FPV image-memory prep, and Candidate F deterministic robot-view capture
policy prep for the private `openai-agents-live` route.

Status: SDK runtime spike, first performance optimization pass, and Group 0
no-provider matrix foundation completed on 2026-06-10. Candidate A deterministic
skill-context proof and Candidate G/J deterministic settings/cache attribution
were accepted on 2026-06-11. Candidate I/AB deterministic prep and Q/Y
deterministic recommendation enrichment were accepted on 2026-06-12. Candidate
N deterministic repeated-map prep and Candidate O deterministic
camera-grounded composite prep were accepted on 2026-06-12. Candidate P
deterministic raw-FPV repeated-failure rails and Candidate AA deterministic
raw-FPV image-memory prep were accepted on 2026-06-12. Candidate F deterministic
robot-view capture policy prep was accepted on 2026-06-12. The first resumed
provider-backed pass on 2026-06-12 produced one `mify` Responses
`world-public-labels` baseline/candidate comparison and one blocked
`codex-env` GPT baseline attempt. The first Candidate O `mify` Responses
`camera-grounded-labels` pair completed but was diagnostic/inconclusive for O
because the composite shortcut was enabled but never called. Prompt/tool
selection has been repaired, and the promptfix2 retry now exercises the
shortcut and passes direct checker reruns after a narrow camera-grounded public
provenance checker repair. Treat it as an accepted O mechanism/diagnostic speed
row, not a normalized or publishable speed claim. Q/Y has now been refreshed
over the promptfix2 artifact with a camera-grounded breakdown that separates
composite-internal declaration substeps from standalone two-step declarations:
promptfix2 has 5 composite calls, 5 composite-internal declarations, and 11
standalone declarations. F now has an opt-in `action_timeline` prep arm, so the
F live A/B has now been tried. It reduced visual capture time but regressed
cleanup quality and wall/model time, so it is expected-rejected evidence rather
than a speed win. I/N/AB input-compaction live A/B has also now been tried. It
reduced model-facing input bytes and uncached tokens substantially, but failed
before `done` and got slower, so it is expected-rejected evidence rather than a
wall-clock win. D per-arm racing observability is now implemented as
single-arm/no-racing deterministic prep, so the next normalized-latency
priority can be a scoped C racing experiment if Q still shows model/SDK gap
dominant and live caps cover the racing multiplier. A behavior-preserving
compaction/session redesign, O paired repeats/tightening, and raw-FPV P/AA
remain valid alternate lower-priority arms. Token deltas are telemetry only;
cost is not a deciding objective for this plan. The full live provider/model x
evidence-lane performance matrix is still not done. The follow-up execution
plan is
`docs/plans/live-agent-runtime-sdk-perf-followups.md`.

Result:

- `live_timing.json` now contains `timeline.schema == "live_agent_timeline_v1"`.
- The timeline records semantic identifiers: `surface`, `intent`,
  `task_name`, `task_intent_mode`, `runtime`, `provider_profile`, `model`, and
  `evidence_lane`.
- The OpenAI Agents SDK route writes sanitized span artifacts:
  `openai-agents-spans.jsonl`.
- Span artifacts keep trace/span IDs, timing, span types, model/usage, MCP tool
  metadata, and errors. They do not persist raw prompts, model text, function
  inputs/outputs, credentials, or private evaluator truth.
- `LiveAgentResult` artifact discovery now includes OpenAI Agents span files.
- The lower private `just molmo::cleanup` direct route now synthesizes the
  default goal contract when no explicit contract path is supplied.
- Agent SDK performance profiles now persist resolved prompt mode,
  continuation mode, SDK turn cap, context budgets, raw-FPV budgets, and cache
  settings in `live_timing.json`.
- Agent SDK model-service fallback now retries classified transient
  model-service failures once by default at the SDK model request boundary,
  with CLI/env controls for retry budget and delay.
- `live_timing.json` and `timeline.latency_attribution` now include
  `model_service_fallback_metrics`, derived from sanitized fallback events
  rather than raw prompts or model/tool payloads.
- Compact continuation uses a public-safe state packet instead of replaying the
  full kickoff prompt when the profile requests it or context crosses the soft
  limit.
- Compact label-lane prompts reduce broad re-audit behavior while preserving
  MCP tool semantics and the `done`/`run_result.json` success gate.
- The raw-FPV budgeted profile now terminates with a classified budget reason
  before provider context-window failure; cleanup success remains out of scope
  for the first raw-FPV performance pass.
- The comparison workflow now accepts an explicit manifest and rejects smoke
  references as full-lane baselines.
- Group 0 unified speedup foundation tooling now exists as a no-provider
  preflight:
  `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py` plus
  `docs/status/active/agent-sdk-speedup-foundation-matrix.json`.
- The Group 0 manifest uses committed fake-provider fixtures under
  `tests/fixtures/agent_sdk_speedup_foundation/`, plans zero provider calls,
  records 5 supported rows and 2 unsupported Kimi/Claude-compatible rows, and
  produces a decision packet with privacy, quality, budget, and reducible-bucket
  gates.
- This Group 0 matrix is a foundation/preflight artifact only. It is not the
  full live provider/model x evidence-lane performance matrix and must not be
  used as a publishable speedup claim.
- Future OpenAI Agents SDK result summaries redact raw assistant output and SDK
  `last_agent` reprs from event/trace artifacts while keeping trace/session,
  usage, output length, and public agent-name metadata.
- Candidate A now gives the private SDK route bounded, auditable access to the
  canonical `molmo-realworld-cleanup` skill markdown. The SDK instructions
  receive the `SKILL.md` text, while persisted artifacts keep only
  `openai-agents-skill-context.json` metadata and `live_timing.json`
  `agent_sdk_skill_context` summary fields such as path, hash, byte counts,
  truncation state, and estimated tokens.
- Candidate G/J now makes SDK `ModelSettings` and `RunConfig` explicit for the
  private route, including trace privacy config, tool-call policy, truncation /
  usage settings by wire API, prompt-cache retention policy where applicable,
  and stable-prefix hash attribution in timing/cache summaries. This is
  deterministic attribution only, not a live speedup claim.
- Candidate I/AB deterministic prep now records the Responses-only continuation
  and session capability surface for each `wire_api`, keeps server-managed
  continuation disabled by default, and adds an opt-in
  `RunConfig.call_model_input_filter` compaction arm through
  `--model-input-compaction` / `ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION`.
  The compaction hook is model-facing only: oversized public tool outputs can be
  replaced with hash/size summaries before model calls while MCP traces,
  reports, and run artifacts remain complete. Events persist aggregate counts
  and byte deltas only, not raw prompts, model text, tool payload bodies,
  credentials, or private truth. `live_timing.json` and
  `timeline.latency_attribution` summarize the aggregate
  `model_input_filter_metrics`.
- Q/Y deterministic recommendation enrichment now extends the Group 0 decision
  packet with row-level latency buckets and aggregate candidate rankings.
  `reducible_bucket_report` separates model/SDK between-tool gap, visual
  capture, MCP/backend tool-handler time, residual/unattributed time,
  failed/noop counts, and dominant bucket. `summary.recommendation_summary`
  records candidate counts, candidate-group counts, dominant-bucket counts, top
  candidate ids/groups, and per-row recommendation evidence. The refreshed
  no-provider packet accepts 5 supported fixture rows, preserves 2 unsupported
  rows, and ranks Group 2 lane-specific reductions first after the already
  accepted Group 1 prep; this is diagnostic recommendation evidence, not a live
  speed claim.
- Candidate N deterministic prep now extends the opt-in SDK model-input
  compaction arm with repeated `metric_map` delta summarization. The first
  `metric_map` output remains full in model input; repeated later `metric_map`
  outputs can become hash/size/count summaries only when the replacement is
  smaller. MCP traces, reports, and run artifacts remain complete.
  `model_input_filter_metrics` and timeline attribution aggregate metric-map
  output counts, repeated-map counts, delta-compacted counts, and map byte
  deltas without storing map bodies in SDK events. This is deterministic
  model-facing prep, not a live speed claim.
- Candidate F deterministic prep now adds an SDK-private
  `robot_view_capture_policy=action_timeline` arm. The default remains `full`.
  The opt-in policy skips report-only `observe` / `scene_objects` robot-view
  captures while preserving before/after views, cleanup action views, raw-FPV
  observe artifact capture, traces, and reports. The OpenAI Agents live runner
  records the policy in `agent_sdk_perf_profile`, mirrors it in
  `live_timing.json`, and forwards `--robot-view-capture-policy` to the private
  cleanup server only when requested. This is deterministic prep only, not a
  live speed claim.
- Candidate P deterministic prep now adds a raw-FPV repeated visual-candidate
  failure rail to `raw_fpv_budgeted_v1`. Repeated compact
  `navigate_to_visual_candidate` failure fingerprints terminate as
  `raw_fpv_repeated_candidate_failure`, with aggregate terminal counts exposed
  in `agent_sdk_budget_terminal` and timeline latency attribution. The terminal
  detail stays compact and does not persist raw prompts, model text, image
  region payloads, full tool payload bodies, credentials, or private truth.
  This is raw-FPV stabilization prep, not a cleanup-pass or speed claim.
- Candidate AA deterministic prep now adds raw-FPV image memory inside the
  private SDK model-input filter. `raw_fpv_budgeted_v1` keeps the latest full
  raw-FPV frame model-visible and summarizes older image blocks only when the
  summary is smaller. Events and timing persist aggregate retained/evicted
  counts, byte deltas, hashes, and policy metadata only. MCP traces, report
  artifacts, and robot-view images remain complete; the raw-FPV MCP observe
  boundary still returns compact state plus a full PNG image block. This is
  model-facing prep, not a cleanup-pass or speed claim.
- The 2026-06-12 live pass satisfied the no-provider Group 0 dry-run/offline
  preflight and recorded live caps: 2 planned live rows for the successful
  `mify` pass, 45-minute wall-clock cap per row, context hard limit 128k,
  concurrency 1, racing multiplier 1, provider credentials present,
  MolmoSpaces/MuJoCo backend slot available, and `network: work` with
  repo-local `codex-env` / `mify` routes allowed.
- The GPT `codex-env` `world-public-labels` baseline attempt stopped before
  task work with classified transient provider 502
  (`provider_transient_failure`, `upstream_unavailable`) after model-service
  retry; no GPT speed or quality claim is made from that row.
- The `mify` Responses `world-public-labels` baseline and `mimo_compact_v1`
  candidate both finished. The diagnostic comparison is not a speed win:
  candidate quality was not worse, model/MCP calls each dropped by 2, but
  observed wall time was +5.746s, observed model API time was +8.749s, and
  uncached input tokens were +7033. Artifacts:
  `output/agent-sdk-perf-followups/mify-world-public-baseline/0612_0814/seed-7/`,
  `output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`,
  and
  `output/agent-sdk-perf-followups/mify-world-public-comparison-diagnostic.json`.
- Q/Y was refreshed from that completed live Responses pair without launching a
  new provider run. The refresh manifest is
  `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`, and the
  packet is `output/agent-sdk-perf-followups/live-refresh-decision.json`. It
  accepted the completed row as diagnostic recommendation evidence, kept
  model/SDK between-tool gap dominant (`205.026s`, 63.34%), recorded visual
  capture as material (`93.256s`, 28.81%), and pointed the next live arm toward
  Group 2 lane-specific work after already-accepted Group 1 prep.
- Q/Y was refreshed again with the O promptfix2 artifact. The packet now
  includes `camera_grounded_tool_breakdown` so composite-internal
  `declare_visual_candidates` requests do not create a false O recommendation.
  The promptfix2 row still recommends O because it has 11 standalone
  declarations beyond 5 composite-internal declarations. It also keeps
  model/SDK between-tool gap dominant (`663.611s`, 77.68%) and visual capture
  material (`156.962s`, 18.37%).
- The Candidate F action-timeline live row completed at
  `output/agent-sdk-perf-followups/mify-world-public-mimo-compact-action-timeline/0612_1303/seed-7/`.
  The mechanism worked locally by reducing `robot_view_capture_s` from
  `93.256s` to `54.975s`, but the shared comparison rejects it as a speed win:
  quality regressed from `4/5` restored to `3/5`, completion changed from
  `success` to `partial_success`, observed wall time increased by `+181.786s`,
  and observed model API time increased by `+216.535s`. Q/Y records this as an
  expected-rejected evidence row in
  `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`; it is not a
  reason to rerun F as the next standalone arm.
- The Candidate I/N input-compaction live row completed at
  `output/agent-sdk-perf-followups/mify-world-public-mimo-compact-input-compaction/0612_1327/seed-7/`.
  The mechanism worked locally: `model_input_filter_metrics` reports
  `input_byte_reduction_ratio=0.939364`, `input_bytes_before=71186480`,
  `input_bytes_after=4316462`, `metric_map_output_count=292`, and
  `repeated_metric_map_output_count=208`; uncached input tokens dropped from
  `197838` to `63045`. The row is still rejected because it failed before
  `done` after two SDK invocations, produced no `run_result.json`, raised
  failed/noop calls to `31`, increased observed wall time by `+62.627s`, and
  increased observed model API time by `+102.956s`. It proves compaction
  mechanics, not a wall-clock win.
- Candidate D deterministic racing-observability prep is implemented. The
  private SDK model request boundary now emits sanitized single-arm
  `model_racing_arm_start` / finish / failure events with stable call/arm ids,
  elapsed time, winner/cancel flags, provider/model/wire axes, failure class,
  token usage availability, and loser-billing-unknown fields. `live_timing.json`
  aggregates these under `model_racing_observability_metrics` in timeline
  latency attribution. Current mode is `racing_enabled=false`,
  `racing_multiplier=1.0`; no C racing run or speed claim is made yet.
- Completed external camera-grounded Chat-compatible evidence at
  `output/experiments/mimo-pro-text-lanes/agent-sdk-camera-grounded-dino/0612_0950/seed-7/`
  shows `mimo-openai-chat` / `mimo-v2.5-pro` finished with 14
  `declare_visual_candidates` calls and a large between-tool/visual bucket. Use
  it as compatibility/diagnostic support for Candidate O, not as a Responses
  speed claim.
- The `mify` Responses Candidate O baseline/composite pair completed:
  `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-baseline/0612_1012/seed-7/`
  and
  `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite/0612_1032/seed-7/`.
  Metrics are
  `output/agent-sdk-perf-followups/mify-camera-grounded-baseline-metrics.json`,
  `output/agent-sdk-perf-followups/mify-camera-grounded-composite-metrics.json`,
  and
  `output/agent-sdk-perf-followups/mify-camera-grounded-composite-comparison.json`.
  The comparison helper marks same-or-better quality and faster wall time
  (`-37.851s`), but the candidate trace still has 19 `observe` requests and 19
  `declare_visual_candidates` requests with zero
  `observe_camera_grounded_candidates` requests. Treat the row as diagnostic
  runtime/provider evidence, not a valid Candidate O speed win.
- Candidate O prompt/tool selection is repaired: the compact private
  `camera-grounded-labels` prompt now uses
  `observe_camera_grounded_candidates` when
  `camera_grounded_composite_tools.enabled=true`, while the default
  camera-grounded prompt still uses the public two-step path.
- The Candidate O promptfix2 retry completed at
  `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-promptfix2/0612_1126/seed-7/`.
  The live runner wrote `run_result.json`, `report.html`, and timing artifacts,
  then exited nonzero only because the checker had a stale public provenance
  allowlist. The checker now allows `camera-grounded-labels` as public
  producer/model provenance only inside the camera-model-policy observed-object
  branch, preserving private-field and support-estimate checks. Direct checker
  reruns pass for both composite artifacts. The promptfix2 trace includes
  5 `observe_camera_grounded_candidates` requests, 16
  `declare_visual_candidates` requests, and 19 underlying `observe` substep
  requests. Shared comparison against the `0612_1012` baseline is accepted
  diagnostically with same quality (`completion_status=success`,
  `restored_count=4/5`, `semantic_accepted_count=5/5`,
  `sweep_coverage_rate=1.0`, `disturbance_count=0`), `-303.142s` observed
  wall, `-319.020s` observed model API time, and `+50586` uncached input
  tokens.
- The shared report-performance quality comparator now caps sweep
  over-coverage at 1.0 for same-or-better comparison, so extra baseline
  inspection waypoints do not create a false regression when the candidate
  still reaches full required coverage. This does not waive cleanup quality,
  disturbance, failed/noop, or semantic acceptance checks.
- `openai-agents-live` remains private/non-default.
- `done`/`run_result.json` remains the only cleanup success signal.

Live evidence:

- Performance comparison manifest:
  `docs/status/active/agent-sdk-perf-opt-0610-comparison-manifest.json`
- GPT `world-public-labels` compact profile passed:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/gpt-world-public/0610_0847/seed-7/`
- GPT `camera-grounded-labels` compact profile passed:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/gpt-camera-grounded/0610_0856/seed-7/`
- MiMo `world-public-labels` compact profile passed:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/mimo-world-public-rerun/0610_0910/seed-7/`
- MiMo `camera-grounded-labels` compact profile passed, but the speedup was
  small and is recorded as a provider/model profile limitation:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/mimo-camera-grounded/0610_0917/seed-7/`
- Raw-FPV budgeted profile terminated with classified reason
  `raw_fpv_sdk_turn_budget_exhausted` inside context budget:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/gpt-raw-fpv-budgeted-turncap/0610_0949/seed-7/`
- `world-public-labels` passed:
  `output/household/household-cleanup/openai-agents-observability-v1-world-public/0609_2119/seed-7/`
- `camera-grounded-labels` passed:
  `output/household/household-cleanup/openai-agents-observability-v1-camera-grounded/0609_2140/seed-7/`
- `camera-raw-fpv` produced the V1 timeline and sanitized spans, but failed
  before checker success:
  `output/household/household-cleanup/openai-agents-observability-v1-raw-fpv/0609_2202/seed-7/`

Raw-FPV failure classification:

- The 2026-06-09 Observability V1 raw-FPV run stopped after one continuation
  attempt with a provider-wrapped context-window failure.
- The 2026-06-10 performance pass first reproduced that the previous 128-turn
  raw-FPV profile could cross its hard context budget inside one SDK attempt.
  The final raw-FPV retry used a lower SDK turn cap and terminated with
  `raw_fpv_sdk_turn_budget_exhausted`, `max_input_tokens=67040` under the 96k
  hard limit, and `context_window_failure_detected=false`.
- The SDK exception classifier has regression coverage for provider-wrapped
  context failures and SDK max-turn budget exhaustion.
- Model-service fallback has regression coverage for model-unavailable/5xx/
  transport retryability, auth/config/context/tool non-retryability, successful
  one-retry recovery, retry-budget exhaustion, and timing/timeline artifact
  summaries.
- Group 0 matrix preflight has regression coverage for dry-run budgets,
  unsupported rows, forbidden artifact keys/secret markers, faster-but-worse
  quality rejection, accepted same-or-better rows, expected-terminal raw-FPV
  diagnostic evidence, model-input-filter event privacy scanning, reducible
  latency buckets, dominant-bucket classification, aggregate recommendation
  summaries, and reducible-bucket recommendations.
- Candidate N has regression coverage for repeated `metric_map` model-input
  delta summaries, no-growth compaction behavior through the smaller-than-
  original guard, profile attribution, aggregate metric-map byte counters, and
  timeline attribution projection.

Verification:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/reports/test_molmo_cleanup_report.py tests/unit/molmo_cleanup/test_summarize_live_run.py -q`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py roboclaws/agents/prompts/household_cleanup.py scripts/molmo_cleanup/summarize_live_run.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_summarize_live_run.py`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --dry-run`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --offline-preflight --decision-packet output/agent-sdk-speedup-foundation/decision.json`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `.venv/bin/ruff format --check scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --offline-preflight --decision-packet output/agent-sdk-speedup-foundation/decision.json`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --dry-run`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `.venv/bin/ruff format --check scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --offline-preflight --decision-packet output/agent-sdk-speedup-foundation/decision.json`
- `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --dry-run`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `.venv/bin/ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`

No-touch scope preserved:

- Do not promote `openai-agents-live` to a public/default route.
- Do not change MCP cleanup success semantics.
- Do not replace or remove existing `codex-live` / `claude-live` behavior.
- Do not write credentials, raw full prompts, or private evaluator truth to
  observability artifacts.
- Do not persist the SDK skill-context body in events, timing, status, or trace
  artifacts; only metadata/hash/size summaries are allowed.
- Do not claim a settings/cache speedup from Candidate G/J until provider-backed
  baseline and candidate rows exist under the live approval gate.
- Do not claim model-input compaction or Responses continuation/session speedup
  from Candidate I/AB deterministic prep until provider-backed baseline and
  candidate rows exist under the live approval gate.

Parked work:

- Post-optimization perf follow-up batch captured in
  `docs/plans/live-agent-runtime-sdk-perf-followups.md`:
  - Candidate A skill parity is accepted; keep its metadata/privacy guard and
    optionally run live A/B only after recorded budget/backend/network gates
    pass.
  - Candidate G/J deterministic settings/cache attribution is accepted; live
    A/B speed proof remains gated on credentials/backend availability,
    network policy, and recorded run caps.
  - Candidate I/AB deterministic prep is accepted; live model-input compaction,
    server-managed continuation, and session-state A/B proof remains gated on
    credentials/backend availability, network policy, and recorded run caps.
    The first `mify` `world-public-labels` baseline versus `mimo_compact_v1`
    row is diagnostic only, not a speed win.
  - Q/Y deterministic recommendation enrichment is accepted for Group 0; the
    current no-provider packet pointed to Group 2 N/O after already-accepted
    Group 1 prep. Q/Y has now been refreshed with the completed `mify`
    world-public live packet; refresh it again with the Candidate O promptfix2
    mechanism row before selecting the next arm.
  - Candidate N deterministic repeated-map prep is accepted inside the opt-in
    model-input compaction arm.
  - Candidate O deterministic prep is accepted as an SDK-private opt-in
    `observe_camera_grounded_candidates` MCP shortcut for
    `camera-grounded-labels`; default public MCP/profile tools remain
    unchanged. The promptfix2 `mify` Responses row actually calls the shortcut
    and is an accepted mechanism/diagnostic speed row, but normalized or
    publishable speed claims still require calibrated/repeated evidence.
  - Candidate P deterministic prep is accepted as a raw-FPV repeated
    visual-candidate failure rail; cleanup-pass and live speed claims remain
    gated.
  - Candidate AA deterministic prep is accepted as raw-FPV SDK model-facing
    image memory; live cleanup-pass and speed claims remain gated, while
    multiresolution thumbnail/crop policy stays parked until live evidence says
    retained full-frame policy is insufficient.
  - Full provider/model x evidence-lane matrix before broad speed claims. The
    GPT `codex-env` baseline needs retry only after the transient 502 gate
    clears.
  - Optional per-model-call racing inside the SDK model interface, only with
    per-arm cache/cost telemetry and explicit live-run approval.
  - Agent-visible state delta/compaction and selective visual artifact capture
    as later speed levers.
  - Additional SDK-native reduce-entropy candidates captured after the first
    batch: explicit `ModelSettings`/`RunConfig` performance profiles,
    Responses/session continuation, `call_model_input_filter` compaction,
    prompt-cache stable-prefix evidence, parallel-tool-call policy audit, and
    non-tool response turn-waste classification.
  - Trace-backed second-pass candidates: evidence-lane tool-surface pruning and
    a trace-derived irreducible-floor/waste classifier. Repeated `metric_map`
    delta prep, the camera-grounded observe/label two-step collapse, raw-FPV
    visual-candidate failure rails, and raw-FPV image memory have deterministic
    prep accepted.
  - Big-flow infrastructure follow-ups after the Group 0 foundation: richer
    feature-flag attribution in live timing, variance/repeatability policy for
    publishable claims, cross-client regression guard, and multiresolution
    raw-FPV thumbnail/crop policy if live evidence shows it is needed.
  - Default MCP composite/merge tools remain out of scope; Candidate O is
    SDK-private and opt-in only.
- Anthropic Claude Agent SDK spike.
- Pi SDK MCP adapter prototype.
- Public/default route promotion for `openai-agents-live`.
- Raw-FPV cleanup strategy improvement, if maintainers want that lane to pass
  cleanup gates rather than only produce classified budget evidence.

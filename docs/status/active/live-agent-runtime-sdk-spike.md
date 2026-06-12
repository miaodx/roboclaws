# Live Agent Runtime SDK Spike Capsule

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`

Current slice: Agent SDK performance optimization, Group 0 matrix foundation,
Candidate A skill-context parity, Candidate G/J deterministic settings
attribution, Candidate I/AB deterministic prep, and Q/Y deterministic
recommendation enrichment, Candidate N deterministic repeated-map prep,
Candidate O deterministic camera-grounded composite prep, and Candidate P
deterministic raw-FPV repeated-failure rails, and Candidate AA deterministic
raw-FPV image-memory prep for the private `openai-agents-live` route.

Status: SDK runtime spike, first performance optimization pass, and Group 0
no-provider matrix foundation completed on 2026-06-10. Candidate A deterministic
skill-context proof and Candidate G/J deterministic settings/cache attribution
were accepted on 2026-06-11. Candidate I/AB deterministic prep and Q/Y
deterministic recommendation enrichment were accepted on 2026-06-12. Candidate
N deterministic repeated-map prep and Candidate O deterministic
camera-grounded composite prep were accepted on 2026-06-12. Candidate P
deterministic raw-FPV repeated-failure rails and Candidate AA deterministic
raw-FPV image-memory prep were accepted on 2026-06-12. The first resumed
provider-backed pass on 2026-06-12 produced one `mify` Responses
`world-public-labels` baseline/candidate comparison and one blocked
`codex-env` GPT baseline attempt; the full live provider/model x evidence-lane
performance matrix is still not done. The follow-up execution plan is
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
- Completed external camera-grounded Chat-compatible evidence at
  `output/experiments/mimo-pro-text-lanes/agent-sdk-camera-grounded-dino/0612_0950/seed-7/`
  shows `mimo-openai-chat` / `mimo-v2.5-pro` finished with 14
  `declare_visual_candidates` calls and a large between-tool/visual bucket. Use
  it as compatibility/diagnostic support for Candidate O, not as a Responses
  speed claim.
- A separate user-owned `camera-grounded-labels` sim-labels run currently owns
  the MolmoSpaces/MuJoCo visual backend slot on port `18788`:
  `output/experiments/mimo-pro-text-lanes/agent-sdk-camera-grounded-sim-labels/0612_0958/seed-7/`.
  Do not terminate it or launch another live visual row until that slot is
  free.
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
    world-public live packet; it points to Group 2 lane-specific reductions,
    with Candidate O camera-grounded A/B as the next preferred live arm once
    the current visual backend slot is free.
  - Candidate N deterministic repeated-map prep is accepted inside the opt-in
    model-input compaction arm.
  - Candidate O deterministic prep is accepted as an SDK-private opt-in
    `observe_camera_grounded_candidates` MCP shortcut for
    `camera-grounded-labels`; default public MCP/profile tools remain
    unchanged, while raw-FPV lane work remains lane-specific and live speed
    claims remain gated. Camera-grounded live A/B remains a likely next arm
    after Q/Y refresh.
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

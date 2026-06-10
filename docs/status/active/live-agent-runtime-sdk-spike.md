# Live Agent Runtime SDK Spike Capsule

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`

Current slice: Agent SDK performance optimization for the private
`openai-agents-live` route.

Status: completed on 2026-06-10.

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

Verification:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/reports/test_molmo_cleanup_report.py`
- `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/reports/test_molmo_cleanup_report.py tests/unit/molmo_cleanup/test_summarize_live_run.py -q`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py roboclaws/agents/prompts/household_cleanup.py scripts/molmo_cleanup/summarize_live_run.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_summarize_live_run.py`

No-touch scope preserved:

- Do not promote `openai-agents-live` to a public/default route.
- Do not change MCP cleanup success semantics.
- Do not replace or remove existing `codex-live` / `claude-live` behavior.
- Do not write credentials, raw full prompts, or private evaluator truth to
  observability artifacts.

Parked work:

- Post-optimization reduce-entropy batch captured in
  `docs/plans/live-agent-runtime-sdk-spike.md`:
  - OpenAI Agents SDK skill parity: the current plain SDK route names
    `molmo-realworld-cleanup` but does not automatically mount/read the
    `SKILL.md` the way Codex/Claude live workspaces do.
  - Full provider/model x evidence-lane matrix before new speed claims.
  - Optional per-model-call racing inside the SDK model interface, only with
    per-arm cache/cost telemetry and explicit live-run approval.
  - Agent-visible state delta/compaction and selective visual artifact capture
    as later speed levers.
  - Additional SDK-native reduce-entropy candidates captured after the first
    batch: explicit `ModelSettings`/`RunConfig` performance profiles,
    Responses/session continuation, `call_model_input_filter` compaction,
    prompt-cache stable-prefix evidence, parallel-tool-call policy audit, and
    non-tool response turn-waste classification.
  - Trace-backed second-pass candidates: evidence-lane tool-surface pruning,
    repeated `metric_map` delta contract, camera-grounded observe/label
    two-step collapse, raw-FPV visual-candidate failure rails, and a
    trace-derived irreducible-floor/waste classifier.
  - Big-flow infrastructure candidates: unified experiment matrix runner,
    feature-flag attribution, offline replay/fake-provider preflight,
    artifact privacy/schema gate, live cost/time/concurrency budget gate,
    variance/repeatability gate, cross-client regression guard, decision
    dashboard, behavior-quality regression comparator, and raw-FPV image-memory
    policy.
  - Default MCP composite/merge tools remain out of scope.
- Anthropic Claude Agent SDK spike.
- Pi SDK MCP adapter prototype.
- Public/default route promotion for `openai-agents-live`.
- Raw-FPV cleanup strategy improvement, if maintainers want that lane to pass
  cleanup gates rather than only produce classified budget evidence.

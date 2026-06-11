---
plan_scope: live-agent-runtime-sdk-perf-followups
status: CONTINUE
source:
  - docs/plans/live-agent-runtime-sdk-spike.md
  - 2026-06-10 Agent SDK performance optimization pass
  - 2026-06-10 Group 0 speedup foundation preflight
last_reviewed: 2026-06-11
---

# Live Agent Runtime SDK Perf Follow-ups

## Status

CONTINUE.

This is the execution gate for the unfinished `openai-agents-live` performance
work. The completed SDK runtime spike remains in
`docs/plans/live-agent-runtime-sdk-spike.md`.

This plan is a re-planned candidate queue, not a promise to run every item. Run
one candidate or group, summarize evidence, update the queue, then continue.

2026-06-11 review after timing-analysis updates: the plan now treats
`roboclaws.reports.live_performance` as the canonical speed/quality packet,
records provider HTTP timing as transport-only evidence, and keeps `wire_api`
as a matrix axis so Responses and Chat-compatible SDK rows are not conflated.

## Completed Prerequisites

- The private `openai-agents-live` route can run cleanup through MCP, `done`,
  checker, and report generation.
- Observability V1, sanitized SDK span artifacts, performance profiles, context
  budgets, compact continuation, compact label-lane prompts, raw-FPV budget
  classification, and model-service fallback are implemented.
- Group 0 no-provider foundation exists through
  `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py` and
  `docs/status/active/agent-sdk-speedup-foundation-matrix.json`.
- Shared report-performance analysis now exists through
  `roboclaws.reports.live_performance`,
  `scripts/reports/extract_live_report_metrics.py`, and
  `scripts/reports/compare_live_report_metrics.py`. Speed and quality
  comparisons should reuse `roboclaws_report_performance_metrics_v1`, not a
  separate SDK-only metric contract.
- Provider timing proxy artifacts now exist for benchmark-style Codex/Claude
  routes through `provider_request_metrics.jsonl`. Treat those rows as observed
  HTTP transport timing with explicit limitations, not provider-internal model
  compute time. Do not use Codex/Claude proxy rows as direct evidence for an
  OpenAI Agents SDK speed claim unless the candidate run itself records
  comparable SDK route metrics.

## Not Done

- Full live GPT/MiMo x evidence-lane matrix.
- Follow-up optimization groups 1-5.
- Explicit Responses-native feature evaluation: server-managed continuation,
  conversation/session state, prompt-cache retention, and other SDK features
  that only apply when the provider really supports the Responses API.
- OpenAI Agents SDK provider-backed matrix rows for Chat-compatible profiles
  such as `mimo-openai-chat` and `kimi-openai-chat`, if those route changes land
  and credentials are available. These rows prove compatibility unless their own
  metrics support a speed claim.
- Publishable speedup claim across all relevant lanes and providers.

## Hard Constraints

- `openai-agents-live` stays private/non-default unless separately promoted.
- `done` / `run_result.json` remains the cleanup success signal.
- Default MCP/profile behavior must not change without cross-client proof.
- No provider-backed live matrix run without explicit live-run approval,
  credential/backend availability, `just dev::network-status`, and budget
  acknowledgement.
- No artifact may persist raw prompts, model text, full tool payload bodies,
  credentials, private evaluator truth, or full compact continuation packets.
- Faster-but-worse behavior is rejected unless a decision packet explicitly
  names and accepts the tradeoff.
- Performance packets and decision rows must use the shared report-performance
  contract where available. Missing usage, duration, image, provider timing, or
  calibration telemetry is `unavailable`, never zero.
- Provider HTTP timing from `provider_request_metrics.jsonl` is transport
  evidence. Do not relabel it as model compute time or use it as a normalized
  speed claim without a separate calibration decision.
- `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py` remains the Group 0
  preflight and decision-packet gate. Baseline/candidate speed claims should be
  judged from shared report-performance packets or comparisons, not from the
  foundation dry-run packet alone.

## Matrix Scope

First live matrix scope:

- Provider/model profiles: GPT through `codex-env`, MiMo through `mify`.
- Evidence lanes: `world-public-labels`, `camera-grounded-labels`,
  `camera-raw-fpv`.
- Responses rows: `codex-env` and `mify`.
- Chat-compatible rows: `mimo-openai-chat` and `kimi-openai-chat` only after the
  route, dependency, and credential gates pass.
- Claude SDK rows stay `unsupported` or `blocked` until a Claude SDK
  route/provider exists. Do not turn this perf pass into provider-integration
  work.

Raw-FPV remains diagnostic by default. It may pass as classified bounded
evidence without cleanup success unless a later lane-specific pass explicitly
changes the gate.

### Wire/API Surface Scope

Treat the provider wire format as a first-class experiment axis:

- `responses`: preferred performance/capability path for `codex-env` and any
  truly Responses-compatible profile. This path may use Responses-only levers
  such as `previous_response_id`, conversation/session state, server-managed
  continuation, prompt-cache retention/stable prefixes, and SDK features whose
  implementation depends on `OpenAIResponsesModel`.
- `chat-completions`: compatibility path for OpenAI-compatible providers that
  expose Chat Completions but not Responses. This path can still use ordinary
  tool calls through the Agents SDK's `OpenAIChatCompletionsModel`, but it must
  not be credited with Responses-only speedups unless equivalent evidence is
  recorded from that provider.

Do not collapse these into one "OpenAI-compatible" bucket in matrix rows,
decision packets, or performance claims. A faster/better Responses run proves a
Responses-route result; a successful Chat route proves provider coverage and
tool-call compatibility unless its own metrics show a comparable speed effect.

## Current Default Queue

Use this queue unless fresh evidence changes it:

1. Re-run Group 0 dry-run/offline preflight only as a gate check.
2. Generate or refresh shared report-performance packets for the relevant
   baseline/candidate rows before changing speed levers.
3. Do A as deterministic skill-context proof.
4. Do G, with J folded into the same settings/cache evidence.
5. Do AB for Responses-only levers when the row uses `wire_api=responses`.
6. Do I, with Q/L measurement folded into the same analysis.
7. Run scoped B live baseline refresh before any strong speed claim, if live
   approval and budget are available.
8. Use Q/Z/Y output to choose O/N or P/AA next.
9. Defer C/D/K/E/F/M/W/X unless the dependency evidence below appears.

Do not spend more time on standalone Group 0 unless a new candidate changes the
manifest, artifact schema, budget gate, privacy gate, comparator, or decision
packet.

## Candidate Queue

Decision values:

- `gate`: required guardrail, not a speed arm.
- `keep`: worth trying or maintaining.
- `merge`: fold into another candidate instead of running standalone.
- `defer`: do not run until named evidence or dependency exists.
- `bypass-for-now`: skip in the next pass because current evidence does not
  justify the cost/risk.

### Group 0: Foundation And Gates

Group goal: make later speed claims comparable, bounded, private-safe, and
decision-ready. Expected direct speedup is none.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| R | gate, mostly done | Maintain the unified experiment matrix runner. | One manifest should replace shell-history experiments. | Dry-run lists rows, flags, dependencies, unsupported rows, budgets, and stop conditions with no provider calls. | Extend only for new live rows or candidate arms. |
| S | gate | Record feature flags and candidate dependencies. | Hidden switches make speed wins unexplainable. | Every row records `experiment_id`, `candidate_ids`, flags, dependencies, and profile id. | Reject comparisons with untracked flag differences. |
| T | gate, mostly done | Run offline replay/fake-provider preflight. | Paid live runs should not discover schema failures. | Every live candidate has a no-provider preflight result. | Stop before live when replay, fake-provider, or schema checks fail. |
| U | gate, mostly done | Run artifact privacy/schema gates. | More telemetry must not leak prompts, model text, tool bodies, secrets, or private truth. | Forbidden keys/content fail; allowed aggregate fields pass. | Block publication and live continuation on privacy failure. |
| V | gate | Gate live cost, time, concurrency, context, and racing multiplier. | Matrices and racing can burn budget and backend time. | Dry-run prints max runs, wall-clock, turn/context caps, concurrency, and multiplier. | Refuse live execution without acknowledged caps. |
| W | defer | Add repeatability policy for publishable claims. | One live run can be lucky. | Winner rows can be repeated or paired; single-run rows are labeled diagnostic. | Do not require repeats for first diagnostic pass; repeat only winners. |
| Y | gate, mostly done | Generate decision packet/dashboard from shared performance packets. | Reviewers need one closeout artifact, but the metrics source should be canonical. | Packet records accepted/rejected/inconclusive/blocked/bypassed/superseded/added rows and links to `roboclaws_report_performance_metrics_v1` packets. | Missing decision data means inconclusive, not accepted. |
| B | keep | Refresh live provider/model x evidence-lane baseline matrix with `wire_api` as an axis. | GPT/MiMo, Responses/Chat routes, and evidence lanes differ materially; anecdotes are insufficient. | Responses rows cover `codex-env`/`mify`; Chat-compatible rows cover `mimo-openai-chat`/`kimi-openai-chat` only when supported; unsupported rows are labeled. | Live rows require approval/budget/backend; do not expand into Claude SDK integration. |
| Z | gate, mostly done | Use shared report-performance comparison for quality and timing guardrails. | Faster can still mean worse cleanup. | Rows include shared quality fields plus wall, model/API, provider HTTP, context, call-count, and residual timing fields where available. | Reject faster-but-worse unless explicitly waived; missing telemetry is unavailable, not zero. |
| Q | keep | Classify irreducible floor and remaining waste from shared performance packets. | Next work should target the largest reducible bucket. | Summary separates model/API timing, provider HTTP transport, MCP/backend, visual capture, between-tool gaps, context growth, and turn/tool waste. | Stop or bypass next arms when remaining gain is smaller than cost/risk. |

### Group 1: Private SDK Levers

Group goal: attack context growth, SDK defaults, skill drift, and wasted turns
without changing default MCP/profile behavior.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| A | keep, quality-first | Give the SDK route bounded, auditable access to canonical `molmo-realworld-cleanup` skill context. | Current SDK route names the skill but does not mount/read `SKILL.md` like Codex/Claude workspaces. | Artifacts show exact skill context received; deterministic proof passes without private leaks. | Live A/B only if context remains bounded; stop if skill packaging changes runtime topology without approval. |
| G | keep | Expose explicit SDK `ModelSettings` / `RunConfig` performance profiles. | Current runtime relies too much on provider defaults while turns/context remain high. | Timing records exact settings; A/B lowers turns, latency, output, or context with same-or-better quality. | Stop on checker regression, unsupported SDK option behavior, missing attribution, or context failure. |
| J | merge into G/Q/AB | Record prompt-cache retention and stable-prefix evidence. | Cache behavior can explain or hide speed wins, and some cache levers are Responses-specific. | G/Q/AB output shows stable-prefix/cache settings and cached vs uncached input when available. | Do not claim cache speedup when usage is unavailable, provider is Chat-only, or prefix changes are untracked. |
| H | bypass-for-now | Use SDK-native session/Responses continuation instead of prompt replay. | Prompt replay can grow context, but compact continuation already fixed the immediate replay issue. | Only reconsider if Q shows continuation replay remains a top context source. | Do not run as next pass; stop if continuation changes task state or hides failure state. |
| I | keep | Add SDK `call_model_input_filter` or equivalent state compaction. | Repeated public tool state is a likely context driver after kickoff compaction. | Replay/fake-provider proof shows repeated payload bytes drop while reports and traces remain complete. | Stop on missing public state, private truth leak, report evidence loss, or checker regression. |
| L | merge into Q/Y | Audit non-tool responses and turn-count waste. | 72-78 model turns suggests avoidable text-only or deferred-action turns. | Q/Y records non-tool, deferred, noop, and turn-waste counts. | Create a separate fix arm only if waste is material. |
| AB | keep, Responses-only | Add a Responses-native feature audit and A/B arm before broad protocol fallback work. | The SDK route now has both Responses and Chat-compatible directions; speed claims must not mix them. | Decision packet records `wire_api=responses`, enabled Responses-only levers, and shared performance deltas for server-managed continuation/session state, prompt-cache retention/stable prefixes, or related SDK settings. | Stop if provider is Chat-only, SDK state hides MCP-visible task state, artifacts lose trace/report completeness, or privacy gates require raw prompt/tool payload persistence. Chat support is compatibility work unless its own metrics prove speed. |

### Group 2: Lane-Specific Reductions

Group goal: reduce lane-local overhead only after Group 1 and Q identify the
remaining waste. Keep changes SDK-private or opt-in until X passes.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| O | keep | Collapse deterministic `camera-grounded-labels` observe/label two-step work. | This lane may spend time on deterministic plumbing that can be represented more directly. | Camera-grounded A/B lowers turns or elapsed time with unchanged checker success and trace reviewability. | Stop if evidence semantics blur into raw-FPV or grounding detail is lost. |
| M | defer | Prune irrelevant tools by evidence lane. | Smaller tool surfaces can reduce choice noise, but broad pruning can break valid actions. | Lane-local allowlist keeps all legitimate cleanup actions available. | Try only if Q shows tool-choice noise after G/I/O; keep SDK-private or opt-in. |
| N | keep, conditional | Add repeated `metric_map` delta contract. | Re-sending static map state can inflate context. | Agent sees enough current map state with fewer repeated bytes; full map remains in artifacts. | Try only if Q/I show repeated map bytes remain material. |
| F | defer | Reduce or reuse report-only visual capture. | Visual capture can be a real wall-clock bucket independent of model speed. | A/B lowers `robot_view_capture_s` while report reviewability and checker results remain intact. | Bypass unless Q shows visual capture is a top remaining cost. |

### Group 3: Raw-FPV Stabilization

Group goal: make raw-FPV bounded and informative before raising budgets,
racing, or attempting cleanup-pass claims.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| P | keep for raw-FPV | Add raw-FPV visual-candidate failure rails. | Raw-FPV repeats unresolved visual searches and needs actionable terminal reasons. | Runs classify unresolved candidates, retries, and terminal state inside context budget. | Stop on repeated unresolved loops without new evidence, unclassified provider failure, or context breach. |
| AA | keep for raw-FPV | Add raw-FPV image-memory and multiresolution policy. | Replaying stale full-frame images consumes context without improving cleanup. | Artifacts record retained/evicted images, thumbnail/crop/full-frame policy, and report visual proof. | Stop if raw-FPV is relabeled as camera-grounded evidence or visual proof disappears. |

### Group 4: Expensive Orchestration

Group goal: use racing or parallelism only when fresh evidence proves the
latency target is worth the extra cost and risk.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| D | merge into C prerequisite | Add per-arm racing cache/cost observability. | Racing can look faster while hiding loser-arm billable work. | Timing records arm start/finish/cancel, winner, usage availability, token/cache fields, and unknown loser billing. | Do D only immediately before/with C. |
| C | defer | Race individual SDK model calls. | The bottleneck may be per-call provider tail latency, not whole-run orchestration. | First schema-valid/MCP-legal response wins; only winner enters history; losers are cancelled/recorded. | Do not run until D exists, Q proves tail latency dominates, budget is approved, and label lanes are scoped. |
| K | bypass-for-now | Audit parallel tool-call policy. | Robot actions are stateful and serial; parallelism is risky. | Policy distinguishes safe read-only tools from stateful actions. | Revisit only for read-only tools if G exposes provider parallelism benefit. |
| E | bypass-for-now | Consider broad agent-visible state delta/compaction. | E is an umbrella for I/N/AA and risks public contract drift. | SDK-private or opt-in deltas reduce repeated state while preserving complete trace/report evidence. | Use I, N, and AA first; revive E only if concrete arms are insufficient. |

### Group 5: Promotion And Compatibility

Group goal: decide whether private or opt-in MCP/profile-affecting speedups can
be promoted to defaults.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| X | gate, conditional | Run cross-client regression guard before promotion. | Private SDK speedups must not silently break direct, Codex, Claude, or OpenClaw clients. | Default routes pass relevant contract/smoke tests; docs label private, opt-in, or safe-default boundary. | Required before promoting M/N/O/P/E beyond SDK-private or opt-in behavior. |

## Adaptive Planning Loop

After each candidate arm or completed group:

1. Summarize fresh evidence from `live_timing.json`, spans, traces, checker
   output, report artifacts, and the decision packet.
2. Re-run a small intuitive planning loop:
   - What changed in the bottleneck picture?
   - Which remaining candidate is now highest leverage?
   - Which candidates are unnecessary, duplicated, too risky, or blocked?
   - Did the run reveal a new candidate that is more precise than A-AA?
3. Update the candidate queue before continuing.
4. Record every queue decision in the acceptance packet.

Allowed queue decisions:

- `accepted`: keep the change or result.
- `rejected`: tried and failed success criteria.
- `inconclusive`: evidence was insufficient; do not claim a speedup.
- `blocked`: needs approval, credentials, backend slot, provider access, or a
  design decision.
- `bypassed`: newer evidence shows low value, duplication, excessive risk, or a
  better replacement.
- `superseded`: replaced by a more precise candidate.
- `added`: new candidate discovered from fresh evidence.

Bypass is a first-class outcome, not a failure.

Append new candidates only when grounded in observed evidence. Add an ID after
`AA` (`AB`, `AC`, ...), group placement, Queue/Do/Why/Success/Stop fields,
blast radius, and proof plan. Do not run a new live candidate until it passes
the same Group 0 dry-run/offline/privacy/budget gates.

## Acceptance Packet

Each candidate arm writes one decision row:

- candidate ids;
- agent engine, provider profile, `wire_api`, model, evidence lane, seed,
  repeat index;
- feature flags and dependency candidate ids;
- elapsed time, response/model turns, context max, cache metrics, and major
  latency buckets;
- checker state and behavior-quality metrics;
- privacy/schema gate state;
- accepted, rejected, inconclusive, blocked, bypassed, superseded, or added;
- queue decision reason and next recommended candidate/group;
- artifact links and explicit waiver if accepting a faster-but-worse result.

## Evidence Ladder

Required no-provider gates before any live row:

```bash
.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py \
  --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json \
  --dry-run

.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py \
  --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json \
  --offline-preflight \
  --decision-packet output/agent-sdk-speedup-foundation/decision.json
```

Shared performance extraction and comparison are now the canonical analysis
surface for baseline/candidate rows:

```bash
.venv/bin/python scripts/reports/extract_live_report_metrics.py \
  --write-model-call-metrics \
  <baseline-run-dir> <candidate-run-dir>

.venv/bin/python scripts/reports/compare_live_report_metrics.py \
  --baseline-run-dir <baseline-run-dir> \
  --candidate-run-dir <candidate-run-dir> \
  --output output/agent-sdk-perf-followups/<row-id>-comparison.json
```

Use the generated `roboclaws_report_performance_metrics_v1` packets for Q, Y,
and Z decisions. If `provider_request_metrics.jsonl` exists, include its
provider HTTP fields as transport timing only. If it does not exist, record
provider timing as unavailable rather than inferring it from wall time.

Focused deterministic gates for runner/schema changes:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py \
  tests/unit/agents/test_live_runtime.py \
  tests/unit/reports/test_live_performance.py

.venv/bin/ruff check \
  scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py \
  scripts/reports/extract_live_report_metrics.py \
  scripts/reports/compare_live_report_metrics.py \
  tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py \
  tests/unit/reports/test_live_performance.py \
  roboclaws/agents/drivers/openai_agents_live.py \
  tests/unit/agents/test_live_runtime.py
```

Provider-backed live rows are local/manual gates. They require explicit approval
and the approval checklist below.

## Approval Gate For Live Runs

Before any provider-backed run, record:

- planned max live runs;
- planned max wall-clock;
- context hard limits;
- model/candidate concurrency;
- racing multiplier, if any;
- provider credentials available;
- backend slot available;
- `just dev::network-status` result;
- explicit budget acknowledgement.

## Stop Condition

Stop the current pass when:

- the selected candidate is accepted, rejected, bypassed, superseded, or
  blocked with evidence;
- the acceptance packet names the next candidate/group or explains why no next
  candidate is worth the cost;
- Group 0 gates still protect any future live run;
- no public/default route, MCP contract, checker semantics, or artifact privacy
  boundary regressed.

Set this document to `PARK` only when Q/Y show that remaining work is blocked,
not worth the cost/risk, or purely future/optional. Set it to `DONE` only after
the accepted perf objective has actually been achieved and no required follow-up
remains.

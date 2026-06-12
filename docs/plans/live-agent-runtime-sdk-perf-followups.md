---
plan_scope: live-agent-runtime-sdk-perf-followups
status: CONTINUE
source:
  - docs/plans/live-agent-runtime-sdk-spike.md
  - 2026-06-10 Agent SDK performance optimization pass
  - 2026-06-10 Group 0 speedup foundation preflight
last_reviewed: 2026-06-12
---

# Live Agent Runtime SDK Perf Follow-ups

## Status

CONTINUE.

This is the execution gate for the unfinished `openai-agents-live` performance
work. The completed SDK runtime spike remains in
`docs/plans/live-agent-runtime-sdk-spike.md`.

This plan is a re-planned candidate queue, not a promise to run every item. Run
one candidate or group, summarize evidence, update the queue, then continue.

2026-06-12 standing authorization update: the maintainer authorizes the agent
to run any deterministic, provider-backed, simulator/backend, A/B, matrix, and
raw-FPV tests it judges useful for this plan. These runs do not need additional
per-run human approval. Before each live/provider-backed run, still record the
planned run count, wall-clock/cost caps, context/concurrency/racing caps,
credential/backend availability, and `just dev::network-status`; stop on
missing credentials/backend access, network-policy failure, privacy/schema
failure, or unsafe/default-contract drift.

2026-06-11 review after timing-analysis updates: the plan now treats
`roboclaws.reports.live_performance` as the canonical speed/quality packet,
records provider HTTP timing as transport-only evidence, and keeps `wire_api`
as a matrix axis so Responses and Chat-compatible SDK rows are not conflated.

2026-06-11 route-support update: the private OpenAI Agents SDK route supports
Responses profiles (`codex-env`, `mify`) and Chat-compatible profiles
(`mimo-openai-chat`, `kimi-openai-chat`). Matrix rows and shared performance
packets now carry `wire_api`; Chat rows remain compatibility evidence unless
their own metrics justify a speed claim.

2026-06-11 Candidate A update: the private SDK route now loads bounded
`molmo-realworld-cleanup` `SKILL.md` context from the repo checkout and passes
it to the OpenAI Agents SDK instructions. Artifacts record only
`openai-agents-skill-context.json` metadata plus `live_timing.json`
`agent_sdk_skill_context` summary fields: skill name, path, hash, byte counts,
truncation state, and estimated tokens. They do not persist the skill body,
raw prompts, tool payload bodies, credentials, or private evaluator truth.

2026-06-11 Candidate G/J deterministic update: the private SDK route now
constructs explicit SDK `ModelSettings` and `RunConfig` instead of relying on
provider defaults. Timing/event/cache summaries record sanitized settings,
trace privacy config, prompt-cache retention policy, and a stable-prefix hash.
This is settings attribution only; provider-backed A/B speed claims still need
live baseline/candidate rows under the standing authorization and run caps.

2026-06-12 Candidate I/AB deterministic prep update: the installed OpenAI
Agents SDK exposes Responses continuation/session arguments and
`RunConfig.call_model_input_filter`. The private SDK route now records the
Responses-only feature surface as gated capability metadata and supports an
opt-in model-input compaction arm through `--model-input-compaction` /
`ROBOCLAWS_OPENAI_AGENTS_INPUT_COMPACTION`. The compaction hook is model-facing
only: it can replace oversized public tool outputs with hash/size summaries
before a model call, while MCP traces, reports, and run artifacts remain
complete. Sanitized events record aggregate counts and byte deltas only, not
raw prompts, model text, tool payload bodies, credentials, or private truth.
`live_timing.json` / `timeline.latency_attribution` summarize the same
compaction arm through `model_input_filter_metrics`. No provider-backed speed
claim is made.

2026-06-12 Q/Y deterministic enrichment update: the Group 0 decision packet now
summarizes row-level reducible latency buckets and recommendations from shared
performance packets. Each bucket report records model/SDK between-tool gap,
visual capture, MCP/backend tool-handler time, residual/unattributed time,
dominant bucket, failed/noop tool count, and recommendation candidates. The
packet summary aggregates candidate counts, candidate-group counts, dominant
bucket counts, top candidate ids/groups, and per-row recommendation evidence.
The refreshed no-provider packet accepted 5 supported fixture rows, preserved 2
unsupported rows, and ranked Group 2 lane-specific reductions first after the
already-accepted deterministic Group 1 prep. This remains diagnostic
recommendation evidence only, not a provider-backed speed claim.

2026-06-12 Candidate N deterministic prep update: the opt-in SDK
`call_model_input_filter` compaction arm now includes repeated `metric_map`
delta summarization. The first `metric_map` output remains available in model
input; later repeated `metric_map` outputs can be replaced with a smaller
hash/size/count summary only when that summary is smaller than the original
public tool output. MCP traces, reports, and run artifacts still retain full
tool responses. `model_input_filter_metrics` now aggregates
`metric_map_output_count`, repeated-map count, delta-compacted count, and
metric-map byte deltas. This is deterministic model-facing prep only; no live
speed claim is made.

2026-06-12 Candidate O deterministic prep update: the private SDK route now has
an opt-in `camera_grounded_composite_tools` profile flag and cleanup-server
`--agent-sdk-camera-grounded-composite-tools` switch. When enabled for
`camera-grounded-labels`, the server registers `observe_camera_grounded_candidates`,
which performs the existing `observe` plus server-side `declare_visual_candidates`
path and returns the existing observe payload plus compact declaration output.
Default public MCP/profile tools remain unchanged, the shortcut is rejected when
not enabled, and trace reviewability is preserved through the underlying
sub-tool events. This is deterministic SDK-private prep only; no live speed
claim is made.

2026-06-12 Candidate P deterministic prep update: the raw-FPV budgeted profile
now has a repeated visual-candidate failure rail through
`raw_fpv_repeated_failure_limit`, defaulting to 3 for
`raw_fpv_budgeted_v1`. The live runner classifies repeated
`navigate_to_visual_candidate` failures as
`raw_fpv_repeated_candidate_failure`, records only compact failure fingerprints
and aggregate terminal counts, and surfaces the same compact terminal summary in
timeline latency attribution. The just route forwards the opt-in override from
`ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_REPEATED_FAILURE_LIMIT`. This is deterministic
raw-FPV stabilization prep only; no cleanup-pass or speed claim is made.

2026-06-12 Candidate AA deterministic prep update: the raw-FPV budgeted profile
now enables a private SDK `raw_fpv_image_memory_v1` arm inside
`RunConfig.call_model_input_filter`. The policy keeps the latest full raw-FPV
image frame in model input and replaces older full-frame image blocks with
hash/size/observation summaries only when the summary is smaller. MCP traces,
report artifacts, and robot-view image files remain complete, and the raw-FPV
MCP boundary still returns compact state plus a full image block. Timing
summaries record aggregate retained/evicted image counts and byte deltas only.
This is deterministic model-facing prep only; no cleanup-pass or speed claim is
made.

2026-06-12 Candidate P/AA live gate update: a scoped raw-FPV live attempt is
recorded in `docs/status/active/agent-sdk-raw-fpv-live-caps.json`. The initial
`mify` Responses route was blocked before launch because `camera-raw-fpv`
requires verified image transport and the provider registry marks
`openai-agents-sdk+mify` `image_transport=unknown`. The verified
`openai-agents-sdk+codex-env` route was then tried twice at
`output/agent-sdk-perf-followups/raw-fpv-budgeted-codex/0612_1512/seed-7/`
and
`output/agent-sdk-perf-followups/raw-fpv-budgeted-codex-retry/0612_1514/seed-7/`.
Both attempts failed before task work with classified
`provider_transient_failure` / `upstream_unavailable` after the model-service
retry path. The attempts prove the raw-FPV route gates and telemetry are
working, but produce no raw-FPV behavior, cleanup-pass, image-memory, repeated
failure, or speed evidence. Do not bypass the raw-FPV image-transport guard;
retry P/AA only after `codex-env` upstream availability recovers or another
OpenAI Agents SDK provider has verified `image_transport=supported`.

2026-06-12 live row update: the first resumed provider-backed pass satisfied
the no-provider Group 0 dry-run/offline preflight, recorded `network: work`
with repo-local `codex-env` / `mify` routes allowed, confirmed provider
credentials and one MolmoSpaces/MuJoCo backend slot, and used concurrency 1,
racing multiplier 1, and a 45-minute wall-clock cap per row. The
`codex-env` GPT baseline row for `world-public-labels` stopped before task work
with a classified transient provider 502 (`provider_transient_failure`,
`upstream_unavailable`) after the model-service retry path. The `mify`
Responses baseline and `mimo_compact_v1` candidate rows both finished for
`world-public-labels`, but the shared comparison is diagnostic rather than a
speed win: the candidate improved recorded cleanup quality, reduced model and
MCP calls by 2 each, but was +5.746s observed wall and +8.749s observed model
API time with +7033 uncached input tokens. The quality comparator now caps
sweep over-coverage at 1.0 so a baseline that visits extra inspection waypoints
does not create a false quality-regression gate when a candidate still reaches
full required coverage. No public/default route, MCP contract, checker
semantics, or artifact privacy boundary changed.

2026-06-12 Q/Y live-refresh update: a zero-provider refresh manifest
(`docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`) now points at
the completed `mify` Responses `world-public-labels` baseline/candidate pair
and writes `output/agent-sdk-perf-followups/live-refresh-decision.json`. The
refresh accepted the row as diagnostic recommendation evidence with no provider
calls planned and no privacy/schema failure. It kept model/SDK between-tool gap
as the dominant bucket (`205.026s`, 63.34% of observed wall), recorded material
visual capture (`93.256s`, 28.81%), and recommended Group 2 lane-specific work
(`N` for repeated `metric_map`, `F` for visual capture) plus already-accepted
Group 1 SDK levers. External compatibility evidence from the completed
`mimo-openai-chat` camera-grounded DINO run
(`output/experiments/mimo-pro-text-lanes/agent-sdk-camera-grounded-dino/0612_0950/seed-7/`)
shows 14 `declare_visual_candidates` calls and a large camera-grounded
between-tool/visual bucket, which supports Candidate O as the next
camera-grounded A/B target. That external row is Chat-compatible diagnostic
evidence, not a Responses speed claim. A separate user-owned
`camera-grounded-labels` sim-labels run currently holds the only visual backend
slot on port `18788`; do not launch another live row until it releases the
slot.

2026-06-12 Candidate O live diagnostic update: the `mify` Responses
`camera-grounded-labels` baseline/composite pair now exists at
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-baseline/0612_1012/seed-7/`
and
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite/0612_1032/seed-7/`,
with metrics in `output/agent-sdk-perf-followups/mify-camera-grounded-baseline-metrics.json`,
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-metrics.json`,
and
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-comparison.json`.
The comparison helper marks the candidate row accepted for same-or-better
recorded quality and faster observed wall time (`-37.851s`), but this is not a
valid Candidate O speed win: the trace contains zero
`observe_camera_grounded_candidates` requests and still contains 19 `observe`
plus 19 `declare_visual_candidates` requests. The composite profile flag and
server opt-in were enabled, but the agent did not call the shortcut, so treat the
row as diagnostic provider/runtime evidence and keep Candidate O live proof
inconclusive until a row actually exercises the composite tool.

2026-06-12 Candidate O prompt-selection repair: the private compact
`camera-grounded-labels` kickoff prompt now switches to an
`observe_camera_grounded_candidates` cadence when the resolved Agent SDK profile
has `camera_grounded_composite_tools.enabled=true`. Default camera-grounded
prompts still use the public two-step `observe` plus `declare_visual_candidates`
path, and the server flag remains private/opt-in. Focused prompt/runtime tests
prove the live runner sends the shortcut prompt when the O flag is enabled; the
remaining proof is a tightly scoped provider-backed rerun that confirms the
trace contains `observe_camera_grounded_candidates` requests before making any
speed claim.

2026-06-12 Candidate O live retry update: the scoped `mify` Responses
camera-grounded promptfix2 retry completed at
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-promptfix2/0612_1126/seed-7/`.
The live runner originally exited nonzero only because the checker had a stale
public-agent-view provenance allowlist; `run_result.json` and `report.html`
were already written. The checker now accepts the public
`camera-grounded-labels` producer/model provenance only inside the
camera-model-policy observed-object branch, while retaining the existing
private-field and support-estimate checks. Direct checker reruns now pass for
both the promptfix2 artifact and the earlier `0612_1032` composite diagnostic
artifact. The promptfix2 trace exercises the shortcut with
5 `observe_camera_grounded_candidates` requests, plus 16
`declare_visual_candidates` requests and 19 underlying `observe` requests from
the composite tool's trace-preserving substeps. Shared report-performance
comparison against the `0612_1012` baseline is accepted diagnostically with
same recorded quality (`completion_status=success`, `restored_count=4/5`,
`sweep_coverage_rate=1.0`, `disturbance_count=0`), `-303.142s` observed wall,
`-319.020s` observed model API time, and `+50586` uncached input tokens. Treat
this as a valid Candidate O mechanism/diagnostic speed row, not a normalized
or publishable speed claim.

2026-06-12 Candidate O continuation-tightening update: trace review of the
promptfix2 row shows the composite cadence held for the first 5
`observe_camera_grounded_candidates` calls, but after the SDK continuation the
agent fell back to standalone `observe` plus `declare_visual_candidates` for 11
remaining declarations. The private compact continuation prompt now carries a
profile-specific camera-grounded composite reminder when
`camera_grounded_composite_tools.enabled=true`, telling the agent to keep using
`observe_camera_grounded_candidates` for remaining waypoint observations and
not resume the older two-step cadence. This changes only the private SDK
composite continuation prompt; default camera-grounded prompts, public
MCP/profile behavior, traces, and reports remain unchanged. Focused tests prove
the continuation prompt keeps the composite cadence without replaying the full
kickoff prompt. No new provider-backed speed claim is made until a paired O
rerun exercises the tightened continuation.

2026-06-12 Candidate O continuation-tightening live result: the scoped `mify`
Responses rerun completed as expected-rejected diagnostic evidence at
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-continuation-tightening/0612_1627/seed-7/`,
with caps in
`docs/status/active/agent-sdk-o-continuation-tightening-live-caps.json`,
metrics
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-continuation-tightening-metrics.json`,
and comparison
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-continuation-tightening-comparison-diagnostic.json`.
The O cadence mechanism improved: trace review records 14
`observe_camera_grounded_candidates` calls, 14 total
`declare_visual_candidates` requests, all 14 declarations composite-internal,
and 0 standalone declarations. The row is still rejected as a speed win because
it failed before `done` / `run_result.json` with
`provider_context_budget_exceeded` (`current_input_tokens=175618` against
`context_hard_limit_tokens=96000`). It was still faster than the camera-grounded
baseline at failure time (`-161.007s` observed wall, `-164.953s` observed model
API), but the quality gate failed because task completion evidence is missing.
Treat this as proof that O's residual two-step cadence is fixed and that the
next bottleneck is behavior-preserving context/session growth, not as an
accepted or normalized speed row.

2026-06-12 Q/Y promptfix2 refresh update: the zero-provider live-refresh
manifest now includes the O promptfix2 retry and the decision packet classifies
camera-grounded declaration work into composite-internal versus standalone
requests. This avoids treating trace-preserving composite substeps as leftover
two-step agent work. The refreshed packet accepts both completed live rows and
records promptfix2 as 5 `observe_camera_grounded_candidates` requests, 16 total
`declare_visual_candidates` requests, 5 composite-internal declarations, and 11
standalone declarations. Because standalone declarations remain, Q/Y still
recommends residual O work for camera-grounded, but the stronger normalized
latency priority is now: (1) direct wall-clock visual capture reduction F,
(2) N/I/AB live A/B for model/SDK between-tool gap and repeated map/state
payloads, and (3) O paired repeats or prompt/tool tightening for the remaining
standalone two-step calls. Token deltas are diagnostic context only and are not
a deciding cost metric for this plan.

2026-06-12 Candidate F live A/B update: the scoped `mify` Responses
`world-public-labels` action-timeline run completed at
`output/agent-sdk-perf-followups/mify-world-public-mimo-compact-action-timeline/0612_1303/seed-7/`
and is compared against
`output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`
in
`output/agent-sdk-perf-followups/mify-world-public-action-timeline-comparison-diagnostic.json`.
The mechanism worked locally: `robot_view_capture_s` dropped from `93.256s` to
`54.975s`. The row is still rejected as a speed win because behavior quality
regressed (`restored_count=4/5` to `3/5`, `completion_status=success` to
`partial_success`) and end-to-end time got worse (`+181.786s` observed wall,
`+216.535s` observed model API, `+212.509s` model/SDK between-tool gap). Q/Y now
keeps this as an expected-rejected evidence row instead of a pending F run.
Given the maintainer clarification that token cost is not a decision objective,
token deltas remain telemetry only; prioritize wall-clock and normalized or
paired-comparable latency. At that point this moved the next high-leverage work toward
N/I/AB live A/B against the dominant model/SDK between-tool gap and toward D/C
racing prep before any C live racing experiment, rather than another standalone
F row.

2026-06-12 Candidate I/N/AB live A/B update: the scoped `mify` Responses
`world-public-labels` input-compaction run completed as an expected-rejected
evidence row at
`output/agent-sdk-perf-followups/mify-world-public-mimo-compact-input-compaction/0612_1327/seed-7/`,
compared against
`output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`
in
`output/agent-sdk-perf-followups/mify-world-public-input-compaction-comparison-diagnostic.json`.
The model-input filter mechanism worked: `model_input_filter_metrics` reports
`input_bytes_before=71186480`, `input_bytes_after=4316462`,
`input_byte_reduction_ratio=0.939364`, `metric_map_output_count=292`, and
`repeated_metric_map_output_count=208`. Model work also dropped substantially
(`max_input_tokens=118979` to `25152`, uncached input tokens `197838` to
`63045`). The row is rejected because it failed to call `done` after two SDK
invocations, has no `run_result.json`, raised failed/noop tool count to `31`,
and got slower (`+62.627s` observed wall, `+102.956s` observed model API,
`+102.04s` model/SDK between-tool gap). Since token cost is not a decision
objective, this proves compaction mechanics but argues against accepting the
current I/N/AB policy as a wall-clock improvement.

2026-06-12 Candidate D deterministic prep update: the private SDK model
boundary now records per-arm racing observability before enabling Candidate C.
Each SDK model request writes sanitized `model_racing_arm_start`,
`model_racing_arm_finish`, and failure events with a stable call/arm id,
provider profile, wire API, model id, elapsed time, winner/cancel flags,
failure class, usage/token availability, and loser-billing-unknown fields. The
current implementation is single-arm/no-racing (`racing_enabled=false`,
`racing_multiplier=1.0`) and does not change the default model call path,
public MCP/profile behavior, or cleanup success gates. `live_timing.json` now
summarizes the events as
`model_racing_observability_metrics` under timeline latency attribution. This
was deterministic observability prep only at this point in the log; the later C
live row is recorded below.

2026-06-12 Candidate C deterministic prep update: the private SDK model
boundary now has an opt-in `get_response` racing arm through
`--model-racing` / `ROBOCLAWS_OPENAI_AGENTS_MODEL_RACING`, with
`--model-racing-arm-count` / `ROBOCLAWS_OPENAI_AGENTS_MODEL_RACING_ARM_COUNT`
as the live-run cap surface. Defaults remain single-arm/no-racing. When enabled,
each SDK `get_response` request launches the configured number of same-provider
arms, returns the first successful SDK model response to the OpenAI Agents SDK
history, cancels pending losers, and records sanitized winner/loser/cancel
events through the Candidate D telemetry surface. `stream_response` is
explicitly kept single-arm and is labeled as such in racing metrics. Focused
unit tests cover winner selection, loser cancellation, all-arm failure, stream
non-racing behavior, and prompt/privacy redaction. This is deterministic C prep
only; no provider-backed C live row or wall-clock speed claim is made.

2026-06-12 Candidate C live A/B update: the scoped `mify` Responses
`world-public-labels` racing pair completed at
`output/agent-sdk-perf-followups/c-racing-baseline/0612_1429/seed-7/`
and
`output/agent-sdk-perf-followups/c-racing-candidate/0612_1448/seed-7/`,
with caps recorded in
`docs/status/active/agent-sdk-c-racing-live-caps.json` and comparison
`output/agent-sdk-perf-followups/c-racing-comparison-diagnostic.json`.
The mechanism worked: candidate `live_timing.json` records
`racing_enabled=true`, `racing_multiplier=2.0`, 53 raced model calls, 106
arms, 76 winners, and 75 cancelled loser arms with sanitized D telemetry. The
row is rejected as a speed win because behavior quality regressed
(`completion_status=success` to `partial_success`, `restored_count=4` to `3`)
even though observed wall time improved by `-260.987s` and
`mcp_between_tool_gap_s` improved by `-247.174s`. Observed model API time rose
by `+397.292s`, as expected for two-arm racing work, and token/cost telemetry
remains non-decisive under the current priority. Q/Y refresh now records C as
expected-rejected evidence rather than a pending live arm.

2026-06-12 Candidate AC deterministic prep update: the private SDK
`call_model_input_filter` path now has an opt-in
`camera_grounded_history_v1` policy through
`--camera-grounded-history-compaction` /
`ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_HISTORY_COMPACTION`. The policy is
completion-safe prep for the O context-growth blocker: it keeps the latest
camera-grounded observation/declaration outputs model-visible, replaces only
older camera-grounded history with compact hash/observation/candidate summaries
when smaller, and leaves MCP traces, reports, and run artifacts complete.
Runtime events and `live_timing.json` aggregate only counts, byte deltas, mode,
provider/model/wire ids, and summary hashes; they do not persist raw prompts,
model text, full tool payload bodies, credentials, private truth, or image
bytes. Defaults remain off for public/default routes and existing compact
profiles. This deterministic prep is now followed by the fixed4 provider-backed
O+AC paired row recorded below.

2026-06-12 Candidate O+AC fixed4 live result: the scoped `mify` Responses
`camera-grounded-labels` O+AC row completed and is accepted as paired
diagnostic evidence at
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-ac-fixed4/0612_1841/seed-7/`,
with caps in
`docs/status/active/agent-sdk-o-ac-camera-grounded-live-caps.json` and
comparison
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-fixed4-comparison.json`.
The row preserved task completion and report quality (`completion_status=success`,
`restored_count=4/5`, `semantic_accepted_count=5/5`, `disturbance_count=0`,
`failed_or_noop_tool_count=0`) while reducing observed wall time by
`-659.477s`, observed model API time by `-653.563s`, and model/SDK
between-tool gap by `-638.809s` against the existing `0612_1012`
camera-grounded baseline. The mechanism exercised
`observe_camera_grounded_candidates` 14 times and compacted 270 of 457
camera-grounded history items, reducing camera-grounded history bytes by
`5255583` and total model-facing input bytes by `20.9928%`. Treat this as the
current best paired wall-clock result, not a normalized or publishable speed
claim; calibrated/repeated evidence and broader B baseline coverage are still
required before broad claims.

2026-06-12 Candidate O+AC repeat live result: the scoped repeat row completed
at
`output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-ac-repeat-mify/0612_1909/seed-7/`,
with caps in
`docs/status/active/agent-sdk-o-ac-camera-grounded-repeat-live-caps.json` and
comparison
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-repeat-mify-comparison.json`.
It is accepted as repeat paired diagnostic evidence: report quality stayed
same-or-better (`completion_status=success`, `restored_count=4/5`,
`semantic_accepted_count=5/5`, `disturbance_count=0`,
`failed_or_noop_tool_count=0`) while observed wall/model API/between-tool gap
improved by `-630.633s` / `-619.022s` / `-612.38s`. The repeat exercised 13
`observe_camera_grounded_candidates` calls, recorded 14
`declare_visual_candidates` calls, compacted 192 of 364 camera-grounded history
items, and reduced camera-grounded history bytes by `3483115`. This strengthens
the O+AC wall-clock direction, while the one residual standalone declaration and
missing calibration coefficients mean the claim remains diagnostic rather than
normalized or publishable.

2026-06-12 O+AC calibrated-normalized diagnostic update: the shared
report-performance extractor/comparison now accepts an explicit
`roboclaws_model_latency_calibration_v1` packet through `--calibration` and
keeps the default no-calibration behavior unchanged. A named diagnostic packet
was generated from 193 sanitized model-call rows across the camera-grounded
baseline, fixed4, and repeat artifacts at
`output/agent-sdk-perf-followups/mify-camera-grounded-o-ac-calibration.json`.
It is available, but its limitation is explicit:
`simple_two-feature_fit_for_diagnostics_only_requires_named_dataset_review`, so
it is not a committed repo-default or publishable calibration. The calibrated
comparison artifacts are
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-fixed4-normalized-comparison.json`
and
`output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-repeat-mify-normalized-comparison.json`.
Both preserve the same quality gates and accepted wall-clock comparison. Under
this diagnostic calibration, estimated model-work deltas increase
(`+163.807s` fixed4, `+338.039s` repeat), while model-latency residual deltas
drop sharply (`-817.37s` fixed4, `-957.061s` repeat). Interpret this as
evidence that the O+AC paired wall-clock gain is coming from reduced residual
model/SDK/provider waiting rather than reduced calibrated model-work. The claim
is now calibrated-diagnostic, still not broad or publishable.

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
- Candidate A deterministic skill-context proof is implemented for the private
  SDK route. The route now records the exact canonical skill context by
  metadata/hash and sends the bounded `SKILL.md` text to the SDK instructions
  without changing public MCP/profile behavior.
- Candidate G/J deterministic settings/cache attribution is implemented. The
  route records explicit SDK model/run settings, disables sensitive trace data,
  tracks stable prompt-prefix hashes, and carries prompt-cache retention policy
  through `live_timing.json` / events without making a speed claim.
- Candidate I deterministic prep is implemented as an opt-in SDK
  `call_model_input_filter` arm. It records aggregate compaction evidence and
  proves fake model-facing payload bytes can drop without changing persisted
  trace/report artifacts. It is disabled by default and still needs live A/B
  evidence before any speed claim.
- Candidate AB deterministic audit is partially implemented: timing/events now
  record whether Responses-only continuation/session levers are available for
  the active `wire_api`, and keep server-managed continuation disabled by
  default until a live A/B row proves task-state/report completeness.
- Group 0 offline preflight now explicitly keeps raw-FPV expected-terminal rows
  as classified diagnostic evidence instead of applying the full cleanup
  `run_result.json` success gate to that lane. The privacy gate scans
  `openai-agents-events*.jsonl`, including model-input-filter events, for
  forbidden keys and markers.
- Q/Y deterministic decision enrichment is implemented in the Group 0
  preflight. `reducible_bucket_report` rows now expose latency buckets,
  dominant buckets, failed/noop counts, and candidate recommendations, while the
  decision packet summary aggregates candidate and candidate-group rankings
  without adding provider calls or raw payload persistence.
- Q/Y has also been refreshed against completed live Responses pairs through
  `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`. This is an
  offline/no-provider packet over existing run artifacts, not a new live row.
  It accepted the completed `mify` world-public diagnostic comparison plus the
  camera-grounded O promptfix2 mechanism row, records composite-internal versus
  standalone camera declarations, and points the next work toward wall-clock
  visual capture reduction, N/I/AB model-facing compaction A/B, and residual O
  tightening/repeats rather than token-cost-only work.
- Candidate N deterministic prep is implemented inside the existing opt-in SDK
  model-input compaction arm. Repeated `metric_map` outputs are summarized only
  in model-facing SDK input, only when smaller than the original, and only with
  hash/size/count metadata; complete MCP trace/report artifacts remain
  unchanged.
- Candidate F deterministic prep is implemented as an SDK-private
  `robot_view_capture_policy=action_timeline` arm. The cleanup server can skip
  report-only `observe` / `scene_objects` robot-view captures while preserving
  before/after views, cleanup action views, raw-FPV observe artifact capture,
  traces, and reports. The OpenAI Agents live runner records the policy in
  `agent_sdk_perf_profile` and forwards it to the private cleanup server only
  when explicitly requested. No live speed claim is made.

## Not Done

- Full live GPT/MiMo x evidence-lane matrix.
- Follow-up optimization groups 1-5 beyond accepted deterministic prep and
  diagnostic rows still need live A/B, repeats, baseline refresh, or promotion
  guards before any normalized/publishable speed claim.
- Provider-backed Responses-native A/B evaluation for server-managed
  continuation, conversation/session state, prompt-cache retention, and
  model-input compaction.
- OpenAI Agents SDK provider-backed matrix rows for Chat-compatible profiles
  such as `mimo-openai-chat` and `kimi-openai-chat`, when credentials and
  backend access are available under the standing authorization. These rows
  prove compatibility unless their own metrics support a speed claim.
- Publishable speedup claim across all relevant lanes and providers.

## Hard Constraints

- `openai-agents-live` stays private/non-default unless separately promoted.
- `done` / `run_result.json` remains the cleanup success signal.
- Default MCP/profile behavior must not change without cross-client proof.
- Provider-backed live matrix, A/B, simulator/backend, and raw-FPV tests are
  pre-authorized by the maintainer for this plan; no additional per-run human
  approval is required. Runs still require credential/backend availability,
  `just dev::network-status`, recorded wall-clock/cost/context/concurrency
  caps, and privacy/schema gates.
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
- Chat-compatible rows: `mimo-openai-chat` and `kimi-openai-chat` after
  dependency and credential gates pass.
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
3. Candidate A is accepted; keep its metadata/privacy guard in future rows.
4. Candidate G/J deterministic settings and cache attribution is accepted; live
   A/B for speed is authorized and should run when credentials/backend access
   and recorded caps are available.
5. Candidate I/AB deterministic prep is accepted, and one `mify`
   `world-public-labels` input-compaction live row has completed. The row proves
   model-facing byte/token compaction but is rejected for wall-clock and cleanup
   behavior. The latest O continuation-tightening row also failed on provider
   context budget after fixing standalone camera declarations. Further I/N/AB
   work should change the compaction policy or continuation/session behavior
   before another live row.
6. Q/Y deterministic recommendation enrichment is accepted for Group 0; it has
   been refreshed from the completed `mify` world-public pair, O promptfix2
   camera-grounded mechanism row, and the expected-rejected F action-timeline,
   I/N compaction, C racing, and O continuation-tightening rows. Refresh again
   whenever new live rows or candidate arms change the packet.
7. Candidate N deterministic prep is accepted inside the opt-in model-input
   compaction arm. The first live I/N row proved compaction events and repeated
   map counters, but `metric_map_bytes_reduced=0` and behavior regressed; do not
   claim an N speedup from that row.
8. Run scoped B live baseline refresh before any strong speed claim when
   credentials/backend access and recorded caps are available.
9. Candidate O deterministic prep is accepted as an SDK-private opt-in MCP
   composite-tool flag for `camera-grounded-labels`. The first `mify` Responses
   live diagnostic row had same-or-better quality and faster wall time, but the
   trace did not call `observe_camera_grounded_candidates`. The promptfix2
   retry does exercise the shortcut and passes the checker after the narrow
   camera-grounded provenance allowlist repair; classify it as a valid
   mechanism/diagnostic speed row, not a normalized or publishable speed claim.
   The refreshed Q/Y packet initially showed O was not exhausted: 11 standalone
   camera declarations remained after the 5 composite calls. Continuation prompt
   tightening fixed that cadence in the latest live rerun, reducing standalone
   declarations to 0, but the row exceeded the provider context budget before
   `done`. Do not rerun O unchanged; the next O evidence needs a
   behavior-preserving context/session redesign before another paired proof row.
10. Candidate P deterministic prep is accepted as a raw-FPV repeated visual
    candidate failure rail. A live raw-FPV gate attempt is now blocked: `mify`
    lacks verified image transport and `codex-env` hit repeated
    provider-transient 502 before task work. Cleanup-pass and speed claims still
    require report-quality evidence.
11. Candidate AA deterministic prep is accepted as raw-FPV model-facing image
    memory inside the private SDK input filter. The same live raw-FPV gate
    attempt produced no image-memory behavior evidence because provider failure
    happened before the first task model response. Cleanup-pass and speed claims
    still require report-quality evidence.
12. Candidate F deterministic prep is accepted as an SDK-private
    `robot_view_capture_policy=action_timeline` arm, and one `mify`
    `world-public-labels` live A/B row has completed. The policy reduced
    `robot_view_capture_s` but the row is rejected because cleanup quality
    regressed and observed wall/model time increased. Do not claim an F speedup
    from this row; only revisit F as a paired/repeated or lane-specific follow-up
    after higher-leverage model/SDK-gap work.
13. Because token cost is not a deciding objective, D/C racing is no longer
    deferred mainly on cost. Candidate D deterministic observability prep is now
    implemented as a single-arm/no-racing event and timing surface. Candidate C
    deterministic prep is implemented behind explicit opt-in flags and live cap
    fields, and one capped `mify` Responses `world-public-labels` live A/B has
    completed. The mechanism reduced observed wall time but regressed cleanup
    quality, so C is now expected-rejected evidence rather than an accepted
    speed win. Do not rerun the same racing policy unchanged; next wall-clock
    work should either preserve behavior in a redesigned compaction/session
    arm, gather O paired/tightening evidence, retry raw-FPV P/AA only after the
    provider/image-transport block clears, or broaden B baseline coverage.
    Still defer K/E/M/X unless the dependency evidence below appears.
14. Candidate AC deterministic prep is accepted as a narrower
    camera-grounded history compaction arm for the O context-growth blocker.
    It is not the rejected broad I/N policy: AC keeps recent actionable
    camera-grounded outputs full, summarizes only older camera-grounded
    observation/declaration history in model-facing SDK input, and preserves
    complete MCP traces/reports/run artifacts. The fixed4 provider-backed O+AC
    row completes the first paired diagnostic proof with `done`,
    `run_result.json`, same-or-better report-quality evidence, and lower
    paired-comparable wall/model latency. Normalized or publishable claims still
    need repeated/calibrated evidence.

Current wall-clock priority after the O+AC calibrated-normalized diagnostic update:

1. Scoped B baseline coverage across provider/model, `wire_api`, and evidence
   lanes before broad speed claims. The current live proof is concentrated on
   `mify` Responses and two evidence lanes.
2. Promote calibration only after a named reviewed dataset with error statistics
   exists; the current O+AC calibration is diagnostic and local to the completed
   artifacts.
3. Raw-FPV P/AA live retry only after `codex-env` upstream availability recovers
   or another OpenAI Agents SDK route has verified image transport.
4. Revisit deferred H/M/K/E only if refreshed Q/Y evidence shows a material
   remaining bucket that the accepted O+AC path, B coverage, and raw-FPV retry
   do not address.

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
| W | keep-for-normalized-claims | Add repeatability policy for publishable or normalized claims. | One live run can be lucky, and the current target is wall-clock plus normalized or paired-comparable latency rather than token cost. | Winner rows can be repeated or paired; single-run rows are labeled diagnostic. | Do not require repeats for first diagnostic pass; require paired/repeated evidence before normalized or publishable speed claims. |
| Y | accepted-deterministic-enrichment, live rows authorized | Generate decision packet/dashboard from shared performance packets. | Reviewers need one closeout artifact, but the metrics source should be canonical. | Implemented for Group 0: packet records accepted/rejected/inconclusive/blocked/unsupported rows plus aggregate recommendation summary, top candidate ids/groups, dominant bucket counts, and artifact links. Live rows are authorized under the standing run authorization and need packet refresh after execution. | Missing decision data means inconclusive, not accepted; extend only when new live rows, candidate arms, or dashboard outputs need it. |
| B | keep | Refresh live provider/model x evidence-lane baseline matrix with `wire_api` as an axis. | GPT/MiMo, Responses/Chat routes, and evidence lanes differ materially; anecdotes are insufficient. | Responses rows cover `codex-env`/`mify`; Chat-compatible rows cover `mimo-openai-chat`/`kimi-openai-chat` only when supported; unsupported rows are labeled. | Live rows are authorized by this plan when credentials/backend access and recorded caps are available; do not expand into Claude SDK integration. |
| Z | gate, mostly done | Use shared report-performance comparison for quality and timing guardrails. | Faster can still mean worse cleanup. | Rows include shared quality fields plus wall, model/API, provider HTTP, context, call-count, and residual timing fields where available. | Reject faster-but-worse unless explicitly waived; missing telemetry is unavailable, not zero. |
| Q | accepted-deterministic-enrichment, refresh with live rows | Classify irreducible floor and remaining waste from shared performance packets. | Next work should target the largest reducible bucket. | Implemented for Group 0: bucket reports separate model/SDK between-tool gap, visual capture, MCP/backend tool-handler time, residual/unattributed time, failed/noop counts, and dominant bucket. Provider HTTP, model/API, context-growth, and turn-waste fields remain live-row dependent when telemetry exists. | Stop or bypass next arms when remaining gain is smaller than cost/risk; refresh Q after live B rows or new candidate arms. |

### Group 1: Private SDK Levers

Group goal: attack context growth, SDK defaults, skill drift, and wasted turns
without changing default MCP/profile behavior.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| A | accepted | Give the SDK route bounded, auditable access to canonical `molmo-realworld-cleanup` skill context. | Current SDK route names the skill but does not mount/read `SKILL.md` like Codex/Claude workspaces. | Implemented: the SDK instructions receive bounded canonical skill markdown, while artifacts persist only path/hash/size/truncation/token metadata. Focused unit and lint gates pass. | Live A/B is optional but authorized; keep the metadata/privacy guard in future rows. |
| G | accepted-deterministic, live A/B authorized | Expose explicit SDK `ModelSettings` / `RunConfig` performance profiles. | Current runtime relies too much on provider defaults while turns/context remain high. | Implemented: runtime applies explicit SDK settings, disables sensitive trace data in run config, and records sanitized settings in timing/events. Live A/B speed proof is authorized but still requires baseline/candidate evidence. | Continue to AB/I deterministic prep or live A/B when credentials/backend access and recorded caps are available. |
| J | accepted with G for attribution | Record prompt-cache retention and stable-prefix evidence. | Cache behavior can explain or hide speed wins, and some cache levers are Responses-specific. | Implemented: timing/cache summaries carry prompt-cache retention policy and stable-prefix hash; cached vs uncached usage remains unavailable unless span usage exists. | Do not claim cache speedup when usage is unavailable, provider is Chat-only, or prefix changes are untracked. |
| H | bypass-for-now | Use SDK-native session/Responses continuation instead of prompt replay. | Prompt replay can grow context, but compact continuation already fixed the immediate replay issue. | Only reconsider if Q shows continuation replay remains a top context source. | Do not run as next pass; stop if continuation changes task state or hides failure state. |
| I | accepted-deterministic-prep, live row rejected | Add SDK `call_model_input_filter` or equivalent state compaction. | Repeated public tool state is a likely context driver after kickoff compaction. | Implemented: replay/fake-provider proof shows oversized public tool outputs and repeated metric maps can be compacted in model-facing input while reports and traces remain complete. The first `mify` world-public live row reduced model-facing input bytes by `93.9364%` and uncached input tokens by `134793`, but failed to call `done`, raised failed/noop tool count, and got slower, so the current policy is rejected as a speed win. | Do not rerun the same policy unchanged. Next I work needs a behavior-preserving compaction/session change or a tighter gate that keeps `done`, report-quality evidence, and task-state semantics intact while reducing model/SDK latency. |
| L | merge into Q/Y | Audit non-tool responses and turn-count waste. | 72-78 model turns suggests avoidable text-only or deferred-action turns. | Q/Y records non-tool, deferred, noop, and turn-waste counts. | Create a separate fix arm only if waste is material. |
| AB | keep, Responses-only | Add a Responses-native feature audit and A/B arm before broad protocol fallback work. | The SDK route now has both Responses and Chat-compatible directions; speed claims must not mix them. | Decision packet records `wire_api=responses`, enabled Responses-only levers, and shared performance deltas for server-managed continuation/session state, prompt-cache retention/stable prefixes, or related SDK settings. | Stop if provider is Chat-only, SDK state hides MCP-visible task state, artifacts lose trace/report completeness, or privacy gates require raw prompt/tool payload persistence. Chat support is compatibility work unless its own metrics prove speed. |

### Group 2: Lane-Specific Reductions

Group goal: reduce lane-local overhead only after Group 1 and Q identify the
remaining waste. Keep changes SDK-private or opt-in until X passes.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| O | accepted-deterministic-prep, live diagnostic mechanism row accepted, continuation-tightening live row rejected | Collapse deterministic `camera-grounded-labels` observe/label two-step work. | This lane may spend time on deterministic plumbing that can be represented more directly. | Implemented as private opt-in `observe_camera_grounded_candidates`: default public MCP/profile tools stay unchanged, the tool exists only behind `--agent-sdk-camera-grounded-composite-tools`, and deterministic tests prove it returns the existing observe payload plus compact `declare_visual_candidates` output while preserving sub-tool trace events. The first `mify` Responses live diagnostic row kept same-or-better quality and faster observed wall time, but did not exercise the shortcut. The promptfix2 retry did exercise it: 5 `observe_camera_grounded_candidates`, 16 `declare_visual_candidates`, and 19 underlying `observe` substep requests, with same recorded quality and an accepted diagnostic comparison (`-303.142s` wall, `-319.020s` model API, `+50586` uncached input tokens). Direct checker reruns pass for both composite artifacts after the narrow camera-grounded provenance allowlist repair. Continuation tightening then reduced standalone declarations to 0 in the latest live rerun, but that row failed before `done` with `provider_context_budget_exceeded`. | Keep O SDK-private/opt-in. Treat promptfix2 as a valid mechanism/diagnostic speed row, not a normalized or publishable speed claim. Treat continuation tightening as rejected diagnostic evidence: the cadence is fixed, but task completion now depends on behavior-preserving context/session redesign. Stop if evidence semantics blur into raw-FPV, grounding detail is lost, or the tool is promoted beyond SDK-private/opt-in behavior without X. |
| M | defer | Prune irrelevant tools by evidence lane. | Smaller tool surfaces can reduce choice noise, but broad pruning can break valid actions. | Lane-local allowlist keeps all legitimate cleanup actions available. | Try only if Q shows tool-choice noise after G/I/O; keep SDK-private or opt-in. |
| N | accepted-deterministic-prep, live row rejected | Add repeated `metric_map` delta contract. | Re-sending static map state can inflate context. | Implemented in the opt-in SDK model-input filter: first map remains full, repeated maps can become hash/size/count summaries only when smaller, and full map responses remain in traces/reports. The first live compaction row recorded `metric_map_output_count=292` and `repeated_metric_map_output_count=208`, but `metric_map_bytes_reduced=0` and cleanup behavior regressed. | Do not claim an N speedup. Revisit only if the repeated-map summary can actually reduce map bytes and preserve cleanup behavior, or after D/C clarifies provider tail latency. |
| F | accepted-deterministic-prep, live row rejected | Reduce or reuse report-only visual capture. | Visual capture is a material wall-clock bucket independent of model speed: live-refresh rows show `93.256s`/`28.81%` for world-public and `156.962s`/`18.37%` for camera-grounded. | Implemented as private opt-in `robot_view_capture_policy=action_timeline`: default `full` behavior is unchanged; the policy skips report-only `observe` / `scene_objects` robot-view captures while preserving before/after views, cleanup action views, raw-FPV observe artifact capture, traces, and reports. Focused server and live-runner tests prove the policy and flag forwarding. The completed `mify` world-public live row reduced `robot_view_capture_s` from `93.256s` to `54.975s`, but quality regressed from `4/5` restored to `3/5` and wall/model time increased by `+181.786s`/`+216.535s`, so the row is rejected as a speed win. | Keep SDK-private/opt-in. Do not rerun F as the next standalone arm; only revisit with paired/repeated evidence or a lane where same-or-better quality is preserved. |

### Group 3: Raw-FPV Stabilization

Group goal: make raw-FPV bounded and informative before raising budgets,
racing, or attempting cleanup-pass claims.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| P | accepted-deterministic-prep, live blocked | Add raw-FPV visual-candidate failure rails. | Raw-FPV repeats unresolved visual searches and needs actionable terminal reasons. | Implemented: `raw_fpv_repeated_failure_limit` classifies repeated compact visual-candidate failure fingerprints as `raw_fpv_repeated_candidate_failure`, records aggregate terminal details in timing/latency attribution, and preserves raw prompt/tool-payload privacy. The first live gate attempt is blocked before raw-FPV behavior evidence: `mify` has unverified image transport and two `codex-env` attempts failed with `provider_transient_failure` / `upstream_unavailable` before task work. | Retry only after `codex-env` upstream availability recovers or another OpenAI Agents SDK provider has verified image transport. Cleanup-pass or speed claims still require report-quality evidence. Stop on unclassified provider failure, context breach, or pressure to persist full image/tool payloads. |
| AA | accepted-deterministic-prep, live blocked | Add raw-FPV image-memory and multiresolution policy. | Replaying stale full-frame images consumes context without improving cleanup. | Implemented as private SDK model-facing image memory: `raw_fpv_budgeted_v1` keeps the latest full raw-FPV frame, summarizes older image blocks only when smaller, and records aggregate retained/evicted counts plus byte deltas while MCP/report artifacts remain complete. The first live gate attempt produced no image-memory behavior evidence because provider failure occurred before raw-FPV observations. Multiresolution thumbnails/crops remain future work if live evidence shows they are needed. | Retry only after a verified-image-transport provider can complete task work. Cleanup-pass or speed claims still require report-quality evidence. Stop if raw-FPV is relabeled as camera-grounded evidence, visual proof disappears, or summaries need raw image bytes/tool payload bodies in persisted events. |

### Group 4: Expensive Orchestration

Group goal: use racing or parallelism only when fresh evidence proves the
latency target is worth the extra cost and risk.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| D | accepted-deterministic-prep, C prerequisite | Add per-arm racing observability. | Racing can look faster while hiding loser-arm work; even when token cost is not a decision objective, normalized wall-clock claims need winner/loser timing and cancellation evidence. | Implemented: each SDK model call records sanitized lifecycle events, stable call/arm ids, elapsed time, winner/cancel flags, failure class, provider/model/wire axes, aggregate token usage availability, loser-billing-unknown fields, and aggregate `model_racing_observability_metrics` in `live_timing.json` latency attribution. Single-arm/no-racing remains the default. | Keep D events mandatory for any C row. |
| C | accepted-deterministic-prep, live row rejected | Race individual SDK `get_response` model calls. | The dominant bucket is still model/SDK between-tool gap, and token cost is not a deciding objective, so provider tail-latency racing is a plausible wall-clock arm once attribution exists. | Implemented behind `--model-racing` / `ROBOCLAWS_OPENAI_AGENTS_MODEL_RACING`, default off. First successful SDK model response wins and enters history; pending losers are cancelled/recorded; all-arm failure preserves retry/failure semantics; `stream_response` remains single-arm. The scoped `mify` Responses live row proves the racing mechanism and D telemetry, but rejects the current policy as a speed win because cleanup quality regressed (`4/5` restored to `3/5`) despite observed wall improvement (`-260.987s`). | Do not rerun the same C policy unchanged. Revisit only with behavior-preserving controls, paired/repeated evidence that restores same-or-better quality, or a narrower lane where racing does not change cleanup behavior. |
| K | bypass-for-now | Audit parallel tool-call policy. | Robot actions are stateful and serial; parallelism is risky. | Policy distinguishes safe read-only tools from stateful actions. | Revisit only for read-only tools if G exposes provider parallelism benefit. |
| E | bypass-for-now | Consider broad agent-visible state delta/compaction. | E is an umbrella for I/N/AA and risks public contract drift. | SDK-private or opt-in deltas reduce repeated state while preserving complete trace/report evidence. | Use I, N, and AA first; revive E only if concrete arms are insufficient. |

### Group 4.5: Context-Growth Follow-up

Group goal: make the O camera-grounded mechanism complete again after cadence
tightening exposed provider context growth as the blocker. These arms are
private SDK model-input/session levers and must preserve `done`, `run_result`,
task-state semantics, and complete trace/report artifacts.

| ID | Queue | Do | Why | Success | Stop / next |
| --- | --- | --- | --- | --- | --- |
| AC | accepted-deterministic-prep, live paired rows accepted, calibrated-diagnostic comparison generated | Add completion-safe camera-grounded history compaction. | O continuation tightening removed standalone declarations but failed before completion on context budget. The rejected I/N policy compacted too broadly and broke task completion; AC narrows compaction to old camera-grounded observation/declaration history while retaining recent actionable outputs. | Implemented as `camera_grounded_history_v1` inside the private SDK model-input filter. It is off by default, can be enabled through `--camera-grounded-history-compaction` / `ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_HISTORY_COMPACTION`, keeps the latest N camera-grounded outputs full, summarizes older outputs only when smaller, records aggregate camera-grounded byte/count metrics, and preserves complete MCP traces/reports/run artifacts. The fixed4 and repeat rows completed with `done`, `run_result.json`, same-or-better quality, and paired wall improvements of `-659.477s` / `-630.633s`. The explicit diagnostic calibration packet from 193 model-call rows adds normalized comparison fields: estimated model-work increases while model-latency residual falls by `-817.37s` / `-957.061s`. | Keep AC SDK-private/opt-in. Treat calibrated output as diagnostic because the coefficient packet is a simple two-feature fit without reviewed error statistics. Next proof is broader B baseline coverage or a reviewed calibration dataset before broad/publishable claims. |

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
- `blocked`: needs credentials, backend slot, provider access, network-policy
  clearance, run-cap feasibility, or a design decision. Lack of additional
  per-run human approval is not a blocker for this plan.
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

### Decision Rows

| Candidate ids | Row | Feature flags / dependencies | Evidence | Decision | Queue decision reason | Next recommended group |
| --- | --- | --- | --- | --- | --- | --- |
| A | `openai-agents-live`, provider/evidence lane agnostic deterministic proof | `agent_sdk_skill_context=canonical_skill_markdown`, no live provider call, no public MCP/profile change | `roboclaws/agents/drivers/openai_agents_live.py`, `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`, `roboclaws/agents/live_runtime.py`, `tests/unit/agents/test_live_runtime.py`; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`; `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py` | accepted | Deterministic proof shows the SDK route receives the canonical skill text, artifact discovery includes `openai-agents-skill-context.json`, and persisted timing/event/artifact summaries omit the skill body and raw prompt/tool payloads. No speed claim is made from this row. | G/J settings and cache attribution, then AB only for `wire_api=responses` rows. |
| G,J | `openai-agents-live`, provider/evidence lane agnostic deterministic settings attribution | `sdk_model_settings`, `sdk_run_config`, `prompt_cache_retention`, `stable_prefix_hash`; no live provider call, no public MCP/profile change | `roboclaws/agents/drivers/openai_agents_live.py`, `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`, `tests/unit/agents/test_live_runtime.py`; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`; `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py`; `.venv/bin/ruff format --check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py` | accepted-deterministic, live A/B authorized | Deterministic proof shows explicit SDK model/run settings are constructed and passed into Agent/Runner, sanitized runtime events expose those settings, cache summaries record retention and stable-prefix hash, and missing usage remains unavailable rather than zero. No speedup claim is made without live baseline/candidate rows. | AB/I deterministic prep, then provider-backed A/B under the standing authorization once credentials/backend availability, network guard, and recorded run caps pass. |
| I,AB | `openai-agents-live`, deterministic compaction prep plus `mify` Responses `world-public-labels` live row | `model_input_compaction=public_tool_result_summary_v1+repeated_metric_map_delta_v1` opt-in, `agent_sdk_responses_features`, no public MCP/profile change | Deterministic prep evidence above; live baseline `output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`; input-compaction candidate `output/agent-sdk-perf-followups/mify-world-public-mimo-compact-input-compaction/0612_1327/seed-7/`; comparison `output/agent-sdk-perf-followups/mify-world-public-input-compaction-comparison-diagnostic.json`; refresh row `mify_world_public_input_compaction_refresh` in `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`. | accepted-deterministic-prep, live row rejected | Deterministic proof shows the SDK route can install `RunConfig.call_model_input_filter`, keep the feature off by default, compact oversized public tool outputs before model calls with aggregate byte-delta events, and record Responses continuation/session capability as gated metadata. The live row proves the model-facing hook is active (`input_byte_reduction_ratio=0.939364`, uncached input tokens `197838` to `63045`) but rejects the current policy as a wall-clock win because it failed before `done`, produced no `run_result.json`, raised failed/noop calls to `31`, and increased observed wall/model time by `+62.627s` / `+102.956s`. | Do not rerun the same compaction policy unchanged. Any next compaction/session arm must preserve behavior and task-state completeness before it can support a wall-clock claim. |
| N | `openai-agents-live`, deterministic repeated-map delta prep plus `mify` Responses `world-public-labels` live row | `model_input_compaction=public_tool_result_summary_v1+repeated_metric_map_delta_v1` opt-in, no public MCP/profile change | Deterministic prep evidence above; live input-compaction row `output/agent-sdk-perf-followups/mify-world-public-mimo-compact-input-compaction/0612_1327/seed-7/`; comparison `output/agent-sdk-perf-followups/mify-world-public-input-compaction-comparison-diagnostic.json`. | accepted-deterministic-prep, live row rejected | Deterministic proof shows repeated `metric_map` outputs can be summarized in model-facing SDK input with original hash, size, map id/version/mode, waypoint counts, and runtime-object/candidate counts, only when the summary is smaller. The live row recorded `metric_map_output_count=292` and `repeated_metric_map_output_count=208`, but `metric_map_bytes_reduced=0`; behavior regressed and the row failed before `done`. | Do not claim an N speedup. Revisit only if repeated-map summaries actually reduce map bytes and preserve cleanup behavior inside a redesigned compaction/session arm. |
| D | `openai-agents-live`, provider/evidence lane agnostic deterministic racing-observability prep | `model_racing_observability=per_arm_observability_v1`, single-arm/no-racing, no public MCP/profile change | `roboclaws/agents/drivers/openai_agents_live.py`, `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`, `tests/unit/agents/test_live_runtime.py`; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`; `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py` | accepted-deterministic-prep, C prerequisite satisfied | Deterministic proof shows SDK model calls now emit sanitized single-arm lifecycle events with stable call/arm ids, elapsed time, winner/cancel flags, failure class, provider/model/wire axes, token usage availability, and loser-billing-unknown fields. The runner aggregates these into `model_racing_observability_metrics` in `live_timing.json` timeline latency attribution. The completed C live row preserved D telemetry for both the single-arm baseline and two-arm candidate. | Keep D events mandatory for any future racing variant. |
| C | `openai-agents-live`, provider/evidence lane agnostic deterministic get-response racing prep plus `mify` Responses `world-public-labels` live row | `model_racing=get_response_racing_v1` opt-in through `--model-racing` / `ROBOCLAWS_OPENAI_AGENTS_MODEL_RACING`, arm count 2, default off, no public MCP/profile change | Deterministic prep evidence above; live caps `docs/status/active/agent-sdk-c-racing-live-caps.json`; baseline `output/agent-sdk-perf-followups/c-racing-baseline/0612_1429/seed-7/`; candidate `output/agent-sdk-perf-followups/c-racing-candidate/0612_1448/seed-7/`; comparison `output/agent-sdk-perf-followups/c-racing-comparison-diagnostic.json`; refresh row `mify_world_public_c_racing_refresh` in `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`. | accepted-deterministic-prep, live row rejected | Deterministic proof shows SDK `get_response` calls can race two or more same-provider arms, return the first successful SDK model response, cancel pending losers, record winner/cancel/failure usage-availability telemetry through D, and keep raw prompts/model text/tool payload bodies out of events. The live row proves the mechanism (`racing_enabled=true`, `racing_multiplier=2.0`, 53 raced calls, 106 arms, 76 winners, 75 cancelled losers) and reduced observed wall time by `-260.987s`, but rejects the policy because behavior quality regressed (`completion_status=success` to `partial_success`, `restored_count=4` to `3`). Observed model API time rose by `+397.292s`, so normalized/publishable claims remain unavailable. | Do not claim a C speedup. Do not rerun the same racing policy unchanged; prefer behavior-preserving compaction/session redesign, O paired/tightening evidence, raw-FPV P/AA live rows, or broader B baselines before another C variant. |
| O | `openai-agents-live`, `mify` Responses `camera-grounded-labels` live diagnostic plus promptfix2 retry and continuation tightening | `camera_grounded_composite_tools=observe_camera_grounded_candidates` opt-in, registered only by `--agent-sdk-camera-grounded-composite-tools`, no default public MCP/profile change | Deterministic prep evidence above; baseline `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-baseline/0612_1012/seed-7/`; inconclusive first composite row `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite/0612_1032/seed-7/`; valid mechanism retry `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-promptfix2/0612_1126/seed-7/`; rejected continuation-tightening row `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-continuation-tightening/0612_1627/seed-7/`; metrics `output/agent-sdk-perf-followups/mify-camera-grounded-baseline-metrics.json`, `output/agent-sdk-perf-followups/mify-camera-grounded-composite-metrics.json`, `output/agent-sdk-perf-followups/mify-camera-grounded-composite-promptfix2-metrics.json`, and `output/agent-sdk-perf-followups/mify-camera-grounded-composite-continuation-tightening-metrics.json`; comparisons `output/agent-sdk-perf-followups/mify-camera-grounded-composite-comparison.json`, `output/agent-sdk-perf-followups/mify-camera-grounded-composite-promptfix2-comparison.json`, and `output/agent-sdk-perf-followups/mify-camera-grounded-composite-continuation-tightening-comparison-diagnostic.json`; direct checker reruns for completed composite artifacts; focused tests for prompt rendering, stale prompt rerender, checker provenance, and composite compact-continuation guidance. | accepted-diagnostic-mechanism-row, continuation-tightening row rejected, not normalized/publishable speed claim | The first composite row had same-or-better recorded quality and faster wall/model API time, but it did not call the intended shortcut. The promptfix2 retry did: 5 `observe_camera_grounded_candidates`, 16 `declare_visual_candidates`, and 19 underlying `observe` substep requests. It preserved quality (`completion_status=success`, `restored_count=4/5`, `semantic_accepted_count=5/5`, `sweep_coverage_rate=1.0`, `disturbance_count=0`) and the shared diagnostic comparison accepted the row with `-303.142s` observed wall and `-319.020s` observed model API time, while uncached input tokens rose by `+50586`. Trace review showed 11 standalone declarations after SDK continuation; the tightened continuation prompt removed that residual in the latest live row (`14` composite calls, `14` composite-internal declarations, `0` standalone declarations), but the row failed before `done` with `provider_context_budget_exceeded` (`175618` current input tokens over the `96000` hard limit). | Keep O SDK-private/opt-in. Do not rerun O unchanged. Next O evidence should follow a behavior-preserving context/session redesign; default/public promotion still requires X cross-client proof and normalized/publishable speed claims still require calibrated/repeated evidence. |
| F | `openai-agents-live`, deterministic robot-view capture prep plus `mify` Responses `world-public-labels` live A/B | `robot_view_capture_policy=action_timeline` opt-in, forwarded to cleanup server only when explicitly requested, no default public MCP/profile change | Deterministic prep evidence above; live baseline `output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`; action-timeline candidate `output/agent-sdk-perf-followups/mify-world-public-mimo-compact-action-timeline/0612_1303/seed-7/`; comparison `output/agent-sdk-perf-followups/mify-world-public-action-timeline-comparison-diagnostic.json`; refresh row `mify_world_public_f_action_timeline_refresh` in `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`. | accepted-deterministic-prep, live row rejected | Deterministic proof shows the server defaults to full robot-view capture, but `action_timeline` skips report-only `observe` / `scene_objects` captures while preserving raw-FPV observe artifact capture and cleanup action captures. The live runner records the policy under `agent_sdk_perf_profile.robot_view_capture_policy`, mirrors it in `live_timing.json`, and forwards `--robot-view-capture-policy action_timeline` to the cleanup server only for opt-in SDK runs. The live row proves the mechanism can reduce visual capture time (`93.256s` to `54.975s`) but rejects it as a speed win because quality regressed (`4/5` restored to `3/5`; `success` to `partial_success`) and observed wall/model time increased (`+181.786s` / `+216.535s`). | Keep F SDK-private/opt-in. Do not run another standalone F row next; revisit only with paired/repeated evidence or a lane where same-or-better quality is preserved. |
| P | `openai-agents-live`, `camera-raw-fpv` deterministic repeated-failure rail prep plus blocked live gate attempts | `raw_fpv_repeated_failure_limit=3` in `raw_fpv_budgeted_v1`, optional `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_REPEATED_FAILURE_LIMIT` override, no public MCP/profile change | Deterministic prep evidence above; live caps `docs/status/active/agent-sdk-raw-fpv-live-caps.json`; blocked `mify` image-transport gate; failed `codex-env` attempts `output/agent-sdk-perf-followups/raw-fpv-budgeted-codex/0612_1512/seed-7/` and `output/agent-sdk-perf-followups/raw-fpv-budgeted-codex-retry/0612_1514/seed-7/`. | accepted-deterministic-prep, live blocked | Deterministic proof shows repeated unresolved `navigate_to_visual_candidate` failures produce `raw_fpv_repeated_candidate_failure` before context-window failure, with compact fingerprint fields and aggregate terminal counts in `agent_sdk_budget_terminal` / latency attribution. Persisted detail excludes raw prompts, model text, full image-region payloads, full tool payload bodies, credentials, and private truth. Live attempts did not reach raw-FPV task work: `mify` is blocked by unverified image transport, and two `codex-env` attempts hit `provider_transient_failure` / `upstream_unavailable` before tool calls beyond initial setup. | Retry only after provider availability or verified image transport changes. Any cleanup-pass or speed claim still needs report-quality evidence. |
| AA | `openai-agents-live`, `camera-raw-fpv` deterministic image-memory prep plus blocked live gate attempts | `raw_fpv_image_memory_v1` in the SDK model-input filter, default enabled only by `raw_fpv_budgeted_v1`, optional `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_IMAGE_MEMORY` and retain-count override, no public MCP/profile change | Deterministic prep evidence above; live caps `docs/status/active/agent-sdk-raw-fpv-live-caps.json`; blocked `mify` image-transport gate; failed `codex-env` attempts `output/agent-sdk-perf-followups/raw-fpv-budgeted-codex/0612_1512/seed-7/` and `output/agent-sdk-perf-followups/raw-fpv-budgeted-codex-retry/0612_1514/seed-7/`. | accepted-deterministic-prep, live blocked | Deterministic proof shows older raw-FPV image blocks can be summarized before SDK model calls while the latest full image remains model-visible, summaries store only observation id, sizes, hashes, and retention policy, and `model_input_filter_metrics` / timeline attribution aggregate retained/evicted counts and byte deltas. The MCP raw-FPV observe contract still returns compact state plus a full PNG image block, and report artifacts remain complete. Live attempts did not reach raw-FPV observations, so image-memory behavior remains unmeasured live. | Retry only after provider availability or verified image transport changes. Multiresolution thumbnail/crop policy is parked until live evidence shows retained full-frame policy is insufficient. |
| AC | `openai-agents-live`, deterministic camera-grounded history compaction prep plus `mify` Responses O+AC live rows and calibrated diagnostic comparison | `model_input_compaction=camera_grounded_history_v1` opt-in through `--camera-grounded-history-compaction` / `ROBOCLAWS_OPENAI_AGENTS_CAMERA_GROUNDED_HISTORY_COMPACTION`, explicit `--calibration` report-analysis packet, no public MCP/profile change | Deterministic prep evidence above; fixed4 caps `docs/status/active/agent-sdk-o-ac-camera-grounded-live-caps.json`; fixed4 candidate `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-ac-fixed4/0612_1841/seed-7/`; fixed4 comparison `output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-fixed4-comparison.json`; fixed4 normalized comparison `output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-fixed4-normalized-comparison.json`; repeat caps `docs/status/active/agent-sdk-o-ac-camera-grounded-repeat-live-caps.json`; repeat candidate `output/agent-sdk-perf-followups/mify-camera-grounded-mimo-compact-composite-ac-repeat-mify/0612_1909/seed-7/`; repeat comparison `output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-repeat-mify-comparison.json`; repeat normalized comparison `output/agent-sdk-perf-followups/mify-camera-grounded-composite-ac-repeat-mify-normalized-comparison.json`; calibration `output/agent-sdk-perf-followups/mify-camera-grounded-o-ac-calibration.json`; refresh rows `mify_camera_grounded_o_ac_fixed4_refresh` and `mify_camera_grounded_o_ac_repeat_refresh` in `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`; `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-live-refresh-matrix.json --dry-run`; `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-live-refresh-matrix.json --offline-preflight --decision-packet output/agent-sdk-perf-followups/live-refresh-decision.json`; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/reports/test_live_performance.py`; `.venv/bin/ruff check roboclaws/reports/live_performance.py scripts/reports/extract_live_report_metrics.py scripts/reports/compare_live_report_metrics.py tests/unit/reports/test_live_performance.py` | accepted-deterministic-prep, live paired rows accepted, calibrated-diagnostic only | Deterministic proof shows the SDK model-input filter can retain the latest camera-grounded outputs while replacing older `observe_camera_grounded_candidates` / camera-model `declare_visual_candidates` / camera-policy `observe` outputs with hash/observation/candidate summaries only when smaller. The fixed4 live row preserved `done`, `run_result.json`, and same-or-better cleanup quality (`completion_status=success`, `restored_count=4/5`, `semantic_accepted_count=5/5`, `disturbance_count=0`) while reducing observed wall/model API/between-tool gap by `-659.477s` / `-653.563s` / `-638.809s`. The repeat row preserved the same quality gates and reduced observed wall/model API/between-tool gap by `-630.633s` / `-619.022s` / `-612.38s`. The explicit 193-row diagnostic calibration leaves quality accepted and shows estimated model-work increasing (`+163.807s` fixed4, `+338.039s` repeat) while model-latency residual falls (`-817.37s`, `-957.061s`), so the normalized interpretation is residual/wait reduction rather than less calibrated model work. | Keep O+AC SDK-private/opt-in and refresh Q/Y from both rows. Next recommended work is scoped B baseline coverage; broad/publishable claims still need provider/lane coverage and a reviewed calibration dataset with error statistics. |
| B,I/AB | `openai-agents-live`, `mify` Responses `world-public-labels` live baseline vs `mimo_compact_v1` candidate | Baseline profile versus `mimo_compact_v1`; same provider profile, wire API, model, evidence lane, seed, map bundle, backend, and run caps. No public MCP/profile change. | `output/agent-sdk-perf-followups/mify-world-public-baseline/0612_0814/seed-7/`; `output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7/`; `output/agent-sdk-perf-followups/mify-world-public-comparison-diagnostic.json`; `output/agent-sdk-perf-followups/mify-world-public-comparison.json`; `.venv/bin/python scripts/reports/extract_live_report_metrics.py --write-model-call-metrics <run-dir>` for both rows; `.venv/bin/python scripts/reports/compare_live_report_metrics.py --baseline-run-dir output/agent-sdk-perf-followups/mify-world-public-baseline/0612_0814/seed-7 --candidate-run-dir output/agent-sdk-perf-followups/mify-world-public-mimo-compact/0612_0820/seed-7 --diagnostic --output output/agent-sdk-perf-followups/mify-world-public-comparison-diagnostic.json`; `./scripts/dev/run_pytest_standalone.sh -q tests/unit/reports/test_live_performance.py`; `.venv/bin/ruff check roboclaws/reports/live_performance.py tests/unit/reports/test_live_performance.py` | diagnostic, no speed win | Both live rows finished and produced reports. Candidate quality was not worse after capping sweep over-coverage at required full coverage, and candidate reduced model/MCP calls by 2 each, but it was slower: +5.746s observed wall, +8.749s observed model API, and +7033 uncached input tokens. Treat this as evidence against claiming a `mimo_compact_v1` world-public speedup on this single row; it does not reject the deterministic prep. | Refresh Q/Y with this live packet before choosing the next arm. Prefer camera-grounded Candidate O live A/B or raw-FPV diagnostic rows if Q/Y still rank Group 2/3; retry GPT `codex-env` only after the transient 502 gate clears. |
| Q,Y | Group 0 deterministic recommendation packet plus completed-live refresh | `reducible_bucket_report.latency_buckets`, `dominant_bucket`, `recommendation_summary`, `expected_decision_status` for known rejected evidence rows, no live provider call, no public MCP/profile change | `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`, `tests/unit/molmo_cleanup/test_agent_sdk_perf_matrix.py`; `docs/status/active/agent-sdk-speedup-foundation-matrix.json`; `docs/status/active/agent-sdk-speedup-live-refresh-matrix.json`; `output/agent-sdk-speedup-foundation/decision.json`; `output/agent-sdk-perf-followups/live-refresh-decision.json`; `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-foundation-matrix.json --offline-preflight --decision-packet output/agent-sdk-speedup-foundation/decision.json`; `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-live-refresh-matrix.json --offline-preflight --decision-packet output/agent-sdk-perf-followups/live-refresh-decision.json`; `.venv/bin/python scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py --manifest docs/status/active/agent-sdk-speedup-live-refresh-matrix.json --dry-run` | accepted-deterministic-enrichment, refreshed-with-live-packet, live rows authorized | Deterministic proof shows the packet can rank candidate ids/groups from shared performance summaries, preserve unsupported rows, classify dominant buckets, preserve known rejected evidence rows without turning the refresh command into an infrastructure failure, and keep recommendation claims scoped to diagnostic evidence. The live-refresh packet now accepts the completed `mify` Responses world-public pair, O promptfix2 mechanism row, and O+AC fixed4 plus repeat paired rows, and keeps F action-timeline, I/N input-compaction, C racing, and O continuation-tightening rows as expected-rejected evidence. The two O+AC rows are the current best paired wall-clock result, and explicit calibrated-diagnostic report comparisons are now available; they show residual/wait reduction under a simple two-feature calibration, not reduced estimated model work. Token deltas are telemetry only under the current maintainer priority. | Next recommended arms: scoped B baseline coverage first, reviewed calibration governance second, and raw-FPV P/AA retry only after provider/image-transport availability changes. Do not rerun the rejected F, I/N, C, or O-tightening policies unchanged. |

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

Provider-backed live rows are authorized for this plan. They do not require
additional per-run human approval, but each run must satisfy and record the
checklist below.

## Run-Cap Gate For Live Runs

Before any provider-backed run, record:

- planned max live runs;
- planned max wall-clock;
- context hard limits;
- model/candidate concurrency;
- racing multiplier, if any;
- provider credentials available;
- backend slot available;
- `just dev::network-status` result;
- expected cost/budget cap under this standing authorization.

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

---
plan_scope: live-agent-runtime-sdk-spike
status: DONE
source:
  - 2026-06-08 SDK deep research discussion
  - intuitive-reduce-entropy
  - inline intuitive-planning-loop
  - intuitive-preflight
last_reviewed: 2026-06-09
---

# Live Agent Runtime SDK Spike

## Status

DONE

Completed on 2026-06-09. Roboclaws now has a provider-neutral
`LiveAgentRuntime` contract and a private/non-default `openai-agents-live`
household cleanup route that runs through the existing MCP server, `done`
handoff, checker, and report boundary. Existing public `codex` and `claude`
household cleanup routes remain unchanged.

Live proof:

- Command:
  `just molmo::cleanup openai-agents-live smoke 7 output/household/household-cleanup/openai-agents-smoke-128 '帮我收拾这个房间' 5 127.0.0.1 18788`
- Artifact:
  `output/household/household-cleanup/openai-agents-smoke-128/0609_1052/seed-7/`
- Result: `live_status.json` finished with exit status 0; checker passed;
  `report.html` was generated; `run_result.json` restored 5/5 targets with
  sweep coverage `1.0`; `openai-agents-events.jsonl` and
  `openai-agents-trace.json` were written.

## Decision Summary

Roboclaws should not treat OpenAI Agents SDK, Anthropic Claude Agent SDK, and Pi
SDK as symmetric replacements for the existing Codex and Claude Code live
routes.

The recommended direction is:

1. Keep the current Docker-backed `codex-live` and `claude-live` CLI routes as
   product/coding-agent baselines.
2. Define a Roboclaws-owned `LiveAgentRuntime` contract at the driver layer.
3. Add one experimental SDK runtime first: `openai-agents-live`, and stop only
   when it can actually run a household cleanup job end-to-end through the
   existing MCP server/checker/report boundary.
4. Keep Anthropic Claude Agent SDK as a conditional second spike only if the
   Claude route needs SDK-level session/control improvements.
5. Park Pi SDK until the goal explicitly becomes an open provider-agnostic
   coding-agent harness with a Roboclaws MCP adapter.

This plan is about the live-agent runtime layer only. It must not move cleanup
strategy into launchers, change the MCP capability contract, or replace the
current public `just task::run household-cleanup codex|claude ...` baselines.

## Current Repo Boundary

The current live-agent boundary is intentionally narrow:

- Live runners launch one coding-agent turn, collect artifacts/status, own
  locks/processes/checker execution, and then stop.
- `done` remains the authoritative cleanup completion gate.
- Provider-transient failures are retryable infrastructure failures, not normal
  cleanup continuation.
- Idle timeout, tool-binding, context, auth, config, MCP namespace, and
  unclassified CLI failures are explicit non-retryable live-run failures.

Source: `docs/plans/refactor-live-agent-runner-boundary.md`.

Current implementation evidence:

- `scripts/molmo_cleanup/run_live_codex_cleanup.py` prepares an isolated task
  workspace, registers the cleanup MCP server with Codex CLI, launches
  `codex exec --json`, writes Codex artifacts, classifies failures, and runs the
  checker.
- `scripts/molmo_cleanup/run_live_claude_cleanup.py` prepares an isolated task
  workspace, writes a Claude MCP config, launches `claude -p --output-format
  stream-json`, classifies failures, and runs the checker.
- `roboclaws/agents/live_status.py` already normalizes provider, tool-binding,
  idle, context, config, and generic CLI failure reasons.
- `scripts/dev/coding_agent_env.sh` owns current coding-agent provider defaults
  and key/base-url routing.

## SDK Fit

### OpenAI Agents SDK

Best fit for a first Roboclaws SDK spike.

Evidence from official docs:

- Python agent runtime with agents, tools, handoffs, guardrails, tracing, and
  result/event streaming.
- MCP integration is a first-class documented feature.
- Sessions provide built-in conversation memory and let callers avoid manual
  full-history plumbing.
- Tracing is first-class and could improve report/debug artifacts.
- Model provider support includes OpenAI plus extension paths such as LiteLLM
  and Any-LLM provider integration.
- Sandbox Agents are relevant to coding-agent style work, but they are a
  separate beta surface and must not be assumed to equal Codex CLI behavior.

Primary sources:

- https://openai.github.io/openai-agents-python/
- https://openai.github.io/openai-agents-python/mcp/
- https://openai.github.io/openai-agents-python/sessions/
- https://openai.github.io/openai-agents-python/tracing/
- https://openai.github.io/openai-agents-python/models/
- https://openai.github.io/openai-agents-python/sandbox_agents/

Roboclaws interpretation:

- Use it to test whether Python-native session/context/tracing control gives
  better runtime observability and failure handling for MCP-driven robot tasks.
- Do not market it as "Codex SDK" and do not assume it preserves Codex CLI
  product behavior.

### Anthropic Claude Agent SDK

Best fit if Roboclaws decides the Claude live route needs a structured
replacement for `claude -p`.

Evidence from official docs:

- Python and TypeScript SDKs expose Claude Code agent sessions through
  `query()` and client-style APIs.
- Session management supports continuation/forking patterns.
- MCP configuration, permissions, and hooks are documented.
- Rate-limit events and structured SDK messages can improve status handling.

Primary sources:

- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/agent-sdk/python
- https://code.claude.com/docs/en/agent-sdk/sessions
- https://code.claude.com/docs/en/agent-sdk/mcp
- https://code.claude.com/docs/en/agent-sdk/permissions
- https://code.claude.com/docs/en/agent-sdk/hooks

Roboclaws interpretation:

- This is closer to "Claude Code as a library" than OpenAI Agents SDK is to
  Codex CLI.
- It should not define the shared runtime abstraction because it is
  Claude-route-specific.

### Pi SDK

Pi SDK here means Earendil Works Pi Coding Agent SDK, not Pydantic AI.

Best fit for a later provider-agnostic coding-agent harness experiment.

Evidence from official docs:

- Node/TypeScript package `@earendil-works/pi-coding-agent`.
- SDK supports creating agent sessions and working with session trees.
- Providers, extensions, RPC, and JSONL-style process interaction are documented.
- Current docs do not present MCP as a native first-class integration surface;
  Roboclaws would need an adapter from the existing MCP server/tools to Pi
  extension/tool semantics.

Primary sources:

- https://pi.dev/docs/latest/sdk
- https://pi.dev/docs/latest/rpc
- https://pi.dev/docs/latest/providers
- https://pi.dev/docs/latest/extensions
- https://pi.dev/docs/latest/session-format

Roboclaws interpretation:

- Pi is strategically interesting if the goal becomes an open coding-agent
  harness independent of Codex/Claude products.
- It is not the lowest-risk first SDK spike for Roboclaws because the current
  robot capability surface is MCP-first and Python-first.

## Inline Planning Loop

### Charter

Goal:

- Turn the SDK comparison into one executable Roboclaws plan for the live-agent
  runtime layer.

Non-goals:

- No production live-runner behavior changes in the planning step.
- No replacement of existing Codex or Claude CLI routes.
- No full dual-SDK support in the first implementation slice.
- No Pi SDK integration until a Roboclaws MCP-to-Pi adapter is explicitly
  scoped.
- No paid, live-provider, Docker, GPU, simulator, or hardware validation unless
  separately approved.

Context inspected:

- Root orientation docs: `README.md`, `ARCHITECTURE.md`, `STATUS.md`,
  `AGENTS.md`, `CLAUDE.md`.
- Current live-runner plan:
  `docs/plans/refactor-live-agent-runner-boundary.md`.
- Current live runner and status files:
  `scripts/molmo_cleanup/run_live_codex_cleanup.py`,
  `scripts/molmo_cleanup/run_live_claude_cleanup.py`,
  `roboclaws/agents/live_status.py`,
  `roboclaws/agents/drivers/household_live.py`,
  `scripts/dev/coding_agent_env.sh`.
- Official SDK docs listed above.

Allowed actions:

- Main-session read-only planning plus this plan/preflight document.

User-review gates:

- Adding new runtime dependencies to `pyproject.toml`.
- Exposing a new public `just task::run ...` driver.
- Running live providers or credentialed smoke tests.
- Replacing or removing current Codex/Claude CLI baselines.

Stop when:

- One first implementation slice has clear scope, non-goals, acceptance
  criteria, verification, and stop gates.

### Entropy Scout Result

Accepted:

- Define `LiveAgentRuntime` before adding SDK-specific task logic.
- Spike OpenAI Agents SDK first because Roboclaws is Python-first and MCP-first.

Merged:

- Session/context/rate-limit concerns belong in the runtime contract and
  normalized result/status surface, not in task strategy or cleanup runners.

Parked:

- Anthropic Claude Agent SDK replacement for `claude -p`.
- Pi SDK provider-agnostic harness and MCP adapter proof.
- Operator-console UX for provider rate-limit retries.

Rejected:

- Directly replacing Codex CLI with OpenAI Agents SDK. It is a different
  product/runtime surface.
- Supporting OpenAI and Anthropic SDKs equally in the first slice.
- Treating Pi SDK as a drop-in MCP runtime.

### Grill Result

Recommended defaults:

- The initial runtime contract should be provider-neutral and task-neutral.
- The first SDK implementation should be experimental and not replace the public
  `codex` or `claude` drivers.
- Keep the existing one-turn runner invariant unless an explicit agent-owned
  checkpoint/handoff protocol is introduced later.
- Preserve `live_status.json`, event stream artifacts, `run_result.json`, and
  checker output as the stable downstream surface.
- Treat SDK tracing/session identifiers as additional artifacts, not as cleanup
  completion signals.

Implementation defaults:

- Prefer a Python protocol/dataclass contract under `roboclaws/agents/`.
- Keep provider transient classification shared through
  `roboclaws/agents/live_status.py`.
- Put SDK-specific code under `roboclaws/agents/drivers/`, not under household
  domain logic.
- Add unit/contract tests before any live provider run.

User-review decisions:

- Whether to install the OpenAI Agents SDK as a normal dependency or an optional
  extra.
- Whether to expose `openai-agents-live` through public `just task::run` or keep
  it as a private maintainer route until a local proof passes.
- Whether live OpenAI provider validation is authorized after mock/contract
  tests pass.

Stop gates:

- Stop if the SDK cannot connect to the existing MCP server without changing
  the MCP capability contract.
- Stop if the SDK driver requires cleanup strategy changes outside the skill.
- Stop if provider/session state cannot be represented in normalized
  `LiveAgentResult` and `live_status.json`.

### Model And Interface Target

The first OpenAI Agents SDK cleanup route should use the SDK's Responses model
path, not Chat Completions, because the current repo's Codex-compatible
profiles already classify `codex-env` and `mify` as `wire_api=responses`.

Development default and target order:

1. Default development and first live cleanup proof target: `codex-env` with
   `CODEX_BASE_URL` + `CODEX_API_KEY`, model `gpt-5.5`, via
   `OpenAIResponsesModel`.
2. Secondary compatibility target after the default route works:
   `codex-mify` with `XM_LLM_BASE_URL` + `XM_LLM_API_KEY`, model
   `xiaomi/mimo-v2.5`, via `OpenAIResponsesModel`.

All OpenAI SDK cleanup runner development, route wiring, artifact parity work,
and first credentialed proof commands should default to `codex-env` unless the
user explicitly requests a `codex-mify` compatibility pass or `codex-env`
credentials are unavailable.

Current probe evidence from 2026-06-09:

- `codex-env` direct Responses API probe succeeded with model `gpt-5.5`.
- `codex-mify` direct Responses API probe succeeded with model
  `xiaomi/mimo-v2.5`; the response included both `reasoning` and `message`
  output items, so artifact parsing must not rely only on a single flat text
  field.
- `codex-env` OpenAI Agents SDK `OpenAIResponsesModel` probe succeeded and
  returned `roboclaws-ok`.
- `codex-mify` OpenAI Agents SDK `OpenAIResponsesModel` probe succeeded and
  returned `roboclaws-ok`.

Out of scope for the first OpenAI SDK cleanup proof:

- Claude Anthropic routes (`kimi-anthropic`, `mimo-anthropic`,
  `mify-anthropic`) are not first-slice OpenAI SDK targets even though those
  models may expose Chat Completions-compatible endpoints elsewhere. Using them
  through OpenAI Agents SDK would require an explicit non-Responses model
  adapter decision, such as Chat Completions or LiteLLM/Any-LLM provider
  wiring.

### Skeptic Result

Risks:

- OpenAI Agents SDK improves runtime control, but it does not automatically
  solve provider quota or rate-limit problems.
- OpenAI Agents SDK is not Codex CLI; a spike must compare behavior honestly
  instead of assuming equivalence.
- A too-general runtime abstraction could become ceremony if it does not first
  preserve the current runner artifacts and failure semantics.
- Pi SDK may be attractive enough to distract from the MCP adapter cost.

Smallest safer plan:

- First implement the runtime contract and an OpenAI experimental driver spike
  behind tests and private route controls. Keep Claude SDK and Pi SDK as parked
  follow-up tracks.

## Recommended Implementation Plan

### Phase 1: Runtime Contract

Create a Roboclaws-owned runtime contract for live coding-agent runs.

Expected shape:

- `LiveAgentRequest`
  - task name
  - skill name or skill prompt
  - MCP server URL/name
  - run directory
  - model/provider profile
  - max turns or one-turn policy
  - timeout/idle timeout
  - artifact paths
  - optional session/resume token
- `LiveAgentResult`
  - phase
  - exit status
  - normalized failure fields
  - retryability fields
  - usage/timing when available
  - event/log artifact paths
  - provider/session identifiers when available
  - `run_result.json` presence/completion fields
- `LiveAgentRuntime`
  - `run(request) -> LiveAgentResult`

Acceptance criteria:

- Current Codex/Claude runner behavior can be described by the contract without
  changing their public behavior.
- Normalized failure semantics remain compatible with existing
  `live_status.json` consumers.
- The contract explicitly separates launcher/session/provider fields from
  cleanup task completion.

### Phase 2: OpenAI Agents Experimental Driver

Add an experimental `openai-agents-live` runtime behind the new contract.

Required behavior:

- Add the OpenAI Agents SDK dependency as a committed optional extra, tentatively
  named `openai-agents`, so the experimental SDK path is reproducible through
  `uv sync --extra dev --extra openai-agents` instead of relying on one-off
  `uv pip install`.
- Start and connect to the existing Roboclaws cleanup MCP server without
  changing MCP tool semantics.
- Run the same household cleanup skill prompt through the SDK runtime.
- Emit SDK event/tracing/session artifacts into the run directory.
- Write the same normalized `live_status.json` and compatible timing/result
  artifacts expected by operator-console and checker paths.
- Provide a runnable repo script and, if useful for traceability, a hidden or
  private `just` route that invokes the SDK runner for `household-cleanup` with
  normal run-dir/status artifacts.
- Run the existing cleanup checker after `done` writes `run_result.json`.
- Preserve one-turn/no-runner-continuation behavior unless a later explicit
  handoff protocol is accepted.

Non-requirements:

- It does not need to outperform Codex CLI in the first spike.
- It does not need to support Claude or Pi.
- It does not need to be exposed as the default public driver.
- It does not need to be promoted to a public `just task::run` driver until a
  maintainer accepts the experimental route.

### Phase 3: Runnable Cleanup Proof

After mock/contract tests pass, run one local OpenAI SDK cleanup proof unless
the only remaining blocker is missing credentials or another explicit
external-input gate.

Minimum runnable proof:

- Command syncs the committed optional OpenAI Agents SDK dependency path.
- Command starts the existing household cleanup MCP server.
- OpenAI SDK runtime connects over MCP and can call cleanup tools.
- A cleanup run reaches `done`, producing `run_result.json`.
- Existing checker runs against that result.
- The run directory contains `live_status.json`, SDK event/trace artifacts,
  checker output, and `report.html`.

If live provider credentials are unavailable, stop with
`BLOCKED_NEEDS_DECISION` only after the dependency, runner, route, artifact, and
mock/contract test slices are complete and the next missing evidence is the
credentialed provider run.

### Phase 4: Compare And Decide

After a runnable SDK cleanup proof exists, compare it with the Codex CLI
baseline.

Decision criteria:

- Does the SDK make session/context/tracing materially clearer?
- Does it classify provider failures with less log guessing?
- Does it preserve MCP/report/checker boundaries?
- Does it produce artifacts that the operator console can consume without
  special-casing task strategy?
- Does the implementation remain smaller than the current CLI wrapper
  complexity it replaces or supplements?

## Alternatives

### Conservative Alternative

Only document the runtime contract and keep all CLI routes unchanged.

Why not first:

- It reduces conceptual entropy but does not test whether an SDK materially
  improves session/context/tracing.

### Claude-First Alternative

Use Anthropic Claude Agent SDK first because it maps more directly to Claude
Code.

Why not first:

- It is route-specific and less aligned with Roboclaws' Python/MCP-first
  architecture.

### Pi-First Alternative

Prototype Pi SDK as a provider-agnostic coding-agent harness.

Why not first:

- It requires a Roboclaws MCP adapter and a Node runtime surface before it can
  test the current robot task.

## Preflight Contract

Preflight status: DONE

Task source:

- User approval of the reduce-entropy recommendation, followed by
  main-session inline planning loop and preflight request.

Canonical source:

- `docs/plans/live-agent-runtime-sdk-spike.md`

Route:

- `$intuitive-refactor` through durable `$intuitive-flow`.

Goal:

- Add a Roboclaws-owned live-agent runtime contract and a first experimental
  OpenAI Agents SDK cleanup runner that can actually use the OpenAI SDK path to
  run the household cleanup job through the existing MCP/checker/report
  boundary, without changing existing Codex/Claude live route behavior.

Scope:

- Define the runtime contract under `roboclaws/agents/`.
- Keep current Codex/Claude CLI runners as baselines.
- Add or prepare focused tests proving current live status/result semantics are
  representable by the contract.
- Add the experimental OpenAI Agents SDK driver only after the contract is
  testable.
- Add dependency handling for OpenAI Agents SDK.
- Add a runnable OpenAI SDK cleanup runner/route that starts the existing MCP
  server, invokes the SDK runtime, waits for `done`, runs the checker, and
  writes normal live artifacts.
- Keep the experimental driver private or clearly non-default unless the user
  approves a public route.
- Document any SDK dependency/extra decision in this plan before changing
  dependency metadata.

Non-goals:

- No removal or replacement of `codex-live` or `claude-live`.
- No Claude Agent SDK implementation in the first slice.
- No Pi SDK implementation or MCP adapter in the first slice.
- No changes to MCP tool semantics or cleanup skill strategy.
- No runner-side cleanup continuation or task-completion inference.
- No public/default route promotion unless separately approved.
- No Codex/Claude baseline replacement.

Context package:

Must read:

- `docs/plans/live-agent-runtime-sdk-spike.md`
- `docs/plans/refactor-live-agent-runner-boundary.md`
- `ARCHITECTURE.md`
- `scripts/molmo_cleanup/run_live_codex_cleanup.py`
- `scripts/molmo_cleanup/run_live_claude_cleanup.py`
- `roboclaws/agents/live_status.py`
- `roboclaws/agents/drivers/household_live.py`
- `scripts/dev/coding_agent_env.sh`
- Relevant unit/contract tests for live reports, operator console status, and
  Just task routing.

Useful evidence:

- `just/README.md`
- `docs/human/mcp-skills-and-semantic-profiles.md`
- `skills/molmo-realworld-cleanup/SKILL.md`
- Official SDK docs linked in this plan.

Do not read unless needed:

- Historical retrospectives.
- Large generated reports under `output/**`.
- GPU/simulator/backend plans unrelated to live-agent runtime boundaries.

Definition of Done / acceptance criteria:

SUCCESS only if:

- A `LiveAgentRuntime` contract exists and clearly represents current CLI
  baseline semantics.
- Existing Codex/Claude live runner behavior and public Just route shape remain
  unchanged unless explicitly approved.
- Normalized status fields remain compatible with existing `live_status.json`
  consumers.
- The OpenAI Agents SDK dependency path is available through committed metadata
  or a documented local experimental install command.
- The OpenAI experimental driver is implemented behind a non-default
  private/experimental route or command.
- The OpenAI SDK route can run the household cleanup job through the existing
  MCP server and produces normal live artifacts.
- `done` remains the only cleanup completion signal, and the existing checker
  runs on the resulting `run_result.json`.
- Tests cover the contract, the preserved failure/status semantics, the route
  wiring, and the SDK runner's artifact/checker behavior.
- Dependency and route exposure decisions are recorded.
- One local credentialed OpenAI SDK cleanup proof has passed, or every
  agent-owned prerequisite for that proof is complete and the plan is explicitly
  blocked on missing provider credentials.

PARTIAL if:

- The runtime contract lands and tests pass, but the OpenAI SDK path cannot yet
  run a cleanup job through MCP/checker/report.

BLOCKED_NEEDS_DECISION if:

- Exposing `openai-agents-live` publicly is required for verification.
- Default `codex-env` credentials are unavailable after dependency, runner,
  route, artifact, and mock/contract slices are complete.
- The SDK cannot connect to the existing MCP server without changing the MCP
  capability contract.

Must not regress:

- `done` as the authoritative completion gate.
- The live runner boundary from
  `docs/plans/refactor-live-agent-runner-boundary.md`.
- Existing `codex-live` and `claude-live` route behavior.
- Operator-console visibility into `live_status.json`, event logs, and report
  artifacts.
- Existing checker/report semantics.

Verification:

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `ruff check` on touched Python files.
- Route trace/dry-run command for the private OpenAI SDK cleanup route.
- Mocked runner test proving the OpenAI SDK route writes normalized status,
  waits for `run_result.json`, and invokes the checker.
- Local credentialed OpenAI SDK cleanup smoke command, unless blocked only by
  missing provider credentials after all agent-owned prerequisites are done.

Execution surface:

- Main session: root supervisor, keeps this plan/preflight aligned and reviews
  final diff.
- Worker: none by default.
- Worker-local goal: none.

Main-session /goal prompt:

```text
/goal execute docs/plans/live-agent-runtime-sdk-spike.md with intuitive-flow
```

To execute:

```text
/goal execute docs/plans/live-agent-runtime-sdk-spike.md with intuitive-flow
```

Approval gate:

- Reply LGTM, approve, or go ahead to approve this preflight contract.
- If the next step should start immediately from the main session, use the
  exact `To execute` command above.

## Parked Follow-Ups

- Anthropic Claude Agent SDK spike for replacing `claude -p` with structured
  SDK calls.
- Pi SDK RPC prototype with a minimal Roboclaws MCP adapter.
- Agent-owned checkpoint/handoff MCP tool for explicit cross-session
  continuation. The private OpenAI Agents SDK route now has bounded same-run
  continuation for incomplete SDK turns, but no durable checkpoint/handoff MCP
  protocol.
- Operator-console retry UX for provider-transient failures.
- Public/default route promotion for `openai-agents-live` after maintainer
  review.

## Completed Slices

1. **Dependency slice**: completed. `openai-agents==0.17.4` is committed as the
   optional `openai-agents` extra in `pyproject.toml` / `uv.lock`. The runtime
   uses `OpenAIResponsesModel` first. Default development and proof target is
   `codex-env` with `CODEX_BASE_URL`, `CODEX_API_KEY`, and model `gpt-5.5`;
   `codex-mify` remains a secondary compatibility target.
2. **Runner slice**: completed. Added
   `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`, which owns the
   cleanup MCP server process, invokes `OpenAIAgentsLiveRuntime`, requires
   `done`/`run_result.json`, runs the existing checker, and writes normal live
   status/timing/checker/report artifacts.
3. **Route slice**: completed. Wired `openai-agents-live` through the private
   `just molmo::cleanup` maintainer surface only. Public
   `just task::run household-cleanup codex|claude ...` behavior remains
   unchanged, and `openai-agents-live` is rejected by public task-driver
   resolution.
4. **Artifact parity slice**: completed. SDK event and trace files
   (`openai-agents-events.jsonl`, `openai-agents-trace.json`) are discovered by
   live artifact helpers, operator-console state, and live-run summary output.
   Operator-console checker status also now surfaces structured cleanup failure
   reasons when available.
5. **Live proof slice**: completed. The local credentialed `codex-env` proof at
   `output/household/household-cleanup/openai-agents-smoke-128/0609_1052/seed-7/`
   passed through MCP, `done`, checker, and `report.html`.
6. **Comparison slice**: completed for the first spike decision. The SDK path
   gives Python-native MCP wiring plus event/trace artifacts, but it is not
   Codex CLI and is not promoted to a public/default route. The decision is to
   keep `openai-agents-live` private/non-default as an experimental supplement
   while retaining Docker-backed Codex and Claude Code CLI routes as product
   baselines.
7. **Bounded incomplete-turn continuation slice**: completed after the
   `codex-mify`/`xiaomi/mimo-v2.5` compatibility run ended cleanly from the SDK
   but stopped before MCP `done`. The private OpenAI Agents SDK runner now has a
   small extension point for incomplete-turn recovery: when an SDK invocation
   exits successfully with `agent-turn-complete` and no `run_result.json`, the
   runner may issue a bounded continuation prompt and invoke the SDK again
   against the same MCP server state. `done`/`run_result.json` remains the only
   cleanup success signal; the runner still fails after the configured attempt
   cap instead of inferring task completion.
8. **SDK performance observability slice**: completed after the mify comparison
   showed SDK success but long MCP between-tool gaps, while direct mify Codex
   failed early. The private OpenAI Agents SDK runner now captures its cleanup
   MCP server stdout/stderr to `openai-agents-server.log` and summarizes
   control-plane request counts in `live_timing.json`, including
   `ListToolsRequest`, `CallToolRequest`, streamable HTTP session count, trace
   export skips, HTTP statuses, and `list_tools_per_call_tool`. This makes the
   repeated-list-tools observation measurable before optimizing it. Because the
   cleanup MCP tool catalog is static within one run, the SDK route now also
   enables the Agents SDK MCP `cache_tools_list` option by default and records
   that setting in timing; `ROBOCLAWS_OPENAI_AGENTS_CACHE_TOOLS_LIST=false` can
   disable it for A/B runs.
9. **Observability V1 slice**: completed. `live_timing.json` now includes an
   intent-neutral `timeline.schema == "live_agent_timeline_v1"` plus semantic
   identifiers for `surface`, `intent`, `task_name`, `task_intent_mode`,
   `runtime`, `provider_profile`, `model`, and `evidence_lane`. The private
   OpenAI Agents SDK route writes sanitized SDK span artifacts to
   `openai-agents-spans.jsonl`, discovers those artifacts through
   `LiveAgentResult`, and summarizes span counts/types in `live_timing.json`.
   The lower private `just molmo::cleanup` route also synthesizes the default
   goal contract for direct `openai-agents-live` runs when no goal contract path
   is supplied. `openai-agents-live` remains private/non-default, and
   `done`/`run_result.json` remains the only cleanup success signal.

### Observability Contract V1

The formal live-agent timing contract should be intent-neutral. Even though the
first implementation lives in the OpenAI Agents SDK cleanup runner, the stable
schema name should be `live_agent_timeline_v1`, not a cleanup-specific name such
as `openai_agents_cleanup_timeline_v1`. The payload should identify the run
semantics explicitly with fields such as `surface`, `intent`, `task_name`,
`task_intent_mode`, `runtime`, `provider_profile`, `model`, and
`evidence_lane`.

The first attribution model has four layers:

- runner wall-clock segments: setup, live-agent runtime, post-agent server wait,
  checker, and final overhead;
- runtime/model attribution: provider or SDK time that is not explained by the
  MCP trace;
- MCP/backend attribution: trace timing, robot-view capture, tool handler time,
  between-tool gaps, control-plane counts, and tool-error classifications;
- task quality: `run_result.json`, checker outcome, restored/failed objects,
  and intent-specific gate failures.

Single-run artifacts remain authoritative for one execution. Multi-run
comparison should be produced by a separate summarizer that reads
`live_timing.json` and related artifacts across run directories instead of
writing aggregate benchmark state back into a run.

The Observability V1 slice adds OpenAI Agents SDK span-level evidence through a
trace processor and writes it to `openai-agents-spans.jsonl`. The span artifact
exposes trace/span identifiers, timing, span types, model/usage, MCP tool names,
and error metadata without changing `done`/`run_result.json` as the only cleanup
success signal. Raw prompts, model text, function inputs/outputs, credentials,
and private evaluator truth are not written to the span artifacts; error samples
may be retained only when they are useful for failure classification and do not
contain secrets.

### Agent SDK Performance Plan

Status: planning contract ready on 2026-06-10 after comparing the final
Observability V1 OpenAI Agents SDK runs against earlier 2026-06-09 SDK cleanup
artifacts. Implementation has not started; this section is the canonical
pre-GSD plan for the next Agent SDK performance slice.

Goal:

- Reduce model-side latency for GPT/codex-env and MiMo/mify
  `openai-agents-live` cleanup runs without changing public route exposure,
  MCP capability semantics, checker gates, or `done`/`run_result.json` as the
  only cleanup success signal.

Current evidence:

- Earlier `mify` smoke SDK runs finished in roughly 2-4 minutes.
- Earlier `codex-env` smoke SDK runs finished in roughly 5 minutes.
- The final Observability V1 `codex-env` full-lane runs took roughly 20 minutes
  for `world-public-labels` and `camera-grounded-labels`, and roughly 58
  minutes for `camera-raw-fpv`.
- MCP tool handler time is not the dominant cost. The large bucket is
  `between_tool_gap_s`, which includes model reasoning, SDK orchestration,
  transport, and other agent-side delay between one MCP response and the next
  MCP request.
- Context size is now a first-class performance risk. The final GPT
  `world-public-labels` run recorded about 4.1M total input tokens across
  response spans, `camera-grounded-labels` about 6.0M, and `camera-raw-fpv`
  about 24.6M before a provider-wrapped context-window failure. Prompt cache
  was observed, but cached-token ratio alone did not keep wall-clock low.

Non-goals:

- Do not promote `openai-agents-live` to the public/default route.
- Do not add macro MCP tools or hide cleanup behind one opaque tool.
- Do not change checker semantics or treat SDK turn completion as cleanup
  success.
- Do not store raw prompts, model text, function inputs/outputs, credentials,
  or private evaluator truth in performance artifacts.
- Do not make raw-FPV cleanup success the first optimization gate; first make
  raw-FPV bounded, classified, and context-safe.

#### Performance Telemetry V2

Add context and cache attribution to `live_timing.json` and the normalized
timeline before changing behavior. This avoids treating all model-side delay as
one undifferentiated `between_tool_gap_s` bucket.

Required field groups for the first implementation:

```text
context_metrics:
  available
  source: openai_agents_span_usage | unavailable
  limitations
  kickoff_prompt_chars
  kickoff_prompt_estimated_tokens
  continuation_prompt_chars
  continuation_prompt_estimated_tokens
  response_span_count
  total_input_tokens
  total_cached_input_tokens
  total_uncached_input_tokens
  cache_hit_ratio
  max_input_tokens
  p50_input_tokens
  p95_input_tokens
  total_output_tokens
  total_reasoning_tokens
  max_reasoning_tokens
  context_window_failure_detected

cache_metrics:
  available
  source: openai_agents_span_usage | unavailable
  limitations
  cache_tools_list
  provider_prompt_cache_observed
  cached_input_token_ratio
  first_response_cached_tokens
  stable_prefix_hash
  prompt_profile_id
  mcp_tool_catalog_cache_enabled

context_growth_metrics:
  available
  source: live_timing_and_trace | unavailable
  limitations
  trace_event_count
  observe_response_count
  raw_fpv_observation_count
  tool_response_bytes_total
  largest_tool_response_bytes
  agent_visible_state_bytes_p95
  continuation_attempt_count
```

Telemetry must derive token and cache data from sanitized span usage where
available. It may store hashes and sizes, but not raw prompt text or tool
payload bodies. Missing span usage is `available=false` with a limitation; it is
never a zero-token measurement.

Metric derivation details:

- `context_metrics` reads only sanitized `span_end` events where
  `span_type == "response"`. Do not also sum parent `custom`/`turn` span usage,
  because those spans may duplicate response usage.
- `total_input_tokens` is the sum of response-span `usage.input_tokens`.
- `total_cached_input_tokens` is the sum of
  `usage.input_tokens_details.cached_tokens`, falling back to
  `usage.cached_input_tokens` only when the nested field is absent.
- `total_uncached_input_tokens = total_input_tokens -
  total_cached_input_tokens`, floored at zero.
- `cache_hit_ratio = total_cached_input_tokens / total_input_tokens` when
  `total_input_tokens > 0`; otherwise it is `null`.
- `total_output_tokens` is the sum of response-span `usage.output_tokens`.
- `total_reasoning_tokens` is the sum of
  `usage.output_tokens_details.reasoning_tokens` when present.
- `p50_input_tokens` and `p95_input_tokens` use nearest-rank percentiles over
  per-response `input_tokens`.
- `provider_prompt_cache_observed` is true when any response span reports
  cached input tokens greater than zero.
- `first_response_cached_tokens` comes from the first response span in
  chronological order.
- `model_or_sdk_unattributed_s` is the non-negative remainder after subtracting
  MCP trace elapsed time and available response-span durations from the OpenAI
  Agents SDK runtime window. If span durations are unavailable, record the
  limitation and derive only the broader SDK-minus-MCP residual.
- `context_window_failure_detected` is true when the live failure reason,
  provider reason, or sanitized error classification matches a context-window,
  max-token, or context-budget failure.

Persistence details:

- Store `context_metrics`, `cache_metrics`, `context_growth_metrics`, and
  `agent_sdk_perf_profile` as top-level `live_timing.json` fields.
- Surface a compact copy of the same groups under
  `timeline.latency_attribution` so cross-run readers can consume the
  normalized timeline without re-reading runner-specific fields.
- Keep `openai_agents_span_metrics` as the span artifact availability/count
  summary; do not overload it with token/cache totals once telemetry V2 exists.

#### Runtime Performance Profiles

Introduce private Agent SDK performance profiles for `openai-agents-live`.
Profiles are runtime strategy/config, not public task names.

Required persisted shape:

```text
agent_sdk_perf_profile:
  schema: agent_sdk_perf_profile_v1
  profile_id: baseline | gpt_compact_v1 | mimo_compact_v1 | raw_fpv_budgeted_v1 | custom
  source: default | cli | environment | metadata
  provider_profile: codex-env | mify
  model_family: gpt | mimo
  prompt_mode: full | compact | raw_fpv_compact
  continuation_mode: repeat_full_prompt | state_summary_only
  max_turns
  max_continuations
  cache_tools_list
  mcp_client_session_timeout_s
  raw_fpv_candidate_budget
  done_retry_budget
  max_observe_per_waypoint
  context_soft_limit_tokens
  context_hard_limit_tokens
```

Expected model-specific defaults:

- GPT/codex-env: prefer explicit action cadence, aggressive context monitoring,
  and state-summary continuation because the full-lane GPT runs showed large
  cached and uncached context growth.
- MiMo/mify: keep the shorter successful smoke behavior as a baseline, then
  compare compact prompts and state-summary continuation against full-lane
  mify runs before promoting defaults.

Profile resolution precedence:

1. Explicit CLI flag.
2. `LiveAgentRequest.metadata`.
3. Environment variable.
4. Provider/model default.

CLI flag contract:

- Add `--agent-sdk-perf-profile` for `profile_id`.
- Add `--prompt-mode`.
- Add `--continuation-mode`.
- Add `--context-soft-limit-tokens`.
- Add `--context-hard-limit-tokens`.
- Add `--max-observe-per-waypoint`.
- Add `--raw-fpv-candidate-budget`.
- Add `--done-retry-budget`.
- Existing `--max-turns`, `--incomplete-turn-continuation-attempts`,
  `--cache-tools-list` / `--no-cache-tools-list`,
  `--mcp-client-session-timeout-s`, `--provider-profile`, and `--model` remain
  the canonical flags for existing fields.

Known profile ids:

| Profile id | Provider/model family | Prompt mode | Continuation mode | Max turns | Max continuations | Cache tools | MCP timeout | Context soft/hard limit | Lane budgets |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `baseline` | inferred from provider/model | `full` | `repeat_full_prompt` | 128 | 2 | true | 30s | unset / unset | unset |
| `gpt_compact_v1` | GPT/codex-env | `compact` | `state_summary_only` | 128 | 1 | true | 30s | 96k / 128k | done retry 2, max observe per waypoint 1 |
| `mimo_compact_v1` | MiMo/mify | `compact` | `state_summary_only` | 128 | 1 | true | 30s | 64k / 96k | done retry 2, max observe per waypoint 1 |
| `raw_fpv_budgeted_v1` | GPT/codex-env or MiMo/mify | `raw_fpv_compact` | `state_summary_only` | 40 | 1 | true | 30s | 64k / 96k | raw-FPV candidates 24, max observe per waypoint 1, done retry 1 |
| `custom` | explicit | explicit | explicit | explicit | explicit | explicit | explicit | explicit | explicit |

Budget notes:

- `baseline` preserves current behavior and exists for apples-to-apples
  telemetry comparison.
- `gpt_compact_v1` can use a higher context budget than `mimo_compact_v1`
  because the GPT Observability V1 runs showed larger windows but still hit
  raw-FPV context risk.
- Hard-limit checks fail before starting another continuation or broad raw-FPV
  observation loop.
- Raw-FPV uses a lower SDK per-attempt turn cap so the runner regains control
  and can classify budget exhaustion before a single attempt grows into a
  provider context-window failure.
- If a provider exposes a smaller effective context window than the configured
  profile, the run records `provider_context_budget_exceeded` and the profile
  limitation instead of retrying with an implicit larger budget.

#### Context Budget And Compaction

Bound continuation and context growth explicitly.

Policy:

- At `context_soft_limit_tokens`, stop repeating the full original prompt in
  continuation. Use a compact state packet instead.
- At `context_hard_limit_tokens`, fail fast with a classified
  `provider_context_budget_exceeded` or `provider_context_failure` instead of
  continuing until the provider rejects the request.
- Continuation state packets must include only public-safe summaries:
  goal contract summary, completed waypoints, handled objects, blocked
  candidates, last few tool failures, remaining required gates, and the next
  recommended action.
- Raw-FPV continuation must not replay the whole raw-FPV observation history.

Compact state packet shape:

```text
compact_continuation_state:
  schema: compact_agent_state_v1
  surface
  intent
  evidence_lane
  goal_summary
  agent_sdk_perf_profile_id
  completed_waypoints
  handled_object_handles
  public_pending_object_handles
  blocked_candidates:
    - public_id
      reason
      last_failure_tool
  recent_tool_failures:
    - tool
      public_error_class
      public_target
  remaining_public_gates
  next_requested_action
```

The compact packet is prompt input only. It may be summarized in telemetry by
size/hash, but the full packet is not persisted separately unless it is proven
to contain only existing public-safe fields.

#### Action Cadence Policy

Reduce model freedom where the next tool action is obvious.

Label lanes:

- Prefer short deterministic chains:
  `observe -> candidate decision -> pick/place chain -> observe`.
- When `done` returns public pending candidates, clean those handles before
  restarting broad sweep logic.
- When all waypoints are observed and checker-visible gates are satisfied, call
  `done` instead of running another global audit.

Raw-FPV lane:

- Limit candidates per waypoint.
- Block repeated `source_observation_id/category/region` failures.
- Bound unresolved candidate count.
- Prefer fail-fast with classified evidence over unlimited observation loops.
- Treat raw-FPV cleanup pass as a later capability target after context safety
  and bounded runtime are proven.

Compact prompt mode contract:

- `prompt_mode=full` is the current kickoff prompt body.
- `prompt_mode=compact` keeps the same public task contract and tool rules but
  removes repeated explanatory prose, long examples, and global re-audit
  encouragement once the model has enough public state to act.
- `prompt_mode=compact` must still include: task goal, public/private boundary,
  `done` as the only success path, required use of public MCP tools, current
  evidence lane, and failure/reporting expectations.
- `prompt_mode=raw_fpv_compact` starts from `compact` and adds raw-FPV budgets,
  repeated visual-candidate failure blocking, and context-safe termination
  instructions.
- Prompt edits live in `roboclaws/agents/prompts/household_cleanup.py`; runner
  code selects the prompt mode but does not embed task prose.

#### A/B Verification Plan

Run the same seed and generated mess count with old vs optimized profiles:

- GPT/codex-env `world-public-labels`
- GPT/codex-env `camera-grounded-labels`
- MiMo/mify `world-public-labels`
- MiMo/mify `camera-grounded-labels`

Acceptance targets:

- Checker pass does not regress for label lanes.
- Total elapsed time drops by at least 40% on full label lanes.
- `between_tool_gap_s` drops by at least 40%.
- `total_uncached_input_tokens` drops by at least 30%.
- Cache hit ratio does not materially regress.
- Raw-FPV does not need to pass cleanup gates in the first performance pass, but
  it must stay within context budget and write a clear terminal
  classification.

#### Implementation Phase Order

Build this as ordered, reviewable slices. Do not jump directly to prompt
changes before the telemetry and profile contract can prove what changed.

Phase 1: telemetry contract, no behavior change

- Add `context_metrics`, `cache_metrics`, `context_growth_metrics`,
  `model_or_sdk_unattributed_s`, and `agent_sdk_perf_profile` to
  `live_timing.json` and `timeline`.
- Derive usage from sanitized `openai-agents-spans*.jsonl` response spans when
  present. Derive context-growth sizes from `trace.jsonl`, `live_timing.json`,
  and public-safe artifact sizes.
- Preserve the current kickoff prompt, continuation behavior, max turns,
  `cache_tools_list`, and checker flow.
- Required proof: deterministic replay/fixture tests show GPT span usage
  becomes numeric metrics and old MiMo artifacts become `available=false`
  instead of zero-token metrics.

Phase 2: private performance profile plumbing, still no strategy change

- Add one private profile resolver for `openai-agents-live`. The resolver may
  read CLI flags, environment variables, and request metadata, but the resolved
  `agent_sdk_perf_profile` must be persisted in `live_timing.json`.
- Keep the existing behavior as `profile_id=baseline`.
- Add explicit knobs for new strategy only after the baseline profile is
  persisted: `ROBOCLAWS_OPENAI_AGENTS_PERF_PROFILE`,
  `ROBOCLAWS_OPENAI_AGENTS_PROMPT_MODE`,
  `ROBOCLAWS_OPENAI_AGENTS_CONTINUATION_MODE`,
  `ROBOCLAWS_OPENAI_AGENTS_CONTEXT_SOFT_LIMIT_TOKENS`,
  `ROBOCLAWS_OPENAI_AGENTS_CONTEXT_HARD_LIMIT_TOKENS`,
  `ROBOCLAWS_OPENAI_AGENTS_MAX_OBSERVE_PER_WAYPOINT`,
  `ROBOCLAWS_OPENAI_AGENTS_RAW_FPV_CANDIDATE_BUDGET`, and
  `ROBOCLAWS_OPENAI_AGENTS_DONE_RETRY_BUDGET`.
- Existing knobs stay valid and must appear inside the profile:
  `ROBOCLAWS_OPENAI_AGENTS_MAX_TURNS`,
  `ROBOCLAWS_OPENAI_AGENTS_INCOMPLETE_TURN_CONTINUATION_ATTEMPTS`,
  `ROBOCLAWS_OPENAI_AGENTS_CACHE_TOOLS_LIST`,
  `ROBOCLAWS_OPENAI_AGENTS_MCP_CLIENT_SESSION_TIMEOUT_S`,
  `ROBOCLAWS_OPENAI_AGENTS_PROVIDER`, `ROBOCLAWS_CODEX_PROVIDER`,
  `ROBOCLAWS_OPENAI_AGENTS_MODEL`, and `ROBOCLAWS_CODEX_MODEL`.
- Required proof: a unit test resolves `baseline`, `gpt_compact_v1`,
  `mimo_compact_v1`, `raw_fpv_budgeted_v1`, and `custom` without changing the
  public `just run::surface` route or accepting `openai-agents-live` through
  public task-driver routing.

Phase 3: continuation compaction

- Change only incomplete-turn recovery first. Replace the current
  `original_prompt + suffix` continuation with `state_summary_only` when the
  resolved profile requests it or context usage crosses the soft limit.
- The continuation packet must be built from public-safe state: goal contract
  summary, completed waypoints, handled object handles, public pending handles,
  blocked candidates, last few public tool failures, remaining public gates,
  and the next requested action.
- The continuation packet must not include raw prompts, model text, full tool
  payload bodies, private target truth, hidden scorer data, or full raw-FPV
  observation history.
- Required proof: mocked incomplete-turn test confirms the continuation prompt
  excludes the full kickoff prompt body and still refuses to mark success
  without `done`/`run_result.json`.

Phase 4: label-lane action cadence

- Apply compact prompt/action-cadence policy to `world-public-labels` and
  `camera-grounded-labels` before raw-FPV.
- Keep tool semantics unchanged: no macro tool, no hidden cleanup routine, no
  private truth in prompts. The prompt may ask the model to use shorter
  deterministic chains when public tool output already identifies the next
  object or pending candidate.
- The runner must not enforce deterministic cleanup sequencing by selecting
  pick/place chains itself. Runner-owned behavior is limited to telemetry,
  profile resolution, continuation policy, and explicit budgets.
- Done retry is bounded by `done_retry_budget`. If `done` reports public
  pending candidates, the next prompt/context packet must focus only those
  candidates before another broad sweep.
- Required proof: local A/B runs for GPT/codex-env and MiMo/mify label lanes
  compare against the canonical baselines below.

Phase 5: raw-FPV budget and classification

- Add raw-FPV budgets after label-lane performance improves, or earlier when
  the change is scoped only as a safety guard that prevents runaway
  context/window failures. Earlier raw-FPV safety work is not a label-lane
  performance-success claim.
- Budget repeated failures by public identifiers:
  `source_observation_id`, category, region, visual-candidate id, and failure
  reason. Do not persist raw image payloads or hidden object truth.
- When budgets are exhausted, fail with a classified public terminal reason
  such as `raw_fpv_candidate_budget_exhausted`,
  `provider_context_budget_exceeded`, or `provider_context_failure`.
- Required proof: raw-FPV no longer runs until provider context-window failure
  without a classified terminal reason. Cleanup pass is not required in this
  phase.

Phase 6: cross-run comparison workflow

- Extend or replace `scripts/molmo_cleanup/summarize_live_run.py` only after
  telemetry V2 exists. The current single-run helper's hard-coded 18m30s
  baseline must not be used for Agent SDK A/B claims.
- The future comparison command must accept explicit run directories or a
  machine-readable manifest. It must print provider, model, lane, profile id,
  checker outcome, elapsed time, `between_tool_gap_s`, context/cache metrics,
  unavailable metric limitations, and raw-FPV terminal classification.
- Required proof: manifest-driven comparison rejects missing baseline/candidate
  pairs instead of silently comparing against smoke or failed runs.

#### Metric Ownership Contract

| Metric group | Single owner | Source artifacts | Scope | Privacy rule |
| --- | --- | --- | --- | --- |
| Runner wall-clock segments | live runner | `live_timing.json` epochs | single run | no raw prompt or payload |
| MCP/backend timing | MCP trace/report timing | `trace.jsonl`, runtime timing | single run | public tool names and durations only |
| MCP control plane | live runner log summarizer | `openai-agents-server.log`, `live_timing.json` | single run | counts/status only |
| SDK span counts/types | SDK span summarizer | `openai-agents-spans*.jsonl` | single run | sanitized span ids/types only |
| Context/cache metrics | telemetry V2 adapter | sanitized response span usage | single run | usage numbers, hashes, and sizes only |
| Context-growth metrics | telemetry V2 adapter | `trace.jsonl`, `live_timing.json`, public artifact sizes | single run | sizes and counts only |
| Agent SDK profile | profile resolver | CLI/env/request metadata | single run | resolved config, never credentials |
| Provider/model residual | latency attribution adapter | runner, MCP timing, span durations | single run | aggregate seconds only |
| Task quality | checker/report | `run_result.json`, report artifacts | single run | public result plus existing checker boundary |
| A/B comparison | cross-run summarizer | explicit manifest/run dirs | cross run | summarize only sanitized single-run metrics |

Implementation rule: compute each metric group once at its owner and pass it
through reports/summaries. Do not recompute the same metric with different
meaning in report rendering, prompt strategy, or cross-run comparison.

#### Canonical Baseline Manifest

Use these as the current comparison manifest until a new baseline pass is
recorded. Smoke runs explain "why did this used to take 2-5 minutes"; they are
not full-lane acceptance baselines.

| Key | Role | Run directory | Outcome | Elapsed / gap | Context/cache availability |
| --- | --- | --- | --- | --- | --- |
| `gpt_world_public_obsv1` | full-lane GPT baseline | `output/household/household-cleanup/openai-agents-observability-v1-world-public/0609_2119/seed-7` | passed, `codex-env`, `gpt-5.5`, `world-public-labels` | 1226.449s / 1036.839s | spans available; about 4.1M input tokens, about 80% cached |
| `gpt_camera_grounded_obsv1` | full-lane GPT baseline | `output/household/household-cleanup/openai-agents-observability-v1-camera-grounded/0609_2140/seed-7` | passed, `codex-env`, `gpt-5.5`, `camera-grounded-labels` | 1243.701s / 1060.527s | spans available; about 6.0M input tokens, about 78% cached |
| `gpt_raw_fpv_obsv1` | raw-FPV diagnostic baseline only | `output/household/household-cleanup/openai-agents-observability-v1-raw-fpv/0609_2202/seed-7` | failed, `provider_transient_failure`, `camera-raw-fpv` | 3470.478s / 2965.239s | spans available; about 24.6M input tokens, about 79% cached |
| `mimo_world_public_0609c` | full-lane MiMo diagnostic baseline | `output/household/household-cleanup/agent-sdk-extra-lanes-0609c/world-public-labels/0609_1733/seed-7` | failed checker, `mify`, `xiaomi/mimo-v2.5`; lane inferred from parent path | 617.464s / 481.810s | unavailable; predates span usage and lane field |
| `mimo_camera_grounded_0609c` | full-lane MiMo baseline | `output/household/household-cleanup/agent-sdk-extra-lanes-0609c/camera-grounded-labels/0609_1733/seed-7` | passed, `mify`, `xiaomi/mimo-v2.5`; lane inferred from parent path | 569.911s / 389.054s | unavailable; predates span usage and lane field |
| `mimo_smoke_obsv` | smoke reference only | `output/household/household-cleanup/openai-agents-mify-mimo-observability/0609_1331/seed-7` | passed, `mify`, `xiaomi/mimo-v2.5`, smoke-like route | 140.727s / 120.642s | unavailable; do not compare as full-lane baseline |
| `mimo_smoke_continuation` | smoke reference only | `output/household/household-cleanup/openai-agents-mify-mimo-continuation/0609_1304/seed-7` | passed, `mify`, `xiaomi/mimo-v2.5`, smoke-like route | 228.841s / 210.013s | unavailable; do not compare as full-lane baseline |
| `gpt_smoke_rerun` | smoke reference only | `output/household/household-cleanup/openai-agents-codex-env-rerun/0609_1127/seed-7` | passed, `codex-env`, `gpt-5.5`, smoke-like route | 284.188s / 267.984s | unavailable; do not compare as full-lane baseline |
| `gpt_smoke_128` | smoke reference only | `output/household/household-cleanup/openai-agents-smoke-128/0609_1052/seed-7` | passed, `codex-env`, `gpt-5.5`, smoke-like route | 321.747s / 310.003s | unavailable; do not compare as full-lane baseline |

Baseline comparison rules:

- Full-lane optimized GPT runs compare only against `gpt_world_public_obsv1`
  and `gpt_camera_grounded_obsv1`.
- Full-lane optimized MiMo runs compare against
  `mimo_camera_grounded_0609c`; `mimo_world_public_0609c` is diagnostic until a
  passing MiMo world-public baseline is recorded.
- Full-lane MiMo world-public performance-success claims require a new passing
  MiMo world-public baseline. The current failed checker run is timing evidence
  only.
- Raw-FPV optimized runs compare runtime/context safety against
  `gpt_raw_fpv_obsv1`; they do not need checker pass in the first performance
  slice.
- Smoke references may be used only to explain the original "2-5 minute"
  observation. They must not be used to claim full-lane speedup.

#### Schema Availability And Privacy Rules

- Every new metric group must include `available`, `source`, and
  `limitations`.
- Numeric usage fields are omitted or `null` when `available=false`; do not use
  zero for missing provider/span data.
- If `openai-agents-spans*.jsonl` exists but has no response-span usage, mark
  context/cache metrics unavailable with limitation
  `span_usage_missing`.
- If older artifacts lack `evidence_lane`, the cross-run summarizer may infer
  lane from the manifest key or parent directory, but the inferred value must be
  labeled as inferred.
- `stable_prefix_hash` may hash the public prompt/profile shape, tool catalog
  signature, and sanitized goal-contract summary. It must not hash or persist
  raw prompt text, raw model text, raw tool payload bodies, credentials, or
  private scorer truth.
- The first implementation must not persist full
  `compact_continuation_state` packets. Store only size/hash telemetry unless a
  later review proves every field is already public-safe and useful to persist.
- Tool-response byte metrics count serialized public MCP responses after the
  existing artifact redaction boundary. Do not introduce a new raw-payload log
  to measure bytes.
- Error samples remain opt-in and must follow the Observability V1 rule:
  retain only public-safe classification detail.

#### Verification Gates By Phase

Phase 1 deterministic gates:

- `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py -q`
- `.venv/bin/ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py`
- Add fixture coverage for available GPT span usage and unavailable old MiMo
  usage.

Phase 2 deterministic gates:

- Same unit/ruff gates as Phase 1.
- `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
- Assert public `just run::surface` still rejects `openai-agents-live`.

Phase 3 deterministic gates:

- Same unit/ruff gates as Phase 1.
- Add continuation tests for `repeat_full_prompt`, `state_summary_only`,
  soft-limit promotion to summary-only, and hard-limit classified failure.

Phase 4 local/live gates:

- GPT/codex-env:
  `world-public-labels` and `camera-grounded-labels`, seed 7,
  generated mess count 5, baseline profile versus optimized profile.
- MiMo/mify:
  `world-public-labels` and `camera-grounded-labels`, seed 7,
  generated mess count 5, baseline profile versus optimized profile.
- Success requires label-lane checker pass does not regress and the optimized
  profile meets the A/B targets above or records a concrete provider/model
  limitation.

Phase 5 local/live gates:

- `camera-raw-fpv`, seed 7, generated mess count 5, optimized budgeted profile.
- Success requires classified termination within context budget. Checker pass
  is allowed but not required.

Phase 6 deterministic gates:

- Cross-run comparison tests use a small fixture manifest and verify that smoke
  references cannot satisfy full-lane baseline requirements.
- Existing single-run summarizer behavior may remain, but any Agent SDK A/B
  command must use explicit run dirs or manifest entries.

#### Stop Condition For This Planning Loop

The plan is implementation-ready when a future agent can answer these without
new archaeology:

- Which file owns the implementation? Primarily
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` and
  `roboclaws/agents/drivers/openai_agents_live.py`, with prompt edits limited
  to `roboclaws/agents/prompts/household_cleanup.py` only in Phase 4/5.
- Which public route changes? None; `openai-agents-live` remains private under
  `just molmo::cleanup`.
- Which metrics must exist and how missing data is represented? Defined above
  with `available/source/limitations`.
- Which old runs are valid baselines? Defined in the manifest above.
- Which changes are forbidden? Macro tools, public/default promotion, checker
  semantic changes, raw prompt/model/tool payload persistence, private truth
  leakage, and treating SDK turn completion as success.
- Which phase can stop early? Any phase may stop at telemetry/profile proof if
  live provider access is blocked; Phase 4/5 performance claims require local
  live runs.

After this section contains no missing P1/P2 direction in a fresh entropy
audit, further wording polish should be parked instead of expanding the plan.

Saturation audit result: DONE on 2026-06-10. The remaining possible edits are
wording polish or future implementation discoveries, not missing plan
directions for the first performance implementation pass.

#### Grill Batch 1 Decisions

Accepted on 2026-06-10:

- Telemetry/profile plumbing is mandatory before prompt or action-cadence
  optimization.
- Phase 4 remains prompt/profile-level action cadence. The runner must not
  become a hidden deterministic cleanup sequencer.
- MiMo `world-public-labels` performance-success claims need a new passing MiMo
  world-public baseline; the current failed checker run stays diagnostic only.
- The first implementation must not persist full compact continuation packets;
  telemetry may record only size/hash.
- Raw-FPV budget/classification may happen before label-lane optimization only
  as a safety guard against runaway/context-failure runs, not as a cleanup-pass
  or performance-success claim.
- The initial context budgets are accepted as configurable starting defaults,
  not final provider/model limits: GPT `96k/128k`, MiMo `64k/96k`, and raw-FPV
  `64k/96k`.

#### Execution Preflight: Agent SDK Performance Optimization

Preflight status: DRAFT

Task source: user request plus the Agent SDK Performance Plan in this file.

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`.

Route: durable `intuitive-flow`.

Goal: implement the first Agent SDK performance optimization pass for
`openai-agents-live`, starting with telemetry/profile proof and then applying
bounded context, continuation, label-lane cadence, raw-FPV safety, and
cross-run comparison without changing public route or cleanup success
semantics.

Scope:

- Phase 1: add telemetry V2 metrics and profile persistence with no behavior
  change.
- Phase 2: add private Agent SDK performance profile resolution and CLI/env
  controls.
- Phase 3: compact incomplete-turn continuation with public-safe state summary.
- Phase 4: optimize label-lane prompt/action cadence without runner-enforced
  cleanup sequencing.
- Phase 5: add raw-FPV budget/classification guard as context-safety work.
- Phase 6: add manifest-driven cross-run comparison after telemetry V2 exists.

Non-goals:

- Do not promote `openai-agents-live` to public/default routing.
- Do not change MCP tool semantics or add macro cleanup tools.
- Do not change checker semantics or treat SDK turn completion as success.
- Do not persist raw prompts, model text, full tool payload bodies,
  credentials, private evaluator truth, hidden scorer data, or full compact
  continuation packets.
- Do not claim full-lane MiMo world-public performance success until a new
  passing MiMo world-public baseline exists.
- Do not require raw-FPV cleanup pass in the first performance pass.

Context package:

- Must read:
  - `README.md`
  - `ARCHITECTURE.md`
  - `STATUS.md`
  - `AGENTS.md`
  - `CLAUDE.md`
  - this Agent SDK Performance Plan section
  - `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
  - `roboclaws/agents/drivers/openai_agents_live.py`
  - `roboclaws/agents/live_runtime.py`
  - `roboclaws/agents/prompts/household_cleanup.py`
  - `tests/unit/agents/test_live_runtime.py`
  - `tests/contract/dev_tools/test_task_agent_just_recipes.py`
- Useful evidence:
  - canonical baseline run directories listed above
  - `openai-agents-spans*.jsonl`, `live_timing.json`, `trace.jsonl`, and
    `run_result.json` from those runs
  - `scripts/molmo_cleanup/summarize_live_run.py`
- Do not read unless needed:
  - unrelated operator-console dirty work
  - unrelated `output/**` runs outside the baseline manifest
  - parked `TODOS.md` / `THOUGHTS.md`
  - root `PLAN.md`

Definition of Done / acceptance criteria:

SUCCESS only if:

- `live_timing.json` and `timeline.latency_attribution` include telemetry V2
  context/cache/context-growth metrics, profile data, and model/SDK residual
  attribution with `available/source/limitations`.
- Missing span usage is represented as unavailable, not zero.
- `agent_sdk_perf_profile` resolves and persists `baseline`, `gpt_compact_v1`,
  `mimo_compact_v1`, `raw_fpv_budgeted_v1`, and `custom`.
- Continuation compaction does not replay the full kickoff prompt and still
  refuses success without `done`/`run_result.json`.
- Label-lane optimized profiles preserve checker success and meet or explain
  the A/B targets against the canonical baselines.
- Raw-FPV budgeted profile terminates within context budget with classified
  evidence; checker pass is optional.
- Cross-run comparison consumes explicit run directories or a manifest and
  rejects smoke references as full-lane baselines.

BLOCKED_NEEDS_DECISION if:

- A proposed optimization needs public route promotion, MCP macro tools,
  checker semantic changes, runner-enforced cleanup sequencing, or private data
  persistence.
- The SDK/provider only exposes required telemetry by storing raw prompts,
  model text, full tool payloads, credentials, or private evaluator truth.
- A MiMo world-public performance-success claim is needed before a passing MiMo
  world-public baseline exists.

BLOCKED_NEEDS_LOCAL_VALIDATION if:

- Deterministic tests pass but required provider-backed GPT/MiMo label-lane A/B
  runs cannot be executed.
- Raw-FPV safety is implemented but the required raw-FPV budgeted local/live
  run cannot be executed.

INTERMEDIATE_ONLY if explicitly approved:

- Phases 1-3 land with deterministic proof but no provider-backed A/B claims.
  This is useful telemetry/profile groundwork, not a complete performance
  success.

Must not regress:

- private/non-default `openai-agents-live` route boundary;
- public `just run::surface` rejection of `openai-agents-live`;
- `done`/`run_result.json` as the only cleanup success signal;
- bounded incomplete-turn recovery;
- MCP client session timeout override;
- `cache_tools_list` configurability;
- existing report/checker artifact generation and privacy boundary.

Verification:

- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py -q`
- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- Required lint gate:
  `.venv/bin/ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py roboclaws/agents/prompts/household_cleanup.py scripts/molmo_cleanup/summarize_live_run.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
- Required local/live acceptance gate for Phase 4:
  GPT/codex-env and MiMo/mify `world-public-labels` plus
  `camera-grounded-labels`, seed 7, generated mess count 5, baseline profile
  versus optimized profile, compared against the manifest above.
- Required local/live acceptance gate for Phase 5:
  `camera-raw-fpv`, seed 7, generated mess count 5, optimized budgeted profile,
  with classified termination inside context budget.
- Required comparison gate:
  manifest-driven comparison reports elapsed time, `between_tool_gap_s`,
  context/cache availability, checker result, and terminal classification.

Execution surface:

- Main session: root supervisor, owns scope, phase boundaries, required live
  gate judgment, and final SUCCESS / INTERMEDIATE_ONLY /
  BLOCKED_NEEDS_LOCAL_VALIDATION status.
- Worker: none required initially. Use a worker only if implementation becomes
  long-running enough that isolated logs and handoff artifacts materially help.
- Worker-local goal: none initially.

To execute:

```text
/goal execute docs/plans/live-agent-runtime-sdk-spike.md with intuitive-flow
```

Approval gate: reply LGTM, approve, go ahead, or use the exact `To execute`
command above to start durable implementation. Request edits if scope,
acceptance, route, or verification should change.

#### Ranked Reduce-Entropy Candidates

Candidate 1: Context/cache telemetry V2

- Severity: P1
- Entropy source: false confidence and recurring rediscovery.
- Materiality: Current timing can prove the delay sits in
  `between_tool_gap_s`, but it cannot separate context growth, cache misses,
  reasoning-token cost, provider latency, or oversized tool responses.
- Impact radius: live-agent runtime and report artifacts.
- Maintainer test: A maintainer should not need an ad hoc Python script to know
  whether a slow SDK run was dominated by uncached context, cached context,
  reasoning, or tool payload size.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose` for measurement shape, then normal implementation.
- Zen hint: make invisible cost explicit.
- Pattern hint: metrics adapter; do not mix telemetry derivation into cleanup
  task strategy.
- Suggested proof: replay existing sanitized span artifacts and assert
  `context_metrics`, `cache_metrics`, and `context_growth_metrics` are present
  without raw prompt/tool payload leakage.
- Execution risk: safe; observability-only when implemented first.

Candidate 2: Continuation prompt stops repeating the full prompt

- Severity: P1
- Entropy source: provider context failure.
- Materiality: Current incomplete-turn continuation repeats
  `original_prompt + suffix`; the final raw-FPV run already reached a
  provider-wrapped context-window failure.
- Impact radius: private `openai-agents-live` runner.
- Maintainer test: Continuation must not make the next SDK attempt larger by
  replaying the same full kickoff prompt plus all accumulated agent history.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose` if reproduced from raw-FPV artifact; otherwise normal
  implementation.
- Zen hint: bounded context is clearer than implicit model memory.
- Pattern hint: state-summary builder.
- Suggested proof: mocked incomplete-turn test where continuation uses a compact
  public state packet and does not contain the full kickoff prompt body.
- Execution risk: medium; it changes recovery behavior and needs live A/B.

Candidate 3: Agent SDK performance profile object

- Severity: P1
- Entropy source: live source drift and recurring rediscovery.
- Materiality: GPT/codex-env and MiMo/mify currently rely on scattered
  environment defaults and ad hoc run names, making A/B comparisons hard to
  reproduce.
- Impact radius: private SDK runtime configuration.
- Maintainer test: The same command should reveal which prompt/context/cache
  strategy was used without reading environment variables or terminal history.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: normal implementation.
- Zen hint: explicit profiles beat hidden provider assumptions.
- Pattern hint: Strategy object.
- Suggested proof: unit tests for `codex-env` and `mify` profile resolution plus
  `live_timing.json` fields containing `agent_sdk_perf_profile`.
- Execution risk: safe if private/non-default and no public route names change.

Candidate 4: Raw-FPV budget guard

- Severity: P1
- Entropy source: real workflow friction and provider context failure.
- Materiality: The final raw-FPV SDK run made 120 `observe` calls, 90
  `navigate_to_visual_candidate` calls, ran for about 58 minutes, and failed
  without `run_result.json`.
- Impact radius: raw-FPV lane strategy and private SDK runtime budget.
- Maintainer test: Raw-FPV should fail fast with classified public evidence
  before exhausting context, even if it is not yet expected to pass cleanup
  gates.
- Affected paths:
  `roboclaws/agents/prompts/household_cleanup.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  raw-FPV tests or artifact replay tests.
- Owner skill: `diagnose`.
- Zen hint: explicit budgets prevent hidden infinite exploration.
- Pattern hint: budget policy/state machine.
- Suggested proof: fixture trace or mocked run that exceeds unresolved
  candidate/context budget and writes a terminal classification without another
  continuation.
- Execution risk: medium; this touches task behavior and needs live evidence.

Candidate 5: Cross-run performance summarizer

- Severity: P2
- Entropy source: recurring rediscovery.
- Materiality: Performance comparison currently depends on one-off Python
  scripts over `output/**`; future model/profile A/B work will repeat that
  manual analysis unless a stable summarizer exists.
- Impact radius: developer workflow.
- Maintainer test: A reviewer should be able to compare GPT vs MiMo SDK runs by
  pointing one command at run directories.
- Affected paths: likely `scripts/molmo_cleanup/summarize_live_run.py` or a new
  scoped summarizer under `scripts/molmo_cleanup/`, plus focused tests.
- Owner skill: normal implementation.
- Zen hint: one obvious comparison command beats copied analysis snippets.
- Pattern hint: report adapter.
- Suggested proof: command accepts multiple run directories and prints elapsed,
  gap, context/cache, checker, and lane/provider columns.
- Execution risk: safe, but only commit-worthy after telemetry fields exist.

Candidate 6: Canonical A/B baseline manifest

- Severity: P1
- Entropy source: recurring rediscovery and false comparisons.
- Materiality: Existing local outputs include smoke, full-lane, failed, mify,
  codex-env, partial, and continuation runs. Without a baseline manifest,
  future performance claims may compare optimized full-lane runs against
  unrelated smoke or failed runs.
- Impact radius: performance workflow and plan evidence.
- Maintainer test: A reviewer should be able to tell which old run is the
  accepted baseline for each provider/lane before reading timing tables.
- Affected paths: this plan and, once implemented, the cross-run summarizer or
  an artifact manifest under a scoped docs/status location.
- Owner skill: `intuitive-reduce-entropy` for planning; normal implementation
  if a machine-readable manifest is added.
- Zen hint: explicit baselines prevent accidental apples-to-oranges claims.
- Pattern hint: data manifest.
- Suggested proof: record the canonical baseline run directories for GPT
  `world-public-labels`, GPT `camera-grounded-labels`, MiMo
  `world-public-labels`, MiMo `camera-grounded-labels`, and smoke references;
  the performance summarizer can consume the manifest later.
- Execution risk: safe; docs/manifest first.

Candidate 7: Performance metric ownership map

- Severity: P2
- Entropy source: live source drift.
- Materiality: `live_timing.json`, `run_result.json`, `trace.jsonl`, sanitized
  spans, and MCP server logs all contain overlapping timing evidence. Without a
  field ownership map, future changes may compute the same metric in multiple
  places with different meanings.
- Impact radius: live-agent observability and report consumers.
- Maintainer test: A future contributor should know whether a metric belongs in
  runner timing, MCP trace timing, span metrics, context metrics, cache metrics,
  or cross-run summaries.
- Affected paths: this plan first; later
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py` and tests.
- Owner skill: normal implementation.
- Zen hint: one owner per metric keeps reports unsurprising.
- Pattern hint: layered telemetry contract.
- Suggested proof: add a table that maps each proposed metric group to source
  artifacts, privacy level, and single-run vs cross-run scope.
- Execution risk: safe; planning-only until implementation.

Candidate 8: Span usage fallback policy for MiMo/mify

- Severity: P2
- Entropy source: false confidence.
- Materiality: Some earlier MiMo/mify artifacts predate sanitized span usage,
  so context/cache telemetry may be unavailable or incomplete for old baseline
  runs. Treating missing usage as zero would make MiMo look cheaper than it is.
- Impact radius: telemetry and A/B summaries.
- Maintainer test: Missing span usage must be reported as unavailable, not as a
  zero-token run.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  cross-run summarizer tests, and this plan.
- Owner skill: normal implementation.
- Zen hint: absence of evidence is not evidence of zero cost.
- Pattern hint: explicit unavailable state.
- Suggested proof: fixture with no span usage emits `context_metrics.available =
  false` or equivalent limitation, while newer GPT artifacts emit numeric token
  fields.
- Execution risk: safe.

Candidate 9: Provider-latency classification beyond context/cache

- Severity: P2
- Entropy source: false confidence.
- Materiality: Even after context/cache metrics, a slow `between_tool_gap_s`
  can still come from provider latency, SDK orchestration, or model reasoning.
  The plan needs a known residual bucket so optimization does not overfit to
  token counts.
- Impact radius: performance diagnosis.
- Maintainer test: If token/cache metrics look healthy but wall-clock is still
  high, the report should say which bucket remains unattributed.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`, and the summarizer.
- Owner skill: `diagnose`.
- Zen hint: name the unknowns instead of hiding them.
- Pattern hint: attribution pipeline.
- Suggested proof: telemetry derives `model_or_sdk_unattributed_s` after
  subtracting MCP trace time and, when available, response span durations; the
  residual is surfaced as a named field.
- Execution risk: safe if it is observability-only.

#### Post-Optimization Reduce-Entropy Batch

Status: planning notes captured on 2026-06-10 after the first Agent SDK
performance optimization pass. These are follow-up candidates, not approved
implementation work.

Context:

- The 2026-06-10 optimization pass made the private `openai-agents-live` route
  much faster on GPT label lanes while preserving checker-visible success, but
  the optimized runs still made about 72-78 response/model turns and still
  reached large per-run context sizes.
- Roboclaws should not default to MCP macro/merge tools for speed. The repo
  already has a skill-first boundary, the active `molmo-realworld-cleanup`
  skill contains the trace-preserving
  `navigate_to_object -> pick -> navigate_to_receptacle -> open? ->
  place/place_inside -> close? -> observe` routine, and historical MCP/skill
  cleanup intentionally kept ADR-0003 as the only default agent-facing cleanup
  MCP surface.
- Codex and Claude live routes prepare an isolated task workspace and expose
  `skills/molmo-realworld-cleanup/SKILL.md` for the agent to read. The current
  plain OpenAI Agents SDK route does not do equivalent automatic skill
  discovery; it sets `LiveAgentRequest.skill_name` and passes a rendered kickoff
  prompt to `Agent.instructions`.
- OpenAI Agents SDK has first-class MCP and model/provider extension points, and
  its `Model` interface is replaceable. Codex-style progressive-disclosure
  Skills are a Codex behavior; Agents SDK also has Sandbox skill capabilities,
  but the current `openai-agents-live` implementation uses a plain
  `Agent + MCPServerStreamableHttp` path, not SandboxAgent skill mounting.

References:

- Current SDK route request metadata:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- Current SDK runtime model/MCP wiring:
  `roboclaws/agents/drivers/openai_agents_live.py`
- Cleanup skill and routine:
  `skills/molmo-realworld-cleanup/SKILL.md`,
  `skills/molmo-realworld-cleanup/scripts/trace_preserving_cleanup.py`,
  `roboclaws/household/cleanup_routine.py`
- Prior MCP/skill minimal-surface decision:
  `docs/retrospectives/plans/refactor-mcp-skill-minimal-surface.md`
- Official SDK/Codex docs inspected during discussion:
  <https://openai.github.io/openai-agents-python/mcp/>,
  <https://openai.github.io/openai-agents-python/models/>,
  <https://openai.github.io/openai-agents-python/ref/sandbox/capabilities/skills/>,
  <https://developers.openai.com/codex/skills>

Grill Batch 2 Decisions:

- The first unified validation flow is a diagnostic sweep. A candidate may
  become a publishable/accepted speedup only after the winning row gets a
  repeat or paired validation pass.
- The first "all relevant models" matrix covers GPT/codex-env and MiMo/mify
  across `world-public-labels`, `camera-grounded-labels`, and
  `camera-raw-fpv`. Kimi/Claude rows should be recorded as unsupported or
  blocked until their SDK route/provider support exists; do not expand this
  speed pass into a provider-integration task.
- The live matrix needs explicit caps before execution: default
  `concurrency=1`, racing disabled, planned max live runs, planned max
  wall-clock, hard context budgets, and any racing-arm multiplier. A dry run
  must display the worst-case budget before provider calls.
- Raw-FPV remains a classified diagnostic target unless a later lane-specific
  pass explicitly makes cleanup success part of the gate. Do not raise budgets
  or add racing before raw-FPV failure rails and image-memory policy are tested.
- MCP/profile-affecting candidates start as SDK-private or opt-in. Promotion to
  default MCP/profile behavior requires Candidate X cross-client proof and a
  separate promotion decision.
- Behavior quality follows same-or-better by default. Faster but lower-quality
  runs are not accepted unless the tradeoff is explicitly waived in the
  decision packet.

Candidate Grouping And Test Priority:

Use this grouping as the practical execution view for the next unified
validation flow. It does not delete candidates. It front-loads the directions
that are most likely to produce useful speed evidence without changing the
public MCP/default route boundary.

Group 0: foundation, comparability, and stop gates

- Candidates: R, S, T, U, V, W, Y, B, Z, Q.
- Purpose: make the experiment matrix runnable, bounded, private-safe,
  comparable, and decision-ready before spending provider time.
- Expected direct speedup: none. This group exists so later speed claims are
  trustworthy.
- Test first because: without these gates, a large live flow can produce
  incomparable artifacts, hidden feature interactions, budget overrun, or a
  faster-but-worse result.
- Default proof: dry-run matrix, offline/fake-provider preflight, privacy gate,
  baseline matrix rows, behavior-quality comparator, and trace-derived
  reducible-bucket report.

Group 1: high-confidence private SDK levers

- Candidates: A, G, J, H, I, L.
- Purpose: remove prompt/skill drift, make SDK model settings explicit, improve
  prompt-cache interpretability, use SDK-native continuation where safe, compact
  model input without changing MCP responses, and measure text-only/deferred
  turns.
- Expected value: high to medium. These attack observed context growth and
  response-turn overhead while staying inside the private SDK route.
- Test before MCP/profile changes because: they are easier to isolate and less
  likely to break Codex/Claude/OpenClaw clients.
- Default proof: label-lane A/B on GPT/codex-env and MiMo/mify after foundation
  gates; repeat only the best winner rows before calling a speedup accepted.

Group 2: high-impact lane-specific reductions

- Candidates: O, M, N, F.
- Purpose: collapse deterministic camera-grounded observe/label plumbing,
  narrow irrelevant tools by evidence lane, avoid repeated static map payloads,
  and reduce report-only visual capture if it becomes a top wall-clock bucket.
- Expected value: high for O in `camera-grounded-labels`; medium-high for M/N
  if Q/I still show tool-choice noise or repeated map bytes; conditional for F.
- Test after Group 1 because: these can touch MCP response shape, tool
  availability, or evidence-lane behavior. Run SDK-private or opt-in first.
- Default proof: lane-local A/B with unchanged checker success, explicit trace
  preservation, and Candidate X before any default/public promotion.

Group 3: raw-FPV stabilization track

- Candidates: P, AA.
- Purpose: make raw-FPV failures actionable and reduce repeated image context
  before increasing budgets or attempting cleanup-pass claims.
- Expected value: high for making raw-FPV bounded and informative; unknown for
  cleanup success.
- Test separately because: raw-FPV has a different success target in this pass:
  classified diagnostic evidence, not label-lane cleanup pass.
- Default proof: fewer repeated `visual_candidate_not_resolved` failures,
  explicit retained/evicted image evidence, bounded context, and unchanged
  report reviewability.

Group 4: speculative or expensive orchestration

- Candidates: D, C, K, E.
- Purpose: measure per-arm cache/cost before racing, optionally race individual
  SDK model calls, audit safe parallel tool-call policy, and consider broader
  agent-visible state deltas after SDK-specific compaction is exhausted.
- Expected value: potentially high but riskier and more expensive.
- Test last by default because: racing can multiply provider cost/cache effects,
  parallel tool calls can violate robot action ordering, and broad state deltas
  can become public contract changes.
- Default proof: Q must identify the target bucket as a top remaining reducible
  source before this group runs. D is mandatory before C; K needs an explicit
  read-only/stateful tool-order policy; E waits until I/N/AA are insufficient.

Group 5: promotion and compatibility gates

- Candidate: X.
- Purpose: decide whether an opt-in/private MCP/profile-affecting speedup can
  become default behavior.
- Expected direct speedup: none. This is the safety gate for promotion.
- Test only when needed: any M/N/O/P/E result that stays private does not need
  public promotion. Default/public behavior requires cross-client proof and a
  separate promotion decision.

Simplification rules:

- Treat E as the umbrella for state compaction; try concrete SDK/lane variants
  I, N, and AA first.
- Treat D as part of C, not a standalone live speed feature.
- Treat X as a promotion gate, not a speed candidate.
- Treat W/Y/S/T/U/V/R as flow infrastructure, not optimization arms.
- Treat B/Z/Q as measurement and acceptance gates, not speed features.

Candidate A: OpenAI Agents SDK skill parity

- Severity: P1
- Entropy source: live source drift and recurring rediscovery.
- Materiality: The route names `molmo-realworld-cleanup` as a skill and the
  kickoff prompt says to use the bundled skill, but the plain SDK runtime does
  not actually mount or progressively disclose `SKILL.md` the way Codex/Claude
  live routes do.
- Why now: Further speed/quality work should not keep duplicating or compressing
  skill rules into runner prompts if the canonical strategy already lives in
  `skills/molmo-realworld-cleanup/`.
- Impact radius: private `openai-agents-live` route, prompt construction, and
  skill packaging.
- Maintainer test: A reviewer should be able to answer "what skill instructions
  did this SDK agent actually receive?" from artifacts without inferring it
  from a hand-edited prompt fragment.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `roboclaws/agents/prompts/household_cleanup.py`,
  `skills/molmo-realworld-cleanup/`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `intuitive-reduce-entropy` for the preflight; normal
  implementation or `openai-docs` if SDK/Sandbox capability details need fresh
  confirmation.
- Zen hint: one canonical skill source beats duplicated prompt memory.
- Pattern hint: skill-pack adapter; keep strategy in skills and runtime wiring
  in the driver.
- Suggested proof: deterministic test showing the SDK kickoff context includes
  a bounded, public-safe skill pack or explicit recorded limitation; no raw
  private truth or full tool payloads are persisted. A live proof should compare
  skill-pack mode against current compact prompt mode on at least one passing
  label lane.
- Execution risk: medium. Plain `Agent` prompt injection is low-risk but may
  increase context; SandboxAgent skill capability may change runtime topology
  and needs a separate decision.

Candidate B: All provider/model x evidence-lane matrix

- Severity: P1
- Entropy source: false comparisons and incomplete coverage.
- Materiality: Current evidence has GPT and MiMo label-lane runs, but raw-FPV
  cleanup success remains out of scope and model/lane performance differs
  materially. Future claims need a complete matrix instead of one-off lane
  anecdotes.
- Why now: The user direction is to support all evidence lanes for all relevant
  models, then verify them as one group.
- Impact radius: local live verification workflow, manifest schema, and
  comparison summary.
- Maintainer test: A maintainer should be able to see, for each model/provider
  and evidence lane, whether the route passes, fails with classified evidence,
  or is unsupported.
- Affected paths:
  `docs/status/active/agent-sdk-perf-opt-0610-comparison-manifest.json`,
  `scripts/molmo_cleanup/summarize_live_run.py`,
  future matrix manifest under `docs/status/active/`.
- Owner skill: normal implementation after planning.
- Zen hint: explicit matrix beats implicit provider preferences.
- Pattern hint: test matrix manifest.
- Suggested proof: manifest rows for GPT/codex-env and MiMo/mify across
  `world-public-labels`, `camera-grounded-labels`, and `camera-raw-fpv`,
  including pass/fail/classified terminal, elapsed time, `between_tool_gap_s`,
  context/cache metrics, and checker result. Add Kimi/Claude-compatible rows
  only after their route/provider support is explicitly available.
- Execution risk: medium because it requires local provider-backed runs and
  backend slot/time budget, but the code change can be docs/summarizer-only.

Candidate C: Per-model-call racing inside the SDK model interface

- Severity: P2 initially, P1 if matrix evidence shows provider tail latency is
  the dominant remaining blocker.
- Entropy source: unexplored latency tradeoff.
- Materiality: The optimized label lanes still spend most wall-clock inside
  model/SDK response-to-next-tool gaps. OpenAI Agents SDK exposes a replaceable
  `Model.get_response(...)` interface, so a wrapper can race multiple provider
  arms for one model call rather than launching two complete live runs.
- Why now: This is the user's preferred racing granularity: one SDK model call
  can be sent to multiple models asynchronously, and the first valid response
  wins.
- Impact radius: private SDK runtime/model adapter and telemetry.
- Maintainer test: A reviewer should be able to tell whether racing reduced
  wall-clock enough to justify extra provider/cache cost and whether loser arms
  were cancelled safely.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`,
  `scripts/molmo_cleanup/summarize_live_run.py`.
- Owner skill: `diagnose` for measurement shape, then normal implementation.
- Zen hint: experiment at the exact bottleneck boundary, not at a coarser run
  boundary.
- Pattern hint: racing/decorator model adapter.
- Suggested proof: deterministic fake-model test for a non-streaming
  `RacingModel` wrapper where two arms receive the same sanitized model input,
  the first schema-valid/MCP-legal response wins, loser cancellation is recorded,
  and only the winner's response enters subsequent agent history. First live
  proof should be opt-in and label-lane-only.
- Execution risk: high enough to require explicit approval before live runs.
  Loser requests may still be billable and may perturb provider-side prompt
  cache behavior.

Candidate D: Racing cache/cost observability

- Severity: P1 if Candidate C is executed.
- Entropy source: false confidence.
- Materiality: Current cache metrics objectively measure single-arm runs, but
  they do not say whether a cancelled loser arm consumed input tokens, cache
  writes, or billable work.
- Why now: The user explicitly called out cache miss/cost uncertainty for
  multi-model racing.
- Impact radius: telemetry V2, span/event artifacts, and comparison summaries.
- Maintainer test: A racing experiment should never report "faster" without
  also reporting known or unknown extra token/cache cost per arm.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose`.
- Zen hint: name the cost uncertainty instead of hiding it behind elapsed time.
- Pattern hint: per-arm telemetry adapter.
- Suggested proof: `live_timing.json` records per-arm fields such as
  `arm_started_at`, `arm_finished_at`, `arm_cancelled_at`, `winner`,
  `usage_available`, `input_tokens`, `cached_input_tokens`,
  `uncached_input_tokens`, and `loser_billable_unknown`. Missing loser usage is
  unavailable, never zero.
- Execution risk: safe as observability, but should be bundled with Candidate C
  if racing is implemented.

Candidate E: Agent-visible state delta/compaction

- Severity: P1 after skill parity/matrix, because it preserves MCP boundaries
  while attacking context growth.
- Entropy source: provider context pressure.
- Materiality: Even optimized label-lane runs can reach max input sizes around
  100k-144k tokens. This suggests repeated tool response state, not only the
  kickoff prompt, is a remaining context driver.
- Why now: The previous pass compacted kickoff and continuation prompts; the
  next non-MCP-merge speed lever is reducing repeated agent-visible state.
- Impact radius: MCP response shaping or SDK-side input filtering; report
  artifacts must stay complete.
- Maintainer test: The agent should see enough current public state to act, but
  not keep re-reading large unchanged map/camera payloads every model call.
- Affected paths:
  `roboclaws/household/realworld_mcp_server.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`,
  report/checker tests if artifact boundaries change.
- Owner skill: `diagnose` followed by normal implementation.
- Zen hint: send deltas to the agent, keep full evidence in artifacts.
- Pattern hint: state snapshot/delta adapter or SDK `call_model_input_filter`.
- Suggested proof: fixture run or replay where repeated map/observation payload
  bytes drop while `run_result.json`, `trace.jsonl`, and report evidence remain
  complete. Do not hide private truth or add macro cleanup behavior.
- Execution risk: medium. This touches the agent-visible contract and needs
  checker/live proof.

Candidate F: Selective visual artifact capture

- Severity: P2.
- Entropy source: real workflow friction.
- Materiality: Optimized label runs still spend roughly 100-130s in
  robot-view capture, which is a real wall-clock bucket separate from model
  reasoning.
- Why now: If model-side work is reduced further, report-only visual capture may
  become a larger share of runtime.
- Impact radius: visual backend/report artifact policy.
- Maintainer test: Report artifacts should remain reviewable, but the live
  agent should not wait on redundant report-only views when a smaller or reused
  artifact would prove the same state.
- Affected paths:
  household visual backend/report code, cleanup runner visual flags, and report
  checker tests.
- Owner skill: normal implementation after matrix data confirms the benefit.
- Zen hint: capture what proves the behavior, not every redundant view.
- Pattern hint: artifact capture policy.
- Suggested proof: A/B run with unchanged checker result and report
  reviewability, plus lower `robot_view_capture_s`.
- Execution risk: medium because it changes visual evidence density.

Candidate G: SDK-native model settings performance profile

- Severity: P1.
- Entropy source: recurring rediscovery and unexplored SDK control surface.
- Materiality: The current private SDK route builds an `OpenAIResponsesModel`
  and passes only `max_turns` to `Runner.run`. Local inspection of the pinned
  `openai-agents==0.17.4` package shows `RunConfig(model_settings=...)` and
  `ModelSettings` support `verbosity`, `parallel_tool_calls`, `truncation`,
  `max_tokens`, `reasoning`, `prompt_cache_retention`, `store`, and
  `context_management`, but the current performance profile does not record or
  vary those SDK-native knobs.
- Why now: Optimized label-lane runs still made 72-78 response/model turns.
  Before adding custom orchestration, the next low-risk pass should test
  whether SDK/model settings can reduce output chatter, reasoning latency, or
  context retention while preserving MCP `done` success.
- Impact radius: private `openai-agents-live` route, performance profile
  schema, and timing artifacts.
- Maintainer test: A reviewer should be able to see the exact SDK model
  settings used for a speed claim instead of guessing provider defaults.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`,
  `scripts/molmo_cleanup/summarize_live_run.py`.
- Owner skill: normal implementation with `openai-docs` refresh if SDK option
  semantics need confirmation beyond local signatures.
- Zen hint: prefer explicit runtime knobs over implicit provider behavior.
- Pattern hint: typed performance-profile adapter.
- Suggested proof: deterministic test that profile settings produce a
  `RunConfig`/`ModelSettings` payload and are persisted in `live_timing.json`;
  A/B label-lane run with unchanged checker success comparing
  `verbosity=low`, explicit `include_usage`, selected `reasoning` effort when
  supported, and any provider-safe `max_tokens` cap.
- Execution risk: medium. Some options are provider/model-specific and must
  degrade to "unsupported/omitted" rather than silently altering behavior.

Candidate H: Responses/session continuation instead of prompt replay

- Severity: P1.
- Entropy source: provider context pressure.
- Materiality: The runner currently starts a fresh SDK invocation for
  incomplete-turn recovery and either repeats the full prompt or sends a compact
  continuation packet. Local SDK signatures expose `previous_response_id`,
  `auto_previous_response_id`, `conversation_id`, and `session` on
  `Runner.run`, which may let the provider/SDK carry prior state without the
  runner replaying large prompt text.
- Why now: Continuation prompt compaction helped, but context growth still
  reaches large per-run maxima. SDK-native continuation is a narrower
  experiment than changing MCP response shapes.
- Impact radius: private SDK runtime, continuation policy, privacy boundary,
  and artifact metadata.
- Maintainer test: A reviewer should be able to tell whether a continuation
  reused provider-side response/session state, what identifiers were persisted,
  and whether no raw prompts/model text were written.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose` for measurement, then normal implementation.
- Zen hint: use the SDK's state primitive when it is clearer than re-sending
  state manually.
- Pattern hint: continuation strategy.
- Suggested proof: fake Runner test covering `previous_response_id` or
  `conversation_id` propagation across continuation attempts, plus live A/B
  with `max_input_tokens`, `total_uncached_input_tokens`, completion/checker
  status, and artifact privacy verified.
- Execution risk: medium-high. Provider-side storage/session behavior may vary
  and must remain private-route-only until privacy, retention, and replay
  semantics are explicit.

Candidate I: SDK `call_model_input_filter` state compaction

- Severity: P1 after Candidate H/G, because it attacks repeated context without
  changing the public MCP tool contract.
- Entropy source: provider context pressure and live source drift.
- Materiality: Candidate E names agent-visible state delta/compaction. The
  lower-risk SDK-specific variant is to apply compaction at
  `RunConfig.call_model_input_filter`, leaving MCP tool responses and report
  artifacts complete while trimming only the model input carried into the next
  response call.
- Why now: Optimized runs still show large repeated input contexts, but the
  repo direction is not to hide cleanup behind MCP merge tools.
- Impact radius: private SDK runtime and tests; public MCP traces/reports should
  remain unchanged.
- Maintainer test: Full trace/report evidence should remain reviewable while
  the next model call receives only the necessary current public state.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose` followed by normal implementation.
- Zen hint: compact at the model boundary, not at the evidence boundary.
- Pattern hint: model-input filter pipeline.
- Suggested proof: fixture test where synthetic repeated tool payloads are
  reduced by the input filter, sensitive data is not introduced, and
  `trace.jsonl`/`run_result.json` stay unchanged; live proof compares
  `tool_response_bytes_total` vs `max_input_tokens` before/after.
- Execution risk: medium. A too-aggressive filter can remove state the model
  needs for ordering or recovery.

Candidate J: Prompt cache retention and stable-prefix hardening

- Severity: P2, or P1 if future matrix runs show high uncached input remains
  the dominant cost.
- Entropy source: cache/cost false confidence.
- Materiality: Current cache metrics report observed cached tokens and a blank
  `stable_prefix_hash`, but the profile does not explicitly control
  `prompt_cache_retention` or prove that the stable prefix stays stable across
  comparable runs. Racing or session experiments need a baseline cache story
  first.
- Why now: The user explicitly asked whether cache hint/miss behavior is
  objective. Single-arm cache metrics are now objective, but stable-prefix
  drift and explicit retention policy remain unmodeled.
- Impact radius: prompt renderer, private SDK profile metadata, summarizer.
- Maintainer test: A reviewer should be able to distinguish real cache miss
  from changed prompt prefix or unavailable provider usage.
- Affected paths:
  `roboclaws/agents/prompts/household_cleanup.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: normal implementation.
- Zen hint: measure the cache key surface instead of trusting anecdotes.
- Pattern hint: stable-prefix fingerprint.
- Suggested proof: persist a sanitized stable prefix hash, profile id,
  `prompt_cache_retention` intent, and cache availability state; fixture proves
  missing usage is unavailable, not zero, and A/B runs with the same prefix show
  expected cache behavior.
- Execution risk: safe if hashes are computed from public-safe prompt segments
  and no raw prompt text is persisted.

Candidate K: Parallel tool-call policy audit

- Severity: P2.
- Entropy source: unexplored SDK control surface with semantic-order risk.
- Materiality: `ModelSettings.parallel_tool_calls` is available, and the mify
  Codex recipe explicitly disables parallel tool calls for that provider. The
  cleanup task is mostly stateful (`navigate -> observe -> pick -> place`), but
  some calls such as early map/fixture reads may be independent. The risk and
  benefit should be documented before enabling it globally.
- Why now: Parallel tool calls are an obvious speed knob, but enabling them
  without a task-order policy could corrupt robot semantics.
- Impact radius: private SDK profile and safety tests.
- Maintainer test: A reviewer should see which tools are safe to parallelize,
  which are strictly sequential, and whether the provider/model supports the
  setting.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `scripts/dev/coding_agent_env.sh`,
  `tests/contract/dev_tools/test_task_agent_just_recipes.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `plan-eng-review` before implementation because this touches
  action ordering.
- Zen hint: make ordering constraints explicit before asking for concurrency.
- Pattern hint: capability/tool execution policy.
- Suggested proof: policy table marking read-only MCP tools versus stateful
  robot tools, deterministic test that mify remains disabled, and live proof
  only if a constrained read-only parallelism mode exists.
- Execution risk: medium-high. Default should remain sequential unless the
  policy proves safety.

Candidate L: Non-tool response and turn-count waste audit

- Severity: P2.
- Entropy source: hidden latency and model behavior drift.
- Materiality: Optimized label lanes still make nearly one response span per
  MCP tool call. If some response turns contain only progress text or defer a
  tool call, `tool_choice`, output guardrails, or stricter SDK instructions may
  cut latency without changing MCP tools. If no such turns exist, this candidate
  should be closed as no-change evidence.
- Why now: The remaining elapsed time is dominated by many response-to-next-tool
  gaps; reducing unnecessary response turns is cheaper than racing models.
- Impact radius: telemetry summarizer and private SDK profile.
- Maintainer test: A maintainer should know whether the 72-78 response turns
  are all necessary tool-selection turns or include avoidable text-only turns.
- Affected paths:
  `roboclaws/agents/drivers/openai_agents_live.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose`.
- Zen hint: count wasted turns before optimizing around them.
- Pattern hint: turn classifier.
- Suggested proof: sanitized span/event classifier reports response spans,
  function/tool spans, terminal outputs, and avoidable text-only turn count
  without persisting model text; only test `tool_choice`/guardrails if the audit
  finds real waste.
- Execution risk: safe as observability; behavior change needs live proof.

Candidate M: Evidence-lane tool-surface pruning

- Severity: P1 if tool-choice noise is confirmed, otherwise P2.
- Entropy source: live source drift and model action entropy.
- Materiality: `public_tool_names_for_profile(...)` currently returns the same
  broad cleanup tool set regardless of evidence lane. Optimized traces show the
  model still reaches tools that are irrelevant or marginal in a given lane:
  world-label runs called `adjust_camera` 6-7 times with noop errors and GPT
  world also called `inspect_visible_object`; MiMo world made one
  `check_operator_messages` call even though no operator-message flow was part
  of the run. A smaller lane-specific tool surface could reduce action search
  and error recovery without hiding cleanup behind a macro tool.
- Why now: After prompt compaction, the remaining latency is dominated by many
  response-to-tool decisions. Reducing the available wrong choices is a direct
  entropy reduction at the model/tool boundary.
- Impact radius: private SDK route first, MCP profile metadata, and profile
  tests if promoted beyond SDK experiments.
- Maintainer test: For each evidence lane, a maintainer should know which tools
  are intentionally exposed and which are unavailable because they cannot help
  that lane.
- Affected paths:
  `roboclaws/household/realworld_mcp_backend.py`,
  `roboclaws/mcp/profiles.py`,
  `docs/human/mcp-skills-and-semantic-profiles.md`,
  `tests/unit/agents/test_live_runtime.py`,
  relevant MCP/profile contract tests.
- Owner skill: `plan-eng-review` before implementation because this touches the
  public capability surface.
- Zen hint: fewer explicit tools beat a broad menu plus repeated prompt
  warnings.
- Pattern hint: capability allowlist by evidence-lane strategy.
- Suggested proof: trace-derived before/after counts for irrelevant tool calls,
  unit tests for lane-specific allowlists, and live label-lane A/B with
  unchanged checker success and no new unknown-tool failures.
- Execution risk: medium. Keep as private route/profile override until
  Codex/Claude/OpenClaw behavior is checked.

Candidate N: `metric_map` repeated-call delta contract

- Severity: P1 if context growth remains the next blocker after SDK input
  filtering; otherwise P2.
- Entropy source: provider context pressure.
- Materiality: Optimized world-label traces repeatedly pull a large
  `metric_map`: GPT world called it 3 times for about 162 KB total with one
  63 KB response; MiMo world called it 2 times for about 101 KB. The map is
  mostly static, while the useful repeated state is visited-waypoint status,
  current public anchors, and recent observed handles.
- Why now: Candidate I can compact at the SDK model boundary. If this remains a
  bottleneck, an explicit MCP-level map snapshot/delta contract would reduce
  repeated agent-visible state for every client while keeping full artifacts in
  `runtime_metric_map.json` and reports.
- Impact radius: `metric_map` response shape, map/report artifacts, and agent
  prompt guidance.
- Maintainer test: A second `metric_map` call in the same run should not replay
  unchanged large map payload unless the agent explicitly requests it.
- Affected paths:
  `roboclaws/household/realworld_contract.py`,
  `roboclaws/household/realworld_mcp_server.py`,
  `tests/unit/agents/test_live_runtime.py`,
  map/report contract tests.
- Owner skill: `diagnose` followed by normal implementation.
- Zen hint: send the changed state, not the whole static map each time.
- Pattern hint: snapshot plus delta/version token.
- Suggested proof: unit fixture where repeated `metric_map` calls return a
  public-safe revision/delta payload, full map evidence still persists to
  artifacts, and live A/B shows lower `tool_response_bytes_total` and
  `max_input_tokens`.
- Execution risk: medium-high if made default. Prefer an opt-in
  `metric_map_delta_v1` or SDK-profile mode until all clients are checked.

Candidate O: Camera-grounded observe/label two-step collapse

- Severity: P1.
- Entropy source: avoidable tool round trips.
- Materiality: Camera-grounded optimized traces show a mechanical pattern:
  every useful `observe` is followed by `declare_visual_candidates` with only
  `observation_id` so the configured camera labeler labels the frame. GPT
  camera used 19 `observe` and 19 `declare_visual_candidates` calls; MiMo
  camera used 18 observes and 19 declares, including one
  `missing_raw_fpv_observation` error. This is not a cleanup macro; it is a
  lane-local perception postprocessor.
- Why now: Collapsing this two-step could remove many model/tool turns in the
  lane with the least semantic risk, because the prompt already instructs the
  model to call the labeler deterministically after each raw FPV observation.
- Impact radius: camera-grounded evidence lane, observation response schema,
  visual-grounding provenance, and report trace preservation.
- Maintainer test: Camera-grounded runs should preserve labeler provenance and
  reviewable image evidence while not requiring the model to issue a separate
  deterministic labeler call after every observe.
- Affected paths:
  `roboclaws/household/realworld_mcp_server.py`,
  `roboclaws/household/realworld_contract.py`,
  camera-grounded report/checker tests, and SDK comparison summaries.
- Owner skill: `diagnose` then normal implementation.
- Zen hint: automate deterministic perception plumbing, keep robot behavior
  explicit.
- Pattern hint: lane-local postprocessor with trace-preserving virtual substep.
- Suggested proof: camera-grounded A/B where tool calls and response spans drop
  by the former declare count, checker still passes, and trace/report artifacts
  still show visual-grounding pipeline evidence for each observation.
- Execution risk: medium. Do not generalize to cleanup action chains; preserve
  an explicit trace event or nested provenance for the auto-label step.

Candidate P: Raw-FPV visual-candidate failure rails

- Severity: P1 for raw-FPV lane work.
- Entropy source: repeated failure and weak affordance contract.
- Materiality: The final raw-FPV budgeted run exhausted turn budget after 40
  model turns. Its trace shows 7 `navigate_to_visual_candidate` calls with 6
  `visual_candidate_not_resolved` failures. The model is spending scarce turns
  guessing regions/actions that the server cannot resolve.
- Why now: Raw-FPV currently has classified budget evidence but no cleanup
  success. Before increasing budgets or racing models, the lane needs tighter
  public affordances for candidate region format, retry cooldown, failure
  fingerprints, and next valid action.
- Impact radius: raw-FPV prompt/rules, `navigate_to_visual_candidate` response
  schema, budget classifier, and trace summary.
- Maintainer test: A raw-FPV failure should teach the next model call exactly
  which public candidate shape failed and how to avoid repeating it, without
  adding structured object labels.
- Affected paths:
  `roboclaws/household/raw_fpv_guidance.py`,
  `roboclaws/household/realworld_contract.py`,
  `roboclaws/household/realworld_mcp_server.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  raw-FPV tests.
- Owner skill: `diagnose`.
- Zen hint: make failure feedback actionable instead of letting the model
  rediscover invalid regions.
- Pattern hint: failure-memory and affordance schema.
- Suggested proof: raw-FPV fixture with repeated invalid visual candidates emits
  compact failure fingerprints, retry limits, and schema hints; live proof
  should show fewer repeated `visual_candidate_not_resolved` failures before
  any larger budget increase is accepted.
- Execution risk: medium. Keep raw-FPV unlabeled; do not silently convert it
  into camera-grounded-labels.

Candidate Q: Trace-derived irreducible floor and waste classifier

- Severity: P1 for deciding the next optimization batch.
- Entropy source: false optimization target.
- Materiality: Current timing says where time was spent, but not which tool
  calls were behaviorally necessary. A trace lower-bound analyzer can classify
  calls into required sweep/navigation/manipulation, deterministic
  lane-plumbing, repeated static-state reads, noop/error recovery, and optional
  report-only capture. That would make future "extreme speedup" experiments
  objective before changing behavior.
- Why now: The optimized runs already expose enough trace data to separate
  likely irreducible work from waste: e.g. 14 waypoint navigations and post-place
  observes may be necessary, while repeated `metric_map`, noop
  `adjust_camera`, and camera declare two-step calls are candidate waste.
- Impact radius: summarizer/reporting only at first.
- Maintainer test: Before implementing another speed feature, a maintainer
  should see the estimated remaining floor and the largest reducible buckets.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/molmo_cleanup/test_summarize_live_run.py`,
  `tests/unit/agents/test_live_runtime.py`.
- Owner skill: `diagnose`.
- Zen hint: measure the remaining floor before chasing another knob.
- Pattern hint: trace classifier pipeline.
- Suggested proof: offline analyzer over the 2026-06-10 artifacts that reports
  required tool count, reducible tool count, repeated response bytes, error/noop
  turns, lane-plumbing turns, and visual-capture wall-clock buckets without
  reading private evaluator truth.
- Execution risk: safe. Observability-only and can precede behavior changes.

Candidate R: Unified Agent SDK experiment matrix runner

- Severity: P1.
- Entropy source: workflow drift and false comparisons.
- Materiality: The current comparison manifest is hand-authored for a small set
  of baseline/candidate pairs, while the next batch spans SDK settings,
  continuation, model-input filtering, tool-surface pruning, lane-specific MCP
  changes, raw-FPV rails, and optional racing. Without a single experiment
  matrix contract, a "big flow" will produce incomparable output directories,
  hidden env overrides, missing baselines, or unbounded live runs.
- Why now: The user wants to try the directions later in one flow, so the flow
  itself needs to become a first-class artifact before more speed changes land.
- Impact radius: local-only live verification workflow, comparison manifest,
  status artifacts, and summarizer.
- Maintainer test: A maintainer should be able to inspect one manifest and know
  every model, evidence lane, seed, candidate feature flag, baseline role,
  output directory, and expected terminal condition before any provider call.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  future `scripts/molmo_cleanup/run_agent_sdk_perf_matrix.py`,
  `docs/status/active/agent-sdk-*.json`,
  `just/molmo.just` only if a private maintainer recipe is useful.
- Owner skill: `diagnose` for matrix shape, then normal implementation.
- Zen hint: one explicit matrix beats many shell-history experiments.
- Pattern hint: experiment manifest runner.
- Suggested proof: dry-run mode emits the full command/status manifest without
  provider calls; execution mode refuses missing baseline/candidate rows,
  duplicate output dirs, unsupported lane/model combos, and matrix entries with
  no stop condition.
- Execution risk: safe in dry-run; live execution needs explicit local approval
  and budget caps.

Candidate S: Feature-flag and interaction isolation contract

- Severity: P1.
- Entropy source: false attribution.
- Materiality: Many candidates can interact. For example, `ModelSettings`,
  session continuation, `call_model_input_filter`, tool pruning, metric-map
  deltas, and camera auto-labeling can all reduce turns or context. If several
  are enabled in one candidate run, the result may be faster but unexplainable.
- Why now: The next pass should be able to run a large flow while still
  attributing wins and regressions to one bounded direction at a time.
- Impact radius: private performance profile schema, live timing metadata, and
  comparison summary.
- Maintainer test: Each candidate arm should record exactly which feature flags
  were enabled and which earlier accepted arms it depends on.
- Affected paths:
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/agents/drivers/openai_agents_live.py`,
  future matrix manifest, and summarizer tests.
- Owner skill: normal implementation.
- Zen hint: isolate one change before composing it.
- Pattern hint: feature-flag strategy with dependency graph.
- Suggested proof: `live_timing.json` persists `experiment_id`,
  `candidate_ids`, `feature_flags`, `dependency_candidate_ids`, and
  `profile_id`; summarizer rejects comparisons where candidate arms differ by
  untracked flags.
- Execution risk: safe. Mostly metadata, but it should block ambiguous live
  comparisons.

Candidate T: Offline replay and fake-provider preflight

- Severity: P1.
- Entropy source: real workflow friction and avoidable provider spend.
- Materiality: Most candidate changes can be schema-tested before live calls:
  trace classifiers can run on existing artifacts; tool-surface pruning can be
  tested against recorded tool sequences; metric-map deltas can use fixtures;
  SDK `RunConfig` settings and session continuation can use fake Runner/Model
  objects. A big flow should not discover basic schema/privacy failures during
  a paid live run.
- Why now: Existing tests mock pieces of the SDK runner, but there is no single
  preflight that replays the 2026-06-10 artifacts and validates the experiment
  matrix without contacting providers.
- Impact radius: tests, summarizer, and future experiment runner.
- Maintainer test: Every live candidate arm should have a no-provider preflight
  result before it is allowed into the live matrix.
- Affected paths:
  `tests/unit/agents/test_live_runtime.py`,
  `tests/unit/molmo_cleanup/test_summarize_live_run.py`,
  future replay fixtures under `tests/fixtures/` or synthesized temp artifacts.
- Owner skill: `diagnose`.
- Zen hint: fail fast on local evidence before spending live time.
- Pattern hint: replay harness.
- Suggested proof: replay existing sanitized trace/timing artifacts to produce
  candidate Q metrics, exercise fake SDK settings/session/filter paths, and
  write a preflight status row for each matrix candidate.
- Execution risk: safe. No provider, no live backend.

Candidate U: Artifact privacy and schema regression gate

- Severity: P1.
- Entropy source: false confidence at the trust boundary.
- Materiality: The new candidates introduce more artifact fields: session IDs,
  stable-prefix hashes, feature flags, racing arm telemetry, trace waste
  classes, tool allowlists, and map delta revisions. Existing checks protect
  many run-result and span paths, but a big flow needs one explicit gate that
  scans all new experiment artifacts for raw prompts, model text, full tool
  payload bodies, credentials, private evaluator truth, and full continuation
  packets.
- Why now: More observability is only useful if it does not erode the current
  public/private boundary.
- Impact radius: artifact writers, summarizer, checker tests, and matrix
  publish step.
- Maintainer test: A failed privacy gate should block comparison publication
  even when the live run itself passed.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  future matrix runner,
  `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`,
  tests for SDK span/timing artifacts.
- Owner skill: normal implementation.
- Zen hint: make the trust boundary executable.
- Pattern hint: artifact schema/privacy validator.
- Suggested proof: fixtures with forbidden keys/content fail; allowed aggregate
  timings, token counts, hashes, public ids, and sanitized session identifiers
  pass.
- Execution risk: safe and should precede live publication.

Candidate V: Live-run cost, time, and concurrency budget gate

- Severity: P1.
- Entropy source: operational risk and unbounded experiment loops.
- Materiality: A full provider/model x evidence-lane x candidate matrix can
  quickly become expensive and can monopolize the MolmoSpaces backend slot.
  Racing makes this worse because loser arms may still be billable. The flow
  needs explicit max runs, max wall-clock, max response/model calls, context
  hard limits, and optional token/cost estimates before execution.
- Why now: The next task is intentionally one large validation flow. It should
  stop safely instead of discovering cost limits through provider failures.
- Impact radius: future experiment runner, live runner budget metadata, and
  local operator workflow.
- Maintainer test: A maintainer should know the maximum possible live spend and
  wall-clock before starting the flow.
- Affected paths:
  future matrix runner,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `docs/status/active/live-agent-runtime-sdk-spike.md`.
- Owner skill: `diagnose` for budgets, normal implementation for gates.
- Zen hint: explicit budgets beat heroic live loops.
- Pattern hint: budget policy/state machine.
- Suggested proof: dry-run prints total planned runs, estimated wall-clock, max
  turns, hard context budgets, and racing-arm multiplier; execution refuses to
  run without acknowledged caps and stops after the first configured hard
  failure class.
- Execution risk: safe. It limits live work rather than expanding it.

Candidate W: Variance and repeatability gate

- Severity: P2 for planning, P1 before publishing a strong speed claim.
- Entropy source: false performance confidence.
- Materiality: Current speed evidence is mostly one run per provider/lane/seed.
  Live model latency and action choices vary, so a one-off win can overstate a
  speedup or hide a regression. The big flow needs repeat indexes or a small
  paired-seed set before declaring a candidate accepted.
- Why now: Once multiple optimization arms exist, reviewers need to know whether
  a speedup survived repeated runs or is just a lucky sample.
- Impact radius: experiment manifest, summarizer, and acceptance criteria.
- Maintainer test: A "winner" row should show either repeated-run stability or
  an explicit "single-run diagnostic only" label.
- Affected paths:
  future matrix runner,
  `scripts/molmo_cleanup/summarize_live_run.py`,
  `tests/unit/molmo_cleanup/test_summarize_live_run.py`.
- Owner skill: `diagnose`.
- Zen hint: label uncertainty instead of laundering it as certainty.
- Pattern hint: paired experiment analysis.
- Suggested proof: manifest supports `seed`, `repeat_index`, and aggregation
  fields such as median elapsed, worst checker state, and p95 max input tokens;
  single-run rows are reported as diagnostic-only.
- Execution risk: medium because repeated live runs cost time/money; keep the
  default repeat count small and opt-in.

Candidate X: Cross-client regression guard for MCP/profile-affecting arms

- Severity: P1 for Candidate M/N/O/P/E, P2 otherwise.
- Entropy source: public contract drift.
- Materiality: Several candidates touch MCP response shape, tool availability,
  or evidence-lane behavior. `openai-agents-live` is private, but the same MCP
  server supports direct, Codex, Claude, and OpenClaw-style clients. A speed win
  in the SDK route should not silently break those clients.
- Why now: Tool-surface pruning and map/observe response changes are tempting
  speed wins, but they need compatibility staging.
- Impact radius: MCP profile contracts, direct runs, Codex/Claude live routes,
  and docs.
- Maintainer test: Any MCP/profile-affecting optimization should say whether it
  is SDK-private, opt-in profile-only, or safe for all clients.
- Affected paths:
  `roboclaws/household/realworld_mcp_backend.py`,
  `roboclaws/household/realworld_mcp_server.py`,
  `roboclaws/mcp/profiles.py`,
  `just/molmo.just`,
  relevant direct/Codex/Claude contract tests.
- Owner skill: `plan-eng-review` before implementation.
- Zen hint: private experiments must not blur into public contract changes.
- Pattern hint: compatibility adapter or opt-in capability profile.
- Suggested proof: direct smoke/contract tests pass for default profiles; SDK
  private profile can narrow tools or responses without changing default
  Codex/Claude/OpenClaw behavior; docs label promotion criteria.
- Execution risk: medium-high for default MCP changes. Stage as private/opt-in
  until cross-client proof passes.

Candidate Y: Decision dashboard and acceptance packet

- Severity: P2, but required for a large combined validation flow.
- Entropy source: recurring rediscovery and buried evidence.
- Materiality: After a big flow, raw artifacts will be spread across output
  dirs, live_timing files, traces, checker logs, and reports. Without a compact
  decision packet, the team will have to rediscover which candidates won,
  regressed, were inconclusive, or were blocked by budget/privacy gates.
- Why now: The plan is explicitly to try the directions later in one big flow,
  so the closeout artifact should be designed before the flow starts.
- Impact radius: summarizer/report generation and active status docs.
- Maintainer test: One generated report should answer "what should we implement
  or keep next?" without reading every run directory.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  future matrix runner,
  `docs/status/active/live-agent-runtime-sdk-spike.md`.
- Owner skill: normal implementation.
- Zen hint: make the decision obvious from one artifact.
- Pattern hint: decision report.
- Suggested proof: generated markdown or JSON report with candidate id, status
  (`accepted`, `rejected`, `inconclusive`, `blocked`), speed/cost/context
  deltas, checker state, privacy gate state, and artifact links.
- Execution risk: safe. Reporting-only.

Candidate Z: Behavior-quality regression comparator

- Severity: P1.
- Entropy source: false confidence.
- Materiality: Speed improvements can preserve `done` and still degrade the run:
  fewer restored objects, lower semantic acceptability, more disturbances,
  earlier premature-done patterns, more failed/noop tools, or weaker evidence
  density. The existing checker is the hard gate, but the big flow also needs a
  quality comparator so "faster" does not silently mean "worse but still
  passing."
- Why now: The user explicitly wants to know that behavior and results have not
  degraded while runtime improves.
- Impact radius: comparison summarizer, decision dashboard, and acceptance
  criteria.
- Maintainer test: Every accepted speedup should show the quality metrics that
  stayed equal or improved, plus any tolerated tradeoff.
- Affected paths:
  `scripts/molmo_cleanup/summarize_live_run.py`,
  future matrix runner,
  `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py`,
  `tests/unit/molmo_cleanup/test_summarize_live_run.py`.
- Owner skill: `diagnose`.
- Zen hint: success should mean same-or-better behavior, not just lower time.
- Pattern hint: behavioral comparator.
- Suggested proof: comparison rows include restored count/rate, semantic
  accepted count, sweep coverage, disturbance count, premature-done flag,
  failed/noop tool count, raw-FPV classified terminal state, and report artifact
  presence; accepted candidates cannot regress configured quality thresholds.
- Execution risk: safe. Reporting/gating only.

Candidate AA: Raw-FPV image-memory and multiresolution policy

- Severity: P1 for any attempt to make raw-FPV pass cleanup gates.
- Entropy source: provider context pressure and visual search entropy.
- Materiality: Raw-FPV runs carry image evidence through the model context and
  the latest budgeted run still consumed about 1.58M total input tokens over 40
  response spans before classified turn-budget exhaustion. Candidate P improves
  failure feedback, but raw-FPV also needs a policy for when full images, compact
  state, thumbnails, crops, or image references remain in the model history.
- Why now: Raising raw-FPV budgets or racing models without reducing repeated
  image context will likely spend more tokens without making cleanup reliable.
- Impact radius: raw-FPV observe response shape, SDK model-input filtering,
  report artifacts, and raw-FPV prompt guidance.
- Maintainer test: The agent should keep enough visual evidence to act, but
  stale full-frame images should not be replayed into every future model call.
- Affected paths:
  `roboclaws/household/realworld_mcp_server.py`,
  `roboclaws/household/raw_fpv_guidance.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/agents/drivers/openai_agents_live.py`,
  raw-FPV tests.
- Owner skill: `diagnose` followed by normal implementation.
- Zen hint: keep the visual proof in artifacts, send the model the smallest
  current image evidence that can support the next action.
- Pattern hint: image-memory policy with thumbnail/crop ladder.
- Suggested proof: raw-FPV fixture and live diagnostic report image count,
  image bytes/tokens when available, retained-image ids, evicted-image ids,
  crop/thumbnail requests, candidate success/failure counts, and unchanged
  report reviewability.
- Execution risk: medium-high. Must not relabel raw-FPV as structured
  camera-grounded evidence, and must not drop image proof from artifacts.

#### Unified Big-Flow Validation Contract

Use this contract when the follow-up candidates are ready to run as one larger
flow. The flow should still execute in staged arms; "big" means one planned
matrix and one decision packet, not one un-attributed mega-change.

Foundation gates before live runs:

1. Build Candidate R's manifest runner in dry-run mode.
2. Add Candidate S feature-flag/dependency metadata and require it in
   `live_timing.json`.
3. Run Candidate T offline replay/fake-provider preflight for every candidate
   arm in the matrix.
4. Run Candidate U privacy/schema gate on synthetic and replayed artifacts.
5. Apply Candidate V budgets: max live runs, max wall-clock, context hard
   limits, default `concurrency=1`, default racing disabled, and any
   racing-arm multiplier.
6. Apply Candidate W repeat policy: the first unified matrix is diagnostic by
   default; accepted/publishable speedup claims require a repeat or paired
   validation pass for the winning row.
7. Add Candidate Z behavior-quality thresholds before accepting any speed win.

Recommended live matrix stages:

1. Baseline refresh: Candidate B across GPT/codex-env and MiMo/mify x evidence
   lane, with old artifacts clearly labeled as historical baselines when not
   rerun. Kimi/Claude rows remain unsupported or blocked until route/provider
   support exists.
2. Low-risk SDK knobs: Candidate G and Candidate J.
3. SDK state/context controls: Candidate H and Candidate I.
4. Turn and tool entropy: Candidate L and Candidate M.
5. Lane-specific reductions: Candidate O for camera-grounded, Candidate N for
   repeated map state, and Candidate P plus Candidate AA for raw-FPV.
6. Visual/report-time reduction: Candidate F only if Q shows capture is a
   dominant remaining bucket.
7. Racing: Candidate D first, then Candidate C only when a matrix row proves
   provider tail latency is worth the extra cost/cache risk.
8. Parallel tool calls: Candidate K only after a tool-order policy is reviewed.

Acceptance gates for any candidate arm:

- `done`/`run_result.json` remains the cleanup success signal.
- Checker-visible behavior does not regress on label lanes.
- Candidate Z quality metrics do not regress beyond configured thresholds:
  restored count/rate, semantic accepted count, sweep coverage, disturbance
  count, premature-done flag, failed/noop tool count, raw-FPV terminal
  classification, and report artifact presence.
- Same-or-better quality is the default acceptance policy. Faster but
  lower-quality runs are rejected unless the decision packet names an explicit
  waiver.
- Raw-FPV may be accepted only as classified diagnostic evidence unless the
  lane explicitly passes cleanup gates.
- No raw prompts, model text, full tool payload bodies, credentials, private
  evaluator truth, or full compact continuation packets are persisted.
- Any MCP/profile-affecting change has Candidate X cross-client proof or stays
  SDK-private or opt-in.
- The decision packet from Candidate Y records accepted, rejected,
  inconclusive, and blocked arms with artifact links.

Stop conditions:

- Stop before live execution if dry-run manifest, offline replay, or privacy
  gate fails.
- Stop a candidate arm after a checker regression, context hard-limit breach,
  unclassified provider failure, or budget exhaustion.
- Stop a speed-acceptance claim when Candidate Z shows behavior-quality
  regression, even if elapsed time improved.
- Stop the loop when Candidate Q shows the remaining reducible bucket is smaller
  than the cost/risk of the next change, or when remaining ideas are only
  wording/profile polish.

Preliminary ordering for a future unified validation pass:

1. Group 0 foundation: R, S, T, U, V, W, Y, B, Z, and Q. This creates the dry
   run matrix, feature-flag attribution, offline preflight, privacy gate, budget
   gate, repeat policy, decision packet, provider/lane baselines,
   behavior-quality comparator, and trace-derived reducible-bucket report.
2. Group 1 private SDK levers: A, G, J, H, I, and L. This is the first real
   speed pass because it targets skill drift, explicit SDK settings, cache
   evidence, continuation, model-input compaction, and avoidable text-only turns
   without changing default MCP/profile behavior.
3. Group 2 lane-specific reductions: O, then M/N as indicated by Q/I, then F
   only if visual capture is still a dominant wall-clock bucket. These remain
   SDK-private or opt-in until cross-client proof exists.
4. Group 3 raw-FPV stabilization: P and AA. This runs on the raw-FPV diagnostic
   track before any budget increase, racing, or cleanup-pass claim.
5. Group 4 speculative/expensive orchestration: D before C, K only after a
   read-only/stateful tool-order policy, and E only if the concrete compaction
   variants I/N/AA are insufficient.
6. Group 5 promotion gate: X before any MCP/profile-affecting result is
   promoted beyond private/opt-in behavior.

Explicit non-goal for this follow-up batch:

- Do not add or promote MCP composite cleanup tools by default. Revisit MCP
  promotion only if multiple skills need the same stable composition, the
  public IO is clear, trace/report artifacts preserve the semantic substeps,
  and measured live performance proves skill-side composition is no longer good
  enough for cross-client use.

### Execution Preflight: Agent SDK Unified Speedup Foundation

Preflight status: DRAFT

Task source: user request plus the Post-Optimization Reduce-Entropy Batch in
this file.

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`.

Route: durable `intuitive-flow`.

Goal: implement the Group 0 foundation for the unified Agent SDK speedup
validation flow, so later speed candidates can be tried in priority order with
bounded cost, privacy gates, comparable metrics, and clear acceptance
decisions.

Scope:

- Add the dry-run experiment matrix runner contract.
- Add feature-flag/dependency metadata for candidate arms.
- Add offline replay / fake-provider preflight.
- Add privacy/schema artifact gate.
- Add live budget gate metadata: max runs, wall-clock, context caps,
  concurrency, and racing multiplier.
- Add behavior-quality comparator and trace-derived reducible-bucket report.
- Add decision packet output for accepted/rejected/inconclusive/blocked arms.
- Preserve the grouped execution order already documented: Group 0 first, then
  Groups 1-5.

Non-goals:

- No live provider-backed matrix runs in this first slice unless separately
  approved after dry-run budget output.
- No public route promotion for `openai-agents-live`.
- No MCP macro cleanup tools.
- No default MCP/profile changes.
- No racing implementation yet.
- No raw-FPV cleanup-pass claim.
- No Codex/Claude route replacement.

Context package:

- Must read:
  - `README.md`
  - `ARCHITECTURE.md`
  - `STATUS.md`
  - `AGENTS.md`
  - `CLAUDE.md`
  - `docs/plans/live-agent-runtime-sdk-spike.md`
  - `docs/status/active/live-agent-runtime-sdk-spike.md`
  - `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
  - `scripts/molmo_cleanup/summarize_live_run.py`
  - `roboclaws/agents/drivers/openai_agents_live.py`
  - `roboclaws/agents/live_runtime.py`
- Useful evidence:
  - `docs/status/active/agent-sdk-perf-opt-0610-comparison-manifest.json`
  - the 2026-06-10 optimized GPT/MiMo/raw-FPV run directories listed in the
    status capsule
  - `skills/molmo-realworld-cleanup/SKILL.md`
- Do not read unless needed:
  - unrelated `output/**`
  - unrelated operator-console dirty work
  - parked `TODOS.md` / `THOUGHTS.md`

Definition of Done / acceptance criteria:

SUCCESS only if:

- Dry-run matrix lists providers, evidence lanes, candidate groups, flags,
  dependencies, stop conditions, unsupported rows, and budget caps.
- Offline/fake-provider preflight runs without provider calls.
- Privacy gate rejects raw prompts, model text, full tool payloads,
  credentials, private evaluator truth, and full compact continuation packets.
- Quality comparator blocks faster-but-worse acceptance unless explicitly
  waived.
- Reducible-bucket report identifies which later groups are worth trying first.
- No default public route, MCP contract, checker semantics, or `done` semantics
  change.

BLOCKED_NEEDS_DECISION if:

- Implementation requires live provider spend, public route promotion, default
  MCP/profile changes, racing, or forbidden artifact persistence.

BLOCKED_NEEDS_LOCAL_VALIDATION if:

- A later approved live matrix cannot run due to credentials, backend slot,
  work-network guard, or provider access.

INTERMEDIATE_ONLY if explicitly approved:

- Tooling lands but dry-run/preflight/privacy/quality gates are incomplete.

Must not regress:

- `done`/`run_result.json` as cleanup success signal.
- Private/non-default `openai-agents-live`.
- Artifact privacy boundary.
- Existing Codex/Claude behavior.
- Report/checker generation.

Verification:

- Deterministic gates:
  - `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_summarize_live_run.py tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/reports/test_molmo_cleanup_report.py -q`
  - `.venv/bin/ruff check scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/summarize_live_run.py roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py tests/unit/agents/test_live_runtime.py tests/unit/molmo_cleanup/test_summarize_live_run.py`
- Integration gates:
  - matrix runner dry-run on the unified manifest
  - offline replay/fake-provider preflight
  - privacy/schema gate on synthetic and replayed artifacts
- Product run gates:
  - dry-run matrix command created by this slice, with no provider calls
- Local/live/manual gates:
  - later only: GPT/codex-env + MiMo/mify across `world-public-labels`,
    `camera-grounded-labels`, and `camera-raw-fpv`, after dry-run budget
    approval and `just dev::network-status`

Execution surface:

- Main session: root supervisor, owns scope and final complete/blocked
  judgment.
- Worker: none required for Group 0; optional later if implementation becomes
  slow.
- Worker-local goal: none.

To execute:

```text
/goal execute docs/plans/live-agent-runtime-sdk-spike.md with intuitive-flow
```

Approval gate: reply `LGTM`, `approve`, or `go ahead` to approve this
contract.

### Execution Preflight: Observability V1

Preflight status: DONE

Task source: this plan plus the 2026-06-09 observability grill.

Canonical source: `docs/plans/live-agent-runtime-sdk-spike.md`.

Route: durable `intuitive-flow`.

Goal: implement the formal live-agent observability V1 for the OpenAI Agents
SDK route while keeping the timing schema intent-neutral and extensible beyond
cleanup.

Scope:

- Rename the emitted timeline schema from `openai_agents_cleanup_timeline_v1`
  to `live_agent_timeline_v1`.
- Add run semantic identifiers to timing/timeline artifacts where available:
  `surface`, `intent`, `task_name`, `task_intent_mode`, `runtime`,
  `provider_profile`, `model`, and `evidence_lane`.
- Preserve current OpenAI Agents SDK-specific metrics without making those
  SDK-specific names the top-level cross-runtime contract.
- Add OpenAI Agents SDK span-level evidence, likely
  `openai-agents-spans.jsonl`, through SDK hooks or a trace processor if the
  SDK APIs expose that data without unsafe logging.
- Keep MCP/backend attribution, tool-error classification, timeout config,
  cached-tool-list config, and continuation attempts visible in
  `live_timing.json`.
- Update focused tests and any report/summarizer consumers that assert the old
  cleanup-specific schema name.

Non-goals:

- Do not promote `openai-agents-live` to the public/default route.
- Do not change MCP cleanup success semantics: `done`/`run_result.json` remains
  authoritative.
- Do not add private evaluator truth, credentials, or full sensitive prompts to
  observability artifacts.
- Do not require Codex CLI or Claude CLI to emit the full same schema in this
  slice unless the existing code path makes that low-risk and local.
- Do not treat repeated `list_tools` as a proven bottleneck without measured
  evidence; keep it as a measured optimization signal.

Definition of Done / acceptance criteria:

SUCCESS only if:

- `live_timing.json` contains `timeline.schema == "live_agent_timeline_v1"`.
- The timeline identifies the run semantics rather than encoding cleanup in the
  schema name.
- Existing latency attribution remains present and covered by tests.
- SDK span-level evidence is emitted, or the implementation records a concrete
  SDK API limitation and still preserves the V1 timeline contract.
- The required local/live acceptance gate below runs the OpenAI Agents SDK
  cleanup route on multiple evidence lanes and records the observability
  artifacts for each run.

PARTIAL if:

- Deterministic tests pass and schema/semantic fields are implemented, but one
  required live lane is blocked by provider credentials, local visual backend
  availability, or SDK span API limits; the missing gate and consequence must
  be recorded.

BLOCKED_NEEDS_DECISION if:

- Adding span hooks requires storing sensitive raw prompts, credentials, or
  private evaluator truth by default.
- The SDK tracing API cannot be used without changing provider credentials,
  external trace export behavior, or the MCP capability contract.

Must not regress:

- bounded incomplete-turn continuation;
- MCP client-session timeout override;
- `cache_tools_list` configurability and metrics;
- private/non-default route boundary;
- checker/report artifact generation;
- `done` as the only cleanup success signal.

Verification:

- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py -q`
- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`
- Required deterministic gate:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`
- Required lint gate:
  `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py roboclaws/household/report.py tests/unit/agents/test_live_runtime.py`
- Required local/live acceptance gate: run `openai-agents-live` cleanup
  sequentially on different evidence lanes, not as an optional exploratory
  follow-up. Minimum lanes:
  - `world-public-labels`:
    `just molmo::cleanup openai-agents-live world-public-labels 7 output/household/household-cleanup/openai-agents-observability-v1-world-public "帮我收拾这个房间" 5 127.0.0.1 18788`
  - `camera-grounded-labels` with deterministic projected labels:
    `just molmo::cleanup openai-agents-live camera-grounded-labels 7 output/household/household-cleanup/openai-agents-observability-v1-camera-grounded "帮我收拾这个房间" 5 127.0.0.1 18788 auto auto auto sim-projected-labels`
  - `camera-raw-fpv`:
    `just molmo::cleanup openai-agents-live camera-raw-fpv 7 output/household/household-cleanup/openai-agents-observability-v1-raw-fpv "帮我收拾这个房间" 5 127.0.0.1 18788`
- For each required live run, inspect `live_timing.json` and confirm the
  timeline schema, semantic identifiers, lane name, attribution buckets,
  tool-error metrics, and span artifact availability or recorded limitation.
  At least one required lane must pass the checker; any lane that fails due to
  model strategy or local backend behavior must still produce classified
  observability artifacts instead of failing silently.

Execution surface:

- Main session: root supervisor, owns scope, test/live-run gating, and final
  complete/partial/blocked judgment.
- Worker: none required initially.
- Worker-local goal: none.

Main-session `/goal` prompt:

```text
/goal execute docs/plans/live-agent-runtime-sdk-spike.md with intuitive-flow
```

Approval gate: reply `LGTM`, `approve`, or `go ahead` to approve this
preflight. To start durable execution from the main session, use the exact
`/goal` prompt above.

## Execution Log

- 2026-06-09: Implemented the first scaffold slice. Added
  `roboclaws.agents.live_runtime` with `LiveAgentRequest`,
  `LiveAgentResult`, `LiveAgentRuntime`, artifact discovery, and
  `live_status.json` normalization helpers. Added private experimental
  `OpenAIAgentsLiveRuntime` under `roboclaws.agents.drivers` using optional
  OpenAI Agents SDK imports, Streamable HTTP MCP configuration, SDK event/trace
  artifacts, and normalized failure/status output. Existing `codex` and
  `claude` live routes and public `just task::run` driver names were not
  changed.
- 2026-06-09: Superseded the scaffold-only dependency decision after the plan
  reopened for an operational cleanup proof. Final dependency decision: commit
  `openai-agents==0.17.4` as an optional `openai-agents` extra, and keep
  `openai-agents-live` private/non-default until maintainer review promotes it.
- 2026-06-09: Verification passed:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py`,
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`,
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py`,
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`,
  and `.venv/bin/ruff check roboclaws/agents/live_runtime.py roboclaws/agents/drivers/openai_agents_live.py tests/unit/agents/test_live_runtime.py`.
  Human-doc alignment updated `ARCHITECTURE.md` to name the new runtime
  contract; README/public command docs remain unchanged because no public route
  changed. No live OpenAI/Codex/Claude provider run was performed, per
  preflight.
- 2026-06-09: Reopened/refactored this plan from scaffold completion to
  operational completion. The stop condition is now: Roboclaws can actually use
  the OpenAI Agents SDK path to run a household cleanup job through the existing
  MCP/checker/report boundary, or the only remaining blocker is explicitly
  external provider credentials after dependency, runner, route, artifact, and
  mock/contract slices are complete.
- 2026-06-09: Ran one-off local SDK model probes after installing
  `openai-agents==0.17.4` into this checkout's `.venv` with `uv pip install`
  (no committed dependency metadata change). Direct Responses API probes passed
  for `codex-env` model `gpt-5.5` and `codex-mify` model `xiaomi/mimo-v2.5`.
  OpenAI Agents SDK `OpenAIResponsesModel` probes also passed for both targets.
  This establishes Responses as the first cleanup-runner interface target; Chat
  Completions remains a fallback/expansion path for non-Responses providers.
- 2026-06-09: Set `codex-env`/`gpt-5.5` as the default development and first
  live cleanup proof target for this plan. `codex-mify`/`xiaomi/mimo-v2.5`
  remains a secondary Responses compatibility target after the default route
  works, not a blocker for the first cleanup proof unless `codex-env`
  credentials are unavailable.
- 2026-06-09: Ran a grill-with-docs-batch saturation check. No additional
  user-facing decision questions are needed before implementation: the plan
  already protects the public route boundary, MCP contract, private-data
  boundary, cleanup `done` gate, and credential blocker semantics. Remaining
  choices are implementation defaults recorded here: use a committed optional
  `openai-agents` extra, keep the first SDK runner private/non-default, and use
  `codex-env` for default development and first live proof.
- 2026-06-09: Completed the operational dependency, runner, route, artifact,
  and proof slices. Added the committed optional dependency, implemented
  explicit `OpenAIResponsesModel` setup for `codex-env`/`codex-mify`, raised
  the SDK internal turn cap to the repo default `128`, added the private
  `openai-agents-live` runner/route, surfaced SDK artifacts in summaries and
  the operator console, and kept public `codex`/`claude` routes unchanged.
- 2026-06-09: Live proof passed with
  `just molmo::cleanup openai-agents-live smoke 7 output/household/household-cleanup/openai-agents-smoke-128 '帮我收拾这个房间' 5 127.0.0.1 18788`.
  Artifact:
  `output/household/household-cleanup/openai-agents-smoke-128/0609_1052/seed-7/`.
  The run finished with exit status 0, checker passed, `report.html` was
  generated, 5/5 targets were restored, sweep coverage was `1.0`, and
  `openai-agents-events.jsonl` / `openai-agents-trace.json` were present.
- 2026-06-09: Final focused verification passed:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py tests/unit/operator_console/test_state.py tests/unit/operator_console/test_launcher.py tests/unit/molmo_cleanup/test_ci_live_reports.py`,
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`,
  and `.venv/bin/ruff check roboclaws/agents/live_runtime.py roboclaws/agents/drivers/openai_agents_live.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py scripts/molmo_cleanup/summarize_live_run.py roboclaws/operator_console/state.py roboclaws/operator_console/launcher.py tests/unit/agents/test_live_runtime.py tests/unit/operator_console/test_state.py tests/unit/operator_console/test_launcher.py tests/contract/dev_tools/test_task_agent_just_recipes.py`.
- 2026-06-09: Completed Observability V1 implementation. The private
  `openai-agents-live` route now writes sanitized
  `openai-agents-spans.jsonl`, includes `live_agent_timeline_v1` in
  `live_timing.json`, and records semantic run identifiers for
  `surface=household-world`, `intent=cleanup`, `task_name=household-cleanup`,
  `task_intent_mode=default_cleanup`, `runtime=openai-agents-live`,
  `provider_profile=codex-env`, model `gpt-5.5`, and the active
  `evidence_lane`.
- 2026-06-09: Observability V1 live acceptance passed on
  `world-public-labels` at
  `output/household/household-cleanup/openai-agents-observability-v1-world-public/0609_2119/seed-7/`
  and `camera-grounded-labels` at
  `output/household/household-cleanup/openai-agents-observability-v1-camera-grounded/0609_2140/seed-7/`.
  Both runs finished with exit status 0, produced `run_result.json`,
  `report.html`, `live_timing.json`, `live_agent_timeline_v1`, and sanitized
  span metrics. Span end counts were 298 and 318 respectively.
- 2026-06-09: The `camera-raw-fpv` live acceptance run at
  `output/household/household-cleanup/openai-agents-observability-v1-raw-fpv/0609_2202/seed-7/`
  did not reach cleanup `done`/checker success. It produced
  `live_timing.json`, `live_agent_timeline_v1`, two sanitized span files, and
  764 span-end records across the initial SDK invocation plus one continuation.
  The run stopped with a provider-wrapped context-window failure after two
  grounded cleanup chains and repeated unresolved visual candidates. The SDK
  exception classifier now has a regression test so this wording is classified
  as `provider_context_failure` before the misleading HTTP 502 wrapper is
  treated as a transient upstream outage.
- 2026-06-09: Observability V1 focused verification passed:
  `./scripts/dev/run_pytest_standalone.sh tests/unit/agents/test_live_runtime.py -q`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/reports/test_molmo_cleanup_report.py -q`,
  `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools/test_task_agent_just_recipes.py -q`,
  and `.venv/bin/ruff check roboclaws/agents/drivers/openai_agents_live.py roboclaws/agents/live_runtime.py scripts/molmo_cleanup/run_live_openai_agents_cleanup.py tests/unit/agents/test_live_runtime.py tests/contract/dev_tools/test_task_agent_just_recipes.py`.
- 2026-06-10: Completed the Agent SDK performance optimization pass for the
  private `openai-agents-live` route. The runner now persists telemetry V2
  context/cache/context-growth metrics, private Agent SDK performance profiles,
  compact continuation state, compact label-lane prompts, raw-FPV budget
  classification, and manifest-driven comparison output. Public
  `run::surface` routing and the `done`/`run_result.json` cleanup success gate
  remain unchanged.
- 2026-06-10: Label-lane live validation passed for GPT/codex-env and MiMo/mify
  on seed 7, generated mess count 5. The comparison manifest at
  `docs/status/active/agent-sdk-perf-opt-0610-comparison-manifest.json`
  reports GPT `world-public-labels` improved from 20m26s to 8m30s and GPT
  `camera-grounded-labels` from 20m43s to 9m04s, both with checker-visible
  `run_result.json`. MiMo `world-public-labels` produced a new passing
  baseline-quality candidate at 6m45s against a failed-checker diagnostic
  baseline, so it is not a clean speedup claim. MiMo `camera-grounded-labels`
  passed but improved only from 9m29s to 9m08s, recorded as a provider/model
  profile limitation rather than a success against the 40% target.
- 2026-06-10: Raw-FPV safety validation first exposed a real implementation gap:
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/gpt-raw-fpv-budgeted/0610_0927/seed-7/`
  crossed the raw profile's 96k response-context hard limit inside one
  128-turn SDK attempt before the runner could classify it, and was interrupted
  deliberately. The raw-FPV profile now uses a lower per-attempt SDK turn cap
  so the runner regains control before provider context failure.
- 2026-06-10: Raw-FPV retry passed the Phase 5 safety gate at
  `output/household/household-cleanup/agent-sdk-perf-opt-0610/gpt-raw-fpv-budgeted-turncap/0610_0949/seed-7/`.
  It terminated with classified reason `raw_fpv_sdk_turn_budget_exhausted`,
  `max_input_tokens=67040` under the 96k hard limit,
  `context_window_failure_detected=false`, 40 response spans, and no
  `run_result.json` as expected for this safety-only phase.

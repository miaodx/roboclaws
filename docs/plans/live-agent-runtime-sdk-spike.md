---
plan_scope: live-agent-runtime-sdk-spike
status: DONE
source:
  - 2026-06-08 SDK deep research discussion
  - intuitive-reduce-entropy
  - inline intuitive-planning-loop
  - intuitive-preflight
last_reviewed: 2026-06-08
---

# Live Agent Runtime SDK Spike

## Status

DONE

## Decision Summary

Roboclaws should not treat OpenAI Agents SDK, Anthropic Claude Agent SDK, and Pi
SDK as symmetric replacements for the existing Codex and Claude Code live
routes.

The recommended direction is:

1. Keep the current Docker-backed `codex-live` and `claude-live` CLI routes as
   product/coding-agent baselines.
2. Define a Roboclaws-owned `LiveAgentRuntime` contract at the driver layer.
3. Add one experimental SDK runtime first: `openai-agents-live`.
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

- Connect to the existing Roboclaws MCP server when possible.
- Run the same household cleanup skill prompt through the SDK runtime.
- Emit SDK event/tracing/session artifacts into the run directory.
- Write the same normalized `live_status.json` and compatible timing/result
  artifacts expected by operator-console and checker paths.
- Preserve one-turn/no-runner-continuation behavior unless a later explicit
  handoff protocol is accepted.

Non-requirements:

- It does not need to outperform Codex CLI in the first spike.
- It does not need to support Claude or Pi.
- It does not need to be exposed as the default public driver.

### Phase 3: Compare And Decide

After mock/contract tests pass, optionally run one local provider proof.

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

Preflight status: IMPLEMENTED

Task source:

- User approval of the reduce-entropy recommendation, followed by
  main-session inline planning loop and preflight request.

Canonical source:

- `docs/plans/live-agent-runtime-sdk-spike.md`

Route:

- `$intuitive-refactor` through durable `$intuitive-flow`.

Goal:

- Add a Roboclaws-owned live-agent runtime contract and a first experimental
  OpenAI Agents SDK driver spike without changing existing Codex/Claude live
  route behavior.

Scope:

- Define the runtime contract under `roboclaws/agents/`.
- Keep current Codex/Claude CLI runners as baselines.
- Add or prepare focused tests proving current live status/result semantics are
  representable by the contract.
- Add the experimental OpenAI Agents SDK driver only after the contract is
  testable.
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
- No paid/live-provider validation unless separately approved.

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
- The OpenAI experimental driver is either implemented behind a non-default
  private/experimental route or explicitly left as the next gated slice with a
  concrete reason.
- Tests cover the contract and the preserved failure/status semantics.
- Dependency and route exposure decisions are recorded.

PARTIAL if:

- The runtime contract lands and tests pass, but the OpenAI SDK driver remains
  blocked by dependency, MCP transport, or provider validation decisions.

BLOCKED_NEEDS_DECISION if:

- Adding the OpenAI Agents SDK dependency requires choosing between a normal
  dependency and optional extra.
- Exposing `openai-agents-live` publicly is required for verification.
- Live provider validation is required to prove the claim.
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

- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/molmo_cleanup/test_ci_live_reports.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_state.py`
- `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `ruff check` on touched Python files.
- `ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup codex smoke`
  if routing metadata changes.
- No live OpenAI/Codex/Claude provider run is required unless separately
  approved.

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
- Agent-owned checkpoint/handoff MCP tool for explicit continuation.
- Operator-console retry UX for provider-transient failures.
- Live provider proof comparing Codex CLI baseline against OpenAI Agents SDK
  artifact and failure surfaces.

## Execution Log

- 2026-06-09: Implemented the first spike slice. Added
  `roboclaws.agents.live_runtime` with `LiveAgentRequest`,
  `LiveAgentResult`, `LiveAgentRuntime`, artifact discovery, and
  `live_status.json` normalization helpers. Added private experimental
  `OpenAIAgentsLiveRuntime` under `roboclaws.agents.drivers` using optional
  OpenAI Agents SDK imports, Streamable HTTP MCP configuration, SDK event/trace
  artifacts, and normalized failure/status output. Existing `codex` and
  `claude` live routes and public `just task::run` driver names were not
  changed.
- 2026-06-09: Dependency decision recorded: do not add `openai-agents` to
  `pyproject.toml` in this slice. The experimental runtime reports
  `reason=provider_config_failure`, `retryable=false` when the SDK is missing.
  Route exposure decision recorded: keep `openai-agents-live` private and
  non-default until a separately approved local provider proof compares it
  against the Codex CLI baseline.
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

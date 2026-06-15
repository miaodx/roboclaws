---
plan_scope: architecture-layer-contract-refresh
status: Implemented - architecture and agent guidance refreshed
created: 2026-06-15
last_reviewed: 2026-06-15
implementation_allowed: true
source:
  - user request to review current repo architecture after cleanup
  - intuitive-reduce-entropy repo entropy packet on architecture/source drift
  - user approval to keep server logic thin and refactor docs accordingly
  - current README.md / ARCHITECTURE.md / STATUS.md / AGENTS.md orientation
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - AGENTS.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/human/coding-agent-nav-server.md
  - docs/human/evaluation.md
  - docs/human/architecture-hygiene-review.md
  - docs/plans/refactor-retire-ai2thor-vlm-direct.md
  - docs/plans/2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
  - docs/adr/0138-use-detector-only-visual-grounding-sidecar.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
---

# Architecture Layer Contract Refresh

## Goal

Refresh the repo's architecture source of truth after the recent cleanup work so
future changes have an explicit architectural home before implementation.

The target state is:

- `ARCHITECTURE.md` clearly states that VLM Direct and AI2-THOR-era direct demo
  routes are retired historical context, not active launch axes.
- The active agent strategy is explicit: stabilize coding-agent routes and the
  OpenAI Agents SDK route first; treat OpenClaw, Hermes-style, and similar
  high-level agent frameworks as planned higher-level clients, not current
  product axes.
- Thin runtime/server adapters are a named infrastructure boundary instead of
  being implied across MCP server docs, live-agent launchers, operator console
  code, and eval bridges.
- Eval suites remain first-class beside product runs and validation gates, with
  live eval behavior summarized in the root architecture doc.
- `AGENTS.md` requires future additions to name their architecture layer, or to
  trigger an architecture discussion before the implementation lands.

## Why Now

The repo has already done the hard cleanup:

- current product shape is centered on `surface=household-world` and
  `surface=planner-proof`;
- `agent_engine=codex-cli`, `claude-code`, and experimental
  `openai-agents-sdk` are the active live-agent routes;
- OpenClaw is registered only as validation-required until off-work-network
  Gateway proof is green;
- detector-only visual grounding has replaced hosted VLM Direct camera-labeler
  and refiner routes;
- eval suites exist under `evals/` and `roboclaws/evals/`.

The remaining entropy is mostly documentation and agent-guidance drift. The
root architecture ladder still moves from agent engine to skill/profile/MCP
without naming the thin server/runtime adapter boundary that now exists in
code. That makes future changes likely to rediscover where launch catalog,
live runtime, MCP server process lifecycle, operator console, and live eval
bridge belong. The fix must not turn server code into a new behavior layer:
Roboclaws should remain MCP- and skill-first.

## Current Evidence

Current architecture docs already record some of the desired state:

- `ARCHITECTURE.md` lists AI2-THOR, direct-VLM, and route-card demos as retired
  historical context.
- `ARCHITECTURE.md` lists `codex-cli`, `claude-code`,
  `openai-agents-sdk`, and `direct-runner`, with `openclaw-gateway` marked
  validation-required.
- `docs/human/evaluation.md` describes product runs, validation matrix, eval
  suites, and harness recipes as distinct proof layers.
- `docs/human/coding-agent-nav-server.md` describes the direct coding-agent
  household MCP lifecycle and the private server facade.

Current code already has a thin server/runtime adapter boundary:

- `roboclaws/launch/catalog.py` resolves public launch axes and lowers them to
  private dispatcher commands.
- `roboclaws/agents/live_runtime.py` defines provider-neutral live-agent
  request/result contracts and MCP server endpoint metadata.
- `roboclaws/cli/agent_server.py` routes supported coding-agent MCP server
  targets: `household-world.cleanup` and `household-world.map-build`.
- `roboclaws/cli/household_agent_server.py` and
  `roboclaws/cli/agibot_map_build_agent_server.py` assemble domain-specific MCP
  server processes.
- `roboclaws/operator_console/server.py` and
  `roboclaws/operator_console/launcher.py` provide the local operator HTTP/API
  surface, route readiness, locks, and fixed `just run::surface` launch argv.
- `roboclaws/evals/live_runtime.py` and `roboclaws/evals/runner.py` bridge live
  eval trials through product `run::surface` routes and grade resulting
  artifacts.

## Target Architecture Ladder

Update the root model to make the thin adapter boundary explicit:

```text
Open-ended goal
  -> Runnable Surface, World / Scene, Backend, Intent, and optional Preset
  -> Agent Skill
  -> Agent Engine and Provider Profile
  -> Capability Profile requirements
  -> MCP Capability Contract and Tools
  -> Thin Runtime / Server Adapter
  -> Backend Adapter / Environment Primitive
  -> Artifacts, Reports, and Eval Suites
```

This ladder separates three concepts that currently get blurred:

- **Agent engine**: the client/runtime family, such as Codex CLI, Claude Code,
  OpenAI Agents SDK, direct-runner, or validation-required OpenClaw Gateway.
- **MCP capability contract/tools**: bounded public robot capability contract for
  observe, map, navigate, pick/place, lifecycle completion, and related tools.
- **Thin runtime/server adapter**: transport and lifecycle plumbing for launch
  catalog lowering, live-agent status, MCP server process lifecycle,
  operator-console run control, locks, ports, output dirs, and eval live
  bridges.

Server adapters should be intentionally small. They may bind transports and
route requests to domain contracts; they should not own cleanup/search/map-build
strategy, prompt policy, private scorer truth, benchmark-specific hints, or
opaque multi-tool task shortcuts. If behavior wants to grow inside a server,
first ask whether it belongs in a skill, MCP capability response, backend
adapter, eval grader, or report.

## Proposed Documentation Changes

### Slice 1: Refresh `ARCHITECTURE.md`

Update the core model and major-stack sections:

- Add `Thin Runtime / Server Adapter` to the core architecture ladder.
- Define its owned responsibilities:
  - launch catalog resolution;
  - agent runtime request/result normalization;
  - MCP server target routing and process lifecycle;
  - operator-console HTTP/API orchestration;
  - eval live-run bridge through product routes.
- Define what it must not own:
  - task strategy;
  - prompt policy and agent recovery playbooks;
  - scoring or private evaluator truth;
  - benchmark-specific hints;
  - opaque multi-tool task shortcuts.
- Rename or clarify the MCP section so "MCP Tools" does not accidentally imply
  ownership of server lifecycle, route locks, provider status, or eval polling.
- Strengthen the active-agent direction:
  - current: coding-agent routes and OpenAI Agents SDK;
  - later: OpenClaw / Hermes-style high-level frameworks after lower routes are
    stable and verified.
- Keep direct-VLM and AI2-THOR retirement as historical context and avoid
  reviving them as active architecture options.
- Add a short eval root summary:
  - deterministic evals run by default;
  - live-agent eval identity can be recorded without execution;
  - `live_execution=run` is opt-in for real provider/runtime runs;
  - failures classify provider/runtime blockers separately from agent behavior.

### Slice 2: Add the Architecture-Fit Rule to `AGENTS.md`

Add a repo-wide rule near the technical constraints or planning workflow:

```text
Every new behavior, surface, server adapter, agent engine, MCP tool, skill,
backend, eval suite, report, or artifact contract must name its owning
architecture layer in the plan, PR note, or doc update. If it does not fit an
existing layer, stop and update ARCHITECTURE.md or record a focused
architecture decision before implementation.
```

The rule should also say where common additions belong:

- surfaces/presets -> launch catalog and domain `tasks.py`;
- agent engines/provider profiles -> `roboclaws/launch/agent_engines.py` and
  provider registry;
- thin server/runtime adapters -> live runtime, agent server router, operator
  console, or eval live bridge, and only for transport/lifecycle concerns;
- MCP robot capabilities -> domain MCP modules and capability profiles;
- skills -> `skills/` behavior packages and skill manifests;
- evals -> `evals/` and `roboclaws/evals/`;
- backend primitives -> backend adapters, not public task names.

Add an explicit guard that server code is not a place to hide strategy. If a
server change starts carrying task policy, move it to a skill or public MCP
capability contract before implementation.

### Slice 3: Cross-Link Human Docs Without Expanding Them

Keep detailed docs where they already belong:

- `docs/human/mcp-skills-and-semantic-profiles.md` remains the detailed
  skill/profile/MCP boundary reference.
- `docs/human/coding-agent-nav-server.md` remains the coding-agent MCP server
  lifecycle guide.
- `docs/human/evaluation.md` remains the eval-suite and validation-boundary
  reference.
- `docs/human/architecture-hygiene-review.md` remains the lightweight review
  checklist.

Only add or adjust links if a reader following `ARCHITECTURE.md` cannot find
the relevant detailed guide.

## Non-Goals

- Do not change product behavior, launch routes, tests, or provider defaults.
- Do not delete OpenClaw code or private recipes in this slice.
- Do not rework the operator console implementation.
- Do not add a third-party eval framework.
- Do not rename existing server targets or artifact schemas.
- Do not reopen VLM Direct / hosted refiner camera-labeler routes.
- Do not convert this doc refresh into broad documentation polish.

## Acceptance Criteria

- `ARCHITECTURE.md` has a named thin runtime/server adapter boundary with
  current code owners and explicit non-ownership of task strategy.
- `ARCHITECTURE.md` states the active staging clearly:
  coding-agent routes and Agent SDK first; OpenClaw/Hermes-style frameworks
  later; direct-VLM retired.
- Eval docs in `ARCHITECTURE.md` align with `docs/human/evaluation.md` and do
  not imply live providers run unless `live_execution=run`.
- `AGENTS.md` requires every future addition to name an architecture layer or
  explicitly update the architecture before implementation, and states that
  server logic must remain transport/lifecycle plumbing.
- No existing command examples are moved away from the canonical
  `just run::surface ...` grammar.
- The change is doc-only and leaves existing untracked plan work untouched.

## Preflight Contract

Preflight status: DRAFT.

Task source: plan path plus conversation.

Canonical source: `docs/plans/2026-06-15-architecture-layer-contract-refresh.md`.

Route: main direct.

Goal: finalize the docs-only architecture-layer refresh that keeps server logic
thin and reinforces MCP/skill-first ownership.

Scope:

- Keep `ARCHITECTURE.md` updated with `Thin Runtime / Server Adapter`.
- Keep `AGENTS.md` guardrails for architecture-layer ownership and thin server
  logic.
- Keep this plan doc as the execution record.
- Preserve unrelated dirty work.

Non-goals:

- No production code changes.
- No server implementation refactor.
- No launch route, MCP tool, eval harness, OpenClaw, or provider behavior
  changes.
- No live/provider/simulator/Docker/GPU gates.

Context:

- Must read: `ARCHITECTURE.md`, `AGENTS.md`, and this plan.
- Useful: `docs/human/mcp-skills-and-semantic-profiles.md`,
  `docs/human/coding-agent-nav-server.md`, `docs/human/evaluation.md`, and
  `docs/human/architecture-hygiene-review.md`.
- Avoid unless needed: historical plans/ADRs, `.planning/`, and output
  artifacts.

Acceptance:

- Success: docs state server is transport/lifecycle plumbing, strategy belongs
  in skills, MCP promotion remains bounded, and eval live runs are opt-in via
  `live_execution=run`.
- Blocked needs decision: none.
- Blocked needs local validation: none.
- Intermediate only: none.
- No regressions: canonical `just run::surface` guidance and retired
  direct-VLM/AI2-THOR status remain unchanged; unrelated dirty files are not
  touched.

Verification:

- Deterministic: `git diff -- ARCHITECTURE.md AGENTS.md docs/plans/2026-06-15-architecture-layer-contract-refresh.md`.
- Deterministic: focused `rg` for thin-server, direct-VLM, OpenClaw, Agent SDK,
  and `live_execution` terms.
- Integration: optional
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_eval_just_recipe.py tests/contract/mcp/test_semantic_profiles.py`.
- Product run: none, docs-only.
- Local/live/manual: none.
- Optional: broader docs scan excluding historical archives.

Execution:

- Main: final doc polish, focused verification, and scoped commit.
- Worker: none.
- Worker goal: none.

Approved execution command:

```text
/goal execute docs/plans/2026-06-15-architecture-layer-contract-refresh.md with intuitive-flow
```

## Suggested Verification

Doc-only focused checks:

```bash
git diff -- README.md ARCHITECTURE.md AGENTS.md docs/human docs/plans
rg -n "direct-VLM|VLM Direct|AI2-THOR|openclaw-gateway|openai-agents-sdk|Thin Runtime / Server Adapter|Server logic stays thin|live_execution" README.md ARCHITECTURE.md STATUS.md AGENTS.md docs/human
```

If tests are desired for confidence, run the existing lightweight doc/contract
checks that cover launch guidance:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/test_eval_just_recipe.py tests/contract/mcp/test_semantic_profiles.py
```

Do not run live-provider, OpenClaw Gateway, simulator/GPU, or real-robot gates
for this documentation-only refresh.

## Execution Notes

The implementation should be a small documentation change. If the edit reveals
that code behavior and docs disagree about a public route, stop and split that
into a separate behavior plan instead of silently fixing code under this doc
refresh.

Recommended order:

1. Update `ARCHITECTURE.md` core ladder and layer definitions.
2. Add the architecture-fit rule to `AGENTS.md`.
3. Add minimal cross-links to human docs if needed.
4. Run the focused searches above.
5. Record any discovered behavior/doc disagreement as a follow-up candidate.

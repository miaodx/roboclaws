---
plan_scope: sdk-only-live-agent-engine
status: Implemented
created: 2026-06-23
last_reviewed: 2026-06-24
implementation_allowed: true
source:
  - user request: less is more, reduce Roboclaws agent-architecture maintenance
  - intuitive-reduce-entropy discussion on retiring Codex/Claude coding-agent support
  - user clarification: keep OpenClaw as a future abstraction layer
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - docs/human/evaluation.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/plans/live-agent-runtime-sdk-spike.md
  - docs/plans/2026-06-14-eval-driven-architecture.md
  - docs/plans/2026-06-16-open-ended-eval-matrix-expansion.md
  - docs/plans/refactor-live-agent-runner-boundary.md
  - docs/plans/refactor-coding-agent-provider-registry.md
---

# SDK-Only Live Agent Engine Cleanup

## Goal

Make OpenAI Agents SDK the only actively supported live-agent product engine in
Roboclaws, while keeping `direct-runner` for deterministic/local proof and
keeping OpenClaw as a future abstraction layer.

The target public shape is:

```text
Current active engines:
  direct-runner          deterministic product/eval proof
  openai-agents-sdk      live-agent product/eval route

Retired active engines:
  codex-cli              remove from public support and active tests
  claude-code            remove from public support and active tests

Kept future abstraction:
  openclaw-gateway       not deleted; remains validation-required/future work
```

This is a reduction plan, not a compatibility migration. Known in-repo callers,
docs, tests, recipes, operator-console rows, eval-harness rows, and examples
should move to the target shape. Do not add aliases or fallback branches for
the old `codex-cli` / `claude-code` engines unless the human explicitly asks.

Implementation default: remove Codex/Claude from the active engine registry and
add one explicit retired-engine rejection contract shared by launch, eval
identity, eval-harness selection, and operator-console routing. Do not keep
retired engines as normal `AgentEngineSpec` rows with a softer availability
state; that preserves the same drift under a new label.

## Why Now

Roboclaws has carried three live-agent routes at once:

- Docker-backed Codex CLI;
- Docker-backed Claude Code;
- Python-native OpenAI Agents SDK.

That made sense while the project was learning which runtime should own MCP
robot control. The current direction is different: OpenAI Agents SDK is the
runtime that will keep receiving active development, live eval work, tracing,
provider-profile tuning, and operator-console improvements.

Keeping Codex/Claude coding-agent support active now increases maintenance
without matching product value:

- public docs still teach Codex/Claude examples;
- launch catalog and operator-console rows still advertise those engines;
- provider readiness logic has engine-specific branches;
- eval runtime carries Codex detached-run polling behavior;
- Docker image and wrapper scripts must stay valid;
- tests keep proving routes that are no longer the future product direction.

If these routes are no longer tested frequently, they should not remain active
support surfaces. A route that appears supported but is not exercised creates
false confidence.

## Architecture Layer

This plan touches existing layers only:

- Agent Engines And Provider Profiles: make `openai-agents-sdk` the only active
  live-agent engine.
- Runnable Surfaces And Presets: update public examples and route validation.
- Thin Runtime / Server Adapters: remove Codex/Claude runner plumbing that only
  exists for active product launch.
- Operator Console: remove Codex/Claude launch rows, readiness branches, and
  route affordances.
- Eval harness / eval suites: keep live eval support focused on
  `openai-agents-sdk`; keep deterministic direct-runner gates.
- Harness recipes: remove or retire coding-agent Docker recipes from active
  validation.

Non-decision:

- This plan does not change the MCP robot capability contract.
- This plan does not move cleanup/map-build strategy into server adapters.
- This plan does not delete OpenClaw.
- This plan does not decide the final OpenClaw integration design.

## Keep OpenClaw

OpenClaw stays in the repo as a future abstraction layer.

Required intent:

- Keep OpenClaw docs, ADR/history, bootstrap knowledge, and guarded recipes
  that are useful for future reactivation.
- Keep `openclaw-gateway` out of the normal active product engine list until it
  has a fresh validation plan and proof gates.
- Do not let this cleanup delete OpenClaw source paths just because Codex and
  Claude Code are being retired.
- Do update wording if needed so OpenClaw is clearly "future /
  validation-required", not current active support.

OpenClaw should become active again only through a separate plan that defines
its abstraction-layer role, supported product surfaces, proof gates, network
constraints, and operator workflow.

## Agibot Dependency

Agibot map-build is currently being moved toward the SDK route by another
agent. This plan must not duplicate or steal that work.

Before landing Codex/Claude retirement, check the current Agibot route state:

- If the other agent has completed SDK support for Agibot map-build, migrate
  this cleanup to that SDK route and delete remaining Codex-only route entries.
- If the other agent is still in progress, do not rush a compatibility bridge.
  Keep this plan ready, and land it after that work merges.
- If the human wants this cleanup landed before the Agibot SDK route is ready,
  explicitly park Agibot live map-build as not active rather than preserving a
  Codex-only exception.

Stop gate:

- Do not leave a public or operator-console Agibot route that requires
  `agent_engine=codex-cli` after this plan is marked implemented.
- Run this stop gate during preflight, before broad docs/code deletion starts.
  Agibot must not become a late surprise after the only live map-build path has
  already been removed.

## Provider Profile Boundary

Retiring a product engine is not the same as deleting a provider profile.

Some current route names, especially `codex-router-responses`, are also used by
OpenAI Agents SDK runs. This cleanup should remove Codex engine support from
provider metadata, not delete SDK-capable provider profiles just because their
current public profile string contains `codex`.

Required behavior:

- Keep provider routes that `openai-agents-sdk` can use.
- Remove `codex-cli` and `claude-code` from `supported_engines`,
  `per_engine_status`, default-provider maps, readiness branches, and CLI
  helpers.
- If a provider profile name is misleading after Codex retirement, treat rename
  as a separate public-contract decision unless the implementation can migrate
  all known in-repo callers without introducing aliases.
- Eval identity and reports should record the selected SDK provider/model
  without implying the retired Codex engine is active.

## Scope

### In Scope

- Remove `codex-cli` and `claude-code` from active public examples.
- Remove `codex-cli` and `claude-code` from normal launch validation hints and
  supported active engine lists.
- Remove Codex/Claude operator-console routes and readiness branches.
- Remove Codex/Claude live eval rows, or convert their expectations to
  historical/retired evidence.
- Remove Codex/Claude runner scripts from active product launch paths.
- Remove coding-agent Docker image/wrapper recipes from active validation.
- Update tests so they prove the SDK-only live-agent contract instead of
  preserving old engines.
- Keep `direct-runner` examples for deterministic map-build, cleanup, planner
  proof, and cheap eval gates.
- Keep OpenAI Agents SDK examples for open-ended and live-agent product routes.

### Out Of Scope

- Deleting OpenClaw.
- Reworking OpenClaw into the new abstraction layer.
- Building the Agibot SDK route if another agent is already doing it.
- Removing historical docs, retrospectives, or archived plan evidence just
  because they mention Codex/Claude/OpenClaw.
- Rewriting the MCP server contract.
- Adding a new generic live-agent abstraction unless it replaces more code than
  it adds.
- Preserving Codex/Claude compatibility for external users.

## Target Contract

Public docs should teach:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=openai-agents-sdk provider_profile=<supported-sdk-profile> prompt="find something useful to drink"
just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run
```

Launch validation should reject removed active engines loudly:

```text
unsupported agent_engine 'codex-cli'
unsupported agent_engine 'claude-code'
expected openai-agents-sdk|direct-runner
```

If OpenClaw remains addressable by maintainer-only recipes, errors and docs
must distinguish it from active engines:

```text
openclaw-gateway is validation-required future abstraction work, not a current
active product engine
```

## Implementation Slices

### Slice 1: Contract And Docs

- Update `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`, `just/README.md`, `docs/human/evaluation.md`, and current human
  docs so active examples use only `direct-runner` or `openai-agents-sdk`.
- Remove the coding-agent household MCP guide from current human entry points,
  or rename it as historical/retired if it is still useful.
- Keep OpenClaw docs discoverable as future/validation-required material.
- Update wording from "coding-agent routes and OpenAI Agents SDK route" to
  "OpenAI Agents SDK live route plus deterministic direct-runner proof".
- Mark the older SDK spike and live-runner-boundary plans as superseded for the
  Codex/Claude-baseline assumption. They remain useful history, but they must
  not keep saying Docker-backed Codex/Claude are current baselines.

Acceptance:

- A new reader following current docs is not sent to Codex CLI or Claude Code.
- OpenClaw is not deleted or described as active product support.
- Current human evaluation docs no longer describe detached Codex artifact
  polling as a live eval behavior to maintain.

### Slice 2: Launch Catalog And Public Route Validation

- Remove `codex-cli` and `claude-code` from active `AgentEngineSpec` entries.
- Add one central retired-engine rejection helper or equivalent contract used
  by launch normalization, eval identity/preflight, eval-harness selection, and
  operator-console route validation.
- Update launch-catalog hints and removed-axis errors to name only current
  active engines.
- Update provider-profile validation so SDK profiles remain supported and old
  Codex/Claude engine/profile combinations fail loudly.
- Prune provider-registry engine metadata without deleting provider profiles
  still used by `openai-agents-sdk`.
- Remove Codex-specific map-build backend helper behavior if it exists only for
  `agent_engine=codex-cli`.

Acceptance:

- `agent_engine=openai-agents-sdk` resolves for supported live surfaces.
- `agent_engine=direct-runner` resolves for deterministic surfaces.
- `agent_engine=codex-cli` and `agent_engine=claude-code` fail with actionable
  retired-engine errors.
- Retired-engine failures are consistent across public launch, eval preflight,
  and eval-harness rows; they are not reported as missing Docker, missing
  provider keys, or generic unsupported axes.

### Slice 3: Operator Console

- Remove Codex/Claude route rows from `roboclaws/operator_console/routes.py`.
- Remove provider readiness branches that only serve Codex/Claude.
- Remove UI affordances, status parsing, handoff/resume flags, command previews,
  and tests that preserve Codex/Claude route IDs.
- Keep SDK route rows and direct-runner utility rows.
- Preserve OpenClaw only if it is maintainer/future scoped and not shown as a
  normal enabled console route.

Acceptance:

- `just console::run` exposes SDK live-agent routes and direct deterministic
  rows only.
- Existing route validation tests fail if Codex/Claude rows come back.
- Operator console still shows OpenClaw only according to future/guarded scope,
  if it is shown at all.

### Slice 4: Runner Scripts, Docker Tooling, And Just Recipes

- Remove Codex/Claude live runner scripts from active recipe dispatch.
- Retire `Dockerfile.coding-agents`, `scripts/dev/coding_agent_docker.sh`, and
  coding-agent toolchain env files if no remaining active route uses them.
- Remove `just code::*` or convert it to explicitly historical/manual debug
  documentation if the human wants to keep a local debugging hook.
- Remove `run_live_codex_agibot_map_build.py` only after the Agibot SDK route
  is merged or the route is explicitly parked.
- Keep OpenAI Agents SDK runner scripts and performance/profile helpers.

Acceptance:

- Public `just run::surface ... agent_engine=openai-agents-sdk ...` still runs
  through the SDK runner.
- Public `just run::surface ... agent_engine=codex-cli|claude-code ...` does
  not launch wrappers, Docker, tmux, or hidden fallback paths.
- No active test depends on the coding-agent Docker image.

### Slice 5: Eval Harness And Reports

- Remove Codex/Claude live eval rows from default/recommended active matrices.
- Keep SDK live eval rows and direct-runner deterministic suites.
- Update eval identity/preflight packets so retired engines are rejected or
  classified as retired, not blocked-on-env.
- Remove Codex-specific detached-run polling from live eval behavior once no
  active live route can detach that way.
- Update live report rendering if it assumes Codex/Claude attempts are current.
- Keep historical report artifacts readable when practical, but do not preserve
  old launch behavior only for old reports.

Acceptance:

- `just agent::eval recommend plan=docs/plans/2026-06-23-sdk-only-live-agent-engine.md budget=focused`
  recommends SDK/direct-runner gates, not Codex/Claude live gates.
- `just agent::eval execute ... budget=focused` can run deterministic gates
  without provider launches by default.
- Opt-in live execution targets `openai-agents-sdk` only.
- Before Slice 5 lands, current `agent::eval recommend` may still select Codex
  rows from this plan text. Treat that as expected evidence of what Slice 5 must
  change, not as proof that the plan is invalid.

### Slice 6: Tests And Deletion Sweep

- Update unit and contract tests that currently assert Codex/Claude route
  availability.
- Delete tests whose only purpose is proving Codex/Claude active support.
- Add focused tests for retired-engine rejection and SDK-only route visibility.
- Run a final search for active `codex-cli`, `claude-code`,
  `coding-agent`, `run_live_codex`, and `run_live_claude` references.
- Classify remaining references as:
  - historical/retrospective;
  - OpenClaw future context;
  - retired-engine error text;
  - current bug to remove.

Acceptance:

- Remaining current docs and active code do not advertise Codex/Claude as
  supported engines.
- Remaining historical references are clearly historical.

## Verification

Recommended deterministic gates:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/unit/evals
./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents
ruff check .
ruff format --check .
```

Recommended eval-harness gate:

```bash
just agent::eval recommend plan=docs/plans/2026-06-23-sdk-only-live-agent-engine.md budget=focused
just agent::eval execute plan=docs/plans/2026-06-23-sdk-only-live-agent-engine.md budget=focused
```

Optional live gate after deterministic proof and healthy provider route:

```bash
just agent::eval suite=open_ended_goals budget=focused agent_engine=openai-agents-sdk live_execution=run
```

Do not run OpenClaw proof as part of this plan. OpenClaw needs its own future
reactivation plan.

## Stop Gates

Stop and ask before implementation continues if:

- the Agibot SDK route is not ready and the human does not want to park Agibot
  live map-build;
- a current production route still has no SDK replacement and is explicitly
  needed by the human;
- deleting coding-agent Docker tooling would remove a separate explicitly
  requested local debugging workflow;
- OpenClaw code would need to be deleted to make tests pass;
- SDK live route cannot pass the focused open-ended eval once provider/runtime
  capacity is healthy.

## Done Definition

- Public current docs name SDK/direct-runner as the supported active engines.
- `codex-cli` and `claude-code` cannot be launched through current public
  surfaces.
- Operator console no longer exposes Codex/Claude active rows.
- Eval-harness recommendations no longer include Codex/Claude live rows by
  default.
- Coding-agent Docker runtime is not required by active tests or active demo
  workflows.
- OpenClaw remains in the repo as a guarded future abstraction layer.
- Agibot map-build is either SDK-backed or explicitly parked as inactive; it is
  not a Codex-only exception.

## Implementation Outcome

Implemented on 2026-06-24.

- Public launch validation rejects `codex-cli` and `claude-code` with the
  shared retired-engine message.
- `openai-agents-sdk` is the only active live-agent engine in launch catalog,
  provider registry, operator-console routes, and eval-harness live rows.
- Agibot G2 Map 12 map-build now routes through
  `scripts/molmo_cleanup/run_live_openai_agents_agibot_map_build.py`.
- Operator console removed Codex/Claude active rows and stale provider fields;
  SDK routes use route metadata for provider profiles.
- OpenClaw remains present as validation-required future abstraction work, not
  a current public product engine.

Verification run:

```bash
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console tests/contract/dev_tools/test_task_agent_just_recipes.py tests/unit/molmo_cleanup/test_live_openai_agents_agibot_map_build.py tests/unit/molmo_cleanup/test_live_codex_agibot_map_build.py tests/unit/evals/test_eval_harness_selector.py tests/unit/evals/test_eval_runner.py tests/unit/providers/test_provider_catalog.py tests/unit/launch
.venv/bin/ruff check roboclaws/operator_console tests/unit/operator_console tests/contract/dev_tools/test_task_agent_just_recipes.py tests/contract/dev_tools/household_surface_trace.py scripts/molmo_cleanup/run_live_openai_agents_agibot_map_build.py tests/unit/molmo_cleanup/test_live_openai_agents_agibot_map_build.py roboclaws/agents/provider_registry.py roboclaws/evals/agent_identity.py roboclaws/evals/live_runtime.py roboclaws/household/tasks.py roboclaws/launch/agent_engines.py roboclaws/launch/catalog.py roboclaws/launch/intents.py tests/unit/launch/test_environment_setup_catalog.py skills/eval-harness/scripts/eval_harness_rows.py skills/eval-harness/scripts/run_eval_harness.py skills/eval-harness/scripts/select_eval_harness.py tests/unit/evals/test_eval_harness_selector.py tests/unit/evals/test_eval_runner.py tests/unit/providers/test_provider_catalog.py
```

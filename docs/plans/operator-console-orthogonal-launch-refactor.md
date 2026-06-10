---
plan_scope: operator-console-orthogonal-launch-refactor
status: proposed
source:
  - 2026-06-10 operator-console UI abstraction discussion
  - intuitive-reduce-entropy
workflow: pre-gsd plan; implement later through intuitive-flow
---

# Operator Console Orthogonal Launch Refactor

## Goal

Refactor the operator console and launch catalog so operators choose independent
axes instead of flattened route cards:

```text
World / scene
  -> Backend runtime
  -> Task intent
  -> Agent engine
  -> Provider / model profile
  -> Evidence lane / perception
  -> Scenario setup
  -> Launch plan
```

The product goal is a console where the left rail answers "which world or scene
will this run happen in?" and the setup panel answers "which backend should run
it, what should the agent do, which engine should drive it, and what
evidence/configuration should it use?"

## Current Problem

The shipped console route list mixes abstraction levels:

- `MuJoCo Cleanup` and `MuJoCo Map Build` are shown as separate route cards,
  even though MuJoCo is a backend/runtime and cleanup/map-build are task
  intents.
- Codex and Claude are embedded in route IDs instead of selected as agent
  engines.
- Provider/model choice is partly route-specific UI, partly environment
  variable override.
- OpenAI Agents SDK exists as a private/non-default live runtime, but the
  console has no way to select it.
- The public launch model has moved toward `surface + intent`, but the Python
  catalog still preserves `task::run` legacy task names and immediately lowers
  canonical runs into `agent::run <legacy-task> <driver> <mode>`.

The result is recurring rediscovery: humans and agents have to infer whether a
label is a world/scene, a backend runtime, a task intent, an agent engine, or a
model route.

## Target Interaction Model

### Left Rail: World / Scene

The route rail becomes a world/scene rail. Initial entries:

| World / Scene | Supported backend(s) | Initial state |
| --- | --- | --- |
| MolmoSpaces rooms | `mujoco`, `isaaclab` where available | enabled |
| Agibot G2 map / real robot site | `agibot-gdk` | map-build enabled with context/safety gates; cleanup blocked |
| B1 / Gaussian digital-twin scenes | `isaaclab` today | enabled or experimental for open-ended navigation when a runnable action exists |
| Genesis / visual-only scene-camera scenes | preview/report backend only | hidden unless there is a concrete preview/report/run action |

The world card should show readiness and available backends. Backend-specific
resource locks, gates, and requirements appear after a world is selected. The
world rail should not duplicate task names.

MolmoSpaces has many rooms/scenes, so the world rail should be backed by a
searchable world catalog rather than hard-coded task cards. A v1 console can
start with a curated subset, but the catalog shape should support search,
filtering, and default worlds without changing the launch grammar.

### Setup Panel: Task And Runtime Axes

Task intent:

- `map-build`
- `cleanup`
- `open-ended`

Agent engine:

- `codex-cli`
- `claude-code`
- `openai-agents-sdk` with an `experimental` badge

Console primary agent engines are Codex CLI, Claude Code, and experimental
OpenAI Agents SDK. `direct-runner` may remain in catalog/public CLI for
deterministic routes, but it is not a primary operator-console engine.

Provider / model profile:

- Codex CLI: `codex-env` / GPT, `mify` / MiMo
- Claude Code: `kimi-anthropic`, `mimo-anthropic`, `mify-anthropic`
- OpenAI Agents SDK: `codex-env` / GPT, `mify` / MiMo

Evidence lane / perception:

- `world-oracle-labels`
- `world-public-labels`
- `camera-grounded-labels`
- `camera-raw-fpv`

Scenario setup:

- `baseline`
- `relocate-loose-objects`
- `relocate-cleanup-related-objects`

Seed stays visible as scenario seed. Baseline must state that it does not
relocate objects; relocation setups also use the seed to choose what moves.

## Launch Catalog Target Model

Add orthogonal launch metadata instead of making the console own hand-written
route cards.

The public launch model should also move to these axes. `run::surface` may keep
its recipe name, but the supported public arguments should evolve from the
overloaded `driver=` token toward explicit launch fields such as `world=`,
`backend=`, `agent_engine=`, and `provider_profile=`. Do not keep legacy task
IDs as a public or catalog-level compatibility layer. Runner class is internal
derived metadata, not a public selector.

This grammar migration is repo-wide for active public routes, not only the
operator console. Active docs and tests should not continue to teach `driver=`
for AI2-THOR, OpenClaw, VLM, household, or smoke routes. Historical plans and
retrospectives may keep old command text when clearly historical.

Public `world=` values should be operator-facing room/map/scene ids such as
`molmospaces/val_0`, `b1-map12`, or `agibot-g2/map-12`. Public `backend=`
values should be runtime names such as `mujoco`, `isaaclab`, or `agibot-gdk`,
not implementation ids such as `molmospaces_subprocess`. Backend implementation
names remain resolved metadata. `scenario_setup` is a direct public rename of
the old `environment_setup` concept; do not keep a public alias.
`scenario_setup` is a household-world setup axis; do not show relocation setup
controls for visual-only, AI2-THOR, planner-proof, or other non-household
surfaces.

Gaussian is a world/scene source before it is a backend. If current Gaussian or
B1 digital-twin support runs through Isaac, represent it as `world=<gaussian or
b1 scene>` with `backend=isaaclab`. Add `backend=gaussian` only when an
independent Gaussian runtime exists; avoid task-shaped backend names such as
`gaussian-navigation`.

Suggested specs:

```text
WorldSpec
  id
  label
  surface_id
  available_backends
  scene_source
  tags
  default_backend
  resource_kind
  availability

BackendSpec
  id
  label
  implementation_backend
  lock_name
  resource_kind
  field_groups
  view_modes
  gates
  default_overrides
  availability

AgentEngineSpec
  id
  label
  public_agent_engine
  lower_runner_class
  provider_env_key
  supported_provider_profiles
  availability
  experimental

LaunchCombinationSpec
  world_id
  backend_id
  intent_id
  agent_engine_id
  provider_profile
  internal_runner_class
  evidence_lanes
  default_evidence_lane
  default_scenario_setup
  checker_id
  prompt_support
  unsupported_reason
```

The console should ask the catalog for valid combinations and unsupported
reasons. It should not maintain an independent support matrix.

Initial support matrix:

- `intent=map-build`: Codex CLI only at first. Claude Code and OpenAI Agents SDK
  stay hidden or unsupported until their runners are proven.
- `intent=cleanup`: Codex CLI, Claude Code, and experimental OpenAI Agents SDK
  where the backend supports the cleanup loop.
- `intent=open-ended`: Codex CLI and Claude Code for household-world; Gaussian/B1
  open-ended navigation where implemented. OpenAI Agents SDK stays unsupported
  for open-ended until proven.
- Deterministic direct runs remain catalog/CLI routes, not primary console
  choices. Public deterministic routes use `agent_engine=direct-runner` and do
  not require `provider_profile`.
- Smoke routes are modeled as smoke evidence/runner mode under direct runner or
  internal runner metadata, not as an `mcp-smoke` agent engine.

## Candidate Refactors

### 1. Replace Flat Console Routes With Orthogonal World Selection

Severity: P1
Entropy source: real workflow friction
Materiality: the current UI presents environment, task, and agent engine as
equivalent route cards, which already caused operator confusion.

Work:

- Replace `Routes` rail with `World / Scene` rail.
- Back the rail with a searchable world catalog. Curated defaults are fine for
  v1, but hard-coded route/task cards are not.
- Add a backend selector filtered by the selected world. If a world supports
  only one backend, preselect and lock it.
- Move task intent choice to setup as an explicit `Task intent` dropdown.
- Move Codex/Claude/OpenAI Agents SDK to an `Agent engine` dropdown.
- Filter tasks and engines by selected world/backend.
- Use operator-facing world/backend ids in UI/API/public commands, with backend
  implementation names shown only as diagnostics/resolved metadata.
- Show unsupported combinations inline with concrete reasons.
- Keep `Agibot G2 Cleanup` blocked because physical manipulation is still not
  available.
- Keep AI2-THOR navigation/games outside this operator console while preserving
  them as non-console public runs/docs.

Affected paths:

- `roboclaws/operator_console/routes.py`
- `roboclaws/operator_console/static/index.html`
- `roboclaws/operator_console/static/app.js`
- `roboclaws/operator_console/static/styles.css`
- `tests/unit/operator_console/`

Suggested proof:

- Static tests assert the DOM exposes world/backend/task-intent/engine
  selectors.
- Catalog tests cover searchable/listable worlds and curated defaults.
- Unit tests assert MuJoCo + cleanup + Codex, MuJoCo + cleanup + Claude, MuJoCo
  + map-build + Codex, Isaac + cleanup + Codex, and Agibot + map-build + Codex
  resolve to launchable plans.
- Unit tests assert unsupported combinations show reasons rather than dead
  route cards.
- UI tests assert `scenario_setup` controls appear only for household-world
  worlds.

### 2. Move Console Support Matrix Into Launch Catalog

Severity: P1
Entropy source: live source drift
Materiality: current source of truth is split between `TaskSurfaceSpec`,
`TaskIntentSpec`, `ConsoleRoute`, and Just dispatcher conditionals.

Work:

- Add world, backend, and agent-engine specs under `roboclaws/launch/`.
- Add a resolver that takes:

  ```text
  world_id
  backend_id
  intent_id
  agent_engine_id
  provider_profile
  evidence_lane
  scenario_setup
  ```

  and returns a `LaunchPlan` or an unsupported reason.
- Generate console payloads from this resolver.
- Preserve route-specific gates, locks, field groups, and view modes as
  catalog metadata.

Affected paths:

- `roboclaws/launch/catalog.py`
- new `roboclaws/launch/worlds.py`
- new `roboclaws/launch/backends.py`
- new `roboclaws/launch/agent_engines.py`
- possibly new `roboclaws/launch/console_matrix.py`
- `roboclaws/operator_console/routes.py`

Suggested proof:

- Catalog tests assert combination availability and unsupported reasons.
- Operator-console route tests no longer assert hand-written route IDs as the
  primary public shape.

### 3. Retire Legacy Task Grammar And Catalog-Level Task Vocabulary

Severity: P1
Entropy source: stale public surface
Materiality: docs say `run::surface` is canonical, but code/tests still protect
`task::run`, `resolve_task_launch`, and catalog-level legacy task names such as
`household-cleanup` and `semantic-map-build`.

Work:

- Remove `task::run` from the supported public/agent-facing grammar.
- Remove `resolve_task_launch`, `resolve_task_run`, `CANONICAL_TASKS`,
  `LEGACY_TASK_ALIASES`, and `SUPPORTED_ROUTES` from public exports.
- Delete or privatize `just/task.just`.
- Update tests to trace `just run::surface ...` instead of `just task::run ...`.
- Update generated rerun commands and report examples to use `run::surface`.
- Remove legacy task names directly from active public/catalog code instead of
  preserving them behind compatibility shims.
- Build `LaunchPlan` from canonical axes:

  ```text
  surface
  intent
  world
  backend
  agent engine
  provider profile
  evidence lane
  scenario setup
  ```

Important boundary:

This refactor removes the legacy public task facade and stops treating lower
task names as catalog-level concepts. `household-cleanup`,
`semantic-map-build`, `ai2thor-nav`, and similar names should be removed from
active launch code rather than treated as compatibility targets. If a lower
script still needs a task-like value temporarily, the implementation should
rename or replace that lower argument in the same refactor slice instead of
advertising a compatibility adapter.

Suggested proof:

- `just --summary` exposes `run::surface`, `agent::*`, and `console::run`, but
  not `task::run`.
- `ROBOCLAWS_JUST_TRACE=1 just run::surface ...` covers every route previously
  covered through `task::run`.
- Searches for active `just task::run` references only find historical docs or
  intentionally parked retrospectives.
- Catalog tests assert public launch resolution without importing legacy task
  constants.
- Searches for `semantic-map-build`, `household-cleanup`, and `ai2thor-nav` in
  active launch code return no public/catalog usages.

### 4. Expose OpenAI Agents SDK As Experimental Agent Engine

Severity: P2
Entropy source: hidden current capability
Materiality: the SDK runner exists, has local proof, and operator-console state
already recognizes its artifacts, but no UI path can select it.

Work:

- Add `openai-agents-sdk` as an experimental agent engine.
- Initially allow only supported household cleanup combinations.
- Keep it visually distinct from product baseline engines.
- Keep `done` / `run_result.json` as the only success signal.
- Do not silently promote it as the default path.

Affected paths:

- `roboclaws/launch/agent_engines.py`
- `roboclaws/operator_console/launcher.py`
- `just/molmo.just`
- `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`
- `tests/unit/operator_console/`
- relevant dev-tool contract tests

Suggested proof:

- UI can select MuJoCo + cleanup + OpenAI Agents SDK and builds a launch
  request that reaches the existing private `openai-agents-live` runner.
- Unsupported SDK combinations show explicit reasons.
- Existing Codex CLI and Claude Code launches are unchanged.

### 5. Clarify Genesis / Gaussian / B1 Digital-Twin Position

Severity: P2
Entropy source: future workflow friction
Materiality: recent visual-scene work is likely to be mistaken for a full
agent-run backend unless the UI and catalog mark the boundary.

Work:

- Add world entries for visual-scene/digital-twin surfaces only when they
  have a clear operator action: launch, open-ended navigation, preview, or
  report.
- Show Gaussian/B1 open-ended navigation as enabled or experimental when the
  runnable navigation action exists. If the support runs through Isaac, model
  it as a Gaussian/B1 world with `backend=isaaclab`, not as a separate
  task-shaped backend.
- Add a separate `backend=gaussian` only when an independent Gaussian runtime
  exists and can support more than a task-specific navigation shim.
- Hide pure placeholders. A hidden/unsupported world can still explain that it
  may appear later when it gains a concrete operator action.
- Label visual-only entries as visual comparison / scene preview until they can
  back an agent-run MCP loop.
- Do not pretend digital-twin surfaces support cleanup or map-build execution
  until that backend capability exists.

Affected paths:

- `roboclaws/launch/worlds.py`
- `roboclaws/launch/backends.py`
- `roboclaws/operator_console/static/app.js`
- Genesis / B1 docs if a visible entry is added.

Suggested proof:

- The UI does not offer Start for visual-only environments that have no runnable
  action.
- Gaussian/B1 open-ended navigation appears only when the runnable action is
  available and is labeled by its supported intent.
- Help text names the current proof boundary.

### 6. Align Active Docs And Demo Matrix With Orthogonal Launch Concepts

Severity: P1
Entropy source: live source drift
Materiality: active human docs still foreground old demo categories such as
AI2-THOR games, VLM, OpenClaw, and task-specific rows. Future agents can follow
those docs and reintroduce the same flattened UI taxonomy.

Work:

- Refresh README demo/run surfaces around supported worlds/backends, task intents,
  and agent engines instead of old demo buckets.
- Keep historical OpenClaw/VLM/AI2-THOR game references only where they describe
  actual supported non-console workflows.
- Make the operator-console docs point to the same world/backend/task/engine
  vocabulary as the launch catalog.
- Update `just/README.md` examples if needed so natural-language mappings do
  not imply `task::run` or flattened route cards.

Affected paths:

- `README.md`
- `ARCHITECTURE.md`
- `just/README.md`
- `docs/human/**` only where active runbooks contradict the new launch model

Suggested proof:

- Active docs use `run::surface` as the public grammar.
- Active docs describe console launch choices as world/backend/task/engine axes.
- Searches for `task::run` in active docs return no live instructions.
- Remaining VLM/OpenClaw/AI2-THOR game references are either supported
  non-console routes or clearly historical/maintenance notes.

### 7. Split Driver Taxonomy Into Engine, Provider, And Internal Runner Class

Severity: P1
Entropy source: recurring rediscovery
Materiality: `driver` currently mixes product agent engines, provider routes,
direct deterministic runners, smoke substitutes, VLM policies, OpenClaw Gateway
routes, and scripts. That overload is the same conceptual ambiguity the console
refactor is trying to remove.

Work:

- Introduce explicit catalog terms:

  ```text
  agent_engine: codex-cli | claude-code | openai-agents-sdk | direct-runner
  provider_profile: codex-env | mify | kimi-anthropic | mimo-anthropic | ...
  internal_runner_class: live-agent | deterministic | smoke | gateway | script
  ```

- Use `agent_engine` for operator-facing selection.
- Keep provider/model choice separate from the engine.
- Treat `direct`, `mcp-smoke`, `vlm`, `openclaw`, and `script` as runner or
  adapter classes instead of peer product engines when they are not the console
  target.
- Keep `run::surface` as the public recipe name, but extend its grammar to
  accept `world=`, `backend=`, `agent_engine=`, and `provider_profile=`.
- Derive internal runner class from the selected engine/provider/world/backend
  combination; do not expose it as a public operator choice.
- Default `provider_profile` for live agents when omitted, but persist the
  resolved value in run state, reports, and history.
- Remove public `driver=` from active route grammar and examples in the same
  refactor. Lower implementation details may still derive an internal runner
  class, but they must not expose `driver=` as the active public selector.

Affected paths:

- `roboclaws/launch/catalog.py`
- `roboclaws/launch/runners.py`
- new `roboclaws/launch/agent_engines.py`
- new or updated catalog tests
- operator-console route and launcher metadata

Suggested proof:

- Console payloads expose `agent_engine` and `provider_profile` distinctly and
  may include derived `internal_runner_class` only for diagnostics.
- Unsupported combinations are explained using those terms instead of raw
  driver strings.
- Public `run::surface` examples and tests use explicit
  `world=` / `backend=` / `agent_engine=` / `provider_profile=` fields instead
  of `driver=` for console-target routes.
- Tests cover Codex CLI, Claude Code, OpenAI Agents SDK, direct runner, and
  smoke/gateway/script internal runner classes without exposing runner class as
  a required public selector.
- Active public AI2-THOR, OpenClaw, VLM, household, deterministic, and smoke
  examples no longer teach `driver=`.

### 8. Replace Route-ID Launch API And State With Canonical Launch Selection

Severity: P1
Entropy source: stale surface
Materiality: even after the UI becomes orthogonal, the console server,
launcher, history, interactions, and tests can keep `route_id` as the real
identity. That would preserve the old flattened route-card model under a new UI.

Work:

- Replace browser launch requests shaped around:

  ```text
  route_id
  intent
  overrides
  ```

  with a canonical selection:

  ```text
  world_id
  backend_id
  intent_id
  agent_engine_id
  provider_profile
  evidence_lane
  scenario_setup
  overrides
  ```

- Persist the canonical selection in run state and history.
- Keep generated argv and lower adapter details as derived fields.
- Remove route-card labels from history/status as primary identity; display a
  composed label from environment + task + engine instead.
- If old history files are still read, treat them as best-effort legacy display
  records rather than supported launch inputs. Old route-id records do not need
  relaunch or semantic reload support.

Affected paths:

- `roboclaws/operator_console/server.py`
- `roboclaws/operator_console/launcher.py`
- `roboclaws/operator_console/history.py`
- `roboclaws/operator_console/interactions.py`
- `roboclaws/operator_console/state.py`
- `roboclaws/operator_console/static/app.js`
- `tests/unit/operator_console/`

Suggested proof:

- Launch API tests submit canonical selection fields, not `route_id`.
- Run state includes world, backend, intent, agent engine, provider profile,
  evidence lane, and scenario setup.
- History/status tests assert composed launch identity instead of route-card id.
- Searches for `route_id` in operator-console code find only legacy history
  readers or intentionally transitional tests.

### 9. Supersede Conflicting Prior Launch And Console Plans

Severity: P2
Entropy source: workflow drift
Materiality: several older plans still describe `task::run`, route cards,
agent-neutral route labels, or `semantic-map-build` / `household-cleanup` as
first-class public tasks. Future agents following related plans can reintroduce
the same concepts this refactor removes.

Work:

- Add a short supersession note to older active-looking operator-console and
  launch refactor plans that now conflict with this plan.
- Point readers to this plan as the current source for console launch taxonomy.
- Do not rewrite historical evidence logs or shipped retrospectives.
- Keep durable design rationale from older plans only when it still matches the
  orthogonal model.

Likely superseded or partially superseded sources:

- `docs/plans/standalone-codex-operator-console-UI-SPEC.md`
- `docs/plans/refactor-operator-console-ui.md`
- `docs/plans/refactor-reduce-entropy-domain-first-launch-architecture.md`
- old sections in `docs/plans/auto-semantic-map-build.md` that still call
  `semantic-map-build` / `household-cleanup` public runnable tasks

Suggested proof:

- Related plan files either point to this plan or are clearly historical.
- Searches for live plan instructions recommending `task::run` are confined to
  superseded/historical sections.
- A future agent reading `docs/plans/` can identify the current console/launch
  taxonomy without comparing multiple stale plans.

## Non-Goals

- Do not rewrite unrelated lower `just/agent.just` shell routing beyond the
  paths needed to remove legacy task IDs and support the new launch axes.
- Do not claim Agibot physical cleanup manipulation.
- Do not make Genesis/Gaussian/B1 a cleanup backend before the backend exists.
- Do not preserve old public `task::run` command examples for active docs.
- Do not preserve old public `driver=` or `environment_setup=` aliases for
  active route grammar.
- Do not add a migration script for old console route-id history.
- Do not create an ADR unless implementation changes the durable public command
  contract beyond this plan.
- Do not add arbitrary browser-submitted shell commands.

## Implementation Strategy For Later Flow

Run this through `intuitive-flow` as one refactor plan, but implement in small
commits.

### Flow Execution Slicing

Treat this plan as one Flow epic, not one giant commit. The implementation
should land in staged, reviewable slices:

1. Launch catalog/domain model first:
   - Add `WorldSpec`, `BackendSpec`, `AgentEngineSpec`, and combination
     resolution.
   - Make `run::surface` resolve `world=`, `backend=`, `agent_engine=`, and
     `provider_profile=`.
   - Rename `environment_setup` to `scenario_setup` without a public alias.
   - Remove active public `driver=` grammar repo-wide.
   - Default and persist resolved provider profiles.
   - Derive internal runner class in catalog/runtime metadata.
2. Remove legacy task grammar in the same first stage:
   - Delete `task::run` as an active public facade.
   - Remove `resolve_task_launch`, `resolve_task_run`, legacy task constants,
     and active tests that protect `household-cleanup`,
     `semantic-map-build`, or `ai2thor-nav` as catalog-level task IDs.
3. Refactor operator-console server/API/state:
   - Replace `route_id` launch requests with canonical launch selection.
   - Persist world, backend, intent, agent engine, provider profile, evidence
     lane, and scenario setup.
   - Treat old route-id history as non-relaunchable best-effort display data or
     ignore it. Do not add a migration script.
4. Refactor static UI:
   - World / scene rail.
   - Backend selector filtered by world.
   - Task-intent, agent-engine, provider-profile, evidence-lane, and
     household-only scenario-setup controls.
   - Unsupported-combination reasons.
5. Add experimental OpenAI Agents SDK exposure where the catalog says it is
   supported.
6. Align active docs and supersede conflicting prior plans.

Do not start with the static UI before the catalog can resolve the new public
launch grammar. The catalog/public grammar slice is the foundation that keeps
the UI from becoming another hand-written support matrix.

No ADR is required for this refactor unless implementation discovers a durable
public command change beyond keeping the `run::surface` recipe name with new
orthogonal arguments. This plan plus `CONTEXT.md` are the current source of
truth.

Recommended first verification ladder:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
ruff check roboclaws/launch roboclaws/operator_console tests/unit/operator_console tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Local/live gates remain separate and should be run only after deterministic
route tests pass:

```bash
just console::run
ROBOCLAWS_JUST_TRACE=1 just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
ROBOCLAWS_JUST_TRACE=1 just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
```

## Acceptance Criteria

- The operator console no longer lists task-specific route cards as the primary
  selection model.
- World, backend, task intent, agent engine, provider/model, evidence lane, and
  scenario setup are distinct controls.
- Unsupported combinations are disabled with concrete reasons.
- OpenAI Agents SDK is selectable only as an experimental engine for supported
  combinations.
- `run::surface` is the only active public run grammar.
- Active docs and tests no longer route through `task::run`.
- Legacy task names are removed from active launch/catalog code rather than
  preserved as compatibility shims.
- Driver, engine, provider, and runner-class concepts are no longer collapsed.
  Operator-facing metadata and console-target public run arguments expose
  world, backend, agent engine, and provider profile; runner class is derived
  internal metadata.
- Console launch API, persisted run state, and history are keyed by canonical
  launch selection, not route-card ids.
- Old route-id history is not relaunchable and does not need semantic reload
  support.
- Conflicting older plan docs are marked superseded or historical so this plan
  remains the current source for console/launch taxonomy.

## Preflight Contract

Preflight status: DRAFT

Task source: plan path plus 2026-06-10 operator-console abstraction discussion.

Canonical source: `docs/plans/operator-console-orthogonal-launch-refactor.md`.

Route: durable `$intuitive-flow`.

Goal: refactor the operator console and launch catalog from flattened route
cards to orthogonal launch axes: `world`, `backend`, `intent`,
`agent_engine`, `provider_profile`, `evidence_lane`, and `scenario_setup`.

### Preflight Scope

- Implement this plan's nine refactor candidates as one Flow epic in small,
  reviewable slices.
- Move console support matrix ownership into launch catalog metadata.
- Replace `route_id` launch API/state with canonical launch selection.
- Migrate active public grammar away from `driver=` and `environment_setup=`
  toward explicit launch axes.
- Remove `task::run`, legacy task IDs, and compatibility shims directly.
- Expose OpenAI Agents SDK as experimental only where supported.
- Update active docs and supersede conflicting old plans.

### Preflight Non-Goals

- No old public aliases for `driver=`, `environment_setup=`, or legacy task IDs.
- No route-id relaunch or history migration.
- No Agibot physical cleanup manipulation claim.
- No `backend=gaussian` until there is an independent Gaussian runtime.
- No arbitrary browser-submitted shell commands.
- No implementation before explicit execution approval.

### Context Package

Must read:

- `docs/plans/operator-console-orthogonal-launch-refactor.md`
- `CONTEXT.md`
- `docs/human/domain.md`
- `ARCHITECTURE.md`
- `just/README.md`
- `roboclaws/launch/`
- `roboclaws/operator_console/`
- Relevant `just/*.just` files for `run::surface`, `task::run`, `agent::*`,
  and `console::run`

Useful evidence:

- `tests/unit/launch/`
- `tests/unit/operator_console/`
- `tests/contract/dev_tools/test_task_agent_just_recipes.py`

Do not read unless needed:

- Shipped retrospectives
- Old phase logs
- Unrelated Isaac/Gaussian map artifacts

### Definition Of Done

SUCCESS only if:

- The catalog, CLI grammar, console API/state/UI, tests, and active docs all
  use the orthogonal launch model.
- Product proof covers affected public routes.
- Manual browser proof covers the operator console selection flow.

BLOCKED_NEEDS_LOCAL_VALIDATION if:

- Required provider-backed, Docker-backed, simulator-backed, or
  browser-observed gates cannot be run in the execution environment.

INTERMEDIATE_ONLY if explicitly approved:

- Deterministic tests pass but product, browser, provider, Docker, or simulator
  proof is still missing. This is not complete, merge-ready, or a no-regression
  claim.

Must not regress:

- `run::surface` remains the public recipe name.
- `task::run` is not an active public facade.
- Active docs/tests do not teach `driver=` or `environment_setup=`.
- `direct-runner` remains available for deterministic CLI/catalog routes, but
  is not a primary console engine.
- Old route-id history is not relaunchable.

### Required Verification

Deterministic gates:

```bash
node --check roboclaws/operator_console/static/app.js
./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch tests/unit/operator_console
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_task_agent_just_recipes.py
ruff check roboclaws/launch roboclaws/operator_console tests/unit/launch tests/unit/operator_console tests/contract/dev_tools/test_task_agent_just_recipes.py
ruff format --check roboclaws/launch roboclaws/operator_console tests/unit/launch tests/unit/operator_console tests/contract/dev_tools/test_task_agent_just_recipes.py
```

Integration and product run gates:

```bash
ROBOCLAWS_JUST_TRACE=1 just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
ROBOCLAWS_JUST_TRACE=1 just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
```

The implementation must also add and run direct deterministic trace examples
using `agent_engine=direct-runner` without `provider_profile`.

Local/live/manual gates:

```bash
just console::run
```

Manual browser checks:

- Select world, backend, task intent, agent engine, provider profile, evidence
  lane, and scenario setup.
- Verify unsupported combinations show concrete reasons.
- Verify `scenario_setup` appears only for household-world worlds.
- Verify history and status use composed canonical launch identity instead of
  route-card relaunch.
- Run provider/Docker/live-agent gates before claiming full success, or report
  `BLOCKED_NEEDS_LOCAL_VALIDATION`.

### Execution Surface

- Main session: supervises durable Flow execution and owns final
  complete/blocked judgment.
- Worker: none by default.
- Worker-local goal: none.

To execute:

```text
/goal execute docs/plans/operator-console-orthogonal-launch-refactor.md with intuitive-flow
```

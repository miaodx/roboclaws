# Refactor: Domain-First Launch Architecture

**Status:** Proposed source plan
**Created:** 2026-06-02
**Source:** server-entrypoint entropy review, `$intuitive-reduce-entropy`,
`$plan-eng-review`, and `$improve-codebase-architecture` discussion
**Workflow:** Pre-GSD architecture plan. Ingest into a GSD phase or route
through `$intuitive-refactor` before implementation.

## Review And Intake Decisions

`$intuitive-flow` implementation intake on 2026-06-02 accepted the plan with
these execution constraints:

- Start with a Python launch composition root and declarative task facades
  before moving implementation modules. This gives the existing public
  `just task::run` surface a stable source of truth without creating a broad
  package-rename diff first.
- Keep `just agent::run` as the lower dispatcher during the first checkpoint.
  The launch root should resolve task, driver, profile/report, backend, and
  target command shape, but the shell dispatcher can continue to execute the
  current routes until the driver split lands.
- Treat the full `roboclaws/molmo_cleanup` to `roboclaws/household` package
  move as a later checkpoint because current scripts, tests, and the bare
  Python GitHub Pages helper still import `roboclaws.molmo_cleanup` directly.
  The move must include a focused import strategy that does not break
  dependency-light Pages assembly.
- Do not preserve obsolete example symlinks or duplicate wrappers at closeout.
  Temporary examples are allowed only while their replacement CLI/launch path is
  being introduced.
- The verification gates remain the focused `task::run` trace routes, contract
  tests, and ruff gates listed below; hardware/provider/OpenClaw/Isaac/Agibot
  live gates must be recorded explicitly if not run in the current runtime.

## Phase 0 Inventory

Current public command grammar stays frozen as:

```bash
just task::run <task> <driver> [report|profile] [key=value ...]
```

Server and agent entrypoint inventory:

| Path | Current role | Decision |
| --- | --- | --- |
| `examples/mcp/coding_agent_nav_server.py` | AI2-THOR coding-agent MCP server wrapper, 192 lines. | Replace with `roboclaws.cli.agent_server` / domain launch path; delete example wrapper once route exists. |
| `examples/coding_agent_nav_server.py` | Symlink to `examples/mcp/coding_agent_nav_server.py`. | Delete as obsolete root compatibility path. |
| `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py` | Household cleanup live-agent MCP/server wrapper, 453 lines. | Move server assembly into launch/CLI; delete or reduce to thin wrapper during MCP consolidation. |
| `examples/molmo_realworld_cleanup_agent_server.py` | Symlink to `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py`. | Delete as obsolete root compatibility path. |
| `examples/molmo_cleanup/agibot_semantic_map_build_agent_server.py` | Agibot semantic-map live-agent server wrapper, 111 lines. | Move to household semantic-map MCP launch path; delete wrapper after CLI route exists. |
| `roboclaws/mcp/server.py` | AI2-THOR navigation MCP capability server, 1393 lines. | Move/rename to domain-local `roboclaws/ai2thor/navigation_mcp.py`; keep shared runtime helpers in `roboclaws/mcp/`. |
| `roboclaws/molmo_cleanup/realworld_mcp_server.py` | Household cleanup MCP capability server, 1025 lines. | Move/rename under `roboclaws/household/` during package move. |
| `roboclaws/molmo_cleanup/agibot_map_build_mcp_server.py` | Agibot map-build MCP capability server, 1237 lines. | Move backend-specific Agibot code under household backend/capability modules and keep server startup through launch. |
| `roboclaws/openclaw/reset_server.py` | OpenClaw reset helper, 162 lines. | Not a duplicate MCP task entrypoint; leave unless launch cleanup shows a direct route need. |

Route-source inventory:

| Surface | Current owner | Decision |
| --- | --- | --- |
| `just/task.just` | Thin public facade that calls `roboclaws.devtools.commands task run`. | Keep as public shell facade. |
| `roboclaws/devtools/commands.py` | Current shallow task/driver normalization and `agent::run` dispatch. | Move route metadata to `roboclaws.launch` and keep this module as CLI-compatible adapter. |
| `just/agent.just` | Large lower dispatcher with override validation, prompts, backend routing, and task-specific command assembly. | Split gradually: launch root first, then prompts/driver adapters, then backend/task-specific command builders. |
| `just/molmo.just` | Long Molmo/household live-agent prompts and checker routes. | Move prompt construction into agent/task prompt templates during driver split. |

Initial checkpoint acceptance:

- [ ] Python launch composition root owns canonical task/driver/profile
      metadata for existing public `task::run` routes.
- [ ] Domain task facade modules exist for AI2-THOR, household, and games.
- [ ] `roboclaws.devtools.commands.resolve_task_run()` delegates to the launch
      catalog and still returns the existing `just agent::run ...` command.
- [ ] `ROBOCLAWS_JUST_TRACE=1` routes still pass focused contract tests.

## Problem

The repo has accumulated several alike server and agent entrypoints:

- `examples/mcp/coding_agent_nav_server.py`
- `examples/coding_agent_nav_server.py`
- `examples/molmo_cleanup/molmo_realworld_cleanup_agent_server.py`
- `examples/molmo_realworld_cleanup_agent_server.py`
- `roboclaws/mcp/server.py`
- `roboclaws/molmo_cleanup/realworld_mcp_server.py`
- `roboclaws/molmo_cleanup/agibot_map_build_mcp_server.py`

Some are byte-for-byte duplicates, and some encode different axes in their path
or filename:

- `examples/mcp/*` names the protocol axis.
- `examples/molmo_cleanup/*` names a historical backend/domain mix.
- `coding_agent_*`, `*_agent_server`, and `agibot_*_server` mix driver,
  protocol, task, and backend in one filename.
- `just` recipes carry task, backend, report-profile, prompt, and driver routing
  in shell conditionals.

This makes it hard to answer simple questions:

- Is this file reusable implementation or runnable demo glue?
- Is this server an MCP capability server, an agent launcher, or both?
- Where should a new backend go?
- Where should a new task go?
- Should Agibot support be copied into every task, or composed once?

The current structure still works, but it raises maintenance cost as the repo
adds more tasks and more backends.

## Goal

Move to a domain-first, composition-root architecture that keeps:

- **minimal MCP tools** as stable capability surfaces;
- **layered and extensible skills** as strategy/routine owners;
- **tasks** as small declarative specs over capabilities, backends, agents, and
  reports;
- **backends** as reusable adapters, not per-task copies;
- **CLI/Just** as a thin public command surface, not the owner of prompts or
  routing logic;
- **examples** as optional runnable wrappers, not canonical implementation.

The target should make extension obvious:

```text
new backend -> add one adapter and capability implementation
new task    -> add one task spec that composes existing capabilities
new driver  -> add one agent driver adapter
new MCP API -> add or revise a bounded capability server
```

## Target Architecture

Prefer this domain-first shape:

```text
roboclaws/
  cli/
    main.py
    task_run.py
    agent_server.py

  launch/
    context.py
    plans.py
    catalog.py
    runners.py

  agents/
    drivers/
      codex.py
      claude.py
      openclaw.py
      direct.py
    prompts/
      ai2thor_nav.md
      household_cleanup.md
      semantic_map_build.md

  mcp/
    profiles.py
    server_runtime.py
    text_bridge.py

  ai2thor/
    backend.py
    lifecycle.py
    navigation_mcp.py
    tasks.py
    views.py

  household/
    contract.py
    cleanup_loop.py
    report.py
    scenario.py
    tasks.py
    capabilities/
      episode.py
      manipulation.py
      world.py
    backends/
      agibot.py
      isaac_lab.py
      molmospaces.py
      nav2.py
      synthetic.py
    perception/
    planner_proof/

  games/
    coverage.py
    tasks.py
    territory.py

examples/
  agent_servers/
    ai2thor_nav_mcp.py
    household_cleanup_mcp.py
    semantic_map_build_mcp.py
```

This is the target shape for the full refactor, not only a first implementation
slice. The `household` package name is locked as the clean domain name for this
work.

## Architecture Decisions

- Use **domain-first packages** under `roboclaws/` instead of top-level
  task/backend/protocol buckets for task implementation.
- Keep `roboclaws/mcp/` for shared MCP runtime utilities only: FastMCP setup,
  profile loading, text bridges, and protocol helpers.
- Keep MCP servers bounded to capability surfaces. MCP should not become a
  task-orchestration registry or a dumping ground for whole workflows.
- Move command composition into `roboclaws/launch/`. `just` should call Python
  launch code rather than owning large task/driver/profile conditionals.
- Move public CLI parsing into `roboclaws/cli/`. CLI modules should parse,
  validate, and call `launch`; they should not own domain logic.
- Move agent-driver details into `roboclaws/agents/`. Codex, Claude, OpenClaw,
  and direct runs are drivers over task specs, not separate task
  implementations.
- Rename `roboclaws/molmo_cleanup/` to `roboclaws/household/`. Cleanup,
  semantic map build, planner proof, synthetic/MolmoSpaces/Isaac/Agibot/Nav2
  backends, perception, and reporting all belong to this domain package.
- Treat Agibot as one backend adapter. Do not copy Agibot-specific code into
  every task.
- Keep a small launch catalog for public names and builder functions. The
  catalog may map task/driver/profile names to declarative task specs and
  launch builders, but it must not own prompts, backend behavior, MCP tool
  logic, safety policy, report rendering, or checker implementation.
- Remove byte-for-byte duplicate example entrypoints instead of preserving old
  paths for compatibility. This repo has no backward-compatibility requirement
  for obsolete demo surfaces.

## Composition Model

The intended runtime layering is:

```text
CLI / just
  -> launch plan
    -> task spec
      -> agent driver
      -> backend adapter
      -> capability surface
      -> report / checker
```

Tasks compose capabilities and requirements:

```text
semantic-map-build
  requires: world observation, episode lifecycle, map report
  optional: perception labels
  does not require: manipulation

household-cleanup
  requires: world observation, manipulation, episode lifecycle, cleanup report
  optional: runtime map prior, perception labels, planner proof

ai2thor-nav
  requires: navigation world, movement actions, visual report
  does not require: household manipulation contract
```

Backend adapters declare supported capabilities:

```text
synthetic
  world: yes
  manipulation: yes, simulated

molmospaces
  world: yes
  manipulation: yes, simulator-backed

isaac_lab
  world: yes
  manipulation: yes, simulator-backed

agibot
  world: yes
  manipulation: gated or backend-dependent

nav2
  world: navigation map and robot pose
  manipulation: no
```

This lets `semantic-map-build + agibot` use Agibot world capability without
duplicating Agibot code, while `household-cleanup + agibot` can fail early or
gate execution if required manipulation capability is unavailable.

## Naming Rules

Use filenames that expose one primary axis:

- Domain modules: `roboclaws/ai2thor/*`, `roboclaws/household/*`.
- Task specs: `tasks.py` or `*_task.py` inside the domain package.
- MCP capability servers: `navigation_mcp.py`, `cleanup_mcp.py`,
  `semantic_map_mcp.py`, or equivalent domain-local names.
- Agent launchers: `roboclaws/cli/agent_server.py` and launch plans, not one
  bespoke `*_agent_server.py` per backend.
- Backend adapters: `backends/agibot.py`, `backends/molmospaces.py`,
  `backends/isaac_lab.py`, etc.
- Examples: delete obsolete examples by default once `roboclaws.cli` /
  `roboclaws.launch` owns the route. Keep an example only when it is a thin
  human-runnable wrapper with no implementation or routing ownership.

Avoid names that combine driver, backend, task, and protocol in one file unless
the file is intentionally a thin runnable wrapper.

## Phased Implementation

Execute this as a full architecture refactor. The phases below may be separate
commits or checkpoints to keep review manageable, but the plan is not DONE until
the launch composition root, domain task facades, agent-driver split,
`household` package move, MCP entrypoint cleanup, duplicate example removal, and
documentation cleanup are all complete.

Temporary import aliases or wrapper paths are allowed only inside a migration
checkpoint when needed to keep tests runnable. They must be removed before
closeout unless a current public command still has no replacement.

### Phase 0: Inventory And Contract Freeze

- List current public commands, tests, examples, and documented paths.
- Identify true implementation modules versus runnable wrappers.
- Identify duplicate files and one-off compatibility paths.
- Freeze the intended public command grammar:
  `just task::run <task> <driver> [report] [key=value ...]`.
- Decide the deletion order for legacy paths under the repo's no
  backward-compatibility policy.

Acceptance:

- One inventory table exists in the implementation phase notes.
- Every duplicate server file has a move/delete decision.
- No code moves happen before the inventory is reviewed.

### Phase 1: Add Launch Composition Root

- Add `roboclaws/launch/` with launch context, task catalog, and runner
  assembly.
- Move the semantic meaning of `task`, `driver`, `report`, and `backend`
  resolution from `just` shell conditionals into Python.
- Keep `just task::run` as the public command surface.
- Make `ROBOCLAWS_JUST_TRACE=1` show the resolved Python launch plan.

Acceptance:

- Existing public `just task::run` routes still resolve.
- Trace output names the selected task, driver, profile/report, backend, and
  target command without requiring users to read shell case blocks.

### Phase 2: Introduce Domain Task Facades

- Add or formalize `ai2thor/tasks.py`, `household/tasks.py`, and `games/tasks.py`.
- Move task-level declarations out of examples and shell recipes.
- Keep task specs declarative: required capabilities, supported reports,
  default profiles, prompt id, checker id, and backend constraints.
- Do not move backend code yet except where needed to create stable imports.

Acceptance:

- `ai2thor-nav`, `household-cleanup`, and `semantic-map-build` resolve through
  domain task specs.
- Task specs do not import Codex/Claude/OpenClaw implementation details.
- Driver-specific prompts are selected through task metadata plus driver
  adapter logic.

### Phase 3: Split Agent Drivers From Task Logic

- Add `roboclaws/agents/drivers/` for Codex, Claude, OpenClaw, and direct runs.
- Move long live-agent prompt construction out of `just/molmo.just` into
  prompt templates and Python rendering.
- Keep prompts close to driver/task composition, not inside MCP servers.
- Preserve current supported Docker-based coding-agent launch route.

Acceptance:

- `just` no longer contains long task prompts.
- Driver launch code is reusable across tasks.
- Network guards and supported Docker runtime constraints remain enforced.

### Phase 4: Rename Molmo Cleanup Domain To Household

- Create `roboclaws/household/` as the domain package for cleanup, semantic map
  build, planner proof, reports, perception, and backends.
- Move backend-neutral cleanup/map/report/contract code under `household/`.
- Move MolmoSpaces-specific code under `household/backends/molmospaces.py` or a
  small subpackage if needed.
- Move Agibot-specific code under `household/backends/agibot.py`.
- Keep import aliases only during the migration checkpoint if needed for tests,
  then remove them before closeout.

Acceptance:

- New code imports household domain modules, not `molmo_cleanup`.
- Backend-specific modules do not own task orchestration.
- Agibot code is not duplicated across cleanup and semantic-map paths.

### Phase 5: Consolidate MCP Capability Servers

- Keep shared MCP runtime in `roboclaws/mcp/`.
- Keep domain-local MCP modules for domain capability surfaces.
- Make server startup go through launch/server composition rather than bespoke
  example scripts.
- Remove duplicate root example files.
- Remove examples that only duplicate CLI/launch routes. Keep an example only if
  it remains useful as a thin human-runnable wrapper that calls `roboclaws.cli`
  or `roboclaws.launch`.

Acceptance:

- No byte-for-byte duplicate server entrypoints remain.
- MCP server names consistently describe task/domain capability, not driver
  implementation.
- No example owns implementation, prompts, routing, backend selection, or MCP
  server assembly.
- Contract tests cover every public MCP launch path.

### Phase 6: Documentation And Compatibility Cleanup

- Update `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `just/README.md`, and
  relevant human docs.
- Delete or update stale references to old example paths.
- Add migration notes for maintainers.
- Close all temporary import aliases and compatibility wrappers created during
  the migration.

Acceptance:

- `find . | grep server.py | grep -v .venv | grep -v vendors` no longer shows
  ambiguous duplicate example roots.
- The architecture docs explain where to add a new task, backend, driver, MCP
  capability, and example.
- The public command grammar remains small and documented.
- Obsolete example paths are deleted, not retained as compatibility wrappers.

## Verification Plan

Focused proof commands for the implementation phase:

```bash
ROBOCLAWS_JUST_TRACE=1 just task::run ai2thor-nav openclaw visual
ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup codex smoke
ROBOCLAWS_JUST_TRACE=1 just task::run household-cleanup codex camera-labels backend=agibot_gdk
ROBOCLAWS_JUST_TRACE=1 just task::run semantic-map-build codex camera-labels backend=agibot_gdk
./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools tests/contract/mcp tests/contract/molmo_cleanup
ruff check roboclaws just examples tests/contract/dev_tools tests/contract/mcp tests/contract/molmo_cleanup
ruff format --check roboclaws just examples tests/contract/dev_tools tests/contract/mcp tests/contract/molmo_cleanup
```

Real AI2-THOR, OpenClaw Gateway, live provider, Isaac, and Agibot hardware gates
should be run only on a suitable local network/runtime according to `AGENTS.md`.
If they are not run during implementation, record that explicitly in the phase
closeout.

## Affected Paths

Expected implementation touch points:

- `README.md`
- `ARCHITECTURE.md`
- `STATUS.md`
- `just/README.md`
- `just/*.just`
- `examples/**`
- `roboclaws/devtools/commands.py`
- `roboclaws/mcp/**`
- `roboclaws/molmo_cleanup/**`
- `roboclaws/openclaw/**`
- new `roboclaws/cli/**`
- new `roboclaws/launch/**`
- new `roboclaws/agents/**`
- new or renamed `roboclaws/ai2thor/**`
- new or renamed `roboclaws/household/**`
- focused contract tests under `tests/contract/**`

## Risks

- Broad import moves can produce noisy diffs and mask behavior changes.
- Moving prompt construction out of `just` may accidentally change live-agent
  behavior if templates are not snapshot-tested.
- A too-powerful launch catalog can become the same registry problem under a
  cleaner name.
- Temporary compatibility aliases can become permanent unless each has a planned
  deletion point.
- Hardware-dependent backends may not be fully verifiable in a cloud or
  headless environment.

Mitigations:

- Land in small phases with focused route and contract tests.
- Keep launch catalog entries declarative and shallow; prompts, backend
  behavior, MCP tools, safety policy, report rendering, and checker
  implementation stay outside the catalog.
- Snapshot or trace rendered launch plans and prompts before/after migration.
- Delete duplicate examples in the same phase that creates their replacement.
- Record unrun local/hardware gates as explicit parked validation.

## Non-Goals

- Do not redesign task behavior, scoring, reports, or cleanup semantics as part
  of the initial architecture move.
- Do not add a generic all-task MCP server unless a later ADR reverses the
  current separate-server direction.
- Do not migrate historical output artifacts.
- Do not preserve obsolete example paths for compatibility.
- Do not move secrets, local `.env` handling, or machine-local mirror settings.

## Done Checklist

- [ ] Public route inventory completed.
- [ ] Launch composition root added.
- [ ] Task specs moved to domain facades.
- [ ] Agent drivers separated from task logic.
- [ ] `molmo_cleanup` backend-neutral domain code renamed or moved to
      `household`.
- [ ] Backends live in one reusable adapter location per backend.
- [ ] MCP capability server naming is consistent.
- [ ] Duplicate example server files removed.
- [ ] Obsolete examples removed unless they remain thin human-runnable wrappers.
- [ ] Long prompts removed from `just` recipes.
- [ ] Docs explain extension paths for tasks, backends, drivers, MCP tools, and
      examples.
- [ ] Focused route, MCP, domain contract, lint, and format gates pass.

## Parked Items

- Revisit ADR-0004 only if multiple domains genuinely need a shared generic MCP
  server after domain-local MCP capability modules are clean.

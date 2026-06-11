---
refactor_scope: retire-ai2thor-vlm-direct
status: DONE
accepted_severities:
  - P1
  - P2
last_verified: 2026-06-11
---

# Refactor Scope: Retire AI2-THOR And VLM Direct

## Status

DONE

Implemented and verified on 2026-06-11. The active repo now exposes
`household-world` and `planner-proof` as public surfaces; AI2-THOR, direct
VLM-policy, route-card games, photo-capture, appliance, and old navigator
harness surfaces have been removed from active code, commands, CI, skills,
tests, and current human docs.

This is a deletion plan, not a quarantine plan. The accepted direction is to
remove the old AI2-THOR and direct VLM-policy demo stack from active code,
commands, CI, tests, skills, and current docs.

Decision: **do not keep AI2-THOR as an optional backend like MuJoCo, Isaac Lab,
or Agibot GDK.**

AI2-THOR was useful for the first navigation/game phase, but it no longer shares
the current product contract. Current work is `surface=household-world` with
cleanup, map-build, open-ended household goals, public/private evaluator
boundaries, runtime maps, and future real-robot parity. AI2-THOR is an old
navigation/game simulator with a separate MCP profile, separate skills, separate
report shape, and separate CI/local-runtime hazards. Keeping it as
`backend=ai2thor` would create false parity with MuJoCo/Isaac/Agibot.

## Target

Make the active repo obvious:

- Public surfaces: `household-world` and `planner-proof`.
- Active household backends: `mujoco`, `isaaclab`, and `agibot-gdk`.
- Active agent engines: coding agents, OpenAI Agents SDK, deterministic direct
  runner, script runner, and household OpenClaw routes where still used.
- Removed public surfaces: `ai2thor-world` and `ai2thor-games`.
- Removed backend: `ai2thor`.
- Removed direct VLM engine: `agent_engine=vlm-policy`.
- Removed AI2-THOR intents: `navigate`, `photo-capture`, `territory`,
  `coverage`.

VLM provider utilities are not automatically deleted just because `vlm-policy`
is retired. Keep model/provider routing that is still required by active
household live-agent, Kimi/MiMo/OpenAI/Anthropic, OpenClaw cleanup, or model
matrix flows. Delete the direct AI2-THOR game loop and direct VLM-policy public
engine.

## Preflight Contract

Preflight status: IMPLEMENTED

Task source: plan path.

Canonical source: `docs/plans/refactor-retire-ai2thor-vlm-direct.md`.

Route: durable `$intuitive-flow`, using `$intuitive-refactor` discipline inside
the cleanup.

Goal:

Retire the active AI2-THOR and VLM Direct stack completely, so current public
surfaces center on `household-world` / `planner-proof` and no live command, CI
gate, skill, or active doc still treats AI2-THOR as supported.

Scope:

- Remove `ai2thor-world`, `ai2thor-games`, `backend=ai2thor`, and
  `agent_engine=vlm-policy`.
- Delete AI2-THOR domain/game/MCP/skill/example/script/CI/test surfaces.
- Remove `ai2thor` from `pyproject.toml` and `uv.lock`.
- Supersede active ADR/doc guidance that presents AI2-THOR as current.
- Preserve household cleanup/map-build, MuJoCo, Isaac Lab, Agibot, and active
  household OpenClaw routes.

Non-goals:

- Do not delete historical `.planning/**`, retrospectives, or research archives
  except active links that mislead.
- Do not remove generic model/provider routing still used by household
  live-agent flows.
- Do not rebuild AI2-THOR as a household backend.
- Do not run retired AI2-THOR/VLM/OpenClaw validation gates.

Context package:

- Must read:
  - `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`, `CLAUDE.md`
  - this plan
  - `pyproject.toml`, `uv.lock`
  - `roboclaws/launch/**`, `just/**`, `.github/workflows/ci.yml`
  - targeted AI2-THOR/VLM references in `roboclaws/**`, `tests/**`,
    `docs/human/**`, `skills/**`
  - `git status --short` before edits
- Useful evidence:
  - `docs/adr/0001-use-ai2thor-for-phase-1.md`
  - `docs/adr/0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md`
  - `docs/human/mcp-skills-and-semantic-profiles.md`
- Do not read unless needed:
  - `.planning/**`, `docs/retrospectives/**`, `output/**`, `tmp/**`, old
    generated reports

Definition of Done / acceptance criteria:

- SUCCESS only if:
  - active public routes no longer accept AI2-THOR/VLM Direct axes;
  - `ai2thor` is gone from `pyproject.toml` and `uv.lock`;
  - active docs, CI, just recipes, skills, and tests no longer advertise or
    validate AI2-THOR/VLM Direct;
  - household-world and planner-proof deterministic gates still pass;
  - final search shows remaining AI2-THOR/VLM references are historical,
    superseded, or in this retirement plan.
- BLOCKED_NEEDS_DECISION if:
  - implementation finds a real active household/OpenClaw dependency on
    AI2-THOR-only code;
  - the user wants to preserve Railway appliance or AI2-THOR archives in-tree.
- BLOCKED_NEEDS_LOCAL_VALIDATION if:
  - required active household product run cannot execute in this environment.
- Must not regress:
  - `household-world` cleanup/map-build launch resolution;
  - Codex/Claude/OpenAI Agents SDK route metadata;
  - MuJoCo/Isaac/Agibot backend catalog;
  - household report/page publishing.

Verification:

- Deterministic gates:
  - `uv sync --extra dev`
  - `ruff check .`
  - `ruff format --check .`
  - `./scripts/dev/run_pytest_standalone.sh -q`
- Integration gates:
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools tests/contract/mcp tests/contract/skills tests/unit/operator_console -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup tests/unit/molmo_cleanup -q`
  - `just --list`
  - negative route checks for retired `ai2thor-world`, `ai2thor-games`,
    `backend=ai2thor`, `vlm-policy`
- Product run gates:
  - `just agent::verify mock`
  - `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline`
- Local/live/manual gates:
  - No AI2-THOR/VLM/Gateway gates are required because those surfaces are being
    removed.
  - MuJoCo/MolmoSpaces product proof is required before claiming complete if
    deterministic tests cannot prove route health.
- Optional exploratory gates:
  - `just agent::harness agent-validation execute since=<base> budget=focused`
    after the main deterministic gates are green.

Execution surface:

- Main session: supervise scope, protect existing dirty worktree changes, and
  keep this checklist synced.
- Worker: optional only after launch-axis deletion is stable; parallel lanes can
  split docs/ADR, CI/Pages, and test cleanup.
- Worker-local goal: bounded to one lane from this plan, never the whole
  retirement.

To execute:

```text
/goal execute docs/plans/refactor-retire-ai2thor-vlm-direct.md with intuitive-flow
```

Approval gate:

Closed. The accepted cleanup checklist is complete.

## Architecture Packet

Zoom-out map:

```text
Current public launch catalog
  -> ai2thor-world / ai2thor-games         [remove]
       -> backend=ai2thor                 [remove]
       -> intents navigate/photo/game     [remove]
       -> agent_engine=vlm-policy         [remove]
       -> roboclaws.ai2thor + games       [remove]
       -> AI2-THOR MCP/profile/skills     [remove]
       -> CI smoke/OpenClaw/photo reports [remove]

  -> household-world                      [keep]
       -> backends mujoco/isaaclab/agibot [keep]
       -> intents cleanup/map-build/open  [keep]
       -> household MCP/profile/skills    [keep]
       -> model/provider live-agent route [keep if consumed]

  -> planner-proof                        [keep]
```

Eng-review recommendation:

- Prefer a hard retirement over a compatibility shim. This repo has no
  backward-compatibility burden for obsolete demo surfaces.
- Remove public axes and known in-repo callers in the same scoped change.
- Keep historical `.planning/**`, retrospectives, and research documents as
  history unless they are linked from current human docs as active guidance.

Public contract / boundary:

- `run::surface` should stop accepting `surface=ai2thor-world`,
  `surface=ai2thor-games`, `backend=ai2thor`, and `agent_engine=vlm-policy`.
- `agent::run` should stop accepting legacy tasks `ai2thor-nav`,
  `photo-chairs`, `territory`, and `coverage` except where historical docs show
  old usage.
- MCP profiles should no longer advertise `ai2thor_navigation_v1`.
- Skills should no longer include `ai2thor-navigator` or
  `capture-object-photo`.

Data flow after cleanup:

```text
just run::surface
  -> roboclaws.launch catalog
  -> household/planner task specs only
  -> household MCP or direct/script/live-agent runner
  -> household reports and map artifacts

No branch lowers to:
  ai2thor Controller
  MultiAgentEngine
  VLM game policy
  AI2-THOR navigation MCP server
  AI2-THOR territory/coverage/photo reports
```

Accepted seam:

- Remove old surfaces at the launch catalog first, then delete the unreachable
  implementation, docs, tests, and CI gates.

Rejected alternatives:

- **Keep AI2-THOR as optional backend:** rejected. It does not implement the
  household-world cleanup/map-build contract and would mislead operators into
  expecting MuJoCo/Isaac/Agibot parity.
- **Hide it behind legacy recipes only:** rejected. Hidden private recipes still
  create stale tests, stale docs, and future rediscovery.
- **Move it to an optional extra:** rejected for active repo scope. If a future
  project wants AI2-THOR games, extract it to a separate archive branch or repo.

Minimum confidence level:

- L0 static and L1/L2 unit/contract gates are required for this refactor.
- L4/L5 local simulator, VLM, and OpenClaw Gateway gates are explicitly not
  required because those surfaces are being deleted.

## Accepted Severities

- P1: live source-of-truth drift, false public routes, false CI/report
  confidence, or active docs pointing humans at removed demo paths.
- P2: stale modules, tests, examples, skills, scripts, and compatibility shims
  inside the AI2-THOR/VLM Direct target.

## Accepted Cleanup Checklist

### 1. Dependencies And Lockfile

- [x] Remove `ai2thor>=5.0` from base dependencies in `pyproject.toml`.
- [x] Remove `ai2thor>=5.0` from the `dev` extra in `pyproject.toml`.
- [x] Regenerate `uv.lock` so the `ai2thor` package and dependency entries are
  gone.
- [x] Re-check whether `Pillow`, `numpy`, `imageio`, or provider packages remain
  used by household reports, visual grounding, and live-agent routes before
  deleting any of them.

### 2. Public Launch Catalog

- [x] `roboclaws/launch/catalog.py`: remove imports of
  `AI2THOR_TASK_SPECS` and `GAME_TASK_SPECS`.
- [x] `roboclaws/launch/catalog.py`: remove `ai2thor-world` and
  `ai2thor-games` from `CANONICAL_SURFACES`, `SURFACE_SPECS`, error hints, and
  removed-axis compatibility messages.
- [x] `roboclaws/launch/worlds.py`: remove `ai2thor/FloorPlan201`,
  `ai2thor-games/FloorPlan201`, and their `DEFAULT_WORLD_BY_SURFACE` entries.
- [x] `roboclaws/launch/backends.py`: remove `BackendSpec(id="ai2thor", ...)`.
- [x] `roboclaws/launch/intents.py`: remove public intents `navigate`,
  `photo-capture`, `territory`, and `coverage`.
- [x] `roboclaws/launch/agent_engines.py`: remove `vlm-policy`.
- [x] `roboclaws/launch/goals.py`: remove AI2-THOR navigation/game goal text
  and defaults.
- [x] `roboclaws/launch/evaluation.py` and related launch tests: remove
  navigation/photo/game evaluator ids if no other active surface uses them.
- [x] Operator console route metadata/tests should no longer list AI2-THOR
  worlds, backend locks, or preview expectations.

### 3. AI2-THOR Domain And Game Runtime

- [x] Delete `roboclaws/ai2thor/**`.
- [x] Delete `roboclaws/games/**`.
- [x] Delete AI2-THOR-specific core engine/runtime modules if no household
  imports remain:
  - `roboclaws/core/engine.py`
  - `roboclaws/core/game_run.py`
  - `roboclaws/core/action_decision.py`
  - `roboclaws/core/navigation_lifecycle.py`
  - `roboclaws/core/scene_grid.py`
  - `roboclaws/core/turn_metrics.py`
  - `roboclaws/core/views.py`
  - `roboclaws/core/visualizer.py`
  - `roboclaws/core/replay.py`
  - `roboclaws/core/reporter.py`
  - `roboclaws/core/rerun.py`
- [x] Keep `roboclaws/core/provider_catalog.py`,
  `roboclaws/core/provider_retry.py`, `roboclaws/core/provider_safety.py`,
  `roboclaws/core/vlm.py`, and `roboclaws/core/providers/**` only if active
  household/OpenClaw/model-matrix code still imports them. If they are kept,
  rename or document them as generic model providers in a follow-up so the
  package no longer reads as "VLM Direct game runtime".

### 4. MCP And Capability Profiles

- [x] Delete AI2-THOR navigation MCP implementation:
  - `roboclaws/ai2thor/navigation_mcp.py`
  - `roboclaws/mcp/server.py` if it only serves AI2-THOR navigation.
- [x] `roboclaws/mcp/profiles.py`: remove `AI2THOR_NAVIGATION_PROFILE`,
  `_AI2THOR_PROFILE`, and `ai2thor_navigation_v1` metadata.
- [x] `roboclaws/mcp/entrypoint.py`: remove AI2-THOR MCP server registration
  and CLI targets if present.
- [x] `roboclaws/cli/agent_server.py`: remove `ai2thor-nav` parsing, startup
  banners, default output dirs, and dispatch branch.
- [x] Keep `household-cleanup`, `semantic-map-build`, and Agibot map-build MCP
  server entrypoints intact.

### 5. Direct VLM Policy And OpenClaw AI2-THOR Routes

- [x] Delete direct VLM-policy game recipes and dispatch:
  - `just/vlm.just`
  - `agent_engine=vlm-policy` mappings in `just/agent.just`
  - legacy `vlm` driver aliases in dev-tool tests.
- [x] Remove AI2-THOR-specific OpenClaw code if no household OpenClaw route uses
  it:
  - `roboclaws/openclaw/skill.py`
  - `roboclaws/openclaw/diagnostics.py`
  - `roboclaws/openclaw/reset_server.py`
  - AI2-THOR-specific parts of `roboclaws/openclaw/bridge.py`
- [x] Preserve generic OpenClaw transport/transcript pieces only if household
  cleanup OpenClaw live/smoke routes still depend on them.
- [x] Remove `roboclaws/core/providers/openclaw.py` only if the active provider
  model matrix and household OpenClaw routes no longer import it.

### 6. Examples, Skills, Harness Tasks, And Assets

- [x] Delete AI2-THOR/game examples:
  - `examples/games/**`
  - `examples/territory_game.py`
  - `examples/coverage_game.py`
  - `examples/single_agent_explore.py`
  - `examples/view_experiment.py`
- [x] Delete AI2-THOR OpenClaw examples:
  - `examples/openclaw/openclaw_demo.py`
  - `examples/openclaw/openclaw_interactive.py`
  - `examples/openclaw/openclaw_nav_autonomous.py`
  - `examples/openclaw/openclaw_photo_task.py`
  - root wrappers `examples/openclaw_demo.py`,
    `examples/openclaw_interactive.py`, `examples/openclaw_nav_autonomous.py`,
    and `examples/openclaw_photo_task.py`.
- [x] Delete skills:
  - `skills/ai2thor-navigator/**`
  - `skills/capture-object-photo/**`
- [x] Update `skills/README.md` and skill manifest tests so those skills are no
  longer listed.
- [x] Delete photo harness tasks and old run logs if they are not historical
  evidence needed by active docs:
  - `harness/tasks/photo-living-room.txt`
  - `harness/runs-log/00*-photo-living-room.md`
- [x] Remove or archive AI2-THOR preview assets:
  - `docs/preview/territory.gif`
  - `docs/preview/coverage.gif`
  - `docs/assets/readme-photo-task.png`

### 7. Scripts And Just Recipes

- [x] `justfile`: remove private `mod vlm`; remove `mod appliance`, `mod chat`,
  `mod mcp`, or `mod openclaw` only if their remaining recipes are AI2-THOR-only.
- [x] `just/agent.just`: remove legacy tasks `ai2thor-nav`, `photo-chairs`,
  `territory`, `coverage`; remove `vlm` driver and `vlm-policy` mapping; remove
  AI2-THOR rerun-command generation.
- [x] `just/run.just`: remove any AI2-THOR removed-axis help or examples.
- [x] `just/code.just`: remove AI2-THOR navigation/photo task mappings for Codex
  and Claude Code.
- [x] `just/mcp.just`: remove `mcp::up` defaults that point at
  `skills/ai2thor-navigator/SKILL.md` and `roboclaws.cli.agent_server`.
- [x] `just/openclaw.just`: remove AI2-THOR navigation, territory, coverage, and
  photo recipes.
- [x] `just/chat.just`: remove AI2-THOR interactive chat route if it only runs
  `examples/openclaw/openclaw_interactive.py`.
- [x] `just/appliance.just`: remove Railway/local AI2-THOR appliance recipes, or
  rewrite them only if there is an active household appliance replacement.
- [x] `just/verify.just`: remove AI2-THOR local-sim gate and comments.
- [x] `just/harness.just`: remove navigator/photo harness routes tied to
  AI2-THOR.
- [x] `just/README.md`: remove AI2-THOR surfaces, worlds, backend, VLM-policy,
  examples, and task mappings.
- [x] Delete AI2-THOR scripts:
  - `scripts/benchmark_ai2thor_rendering.py`
  - `scripts/dev/benchmark_ai2thor_rendering.py`
  - `scripts/check_photo_task.py`
  - `scripts/openclaw/check_photo_task.py`
- [x] Remove or rewrite AI2-THOR OpenClaw bootstrap defaults:
  - `scripts/openclaw/openclaw-bootstrap.sh`
  - `scripts/openclaw/diagnose_openclaw_latency.py`
  - `scripts/openclaw/view-snapshots.py`
  - `scripts/appliance/appliance-run-interactive.sh`
  - `scripts/appliance/appliance_seed_openclaw.py`
  - root wrapper scripts `scripts/openclaw-bootstrap.sh`,
    `scripts/diagnose_openclaw_latency.py`, `scripts/tail-openclaw-chat.py`,
    `scripts/appliance_seed_openclaw.py` if they only serve the retired stack.

### 8. CI, Pages, And Report Publishing

- [x] `.github/workflows/ci.yml`: remove AI2-THOR Unity cache steps.
- [x] Remove Xvfb setup used only for AI2-THOR.
- [x] Remove jobs/steps for:
  - `real-model-smoke`
  - `openclaw-smoke`
  - `territory-openclaw-smoke`
  - `coverage-openclaw-smoke`
  - `photo-task-smoke`
  - AI2-THOR report generation and uploads.
- [x] Remove Pages assembly for:
  - `territory/report.html`
  - `coverage/report.html`
  - `smoke/territory/report.html`
  - `smoke/coverage/report.html`
  - `openclaw/demo/report.html`
  - `openclaw/territory/report.html`
  - `openclaw/coverage/report.html`
  - photo-task artifacts.
- [x] Update `roboclaws/devtools/pages_site.py` and report/page tests so they no
  longer expect AI2-THOR/OpenClaw game tiles.
- [x] Remove `scripts/reports/generate_demo_report.py` territory/coverage demo
  generation unless it is rewritten for household reports.

### 9. Active Docs And ADRs

- [x] `README.md`: remove AI2-THOR territory/coverage/navigation/photo/appliance
  rows, command examples, related-project framing, and stale "VLM policies"
  tagline if it now implies direct VLM game routes.
- [x] `ARCHITECTURE.md`: remove the AI2-THOR Navigation stack and all
  `surface=ai2thor-world`, `backend=ai2thor`, `vlm-policy` examples.
- [x] `AGENTS.md`: remove AI2-THOR availability preflight, VLM Direct key
  preflight for retired demos, iTHOR constraints, example commands, and
  cloud/local split language that treats real AI2-THOR validation as current.
- [x] `CLAUDE.md`: remove AI2-THOR demos, API notes, VLM call pattern, gotchas,
  and local-session wording tied to AI2-THOR.
- [x] `STATUS.md`: update only if current focus or next action changes. Do not
  mirror the whole plan there.
- [x] `docs/human/mcp-skills-and-semantic-profiles.md`: remove
  `ai2thor_navigation_v1`, AI2-THOR privileged tool examples, and AI2-THOR skill
  references.
- [x] `docs/human/technical-design.md`: remove or rewrite AI2-THOR navigation
  rationale as historical only.
- [x] `docs/human/ut_ci_design.md`: remove AI2-THOR and direct VLM CI gates.
- [x] `docs/human/openclaw/**`: delete if AI2-THOR-only; otherwise rewrite to
  household OpenClaw cleanup and remove navigator references.
- [x] `docs/human/coding-agent-nav-server.md`: delete or replace with household
  MCP agent server guidance.
- [x] `docs/human/model-matrix.md`: remove AI2-THOR/OpenClaw Gateway validation
  claims if they only supported retired demos; keep provider info used by active
  household live-agent routes.
- [x] `docs/human/local-runtime.md`: remove territory/coverage/OpenClaw
  AI2-THOR artifact locations.
- [x] `docs/human/agent-task-command-taxonomy.md`: remove legacy task ids and
  AI2-THOR route examples.
- [x] `docs/adr/0001-use-ai2thor-for-phase-1.md`: mark Superseded.
- [x] `docs/adr/0004-use-separate-mcp-servers-for-ai2thor-and-molmo-cleanup.md`:
  mark Superseded.
- [x] `docs/adr/README.md`: update ADR statuses.
- [x] Add a new ADR for this retirement decision, or put the durable decision in
  the implementation PR if the repo prefers not to add ADRs for deletions.

### 10. Tests To Delete Or Rewrite

- [x] Delete AI2-THOR unit tests:
  - `tests/unit/core/test_engine.py`
  - `tests/unit/core/test_visualizer.py`
  - `tests/unit/core/test_visualizer_soul_overlay.py`
  - `tests/unit/examples/test_explore.py`
  - `tests/unit/examples/test_coverage_example.py`
  - `tests/unit/examples/test_territory_example.py`
  - `tests/unit/examples/test_game_run.py`
  - `tests/unit/games/**`
  - `tests/support/game_fakes.py`
- [x] Delete or rewrite direct VLM/provider tests only where they test the
  retired VLM-policy loop:
  - keep provider catalog/retry/safety tests if active household routes still
    use them;
  - delete tests that only assert AI2-THOR game VLM behavior.
- [x] Delete AI2-THOR MCP tests:
  - `tests/contract/mcp/test_coding_agent_nav_server.py`
  - AI2-THOR portions of `tests/contract/mcp/test_mcp_server.py`
  - AI2-THOR profile portions of `tests/contract/mcp/test_semantic_profiles.py`.
- [x] Delete AI2-THOR OpenClaw tests:
  - `tests/contract/openclaw/test_openclaw_demo.py`
  - `tests/contract/openclaw/test_openclaw_interactive.py`
  - `tests/contract/openclaw/test_openclaw_nav_autonomous.py`
  - `tests/contract/openclaw/test_openclaw_photo_task.py`
  - `tests/unit/openclaw/test_skill.py`
  - AI2-THOR-specific parts of bridge/bootstrap/diagnostic tests.
- [x] Delete AI2-THOR appliance tests:
  - `tests/contract/appliance/test_appliance_reset.py`
  - `tests/contract/appliance/test_appliance_runtime_config.py`
  - `tests/contract/appliance/test_appliance_seed_openclaw.py`
  unless the appliance is rewritten around household-world.
- [x] Rewrite launch/dev-tool tests:
  - remove `ai2thor-world`, `ai2thor-games`, `backend=ai2thor`,
    `vlm-policy`, `territory`, `coverage`, `photo-capture`, and `ai2thor-nav`
    expectations from `tests/contract/dev_tools/test_task_agent_just_recipes.py`.
  - remove AI2-THOR mappings from
    `tests/contract/dev_tools/test_code_just_recipes.py`.
  - remove AI2-THOR local-sim assumptions from
    `tests/contract/dev_tools/test_verify_just_recipes.py`.
- [x] Rewrite operator-console tests so available worlds/backends are household
  only:
  - `tests/unit/operator_console/test_routes.py`
  - `tests/unit/operator_console/test_operator_console.py`
  - `tests/unit/operator_console/test_render_scene_previews.py`.
- [x] Rewrite report/page tests:
  - `tests/contract/reports/test_reporter.py`
  - `tests/contract/reports/test_render_autonomous_replay.py`
  - `tests/contract/reports/test_replay.py`
  - `tests/contract/reports/test_pages_site_prune.py`
  - AI2-THOR/OpenClaw tile assertions in
    `tests/unit/molmo_cleanup/test_ci_live_reports.py`.
- [x] Keep household cleanup, maps, Agibot, Isaac, visual grounding, and
  planner-proof tests intact.

### 11. Final Static Sweep

- [x] `rg -n -i 'ai2[-_ ]?thor|ai2thor-world|ai2thor-games|backend=ai2thor|vlm-policy|ai2thor_navigation_v1'` returns only:
  - this plan,
  - superseded ADRs,
  - historical `.planning/**`, retrospectives, or research docs,
  - explicit archive notes.
- [x] `rg -n 'territory|coverage|photo-capture|ai2thor-nav|photo-chairs'`
  returns no active command, CI, test, or README route.
- [x] `just --list` does not advertise retired recipes.
- [x] `just run::surface ...` help/errors only mention active surfaces and
  engines.

## NOT In Scope

- Literal deletion of all historical `.planning/**`, `docs/retrospectives/**`,
  and `docs/research/**` mentions. Those are evidence history, not active
  product surface. Remove active links to them when they mislead current docs.
- Rebuilding AI2-THOR behavior on household-world. If household needs a new
  navigation-only task later, add it as a fresh household intent with household
  reports and MCP capabilities.
- Replacing provider routing. Provider cleanup is allowed only where it is
  directly tied to deleting `vlm-policy`; broader model/provider refactors are a
  separate seam.
- Removing active household OpenClaw cleanup support. This plan deletes
  AI2-THOR OpenClaw routes, not the household OpenClaw confidence lane.

## What Already Exists

- `STATUS.md` already identifies MolmoSpaces cleanup, Isaac Lab, Agibot, and
  visual-grounding confidence as the active direction.
- `roboclaws/household/**` already owns cleanup/map-build runtime behavior,
  reports, MCP server, and active backend boundaries.
- `roboclaws/launch/**` already has a centralized catalog where public axes can
  be deleted cleanly before implementation packages are removed.
- `just run::surface` is already the public command facade. It should become
  smaller, not be duplicated.

## Parked Cross-Seam / Future Ideas

- Rename `roboclaws/core/vlm.py` and provider modules to a neutral
  `roboclaws/models/**` namespace if they survive this deletion because active
  household live-agent routes use them.
- Split remaining generic OpenClaw utilities into `roboclaws/openclaw_household`
  or similar only if household OpenClaw code stays large enough to justify a
  package boundary.
- Archive the old AI2-THOR demo as a separate branch or external repo only if a
  human asks for preservation outside the active product.

## Evidence Ladder

Static planning evidence already sampled:

- Root orientation: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`.
- Active code/doc references via targeted `rg` for AI2-THOR, `ai2thor-world`,
  `ai2thor-games`, `backend=ai2thor`, and `vlm-policy`.
- Launch catalog references in `roboclaws/launch/catalog.py`,
  `worlds.py`, `backends.py`, `agent_engines.py`, and `intents.py`.
- Dependency references in `pyproject.toml` and `uv.lock`.

Required verification after implementation:

```bash
uv sync --extra dev
.venv/bin/ruff check .
.venv/bin/ruff format --check .
./scripts/dev/run_pytest_standalone.sh -q
just --summary
just --list
just agent::verify mock
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline
```

Verified on 2026-06-11:

```bash
uv sync --extra dev
.venv/bin/ruff check .
.venv/bin/ruff format --check .
./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools tests/contract/mcp tests/contract/skills tests/unit/operator_console -q
./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup tests/unit/molmo_cleanup -q
./scripts/dev/run_pytest_standalone.sh tests/integration/coding_agent/test_code_mcp_binding_smoke.py tests/contract/reports/test_run_artifacts.py -q
./scripts/dev/run_pytest_standalone.sh tests/unit/scripts/test_network_status_guard.py -q
./scripts/dev/run_pytest_standalone.sh -q
just --summary
just --list
just agent::verify mock
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels seed=7 scenario_setup=baseline
```

Additional verified sweeps:

```bash
rg -n 'ai2thor' pyproject.toml uv.lock
rg -n -i 'ai2[-_ ]?thor|ai2thor-world|ai2thor-games|backend=ai2thor|vlm-policy|ai2thor_navigation_v1' roboclaws tests scripts just .github README.md ARCHITECTURE.md AGENTS.md CLAUDE.md docs/human skills pyproject.toml uv.lock --glob '!docs/plans/refactor-retire-ai2thor-vlm-direct.md' --glob '!docs/retrospectives/**' --glob '!.planning/**' --glob '!output/**' --glob '!tmp/**'
```

`pyproject.toml` / `uv.lock` contain no `ai2thor` dependency entries. Remaining
active-surface sweep hits are explicit retirement notes or negative tests that
assert retired routes stay rejected.

Suggested focused gates before the full test run:

```bash
./scripts/dev/run_pytest_standalone.sh tests/contract/dev_tools tests/contract/mcp tests/contract/skills tests/unit/operator_console -q
./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup tests/unit/molmo_cleanup -q
```

Skipped gates:

- Real AI2-THOR rendering, Unity cache, and multi-agent collision gates. They
  are deleted by this plan.
- Real direct VLM game smoke. It is deleted by this plan.
- Live OpenClaw Gateway over AI2-THOR. It is deleted by this plan.
- Isaac Lab/GPU and Agibot physical gates. They are not required to prove
  deletion of AI2-THOR, but should remain available for their own active plans.

## Failure Modes To Guard Against

- A public route is removed from docs but still accepted by `run::surface`.
  Guard with launch catalog tests and final `rg`.
- `ai2thor` remains in `uv.lock`, so clean installs still download dead
  simulator dependencies. Guard with `uv sync --extra dev` and lockfile diff.
- Provider code needed by household live-agent routes is deleted accidentally.
  Guard by running provider/unit tests and household live-agent route resolution
  tests.
- OpenClaw household support is removed while deleting AI2-THOR OpenClaw code.
  Guard by separating AI2-THOR navigator tests from household OpenClaw smoke
  tests before deleting.
- Pages or CI still publish stale AI2-THOR report links. Guard by Pages tests
  and final active-doc search.

## Parallelization Strategy

| Step | Modules touched | Depends on |
| --- | --- | --- |
| Launch-axis deletion | `roboclaws/launch`, `just` | none |
| Runtime package deletion | `roboclaws/ai2thor`, `roboclaws/games`, `roboclaws/core`, `roboclaws/mcp`, `roboclaws/openclaw` | Launch-axis deletion |
| Docs/ADR cleanup | root docs, `docs/human`, `docs/adr`, `skills` | Launch decision |
| CI/Pages cleanup | `.github`, `roboclaws/devtools`, report scripts | Runtime package deletion |
| Test rewrite/delete | `tests` | Launch-axis deletion and runtime package deletion |

Parallel lanes:

- Lane A: launch-axis deletion -> dev-tool route tests.
- Lane B: docs/ADR/skill deletion.
- Lane C: runtime package deletion -> MCP/report/provider tests.
- Lane D: CI/Pages cleanup waits for A and C.

Conflict flags:

- `just/agent.just`, `roboclaws/launch/**`, and
  `tests/contract/dev_tools/**` are central. Keep those sequential or merge
  them before parallel lanes continue.

## Stop Condition

Stop when:

- no active public command, launch catalog entry, CI job, current human doc,
  active skill, or active test references AI2-THOR, `ai2thor-world`,
  `ai2thor-games`, `backend=ai2thor`, `ai2thor_navigation_v1`, or
  `agent_engine=vlm-policy`;
- active household-world and planner-proof tests still pass;
- `ai2thor` is absent from `pyproject.toml` and `uv.lock`;
- old AI2-THOR/VLM Direct compatibility shims are deleted rather than hidden;
- remaining references are explicitly historical or superseded.

## Execution Log

- 2026-06-11: Created plan from static audit. No production files changed.
- 2026-06-11: Removed the active AI2-THOR/direct-VLM/game/photo/appliance
  surfaces; deleted obsolete runtime packages, examples, skills, recipes,
  CI/report publishing, assets, stale symlink wrappers, and tests; added
  ADR-0137 for the retirement decision; rewrote current docs around
  `household-world` and `planner-proof`.
- 2026-06-11: Preserved generic provider helpers still used by household
  live-agent and visual-grounding routes, including `roboclaws/core/vlm.py`
  parser/provider contracts and provider modules.
- 2026-06-11: Fixed closeout issues found by verification: `just mcp::up` now
  validates the household MCP server id before warm-path PID reuse, stale
  coding-agent MCP smoke wording was updated, dangling root symlink wrappers
  to deleted scripts were removed, and network-guard tests were aligned with
  surviving recipe ownership.
- 2026-06-11: Verification passed. The product proof generated
  `output/household/semantic-map-build/direct-report/0611_1813/seed-7/report.html`.

# Roboclaws

Multiple VLM/OpenClaw agents controlling simulated robots in competition and cooperation. Python 3.10+, AI2-THOR simulation.

## Required reading

Before writing any code, read only the orientation set in order:
1. `README.md` (project orientation, what you can run, mode discovery)
2. `ARCHITECTURE.md` (code map, four operating modes, MCP contract)
3. `STATUS.md` (human-facing current focus, next action, and source links)
4. `CLAUDE.md` (this file)
5. `AGENTS.md` (operating playbook, cloud-vs-local split, dual-stack workflow)

Then follow the links in `STATUS.md` only as needed:

- Read `.planning/STATE.md` and the current `.planning/phases/*` plan when
  resuming or executing a GSD phase.
- Read `docs/plans/<slug>.md` when shaping, reviewing, or handing off a
  pre-GSD plan.
- Read `docs/technical-design.md` when design rationale or scenario specs are
  needed.
- Read `CONTEXT.md` when domain vocabulary matters.
- Read `TODOS.md` or `THOUGHTS.md` only when asked about parked work or future
  ideas.

Root `PLAN.md` is a legacy compatibility pointer, not an active plan. Shipped
phase history lives under `docs/retrospectives/` and is not required reading.

For navigator-skill / MCP-tool changes, also read `harness/PLAN.md` — the
append-only logbook of scripted-loop runs that grades the skill on curated
tasks. Each `## Run NNN` entry attributes a metric delta to one bounded
change. See [`docs/harness-self-improvement-loop.md`](docs/harness-self-improvement-loop.md)
for the design rationale and [`harness/README.md`](harness/README.md) for
how to run another iteration (`just harness::run <task>`).

## Build & test

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
pytest
```

Run demos (requires AI2-THOR, auto-downloads Unity build ~1GB; see `AGENTS.md` §1.3 for VLM key setup):

```bash
python examples/single_agent_explore.py
python examples/territory_game.py --agents 3
python examples/coverage_game.py --agents 3
```

Common `just` recipes (run `just --list` for the full grouped list):

```bash
just dev::test all                              # full repo confidence (lint + tests)
just openclaw::run photo                         # autonomous chair/sofa photo smoke
just chat::run                                   # OpenClaw Gateway + browser Control UI
DEMO_PASSWORD=demo just appliance::run local      # hosted Railway-style appliance
```

See [`docs/contributing.md`](docs/contributing.md#dev-tooling-uv-and-just)
for the one-line `just` install + tab completion. Modules:
`openclaw`, `vlm`, `chat`, `appliance`, `dev` — each lives in `just/<module>.just`.

## Code style

- Ruff enforces style — do not duplicate linter rules here
- Line length: 100
- Target: Python 3.10
- Type annotations on public APIs; `from __future__ import annotations` in all modules

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the code map. Non-obvious
AI2-THOR quirks and the VLM call pattern are below.

### AI2-THOR key APIs

```python
# Multi-agent initialization
controller = Controller(scene="FloorPlan201", agentCount=3, gridSize=0.25)

# Control a single agent (one agent per step() call)
event = controller.step(action="MoveAhead", agentId=1)

# Get each agent's independent frame and state
frame = event.events[agent_id].frame  # numpy (H, W, 3)
pos = event.events[agent_id].metadata['agent']['position']

# Overhead view
event = controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)
```

**Important notes:**
- iTHOR scenes support multi-agent; ProcTHOR does NOT (known bugs)
- Agents physically collide — they cannot pass through each other
- Agents are visible in each other's camera views
- Scene ranges: FloorPlan1-30 (kitchens), 201-230 (living rooms), 301-330 (bedrooms), 401-430 (bathrooms)

### VLM call pattern

```python
# Each agent's per-step prompt includes:
# 1. First-person camera frame (base64 JPEG)
# 2. Overhead grid map (marking all agent positions + game state)
# 3. Structured JSON (position, score, remaining steps, etc.)
#
# VLM returns JSON: {"reasoning": "...", "action": "MoveAhead"}
```

## Git workflow

- Branch from `main`
- Commit messages: `type: description` (feat, fix, ci, docs, refactor)
- PR strategy: push fixes to the PR's source branch, don't open a new PR

## Cloud vs local development

This project uses a two-topology dev setup — see `AGENTS.md §7` for the full spec. Short version:

- **Cloud sessions** (this Claude Code web session): research, small bounded changes, CI/doc edits, anything validated by `lint-and-mock`. No API keys, no Unity, no GPU in the sandbox.
- **Local sessions** (user's workstation): real Kimi / real AI2-THOR / real OpenClaw Gateway. Owns every task tagged `local-dev` on the issue tracker, plus any multi-round debug loop.

Rule of thumb: if a PR's core claim depends on real hardware or real VLM behavior, the first validation happens **locally**. CI is where that proof stays continuously live, not where it starts. In a cloud session, if you can't actually run the thing, say so explicitly in the PR — don't paper over it with "CI will tell us". File a `local-dev` issue (see #50 for template) and hand off.

**If the session IS local** (you have `docker`, a real `KIMI_API_KEY` / `ANTHROPIC_API_KEY`, a running Gateway, and AI2-THOR installed): the cloud → local handoff protocol does not apply. Run the real thing yourself, iterate, and report what you observed. No need to file a `local-dev` issue or split bounded changes away from real-hardware probes — a local session owns both. The cloud/local split exists to stop *cloud* sessions from papering over missing validation; it does not constrain a local session from carrying a full phase end-to-end.

### Local preflight ritual

Local preflight steps (key loading, Docker hygiene, ROS env stripping for
pytest) live in `AGENTS.md` §1. For the OpenClaw Gateway path specifically,
see `docs/openclw/openclaw-local.md`.

## Design principles

| Principle | Practice |
|-----------|----------|
| **Thin & focused** | Not a heavy framework; give a good model enough context and it runs |
| **Make it work first** | Day 1-2: simplest pipeline to validate core hypothesis. Day 3+: add OpenClaw |
| **Visualization first** | Every feature must produce visible output (screenshots/GIFs/video) |

## Gotchas

- AI2-THOR downloads a Unity build (~1GB) on first run
- AI2-THOR on Linux requires X server or headless rendering (`ai2thor[headless]`)
- macOS may need additional AI2-THOR rendering configuration
- `controller.step()` is synchronous, one agent per call — game engine uses turn-based stepping

## Planning workflow

Use `hybrid-phase-pipeline` when available. It routes Matt-style shaping,
gstack review, and GSD execution without making every task run every framework.

One source of truth per stage, with `STATUS.md` as the short human-facing
dashboard:

- Current orientation: `STATUS.md`.
- Before execution: `docs/plans/*.md` or GitHub issues.
- During execution: `.planning/STATE.md` and `.planning/phases/*`.
- After shipping: summaries, verification reports, and retrospectives.

Do not create `.planning/phases/*` for brainstorming. Once a phase is under GSD,
execute and ship it with GSD unless the user explicitly changes the workflow.
Root `PLAN.md` is retained only for compatibility and must not receive new
active phase content. Current focus and active source links are in `STATUS.md`.
During GSD closeout/verify/ship, update `STATUS.md` when current focus, latest
phase, next action, or blocker changed; keep it short and do not mirror
`.planning/STATE.md`. For parallel standalone terminal work, use one task-owned
file under `docs/status/active/` instead of editing `STATUS.md` for routine
progress.

## Agent skills

### Issue tracker

Issues and PRDs are tracked in GitHub Issues for `MiaoDX/roboclaws`. See
`docs/agents/issue-tracker.md`.

### Triage labels

The repo uses the canonical five-label triage vocabulary. See
`docs/agents/triage-labels.md`.

### Domain docs

Single-context repo: project orientation lives in root docs, with ADRs in
`docs/adr/`. See `docs/agents/domain.md`.

## Skill routing (gstack)

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health

## Skill routing (GSD)

For phase execution, verification, and work that needs `.planning/` structure,
invoke GSD commands first:
- Plan a phase in detail → `/gsd-plan-phase`
- Execute a planned phase → `/gsd-execute-phase`
- Verify UAT on built work → `/gsd-verify-work`
- Create PR for a completed phase → `/gsd-ship`
- Investigation / root cause → `/gsd-debug`
- Small / bounded fix → `/gsd-quick` or `/gsd-fast`
- What's the next step in the workflow? → `/gsd-next` or `/gsd-progress`
- Ingest existing plan docs into `.planning/` → `/gsd-ingest-docs`
- Start a fresh project / milestone under GSD → `/gsd-new-project` or `/gsd-new-milestone`

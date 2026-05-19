# Roboclaws

Multiple VLM/OpenClaw agents controlling simulated robots in competition and cooperation. Python 3.12+, AI2-THOR simulation.

`AGENTS.md` is the canonical repo playbook. This file is a Claude-specific
overlay; when the two conflict, follow `AGENTS.md`.

## Required reading

Before running commands or writing code, read only the orientation set in order:
1. `README.md` (project orientation, what you can run, mode discovery)
2. `ARCHITECTURE.md` (code map, four operating modes, MCP contract)
3. `STATUS.md` (human-facing current focus, next action, and source links)
4. `AGENTS.md` (canonical operating playbook, cloud-vs-local split, dual-stack workflow)
5. `CLAUDE.md` (this file)

Then follow the links in `STATUS.md` only as needed:

- Read `.planning/STATE.md` and the current `.planning/phases/*` plan when
  resuming or executing a GSD phase.
- Read `docs/plans/<slug>.md` when shaping, reviewing, or handing off a
  pre-GSD plan.
- Read `docs/human/technical-design.md` when design rationale or scenario specs are
  needed.
- Read `docs/human/domain.md` when domain vocabulary matters.
- Read `TODOS.md` or `THOUGHTS.md` only when asked about parked work or future
  ideas.

Root `PLAN.md` is a legacy compatibility pointer, not an active plan. Shipped
phase history lives under `docs/retrospectives/` and is not required reading.

For navigator-skill / MCP-tool changes, also read `harness/PLAN.md` — the
append-only logbook of scripted-loop runs that grades the skill on curated
tasks. Each `## Run NNN` entry attributes a metric delta to one bounded
change. See [`docs/ai/harness/self-improvement-loop.md`](docs/ai/harness/self-improvement-loop.md)
for the design rationale and [`harness/README.md`](harness/README.md) for
how to run another iteration (`just agent::harness run <task>`).

## Build & test

Use the repo-local `.venv/` as the canonical Python environment. It is managed
by `uv` from `pyproject.toml` / `uv.lock`, and demos should not rely on hidden
external virtualenvs under `/tmp` or another repo. If a demo needs MolmoSpaces,
MuJoCo, OpenClaw, or other extra dependencies, add or use a declared
`pyproject.toml` extra and install it into this checkout's `.venv/`.
Use `uv sync` for declared project environments and `uv pip install` only for
explicit local one-off installs. Do not use plain `pip install` for repo setup.

For git worktrees, keep a separate `.venv/` at each worktree root. That keeps
branch-specific dependency changes isolated while preserving the same
uv-managed workflow everywhere.

```bash
uv sync --extra dev
ruff check .
ruff format --check .
pytest
```

For real MolmoSpaces/MuJoCo demos, sync the declared extra into the same
repo-local environment:

```bash
uv sync --extra dev --extra molmospaces
```

Run demos (requires AI2-THOR, auto-downloads Unity build ~1GB; see `AGENTS.md` §1.3 for VLM key setup):

```bash
python examples/games/single_agent_explore.py
python examples/games/territory_game.py --agents 3
python examples/games/coverage_game.py --agents 3
```

Common `just` recipes use the small public facade:

```bash
just task::run ai2thor-nav openclaw              # normal OpenClaw navigation
just task::run molmo-cleanup codex smoke          # cheap synthetic cleanup iteration
just agent::verify mock                          # maintainer confidence gate
```

Work-network restriction: if `just dev::network-status` reports `network: work`
(the probe can reach `https://api-router.evad.mioffice.cn/`), do not run
OpenClaw workflows. Guarded recipes include OpenClaw Gateway recipes,
`just chat::run`, `just appliance::run`, and OpenClaw local/integration
verification gates. System-provider Claude Code is also blocked on the work
network, but `just code::cc`, `just harness::navigator`, and
`just molmo::claude-report` may run there when `.env` selects a repo-local
Claude provider such as `ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic` or
`ROBOCLAWS_CLAUDE_PROVIDER=mimo-anthropic`. Model-only overrides do not bypass
the guard.

Coding-agent runtime contract: run direct Codex / Claude Code demos through
`just code::codex` or `just code::cc`. The pinned Docker-backed coding-agent
runtime is the only supported public route; it runs with full local-demo
permissions and an isolated task-skill workspace. New `just` recipes that launch
Codex or Claude Code must reuse those recipes or `scripts/dev/coding_agent_docker.sh`.
Bare host `codex` or `claude` launches are unsupported unless the human
explicitly asks for a system-CLI debugging run.

See [`docs/human/contributing.md`](docs/human/contributing.md#dev-tooling-uv-and-just)
for the one-line `just` install + tab completion. See [`just/README.md`](just/README.md)
for the task/driver/report grammar and prompt mappings.

## Code style

- Ruff enforces style — do not duplicate linter rules here
- Line length: 100
- Target: Python 3.12
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
see `docs/human/openclaw/local.md`.

## Design principles

| Principle | Practice |
|-----------|----------|
| **Thin & focused** | Not a heavy framework; give a good model enough context and it runs |
| **Make it work first** | Day 1-2: simplest pipeline to validate core hypothesis. Day 3+: add OpenClaw |
| **Visualization first** | Every feature must produce visible output (screenshots/GIFs/video) |

### Legacy support policy

This repo has no backward-compatibility burden for obsolete demo surfaces. Code,
docs, tests, skills, or recipes labeled `legacy`, `current-contract`, or kept
only for compatibility are removal or replacement candidates, not APIs to
preserve.

Prefer the current docs and active profile contracts over preserving old paths.
If a legacy surface conflicts with a cleaner current design, update or delete
the legacy surface and its tests/docs in the same scoped change. Preserve a
legacy path only when the user explicitly asks for it or when it is still the
sole working route for the requested demo.

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

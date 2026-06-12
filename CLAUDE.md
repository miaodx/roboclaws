# Roboclaws

Household robot demo routes with MCP tools, reusable skills, and coding-agent
runtimes. Python 3.12+.

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

## Build & test

Use the repo-local `.venv/` as the canonical Python environment. It is managed
by `uv` from `pyproject.toml` / `uv.lock`, and demos should not rely on hidden
external virtualenvs under `/tmp` or another repo. The `dev` extra includes the
standard MolmoSpaces/MuJoCo CPU runtime. If a demo needs another optional
dependency group, add or use a declared `pyproject.toml` extra and install it
into this checkout's `.venv/`.
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

Isaac Lab remains intentionally isolated in `.venv-isaaclab/`; use the Isaac
preflight harness when testing that backend.

Run current public demos through the launch catalog:

```bash
just run::surface surface=household-world agent_engine=direct-runner preset=map-build evidence_lane=world-oracle-labels
just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-oracle-labels
just run::surface surface=household-world agent_engine=codex-cli prompt="find something useful to drink"
```

Common `just` recipes use the small public facade:

```bash
just run::surface surface=household-world agent_engine=direct-runner preset=map-build evidence_lane=world-oracle-labels
just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-oracle-labels
just run::surface surface=planner-proof agent_engine=direct-runner intent=planner-proof mode=dry-run
just agent::verify mock                          # maintainer confidence gate
```

Work-network restriction: if `just dev::network-status` reports `network: work`
(the probe can reach `https://api-router.evad.mioffice.cn/`), do not run
OpenClaw workflows. Guarded recipes include OpenClaw Gateway recipes,
`just chat::run`, and OpenClaw local/integration verification gates.
System-provider Claude Code is also blocked on the work
network. `just molmo::claude-report` may run there when `.env` contains a supported MiMo,
Kimi, or mify Anthropic key route. Codex recipes default to `codex-env` and may
run there when `CODEX_BASE_URL` and `CODEX_API_KEY` are configured. The mify
and MiniMax routes are available only with explicit
`ROBOCLAWS_CODEX_PROVIDER=mify|minimax` and `XM_LLM_API_KEY` or `MM_API_KEY`.
Model-only overrides do not bypass the guard.

Coding-agent runtime contract: run Codex / Claude Code demos through the public
launch catalog, for example
`just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-oracle-labels`.
The pinned Docker-backed coding-agent runtime is the only supported task
runtime; it runs with full local-demo permissions and an isolated task-skill
workspace. New `just` recipes that launch Codex or Claude Code must route
through `run::surface`, the private `agent::*` dispatcher, or
`scripts/dev/coding_agent_docker.sh`.
Bare host `codex` or `claude` launches are unsupported unless the human
explicitly asks for a system-CLI debugging run.

See [`docs/human/contributing.md`](docs/human/contributing.md#dev-tooling-uv-and-just)
for the one-line `just` install + tab completion. See [`just/README.md`](just/README.md)
for the launch-axis grammar and prompt mappings.

## Code style

- Ruff enforces style — do not duplicate linter rules here
- Line length: 100
- Target: Python 3.12
- Type annotations on public APIs; `from __future__ import annotations` in all modules

## Architecture

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the code map. Current household
product contracts use `surface=household-world` plus an open-task `prompt=...`
or `preset=map-build|cleanup`. The planner proof route is
`surface=planner-proof intent=planner-proof`.

Map guidance:
- Base Navigation Map is the start-of-run map contract.
- Runtime Metric Map owns semantic evidence produced during map-build and
  observations.
- `smoke` is a verification preset/private runner mode, not an evidence lane.
- Open-ended household runs omit `preset=` publicly and lower internally to
  `task_intent=open-ended`, not cleanup-specific custom mode language.

## Git workflow

- Branch from `main`
- Commit messages: `type: description` (feat, fix, ci, docs, refactor)
- PR strategy: push fixes to the PR's source branch, don't open a new PR

## Cloud vs local development

This project uses a two-topology dev setup — see `AGENTS.md §7` for the full spec. Short version:

- **Cloud sessions** (this Claude Code web session): research, small bounded changes, CI/doc edits, anything validated by `lint-and-mock`. No API keys, no Unity, no GPU in the sandbox.
- **Local sessions** (user's workstation): real provider keys, simulator/GPU
  resources when needed, and backend-specific services. Owns every task tagged
  `local-dev` on the issue tracker, plus any multi-round debug loop.

Rule of thumb: if a PR's core claim depends on real hardware or real VLM behavior, the first validation happens **locally**. CI is where that proof stays continuously live, not where it starts. In a cloud session, if you can't actually run the thing, say so explicitly in the PR — don't paper over it with "CI will tell us". File a `local-dev` issue (see #50 for template) and hand off.

**If the session IS local** (you have `docker`, real provider keys, and the
needed simulator/backend available): the cloud -> local handoff protocol does
not apply. Run the real thing yourself, iterate, and report what you observed.
No need to file a `local-dev` issue or split bounded changes away from
real-backend probes; a local session owns both. The cloud/local split exists to
stop cloud sessions from papering over missing validation; it does not
constrain a local session from carrying a full phase end-to-end.

### Local preflight ritual

Local preflight steps (key loading, Docker hygiene, ROS env stripping for
pytest) live in `AGENTS.md` §1. For the OpenClaw Gateway path specifically,
see `docs/human/openclaw/local.md`.

For local browser QA with gstack `browse` / Playwright, follow
`AGENTS.md` §1.1.3: if Chromium fails with `No usable sandbox!` on Ubuntu
24.04/AppArmor hosts, run browse commands with
`GSTACK_CHROMIUM_NO_SANDBOX=1` instead of changing system AppArmor or sysctl
settings.

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

- Use `./scripts/dev/run_pytest_standalone.sh` on hosts where ROS site-packages
  leak into pytest.
- Check `just dev::network-status` before OpenClaw or system-provider Claude
  workflows.
- Keep Isaac Lab in `.venv-isaaclab/`; do not mix it into the normal `.venv/`.
- Treat historical AI2-THOR/direct-VLM docs and reports as archived evidence,
  not current launch guidance.

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

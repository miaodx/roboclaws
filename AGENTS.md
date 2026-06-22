# AGENTS.md

This file defines the canonical operating playbook for coding agents working in
this repository. Its scope is the entire repo tree rooted at this directory.
Tool-specific files such as `CLAUDE.md` may add local guidance, but this file
owns repo-wide defaults and conflict resolution.

## 0) First-read policy (mandatory)

Before running any command, read only the orientation set in this order:

1. `README.md` (project orientation, what you can run, mode discovery)
2. `ARCHITECTURE.md` (code map, four operating modes, MCP contract)
3. `STATUS.md` (human-facing current focus, next action, and source links)
4. `AGENTS.md` (this file)
5. `CLAUDE.md`

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

If instructions conflict, priority is:
**system/developer/user prompt > AGENTS.md > CLAUDE.md > inferred defaults**.

---

## 1) Environment preflight (mandatory before tests)

### 1.1 Install dependencies

Roboclaws uses one repo-local Python environment per checkout/worktree:
`.venv/`, managed by `uv` from `pyproject.toml` and `uv.lock`. Treat that
folder as the canonical runtime for demos, tests, and scripts. Do not depend on
hidden external virtualenvs under `/tmp` or another repo for normal demo
operation. If a demo needs a new package, optional extra, or newer Python floor,
update `pyproject.toml` / `uv.lock` and rebuild or sync this repo's `.venv/`.
Use `uv sync` for declared project environments and `uv pip install` only for
explicit local one-off installs. Do not use plain `pip install` for repo setup.

For git worktrees, keep one `.venv/` at the root of each worktree. Do not share
one worktree's `.venv/` with another worktree; each checkout should be
self-contained.

```bash
uv sync --extra dev
```

The `dev` extra includes the standard MolmoSpaces/MuJoCo CPU runtime used by
local cleanup demos. Keep Isaac Lab out of this environment; it belongs in the
isolated `.venv-isaaclab/` runtime created by the Isaac preflight harness.
Install additional optional-extras groups only when a workflow explicitly needs
one.

Mainland China network note: if PyPI downloads are slow or flaky, keep mirror
selection machine-local via uv flags or environment variables, not committed
project metadata. Example:

```bash
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
  uv sync --extra dev
```

Use `uv sync` / `uv pip install` with mirrors as needed; do not switch to plain
`pip install`. Direct Git dependencies such as upstream MolmoSpaces may still
need normal GitHub access or a local network proxy.

### 1.1.1 Work-network guard

OpenClaw Gateway runs and system-provider Claude Code runs are not allowed on
the work network. OpenClaw is a private/maintainer path, not a current public
launch axis. The work network is detected by reachability of
`https://api-router.evad.mioffice.cn/`.
Check the current network before those workflows with:

```bash
just dev::network-status
```

If that command reports `network: work`, do not run `just openclaw::*`,
`just chat::run`, or OpenClaw integration/local verification gates. Do not run
system-provider Claude Code workflows on the
work network. Claude Code recipes may run there only when the repo-local `.env`
contains a supported MiMo, Kimi, or MiMo mify Anthropic key route. Codex recipes
default to `codex-router-responses` and may run there when `CODEX_BASE_URL` and
`CODEX_API_KEY` are configured; mimo-mify-responses and MiniMax are available only as explicit
`ROBOCLAWS_PROVIDER_PROFILE=mimo-mify-responses|minimax-responses` overrides with `XM_LLM_API_KEY` or
`MM_API_KEY`.
Model-only overrides do not bypass the guard. Guarded coding-agent recipes
should fail before launching when the work-network probe is reachable and no
allowed repo-local key route is available.

### 1.1.2 Coding-agent permissions

The pinned coding-agent Docker runtime is the only supported runtime for local
Codex / Claude Code household demos. Launch those demos through the public
catalog:

```bash
just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-public-labels
just run::surface surface=household-world agent_engine=claude-code preset=cleanup evidence_lane=world-public-labels
```

The recipes carry the required bypass-approval / bypass-sandbox flags and
isolate the agent to the task skill. New `just` recipes that launch Codex or
Claude Code must route through `run::surface`, the private `agent::*`
dispatcher, or `scripts/dev/coding_agent_docker.sh`.

Bare host `codex` or `claude` launches are unsupported and must not be used
unless the human explicitly asks for a system-CLI debugging run. If that happens,
state that it is outside the supported demo path.

### 1.1.3 Browser QA sandbox fallback

When using gstack `browse` / Playwright for local UI dogfooding, Ubuntu 24.04
hosts may fail Chromium startup with `No usable sandbox!` even when
`kernel.unprivileged_userns_clone=1`; AppArmor can still restrict
unprivileged user namespaces via `apparmor_restrict_unprivileged_userns=1`.
Do not weaken system AppArmor/sysctl settings for repo QA. Use the per-command
fallback instead:

```bash
GSTACK_CHROMIUM_NO_SANDBOX=1 browse goto http://127.0.0.1:<port>
```

Apply the same environment variable to other gstack `browse` commands in that
session. This is a local browser-test workaround only; it is not a demo runtime
setting and should not be committed into application code or launch recipes.

### 1.2 Simulator availability

The current public household routes use MolmoSpaces/MuJoCo by default, with
Isaac Lab and Agibot GDK behind explicit backend gates. Do not require
AI2-THOR for current household or planner-proof work.

### 1.3 Verify VLM access

Local sessions keep API keys in the repo-local `.env` (gitignored). Load them into
the current shell before running anything that calls a real VLM:

```bash
set -a && source .env && set +a
# Expected keys after source:
#   KIMI_API_KEY         — Kimi (Moonshot) coding-tier key, used by OpenClaw demos
#   NV_API_KEY           — Nvidia inference endpoints (optional)
#   MIMO_TP_KEY          — MiMo, default for the interactive chat path
#   XM_LLM_API_KEY       — internal multi-model aggregator; used by Codex only
#                           with ROBOCLAWS_PROVIDER_PROFILE=mimo-mify-responses, and by optional
#                           Claude mimo-mify-responses route
#   XM_LLM_BASE_URL      — optional override; defaults to https://api.llm.mioffice.cn/v1
#   XM_LLM_ANTHROPIC_BASE_URL — optional Claude mimo-mify-responses override; defaults to
#                               https://api.llm.mioffice.cn/anthropic
#   CODEX_BASE_URL / CODEX_API_KEY — default codex-router-responses endpoint for live agents
#   MM_BASE_URL / MM_API_KEY — optional MiniMax Responses endpoint for Codex
#                              and OpenAI Agents SDK profile=minimax-responses
```

Sanity check:

```bash
python -c "import os; assert os.environ.get('KIMI_API_KEY') or os.environ.get('MIMO_TP_KEY') or os.environ.get('NV_API_KEY') or os.environ.get('XM_LLM_API_KEY') or os.environ.get('CODEX_API_KEY') or os.environ.get('MM_API_KEY'), 'No provider key set — did you source .env?'"
```

`.env` is in `.gitignore` — do not commit, do not paste into logs / PRs / SUMMARY files.

### 1.4 Docker hygiene (OpenClaw local runs)

Before starting a new Gateway, make sure no stale one is still bound to the ports:

```bash
docker ps -a --format '{{.Names}}\t{{.Status}}' | grep -E 'openclaw-gateway' || echo "no stale gateway"
# If a gateway is still running from an earlier session:
docker rm -f openclaw-gateway

# While you're there, consider stopping other unused containers on the same host
# that you no longer need — Gateway needs ports 18788/18789 free:
docker ps --format '{{.Names}}\t{{.Image}}'
```

After your run, leave the Gateway on `profile: minimal` (production-intent state) or
tear it down explicitly: `docker rm -f openclaw-gateway`. Do NOT leave it on
`profile: coding` — see `.planning/milestones/v1.98-phases/02.6-openclaw-mcp-tools-integration/` threat T-02.6-27.

### 1.5 Pytest env isolation (machine-local)

On systems with ROS jazzy installed (this host, for example), `pytest` picks up
`/opt/ros/jazzy/lib/python3.12/site-packages/launch_testing` and fails on a missing
`lark` import. Use the repo wrapper to run tests in a minimal environment:

```bash
./scripts/dev/run_pytest_standalone.sh -x -q
```

This is a machine-local quirk, not a repo issue.

---

## 2) Standard test workflow

### 2.1 Full tests

```bash
pytest -q
```

### 2.2 Run a specific demo

Use `just` recipes. The public command grammar is intentionally small:

```bash
just run::surface surface=household-world agent_engine=direct-runner preset=map-build evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-public-labels
just run::surface surface=household-world agent_engine=codex-cli prompt="find something useful to drink"
just agent::verify mock                          # maintainer confidence gate
```

See [`docs/human/contributing.md`](docs/human/contributing.md#dev-tooling-uv-and-just)
for the one-line install + tab-completion setup. See [`just/README.md`](just/README.md)
for the launch-axis grammar and prompt mappings.

---

## 3) Lint/type checks

```bash
ruff check .
ruff format --check .
```

---

## 4) Key technical constraints

1. **Public launch axes stay canonical**: use `surface`, `world`, `backend`, `intent`, `agent_engine`, `provider_profile`, `evidence_lane`, and `camera_labeler` instead of old task/profile wrappers.
2. **Base Navigation Map is the start-of-run map contract**: do not expose private relocation/scoring truth, static movable-object inventory, or full fixture tables as default agent input.
3. **Runtime Metric Map owns semantic enrichment**: map-build and observations create public anchors, target candidates, and observed-object evidence.
4. **VLM output parsing must be robust**: model-backed runs may return malformed JSON or partial tool arguments. Always wrap parsing in try/except with a safe recovery path.
5. **Cost guard**: default to cheap provider profiles for development (Kimi/MiMo/codex-router-responses as appropriate) and record model usage/cost when live agents run. See `docs/human/model-matrix.md` for current verified models.
6. **Every addition names an architecture layer**: new behavior, surfaces,
   presets, server adapters, agent engines, provider profiles, MCP tools,
   skills, backends, eval suites, reports, or artifact contracts must name
   their owning layer from `ARCHITECTURE.md` in the plan, PR note, or doc
   update. If no existing layer fits, stop and update `ARCHITECTURE.md` or
   record a focused architecture decision before implementation.
7. **Server logic stays thin**: server/runtime code is transport and lifecycle
   plumbing only: MCP target routing, host/port, readiness, locks, run dirs,
   live status, operator-console launch control, and eval live-run polling.
   Do not put cleanup/search/map-build strategy, prompt policy, private scorer
   truth, benchmark-specific hints, or opaque multi-tool task shortcuts in
   server adapters. Put strategy in skills first; put reusable public robot
   capabilities in MCP only after the promotion rule is satisfied.
8. **No silent fallback or compatibility shims**: do not add backward-compatible
   branches for obsolete call shapes, artifact names, providers, surfaces, or
   generated files unless the human explicitly requests that compatibility. If
   a required dependency, config, runtime, or artifact is missing or malformed,
   fail loudly with an actionable error instead of substituting another source
   or silently degrading behavior.

---

## 5) Implementation priorities

This is a thin demo repo. Priorities:

1. **Get it working end-to-end** over making it elegant
2. **Generate visible output** (screenshots, GIFs, videos) for every feature
3. **Log everything** (VLM prompts, responses, game state) for debugging
4. **Keep dependencies minimal**: avoid adding packages unless the active
   surface/backend needs them and they are declared in `pyproject.toml`

### 5.1 Legacy support policy

This repo has no backward-compatibility burden unless the human explicitly asks
for it. When you see code, docs, tests, skills, or recipes labeled `legacy`,
`current-contract`, or kept only for compatibility, treat them as removal or
replacement candidates, not as APIs to preserve.

Prefer the current docs and active profile contracts over preserving old paths.
If a legacy surface conflicts with a cleaner current design, update or delete
the legacy surface and its tests/docs in the same scoped change. Preserve a
legacy path only when the user explicitly asks for it.

Do not add lower-level runner, artifact, `just`, or dispatcher shims solely for
old names or old call shapes. Persisted schema and artifact version identifiers
remain versioned contracts unless the active task explicitly changes them.
When a current contract requires a specific artifact or runtime, missing input
is a blocker, not permission to fall back to an older artifact.

---

## 6) Commit hygiene

- Keep commits scoped: `feat: add cleanup report gate`, `fix: handle provider timeout`
- Commit messages: `type: description` format
- Multiple agents may edit the same checkout at the same time. Before committing,
  inspect `git status --short` and `git diff --cached`; stage only files or hunks
  that belong to your current task.
- Do not use broad staging or commit shortcuts such as `git add -A`, `git add .`,
  or `git commit -a` in a shared checkout. Prefer explicit pathspecs,
  `git add -p`, or a temporary `GIT_INDEX_FILE` index when the worktree already
  contains unrelated changes.
- Do not reset, restore, unstage, or commit another agent's work unless the human
  explicitly asks for that. If a file contains mixed edits that cannot be safely
  separated, leave it uncommitted and report the blocker instead of sweeping in
  unrelated changes.
- If a commit is created by Codex, include `Co-authored-by: Codex <codex@users.noreply.github.com>`
- If a commit is created by another AI coding agent, include a corresponding co-author trailer.

---

## 7) Cloud vs local development split

This project runs agents in two topologies that complement each other. Pick the right
one for the task; don't try to validate a real simulator / real provider / real robot
outcome in a cloud sandbox and don't burn local wall-clock on tasks that a cloud
session could close in minutes.

### 7.1 Cloud agent (Claude Code on the web, this sandbox)

No GPU, no display, no robot backend, typically no VLM/API keys. Good for:

- Research / survey questions across the repo
- Small bounded code changes fully covered by the `lint-and-mock` CI job
- CI workflow edits, `ruff` / `pytest` fixes, doc edits
- Opening issues / PRs, triaging labels, updating roadmaps
- Anything whose success criterion is "tests pass" or "existing mock pipeline
  still works"

**Don't** use a cloud session to validate:

- Real Kimi / Claude / GPT behavior on real frames
- Real simulator rendering, robot navigation, physics, or backend-specific
  map/pose correctness
- Real OpenClaw Gateway docker-compose integration
- Anything needing multi-round debug iteration against a live service

If you wrote a change whose **claim** depends on real hardware / real API calls,
say so explicitly in the PR description ("unvalidated locally, relies on the
next CI run against `main`") rather than implying it was exercised.

### 7.2 Local agent (user's workstation)

Has real provider keys, local simulator/GPU/display resources when needed, and
can run backend-specific services locally.
Required for any task tagged `local-dev` on the issue tracker. Good for:

- End-to-end validation of a new feature with real provider and simulator/backend
- Long-running multi-round debug loops (agents stuck in furniture, VLM choosing
  nonsense actions, OpenClaw session memory growth)
- Taking the GIFs / screenshots that feed the README demo matrix
- Anything that depends on the GitHub Actions CI **already being green** — the
  local session is where the first run happens, CI is where it stays green

### 7.3 Handoff protocol

- **Cloud → local**: when a cloud session lands a change that needs real-world
  validation, it opens a `local-dev` issue enumerating the exact commands to run
  and the acceptance criteria (final `terminate_reason`, coverage fraction,
  cost, etc.). Example template: see issue #50.
- **Local → cloud**: when a local debug session uncovers a bug or concludes a
  feature works, it either closes the `local-dev` issue with a dated comment
  (log + `report.html` attached) or files a regression issue the cloud session
  can pick up.
- CI's role is **continuous proof**, not first validation. If a PR's only
  evidence is "CI will tell us", that's a cloud-session habit to break.

---

## 8) Planning workflow

Use the `hybrid-phase-pipeline` skill when available. It is the router for
combining Matt-style skills, gstack review, and GSD without duplicating process.

Invariant: one source of truth per stage, with `STATUS.md` as the short
human-facing dashboard.

- Current orientation: `STATUS.md`.
- Before execution: `docs/plans/*.md` or GitHub issues.
- During execution: `.planning/STATE.md` and `.planning/phases/*`.
- After shipping: summaries, verification reports, and retrospectives.

Do not create `.planning/phases/*` for brainstorming. Once a phase is under GSD,
execute and ship it with GSD (`/gsd-execute-phase`, `/gsd-ship`) unless the user
explicitly changes the workflow.

Root `PLAN.md` is retained only for compatibility and must not receive new
active phase content. Current focus and the active source links are in
`STATUS.md`. During GSD closeout/verify/ship, update `STATUS.md` when current
focus, latest phase, next action, or blocker changed; keep it short and do not
mirror `.planning/STATE.md`. For parallel standalone terminal work, use one
task-owned file under `docs/status/active/` instead of editing `STATUS.md` for
routine progress.

## 9) Just command routing

When a user asks in natural language to run a demo, cleanup task, or proof task,
translate it to the composable public surface/preset command instead of
searching for a bespoke recipe name.

When a plan, diff, PR, or handoff asks which verification gates or evals to run
for agent-facing changes, prefer the eval harness:

```bash
just agent::eval recommend plan=<path> budget=focused
just agent::eval execute since=<base> budget=focused
```

Use this instead of hand-writing fixed live/product/eval lists. The harness
selects deterministic gates, product rows, eval-suite rows, live-agent eval
rows, perception/DINO rows, simulator rows, and map/cleanup-consumer rows from
plan, diff, or explicit axis signals, and records run/skipped/blocked rationale
under `output/eval-harness/`.

Primary grammar:

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [intent=<intent>] [provider_profile=<profile>] [key=value ...]
```

Use `report=visual` by default for non-Molmo surfaces. For household cleanup,
use `evidence_lane=world-public-labels` by default. `smoke` is a verification
preset or private runner mode, not a public evidence lane.
For household, omit `preset=` for open-ended prompt-driven work; use
`preset=cleanup prompt=...` only when the prompt explicitly narrows cleanup
scope.

Examples:

- "run the map-build task" -> `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino`
- "run the household cleanup task with codex" -> `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-router-responses evidence_lane=world-public-labels`
- "run an open-ended household goal with codex" -> `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-router-responses prompt="我渴了，帮我找些解渴的东西"`
- "run the planner proof dry run" -> `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run`

Use `agent::*` for deeper maintainer control:

```bash
just agent::run <task> <driver> [report] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up|down
just agent::gateway up|down|pull-image
```

Lower modules (`openclaw::*`, `molmo::*`, `harness::*`, `verify::*`,
`mcp::*`, `code::*`, `chat::*`, `dev::*`) are private
implementation details. They remain runnable for debugging, but are hidden from
completion and should not be the first choice for natural-language run requests.

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

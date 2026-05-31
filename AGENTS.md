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

If a new optional-extras group is needed (e.g. `[openclaw]` for the MCP server),
install it with `uv sync --extra dev --extra openclaw`.
For real MolmoSpaces/MuJoCo demos, use
`uv sync --extra dev --extra molmospaces`.

Mainland China network note: if PyPI downloads are slow or flaky, keep mirror
selection machine-local via uv flags or environment variables, not committed
project metadata. Example:

```bash
UV_DEFAULT_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple \
  uv sync --extra dev --extra molmospaces
```

Use `uv sync` / `uv pip install` with mirrors as needed; do not switch to plain
`pip install`. Direct Git dependencies such as upstream MolmoSpaces may still
need normal GitHub access or a local network proxy.

### 1.1.1 Work-network guard

OpenClaw Gateway runs and system-provider Claude Code runs are not allowed on
the work network. The work network is detected by reachability of
`https://api-router.evad.mioffice.cn/`.
Check the current network before those workflows with:

```bash
just dev::network-status
```

If that command reports `network: work`, do not run `just openclaw::*`,
`just chat::run`, `just appliance::run`, or OpenClaw integration/local
verification gates. Do not run system-provider Claude Code workflows on the
work network. Claude Code recipes may run there only when the repo-local `.env`
contains a supported MiMo, Kimi, or mify Anthropic key route. Codex recipes may
run there when `XM_LLM_API_KEY` configures the default repo-local mify route, or
when `CODEX_BASE_URL` and `CODEX_API_KEY` configure an explicit non-mify Codex route.
Model-only overrides do not bypass the guard. Guarded coding-agent recipes
should fail before launching when the work-network probe is reachable and no
allowed repo-local key route is available.

### 1.1.2 Coding-agent permissions

The pinned coding-agent Docker runtime is the only supported public route for
local Codex / Claude Code demos. Use `just code::codex` or `just code::cc` for
direct coding-agent demos; those recipes carry the required bypass-approval /
bypass-sandbox flags and isolate the agent to the task skill. New `just`
recipes that launch Codex or Claude Code must call those recipes or
`scripts/dev/coding_agent_docker.sh`.

Bare host `codex` or `claude` launches are unsupported and must not be used
unless the human explicitly asks for a system-CLI debugging run. If that happens,
state that it is outside the supported demo path.

### 1.2 Verify AI2-THOR is available

```bash
python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"
```

Note: AI2-THOR will download a Unity build (~1GB) on first use.

### 1.3 Verify VLM access

Local sessions keep API keys in the repo-local `.env` (gitignored). Load them into
the current shell before running anything that calls a real VLM:

```bash
set -a && source .env && set +a
# Expected keys after source:
#   KIMI_API_KEY         — Kimi (Moonshot) coding-tier key, used by OpenClaw demos
#   NV_API_KEY           — Nvidia inference endpoints (optional)
#   MIMO_TP_KEY          — MiMo, default for the interactive chat path
#   XM_LLM_API_KEY       — internal multi-model aggregator, default Codex route
#                           and optional Claude mify route
#   XM_LLM_BASE_URL      — optional override; defaults to https://api.llm.mioffice.cn/v1
#   XM_LLM_ANTHROPIC_BASE_URL — optional Claude mify override; defaults to
#                               https://api.llm.mioffice.cn/anthropic
#   CODEX_BASE_URL / CODEX_API_KEY — optional non-mify Codex endpoint for live agents
```

Sanity check:

```bash
python -c "import os; assert os.environ.get('KIMI_API_KEY') or os.environ.get('MIMO_TP_KEY') or os.environ.get('NV_API_KEY') or os.environ.get('XM_LLM_API_KEY') or os.environ.get('CODEX_API_KEY'), 'No provider key set — did you source .env?'"
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

```bash
python examples/games/single_agent_explore.py --steps 20 --model gpt-4o-mini
python examples/games/territory_game.py --agents 2 --steps 50 --scene FloorPlan201
```

Or use `just` recipes. The public command grammar is intentionally small:

```bash
just task::run ai2thor-nav openclaw              # normal OpenClaw navigation
just task::run household-cleanup codex smoke      # cheap synthetic cleanup iteration
just agent::verify mock                          # maintainer confidence gate
```

See [`docs/human/contributing.md`](docs/human/contributing.md#dev-tooling-uv-and-just)
for the one-line install + tab-completion setup. See [`just/README.md`](just/README.md)
for the task/driver/report grammar and prompt mappings.

---

## 3) Lint/type checks

```bash
ruff check .
ruff format --check .
```

---

## 4) Key technical constraints

1. **AI2-THOR multi-agent is synchronous**: `controller.step()` moves one agent per call. Game logic must implement turn-based stepping.
2. **Use iTHOR scenes only**: ProcTHOR has multi-agent bugs (GitHub Issues #1169, #1265). Stick to FloorPlan1-430.
3. **VLM output parsing must be robust**: VLMs sometimes return malformed JSON. Always wrap parsing in try/except with fallback to a safe action (e.g., `RotateRight`).
4. **Image encoding**: Use JPEG quality 60-80 for VLM input to balance cost and quality. Resize to 320×240 or 640×480.
5. **Cost guard**: Default to a cheap provider for development (Kimi/MiMo); switch to Claude/GPT-4o for final demos. See `docs/human/model-matrix.md` for current verified models. Example scripts should expose a `--model` flag and log cumulative API cost per game.

---

## 5) Implementation priorities

This is a thin demo repo. Priorities:

1. **Get it working end-to-end** over making it elegant
2. **Generate visible output** (screenshots, GIFs, videos) for every feature
3. **Log everything** (VLM prompts, responses, game state) for debugging
4. **Keep dependencies minimal**: ai2thor, anthropic/openai, Pillow, numpy

### 5.1 Legacy support policy

This repo has no backward-compatibility burden for obsolete demo surfaces. When
you see code, docs, tests, skills, or recipes labeled `legacy`, `current-contract`,
or kept only for compatibility, treat them as removal or replacement candidates,
not as APIs to preserve.

Prefer the current docs and active profile contracts over preserving old paths.
If a legacy surface conflicts with a cleaner current design, update or delete
the legacy surface and its tests/docs in the same scoped change. Preserve a
legacy path only when the user explicitly asks for it or when it is still the
sole working route for the requested demo.

---

## 6) Commit hygiene

- Keep commits scoped: `feat: add territory game logic`, `fix: handle VLM timeout`
- Commit messages: `type: description` format
- If a commit is created by Codex, include `Co-authored-by: Codex <codex@users.noreply.github.com>`
- If a commit is created by another AI coding agent, include a corresponding co-author trailer.

---

## 7) Cloud vs local development split

This project runs agents in two topologies that complement each other. Pick the right
one for the task; don't try to validate a real-AI2-THOR / real-VLM outcome in a cloud
sandbox and don't burn local wall-clock on tasks that a cloud session could close in
minutes.

### 7.1 Cloud agent (Claude Code on the web, this sandbox)

No GPU, no display, no AI2-THOR Unity build, typically no VLM API keys. Good for:

- Research / survey questions across the repo
- Small bounded code changes fully covered by the `lint-and-mock` CI job
- CI workflow edits, `ruff` / `pytest` fixes, doc edits
- Opening issues / PRs, triaging labels, updating roadmaps
- Anything whose success criterion is "tests pass" or "existing mock pipeline
  still works"

**Don't** use a cloud session to validate:

- Real Kimi / Claude / GPT behavior on real frames
- Real AI2-THOR rendering, multi-agent collision, or `GetReachablePositions`
  correctness
- Real OpenClaw Gateway docker-compose integration
- Anything needing multi-round debug iteration against a live service

If you wrote a change whose **claim** depends on real hardware / real API calls,
say so explicitly in the PR description ("unvalidated locally, relies on the
next CI run against `main`") rather than implying it was exercised.

### 7.2 Local agent (user's workstation)

Has real VLM keys, real AI2-THOR + GPU/X, can run the OpenClaw Gateway locally.
Required for any task tagged `local-dev` on the issue tracker. Good for:

- End-to-end validation of a new feature with real Kimi + real Unity
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

When a user asks in natural language to run a demo, cleanup task, proof task, or
verification gate, translate it to the composable public surface instead of
searching for a bespoke recipe name.

Primary grammar:

```bash
just task::run <task> <driver> [report] [key=value ...]
```

Use `visual` by default for non-Molmo tasks. For Molmo cleanup, use
`world-labels` by default and `smoke` when the prompt asks for cheap,
semantic, or fast AI-agent iteration evidence.

Examples:

- "run the semantic map build task" -> `just task::run semantic-map-build direct world-labels`
- "run the household cleanup task with codex" -> `just task::run household-cleanup codex world-labels`
- "run the household cleanup task with codex with smoke profile" -> `just task::run household-cleanup codex smoke`
- "run the ai2thor nav task with openclaw" -> `just task::run ai2thor-nav openclaw visual`

Use `agent::*` for deeper maintainer control:

```bash
just agent::run <task> <driver> [report] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up|down
just agent::gateway up|down|pull-image
```

Lower modules (`openclaw::*`, `vlm::*`, `molmo::*`, `harness::*`, `verify::*`,
`mcp::*`, `code::*`, `chat::*`, `appliance::*`, `dev::*`) are private
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

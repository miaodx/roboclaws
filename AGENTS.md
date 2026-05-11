# AGENTS.md

This file defines the default operating playbook for coding agents working in this repository.
Its scope is the entire repo tree rooted at this directory.

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

```bash
uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"
```

Prefer `uv` when available — it's faster and already used for the venv at `.venv/`.
If a new optional-extras group is needed (e.g. `[openclaw]` for the MCP server),
install it with `uv pip install -e ".[dev,openclaw]"`.

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
#   ANTHROPIC_API_KEY or OPENAI_API_KEY — direct VLM path (optional)
```

Sanity check:

```bash
python -c "import os; assert os.environ.get('KIMI_API_KEY') or os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'), 'No VLM API key set — did you source .env?'"
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
`profile: coding` — see `.planning/phases/02.6-openclaw-mcp-tools-integration/` threat T-02.6-27.

### 1.5 Pytest env isolation (machine-local)

On systems with ROS jazzy installed (this host, for example), `pytest` picks up
`/opt/ros/jazzy/lib/python3.12/site-packages/launch_testing` and fails on a missing
`lark` import. Use the repo wrapper to run tests in a minimal environment:

```bash
./scripts/run_pytest_standalone.sh -x -q
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
python examples/single_agent_explore.py --steps 20 --model gpt-4o-mini
python examples/territory_game.py --agents 2 --steps 50 --scene FloorPlan201
```

Or use `just` recipes (`just --list` for the full grouped list):

```bash
just dev::test all                              # full repo confidence (lint + tests)
just openclaw::run photo                         # autonomous chair/sofa photo smoke
just chat::run                                  # OpenClaw Gateway + browser Control UI
DEMO_PASSWORD=demo just appliance::run local      # Railway-style hosted appliance
```

See [`docs/human/contributing.md`](docs/human/contributing.md#dev-tooling-uv-and-just)
for the one-line install + tab-completion setup. Modules:
`openclaw`, `vlm`, `chat`, `appliance`, `dev` — each maps to a file in `just/`.

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

# Contributing to Roboclaws

## Development setup

```bash
git clone https://github.com/MiaoDX/roboclaws.git
cd roboclaws
uv sync --extra dev
```

Run the linter and tests before every commit:

```bash
ruff check .
ruff format --check .
pytest
```

## Dev tooling: `uv` and `just`

Two helper binaries make the day-to-day workflows tolerable. Both are single
binaries with no system-package dependencies — install once, forget.

| Tool | What it does | Why we use it |
|------|--------------|---------------|
| [`uv`](https://docs.astral.sh/uv/) | project environment manager | `uv sync --extra dev --extra openclaw` builds the repo-local `.venv/` from `pyproject.toml` and `uv.lock` |
| [`just`](https://just.systems/) | command runner | replaces the `Makefile` matrix; human-facing runs use `just task::run <task> <driver> [report]` with lower-level modules hidden from completion but still available for debugging |

### Install

```bash
# uv — single binary, into ~/.local/bin
curl -LsSf https://astral.sh/uv/install.sh | sh

# just — single binary, into ~/.local/bin (Ubuntu apt is stuck at 1.21,
# which predates module support; use the official script)
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh \
  | bash -s -- --to ~/.local/bin

# Verify (just modules need ≥ 1.31 — current is 1.50+)
uv --version
just --version
```

If either binary isn't found after install, add `~/.local/bin` to your `$PATH`
(`export PATH="$HOME/.local/bin:$PATH"` in your shell rc).

### Discover recipes

```bash
just                       # default: prints the small public facade
just --list                # same
just --list task           # human-facing task grammar
just --list agent          # maintainer dispatchers
just --summary             # task::run plus compact agent::* dispatchers
```

Invoke recipes with the `module::recipe` form:

```bash
just task::run ai2thor-nav openclaw
just task::run household-cleanup codex smoke
just agent::verify mock
just agent::verify ci-required
```

`just <module> <recipe>` (space-separated) also works, but `module::recipe`
keeps the namespace visible at a glance.

### Tab completion (one-time per machine)

`just`'s install script does **not** wire up shell completions. Run this
once to make `just <TAB>`, `just task::<TAB>`, `just agent::<TAB>`, etc.
work in any directory that has a `justfile`:

```bash
echo 'source <(just --completions bash)' >> ~/.bashrc
source ~/.bashrc
```

Zsh / fish equivalents:

```bash
just --completions zsh  > ~/.zfunc/_just                            # zsh (ensure ~/.zfunc is in fpath)
just --completions fish > ~/.config/fish/completions/just.fish      # fish
```

This is per-machine, not per-repo — the completion script reads whichever
`justfile` is in the current directory, so it works for every `just` project
you ever clone.

## Development topology: cloud + local

Day-to-day work on this repo is split between two kinds of sessions, sized
accordingly. The full playbook lives in [`AGENTS.md §7`](../../AGENTS.md);
contributors should read it before picking up work.

| | Cloud session (Claude Code on the web) | Local session (your workstation) |
|---|---|---|
| Has VLM API keys? | no | yes |
| Has AI2-THOR Unity + GPU/display? | no | yes |
| Can run OpenClaw Gateway? | no | yes |
| Typical tasks | research, CI edits, doc edits, mock-covered refactors, opening issues | anything `local-dev`-tagged, real-model validation, long debug loops |
| Validation ceiling | `ruff` + `pytest` + mock-engine HTML demo pipeline | real Kimi + real Unity end-to-end |

**The first validation of a real-model claim happens in a local session**, not
in CI. CI's role is to keep that proof continuously live for anyone reading the
repo. When a cloud session lands a change whose core claim depends on real
hardware (e.g. "territory terminates early on real AI2-THOR"), it files a
`local-dev` issue with exact commands + acceptance criteria, and hands off. See
issue #50 for the template.

## CI overview

CI has one required fast job plus several push-to-`main` smoke/report jobs:

| Job | Trigger | Purpose |
|-----|---------|---------|
| `lint-and-mock` | every push + PR | `just agent::verify ci-required`: ruff lint, format check, pytest, mock-engine HTML demo |
| `real-model-smoke` | push to `main` only | 100-step Kimi + real AI2-THOR territory + coverage games |
| `openclaw-smoke` | push to `main` only (`continue-on-error`) | ephemeral Gateway + Kimi navigation smoke |
| `territory-openclaw-smoke` | push to `main` only (`continue-on-error`) | OpenClaw-backed territory smoke |
| `coverage-openclaw-smoke` | push to `main` only (`continue-on-error`) | OpenClaw-backed coverage smoke |
| `photo-task-smoke` | push to `main` with `[photo-smoke]` in the commit message | chair/sofa photo-task smoke scored by `scripts/openclaw/check_photo_task.py` |
| `publish-pages` | push to `main` after required smoke inputs | publishes mock, real-model, and available OpenClaw reports to GitHub Pages |

## Secrets required for CI

### `KIMI_API_KEY`

**What it is:** API key for the [Moonshot AI (Kimi)](https://platform.moonshot.cn/) service.
Roboclaws uses the Kimi model in CI because it is OpenAI-compatible, cost-effective
(~¢8 per 100-step 2-game smoke run), and does not require a separate SDK.

**Where to get it:**
1. Sign up at <https://platform.moonshot.cn/>.
2. Navigate to **API Keys** in the dashboard and create a new key.

**How to add it to GitHub Actions:**
1. Open your fork / the repository on GitHub.
2. Go to **Settings → Secrets and variables → Actions**.
3. Click **New repository secret**.
4. Name: `KIMI_API_KEY`; Value: your key (starts with `sk-`).

**Local validation:**

```bash
KIMI_API_KEY=sk-... python scripts/dev/check_kimi_key.py
```

A successful run prints:

```
response: {"action": "MoveAhead"}
✓ KIMI_API_KEY is valid and returns parseable JSON
```

## Headless AI2-THOR on Linux

AI2-THOR requires a display.  On CI (and headless servers) use `xvfb-run`:

```bash
sudo apt-get install xvfb libgl1 libglib2.0-0
xvfb-run python examples/games/territory_game.py --agents 2 --steps 5 --model mock
```

The Unity binary (~1 GB) is downloaded to `~/.ai2thor/` on first run and
cached by the CI workflow automatically.

## Git workflow

- Branch from `main`.
- Commit messages: `type: description` (feat, fix, ci, docs, refactor).
- Push to a feature branch and open a PR targeting `main`.

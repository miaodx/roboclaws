# Contributing to Roboclaws

## Development setup

```bash
git clone https://github.com/MiaoDX/roboclaws.git
cd roboclaws
pip install -e ".[dev]"
```

Run the linter and tests before every commit:

```bash
ruff check .
ruff format --check .
pytest
```

## Development topology: cloud + local

Day-to-day work on this repo is split between two kinds of sessions, sized
accordingly. The full playbook lives in [`AGENTS.md §7`](../AGENTS.md);
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

Up to three jobs run on every push / PR (the third only when the Railway secret
is configured):

| Job | Trigger | Purpose |
|-----|---------|---------|
| `lint-and-mock` | every push + PR | ruff lint, format check, pytest, mock-engine HTML demo |
| `real-model-smoke` | push to `main` only | 100-step Kimi + real AI2-THOR territory + coverage games |
| `openclaw-railway-smoke` | push to `main` only (`continue-on-error`) | 3-step ping against a user-deployed Railway OpenClaw Gateway |

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
KIMI_API_KEY=sk-... python scripts/check_kimi_key.py
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
xvfb-run python examples/territory_game.py --agents 2 --steps 5 --model mock
```

The Unity binary (~1 GB) is downloaded to `~/.ai2thor/` on first run and
cached by the CI workflow automatically.

## Git workflow

- Branch from `main`.
- Commit messages: `type: description` (feat, fix, ci, docs, refactor).
- Push to a feature branch and open a PR targeting `main`.

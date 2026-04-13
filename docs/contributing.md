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

## CI overview

Two jobs run on every push / PR:

| Job | Trigger | Purpose |
|-----|---------|---------|
| `lint-and-mock` | every push + PR | ruff lint, format check, pytest (all mock-based) |
| `real-model-smoke` | push to `main` only | validates Kimi API key; future: 5-step territory game |

## Secrets required for CI

### `KIMI_API_KEY`

**What it is:** API key for the [Moonshot AI (Kimi)](https://platform.moonshot.cn/) service.
Roboclaws uses the Kimi model in CI because it is OpenAI-compatible, cost-effective
(~$0.001 per 5-step smoke run), and does not require a separate SDK.

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

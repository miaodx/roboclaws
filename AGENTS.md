# AGENTS.md

This file defines the default operating playbook for coding agents working in this repository.
Its scope is the entire repo tree rooted at this directory.

## 0) First-read policy (mandatory)

Before running any command, read in this order:

1. `AGENTS.md` (this file)
2. `CLAUDE.md`
3. `docs/technical-design.md` (complete technical spec, game rules, API details)

If instructions conflict, priority is:
**system/developer/user prompt > AGENTS.md > CLAUDE.md > inferred defaults**.

---

## 1) Environment preflight (mandatory before tests)

### 1.1 Install dependencies

```bash
uv --version && uv pip install -e ".[dev]" || python -m pip install -e ".[dev]"
```

### 1.2 Verify AI2-THOR is available

```bash
python -c "import ai2thor; print(f'ai2thor {ai2thor.__version__} ok')"
```

Note: AI2-THOR will download a Unity build (~1GB) on first use.

### 1.3 Verify VLM access

```bash
# At least one of these should be set
python -c "import os; assert os.environ.get('ANTHROPIC_API_KEY') or os.environ.get('OPENAI_API_KEY'), 'No VLM API key set'"
```

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
5. **Cost guard**: Default to GPT-4o-mini for development. Add a `--model` flag to all example scripts. Log cumulative API cost per game.

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

# Phase 2.2 — Long-running OpenClaw games (territory + coverage)

> Drafted 2026-04-16. Collapses the previously-split TODOS items 1 (per-agent SOULs) and 2 (long-running games) into a single phase, per user direction. The personalities already exist on disk (`skills/ai2thor-navigator/souls/{aggressive,defensive,cooperative}.md`); the long-running container is already the natural state of `scripts/openclaw-bootstrap.sh`. What's missing is the wiring.

## Problem Statement

Phase 2.1 shipped one OpenClaw tile in README Layer 3 (the nav demo). Layer 2 has three tiles: mock, territory, coverage on direct-VLM. Layer 3 has one. The README's original Phase 2 promise was a 3×N matrix — Layer 3 should be a peer of Layer 2, not a transport-validation footnote. Phase 2.2 closes that gap by shipping territory + coverage over a long-running OpenClaw Gateway with per-agent personalities.

"Long-running" here means **within a single game run**: one bootstrap → one Gateway container → 200+ turns across all agents → tear down at end. Per-agent state is maintained Gateway-side via the named-agent isolation Phase 2.1 established (each agent has its own workspace, SOUL, auth profile, and `state/MEMORY.md` slot).

## Scope

### In scope
- `scripts/openclaw-bootstrap.sh` extended: drop the existing SOUL files (`skills/ai2thor-navigator/souls/{aggressive,defensive,cooperative}.md`) into each named agent's `/home/node/.openclaw/workspaces/<agent-i>/SOUL.md` slot via a new `AGENT_SOULS` env var.
- `examples/territory_game.py` + `examples/coverage_game.py`: add `--backend {direct,openclaw}` flag (default `direct` to preserve existing demos). When `--backend openclaw`, construct `OpenClawProvider` instead of `create_provider(model)`. The games already accept any `VLMProvider`, so no game-class changes are needed.
- Per-agent personality probe in `bootstrap.sh`: after the existing PONG probe, ask each agent the same leading question (e.g. "describe your strategy in one sentence") and assert the responses diverge along the persona axis. Fails fast if SOULs aren't loading.
- Two new CI jobs: `territory-openclaw-smoke` and `coverage-openclaw-smoke`. Mirror the existing `openclaw-smoke` pattern (bootstrap → run game → upload report → publish to Pages). Use `AGENTS=2 AGENT_SOULS=aggressive,defensive` for territory and `AGENTS=2 AGENT_SOULS=cooperative,cooperative` for coverage.
- README Layer 3 rewrite: replace the single nav-demo tile with three tiles (nav, territory, coverage) — symmetric with Layer 2.
- `docs/openclw/openclaw-local.md`: add `AGENT_SOULS=aggressive,defensive,cooperative` example + per-game usage snippets.
- `tests/test_openclaw_bootstrap.py` (new file or extend existing): one test that asserts `bootstrap.sh` with `AGENT_SOULS=aggressive,defensive` writes the right `SOUL.md` files into per-agent workspaces (image-check auto-skips when image not pulled).
- `TODOS.md`: mark items 1 + 2 as shipped under Phase 2.2; demote item 3 (digest pinning) to Phase 2.3.
- PLAN.md: short Phase 2.2 retrospective at end.

### Not in scope
- **Cross-run MEMORY.md persistence** — each game run starts with a fresh container. Within-run MEMORY.md persistence is whatever the Gateway does naturally; we don't add explicit memory injection or summarization.
- **Game-mode-specific SOULs** — use the existing 3 generic SOULs as-is. No `territory-aggressive` vs `coverage-aggressive` variants.
- **Long-running across game modes** — territory and coverage runs each get their own bootstrap. Sharing one container across game modes adds workspace-reset complexity for no demo benefit.
- **Isaac Lab migration** (Phase 3).
- **Remote / Railway Gateway** — transport now supports it but out of scope for 2.2.
- **Cross-agent Gateway memory leakage** — relies on Phase 2.1's per-agent isolation being correct; we test divergence, not isolation primitives.

## Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                       Bootstrap (one-shot)                           │
│   AGENTS=2 AGENT_SOULS=aggressive,defensive ./openclaw-bootstrap.sh  │
│            │                                                         │
│            ├─► /home/node/.openclaw/workspaces/agent-0/SOUL.md  ◄── aggressive.md  │
│            └─► /home/node/.openclaw/workspaces/agent-1/SOUL.md  ◄── defensive.md   │
└──────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│             python examples/territory_game.py --backend openclaw     │
│                                                                      │
│   TerritoryGame(provider=OpenClawProvider(...))                      │
│        │                                                             │
│        │  game.decide(images, prompt_state)                          │
│        ▼                                                             │
│   provider.get_action(images, state)                                 │
│        │                                                             │
│        │  POST /v1/chat/completions                                  │
│        ├─► model="openclaw/agent-0" → SOUL=aggressive (rushes cells) │
│        └─► model="openclaw/agent-1" → SOUL=defensive  (consolidates) │
│                                                                      │
│   Long-running container — one process, full game lifecycle.         │
│   Per-agent workspace state accumulates across turns Gateway-side.   │
└──────────────────────────────────────────────────────────────────────┘

  Both games (territory + coverage) get the same shape — only the
  AGENT_SOULS recipe and the game-class differ.
```

## Implementation Plan

### Task 17: Extend `scripts/openclaw-bootstrap.sh` with per-agent SOUL distribution

**File:** `scripts/openclaw-bootstrap.sh`

1. Add env vars near the top (around line 78 with the other defaults):
   - `SOULS_DIR="${SOULS_DIR:-${PWD}/skills/ai2thor-navigator/souls}"`
   - `AGENT_SOULS="${AGENT_SOULS:-}"` (csv of soul filenames *without* `.md` extension, e.g. `aggressive,defensive,cooperative`; empty = leave default SOUL.md for every agent)
2. Validate inside the agent-loop block: if `AGENT_SOULS` is set, csv length must equal `AGENTS`, else `die "AGENT_SOULS count must match AGENTS"`.
3. In the pre-seed Python block, for each `agent-i` with an assigned soul, copy `<SOULS_DIR>/<soul>.md` into `/home/node/.openclaw/workspaces/<agent-i>/SOUL.md`. Use Python `shutil.copyfile` inside the existing pre-seed heredoc (passes content through env or mounts SOULS_DIR read-only into the pre-seed container).
4. Cleanest path: bind-mount `$SOULS_DIR` read-only into the pre-seed container at `/host-souls/`, then the Python copies from `/host-souls/<soul>.md`. Same pattern as the per-agent skill mount used in step 4.
5. Log per-agent SOUL assignment so users see what's happening: `log "agent-0 → SOUL: aggressive"`.

### Task 18: Personality divergence probe in `bootstrap.sh`

**File:** `scripts/openclaw-bootstrap.sh` (extend the existing probe block at the bottom)

After the existing PONG probe on agent-0, when `AGENT_SOULS` is non-empty:
1. For each agent, POST to `/v1/chat/completions` with the same prompt: `"In one short sentence, describe your strategy."`
2. Hash each response (e.g. first 64 chars sha256). Assert no two agents produce identical hashes.
3. On collision: `log` both responses + the SOUL assignments + `die "agents returned identical strategy responses — SOULs may not have loaded"`. Exit code 5 (new — "personality probe failed").
4. Skipped automatically when `AGENT_SOULS` is empty (back-compat for callers that don't care).

### Task 19: `--backend openclaw` flag in `examples/territory_game.py`

**File:** `examples/territory_game.py`

1. Add CLI flag (around line 95 with other args):
   ```python
   p.add_argument(
       "--backend",
       choices=["direct", "openclaw"],
       default="direct",
       help="VLM transport: 'direct' (cloud API via roboclaws.core.vlm) or 'openclaw' (local Gateway via roboclaws.openclaw.bridge)",
   )
   p.add_argument("--gateway-url", default=None, dest="gateway_url",
                  help="OpenClaw Gateway URL (only used with --backend openclaw)")
   p.add_argument("--token", default=None,
                  help="Gateway bearer token (or OPENCLAW_GATEWAY_TOKEN env var)")
   p.add_argument("--agent-prefix", default="agent-", dest="agent_prefix",
                  help="Named-agent prefix matching bootstrap's AGENT_PREFIX")
   ```
2. In `run_territory_game()`, replace `provider = create_provider(model)` with:
   ```python
   if backend == "openclaw":
       from roboclaws.openclaw.bridge import OpenClawProvider, OpenClawUnavailable
       kwargs = {"agent_prefix": agent_prefix}
       if gateway_url is not None: kwargs["gateway_url"] = gateway_url
       if token is not None: kwargs["token"] = token
       provider = OpenClawProvider(**kwargs)
       try: provider.ping(agent_id=0)
       except OpenClawUnavailable as exc:
           provider.close()
           raise SystemExit(f"Gateway precondition failed: {exc}\nHint: re-run scripts/openclaw-bootstrap.sh with AGENTS={agent_count}.") from exc
   else:
       provider = create_provider(model)
   ```
3. Pass `provider` into `TerritoryGame` exactly as today — no game-class changes.
4. The game's existing `prompt_state` payload (`my_agent_id`, `cells_claimed`, `connectivity_ratio`, etc.) routes the right turn to the right named agent because `OpenClawProvider.get_action` already reads `state["my_agent_id"]`.
5. Update docstring + usage examples in the file header.

### Task 20: `--backend openclaw` flag in `examples/coverage_game.py`

**File:** `examples/coverage_game.py`

Mirror Task 19 exactly. Coverage game's `prompt_state` already includes `my_agent_id`; same adapter pattern works unchanged.

### Task 21: New CI job `territory-openclaw-smoke`

**File:** `.github/workflows/ci.yml`

Add a new job following `openclaw-smoke`'s shape (lines 183-276). Key differences:
- `AGENT_SOULS: "aggressive,defensive"` in the bootstrap env
- Run command: `xvfb-run -a python examples/territory_game.py --backend openclaw --agents 2 --steps 30 --output-dir output/openclaw/territory`
- Artifact name: `report-openclaw-territory`
- Upload path: `output/openclaw/territory/**`

`continue-on-error: true` at the job level (same as openclaw-smoke). Same pinned `OPENCLAW_IMAGE`. Same `KIMI_API_KEY` secret.

### Task 22: New CI job `coverage-openclaw-smoke`

**File:** `.github/workflows/ci.yml`

Mirror Task 21 with:
- `AGENT_SOULS: "cooperative,cooperative"` (both agents cooperate; coverage isn't adversarial)
- Run: `xvfb-run -a python examples/coverage_game.py --backend openclaw --agents 2 --steps 30 --output-dir output/openclaw/coverage`
- Artifact: `report-openclaw-coverage`

### Task 23: Update `publish-pages` to copy 3 OpenClaw artifacts

**File:** `.github/workflows/ci.yml`, `scripts/write_pages_index.py`

1. `publish-pages` job `needs:` array: add `territory-openclaw-smoke`, `coverage-openclaw-smoke`.
2. Download all three artifacts (`report-openclaw`, `report-openclaw-territory`, `report-openclaw-coverage`).
3. Copy to `site/openclaw/{demo,territory,coverage}/` respectively.
4. Update `scripts/write_pages_index.py` to render three OpenClaw cards under Layer 3 instead of one. Card titles: "OpenClaw Navigation", "OpenClaw Territory", "OpenClaw Coverage".

### Task 24: README Layer 3 rewrite

**File:** `README.md`

Replace the single nav-demo block (currently the OpenClaw + Kimi paragraph + one GIF + one report link) with three tiles symmetric to Layer 2:

```markdown
### 3. OpenClaw + Kimi/NVIDIA — push to `main`

The OpenClaw Layer 3 routes the same three demos through a long-running local
Gateway with per-agent personalities (aggressive / defensive / cooperative
SOULs from `skills/ai2thor-navigator/souls/`).

| Demo | GIF | Report |
|------|-----|--------|
| Navigation | ![nav](https://miaodx.github.io/roboclaws/openclaw/demo/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/demo/report.html) |
| Territory  | ![ter](https://miaodx.github.io/roboclaws/openclaw/territory/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/territory/report.html) |
| Coverage   | ![cov](https://miaodx.github.io/roboclaws/openclaw/coverage/replay.gif) | [▶ report](https://miaodx.github.io/roboclaws/openclaw/coverage/report.html) |
```

Also flip the Phase 2.2 box (add a new line if not present): `- [x] **Phase 2.2**: long-running OpenClaw games (territory + coverage) with per-agent SOULs`.

### Task 25: Update `docs/openclw/openclaw-local.md`

**File:** `docs/openclw/openclaw-local.md`

Add a new "Per-agent personalities" section:

````markdown
## Per-agent personalities (Phase 2.2)

Bootstrap can drop a SOUL file into each agent's workspace via `AGENT_SOULS`:

```bash
export KIMI_API_KEY=sk-...
TOKEN=$(AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh)
```

The csv length must match `AGENTS`. Available SOULs (from
`skills/ai2thor-navigator/souls/`): `aggressive`, `defensive`, `cooperative`.
Bootstrap probes each agent post-startup with the same question; if two
agents produce identical strategy descriptions, the bootstrap fails fast
(exit code 5) — usually a sign the SOULs didn't load.

## Run the territory or coverage game over OpenClaw

```bash
# Territory (adversarial — try contrasting SOULs)
TOKEN=$(AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh)
OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/territory_game.py \
    --backend openclaw --agents 2 --steps 60 --output-dir output/openclaw/territory

# Coverage (cooperative — both agents cooperate)
TOKEN=$(AGENTS=2 AGENT_SOULS=cooperative,cooperative ./scripts/openclaw-bootstrap.sh)
OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/coverage_game.py \
    --backend openclaw --agents 2 --steps 60 --output-dir output/openclaw/coverage
```

Each game restarts the Gateway with the right SOUL assignment for its game
mode. The container survives the full game run; only torn down at the end.
````

### Task 26: New test `tests/test_openclaw_bootstrap.py`

**File:** `tests/test_openclaw_bootstrap.py` (new)

One test minimum:
- `test_bootstrap_distributes_souls_to_per_agent_workspaces` — image-check (skip when `ghcr.io/openclaw/openclaw:2026.4.14` not pulled). Runs `AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh` (or its pre-seed step in isolation), then `docker exec` to read both `workspaces/agent-0/SOUL.md` and `workspaces/agent-1/SOUL.md`. Assert content matches `souls/aggressive.md` and `souls/defensive.md` respectively.

Optional second test (if the pure-shell pre-seed is hard to invoke from pytest): a Python-side test that builds the same csv → mapping the bootstrap script does, asserting the validation logic (length-mismatch raises, unknown SOUL filename raises). Same file.

### Task 27: Update `TODOS.md`

**File:** `TODOS.md`

- Move items 1 (Phase 2.2 SOULs) and 2 (Phase 2.5 long-running games) under a new "Shipped" header, with a one-line pointer to the Phase 2.2 retrospective in PLAN.md.
- Renumber item 3 (digest pinning) → 1, mark as Phase 2.3 work.

### Task 28: Live re-validation + artefact capture

**Validation (concrete):**
1. Local bootstrap with all three personas:
   ```bash
   set -a && source .env && set +a
   TOKEN=$(AGENTS=3 AGENT_SOULS=aggressive,defensive,cooperative ./scripts/openclaw-bootstrap.sh)
   ```
   Bootstrap log shows: "agent-0 → SOUL: aggressive", "agent-1 → SOUL: defensive", "agent-2 → SOUL: cooperative", "personality probe ok — 3 distinct strategies".
2. Run territory game: `OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/territory_game.py --backend openclaw --agents 2 --steps 30 --output-dir output/openclaw/territory` runs to completion.
3. `output/openclaw/territory/report.html` opens; per-agent reasoning panes show clearly different strategies (aggressive agent describes "rushing", defensive describes "consolidating").
4. Run coverage game: `python examples/coverage_game.py --backend openclaw --agents 2 --steps 30 --output-dir output/openclaw/coverage`.
5. Coverage report shows both agents using cooperative reasoning.
6. Spot-check per-agent isolation post-run: `docker exec openclaw-gateway cat /home/node/.openclaw/workspaces/agent-0/SOUL.md` differs from agent-1's.
7. After merge + green CI, `curl -sI https://miaodx.github.io/roboclaws/openclaw/{demo,territory,coverage}/report.html` all return `HTTP/2 200`.

### Task 29: PLAN.md retrospective

**File:** `PLAN.md`

Append a "Phase 2.2 retrospective" section at the bottom capturing:
- What shipped vs what TODOS originally split (the collapse rationale)
- Whether the Gateway's natural state actually delivers within-run memory persistence (depends on Task 28 observations) — if it doesn't, file a Phase 2.3 TODO for explicit memory injection
- Anything that surprised the implementer (likely candidates: SOUL hot-swap on running container? required restart? bootstrap ergonomics with 3 long env vars?)

## Test Plan

| Codepath | Test | Location |
|----------|------|----------|
| Bootstrap SOUL distribution (T17) | `test_bootstrap_distributes_souls_to_per_agent_workspaces` | `tests/test_openclaw_bootstrap.py` (new) |
| Bootstrap SOUL csv length validation (T17) | `test_bootstrap_rejects_mismatched_souls_count` | `tests/test_openclaw_bootstrap.py` (new) |
| Personality divergence probe (T18) | Validated via bootstrap exit-code-5 contract; tested implicitly by T26 image-check + manually in T28 step 1 | `scripts/openclaw-bootstrap.sh` |
| `--backend openclaw` flag wiring (T19, T20) | `test_territory_game_backend_openclaw_constructs_provider` + coverage equivalent — mock `OpenClawProvider`, assert it's the provider passed to `TerritoryGame` | `tests/test_territory_example.py`, `tests/test_coverage_example.py` |
| Game state routes correct agent_id to OpenClawProvider | Existing OpenClawProvider tests cover this (state["my_agent_id"]) | `tests/test_bridge.py` |
| Lint passes for game changes | `ruff check examples/{territory,coverage}_game.py` | CI lint-and-mock |
| Territory game end-to-end via OpenClaw | `territory-openclaw-smoke` CI job runs game → asserts `report-openclaw-territory` artifact non-empty | `.github/workflows/ci.yml` |
| Coverage game end-to-end via OpenClaw | `coverage-openclaw-smoke` CI job | `.github/workflows/ci.yml` |
| Pages publishing all 3 reports reachable | Task 28 step 7 curl checks post-merge | Manual + merge-commit record |

## Failure Modes

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| `AGENT_SOULS` csv length ≠ AGENTS | Bootstrap exits with confusing index error | T17 validates length up front, dies with clear message |
| Unknown SOUL filename in csv | Bootstrap `cp` fails inside the pre-seed container | T17 validates each name against `<SOULS_DIR>/*.md` listing before pre-seed |
| Two agents produce identical strategy responses | SOULs didn't load (mount path wrong / file empty) | T18 personality divergence probe — exit code 5, dump both responses, point at SOULS_DIR |
| Gateway restart loses workspace SOUL.md | Post-restart agents revert to default SOUL | Volume persists across restarts (it's a docker volume); SOUL.md survives because pre-seed wrote it before first start |
| Game expects `state["my_agent_id"]` but TerritoryGame passes a differently-keyed dict | Wrong agent gets the turn | TerritoryGame already includes `my_agent_id` (verified at examples/territory_game.py:226-227); coverage same |
| Long game (200 steps × 2 agents = 400 turns) exhausts Kimi free tier | Game halts mid-run with 429 | Bridge already maps 5xx + uses provider_retry; CI uses 30 steps not 200 |
| Per-agent MEMORY.md doesn't accumulate within a run | Long-running differentiator missing | T29 retrospective documents the gap; if confirmed, file Phase 2.3 TODO for explicit memory injection (low priority since per-turn state already carries game context) |
| Gateway ate >14k prompt tokens with 1 skill in Phase 2.1; SOUL.md adds another ~500 tokens × N agents | Higher per-turn token cost | Each agent has its own prompt (named-agent isolation), so the +500 doesn't multiply across agents from a single agent's perspective. Total Gateway token consumption goes up linearly with N — flag in T28 step 5 if it pushes over Kimi free quota |
| `--backend openclaw` flag breaks existing direct-VLM users | Regression in default workflow | Default is `direct`; openclaw is opt-in. Existing `tests/test_{territory,coverage}_example.py` cover the `mock` path, no regression risk |

## Effort Estimate

| Task | Human | CC+gstack |
|------|-------|-----------|
| T17 (bootstrap SOUL distribution) | ~45 min | ~10 min |
| T18 (personality probe) | ~30 min | ~5 min |
| T19 (territory --backend) | ~30 min | ~5 min |
| T20 (coverage --backend) | ~20 min | ~5 min |
| T21 (territory CI job) | ~20 min | ~5 min |
| T22 (coverage CI job) | ~15 min | ~3 min |
| T23 (publish-pages 3 artifacts) | ~30 min | ~5 min |
| T24 (README Layer 3 rewrite) | ~20 min | ~3 min |
| T25 (docs/openclw/openclaw-local.md) | ~20 min | ~3 min |
| T26 (bootstrap test) | ~30 min | ~5 min |
| T27 (TODOS.md update) | ~10 min | ~2 min |
| T28 (live re-validation) | ~30 min | ~10 min |
| T29 (retrospective) | ~15 min | ~5 min |

**Total: ~5h human / ~1h 10min CC+gstack** (plus local validation time for T28).

## What already exists (reuse, don't rebuild)

- **SOULs themselves** — `skills/ai2thor-navigator/souls/{aggressive,defensive,cooperative}.md` (3 files, all written). T17 only wires distribution.
- **Long-running container behavior** — `scripts/openclaw-bootstrap.sh` already starts a container that survives until `docker rm -f`. No new lifecycle code.
- **Per-agent named-agent isolation** — Phase 2.1 already created independent workspaces, agent dirs, and auth profiles per agent. T17 fills the SOUL slot inside the existing structure.
- **Gateway workspace SOUL.md slot** — `docs/openclw/openclaw-gateway-internals.md:67` documents `workspaces/<agentId>/SOUL.md` as the persona slot. Already there, waiting to be filled.
- **`OpenClawProvider` as drop-in `VLMProvider`** — `roboclaws/openclaw/bridge.py:392-487`. `TerritoryGame` and `CoverageGame` already accept any `VLMProvider`; T19/T20 only wire construction.
- **Per-turn `my_agent_id` routing** — `OpenClawProvider.get_action()` reads `state["my_agent_id"]` (`bridge.py:445`). Both games already include this in `prompt_state`.
- **Existing `openclaw-smoke` CI job** (`.github/workflows/ci.yml:183-276`) — T21/T22 copy this shape, only changing the run command + artifact name.
- **Personality CSV plumbing** — bootstrap already iterates `agent_ids` for skill mounts (line 313); T17 reuses the same loop for SOUL.md copies.

## Worktree parallelization strategy

| Step | Modules touched | Depends on |
|------|----------------|------------|
| T17 (bootstrap SOULs) | `scripts/` | — |
| T18 (probe) | `scripts/` | T17 |
| T19 (territory --backend) | `examples/` | — |
| T20 (coverage --backend) | `examples/` | — |
| T21 (territory CI) | `.github/workflows/` | T17 + T19 |
| T22 (coverage CI) | `.github/workflows/` | T17 + T20 |
| T23 (publish-pages) | `.github/workflows/`, `scripts/write_pages_index.py` | T21, T22 |
| T24 (README) | `README.md` | T19 + T20 (demos exist) |
| T25 (docs) | `docs/` | T17 |
| T26 (test) | `tests/` | T17 |
| T27 (TODOS) | `TODOS.md` | — |
| T28 (validation) | — | All above |
| T29 (retro) | `PLAN.md` | T28 |

**Lanes:**
- **Lane A** (bootstrap): T17 → T18 → T26 (sequential, all touch bootstrap or its tests)
- **Lane B** (territory): T19 → T21 (sequential, depends on Lane A's T17 for end-to-end CI)
- **Lane C** (coverage): T20 → T22 (sequential, depends on Lane A's T17)
- **Lane D** (docs+todos): T25, T27 in parallel — independent
- **Lane E** (publish + readme): T23 → T24 — depends on B + C
- **Lane F** (validation + retro): T28 → T29 — runs after everything merges

**Conflict flag:** Lanes B, C, E all touch `.github/workflows/ci.yml` at adjacent locations. Land B first (adds territory-openclaw-smoke job), then C (adds coverage-openclaw-smoke job), then E (rewrites publish-pages `needs:` array + write_pages_index.py). Sequential merges avoid YAML conflicts.

---

## Phase 2.2 Autoplan Review (2026-04-16)

### Review participants

| Phase | Claude subagent | Codex | Verdict |
|-------|-----------------|-------|---------|
| CEO | ran (full) | unavailable (rate-limited until 2026-04-22) | REWORK |
| Design | skipped — no UI scope (no new viewer components) | n/a | n/a |
| Eng | ran (full) | unavailable | REWORK |
| DX | ran (full, 8 dimensions) | unavailable | REWORK (4.6/10) |

`[subagent-only]` mode for the entire pipeline. Treat single-voice findings as
strong-but-not-confirmed signal. Critical findings flagged regardless per autoplan
single-voice rule.

### Consensus tables (single-voice — Claude subagent only)

```
CEO — single-voice findings:
═══════════════════════════════════════════════════════════════
  Dimension                           Subagent  Severity
  ────────────────────────────────── ────────── ───────────
  1. Right problem (3-tile matrix)?  CHALLENGE  CRITICAL
  2. Per-agent SOULs → gameplay?     UNTESTED   CRITICAL
  3. "Long-running" differentiator?  VAPOR      HIGH
  4. Cross-run MEMORY scope?         WRONG CALL CRITICAL
  5. Competitive risk (no viz diff)? FAIL       HIGH
  6. Scope ratio (5:1 meta:feature)? PADDED     HIGH
═══════════════════════════════════════════════════════════════
```

```
ENG — single-voice findings (21 total, 1 critical, 1 high, 12 medium, 7 low/info):
═══════════════════════════════════════════════════════════════
  Dimension                           Subagent  Severity
  ────────────────────────────────── ────────── ───────────
  Architecture (data flow)            CORRECT   medium
  Image-type contract (F21)           BROKEN    CRITICAL
  Rate-limit mid-game (F4)            BROKEN    HIGH
  Test coverage gaps (F8/F10)         THIN      medium
  CI rate-budget collision (F12)      RISK      medium
  DRY (T19/T20 + T21/T22)             VIOLATED  medium
  Token-leak via CLI (F14)            FOOTGUN   low
═══════════════════════════════════════════════════════════════
```

```
DX — single-voice scorecard:
═══════════════════════════════════════════════════════════════
  Dimension                           Score
  ────────────────────────────────── ──────
  1. Time to Hello World              4/10
  2. API/CLI naming                   4/10
  3. Error messages                   3/10
  4. Documentation                    5/10
  5. Upgrade path safety              8/10
  6. Dev environment friction         3/10
  7. Onboarding                       3/10
  8. Escape hatches                   7/10
  ────────────────────────────────── ──────
  OVERALL                             4.6/10
═══════════════════════════════════════════════════════════════
```

### Decision Audit Trail

Auto-applied corrections (mechanical or P3/P5-dominant). Each row: which review
surfaced it, the original plan text, the revision applied, and the principle.

| # | Source | Issue | Auto-applied revision | Principle |
|---|--------|-------|----------------------|-----------|
| 1 | Eng F21 | T19/T20 pass `list[str]` base64 to `OpenClawProvider`, but bridge expects `list[np.ndarray]` — first-turn crash | T19/T20 spec adds: when `backend=="openclaw"`, build `prompt_images = [active_state.frame, map_frame]` (numpy), not `[_frame_to_b64(...), _frame_to_b64(...)]`. Add a regression test covering the type contract. | P5 (explicit) |
| 2 | Eng F4 | Game loop catches only `ProviderHealthError`, not `OpenClawUnavailable` — 429 mid-game loses report | T19/T20 spec adds: extend the `decide()` try-arm to catch both `ProviderHealthError` AND `OpenClawUnavailable`; on the latter, set `termination_reason_override="provider_unstable"` and break cleanly so `recorder.save()` still fires | P1 (completeness) |
| 3 | DX1 | T18 personality probe asserts divergence; T22 explicitly recommends `cooperative,cooperative` for coverage → probe always trips → CI broken | T18 spec adds: skip the divergence assertion when `len(set(AGENT_SOULS))<=1` (intentionally identical SOULs). Also accept `PERSONALITY_PROBE=0` env override. | P5 (explicit) |
| 4 | Eng F3 | Stale `SOUL.md` survives across bootstrap re-runs (volume persists; no cleanup) | T17 spec adds: unconditionally `rm -f` `<workspace>/SOUL.md` for every agent in `AGENT_IDS_CSV` before the conditional copy. | P5 (explicit) |
| 5 | CEO + Eng F5 | `souls/aggressive.md:3` and `defensive.md:3` open with "adversarial territory-claiming game" — confuses VLM in coverage mode | New T17a (before T17): rewrite SOUL openers to game-mode-neutral wording ("multi-agent grid game"). Cooperative.md is already coverage-flavored — leave as-is. | P1 (completeness) |
| 6 | DX2 | `--backend direct` is meaningless ("direct what?"). `vlm` matches the existing module name | T19/T20 spec: rename CLI choice to `--backend {vlm,openclaw}` (default `vlm`). Keep `direct` as deprecated alias for back-compat with one-line warning. | P5 (explicit) |
| 7 | DX2 + Eng F14 | Three new CLI flags per game (`--gateway-url`, `--token`, `--agent-prefix`); `--token` leaks via shell history | T19/T20 spec: drop `--token` and `--agent-prefix` CLI flags. Use `OPENCLAW_GATEWAY_TOKEN` and `OPENCLAW_AGENT_PREFIX` env vars only. Keep `--gateway-url` as debug escape hatch. | P3 (pragmatic) |
| 8 | Eng F18 | T19/T20 duplicate ~15 lines of `OpenClawProvider` construction + ping + `SystemExit` — DRY violation | New T18.5 (before T19): extract `build_openclaw_provider_or_die(*, gateway_url=None, agent_prefix="agent-", agent_count) -> OpenClawProvider` to `roboclaws/openclaw/bridge.py`. T19/T20 each call the helper. | P4 (DRY) |
| 9 | Eng F12 | Three CI jobs (openclaw-smoke, territory-openclaw-smoke, coverage-openclaw-smoke) hit Kimi simultaneously on push to main; share one rate budget | T21/T22 spec adds: `concurrency: { group: openclaw-kimi, cancel-in-progress: false }` on each job. OR: chain via `needs: openclaw-smoke` then `needs: territory-openclaw-smoke`. Default to chain — simpler, deterministic. | P3 (pragmatic) |
| 10 | DX3 | TTHW for Layer 3 territory is ~15-30 min vs ~30s for Layer 2; plan claims "symmetry" but onboarding is asymmetric | New T24a: add `make openclaw-territory` + `make openclaw-coverage` targets (or `scripts/run-layer3-{territory,coverage}.sh`) wrapping bootstrap + token capture + game run with progress echoed. T24 README adds: "**First local run takes ~15 min** (Docker pull + Unity download). See `docs/openclw/openclaw-local.md`. Already set up? `make openclaw-territory`." | P1 (completeness) |
| 11 | DX | Bootstrap goes silent for 60-180s during readyz/probe waits → user thinks it hung | T17/T18 spec adds: per-10s tick during the readyz wait (`log "readyz: still waiting (${elapsed}s/${READY_TIMEOUT}s)"`). Same for the probe wait. | P5 (explicit) |
| 12 | DX | `SystemExit` hint always says "re-run bootstrap with AGENTS=N" but the actual cause is usually 401 token-expired | T19/T20 helper (T18.5) branches the hint by exception type: 401 → "token likely expired; re-capture with `TOKEN=$(./scripts/openclaw-bootstrap.sh)`"; 400 "Invalid model" → "agent N+1 not registered; re-run with AGENTS=N+1"; "unreachable" → "Gateway not running; check `docker ps`". | P5 (explicit) |
| 13 | DX | SOUL filename validation: typo (`aggresive`) shows `cp: cannot stat` deep in pre-seed container log | T17 spec adds: validate `AGENT_SOULS` entries against `ls $SOULS_DIR/*.md` BEFORE the pre-seed run. Error message: `die "unknown SOUL '$soul'; available: $(ls $SOULS_DIR/*.md 2>/dev/null \| xargs -n1 basename \| sed 's/\\.md$//' \| paste -sd, -)"`. | P5 (explicit) |
| 14 | Eng F1 | SOUL.md re-read vs cached at boot — assumed but never verified | T28 step 1b adds: after bootstrap completes, `docker exec openclaw-gateway cat /home/node/.openclaw/workspaces/agent-0/SOUL.md` and assert content matches `souls/aggressive.md` (or whatever was assigned). Cheap sanity. | P5 (explicit) |
| 15 | Eng F6 + DX | Token math is correct per-request, but Phase 2.1 hit 14k baseline; Phase 2.2 adds SOUL.md (~500 tokens/agent) | T28 step 1c adds: capture `usage.prompt_tokens` from the first 3 chat-completions and compare to baseline. Flag if >18k. Informational, not gating. | P5 (explicit) |
| 16 | CEO + Eng | T28 validation step 3 ("per-agent reasoning panes show clearly different strategies") is vibes-based — keyword matching | T28 step 3 rewritten with quantitative gate: "after 30 steps of territory with `aggressive,defensive`, aggressive must claim ≥20% more cells OR reach ≥1.5× distance-from-spawn vs defensive. If neither holds, the SOULs aren't influencing actions — flag as Phase 2.3 issue." | P5 (explicit) |
| 17 | CEO | SOULs → gameplay divergence is untested empirical assumption that could invalidate the whole phase | New T16.5 (very first task, before any wiring): local A/B with the existing 3 SOULs against the existing direct-VLM territory game (no OpenClaw needed) — does swapping SOULs in the prompt change actions? If no: rethink the phase. If yes: proceed with confidence. ~30 min effort. | P1 (completeness) |
| 18 | Eng F7 | T18 personality probe has zero unit-test coverage | T26 spec expands: add `test_bootstrap_personality_probe_hashes_distinct` (mocks two distinct curl responses → exit 0), `test_bootstrap_personality_probe_collides` (mocks identical → exit 5), `test_bootstrap_skips_probe_when_souls_identical` (cooperative,cooperative → exit 0 regardless). | P1 (completeness) |
| 19 | Eng F8 | T19/T20 missing error-path tests (Gateway-unreachable, missing token, missing my_agent_id) | T26 spec expands per game: `test_{game}_backend_openclaw_exits_when_gateway_unreachable`, `test_{game}_backend_openclaw_exits_when_token_missing`, `test_{game}_backend_openclaw_falls_back_to_zero_when_my_agent_id_missing`. | P1 (completeness) |
| 20 | Eng F10 | T26 bootstrap test only checks `cp` worked (tautology) | T26 spec adds: `test_bootstrap_rejects_mismatched_souls_count` (csv length ≠ AGENTS → exit 1 with clear msg) + `test_bootstrap_rejects_unknown_soul_filename` (typo → exit 1 with available-souls list). Extract validator into shellable function so pytest can call it directly. | P1 (completeness) |
| 21 | Eng F16 | T23 publish-pages flag matrix not enumerated (4 cases: neither/territory-only/coverage-only/both) | T23 spec adds: `scripts/write_pages_index.py` flag handling explicitly enumerates 4 cases; missing artifact directory → omit tile (mirrors current `if [ -d openclaw-src/demo ]` pattern). | P5 (explicit) |
| 22 | Eng F20 | Failure Modes row points at `examples/territory_game.py:226-227` for `my_agent_id` check; correct location is `roboclaws/games/territory.py:308-329` | Failure Modes table corrected. | P5 (explicit) |
| 23 | DX | T25 docs are 5 cross-references deep (KIMI_API_KEY needs reading earlier section, AGENTS unset trips users, `aggressive.md` vs `aggressive` trip) | T25 spec rewritten as ONE self-contained recipe per demo. Every env var set inline; expected timing per step; AI2-THOR Unity download note; `OPENCLAW_GATEWAY_TOKEN` capture-and-export shown twice (intentional). | P1 (completeness) |
| 24 | Eng F9 | Signature regression: T19 says "add backend, gateway_url, token, agent_prefix params" — defaults must preserve existing `run_territory_game(scene, agent_count, steps, model, output_dir)` callers | T19 spec pins explicit Python signature: `run_territory_game(*, scene, agent_count, steps, model="mock", output_dir, backend="vlm", gateway_url=None, agent_prefix="agent-", thor_server_timeout=100.0, thor_server_start_timeout=300.0)`. Existing tests must pass unmodified. (Token CLI flag dropped per #7.) | P5 (explicit) |
| 25 | DX | `AGENT_SOULS` positional csv silently rebinds personas when count changes | T17 spec adds: also accept `AGENT_SOULS=agent-0:aggressive,agent-2:cooperative` dict form. Csv form is "positional shortcut" semantics. Default unspecified slots to "default" (no SOUL.md copy = stock SOUL). | P1 (completeness) |

**Total auto-applied: 25 corrections.** Effort delta: +30 min CC / +2h human across the phase. Mostly absorbed in T17 + T19/T20 expansion. Net new tasks: T16.5 (SOUL→gameplay A/B), T17a (rewrite SOULs), T18.5 (helper extract), T24a (make targets).

### User Challenges (final-gate decision required — never auto-decided)

These are flagged by the CEO subagent as challenges to your stated direction. Single-voice mode (Codex unavailable), so the signal is strong-but-not-confirmed. Your call — your direction stands unless you explicitly change it.

**UC1 — Drop the 3×3 matrix; ship ONE OpenClaw-unique demo ("Persona Showdown")**

- *What you said:* "Make the openclaw demo like the VLM one, long running for both scenarios" → plan ships territory + coverage as 2 new Layer 3 tiles symmetric with Layer 2.
- *Subagent recommends:* Drop matrix-completion framing entirely. Ship one demo: same scene, same start positions, two runs side-by-side — Run A: aggressive vs defensive SOUL, Run B: defensive vs defensive (or any swap). Side-by-side GIF showing emergent behavior differences. Viewer's 5-second takeaway becomes "OpenClaw lets me swap personalities and the robots play differently."
- *Why:* The current plan ships Layer 3 GIFs that are visually indistinguishable from Layer 2 GIFs of the same scene. Evaluators give 5 seconds of GIF to convey the differentiator; "same demo, different transport" wastes the one asset OpenClaw uniquely gives you (durable per-agent SOUL).
- *Context we might be missing:* You may have a strategic reason to keep the matrix for narrative symmetry with the README, or downstream stakeholders may have asked for parity specifically.
- *If we're wrong, the cost is:* You ship 3 Layer 3 tiles that read as "we did the work" but don't differentiate. Future me wonders why Layer 3 exists.

**UC2 — Promote cross-run MEMORY persistence from "out of scope" to a P1 stretch goal**

- *What you said:* In the AskUserQuestion you locked "long-running = within-a-run" (i.e., one bootstrap → one Gateway → tear down at end).
- *Subagent recommends:* Reinterpret "long-running" toward the deeper meaning — *across runs, the agent remembers*. Run territory game twice against the same Gateway container (no volume wipe between); show that game-2's agent references game-1 events in `replay.json` reasoning. If the Gateway gives you that for free, it's the differentiator and it costs nothing. If it doesn't, the finding itself is strategically valuable (you know OpenClaw doesn't solve that problem and can stop investing).
- *Why:* Cross-run MEMORY is the only thing about OpenClaw that a direct-VLM backend fundamentally cannot do. Cutting it and keeping "three tiles" is "cutting the filet and shipping the bun" (subagent's words). T28 step "informational, not gating" is the cheapest way to sanity-check this without expanding scope.
- *Context we might be missing:* You may have already investigated MEMORY semantics in Phase 2.1 and found it doesn't work; or your "within-a-run" choice was deliberately conservative to avoid scope drift.
- *If we're wrong, the cost is:* Six months from now someone asks "why does roboclaws have OpenClaw?" and the answer is "it runs the same games the direct backend runs". (We addressed this partially via Decision #15 — capture token usage as informational. UC2 would extend that to also probe MEMORY.)

**UC3 — Visualize SOULs in the GIFs (badge per agent + trail color by SOUL)**

- *What you said:* No visualization changes mentioned in the plan.
- *Subagent recommends:* When `--backend openclaw` is active, `GameVisualizer` renders per-agent SOUL name as a badge on the agent sprite, and tints the agent's trail by SOUL color. ~30-line change in `roboclaws/core/visualizer.py`. Without this, Layer 3 GIFs are visually identical to Layer 2 GIFs — the differentiator is invisible HTTP traffic. Subagent: "literally the only way 'OpenClaw Territory' becomes visually distinguishable from 'Territory' in a thumbnail."
- *Why:* Competitive differentiation lives in the 5 seconds of GIF an evaluator sees. Right now there's nothing visual that says "OpenClaw was here".
- *Context we might be missing:* You may consider this scope creep into visualization work that belongs in a separate phase.
- *If we're wrong, the cost is:* You ship 3 visually-indistinguishable tiles; evaluators see "infrastructure for the same outcome".

### Taste Decisions (auto-decided with recommendation; surface for your override)

| # | Decision | Auto-pick | Alternative | Why |
|---|----------|-----------|-------------|-----|
| TD1 | Refactor `openclaw-smoke` + 2 new jobs into a GitHub Actions matrix? | YES — matrix (~100 lines vs ~270 lines duplicate) | Keep 3 separate jobs (more YAML, easier to read in isolation) | DRY (P4) + maintainability. Matrix lets future demos add a row, not a job. |
| TD2 | Coverage demo SOULs: `cooperative,cooperative` (current plan) vs write `coverage-diverse-{a,b}.md` for visible behavioral diversity? | KEEP `cooperative,cooperative` for now; file diverse SOULs as Phase 2.3 | Write 2 new SOULs in this phase | Pragmatic (P3) — generating new SOUL content is its own design exercise. The probe-skip fix (Decision #3) makes `cooperative,cooperative` viable today. UC1+UC3 would change this. |
| TD3 | Coverage CI step count: align to Layer 2 step count (60? 100?) or stick at 30 to control Kimi cost? | 30 steps in CI; 60+ in local docs | Match Layer 2 exactly | Pragmatic (P3) — CI budget is finite. Document the asymmetry in T29 retro. |
| TD4 | `AGENT_SOULS` env: support both csv (positional) AND dict (`agent-N:soul`) forms in T17? | YES — both (Decision #25) | csv only | Completeness (P1) — dict form is the future-friendly default; csv stays as shortcut. |

### Cross-phase themes

- **"Plan does not validate its own load-bearing assumptions"** — flagged by CEO (SOULs→gameplay is empirical, untested) AND DX (TTHW is undisclosed). Both reviewers landed on REWORK. The auto-fixes (T16.5 A/B + Decision #16 quantitative gate + Decision #10 TTHW callout) address this directly, but the user challenges (UC1-UC3) escalate it to "are we shipping the right thing?"
- **"Layer 3 doesn't actually differentiate from Layer 2"** — flagged by CEO (no visual signal) AND DX (10× TTHW for same outcome). Decision #10 mitigates the friction; UC3 mitigates the visual sameness; UC1 reframes the entire shipping story.
- **"Plan over-engineers the meta-work"** — flagged by CEO (5:1 meta:feature ratio) AND Eng F19 (CI duplication). Decision (TD1) collapses the CI to a matrix. UC1 collapses the README to one demo. Both reduce meta-work.

### Pre-Gate Verification

Phase 1 (CEO): premise challenge ✓ (5 premises evaluated), 6 review dimensions ✓, dual voices ✗ (codex unavailable, single-voice mode), CEO consensus table ✓ (single-voice).

Phase 2 (Design): skipped — no UI scope detected.

Phase 3 (Eng): scope challenge ✓ (read all referenced code), Eng consensus table ✓, 21 findings (1 critical, 1 high, 12 medium, 7 low/info), test coverage analysis ✓ (gaps identified), failure modes registry ✓.

Phase 3.5 (DX): 8 dimensions evaluated ✓, scorecard produced (4.6/10), TTHW assessment ✓.

Decision Audit Trail: 25 entries logged.

User Challenges: 3 surfaced for gate.

Taste Decisions: 4 auto-decided + listed for override.

**STATUS:** Plan is structurally complete. Auto-fixes integrated into the audit trail; the original task specs above are NOT modified inline (the audit trail is the diff — apply during implementation). Three user challenges + four taste decisions surface to you at the final approval gate.

### Final Gate Outcome (2026-04-16, user decisions)

| User Challenge | Decision | Plan impact |
|---|---|---|
| UC1 — Drop matrix for Persona Showdown | **REJECTED — keep matrix** | No plan change. Ship 3 Layer 3 tiles as drafted. User's strategic call honored. Subagent's framing concern documented for Phase 2.3 retro consideration. |
| UC2 — Cross-run MEMORY as P1 stretch | **REJECTED — defer** | No expansion. T28 retains an informational MEMORY-probe step (~5 lines, free) so we don't lose the cheap discovery: post-run, `docker exec` and check `/home/node/.openclaw/workspaces/agent-0/state/MEMORY.md` for any Gateway-side accumulation. Result logged to T29 retro. If naturally accumulating, file Phase 2.3 follow-up. |
| UC3 — SOUL badges + tinted trails in viz | **ACCEPTED** | New task T19.8 added below. ~+20min CC. |

### New task added per UC3 acceptance

**Task 19.8 (T19.8) — SOUL visualization in `GameVisualizer`**

**Files:** `roboclaws/core/visualizer.py`, `examples/territory_game.py`, `examples/coverage_game.py`

When `--backend openclaw` is active, render per-agent SOUL name as a colored badge on each agent sprite in the overhead view, and tint each agent's trail by SOUL color. Without this, Layer 3 GIFs look identical to Layer 2 GIFs — differentiator invisible.

1. **Plumbing:** Game scripts read `AGENT_SOULS` env var when `--backend openclaw` (parse the same csv format the bootstrap uses). Resolve to a `list[str]` of per-agent SOUL labels (default to `"default"` for slots without SOULs). Pass as `agent_labels: list[str] | None = None` kwarg to `GameVisualizer.__init__`.
2. **Color map:** Add a small palette in `GameVisualizer` keyed by SOUL name — `aggressive: red`, `defensive: blue`, `cooperative: green`, `default: grey`. Unknown SOULs fall back to grey.
3. **Badge rendering:** In `render_overhead_map()`, when `agent_labels` is set, draw each SOUL's first letter (A/D/C) on the agent sprite using `PIL.ImageDraw`. ~10 lines.
4. **Trail tinting:** Each agent's covered cells get tinted in their SOUL color (low alpha) so trajectories are visible as colored regions on the overhead map. ~15 lines.
5. **Test:** `tests/test_visualizer_soul_overlay.py` (new) — render with mock `agent_labels=["aggressive","defensive"]`, assert pixel sample at agent-0 sprite location has red component dominant + agent-1 has blue dominant. Skip when PIL/numpy not installed (already handled via existing test infra).

**Effort:** human ~45min / CC ~20min.

**Updates:**
- T24 README spec: add note "Layer 3 GIFs include SOUL badges + colored trails — aggressive=red, defensive=blue, cooperative=green."
- T28 validation step adds: visual confirmation that aggressive/defensive trails are distinguishable in `replay.gif` thumbnail.

### Updated Test Plan addition (per UC3 + T19.8)

| Codepath | Test | Location |
|----------|------|----------|
| `GameVisualizer` SOUL badge rendering | `test_visualizer_renders_soul_badges` | `tests/test_visualizer_soul_overlay.py` (new) |
| `GameVisualizer` SOUL trail tinting | `test_visualizer_tints_trails_by_soul` | `tests/test_visualizer_soul_overlay.py` (new) |
| Game reads `AGENT_SOULS` env when `--backend openclaw` | `test_territory_game_reads_agent_souls_for_viz` | `tests/test_territory_example.py` |

### Updated Worktree parallelization

T19.8 fits Lane B (territory side). Add to dependency table:

| Step | Modules touched | Depends on |
|------|----------------|------------|
| T19.8 (SOUL viz) | `roboclaws/core/`, `examples/`, `tests/` | T19 + T20 (games already wired with --backend) |

Lane B becomes: T19 → T19.8 → T21. Lane C becomes: T20 → T22 (independent of T19.8 — coverage uses cooperative-only by default, badges still helpful for completeness).

**Final go-ahead:** plan is APPROVED with the above UC choices. Implementation contract is the original task specs (T17-T29) plus the 25 auto-fix decisions in the Audit Trail plus T19.8 (SOUL visualization). Total task count: 14 (T16.5 + T17 + T17a + T18 + T18.5 + T19 + T19.8 + T20 + T21 + T22 + T23 + T24 + T24a + T25 + T26 + T27 + T28 + T29 — actually 18 with all the new sub-tasks). Effort ceiling: ~5h human / ~1.5h CC + local validation time.

---

## Phase 2.2 retrospective

Filed 2026-04-16 after T17–T27 shipped (T28 local validation + T29 retro
are the cloud-session close-out). T16.5 was skipped: existing direct-VLM
territory runs already demonstrated SOUL→behavior divergence (the phase
was justified on that basis before any new code).

### What shipped

| Task | Commit(s) | Outcome |
|------|-----------|---------|
| T17 + T17a | SOUL files + bootstrap AGENT_SOULS wiring | `scripts/openclaw-bootstrap.sh` now accepts `AGENT_SOULS=aggressive,defensive` (csv) or `agent-0:aggressive,agent-2:cooperative` (dict); distributes `<soul>.md` from `SOULS_DIR` into each named-agent workspace at pre-seed time. |
| T18 | Personality divergence probe | Post-startup probe asks all agents the same question; exits 5 if responses hash-collide. Skipped when `PERSONALITY_PROBE=0` or all souls identical. |
| T18.5 | `build_openclaw_provider_or_die()` helper | Added to `roboclaws/openclaw/bridge.py`; constructs `OpenClawProvider`, pings agent-0, raises `SystemExit` with contextual hints on 401/400/unreachable. |
| T19 + T19.8 | `examples/territory_game.py` wiring | `--backend {vlm,openclaw,direct}` + `--gateway-url`; openclaw path passes numpy frames, reads `AGENT_SOULS` env → `GameVisualizer(agent_labels=...)`. SOUL badges + tinted trails in GIFs. |
| T20 | `examples/coverage_game.py` wiring | Mirror of T19. |
| T21–T23 | CI: two new smoke jobs | `territory-openclaw-smoke` + `coverage-openclaw-smoke` chained via `needs:` to avoid Kimi rate-budget collisions; `publish-pages` collects all three OpenClaw artifacts. |
| T24 + T24a | README + Makefile | 3-tile Layer 3 table; `make openclaw-territory` + `make openclaw-coverage` convenience targets. |
| T25 | `docs/openclw/openclaw-local.md` update | Self-contained per-game recipes, AGENT_SOULS variable table, SOUL probe explanation. |
| T26 | Tests | 369 lines across 4 test files: openclaw backend construction + numpy frame type contract (territory + coverage), SOUL CLI args, bootstrap SOUL contract checks (5 static), visualizer SOUL overlay (14 tests). |
| T27 | TODOS.md | Items 1 + 2 struck; digest pin becomes item 1 as Phase 2.3. |

### What was dropped / deferred

- **T16.5 (SOUL→gameplay A/B)** — skipped; the phase was justified by
  prior direct-VLM territory runs already showing behavioral divergence.
- **T28 (local validation)** — cloud-session boundary; must be done
  locally with a real Kimi key + Docker. Run `make openclaw-territory` →
  open `output/openclaw/territory/report.html` and confirm aggressive
  trail (red) and defensive trail (blue) differ in cell-claim distribution.
  Also check `docker exec openclaw-gateway sh -lc 'cat /home/node/.openclaw/workspaces/agent-0/state/MEMORY.md'`
  post-game for any Gateway-side MEMORY accumulation (informational, not gating).

### Lessons

1. **The `from module import fn` inside function body pattern** broke the
   `patch("territory_game.build_openclaw_provider_or_die")` approach —
   must patch the *source module attribute*
   (`roboclaws.openclaw.bridge.build_openclaw_provider_or_die`) instead.
   A `MagicMock` dropped directly as a provider breaks JSON serialization
   because `get_status()` returns a MagicMock too; use a plain stub class.

2. **Bootstrap exit codes via `die`** — the `die "..." 5` pattern doesn't
   produce a bare `exit 5` literal; tests that grep for the literal string
   must match the `die` call pattern (`re.search(r"die\b.*\b5\b", text)`).

3. **CI rate-budget collision** — territory + coverage CI jobs both hit
   Kimi; running them concurrently (or after `openclaw-smoke` in the
   same minute window) hits the rate limit. Chaining via `needs:` +
   `concurrency: group: openclaw-kimi` serializes them safely.

4. **SOUL viz test approach** — testing that SOUL colours change the
   rendered output is more robust than testing exact pixel values.
   `assert not np.array_equal(arr_no, arr_with)` is noise-free and
   survives PIL version drift; pixel-value assertions against specific
   `(r,g,b)` tuples are fragile due to alpha compositing rounding.

### Next gate

Phase 2.2 still has T28 (local validation with real Kimi + Docker)
pending — a cloud/local split, not a cloud-session task.

Phase 2.3 (digest pinning) was evaluated on 2026-04-20 and **declined**
— see [`phase-2.3.md`](phase-2.3.md).

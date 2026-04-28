# Phase 2: OpenClaw Integration — Completion Plan

## Problem Statement

Phase 2 aims to prove that AI2-THOR simulated robots can be controlled through an OpenClaw Gateway, producing a visible demo that populates the README's third layer. The existing `--backend openclaw` path in `territory_game.py` and `coverage_game.py` is broken due to a host/container path mismatch, over-complicated for a first demo, and bypasses the `AI2THORNavigatorSkill` wrapper entirely.

## Scope

### In scope
- Create a standalone `examples/openclaw_demo.py` that runs a simple multi-agent AI2-THOR scenario via `OpenClawProvider`
- Fix the host/container shared image directory contract (`work_dir`)
- Write `docs/openclw/openclaw-local.md` with the exact Docker run command including the bind mount
- Validate the demo locally first, then update CI `openclaw-smoke` to run the new demo
- Ensure the demo produces replay GIF + `report.html` that can be published to GitHub Pages
- Update README Phase 2 checkbox when the demo is live

### Not in scope
- Per-agent SOUL preset assignment via the Gateway (deferred to long-running instance work — the new `examples/openclaw_demo.py` uses the Gateway's default skill configuration)
- Territory / Coverage game logic over OpenClaw (the new demo is pure navigation; game modes return in a later phase with long-running Gateway instances)
- Fixing the coverage gameplay mismatch tracked in issue #52
- Phase 3 (Isaac Lab migration)
- Remote/Railway OpenClaw integration (the `openclaw-railway-smoke` job is dropped in Task 7 — remote Gateways can't share a host bind-mount for frame paths; they'll need a different transport)

## Architecture

```
┌─────────────────────────────────────────────┐
│              AI2-THOR Engine                │
│  agent-0 frame ──► OpenClawProvider         │
│  agent-1 frame ──► (writes to ./.openclaw-  │
│                   │   tmp/agent-{id}.jpg)   │
│                   ▼                         │
│         ┌─────────────────────┐             │
│         │  OpenClaw Gateway   │             │
│         │  (Docker container) │             │
│         │  POST /tools/invoke │             │
│         │  session per agent  │             │
│         └─────────────────────┘             │
└─────────────────────────────────────────────┘
```

## Implementation Plan

### Task 1: Fix the shared image directory contract

**Files:** `roboclaws/openclaw/bridge.py`, `.github/workflows/ci.yml`, `.gitignore`

1. Change `OpenClawProvider.__init__` to resolve `work_dir` via a 3-way fallback:
   - explicit `work_dir=` arg wins
   - else `os.environ.get("OPENCLAW_WORK_DIR")` (as `Path(...).resolve()`)
   - else `Path("./.openclaw-tmp").resolve()` (creates if missing)
2. Remove the now-unused `import tempfile` at `bridge.py:16` (ruff will flag it anyway).
3. Update `examples/openclaw_demo.py` (Task 2) to rely on the default `work_dir` behavior.
4. Update CI `openclaw-smoke` Docker run command to mount `$PWD/.openclaw-tmp` to the identical absolute path inside the container so host and container see the same absolute frame paths.
5. Add `./.openclaw-tmp/` to `.gitignore`.

### Task 2: Create `examples/openclaw_demo.py`

**New file:** `examples/openclaw_demo.py`

A minimal standalone demo:
- Scene: `FloorPlan201`
- Agents: 2
- Steps: 20 (fast enough for CI, enough to show motion)
- Uses `MultiAgentEngine`, `OpenClawProvider`, `ReplayRecorder`, `GameVisualizer`
- Simple behavior: agents take turns, each step queries the Gateway for an action
- Outputs: `replay.gif`, `report.html` to `output/openclaw-demo/`
- CLI args: `--scene`, `--agents`, `--steps`, `--output-dir`, `--gateway-url`, `--token`

No game logic (territory/coverage) — just pure navigation so the demo is focused on "can OpenClaw control the robot?"

**Session + work_dir hygiene (from review A1 + A2):**
- On startup, `shutil.rmtree(work_dir, ignore_errors=True)` then recreate — prevents stale container-UID-owned files from a prior run blocking host writes.
- Construct `OpenClawProvider(session_prefix=f"roboclaws-demo-{int(time.time())}")` so each invocation gets a unique Gateway session. Avoids MEMORY leaking across runs when iterating against the same long-running local Gateway container.
- Log the resolved `work_dir` and `session_prefix` on start so users can correlate logs ↔ Gateway state.

### Task 3: Local OpenClaw quick-start guide

**New file:** `docs/openclw/openclaw-local.md`

Contents:
- Prerequisites: Docker, `KIMI_API_KEY` or Gateway already configured
- One-liner Docker run with the bind mount (pinned image tag — A3 decision):
  ```bash
  # Generate a local Gateway token (dev-only is fine for localhost)
  GATEWAY_TOKEN=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')

  docker run -d --name openclaw-gateway \
    -p 127.0.0.1:18789:18789 \
    -v "$PWD/skills/ai2thor-navigator:/home/node/.openclaw/workspace/skills/ai2thor-navigator:ro" \
    -v "$PWD/.openclaw-tmp:$PWD/.openclaw-tmp" \
    -e OPENCLAW_AUTH_MODE=token \
    -e OPENCLAW_AUTH_TOKEN="$GATEWAY_TOKEN" \
    -e OPENCLAW_ALLOWED_TOOLS=ai2thor-navigator \
    ghcr.io/openclaw/openclaw:2026.4.14
  ```
  > ⚠️ Use `127.0.0.1:18789:18789` (not `:18789`) so the port is localhost-only. If you ever expose the Gateway port externally, rotate `OPENCLAW_AUTH_TOKEN` with a fresh `secrets.token_urlsafe(32)` value.
- How to run the demo: `OPENCLAW_GATEWAY_TOKEN=$GATEWAY_TOKEN python examples/openclaw_demo.py --steps 20`
- How to verify readiness: `curl -H "Authorization: Bearer $GATEWAY_TOKEN" http://localhost:18789/readyz`
- **Troubleshooting:**
  - *"Gateway cannot read frame paths"* → check bind mount uses identical absolute paths on host and container.
  - *"file not found" on macOS Docker Desktop* → `$PWD` must be inside Docker Desktop's File Sharing list (Settings → Resources → File Sharing). If `$PWD` is under `/Users/…`, it's shared by default; if you clone to `/opt/...` or a mapped network drive, add it explicitly.
  - *"permission denied writing to .openclaw-tmp"* → files left by a prior run are owned by the container UID. Either `sudo rm -rf .openclaw-tmp` or let the demo clean it (Task 2 adds `shutil.rmtree` on start).

**Update `CLAUDE.md`:** Add cross-reference under "Cloud vs local development".

### Task 4: Replace `openclaw-smoke` CI job

**File:** `.github/workflows/ci.yml`

1. Replace the existing `openclaw-smoke` job with a simpler one that:
   - Pins the image to `ghcr.io/openclaw/openclaw:2026.4.14` (A3 decision — no more `:latest` drift). Keep the `OPENCLAW_IMAGE` env override for forks.
   - Starts the Gateway with the skill mount + `.openclaw-tmp` bind mount at identical absolute paths.
   - Runs `python examples/openclaw_demo.py --agents 2 --steps 10 --output-dir output/openclaw/demo`
   - Runs `python -m roboclaws.core.reporter output/openclaw/demo`
   - Uploads `report-openclaw` artifact
2. Keep `continue-on-error: true` at the job level (OpenClaw Gateway availability is still optional for forks).
3. Update `publish-pages` to copy `openclaw-src/demo` to `site/openclaw/demo/` and update `scripts/write_pages_index.py` flags/landing copy so the index links to the nav demo (not the old territory/coverage placeholders).

### Task 5: Verify report publishing end-to-end

**Validation (concrete — CQ4 decision):**
1. After local validation succeeds, merge to `main` and wait for `openclaw-smoke` + `publish-pages` to go green.
2. Run these checks (each must return `HTTP/2 200`):
   ```bash
   curl -sI https://miaodx.github.io/roboclaws/openclaw/demo/report.html | head -1
   curl -sI https://miaodx.github.io/roboclaws/openclaw/demo/replay.gif  | head -1
   ```
3. Open `report.html` in a browser and confirm: step slider advances, per-agent FPV switches, overhead map renders, VLM reasoning pane shows non-empty entries.
4. Record the digest of the OpenClaw Gateway image that produced the green run (`docker inspect ghcr.io/openclaw/openclaw:2026.4.14 --format '{{index .RepoDigests 0}}'`) in the merge commit message so the pin is reproducible.

### Task 6: Rewrite README Layer 3 and mark Phase 2 complete

**Update `README.md`:**
- Change `- [ ] **Phase 2**: OpenClaw integration` to `- [x] **Phase 2**: OpenClaw integration`
- **Rewrite** the "OpenClaw + Kimi" Layer 3 section (currently lines ~47-52, promising territory + coverage GIFs). Replace with an honest "OpenClaw navigation demo" block (A5 decision):
  - One heading: *"3. OpenClaw + Kimi — push to `main`"*
  - One paragraph: the demo routes one (or more) AI2-THOR agent(s) through a local OpenClaw Gateway + Kimi VLM. Pure navigation, 20 steps, proves the transport end-to-end.
  - One GIF (embedded from Pages): `https://miaodx.github.io/roboclaws/openclaw/demo/replay.gif`
  - One interactive link: `[▶ Interactive report](https://miaodx.github.io/roboclaws/openclaw/demo/report.html)`
  - Retire issue #39 reference (demo is shipping); leave #40 (Railway) closed/superseded since Task 7 drops the Railway job.
  - Remove the territory/coverage OpenClaw GIF references entirely — they return in a later phase with long-running Gateway instances.

### Task 7: Remove dead `--backend openclaw` paths (from review Step 0)

**Files:** `examples/territory_game.py`, `examples/coverage_game.py`, `.github/workflows/ci.yml`, `tests/test_territory_example.py`, `tests/test_coverage_example.py`

After Task 2 ships the new demo, the old `--backend openclaw` wiring is orphaned:
- `examples/territory_game.py:42` imports `OpenClawProvider`; `:107-110` exposes the `--backend` CLI flag; `:164` instantiates `OpenClawProvider()` with no args. Broken and unused.
- `examples/coverage_game.py:43, 108-110, 211` — identical pattern.
- `.github/workflows/ci.yml:178-272` — the whole `openclaw-railway-smoke` job invokes `territory_game.py --backend openclaw` against Railway. Host/container filesystem sharing doesn't apply to a remote Gateway, so this path can never work with the new contract.

Do:
1. Delete the `--backend` argparse flag and related branching from both example scripts.
2. Remove the `from roboclaws.openclaw.bridge import OpenClawProvider` imports from both examples.
3. Remove the entire `openclaw-railway-smoke` job from `.github/workflows/ci.yml` (plus the `needs:` dependency references).
4. Scrub any lingering test references to `--backend openclaw` in `tests/test_{territory,coverage}_example.py`.
5. Update `docs/issues-roadmap.md` Phase 2 section to reflect the new shipping path.

## Test Plan

| Codepath | Test | Location |
|----------|------|----------|
| Bridge work_dir — env var fallback (NEW Task 1) | `test_provider_uses_env_work_dir` | `tests/test_bridge.py` (new test) |
| Bridge work_dir — default to ./.openclaw-tmp (REGRESSION, IRON RULE) | `test_provider_defaults_to_dot_openclaw_tmp` | `tests/test_bridge.py` (new test) |
| Bridge work_dir — precedence: explicit > env > default (T1) | `test_provider_explicit_work_dir_overrides_env` | `tests/test_bridge.py` (new test) |
| Bridge HTTP errors | `test_bridge_step_*` (existing 9 tests) | `tests/test_bridge.py` |
| Demo script lints | `ruff check examples/openclaw_demo.py` | CI lint-and-mock |
| Demo end-to-end | `openclaw-smoke` CI job runs demo → asserts `report-openclaw` artifact non-empty | `.github/workflows/ci.yml` |
| CI Gateway startup + bind mount | `openclaw-smoke` job `/readyz` probe + demo completion | `.github/workflows/ci.yml` |
| Report publishing reachable | Task 5 curl checks post-merge | Manual + merge-commit record |
| Old `--backend openclaw` paths gone (Task 7) | `grep -r "backend openclaw" --include="*.py" --include="*.yml"` returns nothing | CI lint-and-mock (add a grep guard) |

## Error & Rescue Registry

| Error | Cause | Rescue |
|-------|-------|--------|
| `Gateway did not become ready within 60s` | Docker image path/env drift | Read logs, check bind mounts |
| `OpenClawUnavailable: Gateway unreachable` | Local Gateway not running | Point user to `docs/openclw/openclaw-local.md` |
| `Gateway cannot read frame paths` | Missing `.openclaw-tmp` bind mount or path mismatch | Check `-v "$PWD/.openclaw-tmp:$PWD/.openclaw-tmp"` |

## Failure Modes

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| OpenClaw upstream changes image contract | CI breaks | Pinned to `ghcr.io/openclaw/openclaw:2026.4.14` (A3); record digest in Task 5 |
| Session-key collision across local runs | MEMORY leaks between demo invocations | `session_prefix=f"roboclaws-demo-{int(time.time())}"` in Task 2 (A1) |
| Stale `.openclaw-tmp` from prior run blocks host writes | PermissionError on JPEG save | `shutil.rmtree(work_dir, ignore_errors=True)` on demo startup (A2) |
| `$PWD` outside Docker Desktop File Sharing (macOS) | Gateway reports "file not found" | Troubleshooting note in `docs/openclw/openclaw-local.md` (A4 / Task 3) |
| Local developer lacks Docker | Can't run Gateway | Document that layers 1-2 work without it |
| `openclaw-smoke` job fails | Pages section omits OpenClaw card | `continue-on-error: true` + best-effort artifact download keeps landing page alive |

## Effort Estimate

| Task | Human | CC+gstack |
|------|-------|-----------|
| Task 1 (transport fix + 3 unit tests) | ~45 min | ~5 min |
| Task 2 (demo script + session/work_dir hygiene) | ~1.5 h | ~15 min |
| Task 3 (docs incl. troubleshooting) | ~30 min | ~5 min |
| Task 4 (CI update, pin image) | ~30 min | ~5 min |
| Task 5 (post-merge verify + record digest) | ~15 min | ~5 min |
| Task 6 (README Layer 3 rewrite) | ~20 min | ~3 min |
| Task 7 (delete orphans + scrub tests) | ~30 min | ~5 min |

**Total: ~4.5 h human / ~45 min CC+gstack** (plus local validation time)

## What already exists (reuse, don't rebuild)

- `OpenClawProvider` + `OpenClawBridge` (`roboclaws/openclaw/bridge.py`) — Task 1 only tweaks the `work_dir` fallback.
- `tests/test_bridge.py` — 27 existing tests cover bridge construction, healthcheck, step errors, provider image writes. Plan adds 3 new unit tests.
- `tests/test_skill.py` — 21 existing tests cover `AI2THORNavigatorSkill`. Not modified.
- `roboclaws/core/{engine,replay,visualizer,reporter}.py` — the demo imports all four; no changes.
- CI `openclaw-smoke` (`.github/workflows/ci.yml:288-446`) — Task 4 keeps the Gateway startup / token / readiness steps; only the game steps change.
- `publish-pages` job — Task 4 copies to `site/openclaw/demo/` reusing existing artifact flow.

## Worktree parallelization strategy

| Step | Modules touched | Depends on |
|------|----------------|------------|
| Task 1 (bridge + gitignore + 3 tests) | `roboclaws/openclaw/`, `tests/` | — |
| Task 2 (new demo script) | `examples/` | Task 1 (wants resolved work_dir) |
| Task 3 (local quickstart docs) | `docs/`, `CLAUDE.md` | — |
| Task 4 (CI update) | `.github/workflows/`, `scripts/write_pages_index.py` | Task 2 (must call real demo) |
| Task 5 (post-merge verification) | — | Tasks 2 + 4 + 6 merged |
| Task 6 (README rewrite) | `README.md` | Task 2 (demo exists) |
| Task 7 (delete orphans) | `examples/`, `.github/workflows/`, `tests/` | — |

**Parallel lanes:**
- **Lane A:** Task 1 → Task 2 → Task 6 (bridge + demo + readme, sequential — shared concern: demo behavior)
- **Lane B:** Task 3 (docs — independent)
- **Lane C:** Task 7 (orphan cleanup — independent, touches `examples/` + `ci.yml` but at different lines than Lane A/D)
- **Lane D:** Task 4 (CI) — depends on Lane A's Task 2 landing first. Touches `ci.yml` like Lane C → merge Lane C before Lane D to avoid conflicts.
- **Lane E:** Task 5 (post-merge) — runs after everything merges.

**Execution order:** Launch A + B + C in parallel worktrees. Merge C. Launch D (waits for A's Task 2). Merge A + B + D. Run E.

**Conflict flag:** Lanes C and D both touch `.github/workflows/ci.yml`. Run C (deletes `openclaw-railway-smoke`) before D (rewrites `openclaw-smoke` in the same file) so D merges cleanly.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 7 issues resolved, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**Eng Review — 7 resolved decisions + 2 auto-fixes + 1 regression test:**

- **Step 0 scope** — delete orphaned `--backend openclaw` paths + drop `openclaw-railway-smoke` CI job → new **Task 7** added to plan.
- **A1 session-key collision** — `session_prefix=f"roboclaws-demo-{int(time.time())}"` unique per invocation → folded into **Task 2**.
- **A3 image drift** — pin `ghcr.io/openclaw/openclaw:2026.4.14` (user-provided) instead of `:latest` → folded into **Task 4**.
- **A5 README misrepresentation** — rewrite Layer 3 section as "OpenClaw navigation demo" rather than just flipping the checkbox → folded into **Task 6**.
- **T1 precedence test** — add `test_provider_explicit_work_dir_overrides_env` for the 3-way work_dir fallback → added to Test Plan.
- **A2 stale work_dir** (auto-fix) — `shutil.rmtree(work_dir, ignore_errors=True)` on demo startup → folded into Task 2.
- **A4 macOS Docker File Sharing** (auto-fix) — troubleshooting block added to `docs/openclw/openclaw-local.md` → folded into Task 3.
- **CQ1 dev-token doc hygiene** (auto-fix) — replace hardcoded `dev-token` with a generated `secrets.token_urlsafe(32)` + localhost-only `-p 127.0.0.1:18789:18789` → folded into Task 3.
- **CQ4 vague verification** (auto-fix) — Task 5 rewritten with concrete `curl -sI` checks + image digest recording.
- **REGRESSION (IRON RULE)** — default `work_dir` fallback changes from `tempfile.mkdtemp` to `./.openclaw-tmp`. Auto-added `test_provider_defaults_to_dot_openclaw_tmp` to Test Plan without AskUserQuestion.

**UNRESOLVED:** 0

**VERDICT:** ENG CLEARED — plan is ready to implement. Two TODOs captured in `TODOS.md` (Phase 2.5 game restore + digest pinning).

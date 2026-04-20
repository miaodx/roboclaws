<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/main-autoplan-restore-20260415-230209.md -->
# Phase 2: OpenClaw Integration — Completion Plan

## Problem Statement

Phase 2 aims to prove that AI2-THOR simulated robots can be controlled through an OpenClaw Gateway, producing a visible demo that populates the README's third layer. The existing `--backend openclaw` path in `territory_game.py` and `coverage_game.py` is broken due to a host/container path mismatch, over-complicated for a first demo, and bypasses the `AI2THORNavigatorSkill` wrapper entirely.

## Scope

### In scope
- Create a standalone `examples/openclaw_demo.py` that runs a simple multi-agent AI2-THOR scenario via `OpenClawProvider`
- Fix the host/container shared image directory contract (`work_dir`)
- Write `docs/openclaw-local.md` with the exact Docker run command including the bind mount
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

**New file:** `docs/openclaw-local.md`

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
| `OpenClawUnavailable: Gateway unreachable` | Local Gateway not running | Point user to `docs/openclaw-local.md` |
| `Gateway cannot read frame paths` | Missing `.openclaw-tmp` bind mount or path mismatch | Check `-v "$PWD/.openclaw-tmp:$PWD/.openclaw-tmp"` |

## Failure Modes

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| OpenClaw upstream changes image contract | CI breaks | Pinned to `ghcr.io/openclaw/openclaw:2026.4.14` (A3); record digest in Task 5 |
| Session-key collision across local runs | MEMORY leaks between demo invocations | `session_prefix=f"roboclaws-demo-{int(time.time())}"` in Task 2 (A1) |
| Stale `.openclaw-tmp` from prior run blocks host writes | PermissionError on JPEG save | `shutil.rmtree(work_dir, ignore_errors=True)` on demo startup (A2) |
| `$PWD` outside Docker Desktop File Sharing (macOS) | Gateway reports "file not found" | Troubleshooting note in `docs/openclaw-local.md` (A4 / Task 3) |
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
- **A4 macOS Docker File Sharing** (auto-fix) — troubleshooting block added to `docs/openclaw-local.md` → folded into Task 3.
- **CQ1 dev-token doc hygiene** (auto-fix) — replace hardcoded `dev-token` with a generated `secrets.token_urlsafe(32)` + localhost-only `-p 127.0.0.1:18789:18789` → folded into Task 3.
- **CQ4 vague verification** (auto-fix) — Task 5 rewritten with concrete `curl -sI` checks + image digest recording.
- **REGRESSION (IRON RULE)** — default `work_dir` fallback changes from `tempfile.mkdtemp` to `./.openclaw-tmp`. Auto-added `test_provider_defaults_to_dot_openclaw_tmp` to Test Plan without AskUserQuestion.

**UNRESOLVED:** 0

**VERDICT:** ENG CLEARED — plan is ready to implement. Two TODOs captured in `TODOS.md` (Phase 2.5 game restore + digest pinning).

---

# Phase 2.1 Amendment: Transport Correction

> ⚠️ Added 2026-04-16 after end-to-end validation of Tasks 1-7 surfaced an architectural error in the original plan. Tasks 1-7 are structurally correct (commits land clean, tests pass, lint passes) but all target the **wrong Gateway endpoint**. This amendment fixes the transport and re-validates live.

## Problem Statement

The original plan built `OpenClawBridge` against `POST /tools/invoke`, expecting a workspace skill (SKILL.md in `skills/ai2thor-navigator/`) to become an HTTP-invocable tool. That expectation is wrong for the pinned `ghcr.io/openclaw/openclaw:2026.4.14` image (and, as far as I can tell from the docs + source read, for every current OpenClaw version):

- `/tools/invoke` dispatches **only plugin-registered tools** (`acpx`, `browser`, `device-pair`, `phone-control`, `talk-voice`) via `api.registerTool()` — confirmed in `/app/dist/tools-invoke-http-*.js:135-145`.
- Workspace skills are **prompt-injection hints** consumed by the Gateway's LLM agent — confirmed in `/app/dist/skills-*.js:640` (`loadWorkspaceSkills`) which injects skills into the system prompt only.
- End-to-end validation with real Kimi + real AI2-THOR against the pinned image returns `404 Tool not available: ai2thor-navigator` on the first `/tools/invoke` call.

The correct transport is `POST /v1/chat/completions` — the Gateway's OpenAI-compatible chat endpoint. The Gateway agent's system prompt already contains every workspace skill (measured: 14,044 prompt tokens on a one-word user message with just our one skill mounted). A short per-turn user message steers the agent to follow `ai2thor-navigator` and reply in the skill's JSON shape.

Sources: [OpenClaw Skills docs](https://docs.openclaw.ai/tools/skills), [OpenAI Chat Completions HTTP API](https://docs.openclaw.ai/gateway/openai-http-api.md), [Tools Invoke HTTP API](https://docs.openclaw.ai/gateway/tools-invoke-http-api.md), Gateway source `/app/dist/` in image `sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`.

## Revised Architecture — named-agent routing

```
┌────────────────────────────────────────────────────────────────┐
│                      AI2-THOR Engine                           │
│                                                                │
│   sim agent 0 frame ──►  OpenClawProvider                      │
│   sim agent 1 frame ──►     │                                  │
│   sim agent N frame ──►     │  JPEG → base64 data URL          │
│                             ▼                                  │
│         POST /v1/chat/completions                              │
│           ├─► agent 0: model="openclaw/agent-0"                │
│           ├─► agent 1: model="openclaw/agent-1"                │
│           └─► agent N: model="openclaw/agent-N"                │
│                                                                │
│           body: OpenAI messages[] with:                        │
│             • text steer ("follow the ai2thor-navigator        │
│               skill, reply JSON only")                         │
│             • image_url (FPV as data URL)                      │
│             • image_url (overhead as data URL)                 │
│             • structured state (JSON text)                     │
│                                                                │
│ ┌────────────── Gateway: one process, N agents ─────────────┐  │
│ │                                                           │  │
│ │  agent-0               agent-1              agent-N       │  │
│ │   workspace/            workspace/           workspace/   │  │
│ │   SOUL.md               SOUL.md              SOUL.md      │  │
│ │   MEMORY.md             MEMORY.md            MEMORY.md    │  │
│ │   auth-profiles.json    ...                  ...          │  │
│ │   ai2thor-navigator     ai2thor-navigator    ai2thor-nav. │  │
│ │   (skill in prompt)     (skill in prompt)    (skill …)    │  │
│ │                                                           │  │
│ └───────────────────────────────────────────────────────────┘  │
│                                                                │
│  Each agent: independent memory, independent persona slot,     │
│  independent auth — matches SKILL.md's "each simulation agent  │
│  runs as a separate OpenClaw instance" promise.                │
└────────────────────────────────────────────────────────────────┘

No bind mount. No .openclaw-tmp. Images flow inline.
```

## Why named agents, not session headers

Both `model: "openclaw" + x-openclaw-session-key: <key>` and `model: "openclaw/<agentId>"` would work for the transport itself. We pick **named agents** because:

- `skills/ai2thor-navigator/SKILL.md` explicitly promises "each simulation agent runs as a separate OpenClaw instance, each with its own SOUL preset and independent memory". The session-header approach shares memory + persona across all sim agents; the named-agent approach gives each one its own.
- Mirrors the existing per-persona OpenClaw pattern already in use on this machine (`openclaw-alice`, `-bob`, `-carol` containers) — one Gateway process, many logical agents, same mental model.
- Trivially enables Phase 2.2 (per-agent SOUL presets — aggressive/defensive/cooperative): each agent already has its own workspace dir to drop a persona into.
- Model-id parser: `/app/dist/http-utils-*.js:resolveAgentIdFromModel` accepts `openclaw/<agentId>` where `agentId` matches `[a-z0-9][a-z0-9_-]{0,63}`. Missing / unknown agent → 4xx from the chat endpoint, caught fast.

Decision: bootstrap **always pre-creates N agents** (parameterized by `AGENTS` env var, default 2). Demo never calls `openclaw agents add` itself — single source of truth for agent configuration.

## Pure wins from the transport pivot

1. **No bind mount required** → A4 macOS File Sharing trap is gone.
2. **No container-UID-owned stale files** → A2 `shutil.rmtree` hack is gone.
3. **No host/container path identity** → whole class of drift errors gone.
4. **Railway / remote Gateways become viable again** → cloud relay (Issue 13) is no longer fundamentally blocked; just currently deferred.
5. **Per-agent independent memory** → closes the SKILL.md honesty gap.

## What the Gateway needs before it can answer

End-to-end validation uncovered six first-run setup steps the original plan missed. All are one-shot + idempotent — perfect for a bootstrap script:

1. **Chown the config volume + pre-create writable workspace dirs** — Docker creates `/home/node/.openclaw` and `workspace/` as root because of the skill bind mount's parent dirs, blocking the `node` user (uid 1000) from writing state files (`workspace/AGENTS.md`, etc.). Fix: in a one-shot `--user root` container before first startup, `mkdir -p` every dir the Gateway + each agent will need, then `chown -R 1000:1000` the whole tree.
2. **Enable chatCompletions** — `gateway.http.endpoints.chatCompletions.enabled = true` (default: false) in `openclaw.json`.
3. **Register N named agents + seed per-agent state** — for i in 0..N-1:
   - Add agent to `openclaw.json` `agents` map.
   - Create workspace dir `~/.openclaw/workspaces/agent-i/` (with the `ai2thor-navigator` skill bind-mounted).
   - Create agent dir `~/.openclaw/agents/agent-i/agent/` with its own `auth-profiles.json` carrying the Kimi `api_key`.
4. **Pin default model per agent** — each agent entry needs `model.primary = $MODEL` (e.g., `kimi/k2p5`).
5. **SKILL.md frontmatter** — every skill needs YAML frontmatter (`name`, `description`) or the loader drops it. Already fixed in the prep commit (5c812a1).
6. **Use `model: "openclaw/agent-<i>"` in requests** — the `/v1/chat/completions` endpoint rejects raw provider model ids with `"Use openclaw or openclaw/<agentId>"`. agentId regex: `[a-z0-9][a-z0-9_-]{0,63}` (lowercase, alphanumeric + `_-`).

## Scope

### In scope
- `scripts/openclaw-bootstrap.sh` — idempotent first-run setup: volume chown, seed `openclaw.json`, seed `auth-profiles.json`, start container, wait for `/readyz`, print token. Used by both `docs/openclaw-local.md` and CI.
- Rewrite `OpenClawBridge.step()` to `POST /v1/chat/completions` with OpenAI multimodal format.
- Simplify `OpenClawProvider.__init__` — drop `work_dir`, drop JPEG-on-disk flow, drop `.openclaw-tmp` handling.
- Rewrite `examples/openclaw_demo.py` to use the new bridge surface (feeds numpy frames directly, not base64 strings), drop `shutil.rmtree` startup.
- Live re-validation: run the demo end-to-end locally, capture `output/openclaw-demo/report.html` + `replay.gif`, commit the artefacts path in a demo-run log so Task 5 (post-merge verification) can diff against it.
- Rewrite `docs/openclaw-local.md` — `bootstrap.sh` one-liner, no bind mount, drop the stale-files + macOS troubleshooting (they can't happen anymore).
- Rewrite `.github/workflows/ci.yml` `openclaw-smoke` job to call `bootstrap.sh`.
- Retire `OPENCLAW_WORK_DIR` env var and the `./.openclaw-tmp` `.gitignore` entry (or keep `.gitignore` line since it's harmless — decide inside T10).
- Rewrite `tests/test_bridge.py` — existing tests assert the `/tools/invoke` contract and the work_dir fallback. Both are gone.

### Not in scope
- **Per-agent SOUL preset distribution** — bootstrap creates N agents with identical default SOUL. Distributing `skills/ai2thor-navigator/souls/{aggressive,defensive,cooperative}.md` to the corresponding agent workspaces is **Phase 2.2**. The architecture supports it trivially (each agent has its own workspace); we just aren't wiring it up here. File: add `Phase 2.2 — per-agent SOUL presets` to `TODOS.md` at Task 16 close.
- Territory / Coverage game modes over OpenClaw (same as before, later phase).
- Isaac Lab migration (Phase 3).
- Full remote/Railway support — no longer architecturally blocked, but out of this amendment's scope.

## Implementation Plan

### Task 8: `scripts/openclaw-bootstrap.sh`

**New file:** `scripts/openclaw-bootstrap.sh` (already landed in prep commit 5c812a1 — this task extends it to N agents).

Shape (env-driven, all overridable):

```bash
#!/usr/bin/env bash
# Idempotent first-run setup for a local or CI OpenClaw Gateway container.
# Uses: docker, python3 (for token generation + JSON reading).
#
#   AGENTS=2 \
#   AGENT_PREFIX=agent- \
#   CONTAINER=openclaw-gateway \
#   IMAGE=ghcr.io/openclaw/openclaw:2026.4.14 \
#   VOLUME=openclaw-demo-config \
#   PORT=18789 \
#   MODEL=kimi/k2p5 \
#   KIMI_API_KEY=sk-... \
#   ./scripts/openclaw-bootstrap.sh
#
# Outputs (stdout): the Gateway bearer token on a single line so callers can
#   `TOKEN=$(./scripts/openclaw-bootstrap.sh)` in both shells and GitHub Actions.
```

Behaviour:
1. If `CONTAINER` already exists, remove it (clean slate).
2. `docker volume create $VOLUME` (idempotent).
3. One-shot `docker run --rm --user root -v $VOLUME:/home/node/.openclaw $IMAGE` to:
   - `mkdir -p` every dir the Gateway + all N agents will need — including per-agent workspace + per-agent `agents/<id>/agent/` — *before* the real container starts (so Docker doesn't create intermediate dirs as root).
   - Seed `openclaw.json` with:
     - `gateway.auth.mode = "token"`
     - `gateway.http.endpoints.chatCompletions.enabled = true`
     - `agents` map: for each `agent-i` (i=0..AGENTS-1), an entry with `{ workspace: "/home/node/.openclaw/workspaces/agent-i", model: { primary: $MODEL } }`.
     - `agents.defaults.model.primary = $MODEL` so the default agent ("main") also has a valid model — harmless and avoids any "no default" edge case.
   - For each `agent-i`, seed `/home/node/.openclaw/agents/agent-i/agent/auth-profiles.json` with `{"profiles": {"kimi:manual": {"type": "api_key", "provider": "kimi", "key": "$KIMI_API_KEY"}}}` (schema per `/app/dist/store-*.js:parseCredentialEntry`).
   - For each `agent-i`, symlink or copy the `ai2thor-navigator` skill into `/home/node/.openclaw/workspaces/agent-i/skills/ai2thor-navigator`. Actual wiring: one read-only host-side bind mount per agent in step 4 (simpler than copying inside the volume).
   - `chown -R 1000:1000 /home/node/.openclaw`.
4. `docker run -d` the Gateway with:
   - Config volume mount at `/home/node/.openclaw`.
   - One `--mount type=bind,source=$SKILLS_DIR,target=/home/node/.openclaw/workspaces/agent-i/skills/ai2thor-navigator,readonly=true` per agent (a loop builds the `-v` flags). This is more bind mounts but each agent's skill catalog is independent and we can vary skills per agent in Phase 2.2 without rewiring.
5. Wait up to 60s for `/readyz` with bearer auth.
6. `openclaw.json` seeding already pinned the default model per agent; verify via `python3 -c "import json; …"` rather than calling the CLI a second time.
7. Probe `POST /v1/chat/completions` with `model="openclaw/agent-0"` to confirm the full chain (auth profile, skill mount, chat endpoint) works before the demo starts. Fail fast if the first agent doesn't PONG back.
8. Read the live token from `openclaw.json` (the Gateway regenerates the auth token on first boot regardless of env) and echo it on the last stdout line.

Failure modes:
- Missing `KIMI_API_KEY` → exit 1 with a usage hint.
- `AGENTS < 1` or `AGENTS > 8` → exit 1 ("out of supported range; file a Phase 2.x issue if you need more").
- Docker pull fails → exit 2 with the real error.
- `/readyz` never returns 200 within 60s → `docker logs` + exit 3.
- Probe fails → exit 4 with the raw probe body + `docker logs` tail (so the user sees the real Kimi/auth/skill error, not a generic bootstrap failure).

### Task 9: Rewrite `OpenClawBridge.step()` for `/v1/chat/completions` with named agents

**File:** `roboclaws/openclaw/bridge.py`

New `step()` signature (drops `frame_path` / `overhead_path` — they're now inline):

```python
def step(
    self,
    agent_id: int,
    frame: np.ndarray,            # first-person RGB (H, W, 3) uint8
    overhead: np.ndarray,         # overhead map RGB (H, W, 3) uint8
    state: dict[str, Any],
    step_idx: int,
) -> dict[str, Any]:
    """POST a turn to /v1/chat/completions for agent-<agent_id> and parse the action out."""
```

`OpenClawBridge.__init__` gains `agent_prefix: str = "agent-"` so the bridge can compose `model = f"openclaw/{agent_prefix}{agent_id}"` without the caller repeating the prefix. Matches the bootstrap's `AGENT_PREFIX` env var — single source of truth for the naming scheme.

Body:
1. JPEG-encode `frame` and `overhead` → base64 data URLs via `Image.fromarray(...).save(buf, "JPEG", quality=80)`.
2. Build OpenAI messages with a short user steer:
   ```
   user:
     text: "You are RoboClaws {agent_prefix}{agent_id}, step {step_idx}/{max}.
            Follow the ai2thor-navigator skill. Current state (JSON):
            {state_json}. FPV and overhead map attached.
            Reply with ONLY JSON: {\"reasoning\": ..., \"action\": ...}."
     image_url: data:image/jpeg;base64,<fpv>
     image_url: data:image/jpeg;base64,<overhead>
   ```
3. POST with:
   - `Authorization: Bearer <token>`
   - `Content-Type: application/json`
   - body `model = f"openclaw/{agent_prefix}{agent_id}"` (routes to the named agent → its own SOUL / MEMORY / auth)
   - NO `x-openclaw-session-key` header — the named-agent model provides isolation already.
4. Parse `choices[0].message.content`, strip any code fences, `json.loads` → `{"reasoning", "action"}`.
5. Validate `action ∈ NAVIGATION_ACTIONS`, fall back to `MoveAhead` with a visible warning if malformed.
6. Error mapping:
   - `ConnectError` / `ReadTimeout` → `OpenClawUnavailable` (unchanged).
   - HTTP 401 → `OpenClawUnavailable("Gateway rejected bearer token")`.
   - HTTP 400 `"Invalid model"` → `OpenClawUnavailable("agent 'agent-{N}' not registered — run scripts/openclaw-bootstrap.sh with AGENTS>=N+1")`.
   - HTTP 404 → `OpenClawUnavailable("/v1/chat/completions not enabled — re-run scripts/openclaw-bootstrap.sh")`.
   - HTTP 5xx + `{"error": ...}` → `OpenClawUnavailable(body["error"]["message"])`.
   - Non-JSON response from LLM → log full content, return fallback action.

### Task 10: Simplify `OpenClawProvider`

**File:** `roboclaws/openclaw/bridge.py`

- Drop `work_dir` parameter, `OPENCLAW_WORK_DIR` env handling, `_write_image`, the entire `.openclaw-tmp` directory creation.
- Drop `session_prefix` — replaced by `agent_prefix` (see Task 9). One less magic string; matches bootstrap's `AGENT_PREFIX`.
- `get_action(images: list[str], state: dict)` → change signature to accept numpy arrays directly. The base64 intermediate is wasteful given the VLM provider protocol originally used it for the OpenAI providers; for OpenClaw we skip straight to bytes. Grep confirms only caller is `examples/openclaw_demo.py`, updated atomically in Task 11.

### Task 11: Rewrite `examples/openclaw_demo.py`

- Drop `_prepare_work_dir()` (no longer needed — no filesystem exchange).
- Drop `shutil.rmtree` + `OPENCLAW_WORK_DIR` plumbing.
- `OpenClawProvider` gets constructed with just `gateway_url`, `token`, `agent_prefix` — no `work_dir`, no `session_prefix`.
- Add `--agent-prefix` CLI flag (default: `"agent-"`) mirroring the bootstrap's `AGENT_PREFIX`.
- **Precondition check**: before starting the run, demo probes the first agent (`model="openclaw/agent-0"`) with a one-turn PONG to confirm the named agent exists. Fail-fast with an actionable message pointing to `scripts/openclaw-bootstrap.sh AGENTS=$AGENTS` if it doesn't. Avoids the demo running 19 steps before hitting "agent not registered".
- On startup, log: "Gateway URL:", "Agent prefix:", "Agents: agent-0, agent-1, ... (model=openclaw/<agentId>)", "Model (resolved by Gateway):" (read from the probe response).
- Shorter main-flow since no bind-mount prep required.

### Task 12: Rewrite `docs/openclaw-local.md`

Target shape (much shorter than current):

```markdown
## 1. Bootstrap the Gateway (creates N named agents)
export KIMI_API_KEY=sk-...
TOKEN=$(AGENTS=2 ./scripts/openclaw-bootstrap.sh)

## 2. Run the demo
OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/openclaw_demo.py --agents 2 --steps 20

## 3. Clean up
docker rm -f openclaw-gateway
docker volume rm openclaw-gateway-config
```

Plus a short "What the bootstrap actually did" section:
- Created `agent-0`, `agent-1` (or N) named agents with isolated workspaces.
- Each agent has its own `~/.openclaw/agents/<id>/agent/auth-profiles.json` carrying the Kimi key.
- Each agent's workspace has `skills/ai2thor-navigator/` bind-mounted read-only.
- `/v1/chat/completions` is enabled; requests route per-agent via `model=openclaw/agent-<i>`.

Troubleshooting section shrinks to four items:
- `bootstrap.sh` exits 2 on pre-seed → docker daemon + socket perms.
- Gateway returns 401 → token was regenerated; extract with `docker exec openclaw-gateway cat /home/node/.openclaw/openclaw.json | jq -r .gateway.auth.token` or just re-run `bootstrap.sh` and re-capture.
- Gateway returns 400 "Invalid model" on `openclaw/agent-N` → bootstrap didn't create agent-N; re-run with higher `AGENTS=`.
- Gateway returns 404 on `/v1/chat/completions` → bootstrap didn't enable the endpoint; re-run.

Delete: the macOS File Sharing block, the "container-UID-owned stale files" block, the "host+container path identity" block. Those failure modes are gone.

### Task 13: Rewrite CI `openclaw-smoke`

**File:** `.github/workflows/ci.yml`

Replace the current inline Docker run + token-extraction + preflight + skill-mount step with:

```yaml
- name: Bootstrap OpenClaw Gateway (2 named agents)
  id: gateway
  continue-on-error: true
  env:
    KIMI_API_KEY: ${{ secrets.KIMI_API_KEY }}
    AGENTS: "2"
  run: |
    TOKEN=$(./scripts/openclaw-bootstrap.sh)
    echo "::add-mask::$TOKEN"
    echo "token=$TOKEN" >> "$GITHUB_OUTPUT"

- name: Run OpenClaw navigation demo
  if: steps.gateway.outcome == 'success'
  env:
    OPENCLAW_GATEWAY_TOKEN: ${{ steps.gateway.outputs.token }}
  run: |
    xvfb-run -a python examples/openclaw_demo.py \
      --agents 2 --steps 10 \
      --output-dir output/openclaw/demo
```

Drop: the `mkdir -p $PWD/.openclaw-tmp`, the `-v $PWD/.openclaw-tmp:...` bind mount, the `Resolve Gateway token from container config` step (bootstrap does it), the `Wait for Gateway readiness` step (bootstrap does it), the `KIMI_API_KEY` secret from the demo step env (the Gateway has it; the demo doesn't need it).

Keep: `continue-on-error: true` at the job level, image pin (now lives inside bootstrap's `IMAGE` default — job exports it explicitly to keep the pin visible in the workflow), artifact upload, publish-pages wiring (still `site/openclaw/demo/`).

Add: `::add-mask::` on the captured token so it doesn't leak into log output if a later step prints it.

### Task 14: Rewrite `tests/test_bridge.py`

Tests that must be deleted (they test the old contract):
- `test_provider_uses_env_work_dir`
- `test_provider_defaults_to_dot_openclaw_tmp`
- `test_provider_explicit_work_dir_overrides_env`
- Any `test_bridge_step_*` that asserts `/tools/invoke` path, `sessionKey` body field, or the provider-writes-JPEG behaviour.

New tests:
- `test_bridge_step_posts_to_chat_completions` — mock `httpx.Client`, assert URL path `/v1/chat/completions`, `model = "openclaw/agent-0"`, presence of FPV + overhead image_url parts in the OpenAI payload.
- `test_bridge_step_parses_action_from_response` — feed a canned `chat.completion` response with JSON in `choices[0].message.content`, assert the bridge extracts the action.
- `test_bridge_step_fallback_on_malformed_json` — canned non-JSON content → bridge returns `MoveAhead` + logs warning.
- `test_bridge_step_raises_on_400_invalid_model` — canned 400 with "Invalid model" body → `OpenClawUnavailable` with the "run bootstrap with higher AGENTS=" hint.
- `test_bridge_step_raises_on_404` — canned 404 response → `OpenClawUnavailable` pointing at re-running bootstrap.
- `test_bridge_uses_agent_prefix_in_model_id` — construct bridge with `agent_prefix="bot-"`, call `step(agent_id=3, …)`, assert outbound `model == "openclaw/bot-3"`.
- `test_bridge_validates_action_in_navigation_actions` — LLM returns `{"reasoning": "...", "action": "Teleport"}` (valid) → passes through; returns `"WalkIntoWall"` (invalid) → coerced to `MoveAhead`.

Target test count: ~7 bridge tests (replaces the existing 27+3).

### Task 15: Live re-validation + artefact capture

**Validation (concrete — supersedes Task 5):**
1. `set -a && source .env && set +a && TOKEN=$(AGENTS=2 ./scripts/openclaw-bootstrap.sh)` completes cleanly; log shows "agents registered: agent-0, agent-1" + "probe ok".
2. `openclaw/agent-0` and `openclaw/agent-1` both answer a PONG probe independently (sanity-check each named agent exists and has its own auth):
   ```bash
   for a in agent-0 agent-1; do
     curl -s -X POST http://127.0.0.1:18789/v1/chat/completions \
       -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
       -d "{\"model\":\"openclaw/$a\",\"messages\":[{\"role\":\"user\",\"content\":\"PONG\"}]}"
   done
   ```
3. `OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/openclaw_demo.py --agents 2 --steps 8` runs to completion.
4. `output/openclaw-demo/report.html` is >10 KB and opens in a browser.
5. `output/openclaw-demo/replay.gif` renders per-step transitions with visible agent movement.
6. `output/openclaw-demo/replay.json` — spot-check 3 random steps: each has a non-empty `vlm_response.reasoning` and a valid `action`.
7. Spot-check per-agent isolation: after the run, compare `docker exec openclaw-gateway ls /home/node/.openclaw/workspaces/agent-0/` vs `.../agent-1/`. Either both have independent `MEMORY.md` changes or both are empty (with identical content = failure, because they'd be sharing state).
8. Commit-message capture: image digest (`docker inspect ghcr.io/openclaw/openclaw:2026.4.14 --format '{{index .RepoDigests 0}}'`) + Kimi model actually used (read from `replay.json` `summary.provider_status.model`).
9. After merge + `openclaw-smoke` green, `curl -sI https://miaodx.github.io/roboclaws/openclaw/demo/report.html | head -1` → `HTTP/2 200`.

### Task 16: Retro-update the README / PLAN.md

- No README changes (still points at `/openclaw/demo/` — the URL is unchanged).
- Add a short `## Phase 2.1 retrospective` section at the bottom of PLAN.md naming the bug + the fix (so future plans catch this upstream-contract class of error earlier).
- Update `docs/issues-roadmap.md` Phase 2 section — unblock Issue 13 (cloud relay) since transport is no longer bind-mount-bound.

## Test Plan (additions / replacements)

| Codepath | Test | Location | Status vs original plan |
|----------|------|----------|-------------------------|
| Bridge work_dir fallback (3 tests) | — | — | **DELETED** (T14) — no longer applicable |
| Bridge POSTs to `/v1/chat/completions` | `test_bridge_step_posts_to_chat_completions` | `tests/test_bridge.py` | NEW (T14) |
| Bridge parses action from OpenAI content | `test_bridge_step_parses_action_from_response` | `tests/test_bridge.py` | NEW (T14) |
| Bridge handles malformed LLM JSON | `test_bridge_step_fallback_on_malformed_json` | `tests/test_bridge.py` | NEW (T14) |
| Bridge maps 404 to readable error | `test_bridge_step_raises_on_404` | `tests/test_bridge.py` | NEW (T14) |
| Bridge per-agent session header | `test_bridge_session_header_per_agent` | `tests/test_bridge.py` | NEW (T14) |
| `scripts/openclaw-bootstrap.sh` shellcheck | `shellcheck scripts/openclaw-bootstrap.sh` | `lint-and-mock` CI | NEW (T8) |
| Demo end-to-end (live Gateway) | `openclaw-smoke` job runs `bootstrap.sh` + demo → non-empty `report-openclaw` artifact | `.github/workflows/ci.yml` | CHANGED (T13) |

## Effort Estimate (amendment)

| Task | Human | CC+gstack |
|------|-------|-----------|
| Task 8 (bootstrap script) | ~1 h | ~15 min |
| Task 9 (bridge rewrite) | ~1 h | ~15 min |
| Task 10 (provider cleanup) | ~20 min | ~5 min |
| Task 11 (demo rewrite) | ~20 min | ~5 min |
| Task 12 (docs rewrite) | ~30 min | ~5 min |
| Task 13 (CI rewrite) | ~20 min | ~5 min |
| Task 14 (test rewrite) | ~1 h | ~15 min |
| Task 15 (live re-validation) | ~30 min (one real demo run) | ~10 min |
| Task 16 (retro + roadmap) | ~15 min | ~5 min |

**Total for amendment: ~5 h human / ~1 h 20 min CC+gstack.**

## Failure Modes (amendment)

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| Kimi API key invalid | Gateway 500s on every `/v1/chat/completions` | `bootstrap.sh` runs a one-shot `curl` preflight after seed to catch this before demo starts |
| Gateway regenerates auth token on restart | Stale token in CI → 401 | `bootstrap.sh` always reads the live token from `openclaw.json` post-start |
| Kimi changes prompt-token limit and our 14k skill prompt overflows | `chat.completions` 400 | `openclaw models list` reports ctx; fall back to a smaller skill set or a compact skill variant |
| LLM returns "action" outside `NAVIGATION_ACTIONS` | Non-crashing but useless step | Bridge validates + defaults to `MoveAhead`, logs the raw response for debugging (existing behaviour retained) |
| `/v1/chat/completions` rate-limited | Burst of 429s | Reuse `roboclaws/core/provider_retry.py` retry machinery (the VLM providers already use it — wire it into the bridge) |

## Phase 2.1 retrospective

Filed 2026-04-16 after Tasks 8-14 landed and the transport rewrite passed
mock tests + lint. Live re-validation (Task 15) is the separate next
gate — this retrospective captures the *bug class* that motivated the
amendment, so future plans catch it upstream.

- **Bug class**: "we built against an API surface we hadn't proven end-to-end". The 7 original tasks all passed lint + tests + plan review, because the test suite mocked `httpx` responses shaped like the endpoint we *expected* (`/tools/invoke` with `ok/result` body), not the endpoint that actually exists in the pinned image (`/v1/chat/completions` with OpenAI-style `choices[]`). CI's `openclaw-smoke` job was guarded with `continue-on-error: true` and thus silently absorbed the 404 any real run would have produced.
- **Lesson**: any new external HTTP contract must have at least one integration test that hits the *actual* upstream before the plan clears eng-review. Post-merge verification is too late — it should be a pre-merge gate (live-Gateway demo run with a captured `report.html`).
- **Fix for future plans**: when a plan's eng-review marks an external integration as critical, add an "AUTH → READYZ → ONE-REAL-REQUEST" Nyquist gate ahead of any task that builds on it. Bootstrap scripts go *in* the plan, not retrofitted. The Phase 2.1 `scripts/openclaw-bootstrap.sh` ended up doing this — it both sets up the Gateway **and** probes `/v1/chat/completions` on `agent-0` with a PONG turn, failing fast with a pointer to the actual error. That probe belongs in the plan from day 1 for any similar "new upstream HTTP surface" phase.
- **Side benefit**: the named-agent routing (`model=openclaw/<agentId>` instead of a session header) that this amendment adopts also unblocks Issue 13 (remote/Railway Gateway) — the transport is no longer bind-mount-bound. Closing the honesty gap with `SKILL.md`'s per-agent-instance promise and unblocking cloud relay fell out of the same fix.

---

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
- `docs/openclaw-local.md`: add `AGENT_SOULS=aggressive,defensive,cooperative` example + per-game usage snippets.
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

### Task 25: Update `docs/openclaw-local.md`

**File:** `docs/openclaw-local.md`

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
| T25 (docs/openclaw-local.md) | ~20 min | ~3 min |
| T26 (bootstrap test) | ~30 min | ~5 min |
| T27 (TODOS.md update) | ~10 min | ~2 min |
| T28 (live re-validation) | ~30 min | ~10 min |
| T29 (retrospective) | ~15 min | ~5 min |

**Total: ~5h human / ~1h 10min CC+gstack** (plus local validation time for T28).

## What already exists (reuse, don't rebuild)

- **SOULs themselves** — `skills/ai2thor-navigator/souls/{aggressive,defensive,cooperative}.md` (3 files, all written). T17 only wires distribution.
- **Long-running container behavior** — `scripts/openclaw-bootstrap.sh` already starts a container that survives until `docker rm -f`. No new lifecycle code.
- **Per-agent named-agent isolation** — Phase 2.1 already created independent workspaces, agent dirs, and auth profiles per agent. T17 fills the SOUL slot inside the existing structure.
- **Gateway workspace SOUL.md slot** — `docs/openclaw-gateway-internals.md:67` documents `workspaces/<agentId>/SOUL.md` as the persona slot. Already there, waiting to be filled.
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
| 10 | DX3 | TTHW for Layer 3 territory is ~15-30 min vs ~30s for Layer 2; plan claims "symmetry" but onboarding is asymmetric | New T24a: add `make openclaw-territory` + `make openclaw-coverage` targets (or `scripts/run-layer3-{territory,coverage}.sh`) wrapping bootstrap + token capture + game run with progress echoed. T24 README adds: "**First local run takes ~15 min** (Docker pull + Unity download). See `docs/openclaw-local.md`. Already set up? `make openclaw-territory`." | P1 (completeness) |
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
| T25 | `docs/openclaw-local.md` update | Self-contained per-game recipes, AGENT_SOULS variable table, SOUL probe explanation. |
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
— see below.

---

# Phase 2.3 — Pin OpenClaw Gateway image by digest (declined 2026-04-20)

**Decision:** keep `:2026.4.14` instead of pinning by digest.

**Rationale:** the date-shaped tag reads as its release date at a glance
(2026-04-14). That's more useful when skimming CI logs, PRs, or
`docker pull` output than an opaque `sha256:7ea0...`. Digest pinning's
immutability gain is real but modest — upstream re-tagging is a
theoretical risk we haven't hit, and the `OPENCLAW_IMAGE` repo-variable
override already provides the escape hatch if we ever need to pin to a
specific digest without a code change.

**For the record** — the 2026-04-14 digest resolved via the GHCR
manifest API on 2026-04-20 was
`sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
(multi-arch manifest list). Future-us can drop that into the
`OPENCLAW_IMAGE` repo variable as a one-click rollback if upstream ever
re-tags.

**Revisit trigger:** upstream actually re-tags `:2026.4.14`, or we move
to an appliance mode where bit-exact reproducibility matters more than
log readability.

---

# Phase 2.4 — Map representation & view composition A/B

## Problem Statement

VLM agents currently receive two images per step: a first-person camera
frame and a photorealistic top-down overhead with grid tints + agent
dots. Two open questions the team wants answered with data, not vibes:

1. **Does a structured occupancy-grid-style overhead beat the photo
   overhead?** The current top-down leans on VLM segmentation: the model
   has to re-infer walls and free space every step from pixels. AI2-THOR
   already exposes ground-truth reachability via
   `GetReachablePositions` — we can pre-render walls/free/claimed as
   distinct regions. Open question: does that actually help the model,
   or does the photo prior win?
2. **Does adding a third over-the-shoulder chase-cam view improve
   navigation decisions?** Prior user projects saw real gains from a
   slightly-elevated behind-the-agent view for near-obstacle turn
   decisions. Want to reproduce that here and, specifically, separate
   its contribution from the map-v2 contribution so we know which lever
   matters.

The deliverable is a measured answer (with CIs and paired significance
tests), not a shipped feature. If variant C wins, Phase 2.5 ships it as
the default. If variant A wins, we stop spending tokens on a second
image.

## Scope

### In scope

- Three image-input variants for existing games:
  - **A (baseline)**: current 2 images — FPV + `render_overhead_map`
    with photorealistic top-down + cell tints + agent dots.
  - **B (map-v2)**: 2 images — FPV + **structured overhead**: pure grid
    rendering driven by `GetReachablePositions`. Unreachable = solid
    dark; reachable-unclaimed = light; claimed-by-self, claimed-by-
    other-i, covered = distinct colors. Agent marker = arrow in heading
    direction, not circle.
  - **C (map-v2 + chase-cam)**: 3 images — FPV + map-v2 + third-person
    over-the-shoulder view via a per-agent `AddThirdPartyCamera`
    (~1.0 m behind, ~1.5 m above, ~20° pitch down) with per-step
    `UpdateThirdPartyCamera` to follow the active agent.
- Three game paths must support the `--views` flag: `openclaw_demo.py`
  (navigation), `territory_game.py`, `coverage_game.py`.
- A/B harness `examples/view_experiment.py` that sweeps variants × seeds
  × scenes × games and emits `output/view-experiment/results.jsonl` +
  per-run replay directories.
- Analysis script `scripts/analyze_view_experiment.py`: reads the JSONL,
  emits a summary table with bootstrap 95% CIs and paired Wilcoxon
  signed-rank tests (paired by `(seed, scene, game)` tuple).
- Writeup in `docs/view-experiment-2026-04.md` with sample GIFs
  per variant and a one-line verdict per question.
- A new `NvidiaProvider` that talks to `https://integrate.api.nvidia.com/v1`
  (OpenAI-compatible surface) so we can drive NVIDIA-hosted VLMs with
  the same `get_action(images, state)` contract. Specific model choice
  is a T29a sub-decision (probably `meta/llama-4-maverick-17b-128e-instruct`
  or `nvidia/llama-3.1-nemotron-nano-vl-8b-v1`, probed live).
- Local-dev execution: 5 seeds × 3 scenes × 2 games × 3 variants = 90
  runs on `kimi-for-coding` as the workhorse (reuses the existing
  `KimiCodingProvider` + its circuit-breaker machinery from Phase 2.2);
  12-run confirm set on the chosen NVIDIA model comparing the top two
  variants from the Kimi study.

### Not in scope

- Integrating a real ROS2-nav / NavMap occupancy-grid service. Map-v2
  is an AI2-THOR-native overlay, not a general navigation stack.
- Per-agent chase-cam tuning per SOUL (e.g., aggressive gets lower FOV).
  Single fixed pose for all agents.
- Changing the **action space** or game rules. This phase only touches
  image inputs, not the decision model.
- Shipping the winning variant as the default. That is a follow-up
  phase (Phase 2.5) gated on the results here.
- Running the experiment on GPT-4o / Claude Sonnet. Those models are
  parked this phase; if a variant wins decisively on Kimi + NVIDIA,
  Phase 2.5 can optionally re-confirm on them.
- Multi-model cross-product on the full grid. Only Kimi runs all 90
  cells; NVIDIA only runs the 12-cell confirm. Full cross is a
  Phase 2.5 option if results are close.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  view_experiment.py (driver)                    │
│  variants × seeds × scenes × games → N runs                     │
│                      │                                          │
│                      ▼                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  TerritoryGame / CoverageGame / openclaw_demo loop       │   │
│  │                                                          │   │
│  │  prompt_images = view_builder(variant, engine, game)     │   │
│  │                  ┌──────────────┬─────────────┐          │   │
│  │                  │ "baseline"   │ "map-v2"    │"...+chase"│  │
│  │                  └──────────────┴─────────────┘          │   │
│  │                      │                                   │   │
│  │                      ▼                                   │   │
│  │   provider.get_action(images=prompt_images, state=...)   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                      │                                          │
│                      ▼                                          │
│             ReplayRecorder → replay.json + GIF                  │
│             + results.jsonl row tagged with `variant`           │
└─────────────────────────────────────────────────────────────────┘
```

The view-builder is the only new prompt seam. Providers are unchanged:
`get_action(images: list[str], …)` already accepts N images. No new
contract.

## Implementation Plan

### Task T29a: Add `NvidiaProvider` to `roboclaws/core/vlm.py`

**Files:** `roboclaws/core/vlm.py`, `tests/test_nvidia_provider.py`,
`docs/openclaw-local.md` (env-var table addition).

1. New class `NvidiaProvider` that follows `OpenAIProvider`'s shape:
   uses the `openai` SDK with `base_url="https://integrate.api.nvidia.com/v1"`,
   `api_key=os.environ["NVIDIA_API_KEY"]`, and `instructor.from_openai`
   for structured output via the same `_build_agent_action_model()`.
2. Add canonical-alias entries to `_MODEL_ALIASES`:
   - `"nvidia"` → `"meta/llama-4-maverick-17b-128e-instruct"`
     (default pick; a live probe during T35 prep can swap to
     `nvidia/llama-3.1-nemotron-nano-vl-8b-v1` if latency/quality is
     better).
   - Every full model name we want to address, so
     `create_provider("meta/...")` and
     `create_provider("nvidia/...")` both route to `NvidiaProvider`.
3. Add `_COST_PER_M` entries for the chosen models (price lookup from
   NVIDIA's published per-model rates; leave `{0, 0}` fallback if
   unpublished so `cumulative_cost` reports 0 rather than crash).
4. **Live probe** (local-dev step during T35 prep, not a CI gate):
   build `NvidiaProvider(model="meta/llama-4-maverick-17b-128e-instruct")`,
   send one real `get_action(images=[small_b64], state={"hello":"world"})`
   call, assert the returned `action` is in `NAVIGATION_ACTIONS`. This
   is the "new external HTTP surface" live-probe gate — per
   `feedback_live_probe_gate.md`, before merge.
5. Unit tests (mocked SDK):
   - `_COST_PER_M` hit + miss paths don't crash.
   - `get_action` with a 3-image payload serialises to the OpenAI image
     format (2 images baseline, 3 images for variant C).
   - `ProviderStatus.to_dict()` shape parity with other providers.

### Task T30: Structured map renderer (`render_structured_map`)

**Files:** `roboclaws/core/visualizer.py`, `tests/test_visualizer_structured.py`

1. Add `GameVisualizer.render_structured_map(*, agent_positions,
   agent_rotations, reachable_cells, claimed_cells, covered_cells,
   world_bbox) -> PIL.Image`. Pure rendering — no AI2-THOR imports.
2. Rendering contract:
   - Fixed 2 px/cell margin around `world_bbox` for legibility.
   - Unreachable (any cell in bbox not in `reachable_cells`) → `(60,60,60)`.
   - Reachable-unclaimed-uncovered → `(230,230,230)`.
   - Covered (coop coverage) → `(180,230,180)`.
   - Claimed by agent i → SOUL colour (fallback agent palette) at
     `alpha=255` — solid, not tinted — so the boundary is crisp.
   - Agent marker: filled triangle pointing in `rotation['y']` direction,
     height ≈ 1.4 × cell size, outlined black. Agent id label inside.
3. Keep `render_overhead_map` as-is — baseline uses it verbatim.
4. Tests (5+):
   - Unreachable cells render as dark when passed an incomplete
     `reachable_cells` set.
   - Agent triangle points in 4 cardinal directions for
     `y ∈ {0, 90, 180, 270}` — assert dominant non-background pixels
     sit in the expected quadrant of each agent's cell.
   - Three agents at distinct SOULs render in three distinct colours
     (same `assert not np.array_equal` approach as T26).
   - Empty `claimed_cells` and empty `covered_cells` both render cleanly.
   - Output size matches `world_bbox` × `cell_px` within the 2 px margin.

### Task T31: Chase-cam integration in `MultiAgentEngine`

**Files:** `roboclaws/core/engine.py`, `tests/test_engine_chase_cam.py`

1. Add `MultiAgentEngine.add_chase_cam(agent_id: int) -> int` that
   registers a third-party camera and returns its stable index. Pose is
   computed once at registration; the first frame will still look wrong
   until `update_chase_cam` runs.
2. Add `MultiAgentEngine.update_chase_cam(agent_id: int)` that issues
   `UpdateThirdPartyCamera` with pose:
   - position = agent pos + rotation-rotated `(0, 1.5, -1.0)` offset
     (metres; behind + above the agent in agent-local frame).
   - rotation = `(20°, agent_y, 0°)` — pitch down 20°, match agent yaw.
3. Add `MultiAgentEngine.get_chase_cam_frame(agent_id: int) -> np.ndarray`.
4. **Smoke test (local-dev, not CI):** verify per-step pose updates
   actually render (AI2-THOR's third-party camera API may not accept
   `Update` mid-step on all engine versions; fallback is to remove +
   re-add per step, more expensive but always works).
5. Unit test with a mocked controller verifies the position/rotation
   math for 4 cardinal agent headings.

### Task T32: `--views` flag + view-builder dispatch

**Files:** `roboclaws/core/views.py` (new), `examples/openclaw_demo.py`,
`examples/territory_game.py`, `examples/coverage_game.py`,
`tests/test_views.py`

1. New `roboclaws/core/views.py` exports
   `build_prompt_images(variant, *, engine, game, active_agent_id,
   overhead_bg, world_bbox) -> list[np.ndarray]`.
   - `variant="baseline"` → current 2 frames.
   - `variant="map-v2"` → FPV + `render_structured_map(...)` as numpy.
   - `variant="map-v2+chase"` → the map-v2 pair + the chase-cam frame
     for the active agent. Requires `engine.update_chase_cam(active)`
     to have been called this step.
2. Add `--views {baseline,map-v2,map-v2+chase}` CLI flag (default
   `baseline`) to all three examples.
3. Replace `prompt_images = [active_state.frame, map_frame]` in
   `openclaw_demo.py` with the view-builder call. Same wiring in the
   two games.
4. Tests: for each variant, assert `len(build_prompt_images(...))` is
   the expected count (2, 2, 3) and each element is a valid
   `(H, W, 3) uint8` array.

### Task T33: A/B experiment harness

**Files:** `examples/view_experiment.py`, `tests/test_view_experiment.py`

1. CLI: `--variants baseline,map-v2,map-v2+chase --seeds 1,2,3,4,5
   --scenes FloorPlan201,FloorPlan205,FloorPlan210 --games
   territory,coverage --model kimi-coding --agents 3
   --output-dir output/view-experiment --max-usd 15`. `--max-usd` is a
   cumulative wallet cap across all runs in the sweep — if
   `sum(cumulative_cost)` crosses it, the harness aborts cleanly
   (writes what it has, prints remaining runs).
2. For each `(variant, seed, scene, game)` cross-product run:
   - Seed `random.seed(seed)`, `np.random.seed(seed)`.
   - Construct provider with `reset_cost()`.
   - Run the game; capture: scores per agent, total_steps,
     termination_reason, cumulative USD, wallclock seconds, blocking
     events, `provider_status.to_dict()`.
   - Append one JSONL row to `results.jsonl` tagged with all experiment
     coordinates.
   - Save the full replay under
     `output/view-experiment/<variant>/<game>/<scene>-seed<N>/`.
3. A failed run (provider circuit opens, AI2-THOR crashes) logs a row
   with `status=error` and the error kind; the harness continues.
4. Test: smoke with `MockProvider`, 1 variant × 1 seed × 1 scene × 1
   game, assert `results.jsonl` has exactly 1 well-formed row.

### Task T34: Analysis script

**Files:** `scripts/analyze_view_experiment.py`,
`tests/test_analyze_view_experiment.py`

1. Input: `--input output/view-experiment/results.jsonl`.
2. Output: printed table + `output/view-experiment/summary.md` with:
   - Mean + bootstrap 95% CI of the primary metric per `(variant, game)`.
     Primary = `cells_claimed_sum` for territory, `coverage_fraction`
     for coverage, `visited_cells` for navigation.
   - Secondary metrics: mean USD/run, mean wallclock, mean blocking
     events, mean steps-to-termination.
   - Paired Wilcoxon signed-rank test comparing
     `{B vs A, C vs A, C vs B}` per game, paired on `(seed, scene)`.
     Report `p` and effect size.
   - Bold the best variant per game if `p < 0.05`.
3. No plotting dependency — text/markdown output only.
4. Test with synthetic JSONL (dummy runs) asserting the table
   renders and p-value columns appear for each comparison.

### Task T35: Local-dev execution run

**Owner:** local-dev session.
**Guardrail:** cloud session MUST NOT run this task — it depends on
real `KIMI_API_KEY` + `NVIDIA_API_KEY`, real AI2-THOR, and real
wallclock. See `CLAUDE.md § cloud vs local development` + `AGENTS.md §7`.

1. **Pre-flight**: one-call live probe against each provider
   (`NvidiaProvider` is new this phase; `KimiCodingProvider` is already
   live-probed but confirm after any SDK bumps). Per
   `feedback_live_probe_gate.md`: do this before the overnight sweep.
2. **Kimi workhorse sweep**: from a local checkout,
   `python examples/view_experiment.py
   --variants baseline,map-v2,map-v2+chase --seeds 1,2,3,4,5
   --scenes FloorPlan201,FloorPlan205,FloorPlan210
   --games territory,coverage --model kimi-coding --agents 3
   --max-usd 15`. Expected runtime: ~90 games × ~4-6 min/game ≈
   7-9 hours (Kimi Coding's tail latency is ~40-60 s per VLM call —
   slower than GPT-mini). Run overnight. Budget: ~$10-15 on
   `kimi-for-coding` (cost varies with `reasoning_effort=low` reasoning
   token usage; the `--max-usd` gate catches tail cost blowups). The
   existing circuit breaker + per-seed isolation means any one run
   tripping `consecutive_failures_exceeded` logs `status=error` and the
   sweep continues.
3. On completion, run `scripts/analyze_view_experiment.py`, save the
   summary.
4. **NVIDIA confirm set**: pick the top two variants from step 3, run
   3 seeds × 1 scene (FloorPlan201) × 2 games × 2 variants = 12 runs
   on the NVIDIA model chosen in T29a. Budget: variable by model
   (Maverick vs. Nemotron Nano pricing diverges by ~10×); use
   `--max-usd 5` as a guardrail. Confirms the ordering holds across
   model families and on a non-Kimi transport.

### Task T36: Results writeup

**Files:** `docs/view-experiment-2026-04.md`, `README.md` (results tile),
sample GIFs under `docs/img/view-experiment/`.

1. One-line verdict per question (map-v2 helps / doesn't; chase-cam
   helps / doesn't).
2. Full results table copied from `summary.md`.
3. One GIF per variant on the same seed/scene for visual comparison.
4. Decision record: which variant(s) graduate to Phase 2.5 as the
   default, or `declined` with rationale if neither beats baseline.

### Task T37: Phase 2.4 retrospective + TODOS.md update

**Files:** `PLAN.md` (append retrospective), `TODOS.md`.

Shipped / dropped / lessons, same template as Phase 2.2. Promote the
winning variant to a Phase 2.5 "ship as default" item if applicable, or
close with `declined` on both fronts.

## Test Plan

The test diagram maps to the codepaths introduced here:

| New codepath | Test | Location |
|---|---|---|
| `NvidiaProvider` OpenAI-SDK wiring | mocked SDK, assert request shape, cost accounting, image-count support | `tests/test_nvidia_provider.py` |
| `NvidiaProvider` 3-image payload | mocked SDK, assert 3 `image_url` blocks in messages for variant C | `tests/test_nvidia_provider.py` |
| `create_provider("nvidia")` alias | assert returns `NvidiaProvider` instance | `tests/test_nvidia_provider.py` |
| `render_structured_map` arrow direction | pixel-quadrant assertion for 4 cardinal headings | `tests/test_visualizer_structured.py` |
| `render_structured_map` SOUL tint | `assert not np.array_equal` per T26 pattern | `tests/test_visualizer_structured.py` |
| `render_structured_map` unreachable render | dark-pixel assertion in known walled cells | `tests/test_visualizer_structured.py` |
| `add_chase_cam` pose math | mocked controller, verify position + rotation for 4 headings | `tests/test_engine_chase_cam.py` |
| `update_chase_cam` pose per step | mocked controller, assert step-over-step pose change matches agent move | `tests/test_engine_chase_cam.py` |
| `build_prompt_images` variant dispatch | assert image count per variant | `tests/test_views.py` |
| `view_experiment.py` harness smoke | MockProvider, 1x1x1x1, assert JSONL row shape | `tests/test_view_experiment.py` |
| `analyze_view_experiment.py` | synthetic JSONL, assert table + p-values render | `tests/test_analyze_view_experiment.py` |
| Chase-cam `Update` succeeds on live AI2-THOR | **local-dev** smoke, not CI | T31 step 4 |
| `NvidiaProvider` live probe | **local-dev** one-call probe per `feedback_live_probe_gate.md` | T29a step 4 |
| Kimi Coding end-to-end with 3-image prompt (variant C) | **local-dev** 1 seed × 1 scene × 1 game smoke | T35 step 1 |

The CI `lint-and-mock` job must pass across all new tests with
`MockProvider`. Kimi / NVIDIA / Anthropic / OpenAI paths stay mocked
per existing convention.

## Error & Rescue Registry

| Failure | Rescue |
|---|---|
| AI2-THOR rejects `UpdateThirdPartyCamera` mid-step (engine version drift) | T31 step 4: fall back to `delete + AddThirdPartyCamera` per step; local-dev probes this before CI. |
| Kimi Coding rate-limit / circuit-breaker trips mid-sweep | Existing `KimiCodingProvider` circuit opens, per-run `status=error` row, sweep continues. Re-run failed rows by filtering `results.jsonl`. |
| Variant C's 3rd image breaks Kimi `json_schema` path (empty `content`, all answer in `reasoning_content`) | `_extract_action_json` already scans both; if it still fails, T35 step 1 smoke gates before the full overnight sweep. If smoke fails, drop variant C from the Kimi sweep and run it only on NVIDIA. |
| `NvidiaProvider` is a new HTTP surface that passes in cloud but fails live | `feedback_live_probe_gate.md` rule: T29a step 4 live probe is a merge gate; we don't rely on mocked tests alone. |
| Chase-cam pose looks wrong in the GIF (agent not centred) | Log full pose per step during T31 smoke; iterate pose offsets before T35 run. |
| p-values look non-significant but variant C has visible qualitative improvements | Writeup reports both the stat result and the qualitative observation; we don't conflate absence-of-evidence with evidence-of-absence. |

## Failure Modes

- **AI2-THOR non-determinism leaks through seed control.** Even with
  `seed=N`, Unity-side physics has jitter. Mitigation: paired stats (we
  compare variant-B to variant-A on matched `(seed, scene, game)`), not
  absolute means.
- **Chase-cam obscures critical FPV info.** If the model learns to rely
  on the chase-cam and the FPV gets downweighted, variant C wins at
  navigation but loses at object-identification-heavy games. Not
  measurable this phase (games are navigation-dominant) but a flag to
  raise for Phase 3+.
- **Map-v2 is prettier but less informative than the photo.** If the
  structured grid strips out texture cues that helped the model
  disambiguate "chair vs. table", variant B can regress. Writeup
  examines blocking-event rate + qualitative GIF review.
- **Study under-powered at n=5 per (scene, game).** With 5 seeds × 3
  scenes = 15 paired samples per comparison, Wilcoxon can detect medium
  effects (d≈0.7) at α=0.05 with ~80% power. Small true effects would
  require n=30+ seeds. Writeup states the detectable effect size.

## Effort Estimate

| Task | Where | Estimate |
|---|---|---|
| T29a NvidiaProvider + mocked tests | cloud | 1-2 hrs |
| T29a NVIDIA live probe | local | 15 min |
| T30 visualizer + tests | cloud | 2-3 hrs |
| T31 chase-cam math + mocked tests | cloud | 1-2 hrs |
| T31 live chase-cam smoke | local | 30-60 min |
| T32 view-builder + wiring | cloud | 1-2 hrs |
| T33 harness + smoke test (incl. wallet cap) | cloud | 2 hrs |
| T34 analysis script + tests | cloud | 1-2 hrs |
| T35 Kimi sweep (90 games) + NVIDIA confirm (12 games) | local | ~9 hrs wallclock, ~30 min attended |
| T36 writeup + GIFs | local | 1 hr |
| T37 retro + TODOS | cloud or local | 30 min |

**Total engineering**: ~1.5-2 days cloud + ~1 local evening.
**Compute budget**: ~$10-15 (Kimi sweep) + ~$3-5 (NVIDIA confirm) = **~$15-20**,
capped at $20 hard via `--max-usd` wallet gates.

## What already exists (reuse, don't rebuild)

- `MultiAgentEngine.get_reachable_positions` — ground-truth occupancy
  set, already cached after first call.
- `MultiAgentEngine._setup_overhead_camera` pattern — T31's chase-cam
  registration follows the same `AddThirdPartyCamera` shape.
- `GameVisualizer.composite_frame` / `save_gif` / `save_png` — unchanged.
- `ReplayRecorder` — extend to tag each run with `variant`, no shape
  change.
- All VLM provider `get_action(images=..., state=...)` signatures —
  **unchanged**; they already accept variable-length `images: list`.
- `KimiCodingProvider` circuit-breaker + retry machinery — reused
  verbatim for the T35 workhorse sweep. Budget handles Kimi Coding's
  observed 429-burst behaviour without a new implementation.
- `OpenAIProvider` class shape — `NvidiaProvider` is a near-copy with
  `base_url` and `api_key` env-var swap; no new structured-output
  machinery (instructor + `_build_agent_action_model()` carry over).
- `CI lint-and-mock` job — picks up new tests automatically; no
  NVIDIA/Kimi live calls in CI.
- Territory + Coverage game modules — untouched logic; only the
  prompt-image assembly inside their example drivers changes.

## Worktree parallelization strategy

Sequential. T30-T32 all touch `roboclaws/core/`; T33 depends on T32;
T34 depends on T33's JSONL shape. No fan-out wins here. Keep on `main`.



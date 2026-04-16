<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/main-autoplan-restore-20260415-230209.md -->
# Phase 2: OpenClaw Integration — Completion Plan

## GSTACK REVIEW REPORT

**Review date:** 2026-04-16
**Reviewers:** CEO, Design, Eng (Codex + Claude), DX
**Outcome:** REJECTED — plan rewritten after user direction

**Key findings from the review:**
- The original plan treated Gateway readiness (`/readyz` timeout) as the main blocker, but the real issue is the transport contract: `OpenClawProvider` writes JPEGs to a host temp dir (`/tmp/openclaw-*`) while the CI Gateway container only mounts the skill directory, so `/tools/invoke` cannot read the frame paths even if `/readyz` is green.
- Task 2 proposed adding `tests/test_openclaw_skill.py`, but `tests/test_skill.py` already covers every case. More importantly, the failing `--backend openclaw` path uses `OpenClawProvider` directly and never instantiates `AI2THORNavigatorSkill`, so the proposed tests would not reduce real integration risk.
- The completion gate was invalid: `openclaw-smoke` is `continue-on-error`, Pages publishing is best-effort, Phase 1 was still unchecked, and coverage gameplay is known broken (#52).
- There was no proof that SOUL+MEMORY changes behavior: no per-agent SOUL assignment mechanism, and territory/coverage smoke tests reused the same `session_prefix` against the same Gateway container.

**User direction that led to this rewrite:**
- The project needs three layered demos in README: mock, AI2-THOR+VLM direct, AI2-THOR+OpenClaw.
- Elegant `--backend openclaw` switching is not required; a separate standalone demo script is acceptable.
- Build the demo locally first, then put it on CI.
- After the demo works, the next phase will connect AI2-THOR to long-running OpenClaw instances.

---

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
- Wiring `AI2THORNavigatorSkill` into the existing `--backend openclaw` path
- Per-agent SOUL preset assignment via the Gateway (deferred to long-running instance work)
- Fixing the coverage gameplay mismatch tracked in issue #52
- Phase 3 (Isaac Lab migration)

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

**Files:** `roboclaws/openclaw/bridge.py`, `.github/workflows/ci.yml`

1. Change `OpenClawProvider` to read `work_dir` from the `OPENCLAW_WORK_DIR` environment variable, falling back to a resolved `./.openclaw-tmp` path.
2. Update `examples/openclaw_demo.py` (Task 2) to rely on the default `work_dir` behavior.
3. Update CI `openclaw-smoke` Docker run command to mount `$PWD/.openclaw-tmp` to the identical absolute path inside the container so host and container see the same absolute frame paths.
4. Add `./.openclaw-tmp` to `.gitignore`.

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

### Task 3: Local OpenClaw quick-start guide

**New file:** `docs/openclaw-local.md`

Contents:
- Prerequisites: Docker, `KIMI_API_KEY` or Gateway already configured
- One-liner Docker run with the bind mount:
  ```bash
  docker run -d --name openclaw-gateway \
    -p 18789:18789 \
    -v "$PWD/skills/ai2thor-navigator:/home/node/.openclaw/workspace/skills/ai2thor-navigator:ro" \
    -v "$PWD/.openclaw-tmp:$PWD/.openclaw-tmp" \
    -e OPENCLAW_AUTH_MODE=token \
    -e OPENCLAW_AUTH_TOKEN=dev-token \
    -e OPENCLAW_ALLOWED_TOOLS=ai2thor-navigator \
    ghcr.io/openclaw/openclaw:latest
  ```
- How to run the demo: `python examples/openclaw_demo.py --steps 20`
- How to verify readiness: `curl http://localhost:18789/readyz`
- Troubleshooting: "Gateway cannot read frame paths" → check bind mount uses identical absolute paths on host and container

**Update `CLAUDE.md`:** Add cross-reference under "Cloud vs local development".

### Task 4: Replace `openclaw-smoke` CI job

**File:** `.github/workflows/ci.yml`

1. Replace the existing `openclaw-smoke` job with a simpler one that:
   - Starts the Gateway with the skill mount + `.openclaw-tmp` mount
   - Runs `python examples/openclaw_demo.py --agents 2 --steps 10 --output-dir output/openclaw/demo`
   - Runs `python -m roboclaws.core.reporter output/openclaw/demo`
   - Uploads `report-openclaw` artifact
2. Keep `continue-on-error: true` at the job level (OpenClaw Gateway availability is still optional for forks).
3. Update `publish-pages` to copy `openclaw-src/demo` to `site/openclaw/`.

### Task 5: Verify report publishing end-to-end

**Validation:**
- After local validation succeeds, merge to `main`
- Confirm `https://miaodx.github.io/roboclaws/openclaw/demo/report.html` loads
- Confirm the replay GIF is visible

### Task 6: Mark Phase 2 complete

**Update `README.md`:**
- Change `- [ ] **Phase 2**: OpenClaw integration` to `- [x] **Phase 2**: OpenClaw integration`
- Update the "OpenClaw + Kimi" section to reference `examples/openclaw_demo.py` and show the live demo artifact

## Test Plan

| Codepath | Test | Location |
|----------|------|----------|
| Bridge work_dir override | `test_provider_uses_env_work_dir` | `tests/test_bridge.py` (new) |
| Bridge HTTP errors | `test_bridge_step_*` | `tests/test_bridge.py` (existing) |
| Demo script syntax | `ruff check examples/openclaw_demo.py` | CI |
| Demo produces artifacts | Local run | `examples/openclaw_demo.py` |
| CI Gateway startup | `openclaw-smoke` job | `.github/workflows/ci.yml` |
| Report publishing | OpenClaw demo on GitHub Pages | `publish-pages` job |

## Error & Rescue Registry

| Error | Cause | Rescue |
|-------|-------|--------|
| `Gateway did not become ready within 60s` | Docker image path/env drift | Read logs, check bind mounts |
| `OpenClawUnavailable: Gateway unreachable` | Local Gateway not running | Point user to `docs/openclaw-local.md` |
| `Gateway cannot read frame paths` | Missing `.openclaw-tmp` bind mount or path mismatch | Check `-v "$PWD/.openclaw-tmp:$PWD/.openclaw-tmp"` |

## Failure Modes

| Scenario | Impact | Mitigation |
|----------|--------|------------|
| OpenClaw upstream changes image contract again | CI breaks | Pin to a specific image tag once stable |
| Railway secret missing | Optional job skips | Already handled with `continue-on-error` |
| Local developer lacks Docker | Can't run Gateway | Document that layers 1-2 work without it |

## Effort Estimate

- Task 1 (transport fix): 30 min
- Task 2 (demo script): 1–2 hours
- Task 3 (docs): 30 min
- Task 4 (CI update): 30 min
- Task 5 (publish verification): 15 min
- Task 6 (README update): 15 min

**Total: ~3–4 hours** (plus local validation time)

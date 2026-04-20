# Context notes

Running notes keyed by topic, preserved verbatim-in-spirit from the 15
DOC-classified sources. Each block attributes its source. No synthesis
decisions are encoded here — use `decisions.md` / `constraints.md` /
`requirements.md` for those. This file is the background layer for
downstream consumers (gsd-roadmapper and humans reading
`.planning/intel/`).

---

## Project positioning + differentiation

- source: docs/technical-design.md § Project Positioning; README.md;
  docs/research/04-openclaw-robotics-ecosystem.md § Multi-Agent Gap
- note: Roboclaws is positioned as a **thin, focused demo repository**
  validating "multiple OpenClaw/VLM agent instances simultaneously
  controlling multiple simulated robots for adversarial and cooperative
  tasks." Not a heavy framework — an experiment platform where giving a
  good model enough context lets it run autonomously.
- differentiation (as of April 2026): no one in the OpenClaw community has
  publicly demonstrated multiple OpenClaw instances simultaneously
  controlling multiple simulated robots in competition/cooperation.
  Roboclaws is **the first**.
- core hypothesis: if a VLM (Claude/GPT-4o/Kimi) can see the simulation
  camera feed, it can make reasonable navigation and strategic decisions
  to control a robot.

## Current shipped state (as of 2026-04-20)

- source: README.md § Roadmap; docs/retrospectives/phase-2.md,
  phase-2.1.md, phase-2.2.md, phase-2.3.md; TODOS.md
- shipped:
  - Phase 0 (research) — 4 research reports + real-model smoke validation
    report. Research directory `docs/research/` with index README.
  - Phase 2 (OpenClaw integration) — standalone `examples/openclaw_demo.py`
    on 2 agents × 20 steps, `scripts/openclaw-bootstrap.sh`, published at
    `miaodx.github.io/roboclaws/openclaw/demo/`.
  - Phase 2.1 (transport correction) — `/v1/chat/completions` +
    named-agent routing, inline base64 frames, no bind mount.
  - Phase 2.2 (long-running games) — per-agent SOUL distribution
    (aggressive/defensive/cooperative), two new CI jobs
    (`territory-openclaw-smoke`, `coverage-openclaw-smoke`), SOUL badges +
    tinted trails in visualizer, 3-tile Layer 3 in README, `make
    openclaw-territory` / `make openclaw-coverage` shortcuts.
  - Phase 2.3 (declined 2026-04-20) — digest pin evaluated and explicitly
    declined; the LOCKED decision lives in `decisions.md`.
- NOT shipped / not started:
  - Phase 1 formal checkbox — the README lists Phase 1 as "not done"
    even though the Layer 2 Kimi demos are live; this is a README
    presentation gap, not a missing capability.
  - Phase 2.4 (view experiment A/B) — drafted in `PLAN.md`, NOT executed.
  - Phase 2.5 (ship winning view variant as default) — gated on 2.4.
  - Phase 3 (Isaac Lab migration) — explicit long-term target.

## Three-layer live demo matrix

- source: README.md § Live Visualization; docs/openclaw-local.md;
  docs/retrospectives/phase-2.2.md § T23
- layers:
  - **Layer 1** (mock engine) — every push, every branch. Synthetic frames,
    no Unity, no API keys. Validates the visualization + reporting pipeline.
    Published at `miaodx.github.io/roboclaws/{territory,coverage}/`.
  - **Layer 2** (Kimi + real AI2-THOR) — push-to-main only. Real
    `FloorPlan201` rendered by Unity, FPV to Kimi. 100-step cap per game.
    Published at `miaodx.github.io/roboclaws/smoke/{territory,coverage}/`.
  - **Layer 3** (OpenClaw + Kimi) — push-to-main only. Long-running local
    Gateway with per-agent SOULs (aggressive/defensive/cooperative). Three
    tiles: nav, territory, coverage. Published at
    `miaodx.github.io/roboclaws/openclaw/{demo,territory,coverage}/`.
- layer-3-visual-differentiation: SOUL badges + tinted trails (red =
  aggressive, blue = defensive, green = cooperative, grey = default) are
  the only way to tell a Layer 3 GIF apart from Layer 2 at a glance;
  accepted via Phase 2.2 user challenge UC3.

## Phase 3 Isaac Lab target (long-term)

- source: docs/technical-design.md § Phase 3 Isaac Lab Migration;
  docs/research/01-openclaw-isaaclab-feasibility.md;
  docs/research/03-simulation-platforms-2026.md § Isaac Lab
- intent: Phase 3 migrates to Isaac Lab for humanoid (Unitree G1) and
  multi-embodiment navigation. Architecture is two-level: OpenClaw VLM
  planner (1-5 Hz) produces `(vx, vy, ωz)` commands consumed by a
  pre-trained RL locomotion policy (200 Hz). Bridge via ROSClaw or direct
  Python integration.
- Isaac Lab stack: AGILE (G1 velocity tracking), COMPASS (cross-embodiment
  navigation), GR00T N1.6 (Cosmos-Reason-2B VLM + diffusion transformer),
  PointNav example.
- why-not-now: no ready-made indoor scenes in Isaac Lab; building custom
  USD scenes is unrealistic for a 2-3 day PoC; GPU required; setup ~1-2
  weeks vs AI2-THOR's half-day.

## Simulation platform landscape (2026)

- source: docs/research/03-simulation-platforms-2026.md
- MolmoSpaces (Allen AI, Feb 2026): AI2-THOR's physics-accurate successor,
  230K+ indoor scenes, 130K+ objects, 42M+ annotated grasps.
  **Critical: no multi-agent.** Excluded.
- Habitat 3.0 / PARTNR: Most mature multi-agent human-robot platform.
  100K NL tasks, 60 houses. Sobering: humans 93% vs best LLMs 30%. Setup
  complexity exceeds 2-3 day PoC.
- ManiSkill3: 30,000+ FPS GPU-parallel, 2-3× less VRAM than Isaac Lab.
  Manipulation-focused. Useful for Phase 3 manipulation skills.
- Isaac Lab: deep humanoid stack (AGILE, COMPASS, GR00T) but no ready
  indoor scenes. Phase 3 target.

## OpenClaw ecosystem (April 2026)

- source: docs/research/04-openclaw-robotics-ecosystem.md
- signal: OpenClaw (356K+ stars) has spawned ≥6 active robotics
  integration repos in ~4 months. Multi-agent physical robot
  coordination remains a clear gap — roboclaws's differentiation.
- core repos:
  - **ROSClaw** (PlaiPin/rosclaw) — SF OpenClaw Hackathon winner (Feb 2026).
    arXiv:2603.26997. Model-agnostic ROS 2 executive layer via rosbridge
    WebSocket. 8 tools. Deployed on 3 platform types, 4 model backends.
    Up to 4.8× variation in out-of-policy action rates across models.
  - **DimensionalOS** (dimensionalOS/dimos) — 365 commits. "Agentic OS
    for physical space." Supports G1 (beta), Go2 (stable), B1, XArm,
    AgileX Piper, MAVLink/DJI drones. Signature feature: Spatial Agent
    Memory — persistent spatiotemporal model.
  - **RoClaw** (EvolvingAgentsLabs/RoClaw) — dual-brain: "Cortex"
    (OpenClaw) for planning, "Cerebellum" (Qwen3-VL-2B via Ollama) for
    real-time vision-motor via hex-bytecode. Permanent alpha.
  - **ClawBody** (tomrikert/clawbody) — Reachy Mini + MuJoCo sim, 25 Hz
    face tracking.
  - **OpenGo** (arXiv:2604.01708) — Unitree Go2, three-stage pipeline.
    No public code.
- NVIDIA angle: **NemoClaw** is a sandboxing layer, not a robotics
  integration. Jetson Thor running OpenClaw + Nemotron + vLLM announced
  National Robotics Week 2026.
- naming collision: Chinese researchers (Tsinghua/CAS) developed an
  unrelated "OpenClaw" — a 12-DOF open-source five-fingered robotic hand.
  Unrelated project; note for disambiguation.

## AI2-THOR multi-agent research details

- source: docs/research/02-ai2thor-multiagent-foundations.md
- iTHOR supports multi-agent natively; ProcTHOR has unresolved bugs
  (already captured in `constraints.md`).
- Limitations: no native simultaneous actions (turn-based only), no
  built-in inter-agent communication, no documented `agentCount` upper
  limit (rendering overhead scales linearly), sparse multi-agent docs,
  no deformable objects.
- SOUL.md + MEMORY.md are Gateway-provided per-agent files; OpenClaw
  supports multiple fully isolated agents in one Gateway process via
  deterministic routing bindings (channel, accountId, peer, guild/team
  ID); most-specific binding wins.

## Real-model smoke validation outcome (issue #50, 2026-04-14)

- source: docs/research/05-real-model-smoke-validation.md
- setup: post-#46 `main` branch real-model smoke test on Kimi + real
  AI2-THOR, commit `eb588409cb42ebfe56cb0759dcdadcd133582e41`, GH Actions
  run 24402133146.
- observed:
  - Territory: terminated at step 26 via `stale`, score 19/234. Kimi cost
    $0.016.
  - Coverage: terminated at step 100 via `max_steps`, score 21/234
    (8.97% covered). Kimi cost $0.084.
  - Combined Kimi spend: $0.100 (slightly over the "about 10 cents"
    target).
- findings:
  - Territory terminated before 100 steps and not via `max_steps` →
    passed the #50 acceptance criteria for territory.
  - Coverage never reached 95% and ran the full budget → **failed** the
    #50 acceptance criteria for coverage.
- likely cause: two design-vs-implementation mismatches in current
  `main`:
  1. `roboclaws/games/{territory,coverage}.py` call
     `provider.get_action(images=[], state=game_state)` — state-only,
     no images fed. Provider supports images; game loops don't.
  2. `roboclaws/games/coverage.py` uses **visited-cells** semantics,
     while `docs/technical-design.md` describes **field-of-view-based**
     coverage with a 95% target.
- follow-up: issue **#52** must decide ONE coherent story — either
  field-of-view + feed images, or visited-cells + update the docs and
  smoke expectations. Until resolved, README and technical-design
  overstate what the real-model smoke proves.
- → this is the WARNING entry in `INGEST-CONFLICTS.md`: the SPEC says
  field-of-view + images, the DOC reports visited-cells + no images.
  Synthesis preserves both; user must resolve before Phase 2.4 runs the
  coverage game again under an A/B experiment that assumes the
  acceptance criterion is clear.

## Development workflow topology

- source: CLAUDE.md; docs/contributing.md; AGENTS.md (referenced)
- cloud sessions (Claude Code web): research, small bounded changes, CI
  edits, doc edits, refactors guarded by `lint-and-mock`. No API keys,
  no Unity, no GPU.
- local sessions (workstation): every `local-dev` tagged task, every
  real-model validation, every multi-round debug loop. Real Kimi / real
  AI2-THOR / real Gateway.
- rule of thumb: if a PR's core claim depends on real hardware / real
  VLM behavior, first validation happens locally. CI keeps that proof
  live continuously, not starts it. In a cloud session that can't
  actually run the thing, say so explicitly in the PR — don't paper over
  it with "CI will tell us". File a `local-dev` issue.

## Gateway internals — what to spelunk when it breaks

- source: docs/openclaw-gateway-internals.md
- config: `/home/node/.openclaw/openclaw.json`. Gateway rewrites on first
  boot (adds auth token, seeds `controlUi.allowedOrigins`), backs up to
  `.bak`.
- models catalog: `/app/dist/models-config-B-YHRI3g.js` merges implicit
  per-plugin catalog with `cfg.models.providers.<id>` override from
  `openclaw.json` (default merge mode). Unknown IDs → `Unknown model:
  <id>` + `model_not_found` from `/v1/chat/completions`.
- provider plugins: `/app/dist/extensions/<plugin-id>/openclaw.plugin.json`.
  Two plugins roboclaws uses: `kimi-coding` → provider `kimi` (env
  `KIMI_API_KEY` or `KIMICODE_API_KEY`, base
  `https://api.kimi.com/coding/`, API surface `anthropic-messages`);
  `nvidia` → provider `nvidia` (env `NVIDIA_API_KEY`, base
  `https://integrate.api.nvidia.com/v1`, API surface
  `openai-completions`).
- model-id parser: `/app/dist/http-utils-*.js:resolveAgentIdFromModel`.
- useful spelunking:
  - dump dist file:
    `docker run --rm ghcr.io/openclaw/openclaw:2026.4.14 sh -lc 'cat
    /app/dist/<file>.js'`
  - find symbol:
    `docker run --rm ... sh -lc 'grep -rnE "<pattern>" /app/dist/'`
  - live inspect auth token:
    `docker exec openclaw-gateway sh -lc 'cat /home/node/.openclaw/openclaw.json'`
  - per-agent materialisation:
    `docker exec openclaw-gateway sh -lc 'ls -la
    /home/node/.openclaw/workspaces/agent-0/'`

## Multi-agent cost concerns (research)

- source: docs/research/01-openclaw-isaaclab-feasibility.md § Multi-Agent
  Cost; docs/technical-design.md § Cost Estimates
- claude-code embodied agent study (arXiv:2601.20334): $0.51-$5.60 per
  task. Five agents at 1 Hz generates substantial API traffic.
- recommendation: for multi-agent at scale, consider local Qwen-VL / VILA
  (zero marginal cost); for dev default to cheap models (GPT-4o-mini,
  Kimi coding-tier).

## Contributor onboarding + CI secrets

- source: docs/contributing.md
- CI jobs (up to three in the original cloud topology; later amended to
  5 per Phase 2.2):
  - `lint-and-mock` — every push + PR: ruff, format check, pytest,
    mock-engine HTML demo.
  - `real-model-smoke` — push to main only: 100-step Kimi + real
    AI2-THOR territory + coverage games.
  - `openclaw-railway-smoke` — push to main only (`continue-on-error`):
    3-step ping against a user-deployed Railway OpenClaw Gateway.
    Retired in Phase 2 Task 7 (bind-mount transport) and reconsidered
    after Phase 2.1's inline transport unblocked it.
  - `openclaw-smoke` (Phase 2) — push to main only (`continue-on-error`).
  - `territory-openclaw-smoke` / `coverage-openclaw-smoke` (Phase 2.2).
- required secret: `KIMI_API_KEY` (Moonshot/Kimi). Free coding-tier
  quota, ~$0.08 per 100-step 2-game run. Local verify via
  `python scripts/check_kimi_key.py`.

## Research index

- source: docs/research/README.md
- five reports:
  - 01 — openclaw-isaaclab-feasibility: technically feasible; deferred
    to Phase 3.
  - 02 — ai2thor-multiagent-foundations: native multi-agent works on
    iTHOR; ProcTHOR has bugs.
  - 03 — simulation-platforms-2026: MolmoSpaces lacks multi-agent;
    AI2-THOR fastest path.
  - 04 — openclaw-robotics-ecosystem: 6 active repos; multi-agent sim
    control is an open gap.
  - 05 — real-model-smoke-validation: territory OK, coverage
    underperforms, follow-up in #52.
- changelog: initial 4 reports added 2026-04-13; report 05 added
  2026-04-14 after the issue #50 real-model smoke validation.

## GitHub Issues roadmap (original Phase 0-2 plan)

- source: docs/issues-roadmap.md
- P0 Core issues (Issues 1-7): engine, VLM provider, visualizer,
  territory, coverage, replay, CI.
- P1 Example issues (Issues 8-10): single-agent explore, territory game,
  coverage game.
- P2 OpenClaw issues (Issues 11-13): skill wrapper, Gateway bridge,
  cloud relay (unblocked, deferred).
- Phase 2 shipping narrative note: as of the 2.1 transport correction,
  the shipping path is `examples/openclaw_demo.py` (pure nav, 2 agents
  × 20 steps) via `/v1/chat/completions` with named-agent routing.

## TODOS (empty as of 2026-04-20)

- source: TODOS.md
- shipped: Phase 2.2 (per-agent SOUL + long-running games).
- declined: Phase 2.3 (digest pin; decided 2026-04-20; see
  decisions.md's LOCKED ADR).
- **no active TODOs.** Next work should come from a new plan or issue —
  which is precisely why this ingest runs (bootstrap GSD for Phase 2.4
  execution and beyond).

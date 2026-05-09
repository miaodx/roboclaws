---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: active
stopped_at: Phase 17 MolmoSpaces real-world agent dogfood opened on 2026-05-09 via hybrid-phase-pipeline; ADR-0007 and source/GSD plans created for direct coding-agent dogfood on the ADR-0003 MCP surface.
last_updated: "2026-05-09T00:00:00+08:00"
last_activity: 2026-05-09
progress:
  total_phases: 12
  completed_phases: 12
  total_plans: 15
  completed_plans: 14
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 17 — molmospaces-realworld-agent-dogfood (active; direct coding-agent dogfood kit and clean-run checker for the ADR-0003 MCP surface)

## Current Position

Phase: 17 (molmospaces-realworld-agent-dogfood) — ACTIVE
Plan: 1 of 1 active — `17-01` implements ADR-0007 by adding a direct
coding-agent dogfood kit, real-world cleanup skill, and clean-run checker for
the ADR-0003 MCP surface.
Status: Planning slice opened. Next implementation step is to add the
real-world dogfood skill/server entrypoint, checker flags, focused tests,
recipes, and local evidence where feasible.
Last activity: 2026-05-09 - Created ADR-0007, source plan, and GSD Phase 17
plan for the direct coding-agent dogfood slice.

Progress: [##########] 100%
(Phase 08 satisfies the MolmoSpaces prompt-cleanup definition of done with a real upstream MuJoCo scene and subprocess backend. Phase 09 completes the visual FPV/same-room follow-up. Phase 10 completes the semantic-substep/report follow-up. Phase 11 completes the held-object carry visual follow-up. Phase 12 proves current-contract agent/OpenClaw tool viability. Phase 13 makes those agent bridge artifacts visually reviewable. Phase 14 implements the ADR-0003 public/private real-world-style cleanup boundary. Phase 15 closes the larger hidden Generated Mess Set lower-bound gap. Phase 16 exposes the ADR-0003 MCP agent surface. Phase 17 is opening direct coding-agent dogfood on that stricter surface. Remaining MolmoSpaces work after that is OpenClaw policy dogfood, advisory scoring/model checks, raw FPV-only perception, or planner-backed manipulation.)

## Performance Metrics

**Velocity:**

- Total plans completed: 30 (18 historical retrofit + 3 completed in Phase 02.4 + Phase 6/7/8/9/10/11/12/13/14 MolmoSpaces plans)
- Average duration: n/a (ingested from retrospectives, not GSD-tracked)
- Total execution time: n/a (pre-GSD work)

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1. Core simulation + games | 6 | n/a | n/a |
| 1.5. CI + dev topology | 2 | n/a | n/a |
| 2. OpenClaw bridge (original) | 3 | n/a | n/a |
| 2.1. Transport correction | 3 | n/a | n/a |
| 2.2. Long-running OpenClaw games | 3 | n/a | n/a |
| 2.3. Digest pin (declined) | 1 | n/a | n/a |
| 2.4. View-experiment A/B | 3 | n/a | n/a |
| 6. MolmoSpaces cleanup pilot | 4 | n/a | n/a |
| 7. MolmoSpaces prompt cleanup | 2 | n/a | n/a |
| 8. MolmoSpaces real subprocess cleanup | 1 | ~2h | ~2h |
| 9. MolmoSpaces FPV room plausibility | 1 | ~2h | ~2h |
| 10. MolmoSpaces semantic substeps | 1 | ~2h | ~2h |
| 11. MolmoSpaces held-object carry visuals | 1 | ~1h | ~1h |
| 12. MolmoSpaces current-contract agent bridge | 1 | ~3h | ~3h |
| 13. MolmoSpaces agent bridge visual results | 1 | ~3h | ~3h |
| 14. MolmoSpaces real-world cleanup harness | 1 | ~2h | ~2h |

**Recent Trend:**

- Last 3 shipped phases: 12, 13, 14
- Trend: MolmoSpaces cleanup path now moved from real upstream MolmoSpaces/MuJoCo subprocess proof to reviewable semantic object-level cleanup evidence, carried-object visual consistency, direct agent/OpenClaw tool viability, visual agent bridge reports, and ADR-0003 public/private cleanup boundaries.

*Updated after each plan completion — prior entries are one-time ingest backfill.*
| Phase 02.6 P02 | 25min | 3 tasks | 2 files |
| Phase 02.6 P03 | 5min  | 1 task  | 1 file  |
| Phase 02.6 P04 | 7min  | 3 tasks | 2 files |
| Phase 02.6 P05 | 7min  | 1 task  | 3 files (2 deleted, 1 edited) |
| Phase 02.6 P06 | 32min | 6 tasks | 2 files |
| Phase 02.6 P07 | 20min | 3 tasks | 3 files |
| Phase 08 P01 | ~2h | 4 tasks | 18 files |
| Phase 09 P01 | ~2h | 4 tasks | 10 files |
| Phase 10 P01 | ~2h | 4 tasks | 18 files |
| Phase 11 P01 | ~1h | 4 tasks | 7 files |
| Phase 12 P01 | ~3h | 4 tasks | 15 files |
| Phase 13 P01 | ~3h | 4 tasks | 14 files |
| Phase 14 P01 | ~2h | 4 tasks | 15 files |
| Phase 15 P01 | ~2h | 4 tasks | 8 files |
| Phase 16 P01 | ~3h | 6 tasks | 10 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 16 planning (2026-05-09):** ADR-0006 adds a stricter real-world Molmo
  cleanup MCP surface backed by `RealWorldCleanupContract`. It should expose
  Metric Map, Fixture Hints, waypoint observation, Observed Object Handles, and
  semantic cleanup tools, but not current-contract `scene_objects`. The first
  slice uses a deterministic MCP smoke agent; direct Codex/Claude/OpenClaw
  dogfood against the stricter surface follows once this MCP contract is stable.
- **Phase 16 completion (2026-05-09):** The ADR-0003 cleanup contract now has a
  separate `molmo_cleanup_realworld` MCP server/factory. Its public tool surface
  excludes `scene_objects`, rejects that tool explicitly, and writes
  agent-driven real-world artifacts with the shared Agent View, Private
  Evaluation, Score, Cleanup Trace, and Robot View Timeline report underlay.
  Real seed 1 evidence restored 8/10 hidden generated objects, swept all public
  waypoints, recorded no disturbance, and passed the checker with
  `policy=realworld_contract_smoke_agent`. Direct Codex/Claude/OpenClaw dogfood
  against this stricter contract remains a follow-up, not a Phase 16 claim.
- **Phase 17 planning (2026-05-09):** ADR-0007 splits direct coding-agent
  dogfood from the Phase 16 deterministic MCP smoke. The phase should add a
  real-world cleanup skill, direct server entrypoint, checker assertions, and
  focused recipes for clean ADR-0003 agent artifacts before attempting OpenClaw
  Gateway dogfood.
- **Phase 15 planning (2026-05-09):** ADR-0005 makes the Generated Mess Set size
  explicit and configurable. The ADR-0003 real-world harness should use 10
  hidden generated objects as the default v1 evidence shape, while retaining the
  five-object synthetic fixture for fast tests and current-contract
  compatibility. The Scorer must evaluate the whole generated set and derive the
  success threshold from the actual generated count.
- **Phase 15 completion (2026-05-09):** The Generated Mess Set selector now
  lives in `roboclaws/molmo_cleanup/generated_mess.py` and is reused by the real
  MolmoSpaces subprocess worker. `just harness::molmo-realworld-cleanup`
  requests 10 hidden generated objects by default, and
  `scripts/check_molmo_realworld_cleanup_result.py` can enforce that lower
  bound. Real seed 1 evidence produced `generated_mess_count=10`, 10 semantic
  substep rows, 44 robot timeline steps, 176 PNGs, and `cleanup_status=success`.
- **Phase 14 completion (2026-05-09):** ADR-0003 is now implemented as a
  separate real-world-style cleanup harness. The Cleanup Agent sees only
  `metric_map`, room-level `fixture_hints`, waypoint `observe` results, and
  `observed_*` handles; private Generated Mess Set, target count, acceptable
  destination sets, and exact scorer truth are written only to post-run
  `private_evaluation` artifacts/report sections. The deterministic sweep
  baseline passed the real MolmoSpaces subprocess gate for seeds 1, 2, and 3
  with exact `mess_restoration_rate=0.8`, full sweep coverage, and no
  disturbance. A follow-up within the same phase added RBY1M visual report
  parity: current-contract bridge reports and ADR-0003 harness reports now
  share `roboclaws/molmo_cleanup/semantic_timeline.py` as the underlying
  semantic timeline/report model. Seed 1 now produces a `Robot View Timeline`
  with 23 focused robot steps and 92 FPV/chase/map/verification PNGs using
  `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? ->
  place/place_inside` object phases while keeping Agent View and Private
  Evaluation separate. The first slice keeps the existing generated mess count
  of 5; expanding to 10-20 objects is a follow-up.
- **Phase 12 completion (2026-05-08):** The Molmo cleanup current contract now
  has a separate FastMCP bridge for external agents. Codex and Claude Code both
  completed clean direct MCP runs (`success`, 5/5 restored, no stale references)
  using `skills/molmo-cleanup/SKILL.md`. OpenClaw Gateway also restored 5/5 and
  terminated cleanly, but made one recovered stale-reference attempt by using a
  sofa/simulator-style id as an object id; the skill and observe instruction now
  explicitly say object IDs must come only from `scene_objects.objects[*]` and
  receptacles are targets only. This phase remains `contract=current_contract`
  and does not satisfy ADR-0003 because global `scene_objects` is still exposed.
- **Phase 13 completion (2026-05-08):** Agent bridge reports now have the same
  RBY1M robot-view timeline and semantic mid-phase visual rows as the Molmo
  robot visual harness. Visual dogfood passed for Codex, Claude Code, and
  OpenClaw, but the scores were 4/5, 4/5, and 3/5 because public semantic
  choices can miss private scorer truth. This is expected current-contract
  behavior, not ADR-0003 realism.
- **Phase 08 completion (2026-05-07):** The MolmoSpaces cleanup definition of
  done now requires and has evidence for `backend=molmospaces_subprocess`, an
  isolated Python 3.11 runtime, upstream `procthor-10k-val` scene loading, real
  metadata/object-state readback, public-only prompt planning for
  `帮我整理这个房间`, scorer-only private manifest use, and the required
  `before.png` / `after.png` / `trace.jsonl` / `run_result.json` /
  `report.html` artifacts. Provenance remains `api_semantic` because the worker
  mutates real MuJoCo free-joint `qpos`; reserve `real` for future
  RBY1M/Franka planner-backed pick/place.
- **Phase 09 completion (2026-05-08):** RBY1M FPV orientation now uses
  target-facing base yaw for horizontal direction and a separately recorded
  target-framing head pitch for camera readability. Same-room stand-off
  selection is checked against MuJoCo room outlines, and the visual gate now
  requires positive FPV target pixels on focused manipulation steps.
- **Phase 10 completion (2026-05-08):** Cleanup execution is now recorded as
  object-level semantic substeps. Fridge cleanup opens the real articulated
  fridge joint, places the apple with `place_inside`, and records final
  containment/readback as `location_relation=inside`. Robot timeline rows now
  include semantic phase badges, and non-focused context rows no longer show a
  misleading Verification panel. `primitive_provenance=api_semantic` remains
  correct because these commands mutate real MuJoCo state but are not
  planner-backed RBY1M/Franka pick/place.
- **Phase 11 completion (2026-05-08):** Held objects now visually travel with
  RBY1M during semantic cleanup navigation. `navigate_to_receptacle` and
  fridge `open_receptacle` update the held object's real MuJoCo free-joint qpos
  to the robot-relative held pose, and the visual checker requires positive FPV
  object pixels plus robot-relative position evidence on carried navigation
  rows. This remains `api_semantic`, not planner-backed robot manipulation.
- **Phase 02.4 planning (2026-04-21):** GSD decomposition starts with `examples/openclaw_demo.py` (single-agent push-model navigation) before territory/coverage. Phase scope remains the full A/B study; only the execution order changed.
- **Phase 02.4 execution checkpoint (2026-04-21):** Plans `02.4-01` through `02.4-03` are complete and the cloud-safe slice of `02.4-04` (`scripts/analyze_view_experiment.py` plus synthetic-data coverage) is implemented. The actual Kimi/NVIDIA sweep and `docs/view-experiment-2026-04.md` remain local-dev only and are tracked in issue #70.
- **Cross-phase local follow-up (2026-04-22):** The Phase 02.4 view family is now shared with the shipped Phase 02.6 autonomous MCP path. `examples/openclaw_nav_autonomous.py --views map-v2+chase` completed locally with real Kimi + AI2-THOR (`done`, 2 observes + 1 move + 1 done in the summary-fix smoke), and the MCP server now fails fast on bind collisions instead of burning the full wall-clock budget behind a dead listener.
- **Phase 02.4 decision lock (2026-04-24):** The old `baseline` / `map-v2` / `map-v2+chase` A/B study is now historical only. Runtime support was standardized on `map-v2+chase`, user-facing `--views` flags were removed from the main examples, and `02.4-04` was superseded rather than executed.
- **Phase 5 completion (2026-04-23):** The codebase-simplification phase closed all 9 plans in a single verified worktree batch. Eighteen target files finished at or below their original line caps (`9,378` → `9,175`, net `-203`), targeted example/API guards stayed green, and the final repo-wide `pytest`, `ruff check`, and `ruff format --check` gates passed after a small pre-existing lint cleanup in unrelated scripts/tests.
- **Phase 02.7 planning completion (2026-04-22):** The queued autonomous follow-up now has a full GSD planning bundle under `.planning/phases/02.7-openclaw-intermediate-message-capture/`: four executable plan files plus `02.7-RESEARCH.md` and `02.7-VALIDATION.md`. Scope remains unchanged: compare real Gateway streaming vs terminal-body capture, persist transcript artifacts additively, surface them in `report.html`, and validate the shipped path locally. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 5 planning completion (2026-04-23):** Iterative codebase simplification phase now has a full GSD planning bundle under `.planning/phases/05-iterative-codebase-simplification/`: nine executable plan files covering all major source files (visualizer.py, mcp_server.py, reporter.py, transport.py, game modules, provider modules, supporting modules, and example scripts). All plans wave 1, independent, atomic commits, pytest + ruff gate per commit. Verification passed. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 4 planning completion (2026-04-23):** The queued refactor-safety follow-up now has a full GSD planning bundle under `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/`: four executable plan files plus `04-RESEARCH.md` and `04-VALIDATION.md`. Scope is locked to tiny contract fixtures, a thin capture harness, a separate baseline-vs-candidate analyzer, and a local baseline-refresh workflow. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 4 execution completion (2026-04-23):** The refactor-regression harness phase is now implemented. Added `roboclaws/regression.py`, capture/analyze CLIs, operator docs, contract/analyzer tests, and the first real local evidence bundle in `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/04-LOCAL-PROBE-RESULTS.md`. Live probe feedback tightened the harness in two places: `openclaw-autonomous` now treats `terminated_by=error` / zero-observe runs as capture failures, and `explore-vlm` analyzer thresholds now use ratio-or-absolute slack (`usd` +$0.01, `wallclock` +120s) so small same-commit Kimi workflow proofs do not fail on cold-start variance alone. This does **not** change the active phase; Phase 02.4 remains the current blocked milestone work.
- **Phase 02.6 plan 01 (2026-04-21)**: MCP server default bind is `127.0.0.1` (localhost-only) per threat model T-02.6-01; Gateway container reaches via `host.docker.internal` → host-gateway → loopback. Bind is NOT env-configurable — only via explicit argument.
- **Phase 02.6 plan 01 (2026-04-21)**: Trace schema additive-only rule: `tests/fixtures/trace_schema_reference.json` freezes sim_server.py key-sets at phase entry; MCP server emits a SUPERSET. `snapshot_metrics` is the one exception — EQUALITY checked because `run_result_json["sim_server_metrics"]` consumers depend on exact names.
- **Phase 02.6 plan 01 (2026-04-21)**: `mcp[cli]>=1.27` in `dev` + new `openclaw` extra; NOT in top-level `[project].dependencies` (core library stays installable without the Gateway path, mirroring ai2thor).
- **Phase 2.3 (LOCKED, 2026-04-20)**: Decline digest-pinning the Gateway image; keep `ghcr.io/openclaw/openclaw:2026.4.14`. One-click rollback digest recorded in ADR.
- **Phase 2.2 (2026-04-16)**: Ship 3 symmetric Layer 3 tiles (nav / territory / coverage); reject UC1 Persona Showdown framing.
- **Phase 2.2 (2026-04-16)**: "Long-running" = within a single game run; no cross-run MEMORY persistence.
- **Phase 2.1**: Gateway transport is `POST /v1/chat/completions` with `model="openclaw/<agentId>"`; not `/tools/invoke`.
- **Phase 2.1**: Inline base64 image transport; no bind mount.
- Phase 02.6 plan 02 (2026-04-21): ROBOCLAWS_TOOL_PROFILE validated against {minimal, coding, messaging} with hard die 1 on typos (T-02.6-06). SIM_SERVER_URL kept as translate-and-warn fallback one wave; plan 05 removes it. main fallback agent intentionally left without tools.profile (Gateway insists on it existing but never routes). Test pattern: line-based heredoc extraction + base-path replacement exec's python3 against tmp config root (docker-free regression coverage).
- **Phase 02.6 plan 03 (2026-04-21)**: SKILL.md budget is body-only (post second-`---`, non-blank lines), measured via awk extractor not `wc -l`. Final: 10 body lines / 25 total (down from 245, ~90% reduction). Don't enumerate forbidden tools in SKILL.md — profile: minimal removes them from the agent surface, so documenting "don't use exec" both wastes tokens AND risks re-teaching the behavior.
- **Phase 02.6 plan 03 (2026-04-21)**: Prefixed tool-name convention (`roboclaws__observe` etc., double-underscore separator per spike F-2) is load-bearing in SKILL.md — the agent reads exactly the name the tool registry exposes, no translation. Dropped the optional SOULs pointer because SOULs load into `SOUL.md` via bootstrap, not via skill-file reference.
- **Phase 02.6 plan 04 (2026-04-21)**: Kickoff prompt delegates loop mechanics to SKILL.md rather than duplicating tool recipes — shrunk from 38 source lines / 13 non-empty to 7 source lines / 5 non-empty. No "if X fails, try Y" fallback language (that pattern is what let Kimi drift back to `exec` under Phase 2.5). `run_result_json["sim_server_metrics"]` JSON key kept verbatim across the HTTP -> MCP swap — the 8-key snapshot_metrics contract is stable so the JSON shape doesn't change; inline comment at emission site documents the name-vs-backing mismatch. `env.setdefault("ROBOCLAWS_MCP_URL", ...)` pattern (not `env[...]=...`) honors operator-supplied URLs; dual-layer regression coverage — bootstrap side (plan 02 Task 3) + example side (plan 04 Task 3) — guards threat T-02.6-23.
- **Phase 02.6 plan 05 (2026-04-21)**: Pure-deletion plan pattern works when upstream plans fully migrate callers — a recursive grep across `roboclaws/ examples/ tests/ scripts/` returned zero live importers before the `git rm`, and full pytest (475 passed, 1 skipped) held post-delete. Kept historical doc-comments referencing `sim_server.py` in mcp_server.py docstring + example + fixtures — the dependency-scan pattern scoped to `from/import sim_server|openclaw\.sim_server|SimHTTPServer` deliberately excludes prose refs, because the `sim_server_metrics` JSON key + trace-schema source-pointer metadata are frozen contracts that document schema continuity. Kept the plan-02 `SIM_SERVER_URL→ROBOCLAWS_MCP_URL` deprecation-warning fallback in the bootstrap (graceful-degrade for stale shells); only the dead `-e SIM_SERVER_URL=...` docker-run arg was removed.
- Phase 02.6 plan 06 (2026-04-21): Probe 1 uncovered plan 01 T-02.6-01 assumption error — 127.0.0.1 MCP bind unreachable from Gateway container on Linux kernel 6.17 + Docker 29.2.1; fix was host='0.0.0.0' at the example call site (not a default change in mcp_server.py), preserving threat-model intent for other callers.
- Phase 02.6 plan 06 (2026-04-21): Probe 6 prompt-token ratio = 0.568 against live Gateway image 2026.4.14 — not the 0.408 from the spike. The ROADMAP SC#4 threshold of <=0.50 cannot be honored without action; Task 8 operator to choose (revise threshold | trim MCP | image drift investigation).
- Phase 02.6 plan 07 (2026-04-21): Docs-update plan pattern — retro focuses on surprising-only lessons (host='0.0.0.0' Linux gotcha + coding-profile 26% drift) rather than recapping shipped facts. Shipped facts belong in per-plan SUMMARYs. Three-way doc cross-linking (retro ↔ operator ↔ internals) with no prose duplication. Orchestrator added retrospective as third deliverable beyond the plan's 2 tasks; committed under the same docs(phase-02.6-07) prefix.

### Roadmap Evolution

- Phase 2.4 closed (2026-04-24): **Better Views** now has a locked product decision. The repo keeps only the `map-v2+chase` runtime path; the old multi-variant experiment is retained as historical context plus analysis tooling, not as an active gate.
- Phase 12 completed (2026-05-08): **MolmoSpaces current-contract agent
  bridge** — current semantic cleanup contract exposed through FastMCP and
  validated with Codex, Claude Code, and OpenClaw Gateway against the same 5/5
  public rule-based baseline.
- Phase 13 completed (2026-05-08): **MolmoSpaces agent bridge visual results**
  — current-contract agent bridge reports now include robot-view images and
  semantic mid-phase rows comparable to the visual harness; public-agent score
  gaps are documented as private-target limitations.
- Phase 14 completed (2026-05-09): **MolmoSpaces real-world cleanup harness**
  — ADR-0003 public/private contract implemented with metric-map, room fixture
  hints, observed handles, deterministic private scoring, and three-seed real
  MolmoSpaces subprocess evidence.
- Phase 15 completed (2026-05-09): **MolmoSpaces Generated Mess Set scale** —
  ADR-0005 configurable hidden Generated Mess Set size with a real 10-object
  MolmoSpaces/RBY1M evidence run.
- Phase 16 completed (2026-05-09): **MolmoSpaces real-world agent MCP** —
  ADR-0006 exposes the ADR-0003 public cleanup contract through MCP without the
  current-contract `scene_objects` shortcut.
- Phase 5 completed (2026-04-23): **Iterative codebase simplification** — all 9 plans closed, 18 target files simplified, net `-203` targeted lines, and final repo-wide `pytest` + `ruff` gates passed. Per-plan summaries live under `.planning/phases/05-iterative-codebase-simplification/`.
- Phase 4 added (2026-04-23): **Refactor regression harnesses for VLM, territory/coverage, and OpenClaw**. The phase was added via the `phase.add` workflow, then tightened for this repo: root `PLAN.md` is explicitly kept as a source context file, `04-CONTEXT.md` seeds the planning bundle, and the intended harness shape follows existing repo patterns (`results.jsonl` runner + separate analyzer + small fixture-backed contract tests).

### Pending Todos

[From .planning/todos/pending/ — none yet. Root `TODOS.md` is also empty by design as of 2026-04-20; all future TODOs originate from this roadmap.]

None yet.

### Quick Tasks Completed

| # | Description | Date | Commit | Directory |
|---|-------------|------|--------|-----------|
| 260423-q71 | codebase simplification: extract game helpers, dedup example utilities, split vlm.py providers, split bridge.py transport, refactor reporter build_run_section | 2026-04-23 | 9e1fe35 | [260423-q71-codebase-simplification-extract-game-hel](./quick/260423-q71-codebase-simplification-extract-game-hel/) |

### Blockers/Concerns

- No active blocker for the MolmoSpaces cleanup definition of done. Phase 08
  completed the real-scene subprocess proof, Phase 09 completed the
  target-facing FPV / same-room visual-review follow-up, Phase 10 completed
  the semantic substep / fridge containment / report-row follow-up, Phase 11
  completed the held-object carry visual follow-up, Phase 12 completed
  current-contract Codex/Claude/OpenClaw tool-viability proof, Phase 13
  completed visual agent bridge reporting, and Phase 14 completed ADR-0003
  public/private cleanup separation. Phase 15 completed larger hidden generated
  mess sets, and Phase 16 completed the ADR-0003 MCP surface. Model-agent policy
  evaluation on the ADR-0003 MCP contract, advisory scoring/model checks, raw
  FPV-only perception, and planner-backed manipulation remain separate
  follow-ups.
- **Known Phase 02.6 artifact gap (now planned as Phase 02.7):** Autonomous artifacts currently show tool traffic plus the final assistant message, but not the intermediate assistant transcript. This is a queued follow-up, not a blocker for the already-shipped 02.6 MCP loop.
- **Environment split is real:** this local session had AI2-THOR available,
  VLM keys in `.env`, and the isolated Python 3.11 MolmoSpaces runtime. Phase
  08 makes claims only about real MolmoSpaces/MuJoCo scene loading and
  semantic state mutation, not about real VLM/OpenClaw behavior.

> **Resolved 2026-04-20:** The two WARNINGs initially carried from
> `.planning/INGEST-CONFLICTS.md` (image-payload contract, coverage
> semantics) were verified stale — both were already shipped in commit
> `ddfb523` on 2026-04-15, and issue #52 was closed the same day. The
> stale-ingest claim came from a dated validation report
> (`docs/research/05-real-model-smoke-validation.md`, 2026-04-14) that
> the synthesizer treated as current state. See
> `.planning/INGEST-CONFLICTS.md` "UPDATE 2026-04-20" header for full
> evidence and the `feedback_verify_ingest_claims` memory for the
> lesson.

- **Resolved 2026-04-21:** Phase 02.6 plan 06 Probe 6 threshold (ratio 0.568 > 0.50) resolved by revising ROADMAP SC#4 from ≤0.50 to ≤0.60 to match live Gateway reality. Live probe's 43% reduction is a real, material win; spike's 0.408 is not reproducible because Gateway's coding profile shrank 26% between the spike and the probe on the same image tag. Full narrative in `docs/retrospectives/phase-2.6.md` § "The two surprises worth remembering" #2.

## Deferred Items

Items acknowledged and carried forward from the new-mode ingest:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Ops | Gateway image digest pin (`sha256:7ea07…a594ed`) | LOCKED DECLINED | 2026-04-20 |
| Architecture | Phase 3 Isaac Lab migration (humanoid + multi-embodiment nav) | Deferred indefinitely (requires GPU + USD scenes) | 2026-04-20 |
| Framing | Phase 2.2 UC1 Persona Showdown / UC2 cross-run MEMORY | Rejected at final gate | 2026-04-16 |

## Session Continuity

Last session: 2026-05-09T00:00:00+08:00
Stopped at: Phase 16 MolmoSpaces real-world agent MCP planning is complete;
implementation is next.
Latest planning artifacts are
`docs/adr/0006-expose-adr-0003-cleanup-contract-through-mcp.md`,
`docs/plans/molmospaces-realworld-agent-mcp.md`, and
`.planning/phases/16-molmospaces-realworld-agent-mcp/16-01-realworld-agent-mcp-PLAN.md`.
Resume file: .planning/phases/16-molmospaces-realworld-agent-mcp/16-01-realworld-agent-mcp-PLAN.md

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Active Phase:** 16 (molmospaces-realworld-agent-mcp) — active;
implementation should expose the ADR-0003 public contract through MCP before
running direct coding-agent/OpenClaw policy dogfood or planner-backed
RBY1M/Franka manipulation — 2026-05-09T00:00:00+08:00

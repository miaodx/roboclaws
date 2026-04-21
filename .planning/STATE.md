---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: planning
stopped_at: Phase 02.4 planned into .planning/phases/02.4-view-experiment-ab; next step is 02.4-01 openclaw-demo-view-variants
last_updated: "2026-04-21T12:59:13Z"
last_activity: 2026-04-21
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 4
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-21)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 02.4 — view-experiment-ab

## Current Position

Phase: 02.4 (view-experiment-ab) — PLANNED
Plan: 0 of 4 — READY TO EXECUTE (`02.4-01` is the single-agent OpenClaw slice).
Status: Phase 02.4 was migrated from the root `PLAN.md` draft into `.planning/phases/02.4-view-experiment-ab/` on 2026-04-21. Phase 02.6 remains shipped; the next execution step is `02.4-01`.
Last activity: 2026-04-21

Progress: [----------] 0%
(Phase 02.4 now has a 4-plan GSD breakdown; the first plan intentionally lands `examples/openclaw_demo.py` before territory/coverage. Phase 02.6 shipped on 2026-04-21 and remains the latest completed phase.)

## Performance Metrics

**Velocity:**

- Total plans completed: 18 (historical retrofit from shipped phases)
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

**Recent Trend:**

- Last 3 shipped phases: 2.2, 2.3 (declined), 2.6
- Trend: Stable (Phase 2.6 shipped cleanly on 2026-04-21; focus now shifts back to the unexecuted 2.4 views track)

*Updated after each plan completion — prior entries are one-time ingest backfill.*
| Phase 02.6 P02 | 25min | 3 tasks | 2 files |
| Phase 02.6 P03 | 5min  | 1 task  | 1 file  |
| Phase 02.6 P04 | 7min  | 3 tasks | 2 files |
| Phase 02.6 P05 | 7min  | 1 task  | 3 files (2 deleted, 1 edited) |
| Phase 02.6 P06 | 32min | 6 tasks | 2 files |
| Phase 02.6 P07 | 20min | 3 tasks | 3 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 02.4 planning (2026-04-21):** GSD decomposition starts with `examples/openclaw_demo.py` (single-agent push-model navigation) before territory/coverage. Phase scope remains the full A/B study; only the execution order changed.
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

### Pending Todos

[From .planning/todos/pending/ — none yet. Root `TODOS.md` is also empty by design as of 2026-04-20; all future TODOs originate from this roadmap.]

None yet.

### Blockers/Concerns

currently.

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

Last session: 2026-04-21T12:59:13Z
Stopped at: Phase 02.4 planned into .planning/phases/02.4-view-experiment-ab; next step is 02.4-01 openclaw-demo-view-variants
Resume file: None

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Planned Phase:** 02.4 (view-experiment-ab) — 4 plans — 2026-04-21T12:59:13Z

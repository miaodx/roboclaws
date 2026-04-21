---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: executing
stopped_at: Phase 02.6 plan 05 (delete-sim-server) complete. Wave 3 kicked off; plans 06-07 pending.
last_updated: "2026-04-21T10:43:11Z"
last_activity: 2026-04-21 -- Phase 02.6 plan 05 (delete-sim-server) complete
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 7
  completed_plans: 5
  percent: 71
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 02.6 — openclaw-mcp-tools-integration

## Current Position

Phase: 02.6 (openclaw-mcp-tools-integration) — EXECUTING
Plan: 5 of 7 — COMPLETE (delete-sim-server). Waves 1-2 done; Wave 3 kicked off (5/7 total).
Status: Executing Phase 02.6; plans 01-05 complete, awaiting orchestrator to dispatch plans 06-07 (live-probe-gate + docs-update)
Last activity: 2026-04-21 -- Phase 02.6 plan 05 (delete-sim-server) complete

Progress: [█████████████████░░░] 91%
(21 of 23 historical+active plans complete; Phase 2.4 + remaining 02.6 plans (06-07) pending; Phase 3 deferred and excluded from the denominator)

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

- Last 3 shipped phases: 2.1, 2.2, 2.3 (declined)
- Trend: Stable (Phase 2.2 shipped clean 2026-04-16, Phase 2.3 cleanly declined 2026-04-20)

*Updated after each plan completion — prior entries are one-time ingest backfill.*
| Phase 02.6 P02 | 25min | 3 tasks | 2 files |
| Phase 02.6 P03 | 5min  | 1 task  | 1 file  |
| Phase 02.6 P04 | 7min  | 3 tasks | 2 files |
| Phase 02.6 P05 | 7min  | 1 task  | 3 files (2 deleted, 1 edited) |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

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

### Pending Todos

[From .planning/todos/pending/ — none yet. Root `TODOS.md` is also empty by design as of 2026-04-20; all future TODOs originate from this roadmap.]

None yet.

### Blockers/Concerns

None currently.

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

## Deferred Items

Items acknowledged and carried forward from the new-mode ingest:

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| Ops | Gateway image digest pin (`sha256:7ea07…a594ed`) | LOCKED DECLINED | 2026-04-20 |
| Architecture | Phase 3 Isaac Lab migration (humanoid + multi-embodiment nav) | Deferred indefinitely (requires GPU + USD scenes) | 2026-04-20 |
| Framing | Phase 2.2 UC1 Persona Showdown / UC2 cross-run MEMORY | Rejected at final gate | 2026-04-16 |

## Session Continuity

Last session: 2026-04-21T10:43:11Z
Stopped at: Phase 02.6 plan 05 (delete-sim-server) complete. Plans 01-05 done; plans 06-07 (live-probe-gate + docs-update) pending orchestrator dispatch.
Resume file: None

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Planned Phase:** 02.6 (openclaw-mcp-tools-integration) — 7 plans — 2026-04-21T09:00:34.851Z

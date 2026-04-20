---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: Better Views
status: planning
stopped_at: "Roadmap + state + requirements bootstrapped from `.planning/intel/`; both ingest WARNINGs verified stale and marked RESOLVED. Next action: `/gsd-plan-phase 2.4`."
last_updated: "2026-04-20T12:46:04.822Z"
last_activity: 2026-04-20 — new-mode GSD ingest bootstrap (18 docs → intel → roadmap)
progress:
  total_phases: 3
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 82
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-20)

**Core value:** First public demonstration of multiple OpenClaw agent instances simultaneously controlling multiple simulated robots in competition and cooperation, with visible output for every feature.
**Current focus:** Phase 2.4 — View-experiment A/B (drafted in root `PLAN.md`, awaiting `/gsd-plan-phase 2.4`)

## Current Position

Phase: 2.4 of 3 (View-experiment A/B)
Plan: 0 of 6 (tentative plan count — refined during planning)
Status: Ready to plan
Last activity: 2026-04-20 — new-mode GSD ingest bootstrap (18 docs → intel → roadmap)

Progress: [████████████████░░░░] 82%
(18 of 22 historical+active plans complete; Phase 2.4 + 2.5 not started; Phase 3 deferred and excluded from the denominator)

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

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- **Phase 2.3 (LOCKED, 2026-04-20)**: Decline digest-pinning the Gateway image; keep `ghcr.io/openclaw/openclaw:2026.4.14`. One-click rollback digest recorded in ADR.
- **Phase 2.2 (2026-04-16)**: Ship 3 symmetric Layer 3 tiles (nav / territory / coverage); reject UC1 Persona Showdown framing.
- **Phase 2.2 (2026-04-16)**: "Long-running" = within a single game run; no cross-run MEMORY persistence.
- **Phase 2.1**: Gateway transport is `POST /v1/chat/completions` with `model="openclaw/<agentId>"`; not `/tools/invoke`.
- **Phase 2.1**: Inline base64 image transport; no bind mount.

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

Last session: 2026-04-20 (new-mode GSD ingest + post-ingest verification)
Stopped at: Roadmap + state + requirements bootstrapped from `.planning/intel/`; both ingest WARNINGs verified stale and marked RESOLVED. Next action: `/gsd-plan-phase 2.4`.
Resume file: `/home/mi/ws/gogo/roboclaws/PLAN.md` (drafted Phase 2.4)

## Dual-Stack Workflow

- **gstack** owns pre-plan deliberation: `docs/`, `PLAN.md` (root), research reports.
- **GSD** owns execution: `.planning/` (this directory), STATE.md, ROADMAP.md, phase plans.
- Pre-plan → plan handoff: when a drafted phase in root `PLAN.md` is ready for execution, the owner runs `/gsd-plan-phase <phase>` and this STATE.md is updated.

**Planned Phase:** 2.5 (Autonomous OpenClaw loop (v1 single-agent nav + human steer)) — 8 plans — 2026-04-20T12:46:04.817Z

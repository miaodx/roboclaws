# Synthesis — roboclaws ingest (new-mode bootstrap, 2026-04-20)

This file is the entry point for `gsd-roadmapper`. It summarizes what
was synthesized from 18 classified planning documents into the
intel files under `.planning/intel/` and the conflict report at
`.planning/INGEST-CONFLICTS.md`.

## Doc counts by type

| Type | Count | Notes |
|---|---:|---|
| ADR  | 1  | Phase 2.3 (LOCKED — declined digest pin) |
| SPEC | 2  | `docs/technical-design.md` (high confidence), `PLAN.md` (medium — hybrid SPEC/PRD, classified SPEC for its implementation-contract bulk) |
| PRD  | 0  | None in the ingest set |
| DOC  | 15 | 5 research reports, 4 retrospectives (phase-2 / 2.1 / 2.2 / archive), `docs/contributing.md`, `docs/openclaw-local.md`, `docs/openclaw-gateway-internals.md`, `docs/issues-roadmap.md`, `docs/research/README.md`, `README.md`, `TODOS.md` |
| UNKNOWN | 0 | No low-confidence or unknown classifications |

## What shipped into intel/

- `decisions.md` — 1 LOCKED ADR (`DEC-phase-2.3-decline-digest-pin`);
  6 non-locked historical decisions preserved for provenance
  (Phase 2 pinned image, Phase 2.1 transport + named-agent routing,
  Phase 2.1 inline image transport, Phase 2.2 within-run memory,
  Phase 2.2 matrix-not-showdown).
- `requirements.md` — 11 requirements derived from the two SPECs
  (technical-design.md + PLAN.md § Phase 2.4) plus the shipped-state
  retros for scope fidelity. IDs:
  `REQ-ai2thor-multi-agent-engine`,
  `REQ-vlm-provider-pluggable`,
  `REQ-overhead-visualizer`,
  `REQ-soul-overlay-in-visualizer`,
  `REQ-territory-game` (with competing-variants A/B preserved),
  `REQ-coverage-game` (with competing-variants A/B preserved),
  `REQ-game-replay-recorder`,
  `REQ-ci-headless-ai2thor`,
  `REQ-openclaw-gateway-bridge`,
  `REQ-openclaw-per-agent-souls`,
  `REQ-view-experiment-ab` (Phase 2.4; not yet executed),
  `REQ-development-topology-cloud-vs-local`.
- `constraints.md` — 16 constraints (platform-selection, api-contract,
  schema, nfr, protocol). Notably: CONSTR-openclaw-image-pin is
  derived from the LOCKED ADR and pins the date-shaped
  `ghcr.io/openclaw/openclaw:2026.4.14`.
- `context.md` — running notes keyed by topic (positioning,
  shipped-state, three-layer demo matrix, Phase 3 Isaac Lab target,
  simulation platform landscape, OpenClaw ecosystem, AI2-THOR
  multi-agent research, real-model smoke outcome, dev topology,
  Gateway internals, cost concerns, contributor onboarding, research
  index, issues roadmap, current TODOS).

## Decisions locked

**Count:** 1

- `docs/retrospectives/phase-2.3.md` — Pin OpenClaw Gateway image by
  digest: **declined 2026-04-20**. Keep `:2026.4.14`. Digest
  `sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
  recorded in the ADR as the one-click rollback target via
  `OPENCLAW_IMAGE`.

No LOCKED-vs-LOCKED contradictions were possible (only one locked doc
in the ingest set).

## Requirements extracted

**Count:** 11 (see list above). Two carry preserved competing
acceptance variants — coverage game semantics (field-of-view vs
visited-cells) and VLM image-payload contract (SPEC says 2 images /
step, shipped behavior is `images=[]`). These are surfaced as
WARNINGs in the conflicts report; synthesis preserved all variants
rather than merging.

## Constraints (by type)

**Count:** 16

| Type | Count |
|---|---:|
| platform-selection | 1 (iTHOR-only) |
| api-contract       | 4 (AI2-THOR stepping, init shape, action vocabulary, VLM I/O JSON) |
| schema             | 3 (per-agent data, per-agent isolation layout, VLM I/O) |
| nfr                | 5 (image pin, curated provider list, cost envelope, headless Unity, live-probe-gate, dev topology) |
| protocol           | 4 (overhead-camera protocol, Gateway transport, named-agent model ID, webchat gotcha) |

(Some constraints span categories — counts above round to primary type.)

## Context topics

**Count:** 14 topic blocks in `context.md` (project positioning,
shipped-state, demo matrix, Phase 3 target, platform landscape,
OpenClaw ecosystem, AI2-THOR research details, real-model smoke
validation, dev topology, Gateway internals, multi-agent cost, CI
secrets, research index, issues roadmap + TODOS).

## Conflicts

- **BLOCKERS: 0** — safe to route.
- **WARNINGS: 2** — competing acceptance variants that block a clean
  Phase 2.4 execution:
  1. Coverage game: field-of-view vs visited-cells (unresolved by
     issue #52, 2026-04-14).
  2. VLM image-payload contract: SPEC requires 2 images / step;
     shipped game loops pass `images=[]` per 2026-04-14 validation.
- **INFO: 1** — the LOCKED ADR on digest pinning cleanly supersedes
  three non-locked sources that all already agree with it; no action
  needed.

Full detail at `.planning/INGEST-CONFLICTS.md`.

## Entry-point guidance for `gsd-roadmapper`

- The two WARNINGs directly gate Phase 2.4. The view-experiment A/B
  harness (`REQ-view-experiment-ab`) **cannot** produce meaningful
  results until (a) the coverage semantics question is resolved and
  (b) the game loops actually pass `images` through to
  `provider.get_action`. Sequence these two pre-requisite items ahead
  of the T29a-T37 task chain.
- The single LOCKED decision restricts image-pin choices only. No
  other roadmapping constraints flow from it.
- All shipped Phase 2 / 2.1 / 2.2 work is captured as context (not
  re-planned). Phase 2.3 is closed as declined. The next planning
  unit is Phase 2.4 + whatever emerges from #52 resolution.
- TODOS.md is empty by design at ingest time — the bootstrap is
  deliberate; all future TODOs should originate from the roadmap
  generated downstream of this synthesis.

## Pointers

- Decisions: `.planning/intel/decisions.md`
- Requirements: `.planning/intel/requirements.md`
- Constraints: `.planning/intel/constraints.md`
- Context: `.planning/intel/context.md`
- Conflicts report: `.planning/INGEST-CONFLICTS.md`

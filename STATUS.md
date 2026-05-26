# Project Status

Last updated: 2026-05-26

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws is focused on the MolmoSpaces cleanup path: making household cleanup
artifacts visible, honest, and aligned with future real-robot backends.

The active follow-up is the visual-grounding GPU sidecar benchmark for
MolmoSpaces cleanup. The current implementation keeps the existing HTTP
visual-grounding service boundary, adds first-wave benchmark-matrix support,
records sidecar runtime diagnostics, and keeps CUDA/model dependencies in a
dedicated `.venv-visual-grounding/` sidecar environment instead of the core
cleanup `.venv/`. The local GPU pass on 2026-05-26 promoted a stored
RAW_FPV corpus, benchmarked the implemented first-wave rows against a real CUDA
sidecar, and validated the selected Grounding DINO row against a direct cleanup
control run.

The Agibot SDK runner backend boundary for `real_robot_cleanup_v1` remains a
separate confidence layer. Roboclaws keeps the cleanup-shaped public contract and
calls the SDK runner through a subprocess CLI; the SDK runner owns Agibot GDK
map, observation, navigation, and per-stage evidence.

For Agibot/MolmoSpaces confidence-layer distinctions, read root `CONTEXT.md`
before planning or implementation. Keep Agibot map visual dry runs, SDK dry
runs, MolmoSpaces semantic cleanup on Agibot-shaped map data, and MolmoSpaces
Agibot contract rehearsal separate.

## Next Action

Run Codex-runtime cleanup validation for the selected Grounding DINO pipeline
only on a non-work network or through an allowed repo-local key route. Current
proof level is real local CUDA sidecar benchmark plus direct MolmoSpaces
cleanup validation; Codex/OpenClaw validation remains guarded by the
work-network policy.

## Current Blocker

No hosted-CI Codex blocker remains. Hosted CI must not launch Codex, run Codex
provider smoke, or block on Codex acceptance artifacts. Local work-network runs
support Codex and Claude Code only through repo-local `.env` configuration;
local non-work-network runs also support OpenClaw.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill-first MCP design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Active Nav2 cleanup status:
  `docs/status/active/real-robot-nav2-cleanup-pilot.md`
- Active Agibot plan/evidence: `docs/plans/agibot-g2-cleanup-support-pilot.md`
- Agibot robot_map_9 dry-run boundary:
  `docs/plans/agibot-robot-map-9-dry-run-rehearsal.md`
- Agibot robot_map_9 semantic actions:
  `docs/plans/agibot-robot-map-9-semantic-actions-rehearsal.md`
- MolmoSpaces Agibot contract rehearsal:
  `docs/plans/molmospaces-agibot-contract-rehearsal.md`
- Auto semantic map build:
  `docs/plans/auto-semantic-map-build.md`
- Visual grounding GPU sidecar benchmark:
  `docs/plans/visual-grounding-gpu-sidecar-benchmark.md`
- Current status: `STATUS.md`
- Human docs: `docs/human/`

## AI-Agent Sources

- GSD execution state: `.planning/STATE.md`
- Current phase details: follow the latest phase link in `.planning/STATE.md`
- Pre-GSD plans: `docs/plans/`
- Durable decisions: `docs/adr/`
- Shipped history: `docs/retrospectives/`
- Concurrent standalone work: `docs/status/active/`

## Recently Shipped

See `.planning/STATE.md` for the latest phase summary and
`docs/retrospectives/` for shipped history. Keep only current orientation here.

## Parked

- Queued implementation tasks live in `TODOS.md`.
- Scratch ideas and future directions live in `THOUGHTS.md`.
- GitHub issues track externally visible work for `MiaoDX/roboclaws`.

## Concurrent Work

Standalone task/refactor notes live in `docs/status/active/`.
Do not edit `STATUS.md` for routine per-task progress. Update this file only
when the repo-level current focus, latest phase, next action, or blocker
changes.

## Workflow Contract

Use the hybrid pipeline as the normal path:

`idea -> docs/plans/<slug>.md -> review/autoplan -> GSD plan/execute -> verify -> retrospective`

Rules:

- `STATUS.md` answers "what is happening now?"
- `docs/plans/` owns pre-GSD plans.
- `.planning/` is GSD-owned execution detail.
- `docs/human/` is the human-readable doc set; other `docs/` folders are
  primarily AI-agent evidence, generated planning detail, or history.
- `docs/adr/` records durable decisions, not progress.
- Root `PLAN.md` is a legacy compatibility pointer, not an active plan.
- `TODOS.md` and `THOUGHTS.md` are parked-work surfaces, not current status.
- Parallel terminals should use one task-owned file under `docs/status/active/`.
- At GSD closeout/verify/ship, update this file if current focus, latest phase,
  next action, or blocker changed.

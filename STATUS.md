# Project Status

Last updated: 2026-06-11

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws has completed the household-world launch contract saturation:
`surface=household-world` with `intent=map-build`, `cleanup`, and
`open-ended`, plus the `surface=planner-proof` confidence route. The
AI2-THOR/direct-VLM public-surface retirement is implemented and verified; the
active code, docs, tests, skills, CI, and public command facade now center on
household-world / planner-proof.

The implemented source of truth is
`docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`, backed by
ADR-0136. The implemented retirement record is
`docs/plans/refactor-retire-ai2thor-vlm-direct.md`.

## Next Action

Use the canonical launch shape for new work:
`just run::surface surface=household-world ... intent=map-build|cleanup` or a
household prompt that infers `intent=open-ended`. Pick the next implementation
task from `TODOS.md`, `docs/plans/`, or the issue tracker rather than reopening
the completed launch-contract saturation.

## Current Blocker

No current implementation blocker. The household launch-contract saturation and
AI2-THOR/direct-VLM retirement are implemented; live OpenClaw/Gateway and
deleted AI2-THOR gates are not required for those proofs.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill-first MCP design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Implemented household map/launch/open-ended plan:
  `docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`
- Active launch contract ADR:
  `docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md`
- Implemented AI2-THOR/direct-VLM retirement record:
  `docs/plans/refactor-retire-ai2thor-vlm-direct.md`
- Open-ended proof-status contract:
  `docs/plans/2026-06-11-open-ended-proof-status.md`
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

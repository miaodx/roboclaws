# Project Status

Last updated: 2026-05-11

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws is focused on the MolmoSpaces cleanup path: making household cleanup
artifacts honest about which steps are semantic simulator mutations and which
steps have planner-backed RBY1M/CuRobo proof.

Phase 134, MolmoSpaces canonical proof command tool order, is complete. There
is no active GSD implementation phase at the moment.

## Next Action

Execute the bounded `proof_001` two-step local proof attempt with canonical
cleanup tools, then rerun cleanup only if the resulting proof has cleanup
binding coverage.

## Current Blocker

The global cleanup bridge is still blocked until broader or stronger
planner-backed proof evidence exists for cleanup primitives. The latest
`proof_001` artifact is a dry-run command/report, not fresh runtime proof.

## Authoritative Sources

- Human dashboard: `STATUS.md`
- GSD execution state: `.planning/STATE.md`
- Current phase details: follow the latest phase link in `.planning/STATE.md`
- Domain vocabulary: `CONTEXT.md`
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
- `docs/adr/` records durable decisions, not progress.
- Root `PLAN.md` is a legacy compatibility pointer, not an active plan.
- `TODOS.md` and `THOUGHTS.md` are parked-work surfaces, not current status.
- Parallel terminals should use one task-owned file under `docs/status/active/`.
- At GSD closeout/verify/ship, update this file if current focus, latest phase,
  next action, or blocker changed.

# Project Status

Last updated: 2026-05-15

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws is focused on the MolmoSpaces cleanup path: making household cleanup
artifacts visible and honest from local runs through CI-published report pages.

Phase 135, MolmoSpaces CI live-agent reports, is implemented and non-live
verified. The opt-in hosted workflow now installs Codex/Claude Code, prewarms
MolmoSpaces assets, passes explicit Claude MCP config, and reaches the cleanup
MCP tools with repo-scoped provider secrets.

Phase 136, Generic MCP entrypoint and semantic capability profiles, is
implemented and verified. It adds an additive profile/router layer for
AI2-THOR and MolmoSpaces MCP contracts while keeping simulator accelerators and
Molmo private evaluator truth out of canonical public profile metadata.

## Next Action

Land the current report-surface follow-up and Phase 136 semantic-profile
commits, then trigger or monitor the next `main` Pages deploy so the dedicated
Molmo live index and report rerun commands are visible on the public site.

## Current Blocker

The latest completed Molmo live dispatch proved both MiMo entries successfully,
but a later `main` Pages deploy skipped the opt-in Molmo live matrix and erased
those files from the public site. The preservation patch rehydrates the latest
successful live dispatch on ordinary Pages deploys; Kimi live still needs
provider-error follow-up.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill/MCP profile design: `docs/human/mcp-skills-and-semantic-profiles.md`
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

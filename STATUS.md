# Project Status

Last updated: 2026-06-15

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws is executing the eval-driven architecture plan. Slice 0 through Slice
5a are verified: eval suites are visible as a first-class architecture
layer, stale launch-axis documentation is cleaned, current cleanup/map-build
MCP contracts no longer advertise `fixture_hints` as a callable active tool,
and repo-native eval suite/sample/trial/result schema packets plus
direct-runner household fixtures exist. Deterministic eval suites are available
through `just agent::eval suite=smoke_regression budget=smoke` and
`just agent::eval suite=map_build_consumer budget=smoke`; the repeated
`cleanup_capability` suite now records `pass@k` and `pass^k` metrics. Eval
suites write `eval_results.json` plus `eval_report.html` linked to product run
artifacts. The `map_build_consumer` suite covers map-build Runtime Metric Map
actionability, cleanup consumption of `runtime_map_prior`, and open-ended
completion-claim versus artifact-readiness grading.

The household-world launch contract remains the active product shape:
`surface=household-world` defaults to the no-preset open household task
contract, with `preset=map-build` and `preset=cleanup` for standard jobs, plus
the `surface=planner-proof` confidence route.

The active visual-grounding sidecar contract is now detector-only: hosted VLM
refiner/direct-producer camera labelers are retired from active code, command
examples, tests, and benchmark promotion. OpenClaw remains available only as a
guarded validation-required maintainer route until an off-work-network Gateway
proof runs.

The active source of truth is
`docs/plans/2026-06-14-eval-driven-architecture.md`, backed by ADR-0140. The
implemented household launch contract is
`docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`, backed by
ADR-0136. The implemented visual-grounding cleanup is
`docs/plans/2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md`,
backed by ADR-0138. The implemented AI2-THOR/direct-VLM retirement record is
`docs/plans/refactor-retire-ai2thor-vlm-direct.md`.

## Next Action

Continue `docs/plans/2026-06-14-eval-driven-architecture.md` with the remaining
Slice 5 live-agent runtime integration: run selected eval samples with a real
Codex CLI, Claude Code, or OpenAI Agents SDK provider route when local
provider/runtime requirements are available.

## Current Blocker

No current implementation blocker for deterministic eval work. Live-agent eval
execution remains gated on local provider/runtime availability; current
non-direct eval requests are recorded as blocked with provider/runtime failure
classes instead of being downgraded. The only known validation blocker is
OpenClaw Gateway: this host is on the work network, so Gateway proof must run
separately off the work network before OpenClaw can be called healthy.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill-first MCP design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Active eval-driven architecture plan:
  `docs/plans/2026-06-14-eval-driven-architecture.md`
- Active eval-suite ADR:
  `docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md`
- Implemented household map/launch/open-ended plan:
  `docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`
- Active launch contract ADR:
  `docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md`
- Active detector-only sidecar ADR:
  `docs/adr/0138-use-detector-only-visual-grounding-sidecar.md`
- Implemented VLM-sidecar/OpenClaw status cleanup:
  `docs/plans/2026-06-12-vlm-direct-sidecar-and-openclaw-status-cleanup.md`
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

# Project Status

Last updated: 2026-06-18

This is the human-facing dashboard for the repo. Keep it short: current state
and pointers only, not a changelog or execution ledger.

## Current Focus

Roboclaws has implemented the eval-driven architecture plan and the follow-on
non-cleanup eval support plan. Eval suites are visible as a first-class
architecture layer, stale launch-axis documentation is cleaned, current
cleanup/map-build MCP contracts no longer advertise `static_fixture_projection` as a
callable active tool, and repo-native eval suite/sample/trial/result schema
packets plus direct-runner household fixtures exist. Deterministic eval suites
are available through `just agent::eval suite=smoke_regression budget=smoke`,
`just agent::eval suite=open_ended_goals budget=smoke`, and
`just agent::eval suite=map_build_consumer budget=smoke`; the repeated
`cleanup_capability` suite records `pass@k` and `pass^k` metrics. Eval suites
write `eval_results.json` plus `eval_report.html` linked to product run
artifacts. The dedicated `open_ended_goals` suite covers the public no-preset
household prompt route, while `map_build_consumer` covers Runtime Metric Map
actionability and `runtime_map_prior` consumption. Eval-harness recommendations
now distinguish open-ended, map-build, scene-sampler stress, and planner-proof
proof rows. Live eval execution is opt-in with `live_execution=run`; default
non-direct eval requests still record blocked identity/preflight packets so
provider-backed work is not launched by accident. Codex CLI live eval runs pass
a fixed product `run_dir` through the public launch route and poll detached live
artifacts before grading, including a short completion grace window for
late-written `run_result.json` files. OpenAI Agents SDK live eval runs now use
the same open-ended sample contract and grade current `world-public-labels`
artifacts. Failed, blocked, or inconclusive eval results can be promoted into
regression samples with
`just agent::eval promote-regression ...` while keeping private scorer truth
inside grader-only sample metadata.

The household-world launch contract remains the active product shape:
`surface=household-world` defaults to the no-preset open household task
contract, with `preset=map-build` and `preset=cleanup` for standard jobs, plus
the `surface=planner-proof` confidence route.

The sim household map surface simplification is implemented. Current sim
reports and operator-console map slots distinguish the Base Navigation Map
preview from Runtime Metric Map evidence, keep Runtime Map Prior Snapshot
as a prior wrapper, and no longer publish generated `semantic_map.png` /
`map_overlay.json` previews as current map proof.

The active camera-labeling sidecar contract is detector-only. Hosted refiner or
direct-producer camera labelers are retired from active code, command examples,
tests, and benchmark promotion. Validation-required maintainer routes stay
guarded until their separate off-work-network proof runs.

The first-slice cross-environment semantic map parity contract is implemented.
Real-robot, B1 digital-twin, and simulator static map bundles now declare
source-frame spatial metadata, explicit `display_frame` absence, polygon role,
geometry source, and alignment status. B1 scene partition labels bind through
`scene_map_correspondence_v1` instead of list order, and reports label
raw/source-map aligned previews.

The B1 / Map 12 digital-twin map input contract now has accepted geometry
alignment, preview-grade residual-backed robot pose/render proof, and
agent-visible runtime-prior capability exposure. Product and operator-preview
routes compile a generated runtime bundle from
`vendors/agibot_sdk/artifacts/maps/robot_map_12/agibot`,
`vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json`,
`assets/maps/b1-map12-alignment-review.json`, explicit alignment/navigation
proof artifacts, and the raw scene root before passing map context to
lower-level consumers. The implemented P0 consumer-chain plan is
`docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`: explicit B1
runtime priors now expose `digital_twin_capabilities`, `capability_summary`,
render/observation readiness, and blocked `B1_floor2_slow` default visual-route
status through agent-visible MCP/runtime map context. Room/object semantic
projection and public navigation extensions are follow-ups in
`docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`.

The implemented non-cleanup eval support plan is
`docs/plans/2026-06-15-non-cleanup-eval-support.md`. The implemented
open-ended eval matrix expansion is
`docs/plans/2026-06-16-open-ended-eval-matrix-expansion.md`. The active eval
architecture source of truth is
`docs/plans/2026-06-14-eval-driven-architecture.md`, backed by ADR-0140. The
implemented sim map surface simplification is
`docs/plans/2026-06-17-sim-map-surface-simplification.md`. The
implemented household launch contract is
`docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`, backed by
ADR-0136. The implemented visual-grounding cleanup is backed by ADR-0138.
Retirement records remain searchable under `docs/plans/`. The implemented B1 / Map 12
thin review/runtime contract is
`docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`.

## Next Action

Use `docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md` for
the next B1 / Map 12 work: accepted room-semantic anchors, strict room/object
semantic projection, and any public navigation extension after a separate
proof gate.

## Current Blocker

No current human blocker for the implemented B1 P0 digital-twin
navigation/render consumer-chain slice. Room semantic review remains required
before semantic projection follow-up work can be promoted.

No current implementation blocker for deterministic or open-ended coding-agent
smoke eval work. Opt-in live eval execution reaches the live product route on
this host, and `open_ended_goals` passed with `agent_engine=codex-cli`,
`provider_profile=codex-router-responses`, and `live_execution=run` on 2026-06-16. The same
suite also passed with `agent_engine=openai-agents-sdk`,
`provider_profile=minimax-responses`, and `live_execution=run` on 2026-06-16. The
`openai-agents-sdk` / `codex-router-responses` route was exercised live but blocked on an
upstream 502 provider response, so it is not counted as a behavioral pass.
Default non-direct eval requests remain blocked identity/preflight packets
unless live execution is explicitly requested. Remaining validation blockers are
external or product-route-specific: broader live-agent `pass^k` proof needs
healthy provider/runtime capacity and agent behavior that reaches `done`,
RAW-FPV live cleanup needs live-session capacity, and validation-required
maintainer routes need separate off-work-network proof before they can be
called healthy.

## Human Review Surface

- Project orientation: `README.md`
- Architecture and contracts: `ARCHITECTURE.md`
- Skill-first MCP design: `docs/human/mcp-skills-and-semantic-profiles.md`
- Implemented eval-driven architecture plan:
  `docs/plans/2026-06-14-eval-driven-architecture.md`
- Implemented non-cleanup eval support plan:
  `docs/plans/2026-06-15-non-cleanup-eval-support.md`
- Implemented open-ended eval matrix expansion:
  `docs/plans/2026-06-16-open-ended-eval-matrix-expansion.md`
- Implemented sim map surface simplification:
  `docs/plans/2026-06-17-sim-map-surface-simplification.md`
- Active eval-suite ADR:
  `docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md`
- Implemented household map/launch/open-ended plan:
  `docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`
- Active launch contract ADR:
  `docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md`
- Active detector-only sidecar ADR:
  `docs/adr/0138-use-detector-only-visual-grounding-sidecar.md`
- Implemented cross-environment semantic map parity plan:
  `docs/plans/2026-06-15-cross-environment-semantic-map-parity.md`
- Implemented B1 / Map 12 thin review/runtime contract:
  `docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md`
- Active B1 / Map 12 two-map alignment blocker:
  `docs/plans/2026-06-17-b1-map12-two-map-alignment-blocker.md`
- B1 / Map 12 semantic and public-navigation follow-ups:
  `docs/plans/2026-06-18-b1-map12-semantic-and-public-nav-followups.md`
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

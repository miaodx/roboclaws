# ADR-0136: Use Base Navigation Map And First-Class Household Launch Contracts

Status: Accepted

Date: 2026-06-11

## Context

The household-world stack accumulated several overlapping public concepts:

- `map_mode=minimal|rich` exposed a selectable sparse-vs-authored map mode.
- `fixture_hints()` encouraged agents to look for static fixture semantics
  before using runtime evidence.
- `profile`, `cleanup_profile`, `evidence_lane`, `camera_labeler`, and
  `visual_grounding` mixed evidence shape with producer implementation.
- `evidence_lane=smoke` made a cheap verification preset look like agent
  evidence.
- `task_intent_mode=custom` kept open-ended goals tied to cleanup-specific
  runtime language after `intent=open-ended` became first-class.
- Operator-console legacy route IDs such as `codex-mujoco-cleanup` remained
  live beside canonical launch selection IDs.

Recent open-ended household goals, such as asking for something to drink or
fruit, showed that public room-category hints are useful search priors. At the
same time, exposing full simulator-authored fixture inventory remains too close
to private/static truth for the default agent-facing surface.

## Decision

Use `Base Navigation Map` as the current start-of-run map contract. It may
include occupancy/free-space geometry, frame metadata, current robot pose,
generated safe exploration or inspection candidates, and public room-category
hints. It must not expose private relocation/scoring truth, static movable
object inventory, or a full static fixture/receptacle table by default.

Remove public `rich` / `minimal` map-mode selection from current task behavior.
Historical source artifacts and report readers may still understand those terms,
but new product behavior should not ask agents to choose between them.

Keep semantic enrichment in the Runtime Metric Map. Semantic-map-build and
online observations produce public semantic anchors, observed objects, target
candidates, target actionability, and generated inspection candidates.

Remove `fixture_hints()` from active MCP tools after prompts and tests migrate
to Base Navigation Map plus Runtime Metric Map target discovery. Historical
reports may still read old `fixture_hints` artifacts for display.

Use `evidence_lane` only for what the agent sees, and `camera_labeler` only for
the producer used by `camera-grounded-labels`. Keep `smoke` as a verification
preset or runner mode, not an evidence lane. New smoke examples should combine
a smoke preset with a real evidence lane such as `world-oracle-labels`.

Use first-class `intent=open-ended` for open-ended household runs and artifacts.
New artifacts should use `task_intent=open-ended` and
`goal_contract.intent=open-ended` directly. `task_intent_mode=custom` is
historical compatibility only.

Use canonical operator-console launch selection IDs for new launches and
reloads. Legacy route IDs are read-only history display only.

## Rejected Alternatives

- Keep `map_mode=rich` as an explicit debug/product mode.
  Rejected because it preserves a public abstraction that gives agents a stale
  choice between sparse context and static fixture truth.

- Keep `fixture_hints()` as an empty or deprecated active MCP tool.
  Rejected because the tool name keeps reinforcing the wrong first-call habit.

- Keep `evidence_lane=smoke`.
  Rejected because smoke is a verification preset, not evidence presented to an
  agent.

- Keep `task_intent_mode=custom` for new open-ended runs.
  Rejected because it makes a first-class intent depend on cleanup-specific
  compatibility language.

- Keep operator-console legacy route IDs launchable for convenience.
  Rejected because it preserves the old route-card model beside the canonical
  launch catalog.

## Consequences

- The implementation plan is
  `docs/plans/2026-06-11-household-map-launch-open-ended-contracts.md`.
- Current docs, prompts, tests, route code, MCP setup, and checker/report
  expectations should converge on Base Navigation Map and Runtime Metric Map.
- Public room-category hints are allowed as search priors; full static fixture
  inventory remains hidden by default.
- Historical artifacts can remain readable, but compatibility readers must not
  reintroduce old public command/API behavior.
- Cleanup intent remains terminally cleanup-scored. Open-ended cleanup-like
  scores remain advisory and must not override the open-ended terminal outcome.

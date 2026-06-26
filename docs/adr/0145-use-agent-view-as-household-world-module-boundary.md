# ADR-0145: Use Agent View As Household-World Module Boundary

Status: Accepted

Date: 2026-06-22

Plan:
[`docs/plans/2026-06-22-agent-view-module-refactor.md`](../plans/2026-06-22-agent-view-module-refactor.md)

## Context

Household-world runs now expose several public evidence lanes, live agent
engines, direct deterministic runners, Base Metric Map artifacts, Runtime
Metric Map evidence, active perception flows, and eval-harness rows. The
public/private rule is stable, but enforcement is spread across payload
builders, MCP tool responses, done-readiness blockers, visual-candidate helpers,
Agibot pilot code, report readers, and repeated forbidden-key checks.

That spread makes the contract harder to evolve. Future eval and agent-quality
work needs one ownership point for the exact public information an agent may see
and act on.

## Decision

Use Agent View as a first-class household-world module boundary.

Agent View owns:

- agent-facing input assembly for saved artifacts and live robot responses;
- provenance and real-robot-obtainability labels for public evidence;
- blocked-capability and provenance-limited status vocabulary;
- private-exclusion enforcement for generated mess state, hidden setup state,
  private scorer truth, simulator-only oracles, and report-only views.

Agent View covers every household-world backend path, including MolmoSpaces /
MuJoCo and Agibot / GDK. Backend-specific construction may stay local only when
it is behind the shared Agent View schema, guard, provenance, and
blocked-capability vocabulary.

Agent View enforcement applies to:

- `agent_view.json` and embedded `run_result.agent_view`;
- MCP tool responses and completion/readiness blockers;
- visual candidate responses and active-perception evidence returned to agents;
- detector or visual-grounding sidecar request inputs when those inputs affect
  what an agent may see or act on.

Active perception is an Agent View adapter, not a separate product goal.
Grounding DINO, RAW-FPV observations, camera-grounded labels, visual-grounding
sidecar status, uncertainty, and candidate lifecycle summaries should be
represented through Agent View. Sidecar inputs must be built from public Agent
View evidence, Base Metric Map, Runtime Metric Map, public fixture hints, or
current camera evidence.

`static_fixture_projection` is not the new Agent View center. Historical
artifact/report readers may still understand it, but active agent behavior
should reason from Base Metric Map, Runtime Metric Map, public semantic
anchors, target candidates, and public MCP capability metadata.

Eval-to-evolution work may later target `agent_view_module` as a concrete
evolution target. This ADR does not approve a broad eval-harness taxonomy
redesign, `evolution_target` fields, capability-slice grouping, or a provider
matrix expansion.

## Rejected Alternatives

- Keep Agent View as repeated helper functions inside real-world payload code.
  Rejected because the boundary must cover live tool responses, Agibot, active
  perception, and future eval targeting, not only one saved artifact builder.
- Make active perception its own top-level architecture goal. Rejected because
  detectors and RAW-FPV candidate flows are evidence adapters under the
  agent-facing public/private boundary.
- Preserve the current `agent_view.json` field layout with compatibility
  wrappers. Rejected because this is a forward architecture upgrade; known
  in-repo consumers should migrate with an explicit schema/version marker.
- Treat Agibot as a separate Agent View contract. Rejected because physical
  routes should share the same household-world public evidence vocabulary while
  keeping backend-specific execution details behind adapters.
- Use private scorer truth or simulator-only fixture oracles to enrich sidecar
  requests. Rejected because sidecars can influence agent-facing evidence.

## Consequences

- A canonical Agent View module or owner must assemble or validate saved
  artifacts and live agent-facing responses.
- `agent_view.json` may keep its artifact name, but layout changes need an
  explicit schema/version marker and in-repo consumer migration.
- MolmoSpaces and Agibot Agent View producers must share forbidden-key guards,
  provenance labels, and blocked-capability vocabulary even when backend-local
  payload construction remains separate.
- MCP server/runtime adapters must stay thin. Task strategy and prompt policy
  remain in skills, not in Agent View or server plumbing.
- Eval-harness path selection should recognize Agent View module changes
  narrowly, without redesigning row taxonomy.

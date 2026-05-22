# 0130. Default Composition To Trace-Preserving Skill Routines

Date: 2026-05-20

## Status

Accepted; updated by ADR-0132

## Decision

Roboclaws will keep MCP profiles bounded by default: MCP should expose atomic
semantic capabilities and stable semantic services, while repeated task-like
composition starts as a trace-preserving skill routine. A skill routine may use
scripts, evals, structured output, and explicit recovery, but it remains agent
behavior rather than a robot capability claim.

Promote a routine into MCP only when the composition has become a stable,
backend-enforced, cross-client robot capability contract. Promotion requires
stable public inputs and outputs, preserved public substeps, clear provenance
and blocker semantics, public/private boundary clarity, and evidence that
multiple skills or clients need the same capability. After promotion, the skill
should stop duplicating the lower-level call chain and delegate to the promoted
capability.

The normal promoted-tools surface should therefore be empty. A non-empty
promoted surface signals a deliberate promotion event, not a convenient place to
put task strategy or performance shortcuts. `clean_observed_object` remains a
performance-lane promoted candidate for timing work unless and until it satisfies
the promotion criteria for a canonical cleanup contract profile.

For Molmo cleanup, the current trace-preserving routine lives in
`skills/molmo-realworld-cleanup/scripts/trace_preserving_cleanup.py` and is
documented in `skills/molmo-realworld-cleanup/SKILL.md`. A 2026-05-20 live
Codex apples-to-apples comparison showed the skill routine is transparent but
not performance-alike in the timing lane:

- Skill routine:
  `output/molmo/codex-skill-routine-perf/0520_1204/seed-7/report.html`,
  `7m18s`, 85 MCP requests, `clean_observed_object=0`, full sweep.
- Explicit promoted-candidate lane:
  `output/molmo/codex-mcp-routine-perf/0520_1319/seed-7/report.html`,
  `4m35s`, 51 MCP requests, `clean_observed_object=10`, full sweep.

Therefore canonical cleanup composition remains skill-side, but
`world-labels-perf` continues to default to the MCP candidate until a later
skill-side execution path closes that gap. Use `cleanup_routine=skill` for
comparison runs.

The RAW_FPV path was also checked with local Codex on 2026-05-20:

- Skill route:
  `output/molmo/codex-camera-raw-skill-check/0520_1324/seed-7/report.html`,
  `14m06s`, 80 MCP requests, seven grounded atomic cleanup chains, full sweep.
- Explicit promoted-candidate route:
  `output/molmo/codex-camera-raw-mcp-check-final3/0520_1508/seed-7/report.html`,
  `14m35s`, 66 MCP requests, seven grounded `clean_observed_object` calls, full
  sweep.

Both routes are valid comparison paths for RAW_FPV after public visual
grounding. The MCP composite remains an explicitly enabled comparison/perf
candidate, not a canonical cleanup profile tool.

## Considered Options

- Put reusable composition only in MCP. This reduces round trips but risks
  turning MCP into a task API and hiding strategy behind server calls.
- Keep all composition only in skills. This keeps MCP small but loses protocol
  visibility when a composition needs cross-client discovery, schema validation,
  backend safety enforcement, or stable trace semantics.
- Incubate composition in trace-preserving skill routines, then promote only
  when the backend boundary genuinely requires it. This preserves skill-first
  evolution while keeping a narrow path for real robot and cross-client
  capability contracts.

## Consequences

- Skill authors have one obvious default path for reusable behavior: build a
  trace-preserving skill routine first.
- MCP maintainers have one obvious promotion bar: add a composite tool only when
  it is a backend-enforced capability contract, not a performance hack.
- Performance lanes may keep experimental promoted candidates, but canonical
  profiles should not expose them until the promotion criteria are met.

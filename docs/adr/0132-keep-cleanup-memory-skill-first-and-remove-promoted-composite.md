# 0132. Keep Cleanup Memory Skill-First And Remove Promoted Composite

Date: 2026-05-22

## Status

Accepted

## Decision

Roboclaws will keep Molmo cleanup task memory skill-first without expanding the
default MCP surface. A cleanup skill may keep a run-local, non-authoritative
Skill Scratchpad for strategy, hypotheses, retries, and next-action intent. The
contract/runtime owns the Cleanup Worklist: a public lifecycle view derived from
agent-visible capability events and used for `done` gates, reports, and checkers.
If the two disagree, the contract-derived worklist is authoritative.

MCP primitive tools should remain general capability tools. `observe`,
`navigate_to_waypoint`, `pick`, `place`, and related primitives should not carry
cleanup-specific progress summaries by default, and Roboclaws will not add a
default live `cleanup_worklist` query tool just to repair agent memory. A skill
helper may reconcile its scratchpad from public tool results, routine results,
and `done` recovery payloads, but the scratchpad is not scorer, checker, report,
or `done` input.

Roboclaws will remove the `clean_observed_object` promoted MCP candidate and the
`cleanup_routine=mcp|mcp-promoted` route. The 2026-05-20 timing evidence in
[ADR-0130](archive/superseded/0130-default-composition-to-trace-preserving-skill-routines.md)
remains useful history: the promoted candidate reduced MCP round trips and
improved one performance lane, but it introduced a second cleanup sequence and
a cleanup-specific MCP branch. Architecture clarity, one behavior path, and the
skill-first boundary now take priority over that optimization.

Molmo cleanup should instead use one canonical routine engine for a single
already-selected object transport chain:
`navigate_to_object -> pick -> navigate_to_receptacle -> open? -> place/place_inside -> close?`.
Direct demos, MCP smoke runs, and live coding-agent skill helpers should share
that routine engine. The routine does not scan rooms, select candidates, maintain
task memory, read private truth, or decide when cleanup is done; those remain
skill strategy or contract responsibilities.

The `world-labels-perf` profile should be removed as a behavior profile. Fast
or timing-focused runs should use the normal input-contract profile, such as
`world-labels`, with explicit evidence/capture options like disabling robot-view
timeline capture.

## Consequences

- The default MCP surface stays stable and more generally applicable to
  open-ended tasks.
- Cleanup strategy and run-local memory live in the skill layer, while
  verifiable cleanup facts stay contract-derived.
- Reports may show Skill Scratchpad content only as non-authoritative agent
  notes or debug evidence.
- Roboclaws accepts possible extra MCP round trips in live agents to avoid a
  cleanup-specific promoted composite and duplicated semantic cleanup logic.
- ADR-0130 remains the historical record for the promoted-candidate timing
  experiment, but this ADR supersedes its conclusion to keep
  `clean_observed_object` and `world-labels-perf` as active comparison routes.

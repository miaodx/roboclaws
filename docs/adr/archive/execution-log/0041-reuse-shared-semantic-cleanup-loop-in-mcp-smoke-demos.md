# 0041. Reuse Shared Semantic Cleanup Loop In MCP Smoke Demos

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0027 introduced the shared semantic cleanup loop so MolmoSpaces demos use
one implementation for the object cleanup sequence: `nav`, `pick`, `nav`,
optional `open`, then `place`. Later ADRs made the Cleanup Artifact Report and
visual-core checker depend on that same report-facing vocabulary.

The current-contract and ADR-0003 MCP smoke scripts still contain hand-written
tool loops. They produce valid artifacts today, but the duplicate code creates
drift risk: a smoke demo can visually diverge from the shared report underlay or
skip future executor behavior added behind the semantic loop seam.

## Decision

Route MCP smoke cleanup execution through `run_semantic_cleanup_loop` instead
of hand-rolling `navigate_to_object`, `pick`, `navigate_to_receptacle`,
`open_receptacle`, and `place` calls inside smoke scripts.

Current-contract smoke should keep `object_done` enabled because that remains
part of its transitional MCP contract. ADR-0003 smoke should keep fixture-style
requests and no `object_done`, matching the public real-world MCP surface.

## Consequences

- Current-contract, ADR-0003 harness, and ADR-0003 MCP smoke demos share one
  cleanup-loop implementation and one semantic subphase vocabulary.
- Future planner-backed cleanup primitive executor work has one smoke-demo seam
  to test instead of multiple per-script loops.
- Report visual differences must come from evidence mode or contract-specific
  sections, not duplicated cleanup-loop code.

# 0036. Centralize Cleanup Report Visual Core Checks

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009 and ADR-0021 require MolmoSpaces cleanup demos to share one Cleanup
Artifact Report underlay. The latest code mostly follows that, but stale
artifacts such as `output/molmo-agent-bridge-visual-codex/report.html` made the
remaining gap visible: checkers still accepted reports that only proved
individual evidence strings, and the ADR-0003 MCP server still hand-rolled the
robot-view semantic capture mapping that other cleanup paths reuse.

That leaves two ways for report drift to return: a report can render the same
data in a different visual-core order, or an MCP surface can assign raw tool
labels differently from the shared semantic timeline.

## Decision

Add a shared report visual-core contract helper and use it from both the
current-contract bridge checker and the ADR-0003 checker. The visual core is
ordered as Before/After, Object Moves, Semantic Substeps when present, Robot
View Timeline when present, then Score. Semantic Substeps must show the
canonical report-facing labels `nav/object`, `pick/object`, `nav/target`, and
`place/surface` or `place/inside`.

Also route ADR-0003 MCP robot-view capture through
`semantic_timeline.robot_view_capture_for_tool`, with fixture IDs accepted as
the real-world target-key spelling. The MCP server still performs its
observed-handle to internal-object mapping, but no longer owns a second copy of
the semantic phase mapping.

## Consequences

- Stale current-contract reports that only contain raw tool strings no longer
  satisfy the visual-core checker.
- Current-contract, deterministic ADR-0003, and ADR-0003 MCP runs share the
  same semantic subphase display contract.
- This is a report architecture and validation slice. It does not generate new
  live MolmoSpaces artifacts or change planner-backed cleanup readiness.

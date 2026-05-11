# 0021. Use Canonical Cleanup Report Presentation

Date: 2026-05-09

## Status

Accepted

## Context

ADR-0009 requires MolmoSpaces cleanup demos to reuse the shared Cleanup Artifact
Report underlay instead of cloning per-demo HTML. The current implementation
does route current-contract, ADR-0003, direct-agent, OpenClaw, and model-policy
runs through `roboclaws/molmo_cleanup/report.py`, but the report renderer still
assembled sections inline.

That made report shape depend on the newest evidence slice. ADR-0003 audit
sections such as Agent View, Raw FPV Observations, Camera Model Policy,
Private Evaluation, planner proof attachment, and primitive gates could push
the visual cleanup review below the fold. It also left semantic phase labels
split across sections: Semantic Substeps showed report-facing labels, while
Robot View Timeline and primitive gates could still surface raw tool names as
the primary visual flow.

## Decision

The Cleanup Artifact Report has one canonical presentation sequence:

1. summary and contract note;
2. before/after snapshots;
3. object moves;
4. Semantic Cleanup Subphases;
5. Robot View Timeline when robot views exist;
6. score;
7. contract, planner, perception, advisory, and private-evaluation evidence.

Report-facing semantic phases are always displayed as
`nav -> pick -> nav -> open? -> place`. Raw tool names remain available in
traces, `run_result.json`, and secondary evidence fields, but they are not the
primary visual flow.

Current-contract and ADR-0003 demos should add data to the shared report model;
they should not change section order or create a second renderer to regain a
particular visual result.

## Consequences

- Real-world-style reports keep the same visual review rhythm as the older
  current-contract visual bridge artifacts while retaining ADR-0003 evidence.
- New evidence panels can be added without displacing before/after,
  Semantic Substeps, Robot View Timeline, and Score.
- The semantic label vocabulary lives in one timeline/report module and is
  reused by semantic cards, robot timeline badges, and cleanup primitive gates.
- Additional report-specific evidence remains conditional, but it hangs off the
  shared underlay rather than defining another implementation path.

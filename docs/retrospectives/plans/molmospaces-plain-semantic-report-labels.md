# MolmoSpaces Plain Semantic Report Labels

**Status:** Completed in GSD Phase 59 on 2026-05-10
**Source:** user visual review, CONTEXT.md, ADR-0009, ADR-0021, ADR-0036
**Workflow:** `hybrid-phase-pipeline`

## Problem

The report architecture is shared, but part of the report/checker contract
still treats `nav/object`, `pick/object`, and `nav/target` as the visible
semantic label. That is why newer generated reports still feel different from
the original `nav, pick, nav, open?, place` discussion.

The role detail is useful and should not be deleted; it just should not be the
primary report-facing subphase label.

## Decision

Implement ADR-0050 by making the report-facing primary label plain:
`nav`, `pick`, `nav`, optional `open`, `place`.

This phase:

- keeps role detail as secondary text in the phase rail;
- shows robot timeline badges as `Subphase=nav` plus `Role=target`;
- shows cleanup primitive gate rows with separate Display subphase and
  Subphase role columns;
- updates visual-core checks to validate the semantic rail structure rather
  than compound strings;
- keeps raw tool names in raw phase fields, trace files, and `run_result.json`.

## Result

Completed in code and tests. This is a report vocabulary cleanup only; it does
not change cleanup execution, private/public ADR-0003 data, or planner-backed
cleanup readiness.

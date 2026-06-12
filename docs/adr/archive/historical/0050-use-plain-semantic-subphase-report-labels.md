# 0050. Use Plain Semantic Subphase Report Labels

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0009 and ADR-0021 describe the MolmoSpaces cleanup visual loop as
`nav -> pick -> nav -> open? -> place`. Later report-core validation hardened
the more specific labels `nav/object`, `pick/object`, `nav/target`, and
`place/surface` or `place/inside`.

Those compound labels preserve useful role detail, but they also make the
primary report vocabulary drift from the original discussion and from the
operator-facing cleanup story.

## Decision

Cleanup Artifact Reports will use plain semantic subphase labels as the primary
visual vocabulary: `nav`, `pick`, `nav`, optional `open`, then `place`.

Object/target/surface/inside remains as secondary role detail in the semantic
rail, robot timeline badges, and cleanup primitive gate. Raw tool names remain
available in traces, `run_result.json`, and secondary report fields.

This supersedes only the display-label wording in ADR-0036. The shared report
underlay and shared visual-core checker remain the architecture.

## Consequences

- Reports read like the original semantic cleanup loop while still
  distinguishing object-side navigation from target-side navigation.
- Checkers validate the semantic rail structure instead of accepting raw tool
  names or requiring compound `label/detail` strings as the primary label.
- Existing ignored `output/` artifacts may remain stale until regenerated.

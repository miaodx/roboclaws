# Phase 115-01: Semantic Underlay Architecture

## Goal

Prevent future semantic cleanup report/checker drift by making one package
module own the `nav, pick, nav, open?, place` vocabulary.

## Tasks

- Add raw phase constants and canonical phase sequences to
  `semantic_timeline.py`.
- Route the semantic cleanup loop through those constants.
- Route report visual-core checks and report notes through the shared
  vocabulary.
- Route current-contract, ADR-0003, and MolmoSpaces cleanup checkers through
  the shared vocabulary.
- Update tests that asserted loop variants or canonical phase sequences to use
  the shared constants.

## Acceptance

- Only `semantic_timeline.py` defines the loop variant string.
- The focused semantic/report/checker test set passes.
- No cleanup behavior or report visual output changes.

## Result

Completed on 2026-05-10. `semantic_timeline.py` now owns the raw phase names,
canonical surface/inside sequences, display labels, focused action prefixes,
and loop variant strings. The semantic loop, reports, visual-core contract, and
checkers import the vocabulary instead of duplicating it.

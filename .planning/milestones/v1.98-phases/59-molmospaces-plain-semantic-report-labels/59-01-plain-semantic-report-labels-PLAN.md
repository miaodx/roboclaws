# Phase 59 Plan: MolmoSpaces Plain Semantic Report Labels

## Goal

Make Cleanup Artifact Reports use `nav, pick, nav, open?, place` as the primary
semantic subphase vocabulary while keeping object/target/surface/inside as
secondary role detail.

## Tasks

1. Update the semantic timeline display helper so `text` is the plain label.
2. Update report rendering so Robot View Timeline and Cleanup Primitive Gate
   show role detail separately from the primary subphase label.
3. Update the visual-core checker and focused report tests.
4. Record ADR/source-plan/state docs.

## Acceptance Checks

- Semantic rail still includes role detail for object/target/surface/inside.
- Primary report badges/tables do not require `nav/object`-style compound
  labels.
- Raw tool names remain available as raw phase fields.
- Focused ruff and pytest checks pass.

## Result

Completed on 2026-05-10.

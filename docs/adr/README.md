# Architecture Decision Records

Architectural decisions for roboclaws. Each ADR captures one decision —
the context that forced it, the choice made, and the consequences
accepted. Use [Michael Nygard's format](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions):
one decision per file, sequential numbering, explicit status.

## Index

| # | Title | Status |
|---|-------|--------|
| [0001](0001-use-ai2thor-for-phase-1.md) | Use AI2-THOR for Phase 1 | Accepted |
| [0002](0002-defer-isaac-lab-to-phase-3.md) | Defer Isaac Lab integration to Phase 3 | Accepted |

## Adding a new ADR

1. Copy the most recent ADR as a template.
2. Use the next sequential number, zero-padded to 4 digits.
3. Use kebab-case for the title slug.
4. Set status `Accepted` once the decision is taken.
5. Never rewrite a past ADR's decision body — supersede it with a new
   ADR that references the old one (and update the old one's status to
   `Superseded by ADR-NNNN`).
6. Add a row to the index table above.

## When to write an ADR vs. when not to

Write an ADR when:

- The decision is **architecturally significant** — changes the shape of
  the system or constrains future work.
- There are **real alternatives** that were considered and rejected. ADRs
  exist to capture *why not the other thing*.
- A future contributor asking "why did they do X?" would otherwise have
  to dig through commit history or guess.

Don't write an ADR for:

- Implementation details (function signatures, file layout, code style).
  These belong in [`ARCHITECTURE.md`](../../ARCHITECTURE.md) or inline
  code comments.
- Decisions that are obvious from the code (e.g., "use Python" — the
  pyproject.toml already says so).
- Reversible choices that don't constrain anything else.

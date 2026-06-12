# 0055. Discover Fallback Runtime Aliases from KeyError Evidence

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0054 stopped generated fallback proof commands from retrying
upstream/display aliases that fail exact-scene task sampling. That made the
current artifact safe, but it also left no executable alternate aliases.

The warmed Phase 62 proof outputs contain more useful evidence than just the
invalid alias. Each `KeyError` includes the exact-scene runtime valid-name list
from the task sampler. For the same object or target family, that list includes
runtime sibling names such as `book_..._1_1_8`, `shelf_..._1_1_2`,
`bowl_..._1_1_8`, and `sink_..._1_1_5`.

## Decision

The proof-bundle runner may derive additional fallback candidates from prior
proof-result `KeyError` evidence by:

- matching a fallback result back to its source request;
- parsing the invalid alias and valid-name list from blocker messages;
- comparing the invalid alias with the proof's requested object/target field;
- selecting only exact-scene runtime siblings that share the source request's
  runtime alias family.

Discovered aliases remain private runner evidence. The runner manifest and
`report.html` render source request, axis, derived alias, prior fallback result,
invalid alias, and reason. The checker validates discovered-alias evidence when
present.

## Consequences

- The project can turn prior invalid-display-alias failures into a bounded set
  of executable runtime fallback proof commands.
- This is still command-generation evidence, not planner-backed cleanup proof.
  The next local-dev phase must execute the discovered fallback commands and let
  strict proof outputs decide whether any promote cleanup primitive binding.
- The parser is conservative: it derives siblings only from runtime-style names
  that match the same object/target family as the source request alias.

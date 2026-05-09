# 0054. Filter Fallback Aliases to Exact-Scene Runtime Names

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0053 ran warmed generated fallback proofs. The warmup succeeded and the
proofs reached task sampling, but every generated fallback failed with
`KeyError` because fallback generation used upstream/display aliases such as
`Book|surface|8|79`, `ShelvingUnit|2|3`, `Bowl|surface|8|77`, and
`Sink|5|1|0`.

Those aliases are useful private metadata for review, but they are not valid
MolmoSpaces runtime planner names for exact-scene task sampling. The fallback
runner was conflating "known alias metadata" with "safe command argument".

## Decision

Generated fallback proof requests will only use exact-scene runtime-style
planner aliases as executable command inputs. Candidate aliases containing the
upstream/display `|` delimiter are filtered before command generation.

Filtered aliases remain visible in the proof-bundle runner manifest and
`report.html` with source request, axis, alias, and reason. The runner checker
validates that filtered-alias evidence is rendered when present.

## Consequences

- The runner no longer burns local RBY1M/CuRobo execution on aliases already
  known to fail exact-scene task sampling with `KeyError`.
- Candidate alias metadata remains available for diagnosis; only the executable
  fallback command set is narrowed.
- The current exact cleanup artifact has no remaining alternate executable
  aliases after filtering, so fallback selection correctly reports
  `fallback_required` instead of generating invalid proof commands.

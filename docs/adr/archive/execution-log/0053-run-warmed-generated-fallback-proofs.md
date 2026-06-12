# 0053. Run Warmed Generated Fallback Proofs

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0049 executed generated fallback proof requests and found that every proof
timed out at `rby1m_config_import`. ADR-0051 made that timeout stage visible,
and ADR-0052 added an explicit proof-bundle runner warmup step that can run
RBY1M/CuRobo `config_import` once before generated fallback proof commands.

The next useful evidence is not another schema change. It is a local-dev run
that uses the warmed runner path and records whether generated fallback proofs
can get past config import into task sampling, planner-backed execution, planner
views, or cleanup primitive binding promotion.

## Decision

The warmed generated fallback retry will be recorded as a local-dev evidence
phase. It will use the proof-bundle runner with:

- generated fallback request selection enabled;
- `--warmup-rby1m-curobo`;
- an output-local Torch extension cache shared by warmup and proof commands;
- strict proof-output validation through the runner checker.

The result may still be blocked capability. If so, the phase records the exact
stage and blocker rather than treating the warmed retry as success.

## Consequences

- The project gets concrete local evidence for the newly added warmup runner
  path.
- Cleanup primitive readiness still depends on strict generated proof results
  and cleanup binding promotion.
- If the warmed retry remains blocked, the next phase should target the newly
  observed blocker instead of adding more fallback/report plumbing.

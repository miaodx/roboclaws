# 0052. Warm RBY1M CuRobo Before Fallback Proofs

Date: 2026-05-10

## Status

Accepted

## Context

Phase 58 executed generated fallback proof requests locally, but every proof
timed out at `rby1m_config_import`. Phase 60 made that stage visible in the
proof-bundle runner report.

The generated fallback probes all share the same RBY1M/CuRobo runtime setup and
Torch extension cache. Spending each proof's execution budget on first-use
config import/JIT work makes it hard to tell whether any alternate planner alias
can reach task sampling or cleanup primitive binding.

## Decision

The proof-bundle runner will support an explicit RBY1M/CuRobo warmup step before
executing proof commands.

When enabled, the runner records a `config_import` warmup command, run result,
and report path in the proof-bundle manifest. The warmup shares the same
MolmoSpaces Python, embodiment, renderer, memory profile, timeout, and Torch
extension cache settings as the proof commands. If no Torch extension cache is
provided, the runner uses an output-local cache so warmup and proof commands
share one visible cache.

The runner report and checker will render and validate this warmup evidence.

## Consequences

- The next generated fallback retry can separate target runtime warmup/JIT
  progress from proof-command task feasibility.
- Warmup is still local-dev evidence, not strict proof. Generated fallbacks must
  still pass per-proof validation and promote cleanup primitive binding before
  cleanup readiness changes.
- The added manifest section keeps this runtime step reviewable without adding a
  second proof-runner implementation.

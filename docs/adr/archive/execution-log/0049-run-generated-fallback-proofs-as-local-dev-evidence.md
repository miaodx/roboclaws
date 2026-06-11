# 0049. Run Generated Fallback Proofs As Local-Dev Evidence

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0048 introduced private generated fallback proof requests. They are useful
only if local execution can show whether any alternate planner alias escapes the
exact-scene RBY1M task-feasibility blocker and promotes cleanup primitive
binding.

This cannot be a CI-default gate. It depends on the local MolmoSpaces Python
3.11 runtime, CUDA, RBY1M/CuRobo planner dependencies, renderer setup, and
potentially long planner execution. The repo still needs a recorded evidence
artifact so later work is grounded in observed target-runtime behavior rather
than assuming generated fallback requests are feasible.

## Decision

Generated fallback proof execution will be treated as a local-dev evidence
phase. The runner may execute generated fallback probe commands and validate
that proof outputs exist, but strict per-proof status and cleanup primitive
binding promotion remain authoritative.

The phase may conclude with `blocked_capability` evidence. That is still useful
if the runner report classifies the blocker clearly. A blocked fallback proof
does not satisfy planner-backed cleanup replacement.

## Consequences

- Generated fallback request execution stays out of cheap CI/default verify
  gates.
- The proof-bundle runner report becomes the source of truth for which fallback
  aliases were attempted and what each proof output reported.
- If all generated fallbacks remain blocked, the next phase must address the
  specific execution blocker rather than adding more report plumbing.

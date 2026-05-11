# 0051. Surface Fallback Timeout Stage Evidence

Date: 2026-05-10

## Status

Accepted

## Context

Phase 58 executed generated fallback proof requests locally. The raw per-proof
artifacts record worker stage events and `last_worker_stage`, but the
proof-bundle result summary and runner report only show `timeout`.

That forces local operators to inspect individual `run_result.json` and stdout
files before they can tell whether generated fallbacks timed out during
runtime diagnostics, CuRobo JIT/config import, task sampling, or planner
execution.

## Decision

The proof-bundle result summary will surface timeout-stage evidence from each
proof result:

- execution attempted;
- last worker stage;
- compact worker stage event sequence;
- stdout/stderr artifact paths;
- bundle-level timeout and `rby1m_config_import` timeout counts.

The runner report will render those fields next to the proof status, task
feasibility, blockers, and planner views.

## Consequences

- Generated fallback reports become actionable without hand-inspecting every
  proof JSON/stdout file.
- A timeout remains blocked capability. This ADR adds diagnostics only; it does
  not relax proof validation or claim planner-backed cleanup readiness.

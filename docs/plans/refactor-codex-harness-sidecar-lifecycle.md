---
refactor_scope: codex-harness-sidecar-lifecycle
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-04
---

# Refactor Scope: Codex Harness Sidecar Lifecycle

## Status

DONE

## Target

`scripts/molmo_cleanup/run_codex_cleanup_harness8.py` owns the eight-case Codex
cleanup harness lifecycle. The target slice is external-service ownership for
that harness, specifically cleanup MCP and Grounding DINO sidecar behavior.

## Accepted Severities

P0/P1/P2 within this target are in scope. Cross-harness process managers,
operator-console lifecycle, and broader visual-grounding service architecture
are parked.

## Accepted Cleanup Checklist

- [x] Keep cleanup MCP demo-owned: the existing live Codex cleanup runner starts
  one MCP server per demo run and stops it on failure or normal completion.
- [x] Make Grounding DINO a shared singleton for the harness: reuse a healthy
  pre-existing real sidecar, start at most one harness-owned sidecar when absent,
  and stop only the process started by this harness.
- [x] If the DINO port is occupied by an unhealthy or wrong service, classify
  selected DINO-dependent rows as infrastructure failure instead of killing the
  unknown process.
- [x] Persist lifecycle metadata in the harness manifest so weekly reviews can
  see whether DINO was reused, started, stopped, unmanaged, or blocked.
- [x] Keep the public trigger simple through `just agent::harness
  codex-cleanup-harness8 ...`; expose only lifecycle controls that an operator
  can reason about.
- [x] Add focused tests for no-DINO rows, external reuse, harness-owned
  start/stop, and unhealthy bound-port behavior.

## Parked Cross-Seam / Future Ideas

- Add a dedicated visual-grounding service `/healthz` endpoint. The current
  harness probe uses the existing candidates contract to avoid expanding the
  service API during this lifecycle slice.
- Generalize singleton sidecar lifecycle to other visual-grounding families
  such as YOLOE after they become recurring harness dependencies.
- Move all sidecar process ownership into a shared dev-service manager if
  multiple harnesses need the same policy.

## Evidence Ladder

- L1 unit/mock: `tests/unit/molmo_cleanup/test_codex_cleanup_harness8.py`.
- L2 contract: just routing trace for `codex-cleanup-harness8`.
- L6 local harness: one focused DINO row with either a reused or harness-owned
  sidecar before relying on the behavior for regression conclusions.

## Stop Condition

Stop when the accepted checklist is complete, the focused L1/L2 checks pass,
and the docs describe the ownership semantics clearly enough for weekly
architecture hygiene review.

## Execution Log

- 2026-06-04: Started refactor after DINO sidecar infra failures made the
  eight-case harness result ambiguous.
- 2026-06-04: Implemented DINO sidecar lifecycle ownership in the Codex harness,
  added focused unit coverage, and updated the human harness trigger doc.
- 2026-06-04: Verified with focused unit tests, route contract trace,
  compileall, Ruff, and a real readiness probe against the existing
  `127.0.0.1:18880` Grounding DINO sidecar.

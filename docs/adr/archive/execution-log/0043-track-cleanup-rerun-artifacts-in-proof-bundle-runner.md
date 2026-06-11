# 0043. Track Cleanup Rerun Artifacts In Proof Bundle Runner

Date: 2026-05-10

## Status

Accepted

## Context

The planner proof bundle runner can already dry-run proof commands, execute
proof probes with `--execute-probes`, and optionally rerun cleanup with the
generated proof run results. ADR-0042 added a safe default harness for the
dry-run path.

The executed path still leaves an audit gap: the runner manifest and report
record the cleanup rerun command, but they do not name the expected cleanup
rerun `run_result.json` and `report.html` as first-class artifacts. That makes
it too easy to verify proof commands while forgetting to inspect whether the
final cleanup rerun actually produced the visual Cleanup Artifact Report that
can satisfy planner-backed cleanup primitive gates.

## Decision

When `--rerun-cleanup` is used, the proof-bundle runner will record cleanup
rerun artifact metadata in its manifest and render those paths in the runner
report. The runner checker will validate that metadata and can require the
cleanup rerun outputs to exist.

This remains artifact tracking. It does not replace the ADR-0003 cleanup checker
or the strict per-proof planner probe checker.

## Consequences

- Local GPU proof-bundle runs have a visible handoff from generated proof
  artifacts to the final cleanup rerun artifact.
- Operators can fail fast if the runner report names stale or missing cleanup
  rerun outputs.
- Planner-backed cleanup success is still owned by the cleanup artifact checker
  with `--require-planner-backed-cleanup-primitives` and
  `--require-planner-cleanup-bridge-ready`.

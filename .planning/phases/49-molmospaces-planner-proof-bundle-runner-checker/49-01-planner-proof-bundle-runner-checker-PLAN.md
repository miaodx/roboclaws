# 49-01 Planner Proof Bundle Runner Checker Plan

## Goal

Add a focused checker for proof-bundle runner manifests and reports so dry-run
handoffs are gateable before local planner proof execution.

## Status

Planned.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add checker script for runner manifest/report artifacts.
3. [ ] Add tests for valid artifacts and failure modes.
4. [ ] Run focused verification gates.

## Acceptance

- Checker accepts a runner output directory or `proof_bundle_run_manifest.json`.
- Checker validates schema, status, counts, command rows, expected proof
  `run_result.json`, expected proof `report.html`, and `report.html` sections.
- Checker has an opt-in flag to require expected proof outputs to exist.
- Tests cover valid, missing report, missing command metadata, and missing proof
  output when required.

## Verification

- Pending.

## Risks

- The checker must not imply proof success. It validates runner handoff
  integrity only; real proof success remains checked per proof run.

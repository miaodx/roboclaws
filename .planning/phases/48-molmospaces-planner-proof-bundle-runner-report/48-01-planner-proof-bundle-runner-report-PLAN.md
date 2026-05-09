# 48-01 Planner Proof Bundle Runner Report Plan

## Goal

Make the local planner proof bundle runner produce a reviewable `report.html`
alongside its JSON command manifest.

## Status

Planned.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add shared report rendering for proof bundle runner manifests.
3. [ ] Add expected proof report paths to generated command metadata.
4. [ ] Make the runner write and return the report path.
5. [ ] Add dry-run tests for the report and API/CLI payload.
6. [ ] Run focused verification gates.

## Acceptance

- The runner writes `proof_bundle_run_manifest.json` and `report.html`.
- The report shows source cleanup artifact, status, request counts, command
  count, exact probe commands, expected proof `run_result.json` paths, expected
  proof `report.html` paths, and optional cleanup rerun command.
- The runner API and CLI status payload include the report path.
- Dry-run tests do not invoke real RBY1M/CuRobo execution.
- Existing request-manifest and cleanup-report behavior remains unchanged.

## Verification

- Pending.

## Risks

- A command report can be mistaken for proof success. Keep the report language
  explicit: it is command evidence and links to proof outputs, not proof
  validation.

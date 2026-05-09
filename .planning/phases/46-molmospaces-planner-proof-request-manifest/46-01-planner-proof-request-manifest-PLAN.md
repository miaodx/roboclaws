# 46-01 Planner Proof Request Manifest Plan

## Goal

Make ADR-0003 cleanup artifacts emit private, executable planner proof
requests and provide a local runner that can turn them into a real proof bundle.

## Status

Planned.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [ ] Add a planner proof request manifest helper.
3. [ ] Write proof request artifacts from deterministic ADR-0003 cleanup runs.
4. [ ] Write proof request artifacts from ADR-0003 MCP cleanup runs.
5. [ ] Add a local proof-bundle runner with dry-run command evidence and
   opt-in real probe execution.
6. [ ] Add tests for manifest derivation, privacy, and command generation.
7. [ ] Run focused verification gates.

## Acceptance

- Completed ADR-0003 cleanup artifacts include a `planner_proof_requests`
  artifact path.
- Each request records cleanup-facing observed handle/target/source fields and
  planner-facing aliases needed by `run_molmo_planner_manipulation_probe.py`.
- Blocked bindings are recorded with blockers and are not treated as ready
  probe requests.
- Agent View and public trace payloads do not expose planner aliases.
- The runner can dry-run exact probe commands from the manifest.
- The runner can optionally execute probes and rerun cleanup with repeated
  proof results.
- Tests cover the manifest and runner without invoking real GPU/CuRobo.

## Verification

- Pending.

## Risks

- A request manifest generated after cleanup completion can accidentally record
  final source locations instead of original source fixtures. Build from
  semantic substeps and pass `source_receptacle_id` explicitly.
- Real proof generation may still fail due to local RBY1M/CuRobo limits. The
  runner must preserve blockers and command evidence rather than overclaiming.

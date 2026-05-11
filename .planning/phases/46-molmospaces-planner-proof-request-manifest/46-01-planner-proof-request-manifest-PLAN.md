# 46-01 Planner Proof Request Manifest Plan

## Goal

Make ADR-0003 cleanup artifacts emit private, executable planner proof
requests and provide a local runner that can turn them into a real proof bundle.

## Status

Completed 2026-05-10.

## Tasks

1. [x] Add ADR/source-plan documentation and update roadmap/state/context.
2. [x] Add a planner proof request manifest helper.
3. [x] Write proof request artifacts from deterministic ADR-0003 cleanup runs.
4. [x] Write proof request artifacts from ADR-0003 MCP cleanup runs.
5. [x] Add a local proof-bundle runner with dry-run command evidence and
   opt-in real probe execution.
6. [x] Add tests for manifest derivation, privacy, and command generation.
7. [x] Run focused verification gates.

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

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_proof_bundle_from_requests.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- `.venv/bin/python scripts/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --min-generated-mess-count 10 --require-robot-views --require-planner-proof-attachment --accept-blocked-planner-cleanup-primitives --accept-blocked-planner-cleanup-bridge output/molmospaces-planner-cleanup-bridge-readiness/run_result.json`

## Completion Notes

- Added `planner_cleanup_proof_requests_v1` and
  `planner_cleanup_proof_bundle_run_manifest_v1`.
- Deterministic and MCP ADR-0003 cleanup runs now write
  `planner_proof_requests.json` as private artifact metadata.
- The local runner writes a dry-run command manifest by default and only
  executes probes or cleanup reruns when explicitly requested.
- The checker validates new request manifests when present while preserving
  compatibility with older artifacts that predate the manifest.

## Risks

- A request manifest generated after cleanup completion can accidentally record
  final source locations instead of original source fixtures. Build from
  semantic substeps and pass `source_receptacle_id` explicitly.
- Real proof generation may still fail due to local RBY1M/CuRobo limits. The
  runner must preserve blockers and command evidence rather than overclaiming.

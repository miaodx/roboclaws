# MolmoSpaces Planner Proof Request Manifest

**Status:** Completed in GSD Phase 46 on 2026-05-10
**Created:** 2026-05-10
**Source:** CONTEXT.md, ADR-0035, ADR-0037, Phase 45 state
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 44 proved a cleanup artifact can consume a proof bundle, but it does not
tell a local operator how to generate those proofs from a real cleanup run.
Without a durable manifest, the next real multi-proof run requires manually
matching observed handles, target fixtures, source fixtures, planner aliases,
and `run_molmo_planner_manipulation_probe.py` flags.

## Decision

Emit a private planner proof request manifest from ADR-0003 cleanup runs and
add a local runner that turns the manifest into exact planner probe commands.

This phase should:

- add a `planner_cleanup_proof_requests_v1` manifest;
- derive requests from semantic cleanup substeps using the existing private
  observed-handle planner binding;
- write the manifest beside the cleanup artifact and reference it from
  `run_result.json`;
- keep the manifest out of Agent View and public trace payloads;
- add a local runner that reads the manifest, writes command evidence, defaults
  to dry-run, and can opt into real probe execution;
- optionally rerun the cleanup harness with generated proof results as repeated
  `--planner-proof-run-result` inputs;
- test manifest derivation and command generation without requiring GPU/CuRobo.

## Non-Goals

- Do not run a full RBY1M/CuRobo multi-proof bundle in CI.
- Do not expose planner aliases to Agent View.
- Do not relax proof binding, strict proof, or cleanup bridge requirements.
- Do not replace Phase 44 proof-bundle consumption.

## Deliverables

- ADR-0037 and this source plan.
- `.planning/phases/46-molmospaces-planner-proof-request-manifest/46-01-planner-proof-request-manifest-PLAN.md`.
- Manifest helper module and tests.
- ADR-0003 deterministic and MCP artifact integration.
- Local proof-bundle runner script and tests.
- Updated docs/state/roadmap/context.

## Verification Plan

- `uv run ruff check roboclaws/molmo_cleanup/planner_proof_requests.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `uv run ruff format --check roboclaws/molmo_cleanup/planner_proof_requests.py examples/molmospaces_realworld_cleanup.py roboclaws/molmo_cleanup/realworld_mcp_server.py scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py tests/test_molmospaces_realworld_cleanup.py tests/test_molmo_realworld_mcp_server.py`
- Existing real ADR-0003 visual artifact checker remains valid.

## Completion

Phase 46 shipped the manifest helper, deterministic/MCP artifact integration,
dry-run local runner, and focused tests. The implementation also extends the
ADR-0003 artifact checker to validate request manifests when present without
failing older artifacts that predate the manifest.

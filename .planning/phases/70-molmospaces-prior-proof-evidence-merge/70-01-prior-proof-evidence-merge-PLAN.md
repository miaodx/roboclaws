# Phase 70 Plan: MolmoSpaces Prior Proof Evidence Merge

## Goal

Let the proof-bundle runner combine multiple prior proof-bundle manifests so
runtime alias discovery and failed-candidate memory are selected together.

## Tasks

1. Extend the runner CLI and callable helper to accept multiple prior proof
   bundle manifests.
2. Merge prior proof results, discovered runtime aliases, filtered aliases, and
   filtered alias pairs into one selection input.
3. Add focused runner tests for multi-manifest merge behavior and
   single-manifest compatibility.
4. Dry-run the current cleanup artifact with merged prior evidence and verify
   the generated runner report/checker output.
5. Update `CONTEXT.md`, the parent MolmoSpaces plan, roadmap/state, and ADR
   evidence.

## Acceptance Checks

- Multi-manifest prior input carries discovered aliases and filtered pairs at
  the same time.
- Known task-feasibility-blocked pairs are not regenerated when they appear in
  any supplied prior manifest.
- The runner report shows the merged evidence rows.
- Focused tests and the proof-bundle runner checker pass.

## Result

Completed on 2026-05-10.

The runner now accepts multiple prior proof-bundle manifests and merges their
proof results plus fallback-generation memory before request selection. The
Phase 70 dry-run consumed Phase 62 and Phase 68 manifests together and produced
zero generated commands while rendering merged discovered aliases, filtered
aliases, and filtered pairs.

## Validation

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase70-prior-evidence-merge-dry-run`

## Status

Complete.

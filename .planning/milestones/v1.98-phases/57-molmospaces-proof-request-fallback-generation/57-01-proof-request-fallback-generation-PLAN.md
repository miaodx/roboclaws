# Phase 57 Plan: MolmoSpaces Proof Request Fallback Generation

## Goal

Add bounded private fallback proof request generation so prior
task-feasibility-blocked proof requests can produce alternate exact-scene probe
commands instead of ending only at `fallback_required`.

## Inputs

- Source plan:
  `docs/retrospectives/plans/molmospaces-proof-request-fallback-generation.md`
- ADR:
  `docs/adr/0048-generate-private-fallback-proof-requests.md`
- Prior implementation:
  `roboclaws/molmo_cleanup/planner_proof_requests.py`
  `scripts/run_molmo_planner_proof_bundle_from_requests.py`
  `roboclaws/molmo_cleanup/report.py`
  `scripts/check_molmo_planner_proof_bundle_runner_result.py`

## Tasks

1. Extend proof request selection with a fallback-generation schema and helper
   that creates private generated requests from observed-handle planner alias
   candidates.
2. Add runner CLI flags for fallback generation and alias-attempt limits.
3. Include generated fallback requests in command generation without mutating
   the source cleanup artifact.
4. Render generated fallback requests in the proof-bundle runner report.
5. Extend the checker and focused tests for generation, CLI wiring, report
   rendering, and generated command validation.
6. Update CONTEXT, ADR index, roadmap, and GSD state after validation.

## Acceptance Checks

- Focused unit tests pass for planner proof requests, runner CLI, report
  rendering, and runner checker.
- A dry-run runner artifact can be generated with fallback requests enabled and
  accepted by the checker.
- Generated fallback requests remain private runner/report evidence and do not
  alter Agent View or original cleanup outputs.

## Result

Implemented. The proof-bundle runner can now generate private fallback proof
requests from prior task-feasibility-blocked source requests, select them for
dry-run command generation, render them in the runner report, and validate them
with the runner checker. The generated requests preserve cleanup-facing object,
target, source, and semantic tool fields while varying private planner aliases.

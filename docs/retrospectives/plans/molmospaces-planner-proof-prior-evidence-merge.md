# MolmoSpaces Planner Proof Prior Evidence Merge

**Status:** Completed on 2026-05-10
**ADR:** `docs/adr/0061-merge-prior-planner-proof-evidence.md`
**GSD phase:** `.planning/milestones/v1.98-phases/70-molmospaces-prior-proof-evidence-merge/`

## Problem

The planner proof-bundle runner can consume one prior manifest at a time. The
current fallback path needs evidence from multiple prior artifacts: older
`KeyError` runs provide runtime alias discovery, while newer execution and
carry-forward runs provide non-root alias and task-feasibility filters.

This creates an avoidable local-dev hazard. Selecting the older manifest can
generate commands for already-failed target-side pairs; selecting only the
latest manifest can hide why the candidate pool is exhausted.

## Scope

- Allow the runner CLI to accept multiple `--prior-proof-bundle-manifest`
  values.
- Merge prior proof results and fallback-generation memory before request
  selection.
- Preserve discovered runtime aliases, filtered aliases, and filtered pairs in
  the merged prior summary.
- Keep single-manifest behavior backward-compatible.
- Dry-run the current cleanup artifact with Phase 62 plus newer failed-candidate
  manifests and verify the report shows the merged prior evidence.

## Acceptance Criteria

- Passing more than one prior manifest prevents generated commands for known
  filtered alias pairs while still carrying discovered runtime aliases.
- The runner report renders merged discovered aliases, filtered aliases, and
  filtered pairs.
- Focused unit tests cover single-manifest compatibility and multi-manifest
  merge behavior.
- The dry-run passes `check_molmo_planner_proof_bundle_runner_result.py`.

## Non-Goals

- Executing another local RBY1M/CuRobo proof bundle.
- Deriving new pickup root-body aliases from upstream scene metadata.
- Changing Cleanup Artifact Report visual core ordering.

## Result

The proof-bundle runner now accepts multiple
`--prior-proof-bundle-manifest` values and merges prior proof results,
discovered aliases, filtered aliases, and filtered pairs before request
selection.

The Phase 70 dry-run combined Phase 62 KeyError evidence with Phase 68
failed-candidate memory. It generated zero proof commands, kept
`fallback_required=true`, and rendered the merged discovered/filtered evidence
in `report.html`.

## Validation

- `uv run ruff check scripts/run_molmo_planner_proof_bundle_from_requests.py tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_run_molmo_planner_proof_bundle_from_requests.py`
- `.venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py output/debug-real-binding/run_result.json --output-dir output/debug-phase70-prior-evidence-merge-dry-run --runner-python .venv/bin/python --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --embodiment rby1m --probe-mode execute --steps 1 --timeout-s 900 --renderer-device-id 0 --rby1m-curobo-memory-profile low --prior-proof-bundle-manifest output/debug-phase62-warmed-fallback-execute/proof_bundle_run_manifest.json --prior-proof-bundle-manifest output/debug-phase68-filter-carry-forward-dry-run/proof_bundle_run_manifest.json --exclude-task-feasibility-blocked --generate-fallback-requests --fallback-alias-limit 4`
- `.venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py output/debug-phase70-prior-evidence-merge-dry-run`

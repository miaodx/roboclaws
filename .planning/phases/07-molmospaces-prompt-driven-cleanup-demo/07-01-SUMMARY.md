# Phase 7 Plan 01 Summary - Public Cleanup Policy

**Commit:** `fb5f705 feat: add MolmoSpaces public cleanup policy`
**Status:** Complete

## Changes

- Added `roboclaws/molmo_cleanup/policy.py`.
- Added `tests/test_molmo_cleanup_policy.py`.
- The policy consumes task text plus public object/receptacle payloads and
  infers cleanup actions without `private_manifest`, `valid_receptacle_ids`, or
  scorer fields.

## Verification

- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_cleanup_policy.py`
- Pre-commit fast non-integration pytest subset passed.

## Boundary

The policy is a deterministic public heuristic, not a real VLM/coding-agent
policy. It closes the private-manifest planner leak in the harness path while
keeping primitive execution labeled `api_semantic`.

# MolmoSpaces Grasp Pose Policy Cache

**Status:** Completed under GSD Phase 122 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0112, Phase 121 initial-contact result, preserved Phase 119 `Bread_1` candidates, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 121 found a concrete pose policy that succeeds for the preserved
`Bread_1` candidates, but it did not generate or install a loader cache. The
implementation gap was to apply that policy without creating a second,
unvalidated cache/install path.

## Decision

Add a pose-policy cache runner that reuses the initial-contact MuJoCo probe in
cache-output mode and then routes the generated NPZ through the shared
grasp-cache validation/install helper.

The runner accepts either:

- an initial-contact result with a successful `best_variant`; or
- explicit `--approach-sign`, `--approach-distance`, and `--settle-steps`.

Install remains explicit via `--install`, and install only happens after the
generated NPZ validates as non-empty.

## Non-Goals

- Do not patch upstream MolmoSpaces `perturbations_test.py` in place.
- Do not make every object cache-valid; this slice validates the local
  `Bread_1` droid path.
- Do not claim final cleanup readiness until a later proof/cleanup rerun uses
  the newly valid cache.

## Acceptance Criteria

- The runner consumes the ready generation preflight and preserved
  `Bread_1_grasps.json`.
- The selected policy comes from the Phase 121 best variant.
- The generated NPZ validates with nonzero transforms before install.
- If install is requested, the installed loader cache validates and the
  availability preflight returns `ready`.
- Focused lint, format, and tests pass.

## Result

Complete.

The local run selected `sign_1_dist_0.8_settle_1` from the Phase 121 diagnostic
result. It processed 24 candidates, generated 9 successful transforms, validated
the generated NPZ, installed it to the droid loader cache, and revalidated the
installed file with 9 transforms. The installed droid cache availability
preflight returned `ready`.

Artifacts:

- `output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json`
- `output/debug-phase122-grasp-pose-policy-cache/report.html`

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_pose_policy_cache_generation.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --initial-contact-result output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --output-dir output/debug-phase122-grasp-pose-policy-cache --output output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --max-candidates 0 --timeout-s 900 --install`

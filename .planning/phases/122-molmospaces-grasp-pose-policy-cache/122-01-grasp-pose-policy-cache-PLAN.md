# Phase 122 Plan: MolmoSpaces Grasp Pose Policy Cache

## Goal

Apply the validated Phase 121 positive-standoff pose policy to the actual
MolmoSpaces droid grasp-cache path, while preserving one validation/install
contract for generated loader NPZ files.

## Context

Phase 121 proved that the preserved `Bread_1` candidates can produce successful
contacts when the approach starts on the positive side of the grasp axis at a
larger standoff. The best policy, `sign_1_dist_0.8_settle_1`, succeeded for
9/24 candidates with zero initial displacement. Cache generation still needed a
repo-owned path that writes a non-empty NPZ and reuses the same install gate as
the existing grasp-cache runner.

## Scope

- Extend the initial-contact MuJoCo probe with optional cache-output support.
- Add `roboclaws/molmo_cleanup/grasp_pose_policy_cache.py`.
- Add `scripts/run_molmospaces_grasp_pose_policy_cache_generation.py`.
- Reuse the shared generated-cache validation and post-install availability
  check from `grasp_cache_generation.py`.
- Add a shared-style report renderer and focused tests.
- Run the local cache generation/install on the preserved Phase 119 candidates.
- Record ADR-0113, source plan, `CONTEXT.md`, and `.planning/STATE.md`.

## Acceptance Criteria

- The runner consumes the ready generation preflight and preserved candidate
  grasp JSON.
- The selected pose policy comes from the Phase 121 initial-contact best
  variant unless explicit CLI policy values are supplied.
- Generated cache validation reports a non-empty NPZ before install.
- Installed cache validation and availability preflight report ready when
  `--install` is used.
- Focused lint, format, and tests pass.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_pose_policy_cache_generation.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --initial-contact-result output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --output-dir output/debug-phase122-grasp-pose-policy-cache --output output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --max-candidates 0 --timeout-s 900 --install`

## Result

Complete on 2026-05-10.

The local run processed 24 candidates with the Phase 121
`sign_1_dist_0.8_settle_1` policy and produced 9 valid transforms. The generated
NPZ validated before install, the droid loader target changed from empty to
valid with 9 transforms, and the post-install availability preflight returned
`ready`.

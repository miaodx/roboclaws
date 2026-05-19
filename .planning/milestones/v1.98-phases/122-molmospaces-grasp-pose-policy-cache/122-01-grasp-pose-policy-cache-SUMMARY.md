# Phase 122 Summary: MolmoSpaces Grasp Pose Policy Cache

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `122-01-grasp-pose-policy-cache-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Apply the validated Phase 121 positive-standoff pose policy to the actual
MolmoSpaces droid grasp-cache path, while preserving one validation/install
contract for generated loader NPZ files.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The local run processed 24 candidates with the Phase 121
`sign_1_dist_0.8_settle_1` policy and produced 9 valid transforms. The generated
NPZ validated before install, the droid loader target changed from empty to
valid with 9 transforms, and the post-install availability preflight returned
`ready`.

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_pose_policy_cache_generation.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --initial-contact-result output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --output-dir output/debug-phase122-grasp-pose-policy-cache --output output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --max-candidates 0 --timeout-s 900 --install`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

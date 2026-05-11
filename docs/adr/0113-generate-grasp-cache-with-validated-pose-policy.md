# 0113. Generate Grasp Cache with Validated Pose Policy

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0112 turned the manual `Bread_1` initial-contact sweep into reproducible
evidence. The best policy, `sign_1_dist_0.8_settle_1`, produced 9/24 successful
contacts with zero initial object displacement, while the upstream-sign variants
remained zero-success.

The next gap was architectural: applying that policy through a separate script
would create another cache path and another install rule. The droid loader cache
must instead be generated through the same preflight and validated install
contract used by the existing grasp-cache runner.

## Decision

Add a pose-policy cache generation runner.

The runner:

- consumes the ready grasp-generation preflight, preserved candidate grasp JSON,
  and either the Phase 121 initial-contact result or an explicit pose policy;
- reuses the same generated MuJoCo probe as the initial-contact diagnostics,
  adding an optional cache-output mode that writes successful object-relative
  TCP transforms into a loader-compatible NPZ;
- reuses the shared generated-cache validation and post-install availability
  checks before treating an installed droid cache as ready;
- renders the policy, generated transforms, install-before/after validation,
  and command result in a shared HTML report.

## Consequences

- The local droid `Bread_1` loader cache moved from empty to valid: 9 generated
  transforms were validated before install, copied into the loader cache, and
  revalidated after install.
- Initial-contact diagnostics and pose-policy cache generation now share one
  probe implementation for the MuJoCo approach/close mechanics.
- This validates the loader cache artifact only. A later slice still needs to
  rerun the MolmoSpaces cleanup/proof flow against the newly valid cache.

## Evidence

Implemented in Phase 122 on 2026-05-10.

Artifacts:

- `output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json`
- `output/debug-phase122-grasp-pose-policy-cache/report.html`

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/grasp_pose_policy_cache.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_pose_policy_cache_generation.py tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_pose_policy_cache.py tests/test_molmo_grasp_initial_contact_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_pose_policy_cache_generation.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --initial-contact-result output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --output-dir output/debug-phase122-grasp-pose-policy-cache --output output/debug-phase122-grasp-pose-policy-cache/pose_policy_cache_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --max-candidates 0 --timeout-s 900 --install`

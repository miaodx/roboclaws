# Phase 121 Summary: MolmoSpaces Grasp Initial Contact Diagnostics

Completed: 2026-05-10
Backfilled: 2026-05-11
Source plan: `121-01-grasp-initial-contact-diagnostics-PLAN.md`

## What Changed

This closure summary was backfilled from the existing phase plan because the
older hybrid pipeline marked the phase complete inside the plan but did not
write a separate GSD summary artifact.

Recorded phase goal:

Turn the manual `Bread_1` initial-contact/approach sweep into reusable repo
evidence so the next cache-generation slice can apply a validated pose policy
instead of guessing why upstream perturbation filtering saves zero transforms.

## Completed Tasks

- The source plan records completion in its Status/Result section.

## Recorded Status

Complete on 2026-05-10.

The local diagnostic produced 24 candidates, 30 approach variants, and nine
nonzero-success variants. The best variant was `sign_1_dist_0.8_settle_1` with
9/24 successes and zero initial displacement. Upstream-sign variants stayed
zero-success.

## Evidence

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_initial_contact_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --output-dir output/debug-phase121-grasp-initial-contact-diagnostics --output output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --timeout-s 900`

## Backfill Note

This file reconstructs the missing GSD closure artifact from the already
committed plan evidence. It does not add fresh simulator, VLM, Docker, GPU, or
local-dev execution beyond what the source plan records.

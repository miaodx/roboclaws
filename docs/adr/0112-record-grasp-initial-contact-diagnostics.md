# 0112. Record Grasp Initial Contact Diagnostics

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0110 showed that `Bread_1` grasp candidate generation is working: the
bounded diagnostic preserved 24 generated candidates, but all perturbation
filter variants saved zero transforms. A manual MuJoCo probe narrowed the
failure further: the upstream initial approach path can start the open gripper
in contact with the object, and longer open-settle windows can eject the object
before the close phase.

That result needed to become a reusable artifact rather than another one-off
terminal transcript.

## Decision

Add a Grasp Initial Contact Diagnostics runner and report.

The runner:

- consumes the ready grasp-generation preflight plus preserved candidate grasp
  JSON;
- runs a bounded MuJoCo sweep over approach sign, approach standoff distance,
  and open-settle steps;
- records initial contact counts, initial object displacement, final left/right
  gripper contact success, and successful candidate indices;
- renders the sweep and best variant in a shared-style HTML report;
- keeps cache installation blocked until a later slice deliberately applies a
  validated pose policy to the actual filtered cache path.

## Consequences

- The zero-transform cache blocker is no longer opaque: the upstream-sign
  approach path remains zero-success, while positive-sign larger standoffs
  produce nonzero final contacts.
- The best local diagnostic variant for the preserved 24 `Bread_1` candidates
  is `sign_1_dist_0.8_settle_1`, with 9/24 successes and zero initial object
  displacement.
- This is diagnostic evidence only. It does not install a loader cache and does
  not claim the upstream perturbation filter has been fixed.

## Evidence

Implemented in Phase 121 on 2026-05-10.

Artifacts:

- `output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json`
- `output/debug-phase121-grasp-initial-contact-diagnostics/report.html`

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_initial_contact_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --output-dir output/debug-phase121-grasp-initial-contact-diagnostics --output output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --timeout-s 900`

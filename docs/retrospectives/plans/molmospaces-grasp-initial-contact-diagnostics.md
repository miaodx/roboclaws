# MolmoSpaces Grasp Initial Contact Diagnostics

**Status:** Completed under GSD Phase 121 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0110, manual MuJoCo contact sweep, preserved Phase 119 `Bread_1` candidates, `CONTEXT.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

Phase 119 proved that candidate generation is not the blocker: 24 valid
`Bread_1` grasp candidates exist, but the perturbation filter still saves zero
transforms. A manual probe showed why at least part of that happens: the
upstream approach sign and short standoff can place the open gripper in contact
with the object before the approach/close phase, and longer open-settle windows
can eject the object.

The next slice needs reusable evidence for the initial-contact/pose policy
rather than another temporary terminal script.

## Decision

Add a repo-owned initial-contact diagnostic runner.

The runner sweeps:

- approach sign: upstream `-1` and alternate `+1`;
- approach standoff distance: `0.1`, `0.2`, `0.3`, `0.5`, `0.8`;
- open-settle steps: `1`, `50`, `500`.

For each variant, it records candidate count, success count, initial contact
count, initial object displacement, and successful candidate indices. The
report highlights the best variant and sample contact rows.

## Non-Goals

- Do not install or synthesize a droid loader grasp cache.
- Do not patch upstream `perturbations_test.py` yet.
- Do not claim planner-backed cleanup readiness.

## Acceptance Criteria

- The runner consumes the existing ready generation preflight and preserved
  `Bread_1_grasps.json`.
- The local report shows the upstream-sign variants remain zero-success.
- At least one alternate approach variant has nonzero success.
- Focused lint, format, and tests pass.

## Result

Complete.

The local diagnostic produced `ready` status with 24 candidates and 30 variants.
Nine variants had nonzero success. The best variant was
`sign_1_dist_0.8_settle_1`, with 9/24 successful candidates, zero initial
contacts, and zero initial displacement. Upstream-sign variants remained
zero-success.

Artifacts:

- `output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json`
- `output/debug-phase121-grasp-initial-contact-diagnostics/report.html`

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_initial_contact_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --output-dir output/debug-phase121-grasp-initial-contact-diagnostics --output output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --timeout-s 900`

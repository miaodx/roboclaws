# Phase 121 Plan: MolmoSpaces Grasp Initial Contact Diagnostics

## Goal

Turn the manual `Bread_1` initial-contact/approach sweep into reusable repo
evidence so the next cache-generation slice can apply a validated pose policy
instead of guessing why upstream perturbation filtering saves zero transforms.

## Context

Phase 119 preserved candidate and filter artifacts and showed candidate
generation succeeds while all filter variants save zero transforms. The manual
probe showed that upstream-style initial open-settle can collide with and eject
`Bread_1`, while a positive approach direction at larger standoff produces
nonzero final contacts.

## Scope

- Add `roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py`.
- Add `scripts/run_molmospaces_grasp_initial_contact_diagnostics.py`.
- Add a report renderer for the initial-contact sweep.
- Add focused unit tests for variant summarization and report rendering.
- Run the local diagnostic on the preserved Phase 119 `Bread_1` candidates.
- Record ADR-0112, source plan, `CONTEXT.md`, and `.planning/STATE.md`.

## Acceptance Criteria

- The diagnostic consumes the ready generation preflight and preserved
  candidate grasp JSON.
- The report renders all approach variants and highlights a best variant.
- The local result shows the upstream-sign variants remain zero-success and at
  least one alternate approach variant has nonzero success.
- No generated cache is installed.
- Focused lint, format, and tests pass.

## Verification

- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_initial_contact_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_initial_contact_diagnostics.py tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_grasp_initial_contact_diagnostics.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_initial_contact_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --candidate-grasps-path output/debug-phase119-grasp-filter-diagnostics/grasp_filter_diagnostics/Bread_1/Bread_1_grasps.json --output-dir output/debug-phase121-grasp-initial-contact-diagnostics --output output/debug-phase121-grasp-initial-contact-diagnostics/initial_contact_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --timeout-s 900`

## Result

Complete on 2026-05-10.

The local diagnostic produced 24 candidates, 30 approach variants, and nine
nonzero-success variants. The best variant was `sign_1_dist_0.8_settle_1` with
9/24 successes and zero initial displacement. Upstream-sign variants stayed
zero-success.

# Phase 119 Verification: 119-01 Grasp Filter Diagnostics

Date: 2026-05-11
Source plan: `119-01-grasp-filter-diagnostics-PLAN.md`
Backfill status: reconstructed from existing phase evidence.

## Verification Scope

This verification artifact repairs the missing GSD closeout file for Phase
119. It is based on the source plan's embedded status, tasks, acceptance
criteria, and recorded verification evidence. No fresh phase execution was run
as part of this backfill.

## Acceptance Evidence From Plan

- See the source phase plan for acceptance criteria.

## Recorded Verification Evidence

- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `.venv/bin/ruff check roboclaws/molmo_cleanup/grasp_cache_generation.py roboclaws/molmo_cleanup/grasp_filter_diagnostics.py roboclaws/molmo_cleanup/report.py scripts/run_molmospaces_grasp_filter_diagnostics.py tests/test_grasp_filter_diagnostics.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_grasp_filter_diagnostics.py tests/test_grasp_cache_generation.py tests/test_molmo_cleanup_report.py`
- `.venv/bin/python scripts/run_molmospaces_grasp_filter_diagnostics.py --preflight-manifest output/debug-phase117-grasp-generation-prereqs/proof_bundle_run_manifest.json --output-dir output/debug-phase119-grasp-filter-diagnostics --output output/debug-phase119-grasp-filter-diagnostics/filter_diagnostics_result.json --molmospaces-python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --sample-size 24 --num-samples 256 --num-workers 4 --approach-steps 30 --shake-steps 10 --timeout-s 600`

## Artifact Integrity Checks

- Source plan exists: `119-01-grasp-filter-diagnostics-PLAN.md`.
- Source plan contains a completion date or result marker: `2026-05-10`.
- Backfilled summary exists: `119-01-grasp-filter-diagnostics-SUMMARY.md`.
- Backfilled verification exists: `119-VERIFICATION.md`.

## Verdict

GSD artifact closure is repaired for Phase 119 based on the existing
committed phase evidence. Treat this as a documentation repair. If a future
claim depends on real MolmoSpaces, real RBY1M/CuRobo, real VLM, Docker, GPU,
or API-key behavior, rerun the recorded commands or a current equivalent before
using the phase as fresh runtime proof.

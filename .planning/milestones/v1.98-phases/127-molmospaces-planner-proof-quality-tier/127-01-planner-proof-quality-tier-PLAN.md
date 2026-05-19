# Phase 127 Plan: MolmoSpaces Planner Proof Quality Tier

## Goal

Make attached planner proof strength explicit and reusable across attachments,
proof bundles, reports, and ADR-0003 checker gates.

## Tasks

1. Add a reusable planner proof quality module that classifies one-step motion,
   multi-step motion, and containment-level proof evidence.
2. Embed quality evidence in planner proof attachments and bundle summaries.
3. Render proof quality in cleanup reports next to attached planner proof views.
4. Add checker flags for requiring proof quality and minimum executed steps.
5. Add focused tests for quality classification, report rendering, and checker
   enforcement.
6. Record ADR-0118, this phase plan, the pilot plan update, `CONTEXT.md`, and
   `.planning/STATE.md`.

## Acceptance Checks

- Current strict attachments still validate.
- One-step proofs classify as `one_step_motion`.
- Multi-step proofs classify as `multi_step_motion`.
- Report HTML contains `Proof Quality` for single and bundled attached proofs.
- Checker enforcement rejects a proof below the requested step horizon.
- Focused lint, format, and pytest gates pass.

## Result

Complete on 2026-05-10.

`roboclaws/molmo_cleanup/planner_proof_quality.py` is now the shared interface
for proof-strength classification. Attachments and bundles carry reusable
quality evidence, reports render it, and
`scripts/check_molmo_realworld_cleanup_result.py` can require both proof
quality and a minimum executed-step horizon.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof_bundle tests/test_check_molmo_realworld_cleanup_result.py::test_checker_can_require_attached_planner_proof tests/test_check_molmo_realworld_cleanup_result.py::test_checker_rejects_attached_proof_below_min_steps`

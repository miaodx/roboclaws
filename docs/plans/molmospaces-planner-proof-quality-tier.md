# MolmoSpaces Planner Proof Quality Tier

**Status:** Completed under GSD Phase 127 on 2026-05-10
**Created:** 2026-05-10
**Source:** ADR-0117, `CONTEXT.md`, `docs/plans/molmospaces-manipulation-spike.md`
**Workflow:** `hybrid-phase-pipeline`

## Problem

The ADR-0003 cleanup report now consumes a real exact RBY1M/CuRobo proof for
one bound object, but the proof strength was implicit. Attachments, proof
bundles, reports, and checkers each interpreted low-level fields like
`steps_executed` directly.

That makes the architecture brittle. The current Phase 125 proof should be
described as one-step planner motion, while future work may require multi-step
pick/place progress or full containment before claiming stronger cleanup
readiness.

## Decision

Introduce a reusable Planner Proof Quality Evidence module and use it at every
planner-proof consumer:

- attachment creation embeds `proof_quality`;
- proof bundles aggregate `proof_quality_summary`;
- cleanup reports render `Proof Quality`;
- the ADR-0003 checker can require proof quality and a minimum step horizon.

## Non-Goals

- Do not change the semantic cleanup loop.
- Do not re-execute MolmoSpaces planner probes in this phase.
- Do not claim full planner-backed cleanup from a one-step proof.
- Do not make containment required by default before the next proof-generation
  slice exists.

## Acceptance Criteria

- Current proof attachments classify as `one_step_motion` or
  `multi_step_motion` from recorded evidence.
- Proof bundles summarize proof quality tiers.
- Cleanup reports render `Proof Quality` near planner initial/final views.
- The ADR-0003 checker can enforce proof quality and minimum executed steps.
- Focused lint, format, and pytest gates pass.

## Result

Complete.

The new `planner_proof_quality` module classifies proof strength behind one
interface. Reports now show proof strength next to the attached planner proof
views, and checker flags can distinguish a one-step proof from a stricter
multi-step gate.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof_bundle tests/test_check_molmo_realworld_cleanup_result.py::test_checker_can_require_attached_planner_proof tests/test_check_molmo_realworld_cleanup_result.py::test_checker_rejects_attached_proof_below_min_steps`

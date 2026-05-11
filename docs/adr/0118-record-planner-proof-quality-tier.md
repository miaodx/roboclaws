# 0118. Record Planner Proof Quality Tier

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0117 consumed the Phase 125 exact RBY1M/CuRobo proof in the ADR-0003
cleanup primitive path. That proof is valuable, but it is intentionally narrow:
it executed one planner-backed robot-motion step with nonzero robot-state
movement, carried an exact cleanup binding, and did not prove full pick/place
completion or final cleanup containment.

The code had a shallow proof-strength interface. Attachments, proof bundles,
cleanup reports, and checker gates each read `steps_executed` and
`max_abs_qpos_delta` directly. That made it easy for reports to show proof
views while still leaving the proof strength implicit.

## Decision

Add reusable **Planner Proof Quality Evidence** behind one module:
`roboclaws/molmo_cleanup/planner_proof_quality.py`.

The module classifies attached planner proofs into explicit quality tiers:

- `one_step_motion`;
- `multi_step_motion`;
- `containment_proven`;
- lower diagnostic tiers when execution or motion is not proven.

Planner proof attachments now embed `proof_quality`. Proof bundles now carry a
`proof_quality_summary`. Cleanup reports render `Proof Quality` alongside the
planner initial/final views. The ADR-0003 checker can require proof quality
evidence and a minimum executed-step horizon with:

- `--require-planner-proof-quality`;
- `--require-planner-proof-min-steps N`.

Existing strict proof validation remains backward compatible: older attachments
can still be classified from their recorded `steps_executed` and
`max_abs_qpos_delta`.

## Consequences

- The Phase 125 proof can be displayed honestly as `one_step_motion`, not as an
  implied full pick/place or containment proof.
- Future multi-step or containment work can tighten the checker gate without
  changing every report and caller.
- The proof-quality module is a deeper module: reports, bundles, attachments,
  and checkers all cross one interface instead of duplicating tier logic.
- Full planner-backed cleanup still requires exact proof coverage and stricter
  cleanup primitive evidence. This ADR only records proof strength.

## Evidence

Implemented in Phase 127 on 2026-05-10.

Verification:

- `.venv/bin/ruff check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `.venv/bin/ruff format --check roboclaws/molmo_cleanup/planner_proof_quality.py roboclaws/molmo_cleanup/planner_proof_attachment.py roboclaws/molmo_cleanup/planner_proof_bundle.py roboclaws/molmo_cleanup/report.py scripts/check_molmo_realworld_cleanup_result.py tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py tests/test_check_molmo_realworld_cleanup_result.py`
- `./scripts/run_pytest_standalone.sh -q tests/test_molmo_planner_proof_attachment.py tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof tests/test_molmo_cleanup_report.py::test_cleanup_report_renders_attached_planner_proof_bundle tests/test_check_molmo_realworld_cleanup_result.py::test_checker_can_require_attached_planner_proof tests/test_check_molmo_realworld_cleanup_result.py::test_checker_rejects_attached_proof_below_min_steps`

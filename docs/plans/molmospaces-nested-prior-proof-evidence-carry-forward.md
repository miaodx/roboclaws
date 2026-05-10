# MolmoSpaces Nested Prior Proof Evidence Carry-Forward

**Status:** Completed for Phase 88 on 2026-05-10
**Parent plan:** `docs/plans/molmospaces-manipulation-spike.md`
**ADR:** `docs/adr/0079-carry-forward-nested-prior-proof-evidence.md`

## Goal

Let a later proof-bundle runner manifest stand alone as prior evidence while
preserving older nested proof evidence, blocker detail, and report visibility.

## Problem

Phase 86 added `prior_proof_result_summary` to runner manifests and reports.
Phase 87 then produced a new manifest with both current proof results and
nested prior evidence. A later run that loaded only that Phase87 manifest could
consume the current result summary, but risked dropping the nested Phase81
evidence that had been carried forward into the Phase87 report.

That would recreate the multi-implementation problem the report work has been
removing: selection memory would depend on which artifact generation hop was
used instead of one normalized proof-evidence interface.

## Scope

- Load nested `prior_proof_result_summary` from prior proof-bundle manifests.
- Merge nested prior evidence with the prior manifest's current
  `proof_result_summary`.
- Preserve cleanup object/target IDs and grasp-feasibility blocker detail when
  excluded requests are converted back into prior proof results.
- Add regression coverage for nested prior carry-forward and blocker-detail
  preservation.
- Validate a dry-run that uses the Phase87 manifest as the only prior input.

## Non-Goals

- Do not broaden fallback candidate discovery in this slice.
- Do not execute another real proof candidate.
- Do not change the shared report renderer or create a second report shape.
- Do not claim planner-backed cleanup readiness from carried blocker evidence.

## Acceptance Criteria

- A prior proof-bundle manifest's nested `prior_proof_result_summary` is merged
  before request selection.
- The runner excludes both known source requests when the Phase87 manifest is
  used as the only prior input.
- The generated report renders both Phase81 and Phase87 evidence under `Prior
  Proof Evidence`.
- Excluded-request rows retain `object_id`, `target_receptacle_id`,
  `task_feasibility_blocker_kind`, and blocker detail.
- Focused lint, format, pytest, and manual checker validation pass.

## Result

Implemented.

The Phase88 dry-run at
`output/debug-phase88-nested-prior-carry-forward-dry-run/` used the Phase87
proof-bundle manifest as the only prior proof-bundle input. The runner merged
nested Phase81 evidence with Phase87's current proof result, excluded both
source requests as `grasp_feasibility` blocked, generated zero commands, and
rendered both prior evidence rows in the report.

Verification:

- Focused ruff and format checks passed for runner and test files.
- Focused pytest passed for the full proof-bundle runner test module.
- The Phase88 dry-run manifest passed the proof-bundle runner checker.

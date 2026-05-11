---
phase: 06
plan: 04
slug: verification-and-writeup
type: execute
wave: 4
depends_on: [06-01, 06-02, 06-03]
files_modified:
  - .planning/phases/06-molmospaces-api-semantic-cleanup/06-VERIFICATION.md
  - .planning/phases/06-molmospaces-api-semantic-cleanup/06-*-SUMMARY.md
  - docs/plans/molmospaces-manipulation-spike.md
autonomous: true
requirements_addressed: [MOLMO-CLEANUP-07]
---

<objective>
Close the phase with explicit verify/harness evidence and update the original
hybrid plan so there is no stale handoff instruction left behind.
</objective>

<tasks>

<task type="auto">
  <name>Task 1: Run focused and umbrella verification</name>
  <action>
    Run the Molmo cleanup test slice, `just harness::molmo-cleanup`,
    `just verify::molmo-cleanup`, and the relevant contract/static gates.
  </action>
  <verify>
    <automated>just verify::molmo-cleanup && just verify::contract && just verify::static</automated>
  </verify>
</task>

<task type="auto">
  <name>Task 2: Write verification and source-plan update</name>
  <action>
    Write `06-VERIFICATION.md` with command evidence, artifact paths, residual
    risks, and the exact provenance boundary. Update
    `docs/plans/molmospaces-manipulation-spike.md` from handoff-ready to phase
    shipped/verified.
  </action>
</task>

</tasks>

<success_criteria>
- Verification evidence names exact commands and artifact paths.
- The source plan names what shipped and keeps real manipulation deferred.
- Commits remain scoped and do not stage unrelated OpenClaw transcript changes.
</success_criteria>

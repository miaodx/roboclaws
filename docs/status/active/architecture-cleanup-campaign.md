# Architecture Cleanup Campaign

Source gate: `docs/plans/refactor-architecture-cleanup-campaign.md`

Latest user intent: autonomous architecture cleanup campaign with high
autonomy; continue through verified commit slices until a stop gate or two
post-HEAD discovery handoffs find no clear safe P1/P2 slice.

Current slice:

- Fresh discovery handoff for the next cleanup slice.

Last proven evidence:

- Removed the `LaunchPlan.mode` compatibility accessor and migrated tracked
  callers/tests to `evidence_mode`.
- Focused pytest passed.
- Stale-reference search found no launch-plan accessor references; remaining
  `.mode-*` hits are operator-console CSS classes.
- `git diff --check` passed.

Completed slice batch:

- Slice 1: canonicalized launch route tests on `roboclaws.launch.catalog` and
  removed one shallow compatibility module.
- Slice 2: removed one launch-plan compatibility alias while preserving public
  trace text.

Next proof:

```bash
Run a fresh `$intuitive-reduce-entropy` discovery handoff against current HEAD.
```

Stop condition:

- Stop for public contract migration, unavailable proof, external/hardware
  evidence, or two consecutive fresh post-HEAD no-clear-candidate handoffs.

No-touch scope:

- Do not remove historical plan/ADR evidence solely because it names retired
  surfaces.
- Do not change live simulator/provider behavior in this campaign without a
  focused proof gate.

Parked work:

- None yet.

# 0046. Render Proof Bundle Result Feasibility

Date: 2026-05-10

## Status

Accepted

## Context

ADR-0045 made proof-bundle commands sample from the same real cleanup scene as
the ADR-0003 cleanup artifact. Local exact-scene probes now fail for some real
cleanup objects with `HouseInvalidForTask` / robot placement infeasibility.

The proof-bundle runner report still primarily shows commands and expected
artifact paths. After local execution, a reviewer must open each proof
`run_result.json` and `report.html` separately to understand whether the proof
was planner-backed, whether cleanup binding promoted, whether the blocker is
task feasibility, and whether any planner views were captured.

That is another report-underlay gap: command evidence, proof-result evidence,
and final cleanup rerun evidence must be visible in one bundle report before
the next fallback-selection phase can make good choices.

## Decision

The proof-bundle runner manifest will include a proof result summary derived
from the generated proof run results when they exist. The summary will classify
each proof request as not run, planner-backed, binding-not-promoted,
task-feasibility-blocked, or blocked/unknown. It will also record blocker
codes, cleanup binding promotion, exact cleanup task config, proof report path,
and any planner view image artifacts.

The proof-bundle runner report will render that summary as a dedicated visual
section after probe commands. It may show "no views recorded" for probes that
block before policy execution; that is evidence, not a missing report feature.

The runner checker will validate the new section when a summary is present.

## Consequences

- Executed proof-bundle reports become reviewable without manually opening
  every proof artifact first.
- The exact cleanup-scene feasibility blocker is visible at bundle level.
- Future fallback-selection work can consume explicit per-proof feasibility
  status instead of scraping stderr or relying on command success.

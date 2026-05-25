# Research Reports

This directory contains technical research documents that inform Roboclaws project decisions. These reports serve as decision context during periodic project reviews and will be updated as the landscape evolves.

## Report Index

| # | File | Topic | Key Conclusion |
|---|------|-------|---------------|
| 01 | [openclaw-isaaclab-feasibility](01-openclaw-isaaclab-feasibility.md) | OpenClaw + Isaac Lab feasibility | Technically feasible but not for quick PoC; deferred to Phase 3 |
| 02 | [ai2thor-multiagent-foundations](02-ai2thor-multiagent-foundations.md) | AI2-THOR multi-agent API + OpenClaw integration | Native multi-agent works on iTHOR; ProcTHOR has bugs |
| 03 | [simulation-platforms-2026](03-simulation-platforms-2026.md) | 2026 simulation platform landscape | MolmoSpaces lacks multi-agent; AI2-THOR is fastest path |
| 04 | [openclaw-robotics-ecosystem](04-openclaw-robotics-ecosystem.md) | OpenClaw robotics ecosystem mapping | 6 active repos; multi-agent sim control is an open gap |
| 05 | [real-model-smoke-validation](05-real-model-smoke-validation.md) | Issue #50 local-dev validation | Territory terminates early, coverage fails, follow-up tracked in #52 |
| 06 | [visual-grounding-perception-producer](06-visual-grounding-perception-producer.md) | Edge visual-grounding perception producer | Separate producer service; fast proposer first, optional verifier only when measured quality requires it |

## See Also

- [`docs/research-checkpoints/`](../research-checkpoints/) — Monthly ecosystem checkpoint snapshots (Chinese, internal decision-oriented). Complementary to single-topic reports here: research/ answers "should we do X?", checkpoints/ answer "what does the ecosystem look like now and do our prior judgments still hold?".

## Changelog

- **2026-04-13**: Initial version, 4 reports completed
- **2026-04-14**: Added report 05 documenting the issue #50 real-model smoke validation outcome
- **2026-04-28**: Added cross-link to new monthly checkpoint series at `docs/research-checkpoints/`
- **2026-05-25**: Added report 06 on the visual-grounding perception producer reference design

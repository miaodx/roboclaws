---
date: 2026-04-22
type: local-dev
status: in_progress
scope:
  - phase-02.4-local-review
  - phase-02.6-view-bridge-followup
related:
  - .planning/milestones/v1.98-phases/02.4-view-experiment-ab/02.4-04-analysis-local-dev-and-writeup-PLAN.md
  - .planning/milestones/v1.98-phases/02.6-openclaw-mcp-tools-integration/02.6-04-example-rewire-to-mcp-PLAN.md
  - .planning/milestones/v1.98-phases/02.6-openclaw-mcp-tools-integration/02.6-06-live-probe-gate-PLAN.md
artifacts:
  - output/openclaw-demo-kimi-mapv2chase-50/
  - output/openclaw-autonomous-mapv2chase-smoke-rerun/
  - output/openclaw-autonomous-mapv2chase-summaryfix-smoke/
---

# Local Plan: Phase 2.4 Review + Phase 2.6 View Bridge

## Objective

Handle the user's requested local sequence in one pass:

1. commit the current Phase 2.4 scaffold,
2. run a real single-agent Phase 2.4 review demo,
3. make the new view family usable from the Phase 2.6 autonomous MCP path,
4. prove the autonomous path still works locally with the shared view bundle.

## Sequence

- [x] Commit the current Phase 2.4 implementation snapshot before more local changes.
- [x] Run `examples/openclaw_demo.py` for a 50-step Kimi review on `--views map-v2+chase`.
- [x] Extract the navigation-view assembly into shared code so the push-model demo and MCP autonomous path use the same `baseline` / `map-v2` / `map-v2+chase` surface.
- [x] Rewire `examples/openclaw_nav_autonomous.py` and `roboclaws/openclaw/mcp_server.py` to accept `--views`, emit view metadata, and serve the shared prompt bundle.
- [x] Add startup failure detection for MCP bind collisions and restore request-event tracing so Phase 2.6 reports count tool calls correctly.
- [x] Run a real local autonomous smoke on `map-v2+chase` and confirm `observe`/`move`/`done` land through MCP with visible artifacts.

## Evidence

- Phase 2.4 review demo:
  - `output/openclaw-demo-kimi-mapv2chase-50/`
  - result: `50` steps, `terminated=max_steps`, provider `calls=50 ok=50`
- Phase 2.6 bridge smoke:
  - `output/openclaw-autonomous-mapv2chase-smoke-rerun/`
  - result: `terminated=done`, `observe=4`, `move=3`, `done=1`, `view_variant=map-v2+chase`
- Phase 2.6 summary-fix smoke:
  - `output/openclaw-autonomous-mapv2chase-summaryfix-smoke/`
  - result: `terminated=done`, `summary.json total_tool_calls=4`, `tool_calls_by_type={observe:2, move:1, done:1}`

## Remaining Work

- [ ] Phase 2.4 is still open at `02.4-04`: run the full Kimi sweep, run the smaller NVIDIA confirm set if NVIDIA multimodal is repaired, and publish `docs/view-experiment-2026-04.md`.
- [ ] Clean up unrelated local dirt before any ship commit (`uv.lock`, generated `vis/` artifacts) so the next commit scopes only the intended source/docs changes.

## Notes

- The first autonomous smoke on 2026-04-22 exposed a real local failure mode: a stale `/tmp/mcp_launcher.py` listener held port `18788`, the new MCP server failed to bind, and the run silently burned wall clock without any tool calls. The code now hard-fails on that startup condition instead of proceeding.
- The shared-view follow-up does not close Phase 2.4 by itself. It simply ensures the same view family is usable in the shipped Phase 2.6 architecture.

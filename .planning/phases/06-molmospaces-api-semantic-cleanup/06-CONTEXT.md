# Phase 6: MolmoSpaces api-semantic cleanup pilot — Context

**Gathered:** 2026-05-07
**Status:** Ready for execution
**Source:** `docs/plans/molmospaces-manipulation-spike.md`

<domain>
## Phase Boundary

Build the first direct coding-agent cleanup artifact for `帮我收拾这个房间` while
being explicit that this is `api_semantic` cleanup, not real robot grasping.

This phase must produce:

- A deterministic messy-room scenario with a public task view and a private
  scoring manifest.
- A fake/MolmoSpaces-shaped backend whose primitive effects are explicitly
  labeled `api_semantic`.
- A direct MCP-style tool contract that is callable in tests without Docker or
  OpenClaw.
- A scripted cleanup demo that writes `trace.jsonl`, `run_result.json`,
  snapshots/report artifacts, and a private score.
- Verify and harness gates that prove the artifact works locally without a real
  MolmoSpaces dependency.

Not in scope:

- Top-level import of `molmo_spaces` or a repo-wide Python `>=3.11` migration.
- RBY1M/Franka planner-backed manipulation.
- OpenClaw Gateway routing for the cleanup demo.
- Territory/coverage on MolmoSpaces.

</domain>

<decisions>
## Implementation Decisions

### D-01: Provenance is part of every primitive contract
Every object-changing cleanup primitive must carry `primitive_provenance:
api_semantic`. Reports and run results must surface the same label so the demo
cannot be mistaken for real grasping.

### D-02: Fake backend is a contract harness, not a product backend
The fake backend exists to pin object/receptacle IDs, stale-reference errors,
trace shape, private scoring, and report rendering before any optional
MolmoSpaces subprocess adapter is introduced.

### D-03: Private manifest must stay private
The agent-facing scenario and tool responses may expose current locations,
object names, and allowed primitive names. They must not expose the private
valid target map used by the scorer.

### D-04: Direct coding-agent path comes before OpenClaw
OpenClaw integration is deferred until the direct MCP-style cleanup artifact is
stable and its report/run-result evidence is useful.

</decisions>

<canonical_refs>
## Canonical References

- `docs/plans/molmospaces-manipulation-spike.md` — source of truth and local
  capability spike result.
- `roboclaws/mcp/server.py` — Phase 2.6 MCP direct-call/test pattern and trace
  event style.
- `roboclaws/core/run_artifacts.py` — existing trace/run-result helpers and
  report extraction conventions.
- `scripts/render_autonomous_replay.py` — report artifact conventions.
- `harness/README.md`, `harness/PLAN.md`,
  `docs/harness-self-improvement-loop.md` — harness naming and evidence model.
- `.planning/phases/04-refactor-regression-harnesses-for-vlm-territory-coverage-and/`
  — verify/harness split precedent.

</canonical_refs>

<acceptance>
## Phase Acceptance Criteria

- `just harness::molmo-cleanup` exits 0 and writes a deterministic cleanup run
  under `output/molmo-cleanup-harness/`.
- `run_result.json` records `cleanup_status=success`, `restored_count >= 3`,
  `primitive_provenance=api_semantic`, and the report path.
- `report.html` renders the object moves, final score, and provenance label.
- Unit/contract tests cover manifest privacy, stale-reference errors, scorer
  behavior, artifact schema, and no top-level MolmoSpaces import.
- `docs/plans/molmospaces-manipulation-spike.md` is updated after execution to
  describe what shipped and what remains local-dev/deferred.

</acceptance>

---

*Phase: 06-molmospaces-api-semantic-cleanup*
*Context gathered: 2026-05-07 from approved hybrid plan*

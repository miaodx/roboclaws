# Refactor Molmo Cleanup Memory And Routine Entropy

**Status:** Proposed source plan
**Created:** 2026-05-22
**Source:** `$intuitive-reduce-entropy` audit and `$grill-with-docs` design
session on Molmo cleanup worklist, skill memory, and promoted MCP route drift
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

Molmo cleanup currently has too many places that describe or implement the same
behavior:

- live-agent prompts tell the model to maintain a waypoint checklist and avoid
  forgotten `observed_*` handles;
- direct and smoke paths keep local `handled_handles` / `agent_memory` state;
- `RealWorldCleanupContract` keeps observed waypoints, handled handles,
  lifecycle rows, and `done()` gates;
- the skill-side trace-preserving routine, repo-side semantic cleanup loop, and
  promoted `clean_observed_object` candidate each encode a cleanup transport
  sequence;
- `world-labels-perf` and `cleanup_routine=mcp|mcp-promoted` make the command
  surface look like there are multiple valid cleanup behavior routes.

This makes agent behavior hard to reason about and invites drift between live
Codex/Claude runs, deterministic demos, reports, checkers, and docs.

## Goal

Reduce the Molmo cleanup memory/routine surface to one obvious architecture:

```text
Skill Scratchpad
  -> non-authoritative live-agent strategy memory

Canonical cleanup routine engine
  -> one selected object transport chain over public capability tools

Cleanup Worklist
  -> contract-derived public lifecycle facts for done/report/checker

MCP primitive tools
  -> stable, general capability surface with no cleanup-specific progress
     summaries added by default
```

The refactor should preserve skill-first behavior while making cleanup facts
auditable and consistent across direct, smoke, and live coding-agent runs.

## Decisions Locked

- Keep the default MCP tool surface stable. Do not add a default
  `cleanup_worklist` query tool for live agent recovery.
- Keep primitive capability responses general. Do not add cleanup-specific
  progress summaries to `observe`, `navigate_to_waypoint`, `pick`, `place`, or
  related primitive responses by default.
- Introduce or formalize **Skill Scratchpad** as run-local, non-authoritative
  agent memory for strategy, hypotheses, retry history, and next-action intent.
- Introduce or consolidate **Cleanup Worklist** as the contract-derived public
  lifecycle view for observed handles, waypoint coverage, held-object state, and
  pending cleanup candidates.
- If Skill Scratchpad and Cleanup Worklist disagree, the contract-derived
  Cleanup Worklist wins.
- Remove `clean_observed_object` as a promoted MCP candidate rather than keeping
  it as an opt-in compatibility path.
- Remove `cleanup_routine=mcp|mcp-promoted`; do not keep aliases.
- Remove `world-labels-perf` as a behavior profile. Fast/timing runs should use
  normal input-contract profiles plus explicit capture options such as
  `record_robot_views=false`.
- Keep `smoke`, `world-labels`, `camera-raw`, and `camera-labels` as meaningful
  input-contract profiles.
- Direct demo, MCP smoke, Codex live, Claude live, and OpenClaw live cleanup
  routes should use the same canonical single-object cleanup routine engine for
  normal cleanup chains.
- Historical output artifacts do not need migration.

This plan is the implementation follow-through for ADR-0132. It supersedes the
active direction in `docs/plans/molmo-cleanup-codex-harness-speedup.md` that
introduced `world-labels-perf` and the promoted MCP cleanup candidate as active
performance routes.

## Behavior Model

### Skill Scratchpad

The scratchpad is an agent aid, not a fact source.

- It lives in the live agent workspace as `cleanup_scratch.json`.
- It may be copied into the run output as `agent_scratchpad.json` for debugging.
- It records object-level strategy state, current intent, failed attempts,
  retry notes, and reconciliation notes.
- It should be managed through a skill helper script rather than hand-written by
  the model.
- It is updated at decision boundaries, not after every primitive tool call.
- It never drives scorer, checker, report facts, or `done()` gates.

Suggested lightweight schema:

```json
{
  "schema": "molmo_cleanup_skill_scratchpad_v1",
  "observed_handles": {},
  "waypoints": {},
  "current_intent": null,
  "failed_attempts": [],
  "reconciliation_notes": [],
  "notes": []
}
```

### Cleanup Worklist

The worklist is the only public lifecycle view for cleanup facts.

- Keep schema name `cleanup_worklist_v1`.
- `objects[]` is the canonical lifecycle view for observed handles and
  model-declared visual candidates.
- `waypoints[]` is the canonical public sweep coverage view.
- `rooms[]` is derived from waypoints and objects.
- `pending_cleanup_candidates` is derived from `objects[]`, not maintained as a
  separate source of truth.
- Raw-FPV unresolved visual candidates enter the worklist as
  `grounding_unresolved` and do not block `done()`.
- The worklist contains no generated mess truth, hidden target count,
  acceptable destination sets, private planner aliases, or private scorer state.

Canonical object lifecycle states:

- `pending`
- `grounding_unresolved`
- `navigating_to_object`
- `held`
- `navigating_to_receptacle`
- `placed`
- `placed_closed`
- `skipped`
- `stale`
- `blocked`

Do not introduce `observed` as a lifecycle state; actionable observed handles
are `pending`.

### Canonical Routine Engine

Add one routine engine for a single already-selected object transport chain. It
does not scan rooms, choose candidates, maintain scratchpad memory, read private
truth, write reports, or decide when cleanup is complete.

Expected sequence:

```text
navigate_to_object
pick
navigate_to_receptacle
open_receptacle?        # fridge/refrigerator-like targets
place_inside|place
close_receptacle?       # after opening fridge/refrigerator-like targets
```

Placement policy:

- `placement_tool=auto` lets the routine choose from public fixture hints or
  public fixture affordances.
- Explicit `place` / `place_inside` is respected only when compatible with
  public fixture affordances; incompatible explicit choices fail with recovery
  context rather than being silently corrected.
- The contract remains the authoritative semantic order guard.
- The routine may perform one bounded, recorded recovery based on a contract
  `required_tool` response, then fail if recovery does not work.

Suggested result schema:

```json
{
  "schema": "cleanup_routine_result_v1",
  "routine": "canonical_cleanup_routine_v1",
  "object_id": "observed_003",
  "fixture_id": "sink_01",
  "ok": true,
  "selected_placement_tool": "place",
  "steps": [],
  "failed_phase": "",
  "error_reason": "",
  "required_tool": "",
  "recovery_attempted": false
}
```

Scratchpad stores only an object-level summary of this result. Trace/report
artifacts preserve substeps.

## Implementation Scope

### Code

- Add the canonical routine engine, likely
  `roboclaws/molmo_cleanup/cleanup_routine.py`.
- Update deterministic direct and MCP smoke cleanup paths to call the canonical
  routine engine.
- Update live-agent skill helper scripts to call the canonical routine engine
  through public tool adapters.
- Add `skills/molmo-realworld-cleanup/scripts/scratchpad.py` for scratchpad
  init/update/validate/reconcile helpers.
- Convert or replace
  `skills/molmo-realworld-cleanup/scripts/trace_preserving_cleanup.py` so it no
  longer owns a second cleanup sequence implementation.
- Consolidate `RealWorldCleanupContract` lifecycle state into one Cleanup
  Worklist source used by `agent_view_payload()`, `done()`, report, and checker
  paths.
- Remove `RealWorldCleanupContract.clean_observed_object()`.
- Remove promoted cleanup MCP tool registration and dispatch.
- Remove `cleanup_routine=mcp|mcp-promoted` just routing and server args.
- Remove `world-labels-perf` from cleanup profiles and command routing.
- Replace `world-labels-perf` use cases with `world-labels` plus explicit
  capture options.
- Remove direct/smoke local `handled_handles` as a correctness source; use the
  contract-derived Cleanup Worklist instead.
- Keep focused semantic-order tests that deliberately call primitives directly.

### Docs

Update all current-truth docs that would otherwise send users or agents to the
removed routes:

- `skills/molmo-realworld-cleanup/SKILL.md`
- `skills/molmo-realworld-cleanup/skill.json`
- `docs/human/mcp-skills-and-semantic-profiles.md`
- `docs/human/molmospaces-settings.md`
- `docs/human/agent-task-command-taxonomy.md` if it references the old perf
  lane or promoted candidate
- `just/README.md` and related command docs
- any checker/report docs that describe `clean_observed_object`,
  `world-labels-perf`, or `cleanup_routine=mcp|mcp-promoted`

Keep ADR-0130 as historical timing evidence. Do not rewrite its body; ADR-0132
is the active decision.

### Tests

Delete or rewrite tests that only protect removed compatibility behavior:

- promoted tool list contains `clean_observed_object`;
- `clean_observed_object` route works;
- `world-labels-perf` exists as a profile;
- `cleanup_routine=mcp|mcp-promoted` is accepted.

Strengthen tests that protect the new boundary:

- no default promoted cleanup tool surface;
- one canonical routine result schema;
- direct/smoke normal cleanup chains use the canonical routine engine;
- Cleanup Worklist is the only public lifecycle source in `agent_view`;
- unresolved raw-FPV candidates enter worklist as `grounding_unresolved` and do
  not block `done()`;
- `done()` gates derive pending candidates and unvisited waypoints from
  Cleanup Worklist;
- scratchpad schema validation rejects malformed scratchpads;
- reports display scratchpad only as non-authoritative agent notes/debug
  evidence.

## Non-Goals

- Do not add a default live MCP `cleanup_worklist` / `cleanup_status` query
  tool.
- Do not add cleanup progress summaries to generic primitive responses.
- Do not make Skill Scratchpad authoritative for scorer, checker, report facts,
  or `done()` gates.
- Do not keep aliases for removed `cleanup_routine` values.
- Do not preserve `clean_observed_object` for backward compatibility.
- Do not preserve `world-labels-perf` for backward compatibility.
- Do not migrate historical `output/` artifacts.
- Do not require physical Agibot validation for this refactor.
- Do not change private generated-mess scoring semantics.

## Acceptance Criteria

- Runtime code has no active `clean_observed_object` MCP route.
- Runtime command routing has no `cleanup_routine=mcp|mcp-promoted` path.
- Cleanup profiles no longer include `world-labels-perf`.
- Normal direct, MCP smoke, and live coding-agent cleanup paths use the same
  canonical cleanup routine engine for selected-object transport.
- Live coding-agent cleanup uses Skill Scratchpad as a non-authoritative
  strategy aid.
- `agent_view.cleanup_worklist.schema == "cleanup_worklist_v1"` and
  `cleanup_worklist.objects` is the report/checker lifecycle source.
- `done()` gates are unchanged in meaning but derive pending candidates and
  sweep coverage from Cleanup Worklist.
- Reports clearly separate Cleanup Worklist facts from non-authoritative Skill
  Scratchpad notes.
- Current docs no longer present promoted cleanup or `world-labels-perf` as
  active routes.

## Verification Plan

### Static and focused checks

Run after implementation:

```bash
ruff check \
  roboclaws/molmo_cleanup \
  scripts/molmo_cleanup \
  examples/molmo_cleanup \
  skills/molmo-realworld-cleanup/scripts

ruff format --check \
  roboclaws/molmo_cleanup \
  scripts/molmo_cleanup \
  examples/molmo_cleanup \
  skills/molmo-realworld-cleanup/scripts
```

Focused test set:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup \
  tests/contract/reports/test_molmo_cleanup_report.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py
```

Stale-path searches:

```bash
rg -n "clean_observed_object|world-labels-perf|cleanup_routine=mcp|mcp-promoted" \
  roboclaws scripts examples skills docs just tests
```

Any remaining hits must be historical ADR text, explicit migration notes, or
negative tests.

### Required live validation

This refactor is not complete without a real local live cleanup artifact. The
required gate is a work-network-compatible repo-local Codex route, not OpenClaw
and not bare host `codex`.

```bash
just dev::network-status
set -a && source .env && set +a
just task::run molmo-cleanup codex world-labels seed=7 generated_mess_count=10
```

Expected prerequisites:

- `.env` provides the repo-local Codex route, including `CODEX_BASE_URL` and
  `CODEX_API_KEY`.
- The run uses the supported Docker-backed coding-agent path.
- OpenClaw is not required and should not be used for this gate.

Hard gate criteria:

- `report.html` and `run_result.json` are generated.
- Cleanup checker passes.
- `cleanup_status=success`.
- `clean_observed_object` call count is zero and the promoted composite route is
  absent from the trace.
- The trace shows the normal cleanup chain through the canonical routine engine.
- `agent_view.cleanup_worklist.schema == "cleanup_worklist_v1"`.
- Live route produces or archives a valid non-authoritative scratchpad artifact.
- Removed `world-labels-perf` / `cleanup_routine=mcp|mcp-promoted` routes are
  not used.

Strongly recommended but not blocking for the first implementation:

```bash
just task::run molmo-cleanup codex camera-raw seed=7 generated_mess_count=10
```

`camera-raw` evidence should be collected when time and provider stability
allow, but the hard gate is one successful live Codex `world-labels` artifact.

If the required live gate cannot run because of provider, key, Docker, or local
runtime issues, do not mark the refactor complete. Record the blocker, exact
command, and expected artifact criteria.

## GSD Handoff

Preferred handoff:

```text
gsd-plan-phase <phase> --prd docs/plans/refactor-reduce-entropy-molmo-cleanup-memory.md
```

This should be implemented as one vertical refactor flow, not split into a
scratchpad-only phase followed by a later worklist consolidation. The stop
condition is one canonical cleanup routine path, one contract-derived worklist
fact source, no promoted cleanup composite route, no `world-labels-perf`
profile, and a passing live Codex `world-labels` cleanup artifact.

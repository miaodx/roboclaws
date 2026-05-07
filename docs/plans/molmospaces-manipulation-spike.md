<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0507-autoplan-restore-20260507-162727.md -->

# MolmoSpaces Manipulation Spike

**Status:** Approved pre-GSD plan; capability spike is next
**Created:** 2026-05-07
**Reviewed:** 2026-05-07 with `autoplan`; approved by user
**Workflow:** Matt-style plan first; optional `to-issues`; GSD only after
MolmoSpaces capabilities are proven

## Why This Exists

Roboclaws is shifting its strategic center from direct VLM game loops toward
OpenClaw / coding-agent robot control through a small tool contract.

AI2-THOR remains the stable baseline and regression backend. MolmoSpaces is the
future-default substrate for manipulation work because it has richer scenes,
manipulable objects, grasp data, and a path toward MuJoCo / ManiSkill / Isaac.

This spike should prove one agent can manipulate objects before we attempt
multi-agent territory/coverage on the new substrate.

## Operating Decisions

- Use a dual-backend transition: keep AI2-THOR, add MolmoSpaces.
- Direct coding-agent MCP path comes first.
- OpenClaw path comes second after direct MCP works.
- Territory/coverage stay AI2-THOR-only until one-agent MolmoSpaces
  manipulation works well.
- Room randomization happens before the run, outside MCP.
- Semantic/scripted manipulation is acceptable for v0, but every artifact must
  disclose whether each primitive used `real`, `scripted`, or `shim` behavior.
- Split-model navigation work is paused until this path proves useful.
- Do not build a broad backend-neutral simulator abstraction before the
  MolmoSpaces API shape is known.

## Capability Gate

Do not ingest this plan into GSD until the capability spike proves the APIs below
on the target local workstation.

| Capability | Must prove | Evidence |
| --- | --- | --- |
| Install/runtime | MolmoSpaces and the chosen sim path import and run locally. | Command log with versions and any required extras. |
| Scene load/reset | A deterministic scene can be loaded and reset by seed. | Minimal script plus run directory. |
| Object inventory | Objects and receptacles can be listed with stable IDs/types. | Sample `scene_objects` payload. |
| Camera frames | Before/after images can be captured for reports. | Saved image artifacts. |
| State readback | Final object/receptacle state can be scored after actions. | Sample state dump used by scorer. |
| Manipulation primitive | `pick` and `place` can be implemented as real, scripted, or shimmed primitives. | Primitive provenance recorded in trace and `run_result.json`. |
| Failure semantics | Failed/stale/impossible actions return explicit errors. | Example failure payloads. |

If any required capability is missing, stop after the spike, document the
blocker, and do not fake Layer 1 as a successful MolmoSpaces manipulation demo.

## Architecture Shape

```text
scripts/prepare_molmospaces_room.py
        |
        v
output/runs/<id>/scenario.json  +  private scoring manifest
        |
        v
MolmoSpaces MCP entry point
        |
        +--> observe / scene_objects / reach / pick / place / open / close / done
        |
        v
Coding agent skill
        |
        v
trace.jsonl + run_result.json + report.html
        |
        v
state-delta scorer
```

The tool contract is the abstraction boundary. Keep implementation narrow until
the capability gate has real API facts.

## Initial MCP Surface

Keep the tool surface small:

- `observe(label="")`
- `scene_objects(filter_types="")`
- `goto` or `reach`
- `pick(object_id)`
- `place(receptacle_id | location_id)`
- `open(object_id)`
- `close(object_id)`
- `done(reason)`

Contract requirements:

- Tool responses must use stable object/receptacle identifiers or return an
  explicit stale-reference error.
- `scene_objects` must support filtering/truncation so large scenes do not flood
  agent context.
- The server should bind loopback-only by default.
- The private scoring manifest must never be exposed through MCP or copied into
  agent prompt context.
- Timeout/no-progress must be an explicit terminal status, not success.

## Layer 1: Smallest Demo

Goal: deterministic pick/place with one object and one receptacle.

Example:

```text
Pick up the book from the floor and place it on the table.
```

Expected tool flow:

```text
observe -> scene_objects -> goto/reach -> pick -> place -> observe -> done
```

Pass criteria:

- Object ends on the required receptacle.
- `trace.jsonl` records all tool calls.
- `run_result.json` records backend, scenario id, final status, artifact paths,
  and primitive provenance.
- `report.html` shows before/after snapshots and the tool trace.
- The report states whether `pick` / `place` used real MolmoSpaces APIs, a
  scripted planner, or a temporary shim.

## Layer 2: Open Cleanup Demo

Goal: natural-language room cleanup.

Operator prompt:

```text
帮我整理这个房间
```

Pre-run setup should create a seeded messy room, outside MCP:

```bash
python scripts/prepare_molmospaces_room.py \
  --scenario cleanup-room \
  --seed 7 \
  --messiness easy \
  --output output/runs/<id>/scenario.json
```

Private scoring manifest example:

```json
{
  "misplaced": [
    {
      "object_type": "Book",
      "start": "floor",
      "valid_targets": ["Bookshelf", "Desk", "CoffeeTable"]
    },
    {
      "object_type": "Cup",
      "start": "floor",
      "valid_targets": ["Table", "CounterTop"]
    }
  ]
}
```

The agent must not see this private manifest. It should infer the room state
through `observe` and `scene_objects`.

Pass criteria:

- At least 3 of 5 misplaced objects move to valid receptacles.
- No high-severity failure: lost object, impossible placement marked as success,
  or timeout with no progress.
- `report.html` shows initial room, final room, restored/missed object table,
  primitive provenance, and tool trace.

## Task Slices

These are approved vertical slices. Run the capability spike first; only convert
the rest into GSD execution work after the API facts are known.

1. **Capability spike**
   Install/run the smallest MolmoSpaces/MuJoCo example and fill the capability
   matrix. Identify APIs for scene load, reset, object inventory, object state
   changes, camera frames, and manipulation primitives.

2. **Direct MCP Layer 1**
   Add the minimal MolmoSpaces MCP server/entry point and complete deterministic
   pick/place with artifacts. Reuse existing trace/report patterns where
   possible and keep additive compatibility with current trace consumers.

3. **Scenario builder and scoring**
   Add seeded room messiness outside MCP, private manifest, state-delta scoring,
   and report rendering. Use `tdd` for manifest parsing, scorer behavior, and
   privacy boundaries.

4. **Direct MCP Layer 2**
   Run `帮我整理这个房间` through a coding agent and validate 3-of-5 cleanup on
   an easy seed. Keep failures visible in `run_result.json` and the report.

5. **OpenClaw follow-up**
   Reuse the working MCP surface through OpenClaw. Validate Layer 1 first, then
   Layer 2. Split this into a separate GSD phase if direct MCP Layer 1 is not
   stable quickly.

6. **Docs and ADR**
   Reframe README / ARCHITECTURE / technical design after evidence exists. Add
   an ADR that AI2-THOR remains baseline and MolmoSpaces is the next substrate
   for manipulation.

## Validation Plan

Cloud-testable checks:

- Scenario JSON parsing and seed determinism.
- Private manifest parsing and state-delta scoring.
- MCP tool request/response schemas with a fake MolmoSpaces backend.
- Additive `trace.jsonl` and `run_result.json` fields.
- Report rendering for before/after images, restored/missed table, trace
  summary, and primitive provenance.

Local-dev checks:

- MolmoSpaces/MuJoCo install and import.
- Scene load/reset and frame capture.
- Object inventory and object state readback.
- Real/scripted/shim `pick` and `place` behavior.
- End-to-end Layer 1 coding-agent run with artifacts.
- End-to-end Layer 2 cleanup run restoring at least 3 of 5 misplaced objects.

Do not claim real MolmoSpaces validation from cloud-only evidence.

## Artifact Requirements

`trace.jsonl`:

- Keep the existing trace shape additive-only.
- Record every tool call, result status, error reason, and primitive provenance.
- Do not log `.env`, API keys, or private scoring manifests.

`run_result.json`:

- Record backend, scenario id, seed, final status, terminate reason, artifact
  paths, score summary, and primitive provenance.
- Distinguish `success`, `partial_success`, `failed`, `timeout`, and
  `blocked_capability`.

`report.html`:

- Show initial and final room snapshots.
- Show restored/missed object table.
- Show tool trace summary.
- Show backend primitive provenance near the pass/fail summary.
- Avoid wording that makes a shim look like real manipulation.

## Error And Rescue Rules

| Failure | Rescue |
| --- | --- |
| MolmoSpaces local install or APIs do not support the needed loop. | Stop after capability spike, document exact blocker, and do not fake Layer 1. |
| Scripted shim becomes indistinguishable from real manipulation. | Store primitive provenance in `run_result.json`, trace events, and report. |
| Layer 2 prompt is too open and produces noisy failures. | Seed easy scenarios first, cap to 5 misplaced objects, require 3/5 restored. |
| Local-only validation gets implied as cloud-validated. | File/use a `local-dev` validation issue with exact commands and artifacts. |
| Scope expands into territory/multi-agent before one-agent works. | Keep territory and multi-agent explicitly deferred until Layer 2 evidence exists. |
| Large scene inventory overwhelms context. | Filter by visible/relevant types and cap response size. |
| Object/receptacle IDs drift between observe and action. | Use stable IDs or explicit stale-object errors. |

## Deferred

- Multi-agent MolmoSpaces.
- Territory/coverage on MolmoSpaces.
- Low-level arm control and VLA action experts.
- Isaac Lab humanoid migration.
- Full backend-neutral simulator abstraction.
- Split-model navigation optimization.
- Raising Layer 2 beyond 3-of-5 until the first easy cleanup demo works.

## GSD Handoff Trigger

Ingest this plan into GSD only after the capability spike identifies the actual
MolmoSpaces APIs and the implementation slices are no longer speculative.

At that point:

- Optionally run `to-issues` first if the work should be divided across multiple
  agents or tracked in GitHub Issues.
- Add/update the phase in `.planning/ROADMAP.md`.
- Create `.planning/phases/<phase>/` from this doc.
- Let GSD own execution, validation, summaries, and shipped state.

During implementation, use `tdd` inside the slices where behavior needs to drive
the code: scenario scoring, manifest parsing, MCP tool contracts, artifact
schema, and any regression found during local MolmoSpaces validation.

## Review Decisions Incorporated

| Decision | Outcome |
| --- | --- |
| Keep direct coding-agent MCP before OpenClaw. | Accepted. |
| Require capability matrix before GSD ingest. | Accepted. |
| Require primitive provenance in artifacts. | Accepted. |
| Keep `to-issues` optional before GSD. | Accepted. |
| Treat `report.html` as artifact UI, not product UI. | Accepted. |
| Keep territory/coverage deferred. | Accepted. |
| Gate real MolmoSpaces validation as local-dev. | Accepted. |
| Split OpenClaw follow-up if direct Layer 1 is unstable. | Accepted as guidance. |

## Next Workflow

```text
run capability spike
-> update this plan with real API facts
-> optionally run to-issues
-> gsd-plan-phase / gsd-ingest-docs
-> gsd-execute-phase
```

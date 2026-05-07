<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0507-autoplan-restore-20260507-162727.md -->

# MolmoSpaces Manipulation Spike

**Status:** Phase 6 api-semantic cleanup pilot shipped and verified on 2026-05-07
**Created:** 2026-05-07
**Reviewed:** 2026-05-07 with `autoplan`; approved by user
**Workflow:** Matt-style plan -> autoplan -> local capability spike -> GSD
Phase 6 execution. OpenClaw and real planner-backed manipulation remain deferred.

## Why This Exists

Roboclaws is shifting its strategic center from direct VLM game loops toward
OpenClaw / coding-agent robot control through a small tool contract.

AI2-THOR remains the stable baseline and regression backend. MolmoSpaces is the
future-default substrate for manipulation work because it has richer scenes,
manipulable objects, grasp data, and a path toward MuJoCo / ManiSkill / Isaac.

This spike should prove a single coding agent can run the visible cleanup task
`帮我收拾这个房间` through a small MolmoSpaces-backed tool contract before we
attempt OpenClaw, hardware, or multi-agent work on the new substrate.

## Operating Decisions

- Use a dual-backend transition: keep AI2-THOR, add MolmoSpaces.
- Direct coding-agent MCP path comes first.
- OpenClaw path comes second after direct MCP works.
- Territory/coverage stay AI2-THOR-only until the one-agent MolmoSpaces cleanup
  demo works well.
- Room randomization happens before the run, outside MCP.
- The first public proof is cleanup-first, not a separate pick/place milestone.
- MolmoSpaces API-backed semantic manipulation is acceptable for v0, but every
  artifact must disclose whether each primitive used `real`, `api_semantic`,
  `scripted`, or `shim` behavior.
- Navigation comes inside the demo path. `goto` is acceptable; add other
  abilities only when the cleanup loop exposes a real gap.
- Split-model navigation work is paused until this path proves useful.
- Do not build a broad backend-neutral simulator abstraction before the
  MolmoSpaces API shape is known.

## Capability Gate

Do not ingest this plan into GSD until the cleanup-first capability spike proves
the APIs below on the target local workstation.

| Capability | Must prove | Evidence |
| --- | --- | --- |
| Install/runtime | MolmoSpaces and the chosen sim path import and run locally. | Command log with versions and any required extras. |
| Scene load/reset | A deterministic scene can be loaded and reset by seed. | Minimal script plus run directory. |
| Object inventory | Objects and receptacles can be listed with stable IDs/types. | Sample `scene_objects` payload. |
| Camera frames | Before/after images can be captured for reports. | Saved image artifacts. |
| State readback | Final object/receptacle state can be scored after actions. | Sample state dump used by scorer. |
| Semantic manipulation | Object state can be changed through MolmoSpaces APIs or a clearly-labeled temporary shim. | Primitive provenance recorded in trace and `run_result.json`. |
| Cleanup scoring | Seeded misplaced objects can be scored against private valid receptacles. | Sample scorer input/output with private manifest kept out of MCP context. |
| Failure semantics | Failed/stale/impossible actions return explicit errors. | Example failure payloads. |

If any required capability is missing, stop after the spike, document the
blocker, and do not fake the cleanup demo as a successful MolmoSpaces result.

### Local Capability Spike Result - 2026-05-07

The capability spike ran locally against upstream `allenai/molmospaces` main at
commit `3c50ae6093f7e4a4ef32529f8a773715da410a2f`.

Environment result:

- Roboclaws' repo `.venv` is Python `3.10.19`; upstream MolmoSpaces requires
  Python `>=3.11`, so the integration must use an isolated Python 3.11 runtime
  until or unless Roboclaws raises its Python floor.
- Isolated setup succeeded with
  `uv venv --python 3.11 /tmp/roboclaws-molmospaces-spike/.venv` and
  `uv pip install --python /tmp/roboclaws-molmospaces-spike/.venv/bin/python --torch-backend cpu -e ".[mujoco]"`.
- Installed versions: `molmo-spaces 0.0.1`, `mujoco 3.4.0`,
  `molmospaces-resources 0.0.1b4`.
- A minimal MuJoCo EGL render produced a `(64, 64, 3) uint8` RGB frame. This
  proves the local workstation can render headless MuJoCo frames without
  involving AI2-THOR or a real VLM.

API/resource result:

| Capability | Result | Evidence |
| --- | --- | --- |
| Install/runtime | Passed with an isolated Python 3.11 venv; blocked for the repo Python 3.10 venv. | Upstream `pyproject.toml` requires `>=3.11`; local install/import succeeded in `/tmp/roboclaws-molmospaces-spike/.venv`. |
| Scene load/reset | Passed for a tiny on-demand ProcTHOR val scene. | `get_scenes("procthor-10k", "val")` found `val_0.xml`; `install_scene_from_source_index("procthor-10k-val", 0)` installed `procthor-10k-val_val_0.tar.zst`; `mujoco.MjModel.from_xml_path(...)` loaded 415 bodies, 3492 geoms, 129 joints, and `mj_resetData` restored `qpos` exactly. |
| Object inventory | Passed from scene metadata and MuJoCo model state. | `get_scene_metadata(val_0.xml)` returned 140 objects; top categories included `Pencil`, `Chair`, `Pen`, `CellPhone`, `Television`, `Plate`, and `Cup`. |
| Camera frames | Passed at MuJoCo renderer level. | `mujoco.Renderer(...).render()` returned RGB frames for both a toy model and the loaded MolmoSpaces scene. |
| State readback | Passed at MuJoCo state level. | Free-joint object positions are readable through `data.xpos` and `data.qpos`; `ladle_...` moved by `delta_x=0.1` after a controlled `qpos` edit and `mj_forward`. |
| Semantic manipulation | Partially passed as `api_semantic`, not as real robot manipulation. | Direct MuJoCo free-joint edits can move objects and be scored, but that must be labeled `api_semantic`; RBY1M/Franka planner-backed pick/place remains unproven for this demo. |
| Cleanup scoring | Ready for implementation, not upstream-provided as the Roboclaws scenario. | Upstream benchmark schemas cover pick, pick/place, open/close, and nav-to-object episode specs; Roboclaws still needs its private valid-receptacle manifest and 3-of-5 scorer. |
| Failure semantics | Passed at ID lookup level. | `mujoco.mj_name2id(..., "missing-object-id") == -1`; the MCP layer should translate that into `stale_reference` rather than success. |

Operational finding:

- Avoid broad MolmoSpaces config imports during normal Roboclaws startup. A
  config-instantiation probe triggered the resource manager and pulled about
  5 GB into `~/.cache/molmo-spaces-resources`, mostly `objects/thor`,
  `objathor_metadata`, `grasps/droid`, and all robot packages. The first
  implementation slice must use an explicit pinned resource manifest and
  on-demand scene installation only.
- The aborted config probe briefly left the MolmoSpaces cache manifest missing
  the `grasps/droid: 20251116` entry; the local manifest was repaired before
  continuing. Treat this as evidence that demo setup scripts must be
  idempotent and must fail before partial bulk downloads when a manifest is too
  broad.

GSD handoff decision:

- The original "identify actual APIs" gate is satisfied for a narrow first
  GSD phase: fake-backend contracts, private scorer, report schema, and a
  direct MCP cleanup server that uses `api_semantic` object moves against
  MolmoSpaces/MuJoCo state.
- Do not claim real robot manipulation yet. A later local-dev acceptance gate
  must separately prove planner-backed RBY1M or Franka pick/place before any
  artifact uses `primitive_provenance="real"`.
- Do not make Roboclaws import MolmoSpaces at top level. Keep it behind an
  optional subprocess/extra or adapter boundary so the existing AI2-THOR paths
  and CI stay Python 3.10-safe.

### Phase 6 Implementation Result - 2026-05-07

The narrow GSD phase shipped the first cleanup artifact loop:

- `roboclaws/molmo_cleanup/` defines the public/private scenario contract,
  private scorer, API-semantic backend, direct-call MCP-style contract, and
  report renderer.
- `examples/molmospaces_cleanup_demo.py` runs a deterministic scripted cleanup
  and writes `trace.jsonl`, `run_result.json`, `scenario.json`,
  `private_manifest.json`, `before.png`, `after.png`, and `report.html`.
- `just harness::molmo-cleanup` and `just verify::molmo-cleanup` are the focused
  harness and verify gates for this pilot.
- `.planning/phases/06-molmospaces-api-semantic-cleanup/06-VERIFICATION.md`
  records the verification evidence.

Latest harness result:

| Field | Value |
| --- | --- |
| Artifact dir | `output/molmo-cleanup-harness/` |
| Scenario | `molmo-cleanup-default-7` |
| Cleanup status | `success` |
| Restored objects | `5/5` |
| Success threshold | `3/5` |
| Primitive provenance | `api_semantic` |
| Planner | `scripted_reference` |

Boundary:

- This is still not real robot manipulation. It proves the direct cleanup
  artifact contract, private scoring, reports, and provenance labeling.
- The scripted reference demo uses the private manifest to choose targets, so it
  is harness proof of the contract, not autonomous policy performance.
- MolmoSpaces itself remains behind a future optional Python 3.11 adapter or
  subprocess boundary; this phase keeps the repo Python 3.10-safe.

## Upstream Findings

Checked against upstream MolmoSpaces docs/source on 2026-05-07:

- MuJoCo is the primary runtime for this spike. MolmoSpaces supports classic
  MuJoCo and optional MuJoCo Filament installs, and upstream currently states
  data generation and benchmarking are only supported for MuJoCo.
- ManiSkill is useful as a future rendering/loading path because the upstream
  `molmo_spaces_maniskill` package can load MolmoSpaces MJCF assets and scenes
  into SAPIEN/ManiSkill, but it is not the first execution backend for our
  coding-agent MCP demo.
- Isaac Sim / Isaac Lab remain deferred because they are heavier than needed for
  this demo.
- The full Hugging Face dataset is large. Use a pinned micro-set and on-demand
  asset install; never require the whole dataset for a Roboclaws demo.
- Upstream task support maps well to our cleanup-first direction: `PickTask`,
  `PickAndPlaceTask`, `PickAndPlaceNextToTask`, `PickAndPlaceColorTask`,
  `OpeningTask`, `DoorOpeningTask`, and `NavToObjTask`.
- Upstream includes mobile manipulation robots: `RBY1` and `RBY1M` are the best
  fit for Roboclaws' "moving robot with arm(s)" story. `RBY1M` is the preferred
  demo embodiment because it is a mecanum-wheel mobile manipulator / humanoid
  form. Unitree G1-like humanoids are not native in MolmoSpaces today and should
  remain future custom integration work.

Observed small-set download sizes from the public Hugging Face tree on
2026-05-07, before decompression:

| Resource | Approx. archive size | Use |
| --- | ---: | --- |
| `mujoco/scenes/procthor-10k-val/20251217` | 82 MB | First small procedural scene pack. |
| `mujoco/scenes/ithor/20251217` | 540 MB | Hand-authored rooms with articulated assets. |
| `mujoco/robots/rby1/20251224` | 8 MB | Mobile humanoid-style robot. |
| `mujoco/robots/rby1m/20251224` | 11 MB | Preferred mecanum-wheel mobile manipulator. |
| `mujoco/robots/franka_droid/20260127` | 43 MB | Fallback official pick/place benchmark robot. |
| `mujoco/objects/thor/20251117` | 1.6 GB | Avoid initially unless adding standalone objects outside the chosen scene. |
| `mujoco/grasps/droid/20251116` | 384 MB | DROID/Franka grasp annotations. |

The capability spike should record actual disk use after extraction because
archive granularity and lazy-linking behavior may change upstream.

## Demo Scenario Shortlist

Use this order; do not start with a broad "all rooms" setup.

| Priority | Scenario | Scene set | Robot | Why |
| --- | --- | --- | --- | --- |
| 1 | Cleanup: `帮我收拾这个房间` | one iTHOR or ProcTHOR room with 5 seeded misplaced objects | RBY1M target; Franka fallback if needed | The public "wow, it works" proof for robot-agent developers. |
| 2 | One-room navigation-to-object: "Go to the mug/book." | `procthor-10k-val`, same house | RBY1/RBY1M | Bring-up helper for camera, base movement, and object inventory if cleanup exposes nav gaps. |
| 3 | Articulation: "Open the drawer/cabinet/fridge." | `ithor`, one kitchen/office room | RBY1M or Franka fallback | Add only if cleanup needs visible open/close abilities. |
| 4 | One-room pick/place: "Pick up the book/cup and place it on the table." | `procthor-10k-val`, one `house_inds` value | RBY1M if planner works; Franka fallback | Internal debugging fallback, not a standalone milestone. |
| 5 | Two-room cleanup | one small ProcTHOR house with two rooms | RBY1M | Only after single-room cleanup works. |

Avoid for the first demo:

- `holodeck` and `procthor-objaverse` scene sets. They are good later, but they
  pull us toward Objaverse-scale dependencies and more visual variability.
- Full benchmark sweeps. Use benchmark task definitions as examples, not as the
  first Roboclaws product surface.
- G1-like humanoids. Use RBY1M now; revisit G1 after the MCP/scenario/scoring
  path works.

## Small Asset Strategy

The demo must work from a tiny pinned asset manifest, not from a full dataset
install.

Start with this target bundle:

```text
roboclaws-molmo-demo-v0/
  scenes:
    - procthor-10k-val: one selected house
    - ithor: one selected articulated room, only if needed for open/close
  objects:
    - prefer objects already embedded/referenced by the selected scenes
    - install standalone thor objects only if the cleanup randomizer needs them
  robots:
    - rby1m
    - franka_droid fallback
  grasps:
    - omit initially unless MolmoSpaces API-backed cleanup requires them
```

Capability spike requirements:

- Pin exact upstream asset versions in a small manifest.
- Record archive size and extracted disk size.
- Verify that the selected scenes load without installing unrelated scene sets.
- Prefer `install_scene_with_objects_and_grasps_from_path(...)` or equivalent
  on-demand installation over bulk download.
- If upstream archive granularity still downloads a larger source shard, record
  it honestly and keep the selected shard count minimal.
- First attempt should use scene-existing objects only; adding standalone objects
  is a second step because it may pull the larger object bank.

## Renderer And Embodiment Choice

Default path:

1. **MuJoCo classic** for the capability spike and CI-adjacent fake-backend
   contracts.
2. **MuJoCo Filament** for nicer public screenshots/reports if the install is
   stable on the local workstation.
3. **ManiSkill** only as a follow-up visual/runtime comparison after the MuJoCo
   MCP path works.
4. **Isaac Sim / Isaac Lab** deferred.

Robot path:

1. **RBY1M** is the target embodiment for the visible Roboclaws demo because it
   is a moving robot with arms and fits the household cleanup story.
2. **RBY1** is acceptable for mobile navigation and object-search checks.
3. **Franka DROID / Franka FR3** remain fallback bring-up robots because they
   align with upstream pick/place benchmarks.
4. **G1-like humanoid** remains future work. It likely requires importing an
   external MuJoCo model, creating robot config/view/controller bindings, and
   designing locomotion or whole-body-control assumptions before it can be a
   credible Roboclaws demo.

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
        +--> observe / scene_objects / goto / pick / place / open / close / done
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
- `goto(object_id | location_id, distance=...)`
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
- Manipulation responses must include a provenance field:
  `real`, `api_semantic`, `scripted`, or `shim`.

## First Demo: Cleanup-First Semantic Manipulation

Goal: natural-language room cleanup that is impressive as a runnable demo and
honest as an engineering artifact.

Example:

```text
帮我收拾这个房间
```

Expected tool flow:

```text
observe -> scene_objects -> goto -> pick/place/open/close as needed -> observe -> done
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
- `trace.jsonl` records all tool calls, result status, state delta, and
  primitive provenance.
- `run_result.json` records backend, scenario id, seed, final status, artifact
  paths, score summary, and primitive provenance summary.
- `report.html` shows initial room, final room, restored/missed object table,
  primitive provenance, and tool trace.
- The report states whether `pick` / `place` / `open` / `close` used real
  MolmoSpaces behavior, API-backed semantic manipulation, a scripted planner, or
  a temporary shim.
- A robot-agent developer can rerun the demo through the existing
  `just code::codex` / `just code::cc` workflow shape.

## Task Slices

These are approved vertical slices. The capability spike above makes the first
GSD handoff concrete enough to proceed, but only for the narrow
`api_semantic` cleanup path.

1. **Cleanup capability spike**
   Completed locally on 2026-05-07. Keep the result in this plan as source
   context; do not repeat broad config-instantiation probes in GSD.

2. **Provenance and fake-backend contract**
   Define the primitive provenance enum and fake-backend response shapes before
   real MolmoSpaces code. Reuse existing trace/report patterns where possible
   and keep additive compatibility with current trace consumers. This is the
   first GSD implementation slice.

3. **Scenario builder and scoring**
   Add seeded room messiness outside MCP, private manifest, state-delta scoring,
   and report rendering. Use `tdd` for manifest parsing, scorer behavior, and
   privacy boundaries.

4. **Direct MCP cleanup demo**
   Add the minimal MolmoSpaces MCP server/entry point, then run
   `帮我收拾这个房间` through a coding agent and validate 3-of-5 cleanup on an
   easy seed. The first implementation may use `api_semantic` MuJoCo state
   changes, but must label that provenance in `trace.jsonl`, `run_result.json`,
   and `report.html`. Keep failures visible in `run_result.json` and the
   report.

5. **OpenClaw follow-up**
   Reuse the working MCP surface through OpenClaw only after the direct cleanup
   demo is stable. Split this into a separate GSD phase if direct MCP cleanup is
   not stable quickly.

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
- API-backed semantic manipulation behavior, with provenance labels.
- End-to-end cleanup coding-agent run restoring at least 3 of 5 misplaced
  objects.

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
| MolmoSpaces local install or APIs do not support the needed loop. | Stop after capability spike, document exact blocker, and do not fake cleanup success. |
| API-backed semantic behavior or scripted shim becomes indistinguishable from real manipulation. | Store primitive provenance in `run_result.json`, trace events, and report. |
| Cleanup prompt is too open and produces noisy failures. | Seed easy scenarios first, cap to 5 misplaced objects, require 3/5 restored. |
| Local-only validation gets implied as cloud-validated. | File/use a `local-dev` validation issue with exact commands and artifacts. |
| Scope expands into territory/multi-agent before one-agent works. | Keep territory and multi-agent explicitly deferred until cleanup evidence exists. |
| Large scene inventory overwhelms context. | Filter by visible/relevant types and cap response size. |
| Object/receptacle IDs drift between observe and action. | Use stable IDs or explicit stale-object errors. |

## Deferred

- Multi-agent MolmoSpaces.
- Territory/coverage on MolmoSpaces.
- Low-level arm control and VLA action experts.
- Isaac Lab humanoid migration.
- Full backend-neutral simulator abstraction.
- Split-model navigation optimization.
- Raising cleanup beyond 3-of-5 until the first easy cleanup demo works.

## GSD Handoff Trigger

The 2026-05-07 local capability spike identifies enough concrete MolmoSpaces /
MuJoCo APIs for a narrow GSD phase. The handoff is allowed with these limits:

- Optionally run `to-issues` first if the work should be divided across multiple
  agents or tracked in GitHub Issues.
- Add/update the phase in `.planning/ROADMAP.md`.
- Create `.planning/phases/<phase>/` from this doc.
- Let GSD own execution, validation, summaries, and shipped state.
- Keep the first phase scoped to `api_semantic` cleanup, fake-backend contracts,
  scorer, artifact schema, report rendering, and direct coding-agent MCP.
- Defer real RBY1M/Franka planner-backed manipulation and OpenClaw until the
  direct MCP cleanup artifact is stable and explicitly provenance-labeled.

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
| Make `帮我收拾这个房间` the first public proof instead of a separate pick/place milestone. | Accepted in office-hours follow-up. |
| Split OpenClaw follow-up if direct cleanup is unstable. | Accepted as guidance. |

## Current Workflow State

```text
completed:
  gsd-ingest-docs docs/plans/molmospaces-manipulation-spike.md
  gsd-plan-phase 06-molmospaces-api-semantic-cleanup
  gsd-execute-phase 06-molmospaces-api-semantic-cleanup
  gsd-verify-work 06-molmospaces-api-semantic-cleanup

next only after explicit scope approval:
  optional MolmoSpaces Python 3.11 adapter/subprocess
  real RBY1M/Franka planner-backed manipulation proof
  OpenClaw cleanup-agent integration
```

<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0525-autoplan-restore-20260527-231144.md -->
# Isaac Lab MolmoSpaces Backend Support

**Status:** CI-safe fake backend scaffold plus local runtime preflight,
local GPU real-mode Phase A smoke proof, Phase B static robot-view evidence
path, Phase C selected USD-binding diagnostics, strict full-cleanup Isaac report
gate, and Phase E segmentation diagnostics/gates, real-mode snapshot
provenance, and backend semantic-pose state diagnostics implemented;
local GPU MolmoSpaces USD scene indexing, selected USD binding, and one-object
cleanup/report parity now pass over `procthor-10k-val` scenes `val_0` and
`val_1`. Strict cross-scene binding now rejects loose generic-category object
fallback, scene-index scenario generation selects real USD objects/receptacles
when default selected handles do not bind, and the public cleanup worklist now
prefers public USD scene-index fixture candidates over stale map-bundle fixture
ids for scene-specific Isaac runs. Raw composed MolmoSpaces USD semantic AOV
still collapses to `BACKGROUND`, but a flattened semantic USD with labels
authored on final renderable descendants and
`segmentation_semantic_filter=usd_prim_path` now proves selected-object
segmentation evidence. The current integration slice is explicit prepared-USD
handoff, not default cleanup segmentation. Manipulation is still explicitly
`isaac_semantic_pose`, not planner-backed.
**Created:** 2026-05-27
**Last updated:** 2026-05-29
**Source:** MolmoSpaces renderer/backend research and Isaac Lab support
discussion.
**Workflow:** Pre-GSD plan reviewed through `intuitive-flow` autoplan intake;
use this file as the canonical implementation source and closeout ledger.

## Problem

Roboclaws currently proves household cleanup through a MolmoSpaces/MuJoCo
backend. That path is good for stable scene state, current upstream benchmark
compatibility, and visible cleanup reports, but the visual result is limited by
MuJoCo's renderer choices. MuJoCo Filament can improve some images, but local
comparison did not show a clear enough win to make it the default.

MolmoSpaces also publishes assets for Isaac Sim / Isaac Lab through USD, and
Isaac can provide a more realistic renderer and richer sensor outputs. However,
this is not a renderer-only swap. The current Roboclaws backend directly uses
MuJoCo `MjModel`, `MjData`, `qpos`, MuJoCo fixed cameras, body names, joints,
and free-joint state mutation. Isaac Lab would need its own runtime adapter
over USD prims, articulations, sensors, and renderer outputs while preserving
the same public cleanup/MCP contract.

## Goal

Add an Isaac Lab backend variant that can run the current household-cleanup
style flow with MolmoSpaces scenes:

- load a MolmoSpaces USD scene into Isaac Sim / Isaac Lab;
- expose the same public Roboclaws cleanup tools and report shape used by the
  current MolmoSpaces backend;
- capture FPV, chase, verification, and optional segmentation evidence from
  Isaac cameras;
- execute a bounded semantic cleanup loop over one small scene;
- keep all Isaac-specific dependencies and runtime state outside the core
  Roboclaws `.venv/`;
- label early results honestly as `isaac_semantic_pose` or equivalent, not as
  planner-backed manipulation.

The target first proof is backend parity for a cleanup report, not a full
Isaac Lab RL benchmark and not real manipulation control.

## Non-Goals

- Do not replace the current MuJoCo backend as the default truth path.
- Do not treat Isaac Sim as a drop-in renderer behind the MuJoCo state model.
- Do not add Isaac Lab dependencies to the core Roboclaws `.venv/`.
- Do not claim RBY1M or humanoid planner-backed manipulation from pose edits.
- Do not raise RAW_FPV or cleanup default render resolution globally.
- Do not build a full Isaac Lab training task, reward stack, or leaderboard
  integration in the first phase.
- Do not block existing MolmoSpaces cleanup, visual-grounding, or Agibot work
  on Isaac support.

## Autoplan Review Decisions

The `intuitive-flow` autoplan precheck accepted the plan with scope-preserving
implementation constraints. Outside Codex/Claude subagent voices were not run:
the supported repo route forbids bare host coding-agent launches, and no
subagent tool is available in this session. The primary review inspected the
current cleanup subprocess seam, direct cleanup runner, just facade, and
contract tests.

### Accepted Decisions

| # | Area | Decision | Rationale |
|---|------|----------|-----------|
| 1 | Scope | Keep the full Isaac backend objective, but execute it as ordered vertical slices from runtime smoke through semantic cleanup parity. | The plan is too hardware-sensitive for one unverified jump, but slicing does not reduce the final state. |
| 2 | Backend seam | Add `IsaacLabSubprocessBackend` beside `MolmoSpacesSubprocessBackend`; do not import Isaac from normal Roboclaws modules. | This matches the existing heavy-runtime subprocess boundary and preserves the core `.venv/`. |
| 3 | Provenance | Use a dedicated `isaac_semantic_pose` primitive provenance in all Phase D semantic-pose responses. | `api_semantic` is MuJoCo-shaped today; Isaac pose edits need honest, distinct labeling. |
| 4 | Command surface | Keep `household-cleanup` as the public task and add a local-dev backend selector rather than a new public task. | This preserves task/profile layering and makes Isaac a backend variant. |
| 5 | Test strategy | Add CI-safe protocol/unit tests with a fake worker path, plus local-only real Isaac acceptance commands. | CI can prove routing, schema, provenance, and no-import boundaries; real renderer/GPU proof remains local-dev evidence. |
| 6 | Report shape | Extend `run_result.json` with `isaac_runtime` diagnostics and segmentation status instead of changing agent-facing MCP fields. | Diagnostics belong in backend/report evidence; private or simulator segmentation must not leak into Agent View. |
| 7 | Map source | Keep public map/fixture context from the existing map bundle until a separate USD map-projection parity gate exists. | Avoids silently changing the Runtime Metric Map contract while backend mapping is immature. |

### Post-AOV Integration Decision

On 2026-05-29, local GPU AOV probes narrowed the MolmoSpaces segmentation issue
to raw composed USD semantics, not Isaac semantic AOV as a whole. The first
integration path is a prepared-artifact boundary:

- run `prepare_molmospaces_flattened_semantic_usd.py` before cleanup to produce
  `scene_semantic.usda` and `summary.json`;
- require the prep summary to be `ready`, with matched metadata entries and
  renderable Mesh/Gprim labels;
- pass the prepared USD explicitly into the local Isaac probe or cleanup smoke;
- request segmentation with `segmentation_semantic_filter=usd_prim_path`;
- keep online flatten/label prep out of cleanup backend init until multiple
  scenes prove the prepared-artifact gate;
- keep public `household-cleanup` defaults unchanged and keep this path on
  maintainer/local-dev commands until the boundary is stable.

### Implementation Task Order

1. **Runtime smoke scaffold**: create the isolated worker script, runtime
   diagnostics schema, nonblank image writer, and no-normal-startup Isaac
   import test.
2. **Backend protocol**: add `IsaacLabSubprocessBackend`, command timeouts,
   JSON parsing/error handling, and fake-worker tests for `init`, snapshots,
   robot views, and semantic cleanup primitives.
3. **Run facade integration**: add `backend=isaaclab_subprocess` to the direct
   `household-cleanup` route while keeping `world-labels` defaults unchanged.
4. **Semantic cleanup parity**: make one-object direct cleanup produce
   `run_result.json`, `trace.jsonl`, `report.html`, Isaac robot-view timeline
   artifacts, and `primitive_provenance=isaac_semantic_pose`.
5. **Local-dev real Isaac proof**: run the real `.venv-isaaclab/` command on a
   GPU/Isaac host and record unresolved USD/segmentation mapping blockers.

### Verification Expectations

- Focused CI-safe tests cover:
  - the new backend wrapper and worker protocol;
  - direct cleanup runner acceptance for `backend=isaaclab_subprocess` using a
    fake worker;
  - just/task routing for `backend=isaaclab_subprocess`;
  - report/checker handling of `isaac_runtime` diagnostics and
    `isaac_semantic_pose` provenance;
  - no Isaac package import during normal Roboclaws module import.
- Local-dev acceptance remains required before claiming Phase A/B real Isaac
  success. Start with the preflight gate, then run the worker and cleanup
  commands only after `.venv-isaaclab/` is ready:

  ```bash
  just agent::harness molmo-isaac-runtime-preflight

  just agent::harness molmo-isaac-runtime-smoke

  # Phase B / full cleanup parity must pass a caller-supplied MolmoSpaces/local USD path.
  just agent::harness molmo-isaac-cleanup-smoke \
    scene_usd_path=/path/to/molmospaces-scene.usd

  .venv-isaaclab/bin/python scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
    --state-path output/isaaclab/smoke/state.json \
    init --run-dir output/isaaclab/smoke --scene-source procthor-10k-val --scene-index 0

  just task::run household-cleanup direct world-labels \
    backend=isaaclab_subprocess seed=7 generated_mess_count=1
  ```

### Implementation Evidence

The CI-safe scaffold implements task-order items 1-4 with a fake Isaac worker
protocol:

- `IsaacLabSubprocessBackend` runs behind the existing `household-cleanup`
  surface as `backend=isaaclab_subprocess`.
- The worker records Isaac runtime diagnostics, writes nonblank placeholder
  image artifacts, emits robot view keys `fpv`, `chase`, `map`, and `verify`,
  and labels segmentation as unavailable/blocked instead of fabricating visual
  grounding proof.
- The report now records scene-load status, rendering-proof status, and
  explicit mapping gaps so fake protocol artifacts cannot be mistaken for real
  Isaac renderer/USD scene evidence.
- Cleanup primitive provenance is `isaac_semantic_pose`; reports explicitly do
  not claim planner-backed or physical-robot manipulation.
- Fake-worker cleanup can align to the selected Nav2 map bundle
  `assets/maps/molmospaces-procthor-val-0-7`.
- `scripts/isaac_lab_cleanup/check_isaac_lab_runtime.py` adds the local-dev
  Isaac runtime preflight gate. It records Python 3.12, `uv`, disk, NVIDIA GPU,
  `.venv-isaaclab/`, Isaac Sim, Isaac Lab, and Torch readiness in
  `output/isaaclab/preflight/.../preflight.json`, writes a reproducible
  `install_isaac_lab_runtime.sh`, and only attempts to create/install the
  isolated runtime when both `--install` and `--accept-nvidia-eula` are passed.
- `just agent::harness molmo-isaac-runtime-preflight` exposes that preflight
  through the maintainer harness without adding a new public task name.
- `scripts/isaac_lab_cleanup/check_isaac_lab_runtime_smoke_result.py` and
  `just agent::harness molmo-isaac-runtime-smoke` add a strict local proof gate
  for Phase A. The checker rejects import-only real mode, placeholder visuals,
  and unproven USD stage loading so the current scaffold cannot be mistaken for
  real Isaac renderer or scene-load evidence.
- `scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py` now has a real-mode
  Phase A smoke path: after `.venv-isaaclab/` is installed, `init` attempts to
  launch Isaac Lab through `AppLauncher`, load a generated local USD stage,
  capture one RGB camera frame, and mark rendering/USD diagnostics as proven
  only if that image exists. CI tests monkeypatch this helper to verify the
  diagnostics contract without importing Isaac.
- The real-mode worker and local smoke harness now accept a caller-supplied
  local USD path for Phase B probing. When a local USD is loaded, the worker
  records `scene_index_diagnostics`, USD-derived object/receptacle candidate
  counts, and USD prim paths when current path heuristics can identify them.
  The strict smoke checker can require this USD scene index so missing
  object/receptacle parity remains a visible blocker instead of a silent pass.
- The real-mode worker now captures FPV, chase, map, and verification images
  from the loaded USD scene during init and carries them into `robot_views`
  calls as static Isaac camera evidence. The local smoke harness runs the
  `robot_views` command after init, and the checker can now require nonblank
  Isaac robot-view images with non-placeholder provenance. This is Phase B
  camera-evidence plumbing only: semantic pose edits are still tracked in
  backend JSON state and are not rendered back into Isaac USD state.
- The worker now records `scene_binding_diagnostics` for public cleanup
  objects and target receptacles. Generated smoke USDs include the selected
  cleanup objects plus their source and target receptacles, one-object Isaac
  scenarios are aligned to the selected private target instead of the first
  arbitrary fixture object, and `run_result.json` / `report.html` surface the
  selected binding counts without exposing private scoring truth to the agent.
  `scripts/isaac_lab_cleanup/check_isaac_lab_runtime_smoke_result.py` and
  `just agent::harness molmo-isaac-runtime-smoke` can now require selected
  cleanup handles to bind to USD prims through `--require-selected-usd-bindings`.
- `scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py` now has
  report-level Isaac gates for full cleanup runs:
  `--require-isaac-real-runtime`, `--require-isaac-scene-loaded`,
  `--require-isaac-selected-usd-bindings`,
  `--require-isaac-robot-view-provenance`, and
  `--require-isaac-semantic-pose`. The private
  `just agent::harness molmo-isaac-cleanup-smoke` command runs the existing
  `household-cleanup`-shaped direct entrypoint with
  `backend=isaaclab_subprocess` and applies those strict report gates, so real
  cleanup report parity has one local-dev acceptance command once
  `.venv-isaaclab/` is available.
- The real-mode camera path now requests Isaac semantic and instance
  segmentation outputs and records report-only `isaac_segmentation_diagnostics_v1`
  evidence. When Isaac returns label-mapped segmentation tensors, the worker
  derives bounded bbox candidates and selected-USD-hit counts; otherwise the
  report records an explicit segmentation blocker. The new smoke/checker gates
  `--require-segmentation-evidence` and
  `--require-isaac-segmentation-evidence` reject missing tensors, missing bbox
  candidates, missing selected-USD matches, agent-facing leakage, and simulator
  label fallback.
- The explicit prepared-USD handoff now reaches both local-dev entrypoints:
  `molmo-isaac-runtime-smoke` and `molmo-isaac-cleanup-smoke` accept
  `segmentation_semantic_filter=usd_prim_path`, and the cleanup CLI forwards
  `--isaac-segmentation-semantic-filter` into `IsaacLabSubprocessBackend`
  without enabling segmentation by default.
- Real-mode snapshot calls now reuse the captured Isaac RGB frame instead of
  drawing placeholder images. `run_result.json` records `snapshot_artifacts`
  with provenance, static-capture status, and `semantic_pose_rendered=false`;
  the strict cleanup checker can require this through
  `--require-isaac-snapshot-provenance`. This still does not claim that later
  semantic pose edits are rendered back into the USD stage.
- Phase D semantic controls now maintain `semantic_pose_state` under
  `isaac_runtime`, recording backend JSON object poses, articulation state, USD
  prim handles, and per-tool mutation events. The report now renders reviewable
  `Semantic Pose State` and `Semantic Pose Events` tables, and the
  `--require-isaac-semantic-pose` checker gate verifies that the report and
  JSON state show `isaac_semantic_pose`, `rendered_to_usd=false`,
  `planner_backed=false`, and `physical_robot=false`.
- Full cleanup runs now persist `isaac_scene_index.json` as a report-only Phase
  C artifact. It carries scene-load diagnostics, object/receptacle USD indexes,
  selected binding diagnostics, segmentation diagnostics, mapping gaps, and
  explicit `agent_facing=false` / `private_manifest_exposed_to_agent=false`
  flags so USD handle evidence is reviewable without moving private scoring
  truth into Agent View. The strict selected-USD-binding checker gate now
  requires this artifact when asserting real cleanup parity.
- The cleanup report now expands `isaac_scene_index.json` into selected USD
  binding rows and the corresponding USD index rows. The strict
  selected-USD-binding checker verifies that those rows render the selected
  USD handles and prim paths, so real Isaac cleanup parity must be visible in
  both JSON artifacts and `report.html`.
- The Isaac runtime smoke checker now rejects count-only selected binding
  claims. `--require-selected-usd-bindings` requires selected object and target
  receptacle binding rows with bound status, USD handles, USD prim paths,
  match strategy, USD-stage index provenance, and no private manifest payload.
- The same smoke gate now cross-checks selected binding rows against the
  emitted USD `object_index` / `receptacle_index`, so selected handles must
  point at indexed USD prim paths rather than standalone row claims.
- The full cleanup checker now applies the same row/index rigor to
  `--require-isaac-selected-usd-bindings`: selected binding rows must carry
  USD handles, prim paths, `index_source=usd_stage_traversal`, non-empty match
  strategies, no private manifest payload, and USD prim paths that match the
  report-only `isaac_scene_index.json` object/receptacle indexes.
- The same full-cleanup gate now rejects drift between
  `run_result.json["isaac_runtime"]["scene_binding_diagnostics"]` and
  `isaac_scene_index.json["scene_binding_diagnostics"]`, so report-only USD
  evidence cannot silently disagree with the runtime diagnostics it is meant to
  render.
- When strict Isaac segmentation evidence is required alongside selected USD
  bindings, the full-cleanup checker now also cross-checks
  `isaac_scene_index.json["segmentation"]` against the runtime segmentation
  diagnostics in `run_result.json`, including candidate counts, selected USD
  hits, candidate bbox rows, provenance fields, and agent-facing/private-boundary
  flags.
- When strict selected USD bindings and semantic pose evidence are both
  required, the full-cleanup checker now cross-checks semantic pose object,
  support, articulation, and mutation-event USD prim paths against the selected
  binding rows and `isaac_scene_index.json` object/receptacle indexes. Semantic
  pose diagnostics can no longer point at unrelated USD prim paths while still
  passing the strict cleanup report gate.
- The strict semantic-pose gate now also verifies that `report.html` renders
  the semantic object/support USD rows, articulation USD rows, and mutation
  event USD paths. A run cannot pass with semantic pose state present only in
  JSON while the human report omits the reviewable pose evidence.
- The same gate now checks `trace.jsonl` for successful semantic primitive
  responses with `primitive_provenance=isaac_semantic_pose`, `isaac_*` state
  mutations, and trace tool coverage matching the backend semantic pose events.
  This keeps Phase D trace evidence aligned with `run_result.json` and
  `report.html`.
- Strict real-mode smoke and full-cleanup gates now require runtime diagnostics
  named by the plan: Python, Isaac Sim, Isaac Lab, CUDA/GPU/VRAM, renderer
  mode, and camera resolution. A run can no longer pass strict real Isaac gates
  with only `runtime_mode=real` and `real_rendering_proven=true` booleans.
- Strict loaded-scene gates now require a concrete readable `scene_usd` path,
  `loaded_asset_kind`, and `manual_editor_steps_required=false`. This keeps
  Phase A/B smoke and full-cleanup proof from passing on a status-only
  `usd_stage_loaded=true` claim or on scene setup that still requires manual
  editor steps.
- Strict Phase B/full-cleanup local-scene gates can now require
  `loaded_asset_kind=local_scene_usd`. The cleanup smoke harness defaults this
  gate on and fails early without `scene_usd_path=...`, so a generated Phase A
  USD smoke scene cannot be mistaken for caller-supplied MolmoSpaces/local USD
  scene parity.
- Strict full-cleanup Isaac robot-view and snapshot provenance gates now verify
  that the referenced artifacts are readable, nonblank RGB images. Provenance
  strings and nonempty placeholder files are no longer enough to satisfy the
  real Isaac visual-evidence checks.
- Full cleanup `run_result.json` now carries the report-only Isaac
  object/receptacle USD indexes, and the strict `isaac_scene_index.json` gate
  cross-checks those indexes against the runtime payload. The scene-index
  artifact can no longer drift to unrelated non-selected USD prim rows while
  selected binding rows still happen to pass.

Real `.venv-isaaclab/` execution on this GPU host now proves Phase A renderer
and generated-USD plumbing. It also proves a first Phase B/Phase C/Phase D
slice over one real MolmoSpaces USD scene: scene load, USD object/receptacle
indexing, selected cleanup handle binding, static Isaac robot-view provenance,
snapshot provenance, and one-object semantic cleanup/report parity. It still
does not prove Isaac segmentation or planner-backed manipulation.

Latest installing local preflight, run on 2026-05-28 with the NVIDIA/Omniverse
EULA accepted by the human:
`just agent::harness molmo-isaac-runtime-preflight install=true
accept_nvidia_eula=true strict=true` wrote
`output/isaaclab/preflight/0528_115717/preflight.json` with `status=ready`.
The host recorded Python 3.12, `torch==2.7.0+cu128`, Isaac Lab `0.54.3`,
Isaac Sim import readiness, and an NVIDIA RTX 3500 Ada GPU.

Latest local Phase A smoke, run on 2026-05-28:
`just agent::harness molmo-isaac-runtime-smoke` wrote
`output/isaaclab/runtime-smoke/0528_1223/` and the strict checker returned
`status=passed`. Evidence includes `state.json`, `init_result.json`,
`isaac_runtime_smoke.png`, FPV/chase/map/verify robot-view images, generated
`roboclaws_phase_a_smoke_scene.usda`, real runtime diagnostics, selected USD
binding rows, and nonblank image checks. No stale Isaac worker or telemetry
process remained after the run.

Latest generated-local-USD cleanup smoke, run on 2026-05-28:
`just agent::harness molmo-isaac-cleanup-smoke
scene_usd_path=output/isaaclab/runtime-smoke/0528_1223/roboclaws_phase_a_smoke_scene.usda`
wrote `output/isaaclab/cleanup-smoke/0528_1226/` and the strict cleanup checker
returned `molmo-realworld-cleanup ok`. Evidence includes `run_result.json`,
`trace.jsonl`, `report.html`, `isaac_scene_index.json`, real Isaac runtime
diagnostics, nonblank before/after images, FPV/chase/map/verify robot-view
timelines, `primitive_provenance=isaac_semantic_pose`, and a successful
one-object deterministic cleanup score. This proves the cleanup/report path over
a generated local USD scene, not MolmoSpaces scene parity.

MolmoSpaces USD scene download/probe, run on 2026-05-28:
the upstream `molmo_spaces_isaac` downloader source was available from the local
uv git checkout, and R2 access to `isaac-thor-resources` worked from this
mainland-China host. The USD `procthor-10k-val` manifest reported about 64GB
available data in on-demand mode; only `procthor-10k-val_val_0.tar.zst`
(`58.063` MB) was downloaded and linked to
`output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_0/scene.usda`.

Dependency/version check, run on 2026-05-28:
official Isaac Sim/Isaac Lab latest docs now target Isaac Sim 6.x on Python
3.12 and show `isaacsim[all,extscache]==6.0.0` with the NVIDIA package index.
The local isolated runtime matches that direction for Roboclaws:
Python 3.12.12, `isaacsim==6.0.0.0`, Torch `2.7.0+cu128`, and an Isaac Lab
source checkout at commit `84d0ff0`. The upstream pinned
`molmo_spaces_isaac` checkout remains asset/USD tooling rather than the
Roboclaws runtime dependency: its `sim` extra is
`isaaclab[all,isaacsim]>=2.3.1`, its README says that install path pulls
IsaacSim 5.1.0 and IsaacLab 2.3.1, and its package metadata still targets
`>=3.11`. Tsinghua TUNA simple index checks from this host returned entries for
`isaacsim`, `isaaclab`, and `torch`, but returned 404 for `molmo-spaces` and
`molmo-spaces-isaac`; direct GitHub, NVIDIA, and PyTorch CUDA indexes remain
part of the real setup path.

The first real-scene runtime smoke against that USD failed on 2026-05-28:
`just agent::harness molmo-isaac-runtime-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_0/scene.usda
require_local_scene_usd=true stamp=0528_val0_blank_gate` then failed quickly
with `Isaac Lab camera RGB tensor was blank for fpv`. The failure run wrote
`output/isaaclab/runtime-smoke/0528_val0_blank_gate/init_result.json` and left
no stale Isaac worker or telemetry process after the failure-path cleanup fix.

That real-scene blocker was resolved by dynamically deriving camera poses from
the loaded USD stage bounds, adding smoke lighting, indexing MolmoSpaces
`scene_metadata.json`, and resolving synthetic public cleanup ids such as
`mug_01` through selected USD binding diagnostics.

Latest MolmoSpaces USD runtime smoke, run on 2026-05-28:
`just agent::harness molmo-isaac-runtime-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_0/scene.usda
require_local_scene_usd=true stamp=0528_val0_metadata_index`
wrote `output/isaaclab/runtime-smoke/0528_val0_metadata_index/` and passed the
strict checker. Evidence records `scene_index_status=indexed`,
`stage_prim_count=308`, `object_candidate_count=86`,
`receptacle_candidate_count=29`, `scene_binding_status=selected_bound`, and no
scene-index blockers. The selected public object `mug_01` is bound by
`public_id_prefix_first` to
`/val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6`; the selected
sink target is bound to
`/val_0/Geometry/sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_5`. Both selected
rows use `index_source=usd_stage_traversal`.

Latest MolmoSpaces USD cleanup-shaped smoke, run on 2026-05-28:
`just agent::harness molmo-isaac-cleanup-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_0/scene.usda
stamp=0528_val0_semantic_path_cleanup`
wrote `output/isaaclab/cleanup-smoke/0528_val0_semantic_path_cleanup/` and the
strict cleanup checker returned `molmo-realworld-cleanup ok`. Evidence includes
`run_result.json`, `trace.jsonl`, `report.html`, `isaac_scene_index.json`,
real Isaac runtime diagnostics, readable nonblank before/after snapshots,
FPV/chase/map/verify robot-view provenance, selected USD binding rows, and
semantic pose events whose object/support/articulation USD paths resolve through
the selected binding diagnostics. The run completed one deterministic cleanup
with `backend=isaaclab_subprocess`, `cleanup_status=success`, and
`primitive_provenance=isaac_semantic_pose`.

Additional MolmoSpaces USD scene broadening, run on 2026-05-28:
`procthor-10k-val_val_1.tar.zst` (`125.204` MB) was downloaded from the same
R2-backed USD manifest and linked to
`output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda`.
`just agent::harness molmo-isaac-runtime-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
require_local_scene_usd=true stamp=0528_val1_runtime_smoke` passed the strict
runtime checker with real Isaac RGB/robot-view evidence, `stage_prim_count=110`,
`object_candidate_count=18`, `receptacle_candidate_count=11`, and
`scene_binding_status=selected_bound`. `just agent::harness
molmo-isaac-cleanup-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
stamp=0528_val1_cleanup_smoke` also returned `molmo-realworld-cleanup ok`.
This broadens local GPU scene-load, RGB, indexing, selected-binding, report,
and semantic-pose cleanup evidence beyond `val_0`, but it is not yet exact
scene-specific cleanup truth: the public cleanup scenario still comes from
`assets/maps/molmospaces-procthor-val-0-7`, so public `mug_01` rebound to
`/val_1/Geometry/sponge_41cc9aa65073b4cd1fc4d9871335148d_1_0_3` through
`semantic_label_token_first`, while the sink rebound by prefix to
`/val_1/Geometry/sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3`.

Strict cross-scene binding follow-up, implemented on 2026-05-28:
generic public cleanup object buckets such as `dish`, `book`, `food`,
`electronics`, `linen`, and `toy` no longer drive category-token USD fallback
for selected objects. Specific object labels and exact/prefix USD handles still
bind, so `val_0` continues to bind public `mug_01` to a real Mug USD prim while
`val_1` now reports public `mug_01` as unresolved instead of binding it to
DishSponge. Focused unit coverage verifies both the rejected DishSponge fallback
and the preserved specific unique-category path. Existing local checker
evidence:

- `output/isaaclab/runtime-smoke/0528_val0_strict_binding_runtime/` passes the
  strict runtime smoke checker with `scene_binding_status=selected_bound`,
  selected object `mug_01 -> /val_0/Geometry/mug_3ebc45568ed53a18c8797978b3744a99_1_0_6`,
  and selected sink target bound by exact public id.
- `output/isaaclab/runtime-smoke/0528_val1_strict_binding_runtime/` fails the
  strict selected-USD-binding checker as intended with
  `scene_binding_status=partial` and blocker
  `Selected cleanup object has no USD binding: mug_01`.

Scene-index cleanup parity follow-up, implemented and locally verified on
2026-05-28:
when a real Isaac scene does not bind the default map-bundle selected cleanup
object, the worker generates a one-object cleanup scenario from the loaded USD
scene index. The public cleanup contract keeps the existing static map-bundle
coverage waypoints but adds a public USD scene-index fixture overlay ahead of
the stale map-bundle fixtures, so observed scene objects route to scene-local
public receptacles instead of old fixture ids. The worker also infers
`scene_index` from caller-supplied `.../val_<n>/scene.usda` paths, so local
proof artifacts no longer report `scene_index=0` for `val_1` runs.

Latest exact `val_1` cleanup-shaped smoke, run on 2026-05-28:
`just agent::harness molmo-isaac-cleanup-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
stamp=0528_val1_scene_overlay_indexed_cleanup` wrote
`output/isaaclab/cleanup-smoke/0528_val1_scene_overlay_indexed_cleanup/` and
the strict cleanup checker returned `molmo-realworld-cleanup ok`. Evidence
records `scenario_id=isaac-scene-index-procthor-10k-val-1-7-1`,
`scene_index=1`, `scenario_source=isaac_scene_index`, selected binding status
`selected_bound`, public worklist candidate
`sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3`, final Bowl location
`sink_07e796f32d0d3efce9acf4be00f3bc53_1_0_3`, `cleanup_status=success`,
and `primitive_provenance=isaac_semantic_pose`.

Segmentation opt-in probe, run on 2026-05-28:
`just agent::harness molmo-isaac-runtime-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
require_local_scene_usd=true stamp=0528_val1_segmentation_probe
require_segmentation_evidence=true` now requests Isaac segmentation tensors
through `--enable-segmentation`, but the local Isaac/Omniverse process aborts
before writing a worker state. The captured log at
`output/isaaclab/runtime-smoke/0528_val1_segmentation_probe/init_result.json`
shows `omni.syntheticdata.plugin` semantic-label AOV warnings before the
process exits with code 134 and a CUDA illegal-address coredump. No stale Isaac
worker process remained after the abort. Follow-up routing now makes
`molmo-isaac-cleanup-smoke require_segmentation_evidence=true` pass
`--isaac-enable-segmentation` into the direct cleanup runner and backend, so
segmentation-required cleanup probes actually request Isaac segmentation instead
of only enabling the final checker gate.

Post-routing default cleanup regression, run on 2026-05-28:
`just agent::harness molmo-isaac-cleanup-smoke
scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
stamp=0528_val1_seg_filter_default_cleanup` wrote
`output/isaaclab/cleanup-smoke/0528_val1_seg_filter_default_cleanup/` and the
strict cleanup checker returned `molmo-realworld-cleanup ok`. This confirms the
passing local GPU cleanup path is unchanged when segmentation remains at its
default off state after the segmentation data-type diagnostic changes.

Segmentation data-type narrowing, run on 2026-05-28:
the runtime smoke and cleanup smoke harnesses now accept
`segmentation_data_types=...`, and the backend/worker can request individual
Isaac camera annotators. The worker segmentation label parser now accepts
Isaac's list-shaped `camera.data.info` payloads, so report diagnostics record
the returned tensors instead of crashing on our own parser.

- `just agent::harness molmo-isaac-runtime-smoke
  scene_usd_path=output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda
  require_local_scene_usd=true stamp=0528_val1_seg_semantic_probe_v2
  require_segmentation_evidence=true
  segmentation_data_types=semantic_segmentation` completed worker init and
  robot-view capture, then failed the strict segmentation checker as expected.
  The artifact at
  `output/isaaclab/runtime-smoke/0528_val1_seg_semantic_probe_v2/` records
  `tensor_output_available=true`,
  `output_data_types=["semantic_segmentation"]`, `candidate_bbox_count=4`,
  and `selected_usd_prim_match_count=0`; all four candidates are full-frame
  `BACKGROUND` rows rather than selected USD prims.
- `just agent::harness molmo-isaac-runtime-smoke ...
  stamp=0528_val1_seg_instance_probe
  segmentation_data_types=instance_segmentation_fast` produced the same shape:
  `tensor_output_available=true`,
  `output_data_types=["instance_segmentation_fast"]`,
  `candidate_bbox_count=4`, and `selected_usd_prim_match_count=0`, with only
  full-frame `BACKGROUND` candidates.
- `just agent::harness molmo-isaac-runtime-smoke ...
  stamp=0528_val1_seg_instance_id_probe_v3
  segmentation_data_types=instance_id_segmentation_fast` still exits 134 inside
  Isaac/Omniverse before worker state is written. The runtime-smoke harness now
  captures stderr into `init_result.json`, so
  `output/isaaclab/runtime-smoke/0528_val1_seg_instance_id_probe_v3/init_result.json`
  contains the `CUDBG_EXCEPTION_WARP_ILLEGAL_ADDRESS` coredump line and
  `_Z20array_copy_1d_kernel...` stack frame. No stale Isaac worker process
  remained after the abort.
- Follow-up scene-index semantic labeling probes, run on 2026-05-28, apply
  `class`, `kind`, and `usd_prim_path` labels to all 29 object/receptacle USD
  prims from the loaded `val_1` scene index before camera capture. Both
  `stamp=0528_val1_seg_semantic_labeled_probe` and
  `stamp=0528_val1_seg_instance_labeled_probe` record
  `semantic_label_application.status="applied"`, `applied_count=29`,
  `failed_count=0`, and `missing_prim_count=0`, but the strict segmentation
  checker still fails. `semantic_segmentation` and
  `instance_segmentation_fast` continue to return four full-frame `BACKGROUND`
  candidates, zero selected USD prim matches, and repeated
  `OgnSdSemanticLabelsMap: invalid input AOV SemanticLabelTokenSD` warnings.
  This narrows the remaining Phase E blocker away from missing scene-index
  labels and toward the Isaac Camera/Replicator semantic AOV or render-product
  path for these loaded MolmoSpaces USD stages.
- A targeted USD reference install pass, run on 2026-05-28, uses
  `just agent::harness molmo-isaac-usd-references
  state_path=output/isaaclab/runtime-smoke/0528_val1_seg_geometry_diag_probe_v2/state.json`
  to read the worker's `missing_referenced_assets`, map them to upstream
  MolmoSpaces USD object packages, and install only the 22 required
  `objects/thor` archives from R2. The run wrote
  `output/isaaclab/molmospaces-usd/usd_reference_install_val1.json` with
  `status="ready"`, `installed=true`, `package_count=22`, and no unresolved
  assets. The installed cache is about 694 MB and exposes the expected
  `output/isaaclab/molmospaces-usd/objects/thor` symlink without pulling the
  whole Objaverse catalog.
- The follow-up strict semantic segmentation probe
  `stamp=0528_val1_seg_refs_installed_probe` confirms that USD object geometry
  now resolves: selected Bowl and Sink bindings report
  `geometry_status="renderable"`, `has_renderable_geometry=true`,
  `missing_referenced_asset_count=0`, and nonzero mesh/renderable descendant
  counts. The strict segmentation checker still fails because all four
  `semantic_segmentation` candidates remain full-frame `BACKGROUND` rows with
  `selected_usd_prim_match_count=0`, and Isaac logs
  `OgnSdSemanticLabelsMap: invalid input AOV SemanticLabelTokenSD`. This closes
  the missing referenced USD object asset blocker and leaves the semantic AOV
  path as the active segmentation blocker.
- A cache-link compatibility follow-up, run on 2026-05-28, extends the targeted
  reference installer to expose versioned MolmoSpaces object assets at both
  `~/.molmospaces/usd/objects/thor/<asset>` and
  `~/.molmospaces/usd/scenes/objects/thor/<asset>`. The latter is the path
  Isaac Kit resolves from scene payload references such as
  `../../../../objects/thor/Bowl_12_mesh/Bowl_12_mesh.usda`. The run wrote
  `output/isaaclab/molmospaces-usd/usd_reference_install_val1_scene_object_links.json`
  with `status="ready"`, `conflict_count=0`, and 26
  `kit_scene_object_root` symlinks created.
- The follow-up strict semantic segmentation probe
  `stamp=0528_val1_seg_scene_object_links_probe` still failed only the strict
  segmentation checker: scene loading, RGB/robot-view capture, scene-index
  binding, and selected Bowl/Sink renderable geometry all remained valid, but
  all four `semantic_segmentation` candidates were still full-frame
  `BACKGROUND` rows. A second probe,
  `stamp=0528_val1_seg_semantic_filter_class_probe`, set IsaacLab
  `CameraCfg.semantic_filter=["class"]` and recorded that filter in the worker
  capture diagnostics; it produced the same `BACKGROUND` result and the same
  `OgnSdSemanticLabelsMap: invalid input AOV SemanticLabelTokenSD` warnings.
  This keeps the active blocker at Isaac/Replicator semantic AOV generation,
  not MolmoSpaces object package availability, scene-index labels, or semantic
  filter breadth.

Remaining limitations after the passing MolmoSpaces USD smoke runs:
raw composed-scene segmentation remains a blocked capability. Default cleanup
runs do not request segmentation tensors. Explicit local segmentation probes on
the raw composed `val_1` scene show that `semantic_segmentation` and
`instance_segmentation_fast` return tensors, but only background candidates
with no selected-USD matches, even after scene-index labels are applied to the
loaded USD prims. The proven route is to flatten the composed scene, author
semantic labels on final renderable descendants, and request
`segmentation_semantic_filter=usd_prim_path` against the prepared USD. Meanwhile
`instance_id_segmentation_fast` still aborts inside Isaac/Omniverse before
producing worker state;
semantic pose edits are tracked in backend JSON state and snapshots rather than
rendered back into the live USD stage; planner-backed/physics-backed
manipulation is still out of scope for this slice; broader scene coverage should
keep strict artifact gates enabled rather than relying on import success because
Isaac/Omniverse runtime logs still include non-fatal USD/runtime warnings.

## Architecture

Keep the current Roboclaws ladder intact:

```text
Runnable task
  -> cleanup skill / MCP tools
  -> realworld cleanup contract
  -> backend variant
  -> artifacts and report
```

The new work belongs at the backend layer:

```text
household-cleanup
  -> realworld_cleanup_v1
  -> IsaacLabSubprocessBackend
  -> scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py
  -> report.html / run_result.json / trace.jsonl
```

The public tool surface should remain compatible with the current backend:

- `observe`
- `navigate_to_object`
- `pick`
- `navigate_to_receptacle`
- `open_receptacle`
- `place`
- `place_inside`
- `close_receptacle`
- `done`
- report helpers such as `write_snapshot` and `write_robot_views`

The first backend should be subprocess-based, mirroring
`MolmoSpacesSubprocessBackend`. Isaac Lab has a heavy runtime lifecycle, so the
main Roboclaws process should communicate through JSON commands and artifacts
rather than importing Isaac directly.

## Runtime Boundary

Create an isolated Isaac runtime, for example:

```text
.venv-isaaclab/
```

Use `.venv-isaaclab/` for the first local spike. A dedicated Docker image is a
fallback only if local Isaac pip setup is too brittle to reproduce. This is a
deliberate exception to the repo's normal one-`.venv/` rule because Isaac Sim,
CUDA Torch, RTX rendering, and Omniverse dependencies should not contaminate the
core cleanup runtime.

The worker should record diagnostics in every run:

- Isaac Sim version;
- Isaac Lab version;
- Python version;
- CUDA availability;
- GPU name and VRAM when available;
- renderer mode;
- camera resolution;
- selected scene USD path;
- object/receptacle index count;
- segmentation availability.

## Scene And State Mapping

The hardest part is not launching Isaac; it is preserving Roboclaws' cleanup
semantics over a different simulator state model.

Build an `IsaacSceneIndex` that maps:

- MolmoSpaces object ids to USD prim paths;
- receptacle ids to fixture prims and support poses;
- openable receptacles to Isaac articulation/joint handles;
- object categories to public visible-detection labels;
- semantic/instance ids to report-visible object handles;
- room and fixture metadata to the existing Runtime Metric Map / fixture hints
  shape.

For the MVP, reuse the existing prebuilt map bundle for public Agent View and
report comparison. USD-derived map or projection data may be recorded as backend
diagnostics, but it should not replace the public Metric Map contract until it
has its own parity/audit gate.

The MuJoCo backend stores mutable truth in `qpos`, object body positions, and
joint positions. The Isaac backend must store equivalent public/private state in
terms of USD prim transforms, articulation states, and backend-side JSON state.

## Control Strategy

Start with semantic control, then graduate to real controllers only after the
report path is stable.

Do not require RBY1M for the first Isaac runtime and rendering smoke tests.
Phase A and Phase B may use the simplest Isaac-compatible camera/robot rig that
proves scene loading, camera capture, and report plumbing. RBY1M becomes a
target for the semantic cleanup backend only after the USD/Isaac embodiment path
is practical enough to avoid blocking renderer and scene parity work.

### Phase 1 Control: Semantic Pose Backend

Use explicit simulator state edits:

- `navigate_to_object`: set robot root/base pose near the object's current
  fixture.
- `pick`: attach the object to a held-object state and move its prim near the
  robot/gripper frame.
- `navigate_to_receptacle`: set robot root/base pose near the target fixture
  and carry the held object.
- `open_receptacle`: set a target articulation joint/open value where available.
- `place` / `place_inside`: set object prim transform to a fixture support or
  inside pose.
- `close_receptacle`: set the articulation joint back to the closed value.

Every response must report provenance such as:

```text
primitive_provenance=isaac_semantic_pose
physical_robot=false
planner_backed=false
```

### Later Control: Planner-Backed Isaac

Only after semantic backend parity is stable, add real controllers:

- base navigation controller or waypoint follower;
- arm IK or motion planner;
- grasp candidate selection;
- collision-aware place;
- articulation interaction policy.

This later layer can use Isaac Lab controllers or external planners, but it
should attach proof artifacts to cleanup substeps the same way current
planner-backed MolmoSpaces proof bundles do.

## Camera And Perception

First version should support:

- FPV camera;
- chase camera;
- verification/focus camera;
- optional map/snapshot view;
- RGB output at the same default cleanup resolution as MuJoCo today;
- optional semantic or instance segmentation when available.

Do not change the global cleanup default resolution. Use a renderer comparison
or Isaac-specific probe to test `1280x720` / 1280p images before changing
RAW_FPV or visual-grounding defaults.

Segmentation is not agent-facing in the MVP. Capture semantic or instance
segmentation as backend/report evidence first. When it becomes cleanup input,
route it through the existing camera-label producer boundary rather than adding
a new MCP tool field or exposing private simulator truth directly.

Isaac camera outputs should feed the same report and visual-grounding paths:

- `raw_fpv_observation`;
- `camera-labels` producer inputs;
- bbox overlays;
- robot view timeline;
- renderer/runtime diagnostics.

## Implementation Phases

### Phase A: Isaac Runtime Smoke

Deliver a standalone local script that:

- starts Isaac Sim / Isaac Lab headlessly or with a minimal viewer;
- loads one tiny USD scene or a MolmoSpaces USD scene if already available;
- captures one RGB image;
- writes runtime diagnostics and a small HTML or JSON artifact.
- may use the simplest Isaac-compatible camera/robot rig; RBY1M is not required
  for this phase.

Acceptance:

- one command produces a nonblank image;
- diagnostics show Isaac and GPU/runtime information;
- no Isaac package is imported by normal Roboclaws startup.

### Phase B: MolmoSpaces USD Scene Parity

Load one MolmoSpaces scene through the Isaac asset path.

Acceptance:

- scene loads without manual editor steps;
- object and receptacle counts are recorded;
- at least one FPV, one chase, and one verification image are saved;
- report diagnostics list unresolved mapping gaps.
- public map/fixture context still comes from the existing map bundle unless a
  separate USD map-projection parity gate has passed.

### Phase C: Public Object/Receptacle Index

Build the `IsaacSceneIndex`.

Acceptance:

- public scenario can be generated from Isaac scene state;
- selected cleanup objects and target receptacles are deterministic;
- private manifest remains separate from agent view;
- object/receptacle ids map to stable USD prim paths or recorded blockers.

### Phase D: Semantic Cleanup Backend

Implement `IsaacLabSubprocessBackend` behind the existing cleanup contract.

Acceptance:

- a one-object cleanup run completes `nav -> pick -> nav -> place`;
- `run_result.json`, `trace.jsonl`, and `report.html` are generated;
- report includes robot view timeline images from Isaac;
- primitive provenance is visibly `isaac_semantic_pose`;
- existing MuJoCo backend behavior is unchanged.

### Phase E: Camera/Segmentation Parity

Add segmentation or instance-id evidence if the selected Isaac renderer path
supports it reliably.

Acceptance:

- FPV RGB remains available;
- segmentation availability is recorded as explicit success or blocker;
- MolmoSpaces semantic segmentation uses an explicit prepared USD artifact
  first: `summary.json.status=ready`, matched metadata entries, renderable
  Mesh/Gprim labels, and prepared scene handoff into the local Isaac probe;
- prepared MolmoSpaces USD probes request `semantic_filter=["usd_prim_path"]`
  so selected-object bbox rows can bind back to USD prim paths;
- bbox/candidate overlays can be generated from Isaac camera evidence;
- no fallback silently substitutes MuJoCo or simulator labels.
- segmentation remains report/backend evidence or camera-label producer input,
  not a new direct agent-facing MCP field.

### Phase F: Planner-Backed Follow-Up

Only after Phases A-E are stable, scope planner-backed manipulation.

Acceptance:

- each planner-backed substep has proof evidence;
- semantic pose fallback remains clearly labeled;
- failed planner attempts produce visible blockers, not fabricated success.

## Recommended First Command Surface

Do not add a new public task name. Add a backend selector to the existing
household cleanup run shape, for local-dev only at first:

```bash
just task::run household-cleanup direct world-labels \
  backend=isaaclab_subprocess \
  seed=7 \
  generated_mess_count=1
```

Renderer comparison can use an explicit maintainer or harness command instead:

```bash
just agent::harness molmo-isaac-renderer-comparison \
  scene=procthor-val-0 \
  resolution=1280x720
```

Prepared MolmoSpaces semantic segmentation remains a maintainer/local-dev path
until broader scene coverage passes. The intended first flow is:

```bash
.venv-isaaclab/bin/python scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py \
  --scene-usd-path output/isaaclab/molmospaces-usd/scenes/procthor-10k-val/val_1/scene.usda \
  --output-usd-path output/isaaclab/flattened-semantic-usd/val_1/scene_semantic.usda \
  --summary-output output/isaaclab/flattened-semantic-usd/val_1/summary.json

just agent::harness molmo-isaac-runtime-smoke \
  scene_usd_path=output/isaaclab/flattened-semantic-usd/val_1/scene_semantic.usda \
  require_local_scene_usd=true \
  enable_segmentation=true \
  require_segmentation_evidence=true \
  segmentation_data_types=semantic_segmentation \
  segmentation_semantic_filter=usd_prim_path

just agent::harness molmo-isaac-cleanup-smoke \
  scene_usd_path=output/isaaclab/flattened-semantic-usd/val_1/scene_semantic.usda \
  require_local_scene_usd=true \
  require_segmentation_evidence=true \
  segmentation_data_types=semantic_segmentation \
  segmentation_semantic_filter=usd_prim_path
```

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Isaac install/runtime is heavy or host-specific | Local setup takes longer than backend code | Keep isolated runtime and write diagnostics first |
| MolmoSpaces USD metadata does not preserve every cleanup handle | Object/receptacle mapping gaps | Build `IsaacSceneIndex` with explicit unresolved rows |
| RTX rendering memory pressure | 1280p or segmentation may fail | Keep 540x360 default and make 1280p comparison-only |
| Implicit online USD prep hides failures | Cleanup errors become hard to separate from scene-prep errors | Use explicit prepared USD plus summary gate first; add online convenience only after multiple scenes pass |
| Articulation or collision behavior differs from MuJoCo | Open/place semantics drift | Label phase-D as semantic pose and defer planner proof |
| Report becomes backend-specific | Cleanup evidence gets harder to compare | Reuse existing report schema and add backend diagnostics only |

## Research Sources

- MolmoSpaces README: assets are usable in MuJoCo, Isaac, and ManiSkill, while
  data generation and benchmarking are only supported for MuJoCo:
  <https://github.com/allenai/molmospaces>
- MolmoSpaces Isaac package: USD asset/scene conversion and loading path:
  <https://github.com/allenai/molmospaces/tree/main/molmo_spaces_isaac>
- Isaac Lab installation:
  <https://isaac-sim.github.io/IsaacLab/develop/source/setup/installation/pip_installation.html>
- Isaac Sim system requirements:
  <https://docs.isaacsim.omniverse.nvidia.com/latest/installation/requirements.html>
- Isaac Lab cameras and renderer outputs:
  <https://isaac-sim.github.io/IsaacLab/v3.0.0-beta/source/overview/core-concepts/sensors/camera.html>
- Isaac Lab AppLauncher:
  <https://isaac-sim.github.io/IsaacLab/main/source/tutorials/00_sim/launch_app.html>

## Deferred Implementation Defaults

- First pinned scene: default to the current MolmoSpaces cleanup baseline,
  `procthor-10k-val` scene index `0`, unless the USD asset path cannot load it
  cleanly. If it fails, choose the smallest MolmoSpaces USD scene that can
  prove scene loading, camera capture, and object/receptacle indexing.
- Segmentation report shape: record semantic label and instance id when both are
  available. Choose a canonical report field only after Phase E proves the
  selected Isaac renderer path exposes stable outputs.

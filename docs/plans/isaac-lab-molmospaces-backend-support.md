<!-- /autoplan restore point: /home/mi/.gstack/projects/MiaoDX-roboclaws/dongxu-dev-0525-autoplan-restore-20260527-231144.md -->
# Isaac Lab MolmoSpaces Backend Support

**Status:** CI-safe fake backend scaffold plus local runtime preflight,
real-mode Phase A smoke attempt, Phase B static robot-view evidence path, Phase
C selected USD-binding diagnostics, strict full-cleanup Isaac report gate, and
Phase E segmentation diagnostics/gates, real-mode snapshot provenance, and
backend semantic-pose state diagnostics implemented; real Isaac proof pending
**Created:** 2026-05-27
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
- Real-mode snapshot calls now reuse the captured Isaac RGB frame instead of
  drawing placeholder images. `run_result.json` records `snapshot_artifacts`
  with provenance, static-capture status, and `semantic_pose_rendered=false`;
  the strict cleanup checker can require this through
  `--require-isaac-snapshot-provenance`. This still does not claim that later
  semantic pose edits are rendered back into the USD stage.
- Phase D semantic controls now maintain `semantic_pose_state` under
  `isaac_runtime`, recording backend JSON object poses, articulation state, USD
  prim handles, and per-tool mutation events. The report and
  `--require-isaac-semantic-pose` checker gate verify that the state is
  `isaac_semantic_pose`, `rendered_to_usd=false`, `planner_backed=false`, and
  `physical_robot=false`.

Real `.venv-isaaclab/` execution on a GPU/Isaac host remains unvalidated. Do
not claim real Isaac renderer, USD scene parity, segmentation, or planner-backed
manipulation proof from the fake protocol evidence.

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

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Isaac install/runtime is heavy or host-specific | Local setup takes longer than backend code | Keep isolated runtime and write diagnostics first |
| MolmoSpaces USD metadata does not preserve every cleanup handle | Object/receptacle mapping gaps | Build `IsaacSceneIndex` with explicit unresolved rows |
| RTX rendering memory pressure | 1280p or segmentation may fail | Keep 540x360 default and make 1280p comparison-only |
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

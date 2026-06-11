# MolmoSpaces Cleanup Profile Architecture

Status: superseded by the two-axis evidence-lane model, 2026-06-06

This note records the older one-axis cleanup-profile model. Current public
commands use `evidence_lane` plus `camera_labeler`:

```text
evidence_lane decides what the agent sees.
camera_labeler only applies to evidence_lane=camera-grounded-labels and decides
how camera labels are produced.
```

Current evidence lanes are `world-oracle-labels`, `world-public-labels`,
`camera-grounded-labels`, and `camera-raw-fpv`. `smoke` remains a cheap
synthetic verification preset, not a real evidence lane. The old names below
are retained as historical rationale and should not be copied into new command
examples.

## Problem

The current command surface mixes several separate questions:

- What does the agent actually receive as input?
- Are visual artifacts model input or report evidence?
- Which backend is running?
- Which verifier gates decide pass/fail?

The most confusing case is `visual`. In current Molmo cleanup commands,
`visual` means "produce RBY1M robot-view report artifacts." It does not mean the
agent reasons over images. The default visual cleanup run still uses structured
object detections.

The current raw/image-related names are also too implementation-shaped:

- `visible_object_detections`
- `raw_fpv_only`
- `camera_model_policy`

They make it too easy to forget which runs are structured-label runs, which runs
exercise raw image input, and which runs use simulated camera-derived labels.

## Design Direction

Expose one public cleanup evidence concept: `evidence_lane`.

Keep runtime selection orthogonal: public runs select `world`, `backend`,
`intent`, `agent_engine`, and optional `provider_profile` separately.

Do not expose `agent_input`, `report`, `world_backend`, `perception_provenance`,
or `verifier` as first-class public knobs by default. Those remain profile
metadata and report metadata.

Current canonical command shape:

```bash
just run::surface surface=household-world world=<world> backend=<backend> intent=cleanup agent_engine=<engine> [provider_profile=<profile>] evidence_lane=<lane> [camera_labeler=<labeler>]
```

Examples:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=claude-code provider_profile=mimo-anthropic evidence_lane=world-oracle-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=claude-code provider_profile=mimo-anthropic evidence_lane=camera-raw-fpv
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels
```

No backward compatibility is required for this refactor. The new names can
replace the old public names instead of preserving aliases.

## Profile Naming Principles

Profile names should answer one question: what kind of evidence does the agent
use?

Use short names that expose the agent input source:

- `world-*` means labels come from a world model, semantic map, simulator state,
  or object memory.
- `camera-*` means the camera observation is the source.
- `*-labels` means the agent receives structured object candidates or handles.
- `*-raw` means the agent receives raw camera artifacts and must infer from
  pixels or image-derived text.

Avoid names that describe only report output:

- Avoid `visual`.
- Avoid `robot-view` as a profile name.
- Use robot-view wording only inside report metadata.

Avoid simulator-specific names in the public profile:

- Avoid `sim-*`.
- Avoid `oracle`.

Simulator-vs-real provenance belongs in metadata, not in the profile name.

## Recommended Profiles

| Profile | Agent input | Default backend | Default report | What it proves |
| --- | --- | --- | --- | --- |
| `smoke` | world labels | synthetic contract | semantic report | Cheap command and contract sanity. |
| `world-labels` | world labels | MolmoSpaces sim | robot-view report | Oracle structured semantic upper bound; labels are semantic candidates until source-FPV confirmation authorizes navigation. |
| `world-labels-sanitized` | sanitized world labels | MolmoSpaces sim | robot-view report | Perfect-detector ablation: structured detections without destination/tool oracle hints or pre-confirmed navigation. |
| `camera-raw` | raw camera artifacts | MolmoSpaces sim | robot-view report | Image-input contract: structured labels are withheld. |
| `camera-labels` | camera-derived labels | MolmoSpaces sim | robot-view report | Camera-perception-label contract. Today simulated; later real detector/VLM. |

This gives humans five memorable buckets:

```text
smoke
world-labels
world-labels-sanitized
camera-raw
camera-labels
```

The names are intentionally not perfectly symmetrical with the current
implementation. They describe the durable contract.

## Profile Details

### `smoke`

Cheap deterministic confidence gate.

Expanded meaning:

```text
agent_input=world_labels
input_provenance=synthetic_contract
world_backend=synthetic_contract
report=semantic_report
verifier=contract_only
```

Use this for fast agent iteration and CI-style checks. It is not a visual
cleanup claim and does not exercise image input.

### `world-labels`

Oracle structured-label cleanup upper bound with robot-view report artifacts.

Expanded meaning:

```text
agent_input=world_labels
input_provenance=simulator_state
world_backend=molmospaces_sim
report=robot_view_report
verifier=cleanup_success + robot_view_honesty + real_robot_alignment
```

This is the current "MolmoSpaces cleanup with visual result" behavior. The
agent receives handles such as `observed_001`, object categories, support
estimates, public candidate fixture hints, cleanup recommendation flags, and
placement-tool hints. Initial detections are semantic candidates; before
`navigate_to_object` or `pick`, the agent must run an FPV scan/observe step that
binds the same handle to a reviewable source-frame bbox and promotes the
candidate to navigation-authorized. The FPV/chase/map/verification images are
report artifacts, not model input. Treat this lane as an oracle upper bound for
structured semantic cleanup, not the default fairness baseline against camera
lanes.

Future real hardware can still use this profile if the labels come from a robot
semantic map or object memory. The public profile should not change just because
the provenance changes.

### `world-labels-sanitized`

Perfect-detector structured-label ablation with robot-view report artifacts.

Expanded meaning:

```text
agent_input=sanitized_world_labels
input_provenance=simulator_state
world_backend=molmospaces_sim
report=robot_view_report
verifier=cleanup_success + robot_view_honesty + real_robot_alignment
detection_exposure_policy=sanitized_visible_object_detections
```

The agent receives run-local observed handles such as `observed_001`, object
categories, source observation ids, confidence, room/waypoint context, producer
provenance, and approximate public support evidence. Initial detections are
semantic candidates with verbal scan guidance, not navigation-authorizing
synthetic bboxes. It does not receive `candidate_fixture_id`,
`cleanup_recommended`, or `recommended_tool` in agent-facing detections.
Runtime-map observed-object rows still report producer type, source observation,
image region, grounding status,
and actionability, but destination selection is marked policy-required instead
of cleanup-ready.

Use this as the preferred structured-detector ablation when comparing against
`camera-labels` and `camera-raw`. It keeps perfect simulator detection/tracking
while removing direct cleanup destination answers.

### `camera-raw`

Raw camera-input cleanup.

Expanded meaning:

```text
agent_input=raw_camera
input_provenance=camera_artifact
world_backend=molmospaces_sim
report=robot_view_report
verifier=image_input_contract + cleanup_success + robot_view_honesty
```

This is the profile to use when the test is meant to prove that the model path
does not depend on prebuilt object labels. The contract should provide camera
artifacts and withhold object handles, categories, support estimates, and
candidate fixtures.

This profile is the one that can exercise real image reasoning when paired with
a model that supports image input and a launcher that passes images correctly.

Implemented refinement: `camera-raw` lets the main cleanup agent create
Model-Declared Observations from FPV image evidence. The agent still receives no
structured labels before declaration, but it may call a narrow declaration or
inline navigation tool when it is ready to act on a visual candidate.

Current live-agent status, 2026-06-06: treat pure `camera-raw` as a baseline,
debug, or ablation lane, not the recommended real-robot production path. After
the strict FPV visual-evidence gate, navigation and pick actions require a
source-observation-local FPV bbox and `navigation_authorized` candidate state.
With that gate enforced, the live Codex `camera-raw` run for
`seed=7 generated_mess_count=5` completed the full 14/14 public waypoint sweep
and produced two grounded cleanup chains, but it did not reliably find enough
same-source reviewable candidates to reach the five-object cleanup threshold.
Focused prompt/skill tuning improved behavior but reached a PARTIAL stop.

The real-robot direction is therefore assisted RAW-FPV / `camera-labels`: a
robot-deployable visual-grounding producer such as Grounding DINO, YOLO-family
open-vocabulary detection, SAM-style segmentation, or another perception
sidecar proposes bbox/mask evidence from the robot camera stream, while the
LLM/coding agent chooses among candidates, plans recovery, and calls the normal
navigation/manipulation tools. This is still a camera-evidence path, not a
simulator-label path, as long as candidate provenance records the source frame,
image region, confidence, and grounding status.

Older raw-FPV success or near-success rows must not be compared as equivalent
production evidence unless they pass the current gate. Before the 2026-06-06
strict gate, some action chains could be authorized by synthetic report-like
bboxes or by source-fixture, room, or broad-category fallback matching. Those
paths made reports look cleaner than the actual source-FPV evidence warranted.
The current stricter result is less flattering, but it is the honest real-robot
boundary.

The first live-agent gate for this profile should use semantic acceptability
rather than only exact hidden restoration. Exact private restoration remains
visible in the report, but preferred/acceptable advisory placements are the
better first-pass signal for raw-FPV cleanup because image-derived tidy choices
can legitimately differ from a generated exact fixture.

### `camera-labels`

Camera-derived structured labels.

Expanded meaning:

```text
agent_input=camera_labels
input_provenance=simulated_camera_model
world_backend=molmospaces_sim
report=robot_view_report
verifier=image_input_contract + cleanup_success + robot_view_honesty
```

The agent receives structured object candidates, but those candidates are
registered from a camera-observation step rather than directly from the world
model.

Current implementation note: the internal `camera_model_policy` path uses
deterministic simulated camera-label producer evidence. It does not call a real
VLM or detector. The Model-Declared Observation bridge keeps the public
`camera-labels` profile on the same declaration schema used by `camera-raw`; a
future implementation can change `input_provenance` to `vlm_detector` or
`object_detector`.

The profile should remain stable when that happens. Model choice belongs to
pipeline provenance, not to the profile name. Planned pipeline values include
`sim`, `fake-http`, proposer-only routes such as `grounding-dino` and `yoloe`,
proposer-plus-refiner routes such as `grounding-dino+mimo-v2.5`, and optional
direct VLM routes such as `qwen3-vl-direct`. They should all feed the same
`declare_visual_candidates` contract and produce the same normalized candidate
shape.

Grounding DINO and YOLOE should be treated as competing visual-region proposers.
MiMo v2.5 and Qwen3-VL should first be treated as refiners over those
proposals, with direct-producer modes kept as comparison experiments. A
perception-isolated benchmark over fixed RAW_FPV observations should select
which pipelines deserve full end-to-end cleanup probes.

## Model-Declared Observation Bridge

The durable bridge between camera evidence and cleanup handles is a
Model-Declared Observation: a public `observed_*` handle created from a camera
inference producer's interpretation of a public FPV observation.

This keeps the MCP boundary narrow. The contract does not expose a whole
`cleanup_room()` task tool, and it does not leak private scoring truth. It only
lets the agent or another producer turn camera evidence into an auditable public
handle, after which the normal semantic cleanup loop still applies:

```text
observe raw FPV
  -> navigate_to_visual_candidate
  -> pick
  -> navigate_to_receptacle
  -> open? -> place/place_inside -> close?
```

`camera-raw` uses one live-agent strategy: `inline_on_navigate`. The cleanup
agent declares a candidate only when trying to act on it, through
`navigate_to_visual_candidate`. Do not add a separate pre-registration knob to
normal raw-FPV runs unless future harness evidence shows a clear win.

In minimal-map runs, the cleanup agent must omit `target_fixture_id` when
calling `navigate_to_visual_candidate`; authored fixture hints are intentionally
hidden. The tool resolves public grounding and returns `candidate_fixture_id`
and `recommended_tool` for the follow-up pick/place chain. In explicit rich
legacy/debug runs only, a target fixture may come from non-empty
`fixture_hints`.

Explicit registration still belongs to producer-style perception flows:
`camera-labels` uses `declare_visual_candidates` after an observation, then the
cleanup policy chooses among the resulting `observed_*` handles.

Hidden grounding may use execution geometry or camera calibration to bind a
declaration to an executable object, but model-facing feedback must stay public:
resolved/ambiguous/unresolved status, confidence, basis, and recovery hint. An
unresolved declaration can be shown in reports but must not be pickable.

## Metadata Kept Behind Profiles

Profiles expand into implementation metadata. This metadata should appear in
reports and checker output, but most users should not type it.

### Agent Input

| Metadata value | Meaning |
| --- | --- |
| `world_labels` | Structured object handles and labels from a world model. |
| `raw_camera` | Raw camera/FPV artifacts with no structured labels. |
| `camera_labels` | Structured object candidates derived from camera perception. |

### Input Provenance

| Metadata value | Meaning |
| --- | --- |
| `synthetic_contract` | Cheap contract-shaped test data. |
| `simulator_state` | Labels derived from simulator object locations/state. |
| `robot_semantic_map` | Labels from a real robot semantic map or object memory. |
| `camera_artifact` | Raw camera artifact supplied without labels. |
| `simulated_camera_model` | Camera-label candidates generated from public simulator state. |
| `vlm_detector` | Camera-label candidates generated by a real multimodal model. |
| `object_detector` | Camera-label candidates generated by a conventional detector. |
| `human_annotation` | Labels supplied by a human or offline annotation process. |

### Report

| Metadata value | Meaning |
| --- | --- |
| `semantic_report` | Shared cleanup report without robot-view timeline. |
| `robot_view_report` | Adds RBY1M FPV/chase/map/verification timeline. |

### Verifier

| Metadata value | Meaning |
| --- | --- |
| `contract_only` | Contract shape exists and artifacts are present. |
| `cleanup_success` | Restoration, coverage, disturbance, and cleanup status gates. |
| `robot_view_honesty` | Robot-view timeline and waypoint/post-place roles are honest. |
| `image_input_contract` | Raw camera or camera-label path is actually used as expected. |
| `real_robot_alignment` | Reports keep semantic simulation separate from real robot readiness. |

## Legacy Name Replacement

No compatibility layer is required. Replace old public names directly.

| Old public/internal name | New public profile or metadata |
| --- | --- |
| `visual` | `profile=world-labels` when used as the default visual cleanup result. |
| `semantic` | `profile=smoke` for cheap contract checks, or `report=semantic_report` in metadata. |
| `raw-fpv` | `profile=camera-raw`. |
| `visible_object_detections` | `agent_input=world_labels` metadata. |
| `raw_fpv_only` | `agent_input=raw_camera` metadata. |
| `camera_model_policy` | `profile=camera-labels`, with `input_provenance=simulated_camera_model` today. |
| `synthetic` | `world_backend=synthetic_contract` metadata. |
| `molmospaces` | `world_backend=molmospaces_sim` metadata. |

## Missing Default Tests

The refactor should make these gaps visible and testable:

| Test target | Purpose |
| --- | --- |
| `profile=smoke` | Cheap contract sanity still works. |
| `profile=world-labels` | Current structured-label cleanup input lane still produces robot-view artifacts, but structured labels are semantic candidates until source-FPV confirmation authorizes navigation. |
| `profile=world-labels-sanitized` | Structured detections keep producer/source/actionability fields while omitting destination/tool oracle hints and pre-confirmed navigation authorization. |
| `profile=camera-raw` | Raw camera artifacts are actually used, structured labels are withheld before declaration, and model-declared handles can drive cleanup. |
| `profile=camera-labels` | Camera-derived label path is separate from world-label path, records producer provenance, and uses the same declaration schema as raw camera cleanup. |

The most important regression test is:

```text
profile=world-labels must not be described as image reasoning, online mapping,
or offline prior-map cleanup. Cleanup starts from the Base Navigation Map by
default; runtime_map_prior may add prior Runtime Metric Map or Actionable
Semantic Map Snapshot evidence.
```

The fair-comparison regression test is:

```text
profile=world-labels-sanitized must not expose candidate_fixture_id,
cleanup_recommended, or recommended_tool in visible_object_detections.
It must not expose cleanup_recommended=false as a skip signal in sanitized
agent-facing object rows.
Runtime observed_objects should still expose producer_type,
source_observation_id, image_region, grounding_status, and actionability.
```

The second most important regression test is:

```text
profile=camera-raw must fail if structured object labels leak into agent input.
```

## Implementation Result

Historical implementation result, superseded by
`docs/plans/operator-console-orthogonal-launch-refactor.md`:

1. `just task::run household-cleanup <driver> <profile>` treats the third
   positional argument as the cleanup profile.
2. The public profiles are `smoke`, `world-labels`,
   `world-labels-sanitized`, `camera-raw`, and `camera-labels`.
3. Old public profile values (`visual`, `semantic`, `raw-fpv`) are not accepted
   as cleanup profiles.
4. Profile expansion lives in `roboclaws/household/profiles.py`, while
   existing perception constants such as `visible_object_detections`,
   `raw_fpv_only`, and `camera_model_policy` remain internal metadata.
5. Generated cleanup artifacts can record `cleanup_profile` and
   `cleanup_profile_metadata`; the HTML report surfaces profile, agent input,
   provenance, report type, and verifier metadata.
6. Command help, `docs/human/molmospaces-settings.md`, and `just/README.md`
   use profile names.
7. Focused tests cover profile expansion, report metadata, command routing,
   raw-camera label leakage, and camera-label provenance.

## Decisions Made

- `direct` was left unchanged as a driver name. It remains clear enough for this
  refactor.
- `camera-labels` is exposed through the direct cleanup demo, deterministic MCP
  smoke path, and live cleanup MCP server CLI. It still records
  `input_provenance=simulated_camera_model` until a real detector/VLM path is
  implemented.
- `profile=world-labels` keeps the current direct-driver multi-seed review
  behavior (`1 2 3`) and live-driver single-seed behavior.
- `profile=world-labels-sanitized` keeps the `world-labels` backend,
  robot-view, and minimal-map behavior, but strips destination/tool oracle hints
  from the agent-facing detection and runtime-map boundary.

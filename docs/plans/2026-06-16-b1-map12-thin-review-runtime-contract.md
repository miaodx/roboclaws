---
plan_scope: b1-map12-thin-review-runtime-contract
status: Draft
created: 2026-06-16
last_reviewed: 2026-06-16
implementation_allowed: false
source:
  - user request to remove the thick B1 / Map 12 merged intermediate bundle
  - user concern that raw Map12 and Gaussian/scene inputs are likely acceptable while the merge artifact is not
  - user decision that human review should produce a usable digital-twin result without making the merge artifact a new source of truth
  - user decision on 2026-06-17 that no backward compatibility is required for this slice
related_context:
  - ARCHITECTURE.md
  - STATUS.md
  - docs/plans/2026-06-15-cross-environment-semantic-map-parity.md
  - docs/plans/2026-06-16-b1-map12-verified-map-scene-alignment.md
  - assets/maps/agibot-robot-map-12/
  - assets/maps/b1-map12-room-semantics/
  - data/robot-data-lab/scene-engine/data/2rd_floor_seperated/
  - roboclaws/maps/room_semantics.py
  - scripts/maps/render_b1_map12_label_tool.py
  - roboclaws/launch/worlds.py
---

# B1 / Map 12 Thin Review Contract And Runtime Bundle

## Status

Draft plan. Implementation is not approved yet.

This plan supersedes using `assets/maps/b1-map12-room-semantics` as a maintained
source of truth for B1 / Map 12 room labels. The replacement direction is:

```text
raw Map12 bundle
  + raw scene/Gaussian asset partitions
  + human review manifest
  -> generated digital-twin runtime bundle
```

The generated runtime bundle may be used by B1 digital-twin runs, reports, and
operator previews, but it must be rebuildable and must not become the human-edited
source.

There is no backward-compatibility requirement for the old B1 / Map 12 merged
bundle path. Current product routes, scripts, docs, and tests should move to the
thin review contract directly instead of preserving compatibility shims.

## Problem

The current B1 / Map 12 intermediate bundle is too thick. It copies the Map12
Nav2 bundle, applies scene room labels into `semantics.json`, retargets
inspection waypoints, and rebuilds driveable ways.

That makes a candidate correspondence look like a coherent semantic map. The
failure mode is visible today: `reception_area_a`, `short_corridor_a`, and
`storage_room_a` all inherit the same `south_fixture_area` polygon because the
overlay correspondence maps three scene partitions to one Map12 navigation area.
The raw inputs may be fine, but the merged artifact hides the uncertainty.

## Goals

1. Remove the thick merged bundle from the source-of-truth path.
2. Keep raw inputs separate and inspectable:
   - Map source: `assets/maps/agibot-robot-map-12/`
   - Scene source: `data/robot-data-lab/scene-engine/data/2rd_floor_seperated/`
3. Make the human review manifest the only maintained manual source.
4. Generate the digital-twin runtime bundle deterministically from raw inputs
   plus the review manifest.
5. Fail loudly when the review manifest would recreate the current false
   confidence, such as duplicate scene partitions silently sharing one polygon.

## Non-Goals

- Do not change public `household-world` command grammar.
- Do not change MCP capability contracts.
- Do not claim object-level USD truth, receptacle bindings, pick/place support,
  or manipulation readiness.
- Do not solve global map-scene transform verification in this plan. That remains
  owned by the verified map-scene alignment plan.
- Do not preserve `b1-map12-room-semantics` as a launch input, fixture contract,
  or compatibility path.

## Architecture Layers

This plan touches:

- Worlds / Scenes: `world=b1-map12` digital-twin defaults.
- Backend Runtime / Environment Primitive: the B1 Isaac runtime input map bundle
  prepared before a run.
- Artifacts, reports, and eval suites: review manifests, generated runtime
  bundles, previews, validation gates, and provenance.

This plan must not move cleanup/search strategy into server adapters or MCP
tools. Runtime preparation is artifact plumbing.

## Proposed Contract

### Source Assets

Raw map source remains:

```text
assets/maps/agibot-robot-map-12/
```

Raw scene source remains:

```text
data/robot-data-lab/scene-engine/data/2rd_floor_seperated/
```

The B1 digital-twin launch route should no longer default to:

```text
map_bundle=b1-map12-room-semantics
```

It should instead name the raw map and review contract:

```text
map_bundle=agibot-robot-map-12
b1_alignment_review=assets/maps/b1-map12-alignment-review.json
isaac_scene_usd_path=data/robot-data-lab/scene-engine/data/2rd_floor_seperated/storey_1/configuration/scene_base.usd
```

The backend or launch-prep layer may compile a runtime bundle into the run
directory or `output/`, then pass that generated bundle to existing lower-level
map consumers.

### Human Review Manifest

Add a first-class reviewed manifest:

```json
{
  "schema": "b1_map12_alignment_review_v1",
  "source_assets": {
    "map_bundle": "assets/maps/agibot-robot-map-12",
    "scene_root": "data/robot-data-lab/scene-engine/data/2rd_floor_seperated",
    "scene_usd_path": "data/robot-data-lab/scene-engine/data/2rd_floor_seperated/storey_1/configuration/scene_base.usd"
  },
  "display_adjustment": {
    "global_tilt_deg": 0.0,
    "status": "review_display_only"
  },
  "labels": [
    {
      "label_id": "meeting_room_a",
      "scene_partition_id": "meeting_room_a",
      "room_label": "Meeting room A",
      "category": "meeting_room",
      "map_area_id": "west_corridor",
      "geometry": {
        "type": "map_polygon",
        "source": "manual_review",
        "frame_id": "map",
        "points": [
          {"x": -8.7, "y": 0.5},
          {"x": -5.5, "y": 0.5},
          {"x": -5.5, "y": 4.8},
          {"x": -8.7, "y": 4.8}
        ]
      },
      "review_status": "accepted",
      "operator_note": ""
    }
  ]
}
```

Rules:

- `accepted` labels may enter the generated runtime bundle.
- `draft` and `proposed` labels stay review-only unless an explicit debug flag
  is used.
- A label without map-frame geometry is not a runtime navigation label.
- Multiple labels may share a `map_area_id` only when they explicitly declare
  `shared_area_policy: "composite_area"` or similar. The compiler must not
  silently inherit one polygon for several scene partitions.
- Display tilt is a review/display transform. Exported geometry is stored in the
  Map12 source map frame.

First-slice location:

```text
assets/maps/b1-map12-alignment-review.json
```

Draft downloads and autosaves may live under `output/`, but accepted review
state used by product routes should be a normal repo asset so digital-twin runs
are reproducible.

### Label Tool

The label tool should load:

```text
raw Map12 bundle + scene root + optional existing review manifest
```

It should not load `assets/maps/b1-map12-room-semantics/semantics.json` as the
default source.

Its packet should show three separate layers:

1. Map12 navigation areas, waypoints, fixtures, and free-space image.
2. Scene/Gaussian partition names and evidence.
3. Human review labels and geometry.

Saving from the tool writes or downloads a `b1_map12_alignment_review_v1`
manifest. It does not mutate either raw source.

### Runtime Compiler

Add a deterministic compiler command, for example:

```bash
python scripts/maps/compile_b1_map12_runtime_bundle.py \
  --map-bundle assets/maps/agibot-robot-map-12 \
  --scene-root data/robot-data-lab/scene-engine/data/2rd_floor_seperated \
  --review-manifest assets/maps/b1-map12-alignment-review.json \
  --output-dir output/b1-map12/digital-twin-runtime
```

The compiler may copy `map.yaml`, `map.pgm`, costmaps, and profiles from the raw
Map12 bundle. It may write a runtime `semantics.json`, `preview.png`, and
provenance file. It must include:

- source raw map path and checksum or mtime marker;
- source scene root path;
- review manifest path and schema;
- compile timestamp;
- draft-label policy;
- duplicate/shared-area validation result;
- generated-artifact marker such as `generated_from_review_manifest: true`.

The compiler output is a product/runtime artifact. It is never manually edited.

### Digital-Twin Runtime Consumption

First implementation should compile into the product run directory. A separate
`output/b1-map12/digital-twin-runtime` path is fine for manual tool exports and
tests, but product launches should not share a mutable global generated bundle
between runs. A checked-in generated runtime snapshot is not part of the first
slice. If later startup or packaging needs a committed snapshot, create a
separate decision that names it as generated and adds a stale-output gate.

Existing lower-level consumers that require a map bundle should receive the
generated runtime bundle path. They should not keep a fallback to the old merged
bundle.

## Replacement Plan

1. Add the review manifest schema and validator.
2. Change the label tool default input from `b1-map12-room-semantics` to raw
   Map12 bundle plus scene root.
3. Add runtime compiler and validation tests.
4. Update `world=b1-map12` defaults to name raw map plus review manifest, not
   `b1-map12-room-semantics`.
5. Update operator-console preview generation so it can render from raw inputs
   plus a compiled runtime artifact.
6. Remove `apply_room_semantic_overlay_to_bundle` and the `--apply-to-bundle`
   skill path from current code/docs/tests unless another non-B1 consumer is
   discovered during implementation. If a non-B1 consumer exists, split it out
   under a different, explicitly current contract instead of preserving the B1
   compatibility behavior.
7. Remove default-route and report assumptions that `room_semantic_overlay.json`
   is present in the consumed map bundle.
8. Delete `assets/maps/b1-map12-room-semantics` after replacement consumers and
   tests are updated. If a small historical fixture is still needed for a
   regression test, keep only the minimal fixture under `tests/fixtures/` with a
   name that cannot be selected by product routes.

## Acceptance Criteria

- `rg "b1-map12-room-semantics" roboclaws scripts just docs/human docs/plans`
  returns no current route, script, or human-facing guidance references other
  than this replacement plan and explicitly superseded plans.
- `rg "b1-map12-room-semantics" tests` returns no active test references. If
  regression coverage needs old data, it uses a minimal `tests/fixtures/`
  fixture with a non-product name.
- Label tool packet provenance lists raw Map12, raw scene root, and review
  manifest separately.
- Runtime compiler fails on duplicate `map_area_id` / shared polygon unless an
  explicit shared-area policy is present.
- Runtime compiler excludes draft labels by default.
- Generated runtime bundle validates as a Nav2-shaped map bundle when accepted
  labels are present.
- B1 launch route can prepare or locate a generated runtime bundle before Isaac
  consumes map context.
- Existing tests no longer assert or imply that
  `assets/maps/b1-map12-room-semantics` is the canonical B1 semantic source.

## Verification

Recommended focused gates:

```bash
ruff check scripts/maps/render_b1_map12_label_tool.py scripts/maps/compile_b1_map12_runtime_bundle.py tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_b1_map12_runtime_bundle.py
./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_b1_map12_label_tool.py tests/contract/maps/test_b1_map12_runtime_bundle.py tests/unit/launch/test_environment_setup_catalog.py tests/unit/operator_console/test_routes.py -q
just agent::eval recommend plan=docs/plans/2026-06-16-b1-map12-thin-review-runtime-contract.md budget=focused
```

If the eval harness recommends a live Isaac or provider-backed route, record it
as local-validation follow-up unless the current session has the needed runtime.

## Reduce-Entropy Audit

### Round 1: Source-Of-Truth Collapse

Candidate 1: Remove thick merged bundle from the default source path.

Severity: P0

Entropy source: false confidence

Demand gate: pass. Keeping the bundle as source lets a candidate
scene-to-map merge look like a valid semantic map, which already produced shared
room polygons.

Materiality: future users and agents will trust `semantics.json` because it
looks like a normal map bundle.

Affected paths:

- `assets/maps/b1-map12-room-semantics/`
- `roboclaws/launch/worlds.py`
- `scripts/maps/render_b1_map12_label_tool.py`
- `scripts/operator_console/render_scene_previews.py`
- `tests/contract/maps/test_scene_room_semantic_overlay.py`

Proof: search for `b1-map12-room-semantics` default-route references and remove
or demote them.

Risk: medium. Digital-twin consumers still need a bundle-shaped runtime input,
so runtime compilation must land in the same replacement slice.

### Round 2: Runtime Compatibility Without A New Source

Candidate 2: Compile runtime bundles at launch prep or explicit export time.

Severity: P1

Entropy source: workflow friction

Demand gate: pass. Digital-twin runs need a concrete map bundle, but making a
maintained generated bundle the source recreates the current problem.

Materiality: without this compiler, deleting the intermediate breaks B1
digital-twin usage; with a checked-in generated runtime as source, the source of
truth remains ambiguous.

Proof: B1 launch tests should show raw map + review manifest inputs and a
generated map bundle path passed to lower-level map consumers.

Risk: medium. The compiler must fit current map-bundle validators without
reintroducing hidden merge behavior.

### Round 3: Validation And Stale Surface

Candidate 3: Add manifest invariants before replacement.

Severity: P1

Entropy source: acceptance gap

Demand gate: pass. The current bug is not a rendering bug; it is a missing
invariant that allowed several scene labels to share one area silently.

Required invariants:

- no duplicate `label_id`;
- no duplicate accepted geometry unless explicitly shared;
- no accepted label without map-frame geometry;
- draft/proposed labels excluded from runtime by default;
- display tilt cannot modify saved source-frame coordinates unless explicitly
  inverted during export.

Proof: focused manifest validator tests and compiler failure tests.

Risk: low to medium. Some legitimate shared spaces may need an explicit
`composite_area` status instead of silent success.

Candidate 4: Remove the old overlay application path from current docs/tests.

Severity: P1

Entropy source: stale surface

Demand gate: pass. The skill currently advertises generating
`scene_room_semantic_overlay_v1` and applying it to a Nav2 bundle, which is the
behavior this plan is removing from the default workflow.

Proof: skill docs should point to the thin review manifest workflow, and
`--apply-to-bundle` tests should be removed unless a separate current non-B1
contract is discovered.

Risk: medium. Existing tests around cross-environment semantic parity mention
the old bundle and need replacement assertions.

### Saturation Result

No additional P0/P1 direction is needed inside this plan after the four
candidates above. The remaining issues are parked because they belong to adjacent
plans:

- residual-backed global map-scene transform verification;
- object-level USD prim binding;
- manipulation/receptacle semantics;
- committing a generated runtime snapshot for packaging;
- UI polish for the label tool.

Saturation audit note: the main implementation ambiguity left after this loop is
mechanical execution scope, not product direction. It should be handled by
preflight, not by another discovery loop.

## Recommended Next Action

Run a preflight on this plan before implementation. The preflight should lock:

- whether the first slice creates the accepted review manifest from the current
  draft or starts with an empty reviewed asset;
- exact run-directory path and artifact naming for compiled runtime bundles;
- how B1 launch prep passes the generated bundle to current consumers;
- which old tests are deleted versus rewritten around the new contract.

Shortcut: `preflight thin runtime`.

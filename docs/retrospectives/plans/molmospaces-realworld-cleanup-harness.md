# MolmoSpaces Real-World-Style Cleanup Harness

**Status:** Implemented 2026-05-09 under GSD Phase 14
**Created:** 2026-05-08
**Source:** `grill-with-docs` discussion, `CONTEXT.md`, ADR-0003
**Workflow result:** Source planning doc accepted for execution via the
`hybrid-phase-pipeline` route, then implemented under
`.planning/milestones/v1.98-phases/14-molmospaces-realworld-cleanup-harness/`.

## Implementation Result

Implemented under GSD Phase 14:
`.planning/milestones/v1.98-phases/14-molmospaces-realworld-cleanup-harness/`.

Shipped ADR-0003 harness artifacts:

- `roboclaws/molmo_cleanup/realworld_contract.py`
- `roboclaws/molmo_cleanup/semantic_timeline.py`
- `examples/molmospaces_realworld_cleanup.py`
- `scripts/check_molmo_realworld_cleanup_result.py`
- `just harness::molmo-realworld-cleanup`
- `just verify::molmo-realworld-cleanup`

Local evidence from 2026-05-09:

| Gate | Artifact | Result |
| --- | --- | --- |
| Focused synthetic tests | `tests/test_molmo_realworld_contract.py`, `tests/test_molmospaces_realworld_cleanup.py`, `tests/test_check_molmo_realworld_cleanup_result.py` | 20 focused Molmo tests passed with related report/current-contract regressions. |
| Real MolmoSpaces three-seed harness | `output/molmo-realworld-cleanup-harness/seed-{1,2,3}/run_result.json` | Checker passed all 3 runs with `contract=realworld_cleanup_v1`, `policy_uses_private_truth=false`, `fixture_hint_mode=room_only`, `mess_restoration_rate=0.8`, `sweep_coverage_rate=1.0`, and `disturbance_count=0`. |
| Visual report parity | `output/molmo-realworld-cleanup-harness/seed-1/report.html` | Seed 1 now includes the shared `Robot View Timeline` visual report surface: 23 robot timeline steps and 92 FPV/chase/map/verification PNGs. Object rows use the same semantic shape as the bridge report: `navigate_to_object -> pick -> navigate_to_receptacle -> open_receptacle? -> place/place_inside`, while preserving the separated `Agent View` and `Private Evaluation` sections. |

This first implementation slice keeps `generated_mess_count=5`, inherited from
the existing fixed MolmoSpaces target selector, rather than expanding to 10-20
objects. The ADR-0003 boundary is nevertheless implemented: the Agent View no
longer receives the Generated Mess Set, hidden target count, acceptable
destination sets, `is_misplaced` labels, or a global movable-object inventory.
The private scorer data appears only in post-run `private_evaluation` artifacts
and the report's Private Evaluation section.

Follow-up update, 2026-05-09: Phase 15 implemented ADR-0005 and expanded the
real ADR-0003 harness recipe to request 10 hidden generated objects by default.
See
[`docs/retrospectives/plans/molmospaces-generated-mess-set-scale.md`](molmospaces-generated-mess-set-scale.md)
and
`.planning/milestones/v1.98-phases/15-molmospaces-generated-mess-set-scale/15-VERIFICATION.md`.

Architecture note: current-contract bridge artifacts and ADR-0003 harness
artifacts intentionally keep separate public contracts, but share the same
semantic timeline/report underlay in `roboclaws/molmo_cleanup/semantic_timeline.py`.
That keeps the bridge's `object_done` readback extension separate from
ADR-0003's observed-handle contract without maintaining two report-phase
implementations.

## Problem

The current MolmoSpaces cleanup harness proves real MolmoSpaces/MuJoCo scene
loading, RBY1M visual reporting, semantic substeps, and public-heuristic
cleanup. It is still easier than a real cleanup scenario:

- the backend selects a curated target set during setup;
- the public scenario lists selected cleanup targets first;
- the policy builds a full object-to-receptacle cleanup plan up front;
- scoring is framed around a small fixed target set.

This means `planner_uses_private_manifest=false` is true but incomplete as a
realism claim. The Cleanup Agent still benefits from a target-shaped public
payload rather than discovering misplaced objects through a room sweep.

## Goal

Build the **MolmoSpaces Real-World-Style Cleanup Harness**: a cleanup harness
where a Mess Generator creates a larger hidden mess, the Cleanup Agent receives
only public map/perception inputs, and the Scorer evaluates tidy-plausible final
state after the run.

The task remains:

```text
帮我收拾这个房间
```

The first version should prove the public/private contract with a deterministic
sweep baseline before evaluating coding-agent or OpenClaw policies.

## Decisions Locked

- The Cleanup Agent must not receive the Generated Mess Set, target count,
  acceptable destination sets, or `is_misplaced` labels.
- Public inputs may include a Metric Map, room-level fixture hints, Public
  Fixture IDs, Fixture Affordances, robot-local Visible Object Detections, and
  Support Estimates.
- Small movable object IDs become available only as Observed Object Handles
  after local perception sees the object.
- V1 may use Visible Object Detections; raw FPV-only inference is deferred.
- V1 may use Map-Guided Semantic Navigation and `api_semantic` manipulation;
  planner-backed navigation/manipulation remain separate follow-ups.
- Deterministic scoring is authoritative for v1; LLM scoring may be advisory
  only.
- Reports may show Private Evaluation after the run, but must separate it from
  the Agent View.

See ADR-0003:
[`docs/adr/0003-separate-cleanup-agent-view-from-private-evaluation.md`](../adr/0003-separate-cleanup-agent-view-from-private-evaluation.md).

## Public Contract

### `metric_map`

Returns public navigation structure:

- rooms and room labels;
- walls, doors, and driveable ways;
- robot pose;
- 2-4 public Inspection Waypoints per room;
- optional coarse waypoint coverage estimates.

It must not include hidden object coverage or movable-object locations.

### `fixture_hints`

Returns room-level fixture knowledge:

```json
{
  "fixture_hint_mode": "room_only",
  "rooms": [
    {
      "room_id": "kitchen_1",
      "room_label": "kitchen",
      "fixtures": [
        {
          "fixture_id": "fridge_1",
          "category": "Fridge",
          "name": "fridge",
          "affordances": ["open", "place_inside"],
          "position_detail": "room_only"
        }
      ]
    }
  ]
}
```

Default mode is `room_only`. An easier operator-selected fallback mode,
`exact_fixtures`, may expose exact fixture poses and must be recorded in
`run_result.json`.

### `observe`

Returns robot-local perception at the current pose:

- FPV/chase/map images where available;
- current room and pose;
- Visible Object Detections for objects visible from the current viewpoint.

Detection shape:

```json
{
  "object_id": "observed_12",
  "category": "Pillow",
  "name": "pillow",
  "current_room_id": "bedroom_1",
  "visibility_confidence": 0.82,
  "image_bbox": [120, 90, 42, 31],
  "support_estimate": {
    "fixture_id": "desk_2",
    "relation": "on",
    "confidence": 0.74,
    "source": "visible_detection"
  }
}
```

Detections must not include target receptacles, acceptable destinations, or
`is_misplaced`.

### Movement And Manipulation

V1 may expose semantic tools:

- `navigate_to_room(room_id)`
- `navigate_to_waypoint(waypoint_id)`
- `inspect_visible_object(object_id)`
- `pick(object_id)`
- `open_receptacle(fixture_id)`
- `place(fixture_id)`
- `place_inside(fixture_id)`
- `done(reason)`

All action responses must preserve provenance labels. V1 is expected to remain
`api_semantic` unless a later planner-backed robot path is proven.

The current global movable-object `scene_objects` shape should be retired or
restricted. If kept for compatibility, it must not expose a global inventory to
the Cleanup Agent in this harness.

## Mess Generator

The Mess Generator runs before the Cleanup Agent starts.

V1 setup:

- use the existing real MolmoSpaces subprocess backend;
- start with `procthor-10k-val` scene index `0`;
- run multiple mess seeds, initially `1,2,3`;
- create a hidden Generated Mess Set of roughly 10-20 movable objects;
- move objects to plausible-but-wrong rooms/surfaces;
- keep non-generated tidy objects in plausible places where possible;
- write private setup truth for the Scorer only.

The Cleanup Agent must not receive:

- the Generated Mess Set;
- target count;
- acceptable destination sets;
- hidden target receptacle IDs;
- a public object-category-to-destination table.

## Scorer

The Scorer judges Tidy-Plausible Outcomes using deterministic rules first.

Private Scoring Truth should support multiple acceptable destinations per
object class, for example:

- pillow -> bed or sofa;
- book -> bookshelf or desk;
- remote -> TV stand or plausible living-room surface;
- food -> fridge or plausible kitchen surface, depending category;
- dishware -> sink or plausible kitchen counter/sink area.

V1 score fields:

- `mess_restoration_rate`: fraction of Generated Mess Set ending in
  tidy-plausible locations;
- `sweep_coverage_rate`: fraction of public Inspection Waypoints observed;
- `disturbance_count`: initially tidy objects made less tidy-plausible;
- `completion_status`: `success`, `partial_success`, or `failed`;
- optional `efficiency`: actions per restored object.

Default success threshold:

- `mess_restoration_rate >= 0.70`;
- `sweep_coverage_rate >= 0.90`;
- `disturbance_count <= 2`;
- no critical tool/provenance failure.

An Advisory LLM Scorer may be added later to explain ambiguous placements and
surface disagreements, but deterministic scoring remains authoritative for v1.

## Deterministic Sweep Baseline

The first policy should be a Deterministic Sweep Baseline, not OpenClaw or a
coding-agent policy.

Rules:

- it must obey the same public contract as future model-driven agents;
- it may use common-sense category heuristics;
- it must not use the Generated Mess Set, Private Scoring Truth, or hidden
  target count;
- it should visit public Inspection Waypoints, accumulate an Agent-Built
  Semantic Map, handle visible cleanup candidates, then call `done`.

The baseline exists to prove the harness is fair, inspectable, and not dependent
on private leakage before model policy behavior is evaluated.

## Report Requirements

The report must separate:

- **Agent View**: public inputs, observations, visible detections, map, fixture
  hints, and actions available at run time;
- **Agent Memory**: objects discovered, decisions made, candidates skipped, and
  inferred destinations;
- **Private Evaluation**: Generated Mess Set, acceptable destination sets,
  restored/missed objects, disturbance penalty, and final score;
- **Artifacts**: before/after images, robot views, map images, trace, and
  `run_result.json`.

The report may reveal Private Evaluation only after the run, never as an agent
input.

## Acceptance Criteria

- `just harness::molmo-realworld-cleanup` runs on the fixed real MolmoSpaces
  scene for at least three mess seeds.
- `just verify::molmo-realworld-cleanup` passes focused tests and the harness
  gate.
- `run_result.json` records:
  - `backend=molmospaces_subprocess`;
  - `task_prompt="帮我收拾这个房间"`;
  - `fixture_hint_mode`;
  - `generated_mess_count`;
  - `planner` or `policy`;
  - `policy_uses_private_truth=false`;
  - `mess_restoration_rate`;
  - `sweep_coverage_rate`;
  - `disturbance_count`;
  - `primitive_provenance` summary.
- The Agent View contains no Generated Mess Set, hidden target count,
  acceptable destination sets, `is_misplaced`, or global movable-object
  inventory.
- The deterministic baseline satisfies the default v1 success threshold across
  the initial multi-seed gate.
- `report.html` clearly separates Agent View from Private Evaluation.

## Non-Goals

- No authoritative LLM scorer.
- No raw FPV-only object discovery.
- No OpenClaw/coding-agent policy evaluation in the first implementation slice.
- No planner-backed RBY1M/Franka manipulation claim.
- No planner-backed collision-free navigation claim.
- No multi-scene sweep until the single-scene multi-seed contract is stable.
- No exact fixture positions by default.

## Follow-Up Path

After the deterministic baseline and contract pass:

1. Run a coding-agent policy against the same public contract.
2. Run OpenClaw against the same public contract.
3. Add optional `exact_fixtures` comparison if room-level fixture hints are too
   weak.
4. Add Advisory LLM Scorer calibration on saved runs.
5. Add raw FPV-only object inference as a harder perception mode.
6. Expand to 3 scenes x 3 mess seeds.
7. Revisit planner-backed RBY1M/Franka navigation and manipulation.

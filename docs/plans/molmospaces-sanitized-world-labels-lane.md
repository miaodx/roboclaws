# MolmoSpaces Sanitized World Labels Lane

**Status:** Proposed source plan
**Created:** 2026-06-03
**Source:** Molmo cleanup comparison discussion after Codex world-labels,
RAW_FPV, and Grounding DINO reruns
**Workflow:** Pre-GSD plan. Ingest or pass to `gsd-plan-phase` before
implementation.

## Problem

The current `world-labels` lane is useful as a structured semantic upper bound,
but it is not a fair approximation of what a real robot camera stack can
produce. It gives the cleanup agent simulator-derived structured object handles
and labels, and the downstream observation/runtime-map payload can also expose
cleanup-oriented hints such as source support, destination fixture candidates,
cleanup recommendation, and recommended placement tool.

Recent Codex comparison evidence shows the difference clearly:

- `world-labels`: strong cleanup result from already structured simulator
  detections.
- `camera-labels` with Grounding DINO: raw FPV plus external visual-grounding
  producer, with fewer resolved/actionable handles.
- `camera-raw`: raw FPV only, where the cleanup agent declares candidates inline
  while acting and can easily produce unresolved hypotheses.

The comparison needs an intermediate lane that still uses simulator labels as a
perfect object detector, but removes destination and cleanup oracle information.
That lane should clarify how much of the `world-labels` advantage comes from
clean visual detection versus simulator-only cleanup shortcuts.

## Goals

- Add a public cleanup profile named `world-labels-sanitized`.
- Preserve the existing `world-labels` profile unchanged as an oracle structured
  semantic upper bound.
- Make `world-labels-sanitized` closer to a real structured camera perception
  stack: detected object/category/region/tracking are available, direct cleanup
  destination answers are not.
- Align the runtime-map shape across `world-labels`, `world-labels-sanitized`,
  `camera-labels`, and `camera-raw` so every lane reports producer provenance,
  grounding status, source observation, image region, and actionability.
- Produce an apples-to-apples comparison table that clearly distinguishes
  oracle, sanitized detector, camera producer, and raw FPV lanes.

## Non-Goals

- Do not degrade or remove the current `world-labels` lane.
- Do not simulate detector noise, missed detections, or false positives in the
  first sanitized lane.
- Do not change the raw FPV agent strategy in this slice.
- Do not ask external visual-grounding models to own final cleanup destination
  policy.

## Proposed Lane Model

The public cleanup lanes should be described as:

| Profile | Role | Agent input | Fairness note |
| --- | --- | --- | --- |
| `world-labels` | Oracle structured semantic upper bound | Simulator structured detections plus cleanup-ready hints | Not real-robot reachable as-is |
| `world-labels-sanitized` | Perfect detector ablation | Structured detections without destination/cleanup oracle fields | Closer to real robot structured perception |
| `camera-labels` | Camera producer lane | Raw FPV, then producer-registered visual candidates | Real detector/VLM approximation |
| `camera-raw` | Raw visual agent lane | Raw FPV only, agent declares candidates while acting | Closest to end-to-end FPV input |

`world-labels-sanitized` should keep the same backend, robot-view report, and
minimal-map behavior as `world-labels`. It should differ only in what the agent
can learn from structured detections and runtime-map observed objects.

## Sanitized Observation Policy

For `world-labels-sanitized`, agent-facing `visible_object_detections` should:

- keep `object_id` as a run-local observed handle;
- keep `category`, `image_region`, `confidence`, `source_observation_id`,
  `room_id`, and `waypoint_id`;
- keep producer provenance, using a distinct producer type such as
  `sanitized_visible_object_detections`;
- downgrade support context to approximate public evidence, not a private
  simulator cleanup shortcut;
- remove `candidate_fixture_id`, `cleanup_recommended`, and
  `recommended_tool`;
- avoid exposing any field that directly answers "where should this object be
  placed?"

Runtime-map `observed_objects` should still be written for sanitized detections,
but their `actionability` should reflect that the object is observed/resolved
while destination selection remains policy-required or unresolved. The source
map must remain unmutated, and priors must still require current confirmation.

## Implementation Notes

Add the new profile in `roboclaws.household.profiles` with:

- profile: `world-labels-sanitized`;
- perception mode: `visible_object_detections`;
- backend/report/robot-view flags matching `world-labels`;
- agent input: a new value such as `sanitized_world_labels`;
- metadata summary and model-input note explicitly calling it a no-destination
  oracle ablation.

Introduce a small sanitization path in the real-world cleanup contract rather
than overloading every visible-detection caller. The runner/server should pass
the selected cleanup profile into the contract or otherwise derive the
agent-facing detection exposure policy from run metadata. Existing
`world-labels` calls must continue to receive the current rich payload.

Update public command routing to accept the new profile in:

- `just task::run household-cleanup <driver> world-labels-sanitized`;
- direct, Codex, Claude, MCP-smoke, and report/checker paths that currently
  allow `smoke|world-labels|camera-raw|camera-labels`;
- live-agent prompts only as needed to describe the new lane as structured
  detections without destination oracle fields.

Docs should mark `world-labels` as oracle upper bound and
`world-labels-sanitized` as the preferred structured-detector ablation for fair
comparison against camera lanes.

## Test Plan

- Add profile metadata tests proving `world-labels-sanitized` validates and
  keeps the expected backend/perception/report settings.
- Add contract tests proving sanitized observations omit `candidate_fixture_id`,
  `cleanup_recommended`, and `recommended_tool` while retaining detection,
  provenance, image-region, and observation fields.
- Add runtime-map tests proving all four lanes expose comparable
  `producer_type`, `source_observation_id`, `image_region`, `grounding_status`,
  and `actionability` fields.
- Add command-routing/checker tests proving `just task::run household-cleanup
  direct world-labels-sanitized` and Codex/Claude profile allowlists accept the
  new lane.
- Run a seed-7 comparison after implementation:

```bash
just task::run household-cleanup codex world-labels seed=7 generated_mess_count=10
just task::run household-cleanup codex world-labels-sanitized seed=7 generated_mess_count=10
just task::run household-cleanup codex camera-labels seed=7 generated_mess_count=10 visual_grounding=grounding-dino
just task::run household-cleanup codex camera-raw seed=7 generated_mess_count=10
```

Record restored count, semantic accepted count, resolved observed-object count,
producer summary, and whether cleanup started before a full survey.

## Assumptions

- The first sanitized lane is an ablation, not a real detector simulation.
- The expected result should fall between `world-labels` and the camera lanes;
  if it remains close to `world-labels`, the advantage likely comes mostly from
  perfect object detection/tracking rather than destination hints.
- If the sanitized lane is still too strong, the next slice should add a
  detector-noise ablation instead of weakening `camera-labels` or `camera-raw`.
- The main comparison table should not use `world-labels` as the fairness
  baseline after this lane exists.

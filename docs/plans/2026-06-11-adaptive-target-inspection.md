# Adaptive Target Inspection

**Status:** Implemented with optional exploratory follow-ups
**Created:** 2026-06-11
**Last reviewed:** 2026-06-11
**Current implementation contract:** slices 1-5 are implemented for the
deterministic household-world/MolmoSpaces direct-runner path, including public
target-query recovery. The real Grounding-DINO direct-runner product gate, one
Codex RAW-FPV live-agent map-build gate, and one clean Codex Grounding-DINO
live-agent map-build gate have passed. A small Grounding-DINO + MiMo refiner
smoke benchmark has also passed. There are no remaining plan-scoped parked
gates for this implementation contract; broader detector/refiner ranking is a
future optional benchmark outside this plan's done criteria.
**Related ADRs:** none yet. Create an ADR only if implementation adds a durable
public MCP tool, changes `metric_map()` / Agent View payload guarantees, or
changes public profile guarantees.
**Supersedes / Superseded by:** none.

## Implementation Status

Implemented on 2026-06-11:

- Runtime Metric Map now exposes `target_candidates`,
  `target_search_summary`, per-observe `inspection_observations`, bounded
  `adjust_camera` events, and `generated_target_inspection_candidates`.
- Generated target-inspection candidates are projected as public waypoint
  entries and reuse `navigate_to_waypoint`; no new opaque navigation tool was
  added.
- Reports render Target Candidates and checker gates verify private-truth
  exclusion, waypoint honesty, non-actionable candidate restrictions, and
  missing-target budget evidence.
- Semantic-sweep map-build checkers accept scan-only camera-grounded/RAW-FPV
  evidence when public runtime-map target candidates and viewpoint budgets are
  present; cleanup still requires current observed handles for manipulation.
- `resolve_target_query` is exposed through the public household MCP surface
  and resolves stale labels, raw fixture ids, destination categories, and
  open-ended target text through public `runtime_metric_map.target_candidates`
  only. Not-found responses include public search-budget evidence.

Verified deterministic evidence:

- `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -q`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
- `uv run ruff check roboclaws/household/realworld_contract.py roboclaws/household/report.py scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
- `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-public-labels map_mode=minimal scenario_setup=baseline seed=7`
  - report:
    `output/household/semantic-map-build/direct-world-public-labels/0611_1218/seed-7/report.html`
- `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels map_mode=minimal scenario_setup=baseline seed=7`
  - report:
    `output/household/semantic-map-build/direct-camera-grounded-labels/0611_1227/seed-7/report.html`
- `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-raw-fpv map_mode=minimal scenario_setup=baseline seed=7`
  - report:
    `output/household/semantic-map-build/direct-camera-raw-fpv/0611_1235/seed-7/report.html`
- Cleanup consumer gate using the camera-grounded runtime-map prior:
  `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=world-public-labels map_mode=minimal scenario_setup=relocate-cleanup-related-objects relocation_count=5 seed=7 runtime_map_prior=output/household/semantic-map-build/direct-camera-grounded-labels/0611_1227/seed-7/runtime_metric_map.json`
  - report:
    `output/household/household-cleanup/direct-world-public-labels/0611_1230/seed-7/report.html`
- Target-query recovery helper gate:
  `.venv/bin/python skills/molmo-realworld-cleanup/scripts/target_query_recovery.py output/household/semantic-map-build/direct-camera-grounded-labels/0611_1309/seed-7/runtime_metric_map.json sink_01 --operation destination --max-results 1`
  - result: `status=matched`, best match is the public Sink anchor
    `anchor_fixture_010` at `generated_exploration_014`, with
    `required_next_tool=navigate_to_waypoint` and
    `private_truth_included=false`.
- Grounding-DINO direct-runner product gate:
  `VISUAL_GROUNDING_BASE_URL=http://127.0.0.1:18881 VISUAL_GROUNDING_TIMEOUT_S=120 just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino map_mode=minimal scenario_setup=baseline seed=7`
  - report:
    `output/household/semantic-map-build/direct-camera-grounded-labels/0611_1309/seed-7/report.html`
  - checker:
    `.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --expect-backend molmospaces_subprocess --expect-policy semantic_sweep_baseline --expect-profile camera-grounded-labels --min-generated-mess-count 0 --require-runtime-metric-map --require-semantic-sweep --require-minimal-map --require-camera-model-policy --expect-visual-grounding-pipeline grounding-dino --min-sweep-coverage 1.0 output/household/semantic-map-build/direct-camera-grounded-labels/0611_1309/seed-7/run_result.json`
  - result: 14/14 public waypoints visited, 42 camera-model policy events,
    193 detector candidates, 28 camera adjustments, sweep coverage 1.0, and
    no cleanup actions.
- Codex RAW-FPV live-agent exploratory gate:
  `output/household/semantic-map-build/codex-camera-raw-fpv/0611_1313/seed-7/report.html`
  - checker:
    `.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --expect-task-name semantic-map-build --expect-backend molmospaces_subprocess --expect-policy codex_agent --expect-profile camera-raw-fpv --expect-mcp-server molmo_cleanup_realworld --min-generated-mess-count 0 --require-agent-driven --require-runtime-metric-map --require-semantic-sweep --require-minimal-map --require-raw-fpv-observations --min-sweep-coverage 1.0 output/household/semantic-map-build/codex-camera-raw-fpv/0611_1313/seed-7/run_result.json`
  - result: `policy=codex_agent`, 14/14 public waypoints visited, 14 raw-FPV
    observations, 33 MCP tool calls, zero cleanup actions, sweep coverage 1.0.
    Runner wall time was 316.295s (about 5m16s), down from the earlier
    18m30s baseline for this live-agent map-build path.
- Grounding-DINO + MiMo refiner smoke benchmark:
  `output/visual-grounding-benchmark/0611_refiner_smoke/0611_1404/visual_grounding_benchmark_report.html`
  - command:
    `VISUAL_GROUNDING_BASE_URL=http://127.0.0.1:18882 VISUAL_GROUNDING_TIMEOUT_S=240 just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino+mimo-v2.5 corpus=harness/visual_grounding/smoke_corpus.json timeout_s=240 output_dir=output/visual-grounding-benchmark/0611_refiner_smoke`
  - result: 3/3 observations completed, zero failures/timeouts, 2 candidates,
    bbox precision 1.0, bbox recall 1.0, mean bbox IoU 0.851509, 3 rejected
    proposals, no private labels in requests, and `auth_mode=bearer_configured`.
    The DINO proposer ran on CUDA (`NVIDIA RTX 3500 Ada Generation Laptop GPU`,
    Torch `2.12.0+cu130`); the hosted MiMo refiner used 8,572 total reported
    tokens. Stage latency was about 3.9s average for the proposer and 31.6s
    average for the refiner, confirming the refiner route works but remains too
    slow for default low-latency cleanup gates.

Latest focused verification:

- `uv run ruff check scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`
- `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py::test_checker_accepts_live_raw_fpv_semantic_map_build_shape tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_smoke_writes_agent_artifacts -q`

Completed exploratory gates:

- Live-agent `camera-grounded-labels + camera_labeler=grounding-dino` has now
  been exercised with clean detector uptime:
  `output/household/semantic-map-build/codex-camera-grounded-labels/0611_1436/seed-7/report.html`.
  Checker passed with
  `.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py --expect-task-name semantic-map-build --expect-backend molmospaces_subprocess --expect-policy codex_agent --expect-profile camera-grounded-labels --expect-mcp-server molmo_cleanup_realworld --min-generated-mess-count 0 --require-agent-driven --require-runtime-metric-map --require-semantic-sweep --require-minimal-map --require-camera-model-policy --expect-visual-grounding-pipeline grounding-dino --min-sweep-coverage 1.0 output/household/semantic-map-build/codex-camera-grounded-labels/0611_1436/seed-7/run_result.json`.
  Result: `policy=codex_agent`, 14/14 public waypoints visited, 14 raw-FPV
  observations, 14 `declare_visual_candidates` calls, 12 model-declared
  visual candidates, zero cleanup actions, sweep coverage 1.0, and runner wall
  time 1087.095s. No `connection_error` was recorded in the driver log;
  Grounding-DINO returned `status=ok` for the detector calls.
- An earlier rescued live-agent DINO run also passed at
  `output/household/semantic-map-build/codex-camera-grounded-labels/0611_1420/seed-7/report.html`.
  That run remains useful recovery evidence, but the clean `0611_1436` run is
  the detector-uptime gate for this plan closeout.
- Grounding-DINO refiner combinations are no longer completely unrun: the
  `grounding-dino+mimo-v2.5` smoke benchmark above passed on the 3-observation
  smoke corpus. Broader detector/refiner ranking remains a future optional
  benchmark until there is a broader bbox-labeled comparison corpus or an
  explicit phase budget for the hosted-refiner cost and latency; it is not a
  remaining parked gate for this adaptive-target-inspection plan.

## Problem

The current map-build plan correctly says that semantic labels, visual matches,
and generated exploration candidates are not automatically executable robot
targets. It is still too easy for an implementation agent to read the sweep
flow as:

```text
visit waypoint
observe once
move on
```

That is not enough for minimal maps, RAW-FPV evidence, or semantic-map build.
The failure mode is systemic: the agent may know a target label exists, or may
see something that looks like the target, but still cannot safely navigate to
or use it because no public, reachable, actionability-checked target exists.

The desired behavior is not a single room-level destination. It is an adaptive
inspection loop that can change camera pose, revisit nearby public candidates,
ask the backend/server/operator layer to verify a new standoff point, and only
then promote a candidate toward `actionable`.

## Goals

- Make `surface=household-world intent=map-build` and later household skills
  able to inspect any allowed target area through bounded public navigation
  candidates, even when the source map has no authored room, fixture, or object
  semantics.
- Make cleanup reuse the same target-inspection support for destination
  discovery while keeping manipulation gated on current Observed Object Handles.
- Support multiple public navigation or inspection points for the same room,
  anchor, fixture, receptacle, or target query.
- Allow new custom inspection points only when produced or verified by the
  backend, server, or operator layer as public generated candidates.
- Preserve evidence-lane parity: structured world-label lanes may use cheaper
  candidate generation, but they should still expose the same public
  actionability states as map-build, camera-grounded-label, and RAW-FPV lanes.
- Make failed target search reviewable: reports should show which viewpoints,
  camera adjustments, generated candidates, and budgets were used before the
  skill declared a target missing or unreachable.

## Non-Goals

- Do not add an opaque `find_and_go` or `go_to_label` tool.
- Do not let Agent Skills invent arbitrary robot coordinates.
- Do not require a global next-best-view planner or path-optimized coverage
  planner in the first slice.
- Do not require Grounding DINO, YOLOE, Qwen, MiMo, vLLM, or SGLang for the
  first implementation gate.
- Do not treat simulator private inventory, hidden generated mess sets,
  acceptable destinations, or scorer truth as public target evidence.
- Do not make movable-object manipulation possible from an old prior or
  semantic label alone. `pick`, `place`, `place_inside`, `open`, and `close`
  still require the existing cleanup contract gates.

## Layer Ownership

Agent Skill owns strategy:

- query variants and synonyms;
- evidence lane choice;
- waypoint and candidate ordering;
- camera adjustment policy;
- search budget;
- recovery after stale references;
- stop/missing-target decisions.

MCP/server logic owns public target state:

- Target Candidate ids;
- Target Actionability Status;
- stale-reference recovery;
- stable observation, source, and provenance links;
- redaction of private inventory, hidden fixture ids, scorer truth, and
  unverified coordinates.

Backend, server, or operator map layers own executability:

- reachability;
- safety bounds;
- waypoint validity;
- standoff-pose generation or verification;
- robot-specific localization and run-enablement gates.

Reports and checkers own evidence classification:

- searched viewpoints;
- candidate ranking;
- camera-adjustment and reobserve attempts;
- actionability transitions;
- exhausted search budgets;
- private-truth exclusion;
- whether a failed goal was a perception gap, map gap, navigation gap, or
  skill-budget decision.

## Target Actionability

Use the actionability vocabulary from `auto-semantic-map-build.md`:

- `query_unmatched`: no public candidate currently matches the query.
- `visible_only`: camera evidence shows a possible target, but there is no
  executable navigation or manipulation target yet.
- `anchor_unbound`: semantic evidence names a place or object class, but it is
  not linked to a verified waypoint, standoff pose, or current observation.
- `needs_observe`: a candidate has a plausible public location, but needs a
  fresh observation from an allowed viewpoint before action.
- `unreachable`: the backend/operator layer rejected the candidate as unsafe,
  blocked, or outside the executable navigation set.
- `actionable`: the candidate has enough public evidence and backend-verified
  reachability for the requested operation.

`where is X` and `is there X` may return non-actionable candidates with caveats.
`go to X`, `use X`, and `place into/on X` require `actionable`. A raw label,
old prior, room name, or visual guess is not enough.

## Adaptive Inspection Loop

The first implementation should make the loop explicit in traces and reports:

```text
read metric_map / runtime map
choose public waypoint, anchor, generated exploration candidate, or target query
navigate to the chosen public candidate
observe
if evidence is incomplete: adjust_camera and observe again within budget
if visible but not actionable: request or derive verified standoff/inspection candidate
if candidate is verified: navigate to it and observe again
update Target Candidate and Runtime Metric Map actionability
repeat until actionable, unreachable, or public search budget is exhausted
```

Waypoint completion should mean "observed enough for the active goal or budget",
not just "arrived once". A waypoint may need multiple camera views. A room or
anchor may need multiple public navigation points. A failed candidate should
stay visible in public evidence instead of disappearing into a generic "not
found" result.

## Evidence Lane Behavior

`world-oracle-labels`:

- may use privileged simulator labels as a control lane;
- must still emit public Target Candidate/actionability state;
- should not skip actionability just because the simulator knows the label.

`world-public-labels`:

- may expose sanitized structured detections;
- must not expose destination/tool oracle hints;
- should exercise stale-reference recovery and non-actionable candidate states.

`camera-grounded-labels`:

- consumes camera-derived structured candidates;
- should preserve image region, source observation, producer, confidence, and
  viewpoint provenance;
- may create `visible_only`, `needs_observe`, or generated inspection candidates
  before anything becomes `actionable`.

`camera-raw-fpv`:

- has no pre-registered detector candidates;
- the agent or selected skill must reason from raw FPV evidence;
- should use camera adjustment, alternate viewpoints, and generated inspection
  candidates before declaring a target missing.

`map-build`:

- should treat generated exploration candidates as the initial navigation
  surface when the source map is minimal;
- should create Public Semantic Anchors only from public observation evidence;
- should expose which candidates were visited, reobserved, promoted, rejected,
  or left unvisited.

## Candidate Types

Allowed executable navigation inputs:

- authored public inspection waypoints when present;
- generated exploration candidates derived from free-space geometry and safety
  bounds;
- Public Semantic Anchors with verified waypoint or pose links;
- Generated Target Inspection Candidates produced or verified by the
  backend/server/operator layer;
- current visible-object navigation targets only after the existing visual
  candidate contract marks them executable.

Disallowed executable navigation inputs:

- arbitrary coordinates invented by the Agent Skill;
- hidden fixture ids or private inventory entries;
- raw labels without public observation and reachability evidence;
- old snapshot priors without current-run confirmation;
- visual guesses that have not been converted into a public candidate.

## Implementation Slices

### Slice 1: Public candidate trace shape

- Add a run-local Target Candidate trace shape if the current runtime map does
  not already expose enough fields.
- Preserve candidate id, query, label/category, source observation, evidence
  lane, producer provenance, waypoint or pose link, actionability, confidence,
  and rejection reason when present.
- Render candidate state in reports without adding a new MCP tool.

### Slice 2: Adaptive waypoint observation

- Teach map-build and cleanup skills that a waypoint is not complete until the
  active goal's observation budget is satisfied.
- Allow bounded `adjust_camera -> observe` attempts per waypoint or target.
- Record each camera view and whether it changed candidate state.
- Keep exact camera yaw/pitch defaults as implementation details.

### Slice 3: Generated inspection candidates

- Add server/backend support to produce or verify standoff/inspection candidates
  from visible evidence, anchor geometry, or free-space geometry.
- Expose generated candidates as public waypoint/standoff entries with
  provenance and actionability.
- Reuse `navigate_to_waypoint` if projection into generated waypoint entries is
  enough; defer a dedicated navigation tool until that shape proves insufficient.

### Slice 4: Target query recovery

- Add skill-side target-search routines for map-build, cleanup destination
  discovery, and open-ended household goals.
- Recover stale raw fixture ids or labels by resolving them through public
  target candidates rather than failing or using hidden source truth.
- Require `not found` to include the exhausted public search budget.

### Slice 5: Checker and report gates

- Check that no private truth, hidden inventory, or unverified coordinates
  reached Agent View.
- Check that non-actionable candidates did not trigger navigation, pickup, or
  placement actions.
- Check that target-missing claims include inspected viewpoints and budget.
- Check that map-build reports show visited/unvisited generated candidates and
  actionability transitions.

## Acceptance Gates

- A minimal-map `surface=household-world intent=map-build` run can start with no
  authored rooms, fixtures, or inspection waypoints and still inspect multiple
  generated candidates.
- A target that is visible from one view but not reachable from that view can
  produce a Generated Target Inspection Candidate and reobserve from it.
- A room or anchor can expose multiple public inspection points, with ranking
  and status visible in the report.
- `camera-raw-fpv` and `camera-grounded-labels` runs can show active search
  evidence instead of a one-shot waypoint sweep.
- `world-oracle-labels` and `world-public-labels` produce the same public
  actionability statuses even if their candidate producer is cheaper.
- Cleanup can use target inspection for destinations, but cannot manipulate
  movable objects from labels, priors, or semantic anchors alone.

## Execution Preflight

**Preflight status:** Approved and executed, 2026-06-11. Slices 1-5 are
implemented for deterministic direct-runner gates, with Grounding-DINO direct
validation and one Codex RAW-FPV live-agent exploratory gate completed. Keep
this preflight for historical scope and future optional live/refiner
validation, not as an active implementation backlog.

**Route:** durable `$intuitive-flow`.

**Goal:** implement adaptive target inspection so map-build and cleanup can move
from labels or weak visual evidence to public, reachable Target Candidates with
explicit actionability.

**Scope:**

- Add or extend public Target Candidate trace shape.
- Track Target Actionability Status and transitions.
- Support bounded `adjust_camera -> observe` attempts per waypoint or target.
- Add generated inspection/standoff candidates only through
  server/backend/operator verification.
- Update reports and checkers to show searched viewpoints, budgets, and
  private-truth exclusion.
- Update this source plan closeout status when done.

**Non-goals:**

- No opaque `find_and_go` or `go_to_label`.
- No agent-invented coordinates.
- No dedicated new MCP tool unless waypoint projection proves insufficient.
- No real detector/provider requirement for deterministic gates.
- No manipulation from labels, priors, or anchors alone.

**Context package:**

- Must read:
  - this plan;
  - [`auto-semantic-map-build.md`](auto-semantic-map-build.md);
  - [`../../CONTEXT.md`](../../CONTEXT.md);
  - [`../../roboclaws/household/realworld_contract.py`](../../roboclaws/household/realworld_contract.py);
  - [`../../skills/molmo-realworld-cleanup/SKILL.md`](../../skills/molmo-realworld-cleanup/SKILL.md);
  - [`../../tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py`](../../tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py).
- Useful evidence:
  - [`../human/mcp-skills-and-semantic-profiles.md`](../human/mcp-skills-and-semantic-profiles.md);
  - [`../human/molmospaces-cleanup-mode-architecture.md`](../human/molmospaces-cleanup-mode-architecture.md);
  - [`../../tests/contract/molmo_cleanup/test_molmo_realworld_contract.py`](../../tests/contract/molmo_cleanup/test_molmo_realworld_contract.py);
  - [`../../tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py`](../../tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py).
- Do not read unless needed:
  - `output/**`;
  - archived ADR execution logs;
  - unrelated operator-console dirty files.

**Definition of Done / acceptance criteria:**

- SUCCESS only if minimal-map map-build exposes multiple generated candidates
  and visit/reobserve state.
- SUCCESS only if non-actionable candidates cannot trigger navigation or
  manipulation beyond allowed inspection.
- SUCCESS only if reports/checkers show candidate ranking, viewpoints,
  actionability transitions, exhausted budget, and no private truth.
- SUCCESS only if cleanup can use target inspection for destinations while
  still requiring current Observed Object Handles for movable-object
  manipulation.
- SUCCESS only if this source plan is refreshed to `Implemented`,
  `Partially implemented`, or `Active` with explicit remaining gates.
- BLOCKED_NEEDS_LOCAL_VALIDATION if required product run gates cannot run in the
  current environment.
- Must not regress existing cleanup actionability gates, private generated
  mess/scorer truth exclusion, or minimal-map waypoint honesty checks.

**Verification:**

- Deterministic gates:
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/molmo_cleanup/test_molmo_realworld_contract.py -q`
  - `./scripts/dev/run_pytest_standalone.sh tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py -q`
  - targeted unit tests under `tests/unit/molmo_cleanup/`
- Integration gates:
  - MCP/server contract tests for `metric_map`, `observe`, `adjust_camera`,
    `declare_visual_candidates`, and generated waypoint responses;
  - report/checker tests proving non-actionable candidate rejection and
    missing-target budget evidence.
- Required product run gates:
  - `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-public-labels map_mode=minimal scenario_setup=baseline`
  - `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels map_mode=minimal scenario_setup=baseline`
  - `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=grounding-dino map_mode=minimal scenario_setup=baseline`
  - `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=camera-raw-fpv map_mode=minimal scenario_setup=baseline`
  - one cleanup consumer run with `runtime_map_prior=...` if implementation
    touches cleanup consumption.
- Local/live/manual gates:
  - `camera_labeler=grounding-dino` is required as the real camera-labeler
    proof, not optional exploration. If the visual-grounding runtime, model
    weights, GPU/CPU budget, or sidecar dependencies are unavailable, mark
    `BLOCKED_NEEDS_LOCAL_VALIDATION`; do not replace it with
    `sim-projected-labels` and claim complete.
  - If any required product run gate needs simulator/runtime support that is
    unavailable, mark `BLOCKED_NEEDS_LOCAL_VALIDATION`; do not claim complete.
- Optional exploratory gates:
  - live-agent `camera-raw-fpv`, `camera-grounded-labels`, or
    `camera_labeler=grounding-dino+<refiner>` after deterministic and
    direct-runner product gates pass.

**Execution surface:**

- Main session: root supervisor, route decisions, source-plan/status updates,
  final commit audit.
- Worker: `skill-runner` worker was recommended for the original
  implementation; no active worker is required for the completed contract.
- Worker-local goal: historical first slice was adaptive target inspection
  slices 1-3; follow-up slice 4/5 and validation were completed in the main
  flow.

**To execute:**

```text
/goal execute docs/plans/2026-06-11-adaptive-target-inspection.md with intuitive-flow
```

## Open Implementation Defaults

- Exact camera yaw/pitch/height schedule.
- Exact per-waypoint and per-target observation budgets.
- Exact candidate ranking heuristic.
- Whether the first trace payload lives only in `run_result.json` /
  `agent_view.json` or also in a separate `target_candidates.json`.
- Whether the first generated inspection candidates are implemented entirely as
  `generated_*` waypoints or later receive a dedicated public tool.

These defaults should not block the plan. Pick conservative bounded values and
make them visible in the report.

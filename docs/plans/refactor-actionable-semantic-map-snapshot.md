---
refactor_scope: actionable-semantic-map-snapshot
status: DONE
accepted_severities:
  - P0
  - P1
  - P2
last_verified: 2026-06-03
---

# Refactor Scope: Actionable Semantic Map Snapshot

## Status

DONE

## Intuitive-Flow Autoplan Reconciliation

**Review date:** 2026-06-03
**Review route:** `intuitive-flow` inline review. The vendored gstack
`autoplan` skill document is available, but the full interactive/subagent
review surface is not available in this host and the repo policy forbids bare
host Codex/Claude launches for supported demo routes. The decisions below are
reconciled into this plan before implementation, following the existing
Roboclaws pre-GSD plan pattern.

Accepted decisions:

- Add one canonical `actionable_semantic_map_snapshot_v1` wrapper around the
  existing `runtime_metric_map_v1` payload instead of introducing an
  Agibot-only cleanup loading branch.
- Keep deterministic conversion under `roboclaws.maps`: parse
  `navigation_memory.json`, Nav2 metadata, occupancy cells, source provenance,
  stable ids, reachability/actionability defaults, and materialized consumer
  targets. Agent/skill semantic judgment remains represented as explicit
  classification fields on each converted anchor.
- Prove downstream equivalence with contract tests: online semantic-map-build
  output and offline converted navigation memory must have the same
  consumer-facing snapshot sections, and actionable anchors must materialize to
  navigation waypoints plus fixture/receptacle candidates.
- Preserve current Runtime Metric Map safety: movable prior objects stay in
  `observed_objects` as `needs_confirm` priors, not static fixture candidates
  or pickable cleanup targets.
- Use a checked-in test fixture copied from the local
  `robot_map_12` artifact folder because `vendors/agibot_sdk` is a submodule;
  the converter still accepts the real vendor path when present locally.

Deferred decisions:

- Do not add a new public MCP tool or runnable task in this slice.
- Do not mutate the source Agibot map folder or any source Navigation Map
  Artifact.
- Do not require real Agibot GDK, OpenClaw, VLM relabeling, or physical robot
  validation for the first contract slice.

## Target

Define one canonical semantic-map-build completion artifact that both online
build runs and offline/prebuilt semantic-memory conversion can produce.

The target shape is:

```text
Minimal Navigation Map Artifact
  -> semantic-map-build
  -> Actionable Semantic Map Snapshot
  -> household-cleanup / open household tasks

Agibot navigation_memory.json
  -> conversion skill
  -> Actionable Semantic Map Snapshot
  -> household-cleanup / open household tasks
```

The snapshot should preserve the current Runtime Metric Map safety boundary
while also carrying enough materialized navigation and fixture/receptacle
targets for downstream tools to consume it directly.

## Accepted Severities

- P0: Any private scoring truth, generated mess truth, or hidden acceptable
  destination data leaked into agent-facing semantic-map artifacts.
- P1: Online semantic-map-build output and offline converted semantic memory
  cannot be consumed through the same canonical artifact contract.
- P1: A semantic target is visible in Agent View but cannot be materialized as a
  valid navigation waypoint or fixture/receptacle target when its status says it
  is actionable.
- P2: Naming, documentation, test, or adapter drift that makes future agents
  rediscover the difference between visible semantic anchors and tool-valid
  registered targets.

## Accepted Cleanup Checklist

- [x] Define the canonical **Actionable Semantic Map Snapshot** contract:
      source navigation-map reference, `runtime_metric_map_v1`, public semantic
      anchors, materialized inspection waypoints, materialized
      fixture/receptacle candidates, affordances, reachability/actionability
      status, and evidence/provenance.
- [x] Make the contract explicit that online `semantic-map-build` output and
      offline `navigation_memory.json` conversion produce the same downstream
      artifact shape. Only provenance should differ.
- [x] Add a conversion boundary for
      `vendors/agibot_sdk/artifacts/maps/*/navigation_memory.json` that can be
      owned by a skill: deterministic scripts perform file parsing, map-frame
      checks, and scaffold generation; an agent supplies semantic
      classification such as anchor type, affordances, object-vs-fixture, and
      review status.
- [x] Add contract tests proving a converted Agibot navigation-memory artifact
      can be loaded as the same semantic-map snapshot shape expected from an
      online build result.
- [x] Add contract tests proving cleanup/open-task consumers can materialize
      actionable anchors as valid navigation waypoints and fixture/receptacle
      targets without reading private truth.
- [x] Preserve existing Runtime Metric Map prior safety for movable objects:
      observed-object priors remain `needs_confirm` until current-run evidence
      confirms them.
- [x] Update human/agent docs only where they describe the map artifact
      boundary: Minimal Navigation Map Artifact, Runtime Metric Map, Public
      Semantic Anchor, Prebuilt Robot Map Bundle, and semantic-map-build output.

## Success Criteria

The primary success rule is:

```text
Online semantic-map-build output and offline converted navigation_memory output
produce the same downstream artifact contract. Cleanup and open household tasks
consume it through one path.
```

Concrete acceptance criteria:

- The two producer paths are structurally equivalent:
  `Minimal Navigation Map Artifact -> semantic-map-build` and
  `navigation_memory.json -> conversion skill` both produce an Actionable
  Semantic Map Snapshot. They may differ in producer/provenance metadata only.
- Semantic entries are both agent-visible and tool-consumable. If an anchor is
  marked actionable, the consumer can materialize a valid navigation waypoint
  and, when appropriate, a fixture/receptacle target with affordances.
- Static, semi-static, and movable semantics stay separated. Fixed destinations
  such as fridges, sinks, tables, sofas, and room areas can become
  fixture/receptacle/surface/room anchors. Movable objects such as a plastic
  bottle must not be promoted into static fixtures.
- Private scoring truth remains absent from every agent-facing artifact:
  generated mess sets, acceptable destination sets, private manifests, target
  counts, and scorer-only truth are forbidden.
- Prior movable objects remain non-actionable until current-run evidence
  confirms them. A converted or prior observed object must default to
  `needs_confirm`, not `actionable`.
- Uncertainty is explicit. Reachability conflicts, low-confidence semantics,
  missing referenced evidence artifacts, or ambiguous object-vs-fixture
  classifications must be represented with status fields such as
  `needs_review`, `observe_only`, `costmap_disagrees`, `projected`, or
  equivalent contract values.
- No special cleanup/open-task branch is introduced for Agibot
  `navigation_memory.json`. The conversion happens at the map-artifact boundary;
  downstream tasks consume the canonical snapshot.

Counterexamples that fail this gate:

- The agent can see `fridge_main`, but `navigate_to_waypoint` or
  `navigate_to_receptacle` treats it as an unknown target.
- Online semantic-map-build output and offline converted output require
  different cleanup loading paths.
- `plastic_bottle_table_1` appears in static fixture semantics.
- A prior movable object from a previous snapshot is directly pickable without
  current-run confirmation.
- The converted artifact leaks private cleanup truth or silently mutates the
  source navigation map.

## Vendor Fixture Use

Use
`vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json` as the
primary real input fixture for the offline conversion path.

The test fixture should include the whole map folder, not only the JSON file:

- `navigation_memory.json` for semantic memory entries.
- `agibot/nav2.yaml` for map-frame metadata.
- `agibot/occupancy.pgm` for offline costmap/free-cell checks.
- `agibot/source.json` and `agibot/raw_map.json.gz` for source provenance when
  needed.

This vendor map is intentionally valuable because it includes mixed semantic
types and edge cases:

- `fridge_main`, `sink_kitchen_1`, `coffee_table_1`, `long_table`, and
  `large_white_sofa_1` cover receptacle/surface/fixture classification.
- `kitchen_center` covers a room-area anchor.
- `stone_book_decor_1` covers a low-confidence landmark/decor candidate.
- `plastic_bottle_table_1` covers movable-object handling and must not become
  a static fixture.
- `fridge_main` has evidence of successful navigation but its current
  `nav_goal` does not land on a free occupancy cell. The conversion must record
  this conflict explicitly instead of silently hiding it.

Do not make the tests depend on byte-for-byte equality of the entire converted
JSON. Evidence notes, timestamps, and source text may change. Prefer a frozen
expected summary under `tests/fixtures` or equivalent contract assertions for
the fields that matter:

- anchor count and required anchor ids
- materialized waypoint ids
- fixture/receptacle/surface classification for known entries
- movable-object non-promotion for `plastic_bottle_table_1`
- reachability status for `fridge_main`
- no forbidden private keys
- producer/provenance values identifying offline navigation-memory conversion

## Test Strategy

First-pass verification does not require real hardware.

Required offline/mock tests:

- Unit tests for deterministic parsing of `navigation_memory.json`, Nav2 YAML
  parsing, world-to-grid projection, free-cell checks, and stable id generation.
- Unit tests for semantic normalization defaults: anchor type, affordances,
  object-vs-fixture-vs-landmark classification, actionability, and review
  status.
- Contract tests that convert `robot_map_12` into an Actionable Semantic Map
  Snapshot and assert the success criteria above.
- Contract tests that compare the consumer-facing shape of an online
  semantic-map-build snapshot and an offline converted snapshot. The assertion
  should be equivalence of contract shape and consumer materialization, not
  identical provenance.
- Contract tests proving actionable anchors can materialize into navigation
  waypoints and fixture/receptacle candidates through the same loading path
  used by cleanup/open tasks.
- Checker tests proving private-truth exclusion and prior-object
  non-actionability still hold.
- One mock or smoke cleanup/open-task run that consumes the converted snapshot
  and proves the task reads targets from the artifact rather than a special
  Agibot-only branch.

Optional local follow-up tests:

- Real Agibot GDK map fetch or PNC navigation validation.
- OpenClaw Gateway or physical robot consumption of the converted snapshot.
- Real VLM semantic relabeling or visual evidence expansion.
- Real manipulation proof for pick/place/open/close.

Those local gates are useful confidence evidence, but they do not block the
first contract slice unless a later scope update explicitly requires them.

## Parked Cross-Seam / Future Ideas

- Full room-wide semantic annotation is out of scope; the first conversion may
  use only the semantic entries already present in `navigation_memory.json`.
- Real Agibot GDK, OpenClaw Gateway, VLM, and physical robot validation are out
  of scope for the first contract slice.
- Cleanup policy strategy changes are out of scope. The goal is to make the
  world artifact consumable, not to redesign object-selection behavior.
- Persistent source-map mutation remains out of scope. The snapshot is a
  derived, reviewable artifact; it is not a silent rewrite of the original
  source map.
- A polished public skill UX for semantic labeling can follow after the
  contract and core conversion proof are stable.

## Evidence Ladder

- L0 Static: `ruff check` for touched Python modules and tests.
- L1 Unit/mock: unit tests for deterministic conversion helpers, map-frame
  projection, reachability status assignment, and affordance normalization.
- L2 Contract: contract tests for snapshot schema, no-private-truth guarantees,
  vendor `robot_map_12` conversion, online/offline artifact equivalence, and
  cleanup/open-task consumer materialization.
- L3 Mock regression: one mock or smoke cleanup/open-task run consuming the
  converted snapshot through the same path used for online build output.
- L4+ Local-only gates are optional follow-up evidence for real Agibot/OpenClaw
  runs and should not block the first contract slice unless explicitly requested.

## Stop Condition

Stop when all accepted P0/P1/P2 checklist items inside this target are either
implemented and verified through L2 contract tests, or explicitly parked with a
reason. The final state must let future agents state one rule:

```text
Online semantic-map-build output and offline converted navigation_memory output
produce the same Actionable Semantic Map Snapshot contract. Cleanup and open
household tasks consume that contract through one path.
```

Do not start broad cleanup, policy redesign, full map annotation, or local
hardware validation under this gate.

## Execution Log

- 2026-06-03: Created scope gate after discussion of
  `vendors/agibot_sdk/artifacts/maps/robot_map_12/navigation_memory.json`.
  Decision: the prebuilt semantic memory should not be treated as minimal-map
  input. It should convert to the same canonical completion artifact as an
  online semantic-map-build run, with different provenance only.
- 2026-06-03: Extended gate with explicit success criteria, vendor fixture use,
  offline/mock test strategy, and local hardware boundary. Decision: the first
  contract slice must use `robot_map_12` as a real conversion fixture but must
  not require real Agibot hardware, OpenClaw, VLM, or physical manipulation
  validation.
- 2026-06-03: Implemented the first contract slice. Added
  `roboclaws.maps.actionable_snapshot`, the Agibot navigation-memory converter,
  the skill-owned wrapper, `robot_map_12` test fixture, shared
  `runtime_map_prior` snapshot unwrapping, and contract tests for online/offline
  shape equivalence, consumer materialization, private-truth exclusion, and
  movable-prior non-actionability. Focused verification passed:
  `./scripts/dev/run_pytest_standalone.sh tests/contract/maps/test_actionable_semantic_map_snapshot.py tests/contract/maps/test_nav2_map_bundle_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/skills/test_skill_manifests.py -q`;
  `ruff check` and `ruff format --check` on touched Python/script files; direct
  converter and skill wrapper runs both exported 9 anchors, 6 fixtures, and 9
  waypoints.

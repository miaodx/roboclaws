---
plan_scope: agent-view-module-refactor
status: Implemented
created: 2026-06-22
last_reviewed: 2026-06-23
implementation_allowed: true
source:
  - user north-star clarification on open-ended robot agency and eval-driven evolution
  - plan-bakeoff candidate selection, 2026-06-22
related_context:
  - README.md
  - ARCHITECTURE.md
  - STATUS.md
  - CONTEXT.md
  - docs/human/domain.md
  - docs/human/mcp-skills-and-semantic-profiles.md
  - docs/human/molmospaces-settings.md
  - docs/adr/0136-use-base-navigation-map-and-first-class-household-launch-contracts.md
  - docs/adr/0138-use-detector-only-visual-grounding-sidecar.md
  - docs/adr/0140-use-eval-suites-as-first-class-architecture-layer.md
  - docs/adr/0141-use-eval-harness-as-maintainer-orchestration-facade.md
  - docs/adr/0145-use-agent-view-as-household-world-module-boundary.md
---

# Agent View Module Refactor

## Goal

Make **Agent View** the explicit module boundary for what a household-world
agent may see and act on.

The refactor should turn the current scattered rule into a concrete contract:

```text
Every agent-facing input is either:
  real-robot-obtainable public evidence,
  provenance-limited public evidence,
  or an explicitly blocked capability/status.

Private scorer truth, hidden setup state, simulator-only affordances, and
report-only views must not enter Agent View.
```

This is Candidate 1 from the architecture bakeoff. Candidate 4, active
perception, is included as an adapter inside this module. Candidate 2,
eval-to-evolution, is the immediate follow-up after this plan creates a stable
`agent_view_module` evolution target. Candidate 3, capability-slice eval
groups, stays parked as later eval-harness metadata.

Scope decision: Agent View is the shared household-world contract across
current and planned household backends, including MolmoSpaces/MuJoCo and
Agibot/GDK. Backend-local payload construction may remain local only when it is
behind the shared Agent View schema, guard, provenance, and blocked-capability
vocabulary.

## Why Now

The repo has intentionally broadened its surface:

- open-ended household prompts;
- coding-agent engines such as Codex CLI and Claude Code;
- OpenAI Agents SDK;
- direct deterministic runners;
- Base Navigation Map and Runtime Metric Map artifacts;
- `world-public-labels`, `camera-grounded-labels`, and `camera-raw-fpv`
  evidence lanes;
- Grounding DINO and other camera labelers;
- RAW-FPV candidate declaration and recovery;
- eval suites and eval-harness selection rows.

That breadth is not the problem. The current entropy is that the rule
"only expose what a real robot could obtain" is enforced by a mix of payload
builders, MCP profile metadata, RAW-FPV guidance, visual-candidate lifecycle
helpers, report code, and repeated `assert_no_forbidden_agent_view_keys` calls.

A clear Agent View Module gives the broad surface one ownership point. It also
lets evals later route failures to `agent_view_module` instead of vaguely
blaming provider routes, prompts, or broad harness rows.

## Current Evidence

Current source shape:

- `roboclaws/household/realworld_agent_view_contract.py` owns useful helper
  behavior such as forbidden-key checks, public acceptance config, policy-trace
  delegation, and real-robot readiness extraction.
- `roboclaws/household/realworld_contract_payloads.py` builds
  `agent_view_payload`, `runtime_metric_map_payload`, policy view, camera-model
  evidence, model-declared observations, and sanitized visible detections.
- `roboclaws/household/realworld_contract.py` still acts as a broad coordinator
  and forwards many private guard functions into helper modules.
- `roboclaws/household/agibot_cleanup_contract.py` has a separate
  `agent_view_payload` with the same top-level shape for the Agibot pilot path.
  This is a second owner for Agent View semantics and must be brought under the
  same guard/schema contract even if backend-specific payload construction
  stays local in the first implementation slice.
- RAW-FPV and active perception semantics are spread across
  `raw_fpv_guidance.py`, `realworld_visual_candidates.py`,
  `realworld_visual_candidate_declarations.py`,
  `realworld_visual_candidate_lifecycle.py`, `visual_grounding.py`, and
  `visual_grounding_contract.py`.
- `roboclaws/mcp/profiles.py` owns capability profile metadata that influences
  the agent-facing public tool/capability surface.
- `skills/eval-harness/scripts/select_eval_harness.py` and
  `skills/eval-harness/scripts/eval_harness_rows.py` still exist on this
  branch. The JSON row catalog and ADR-0145 discussed in an earlier branch are
  not present here, so this plan must not assume them.
- The current eval-harness selector already has signals for
  `realworld_contract`, `visual_grounding`, `raw_fpv`, and
  `runtime_metric_map`, but it does not explicitly know a future
  `roboclaws/household/agent_view.py` path yet.

Observed risk:

- Agent View is documented as the exact public information available to the
  cleanup agent, but current implementation does not expose one module-shaped
  interface that names all inputs, provenance, blocked capabilities, and
  private exclusions.
- `static_fixture_projection` still appears in current payload paths. This plan
  should not preserve it as an Agent View compatibility surface. Known
  consumers should migrate to the new Agent View contract shape, and the
  explicit contract should center Base Navigation Map, Runtime Metric Map,
  public runtime evidence, active perception evidence, public MCP capabilities,
  and blocked/provenance-limited states.

## Architecture Decision To Record

Create a short ADR before implementation.

Decision:

- Agent View is a first-class household-world module boundary.
- Agent View owns agent-facing input assembly, provenance labeling,
  real-robot-obtainability labeling, blocked-capability labeling, and private
  exclusion enforcement.
- Agent View enforcement covers every agent-facing robot input, including
  `agent_view.json`, MCP tool responses, `done` readiness blockers, visual
  candidate responses, and any sidecar evidence returned to the agent.
- Active perception is an Agent View adapter, not a separate top-level product
  goal.
- Active-perception sidecar inputs must be built from public Agent View
  evidence, Base Navigation Map, Runtime Metric Map, or public fixture hints;
  private scorer truth, hidden setup state, simulator-only fixture oracles, and
  report-only views must not feed the sidecar.
- Eval-to-evolution should later be allowed to target `agent_view_module` as a
  concrete evolution target.

The ADR should not approve a broad eval-harness redesign. It should only name
the boundary that this refactor creates.

## Target Module Shape

Prefer evolving the existing implementation instead of adding a parallel
concept.

Suggested package shape:

```text
roboclaws/household/agent_view.py
  AgentViewPayload
  AgentViewSection / provenance helper types if useful
  build_agent_view(...)
  build_or_validate_agent_tool_response(...)
  build_runtime_metric_map_view(...)
  build_policy_view(...)
  build_active_perception_sidecar_input(...)
  assert_no_private_agent_view_keys(...)
  strip_private_agent_view_keys(...)
  label_real_robot_obtainability(...)

roboclaws/household/agent_view_adapters.py       # only if agent_view.py gets too large
  map adapter
  runtime evidence adapter
  active perception adapter
  mcp capability/profile adapter
```

If a rename is lower churn, `realworld_agent_view_contract.py` may become the
module owner directly. Avoid a second module that duplicates the same concept.

Expected Agent View sections:

| Section | Owns | Notes |
| --- | --- | --- |
| `schema` / version marker | explicit artifact-contract version such as `agent_view_v2` | Artifact name can remain `agent_view.json`; field layout changes still need a visible schema/version. |
| `task` | prompt, preset/intent, public acceptance config | No private scenario setup or scorer target count. |
| `capabilities` | public tool names, capability profile metadata, blocked capabilities | Pulls from MCP/capability profile source, not duplicated prose. |
| `base_navigation_map` | start-of-run public map context | Must not include static movable inventory or private relocation truth. |
| `runtime_metric_map` | public current-run map/evidence enrichment | Owns observed objects, anchors, candidates, map-update candidates. |
| `active_perception` | RAW-FPV observations, camera-grounded labels, visual-grounding provenance | Candidate 4 lives here. Include uncertainty and sidecar readiness. |
| `policy_view` | allowed/excluded policy inputs | Report-only views stay explicitly excluded. |
| `readiness` | real-robot readiness and blocked/provenance-limited states | Use explicit labels rather than silent fallbacks. |
| `privacy` | forbidden key policy and private-truth absence evidence | One canonical guard. |

Names may change during implementation, but these responsibilities should not
disappear.

## Implementation Slices

### Slice 1: ADR And Interface Inventory

- Add the ADR described above.
- Inventory current agent-facing payload builders and private guard call sites.
- Inventory agent-facing MCP tool responses, `done` readiness blocker payloads,
  visual candidate responses, and active-perception sidecar request inputs that
  can affect what an agent sees or acts on.
- Identify which current fields are public current contract, historical/report
  compatibility, or migration candidates.
- Record the intended owner for each field in the plan or ADR appendix.
- Include both MolmoSpaces/realworld and Agibot cleanup Agent View producers in
  the inventory. Do not let the new module become Molmo-only by accident.
- Do not move builders, rename code modules, or migrate artifact consumers in
  this slice. Slice 1 is ADR plus interface inventory only.

Acceptance:

- The ADR names Agent View as the module boundary.
- The field inventory distinguishes Base Navigation Map, Runtime Metric Map,
  active perception, MCP capability metadata, blocked capabilities, and private
  exclusions.
- The inventory distinguishes artifact payloads from live agent-facing tool
  responses and sidecar inputs, and names whether each is Agent View-owned,
  Agent View-derived, or report/private-only.
- The inventory explicitly marks `static_fixture_projection` as not a new
  long-term public Agent View center.
- The inventory has a row for `agibot_cleanup_contract.agent_view_payload` and
  states whether it migrates in this plan or remains a backend-local adapter
  behind shared Agent View guards.
- The inventory states that Agent View covers all household-world backends,
  including Agibot, while full builder migration is deferred until a later
  slice.

#### Slice 1 Interface Inventory

Status: complete for inventory, code movement intentionally not started in
this slice.

ADR: `docs/adr/0145-use-agent-view-as-household-world-module-boundary.md`

Architecture layer: Agent View sits between **Agent Skill** strategy and the
**MCP Capability Contract And Tools** / **Artifacts** layers. It owns the
agent-facing evidence boundary and must not move cleanup strategy into server
adapters.

Inventory:

| Surface | Current owner | Current field/response shape | Classification | Intended Agent View owner |
| --- | --- | --- | --- | --- |
| MolmoSpaces saved Agent View artifact | `roboclaws/household/realworld_contract_payloads.py::agent_view_payload`, called by `RealWorldCleanupContract.agent_view_payload` | `contract`, `perception_mode`, `metric_map`, `runtime_metric_map`, `static_fixture_projection`, `observed_objects`, `raw_fpv_observations`, camera/model evidence, `policy_view`, `cleanup_worklist`, `public_tool_names`, forbidden absence marker | Agent View-owned artifact payload | Move or wrap behind canonical Agent View builder in Slice 2, add explicit schema/version, and migrate known consumers to sectioned fields. |
| Agibot cleanup saved Agent View artifact | `roboclaws/household/agibot_cleanup_contract.py::AgibotCleanupMCPContract.agent_view_payload` | Same broad top-level shape as MolmoSpaces, with physical navigation evidence and blocked manipulation | Backend-local Agent View producer | Wrap with shared Agent View schema/guard/provenance vocabulary in Slice 2; full builder unification may wait if it would pull Agibot-specific backend logic into Molmo realworld paths. |
| Base Navigation Map / metric map | `realworld_contract_projection._metric_map`, Agibot adapter `metric_map`, MCP `metric_map` responses | Start-of-run map context, public rooms/waypoints/driveable geometry, inspection candidates, current visit state | Agent View-owned public map section | `base_navigation_map` section; must exclude static movable inventory, private relocation truth, and private scorer targets. |
| Runtime Metric Map | `realworld_contract_payloads.runtime_metric_map_payload`, `realworld_runtime_map_contract`, `realworld_runtime_map_targets`, Agibot `runtime_metric_map_payload` | Current-run public map enrichment, observed objects, priors, public semantic anchors, target candidates, actionability, map-update candidates | Agent View-owned runtime evidence section | `runtime_metric_map` section; owns semantic enrichment and current-run evidence. |
| Historical/static fixture projection | `realworld_contract_projection._static_fixture_projection`, Agibot `static_fixture_projection`, report/map readers | Static fixture/receptacle projection, sometimes copied inside saved Agent View today; active MCP calls reject `static_fixture_projection` | Migration/report-compatibility artifact, not new public Agent View center | Keep as report/map compatibility only where required; Slice 2 should stop treating it as a first-class Agent View section unless narrowed to public fixture hints under `base_navigation_map` or `runtime_metric_map`. |
| Public cleanup worklist | `realworld_contract_payloads.cleanup_worklist_payload`, Agibot `cleanup_worklist_payload`, done readiness | Public observed handles, candidate fixtures or destination policies, waypoint/room sweep state | Agent View-derived task/readiness input | Belongs under `task` or `readiness`/`runtime_metric_map` derived state; no private acceptable destination sets. |
| Policy view | `realworld_contract_payloads.policy_view_payload`, Agibot `policy_view_payload` | Allowed policy inputs and excluded report-only views | Agent View-owned privacy/policy section | `policy_view` plus `privacy`; explicitly list report-only exclusions. |
| Forbidden private-key guard | `realworld_agent_view_contract.assert_no_forbidden_agent_view_keys`, local `_assert_no_forbidden_agent_view_keys` wrappers, Agibot currently implicit | Recursive guard rejects private keys such as generated mess state, relocation data, target count, private manifests, acceptable destinations, scorer fields | Agent View-owned guard | Centralize as canonical guard in Slice 2 and apply to MolmoSpaces artifacts, Agibot artifacts, and live response payloads. |
| Live MCP success/error responses | `RealWorldCleanupContract._ok/_error`, `realworld_tool_responses.py`, MCP backend dispatch, Agibot map-build tools | Public tool response envelopes for map, navigation, observe, visual candidates, manipulation, blocked capability, and errors | Agent View-owned or Agent View-derived live response | Slice 2 must validate live agent-facing responses with the same forbidden-key guard used for artifacts. |
| `done` readiness blocker | `realworld_done_readiness.evaluate_done_readiness` and `done_readiness_blocked_response`; server `done_readiness_evidence` summarizes public trace substeps | Structured blocker/recovery payloads based on public Agent View state, public trace evidence, public worklists, and acceptance config | Agent View-derived live response | Keep under Agent View guard; readiness may use public trace evidence, never private generated mess membership or scorer truth. |
| RAW-FPV observations | `realworld_contract_payloads.record_raw_fpv_observation`, Agibot `_raw_observation_from_response`, `raw_fpv_guidance.py`, tests/probes | Robot-local camera observations, image artifact status, no structured detections before declaration | Agent View-owned active-perception evidence | Move under `active_perception.raw_fpv_observations` with source/provenance and blocked/unavailable states in Slice 3. |
| Camera-grounded labels and visual grounding evidence | `visual_grounding.py`, `visual_grounding_contract.py`, `realworld_visual_candidates.py`, `camera_model_policy_payload` | Detector pipeline IDs, candidate evidence, failure counts, duplicate rate, model provenance | Agent View-owned active-perception adapter | `active_perception.camera_grounded_labels` / `visual_grounding` section; sidecar unavailable and provider unavailable states must be explicit. |
| Visual candidate lifecycle/tool responses | `realworld_visual_candidate_lifecycle.py`, `realworld_visual_candidate_declarations.py`, `realworld_visual_candidates.py` | `declare_visual_candidates`, `navigate_to_visual_candidate`, candidate state/history/actionability and recovery | Agent View-derived live response | Continue using public runtime evidence and enforce canonical Agent View guard on responses; candidate summary folds into active perception. |
| Active-perception sidecar requests | `visual_grounding_contract.py` and visual-grounding client/request code; tests currently include requests with `static_fixture_projection` in some Agibot pilot paths | Detector request inputs built from current camera evidence and context | Agent View-derived sidecar input | Slice 3 must prove requests are built from public Agent View/Base Navigation Map/Runtime Metric Map/public fixture hints/current camera evidence only; `static_fixture_projection` request fields are migration candidates. |
| Capability/profile metadata | `roboclaws/mcp/profiles.py`, `realworld_mcp_backend.agent_view_public_tool_names`, `public_tool_names` methods | Public tool names, capability families, provenance expectations, blocked capabilities | Agent View-derived capability section | Slice 4 should derive `capabilities` and blocked capabilities from current MCP profiles/tool registration instead of duplicating stale prose. |
| Private evaluation payloads | `RealWorldCleanupContract.private_evaluation_payload`, `AgibotCleanupMCPContract.private_evaluation_payload`, reports/scorers | Generated mess set/count, acceptable destination sets, object results, private scoring truth | Report/private-only | Never Agent View-owned or Agent View-derived; may appear only after run for scorer/report surfaces. |
| Report-only robot views | Report renderers, robot-view/chase-camera artifacts, policy view exclusions | Chase/third-person or private operator views for human review | Report-only | Keep excluded through `policy_view`/`privacy`; do not feed Agent View or sidecar inputs. |
| Eval-harness selection | `skills/eval-harness/scripts/select_eval_harness.py`, `eval_harness_rows.py` | Signals for realworld contract, MCP/checker, raw FPV, visual grounding, runtime maps, open-ended routes | Verification surface | Slice 2 should add a narrow Agent View module path signal so diffs under the canonical module select Agent View contract coverage. |

Field ownership notes:

- Public current contract fields: Base Navigation Map/metric map, Runtime
  Metric Map, public observed handles, raw FPV observations, camera-grounded
  labels, visual candidate public state, MCP tool names, blocked capabilities,
  public acceptance config, done-readiness public blockers.
- Historical/report compatibility fields: saved-artifact
  `static_fixture_projection` and static fixture projection report/map readers.
  This plan must not preserve it as the long-term Agent View center.
- Private/report-only fields: generated mess state, relocation/setup details,
  target counts, acceptable destination sets, private manifests, scorer object
  results, simulator-only fixture oracles, report-only chase/third-person
  camera views.
- Agibot migration status: `agibot_cleanup_contract.agent_view_payload` remains
  backend-local for the first implementation slice, but Slice 2 must wrap it in
  the shared Agent View schema, guard, provenance labels, and blocked-capability
  vocabulary. Leaving it as an unvalidated duplicate is not accepted.

### Slice 2: Canonical Agent View Builder

- Move or wrap `agent_view_payload` construction behind one canonical builder.
- Centralize forbidden-private-key enforcement through the Agent View module
  for both `agent_view.json` and agent-facing MCP/tool response payloads.
- Add explicit real-robot-obtainability/provenance labels to top-level Agent
  View sections.
- Keep existing product launch commands and output artifact names stable.
- Treat this as a forward architecture upgrade, not a backward-compatibility
  patch. Migrate known in-repo consumers to the new `agent_view.json` contract
  shape in the same scoped work instead of keeping old top-level keys only for
  compatibility.
- Add an explicit Agent View schema/version marker such as `agent_view_v2`
  before changing the artifact field layout.
- Teach eval-harness path selection to recognize the new Agent View module path
  in this slice so diff-based `recommend` does not miss the new boundary.
- Ensure MolmoSpaces and Agibot Agent View payloads use the same forbidden-key
  guard and section labeling vocabulary, even if their backend-specific map or
  movement evidence stays in separate adapters.

Acceptance:

- `agent_view.json` remains the artifact name, but its schema may move forward
  when the ADR names the new contract, the payload carries an explicit schema or
  version marker, and known consumers are migrated.
- Callers use the canonical Agent View module rather than assembling payloads
  directly across unrelated helper modules.
- Forbidden private fields still fail loudly in both artifact payloads and
  agent-facing tool responses.
- No compatibility shim is added for obsolete public command names.
- No compatibility shim is added for the old Agent View field layout.
- Eval-harness focused recommendations include Agent View contract coverage for
  changes under the new Agent View module path.
- The Agibot payload path is either migrated to the shared builder or explicitly
  wrapped by shared Agent View validation; leaving it as an unvalidated duplicate
  is not accepted.

#### Slice 2 Implementation Evidence

Status: complete for canonical builder and known in-repo consumer migration.

Implementation notes:

- Added `roboclaws/household/agent_view.py` as the canonical Agent View module
  with `schema=agent_view_v2`, section metadata, section accessors, and the
  shared private-field guard.
- Routed MolmoSpaces, Agibot cleanup, Agibot map-build MCP, Agibot SDK export,
  and MolmoSpaces Agibot rehearsal payload producers through the v2
  schema/guard vocabulary.
- Migrated known report, checker, probe, corpus, artifact, and focused test
  consumers to v2 accessors. The remaining old-shape scan hits are local
  pseudo-map fixtures in `tests/contract/maps/test_nav2_map_bundle_contract.py`,
  not saved `agent_view.json` artifacts.
- Added a narrow eval-harness path signal for the new Agent View module.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/unit/evals/test_eval_harness_selector.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  -k 'agent_view or agibot or raw_fpv or camera_model_policy or open_ended' \
  tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py::test_agibot_molmospaces_prehardware_map_build_starts_from_base_navigation_map
```

Result: passed with one environment/fixture skip.

Additional proof:

```bash
ruff check roboclaws/household scripts/molmo_cleanup scripts/visual_grounding \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/unit/evals/test_eval_harness_selector.py

ruff format --check roboclaws/household scripts/molmo_cleanup/realworld_agent_view_checker.py \
  scripts/molmo_cleanup/realworld_base_navigation_map_checker.py \
  scripts/molmo_cleanup/realworld_agibot_map_build_checker.py \
  scripts/molmo_cleanup/realworld_waypoint_honesty_checker.py \
  scripts/molmo_cleanup/run_raw_fpv_perception_probe.py \
  scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  scripts/molmo_cleanup/run_codex_cleanup_apple2apple_summary.py \
  scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/unit/evals/test_eval_harness_selector.py

just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

Result: static checks passed; eval-harness wrote
`output/eval-harness/20260622T180801Z/eval_harness.json`.

### Slice 3: Active Perception Adapter

- Bring RAW-FPV guidance, camera-grounded-label evidence, detector provenance,
  visual-grounding sidecar status, uncertainty, and candidate lifecycle summary
  under the Agent View active-perception section.
- Build visual-grounding / detector sidecar inputs only from public Agent View
  evidence, Base Navigation Map, Runtime Metric Map, public fixture hints, or
  current camera evidence.
- Preserve the current distinction between `camera-raw-fpv` and
  `camera-grounded-labels`.
- Do not make DINO or RAW-FPV separate top-level goals outside Agent View.

Acceptance:

- RAW-FPV observations and camera-grounded labels carry source/provenance.
- Sidecar unavailable, provider unavailable, and no-camera evidence states are
  visible as blocked/provenance-limited Agent View state rather than silent
  fallback.
- Sidecar request payloads do not consume private scorer truth, hidden
  relocation/setup state, simulator-only fixture oracles, or report-only views.
- If an existing sidecar request schema still names `static_fixture_projection`,
  it must be treated as a migration candidate toward public map/fixture hints,
  not as permission to pass private fixture truth.
- Existing RAW-FPV candidate recovery tests still pass or are updated to assert
  the new Agent View section.

#### Slice 3 Implementation Evidence

Status: complete for active-perception summaries and live sidecar request
boundary.

Implementation notes:

- Added Agent View `active_perception.raw_fpv_summary`,
  `active_perception.camera_grounded_labels`, and
  `active_perception.visual_candidate_lifecycle` summaries derived from public
  RAW-FPV rows, detector/model-declared evidence, and visual-candidate lifecycle
  rows.
- Advanced the live visual-grounding request schema to
  `visual_grounding_request_v2` and replaced request
  `static_fixture_projection` with `public_map_hints.fixture_hints`.
- Updated MolmoSpaces, Agibot map-build, the visual-grounding HTTP service
  adapter, and the benchmark runner to use the v2 request shape.
- Added request validation that rejects legacy `static_fixture_projection`,
  `public_map_hints.private_truth_included=true`, and known private scorer or
  setup keys inside sidecar map hints.
- Replaced stale policy-view allowed-input vocabulary with
  `base_navigation_map` / `runtime_metric_map` for current Agent View policy
  inputs.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/contract/visual_grounding/test_visual_grounding_service.py \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  -k 'raw_fpv_mode_suppresses_structured_detections or camera_model_policy_observe_exposes_model_declared_candidates or camera_model_policy_records_sim_pipeline_provenance or camera_labels_http_success_uses_destination_resolver or camera_labels_http_failure_is_visible_without_sim_fallback or camera_labels_missing_raw_image_fails_before_sidecar or agent_view_payload_keeps_private_evaluation_out' \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  -k 'camera_grounded_composite or raw_fpv or camera_labels_declare_response_is_agent_compact' \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding
```

Result: passed.

Additional proof:

```bash
ruff check roboclaws/household/agent_view.py \
  roboclaws/household/visual_grounding.py \
  roboclaws/household/visual_grounding_contract.py \
  roboclaws/household/realworld_visual_candidates.py \
  roboclaws/household/realworld_visual_candidate_declarations.py \
  roboclaws/household/agibot_map_build_mcp_server.py \
  roboclaws/household/realworld_contract_payloads.py \
  roboclaws/household/agibot_cleanup_contract.py \
  scripts/visual_grounding/adapters.py \
  scripts/visual_grounding/run_visual_grounding_benchmark.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/contract/visual_grounding/test_visual_grounding_service.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py

ruff format --check roboclaws/household/agent_view.py \
  roboclaws/household/visual_grounding.py \
  roboclaws/household/visual_grounding_contract.py \
  roboclaws/household/realworld_visual_candidates.py \
  roboclaws/household/realworld_visual_candidate_declarations.py \
  roboclaws/household/agibot_map_build_mcp_server.py \
  roboclaws/household/realworld_contract_payloads.py \
  roboclaws/household/agibot_cleanup_contract.py \
  scripts/visual_grounding/adapters.py \
  scripts/visual_grounding/run_visual_grounding_benchmark.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/contract/visual_grounding/test_visual_grounding_service.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py

git diff --check
```

Result: passed after formatting touched Slice 3 files.

### Slice 4: MCP Capability/Profile Adapter

- Ensure Agent View capability metadata is derived from current MCP capability
  profiles and public tool names.
- Represent blocked capabilities in Agent View using the same vocabulary as
  capability profiles/reports where possible.
- Keep server/runtime adapters thin; do not move cleanup strategy or prompt
  policy into server code.

Acceptance:

- Agent View describes available public tools and blocked capabilities without
  duplicating stale profile semantics.
- MCP server and launch routes keep the same public command grammar.

#### Slice 4 Implementation Evidence

Status: complete for MCP profile-derived capability metadata.

Implementation notes:

- Agent View now derives `capabilities` from MCP profile metadata and runtime
  public-tool registration. The section includes profile metadata, expected
  public tool names by profile, runtime extra public tools, public tool
  descriptors, and blocked-capability details.
- `with_public_tool_names(...)` rebuilds the derived capability section when
  MCP server runtime tools such as `observe_camera_grounded_candidates` are
  enabled, so opt-in tools are marked as runtime extras rather than profile
  tools.
- MolmoSpaces and Agibot Agent View builders now pass MCP profile constants
  instead of duplicated string literals. Agibot paths that expose blocked
  manipulation tools include the manipulation profile so blocked tool details
  resolve to profile metadata.
- The Agibot SDK runner wrapper now converts the SDK-local Agent View export
  into the Roboclaws-owned `agent_view_v2` artifact, keeps
  `vendor_agent_view.json` for subsequent vendor CLI stages, and embeds the v2
  artifact in `run_result.json` instead of an old-shape inline payload.
- Updated stale privacy proxy tests/checks that rejected public Agibot profile
  provenance as if it were private map-source truth; map-source and
  verification payloads remain forbidden.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_registered_tools_match_profile_public_surface \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_agent_sdk_camera_grounded_composite_tool_is_opt_in \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_physical_agibot_pilot_uses_sdk_runner_reports_without_movement \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py::test_molmospaces_agibot_contract_rehearsal_writes_simulated_report \
  tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates
```

Result: passed.

Additional proof:

```bash
ruff check roboclaws/household/agent_view.py \
  roboclaws/household/realworld_contract_payloads.py \
  roboclaws/household/agibot_cleanup_contract.py \
  roboclaws/household/agibot_map_build_mcp_server.py \
  roboclaws/household/agibot_contract_rehearsal.py \
  roboclaws/household/agibot_sdk_runner.py \
  scripts/molmo_cleanup/realworld_agibot_map_build_checker.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py

ruff format --check roboclaws/household/agent_view.py \
  roboclaws/household/realworld_contract_payloads.py \
  roboclaws/household/agibot_cleanup_contract.py \
  roboclaws/household/agibot_map_build_mcp_server.py \
  roboclaws/household/agibot_contract_rehearsal.py \
  roboclaws/household/agibot_sdk_runner.py \
  scripts/molmo_cleanup/realworld_agibot_map_build_checker.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py

python -m py_compile vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py
git diff --check
```

Result: passed.

### Slice 5: Eval-Harness Hook, Not Redesign

- Add an Agent View focused deterministic gate if the existing focused tests are
  too scattered to catch private leakage/provenance drift.
- Keep this hook narrow: focused deterministic Agent View gate coverage only.
  The new module path signal belongs in Slice 2 so selector coverage exists as
  soon as the new path exists. Do not add `evolution_target`,
  capability-slice grouping, or a row taxonomy redesign in this plan.
- Do not reorganize the whole row taxonomy in this plan.

Acceptance:

- `just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
  selects deterministic Agent View / MCP / perception relevant rows.
- Changes to `roboclaws/household/agent_view.py`,
  `realworld_agent_view_contract.py`, `realworld_contract_payloads.py`, or
  `agibot_cleanup_contract.py` select the same Agent View contract gate.
- `execute budget=focused` either runs focused deterministic gates or records
  explicit blocked evidence for environment/provider-only rows.
- No new provider matrix is introduced by this refactor.
- No `evolution_target` or capability-slice eval grouping field is introduced
  by this refactor.

#### Slice 5 Implementation Evidence

Status: complete for narrow eval-harness Agent View gate coverage.

Implementation notes:

- Added `agent-view-contract-tests` as a focused deterministic eval-harness row.
  The row reuses existing Agent View artifact, MCP/profile, active-perception,
  visual-grounding request, and Agibot export tests instead of adding a new
  row taxonomy.
- Kept the existing `agent_view_module` path/text signal narrow and wired it to
  the new deterministic gate, cleanup contract tests, and one direct
  world-public product row.
- Added selector coverage proving changes to
  `roboclaws/household/agent_view.py`,
  `roboclaws/household/realworld_agent_view_contract.py`,
  `roboclaws/household/realworld_contract_payloads.py`, and
  `roboclaws/household/agibot_cleanup_contract.py` select the same Agent View
  gate.
- Corrected the current real-robot alignment checker/report readiness proof to
  require `real_robot_readiness.public_static_map=true` and
  `static_fixture_projection=false`, matching the new Agent View boundary. The
  direct product row first exposed the stale assertion that still required the
  historical Agent View static fixture projection.
- No provider matrix, `evolution_target`, or capability-slice grouping fields
  were added.

Proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/unit/evals/test_eval_harness_selector.py
```

Result: passed.

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_agent_view_payload_keeps_private_evaluation_out \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_raw_fpv_mode_suppresses_structured_detections \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_model_policy_registers_model_labelled_candidates \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_model_policy_records_sim_pipeline_provenance \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_http_failure_is_visible_without_sim_fallback \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_missing_raw_image_fails_before_sidecar \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py::test_realworld_camera_labels_http_success_uses_destination_resolver \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_registered_tools_match_profile_public_surface \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_agent_sdk_camera_grounded_composite_tool_is_opt_in \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py::test_realworld_mcp_rejects_removed_static_fixture_projection_tool \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_static_fixture_projection_field \
  tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_private_public_map_hints \
  tests/unit/molmo_cleanup/test_visual_grounding.py::test_visual_grounding_request_rejects_private_hint_keys \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding \
  tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates
```

Result: passed.

```bash
just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

Result: wrote `output/eval-harness/20260622T185007Z/eval_harness.json`.
The recommendation selects `agent-view-contract-tests` as a required
deterministic row for the `agent_view_module` signal.

```bash
just agent::eval execute changed_file=roboclaws/household/agent_view.py budget=focused
```

Result: passed after the readiness checker fix. The narrowed manifest
`output/eval-harness/20260622T185559Z/eval_harness.json` selected three rows:
`cleanup-contract-tests`, `agent-view-contract-tests`, and
`household-direct-world-public-product`; all three ran and passed.

## Non-Goals

- Do not delete active evidence lanes.
- Do not remove DINO, RAW-FPV, OpenAI Agents SDK, Codex CLI, Claude Code, or
  provider profiles just because the surface is broad.
- Do not redesign eval-harness row taxonomy in this plan.
- Do not add the eval `evolution_target` field in this plan; park it as the
  immediate follow-up after Agent View exists as a target.
- Do not change public `just run::surface` grammar.
- Do not introduce a new robotics backend or simulator.
- Do not rely on private scorer truth, hidden relocation data, static movable
  object inventory, or report-only camera views as agent inputs.
- Do not add compatibility wrappers for obsolete task/profile names.

## Verification Plan

Start with eval-harness:

```bash
just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

The recommendation pass is discovery evidence, not an instruction to run every
selected row for every slice. On 2026-06-22, this plan selected 19 focused rows
because the plan intentionally mentions eval harness, cleanup, open-ended,
MCP/checker, DINO, RAW-FPV, map-build, launch catalog, Codex, and Agent SDK.
That is expected for the whole refactor, but the first execution slice should
copy the relevant narrow subset into its preflight instead of claiming the full
matrix as required DoD.

Run full focused execution only after the slice owner has narrowed the row set
or explicitly accepts the cost/provider/runtime implications:

```bash
just agent::eval execute plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused
```

Focused deterministic checks expected to be relevant:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/unit/evals/test_eval_harness_selector.py
```

Static checks:

```bash
ruff check roboclaws/household roboclaws/mcp skills/eval-harness tests
ruff format --check roboclaws/household roboclaws/mcp skills/eval-harness tests
git diff --check
rg -n "hidden|relocation|private|scorer|static_fixture_projection" \
  roboclaws/household tests docs/plans/2026-06-22-agent-view-module-refactor.md
```

When Slice 2 changes the artifact layout, add an explicit schema/version check
for `agent_view.json` and at least one guard test that exercises an
agent-facing MCP/tool response, not only the report artifact. When Slice 3
touches visual grounding, add or update a sidecar-request test proving its
input is built from public Agent View evidence rather than private setup or
scorer truth.

Optional local/live proof only after deterministic gates:

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=cleanup agent_engine=direct-runner evidence_lane=world-public-labels

just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco \
  preset=map-build agent_engine=direct-runner \
  evidence_lane=camera-grounded-labels camera_labeler=grounding-dino
```

Live coding-agent or Agent SDK evals remain opt-in and provider/environment
dependent. They should be selected through eval-harness and recorded as run,
blocked, or skipped by budget; do not claim live proof from deterministic tests.

## Risks And Stop Gates

- **Scope creep into eval redesign:** stop if implementation starts reshaping
  eval-harness taxonomy beyond path selection or a focused Agent View gate.
- **Scope creep into server behavior:** stop if MCP server or runtime adapter
  code starts owning cleanup/search/map-build strategy.
- **Private truth leakage:** stop if a desired report field cannot be included
  without exposing private scorer/setup truth to Agent View.
- **Tool-response leak:** stop if a live MCP/tool response can expose a field
  that would be forbidden in `agent_view.json`.
- **Sidecar oracle leak:** stop if a detector or visual-grounding sidecar needs
  private scorer truth, hidden setup state, simulator-only fixture oracles, or
  report-only views to operate.
- **Unversioned artifact break:** stop if `agent_view.json` field layout changes
  without an explicit schema/version marker and migrated in-repo consumers.
- **Public command churn:** stop if a slice requires changing
  `just run::surface` grammar; that needs a separate plan/ADR.
- **Live provider dependency:** stop before requiring paid/live provider
  success for the deterministic refactor definition of done.
- **Eval-harness over-selection:** stop before treating all rows selected by
  the whole-plan `recommend` pass as mandatory for a small slice. Narrow the
  execution preflight to the changed files and accepted slice.
- **Mixed dirty worktree:** stop before staging or committing unrelated files.

## Follow-Up Sequence

1. **Eval-To-Evolution Feedback Module:** add `evolution_target` to eval result
   and harness summaries after `agent_view_module` exists as a stable target.
2. **Capability-Slice Eval Groups:** add lightweight capability-slice metadata
   to eval-harness rows only after the Agent View and evolution-target
   contracts exist.
3. **Surface stripping:** remove or retire surfaces only when eval evidence and
   architecture docs show they no longer serve open-ended robot agency or
   eval-driven evolution.

## Open Questions

1. Should the module file be named `agent_view.py`, or should
   `realworld_agent_view_contract.py` become the canonical owner to minimize
   churn? Proposed default: create `agent_view.py` as the canonical public
   module and move existing helper behavior there, leaving no new parallel
   concept.
2. Which current `agent_view_payload` fields are contractual versus historical
   report compatibility? Decision: no backward-compatibility burden for
   historical Agent View fields during a forward architecture upgrade. Slice 1
   should classify them so known consumers can migrate or delete their old
   assumptions.
3. Should the new top-level Agent View sections be additive in
   `agent_view.json`, or should existing top-level keys be migrated into
   sections in one breaking artifact-schema change? Decision: migrate known
   consumers to the new schema instead of preserving old keys for compatibility.
   Keep the artifact name stable, but do not keep old field layout solely for
   backward compatibility.
4. What is the minimum focused test set that proves Agent View without running
   the whole household suite? Proposed default: add one focused Agent View
   contract test module and keep the existing MCP/profile/perception focused
   tests as support.
5. Should Agibot use the same builder immediately or only the same validation
   and labels? Decision: Agent View covers Agibot as part of the
   household-world contract. Share guard/schema/provenance/blocked-capability
   vocabulary immediately; migrate the full builder only in a later slice if it
   does not pull Agibot-specific backend logic into the household realworld
   path.
6. Should Slice 1 start code movement? Decision: no. Slice 1 is ADR plus
   interface inventory only; builder migration, artifact-consumer migration,
   and module renames start in later slices.
7. Does the eval-harness selector hook belong in this plan? Decision: yes, but
   narrowly. It may add Agent View path signals and a focused deterministic
   gate; it must not add `evolution_target`, capability-slice grouping, or a
   provider-matrix redesign.
8. Does Agent View guard only the saved artifact, or every live agent-facing
   robot input? Decision: every live agent-facing robot input. MCP tool
   responses, `done` blockers, visual candidate responses, and sidecar evidence
   returned to the agent must be Agent View-owned, Agent View-derived, or
   explicitly blocked/provenance-limited.
9. May active-perception sidecars consume richer private/simulator context than
   the acting agent? Decision: no by default. Sidecar inputs must be assembled
   from public Agent View evidence, Base Navigation Map, Runtime Metric Map,
   public fixture hints, or current camera evidence; private scorer/setup truth
   and simulator-only oracles remain excluded.
10. Does breaking `agent_view.json` field layout require an explicit schema or
    version marker? Decision: yes. Keep the artifact name stable, but add a
    visible schema/version marker and migrate in-repo consumers rather than
    keeping compatibility shims.
11. Should eval-harness path selection wait until Slice 5? Decision: no. The
    new Agent View module path signal belongs in Slice 2 so diff-based
    `recommend` recognizes the boundary immediately; Slice 5 keeps the broader
    focused deterministic gate work.

## Reduce-Entropy Loop Notes

Selected mode: plan entropy mode.

Why: this is a new architecture refactor plan that needed missing decisions,
weak assumptions, and proof gaps found before preflight or execution.

Redirect: none.

Discovery intensity: saturation scan.

Demand sanity gate: passed. Candidate 1 deserves a new plan and ADR because the
current repo already has broad live-agent, Agent SDK, direct-runner,
perception, map, and eval surfaces; the surprise is not breadth, but the lack
of one explicit Agent View boundary for real-robot-obtainable inputs.

Round 1 findings resolved in this plan:

- Agibot has a separate `agent_view_payload`, so the plan now requires both
  MolmoSpaces/realworld and Agibot Agent View producers to share the same
  guard/schema vocabulary.
- The current branch has `select_eval_harness.py` and `eval_harness_rows.py`,
  not the JSON row catalog or ADR-0145 from another branch; the plan now treats
  those as absent.
- The future `roboclaws/household/agent_view.py` path is not an explicit
  eval-harness signal today; Slice 5 now requires a focused selector hook.

Round 2 findings resolved in this plan:

- New structured Agent View sections are a forward architecture upgrade. Known
  in-repo consumers should migrate to the new schema; old top-level keys should
  not be retained solely for compatibility.
- `static_fixture_projection` should not remain as an Agent View compatibility
  surface. If a report or map path still needs it, that use should be explicit
  outside the agent-facing contract.

Round 3 findings resolved in this plan:

- `just agent::eval recommend ... budget=focused` currently selects 19 rows for
  the whole plan. This is useful discovery evidence but too broad for a first
  implementation slice. The verification plan now requires slice-level
  narrowing before `execute`.

Round 4 findings resolved in this plan:

- Agent View is a shared household-world contract, including the Agibot path.
  Backend-local payload construction may remain only behind shared schema,
  guard, provenance, and blocked-capability vocabulary.
- Slice 1 is intentionally ADR plus interface inventory. It should not perform
  builder migration, artifact-consumer migration, or module renames.
- The eval-harness work in this plan is narrowly limited to Agent View path
  selection and focused deterministic gate coverage. `evolution_target` and
  capability-slice grouping remain follow-ups.

Round 5 findings resolved in this plan:

- Agent View enforcement covers live agent-facing MCP/tool responses and
  readiness blockers, not only the saved `agent_view.json` artifact.
- Active-perception sidecar inputs are part of the public-evidence boundary;
  DINO, RAW-FPV, and visual-grounding requests must not depend on private
  scorer/setup truth or simulator-only fixture oracles.
- A breaking `agent_view.json` layout change needs an explicit schema/version
  marker while still avoiding backward-compatibility shims.
- Eval-harness path selection for the new Agent View module moves to Slice 2 so
  selector coverage exists as soon as the module path exists; Slice 5 keeps only
  focused deterministic gate coverage.

Parked observations:

- Eval `evolution_target` belongs to the Candidate 2 follow-up after this plan
  creates `agent_view_module` as a stable target.
- Capability-slice eval grouping belongs to later row metadata, not this
  refactor.
- Surface stripping should wait for eval and architecture evidence that a route
  no longer serves open-ended robot agency or eval-driven evolution.

Saturation status: saturated for plan entropy. No remaining P0/P1 plan gap was
found after Agibot ownership, eval-harness path selection, artifact-schema
versioning, live tool-response coverage, sidecar-input boundaries, and
whole-plan row over-selection were made explicit.

The next workflow should check:

- scope leaks between C1, C2, C3, and C4;
- implementation flow for the full refactor, not Slice 1 only;
- ADR naming and numbering;
- exact field-inventory format;
- focused proof commands for the affected slices.

## Preflight Contract

Preflight status: DRAFT

Task source: plan + user prompt

Canonical source: `docs/plans/2026-06-22-agent-view-module-refactor.md`

Route: durable `$intuitive-flow`

Goal: Implement the full Agent View Module refactor, not just Slice 1, while
preserving the real-robot-obtainable public/private boundary.

Scope:

- Create ADR for Agent View as household-world module boundary.
- Inventory and migrate agent-facing artifacts, MCP/tool responses, `done`
  blockers, sidecar inputs, and Agibot/Molmo producers.
- Add canonical Agent View builder or owner module, explicit `agent_view`
  schema/version marker, shared private-key/provenance guards, and migrated
  in-repo consumers.
- Bring RAW-FPV, camera-grounded labels, visual-grounding sidecar state,
  uncertainty, and candidate lifecycle under Agent View active perception.
- Derive capability/blocked-capability metadata from MCP profiles.
- Add eval-harness Agent View path signal and focused deterministic gate
  coverage.

Non-goals:

- No `evolution_target` implementation.
- No capability-slice eval grouping.
- No provider matrix redesign.
- No public `just run::surface` grammar change.
- No backward-compatible shims for old Agent View field layout unless
  explicitly requested.

Entity budget:

- reuse: `realworld_agent_view_contract.py`,
  `realworld_contract_payloads.py`, `agibot_cleanup_contract.py`, MCP profiles,
  eval-harness scripts.
- remove/merge: duplicate Agent View semantics and stale compatibility
  assumptions.
- new: `roboclaws/household/agent_view.py` only if clearer than renaming the
  existing owner, plus ADR and focused tests.
- expansion triggers: public command changes, live-provider matrix changes, or
  compatibility bridge.

Context:

- must-read: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`, this plan, `CONTEXT.md`, `docs/human/domain.md`,
  `docs/human/mcp-skills-and-semantic-profiles.md`.
- useful: `output/eval-harness/20260622T091939Z/eval_harness.md` when present.
- avoid-unless-needed: historical plans and retrospectives.

Acceptance:

- SUCCESS: Agent View is a single enforced boundary for saved artifacts and
  live agent-facing responses; private truth fails loudly; `agent_view.json` has
  explicit schema/version; Molmo and Agibot paths share guards/vocabulary;
  sidecar inputs are public-evidence only; eval-harness selects Agent View
  gates.
- BLOCKED_NEEDS_DECISION: none.
- BLOCKED_NEEDS_LOCAL_VALIDATION: live Codex / Claude Code / OpenAI Agents SDK
  proof unavailable or provider/Docker/network blocked.
- INTERMEDIATE_ONLY: none unless the human approves a checkpoint.
- No regressions: existing household cleanup, map-build, RAW-FPV,
  visual-grounding, MCP/profile, eval-harness, and open-ended contract tests
  pass or are intentionally migrated.

Verification:

- deterministic:
  - `ruff check roboclaws/household roboclaws/mcp skills/eval-harness tests`
  - `ruff format --check roboclaws/household roboclaws/mcp skills/eval-harness tests`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/molmo_cleanup/test_molmo_realworld_contract.py tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py tests/contract/mcp/test_semantic_profiles.py tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py tests/unit/molmo_cleanup/test_visual_grounding.py tests/unit/evals/test_eval_harness_selector.py`
- integration:
  - `just agent::eval recommend plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
  - narrowed `just agent::eval execute plan=docs/plans/2026-06-22-agent-view-module-refactor.md budget=focused`
- product-run: direct cleanup world-public, direct map-build Grounding-DINO,
  direct RAW-FPV cleanup, runtime-prior cleanup consumer as selected by
  eval-harness.
- local-live-manual: Codex CLI, Claude Code, and OpenAI Agents SDK live rows if
  provider/Docker/network gates are available; otherwise record blocked
  evidence.
- optional: full focused matrix after deterministic and product gates are green.

Execution:

- main: root supervisor owns flow state, commits, gate judgment.
- worker: optional scoped workers for inventory or test migration only.
- worker-goal: bounded file inventory or focused test update, no independent
  architecture decisions.

To execute:

```text
/goal execute docs/plans/2026-06-22-agent-view-module-refactor.md with intuitive-flow
```

Optional tracking: none

Approval: `LGTM`, `approve`, or `go ahead` approves; edits request revision.

## Current Recommendation

Proceed to `$intuitive-flow` for the full Agent View Module refactor using the
preflight contract above.

## Implementation Closeout

Status: implemented on 2026-06-23.

Final result:

- Agent View is now a sectioned v2 household-world boundary owned by
  `roboclaws/household/agent_view.py`.
- MolmoSpaces, Agibot cleanup, Agibot map-build MCP, the Roboclaws Agibot SDK
  wrapper, report, checker, probe, visual-grounding, and focused test consumers
  use the v2 Agent View schema/accessors for current saved artifacts and live
  agent-facing payloads. The vendor Agibot SDK runner remains SDK-local and is
  consumed through the wrapper boundary.
- Active perception, visual-grounding sidecar requests, and capability metadata
  are Agent View-owned or Agent View-derived without private scorer/setup truth.
- Eval-harness has a narrow `agent-view-contract-tests` deterministic gate for
  the `agent_view_module` signal.
- `ARCHITECTURE.md` names the canonical Agent View module and the current
  `agent_view_v2` artifact sections.

Final proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/mcp/test_semantic_profiles.py \
  tests/unit/molmo_cleanup/test_raw_fpv_perception_probe.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  tests/unit/evals/test_eval_harness_selector.py

./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  -k 'agent_view or real_robot_alignment or runtime_metric_map or raw_fpv or camera_model_policy or static_fixture_projection or base_navigation_map' \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py::test_vendor_sdk_runner_exports_base_navigation_context_generated_candidates \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py::test_agibot_map_build_camera_labels_call_external_grounding \
  tests/contract/visual_grounding/test_visual_grounding_service.py

just agent::eval execute changed_file=roboclaws/household/agent_view.py budget=focused

ruff check roboclaws/household roboclaws/mcp skills/eval-harness tests scripts/molmo_cleanup scripts/visual_grounding

ruff format --check roboclaws/household roboclaws/mcp \
  skills/eval-harness/scripts/eval_harness_rows.py \
  skills/eval-harness/scripts/select_eval_harness.py \
  tests/contract/agibot/test_agibot_map_context_scripts.py \
  tests/contract/checkers/test_check_molmo_realworld_cleanup_result.py \
  tests/contract/checkers/test_realworld_base_navigation_map_checker.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_contract.py \
  tests/contract/molmo_cleanup/test_molmo_realworld_mcp_server.py \
  tests/contract/molmo_cleanup/test_molmospaces_agibot_contract_rehearsal.py \
  tests/contract/molmo_cleanup/test_physical_agibot_pilot.py \
  tests/contract/visual_grounding/test_visual_grounding_service.py \
  tests/unit/evals/test_eval_harness_selector.py \
  tests/unit/molmo_cleanup/test_visual_grounding.py \
  scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
  scripts/molmo_cleanup/realworld_agent_view_checker.py \
  scripts/molmo_cleanup/realworld_agibot_map_build_checker.py \
  scripts/molmo_cleanup/realworld_base_navigation_map_checker.py \
  scripts/molmo_cleanup/realworld_waypoint_honesty_checker.py \
  scripts/molmo_cleanup/run_codex_cleanup_apple2apple_summary.py \
  scripts/molmo_cleanup/run_raw_fpv_perception_probe.py \
  scripts/molmo_cleanup/summarize_robot_camera_visual_parity.py \
  scripts/visual_grounding/adapters.py \
  scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py \
  scripts/visual_grounding/run_visual_grounding_benchmark.py

python -m py_compile vendors/agibot_sdk/tools/run_agibot_cleanup_backend.py
git diff --check
```

Result: passed.

Skipped or partial proof:

- Repo-wide `ruff format --check roboclaws/household roboclaws/mcp
  skills/eval-harness tests scripts/molmo_cleanup scripts/visual_grounding`
  found unrelated pre-existing format drift in
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `tests/unit/launch/test_environment_setup_catalog.py`, and
  `tests/unit/molmo_cleanup/test_ci_live_reports.py`. The owned changed scope
  format check passed.

Parked follow-ups:

- Add eval `evolution_target` after Agent View exists as a stable target.
- Add capability-slice eval grouping metadata after the Agent View and
  evolution-target contracts exist.
- Provider matrix changes and live-provider proof remain separate opt-in
  follow-ups.

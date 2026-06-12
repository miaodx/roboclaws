---
refactor_scope: coding-agent-provider-registry
status: READY_FOR_IMPLEMENTATION
accepted_severities:
  - P0
  - P1
  - P2
last_verified: null
---

# Refactor Scope: Coding-Agent Provider Registry

## Status

READY_FOR_IMPLEMENTATION

The grill pass is saturated: no decision-impact open questions remain before
implementation. This document is plan-first; do not implement it from the
planning turn alone.

## Target

Create one canonical provider/model registry for coding-agent and remaining
model-provider metadata. The registry should make it cheap to add GPT, Kimi,
MiMo, MiniMax, and future providers without editing scattered shell helpers,
operator-console gates, launch specs, docs, and tests by hand.

## Architecture Packet

Zoom-out map:

- Public launch axes choose `agent_engine`, `provider_profile`, optional
  model override, and `evidence_lane`.
- Coding-agent launchers translate those axes into provider env, base URL,
  wire API, default model, and runtime prompts.
- Operator console exposes the same choices and readiness messages.
- Reports and model-matrix docs record whether the route actually worked.

Accepted seam:

- `roboclaws/agents/provider_registry.py` is the canonical Python source for
  provider/model metadata.
- Shell helpers may mirror a subset only when covered by a consistency test.
- Household evidence-lane policy is declarative and separate from provider
  metadata.

Rejected alternatives:

- Do not keep adding provider-specific case branches across launch, shell,
  console, docs, and tests.
- Do not infer model family or modality from arbitrary string substrings.
- Do not treat "model supports images" as equivalent to "this runtime route can
  run raw FPV."

## Context

Current live experiments split model routes into two practical groups:

- Full-modal or vision-capable routes, such as GPT, Kimi, MiMo v2.5, and
  MiniMax M3. These are eligible for raw FPV style evidence only when the
  selected agent runtime can actually receive image input.
- Text or fast-agent routes, such as MiniMax highspeed and some MiMo Pro-style
  routes. These should be allowed on structured evidence lanes such as
  `world-oracle-labels`, `world-public-labels`, and `camera-grounded-labels`,
  but not on `camera-raw-fpv`.

MiMo has a special current limitation: MiMo TokenPlan exposes Chat-style routes,
but not native Responses for Codex. Codex + MiMo therefore goes through the
mify Responses-compatible gateway. Local evidence shows:

- Agent SDK + MiMo Chat can complete non-raw-FPV cleanup lanes.
- Codex + MiMo through mify can call MCP tools but early-stops after one
  live-agent turn in current probes.
- Codex + GPT 5.5 through `codex-env` completes the same lanes.

This is not enough reason to remove MiMo/mify from Codex. Until MiniMax or
another official Responses model is proven healthy in Codex, MiMo/mify remains
useful as a comparison route. It should be represented as supported but
provisional/degraded for Codex, not deleted.

## Terminology

Use these names consistently in implementation and docs:

- `provider_profile`: public launch/catalog value, kept for existing command
  grammar.
- `provider_route`: internal registry id for a key route plus transport, such
  as `codex-env`, `mify`, `minimax`, `mimo-openai-chat`, or
  `kimi-openai-chat`.
- `model_id`: concrete model string sent to the runtime, such as `gpt-5.5`,
  `xiaomi/mimo-v2.5-pro`, `MiniMax-M3`, or `MiniMax-M2.7-highspeed`.
- `model_family`: semantic family such as `gpt`, `mimo`, `minimax`, `kimi`,
  `nvidia`, `anthropic`, or `mock`.
- `model_capabilities`: model-level capability facts independent of provider
  route. First-slice values are `text` and `image_input`.
- `wire_api`: protocol shape: `responses`, `chat-completions`, or
  `anthropic`.
- `wire_source`: compatibility quality: `native`, `gateway`, `shim`, or
  `unknown`.
- `route_capabilities`: route plus agent-runtime transport facts that can vary
  by `provider_route` and `agent_engine`. First-slice keys are
  `image_transport` and `tool_call_transport`, with values `supported`,
  `unsupported`, or `unknown`.
- `agent_engine`: product runtime, such as `codex-cli`,
  `openai-agents-sdk`, or `claude-code`.
- `route_status`: health state for a provider route under one engine.
- `evidence_lane_requirement`: household lane-policy requirement matched
  against model, route, and runtime capabilities. It is not a model field.

Do not use `provider` ambiguously for vendor, route, and transport in new code.

## Route Health States

- `healthy`: verified for the advertised engine/lane class and acceptable as a
  default or comparison route.
- `experimental`: available but not enough live evidence for default
  recommendation.
- `provisional`: intentionally kept for comparison or investigation despite
  incomplete evidence.
- `degraded`: known issue exists, but the route remains useful for comparison
  or limited lanes.
- `blocked`: launch should be prevented until prerequisites change.

Starting classifications:

- `codex-cli` + `codex-env` + GPT 5.5: `healthy` for structured labels and
  camera-grounded labels based on current local cleanup evidence.
- `codex-cli` + `mify` + MiMo: `provisional` or `degraded` for Codex Responses
  completion reliability, but still supported as a comparison route.
- `openai-agents-sdk` + `mimo-openai-chat`: `healthy` or `experimental` for
  non-raw-FPV cleanup lanes, depending on model-matrix strictness.
- `codex-cli` + `minimax`: `experimental` until MiniMax Codex cleanup runs are
  reviewed.

## Evidence-Lane Requirement Matrix

The household lane policy should be declarative and separate from provider
metadata.

| Evidence lane | Agent-model image input required? | External/structured visual producer | Text-only model allowed? | Notes |
| --- | --- | --- | --- | --- |
| `world-oracle-labels` | No | Structured world labels | Yes | Best cheap text-model control lane. |
| `world-public-labels` | No | Sanitized public labels | Yes | Text model must resolve destinations from public policy. |
| `camera-grounded-labels` | No | Camera labeler such as sim labels or Grounding DINO | Yes | Agent consumes structured candidates; labeler owns visual proposal. |
| `camera-raw-fpv` | Yes | Agent model sees raw image evidence | No by default | Requires verified runtime image transport, not only model marketing capability. |

This matrix should be the source for gating, console disable reasons, and test
expectations.

## Registry Shape Sketch

The implementation can choose exact names, but the plan expects equivalent
data:

```python
ModelSpec(
    model_id="MiniMax-M3",
    aliases=("minimax-m3",),
    family="minimax",
    model_capabilities=frozenset({"text", "image_input"}),
)

ProviderRouteSpec(
    route_id="minimax",
    public_profile="minimax",
    label="MiniMax Responses",
    supported_engines=("codex-cli", "openai-agents-sdk"),
    default_model_id="MiniMax-M3",
    required_env_keys=("MM_API_KEY",),
    base_url_env="MM_BASE_URL",
    base_url_default="https://api.minimaxi.com/v1",
    wire_api="responses",
    wire_source="native",
    per_engine_status={"codex-cli": "experimental"},
    route_capabilities={
        "image_transport": "unknown",
        "tool_call_transport": "supported",
    },
    per_engine_route_capability_overrides={
        "codex-cli": {"image_transport": "unknown"},
    },
)

EvidenceLaneRequirement(
    lane_id="camera-raw-fpv",
    requires_agent_image_input=True,
    text_only_allowed=False,
)
```

Raw-FPV eligibility is not a `ModelSpec` field. It is derived from model
modality, provider route transport support, agent engine runtime support, and
optional live evidence verdicts.

## Resolved Decisions

- The canonical registry will live at
  `roboclaws/agents/provider_registry.py`.
- `roboclaws/core/provider_catalog.py` should be deleted after known in-repo
  callers and tests move to the new registry. Do not keep a compatibility
  re-export.
- `roboclaws/core/vlm.py` should not survive under that name. Delete it
  outright if remaining imports are provider tests / old factory coverage only,
  or split surviving generic primitives into neutral provider/runtime modules
  before deleting `vlm.py`.
- `mify` + MiMo remains an explicit Codex provider route. Mark it
  `provisional` or `degraded` for Codex Responses completion reliability, show
  that status in console/docs/report metadata, but do not block explicit runs.
- Raw FPV incompatibility is a hard launch gate for known text-only routes or
  routes with unknown image transport. Add a named experimental override only
  in a future plan if operators need to force a probe.
- Live route verdicts should be stored in
  `docs/human/model-route-verdicts.yaml`, with human narrative continuing in
  `docs/human/model-matrix.md`.
- Route health is keyed by `agent_engine + provider_route + model_id`, with
  optional lane-level verdicts when evidence differs by evidence lane.
- Protocol/source terms are metadata fields, not capability names.
- Evidence-lane compatibility is owned by the household lane policy; model and
  provider-route specs only expose the facts that policy consumes.

## Accepted Severities

- P0: A default route launches a provider/model with missing required key or
  wrong wire API.
- P1: A model capability mismatch lets text-only routes claim raw-FPV support,
  or hides a provider compatibility risk such as MiMo/mify Responses.
- P1: Two current sources of truth disagree about default model, required env
  keys, supported engines, or supported wire API.
- P2: Adding a new provider requires coordinated edits in multiple unrelated
  modules, docs, tests, and UI surfaces.

## Accepted Cleanup Checklist

- [ ] Add a canonical Python registry for coding-agent provider profiles and
  model metadata.
- [ ] Remove string-inference traps, including `_model_family()` substring
  matching and raw-FPV eligibility from model id alone.
- [ ] Keep MiMo/mify as a Codex provider, with provisional/degraded status.
- [ ] Add MiniMax profiles without multiplying provider-specific branches.
- [ ] Merge and delete `roboclaws/core/provider_catalog.py` with no shim.
- [ ] Retire the stale `roboclaws/core/vlm.py` boundary with no shim.
- [ ] Migrate Python consumers to the registry:
  `roboclaws/launch/agent_engines.py`,
  `roboclaws/operator_console/launcher.py`,
  `roboclaws/operator_console/routes.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `scripts/molmo_cleanup/run_live_codex_cleanup.py`, and any surviving neutral
  provider/runtime module split out of `core/vlm.py`.
- [ ] Keep `scripts/dev/coding_agent_env.sh` thin and consistency-tested.
- [ ] Add capability-aware household lane gating.
- [ ] Add `docs/human/model-route-verdicts.yaml`.
- [ ] Add registry consistency tests.
- [ ] Update operator console metadata flow.
- [ ] Update docs and tests after the registry shape is accepted:
  `just/README.md`, `docs/human/coding-agent-nav-server.md`,
  `docs/human/model-matrix.md`, `.env.example`, and
  provider/launch/operator-console tests.

## Parked Cross-Seam / Future Ideas

- Do not change the default Codex provider away from `codex-env`.
- Do not make MiniMax the preferred comparison route until its live Codex
  cleanup results are reviewed.
- Do not remove MiMo/mify from Codex merely because current mify Responses
  probes are weak; downgrade only after an official-Responses control model
  clearly works better.
- Do not run paid/live provider gates as part of implementation unless
  explicitly authorized.
- Do not preserve old provider catalog or `core.vlm` import paths once known
  in-repo callers are migrated.

## Grill Saturation Audit

No decision-impact open questions remain before implementation.

Already decided:

- The canonical registry path, old-catalog deletion policy, stale `core/vlm.py`
  retirement, and no-compat-shim stance are fixed.
- MiMo/mify remains an explicit Codex route, but carries provisional/degraded
  status until Responses completion reliability improves.
- Text-only and unknown-image-transport routes are hard-blocked from raw-FPV.
- Live route verdicts go to `docs/human/model-route-verdicts.yaml` while
  `docs/human/model-matrix.md` remains the human narrative.
- Capability vocabulary is split into model capabilities, wire metadata, and
  route/runtime transport capabilities.
- Evidence-lane compatibility is a household lane-policy decision, not a model
  metadata field.

Remaining implementation-local choices:

- Exact helper/function names inside `roboclaws/agents/provider_registry.py`.
- Whether the lane policy helper physically lives under `roboclaws/household`
  or a launch-facing household module.
- Whether to rename existing provider tests in one move or add new registry
  tests first and remove old catalog tests with the module deletion.
- Exact neutral module names for any surviving generic provider primitives
  split out of `roboclaws/core/vlm.py`.

## Preflight Contract

Preflight status: DRAFT

Task source: `docs/plans/refactor-coding-agent-provider-registry.md` plus the
2026-06-12 grill discussion.

Canonical source: `docs/plans/refactor-coding-agent-provider-registry.md`

Route: durable `$intuitive-flow`, with refactor-shaped execution discipline.

Goal: implement one canonical provider/model registry for coding-agent routes,
remove stale provider metadata sources, and make route/lane capability gates
explicit without changing the public launch grammar.

Scope:

- Add `roboclaws/agents/provider_registry.py` with typed model, provider-route,
  route-status, wire, and capability metadata.
- Migrate launch, operator-console, live Codex, OpenAI Agents SDK, shell-helper
  consistency, docs, and tests to registry facts.
- Delete `roboclaws/core/provider_catalog.py` with no compatibility shim.
- Retire `roboclaws/core/vlm.py`: delete it outright, or split surviving
  generic provider primitives into neutral modules and remove all
  `roboclaws.core.vlm` imports.
- Preserve explicit Codex `mify` support, mark MiMo/mify provisional/degraded,
  and add MiniMax route metadata without provider-specific branch sprawl.
- Add household lane-policy gating so raw-FPV requires model `image_input` plus
  route/engine `image_transport=supported`; structured-label lanes remain
  usable by text-only routes.
- Add `docs/human/model-route-verdicts.yaml` and update human docs manually.

Non-goals:

- Do not change the default Codex provider away from `codex-env`.
- Do not remove explicit `provider_profile=mify` from Codex.
- Do not make MiniMax the preferred comparison route until live Codex evidence
  is reviewed.
- Do not generate `docs/human/model-matrix.md` from YAML in this slice.
- Do not introduce a compatibility re-export for deleted catalog or `core.vlm`
  modules.
- Do not claim live provider quality or speed improvements unless local/live
  provider gates actually pass.

Context:

- must-read: `README.md`, `ARCHITECTURE.md`, `STATUS.md`, `AGENTS.md`,
  `CLAUDE.md`, this plan, `docs/human/domain.md`,
  `docs/human/model-matrix.md`, `docs/human/coding-agent-nav-server.md`,
  `just/README.md`, `roboclaws/launch/agent_engines.py`,
  `roboclaws/operator_console/routes.py`,
  `roboclaws/operator_console/launcher.py`,
  `scripts/dev/coding_agent_env.sh`,
  `scripts/molmo_cleanup/run_live_codex_cleanup.py`,
  `scripts/molmo_cleanup/run_live_openai_agents_cleanup.py`,
  `roboclaws/core/provider_catalog.py`, and `roboclaws/core/vlm.py`.
- useful: `docs/plans/refactor-retire-ai2thor-vlm-direct.md`,
  `tests/unit/launch/test_environment_setup_catalog.py`,
  `tests/unit/operator_console/test_launcher.py`,
  `tests/unit/operator_console/test_routes.py`,
  `tests/unit/scripts/test_network_status_guard.py`, and
  `tests/unit/agents/test_live_runtime.py`.
- avoid-unless-needed: historical `docs/ai/**`, `docs/research-checkpoints/**`,
  archived AI2-THOR/direct-VLM execution logs, and `output/**` artifacts not
  linked from current route-verdict evidence.

Acceptance:

- SUCCESS: one canonical registry owns provider/model facts; old catalog and
  `roboclaws.core.vlm` imports are gone; shell/UI/docs align with registry or
  are consistency-tested; MiMo/mify remains explicit but visibly
  provisional/degraded; MiniMax routes are represented; raw-FPV gating blocks
  text-only and unknown-image-transport routes; route verdict YAML exists; L0,
  L1, L2, and the focused agent-validation product matrix pass or record only
  explicitly accepted local/live skips.
- BLOCKED_NEEDS_DECISION: active non-test code depends on a `core.vlm` behavior
  that cannot be moved under a neutral provider/runtime name without choosing a
  new public boundary, or route metadata conflicts with a current public launch
  contract.
- BLOCKED_NEEDS_LOCAL_VALIDATION: deterministic gates pass but required
  provider-backed, Docker-backed, simulator-backed, or operator-console proof
  cannot run in the current environment; do not claim live route health.
- INTERMEDIATE_ONLY: registry exists but old catalog/`core.vlm` imports remain,
  shell facts are unchecked, or lane gating/report metadata is not wired.
- No regressions: existing `codex-env`, explicit `mify`, `minimax`,
  `mimo-openai-chat`, `kimi-openai-chat`, and Claude provider-profile behavior
  remains launchable where currently supported; world-label and camera-grounded
  lanes still allow text-only models; raw-FPV remains blocked for unsupported
  routes.

Verification:

- deterministic:
  `rg -n "provider_catalog|CODEX_PROVIDER_DEFAULT_MODELS|OPENAI_AGENTS_PROVIDER_DEFAULT_MODELS|CLAUDE_PROVIDER_DEFAULT_MODELS" roboclaws scripts tests`;
  `rg -n "roboclaws\\.core\\.vlm|from roboclaws\\.core\\.vlm|core/vlm.py" roboclaws scripts tests docs`;
  `rg -n "_model_family\\(|\"mify\".*\"mimo\"|raw_fpv_eligible|route_status" roboclaws scripts tests`;
  `test -f docs/human/model-route-verdicts.yaml`;
  `bash -n scripts/dev/coding_agent_env.sh`;
  `ruff check .`; `ruff format --check .`.
- integration:
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_provider_registry.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_environment_setup_catalog.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_routes.py tests/unit/operator_console/test_static_assets.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/scripts/test_network_status_guard.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_live_runtime.py tests/unit/agents/test_openai_agents_minimax_provider.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/unit/providers/test_provider_retry.py tests/unit/providers/test_provider_safety.py`;
  `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py`.
- product-run:
  `just agent::harness agent-validation recommend plan=docs/plans/refactor-coding-agent-provider-registry.md budget=focused`;
  `just agent::harness agent-validation execute plan=docs/plans/refactor-coding-agent-provider-registry.md budget=focused`.
- local-live-manual:
  before live/provider gates run `just dev::network-status`; if credentials,
  Docker, simulator, and policy allow it, run at least one public Codex cleanup
  route through `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels seed=7 scenario_setup=relocate-cleanup-related-objects relocation_count=5`;
  run extra `mify`, `minimax`, camera-grounded, or raw-FPV gates only when
  explicitly validating live route health or image transport.
- optional: operator-console browser smoke after `just console::run`; live
  MiniMax/MiMo/GPT comparison reruns; raw-FPV image-transport probes for a
  vision-capable model.

Execution: main=root supervisor owns scope, validation judgment, and dirty-tree
protection; worker=none by default, use a `skill-runner` worker only if the
implementation becomes long-running or needs isolated post-run artifacts;
worker-goal=none unless execution is delegated.

To execute:

```text
/goal execute docs/plans/refactor-coding-agent-provider-registry.md with intuitive-flow
```

Approval: `LGTM`, `approve`, `go ahead`, or `do this` approves this preflight;
edits request revision before implementation.

## Evidence Ladder

- L0 static:
  - `rg -n "provider_catalog|CODEX_PROVIDER_DEFAULT_MODELS|OPENAI_AGENTS_PROVIDER_DEFAULT_MODELS|CLAUDE_PROVIDER_DEFAULT_MODELS" roboclaws scripts tests`
  - `rg -n "roboclaws\\.core\\.vlm|from roboclaws\\.core\\.vlm|core/vlm.py" roboclaws scripts tests docs`
  - `rg -n "_model_family\\(|\"mify\".*\"mimo\"|raw_fpv_eligible|route_status" roboclaws scripts tests`
  - `test -f docs/human/model-route-verdicts.yaml`
  - `ruff check` and `ruff format --check` on touched Python files.
  - `bash -n scripts/dev/coding_agent_env.sh`
- L1 unit:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/agents/test_provider_registry.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/launch/test_environment_setup_catalog.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/operator_console/test_launcher.py tests/unit/operator_console/test_routes.py tests/unit/operator_console/test_static_assets.py`
  - `./scripts/dev/run_pytest_standalone.sh -q tests/unit/scripts/test_network_status_guard.py`
- L2 contract:
  - `./scripts/dev/run_pytest_standalone.sh -q tests/contract/dev_tools/test_code_just_recipes.py tests/contract/dev_tools/test_task_agent_just_recipes.py`
- L5 local provider:
  - Optional after implementation: one Codex provider smoke per official
    Responses provider selected for validation.
- L6 live harness:
  - Optional after implementation: one cleanup lane per capability class:
    structured text lane, camera-grounded lane, and raw-FPV lane for an
    image-capable model.

## Stop Condition

Stop when provider/model metadata has one canonical Python source, known
in-repo callers no longer import the old catalog or `roboclaws.core.vlm`,
shell/UI/docs are aligned with the registry or covered by a
registry-consistency test, `docs/human/model-route-verdicts.yaml` records the
current live-route verdicts needed for route status, and L0-L2 evidence passes.
Live MiniMax/MiMo/GPT validation can remain a separate evidence task and must be
recorded as skipped or linked if not run.

## Execution Log

- 2026-06-12: Plan recreated after the untracked draft disappeared from the
  worktree. No implementation changes are authorized yet.
- 2026-06-12: Grill batch accepted the registry location, deletion of the old
  catalog instead of a shim, explicit-but-degraded MiMo/mify Codex support,
  hard raw-FPV gating for non-image/unknown-transport routes, YAML live-route
  verdict index, and per engine+route+model health keys.
- 2026-06-12: Final grill saturation pass closed the remaining implementation
  boundary defaults: capability vocabulary layering, separate household lane
  policy ownership, MiniMax M3 raw-FPV gating via `image_transport=unknown`,
  and no first-slice model-matrix generation.
- 2026-06-12: Follow-up audit corrected the `core/vlm.py` default. The file
  survived earlier direct-VLM retirement because it mixed generic provider
  helpers with old direct-VLM naming, but this provider-registry slice should
  delete it or split surviving primitives into neutral modules instead of
  keeping the stale boundary.
- 2026-06-12: Added intuitive-preflight execution contract.

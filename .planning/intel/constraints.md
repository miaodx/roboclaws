# Constraints

Synthesized from the two SPEC-classified docs (`docs/technical-design.md`,
`PLAN.md`) and reinforced by the Gateway internals DOC
(`docs/openclaw-gateway-internals.md`). Each constraint is load-bearing:
violating it breaks either the sim platform, the Gateway transport, or the
published demo matrix.

Grouped by type: platform-selection, api-contract, schema, nfr (non-functional
requirement), protocol.

---

## CONSTR-platform-ai2thor-ithor (platform-selection)

- source: docs/technical-design.md § Why AI2-THOR (Phase 1); § Scene Selection;
  docs/research/02-ai2thor-multiagent-foundations.md § ProcTHOR Multi-Agent Bug
- constraint: Use **iTHOR** scenes only (`FloorPlan1-30` kitchens, `201-230`
  living rooms, `301-330` bedrooms, `401-430` bathrooms). ProcTHOR multi-agent
  is buggy (AI2-THOR Issues #1169, #1265: `agentCount=2` returns only one
  event; controlling `agentId=1` throws TimeoutError. Both unresolved).
- recommendation for Phase 1: living rooms (`201-230`) — larger spaces for
  multi-agent movement.
- consequence: `MolmoSpaces` is excluded from Phase 1-2 even though it has
  230K+ scenes — zero multi-agent support.

## CONSTR-ai2thor-turn-based-stepping (api-contract)

- source: docs/technical-design.md § Control Model; § AI2-THOR key APIs in
  CLAUDE.md
- constraint: `controller.step(action=..., agentId=i)` moves **one agent per
  call**. Returned event contains all agents' independent state via
  `event.events[i]`. Game engine is turn-based — no native simultaneous
  actions. No built-in inter-agent communication (we implement it via shared
  game state). Agents physically collide (Unity physics, `lastActionSuccess`
  reports failure); agents are visible in each other's camera views.

## CONSTR-ai2thor-controller-init-shape (api-contract)

- source: docs/technical-design.md § Initialization
- constraint: Canonical multi-agent init must supply `agentCount=N`,
  `gridSize` (default 0.25), `snapToGrid=True` (grid-based movement),
  `rotateStepDegrees` (default 90), `fieldOfView`, `width`, `height`. Grid
  mode is the default; continuous mode (`snapToGrid=False`) is supported for
  noise simulation but not used by territory/coverage games.
- example:
  ```python
  Controller(scene="FloorPlan201", agentCount=3, gridSize=0.25,
             snapToGrid=True, rotateStepDegrees=90, fieldOfView=90,
             width=640, height=480)
  ```

## CONSTR-ai2thor-per-agent-data-schema (schema)

- source: docs/technical-design.md § Per-Agent Data
- constraint: For every step, per-agent data available on `event.events[i]`:
  - `frame` — numpy `(H, W, 3)` RGB
  - `depth_frame` — float32 depth in meters
  - `metadata['agent']['position']` — `{x, y, z}`
  - `metadata['agent']['rotation']` — `{x, y, z}` Euler angles
  - `metadata['agent']['cameraHorizon']`
  - `metadata['objects']` — filter by `visible=True` for visible set
  - `metadata['lastActionSuccess']` — bool
  - `metadata['errorMessage']` — str

## CONSTR-ai2thor-overhead-camera (protocol)

- source: docs/technical-design.md § Overhead View
- constraint: Overhead view obtained via
  `controller.step(action="GetMapViewCameraProperties", raise_for_failure=True)`
  → deepcopy `event.metadata["actionReturn"]` → set `orthographic=True` →
  `controller.step(action="AddThirdPartyCamera", **pose, skyboxColor="white")`.
  Top-down frame then at
  `controller.last_event.events[0].third_party_camera_frames[-1]`.

## CONSTR-action-vocabulary (api-contract)

- source: docs/technical-design.md § Available Actions; VLM prompting contract
- constraint: VLM output `action` field must be one of
  `NAVIGATION_ACTIONS`: `MoveAhead`, `MoveBack`, `MoveLeft`, `MoveRight`,
  `RotateLeft`, `RotateRight`, `LookUp`, `LookDown`, `Teleport`, `Done`.
  Invalid actions are coerced to `MoveAhead` with a logged warning.
  Object-interaction actions (`PickupObject`, `PutObject`, `OpenObject`,
  `CloseObject`, `ToggleObjectOn/Off`) are **Phase 3**.

## CONSTR-vlm-io-json-contract (schema)

- source: docs/technical-design.md § VLM Strategy § Prompt Structure
- constraint: Per-step VLM reply must be JSON-parseable and match:
  ```json
  {"reasoning": "<free text>", "action": "<one of NAVIGATION_ACTIONS>"}
  ```
- prompt structure: system role describes competition/cooperation; user role
  includes (1) first-person camera frame (base64 JPEG), (2) overhead map
  marking self ★ and opponents ●, (3) structured state
  (position, rotation, score, remaining steps, last action + success, available
  actions). Code-fence wrappers in the reply are stripped.

## CONSTR-openclaw-gateway-transport (protocol)

- source: docs/retrospectives/phase-2.1.md § Problem Statement, § Revised
  Architecture; docs/openclaw-gateway-internals.md § Named-agent routing
- constraint: OpenClaw Gateway transport for roboclaws is the OpenAI-compatible
  `POST /v1/chat/completions`. Endpoint must be explicitly enabled via
  `gateway.http.endpoints.chatCompletions.enabled = true` (default: false);
  bootstrap sets this. Auth: `Authorization: Bearer <token>`;
  `Content-Type: application/json`.
- forbidden: `POST /tools/invoke` (dispatches only plugin-registered tools,
  not workspace skills; confirmed in
  `/app/dist/tools-invoke-http-*.js:135-145`).

## CONSTR-openclaw-named-agent-model-id (protocol)

- source: docs/retrospectives/phase-2.1.md § Why named agents;
  docs/openclaw-gateway-internals.md § Named-agent routing
- constraint: Chat completions request body must use
  `model = "openclaw/<agentId>"`. The Gateway rejects raw provider model IDs
  on this endpoint with `"Use openclaw or openclaw/<agentId>"`. `agentId`
  regex: `[a-z0-9][a-z0-9_-]{0,63}`.
- convention: agentId is the bootstrap-provided `<AGENT_PREFIX><i>`
  (default `agent-0`, `agent-1`, …). `OpenClawBridge.__init__` has
  `agent_prefix: str = "agent-"` — single source of truth with bootstrap.

## CONSTR-openclaw-per-agent-isolation (schema)

- source: docs/retrospectives/phase-2.1.md § Revised Architecture;
  docs/openclaw-gateway-internals.md § Per-agent workspace contents
- constraint: Each named agent must have:
  - workspace: `/home/node/.openclaw/workspaces/<agentId>/` containing
    `AGENTS.md`, `BOOTSTRAP.md`, `HEARTBEAT.md`, `IDENTITY.md`, `SOUL.md`,
    `TOOLS.md`, `USER.md`, `skills/` (bind-mounted), `state/` (MEMORY lives
    here).
  - agent dir: `/home/node/.openclaw/agents/<agentId>/agent/` with its own
    `auth-profiles.json` (schema: `{"profiles": {"<provider>:manual":
    {"type": "api_key" | "oauth" | "token", "provider": "<id>",
    "key": "<api-key>"}}}`).
  - `agents.list[]` entry in `openclaw.json` with `model.primary = $MODEL`.

## CONSTR-openclaw-image-pin (nfr, LOCKED-decision-derived)

- source: DEC-phase-2.3-decline-digest-pin (LOCKED ADR);
  docs/openclaw-local.md env-var table; docs/retrospectives/phase-2.md A3
- constraint: Gateway image pin is the date-shaped tag
  `ghcr.io/openclaw/openclaw:2026.4.14`. **Do not** pin by `sha256:` digest
  unless upstream re-tags. The `OPENCLAW_IMAGE` repo-variable/env override
  exists as the escape hatch (see the recorded
  `sha256:7ea070b04d1e70811fe8ba15feaad5890b1646021b24e00f4795bd4587a594ed`
  in the phase-2.3 ADR if emergency rollback is ever needed).

## CONSTR-openclaw-curated-provider-list (nfr)

- source: docs/openclaw-local.md § Why just these two
- constraint: Bootstrap's curated provider catalog is **deliberately narrow**
  — only models verified end-to-end with the 2-image turn (FPV + overhead):
  - `nvidia` → `nvidia/nvidia/nemotron-nano-12b-v2-vl` (base URL
    `https://integrate.api.nvidia.com/v1`, OpenAI-compatible, free, vision,
    multi-image).
  - `kimi` → `kimi/k2p5` (base URL `https://api.kimi.com/coding/`, Gateway
    alias to `kimi-for-coding` which is Kimi 2.6 as of this writing; free
    coding-tier quota, vision, multi-image).
- rationale: curated 1-per-provider, not a broad catalog (memory rule:
  "curated models over breadth"). To re-enable more, lift the curation in
  `scripts/openclaw-bootstrap.sh` (`EXTRA_MODELS_JSON` arrays) and rerun
  `tests/test_openclaw_bootstrap.py`.
- models explicitly excluded (why): `meta/llama-3.2-11b/90b-vision-instruct`
  (400 "At most 1 image(s) per request"), `minimaxai/minimax-m2.5/2.7` (400
  "not a multimodal model"), `microsoft/phi-4-multimodal-instruct` (not
  re-tested under agent framework), `nvidia/llama-3.1-nemotron-nano-vl-8b-v1`
  (works; dropped to keep curated list to one entry),
  `nvidia/nemotron-3-super-120b-a12b:free` on OpenRouter (text-only),
  `google/gemma-3-12b/27b-it:free` on OpenRouter (`:free` endpoints don't
  support tool use — Gateway agent edge sees 404).

## CONSTR-openclaw-webchat-tool-dispatch-gotcha (protocol)

- source: docs/openclaw-gateway-internals.md § Internal "webchat" channel
  gotcha
- constraint: Models added to the curated list must return plain text in
  `choices[0].message.content`, NOT a tool call. The Gateway's OpenAI HTTP
  endpoint sets `defaultMessageChannel: "webchat"` but
  `channel-selection-*.js:isKnownChannel` rejects `webchat` for tool
  dispatch. Aggressive-tool-calling models deadlock (tool dispatch error →
  framework retry → timeout).
- probe rule: before adding a new model, probe `/v1/chat/completions` with a
  plain "reply PONG" prompt; if it returns a tool call, reject.

## CONSTR-per-turn-cost-envelope (nfr)

- source: docs/technical-design.md § Cost Estimates;
  docs/contributing.md § Secrets required for CI;
  PLAN.md § Effort Estimate / Compute budget
- constraint: Target per-game cost envelope (320×240 FPV + overhead,
  2 images per step, 3 agents × 200 steps):
  - GPT-4o-mini: ~$0.018/game (dev default)
  - GPT-4o: ~$0.24/game
  - Claude Sonnet: ~$0.36/game
  - Kimi (coding-tier, CI real-model-smoke): ~$0.10 per 100-step 2-game run
    (observed in 05-real-model-smoke-validation.md).
- phase-2.4 wallet gates: `--max-usd 15` for the Kimi overnight sweep,
  `--max-usd 5` for the NVIDIA confirm, $20 hard cap overall.

## CONSTR-headless-unity-on-linux (nfr)

- source: docs/contributing.md § Headless AI2-THOR on Linux;
  CLAUDE.md § Gotchas
- constraint: AI2-THOR on Linux requires either X server or `xvfb-run` +
  `ai2thor[headless]`. Unity binary (~1 GB) downloads to `~/.ai2thor/` on
  first run; CI caches this. macOS may need additional rendering config.
- CI incantation: `xvfb-run -a python examples/<demo>.py ...`.

## CONSTR-live-probe-before-merge (nfr)

- source: `feedback_live_probe_gate.md` (per MEMORY.md pointer);
  PLAN.md § Failure Modes § NvidiaProvider row;
  docs/retrospectives/phase-2.1.md § retrospective § lesson
- constraint: Any new external HTTP surface (new provider, new Gateway
  endpoint contract) requires a real upstream probe before merge. Mocked
  tests alone are not sufficient. This is an iron rule derived from the
  Phase 2.1 incident where all 7 tasks passed lint + mocked tests against
  the wrong endpoint (`/tools/invoke`) and only broke on the first real
  request.

## CONSTR-development-topology (nfr)

- source: CLAUDE.md § Cloud vs local development;
  docs/contributing.md § Development topology
- constraint: Cloud sessions MUST NOT run tasks tagged `local-dev`. Real
  API keys, real Unity, real Gateway are workstation-only. CI can mirror
  them but proof starts locally. PRs whose core claim depends on real
  hardware must document local validation or file a `local-dev` issue
  (template: #50).

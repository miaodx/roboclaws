# Just Command Surface

Roboclaws uses a small composable Just grammar instead of exposing every
world/backend/preset/agent-engine combination as a separate recipe.

## Public Namespaces

- `run::*` is for humans and natural-language delegation.
- `agent::*` is for maintainer-level dispatch into private implementation
  modules.

Lower modules such as `openclaw::*`, `molmo::*`,
`harness::*`, `verify::*`, `mcp::*`, `code::*`, `chat::*`,
and `dev::*` are private. They remain runnable for debugging, but they are
hidden from `just --summary` and shell completion.

## Main Grammar

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [preset=<preset>] [prompt=<goal>] [provider_profile=<profile>] [key=value ...]
```

Surfaces:

- `household-world`
- `planner-proof`

Household presets:

- `map-build`
- `cleanup`

Planner-proof still uses `intent=planner-proof`:

- `planner-proof`

Worlds and scenes:

- `molmospaces/val_0`
- `agibot-g2/map-12`
- `b1-map12`
- `planner-proof/default`

Backends are world-scoped, not a cross product:

- `mujoco` for MolmoSpaces household scenes and planner proof
- `isaaclab` for `world=b1-map12` and generic local Isaac runtime proof
- `agibot-gdk` for `world=agibot-g2/map-12`

MolmoSpaces household routes do not accept `backend=isaaclab`.

Agent engines:

- `codex-cli`
- `claude-code`
- `openai-agents-sdk`
- `direct-runner`

Provider profiles are selected only for agent engines that need a model/key
route. Examples include `codex-env`, `mify`, `kimi-anthropic`,
`mimo-anthropic`, and `mify-anthropic`. Deterministic engines such as
`direct-runner` do not accept `provider_profile`.

Validation-required maintainer engines, such as `openclaw-gateway`, stay out of
the normal public engine list. Use the OpenClaw docs before running them.

Reports for non-Molmo tasks:

- `visual` is the default. Use it for human-facing runs that should produce
  reviewable images, timelines, and metrics.
- `minimal` is for cheaper semantic evidence during AI-agent iteration.

Household cleanup input/evidence lanes:

- `smoke` is the cheap synthetic contract sanity preset, not a real evidence
  lane.
- `world-oracle-labels` is the default structured-label lane: the agent
  receives observed object handles and structured labels from privileged world
  state; robot-view images are report evidence, not model input.
- `world-public-labels` keeps structured detections while removing
  destination/tool oracle hints and pre-confirmed navigation authorization.
- `camera-raw-fpv` withholds structured labels and provides raw camera
  artifacts for model-declared observations.
- `camera-grounded-labels` registers structured candidates from camera
  observations and requires `camera_labeler=<labeler>`.

`evidence_lane` decides what the agent sees. `camera_labeler` only applies to
`camera-grounded-labels` and decides how camera labels are produced. Use
`camera_labeler=sim-projected-labels` for the deterministic camera-projected
control producer, or labelers such as `grounding-dino`, `yoloe`, and
`omdet-turbo` for deployable camera producers. Public `visual_grounding=...`
is no longer accepted on task routes; Visual Grounding Service terminology
remains internal service and benchmark provenance.

These lanes do not choose online/offline map behavior. Base Navigation Map is
the current start-of-run map context: occupancy geometry, generated exploration
candidates, and public room-category hints when available. Use
`runtime_map_prior=...` when a cleanup run should consume a prebuilt Runtime
Metric Map snapshot or canonical Actionable Semantic Map Snapshot. Historical
`minimal` / `rich` map artifacts may remain readable, but they are not current
product choices for operators or agents.

For timing work that should skip per-tool robot-view capture, keep the normal
`world-oracle-labels` lane and pass an explicit capture option such as
`robot_views=off`.

For `surface=household-world`, omit `preset=` for no-preset open household
goals and pass the operator goal through `prompt=...`. Use
`preset=cleanup prompt=...` only when the prompt narrows cleanup scope while
keeping cleanup evaluation.

## Live Agent Launch Behavior

`just run::surface surface=household-world agent_engine=codex-cli preset=cleanup evidence_lane=world-oracle-labels` launches a detached tmux session.
The session owns the cleanup MCP server, the `codex exec` process, raw Codex
logs, the MCP trace, and the final checker. The invoking terminal returns after
printing the tmux session name and artifact directory, so monitor sessions do
not spend their own context window on the live agent transcript.

Use the printed probe command, or let it find the latest Codex cleanup run:

```bash
just molmo::status
just molmo::status output/molmo/codex-report/<stamp>/seed-7
tmux attach -t <session>
tail -f output/molmo/codex-report/<stamp>/seed-7/driver.log
```

The probe summarizes tmux liveness, elapsed time, MCP tool progress,
`run_result.json` / `report.html` readiness, and the latest Codex message when
available. Only one detached Molmo/Codex cleanup run is allowed at a time
because each visual run owns a MuJoCo-backed MolmoSpaces backend. If a run is
active or the requested MCP port is already accepting connections, the launcher
fails instead of choosing another port. Claude Code and OpenClaw live cleanup
engines still use their existing interactive launch paths.

Repo-local `.env` keys route live Codex and Claude launchers without editing
user-level CLI config. Normal users configure keys only; command shape controls
behavior.

```bash
cp .env.example .env
# Fill CODEX_BASE_URL and CODEX_API_KEY for the default Codex codex-env route.
# Fill MIMO_TP_KEY, KIMI_API_KEY, or XM_LLM_API_KEY for Claude Code routes.
# Optional: set ROBOCLAWS_CODEX_PROVIDER=mify explicitly to use XM_LLM_API_KEY for Codex.
# Optional: set ROBOCLAWS_CODEX_PROVIDER=minimax explicitly to use MM_API_KEY for Codex.
```

Detached live Codex sessions inherit selected API keys and proxy variables
exported in the invoking shell at launch time. They also source repo-local
`.env` inside the runner, so either route works for local-only credentials.

Run `just code::codex-provider-smoke` locally before long Codex visual runs to
verify the `.env`-configured Responses-compatible endpoint works with the pinned
Docker-backed Codex CLI. Codex defaults to `codex-env` (`CODEX_BASE_URL` plus
`CODEX_API_KEY`, Responses API, default model `gpt-5.5`). To use the internal
multi-model aggregator, set `ROBOCLAWS_CODEX_PROVIDER=mify` explicitly with
`XM_LLM_API_KEY`; that profile uses `xiaomi/mimo-v2.5` and disables web search
because the gateway phase does not support Codex's web search tool. To use
MiniMax's Responses-compatible token-plan route, set
`ROBOCLAWS_CODEX_PROVIDER=minimax` with `MM_API_KEY`; the default model is
`MiniMax-M3`, and `ROBOCLAWS_CODEX_MODEL=MiniMax-M2.7-highspeed` selects the
faster text-only route for agent latency tests. The highspeed model still emits
reasoning tokens on the Responses route, so tiny output-token budgets can stop
before assistant text is produced. Hosted CI does not run Codex or Codex
provider smoke.

Provider/model facts are centralized in
`roboclaws/agents/provider_registry.py`. Shell helpers and the operator console
read that registry for default models, required env keys, wire API, route
status, and route capabilities. Household evidence-lane policy is separate:
structured lanes can use text-only routes, while `camera-raw-fpv` requires both
model image input and verified runtime image transport. MiniMax highspeed and
routes with unknown image transport are therefore blocked from raw-FPV launches
until a live route verdict proves otherwise. Current live verdicts live in
`docs/human/model-route-verdicts.yaml`; the narrative audit remains in
`docs/human/model-matrix.md`.

Public Codex / Claude live-agent runs support only the pinned Docker toolchain:

```bash
just run::surface surface=household-world agent_engine=claude-code provider_profile=mimo-anthropic preset=cleanup evidence_lane=world-oracle-labels
```

The image is defined by `Dockerfile.coding-agents` and pins
`@openai/codex@0.130.0` plus `@anthropic-ai/claude-code@2.1.143` by default.
Update `scripts/dev/coding_agent_toolchain.env` deliberately when advancing the
agent CLIs. `just code::docker-install-wrappers` still exists for CI setup and
manual debugging where a `codex` or `claude` command path is required.

Codex runs use repo-local `.env` credentials in the pinned container. Host
`~/.codex` auth/config is not copied into repo workflows:

```bash
just run::surface surface=household-world agent_engine=codex-cli provider_profile=codex-env preset=cleanup evidence_lane=world-oracle-labels
```

Docker-backed coding-agent tasks use an isolated generated workspace owned by
the recipe. The agent container sees `/workspace/task` plus only the mounted
task skill directories under `/workspace/skills/<name>`. Repo-root
`AGENTS.md`, `CLAUDE.md`, `.git`, and implementation files are not mounted; the
MCP implementation stays on the host and is reached over HTTP.
Current task mappings:

- `surface=household-world preset=map-build`: `household-open-task` with cleanup actions disabled for simulator backends; dedicated Agibot map-build runner for public `backend=agibot-gdk`, lowered internally to implementation backend `agibot_gdk`
- `surface=household-world preset=cleanup`: `molmo-realworld-cleanup`
- `surface=household-world prompt=...`: `household-open-task` with an open-ended goal contract
- `surface=planner-proof intent=planner-proof`: planner-proof bundle runner

Python owns route metadata and reusable launch pieces:

- Public task specs live in domain packages such as `roboclaws.household.tasks`,
  then register through `roboclaws.launch.catalog`.
- Coding-agent driver helpers and kickoff prompts live under
  `roboclaws.agents`.
- MCP server startup goes through `python -m roboclaws.cli.agent_server`, with
  launch-shaped household targets selecting the household server variants.
- Direct deterministic household cleanup runs through
  `python -m roboclaws.household.realworld_cleanup`; the example script is a
  thin wrapper for manual use.

For Codex, isolated runs also mount an empty read-only `CODEX_HOME/skills`, so
bundled/system Codex skills are not available. Recipe-owned prompts should state
that the bundled task skill instructions are already available in the generated
workspace and should include the operative task constraints directly; avoid
prompting Codex to call `read_mcp_resource`, `resources/read`, or invented MCP
namespaces such as `mcp__<server>__`.

## Examples

```bash
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels scenario_setup=baseline
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="我渴了，帮我找些解渴的东西"
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels runtime_map_prior=output/map/runtime_metric_map.json
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=camera-raw-fpv
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=fake-http
just agent::harness molmo-visual-grounding-benchmark pipeline=fake-http
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino,yoloe,omdet-turbo
just agent::harness molmo-visual-grounding-benchmark matrix=harness/visual_grounding/first_wave_gpu_sidecar_matrix.json corpus=harness/visual_grounding/local_raw_fpv_corpus.json timeout_s=60
just agent::eval recommend plan=docs/plans/example.md budget=focused
just agent::eval execute since=origin/main budget=focused
.venv/bin/python scripts/visual_grounding/build_representative_visual_grounding_corpus.py output --output output/visual-grounding-corpora/representative-raw-fpv/representative_raw_fpv_corpus.json
.venv/bin/python scripts/visual_grounding/build_molmospaces_visual_grounding_bbox_corpus.py --output output/visual-grounding-corpora/molmospaces-bbox-10x10/corpus.json --scene-indices 0-9 --targets-per-scene 10
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --pipeline real-router --adapter-mode real
just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run
```

For `pipeline=fake-http` visual-grounding runs, start the configurable service
in fake mode first:

```bash
.venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --pipeline fake-http
```

For named contract pipelines without real model weights, use the contract-fake
dispatcher:

```bash
.venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
  --pipeline contract-fake
```

For real proposer sidecar probes, install the optional model dependencies and
weights explicitly in the dedicated sidecar environment, then start the same
service in real-router mode:

```bash
UV_PROJECT_ENVIRONMENT="$PWD/.venv-visual-grounding" \
  uv sync --project sidecars/visual-grounding --extra cuda --extra yoloe --extra omdet

VISUAL_GROUNDING_DEVICE=auto \
VISUAL_GROUNDING_TORCH_DTYPE=auto \
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base \
VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 \
VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real

VISUAL_GROUNDING_YOLOE_MODEL_ID=yoloe-11s-seg.pt \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real

VISUAL_GROUNDING_OMDET_MODEL_ID=omlab/omdet-turbo-swin-tiny-hf \
  .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline real-router --adapter-mode real
```

Hosted VLM refiner/direct-producer routes are retired from the active
visual-grounding sidecar contract. ADR-0138 keeps old Gemini/MiMo/Qwen evidence
as historical context instead of keeping those provider slots runnable here.

To inspect the sidecar adapter slots without starting a service:

```bash
.venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --list-adapters
```

The adapter catalog includes redacted `runtime` readiness for each slot. Local
proposers report importable dependencies such as `torch`, `transformers`, and
`ultralytics`; weights are verified only by a real adapter run.

Benchmark reports include API cost and memory telemetry slots. They are
populated only when the configured sidecar reports stage usage/cost or memory
metadata; otherwise the result records `not_reported_by_service`.
The benchmark result also emits the capped end-to-end probe set: `sim` plus the
best detector-only proposer pipeline.
Full cleanup probes stay blocked until every selected non-sim pipeline has real
detector sidecar provenance; mixed fake/real rows are still benchmark-shape
evidence, not rollout evidence.
`--require-success` on the benchmark checker means no pipeline failures; zero
candidates remain a valid poor-recall result. Use `--require-candidates` only
for fake smoke tests that should always emit candidates.

To create a local path-backed RAW_FPV benchmark corpus from a stored cleanup run:

```bash
.venv/bin/python scripts/visual_grounding/build_visual_grounding_corpus_from_cleanup_run.py \
  output/molmo/<run>/seed-7 \
  --output harness/visual_grounding/local_raw_fpv_corpus.json
```

Real proposer pipeline ids such as `grounding-dino` and `yoloe` report
`adapter_unavailable` or dependency failures unless the service is started with
`--adapter-mode contract-fake` for contract tests or `--adapter-mode real` with
installed sidecar dependencies and model weights. Retired hosted VLM ids such
as `grounding-dino+mimo-v2.5`, `mimo-v2.5-direct`, and `qwen3-vl-direct` are not
active adapter slots. The adapter catalog records the optional sidecar extra and
current redacted runtime readiness for each target adapter.
`scripts/visual_grounding/serve_fake_visual_grounding.py` is a deterministic
fake-service utility for tests and local scripts that need that endpoint
directly.

Prompt mappings for agents:

| Prompt | Command |
|---|---|
| "run the semantic map build task" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels` |
| "run the semantic map build task with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=map-build agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels` |
| "run the household cleanup task with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels` |
| "run an open-ended household goal with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="我渴了，帮我找些解渴的东西"` |
| "run the household cleanup camera raw lane" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco preset=cleanup agent_engine=direct-runner evidence_lane=camera-raw-fpv` |
| "run the planner proof dry run" | `just run::surface surface=planner-proof world=planner-proof/default backend=mujoco intent=planner-proof agent_engine=direct-runner mode=dry-run` |

## Maintainer Dispatch

Use `agent::*` only when you are intentionally bypassing the human task grammar:

```bash
just agent::run <dispatch-target> <agent-engine> [report|evidence-lane] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up
just agent::gateway up
```

`agent::run` is a private maintainer dispatcher. Public callers should use
`run::surface`; the dispatcher accepts launch-shaped targets such as
`household-world.cleanup` and normalizes them to older implementation recipes
only after the public axes have been resolved.

The required PR gate is reproducible locally with
`just agent::verify ci-required`. Use `just agent::verify mock` for a faster
loop when you do not need the mock HTML report artifact.

Use `just agent::eval recommend|execute ...` when a plan or diff needs the
eval-harness facade instead of a hand-written fixed proof list. The harness
writes JSON, Markdown, and HTML under `output/eval-harness/` and records
selected, skipped, run, failed, and blocked rows with source-signal rationale.

For tests, set `ROBOCLAWS_JUST_TRACE=1` to print the lower-level command route
without launching the underlying simulator, Gateway, or agent.

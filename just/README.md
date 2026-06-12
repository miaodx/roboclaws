# Just Command Surface

Roboclaws uses a small composable Just grammar instead of exposing every
world/backend/intent/agent-engine combination as a separate recipe.

## Public Namespaces

- `run::*` is for humans and natural-language delegation.
- `agent::*` is for maintainer-level dispatch into private implementation
  modules.

Lower modules such as `openclaw::*`, `vlm::*`, `molmo::*`,
`harness::*`, `verify::*`, `mcp::*`, `code::*`, `chat::*`, `appliance::*`,
and `dev::*` are private. They remain runnable for debugging, but they are
hidden from `just --summary` and shell completion.

## Main Grammar

```bash
just run::surface surface=<surface> agent_engine=<engine> [world=<world>] [backend=<backend>] [intent=<intent>] [provider_profile=<profile>] [key=value ...]
```

Surfaces:

- `ai2thor-world`
- `ai2thor-games`
- `household-world`
- `planner-proof`

Intents:

- `navigate`
- `photo-capture`
- `territory`
- `coverage`
- `map-build`
- `cleanup`
- `open-ended`
- `planner-proof`

Worlds and scenes:

- `molmospaces/val_0`
- `agibot-g2/map-12`
- `b1-map12`
- `ai2thor/FloorPlan201`
- `ai2thor-games/FloorPlan201`
- `planner-proof/default`

Backends:

- `mujoco`
- `isaaclab`
- `agibot-gdk`
- `ai2thor`

Agent engines:

- `codex-cli`
- `claude-code`
- `openai-agents-sdk`
- `direct-runner`
- `openclaw-gateway`
- `vlm-policy`
- `script-runner`

Provider profiles are selected only for agent engines that need a model/key
route. Examples include `codex-env`, `mify`, `kimi-anthropic`,
`mimo-anthropic`, and `mify-anthropic`. Deterministic engines such as
`direct-runner` and `script-runner` do not accept `provider_profile`.

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

These lanes do not choose online/offline map behavior. `map_mode=minimal` is the
default map projection: it exposes occupancy geometry, generated exploration
candidates, and runtime semantic anchors. Use `runtime_map_prior=...` when a
cleanup run should consume a prebuilt runtime map snapshot. `map_mode=rich`
remains available only as an explicit legacy/debug projection with pre-authored
public fixture semantics.

For timing work that should skip per-tool robot-view capture, keep the normal
`world-oracle-labels` lane and pass an explicit capture option such as
`robot_views=off`.

If `intent=` is omitted, the surface default is used. For
`surface=household-world`, a supplied `prompt=` without `intent=` infers
`intent=open-ended`; an explicit `intent=cleanup prompt=...` narrows cleanup
scope while keeping cleanup evaluation.

## Live Agent Launch Behavior

`just run::surface surface=household-world agent_engine=codex-cli intent=cleanup evidence_lane=world-oracle-labels` launches a detached tmux session.
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
because the gateway phase does not support Codex's web search tool. Hosted CI
does not run Codex or Codex provider smoke.

Public Codex / Claude live-agent runs support only the pinned Docker toolchain:

```bash
just run::surface surface=household-world agent_engine=claude-code provider_profile=mimo-anthropic intent=cleanup evidence_lane=world-oracle-labels
```

The image is defined by `Dockerfile.coding-agents` and pins
`@openai/codex@0.130.0` plus `@anthropic-ai/claude-code@2.1.143` by default.
Update `scripts/dev/coding_agent_toolchain.env` deliberately when advancing the
agent CLIs. `just code::docker-install-wrappers` still exists for CI setup and
manual debugging where a `codex` or `claude` command path is required.

Codex runs use repo-local `.env` credentials in the pinned container. Host
`~/.codex` auth/config is not copied into repo workflows:

```bash
just run::surface surface=household-world agent_engine=codex-cli provider_profile=codex-env intent=cleanup evidence_lane=world-oracle-labels
```

Docker-backed coding-agent tasks use an isolated generated workspace owned by
the recipe. The agent container sees `/workspace/task` plus only the mounted
task skill directories under `/workspace/skills/<name>`. Repo-root
`AGENTS.md`, `CLAUDE.md`, `.git`, and implementation files are not mounted; the
MCP implementation stays on the host and is reached over HTTP.
Current task mappings:

- `ai2thor-nav` direct Codex/Claude: `ai2thor-navigator`
- `photo-chairs` direct Codex/Claude: `capture-object-photo`
- `semantic-map-build` direct: `molmo-realworld-cleanup` with cleanup actions disabled
- `semantic-map-build` live Codex: `molmo-realworld-cleanup` with cleanup actions disabled for simulator backends; dedicated Agibot map-build runner for public `backend=agibot-gdk`, lowered internally to implementation backend `agibot_gdk`
- `household-cleanup` live Codex/Claude: `molmo-realworld-cleanup`

Python owns route metadata and reusable launch pieces:

- Public task specs live in domain packages such as `roboclaws.ai2thor.tasks`
  and `roboclaws.household.tasks`, then register through
  `roboclaws.launch.catalog`.
- Coding-agent driver helpers and kickoff prompts live under
  `roboclaws.agents`.
- MCP server startup goes through `python -m roboclaws.cli.agent_server`, with
  `household-cleanup` and `semantic-map-build` selecting the household server
  variants.
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
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels scenario_setup=baseline
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=smoke
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="我渴了，帮我找些解渴的东西"
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=world-oracle-labels runtime_map_prior=output/map/runtime_metric_map.json
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=camera-raw-fpv
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=sim-projected-labels
just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=camera-grounded-labels camera_labeler=fake-http
just agent::harness molmo-visual-grounding-benchmark pipeline=fake-http
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino,yoloe,yoloe+mimo-v2.5
just agent::harness molmo-visual-grounding-benchmark matrix=harness/visual_grounding/first_wave_gpu_sidecar_matrix.json corpus=harness/visual_grounding/local_raw_fpv_corpus.json timeout_s=60
just agent::harness agent-validation recommend plan=docs/plans/example.md budget=focused
just agent::harness agent-validation execute since=origin/main budget=focused
.venv/bin/python scripts/visual_grounding/build_representative_visual_grounding_corpus.py output --output output/visual-grounding-corpora/representative-raw-fpv/representative_raw_fpv_corpus.json
.venv/bin/python scripts/visual_grounding/build_molmospaces_visual_grounding_bbox_corpus.py --output output/visual-grounding-corpora/molmospaces-bbox-10x10/corpus.json --scene-indices 0-9 --targets-per-scene 10
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --pipeline real-router --adapter-mode real
just run::surface surface=ai2thor-world world=ai2thor/FloorPlan201 backend=ai2thor intent=navigate agent_engine=openclaw-gateway
just run::surface surface=ai2thor-world world=ai2thor/FloorPlan201 backend=ai2thor intent=photo-capture agent_engine=codex-cli provider_profile=codex-env
just run::surface surface=ai2thor-games world=ai2thor-games/FloorPlan201 backend=ai2thor intent=territory agent_engine=vlm-policy steps=20 agents=2
just run::surface surface=ai2thor-games world=ai2thor-games/FloorPlan201 backend=ai2thor intent=coverage agent_engine=script-runner output_dir=output/script/coverage-smoke
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

Hosted VLM refiner/direct-producer routes use the same sidecar binary and an
OpenAI-compatible chat-completions endpoint. Configure the endpoint explicitly
for local test servers, or use the MiMo defaults with `MIMO_TP_KEY`:

```bash
MIMO_TP_KEY=... \
  .venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline grounding-dino+mimo-v2.5 --adapter-mode real

VISUAL_GROUNDING_QWEN_BASE_URL=http://127.0.0.1:8000/v1 \
VISUAL_GROUNDING_QWEN_API_KEY=... \
  .venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py \
    --pipeline qwen3-vl-direct --adapter-mode real
```

To inspect the sidecar adapter slots without starting a service:

```bash
.venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --list-adapters
```

The adapter catalog includes redacted `runtime` readiness for each slot. Local
proposers report importable dependencies such as `torch`, `transformers`, and
`ultralytics`; weights are verified only by a real adapter run. Hosted MiMo/Qwen
routes report endpoint/auth readiness and auth mode without exposing raw keys or
bearer tokens.

Benchmark reports include API cost and memory telemetry slots. They are
populated only when the configured sidecar reports stage usage/cost or memory
metadata; otherwise the result records `not_reported_by_service`.
The benchmark result also emits the capped end-to-end probe set: `sim`, the
best proposer-only pipeline, the best proposer-plus-refiner pipeline, and at
most one direct VLM pipeline.
Promotion stays blocked until every selected non-sim pipeline has real or
hosted stage provenance; mixed fake/real rows are still benchmark-shape
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
installed sidecar dependencies and model weights. Hosted refiner/direct routes
such as `grounding-dino+mimo-v2.5`, `mimo-v2.5-direct`, and
`qwen3-vl-direct` report `missing_config` until their OpenAI-compatible
endpoint and key/no-key local policy are configured. The adapter catalog records
the optional sidecar extra, provider configuration slot, and current redacted
runtime readiness for each target adapter. The older
`scripts/visual_grounding/serve_fake_visual_grounding.py`
entry point remains a compatibility shim for tests and local scripts that need
the deterministic fake endpoint directly.

Prompt mappings for agents:

| Prompt | Command |
|---|---|
| "run the semantic map build task" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=direct-runner evidence_lane=world-oracle-labels` |
| "run the semantic map build task with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=map-build agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels` |
| "run the household cleanup task with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=world-oracle-labels` |
| "run the household cleanup task with codex with smoke profile" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=codex-cli provider_profile=codex-env evidence_lane=smoke` |
| "run an open-ended household goal with codex" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco agent_engine=codex-cli provider_profile=codex-env prompt="我渴了，帮我找些解渴的东西"` |
| "run the household cleanup camera raw lane" | `just run::surface surface=household-world world=molmospaces/val_0 backend=mujoco intent=cleanup agent_engine=direct-runner evidence_lane=camera-raw-fpv` |
| "run the ai2thor nav task with openclaw" | `just run::surface surface=ai2thor-world world=ai2thor/FloorPlan201 backend=ai2thor intent=navigate agent_engine=openclaw-gateway report=visual` |

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

Use `just agent::harness agent-validation recommend|execute ...` when a plan or
diff needs an adaptive validation matrix instead of a hand-written fixed
harness. The matrix writes JSON, Markdown, and HTML under
`output/agent-validation-matrix/` and records selected, skipped, run, and
blocked gates with source-signal rationale.

For tests, set `ROBOCLAWS_JUST_TRACE=1` to print the lower-level command route
without launching the underlying simulator, Gateway, or agent.

# Just Command Surface

Roboclaws uses a small composable Just grammar instead of exposing every
task/driver/report combination as a separate recipe.

## Public Namespaces

- `task::*` is for humans and natural-language delegation.
- `agent::*` is for maintainer-level dispatch into private implementation
  modules.

Lower modules such as `openclaw::*`, `vlm::*`, `molmo::*`, `harness::*`,
`verify::*`, `mcp::*`, `code::*`, `chat::*`, `appliance::*`, and `dev::*` are
private. They remain runnable for debugging, but they are hidden from
`just --summary` and shell completion.

## Main Grammar

```bash
just task::run <task> <driver> [report|profile] [key=value ...]
```

Tasks:

- `ai2thor-nav`
- `territory`
- `coverage`
- `photo-chairs`
- `semantic-map-build`
- `household-cleanup`
- `molmo-planner-proof`

Drivers:

- `openclaw`
- `vlm`
- `codex`
- `claude`
- `script`
- `direct`
- `mcp-smoke`

Reports for non-Molmo tasks:

- `visual` is the default. Use it for human-facing runs that should produce
  reviewable images, timelines, and metrics.
- `minimal` is for cheaper semantic evidence during AI-agent iteration.

Household cleanup input/evidence lanes:

- `smoke` is the cheap synthetic contract sanity profile.
- `world-labels` is the default structured-label lane: the agent receives
  observed object handles and structured labels; robot-view images are report
  evidence, not model input.
- `camera-raw` withholds structured labels and provides raw camera artifacts.
- `camera-labels` registers structured candidates from camera observations.

These lanes do not choose online/offline map behavior. Use `map_mode=minimal`
or `map_mode=rich` for the map projection, and `runtime_map_prior=...` when a
cleanup run should consume a prebuilt runtime map snapshot.

For timing work that should skip per-tool robot-view capture, keep the normal
`world-labels` profile and pass an explicit capture option such as
`robot_views=off`.

If the third argument is `key=value`, `task::run` treats the report/profile as
omitted and keeps the task default (`visual` for non-Molmo tasks,
`world-labels` for household cleanup).

## Live Agent Launch Behavior

`just task::run household-cleanup codex world-labels` launches a detached tmux session.
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
fails instead of choosing another port. `claude` and `openclaw` live cleanup
drivers still use their existing interactive launch paths.

Repo-local `.env` keys route live Codex and Claude launchers without editing
user-level CLI config. Normal users configure keys only; command shape controls
behavior.

```bash
cp .env.example .env
# Fill XM_LLM_API_KEY for the default Codex mify route.
# Fill MIMO_TP_KEY, KIMI_API_KEY, or XM_LLM_API_KEY for Claude Code routes.
# Optional: fill CODEX_BASE_URL / CODEX_API_KEY only for non-mify Codex debugging.
```

Detached live Codex sessions inherit selected API keys and proxy variables
exported in the invoking shell at launch time. They also source repo-local
`.env` inside the runner, so either route works for local-only credentials.

Run `just code::codex-provider-smoke` locally before long Codex visual runs to
verify the `.env`-configured Responses-compatible endpoint works with the pinned
Docker-backed Codex CLI. When `XM_LLM_API_KEY` is present, Codex defaults to the
internal multi-model aggregator (`mify`, `xiaomi/mimo-v2-omni`, Responses API)
and disables web search because that gateway phase does not support Codex's web
search tool. Hosted CI does not run Codex or Codex provider smoke.

Public Codex / Claude live-agent runs support only the pinned Docker toolchain:

```bash
just task::run household-cleanup claude world-labels
```

The image is defined by `Dockerfile.coding-agents` and pins
`@openai/codex@0.130.0` plus `@anthropic-ai/claude-code@2.1.143` by default.
Update `scripts/dev/coding_agent_toolchain.env` deliberately when advancing the
agent CLIs. `just code::docker-install-wrappers` still exists for CI setup and
manual debugging where a `codex` or `claude` command path is required.

Codex runs use repo-local `.env` credentials in the pinned container. Host
`~/.codex` auth/config is not copied into repo workflows:

```bash
just task::run household-cleanup codex world-labels
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
- `household-cleanup` live Codex/Claude: `molmo-realworld-cleanup`

For Codex, isolated runs also mount an empty read-only `CODEX_HOME/skills`, so
bundled/system Codex skills are not available. Recipe-owned prompts should state
that the bundled task skill instructions are already available in the generated
workspace and should include the operative task constraints directly; avoid
prompting Codex to call `read_mcp_resource`, `resources/read`, or invented MCP
namespaces such as `mcp__<server>__`.

## Examples

```bash
just task::run semantic-map-build direct world-labels
just task::run household-cleanup codex
just task::run household-cleanup codex smoke
just task::run household-cleanup direct camera-raw
just task::run household-cleanup direct camera-labels
just task::run household-cleanup mcp-smoke camera-labels visual_grounding=fake-http
just task::run household-cleanup direct world-labels runtime_map_prior=output/map/runtime_metric_map.json
just agent::harness molmo-visual-grounding-benchmark pipeline=fake-http
just agent::harness molmo-visual-grounding-benchmark pipeline=grounding-dino,yoloe,yoloe+mimo-v2-omni
just agent::harness molmo-visual-grounding-benchmark matrix=harness/visual_grounding/first_wave_gpu_sidecar_matrix.json corpus=harness/visual_grounding/local_raw_fpv_corpus.json timeout_s=60
.venv/bin/python scripts/visual_grounding/build_representative_visual_grounding_corpus.py output --output output/visual-grounding-corpora/representative-raw-fpv/representative_raw_fpv_corpus.json
.venv/bin/python scripts/visual_grounding/build_molmospaces_visual_grounding_bbox_corpus.py --output output/visual-grounding-corpora/molmospaces-bbox-10x10/corpus.json --scene-indices 0-9 --targets-per-scene 10
VISUAL_GROUNDING_DINO_MODEL_ID=IDEA-Research/grounding-dino-base VISUAL_GROUNDING_DINO_BOX_THRESHOLD=0.25 VISUAL_GROUNDING_DINO_TEXT_THRESHOLD=0.20 .venv-visual-grounding/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --pipeline real-router --adapter-mode real
just task::run ai2thor-nav openclaw
just task::run photo-chairs codex
just task::run territory vlm steps=20 agents=2
just task::run coverage script output_dir=output/script/coverage-smoke
just task::run molmo-planner-proof direct mode=dry-run
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
    --pipeline grounding-dino+mimo-v2-omni --adapter-mode real

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
such as `grounding-dino+mimo-v2-omni`, `mimo-v2-omni-direct`, and
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
| "run the semantic map build task" | `just task::run semantic-map-build direct world-labels` |
| "run the household cleanup task with codex" | `just task::run household-cleanup codex world-labels` |
| "run the household cleanup task with codex with smoke profile" | `just task::run household-cleanup codex smoke` |
| "run the household cleanup camera raw profile" | `just task::run household-cleanup direct camera-raw` |
| "run the ai2thor nav task with openclaw" | `just task::run ai2thor-nav openclaw visual` |

## Maintainer Dispatch

Use `agent::*` only when you are intentionally bypassing the human task grammar:

```bash
just agent::run <task> <driver> [report] [key=value ...]
just agent::verify <target> [args ...]
just agent::harness <target> [args ...]
just agent::mcp up
just agent::gateway up
```

For tests, set `ROBOCLAWS_JUST_TRACE=1` to print the lower-level command route
without launching the underlying simulator, Gateway, or agent.

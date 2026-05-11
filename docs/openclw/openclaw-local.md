# OpenClaw Gateway — local quick-start

This is the concrete recipe for running the Phase 2 demo
(`examples/openclaw_demo.py`) against a local OpenClaw Gateway. CI follows
the same contract in `.github/workflows/ci.yml` under the `openclaw-smoke`
job.

If you want a warm cache before running multiple demos, pre-pull the image first:

```bash
just openclaw::pull-image
```

## Prerequisites

- Docker (Linux: rootless or regular; macOS: Docker Desktop).
- An API key for one of the two supported upstream providers:
  - **`NV_API_KEY`** — NVIDIA NIM free tier (the bootstrap's default when
    this is set). Get one at <https://build.nvidia.com>.
  - **`KIMI_API_KEY`** — Moonshot/Kimi coding tier. Free (coding quota).
    Resolves via the Gateway plugin's alias to the current
    `kimi-for-coding` upstream, which is Kimi 2.6 as of this writing.
- A clone of `roboclaws` with the `skills/ai2thor-navigator/` directory
  present.

## 1. Bootstrap the Gateway (creates N named agents)

```bash
# NVIDIA NIM — default when NV_API_KEY is set:
export NV_API_KEY=nvapi-...
TOKEN=$(AGENTS=2 ./scripts/openclaw-bootstrap.sh)

# Kimi — explicit selection (or default when only KIMI_API_KEY is set):
export KIMI_API_KEY=sk-...
TOKEN=$(PROVIDER=kimi AGENTS=2 ./scripts/openclaw-bootstrap.sh)

# Kimi via the stock Gateway plugin/provider instead of the custom override:
TOKEN=$(PROVIDER=kimi KIMI_PROVIDER_MODE=plugin AGENTS=2 ./scripts/openclaw-bootstrap.sh)
```

That one command does every first-run step: pulls the pinned image, creates
a config volume, pre-creates the per-agent workspace + agent dirs,
pre-seeds `openclaw.json` (with `chatCompletions.enabled = true` and an
`agents.list` entry per agent), pre-seeds each agent's
`auth-profiles.json` with your Kimi key, mounts the `ai2thor-navigator`
skill read-only into every agent's workspace, starts the Gateway, waits
for `/readyz`, and finally probes `openclaw/agent-0` with a one-turn
`PONG` call so if anything in the skill/auth/model chain is broken you
hear about it before `examples/openclaw_demo.py` boots Unity.

The script prints the live bearer token on stdout (everything else goes
to stderr), so `TOKEN=$(...)` captures just the token.

Useful overrides:

| Var                 | Default                                   | Notes                                                           |
|---------------------|-------------------------------------------|-----------------------------------------------------------------|
| `PROVIDER`          | `nvidia` if `NV_API_KEY` set, else `kimi` | `nvidia` \| `kimi`.                                             |
| `KIMI_PROVIDER_MODE` | `custom`                                 | Kimi only: `custom` (repo default) \| `plugin` (stock Gateway Kimi provider). |
| `AGENTS`            | `2`                                       | Number of named agents (`1..8`).                                |
| `AGENT_PREFIX`      | `agent-`                                  | Must match `--agent-prefix` on the demo.                        |
| `AGENT_SOULS`       | `` (empty)                                | Csv of soul names per agent, e.g. `aggressive,defensive`. Supports dict form `agent-0:aggressive,agent-2:cooperative`. |
| `SOULS_DIR`         | `$PWD/skills/ai2thor-navigator/souls`     | Directory containing `<name>.md` SOUL files.                    |
| `PERSONALITY_PROBE` | `1`                                       | Set to `0` to skip divergence probe (needed when souls are identical). |
| `IMAGE`             | Same as `scripts/openclaw-defaults.env` (`OPENCLAW_IMAGE_DEFAULT`) | Pinned tag under test (override with a known-good release if needed). |
| `MODEL`             | per-provider default (see below)          | Explicit override. Format: `<provider>/<model-id>`.             |
| `IMAGE_MODEL`       | same as `MODEL`                           | Vision model for the generic OpenClaw `image` tool. Keep this pinned when you want deterministic image-tool routing. |
| `READY_TIMEOUT`     | `180`                                     | Seconds to wait for `/readyz`; newer image builds can spend more than 60s on cold start while provider/runtime deps settle. |
| `HOST_IP`           | `127.0.0.1`                               | Gateway port is localhost-only by default.                      |
| `PORT`              | `18789`                                   | Gateway HTTP port.                                              |
| `CONTAINER`         | `openclaw-gateway`                        | Docker container name.                                          |
| `VOLUME`            | `openclaw-gateway-config`                 | Docker volume holding `openclaw.json` + state.                  |

The bootstrap ships a **deliberately narrow** provider list — just the two
models verified end-to-end with the demo (FPV + overhead = 2 images per
turn, so the model must be free, multi-image-capable, and cooperate with
the Gateway's tool-bearing agent framework):

| Provider | Default model                           | Upstream                                             | Free | Vision | Multi-image | Status          |
|----------|-----------------------------------------|------------------------------------------------------|------|--------|-------------|-----------------|
| `nvidia` | `nvidia/nvidia/nemotron-nano-12b-v2-vl` | `https://integrate.api.nvidia.com/v1`                | yes  | yes    | yes         | verified        |
| `kimi`   | `anthropic_kimi/k2.6`                   | `https://api.kimi.com/coding/` (→ Kimi 2.6)          | yes  | yes    | yes         | verified        |
| `mimo`   | `mimo_openai/mimo-v2-omni`              | `https://token-plan-cn.xiaomimimo.com/v1`            | ?    | yes    | yes         | vision+tools ✓  |
| `mimo`   | `mimo_openai/mimo-v2.5-pro`             | `https://token-plan-cn.xiaomimimo.com/v1`            | ?    | no     | no          | text+tools ✓    |
| `mimo` (anthropic) | `mimo_anthropic/mimo-v2-omni`  | `https://token-plan-cn.xiaomimimo.com/anthropic`    | ?    | ?      | ?           | untested        |

> ℹ️ **MiMo model matrix** (probed 2026-04-23):
> - `mimo-v2-omni`: vision (base64 inline images) ✓ + tool calls ✓ — use for navigation.
> - `mimo-v2.5-pro` / `mimo-v2.5`: text + tool calls only; inline images silently ignored.
> - `just chat::run` defaults to the MiMo `mimo_openai/mimo-v2-omni` model
>   in this document's split-model examples.
> - Key env var: `MIMO_TP_KEY`. Mode: `MIMO_PROVIDER_MODE=openai` (default) or `anthropic`.

> ℹ️ By default the repo does **not** use the stock `kimi/k2p5` plugin path.
> It registers a custom provider override (`anthropic_kimi/k2.6`)
> at the same Kimi host so the request shape stays on plain
> `anthropic-messages` without the built-in plugin's reasoning-heavy defaults.
> The bootstrap also pins `agents.defaults.imageModel.primary` to the same
> model (or `IMAGE_MODEL` if you override it) so OpenClaw's generic `image`
> tool does not auto-pair to a different image-capable Kimi catalog entry.
> Set `KIMI_PROVIDER_MODE=plugin` to compare against the stock OpenClaw Kimi
> provider. In that mode, `kimi/k2p5` is the Gateway's legacy alias to
> `kimi-for-coding` per `/app/dist/provider-catalog-BCrO6TZn.js`. If the Kimi
> coding quota is exhausted the Gateway surfaces a `rate_limit_error` in the
> first turn (the probe catches it and the bootstrap exits 4).

For image-analysis flows, prefer base64 `data:image/...` payloads or files
written under the agent workspace / OpenClaw media roots. Avoid ad-hoc `/tmp/*`
paths inside the container: the Gateway's local-media allowlist rejects files
outside its configured workspace/media/temp roots.

### Why just these two

Kept short on purpose — every other free vision model we probed failed one
of three constraints. History preserved here so this file is the record
when we revisit in a future phase:

| Model                                          | Provider   | Why it's not viable                                                     |
|------------------------------------------------|------------|-------------------------------------------------------------------------|
| `meta/llama-3.2-{11b,90b}-vision-instruct`     | NVIDIA NIM | 400 "At most 1 image(s) per request" — demo sends 2                      |
| `microsoft/phi-4-multimodal-instruct`          | NVIDIA NIM | works for images in isolation; not re-tested under the agent framework   |
| `nvidia/llama-3.1-nemotron-nano-vl-8b-v1`      | NVIDIA NIM | works; dropped to keep the curated list to one entry                     |
| `minimaxai/minimax-m2.7` / `m2.5`              | NVIDIA NIM | 400 "not a multimodal model" — text-only on NIM                          |
| `nvidia/nemotron-3-super-120b-a12b:free`       | OpenRouter | text-only; returns 404 "No endpoints support image input"                |
| `google/gemma-3-{12b,27b}-it:free`             | OpenRouter | :free endpoints don't support tool use — Gateway's agent edge sees 404   |

To re-enable a broader list, lift the curation in
`scripts/openclaw-bootstrap.sh` (the `EXTRA_MODELS_JSON` arrays) and
rerun `tests/test_openclaw_bootstrap.py`.

## Per-agent personalities (Phase 2.2)

Bootstrap can drop a SOUL file into each agent's workspace via `AGENT_SOULS`:

```bash
export KIMI_API_KEY=sk-...
# Positional csv — one soul name per agent (no .md extension)
TOKEN=$(AGENTS=2 AGENT_SOULS=aggressive,defensive ./scripts/openclaw-bootstrap.sh)
```

The csv length must match `AGENTS`. Available SOULs (from
`skills/ai2thor-navigator/souls/`): `aggressive`, `defensive`, `cooperative`.

Bootstrap probes each agent post-startup with the same strategy question; if
two agents produce identical responses the bootstrap exits with code 5 —
usually a sign the SOULs didn't load (check `SOULS_DIR`). The probe is
automatically skipped when all souls are identical (e.g.
`cooperative,cooperative`) or when `PERSONALITY_PROBE=0`.

Dict form is also accepted for sparse assignment:
```bash
TOKEN=$(AGENTS=3 AGENT_SOULS="agent-0:aggressive,agent-2:cooperative" ./scripts/openclaw-bootstrap.sh)
# agent-1 gets the default (stock) SOUL
```

## Run the territory or coverage game over OpenClaw

Self-contained recipes — every env var is set inline.

### Territory game (adversarial — aggressive vs defensive)

Expected timing: ~3 min bootstrap (Docker pull cached) + ~15 min game (60 steps × 2 agents).
AI2-THOR Unity downloads ~1 GB on first run.

```bash
# 1. Set your API key
export KIMI_API_KEY=sk-...          # or: export NV_API_KEY=nvapi-...

# 2. Bootstrap with SOULs
export OPENCLAW_GATEWAY_TOKEN=$(AGENTS=2 AGENT_SOULS=aggressive,defensive \
    ./scripts/openclaw-bootstrap.sh)

# 3. Run the game
AGENT_SOULS=aggressive,defensive \
    xvfb-run -a python examples/territory_game.py \
    --backend openclaw --agents 2 --steps 60 \
    --output-dir output/openclaw/territory

# 4. Tear down
docker rm -f openclaw-gateway
```

Open `output/openclaw/territory/report.html` — aggressive agent's trail is
red, defensive is blue (SOUL badges visible on agent sprites).

Or use the canonical command: `just openclaw::run territory`

### Coverage game (cooperative — both agents cooperate)

```bash
# 1. Set your API key
export KIMI_API_KEY=sk-...

# 2. Bootstrap (PERSONALITY_PROBE=0 because both souls are identical)
export OPENCLAW_GATEWAY_TOKEN=$(AGENTS=2 AGENT_SOULS=cooperative,cooperative \
    PERSONALITY_PROBE=0 ./scripts/openclaw-bootstrap.sh)

# 3. Run the game
AGENT_SOULS=cooperative,cooperative \
    xvfb-run -a python examples/coverage_game.py \
    --backend openclaw --agents 2 --steps 60 \
    --output-dir output/openclaw/coverage

# 4. Tear down
docker rm -f openclaw-gateway
```

Or use the canonical command: `just openclaw::run coverage`

## 2. Run the navigation demo

```bash
OPENCLAW_GATEWAY_TOKEN=$TOKEN python examples/openclaw_demo.py \
    --agents 2 --steps 20
```

The demo posts each turn to `POST /v1/chat/completions` with
`model = "openclaw/<agent-N>"`. Frames flow inline as base64 `data:`
URLs — no bind mount, no shared filesystem. Artefacts land under
`output/openclaw-demo/`:

- `replay.gif` — animated overview (one composite frame per step)
- `report.html` — self-contained interactive report (step slider,
  per-agent FPV, VLM reasoning log)
- `replay.json` — full per-step manifest

## 3. Clean up

```bash
docker rm -f openclaw-gateway
docker volume rm openclaw-gateway-config
```

## What the bootstrap actually did

- Created `agent-0`, `agent-1`, … (one per `AGENTS=`) as **named
  Gateway agents**, each with its own workspace directory, `MEMORY.md`
  slot, and persona slot.
- Seeded every agent's `~/.openclaw/agents/<id>/agent/auth-profiles.json`
  with a `<provider>:manual` profile carrying the selected provider's API
  key, so each agent has an isolated credential store.
- Bind-mounted `skills/ai2thor-navigator/` read-only into every
  agent's workspace, so every agent's system prompt contains the
  navigator skill.
- When `AGENT_SOULS` is set: copied `<SOULS_DIR>/<soul>.md` into each
  agent's workspace as `SOUL.md`, giving each agent a distinct persona.
  Any stale `SOUL.md` from a previous bootstrap run is removed first.
- Enabled `gateway.http.endpoints.chatCompletions = true` (default is
  `false`).
- Pinned `agents.defaults.model.primary = $MODEL` and each agent's
  `model.primary = $MODEL` so the first turn has a valid default.

## MCP tool surface (Phase 2.6)

The autonomous-loop path (`examples/openclaw_nav_autonomous.py`) flips the
integration around: the Gateway still receives one long-running
`POST /v1/chat/completions` kickoff, but the agent's only path back to the
AI2-THOR engine is three **first-class MCP tools** exposed by a host-side
FastMCP server. The agent sees them as:

- `roboclaws__observe()` — FPV + overhead PNG frames + structured state JSON
- `roboclaws__move(direction, reason)` — one physical step;
  `direction` is one of `MoveAhead`, `MoveBack`, `MoveLeft`, `MoveRight`,
  `RotateLeft`, `RotateRight`, `LookUp`, `LookDown`
- `roboclaws__done(reason)` — end the run cleanly

The agent runs under Gateway tool `profile: "minimal"`, so its complete tool
list is exactly `session_status` plus the three above — no `exec`, no generic
`image`, no `read`/`write`/`browser`. This is enforced at config time by the
bootstrap script; no prompt-steering needed (and none should be added — the
tools literally don't exist in the agent's surface anymore).

Supersedes the Phase 2.5 `curl`-from-`exec` HTTP contract, which is gone
entirely — `roboclaws/openclaw/sim_server.py` was deleted in plan 02.6-05 and
no operator recipe here should mention it. The full lesson lives in
[`../retrospectives/phase-2.6.md`](../retrospectives/phase-2.6.md).

### Install

```bash
pip install -e ".[openclaw,dev]"   # pulls mcp[cli]>=1.27
```

### Env vars

| Var | Default | Purpose |
|-----|---------|---------|
| `ROBOCLAWS_MCP_URL` | `http://host.docker.internal:18788/mcp` | URL the Gateway container uses to reach the host-side MCP server. Seeded into `openclaw.json` *before* first container start so the Gateway never triggers its SIGUSR1 restart dance on live `mcp.servers` edits. |
| `ROBOCLAWS_TOOL_PROFILE` | `minimal` | Agent tool allowlist. Accepted values: `minimal`, `coding`, `messaging`. Leave `minimal` for autonomous-nav; `coding` reintroduces `exec`/`image`/`browser` and breaks the Phase 2.6 contract (Phase 2.5 proved Kimi drifts straight back to `exec` in that mode). Typos die 1 at bootstrap start. |

`SIM_SERVER_URL` is still accepted as a deprecated fallback — bootstrap
translates it to `ROBOCLAWS_MCP_URL` with a stderr `WARN` — and will be
removed in a follow-on phase. New code should set `ROBOCLAWS_MCP_URL` directly.

### Run the autonomous demo

```bash
export KIMI_API_KEY=sk-...
python examples/openclaw_nav_autonomous.py \
  --scene FloorPlan201 \
  --max-moves 30 \
  --wall-budget 180
```

Output lands in `output/openclaw-autonomous/<timestamp>/` with `replay.gif`,
`report.html`, `trace.jsonl`, and `run_result.json`. The example starts the
MCP server in-process on port `18788` before the bootstrap subprocess runs, so
operators don't need to launch anything extra. The current default prompt-image
bundle is `map-v2+chase`; pass `--views baseline` or `--views map-v2` when you
want a direct comparison.

### Reuse one long-lived Gateway for repeated probes

For local validation it is often faster to bootstrap once and reuse the same
Gateway container across multiple autonomous runs:

```bash
export OPENCLAW_GATEWAY_TOKEN=$(./scripts/openclaw-bootstrap.sh)

python examples/openclaw_nav_autonomous.py --skip-bootstrap \
  --scene FloorPlan201 --max-moves 50 --wall-budget 300
python examples/openclaw_nav_autonomous.py --skip-bootstrap \
  --scene FloorPlan201 --max-moves 50 --wall-budget 300
```

`--skip-bootstrap` tells the example to reuse the running Gateway referenced
by `OPENCLAW_GATEWAY_TOKEN` instead of creating and removing the container on
every run. AI2-THOR engine state is reset per run via
`bridge._reset_workspace_state` — `z=1.5` spawn on `FloorPlan201` both times.

### Transcript capture (Phase 2.7)

Autonomous runs now persist assistant transcript data additively in three
places:

- `trace.jsonl` gets `assistant_transcript` events
- `run_result.json` exposes `transcript_capture_mode`, `transcript_source`,
  and `transcript_messages`
- `report.html` renders a `Transcript` section whenever transcript entries
  exist

The CLI keeps `--transcript-mode {stream|terminal-body}` as a validation/debug
override, but omitting the flag uses the shipped default request mode.

Separately, the autonomous example's current default `--views` bundle is
`map-v2+chase`. That view choice is independent of transcript capture mode.

On the dated local validation rerun for Phase 2.7, the shipped default was:

- request mode: `terminal-body`
- actual transcript source on the long-running autonomous timeout path:
  `session-store`

That means operators should not read `terminal-body` as "the final HTTP body
always arrived". On long autonomous runs, the non-stream request may still hit
the wall-clock limit before a terminal body is returned; in that case the
bridge recovers truthful assistant-visible text from the Gateway's per-session
JSONL store and records `transcript_source: "session-store"`.

The explicit `stream` override is still useful for comparison runs, but it can
emit hundreds of tiny chunk rows and may overrun the practical request wall
clock on long autonomous runs. It is not the shipped default. Use it when you
explicitly want HTTP chunk-level visibility, not the cleanest operator report.

Live evidence for the winner/loser comparison lives in
[`.planning/phases/02.7-openclaw-intermediate-message-capture/02.7-LOCAL-PROBE-RESULTS.md`](../../.planning/phases/02.7-openclaw-intermediate-message-capture/02.7-LOCAL-PROBE-RESULTS.md).

### Gotchas

**1. MCP server must bind `host="0.0.0.0"`, not `127.0.0.1`, on Linux.**

The Gateway container reaches the host via `--add-host=host.docker.internal:host-gateway`
which resolves to the docker0 bridge IP (typically `172.17.0.1`), not host
loopback. A host-side MCP server bound only to `127.0.0.1` is **unreachable**
from the container on recent Linux kernels + Docker (verified on kernel 6.17
+ Docker 29.2.1 during plan 02.6-06; symptom was
`[bundle-mcp] failed to start server "roboclaws": TypeError: fetch failed`
in the Gateway log and the agent reporting "I don't have access to a tool
named roboclaws__observe"). `examples/openclaw_nav_autonomous.py` already
passes `host="0.0.0.0"` at the `make_roboclaws_mcp(...)` call site; any new
caller starting the MCP server independently must do the same. LAN-exposure
risk is accepted for local-dev on a trusted workstation.

**2. The MCP config key is `transport`, not `type`.**

Bootstrap seeds the correct shape automatically. If you hand-edit
`openclaw.json` and use `{"type": "http", ...}` the Gateway silently rejects
the server and the agent won't see any MCP tools. Accepted `transport`
values are `"streamable-http"` and `"sse"`. Internals spelunking lives in
[`openclaw-gateway-internals.md`](openclaw-gateway-internals.md#mcp-config-in-openclawjson).

**3. Changing `mcp.servers` on a running Gateway triggers a container exit.**

The Gateway reloads MCP config by sending itself SIGUSR1, which in Docker
means PID-1 exits and the container stops (`Exited (0)`). Bootstrap avoids
this by seeding `mcp.servers` into `openclaw.json` *before* the first
`docker run`. Don't use `openclaw mcp set` on a live container unless you
mean to restart.

### Verify MCP is reachable from the Gateway container

Before a real autonomous run, probe MCP `initialize` from inside the Gateway:

```bash
docker exec openclaw-gateway curl -sS -X POST \
  http://host.docker.internal:18788/mcp \
  -H 'Accept: application/json, text/event-stream' \
  -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'
```

Expected: `HTTP 200` with an SSE `data:` line whose JSON contains
`"serverInfo":{"name":"roboclaws",...}`. If the server info is missing,
re-check gotcha #1 above (MCP bind address).

If the bootstrap script's built-in `PONG` smoke probe is flaky on a provider
even though the container is healthy, verify the Gateway itself first:

```bash
curl -sf http://127.0.0.1:18789/readyz
```

`{"ready":true}` means the Gateway is up; the live bearer token is stored in
`/home/node/.openclaw/openclaw.json` inside the container.

### Live-probed evidence

End-to-end evidence for this contract (6 probes covering MCP reachability,
multimodal vision flow, tool-allowlist enforcement, full autonomous run,
back-to-back workspace reset, and prompt-token overhead ratio) lives in
[`.planning/phases/02.6-openclaw-mcp-tools-integration/02.6-LOCAL-PROBE-RESULTS.md`](../../.planning/phases/02.6-openclaw-mcp-tools-integration/02.6-LOCAL-PROBE-RESULTS.md).
Linux-only bootstrap fallback (`--network host`) is still available if
`--add-host=host.docker.internal:host-gateway` doesn't resolve on a specific
machine: edit `scripts/openclaw-bootstrap.sh` locally and swap the
published-port + `--add-host` pair for `--network host`. Not portable to
Docker Desktop.

## Troubleshooting

### `bootstrap.sh` exits 2 on pre-seed
The one-shot `--user root` pre-seed couldn't talk to Docker. Check your
Docker daemon is running and that your user can talk to the socket
(`docker ps` should work without `sudo`).

### Gateway returns 401
The persisted token was regenerated (e.g. you recreated the volume).
Extract the live one and re-export `OPENCLAW_GATEWAY_TOKEN`:

```bash
docker exec openclaw-gateway sh -lc 'cat /home/node/.openclaw/openclaw.json' \
  | python -c 'import json,sys; print(json.load(sys.stdin)["gateway"]["auth"]["token"])'
```

### Chat agent says it only has `session_status`

Check the latest host trace first:

```bash
tail -5 output/openclaw-interactive/*/trace.jsonl
docker logs --tail 80 openclaw-gateway
```

If the trace shows `interactive_stopped` before the Gateway log says
`ready`, the host-side Roboclaws MCP server has already shut down. The
Gateway may still serve the Control UI, but it cannot attach
`roboclaws__observe`, `roboclaws__move`, or `roboclaws__done`, so the
minimal profile exposes only `session_status`. Re-run `just chat::run`; current
bootstrap waits 180s for cold starts and removes the container on startup
failure to avoid this orphan state.

Or just re-run `bootstrap.sh` and re-capture `TOKEN`.

### Gateway returns 400 `Invalid model` on `openclaw/agent-N`
`bootstrap.sh` didn't register agent-N. Re-run with a higher `AGENTS=`:

```bash
TOKEN=$(AGENTS=4 ./scripts/openclaw-bootstrap.sh)
```

### Gateway returns 404 on `/v1/chat/completions`
Bootstrap didn't enable the chat-completions endpoint (or an older
Gateway image is being used). Re-run `bootstrap.sh` — it always seeds
`gateway.http.endpoints.chatCompletions.enabled = true`.

### Gateway logs

```bash
docker logs -f openclaw-gateway
```

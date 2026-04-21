# OpenClaw Gateway — local quick-start

This is the concrete recipe for running the Phase 2 demo
(`examples/openclaw_demo.py`) against a local OpenClaw Gateway. CI follows
the same contract in `.github/workflows/ci.yml` under the `openclaw-smoke`
job.

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
| `AGENTS`            | `2`                                       | Number of named agents (`1..8`).                                |
| `AGENT_PREFIX`      | `agent-`                                  | Must match `--agent-prefix` on the demo.                        |
| `AGENT_SOULS`       | `` (empty)                                | Csv of soul names per agent, e.g. `aggressive,defensive`. Supports dict form `agent-0:aggressive,agent-2:cooperative`. |
| `SOULS_DIR`         | `$PWD/skills/ai2thor-navigator/souls`     | Directory containing `<name>.md` SOUL files.                    |
| `PERSONALITY_PROBE` | `1`                                       | Set to `0` to skip divergence probe (needed when souls are identical). |
| `IMAGE`             | `ghcr.io/openclaw/openclaw:2026.4.14`     | Pinned digest-traceable tag.                                    |
| `MODEL`             | per-provider default (see below)          | Explicit override. Format: `<provider>/<model-id>`.             |
| `HOST_IP`           | `127.0.0.1`                               | Gateway port is localhost-only by default.                      |
| `PORT`              | `18789`                                   | Gateway HTTP port.                                              |
| `CONTAINER`         | `openclaw-gateway`                        | Docker container name.                                          |
| `VOLUME`            | `openclaw-gateway-config`                 | Docker volume holding `openclaw.json` + state.                  |

The bootstrap ships a **deliberately narrow** provider list — just the two
models verified end-to-end with the demo (FPV + overhead = 2 images per
turn, so the model must be free, multi-image-capable, and cooperate with
the Gateway's tool-bearing agent framework):

| Provider | Default model                           | Upstream                                      | Free | Vision | Multi-image |
|----------|-----------------------------------------|-----------------------------------------------|------|--------|-------------|
| `nvidia` | `nvidia/nvidia/nemotron-nano-12b-v2-vl` | `https://integrate.api.nvidia.com/v1`         | yes  | yes    | yes         |
| `kimi`   | `kimi/k2p5`                             | `https://api.kimi.com/coding/` (→ Kimi 2.6)   | yes  | yes    | yes         |

> ℹ️ `kimi/k2p5` is the Gateway's legacy alias; it resolves upstream to
> `kimi-for-coding` — the current Kimi 2.6 coding-tier model — per
> `/app/dist/provider-catalog-BCrO6TZn.js`. If the Kimi coding quota is
> exhausted the Gateway surfaces a `rate_limit_error` in the first turn
> (the probe catches it and the bootstrap exits 4).

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

Or use the Makefile shortcut: `make openclaw-territory`

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

Or use the Makefile shortcut: `make openclaw-coverage`

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

## Autonomous loop — sim server networking (Phase 2.5)

The autonomous-loop path (`examples/openclaw_nav_autonomous.py`) flips the
integration around: the Gateway still receives one long-running
`POST /v1/chat/completions` kickoff, but the agent then calls host-side tools
(`observe`, `move`, `done`) on a local sim server. That sim server runs on the
host, not in the container, so the Gateway container needs a reliable route back
to the host-side listener on port `18788`. In the current implementation the sim
server binds `0.0.0.0` so the container can reach it through the host-gateway
bridge while the Gateway port itself remains localhost-only.

The bootstrap now adds `--add-host=host.docker.internal:host-gateway`
unconditionally. On Docker 20.10+ Linux this resolves `host-gateway` to the
bridge gateway IP, which gives the container a stable name for the host. On
Docker Desktop for macOS and Windows, `host.docker.internal` already resolves
natively, so the same setting works there too. This is the default path for the
autonomous loop because it keeps normal port publishing (`-p 127.0.0.1:18789:18789`)
intact while still letting the container reach the host-side sim server.

Bootstrap also accepts `SIM_SERVER_URL`, which defaults to
`http://host.docker.internal:18788`, and passes it into the container. Use that
when you need the autonomous-loop caller to point at a non-default port or a
different host alias. The durable tool contract in
`skills/ai2thor-navigator/SKILL.md` is written against the default URL above, so
if you override `SIM_SERVER_URL` locally keep the skill contract and runtime
routing aligned for your probe.

Linux-only fallback: `--network host`. If `--add-host=host.docker.internal:host-gateway`
does not resolve on a specific machine, the escape hatch is to edit
`scripts/openclaw-bootstrap.sh` locally and replace the published-port +
`--add-host` pair with `--network host`. In that mode Docker does not publish
`-p "${HOST_IP}:${PORT}:18789"` because the container shares the host network
stack directly; the Gateway simply binds to `18789` on the host. This fallback
is Linux-only and not portable to Docker Desktop on macOS or Windows.

Before a real autonomous run, do the live probe from inside the container:

```bash
docker exec openclaw-gateway curl -sf \
  http://host.docker.internal:18788/observe | head -c 200
```

### Reuse one long-lived Gateway for repeated probes

For local validation, it is often faster to bootstrap once and reuse the same Gateway
container across multiple autonomous runs:

```bash
export OPENCLAW_GATEWAY_TOKEN=$(./scripts/openclaw-bootstrap.sh)

python examples/openclaw_nav_autonomous.py --skip-bootstrap \
  --scene FloorPlan201 --max-moves 50 --wall-budget 300
python examples/openclaw_nav_autonomous.py --skip-bootstrap \
  --scene FloorPlan201 --max-moves 50 --wall-budget 300
```

`--skip-bootstrap` tells the example to reuse the running Gateway referenced by
`OPENCLAW_GATEWAY_TOKEN` instead of creating and removing the container on every run.
This is the path used for Phase 2.5's back-to-back local reset probe.

If the bootstrap script's built-in `PONG` smoke probe is flaky on a provider even
though the container is healthy, verify the service directly first:

```bash
curl -sf http://127.0.0.1:18789/readyz
```

If that returns `{"ready":true}`, the Gateway itself is up. The live bearer token is
stored in `/home/node/.openclaw/openclaw.json` inside the container and can be read
there for a manual reuse-session export when needed.

A `200` plus the first chunk of JSON is the green light that the container can
see the host-side sim server. If that probe fails, fix the networking first; do
not treat the later autonomous-loop failure as an agent bug.

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
